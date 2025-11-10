# dialogs/page_number_dialog.py
import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QDialogButtonBox, QWidget
)
from PySide6.QtCore import Qt


class PageNumberDialog(QDialog):
    """
    A simple dialog to ask for a page number or range.
    Formats the output as (p. XX) or (pp. XX-XX).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Page Citation")

        self.page_text = ""

        main_layout = QVBoxLayout(self)

        label = QLabel("Page(s):")
        main_layout.addWidget(label)

        self.page_entry = QLineEdit()
        self.page_entry.setPlaceholderText("e.g., 10 or 12-15")
        main_layout.addWidget(self.page_entry)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

        self.page_entry.setFocus()

    def accept(self):
        """Formats the text before closing."""
        text = self.page_entry.text().strip()
        if not text:
            # Don't accept if empty
            return

        # Determine prefix
        prefix = "pp." if '-' in text or ',' in text or ' ' in text else "p."
        self.page_text = f"({prefix} {text})"

        super().accept()