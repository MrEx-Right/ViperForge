"""
ViperForge v2.1 — Macro Dialog
QDialog for creating / editing macro blocks.
"""

try:
    from PyQt6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
        QTextEdit, QPushButton, QWidget, QScrollArea, QFrame,
    )
    from PyQt6.QtGui import QFont, QColor
    from PyQt6.QtCore import Qt, pyqtSignal
    _PY6 = True
except ImportError:
    from PyQt5.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
        QTextEdit, QPushButton, QWidget, QScrollArea, QFrame,
    )
    from PyQt5.QtGui import QFont, QColor
    from PyQt5.QtCore import Qt, pyqtSignal
    _PY6 = False

import qtawesome as qta
from .theme import (
    BG_DEEP, BG_PANEL, BG_CARD, BORDER_DARK,
    TEXT_PRIMARY, TEXT_DIM, ACCENT_GOLD, ACCENT_RED,
)


class MacroDialog(QDialog):
    """
    Dialog for creating a new macro from selected blocks.
    Shows the list of blocks being bundled, and lets the user
    set a name and description.
    """

    macro_saved = pyqtSignal(str, str, list, list)  # name, desc, blocks_data, conns_data

    def __init__(self, blocks_data: list, connections_data: list, parent=None):
        super().__init__(parent)
        self.blocks_data = blocks_data
        self.connections_data = connections_data

        self.setWindowTitle("ViperForge — Create Macro")
        self.setMinimumSize(500, 440)
        self.setMaximumSize(700, 600)
        self.setStyleSheet(f"""
            QDialog {{
                background: {BG_DEEP};
                color: {TEXT_PRIMARY};
                font-family: "JetBrains Mono", "Consolas", monospace;
            }}
            QLabel {{ background: transparent; }}
            QLineEdit {{
                background: {BG_CARD}; border: 1px solid {BORDER_DARK};
                border-radius: 4px; padding: 6px 10px; color: {TEXT_PRIMARY};
                font-size: 13px;
            }}
            QLineEdit:focus {{ border: 1px solid {ACCENT_GOLD}; }}
            QTextEdit {{
                background: {BG_CARD}; border: 1px solid {BORDER_DARK};
                border-radius: 4px; padding: 6px 10px; color: {TEXT_PRIMARY};
                font-size: 12px;
            }}
            QPushButton {{
                background: {BG_CARD}; color: {TEXT_PRIMARY};
                border: 1px solid {BORDER_DARK}; border-radius: 6px;
                padding: 8px 18px; font-weight: bold;
            }}
            QPushButton:hover {{
                background: {ACCENT_GOLD}; color: black; border-color: {ACCENT_GOLD};
            }}
        """)

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title = QLabel()
        title.setPixmap(qta.icon('fa5s.layer-group', color=ACCENT_GOLD).pixmap(24, 24))
        title_text = QLabel(f"  <b style='color:{ACCENT_GOLD}; font-size:15px;'>Create New Macro</b>")
        title_text.setTextFormat(Qt.TextFormat.RichText if _PY6 else Qt.RichText)
        title_row = QHBoxLayout()
        title_row.addWidget(title)
        title_row.addWidget(title_text)
        title_row.addStretch()
        layout.addLayout(title_row)

        # Name
        lbl_name = QLabel(f"<span style='color:{ACCENT_GOLD};'>MACRO NAME</span>")
        lbl_name.setTextFormat(Qt.TextFormat.RichText if _PY6 else Qt.RichText)
        layout.addWidget(lbl_name)
        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("e.g. Auth Bypass Chain")
        layout.addWidget(self._name_input)

        # Description
        lbl_desc = QLabel(f"<span style='color:{ACCENT_GOLD};'>DESCRIPTION</span>")
        lbl_desc.setTextFormat(Qt.TextFormat.RichText if _PY6 else Qt.RichText)
        layout.addWidget(lbl_desc)
        self._desc_input = QTextEdit()
        self._desc_input.setPlaceholderText("Briefly describe what this macro does...")
        self._desc_input.setMaximumHeight(80)
        layout.addWidget(self._desc_input)

        # Block list preview
        lbl_blocks = QLabel(
            f"<span style='color:{ACCENT_GOLD};'>INCLUDED BLOCKS</span>"
            f"  <span style='color:{TEXT_DIM};'>({len(self.blocks_data)} blocks)</span>"
        )
        lbl_blocks.setTextFormat(Qt.TextFormat.RichText if _PY6 else Qt.RichText)
        layout.addWidget(lbl_blocks)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(150)
        if _PY6:
            scroll.setFrameShape(QFrame.Shape.NoFrame)
        else:
            scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(f"""
            QScrollArea {{ background: {BG_PANEL}; border: 1px solid {BORDER_DARK}; border-radius: 4px; }}
            QScrollBar:vertical {{ width: 4px; }}
        """)

        content = QWidget()
        content.setStyleSheet(f"background: {BG_PANEL};")
        c_layout = QVBoxLayout(content)
        c_layout.setContentsMargins(8, 8, 8, 8)
        c_layout.setSpacing(4)

        from viperforge.registry import get_exploit_by_id, CATEGORY_COLORS
        for bd in self.blocks_data:
            exp = get_exploit_by_id(bd.get("exploit_id"))
            if not exp:
                continue
            color = CATEGORY_COLORS.get(exp.category, "#ffffff")
            row = QLabel(
                f"<span style='color:{color};'>●</span> "
                f"<b style='color:{TEXT_PRIMARY};'>{exp.name}</b>"
                f"  <span style='color:{TEXT_DIM};'>— {exp.description[:40]}</span>"
            )
            row.setTextFormat(Qt.TextFormat.RichText if _PY6 else Qt.RichText)
            row.setStyleSheet(f"background: transparent; padding: 2px 0;")
            c_layout.addWidget(row)

        c_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_cancel = QPushButton(" Cancel")
        btn_cancel.setIcon(qta.icon('fa5s.times', color=ACCENT_RED))
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        btn_save = QPushButton(" Save Macro")
        btn_save.setIcon(qta.icon('fa5s.save', color=ACCENT_GOLD))
        btn_save.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #8b6f00, stop:1 {ACCENT_GOLD});
                color: black; border: none; font-size: 13px;
                border-radius: 6px; padding: 10px 24px;
            }}
            QPushButton:hover {{
                background: {ACCENT_GOLD};
            }}
        """)
        btn_save.clicked.connect(self._on_save)
        btn_row.addWidget(btn_save)

        layout.addLayout(btn_row)

    def _on_save(self):
        name = self._name_input.text().strip()
        if not name:
            name = "Unnamed Macro"
        desc = self._desc_input.toPlainText().strip()
        self.macro_saved.emit(name, desc, self.blocks_data, self.connections_data)
        self.accept()
