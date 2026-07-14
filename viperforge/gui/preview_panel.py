"""
ViperForge v2.0 — Preview Panel (Right Panel - Bottom)
Chain-aware live Python exploit code preview.
"""

import re
try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel,
        QPlainTextEdit, QFrame, QPushButton,
    )
    from PyQt6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat
    from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve
    _PY6 = True
except ImportError:
    from PyQt5.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel,
        QPlainTextEdit, QFrame, QPushButton,
    )
    from PyQt5.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat
    from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve
    _PY6 = False

from .theme import (
    BG_PANEL, BG_DEEP, ACCENT_RED, TEXT_DIM, BORDER_DARK,
    TEXT_CODE, ACCENT_GOLD, ACCENT_GREEN, ACCENT_BLUE, TEXT_PRIMARY,
)


class PythonHighlighter(QSyntaxHighlighter):
    """Rich Python syntax highlighter."""

    def __init__(self, document):
        super().__init__(document)
        self._rules = []

        def add(pattern: str, color: str, bold: bool = False, italic: bool = False):
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(color))
            if bold:
                fmt.setFontWeight(700)
            if italic:
                fmt.setFontItalic(True)
            self._rules.append((re.compile(pattern), fmt))

        # Section comment headers (# ── ... ──)
        add(r"#\s*[─═]+.*", "#3d4a6b", italic=True)
        # Comment
        add(r"#[^\n]*", "#5a6880", italic=True)
        # Shebang
        add(r"^#!.*", "#888888", italic=True)

        # Keyword
        kws = (r"\b(def|class|import|from|return|if|elif|else|for|while|"
               r"try|except|finally|with|as|pass|break|continue|lambda|yield|"
               r"in|not|and|or|is|raise|global|nonlocal|del|assert|async|await)\b")
        add(kws, "#ff79c6", bold=True)

        # Built-in constants
        add(r"\b(True|False|None)\b", "#bd93f9", bold=True)

        # Built-in functions
        add(r"\b(print|len|range|str|int|float|bytes|bytearray|list|dict|set|"
            r"tuple|type|isinstance|eval|exec|open|input|repr|format|"
            r"enumerate|zip|map|filter|sorted|reversed|sum|min|max|abs|"
            r"hasattr|getattr|setattr|vars|dir)\b(?=\s*\()", "#8be9fd")

        # CTX special highlight
        add(r"\bCTX\b", "#00ff88", bold=True)

        # String (triple first)
        add(r'"""[\s\S]*?"""', "#f1fa8c")
        add(r"'''[\s\S]*?'''", "#f1fa8c")
        add(r'"[^"\\\n]*(\\.[^"\\\n]*)*"', "#f1fa8c")
        add(r"'[^'\\\n]*(\\.[^'\\\n]*)*'", "#f1fa8c")
        add(r'f"[^"\\]*(\\.[^"\\]*)*"', "#ffb86c")
        add(r"f'[^'\\]*(\\.[^'\\]*)*'", "#ffb86c")

        # Hex / numbers
        add(r"\b0x[0-9a-fA-F]+\b", "#bd93f9")
        add(r"\b\d+\.?\d*\b", "#bd93f9")

        # Decorator
        add(r"@[A-Za-z_][A-Za-z0-9_.]*", ACCENT_RED)

        # Function / method call
        add(r"\b[A-Za-z_][A-Za-z0-9_]*(?=\s*\()", "#50fa7b")

        # Type hints / class names (CamelCase)
        add(r"\b[A-Z][A-Za-z0-9_]+\b", "#8be9fd")

    def highlightBlock(self, text: str) -> None:
        for pattern, fmt in self._rules:
            for m in pattern.finditer(text):
                self.setFormat(m.start(), m.end() - m.start(), fmt)


class PreviewPanel(QWidget):
    """
    Chain-aware live preview of the Python exploit code.
    Shows single-block preview OR full chain output depending on canvas state.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("right_panel")
        self._mode = "single"   # "single" | "chain"
        self._line_count = 0
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Header ────────────────────────────────────────────────────
        header = QWidget()
        header.setFixedHeight(42)
        header.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #0a0a18, stop:1 {BG_PANEL});
            border-bottom: 1px solid {BORDER_DARK};
        """)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(14, 0, 10, 0)
        h_layout.setSpacing(8)

        # Mode icon + label
        self._mode_icon = QLabel("⚡")
        self._mode_icon.setStyleSheet("font-size: 14px; background: transparent;")
        h_layout.addWidget(self._mode_icon)

        self._title_lbl = QLabel("LIVE PREVIEW")
        self._title_lbl.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 10px; font-weight: bold; "
            f"letter-spacing: 2px; background: transparent;"
        )
        h_layout.addWidget(self._title_lbl)

        h_layout.addStretch()

        # Mode badge (SINGLE / CHAIN)
        self._mode_badge = QLabel("SINGLE")
        self._mode_badge.setStyleSheet(f"""
            background: #1a1a2e;
            color: {ACCENT_GOLD};
            border: 1px solid {ACCENT_GOLD}44;
            border-radius: 3px;
            padding: 1px 7px;
            font-size: 9px;
            font-weight: bold;
            letter-spacing: 1px;
        """)
        h_layout.addWidget(self._mode_badge)

        # Line count badge
        self._lines_badge = QLabel("0 lines")
        self._lines_badge.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 9px; "
            f"background: transparent; padding: 0 4px;"
        )
        h_layout.addWidget(self._lines_badge)

        layout.addWidget(header)

        # ── Code editor ───────────────────────────────────────────────
        self._editor = QPlainTextEdit()
        self._editor.setReadOnly(True)
        self._editor.setFont(QFont("JetBrains Mono", 10))
        self._editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self._editor.setStyleSheet(f"""
            QPlainTextEdit {{
                background: {BG_DEEP};
                border: none;
                color: {TEXT_CODE};
                padding: 10px 14px;
                selection-background-color: #303050;
            }}
        """)
        self._editor.setPlaceholderText(
            "# 🧩  Add blocks to the canvas and connect them.\n"
            "# \n"
            "# The complete chain exploit code will appear here\n"
            "# as you build your attack flow.\n"
            "# \n"
            "# ─── Quick Start ───────────────────────────────────────────\n"
            "#  1. Double-click a block from the left palette to add it.\n"
            "#  2. Click the ▼ connector at the bottom of each block\n"
            "#     and connect it to the next block.\n"
            "#  3. Fill in the parameters on the right panel.\n"
            "#  4. Hit GENERATE EXPLOIT to save the final script."
        )
        layout.addWidget(self._editor, 1)

        # Syntax highlighter
        self._highlighter = PythonHighlighter(self._editor.document())

    # ── Public API ────────────────────────────────────────────────────

    def set_code(self, code: str, mode: str = "single") -> None:
        """
        Update preview code.
        mode = "single" | "chain"
        """
        self._mode = mode
        self._editor.setPlainText(code)
        self._update_badges(code, mode)

    def set_chain_code(self, code: str) -> None:
        """Shortcut for chain mode."""
        self.set_code(code, "chain")

    def set_single_code(self, code: str) -> None:
        """Shortcut for single-block mode."""
        self.set_code(code, "single")

    def clear(self) -> None:
        self._editor.clear()
        self._update_badges("", "single")

    # ── Internal ──────────────────────────────────────────────────────

    def _update_badges(self, code: str, mode: str) -> None:
        lines = code.count("\n") + (1 if code.strip() else 0)
        self._lines_badge.setText(f"{lines} lines")

        if mode == "chain":
            self._mode_badge.setText("🔗 CHAIN")
            self._mode_badge.setStyleSheet(f"""
                background: #002a18;
                color: {ACCENT_GREEN};
                border: 1px solid {ACCENT_GREEN}55;
                border-radius: 3px;
                padding: 1px 7px;
                font-size: 9px;
                font-weight: bold;
                letter-spacing: 1px;
            """)
            self._mode_icon.setText("🔗")
            self._title_lbl.setText("CHAIN OUTPUT")
            self._title_lbl.setStyleSheet(
                f"color: {ACCENT_GREEN}; font-size: 10px; font-weight: bold; "
                f"letter-spacing: 2px; background: transparent; opacity: 0.8;"
            )
        else:
            self._mode_badge.setText("⚡ SINGLE")
            self._mode_badge.setStyleSheet(f"""
                background: #1a1a2e;
                color: {ACCENT_GOLD};
                border: 1px solid {ACCENT_GOLD}44;
                border-radius: 3px;
                padding: 1px 7px;
                font-size: 9px;
                font-weight: bold;
                letter-spacing: 1px;
            """)
            self._mode_icon.setText("⚡")
            self._title_lbl.setText("LIVE PREVIEW")
            self._title_lbl.setStyleSheet(
                f"color: {TEXT_DIM}; font-size: 10px; font-weight: bold; "
                f"letter-spacing: 2px; background: transparent;"
            )
