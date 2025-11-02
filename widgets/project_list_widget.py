import sys
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QHBoxLayout, QMenu, QMessageBox, QInputDialog,
    QApplication, QDialog, QTreeWidgetItemIterator  # <-- FIXED: Added QTreeWidgetItemIterator
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction

from database_manager import DatabaseManager

# --- NEW: Import all our new dialogs ---
try:
    from dialogs.create_item_dialog import CreateItemDialog
    from dialogs.edit_assignment_dialog import EditAssignmentDialog
    from dialogs.move_project_dialog import MoveProjectDialog
    from dialogs.reorder_dialog import ReorderDialog
except ImportError as e:
    print(f"Failed to import dialogs: {e}")
    print("Make sure all dialog files are in the 'dialogs' directory.")
    sys.exit(1)


# --- END NEW ---


class ProjectListWidget(QWidget):
    """
    This widget replaces your 'HomeScreen' frame.
    It contains the project tree and buttons, porting
    the logic from home_screen.py.
    """

    projectSelected = Signal(dict)

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.selected_tree_item = None  # This will be the QTreeWidgetItem

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

        btn_connections = QPushButton("Connections")
        main_layout.addWidget(btn_connections)

        # --- Bindings (PySide6 uses signals/slots and policies) ---
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        self.tree.itemDoubleClicked.connect(self.on_double_click)

        # --- Connect button clicks ---
        btn_add_project.clicked.connect(lambda: self.handle_create_item('project', from_button=True))
        btn_add_class.clicked.connect(lambda: self.handle_create_item('class', from_button=True))
        btn_connections.clicked.connect(self.open_connections_window)

    def load_data_to_tree(self):
        """
        Clear and reload all items from the database into the tree.
        (Ported from home_screen.py)
        """
        expanded_ids = set()
        if self.tree.topLevelItemCount() > 0:
            # Use an iterator to find all items
            it = QTreeWidgetItemIterator(self.tree)  # <-- This line caused the error
            while it.value():
                item = it.value()
                if item.isExpanded():
                    db_id = item.data(0, Qt.ItemDataRole.UserRole)
                    if db_id:
                        expanded_ids.add(int(db_id))
                it += 1

        self.tree.clear()
        self._load_children(parent_widget_item=self.tree, parent_db_id=None)

        # Restore expanded state
        it = QTreeWidgetItemIterator(self.tree)  # <-- This line also needed the import
        while it.value():
            item = it.value()
            db_id = item.data(0, Qt.ItemDataRole.UserRole)
            if db_id and int(db_id) in expanded_ids:
                item.setExpanded(True)
            it += 1

    def _load_children(self, parent_widget_item, parent_db_id):
        """
        Recursive helper function to load items.
        (Ported from _load_children in home_screen.py)
        """
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
        """
        Display the right-click context menu.
        (Fully updated based on user request)
        """
        self.selected_tree_item = self.tree.itemAt(position)
        menu = QMenu()

        if self.selected_tree_item:
            # Right-clicked on an item
            db_id = self.selected_tree_item.data(0, Qt.ItemDataRole.UserRole)
            item_type = self.selected_tree_item.data(0, Qt.ItemDataRole.UserRole + 1)

            if not db_id: return

            if item_type == 'project':
                menu.addAction("Edit Project", self.rename_item)
                menu.addAction("Copy Project", self.duplicate_item)
                menu.addAction("Move Project", self.move_project)
                menu.addAction("Edit Assignment Status", self.edit_assignment_status)

            elif item_type == 'class':
                menu.addAction("Edit Class", self.rename_item)
                menu.addAction("Add Project to Class", lambda: self.handle_create_item('project', from_button=False))

            menu.addSeparator()
            menu.addAction("Reorder", self.reorder_items)
            menu.addSeparator()
            menu.addAction("Delete", self.delete_item)

        else:
            # Right-clicked on empty space
            menu.addAction("Add New Project (Standalone)",
                           lambda: self.handle_create_item('project', from_button=True))
            menu.addAction("Add New Class",
                           lambda: self.handle_create_item('class', from_button=True))
            menu.addSeparator()
            menu.addAction("Reorder Root Items", self.reorder_items)

        menu.exec(self.tree.viewport().mapToGlobal(position))

    def on_double_click(self, item, column):
        """
        Handle double-click event to open a project.
        """
        item_type = item.data(0, Qt.ItemDataRole.UserRole + 1)

        if 'project' in item_type:
            db_id = item.data(0, Qt.ItemDataRole.UserRole)
            project_details = self.db.get_item_details(db_id)
            if project_details:
                self.projectSelected.emit(dict(project_details))
            else:
                QMessageBox.critical(self, "Error", f"Could not load project with ID {db_id}")

    # --- NEW/UPDATED ACTION HANDLERS ---

    def handle_create_item(self, item_type, from_button=False):
        """
        Central handler for creating a new project or class.
        (Ported from home_screen.py and uses new dialog)
        """
        parent_db_id = None
        if not from_button and self.selected_tree_item:
            # Check if selected item is a class
            item_type_selected = self.selected_tree_item.data(0, Qt.ItemDataRole.UserRole + 1)
            if item_type_selected == 'class':
                parent_db_id = self.selected_tree_item.data(0, Qt.ItemDataRole.UserRole)

        dialog = CreateItemDialog(item_type, self)

        # .exec() shows the dialog modally and returns True if Ok was clicked
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name = dialog.name
            is_assignment = dialog.is_assignment

            self.db.create_item(name, item_type, parent_db_id, is_assignment)
            self.load_data_to_tree()

    def rename_item(self):
        """
        Rename the selected item using QInputDialog.
        (Ported from home_screen.py)
        """
        if not self.selected_tree_item: return
        db_id = self.selected_tree_item.data(0, Qt.ItemDataRole.UserRole)
        old_name = self.selected_tree_item.text(0)

        new_name, ok = QInputDialog.getText(self, "Rename Item", "Enter new name:", text=old_name)

        if ok and new_name and new_name != old_name:
            self.db.rename_item(db_id, new_name)
            self.load_data_to_tree()

    def delete_item(self):
        """
        Delete the selected item with confirmation.
        (Ported from home_screen.py)
        """
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
        """
        Duplicates the selected item.
        (Ported from home_screen.py)
        """
        if not self.selected_tree_item: return
        db_id = self.selected_tree_item.data(0, Qt.ItemDataRole.UserRole)
        self.db.duplicate_item(db_id)
        self.load_data_to_tree()

    def move_project(self):
        """
        Move the selected project to a new parent (or root).
        (Ported from home_screen.py and uses new dialog)
        """
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

    def edit_assignment_status(self):
        """
        Open the dialog to edit the 'is_assignment' status of a project.
        (Ported from home_screen.py and uses new dialog)
        """
        if not self.selected_tree_item: return
        db_id = self.selected_tree_item.data(0, Qt.ItemDataRole.UserRole)
        item_details = self.db.get_item_details(db_id)
        if not item_details: return

        current_status = item_details['is_assignment'] if item_details['is_assignment'] is not None else 1

        dialog = EditAssignmentDialog(current_status, self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_status_val = dialog.new_status
            if new_status_val != current_status:
                if current_status == 1 and new_status_val == 0:
                    reply = QMessageBox.question(self, "Warning",
                                                 "This will permanently delete existing assignment data for this project.\nAre you sure you want to continue?",
                                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                                 QMessageBox.StandardButton.No)
                    if reply == QMessageBox.StandardButton.No:
                        return

                # We need a new DB method for this
                # self.db.update_assignment_status(db_id, new_status_val)
                print(f"DB: Update project {db_id} assignment status to {new_status_val}")
                QMessageBox.information(self, "TODO",
                                        "This needs 'update_assignment_status' in database_manager.py")

    def reorder_items(self):
        """
        Opens the reorder dialog for the selected item's siblings.
        (New function, handles request for root and child reordering)
        """
        items_to_reorder = []

        if self.selected_tree_item:
            # Reordering children of a class or items at root
            parent_item = self.selected_tree_item.parent()
            if parent_item:
                # Reordering children of a class
                parent_db_id = parent_item.data(0, Qt.ItemDataRole.UserRole)
                db_items = self.db.get_items(parent_db_id)
                items_to_reorder = [(item['name'], item['id']) for item in db_items]
            else:
                # Reordering items at root
                db_items = self.db.get_items(parent_id=None)
                items_to_reorder = [(item['name'], item['id']) for item in db_items]
        else:
            # Right-clicked empty space, reordering root
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

    def open_connections_window(self):
        """Placeholder for opening the connections management window."""
        QMessageBox.information(self, "Connections", "This feature is not yet implemented.")

