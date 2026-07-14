"""
ViperForge v2.0 — Qt Style Sheet Theme
Cyberpunk dark neon theme constants and QSS styles.
"""

# ── Color palette ──────────────────────────────────────────────────────────────
BG_DEEP      = "#07070f"
BG_PANEL     = "#0d0d1a"
BG_CARD      = "#111122"
BG_HOVER     = "#1a1a30"
BG_SELECTED  = "#1e1e3a"

ACCENT_RED   = "#e63946"
ACCENT_GREEN = "#00ff88"
ACCENT_BLUE  = "#00b4d8"
ACCENT_GOLD  = "#ffd60a"
ACCENT_PURPLE= "#9b5de5"

TEXT_PRIMARY = "#e8e8f0"
TEXT_DIM     = "#666680"
TEXT_CODE    = "#a8ff78"

BORDER_DARK  = "#1e1e35"
BORDER_GLOW  = "#e63946"

CATEGORY_QSS_COLORS = {
    "Binary Exploitation":      "#e63946",
    "Web Exploitation":         "#f4a261",
    "Privilege Escalation":     "#2ec4b6",
    "Network Attacks":          "#9b5de5",
    "Cryptography":             "#fee440",
    "Active Directory":         "#00b4d8",
    "Exploit Builder (0-Day)": "#00ff88",
}

# ── Main window QSS ──────────────────────────────────────────────────────────
MAIN_QSS = f"""
/* ── Global ─────────────────────────────────────────────────────────────── */
QWidget {{
    background-color: {BG_DEEP};
    color: {TEXT_PRIMARY};
    font-family: "JetBrains Mono", "Consolas", "Courier New", monospace;
    font-size: 13px;
}}

QMainWindow {{
    background-color: {BG_DEEP};
}}

/* ── Splitter ────────────────────────────────────────────────────────────── */
QSplitter::handle {{
    background-color: {BORDER_DARK};
    width: 2px;
}}

/* ── ScrollBars ──────────────────────────────────────────────────────────── */
QScrollBar:vertical {{
    background: {BG_PANEL};
    width: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: {ACCENT_RED};
    border-radius: 4px;
    min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: {BG_PANEL};
    height: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal {{
    background: {ACCENT_RED};
    border-radius: 4px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* ── LineEdit / TextEdit ─────────────────────────────────────────────────── */
QLineEdit {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER_DARK};
    border-radius: 4px;
    padding: 5px 8px;
    color: {TEXT_PRIMARY};
    selection-background-color: {ACCENT_RED};
}}
QLineEdit:focus {{
    border: 1px solid {ACCENT_RED};
}}

QPlainTextEdit, QTextEdit {{
    background-color: {BG_PANEL};
    border: 1px solid {BORDER_DARK};
    border-radius: 6px;
    color: {TEXT_CODE};
    font-family: "JetBrains Mono", "Consolas", monospace;
    font-size: 12px;
    padding: 8px;
}}

/* ── Labels ──────────────────────────────────────────────────────────────── */
QLabel {{
    color: {TEXT_PRIMARY};
    background: transparent;
}}
QLabel#section_title {{
    color: {ACCENT_RED};
    font-size: 11px;
    font-weight: bold;
    letter-spacing: 2px;
    padding: 4px 0px;
}}

/* ── Buttons ─────────────────────────────────────────────────────────────── */
QPushButton {{
    background-color: {BG_CARD};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_DARK};
    border-radius: 6px;
    padding: 7px 16px;
    font-weight: bold;
}}
QPushButton:hover {{
    background-color: {BG_HOVER};
    border-color: {ACCENT_RED};
    color: {ACCENT_RED};
}}
QPushButton:pressed {{
    background-color: {ACCENT_RED};
    color: white;
}}
QPushButton#btn_generate {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #8b0000, stop:1 {ACCENT_RED});
    color: white;
    font-size: 14px;
    font-weight: bold;
    border: none;
    border-radius: 8px;
    padding: 12px 24px;
    letter-spacing: 1px;
}}
QPushButton#btn_generate:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {ACCENT_RED}, stop:1 #ff6b6b);
}}
QPushButton#btn_clear_canvas {{
    background-color: transparent;
    border: 1px solid {BORDER_DARK};
    color: {TEXT_DIM};
    padding: 5px 12px;
    font-size: 11px;
}}
QPushButton#btn_clear_canvas:hover {{
    border-color: {ACCENT_GOLD};
    color: {ACCENT_GOLD};
}}

/* ── Palette sidebar ─────────────────────────────────────────────────────── */
QWidget#palette_panel {{
    background-color: {BG_PANEL};
    border-right: 2px solid {BORDER_DARK};
}}
QTreeWidget {{
    background-color: {BG_PANEL};
    border: none;
    outline: 0;
    padding: 4px;
}}
QTreeWidget::item {{
    padding: 5px 4px;
    border-radius: 4px;
    margin: 1px 0;
}}
QTreeWidget::item:hover {{
    background-color: {BG_HOVER};
}}
QTreeWidget::item:selected {{
    background-color: {BG_SELECTED};
    color: {ACCENT_RED};
}}
QTreeWidget::branch {{
    background: transparent;
}}

/* ── Canvas / Graphics ───────────────────────────────────────────────────── */
QGraphicsView {{
    background-color: {BG_DEEP};
    border: none;
}}

/* ── Right panel ─────────────────────────────────────────────────────────── */
QWidget#right_panel {{
    background-color: {BG_PANEL};
    border-left: 2px solid {BORDER_DARK};
}}

/* ── Combo box ───────────────────────────────────────────────────────────── */
QComboBox {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER_DARK};
    border-radius: 4px;
    padding: 5px 8px;
    color: {TEXT_PRIMARY};
}}
QComboBox::drop-down {{
    border: none;
    padding-right: 8px;
}}
QComboBox QAbstractItemView {{
    background-color: {BG_CARD};
    border: 1px solid {ACCENT_RED};
    selection-background-color: {BG_SELECTED};
}}

/* ── Tooltip ─────────────────────────────────────────────────────────────── */
QToolTip {{
    background-color: {BG_CARD};
    color: {TEXT_PRIMARY};
    border: 1px solid {ACCENT_RED};
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 12px;
}}

/* ── Tab bar ─────────────────────────────────────────────────────────────── */
QTabBar::tab {{
    background: {BG_PANEL};
    color: {TEXT_DIM};
    padding: 6px 16px;
    border: none;
    border-bottom: 2px solid transparent;
}}
QTabBar::tab:selected {{
    color: {ACCENT_RED};
    border-bottom: 2px solid {ACCENT_RED};
}}
QTabBar::tab:hover {{
    color: {TEXT_PRIMARY};
}}
QTabWidget::pane {{
    border: none;
    background: {BG_PANEL};
}}
"""


def category_badge_style(category: str) -> str:
    """Returns block badge style with category color."""
    color = CATEGORY_QSS_COLORS.get(category, "#ffffff")
    return (
        f"background-color: {color}22;"
        f"border: 1px solid {color};"
        f"border-radius: 4px;"
        f"color: {color};"
        f"padding: 2px 6px;"
        f"font-size: 10px;"
        f"font-weight: bold;"
    )
