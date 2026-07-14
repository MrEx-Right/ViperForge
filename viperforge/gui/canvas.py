"""
ViperForge v2.0 — Canvas (QGraphicsView + Scene)
Drag-and-drop block editor.
"""

try:
    from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene
    from PyQt6.QtGui import QColor, QPainter, QBrush, QPen
    from PyQt6.QtCore import Qt, QPointF, pyqtSignal
    _PY6 = True
except ImportError:
    from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene
    from PyQt5.QtGui import QColor, QPainter, QBrush, QPen
    from PyQt5.QtCore import Qt, QPointF, pyqtSignal
    _PY6 = False

def _middle_button():
    return Qt.MouseButton.MiddleButton if _PY6 else Qt.MiddleButton

def _closed_hand():
    return Qt.CursorShape.ClosedHandCursor if _PY6 else Qt.ClosedHandCursor

def _arrow_cursor():
    return Qt.CursorShape.ArrowCursor if _PY6 else Qt.ArrowCursor

def _key_delete():
    return Qt.Key.Key_Delete if _PY6 else Qt.Key_Delete

def _key_backspace():
    return Qt.Key.Key_Backspace if _PY6 else Qt.Key_Backspace

from viperforge.registry import ExploitDef
from viperforge.session import Session
from .block_item import BlockItem
from .connector import ConnectorItem
from .theme import BG_DEEP, BORDER_DARK, ACCENT_RED

# Grid settings
GRID_SIZE    = 30
GRID_COLOR   = QColor(BORDER_DARK)
BLOCK_MARGIN = 40


class ExploitCanvas(QGraphicsView):
    """
    Main canvas widget. Holds blocks and manages chain connections.
    Signals:
        block_selected(BlockItem) — a block was selected
        canvas_changed()          — any change
    """

    block_selected = pyqtSignal(object)    # BlockItem | None
    canvas_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self._scene = QGraphicsScene(self)
        self._scene.setBackgroundBrush(QBrush(QColor(BG_DEEP)))
        self.setScene(self._scene)

        # View settings
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        if _PY6:
            self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
            self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
            self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
            self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        else:
            self.setDragMode(QGraphicsView.RubberBandDrag)
            self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
            self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
            self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # State
        self._blocks:     list[BlockItem]    = []
        self._connectors: list[ConnectorItem]= []
        self._pending_src: BlockItem | None  = None   # waiting for chain connection?

        # Canvas size
        self._scene.setSceneRect(-2000, -2000, 6000, 6000)

    # ── Add block ───────────────────────────────────────────────────────────
    def add_block(self, exploit_def: ExploitDef, session: Session) -> BlockItem:
        """Create new block, add to canvas."""
        block = BlockItem(exploit_def, session)

        # Position: below the last block, otherwise center
        if self._blocks:
            last = self._blocks[-1]
            x = last.x()
            y = last.y() + last.block_h + 80
        else:
            center = self.mapToScene(self.viewport().rect().center())
            x = center.x() - 110
            y = center.y() - 60

        block.setPos(x, y)
        self._scene.addItem(block)
        self._blocks.append(block)

        # Connect signals
        block.signals.clicked.connect(self._on_block_clicked)
        block.signals.moved.connect(self._on_block_moved)
        block.signals.connect_req.connect(self._on_connect_req)
        block.signals.delete_req.connect(self._on_block_delete_req)

        self.canvas_changed.emit()
        return block

    # ── Clear all blocks ──────────────────────────────────────────────────
    def clear_canvas(self) -> None:
        for item in list(self._scene.items()):
            self._scene.removeItem(item)
        self._blocks.clear()
        self._connectors.clear()
        self._pending_src = None
        self.canvas_changed.emit()

    # ── Save/Load Workspace ───────────────────────────────────────────────
    def to_dict(self) -> dict:
        import uuid
        block_ids = {}
        blocks_data = []
        for b in self._blocks:
            bid = str(uuid.uuid4())
            block_ids[b] = bid
            opts = dict(b.session.options)
            blocks_data.append({
                "uuid": bid,
                "exploit_id": b.exploit_def.id,
                "x": b.x(),
                "y": b.y(),
                "options": opts
            })
            
        conns_data = []
        for c in self._connectors:
            if c.src in block_ids and c.dst in block_ids:
                conns_data.append({
                    "src": block_ids[c.src],
                    "dst": block_ids[c.dst]
                })
                
        return {"blocks": blocks_data, "connections": conns_data}

    def from_dict(self, data: dict) -> list[BlockItem]:
        self.clear_canvas()
        from viperforge.registry import get_exploit_by_id
        from viperforge.session import Session
        
        block_map = {}
        created_blocks = []
        for b_data in data.get("blocks", []):
            eid = b_data.get("exploit_id")
            exp = get_exploit_by_id(eid)
            if not exp:
                continue
            sess = Session()
            sess.set_exploit(exp)
            opts = b_data.get("options", {})
            for k, v in opts.items():
                sess.set_option(k, v)
            
            block = BlockItem(exp, sess)
            block.setPos(b_data.get("x", 0), b_data.get("y", 0))
            self._scene.addItem(block)
            self._blocks.append(block)
            created_blocks.append(block)
            
            block.signals.clicked.connect(self._on_block_clicked)
            block.signals.moved.connect(self._on_block_moved)
            block.signals.connect_req.connect(self._on_connect_req)
            block.signals.delete_req.connect(self._on_block_delete_req)
            
            block_map[b_data.get("uuid")] = block
            
        for c_data in data.get("connections", []):
            src = block_map.get(c_data.get("src"))
            dst = block_map.get(c_data.get("dst"))
            if src and dst:
                self._add_connector(src, dst)
        
        self.canvas_changed.emit()
        return created_blocks

    # ── Connection management ─────────────────────────────────────────────────────
    def _on_connect_req(self, block: BlockItem) -> None:
        """Connector click: detach if exists, else start connection."""
        # If there's an outgoing connection, detach it
        existing_conns = [c for c in self._connectors if c.src is block]
        if existing_conns:
            for c in existing_conns:
                self._scene.removeItem(c)
                self._connectors.remove(c)
            block.set_connected(False)
            self.canvas_changed.emit()
            return

        if self._pending_src is None:
            self._pending_src = block
            block.set_connected(True)
        else:
            if self._pending_src is not block:
                self._add_connector(self._pending_src, block)
            else:
                self._pending_src.set_connected(False)
            self._pending_src = None

    def _add_connector(self, src: BlockItem, dst: BlockItem) -> None:
        conn = ConnectorItem(src, dst)
        self._scene.addItem(conn)
        self._connectors.append(conn)
        src.set_connected(True)
        self.canvas_changed.emit()

    def _update_connectors(self) -> None:
        for conn in self._connectors:
            conn.update_path()

    # ── Block signals ─────────────────────────────────────────────────────────
    def _on_block_clicked(self, block: BlockItem) -> None:
        if self._pending_src is not None and self._pending_src is not block:
            self._add_connector(self._pending_src, block)
            self._pending_src = None
        else:
            self.block_selected.emit(block)

    def _on_block_delete_req(self, block: BlockItem) -> None:
        self._scene.clearSelection()
        block.setSelected(True)
        self.delete_selected_blocks()

    def _on_block_moved(self, block: BlockItem) -> None:
        self._update_connectors()
        self.canvas_changed.emit()

    # ── Calculate chain order ────────────────────────────────────────────────
    def get_chain_order(self) -> list[BlockItem]:
        """
        Returns topological order based on connector graph.
        If no connection, returns by addition order.
        """
        if not self._connectors:
            return list(self._blocks)

        # Order connected blocks
        adj: dict[BlockItem, BlockItem] = {c.src: c.dst for c in self._connectors}
        starts = [b for b in self._blocks if not any(c.dst is b for c in self._connectors)]

        ordered: list[BlockItem] = []
        for start in starts:
            cur = start
            while cur is not None:
                ordered.append(cur)
                cur = adj.get(cur)

        # Add unconnected blocks
        for b in self._blocks:
            if b not in ordered:
                ordered.append(b)

        return ordered

    # ── Deletion Process ─────────────────────────────────────────────────────────
    def keyPressEvent(self, event):
        if event.key() in (_key_delete(), _key_backspace()):
            self.delete_selected_blocks()
        else:
            super().keyPressEvent(event)

    def delete_selected_blocks(self) -> None:
        selected_blocks = [item for item in self._scene.selectedItems() if isinstance(item, BlockItem)]
        selected_conns = [item for item in self._scene.selectedItems() if isinstance(item, ConnectorItem)]

        if not selected_blocks and not selected_conns:
            return

        # Delete selected connections
        for c in selected_conns:
            if c in self._connectors:
                self._scene.removeItem(c)
                self._connectors.remove(c)
                # Update src connected status
                if not any(oc.src is c.src for oc in self._connectors):
                    c.src.set_connected(False)

        # Delete selected blocks
        for block in selected_blocks:
            # Find and delete remaining connectors for this block
            conns_to_remove = [c for c in self._connectors if c.src is block or c.dst is block]
            for c in conns_to_remove:
                self._scene.removeItem(c)
                self._connectors.remove(c)
                
                # Update status of the other block if it was the source
                if c.src is not block:
                    if not any(oc.src is c.src for oc in self._connectors):
                        c.src.set_connected(False)
            
            self._scene.removeItem(block)
            self._blocks.remove(block)
            if self._pending_src is block:
                self._pending_src = None
                
        self.canvas_changed.emit()

    # ── Panning & Zoom ───────────────────────────────────────────────────────
    def mousePressEvent(self, event):
        if event.button() == _middle_button():
            self._is_panning = True
            self._pan_start = event.pos()
            self.setCursor(_closed_hand())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if getattr(self, '_is_panning', False):
            delta = event.pos() - self._pan_start
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            self._pan_start = event.pos()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == _middle_button():
            self._is_panning = False
            self.setCursor(_arrow_cursor())
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(factor, factor)

    # ── Draw grid ──────────────────────────────────────────────────────────
    def drawBackground(self, painter: QPainter, rect) -> None:
        super().drawBackground(painter, rect)

        # Dot grid
        pen = QPen(QColor(BORDER_DARK), 1)
        painter.setPen(pen)

        left   = int(rect.left())   - (int(rect.left())   % GRID_SIZE)
        top    = int(rect.top())    - (int(rect.top())    % GRID_SIZE)
        right  = int(rect.right())  + GRID_SIZE
        bottom = int(rect.bottom()) + GRID_SIZE

        for x in range(left, right, GRID_SIZE):
            for y in range(top, bottom, GRID_SIZE):
                painter.drawPoint(QPointF(x, y))

    @property
    def blocks(self) -> list[BlockItem]:
        return self._blocks
