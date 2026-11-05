"""
ViperForge — Chain Validator
Analyzes the block chain and returns a list of warning/error messages
before code generation. Prevents invalid combinations from silently
producing broken exploits.
"""

import ast
from typing import List, Optional, Tuple

from .graph import SUCCESS, Edge, find_cycle, outgoing

# Builder blocks that NEED a socket in CTX before them
_SOCKET_CONSUMERS = {
    "builder_send",
    "builder_recv",
    "builder_recv_until",
}

# Builder blocks that PRODUCE a socket into CTX
_SOCKET_PRODUCERS = {
    "builder_socket",
}

# Builder blocks that READ from a CTX variable (input_var or similar)
_CTX_READERS = {
    "builder_send":      "PAYLOAD_VAR",
    "builder_b64encode": "INPUT_VAR",
    "builder_b64decode": "INPUT_VAR",
    "builder_urlencode": "INPUT_VAR",
    "builder_hex":       "INPUT_VAR",
    "builder_xor":       "INPUT_VAR",
    "builder_write_file":"INPUT_VAR",
    "builder_print":     "VAR_NAME",
}

# Builder blocks that WRITE into a CTX variable (output_var or similar)
_CTX_WRITERS = {
    "builder_socket":       "SOCK_NAME",
    "builder_recv":         "RECV_VAR",
    "builder_recv_until":   "RECV_VAR",
    "builder_http_req":     "RESP_VAR",
    "builder_b64encode":    "OUTPUT_VAR",
    "builder_b64decode":    "OUTPUT_VAR",
    "builder_urlencode":    "OUTPUT_VAR",
    "builder_hex":          "OUTPUT_VAR",
    "builder_xor":          "OUTPUT_VAR",
    "builder_read_file":    "OUTPUT_VAR",
    "builder_pack":         "VAR_NAME",
    "builder_p32_p64":      "OUTPUT_VAR",
    "builder_variable_set": "VAR_NAME",
    "builder_loop":         "ITERATOR_VAR",
}

# Container blocks: the blocks on their Success pin are the loop body / protected code
_CONTAINER_BODY = {
    "builder_loop":      "loop body",
    "builder_try_catch": "protected code",
}

# Severity levels
ERROR   = "error"
WARNING = "warning"
INFO    = "info"


# Node types allowed in a VALUE expression: literals combined with arithmetic /
# bitwise operators (e.g. "0xdeadbeef", "0x41414141 + 8", "1 << 16").
# Anything else (names, calls, attribute access) is rejected without evaluation,
# so a crafted workspace/macro file can't execute code during validation.
_VALUE_NODES = (
    ast.Expression, ast.Constant, ast.BinOp, ast.UnaryOp,
    ast.Add, ast.Sub, ast.Mult, ast.FloorDiv, ast.Mod,
    ast.LShift, ast.RShift, ast.BitOr, ast.BitAnd, ast.BitXor,
    ast.USub, ast.UAdd, ast.Invert,
)


def _is_literal_expr(text: str) -> bool:
    try:
        tree = ast.parse(text.strip(), mode="eval")
    except SyntaxError:
        return False
    if not all(isinstance(n, _VALUE_NODES) for n in ast.walk(tree)):
        return False
    try:
        eval(compile(tree, "<VALUE>", "eval"), {"__builtins__": {}}, {})
    except Exception:
        return False
    return True


def _get_opt(session, key: str, default: str = "") -> str:
    v = session.get_option(key)
    return v if v else default


class ValidationIssue:
    def __init__(self, severity: str, block_name: str, message: str):
        self.severity   = severity   # "error" | "warning" | "info"
        self.block_name = block_name
        self.message    = message

    def __str__(self) -> str:
        icon = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}.get(self.severity, "•")
        return f"{icon}  [{self.block_name}]  {self.message}"


def _expand_macro_sessions(sessions) -> list:
    """Macro blocks are validated through the blocks they contain."""
    from .macro import macro_to_sessions   # imported here to avoid circular deps
    expanded = []
    for s in sessions:
        macro_def = getattr(s.active_exploit, "_macro_def", None) if s.active_exploit else None
        if macro_def is not None:
            expanded.extend(macro_to_sessions(macro_def))
        else:
            expanded.append(s)
    return expanded


def validate_chain(blocks, sessions, edges: Optional[List[Edge]] = None) -> List[ValidationIssue]:
    """
    Validate a chain of (BlockItem, Session) pairs in chain order.
    `edges` are the connections as (src_index, dst_index, port_type) over `sessions`.
    Returns a list of ValidationIssue objects.
    """
    issues: List[ValidationIssue] = []
    if not sessions:
        return []

    # ── Connections must not loop back — generated code runs top to bottom ──
    cycle = find_cycle(len(sessions), edges or [])
    if cycle:
        names = " → ".join(
            sessions[i].active_exploit.name if sessions[i].active_exploit else f"Block #{i+1}"
            for i in cycle
        )
        issues.append(ValidationIssue(
            ERROR, "Chain",
            f"Connections form a loop ({names}). Remove one connection — "
            f"use a 'builder_loop' block for repetition."
        ))

    # ── Containers need something on their Success pin to wrap ──────────
    # Without a graph, the session list is one linear chain.
    graph_edges = edges if edges is not None else [
        (i, i + 1, SUCCESS) for i in range(len(sessions) - 1)
    ]
    succ, _fail = outgoing(len(sessions), graph_edges)
    for idx, session in enumerate(sessions):
        name = session.active_exploit.name if session.active_exploit else ""
        if name in _CONTAINER_BODY and succ[idx] is None:
            issues.append(ValidationIssue(
                WARNING, name,
                f"Nothing is connected to the Success pin, so the {_CONTAINER_BODY[name]} "
                f"is empty. Connect the blocks it should wrap to its Success pin."
            ))

    # Build ordered list of (block, session) tuples, macros expanded
    sessions = _expand_macro_sessions(sessions)
    ordered = list(zip([None] * len(sessions), sessions))
    if not ordered:
        return issues

    # Track what's been written to CTX so far
    ctx_vars: dict[str, str] = {}          # var_name -> "written by block_name"
    socket_names_available: set[str] = set()

    has_builder = any(
        s.active_exploit and s.active_exploit.name.startswith("builder_")
        for _, s in ordered
    )
    has_classic = any(
        s.active_exploit and not s.active_exploit.name.startswith("builder_")
        for _, s in ordered
    )

    # Warn about mixing builder + classic
    if has_builder and has_classic:
        issues.append(ValidationIssue(
            WARNING, "Chain",
            "Mixing '0-Day Builder' blocks with classic exploit blocks: builder blocks run "
            "inline and classic blocks as separate stage functions, so they only share "
            "data through CTX, not through local variables."
        ))

    for idx, (block, session) in enumerate(ordered):
        if not session.active_exploit:
            issues.append(ValidationIssue(ERROR, f"Block #{idx+1}", "No exploit assigned to this block."))
            continue

        name = session.active_exploit.name

        # ── builder_custom: ensure CODE is not empty ──────────────────────
        if name == "builder_custom":
            code = _get_opt(session, "CODE")
            if not code.strip():
                issues.append(ValidationIssue(
                    ERROR, name, "CODE field is empty — this block will do nothing."
                ))

        # ── Socket consumers: check that a socket was produced before ─────
        if name in _SOCKET_CONSUMERS:
            sock_name = _get_opt(session, "SOCK_NAME", "sock")
            if sock_name not in socket_names_available:
                issues.append(ValidationIssue(
                    ERROR, name,
                    f"No 'builder_socket' block that creates '{sock_name}' was found "
                    f"before this block. Add a 'builder_socket' block first."
                ))

        # ── Socket producers: register socket name ────────────────────────
        if name in _SOCKET_PRODUCERS:
            sock_name = _get_opt(session, "SOCK_NAME", "sock")
            socket_names_available.add(sock_name)

        # ── CTX readers: check that input_var was written before ──────────
        if name in _CTX_READERS:
            input_key = _CTX_READERS[name]
            input_var = _get_opt(session, input_key)
            if input_var and input_var not in ctx_vars:
                # It might be a raw Python variable, so only warn
                issues.append(ValidationIssue(
                    WARNING, name,
                    f"'{input_var}' has not been produced by a previous block. "
                    f"Make sure it's defined earlier in the chain or it's a global variable."
                ))

        # ── CTX writers: register output_var ─────────────────────────────
        if name in _CTX_WRITERS:
            out_key = _CTX_WRITERS[name]
            out_var = _get_opt(session, out_key)
            if out_var:
                ctx_vars[out_var] = name

        # ── builder_pack / builder_p32_p64: check VALUE is parseable ─────
        if name in ("builder_pack", "builder_p32_p64"):
            val_str = _get_opt(session, "VALUE", "0")
            if not _is_literal_expr(val_str):
                issues.append(ValidationIssue(
                    ERROR, name,
                    f"VALUE '{val_str}' cannot be parsed as a Python integer/hex. "
                    f"Use format like '0xdeadbeef' or '100'."
                ))

        # ── builder_sleep: ensure SECONDS is a valid number ───────────────
        if name == "builder_sleep":
            sec_str = _get_opt(session, "SECONDS", "1")
            try:
                float(sec_str)
            except ValueError:
                issues.append(ValidationIssue(
                    ERROR, name,
                    f"SECONDS '{sec_str}' is not a valid number."
                ))

        # ── builder_http_req: check URL format ───────────────────────────
        if name == "builder_http_req":
            url = _get_opt(session, "URL", "")
            if not url.startswith(("http://", "https://")):
                issues.append(ValidationIssue(
                    WARNING, name,
                    f"URL '{url}' does not start with http:// or https://. "
                    f"The request may fail."
                ))

        # ── builder_read_file: check path is not empty ───────────────────
        if name == "builder_read_file":
            fpath = _get_opt(session, "FILE_PATH", "")
            if not fpath.strip():
                issues.append(ValidationIssue(
                    ERROR, name, "FILE_PATH is empty."
                ))

        # ── builder_write_file: check path is not empty ──────────────────
        if name == "builder_write_file":
            fpath = _get_opt(session, "FILE_PATH", "")
            if not fpath.strip():
                issues.append(ValidationIssue(
                    ERROR, name, "FILE_PATH is empty."
                ))

        # ── builder_if_else: check VAR_NAME is not empty ─────────────────
        if name == "builder_if_else":
            var = _get_opt(session, "VAR_NAME", "")
            if not var.strip():
                issues.append(ValidationIssue(
                    ERROR, name, "VAR_NAME is empty — condition has nothing to evaluate."
                ))
            op = _get_opt(session, "OPERATOR", "==")
            if op not in ("==", "!=", "contains", ">", "<"):
                issues.append(ValidationIssue(
                    WARNING, name,
                    f"OPERATOR '{op}' is not one of ==, !=, contains, >, <."
                ))

        # ── builder_loop: validate by mode ───────────────────────────────
        if name == "builder_loop":
            mode = _get_opt(session, "MODE", "LIST")
            if mode == "FILE":
                fpath = _get_opt(session, "FILE_PATH", "")
                if not fpath.strip():
                    issues.append(ValidationIssue(
                        ERROR, name, "FILE_PATH is empty (MODE=FILE requires a path)."
                    ))
            elif mode == "RANGE":
                for key in ("RANGE_START", "RANGE_END"):
                    val = _get_opt(session, key, "0")
                    try:
                        int(val)
                    except ValueError:
                        issues.append(ValidationIssue(
                            ERROR, name, f"{key} '{val}' is not a valid integer."
                        ))

        # ── builder_try_catch: validate retry count ──────────────────────
        if name == "builder_try_catch":
            action = _get_opt(session, "FALLBACK_ACTION", "LOG")
            if action == "RETRY":
                rc = _get_opt(session, "RETRY_COUNT", "3")
                try:
                    n = int(rc)
                    if n < 1:
                        raise ValueError
                except ValueError:
                    issues.append(ValidationIssue(
                        ERROR, name,
                        f"RETRY_COUNT '{rc}' must be a positive integer."
                    ))

        # ── builder_variable_set: validate by mode ───────────────────────
        if name == "builder_variable_set":
            vmode = _get_opt(session, "MODE", "STATIC")
            vname = _get_opt(session, "VAR_NAME", "")
            if not vname.strip():
                issues.append(ValidationIssue(
                    ERROR, name, "VAR_NAME is empty — nothing to set."
                ))
            if vmode == "REGEX":
                pat = _get_opt(session, "REGEX_PATTERN", "")
                if not pat.strip():
                    issues.append(ValidationIssue(
                        ERROR, name,
                        "REGEX_PATTERN is empty (MODE=REGEX requires a pattern)."
                    ))
                src_var = _get_opt(session, "SOURCE_VAR", "")
                if src_var and src_var not in ctx_vars:
                    issues.append(ValidationIssue(
                        WARNING, name,
                        f"SOURCE_VAR '{src_var}' has not been produced by a previous block."
                    ))

    # Warn if only one block but chain mode would be triggered
    if len(ordered) == 1 and has_builder:
        issues.append(ValidationIssue(
            INFO, "Chain",
            "Only one block in the chain. Add more blocks to build a complete exploit flow."
        ))

    return issues
