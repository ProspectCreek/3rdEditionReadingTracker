# tabs/graph_view_tab.py
import sys
import math
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene,
    QGraphicsItem, QGraphicsLineItem, QGraphicsTextItem,
    QGraphicsEllipseItem, QGraphicsRectItem, QMenu, QGraphicsSceneMouseEvent,
    QMessageBox, QApplication
)
from PySide6.QtCore import Qt, QPointF, QRectF, QTimer, Signal, Slot, QLineF
from PySide6.QtGui import QPainter, QBrush, QColor, QPen, QFont, QPainterPath

# --- Constants for dynamic node sizing ---
NODE_MIN_WIDTH = 100
NODE_MIN_HEIGHT = 40
H_PAD = 20  # Horizontal padding
V_PAD = 10  # Vertical padding


# --- END ---


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


class BaseGraphNode(QGraphicsItem):
    """Base class for all nodes in the graph."""

    def __init__(self, name, graph_view, parent=None):
        super().__init__(parent)
        self.name = name
        self.graph_view = graph_view
        self.edges = []

        # --- DYNAMIC SIZING ---
        self.text_item = QGraphicsTextItem(self.name, self)
        font = QFont("Arial", 10)
        self.text_item.setFont(font)
        self.update_geometry()
        # --- END DYNAMIC SIZING ---

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setCacheMode(QGraphicsItem.CacheMode.DeviceCoordinateCache)
        self.setZValue(1)

    def update_geometry(self):
        """Calculates the node's bounds based on its text."""
        self.prepareGeometryChange()

        self.text_item.setTextWidth(-1)
        text_rect = self.text_item.boundingRect()

        self.width = max(NODE_MIN_WIDTH, text_rect.width() + H_PAD)

        self.text_item.setTextWidth(self.width - H_PAD)
        text_rect = self.text_item.boundingRect()

        self.height = max(NODE_MIN_HEIGHT, text_rect.height() + V_PAD)

        text_x = -text_rect.width() / 2
        text_y = -text_rect.height() / 2
        self.text_item.setPos(text_x, text_y)

    def boundingRect(self):
        """Returns the dynamically calculated bounding rect."""
        return QRectF(-self.width / 2, -self.height / 2, self.width, self.height)

    def shape(self):
        """Returns the precise shape for collision detection and painting."""
        path = QPainterPath()
        path.addRect(self.boundingRect())
        return path

    def add_edge(self, edge):
        if edge not in self.edges:
            self.edges.append(edge)

    def get_connected_nodes(self):
        """Returns a set of all nodes connected to this one."""
        nodes = set()
        for edge in self.edges:
            if edge.from_node == self:
                nodes.add(edge.to_node)
            else:
                nodes.add(edge.from_node)
        return nodes

    def get_connection_point(self, to_point):
        """Finds the intersection point on the node's bounding box."""
        center_point = self.pos()
        rect = self.boundingRect().translated(center_point)

        center_line = QLineF(center_point, to_point)
        if center_line.length() == 0:
            return center_point

        lines = [
            QLineF(rect.topLeft(), rect.topRight()),
            QLineF(rect.topRight(), rect.bottomRight()),
            QLineF(rect.bottomRight(), rect.bottomLeft()),
            QLineF(rect.bottomLeft(), rect.topLeft())
        ]

        intersect_points = []
        for line in lines:
            try:
                intersect_type, intersect_point = center_line.intersects(line)
                if intersect_type == QLineF.IntersectionType.BoundedIntersection:
                    intersect_points.append(intersect_point)
            except Exception:
                intersect_point = QPointF()
                intersect_type = line.intersect(center_line, intersect_point)
                if intersect_type == QLineF.IntersectionType.BoundedIntersection:
                    intersect_points.append(intersect_point)

        if intersect_points:
            intersect_points.sort(key=lambda p: QLineF(p, to_point).length())
            return intersect_points[0]

        return center_point

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            for edge in self.edges:
                edge.update_position()

        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedChange:
            if self.scene():
                if hasattr(self.scene(), 'update_highlights'):
                    self.scene().update_highlights()

        return super().itemChange(change, value)

    def mouseDoubleClickEvent(self, event):
        """Placeholder for subclasses to implement."""
        print(f"Node '{self.name}' double-clicked (Base)")
        super().mouseDoubleClickEvent(event)

    def paint(self, painter, option, widget):
        """Overridden by subclasses to draw specific shapes."""
        pass

    def set_highlight_state(self, highlight):
        """Sets the visual state of the node."""
        if highlight:
            self.setOpacity(1.0)
            self.setZValue(2)
        else:
            self.setOpacity(0.2)
            self.setZValue(1)

    def reset_highlight_state(self):
        """Resets to default."""
        self.setOpacity(1.0)
        self.setZValue(1)


class ReadingNodeItem(BaseGraphNode):
    """A node representing a Reading."""

    def __init__(self, reading_id, name, graph_view, parent=None):
        self.reading_id = reading_id
        super().__init__(name, graph_view, parent)

    def shape(self):
        path = QPainterPath()
        path.addEllipse(self.boundingRect())
        return path

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = self.shape()

        brush = QBrush(QColor("#cce0f5"))
        painter.fillPath(path, brush)

        pen = QPen(QColor("#0047b2"), 2)
        painter.setPen(pen)
        painter.drawPath(path)

    def mouseDoubleClickEvent(self, event):
        print(f"Reading node '{self.name}' double-clicked")
        self.graph_view.emit_reading_double_clicked(self.reading_id)
        super().mouseDoubleClickEvent(event)


class TagNodeItem(BaseGraphNode):
    """A node representing a Tag."""

    def __init__(self, tag_id, name, graph_view, parent=None):
        self.tag_id = tag_id
        super().__init__(name, graph_view, parent)

    def shape(self):
        path = QPainterPath()
        path.addRoundedRect(self.boundingRect(), 5, 5)
        return path

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = self.shape()

        brush = QBrush(QColor("#cce8cc"))
        painter.fillPath(path, brush)

        pen = QPen(QColor("#006100"), 2)
        painter.setPen(pen)
        painter.drawPath(path)

    def mouseDoubleClickEvent(self, event):
        print(f"Tag node '{self.name}' double-clicked")
        self.graph_view.emit_tag_double_clicked(self.tag_id)
        super().mouseDoubleClickEvent(event)


class GraphViewScene(QGraphicsScene):
    """Custom scene to manage highlight updates."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.all_nodes = []
        self.all_edges = []

    def update_highlights(self):
        """
        Updates the opacity of all nodes and edges based on the
        current selection.
        """
        selected_nodes = self.selectedItems()

        if not selected_nodes:
            # No selection, reset everything
            for node in self.all_nodes:
                node.reset_highlight_state()
            for edge in self.all_edges:
                edge.reset_highlight_state()
            return

        highlight_set = set(selected_nodes)
        edges_to_highlight = set()

        for node in selected_nodes:
            if isinstance(node, BaseGraphNode):
                for edge in node.edges:
                    edges_to_highlight.add(edge)
                    highlight_set.add(edge.from_node)
                    highlight_set.add(edge.to_node)

        for node in self.all_nodes:
            node.set_highlight_state(node in highlight_set)

        for edge in self.all_edges:
            edge.set_highlight_state(edge in edges_to_highlight)

    def clear_graph(self):
        """Clears all items and internal lists."""
        self.clear()
        self.all_nodes.clear()
        self.all_edges.clear()

    def add_node(self, node):
        self.all_nodes.append(node)
        self.addItem(node)

    def add_edge(self, edge):
        self.all_edges.append(edge)
        self.addItem(edge)


class GraphViewTab(QWidget):
    """
    Main widget for the "Graph View" tab.
    """
    readingDoubleClicked = Signal(int)
    tagDoubleClicked = Signal(int)

    def __init__(self, db_manager, project_id, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.project_id = project_id

        self.nodes = {}
        self.edges = []

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.scene = GraphViewScene(self)
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        main_layout.addWidget(self.view)

        self.view.mousePressEvent = self.view_mouse_press

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_physics)
        self.timer.start(16)

    def view_mouse_press(self, event):
        """
        Overrides the view's mouse press event to clear selection
        when the background is clicked.
        """
        item_at_pos = self.view.itemAt(event.pos())

        if item_at_pos is None and event.button() == Qt.MouseButton.LeftButton:
            self.scene.clearSelection()
            self.scene.update_highlights()
            event.accept()
            return

        super(QGraphicsView, self.view).mousePressEvent(event)

    @Slot(int)
    def emit_reading_double_clicked(self, reading_id):
        self.readingDoubleClicked.emit(reading_id)

    @Slot(int)
    def emit_tag_double_clicked(self, tag_id):
        self.tagDoubleClicked.emit(tag_id)

    def load_graph(self):
        """Fetches data from the DB and builds the graph."""
        if not self.db or self.project_id is None:
            return

        self.scene.clear_graph()
        self.nodes.clear()
        self.edges.clear()

        try:
            data = self.db.get_graph_data(self.project_id)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load graph data: {e}")
            return

        pos_x, pos_y = 0, 0
        for reading in data['readings']:
            node_id = f"r_{reading['id']}"
            node_item = ReadingNodeItem(reading['id'], reading['name'], self)
            node_item.setPos(pos_x, pos_y)
            self.scene.add_node(node_item)
            self.nodes[node_id] = node_item
            pos_x += 50

        for tag in data['tags']:
            node_id = f"t_{tag['id']}"
            node_item = TagNodeItem(tag['id'], tag['name'], self)
            node_item.setPos(pos_x, pos_y + 100)
            self.scene.add_node(node_item)
            self.nodes[node_id] = node_item
            pos_x += 50

        for edge in data['edges']:
            from_id = f"r_{edge['reading_id']}"
            to_id = f"t_{edge['tag_id']}"

            if from_id in self.nodes and to_id in self.nodes:
                from_node = self.nodes[from_id]
                to_node = self.nodes[to_id]

                edge_item = GraphEdgeItem(from_node, to_node)
                self.scene.add_edge(edge_item)
                self.edges.append(edge_item)

                from_node.add_edge(edge_item)
                to_node.add_edge(edge_item)

        if self.nodes:
            self.view.setSceneRect(self.scene.itemsBoundingRect().adjusted(-50, -50, 50, 50))

    def update_physics(self):
        """Simple physics simulation for the graph."""
        if not self.nodes:
            return

        # --- FIX: Tuned constants to be more stable ---
        K_REPEL = 20000  # Repulsion force
        K_ATTRACT = 0.02  # Attraction force (spring) - WAS 0.05
        DAMPING = 0.85  # Damping factor - WAS 0.95
        CENTER_PULL = 0.002  # Force pulling nodes to center - WAS 0.001
        MIN_DIST = 10.0  # Minimum distance to avoid division by zero
        # --- END FIX ---

        node_list = list(self.nodes.values())

        for i, node_a in enumerate(node_list):
            if node_a.isSelected():
                if hasattr(node_a, 'velocity'):
                    node_a.velocity = QPointF(0, 0)
                continue

            force = QPointF(0, 0)

            # 1. Repulsion from all other nodes
            for j, node_b in enumerate(node_list):
                if i == j:
                    continue

                delta = node_a.pos() - node_b.pos()
                dist_sq = max(MIN_DIST, QPointF.dotProduct(delta, delta))

                repel_force = K_REPEL / dist_sq

                dist = math.sqrt(dist_sq)
                force += (delta / dist) * repel_force

            # 2. Attraction from connected nodes (edges)
            for edge in node_a.edges:
                other_node = edge.from_node if edge.to_node == node_a else edge.to_node

                if other_node.isSelected():
                    continue

                delta = other_node.pos() - node_a.pos()
                dist_sq = max(MIN_DIST, QPointF.dotProduct(delta, delta))

                dist = math.sqrt(dist_sq)
                attract_force = dist * K_ATTRACT  # Correct spring force F = k * x

                force += (delta / dist) * attract_force

            # 3. Pull towards center
            center_delta = -node_a.pos()
            force += center_delta * CENTER_PULL

            # Apply force
            if not hasattr(node_a, 'velocity'):
                node_a.velocity = QPointF(0, 0)

            node_a.velocity = (node_a.velocity + force) * DAMPING

            if not (node_a.isUnderMouse() and QApplication.mouseButtons() & Qt.MouseButton.LeftButton):
                node_a.setPos(node_a.pos() + node_a.velocity)

        # Update all edge positions
        for edge in self.edges:
            edge.update_position()