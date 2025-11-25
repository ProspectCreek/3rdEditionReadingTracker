# tabs/pdf_node_viewer.py
import sys
import os

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGraphicsView, QGraphicsScene,
    QPushButton, QLabel, QListWidget, QDockWidget, QWidget, QSplitter,
    QGraphicsPixmapItem, QMenu, QInputDialog, QMessageBox, QGraphicsRectItem,
    QFormLayout, QLineEdit, QTextEdit, QComboBox, QDialogButtonBox, QApplication,
    QListWidgetItem, QColorDialog, QFrame, QTabWidget, QSizePolicy
)
from PySide6.QtCore import Qt, QPointF, QRectF, Signal, QEvent, QPoint
from PySide6.QtGui import QPixmap, QImage, QPainter, QPen, QColor, QAction, QCursor, QIcon

from tabs.pdf_graph_helpers import PdfMarkerNode

# --- Stylesheet for Viewer ---
VIEWER_STYLESHEET = """
QDialog {
    background-color: #F3F4F6;
}
QFrame#LeftPanel {
    background-color: #FFFFFF;
    border-right: 1px solid #E5E7EB;
}
QLabel {
    font-family: 'Segoe UI', sans-serif;
    color: #374151;
    font-size: 13px;
}
QLabel#Header {
    font-size: 12px;
    font-weight: bold;
    text-transform: uppercase;
    color: #6B7280;
    margin-top: 10px;
    margin-bottom: 4px;
}
QListWidget {
    border: 1px solid #E5E7EB;
    border-radius: 6px;
    background-color: #FFFFFF;
    outline: none;
    font-size: 13px;
}
QListWidget::item {
    padding: 4px 8px;
    border-bottom: 1px solid #F9FAFB;
    color: #1F2937;
}
QListWidget::item:selected {
    background-color: #EFF6FF;
    color: #1D4ED8;
    border-left: 3px solid #2563EB;
}
QPushButton {
    background-color: #FFFFFF;
    border: 1px solid #D1D5DB;
    border-radius: 4px;
    padding: 4px 12px;
    color: #374151;
    font-weight: 600;
    font-size: 12px;
}
QPushButton:hover {
    background-color: #F9FAFB;
    border-color: #9CA3AF;
}
QPushButton:pressed {
    background-color: #E5E7EB;
}
QLineEdit {
    border: 1px solid #D1D5DB;
    border-radius: 4px;
    padding: 4px;
    background: #FFF;
}
QTabWidget::pane {
    border: 1px solid #E5E7EB;
    background: #FFF;
    border-radius: 4px;
}
QTabBar::tab {
    background: #F3F4F6;
    padding: 6px 12px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    color: #6B7280;
}
QTabBar::tab:selected {
    background: #FFF;
    color: #2563EB;
    border-bottom: 2px solid #2563EB;
}
QGraphicsView {
    border: none;
    background-color: #525659; /* Dark grey standard PDF background */
}
"""


class PdfNodeViewer(QDialog):
    """
    A pop-out window for viewing a PDF, adding spatial nodes, and
    selecting text via marquee.
    """

    def __init__(self, db, reading_id, attachment_id, file_path, parent=None):
        super().__init__(parent)
        self.db = db
        self.reading_id = reading_id
        self.attachment_id = attachment_id
        self.file_path = file_path

        # 1. Window Flags for proper maximization
        self.setWindowFlags(Qt.Window)

        self.setWindowTitle(f"PDF Node Viewer - {os.path.basename(file_path)}")
        self.resize(1400, 900)
        self.setStyleSheet(VIEWER_STYLESHEET)

        self.pdf_doc = None
        self.current_page_idx = 0
        self.zoom_level = 1.5
        self.project_id = None

        # --- FIX: Robust Project ID Fetching (handles QDA Tool context) ---
        self._resolve_project_id()

        self._marquee_rect_item = None
        self._marquee_start = None
        self._is_marquee_mode = False

        self.setup_ui()

        if fitz:
            self.load_pdf()
        else:
            QMessageBox.critical(self, "Error", "PyMuPDF (fitz) is not installed correctly.")

        # Ensure maximization happens after UI setup
        self.showMaximized()

    def _resolve_project_id(self):
        """Attempts to find the project_id using various DB methods."""
        # 1. Try standard method
        if hasattr(self.db, 'get_reading_details'):
            try:
                reading = self.db.get_reading_details(self.reading_id)
                if reading:
                    self.project_id = reading['project_id']
                    return
            except:
                pass

        # 2. Try QDA/Tracker direct SQL method
        if hasattr(self.db, 'tracker_cursor') and self.db.tracker_cursor:
            try:
                self.db.tracker_cursor.execute("SELECT project_id FROM readings WHERE id=?", (self.reading_id,))
                row = self.db.tracker_cursor.fetchone()
                if row:
                    self.project_id = row['project_id']
                    return
            except Exception as e:
                print(f"Error resolving project ID in QDA context: {e}")

    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(1)
        main_layout.addWidget(self.splitter)

        # --- Left Panel ---
        left_container = QFrame()
        left_container.setObjectName("LeftPanel")
        # Compact layout
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(8, 8, 8, 8)
        left_layout.setSpacing(8)

        # --- Page Controls (Top) ---
        page_ctrl_layout = QHBoxLayout()
        self.btn_prev = QPushButton("←")
        self.btn_prev.setFixedWidth(40)
        self.btn_next = QPushButton("→")
        self.btn_next.setFixedWidth(40)
        self.lbl_page = QLabel("Page: -/-")
        self.lbl_page.setAlignment(Qt.AlignCenter)
        self.lbl_page.setStyleSheet("font-weight: bold; color: #333;")

        self.btn_prev.clicked.connect(lambda: self.change_page(-1))
        self.btn_next.clicked.connect(lambda: self.change_page(1))

        page_ctrl_layout.addWidget(self.btn_prev)
        page_ctrl_layout.addWidget(self.lbl_page, 1)
        page_ctrl_layout.addWidget(self.btn_next)
        left_layout.addLayout(page_ctrl_layout)

        # --- Tab Widget for Categories / Nodes ---
        self.tabs = QTabWidget()
        left_layout.addWidget(self.tabs)

        # Tab 1: Current Page & Categories
        page_tab = QWidget()
        page_layout = QVBoxLayout(page_tab)
        page_layout.setContentsMargins(6, 6, 6, 6)
        page_layout.setSpacing(6)

        # Categories Area
        cat_header = QHBoxLayout()
        cat_header.addWidget(QLabel("CATEGORIES"))
        cat_header.addStretch()
        # Restore the + button properly
        btn_add_cat = QPushButton("+")
        btn_add_cat.setFixedSize(24, 24)
        btn_add_cat.setStyleSheet("padding: 0; font-size: 16px; font-weight: bold;")
        btn_add_cat.setToolTip("Add Category")
        btn_add_cat.clicked.connect(self._add_category)
        cat_header.addWidget(btn_add_cat)

        page_layout.addLayout(cat_header)

        self.cat_list = QListWidget()
        self.cat_list.setFixedHeight(100)  # Keep compact
        self.cat_list.itemDoubleClicked.connect(self._edit_category)
        self.cat_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.cat_list.customContextMenuRequested.connect(self._show_category_context_menu)
        page_layout.addWidget(self.cat_list)

        # Nodes on THIS Page
        page_layout.addWidget(QLabel("NODES (CURRENT PAGE)", objectName="Header"))
        self.node_list = QListWidget()
        self.node_list.itemClicked.connect(self.on_node_list_clicked)
        page_layout.addWidget(self.node_list, 1)  # Give this stretch

        self.tabs.addTab(page_tab, "Current")

        # Tab 2: ALL Nodes (Global Search)
        all_nodes_tab = QWidget()
        all_layout = QVBoxLayout(all_nodes_tab)
        all_layout.setContentsMargins(6, 6, 6, 6)
        all_layout.setSpacing(6)

        # Search Bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search all nodes...")
        self.search_input.textChanged.connect(self._filter_all_nodes)
        all_layout.addWidget(self.search_input)

        self.all_nodes_list = QListWidget()
        self.all_nodes_list.itemClicked.connect(self.on_all_nodes_clicked)
        all_layout.addWidget(self.all_nodes_list, 1)

        btn_refresh = QPushButton("Refresh List")
        btn_refresh.clicked.connect(self._load_all_nodes)
        all_layout.addWidget(btn_refresh)

        self.tabs.addTab(all_nodes_tab, "All Nodes")

        # Help Text
        help_lbl = QLabel("Shift+Drag to OCR Copy")
        help_lbl.setStyleSheet("color: #9CA3AF; font-size: 11px; font-style: italic;")
        help_lbl.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(help_lbl)

        # --- Right Panel: Graphics View ---
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.view.viewport().installEventFilter(self)

        self.splitter.addWidget(left_container)
        self.splitter.addWidget(self.view)
        self.splitter.setSizes([280, 1000])  # Tighter left panel

        # Initial Loads
        self.refresh_categories()
        self._load_all_nodes()

    # --- Category Management ---
    def refresh_categories(self):
        self.cat_list.clear()
        if not self.project_id:
            # Try one more time in case DB was slow to init
            self._resolve_project_id()
            if not self.project_id:
                return

        cats = self.db.get_pdf_node_categories(self.project_id)
        for c in cats:
            item = QListWidgetItem(c['name'])
            item.setData(Qt.UserRole, c['id'])
            item.setData(Qt.UserRole + 1, c['color_hex'])

            # Show color swatch
            pix = QPixmap(14, 14)
            pix.fill(QColor(c['color_hex']))
            item.setIcon(QIcon(pix))

            self.cat_list.addItem(item)

    def _add_category(self):
        if not self.project_id:
            QMessageBox.warning(self, "Error", "Project context missing. Cannot add category.")
            return

        name, ok = QInputDialog.getText(self, "New Category", "Name:")
        if ok and name:
            color = QColorDialog.getColor(Qt.white, self, "Choose Color")
            if color.isValid():
                self.db.add_pdf_node_category(self.project_id, name, color.name())
                self.refresh_categories()

    def _edit_category(self, item):
        cat_id = item.data(Qt.UserRole)
        old_name = item.text()
        old_color = item.data(Qt.UserRole + 1)

        # Custom dialog or simple inputs
        name, ok = QInputDialog.getText(self, "Edit Category", "Name:", text=old_name)
        if not ok: return

        color = QColorDialog.getColor(QColor(old_color), self, "Choose Color (Cancel to keep current)")
        new_color = color.name() if color.isValid() else old_color

        self.db.update_pdf_node_category(cat_id, name, new_color)
        self.refresh_categories()

        # --- FIX: Force repaint of all nodes to reflect new color immediately ---
        self.render_current_page()
        self._load_all_nodes()
        # --- END FIX ---

    def _show_category_context_menu(self, pos):
        item = self.cat_list.itemAt(pos)
        if not item: return

        menu = QMenu(self)
        edit_action = QAction("Edit Category", self)
        edit_action.triggered.connect(lambda: self._edit_category(item))
        menu.addAction(edit_action)

        del_action = QAction("Delete Category", self)
        del_action.triggered.connect(lambda: self._delete_category_item(item))
        menu.addAction(del_action)

        menu.exec(self.cat_list.mapToGlobal(pos))

    def _delete_category_item(self, item):
        cat_id = item.data(Qt.UserRole)
        if QMessageBox.question(self, "Delete", f"Delete category '{item.text()}'?") == QMessageBox.StandardButton.Yes:
            self.db.delete_pdf_node_category(cat_id)
            self.refresh_categories()
            self.render_current_page()
            self._load_all_nodes()

    # --- PDF & Node Logic ---

    def load_pdf(self):
        if not fitz: return
        try:
            self.pdf_doc = fitz.open(self.file_path)
            self.render_current_page()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load PDF: {e}")

    def change_page(self, delta):
        if not self.pdf_doc: return
        new_idx = self.current_page_idx + delta
        if 0 <= new_idx < len(self.pdf_doc):
            self.current_page_idx = new_idx
            self.render_current_page()

    def render_current_page(self):
        if not self.pdf_doc: return

        self.scene.clear()
        self.node_list.clear()

        self.lbl_page.setText(f"Page {self.current_page_idx + 1} / {len(self.pdf_doc)}")
        self.btn_prev.setEnabled(self.current_page_idx > 0)
        self.btn_next.setEnabled(self.current_page_idx < len(self.pdf_doc) - 1)

        page = self.pdf_doc.load_page(self.current_page_idx)
        mat = fitz.Matrix(self.zoom_level, self.zoom_level)
        pix = page.get_pixmap(matrix=mat)
        img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(img)

        self.pdf_item = QGraphicsPixmapItem(pixmap)
        self.scene.addItem(self.pdf_item)
        self.scene.setSceneRect(QRectF(pixmap.rect()))

        self.load_nodes_for_page()

    def load_nodes_for_page(self):
        nodes = self.db.get_pdf_nodes_for_page(self.attachment_id, self.current_page_idx)
        for node_data in nodes:
            node_item = PdfMarkerNode(node_data['x_pos'], node_data['y_pos'], 20, node_data, self)
            self.scene.addItem(node_item)

            label = node_data['label']
            if node_data.get('category_name'):
                label = f"({node_data['category_name']}) {label}"

            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, node_data['id'])

            # Add color icon to list item too
            color_hex = node_data.get('category_color') or node_data.get('color_hex') or '#FFFF00'
            pix = QPixmap(10, 10)
            pix.fill(QColor(color_hex))
            item.setIcon(QIcon(pix))

            self.node_list.addItem(item)

    def add_node_at(self, pos_scene):
        # Dialog
        dlg = QDialog(self)
        dlg.setWindowTitle("Add Node")
        layout = QFormLayout(dlg)

        name_edit = QLineEdit()
        layout.addRow("Label:", name_edit)

        cat_combo = QComboBox()
        cat_combo.addItem("None", None)
        cats = self.db.get_pdf_node_categories(self.project_id) if self.project_id else []
        for c in cats:
            cat_combo.addItem(c['name'], c['id'])
        layout.addRow("Category:", cat_combo)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(dlg.accept)
        btn_box.rejected.connect(dlg.reject)
        layout.addWidget(btn_box)

        if dlg.exec() == QDialog.Accepted:
            label = name_edit.text().strip() or "New Node"
            cat_id = cat_combo.currentData()

            self.db.add_pdf_node(
                self.reading_id,
                self.attachment_id,
                self.current_page_idx,
                pos_scene.x(),
                pos_scene.y(),
                "Note",
                "#FFFF00",
                label,
                "",
                cat_id
            )
            self.render_current_page()
            self._load_all_nodes()

    def update_node_position(self, node_id, x, y):
        self.db.update_pdf_node(node_id, x_pos=x, y_pos=y)

    def edit_node_dialog(self, node_id):
        details = self.db.get_pdf_node_details(node_id)
        if not details: return

        dlg = QDialog(self)
        dlg.setWindowTitle("Edit Node")
        layout = QFormLayout(dlg)

        name_edit = QLineEdit(details['label'])
        layout.addRow("Label:", name_edit)

        cat_combo = QComboBox()
        cat_combo.addItem("None", None)
        cats = self.db.get_pdf_node_categories(self.project_id) if self.project_id else []

        current_cat_idx = 0
        for i, c in enumerate(cats):
            cat_combo.addItem(c['name'], c['id'])
            if c['id'] == details['category_id']:
                current_cat_idx = i + 1

        cat_combo.setCurrentIndex(current_cat_idx)
        layout.addRow("Category:", cat_combo)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(dlg.accept)
        btn_box.rejected.connect(dlg.reject)
        layout.addWidget(btn_box)

        if dlg.exec() == QDialog.Accepted:
            self.db.update_pdf_node(
                node_id,
                label=name_edit.text(),
                category_id=cat_combo.currentData()
            )
            self.render_current_page()
            self._load_all_nodes()

    def delete_node(self, node_id):
        if QMessageBox.question(self, "Delete", "Delete this node?") == QMessageBox.StandardButton.Yes:
            self.db.delete_pdf_node(node_id)
            self.render_current_page()
            self._load_all_nodes()

    def jump_to_node(self, node_id):
        details = self.db.get_pdf_node_details(node_id)
        if not details: return
        page_idx = details['page_number']
        if page_idx != self.current_page_idx:
            self.current_page_idx = page_idx
            self.render_current_page()
        self.view.centerOn(details['x_pos'], details['y_pos'])

        # Highlight in list
        for i in range(self.node_list.count()):
            item = self.node_list.item(i)
            if item.data(Qt.UserRole) == node_id:
                self.node_list.setCurrentItem(item)
                break

    def on_node_list_clicked(self, item):
        node_id = item.data(Qt.UserRole)
        self.jump_to_node(node_id)

    # --- Global Node List Methods ---
    def _load_all_nodes(self):
        self.all_nodes_list.clear()

        # --- FIX: Handle QDA vs Main App DB differences ---
        nodes = []
        if hasattr(self.db, 'get_all_pdf_nodes_for_attachment'):
            nodes = self.db.get_all_pdf_nodes_for_attachment(self.attachment_id)
        elif hasattr(self.db, 'get_tracker_pdf_nodes'):
            # QDA Tool: Get ALL nodes for reading, filter by attachment ID
            all_nodes = self.db.get_tracker_pdf_nodes(self.reading_id)
            # Filter
            nodes = [n for n in all_nodes if n['attachment_id'] == self.attachment_id]
        # --- END FIX ---

        self._display_all_nodes(nodes)

    def _display_all_nodes(self, nodes):
        self.all_nodes_list.clear()
        for n in nodes:
            label = n['label']
            if n.get('category_name'):
                label = f"({n['category_name']}) {label}"

            # Add Page Info
            label = f"Pg {n['page_number'] + 1}: {label}"

            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, n['id'])

            # Color code item
            color_hex = n.get('category_color') or n.get('color_hex') or '#FFFF00'
            pix = QPixmap(10, 10)
            pix.fill(QColor(color_hex))
            item.setIcon(QIcon(pix))

            self.all_nodes_list.addItem(item)

    def _filter_all_nodes(self, text):
        text = text.lower().strip()
        for i in range(self.all_nodes_list.count()):
            item = self.all_nodes_list.item(i)
            if not text or text in item.text().lower():
                item.setHidden(False)
            else:
                item.setHidden(True)

    def on_all_nodes_clicked(self, item):
        node_id = item.data(Qt.UserRole)
        self.jump_to_node(node_id)

    # --- Event Filter (Marquee & Context Menu) ---
    def eventFilter(self, source, event):
        if source is self.view.viewport():
            if event.type() == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton and (
                        event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
                    self._is_marquee_mode = True
                    self._marquee_start = self.view.mapToScene(event.pos())
                    self._marquee_rect_item = QGraphicsRectItem()
                    self._marquee_rect_item.setPen(QPen(Qt.GlobalColor.blue, 1, Qt.PenStyle.DashLine))
                    self.scene.addItem(self._marquee_rect_item)
                    return True
            elif event.type() == QEvent.Type.MouseMove:
                if self._is_marquee_mode and self._marquee_start:
                    current_pos = self.view.mapToScene(event.pos())
                    rect = QRectF(self._marquee_start, current_pos).normalized()
                    self._marquee_rect_item.setRect(rect)
                    return True
            elif event.type() == QEvent.Type.MouseButtonRelease:
                if self._is_marquee_mode and self._marquee_start:
                    self._is_marquee_mode = False
                    rect_scene = self._marquee_rect_item.rect()
                    self.scene.removeItem(self._marquee_rect_item)
                    self._marquee_rect_item = None
                    self._extract_text_from_rect(rect_scene)
                    return True
            elif event.type() == QEvent.Type.ContextMenu:
                pos = event.pos()
                scene_pos = self.view.mapToScene(pos)
                items = self.scene.items(scene_pos)
                if not any(isinstance(i, PdfMarkerNode) for i in items):
                    menu = QMenu()
                    add_action = menu.addAction("Add Node Here")
                    action = menu.exec(event.globalPos())
                    if action == add_action:
                        self.add_node_at(scene_pos)
                    return True
        return super().eventFilter(source, event)

    def _extract_text_from_rect(self, rect_scene):
        if not self.pdf_doc: return
        x0 = rect_scene.left() / self.zoom_level
        y0 = rect_scene.top() / self.zoom_level
        x1 = rect_scene.right() / self.zoom_level
        y1 = rect_scene.bottom() / self.zoom_level
        pdf_rect = fitz.Rect(x0, y0, x1, y1)
        page = self.pdf_doc.load_page(self.current_page_idx)
        text = page.get_text("text", clip=pdf_rect)
        if text.strip():
            QApplication.clipboard().setText(text.strip())
            print(f"Copied: {text.strip()[:20]}...")
        else:
            print("No text found in selection.")