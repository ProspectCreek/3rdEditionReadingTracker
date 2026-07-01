from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QLineEdit,
    QDialogButtonBox,
    QComboBox,
)


class AddReadingDialog(QDialog):
    """Dialog to add a new reading or edit an existing one."""

    def __init__(self, db_manager, current_data=None, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.current_data = current_data or {}

        self.setWindowTitle("Edit Reading" if current_data else "Add New Reading")
        self.setMinimumWidth(600)

        self.title = ""
        self.author = ""
        self.nickname = ""
        self.published = ""
        self.pages = ""
        self.level = ""
        self.classification = ""

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("e.g. How to Read a Book")
        form_layout.addRow("Title:", self.title_edit)

        self.author_edit = QLineEdit()
        self.author_edit.setPlaceholderText("Lastname, Firstname")
        form_layout.addRow("Author:", self.author_edit)

        self.published_edit = QLineEdit()
        self.published_edit.setPlaceholderText("YYYY or YYYY-MM-DD")
        form_layout.addRow("Published Date:", self.published_edit)

        self.nickname_edit = QLineEdit()
        self.nickname_edit.setPlaceholderText("e.g. Adler 1972")
        form_layout.addRow("Citation Nickname:", self.nickname_edit)

        self.pages_edit = QLineEdit()
        self.pages_edit.setPlaceholderText("Total pages or range")
        form_layout.addRow("Pages:", self.pages_edit)

        self.level_combo = QComboBox()
        self.level_combo.addItems([
            "Elementary (Entertainment)",
            "Inspectional (Information)",
            "Analytical (Understanding)",
            "Syntopic (Mastery)",
        ])
        form_layout.addRow("Level:", self.level_combo)

        self.classification_edit = QLineEdit()
        self.classification_edit.setPlaceholderText("e.g. History, Science, Fiction")
        form_layout.addRow("Classification:", self.classification_edit)

        layout.addLayout(form_layout)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self._load_current_data()
        self.title_edit.setFocus()

    def _load_current_data(self):
        if not self.current_data:
            return

        self.title_edit.setText(self.current_data.get("title", ""))
        self.author_edit.setText(self.current_data.get("author", ""))
        self.nickname_edit.setText(self.current_data.get("nickname", ""))
        self.published_edit.setText(self.current_data.get("published", ""))
        self.pages_edit.setText(self.current_data.get("pages", ""))
        self.classification_edit.setText(self.current_data.get("classification", ""))

        level = self.current_data.get("level", "")
        if level:
            self.level_combo.setCurrentText(level)

    def accept(self):
        self.title = self.title_edit.text().strip()
        self.author = self.author_edit.text().strip()
        self.nickname = self.nickname_edit.text().strip()
        self.published = self.published_edit.text().strip()
        self.pages = self.pages_edit.text().strip()
        self.level = self.level_combo.currentText()
        self.classification = self.classification_edit.text().strip()

        if not self.title:
            self.title_edit.setFocus()
            return

        super().accept()
