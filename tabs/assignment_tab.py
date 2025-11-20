import sys
import re
import json
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QLabel,
    QTreeWidget, QTreeWidgetItem, QFrame, QMenu,
    QInputDialog, QMessageBox, QApplication, QDialog, QPushButton,
    QComboBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QTextCursor, QTextCharFormat, QFont

from tabs.rich_text_editor_tab import RichTextEditorTab, CitationDataProperty

try:
    from dialogs.reorder_dialog import ReorderDialog
except ImportError:
    ReorderDialog = None

try:
    from dialogs.add_citation_dialog import AddCitationDialog
except ImportError:
    AddCitationDialog = None

try:
    from pyzotero import zotero
except ImportError:
    zotero = None


class AssignmentTab(QWidget):
    """
    This is the "Assignment" tab, which holds the rubric
    and the assignment text editors.
    """

    CITATION_STYLES = {
        "APA (7th edition)": "apa",
        "MLA (9th edition)": "modern-language-association",
        "Chicago 18th (Notes & Bib)": "chicago-note-bibliography",
        "Chicago 18th (Author-Date)": "chicago-author-date",
        "IEEE": "ieee",
        "ASA (6th edition)": "american-sociological-association",
        "Harvard (Cite Them Right)": "harvard-cite-them-right"
    }

    def __init__(self, db_manager, project_id, spell_checker_service=None, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.project_id = project_id
        self.spell_checker_service = spell_checker_service
        self._block_rubric_item_changed = False

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(self.splitter, 1)

        # --- Left Panel (Rubric) ---
        left_panel = QFrame()
        left_panel.setFrameShape(QFrame.Shape.StyledPanel)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(6, 6, 6, 6)
        left_layout.setSpacing(4)

        rubric_label = QLabel("Rubric")
        rubric_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        left_layout.addWidget(rubric_label)

        self.rubric_tree = QTreeWidget()
        self.rubric_tree.setHeaderHidden(True)
        self.rubric_tree.setColumnCount(1)
        left_layout.addWidget(self.rubric_tree)

        self.rubric_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.rubric_tree.customContextMenuRequested.connect(self.show_rubric_context_menu)
        self.rubric_tree.itemChanged.connect(self.on_rubric_item_changed)

        # --- Right Panel (Editors) ---
        right_panel = QFrame()
        right_panel.setFrameShape(QFrame.Shape.StyledPanel)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(6, 6, 6, 6)

        editor_splitter = QSplitter(Qt.Orientation.Vertical)
        right_layout.addWidget(editor_splitter)

        # Top Editor
        instructions_widget = QWidget()
        instructions_layout = QVBoxLayout(instructions_widget)
        instructions_layout.setContentsMargins(0, 0, 0, 0)
        instructions_layout.setSpacing(4)
        instructions_label = QLabel("Assignment Instructions")
        instructions_label.setStyleSheet("font-weight: bold;")
        self.instructions_editor = RichTextEditorTab("Assignment Instructions",
                                                     spell_checker_service=self.spell_checker_service)
        instructions_layout.addWidget(instructions_label)
        instructions_layout.addWidget(self.instructions_editor)
        instructions_widget.setLayout(instructions_layout)

        # Bottom Editor
        draft_widget = QWidget()
        draft_layout = QVBoxLayout(draft_widget)
        draft_layout.setContentsMargins(0, 0, 0, 0)
        draft_layout.setSpacing(4)
        draft_label = QLabel("Assignment Draft")
        draft_label.setStyleSheet("font-weight: bold;")
        self.draft_editor = RichTextEditorTab("Assignment Draft", spell_checker_service=self.spell_checker_service)

        # Connect Editing Signal
        self.draft_editor.citationEditTriggered.connect(self.edit_citation)

        draft_layout.addWidget(draft_label)
        draft_layout.addWidget(self.draft_editor)
        draft_widget.setLayout(draft_layout)

        editor_splitter.addWidget(instructions_widget)
        editor_splitter.addWidget(draft_widget)
        editor_splitter.setStretchFactor(0, 1)
        editor_splitter.setStretchFactor(1, 2)

        self.splitter.addWidget(left_panel)
        self.splitter.addWidget(right_panel)
        self.splitter.setSizes([300, 700])

        # --- Bottom Button Bar ---
        button_bar = QWidget()
        button_bar.setStyleSheet("padding: 2px;")
        button_layout = QHBoxLayout(button_bar)
        button_layout.setContentsMargins(0, 0, 0, 0)

        btn_create_component = QPushButton("Create Component")
        btn_save_assignment = QPushButton("Save Assignment")

        # --- Citation Controls ---
        self.style_combo = QComboBox()
        self.style_combo.setMinimumWidth(200)
        self.style_combo.setToolTip("Select Citation Style for Zotero")

        for name, style_id in self.CITATION_STYLES.items():
            self.style_combo.addItem(name, style_id)

        self._load_style_preference()
        self.style_combo.currentIndexChanged.connect(self._save_style_preference)

        btn_add_citation = QPushButton("Add Zotero Citation")
        btn_gen_bib = QPushButton("Generate Bibliography")

        btn_gen_bib.clicked.connect(self.generate_bibliography)
        btn_create_component.clicked.connect(self.add_component)
        btn_save_assignment.clicked.connect(self.save_editors)
        btn_add_citation.clicked.connect(self.open_citation_dialog)

        button_layout.addWidget(btn_create_component)
        button_layout.addStretch()
        button_layout.addWidget(QLabel("Style:"))
        button_layout.addWidget(self.style_combo)
        button_layout.addWidget(btn_add_citation)
        button_layout.addWidget(btn_gen_bib)
        button_layout.addWidget(btn_save_assignment)

        main_layout.addWidget(button_bar)

    def _load_style_preference(self):
        settings = self.db.get_user_settings()
        if settings:
            saved_style = settings.get('citation_style', 'apa')
            index = self.style_combo.findData(saved_style)
            if index != -1:
                self.style_combo.setCurrentIndex(index)

    def _save_style_preference(self):
        style = self.style_combo.currentData()
        if style:
            self.db.save_citation_style(style)

    def load_data(self, project_details):
        self.load_rubric()
        instr_html = project_details.get('assignment_instructions_text', '')
        draft_html = project_details.get('assignment_draft_text', '')
        self.instructions_editor.set_html(instr_html or "")
        self.draft_editor.set_html(draft_html or "")

    def save_editors(self):
        print("Saving assignment editors...")
        self.instructions_editor.get_html(
            lambda html: self.db.update_project_text_field(
                self.project_id, 'assignment_instructions_text', html
            ) if html is not None else None
        )
        self.draft_editor.get_html(
            lambda html: self.db.update_project_text_field(
                self.project_id, 'assignment_draft_text', html
            ) if html is not None else None
        )

    def load_rubric(self):
        self._block_rubric_item_changed = True
        self.rubric_tree.clear()
        try:
            components = self.db.get_rubric_components(self.project_id)
            for comp in components:
                item = QTreeWidgetItem([comp['component_text']])
                item.setData(0, Qt.ItemDataRole.UserRole, comp['id'])
                item.setCheckState(0, Qt.CheckState.Checked if comp['is_checked'] else Qt.CheckState.Unchecked)
                self.rubric_tree.addTopLevelItem(item)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load rubric: {e}")
        finally:
            self._block_rubric_item_changed = False

    def on_rubric_item_changed(self, item, column):
        if self._block_rubric_item_changed or column != 0:
            return
        component_id = item.data(0, Qt.ItemDataRole.UserRole)
        is_checked = item.checkState(0) == Qt.CheckState.Checked
        try:
            self.db.update_rubric_component_checked(component_id, is_checked)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not update check state: {e}")

    def show_rubric_context_menu(self, position):
        menu = QMenu(self)
        item = self.rubric_tree.itemAt(position)
        add_action = QAction("Add Component", self)
        add_action.triggered.connect(self.add_component)
        menu.addAction(add_action)

        if item:
            menu.addSeparator()
            edit_action = QAction("Edit Component", self)
            edit_action.triggered.connect(self.edit_component)
            menu.addAction(edit_action)
            delete_action = QAction("Delete Component", self)
            delete_action.triggered.connect(self.delete_component)
            menu.addAction(delete_action)

        if ReorderDialog and self.rubric_tree.topLevelItemCount() > 0:
            menu.addSeparator()
            reorder_action = QAction("Reorder Components", self)
            reorder_action.triggered.connect(self.reorder_components)
            menu.addAction(reorder_action)

        menu.exec(self.rubric_tree.viewport().mapToGlobal(position))

    def add_component(self):
        text, ok = QInputDialog.getMultiLineText(self, "Add Rubric Component", "Component Text:")
        if ok and text:
            try:
                self.db.add_rubric_component(self.project_id, text)
                self.load_rubric()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not add component: {e}")

    def edit_component(self):
        item = self.rubric_tree.currentItem()
        if not item: return
        component_id = item.data(0, Qt.ItemDataRole.UserRole)
        current_text = item.text(0)
        text, ok = QInputDialog.getMultiLineText(self, "Edit Rubric Component", "Component Text:", current_text)
        if ok and text and text != current_text:
            try:
                self.db.update_rubric_component_text(component_id, text)
                self.load_rubric()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not update component: {e}")

    def delete_component(self):
        item = self.rubric_tree.currentItem()
        if not item: return
        component_id = item.data(0, Qt.ItemDataRole.UserRole)
        reply = QMessageBox.question(
            self, "Delete Component",
            f"Are you sure you want to delete this component?\n\n'{item.text(0)}'",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.db.delete_rubric_component(component_id)
                self.load_rubric()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not delete component: {e}")

    def reorder_components(self):
        if not ReorderDialog:
            QMessageBox.critical(self, "Error", "Reorder dialog is not available.")
            return
        try:
            items = self.db.get_rubric_components(self.project_id)
            if not items: return
            items_to_reorder = [(item['component_text'], item['id']) for item in items]
            dialog = ReorderDialog(items_to_reorder, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                ordered_ids = dialog.ordered_db_ids
                self.db.update_rubric_component_order(ordered_ids)
                self.load_rubric()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not reorder components: {e}")

    # --- Citation Logic ---
    def open_citation_dialog(self):
        if not AddCitationDialog:
            QMessageBox.critical(self, "Error", "Citation dialog could not be loaded.")
            return

        readings = self.db.get_readings(self.project_id)
        if not readings:
            QMessageBox.information(self, "No Readings",
                                    "You must add readings to this project before you can cite them.")
            return

        selected_style = self.style_combo.currentData() or "apa"

        dialog = AddCitationDialog(readings, parent=self, db=self.db, enable_zotero=True, citation_style=selected_style)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._insert_citations_from_dialog(dialog)

    def edit_citation(self, citation_data_json):
        """Re-opens the dialog to edit an existing citation."""
        try:
            # We rely on finding the citation by property.
            # The context menu already placed the cursor inside the citation property.
            cursor = self.draft_editor.editor.textCursor()
            fmt = cursor.charFormat()
            data_str = fmt.property(CitationDataProperty)

            # If for some reason data is missing or mismatch (cursor moved?), use argument
            if not data_str:
                data_str = citation_data_json

            data = json.loads(data_str)
            if not isinstance(data, list): data = [data]
        except:
            return

        readings = self.db.get_readings(self.project_id)
        style = self.style_combo.currentData() or "apa"

        dialog = AddCitationDialog(readings, parent=self, db=self.db, enable_zotero=True,
                                   citation_style=style, current_data=data)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Determine if Endnote/In-Text from dialog result
            if dialog.is_endnote_mode:
                # Determine which note we are editing by scanning for [N]
                # We look at the selection
                sel_text = cursor.selectedText()
                match = re.search(r"\[(\d+)\]", sel_text)
                existing_number = int(match.group(1)) if match else None

                self._insert_citations_from_dialog(dialog, edit_existing_number=existing_number)
            else:
                # In-Text: Remove old text and insert new
                # Make sure we select the WHOLE citation to replace it
                self.draft_editor._select_citation_at_cursor(cursor)
                cursor.removeSelectedText()
                self.draft_editor.editor.setTextCursor(cursor)

                self._insert_citations_from_dialog(dialog)

    def _insert_citations_from_dialog(self, dialog, edit_existing_number=None):
        """Helper to insert/merge citations and FIX FONTS."""
        citations = dialog.generated_citations
        if not citations: return

        data_json = json.dumps(dialog.result_data)

        # --- FONT FIX: Capture default format ---
        default_font = self.draft_editor.default_format.font()
        default_color = self.draft_editor.default_format.foreground()

        if dialog.is_endnote_mode:
            # --- ENDNOTE LOGIC ---
            combined_note = "; ".join(citations)
            if not combined_note.endswith("."): combined_note += "."

            if edit_existing_number is not None:
                # --- EDITING EXISTING ENDNOTE ---
                # 1. Update Marker Data (Selection is maintained)
                cursor = self.draft_editor.editor.textCursor()
                fmt = cursor.charFormat()
                fmt.setProperty(CitationDataProperty, data_json)
                cursor.mergeCharFormat(fmt)

                # 2. Update Footer Text
                doc = self.draft_editor.editor.document()
                # Heuristic search for footer note
                search_cursor = doc.find(f"[{edit_existing_number}]")
                while not search_cursor.isNull():
                    # Check if this is the marker or the footer note
                    # Marker has CitationDataProperty, footer note does not.
                    if not search_cursor.charFormat().property(CitationDataProperty):
                        # Found footer! Replace text.
                        search_cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
                        search_cursor.insertText(f"[{edit_existing_number}] {combined_note}")
                        break
                    search_cursor = doc.find(f"[{edit_existing_number}]", search_cursor)
            else:
                # --- NEW ENDNOTE ---
                current_html = self.draft_editor.editor.toHtml()
                pattern = r"\[(\d+)\]"
                matches = re.findall(pattern, current_html)
                next_num = max([int(m) for m in matches if m.isdigit()], default=0) + 1

                anchor_name = f"endnote-{next_num}"
                marker_text = f"[{next_num}]"

                cursor = self.draft_editor.editor.textCursor()

                # Insert marker
                marker_fmt = QTextCharFormat()
                marker_fmt.setVerticalAlignment(QTextCharFormat.VerticalAlignment.AlignSuperScript)
                marker_fmt.setForeground(Qt.blue)
                marker_fmt.setAnchor(True)
                marker_fmt.setAnchorHref(f"#{anchor_name}")
                marker_fmt.setProperty(CitationDataProperty, data_json)

                cursor.insertText(marker_text, marker_fmt)

                # FIX: Reset Font
                cursor.insertText("\u200B")  # Zero-width space
                clean_fmt = QTextCharFormat()
                clean_fmt.setFont(default_font)
                clean_fmt.setForeground(default_color)
                clean_fmt.setVerticalAlignment(QTextCharFormat.VerticalAlignment.AlignNormal)
                clean_fmt.setAnchor(False)
                clean_fmt.clearBackground()
                clean_fmt.clearProperty(CitationDataProperty)

                cursor.movePosition(QTextCursor.Left, QTextCursor.KeepAnchor, 1)
                cursor.setCharFormat(clean_fmt)
                cursor.clearSelection()
                self.draft_editor.editor.setTextCursor(cursor)

                # Append Note
                cursor.movePosition(QTextCursor.MoveOperation.End)
                self.draft_editor.editor.setTextCursor(cursor)

                if next_num == 1:
                    self.draft_editor.editor.insertHtml("<br><br><hr><h4>Notes</h4><br>")

                note_html = f"<p style='margin-bottom:10px;'><a name='{anchor_name}'></a><small>[{next_num}] {combined_note}</small></p><br>"
                self.draft_editor.editor.insertHtml(note_html)

        else:
            # --- IN-TEXT LOGIC ---
            text = dialog.result_text

            self.draft_editor.editor.insertPlainText(f" {text} ")

            cursor = self.draft_editor.editor.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.KeepAnchor, len(text) + 2)
            self.draft_editor.editor.setTextCursor(cursor)

            self.draft_editor.apply_citation_format(data_json)

            cursor.clearSelection()
            self.draft_editor.editor.setTextCursor(cursor)

            # FIX: Font Reset
            clean_fmt = QTextCharFormat()
            clean_fmt.setFont(default_font)
            self.draft_editor.editor.setCurrentCharFormat(clean_fmt)

        self.draft_editor.focus_editor()

    def generate_bibliography(self):
        """Fetches Zotero bibliography using the SELECTED STYLE."""
        if zotero is None:
            QMessageBox.critical(self, "Error", "PyZotero library is not installed.")
            return

        settings = self.db.get_user_settings()
        if not settings or not settings.get('zotero_library_id') or not settings.get('zotero_api_key'):
            QMessageBox.warning(self, "Zotero Settings",
                                "Please configure Zotero settings in the 'Add Reading' dialog first.")
            return

        readings = self.db.get_readings(self.project_id)
        keys = []
        for r in readings:
            k = r.get('zotero_item_key')
            if k: keys.append(k)

        if not keys:
            QMessageBox.information(self, "No Linked Readings",
                                    "No readings in this project are linked to Zotero items.")
            return

        selected_style = self.style_combo.currentData() or "apa"

        try:
            zot = zotero.Zotero(
                settings['zotero_library_id'],
                settings.get('zotero_library_type', 'user'),
                settings['zotero_api_key']
            )

            keys_str = ",".join(keys)

            bib_html = zot.items(itemKey=keys_str, format='bib', style=selected_style)

            if not bib_html:
                raise Exception("Empty response from Zotero.")

            if isinstance(bib_html, list):
                bib_html = "".join(str(x) for x in bib_html)

            html_to_insert = "<br><hr><h2>Bibliography</h2>" + bib_html

            cursor = self.draft_editor.editor.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.draft_editor.editor.setTextCursor(cursor)
            self.draft_editor.editor.insertHtml(html_to_insert)

            QMessageBox.information(self, "Success", "Bibliography generated and appended to draft.")

        except Exception as e:
            QMessageBox.critical(self, "Zotero API Error", f"Failed to generate bibliography: {e}")