# dialogs/edit_driving_question_dialog.py
import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QTextEdit,
    QComboBox, QCheckBox, QDialogButtonBox, QWidget, QHBoxLayout,
    QRadioButton, QSpacerItem, QSizePolicy, QLabel, QPushButton
)
from PySide6.QtCore import Qt


class EditDrivingQuestionDialog(QDialog):
    """
    A dialog for adding or editing a driving question, based on the user's screenshot.
    """

    def __init__(self, current_question_data=None, all_questions=None, outline_items=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Driving Question" if current_question_data else "Add Driving Question")
        self.setMinimumWidth(600)

        self.data = current_question_data if current_question_data else {}
        self.all_questions = all_questions if all_questions else []
        self.outline_items = outline_items if outline_items else []

        main_layout = QVBoxLayout(self)

        # Purpose Label
        purpose_label = QLabel(
            "Purpose: If the author never wrote this book, what puzzle would remain unsolved? That's your driving question."
        )
        purpose_label.setWordWrap(True)
        purpose_label.setStyleSheet("font-style: italic; color: #333;")
        main_layout.addWidget(purpose_label)

        # Form Layout
        form_layout = QFormLayout()
        form_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)

        self.question_text_edit = QTextEdit()
        self.question_text_edit.setPlaceholderText("Enter the driving question...")
        self.question_text_edit.setMinimumHeight(60)
        self.question_text_edit.setText(self.data.get("question_text", ""))
        form_layout.addRow("Driving Question:", self.question_text_edit)

        self.nickname_edit = QLineEdit()
        self.nickname_edit.setPlaceholderText("Enter a short nickname for this question")
        self.nickname_edit.setText(self.data.get("nickname", ""))
        form_layout.addRow("Nickname:", self.nickname_edit)

        # Type (Radio Buttons)
        type_layout = QHBoxLayout()
        self.type_stated_radio = QRadioButton("Stated")
        self.type_inferred_radio = QRadioButton("Inferred")
        type_layout.addWidget(self.type_stated_radio)
        type_layout.addWidget(self.type_inferred_radio)
        type_layout.addStretch()
        if self.data.get("type", "Inferred") == "Stated":
            self.type_stated_radio.setChecked(True)
        else:
            self.type_inferred_radio.setChecked(True)
        form_layout.addRow("Type:", type_layout)

        # Question Category
        self.category_combo = QComboBox()
        self.category_combo.addItems([
            "Descriptive (what/which)",
            "Explanatory (why/how)",
            "Evaluative (true/good)",
            "Prescriptive (what should we do)"
        ])
        self.category_combo.setCurrentText(self.data.get("question_category", "Explanatory (why/how)"))
        form_layout.addRow("Question Category:", self.category_combo)

        # Scope
        scope_layout = QHBoxLayout()
        self.scope_combo = QComboBox()
        self.scope_combo.addItems([
            "Global",
            "Part",
            "Chapter",
            "Section"
        ])
        self.scope_combo.setCurrentText(self.data.get("scope", "Global"))
        scope_layout.addWidget(self.scope_combo)
        # REMOVED: self.reading_has_parts_check
        scope_layout.addStretch()
        form_layout.addRow("Scope:", scope_layout)

        # Parent Question
        self.parent_combo = QComboBox()
        self.parent_combo.addItem("None (Root Question)", None)
        current_id = self.data.get("id")
        for q in self.all_questions:
            # Don't allow a question to be its own parent
            if q["id"] != current_id:
                # Simple indentation for hierarchy
                prefix = ""
                if q["parent_id"]:
                    prefix = "  - "
                display_text = q.get('nickname') or q.get('question_text', '')
                if not display_text:
                    display_text = f"Question {q['id']}"
                self.parent_combo.addItem(f"{prefix}{display_text[:50]}...", q["id"])

        if self.data.get("parent_id"):
            self.parent_combo.setCurrentIndex(self.parent_combo.findData(self.data.get("parent_id")))
        form_layout.addRow("Parent:", self.parent_combo)

        # Where in Reading
        where_layout = QHBoxLayout()
        self.where_combo = QComboBox()
        self.where_combo.addItem("Reading-Level Notes (Default)", None)  # Use None as ID for default

        # Populate outline
        self._populate_outline_combo(self.outline_items, self.where_combo)

        self.where_combo.setEnabled(True)

        # Set current item
        current_outline_id = self.data.get("outline_id")
        if current_outline_id:
            idx = self.where_combo.findData(current_outline_id)
            if idx != -1:
                self.where_combo.setCurrentIndex(idx)

        where_layout.addWidget(self.where_combo)
        where_layout.addWidget(QLabel("Page(s):"))
        self.pages_edit = QLineEdit()
        self.pages_edit.setPlaceholderText("e.g., 12-15")
        self.pages_edit.setFixedWidth(80)
        self.pages_edit.setText(self.data.get("pages", ""))
        where_layout.addWidget(self.pages_edit)
        where_layout.addStretch()
        form_layout.addRow("Where in Reading:", where_layout)  # Label Changed

        # Why this question
        self.why_question_edit = QTextEdit()
        self.why_question_edit.setPlaceholderText("Explain why you think this is the driving question...")
        self.why_question_edit.setMinimumHeight(80)
        self.why_question_edit.setText(self.data.get("why_question", ""))
        form_layout.addRow("Why I think this is the question:", self.why_question_edit)

        # Synthesis Tags (as requested, placeholders)
        tags_layout = QHBoxLayout()
        self.tags_edit = QTextEdit()
        self.tags_edit.setPlaceholderText("Tags separated by commas")
        self.tags_edit.setEnabled(False)  # Placeholder
        self.tags_edit.setFixedHeight(60)
        tags_layout.addWidget(self.tags_edit)
        connect_btn = QPushButton("Connect...")
        connect_btn.setEnabled(False)  # Placeholder
        tags_layout.addWidget(connect_btn)
        form_layout.addRow("Synthesis Tags:", tags_layout)

        # Checkboxes
        check_layout = QVBoxLayout()
        self.is_working_question_check = QCheckBox("Mark as Working Question")
        self.is_working_question_check.setChecked(self.data.get("is_working_question", False))
        # REMOVED: self.include_in_summary_check
        check_layout.addWidget(self.is_working_question_check)
        form_layout.addRow("", check_layout)

        main_layout.addLayout(form_layout)

        # Standard OK/Cancel buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

    def _populate_outline_combo(self, outline_items, combo_widget, indent_level=0):
        """Recursively populates the QComboBox with indented outline items."""
        indent = "  " * indent_level
        for item in outline_items:
            # Add this item
            combo_widget.addItem(f"{indent}{item['section_title']}", item['id'])

            # Recursively add its children
            children = item.get('children', [])  # We need to modify get_reading_outline to fetch children
            if children:
                self._populate_outline_combo(children, combo_widget, indent_level + 1)

    def get_data(self):
        """Returns the collected data in a dictionary."""
        parent_data = self.parent_combo.currentData()
        outline_data = self.where_combo.currentData()

        return {
            "question_text": self.question_text_edit.toPlainText().strip(),
            "nickname": self.nickname_edit.text().strip(),
            "type": "Stated" if self.type_stated_radio.isChecked() else "Inferred",
            "question_category": self.category_combo.currentText(),
            "scope": self.scope_combo.currentText(),
            # "reading_has_parts": (removed)
            "parent_id": parent_data,
            "outline_id": outline_data,  # Changed from where_in_book
            "pages": self.pages_edit.text().strip(),
            "why_question": self.why_question_edit.toPlainText().strip(),
            "synthesis_tags": self.tags_edit.toPlainText().strip(),  # Placeholder
            "is_working_question": self.is_working_question_check.isChecked(),
            # "include_in_summary": (removed)
        }