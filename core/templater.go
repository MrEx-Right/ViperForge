package core

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"text/template"
)

func GenerateExploit(session *Session) error {
	templatePath := filepath.Join("templates", "exploits", session.ActiveExploit+".tmpl")
	
	if _, err := os.Stat(templatePath); os.IsNotExist(err) {
		return fmt.Errorf("template %s not found", templatePath)
	}

	tmpl, err := template.ParseFiles(templatePath)
	if err != nil {
		return fmt.Errorf("failed to parse template: %v", err)
	}

	// Check if we need to compile a payload
	if payloadName := session.GetOption("PAYLOAD"); payloadName != "" {
		fmt.Printf("[*] Compiling payload: %s\n", payloadName)
		shellcode, err := CompilePayload(payloadName)
		if err != nil {
			return fmt.Errorf("failed to compile payload: %v", err)
		}
		session.SetOption("SHELLCODE", shellcode)
	}

	// Prepare output file name (e.g. bof_remote_exploit.py)
	outName := strings.ReplaceAll(session.ActiveExploit, "/", "_") + "_exploit.py"
	
	outFile, err := os.Create(outName)
	if err != nil {
		return fmt.Errorf("failed to create output file: %v", err)
	}
	defer outFile.Close()

	err = tmpl.Execute(outFile, session.Options)
	if err != nil {
		return fmt.Errorf("failed to execute template: %v", err)
	}

	fmt.Printf("[+] Exploit successfully generated: %s\n", outName)
	return nil
}
