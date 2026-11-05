"""
ViperForge — Filesystem Locations
Anchors user-data directories (generated exploits, workspaces, macros) to a
fixed root instead of the current working directory, so running ViperForge
from another folder doesn't scatter output/ and workspaces/ around the disk.

  - From source:          <repo>/output, <repo>/workspaces
  - PyInstaller .exe:     next to ViperForge.exe
"""

import sys
from pathlib import Path


def _data_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


DATA_ROOT      = _data_root()
OUTPUT_DIR     = DATA_ROOT / "output"
WORKSPACES_DIR = DATA_ROOT / "workspaces"
MACROS_DIR     = WORKSPACES_DIR / "macros"
