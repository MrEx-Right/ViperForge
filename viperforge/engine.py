"""
ViperForge v2.0 — Exploit Engine
Generates Python exploits from block chain or single session using Jinja2 templates.

Chain modes:
  - "builder_*" blocks  → flat sequential code (CTX shared dict, imports deduped)
  - Classic blocks      → each wrapped in its own function, called by main()
"""

import re
import os
from pathlib import Path
from typing import List, Optional
from jinja2 import Environment, FileSystemLoader, Undefined

from .session import Session
from .compiler import compile_payload
from .encoder import encode_shellcode_file

TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "exploits"
OUTPUT_DIR    = Path("output")

_IMPORT_RE = re.compile(r"^(import\s+\S+|from\s+\S+\s+import\s+.+)$", re.MULTILINE)


def _get_jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        undefined=Undefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )


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


def _render_template(session: Session, env: Environment) -> str:
    """Render a single session template and return the code string."""
    tmpl_name = f"{session.active_exploit.template}.j2"
    try:
        tmpl = env.get_template(tmpl_name)
    except Exception as e:
        raise RuntimeError(f"Template not found: {tmpl_name} — {e}")
    return tmpl.render(**session.to_dict())


# ─── Single block ──────────────────────────────────────────────────────────────

def generate_single(session: Session, out_path: Optional[str] = None) -> str:
    """Single mode: generates one exploit from one session."""
    if not session.active_exploit:
        raise RuntimeError("No active exploit in session.")

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
        rendered = _render_template(session, env)
        lines = rendered.splitlines()

        import_lines = []
        body_lines   = []
        for line in lines:
            if _IMPORT_RE.match(line.strip()):
                import_lines.append(line)
            else:
                body_lines.append(line)

        # Collect unique imports
        for imp in import_lines:
            if imp not in all_imports:
                all_imports.append(imp)

        # Trim empty leading/trailing lines from body
        while body_lines and not body_lines[0].strip():
            body_lines.pop(0)
        while body_lines and not body_lines[-1].strip():
            body_lines.pop()

        block_name = session.active_exploit.name
        all_bodies.append(f"\n# ── {block_name} {'─' * max(0, 55 - len(block_name))}")
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
        rendered = _render_template(session, env)

        func_name = f"stage_{idx + 1}_{session.active_exploit.name}"
        func_names.append(func_name)

        # Wrap body (skip __main__ block)
        lines = rendered.splitlines()
        body_lines = []
        skip_main = False
        for line in lines:
            if line.startswith("if __name__"):
                skip_main = True
            if not skip_main:
                body_lines.append("    " + line if line.strip() else line)

        func_block = f"\ndef {func_name}():\n    global CTX\n" + "\n".join(body_lines) + "\n"
        parts.append(func_block)

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


def generate_chain(sessions: List[Session], out_path: Optional[str] = None) -> str:
    """
    Chain mode: generates a single exploit script from multiple sessions.
    Automatically selects flat-mode (builder_*) or function-wrap mode (classic).
    Mixed chains get a hybrid treatment: builders run first as flat, classics as functions.
    """
    if not sessions:
        raise RuntimeError("No sessions in chain.")

    env = _get_jinja_env()

    builder_sessions = [s for s in sessions if _is_builder(s)]
    classic_sessions = [s for s in sessions if not _is_builder(s)]

    # Determine output filename
    if out_path is None:
        OUTPUT_DIR.mkdir(exist_ok=True)
        chain_name = "_".join(
            s.active_exploit.name for s in sessions if s.active_exploit
        )
        out_path = str(OUTPUT_DIR / f"chain_{chain_name}_exploit.py")

    if builder_sessions and not classic_sessions:
        # Pure builder chain — flat sequential
        code = _generate_builder_chain(sessions, env)

    elif classic_sessions and not builder_sessions:
        # Pure classic chain — function wrapped
        code = _generate_classic_chain(sessions, env)

    else:
        # Mixed chain: flat builders first, then classic stages
        builder_code = _generate_builder_chain(builder_sessions, env)
        classic_code = _generate_classic_chain(classic_sessions, env)

        code = (
            "#!/usr/bin/env python3\n"
            "# ViperForge — HYBRID Chain Exploit (Auto-Generated)\n\n"
            "# ═══════════════ BUILDER BLOCKS (flat) ════════════════════\n"
            + "\n".join(builder_code.splitlines()[3:]) +   # skip duplicate shebang
            "\n\n# ═══════════════ CLASSIC STAGES (functions) ═══════════\n"
            + "\n".join(classic_code.splitlines()[3:])
        )

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

    env = _get_jinja_env()
    tmpl_name = f"{session.active_exploit.template}.j2"
    try:
        tmpl = env.get_template(tmpl_name)
    except Exception:
        return f"# Template not found: {tmpl_name}"

    context = session.to_dict()
    rendered = tmpl.render(**context)
    if "CTX" in rendered and "CTX = {}" not in rendered:
        rendered = "CTX = {}\n\n" + rendered
    return rendered


def preview_chain(sessions: List[Session]) -> str:
    """For GUI chain preview: returns the full chain code without writing to file."""
    if not sessions:
        return "# No blocks in chain."

    env = _get_jinja_env()

    builder_sessions = [s for s in sessions if _is_builder(s)]
    classic_sessions = [s for s in sessions if not _is_builder(s)]

    try:
        if builder_sessions and not classic_sessions:
            return _generate_builder_chain(sessions, env)
        elif classic_sessions and not builder_sessions:
            return _generate_classic_chain(sessions, env)
        else:
            b = _generate_builder_chain(builder_sessions, env)
            c = _generate_classic_chain(classic_sessions, env)
            return (
                "# HYBRID CHAIN\n\n"
                "# ── Builder Blocks ──\n" + b +
                "\n\n# ── Classic Stages ──\n" + c
            )
    except Exception as e:
        return f"# Preview error: {e}"
