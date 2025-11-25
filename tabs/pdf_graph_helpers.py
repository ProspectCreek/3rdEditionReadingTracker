# tabs/pdf_graph_helpers.py
import sys
from PySide6.QtWidgets import (
    QGraphicsEllipseItem, QMenu, QInputDialog, QGraphicsItem, QStyle
)
from PySide6.QtGui import QPen, QBrush, QColor, QCursor, QFont
from PySide6.QtCore import Qt


class PdfMarkerNode(QGraphicsEllipseItem):
    """
    A QGraphicsItem representing a spatial node on a PDF page.
    """

    def __init__(self, x, y, radius, node_data, viewer_ref):
        # Start centered at x, y
        super().__init__(-radius / 2, -radius / 2, radius, radius)
        self.setPos(x, y)

        self.node_data = node_data  # dict with id, label, color_hex, category_color, etc.
        self.viewer_ref = viewer_ref  # Reference to the parent viewer for callbacks

        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
                      QGraphicsItem.GraphicsItemFlag.ItemIsMovable)

        # Build tooltip
        tooltip = f"{self.node_data.get('label', 'Node')}"
        if self.node_data.get('category_name'):
            tooltip += f"\nCategory: {self.node_data['category_name']}"
        if self.node_data.get('description'):
            tooltip += f"\n{self.node_data['description']}"

        self.setToolTip(tooltip)

        # Initial Style
        self.update_visuals()

    def update_visuals(self):
        """Updates color and size based on data. Prioritize category color."""
        # Use category_color if present, otherwise fallback to individual color_hex, then default
        color_hex = self.node_data.get('category_color') or self.node_data.get('color_hex') or '#FFFF00'

        self.setBrush(QBrush(QColor(color_hex)))
        self.setPen(QPen(Qt.GlobalColor.black, 1))

    def mousePressEvent(self, event):
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        # Update position in DB after drag
        new_pos = self.pos()
        self.viewer_ref.update_node_position(self.node_data['id'], new_pos.x(), new_pos.y())

    def contextMenuEvent(self, event):
        menu = QMenu()
        rename_action = menu.addAction("Edit Node")
        rename_action.triggered.connect(self.edit_node)
        delete_action = menu.addAction("Delete Node")
        delete_action.triggered.connect(self.delete_node)
        menu.exec(QCursor.pos())

    def edit_node(self):
        self.viewer_ref.edit_node_dialog(self.node_data['id'])

    def delete_node(self):
        self.viewer_ref.delete_node(self.node_data['id'])

    def paint(self, painter, option, widget):
        # Remove selection dotted line for cleaner look
        option.state &= ~QStyle.StateFlag.State_Selected
        super().paint(painter, option, widget)