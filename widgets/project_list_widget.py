import sys
import os
import subprocess
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QHBoxLayout, QMenu, QMessageBox, QInputDialog,
    QApplication, QDialog, QTreeWidgetItemIterator
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction

from database_manager import DatabaseManager

# --- Import dialogs ---
try:
    from dialogs.create_item_dialog import CreateItemDialog
    from dialogs.edit_assignment_dialog import EditProjectStatusDialog
    from dialogs.move_project_dialog import MoveProjectDialog
    from dialogs.reorder_dialog import ReorderDialog
except ImportError as e:
    print(f"Failed to import dialogs: {e}")
    print("Make sure all dialog files are in the 'dialogs' directory.")
    sys.exit(1)


class ProjectListWidget(QWidget):
    """
    This widget replaces your 'HomeScreen' frame.
    """

    projectSelected = Signal(dict)

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.selected_tree_item = None

        self.create_widgets()
        self.load_data_to_tree()

    def create_widgets(self):
        main_layout = QVBoxLayout(self)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("My Projects and Classes")
        self.tree.setColumnCount(1)
        self.tree.setHeaderHidden(True)

        main_layout.addWidget(self.tree)

        # --- Button Frame ---
        button_layout = QHBoxLayout()
        btn_add_project = QPushButton("Add Project")
        btn_add_class = QPushButton("Add Class")

        button_layout.addWidget(btn_add_project)
        button_layout.addWidget(btn_add_class)
        main_layout.addLayout(button_layout)

        btn_qda = QPushButton("Launch QDA Tool")
        main_layout.addWidget(btn_qda)

        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        self.tree.itemDoubleClicked.connect(self.on_double_click)

        btn_add_project.clicked.connect(lambda: self.handle_create_item('project', from_button=True))
        btn_add_class.clicked.connect(lambda: self.handle_create_item('class', from_button=True))
        btn_qda.clicked.connect(self.launch_qda_tool)

    def load_data_to_tree(self):
        expanded_ids = set()
        if self.tree.topLevelItemCount() > 0:
            it = QTreeWidgetItemIterator(self.tree)
            while it.value():
                item = it.value()
                if item.isExpanded():
                    db_id = item.data(0, Qt.ItemDataRole.UserRole)
                    if db_id:
                        expanded_ids.add(int(db_id))
                it += 1

        self.tree.clear()
        self._load_children(parent_widget_item=self.tree, parent_db_id=None)

        it = QTreeWidgetItemIterator(self.tree)
        while it.value():
            item = it.value()
            db_id = item.data(0, Qt.ItemDataRole.UserRole)
            if db_id and int(db_id) in expanded_ids:
                item.setExpanded(True)
            it += 1

    def _load_children(self, parent_widget_item, parent_db_id):
        items = self.db.get_items(parent_db_id)
        for item in items:
            tree_item = QTreeWidgetItem(parent_widget_item)
            tree_item.setText(0, item['name'])
            tree_item.setData(0, Qt.ItemDataRole.UserRole, item['id'])
            tree_item.setData(0, Qt.ItemDataRole.UserRole + 1, item['type'])
            tree_item.setData(0, Qt.ItemDataRole.UserRole + 2, item['parent_id'])

            if item['type'] == 'class':
                self._load_children(
                    parent_widget_item=tree_item,
                    parent_db_id=item['id']
                )

    def show_context_menu(self, position):
        self.selected_tree_item = self.tree.itemAt(position)
        menu = QMenu()

        if self.selected_tree_item:
            db_id = self.selected_tree_item.data(0, Qt.ItemDataRole.UserRole)
            item_type = self.selected_tree_item.data(0, Qt.ItemDataRole.UserRole + 1)

            if not db_id: return

            if item_type == 'project':
                menu.addAction("Edit Project Name", self.rename_item)
                menu.addAction("Copy Project", self.duplicate_item)
                menu.addAction("Move Project", self.move_project)
                # Changed menu text
                menu.addAction("Edit Project Configuration", self.edit_project_status)

            elif item_type == 'class':
                menu.addAction("Edit Class", self.rename_item)
                menu.addAction("Add Project to Class", lambda: self.handle_create_item('project', from_button=False))

            menu.addSeparator()
            menu.addAction("Reorder", self.reorder_items)
            menu.addSeparator()
            menu.addAction("Delete", self.delete_item)

        else:
            menu.addAction("Add New Project (Standalone)",
                           lambda: self.handle_create_item('project', from_button=True))
            menu.addAction("Add New Class",
                           lambda: self.handle_create_item('class', from_button=True))
            menu.addSeparator()
            menu.addAction("Reorder Root Items", self.reorder_items)

        menu.exec(self.tree.viewport().mapToGlobal(position))

    def on_double_click(self, item, column):
        item_type = item.data(0, Qt.ItemDataRole.UserRole + 1)

        if 'project' in item_type:
            db_id = item.data(0, Qt.ItemDataRole.UserRole)
            project_details = self.db.get_item_details(db_id)
            if project_details:
                self.projectSelected.emit(dict(project_details))
            else:
                QMessageBox.critical(self, "Error", f"Could not load project with ID {db_id}")

    def handle_create_item(self, item_type, from_button=False):
        parent_db_id = None
        if not from_button and self.selected_tree_item:
            item_type_selected = self.selected_tree_item.data(0, Qt.ItemDataRole.UserRole + 1)
            if item_type_selected == 'class':
                parent_db_id = self.selected_tree_item.data(0, Qt.ItemDataRole.UserRole)

        dialog = CreateItemDialog(item_type, self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            name = dialog.name
            is_assignment = dialog.is_assignment
            is_research = getattr(dialog, 'is_research', 0)
            is_annotated_bib = getattr(dialog, 'is_annotated_bib', 0)

            try:
                new_id = self.db.create_item(name, item_type, parent_db_id, is_assignment, is_research,
                                             is_annotated_bib)
                self.load_data_to_tree()

                if item_type == 'project':
                    project_details = self.db.get_item_details(new_id)
                    if project_details:
                        self.projectSelected.emit(dict(project_details))
                    else:
                        QMessageBox.critical(self, "Error", f"Could not find newly created project with ID {new_id}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not create item: {e}")
                self.load_data_to_tree()

    def rename_item(self):
        if not self.selected_tree_item: return
        db_id = self.selected_tree_item.data(0, Qt.ItemDataRole.UserRole)
        old_name = self.selected_tree_item.text(0)

        new_name, ok = QInputDialog.getText(self, "Rename Item", "Enter new name:", text=old_name)

        if ok and new_name and new_name != old_name:
            self.db.rename_item(db_id, new_name)
            self.load_data_to_tree()

    def delete_item(self):
        if not self.selected_tree_item: return
        db_id = self.selected_tree_item.data(0, Qt.ItemDataRole.UserRole)
        item_type = self.selected_tree_item.data(0, Qt.ItemDataRole.UserRole + 1)
        item_name = self.selected_tree_item.text(0)

        if item_type == 'class':
            msg = f"Are you sure you want to delete the class '{item_name}'?\n\n" \
                  "ALL projects inside this class will also be permanently deleted."
            title = "Delete Class?"
        else:
            msg = f"Are you sure you want to delete the project '{item_name}'?"
            title = "Delete Project?"

        reply = QMessageBox.question(self, title, msg,
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            self.db.delete_item(db_id)
            self.load_data_to_tree()

    def duplicate_item(self):
        if not self.selected_tree_item: return
        db_id = self.selected_tree_item.data(0, Qt.ItemDataRole.UserRole)
        self.db.duplicate_item(db_id)
        self.load_data_to_tree()

    def move_project(self):
        if not self.selected_tree_item: return
        db_id = self.selected_tree_item.data(0, Qt.ItemDataRole.UserRole)
        current_parent_id = self.selected_tree_item.data(0, Qt.ItemDataRole.UserRole + 2)

        all_classes = self.db.get_all_classes()
        dialog = MoveProjectDialog(all_classes, self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_parent_id = dialog.new_parent_id
            if new_parent_id != current_parent_id:
                self.db.move_item(db_id, new_parent_id)
                self.load_data_to_tree()

    def edit_project_status(self):
        """
        Replaces edit_assignment_status to handle all project flags using EditProjectStatusDialog.
        """
        if not self.selected_tree_item: return
        db_id = self.selected_tree_item.data(0, Qt.ItemDataRole.UserRole)
        item_details = self.db.get_item_details(db_id)
        if not item_details: return

        current_assign = item_details.get('is_assignment', 0)
        current_research = item_details.get('is_research', 0)
        current_bib = item_details.get('is_annotated_bib', 0)

        dialog = EditProjectStatusDialog(current_assign, current_research, current_bib, self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_assign = dialog.new_assignment_status
            new_research = dialog.new_research_status
            new_bib = dialog.new_bib_status

            if (new_assign != current_assign or
                    new_research != current_research or
                    new_bib != current_bib):

                # Warning only if turning OFF assignment (data loss risk)
                if current_assign == 1 and new_assign == 0:
                    reply = QMessageBox.question(self, "Warning",
                                                 "Unchecking 'Assignment' will delete associated rubric/instruction data.\nContinue?",
                                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                                 QMessageBox.StandardButton.No)
                    if reply == QMessageBox.StandardButton.No:
                        return

                self.db.update_project_status(db_id, new_assign, new_research, new_bib)
                self.load_data_to_tree()

    # Alias for backward compatibility if needed
    edit_assignment_status = edit_project_status

    def reorder_items(self):
        items_to_reorder = []

        if self.selected_tree_item:
            parent_item = self.selected_tree_item.parent()
            if parent_item:
                parent_db_id = parent_item.data(0, Qt.ItemDataRole.UserRole)
                db_items = self.db.get_items(parent_db_id)
                items_to_reorder = [(item['name'], item['id']) for item in db_items]
            else:
                db_items = self.db.get_items(parent_id=None)
                items_to_reorder = [(item['name'], item['id']) for item in db_items]
        else:
            db_items = self.db.get_items(parent_id=None)
            items_to_reorder = [(item['name'], item['id']) for item in db_items]

        if not items_to_reorder:
            QMessageBox.information(self, "Reorder", "There are no items to reorder in this group.")
            return

        dialog = ReorderDialog(items_to_reorder, self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            ordered_ids = dialog.ordered_db_ids
            self.db.update_order(ordered_ids)
            self.load_data_to_tree()

    def launch_qda_tool(self):
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            qda_dir = os.path.join(base_dir, 'qda_tool')
            script_name = "qda_coding_app.py"
            script_path = os.path.join(qda_dir, script_name)

            if not os.path.exists(script_path):
                QMessageBox.critical(self, "Error", f"Could not find QDA Tool at:\n{script_path}")
                return

            subprocess.Popen([sys.executable, script_name], cwd=qda_dir)

        except Exception as e:
            QMessageBox.critical(self, "Launch Error", f"Failed to launch QDA Tool:\n{e}")

    def open_connections_window(self):
        QMessageBox.information(self, "Connections", "Please use the 'Launch QDA Tool' button instead.")