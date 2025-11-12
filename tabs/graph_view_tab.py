# tabs/graph_view_tab.py
import sys
import math
import sqlite3
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene,
    QGraphicsItem, QGraphicsLineItem, QGraphicsTextItem,
    QGraphicsEllipseItem, QGraphicsRectItem, QMenu, QGraphicsSceneMouseEvent,
    QMessageBox, QApplication, QGraphicsDropShadowEffect, QLineEdit,
    QGraphicsProxyWidget
)
from PySide6.QtCore import (
    Qt, QPointF, QRectF, QTimer, Signal, Slot, QLineF,
    QPoint
)
from PySide6.QtGui import QPainter, QBrush, QColor, QPen, QFont, QPainterPath, QFontMetrics

try:
    from dialogs.edit_tag_dialog import EditTagDialog
except ImportError:
    print("Error: Could not import EditTagDialog for GraphViewTab")
    EditTagDialog = None

# --- Constants for dynamic node sizing ---
NODE_MIN_WIDTH = 100
NODE_MIN_HEIGHT = 40
H_PAD = 20  # Horizontal padding
V_PAD = 10  # Vertical padding


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


class BaseGraphNode(QGraphicsItem):
    """Base class for all nodes in the graph."""

    def __init__(self, name, graph_view, parent=None):
        super().__init__(parent)
        self.name = name
        self.graph_view = graph_view
        self.edges = []

        self.text_item = QGraphicsTextItem(self)
        font = QFont("Arial", 10)
        self.text_item.setFont(font)
        self.update_geometry()

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setCacheMode(QGraphicsItem.CacheMode.DeviceCoordinateCache)
        self.setZValue(1)

        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(Qt.MouseButton.RightButton | Qt.MouseButton.LeftButton)

    def update_geometry(self):
        """Calculates the node's bounds based on its text."""
        self.prepareGeometryChange()

        font = QFont("Arial", 10)
        self.text_item.setFont(font)

        self.text_item.setPlainText(self.name)

        self.text_item.setTextWidth(-1)
        text_rect = self.text_item.boundingRect()

        self.width = max(NODE_MIN_WIDTH, text_rect.width() + H_PAD)

        self.text_item.setTextWidth(self.width - H_PAD)
        text_rect = self.text_item.boundingRect()

        self.height = max(NODE_MIN_HEIGHT, text_rect.height() + V_PAD)

        text_x = -text_rect.width() / 2
        text_y = -text_rect.height() / 2
        self.text_item.setPos(text_x, text_y)

    def update_node_scale_and_tooltip(self):
        """Sets the node's scale and tooltip based on its connection count."""
        connection_count = len(self.edges)

        scale_factor = 1.0 + (math.sqrt(connection_count) / 2.5)
        self.setScale(scale_factor)

        tooltip_parts = [f"Name: {self.name}"]

        if isinstance(self, ReadingNodeItem):
            if hasattr(self, 'full_title') and self.full_title != self.name:
                tooltip_parts.append(f"Title: {self.full_title}")
            if hasattr(self, 'author') and self.author:
                tooltip_parts.append(f"Author: {self.author}")

        if isinstance(self, TagNodeItem):
            tooltip_parts = [f"Tag: {self.name}"]

        tooltip_parts.append(f"Connections: {connection_count}")
        self.setToolTip("\n".join(tooltip_parts))

    def hoverEnterEvent(self, event):
        """Enlarge slightly on hover to show interactivity."""
        self.setZValue(10)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        """Reset size and z-value on hover leave."""
        self.setZValue(1)
        super().hoverLeaveEvent(event)

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
                intersect_point = QPointF()
                intersect_type = line.intersect(center_line, intersect_point)
                if intersect_type == QLineF.IntersectionType.BoundedIntersection:
                    intersect_points.append(intersect_point)
            except Exception as e:
                try:
                    intersect_type, intersect_point = center_line.intersects(line)
                    if intersect_type == QLineF.IntersectionType.BoundedIntersection:
                        intersect_points.append(intersect_point)
                except Exception as e:
                    print(f"Error calculating intersection: {e}")

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
        """Allows editing node text on double-click."""
        if isinstance(self, TagNodeItem) or isinstance(self, ReadingNodeItem):
            self.line_edit = QLineEdit()
            self.line_edit.setText(self.name.strip())
            self.line_edit.selectAll()

            self.proxy = self.scene().addWidget(self.line_edit)
            self.proxy.setParentItem(self)

            self.proxy.setPos(self.text_item.pos())
            self.proxy.resize(self.text_item.boundingRect().width(), self.text_item.boundingRect().height())

            self.text_item.hide()
            self.line_edit.setFocus()

            self.line_edit.editingFinished.connect(self._on_rename_finished)
        else:
            if event:
                super().mouseDoubleClickEvent(event)

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
            self.update_geometry()

            if isinstance(self, ReadingNodeItem):
                self.graph_view.rename_reading(self.reading_id, new_name)
            elif isinstance(self, TagNodeItem):
                self.graph_view.rename_tag(self.tag_id, new_name)

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

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(3, 3)
        self.setGraphicsEffect(shadow)

    def shape(self):
        path = QPainterPath()
        path.addRoundedRect(self.boundingRect(), 10, 10)
        return path

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = self.shape()
        brush = QBrush(QColor("#cce0f5"))
        painter.fillPath(path, brush)
        pen = QPen(QColor("#0047b2"), 1)
        painter.setPen(pen)
        painter.drawPath(path)

    def mouseDoubleClickEvent(self, event):
        print(f"Reading node '{self.name}' double-clicked")
        # --- MODIFIED: Pass event to super() ---
        super().mouseDoubleClickEvent(event)
        # --- END MODIFIED ---


class TagNodeItem(BaseGraphNode):
    """A node representing a Tag."""

    def __init__(self, tag_id, name, graph_view, parent=None):
        self.tag_id = tag_id
        super().__init__(name, graph_view, parent)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(3, 3)
        self.setGraphicsEffect(shadow)

    def shape(self):
        path = QPainterPath()
        path.addRoundedRect(self.boundingRect(), 5, 5)
        return path

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = self.shape()
        brush = QBrush(QColor("#cce8cc"))
        painter.fillPath(path, brush)
        pen = QPen(QColor("#006100"), 1)
        painter.setPen(pen)
        painter.drawPath(path)

    def mouseDoubleClickEvent(self, event):
        print(f"Tag node '{self.name}' double-clicked")
        # --- MODIFIED: Pass event to super() ---
        super().mouseDoubleClickEvent(event)
        # --- END MODIFIED ---


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

    tagsUpdated = Signal()

    def __init__(self, db_manager, project_id, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.project_id = project_id

        self.nodes = {}
        self.edges = []

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.scene = GraphViewScene(self)
        self.view = ZoomableGraphicsView(self.scene, self)
        main_layout.addWidget(self.view)

        self.view.mousePressEvent = self.view_mouse_press

        self.view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self.show_graph_context_menu)

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

        ZoomableGraphicsView.mousePressEvent(self.view, event)

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
            node_item.full_title = reading.get('title', reading['name'])
            node_item.author = reading.get('author', '')

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

        for node in self.nodes.values():
            node.update_node_scale_and_tooltip()

        if self.nodes:
            # --- MODIFIED: Center view on load ---
            bounds = self.scene.itemsBoundingRect().adjusted(-50, -50, 50, 50)
            self.view.setSceneRect(bounds)
            self.view.fitInView(bounds, Qt.AspectRatioMode.KeepAspectRatio)
            # --- END MODIFIED ---

    def update_physics(self):
        """Simple physics simulation for the graph."""
        if not self.nodes:
            return

        # --- THIS IS THE FIX for overlapping project nodes ---
        K_REPEL = 80000  # Repulsion force (was 150000, orig 50000)
        K_ATTRACT = 0.03  # Attraction force (spring) (was 0.02)
        DAMPING = 0.85  # Damping factor
        CENTER_PULL = 0.002  # Force pulling nodes to center
        MIN_DIST = 50.0  # Minimum distance
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
                attract_force = dist * K_ATTRACT

                force += (delta / dist) * attract_force

            # 3. Pull towards center
            center_delta = -node_a.pos()
            force += center_delta * CENTER_PULL

            if not hasattr(node_a, 'velocity'):
                node_a.velocity = QPointF(0, 0)

            node_a.velocity = (node_a.velocity + force) * DAMPING

            if not (node_a.isUnderMouse() and QApplication.mouseButtons() & Qt.MouseButton.LeftButton):
                node_a.setPos(node_a.pos() + node_a.velocity)

        for edge in self.edges:
            edge.update_position()

    @Slot(int, str)
    def rename_reading(self, reading_id, new_name):
        """Updates a reading's nickname in the database."""
        try:
            self.db.update_reading_nickname(reading_id, new_name)
            self.load_graph()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not rename reading: {e}")
            self.load_graph()

    @Slot(int, str)
    def rename_tag(self, tag_id, new_name):
        """Updates a tag's name in the database."""
        try:
            self.db.rename_tag(tag_id, new_name)
            self.load_graph()
            self.tagsUpdated.emit()
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "Tag Exists", f"A tag named '{new_name}' already exists.")
            self.load_graph()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not rename tag: {e}")
            self.load_graph()

    @Slot(QPoint)
    def show_graph_context_menu(self, pos):
        """Shows the right-click menu for the graph view."""
        scene_pos = self.view.mapToScene(pos)
        item = self.view.itemAt(pos)
        menu = QMenu(self)

        node = None
        if isinstance(item, BaseGraphNode):
            node = item
        elif isinstance(item, QGraphicsTextItem) and isinstance(item.parentItem(), BaseGraphNode):
            node = item.parentItem()

        if node:
            if not node.isSelected():
                self.scene.clearSelection()
                node.setSelected(True)
            # --- MODIFIED: Pass None to mouseDoubleClickEvent ---
            menu.addAction("Rename", lambda: node.mouseDoubleClickEvent(None))
            # --- END MODIFIED ---
            menu.addAction("Delete", lambda: self.delete_node(node))

        elif isinstance(item, GraphEdgeItem):
            menu.addAction("View Anchors (Tag <-> Reading)", lambda: self.view_anchors(item))

        else:
            try:
                # self (GraphViewTab) -> QStackedWidget -> QWidget -> ProjectDashboardWidget
                # --- MODIFIED: Simpler parent finding ---
                dashboard = self.parentWidget().parentWidget()
                # --- END MODIFIED ---
                if hasattr(dashboard, 'add_reading'):
                    menu.addAction("Add New Reading...", dashboard.add_reading)
                else:
                    print("Could not find add_reading method on parent.")
            except Exception as e:
                print(f"Error finding add_reading method: {e}")

            menu.addAction("Add New Tag...", self.create_new_tag_from_graph)

        menu.exec(self.view.mapToGlobal(pos))

    @Slot(BaseGraphNode)
    def delete_node(self, node):
        """Deletes the selected node from the graph and DB."""
        if isinstance(node, ReadingNodeItem):
            reply = QMessageBox.question(self, "Delete Reading",
                                         f"Are you sure you want to delete '{node.name}'?\nThis will delete the reading, its outline, and all attachments.",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                         QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    self.db.delete_reading(node.reading_id)
                    self.load_graph()
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Could not delete reading: {e}")

        elif isinstance(node, TagNodeItem):
            reply = QMessageBox.question(self, "Delete Tag",
                                         f"Are you sure you want to delete '{node.name}'?\nThis will delete the tag and all its anchors from all projects.",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                         QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    self.db.delete_tag_and_anchors(node.tag_id)
                    self.load_graph()
                    self.tagsUpdated.emit()
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Could not delete tag: {e}")

    @Slot(GraphEdgeItem)
    def view_anchors(self, edge):
        """Emits a signal to view anchors for the connected tag."""
        tag_node = None
        if isinstance(edge.from_node, TagNodeItem):
            tag_node = edge.from_node
        elif isinstance(edge.to_node, TagNodeItem):
            tag_node = edge.to_node

        if tag_node:
            self.tagDoubleClicked.emit(tag_node.tag_id)

    @Slot()
    def create_new_tag_from_graph(self):
        """Opens a dialog to create a new tag."""
        if not EditTagDialog:
            QMessageBox.critical(self, "Error", "EditTagDialog not loaded.")
            return

        dialog = EditTagDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_name = dialog.get_tag_name()
            if not new_name:
                return

            try:
                self.db.get_or_create_tag(new_name, self.project_id)
                self.load_graph()
                self.tagsUpdated.emit()
            except sqlite3.IntegrityError:
                QMessageBox.warning(self, "Tag Exists", f"A tag named '{new_name}' already exists.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not create tag: {e}")