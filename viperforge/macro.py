"""
ViperForge — Macro System
Manages composite macro blocks (sub-graphs) that encapsulate
multiple blocks into reusable units.
"""

import json
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from .session import Session
from .registry import get_exploit_by_id
from .graph import Edge, SUCCESS, chain_order, remap_edges
from .paths import MACROS_DIR


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


def macro_to_graph(macro: MacroDef) -> Tuple[List[Session], List[Edge]]:
    """
    Convert a macro into Session objects plus the connections between them
    (as index edges), ordered by the macro's own wiring. Blocks whose module
    no longer exists are dropped along with their connections.
    """
    sessions: List[Session] = []
    index_by_uuid: Dict[str, int] = {}
    for b_data in macro.blocks:
        eid = b_data.get("exploit_id")
        exp = get_exploit_by_id(eid)
        if not exp:
            continue
        sess = Session()
        sess.set_exploit(exp)
        for k, v in b_data.get("options", {}).items():
            sess.set_option(k, v)
        if b_data.get("uuid"):
            index_by_uuid[b_data["uuid"]] = len(sessions)
        sessions.append(sess)

    edges: List[Edge] = []
    for c in macro.connections:
        src, dst = index_by_uuid.get(c.get("src")), index_by_uuid.get(c.get("dst"))
        if src is not None and dst is not None:
            edges.append((src, dst, c.get("port_type", SUCCESS)))

    order = chain_order(len(sessions), edges)
    new_index: List[Optional[int]] = [None] * len(sessions)
    for new, old in enumerate(order):
        new_index[old] = new
    return [sessions[i] for i in order], remap_edges(edges, new_index)


def macro_to_sessions(macro: MacroDef) -> List[Session]:
    """
    Convert a macro's blocks into Session objects in wiring order.
    This expands the macro for code generation.
    """
    return macro_to_graph(macro)[0]


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
