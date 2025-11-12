# dialogs/create_anchor_dialog.py
import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QTextEdit,
    QComboBox, QCheckBox, QDialogButtonBox, QLabel
)
from PySide6.QtCore import Qt


class CreateAnchorDialog(QDialog):
    """
    A dialog for creating or editing a synthesis anchor.
    """

    def __init__(self, selected_text, project_tags_list=None, current_data=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create Synthesis Anchor")
        if current_data:
            self.setWindowTitle("Edit Synthesis Anchor")

        self.project_tags = project_tags_list if project_tags_list else []
        self.current_data = current_data if current_data else {}

        main_layout = QVBoxLayout(self)

        # Selected Text (read-only)
        form_layout = QFormLayout()
        self.selected_text_label = QLineEdit(selected_text)
        self.selected_text_label.setReadOnly(True)
        self.selected_text_label.setStyleSheet("background-color: #f0f0f0;")
        form_layout.addRow("Selected Text:", self.selected_text_label)

        # Tag selection/creation
        self.tag_combo = QComboBox()
        self.tag_combo.setEditable(True)
        self.tag_combo.setPlaceholderText("Select or create new tag...")

        # Populate with existing tags
        self.tag_combo.addItem("", None)  # Add a blank entry
        for tag in self.project_tags:
            self.tag_combo.addItem(tag['name'], tag['id'])

        # Set current tag if editing
        current_tag_name = self.current_data.get('tag_name', '')
        if current_tag_name:
            idx = self.tag_combo.findText(current_tag_name)
            if idx != -1:
                self.tag_combo.setCurrentIndex(idx)
            else:
                self.tag_combo.setEditText(current_tag_name)

        form_layout.addRow("Select tag or create new:", self.tag_combo)

        # Add '#' prefix checkbox
        self.add_prefix_check = QCheckBox("Add '#' prefix")
        self.add_prefix_check.setChecked(True)
        form_layout.addRow("", self.add_prefix_check)

        # Comment
        self.comment_edit = QTextEdit()
        self.comment_edit.setPlaceholderText("Add optional comment...")
        self.comment_edit.setMinimumHeight(80)
        self.comment_edit.setText(self.current_data.get('comment', ''))
        form_layout.addRow("Comment (optional):", self.comment_edit)

        main_layout.addLayout(form_layout)

        # Standard OK/Cancel buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

        self.tag_combo.currentTextChanged.connect(self._update_prefix_state)
        self._update_prefix_state(self.tag_combo.currentText())

    def _update_prefix_state(self, text):
        """Disables the '#' prefix checkbox if the tag already has one."""
        if text.startswith("#"):
            self.add_prefix_check.setChecked(False)
            self.add_prefix_check.setEnabled(False)
        else:
            self.add_prefix_check.setEnabled(True)

    def get_tag_text(self):
        """Gets the final tag text, adding prefix if needed."""
        text = self.tag_combo.currentText().strip()
        if self.add_prefix_check.isChecked() and not text.startswith("#"):
            return f"#{text}"
        return text

    def get_comment(self):
        """Gets the comment text."""
        return self.comment_edit.toPlainText().strip()