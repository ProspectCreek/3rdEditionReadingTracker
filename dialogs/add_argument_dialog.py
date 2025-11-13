# prospectcreek/3rdeditionreadingtracker/3rdEditionReadingTracker-d0eaa6c33c524aa054deaa3e5b81207eb93ba7d2/dialogs/add_argument_dialog.py

import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QTextEdit,
    QComboBox, QRadioButton, QCheckBox, QDialogButtonBox,
    QWidget, QHBoxLayout, QPushButton, QLabel, QMessageBox,
    QScrollArea, QFrame
)
from PySide6.QtCore import Qt, Slot, Signal


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
        self.select_radio = QRadioButton("Select to Remove")
        top_layout.addWidget(self.select_radio)
        top_layout.addStretch()
        self.delete_btn = QPushButton("-")
        self.delete_btn.setToolTip("Remove this evidence")
        self.delete_btn.setFixedSize(24, 24)
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

        # Role in Argument
        role_grid = QWidget()
        role_layout = QHBoxLayout(role_grid)
        role_layout.setContentsMargins(0, 0, 0, 0)
        self.role_radios = {
            "States Claim": QRadioButton("States Claim"),
            "Justifies Claim": QRadioButton("Justifies Claim"),
            "Limits Claim": QRadioButton("Limits Claim"),
            "Contradicts Claim": QRadioButton("Contradicts Claim")
        }
        current_role = None  # Default
        checked_one = False
        for text, radio in self.role_radios.items():
            role_layout.addWidget(radio)
            if text == current_role:
                radio.setChecked(True)
                checked_one = True
        if not checked_one:
            self.role_radios["States Claim"].setChecked(True)  # Default
        role_layout.addStretch()
        form_layout.addRow("Role in Argument:", role_grid)

        # Evidence Type
        type_grid = QWidget()
        type_layout = QHBoxLayout(type_grid)
        type_layout.setContentsMargins(0, 0, 0, 0)
        self.type_radios = {
            "Reasoning": QRadioButton("Reasoning"),
            "Example": QRadioButton("Example"),
            "Authority": QRadioButton("Authority"),
            "Data": QRadioButton("Data")
        }
        current_type = None  # Default
        checked_one = False
        for text, radio in self.type_radios.items():
            type_layout.addWidget(radio)
            if text == current_type:
                radio.setChecked(True)
                checked_one = True
        if not checked_one:
            self.type_radios["Reasoning"].setChecked(True)  # Default
        type_layout.addStretch()
        form_layout.addRow("Evidence Type:", type_grid)

        # Status
        status_grid = QWidget()
        status_layout = QHBoxLayout(status_grid)
        status_layout.setContentsMargins(0, 0, 0, 0)
        self.status_radios = {
            "Solved": QRadioButton("Solved"),
            "Partially Solved": QRadioButton("Partially Solved"),
            "Unsolved": QRadioButton("Unsolved")
        }
        current_status = None  # Default
        checked_one = False
        for text, radio in self.status_radios.items():
            status_layout.addWidget(radio)
            if text == current_status:
                radio.setChecked(True)
                checked_one = True
        if not checked_one:
            self.status_radios["Solved"].setChecked(True)  # Default
        status_layout.addStretch()
        form_layout.addRow("Status:", status_grid)

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

        def get_radio_selection(radio_group):
            for text, radio in radio_group.items():
                if radio.isChecked():
                    return text
            return None

        return {
            "outline_id": self.where_combo.currentData(),
            "pages_text": self.page_edit.text().strip(),
            "argument_text": self.argument_text_edit.text().strip(),
            "reading_text": self.reading_text_edit.toPlainText().strip(),
            "role_in_argument": get_radio_selection(self.role_radios),
            "evidence_type": get_radio_selection(self.type_radios),
            "status": get_radio_selection(self.status_radios),
            "rationale_text": self.rationale_edit.toPlainText().strip(),
        }

    def set_data(self, data):
        """Populates the widget fields from a data dictionary."""

        def set_radio_selection(radio_group, value):
            for text, radio in radio_group.items():
                if text == value:
                    radio.setChecked(True)
                    return

        current_outline_id = data.get("outline_id")
        if current_outline_id:
            idx = self.where_combo.findData(current_outline_id)
            if idx != -1:
                self.where_combo.setCurrentIndex(idx)

        self.page_edit.setText(data.get("pages_text", ""))
        self.argument_text_edit.setText(data.get("argument_text", ""))
        self.reading_text_edit.setPlainText(data.get("reading_text", ""))
        self.rationale_edit.setPlainText(data.get("rationale_text", ""))

        set_radio_selection(self.role_radios, data.get("role_in_argument"))
        set_radio_selection(self.type_radios, data.get("evidence_type"))
        set_radio_selection(self.status_radios, data.get("status"))


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
            "evidence": evidence_list
        }