# tabs/arguments_tab.py
import sys
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTreeWidget,
    QTreeWidgetItem, QMenu, QMessageBox, QDialog, QLabel, QFrame,
    QHeaderView
)
from PySide6.QtCore import Qt, Signal, QPoint, Slot
from PySide6.QtGui import QAction, QFont, QColor

try:
    from dialogs.add_argument_dialog import AddArgumentDialog
except ImportError:
    print("Error: Could not import AddArgumentDialog")
    AddArgumentDialog = None

try:
    from dialogs.reorder_dialog import ReorderDialog
except ImportError:
    print("Error: Could not import ReorderDialog")
    ReorderDialog = None


class ArgumentsTab(QWidget):
    """
    Widget for managing "Arguments" for a reading.
    """

    def __init__(self, db, project_id, reading_id, parent=None):
        super().__init__(parent)
        self.db = db
        self.reading_id = reading_id
        self.project_id = project_id
        self._block_check_signals = False

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(4)

        self.prompt_label = QLabel("")
        self.prompt_label.setWordWrap(True)
        self.prompt_label.setStyleSheet("font-style: italic; color: #555;")
        self.prompt_label.setVisible(False)
        main_layout.addWidget(self.prompt_label)

        button_bar = QFrame()
        button_layout = QHBoxLayout(button_bar)
        button_layout.setContentsMargins(0, 0, 0, 0)
        self.btn_add = QPushButton("Add Argument")
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

        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(["Insight", "Claim", "Because", "Tags", "Details"])
        header = self.tree_widget.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)
        self.tree_widget.setColumnWidth(0, 50)
        self.tree_widget.setColumnWidth(3, 120)
        self.tree_widget.setColumnWidth(4, 150)

        self.tree_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        main_layout.addWidget(self.tree_widget)

        self.btn_add.clicked.connect(self._add_item)
        self.btn_edit.clicked.connect(self._edit_item)
        self.btn_delete.clicked.connect(self._delete_item)
        self.btn_move_up.clicked.connect(self._move_up)
        self.btn_move_down.clicked.connect(self._move_down)

        self.tree_widget.itemDoubleClicked.connect(self._edit_item)
        self.tree_widget.customContextMenuRequested.connect(self.show_context_menu)
        self.tree_widget.currentItemChanged.connect(self._update_button_states)
        self.tree_widget.itemChanged.connect(self._on_item_changed)

        self.load_arguments()
        self._update_button_states()

    def update_instructions(self, instructions_data, key):
        text = instructions_data.get(key, "")
        self.prompt_label.setText(text)
        self.prompt_label.setVisible(bool(text))

    def load_arguments(self):
        self._block_check_signals = True
        self.tree_widget.clear()
        try:
            arguments = self.db.get_reading_arguments(self.reading_id)
            for arg_data in arguments:
                self._add_argument_to_tree(self.tree_widget, arg_data)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load arguments: {e}")
        finally:
            self._block_check_signals = False

    def _add_argument_to_tree(self, parent_widget, arg_data):
        item = QTreeWidgetItem(parent_widget)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(0, Qt.CheckState.Checked if arg_data.get("is_insight") else Qt.CheckState.Unchecked)

        claim = arg_data.get("claim_text", "N/A")
        if arg_data.get('pdf_node_id'):
            claim += " (PDF Link)"

        item.setText(1, claim)
        item.setText(2, arg_data.get("because_text", ""))
        item.setText(3, arg_data.get("synthesis_tags", ""))
        item.setText(4, arg_data.get("details", ""))

        item.setData(0, Qt.ItemDataRole.UserRole, arg_data["id"])
        item.setData(0, Qt.ItemDataRole.UserRole + 1, dict(arg_data))
        item.setExpanded(True)

    def _on_item_changed(self, item, column):
        if self._block_check_signals or column != 0: return
        argument_id = item.data(0, Qt.ItemDataRole.UserRole)
        is_insight = item.checkState(0) == Qt.CheckState.Checked
        try:
            self.db.update_argument_insight_status(argument_id, is_insight)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not update insight: {e}")
            self.load_arguments()

    def _get_outline_items(self, parent_id=None):
        items = self.db.get_reading_outline(self.reading_id, parent_id=parent_id)
        for item in items:
            children = self._get_outline_items(parent_id=item['id'])
            if children: item['children'] = children
        return items

    def _get_driving_questions(self):
        return self.db.get_driving_questions(self.reading_id, parent_id=True)

    def _update_button_states(self):
        item = self.tree_widget.currentItem()
        sel = item is not None
        self.btn_edit.setEnabled(sel)
        self.btn_delete.setEnabled(sel)
        can_move = False
        if sel and not item.parent():
            idx = self.tree_widget.indexOfTopLevelItem(item)
            can_move = True
        self.btn_move_up.setEnabled(can_move)
        self.btn_move_down.setEnabled(can_move)

    def show_context_menu(self, position):
        menu = QMenu(self)
        item = self.tree_widget.itemAt(position)
        menu.addAction(self.btn_add.text(), self._add_item)
        if item:
            menu.addAction(self.btn_edit.text(), self._edit_item)
            menu.addAction(self.btn_delete.text(), self._delete_item)

            data = item.data(0, Qt.ItemDataRole.UserRole + 1)
            if data and data.get('pdf_node_id'):
                menu.addSeparator()
                pdf_action = QAction("View Linked PDF Node", self)
                pdf_action.triggered.connect(lambda: self._trigger_pdf_jump(data['pdf_node_id']))
                menu.addAction(pdf_action)

            menu.addSeparator()

        if self.tree_widget.topLevelItemCount() > 1 and ReorderDialog:
            reorder = QAction("Reorder Items...", self)
            reorder.triggered.connect(self._reorder_items)
            menu.addAction(reorder)
        menu.exec(self.tree_widget.viewport().mapToGlobal(position))

    def _trigger_pdf_jump(self, pdf_node_id):
        parent = self.parent()
        while parent:
            if parent.metaObject().className() == 'ProjectDashboardWidget':
                if hasattr(parent, '_jump_to_pdf_node'):
                    parent._jump_to_pdf_node(pdf_node_id)
                break
            parent = parent.parent()

    @Slot()
    def _handle_save(self, data, argument_id=None):
        try:
            item_id = None
            if argument_id:
                self.db.update_argument(argument_id, data)
                item_id = argument_id
            else:
                item_id = self.db.add_argument(self.reading_id, data)
            if not item_id: raise Exception("Failed to get item ID.")
            self.load_arguments()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save argument: {e}")

    @Slot()
    def _add_item(self):
        if not AddArgumentDialog: return
        dialog = AddArgumentDialog(self.db, self.project_id, self.reading_id, self._get_outline_items(),
                                   self._get_driving_questions(), parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if not data.get('claim_text'): return
            self._handle_save(data, argument_id=None)

    @Slot()
    def _edit_item(self):
        item = self.tree_widget.currentItem()
        if not item: return
        argument_id = item.data(0, Qt.ItemDataRole.UserRole)
        current_data = self.db.get_argument_details(argument_id)
        if not current_data: return

        dialog = AddArgumentDialog(self.db, self.project_id, self.reading_id, self._get_outline_items(),
                                   self._get_driving_questions(), current_data=current_data, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if not data.get('claim_text'): return
            self._handle_save(data, argument_id=argument_id)

    @Slot()
    def _delete_item(self):
        item = self.tree_widget.currentItem()
        if not item: return
        argument_id = item.data(0, Qt.ItemDataRole.UserRole)
        if QMessageBox.question(self, "Delete", "Delete argument?") == QMessageBox.StandardButton.Yes:
            self.db.delete_argument(argument_id)
            self.load_arguments()

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
        if item.parent(): return
        idx = self.tree_widget.indexOfTopLevelItem(item)
        new_idx = idx + direction
        if 0 <= new_idx < self.tree_widget.topLevelItemCount():
            self.tree_widget.takeTopLevelItem(idx)
            self.tree_widget.insertTopLevelItem(new_idx, item)
            self.tree_widget.setCurrentItem(item)
            self._save_order()
        self._update_button_states()

    @Slot()
    def _reorder_items(self):
        if not ReorderDialog: return
        siblings = self.db.get_reading_arguments(self.reading_id)
        if len(siblings) < 2: return
        items = [(q.get('claim_text', '...'), q['id']) for q in siblings]
        dialog = ReorderDialog(items, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.db.update_argument_order(dialog.ordered_db_ids)
            self.load_arguments()

    def _save_order(self):
        ordered_ids = []
        for i in range(self.tree_widget.topLevelItemCount()):
            ordered_ids.append(self.tree_widget.topLevelItem(i).data(0, Qt.ItemDataRole.UserRole))
        try:
            self.db.update_argument_order(ordered_ids)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save order: {e}")