"""
ViperForge v2.1 — Connector (SVG Bezier line)
Draws the chain connection between two blocks.
Supports port_type: "success" (green) or "failure" (red).
"""

try:
    from PyQt6.QtWidgets import QGraphicsPathItem
    from PyQt6.QtGui import QPen, QColor, QPainterPath
    from PyQt6.QtCore import Qt, QPointF
    _PY6 = True
except ImportError:
    from PyQt5.QtWidgets import QGraphicsPathItem
    from PyQt5.QtGui import QPen, QColor, QPainterPath
    from PyQt5.QtCore import Qt, QPointF
    _PY6 = False

from .theme import ACCENT_RED

# Port-type colours
_PORT_COLORS = {
    "success": "#00ff88",
    "failure": "#e63946",
}
_SELECTED_COLOR = "#ffaa00"


class ConnectorItem(QGraphicsPathItem):
    """
    Draws a bezier curve between two BlockItems.
    port_type: "success" | "failure"
    """

    def __init__(self, src_block, dst_block, port_type: str = "success", parent=None):
        super().__init__(parent)
        self.src = src_block
        self.dst = dst_block
        self.port_type = port_type

        line_color = _PORT_COLORS.get(port_type, ACCENT_RED)
        pen = QPen(QColor(line_color), 2, Qt.PenStyle.SolidLine if _PY6 else Qt.SolidLine)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap if _PY6 else Qt.RoundCap)
        self.setPen(pen)
        self.setZValue(-1)   # Below the blocks

        # Enable selection
        if _PY6:
            from PyQt6.QtWidgets import QGraphicsItem
            self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        else:
            from PyQt5.QtWidgets import QGraphicsItem
            self.setFlag(QGraphicsItem.ItemIsSelectable)

        self.update_path()

    def paint(self, painter, option, widget=None):
        if self.isSelected():
            pen = QPen(QColor(_SELECTED_COLOR), 4, Qt.PenStyle.SolidLine if _PY6 else Qt.SolidLine)
            painter.setPen(pen)
        else:
            painter.setPen(self.pen())
        painter.drawPath(self.path())

    def shape(self):
        # Create a wider shape for easier clicking
        try:
            from PyQt6.QtGui import QPainterPathStroker
        except ImportError:
            from PyQt5.QtGui import QPainterPathStroker
            
        stroker = QPainterPathStroker()
        stroker.setWidth(15) # 15 pixels wide hit area
        return stroker.createStroke(self.path())

    def update_path(self) -> None:
        # Source position depends on port type
        if self.port_type == "failure":
            src_pt = self.src.failure_connector_pos()
        else:
            src_pt = self.src.success_connector_pos()
        dst_pt = self.dst.top_connector_pos()

        ctrl_offset = max(60, abs(dst_pt.y() - src_pt.y()) * 0.5)
        ctrl1 = QPointF(src_pt.x(), src_pt.y() + ctrl_offset)
        ctrl2 = QPointF(dst_pt.x(), dst_pt.y() - ctrl_offset)

        path = QPainterPath(src_pt)
        path.cubicTo(ctrl1, ctrl2, dst_pt)
        self.setPath(path)
