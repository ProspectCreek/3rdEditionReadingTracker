# dialogs/add_argument_dialog.py
import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QTextEdit,
    QComboBox, QCheckBox, QDialogButtonBox,
    QWidget, QHBoxLayout, QPushButton, QLabel, QMessageBox,
    QScrollArea, QFrame
)
from PySide6.QtCore import Qt, Slot, Signal

try:
    from dialogs.connect_tags_dialog import ConnectTagsDialog
except ImportError:
    ConnectTagsDialog = None

try:
    from dialogs.pdf_link_dialog import PdfLinkDialog
except ImportError:
    PdfLinkDialog = None


class EvidenceWidget(QFrame):
    # ... (EvidenceWidget code remains unchanged as evidence doesn't have PDF links individually in this request) ...
    deleteRequested = Signal(QWidget)

    def __init__(self, reading_id, outline_items, parent=None):
        super().__init__(parent)
        self.reading_id = reading_id
        self.outline_items = outline_items
        self.setFrameShape(QFrame.Shape.StyledPanel)

        main_layout = QVBoxLayout(self)
        top_layout = QHBoxLayout()
        self.select_radio = QCheckBox("Select to Remove")
        top_layout.addWidget(self.select_radio)
        top_layout.addStretch()
        self.delete_btn = QPushButton("-")
        self.delete_btn.setToolTip("Remove this evidence")
        self.delete_btn.setFixedSize(24, 24)
        self.delete_btn.setStyleSheet("padding: 0px; font-weight: bold; font-size: 14px;")
        self.delete_btn.clicked.connect(lambda: self.deleteRequested.emit(self))
        top_layout.addWidget(self.delete_btn)
        main_layout.addLayout(top_layout)

        form_layout = QFormLayout()
        form_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)

        where_layout = QHBoxLayout()
        self.where_combo = QComboBox()
        self._populate_where_combo(self.outline_items)
        self.page_edit = QLineEdit()
        self.page_edit.setPlaceholderText("e.g., 10-12")
        self.page_edit.setFixedWidth(80)
        where_layout.addWidget(self.where_combo)
        where_layout.addWidget(QLabel("Page(s):"))
        where_layout.addWidget(self.page_edit)
        form_layout.addRow("Related Part:", where_layout)

        self.argument_text_edit = QLineEdit()
        self.argument_text_edit.setPlaceholderText("The evidence/argument text")
        form_layout.addRow("Argument:", self.argument_text_edit)

        self.reading_text_edit = QTextEdit()
        self.reading_text_edit.setPlaceholderText("Enter the direct quote from the reading...")
        self.reading_text_edit.setMinimumHeight(60)
        form_layout.addRow("Reading Text:", self.reading_text_edit)

        self.role_combo = QComboBox()
        self.role_combo.addItems(["States Claim", "Justifies Claim", "Limits Claim", "Contradicts Claim"])
        form_layout.addRow("Role in Argument:", self.role_combo)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["Reasoning", "Example", "Authority", "Data"])
        form_layout.addRow("Evidence Type:", self.type_combo)

        self.status_combo = QComboBox()
        self.status_combo.addItems(["Solved", "Partially Solved", "Unsolved"])
        form_layout.addRow("Status:", self.status_combo)

        self.rationale_edit = QTextEdit()
        self.rationale_edit.setMinimumHeight(60)
        self.rationale_edit.setPlaceholderText("Rationale for status...")
        form_layout.addRow("Rationale:", self.rationale_edit)

        main_layout.addLayout(form_layout)

    def _populate_where_combo(self, outline_items, indent=0):
        if indent == 0:
            self.where_combo.addItem("[Reading-Level Notes]", None)
        for item in outline_items:
            prefix = "  " * indent
            self.where_combo.addItem(f"{prefix} {item['section_title']}", item['id'])
            if 'children' in item:
                self._populate_where_combo(item['children'], indent + 1)

    def is_selected_for_removal(self):
        return self.select_radio.isChecked()

    def get_data(self):
        return {
            "outline_id": self.where_combo.currentData(),
            "pages_text": self.page_edit.text().strip(),
            "argument_text": self.argument_text_edit.text().strip(),
            "reading_text": self.reading_text_edit.toPlainText().strip(),
            "role_in_argument": self.role_combo.currentText(),
            "evidence_type": self.type_combo.currentText(),
            "status": self.status_combo.currentText(),
            "rationale_text": self.rationale_edit.toPlainText().strip(),
        }

    def set_data(self, data):
        current_outline_id = data.get("outline_id")
        if current_outline_id:
            idx = self.where_combo.findData(current_outline_id)
            if idx != -1: self.where_combo.setCurrentIndex(idx)

        self.page_edit.setText(data.get("pages_text", ""))
        self.argument_text_edit.setText(data.get("argument_text", ""))
        self.reading_text_edit.setPlainText(data.get("reading_text", ""))
        self.rationale_edit.setPlainText(data.get("rationale_text", ""))
        self.role_combo.setCurrentText(data.get("role_in_argument", "States Claim"))
        self.type_combo.setCurrentText(data.get("evidence_type", "Reasoning"))
        self.status_combo.setCurrentText(data.get("status", "Solved"))


class AddArgumentDialog(QDialog):
    """
    Dialog for adding or editing a 'Argument' and its evidence.
    """

    def __init__(self, db, project_id, reading_id, outline_items, driving_questions, current_data=None, parent=None):
        super().__init__(parent)

        self.db = db
        self.project_id = project_id
        self.reading_id = reading_id
        self.outline_items = outline_items
        self.driving_questions = driving_questions
        self.current_data = current_data if current_data else {}
        self.evidence_widgets = []
        self.selected_pdf_node_id = self.current_data.get('pdf_node_id')

        self.setWindowTitle("Edit Argument" if current_data else "Add Argument")
        self.setMinimumWidth(700)
        self.setMinimumHeight(800)

        self.setup_ui()

        if self.selected_pdf_node_id:
            self._update_pdf_label_from_id(self.selected_pdf_node_id)

        # Load Data
        if self.current_data:
            self._set_data(self.current_data)
        else:
            self._add_evidence_widget()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        top_form_layout = QFormLayout()

        self.claim_edit = QLineEdit()
        self.claim_edit.setPlaceholderText("Enter the claim...")
        top_form_layout.addRow("Claim:", self.claim_edit)

        self.because_edit = QLineEdit()
        self.because_edit.setPlaceholderText("Enter the 'because' statement...")
        top_form_layout.addRow("Because:", self.because_edit)

        self.dq_combo = QComboBox()
        self.dq_combo.addItem("None", None)
        for dq in self.driving_questions:
            nickname = dq.get('nickname')
            display_text = nickname if nickname else dq.get('question_text', '')[:70]
            self.dq_combo.addItem(display_text, dq['id'])
        top_form_layout.addRow("Addresses which Question:", self.dq_combo)

        # Tags
        tags_layout = QHBoxLayout()
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("e.g., #logic")
        connect_btn = QPushButton("Connect...")
        if ConnectTagsDialog:
            connect_btn.clicked.connect(self._open_connect_tags_dialog)
        else:
            connect_btn.setEnabled(False)
        tags_layout.addWidget(self.tags_edit)
        tags_layout.addWidget(connect_btn)
        top_form_layout.addRow("Synthesis Tags:", tags_layout)

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
        top_form_layout.addRow("PDF Link:", pdf_layout)

        self.is_insight_check = QCheckBox("Mark as Insight")
        top_form_layout.addRow("", self.is_insight_check)

        main_layout.addLayout(top_form_layout)

        main_layout.addWidget(QLabel("<b>Evidence</b>"))
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        self.evidence_layout = QVBoxLayout(scroll_widget)
        self.evidence_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area, 1)

        ev_btn_layout = QHBoxLayout()
        ev_btn_layout.addStretch()
        self.add_evidence_btn = QPushButton("Add Additional Evidence")
        self.remove_evidence_btn = QPushButton("Remove Selected Evidence")
        ev_btn_layout.addWidget(self.add_evidence_btn)
        ev_btn_layout.addWidget(self.remove_evidence_btn)
        main_layout.addLayout(ev_btn_layout)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        main_layout.addWidget(self.button_box)

        self.add_evidence_btn.clicked.connect(self._add_evidence_widget)
        self.remove_evidence_btn.clicked.connect(self._remove_selected_evidence)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

    def _set_data(self, data):
        self.claim_edit.setText(data.get("claim_text", ""))
        self.because_edit.setText(data.get("because_text", ""))
        self.is_insight_check.setChecked(bool(data.get("is_insight", 0)))
        self.tags_edit.setText(data.get("synthesis_tags", ""))
        dq_id = data.get("driving_question_id")
        if dq_id:
            idx = self.dq_combo.findData(dq_id)
            if idx != -1: self.dq_combo.setCurrentIndex(idx)

        for ev_data in data.get("evidence", []):
            self._add_evidence_widget(ev_data)

    def _add_evidence_widget(self, data=None):
        widget = EvidenceWidget(self.reading_id, self.outline_items, self)
        if data: widget.set_data(data)
        widget.deleteRequested.connect(self._on_delete_evidence_widget)
        self.evidence_layout.addWidget(widget)
        self.evidence_widgets.append(widget)

    @Slot(QWidget)
    def _on_delete_evidence_widget(self, widget):
        if widget in self.evidence_widgets:
            widget.deleteLater()
            self.evidence_widgets.remove(widget)

    @Slot()
    def _remove_selected_evidence(self):
        to_remove = [w for w in self.evidence_widgets if w.is_selected_for_removal()]
        if not to_remove: return
        if len(to_remove) == len(self.evidence_widgets):
            QMessageBox.warning(self, "Remove", "Argument must have at least one evidence item.")
            return
        for widget in to_remove:
            self._on_delete_evidence_widget(widget)

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
        evidence_list = [w.get_data() for w in self.evidence_widgets]
        return {
            "claim_text": self.claim_edit.text().strip(),
            "because_text": self.because_edit.text().strip(),
            "driving_question_id": self.dq_combo.currentData(),
            "is_insight": self.is_insight_check.isChecked(),
            "synthesis_tags": self.tags_edit.text().strip(),
            "evidence": evidence_list,
            "pdf_node_id": self.selected_pdf_node_id
        }