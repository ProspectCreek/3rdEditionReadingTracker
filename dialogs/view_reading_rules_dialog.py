# dialogs/view_reading_rules_dialog.py
import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QTextBrowser, QDialogButtonBox
)
from PySide6.QtCore import Qt


class ViewReadingRulesDialog(QDialog):
    """
    A simple dialog to display the (formatted) reading rules.
    Read-only.
    """

    def __init__(self, rules_html, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Analytical Reading Rules")
        self.setMinimumSize(600, 700)

        main_layout = QVBoxLayout(self)

        self.text_browser = QTextBrowser()
        self.text_browser.setHtml(rules_html)
        self.text_browser.setOpenExternalLinks(True)
        main_layout.addWidget(self.text_browser)

        # Standard Close button
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.button_box.rejected.connect(self.reject) # Close maps to reject
        main_layout.addWidget(self.button_box)