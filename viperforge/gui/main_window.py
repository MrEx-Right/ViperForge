"""
ViperForge v2.1 — Main Window
Main PyQt6 window: palette + canvas + right panel.
Macro system and dual-pin branching support.
"""

import os
import sys
from pathlib import Path

try:
    from PyQt6.QtWidgets import (
        QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
        QSplitter, QPushButton, QLabel, QStatusBar,
        QFileDialog, QMessageBox, QToolBar, QSizePolicy,
    )
    from PyQt6.QtGui import QColor, QFont, QIcon, QAction, QPalette
    from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject, QSize
    _PY6 = True
except ImportError:
    from PyQt5.QtWidgets import (
        QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
        QSplitter, QPushButton, QLabel, QStatusBar,
        QFileDialog, QMessageBox, QToolBar, QSizePolicy,
    )
    from PyQt5.QtGui import QColor, QFont, QIcon, QPalette
    from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject, QSize
    _PY6 = False

import qtawesome as qta

# Qt5/6 compat helpers
def _toolbar_area():
    return Qt.ToolBarArea.TopToolBarArea if _PY6 else Qt.TopToolBarArea

def _orientation_h():
    return Qt.Orientation.Horizontal if _PY6 else Qt.Horizontal

def _text_format_rich():
    return Qt.TextFormat.RichText if _PY6 else Qt.RichText

def _align_right():
    return Qt.AlignmentFlag.AlignRight if _PY6 else Qt.AlignRight

def _sp(h=True):
    p = QSizePolicy.Policy if _PY6 else QSizePolicy
    return (p.Expanding, p.Preferred) if h else (p.Preferred, p.Preferred)

def _mb_yes_no():
    b = QMessageBox.StandardButton if _PY6 else QMessageBox
    return b.Yes | b.No

def _mb_yes():
    b = QMessageBox.StandardButton if _PY6 else QMessageBox
    return b.Yes

def _mb_icon_info():
    return QMessageBox.Icon.Information if _PY6 else QMessageBox.Information

from viperforge.registry import ExploitDef
from viperforge.session import Session
from viperforge.engine import generate_single, generate_chain, preview_single, preview_chain
from viperforge.validator import validate_chain, ERROR as V_ERROR, WARNING as V_WARNING
from viperforge.macro import (
    MacroDef, save_macro, load_macro, list_macros,
    create_macro_from_blocks, macro_to_sessions,
)

from .block_palette import BlockPalette
from .canvas import ExploitCanvas
from .block_item import BlockItem
from .macro_block_item import MacroBlockItem
from .macro_dialog import MacroDialog
from .param_panel import ParamPanel
from .preview_panel import PreviewPanel
from .theme import (
    MAIN_QSS, BG_DEEP, BG_PANEL, ACCENT_RED, TEXT_PRIMARY,
    TEXT_DIM, BORDER_DARK, ACCENT_GOLD, ACCENT_GREEN, BG_CARD,
)

BANNER_ASCII = """\
 ██╗   ██╗██╗██████╗ ███████╗██████╗ ███████╗ ██████╗ ██████╗  ██████╗ ███████╗
 ██║   ██║██║██╔══██╗██╔════╝██╔══██╗██╔════╝██╔═══██╗██╔══██╗██╔════╝ ██╔════╝
 ██║   ██║██║██████╔╝█████╗  ██████╔╝█████╗  ██║   ██║██████╔╝██║  ███╗█████╗  
 ╚██╗ ██╔╝██║██╔═══╝ ██╔══╝  ██╔══██╗██╔══╝  ██║   ██║██╔══██╗██║   ██║██╔══╝  
  ╚████╔╝ ██║██║     ███████╗██║  ██║██║     ╚██████╔╝██║  ██║╚██████╔╝███████╗
   ╚═══╝  ╚═╝╚═╝     ╚══════╝╚═╝  ╚═╝╚═╝      ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝"""


class GenerateWorker(QObject):
    """Generates exploit in the background (to prevent UI freeze)."""
    finished = pyqtSignal(str)   # out_path
    error    = pyqtSignal(str)   # error message

    def __init__(self, sessions: list[Session], chain: bool, out_path: str | None = None):
        super().__init__()
        self.sessions  = sessions
        self.chain     = chain
        self.out_path  = out_path

    def run(self):
        try:
            if self.chain and len(self.sessions) > 1:
                path = generate_chain(self.sessions, self.out_path)
            else:
                path = generate_single(self.sessions[0], self.out_path)
            self.finished.emit(path)
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ViperForge — Block Exploit Builder")
        
        base_dir = Path(__file__).resolve().parent.parent.parent
        logo_path = base_dir / "assets" / "images" / "logo.png"
        self.setWindowIcon(QIcon(str(logo_path)))

        self.setMinimumSize(1280, 780)
        self.resize(1520, 900)
        self.setStyleSheet(MAIN_QSS)

        # Block -> Session mapping
        self._block_sessions: dict[BlockItem, Session] = {}
        self._selected_block: BlockItem | None = None

        self._build_ui()
        self._connect_signals()

    # ─── UI construction ─────────────────────────────────────────────────────────
    def _build_ui(self) -> None:
        # ── Title bar ─────────────────────────────────────────────────────
        toolbar = self._build_toolbar()
        self.addToolBar(_toolbar_area(), toolbar)

        # ── Main layout ────────────────────────────────────────────────────
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Splitter ──────────────────────────────────────────────────────
        splitter = QSplitter(_orientation_h())
        splitter.setHandleWidth(2)
        splitter.setStyleSheet(f"QSplitter::handle {{ background: {BORDER_DARK}; }}")

        # Left: Palette
        self.palette  = BlockPalette()
        splitter.addWidget(self.palette)

        # Center: Canvas + bottom toolbar
        canvas_widget = self._build_canvas_section()
        splitter.addWidget(canvas_widget)

        # Right: Param + Preview
        right_panel = self._build_right_panel()
        splitter.addWidget(right_panel)

        splitter.setSizes([340, 720, 380])
        main_layout.addWidget(splitter)

        # ── Status bar ────────────────────────────────────────────────────
        self._status = QStatusBar()
        self._status.setStyleSheet(f"""
            background: {BG_PANEL};
            color: {TEXT_DIM};
            border-top: 1px solid {BORDER_DARK};
            font-size: 11px;
            padding: 0 8px;
        """)
        self.setStatusBar(self._status)
        self._set_status("Ready. Double-click a block in the palette to add it to the canvas.")

    def _build_toolbar(self) -> QToolBar:
        tb = QToolBar("Main")
        tb.setMovable(False)
        tb.setFloatable(False)
        tb.setStyleSheet(f"""
            QToolBar {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0d0010, stop:0.5 {BG_PANEL}, stop:1 #0d0010);
                border-bottom: 2px solid {ACCENT_RED};
                padding: 4px 12px;
                spacing: 8px;
            }}
            QToolBar::separator {{
                background: {BORDER_DARK};
                width: 1px;
                margin: 4px 8px;
            }}
        """)
        tb.setIconSize(QSize(16, 16))

        # Logo label
        logo_icon = QLabel()
        base_dir = Path(__file__).resolve().parent.parent.parent
        logo_path = base_dir / "assets" / "images" / "logo.png"
        
        try:
            from PyQt6.QtGui import QPixmap
            pm = QPixmap(str(logo_path)).scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        except ImportError:
            from PyQt5.QtGui import QPixmap
            pm = QPixmap(str(logo_path)).scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        logo_icon.setPixmap(pm)
        logo_icon.setStyleSheet("background: transparent; padding-left: 12px;")
        tb.addWidget(logo_icon)

        logo = QLabel(
            " <b style='color:#e63946; font-size:15px;'>ViperForge</b>"
            "  <span style='background:#3d0010; color:#ff6680; border:1px solid #e6394688;"
            " border-radius:3px; padding:1px 6px; font-size:9px; font-weight:bold;"
            " letter-spacing:1px;'>2.1.0-beta</span>"
            "  <span style='color:#666680; font-size:10px;'>Block Exploit Builder</span>"
        )
        logo.setTextFormat(_text_format_rich())
        logo.setStyleSheet("background: transparent; color: white; padding-right: 12px;")
        tb.addWidget(logo)

        spacer = QWidget()
        exp, pref = _sp(True)
        spacer.setSizePolicy(exp, pref)
        spacer.setStyleSheet("background: transparent;")
        tb.addWidget(spacer)

        # Buttons
        self._btn_save_ws = QPushButton(" Save WS")
        self._btn_save_ws.setIcon(qta.icon('fa5s.save', color='#00ff88'))
        self._btn_save_ws.setFixedHeight(32)
        tb.addWidget(self._btn_save_ws)

        self._btn_load_ws = QPushButton(" Load WS")
        self._btn_load_ws.setIcon(qta.icon('fa5s.folder-open', color='#00b4d8'))
        self._btn_load_ws.setFixedHeight(32)
        tb.addWidget(self._btn_load_ws)

        tb.addSeparator()

        self._btn_clear = QPushButton(" Clear Canvas")
        self._btn_clear.setIcon(qta.icon('fa5s.trash-alt', color='white'))
        self._btn_clear.setObjectName("btn_clear_canvas")
        self._btn_clear.setFixedHeight(32)
        tb.addWidget(self._btn_clear)

        tb.addSeparator()

        self._mode_label = QLabel(
            f"  Mode: <span style='color:{ACCENT_GOLD}; font-weight:bold;'>Single</span>"
        )
        self._mode_label.setTextFormat(_text_format_rich())
        self._mode_label.setStyleSheet("background: transparent; font-size:12px;")
        tb.addWidget(self._mode_label)

        tb.addSeparator()

        self._btn_generate = QPushButton(" GENERATE EXPLOIT")
        self._btn_generate.setIcon(qta.icon('fa5s.fire', color='#ffaa00'))
        self._btn_generate.setObjectName("btn_generate")
        self._btn_generate.setFixedHeight(34)
        tb.addWidget(self._btn_generate)

        tb.addSeparator()

        self._btn_macros = QPushButton(" Macros")
        self._btn_macros.setIcon(qta.icon('fa5s.layer-group', color='#ffd60a'))
        self._btn_macros.setFixedHeight(32)
        self._btn_macros.setToolTip("Saved macro blocks")
        tb.addWidget(self._btn_macros)

        return tb

    def _build_canvas_section(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Canvas info bar
        info_bar = QWidget()
        info_bar.setFixedHeight(32)
        info_bar.setStyleSheet(f"background: {BG_PANEL}; border-bottom: 1px solid {BORDER_DARK};")
        ib_layout = QHBoxLayout(info_bar)
        ib_layout.setContentsMargins(12, 0, 12, 0)

        self._canvas_info = QLabel("Canvas  ·  Scroll to zoom  ·  Drag blocks to rearrange  ·  Click connector ▼ to chain")
        self._canvas_info.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px; background: transparent;")
        ib_layout.addWidget(self._canvas_info)

        self._block_count_label = QLabel("0 blocks")
        self._block_count_label.setStyleSheet(f"color: {ACCENT_RED}; font-size: 11px; font-weight: bold; background: transparent;")
        ib_layout.addWidget(self._block_count_label, 0, _align_right())

        layout.addWidget(info_bar)

        # Validation bar (below info bar)
        self._validation_bar = self._build_validation_bar()
        layout.addWidget(self._validation_bar)

        # Canvas
        self.canvas = ExploitCanvas()
        layout.addWidget(self.canvas, 1)

        return widget

    def _build_validation_bar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("validation_bar")
        bar.setFixedHeight(0)   # hidden initially
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(12, 4, 12, 4)
        bar_layout.setSpacing(8)

        self._val_icon  = QLabel("")
        self._val_text  = QLabel("")
        self._val_text.setWordWrap(True)
        self._val_icon.setStyleSheet("font-size: 14px; background: transparent;")
        self._val_text.setStyleSheet("font-size: 11px; background: transparent;")

        bar_layout.addWidget(self._val_icon)
        bar_layout.addWidget(self._val_text, 1)

        return bar

    def _show_validation(self, issues) -> None:
        if not issues:
            self._validation_bar.setFixedHeight(0)
            self._validation_bar.hide()
            return

        # Show only errors and warnings — ignore INFO-only
        errors   = [i for i in issues if i.severity == V_ERROR]
        warnings = [i for i in issues if i.severity == V_WARNING]
        shown    = errors if errors else warnings

        # If there are only INFO items, hide the bar (no action needed)
        if not shown:
            self._validation_bar.setFixedHeight(0)
            self._validation_bar.hide()
            return

        if errors:
            bg, fg, icon_name = "#3d0010", "#ff4455", "fa5s.times-circle"
        else:
            bg, fg, icon_name = "#3d2b00", "#ffaa00", "fa5s.exclamation-triangle"

        self._validation_bar.setStyleSheet(
            f"background: {bg}; border-bottom: 1px solid {fg};"
        )
        self._val_icon.setPixmap(qta.icon(icon_name, color=fg).pixmap(14, 14))
        self._val_text.setStyleSheet(f"color: {fg}; font-size: 11px; background: transparent;")

        summary = shown[0].message
        if len(shown) > 1:
            summary += f"  (+{len(shown)-1} more issues)"
        self._val_text.setText(f"[{shown[0].block_name}]  {summary}")

        self._validation_bar.setFixedHeight(32)
        self._validation_bar.show()

    def _build_right_panel(self) -> QWidget:
        widget = QWidget()
        widget.setObjectName("right_panel")
        widget.setMinimumWidth(320)
        widget.setMaximumWidth(460)

        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Param panel (top 55%)
        self.param_panel = ParamPanel()
        layout.addWidget(self.param_panel, 55)

        # Divider
        div = QWidget()
        div.setFixedHeight(2)
        div.setStyleSheet(f"background: {BORDER_DARK};")
        layout.addWidget(div)

        # Preview panel (bottom 45%)
        self.preview_panel = PreviewPanel()
        layout.addWidget(self.preview_panel, 45)

        return widget

    # ─── Signal connections ──────────────────────────────────────────────────
    def _connect_signals(self) -> None:
        self.palette.exploit_selected.connect(self._on_exploit_selected)
        self.canvas.block_selected.connect(self._on_block_selected)
        self.canvas.canvas_changed.connect(self._on_canvas_changed)
        self.canvas.macro_requested.connect(self._on_macro_requested)
        self.param_panel.param_changed.connect(self._on_param_changed)
        self._btn_save_ws.clicked.connect(self._on_save_workspace)
        self._btn_load_ws.clicked.connect(self._on_load_workspace)
        self._btn_clear.clicked.connect(self._on_clear_canvas)
        self._btn_generate.clicked.connect(self._on_generate)
        self._btn_macros.clicked.connect(self._on_show_macros)

    # ─── Helpers ─────────────────────────────────────────────────────────────
    def _get_ordered_sessions(self):
        """Returns (blocks, sessions) in chain order."""
        blocks = self.canvas.get_chain_order()
        sessions = [self._block_sessions[b] for b in blocks if b in self._block_sessions]
        return blocks, sessions

    # ─── Event handlers ──────────────────────────────────────────────────────
    def _on_exploit_selected(self, exploit_def: ExploitDef) -> None:
        """Double click from palette -> add to canvas."""
        macro_def = getattr(exploit_def, '_macro_def', None)
        if macro_def is not None:
            self._add_macro_to_canvas(macro_def)
            return

        session = Session()
        session.set_exploit(exploit_def)

        block = self.canvas.add_block(exploit_def, session)
        self._block_sessions[block] = session

        # Auto select
        self._select_block(block)
        self._set_status(f"Added: {exploit_def.name}  [{exploit_def.category}]")

    def _on_block_selected(self, block: BlockItem) -> None:
        self._select_block(block)

    def _select_block(self, block: BlockItem) -> None:
        self._selected_block = block
        session = self._block_sessions.get(block)
        if session and block.exploit_def:
            self.param_panel.load_block(session, block.exploit_def)
            self._update_preview(session)

    def _on_param_changed(self) -> None:
        """Update preview and refresh block when parameter changes."""
        if self._selected_block:
            session = self._block_sessions.get(self._selected_block)
            if session:
                blocks, sessions = self._get_ordered_sessions()
                if len(sessions) > 1:
                    self.preview_panel.set_chain_code(preview_chain(sessions))
                else:
                    self._update_preview(session)
                self._selected_block.refresh()
                # Re-run validation
                issues = validate_chain(blocks, sessions)
                self._show_validation(issues)

    def _update_preview(self, session: Session) -> None:
        code = preview_single(session)
        self.preview_panel.set_single_code(code)

    def _on_canvas_changed(self) -> None:
        count = len(self.canvas.blocks)
        self._block_count_label.setText(f"{count} block{'s' if count != 1 else ''}")

        # Mode label
        if count > 1:
            self._mode_label.setText(
                f"  Mode: <span style='color:{ACCENT_RED}; font-weight:bold;'>Chain ({count} stages)</span>"
            )
        else:
            self._mode_label.setText(
                f"  Mode: <span style='color:{ACCENT_GOLD}; font-weight:bold;'>Single</span>"
            )

        # ── Purge deleted blocks from session map ─────────────────────────
        alive = set(self.canvas.blocks)
        dead  = [b for b in list(self._block_sessions.keys()) if b not in alive]
        for b in dead:
            del self._block_sessions[b]

        # ── If the selected block was deleted, clear the right panel ──────
        if self._selected_block not in alive:
            self._selected_block = None
            self.param_panel.clear()
            self.preview_panel.clear()

        # ── If canvas is empty, hide validation bar ───────────────────────
        if count == 0:
            self._show_validation([])
            return

        # Run validation and show banner
        blocks, sessions = self._get_ordered_sessions()
        if sessions:
            issues = validate_chain(blocks, sessions)
            self._show_validation(issues)
            # Update chain preview when connections change
            if len(sessions) > 1:
                self.preview_panel.set_chain_code(preview_chain(sessions))
            elif len(sessions) == 1 and self._selected_block:
                sess = self._block_sessions.get(self._selected_block)
                if sess:
                    self.preview_panel.set_single_code(preview_single(sess))
        else:
            self._show_validation([])

    def _on_clear_canvas(self) -> None:
        if self.canvas.blocks:
            reply = QMessageBox.question(
                self, "Clear Canvas",
                "Remove all blocks from the canvas?",
                _mb_yes_no(),
            )
            if reply != _mb_yes():
                return

        self.canvas.clear_canvas()
        self._block_sessions.clear()
        self._selected_block = None
        self.param_panel.clear()
        self.preview_panel.clear()
        self._set_status("Canvas cleared.")

    def _on_save_workspace(self) -> None:
        if not self.canvas.blocks:
            QMessageBox.warning(self, "Empty Canvas", "There are no blocks to save.")
            return

        out_dir = Path("workspaces")
        out_dir.mkdir(exist_ok=True)
        
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Workspace", str(out_dir / "chain.json"), "JSON Files (*.json);;All Files (*)"
        )
        if not path:
            return
            
        import json
        data = self.canvas.to_dict()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            self._set_status(f"[OK] Workspace saved to {path}")
        except Exception as e:
            QMessageBox.critical(self, "Error Saving Workspace", str(e))

    def _on_load_workspace(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Workspace", "workspaces", "JSON Files (*.json);;All Files (*)"
        )
        if not path:
            return
            
        import json
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            self._block_sessions.clear()
            self._selected_block = None
            self.param_panel.clear()
            self.preview_panel.clear()
                
            created_blocks = self.canvas.from_dict(data)
            for b in created_blocks:
                self._block_sessions[b] = b.session

            skipped = getattr(self.canvas, '_load_skipped_count', 0)
            if skipped:
                self._set_status(
                    f"[WARN] Workspace loaded from {path} — {skipped} block(s) could not be restored."
                )
                QMessageBox.warning(
                    self, "Workspace Partially Loaded",
                    f"{skipped} block(s) referenced an exploit or macro that no longer "
                    f"exists and were skipped. The remaining blocks loaded normally."
                )
            else:
                self._set_status(f"[OK] Workspace loaded from {path}")
        except Exception as e:
            QMessageBox.critical(self, "Error Loading Workspace", f"Failed to load workspace:\n{str(e)}")

    def _on_generate(self) -> None:
        blocks, sessions = self._get_ordered_sessions()
        if not sessions:
            QMessageBox.warning(self, "No Blocks", "Add at least one exploit block to the canvas.")
            return

        # Run validation first — block on errors
        issues = validate_chain(blocks, sessions)
        errors = [i for i in issues if i.severity == V_ERROR]
        if errors:
            err_text = "\n".join(str(i) for i in errors)
            QMessageBox.critical(
                self, "Chain Validation Failed",
                f"<b>Cannot generate: the following errors must be fixed first:</b><br><br>"
                f"<pre style='color:#ff4455;'>{err_text}</pre>"
            )
            return

        # Ask for save location
        default_name = (
            f"chain_exploit.py" if len(sessions) > 1
            else f"{sessions[0].active_exploit.name}_exploit.py"
        )
        out_dir = Path("output")
        out_dir.mkdir(exist_ok=True)

        out_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Exploit Script",
            str(out_dir / default_name),
            "Python Scripts (*.py);;All Files (*)",
        )
        if not out_path:
            return

        # Worker thread
        self._worker_thread = QThread()
        self._worker = GenerateWorker(sessions, chain=len(sessions) > 1, out_path=out_path)
        self._worker.moveToThread(self._worker_thread)
        self._worker_thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_generate_done)
        self._worker.error.connect(self._on_generate_error)
        self._worker.finished.connect(self._worker_thread.quit)
        self._worker.error.connect(self._worker_thread.quit)

        self._btn_generate.setEnabled(False)
        self._btn_generate.setIcon(qta.icon('fa5s.hourglass-half', color='#ffaa00'))
        self._btn_generate.setText(" Generating...")
        self._set_status("Generating exploit script...")
        self._worker_thread.start()

    def _on_generate_done(self, out_path: str) -> None:
        self._btn_generate.setEnabled(True)
        self._btn_generate.setIcon(qta.icon('fa5s.fire', color='#ffaa00'))
        self._btn_generate.setText(" GENERATE EXPLOIT")
        self._set_status(f"[OK]  Exploit saved: {out_path}")

        msg = QMessageBox(self)
        msg.setWindowTitle("Exploit Generated")
        msg.setIcon(_mb_icon_info())
        msg.setText(f"<b style='color:#00ff88;'>Exploit script generated successfully!</b>")
        msg.setInformativeText(f"<tt>{out_path}</tt>")
        msg.setStyleSheet(f"background: {BG_CARD}; color: {TEXT_PRIMARY};")
        msg.exec()

    def _on_generate_error(self, err: str) -> None:
        self._btn_generate.setEnabled(True)
        self._btn_generate.setIcon(qta.icon('fa5s.fire', color='#ffaa00'))
        self._btn_generate.setText(" GENERATE EXPLOIT")
        self._set_status(f"[ERROR]  Error: {err}")
        QMessageBox.critical(self, "Generation Failed", err)

    def _set_status(self, msg: str) -> None:
        self._status.showMessage(f"  {msg}")

    # ── Macro handlers ──────────────────────────────────────────────────────
    def _on_macro_requested(self, selected_blocks: list) -> None:
        """Canvas context menu -> Create Macro from selected blocks."""
        import uuid as _uuid
        # Gather block data and connections between them
        block_set = set(id(b) for b in selected_blocks)
        block_ids = {}
        blocks_data = []
        for b in selected_blocks:
            bid = str(_uuid.uuid4())
            block_ids[id(b)] = bid
            opts = dict(b.session.options)
            blocks_data.append({
                "uuid": bid,
                "exploit_id": b.exploit_def.id,
                "x": b.x(),
                "y": b.y(),
                "options": opts,
                "failure_enabled": getattr(b, '_failure_enabled', False),
            })

        conns_data = []
        for c in self.canvas._connectors:
            if id(c.src) in block_set and id(c.dst) in block_set:
                conns_data.append({
                    "src": block_ids.get(id(c.src), ""),
                    "dst": block_ids.get(id(c.dst), ""),
                    "port_type": c.port_type,
                })

        dialog = MacroDialog(blocks_data, conns_data, parent=self)
        dialog.macro_saved.connect(self._on_macro_saved)
        dialog.exec()

    def _on_macro_saved(self, name: str, desc: str,
                         blocks_data: list, conns_data: list) -> None:
        macro = create_macro_from_blocks(name, desc, blocks_data, conns_data)
        path = save_macro(macro)
        self._set_status(f"[OK]  Macro saved: {name} → {path}")
        # Refresh palette to show new macros
        self.palette.refresh_macros()

    def _on_show_macros(self) -> None:
        """Show menu of available macros to add to canvas."""
        macros = list_macros()
        if not macros:
            QMessageBox.information(
                self, "Macros",
                "No macros saved yet.\n\n"
                "You can create one by selecting 2+ blocks on the canvas,\n"
                "right-clicking, and choosing 'Create Macro'."
            )
            return

        from PyQt6.QtWidgets import QMenu
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{ background: #1a1a2e; color: {TEXT_PRIMARY}; border: 1px solid {BORDER_DARK}; }}
            QMenu::item:selected {{ background: {ACCENT_GOLD}; color: black; }}
        """)

        for m in macros:
            act = menu.addAction(
                qta.icon('fa5s.layer-group', color=ACCENT_GOLD),
                f"{m.name}  ({len(m.blocks)} blocks)"
            )
            act.triggered.connect(lambda checked, md=m: self._add_macro_to_canvas(md))

        menu.exec(self._btn_macros.mapToGlobal(
            self._btn_macros.rect().bottomLeft()
        ))

    def _add_macro_to_canvas(self, macro_def: MacroDef) -> None:
        """Add a macro block to the canvas."""
        session = Session()
        block = MacroBlockItem(macro_def, session)

        # Position
        if self.canvas.blocks:
            last = self.canvas.blocks[-1]
            x = last.x()
            y = last.y() + last.block_h + 80
        else:
            center = self.canvas.mapToScene(self.canvas.viewport().rect().center())
            x = center.x() - 110
            y = center.y() - 60

        block.setPos(x, y)
        self.canvas._scene.addItem(block)
        self.canvas._blocks.append(block)

        block.signals.clicked.connect(self.canvas._on_block_clicked)
        block.signals.moved.connect(self.canvas._on_block_moved)
        block.signals.connect_success_req.connect(self.canvas._on_connect_success_req)
        block.signals.connect_failure_req.connect(self.canvas._on_connect_failure_req)
        block.signals.delete_req.connect(self.canvas._on_block_delete_req)
        block.signals.failure_pin_toggled.connect(self.canvas._on_failure_pin_toggled)
        block.signals.macro_requested.connect(self.canvas.macro_requested.emit)

        self._block_sessions[block] = session
        self.canvas.canvas_changed.emit()
        self._set_status(f"Macro added: {macro_def.name}")
