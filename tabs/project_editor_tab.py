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
      - open_edit_instructions_dialog()
    """
    def __init__(self, db, project_id: int, text_field: str, project_root_dir: str = "", parent=None):
        super().__init__(parent)
        self.db = db
        self.project_id = project_id
        self.text_field = text_field

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        title = {
            "key_questions": "Key Questions",
            "thesis": "Thesis / Argument",
            "insights": "Key Insights",
            "unresolved": "Unresolved Questions",
        }.get(text_field, "Editor")

        # Optional prompt example
        if text_field == "key_questions":
            prompt = QLabel("What is the central question this project aims to answer?")
            prompt.setWordWrap(True)
            layout.addWidget(prompt)

        self.editor = RichTextEditorTab(title)
        layout.addWidget(self.editor, 1)

    # ---- API used by dashboard ----
    def load_data(self):
        html = ""
        try:
            if hasattr(self.db, "get_project_text_field"):
                html = self.db.get_project_text_field(self.project_id, self.text_field) or ""
        except Exception as e:
            print(f"[WARN] load_data({self.text_field}): {e}")
        self.editor.set_html(html)

    def get_editor_content(self, callback):
        self.editor.get_html(callback)

    def open_edit_instructions_dialog(self):
        QMessageBox.information(
            self,
            "Edit Instructions",
            "Instruction editing UI not wired in this native refactor.\n"
            "Formatting is now powered by a Qt toolbar with QTextEdit."
        )
