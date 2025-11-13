# tabs/terminology_tab.py
import sys
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QLabel,
    QListWidget, QListWidgetItem, QFrame, QTextBrowser,
    QMenu, QMessageBox, QDialog, QPushButton
)
from PySide6.QtCore import Qt, Signal, Slot, QPoint

# Import the new dialog
try:
    from dialogs.add_term_dialog import AddTermDialog
except ImportError:
    print("Error: Could not import AddTermDialog")
    AddTermDialog = None

# Import ReorderDialog
try:
    from dialogs.reorder_dialog import ReorderDialog
except ImportError:
    print("Error: Could not import ReorderDialog")
    ReorderDialog = None


class TerminologyTab(QWidget):
    """
    A widget for managing "My Terminology".
    Shows a list of terms and a detail view for meaning and references.
    """

    def __init__(self, db, project_id, parent=None):
        super().__init__(parent)
        self.db = db
        self.project_id = project_id

        main_layout = QVBoxLayout(self)

        # --- (1) "Add Term" Button ---
        self.add_term_btn = QPushButton("Add Term")
        self.add_term_btn.clicked.connect(self._add_term)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.add_term_btn)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)

        # --- Splitter for List and Detail ---
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        main_layout.addWidget(splitter, 1)  # Give splitter all remaining space

        # --- Left Panel (Term List) ---
        left_panel = QFrame()
        left_panel.setFrameShape(QFrame.Shape.StyledPanel)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(4, 4, 4, 4)
        left_layout.addWidget(QLabel("My Terms"))

        self.term_list = QListWidget()
        self.term_list.currentItemChanged.connect(self.on_term_selected)
        # --- (2) Right-click Context Menu ---
        self.term_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.term_list.customContextMenuRequested.connect(self.show_context_menu)
        left_layout.addWidget(self.term_list)

        splitter.addWidget(left_panel)

        # --- Right Panel (Detail Viewer) ---
        right_panel = QFrame()
        right_panel.setFrameShape(QFrame.Shape.StyledPanel)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(4, 4, 4, 4)
        right_layout.addWidget(QLabel("Details"))

        self.detail_viewer = QTextBrowser()
        right_layout.addWidget(self.detail_viewer)

        splitter.addWidget(right_panel)
        splitter.setSizes([250, 600])

        # --- NEW: (5) Connect double-click signal ---
        self.term_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        # --- END NEW ---

    def load_terminology(self):
        """Reloads the list of terms from the database."""
        self.term_list.clear()
        self.detail_viewer.clear()
        try:
            terms = self.db.get_project_terminology(self.project_id)
            if not terms:
                item = QListWidgetItem("No terms added yet.")
                item.setFlags(Qt.ItemFlag.NoItemFlags)
                self.term_list.addItem(item)
                return

            for term in terms:
                item = QListWidgetItem(term['term'])
                item.setData(Qt.ItemDataRole.UserRole, term['id'])
                self.term_list.addItem(item)
        except Exception as e:
            QMessageBox.critical(self, "Error Loading Terms", f"Could not load terms: {e}")

    @Slot(QListWidgetItem, QListWidgetItem)
    def on_term_selected(self, current_item, previous_item):
        """Called when a term is clicked, loads its details."""
        if current_item is None:
            self.detail_viewer.clear()
            return

        term_id = current_item.data(Qt.ItemDataRole.UserRole)
        if term_id is None:
            self.detail_viewer.clear()
            return

        try:
            data = self.db.get_terminology_details(term_id)
            if not data:
                self.detail_viewer.setHtml("<i>Could not load term details.</i>")
                return

            # --- NEW: (4) Modern Viewer Styling ---
            html = f"""
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; }}
                h2 {{
                    color: #111;
                    margin-bottom: 5px;
                    font-size: 1.5em;
                }}
                h3 {{
                    color: #333;
                    border-bottom: 1px solid #ddd;
                    padding-bottom: 4px;
                    margin-top: 20px;
                    margin-bottom: 10px;
                    font-size: 1.2em;
                }}
                h4 {{
                    margin: 0 0 10px 0;
                    color: #0055A4;
                    font-size: 1.1em;
                }}
                .card {{
                    background: #ffffff;
                    border: 1px solid #ddd;
                    padding: 15px;
                    border-radius: 5px;
                    margin-bottom: 10px;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
                }}
                .meaning {{
                    background: #fdfdfd;
                    border: 1px solid #eee;
                    padding: 10px;
                    border-radius: 5px;
                    margin-bottom: 15px;
                    font-size: 1.05em;
                }}
                .reference-block {{
                    padding-left: 15px;
                    border-left: 3px solid #007acc;
                    margin-top: 5px;
                }}
                .ref-notes {{
                    margin-top: 8px;
                }}
                .not-in-reading {{
                    font-style: italic;
                    color: #777;
                }}
            </style>
            """

            html += f"<h2>{data.get('term', 'No Term')}</h2>"
            html += "<h3>My Meaning:</h3>"
            html += f"<div class='meaning'>{data.get('meaning', '<i>No meaning defined.</i>')}</div>"
            html += "<hr>"
            html += "<h3>Reading References:</h3>"

            all_readings = self.db.get_readings(self.project_id)
            all_statuses = data.get('statuses', {})
            all_refs = data.get("references", [])

            if not all_readings:
                html += "<i>No readings in this project to reference.</i>"

            for reading in all_readings:
                reading_id = reading['id']
                reading_name = reading.get('nickname') or reading.get('title', 'Unknown Reading')
                status = all_statuses.get(reading_id, 0)  # Default to 0 (present)

                html += f"<div class='card'>"
                html += f"<h4>{reading_name}</h4>"

                if status == 1:
                    # Term is marked as not in this reading
                    html += "<div class='not-in-reading'>Term not in reading.</div>"
                else:
                    # Term is present, find its references
                    refs_for_this_reading = [r for r in all_refs if r['reading_id'] == reading_id]
                    if not refs_for_this_reading:
                        html += "<div class='not-in-reading'>No references added.</div>"
                    else:
                        for i, ref in enumerate(refs_for_this_reading):

                            # --- FIX: (1) Use section_title ---
                            section = ref.get('section_title')
                            context = ""
                            if section:
                                context = f"({section})"
                            else:
                                context = "(Reading-Level)"
                            # --- END FIX ---

                            if ref.get('page_number'):
                                context += f" - p. {ref['page_number']}"

                            html += f"<div class='reference-block'>"
                            html += f"<b>{context}</b>"

                            # --- FIX: (3) Wording Change ---
                            html += f"<br><b style='color: #555;'>How the Author Addresses My Term:</b>"
                            html += f"<div>{ref.get('author_address', 'N/A')}</div>"

                            html += f"<div class='ref-notes'><b style='color: #555;'>My Notes:</b>"
                            html += f"<div>{ref.get('notes', 'N/A')}</div></div>"

                            html += "</div>"  # end .reference-block

                            # Add a visual separator if not the last reference for this reading
                            if i < len(refs_for_this_reading) - 1:
                                html += "<hr style='border: 0; border-top: 1px dashed #eee; margin: 10px 0;'>"

                html += "</div>"  # end .card

            self.detail_viewer.setHtml(html)
            # --- END NEW: (4) ---

        except Exception as e:
            self.detail_viewer.setHtml(f"<p><b>Error loading details:</b><br>{e}</p>")
            QMessageBox.critical(self, "Error", f"Could not load term details: {e}")

    @Slot(QPoint)
    def show_context_menu(self, position):
        """Shows the right-click menu for the term list."""
        menu = QMenu(self)

        # (A) Add Term
        add_action = menu.addAction("Add New Term...")
        add_action.triggered.connect(self._add_term)

        item = self.term_list.itemAt(position)
        if item and item.data(Qt.ItemDataRole.UserRole) is not None:
            menu.addSeparator()
            # (B) Edit Term
            edit_action = menu.addAction("Edit Term...")
            edit_action.triggered.connect(self._edit_term)
            # (C) Delete Term
            delete_action = menu.addAction("Delete Term")
            delete_action.triggered.connect(self._delete_term)

        # (D) Reorder Terms
        # Check if there are at least 2 real items to reorder
        real_item_count = 0
        for i in range(self.term_list.count()):
            if self.term_list.item(i).data(Qt.ItemDataRole.UserRole) is not None:
                real_item_count += 1

        if real_item_count > 1 and ReorderDialog:
            menu.addSeparator()
            reorder_action = menu.addAction("Reorder Terms...")
            reorder_action.triggered.connect(self._reorder_terms)

        menu.exec(self.term_list.mapToGlobal(position))

    # --- NEW: (5) Slot for double-click ---
    @Slot(QListWidgetItem)
    def _on_item_double_clicked(self, item):
        """Handles double-clicking a term in the list to edit it."""
        if item and item.data(Qt.ItemDataRole.UserRole) is not None:
            self._edit_term()

    # --- END NEW ---

    @Slot()
    def _add_term(self):
        """Opens the AddTermDialog to create a new term."""
        if not AddTermDialog:
            QMessageBox.critical(self, "Error", "Add Term Dialog could not be loaded.")
            return

        dialog = AddTermDialog(self.db, self.project_id, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if not data['term']:
                QMessageBox.warning(self, "Invalid Term", "Term name cannot be empty.")
                return

            try:
                # Use the high-level save function
                self.db.save_terminology_entry(self.project_id, None, data)
                self.load_terminology()  # Refresh the list
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not save new term: {e}")

    @Slot()
    def _edit_term(self):
        """Opens the AddTermDialog to edit the selected term."""
        item = self.term_list.currentItem()
        if not item or item.data(Qt.ItemDataRole.UserRole) is None:
            return

        term_id = item.data(Qt.ItemDataRole.UserRole)

        if not AddTermDialog:
            QMessageBox.critical(self, "Error", "Edit Term Dialog could not be loaded.")
            return

        # Pass the term_id to the dialog
        dialog = AddTermDialog(self.db, self.project_id, terminology_id=term_id, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if not data['term']:
                QMessageBox.warning(self, "Invalid Term", "Term name cannot be empty.")
                return

            try:
                # Use the high-level save function, passing the term_id
                self.db.save_terminology_entry(self.project_id, term_id, data)
                self.load_terminology()  # Refresh the list
                # Reselect the item to refresh the detail view
                for i in range(self.term_list.count()):
                    if self.term_list.item(i).data(Qt.ItemDataRole.UserRole) == term_id:
                        self.term_list.setCurrentRow(i)
                        break
                self.on_term_selected(self.term_list.currentItem(), None)  # Refresh details
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not update term: {e}")

    @Slot()
    def _delete_term(self):
        """Deletes the selected term."""
        item = self.term_list.currentItem()
        if not item or item.data(Qt.ItemDataRole.UserRole) is None:
            return

        term_id = item.data(Qt.ItemDataRole.UserRole)
        term_name = item.text()

        reply = QMessageBox.question(
            self, "Delete Term",
            f"Are you sure you want to delete the term '{term_name}'?\n\nThis will remove the term, its meaning, and all its reading references.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.db.delete_terminology(term_id)
                self.load_terminology()  # Refresh the list
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not delete term: {e}")

    @Slot()
    def _reorder_terms(self):
        """Opens the reorder dialog for terms."""
        if not ReorderDialog:
            QMessageBox.critical(self, "Error", "Reorder dialog is not available.")
            return

        items_to_reorder = []
        for i in range(self.term_list.count()):
            item = self.term_list.item(i)
            term_id = item.data(Qt.ItemDataRole.UserRole)
            if term_id is not None:
                items_to_reorder.append((item.text(), term_id))

        if len(items_to_reorder) < 2:
            return

        dialog = ReorderDialog(items_to_reorder, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            ordered_ids = dialog.ordered_db_ids
            try:
                self.db.update_terminology_order(ordered_ids)
                self.load_terminology()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not reorder terms: {e}")