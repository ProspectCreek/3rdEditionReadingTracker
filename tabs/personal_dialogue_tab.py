# prospectcreek/3rdeditionreadingtracker/3rdEditionReadingTracker-f9372c7f456315b9a3fa82060c18255c8574e1ea/tabs/personal_dialogue_tab.py
import sys
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from tabs.rich_text_editor_tab import RichTextEditorTab


class PersonalDialogueTab(QWidget):
    """
    A simple tab that just contains a rich text editor for 'Personal Dialogue'.
    """

    def __init__(self, spell_checker_service=None, parent=None):
        super().__init__(parent)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)

        instructions = QLabel("Instructions for Personal Dialogue go here.")
        # --- NEW: Store label and hide it ---
        self.prompt_label = instructions # Re-use the existing label
        self.prompt_label.setWordWrap(True)
        self.prompt_label.setStyleSheet("font-style: italic; color: #555;")
        self.prompt_label.setVisible(False) # Hidden by default
        # --- END NEW ---
        main_layout.addWidget(instructions)

        self.editor = RichTextEditorTab("Personal Dialogue", spell_checker_service=spell_checker_service) # <-- PASS SERVICE
        main_layout.addWidget(self.editor)

    def update_instructions(self, instructions_data, key):
        """Sets the instruction text for this tab."""
        text = instructions_data.get(key, "")
        self.prompt_label.setText(text)
        self.prompt_label.setVisible(bool(text))