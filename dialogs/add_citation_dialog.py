# dialogs/add_citation_dialog.py
import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QDialogButtonBox, QPushButton, QWidget,
    QScrollArea, QMessageBox, QCheckBox
)
from PySide6.QtCore import Qt
from bs4 import BeautifulSoup

try:
    from pyzotero import zotero
except ImportError:
    zotero = None


class CitationRow(QWidget):
    """A single row widget for one citation entry."""

    def __init__(self, readings_list, parent=None):
        super().__init__(parent)
        self.readings = readings_list
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.source_combo = QComboBox()
        self.source_combo.setPlaceholderText("Select Source")
        self.source_combo.setMinimumWidth(200)

        for r in readings_list:
            try:
                nickname = r['nickname']
            except IndexError:
                nickname = None

            display_text = nickname if (nickname and nickname.strip()) else r['title']
            if r.get('zotero_item_key'):
                display_text = f"📚 {display_text}"
            self.source_combo.addItem(display_text, r['id'])

        self.page_label = QLabel("Page(s):")
        self.page_entry = QLineEdit()
        self.page_entry.setFixedWidth(80)

        self.layout.addWidget(self.source_combo)
        self.layout.addWidget(self.page_label)
        self.layout.addWidget(self.page_entry)

    def get_data(self):
        """Returns the data for this row."""
        reading_id = self.source_combo.currentData()
        page_text = self.page_entry.text().strip()

        if not reading_id:
            return None

        # Find the reading object
        reading = next((r for r in self.readings if r['id'] == reading_id), None)

        return {
            "reading_id": reading_id,  # Store ID for reconstruction
            "reading": reading,
            "page_text": page_text
        }

    def set_data(self, rid, page):
        idx = self.source_combo.findData(rid)
        if idx >= 0: self.source_combo.setCurrentIndex(idx)
        self.page_entry.setText(page)


class AddCitationDialog(QDialog):
    """
    A dialog to build a citation string.
    """

    def __init__(self, readings_list, parent=None, db=None, enable_zotero=False, citation_style='apa',
                 current_data=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Citation" if current_data else "Add Zotero Citation")
        self.setMinimumWidth(500)

        # --- INIT VARIABLES IMMEDIATELY ---
        self.is_endnote_mode = False
        self.generated_citations = []  # List of formatted strings
        self.result_text = ""  # Combined string (for in-text)
        self.result_data = []  # Raw data for saving
        self.citation_rows = []
        # ----------------------------------

        self.readings = readings_list
        self.db = db
        self.enable_zotero = enable_zotero and (zotero is not None) and (self.db is not None)
        self.citation_style = citation_style

        main_layout = QVBoxLayout(self)

        if self.enable_zotero:
            main_layout.addWidget(QLabel(f"Using Style: <b>{citation_style.upper()}</b>"))

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setMinimumHeight(150)
        self.widget = QWidget()
        self.rows_layout = QVBoxLayout(self.widget)
        self.rows_layout.setSpacing(10)
        self.scroll.setWidget(self.widget)
        main_layout.addWidget(self.scroll)

        controls = QHBoxLayout()
        btn_add = QPushButton("+ Add Source")
        btn_del = QPushButton("- Delete Last")
        self.checkbox_endnote = QCheckBox("Insert as Endnote")

        # Auto-check if style name implies it
        if "note" in self.citation_style.lower():
            self.checkbox_endnote.setChecked(True)

        controls.addWidget(self.checkbox_endnote)
        controls.addStretch()
        controls.addWidget(btn_add)
        controls.addWidget(btn_del)
        main_layout.addLayout(controls)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

        btn_add.clicked.connect(self._add_row)
        btn_del.clicked.connect(self._delete_last_row)

        # Load existing data if editing
        if current_data:
            # If we are editing, we assume the mode based on context,
            # but usually editing is for in-text.
            # If editing, current_data is a list of dicts.
            for entry in current_data:
                row = self._add_row()
                # Handle both structure variations if necessary
                rid = entry.get('reading_id')
                page = entry.get('page_text', '')
                row.set_data(rid, page)
        else:
            self._add_row()

    def _add_row(self):
        row = CitationRow(self.readings)
        self.rows_layout.addWidget(row)
        self.citation_rows.append(row)
        if self.height() < 600:
            self.resize(self.width(), self.height() + 50)
        return row

    def _delete_last_row(self):
        if len(self.citation_rows) > 1:
            row = self.citation_rows.pop()
            self.rows_layout.removeWidget(row)
            row.deleteLater()
            self.resize(self.width(), max(300, self.height() - 50))

    def _get_zotero_client(self):
        settings = self.db.get_user_settings()
        if not settings: return None
        return zotero.Zotero(settings['zotero_library_id'], settings.get('zotero_library_type', 'user'),
                             settings['zotero_api_key'])

    def accept(self):
        # 1. Collect Data
        self.result_data = [row.get_data() for row in self.citation_rows if row.get_data()]
        if not self.result_data:
            super().accept()
            return

        self.is_endnote_mode = self.checkbox_endnote.isChecked()
        zot = self._get_zotero_client() if self.enable_zotero else None

        self.generated_citations = []

        # 2. Generate Citations
        if self.is_endnote_mode:
            # Generate individual strings. The caller (AssignmentTab) will merge them.
            for data in self.result_data:
                self.generated_citations.append(self._generate_single_citation(zot, data, format='bib'))
        else:
            # In-Text: Generate individual strings (Author Year), then merge here.
            parts = []
            for data in self.result_data:
                cit = self._generate_single_citation(zot, data, format='citation')
                # Strip outer parens if present so we can merge them into one set
                if cit.startswith("(") and cit.endswith(")"):
                    cit = cit[1:-1]
                parts.append(cit)

            self.result_text = f"({'; '.join(parts)})"
            self.generated_citations = [self.result_text]

        super().accept()

    def _generate_single_citation(self, zot, data, format):
        r = data['reading']
        key = r.get('zotero_item_key')
        page = data['page_text']

        if zot and key:
            try:
                if format == 'bib':
                    # Full note style
                    items = zot.items(itemKey=key, format='bib', style=self.citation_style)
                    if items:
                        soup = BeautifulSoup(items[0], "html.parser")
                        text = soup.get_text().strip()
                        # Clean trailing period before adding page
                        if text.endswith(".") and page: text = text[:-1]

                        if page:
                            text += f", {page}."
                        elif not text.endswith("."):
                            text += "."
                        return text
                else:
                    # In-text style
                    resp = zot.items(itemKey=key, format='citation', style=self.citation_style)
                    if resp:
                        text = resp[0]  # e.g. "(Smith, 2020)"
                        # Hacky page insertion for in-text
                        if page:
                            if text.endswith(")"):
                                text = text[:-1] + f", {page})"
                            else:
                                text += f", {page}"
                        return text
            except Exception as e:
                print(f"Zotero error: {e}")

        # Fallback
        return self._manual_fallback(r, page, format == 'bib')

    def _manual_fallback(self, reading, page, is_full):
        author = reading.get('author', 'Unknown')
        title = reading.get('title', 'Unknown')
        year = reading.get('published', 'n.d.')
        prefix = "p." if page else ""
        if is_full:
            return f"{author}. {title}. {year}. {prefix} {page}."
        else:
            return f"({author}, {year}, {prefix} {page})"