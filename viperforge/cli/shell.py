"""
ViperForge v2.0 — CLI Shell (--cli mode)
Python port of Go's shell.go, using the Rich library.
"""

import os
import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from rich.text import Text
from rich import box

from viperforge.registry import REGISTRY, all_categories, get_by_category, CATEGORY_ICONS, CATEGORY_COLORS
from viperforge.session import Session
from viperforge.engine import generate_single

console = Console()

BANNER = r"""
    ____   ____.__                     ___________                           
    \   \ /   /|__|_____   ___________ \_   _____/__________  ____   ____  
     \   Y   / |  \____ \_/ __ \_  __ \ |    __)/  _ \_  __ \/ ___\_/ __ \ 
      \     /  |  |  |_> >  ___/|  | \/ |     \(  <_> )  | \/ /_/  >  ___/ 
       \___/   |__|   __/ \___  >__|    \___  / \____/|__|  \___  / \___  >
                  |__|        \/            \/             /_____/      \/ 
"""


def print_banner() -> None:
    console.print(f"[bold red]{BANNER}[/bold red]")
    console.print(
        "                           [dim]Red Team Exploit Factory[/dim] "
        "[bold red]v2.1.0-beta[/bold red]\n"
    )


def print_categories() -> None:
    table = Table(
        title="[bold red]Exploit Categories[/bold red]",
        box=box.DOUBLE_EDGE,
        border_style="red",
        show_header=False,
        min_width=50,
    )
    table.add_column("idx", style="bold yellow", width=4)
    table.add_column("icon", width=3)
    table.add_column("name", style="bold white")

    for i, cat in enumerate(all_categories(), 1):
        icon = CATEGORY_ICONS.get(cat, "⚡")
        table.add_row(f"[{i}]", icon, cat)

    console.print(table)
    console.print("  [dim][exit] Terminate Session[/dim]\n")


def print_category_exploits(cat: str) -> None:
    exploits = get_by_category(cat)
    icon     = CATEGORY_ICONS.get(cat, "⚡")
    color    = CATEGORY_COLORS.get(cat, "#ffffff").lstrip("#")

    table = Table(
        title=f"[bold]#{icon} {cat}[/bold]",
        box=box.ROUNDED,
        border_style="dim",
        show_header=True,
    )
    table.add_column("#",    style="bold yellow", width=4)
    table.add_column("Module",  style="bold white", min_width=22)
    table.add_column("Description", style="dim white")

    for i, e in enumerate(exploits, 1):
        table.add_row(f"[{i}]", e.name, e.description)

    console.print(table)
    console.print("  [dim][0/back] Back  [clear] Clear  [exit] Exit[/dim]\n")


def run_wizard(session: Session, exploit_def) -> None:
    console.rule(f"[bold red]⚡ {exploit_def.name}[/bold red]")
    console.print(f"[dim]{exploit_def.description}[/dim]\n")

    session.set_exploit(exploit_def)

    while True:
        # Parameter collection
        for opt in exploit_def.options:
            default_display = f"[{opt.default}]" if opt.default else "[empty]"
            val = Prompt.ask(
                f"  [yellow]{opt.name}[/yellow] [dim]{opt.description} {default_display}[/dim]",
                default=opt.default,
                console=console,
            )
            if val:
                session.set_option(opt.name, val)

        # Preview
        console.rule("[bold]Exploit Preview[/bold]")
        _print_preview(session, exploit_def)

        # Action
        console.print("\n[bold]Actions:[/bold]")
        console.print("  [bold green][1][/bold green] Generate Exploit Script")
        console.print("  [bold yellow][2][/bold yellow] Reconfigure Parameters")
        console.print("  [bold red][3][/bold red] Return to Module List\n")

        act = Prompt.ask("  Action", choices=["1", "2", "3"], default="1", console=console)

        if act == "1":
            try:
                out = generate_single(session)
                console.print(f"\n[bold green][+] Exploit generated:[/bold green] [cyan]{out}[/cyan]")
            except Exception as e:
                console.print(f"[bold red][-] Error:[/bold red] {e}")
            Prompt.ask("\n  [dim]Press Enter to continue[/dim]", default="", console=console)
            break
        elif act == "2":
            console.print("[*] Reinitializing wizard...\n")
            session.set_exploit(exploit_def)
            continue
        else:
            break


def _print_preview(session: Session, exploit_def) -> None:
    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    table.add_column("key",   style="bold yellow", width=20)
    table.add_column("value", style="white")

    table.add_row("Module",      exploit_def.name)
    table.add_row("Description", exploit_def.description)
    table.add_row("Category",    exploit_def.category)
    table.add_row("─" * 18,      "─" * 30)

    for opt in exploit_def.options:
        val = session.get_option(opt.name) or f"[dim]{opt.default}[/dim]"
        table.add_row(opt.name, val)

    console.print(table)


def _wizard_params_only(session: Session, exploit_def) -> None:
    os.system("cls" if sys.platform == "win32" else "clear")
    print_banner()
    console.rule(f"[bold red]⚡ Configure {exploit_def.name}[/bold red]")
    console.print(f"[dim]{exploit_def.description}[/dim]\n")

    session.set_exploit(exploit_def)
    for opt in exploit_def.options:
        default_display = f"[{opt.default}]" if opt.default else "[empty]"
        val = Prompt.ask(
            f"  [yellow]{opt.name}[/yellow] [dim]{opt.description} {default_display}[/dim]",
            default=opt.default,
            console=console,
        )
        if val:
            session.set_option(opt.name, val)


def _chain_add_block(sessions: list[Session]) -> None:
    categories = all_categories()
    while True:
        os.system("cls" if sys.platform == "win32" else "clear")
        print_banner()
        print_categories()
        choice = Prompt.ask(
            "[bold red]ViperForge[/bold red] (Add Block) [dim]>[/dim]",
            console=console,
        ).strip().lower()

        if choice in ("0", "back", "exit", "quit"):
            break
        if choice.isdigit() and 1 <= int(choice) <= len(categories):
            cat = categories[int(choice) - 1]
            while True:
                os.system("cls" if sys.platform == "win32" else "clear")
                print_banner()
                print_category_exploits(cat)
                exp_choice = Prompt.ask(
                    f"[bold red]ViperForge[/bold red] ([cyan]{cat}[/cyan]) [dim]>[/dim]",
                    console=console,
                ).strip().lower()
                
                if exp_choice in ("0", "back"):
                    break
                
                exploits = get_by_category(cat)
                if exp_choice.isdigit() and 1 <= int(exp_choice) <= len(exploits):
                    exp = exploits[int(exp_choice) - 1]
                    new_session = Session()
                    _wizard_params_only(new_session, exp)
                    sessions.append(new_session)
                    return


def _chain_remove_block(sessions: list[Session]) -> None:
    choice = Prompt.ask(f"  Remove block index (1-{len(sessions)})", console=console)
    if choice.isdigit() and 1 <= int(choice) <= len(sessions):
        idx = int(choice) - 1
        removed = sessions.pop(idx)
        console.print(f"[*] Removed {removed.active_exploit.name}")
        import time; time.sleep(1)


def _chain_generate(sessions: list[Session]) -> None:
    from viperforge.engine import generate_chain
    try:
        out = generate_chain(sessions)
        console.print(f"\n[bold green][+] Chain exploit generated:[/bold green] [cyan]{out}[/cyan]")
    except Exception as e:
        console.print(f"[bold red][-] Error:[/bold red] {e}")
    Prompt.ask("\n  [dim]Press Enter to continue[/dim]", default="", console=console)


def _chain_mode_loop() -> None:
    sessions: list[Session] = []
    while True:
        os.system("cls" if sys.platform == "win32" else "clear")
        print_banner()
        console.print("[bold magenta]━━━ Chain Builder Mode ━━━[/bold magenta]\n")
        
        if not sessions:
            console.print("  [dim]Chain is currently empty. Add blocks to begin.[/dim]\n")
        else:
            table = Table(box=box.SIMPLE_HEAVY, show_header=True)
            table.add_column("#", style="bold yellow")
            table.add_column("Module", style="bold white")
            table.add_column("Category", style="cyan")
            for i, s in enumerate(sessions, 1):
                table.add_row(f"[{i}]", s.active_exploit.name, s.active_exploit.category)
            console.print(table)
            console.print("")
            
        console.print("[bold]Actions:[/bold]")
        console.print("  [bold green][1][/bold green] Add Block")
        if sessions:
            console.print("  [bold red][2][/bold red] Remove Block")
            console.print("  [bold yellow][3][/bold yellow] Generate Chain Script")
        console.print("  [dim][0] Back to Main Menu[/dim]\n")
        
        valid_choices = ["1", "0"]
        if sessions:
            valid_choices.extend(["2", "3"])
            
        act = Prompt.ask("  Action", choices=valid_choices, default="1", console=console)
        
        if act == "0":
            break
        elif act == "1":
            _chain_add_block(sessions)
        elif act == "2":
            _chain_remove_block(sessions)
        elif act == "3":
            _chain_generate(sessions)


def _single_mode_loop() -> None:
    categories   = all_categories()
    current_cat  = None
    session      = Session()

    while True:
        if current_cat is None:
            print_categories()
            choice = Prompt.ask(
                "[bold red]ViperForge[/bold red] [dim]>[/dim]",
                console=console,
            ).strip().lower()

            if choice in ("0", "back", "exit", "quit"):
                break
            if choice == "clear":
                os.system("cls" if sys.platform == "win32" else "clear")
                print_banner()
                continue
            if choice.isdigit() and 1 <= int(choice) <= len(categories):
                current_cat = categories[int(choice) - 1]
                os.system("cls" if sys.platform == "win32" else "clear")
                print_banner()
            else:
                console.print("[red][-] Invalid selection.[/red]")
        else:
            exploits = get_by_category(current_cat)
            print_category_exploits(current_cat)
            choice = Prompt.ask(
                f"[bold red]ViperForge[/bold red] ([cyan]{current_cat}[/cyan]) [dim]>[/dim]",
                console=console,
            ).strip().lower()

            if choice in ("0", "back"):
                current_cat = None
                os.system("cls" if sys.platform == "win32" else "clear")
                print_banner()
                continue
            if choice in ("exit", "quit"):
                break
            if choice == "clear":
                os.system("cls" if sys.platform == "win32" else "clear")
                print_banner()
                continue
            if choice.isdigit() and 1 <= int(choice) <= len(exploits):
                exploit_def = exploits[int(choice) - 1]
                run_wizard(session, exploit_def)
                os.system("cls" if sys.platform == "win32" else "clear")
                print_banner()
            else:
                console.print("[red][-] Invalid selection.[/red]")


def start_cli() -> None:
    while True:
        os.system("cls" if sys.platform == "win32" else "clear")
        print_banner()

        console.print("[bold]Select Mode:[/bold]")
        console.print("  [bold cyan][1][/bold cyan] Single Exploit Mode")
        console.print("  [bold magenta][2][/bold magenta] Chain Builder Mode")
        console.print("  [dim][0] Exit[/dim]\n")
        
        choice = Prompt.ask("  Mode", choices=["1", "2", "0", "exit", "quit"], default="1", console=console)
        
        if choice in ("0", "exit", "quit"):
            console.print("[*] Terminating ViperForge. Goodbye.")
            break
            
        if choice == "1":
            _single_mode_loop()
        elif choice == "2":
            _chain_mode_loop()


