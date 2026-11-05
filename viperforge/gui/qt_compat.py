"""
ViperForge — Qt Compat Layer
Falls back to PyQt5 if PyQt6 is not available.
"""

try:
    from PyQt6.QtWidgets import *
    from PyQt6.QtGui import *
    from PyQt6.QtCore import *
    QT_VERSION = 6
except ImportError:
    try:
        from PyQt5.QtWidgets import *
        from PyQt5.QtGui import *
        from PyQt5.QtCore import *
        # PyQt5 compat: GraphicsItemFlag and other enum differences
        import PyQt5.QtWidgets as _w
        import PyQt5.QtCore as _c

        # Enums are in a different place in PyQt5
        if not hasattr(QGraphicsItem, 'GraphicsItemFlag'):
            class _GIF:
                ItemIsMovable            = 0x1
                ItemIsSelectable         = 0x2
                ItemSendsGeometryChanges = 0x800
            QGraphicsItem.GraphicsItemFlag = _GIF

        if not hasattr(QGraphicsView, 'DragMode'):
            class _DM:
                RubberBandDrag = 1
                NoDrag = 0
            QGraphicsView.DragMode = _DM

        if not hasattr(QGraphicsView, 'ViewportAnchor'):
            class _VA:
                AnchorUnderMouse = 1
                AnchorViewCenter = 2
            QGraphicsView.ViewportAnchor = _VA

        QT_VERSION = 5
    except ImportError:
        raise ImportError(
            "Neither PyQt6 nor PyQt5 is installed.\n"
            "Install with:  pip install PyQt6\n"
            "Or fallback:   pip install PyQt5"
        )
