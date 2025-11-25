import sys
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QLabel,
    QTreeWidget, QTreeWidgetItem, QFrame, QMenu,
    QInputDialog, QMessageBox, QPushButton, QDialog
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction

from tabs.rich_text_editor_tab import RichTextEditorTab

try:
    from dialogs.reorder_dialog import ReorderDialog
except ImportError:
    ReorderDialog = None

try:
    from dialogs.add_citation_dialog import AddCitationDialog
except ImportError:
    AddCitationDialog = None


class AssignmentTab(QWidget):
    """
    This is the "Assignment" tab, which holds the rubric
    and the assignment text editors.
    """

    def __init__(self, db_manager, project_id, spell_checker_service=None, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.project_id = project_id
        self.spell_checker_service = spell_checker_service
        self._block_rubric_item_changed = False

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(self.splitter, 1)

        # --- Left Panel (Rubric) ---
        left_panel = QFrame()
        left_panel.setFrameShape(QFrame.Shape.StyledPanel)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(6, 6, 6, 6)
        left_layout.setSpacing(4)

        rubric_label = QLabel("Rubric")
        rubric_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        left_layout.addWidget(rubric_label)

        self.rubric_tree = QTreeWidget()
        self.rubric_tree.setHeaderHidden(True)
        self.rubric_tree.setColumnCount(1)
        left_layout.addWidget(self.rubric_tree)

        self.rubric_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.rubric_tree.customContextMenuRequested.connect(self.show_rubric_context_menu)
        self.rubric_tree.itemChanged.connect(self.on_rubric_item_changed)

        # --- Right Panel (Editors) ---
        right_panel = QFrame()
        right_panel.setFrameShape(QFrame.Shape.StyledPanel)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(6, 6, 6, 6)

        editor_splitter = QSplitter(Qt.Orientation.Vertical)
        right_layout.addWidget(editor_splitter)

        # Top Editor
        instructions_widget = QWidget()
        instructions_layout = QVBoxLayout(instructions_widget)
        instructions_layout.setContentsMargins(0, 0, 0, 0)
        instructions_layout.setSpacing(4)
        instructions_label = QLabel("Assignment Instructions")
        instructions_label.setStyleSheet("font-weight: bold;")
        self.instructions_editor = RichTextEditorTab("Assignment Instructions",
                                                     spell_checker_service=self.spell_checker_service)
        instructions_layout.addWidget(instructions_label)
        instructions_layout.addWidget(self.instructions_editor)
        instructions_widget.setLayout(instructions_layout)

        # Bottom Editor
        draft_widget = QWidget()
        draft_layout = QVBoxLayout(draft_widget)
        draft_layout.setContentsMargins(0, 0, 0, 0)
        draft_layout.setSpacing(4)
        draft_label = QLabel("Assignment Draft")
        draft_label.setStyleSheet("font-weight: bold;")
        self.draft_editor = RichTextEditorTab("Assignment Draft", spell_checker_service=self.spell_checker_service)

        draft_layout.addWidget(draft_label)
        draft_layout.addWidget(self.draft_editor)
        draft_widget.setLayout(draft_layout)

        editor_splitter.addWidget(instructions_widget)
        editor_splitter.addWidget(draft_widget)
        editor_splitter.setStretchFactor(0, 1)
        editor_splitter.setStretchFactor(1, 2)

        self.splitter.addWidget(left_panel)
        self.splitter.addWidget(right_panel)
        self.splitter.setSizes([300, 700])

        # --- Bottom Button Bar ---
        button_bar = QWidget()
        button_bar.setStyleSheet("padding: 2px;")
        button_layout = QHBoxLayout(button_bar)
        button_layout.setContentsMargins(0, 0, 0, 0)

        btn_create_component = QPushButton("Create Component")
        btn_save_assignment = QPushButton("Save Assignment")
        btn_add_citation = QPushButton("Add Citation")

        btn_create_component.clicked.connect(self.add_component)
        btn_save_assignment.clicked.connect(self.save_editors)
        btn_add_citation.clicked.connect(self.open_citation_dialog)

        button_layout.addWidget(btn_create_component)
        button_layout.addStretch()
        button_layout.addWidget(btn_add_citation)
        button_layout.addWidget(btn_save_assignment)

        main_layout.addWidget(button_bar)

    def load_data(self, project_details):
        self.load_rubric()
        instr_html = project_details.get('assignment_instructions_text', '')
        draft_html = project_details.get('assignment_draft_text', '')
        self.instructions_editor.set_html(instr_html or "")
        self.draft_editor.set_html(draft_html or "")

    def save_editors(self):
        print("Saving assignment editors...")
        self.instructions_editor.get_html(
            lambda html: self.db.update_project_text_field(
                self.project_id, 'assignment_instructions_text', html
            ) if html is not None else None
        )
        self.draft_editor.get_html(
            lambda html: self.db.update_project_text_field(
                self.project_id, 'assignment_draft_text', html
            ) if html is not None else None
        )

    def load_rubric(self):
        self._block_rubric_item_changed = True
        self.rubric_tree.clear()
        try:
            components = self.db.get_rubric_components(self.project_id)
            for comp in components:
                item = QTreeWidgetItem([comp['component_text']])
                item.setData(0, Qt.ItemDataRole.UserRole, comp['id'])
                item.setCheckState(0, Qt.CheckState.Checked if comp['is_checked'] else Qt.CheckState.Unchecked)
                self.rubric_tree.addTopLevelItem(item)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load rubric: {e}")
        finally:
            self._block_rubric_item_changed = False

    def on_rubric_item_changed(self, item, column):
        if self._block_rubric_item_changed or column != 0:
            return
        component_id = item.data(0, Qt.ItemDataRole.UserRole)
        is_checked = item.checkState(0) == Qt.CheckState.Checked
        try:
            self.db.update_rubric_component_checked(component_id, is_checked)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not update check state: {e}")

    def show_rubric_context_menu(self, position):
        menu = QMenu(self)
        item = self.rubric_tree.itemAt(position)
        add_action = QAction("Add Component", self)
        add_action.triggered.connect(self.add_component)
        menu.addAction(add_action)

        if item:
            menu.addSeparator()
            edit_action = QAction("Edit Component", self)
            edit_action.triggered.connect(self.edit_component)
            menu.addAction(edit_action)
            delete_action = QAction("Delete Component", self)
            delete_action.triggered.connect(self.delete_component)
            menu.addAction(delete_action)

        if ReorderDialog and self.rubric_tree.topLevelItemCount() > 0:
            menu.addSeparator()
            reorder_action = QAction("Reorder Components", self)
            reorder_action.triggered.connect(self.reorder_components)
            menu.addAction(reorder_action)

        menu.exec(self.rubric_tree.viewport().mapToGlobal(position))

    def add_component(self):
        text, ok = QInputDialog.getMultiLineText(self, "Add Rubric Component", "Component Text:")
        if ok and text:
            try:
                self.db.add_rubric_component(self.project_id, text)
                self.load_rubric()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not add component: {e}")

    def edit_component(self):
        item = self.rubric_tree.currentItem()
        if not item: return
        component_id = item.data(0, Qt.ItemDataRole.UserRole)
        current_text = item.text(0)
        text, ok = QInputDialog.getMultiLineText(self, "Edit Rubric Component", "Component Text:", current_text)
        if ok and text and text != current_text:
            try:
                self.db.update_rubric_component_text(component_id, text)
                self.load_rubric()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not update component: {e}")

    def delete_component(self):
        item = self.rubric_tree.currentItem()
        if not item: return
        component_id = item.data(0, Qt.ItemDataRole.UserRole)
        reply = QMessageBox.question(
            self, "Delete Component",
            f"Are you sure you want to delete this component?\n\n'{item.text(0)}'",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.db.delete_rubric_component(component_id)
                self.load_rubric()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not delete component: {e}")

    def reorder_components(self):
        if not ReorderDialog:
            QMessageBox.critical(self, "Error", "Reorder dialog is not available.")
            return
        try:
            items = self.db.get_rubric_components(self.project_id)
            if not items: return
            items_to_reorder = [(item['component_text'], item['id']) for item in items]
            dialog = ReorderDialog(items_to_reorder, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                ordered_ids = dialog.ordered_db_ids
                self.db.update_rubric_component_order(ordered_ids)
                self.load_rubric()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not reorder components: {e}")

    # --- Citation Logic ---
    def open_citation_dialog(self):
        if not AddCitationDialog:
            QMessageBox.critical(self, "Error", "Citation dialog could not be loaded.")
            return

        readings = self.db.get_readings(self.project_id)
        if not readings:
            QMessageBox.information(self, "No Readings",
                                    "You must add readings to this project before you can cite them.")
            return

        dialog = AddCitationDialog(readings, parent=self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            text = dialog.result_text
            if text:
                self.draft_editor.editor.insertPlainText(f" {text} ")
                self.draft_editor.focus_editor()