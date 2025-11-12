# dialogs/global_graph_dialog.py
import sys
import math
import random
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QSplitter, QGraphicsView,
    QGraphicsScene, QGraphicsItem, QLabel, QTextBrowser,
    QMessageBox, QWidget
)
from PySide6.QtCore import Qt, QTimer, QRectF, QPointF, QLineF, Signal, Slot, QUrl
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QBrush, QPainterPath

# Reuse the node and edge items from the project graph for consistency
try:
    from tabs.graph_view_tab import BaseGraphNode, GraphEdgeItem
except ImportError:
    QMessageBox.critical(None, "Import Error", "Could not import graph components from tabs.graph_view_tab.py")
    sys.exit(1)


class GlobalTagNodeItem(BaseGraphNode):
    """
    A specific TagNodeItem for the global graph.
    We're scaling it based on project count.
    """

    def __init__(self, tag_id, name, project_count, graph_view, parent=None):
        self.tag_id = tag_id
        self.project_count = project_count
        super().__init__(name, graph_view, parent)

        # Scale the node based on the count
        # Use a non-linear scale (sqrt) so it doesn't get *too* big
        scale_factor = 1 + (math.sqrt(self.project_count) / 3)
        self.setScale(scale_factor)

        self.setToolTip(f"{name}\nUsed in {project_count} project(s)")

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

        pen = QPen(QColor("#006100"), 2)  # Dark green border
        painter.setPen(pen)
        painter.drawPath(path)

    def mouseDoubleClickEvent(self, event):
        """Override to pass the tag *name* instead of ID."""
        print(f"Global Graph: Node clicked, calling parent tab for tag '{self.name}'")
        # In the global graph, we emit the NAME
        self.graph_view.node_double_clicked(self.name, 'tag')
        event.accept()


class GlobalGraphDialog(QDialog):
    """
    A dialog window that displays a force-directed graph of all
    synthesis tags across all projects.
    """

    # This signal is internal to this dialog, for the node to talk to the dialog
    _tagDoubleClicked = Signal(str)

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.nodes = {}  # Stores node items keyed by tag_name

        self.setWindowTitle("Global Knowledge Graph")
        self.setMinimumSize(1000, 700)
        self.setModal(True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

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

        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.view.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.view.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
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
        self.timer.timeout.connect(self._update_forces)
        self._simulation_steps = 0
        self.REPULSION = 15000  # More repulsion for a global graph
        self.ATTRACTION = 0.005  # Less attraction (no edges)
        self.DAMPING = 0.95

        # --- Connect Internal Signal ---
        self._tagDoubleClicked.connect(self.load_anchors_for_tag)

        # Load the graph
        QTimer.singleShot(0, self.load_global_graph)

    def load_global_graph(self):
        self.timer.stop()
        self.scene.clear()
        self.nodes.clear()

        try:
            tags_data = self.db.get_global_graph_tags()
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Could not load global tags: {e}")
            return

        if not tags_data:
            label = self.scene.addSimpleText("No synthesis tags found across any projects.")
            label.setPos(0, 0)
            return

        # Create all nodes
        for tag in tags_data:
            tag_name = tag['name']
            # --- FIX: Pass tag['id'] as the tag_id ---
            node_item = GlobalTagNodeItem(
                tag_id=tag['id'],  # <--- THIS WAS THE FIX
                name=tag_name,
                project_count=tag['project_count'],
                graph_view=self,  # Pass self (the dialog) as the graph_view
                parent=None
            )
            # --- END FIX ---
            self.scene.addItem(node_item)
            self.nodes[tag_name] = node_item

        # Randomly position nodes
        scene_size = 300 * math.sqrt(len(self.nodes))
        for node in self.nodes.values():
            node.setPos(random.uniform(-scene_size, scene_size),
                        random.uniform(-scene_size, scene_size))

        # Start simulation
        self._simulation_steps = 0
        self.timer.start(16)

    @Slot()
    def _update_forces(self):
        """One tick of the physics simulation (repulsion only)."""
        if not self.nodes:
            self.timer.stop()
            return

        all_nodes = list(self.nodes.values())

        # Reset forces
        for node in all_nodes:
            node.force_x = 0.0
            node.force_y = 0.0

        # Calculate all forces
        for node in all_nodes:
            # Center pull
            center_dx = -node.pos().x()
            center_dy = -node.pos().y()
            node.force_x += center_dx * self.ATTRACTION
            node.force_y += center_dy * self.ATTRACTION

            # Repulsion
            for other_node in all_nodes:
                if node is other_node:
                    continue

                dx = node.pos().x() - other_node.pos().x()
                dy = node.pos().y() - other_node.pos().y()
                distance = math.hypot(dx, dy) + 0.1

                if distance < (300 * math.sqrt(len(all_nodes))):
                    repulsion = self.REPULSION / (distance * distance)  # F = k / r^2
                    node.force_x += (dx / distance) * repulsion
                    node.force_y += (dy / distance) * repulsion

        # Apply all forces
        has_moved = False
        for node in all_nodes:
            if node.isSelected() and self.view.underMouse():  # Don't move selected node
                if not hasattr(node, 'velocity'):
                    node.velocity = QPointF(0, 0)
                node.velocity = QPointF(0, 0)
                node.force_x = 0.0
                node.force_y = 0.0
                continue

            if not hasattr(node, 'velocity'):
                node.velocity = QPointF(0, 0)

            node.velocity = (node.velocity + QPointF(node.force_x, node.force_y)) * self.DAMPING

            if QPointF.dotProduct(node.velocity, node.velocity) > 0.1:
                node.setPos(node.pos() + node.velocity)
                has_moved = True

        # Stop simulation
        self._simulation_steps += 1
        if not has_moved or self._simulation_steps > 200:
            self.timer.stop()
            self._center_graph()
            print("Global graph simulation complete.")

    def _center_graph(self):
        try:
            bounds = self.scene.itemsBoundingRect().adjusted(-100, -100, 100, 100)
            if bounds.isValid():
                self.view.fitInView(bounds, Qt.AspectRatioMode.KeepAspectRatio)
        except Exception as e:
            print(f"Error centering global graph: {e}")

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
        It will just show a message for now.
        """
        url_str = url.toString()
        if url_str.startswith("jumpto:"):
            try:
                parts = url_str.split(":")
                project_id = int(parts[1])
                reading_id = int(parts[2])
                outline_id = int(parts[3])

                # In a real app, this would emit a signal to the main window
                # For now, show an info box
                QMessageBox.information(
                    self,
                    "Global Graph Navigation",
                    f"This anchor is in:\n\n"
                    f"Project ID: {project_id}\n"
                    f"Reading ID: {reading_id}\n"
                    f"Outline ID: {outline_id}\n\n"
                    "(This would jump to the project in a full implementation.)"
                )
            except Exception as e:
                print(f"Error handling jumpto link: {e}")

    def showEvent(self, event):
        """Override showEvent to fit view."""
        super().showEvent(event)
        if not self.timer.isActive():
            QTimer.singleShot(10, self._center_graph)