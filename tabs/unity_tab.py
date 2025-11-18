# tabs/unity_tab.py
import sys
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QComboBox,
    QLabel, QMessageBox
)
from PySide6.QtCore import Qt, Slot

try:
    from tabs.rich_text_editor_tab import RichTextEditorTab
except ImportError:
    print("Error: Could not import RichTextEditorTab")
    RichTextEditorTab = None


class UnityTab(QWidget):
    """
    A custom widget for the 'Unity' tab, containing a text editor
    and dropdowns for 'Kind of Work' and 'Driving Question'.
    """

    def __init__(self, db, project_id, reading_id, parent=None):
        super().__init__(parent)
        self.db = db
        self.project_id = project_id
        self.reading_id = reading_id
        self._is_loaded = False

        if RichTextEditorTab is None:
            main_layout = QVBoxLayout(self)
            main_layout.addWidget(QLabel("Error: RichTextEditorTab could not be loaded."))
            return

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(6)

        # --- NEW: Add Instruction Label ---
        self.prompt_label = QLabel("")
        self.prompt_label.setWordWrap(True)
        self.prompt_label.setStyleSheet("font-style: italic; color: #555;")
        self.prompt_label.setVisible(False) # Hidden by default
        main_layout.addWidget(self.prompt_label)
        # --- END NEW ---

        # --- Top: Rich Text Editor ---
        self.unity_label = QLabel("Unity (1-2 sentences):")
        self.unity_editor = RichTextEditorTab("Unity")
        self.unity_editor.setMinimumHeight(150)  # Give it some space

        main_layout.addWidget(self.unity_label)
        main_layout.addWidget(self.unity_editor, 1)  # Give editor stretch

        # --- Bottom: Form Layout for Dropdowns ---
        form_layout = QFormLayout()
        form_layout.setSpacing(8)

        # 1. Kind of Work
        self.kind_combo = QComboBox()
        self.kind_combo.addItems([
            "Theoretical",
            "Practical",
            "Imaginative",
            "Historical",
            "Scientific"
        ])
        form_layout.addRow("Kind of Work:", self.kind_combo)

        # 2. Driving Question
        self.dq_combo = QComboBox()
        form_layout.addRow("Addresses which Driving Question?:", self.dq_combo)

        main_layout.addLayout(form_layout)

        self._is_loaded = True  # Set flag after all UI elements are created

    def update_instructions(self, instructions_data, key):
        """Sets the instruction text for this tab."""
        text = instructions_data.get(key, "")
        self.prompt_label.setText(text)
        self.prompt_label.setVisible(bool(text))

    def load_data(self):
        """Loads data from the database into the widgets."""
        if not self._is_loaded or not self.reading_id or not hasattr(self, 'unity_editor'):
            return

        try:
            # 1. Load driving questions for the dropdown
            self.dq_combo.clear()
            self.dq_combo.addItem("None", None)  # Add a 'None' option

            # --- FIX: This call will now correctly *only* get driving questions ---
            questions = self.db.get_driving_questions(self.reading_id, parent_id=True)

            for q in questions:
                # Use nickname if available, otherwise truncate text
                nickname = q.get('nickname')
                if nickname and nickname.strip():
                    display_text = nickname
                else:
                    q_text = (q.get('question_text', '') or '')
                    display_text = (q_text[:70] + "...") if len(q_text) > 70 else q_text

                self.dq_combo.addItem(display_text, q['id'])

            # 2. Load the saved data for this reading
            reading_data = self.db.get_reading_details(self.reading_id)
            if not reading_data:
                return

            # Set Unity editor text
            self.unity_editor.set_html(reading_data.get('unity_html', ''))

            # Set Kind of Work dropdown
            kind_of_work = reading_data.get('unity_kind_of_work')
            if kind_of_work:
                self.kind_combo.setCurrentText(kind_of_work)

            # Set Driving Question dropdown
            dq_id = reading_data.get('unity_driving_question_id')
            if dq_id:
                index = self.dq_combo.findData(dq_id)
                if index != -1:
                    self.dq_combo.setCurrentIndex(index)

        except Exception as e:
            QMessageBox.critical(self, "Error Loading Unity", f"Could not load Unity tab data: {e}")

    def save_data(self):
        """Saves data from the widgets back to the database."""
        if not self._is_loaded or not hasattr(self, 'unity_editor'):
            return

        # 1. Get data from widgets
        kind_of_work = self.kind_combo.currentText()
        dq_id = self.dq_combo.currentData()

        # 2. Get HTML content from the editor
        # This is an async call, so we do the DB save inside the callback
        def save_html_callback(html_content):
            if html_content is None:
                return  # Editor might not be ready

            try:
                self.db.save_reading_unity_data(
                    self.reading_id,
                    html_content,
                    kind_of_work,
                    dq_id
                )
            except Exception as e:
                print(f"Error saving Unity data: {e}")

        self.unity_editor.get_html(save_html_callback)