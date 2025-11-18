# prospectcreek/3rdeditionreadingtracker/3rdEditionReadingTracker-f9372c7f456315b9a3fa82060c18255c8574e1ea/tabs/parts_order_relation_tab.py

import sys
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QComboBox,
    QLabel, QMessageBox, QFrame, QHBoxLayout,
    QPushButton, QScrollArea, QTreeWidget, QTreeWidgetItemIterator,
    QGridLayout, QSizePolicy, QTreeWidgetItem, QTextEdit,
    QTextBrowser, QHeaderView, QDialog
)
from PySide6.QtCore import Qt, Slot, QSize, QUrl, Signal, QPoint
from PySide6.QtGui import QDesktopServices, QFont, QAction, QColor

# --- NEW: Import new dialog ---
try:
    from dialogs.add_part_dialog import AddPartDialog
except ImportError:
    print("Error: Could not import AddPartDialog")
    AddPartDialog = None

# --- NEW: Import ReorderDialog ---
try:
    from dialogs.reorder_dialog import ReorderDialog
except ImportError:
    print("Error: Could not import ReorderDialog")
    ReorderDialog = None


class PartsOrderRelationTab(QWidget):
    """
    PySide6 implementation of the Parts: Order and Relation tab.
    Uses a TreeWidget view and a pop-up dialog for editing.
    """

    def __init__(self, db, project_id, reading_id, parent=None):
        super().__init__(parent)
        self.db = db
        self.project_id = project_id
        self.reading_id = reading_id

        self._is_loaded = False

        # --- Main layout ---
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(4)

        # --- NEW: Add Instruction Label ---
        self.prompt_label = QLabel("")
        self.prompt_label.setWordWrap(True)
        self.prompt_label.setStyleSheet("font-style: italic; color: #555; padding: 4px;") # Add padding
        self.prompt_label.setVisible(False) # Hidden by default
        main_layout.addWidget(self.prompt_label)
        # --- END NEW ---

        # --- Button bar ---
        button_bar = QFrame()
        button_layout = QHBoxLayout(button_bar)
        button_layout.setContentsMargins(0, 0, 0, 0)

        self.btn_add = QPushButton("Add/Edit Part Details")
        self.btn_add.setToolTip("Select an outline item in the dialog to add or edit its details.")

        button_layout.addWidget(self.btn_add)
        button_layout.addStretch()
        main_layout.addWidget(button_bar)

        # --- Tree widget (the new main view) ---
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(["Part Name", "Function", "Relation", "Dependency"])

        header = self.tree_widget.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

        self.tree_widget.setColumnWidth(0, 200)

        self.tree_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        main_layout.addWidget(self.tree_widget)

        # --- Connections ---
        self.btn_add.clicked.connect(self._add_item)  # "Add" button opens the dialog
        self.tree_widget.itemDoubleClicked.connect(self._edit_item)
        self.tree_widget.customContextMenuRequested.connect(self.show_context_menu)

        self._is_loaded = True

    def update_instructions(self, instructions_data, key):
        """Sets the instruction text for this tab."""
        text = instructions_data.get(key, "")
        self.prompt_label.setText(text)
        self.prompt_label.setVisible(bool(text))

    def load_data(self):
        """Called by ReadingNotesTab to load all data."""
        if not self._is_loaded:
            return
        self.load_parts()

    def load_parts(self):
        """Reloads all structural parts from the database into the tree."""
        self.tree_widget.clear()
        try:
            # This DB function already returns only structural parts
            parts = self.db.get_parts_data(self.reading_id)

            if not parts:
                placeholder_item = QTreeWidgetItem(self.tree_widget, ["No structural parts defined yet."])
                placeholder_item.setFlags(placeholder_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
                placeholder_item.setForeground(0, QColor("#888888"))
                font = placeholder_item.font(0)
                font.setItalic(True)
                placeholder_item.setFont(0, font)
                return

            for part_data in parts:
                item = QTreeWidgetItem(self.tree_widget)
                item.setText(0, part_data.get("section_title", "N/A"))
                item.setText(1, part_data.get("part_function_text_plain", ""))
                item.setText(2, part_data.get("part_relation_text_plain", ""))
                item.setText(3, part_data.get("part_dependency_text_plain", ""))
                item.setData(0, Qt.ItemDataRole.UserRole, part_data["id"])  # Store outline_id
                item.setExpanded(True)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load parts: {e}")

    def _get_outline_items(self, parent_id=None):
        """Recursively fetches outline items to build a nested list for the dialog."""
        items = self.db.get_reading_outline(self.reading_id, parent_id=parent_id)
        for item in items:
            children = self._get_outline_items(parent_id=item['id'])
            if children:
                item['children'] = children
        return items

    def _get_driving_questions(self):
        """Fetches all driving questions for this reading."""
        return self.db.get_driving_questions(self.reading_id, parent_id=True)

    def show_context_menu(self, position):
        menu = QMenu(self)
        item = self.tree_widget.itemAt(position)

        menu.addAction("Add/Edit Part Details...", self._add_item)

        if item and item.data(0, Qt.ItemDataRole.UserRole) is not None:
            menu.addAction("Edit This Part...", self._edit_item)
            menu.addAction("Remove Part Details (Clear)", self._delete_item)
            menu.addSeparator()

        if self.tree_widget.topLevelItemCount() > 1 and ReorderDialog:
            reorder_action = QAction("Reorder Parts...", self._reorder_items)
            menu.addAction(reorder_action)

        menu.exec(self.tree_widget.viewport().mapToGlobal(position))

    @Slot()
    def _handle_save(self, data, outline_id):
        """Central logic for saving part details."""
        try:
            # We are *always* updating, as the part is just an outline item
            self.db.save_part_data(self.reading_id, outline_id, data)
            self.load_parts()  # Refresh tree
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save part details: {e}")

    @Slot()
    def _add_item(self):
        """
        Opens the dialog to add details to an *existing* outline item,
        turning it into a "Part".
        """
        if not AddPartDialog:
            QMessageBox.critical(self, "Error", "Add Part dialog not loaded.")
            return

        outline_items = self._get_outline_items()
        driving_questions = self._get_driving_questions()

        dialog = AddPartDialog(
            db_manager=self.db,
            reading_id=self.reading_id,
            outline_items=outline_items,
            driving_questions=driving_questions,
            parent=self
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if data:
                self._handle_save(data, data['outline_id'])

    @Slot()
    def _edit_item(self):
        """Edits the selected part."""
        item = self.tree_widget.currentItem()
        if not item or item.data(0, Qt.ItemDataRole.UserRole) is None:
            # If no item selected, just open the "Add" dialog
            self._add_item()
            return

        outline_id = item.data(0, Qt.ItemDataRole.UserRole)
        outline_items = self._get_outline_items()
        driving_questions = self._get_driving_questions()

        # Get the full data for this part
        current_data = self.db.get_part_data(outline_id)

        if not current_data:
            QMessageBox.critical(self, "Error", "Could not find part details.")
            return

        dialog = AddPartDialog(
            db_manager=self.db,
            reading_id=self.reading_id,
            outline_items=outline_items,
            driving_questions=driving_questions,
            current_data=current_data,
            parent=self
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if data:
                self._handle_save(data, data['outline_id'])

    @Slot()
    def _delete_item(self):
        """
        Deletes the *details* for a part, reverting it to a simple outline item.
        It does not delete the outline item itself.
        """
        item = self.tree_widget.currentItem()
        if not item or item.data(0, Qt.ItemDataRole.UserRole) is None:
            return

        outline_id = item.data(0, Qt.ItemDataRole.UserRole)
        reply = QMessageBox.question(
            self, "Remove Part Details",
            f"Are you sure you want to remove all part details from '{item.text(0)}'?\n\nThis will not delete the outline section, only its part data.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Create an empty data dict to "clear" the part
                empty_data = {
                    'is_structural': False,  # Set to False
                    'driving_question_id': None,
                    'function_text': "",
                    'relation_text': "",
                    'dependency_text': ""
                }
                self.db.save_part_data(self.reading_id, outline_id, empty_data)
                self.load_parts()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not remove part details: {e}")

    @Slot()
    def _reorder_items(self):
        """
        Reorders the *structural parts* in the view.
        This reorders the underlying *outline items*.
        """
        if not ReorderDialog:
            QMessageBox.critical(self, "Error", "Reorder dialog is not available.")
            return

        try:
            # We must reorder based on outline hierarchy.
            # For now, we only support reordering root-level parts.
            parts = self.db.get_parts_data(self.reading_id)
            root_parts = [p for p in parts if p.get('parent_id') is None]

            if len(root_parts) < 2:
                QMessageBox.information(self, "Reorder", "Not enough root-level parts to reorder.")
                return

            items_to_reorder = [(q.get('section_title', '...'), q['id']) for q in root_parts]
            dialog = ReorderDialog(items_to_reorder, self)

            if dialog.exec() == QDialog.DialogCode.Accepted:
                ordered_ids = dialog.ordered_db_ids
                # This will reorder the outline items, which in turn
                # reorders the parts list on next load.
                self.db.update_outline_section_order(ordered_ids)
                self.load_parts()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not reorder parts: {e}")

    def save_data(self):
        """
        Public save method for autosave.
        In this new design, saving is modal (only via dialog),
        so this method does nothing.
        """
        pass