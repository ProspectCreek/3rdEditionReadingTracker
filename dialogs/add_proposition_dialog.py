# dialogs/add_proposition_dialog.py
import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QTextEdit,
    QDialogButtonBox, QScrollArea, QWidget, QLabel, QSplitter,
    QHBoxLayout, QPushButton, QComboBox, QFrame, QMessageBox,
    QCheckBox
)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QIcon


class PropositionReferenceWidget(QFrame):
    """
    A widget representing a single reference to a proposition within a reading.
    (Where in Reading, How Author Addresses, My Notes, etc.)
    """
    deleteRequested = Signal(QWidget)

    def __init__(self, reading_id, outline_items, parent=None):
        """
        Initializes the reference widget.
        outline_items is a list of (display_text, outline_id) tuples.
        """
        super().__init__(parent)
        self.reading_id = reading_id
        self.setFrameShape(QFrame.Shape.StyledPanel)

        main_layout = QHBoxLayout(self)

        form_layout = QFormLayout()
        form_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)

        # (a) Where In Reading?
        where_layout = QHBoxLayout()
        self.outline_combo = QComboBox()
        self.outline_combo.addItem("Reading-Level", None)  # Add default
        for text, outline_id in outline_items:
            self.outline_combo.addItem(text, outline_id)
        self.page_input = QLineEdit()
        self.page_input.setPlaceholderText("Page(s)")
        self.page_input.setMaximumWidth(100)
        where_layout.addWidget(self.outline_combo, 1)
        where_layout.addWidget(self.page_input, 0)
        form_layout.addRow("Where In Reading:", where_layout)

        # (b) How the Author Addresses the Proposition
        self.how_addressed_input = QTextEdit()
        self.how_addressed_input.setPlaceholderText("How does the author address this proposition?")
        self.how_addressed_input.setMinimumHeight(60)
        form_layout.addRow("How does the author address this proposition:", self.how_addressed_input)

        # (c) My Notes
        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("My notes on this reference...")
        self.notes_input.setMinimumHeight(60)
        form_layout.addRow("My Notes:", self.notes_input)

        main_layout.addLayout(form_layout, 1)

        # (d) Delete Button
        delete_button_layout = QVBoxLayout()
        delete_button_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.delete_btn = QPushButton("-")
        self.delete_btn.setToolTip("Remove this reference")
        self.delete_btn.setFixedSize(24, 24)
        self.delete_btn.clicked.connect(lambda: self.deleteRequested.emit(self))
        delete_button_layout.addWidget(self.delete_btn)
        main_layout.addLayout(delete_button_layout, 0)

    def get_data(self):
        """Returns the data contained in this widget as a dict."""
        return {
            "reading_id": self.reading_id,
            "outline_id": self.outline_combo.currentData(),
            "page_number": self.page_input.text().strip(),
            "how_addressed": self.how_addressed_input.toHtml(),
            "notes": self.notes_input.toHtml()
        }

    def set_data(self, data):
        """Populates the widget from a data dict."""
        if data.get("outline_id"):
            index = self.outline_combo.findData(data["outline_id"])
            if index != -1:
                self.outline_combo.setCurrentIndex(index)
        self.page_input.setText(data.get("page_number", ""))
        self.how_addressed_input.setHtml(data.get("how_addressed", ""))
        self.notes_input.setHtml(data.get("notes", ""))


class PropositionReadingGroup(QFrame):
    """
    A widget that groups all PropositionReferenceWidgets for a single reading.
    Includes the reading's name and an '+' button.
    """

    def __init__(self, reading, outline_items, parent=None):
        """
        reading is a dict from db.get_readings()
        outline_items is a list of (display_text, outline_id) tuples
        """
        super().__init__(parent)
        self.reading = reading
        self.outline_items = outline_items
        self.reference_widgets = []
        self.setFrameShape(QFrame.Shape.StyledPanel)

        main_layout = QVBoxLayout(self)

        # Header with Reading Nickname and Add Button
        header_layout = QHBoxLayout()
        nickname = self.reading.get('nickname') or self.reading.get('title', 'Unknown Reading')
        header_label = QLabel(f"<b>{nickname}</b>")
        header_layout.addWidget(header_label, 1)

        self.not_in_reading_check = QCheckBox("Proposition Not In Reading")
        self.not_in_reading_check.toggled.connect(self._toggle_controls)
        header_layout.addWidget(self.not_in_reading_check)

        self.add_ref_btn = QPushButton("+")
        self.add_ref_btn.setToolTip("Add a reference for this reading")
        self.add_ref_btn.setFixedSize(24, 24)
        self.add_ref_btn.clicked.connect(self.add_reference_widget)
        header_layout.addWidget(self.add_ref_btn, 0)
        main_layout.addLayout(header_layout)

        # Container for the reference widgets
        self.references_layout = QVBoxLayout()
        main_layout.addLayout(self.references_layout)

    @Slot()
    def add_reference_widget(self, data=None):
        """Adds a new PropositionReferenceWidget to this group."""
        ref_widget = PropositionReferenceWidget(self.reading['id'], self.outline_items)
        if data:
            ref_widget.set_data(data)

        ref_widget.deleteRequested.connect(self.delete_reference_widget)
        self.references_layout.addWidget(ref_widget)
        self.reference_widgets.append(ref_widget)
        self._toggle_controls(self.not_in_reading_check.isChecked())

    @Slot(QWidget)
    def delete_reference_widget(self, widget):
        """Removes and deletes a specific PropositionReferenceWidget."""
        if widget in self.reference_widgets:
            self.references_layout.removeWidget(widget)
            self.reference_widgets.remove(widget)
            widget.deleteLater()

    @Slot(bool)
    def _toggle_controls(self, is_checked):
        """Disables/enables controls based on the checkbox."""
        self.add_ref_btn.setEnabled(not is_checked)
        for widget in self.reference_widgets:
            widget.setEnabled(not is_checked)

    def get_status(self):
        """Returns the status of the 'Not In Reading' checkbox."""
        return {
            "reading_id": self.reading['id'],
            "not_in_reading": 1 if self.not_in_reading_check.isChecked() else 0
        }

    def set_status(self, not_in_reading):
        """Sets the state of the checkbox and child widgets."""
        self.not_in_reading_check.setChecked(bool(not_in_reading))
        self._toggle_controls(bool(not_in_reading))

    def get_data(self):
        """Returns a list of data dicts from all child PropositionReferenceWidgets."""
        return [widget.get_data() for widget in self.reference_widgets]


class AddPropositionDialog(QDialog):
    """
    The main dialog for adding or editing a Proposition entry.
    """

    def __init__(self, db, project_id, proposition_id=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.project_id = project_id
        self.proposition_id = proposition_id
        self.reading_groups = []

        if self.proposition_id:
            self.setWindowTitle("Edit Proposition")
        else:
            self.setWindowTitle("Add New Proposition")

        self.setMinimumSize(700, 800)

        main_layout = QVBoxLayout(self)

        # --- Top Part: Proposition ---
        form_widget = QWidget()
        form_layout = QFormLayout(form_widget)
        form_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)

        self.display_name_input = QLineEdit()
        self.display_name_input.setPlaceholderText("Short name for list, e.g., 'Main Argument'")
        form_layout.addRow("Display Name:", self.display_name_input)

        self.proposition_input = QTextEdit()
        self.proposition_input.setPlaceholderText("Enter your proposition...")
        self.proposition_input.setMinimumHeight(100)
        form_layout.addRow("My Proposition:", self.proposition_input)

        main_layout.addWidget(form_widget)

        main_layout.addWidget(QLabel("<b>Reading References:</b>"))

        # --- Bottom Part: Readings Scroll Area ---
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        self.readings_layout = QVBoxLayout(scroll_widget)
        self.readings_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area, 1)

        # --- Dialog Buttons ---
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)

        # --- Load Data ---
        self.load_all_readings()
        if self.proposition_id:
            self.load_existing_proposition_data()

    def load_all_readings(self):
        """
        Fetches all readings and their outline sections, creating the
        PropositionReadingGroup widgets.
        """
        readings = self.db.get_readings(self.project_id)
        outline_map = self.db.get_all_outline_items_for_project(self.project_id)

        for reading in readings:
            reading_id = reading['id']
            outline_items = outline_map.get(reading_id, [])

            group_widget = PropositionReadingGroup(reading, outline_items, self)
            self.readings_layout.addWidget(group_widget)
            self.reading_groups.append(group_widget)

    def load_existing_proposition_data(self):
        """If editing, loads the proposition's data and its references."""
        data = self.db.get_proposition_details(self.proposition_id)
        if not data:
            QMessageBox.critical(self, "Error", "Could not load proposition data.")
            self.reject()
            return

        self.display_name_input.setText(data.get("display_name", ""))
        self.proposition_input.setHtml(data.get("proposition_html", ""))

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
        """
        Collects all data from the dialog into a single dict
        ready to be saved to the database.
        """
        all_references = []
        for group in self.reading_groups:
            all_references.extend(group.get_data())

        all_statuses = [group.get_status() for group in self.reading_groups]

        return {
            "display_name": self.display_name_input.text().strip(),
            "proposition_html": self.proposition_input.toHtml(),
            "references": all_references,
            "statuses": all_statuses
        }