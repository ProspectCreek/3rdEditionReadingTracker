from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QTextEdit,
    QDialogButtonBox, QWidget
)
from PySide6.QtCore import Qt


class EditInstructionsDialog(QDialog):
    """
    PySide6 port of the EditInstructionsDialog.
    Allows editing the four instruction fields for the project dashboard.
    """

    def __init__(self, current_instructions, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Project Homepage Instructions")
        self.setMinimumWidth(500)

        self.instructions = current_instructions
        self.result = None  # To store the new values

        main_layout = QVBoxLayout(self)

        self.text_widgets = {}
        fields = [
            ("key_questions_instr", "Key Questions"),
            ("thesis_instr", "Thesis/Argument"),
            ("insights_instr", "Key Insights"),
            ("unresolved_instr", "Unresolved Questions")
        ]

        for field_key, field_label in fields:
            label = QLabel(field_label)
            main_layout.addWidget(label)

            text_widget = QTextEdit()
            text_widget.setAcceptRichText(False)
            text_widget.setPlainText(self.instructions.get(field_key, ""))
            text_widget.setFixedHeight(70)  # Give it a bit of space

            main_layout.addWidget(text_widget)
            self.text_widgets[field_key] = text_widget

        # Standard OK/Cancel buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        main_layout.addStretch()
        main_layout.addWidget(self.button_box)

    def accept(self):
        """Saves the new instruction values to the 'result' attribute."""
        self.result = {
            "key_questions_instr": self.text_widgets["key_questions_instr"].toPlainText(),
            "thesis_instr": self.text_widgets["thesis_instr"].toPlainText(),
            "insights_instr": self.text_widgets["insights_instr"].toPlainText(),
            "unresolved_instr": self.text_widgets["unresolved_instr"].toPlainText()
        }
        super().accept()
