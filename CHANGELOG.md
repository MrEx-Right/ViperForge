# Changelog

All notable changes to **ViperForge** will be documented in this file.

This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) and the [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format.

---

## [Unreleased]

> Changes staged for the next release will be listed here.

---

## [1.1.0-beta] — 2026-05-23

### Added
- **Automatic Pre-Flight Dependency Checking:** Generated Python exploit scripts now include a built-in pre-flight check logic that automatically verifies the existence of required modules (`pwntools`, `requests`, `impacket`) via the `dependency_controller`. Missing dependencies gracefully abort the exploit execution with a user-friendly error message, ensuring the target environment is ready before attempting execution.
- Added `PostGenerateHook` in `core/templater.go` to intercept and dynamically modify exploit scripts right after generation without altering template files directly.

---

## [1.0.0-beta] — 2026-05-09

> 🐍 **Initial public beta release of ViperForge.**  
> *Red Team Exploit Factory — wizard-driven, modular, evasion-ready.*

### Added

#### Core Framework
- **Interactive readline shell** (`console/shell.go`) with persistent command history (`viperforge_history.tmp`), `^C` interrupt handling, and `EOF` exit handling via `github.com/chzyer/readline`.
- **Two-stage nested menu system**: top-level category selection → per-category exploit listing, with `[0]/back` navigation and `clear`/`exit` global commands.
- **Interactive configuration wizard** (`runWizard`): per-option prompts with inline descriptions and default values displayed in bracket notation `[default]`.
- **Exploit execution preview**: human-readable attack flow summary rendered before script generation, tailored per exploit module.
- **Session state management** (`core/session.go`): active exploit tracking and key-value option storage across wizard interactions.
- **Go template engine** (`core/templater.go`): renders Python exploit scripts from `.tmpl` files using session options; writes output to `output/` directory.

#### Exploit Registry — 18 Modules (`core/registry.go`)

| Category | Modules Added |
|---|---|
| **Binary Exploitation** | `bof_remote`, `bof_local`, `rop_chain`, `format_string`, `heap_uaf` |
| **Web Exploitation** | `web_lfi`, `web_sqli`, `web_ssti`, `web_cmd_exec`, `web_xxe`, `web_deserialization`, `web_ssrf` |
| **Privilege Escalation** | `privesc_suid`, `privesc_sudo_token` |
| **Network Attacks** | `network_ftp_anon`, `network_smb_relay` |
| **Cryptography** | `crypto_padding_oracle` |
| **Active Directory** | `ad_kerberoasting` |

#### Payload Pipeline (`core/compiler.go`)
- **Automated C payload compilation**: invokes `gcc -m32 -fno-stack-protector` to compile C source files in `templates/payloads/`.
- **Shellcode extraction**: uses `objcopy -O binary -j .text` to strip ELF headers and extract raw `.text` section bytes.
- **Hex formatting**: shellcode bytes serialized as Python-compatible `\xNN` escape sequences for direct embedding into generated exploit scripts.
- Temporary `.o` and `.bin` artifacts are automatically cleaned up after compilation.

#### Polymorphic XOR Encoder (`core/encoder.go`)
- **Cryptographically random 4-byte XOR key** generation via `crypto/rand` (with deterministic fallback on failure).
- **Block-level XOR encoding**: shellcode padded to 4-byte alignment with `0x90` NOP bytes and encoded in 4-byte chunks.
- **JMP-CALL-POP decoder stub** prepended to encoded payload — achieves position-independent, self-decrypting shellcode with no hardcoded addresses.
- Ensures no two compiled payloads share identical byte signatures.

#### C Payload Sources (`templates/payloads/`)
- **`execve.c`** — Linux `execve("/bin/sh", NULL, NULL)` shellcode in 32-bit x86 position-independent C.
- **`win_exec.c`** — Windows shellcode leveraging PEB (Process Environment Block) parsing and API hashing to dynamically resolve `WinExec` and `ExitProcess` without import tables — evades static IAT analysis.

#### Python Exploit Templates (`templates/exploits/`)
- **18 production-ready Python exploit templates** using `pwntools` and/or `requests` library patterns:
  - `bof_remote.tmpl` — TCP socket exploit with NOP sled + shellcode payload
  - `bof_local.tmpl` — Local binary exploit via subprocess argument injection
  - `rop_chain.tmpl` — libc-based ROP chain with dynamic address calculation
  - `format_string.tmpl` — `%n`-based arbitrary write via format string
  - `heap_uaf.tmpl` — Use-After-Free heap manipulation script
  - `web_lfi.tmpl` — LFI log poisoning via malicious User-Agent injection
  - `web_sqli.tmpl` — Blind SQLi with `INTO OUTFILE` web shell deployment
  - `web_ssti.tmpl` — Jinja2 SSTI payload delivery and output extraction
  - `web_cmd_exec.tmpl` — WAF-evasive Base64-encoded command injection (GET/POST)
  - `web_xxe.tmpl` — XXE payload for arbitrary file read
  - `web_deserialization.tmpl` — Python Pickle deserialization RCE via cookie injection
  - `web_ssrf.tmpl` — SSRF-based internal port scanner
  - `privesc_suid.tmpl` — PATH hijacking exploit script for SUID binaries
  - `privesc_sudo_token.tmpl` — Sudo token hijacking via `/proc/[pid]/mem` write
  - `network_ftp_anon.tmpl` — FTP anonymous login + payload upload automation
  - `network_smb_relay.tmpl` — Wrapper script for SMB relay attack orchestration
  - `crypto_padding_oracle.tmpl` — Block-by-block CBC padding oracle decryption
  - `ad_kerberoasting.tmpl` — Impacket-based Kerberoasting with auto hash output

#### Evasion Techniques
- **Randomized NOP sled generation** in BOF templates — variable-length, non-static padding.
- **Base64-encoded command injection** payloads in `web_cmd_exec` to bypass WAF pattern matching.
- **`/dev/shm`-based payload staging** in binary exploitation templates — avoids disk-based EDR detection.
- **Dynamic API resolution** in `win_exec.c` via PEB walking — no hardcoded function imports.

