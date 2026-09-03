"""
ViperForge v2.0 — Exploit Registry
Definitions of all exploit modules are here.
"""

from dataclasses import dataclass, field
from typing import List

# ─── Block colors (by category) ──────────────────────────────────────────────
CATEGORY_COLORS = {
    "Binary Exploitation":  "#e63946",   # neon red
    "Web Exploitation":     "#f4a261",   # neon orange
    "Privilege Escalation": "#2ec4b6",   # neon teal
    "Network Attacks":      "#9b5de5",   # neon purple
    "Cryptography":         "#fee440",   # neon yellow
    "Active Directory":     "#00b4d8",   # neon blue
    "Exploit Builder (0-Day)": "#00ff88", # neon green
    "Macros":               "#ffd60a",   # neon gold
}

CATEGORY_ICONS = {
    "Binary Exploitation":  "fa5s.bomb",
    "Web Exploitation":     "fa5s.globe",
    "Privilege Escalation": "fa5s.angle-double-up",
    "Network Attacks":      "fa5s.network-wired",
    "Cryptography":         "fa5s.lock",
    "Active Directory":     "fa5s.building",
    "Exploit Builder (0-Day)": "fa5s.puzzle-piece",
    "Macros":               "fa5s.layer-group",
}


@dataclass
class ExploitOption:
    name:        str
    description: str
    default:     str


@dataclass
class ExploitDef:
    id:          int
    name:        str
    category:    str
    description: str
    template:    str
    options:     List[ExploitOption] = field(default_factory=list)

    @property
    def color(self) -> str:
        return CATEGORY_COLORS.get(self.category, "#ffffff")

    @property
    def icon(self) -> str:
        return CATEGORY_ICONS.get(self.category, "fa5s.bolt")


# ─── Registry ─────────────────────────────────────────────────────────────────
REGISTRY: List[ExploitDef] = [
    # ── Exploit Builder (0-Day) ────────────────────────────────────────────────
    ExploitDef(
        id=19, name="builder_socket", category="Exploit Builder (0-Day)",
        description="Create a TCP network socket",
        template="builder_socket",
        options=[
            ExploitOption("SOCK_NAME", "Variable name for the socket", "sock"),
            ExploitOption("TARGET_IP", "Target IP Address", "127.0.0.1"),
            ExploitOption("TARGET_PORT", "Target Port", "4444"),
        ],
    ),
    ExploitDef(
        id=20, name="builder_send", category="Exploit Builder (0-Day)",
        description="Send data via socket",
        template="builder_send",
        options=[
            ExploitOption("SOCK_NAME", "Variable name for the socket", "sock"),
            ExploitOption("PAYLOAD_VAR", "Variable name containing data to send", "payload"),
        ],
    ),
    ExploitDef(
        id=21, name="builder_recv", category="Exploit Builder (0-Day)",
        description="Receive data from socket",
        template="builder_recv",
        options=[
            ExploitOption("SOCK_NAME", "Variable name for the socket", "sock"),
            ExploitOption("RECV_VAR", "Variable name to store received data", "response"),
            ExploitOption("BUFFER_SIZE", "Receive buffer size", "4096"),
        ],
    ),
    ExploitDef(
        id=22, name="builder_pack", category="Exploit Builder (0-Day)",
        description="Pack integers/bytes into a struct buffer",
        template="builder_pack",
        options=[
            ExploitOption("VAR_NAME", "Variable name for packed output", "payload"),
            ExploitOption("FORMAT_STR", "Struct format string (e.g. <I, <Q)", "<I"),
            ExploitOption("VALUE", "Value to pack (eval'd in python)", "0xdeadbeef"),
            ExploitOption("APPEND_TO", "Existing buffer var to append to (optional)", ""),
        ],
    ),
    ExploitDef(
        id=23, name="builder_custom", category="Exploit Builder (0-Day)",
        description="Custom Python Code Execution",
        template="builder_custom",
        options=[
            ExploitOption("CODE", "Python code to execute", "print('[*] Custom code executing')"),
        ],
    ),
    
    # --- Newly Added Extended Micro Blocks ---
    ExploitDef(
        id=24, name="builder_recv_until", category="Exploit Builder (0-Day)",
        description="Receive data from socket until a specific string is found",
        template="builder_recv_until",
        options=[
            ExploitOption("SOCK_NAME", "Variable name for the socket", "sock"),
            ExploitOption("RECV_VAR", "Variable name to store received data", "response"),
            ExploitOption("PATTERN", "String or byte pattern to wait for", "Password: "),
            ExploitOption("TIMEOUT", "Timeout in seconds", "5.0"),
        ],
    ),
    ExploitDef(
        id=25, name="builder_http_req", category="Exploit Builder (0-Day)",
        description="Send an HTTP GET/POST request (like python requests)",
        template="builder_http_req",
        options=[
            ExploitOption("URL", "Target URL", "http://127.0.0.1/"),
            ExploitOption("METHOD", "HTTP Method (GET, POST)", "GET"),
            ExploitOption("DATA_VAR", "Variable name containing data to send (optional)", ""),
            ExploitOption("HEADERS", "JSON string for headers (optional)", "{\"User-Agent\": \"ViperForge/2.0\"}"),
            ExploitOption("RESP_VAR", "Variable name to store response text", "response"),
        ],
    ),
    ExploitDef(
        id=26, name="builder_b64encode", category="Exploit Builder (0-Day)",
        description="Base64 Encode a string or bytes",
        template="builder_b64encode",
        options=[
            ExploitOption("INPUT_VAR", "Variable name containing input data", "payload"),
            ExploitOption("OUTPUT_VAR", "Variable name for encoded output", "encoded_payload"),
        ],
    ),
    ExploitDef(
        id=27, name="builder_b64decode", category="Exploit Builder (0-Day)",
        description="Base64 Decode a string or bytes",
        template="builder_b64decode",
        options=[
            ExploitOption("INPUT_VAR", "Variable name containing base64 data", "encoded_payload"),
            ExploitOption("OUTPUT_VAR", "Variable name for decoded output", "decoded_payload"),
        ],
    ),
    ExploitDef(
        id=28, name="builder_urlencode", category="Exploit Builder (0-Day)",
        description="URL Encode a string",
        template="builder_urlencode",
        options=[
            ExploitOption("INPUT_VAR", "Variable name containing input string", "payload"),
            ExploitOption("OUTPUT_VAR", "Variable name for urlencoded output", "url_payload"),
        ],
    ),
    ExploitDef(
        id=29, name="builder_hex", category="Exploit Builder (0-Day)",
        description="Convert string/bytes to Hex (or reverse)",
        template="builder_hex",
        options=[
            ExploitOption("INPUT_VAR", "Variable name containing input data", "payload"),
            ExploitOption("OUTPUT_VAR", "Variable name for output data", "hex_payload"),
            ExploitOption("MODE", "Direction: ENCODE or DECODE", "ENCODE"),
        ],
    ),
    ExploitDef(
        id=30, name="builder_xor", category="Exploit Builder (0-Day)",
        description="XOR data with a specific key",
        template="builder_xor",
        options=[
            ExploitOption("INPUT_VAR", "Variable name containing input bytes", "shellcode"),
            ExploitOption("KEY", "XOR key string or hex (e.g. 0xaa)", "0xaa"),
            ExploitOption("OUTPUT_VAR", "Variable name for XOR'd output", "obfuscated"),
        ],
    ),
    ExploitDef(
        id=31, name="builder_shell_cmd", category="Exploit Builder (0-Day)",
        description="Execute a local shell command (e.g. start netcat listener)",
        template="builder_shell_cmd",
        options=[
            ExploitOption("COMMAND", "Shell command to execute locally", "nc -lvnp 4444"),
            ExploitOption("BLOCKING", "Wait for command to finish (True/False)", "False"),
        ],
    ),
    ExploitDef(
        id=32, name="builder_read_file", category="Exploit Builder (0-Day)",
        description="Read a local file into a variable",
        template="builder_read_file",
        options=[
            ExploitOption("FILE_PATH", "Path to file to read", "/etc/passwd"),
            ExploitOption("OUTPUT_VAR", "Variable name to store file contents", "file_data"),
            ExploitOption("MODE", "Read mode (TEXT or BINARY)", "TEXT"),
        ],
    ),
    ExploitDef(
        id=33, name="builder_write_file", category="Exploit Builder (0-Day)",
        description="Write a variable's content to a local file",
        template="builder_write_file",
        options=[
            ExploitOption("INPUT_VAR", "Variable name containing data to write", "dumped_data"),
            ExploitOption("FILE_PATH", "Path to file to write", "output.bin"),
            ExploitOption("MODE", "Write mode (TEXT or BINARY)", "BINARY"),
        ],
    ),
    ExploitDef(
        id=34, name="builder_print", category="Exploit Builder (0-Day)",
        description="Print a message or variable value to console",
        template="builder_print",
        options=[
            ExploitOption("MESSAGE", "Text to print (can use format strings with CTX)", "[*] Stage 1 complete."),
            ExploitOption("VAR_NAME", "Variable name to print (optional)", ""),
        ],
    ),
    ExploitDef(
        id=35, name="builder_sleep", category="Exploit Builder (0-Day)",
        description="Pause execution for N seconds",
        template="builder_sleep",
        options=[
            ExploitOption("SECONDS", "Number of seconds to sleep", "1.5"),
        ],
    ),
    ExploitDef(
        id=36, name="builder_p32_p64", category="Exploit Builder (0-Day)",
        description="Fast pack an integer to 32/64 bit little-endian (p32/p64)",
        template="builder_p32_p64",
        options=[
            ExploitOption("VALUE", "Integer or hex value to pack", "0xdeadbeef"),
            ExploitOption("ARCH", "Architecture (32 or 64)", "32"),
            ExploitOption("OUTPUT_VAR", "Variable name to store packed bytes", "packed_val"),
            ExploitOption("APPEND_TO", "Existing buffer var to append to (optional)", ""),
        ],
    ),

    # ── Logic / Loop Micro-Blocks ──────────────────────────────────────────────
    ExploitDef(
        id=37, name="builder_if_else", category="Exploit Builder (0-Day)",
        description="Conditional branch based on CTX variable",
        template="builder_if_else",
        options=[
            ExploitOption("VAR_NAME",      "CTX variable name to evaluate",    "response"),
            ExploitOption("OPERATOR",      "Comparison operator (==, !=, contains, >, <)", "=="),
            ExploitOption("COMPARE_VALUE", "Value to compare against",         "200"),
        ],
    ),
    ExploitDef(
        id=38, name="builder_loop", category="Exploit Builder (0-Day)",
        description="Iterate over wordlist, range, or file lines",
        template="builder_loop",
        options=[
            ExploitOption("MODE",         "Loop mode (LIST, RANGE, FILE)",    "LIST"),
            ExploitOption("WORDLIST_VAR", "CTX variable holding the list",    "wordlist"),
            ExploitOption("ITERATOR_VAR", "Iterator variable name",           "item"),
            ExploitOption("RANGE_START",  "Range start (if MODE=RANGE)",      "0"),
            ExploitOption("RANGE_END",    "Range end (if MODE=RANGE)",        "100"),
            ExploitOption("FILE_PATH",    "File path (if MODE=FILE)",         "wordlist.txt"),
        ],
    ),
    ExploitDef(
        id=39, name="builder_try_catch", category="Exploit Builder (0-Day)",
        description="Wrap next blocks in try/except for error handling",
        template="builder_try_catch",
        options=[
            ExploitOption("ERROR_TYPES",    "Exception types to catch (Timeout, ConnectionReset, All)", "All"),
            ExploitOption("FALLBACK_ACTION","Action on error (SKIP, RETRY, LOG)",                      "LOG"),
            ExploitOption("RETRY_COUNT",    "Number of retries (if RETRY)",                             "3"),
        ],
    ),
    ExploitDef(
        id=40, name="builder_variable_set", category="Exploit Builder (0-Day)",
        description="Set a CTX variable (static, regex, or eval)",
        template="builder_variable_set",
        options=[
            ExploitOption("VAR_NAME",      "CTX variable name to set",         "token"),
            ExploitOption("VALUE",         "Static value or eval expression",  ""),
            ExploitOption("MODE",          "Mode (STATIC, REGEX, EVAL)",       "STATIC"),
            ExploitOption("REGEX_PATTERN", "Regex pattern with group(1)",      ""),
            ExploitOption("SOURCE_VAR",    "CTX variable to apply regex on",   "response"),
        ],
    ),

    # ── Binary Exploitation ────────────────────────────────────────────────────
    ExploitDef(
        id=1, name="bof_remote", category="Binary Exploitation",
        description="Remote Buffer Overflow via TCP",
        template="bof_remote",
        options=[
            ExploitOption("RHOST",   "Target IP Address",         "127.0.0.1"),
            ExploitOption("RPORT",   "Target Port",               "4444"),
            ExploitOption("OFFSET",  "Offset to EIP/RIP",         "100"),
            ExploitOption("EIP",     "Return Address (Hex)",       "0x080484b6"),
            ExploitOption("PAYLOAD", "C Payload Name (e.g. execve)", ""),
        ],
    ),
    ExploitDef(
        id=2, name="bof_local", category="Binary Exploitation",
        description="Local Buffer Overflow (CLI Arguments / Stdin)",
        template="bof_local",
        options=[
            ExploitOption("TARGET_BIN", "Path to vulnerable executable", "./vuln"),
            ExploitOption("OFFSET",     "Offset to EIP/RIP",             "100"),
            ExploitOption("EIP",        "Return Address (Hex)",           "0x080484b6"),
            ExploitOption("PAYLOAD",    "C Payload Name",                 ""),
        ],
    ),
    ExploitDef(
        id=3, name="rop_chain", category="Binary Exploitation",
        description="Return-Oriented Programming (ROP) Chain Generator",
        template="rop_chain",
        options=[
            ExploitOption("RHOST",          "Target IP Address",         "127.0.0.1"),
            ExploitOption("RPORT",          "Target Port",               "4444"),
            ExploitOption("OFFSET",         "Offset to return address",  "100"),
            ExploitOption("LIBC_BASE",      "Leaked Libc Base (Hex)",    "0xf7dc2000"),
            ExploitOption("SYSTEM_OFFSET",  "system() offset in libc",   "0x0003a940"),
            ExploitOption("BINSH_OFFSET",   "/bin/sh offset in libc",    "0x0015902b"),
        ],
    ),
    ExploitDef(
        id=4, name="format_string", category="Binary Exploitation",
        description="Format String Arbitrary Memory Write",
        template="format_string",
        options=[
            ExploitOption("RHOST",       "Target IP Address",                      "127.0.0.1"),
            ExploitOption("RPORT",       "Target Port",                            "4444"),
            ExploitOption("TARGET_ADDR", "Memory address to overwrite (e.g. GOT)", "0x0804a01c"),
            ExploitOption("WRITE_VAL",   "Value to inject (e.g. system addr)",     "0x08048320"),
            ExploitOption("FMT_OFFSET",  "Format string parameter offset",         "7"),
        ],
    ),
    ExploitDef(
        id=5, name="heap_uaf", category="Binary Exploitation",
        description="Heap Exploitation (Use-After-Free)",
        template="heap_uaf",
        options=[
            ExploitOption("RHOST",      "Target IP Address",              "127.0.0.1"),
            ExploitOption("RPORT",      "Target Port",                    "4444"),
            ExploitOption("CHUNK_SIZE", "Size of allocated chunk",        "64"),
            ExploitOption("MAGIC_FUNC", "Address to redirect execution",  "0x08048550"),
        ],
    ),

    # ── Web Exploitation ───────────────────────────────────────────────────────
    ExploitDef(
        id=6, name="web_lfi", category="Web Exploitation",
        description="Local File Inclusion to RCE (Log Poisoning)",
        template="web_lfi",
        options=[
            ExploitOption("TARGET_URL",  "Target URL with LFI parameter",       "http://127.0.0.1/index.php?page="),
            ExploitOption("LOG_PATH",    "Path to poisonable server log file",   "/var/log/apache2/access.log"),
            ExploitOption("PAYLOAD_CMD", "System command to execute",            "id"),
        ],
    ),
    ExploitDef(
        id=7, name="web_sqli", category="Web Exploitation",
        description="Blind SQL Injection to RCE (via INTO OUTFILE)",
        template="web_sqli",
        options=[
            ExploitOption("TARGET_URL",  "Target URL with SQLi parameter",     "http://127.0.0.1/product.php?id=1"),
            ExploitOption("WEB_ROOT",    "Absolute path to server web root",   "/var/www/html/"),
            ExploitOption("SHELL_NAME",  "Filename of the persistent web shell", "shell.php"),
        ],
    ),
    ExploitDef(
        id=8, name="web_ssti", category="Web Exploitation",
        description="Server-Side Template Injection (Jinja2/Flask)",
        template="web_ssti",
        options=[
            ExploitOption("TARGET_URL",  "Target URL with SSTI parameter",   "http://127.0.0.1/hello?name="),
            ExploitOption("PAYLOAD_CMD", "System command to execute",        "id"),
        ],
    ),
    ExploitDef(
        id=9, name="web_cmd_exec", category="Web Exploitation",
        description="OS Command Injection via HTTP Parameters",
        template="web_cmd_exec",
        options=[
            ExploitOption("TARGET_URL",  "Target URL with injectable parameter", "http://127.0.0.1/ping.php?ip="),
            ExploitOption("PAYLOAD_CMD", "System command to execute",            "id"),
            ExploitOption("METHOD",      "HTTP Method (GET/POST)",               "GET"),
        ],
    ),
    ExploitDef(
        id=10, name="web_xxe", category="Web Exploitation",
        description="XML External Entity (XXE) Data Exfiltration",
        template="web_xxe",
        options=[
            ExploitOption("TARGET_URL", "Target URL accepting XML input",  "http://127.0.0.1/api/xml"),
            ExploitOption("READ_FILE",  "File to read from target system", "/etc/passwd"),
        ],
    ),
    ExploitDef(
        id=11, name="web_deserialization", category="Web Exploitation",
        description="Insecure Deserialization (Python Pickle)",
        template="web_deserialization",
        options=[
            ExploitOption("TARGET_URL",  "Target URL accepting serialized data", "http://127.0.0.1/load_session"),
            ExploitOption("PAYLOAD_CMD", "System command to execute",            "id"),
            ExploitOption("COOKIE_NAME", "Name of the cookie with serialized data", "session"),
        ],
    ),
    ExploitDef(
        id=12, name="web_ssrf", category="Web Exploitation",
        description="Server-Side Request Forgery (SSRF) Internal Port Scanner",
        template="web_ssrf",
        options=[
            ExploitOption("TARGET_URL",  "Target URL with SSRF vulnerability", "http://127.0.0.1/fetch?url="),
            ExploitOption("INTERNAL_IP", "Internal IP to scan",                "127.0.0.1"),
            ExploitOption("PORTS",       "Comma-separated list of ports",       "22,80,443,3306,6379"),
        ],
    ),

    # ── Privilege Escalation ───────────────────────────────────────────────────
    ExploitDef(
        id=13, name="privesc_suid", category="Privilege Escalation",
        description="Local Privilege Escalation via SUID PATH Hijacking",
        template="privesc_suid",
        options=[
            ExploitOption("VULN_BIN",    "Path to vulnerable SUID binary",         "/usr/local/bin/vuln"),
            ExploitOption("HIJACK_CMD",  "Command being called without abs path",  "cat"),
            ExploitOption("PAYLOAD_CMD", "Command to execute as root",             "/bin/sh -p"),
        ],
    ),
    ExploitDef(
        id=14, name="privesc_sudo_token", category="Privilege Escalation",
        description="Local Privilege Escalation via Sudo Token Hijacking",
        template="privesc_sudo_token",
        options=[
            ExploitOption("TARGET_USER", "User to hijack sudo token from", "root"),
            ExploitOption("PAYLOAD_CMD", "Command to execute as root",     "/bin/bash -i"),
        ],
    ),

    # ── Network Attacks ────────────────────────────────────────────────────────
    ExploitDef(
        id=15, name="network_ftp_anon", category="Network Attacks",
        description="FTP Anonymous Login and Payload Upload",
        template="network_ftp_anon",
        options=[
            ExploitOption("RHOST",       "Target IP Address",             "127.0.0.1"),
            ExploitOption("RPORT",       "Target Port",                   "21"),
            ExploitOption("UPLOAD_FILE", "Local file to upload",          "payload.php"),
            ExploitOption("REMOTE_DIR",  "Remote directory to upload to", "/var/www/html/"),
        ],
    ),
    ExploitDef(
        id=16, name="network_smb_relay", category="Network Attacks",
        description="SMB Relay Attack Script (Wrapper)",
        template="network_smb_relay",
        options=[
            ExploitOption("TARGET_IP",   "Target IP to relay authentication to", "192.168.1.100"),
            ExploitOption("PAYLOAD_CMD", "Command to execute upon relay",        "whoami"),
        ],
    ),

    # ── Cryptography ───────────────────────────────────────────────────────────
    ExploitDef(
        id=17, name="crypto_padding_oracle", category="Cryptography",
        description="Padding Oracle Attack Automation",
        template="crypto_padding_oracle",
        options=[
            ExploitOption("TARGET_URL",  "Target URL with Padding Oracle vuln", "http://127.0.0.1/decrypt?cipher="),
            ExploitOption("BLOCK_SIZE",  "Cipher block size in bytes",           "16"),
            ExploitOption("CIPHERTEXT",  "Base64 or Hex encoded ciphertext",     ""),
        ],
    ),

    # ── Active Directory ───────────────────────────────────────────────────────
    ExploitDef(
        id=18, name="ad_kerberoasting", category="Active Directory",
        description="Kerberoasting Attack Automation",
        template="ad_kerberoasting",
        options=[
            ExploitOption("DOMAIN",    "Target Domain",               "corp.local"),
            ExploitOption("DC_IP",     "Domain Controller IP Address", "192.168.1.10"),
            ExploitOption("USERNAME",  "Valid Username",               "user"),
            ExploitOption("PASSWORD",  "Valid Password",               "Password123!"),
        ],
    ),
]

# ─── Helper functions ─────────────────────────────────────────────────────────

def get_exploit_by_id(exploit_id: int) -> ExploitDef | None:
    return next((e for e in REGISTRY if e.id == exploit_id), None)


def get_exploit_by_name(name: str) -> ExploitDef | None:
    return next((e for e in REGISTRY if e.name == name), None)


def get_by_category(category: str) -> List[ExploitDef]:
    return [e for e in REGISTRY if e.category == category]


def all_categories() -> List[str]:
    seen = []
    for e in REGISTRY:
        if e.category not in seen:
            seen.append(e.category)
    return seen
