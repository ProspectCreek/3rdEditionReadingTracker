# dialogs/add_todo_dialog.py
import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QTextEdit,
    QDialogButtonBox, QLabel
)
from PySide6.QtCore import Qt


class AddTodoDialog(QDialog):
    """
    Dialog for adding or editing a to-do list item.
    """

    def __init__(self, current_data=None, parent=None):
        super().__init__(parent)

        self.current_data = current_data if current_data else {}
        self.setWindowTitle("Edit To-Do Item" if current_data else "Add To-Do Item")
        self.setMinimumWidth(400)

        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        # Display Name
        self.display_name_edit = QLineEdit()
        self.display_name_edit.setText(self.current_data.get("display_name", ""))
        form_layout.addRow("Display Name:", self.display_name_edit)

        # Task
        self.task_edit = QTextEdit()
        self.task_edit.setPlaceholderText("Describe the task...")
        self.task_edit.setMinimumHeight(80)
        self.task_edit.setHtml(self.current_data.get("task_html", ""))
        form_layout.addRow("Task:", self.task_edit)

        # Notes
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Add any notes...")
        self.notes_edit.setMinimumHeight(60)
        self.notes_edit.setHtml(self.current_data.get("notes_html", ""))
        form_layout.addRow("Notes:", self.notes_edit)

        main_layout.addLayout(form_layout)

        # --- Standard OK/Cancel buttons ---
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

    def get_data(self):
        """Returns all data from the dialog fields in a dictionary."""
        return {
            "display_name": self.display_name_edit.text().strip(),
            "task_html": self.task_edit.toHtml(),
            "notes_html": self.notes_edit.toHtml(),
        }