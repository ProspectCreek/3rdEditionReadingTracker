# dialogs/edit_driving_question_dialog.py
import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QTextEdit,
    QComboBox, QCheckBox, QDialogButtonBox,
    QWidget, QHBoxLayout, QPushButton, QLabel, QMessageBox
)
from PySide6.QtCore import Qt, Slot

# --- NEW: Import ConnectTagsDialog ---
try:
    from dialogs.connect_tags_dialog import ConnectTagsDialog
except ImportError:
    print("Error: Could not import ConnectTagsDialog")
    ConnectTagsDialog = None


# --- END NEW ---


class EditDrivingQuestionDialog(QDialog):
    """
    Dialog for adding or editing a driving question.
    """

    def __init__(self, all_questions, outline_items, db_manager=None, project_id=None, current_question_data=None,
                 parent=None):
        super().__init__(parent)

        self.current_data = current_question_data if current_question_data else {}
        self.all_questions = all_questions
        self.outline_items = outline_items
        self.db = db_manager  # <-- ADD
        self.project_id = project_id  # <-- ADD

        self.setWindowTitle("Edit Driving Question")
        if not self.current_data:
            self.setWindowTitle("Add Driving Question")

        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        # --- Purpose Label ---
        purpose_label = QLabel(
            "Purpose: If the author never wrote this book, what puzzle would remain unsolved? "
            "That's your driving question."
        )
        purpose_label.setWordWrap(True)
        purpose_label.setStyleSheet("font-style: italic; color: #555;")
        main_layout.addWidget(purpose_label)

        # --- Question Text ---
        self.question_text_edit = QTextEdit()
        self.question_text_edit.setMinimumHeight(60)
        self.question_text_edit.setPlaceholderText("Enter the driving question here...")
        self.question_text_edit.setText(self.current_data.get("question_text", ""))
        form_layout.addRow("Driving Question:", self.question_text_edit)

        # --- Nickname ---
        self.nickname_edit = QLineEdit()
        self.nickname_edit.setPlaceholderText("e.g., 'The Gratitude Puzzle'")
        self.nickname_edit.setText(self.current_data.get("nickname", ""))
        form_layout.addRow("Nickname:", self.nickname_edit)

        # --- Type (Stated/Inferred) - CHANGED TO COMBOBOX ---
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Stated", "Inferred"])

        # Set current value or default to Inferred
        current_type = self.current_data.get("type", "Inferred")
        self.type_combo.setCurrentText(current_type)

        form_layout.addRow("Type:", self.type_combo)

        # --- Question Category ---
        self.category_combo = QComboBox()
        self.category_combo.addItems([
            "Descriptive (what/which)",
            "Explanatory (why/how)",
            "Evaluative (true/good)",
            "Prescriptive (what should we do)"
        ])
        self.category_combo.setCurrentText(self.current_data.get("question_category", "Explanatory (why/how)"))
        form_layout.addRow("Question Category:", self.category_combo)

        # --- Scope ---
        scope_layout = QHBoxLayout()
        scope_layout.setContentsMargins(0, 0, 0, 0)
        self.scope_combo = QComboBox()
        self.scope_combo.addItems([
            "Global",
            "Part",
            "Chapter",
            "Section"
        ])
        self.scope_combo.setCurrentText(self.current_data.get("scope", "Global"))
        scope_layout.addWidget(self.scope_combo)
        scope_layout.addStretch()
        form_layout.addRow("Scope:", scope_layout)

        # --- Parent Question ---
        self.parent_combo = QComboBox()
        self._populate_parent_combo(self.all_questions, self.current_data.get("id"))

        # Set current parent
        current_parent_id = self.current_data.get("parent_id")
        if current_parent_id:
            idx = self.parent_combo.findData(current_parent_id)
            if idx != -1:
                self.parent_combo.setCurrentIndex(idx)
        form_layout.addRow("Parent:", self.parent_combo)

        # --- Where in Reading (Outline) ---
        where_layout = QHBoxLayout()
        where_layout.setContentsMargins(0, 0, 0, 0)
        self.where_combo = QComboBox()
        self._populate_where_combo(self.outline_items)

        # Set current location
        current_outline_id = self.current_data.get("outline_id")
        if current_outline_id:
            idx = self.where_combo.findData(current_outline_id)
            if idx != -1:
                self.where_combo.setCurrentIndex(idx)

        self.page_edit = QLineEdit()
        self.page_edit.setPlaceholderText("e.g., 10-12")
        self.page_edit.setFixedWidth(60)
        self.page_edit.setText(self.current_data.get("pages", ""))

        where_layout.addWidget(self.where_combo)
        where_layout.addWidget(QLabel("Page(s):"))
        where_layout.addWidget(self.page_edit)
        form_layout.addRow("Where in Reading:", where_layout)

        # --- Why this question ---
        self.why_edit = QTextEdit()
        self.why_edit.setMinimumHeight(60)
        self.why_edit.setPlaceholderText("Why do you think this is the question?")
        self.why_edit.setText(self.current_data.get("why_question", ""))
        form_layout.addRow("Why I think this is the question:", self.why_edit)

        # --- Synthesis Tags ---
        tags_layout = QHBoxLayout()
        tags_layout.setContentsMargins(0, 0, 0, 0)
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("e.g., #gratitude, #leadership")
        self.tags_edit.setText(self.current_data.get("synthesis_tags", ""))
        connect_btn = QPushButton("Connect...")

        # --- MODIFICATION ---
        if self.db and self.project_id is not None and ConnectTagsDialog:
            connect_btn.setEnabled(True)
            connect_btn.clicked.connect(self._open_connect_tags_dialog)
        else:
            connect_btn.setEnabled(False)
            connect_btn.setToolTip("Database connection not available or dialog not found")
        # --- END MODIFICATION ---

        tags_layout.addWidget(self.tags_edit)
        tags_layout.addWidget(connect_btn)
        form_layout.addRow("Synthesis Tags:", tags_layout)

        main_layout.addLayout(form_layout)

        # --- Checkboxes ---
        self.is_working_check = QCheckBox("Mark as Working Question")
        if self.current_data.get("is_working_question"):
            self.is_working_check.setChecked(True)
        main_layout.addWidget(self.is_working_check)

        # --- Standard OK/Cancel buttons ---
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

    def _get_all_descendant_ids(self, all_questions, parent_id):
        """Recursively finds all children and grandchildren IDs."""
        descendant_ids = set()
        # Find direct children
        children = [q for q in all_questions if q.get('parent_id') == parent_id]

        for child in children:
            child_id = child['id']
            if child_id not in descendant_ids:
                descendant_ids.add(child_id)
                # Recursively find children of this child
                descendant_ids.update(self._get_all_descendant_ids(all_questions, child_id))
        return descendant_ids

    def _populate_parent_combo(self, all_questions, current_question_id=None):
        """Populates the parent dropdown, excluding self and descendants."""
        self.parent_combo.addItem("[No Parent]", None)

        # --- FIX: Exclude self and all descendants ---
        ids_to_exclude = set()
        if current_question_id:
            ids_to_exclude.add(current_question_id)
            # Find all children, grandchildren, etc.
            ids_to_exclude.update(self._get_all_descendant_ids(all_questions, current_question_id))
        # --- END FIX ---

        # For now, we only show root-level questions as potential parents
        # A more complex hierarchy might be needed later
        for q in all_questions:
            if q['id'] not in ids_to_exclude:
                display_text = q.get('nickname') or q.get('question_text', 'Untitled Question')
                display_text = display_text[:70] + "..." if len(display_text) > 70 else display_text
                self.parent_combo.addItem(display_text, q['id'])

    def _populate_where_combo(self, outline_items, indent=0):
        """Recursively populates the 'Where in Reading' dropdown."""
        if indent == 0:
            self.where_combo.addItem("[Reading-Level Notes]", None)  # Top-level

        for item in outline_items:
            prefix = "  " * indent
            display_text = f"{prefix} {item['section_title']}"
            self.where_combo.addItem(display_text, item['id'])

            if 'children' in item:
                self._populate_where_combo(item['children'], indent + 1)

    def get_data(self):
        """Returns all data from the dialog fields in a dictionary."""
        return {
            "question_text": self.question_text_edit.toPlainText().strip(),
            "nickname": self.nickname_edit.text().strip(),
            "type": self.type_combo.currentText(),  # <-- Changed from radios to combo
            "question_category": self.category_combo.currentText(),
            "scope": self.scope_combo.currentText(),
            "parent_id": self.parent_combo.currentData(),
            "outline_id": self.where_combo.currentData(),
            "pages": self.page_edit.text().strip(),
            "why_question": self.why_edit.toPlainText().strip(),
            "synthesis_tags": self.tags_edit.text().strip(),
            "is_working_question": self.is_working_check.isChecked()
        }

    # --- NEW: Slot to open tag connector ---
    @Slot()
    def _open_connect_tags_dialog(self):
        if not self.db or self.project_id is None:
            QMessageBox.warning(self, "Error", "Database connection is not available.")
            return
        if not ConnectTagsDialog:
            QMessageBox.critical(self, "Error", "ConnectTagsDialog could not be loaded.")
            return

        try:
            # 1. Get all tags for this project
            all_project_tags = self.db.get_project_tags(self.project_id)

            # 2. Get currently selected tags from the line edit
            current_tags_text = self.tags_edit.text().strip()
            selected_tag_names = [tag.strip() for tag in current_tags_text.split(',') if tag.strip()]

            # 3. Open the dialog
            dialog = ConnectTagsDialog(all_project_tags, selected_tag_names, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # 4. Update the line edit with the new tag list
                new_names = dialog.get_selected_tag_names()
                self.tags_edit.setText(", ".join(new_names))

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open tag connector: {e}")
    # --- END NEW ---