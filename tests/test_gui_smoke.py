import json
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
QtWidgets = pytest.importorskip("PyQt6.QtWidgets")

from viperforge import __version__
from viperforge.registry import get_exploit_by_name


@pytest.fixture(scope="module")
def qapp():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    yield app


@pytest.fixture
def window(qapp):
    from viperforge.gui.main_window import MainWindow
    w = MainWindow()
    yield w
    w.close()
    w.deleteLater()


def test_main_window_shows_version(window):
    labels = [l.text() for l in window.findChildren(QtWidgets.QLabel)]
    assert any(f"v{__version__}" in t for t in labels)


def test_add_blocks_and_get_chain(window):
    for name in ("builder_socket", "builder_send", "builder_recv"):
        window._on_exploit_selected(get_exploit_by_name(name))
    blocks, sessions, edges = window._get_ordered_sessions()
    assert [s.active_exploit.name for s in sessions] == ["builder_socket", "builder_send", "builder_recv"]
    assert edges == []


def test_failure_connection_reaches_engine(window):
    from viperforge.engine import preview_chain
    for name in ("builder_socket", "builder_print", "builder_sleep"):
        window._on_exploit_selected(get_exploit_by_name(name))
    a, b, c = window.canvas.blocks
    a.failure_enabled = True
    window.canvas._add_connector(a, b, "success")
    window.canvas._add_connector(a, c, "failure")

    blocks, sessions, edges = window._get_ordered_sessions()
    assert sorted(edges) == [(0, 1, "success"), (0, 2, "failure")]
    code = preview_chain(sessions, edges)
    assert 'CTX.get("_vf_branch") == "failure"' in code


def test_workspace_roundtrip_keeps_connections_and_pins(window):
    canvas = window.canvas
    for name in ("builder_socket", "builder_send", "builder_print"):
        window._on_exploit_selected(get_exploit_by_name(name))
    a, b, c = canvas.blocks
    a.failure_enabled = True
    a.session.set_option("RHOST", "10.0.0.5")
    canvas._add_connector(a, b, "success")
    canvas._add_connector(a, c, "failure")

    data = json.loads(json.dumps(canvas.to_dict()))
    restored = canvas.from_dict(data)

    assert [blk.exploit_def.name for blk in restored] == ["builder_socket", "builder_send", "builder_print"]
    assert restored[0].failure_enabled is True
    assert restored[0].session.get_option("RHOST") == "10.0.0.5"
    assert sorted(c.port_type for c in canvas._connectors) == ["failure", "success"]


def test_unknown_blocks_are_skipped_on_load(window):
    created = window.canvas.from_dict({"blocks": [{"uuid": "x", "exploit_id": 99999}], "connections": []})
    assert created == []
    assert window.canvas._load_skipped_count == 1
