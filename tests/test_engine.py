import ast
from pathlib import Path

import pytest

from viperforge import engine
from viperforge.macro import create_macro_from_blocks
from viperforge.registry import REGISTRY, ExploitDef, get_exploit_by_name
from viperforge.session import Session

from conftest import make_session

BUILDER = [e.name for e in REGISTRY if e.name.startswith("builder_")]
CLASSIC = [e.name for e in REGISTRY if not e.name.startswith("builder_")]


def assert_valid_python(code: str) -> None:
    assert not code.startswith(("# Preview error", "# Template not found")), code[:200]
    ast.parse(code)


def macro_session(*names: str) -> Session:
    """A session shaped like the GUI's MacroBlockItem: virtual def tagged with _macro_def."""
    blocks = [{"exploit_id": get_exploit_by_name(n).id, "options": {}} for n in names]
    mdef = create_macro_from_blocks("Test Macro", "", blocks, [])
    vdef = ExploitDef(id=-1, name=mdef.name, category="Macros",
                      description="", template="", options=[])
    vdef._macro_def = mdef
    s = Session()
    s.set_exploit(vdef)
    return s


# ── Single modules ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("name", [e.name for e in REGISTRY])
def test_every_module_renders_valid_python(name):
    assert_valid_python(engine.preview_single(make_session(name)))


def test_generate_single_writes_to_output_dir(isolated_dirs):
    out_dir, _ = isolated_dirs
    path = Path(engine.generate_single(make_session("web_lfi")))
    assert path.parent == out_dir
    assert path.name == "web_lfi_exploit.py"
    assert_valid_python(path.read_text(encoding="utf-8"))


def test_generate_single_respects_out_path(tmp_path):
    target = tmp_path / "custom.py"
    assert engine.generate_single(make_session("web_sqli"), str(target)) == str(target)
    assert target.is_file()


def test_generate_single_without_exploit_raises():
    with pytest.raises(RuntimeError):
        engine.generate_single(Session())


def test_builder_single_block_gets_ctx_declaration():
    code = engine.preview_single(make_session("builder_recv"))
    assert code.startswith("CTX = {}")


def test_payload_is_xor_encoded_into_output(monkeypatch, tmp_path):
    monkeypatch.setattr(engine, "compile_payload", lambda name: "31c050cc")
    target = tmp_path / "bof.py"
    engine.generate_single(make_session("bof_remote", PAYLOAD="execve"), str(target))
    code = target.read_text(encoding="utf-8")
    assert_valid_python(code)
    assert "ViperForge XOR Decoder Stub" in code
    assert 'bytes.fromhex("31c050cc")' in code


# ── Chains ────────────────────────────────────────────────────────────────────

def test_builder_chain_dedupes_imports_and_ctx():
    sessions = [make_session(n) for n in ("builder_socket", "builder_send", "builder_recv")]
    code = engine.preview_chain(sessions)
    assert_valid_python(code)
    lines = code.splitlines()
    imports = [l for l in lines if l.startswith(("import ", "from "))]
    assert len(imports) == len(set(imports))
    assert sum(1 for l in lines if l.startswith("CTX = {}")) == 1
    assert "# Blocks: builder_socket → builder_send → builder_recv" in code


def test_all_builder_blocks_chain_to_valid_python():
    assert_valid_python(engine.preview_chain([make_session(n) for n in BUILDER]))


def test_classic_chain_wraps_stages_in_order():
    sessions = [make_session(n) for n in ("web_lfi", "privesc_suid")]
    code = engine.preview_chain(sessions)
    assert_valid_python(code)
    tree = ast.parse(code)
    funcs = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert funcs == ["stage_1_web_lfi", "stage_2_privesc_suid", "main"]
    assert code.index("    stage_1_web_lfi()") < code.index("    stage_2_privesc_suid()")


def test_all_classic_blocks_chain_to_valid_python():
    assert_valid_python(engine.preview_chain([make_session(n) for n in CLASSIC]))


def test_hybrid_chain_runs_builders_inline_and_classics_as_stages(isolated_dirs):
    sessions = [make_session("builder_socket"), make_session("web_ssti"),
                make_session("builder_print")]
    path = Path(engine.generate_chain(sessions))
    code = path.read_text(encoding="utf-8")
    assert_valid_python(code)
    funcs = [n.name for n in ast.parse(code).body if isinstance(n, ast.FunctionDef)]
    assert funcs == ["stage_1_web_ssti", "main"]
    assert path.parent == isolated_dirs[0]


def test_empty_chain():
    assert engine.preview_chain([]) == "# No blocks in chain."
    with pytest.raises(RuntimeError):
        engine.generate_chain([])


# ── Macros ────────────────────────────────────────────────────────────────────

def test_macro_expands_inline_in_chain():
    expanded = engine.preview_chain(
        [make_session("builder_socket"), make_session("builder_send"), make_session("builder_print")])
    with_macro = engine.preview_chain(
        [macro_session("builder_socket", "builder_send"), make_session("builder_print")])
    assert with_macro == expanded


def test_macro_single_preview_uses_inner_blocks():
    code = engine.preview_single(macro_session("builder_socket", "builder_print"))
    assert_valid_python(code)
    assert "builder_socket → builder_print" in code


def test_empty_macro_is_reported():
    s = macro_session()
    assert "no valid inner blocks" in engine.preview_single(s)
    with pytest.raises(RuntimeError):
        engine.generate_single(s)
