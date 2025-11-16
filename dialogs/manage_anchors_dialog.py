# dialogs/manage_anchors_dialog.py
import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QListWidget, QListWidgetItem,
    QDialogButtonBox, QPushButton, QHBoxLayout, QMessageBox, QLabel
)
from PySide6.QtCore import Qt, Signal


class ManageAnchorsDialog(QDialog):
    """
    A dialog to view all anchors for a specific tag and delete them
    individually.
    """
    # Signal emitted when an anchor has been deleted
    anchorDeleted = Signal()

    # ##################################################################
    # #
    # #                 --- MODIFICATION START ---
    # #
    # ##################################################################
    def __init__(self, db, project_id, tag_id, tag_name, parent=None):
        super().__init__(parent)
        self.db = db
        self.project_id = project_id  # <-- Store project_id
        self.tag_id = tag_id
        self.tag_name = tag_name
        # ##################################################################
        # #
        # #                 --- MODIFICATION END ---
        # #
        # ##################################################################

        self.setWindowTitle(f"Manage Anchors for '{tag_name}'")
        self.setMinimumSize(600, 400)

        main_layout = QVBoxLayout(self)

        main_layout.addWidget(QLabel(f"Anchors for: {tag_name}"))

        self.anchor_list = QListWidget()
        main_layout.addWidget(self.anchor_list)

        btn_layout = QHBoxLayout()
        self.delete_btn = QPushButton("Delete Selected Anchor")
        btn_layout.addStretch()
        btn_layout.addWidget(self.delete_btn)
        main_layout.addLayout(btn_layout)

        # Standard OK/Cancel buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        main_layout.addWidget(self.button_box)

        # --- Connections ---
        self.delete_btn.clicked.connect(self._delete_selected_anchor)
        self.button_box.rejected.connect(self.reject)
        self.anchor_list.currentItemChanged.connect(self._update_button_state)

        self.load_anchors()
        self._update_button_state()

    def load_anchors(self):
        """Reloads the list of anchors for this tag."""
        self.anchor_list.clear()
        try:
            # ##################################################################
            # #
            # #                 --- MODIFICATION START ---
            # #
            # ##################################################################
            # Use the new "simple" getter that is filtered by project_id
            anchors = self.db.get_anchors_for_tag_simple(self.tag_id, self.project_id)
            # ##################################################################
            # #
            # #                 --- MODIFICATION END ---
            # #
            # ##################################################################

            if not anchors:
                item = QListWidgetItem("No anchors found for this tag in this project.")
                item.setFlags(Qt.ItemFlag.NoItemFlags)
                self.anchor_list.addItem(item)
                return

            for anchor in anchors:
                text = anchor['selected_text']
                comment = anchor.get('comment', '')

                # Truncate for display
                if len(text) > 100:
                    text = text[:100] + "..."

                display_text = f"\"{text}\""
                if comment:
                    display_text += f"\n    Comment: {comment[:100]}..."

                item = QListWidgetItem(display_text)
                item.setData(Qt.ItemDataRole.UserRole, anchor['id'])
                self.anchor_list.addItem(item)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load anchors: {e}")

    def _update_button_state(self):
        """Enables or disables the delete button."""
        selected_item = self.anchor_list.currentItem()
        can_delete = selected_item is not None and selected_item.data(Qt.ItemDataRole.UserRole) is not None
        self.delete_btn.setEnabled(can_delete)

    def _delete_selected_anchor(self):
        """Deletes just the one selected anchor."""
        item = self.anchor_list.currentItem()
        if not item or item.data(Qt.ItemDataRole.UserRole) is None:
            return

        anchor_id = item.data(Qt.ItemDataRole.UserRole)
        text = item.text().split("\n")[0]

        reply = QMessageBox.question(
            self, "Delete Anchor",
            f"Are you sure you want to delete this anchor?\n\n{text}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.db.delete_anchor(anchor_id)
                self.load_anchors()  # Refresh this dialog's list
                self.anchorDeleted.emit()  # Signal to the app
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not delete anchor: {e}")