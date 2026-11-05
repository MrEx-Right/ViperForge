"""
ViperForge — Exploit Engine
Generates Python exploits from block chain or single session using Jinja2 templates.

Chain modes:
  - "builder_*" blocks  → flat sequential code (CTX shared dict, imports deduped)
  - Classic blocks      → each wrapped in its own function, called by main()
  - Macro blocks        → expanded inline into their constituent blocks (keeping their wiring)
  - Success/Failure     → a block with a connected failure pin runs inside try/except;
                          its success and failure paths become an if/else in main()
  - Mixed builder + classic chains use the same main() flow, so block order is kept
  - builder_loop / builder_try_catch are containers: the blocks on their Success
    pin become the loop body / protected code, the Failure pin their error path
"""

import io
import re
import os
import tokenize
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set
from jinja2 import Environment, FileSystemLoader, Undefined

from .session import Session
from .compiler import compile_payload
from .encoder import encode_shellcode_file
from .paths import OUTPUT_DIR
from .graph import (
    SUCCESS, Edge, find_cycle, has_branches, immediate_post_dominators, outgoing, roots,
)

TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "exploits"

_IMPORT_RE = re.compile(r"^(import\s+\S+|from\s+\S+\s+import\s+.+)$", re.MULTILINE)

_INDENT = "    "

# Container blocks: their templates mark where the Success-pin blocks (loop body /
# protected code) and the Failure-pin blocks go with these placeholder lines.
CONTAINER_BLOCKS = {"builder_loop", "builder_try_catch"}
_SLOT_BODY    = "# @@VF_BODY@@"
_SLOT_FAILURE = "# @@VF_FAILURE@@"


def _get_jinja_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        undefined=Undefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    # {{ VALUE | py }} → a Python string literal, safe for backslashes and quotes
    # (e.g. Windows paths like C:\Users\..., which break inside "{{ VALUE }}").
    env.filters["py"] = lambda value: repr(str(value))
    return env


def _resolve_shellcode(session: Session) -> None:
    """
    If PAYLOAD is selected, compile with GCC, XOR encode,
    and write SHELLCODE and DECODER_STUB variables to the session.
    """
    payload_name = session.get_option("PAYLOAD")
    if not payload_name:
        return

    print(f"[*] Compiling payload: {payload_name}")
    hex_shellcode = compile_payload(payload_name)
    raw = bytes.fromhex(hex_shellcode)

    _encoded, key, stub = encode_shellcode_file(raw)
    session.set_option("SHELLCODE",    hex_shellcode)
    session.set_option("XOR_KEY",      f"0x{key:02x}")
    session.set_option("DECODER_STUB", stub)


def _is_builder(session: Session) -> bool:
    """Returns True if the session uses a builder_* (0-Day) block."""
    return bool(session.active_exploit and
                session.active_exploit.name.startswith("builder_"))


def _is_macro(session: Session) -> bool:
    """Returns True if the session's active exploit is a macro (composite) block."""
    return bool(session.active_exploit and
                getattr(session.active_exploit, '_macro_def', None) is not None)


def _is_container(session: Session) -> bool:
    return bool(session.active_exploit and session.active_exploit.name in CONTAINER_BLOCKS)


def _render_template(session: Session, env: Environment,
                     uid: str = "", keep_slots: bool = False) -> str:
    """
    Render a single session template and return the code string.
    `uid` keeps a container's helper variables unique when containers nest;
    unless `keep_slots`, container placeholders are filled with `pass`.
    """
    if not session.active_exploit or not session.active_exploit.template:
        return ""  # macro blocks have no template
    tmpl_name = f"{session.active_exploit.template}.j2"
    try:
        tmpl = env.get_template(tmpl_name)
    except Exception as e:
        raise RuntimeError(f"Template not found: {tmpl_name} — {e}")
    rendered = tmpl.render(**session.to_dict(), VF_UID=uid)
    if keep_slots:
        return rendered
    return "\n".join(_fill_slots(rendered.splitlines(), [], []))


def _macro_graph(session: Session):
    from .macro import macro_to_graph   # imported here to avoid circular deps
    return macro_to_graph(session.active_exploit._macro_def)


def _expand_macros(sessions: List[Session]) -> List[Session]:
    """Expand any macro sessions into their constituent sub-sessions."""
    expanded = []
    for s in sessions:
        if _is_macro(s):
            expanded.extend(_macro_graph(s)[0])
        elif s.active_exploit is None or s.active_exploit.id == -1:
            # Defensive: an unset or otherwise-untagged macro placeholder
            # session — nothing usable to expand, drop it rather than
            # crash the render on a template-less block.
            continue
        else:
            expanded.append(s)
    return expanded


def _macros_have_branches(sessions: List[Session]) -> bool:
    return any(_is_macro(s) and has_branches(_macro_graph(s)[1]) for s in sessions)


# ─── Code layout helpers ──────────────────────────────────────────────────────

def _string_continuation_rows(code: str) -> Set[int]:
    """
    1-based line numbers that sit inside a multi-line string literal. Those
    lines are part of the string's value, so (de)indenting them would change it.
    """
    rows: Set[int] = set()
    fstring_start = getattr(tokenize, "FSTRING_START", None)   # Python 3.12+
    fstring_end   = getattr(tokenize, "FSTRING_END", None)
    open_fstrings: List[int] = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(code).readline):
            if tok.type == fstring_start:
                open_fstrings.append(tok.start[0])
            elif tok.type == fstring_end and open_fstrings:
                rows.update(range(open_fstrings.pop() + 1, tok.end[0] + 1))
            elif tok.type == tokenize.STRING and tok.end[0] > tok.start[0]:
                rows.update(range(tok.start[0] + 1, tok.end[0] + 1))
    except (tokenize.TokenError, SyntaxError):
        pass
    return rows


def _indent(lines: Sequence[str], prefix: str = _INDENT) -> List[str]:
    """Indent code lines, leaving blank lines and multi-line string contents alone."""
    keep = _string_continuation_rows("\n".join(lines) + "\n")
    return [line if (i in keep or not line.strip()) else prefix + line
            for i, line in enumerate(lines, 1)]


def _fill_slots(lines: Sequence[str], body: Sequence[str], failure: Sequence[str]) -> List[str]:
    """Replace container placeholders with code indented to the placeholder's level."""
    out: List[str] = []
    for line in lines:
        slot = line.strip()
        if slot in (_SLOT_BODY, _SLOT_FAILURE):
            code = body if slot == _SLOT_BODY else failure
            out += _indent(list(code) or ["pass"], line[:len(line) - len(line.lstrip())])
        else:
            out.append(line)
    return out


def _split_imports(rendered: str):
    """Split rendered code into (import lines, body lines without blank edges)."""
    import_lines: List[str] = []
    body_lines:   List[str] = []
    for line in rendered.splitlines():
        if _IMPORT_RE.match(line.strip()):
            import_lines.append(line)
        else:
            body_lines.append(line)
    while body_lines and not body_lines[0].strip():
        body_lines.pop(0)
    while body_lines and not body_lines[-1].strip():
        body_lines.pop()
    return import_lines, body_lines


def _stage_body(rendered: str) -> List[str]:
    """
    Body of a classic stage function: the module code of the template followed
    by the statements of its `if __name__ == "__main__":` block, which is where
    classic templates actually run their exploit.
    """
    lines = rendered.splitlines()
    keep = _string_continuation_rows(rendered + "\n")

    guard = next((i for i, l in enumerate(lines)
                  if l.startswith("if __name__") and (i + 1) not in keep), None)
    body = lines if guard is None else lines[:guard]
    body = [l for i, l in enumerate(body) if not (l.startswith("#!") and i == 0)]

    if guard is not None:
        main_rows = range(guard + 1, len(lines))
        first = next((lines[i] for i in main_rows if lines[i].strip()), "")
        depth = len(first) - len(first.lstrip())
        for i in main_rows:
            line = lines[i]
            if (i + 1) not in keep and line[:depth].strip() == "":
                line = line[depth:]
            body.append(line)

    while body and not body[-1].strip():
        body.pop()
    return body


def _label(name: str) -> str:
    """Block/macro name safe to embed in a single-line comment."""
    return " ".join(str(name).split())


def _section(name: str) -> str:
    label = _label(name)
    return f"# ── {label} {'─' * max(0, 55 - len(label))}"


# ─── Single block ──────────────────────────────────────────────────────────────

def generate_single(session: Session, out_path: Optional[str] = None) -> str:
    """Single mode: generates one exploit from one session."""
    if not session.active_exploit:
        raise RuntimeError("No active exploit in session.")

    if _is_macro(session):
        inner, edges = _macro_graph(session)
        if not inner:
            raise RuntimeError(
                f"Macro '{session.active_exploit.name}' has no valid inner blocks to generate."
            )
        return generate_chain(inner, out_path, edges)

    _resolve_shellcode(session)

    env = _get_jinja_env()
    rendered = _render_template(session, env)

    # Micro-block support (CTX)
    if "CTX" in rendered and "CTX = {}" not in rendered:
        rendered = "CTX = {}\n\n" + rendered

    OUTPUT_DIR.mkdir(exist_ok=True)
    if out_path is None:
        out_path = str(OUTPUT_DIR / f"{session.active_exploit.name}_exploit.py")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(rendered)

    print(f"[+] Exploit generated: {out_path}")
    return out_path


# ─── Chain ────────────────────────────────────────────────────────────────────

def _generate_builder_chain(sessions: List[Session], env: Environment) -> str:
    """
    Flat chain for builder_* blocks.
    - All import statements are collected, deduplicated, and placed at the top.
    - CTX = {} is declared once.
    - Block bodies are joined sequentially with section comments.
    """
    all_imports: list[str] = []
    all_bodies:  list[str] = []

    for session in sessions:
        _resolve_shellcode(session)
        import_lines, body_lines = _split_imports(_render_template(session, env))

        # Collect unique imports
        for imp in import_lines:
            if imp not in all_imports:
                all_imports.append(imp)

        all_bodies.append("\n" + _section(session.active_exploit.name))
        all_bodies.extend(body_lines)

    header = (
        "#!/usr/bin/env python3\n"
        "# ViperForge — 0-Day Builder Exploit (Auto-Generated)\n"
        f"# Blocks: {' → '.join(s.active_exploit.name for s in sessions if s.active_exploit)}\n\n"
    )

    imports_block = "\n".join(all_imports)
    ctx_decl      = "\nCTX = {}   # Shared context dictionary\n"
    body_block    = "\n".join(all_bodies)

    footer = (
        "\n\n# ── Entry point ─────────────────────────────────────────────────────────────\n"
        "if __name__ == '__main__':\n"
        "    pass  # Code above runs at module level — remove this block if needed\n"
    )

    return header + imports_block + ctx_decl + body_block + footer


def _stage_function(func_name: str, rendered: str) -> str:
    body = _indent(_stage_body(rendered)) or [_INDENT + "pass"]
    return f"\ndef {func_name}():\n    global CTX\n" + "\n".join(body) + "\n"


def _generate_classic_chain(sessions: List[Session], env: Environment) -> str:
    """
    Function-wrapped chain for classic exploit blocks.
    Each block becomes its own stage_N_name() function, called by main().
    """
    parts: List[str] = []

    header = (
        "#!/usr/bin/env python3\n"
        "# ViperForge — Chain Exploit (Auto-Generated)\n"
        f"# Modules: {' → '.join(s.active_exploit.name for s in sessions if s.active_exploit)}\n\n"
        "CTX = {}\n\n"
    )
    parts.append(header)

    func_names: List[str] = []

    for idx, session in enumerate(sessions):
        if not session.active_exploit:
            continue

        _resolve_shellcode(session)
        func_name = f"stage_{idx + 1}_{session.active_exploit.name}"
        func_names.append(func_name)
        parts.append(_stage_function(func_name, _render_template(session, env)))

    # Main chain runner
    main_calls = "\n".join(f"    {fn}()" for fn in func_names)
    main_block = (
        f"\ndef main():\n"
        f"    print('[*] ViperForge Chain — Starting {len(func_names)} stage(s)...')\n"
        f"{main_calls}\n"
        f"    print('[+] Chain complete.')\n\n"
        f"if __name__ == '__main__':\n"
        f"    main()\n"
    )
    parts.append(main_block)

    return "".join(parts)


class _FlowEmitter:
    """
    Builds a main() flow from a block graph. Builder blocks are inlined,
    classic blocks become stage functions called from the flow, and macros
    are emitted recursively from their own inner graph.

    A block whose failure pin is connected runs inside try/except. It counts
    as failed if it raises or sets CTX["_vf_branch"] = "failure" (the flag the
    builder_if_else / builder_try_catch blocks already use). The success and
    failure paths are emitted under an if/else and rejoin at the first block
    both paths lead to.
    """

    def __init__(self, env: Environment):
        self.env = env
        self.imports: List[str] = []
        self.stages:  List[str] = []
        self._stage_names: Dict[int, str] = {}
        self._containers = 0

    # ── public ──
    def render(self, sessions: List[Session], edges: List[Edge]) -> str:
        flow = self.emit_graph(sessions, edges)
        names = " → ".join(_label(s.active_exploit.name) for s in sessions if s.active_exploit)
        header = (
            "#!/usr/bin/env python3\n"
            "# ViperForge — Chain Exploit (Auto-Generated)\n"
            f"# Blocks: {names}\n\n"
        )
        main = (
            "\n\ndef main():\n"
            "    print('[*] ViperForge Chain — starting...')\n"
            + "\n".join(_indent(flow)) + "\n"
            "    print('[+] Chain complete.')\n\n\n"
            "if __name__ == '__main__':\n"
            "    main()\n"
        )
        return (header + "\n".join(self.imports)
                + "\n\nCTX = {}   # Shared context dictionary\n"
                + "".join(self.stages) + main)

    def emit_graph(self, sessions: List[Session], edges: List[Edge]) -> List[str]:
        count = len(sessions)
        cycle = find_cycle(count, edges)
        if cycle:
            loop = " → ".join(_label(sessions[i].active_exploit.name) for i in cycle)
            raise RuntimeError(
                f"Chain contains a loop ({loop}). Connections must not form a cycle — "
                f"use a builder_loop block for repetition."
            )
        succ, fail = outgoing(count, edges)
        joins = immediate_post_dominators(count, edges)

        lines: List[str] = []
        for root in roots(count, edges):
            lines += self._emit_path(sessions, succ, fail, joins, root, None)
        return lines

    # ── internals ──
    def _emit_path(self, sessions, succ, fail, joins, node, stop) -> List[str]:
        out: List[str] = []
        while node is not None and node != stop:
            session = sessions[node]
            name = session.active_exploit.name if session.active_exploit else "?"
            if _is_container(session):
                # Body runs to where the Failure path rejoins — or, without a
                # Failure connection, to the end of the enclosing path.
                join = stop if fail[node] is None else joins[node]
                body    = self._emit_path(sessions, succ, fail, joins, succ[node], join)
                failure = self._emit_path(sessions, succ, fail, joins, fail[node], join)
                out += ["", _section(name)] + self._container_code(session, body, failure)
                node = join
                continue

            code = self._node_code(session)

            if fail[node] is None:
                if code:
                    out += ["", _section(name)] + code
                node = succ[node]
                continue

            join = joins[node]
            ok_path  = self._emit_path(sessions, succ, fail, joins, succ[node], join)
            err_path = self._emit_path(sessions, succ, fail, joins, fail[node], join)
            out += self._branch(name, code, ok_path, err_path)
            node = join
        return out

    def _branch(self, name: str, code: List[str], ok_path: List[str], err_path: List[str]) -> List[str]:
        label = _label(name)
        lines = [
            "",
            _section(f"{label} [branch: success / failure]"),
            'CTX["_vf_branch"] = "success"',
            "try:",
            *(_indent(code) or [_INDENT + "pass"]),
            "except Exception as _vf_err:",
            _INDENT + 'CTX["_vf_branch"] = "failure"',
            _INDENT + f"print({f'[!] {label} failed:'!r}, _vf_err)",
        ]
        if err_path:
            lines.append('if CTX.get("_vf_branch") == "failure":')
            lines += _indent(err_path)
            if ok_path:
                lines.append("else:")
                lines += _indent(ok_path)
        elif ok_path:
            lines.append('if CTX.get("_vf_branch") != "failure":')
            lines += _indent(ok_path)
        return lines

    def _container_code(self, session: Session, body: List[str], failure: List[str]) -> List[str]:
        self._containers += 1
        _resolve_shellcode(session)
        rendered = _render_template(session, self.env, uid=f"_{self._containers}", keep_slots=True)
        import_lines, code = _split_imports(rendered)
        for imp in import_lines:
            if imp not in self.imports:
                self.imports.append(imp)
        return _fill_slots(code, body, failure)

    def _node_code(self, session: Session) -> List[str]:
        if _is_macro(session):
            inner, inner_edges = _macro_graph(session)
            return self.emit_graph(inner, inner_edges)
        if session.active_exploit is None or session.active_exploit.id == -1:
            return []

        if _is_builder(session):
            _resolve_shellcode(session)
            import_lines, body = _split_imports(_render_template(session, self.env))
            for imp in import_lines:
                if imp not in self.imports:
                    self.imports.append(imp)
            return body

        # Classic: one stage function per block, reused if the flow visits it twice
        key = id(session)
        if key not in self._stage_names:
            _resolve_shellcode(session)
            func_name = f"stage_{len(self._stage_names) + 1}_{session.active_exploit.name}"
            self._stage_names[key] = func_name
            self.stages.append(_stage_function(func_name, _render_template(session, self.env)))
        return [f"{self._stage_names[key]}()"]


def _render_chain(sessions: List[Session], edges: Optional[List[Edge]], env: Environment) -> str:
    # No graph given (CLI, API callers): the list itself is the chain.
    if edges is None:
        edges = [(i, i + 1, SUCCESS) for i in range(len(sessions) - 1)]
    edges = list(edges)
    expanded = _expand_macros(sessions)
    if not expanded:
        raise RuntimeError("No usable blocks in chain.")

    has_builder = any(_is_builder(s) for s in expanded)
    has_classic = any(not _is_builder(s) for s in expanded)

    if (has_branches(edges) or _macros_have_branches(sessions)
            or (has_builder and has_classic) or any(_is_container(s) for s in expanded)):
        return _FlowEmitter(env).render(sessions, edges)
    if has_builder:
        return _generate_builder_chain(expanded, env)
    return _generate_classic_chain(expanded, env)


def generate_chain(sessions: List[Session], out_path: Optional[str] = None,
                   edges: Optional[List[Edge]] = None) -> str:
    """
    Chain mode: generates a single exploit script from multiple sessions.

    `edges` are the canvas connections as (src_index, dst_index, port_type)
    tuples over `sessions`; None means `sessions` is one linear chain.
    Without failure connections or container blocks the chain is linear:
    flat for builder_* blocks, function-wrapped for classic ones. Failure
    connections, macros containing them, loop/try_catch containers and mixed
    builder/classic chains are generated as a main() flow. Macro blocks are
    expanded inline.
    """
    if not sessions:
        raise RuntimeError("No sessions in chain.")

    env = _get_jinja_env()
    code = _render_chain(sessions, edges, env)

    # Determine output filename
    if out_path is None:
        chain_name = "_".join(
            s.active_exploit.name for s in _expand_macros(sessions) if s.active_exploit
        )
        out_path = str(OUTPUT_DIR / f"chain_{chain_name}_exploit.py")

    OUTPUT_DIR.mkdir(exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(code)

    print(f"[+] Chain exploit generated: {out_path}")
    return out_path


# ─── Preview ──────────────────────────────────────────────────────────────────

def preview_single(session: Session) -> str:
    """For GUI live preview: returns rendered string without writing to file."""
    if not session.active_exploit:
        return "# No exploit selected."

    if _is_macro(session):
        inner, edges = _macro_graph(session)
        if not inner:
            return f"# Macro '{session.active_exploit.name}' has no valid inner blocks."
        return preview_chain(inner, edges)

    env = _get_jinja_env()
    tmpl_name = f"{session.active_exploit.template}.j2"
    try:
        env.get_template(tmpl_name)
    except Exception:
        return f"# Template not found: {tmpl_name}"

    rendered = _render_template(session, env)
    if "CTX" in rendered and "CTX = {}" not in rendered:
        rendered = "CTX = {}\n\n" + rendered
    return rendered


def preview_chain(sessions: List[Session], edges: Optional[List[Edge]] = None) -> str:
    """For GUI chain preview: returns the full chain code without writing to file."""
    if not sessions:
        return "# No blocks in chain."

    try:
        return _render_chain(sessions, edges, _get_jinja_env())
    except Exception as e:
        return f"# Preview error: {e}"
