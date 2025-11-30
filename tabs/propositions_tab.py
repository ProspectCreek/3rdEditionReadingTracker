# tabs/propositions_tab.py
import sys
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QLabel,
    QListWidget, QListWidgetItem, QFrame, QTextBrowser,
    QMenu, QMessageBox, QDialog, QPushButton
)
from PySide6.QtCore import Qt, Signal, Slot, QPoint, QUrl

try:
    from dialogs.add_proposition_dialog import AddPropositionDialog
except ImportError:
    print("Error: Could not import AddPropositionDialog")
    AddPropositionDialog = None

try:
    from dialogs.reorder_dialog import ReorderDialog
except ImportError:
    print("Error: Could not import ReorderDialog")
    ReorderDialog = None


class PropositionsTab(QWidget):
    """
    A widget for managing "My Propositions".
    Shows a list of propositions and a detail view for meaning and references.
    """

    requestOpenPdfNode = Signal(int)

    def __init__(self, db, project_id, parent=None):
        super().__init__(parent)
        self.db = db
        self.project_id = project_id

        main_layout = QVBoxLayout(self)

        # Instruction Label
        self.prompt_label = QLabel("")
        self.prompt_label.setWordWrap(True)
        self.prompt_label.setStyleSheet("font-style: italic; color: #555;")
        self.prompt_label.setVisible(False)
        main_layout.addWidget(self.prompt_label)

        # Add Button
        self.add_item_btn = QPushButton("Add Proposition")
        self.add_item_btn.clicked.connect(self._add_item)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.add_item_btn)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)

        # Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        main_layout.addWidget(splitter, 1)

        # Left Panel
        left_panel = QFrame()
        left_panel.setFrameShape(QFrame.Shape.StyledPanel)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(4, 4, 4, 4)
        left_layout.addWidget(QLabel("My Propositions"))

        self.item_list = QListWidget()
        self.item_list.currentItemChanged.connect(self.on_item_selected)
        self.item_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.item_list.customContextMenuRequested.connect(self.show_context_menu)
        left_layout.addWidget(self.item_list)

        splitter.addWidget(left_panel)

        # Right Panel
        right_panel = QFrame()
        right_panel.setFrameShape(QFrame.Shape.StyledPanel)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(4, 4, 4, 4)
        right_layout.addWidget(QLabel("Details"))

        self.detail_viewer = QTextBrowser()
        # CRITICAL FIX: Disable openLinks to prevent blank page on click
        self.detail_viewer.setOpenLinks(False)
        self.detail_viewer.setOpenExternalLinks(False)
        self.detail_viewer.anchorClicked.connect(self._on_link_clicked)

        right_layout.addWidget(self.detail_viewer)

        splitter.addWidget(right_panel)
        splitter.setSizes([250, 600])

        self.item_list.itemDoubleClicked.connect(self._edit_item)

    def update_instructions(self, instructions_data, key):
        text = instructions_data.get(key, "")
        self.prompt_label.setText(text)
        self.prompt_label.setVisible(bool(text))

    def load_items(self):
        self.item_list.clear()
        self.detail_viewer.clear()
        try:
            items = self.db.get_project_propositions(self.project_id)
            if not items:
                item = QListWidgetItem("No propositions added yet.")
                item.setFlags(Qt.ItemFlag.NoItemFlags)
                self.item_list.addItem(item)
                return

            for item_data in items:
                item = QListWidgetItem(item_data['display_name'])
                item.setData(Qt.ItemDataRole.UserRole, item_data['id'])
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
            data = self.db.get_proposition_details(item_id)
            if not data:
                self.detail_viewer.setHtml("<i>Could not load proposition details.</i>")
                return

            html = f"""
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; }}
                h2 {{ color: #111; margin-bottom: 5px; font-size: 1.5em; }}
                h3 {{ color: #333; border-bottom: 1px solid #ddd; padding-bottom: 4px; margin-top: 20px; margin-bottom: 10px; font-size: 1.2em; }}
                h4 {{ margin: 0 0 10px 0; color: #0055A4; font-size: 1.1em; }}
                .card {{ background: #ffffff; border: 1px solid #ddd; padding: 15px; border-radius: 5px; margin-bottom: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }}
                .meaning {{ background: #fdfdfd; border: 1px solid #eee; padding: 10px; border-radius: 5px; margin-bottom: 15px; font-size: 1.05em; }}
                .reference-block {{ padding-left: 15px; border-left: 3px solid #007acc; margin-top: 5px; }}
                .ref-notes {{ margin-top: 8px; }}
                .not-in-reading {{ font-style: italic; color: #777; }}
                a {{ color: #008080; text-decoration: none; font-weight: bold; }}
            </style>
            """

            html += f"<h2>{data.get('display_name', 'No Proposition')}</h2>"
            html += "<h3>My Proposition:</h3>"
            html += f"<div class='meaning'>{data.get('proposition_html', '<i>No proposition defined.</i>')}</div>"
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
                status = all_statuses.get(reading_id, 0)

                html += f"<div class='card'>"
                html += f"<h4>{reading_name}</h4>"

                if status == 1:
                    html += "<div class='not-in-reading'>Proposition not in reading.</div>"
                else:
                    refs_for_this_reading = [r for r in all_refs if r['reading_id'] == reading_id]
                    if not refs_for_this_reading:
                        html += "<div class='not-in-reading'>No references added.</div>"
                    else:
                        for i, ref in enumerate(refs_for_this_reading):
                            section = ref.get('section_title')
                            context = f"({section})" if section else "(Reading-Level)"

                            # Links (Multiple PDF nodes)
                            links_html = ""
                            if ref.get('pdf_nodes'):
                                link_parts = []
                                for node in ref['pdf_nodes']:
                                    pg = node['page_number'] + 1
                                    lbl = node['label']
                                    link_parts.append(f"<a href='pdfnode:///{node['id']}'>{lbl} (Pg {pg})</a>")
                                links_html = " - " + ", ".join(link_parts)
                            elif ref.get('page_number'):
                                links_html = f" - p. {ref['page_number']}"

                            html += f"<div class='reference-block'>"
                            html += f"<b>{context}{links_html}</b>"

                            html += f"<br><b style='color: #555;'>How the author addresses this proposition:</b>"
                            html += f"<div>{ref.get('how_addressed', 'N/A')}</div>"

                            html += f"<div class='ref-notes'><b style='color: #555;'>My Notes:</b>"
                            html += f"<div>{ref.get('notes', 'N/A')}</div></div>"

                            html += "</div>"

                            if i < len(refs_for_this_reading) - 1:
                                html += "<hr style='border: 0; border-top: 1px dashed #eee; margin: 10px 0;'>"

                html += "</div>"

            self.detail_viewer.setHtml(html)

        except Exception as e:
            self.detail_viewer.setHtml(f"<p><b>Error loading details:</b><br>{e}</p>")
            QMessageBox.critical(self, "Error", f"Could not load proposition details: {e}")

    def _on_link_clicked(self, url):
        """Handles clicks on anchors in the text browser."""
        url_str = url.toString()
        if url.scheme() == 'pdfnode' or url_str.startswith('pdfnode:'):
            try:
                path = url.path()
                if not path and ':' in url_str:
                    path = url_str.split(':', 1)[1]

                if path.startswith('/'): path = path[1:]

                if path.isdigit():
                    node_id = int(path)
                    self.requestOpenPdfNode.emit(node_id)
            except Exception as e:
                print(f"Error parsing PDF node link: {e}")

    @Slot(QPoint)
    def show_context_menu(self, position):
        menu = QMenu(self)
        menu.addAction("Add New Proposition...", self._add_item)

        item = self.item_list.itemAt(position)
        if item and item.data(Qt.ItemDataRole.UserRole) is not None:
            menu.addSeparator()
            menu.addAction("Edit Proposition...", self._edit_item)
            menu.addAction("Delete Proposition", self._delete_item)

        real_count = sum(
            1 for i in range(self.item_list.count()) if self.item_list.item(i).data(Qt.ItemDataRole.UserRole))
        if real_count > 1 and ReorderDialog:
            menu.addSeparator()
            menu.addAction("Reorder Propositions...", self._reorder_items)

        menu.exec(self.item_list.mapToGlobal(position))

    @Slot()
    def _add_item(self):
        if not AddPropositionDialog:
            QMessageBox.critical(self, "Error", "Add Proposition Dialog could not be loaded.")
            return

        dialog = AddPropositionDialog(self.db, self.project_id, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if not data['display_name']:
                QMessageBox.warning(self, "Invalid Name", "Display Name cannot be empty.")
                return
            try:
                self.db.save_proposition_entry(self.project_id, None, data)
                self.load_items()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not save new proposition: {e}")

    @Slot()
    def _edit_item(self):
        item = self.item_list.currentItem()
        if not item or item.data(Qt.ItemDataRole.UserRole) is None:
            return
        item_id = item.data(Qt.ItemDataRole.UserRole)

        if not AddPropositionDialog:
            QMessageBox.critical(self, "Error", "Edit Proposition Dialog could not be loaded.")
            return

        dialog = AddPropositionDialog(self.db, self.project_id, proposition_id=item_id, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if not data['display_name']:
                QMessageBox.warning(self, "Invalid Name", "Display Name cannot be empty.")
                return
            try:
                self.db.save_proposition_entry(self.project_id, item_id, data)
                self.load_items()
                for i in range(self.item_list.count()):
                    if self.item_list.item(i).data(Qt.ItemDataRole.UserRole) == item_id:
                        self.item_list.setCurrentRow(i)
                        break
                self.on_item_selected(self.item_list.currentItem(), None)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not update proposition: {e}")

    @Slot()
    def _delete_item(self):
        item = self.item_list.currentItem()
        if not item or item.data(Qt.ItemDataRole.UserRole) is None:
            return
        item_id = item.data(Qt.ItemDataRole.UserRole)
        item_name = item.text()
        reply = QMessageBox.question(
            self, "Delete Proposition",
            f"Are you sure you want to delete the proposition '{item_name}'?\n\nThis will remove the proposition and all its reading references.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.db.delete_proposition(item_id)
                self.load_items()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not delete proposition: {e}")

    @Slot()
    def _reorder_items(self):
        if not ReorderDialog:
            QMessageBox.critical(self, "Error", "Reorder dialog is not available.")
            return
        items_to_reorder = []
        for i in range(self.item_list.count()):
            item = self.item_list.item(i)
            item_id = item.data(Qt.ItemDataRole.UserRole)
            if item_id is not None: items_to_reorder.append((item.text(), item_id))
        if len(items_to_reorder) < 2: return
        dialog = ReorderDialog(items_to_reorder, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.db.update_proposition_order(dialog.ordered_db_ids)
            self.load_items()