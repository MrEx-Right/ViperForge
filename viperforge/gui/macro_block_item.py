"""
ViperForge v2.1 — Macro Block Item
Special QGraphicsItem for macro blocks on the canvas.
Displays a gold-themed composite block with inner block count badge.
"""

try:
    from PyQt6.QtWidgets import QGraphicsDropShadowEffect, QMenu
    from PyQt6.QtGui import (
        QPainter, QColor, QPen, QBrush, QLinearGradient,
        QFont, QPainterPath,
    )
    from PyQt6.QtCore import Qt, QRectF, QPointF
    _PY6 = True
except ImportError:
    from PyQt5.QtWidgets import QGraphicsDropShadowEffect, QMenu
    from PyQt5.QtGui import (
        QPainter, QColor, QPen, QBrush, QLinearGradient,
        QFont, QPainterPath,
    )
    from PyQt5.QtCore import Qt, QRectF, QPointF
    _PY6 = False

import qtawesome as qta

from viperforge.macro import MacroDef, macro_to_sessions
from viperforge.session import Session
from .block_item import (
    BlockItem, BlockSignals, ExploitDef,
    BLOCK_W, BLOCK_H_BASE, CONN_W, CONN_H, CONN_R, CONN_GAP,
    CORNER_R, PIN_SUCCESS_COLOR, PIN_FAILURE_COLOR,
    _NO_PEN, _BOLD, _ALIGN_C, _ALIGN_V,
)
from .theme import BG_CARD, BORDER_DARK, TEXT_PRIMARY, TEXT_DIM, ACCENT_GOLD

_MACRO_ACCENT = QColor(ACCENT_GOLD)

# Fake ExploitDef for macro blocks
_MACRO_CATEGORY = "Macros"


class MacroBlockItem(BlockItem):
    """
    A macro block that encapsulates multiple inner blocks.
    Renders with gold accent and shows inner block count.
    Double-click opens macro editor dialog.
    """

    def __init__(self, macro_def: MacroDef, session: Session, parent=None):
        # Create a virtual ExploitDef for compatibility
        virtual_def = ExploitDef(
            id=-1,  # negative = macro
            name=macro_def.name,
            category=_MACRO_CATEGORY,
            description=macro_def.description or f"Macro ({len(macro_def.blocks)} blocks)",
            template="",  # no template — expanded at generation time
            options=[],
        )
        # Tag the virtual def so the engine can recognize and expand this
        # session as a macro (see engine._is_macro / _expand_macros).
        virtual_def._macro_def = macro_def

        super().__init__(virtual_def, session, parent)

        # Wire the session to the virtual exploit def so downstream code
        # (validation, generation, preview) sees a valid active_exploit
        # instead of an empty/unset Session.
        self.session.set_exploit(virtual_def)

        self.macro_def = macro_def
        self.accent = _MACRO_ACCENT
        self.block_h = BLOCK_H_BASE + 10  # slightly taller

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        body_rect = QRectF(0, 0, BLOCK_W, self.block_h)

        # Glow
        if self.isSelected() or self._hovered:
            glow_pen = QPen(_MACRO_ACCENT, 2 if self._hovered else 3)
            painter.setPen(glow_pen)
        else:
            painter.setPen(QPen(QColor(BORDER_DARK), 1))

        # Body — gold gradient
        grad = QLinearGradient(0, 0, 0, self.block_h)
        grad.setColorAt(0.0, QColor("#1a1800"))
        grad.setColorAt(1.0, QColor("#0f0e00"))
        painter.setBrush(QBrush(grad))
        painter.drawRoundedRect(body_rect, CORNER_R, CORNER_R)

        # Left accent bar
        accent_path = QPainterPath()
        accent_path.addRoundedRect(QRectF(0, 0, 4, self.block_h), 2, 2)
        painter.setPen(_NO_PEN)
        painter.setBrush(_MACRO_ACCENT)
        painter.drawPath(accent_path)

        # Header gradient
        header_rect = QRectF(4, 0, BLOCK_W - 4, 38)
        header_grad = QLinearGradient(0, 0, BLOCK_W, 0)
        header_grad.setColorAt(0.0, QColor(255, 214, 10, 50))
        header_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(header_grad))
        painter.setPen(_NO_PEN)
        painter.drawRoundedRect(header_rect, CORNER_R - 2, CORNER_R - 2)

        # Icon + Title
        icon_pixmap = qta.icon("fa5s.layer-group", color=ACCENT_GOLD).pixmap(18, 18)
        painter.drawPixmap(QPointF(14, 10), icon_pixmap)

        title_font = QFont("JetBrains Mono", 10, _BOLD)
        painter.setFont(title_font)
        painter.setPen(_MACRO_ACCENT)
        painter.drawText(QRectF(40, 6, BLOCK_W - 50, 16), _ALIGN_V, self.macro_def.name)

        desc_font = QFont("Consolas", 8)
        painter.setFont(desc_font)
        painter.setPen(QColor(TEXT_DIM))
        desc = self.macro_def.description or "Custom macro block"
        if len(desc) > 30:
            desc = desc[:28] + "…"
        painter.drawText(QRectF(40, 22, BLOCK_W - 50, 14), _ALIGN_V, desc)

        # Inner block count badge
        badge_text = f"⬡ {len(self.macro_def.blocks)} blocks"
        badge_rect = QRectF(14, 44, BLOCK_W - 28, 22)
        painter.setPen(QPen(QColor(ACCENT_GOLD + "44"), 1))
        painter.setBrush(QBrush(QColor(ACCENT_GOLD + "15")))
        painter.drawRoundedRect(badge_rect, 4, 4)
        painter.setFont(QFont("Consolas", 8))
        painter.setPen(QColor(ACCENT_GOLD))
        painter.drawText(badge_rect, _ALIGN_C, badge_text)

        # Dashed border (to show it's a composite)
        from PyQt6.QtCore import Qt as QtNS
        dash_pen = QPen(QColor(ACCENT_GOLD + "44"), 1)
        dash_pen.setStyle(QtNS.PenStyle.DashLine if _PY6 else Qt.DashLine)
        painter.setPen(dash_pen)
        painter.setBrush(QBrush(QColor(0, 0, 0, 0)))
        painter.drawRoundedRect(QRectF(2, 2, BLOCK_W - 4, self.block_h - 4), CORNER_R - 1, CORNER_R - 1)

        # Bottom connector (success pin)
        conn_x = (BLOCK_W - CONN_W) / 2
        conn_y = self.block_h
        conn_rect = QRectF(conn_x, conn_y, CONN_W, CONN_H)
        conn_color = QColor(PIN_SUCCESS_COLOR) if self._connected_success else QColor(BORDER_DARK)
        painter.setPen(QPen(conn_color, 1))
        painter.setBrush(QBrush(QColor(conn_color.red(), conn_color.green(), conn_color.blue(), 120)))
        painter.drawRoundedRect(conn_rect, CONN_R, CONN_R)
        painter.setFont(QFont("Consolas", 7))
        painter.setPen(conn_color)
        painter.drawText(conn_rect, _ALIGN_C, "v")

    def get_inner_sessions(self) -> list:
        """Expand macro into list of Session objects for code generation."""
        return macro_to_sessions(self.macro_def)

    def mouseDoubleClickEvent(self, event):
        """Double-click opens macro info (could be expanded to full editor)."""
        self.signals.clicked.emit(self)
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event):
        """
        Macro-specific context menu. Deliberately omits "Replace with..."
        (inherited from BlockItem) since swapping self.exploit_def for a
        real ExploitDef would desync it from self.macro_def, leaving the
        block rendered as a macro but generating as something else.
        """
        menu = QMenu()
        menu.setStyleSheet(f"""
            QMenu {{ background: #1a1a2e; color: {TEXT_PRIMARY}; border: 1px solid {BORDER_DARK}; }}
            QMenu::item:selected {{ background: {ACCENT_GOLD}; color: black; }}
        """)

        selected_blocks = [item for item in self.scene().selectedItems() if isinstance(item, BlockItem)]
        action_macro = None

        if len(selected_blocks) >= 2:
            action_macro = menu.addAction(
                qta.icon('fa5s.layer-group', color=ACCENT_GOLD),
                f"Create Macro ({len(selected_blocks)} blocks)"
            )
            menu.addSeparator()

        action_edit = menu.addAction(qta.icon('fa5s.edit', color='white'), "Edit")

        menu.addSeparator()

        if self._failure_enabled:
            action_fp = menu.addAction(
                qta.icon('fa5s.times-circle', color=PIN_FAILURE_COLOR),
                "Remove Failure Pin"
            )
        else:
            action_fp = menu.addAction(
                qta.icon('fa5s.code-branch', color=PIN_SUCCESS_COLOR),
                "Add Failure Pin (Branch)"
            )

        menu.addSeparator()

        action_delete = menu.addAction(qta.icon('fa5s.trash-alt', color='#ff4455'), "Delete")

        selected = menu.exec(event.screenPos())
        if selected == action_edit:
            self.signals.clicked.emit(self)
        elif selected == action_fp:
            self._failure_enabled = not self._failure_enabled
            self.prepareGeometryChange()
            self.update()
            self.signals.failure_pin_toggled.emit(self)
            self.signals.moved.emit(self)
        elif selected == action_delete:
            self.signals.delete_req.emit(self)
        elif action_macro and selected == action_macro:
            self.signals.macro_requested.emit(selected_blocks)
