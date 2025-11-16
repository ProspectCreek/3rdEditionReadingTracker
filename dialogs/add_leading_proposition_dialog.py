# dialogs/add_leading_proposition_dialog.py
import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QTextEdit,
    QComboBox, QDialogButtonBox, QWidget, QHBoxLayout, QPushButton,
    QLabel, QMessageBox
)
from PySide6.QtCore import Qt, Slot

try:
    from dialogs.connect_tags_dialog import ConnectTagsDialog
except ImportError:
    print("Error: Could not import ConnectTagsDialog")
    ConnectTagsDialog = None


class AddLeadingPropositionDialog(QDialog):
    """
    Dialog for adding or editing a 'Leading Proposition'
    that is specific to a single reading.
    """

    def __init__(self, db_manager, project_id, reading_id, outline_items, current_data=None, parent=None):
        super().__init__(parent)

        self.db = db_manager
        self.project_id = project_id
        self.reading_id = reading_id
        self.outline_items = outline_items
        self.current_data = current_data if current_data else {}

        self.setWindowTitle("Edit Proposition" if current_data else "Add Proposition")
        self.setMinimumWidth(500)

        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        # --- Proposition Text ---
        self.proposition_text_edit = QTextEdit()
        self.proposition_text_edit.setMinimumHeight(80)
        self.proposition_text_edit.setPlaceholderText("Enter the proposition...")
        self.proposition_text_edit.setText(self.current_data.get("proposition_text", ""))
        form_layout.addRow("Proposition:", self.proposition_text_edit)

        # --- Nickname ---
        self.nickname_edit = QLineEdit()
        self.nickname_edit.setPlaceholderText("Optional short name for lists...")
        self.nickname_edit.setText(self.current_data.get("nickname", ""))
        form_layout.addRow("Nickname:", self.nickname_edit)

        # --- Location (Outline) ---
        where_layout = QHBoxLayout()
        where_layout.setContentsMargins(0, 0, 0, 0)
        self.where_combo = QComboBox()
        self._populate_where_combo(self.outline_items)

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
        form_layout.addRow("Location:", where_layout)

        # --- Why this is important ---
        self.why_edit = QTextEdit()
        self.why_edit.setMinimumHeight(60)
        self.why_edit.setPlaceholderText("Why is this proposition important?")
        self.why_edit.setText(self.current_data.get("why_important", ""))
        form_layout.addRow("Why is this important:", self.why_edit)

        # --- Synthesis Tags ---
        tags_layout = QHBoxLayout()
        tags_layout.setContentsMargins(0, 0, 0, 0)
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("e.g., #gratitude, #leadership")
        self.tags_edit.setText(self.current_data.get("synthesis_tags", ""))
        connect_btn = QPushButton("Connect...")

        if self.db and self.project_id is not None and ConnectTagsDialog:
            connect_btn.setEnabled(True)
            connect_btn.clicked.connect(self._open_connect_tags_dialog)
        else:
            connect_btn.setEnabled(False)
            connect_btn.setToolTip("Database connection not available or dialog not found")

        tags_layout.addWidget(self.tags_edit)
        tags_layout.addWidget(connect_btn)
        form_layout.addRow("Synthesis Tags:", tags_layout)

        main_layout.addLayout(form_layout)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

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
            "proposition_text": self.proposition_text_edit.toPlainText().strip(),
            "nickname": self.nickname_edit.text().strip(),
            "outline_id": self.where_combo.currentData(),
            "pages": self.page_edit.text().strip(),
            "why_important": self.why_edit.toPlainText().strip(),
            "synthesis_tags": self.tags_edit.text().strip(),
        }

    @Slot()
    def _open_connect_tags_dialog(self):
        if not self.db or self.project_id is None:
            QMessageBox.warning(self, "Error", "Database connection is not available.")
            return
        if not ConnectTagsDialog:
            QMessageBox.critical(self, "Error", "ConnectTagsDialog could not be loaded.")
            return

        try:
            all_project_tags = self.db.get_project_tags(self.project_id)
            current_tags_text = self.tags_edit.text().strip()
            selected_tag_names = [tag.strip() for tag in current_tags_text.split(',') if tag.strip()]

            dialog = ConnectTagsDialog(all_project_tags, selected_tag_names, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                new_names = dialog.get_selected_tag_names()
                self.tags_edit.setText(", ".join(new_names))

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open tag connector: {e}")