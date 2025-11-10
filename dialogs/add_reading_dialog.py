# dialogs/add_reading_dialog.py
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit,
    QDialogButtonBox, QMessageBox
)


class AddReadingDialog(QDialog):
    """
    A dialog to add a new reading, asking for
    Title, Author, and Nickname.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Reading")

        self.title = ""
        self.author = ""
        self.nickname = ""

        main_layout = QVBoxLayout(self)

        # Title
        title_label = QLabel("Title (Required):")
        self.title_entry = QLineEdit()
        main_layout.addWidget(title_label)
        main_layout.addWidget(self.title_entry)

        # Author
        author_label = QLabel("Author (Optional):")
        self.author_entry = QLineEdit()
        main_layout.addWidget(author_label)
        main_layout.addWidget(self.author_entry)

        nickname_label = QLabel("Citation Nickname (Optional):")
        self.nickname_entry = QLineEdit()
        self.nickname_entry.setPlaceholderText("e.g., 'Smith (2020)' or 'Economics Ch. 1'")
        main_layout.addWidget(nickname_label)
        main_layout.addWidget(self.nickname_entry)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        main_layout.addStretch()
        main_layout.addWidget(self.button_box)

        self.title_entry.setFocus()

    def accept(self):
        """Save the values from the text fields before closing."""
        self.title = self.title_entry.text().strip()
        self.author = self.author_entry.text().strip()
        self.nickname = self.nickname_entry.text().strip()

        # --- DEBUG SNIPPET ---
        print(f"[AddReadingDialog.accept] Reading fields:")
        print(f"  > Title: '{self.title}'")
        print(f"  > Author: '{self.author}'")
        print(f"  > Nickname: '{self.nickname}'")
        # --- END DEBUG SNIPPET ---

        if not self.title:
            QMessageBox.warning(self, "Title Required", "The 'Title' field cannot be empty.")
            return  # Don't close the dialog

        super().accept()