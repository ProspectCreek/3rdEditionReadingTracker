# dialogs/global_graph_dialog.py
import sys
import math
import random
import sqlite3
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QSplitter, QGraphicsView,
    QGraphicsScene, QGraphicsItem, QLabel, QTextBrowser,
    QMessageBox, QWidget, QGraphicsDropShadowEffect, QApplication,
    QFrame, QFormLayout, QPushButton, QColorDialog, QScrollArea,
    QMenu
)
from PySide6.QtCore import Qt, QTimer, QRectF, QPointF, QLineF, Signal, Slot, QUrl
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QBrush, QPainterPath

    # ---!!--- IMPORT NEW SHARED HELPERS ---!!---

try:
    from tabs.graph_helpers import (
        ZoomableGraphicsView, GraphEdgeItem, ObsidianNodeItem, ObsidianGraphScene
    )
except ImportError:
    QMessageBox.critical(None, "Import Error", "Could not import graph components from tabs.graph_helpers.py")
    sys.exit(1)
# ---!!--- END IMPORT ---!!---

try:
    from dialogs.edit_tag_dialog import EditTagDialog
except ImportError:
    print("Error: Could not import EditTagDialog for GlobalGraphDialog")
    EditTagDialog = None

# --- NEW: Import Details Dialog ---
try:
    from dialogs.global_tag_details_dialog import GlobalTagDetailsDialog
except ImportError:
    print("Error: Could not import GlobalTagDetailsDialog")
    GlobalTagDetailsDialog = None


# --- END NEW ---


class GlobalGraphDialog(QDialog):
    """
    A dialog window that displays a force-directed graph of all
    synthesis tags across all projects, using the new Obsidian-style nodes.
    """

    jumpToAnchor = Signal(int, int, int)  # project_id, reading_id, outline_id

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.nodes = {}  # Stores node items keyed by a unique ID string
        self.edges = []
        self.color_map = {}  # Stores { 'project_colors': {id: hex}, 'tag_color': hex }
        self.color_buttons = {}  # Stores { 'p_123': button, 'tag_0': button }
        self.tag_id_name_map = {}  # Map ID to Name for lookups

        self.setWindowTitle("Global Knowledge Connections")
        self.setMinimumSize(1000, 700)
        self.setModal(False)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.CustomizeWindowHint |
            Qt.WindowType.WindowTitleHint |
            Qt.WindowType.WindowMinimizeButtonHint |
            Qt.WindowType.WindowMaximizeButtonHint |
            Qt.WindowType.WindowCloseButtonHint
        )

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(self.splitter)

        # --- Left Panel: Control Panel ---
        self.control_panel = QFrame(self)
        self.control_panel.setMinimumWidth(250)
        self.control_panel.setMaximumWidth(400)
        self.control_panel.setFrameShape(QFrame.Shape.StyledPanel)

        panel_layout = QVBoxLayout(self.control_panel)
        panel_layout.setContentsMargins(5, 5, 5, 5)

        panel_title = QLabel("Graph Settings")
        panel_title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        panel_layout.addWidget(panel_title)

        # Scroll Area for color pickers
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        self.controls_form_layout = QFormLayout(scroll_widget)
        self.controls_form_layout.setSpacing(10)
        scroll_area.setWidget(scroll_widget)

        panel_layout.addWidget(scroll_area)  # Add scroll area to panel

        # --- Center Panel: Graph ---
        graph_widget = QWidget(self)
        graph_layout = QVBoxLayout(graph_widget)
        graph_layout.setContentsMargins(0, 0, 0, 0)
        self.scene = ObsidianGraphScene(self)  # Use the shared scene class
        self.scene.setBackgroundBrush(QColor("#F8F8F8"))
        self.view = ZoomableGraphicsView(self.scene, self)  # Use shared view class
        graph_layout.addWidget(self.view)

        # --- Right Panel: Global Synthesis View ---
        synthesis_widget = QWidget(self)
        synthesis_layout = QVBoxLayout(synthesis_widget)
        synthesis_layout.setContentsMargins(4, 4, 4, 4)

        synthesis_layout.addWidget(QLabel("Global Synthesis View"))

        self.synthesis_display = QTextBrowser()
        self.synthesis_display.setOpenExternalLinks(False)  # Handle links ourselves
        self.synthesis_display.anchorClicked.connect(self.on_anchor_link_clicked)
        synthesis_layout.addWidget(self.synthesis_display)

        # Add to splitter
        self.splitter.addWidget(self.control_panel)
        self.splitter.addWidget(graph_widget)
        self.splitter.addWidget(synthesis_widget)

        # Start with synthesis view hidden, 25/75 split for controls/graph
        self.splitter.setSizes([250, 750, 0])

        # --- Physics Timer ---
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_physics)
        self._simulation_steps = 0
        self.K_REPEL = 80000
        self.K_ATTRACT = 0.03
        self.DAMPING = 0.85
        self.CENTER_PULL = 0.002
        self.MIN_DIST = 50.0

        # --- Connect View Signals ---
        self.view.mousePressEvent = self.view_mouse_press
        self.view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self.show_graph_context_menu)

        # Load the graph
        QTimer.singleShot(0, self.load_global_graph)

    # --- FIX: Allow panning by not returning early ---
    def view_mouse_press(self, event):
        """Overrides the view's mouse press event."""
        item_at_pos = self.view.itemAt(event.pos())

        if item_at_pos is None and event.button() == Qt.MouseButton.LeftButton:
            self.scene.clearSelection()
            self.scene.update_highlights()
            # Removed event.accept() and return so drag event propagates to base class

        # Pass event to base class for node selection/dragging/panning
        ZoomableGraphicsView.mousePressEvent(self.view, event)

    # --- END FIX ---

    def _build_control_panel(self, projects):
        """Creates the color-picker buttons for projects and tags."""
        # Clear old widgets
        for i in reversed(range(self.controls_form_layout.count())):
            widget = self.controls_form_layout.takeAt(i).widget()
            if widget is not None:
                widget.deleteLater()
        self.color_buttons.clear()

        # 1. Add "All Tags" color button
        tag_button = QPushButton("Change Color")
        tag_button.setToolTip("Set color for ALL tag nodes")
        tag_button.setProperty("item_type", "tag")
        tag_button.setProperty("item_id", 0)  # Special ID for "all tags"
        tag_button.clicked.connect(self.open_color_picker)

        self.controls_form_layout.addRow("All Tags:", tag_button)
        self.color_buttons["tag_0"] = tag_button

        # 2. Add separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        self.controls_form_layout.addRow(separator)

        # 3. Add buttons for each project
        for project in projects:
            project_id = project['id']
            project_name = project['name']

            button = QPushButton("Change Color")
            button.setToolTip(f"Set color for '{project_name}' nodes")
            button.setProperty("item_type", "project")
            button.setProperty("item_id", project_id)
            button.clicked.connect(self.open_color_picker)

            self.controls_form_layout.addRow(f"{project_name}:", button)
            self.color_buttons[f"p_{project_id}"] = button

    def _update_color_buttons(self):
        """Updates button colors from the color map."""

        # Update "All Tags" button
        tag_color_hex = self.color_map.get('tag_color', '#cce8cc')
        if "tag_0" in self.color_buttons:
            self.color_buttons["tag_0"].setStyleSheet(f"""
                QPushButton {{ background-color: {tag_color_hex}; 
                              color: {'#000' if QColor(tag_color_hex).lightness() > 128 else '#FFF'}; 
                              border: 1px solid #555; padding: 4px; }}
                QPushButton:hover {{ border: 1px solid #00AEEB; }}
            """)

        # Update project buttons
        project_colors = self.color_map.get('project_colors', {})
        default_project_color = self.db.DEFAULT_GLOBAL_COLORS['project']

        for key, button in self.color_buttons.items():
            if key.startswith("p_"):
                project_id = int(key.split("_")[1])
                color_hex = project_colors.get(project_id, default_project_color)
                button.setStyleSheet(f"""
                    QPushButton {{ background-color: {color_hex}; 
                                  color: {'#000' if QColor(color_hex).lightness() > 128 else '#FFF'}; 
                                  border: 1px solid #555; padding: 4px; }}
                    QPushButton:hover {{ border: 1px solid #00AEEB; }}
                """)

    @Slot()
    def open_color_picker(self):
        """Opens the color dialog for the button that was clicked."""
        sender_button = self.sender()
        if not sender_button:
            return

        item_type = sender_button.property("item_type")
        item_id = sender_button.property("item_id")
        if not item_type:
            return

        if item_type == 'tag':
            current_color_hex = self.color_map.get('tag_color', '#cce8cc')
        else:  # project
            current_color_hex = self.color_map.get('project_colors', {}).get(item_id,
                                                                             self.db.DEFAULT_GLOBAL_COLORS['project'])

        color = QColorDialog.getColor(QColor(current_color_hex), self, f"Select Color for {item_type}")

        if color.isValid():
            new_color_hex = color.name()
            self.db.save_global_graph_setting(item_type, item_id, new_color_hex)
            self.load_global_graph()  # Reload graph to apply new colors

    def load_global_graph(self):
        self.timer.stop()
        self.scene.clear_graph()
        self.nodes.clear()
        self.edges.clear()
        self.tag_id_name_map.clear()  # Clear map

        try:
            data = self.db.get_global_graph_data()
            self.color_map = self.db.get_global_graph_settings()

            # Build control panel with project list
            self._build_control_panel(data['projects'])
            self._update_color_buttons()

            # Populate tag map for double-click lookups
            self.tag_id_name_map = {t['id']: t['name'] for t in data['tags']}

        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Could not load global tags: {e}")
            return

        if not data['tags'] and not data['projects']:
            label = self.scene.addSimpleText("No projects or tags found.")
            label.setPos(0, 0)
            return

        scene_size = 300 * math.sqrt(len(data['tags']) + len(data['projects']))
        tag_color_hex = self.color_map.get('tag_color', self.db.DEFAULT_GLOBAL_COLORS['tag'])
        tag_border_hex = QColor(tag_color_hex).darker(120).name()
        project_colors = self.color_map.get('project_colors', {})
        default_project_color = self.db.DEFAULT_GLOBAL_COLORS['project']

        # Create Tag Nodes
        for tag in data['tags']:
            node_id = f"t_{tag['id']}"
            node_data = {'tag_id': tag['id'], 'project_count': tag['project_count']}
            node_item = ObsidianNodeItem(node_id, tag['name'], 'tag', node_data,
                                         QColor(tag_color_hex), QColor(tag_border_hex), self)
            node_item.setPos(random.uniform(-scene_size, scene_size),
                             random.uniform(-scene_size, scene_size))
            self.scene.add_node(node_item)
            self.nodes[node_id] = node_item

        # Create Project Nodes
        for project in data['projects']:
            node_id = f"p_{project['id']}"
            node_data = {'project_id': project['id']}

            color_hex = project_colors.get(project['id'], default_project_color)
            border_hex = QColor(color_hex).darker(120).name()

            node_item = ObsidianNodeItem(node_id, project['name'], 'project', node_data,
                                         QColor(color_hex), QColor(border_hex), self)
            node_item.setPos(random.uniform(-scene_size, scene_size),
                             random.uniform(-scene_size, scene_size))
            self.scene.add_node(node_item)
            self.nodes[node_id] = node_item

        # Create Edges
        for edge in data['edges']:
            from_id = f"p_{edge['project_id']}"
            to_id = f"t_{edge['tag_id']}"

            if from_id in self.nodes and to_id in self.nodes:
                from_node = self.nodes[from_id]
                to_node = self.nodes[to_id]

                edge_item = GraphEdgeItem(from_node, to_node)
                self.scene.add_edge(edge_item)
                self.edges.append(edge_item)
                from_node.add_edge(edge_item)
                to_node.add_edge(edge_item)
                edge_item.update_position()

        for node in self.nodes.values():
            node.update_node_scale_and_tooltip()

        self.timer.start(16)
        QTimer.singleShot(0, self._center_graph)

    def update_physics(self):
        """Simple physics simulation for the graph."""
        if not self.nodes:
            return

        node_list = list(self.nodes.values())

        for i, node_a in enumerate(node_list):
            if node_a.isSelected() and self.view.underMouse():
                if hasattr(node_a, 'velocity'):
                    node_a.velocity = QPointF(0, 0)
                continue

            force = QPointF(0, 0)

            # 1. Repulsion from all other nodes
            for j, node_b in enumerate(node_list):
                if i == j:
                    continue
                delta = node_a.pos() - node_b.pos()
                dist_sq = max(self.MIN_DIST, QPointF.dotProduct(delta, delta))
                repel_force = self.K_REPEL / dist_sq
                dist = math.sqrt(dist_sq)
                force += (delta / dist) * repel_force

            # 2. Attraction from connected nodes (edges)
            for edge in node_a.edges:
                other_node = edge.from_node if edge.to_node == node_a else edge.to_node
                if other_node.isSelected():
                    continue
                delta = other_node.pos() - node_a.pos()
                dist_sq = max(self.MIN_DIST, QPointF.dotProduct(delta, delta))
                dist = math.sqrt(dist_sq)
                attract_force = dist * self.K_ATTRACT
                force += (delta / dist) * attract_force

            # 3. Pull towards center
            center_delta = -node_a.pos()
            force += center_delta * self.CENTER_PULL

            if not hasattr(node_a, 'velocity'):
                node_a.velocity = QPointF(0, 0)

            node_a.velocity = (node_a.velocity + force) * self.DAMPING

            if not (node_a.isUnderMouse() and QApplication.mouseButtons() & Qt.MouseButton.LeftButton):
                node_a.setPos(node_a.pos() + node_a.velocity)

        for edge in self.edges:
            edge.update_position()

    def _center_graph(self):
        try:
            bounds = self.scene.itemsBoundingRect().adjusted(-100, -100, 100, 100)
            if bounds.isValid():
                self.view.fitInView(bounds, Qt.AspectRatioMode.KeepAspectRatio)
        except Exception as e:
            print(f"Error centering global graph: {e}")

    # --- NEW: Double Click Handlers ---
    @Slot(int)
    def emit_tag_double_clicked(self, tag_id):
        """Handle double click on a tag node."""
        tag_name = self.tag_id_name_map.get(tag_id)
        if tag_name:
            self._open_tag_details(tag_name)

    # --- NEW: Handle Project Double Click ---
    @Slot(int)
    def emit_project_double_clicked(self, project_id):
        """Handle double click on a project node."""
        # Jump to project root (reading_id=0, outline_id=0)
        self.jumpToAnchor.emit(project_id, 0, 0)
        self.accept()  # Close global graph

    # --- END NEW ---

    def _open_tag_details(self, tag_name):
        """Opens the GlobalTagDetailsDialog."""
        if not GlobalTagDetailsDialog:
            QMessageBox.warning(self, "Error", "GlobalTagDetailsDialog not available.")
            return

        dialog = GlobalTagDetailsDialog(self.db, tag_name, self)
        dialog.jumpToAnchor.connect(self._handle_jump_from_details)
        dialog.exec()

    def _handle_jump_from_details(self, p_id, r_id, o_id):
        """Forwards the jump signal and closes the graph window."""
        self.jumpToAnchor.emit(p_id, r_id, o_id)
        self.accept()

    # Stub handlers for other types
    @Slot(int)
    def emit_reading_double_clicked(self, reading_id):
        pass

    @Slot(int)
    def emit_anchor_double_clicked(self, anchor_id):
        pass

    @Slot(str)
    def load_anchors_for_tag(self, tag_name):
        self._open_tag_details(tag_name)

    @Slot(QUrl)
    def on_anchor_link_clicked(self, url):
        """Handles clicks on 'jumpto' links in the old side panel."""
        url_str = url.toString()
        if url_str.startswith("jumpto:"):
            try:
                parts = url_str.split(":")
                project_id = int(parts[1])
                reading_id = int(parts[2])
                outline_id = int(parts[3])

                self.jumpToAnchor.emit(project_id, reading_id, outline_id)
                self.accept()  # Close the global graph dialog
            except Exception as e:
                print(f"Error handling jumpto link: {e}")

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
            menu.addAction("View Info (Tooltip)", lambda: None).setEnabled(False)

        else:  # Clicked on empty space
            menu.addAction("Add New Tag...", self.create_new_tag_from_graph)

        menu.exec(self.view.mapToGlobal(pos))

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
                # In global graph, we don't link to a project automatically
                self.db.add_tag(new_name)
                self.load_global_graph()
            except sqlite3.IntegrityError:
                QMessageBox.warning(self, "Tag Exists", f"A tag named '{new_name}' already exists.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not create tag: {e}")
