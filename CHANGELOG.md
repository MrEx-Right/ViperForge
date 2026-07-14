# Changelog

All notable changes to **ViperForge** will be documented in this file.

This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) and the [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format.

---

## [2.0.0-beta] — 2026-07-14

> 🐍 **ViperForge v2.0 — Full Python rewrite with a visual block-based exploit builder.**  
> *The entire framework has been rewritten from Go to Python. A node-based GUI, a rebuilt CLI, an expanded exploit registry, and a modular 0-Day Builder system.*

---

### ⚠️ Breaking Changes

- The full codebase has been rewritten from **Go → Python**. All previous Go binaries (`shell.go`, `compiler.go`, `encoder.go`, `templater.go`, `registry.go`, `session.go`) are replaced by their Python equivalents.
- Exploit templates have been migrated from `.tmpl` (Go text/template) → `.j2` (Jinja2). Old `.tmpl` files are kept alongside the new `.j2` files but are no longer the active templates.
- The entry point is now `viperforge.py` instead of a compiled Go binary.

---

### Added

#### GUI — Visual Block Exploit Builder (`viperforge/gui/`)

A fully new **PyQt6 / PyQt5** graphical interface for building exploit chains visually.

- **`MainWindow`** — Three-pane layout: Block Palette (left) · Canvas (center) · Param + Preview (right).
- **`ExploitCanvas`** (`canvas.py`) — `QGraphicsView`-based drag-and-drop canvas:
  - Blocks are freely draggable and repositioned anywhere on the canvas.
  - Dot-grid background with real-time rendering.
  - Scroll-to-zoom and middle-mouse-button panning.
  - `Delete` / `Backspace` key support to remove selected blocks or connectors.
  - `get_chain_order()` — topological sort of connected blocks for correct chain ordering.
  - Workspace serialization: `to_dict()` / `from_dict()` for JSON save/load.
- **`BlockItem`** (`block_item.py`) — `QGraphicsItem` subclass representing each exploit block:
  - Category color accent line, icon, title, description, and up to 3 inline parameter rows.
  - Hover glow and selection highlight effects.
  - Bottom connector button (`▼`) for chaining blocks together.
  - Right-click context menu: **Edit**, **Replace with another block** (sub-menu by category), **Delete**.
  - `change_exploit()` — swap a block's exploit module in-place without removing it from the canvas.
- **`ConnectorItem`** (`connector.py`) — Arrow line connecting two blocks, automatically updates position when blocks are moved.
- **`BlockPalette`** (`block_palette.py`) — Left sidebar with all available exploit modules:
  - Categorized expandable/collapsible sections with category icons and module counts.
  - "Exploit Builder (0-Day)" category is expanded by default; all others collapsed.
  - Real-time search bar that filters by module name or description and force-expands matched categories.
  - Parameter count pill badge on each module row.
  - Double-click to add a block to the canvas.
- **`ParamPanel`** (`param_panel.py`) — Right-panel parameter editor:
  - Auto-generates a labeled input field for every option of the selected block.
  - Emits `param_changed` signal on every keystroke for live preview updates.
- **`PreviewPanel`** (`preview_panel.py`) — Live Python code preview (read-only):
  - Full Python syntax highlighter (`PythonHighlighter`) with Dracula-inspired color scheme.
  - Special highlight for `CTX` shared context variable (neon green).
  - Switches between `⚡ SINGLE` and `🔗 CHAIN` mode badges automatically.
  - Line count badge updated in real time.
  - Placeholder quick-start guide when canvas is empty.
- **`theme.py`** — Centralized dark theme with neon accents (red, gold, green, blue) used across all widgets via Qt stylesheets.
- **Toolbar** — Top toolbar with: logo + version label, **Save WS** / **Load WS**, **Clear Canvas**, current mode indicator, and **GENERATE EXPLOIT** button.
- **Mode indicator** — Displays `Single` (gold) or `Chain (N stages)` (red) based on canvas state.
- **Block counter** — Live "N blocks" label on the canvas info bar.
- **Validation bar** — Inline error/warning banner below the canvas info bar (hides when no issues).
- **Background generation** — `GenerateWorker` runs exploit generation on a `QThread` to prevent UI freezing; button becomes "Generating…" spinner during generation.
- **Save/Load Workspace** — Canvas state (block positions, connections, all parameter values) saved to / loaded from JSON files in the `workspaces/` directory.
- **File dialog for output** — "GENERATE EXPLOIT" opens a save dialog pre-filled with a sensible filename.
- **PyQt5 / PyQt6 compatibility shim** (`qt_compat.py`) — All Qt5/Qt6 enum differences handled transparently; the same codebase works with both versions.

---

#### CLI — Interactive Rich Shell (`viperforge/cli/shell.py`)

A complete rewrite of the original Go shell using the **Rich** library.

- **Dual-mode launcher**: `python viperforge.py` → GUI, `python viperforge.py --cli` → CLI.
- **Mode selection menu** on startup: Single Exploit Mode or Chain Builder Mode.
- **Single Exploit Mode** (`_single_mode_loop`):
  - Two-level nested menu: category selection → exploit listing.
  - `[0/back]` navigation and `clear` / `exit` global commands.
  - Interactive wizard (`run_wizard`) prompts each parameter with its description and default value.
  - Preview table showing all configured options before generation.
  - Actions after preview: Generate / Reconfigure / Back.
- **Chain Builder Mode** (`_chain_mode_loop`):
  - Add blocks one by one, each with their own parameter wizard.
  - Display current chain as a numbered table.
  - Remove a block by index.
  - Generate the full chain exploit script in one step.
- **Rich-formatted output**: colored tables, panels, rules, bold/dim text throughout.
- **ASCII banner** printed on every screen clear.

---

#### Exploit Engine (`viperforge/engine.py`)

- **`generate_single(session, out_path)`** — Renders a single Jinja2 template with session options and writes the exploit script to `output/`.
- **`generate_chain(sessions, out_path)`** — Merges multiple sessions into one Python script. Three modes:
  - **Pure builder chain** (`_generate_builder_chain`) — flat sequential code; imports deduplicated and placed at top; `CTX = {}` declared once; blocks separated by section comments.
  - **Pure classic chain** (`_generate_classic_chain`) — each block wrapped in its own `stage_N_name()` function; `main()` calls them in order with progress messages.
  - **Hybrid chain** — builder blocks first as flat code, classic blocks as functions, separated by section banners.
- **`preview_single(session)`** — Returns rendered template as a string (no file write) for GUI live preview.
- **`preview_chain(sessions)`** — Returns full chain code as a string for GUI chain preview.
- **Automatic CTX injection** — Adds `CTX = {}` header to single-block output if the template uses `CTX` without declaring it.
- **Shebang + auto-generated header** — All chain outputs include `#!/usr/bin/env python3`, a version comment, and the block/module list.
- **`_is_builder(session)`** — Detects whether a session uses a `builder_*` block to select the correct generation path.

---

#### Chain Validator (`viperforge/validator.py`)

Pre-generation static analysis that prevents broken exploit chains from being silently generated.

- **Socket dependency check** — `builder_send`, `builder_recv`, `builder_recv_until` require a `builder_socket` block with a matching `SOCK_NAME` earlier in the chain (ERROR if missing).
- **CTX variable tracking** — Warns if a block reads a variable (`INPUT_VAR`, `PAYLOAD_VAR`, `VAR_NAME`) that was not written by any earlier block in the chain.
- **Empty CODE check** — `builder_custom` blocks with an empty `CODE` field raise an ERROR.
- **Value parseability check** — `builder_pack` and `builder_p32_p64` validate that `VALUE` is a parseable Python integer/hex (ERROR if not).
- **Sleep seconds check** — `builder_sleep` validates `SECONDS` as a valid float (ERROR if not).
- **HTTP URL format check** — `builder_http_req` warns if `URL` does not start with `http://` or `https://`.
- **Empty file path check** — `builder_read_file` and `builder_write_file` raise an ERROR if `FILE_PATH` is empty.
- **Mixed chain warning** — Warns (WARNING) when builder blocks and classic exploit blocks are mixed in the same chain.
- **Single block info** — Info-level hint when only one builder block is in the chain.
- **`ValidationIssue`** class with `severity` (`error` / `warning` / `info`), `block_name`, and `message`.

---

#### Exploit Registry — 36 Modules (`viperforge/registry.py`)

Expanded from 18 → 36 modules. All modules have unique IDs, names, categories, descriptions, a Jinja2 template reference, and typed `ExploitOption` entries.

**Category color and icon maps** — each category has a neon color and a FontAwesome 5 icon used in both the GUI and CLI.

##### Exploit Builder (0-Day) — 18 Micro-Blocks

| ID | Module | Description |
|---|---|---|
| 19 | `builder_socket` | Create a TCP network socket |
| 20 | `builder_send` | Send data via socket |
| 21 | `builder_recv` | Receive data from socket |
| 22 | `builder_pack` | Pack integers/bytes into a struct buffer |
| 23 | `builder_custom` | Custom Python code execution |
| 24 | `builder_recv_until` | Receive from socket until a pattern is matched (with timeout) |
| 25 | `builder_http_req` | HTTP GET/POST request via `requests` |
| 26 | `builder_b64encode` | Base64-encode a variable |
| 27 | `builder_b64decode` | Base64-decode a variable |
| 28 | `builder_urlencode` | URL-encode a string |
| 29 | `builder_hex` | Hex encode or decode a variable |
| 30 | `builder_xor` | XOR a bytes variable with a key |
| 31 | `builder_shell_cmd` | Execute a local shell command (blocking or non-blocking) |
| 32 | `builder_read_file` | Read a local file into a variable (text or binary) |
| 33 | `builder_write_file` | Write a variable's content to a local file (text or binary) |
| 34 | `builder_print` | Print a message or variable to console |
| 35 | `builder_sleep` | Pause execution for N seconds |
| 36 | `builder_p32_p64` | Pack an integer to 32/64-bit little-endian bytes (p32/p64) |

##### Classic Exploit Modules — 18 Modules (unchanged from v1.0.0-beta)

| Category | Modules |
|---|---|
| **Binary Exploitation** | `bof_remote`, `bof_local`, `rop_chain`, `format_string`, `heap_uaf` |
| **Web Exploitation** | `web_lfi`, `web_sqli`, `web_ssti`, `web_cmd_exec`, `web_xxe`, `web_deserialization`, `web_ssrf` |
| **Privilege Escalation** | `privesc_suid`, `privesc_sudo_token` |
| **Network Attacks** | `network_ftp_anon`, `network_smb_relay` |
| **Cryptography** | `crypto_padding_oracle` |
| **Active Directory** | `ad_kerberoasting` |

**Helper functions**: `get_exploit_by_id()`, `get_exploit_by_name()`, `get_by_category()`, `all_categories()`.

---

#### Jinja2 Template Engine (`viperforge/engine.py` + `templates/exploits/`)

All 36 exploit modules now have Jinja2 (`.j2`) templates replacing the Go text/template (`.tmpl`) files.

- **18 builder micro-block templates** — Flat, importless code snippets designed to be stitched together into a single flat script.
- **18 classic exploit templates** — Self-contained scripts with imports and `if __name__ == "__main__"` guards.

---

#### C Payload Compiler (`viperforge/compiler.py`)

Python port of the original Go `compiler.go`. Unchanged functionality.

- Compiles `.c` payload sources from `templates/payloads/` using `gcc -m32 -fno-stack-protector -z execstack -nostdlib -static`.
- Extracts raw `.text` section bytes with `objcopy --only-section=.text --output-target=binary`.
- Returns raw shellcode as a hex string for embedding into exploit templates.
- Uses `tempfile.TemporaryDirectory` — all intermediate `.o` and `.bin` files are cleaned up automatically.

---

#### XOR Encoder (`viperforge/encoder.py`)

Python port of the original Go `encoder.go`. Upgraded decoder stub.

- `generate_key()` — generates a non-null cryptographically random single-byte XOR key via `os.urandom(1)`.
- `xor_encode(shellcode, key)` — single-byte XOR encoding.
- `build_decoder_stub_python(encoded, key)` — generates a self-contained Python decoder stub using `ctypes` and `mmap`:
  - Allocates `mmap` with `PROT_READ | PROT_WRITE | PROT_EXEC`.
  - Decodes shellcode inline using a list comprehension.
  - Casts to a `ctypes.CFUNCTYPE` and executes — position-independent execution without any subprocess.
- `encode_shellcode_file(shellcode)` — convenience wrapper returning `(encoded_bytes, key, stub_str)`.

---

#### Session Management (`viperforge/session.py`)

- `Session` class — holds `active_exploit` (`ExploitDef`) and a string `options` dict.
- `set_exploit(exploit_def)` — sets the active exploit and pre-fills all options with their defaults.
- `set_option(key, value)` / `get_option(key)` — option read/write.
- `to_dict()` — returns a flat dict for Jinja2 template rendering (merges exploit metadata + all options).

---

#### Dependencies (`requirements.txt`)

| Package | Version |
|---|---|
| `PyQt6` | ≥ 6.6.0 |
| `jinja2` | ≥ 3.1.0 |
| `rich` | ≥ 13.0.0 |
| `qtawesome` | ≥ 1.3.0 |

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

#### Core Framework (Go)
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
- **18 production-ready Python exploit templates** using `pwntools` and/or `requests` library patterns.

#### Evasion Techniques
- **Randomized NOP sled generation** in BOF templates — variable-length, non-static padding.
- **Base64-encoded command injection** payloads in `web_cmd_exec` to bypass WAF pattern matching.
- **`/dev/shm`-based payload staging** in binary exploitation templates — avoids disk-based EDR detection.
- **Dynamic API resolution** in `win_exec.c` via PEB walking — no hardcoded function imports.
