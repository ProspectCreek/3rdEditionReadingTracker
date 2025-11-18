# dialogs/edit_syntopic_rules_dialog.py
import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QDialogButtonBox, QLabel
)
from PySide6.QtCore import Qt

try:
    from tabs.rich_text_editor_tab import RichTextEditorTab
except ImportError:
    print("Error: Could not import RichTextEditorTab for EditSyntopicRulesDialog")
    RichTextEditorTab = None


class EditSyntopicRulesDialog(QDialog):
    """
    A dialog to edit the syntopic reading rules using the full
    RichTextEditorTab.
    """

    def __init__(self, rules_html, spell_checker_service=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Syntopical Reading Rules")
        self.setMinimumSize(600, 700)

        self.new_html = rules_html  # Default to old html if no change

        main_layout = QVBoxLayout(self)

        if RichTextEditorTab:
            self.editor = RichTextEditorTab("Syntopic Rules Editor", spell_checker_service)
            self.editor.set_html(rules_html)
            main_layout.addWidget(self.editor)
        else:
            main_layout.addWidget(QLabel("Error: RichTextEditorTab could not be loaded."))

        # Standard OK/Cancel buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

    def accept(self):
        """Saves the new HTML content."""
        if RichTextEditorTab and hasattr(self, 'editor'):
            # This is a synchronous call to get the HTML
            self.editor.get_html(self._set_html_and_close)
        else:
            self.reject()  # Don't save if editor didn't load

    def _set_html_and_close(self, html):
        """Callback to store the HTML and then accept the dialog."""
        self.new_html = html
        super().accept()  # Now, actually accept the dialog

    def get_html(self):
        return self.new_html
