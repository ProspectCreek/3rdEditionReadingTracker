# prospectcreek/3rdeditionreadingtracker/3rdEditionReadingTracker-f9372c7f456315b9a3fa82060c18255c8574e1ea/tabs/elevator_abstract_tab.py
import sys
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from tabs.rich_text_editor_tab import RichTextEditorTab


class ElevatorAbstractTab(QWidget):
    """
    A simple tab that just contains a rich text editor for 'Elevator Abstract'.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)

        instructions = QLabel("Instructions for Elevator Abstract go here.")
        main_layout.addWidget(instructions)

        self.editor = RichTextEditorTab("Elevator Abstract")
        main_layout.addWidget(self.editor)