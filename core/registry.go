package core

import "fmt"

type ExploitOption struct {
	Name        string
	Description string
	DefaultVal  string
}

type ExploitDef struct {
	ID          int
	Name        string
	Category    string
	Description string
	Template    string
	Options     []ExploitOption
}

var Registry = []ExploitDef{
	{
		ID:          1,
		Name:        "bof_remote",
		Category:    "Binary Exploitation",
		Description: "Remote Buffer Overflow via TCP",
		Template:    "bof_remote",
		Options: []ExploitOption{
			{"RHOST", "Target IP Address", "127.0.0.1"},
			{"RPORT", "Target Port", "4444"},
			{"OFFSET", "Offset to EIP/RIP", "100"},
			{"EIP", "Return Address (Hex)", "0x080484b6"},
			{"PAYLOAD", "C Payload Name (e.g. execve)", ""},
		},
	},
	{
		ID:          2,
		Name:        "bof_local",
		Category:    "Binary Exploitation",
		Description: "Local Buffer Overflow (CLI Arguments / Stdin)",
		Template:    "bof_local",
		Options: []ExploitOption{
			{"TARGET_BIN", "Path to vulnerable executable", "./vuln"},
			{"OFFSET", "Offset to EIP/RIP", "100"},
			{"EIP", "Return Address (Hex)", "0x080484b6"},
			{"PAYLOAD", "C Payload Name", ""},
		},
	},
	{
		ID:          3,
		Name:        "rop_chain",
		Category:    "Binary Exploitation",
		Description: "Return-Oriented Programming (ROP) Chain Generator",
		Template:    "rop_chain",
		Options: []ExploitOption{
			{"RHOST", "Target IP Address", "127.0.0.1"},
			{"RPORT", "Target Port", "4444"},
			{"OFFSET", "Offset to return address", "100"},
			{"LIBC_BASE", "Leaked Libc Base (Hex)", "0xf7dc2000"},
			{"SYSTEM_OFFSET", "system() offset in libc", "0x0003a940"},
			{"BINSH_OFFSET", "/bin/sh offset in libc", "0x0015902b"},
		},
	},
	{
		ID:          4,
		Name:        "format_string",
		Category:    "Binary Exploitation",
		Description: "Format String Arbitrary Memory Write",
		Template:    "format_string",
		Options: []ExploitOption{
			{"RHOST", "Target IP Address", "127.0.0.1"},
			{"RPORT", "Target Port", "4444"},
			{"TARGET_ADDR", "Memory address to overwrite (e.g. GOT)", "0x0804a01c"},
			{"WRITE_VAL", "Value to inject (e.g. system addr)", "0x08048320"},
			{"FMT_OFFSET", "Format string parameter offset", "7"},
		},
	},
	{
		ID:          5,
		Name:        "heap_uaf",
		Category:    "Binary Exploitation",
		Description: "Heap Exploitation (Use-After-Free)",
		Template:    "heap_uaf",
		Options: []ExploitOption{
			{"RHOST", "Target IP Address", "127.0.0.1"},
			{"RPORT", "Target Port", "4444"},
			{"CHUNK_SIZE", "Size of allocated chunk", "64"},
			{"MAGIC_FUNC", "Address to redirect execution", "0x08048550"},
		},
	},
	{
		ID:          6,
		Name:        "web_lfi",
		Category:    "Web Exploitation",
		Description: "Local File Inclusion to Remote Code Execution (Log Poisoning)",
		Template:    "web_lfi",
		Options: []ExploitOption{
			{"TARGET_URL", "Target URL with LFI parameter", "http://127.0.0.1/index.php?page="},
			{"LOG_PATH", "Path to poisonable server log file", "/var/log/apache2/access.log"},
			{"PAYLOAD_CMD", "System command to execute", "id"},
		},
	},
	{
		ID:          7,
		Name:        "web_sqli",
		Category:    "Web Exploitation",
		Description: "Blind SQL Injection to RCE (via INTO OUTFILE)",
		Template:    "web_sqli",
		Options: []ExploitOption{
			{"TARGET_URL", "Target URL with SQLi parameter", "http://127.0.0.1/product.php?id=1"},
			{"WEB_ROOT", "Absolute path to server web root", "/var/www/html/"},
			{"SHELL_NAME", "Filename of the persistent web shell", "shell.php"},
		},
	},
	{
		ID:          8,
		Name:        "web_ssti",
		Category:    "Web Exploitation",
		Description: "Server-Side Template Injection (Jinja2/Flask Environments)",
		Template:    "web_ssti",
		Options: []ExploitOption{
			{"TARGET_URL", "Target URL with SSTI parameter", "http://127.0.0.1/hello?name="},
			{"PAYLOAD_CMD", "System command to execute", "id"},
		},
	},
	{
		ID:          9,
		Name:        "web_cmd_exec",
		Category:    "Web Exploitation",
		Description: "OS Command Injection via HTTP Parameters",
		Template:    "web_cmd_exec",
		Options: []ExploitOption{
			{"TARGET_URL", "Target URL with injectable parameter", "http://127.0.0.1/ping.php?ip="},
			{"PAYLOAD_CMD", "System command to execute", "id"},
			{"METHOD", "HTTP Method (GET/POST)", "GET"},
		},
	},
	{
		ID:          10,
		Name:        "web_xxe",
		Category:    "Web Exploitation",
		Description: "XML External Entity (XXE) Data Exfiltration",
		Template:    "web_xxe",
		Options: []ExploitOption{
			{"TARGET_URL", "Target URL accepting XML input", "http://127.0.0.1/api/xml"},
			{"READ_FILE", "File to read from the target system", "/etc/passwd"},
		},
	},
	{
		ID:          11,
		Name:        "web_deserialization",
		Category:    "Web Exploitation",
		Description: "Insecure Deserialization (Python Pickle)",
		Template:    "web_deserialization",
		Options: []ExploitOption{
			{"TARGET_URL", "Target URL accepting serialized data", "http://127.0.0.1/load_session"},
			{"PAYLOAD_CMD", "System command to execute", "id"},
			{"COOKIE_NAME", "Name of the cookie containing serialized data", "session"},
		},
	},
	{
		ID:          12,
		Name:        "web_ssrf",
		Category:    "Web Exploitation",
		Description: "Server-Side Request Forgery (SSRF) Internal Port Scanner",
		Template:    "web_ssrf",
		Options: []ExploitOption{
			{"TARGET_URL", "Target URL with SSRF vulnerability", "http://127.0.0.1/fetch?url="},
			{"INTERNAL_IP", "Internal IP to scan", "127.0.0.1"},
			{"PORTS", "Comma-separated list of ports to scan", "22,80,443,3306,6379"},
		},
	},
	{
		ID:          13,
		Name:        "privesc_suid",
		Category:    "Privilege Escalation",
		Description: "Local Privilege Escalation via SUID PATH Hijacking",
		Template:    "privesc_suid",
		Options: []ExploitOption{
			{"VULN_BIN", "Path to vulnerable SUID binary", "/usr/local/bin/vuln"},
			{"HIJACK_CMD", "Command being called without absolute path", "cat"},
			{"PAYLOAD_CMD", "Command to execute as root", "/bin/sh -p"},
		},
	},
	{
		ID:          14,
		Name:        "privesc_sudo_token",
		Category:    "Privilege Escalation",
		Description: "Local Privilege Escalation via Sudo Token Hijacking",
		Template:    "privesc_sudo_token",
		Options: []ExploitOption{
			{"TARGET_USER", "User to hijack sudo token from", "root"},
			{"PAYLOAD_CMD", "Command to execute as root", "/bin/bash -i"},
		},
	},
	{
		ID:          15,
		Name:        "network_ftp_anon",
		Category:    "Network Attacks",
		Description: "FTP Anonymous Login and Payload Upload",
		Template:    "network_ftp_anon",
		Options: []ExploitOption{
			{"RHOST", "Target IP Address", "127.0.0.1"},
			{"RPORT", "Target Port", "21"},
			{"UPLOAD_FILE", "Local file to upload", "payload.php"},
			{"REMOTE_DIR", "Remote directory to upload to", "/var/www/html/"},
		},
	},
	{
		ID:          16,
		Name:        "network_smb_relay",
		Category:    "Network Attacks",
		Description: "SMB Relay Attack Script (Wrapper)",
		Template:    "network_smb_relay",
		Options: []ExploitOption{
			{"TARGET_IP", "Target IP to relay authentication to", "192.168.1.100"},
			{"PAYLOAD_CMD", "Command to execute upon successful relay", "whoami"},
		},
	},
	{
		ID:          17,
		Name:        "crypto_padding_oracle",
		Category:    "Cryptography",
		Description: "Padding Oracle Attack Automation",
		Template:    "crypto_padding_oracle",
		Options: []ExploitOption{
			{"TARGET_URL", "Target URL with Padding Oracle vulnerability", "http://127.0.0.1/decrypt?cipher="},
			{"BLOCK_SIZE", "Cipher block size in bytes", "16"},
			{"CIPHERTEXT", "Base64 or Hex encoded ciphertext to decrypt", ""},
		},
	},
	{
		ID:          18,
		Name:        "ad_kerberoasting",
		Category:    "Active Directory",
		Description: "Kerberoasting Attack Automation",
		Template:    "ad_kerberoasting",
		Options: []ExploitOption{
			{"DOMAIN", "Target Domain", "corp.local"},
			{"DC_IP", "Domain Controller IP Address", "192.168.1.10"},
			{"USERNAME", "Valid Username", "user"},
			{"PASSWORD", "Valid Password", "Password123!"},
		},
	},
}

func GetExploitByID(id int) (*ExploitDef, error) {
	for _, e := range Registry {
		if e.ID == id {
			return &e, nil
		}
	}
	return nil, fmt.Errorf("exploit ID %d not found in database", id)
}
