# dialogs/edit_driving_question_dialog.py
import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QTextEdit,
    QComboBox, QCheckBox, QDialogButtonBox,
    QWidget, QHBoxLayout, QPushButton, QLabel, QMessageBox
)
from PySide6.QtCore import Qt, Slot

# --- Imports for Tag and PDF Linking ---
try:
    from dialogs.connect_tags_dialog import ConnectTagsDialog
except ImportError:
    ConnectTagsDialog = None

try:
    from dialogs.pdf_link_dialog import PdfLinkDialog
except ImportError:
    PdfLinkDialog = None


class EditDrivingQuestionDialog(QDialog):
    """
    Dialog for adding or editing a Driving Question.
    Includes fields for Question, Nickname, Type/Category, Context,
    Tags, and PDF Node linking.
    """

    def __init__(self, db, dq_data=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.dq_data = dq_data if dq_data else {}
        self.result_data = None

        # Project ID needed for tags/PDFs
        self.project_id = None
        if parent and hasattr(parent, 'project_id'):
            self.project_id = parent.project_id

        # Determine Title
        is_edit = bool(self.dq_data.get('id'))
        self.setWindowTitle("Edit Driving Question" if is_edit else "Add Driving Question")
        self.setMinimumWidth(600)

        # Fetch Outline Items for the dropdown
        self.outline_items = []
        if parent and hasattr(parent, '_get_outline_items'):
            self.outline_items = parent._get_outline_items()

        # Initialize PDF selection state
        self.selected_pdf_node_id = self.dq_data.get('pdf_node_id')

        self.setup_ui()
        self.load_data()

        # Load initial PDF label if ID exists
        if self.selected_pdf_node_id:
            self._update_pdf_label_from_id(self.selected_pdf_node_id)

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        # --- Question Text ---
        self.question_edit = QTextEdit()
        self.question_edit.setPlaceholderText("Enter the question...")
        self.question_edit.setMinimumHeight(80)
        form_layout.addRow("Question:", self.question_edit)

        # --- Nickname ---
        self.nickname_edit = QLineEdit()
        self.nickname_edit.setPlaceholderText("Short name (e.g. 'Main Inquiry')")
        form_layout.addRow("Nickname:", self.nickname_edit)

        # --- Type & Category (Row) ---
        row_meta = QHBoxLayout()

        self.type_combo = QComboBox()
        self.type_combo.setEditable(True)
        self.type_combo.addItems(["Inferred", "Explicit"])
        row_meta.addWidget(QLabel("Type:"))
        row_meta.addWidget(self.type_combo)

        self.category_combo = QComboBox()
        self.category_combo.setEditable(True)
        self.category_combo.addItems(["Fact", "Explanation", "Evaluation", "Background"])
        row_meta.addWidget(QLabel("Category:"))
        row_meta.addWidget(self.category_combo)

        form_layout.addRow("Classification:", row_meta)

        # --- Scope & Location (Row) ---
        row_loc = QHBoxLayout()

        self.scope_combo = QComboBox()
        self.scope_combo.setEditable(True)
        self.scope_combo.addItems(["Global", "Section", "Local"])
        row_loc.addWidget(QLabel("Scope:"))
        row_loc.addWidget(self.scope_combo)

        self.outline_combo = QComboBox()
        self._populate_outline_combo(self.outline_items)
        row_loc.addWidget(QLabel("Section:"))
        row_loc.addWidget(self.outline_combo)

        form_layout.addRow("Context:", row_loc)

        # --- Pages ---
        self.pages_edit = QLineEdit()
        self.pages_edit.setPlaceholderText("e.g. 12-15")
        form_layout.addRow("Page(s):", self.pages_edit)

        # --- Why Important ---
        self.why_edit = QTextEdit()
        self.why_edit.setPlaceholderText("Why is this question important?")
        self.why_edit.setMinimumHeight(60)
        form_layout.addRow("Importance:", self.why_edit)

        # --- Synthesis Tags (Row) ---
        tags_layout = QHBoxLayout()
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("e.g., #theme, #concept")
        connect_btn = QPushButton("Connect...")

        if self.db and self.project_id is not None and ConnectTagsDialog:
            connect_btn.setEnabled(True)
            connect_btn.clicked.connect(self._open_connect_tags_dialog)
        else:
            connect_btn.setEnabled(False)

        tags_layout.addWidget(self.tags_edit)
        tags_layout.addWidget(connect_btn)
        form_layout.addRow("Tags:", tags_layout)

        # --- PDF Link (Row) ---
        pdf_layout = QHBoxLayout()
        self.pdf_label = QLabel("No PDF Node connected")
        self.pdf_label.setStyleSheet("font-style: italic; color: #555;")

        self.btn_pdf = QPushButton("Add/Change Node")
        if PdfLinkDialog:
            self.btn_pdf.clicked.connect(self._open_pdf_link_dialog)
        else:
            self.btn_pdf.setEnabled(False)

        self.btn_clear_pdf = QPushButton("Clear")
        self.btn_clear_pdf.clicked.connect(self._clear_pdf_link)

        pdf_layout.addWidget(self.pdf_label)
        pdf_layout.addStretch()
        pdf_layout.addWidget(self.btn_pdf)
        pdf_layout.addWidget(self.btn_clear_pdf)

        form_layout.addRow("PDF Link:", pdf_layout)

        # --- Working Question Checkbox ---
        self.working_check = QCheckBox("Set as Current Working Question")
        form_layout.addRow("", self.working_check)

        main_layout.addLayout(form_layout)

        # --- Buttons ---
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

    def _populate_outline_combo(self, items, indent=0):
        if indent == 0:
            self.outline_combo.addItem("[Reading-Level]", None)

        for item in items:
            prefix = "  " * indent
            self.outline_combo.addItem(f"{prefix}{item['section_title']}", item['id'])
            if 'children' in item:
                self._populate_outline_combo(item['children'], indent + 1)

    def load_data(self):
        """Populates fields from self.dq_data"""
        self.question_edit.setPlainText(self.dq_data.get('question_text', ''))
        self.nickname_edit.setText(self.dq_data.get('nickname', ''))
        self.type_combo.setCurrentText(self.dq_data.get('type', 'Inferred'))
        self.category_combo.setCurrentText(self.dq_data.get('question_category', ''))
        self.scope_combo.setCurrentText(self.dq_data.get('scope', ''))

        outline_id = self.dq_data.get('outline_id')
        if outline_id:
            idx = self.outline_combo.findData(outline_id)
            if idx != -1:
                self.outline_combo.setCurrentIndex(idx)

        self.pages_edit.setText(self.dq_data.get('pages', ''))
        self.why_edit.setPlainText(self.dq_data.get('why_question', ''))
        self.tags_edit.setText(self.dq_data.get('synthesis_tags', ''))
        self.working_check.setChecked(bool(self.dq_data.get('is_working_question', 0)))

    @Slot()
    def _open_connect_tags_dialog(self):
        if not ConnectTagsDialog: return
        try:
            all_tags = self.db.get_project_tags(self.project_id)
            current_tags = [t.strip() for t in self.tags_edit.text().split(',') if t.strip()]
            dialog = ConnectTagsDialog(all_tags, current_tags, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.tags_edit.setText(", ".join(dialog.get_selected_tag_names()))
        except Exception as e:
            print(f"Error opening tags dialog: {e}")

    @Slot()
    def _open_pdf_link_dialog(self):
        if not PdfLinkDialog: return
        # We can pass None as project_id if we want it to default to all,
        # or self.project_id if the dialog supports filtering.
        dialog = PdfLinkDialog(self.db, self.project_id, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if dialog.selected_node_id:
                self.selected_pdf_node_id = dialog.selected_node_id
                self._update_pdf_label_from_id(self.selected_pdf_node_id)

    def _update_pdf_label_from_id(self, node_id):
        """Fetches node details to display a friendly label."""
        node = self.db.get_pdf_node_details(node_id)
        if node:
            lbl = node.get('label', 'Node')
            pg = node.get('page_number', 0) + 1
            self.pdf_label.setText(f"{lbl} (Pg {pg})")
            self.pdf_label.setStyleSheet("font-weight: bold; color: #2563EB;")
        else:
            self.pdf_label.setText(f"Node ID: {node_id} (Details not found)")

    @Slot()
    def _clear_pdf_link(self):
        self.selected_pdf_node_id = None
        self.pdf_label.setText("No PDF Node connected")
        self.pdf_label.setStyleSheet("font-style: italic; color: #555;")

    def accept(self):
        """Collects data and closes."""
        self.result_data = {
            "question_text": self.question_edit.toPlainText().strip(),
            "nickname": self.nickname_edit.text().strip(),
            "type": self.type_combo.currentText(),
            "question_category": self.category_combo.currentText(),
            "scope": self.scope_combo.currentText(),
            "outline_id": self.outline_combo.currentData(),
            "pages": self.pages_edit.text().strip(),
            "why_question": self.why_edit.toPlainText().strip(),
            "synthesis_tags": self.tags_edit.text().strip(),
            "is_working_question": self.working_check.isChecked(),
            "pdf_node_id": self.selected_pdf_node_id,
            # Preserve parent_id if it existed
            "parent_id": self.dq_data.get("parent_id")
        }
        super().accept()