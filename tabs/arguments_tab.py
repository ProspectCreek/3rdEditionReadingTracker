# tabs/arguments_tab.py
import sys
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTreeWidget,
    QTreeWidgetItem, QMenu, QMessageBox, QDialog, QLabel, QFrame,
    QHeaderView
)
from PySide6.QtCore import Qt, Signal, QPoint, Slot
from PySide6.QtGui import QAction, QFont, QColor

try:
    from dialogs.add_argument_dialog import AddArgumentDialog
except ImportError:
    print("Error: Could not import AddArgumentDialog")
    AddArgumentDialog = None

try:
    from dialogs.reorder_dialog import ReorderDialog
except ImportError:
    print("Error: Could not import ReorderDialog")
    ReorderDialog = None


class ArgumentsTab(QWidget):
    """
    Widget for managing "Arguments" for a reading.
    (Based on tabs/key_terms_tab.py and screenshot image_27d567.png)
    """

    def __init__(self, db, project_id, reading_id, parent=None):
        super().__init__(parent)
        self.db = db
        self.reading_id = reading_id
        self.project_id = project_id
        self._block_check_signals = False

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(4)

        # Button bar
        button_bar = QFrame()
        button_layout = QHBoxLayout(button_bar)
        button_layout.setContentsMargins(0, 0, 0, 0)

        self.btn_add = QPushButton("Add Argument")
        self.btn_edit = QPushButton("Edit")
        self.btn_delete = QPushButton("Delete")
        self.btn_move_up = QPushButton("Move Up")
        self.btn_move_down = QPushButton("Move Down")

        button_layout.addWidget(self.btn_add)
        button_layout.addWidget(self.btn_edit)
        button_layout.addWidget(self.btn_delete)
        button_layout.addStretch()
        button_layout.addWidget(self.btn_move_up)
        button_layout.addWidget(self.btn_move_down)
        main_layout.addWidget(button_bar)

        # Tree widget
        self.tree_widget = QTreeWidget()
        # --- MODIFIED: Added 'Tags' column ---
        self.tree_widget.setHeaderLabels(["Insight", "Claim", "Because", "Tags", "Details"])

        header = self.tree_widget.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)  # Tags column
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)  # Details column

        self.tree_widget.setColumnWidth(0, 50)
        self.tree_widget.setColumnWidth(3, 120)  # Tags column width
        self.tree_widget.setColumnWidth(4, 150)  # Details column width
        # --- END MODIFIED ---

        self.tree_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        main_layout.addWidget(self.tree_widget)

        # --- Connections ---
        self.btn_add.clicked.connect(self._add_item)
        self.btn_edit.clicked.connect(self._edit_item)
        self.btn_delete.clicked.connect(self._delete_item)
        self.btn_move_up.clicked.connect(self._move_up)
        self.btn_move_down.clicked.connect(self._move_down)

        self.tree_widget.itemDoubleClicked.connect(self._edit_item)
        self.tree_widget.customContextMenuRequested.connect(self.show_context_menu)
        self.tree_widget.currentItemChanged.connect(self._update_button_states)
        self.tree_widget.itemChanged.connect(self._on_item_changed)  # For checkbox

        self.load_arguments()
        self._update_button_states()

    def load_arguments(self):
        """Reloads all arguments from the database into the tree."""
        self._block_check_signals = True
        self.tree_widget.clear()
        try:
            arguments = self.db.get_reading_arguments(self.reading_id)
            for arg_data in arguments:
                self._add_argument_to_tree(self.tree_widget, arg_data)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load arguments: {e}")
        finally:
            self._block_check_signals = False

    def _add_argument_to_tree(self, parent_widget, arg_data):
        """Helper to build the tree item with multiple columns."""

        item = QTreeWidgetItem(parent_widget)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        if arg_data.get("is_insight"):
            item.setCheckState(0, Qt.CheckState.Checked)
        else:
            item.setCheckState(0, Qt.CheckState.Unchecked)

        item.setText(1, arg_data.get("claim_text", "N/A"))
        item.setText(2, arg_data.get("because_text", ""))
        item.setText(3, arg_data.get("synthesis_tags", ""))  # <-- ADDED
        item.setText(4, arg_data.get("details", ""))

        item.setData(0, Qt.ItemDataRole.UserRole, arg_data["id"])
        item.setExpanded(True)

    def _on_item_changed(self, item, column):
        """Called when the 'Insight' checkbox is clicked."""
        if self._block_check_signals or column != 0:
            return

        argument_id = item.data(0, Qt.ItemDataRole.UserRole)
        is_insight = item.checkState(0) == Qt.CheckState.Checked

        try:
            self.db.update_argument_insight_status(argument_id, is_insight)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not update insight status: {e}")
            self.load_arguments()  # Revert on failure

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

    def _update_button_states(self):
        """Enables/disables buttons based on selection."""
        item = self.tree_widget.currentItem()
        is_item_selected = item is not None

        self.btn_edit.setEnabled(is_item_selected)
        self.btn_delete.setEnabled(is_item_selected)

        # Move logic (only for root items)
        can_move_up = False
        can_move_down = False
        if is_item_selected and not item.parent():
            index = self.tree_widget.indexOfTopLevelItem(item)
            can_move_up = index > 0
            can_move_down = index < self.tree_widget.topLevelItemCount() - 1

        self.btn_move_up.setEnabled(can_move_up)
        self.btn_move_down.setEnabled(can_move_down)

    def show_context_menu(self, position):
        menu = QMenu(self)
        item = self.tree_widget.itemAt(position)

        menu.addAction(self.btn_add.text(), self._add_item)

        if item:
            menu.addAction(self.btn_edit.text(), self._edit_item)
            menu.addAction(self.btn_delete.text(), self._delete_item)
            menu.addSeparator()

        if self.tree_widget.topLevelItemCount() > 1 and ReorderDialog:
            reorder_action = QAction("Reorder Items...", self._reorder_items)
            menu.addAction(reorder_action)

        menu.exec(self.tree_widget.viewport().mapToGlobal(position))

    @Slot()
    def _handle_save(self, data, argument_id=None):
        """Central logic for saving an argument (add or edit)."""
        try:
            item_id = None
            if argument_id:
                # Update existing
                self.db.update_argument(argument_id, data)
                item_id = argument_id
            else:
                # Add new
                item_id = self.db.add_argument(self.reading_id, data)

            if not item_id:
                raise Exception("Failed to get item ID after save/update.")

            # --- VIRTUAL ANCHOR FIX ---
            # 1. Clear all existing virtual anchors for this item
            self.db.delete_anchors_by_item_link_id(item_id)

            # 2. Add new ones based on the tags
            tags_text = data.get("synthesis_tags", "")
            if tags_text:
                tag_names = [tag.strip() for tag in tags_text.split(',') if tag.strip()]
                summary_text = f"Argument: {data.get('claim_text', '')[:50]}..."

                for tag_name in tag_names:
                    tag_data = self.db.get_or_create_tag(tag_name, self.project_id)
                    if tag_data:
                        # Arguments don't have a single outline_id, so we pass None
                        self.db.create_anchor(
                            project_id=self.project_id,
                            reading_id=self.reading_id,
                            outline_id=None,
                            tag_id=tag_data['id'],
                            selected_text=summary_text,
                            comment=f"Linked to Argument ID {item_id}",
                            unique_doc_id=f"arg-{item_id}-{tag_data['id']}",
                            item_link_id=item_id
                        )
            # --- END VIRTUAL ANCHOR FIX ---

            self.load_arguments()  # Refresh tree
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save argument: {e}")
            import traceback
            traceback.print_exc()

    @Slot()
    def _add_item(self):
        """Adds a new root-level argument."""
        if not AddArgumentDialog:
            QMessageBox.critical(self, "Error", "Add Argument dialog not loaded.")
            return

        outline_items = self._get_outline_items()
        driving_questions = self._get_driving_questions()

        dialog = AddArgumentDialog(
            db=self.db,
            project_id=self.project_id,
            reading_id=self.reading_id,
            outline_items=outline_items,
            driving_questions=driving_questions,
            parent=self
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if not data.get('claim_text'):
                QMessageBox.warning(self, "Claim Required", "The 'Claim' field cannot be empty.")
                return
            self._handle_save(data, argument_id=None)

    @Slot()
    def _edit_item(self):
        """Edits the selected argument."""
        item = self.tree_widget.currentItem()
        if not item:
            return

        argument_id = item.data(0, Qt.ItemDataRole.UserRole)
        outline_items = self._get_outline_items()
        driving_questions = self._get_driving_questions()
        current_data = self.db.get_argument_details(argument_id)

        if not current_data:
            QMessageBox.critical(self, "Error", "Could not find argument details.")
            return

        dialog = AddArgumentDialog(
            db=self.db,
            project_id=self.project_id,
            reading_id=self.reading_id,
            outline_items=outline_items,
            driving_questions=driving_questions,
            current_data=current_data,
            parent=self
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if not data.get('claim_text'):
                QMessageBox.warning(self, "Claim Required", "The 'Claim' field cannot be empty.")
                return
            self._handle_save(data, argument_id=argument_id)

    @Slot()
    def _delete_item(self):
        """Deletes the selected argument."""
        item = self.tree_widget.currentItem()
        if not item:
            return

        argument_id = item.data(0, Qt.ItemDataRole.UserRole)
        reply = QMessageBox.question(
            self, "Delete Argument",
            f"Are you sure you want to delete this argument and all its evidence?\n\n'{item.text(1)}'\n\nThis will also delete any linked synthesis tags.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Cascade delete will handle the linked anchors
                self.db.delete_argument(argument_id)
                self.load_arguments()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not delete argument: {e}")

    @Slot()
    def _move_up(self):
        item = self.tree_widget.currentItem()
        if not item: return
        self._move_item(item, -1)

    @Slot()
    def _move_down(self):
        item = self.tree_widget.currentItem()
        if not item: return
        self._move_item(item, 1)

    def _move_item(self, item, direction):
        """Moves an item up (-1) or down (1) in its list."""
        if item.parent(): return  # Should not happen

        index = self.tree_widget.indexOfTopLevelItem(item)
        new_index = index + direction
        if 0 <= new_index < self.tree_widget.topLevelItemCount():
            self.tree_widget.takeTopLevelItem(index)
            self.tree_widget.insertTopLevelItem(new_index, item)
            self.tree_widget.setCurrentItem(item)
            self._save_order()

        self._update_button_states()

    @Slot()
    def _reorder_items(self):
        """Opens the full reorder dialog."""
        if not ReorderDialog:
            QMessageBox.critical(self, "Error", "Reorder dialog is not available.")
            return

        try:
            siblings = self.db.get_reading_arguments(self.reading_id)
            if len(siblings) < 2:
                QMessageBox.information(self, "Reorder", "Not enough items to reorder.")
                return

            items_to_reorder = [(q.get('claim_text', '...'), q['id']) for q in siblings]
            dialog = ReorderDialog(items_to_reorder, self)

            if dialog.exec() == QDialog.DialogCode.Accepted:
                ordered_ids = dialog.ordered_db_ids
                self.db.update_argument_order(ordered_ids)
                self.load_arguments()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not reorder arguments: {e}")

    def _save_order(self):
        """Saves the display order of root items."""
        ordered_ids = []
        for i in range(self.tree_widget.topLevelItemCount()):
            ordered_ids.append(self.tree_widget.topLevelItem(i).data(0, Qt.ItemDataRole.UserRole))

        try:
            self.db.update_argument_order(ordered_ids)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save new order: {e}")
            self.load_arguments()  # Revert on error