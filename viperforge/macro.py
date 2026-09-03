"""
ViperForge v2.1 — Macro System
Manages composite macro blocks (sub-graphs) that encapsulate
multiple blocks into reusable units.
"""

import json
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Dict, Optional

from .session import Session
from .registry import get_exploit_by_id


MACROS_DIR = Path("workspaces") / "macros"


@dataclass
class MacroDef:
    """Definition of a user-created macro block."""
    id:          str                  # UUID
    name:        str                  # user-defined name
    description: str                  # short description
    blocks:      List[Dict]          # [{exploit_id, options, x, y, uuid, failure_enabled}, ...]
    connections: List[Dict]          # [{src, dst, port_type}, ...]

    def to_dict(self) -> dict:
        return {
            "id":          self.id,
            "name":        self.name,
            "description": self.description,
            "blocks":      self.blocks,
            "connections": self.connections,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "MacroDef":
        return cls(
            id=d.get("id", str(uuid.uuid4())),
            name=d.get("name", "Unnamed Macro"),
            description=d.get("description", ""),
            blocks=d.get("blocks", []),
            connections=d.get("connections", []),
        )


def save_macro(macro: MacroDef, path: Optional[str] = None) -> str:
    """Save a macro definition to JSON. Returns the file path."""
    MACROS_DIR.mkdir(parents=True, exist_ok=True)
    if path is None:
        safe_name = macro.name.replace(" ", "_").lower()
        path = str(MACROS_DIR / f"{safe_name}_{macro.id[:8]}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(macro.to_dict(), f, indent=4, ensure_ascii=False)
    return path


def load_macro(path: str) -> MacroDef:
    """Load a macro definition from a JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return MacroDef.from_dict(data)


def list_macros(macros_dir: Optional[str] = None) -> List[MacroDef]:
    """List all saved macros from the macros directory."""
    d = Path(macros_dir) if macros_dir else MACROS_DIR
    if not d.exists():
        return []
    macros = []
    for p in sorted(d.glob("*.json")):
        try:
            macros.append(load_macro(str(p)))
        except Exception:
            continue
    return macros


def delete_macro(macro_id: str, macros_dir: Optional[str] = None) -> bool:
    """Delete a macro by ID. Returns True if deleted."""
    d = Path(macros_dir) if macros_dir else MACROS_DIR
    if not d.exists():
        return False
    for p in d.glob("*.json"):
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("id") == macro_id:
                p.unlink()
                return True
        except Exception:
            continue
    return False


def macro_to_sessions(macro: MacroDef) -> List[Session]:
    """
    Convert a macro's block list into ordered Session objects.
    This expands the macro for code generation.
    """
    sessions = []
    for b_data in macro.blocks:
        eid = b_data.get("exploit_id")
        exp = get_exploit_by_id(eid)
        if not exp:
            continue
        sess = Session()
        sess.set_exploit(exp)
        for k, v in b_data.get("options", {}).items():
            sess.set_option(k, v)
        sessions.append(sess)
    return sessions


def create_macro_from_blocks(name: str, description: str,
                              blocks_data: List[Dict],
                              connections_data: List[Dict]) -> MacroDef:
    """Create a new MacroDef from canvas block/connection data."""
    return MacroDef(
        id=str(uuid.uuid4()),
        name=name,
        description=description,
        blocks=blocks_data,
        connections=connections_data,
    )
