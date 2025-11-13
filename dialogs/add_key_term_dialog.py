# prospectcreek/3rdeditionreadingtracker/3rdEditionReadingTracker-d0eaa6c33c524aa054deaa3e5b81207eb93ba7d2/dialogs/add_key_term_dialog.py

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


class AddKeyTermDialog(QDialog):
    """
    Dialog for adding or editing a 'Key Term'
    that is specific to a single reading.
    (Based on screenshot image_26e8c6.png)
    """

    def __init__(self, db_manager, project_id, reading_id, outline_items, current_data=None, parent=None):
        super().__init__(parent)

        self.db = db_manager
        self.project_id = project_id
        self.reading_id = reading_id
        self.outline_items = outline_items
        self.current_data = current_data if current_data else {}

        self.setWindowTitle("Edit Key Term" if current_data else "Add Key Term")
        self.setMinimumWidth(550)

        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        # --- Term ---
        self.term_edit = QLineEdit()
        self.term_edit.setPlaceholderText("Enter the key term...")
        self.term_edit.setText(self.current_data.get("term", ""))
        form_layout.addRow("Term:", self.term_edit)

        # --- My Definition ---
        self.definition_edit = QTextEdit()
        self.definition_edit.setMinimumHeight(80)
        self.definition_edit.setPlaceholderText("Enter your definition of the term...")
        self.definition_edit.setText(self.current_data.get("definition", ""))
        form_layout.addRow("My Definition:", self.definition_edit)

        # --- Author's Wording / Citation ---
        quote_label = QLabel("Author's Wording / Citation (Optional)")
        quote_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        main_layout.addLayout(form_layout)
        main_layout.addWidget(quote_label)

        citation_form_layout = QFormLayout()

        # --- MODIFICATION: Changed QLineEdit to QTextEdit ---
        self.quote_edit = QTextEdit()
        self.quote_edit.setPlaceholderText("Enter a direct quote...")
        self.quote_edit.setMinimumHeight(60)  # Allow for multiple lines
        self.quote_edit.setPlainText(self.current_data.get("quote", ""))
        citation_form_layout.addRow("Quote:", self.quote_edit)
        # --- END MODIFICATION ---

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
        citation_form_layout.addRow("Location:", where_layout)

        main_layout.addLayout(citation_form_layout)

        # --- Role in Argument ---
        role_label = QLabel("Role in Argument")
        role_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        main_layout.addWidget(role_label)

        role_grid = QWidget()
        role_layout = QHBoxLayout(role_grid)
        role_layout.setContentsMargins(0, 0, 0, 0)

        self.role_radios = {
            "defines scope": QRadioButton("defines scope"),
            "names mechanism": QRadioButton("names mechanism"),
            "criterion/test": QRadioButton("criterion/test"),
            "assumption": QRadioButton("assumption"),
            "contrast/foil": QRadioButton("contrast/foil"),
            "key variable": QRadioButton("key variable")
        }

        current_role = self.current_data.get("role")
        checked_one = False
        for text, radio in self.role_radios.items():
            role_layout.addWidget(radio)
            if text == current_role:
                radio.setChecked(True)
                checked_one = True

        if not checked_one and self.role_radios:
            self.role_radios["defines scope"].setChecked(True)  # Default

        role_layout.addStretch()
        main_layout.addWidget(role_grid)

        # --- Synthesis Tags & Notes ---
        other_form_layout = QFormLayout()

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
        other_form_layout.addRow("Synthesis Tags:", tags_layout)

        self.notes_edit = QTextEdit()
        self.notes_edit.setMinimumHeight(60)
        self.notes_edit.setPlaceholderText("Additional notes...")
        self.notes_edit.setText(self.current_data.get("notes", ""))
        other_form_layout.addRow("Notes:", self.notes_edit)

        main_layout.addLayout(other_form_layout)

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

        selected_role = "defines scope"  # Default
        for text, radio in self.role_radios.items():
            if radio.isChecked():
                selected_role = text
                break

        return {
            "term": self.term_edit.text().strip(),
            "definition": self.definition_edit.toPlainText().strip(),
            # --- MODIFICATION: Use toPlainText() ---
            "quote": self.quote_edit.toPlainText().strip(),
            # --- END MODIFICATION ---
            "outline_id": self.where_combo.currentData(),
            "pages": self.page_edit.text().strip(),
            "role": selected_role,
            "synthesis_tags": self.tags_edit.text().strip(),
            "notes": self.notes_edit.toPlainText().strip(),
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