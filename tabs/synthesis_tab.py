# prospectcreek/3rdeditionreadingtracker/tabs/synthesis_tab.py
import sys
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QLabel,
    QListWidget, QListWidgetItem, QFrame, QTextEdit, QCheckBox,
    QTextBrowser, QMenu, QInputDialog, QMessageBox, QDialog,
    QTabWidget, QPushButton
)
from PySide6.QtCore import Qt, Signal, Slot, QUrl, QPoint
from PySide6.QtGui import QColor, QFont, QAction
import sqlite3

try:
    from tabs.rich_text_editor_tab import RichTextEditorTab
except ImportError:
    print("Error: Could not import RichTextEditorTab")
    RichTextEditorTab = None

try:
    from tabs.terminology_tab import TerminologyTab
except ImportError:
    print("Error: Could not import TerminologyTab")
    TerminologyTab = None

try:
    from tabs.propositions_tab import PropositionsTab
except ImportError:
    print("Error: Could not import PropositionsTab")
    PropositionsTab = None

try:
    from dialogs.edit_tag_dialog import EditTagDialog
except ImportError:
    print("Error: Could not import EditTagDialog")
    EditTagDialog = None

try:
    from dialogs.manage_anchors_dialog import ManageAnchorsDialog
except ImportError:
    print("Error: Could not import ManageAnchorsDialog")
    ManageAnchorsDialog = None

try:
    from dialogs.add_citation_dialog import AddCitationDialog
except ImportError:
    print("Error: Could not import AddCitationDialog for SynthesisTab")
    AddCitationDialog = None


class SynthesisTab(QWidget):
    """
    A widget for synthesizing information.
    Shows a master list of tags and a detail view of anchors.
    """
    openReading = Signal(int, int, int, int, str)
    tagsUpdated = Signal()

    def __init__(self, db, project_id, parent=None):
        super().__init__(parent)
        self.db = db
        self.project_id = project_id

        main_layout = QHBoxLayout(self)
        self.main_splitter = QSplitter(Qt.Orientation.Vertical)
        main_layout.addWidget(self.main_splitter)

        top_widget = QFrame()
        top_widget.setFrameShape(QFrame.Shape.StyledPanel)
        top_layout = QHBoxLayout(top_widget)
        top_widget.setLayout(top_layout)

        top_splitter = QSplitter(Qt.Orientation.Horizontal)
        top_layout.addWidget(top_splitter)

        left_panel = QFrame()
        left_panel.setFrameShape(QFrame.Shape.NoFrame)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(4, 4, 4, 4)
        left_layout.addWidget(QLabel("Synthesis Tags"))
        self.tag_list = QListWidget()
        left_layout.addWidget(self.tag_list)
        left_panel.setLayout(left_layout)

        right_panel = QFrame()
        right_panel.setFrameShape(QFrame.Shape.NoFrame)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(4, 4, 4, 4)
        right_layout.addWidget(QLabel("Connected Anchors"))
        self.anchor_display = QTextBrowser()
        self.anchor_display.setOpenExternalLinks(False)
        self.anchor_display.anchorClicked.connect(self.on_anchor_link_clicked)
        right_layout.addWidget(self.anchor_display)
        right_panel.setLayout(right_layout)

        top_splitter.addWidget(left_panel)
        top_splitter.addWidget(right_panel)
        top_splitter.setSizes([250, 600])

        bottom_panel = QFrame()
        bottom_panel.setFrameShape(QFrame.Shape.StyledPanel)
        bottom_layout = QVBoxLayout(bottom_panel)
        bottom_layout.setContentsMargins(4, 4, 4, 4)
        self.bottom_tab_widget = QTabWidget()
        bottom_layout.addWidget(self.bottom_tab_widget)

        if TerminologyTab:
            self.terminology_tab = TerminologyTab(self.db, self.project_id)
            self.bottom_tab_widget.addTab(self.terminology_tab, "My Terminology")
        else:
            self.bottom_tab_widget.addTab(QLabel("TerminologyTab failed to load."), "My Terminology")

        if PropositionsTab:
            self.propositions_tab = PropositionsTab(self.db, self.project_id)
            self.bottom_tab_widget.addTab(self.propositions_tab, "My Propositions")
        else:
            self.propositions_tab = QLabel("PropositionsTab failed to load.")
            self.propositions_tab.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.bottom_tab_widget.addTab(self.propositions_tab, "My Propositions")

        notes_container = QWidget()
        notes_layout = QVBoxLayout(notes_container)
        notes_layout.setContentsMargins(0, 0, 0, 0)
        notes_layout.setSpacing(4)

        if RichTextEditorTab:
            self.notes_editor = RichTextEditorTab("Notes")
            notes_layout.addWidget(self.notes_editor, 1)
            notes_btn_layout = QHBoxLayout()
            notes_btn_layout.addStretch(1)
            self.notes_citation_btn = QPushButton("Add Citation")
            self.notes_citation_btn.clicked.connect(self.open_notes_citation_dialog)
            notes_btn_layout.addWidget(self.notes_citation_btn)
            notes_layout.addLayout(notes_btn_layout)
            self.bottom_tab_widget.addTab(notes_container, "Notes")
        else:
            self.bottom_tab_widget.addTab(QLabel("Editor failed to load."), "Notes")

        self.main_splitter.addWidget(top_widget)
        self.main_splitter.addWidget(bottom_panel)
        self.main_splitter.setStretchFactor(0, 1)
        self.main_splitter.setStretchFactor(1, 1)

        self.tag_list.currentItemChanged.connect(self.on_tag_selected)
        self.tag_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tag_list.customContextMenuRequested.connect(self.show_tag_context_menu)

    def load_tab_data(self, project_details):
        self.load_tags_list()
        self.anchor_display.clear()
        if TerminologyTab and hasattr(self, 'terminology_tab'):
            self.terminology_tab.load_terminology()
        if PropositionsTab and hasattr(self, 'propositions_tab'):
            self.propositions_tab.load_items()
        if RichTextEditorTab and hasattr(self, 'notes_editor'):
            self.notes_editor.set_html(project_details.get('synthesis_notes_html', ''))

    def save_editors(self):
        if self.project_id == -1:
            return
        print("Saving synthesis editors...")
        if RichTextEditorTab and hasattr(self, 'notes_editor'):
            def create_callback(field_name):
                return lambda html: self.db.update_project_text_field(
                    self.project_id, field_name, html
                ) if html is not None else None

            self.notes_editor.get_html(create_callback('synthesis_notes_html'))

    def load_tags_list(self):
        self.tag_list.clear()
        try:
            tags = self.db.get_tags_with_counts(self.project_id)
            if not tags:
                item = QListWidgetItem("No tags created yet.")
                item.setFlags(Qt.ItemFlag.NoItemFlags)
                self.tag_list.addItem(item)
                return
            for tag in tags:
                display_text = f"{tag['name']} ({tag['anchor_count']})"
                item = QListWidgetItem(display_text)
                item.setData(Qt.ItemDataRole.UserRole, tag['id'])
                item.setData(Qt.ItemDataRole.UserRole + 1, tag['name'])
                self.tag_list.addItem(item)
        except Exception as e:
            QMessageBox.critical(self, "Error Loading Tags", f"Could not load tags: {e}")

    @Slot(QListWidgetItem, QListWidgetItem)
    def on_tag_selected(self, current_item, previous_item):
        if current_item is None:
            self.anchor_display.clear()
            return
        tag_id = current_item.data(Qt.ItemDataRole.UserRole)
        if tag_id is None:
            self.anchor_display.clear()
            return

        try:
            anchors = self.db.get_anchors_for_tag_with_context(tag_id, self.project_id)
            if not anchors:
                self.anchor_display.setHtml("<i>No anchors found for this tag.</i>")
                return

            html = """
            <style>
                h3 { margin-top: 15px; margin-bottom: 5px; font-size: 1.2em; }
                p { margin-top: 0px; margin-bottom: 2px; }
                blockquote { 
                    margin-top: 5px; 
                    margin-bottom: 10px; 
                    margin-left: 15px; 
                    padding-left: 10px; 
                    border-left: 3px solid #ccc; 
                }
                a { color: #0000EE; text-decoration: none; }
                a:hover { text-decoration: underline; }
                .virtual-anchor-title { font-weight: bold; }
                .virtual-anchor-content { font-style: italic; }
            </style>
            """

            current_reading = None
            for anchor in anchors:
                reading_name = anchor['reading_nickname'] or anchor['reading_title']
                if reading_name != current_reading:
                    current_reading = reading_name
                    html += f"<h3>{current_reading}</h3>"

                context_parts = []
                if anchor['outline_title']:
                    context_parts.append(f"Section: {anchor['outline_title']}")

                item_link_id = anchor.get('item_link_id')
                item_type = anchor.get('item_type') or ''
                jumpto_link = (
                    f"jumpto:{anchor['id']}:{anchor['reading_id']}:{anchor['outline_id'] or 0}:"
                    f"{item_link_id or 0}:{item_type}"
                )

                if context_parts:
                    html += f"<p><i><a href='{jumpto_link}'>({', '.join(context_parts)})</a></i></p>"
                else:
                    html += f"<p><i><a href='{jumpto_link}'>(Reading-Level Note)</a></i></p>"

                html += "<blockquote>"

                # --- THIS IS THE FIX ---
                if item_link_id:
                    # This is a VIRTUAL ANCHOR (DQ, Term, Prop, Arg, Theory)

                    # 1. Get the title (Nickname or Anchor Summary)
                    title = anchor.get('nickname') or anchor.get('selected_text', 'Linked Item')
                    title = title.replace("\n", "<br>")
                    html += f"<p class='virtual-anchor-title'>{title}</p>"

                    # 2. Get the content (Definition, Question Text, Claim, etc.)
                    content_html = ""
                    if item_type == 'dq':
                        content_html = anchor.get('dq_question_text')
                    elif item_type == 'term':
                        content_html = anchor.get('dq_definition')  # 'question_category' is aliased
                    elif item_type == 'theory':
                        content_html = anchor.get('dq_definition')  # 'question_category' is aliased
                    elif item_type == 'proposition':
                        content_html = anchor.get('dq_question_text')
                    elif item_type == 'argument':
                        claim = anchor.get('arg_claim_text', '')
                        content_html = f"Claim: {claim}"

                    if content_html:
                        content_html = content_html.replace("\n", "<br>")
                        html += f"<p class='virtual-anchor-content'>{content_html}</p>"

                else:
                    # This is a standard TEXT ANCHOR
                    selected_text_html = anchor['selected_text'].replace("\n", "<br>")
                    html += f"<p>{selected_text_html}</p>"

                    comment = anchor.get('comment', '')
                    if comment:
                        comment_html = comment.replace("\n", "<br>")
                        html += f"<p><i>— {comment_html}</i></p>"
                # --- END FIX ---

                html += "</blockquote>"

            self.anchor_display.setHtml(html)

        except Exception as e:
            self.anchor_display.setHtml(f"<p><b>Error loading anchors:</b><br>{e}</p>")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Could not load anchors: {e}")

    @Slot(QUrl)
    def on_anchor_link_clicked(self, url):
        url_str = url.toString()
        if url_str.startswith("jumpto:"):
            try:
                parts = url_str.split(":")
                if len(parts) < 6:
                    raise ValueError("Malformed jumpto link")
                anchor_id = int(parts[1])
                reading_id = int(parts[2])
                outline_id = int(parts[3])
                item_link_id = int(parts[4])
                item_type = parts[5]
                print(
                    "Emitting openReading signal for "
                    f"anchor_id={anchor_id}, reading_id={reading_id}, outline_id={outline_id}, "
                    f"item_id={item_link_id}, type={item_type}"
                )
                self.openReading.emit(anchor_id, reading_id, outline_id, item_link_id, item_type)
            except Exception as e:
                print(f"Error handling jumpto link: {e}")

    @Slot(QPoint)
    def show_tag_context_menu(self, position):
        menu = QMenu(self)
        item = self.tag_list.itemAt(position)
        create_action = QAction("Create New Tag...", self)
        create_action.triggered.connect(self._create_new_tag)
        menu.addAction(create_action)
        if item and item.data(Qt.ItemDataRole.UserRole) is not None:
            menu.addSeparator()
            manage_action = QAction("Manage Anchors for this Tag...", self)
            manage_action.triggered.connect(self._manage_tag_anchors)
            menu.addAction(manage_action)
            rename_action = QAction("Rename Tag...", self)
            rename_action.triggered.connect(self._rename_tag)
            menu.addAction(rename_action)
            delete_action = QAction("Delete Tag and All Anchors...", self)
            delete_action.triggered.connect(self._delete_tag)
            menu.addAction(delete_action)
        menu.exec(self.tag_list.mapToGlobal(position))

    @Slot()
    def _create_new_tag(self):
        if not EditTagDialog:
            QMessageBox.critical(self, "Error", "EditTagDialog could not be loaded.")
            return
        dialog = EditTagDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_name = dialog.get_tag_name()
            if not new_name:
                QMessageBox.warning(self, "Invalid Name", "Tag name cannot be empty.")
                return
            try:
                self.db.get_or_create_tag(new_name, self.project_id)
                self.load_tags_list()
            except sqlite3.IntegrityError:
                QMessageBox.warning(self, "Tag Exists", f"A tag named '{new_name}' already exists.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not create tag: {e}")

    @Slot()
    def _rename_tag(self):
        item = self.tag_list.currentItem()
        if not item or item.data(Qt.ItemDataRole.UserRole) is None:
            return
        tag_id = item.data(Qt.ItemDataRole.UserRole)
        tag_name = item.data(Qt.ItemDataRole.UserRole + 1)
        if not EditTagDialog:
            QMessageBox.critical(self, "Error", "EditTagDialog could not be loaded.")
            return
        dialog = EditTagDialog(current_name=tag_name, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_name = dialog.get_tag_name()
            if not new_name or new_name == tag_name:
                return
            try:
                self.db.rename_tag(tag_id, new_name)
                self.load_tags_list()
                self.tagsUpdated.emit()
            except sqlite3.IntegrityError:
                QMessageBox.warning(self, "Tag Exists", f"A tag named '{new_name}' already exists.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not rename tag: {e}")

    @Slot()
    def _delete_tag(self):
        item = self.tag_list.currentItem()
        if not item or item.data(Qt.ItemDataRole.UserRole) is None:
            return
        tag_id = item.data(Qt.ItemDataRole.UserRole)
        tag_name = item.data(Qt.ItemDataRole.UserRole + 1)
        reply = QMessageBox.question(
            self, "Delete Tag",
            f"Are you sure you want to delete the tag '{tag_name}'?\n\n"
            "This will delete the tag itself AND all anchors associated with it from all projects.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.db.delete_tag_and_anchors(tag_id)
                self.tagsUpdated.emit()
                self.load_tags_list()
                self.anchor_display.clear()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not delete tag: {e}")

    @Slot()
    def _manage_tag_anchors(self):
        item = self.tag_list.currentItem()
        if not item or item.data(Qt.ItemDataRole.UserRole) is None:
            return
        tag_id = item.data(Qt.ItemDataRole.UserRole)
        tag_name = item.data(Qt.ItemDataRole.UserRole + 1)
        if not ManageAnchorsDialog:
            QMessageBox.critical(self, "Error", "ManageAnchorsDialog could not be loaded.")
            return

        # ##################################################################
        # #
        # #                      --- MODIFICATION START ---
        # #
        # ##################################################################
        # Pass the project_id to the dialog
        dialog = ManageAnchorsDialog(self.db, self.project_id, tag_id, tag_name, self)
        # ##################################################################
        # #
        # #                      --- MODIFICATION END ---
        # #
        # ##################################################################

        dialog.anchorDeleted.connect(self._on_anchor_deleted_from_dialog)
        dialog.exec()

    @Slot()
    def _on_anchor_deleted_from_dialog(self):
        self.tagsUpdated.emit()
        self.load_tags_list()
        current_item = self.tag_list.currentItem()
        if current_item:
            self.on_tag_selected(current_item, None)
        else:
            self.anchor_display.clear()

    @Slot(int)
    def select_tag_by_id(self, tag_id_to_select):
        for i in range(self.tag_list.count()):
            item = self.tag_list.item(i)
            tag_id = item.data(Qt.ItemDataRole.UserRole)
            if tag_id == tag_id_to_select:
                self.tag_list.setCurrentItem(item)
                return

    @Slot()
    def open_notes_citation_dialog(self):
        if not AddCitationDialog:
            QMessageBox.critical(self, "Error", "Citation dialog could not be loaded.")
            return
        readings = self.db.get_readings(self.project_id)
        if not readings:
            QMessageBox.information(self, "No Readings",
                                    "You must add readings to this project before you can cite them.")
            return
        dialog = AddCitationDialog(readings, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.citation_text:
            if hasattr(self, 'notes_editor') and self.notes_editor:
                self.notes_editor.editor.insertPlainText(f" {dialog.citation_text} ")
                self.notes_editor.focus_editor()
            else:
                QMessageBox.warning(self, "Error", "Notes editor is not available.")