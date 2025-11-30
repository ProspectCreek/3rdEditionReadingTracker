# tabs/leading_propositions_tab.py
import sys
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QLabel,
    QListWidget, QListWidgetItem, QFrame, QTextBrowser,
    QMenu, QMessageBox, QDialog, QPushButton
)
from PySide6.QtCore import Qt, Signal, Slot, QPoint
from PySide6.QtGui import QAction, QColor, QFont

try:
    from dialogs.add_leading_proposition_dialog import AddLeadingPropositionDialog
except ImportError:
    print("Error: Could not import AddLeadingPropositionDialog")
    AddLeadingPropositionDialog = None

try:
    from dialogs.reorder_dialog import ReorderDialog
except ImportError:
    print("Error: Could not import ReorderDialog")
    ReorderDialog = None


class LeadingPropositionsTab(QWidget):
    """
    A widget for managing "Leading Propositions" for a *single reading*.
    """

    def __init__(self, db, project_id, reading_id, parent=None):
        super().__init__(parent)
        self.db = db
        self.project_id = project_id
        self.reading_id = reading_id

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(4)

        self.prompt_label = QLabel("")
        self.prompt_label.setWordWrap(True)
        self.prompt_label.setStyleSheet("font-style: italic; color: #555; padding: 4px;")
        self.prompt_label.setVisible(False)
        main_layout.addWidget(self.prompt_label)

        self.add_item_btn = QPushButton("Add Leading Proposition")
        self.add_item_btn.clicked.connect(self._add_item)
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.add_item_btn)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        main_layout.addWidget(splitter, 1)

        left_panel = QFrame()
        left_panel.setFrameShape(QFrame.Shape.StyledPanel)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(4, 4, 4, 4)
        left_layout.addWidget(QLabel("Leading Propositions"))

        self.item_list = QListWidget()
        self.item_list.currentItemChanged.connect(self.on_item_selected)
        self.item_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.item_list.customContextMenuRequested.connect(self.show_context_menu)
        left_layout.addWidget(self.item_list)

        splitter.addWidget(left_panel)

        right_panel = QFrame()
        right_panel.setFrameShape(QFrame.Shape.StyledPanel)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(4, 4, 4, 4)
        right_layout.addWidget(QLabel("Details"))

        self.detail_viewer = QTextBrowser()
        right_layout.addWidget(self.detail_viewer)

        splitter.addWidget(right_panel)
        splitter.setSizes([250, 600])

        self.item_list.itemDoubleClicked.connect(self._edit_item)
        self.load_propositions()

    def update_instructions(self, instructions_data, key):
        text = instructions_data.get(key, "")
        self.prompt_label.setText(text)
        self.prompt_label.setVisible(bool(text))

    def load_propositions(self):
        self.item_list.clear()
        self.detail_viewer.clear()
        try:
            items = self.db.get_reading_propositions_simple(self.reading_id)

            if not items:
                item = QListWidgetItem("No propositions added yet.")
                item.setFlags(Qt.ItemFlag.NoItemFlags)
                self.item_list.addItem(item)
                return

            for item_data in items:
                nickname = item_data.get('nickname')
                prop_text = item_data.get('proposition_text', 'N/A').split('\n')[0]
                display_text = nickname if nickname else prop_text
                if len(display_text) > 70: display_text = display_text[:70] + "..."

                # PDF Link
                if item_data.get('pdf_node_id'):
                    display_text += " (PDF Link)"

                item = QListWidgetItem(display_text)
                item.setData(Qt.ItemDataRole.UserRole, item_data['id'])
                item.setData(Qt.ItemDataRole.UserRole + 1, dict(item_data))
                self.item_list.addItem(item)
        except Exception as e:
            QMessageBox.critical(self, "Error Loading Propositions", f"Could not load propositions: {e}")

    @Slot(QListWidgetItem, QListWidgetItem)
    def on_item_selected(self, current_item, previous_item):
        if current_item is None:
            self.detail_viewer.clear()
            return
        item_id = current_item.data(Qt.ItemDataRole.UserRole)
        if item_id is None:
            self.detail_viewer.clear()
            return

        try:
            data = self.db.get_reading_proposition_details(item_id)
            if not data:
                self.detail_viewer.setHtml("<i>Could not load proposition details.</i>")
                return

            html = ""
            if data.get('nickname'):
                html += f"<h3>Nickname:</h3><p>{data.get('nickname')}</p>"
            html += f"<h3>Proposition:</h3><p>{data.get('proposition_text', 'N/A').replace(chr(10), '<br>')}</p>"

            location = "Reading-Level Notes"
            if data.get('outline_title'): location = data['outline_title']
            if data.get('pages'): location += f" (p. {data.get('pages')})"
            html += f"<h3>Location:</h3><p>{location}</p>"
            html += f"<h3>Why it's important:</h3><p>{data.get('why_important', 'N/A').replace(chr(10), '<br>')}</p>"
            html += f"<h3>Synthesis Tags:</h3><p>{data.get('synthesis_tags', 'N/A')}</p>"

            if data.get('pdf_node_id'):
                html += f"<h3 style='color:#2563EB'>PDF Link Active (Right click list to view)</h3>"

            self.detail_viewer.setHtml(html)
        except Exception as e:
            self.detail_viewer.setHtml(f"<p>Error: {e}</p>")

    @Slot(QPoint)
    def show_context_menu(self, position):
        menu = QMenu(self)
        menu.addAction("Add New Leading Proposition...", self._add_item)

        item = self.item_list.itemAt(position)
        if item and item.data(Qt.ItemDataRole.UserRole) is not None:
            menu.addSeparator()
            menu.addAction("Edit Leading Proposition...", self._edit_item)
            menu.addAction("Delete Leading Proposition", self._delete_item)

            data = item.data(Qt.ItemDataRole.UserRole + 1)
            if data and data.get('pdf_node_id'):
                menu.addSeparator()
                pdf_action = QAction("View Linked PDF Node", self)
                pdf_action.triggered.connect(lambda: self._trigger_pdf_jump(data['pdf_node_id']))
                menu.addAction(pdf_action)

        real_count = sum(
            1 for i in range(self.item_list.count()) if self.item_list.item(i).data(Qt.ItemDataRole.UserRole))
        if real_count > 1 and ReorderDialog:
            menu.addSeparator()
            menu.addAction("Reorder Leading Propositions...", self._reorder_items)
        menu.exec(self.item_list.mapToGlobal(position))

    def _trigger_pdf_jump(self, pdf_node_id):
        parent = self.parent()
        while parent:
            if parent.metaObject().className() == 'ProjectDashboardWidget':
                if hasattr(parent, '_jump_to_pdf_node'):
                    parent._jump_to_pdf_node(pdf_node_id)
                break
            parent = parent.parent()

    def _get_outline_items(self, parent_id=None):
        items = self.db.get_reading_outline(self.reading_id, parent_id=parent_id)
        for item in items:
            children = self._get_outline_items(parent_id=item['id'])
            if children: item['children'] = children
        return items

    @Slot()
    def _add_item(self):
        if not AddLeadingPropositionDialog: return
        dialog = AddLeadingPropositionDialog(self.db, self.project_id, self.reading_id, self._get_outline_items(),
                                             parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if not data['proposition_text']: return
            try:
                self.db.add_reading_proposition(self.reading_id, data)
                self.load_propositions()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not save: {e}")

    @Slot()
    def _edit_item(self):
        item = self.item_list.currentItem()
        if not item or item.data(Qt.ItemDataRole.UserRole) is None: return
        item_id = item.data(Qt.ItemDataRole.UserRole)
        current_data = self.db.get_reading_proposition_details(item_id)
        if not current_data: return

        dialog = AddLeadingPropositionDialog(self.db, self.project_id, self.reading_id, self._get_outline_items(),
                                             current_data=current_data, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if not data['proposition_text']: return
            try:
                self.db.update_reading_proposition(item_id, data)
                self.load_propositions()
                self.on_item_selected(self.item_list.currentItem(), None)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not update: {e}")

    @Slot()
    def _delete_item(self):
        item = self.item_list.currentItem()
        if not item or item.data(Qt.ItemDataRole.UserRole) is None: return
        item_id = item.data(Qt.ItemDataRole.UserRole)
        if QMessageBox.question(self, "Delete", "Delete proposition?") == QMessageBox.StandardButton.Yes:
            self.db.delete_reading_proposition(item_id)
            self.load_propositions()

    @Slot()
    def _reorder_items(self):
        if not ReorderDialog: return
        items_to_reorder = []
        for i in range(self.item_list.count()):
            item = self.item_list.item(i)
            item_id = item.data(Qt.ItemDataRole.UserRole)
            if item_id is not None: items_to_reorder.append((item.text(), item_id))
        if len(items_to_reorder) < 2: return
        dialog = ReorderDialog(items_to_reorder, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.db.update_reading_proposition_order(dialog.ordered_db_ids)
            self.load_propositions()