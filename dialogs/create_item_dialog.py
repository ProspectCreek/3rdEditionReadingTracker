from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit,
    QRadioButton, QDialogButtonBox, QWidget, QHBoxLayout
)
from PySide6.QtCore import Qt


class CreateItemDialog(QDialog):
    """
    PySide6 port of the CreateItemDialog.
    Asks for an item name and (if it's a project)
    if it's an assignment.
    """

    def __init__(self, item_type, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Create New {item_type.capitalize()}")
        self.item_type = item_type

        # These will store the results
        self.name = ""
        self.is_assignment = 1  # Default to 'Yes'

        main_layout = QVBoxLayout(self)

        # Name Entry
        name_label = QLabel(f"Enter {item_type} name:")
        self.name_entry = QLineEdit()
        self.name_entry.setFixedWidth(300)  # Set a reasonable width

        main_layout.addWidget(name_label)
        main_layout.addWidget(self.name_entry)

        if self.item_type == 'project':
            # Assignment Radio Buttons
            assign_label = QLabel("For assignment:")
            main_layout.addWidget(assign_label)

            radio_widget = QWidget()  # Use a widget to hold the HBox
            radio_layout = QHBoxLayout(radio_widget)
            radio_layout.setContentsMargins(0, 0, 0, 0)

            self.yes_radio = QRadioButton("Yes")
            self.yes_radio.setChecked(True)
            self.no_radio = QRadioButton("No")

            radio_layout.addWidget(self.yes_radio)
            radio_layout.addWidget(self.no_radio)
            radio_layout.addStretch()  # Push buttons to the left

            main_layout.addWidget(radio_widget)

        else:  # It's a 'class'
            self.is_assignment = 0  # Classes are not assignments

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
            # You could show a QMessageBox here, but for now just don't close
            return

        if self.item_type == 'project':
            self.is_assignment = 1 if self.yes_radio.isChecked() else 0

        super().accept()  # This closes the dialog with QDialog.Accepted
