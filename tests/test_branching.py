import ast
import socket
import threading

import pytest

from viperforge import engine, graph
from viperforge.engine import _indent, generate_chain, preview_chain
from viperforge.macro import create_macro_from_blocks, macro_to_graph
from viperforge.registry import ExploitDef, get_exploit_by_name
from viperforge.session import Session
from viperforge.validator import ERROR, validate_chain

from conftest import closed_port, make_session, run_script, say

S, F = graph.SUCCESS, graph.FAILURE


def macro_session(blocks, connections, name="Macro") -> Session:
    mdef = create_macro_from_blocks(name, "", blocks, connections)
    vdef = ExploitDef(id=-1, name=name, category="Macros", description="", template="", options=[])
    vdef._macro_def = mdef
    s = Session()
    s.set_exploit(vdef)
    return s


def macro_block(uuid, name, **opts):
    return {"uuid": uuid, "exploit_id": get_exploit_by_name(name).id, "options": opts}


# ── graph helpers ─────────────────────────────────────────────────────────────

def test_outgoing_keeps_first_edge_per_port():
    succ, fail = graph.outgoing(3, [(0, 1, S), (0, 2, S), (0, 2, F), (5, 1, S)])
    assert succ == [1, None, None]
    assert fail == [2, None, None]


def test_roots_and_chain_order():
    edges = [(2, 0, S), (0, 1, F)]
    assert graph.roots(4, edges) == [2, 3]
    assert graph.chain_order(4, edges) == [2, 0, 1, 3]


def test_find_cycle():
    assert graph.find_cycle(3, [(0, 1, S), (1, 2, S)]) is None
    assert graph.find_cycle(3, [(0, 1, S), (1, 2, F), (2, 0, S)]) == [0, 1, 2, 0]


def test_post_dominators_diamond():
    # 0 -ok-> 1 -> 3, 0 -err-> 2 -> 3
    ipdom = graph.immediate_post_dominators(4, [(0, 1, S), (0, 2, F), (1, 3, S), (2, 3, S)])
    assert ipdom == [3, 3, 3, None]


def test_post_dominators_failure_without_join():
    ipdom = graph.immediate_post_dominators(3, [(0, 1, S), (0, 2, F)])
    assert ipdom[0] is None


# ── generated structure ───────────────────────────────────────────────────────

def test_linear_chains_ignore_edges_without_failure_pins():
    sessions = [make_session("builder_socket"), make_session("builder_send")]
    assert preview_chain(sessions, [(0, 1, S)]) == preview_chain(sessions)


def test_branch_structure():
    sessions = [make_session("builder_socket"), say("OK"), say("FAIL"), say("JOIN")]
    code = preview_chain(sessions, [(0, 1, S), (0, 2, F), (1, 3, S), (2, 3, S)])
    tree = ast.parse(code)
    main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    kinds = [type(n).__name__ for n in main.body]
    assert "Try" in kinds and "If" in kinds
    # Join block comes after the if/else, at main() level — generated exactly once
    assert code.count('"JOIN"') == 1
    assert kinds.index("If") < max(i for i, n in enumerate(main.body)
                                   if isinstance(n, ast.Assign) and "JOIN" in ast.unparse(n))


def test_cycle_is_rejected_everywhere():
    sessions = [say("a"), say("b")]
    edges = [(0, 1, S), (1, 0, F)]
    assert "loop" in preview_chain(sessions, edges)
    with pytest.raises(RuntimeError, match="loop"):
        generate_chain(sessions, edges=edges)
    issues = validate_chain([None, None], sessions, edges)
    assert any(i.severity == ERROR and "loop" in i.message for i in issues)


def test_unusual_block_names_cannot_break_generated_code():
    sessions = [macro_session([macro_block("a", "builder_print")], [], name='Evil"\n{x}'), say("ok")]
    code = preview_chain(sessions, [(0, 1, F)])
    ast.parse(code)


# ── execution: the branch actually taken at runtime ───────────────────────────

def _connect_chain(port: int):
    sessions = [make_session("builder_socket", TARGET_PORT=str(port)),
                say("OK-PATH"), say("FAIL-PATH"), say("JOIN")]
    return sessions, [(0, 1, S), (0, 2, F), (1, 3, S), (2, 3, S)]


def test_failure_branch_runs_when_block_raises(tmp_path):
    sessions, edges = _connect_chain(closed_port())
    out = run_script(generate_chain(sessions, str(tmp_path / "x.py"), edges))
    assert "FAIL-PATH" in out and "OK-PATH" not in out and "JOIN" in out


def test_success_branch_runs_when_block_succeeds(tmp_path):
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    threading.Thread(target=lambda: server.accept(), daemon=True).start()
    try:
        sessions, edges = _connect_chain(server.getsockname()[1])
        out = run_script(generate_chain(sessions, str(tmp_path / "x.py"), edges))
    finally:
        server.close()
    assert "OK-PATH" in out and "FAIL-PATH" not in out and "JOIN" in out


@pytest.mark.parametrize("value, expected", [("admin", "OK-PATH"), ("guest", "FAIL-PATH")])
def test_if_else_flag_selects_branch(tmp_path, value, expected):
    sessions = [
        make_session("builder_variable_set", VAR_NAME="role", VALUE=value),
        make_session("builder_if_else", VAR_NAME="role", OPERATOR="==", COMPARE_VALUE="admin"),
        say("OK-PATH"), say("FAIL-PATH"),
    ]
    edges = [(0, 1, S), (1, 2, S), (1, 3, F)]
    out = run_script(generate_chain(sessions, str(tmp_path / "x.py"), edges))
    other = "FAIL-PATH" if expected == "OK-PATH" else "OK-PATH"
    assert expected in out and other not in out


def test_hybrid_chain_keeps_block_order(tmp_path):
    sessions = [say("FIRST"), make_session("network_smb_relay"), say("LAST")]
    code = preview_chain(sessions)
    ast.parse(code)
    flow = code[code.index("def main():"):]
    assert flow.index('"FIRST"') < flow.index("stage_1_network_smb_relay()") < flow.index('"LAST"')


# ── classic stages ────────────────────────────────────────────────────────────

def test_classic_stage_runs_template_main_block():
    code = preview_chain([make_session("web_lfi"), make_session("privesc_suid")])
    tree = ast.parse(code)
    stage = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "stage_1_web_lfi")
    calls = [ast.unparse(n) for n in stage.body if isinstance(n, ast.Expr)]
    assert "poison_log()" in calls and "trigger_lfi()" in calls


def test_indent_preserves_multiline_string_contents():
    code = ['X = """line one', '<root>', '  two"""', 'Y = f"""{1}', 'tail"""', "if True:", "    Z = 1"]
    ns_flat, ns_nested = {}, {}
    exec("\n".join(code), ns_flat)
    exec("def f():\n" + "\n".join(_indent(code)) + "\n    return X, Y\n", ns_nested)
    assert ns_nested["f"]() == (ns_flat["X"], ns_flat["Y"])


# ── macros ────────────────────────────────────────────────────────────────────

def test_macro_expansion_follows_inner_wiring():
    blocks = [macro_block("p", "builder_print"), macro_block("s", "builder_socket")]
    sessions, edges = macro_to_graph(create_macro_from_blocks(
        "M", "", blocks, [{"src": "s", "dst": "p", "port_type": S}]))
    assert [x.active_exploit.name for x in sessions] == ["builder_socket", "builder_print"]
    assert edges == [(0, 1, S)]


def test_macro_with_inner_branch(tmp_path):
    port = closed_port()
    blocks = [macro_block("s", "builder_socket", TARGET_PORT=str(port)),
              macro_block("ok", "builder_print", MESSAGE="IN-OK"),
              macro_block("err", "builder_print", MESSAGE="IN-FAIL")]
    conns = [{"src": "s", "dst": "ok", "port_type": S}, {"src": "s", "dst": "err", "port_type": F}]
    sessions = [macro_session(blocks, conns), say("AFTER")]
    out = run_script(generate_chain(sessions, str(tmp_path / "x.py"), [(0, 1, S)]))
    assert "IN-FAIL" in out and "IN-OK" not in out and "AFTER" in out


def test_failure_pin_on_macro_wraps_whole_macro(tmp_path):
    blocks = [macro_block("a", "builder_print", MESSAGE="IN-MACRO"),
              macro_block("b", "builder_socket", TARGET_PORT=str(closed_port()))]
    sessions = [macro_session(blocks, [{"src": "a", "dst": "b", "port_type": S}]),
                say("OK-PATH"), say("FAIL-PATH")]
    out = run_script(generate_chain(sessions, str(tmp_path / "x.py"), [(0, 1, S), (0, 2, F)]))
    assert "IN-MACRO" in out and "FAIL-PATH" in out and "OK-PATH" not in out


def test_validator_sees_sockets_created_inside_macros():
    sessions = [macro_session([macro_block("s", "builder_socket")], []), make_session("builder_send")]
    issues = validate_chain([None, None], sessions, [(0, 1, S)])
    assert not [i for i in issues if i.severity == ERROR]
