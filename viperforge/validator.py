"""
ViperForge v2.0 — Chain Validator
Analyzes the block chain and returns a list of warning/error messages
before code generation. Prevents invalid combinations from silently
producing broken exploits.
"""

from typing import List, Tuple

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
    "builder_socket":    "SOCK_NAME",
    "builder_recv":      "RECV_VAR",
    "builder_recv_until":"RECV_VAR",
    "builder_http_req":  "RESP_VAR",
    "builder_b64encode": "OUTPUT_VAR",
    "builder_b64decode": "OUTPUT_VAR",
    "builder_urlencode": "OUTPUT_VAR",
    "builder_hex":       "OUTPUT_VAR",
    "builder_xor":       "OUTPUT_VAR",
    "builder_read_file": "OUTPUT_VAR",
    "builder_pack":      "VAR_NAME",
    "builder_p32_p64":   "OUTPUT_VAR",
}

# Severity levels
ERROR   = "error"
WARNING = "warning"
INFO    = "info"


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


def validate_chain(blocks, sessions) -> List[ValidationIssue]:
    """
    Validate a chain of (BlockItem, Session) pairs.
    Returns a list of ValidationIssue objects.
    """
    issues: List[ValidationIssue] = []

    # Build ordered list of (name, session) tuples
    ordered = list(zip(blocks, sessions))
    if not ordered:
        return []

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
            "Mixing '0-Day Builder' blocks with classic exploit blocks in the same "
            "chain may produce unexpected results. Consider using only one type."
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
            try:
                eval(val_str)   # safe for hex literals and simple integers
            except Exception:
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

    # Warn if only one block but chain mode would be triggered
    if len(ordered) == 1 and has_builder:
        issues.append(ValidationIssue(
            INFO, "Chain",
            "Only one block in the chain. Add more blocks to build a complete exploit flow."
        ))

    return issues
