# dialogs/edit_tag_dialog.py
import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QCheckBox, QDialogButtonBox, QLabel
)
from PySide6.QtCore import Qt, Slot


class EditTagDialog(QDialog):
    """
    A simple dialog to create a new tag or rename an existing one.
    """

    def __init__(self, current_name=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create New Tag" if current_name is None else "Rename Tag")

        self.original_name = current_name or ""
        main_layout = QVBoxLayout(self)

        form_layout = QFormLayout()
        self.tag_name_edit = QLineEdit()
        self.tag_name_edit.setText(self.original_name.lstrip("#"))  # Start without '#'
        form_layout.addRow("Tag Name:", self.tag_name_edit)

        self.add_prefix_check = QCheckBox("Add '#' prefix")
        # If the original name had a #, check the box. Otherwise, default to checked.
        self.add_prefix_check.setChecked(self.original_name.startswith("#") or current_name is None)

        form_layout.addRow("", self.add_prefix_check)

        main_layout.addLayout(form_layout)

        # Standard OK/Cancel buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

        # Connect the line edit to update the checkbox state
        self.tag_name_edit.textChanged.connect(self._update_prefix_state)
        self._update_prefix_state(self.tag_name_edit.text())

    @Slot(str)
    def _update_prefix_state(self, text):
        """Disables the '#' prefix checkbox if the tag already has one."""
        if text.startswith("#"):
            self.add_prefix_check.setChecked(False)
            self.add_prefix_check.setEnabled(False)
        else:
            self.add_prefix_check.setEnabled(True)

    def get_tag_name(self):
        """Gets the final tag text, adding prefix if needed."""
        text = self.tag_name_edit.text().strip()
        if not text:
            return ""  # Return empty if no name

        if self.add_prefix_check.isChecked() and not text.startswith("#"):
            return f"#{text}"

        # If text already starts with #, the checkbox is disabled, so just return text
        return text