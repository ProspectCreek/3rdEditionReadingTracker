# tabs/reading_notes_tab.py
import sys
import uuid  # <-- NEW: For synthesis anchors
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QLabel, QFrame,
    QTreeWidget, QTreeWidgetItem, QFormLayout, QLineEdit, QComboBox,
    QPushButton, QMenu, QStackedWidget, QInputDialog, QMessageBox, QDialog,
    QTabWidget, QMenuBar, QTextEdit, QApplication, QAbstractItemView,
    QTreeWidgetItemIterator
    # <-- REMOVED QTextBrowser
)
from PySide6.QtCore import Qt, Signal, QPoint, Slot, QTimer, QUrl  # <-- Added QTimer, QUrl
from PySide6.QtGui import QAction, QTextCharFormat, QColor, QTextCursor

from tabs.rich_text_editor_tab import (
    RichTextEditorTab, AnchorIDProperty, AnchorTagNameProperty,
    AnchorTagIDProperty, AnchorCommentProperty, AnchorUUIDProperty
)

# --- NEW: Import all the new tab types ---
try:
    from tabs.driving_question_tab import DrivingQuestionTab
except ImportError:
    print("Error: Could not import DrivingQuestionTab")
    DrivingQuestionTab = None

try:
    from tabs.attachments_tab import AttachmentsTab
except ImportError:
    print("Error: Could not import AttachmentsTab")
    AttachmentsTab = None

try:
    from tabs.timers_tab import TimersTab
except ImportError:
    print("Error: Could not import TimersTab")
    TimersTab = None
# --- END NEW ---


# Import dialogs
try:
    from dialogs.reorder_dialog import ReorderDialog
except ImportError:
    print("Error: Could not import ReorderDialog for ReadingNotesTab")
    ReorderDialog = None

try:
    from dialogs.page_number_dialog import PageNumberDialog
except ImportError:
    print("Error: Could not import PageNumberDialog for ReadingNotesTab")
    PageNumberDialog = None

# --- NEW: Import Anchor Dialog ---
try:
    from dialogs.create_anchor_dialog import CreateAnchorDialog
except ImportError:
    print("Error: Could not import CreateAnchorDialog")
    CreateAnchorDialog = None


# --- END NEW ---


class ReadingNotesTab(QWidget):
    """
    This tab holds the complex layout for managing a single reading,
    including details, outline, and notes.
    """

    # let dashboard know to rename tab/tree when details saved
    readingTitleChanged = Signal(int, object)  # (reading_id, self)

    # --- FIX: Updated __init__ signature ---
    def __init__(self, db, project_id: int, reading_id: int, parent=None):
        super().__init__(parent)
        self.db = db
        self.project_id = project_id  # <-- Store project_id
        self.reading_id = reading_id
        # --- END FIX ---

        self.reading_details_row = None  # sqlite3.Row
        self.current_outline_id = None
        self._block_outline_save = False  # prevent save-on-switch loops
        self._is_loaded = False  # <<< guard to avoid saving blanks

        # --- NEW (Step 5.2): Store all bottom editors ---
        self.bottom_editors = {}
        # --- END NEW ---

        # Main Layout: A horizontal splitter
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # --- Left Panel (Details + Outline) ---
        left_panel = QFrame()
        left_panel.setFrameShape(QFrame.Shape.StyledPanel)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(4, 4, 4, 4)

        # Vertical splitter for left panel
        left_splitter = QSplitter(Qt.Orientation.Vertical)
        left_layout.addWidget(left_splitter)

        # Top-Left: Reading Details
        details_frame = QFrame()
        details_frame.setFrameShape(QFrame.Shape.StyledPanel)
        details_layout = QVBoxLayout(details_frame)
        details_layout.setContentsMargins(6, 6, 6, 6)

        details_label = QLabel("Reading Details")
        details_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        details_layout.addWidget(details_label)

        self._create_details_form(details_layout)

        # Bottom-Left: Reading Outline
        outline_frame = QFrame()
        outline_frame.setFrameShape(QFrame.Shape.StyledPanel)
        outline_layout = QVBoxLayout(outline_frame)
        outline_layout.setContentsMargins(6, 6, 6, 6)

        outline_label = QLabel("Outline")
        outline_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        outline_layout.addWidget(outline_label)

        self.outline_tree = QTreeWidget()
        self.outline_tree.setHeaderHidden(True)
        # --- NEW: Allow selecting nothing ---
        self.outline_tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        # --- END NEW ---
        outline_layout.addWidget(self.outline_tree, 1)

        outline_btn_layout = QHBoxLayout()
        btn_add_section = QPushButton("+ Section")
        btn_add_subsection = QPushButton("+ Subsection")
        outline_btn_layout.addWidget(btn_add_section)
        outline_btn_layout.addWidget(btn_add_subsection)
        outline_btn_layout.addStretch()
        outline_layout.addLayout(outline_btn_layout)

        # Add to left splitter
        left_splitter.addWidget(details_frame)
        left_splitter.addWidget(outline_frame)
        left_splitter.setSizes([1, 450])
        details_frame.setMinimumHeight(150)
        left_splitter.setCollapsible(0, True)
        left_splitter.setCollapsible(1, False)

        # --- Right Panel (Notes) ---
        right_panel = QFrame()
        right_panel.setFrameShape(QFrame.Shape.StyledPanel)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(6, 6, 6, 6)
        right_layout.setSpacing(0)  # --- FIX for menu bar ---

        # --- NEW: Menu Bar ---
        self.reading_menu_bar = QMenuBar()
        right_layout.addWidget(self.reading_menu_bar)
        self._create_reading_menu(self.reading_menu_bar)
        # --- END NEW ---

        # Vertical splitter for notes and bottom tabs
        right_splitter = QSplitter(Qt.Orientation.Vertical)
        right_layout.addWidget(right_splitter)

        # Top-Right Widget (The Notes Editor)
        top_right_widget = QWidget()
        top_right_layout = QVBoxLayout(top_right_widget)
        top_right_layout.setContentsMargins(0, 4, 0, 0)  # --- Add padding above label ---
        top_right_layout.setSpacing(4)

        notes_label = QLabel("Outline Item Notes")
        notes_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        top_right_layout.addWidget(notes_label)

        # Stacked widget to show/hide editor
        self.notes_stack = QStackedWidget()
        top_right_layout.addWidget(self.notes_stack, 1)

        # Page 0: Placeholder
        self.notes_placeholder = QLabel("Select an outline item to view its notes.")
        self.notes_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.notes_placeholder.setStyleSheet("color: #888; font-style: italic;")
        self.notes_stack.addWidget(self.notes_placeholder)

        # Page 1: Editor
        self.notes_editor = RichTextEditorTab("Outline Notes")
        self.notes_stack.addWidget(self.notes_editor)

        # --- NEW: Connect anchor signals ---
        self.notes_editor.anchorActionTriggered.connect(self._on_create_anchor)
        self.notes_editor.anchorEditTriggered.connect(self._on_edit_anchor)
        self.notes_editor.anchorDeleteTriggered.connect(self._on_delete_anchor)
        # --- END NEW ---

        self.notes_stack.setCurrentWidget(self.notes_placeholder)  # Start on placeholder

        # Add Citation button
        citation_btn_layout = QHBoxLayout()
        btn_add_citation = QPushButton("Add Citation (p.)")
        citation_btn_layout.addStretch()
        citation_btn_layout.addWidget(btn_add_citation)
        top_right_layout.addLayout(citation_btn_layout)

        # --- Bottom-Right Widget (New Tabbed Area) ---
        # --- FIX: Create a frame for the bottom tabs ---
        bottom_right_frame = QFrame()
        bottom_right_frame.setFrameShape(QFrame.Shape.StyledPanel)
        bottom_right_layout = QVBoxLayout(bottom_right_frame)
        bottom_right_layout.setContentsMargins(6, 6, 6, 6)

        self.bottom_right_tabs = QTabWidget()
        bottom_right_layout.addWidget(self.bottom_right_tabs)
        # --- END FIX ---

        right_splitter.addWidget(top_right_widget)
        right_splitter.addWidget(bottom_right_frame)  # <-- Add the frame

        # --- FIX: Set 50/50 split ---
        right_splitter.setStretchFactor(0, 1)
        right_splitter.setStretchFactor(1, 1)
        # --- END FIX ---

        # --- Add all the new tabs ---
        self._add_bottom_tabs()
        # --- END ---

        # Add panels to main splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([400, 600])

        # --- Connect Signals ---
        self.btn_save_details.clicked.connect(self.save_details)
        self.outline_tree.customContextMenuRequested.connect(self.show_outline_context_menu)
        self.outline_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.outline_tree.currentItemChanged.connect(self.on_outline_selection_changed)

        btn_add_section.clicked.connect(self.add_section)
        btn_add_subsection.clicked.connect(self.add_subsection)
        btn_add_citation.clicked.connect(self.open_page_citation_dialog)

    def _create_details_form(self, parent_layout):
        """Creates the QFormLayout for reading details."""
        form_layout = QFormLayout()
        form_layout.setSpacing(8)

        self.edit_title = QLineEdit()
        self.edit_author = QLineEdit()
        self.edit_published = QLineEdit()
        self.edit_nickname = QLineEdit()
        self.edit_pages = QLineEdit()
        self.edit_assignment = QLineEdit()
        self.combo_level = QComboBox()
        self.edit_classification = QLineEdit()

        self.combo_level.addItems([
            "Elementary (Entertainment)",
            "Inspectional (Information)",
            "Analytical (Understanding)",
            "Syntopic (Mastery)"
        ])

        form_layout.addRow("Title:", self.edit_title)
        form_layout.addRow("Author:", self.edit_author)
        form_layout.addRow("Published:", self.edit_published)
        form_layout.addRow("Citation Nickname:", self.edit_nickname)
        form_layout.addRow("Pages:", self.edit_pages)
        form_layout.addRow("Assignment:", self.edit_assignment)
        form_layout.addRow("Level:", self.combo_level)
        form_layout.addRow("Classification:", self.edit_classification)

        parent_layout.addLayout(form_layout)

        # Buttons
        details_btn_layout = QHBoxLayout()
        self.btn_reading_rules = QPushButton("Reading Rules")
        self.btn_save_details = QPushButton("Save Details")
        details_btn_layout.addStretch()
        details_btn_layout.addWidget(self.btn_reading_rules)
        details_btn_layout.addWidget(self.btn_save_details)
        parent_layout.addLayout(details_btn_layout)

    def _add_bottom_tabs(self):
        """Creates and adds all the tabs for the bottom-right panel."""

        # --- Driving Question ---
        if DrivingQuestionTab:
            self.driving_question_tab = DrivingQuestionTab(self.db, self.reading_id)
            self.bottom_right_tabs.addTab(self.driving_question_tab, "Driving Question")
        else:
            self.bottom_right_tabs.addTab(QLabel("Driving Question (Failed to load)"), "Driving Question")

        # --- MODIFIED (Step 5.2): Activate all placeholder tabs ---

        # Helper function to create a standard editor tab
        def create_editor_tab(title, instructions, field_name):
            widget = QWidget()
            layout = QVBoxLayout(widget)
            layout.setContentsMargins(4, 4, 4, 4)
            layout.setSpacing(4)
            if instructions:
                layout.addWidget(QLabel(instructions))

            editor = RichTextEditorTab(title)
            self.bottom_editors[field_name] = editor  # Store editor
            layout.addWidget(editor)

            self.bottom_right_tabs.addTab(widget, title)

        # --- Leading Propositions ---
        create_editor_tab("Leading Propositions", "Instructions for Leading Propositions go here.", "propositions_html")

        # --- Unity ---
        create_editor_tab("Unity", "Instructions for Unity go here.", "unity_html")

        # --- Elevator Abstract ---
        create_editor_tab("Elevator Abstract", "Instructions for Elevator Abstract go here.",
                          "personal_dialogue_html")  # Re-using personal_dialogue

        # --- Parts: Order and Relation ---
        # Note: This tab is complex, for now we make it a simple notes tab.
        # We will reuse the 'personal_dialogue_html' field as a placeholder.
        # In a future step, this could be a tree editor.
        create_editor_tab("Parts", "Instructions for Parts: Order and Relation go here.", "personal_dialogue_html")

        # --- Key Terms ---
        create_editor_tab("Key Terms", "Instructions for Key Terms go here.", "key_terms_html")

        # --- Arguments ---
        create_editor_tab("Arguments", "Instructions for Arguments go here.", "arguments_html")

        # --- Gaps ---
        create_editor_tab("Gaps", "Instructions for Gaps go here.", "gaps_html")

        # --- Theories ---
        create_editor_tab("Theories", "Instructions for Theories go here.", "theories_html")

        # --- Personal Dialogue ---
        create_editor_tab("Personal Dialogue", "Instructions for Personal Dialogue go here.", "personal_dialogue_html")

        # --- END MODIFIED ---

        # --- Attachments ---
        if AttachmentsTab:
            self.attachments_tab = AttachmentsTab(self.db, self.reading_id)
            self.bottom_right_tabs.addTab(self.attachments_tab, "Attachments")
        else:
            self.bottom_right_tabs.addTab(QLabel("Attachments (Failed to load)"), "Attachments")

        # --- Timers ---
        if TimersTab:
            self.timers_tab = TimersTab()
            self.bottom_right_tabs.addTab(self.timers_tab, "Timers")
        else:
            self.bottom_right_tabs.addTab(QLabel("Timers (Failed to load)"), "Timers")

    # --- NEW: Menu placeholder ---
    def _create_reading_menu(self, menu_bar: QMenuBar):
        settings_menu = menu_bar.addMenu("Reading Settings")
        edit_instr_action = QAction("Edit Tab Instructions...", self)
        edit_instr_action.setEnabled(False)  # Not implemented yet
        settings_menu.addAction(edit_instr_action)

    # --- Data Loading and Saving ---

    def _get_detail(self, key, default=''):
        """Safely get a value from the sqlite3.Row by key."""
        try:
            if self.reading_details_row and key in self.reading_details_row.keys():
                val = self.reading_details_row[key]
                return val if val is not None else default
            return default
        except (IndexError, AttributeError):
            return default

    def load_data(self):
        """
        Called by the dashboard to load all data for this reading tab.
        """
        try:
            details = self.db.get_reading_details(self.reading_id)
            if not details:
                QMessageBox.critical(self, "Error", f"Could not load details for reading ID {self.reading_id}")
                return

            self.reading_details_row = details

            title = self._get_detail('title')
            author = self._get_detail('author')
            nickname = self._get_detail('nickname')

            self.edit_title.setText(title)
            self.edit_author.setText(author)
            self.edit_nickname.setText(nickname)
            self.edit_published.setText(self._get_detail('published'))
            self.edit_pages.setText(self._get_detail('pages'))
            self.edit_assignment.setText(self._get_detail('assignment'))
            self.edit_classification.setText(self._get_detail('classification'))

            level_text = self._get_detail('level')
            level_index = self.combo_level.findText(level_text, Qt.MatchFlag.MatchStartsWith)
            self.combo_level.setCurrentIndex(level_index if level_index != -1 else 0)

            # Populate Outline
            self.load_outline()

            # Mark as fully loaded so autosave is allowed
            self._is_loaded = True

            # --- MODIFIED (Step 5.2): Load bottom tab data ---
            self.load_bottom_tabs_content()
            # --- END MODIFIED ---

            print(f"Loading details for reading {self.reading_id}: {dict(self.reading_details_row)}")

        except Exception as e:
            QMessageBox.critical(self, "Error Loading Reading", f"An error occurred: {e}")
            import traceback;
            traceback.print_exc()

    # --- NEW: Bottom Tab Load/Save (Step 5.2) ---
    def load_bottom_tabs_content(self):
        """Loads data into the bottom-right tabs."""
        if not self.reading_details_row:
            return
        for field_name, editor in self.bottom_editors.items():
            html = self._get_detail(field_name, default="")
            editor.set_html(html)

    def save_bottom_tabs_content(self):
        """Saves data from the bottom-right tabs."""
        if not self._is_loaded:
            return
        for field_name, editor in self.bottom_editors.items():
            # Use a closure to capture the field_name
            def create_callback(fname):
                return lambda html: self.db.update_reading_field(
                    self.reading_id, fname, html
                ) if html is not None else None

            editor.get_html(create_callback(field_name))

    # --- END NEW ---

    def save_all(self):
        """Called by the dashboard to save all data on this tab."""
        if not self._is_loaded:
            # Prevent saving blanks during tab creation
            return
        self.save_details(show_message=False)
        self.save_current_outline_notes()
        # --- MODIFIED (Step 5.2): Save bottom tabs ---
        self.save_bottom_tabs_content()
        # --- END MODIFIED ---

    def save_details(self, show_message=True):
        """Saves the data from the 'Reading Details' form and notifies dashboard to rename the tab if needed."""
        if not self._is_loaded:
            # Avoid writing empty fields before load_data ran
            return

        details = {
            'title': self.edit_title.text(),
            'author': self.edit_author.text(),
            'nickname': self.edit_nickname.text(),
            'published': self.edit_published.text(),
            'pages': self.edit_pages.text(),
            'assignment': self.edit_assignment.text(),
            'level': self.combo_level.currentText(),
            'classification': self.edit_classification.text()
        }

        try:
            self.db.update_reading_details(self.reading_id, details)
            if show_message:
                QMessageBox.information(self, "Success", "Reading details saved.")
            # Tell dashboard to recompute tab/tree title
            self.readingTitleChanged.emit(self.reading_id, self)
        except Exception as e:
            if show_message:
                QMessageBox.critical(self, "Error", f"Could not save details: {e}")

    def save_current_outline_notes(self):
        """Saves the notes for the currently selected outline item."""
        if self.current_outline_id is None or self._block_outline_save or not self._is_loaded:
            return

        section_id = self.current_outline_id

        def save_callback(html):
            if html is not None:
                try:
                    self.db.update_outline_section_notes(section_id, html)
                    print(f"Save complete for outline section {section_id}")
                except Exception as e:
                    print(f"Error saving notes for outline section {section_id}: {e}")

        self.notes_editor.get_html(save_callback)

    # --- Outline Tree Functions ---

    def load_outline(self):
        """Reloads the outline tree from the database."""
        self.outline_tree.clear()
        try:
            # --- FIX: Use list[dict] from db ---
            root_items = self.db.get_reading_outline(self.reading_id, parent_id=None)
            for item_data in root_items:
                parent_widget = self.outline_tree
                self._add_outline_item(parent_widget, item_data)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load reading outline: {e}")

    def _add_outline_item(self, parent_widget, item_data: dict):
        """Recursive helper to add items to the outline tree."""
        item = QTreeWidgetItem(parent_widget, [item_data['section_title']])
        item.setData(0, Qt.ItemDataRole.UserRole, item_data['id'])

        # Recursively load children
        children_data = self.db.get_reading_outline(self.reading_id, parent_id=item_data['id'])
        for child_data in children_data:
            self._add_outline_item(item, child_data)

        item.setExpanded(True)

    # --- END FIX ---

    def on_outline_selection_changed(self, current, previous):
        """Handles switching the notes editor when the tree selection changes."""
        # Save previous notes before loading new
        if previous:
            prev_id = previous.data(0, Qt.ItemDataRole.UserRole)
            if prev_id is not None and self._is_loaded:
                self.notes_editor.get_html(
                    lambda html, pid=prev_id: self.db.update_outline_section_notes(pid,
                                                                                   html) if html is not None else None
                )

        if current:
            self.current_outline_id = current.data(0, Qt.ItemDataRole.UserRole)
            if self.current_outline_id:
                self._block_outline_save = True
                try:
                    notes_html = self.db.get_outline_section_notes(self.current_outline_id)
                    self.notes_editor.set_html(notes_html or "")
                    self.notes_stack.setCurrentWidget(self.notes_editor)

                    # --- BUG FIX: Add call to refresh formatting ---
                    # Use a timer to run the refresh *after* the UI has settled
                    # This cleans stale anchors every time notes are loaded.
                    QTimer.singleShot(50, self.refresh_anchor_formatting)
                    # --- END BUG FIX ---

                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Could not load notes: {e}")
                    self.notes_stack.setCurrentWidget(self.notes_placeholder)
                finally:
                    self._block_outline_save = False
            else:
                self.current_outline_id = None
                self.notes_stack.setCurrentWidget(self.notes_placeholder)
        else:
            self.current_outline_id = None
            self.notes_stack.setCurrentWidget(self.notes_placeholder)

    def show_outline_context_menu(self, position):
        """Shows the right-click menu for the outline tree."""
        menu = QMenu(self)
        item = self.outline_tree.itemAt(position)

        add_section_action = QAction("Add Section", self)
        add_section_action.triggered.connect(self.add_section)
        menu.addAction(add_section_action)

        if item:
            add_subsection_action = QAction("Add Subsection", self)
            add_subsection_action.triggered.connect(self.add_subsection)
            menu.addAction(add_subsection_action)

            menu.addSeparator()
            rename_action = QAction("Rename", self)
            rename_action.triggered.connect(self.rename_section)
            menu.addAction(rename_action)

            delete_action = QAction("Delete", self)
            delete_action.triggered.connect(self.delete_section)
            menu.addAction(delete_action)

        if ReorderDialog and self.outline_tree.topLevelItemCount() > 0:
            menu.addSeparator()
            reorder_action = QAction("Reorder...", self)
            reorder_action.triggered.connect(self.reorder_sections)
            menu.addAction(reorder_action)

        menu.exec(self.outline_tree.viewport().mapToGlobal(position))

    def add_section(self):
        """Adds a new root-level section."""
        text, ok = QInputDialog.getText(self, "Add Section", "Section Title:")
        if ok and text:
            try:
                self.db.add_outline_section(self.reading_id, text, parent_id=None)
                self.load_outline()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not add section: {e}")

    def add_subsection(self):
        """Adds a new subsection to the currently selected item."""
        item = self.outline_tree.currentItem()
        if not item:
            QMessageBox.information(self, "Add Subsection", "Please select a parent section first.")
            return

        parent_id = item.data(0, Qt.ItemDataRole.UserRole)
        text, ok = QInputDialog.getText(self, "Add Subsection", "Subsection Title:")
        if ok and text:
            try:
                self.db.add_outline_section(self.reading_id, text, parent_id=parent_id)
                self.load_outline()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not add subsection: {e}")

    def rename_section(self):
        """Renames the currently selected section."""
        item = self.outline_tree.currentItem()
        if not item:
            return

        section_id = item.data(0, Qt.ItemDataRole.UserRole)
        current_title = item.text(0)

        new_title, ok = QInputDialog.getText(self, "Rename Section", "New Title:", current_title)
        if ok and new_title and new_title != current_title:
            try:
                self.db.update_outline_section_title(section_id, new_title)
                self.load_outline()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not rename section: {e}")

    def delete_section(self):
        """Deletes the selected section and all its subsections."""
        item = self.outline_tree.currentItem()
        if not item:
            return

        section_id = item.data(0, Qt.ItemDataRole.UserRole)
        reply = QMessageBox.question(
            self, "Delete Section",
            f"Are you sure you want to delete '{item.text(0)}' and all its subsections?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.db.delete_outline_section(section_id)
                self.load_outline()
                self.on_outline_selection_changed(None, None)  # Clear editor
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not delete section: {e}")

    def reorder_sections(self):
        """Reorders the children of the selected item, or root items."""
        item = self.outline_tree.currentItem()
        parent_id = None

        if item:
            reply = QMessageBox.question(self, "Reorder",
                                         "Reorder top-level sections?\n\n(Click 'No' to reorder subsections of the selected item.)",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                         QMessageBox.StandardButton.Yes)
            if reply == QMessageBox.StandardButton.No:
                parent_id = item.data(0, Qt.ItemDataRole.UserRole)

        try:
            items_data = self.db.get_reading_outline(self.reading_id, parent_id)
            if not items_data:
                QMessageBox.information(self, "Reorder", "No items to reorder in this section.")
                return

            items_to_reorder = [(i['section_title'], i['id']) for i in items_data]
            dialog = ReorderDialog(items_to_reorder, self)

            if dialog.exec() == QDialog.DialogCode.Accepted:
                ordered_ids = dialog.ordered_db_ids
                self.db.update_outline_section_order(ordered_ids)
                self.load_outline()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not reorder sections: {e}")

    def open_page_citation_dialog(self):
        """Opens the simple page number citation dialog."""
        if not PageNumberDialog:
            QMessageBox.critical(self, "Error", "Page Number Dialog could not be loaded.")
            return

        dialog = PageNumberDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.page_text:
            self.notes_editor.editor.insertPlainText(f" {dialog.page_text} ")
            self.notes_editor.focus_editor()

    # --- NEW: Public Slots ---
    @Slot(int)
    def set_outline_selection(self, outline_id: int):
        """
        Finds and selects an item in the outline tree.
        Used by the Synthesis tab to "jump to" an anchor.
        """
        if outline_id == 0:  # 0 means "reading-level"
            self.outline_tree.clearSelection()
            self.on_outline_selection_changed(None, None)
            return

        it = QTreeWidgetItemIterator(self.outline_tree)
        while it.value():
            item = it.value()
            if item.data(0, Qt.ItemDataRole.UserRole) == outline_id:
                self.outline_tree.setCurrentItem(item)
                self.outline_tree.scrollToItem(item, QAbstractItemView.ScrollHint.PositionAtCenter)
                self.notes_editor.focus_editor()
                return
            it += 1

    @Slot()
    def refresh_anchor_formatting(self):
        """
        Iterates through the document and removes highlighting from
        any anchors that no longer exist in the database.
        """
        # --- BUG FIX: Only run if the editor is visible ---
        if not self._is_loaded or self.notes_stack.currentWidget() != self.notes_editor:
            return
        # --- END BUG FIX ---

        print(f"Reading {self.reading_id}: Refreshing anchor formatting...")
        doc = self.notes_editor.editor.document()
        cursor = QTextCursor(doc)
        cursor.setPosition(0)

        current_pos = 0
        while current_pos < doc.characterCount() - 1:
            cursor.setPosition(current_pos)
            cursor.movePosition(QTextCursor.MoveOperation.NextCharacter, QTextCursor.MoveMode.KeepAnchor, 1)
            fmt = cursor.charFormat()

            # Helper to safely convert QVariant to int
            anchor_id_qvar = fmt.property(AnchorIDProperty)
            anchor_id = None
            if anchor_id_qvar is not None:
                try:
                    if hasattr(anchor_id_qvar, 'toInt'):  # PySide6/PyQt6
                        val, ok = anchor_id_qvar.toInt()
                        if ok: anchor_id = val
                    else:  # Plain int
                        anchor_id = int(anchor_id_qvar)
                except Exception:
                    pass  # Not a valid anchor ID

            if anchor_id:
                # This text has an anchor ID. Check if it's still valid.
                anchor_exists = self.db.get_anchor_by_id(anchor_id)

                if not anchor_exists:
                    # Anchor was deleted. We need to find its bounds and clear it.
                    start_pos = cursor.position() - 1

                    # Move forward to find the end
                    while not cursor.atEnd():
                        cursor.movePosition(QTextCursor.MoveOperation.NextCharacter, QTextCursor.MoveMode.KeepAnchor)
                        fmt = cursor.charFormat()

                        next_anchor_id_qvar = fmt.property(AnchorIDProperty)
                        next_anchor_id = None
                        if next_anchor_id_qvar is not None:
                            try:
                                if hasattr(next_anchor_id_qvar, 'toInt'):
                                    val, ok = next_anchor_id_qvar.toInt()
                                    if ok: next_anchor_id = val
                                else:
                                    next_anchor_id = int(next_anchor_id_qvar)
                            except Exception:
                                pass

                        if next_anchor_id != anchor_id:
                            cursor.movePosition(QTextCursor.MoveOperation.PreviousCharacter,
                                                QTextCursor.MoveMode.KeepAnchor)
                            break

                    # 'cursor' now selects the entire stale anchor

                    # --- BUG FIX 2 (FONT FIX): Preserve existing font formatting ---
                    # Get the existing format of the selection
                    existing_fmt = cursor.charFormat()

                    # Clear only the anchor-related properties
                    existing_fmt.clearBackground()
                    existing_fmt.clearProperty(AnchorIDProperty)
                    existing_fmt.clearProperty(AnchorTagIDProperty)
                    existing_fmt.clearProperty(AnchorTagNameProperty)
                    existing_fmt.clearProperty(AnchorCommentProperty)
                    existing_fmt.clearProperty(AnchorUUIDProperty)  # <-- Also clear this
                    existing_fmt.setToolTip("")

                    # Re-apply the modified format, preserving font, size, etc.
                    cursor.setCharFormat(existing_fmt)
                    # --- END BUG FIX 2 ---

                    current_pos = cursor.position()
                else:
                    # Anchor still exists, just move on
                    current_pos += 1
            else:
                # Not an anchor, move on
                current_pos += 1

        # After loop, save the cleaned-up notes
        self.save_current_outline_notes()

    # --- END NEW ---

    # --- NEW: Synthesis Anchor Handlers ---

    @Slot(str)
    def _on_create_anchor(self, selected_text):
        """Handles the 'Create Synthesis Anchor' signal from the editor."""
        if not CreateAnchorDialog:
            QMessageBox.critical(self, "Error", "CreateAnchorDialog not loaded.")
            return

        # --- MODIFIED (Step 2.1): Get ALL tags ---
        tags = self.db.get_all_tags()
        # --- END MODIFIED ---

        dialog = CreateAnchorDialog(selected_text, project_tags_list=tags, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            tag_name = dialog.get_tag_text()
            comment = dialog.get_comment()

            if not tag_name:
                QMessageBox.warning(self, "Tag Required", "An anchor must have a tag.")
                return

            try:
                # 1. Get or create the tag ID
                # --- MODIFIED (Step 2.2): Pass project_id to link the new tag ---
                tag_data = self.db.get_or_create_tag(tag_name, self.project_id)
                # --- END MODIFIED ---
                if not tag_data:
                    raise Exception(f"Could not get or create tag '{tag_name}'")

                tag_id = tag_data['id']

                # 2. Generate a unique ID for this specific anchor instance
                unique_doc_id = str(uuid.uuid4())

                # 3. Create the anchor in the DB
                anchor_id = self.db.create_anchor(
                    project_id=self.project_id,
                    reading_id=self.reading_id,
                    outline_id=self.current_outline_id,
                    tag_id=tag_id,  # <-- Pass the tag_id
                    selected_text=selected_text,
                    comment=comment,
                    unique_doc_id=unique_doc_id
                )

                if not anchor_id:
                    raise Exception("Failed to create anchor in database.")

                # 4. Apply the format to the selected text in the editor
                self.notes_editor.apply_anchor_format(
                    anchor_id=anchor_id,
                    tag_id=tag_id,
                    tag_name=tag_name,
                    comment=comment,
                    unique_doc_id=unique_doc_id
                )

                # 5. Immediately save the notes
                self.save_current_outline_notes()

            except Exception as e:
                QMessageBox.critical(self, "Error Creating Anchor", f"{e}")

    @Slot(int)
    def _on_edit_anchor(self, anchor_id):
        """Handles the 'Edit Synthesis Anchor' signal."""
        try:
            # 1. Get current anchor data from DB
            current_data = self.db.get_anchor_details(anchor_id)
            if not current_data:
                QMessageBox.critical(self, "Error", "Could not find anchor data to edit.")
                return

            # --- MODIFIED (Step 2.1): Get ALL tags ---
            tags = self.db.get_all_tags()
            # --- END MODIFIED ---

            # 3. Open dialog
            dialog = CreateAnchorDialog(
                selected_text=current_data['selected_text'],
                project_tags_list=tags,
                current_data=current_data,
                parent=self
            )

            if dialog.exec() == QDialog.DialogCode.Accepted:
                new_tag_name = dialog.get_tag_text()
                new_comment = dialog.get_comment()

                if not new_tag_name:
                    QMessageBox.warning(self, "Tag Required", "An anchor must have a tag.")
                    return

                # 4. Get/Create new tag
                # --- MODIFIED (Step 2.2): Pass project_id to link the new tag ---
                tag_data = self.db.get_or_create_tag(new_tag_name, self.project_id)
                # --- END MODIFIED ---
                if not tag_data:
                    raise Exception(f"Could not get or create tag '{new_tag_name}'")

                new_tag_id = tag_data['id']

                # 5. Update in DB
                self.db.update_anchor(anchor_id, new_tag_id, new_comment)

                # 6. Find and update the format in the text editor
                self.notes_editor.find_and_update_anchor_format(
                    anchor_id=anchor_id,
                    tag_id=new_tag_id,
                    tag_name=new_tag_name,
                    comment=new_comment
                )

                # 7. Immediately save the notes
                self.save_current_outline_notes()

        except Exception as e:
            QMessageBox.critical(self, "Error Editing Anchor", f"{e}")

    @Slot(int)
    def _on_delete_anchor(self, anchor_id):
        """Handles the 'Delete Synthesis Anchor' signal."""
        reply = QMessageBox.question(
            self, "Delete Anchor",
            "Are you sure you want to delete this synthesis anchor?\n\nThis will remove it from the database and the text.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # 1. Delete from DB
                self.db.delete_anchor(anchor_id)

                # 2. Remove format from editor (user must have it selected)
                self.notes_editor.remove_anchor_format()

                # 3. Immediately save the notes
                self.save_current_outline_notes()

            except Exception as e:
                QMessageBox.critical(self, "Error Deleting Anchor", f"{e}")

    # --- END NEW ---