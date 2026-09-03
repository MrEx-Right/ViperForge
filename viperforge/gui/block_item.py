"""
ViperForge v2.0 — Block Item (QGraphicsItem)
Draggable exploit block on the canvas.
"""

import math
try:
    from PyQt6.QtWidgets import (
        QGraphicsItem, QGraphicsDropShadowEffect,
        QGraphicsTextItem, QStyleOptionGraphicsItem, QWidget, QMenu,
    )
    from PyQt6.QtGui import (
        QPainter, QColor, QPen, QBrush, QLinearGradient,
        QFont, QFontMetrics, QPainterPath,
    )
    from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal, QObject
    _PY6 = True
except ImportError:
    from PyQt5.QtWidgets import (
        QGraphicsItem, QGraphicsDropShadowEffect,
        QGraphicsTextItem, QStyleOptionGraphicsItem, QWidget, QMenu,
    )
    from PyQt5.QtGui import (
        QPainter, QColor, QPen, QBrush, QLinearGradient,
        QFont, QFontMetrics, QPainterPath,
    )
    from PyQt5.QtCore import Qt, QRectF, QPointF, pyqtSignal, QObject
    _PY6 = False

# Enum shortcuts (both Qt5 and Qt6 compatible)
def _flag(name):
    """GraphicsItemFlag enum compat."""
    if _PY6:
        return getattr(QGraphicsItem.GraphicsItemFlag, name)
    return getattr(QGraphicsItem, name)

def _align(name):
    if _PY6:
        return getattr(Qt.AlignmentFlag, name)
    return getattr(Qt, name)

_NO_PEN  = Qt.PenStyle.NoPen        if _PY6 else Qt.NoPen
_SOLID   = Qt.PenStyle.SolidLine    if _PY6 else Qt.SolidLine
_BOLD    = QFont.Weight.Bold        if _PY6 else QFont.Bold
_ALIGN_C = _align('AlignCenter')
_ALIGN_V = _align('AlignVCenter')
_IC_POS  = (QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged
            if _PY6 else QGraphicsItem.ItemPositionHasChanged)

from viperforge.registry import ExploitDef, all_categories, get_by_category
from viperforge.session import Session
from .theme import BG_CARD, BORDER_DARK, TEXT_PRIMARY, TEXT_DIM, CATEGORY_QSS_COLORS
import qtawesome as qta

# Block dimensions
BLOCK_W      = 220
BLOCK_H_BASE = 80
ROW_H        = 22
CORNER_R     = 12

# Connector dimensions
CONN_W  = 26
CONN_H  = 12
CONN_R  = 5
CONN_GAP = 14   # gap between success and failure pins

# Pin colours
PIN_SUCCESS_COLOR = "#00ff88"
PIN_FAILURE_COLOR = "#e63946"


class BlockSignals(QObject):
    """Separate QObject for QGraphicsItem signals."""
    clicked              = pyqtSignal(object)   # BlockItem
    moved                = pyqtSignal(object)   # BlockItem
    connect_success_req  = pyqtSignal(object)   # BlockItem (success pin clicked)
    connect_failure_req  = pyqtSignal(object)   # BlockItem (failure pin clicked)
    delete_req           = pyqtSignal(object)   # BlockItem (delete requested via menu)
    failure_pin_toggled  = pyqtSignal(object)   # BlockItem (failure pin enabled/disabled)
    macro_requested      = pyqtSignal(list)     # list[BlockItem]


class BlockItem(QGraphicsItem):
    """
    Exploit block draggable via drag-and-drop on the canvas.
    """

    def __init__(self, exploit_def: ExploitDef, session: Session, parent=None):
        super().__init__(parent)

        self.exploit_def = exploit_def
        self.session     = session

        # Color
        self.accent = QColor(
            CATEGORY_QSS_COLORS.get(exploit_def.category, "#e63946")
        )

        # Block height: title + parameter lines (first 3 params as summary)
        self._visible_opts = exploit_def.options[:3]
        self.block_h = BLOCK_H_BASE + len(self._visible_opts) * ROW_H

        # Signals
        self.signals = BlockSignals()

        # Flags
        self.setFlag(_flag('ItemIsMovable'))
        self.setFlag(_flag('ItemIsSelectable'))
        self.setFlag(_flag('ItemSendsGeometryChanges'))
        self.setAcceptHoverEvents(True)

        # State
        self._hovered   = False
        self._connected_success = False
        self._connected_failure = False
        self._failure_enabled   = False   # Whether failure pin is visible

        # Tooltip
        self.setToolTip(f"{exploit_def.category}\n{exploit_def.description}")

    # ── Size ─────────────────────────────────────────────────────────────────
    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, BLOCK_W, self.block_h + CONN_H + 2)

    # ── Paint ─────────────────────────────────────────────────────────────────
    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        body_rect = QRectF(0, 0, BLOCK_W, self.block_h)

        # ── Glow (when selected) ─────────────────────────────────
        if self.isSelected() or self._hovered:
            glow_pen = QPen(self.accent, 2 if self._hovered else 3)
            glow_pen.setStyle(_SOLID)
            painter.setPen(glow_pen)
        else:
            painter.setPen(QPen(QColor(BORDER_DARK), 1))

        # ── Body ─────────────────────────────────────────────────────────
        grad = QLinearGradient(0, 0, 0, self.block_h)
        grad.setColorAt(0.0, QColor("#1a1a2e"))
        grad.setColorAt(1.0, QColor("#0f0f1c"))
        painter.setBrush(QBrush(grad))
        painter.drawRoundedRect(body_rect, CORNER_R, CORNER_R)

        # ── Left accent line ─────────────────────────────────────────────
        accent_path = QPainterPath()
        accent_path.addRoundedRect(QRectF(0, 0, 4, self.block_h), 2, 2)
        painter.setPen(_NO_PEN)
        painter.setBrush(self.accent)
        painter.drawPath(accent_path)

        # ── Header ────────────────────────────────────────
        header_rect = QRectF(4, 0, BLOCK_W - 4, 38)
        header_grad = QLinearGradient(0, 0, BLOCK_W, 0)
        header_grad.setColorAt(0.0, QColor(self.accent.red(), self.accent.green(), self.accent.blue(), 60))
        header_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(header_grad))
        painter.setPen(_NO_PEN)
        painter.drawRoundedRect(header_rect, CORNER_R - 2, CORNER_R - 2)

        # ── Icon + Title ─────────────────────────────────────────────────
        icon_pixmap = qta.icon(self.exploit_def.icon, color=TEXT_PRIMARY).pixmap(18, 18)
        painter.drawPixmap(QPointF(14, 10), icon_pixmap)

        title_font = QFont("JetBrains Mono", 10, _BOLD)
        painter.setFont(title_font)
        painter.setPen(self.accent)
        painter.drawText(QRectF(40, 6, BLOCK_W - 50, 16), _ALIGN_V, self.exploit_def.name)

        desc_font = QFont("Consolas", 8)
        painter.setFont(desc_font)
        painter.setPen(QColor(TEXT_DIM))
        painter.drawText(QRectF(40, 22, BLOCK_W - 50, 14), _ALIGN_V, self.exploit_def.description[:30] + ("…" if len(self.exploit_def.description) > 30 else ""))

        # ── Parameter lines ───────────────────────────────────────────
        param_font = QFont("Consolas", 8)
        painter.setFont(param_font)
        for i, opt in enumerate(self._visible_opts):
            y = 44 + i * ROW_H
            # Row separator
            painter.setPen(QPen(QColor(BORDER_DARK), 1))
            painter.drawLine(QPointF(10, y), QPointF(BLOCK_W - 10, y))
            # Key
            painter.setPen(QColor(TEXT_DIM))
            painter.drawText(QRectF(10, y + 2, 80, ROW_H - 4), _ALIGN_V, opt.name)
            # Value
            val = self.session.get_option(opt.name)
            if not val:
                val = opt.default
            val_str = str(val) if val is not None else ""
            val_str = val_str[:18] + "…" if len(val_str) > 18 else val_str
            painter.setPen(QColor(TEXT_PRIMARY))
            painter.drawText(QRectF(90, y + 2, BLOCK_W - 100, ROW_H - 4), _ALIGN_V, val_str)

        # ── Bottom connectors (Success / Failure pins) ────────────────────────
        if self._failure_enabled:
            # Two pins side by side
            total_w = CONN_W * 2 + CONN_GAP
            base_x = (BLOCK_W - total_w) / 2
            # Success pin (left — green)
            s_rect = QRectF(base_x, self.block_h, CONN_W, CONN_H)
            s_color = QColor(PIN_SUCCESS_COLOR) if self._connected_success else QColor(BORDER_DARK)
            painter.setPen(QPen(s_color, 1))
            painter.setBrush(QBrush(QColor(s_color.red(), s_color.green(), s_color.blue(), 120)))
            painter.drawRoundedRect(s_rect, CONN_R, CONN_R)
            painter.setFont(QFont("Consolas", 6))
            painter.setPen(s_color)
            painter.drawText(s_rect, _ALIGN_C, "OK")

            # Failure pin (right — red)
            f_rect = QRectF(base_x + CONN_W + CONN_GAP, self.block_h, CONN_W, CONN_H)
            f_color = QColor(PIN_FAILURE_COLOR) if self._connected_failure else QColor(BORDER_DARK)
            painter.setPen(QPen(f_color, 1))
            painter.setBrush(QBrush(QColor(f_color.red(), f_color.green(), f_color.blue(), 120)))
            painter.drawRoundedRect(f_rect, CONN_R, CONN_R)
            painter.setFont(QFont("Consolas", 6))
            painter.setPen(f_color)
            painter.drawText(f_rect, _ALIGN_C, "ERR")
        else:
            # Single success pin (centred — green when connected)
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

    # ── Hover ─────────────────────────────────────────────────────────────────
    def hoverEnterEvent(self, event):
        self._hovered = True
        self.update()

    def hoverLeaveEvent(self, event):
        self._hovered = False
        self.update()

    # ── Click -> select and send signal ─────────────────────────────────────────
    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        local_pos = event.pos()
        conn_y = self.block_h

        if self._failure_enabled:
            total_w = CONN_W * 2 + CONN_GAP
            base_x = (BLOCK_W - total_w) / 2
            # Success pin hit-test
            if (base_x <= local_pos.x() <= base_x + CONN_W and
                    conn_y <= local_pos.y() <= conn_y + CONN_H):
                self.signals.connect_success_req.emit(self)
                return
            # Failure pin hit-test
            fx = base_x + CONN_W + CONN_GAP
            if (fx <= local_pos.x() <= fx + CONN_W and
                    conn_y <= local_pos.y() <= conn_y + CONN_H):
                self.signals.connect_failure_req.emit(self)
                return
        else:
            conn_x = (BLOCK_W - CONN_W) / 2
            if (conn_x <= local_pos.x() <= conn_x + CONN_W and
                    conn_y <= local_pos.y() <= conn_y + CONN_H):
                self.signals.connect_success_req.emit(self)
                return

        self.signals.clicked.emit(self)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self.signals.moved.emit(self)

    # ── Position change ────────────────────────────────────────────────────────
    def itemChange(self, change, value):
        if change == _IC_POS:
            self.signals.moved.emit(self)
        return super().itemChange(change, value)

    # ── Connector center points ──────────────────────────────────────────────
    def top_connector_pos(self) -> QPointF:
        return self.mapToScene(QPointF(BLOCK_W / 2, 0))

    def bottom_connector_pos(self) -> QPointF:
        """Legacy: centre bottom (used when failure pin is disabled)."""
        return self.mapToScene(QPointF(BLOCK_W / 2, self.block_h + CONN_H))

    def success_connector_pos(self) -> QPointF:
        if self._failure_enabled:
            total_w = CONN_W * 2 + CONN_GAP
            base_x = (BLOCK_W - total_w) / 2
            cx = base_x + CONN_W / 2
        else:
            cx = BLOCK_W / 2
        return self.mapToScene(QPointF(cx, self.block_h + CONN_H))

    def failure_connector_pos(self) -> QPointF:
        total_w = CONN_W * 2 + CONN_GAP
        base_x = (BLOCK_W - total_w) / 2
        cx = base_x + CONN_W + CONN_GAP + CONN_W / 2
        return self.mapToScene(QPointF(cx, self.block_h + CONN_H))

    def set_connected(self, state: bool, port_type: str = "success") -> None:
        if port_type == "failure":
            self._connected_failure = state
        else:
            self._connected_success = state
        self.update()

    @property
    def failure_enabled(self) -> bool:
        return self._failure_enabled

    @failure_enabled.setter
    def failure_enabled(self, val: bool) -> None:
        self._failure_enabled = val
        self.update()
        self.signals.moved.emit(self)

    def refresh(self) -> None:
        """Refresh block when session changes."""
        self.update()

    def change_exploit(self, new_def: ExploitDef) -> None:
        self.exploit_def = new_def
        self.session.set_exploit(new_def)
        self.accent = QColor(CATEGORY_QSS_COLORS.get(new_def.category, "#e63946"))
        self._visible_opts = new_def.options[:3]
        self.block_h = BLOCK_H_BASE + len(self._visible_opts) * ROW_H
        self.setToolTip(f"{new_def.category}\n{new_def.description}")
        self.update()
        self.signals.moved.emit(self) # to trigger connector redraw
        self.signals.clicked.emit(self) # to refresh right panel

    def contextMenuEvent(self, event):
        menu = QMenu()
        menu.setStyleSheet(f"""
            QMenu {{ background: #1a1a2e; color: {TEXT_PRIMARY}; border: 1px solid {BORDER_DARK}; }}
            QMenu::item:selected {{ background: #e63946; }}
        """)
        
        selected_blocks = [item for item in self.scene().selectedItems() if isinstance(item, BlockItem)]
        action_macro = None
        
        # If multiple blocks are selected, add Create Macro to top of menu
        if len(selected_blocks) >= 2:
            action_macro = menu.addAction(
                qta.icon('fa5s.layer-group', color='#ffd60a'),
                f"Create Macro ({len(selected_blocks)} blocks)"
            )
            menu.addSeparator()
        
        # Edit
        action_edit = menu.addAction(qta.icon('fa5s.edit', color='white'), "Edit")
        
        # Replace
        menu_replace = menu.addMenu(qta.icon('fa5s.exchange-alt', color='#ffaa00'), "Replace with...")
        menu_replace.setStyleSheet(f"""
            QMenu {{ background: #1a1a2e; color: {TEXT_PRIMARY}; border: 1px solid {BORDER_DARK}; }}
            QMenu::item:selected {{ background: #ffaa00; color: black; }}
        """)
        
        cat_menus = {}
        for cat in all_categories():
            cat_menu = menu_replace.addMenu(cat)
            cat_menus[cat] = cat_menu
            
            exploits = get_by_category(cat)
            for exp in exploits:
                if exp.id == self.exploit_def.id:
                    continue
                act = cat_menu.addAction(qta.icon(exp.icon, color='white'), exp.name)
                # Use lambda default arg trick to bind exp
                act.triggered.connect(lambda checked, e=exp: self.change_exploit(e))

        menu.addSeparator()

        # Toggle failure pin
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
        
        # Delete
        action_delete = menu.addAction(qta.icon('fa5s.trash-alt', color='#ff4455'), "Delete")

        # Execute menu
        selected = menu.exec(event.screenPos())
        if selected == action_edit:
            self.signals.clicked.emit(self)
        elif selected == action_fp:
            self._failure_enabled = not self._failure_enabled
            self.prepareGeometryChange()
            self.update()
            self.signals.failure_pin_toggled.emit(self)
            self.signals.moved.emit(self)   # redraw connectors
        elif selected == action_delete:
            self.signals.delete_req.emit(self)
        elif action_macro and selected == action_macro:
            self.signals.macro_requested.emit(selected_blocks)
