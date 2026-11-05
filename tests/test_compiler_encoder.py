import ast

import pytest

from viperforge import compiler
from viperforge.encoder import encode_shellcode_file, xor_encode


def test_missing_payload_source():
    with pytest.raises(RuntimeError, match="Payload source not found"):
        compiler.compile_payload("does_not_exist")


@pytest.mark.parametrize("missing", ["gcc", "objcopy"])
def test_missing_toolchain_gives_actionable_error(monkeypatch, missing):
    monkeypatch.setattr(compiler.shutil, "which",
                        lambda tool: None if tool == missing else f"/usr/bin/{tool}")
    with pytest.raises(RuntimeError, match=f"'{missing}' was not found on PATH"):
        compiler.compile_payload("execve")


def test_xor_roundtrip():
    data = bytes(range(256))
    assert xor_encode(xor_encode(data, 0x5A), 0x5A) == data


def test_encode_shellcode_file():
    raw = b"\x31\xc0\x50\x68//sh"
    encoded, key, stub = encode_shellcode_file(raw)
    assert key != 0
    assert xor_encode(encoded, key) == raw
    assert f"_KEY   = 0x{key:02x}" in stub
    ast.parse(stub)
