"""builder_loop / builder_try_catch: blocks on the Success pin are the body, the Failure pin the error path."""

import ast

import pytest

from viperforge import graph
from viperforge.engine import generate_chain, preview_chain
from viperforge.macro import create_macro_from_blocks
from viperforge.registry import ExploitDef, get_exploit_by_name
from viperforge.session import Session
from viperforge.validator import WARNING, validate_chain

from conftest import closed_port, make_session, run_script, say

S, F = graph.SUCCESS, graph.FAILURE


def show(var: str):
    return make_session("builder_print", MESSAGE="ITEM", VAR_NAME=var)


def wordlist(*words):
    return make_session("builder_variable_set", VAR_NAME="wordlist", MODE="EVAL",
                        VALUE=repr(list(words)))


def run(tmp_path, sessions, edges=None) -> str:
    return run_script(generate_chain(sessions, str(tmp_path / "chain.py"), edges))


def lines_with(out: str, text: str):
    return [l for l in out.splitlines() if text in l]


# ── builder_loop ──────────────────────────────────────────────────────────────

def test_loop_runs_body_per_item_then_continues_at_join(tmp_path):
    # wordlist → loop -ok-> show(item) → AFTER ; loop -err-> AFTER
    sessions = [wordlist("alpha", "beta", "gamma"), make_session("builder_loop"),
                show("item"), say("AFTER")]
    edges = [(0, 1, S), (1, 2, S), (2, 3, S), (1, 3, F)]
    out = run(tmp_path, sessions, edges)
    assert [l.split("= ")[1].rstrip("]") for l in lines_with(out, "ITEM [item")] == ["alpha", "beta", "gamma"]
    assert len(lines_with(out, "AFTER")) == 1
    assert out.index("gamma") < out.index("AFTER")


def test_loop_without_failure_pin_wraps_rest_of_path(tmp_path):
    sessions = [make_session("builder_loop", MODE="RANGE", RANGE_START="0", RANGE_END="3"),
                show("item"), say("TAIL")]
    out = run(tmp_path, sessions, [(0, 1, S), (1, 2, S)])
    assert len(lines_with(out, "ITEM [item")) == 3
    assert len(lines_with(out, "TAIL")) == 3


def test_loop_over_file_lines(tmp_path):
    words = tmp_path / "words.txt"
    words.write_text("root\n\nadmin\n", encoding="utf-8")
    sessions = [make_session("builder_loop", MODE="FILE", FILE_PATH=str(words)), show("item")]
    out = run(tmp_path, sessions, [(0, 1, S)])
    assert [l.split("= ")[1].rstrip("]") for l in lines_with(out, "ITEM [item")] == ["root", "admin"]


@pytest.mark.parametrize("loop", [
    lambda tmp: make_session("builder_loop", MODE="FILE", FILE_PATH=str(tmp / "missing.txt")),
    lambda tmp: make_session("builder_loop", MODE="LIST", WORDLIST_VAR="nothing_here"),
], ids=["missing-file", "empty-list"])
def test_loop_failure_pin_runs_when_nothing_to_iterate(tmp_path, loop):
    sessions = [loop(tmp_path), show("item"), say("NO-ITEMS"), say("AFTER")]
    out = run(tmp_path, sessions, [(0, 1, S), (0, 2, F), (1, 3, S), (2, 3, S)])
    assert "NO-ITEMS" in out and "ITEM [" not in out and "AFTER" in out


def test_loop_break(tmp_path):
    sessions = [make_session("builder_loop", MODE="RANGE", RANGE_START="0", RANGE_END="10"),
                show("item"),
                make_session("builder_variable_set", VAR_NAME="_vf_loop_break", VALUE="1")]
    out = run(tmp_path, sessions, [(0, 1, S), (1, 2, S)])
    assert len(lines_with(out, "ITEM [item")) == 1
    assert "break requested" in out


def test_linear_chain_without_graph_uses_following_blocks_as_body(tmp_path):
    # CLI-style call: no edges → the list is the chain
    sessions = [make_session("builder_loop", MODE="RANGE", RANGE_START="0", RANGE_END="2"), say("BODY")]
    out = run(tmp_path, sessions)
    assert len(lines_with(out, "BODY")) == 2


def test_unconnected_blocks_are_not_part_of_the_body(tmp_path):
    sessions = [make_session("builder_loop", MODE="RANGE", RANGE_START="0", RANGE_END="2"), say("ONCE")]
    out = run(tmp_path, sessions, [])
    assert len(lines_with(out, "ONCE")) == 1


def test_nested_loops(tmp_path):
    sessions = [make_session("builder_loop", MODE="RANGE", RANGE_START="0", RANGE_END="2", ITERATOR_VAR="i"),
                make_session("builder_loop", MODE="RANGE", RANGE_START="0", RANGE_END="3", ITERATOR_VAR="j"),
                show("j")]
    out = run(tmp_path, sessions, [(0, 1, S), (1, 2, S)])
    assert len(lines_with(out, "ITEM [j")) == 6


# ── builder_try_catch ─────────────────────────────────────────────────────────

def _guarded_connect(port, **opts):
    # try -ok-> socket → AFTER ; try -err-> HANDLER → AFTER
    sessions = [make_session("builder_try_catch", **opts),
                make_session("builder_socket", TARGET_PORT=str(port)),
                make_session("builder_print", MESSAGE="HANDLER", VAR_NAME="_vf_last_error"),
                say("AFTER")]
    return sessions, [(0, 1, S), (0, 2, F), (1, 3, S), (2, 3, S)]


def test_try_catch_runs_handler_on_error(tmp_path):
    out = run(tmp_path, *_guarded_connect(closed_port(), FALLBACK_ACTION="LOG"))
    handler = lines_with(out, "HANDLER")
    assert len(handler) == 1 and "<not found in CTX>" not in handler[0]
    assert "error logged" in out and "AFTER" in out


def test_try_catch_skips_handler_when_body_succeeds(tmp_path):
    sessions = [make_session("builder_try_catch"), say("BODY"), say("HANDLER"), say("AFTER")]
    out = run(tmp_path, sessions, [(0, 1, S), (0, 2, F), (1, 3, S), (2, 3, S)])
    assert "BODY" in out and "HANDLER" not in out and "AFTER" in out


def test_try_catch_retries_body(tmp_path):
    out = run(tmp_path, *_guarded_connect(closed_port(), FALLBACK_ACTION="RETRY", RETRY_COUNT="2"))
    assert len(lines_with(out, "Creating socket")) == 2
    assert "retries exhausted" in out and "HANDLER" in out and "AFTER" in out


def test_try_catch_only_catches_selected_error_types(tmp_path):
    sessions, edges = _guarded_connect(closed_port(), ERROR_TYPES="Timeout")
    out = run_script(generate_chain(sessions, str(tmp_path / "chain.py"), edges), expect_ok=False)
    assert "HANDLER" not in out and "AFTER" not in out


def test_nested_try_catch_keeps_outer_on_success_path(tmp_path):
    # outer -ok-> inner ; inner -ok-> socket(fails) / -err-> INNER-HANDLER ; both → OUTER-BODY-DONE
    # outer -err-> OUTER-HANDLER
    sessions = [make_session("builder_try_catch"), make_session("builder_try_catch"),
                make_session("builder_socket", TARGET_PORT=str(closed_port())),
                say("INNER-HANDLER"), say("OUTER-BODY-DONE"), say("OUTER-HANDLER")]
    edges = [(0, 1, S), (0, 5, F), (1, 2, S), (1, 3, F), (2, 4, S), (3, 4, S)]
    out = run(tmp_path, sessions, edges)
    assert "INNER-HANDLER" in out and "OUTER-BODY-DONE" in out
    assert "OUTER-HANDLER" not in out


# ── composition ───────────────────────────────────────────────────────────────

def test_container_inside_macro(tmp_path):
    blocks = [
        {"uuid": "l", "exploit_id": get_exploit_by_name("builder_loop").id,
         "options": {"MODE": "RANGE", "RANGE_START": "0", "RANGE_END": "2"}},
        {"uuid": "p", "exploit_id": get_exploit_by_name("builder_print").id,
         "options": {"MESSAGE": "IN-MACRO-LOOP"}},
    ]
    mdef = create_macro_from_blocks("Looper", "", blocks, [{"src": "l", "dst": "p", "port_type": S}])
    vdef = ExploitDef(id=-1, name="Looper", category="Macros", description="", template="", options=[])
    vdef._macro_def = mdef
    macro = Session()
    macro.set_exploit(vdef)
    out = run(tmp_path, [macro, say("AFTER-MACRO")], [(0, 1, S)])
    assert len(lines_with(out, "IN-MACRO-LOOP")) == 2
    assert len(lines_with(out, "AFTER-MACRO")) == 1


def test_container_preview_without_body_is_valid():
    for name in ("builder_loop", "builder_try_catch"):
        code = preview_chain([make_session(name), say("x")], [])
        ast.parse(code)
        assert "@@VF_" not in code


# ── validator ─────────────────────────────────────────────────────────────────

def _container_warnings(issues, name):
    return [i for i in issues if i.block_name == name and i.severity == WARNING
            and "Success pin" in i.message]


@pytest.mark.parametrize("name", ["builder_loop", "builder_try_catch"])
def test_validator_warns_on_empty_container(name):
    sessions = [make_session(name), say("x")]
    assert _container_warnings(validate_chain([None] * 2, sessions, []), name)
    assert not _container_warnings(validate_chain([None] * 2, sessions, [(0, 1, S)]), name)


def test_validator_linear_chain_container_last_is_empty():
    sessions = [say("x"), make_session("builder_loop")]
    assert _container_warnings(validate_chain([None] * 2, sessions), "builder_loop")


def test_validator_knows_loop_iterator_variable():
    sessions = [make_session("builder_loop", ITERATOR_VAR="pw"),
                make_session("builder_b64encode", INPUT_VAR="pw")]
    issues = validate_chain([None] * 2, sessions, [(0, 1, S)])
    assert not [i for i in issues if i.block_name == "builder_b64encode"]
