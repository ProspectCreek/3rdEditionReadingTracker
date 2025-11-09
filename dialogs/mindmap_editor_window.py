# dialogs/mindmap_editor_window.py
import sys
import math
import json
from PySide6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsItem, QGraphicsLineItem,
    QGraphicsPolygonItem, QGraphicsEllipseItem, QGraphicsRectItem, QGraphicsTextItem,
    QDialog, QVBoxLayout, QMenu, QMessageBox, QColorDialog, QFontDialog,
    QInputDialog, QFileDialog, QGraphicsSceneMouseEvent, QGraphicsRectItem,
    QApplication, QMenuBar
)
from PySide6.QtGui import (
    QPainter, QColor, QFont, QPen, QBrush, QPolygonF, QImage,
    QAction, QKeySequence, QPainterPath, QPainterPathStroker
)
from PySide6.QtCore import (
    Qt, QRectF, QPointF, QLineF
)

# --- Constants ---
NODE_MIN_WIDTH = 80
NODE_MIN_HEIGHT = 40
H_PAD = 25
V_PAD = 15


class MindmapEdge(QGraphicsLineItem):
    """A custom QGraphicsItem for drawing edges between nodes."""

    def __init__(self, from_node, to_node, edge_data, parent=None):
        super().__init__(parent)
        self.from_node = from_node
        self.to_node = to_node
        self.edge_data = edge_data

        if self.from_node:
            self.from_node.add_edge(self)
        if self.to_node:
            self.to_node.add_edge(self)

        self.setZValue(-1)  # Ensure edges are behind nodes

        # Make edge explicitly selectable (helps future flows and consistency)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)

        self.update_style()
        self.update_position()

    def get_data(self):
        """Returns the serializable data for this edge."""
        return {
            'from_node_id': self.from_node.node_id,
            'to_node_id': self.to_node.node_id,
            'color': self.edge_data.get('color', 'black'),
            'style': self.edge_data.get('style', 'solid'),
            'width': self.edge_data.get('width', 2),
            'arrow_style': self.edge_data.get('arrow_style', 'none')
        }

    def update_style(self):
        """Applies color, width, and style from edge_data."""
        pen = QPen(QColor(self.edge_data.get('color', 'black')))
        pen.setWidth(self.edge_data.get('width', 2))

        style = self.edge_data.get('style', 'solid')
        if style == 'dashed':
            pen.setStyle(Qt.PenStyle.DashLine)
        else:
            pen.setStyle(Qt.PenStyle.SolidLine)

        self.setPen(pen)

    def update_position(self):
        """Recalculates and sets the line's start and end points."""
        if not self.from_node or not self.to_node:
            return
        from_point = self.from_node.get_connection_point(self.to_node.pos())
        to_point = self.to_node.get_connection_point(self.from_node.pos())
        self.setLine(QLineF(from_point, to_point))

    # --- Make line clickable ---
    def shape(self):
        """Returns a wider shape for easier click detection."""
        line = self.line()
        path = QPainterPath(line.p1())
        path.lineTo(line.p2())
        stroker = QPainterPathStroker()
        stroker.setWidth(10)  # 10px wide hit area for right-clicks
        return stroker.createStroke(path)

    def boundingRect(self):
        """Ensures the bounding rect accounts for the wider shape."""
        return self.shape().boundingRect()

    def paint(self, painter, option, widget):
        """Paints the line and custom arrows."""
        # Draw the line itself
        super().paint(painter, option, widget)

        arrow_style = self.edge_data.get('arrow_style', 'none')
        if arrow_style == 'none':
            return

        painter.setPen(self.pen())
        painter.setBrush(QBrush(self.pen().color()))

        line = self.line()
        if line.length() == 0:
            return

        angle = math.atan2(-line.dy(), line.dx())
        arrow_size = 5 + self.pen().width() * 2

        # Draw arrow at the end
        if arrow_style in ['last', 'both']:
            arrow_p1 = line.p2() - QPointF(math.sin(angle + math.pi / 3) * arrow_size,
                                           math.cos(angle + math.pi / 3) * arrow_size)
            arrow_p2 = line.p2() - QPointF(math.sin(angle + math.pi - math.pi / 3) * arrow_size,
                                           math.cos(angle + math.pi - math.pi / 3) * arrow_size)
            arrow_head = QPolygonF([line.p2(), arrow_p1, arrow_p2])
            painter.drawPolygon(arrow_head)

        # Draw arrow at the start
        if arrow_style == 'both':
            arrow_p1 = line.p1() + QPointF(math.sin(angle + math.pi / 3) * arrow_size,
                                           math.cos(angle + math.pi / 3) * arrow_size)
            arrow_p2 = line.p1() + QPointF(math.sin(angle + math.pi - math.pi / 3) * arrow_size,
                                           math.cos(angle + math.pi - math.pi / 3) * arrow_size)
            arrow_head = QPolygonF([line.p1(), arrow_p1, arrow_p2])
            painter.drawPolygon(arrow_head)


class MindmapNode(QGraphicsItem):
    """A custom QGraphicsItem for a mindmap node."""

    def __init__(self, node_id, node_data, default_font, interactive=True, parent=None):
        super().__init__(parent)
        self.node_id = str(node_id)  # Ensure it's a string for consistency
        self.node_data = node_data
        self.edges = []

        # Set shape, position, and flags
        self.setPos(node_data['x'], node_data['y'])

        if interactive:
            self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
            self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
            self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)

        # Create text item as a child
        self.text_item = QGraphicsTextItem(self)

        # Ignore mouse on the text so the node handles clicks
        self.text_item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)

        self.text_item.setHtml(self._text_to_html(node_data.get('text', '')))

        doc = self.text_item.document()
        option = doc.defaultTextOption()
        option.setAlignment(Qt.AlignmentFlag.AlignCenter)
        doc.setDefaultTextOption(option)

        # Set font
        font_family = node_data.get('font_family') or default_font.family()
        font_size = node_data.get('font_size') or default_font.pointSize()
        font_weight = default_font.weight()
        if node_data.get('font_weight') == 'bold':
            font_weight = QFont.Weight.Bold
        elif node_data.get('font_weight') == 'normal':
            font_weight = QFont.Weight.Normal

        font_italic = default_font.italic()
        if node_data.get('font_slant') == 'italic':
            font_italic = True
        elif node_data.get('font_slant') == 'roman':
            font_italic = False

        font = QFont(font_family, font_size)
        font.setWeight(font_weight)
        font.setItalic(font_italic)
        self.text_item.setFont(font)

        self.text_item.setDefaultTextColor(QColor(node_data.get('text_color', 'black')))

        self.update_geometry()

    def _text_to_html(self, text):
        """Converts newline characters to HTML breaks for QGraphicsTextItem."""
        if text is None:
            return ""
        return str(text).replace('\n', '<br>')

    def get_data(self):
        """Returns the serializable data for this node."""
        font = self.text_item.font()
        data = self.node_data.copy()
        data.update({
            'id': self.node_id,
            'x': self.pos().x(),
            'y': self.pos().y(),
            'text': self.text_item.toPlainText(),
            'text_color': self.text_item.defaultTextColor().name(),
            'font_family': font.family(),
            'font_size': font.pointSize(),
            'font_weight': 'bold' if font.weight() >= QFont.Weight.Bold else 'normal',
            'font_slant': 'italic' if font.italic() else 'roman',
        })
        return data

    def update_geometry(self):
        """Recalculates the node's shape based on its text content."""
        self.prepareGeometryChange()

        # 1. Get natural text rect (unwrapped)
        self.text_item.setTextWidth(-1)
        text_rect_unwrapped = self.text_item.boundingRect()

        # 2. Ideal node width
        w = max(NODE_MIN_WIDTH, text_rect_unwrapped.width() + H_PAD)

        # 3. Wrap to width (with padding inside)
        self.text_item.setTextWidth(w - H_PAD)

        # 4. Get wrapped rect (may be taller)
        text_rect_wrapped = self.text_item.boundingRect()

        # 5. Final height
        h = max(NODE_MIN_HEIGHT, text_rect_wrapped.height() + V_PAD)

        # 6. Circle handling
        shape = self.node_data.get('shape_type', 'oval')
        if shape == 'circle':
            w = h = max(w, h)
            self.text_item.setTextWidth(w - H_PAD)
            text_rect_wrapped = self.text_item.boundingRect()

        # 7. Store size
        self.node_data['width'] = w
        self.node_data['height'] = h

        # 8. Center text block
        text_x = -text_rect_wrapped.width() / 2
        text_y = -text_rect_wrapped.height() / 2
        self.text_item.setPos(text_x, text_y)

    def boundingRect(self):
        w = self.node_data.get('width', NODE_MIN_WIDTH)
        h = self.node_data.get('height', NODE_MIN_HEIGHT)
        return QRectF(-w / 2, -h / 2, w, h)

    def shape(self):
        """Returns the precise QPainterPath of the node for accurate click detection."""
        path = QPainterPath()
        rect = self.boundingRect()
        shape_type = self.node_data.get('shape_type', 'oval')

        if shape_type in ['oval', 'circle']:
            path.addEllipse(rect)
        elif shape_type == 'rectangle':
            path.addRect(rect)
        elif shape_type == 'rounded_rectangle':
            path.addRoundedRect(rect, 20, 20)
        elif shape_type in ['hexagon', 'diamond', 'parallelogram']:
            poly = self.get_shape_polygon(rect.width(), rect.height())
            path.addPolygon(poly)
        else:
            path.addRect(rect)

        return path

    def get_shape_polygon(self, w, h):
        """Helper to get points for polygon shapes."""
        shape = self.node_data.get('shape_type', 'oval')
        half_w, half_h = w / 2, h / 2

        if shape == 'hexagon':
            return QPolygonF([
                QPointF(0, -half_h), QPointF(half_w, -half_h / 2),
                QPointF(half_w, half_h / 2), QPointF(0, half_h),
                QPointF(-half_w, half_h / 2), QPointF(-half_w, -half_h / 2)
            ])
        if shape == 'diamond':
            return QPolygonF([
                QPointF(0, -half_h), QPointF(half_w, 0),
                QPointF(0, half_h), QPointF(-half_w, 0)
            ])
        if shape == 'parallelogram':
            offset = w * 0.2
            return QPolygonF([
                QPointF(-half_w + offset, -half_h), QPointF(half_w + offset, -half_h),
                QPointF(half_w - offset, half_h), QPointF(-half_w - offset, h/2)
            ])
        return QPolygonF()  # Empty

    def paint(self, painter, option, widget):
        rect = self.boundingRect()

        # Set pen (outline)
        pen_color = QColor('cyan') if self.isSelected() else QColor(self.node_data.get('outline_color', 'black'))
        pen = QPen(pen_color)
        pen.setWidth(2)
        painter.setPen(pen)

        # Set brush (fill)
        brush = QBrush(QColor(self.node_data.get('fill_color', 'white')))
        painter.setBrush(brush)

        # Draw shape using the QPainterPath from shape() for consistency
        painter.drawPath(self.shape())

    def itemChange(self, change, value):
        """Called when item's state changes, e.g., it's moved."""
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            for edge in self.edges:
                edge.update_position()
        return super().itemChange(change, value)

    def add_edge(self, edge):
        if edge not in self.edges:
            self.edges.append(edge)

    def remove_edge(self, edge):
        if edge in self.edges:
            self.edges.remove(edge)

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
            except Exception as e:
                print(f"Error calculating intersection: {e}")

        if intersect_points:
            intersect_points.sort(key=lambda p: QLineF(p, to_point).length())
            return intersect_points[0]

        return center_point  # Fallback

    def set_text(self, text):
        self.text_item.setHtml(self._text_to_html(text))
        self.update_geometry()
        for edge in self.edges:
            edge.update_position()

    def set_font(self, font):
        self.text_item.setFont(font)
        self.update_geometry()
        for edge in self.edges:
            edge.update_position()

    def set_color(self, part, color):
        if part == 'fill':
            self.node_data['fill_color'] = color.name()
        elif part == 'outline':
            self.node_data['outline_color'] = color.name()
        elif part == 'text':
            self.node_data['text_color'] = color.name()
            self.text_item.setDefaultTextColor(color)
        self.update()  # Triggers repaint

    def set_shape(self, shape_type):
        self.node_data['shape_type'] = shape_type
        self.update_geometry()
        self.update()
        for edge in self.edges:
            edge.update_position()


class MindmapGraphicsView(QGraphicsView):
    """Subclassed QGraphicsView to handle mouse events for drawing."""

    def __init__(self, scene, parent_dialog):
        super().__init__(scene, parent_dialog)
        self.parent_dialog = parent_dialog
        self._marquee_rect = None

    def get_node_at(self, view_pos):
        """
        Gets the MindmapNode at a QPoint in **view coordinates**, checking for
        text items and returning their parent node if found.
        """
        item = self.itemAt(view_pos)
        if isinstance(item, MindmapNode):
            return item
        if isinstance(item, QGraphicsTextItem) and isinstance(item.parentItem(), MindmapNode):
            return item.parentItem()
        return None

    def mousePressEvent(self, event):
        """Handles mouse presses for selection, drawing, and marquee."""
        # Handle connection mode first
        if self.parent_dialog.is_in_connection_mode():
            self.parent_dialog.hide_drawing_line()
            clicked_node = self.get_node_at(event.pos())
            self.parent_dialog.finish_connection_mode(clicked_node)
            event.accept()
            return

        # Left-click selection / marquee
        if event.button() == Qt.MouseButton.LeftButton:
            clicked_node = self.get_node_at(event.pos())

            if clicked_node is None:
                # Clicked on empty space: Start marquee selection
                self.scene().clearSelection()
                self._marquee_rect = QGraphicsRectItem(
                    QRectF(self.mapToScene(event.pos()), self.mapToScene(event.pos())))
                self._marquee_rect.setPen(QPen(Qt.GlobalColor.blue, 1, Qt.PenStyle.DashLine))
                self.scene().addItem(self._marquee_rect)
            else:
                # Let the base class handle left-click selection and drag
                super().mousePressEvent(event)
        # Right-click does nothing here; contextMenuEvent on the dialog will handle it.

    def mouseMoveEvent(self, event):
        scene_pos = self.mapToScene(event.pos())
        self.parent_dialog.update_last_mouse_pos(scene_pos)  # Update position for pasting

        if self.parent_dialog.is_in_connection_mode():
            self.parent_dialog.update_drawing_line(scene_pos)
        elif self._marquee_rect:
            rect = QRectF(self._marquee_rect.rect().topLeft(), scene_pos).normalized()
            self._marquee_rect.setRect(rect)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._marquee_rect:
            # Finish marquee selection
            rect = self._marquee_rect.rect()
            self.scene().removeItem(self._marquee_rect)
            self._marquee_rect = None

            path = QPainterPath()
            path.addRect(rect)
            self.scene().setSelectionArea(path, mode=Qt.ItemSelectionMode.IntersectsItemShape)
        else:
            super().mouseReleaseEvent(event)


class MindmapEditorWindow(QDialog):
    """PySide6 replica of the Mindmap Editor Window."""

    def __init__(self, parent, db_manager, mindmap_id, mindmap_name):
        super().__init__(parent)
        self.db = db_manager
        self.mindmap_id = mindmap_id
        self.mindmap_name = mindmap_name

        self.setWindowTitle(f"Mind Map: {self.mindmap_name}")
        self.setMinimumSize(1000, 700)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.setModal(False)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        self.nodes = {}
        self.edges = []
        self.default_font = QFont("Times New Roman", 12)

        self._clipboard = {}
        self._next_node_id_counter = 1
        self._last_mouse_pos = QPointF(100, 100)
        self._selected_edge = None

        self._drawing_connection_from_node = None
        self._drawing_line = None

        self.load_mindmap_data = self.db.get_mindmap_data

        self.menu_bar = QMenuBar(self)
        layout.addWidget(self.menu_bar)

        self._create_menus()

        self.scene = QGraphicsScene(self)
        self.view = MindmapGraphicsView(self.scene, self)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setDragMode(QGraphicsView.DragMode.NoDrag)

        layout.addWidget(self.view)

        self.scene.selectionChanged.connect(self.update_selection_from_scene)

        self.load_mindmap()
        self.view.setFocus()

    def update_last_mouse_pos(self, pos):
        """Called by the view to keep track of the mouse."""
        self._last_mouse_pos = pos

    def _export_as_image(self):
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export Mind Map as Image", "", "PNG Image (*.png);;JPEG Image (*.jpg)"
        )
        if not filepath:
            return

        try:
            image = QImage(self.scene.sceneRect().size().toSize(), QImage.Format.Format_ARGB32)
            image.fill(Qt.GlobalColor.white)

            painter = QPainter(image)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            self.scene.render(painter)
            painter.end()

            if image.save(filepath):
                QMessageBox.information(self, "Export Successful", f"Mind map saved to:\n{filepath}")
            else:
                QMessageBox.critical(self, "Export Failed", f"Could not save image to:\n{filepath}")
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"An error occurred: {e}")

    def save_mindmap(self, show_message=True):
        nodes_to_save = [node.get_data() for node in self.nodes.values()]
        edges_to_save = [edge.get_data() for edge in self.edges]

        try:
            self.db.save_mindmap_data(self.mindmap_id, nodes_to_save, edges_to_save)
            if show_message:
                QMessageBox.information(self, "Success", "Mind map saved successfully.")
        except Exception as e:
            if show_message:
                QMessageBox.critical(self, "Error", f"Could not save mind map: {e}")

    def load_mindmap(self):
        self.scene.clear()
        self.nodes.clear()
        self.edges.clear()

        details_row = self.db.get_mindmap_details(self.mindmap_id)
        details = dict(details_row) if details_row else {}

        if details and details.get('default_font_family'):
            font = QFont(details.get('default_font_family'), details.get('default_font_size', 12))
            font.setWeight(QFont.Weight.Bold if details.get('default_font_weight') == 'bold' else QFont.Weight.Normal)
            font.setItalic(details.get('default_font_slant') == 'italic')
            self.default_font = font
        else:
            self.default_font = QFont("Times New Roman", 12)

        data = self.db.get_mindmap_data(self.mindmap_id)

        max_id_num = 0
        all_nodes_data = data.get('nodes', [])
        if not all_nodes_data:
            self.add_node(QPointF(200, 200), text="Central Idea")
            self._next_node_id_counter = 2
        else:
            for node_data in all_nodes_data:
                node_id_text = str(node_data['node_id_text'])
                pos = QPointF(node_data['x'], node_data['y'])
                self.add_node(pos, from_db_id=node_id_text, **node_data)

                if node_id_text.startswith('new_'):
                    try:
                        num = int(node_id_text.split('_')[1])
                        if num > max_id_num: max_id_num = num
                    except Exception:
                        pass
                else:
                    try:
                        num = int(node_id_text)
                        if num > max_id_num: max_id_num = num
                    except Exception:
                        pass

            self._next_node_id_counter = max_id_num + 1

        for edge_data in data.get('edges', []):
            from_node = self.nodes.get(str(edge_data['from_node_id_text']))
            to_node = self.nodes.get(str(edge_data['to_node_id_text']))

            if from_node and to_node:
                self.add_edge(from_node, to_node, **edge_data)

        scene_rect = self.scene.itemsBoundingRect()
        if not scene_rect.isEmpty():
            self.view.setSceneRect(scene_rect.adjusted(-50, -50, 50, 50))

    def _copy_selection(self):
        nodes = self.get_selected_nodes()
        if not nodes:
            return

        self._clipboard = {'nodes': [], 'edges': []}

        min_x = min(n.pos().x() for n in nodes)
        min_y = min(n.pos().y() for n in nodes)

        for node in nodes:
            node_data = node.get_data()
            node_data['original_id'] = node.node_id
            node_data['rel_x'] = node.pos().x() - min_x
            node_data['rel_y'] = node.pos().y() - min_y
            self._clipboard['nodes'].append(node_data)

        selected_ids = {n.node_id for n in nodes}
        for edge in self.edges:
            if edge.from_node.node_id in selected_ids and edge.to_node.node_id in selected_ids:
                edge_data = edge.get_data()
                self._clipboard['edges'].append(edge_data)

    def _paste_selection(self):
        if not self._clipboard or not self._clipboard.get('nodes'):
            return

        self.scene.clearSelection()

        paste_pos = self._last_mouse_pos

        id_map = {}
        newly_created_nodes = []

        for node_data in self._clipboard['nodes']:
            original_id = node_data['original_id']

            new_x = paste_pos.x() + node_data['rel_x'] + 20
            new_y = paste_pos.y() + node_data['rel_y'] + 20

            kwargs = node_data.copy()
            for key in ['original_id', 'rel_x', 'rel_y', 'x', 'y', 'id']:
                kwargs.pop(key, None)

            new_node = self.add_node(QPointF(new_x, new_y), **kwargs)
            if new_node:
                id_map[original_id] = new_node
                newly_created_nodes.append(new_node)

        for edge_data in self._clipboard['edges']:
            original_from = str(edge_data['from_node_id'])
            original_to = str(edge_data['to_node_id'])

            new_from_node = id_map.get(original_from)
            new_to_node = id_map.get(original_to)

            if new_from_node and new_to_node:
                kwargs = edge_data.copy()
                for key in ['from_node_id', 'to_node_id', 'id']:
                    kwargs.pop(key, None)
                self.add_edge(new_from_node, new_to_node, **kwargs)

        for node in newly_created_nodes:
            node.setSelected(True)

    def closeEvent(self, event):
        """Handle window close event."""
        self.cancel_connection_mode()
        self.save_mindmap(show_message=False)
        event.accept()

    def _create_menus(self):
        """Creates the menu bar and context menu actions."""

        self.save_action = QAction("Save", self)
        self.save_action.setShortcut(QKeySequence(QKeySequence.StandardKey.Save))
        self.save_action.triggered.connect(self.save_mindmap)

        self.export_action = QAction("Export as Image...", self)
        self.export_action.triggered.connect(self._export_as_image)

        self.set_default_font_action = QAction("Set Default Font...", self)
        self.set_default_font_action.triggered.connect(self._set_default_font)

        file_menu = self.menu_bar.addMenu("File")
        file_menu.addAction(self.save_action)
        file_menu.addAction(self.export_action)

        font_menu = self.menu_bar.addMenu("Font")
        font_menu.addAction(self.set_default_font_action)

        self.add_node_action = QAction("Add Node", self)
        self.add_node_action.setShortcut(QKeySequence("Ctrl+N"))
        self.add_node_action.triggered.connect(self.add_node_at_last_pos)
        self.addAction(self.add_node_action)

        self.copy_action = QAction("Copy", self)
        self.copy_action.setShortcut(QKeySequence(QKeySequence.StandardKey.Copy))
        self.copy_action.triggered.connect(self._copy_selection)
        self.addAction(self.copy_action)

        self.paste_action = QAction("Paste", self)
        self.paste_action.setShortcut(QKeySequence(QKeySequence.StandardKey.Paste))
        self.paste_action.triggered.connect(self._paste_selection)
        self.addAction(self.paste_action)

    # --- Connection Drawing Methods ---
    def is_in_connection_mode(self):
        return self._drawing_connection_from_node is not None

    def start_connection_mode(self, node):
        """Starts the line drawing mode from a given node."""
        self.cancel_connection_mode()
        self._drawing_connection_from_node = node
        start_pos = node.pos()
        self._drawing_line = QGraphicsLineItem(QLineF(start_pos, start_pos))
        self._drawing_line.setPen(QPen(Qt.GlobalColor.black, 2, Qt.PenStyle.DashLine))
        self.scene.addItem(self._drawing_line)
        self.view.setCursor(Qt.CursorShape.CrossCursor)

    def hide_drawing_line(self):
        """Temporarily hides the drawing line so it doesn't block clicks."""
        if self._drawing_line:
            self._drawing_line.show()
            self._drawing_line.hide()

    def update_drawing_line(self, scene_pos):
        """Updates the temporary line to follow the mouse."""
        if self._drawing_line and self._drawing_connection_from_node:
            if not self._drawing_line.isVisible():
                self._drawing_line.show()
            self._drawing_line.setLine(QLineF(self._drawing_connection_from_node.pos(), scene_pos))

    def finish_connection_mode(self, end_node):
        """Finishes (or cancels) the line drawing mode."""
        if isinstance(end_node, MindmapNode) and self._drawing_connection_from_node != end_node:
            # Success
            self.add_edge(self._drawing_connection_from_node, end_node)

        # Always cancel mode
        self.cancel_connection_mode()

    def cancel_connection_mode(self):
        """Cleans up the connection drawing state."""
        if self._drawing_line:
            self.scene.removeItem(self._drawing_line)
            self._drawing_line = None
        self._drawing_connection_from_node = None
        self.view.setCursor(Qt.CursorShape.ArrowCursor)

    def contextMenuEvent(self, event):
        """Show right-click context menu on the view."""
        # Cancel connection mode if active
        if self.is_in_connection_mode():
            self.cancel_connection_mode()
            return

        # --- KEY FIX: correct coordinate mapping ---
        # Convert from global -> view coords for itemAt/get_node_at
        view_pos = self.view.mapFromGlobal(event.globalPos())
        scene_pos = self.view.mapToScene(view_pos)
        self._last_mouse_pos = scene_pos

        raw_item = self.view.itemAt(view_pos)
        clicked_node = self.view.get_node_at(view_pos)
        # -------------------------------------------

        # Edge detection (MindmapEdge inherits QGraphicsLineItem)
        clicked_edge = raw_item if isinstance(raw_item, MindmapEdge) else None
        if not clicked_node and isinstance(raw_item, QGraphicsTextItem) and isinstance(raw_item.parentItem(), MindmapNode):
            clicked_node = raw_item.parentItem()

        menu = QMenu(self)

        if clicked_node:
            self._selected_edge = None
            if not clicked_node.isSelected():
                self.scene.clearSelection()
                clicked_node.setSelected(True)

            menu.addAction(self.copy_action)
            if self._clipboard:
                menu.addAction(self.paste_action)
            menu.addSeparator()
            menu.addAction("Edit Text", lambda: self.edit_node_text(clicked_node))
            menu.addAction("Create Connection", lambda: self.start_connection_mode(clicked_node))

            format_menu = menu.addMenu("Format Node")
            shape_menu = format_menu.addMenu("Change Node Shape")
            shape_menu.addAction("Circle", lambda: self._change_node_shape('circle'))
            shape_menu.addAction("Oval", lambda: self._change_node_shape('oval'))
            shape_menu.addAction("Rectangle", lambda: self._change_node_shape('rectangle'))
            shape_menu.addAction("Rounded Rectangle", lambda: self._change_node_shape('rounded_rectangle'))
            shape_menu.addAction("Hexagon", lambda: self._change_node_shape('hexagon'))
            shape_menu.addAction("Diamond", lambda: self._change_node_shape('diamond'))
            shape_menu.addAction("Parallelogram", lambda: self._change_node_shape('parallelogram'))
            format_menu.addSeparator()
            format_menu.addAction("Change Node Fill Color...", lambda: self._change_color('fill'))
            format_menu.addAction("Change Node Outline Color...", lambda: self._change_color('outline'))
            format_menu.addAction("Change Node Text Color...", lambda: self._change_color('text'))
            format_menu.addSeparator()
            format_menu.addAction("Change Node Font...", self._change_font)

            menu.addSeparator()
            menu.addAction("Delete Node(s)", self.delete_selected_nodes)

        elif clicked_edge:
            self.scene.clearSelection()
            self._selected_edge = clicked_edge

            menu.addAction("Change Line Color...", self._change_edge_color)

            width_menu = menu.addMenu("Change Line Width")
            for w in [1, 2, 3, 5, 8]:
                width_menu.addAction(f"{w}px", lambda width=w: self._change_edge_width(width))

            style_menu = menu.addMenu("Change Line Style")
            style_menu.addAction("Solid", lambda: self._change_edge_style('solid'))
            style_menu.addAction("Dashed", lambda: self._change_edge_style('dashed'))

            arrow_menu = menu.addMenu("Change Arrow Style")
            arrow_menu.addAction("None", lambda: self._change_edge_arrow_style('none'))
            arrow_menu.addAction("One Arrow (End)", lambda: self._change_edge_arrow_style('last'))
            arrow_menu.addAction("Two Arrows (Both)", lambda: self._change_edge_arrow_style('both'))

            menu.addSeparator()
            menu.addAction("Delete Connection", self._delete_edge)

        else:
            self.scene.clearSelection()
            self._selected_edge = None
            if self._clipboard:
                menu.addAction(self.paste_action)
            menu.addAction("Add Node Here", lambda: self.add_node(scene_pos))

        menu.exec(event.globalPos())

    def update_selection_from_scene(self):
        """Syncs our selection state with the scene's."""
        self._selected_edge = None
        self.view.update()

    def get_selected_nodes(self):
        """Returns a list of currently selected MindmapNode items."""
        return [item for item in self.scene.selectedItems() if isinstance(item, MindmapNode)]

    def add_node_at_last_pos(self):
        self.add_node(self._last_mouse_pos)

    def add_node(self, pos, text="New Node", from_db_id=None, **kwargs):
        """Adds a new node to the scene."""
        is_new_node = from_db_id is None

        node_id_text = from_db_id if from_db_id else f"new_{self._next_node_id_counter}"
        if is_new_node:
            self._next_node_id_counter += 1

        if node_id_text in self.nodes:
            print(f"Warning: Node with ID {node_id_text} already exists. Skipping.")
            return None

        node_data = {
            'x': pos.x(), 'y': pos.y(), 'text': text,
            'shape_type': 'oval', 'fill_color': 'white',
            'outline_color': 'black', 'text_color': 'black',
            'width': NODE_MIN_WIDTH, 'height': NODE_MIN_HEIGHT
        }
        node_data.update(kwargs)

        node_item = MindmapNode(node_id_text, node_data, self.default_font)
        self.scene.addItem(node_item)
        self.nodes[node_id_text] = node_item
        return node_item

    def add_edge(self, from_node, to_node, **edge_data):
        """Adds a new edge to the scene."""
        for edge in self.edges:
            if (edge.from_node == from_node and edge.to_node == to_node) or \
               (edge.from_node == to_node and edge.to_node == from_node):
                return

        edge_item = MindmapEdge(from_node, to_node, edge_data)
        self.scene.addItem(edge_item)
        self.edges.append(edge_item)

    def edit_node_text(self, node):
        """Opens a dialog to edit the node's text."""
        if not node:
            nodes = self.get_selected_nodes()
            if len(nodes) != 1:
                return
            node = nodes[0]

        current_text = node.text_item.toPlainText()
        new_text, ok = QInputDialog.getMultiLineText(self, "Edit Node Text", "Text:", current_text)

        if ok and new_text != current_text:
            node.set_text(new_text)

    def delete_selected_nodes(self):
        """Deletes all selected nodes and their connected edges."""
        nodes_to_delete = self.get_selected_nodes()
        if not nodes_to_delete:
            return

        reply = QMessageBox.question(
            self, "Delete Node(s)",
            f"Are you sure you want to delete {len(nodes_to_delete)} node(s)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.No:
            return

        for node in nodes_to_delete:
            for edge in list(node.edges):
                if edge in self.edges:
                    self.edges.remove(edge)
                if edge.from_node:
                    edge.from_node.remove_edge(edge)
                if edge.to_node:
                    edge.to_node.remove_edge(edge)
                self.scene.removeItem(edge)

            if node.node_id in self.nodes:
                del self.nodes[node.node_id]
            self.scene.removeItem(node)

    # --- Formatting Methods ---

    def _change_color(self, part):
        nodes = self.get_selected_nodes()
        if not nodes:
            return

        initial_color = QColor(nodes[0].get_data().get(f"{part}_color", "black"))
        color = QColorDialog.getColor(initial_color, self, f"Choose {part.capitalize()} Color")

        if color.isValid():
            for node in nodes:
                node.set_color(part, color)

    def _change_font(self):
        nodes = self.get_selected_nodes()
        if not nodes:
            return

        initial_font = nodes[0].text_item.font()

        ok, font = QFontDialog.getFont(initial_font, self, "Choose Font")

        if ok:
            for node in nodes:
                node.set_font(font)

    def _set_default_font(self):
        ok, font = QFontDialog.getFont(self.default_font, self, "Choose Default Font")

        if ok:
            self.default_font = font
            font_details = {
                'family': font.family(), 'size': font.pointSize(),
                'weight': 'bold' if font.weight() >= QFont.Weight.Bold else 'normal',
                'slant': 'italic' if font.italic() else 'roman'
            }
            self.db.update_mindmap_defaults(self.mindmap_id, font_details)

            reply = QMessageBox.question(
                self,
                "Apply Font",
                "Apply this new default font to all nodes?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                for node in self.nodes.values():
                    node.set_font(font)

    def _change_node_shape(self, shape_type):
        nodes = self.get_selected_nodes()
        for node in nodes:
            node.set_shape(shape_type)

    # --- Edge Formatting ---

    def _change_edge_color(self):
        if not self._selected_edge:
            return
        initial_color = self._selected_edge.pen().color()
        color = QColorDialog.getColor(initial_color, self, "Choose Line Color")
        if color.isValid():
            self._selected_edge.edge_data['color'] = color.name()
            self._selected_edge.update_style()

    def _change_edge_width(self, width):
        if not self._selected_edge:
            return
        self._selected_edge.edge_data['width'] = width
        self._selected_edge.update_style()

    def _change_edge_style(self, style):
        if not self._selected_edge:
            return
        self._selected_edge.edge_data['style'] = style
        self._selected_edge.update_style()

    def _change_edge_arrow_style(self, style):
        if not self._selected_edge:
            return
        self._selected_edge.edge_data['arrow_style'] = style
        self._selected_edge.update()  # Redraw to show/hide arrows

    def _delete_edge(self):
        if not self._selected_edge:
            return
        reply = QMessageBox.question(
            self, "Delete Connection", "Delete this connection?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            if self._selected_edge.from_node:
                self._selected_edge.from_node.remove_edge(self._selected_edge)
            if self._selected_edge.to_node:
                self._selected_edge.to_node.remove_edge(self._selected_edge)
            if self._selected_edge in self.edges:
                self.edges.remove(self._selected_edge)

            self.scene.removeItem(self._selected_edge)
            self._selected_edge = None
