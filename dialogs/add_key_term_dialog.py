# dialogs/add_key_term_dialog.py
import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QTextEdit,
    QComboBox, QCheckBox, QDialogButtonBox,
    QWidget, QHBoxLayout, QPushButton, QLabel, QMessageBox
)
from PySide6.QtCore import Qt, Slot

try:
    from dialogs.connect_tags_dialog import ConnectTagsDialog
except ImportError:
    ConnectTagsDialog = None

try:
    from dialogs.pdf_link_dialog import PdfLinkDialog
except ImportError:
    PdfLinkDialog = None


class AddKeyTermDialog(QDialog):
    """
    Dialog for adding or editing a 'Key Term'.
    """

    def __init__(self, db_manager, project_id, reading_id, outline_items, current_data=None, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.project_id = project_id
        self.reading_id = reading_id
        self.outline_items = outline_items
        self.current_data = current_data if current_data else {}
        self.selected_pdf_node_id = self.current_data.get('pdf_node_id')

        self.setWindowTitle("Edit Key Term" if current_data else "Add Key Term")
        self.setMinimumWidth(550)

        self.setup_ui()

        # Load initial PDF label if ID exists
        if self.selected_pdf_node_id:
            self._update_pdf_label_from_id(self.selected_pdf_node_id)

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.term_edit = QLineEdit()
        self.term_edit.setPlaceholderText("Enter the key term...")
        self.term_edit.setText(self.current_data.get("term", ""))
        form_layout.addRow("Term:", self.term_edit)

        self.definition_edit = QTextEdit()
        self.definition_edit.setMinimumHeight(80)
        self.definition_edit.setPlaceholderText("Enter definition...")
        self.definition_edit.setText(self.current_data.get("definition", ""))
        form_layout.addRow("My Definition:", self.definition_edit)

        # --- Location & Context ---
        citation_form_layout = QFormLayout()

        self.quote_edit = QTextEdit()
        self.quote_edit.setPlaceholderText("Enter a direct quote...")
        self.quote_edit.setMinimumHeight(60)
        self.quote_edit.setPlainText(self.current_data.get("quote", ""))
        citation_form_layout.addRow("Quote:", self.quote_edit)

        where_layout = QHBoxLayout()
        self.where_combo = QComboBox()
        self._populate_where_combo(self.outline_items)

        current_outline_id = self.current_data.get("outline_id")
        if current_outline_id:
            idx = self.where_combo.findData(current_outline_id)
            if idx != -1: self.where_combo.setCurrentIndex(idx)

        self.page_edit = QLineEdit()
        self.page_edit.setPlaceholderText("e.g., 10-12")
        self.page_edit.setFixedWidth(80)
        self.page_edit.setText(self.current_data.get("pages", ""))

        where_layout.addWidget(self.where_combo)
        where_layout.addWidget(QLabel("Page(s):"))
        where_layout.addWidget(self.page_edit)
        citation_form_layout.addRow("Location:", where_layout)

        self.role_combo = QComboBox()
        self.role_combo.addItems([
            "Defines Scope", "Names Mechanism", "Criterion/Test",
            "Assumption", "Contrast/Foil", "Key Variable"
        ])
        self.role_combo.setCurrentText(self.current_data.get("role", "Defines Scope"))
        citation_form_layout.addRow("Role:", self.role_combo)

        main_layout.addLayout(citation_form_layout)

        # --- Tags & PDF ---
        other_form_layout = QFormLayout()

        tags_layout = QHBoxLayout()
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("e.g., #concept")
        self.tags_edit.setText(self.current_data.get("synthesis_tags", ""))
        connect_btn = QPushButton("Connect...")
        if ConnectTagsDialog:
            connect_btn.clicked.connect(self._open_connect_tags_dialog)
        else:
            connect_btn.setEnabled(False)
        tags_layout.addWidget(self.tags_edit)
        tags_layout.addWidget(connect_btn)
        other_form_layout.addRow("Synthesis Tags:", tags_layout)

        # PDF Link
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
        other_form_layout.addRow("PDF Link:", pdf_layout)

        self.notes_edit = QTextEdit()
        self.notes_edit.setMinimumHeight(60)
        self.notes_edit.setPlaceholderText("Additional notes...")
        self.notes_edit.setText(self.current_data.get("notes", ""))
        other_form_layout.addRow("Notes:", self.notes_edit)

        main_layout.addLayout(other_form_layout)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

    def _populate_where_combo(self, outline_items, indent=0):
        if indent == 0:
            self.where_combo.addItem("[Reading-Level Notes]", None)
        for item in outline_items:
            prefix = "  " * indent
            self.where_combo.addItem(f"{prefix} {item['section_title']}", item['id'])
            if 'children' in item:
                self._populate_where_combo(item['children'], indent + 1)

    @Slot()
    def _open_connect_tags_dialog(self):
        if not ConnectTagsDialog: return
        try:
            all_tags = self.db.get_project_tags(self.project_id)
            current = [t.strip() for t in self.tags_edit.text().split(',') if t.strip()]
            dialog = ConnectTagsDialog(all_tags, current, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.tags_edit.setText(", ".join(dialog.get_selected_tag_names()))
        except Exception as e:
            print(f"Error opening tags: {e}")

    @Slot()
    def _open_pdf_link_dialog(self):
        if not PdfLinkDialog: return
        dialog = PdfLinkDialog(self.db, self.project_id, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if dialog.selected_node_id:
                self.selected_pdf_node_id = dialog.selected_node_id
                self._update_pdf_label_from_id(self.selected_pdf_node_id)

    def _update_pdf_label_from_id(self, node_id):
        node = self.db.get_pdf_node_details(node_id)
        if node:
            lbl = node.get('label', 'Node')
            pg = node.get('page_number', 0) + 1
            self.pdf_label.setText(f"{lbl} (Pg {pg})")
            self.pdf_label.setStyleSheet("font-weight: bold; color: #2563EB;")
        else:
            self.pdf_label.setText(f"Node ID: {node_id}")

    @Slot()
    def _clear_pdf_link(self):
        self.selected_pdf_node_id = None
        self.pdf_label.setText("No PDF Node connected")
        self.pdf_label.setStyleSheet("font-style: italic; color: #555;")

    def get_data(self):
        return {
            "term": self.term_edit.text().strip(),
            "definition": self.definition_edit.toPlainText().strip(),
            "quote": self.quote_edit.toPlainText().strip(),
            "outline_id": self.where_combo.currentData(),
            "pages": self.page_edit.text().strip(),
            "role": self.role_combo.currentText(),
            "synthesis_tags": self.tags_edit.text().strip(),
            "notes": self.notes_edit.toPlainText().strip(),
            "pdf_node_id": self.selected_pdf_node_id
        }