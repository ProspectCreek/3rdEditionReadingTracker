# prospectcreek/3rdeditionreadingtracker/3rdEditionReadingTracker-d0eaa6c33c524aa054deaa3e5b81207eb93ba7d2/dialogs/add_theory_dialog.py

import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QTextEdit,
    QComboBox, QRadioButton, QCheckBox, QDialogButtonBox,
    QWidget, QHBoxLayout, QPushButton, QLabel, QMessageBox
)
from PySide6.QtCore import Qt, Slot

try:
    from dialogs.connect_tags_dialog import ConnectTagsDialog
except ImportError:
    print("Error: Could not import ConnectTagsDialog")
    ConnectTagsDialog = None


class AddTheoryDialog(QDialog):
    """
    Dialog for adding or editing a 'Theory'
    that is specific to a single reading.
    (Based on screenshot image_275983.png)
    """

    def __init__(self, db_manager, project_id, reading_id, outline_items, current_data=None, parent=None):
        super().__init__(parent)

        self.db = db_manager
        self.project_id = project_id
        self.reading_id = reading_id
        self.outline_items = outline_items
        self.current_data = current_data if current_data else {}

        self.setWindowTitle("Edit Theory" if current_data else "Add Theory")
        self.setMinimumWidth(550)

        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        # --- Theory Name ---
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter the theory name...")
        self.name_edit.setText(self.current_data.get("theory_name", ""))
        form_layout.addRow("Theory Name:", self.name_edit)

        # --- Theory Author ---
        self.author_edit = QLineEdit()
        self.author_edit.setPlaceholderText("e.g., Smith (2020) or 'First Principles'")
        self.author_edit.setText(self.current_data.get("theory_author", ""))
        form_layout.addRow("Theory Author:", self.author_edit)

        # --- Year ---
        self.year_edit = QLineEdit()
        self.year_edit.setFixedWidth(80)
        self.year_edit.setText(self.current_data.get("year", ""))
        form_layout.addRow("Year:", self.year_edit)

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

        # --- Description ---
        self.description_edit = QTextEdit()
        self.description_edit.setMinimumHeight(80)
        self.description_edit.setPlaceholderText("Enter the theory's description...")
        self.description_edit.setPlainText(self.current_data.get("description", ""))
        form_layout.addRow("Description:", self.description_edit)

        # --- Purpose ---
        self.purpose_edit = QTextEdit()
        self.purpose_edit.setMinimumHeight(80)
        self.purpose_edit.setPlaceholderText("What is the purpose of this theory in the reading?")
        self.purpose_edit.setPlainText(self.current_data.get("purpose", ""))
        form_layout.addRow("Purpose:", self.purpose_edit)

        # --- Notes ---
        self.notes_edit = QTextEdit()
        self.notes_edit.setMinimumHeight(60)
        self.notes_edit.setPlaceholderText("Additional notes...")
        self.notes_edit.setPlainText(self.current_data.get("notes", ""))
        form_layout.addRow("Notes:", self.notes_edit)
        # --- FIELD IS NOW ENABLED ---

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

        # --- Standard OK/Cancel buttons ---
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
            "theory_name": self.name_edit.text().strip(),
            "theory_author": self.author_edit.text().strip(),
            "year": self.year_edit.text().strip(),
            "outline_id": self.where_combo.currentData(),
            "pages": self.page_edit.text().strip(),
            "description": self.description_edit.toPlainText().strip(),
            "purpose": self.purpose_edit.toPlainText().strip(),
            "notes": self.notes_edit.toPlainText().strip(),  # <-- Will now be saved
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