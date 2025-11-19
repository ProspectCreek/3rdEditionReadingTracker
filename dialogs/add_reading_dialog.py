from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QDialogButtonBox
)


class AddReadingDialog(QDialog):
    """
    Dialog to add a new reading (Title, Author, Nickname).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Reading")
        self.setMinimumWidth(600)  # <--- WIDENED DIALOG

        self.title = ""
        self.author = ""
        self.nickname = ""

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("e.g. How to Read a Book")

        self.author_edit = QLineEdit()
        self.author_edit.setPlaceholderText("e.g. Mortimer J. Adler")

        self.nickname_edit = QLineEdit()
        self.nickname_edit.setPlaceholderText("e.g. Adler")

        form_layout.addRow("Title:", self.title_edit)
        form_layout.addRow("Author:", self.author_edit)
        form_layout.addRow("Nickname (for tree view):", self.nickname_edit)

        layout.addLayout(form_layout)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        # Focus title by default
        self.title_edit.setFocus()

    def accept(self):
        self.title = self.title_edit.text().strip()
        self.author = self.author_edit.text().strip()
        self.nickname = self.nickname_edit.text().strip()
        super().accept()