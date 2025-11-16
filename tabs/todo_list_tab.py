# tabs/todo_list_tab.py
import sys
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QLabel,
    QListWidget, QListWidgetItem, QFrame, QTextBrowser,
    QMenu, QMessageBox, QDialog, QPushButton
)
from PySide6.QtCore import Qt, Signal, Slot, QPoint
from PySide6.QtGui import QAction, QColor, QFont

# Import the new dialog
try:
    from dialogs.add_todo_dialog import AddTodoDialog
except ImportError:
    print("Error: Could not import AddTodoDialog")
    AddTodoDialog = None

# Import ReorderDialog
try:
    from dialogs.reorder_dialog import ReorderDialog
except ImportError:
    print("Error: Could not import ReorderDialog")
    ReorderDialog = None


class TodoListTab(QWidget):
    """
    A widget for managing a project "To-Do" list.
    Shows a list of items with checkboxes and a detail view.
    """

    def __init__(self, db, project_id, parent=None):
        super().__init__(parent)
        self.db = db
        self.project_id = project_id
        self._block_item_changed = False  # Flag to prevent signal loops

        main_layout = QVBoxLayout(self)

        # --- (1) "Add Item" Button ---
        self.add_item_btn = QPushButton("Add New Item")
        self.add_item_btn.clicked.connect(self._add_item)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.add_item_btn)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)

        # --- Splitter for List and Detail ---
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        main_layout.addWidget(splitter, 1)  # Give splitter all remaining space

        # --- Left Panel (To-Do List) ---
        left_panel = QFrame()
        left_panel.setFrameShape(QFrame.Shape.StyledPanel)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(4, 4, 4, 4)
        left_layout.addWidget(QLabel("To-Do Items"))

        self.item_list = QListWidget()
        self.item_list.currentItemChanged.connect(self.on_item_selected)
        self.item_list.itemChanged.connect(self.on_item_changed)  # For checkbox
        # --- (2) Right-click Context Menu ---
        self.item_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.item_list.customContextMenuRequested.connect(self.show_context_menu)
        left_layout.addWidget(self.item_list)

        splitter.addWidget(left_panel)

        # --- Right Panel (Detail Viewer) ---
        right_panel = QFrame()
        right_panel.setFrameShape(QFrame.Shape.StyledPanel)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(4, 4, 4, 4)
        right_layout.addWidget(QLabel("Details"))

        self.detail_viewer = QTextBrowser()
        right_layout.addWidget(self.detail_viewer)

        splitter.addWidget(right_panel)
        splitter.setSizes([300, 600])

        self.item_list.itemDoubleClicked.connect(self._edit_item)

    def load_items(self):
        """Reloads the list of to-do items from the database."""
        self._block_item_changed = True
        self.item_list.clear()
        self.detail_viewer.clear()
        try:
            items = self.db.get_project_todo_items(self.project_id)

            if not items:
                item = QListWidgetItem("No to-do items added yet.")
                item.setFlags(Qt.ItemFlag.NoItemFlags)
                self.item_list.addItem(item)
                self._block_item_changed = False
                return

            for item_data in items:
                item = QListWidgetItem(item_data['display_name'])
                # --- FIX: Use 1-argument setData ---
                item.setData(Qt.ItemDataRole.UserRole, item_data['id'])
                item.setCheckState(Qt.CheckState.Checked if item_data['is_checked'] else Qt.CheckState.Unchecked)
                self.item_list.addItem(item)
        except Exception as e:
            QMessageBox.critical(self, "Error Loading Items", f"Could not load to-do items: {e}")
        finally:
            self._block_item_changed = False

    @Slot(QListWidgetItem)
    def on_item_changed(self, item):
        """Called when an item is checked or unchecked."""
        if self._block_item_changed:
            return

        # --- FIX: Use 1-argument data() ---
        item_id = item.data(Qt.ItemDataRole.UserRole)
        if item_id is None:
            return

        is_checked = item.checkState() == Qt.CheckState.Checked
        try:
            self.db.update_todo_item_checked(item_id, is_checked)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not update check state: {e}")
            # Revert check state on error
            self._block_item_changed = True
            item.setCheckState(Qt.CheckState.Unchecked if is_checked else Qt.CheckState.Checked)
            self._block_item_changed = False

    @Slot(QListWidgetItem, QListWidgetItem)
    def on_item_selected(self, current_item, previous_item):
        """Called when an item is clicked, loads its details."""
        if current_item is None:
            self.detail_viewer.clear()
            return

        # --- FIX: Use 1-argument data() ---
        item_id = current_item.data(Qt.ItemDataRole.UserRole)
        if item_id is None:
            self.detail_viewer.clear()
            return

        try:
            data = self.db.get_todo_item_details(item_id)
            if not data:
                self.detail_viewer.setHtml("<i>Could not load item details.</i>")
                return

            html = f"""
            <style>
                h3 {{
                    color: #333;
                    border-bottom: 1px solid #ddd;
                    padding-bottom: 4px;
                }}
                .card {{
                    background: #fdfdfd;
                    border: 1px solid #eee;
                    padding: 10px;
                    border-radius: 5px;
                    margin-bottom: 15px;
                }}
            </style>
            """
            html += f"<h3>Task:</h3>"
            html += f"<div class='card'>{data.get('task_html', '<i>No task description.</i>')}</div>"
            html += f"<h3>Notes:</h3>"
            html += f"<div class='card'>{data.get('notes_html', '<i>No notes.</i>')}</div>"

            self.detail_viewer.setHtml(html)

        except Exception as e:
            self.detail_viewer.setHtml(f"<p><b>Error loading details:</b><br>{e}</p>")
            QMessageBox.critical(self, "Error", f"Could not load item details: {e}")

    @Slot(QPoint)
    def show_context_menu(self, position):
        """Shows the right-click menu for the item list."""
        menu = QMenu(self)

        # (A) Add Item
        add_action = menu.addAction("Add New Item...")
        add_action.triggered.connect(self._add_item)

        item = self.item_list.itemAt(position)
        # --- FIX: Use 1-argument data() ---
        if item and item.data(Qt.ItemDataRole.UserRole) is not None:
            menu.addSeparator()
            # (B) Edit Item
            edit_action = menu.addAction("Edit Item...")
            edit_action.triggered.connect(self._edit_item)
            # (C) Delete Item
            delete_action = menu.addAction("Delete Item")
            delete_action.triggered.connect(self._delete_item)

        # (D) Reorder Items
        real_item_count = 0
        for i in range(self.item_list.count()):
            # --- FIX: Use 1-argument data() ---
            if self.item_list.item(i).data(Qt.ItemDataRole.UserRole) is not None:
                real_item_count += 1

        if real_item_count > 1 and ReorderDialog:
            menu.addSeparator()
            reorder_action = menu.addAction("Reorder Items...")
            reorder_action.triggered.connect(self._reorder_items)

        menu.exec(self.item_list.mapToGlobal(position))

    @Slot()
    def _add_item(self):
        """Opens the AddTodoDialog to create a new item."""
        if not AddTodoDialog:
            QMessageBox.critical(self, "Error", "Add To-Do Dialog could not be loaded.")
            return

        dialog = AddTodoDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if not data['display_name']:
                QMessageBox.warning(self, "Invalid Name", "Display Name cannot be empty.")
                return

            try:
                db_data = {
                    'display_name': data.get('display_name'),
                    'task_html': data.get('task_html'),
                    'notes_html': data.get('notes_html')
                }
                self.db.add_todo_item(self.project_id, db_data)
                self.load_items()  # Refresh the list
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not save new item: {e}")

    @Slot()
    def _edit_item(self):
        """Opens the AddTodoDialog to edit the selected item."""
        item = self.item_list.currentItem()
        # --- FIX: Use 1-argument data() ---
        if not item or item.data(Qt.ItemDataRole.UserRole) is None:
            return

        # --- FIX: Use 1-argument data() ---
        item_id = item.data(Qt.ItemDataRole.UserRole)

        if not AddTodoDialog:
            QMessageBox.critical(self, "Error", "Edit To-Do Dialog could not be loaded.")
            return

        current_data = self.db.get_todo_item_details(item_id)
        if not current_data:
            QMessageBox.critical(self, "Error", "Could not find item details to edit.")
            return

        # Pass the HTML content to the dialog
        current_data['task_html'] = current_data.get('task_html', '')
        current_data['notes_html'] = current_data.get('notes_html', '')

        dialog = AddTodoDialog(current_data=current_data, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if not data['display_name']:
                QMessageBox.warning(self, "Invalid Name", "Display Name cannot be empty.")
                return

            try:
                db_data = {
                    'display_name': data.get('display_name'),
                    'task_html': data.get('task_html'),
                    'notes_html': data.get('notes_html')
                }
                self.db.update_todo_item(item_id, db_data)
                self.load_items()  # Refresh the list
                # Reselect the item to refresh the detail view
                for i in range(self.item_list.count()):
                    # --- FIX: Use 1-argument data() ---
                    if self.item_list.item(i).data(Qt.ItemDataRole.UserRole) == item_id:
                        self.item_list.setCurrentRow(i)
                        break
                self.on_item_selected(self.item_list.currentItem(), None)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not update item: {e}")

    @Slot()
    def _delete_item(self):
        """Deletes the selected item."""
        item = self.item_list.currentItem()
        # --- FIX: Use 1-argument data() ---
        if not item or item.data(Qt.ItemDataRole.UserRole) is None:
            return

        # --- FIX: Use 1-argument data() ---
        item_id = item.data(Qt.ItemDataRole.UserRole)
        item_name = item.text()

        reply = QMessageBox.question(
            self, "Delete Item",
            f"Are you sure you want to delete the item '{item_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.db.delete_todo_item(item_id)
                self.load_items()  # Refresh the list
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not delete item: {e}")

    @Slot()
    def _reorder_items(self):
        """Opens the reorder dialog for items."""
        if not ReorderDialog:
            QMessageBox.critical(self, "Error", "Reorder dialog is not available.")
            return

        items_to_reorder = []
        for i in range(self.item_list.count()):
            item = self.item_list.item(i)
            # --- FIX: Use 1-argument data() ---
            item_id = item.data(Qt.ItemDataRole.UserRole)
            if item_id is not None:
                items_to_reorder.append((item.text(), item_id))

        if len(items_to_reorder) < 2:
            return

        dialog = ReorderDialog(items_to_reorder, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            ordered_ids = dialog.ordered_db_ids
            try:
                self.db.update_todo_order(ordered_ids)
                self.load_items()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not reorder items: {e}")