# prospectcreek/3rdeditionreadingtracker/tabs/graph_helpers.py
import sys
import math
from PySide6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsItem, QGraphicsLineItem,
    QGraphicsTextItem, QGraphicsDropShadowEffect, QLineEdit,
    QGraphicsProxyWidget
)
from PySide6.QtCore import Qt, QPointF, QRectF, QTimer, Signal, Slot, QLineF
from PySide6.QtGui import QPainter, QBrush, QColor, QPen, QFont, QPainterPath


class ZoomableGraphicsView(QGraphicsView):
    """A QGraphicsView that zooms with Ctrl+Wheel."""

    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setMouseTracking(True)

    def wheelEvent(self, event):
        """Zooms the view on Ctrl+Mouse Wheel."""
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            zoom_in_factor = 1.15
            zoom_out_factor = 1 / zoom_in_factor

            old_pos = self.mapToScene(event.position().toPoint())

            if event.angleDelta().y() > 0:
                self.scale(zoom_in_factor, zoom_in_factor)
            else:
                self.scale(zoom_out_factor, zoom_out_factor)

            new_pos = self.mapToScene(event.position().toPoint())

            delta = new_pos - old_pos
            self.translate(delta.x(), delta.y())

            event.accept()
        else:
            super().wheelEvent(event)


class GraphEdgeItem(QGraphicsLineItem):
    """A custom edge for the graph."""

    def __init__(self, from_node, to_node, parent=None):
        super().__init__(parent)
        self.from_node = from_node
        self.to_node = to_node
        self.setZValue(-1)
        self.setPen(QPen(QColor("#555"), 2))

    def update_position(self):
        if not self.from_node or not self.to_node:
            return
        from_point = self.from_node.get_connection_point(self.to_node.pos())
        to_point = self.to_node.get_connection_point(self.from_node.pos())
        self.setLine(QLineF(from_point, to_point))

    def set_highlight_state(self, highlight):
        """Sets the visual state of the edge."""
        if highlight:
            self.setOpacity(1.0)
            self.setPen(QPen(QColor("#000"), 2.5))
        else:
            self.setOpacity(0.2)
            self.setPen(QPen(QColor("#aaa"), 1.5))

    def reset_highlight_state(self):
        """Resets to default."""
        self.setOpacity(1.0)
        self.setPen(QPen(QColor("#555"), 2))


class ObsidianNodeItem(QGraphicsItem):
    """
    A new node item inspired by Obsidian.
    It renders as a colored circle with a text label *below* it.
    """

    NODE_RADIUS = 12

    def __init__(self, node_id, name, node_type, data, fill_color, border_color, graph_view, parent=None):
        super().__init__(parent)
        self.node_id = node_id
        self.name = name
        self.node_type = node_type
        self.data = data  # Stores IDs and extra info
        self.graph_view = graph_view
        self.edges = []

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setCacheMode(QGraphicsItem.CacheMode.DeviceCoordinateCache)
        self.setZValue(1)
        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(Qt.MouseButton.RightButton | Qt.MouseButton.LeftButton)

        # 1. The Text Label
        self.text_item = QGraphicsTextItem(self)
        self.text_item.setPlainText(self.name)
        self.text_item.setFont(QFont("Arial", 9))
        self.text_item.setDefaultTextColor(QColor("#333"))

        # Center the text horizontally under the node
        text_rect = self.text_item.boundingRect()
        self.text_item.setPos(-text_rect.width() / 2, self.NODE_RADIUS + 2)

        # 2. The Circle Colors (passed in)
        self.fill_color = fill_color
        self.border_color = border_color

        # 3. Tooltip
        self.update_node_scale_and_tooltip()

        # 4. Shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(1, 1)
        self.setGraphicsEffect(shadow)

    def boundingRect(self):
        """The bounding rect must include the circle AND the text below it."""
        circle_rect = QRectF(-self.NODE_RADIUS, -self.NODE_RADIUS, self.NODE_RADIUS * 2, self.NODE_RADIUS * 2)
        text_rect = self.text_item.boundingRect().translated(self.text_item.pos())
        return circle_rect.united(text_rect)

    def shape(self):
        """The shape for collision and selection is just the circle."""
        path = QPainterPath()
        path.addEllipse(QPointF(0, 0), self.NODE_RADIUS, self.NODE_RADIUS)
        return path

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw Circle
        brush = QBrush(self.fill_color)
        pen = QPen(self.border_color, 1.5)

        if self.isSelected():
            pen.setColor(QColor("#00AEEB"))  # Bright cyan for selection
            pen.setWidth(3)

        painter.setPen(pen)
        painter.setBrush(brush)
        painter.drawEllipse(QPointF(0, 0), self.NODE_RADIUS, self.NODE_RADIUS)

        # Text is a child item, so it paints itself

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            for edge in self.edges:
                edge.update_position()

        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedChange:
            if self.scene():
                if hasattr(self.scene(), 'update_highlights'):
                    QTimer.singleShot(0, self.scene().update_highlights)

        return super().itemChange(change, value)

    def mouseDoubleClickEvent(self, event):
        """Emit the correct signal based on node type."""
        if self.node_type == 'reading':
            self.graph_view.emit_reading_double_clicked(self.data.get('reading_id', 0))
        elif self.node_type == 'tag':
            self.graph_view.emit_tag_double_clicked(self.data.get('tag_id', 0))
        elif self.data.get('anchor_id'):
            self.graph_view.emit_anchor_double_clicked(self.data.get('anchor_id', 0))
        event.accept()

    def add_edge(self, edge):
        if edge not in self.edges:
            self.edges.append(edge)

    def get_connection_point(self, to_point):
        """Finds the intersection point on the node's circle edge."""
        center_point = self.pos()
        line = QLineF(center_point, to_point)
        if line.length() == 0:
            return center_point

        # Calculate point on the circumference
        angle = line.angle()
        dx = self.NODE_RADIUS * math.cos(math.radians(angle))
        dy = -self.NODE_RADIUS * math.sin(math.radians(angle))  # y-axis is inverted

        return center_point + QPointF(dx, dy)

    def get_connected_nodes(self):
        nodes = set()
        for edge in self.edges:
            if edge.from_node == self:
                nodes.add(edge.to_node)
            else:
                nodes.add(edge.from_node)
        return nodes

    def update_node_scale_and_tooltip(self):
        """Sets the node's scale and tooltip."""
        connection_count = len(self.edges)

        # Scale based on connections
        scale_factor = 1.0 + (math.sqrt(connection_count) / 4.0)
        self.setScale(scale_factor)

        # Set tooltip
        tooltip_parts = [f"Name: {self.name}"]
        if self.node_type == 'reading':
            if self.data.get('full_title') and self.data['full_title'] != self.name:
                tooltip_parts.append(f"Title: {self.data['full_title']}")
            if self.data.get('author'):
                tooltip_parts.append(f"Author: {self.data['author']}")
        elif self.node_type == 'tag':
            tooltip_parts = [f"Tag: {self.name}"]
        elif self.data.get('summary_text'):
            tooltip_parts = [f"Type: {self.data.get('item_type', 'item')}", f"Text: {self.data['summary_text']}"]

        tooltip_parts.append(f"Connections: {connection_count}")
        self.setToolTip("\n".join(tooltip_parts))

    def set_highlight_state(self, highlight):
        if highlight:
            self.setOpacity(1.0)
            self.setZValue(2)
        else:
            self.setOpacity(0.2)
            self.setZValue(1)

    def reset_highlight_state(self):
        self.setOpacity(1.0)
        self.setZValue(1)

    def set_colors(self, fill_color, border_color):
        """Public method to update colors from the control panel."""
        self.fill_color = fill_color
        self.border_color = border_color
        self.update()  # Trigger a repaint

    def start_rename_editor(self):
        """Starts the inline QLineEdit editor for renaming."""
        # This is slightly different; the text is a child, not part of this item
        if hasattr(self, 'line_edit'):
            return  # Already editing

        self.line_edit = QLineEdit()
        self.line_edit.setText(self.name.strip())
        self.line_edit.selectAll()

        self.proxy = self.scene().addWidget(self.line_edit)
        self.proxy.setParentItem(self)

        # Position the proxy widget where the text item is
        text_rect = self.text_item.boundingRect()
        self.proxy.setPos(self.text_item.pos())
        self.proxy.resize(text_rect.width() + 10, text_rect.height())  # Give a little extra width

        self.text_item.hide()
        self.line_edit.setFocus()

        self.line_edit.editingFinished.connect(self._on_rename_finished)

    @Slot()
    def _on_rename_finished(self):
        """Handles when editing is finished."""
        if not hasattr(self, 'line_edit'):
            return

        new_name = self.line_edit.text().strip()

        self.proxy.setParentItem(None)
        self.scene().removeItem(self.proxy)
        del self.proxy
        del self.line_edit
        self.text_item.show()

        if new_name and new_name != self.name:
            self.name = new_name
            # Update text item and its position
            self.text_item.setPlainText(self.name)
            text_rect = self.text_item.boundingRect()
            self.text_item.setPos(-text_rect.width() / 2, self.NODE_RADIUS + 2)
            self.update()  # Update bounding rect

            if self.node_type == 'reading':
                self.graph_view.rename_reading(self.data['reading_id'], new_name)
            elif self.node_type == 'tag':
                self.graph_view.rename_tag(self.data['tag_id'], new_name)


class ObsidianGraphScene(QGraphicsScene):
    """Custom scene to manage highlight updates for new node type."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.all_nodes = []
        self.all_edges = []

    def update_highlights(self):
        selected_nodes = self.selectedItems()

        if not selected_nodes:
            for node in self.all_nodes:
                node.reset_highlight_state()
            for edge in self.all_edges:
                edge.reset_highlight_state()
            return

        highlight_set = set(selected_nodes)
        edges_to_highlight = set()

        for node in selected_nodes:
            if isinstance(node, ObsidianNodeItem):
                for edge in node.edges:
                    edges_to_highlight.add(edge)
                    highlight_set.add(edge.from_node)
                    highlight_set.add(edge.to_node)

        for node in self.all_nodes:
            node.set_highlight_state(node in highlight_set)

        for edge in self.all_edges:
            edge.set_highlight_state(edge in edges_to_highlight)

    def clear_graph(self):
        self.clear()
        self.all_nodes.clear()
        self.all_edges.clear()

    def add_node(self, node):
        self.all_nodes.append(node)
        self.addItem(node)

    def add_edge(self, edge):
        self.all_edges.append(edge)
        self.addItem(edge)