import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QDialogButtonBox, QPushButton, QWidget,
    QScrollArea
)
from PySide6.QtCore import Qt


class CitationRow(QWidget):
    """A single row widget for one citation entry (Reading + Page)."""

    def __init__(self, readings_list, parent=None):
        super().__init__(parent)
        self.readings = readings_list
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.source_combo = QComboBox()
        self.source_combo.setPlaceholderText("Select Source")
        self.source_combo.setMinimumWidth(200)

        for r in self.readings:
            # Prioritize nickname, fallback to title
            nickname = r.get('nickname')
            display_text = nickname if (nickname and nickname.strip()) else r.get('title', 'Unknown Title')

            self.source_combo.addItem(display_text, r['id'])

        self.page_label = QLabel("Page(s):")
        self.page_entry = QLineEdit()
        self.page_entry.setPlaceholderText("e.g. 12")
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
            "reading": reading,
            "page_text": page_text
        }

    def set_data(self, rid, page):
        idx = self.source_combo.findData(rid)
        if idx >= 0: self.source_combo.setCurrentIndex(idx)
        self.page_entry.setText(page)


class AddCitationDialog(QDialog):
    """
    A simplified dialog to build a citation string with multiple references.
    Output format: (Nickname, p. XX; Nickname 2, p. YY)
    """

    def __init__(self, readings_list, parent=None, current_data=None):
        super().__init__(parent)
        self.setWindowTitle("Add Citation")
        self.setMinimumWidth(500)

        self.readings = readings_list
        self.citation_rows = []
        self.result_text = ""  # The final string to insert

        main_layout = QVBoxLayout(self)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setMinimumHeight(150)
        self.widget = QWidget()
        self.rows_layout = QVBoxLayout(self.widget)
        self.rows_layout.setSpacing(10)
        self.rows_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll.setWidget(self.widget)
        main_layout.addWidget(self.scroll)

        controls = QHBoxLayout()
        btn_add = QPushButton("+ Add Source")
        btn_del = QPushButton("- Delete Last")

        controls.addWidget(btn_add)
        controls.addWidget(btn_del)
        controls.addStretch()
        main_layout.addLayout(controls)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

        btn_add.clicked.connect(self._add_row)
        btn_del.clicked.connect(self._delete_last_row)

        # Always start with one row
        self._add_row()

    def _add_row(self):
        row = CitationRow(self.readings)
        self.rows_layout.addWidget(row)
        self.citation_rows.append(row)
        if self.height() < 600 and len(self.citation_rows) > 3:
            self.resize(self.width(), self.height() + 40)
        return row

    def _delete_last_row(self):
        if len(self.citation_rows) > 1:
            row = self.citation_rows.pop()
            self.rows_layout.removeWidget(row)
            row.deleteLater()

    def accept(self):
        """Generates the result string."""
        parts = []

        for row in self.citation_rows:
            data = row.get_data()
            if not data: continue

            reading = data['reading']
            page = data['page_text']

            # Determine Name: Nickname > Author > Title
            name = reading.get('nickname')
            if not name or not name.strip():
                name = reading.get('author')
            if not name or not name.strip():
                name = reading.get('title', 'Unknown')

            ref_str = name.strip()

            if page:
                # Auto-detect multiple pages
                prefix = "pp." if ("-" in page or "," in page) else "p."
                ref_str += f", {prefix} {page}"

            parts.append(ref_str)

        if parts:
            self.result_text = f"({'; '.join(parts)})"
        else:
            self.result_text = ""

        super().accept()