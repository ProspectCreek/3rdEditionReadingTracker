import sys
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton,
    QMessageBox, QDialog
)
from PySide6.QtCore import Qt, Slot

# This is our actual web view widget
from tabs.quill_editor_tab import QuillEditorTab

try:
    from dialogs.edit_instructions_dialog import EditInstructionsDialog
except ImportError:
    print("Error: Could not import EditInstructionsDialog")
    sys.exit(1)


class ProjectEditorTab(QWidget):
    """
    A single tab for the project dashboard's bottom section.
    Contains:
    1. Clickable instructions.
    2. A Quill Editor instance.
    """

    def __init__(self, db_manager, project_id, field_name, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.project_id = project_id

        # field_name is 'key_questions', 'thesis', 'insights', 'unresolved'
        self.instr_field = f"{field_name}_instr"
        self.text_field = f"{field_name}_text"

        self.current_instructions = {}

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # 1. Instructions Label
        self.instr_label = QLabel("Loading instructions...")
        self.instr_label.setWordWrap(True)
        self.instr_label.setStyleSheet("QLabel { color: #555; font-style: italic; }")

        # 2. The Quill Editor
        self.quill_editor = QuillEditorTab()

        main_layout.addWidget(self.instr_label)
        main_layout.addWidget(self.quill_editor)

        self.load_data()

    def load_data(self):
        """Loads instructions and text content from the database."""
        # Load instructions
        self.current_instructions = self.db.get_or_create_instructions(self.project_id)
        if self.current_instructions:
            self.instr_label.setText(self.current_instructions.get(self.instr_field, ""))

        # Load editor content
        project_data = self.db.get_item_details(self.project_id)
        if project_data:
            self.quill_editor.set_content(project_data[self.text_field])

    def open_edit_instructions_dialog(self):
        """
        Public method to be called from the new menu.
        Opens the dialog to edit all four instruction fields.
        """
        # We need to refresh this just in case
        self.current_instructions = self.db.get_or_create_instructions(self.project_id)

        dialog = EditInstructionsDialog(self.current_instructions, self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_instr = dialog.result
            try:
                self.db.update_instructions(
                    self.project_id,
                    new_instr["key_questions_instr"],
                    new_instr["thesis_instr"],
                    new_instr["insights_instr"],
                    new_instr["unresolved_instr"]
                )
                # Reload data for this tab
                self.load_data()
            except Exception as e:
                QMessageBox.critical(self, "DatabaseError", f"Could not update instructions: {e}")

    def get_editor_content(self, callback):
        """Passes the async request down to the quill editor."""
        self.quill_editor.get_content(callback)

