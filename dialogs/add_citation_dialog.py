# dialogs/add_citation_dialog.py
import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QDialogButtonBox, QPushButton, QWidget,
    QScrollArea, QMessageBox
)
from PySide6.QtCore import Qt


class CitationRow(QWidget):
    """A single row widget for one citation entry."""

    def __init__(self, readings_list, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.source_combo = QComboBox()
        self.source_combo.setPlaceholderText("Select Source")
        self.source_combo.setMinimumWidth(200)

        for r in readings_list:
            # --- FIX: Robust fallback logic for nickname ---
            try:
                nickname = r['nickname']
            except IndexError:
                nickname = None

            display_text = nickname if (nickname and nickname.strip()) else r['title']
            # --- END FIX ---
            self.source_combo.addItem(display_text, r['id'])

        self.page_label = QLabel("p./pp.:")
        self.page_entry = QLineEdit()
        self.page_entry.setPlaceholderText("e.g., 10 or 12-15")
        self.page_entry.setFixedWidth(100)

        self.layout.addWidget(self.source_combo)
        self.layout.addWidget(self.page_label)
        self.layout.addWidget(self.page_entry)
        self.layout.addStretch()

    def get_data(self):
        """Returns the text from the combo box and page entry."""
        source_text = self.source_combo.currentText()
        page_text = self.page_entry.text().strip()

        if not source_text or not page_text:
            return None

        # Determine prefix p. or pp.
        prefix = "pp." if '-' in page_text or ',' in page_text or ' ' in page_text else "p."

        return f"{source_text}, {prefix} {page_text}"


class AddCitationDialog(QDialog):
    """
    A dialog to build a citation string from one or more readings.
    """

    def __init__(self, readings_list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Citation")
        self.setMinimumWidth(450)

        self.readings = readings_list
        self.citation_text = ""
        self.citation_rows = []

        main_layout = QVBoxLayout(self)

        # ScrollArea to hold the citation rows
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        self.rows_layout = QVBoxLayout(scroll_widget)
        self.rows_layout.setSpacing(10)
        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)

        # Add/Delete buttons
        add_del_layout = QHBoxLayout()
        btn_add = QPushButton("+ Add Another")
        btn_del = QPushButton("- Delete Last")
        add_del_layout.addStretch()
        add_del_layout.addWidget(btn_add)
        add_del_layout.addWidget(btn_del)
        main_layout.addLayout(add_del_layout)

        # Standard OK/Cancel buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        main_layout.addWidget(self.button_box)

        # --- Connections ---
        btn_add.clicked.connect(self._add_row)
        btn_del.clicked.connect(self._delete_last_row)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        # Add the first row
        self._add_row()

    def _add_row(self):
        """Adds a new CitationRow widget to the layout."""
        row = CitationRow(self.readings)
        self.rows_layout.addWidget(row)
        self.citation_rows.append(row)

    def _delete_last_row(self):
        """Removes the last CitationRow widget from the layout."""
        if len(self.citation_rows) > 1:  # Always keep at least one row
            row = self.citation_rows.pop()
            self.rows_layout.removeWidget(row)
            row.deleteLater()

    def accept(self):
        """
        Builds the citation string and saves it before closing.
        """
        citations = []
        for row in self.citation_rows:
            data = row.get_data()
            if data:
                citations.append(data)

        if not citations:
            self.citation_text = ""
        else:
            self.citation_text = f"({'; '.join(citations)})"

        super().accept()