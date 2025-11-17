# tabs/project_editor_tab.py

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QMessageBox
from tabs.rich_text_editor_tab import RichTextEditorTab


class ProjectEditorTab(QWidget):
    """
    Bottom-area editor tab that wraps a RichTextEditorTab (native Qt).
    Public API kept identical to your previous version:
      - text_field (str)
      - load_data()
      - get_editor_content(callback)
    """

    def __init__(self, db, project_id: int, text_field: str, project_root_dir: str = "", spell_checker_service=None,
                 parent=None):
        super().__init__(parent)
        self.db = db
        self.project_id = project_id
        self.spell_checker_service = spell_checker_service  # <-- STORE SERVICE
        self.text_field = text_field
        self.prompt_label = None  # MODIFIED: To hold the prompt label

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # MODIFIED: Use the full 'text_field' names (e.g., 'key_questions_text')
        # to look up the display title.
        title = {
            "key_questions_text": "Key Questions",
            "thesis_text": "Thesis / Argument",
            "insights_text": "Key Insights",
            "unresolved_text": "Unresolved Questions",
        }.get(text_field, "Editor")

        # MODIFIED: Get instructions from DB and show the correct prompt
        self.instructions = self.db.get_or_create_instructions(self.project_id)
        prompt_text_map = {
            "key_questions_text": self.instructions.get("key_questions_instr", ""),
            "thesis_text": self.instructions.get("thesis_instr", ""),
            "insights_text": self.instructions.get("insights_instr", ""),
            "unresolved_text": self.instructions.get("unresolved_instr", "")
        }
        prompt_text = prompt_text_map.get(self.text_field)

        if prompt_text:
            self.prompt_label = QLabel(prompt_text)
            self.prompt_label.setWordWrap(True)
            self.prompt_label.setStyleSheet("font-style: italic; color: #555;") # Added styling
            layout.addWidget(self.prompt_label)

        self.editor = RichTextEditorTab(title, spell_checker_service=self.spell_checker_service) # <-- PASS SERVICE
        layout.addWidget(self.editor, 1)

    # ---- API used by dashboard ----
    # MODIFIED: Replaced load_data() with a direct set_html() method.
    # The dashboard will now push the data to this widget.
    def set_html(self, html: str):
        """Public method to set the editor's content."""
        self.editor.set_html(html or "")

    def get_editor_content(self, callback):
        self.editor.get_html(callback)

    # MODIFIED: This method is called by the dashboard to refresh the prompt text
    def update_instructions(self):
        """Fetches the latest instructions from the DB and updates the prompt label."""
        self.instructions = self.db.get_or_create_instructions(self.project_id)
        if self.prompt_label:
            prompt_text_map = {
                "key_questions_text": self.instructions.get("key_questions_instr", ""),
                "thesis_text": self.instructions.get("thesis_instr", ""),
                "insights_text": self.instructions.get("insights_instr", ""),
                "unresolved_text": self.instructions.get("unresolved_instr", "")
            }
            new_text = prompt_text_map.get(self.text_field, "")
            self.prompt_label.setText(new_text)
            # Hide the label if the instruction text is empty
            self.prompt_label.setVisible(bool(new_text))


