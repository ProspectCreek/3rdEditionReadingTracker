# tabs/terminology_tab.py
import sys
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QListWidget,
    QListWidgetItem, QTextBrowser, QPushButton, QMenu, QMessageBox,
    QInputDialog, QDialog
)
from PySide6.QtCore import Qt, Signal, Slot, QPoint, QUrl

try:
    from dialogs.add_term_dialog import AddTermDialog
except ImportError:
    AddTermDialog = None

try:
    from dialogs.reorder_dialog import ReorderDialog
except ImportError:
    ReorderDialog = None


class TerminologyTab(QWidget):
    """
    A tab for defining project-specific terminology and linking it to readings/locations.
    """

    # Signal to request opening a specific PDF node (SynthesisTab/Dashboard should catch this)
    requestOpenPdfNode = Signal(int)

    def __init__(self, db, project_id, parent=None):
        super().__init__(parent)
        self.db = db
        self.project_id = project_id
        self._current_term_id = None

        self.create_widgets()
        self.load_terminology()

    def create_widgets(self):
        main_layout = QVBoxLayout(self)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # --- Left Panel: Term List ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.term_list = QListWidget()
        self.term_list.currentItemChanged.connect(self.on_term_selected)
        self.term_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.term_list.customContextMenuRequested.connect(self.show_context_menu)
        left_layout.addWidget(self.term_list)

        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("Add Term")
        self.btn_add.clicked.connect(self.add_term)

        self.btn_reorder = QPushButton("Reorder")
        self.btn_reorder.clicked.connect(self.reorder_terms)

        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_reorder)
        left_layout.addLayout(btn_layout)

        splitter.addWidget(left_panel)

        # --- Right Panel: Detail Viewer ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.detail_viewer = QTextBrowser()
        # CRITICAL FIX: setOpenLinks(False) prevents the browser from
        # trying to navigate to "pdfnode://...", which causes the blank page.
        # Instead, it strictly emits anchorClicked.
        self.detail_viewer.setOpenLinks(False)
        self.detail_viewer.setOpenExternalLinks(False)
        self.detail_viewer.anchorClicked.connect(self._on_link_clicked)

        right_layout.addWidget(self.detail_viewer)

        splitter.addWidget(right_panel)
        splitter.setSizes([300, 700])

        self.term_list.itemDoubleClicked.connect(self._on_item_double_clicked)

    def load_terminology(self):
        self.term_list.clear()
        terms = self.db.get_project_terminology(self.project_id)
        for term in terms:
            item = QListWidgetItem(term['term'])
            item.setData(Qt.ItemDataRole.UserRole, term['id'])
            self.term_list.addItem(item)

    @Slot(int)
    def select_term_by_id(self, term_id):
        """Selects a term in the list by its ID."""
        # Ensure int comparison
        target_id = int(term_id)
        for i in range(self.term_list.count()):
            item = self.term_list.item(i)
            # data can be int or string depending on how it was set, cast safely
            current_id = item.data(Qt.ItemDataRole.UserRole)
            if current_id is not None and int(current_id) == target_id:
                self.term_list.setCurrentItem(item)
                return

    @Slot(QListWidgetItem, QListWidgetItem)
    def on_term_selected(self, current_item, previous_item):
        if not current_item:
            self.detail_viewer.clear()
            self._current_term_id = None
            return

        term_id = current_item.data(Qt.ItemDataRole.UserRole)
        self._current_term_id = term_id

        data = self.db.get_terminology_details(term_id)
        if not data:
            self.detail_viewer.setHtml("<i>Error loading term details.</i>")
            return

        # Generate HTML Report
        html = f"<h1>{data['term']}</h1>"
        html += f"<div style='background-color:#f0f0f0; padding:10px; margin-bottom:15px;'><b>Meaning:</b><br>{data['meaning']}</div>"

        html += "<h3>References in Readings:</h3>"

        # Group references by reading for display
        refs_by_reading = {}
        readings = self.db.get_readings(self.project_id)

        # Initialize with known statuses
        for r_id, not_in in data.get('statuses', {}).items():
            if not_in:
                refs_by_reading[r_id] = "NOT_IN_READING"
            else:
                refs_by_reading[r_id] = []

        # Add actual references
        for ref in data.get('references', []):
            r_id = ref['reading_id']
            if r_id not in refs_by_reading or refs_by_reading[r_id] == "NOT_IN_READING":
                refs_by_reading[r_id] = []
            refs_by_reading[r_id].append(ref)

        # Build HTML
        for reading in readings:
            r_id = reading['id']
            title = reading.get('nickname') or reading.get('title')

            val = refs_by_reading.get(r_id)

            if val == "NOT_IN_READING":
                html += f"<p><b>{title}:</b> <span style='color:red;'>Not in reading</span></p>"
            elif isinstance(val, list) and len(val) > 0:
                html += f"<p><b>{title}:</b></p><ul>"
                for ref in val:
                    section = ref.get('section_title')
                    loc_text = f"({section})" if section else "(Reading-Level)"

                    # Links (Multiple PDF nodes)
                    links_html = ""
                    if ref.get('pdf_nodes'):
                        link_parts = []
                        for node in ref['pdf_nodes']:
                            pg = node['page_number'] + 1
                            lbl = node['label']
                            # Note: using pdfnode:///ID format
                            link_parts.append(f"<a href='pdfnode:///{node['id']}'>{lbl} (Pg {pg})</a>")
                        links_html = " - " + ", ".join(link_parts)
                    elif ref.get('page_number'):
                        links_html = f" - p. {ref['page_number']}"

                    html += f"<li>{loc_text}{links_html}"

                    if ref.get('author_address'):
                        html += f"<br><i>Author's Use:</i> {ref['author_address']}"

                    if ref.get('notes'):
                        html += f"<br><i>My Notes:</i> {ref['notes']}"

                    html += "</li><br>"
                html += "</ul>"

        self.detail_viewer.setHtml(html)

    def _on_link_clicked(self, url):
        """Handles clicks on anchors in the text browser."""
        url_str = url.toString()

        # Check for pdfnode scheme
        if url.scheme() == 'pdfnode' or url_str.startswith('pdfnode:'):
            try:
                # Handle cases like pdfnode:///123 or pdfnode:123
                path = url.path()
                if not path and ':' in url_str:
                    parts = url_str.split(':', 1)
                    if len(parts) > 1:
                        path = parts[1]

                if path.startswith('/'):
                    path = path[1:]

                if path.isdigit():
                    node_id = int(path)
                    self.requestOpenPdfNode.emit(node_id)
                else:
                    print(f"Invalid node ID in link: {url_str}")
            except Exception as e:
                print(f"Error parsing PDF node link: {e}")

    @Slot(QListWidgetItem)
    def _on_item_double_clicked(self, item):
        if item and item.data(Qt.ItemDataRole.UserRole) is not None:
            self.edit_term()

    def show_context_menu(self, pos):
        item = self.term_list.itemAt(pos)
        menu = QMenu()

        if item:
            menu.addAction("Edit Term", self.edit_term)
            menu.addAction("Delete Term", self.delete_term)
        else:
            menu.addAction("Add New Term", self.add_term)

        menu.exec(self.term_list.viewport().mapToGlobal(pos))

    def add_term(self):
        if not AddTermDialog:
            QMessageBox.warning(self, "Error", "AddTermDialog not available.")
            return

        dialog = AddTermDialog(self.db, self.project_id, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            try:
                self.db.save_terminology_entry(self.project_id, None, data)
                self.load_terminology()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save term: {e}")

    def edit_term(self):
        if not self._current_term_id or not AddTermDialog: return

        dialog = AddTermDialog(self.db, self.project_id, self._current_term_id, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            try:
                self.db.save_terminology_entry(self.project_id, self._current_term_id, data)
                self.load_terminology()
                items = self.term_list.findItems(data['term'], Qt.MatchFlag.MatchExactly)
                if items:
                    self.term_list.setCurrentItem(items[0])
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to update term: {e}")

    def delete_term(self):
        item = self.term_list.currentItem()
        if not item: return

        term_id = item.data(Qt.ItemDataRole.UserRole)
        confirm = QMessageBox.question(self, "Delete Term",
                                       f"Are you sure you want to delete '{item.text()}'?",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if confirm == QMessageBox.StandardButton.Yes:
            self.db.delete_terminology(term_id)
            self.load_terminology()
            self.detail_viewer.clear()

    def reorder_terms(self):
        if not ReorderDialog: return

        items = []
        for i in range(self.term_list.count()):
            it = self.term_list.item(i)
            items.append((it.text(), it.data(Qt.ItemDataRole.UserRole)))

        dialog = ReorderDialog(items, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.db.update_terminology_order(dialog.ordered_db_ids)
            self.load_terminology()

    def update_instructions(self, instructions_data, key):
        pass