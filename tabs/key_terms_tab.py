# tabs/key_terms_tab.py
import sys
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTreeWidget,
    QTreeWidgetItem, QMenu, QMessageBox, QDialog, QLabel, QFrame,
    QHeaderView
)
from PySide6.QtCore import Qt, Signal, QPoint, Slot
from PySide6.QtGui import QAction, QFont, QColor

try:
    from dialogs.add_key_term_dialog import AddKeyTermDialog
except ImportError:
    print("Error: Could not import AddKeyTermDialog")
    AddKeyTermDialog = None

try:
    from dialogs.reorder_dialog import ReorderDialog
except ImportError:
    print("Error: Could not import ReorderDialog")
    ReorderDialog = None


class KeyTermsTab(QWidget):
    """
    Widget for managing "Key Terms" for a reading.
    """

    def __init__(self, db, project_id, reading_id, parent=None):
        super().__init__(parent)
        self.db = db
        self.reading_id = reading_id
        self.project_id = project_id  # Needed for dialog

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(4)

        self.prompt_label = QLabel("")
        self.prompt_label.setWordWrap(True)
        self.prompt_label.setStyleSheet("font-style: italic; color: #555;")
        self.prompt_label.setVisible(False)
        main_layout.addWidget(self.prompt_label)

        # Button bar
        button_bar = QFrame()
        button_layout = QHBoxLayout(button_bar)
        button_layout.setContentsMargins(0, 0, 0, 0)

        self.btn_add = QPushButton("Add Key Term")
        button_layout.addWidget(self.btn_add)
        button_layout.addStretch()
        main_layout.addWidget(button_bar)

        # Tree widget
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(["Term", "My Definition", "Role", "Links"])
        self.tree_widget.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.tree_widget.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tree_widget.header().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.tree_widget.header().setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        self.tree_widget.setColumnWidth(0, 150)
        self.tree_widget.setColumnWidth(2, 120)
        self.tree_widget.setColumnWidth(3, 100)

        self.tree_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        main_layout.addWidget(self.tree_widget)

        # --- Connections ---
        self.btn_add.clicked.connect(self._add_item)
        self.tree_widget.itemDoubleClicked.connect(self._edit_item)
        self.tree_widget.customContextMenuRequested.connect(self.show_context_menu)

        self.load_key_terms()

    def update_instructions(self, instructions_data, key):
        text = instructions_data.get(key, "")
        self.prompt_label.setText(text)
        self.prompt_label.setVisible(bool(text))

    def load_key_terms(self):
        self.tree_widget.clear()
        try:
            terms = self.db.get_reading_key_terms(self.reading_id)
            for term_data in terms:
                self._add_term_to_tree(self.tree_widget, term_data)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load key terms: {e}")

    def _add_term_to_tree(self, parent_widget, term_data):
        term_text = term_data.get("term", "N/A")

        # Add indicator if linked to PDF
        if term_data.get('pdf_node_id'):
            term_text += " (PDF Link)"

        item = QTreeWidgetItem(parent_widget)
        item.setText(0, term_text)
        item.setText(1, term_data.get("definition", ""))
        item.setText(2, term_data.get("role", ""))
        item.setText(3, term_data.get("synthesis_tags", ""))

        item.setData(0, Qt.ItemDataRole.UserRole, term_data["id"])
        item.setData(0, Qt.ItemDataRole.UserRole + 1, dict(term_data))  # Store full data
        item.setExpanded(True)

    def _get_outline_items(self, parent_id=None):
        items = self.db.get_reading_outline(self.reading_id, parent_id=parent_id)
        for item in items:
            children = self._get_outline_items(parent_id=item['id'])
            if children:
                item['children'] = children
        return items

    def show_context_menu(self, position):
        menu = QMenu(self)
        item = self.tree_widget.itemAt(position)
        menu.addAction(self.btn_add.text(), self._add_item)

        if item:
            menu.addAction("Edit Key Term...", self._edit_item)
            menu.addAction("Delete Key Term", self._delete_item)

            # PDF Link
            data = item.data(0, Qt.ItemDataRole.UserRole + 1)
            if data and data.get('pdf_node_id'):
                menu.addSeparator()
                pdf_action = QAction("View Linked PDF Node", self)
                pdf_action.triggered.connect(lambda: self._trigger_pdf_jump(data['pdf_node_id']))
                menu.addAction(pdf_action)

            menu.addSeparator()

        if self.tree_widget.topLevelItemCount() > 1 and ReorderDialog:
            reorder_action = QAction("Reorder Items...", self)
            reorder_action.triggered.connect(self._reorder_items)
            menu.addAction(reorder_action)

        menu.exec(self.tree_widget.viewport().mapToGlobal(position))

    def _trigger_pdf_jump(self, pdf_node_id):
        parent = self.parent()
        while parent:
            if parent.metaObject().className() == 'ProjectDashboardWidget':
                if hasattr(parent, '_jump_to_pdf_node'):
                    parent._jump_to_pdf_node(pdf_node_id)
                break
            parent = parent.parent()

    @Slot()
    def _handle_save(self, data, term_id=None):
        try:
            item_id = None
            if term_id:
                self.db.update_reading_key_term(term_id, data)
                item_id = term_id
            else:
                item_id = self.db.add_reading_key_term(self.reading_id, data)

            if not item_id: raise Exception("Failed to get item ID.")

            # --- VIRTUAL ANCHOR FIX (Handled in Mixin now mostly, but ensure consistency) ---
            # Mixin handles anchor update. We just reload tree.
            self.load_key_terms()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save key term: {e}")

    @Slot()
    def _add_item(self):
        if not AddKeyTermDialog: return
        dialog = AddKeyTermDialog(self.db, self.project_id, self.reading_id, self._get_outline_items(), parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if not data.get('term'): return
            self._handle_save(data, term_id=None)

    @Slot()
    def _edit_item(self):
        item = self.tree_widget.currentItem()
        if not item: return
        term_id = item.data(0, Qt.ItemDataRole.UserRole)
        current_data = self.db.get_reading_key_term_details(term_id)
        if not current_data: return

        dialog = AddKeyTermDialog(self.db, self.project_id, self.reading_id, self._get_outline_items(),
                                  current_data=current_data, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if not data.get('term'): return
            self._handle_save(data, term_id=term_id)

    @Slot()
    def _delete_item(self):
        item = self.tree_widget.currentItem()
        if not item: return
        term_id = item.data(0, Qt.ItemDataRole.UserRole)
        if QMessageBox.question(self, "Delete", "Delete this term?") == QMessageBox.StandardButton.Yes:
            self.db.delete_reading_key_term(term_id)
            self.load_key_terms()

    @Slot()
    def _reorder_items(self):
        if not ReorderDialog: return
        siblings = self.db.get_reading_key_terms(self.reading_id)
        if len(siblings) < 2: return
        items_to_reorder = [(q.get('term', '...'), q['id']) for q in siblings]
        dialog = ReorderDialog(items_to_reorder, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.db.update_reading_key_term_order(dialog.ordered_db_ids)
            self.load_key_terms()