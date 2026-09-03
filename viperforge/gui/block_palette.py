"""
ViperForge v2.0 -- Block Palette (Left Sidebar)
Clean QScrollArea based palette. No QTreeWidget + setItemWidget hacks.
Proper hover via enterEvent / leaveEvent on QFrame subclasses.
"""

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel,
        QLineEdit, QScrollArea, QFrame, QSizePolicy,
    )
    from PyQt6.QtCore import Qt, pyqtSignal
    _PY6 = True
except ImportError:
    from PyQt5.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel,
        QLineEdit, QScrollArea, QFrame, QSizePolicy,
    )
    from PyQt5.QtCore import Qt, pyqtSignal
    _PY6 = False


from viperforge.registry import REGISTRY, all_categories, CATEGORY_ICONS, CATEGORY_COLORS, ExploitDef
from .theme import BG_PANEL, BG_CARD, TEXT_PRIMARY, TEXT_DIM, ACCENT_RED, BORDER_DARK
import qtawesome as qta

_PRIORITY_CAT = "Exploit Builder (0-Day)"

_CAT_DESC = {
    "Exploit Builder (0-Day)": "Build exploits block by block",
    "Binary Exploitation":     "BOF - ROP - Heap - UAF",
    "Web Exploitation":        "LFI - SQLi - SSTI - XSS",
    "Privilege Escalation":    "SUID - sudo abuse",
    "Network Attacks":         "FTP - SMB - relay",
    "Cryptography":            "Padding oracle - hash",
    "Active Directory":        "Kerberoast - AS-REP",
    "Macros":                  "User-defined sub-routines",
}

# --- Exploit item ---

class _ExploitItem(QFrame):
    """Single exploit row -- proper hover via enterEvent / leaveEvent."""

    dclicked = pyqtSignal(object)

    def __init__(self, exploit, parent=None):
        super().__init__(parent)
        self.exploit = exploit
        self._color  = CATEGORY_COLORS.get(exploit.category, "#aaaaff")
        self._build()

    def _build(self):
        self.setObjectName("ExploitItem")
        self.setFixedHeight(44)
        if _PY6:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setCursor(Qt.PointingHandCursor)
        self._set_style(False)

        hl = QHBoxLayout(self)
        hl.setContentsMargins(18, 0, 10, 0)
        hl.setSpacing(8)

        self._arrow = QLabel(">")
        self._arrow.setFixedWidth(10)
        self._arrow.setStyleSheet(
            f"color: {self._color}55; font-size: 13px; background: transparent; font-weight: bold;"
        )
        hl.addWidget(self._arrow)

        vl = QVBoxLayout()
        vl.setSpacing(1)
        vl.setContentsMargins(0, 0, 0, 0)

        self._name = QLabel(self.exploit.name)
        self._name.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: 11px; font-weight: bold; background: transparent;"
        )
        vl.addWidget(self._name)

        desc = self.exploit.description
        if len(desc) > 40:
            desc = desc[:38] + "..."
        self._desc = QLabel(desc)
        self._desc.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 9px; background: transparent;"
        )
        vl.addWidget(self._desc)
        hl.addLayout(vl, 1)

        n = len(self.exploit.options)
        if n > 0:
            pill = QLabel(f"{n}p")
            pill.setFixedHeight(14)
            pill.setStyleSheet(
                f"color: {self._color}99; border: 1px solid {self._color}44; "
                f"border-radius: 5px; padding: 0 5px; font-size: 8px; background: transparent;"
            )
            hl.addWidget(pill)

    def _set_style(self, hovered: bool):
        if hovered:
            self.setStyleSheet(
                f"#ExploitItem {{ background: {self._color}12; "
                f"border-left: 2px solid {self._color}; "
                f"border-bottom: 1px solid {BORDER_DARK}33; }}"
            )
        else:
            self.setStyleSheet(
                f"#ExploitItem {{ background: transparent; "
                f"border-left: 2px solid transparent; "
                f"border-bottom: 1px solid {BORDER_DARK}33; }}"
            )

    def enterEvent(self, event):
        self._set_style(True)
        self._arrow.setStyleSheet(
            f"color: {self._color}; font-size: 13px; background: transparent; font-weight: bold;"
        )
        self._name.setStyleSheet(
            f"color: {self._color}; font-size: 11px; font-weight: bold; background: transparent;"
        )
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._set_style(False)
        self._arrow.setStyleSheet(
            f"color: {self._color}55; font-size: 13px; background: transparent; font-weight: bold;"
        )
        self._name.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: 11px; font-weight: bold; background: transparent;"
        )
        super().leaveEvent(event)

    def mouseDoubleClickEvent(self, event):
        self.dclicked.emit(self.exploit)
        super().mouseDoubleClickEvent(event)


# --- Category header ---

class _CatHeader(QFrame):
    """Clickable category header with collapse/expand."""

    def __init__(self, cat: str, count: int, parent=None):
        super().__init__(parent)
        self.cat       = cat
        self._color    = CATEGORY_COLORS.get(cat, "#ffffff")
        self._icon     = CATEGORY_ICONS.get(cat, "fa5s.bolt")
        self._count    = count
        self._expanded = (cat == _PRIORITY_CAT)
        self._container = None
        self._build()

    def set_container(self, w):
        self._container = w
        w.setVisible(self._expanded)

    def _build(self):
        self.setObjectName("CatHeader")
        self.setFixedHeight(46)
        if _PY6:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setCursor(Qt.PointingHandCursor)
        self._set_style(False)

        hl = QHBoxLayout(self)
        hl.setContentsMargins(10, 0, 10, 0)
        hl.setSpacing(7)

        icon = QLabel()
        icon.setFixedWidth(22)
        icon.setPixmap(qta.icon(self._icon, color=self._color).pixmap(15, 15))
        icon.setStyleSheet("background: transparent;")
        hl.addWidget(icon)

        vl = QVBoxLayout()
        vl.setSpacing(0)
        vl.setContentsMargins(0, 0, 0, 0)

        name_lbl = QLabel(self.cat)
        name_lbl.setStyleSheet(
            f"color: {self._color}; font-weight: bold; font-size: 10px; "
            f"letter-spacing: 0.5px; background: transparent;"
        )
        if _PY6:
            name_lbl.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        else:
            name_lbl.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        vl.addWidget(name_lbl)

        desc = _CAT_DESC.get(self.cat, "")
        if desc:
            d = QLabel(desc)
            d.setStyleSheet(f"color: {TEXT_DIM}; font-size: 9px; background: transparent;")
            if _PY6:
                d.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            else:
                d.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
            vl.addWidget(d)

        hl.addLayout(vl, 1)

        badge = QLabel(str(self._count))
        badge.setFixedWidth(28)
        if _PY6:
            badge.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        else:
            badge.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        badge.setStyleSheet(
            f"color: {self._color}cc; font-size: 10px; font-weight: bold; "
            f"background: transparent;"
        )
        hl.addWidget(badge)

        self._arrow_lbl = QLabel("v" if self._expanded else ">")
        self._arrow_lbl.setFixedWidth(14)
        self._arrow_lbl.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 10px; background: transparent;"
        )
        hl.addWidget(self._arrow_lbl)

    def _set_style(self, hovered: bool):
        bg = BG_CARD if hovered else BG_PANEL
        self.setStyleSheet(
            f"#CatHeader {{ background: {bg}; "
            f"border-left: 3px solid {self._color}; "
            f"border-bottom: 1px solid {BORDER_DARK}; }}"
        )

    def enterEvent(self, event):
        self._set_style(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._set_style(False)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        self._expanded = not self._expanded
        self._arrow_lbl.setText("v" if self._expanded else ">")
        if self._container:
            self._container.setVisible(self._expanded)
        super().mousePressEvent(event)


# --- Main palette widget ---

class BlockPalette(QWidget):
    """Left sidebar: categorized exploit block palette."""

    exploit_selected = pyqtSignal(ExploitDef)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("palette_panel")
        self.setMinimumWidth(230)
        self.setMaximumWidth(400)
        if _PY6:
            self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        else:
            self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self._build_ui()
        self._populate()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QWidget()
        header.setFixedHeight(52)
        header.setStyleSheet(f"background: {BG_PANEL}; border-bottom: 2px solid {ACCENT_RED};")
        h_hl = QHBoxLayout(header)
        h_hl.setContentsMargins(12, 0, 12, 0)
        h_hl.setSpacing(8)

        title = QLabel("EXPLOIT BLOCKS")
        title.setStyleSheet(
            f"color: {ACCENT_RED}; font-size: 11px; font-weight: bold; "
            f"letter-spacing: 2px; background: transparent;"
        )
        h_hl.addWidget(title)
        h_hl.addStretch()

        total = QLabel(str(len(REGISTRY)))
        total.setStyleSheet(
            f"color: {ACCENT_RED}aa; font-size: 11px; font-weight: bold; "
            f"background: transparent; padding: 0 4px;"
        )
        h_hl.addWidget(total)
        layout.addWidget(header)

        # Search bar
        sw = QWidget()
        sw.setFixedHeight(36)
        sw.setStyleSheet(f"background: {BG_CARD}; border-bottom: 1px solid {BORDER_DARK};")
        sw_hl = QHBoxLayout(sw)
        sw_hl.setContentsMargins(10, 0, 10, 0)
        sw_hl.setSpacing(6)

        loup = QLabel("search:")
        loup.setStyleSheet(f"font-size: 10px; background: transparent; color: {TEXT_DIM};")
        sw_hl.addWidget(loup)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search modules...")
        self._search.setStyleSheet(
            f"background: transparent; border: none; color: {TEXT_PRIMARY}; font-size: 12px;"
        )
        self._search.textChanged.connect(self._filter)
        sw_hl.addWidget(self._search, 1)
        layout.addWidget(sw)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        if _PY6:
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        else:
            scroll.setFrameShape(QFrame.NoFrame)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            f"QScrollArea {{ background: {BG_PANEL}; border: none; }}"
            f"QScrollBar:vertical {{ background: {BG_PANEL}; width: 4px; }}"
            f"QScrollBar::handle:vertical {{ background: {BORDER_DARK}; border-radius: 2px; min-height: 20px; }}"
            f"QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}"
        )

        self._content = QWidget()
        self._content.setStyleSheet(f"background: {BG_PANEL};")
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(0)
        self._content_layout.addStretch()

        scroll.setWidget(self._content)
        layout.addWidget(scroll, 1)

        # Footer
        footer = QWidget()
        footer.setFixedHeight(26)
        footer.setStyleSheet(f"background: {BG_CARD}; border-top: 1px solid {BORDER_DARK};")
        f_hl = QHBoxLayout(footer)
        f_hl.setContentsMargins(10, 0, 10, 0)
        hint = QLabel("double-click to add  |  use arrow to chain")
        hint.setStyleSheet(f"color: {TEXT_DIM}; font-size: 9px; background: transparent;")
        f_hl.addWidget(hint)
        layout.addWidget(footer)

    def _populate(self, filter_text: str = ""):
        # Initial population of all categories and exploits
        self._categories = []
        
        cats = all_categories()
        if _PRIORITY_CAT in cats:
            cats = [_PRIORITY_CAT] + [c for c in cats if c != _PRIORITY_CAT]

        for cat in cats:
            exploits = [e for e in REGISTRY if e.category == cat]
            if not exploits:
                continue

            cat_header = _CatHeader(cat, len(exploits))
            self._content_layout.insertWidget(self._content_layout.count() - 1, cat_header)

            container = QWidget()
            container.setStyleSheet(f"background: {BG_PANEL};")
            c_vl = QVBoxLayout(container)
            c_vl.setContentsMargins(0, 0, 0, 0)
            c_vl.setSpacing(0)
            
            items = []
            for exploit in exploits:
                row = _ExploitItem(exploit)
                row.dclicked.connect(self._on_dclick)
                c_vl.addWidget(row)
                items.append(row)

            cat_header.set_container(container)
            self._content_layout.insertWidget(self._content_layout.count() - 1, container)
            
            # Store badge label directly on header for quick access
            cat_header._badge = cat_header.layout().itemAt(2).widget()
            
            self._categories.append({
                'header': cat_header,
                'container': container,
                'items': items
            })

    def _filter(self, text: str):
        ft = text.strip().lower()
        for cat_data in self._categories:
            visible_count = 0
            for row in cat_data['items']:
                exp = row.exploit
                if not ft or ft in exp.name.lower() or ft in exp.description.lower():
                    row.setVisible(True)
                    visible_count += 1
                else:
                    row.setVisible(False)
            
            # Update header badge
            cat_data['header']._count = visible_count
            cat_data['header']._badge.setText(str(visible_count))
            
            # Show/Hide category based on matches
            if visible_count == 0:
                cat_data['header'].setVisible(False)
                cat_data['container'].setVisible(False)
            else:
                cat_data['header'].setVisible(True)
                if ft:
                    # If searching, force expand the container
                    cat_data['container'].setVisible(True)
                    cat_data['header']._expanded = True
                    cat_data['header']._arrow_lbl.setText("v")
                else:
                    # If empty search, respect the stored expanded state
                    cat_data['container'].setVisible(cat_data['header']._expanded)
                    cat_data['header']._arrow_lbl.setText("v" if cat_data['header']._expanded else ">")

    def _on_dclick(self, exploit):
        self.exploit_selected.emit(exploit)

    def refresh_macros(self):
        """Reload saved macros into the palette (called after a macro is saved)."""
        from viperforge.macro import list_macros
        from viperforge.registry import CATEGORY_COLORS, CATEGORY_ICONS, ExploitDef, ExploitOption

        # Remove existing Macros category if present
        for cat_data in list(self._categories):
            if cat_data['header'].cat == 'Macros':
                cat_data['header'].setParent(None)
                cat_data['container'].setParent(None)
                self._categories.remove(cat_data)
                break

        macros = list_macros()
        if not macros:
            return

        # Create virtual ExploitDefs for macros
        macro_exploits = []
        for m in macros:
            vdef = ExploitDef(
                id=-1,
                name=m.name,
                category="Macros",
                description=m.description or f"Macro ({len(m.blocks)} blocks)",
                template="",
                options=[],
            )
            # Attach macro_def for later use
            vdef._macro_def = m
            macro_exploits.append(vdef)

        cat_header = _CatHeader("Macros", len(macro_exploits))
        self._content_layout.insertWidget(self._content_layout.count() - 1, cat_header)

        container = QWidget()
        container.setStyleSheet(f"background: {BG_PANEL};")
        c_vl = QVBoxLayout(container)
        c_vl.setContentsMargins(0, 0, 0, 0)
        c_vl.setSpacing(0)

        items = []
        for vdef in macro_exploits:
            row = _ExploitItem(vdef)
            row.dclicked.connect(self._on_dclick)
            c_vl.addWidget(row)
            items.append(row)

        cat_header.set_container(container)
        self._content_layout.insertWidget(self._content_layout.count() - 1, container)

        cat_header._badge = cat_header.layout().itemAt(2).widget()

        self._categories.append({
            'header': cat_header,
            'container': container,
            'items': items,
        })
