# prospectcreek/3rdeditionreadingtracker/3rdEditionReadingTracker-d0eaa6c33c524aa054deaa3e5b81207eb93ba7d2/dialogs/add_argument_dialog.py

import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QTextEdit,
    QComboBox, QCheckBox, QDialogButtonBox,
    QWidget, QHBoxLayout, QPushButton, QLabel, QMessageBox,
    QScrollArea, QFrame
)
from PySide6.QtCore import Qt, Slot, Signal

# --- NEW: Import ConnectTagsDialog ---
try:
    from dialogs.connect_tags_dialog import ConnectTagsDialog
except ImportError:
    print("Error: Could not import ConnectTagsDialog")
    ConnectTagsDialog = None
# --- END NEW ---


class EvidenceWidget(QFrame):
    """
    A widget representing a single piece of evidence for an argument.
    """
    deleteRequested = Signal(QWidget)

    def __init__(self, reading_id, outline_items, parent=None):
        super().__init__(parent)
        self.reading_id = reading_id
        self.outline_items = outline_items
        self.setFrameShape(QFrame.Shape.StyledPanel)

        main_layout = QVBoxLayout(self)

        # --- Top row: Radio button and Delete button ---
        top_layout = QHBoxLayout()
        self.select_radio = QCheckBox("Select to Remove") # Changed to Checkbox for logic consistency, though prompt didn't ask. Logic remains same.
        top_layout.addWidget(self.select_radio)
        top_layout.addStretch()
        self.delete_btn = QPushButton("-")
        self.delete_btn.setToolTip("Remove this evidence")
        self.delete_btn.setFixedSize(24, 24)
        # --- FIX: Style to fix blank button ---
        self.delete_btn.setStyleSheet("padding: 0px; font-weight: bold; font-size: 14px;")
        # --- END FIX ---
        self.delete_btn.clicked.connect(lambda: self.deleteRequested.emit(self))
        top_layout.addWidget(self.delete_btn)
        main_layout.addLayout(top_layout)

        # --- Form ---
        form_layout = QFormLayout()
        form_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)

        # Location (Outline)
        where_layout = QHBoxLayout()
        self.where_combo = QComboBox()
        self._populate_where_combo(self.outline_items)
        self.page_edit = QLineEdit()
        self.page_edit.setPlaceholderText("e.g., 10-12")
        self.page_edit.setFixedWidth(60)
        where_layout.addWidget(self.where_combo)
        where_layout.addWidget(QLabel("Page(s):"))
        where_layout.addWidget(self.page_edit)
        form_layout.addRow("Related Part:", where_layout)

        # Argument (Text)
        self.argument_text_edit = QLineEdit()
        self.argument_text_edit.setPlaceholderText("The evidence/argument text")
        form_layout.addRow("Argument:", self.argument_text_edit)

        # Reading Text (Quote)
        self.reading_text_edit = QTextEdit()
        self.reading_text_edit.setPlaceholderText("Enter the direct quote from the reading...")
        self.reading_text_edit.setMinimumHeight(60)
        form_layout.addRow("Reading Text:", self.reading_text_edit)

        # Role in Argument - CHANGED TO COMBOBOX
        self.role_combo = QComboBox()
        self.role_combo.addItems([
            "States Claim",
            "Justifies Claim",
            "Limits Claim",
            "Contradicts Claim"
        ])
        form_layout.addRow("Role in Argument:", self.role_combo)

        # Evidence Type - CHANGED TO COMBOBOX
        self.type_combo = QComboBox()
        self.type_combo.addItems([
            "Reasoning",
            "Example",
            "Authority",
            "Data"
        ])
        form_layout.addRow("Evidence Type:", self.type_combo)

        # Status - CHANGED TO COMBOBOX
        self.status_combo = QComboBox()
        self.status_combo.addItems([
            "Solved",
            "Partially Solved",
            "Unsolved"
        ])
        form_layout.addRow("Status:", self.status_combo)

        # Rationale
        self.rationale_edit = QTextEdit()
        self.rationale_edit.setMinimumHeight(60)
        self.rationale_edit.setPlaceholderText("Rationale for status...")
        form_layout.addRow("Rationale:", self.rationale_edit)

        main_layout.addLayout(form_layout)

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

    def is_selected_for_removal(self):
        return self.select_radio.isChecked()

    def get_data(self):
        """Returns all data from the dialog fields in a dictionary."""
        return {
            "outline_id": self.where_combo.currentData(),
            "pages_text": self.page_edit.text().strip(),
            "argument_text": self.argument_text_edit.text().strip(),
            "reading_text": self.reading_text_edit.toPlainText().strip(),
            "role_in_argument": self.role_combo.currentText(), # <-- Combo
            "evidence_type": self.type_combo.currentText(),    # <-- Combo
            "status": self.status_combo.currentText(),         # <-- Combo
            "rationale_text": self.rationale_edit.toPlainText().strip(),
        }

    def set_data(self, data):
        """Populates the widget fields from a data dictionary."""
        current_outline_id = data.get("outline_id")
        if current_outline_id:
            idx = self.where_combo.findData(current_outline_id)
            if idx != -1:
                self.where_combo.setCurrentIndex(idx)

        self.page_edit.setText(data.get("pages_text", ""))
        self.argument_text_edit.setText(data.get("argument_text", ""))
        self.reading_text_edit.setPlainText(data.get("reading_text", ""))
        self.rationale_edit.setPlainText(data.get("rationale_text", ""))

        # Set Combos
        self.role_combo.setCurrentText(data.get("role_in_argument", "States Claim"))
        self.type_combo.setCurrentText(data.get("evidence_type", "Reasoning"))
        self.status_combo.setCurrentText(data.get("status", "Solved"))


class AddArgumentDialog(QDialog):
    """
    Dialog for adding or editing a 'Argument' and its evidence.
    """

    def __init__(self, db, project_id, reading_id, outline_items, driving_questions, current_data=None, parent=None):
        super().__init__(parent)

        self.db = db
        self.project_id = project_id
        self.reading_id = reading_id
        self.outline_items = outline_items
        self.driving_questions = driving_questions
        self.current_data = current_data if current_data else {}
        self.evidence_widgets = []

        self.setWindowTitle("Edit Argument" if current_data else "Add Argument")
        self.setMinimumWidth(700)
        self.setMinimumHeight(800)

        main_layout = QVBoxLayout(self)

        # --- Top Form ---
        top_form_layout = QFormLayout()

        self.claim_edit = QLineEdit()
        self.claim_edit.setPlaceholderText("Enter the claim...")
        top_form_layout.addRow("Claim:", self.claim_edit)

        self.because_edit = QLineEdit()
        self.because_edit.setPlaceholderText("Enter the 'because' statement...")
        top_form_layout.addRow("Because:", self.because_edit)

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
        top_form_layout.addRow("Addresses which Question:", self.dq_combo)

        # --- NEW: Synthesis Tags ---
        tags_layout = QHBoxLayout()
        tags_layout.setContentsMargins(0, 0, 0, 0)
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("e.g., #gratitude, #leadership")
        connect_btn = QPushButton("Connect...")

        if self.db and self.project_id is not None and ConnectTagsDialog:
            connect_btn.setEnabled(True)
            connect_btn.clicked.connect(self._open_connect_tags_dialog)
        else:
            connect_btn.setEnabled(False)
            connect_btn.setToolTip("Database connection not available or dialog not found")

        tags_layout.addWidget(self.tags_edit)
        tags_layout.addWidget(connect_btn)
        top_form_layout.addRow("Synthesis Tags:", tags_layout)
        # --- END NEW ---

        self.is_insight_check = QCheckBox("Mark as Insight")
        top_form_layout.addRow("", self.is_insight_check)

        main_layout.addLayout(top_form_layout)

        # --- Evidence Area ---
        main_layout.addWidget(QLabel("<b>Evidence</b>"))

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        self.evidence_layout = QVBoxLayout(scroll_widget)
        self.evidence_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll_area.setWidget(scroll_widget)

        main_layout.addWidget(scroll_area, 1)  # Give stretch

        # --- Evidence Buttons ---
        ev_btn_layout = QHBoxLayout()
        ev_btn_layout.addStretch()
        self.add_evidence_btn = QPushButton("Add Additional Evidence")
        self.remove_evidence_btn = QPushButton("Remove Selected Evidence")
        ev_btn_layout.addWidget(self.add_evidence_btn)
        ev_btn_layout.addWidget(self.remove_evidence_btn)
        main_layout.addLayout(ev_btn_layout)

        # --- Dialog Buttons ---
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        main_layout.addWidget(self.button_box)

        # --- Connections ---
        self.add_evidence_btn.clicked.connect(self._add_evidence_widget)
        self.remove_evidence_btn.clicked.connect(self._remove_selected_evidence)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        # --- Load Data ---
        if self.current_data:
            self._set_data(self.current_data)
        else:
            # Add one blank evidence widget to start
            self._add_evidence_widget()

    def _add_evidence_widget(self, data=None):
        """Adds a new EvidenceWidget to the scroll area."""
        widget = EvidenceWidget(self.reading_id, self.outline_items, self)
        if data:
            widget.set_data(data)
        widget.deleteRequested.connect(self._on_delete_evidence_widget)
        self.evidence_layout.addWidget(widget)
        self.evidence_widgets.append(widget)

    @Slot(QWidget)
    def _on_delete_evidence_widget(self, widget):
        """Slot to handle direct deletion from the widget."""
        if widget in self.evidence_widgets:
            widget.deleteLater()
            self.evidence_widgets.remove(widget)

    @Slot()
    def _remove_selected_evidence(self):
        """Removes all evidence widgets that are checked."""
        widgets_to_remove = [w for w in self.evidence_widgets if w.is_selected_for_removal()]
        if not widgets_to_remove:
            QMessageBox.information(self, "Remove", "No evidence items were selected for removal.")
            return

        if len(widgets_to_remove) == len(self.evidence_widgets):
            QMessageBox.warning(self, "Remove",
                                "You cannot remove all evidence items. An argument must have at least one.")
            return

        for widget in widgets_to_remove:
            self._on_delete_evidence_widget(widget)

    def _set_data(self, data):
        """Populates the entire dialog from existing data."""
        self.claim_edit.setText(data.get("claim_text", ""))
        self.because_edit.setText(data.get("because_text", ""))
        self.is_insight_check.setChecked(bool(data.get("is_insight", 0)))
        self.tags_edit.setText(data.get("synthesis_tags", ""))

        dq_id = data.get("driving_question_id")
        if dq_id:
            idx = self.dq_combo.findData(dq_id)
            if idx != -1:
                self.dq_combo.setCurrentIndex(idx)

        for ev_data in data.get("evidence", []):
            self._add_evidence_widget(ev_data)

        # Ensure at least one widget exists
        if not self.evidence_widgets:
            self._add_evidence_widget()

    def get_data(self):
        """Returns all data from the dialog fields in a dictionary."""

        evidence_list = [w.get_data() for w in self.evidence_widgets]

        return {
            "claim_text": self.claim_edit.text().strip(),
            "because_text": self.because_edit.text().strip(),
            "driving_question_id": self.dq_combo.currentData(),
            "is_insight": self.is_insight_check.isChecked(),
            "synthesis_tags": self.tags_edit.text().strip(),
            "evidence": evidence_list
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
            all_project_tags = self.db.get_project_tags(self.project_id)
            current_tags_text = self.tags_edit.text().strip()
            selected_tag_names = [tag.strip() for tag in current_tags_text.split(',') if tag.strip()]

            dialog = ConnectTagsDialog(all_project_tags, selected_tag_names, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                new_names = dialog.get_selected_tag_names()
                self.tags_edit.setText(", ".join(new_names))

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open tag connector: {e}")
    # --- END NEW ---