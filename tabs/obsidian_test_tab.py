# prospectcreek/3rdeditionreadingtracker/tabs/obsidian_test_tab.py
import sys
import math
import sqlite3
import random
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QGraphicsView, QGraphicsScene,
    QGraphicsItem, QGraphicsLineItem, QGraphicsTextItem,
    QGraphicsEllipseItem, QMenu, QGraphicsSceneMouseEvent,
    QMessageBox, QApplication, QGraphicsDropShadowEffect, QLineEdit,
    QGraphicsProxyWidget, QDialog, QFrame, QLabel, QPushButton,
    QFormLayout, QColorDialog
)
from PySide6.QtCore import (
    Qt, QPointF, QRectF, QTimer, Signal, Slot, QLineF,
    QPoint
)
from PySide6.QtGui import QPainter, QBrush, QColor, QPen, QFont, QPainterPath, QFontMetrics

# Import supporting classes from the existing graph_view_tab
try:
    from tabs.graph_view_tab import ZoomableGraphicsView, GraphEdgeItem
except ImportError:
    QMessageBox.critical(None, "Import Error", "Could not import graph components from tabs.graph_view_tab.py")
    sys.exit(1)

try:
    from dialogs.edit_tag_dialog import EditTagDialog
except ImportError:
    print("Error: Could not import EditTagDialog for ObsidianTestTab")
    EditTagDialog = None


# --- NEW OBSIDIAN-STYLE NODE ---
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


# --- END NEW NODE ---


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


class ObsidianTestTab(QWidget):
    """
    Test widget for the "Obsidian" style graph.
    Includes a collapsible control panel.
    """
    readingDoubleClicked = Signal(int, int, int, int,
                                  str)  # (anchor_id, reading_id, outline_id, item_link_id, item_type)
    tagDoubleClicked = Signal(int)
    tagsUpdated = Signal()  # For tag renaming/deleting

    def __init__(self, db_manager, project_id, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.project_id = project_id

        self.nodes = {}  # Stores {node_id_str: ObsidianNodeItem}
        self.edges = []
        self.color_map = {}
        self.color_buttons = {}

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.splitter = QSplitter(Qt.Orientation.Horizontal, self)
        main_layout.addWidget(self.splitter)

        # --- Left Panel: Control Panel ---
        self.control_panel = QFrame(self)
        self.control_panel.setMinimumWidth(200)
        self.control_panel.setMaximumWidth(350)
        self.control_panel.setFrameShape(QFrame.Shape.StyledPanel)

        panel_layout = QVBoxLayout(self.control_panel)
        panel_layout.setContentsMargins(5, 5, 5, 5)

        panel_title = QLabel("Graph Settings")
        panel_title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        panel_layout.addWidget(panel_title)

        self.controls_form_layout = QFormLayout()
        self.controls_form_layout.setSpacing(10)
        panel_layout.addLayout(self.controls_form_layout)

        self._build_control_panel()

        panel_layout.addStretch()

        # --- Right Panel: Graph ---
        graph_widget = QWidget(self)
        graph_layout = QVBoxLayout(graph_widget)
        graph_layout.setContentsMargins(0, 0, 0, 0)
        self.scene = ObsidianGraphScene(self)
        self.view = ZoomableGraphicsView(self.scene, self)
        graph_layout.addWidget(self.view)

        # Add to splitter
        self.splitter.addWidget(self.control_panel)
        self.splitter.addWidget(graph_widget)
        self.splitter.setSizes([250, 750])  # Initial size

        self.view.mousePressEvent = self.view_mouse_press
        self.view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self.show_graph_context_menu)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_physics)
        self.timer.start(16)

    def _build_control_panel(self):
        """Creates the color-picker buttons."""
        self.color_buttons = {}

        node_types = [
            'reading', 'tag', 'dq', 'term',
            'proposition', 'argument', 'theory', 'default'
        ]

        for node_type in node_types:
            button = QPushButton("Change Color")
            button.setToolTip(f"Set color for {node_type} nodes")
            # Store node_type in the button using a dynamic property
            button.setProperty("node_type", node_type)
            button.clicked.connect(self.open_color_picker)

            self.controls_form_layout.addRow(f"{node_type.capitalize()}:", button)
            self.color_buttons[node_type] = button

    def _update_color_buttons(self):
        """Updates the background color of the buttons to match the current color map."""
        for node_type, button in self.color_buttons.items():
            color_hex = self.color_map.get(node_type, '#888888')
            button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color_hex};
                    color: {'#000' if QColor(color_hex).lightness() > 128 else '#FFF'};
                    border: 1px solid #555;
                    padding: 4px;
                }}
                QPushButton:hover {{
                    border: 1px solid #00AEEB;
                }}
            """)

    @Slot()
    def open_color_picker(self):
        """Opens the color dialog for the button that was clicked."""
        sender_button = self.sender()
        if not sender_button:
            return

        node_type = sender_button.property("node_type")
        if not node_type:
            return

        current_color_hex = self.color_map.get(node_type, '#FFFFFF')
        color = QColorDialog.getColor(QColor(current_color_hex), self, f"Select Color for {node_type}")

        if color.isValid():
            new_color_hex = color.name()
            # Save to DB
            self.db.save_graph_setting(self.project_id, node_type, new_color_hex)
            # Reload graph to apply new colors
            self.load_graph()

    def view_mouse_press(self, event):
        """Overrides the view's mouse press event."""
        item_at_pos = self.view.itemAt(event.pos())

        if item_at_pos is None and event.button() == Qt.MouseButton.LeftButton:
            self.scene.clearSelection()
            self.scene.update_highlights()
            event.accept()
            return

        ZoomableGraphicsView.mousePressEvent(self.view, event)

    @Slot(int)
    def emit_reading_double_clicked(self, reading_id):
        self.readingDoubleClicked.emit(0, reading_id, 0, 0, '')

    @Slot(int)
    def emit_anchor_double_clicked(self, anchor_id):
        """Finds the reading/outline info and emits the full signal."""
        try:
            anchor = self.db.get_anchor_navigation_details(anchor_id)
            if anchor:
                self.readingDoubleClicked.emit(
                    anchor_id,
                    anchor['reading_id'],
                    anchor.get('outline_id', 0),
                    anchor.get('item_link_id', 0),
                    anchor.get('item_type', '')
                )
        except Exception as e:
            print(f"ObsidianTestTab: Error emitting anchor click: {e}")

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
            # 1. Get graph data
            data = self.db.get_graph_data_full(self.project_id)
            # 2. Get color settings
            self.color_map = self.db.get_graph_settings(self.project_id)
            # 3. Update buttons in control panel
            self._update_color_buttons()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load graph data: {e}")
            return

        scene_size = 300 * math.sqrt(len(data['readings']) + len(data['tags']) + len(data['virtual_anchors']))

        # 1. Create Reading Nodes
        for reading in data['readings']:
            node_id = f"r_{reading['id']}"
            node_name = reading['name'] or 'Untitled Reading'
            node_data = {
                'reading_id': reading['id'],
                'full_title': reading.get('title', node_name),
                'author': reading.get('author', '')
            }
            color_hex = self.color_map.get('reading', '#cce0f5')
            border_hex = QColor(color_hex).darker(120).name()

            node_item = ObsidianNodeItem(node_id, node_name, 'reading', node_data, QColor(color_hex),
                                         QColor(border_hex), self)
            node_item.setPos(random.uniform(-scene_size, scene_size), random.uniform(-scene_size, scene_size))
            self.scene.add_node(node_item)
            self.nodes[node_id] = node_item

        # 2. Create Tag Nodes
        for tag in data['tags']:
            node_id = f"t_{tag['id']}"
            node_data = {'tag_id': tag['id']}
            color_hex = self.color_map.get('tag', '#cce8cc')
            border_hex = QColor(color_hex).darker(120).name()

            node_item = ObsidianNodeItem(node_id, tag['name'], 'tag', node_data, QColor(color_hex), QColor(border_hex),
                                         self)
            node_item.setPos(random.uniform(-scene_size, scene_size), random.uniform(-scene_size, scene_size))
            self.scene.add_node(node_item)
            self.nodes[node_id] = node_item

        # 3. Create Virtual Anchor Nodes (as dots)
        virtual_anchor_nodes = {}  # Map item_link_id to node_item
        for anchor_link in data.get('virtual_anchors', []):
            item_link_id = anchor_link['item_link_id']
            item_type = anchor_link.get('item_type', 'item')
            node_id = f"item_{item_link_id}"  # Group by item

            if node_id not in self.nodes:
                node_data = {
                    'anchor_id': anchor_link['id'],  # Store one anchor ID for jumping
                    'item_link_id': item_link_id,
                    'item_type': item_type,
                    'summary_text': anchor_link['selected_text']
                }

                color_hex = self.color_map.get(item_type, self.color_map['default'])
                border_hex = QColor(color_hex).darker(120).name()

                # Use item_type as the visible name
                item_node = ObsidianNodeItem(node_id, item_type, item_type, node_data, QColor(color_hex),
                                             QColor(border_hex), self)
                item_node.setPos(random.uniform(-scene_size, scene_size), random.uniform(-scene_size, scene_size))
                self.scene.add_node(item_node)
                self.nodes[node_id] = item_node
                virtual_anchor_nodes[item_link_id] = item_node

            item_node = virtual_anchor_nodes[item_link_id]

            # Link Anchor Node to Tag Node
            if anchor_link['tag_id']:
                to_id = f"t_{anchor_link['tag_id']}"
                to_node = self.nodes.get(to_id)
                if to_node:
                    edge_item = GraphEdgeItem(item_node, to_node)
                    self.scene.add_edge(edge_item)
                    self.edges.append(edge_item)
                    item_node.add_edge(edge_item)
                    to_node.add_edge(edge_item)

            # Link Anchor Node to Reading Node
            reading_id_key = f"r_{anchor_link['reading_id']}"
            reading_node = self.nodes.get(reading_id_key)
            if reading_node:
                exists = any(
                    (edge.from_node == item_node and edge.to_node == reading_node) or \
                    (edge.from_node == reading_node and edge.to_node == item_node)
                    for edge in item_node.edges
                )
                if not exists:
                    edge_item = GraphEdgeItem(item_node, reading_node)
                    pen = QPen(QColor("#FFB0B0"), 1.5, Qt.PenStyle.DotLine)  # Keep this dotted
                    edge_item.setPen(pen)
                    self.scene.add_edge(edge_item)
                    self.edges.append(edge_item)
                    item_node.add_edge(edge_item)
                    reading_node.add_edge(edge_item)

        # 4. Create Text Anchor Edges (Reading <-> Tag)
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

        # 5. Finalize setup
        for node in self.nodes.values():
            if hasattr(node, 'update_node_scale_and_tooltip'):
                node.update_node_scale_and_tooltip()

        if self.nodes:
            bounds = self.scene.itemsBoundingRect().adjusted(-200, -200, 200, 200)
            self.view.setSceneRect(bounds)
            self.view.fitInView(bounds, Qt.AspectRatioMode.KeepAspectRatio)

    def update_physics(self):
        """Simple physics simulation for the graph."""
        if not self.nodes:
            return

        K_REPEL = 80000
        K_ATTRACT = 0.03
        DAMPING = 0.85
        CENTER_PULL = 0.002
        MIN_DIST = 50.0

        node_list = list(self.nodes.values())

        for i, node_a in enumerate(node_list):
            if node_a.isSelected():
                if hasattr(node_a, 'velocity'):
                    node_a.velocity = QPointF(0, 0)
                continue

            force = QPointF(0, 0)

            for j, node_b in enumerate(node_list):
                if i == j:
                    continue
                delta = node_a.pos() - node_b.pos()
                dist_sq = max(MIN_DIST, QPointF.dotProduct(delta, delta))

                repel_force = K_REPEL / dist_sq
                # Reduce repulsion for dot-like nodes
                if node_a.node_type not in ['reading', 'tag']:
                    repel_force *= 0.25
                if node_b.node_type not in ['reading', 'tag']:
                    repel_force *= 0.25

                dist = math.sqrt(dist_sq)
                force += (delta / dist) * repel_force

            for edge in node_a.edges:
                other_node = edge.from_node if edge.to_node == node_a else edge.to_node
                if other_node.isSelected():
                    continue
                delta = other_node.pos() - node_a.pos()
                dist_sq = max(MIN_DIST, QPointF.dotProduct(delta, delta))
                dist = math.sqrt(dist_sq)
                attract_force = dist * K_ATTRACT
                force += (delta / dist) * attract_force

            center_delta = -node_a.pos()
            force += center_delta * CENTER_PULL

            if not hasattr(node_a, 'velocity'):
                node_a.velocity = QPointF(0, 0)

            node_a.velocity = (node_a.velocity + force) * DAMPING

            if not (node_a.isUnderMouse() and QApplication.mouseButtons() & Qt.MouseButton.LeftButton):
                node_a.setPos(node_a.pos() + node_a.velocity)

        for edge in self.edges:
            edge.update_position()

    @Slot(QPoint)
    def show_graph_context_menu(self, pos):
        """Shows the right-click menu for the graph view."""
        scene_pos = self.view.mapToScene(pos)
        item = self.view.itemAt(pos)
        menu = QMenu(self)

        node = None
        if isinstance(item, ObsidianNodeItem):
            node = item
        elif isinstance(item, QGraphicsTextItem) and isinstance(item.parentItem(), ObsidianNodeItem):
            node = item.parentItem()

        if node:
            if not node.isSelected():
                self.scene.clearSelection()
                node.setSelected(True)
            # For now, no rename/delete in test tab
            menu.addAction("View Info (Tooltip)", lambda: None).setEnabled(False)

        elif isinstance(item, GraphEdgeItem):
            menu.addAction("View Anchors (Tag <-> Reading)", lambda: self.view_anchors(item))

        else:
            menu.addAction("Add New Tag...", self.create_new_tag_from_graph)

        menu.exec(self.view.mapToGlobal(pos))

    @Slot(GraphEdgeItem)
    def view_anchors(self, edge):
        """Emits a signal to view anchors for the connected tag."""
        tag_node = None
        if isinstance(edge.from_node, ObsidianNodeItem) and edge.from_node.node_type == 'tag':
            tag_node = edge.from_node
        elif isinstance(edge.to_node, ObsidianNodeItem) and edge.to_node.node_type == 'tag':
            tag_node = edge.to_node

        if tag_node:
            self.tagDoubleClicked.emit(tag_node.data.get('tag_id', 0))

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