# tabs/driving_question_tab.py
import sys
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTreeWidget,
    QTreeWidgetItem, QMenu, QMessageBox, QDialog, QLabel, QFrame,
    QHeaderView
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

    # Signal to open a PDF node in the viewer (handled by Dashboard)
    requestOpenPdfNode = Signal(int)

    def __init__(self, db, reading_id: int, parent=None):
        super().__init__(parent)
        self.db = db
        self.reading_id = reading_id
        # --- NEW: Get project_id from reading_details ---
        try:
            reading_details = self.db.get_reading_details(self.reading_id)
            self.project_id = reading_details['project_id']
        except Exception as e:
            print(f"Error getting project_id for DrivingQuestionTab: {e}")
            self.project_id = -1  # Invalid project ID
        # --- END NEW ---

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(4)

        # --- NEW: Add Instruction Label ---
        self.prompt_label = QLabel("")
        self.prompt_label.setWordWrap(True)
        self.prompt_label.setStyleSheet("font-style: italic; color: #555; padding: 4px;")  # Add padding
        self.prompt_label.setVisible(False)  # Hidden by default
        main_layout.addWidget(self.prompt_label)
        # --- END NEW ---

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

    def update_instructions(self, instructions_data, key):
        """Sets the instruction text for this tab."""
        text = instructions_data.get(key, "")
        self.prompt_label.setText(text)
        self.prompt_label.setVisible(bool(text))

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
        pdf_node_id = q_data.get("pdf_node_id")

        display_text = ""
        # --- NEW: Star is on the left ---
        if is_working:
            display_text += "★ "  # Add a star for working question

        if nickname:
            display_text += f"({nickname}) "
        display_text += question_text

        # --- NEW: Append PDF Link text ---
        if pdf_node_id:
            display_text += " (PDF Link)"
        # --- END NEW ---

        item = QTreeWidgetItem(parent_widget, [display_text])
        item.setData(0, Qt.ItemDataRole.UserRole, q_data["id"])
        item.setData(0, Qt.ItemDataRole.UserRole + 1, dict(q_data))  # Store full data for context menu

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

            # --- PDF Link Action ---
            dq_data = item.data(0, Qt.ItemDataRole.UserRole + 1)
            pdf_node_id = dq_data.get('pdf_node_id')
            if pdf_node_id:
                menu.addSeparator()
                view_pdf_action = QAction("View Linked PDF Node", self)
                view_pdf_action.triggered.connect(lambda: self._trigger_pdf_jump(pdf_node_id))
                menu.addAction(view_pdf_action)
            # -----------------------

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

    def _trigger_pdf_jump(self, pdf_node_id):
        """Emits signal to jump to PDF."""
        parent = self.parent()
        while parent:
            if parent.metaObject().className() == 'ProjectDashboardWidget':
                if hasattr(parent, '_jump_to_pdf_node'):
                    parent._jump_to_pdf_node(pdf_node_id)
                break
            parent = parent.parent()

    @Slot()
    def _handle_save(self, data, question_id=None):
        """Central logic for saving a question (add or edit)."""
        # --- Working Question Check ---
        if data.get("is_working_question"):
            current_working_q = self.db.find_current_working_question(self.reading_id)

            if current_working_q and current_working_q['id'] != question_id:
                wq_name = current_working_q.get('nickname') or current_working_q.get('question_text',
                                                                                     'another question')
                msg = f"This will replace '{wq_name[:50]}...' as the working question. Continue?"

                reply = QMessageBox.question(
                    self, "Replace Working Question?", msg,
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.No:
                    data["is_working_question"] = False  # Uncheck it if user cancelled

            if data.get("is_working_question"):  # Check again in case user cancelled
                # Unset all others
                self.db.clear_all_working_questions(self.reading_id)

        try:
            item_id = None
            if question_id:
                # Update existing
                self.db.update_driving_question(question_id, data)
                item_id = question_id
            else:
                # Add new
                item_id = self.db.add_driving_question(self.reading_id, data)

            if not item_id:
                raise Exception("Failed to get item ID after save/update.")

            # --- VIRTUAL ANCHOR FIX ---
            # 1. Clear all existing virtual anchors for this item
            self.db.delete_anchors_by_item_link_id(item_id)

            # 2. Add new ones based on the tags
            tags_text = data.get("synthesis_tags", "")
            if tags_text:
                tag_names = [tag.strip() for tag in tags_text.split(',') if tag.strip()]
                q_text = data.get('question_text', '')[:50]
                nickname = data.get('nickname', '')
                summary_text = f"Driving Question: {nickname or q_text}..."

                for tag_name in tag_names:
                    tag_data = self.db.get_or_create_tag(tag_name, self.project_id)
                    if tag_data:
                        self.db.create_anchor(
                            project_id=self.project_id,
                            reading_id=self.reading_id,
                            outline_id=data.get("outline_id"),
                            tag_id=tag_data['id'],
                            selected_text=summary_text,
                            comment=f"Linked to Driving Question ID {item_id}",
                            unique_doc_id=f"dq-{item_id}-{tag_data['id']}",  # Make unique doc_id
                            item_link_id=item_id,
                            pdf_node_id=data.get("pdf_node_id")  # Pass PDF node ID if present
                        )
            # --- END VIRTUAL ANCHOR FIX ---

            self.load_questions()  # Refresh tree
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save question: {e}")
            import traceback
            traceback.print_exc()

    @Slot()
    def _add_question(self):
        """Adds a new root-level question."""
        all_questions = self._get_all_questions_flat()
        outline_items = self._get_outline_items()

        # Correct call:
        dialog = EditDrivingQuestionDialog(
            db=self.db,
            dq_data={},  # Empty data for new question
            parent=self
        )

        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.result_data  # The dialog stores result in result_data
            self._handle_save(data, question_id=None)

    @Slot()
    def _add_child_question(self):
        """Adds a child question to the selected item."""
        item = self.tree_widget.currentItem()
        if not item:
            return

        parent_id = item.data(0, Qt.ItemDataRole.UserRole)

        # Pre-set parent in data
        initial_data = {"parent_id": parent_id}

        dialog = EditDrivingQuestionDialog(
            db=self.db,
            dq_data=initial_data,
            parent=self
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.result_data
            self._handle_save(data, question_id=None)

    @Slot()
    def _edit_question(self):
        """Edits the selected question."""
        item = self.tree_widget.currentItem()
        if not item:
            return

        question_id = item.data(0, Qt.ItemDataRole.UserRole)

        # Get fresh data from DB to be safe
        current_data = self.db.get_driving_question_details(question_id)

        if not current_data:
            QMessageBox.critical(self, "Error", "Could not find question details.")
            return

        # Correct call:
        dialog = EditDrivingQuestionDialog(
            db=self.db,
            dq_data=current_data,
            parent=self
        )

        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.result_data
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
            "Are you sure you want to delete this question and all its sub-questions?\n\nThis will also delete any linked synthesis tags.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Deleting the question will automatically cascade-delete
                # the linked anchors thanks to the schema.
                self.db.delete_driving_question(question_id)
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