import json
from pathlib import Path

from viperforge.macro import (
    MacroDef, create_macro_from_blocks, delete_macro, list_macros,
    load_macro, macro_to_sessions, save_macro,
)
from viperforge.registry import get_exploit_by_name


def _blocks(*names, **opts):
    return [{"exploit_id": get_exploit_by_name(n).id, "options": dict(opts)} for n in names]


def test_save_load_roundtrip(isolated_dirs):
    _, macros_dir = isolated_dirs
    m = create_macro_from_blocks("Recon Flow", "desc", _blocks("builder_socket", "builder_send"),
                                 [{"src": "a", "dst": "b", "port_type": "success"}])
    path = save_macro(m)
    assert macros_dir in Path(path).parents
    assert load_macro(path).to_dict() == m.to_dict()


def test_list_and_delete(isolated_dirs):
    a = create_macro_from_blocks("A", "", _blocks("builder_print"), [])
    b = create_macro_from_blocks("B", "", _blocks("builder_sleep"), [])
    save_macro(a)
    save_macro(b)
    assert {m.id for m in list_macros()} == {a.id, b.id}
    assert delete_macro(a.id) is True
    assert delete_macro(a.id) is False
    assert [m.id for m in list_macros()] == [b.id]


def test_list_skips_corrupt_files(isolated_dirs):
    _, macros_dir = isolated_dirs
    save_macro(create_macro_from_blocks("Good", "", _blocks("builder_print"), []))
    (macros_dir / "broken.json").write_text("{not json", encoding="utf-8")
    assert [m.name for m in list_macros()] == ["Good"]


def test_list_when_dir_missing():
    assert list_macros() == []
    assert delete_macro("nope") is False


def test_from_dict_defaults():
    m = MacroDef.from_dict({})
    assert m.name == "Unnamed Macro"
    assert m.blocks == [] and m.connections == []
    assert m.id


def test_macro_to_sessions_applies_options_and_skips_unknown():
    blocks = _blocks("builder_sleep", SECONDS="7") + [{"exploit_id": 99999, "options": {}}]
    sessions = macro_to_sessions(create_macro_from_blocks("M", "", blocks, []))
    assert len(sessions) == 1
    assert sessions[0].active_exploit.name == "builder_sleep"
    assert sessions[0].get_option("SECONDS") == "7"


def test_saved_file_is_utf8_json(isolated_dirs):
    path = save_macro(create_macro_from_blocks("Çığ Ünlü", "açıklama", [], []))
    with open(path, encoding="utf-8") as f:
        assert json.load(f)["name"] == "Çığ Ünlü"
