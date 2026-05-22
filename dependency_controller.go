package main

import (
	"fmt"
	"os"
	"strings"
)

// InjectDependencyCheck appends a Python pre-flight check to the generated script
func InjectDependencyCheck(scriptPath string) {
	if !strings.HasSuffix(scriptPath, ".py") {
		return
	}

	content, err := os.ReadFile(scriptPath)
	if err != nil {
		fmt.Printf("[-] Failed to read generated script for dependency check: %v\n", err)
		return
	}

	preflight := `
import sys
import importlib.util

def __preflight_check():
    required_deps = {
        'pwntools': 'pwn',
        'requests': 'requests',
        'impacket': 'impacket'
    }
    missing = []
    for friendly_name, module_name in required_deps.items():
        if importlib.util.find_spec(module_name) is None:
            missing.append(friendly_name)
            
    if missing:
        print(f"[-] Pre-flight check failed! Missing dependencies: {', '.join(missing)}")
        print("[*] Please install them before running the exploit.")
        sys.exit(1)

__preflight_check()

`

	scriptStr := string(content)
	var newContent string

	// Check if there's a shebang line
	if strings.HasPrefix(scriptStr, "#!") {
		nl := strings.Index(scriptStr, "\n")
		if nl != -1 {
			newContent = scriptStr[:nl+1] + preflight + scriptStr[nl+1:]
		} else {
			newContent = preflight + scriptStr
		}
	} else {
		newContent = preflight + scriptStr
	}

	err = os.WriteFile(scriptPath, []byte(newContent), 0755)
	if err != nil {
		fmt.Printf("[-] Failed to inject dependency check: %v\n", err)
	} else {
		fmt.Printf("[+] Pre-flight dependency check injected into %s\n", scriptPath)
	}
}
