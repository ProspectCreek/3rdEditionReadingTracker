# tabs/reading_notes_tab.py
import sys
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QLabel, QFrame,
    QTreeWidget, QTreeWidgetItem, QFormLayout, QLineEdit, QComboBox,
    QPushButton, QMenu, QStackedWidget, QInputDialog, QMessageBox, QDialog,
    QTabWidget, QTextEdit, QMenuBar
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction

from tabs.rich_text_editor_tab import RichTextEditorTab

# --- Import New Tabs ---
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
try:
    from tabs.driving_question_tab import DrivingQuestionTab
except ImportError:
    print("Error: Could not import DrivingQuestionTab")
    DrivingQuestionTab = None
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


class ReadingNotesTab(QWidget):
    """
    This tab holds the complex layout for managing a single reading,
    including details, outline, and notes.
    """

    # NEW: let dashboard know to rename tab/tree when details saved
    readingTitleChanged = Signal(int, object)  # (reading_id, self)

    def __init__(self, db, reading_id: int, parent=None):
        super().__init__(parent)
        self.db = db
        self.reading_id = reading_id
        self.reading_details_row = None  # sqlite3.Row
        self.current_outline_id = None
        self._block_outline_save = False  # prevent save-on-switch loops
        self._is_loaded = False  # <<< guard to avoid saving blanks
        self.reading_sub_tabs = {}  # To store references to the bottom tabs

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
        right_layout.setSpacing(0)  # No spacing for menu bar

        # --- Menu Bar ---
        self.reading_menu_bar = QMenuBar()
        right_layout.addWidget(self.reading_menu_bar)
        self._create_reading_menu(self.reading_menu_bar)

        # Vertical splitter for notes and bottom tabs
        right_splitter = QSplitter(Qt.Orientation.Vertical)
        right_layout.addWidget(right_splitter)

        # Top-Right Widget (The Notes Editor)
        top_right_widget = QWidget()
        top_right_layout = QVBoxLayout(top_right_widget)
        top_right_layout.setContentsMargins(0, 4, 0, 0)  # Add padding on top
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

        self.notes_stack.setCurrentWidget(self.notes_placeholder)  # Start on placeholder

        # Add Citation button
        citation_btn_layout = QHBoxLayout()
        btn_add_citation = QPushButton("Add Citation (p.)")
        citation_btn_layout.addStretch()
        citation_btn_layout.addWidget(btn_add_citation)
        top_right_layout.addLayout(citation_btn_layout)

        # Bottom-Right Widget (Tabbed Editors)
        bottom_right_widget = QWidget()
        bottom_right_layout = QVBoxLayout(bottom_right_widget)
        bottom_right_layout.setContentsMargins(0, 4, 0, 0)
        bottom_right_layout.setSpacing(4)

        self.bottom_tab_widget = QTabWidget()
        bottom_right_layout.addWidget(self.bottom_tab_widget)
        self._create_bottom_tabs()

        right_splitter.addWidget(top_right_widget)
        right_splitter.addWidget(bottom_right_widget)
        # --- FIX: Set stretch factors to 1 for a 50/50 split ---
        right_splitter.setSizes([self.height() // 2, self.height() // 2])
        right_splitter.setStretchFactor(0, 1)
        right_splitter.setStretchFactor(1, 1)
        # --- END FIX ---

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

    def _create_reading_menu(self, menu_bar: QMenuBar):
        """Creates the menu bar for the reading tab."""
        settings_menu = menu_bar.addMenu("Settings")
        edit_instr_action = QAction("Edit Instructions", self)
        edit_instr_action.setEnabled(False)  # Disabled for now
        # edit_instr_action.triggered.connect(self.open_edit_instructions)
        settings_menu.addAction(edit_instr_action)

    def _create_bottom_tabs(self):
        """Creates and populates the bottom tab widget."""
        self.bottom_tab_widget.clear()
        self.reading_sub_tabs.clear()

        tabs_to_create = [
            ("driving_question", "Driving Question"),
            ("leading_propositions", "Leading Propositions"),
            ("unity", "Unity"),
            ("elevator_abstract", "Elevator Abstract"),
            ("parts_order_relation", "Parts: Order and Relation"),
            ("key_terms", "Key Terms"),
            ("arguments", "Arguments"),
            ("gaps", "Gaps"),
            ("theories", "Theories"),
            ("personal_dialogue", "Personal Dialogue"),
            ("attachments", "Attachments"),
            ("timers", "Timers")
        ]

        # --- FAKE DATA FOR NOW ---
        instructions = {
            "driving_question": "What is the author trying to find out?",
            "leading_propositions": "What are the key arguments or propositions?",
            "unity": "How does the author structure the argument?",
            "elevator_abstract": "A brief abstract of the work.",
            "parts_order_relation": "How do the parts of the work relate to each other?",
            "key_terms": "What are the key terms and their definitions?",
            "arguments": "Detailed breakdown of the author's arguments.",
            "gaps": "What gaps or unanswered questions remain?",
            "theories": "What theories or frameworks does the author use or propose?",
            "personal_dialogue": "Your thoughts, questions, and reactions.",
            "attachments": "Manage file attachments for this reading.",
            "timers": "Manage your focus and break timers."
        }
        # --- END FAKE DATA ---

        for key, title in tabs_to_create:
            tab_widget = QWidget()
            tab_layout = QVBoxLayout(tab_widget)
            tab_layout.setContentsMargins(6, 6, 6, 6)
            tab_layout.setSpacing(4)

            # Get instruction text from DB (or use default)
            instr_text = instructions.get(key, f"Instructions for {title}")

            instr_label = QLabel(instr_text)
            instr_label.setWordWrap(True)
            instr_label.setStyleSheet("font-style: italic; color: #555;")
            instr_label.setVisible(bool(instr_text))  # Hide if empty
            tab_layout.addWidget(instr_label)

            content_widget = None

            # --- NEW: Refactored Tab Loading ---
            if key == "driving_question":
                if DrivingQuestionTab:
                    content_widget = DrivingQuestionTab(self.db, self.reading_id)
                else:
                    content_widget = QLabel("Error: DrivingQuestionTab component could not be loaded.")
            elif key == "gaps":
                content_widget = RichTextEditorTab(title)
            elif key == "personal_dialogue":
                content_widget = RichTextEditorTab(title)
            elif key == "attachments":
                if AttachmentsTab:
                    content_widget = AttachmentsTab(self.db, self.reading_id)
                else:
                    content_widget = QLabel("Error: AttachmentsTab component could not be loaded.")
            elif key == "timers":
                if TimersTab:
                    content_widget = TimersTab()
                else:
                    content_widget = QLabel("Error: TimersTab component could not be loaded.")
            else:
                # Use QTextEdit as a simple placeholder for other tabs
                content_widget = QTextEdit()
                content_widget.setPlaceholderText(f"Notes for {title}...")
            # --- END NEW ---

            if content_widget:
                tab_layout.addWidget(content_widget, 1)

            tab_widget.setLayout(tab_layout)
            self.bottom_tab_widget.addTab(tab_widget, title)

            # Store references
            self.reading_sub_tabs[key] = {
                "tab": tab_widget,
                "editor": content_widget,
                "instruction_label": instr_label
            }

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

    # --- Data Loading and Saving ---

    def _get_detail(self, key, default=''):
        """Safely get a value from the sqlite3.Row by key."""
        try:
            if key in self.reading_details_row.keys():
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

            # Debug
            print(f"Loading details for reading {self.reading_id}: {dict(self.reading_details_row)}")

        except Exception as e:
            QMessageBox.critical(self, "Error Loading Reading", f"An error occurred: {e}")
            import traceback;
            traceback.print_exc()

    def save_all(self):
        """Called by the dashboard to save all data on this tab."""
        if not self._is_loaded:
            # Prevent saving blanks during tab creation
            return
        self.save_details(show_message=False)
        self.save_current_outline_notes()
        self.save_bottom_tabs_content()  # <-- NEW: Save bottom tabs

    def save_bottom_tabs_content(self):
        """Saves the content of all bottom tabs."""
        if not self._is_loaded: return

        print(f"Saving bottom tabs for reading {self.reading_id}...")
        # In a real implementation, you'd save each tab's content to its
        # own field in the database.
        # For now, this is a placeholder.

        for key, tab_data in self.reading_sub_tabs.items():
            editor = tab_data["editor"]
            if isinstance(editor, RichTextEditorTab):
                # This is an async call, so we define a callback
                def save_callback(html, editor_key=key):
                    if html is not None:
                        print(f"  -> Saving content for: {editor_key}")
                        # Example: self.db.update_reading_field(self.reading_id, editor_key, html)

                editor.get_html(save_callback)
            elif isinstance(editor, QTextEdit):
                # This is sync
                html = editor.toHtml()
                print(f"  -> Saving content for: {key}")
                # Example: self.db.update_reading_field(self.reading_id, key, html)
            # Add logic for other tab types (like AttachmentsTab) if they need saving
            elif isinstance(editor, (AttachmentsTab, TimersTab, DrivingQuestionTab)):
                # These tabs manage their own saving logic,
                # so we don't need to do anything here.
                pass

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
            root_items = self.db.get_reading_outline(self.reading_id, parent_id=None)
            for item_data in root_items:
                parent_widget = self.outline_tree
                self._add_outline_item(parent_widget, item_data)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load reading outline: {e}")

    def _add_outline_item(self, parent_widget, item_data):
        """Recursive helper to add items to the outline tree."""
        item = QTreeWidgetItem(parent_widget, [item_data['section_title']])
        item.setData(0, Qt.ItemDataRole.UserRole, item_data['id'])

        # Recursively load children
        children_data = self.db.get_reading_outline(self.reading_id, parent_id=item_data['id'])
        for child_data in children_data:
            self._add_outline_item(item, child_data)

        item.setExpanded(True)

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