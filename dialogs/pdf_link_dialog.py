# dialogs/pdf_link_dialog.py
import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QListWidget, QListWidgetItem, QLineEdit, QLabel, QPushButton,
    QDialogButtonBox, QSplitter, QWidget
)
from PySide6.QtCore import Qt, Slot


class PdfLinkDialog(QDialog):
    """
    A dialog to select a PDF Node to link to.
    Structure:
      - Top: Search Bar
      - Splitter:
          - Left: Tree (Project -> Reading)
          - Right: List (Nodes for selected Reading)
    """

    def __init__(self, db, current_project_id=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.current_project_id = current_project_id
        self.selected_node_id = None
        self.selected_node_label = None

        self.setWindowTitle("Link to PDF Node")
        self.resize(800, 600)

        main_layout = QVBoxLayout(self)

        # --- Search Bar ---
        search_layout = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search nodes by name...")
        self.search_edit.textChanged.connect(self._on_search_text_changed)
        search_layout.addWidget(QLabel("Search:"))
        search_layout.addWidget(self.search_edit)
        main_layout.addLayout(search_layout)

        # --- Splitter ---
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter, 1)

        # Left: Navigation Tree
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(QLabel("<b>Projects & Readings</b>"))
        self.nav_tree = QTreeWidget()
        self.nav_tree.setHeaderHidden(True)
        self.nav_tree.itemClicked.connect(self._on_tree_item_clicked)
        left_layout.addWidget(self.nav_tree)
        splitter.addWidget(left_widget)

        # Right: Node List
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(QLabel("<b>Nodes</b>"))
        self.node_list = QListWidget()
        self.node_list.itemDoubleClicked.connect(self._on_node_double_clicked)
        self.node_list.itemClicked.connect(self._update_buttons)
        right_layout.addWidget(self.node_list)
        splitter.addWidget(right_widget)

        splitter.setSizes([300, 500])

        # --- Buttons ---
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.button(QDialogButtonBox.Ok).setEnabled(False)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

        self._load_tree()

    def _load_tree(self):
        """Loads Projects and Readings into the tree."""
        self.nav_tree.clear()
        self.db.cursor.execute("SELECT * FROM items WHERE type='project' ORDER BY name")
        all_projects = self.db._map_rows(self.db.cursor.fetchall())

        for proj in all_projects:
            p_item = QTreeWidgetItem([proj['name']])
            p_item.setData(0, Qt.ItemDataRole.UserRole, "project")
            p_item.setData(0, Qt.ItemDataRole.UserRole + 1, proj['id'])
            self.nav_tree.addTopLevelItem(p_item)

            readings = self.db.get_readings(proj['id'])
            for r in readings:
                r_name = r['nickname'] if r['nickname'] else r['title']
                r_item = QTreeWidgetItem([r_name])
                r_item.setData(0, Qt.ItemDataRole.UserRole, "reading")
                r_item.setData(0, Qt.ItemDataRole.UserRole + 1, r['id'])
                p_item.addChild(r_item)

            if self.current_project_id and proj['id'] == self.current_project_id:
                p_item.setExpanded(True)
                self.nav_tree.setCurrentItem(p_item)

    def _on_tree_item_clicked(self, item, column):
        item_type = item.data(0, Qt.ItemDataRole.UserRole)
        item_id = item.data(0, Qt.ItemDataRole.UserRole + 1)

        if item_type == "reading":
            self._load_nodes_for_reading(item_id)
        else:
            self.node_list.clear()
            self._update_buttons()

    def _load_nodes_for_reading(self, reading_id):
        self.node_list.clear()
        # Use new mixin method that returns category data
        nodes = self.db.get_all_pdf_nodes_for_reading(reading_id)

        for node in nodes:
            # Format: (Category) Node Name (Pg X)
            label = node['label']
            if node.get('category_name'):
                label = f"({node['category_name']}) {label}"

            label += f" (Pg {node['page_number'] + 1})"

            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, node['id'])
            item.setData(Qt.ItemDataRole.UserRole + 1, node['label'])
            self.node_list.addItem(item)

        self._update_buttons()

    def _on_search_text_changed(self, text):
        text = text.strip().lower()
        if not text: return

        self.node_list.clear()
        self.nav_tree.clearSelection()

        sql = """
            SELECT n.id, n.label, n.page_number, r.nickname, r.title, i.name as project_name, c.name as category_name
            FROM pdf_nodes n
            JOIN readings r ON n.reading_id = r.id
            JOIN items i ON r.project_id = i.id
            LEFT JOIN pdf_node_categories c ON n.category_id = c.id
            WHERE lower(n.label) LIKE ? OR lower(n.description) LIKE ?
            ORDER BY i.name, r.display_order, n.page_number
            LIMIT 50
        """
        self.db.cursor.execute(sql, (f"%{text}%", f"%{text}%"))
        results = self.db._map_rows(self.db.cursor.fetchall())

        for row in results:
            reading_name = row['nickname'] if row['nickname'] else row['title']

            label_part = row['label']
            if row.get('category_name'):
                label_part = f"({row['category_name']}) {label_part}"

            display = f"{row['project_name']} > {reading_name} > {label_part} (Pg {row['page_number'] + 1})"
            item = QListWidgetItem(display)
            item.setData(Qt.ItemDataRole.UserRole, row['id'])
            item.setData(Qt.ItemDataRole.UserRole + 1, row['label'])
            self.node_list.addItem(item)

    def _update_buttons(self):
        has_selection = self.node_list.currentItem() is not None
        self.button_box.button(QDialogButtonBox.Ok).setEnabled(has_selection)

    def _on_node_double_clicked(self, item):
        self.accept()

    def accept(self):
        item = self.node_list.currentItem()
        if item:
            self.selected_node_id = item.data(Qt.ItemDataRole.UserRole)
            self.selected_node_label = item.data(Qt.ItemDataRole.UserRole + 1)
            super().accept()