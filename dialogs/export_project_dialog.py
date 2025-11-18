# dialogs/export_project_dialog.py
import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QRadioButton, QDialogButtonBox, QPushButton,
    QButtonGroup, QAbstractItemView, QFrame, QTreeWidget, QTreeWidgetItem,
    QTreeWidgetItemIterator
)
from PySide6.QtCore import Qt, Slot


class ExportProjectDialog(QDialog):
    """
    A dialog to configure a project export.
    Allows selecting format, components, and reordering components.
    """

    def __init__(self, db, project_id, parent=None):
        super().__init__(parent)
        self.db = db
        self.project_id = project_id

        self.setWindowTitle("Export Project")
        self.setMinimumSize(500, 600)

        main_layout = QVBoxLayout(self)

        # 1. Format Selection
        format_frame = QFrame()
        format_frame.setFrameShape(QFrame.Shape.StyledPanel)
        format_layout = QHBoxLayout(format_frame)
        format_layout.addWidget(QLabel("<b>Select Format:</b>"))

        self.format_group = QButtonGroup(self)
        self.radio_html = QRadioButton("HTML")
        self.radio_docx = QRadioButton("DOCX (Word)")
        self.radio_txt = QRadioButton("TXT (Plain Text)")

        self.radio_html.setChecked(True)  # Default

        self.format_group.addButton(self.radio_html, 1)
        self.format_group.addButton(self.radio_docx, 2)
        self.format_group.addButton(self.radio_txt, 3)

        format_layout.addWidget(self.radio_html)
        format_layout.addWidget(self.radio_docx)
        format_layout.addWidget(self.radio_txt)
        format_layout.addStretch()
        main_layout.addWidget(format_frame)

        # 2. Component Selection
        main_layout.addWidget(QLabel("<b>Select and Reorder Components to Export:</b>"))

        self.component_tree = QTreeWidget()
        self.component_tree.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.component_tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.component_tree.setHeaderHidden(True)
        main_layout.addWidget(self.component_tree)

        # 3. Selection / Reorder Buttons
        select_btn_layout = QHBoxLayout()
        self.btn_select_all = QPushButton("Select All")
        self.btn_deselect_all = QPushButton("Deselect All")
        self.btn_move_up = QPushButton("Move Up")
        self.btn_move_down = QPushButton("Move Down")

        select_btn_layout.addStretch()
        select_btn_layout.addWidget(self.btn_move_up)
        select_btn_layout.addWidget(self.btn_move_down)
        select_btn_layout.addSpacing(20)
        select_btn_layout.addWidget(self.btn_select_all)
        select_btn_layout.addWidget(self.btn_deselect_all)
        main_layout.addLayout(select_btn_layout)

        # 4. Standard OK/Cancel
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setText("Export")
        main_layout.addWidget(self.button_box)

        # --- Connections ---
        self.btn_select_all.clicked.connect(self._toggle_all_checks)
        self.btn_deselect_all.clicked.connect(lambda: self._toggle_all_checks(False))
        self.btn_move_up.clicked.connect(self._move_item_up)
        self.btn_move_down.clicked.connect(self._move_item_down)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        self._populate_component_list()

    def _populate_component_list(self):
        """Fetches all exportable components and adds them to the list."""
        self.component_tree.clear()

        # Get project details
        project = self.db.get_item_details(self.project_id)

        # --- (A) Project-Level Components ---
        self.add_component_item(self.component_tree, "Project Purpose", "project_purpose_text")
        self.add_component_item(self.component_tree, "Project Goals", "project_goals_text")

        # --- (B) Assignment Components ---
        if project.get('is_assignment', 0) == 1:
            self.add_component_item(self.component_tree, "Assignment Instructions", "assignment_instructions_text")
            self.add_component_item(self.component_tree, "Assignment Rubric", "assignment_rubric")
            self.add_component_item(self.component_tree, "Assignment Draft", "assignment_draft_text")

        # --- (C) Project Dashboard Components ---
        self.add_component_item(self.component_tree, "Key Questions", "key_questions_text")
        self.add_component_item(self.component_tree, "Thesis / Argument", "thesis_text")
        self.add_component_item(self.component_tree, "Key Insights", "insights_text")
        self.add_component_item(self.component_tree, "Unresolved Questions", "unresolved_text")

        # --- (D) Reading-Specific Components ---
        readings = self.db.get_readings(self.project_id)
        for reading in readings:
            reading_id = reading['id']
            name = reading['nickname'] or reading['title']

            # Add the main reading item
            reading_item = self.add_component_item(self.component_tree, f"Reading: {name}",
                                                   f"reading_header_{reading_id}")
            reading_item.setFlags(reading_item.flags() | Qt.ItemFlag.ItemIsAutoTristate)  # Auto-check/uncheck children

            # Add reading sub-components
            self.add_component_item(reading_item, "Outline & Notes", f"reading_outline_{reading_id}")
            self.add_component_item(reading_item, "Driving Questions", f"reading_driving_questions_{reading_id}")
            self.add_component_item(reading_item, "Leading Propositions", f"reading_leading_propositions_{reading_id}")
            self.add_component_item(reading_item, "Key Terms", f"reading_key_terms_{reading_id}")
            self.add_component_item(reading_item, "Arguments", f"reading_arguments_{reading_id}")
            self.add_component_item(reading_item, "Theories", f"reading_theories_{reading_id}")
            self.add_component_item(reading_item, "Unity", f"reading_unity_{reading_id}")

            reading_item.setExpanded(True)

        # --- (E) Synthesis Tab Components ---
        self.add_component_item(self.component_tree, "Synthesis: My Terminology", "synthesis_terminology")
        self.add_component_item(self.component_tree, "Synthesis: My Propositions", "synthesis_propositions")
        self.add_component_item(self.component_tree, "Synthesis: Notes", "synthesis_notes_html")

        # --- (F) To-Do List ---
        self.add_component_item(self.component_tree, "To-Do List", "todo_list")

    def add_component_item(self, parent_widget, title, data_key):
        """Helper to add a checkable item to the tree."""
        item = QTreeWidgetItem(parent_widget, [title])
        item.setData(0, Qt.ItemDataRole.UserRole, data_key)
        item.setCheckState(0, Qt.CheckState.Checked)  # Default to checked
        return item

    def _toggle_all_checks(self, check=True):
        """Selects or deselects all items in the component list."""
        state = Qt.CheckState.Checked if check else Qt.CheckState.Unchecked

        iterator = QTreeWidgetItemIterator(self.component_tree)
        while iterator.value():
            item = iterator.value()
            item.setCheckState(0, state)
            iterator += 1

    def _move_item_up(self):
        item = self.component_tree.currentItem()
        if not item:
            return

        parent = item.parent()
        if parent:
            index = parent.indexOfChild(item)
            if index > 0:
                parent.takeChild(index)
                parent.insertChild(index - 1, item)
                self.component_tree.setCurrentItem(item)
        else:
            index = self.component_tree.indexOfTopLevelItem(item)
            if index > 0:
                self.component_tree.takeTopLevelItem(index)
                self.component_tree.insertTopLevelItem(index - 1, item)
                self.component_tree.setCurrentItem(item)

    def _move_item_down(self):
        item = self.component_tree.currentItem()
        if not item:
            return

        parent = item.parent()
        if parent:
            index = parent.indexOfChild(item)
            if index < parent.childCount() - 1:
                parent.takeChild(index)
                parent.insertChild(index + 1, item)
                self.component_tree.setCurrentItem(item)
        else:
            index = self.component_tree.indexOfTopLevelItem(item)
            if index < self.component_tree.topLevelItemCount() - 1:
                self.component_tree.takeTopLevelItem(index)
                self.component_tree.insertTopLevelItem(index + 1, item)
                self.component_tree.setCurrentItem(item)

    def get_export_config(self):
        """Returns the selected format and component list."""
        # Get selected format
        selected_format = "html"  # default
        if self.radio_docx.isChecked():
            selected_format = "docx"
        elif self.radio_txt.isChecked():
            selected_format = "txt"

        # Get selected and ordered components
        components = []

        def traverse(parent_item):
            for i in range(parent_item.childCount()):
                item = parent_item.child(i)
                if item.checkState(0) == Qt.CheckState.Checked:
                    components.append({
                        "title": item.text(0),
                        "key": item.data(0, Qt.ItemDataRole.UserRole)
                    })
                if item.childCount() > 0:
                    traverse(item)

        # Traverse tree from the invisible root item
        traverse(self.component_tree.invisibleRootItem())

        return {
            "format": selected_format,
            "components": components
        }