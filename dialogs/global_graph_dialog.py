# dialogs/global_graph_dialog.py
import sys
import math
import random
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QSplitter, QGraphicsView,
    QGraphicsScene, QGraphicsItem, QLabel, QTextBrowser,
    QMessageBox, QWidget, QGraphicsDropShadowEffect, QApplication
)
from PySide6.QtCore import Qt, QTimer, QRectF, QPointF, QLineF, Signal, Slot, QUrl
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QBrush, QPainterPath, QFontMetrics  # <-- Import QFontMetrics

# Reuse the node and edge items from the project graph for consistency
try:
    # --- MODIFIED: Import new ZoomableGraphicsView ---
    from tabs.graph_view_tab import BaseGraphNode, GraphEdgeItem, ZoomableGraphicsView
except ImportError:
    QMessageBox.critical(None, "Import Error", "Could not import graph components from tabs.graph_view_tab.py")
    sys.exit(1)


# --- END MODIFIED ---


class GlobalTagNodeItem(BaseGraphNode):
    """
    A specific TagNodeItem for the global graph.
    We're scaling it based on project count.
    """

    def __init__(self, tag_id, name, project_count, graph_view, parent=None):
        self.tag_id = tag_id
        self.project_count = project_count
        super().__init__(name, graph_view, parent)

        # --- NEW: Add shadow ---
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(3, 3)
        self.setGraphicsEffect(shadow)
        # --- END NEW ---

    # --- NEW: More informative tooltip ---
    def update_node_scale_and_tooltip(self):
        """Sets the node's scale and tooltip based on its connection count."""
        connection_count = len(self.edges)

        # --- MODIFIED: More aggressive scaling ---
        # Scale based on *both* project count and direct connections
        total_weight = self.project_count + connection_count
        scale_factor = 1.0 + (math.sqrt(total_weight) / 2.5)  # Was / 4.0
        self.setScale(scale_factor)
        # --- END MODIFIED ---

        self.setToolTip(f"Tag: {self.name}\nProjects: {self.project_count}\nConnections: {connection_count}")

    # --- END NEW ---

    def shape(self):
        """Override shape to be a rounded rect."""
        path = QPainterPath()
        path.addRoundedRect(self.boundingRect(), 5, 5)
        return path

    def paint(self, painter, option, widget):
        """Override paint to draw a tag node."""
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = self.shape()

        brush = QBrush(QColor("#cce8cc"))  # Light green
        painter.fillPath(path, brush)

        pen = QPen(QColor("#006100"), 1)  # Thinner green border
        painter.setPen(pen)
        painter.drawPath(path)

    def mouseDoubleClickEvent(self, event):
        """Override to pass the tag *name* instead of ID."""
        print(f"Global Graph: Node clicked, calling parent tab for tag '{self.name}'")
        # In the global graph, we emit the NAME
        self.graph_view.node_double_clicked(self.name, 'tag')
        event.accept()


# --- NEW (Step 3.2): Project Node for Global Graph ---
class GlobalProjectNodeItem(BaseGraphNode):
    """A node representing a Project in the global graph."""

    def __init__(self, project_id, name, graph_view, parent=None):
        self.project_id = project_id
        super().__init__(name, graph_view, parent)

        # Add shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(3, 3)
        self.setGraphicsEffect(shadow)

    # --- NEW: More informative tooltip ---
    def update_node_scale_and_tooltip(self):
        """Sets the node's scale and tooltip based on its connection count."""
        connection_count = len(self.edges)

        # --- MODIFIED: More aggressive scaling ---
        scale_factor = 1.0 + (math.sqrt(connection_count) / 2.5)  # Was / 4.0
        self.setScale(scale_factor)
        # --- END MODIFIED ---

        self.setToolTip(f"Project: {self.name}\nTag Connections: {connection_count}")

    # --- END NEW ---

    def shape(self):
        """Override shape to be a rounded rect."""
        path = QPainterPath()
        path.addRoundedRect(self.boundingRect(), 10, 10)  # More rounded
        return path

    def paint(self, painter, option, widget):
        """Override paint to draw a project node."""
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = self.shape()

        brush = QBrush(QColor("#cce0f5"))  # Light blue
        painter.fillPath(path, brush)

        pen = QPen(QColor("#0047b2"), 1)  # Thinner blue border
        painter.setPen(pen)
        painter.drawPath(path)

    def mouseDoubleClickEvent(self, event):
        """Double-clicking a project in the global graph does nothing for now."""
        print(f"Project node '{self.name}' double-clicked (no action)")
        # --- MODIFIED: Do not call base class implementation ---
        # super().mouseDoubleClickEvent(event) # Do not call edit
        event.accept()
        # --- END MODIFIED ---


# --- END NEW ---


class GlobalGraphDialog(QDialog):
    """
    A dialog window that displays a force-directed graph of all
    synthesis tags across all projects.
    """

    # This signal is internal to this dialog, for the node to talk to the dialog
    _tagDoubleClicked = Signal(str)

    # --- NEW (Step 3.3): Signal to jump to an anchor ---
    jumpToAnchor = Signal(int, int, int)  # project_id, reading_id, outline_id

    # --- END NEW ---

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.nodes = {}  # Stores node items keyed by tag_name
        self.edges = []  # --- NEW (Step 3.2) ---

        # --- RENAMED ---
        self.setWindowTitle("Global Knowledge Connections")
        self.setMinimumSize(1000, 700)
        # --- MODIFIED: Change window behavior ---
        self.setModal(False)  # No longer modal
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.CustomizeWindowHint |
            Qt.WindowType.WindowTitleHint |
            Qt.WindowType.WindowMinimizeButtonHint |
            Qt.WindowType.WindowMaximizeButtonHint |
            Qt.WindowType.WindowCloseButtonHint
        )
        # --- END MODIFIED ---

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(self.splitter)

        # --- Left Panel: Graph ---
        graph_widget = QWidget()
        graph_layout = QVBoxLayout(graph_widget)
        graph_layout.setContentsMargins(4, 4, 4, 4)

        self.scene = QGraphicsScene(self)
        self.scene.setBackgroundBrush(QColor("#F8F8F8"))

        # --- MODIFIED: Use new ZoomableGraphicsView ---
        self.view = ZoomableGraphicsView(self.scene, self)
        # --- END MODIFIED ---
        graph_layout.addWidget(self.view)

        # --- Right Panel: Global Synthesis View ---
        synthesis_widget = QWidget()
        synthesis_layout = QVBoxLayout(synthesis_widget)
        synthesis_layout.setContentsMargins(4, 4, 4, 4)

        synthesis_layout.addWidget(QLabel("Global Synthesis View"))

        self.synthesis_display = QTextBrowser()
        self.synthesis_display.setOpenExternalLinks(False)  # Handle links ourselves
        self.synthesis_display.anchorClicked.connect(self.on_anchor_link_clicked)
        synthesis_layout.addWidget(self.synthesis_display)

        # Add to splitter
        self.splitter.addWidget(graph_widget)
        self.splitter.addWidget(synthesis_widget)

        # Start with synthesis view hidden
        self.splitter.setSizes([self.width(), 0])

        # --- Physics Timer ---
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_forces)  # <-- RENAMED
        self._simulation_steps = 0
        # --- MODIFIED: Use constants from the working graph tab ---
        self.K_REPEL = 80000
        self.K_ATTRACT = 0.03
        self.DAMPING = 0.85
        self.CENTER_PULL = 0.002
        self.MIN_DIST = 50.0
        # --- END MODIFIED ---

        # --- Connect Internal Signal ---
        self._tagDoubleClicked.connect(self.load_anchors_for_tag)

        # Load the graph
        QTimer.singleShot(0, self.load_global_graph)

    def load_global_graph(self):
        self.timer.stop()
        self.scene.clear()
        self.nodes.clear()
        self.edges.clear()  # --- NEW (Step 3.2) ---

        try:
            # --- MODIFIED (Step 3.2): Call new DB method ---
            data = self.db.get_global_graph_data()
            # --- END MODIFIED ---
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Could not load global tags: {e}")
            return

        if not data['tags'] and not data['projects']:
            label = self.scene.addSimpleText("No projects or tags found.")
            label.setPos(0, 0)
            return

        # --- MODIFIED (Step 3.2): Create all nodes (Projects and Tags) ---
        scene_size = 300 * math.sqrt(len(data['tags']) + len(data['projects']))

        # Create Tag Nodes
        for tag in data['tags']:
            node_id = f"t_{tag['id']}"
            node_item = GlobalTagNodeItem(
                tag_id=tag['id'],
                name=tag['name'],
                project_count=tag['project_count'],
                graph_view=self,
                parent=None
            )
            node_item.setPos(random.uniform(-scene_size, scene_size),
                             random.uniform(-scene_size, scene_size))
            self.scene.addItem(node_item)
            self.nodes[node_id] = node_item

        # Create Project Nodes
        for project in data['projects']:
            node_id = f"p_{project['id']}"
            node_item = GlobalProjectNodeItem(
                project_id=project['id'],
                name=project['name'],
                graph_view=self,
                parent=None
            )
            node_item.setPos(random.uniform(-scene_size, scene_size),
                             random.uniform(-scene_size, scene_size))
            self.scene.addItem(node_item)
            self.nodes[node_id] = node_item

        # Create Edges
        for edge in data['edges']:
            from_id = f"p_{edge['project_id']}"
            to_id = f"t_{edge['tag_id']}"

            if from_id in self.nodes and to_id in self.nodes:
                from_node = self.nodes[from_id]
                to_node = self.nodes[to_id]

                edge_item = GraphEdgeItem(from_node, to_node)
                self.scene.addItem(edge_item)
                self.edges.append(edge_item)  # Add to list

                from_node.add_edge(edge_item)
                to_node.add_edge(edge_item)

                # --- THIS IS THE FIX ---
                # Call update_position() immediately to draw the initial line.
                # The physics timer will update it from here.
                edge_item.update_position()
                # --- END FIX ---
        # --- END MODIFIED ---

        # --- NEW: Update scaling *after* edges are added ---
        for node in self.nodes.values():
            node.update_node_scale_and_tooltip()
        # --- END NEW ---

        # Start simulation
        self._simulation_steps = 0
        self.timer.start(16)

    @Slot()
    def _update_forces(self):
        """
        One tick of the physics simulation.
        This logic is copied from the working graph_view_tab.py.
        """
        if not self.nodes:
            self.timer.stop()
            return

        node_list = list(self.nodes.values())

        for i, node_a in enumerate(node_list):
            # Don't apply physics to a node being dragged
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

            # Apply force and damping
            node_a.velocity = (node_a.velocity + force) * self.DAMPING

            # Apply velocity
            if not (node_a.isUnderMouse() and QApplication.mouseButtons() & Qt.MouseButton.LeftButton):
                node_a.setPos(node_a.pos() + node_a.velocity)

        # Update all edge positions after nodes have moved
        for edge in self.edges:
            edge.update_position()

        # --- REMOVED STOP CONDITION ---
        # The timer now runs continuously, just like the project graph.
        # self._simulation_steps += 1
        # if not has_moved or self._simulation_steps > 200:
        #     self.timer.stop()
        #     self._center_graph()
        #     print("Global connections simulation complete.")

    def _center_graph(self):
        try:
            bounds = self.scene.itemsBoundingRect().adjusted(-100, -100, 100, 100)
            if bounds.isValid():
                self.view.fitInView(bounds, Qt.AspectRatioMode.KeepAspectRatio)
        except Exception as e:
            print(f"Error centering global connections: {e}")  # <-- RENAMED

    @Slot(str, str)
    def node_double_clicked(self, data_id_or_name, data_type):
        """Called by a node item on double-click."""
        if data_type == 'tag':
            self._tagDoubleClicked.emit(data_id_or_name)  # Emits the tag NAME

    @Slot(str)
    def load_anchors_for_tag(self, tag_name):
        """Fetches and displays all anchors for a given tag name."""
        try:
            anchors = self.db.get_global_anchors_for_tag_name(tag_name)

            html = f"<h2>Global Synthesis for: {tag_name}</h2>"

            current_project = None
            current_reading = None

            for anchor in anchors:
                # Group by Project
                project_name = anchor['project_name']
                if project_name != current_project:
                    current_project = project_name
                    html += f"<hr><h3>Project: {current_project}</h3>"
                    current_reading = None  # Reset reading for new project

                # Group by Reading
                reading_name = anchor['reading_nickname'] or anchor['reading_title']
                if reading_name != current_reading:
                    current_reading = reading_name
                    html += f"<h4>{current_reading}</h4>"

                # Build Context
                context_parts = []
                if anchor['outline_title']:
                    context_parts.append(f"Section: {anchor['outline_title']}")

                # --- FIX: Link format for global graph (needs project_id) ---
                # Format: jumpto:project_id:reading_id:outline_id
                jumpto_link = f"jumpto:{anchor['project_id']}:{anchor['reading_id']}:{anchor['outline_id'] or 0}"

                if context_parts:
                    html += f"<p><i><a href='{jumpto_link}'>({', '.join(context_parts)})</a></i></p>"
                else:
                    html += f"<p><i><a href='{jumpto_link}'>(Reading-Level Note)</a></i></p>"
                # --- END FIX ---

                # Build Anchor Body
                html += "<blockquote>"
                html += f"<p>{anchor['selected_text']}</p>"
                if anchor['comment']:
                    comment_html = anchor['comment'].replace("\n", "<br>")
                    html += f"<p><i>— {comment_html}</i></p>"
                html += "</blockquote>"

            if not anchors:
                html += "<i>No anchors found for this tag.</i>"

            self.synthesis_display.setHtml(html)
            # Show the synthesis panel
            self.splitter.setSizes([self.width() // 2, self.width() // 2])

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load anchors: {e}")

    @Slot(QUrl)
    def on_anchor_link_clicked(self, url):
        """
        Handles clicks on 'jumpto' links.
        This is a global view, so it can't directly open tabs.
        It will emit a signal for the main window.
        """
        url_str = url.toString()
        if url_str.startswith("jumpto:"):
            try:
                # --- MODIFIED (Step 3.3): Emit signal and close ---
                parts = url_str.split(":")
                project_id = int(parts[1])
                reading_id = int(parts[2])
                outline_id = int(parts[3])

                self.jumpToAnchor.emit(project_id, reading_id, outline_id)
                self.accept()  # Close the global graph dialog
                # --- END MODIFIED ---
            except Exception as e:
                print(f"Error handling jumpto link: {e}")

    def showEvent(self, event):
        """Override showEvent to fit view."""
        super().showEvent(event)
        if not self.timer.isActive():
            QTimer.singleShot(10, self._center_graph)