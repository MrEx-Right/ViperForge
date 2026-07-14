"""
ViperForge v2.0 — C Payload Compiler
Python equivalent of Go's compiler.go.
Compiles .c source into raw shellcode using GCC.
"""

import os
import subprocess
import tempfile
from pathlib import Path

PAYLOADS_DIR = Path(__file__).parent.parent / "templates" / "payloads"


def compile_payload(payload_name: str) -> str:
    """
    Compiles the C payload source and returns the shellcode as a hex string.
    Raises RuntimeError on failure.
    """
    src_path = PAYLOADS_DIR / f"{payload_name}.c"
    if not src_path.exists():
        raise RuntimeError(f"Payload source not found: {src_path}")

    with tempfile.TemporaryDirectory() as tmpdir:
        obj_path  = os.path.join(tmpdir, f"{payload_name}.o")
        bin_path  = os.path.join(tmpdir, f"{payload_name}.bin")

        # Compile: gcc -m32 -fno-stack-protector -z execstack -o obj.o src.c
        gcc_cmd = [
            "gcc", "-m32",
            "-fno-stack-protector",
            "-z", "execstack",
            "-nostdlib", "-static",
            "-o", obj_path,
            str(src_path),
        ]
        result = subprocess.run(gcc_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"GCC failed:\n{result.stderr}")

        # Extract raw text section
        objcopy_cmd = [
            "objcopy",
            "--only-section=.text",
            "--output-target=binary",
            obj_path, bin_path,
        ]
        result = subprocess.run(objcopy_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"objcopy failed:\n{result.stderr}")

        with open(bin_path, "rb") as f:
            raw = f.read()

    # Returns in hex string format (embedded into the exploit template)
    return raw.hex()
