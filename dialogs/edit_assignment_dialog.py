from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel,
    QCheckBox, QDialogButtonBox, QWidget, QHBoxLayout
)
from PySide6.QtCore import Qt


class EditProjectStatusDialog(QDialog):
    """
    Allows editing 'is_assignment', 'is_research', and 'is_annotated_bib' status.
    """

    def __init__(self, current_assignment_status, current_research_status, current_bib_status, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Project Configuration")

        # Results
        self.new_assignment_status = current_assignment_status
        self.new_research_status = current_research_status
        self.new_bib_status = current_bib_status

        main_layout = QVBoxLayout(self)

        label = QLabel("Project Type Configuration:")
        main_layout.addWidget(label)

        # Checkbox Widgets
        self.assignment_check = QCheckBox("For Assignment")
        self.assignment_check.setChecked(bool(current_assignment_status))

        self.research_check = QCheckBox("Research Project")
        self.research_check.setChecked(bool(current_research_status))

        self.bib_check = QCheckBox("Create Annotated Bibliography")
        self.bib_check.setChecked(bool(current_bib_status))

        main_layout.addWidget(self.assignment_check)
        main_layout.addWidget(self.research_check)
        main_layout.addWidget(self.bib_check)

        # Standard OK/Cancel buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        main_layout.addStretch()
        main_layout.addWidget(self.button_box)

    def accept(self):
        """Called when OK is clicked. Saves the data."""
        self.new_assignment_status = 1 if self.assignment_check.isChecked() else 0
        self.new_research_status = 1 if self.research_check.isChecked() else 0
        self.new_bib_status = 1 if self.bib_check.isChecked() else 0
        super().accept()