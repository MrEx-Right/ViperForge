import socket
import subprocess
import sys

import pytest

from viperforge import engine, macro
from viperforge.registry import get_exploit_by_name
from viperforge.session import Session


def make_session(name: str, **options) -> Session:
    """Session for a registry module, with defaults plus any overrides."""
    exp = get_exploit_by_name(name)
    assert exp is not None, f"unknown module: {name}"
    s = Session()
    s.set_exploit(exp)
    for k, v in options.items():
        s.set_option(k, v)
    return s


def say(text: str) -> Session:
    """builder_print block that prints `text`."""
    return make_session("builder_print", MESSAGE=text)


def run_script(path, expect_ok: bool = True) -> str:
    """Execute a generated exploit script and return its stdout."""
    result = subprocess.run([sys.executable, "-X", "utf8", str(path)],
                            capture_output=True, text=True, timeout=60, encoding="utf-8")
    if expect_ok:
        assert result.returncode == 0, result.stderr
    return result.stdout


def closed_port() -> int:
    """A localhost port with nothing listening — connecting to it fails fast."""
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture
def session_factory():
    return make_session


@pytest.fixture(autouse=True)
def isolated_dirs(tmp_path, monkeypatch):
    """Keep generated scripts and macros out of the real output/ and workspaces/."""
    out_dir = tmp_path / "output"
    macros_dir = tmp_path / "workspaces" / "macros"
    monkeypatch.setattr(engine, "OUTPUT_DIR", out_dir)
    monkeypatch.setattr(macro, "MACROS_DIR", macros_dir)
    return out_dir, macros_dir
