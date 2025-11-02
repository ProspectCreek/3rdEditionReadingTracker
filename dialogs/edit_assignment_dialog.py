from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel,
    QRadioButton, QDialogButtonBox, QWidget, QHBoxLayout
)
from PySide6.QtCore import Qt


class EditAssignmentDialog(QDialog):
    """
    PySide6 port of the EditAssignmentDialog.
    Asks to change the 'is_assignment' status.
    """

    def __init__(self, current_status, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Assignment Status")

        # This will store the result
        self.new_status = current_status

        main_layout = QVBoxLayout(self)

        label = QLabel("Is this project for an assignment?")
        main_layout.addWidget(label)

        # Radio Button Widget/Layout
        radio_widget = QWidget()
        radio_layout = QHBoxLayout(radio_widget)
        radio_layout.setContentsMargins(0, 0, 0, 0)

        self.yes_radio = QRadioButton("Yes")
        self.no_radio = QRadioButton("No")

        if current_status == 1:
            self.yes_radio.setChecked(True)
        else:
            self.no_radio.setChecked(True)

        radio_layout.addWidget(self.yes_radio)
        radio_layout.addWidget(self.no_radio)
        radio_layout.addStretch()

        main_layout.addWidget(radio_widget)

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
        self.new_status = 1 if self.yes_radio.isChecked() else 0
        super().accept()
