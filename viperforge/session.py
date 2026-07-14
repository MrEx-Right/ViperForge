"""
ViperForge v2.0 — Session State
Holds the active exploit and parameter values.
"""

from typing import Optional, Dict, Any
from .registry import ExploitDef


class Session:
    def __init__(self):
        self.active_exploit: Optional[ExploitDef] = None
        self.options: Dict[str, str] = {}

    def set_exploit(self, exploit: ExploitDef) -> None:
        self.active_exploit = exploit
        # Load default values
        self.options = {opt.name: opt.default for opt in exploit.options}

    def set_option(self, key: str, value: str) -> None:
        self.options[key] = value

    def get_option(self, key: str) -> str:
        return self.options.get(key, "")

    def reset(self) -> None:
        self.active_exploit = None
        self.options = {}

    def to_dict(self) -> Dict[str, Any]:
        """Returns a dict for Jinja2 template context."""
        return dict(self.options)
