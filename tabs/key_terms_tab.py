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
    (Based on tabs/driving_question_tab.py and screenshot image_26e84d.png)
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

        # --- NEW: Add Instruction Label ---
        self.prompt_label = QLabel("")
        self.prompt_label.setWordWrap(True)
        self.prompt_label.setStyleSheet("font-style: italic; color: #555;")
        self.prompt_label.setVisible(False) # Hidden by default
        main_layout.addWidget(self.prompt_label)
        # --- END NEW ---

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
        # --- NEW: Set columns based on screenshot ---
        self.tree_widget.setHeaderLabels(["Term", "My Definition", "Role", "Links"])
        self.tree_widget.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.tree_widget.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tree_widget.header().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.tree_widget.header().setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        self.tree_widget.setColumnWidth(0, 150)
        self.tree_widget.setColumnWidth(2, 120)
        self.tree_widget.setColumnWidth(3, 100)
        # --- END NEW ---

        self.tree_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        main_layout.addWidget(self.tree_widget)

        # --- Connections ---
        self.btn_add.clicked.connect(self._add_item)

        self.tree_widget.itemDoubleClicked.connect(self._edit_item)
        self.tree_widget.customContextMenuRequested.connect(self.show_context_menu)

        self.load_key_terms()

    def update_instructions(self, instructions_data, key):
        """Sets the instruction text for this tab."""
        text = instructions_data.get(key, "")
        self.prompt_label.setText(text)
        self.prompt_label.setVisible(bool(text))

    def load_key_terms(self):
        """Reloads all key terms from the database into the tree."""
        self.tree_widget.clear()
        try:
            terms = self.db.get_reading_key_terms(self.reading_id)
            for term_data in terms:
                self._add_term_to_tree(self.tree_widget, term_data)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load key terms: {e}")

    def _add_term_to_tree(self, parent_widget, term_data):
        """Helper to build the tree item with multiple columns."""

        item = QTreeWidgetItem(parent_widget)
        item.setText(0, term_data.get("term", "N/A"))
        item.setText(1, term_data.get("definition", ""))
        item.setText(2, term_data.get("role", ""))
        item.setText(3, term_data.get("synthesis_tags", ""))

        item.setData(0, Qt.ItemDataRole.UserRole, term_data["id"])

        item.setExpanded(True)

    def _get_outline_items(self, parent_id=None):
        """Recursively fetches outline items to build a nested list for the dialog."""
        items = self.db.get_reading_outline(self.reading_id, parent_id=parent_id)
        for item in items:
            # item is already a dict
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
            menu.addSeparator()

        if self.tree_widget.topLevelItemCount() > 1 and ReorderDialog:
            reorder_action = QAction("Reorder Items...", self)
            reorder_action.triggered.connect(self._reorder_items)
            menu.addAction(reorder_action)

        menu.exec(self.tree_widget.viewport().mapToGlobal(position))

    @Slot()
    def _handle_save(self, data, term_id=None):
        """Central logic for saving a key term (add or edit)."""
        try:
            item_id = None
            if term_id:
                # Update existing
                self.db.update_reading_key_term(term_id, data)
                item_id = term_id
            else:
                # Add new
                item_id = self.db.add_reading_key_term(self.reading_id, data)

            if not item_id:
                raise Exception("Failed to get item ID after save/update.")

            # --- VIRTUAL ANCHOR FIX ---
            # 1. Clear all existing virtual anchors for this item
            self.db.delete_anchors_by_item_link_id(item_id)

            # 2. Add new ones based on the tags
            tags_text = data.get("synthesis_tags", "")
            if tags_text:
                tag_names = [tag.strip() for tag in tags_text.split(',') if tag.strip()]
                summary_text = f"Key Term: {data.get('term', '')[:50]}..."

                for tag_name in tag_names:
                    tag_data = self.db.get_or_create_tag(tag_name, self.project_id)
                    if tag_data:
                        self.db.create_anchor(
                            project_id=self.project_id,
                            reading_id=self.reading_id,
                            outline_id=data.get("outline_id"),
                            tag_id=tag_data['id'],
                            selected_text=summary_text,
                            comment=f"Linked to Key Term ID {item_id}",
                            unique_doc_id=f"term-{item_id}-{tag_data['id']}",
                            item_link_id=item_id
                        )
            # --- END VIRTUAL ANCHOR FIX ---

            self.load_key_terms()  # Refresh tree
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save key term: {e}")
            import traceback
            traceback.print_exc()

    @Slot()
    def _add_item(self):
        """Adds a new root-level key term."""
        if not AddKeyTermDialog:
            QMessageBox.critical(self, "Error", "Add Key Term dialog not loaded.")
            return

        outline_items = self._get_outline_items()

        dialog = AddKeyTermDialog(
            db_manager=self.db,
            project_id=self.project_id,
            reading_id=self.reading_id,
            outline_items=outline_items,
            parent=self
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if not data.get('term'):
                QMessageBox.warning(self, "Term Required", "The 'Term' field cannot be empty.")
                return
            self._handle_save(data, term_id=None)

    @Slot()
    def _edit_item(self):
        """Edits the selected key term."""
        item = self.tree_widget.currentItem()
        if not item:
            return

        term_id = item.data(0, Qt.ItemDataRole.UserRole)
        outline_items = self._get_outline_items()
        current_data = self.db.get_reading_key_term_details(term_id)

        if not current_data:
            QMessageBox.critical(self, "Error", "Could not find key term details.")
            return

        dialog = AddKeyTermDialog(
            db_manager=self.db,
            project_id=self.project_id,
            reading_id=self.reading_id,
            outline_items=outline_items,
            current_data=current_data,
            parent=self
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if not data.get('term'):
                QMessageBox.warning(self, "Term Required", "The 'Term' field cannot be empty.")
                return
            self._handle_save(data, term_id=term_id)

    @Slot()
    def _delete_item(self):
        """Deletes the selected key term."""
        item = self.tree_widget.currentItem()
        if not item:
            return

        term_id = item.data(0, Qt.ItemDataRole.UserRole)
        reply = QMessageBox.question(
            self, "Delete Key Term",
            f"Are you sure you want to delete this term: '{item.text(0)}'?\n\nThis will also delete any linked synthesis tags.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Cascade delete will handle the linked anchors
                self.db.delete_reading_key_term(term_id)
                self.load_key_terms()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not delete key term: {e}")

    @Slot()
    def _reorder_items(self):
        """Opens the full reorder dialog."""
        if not ReorderDialog:
            QMessageBox.critical(self, "Error", "Reorder dialog is not available.")
            return

        try:
            siblings = self.db.get_reading_key_terms(self.reading_id)
            if len(siblings) < 2:
                QMessageBox.information(self, "Reorder", "Not enough items to reorder.")
                return

            items_to_reorder = [(q.get('term', '...'), q['id']) for q in siblings]
            dialog = ReorderDialog(items_to_reorder, self)

            if dialog.exec() == QDialog.DialogCode.Accepted:
                ordered_ids = dialog.ordered_db_ids
                self.db.update_reading_key_term_order(ordered_ids)
                self.load_key_terms()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not reorder key terms: {e}")