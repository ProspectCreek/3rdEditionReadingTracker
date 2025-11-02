from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit,
    QDialogButtonBox
)


class AddReadingDialog(QDialog):
    """
    A dialog to add a new reading, asking for
    Title and Author.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Reading")

        self.title = ""
        self.author = ""

        main_layout = QVBoxLayout(self)

        # Title
        title_label = QLabel("Title:")
        self.title_entry = QLineEdit()
        main_layout.addWidget(title_label)
        main_layout.addWidget(self.title_entry)

        # Author
        author_label = QLabel("Author (Optional):")
        self.author_entry = QLineEdit()
        main_layout.addWidget(author_label)
        main_layout.addWidget(self.author_entry)

        # Standard OK/Cancel buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        main_layout.addStretch()
        main_layout.addWidget(self.button_box)

        self.title_entry.setFocus()

    def accept(self):
        """Save the values before closing."""
        self.title = self.title_entry.text()
        self.author = self.author_entry.text()

        if not self.title:
            # Simple validation
            return  # Don't close

        super().accept()
