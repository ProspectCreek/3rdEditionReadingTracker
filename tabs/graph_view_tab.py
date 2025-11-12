# tabs/graph_view_tab.py
import sys
import math
import random
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene, QGraphicsItem,
    QGraphicsLineItem, QGraphicsEllipseItem, QGraphicsRectItem,
    QGraphicsSimpleTextItem, QApplication
)
from PySide6.QtCore import Qt, QTimer, QRectF, QPointF, QLineF, Signal, Slot
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QBrush, QPainterPath


# --- GRAPHICS ITEMS ---

class GraphEdgeItem(QGraphicsLineItem):
    """A simple line to connect two nodes."""

    def __init__(self, node1, node2, parent=None):
        super().__init__(parent)
        self.node1 = node1
        self.node2 = node2
        self.setZValue(-1)  # Draw behind nodes
        self.setPen(QPen(QColor("#555555"), 1.5))

    def adjust(self):
        """Updates the line position based on node centers."""
        line = QLineF(self.node1.pos(), self.node2.pos())
        self.setLine(line)


class BaseGraphNode(QGraphicsItem):
    """
    Base class for physics-enabled nodes.
    Handles forces, position, and edge management.
    """

    # --- FIX: Signals are REMOVED from this class. ---
    # QGraphicsItem does not inherit from QObject and cannot have signals.

    def __init__(self, data_id, name, data_type, parent_tab):
        super().__init__()
        self.data_id = data_id
        self.name = name
        self.data_type = data_type  # 'reading' or 'tag'
        self.parent_tab = parent_tab  # This is the GraphViewTab

        self.edges = []
        self.force_x = 0.0
        self.force_y = 0.0

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Simple text label, child of the node
        self.label = QGraphicsSimpleTextItem(self.name, self)
        self.label.setFont(QFont("Segoe UI", 9))
        self.label.setBrush(QColor("#000000"))
        # Center the label
        label_rect = self.label.boundingRect()
        self.label.setPos(-label_rect.width() / 2, -label_rect.height() / 2)

    def add_edge(self, edge):
        if edge not in self.edges:
            self.edges.append(edge)

    def adjust_edges(self):
        for edge in self.edges:
            edge.adjust()

    def calculate_forces(self, all_nodes, repulsion_strength, attraction_strength):
        """Calculate repulsion from all nodes and attraction from neighbors."""
        for node in all_nodes:
            if node is self:
                continue

            # --- Repulsion (from all nodes) ---
            dx = self.pos().x() - node.pos().x()
            dy = self.pos().y() - node.pos().y()
            distance = math.hypot(dx, dy) + 0.1  # avoid division by zero

            if distance < 250:  # Only repel if somewhat close
                # Coulomb's Law: F = k * (q1*q2) / r^2
                # We'll simplify: F = k / r
                repulsion = repulsion_strength / distance
                self.force_x += (dx / distance) * repulsion
                self.force_y += (dy / distance) * repulsion

        # --- Attraction (along edges) ---
        for edge in self.edges:
            other_node = edge.node1 if edge.node1 is not self else edge.node2

            # Hooke's Law: F = -k * x
            dx = other_node.pos().x() - self.pos().x()
            dy = other_node.pos().y() - self.pos().y()
            # No distance check, springs always pull
            self.force_x += dx * attraction_strength
            self.force_y += dy * attraction_strength

    def advance_position(self, damping):
        """Apply calculated forces to the node's position."""
        if math.hypot(self.force_x, self.force_y) < 0.1:
            self.force_x, self.force_y = 0.0, 0.0
            return False  # No significant movement

        # Apply damping
        self.force_x *= damping
        self.force_y *= damping

        # Update position
        self.setPos(self.pos().x() + self.force_x, self.pos().y() + self.force_y)

        # Reset forces for next tick
        self.force_x = 0.0
        self.force_y = 0.0
        return True  # Moved

    def itemChange(self, change, value):
        """Ensure edges update when the node is moved (by physics or user)."""
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self.adjust_edges()
        return super().itemChange(change, value)

    def doubleClickEvent(self, event):
        """
        FIX: Emit a signal by calling a method on the parent_tab (GraphViewTab),
        which IS a QObject and can emit signals.
        """
        if self.data_type == 'reading':
            print(f"Graph: Node clicked, calling parent tab for reading {self.data_id}")
            self.parent_tab.node_double_clicked(self.data_id, 'reading')
        elif self.data_type == 'tag':
            print(f"Graph: Node clicked, calling parent tab for tag {self.data_id}")
            self.parent_tab.node_double_clicked(self.data_id, 'tag')
        event.accept()


class ReadingNodeItem(BaseGraphNode):
    """A circular node representing a Reading."""

    def __init__(self, data_id, name, parent_tab):
        super().__init__(data_id, name, 'reading', parent_tab)
        self.setZValue(1)  # Draw nodes on top of edges

    def boundingRect(self):
        return QRectF(-20, -20, 40, 40)

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.boundingRect()

        # Draw shadow
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 50))
        painter.drawEllipse(rect.translated(2, 2))

        # Draw main circle
        pen_color = QColor("#003366")
        brush_color = QColor("#B0C4DE")  # Light Steel Blue
        if self.isSelected():
            pen_color = QColor("#FF0000")
            brush_color = QColor("#D8E0EB")

        painter.setPen(QPen(pen_color, 2))
        painter.setBrush(brush_color)
        painter.drawEllipse(rect)


class TagNodeItem(BaseGraphNode):
    """A square node representing a Tag."""

    def __init__(self, data_id, name, parent_tab):
        super().__init__(data_id, name, 'tag', parent_tab)
        self.setZValue(1)

    def boundingRect(self):
        return QRectF(-15, -15, 30, 30)

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.boundingRect()

        # Draw shadow
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 50))
        painter.drawRoundedRect(rect.translated(2, 2), 5, 5)

        # Draw main rectangle
        pen_color = QColor("#006400")  # Dark Green
        brush_color = QColor("#C8E6C9")  # Light Green
        if self.isSelected():
            pen_color = QColor("#FF0000")
            brush_color = QColor("#E3F0E3")

        painter.setPen(QPen(pen_color, 2))
        painter.setBrush(brush_color)
        painter.drawRoundedRect(rect, 5, 5)


# --- MAIN TAB WIDGET ---

class GraphViewTab(QWidget):
    """
    Main widget for the "Graph View" tab.
    Manages the scene, view, and physics simulation.
    """
    # Signals for interactivity (to be connected by the dashboard)
    readingDoubleClicked = Signal(int)  # Emits reading_id
    tagDoubleClicked = Signal(int)  # Emits tag_id

    def __init__(self, db, project_id, parent=None):
        super().__init__(parent)
        self.db = db
        self.project_id = project_id

        self.nodes = {}  # Stores all node items, keyed by "r_ID" or "t_ID"
        self.edges = []  # Stores all edge items

        # --- UI Setup ---
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.scene = QGraphicsScene(self)
        self.scene.setBackgroundBrush(QColor("#F8F8F8"))

        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.view.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.view.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)

        main_layout.addWidget(self.view)

        # --- Physics Timer ---
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_forces)
        self._simulation_steps = 0
        self.REPULSION = 10000
        self.ATTRACTION = 0.01
        self.DAMPING = 0.95

    def load_graph(self):
        """
        Clears the scene and builds a new graph from database data.
        Called by the dashboard when this tab becomes visible.
        """
        # Stop simulation if it's running
        self.timer.stop()

        # Clear old items
        self.scene.clear()
        self.nodes.clear()
        self.edges.clear()

        # Get data from DB
        try:
            data = self.db.get_graph_data(self.project_id)
        except Exception as e:
            print(f"Error loading graph data: {e}")
            return

        # 1. Create all nodes
        for reading in data['readings']:
            node_key = f"r_{reading['id']}"
            node_item = ReadingNodeItem(reading['id'], reading['name'], self)
            # --- FIX: REMOVED connect call ---
            self.scene.addItem(node_item)
            self.nodes[node_key] = node_item

        for tag in data['tags']:
            node_key = f"t_{tag['id']}"
            node_item = TagNodeItem(tag['id'], tag['name'], self)
            # --- FIX: REMOVED connect call ---
            self.scene.addItem(node_item)
            self.nodes[node_key] = node_item

        # 2. Create all edges
        for edge in data['edges']:
            from_key = f"r_{edge['reading_id']}"
            to_key = f"t_{edge['tag_id']}"

            if from_key in self.nodes and to_key in self.nodes:
                node1 = self.nodes[from_key]
                node2 = self.nodes[to_key]

                edge_item = GraphEdgeItem(node1, node2)
                self.scene.addItem(edge_item)
                self.edges.append(edge_item)
                node1.add_edge(edge_item)
                node2.add_edge(edge_item)

        if not self.nodes:
            return  # No graph to draw

        # 3. Randomly position nodes to start
        scene_size = 500 * math.sqrt(len(self.nodes))
        for node in self.nodes.values():
            node.setPos(random.uniform(-scene_size, scene_size),
                        random.uniform(-scene_size, scene_size))

        # 4. Start the physics simulation
        self._simulation_steps = 0
        self.timer.start(16)  # ~60 FPS

    @Slot()
    def _update_forces(self):
        """One tick of the physics simulation."""
        if not self.nodes:
            self.timer.stop()
            return

        all_nodes = list(self.nodes.values())

        # Calculate all forces
        for node in all_nodes:
            node.calculate_forces(all_nodes, self.REPULSION, self.ATTRACTION)

        # Apply all forces
        has_moved = False
        for node in all_nodes:
            if node.advance_position(self.DAMPING):
                has_moved = True

        # Adjust all edges
        for edge in self.edges:
            edge.adjust()

        # Stop simulation if it's stable or has run long enough
        self._simulation_steps += 1
        if not has_moved or self._simulation_steps > 150:  # ~2.5 seconds
            self.timer.stop()
            self._center_graph()
            print("Graph simulation complete.")

    def _center_graph(self):
        """Fits the view to the items after simulation."""
        try:
            bounds = self.scene.itemsBoundingRect().adjusted(-50, -50, 50, 50)
            if bounds.isValid():
                self.view.fitInView(bounds, Qt.AspectRatioMode.KeepAspectRatio)
        except Exception as e:
            print(f"Error centering graph: {e}")

    def showEvent(self, event):
        """Override showEvent to re-center the graph without re-running simulation."""
        super().showEvent(event)
        if not self.timer.isActive():
            QTimer.singleShot(10, self._center_graph)

    # --- NEW: Slot to receive click from node ---
    @Slot(int, str)
    def node_double_clicked(self, data_id, data_type):
        """Called by a node item on double-click."""
        if data_type == 'reading':
            self.readingDoubleClicked.emit(data_id)
        elif data_type == 'tag':
            self.tagDoubleClicked.emit(data_id)
    # --- END NEW ---