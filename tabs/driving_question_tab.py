# tabs/driving_question_tab.py
import sys
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTreeWidget,
    QTreeWidgetItem, QMenu, QMessageBox, QDialog, QLabel, QFrame
)
from PySide6.QtCore import Qt, Signal, QPoint, Slot
from PySide6.QtGui import QAction, QFont, QColor

try:
    from dialogs.edit_driving_question_dialog import EditDrivingQuestionDialog
except ImportError:
    print("Error: Could not import EditDrivingQuestionDialog")
    EditDrivingQuestionDialog = None

try:
    from dialogs.reorder_dialog import ReorderDialog
except ImportError:
    print("Error: Could not import ReorderDialog")
    ReorderDialog = None


class DrivingQuestionTab(QWidget):
    """
    Widget for managing "Driving Questions" for a reading.
    Includes a tree view and buttons for CRUD operations.
    """

    def __init__(self, db, reading_id: int, parent=None):
        super().__init__(parent)
        self.db = db
        self.reading_id = reading_id

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(4)

        # Button bar
        button_bar = QFrame()
        button_layout = QHBoxLayout(button_bar)
        button_layout.setContentsMargins(0, 0, 0, 0)

        self.btn_add = QPushButton("Add Driving Question")
        self.btn_edit = QPushButton("Edit")
        self.btn_delete = QPushButton("Delete")
        self.btn_move_up = QPushButton("Move Up")
        self.btn_move_down = QPushButton("Move Down")

        button_layout.addWidget(self.btn_add)
        button_layout.addWidget(self.btn_edit)
        button_layout.addWidget(self.btn_delete)
        button_layout.addStretch()
        button_layout.addWidget(self.btn_move_up)
        button_layout.addWidget(self.btn_move_down)
        main_layout.addWidget(button_bar)

        # Tree widget
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(["Question"])
        self.tree_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        main_layout.addWidget(self.tree_widget)

        # --- Connections ---
        self.btn_add.clicked.connect(self._add_question)
        self.btn_edit.clicked.connect(self._edit_question)
        self.btn_delete.clicked.connect(self._delete_question)
        self.btn_move_up.clicked.connect(self._move_up)
        self.btn_move_down.clicked.connect(self._move_down)

        self.tree_widget.itemDoubleClicked.connect(self._edit_question)
        self.tree_widget.customContextMenuRequested.connect(self.show_context_menu)
        self.tree_widget.currentItemChanged.connect(self._update_button_states)

        self.load_questions()
        self._update_button_states()

    def load_questions(self):
        """Reloads all questions from the database into the tree."""
        self.tree_widget.clear()
        try:
            root_questions = self.db.get_driving_questions(self.reading_id, parent_id=None)
            # --- FIX: Add loop protection ---
            visited_ids = set()
            # --- END FIX ---
            for q_data in root_questions:
                self._add_question_to_tree(self.tree_widget, q_data, visited_ids)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load driving questions: {e}")
        self._update_button_states()

    def _add_question_to_tree(self, parent_widget, q_data, visited_ids):
        """Recursive helper to build the tree. Includes loop protection."""

        q_id = q_data["id"]

        # --- FIX: Loop protection ---
        if q_id in visited_ids:
            print(f"Error: Detected recursion loop in driving questions! Question ID: {q_id}")
            # Add a placeholder item to show the error
            item = QTreeWidgetItem(parent_widget, [f"Error: Loop detected on item {q_id}"])
            item.setForeground(0, QColor("red"))
            return

        visited_ids.add(q_id)
        # --- END FIX ---

        # Format display text
        nickname = q_data.get("nickname", "")
        question_text = q_data.get("question_text", "No question text")
        is_working = q_data.get("is_working_question", False)

        display_text = ""
        # --- NEW: Star is on the left ---
        if is_working:
            display_text += "★ "  # Add a star for working question

        if nickname:
            display_text += f"({nickname}) "
        display_text += question_text

        item = QTreeWidgetItem(parent_widget, [display_text])
        item.setData(0, Qt.ItemDataRole.UserRole, q_data["id"])

        # Set font for working question
        if is_working:
            font = item.font(0)
            font.setBold(True)
            item.setFont(0, font)
            item.setForeground(0, QColor("#0055A4"))  # A blue color

        # Recursively add children
        child_questions = self.db.get_driving_questions(self.reading_id, parent_id=q_data["id"])
        for child_data in child_questions:
            # --- FIX: Pass a copy of the visited set for this branch ---
            self._add_question_to_tree(item, child_data, visited_ids.copy())

        item.setExpanded(True)

    def _get_all_questions_flat(self):
        """Fetches all questions for this reading as a flat list for the parent dropdown."""
        # --- FIX: Use parent_id=True to get ALL questions for loop checking ---
        return self.db.get_driving_questions(self.reading_id, parent_id=True)
        # --- END FIX ---

    def _get_outline_items(self, parent_id=None):
        """Recursively fetches outline items to build a nested list for the dialog."""
        items = self.db.get_reading_outline(self.reading_id, parent_id=parent_id)
        for item in items:
            # item is already a dict
            children = self._get_outline_items(parent_id=item['id'])
            if children:
                item['children'] = children
        return items

    def _update_button_states(self):
        """Enables/disables buttons based on selection."""
        item = self.tree_widget.currentItem()
        is_item_selected = item is not None

        self.btn_edit.setEnabled(is_item_selected)
        self.btn_delete.setEnabled(is_item_selected)

        # Move logic
        can_move_up = False
        can_move_down = False
        if is_item_selected:
            parent = item.parent()
            if parent:
                index = parent.indexOfChild(item)
                can_move_up = index > 0
                can_move_down = index < parent.childCount() - 1
            else:  # Root item
                index = self.tree_widget.indexOfTopLevelItem(item)
                can_move_up = index > 0
                can_move_down = index < self.tree_widget.topLevelItemCount() - 1

        self.btn_move_up.setEnabled(can_move_up)
        self.btn_move_down.setEnabled(can_move_down)

    def show_context_menu(self, position):
        menu = QMenu(self)
        item = self.tree_widget.itemAt(position)

        menu.addAction(self.btn_add.text(), self._add_question)

        if item:
            menu.addAction(self.btn_edit.text(), self._edit_question)
            menu.addAction(self.btn_delete.text(), self._delete_question)
            menu.addSeparator()
            add_child_action = QAction("Add Research Question (Child)", self)
            add_child_action.triggered.connect(self._add_child_question)
            menu.addAction(add_child_action)
            menu.addSeparator()

        # Reorder Action
        has_siblings = False
        if item:
            parent = item.parent()
            if parent:
                has_siblings = parent.childCount() > 1
            else:
                has_siblings = self.tree_widget.topLevelItemCount() > 1
        elif self.tree_widget.topLevelItemCount() > 1:
            has_siblings = True

        if has_siblings and ReorderDialog:
            reorder_action = QAction("Reorder Items...", self)
            reorder_action.triggered.connect(self._reorder_questions)
            menu.addAction(reorder_action)

        menu.exec(self.tree_widget.viewport().mapToGlobal(position))

    @Slot()
    def _handle_save(self, data, question_id=None):
        """Central logic for saving a question (add or edit)."""
        # --- Working Question Check ---
        if data.get("is_working_question"):
            current_working_q = self.db.find_current_working_question(self.reading_id)

            # Check if we are trying to set a *different* question as the working one
            if current_working_q and current_working_q['id'] != question_id:
                # A different question is already the working question. Ask to replace.
                wq_name = current_working_q.get('nickname') or current_working_q.get('question_text',
                                                                                     'another question')
                msg = f"This will replace '{wq_name[:50]}...' as the working question. Continue?"

                reply = QMessageBox.question(
                    self, "Replace Working Question?", msg,
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.No:
                    return  # User cancelled

                # Unset all others
                self.db.clear_all_working_questions(self.reading_id)

            elif not current_working_q:
                # No working question exists, so no need to clear anything.
                # This check handles the first-time case.
                pass

            # If current_working_q['id'] == question_id, we are just re-saving
            # the same question as working, so no action is needed.

        # --- End Working Question Check ---

        try:
            if question_id:
                # Update existing
                self.db.update_driving_question(question_id, data)
            else:
                # Add new
                self.db.add_driving_question(self.reading_id, data)

            self.load_questions()  # Refresh tree
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save question: {e}")

    @Slot()
    def _add_question(self):
        """Adds a new root-level question."""
        all_questions = self._get_all_questions_flat()
        outline_items = self._get_outline_items()

        dialog = EditDrivingQuestionDialog(
            all_questions=all_questions,
            outline_items=outline_items,
            parent=self
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            self._handle_save(data, question_id=None)

    @Slot()
    def _add_child_question(self):
        """Adds a child question to the selected item."""
        item = self.tree_widget.currentItem()
        if not item:
            return

        parent_id = item.data(0, Qt.ItemDataRole.UserRole)
        all_questions = self._get_all_questions_flat()
        outline_items = self._get_outline_items()

        # Pre-set parent in data
        initial_data = {"parent_id": parent_id}

        dialog = EditDrivingQuestionDialog(
            current_question_data=initial_data,
            all_questions=all_questions,
            outline_items=outline_items,
            parent=self
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            self._handle_save(data, question_id=None)

    @Slot()
    def _edit_question(self):
        """Edits the selected question."""
        item = self.tree_widget.currentItem()
        if not item:
            return

        question_id = item.data(0, Qt.ItemDataRole.UserRole)
        all_questions = self._get_all_questions_flat()
        outline_items = self._get_outline_items()
        current_data = self.db.get_driving_question_details(question_id)

        if not current_data:
            QMessageBox.critical(self, "Error", "Could not find question details.")
            return

        dialog = EditDrivingQuestionDialog(
            current_question_data=current_data,
            all_questions=all_questions,
            outline_items=outline_items,
            parent=self
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            self.load_questions()  # Refresh tree before save to get fresh data for check
            self._handle_save(data, question_id=question_id)

    @Slot()
    def _delete_question(self):
        """Deletes the selected question and its children."""
        item = self.tree_widget.currentItem()
        if not item:
            return

        question_id = item.data(0, Qt.ItemDataRole.UserRole)
        reply = QMessageBox.question(
            self, "Delete Question",
            "Are you sure you want to delete this question and all its sub-questions?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.db.delete_driving_question(question_id)  # Relies on foreign keys cascade
                self.load_questions()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not delete question: {e}")

    @Slot()
    def _move_up(self):
        item = self.tree_widget.currentItem()
        if not item: return
        self._move_item(item, -1)

    @Slot()
    def _move_down(self):
        item = self.tree_widget.currentItem()
        if not item: return
        self._move_item(item, 1)

    def _move_item(self, item, direction):
        """Moves an item up (-1) or down (1) in its list."""
        parent = item.parent()
        if parent:
            index = parent.indexOfChild(item)
            new_index = index + direction
            if 0 <= new_index < parent.childCount():
                parent.takeChild(index)
                parent.insertChild(new_index, item)
                self.tree_widget.setCurrentItem(item)
                self._save_order(parent)
        else:
            index = self.tree_widget.indexOfTopLevelItem(item)
            new_index = index + direction
            if 0 <= new_index < self.tree_widget.topLevelItemCount():
                self.tree_widget.takeTopLevelItem(index)
                self.tree_widget.insertTopLevelItem(new_index, item)
                self.tree_widget.setCurrentItem(item)
                self._save_order(None)  # None for root

        self._update_button_states()

    @Slot()
    def _reorder_questions(self):
        """Opens the full reorder dialog."""
        item = self.tree_widget.currentItem()
        parent_item = item.parent() if item else None
        parent_id = parent_item.data(0, Qt.ItemDataRole.UserRole) if parent_item else None

        try:
            siblings = self.db.get_driving_questions(self.reading_id, parent_id=parent_id)
            if len(siblings) < 2:
                QMessageBox.information(self, "Reorder", "Not enough items to reorder.")
                return

            items_to_reorder = [(q.get('nickname') or q.get('question_text', '...'), q['id']) for q in siblings]
            dialog = ReorderDialog(items_to_reorder, self)

            if dialog.exec() == QDialog.DialogCode.Accepted:
                ordered_ids = dialog.ordered_db_ids
                self.db.update_driving_question_order(ordered_ids)
                self.load_questions()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not reorder questions: {e}")

    def _save_order(self, parent_item):
        """Saves the display order of items under a parent."""
        ordered_ids = []
        if parent_item:
            for i in range(parent_item.childCount()):
                ordered_ids.append(parent_item.child(i).data(0, Qt.ItemDataRole.UserRole))
        else:
            for i in range(self.tree_widget.topLevelItemCount()):
                ordered_ids.append(self.tree_widget.topLevelItem(i).data(0, Qt.ItemDataRole.UserRole))

        try:
            self.db.update_driving_question_order(ordered_ids)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save new order: {e}")
            self.load_questions()  # Revert on error