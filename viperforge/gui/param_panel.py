"""
ViperForge — Parameter Panel (Right Panel - Top)
Displays parameters of the selected block as a dynamic form.
"""

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel,
        QLineEdit, QScrollArea, QFrame, QSizePolicy,
    )
    from PyQt6.QtGui import QColor, QFont
    from PyQt6.QtCore import Qt, pyqtSignal
    _PY6 = True
except ImportError:
    from PyQt5.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel,
        QLineEdit, QScrollArea, QFrame, QSizePolicy,
    )
    from PyQt5.QtGui import QColor, QFont
    from PyQt5.QtCore import Qt, pyqtSignal
    _PY6 = False

def _text_format_rich():
    return Qt.TextFormat.RichText if _PY6 else Qt.RichText

from viperforge.session import Session
from viperforge.registry import ExploitDef, CATEGORY_COLORS, CATEGORY_ICONS
from .theme import (
    BG_PANEL, BG_CARD, TEXT_PRIMARY, TEXT_DIM,
    ACCENT_RED, BORDER_DARK,
)


class ParamPanel(QWidget):
    """
    Form displaying parameters of the selected block.
    Emits `param_changed` signal whenever a value changes.
    """

    param_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("right_panel")

        self._session:      Session | None     = None
        self._exploit_def:  ExploitDef | None  = None
        self._fields:       dict[str, QLineEdit] = {}

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Title ────────────────────────────────────────────────────────
        self._header = QWidget()
        self._header.setFixedHeight(56)
        self._header.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #1a0010, stop:1 {BG_PANEL});
            border-bottom: 2px solid {ACCENT_RED};
        """)
        h_layout = QVBoxLayout(self._header)
        h_layout.setContentsMargins(14, 8, 14, 8)

        self._module_label = QLabel("No Block Selected")
        self._module_label.setStyleSheet(f"color: {ACCENT_RED}; font-weight: bold; font-size: 13px; background: transparent;")
        h_layout.addWidget(self._module_label)

        self._cat_label = QLabel("")
        self._cat_label.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px; background: transparent;")
        h_layout.addWidget(self._cat_label)

        layout.addWidget(self._header)

        # ── Form with scroll area ──────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(f"background: {BG_PANEL};")

        self._form_widget = QWidget()
        self._form_widget.setStyleSheet(f"background: {BG_PANEL};")
        self._form_layout = QVBoxLayout(self._form_widget)
        self._form_layout.setContentsMargins(12, 12, 12, 12)
        self._form_layout.setSpacing(10)
        self._form_layout.addStretch()

        scroll.setWidget(self._form_widget)
        layout.addWidget(scroll, 1)

    def load_block(self, session: Session, exploit_def: ExploitDef) -> None:
        """Load parameters for a block."""
        self._session     = session
        self._exploit_def = exploit_def
        self._fields.clear()

        # Update header
        icon  = CATEGORY_ICONS.get(exploit_def.category, "⚡")
        color = CATEGORY_COLORS.get(exploit_def.category, ACCENT_RED)
        self._module_label.setText(f"{icon}  {exploit_def.name}")
        self._module_label.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 13px; background: transparent;")
        self._cat_label.setText(f"{exploit_def.category}  ·  {exploit_def.description}")

        # Clear old form
        while self._form_layout.count() > 1:
            item = self._form_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # New fields
        section_label = QLabel("⚙  PARAMETERS")
        section_label.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px; font-weight: bold; letter-spacing: 2px; padding: 4px 0;")
        self._form_layout.insertWidget(self._form_layout.count() - 1, section_label)

        for opt in exploit_def.options:
            row = QWidget()
            row.setStyleSheet(f"""
                background: {BG_CARD};
                border: 1px solid {BORDER_DARK};
                border-radius: 6px;
            """)
            row_layout = QVBoxLayout(row)
            row_layout.setContentsMargins(10, 8, 10, 8)
            row_layout.setSpacing(4)

            lbl = QLabel(f"{opt.name}  <span style='color:{TEXT_DIM}; font-size:10px;'>{opt.description}</span>")
            lbl.setTextFormat(_text_format_rich())
            lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 11px; font-weight: bold; background: transparent;")
            row_layout.addWidget(lbl)

            field = QLineEdit()
            val = session.get_option(opt.name)
            field.setText(val if val else opt.default)
            field.setPlaceholderText(opt.default or "")
            field.setStyleSheet(f"""
                background: {BG_PANEL};
                border: 1px solid {BORDER_DARK};
                border-radius: 4px;
                padding: 5px 8px;
                color: {TEXT_PRIMARY};
                font-size: 12px;
            """)
            field.textChanged.connect(lambda text, name=opt.name: self._on_field_changed(name, text))
            field.setObjectName(f"field_{opt.name}")
            row_layout.addWidget(field)

            self._fields[opt.name] = field
            self._form_layout.insertWidget(self._form_layout.count() - 1, row)

    def _on_field_changed(self, opt_name: str, text: str) -> None:
        if self._session:
            self._session.set_option(opt_name, text)
            self.param_changed.emit()

    def clear(self) -> None:
        """Clear panel (no block selected)."""
        self._session     = None
        self._exploit_def = None
        self._fields.clear()
        self._module_label.setText("No Block Selected")
        self._module_label.setStyleSheet(f"color: {ACCENT_RED}; font-weight: bold; font-size: 13px; background: transparent;")
        self._cat_label.setText("")

        while self._form_layout.count() > 1:
            item = self._form_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
