# dialogs/add_term_dialog.py
import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QTextEdit,
    QDialogButtonBox, QScrollArea, QWidget, QLabel, QSplitter,
    QHBoxLayout, QPushButton, QComboBox, QFrame, QMessageBox,
    QCheckBox, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QIcon

try:
    from dialogs.pdf_link_dialog import PdfLinkDialog
except ImportError:
    PdfLinkDialog = None


class ReferenceWidget(QFrame):
    """
    A widget representing a single reference to a term within a reading.
    Supports multiple PDF links.
    """
    deleteRequested = Signal(QWidget)

    def __init__(self, reading_id, outline_items, db=None, parent=None):
        super().__init__(parent)
        self.reading_id = reading_id
        self.db = db
        # Store list of IDs
        self.selected_pdf_ids = []

        self.setFrameShape(QFrame.Shape.StyledPanel)

        main_layout = QHBoxLayout(self)

        form_layout = QFormLayout()
        form_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)

        # (a) Where In Reading?
        where_layout = QHBoxLayout()
        self.outline_combo = QComboBox()
        self.outline_combo.addItem("Reading-Level", None)
        for text, outline_id in outline_items:
            self.outline_combo.addItem(text, outline_id)
        where_layout.addWidget(self.outline_combo, 1)
        form_layout.addRow("Where In Reading:", where_layout)

        # (b) Author Address
        self.author_address_input = QTextEdit()
        self.author_address_input.setPlaceholderText("How does the author address this term?")
        self.author_address_input.setMinimumHeight(60)
        form_layout.addRow("How the Author Addresses My Term:", self.author_address_input)

        # (c) PDF Node Links (Multiple)
        pdf_group = QWidget()
        pdf_layout = QVBoxLayout(pdf_group)
        pdf_layout.setContentsMargins(0, 0, 0, 0)

        self.pdf_list = QListWidget()
        self.pdf_list.setMaximumHeight(80)
        pdf_layout.addWidget(self.pdf_list)

        pdf_btn_layout = QHBoxLayout()
        self.btn_link_pdf = QPushButton("Add Link")
        self.btn_link_pdf.clicked.connect(self._link_pdf)
        self.btn_remove_pdf = QPushButton("Remove")
        self.btn_remove_pdf.clicked.connect(self._remove_pdf_link)

        pdf_btn_layout.addWidget(self.btn_link_pdf)
        pdf_btn_layout.addWidget(self.btn_remove_pdf)
        pdf_btn_layout.addStretch()
        pdf_layout.addLayout(pdf_btn_layout)

        form_layout.addRow("PDF References:", pdf_group)

        # (d) My Notes
        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("My notes on this reference...")
        self.notes_input.setMinimumHeight(60)
        form_layout.addRow("My Notes:", self.notes_input)

        main_layout.addLayout(form_layout, 1)

        # (e) Delete Button
        delete_button_layout = QVBoxLayout()
        delete_button_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.delete_btn = QPushButton("-")
        self.delete_btn.setToolTip("Remove this reference")
        self.delete_btn.setFixedSize(24, 24)
        self.delete_btn.setStyleSheet("padding: 0px; font-weight: bold; font-size: 14px;")
        self.delete_btn.clicked.connect(lambda: self.deleteRequested.emit(self))
        delete_button_layout.addWidget(self.delete_btn)
        main_layout.addLayout(delete_button_layout, 0)

    def _link_pdf(self):
        if not PdfLinkDialog: return
        dialog = PdfLinkDialog(self.db, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if dialog.selected_node_id:
                node_id = dialog.selected_node_id
                if node_id not in self.selected_pdf_ids:
                    self.selected_pdf_ids.append(node_id)
                    self._refresh_pdf_list()

    def _remove_pdf_link(self):
        item = self.pdf_list.currentItem()
        if item:
            nid = item.data(Qt.UserRole)
            if nid in self.selected_pdf_ids:
                self.selected_pdf_ids.remove(nid)
                self._refresh_pdf_list()

    def _refresh_pdf_list(self):
        self.pdf_list.clear()
        for nid in self.selected_pdf_ids:
            label = f"Node {nid}"
            if self.db:
                node = self.db.get_pdf_node_details(nid)
                if node:
                    label = f"{node['label']} (Pg {node['page_number'] + 1})"

            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, nid)
            self.pdf_list.addItem(item)

    def get_data(self):
        return {
            "reading_id": self.reading_id,
            "outline_id": self.outline_combo.currentData(),
            "author_address": self.author_address_input.toHtml(),
            "notes": self.notes_input.toHtml(),
            "pdf_node_ids": self.selected_pdf_ids  # List of IDs
        }

    def set_data(self, data):
        if data.get("outline_id"):
            index = self.outline_combo.findData(data["outline_id"])
            if index != -1:
                self.outline_combo.setCurrentIndex(index)
        self.author_address_input.setHtml(data.get("author_address", ""))
        self.notes_input.setHtml(data.get("notes", ""))

        # Handle old single ID or new list
        single_id = data.get("pdf_node_id")
        list_ids = data.get("pdf_node_ids", [])

        self.selected_pdf_ids = list(list_ids)
        if single_id and single_id not in self.selected_pdf_ids:
            self.selected_pdf_ids.append(single_id)

        self._refresh_pdf_list()


class ReadingReferenceGroup(QFrame):
    """
    A widget that groups all ReferenceWidgets for a single reading.
    """

    def __init__(self, db, reading, outline_items, parent=None):
        super().__init__(parent)
        self.db = db
        self.reading = reading
        self.outline_items = outline_items
        self.reference_widgets = []
        self.setFrameShape(QFrame.Shape.StyledPanel)

        main_layout = QVBoxLayout(self)

        # Header
        header_layout = QHBoxLayout()
        nickname = self.reading.get('nickname') or self.reading.get('title', 'Unknown Reading')
        header_label = QLabel(f"<b>{nickname}</b>")
        header_layout.addWidget(header_label, 1)

        self.not_in_reading_check = QCheckBox("Term Not In Reading")
        self.not_in_reading_check.toggled.connect(self._toggle_controls)
        header_layout.addWidget(self.not_in_reading_check)

        self.add_ref_btn = QPushButton("+")
        self.add_ref_btn.setToolTip("Add a reference for this reading")
        self.add_ref_btn.setFixedSize(24, 24)
        self.add_ref_btn.setStyleSheet("padding: 0px; font-weight: bold; font-size: 14px;")
        self.add_ref_btn.clicked.connect(self.add_reference_widget)
        header_layout.addWidget(self.add_ref_btn, 0)
        main_layout.addLayout(header_layout)

        self.references_layout = QVBoxLayout()
        main_layout.addLayout(self.references_layout)

    @Slot()
    def add_reference_widget(self, data=None):
        ref_widget = ReferenceWidget(self.reading['id'], self.outline_items, db=self.db)
        if data:
            ref_widget.set_data(data)

        ref_widget.deleteRequested.connect(self.delete_reference_widget)
        self.references_layout.addWidget(ref_widget)
        self.reference_widgets.append(ref_widget)

        self._toggle_controls(self.not_in_reading_check.isChecked())

    @Slot(QWidget)
    def delete_reference_widget(self, widget):
        if widget in self.reference_widgets:
            self.references_layout.removeWidget(widget)
            self.reference_widgets.remove(widget)
            widget.deleteLater()

    @Slot(bool)
    def _toggle_controls(self, is_checked):
        self.add_ref_btn.setEnabled(not is_checked)
        for widget in self.reference_widgets:
            widget.setEnabled(not is_checked)

    def get_status(self):
        return {
            "reading_id": self.reading['id'],
            "not_in_reading": 1 if self.not_in_reading_check.isChecked() else 0
        }

    def set_status(self, not_in_reading):
        self.not_in_reading_check.setChecked(bool(not_in_reading))
        self._toggle_controls(bool(not_in_reading))

    def get_data(self):
        return [widget.get_data() for widget in self.reference_widgets]


class AddTermDialog(QDialog):
    def __init__(self, db, project_id, terminology_id=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.project_id = project_id
        self.terminology_id = terminology_id
        self.reading_groups = []

        if self.terminology_id:
            self.setWindowTitle("Edit Term")
        else:
            self.setWindowTitle("Add New Term")

        self.setMinimumSize(900, 800)

        main_layout = QVBoxLayout(self)

        form_widget = QWidget()
        form_layout = QFormLayout(form_widget)
        form_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        self.term_input = QLineEdit()
        self.meaning_input = QTextEdit()
        self.meaning_input.setPlaceholderText("Your definition of this term...")
        self.meaning_input.setMinimumHeight(100)
        form_layout.addRow("My Term:", self.term_input)
        form_layout.addRow("My Meaning:", self.meaning_input)
        main_layout.addWidget(form_widget)

        main_layout.addWidget(QLabel("<b>Reading References:</b>"))

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        self.readings_layout = QVBoxLayout(scroll_widget)
        self.readings_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area, 1)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)

        self.load_all_readings()
        if self.terminology_id:
            self.load_existing_term_data()

    def load_all_readings(self):
        readings = self.db.get_readings(self.project_id)
        outline_map = self.db.get_all_outline_items_for_project(self.project_id)

        for reading in readings:
            reading_id = reading['id']
            outline_items = outline_map.get(reading_id, [])
            group_widget = ReadingReferenceGroup(self.db, reading, outline_items, self)
            self.readings_layout.addWidget(group_widget)
            self.reading_groups.append(group_widget)

    def load_existing_term_data(self):
        data = self.db.get_terminology_details(self.terminology_id)
        if not data:
            QMessageBox.critical(self, "Error", "Could not load terminology data.")
            self.reject()
            return

        self.term_input.setText(data.get("term", ""))
        self.meaning_input.setHtml(data.get("meaning", ""))

        refs_by_reading = {}
        for ref in data.get("references", []):
            reading_id = ref['reading_id']
            if reading_id not in refs_by_reading:
                refs_by_reading[reading_id] = []
            refs_by_reading[reading_id].append(ref)

        for group in self.reading_groups:
            reading_id = group.reading['id']
            statuses = data.get('statuses', {})
            group.set_status(statuses.get(reading_id, 0))

            if reading_id in refs_by_reading:
                for ref_data in refs_by_reading[reading_id]:
                    group.add_reference_widget(ref_data)

    def get_data(self):
        all_references = []
        for group in self.reading_groups:
            all_references.extend(group.get_data())

        all_statuses = [group.get_status() for group in self.reading_groups]

        return {
            "term": self.term_input.text().strip(),
            "meaning": self.meaning_input.toHtml(),
            "references": all_references,
            "statuses": all_statuses
        }