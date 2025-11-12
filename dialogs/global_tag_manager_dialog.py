# dialogs/global_tag_manager_dialog.py
import sys
import sqlite3
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QDialogButtonBox, QMessageBox, QInputDialog
)
from PySide6.QtCore import Qt, Slot

# Import the dialog for renaming
try:
    from dialogs.edit_tag_dialog import EditTagDialog
except ImportError:
    EditTagDialog = None

class GlobalTagManagerDialog(QDialog):
    """
    A dialog for managing all global synthesis tags:
    rename, delete, and merge.
    """

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Global Tag Manager")
        self.setMinimumSize(400, 500)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        main_layout = QVBoxLayout(self)

        self.tag_list = QListWidget()
        self.tag_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        main_layout.addWidget(self.tag_list)

        btn_layout = QHBoxLayout()
        self.rename_btn = QPushButton("Rename...")
        self.delete_btn = QPushButton("Delete...")
        self.merge_btn = QPushButton("Merge...")
        btn_layout.addWidget(self.rename_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addWidget(self.merge_btn)
        main_layout.addLayout(btn_layout)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        main_layout.addWidget(self.button_box)

        # Connections
        self.rename_btn.clicked.connect(self._rename_tag)
        self.delete_btn.clicked.connect(self._delete_tag)
        self.merge_btn.clicked.connect(self._merge_tags)
        self.button_box.rejected.connect(self.reject) # Close maps to reject
        self.tag_list.itemSelectionChanged.connect(self._update_button_states)

        self.load_tags()
        self._update_button_states()

    def load_tags(self):
        """Reloads the list of all tags from the database."""
        self.tag_list.clear()
        try:
            tags = self.db.get_all_tags()
            for tag in tags:
                item = QListWidgetItem(tag['name'])
                item.setData(Qt.ItemDataRole.UserRole, tag['id'])
                self.tag_list.addItem(item)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load tags: {e}")

    @Slot()
    def _update_button_states(self):
        """Updates button enabled state based on selection."""
        selected_count = len(self.tag_list.selectedItems())
        self.rename_btn.setEnabled(selected_count == 1)
        self.delete_btn.setEnabled(selected_count > 0)
        self.merge_btn.setEnabled(selected_count > 1) # Merge requires 2 or more

    @Slot()
    def _rename_tag(self):
        """Renames the selected tag."""
        if not EditTagDialog:
            QMessageBox.critical(self, "Error", "EditTagDialog not loaded.")
            return

        selected_items = self.tag_list.selectedItems()
        if len(selected_items) != 1:
            return

        item = selected_items[0]
        tag_id = item.data(Qt.ItemDataRole.UserRole)
        current_name = item.text()

        dialog = EditTagDialog(current_name=current_name, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_name = dialog.get_tag_name()
            if not new_name or new_name == current_name:
                return

            try:
                self.db.rename_tag(tag_id, new_name)
                self.load_tags()
                self.accept()  # Signal to home screen to refresh
            except sqlite3.IntegrityError:
                QMessageBox.warning(self, "Tag Exists", f"A tag named '{new_name}' already exists.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not rename tag: {e}")

    @Slot()
    def _delete_tag(self):
        """Deletes the selected tag(s)."""
        selected_items = self.tag_list.selectedItems()
        if not selected_items:
            return

        names = [item.text() for item in selected_items]
        reply = QMessageBox.question(
            self, "Delete Tags",
            f"Are you sure you want to delete {len(names)} tag(s)?\n\n"
            f"({', '.join(names[:5])}...)\n\n"
            "This will delete the tag(s) and all associated anchors from all projects.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                for item in selected_items:
                    tag_id = item.data(Qt.ItemDataRole.UserRole)
                    self.db.delete_tag_and_anchors(tag_id)
                self.load_tags()
                self.accept()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not delete tags: {e}")

    @Slot()
    def _merge_tags(self):
        """Merges multiple tags into one."""
        selected_items = self.tag_list.selectedItems()
        if len(selected_items) < 2:
            return

        # Use QInputDialog to get the target tag name from the user
        tag_names = [item.text() for item in selected_items]
        target_name, ok = QInputDialog.getItem(
            self,
            "Merge Tags",
            "Select the tag to merge all others into:",
            tag_names,
            0,
            False
        )

        if not ok or not target_name:
            return

        # Find the target item
        target_item = next(item for item in selected_items if item.text() == target_name)
        target_tag_id = target_item.data(Qt.ItemDataRole.UserRole)
        source_items = [item for item in selected_items if item.text() != target_name]

        try:
            for item in source_items:
                source_tag_id = item.data(Qt.ItemDataRole.UserRole)
                self.db.merge_tags(source_tag_id, target_tag_id)

            self.load_tags()
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not merge tags: {e}")