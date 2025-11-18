# dialogs/edit_instructions_dialog.py
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QTextEdit,
    QDialogButtonBox, QWidget, QTabWidget, QFormLayout
)
from PySide6.QtCore import Qt


class EditInstructionsDialog(QDialog):
    """
    PySide6 port of the EditInstructionsDialog.
    Allows editing all instruction fields for the project, organized by tabs.
    """

    def __init__(self, current_instructions, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Tab Instructions")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)  # Make dialog taller

        self.instructions = current_instructions
        self.result = None  # To store the new values
        self.text_widgets = {}  # Store all text widgets

        main_layout = QVBoxLayout(self)

        tab_widget = QTabWidget()
        main_layout.addWidget(tab_widget)

        # --- Tab 1: Project Dashboard ---
        project_tab = QWidget()
        project_layout = QFormLayout(project_tab)
        project_layout.setSpacing(8)
        self.project_fields = [
            ("key_questions_instr", "Key Questions"),
            ("thesis_instr", "Thesis/Argument"),
            ("insights_instr", "Key Insights"),
            ("unresolved_instr", "Unresolved Questions")
        ]
        self._create_form_fields(project_layout, self.project_fields)
        tab_widget.addTab(project_tab, "Project")

        # --- Tab 2: Synthesis ---
        synthesis_tab = QWidget()
        synthesis_layout = QFormLayout(synthesis_tab)
        synthesis_layout.setSpacing(8)
        self.synthesis_fields = [
            ("synthesis_terminology_instr", "My Terminology"),
            ("synthesis_propositions_instr", "My Propositions"),
            ("synthesis_notes_instr", "Synthesis Notes")
        ]
        self._create_form_fields(synthesis_layout, self.synthesis_fields)
        tab_widget.addTab(synthesis_tab, "Synthesis")

        # --- Tab 3: Reading Tabs ---
        reading_tab = QWidget()
        reading_layout = QFormLayout(reading_tab)
        reading_layout.setSpacing(8)
        self.reading_fields = [
            ("reading_dq_instr", "Driving Question"),
            ("reading_lp_instr", "Leading Propositions"),
            ("reading_unity_instr", "Unity"),
            ("reading_elevator_instr", "Elevator Abstract"),
            ("reading_parts_instr", "Parts: Order and Relation"),
            ("reading_key_terms_instr", "Key Terms"),
            ("reading_arguments_instr", "Arguments"),
            ("reading_gaps_instr", "Gaps"),
            ("reading_theories_instr", "Theories"),
            ("reading_dialogue_instr", "Personal Dialogue")
        ]
        self._create_form_fields(reading_layout, self.reading_fields)
        tab_widget.addTab(reading_tab, "Reading")

        # Standard OK/Cancel buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        main_layout.addStretch()
        main_layout.addWidget(self.button_box)

    def _create_form_fields(self, layout, field_list):
        """Helper to create labels and text editors for a list of fields."""
        for field_key, field_label in field_list:
            label = QLabel(field_label)
            text_widget = QTextEdit()
            text_widget.setAcceptRichText(False)
            text_widget.setPlainText(self.instructions.get(field_key, ""))
            text_widget.setFixedHeight(70)  # Give it a bit of space

            layout.addRow(label, text_widget)
            self.text_widgets[field_key] = text_widget

    def accept(self):
        """Saves all new instruction values to the 'result' attribute."""
        self.result = {}
        all_fields = self.project_fields + self.synthesis_fields + self.reading_fields

        for field_key, _ in all_fields:
            if field_key in self.text_widgets:
                self.result[field_key] = self.text_widgets[field_key].toPlainText()

        super().accept()