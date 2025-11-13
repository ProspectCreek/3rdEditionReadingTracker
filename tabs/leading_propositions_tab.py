# tabs/leading_propositions_tab.py
import sys
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QMenu, QMessageBox, QDialog, QPushButton, QHeaderView, QLabel
)
from PySide6.QtCore import Qt, Signal, Slot, QPoint
from PySide6.QtGui import QAction, QColor, QFont, QTextDocument

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
    A widget for managing "Leading Propositions" for a single reading.
    Shows a tree view with columns.
    """

    def __init__(self, db, reading_id, parent=None):
        super().__init__(parent)
        self.db = db
        self.reading_id = reading_id
        try:
            reading_details = self.db.get_reading_details(self.reading_id)
            self.project_id = reading_details['project_id']
        except Exception as e:
            print(f"Error getting project_id for LeadingPropositionsTab: {e}")
            self.project_id = -1

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(4)

        # Button bar
        button_layout = QHBoxLayout()
        self.btn_add = QPushButton("Add Proposition")
        button_layout.addWidget(self.btn_add)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)

        # Tree widget
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(["Proposition", "Location", "Importance"])
        self.tree_widget.setColumnCount(3)
        self.tree_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        # Set column widths
        header = self.tree_widget.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.tree_widget.setColumnWidth(1, 150)

        main_layout.addWidget(self.tree_widget)

        # --- Connections ---
        self.btn_add.clicked.connect(self._add_item)
        self.tree_widget.itemDoubleClicked.connect(self._edit_item)
        self.tree_widget.customContextMenuRequested.connect(self.show_context_menu)

        self.load_propositions()

    def _html_to_plain(self, html):
        """Utility to convert HTML to plain text for tree display."""
        doc = QTextDocument()
        doc.setHtml(html)
        return doc.toPlainText().replace('\n', ' ').strip()

    def load_propositions(self):
        """Reloads all propositions from the database into the tree."""
        self.tree_widget.clear()
        try:
            # 1. Get outline items for the location dropdown
            outline_items_raw = self.db.get_reading_outline(self.reading_id, parent_id=None)
            self.outline_map = {item['id']: item['section_title'] for item in outline_items_raw}
            # Recursively build map
            self._build_outline_map(outline_items_raw)

            # 2. Get propositions
            propositions = self.db.get_reading_propositions(self.reading_id)
            if not propositions:
                item = QTreeWidgetItem(["No propositions added yet."])
                item.setDisabled(True)
                item.setForeground(0, QColor("#888"))
                item.setFont(0, QFont("Arial", 10, QFont.Weight.Normal, True))
                self.tree_widget.addTopLevelItem(item)
                return

            for prop in propositions:
                prop_text = self._html_to_plain(prop.get("proposition_text", ""))

                # Build Location string
                loc_text = self.outline_map.get(prop.get("outline_id"), "[Reading-Level]")
                if prop.get("pages"):
                    loc_text += f" (p. {prop.get('pages')})"

                importance_text = self._html_to_plain(prop.get("importance_text", ""))

                item = QTreeWidgetItem([prop_text, loc_text, importance_text])
                item.setData(0, Qt.ItemDataRole.UserRole, prop["id"])

                # Set tooltips to show full content
                item.setToolTip(0, f"<b>Proposition:</b><br>{prop.get('proposition_text', '')}")
                item.setToolTip(1, f"<b>Location:</b><br>{loc_text}")
                item.setToolTip(2, f"<b>Importance:</b><br>{prop.get('importance_text', '')}")

                self.tree_widget.addTopLevelItem(item)

                # Auto-resize row height to content
                item.setSizeHint(0, item.sizeHint(0))

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load propositions: {e}")
            import traceback
            traceback.print_exc()

    def _build_outline_map(self, items):
        """Recursively populates self.outline_map."""
        for item in items:
            self.outline_map[item['id']] = item['section_title']
            children = self.db.get_reading_outline(self.reading_id, parent_id=item['id'])
            if children:
                self._build_outline_map(children)

    def _get_outline_items_for_dialog(self, parent_id=None):
        """Recursively fetches outline items to build a nested list for the dialog."""
        items = self.db.get_reading_outline(self.reading_id, parent_id=parent_id)
        for item in items:
            children = self._get_outline_items_for_dialog(parent_id=item['id'])
            if children:
                item['children'] = children
        return items

    def show_context_menu(self, position):
        menu = QMenu(self)
        item = self.tree_widget.itemAt(position)

        menu.addAction("Add Proposition", self._add_item)

        if item and item.data(0, Qt.ItemDataRole.UserRole) is not None:
            menu.addSeparator()
            menu.addAction("Edit Proposition", self._edit_item)
            menu.addAction("Delete Proposition", self._delete_item)

        if ReorderDialog and self.tree_widget.topLevelItemCount() > 1:
            menu.addSeparator()
            reorder_action = QAction("Reorder Items...", self)
            reorder_action.triggered.connect(self._reorder_items)
            menu.addAction(reorder_action)

        menu.exec(self.tree_widget.viewport().mapToGlobal(position))

    @Slot()
    def _add_item(self):
        """Adds a new proposition."""
        if not AddLeadingPropositionDialog:
            QMessageBox.critical(self, "Error", "Add Proposition Dialog could not be loaded.")
            return

        outline_items = self._get_outline_items_for_dialog()
        dialog = AddLeadingPropositionDialog(
            db_manager=self.db,
            project_id=self.project_id,
            outline_items=outline_items,
            parent=self
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            try:
                self.db.add_reading_proposition(self.reading_id, data)
                self.load_propositions()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not save proposition: {e}")

    @Slot()
    def _edit_item(self):
        """Edits the selected proposition."""
        item = self.tree_widget.currentItem()
        if not item or item.data(0, Qt.ItemDataRole.UserRole) is None:
            return

        proposition_id = item.data(0, Qt.ItemDataRole.UserRole)
        current_data = self.db.get_reading_proposition_details(proposition_id)
        if not current_data:
            QMessageBox.critical(self, "Error", "Could not find proposition details.")
            return

        outline_items = self._get_outline_items_for_dialog()
        dialog = AddLeadingPropositionDialog(
            db_manager=self.db,
            project_id=self.project_id,
            outline_items=outline_items,
            current_data=current_data,
            parent=self
        )

        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            try:
                self.db.update_reading_proposition(proposition_id, data)
                self.load_propositions()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not update proposition: {e}")

    @Slot()
    def _delete_item(self):
        """Deletes the selected proposition."""
        item = self.tree_widget.currentItem()
        if not item or item.data(0, Qt.ItemDataRole.UserRole) is None:
            return

        proposition_id = item.data(0, Qt.ItemDataRole.UserRole)
        reply = QMessageBox.question(
            self, "Delete Proposition",
            "Are you sure you want to delete this proposition?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.db.delete_reading_proposition(proposition_id)
                self.load_propositions()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not delete proposition: {e}")

    @Slot()
    def _reorder_items(self):
        """Opens the reorder dialog."""
        try:
            propositions = self.db.get_reading_propositions(self.reading_id)
            if len(propositions) < 2:
                QMessageBox.information(self, "Reorder", "Not enough items to reorder.")
                return

            items_to_reorder = [(self._html_to_plain(p.get('proposition_text', '...')), p['id']) for p in propositions]
            dialog = ReorderDialog(items_to_reorder, self)

            if dialog.exec() == QDialog.DialogCode.Accepted:
                ordered_ids = dialog.ordered_db_ids
                self.db.update_reading_proposition_order(ordered_ids)
                self.load_propositions()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not reorder propositions: {e}")