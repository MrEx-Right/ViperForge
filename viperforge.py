#!/usr/bin/env python3
"""
ViperForge v2.0 — Entry Point
  python viperforge.py          → GUI (default)
  python viperforge.py --cli    → CLI wizard
"""

import sys
import argparse
import os


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="viperforge",
        description="ViperForge v2.0 — Block-Based Exploit Builder",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python viperforge.py           Launch the GUI (default)
  python viperforge.py --cli     Launch the interactive CLI wizard
        """,
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Launch the interactive CLI wizard instead of the GUI",
    )
    args = parser.parse_args()

    if args.cli:
        # ── CLI mode ──────────────────────────────────────────────────────
        from viperforge.cli.shell import start_cli
        start_cli()
    else:
        # ── GUI mode ──────────────────────────────────────────────────────
        try:
            from PyQt6.QtWidgets import QApplication
            from PyQt6.QtGui import QFont, QFontDatabase
            from PyQt6.QtCore import Qt
        except ImportError:
            print("[!] PyQt6 not found. Install with:")
            print("    pip install PyQt6")
            sys.exit(1)

        # High-DPI support
        os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")

        app = QApplication(sys.argv)
        app.setApplicationName("ViperForge")
        app.setApplicationVersion("2.0")
        app.setOrganizationName("Red Team Tools")

        # Font
        app.setFont(QFont("Consolas", 11))

        from viperforge.gui.main_window import MainWindow
        win = MainWindow()
        win.show()

        sys.exit(app.exec())


if __name__ == "__main__":
    main()
