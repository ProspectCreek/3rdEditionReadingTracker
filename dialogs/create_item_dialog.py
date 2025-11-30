from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit,
    QCheckBox, QDialogButtonBox, QWidget, QHBoxLayout
)
from PySide6.QtCore import Qt


class CreateItemDialog(QDialog):
    """
    Asks for an item name and configuration.
    Now includes checks for both Assignment and Research status for projects.
    """

    def __init__(self, item_type, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Create New {item_type.capitalize()}")
        self.item_type = item_type

        # These will store the results
        self.name = ""
        self.is_assignment = 1  # Default to 'Yes'
        self.is_research = 0  # Default to 'No'

        main_layout = QVBoxLayout(self)

        # Name Entry
        name_label = QLabel(f"Enter {item_type} name:")
        self.name_entry = QLineEdit()
        self.name_entry.setFixedWidth(300)  # Set a reasonable width

        main_layout.addWidget(name_label)
        main_layout.addWidget(self.name_entry)

        if self.item_type == 'project':
            # Assignment Checkbox
            self.assignment_check = QCheckBox("For Assignment")
            self.assignment_check.setChecked(True)  # Default to Yes

            # Research Checkbox
            self.research_check = QCheckBox("Research Project")
            self.research_check.setChecked(False)  # Default to No

            # Add some vertical spacing
            main_layout.addSpacing(10)
            main_layout.addWidget(self.assignment_check)
            main_layout.addWidget(self.research_check)

        else:  # It's a 'class'
            self.is_assignment = 0
            self.is_research = 0

        # Standard OK/Cancel buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        main_layout.addStretch()  # Add space before buttons
        main_layout.addWidget(self.button_box)

        self.name_entry.setFocus()

    def accept(self):
        """
        Called when OK is clicked. Validates and saves the data.
        """
        self.name = self.name_entry.text().strip()
        if not self.name:
            return

        if self.item_type == 'project':
            self.is_assignment = 1 if self.assignment_check.isChecked() else 0
            self.is_research = 1 if self.research_check.isChecked() else 0

        super().accept()  # This closes the dialog with QDialog.Accepted