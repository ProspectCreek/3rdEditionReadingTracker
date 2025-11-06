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
    def __init__(self, db, project_id: int, text_field: str, project_root_dir: str = "", parent=None):
        super().__init__(parent)
        self.db = db
        self.project_id = project_id
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

        self.editor = RichTextEditorTab(title)
        layout.addWidget(self.editor, 1)

    # ---- API used by dashboard ----
    def load_data(self):
        html = ""
        try:
            # This was already correct
            if hasattr(self.db, "get_project_text_field"):
                html = self.db.get_project_text_field(self.project_id, self.text_field) or ""
        except Exception as e:
            print(f"[WARN] load_data({self.text_field}): {e}")
        self.editor.set_html(html)

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

