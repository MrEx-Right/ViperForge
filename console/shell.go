package console

import (
	"fmt"
	"os"
	"os/exec"
	"runtime"
	"strconv"
	"strings"

	"viperforge/core"

	"github.com/chzyer/readline"
)

func clearScreen() {
	if runtime.GOOS == "windows" {
		cmd := exec.Command("cmd", "/c", "cls")
		cmd.Stdout = os.Stdout
		cmd.Run()
	} else {
		fmt.Print("\033[H\033[2J")
	}
}

func printBanner() {
	fmt.Println(`
    ____   ____.__                     ___________                           
    \   \ /   /|__|_____   ___________ \_   _____/__________  ____   ____  
     \   Y   / |  \____ \_/ __ \_  __ \ |    __)/  _ \_  __ \/ ___\_/ __ \ 
      \     /  |  |  |_> >  ___/|  | \/ |     \(  <_> )  | \/ /_/  >  ___/ 
       \___/   |__|   __/ \___  >__|    \___  / \____/|__|  \___  / \___  >
                  |__|        \/            \/             /_____/      \/ v1.1.0-beta
                                Red Team Exploit Factory
	`)
}

var categories = []string{
	"Binary Exploitation",
	"Web Exploitation",
	"Privilege Escalation",
	"Network Attacks",
	"Cryptography",
	"Active Directory",
}

func printCategories() {
	fmt.Println("\n[ Exploit Categories ]")
	fmt.Println("======================")
	for i, c := range categories {
		fmt.Printf("[%d] %s\n", i+1, c)
	}
	fmt.Println("\n [exit] Terminate Session")
}

func printCategoryExploits(cat string) {
	fmt.Printf("\n[ %s ]\n", cat)
	fmt.Println(strings.Repeat("=", len(cat)+4))
	idx := 1
	for _, e := range core.Registry {
		if e.Category == cat {
			fmt.Printf("[%d] %-20s - %s\n", idx, e.Name, e.Description)
			idx++
		}
	}
	fmt.Println("\nCommands: [0] Back to Categories, [clear] Clear Screen, [exit] Terminate Session")
}

func getExploitByCategoryAndIndex(cat string, idx int) *core.ExploitDef {
	curr := 1
	for _, e := range core.Registry {
		if e.Category == cat {
			if curr == idx {
				def, _ := core.GetExploitByID(e.ID)
				return def
			}
			curr++
		}
	}
	return nil
}

func StartShell(session *core.Session) {
	l, err := readline.NewEx(&readline.Config{
		Prompt:          "\033[31mViperForge\033[0m > ",
		HistoryFile:     "viperforge_history.tmp",
		InterruptPrompt: "^C",
		EOFPrompt:       "exit",
	})
	if err != nil {
		panic(err)
	}
	defer l.Close()

	clearScreen()
	printBanner()

	currentCategory := ""

	for {
		if currentCategory == "" {
			printCategories()
			l.SetPrompt("\033[31mViperForge\033[0m > ")
		} else {
			printCategoryExploits(currentCategory)
			l.SetPrompt(fmt.Sprintf("\033[31mViperForge\033[0m (\033[36m%s\033[0m) > ", currentCategory))
		}

		line, err := l.Readline()
		if err != nil { // EOF or Ctrl+C
			break
		}

		line = strings.TrimSpace(line)
		if len(line) == 0 {
			continue
		}

		if line == "exit" || line == "quit" {
			fmt.Println("[*] Terminating ViperForge session. Goodbye.")
			return
		}
		if line == "clear" {
			clearScreen()
			printBanner()
			continue
		}

		if currentCategory == "" {
			idx, err := strconv.Atoi(line)
			if err != nil || idx < 1 || idx > len(categories) {
				fmt.Println("[-] Invalid category selection.")
				continue
			}
			currentCategory = categories[idx-1]
			clearScreen()
			printBanner()
		} else {
			if line == "0" || line == "back" {
				currentCategory = ""
				clearScreen()
				printBanner()
				continue
			}

			idx, err := strconv.Atoi(line)
			if err != nil {
				fmt.Println("[-] Invalid selection.")
				continue
			}
			def := getExploitByCategoryAndIndex(currentCategory, idx)
			if def == nil {
				fmt.Println("[-] Invalid exploit selection.")
				continue
			}

			runWizard(l, session, def)
			// Return to category selection or stay in current category?
			// It returns to the main loop, currentCategory is preserved.
			clearScreen()
			printBanner()
		}
	}
}

func runWizard(l *readline.Instance, session *core.Session, def *core.ExploitDef) {
	for {
		session.SetExploit(def)
		fmt.Printf("\n[*] Initializing Module: %s - %s\n", def.Name, def.Description)
		fmt.Println("[*] Entering Interactive Configuration Wizard...")

		for _, opt := range def.Options {
			promptStr := fmt.Sprintf(" > %s (%s) [%s]: ", opt.Name, opt.Description, opt.DefaultVal)
			l.SetPrompt(promptStr)
			val, err := l.Readline()
			if err != nil {
				return
			}
			val = strings.TrimSpace(val)
			if val != "" {
				session.SetOption(opt.Name, val)
			}
		}

		// Preview
		clearScreen()
		printBanner()
		fmt.Println("\n[ EXPLOIT PREVIEW & EXECUTION PLAN ]")
		fmt.Println("====================================")
		fmt.Printf("Vulnerability Profile : %s\n", def.Description)
		fmt.Println("Target Configuration  :")
		for _, opt := range def.Options {
			fmt.Printf("  -> %-15s : %s\n", opt.Name, session.GetOption(opt.Name))
		}

		fmt.Println("\n[ Attack Flow Overview ]")
		switch def.Name {
		case "bof_remote":
			fmt.Printf("1. Establish TCP connection to the target at %s:%s.\n", session.GetOption("RHOST"), session.GetOption("RPORT"))
			fmt.Printf("2. Construct malicious payload consisting of %s bytes of padding, an EIP overwrite (%s), and the compiled shellcode.\n", session.GetOption("OFFSET"), session.GetOption("EIP"))
			fmt.Println("3. Transmit payload to trigger memory corruption and execute arbitrary code.")
		case "bof_local":
			fmt.Printf("1. Initialize local execution of vulnerable binary: %s.\n", session.GetOption("TARGET_BIN"))
			fmt.Printf("2. Inject payload buffer containing %s bytes of padding and EIP override (%s).\n", session.GetOption("OFFSET"), session.GetOption("EIP"))
			fmt.Println("3. Exploit memory corruption to achieve local privilege escalation or arbitrary execution.")
		case "rop_chain":
			fmt.Printf("1. Establish connection to the target at %s:%s.\n", session.GetOption("RHOST"), session.GetOption("RPORT"))
			fmt.Println("2. Construct ROP Chain leveraging libc functions: system() -> exit() -> '/bin/sh'.")
			fmt.Printf("3. Calculate dynamic addresses utilizing Libc Base (%s), system() offset (%s), and /bin/sh offset (%s).\n", session.GetOption("LIBC_BASE"), session.GetOption("SYSTEM_OFFSET"), session.GetOption("BINSH_OFFSET"))
			fmt.Println("4. Deliver payload to bypass NX/DEP mitigations and spawn a shell.")
		case "format_string":
			fmt.Printf("1. Establish connection to the target at %s:%s.\n", session.GetOption("RHOST"), session.GetOption("RPORT"))
			fmt.Printf("2. Leverage format string vulnerability at parameter offset %s.\n", session.GetOption("FMT_OFFSET"))
			fmt.Printf("3. Perform arbitrary memory write operation: inject %s into target address %s.\n", session.GetOption("WRITE_VAL"), session.GetOption("TARGET_ADDR"))
		case "heap_uaf":
			fmt.Printf("1. Establish connection to the target at %s:%s.\n", session.GetOption("RHOST"), session.GetOption("RPORT"))
			fmt.Printf("2. Manipulate heap layout: allocate and subsequently free a chunk of size %s.\n", session.GetOption("CHUNK_SIZE"))
			fmt.Printf("3. Reallocate memory covering the freed chunk to overwrite function pointers with %s.\n", session.GetOption("MAGIC_FUNC"))
			fmt.Println("4. Trigger Use-After-Free condition to redirect code execution flow.")
		case "web_lfi":
			fmt.Printf("1. Transmit HTTP request containing a malicious User-Agent (<?php system('%s'); ?>) to %s.\n", session.GetOption("PAYLOAD_CMD"), session.GetOption("TARGET_URL"))
			fmt.Printf("2. Exploit Local File Inclusion by referencing the poisoned log file at %s.\n", session.GetOption("LOG_PATH"))
			fmt.Println("3. Achieve Remote Code Execution parsing the poisoned PHP log entries.")
		case "web_sqli":
			fmt.Printf("1. Target SQL Injection vulnerability at %s.\n", session.GetOption("TARGET_URL"))
			fmt.Printf("2. Inject UNION SELECT query leveraging INTO OUTFILE to drop a persistent web shell named %s at %s.\n", session.GetOption("SHELL_NAME"), session.GetOption("WEB_ROOT"))
			fmt.Println("3. Access the deployed web shell endpoint to execute arbitrary system commands.")
		case "web_ssti":
			fmt.Printf("1. Target Server-Side Template Injection vulnerability at %s.\n", session.GetOption("TARGET_URL"))
			fmt.Printf("2. Inject Jinja2/Python payload: os.popen('%s').read().\n", session.GetOption("PAYLOAD_CMD"))
			fmt.Println("3. Retrieve command execution output seamlessly from the HTTP response.")
		}
		fmt.Println("====================================")

		// Action Menu
		fmt.Println("\nAvailable Actions:")
		fmt.Println("[1] Generate Exploit Script")
		fmt.Println("[2] Reconfigure Parameters")
		fmt.Println("[3] Return to Exploit Database")

		l.SetPrompt("Action Selection > ")
		act, err := l.Readline()
		if err != nil {
			return
		}
		act = strings.TrimSpace(act)

		if act == "1" {
			err := core.GenerateExploit(session)
			if err != nil {
				fmt.Printf("[-] Exploit generation failed: %v\n", err)
			}
			fmt.Println("\n[+] Operation completed. Press Enter to continue...")
			l.Readline()
			clearScreen()
			printBanner()
			break
		} else if act == "2" {
			fmt.Println("[*] Reinitializing Interactive Configuration Wizard...")
			continue
		} else {
			clearScreen()
			printBanner()
			break
		}
	}
}
