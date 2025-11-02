from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel,
    QComboBox, QDialogButtonBox
)
from PySide6.QtCore import Qt


class MoveProjectDialog(QDialog):
    """
    PySide6 port of the MoveProjectDialog.
    Asks which class to move a project to, or to root.
    """

    def __init__(self, all_classes, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Move Project")

        # This will store the result
        self.new_parent_id = None

        main_layout = QVBoxLayout(self)

        label = QLabel("Move this project to:")
        main_layout.addWidget(label)

        self.class_combo = QComboBox()
        self.class_combo.setFixedWidth(300)

        # This dictionary will map the combobox text back to the ID
        self.class_options = {"Standalone Project (Root)": None}

        # Add root option first
        self.class_combo.addItem("Standalone Project (Root)", userData=None)

        # Add all other classes
        for class_item in all_classes:
            self.class_options[class_item['name']] = class_item['id']
            self.class_combo.addItem(class_item['name'], userData=class_item['id'])

        main_layout.addWidget(self.class_combo)

        # Standard OK/Cancel buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        main_layout.addStretch()
        main_layout.addWidget(self.button_box)

    def accept(self):
        """Called when OK is clicked. Saves the selected ID."""
        # Get the 'userData' we stored for the selected item
        self.new_parent_id = self.class_combo.currentData()
        super().accept()
