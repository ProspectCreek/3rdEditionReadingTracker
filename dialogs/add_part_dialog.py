# prospectcreek/3rdeditionreadingtracker/3rdEditionReadingTracker-d0eaa6c33c524aa054deaa3e5b81207eb93ba7d2/dialogs/add_part_dialog.py

import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QTextEdit,
    QComboBox, QDialogButtonBox, QWidget, QHBoxLayout,
    QPushButton, QLabel, QMessageBox
)
from PySide6.QtCore import Qt, Slot


class AddPartDialog(QDialog):
    """
    Dialog for adding or editing a 'Part' and its relationships.
    """

    def __init__(self, db_manager, reading_id, outline_items, driving_questions, current_data=None, parent=None):
        super().__init__(parent)

        self.db = db_manager
        self.reading_id = reading_id
        self.outline_items = outline_items
        self.driving_questions = driving_questions
        self.current_data = current_data if current_data else {}

        self.setWindowTitle("Edit Part Details" if current_data else "Add New Part")
        self.setMinimumWidth(550)

        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        # --- Part Selection (Outline Item) ---
        self.part_combo = QComboBox()
        self._populate_outline_combo(self.outline_items)
        form_layout.addRow("Select Part:", self.part_combo)

        # --- Linked Driving Question ---
        self.dq_combo = QComboBox()
        self.dq_combo.addItem("None", None)
        for dq in self.driving_questions:
            nickname = dq.get('nickname')
            if nickname and nickname.strip():
                display_text = nickname
            else:
                q_text = (dq.get('question_text', '') or '')
                display_text = (q_text[:70] + "...") if len(q_text) > 70 else q_text
            self.dq_combo.addItem(display_text, dq['id'])
        form_layout.addRow("Linked DQ:", self.dq_combo)

        # --- Function ---
        self.function_editor = QTextEdit()
        self.function_editor.setPlaceholderText("Defines the problem; introduces theory; presents data…")
        self.function_editor.setMinimumHeight(100)
        form_layout.addRow("Function:", self.function_editor)

        # --- Relation ---
        self.relation_editor = QTextEdit()
        self.relation_editor.setPlaceholderText("Bridges theory to evidence; answers prior question…")
        self.relation_editor.setMinimumHeight(100)
        form_layout.addRow("Relation:", self.relation_editor)

        # --- Dependency ---
        self.dependency_editor = QTextEdit()
        self.dependency_editor.setPlaceholderText("Later claims lose context; conclusions lack base…")
        self.dependency_editor.setMinimumHeight(100)
        form_layout.addRow("Dependency:", self.dependency_editor)

        main_layout.addLayout(form_layout)

        # --- Standard OK/Cancel buttons ---
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

        if self.current_data:
            self._set_data(self.current_data)
        else:
            # When adding, we must select an outline item
            self.part_combo.setCurrentIndex(0)

    def _populate_outline_combo(self, outline_items, indent=0):
        """Recursively populates the 'Select Part' dropdown."""
        if indent == 0:
            self.part_combo.addItem("[Select a Part]", None)  # Top-level

        for item in outline_items:
            prefix = "  " * indent
            display_text = f"{prefix} {item['section_title']}"
            self.part_combo.addItem(display_text, item['id'])

            if 'children' in item:
                self._populate_outline_combo(item['children'], indent + 1)

    def _set_data(self, data):
        """Populates the dialog with existing data."""
        outline_id = data.get("id")  # In this case, the part data IS the outline item
        if outline_id:
            idx = self.part_combo.findData(outline_id)
            if idx != -1:
                self.part_combo.setCurrentIndex(idx)
            # Disable changing the part, you can only edit its details
            self.part_combo.setEnabled(False)

        dq_id = data.get('part_dq_id')
        if dq_id:
            idx = self.dq_combo.findData(dq_id)
            if idx != -1:
                self.dq_combo.setCurrentIndex(idx)

        self.function_editor.setPlainText(data.get('part_function_text_plain', ''))
        self.relation_editor.setPlainText(data.get('part_relation_text_plain', ''))
        self.dependency_editor.setPlainText(data.get('part_dependency_text_plain', ''))

    def get_data(self):
        """Returns all data from the dialog fields in a dictionary."""

        outline_id = self.part_combo.currentData()
        if not outline_id:
            # This is a validation check, we will handle it in the accept() method
            return None

        return {
            "is_structural": True,  # By saving, it becomes a structural part
            "outline_id": outline_id,
            "driving_question_id": self.dq_combo.currentData(),
            "function_text": self.function_editor.toPlainText().strip(),
            "relation_text": self.relation_editor.toPlainText().strip(),
            "dependency_text": self.dependency_editor.toPlainText().strip()
        }

    def accept(self):
        """Validate before accepting."""
        if not self.part_combo.currentData():
            QMessageBox.warning(self, "Error", "You must select a part from the 'Select Part' dropdown.")
            return  # Do not close

        super().accept()