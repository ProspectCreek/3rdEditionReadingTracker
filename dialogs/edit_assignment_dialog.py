from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel,
    QCheckBox, QDialogButtonBox, QWidget, QHBoxLayout
)
from PySide6.QtCore import Qt


class EditProjectStatusDialog(QDialog):
    """
    Allows editing both 'is_assignment' and 'is_research' status.
    Replaces the old radio buttons with checkboxes.
    """

    def __init__(self, current_assignment_status, current_research_status, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Assignment/Research Status")

        # Results
        self.new_assignment_status = current_assignment_status
        self.new_research_status = current_research_status

        main_layout = QVBoxLayout(self)

        label = QLabel("Project Type Configuration:")
        main_layout.addWidget(label)

        # Checkbox Widget
        self.assignment_check = QCheckBox("For Assignment")
        self.assignment_check.setChecked(bool(current_assignment_status))

        self.research_check = QCheckBox("Research Project")
        self.research_check.setChecked(bool(current_research_status))

        main_layout.addWidget(self.assignment_check)
        main_layout.addWidget(self.research_check)

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
        super().accept()