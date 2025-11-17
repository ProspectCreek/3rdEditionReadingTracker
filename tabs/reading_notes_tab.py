# prospectcreek/3rdeditionreadingtracker/tabs/reading_notes_tab.py
import sys
import uuid
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QLabel, QFrame,
    QTreeWidget, QTreeWidgetItem, QFormLayout, QLineEdit, QComboBox,
    QPushButton, QMenu, QStackedWidget, QInputDialog, QMessageBox, QDialog,
    QTabWidget, QMenuBar, QTextEdit, QApplication, QAbstractItemView,
    QTreeWidgetItemIterator
)
from PySide6.QtCore import Qt, Signal, QPoint, Slot, QTimer, QUrl
from PySide6.QtGui import (
    QAction, QTextCharFormat, QColor, QTextCursor, QTextListFormat, QFont,
    QDesktopServices
)

from tabs.rich_text_editor_tab import (
    RichTextEditorTab, AnchorIDProperty, AnchorTagNameProperty,
    AnchorTagIDProperty, AnchorCommentProperty, AnchorUUIDProperty
)

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

try:
    from tabs.leading_propositions_tab import LeadingPropositionsTab
except ImportError:
    print("Error: Could not import LeadingPropositionsTab")
    LeadingPropositionsTab = None

try:
    from tabs.unity_tab import UnityTab
except ImportError:
    print("Error: Could not import UnityTab")
    UnityTab = None

try:
    from tabs.parts_order_relation_tab import PartsOrderRelationTab
except ImportError:
    print("Error: Could not import PartsOrderRelationTab")
    PartsOrderRelationTab = None

try:
    from tabs.key_terms_tab import KeyTermsTab
except ImportError:
    print("Error: Could not import KeyTermsTab")
    KeyTermsTab = None

try:
    from tabs.theories_tab import TheoriesTab
except ImportError:
    print("Error: Could not import TheoriesTab")
    TheoriesTab = None

try:
    from tabs.arguments_tab import ArgumentsTab
except ImportError:
    print("Error: Could not import ArgumentsTab")
    ArgumentsTab = None

try:
    from tabs.elevator_abstract_tab import ElevatorAbstractTab
except ImportError:
    print("Error: Could not import ElevatorAbstractTab")
    ElevatorAbstractTab = None

try:
    from tabs.gaps_tab import GapsTab
except ImportError:
    print("Error: Could not import GapsTab")
    GapsTab = None

try:
    from tabs.personal_dialogue_tab import PersonalDialogueTab
except ImportError:
    print("Error: CouldL not import PersonalDialogueTab")
    PersonalDialogueTab = None

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

try:
    from dialogs.create_anchor_dialog import CreateAnchorDialog
except ImportError:
    print("Error: Could not import CreateAnchorDialog")
    CreateAnchorDialog = None


class ReadingNotesTab(QWidget):
    """
    This tab holds the complex layout for managing a single reading,
    including details, outline, and notes.
    """

    readingTitleChanged = Signal(int, object)  # (reading_id, self)
    openSynthesisTab = Signal(int)  # --- NEW: Signal to open synth tab ---

    def __init__(self, db, project_id: int, reading_id: int, parent=None):
        super().__init__(parent)
        self.db = db
        self.project_id = project_id
        self.reading_id = reading_id

        self.reading_details_row = None  # sqlite3.Row
        self.current_outline_id = None
        self._block_outline_save = False  # prevent save-on-switch loops
        self._is_loaded = False  # <<< guard to avoid saving blanks

        self.bottom_tabs_with_editors = []
        self._pending_anchor_focus = None

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
        self.outline_tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
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
        right_layout.setSpacing(0)

        self.reading_menu_bar = QMenuBar()
        right_layout.addWidget(self.reading_menu_bar)
        self._create_reading_menu(self.reading_menu_bar)

        # Vertical splitter for notes and bottom tabs
        self.right_splitter = QSplitter(Qt.Orientation.Vertical)
        right_layout.addWidget(self.right_splitter)

        # Top-Right Widget (The Notes Editor)
        top_right_widget = QWidget()
        top_right_layout = QVBoxLayout(top_right_widget)
        top_right_layout.setContentsMargins(0, 4, 0, 0)
        top_right_layout.setSpacing(4)

        self.notes_label = QLabel("Outline Item Notes")
        self.notes_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        top_right_layout.addWidget(self.notes_label)

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

        self.notes_editor.anchorActionTriggered.connect(self._on_create_anchor)
        self.notes_editor.anchorEditTriggered.connect(self._on_edit_anchor)
        self.notes_editor.anchorDeleteTriggered.connect(self._on_delete_anchor)

        # --- Connect click signal ---
        self.notes_editor.anchorClicked.connect(self._on_anchor_clicked)

        self.notes_stack.setCurrentWidget(self.notes_placeholder)

        # Add Citation button
        citation_btn_layout = QHBoxLayout()
        btn_add_citation = QPushButton("Add Citation (p.)")
        citation_btn_layout.addStretch()
        citation_btn_layout.addWidget(btn_add_citation)
        top_right_layout.addLayout(citation_btn_layout)

        # --- Bottom-Right Widget (New Tabbed Area) ---
        bottom_right_frame = QFrame()
        bottom_right_frame.setFrameShape(QFrame.Shape.StyledPanel)
        bottom_right_layout = QVBoxLayout(bottom_right_frame)
        bottom_right_layout.setContentsMargins(6, 6, 6, 6)

        self.bottom_right_tabs = QTabWidget()
        bottom_right_layout.addWidget(self.bottom_right_tabs)

        self.right_splitter.addWidget(top_right_widget)
        self.right_splitter.addWidget(bottom_right_frame)

        self.right_splitter.setStretchFactor(0, 1)
        self.right_splitter.setStretchFactor(1, 1)

        self._add_bottom_tabs()

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

        QTimer.singleShot(0, self._enforce_right_split)

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

        details_btn_layout = QHBoxLayout()
        self.btn_reading_rules = QPushButton("Reading Rules")
        self.btn_save_details = QPushButton("Save Details")
        details_btn_layout.addStretch()
        details_btn_layout.addWidget(self.btn_reading_rules)
        details_btn_layout.addWidget(self.btn_save_details)
        parent_layout.addLayout(details_btn_layout)

    def _add_bottom_tabs(self):
        """Creates and adds all the tabs for the bottom-right panel."""

        self.bottom_tabs_with_editors.clear()

        if DrivingQuestionTab:
            self.driving_question_tab = DrivingQuestionTab(self.db, self.reading_id)
            self.bottom_right_tabs.addTab(self.driving_question_tab, "Driving Question")
        else:
            self.bottom_right_tabs.addTab(QLabel("Driving Question (Failed to load)"), "Driving Question")

        def create_editor_tab(title, instructions, field_name):
            widget = QWidget()
            layout = QVBoxLayout(widget)
            layout.setContentsMargins(4, 4, 4, 4)
            layout.setSpacing(4)
            if instructions:
                layout.addWidget(QLabel(instructions))

            editor = RichTextEditorTab(title)
            self.bottom_tabs_with_editors.append((field_name, editor))
            layout.addWidget(editor)
            self.bottom_right_tabs.addTab(widget, title)

        if LeadingPropositionsTab:
            self.leading_propositions_tab = LeadingPropositionsTab(
                self.db, self.project_id, self.reading_id
            )
            self.bottom_right_tabs.addTab(self.leading_propositions_tab, "Leading Propositions")
        else:
            create_editor_tab("Leading Propositions", "Instructions for Leading Propositions go here.",
                              "propositions_html")

        if UnityTab:
            self.unity_tab = UnityTab(self.db, self.project_id, self.reading_id)
            self.bottom_right_tabs.addTab(self.unity_tab, "Unity")
        else:
            create_editor_tab("Unity", "Instructions for Unity go here.", "unity_html")

        if ElevatorAbstractTab:
            self.elevator_abstract_tab = ElevatorAbstractTab()
            self.bottom_right_tabs.addTab(self.elevator_abstract_tab, "Elevator Abstract")
            self.bottom_tabs_with_editors.append(("personal_dialogue_html", self.elevator_abstract_tab.editor))
        else:
            create_editor_tab("Elevator Abstract", "Instructions for Elevator Abstract go here.",
                              "personal_dialogue_html")

        if PartsOrderRelationTab:
            self.parts_order_relation_tab = PartsOrderRelationTab(
                self.db, self.project_id, self.reading_id
            )
            self.bottom_right_tabs.addTab(self.parts_order_relation_tab, "Parts: Order and Relation")
        else:
            create_editor_tab("Parts: Order and Relation", "Instructions for Parts: Order and Relation go here.",
                              "personal_dialogue_html")

        if KeyTermsTab:
            self.key_terms_tab = KeyTermsTab(self.db, self.project_id, self.reading_id)
            self.bottom_right_tabs.addTab(self.key_terms_tab, "Key Terms")
        else:
            create_editor_tab("Key Terms", "Instructions for Key Terms go here.", "key_terms_html")

        if ArgumentsTab:
            self.arguments_tab = ArgumentsTab(self.db, self.project_id, self.reading_id)
            self.bottom_right_tabs.addTab(self.arguments_tab, "Arguments")
        else:
            create_editor_tab("Arguments", "Instructions for Arguments go here.", "arguments_html")

        if GapsTab:
            self.gaps_tab = GapsTab()
            self.bottom_right_tabs.addTab(self.gaps_tab, "Gaps")
            self.bottom_tabs_with_editors.append(("gaps_html", self.gaps_tab.editor))
        else:
            create_editor_tab("Gaps", "Instructions for Gaps go here.", "gaps_html")

        if TheoriesTab:
            self.theories_tab = TheoriesTab(self.db, self.project_id, self.reading_id)
            self.bottom_right_tabs.addTab(self.theories_tab, "Theories")
        else:
            create_editor_tab("Theories", "Instructions for Theories go here.", "theories_html")

        if PersonalDialogueTab:
            self.personal_dialogue_tab = PersonalDialogueTab()
            self.bottom_right_tabs.addTab(self.personal_dialogue_tab, "Personal Dialogue")
            self.bottom_tabs_with_editors.append(("personal_dialogue_html", self.personal_dialogue_tab.editor))
        else:
            create_editor_tab("Personal Dialogue", "Instructions for Personal Dialogue go here.",
                              "personal_dialogue_html")

        if AttachmentsTab:
            self.attachments_tab = AttachmentsTab(self.db, self.reading_id)
            self.bottom_right_tabs.addTab(self.attachments_tab, "Attachments")
        else:
            self.bottom_right_tabs.addTab(QLabel("Attachments (Failed to load)"), "Attachments")

        if TimersTab:
            self.timers_tab = TimersTab()
            self.bottom_right_tabs.addTab(self.timers_tab, "Timers")
        else:
            self.bottom_right_tabs.addTab(QLabel("Timers (Failed to load)"), "Timers")

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

            self.load_bottom_tabs_content()

        except Exception as e:
            QMessageBox.critical(self, "Error Loading Reading", f"An error occurred: {e}")
            import traceback;
            traceback.print_exc()

    def load_bottom_tabs_content(self):
        """Loads data into the bottom-right tabs."""
        if not self.reading_details_row:
            return

        if DrivingQuestionTab and hasattr(self, 'driving_question_tab'):
            self.driving_question_tab.load_questions()
        if LeadingPropositionsTab and hasattr(self, 'leading_propositions_tab'):
            self.leading_propositions_tab.load_propositions()
        if UnityTab and hasattr(self, 'unity_tab'):
            self.unity_tab.load_data()
        if PartsOrderRelationTab and hasattr(self, 'parts_order_relation_tab'):
            self.parts_order_relation_tab.load_data()
        if KeyTermsTab and hasattr(self, 'key_terms_tab'):
            self.key_terms_tab.load_key_terms()
        if TheoriesTab and hasattr(self, 'theories_tab'):
            self.theories_tab.load_theories()
        if ArgumentsTab and hasattr(self, 'arguments_tab'):
            self.arguments_tab.load_arguments()
        if AttachmentsTab and hasattr(self, 'attachments_tab'):
            self.attachments_tab.load_attachments()

        for field_name, editor in self.bottom_tabs_with_editors:
            if field_name == 'propositions_html' and LeadingPropositionsTab and hasattr(self,
                                                                                       'leading_propositions_tab'):
                continue
            if field_name == 'unity_html' and UnityTab and hasattr(self, 'unity_tab'):
                continue
            if field_name == 'key_terms_html' and KeyTermsTab and hasattr(self, 'key_terms_tab'):
                continue
            if field_name == 'theories_html' and TheoriesTab and hasattr(self, 'theories_tab'):
                continue
            if field_name == 'arguments_html' and ArgumentsTab and hasattr(self, 'arguments_tab'):
                continue

            if field_name == 'personal_dialogue_html' and PartsOrderRelationTab and hasattr(self,
                                                                                           'parts_order_relation_tab') and editor.editor_title == "Parts: Order and Relation":
                continue

            html = self._get_detail(field_name, default="")
            editor.set_html(html)

    def save_bottom_tabs_content(self):
        """Saves data from the bottom-right tabs."""
        if not self._is_loaded:
            return

        if UnityTab and hasattr(self, 'unity_tab'):
            self.unity_tab.save_data()
        if PartsOrderRelationTab and hasattr(self, 'parts_order_relation_tab'):
            self.parts_order_relation_tab.save_data()

        for field_name, editor in self.bottom_tabs_with_editors:
            if field_name == 'propositions_html' and LeadingPropositionsTab and hasattr(self,
                                                                                       'leading_propositions_tab'):
                continue
            if field_name == 'unity_html' and UnityTab and hasattr(self, 'unity_tab'):
                continue
            if field_name == 'key_terms_html' and KeyTermsTab and hasattr(self, 'key_terms_tab'):
                continue
            if field_name == 'theories_html' and TheoriesTab and hasattr(self, 'theories_tab'):
                continue
            if field_name == 'arguments_html' and ArgumentsTab and hasattr(self, 'arguments_tab'):
                continue

            if field_name == 'personal_dialogue_html' and PartsOrderRelationTab and hasattr(self,
                                                                                           'parts_order_relation_tab') and editor.editor_title == "Parts: Order and Relation":
                continue

            def create_callback(fname):
                return lambda html: self.db.update_reading_field(
                    self.reading_id, fname, html
                ) if html is not None else None

            editor.get_html(create_callback(field_name))

    def save_all(self):
        """Called by the dashboard to save all data on this tab."""
        if not self._is_loaded:
            return
        self.save_details(show_message=False)
        self.save_current_outline_notes()
        self.save_bottom_tabs_content()

    def save_details(self, show_message=True):
        """Saves the data from the 'Reading Details' form and notifies dashboard to rename the tab if needed."""
        if not self._is_loaded:
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
                except Exception as e:
                    print(f"DEBUG: Error saving notes for outline section {section_id}: {e}")

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

    def _add_outline_item(self, parent_widget, item_data: dict):
        """Recursive helper to add items to the outline tree."""
        item = QTreeWidgetItem(parent_widget, [item_data['section_title']])
        item.setData(0, Qt.ItemDataRole.UserRole, item_data['id'])

        children_data = self.db.get_reading_outline(self.reading_id, parent_id=item_data['id'])
        for child_data in children_data:
            self._add_outline_item(item, child_data)

        item.setExpanded(True)

    # --- NEW HELPER FUNCTION ---
    def _find_and_select_outline_item(self, section_id):
        """Finds and selects an item in the outline tree by its ID."""
        if section_id is None:
            return

        it = QTreeWidgetItemIterator(self.outline_tree)
        while it.value():
            item = it.value()
            if item.data(0, Qt.ItemDataRole.UserRole) == section_id:
                self.outline_tree.setCurrentItem(item)
                # Ensure it's visible
                self.outline_tree.scrollToItem(item, QAbstractItemView.ScrollHint.PositionAtCenter)
                break
            it += 1

    # --- END HELPER ---

    def on_outline_selection_changed(self, current, previous):
        """Handles switching the notes editor when the tree selection changes."""
        # --- DIAGNOSTIC PRINT ---
        print(
            f"      ReadingTab.on_outline_selection_changed: Triggered. Current focus: {QApplication.instance().focusWidget()}")
        # --- END DIAGNOSTIC ---

        if previous:
            prev_id = previous.data(0, Qt.ItemDataRole.UserRole)
            if prev_id is not None and self._is_loaded:
                self.notes_editor.get_html(
                    lambda html, pid=prev_id: self.db.update_outline_section_notes(pid,
                                                                                   html) if html is not None else None
                )

        if current:
            # --- THIS IS THE NEW LOGIC ---
            item_text = current.text(0)
            self.notes_label.setText(f"Outline Item Notes: {item_text}")
            # --- END NEW LOGIC ---

            self.current_outline_id = current.data(0, Qt.ItemDataRole.UserRole)
            if self.current_outline_id:
                self._block_outline_save = True
                try:
                    notes_html = self.db.get_outline_section_notes(self.current_outline_id)
                    self.notes_editor.set_html(notes_html or "")
                    self.notes_stack.setCurrentWidget(self.notes_editor)
                    QTimer.singleShot(50, self.refresh_anchor_formatting)
                    self._queue_pending_anchor_focus()
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Could not load notes: {e}")
                    self.notes_stack.setCurrentWidget(self.notes_placeholder)
                finally:
                    self._block_outline_save = False
            else:
                self.current_outline_id = None
                self.notes_stack.setCurrentWidget(self.notes_placeholder)
                # --- ADD RESET HERE TOO ---
                self.notes_label.setText("Outline Item Notes")
                self._pending_anchor_focus = None
        else:
            # --- THIS IS THE NEW LOGIC ---
            self.notes_label.setText("Outline Item Notes")
            # --- END NEW LOGIC ---

            self.current_outline_id = None
            self.notes_stack.setCurrentWidget(self.notes_placeholder)
            self._pending_anchor_focus = None

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
                # --- MODIFICATION: Capture new ID ---
                new_id = self.db.add_outline_section(self.reading_id, text, parent_id=None)
                self.load_outline()
                # --- MODIFICATION: Select new item ---
                self._find_and_select_outline_item(new_id)
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
                # --- MODIFICATION: Capture new ID ---
                new_id = self.db.add_outline_section(self.reading_id, text, parent_id=parent_id)
                self.load_outline()
                # --- MODIFICATION: Select new item ---
                self._find_and_select_outline_item(new_id)
                # --- END MODIFICATION ---
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not add subsection: {e}")

    def rename_section(self):
        """Renames the currently selected section."""
        item = self.outline_tree.currentItem()
        if not item:
            return

        section_id = item.data(0, Qt.ItemDataRole.UserRole)
        current_title = item.text(0)

        new_title, ok = QInputDialog.getText(self, "Rename Section", "New Title:", text=current_title)
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

    @Slot()
    def _enforce_right_split(self):
        """Forces the right-hand splitter to be 50/50."""
        try:
            total_h = max(2, self.right_splitter.size().height())
            self.right_splitter.setSizes([total_h // 2, total_h - total_h // 2])
        except Exception as e:
            print(f"Warning: Could not enforce right split: {e}")

    # ##################################################################
    # #
    # #                      --- MODIFICATION START (DIAGNOSTICS) ---
    # #
    # ##################################################################
    @Slot(int, int, int, str)
    def set_outline_selection(self, anchor_id: int, outline_id: int, item_link_id: int, item_type: str = ''):
        """
        Finds and selects an item in the outline tree.
        If item_link_id is provided, it tries to find and select
        the item in the corresponding bottom tab.
        """
        print(f"    ReadingTab.set_outline_selection: START (anchor={anchor_id}). Current focus: {QApplication.instance().focusWidget()}")

        self._pending_anchor_focus = anchor_id if (anchor_id and outline_id) else None

        # --- Part 1: Select Outline Item ---
        if outline_id == 0:
            self._pending_anchor_focus = None
            self.outline_tree.clearSelection()
            # This call is fine, it will clear the notes editor
            self.on_outline_selection_changed(None, None)
        else:
            it = QTreeWidgetItemIterator(self.outline_tree)
            while it.value():
                item = it.value()
                if item.data(0, Qt.ItemDataRole.UserRole) == outline_id:
                    # This triggers on_outline_selection_changed, loading the notes
                    self.outline_tree.setCurrentItem(item)
                    self.outline_tree.scrollToItem(item, QAbstractItemView.ScrollHint.PositionAtCenter)
                    break
                it += 1

        # --- Part 2: Select Bottom Tab Item ---
        if item_link_id > 0:
            self._pending_anchor_focus = None
            tabs_to_check = [
                # (Tab object, Tab index)
                (getattr(self, 'driving_question_tab', None),
                 self.bottom_right_tabs.indexOf(getattr(self, 'driving_question_tab', None))),
                (getattr(self, 'leading_propositions_tab', None),
                 self.bottom_right_tabs.indexOf(getattr(self, 'leading_propositions_tab', None))),
                (getattr(self, 'key_terms_tab', None),
                 self.bottom_right_tabs.indexOf(getattr(self, 'key_terms_tab', None))),
                (getattr(self, 'arguments_tab', None),
                 self.bottom_right_tabs.indexOf(getattr(self, 'arguments_tab', None))),
                (getattr(self, 'theories_tab', None),
                 self.bottom_right_tabs.indexOf(getattr(self, 'theories_tab', None))),
            ]

            for tab, tab_index in tabs_to_check:
                if tab and tab_index != -1 and hasattr(tab, 'tree_widget'):
                    tree = tab.tree_widget
                    it = QTreeWidgetItemIterator(tree)
                    while it.value():
                        item = it.value()
                        if item.data(0, Qt.ItemDataRole.UserRole) == item_link_id:
                            # 1. Switch the bottom tab
                            self.bottom_right_tabs.setCurrentIndex(tab_index)

                            # 2. Select the item in that tab's tree
                            tree.setCurrentItem(item)
                            tree.scrollToItem(item, QAbstractItemView.ScrollHint.PositionAtCenter)
                            print(
                                f"    ReadingTab.set_outline_selection: Set item in BOTTOM tab. Focus is now: {QApplication.instance().focusWidget()}")

                            # --- FIX: Re-introduce 0ms timer to set focus ---
                            # This queues the focus change to happen *after*
                            # all event processing for the tab switch is complete.
                            print(f"    ReadingTab.set_outline_selection: Queuing 0ms timer to focus outline_tree...")
                            QTimer.singleShot(0, lambda: (
                                print(
                                    f"    ReadingTab.set_outline_selection: 0ms timer FIRED. Setting focus to outline_tree."),
                                self.outline_tree.setFocus(),
                                print(
                                    f"    ReadingTab.set_outline_selection: FINAL focus is: {QApplication.instance().focusWidget()}")
                            ))
                            # --- END FIX ---
                            return  # We are done.
                        it += 1

        # --- Part 3: Fallback Focus ---
        # If we only selected an outline item (no item_link_id),
        # or if the item_link_id wasn't found.
        if outline_id != 0:
            # --- FIX: Re-introduce 0ms timer to set focus ---
            print(f"    ReadingTab.set_outline_selection: (Fallback) Queuing 0ms timer to focus outline_tree...")
            QTimer.singleShot(0, lambda: (
                print(
                    f"    ReadingTab.set_outline_selection: (Fallback) 0ms timer FIRED. Setting focus to outline_tree."),
                self.outline_tree.setFocus(),
                print(
                    f"    ReadingTab.set_outline_selection: (Fallback) FINAL focus is: {QApplication.instance().focusWidget()}")
            ))
            # --- END FIX ---

    def _queue_pending_anchor_focus(self):
        """Ensures the requested text anchor is highlighted once notes load."""
        if not self._pending_anchor_focus or not hasattr(self, 'notes_editor'):
            return

        anchor_id = self._pending_anchor_focus
        self._pending_anchor_focus = None

        def _focus_anchor():
            if hasattr(self.notes_editor, 'focus_anchor_by_id'):
                success = self.notes_editor.focus_anchor_by_id(anchor_id)
                print(
                    f"    ReadingTab.set_outline_selection: focus_anchor_by_id({anchor_id}) -> {success}."
                )

        QTimer.singleShot(0, _focus_anchor)

    # ##################################################################
    # #
    # #                      --- MODIFICATION END ---
    # #
    # ##################################################################

    @Slot()
    def refresh_anchor_formatting(self):
        """
        Iterates through the document and removes highlighting/links from
        any anchors that no longer exist in the database, preserving
        other formatting.
        """
        if not self._is_loaded or self.notes_stack.currentWidget() != self.notes_editor:
            return

        doc = self.notes_editor.editor.document()
        cursor = QTextCursor(doc)
        cursor.setPosition(0)

        current_pos = 0
        while current_pos < doc.characterCount() - 1:
            cursor.setPosition(current_pos)
            cursor.movePosition(QTextCursor.MoveOperation.NextCharacter, QTextCursor.MoveMode.KeepAnchor, 1)
            fmt = cursor.charFormat()

            # --- MODIFIED: Use new helper ---
            anchor_id = self.notes_editor._get_anchor_id_from_format(fmt)
            # --- END MODIFIED ---

            if anchor_id:
                # This character is part of an anchor. Check if it still exists.
                anchor_exists = self.db.get_anchor_by_id(anchor_id)

                if not anchor_exists:
                    # This anchor is orphaned. Find its full extent.
                    start_pos = cursor.position() - 1
                    while not cursor.atEnd():
                        cursor.movePosition(QTextCursor.MoveOperation.NextCharacter, QTextCursor.MoveMode.KeepAnchor)
                        fmt = cursor.charFormat()

                        # --- MODIFIED: Use new helper ---
                        next_anchor_id = self.notes_editor._get_anchor_id_from_format(fmt)
                        # --- END MODIFIED ---

                        if next_anchor_id != anchor_id:
                            cursor.movePosition(QTextCursor.MoveOperation.PreviousCharacter,
                                                QTextCursor.MoveMode.KeepAnchor)
                            break

                    # Now 'cursor' holds the selection for the entire orphaned anchor

                    self.notes_editor.editor.setTextCursor(cursor)
                    self.notes_editor.remove_anchor_format()

                    # Update our position to after the cleared block
                    current_pos = cursor.position()
                else:
                    # Anchor exists, just move to the next character
                    current_pos += 1
            else:
                # Not an anchor, just move to the next character
                current_pos += 1

        # Save the notes now that the formatting is clean
        self.save_current_outline_notes()

    @Slot(str)
    def _on_create_anchor(self, selected_text):
        """Handles the 'Create Synthesis Anchor' signal from the editor."""
        if not CreateAnchorDialog:
            QMessageBox.critical(self, "Error", "CreateAnchorDialog not loaded.")
            return

        tags = self.db.get_all_tags()

        dialog = CreateAnchorDialog(selected_text, project_tags_list=tags, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            tag_name = dialog.get_tag_text()
            comment = dialog.get_comment()

            if not tag_name:
                QMessageBox.warning(self, "Tag Required", "An anchor must have a tag.")
                return

            try:
                tag_data = self.db.get_or_create_tag(tag_name, self.project_id)
                if not tag_data:
                    raise Exception(f"Could not get or create tag '{tag_name}'")
                tag_id = tag_data['id']
                unique_doc_id = str(uuid.uuid4())

                anchor_id = self.db.create_anchor(
                    project_id=self.project_id,
                    reading_id=self.reading_id,
                    outline_id=self.current_outline_id,
                    tag_id=tag_id,
                    selected_text=selected_text,
                    comment=comment,
                    unique_doc_id=unique_doc_id,
                    item_link_id=None
                )

                if not anchor_id:
                    raise Exception("Failed to create anchor in database.")

                self.notes_editor.apply_anchor_format(
                    anchor_id=anchor_id,
                    tag_id=tag_id,
                    tag_name=tag_name,
                    comment=comment,
                    unique_doc_id=unique_doc_id
                )
                self.save_current_outline_notes()
            except Exception as e:
                QMessageBox.critical(self, "Error Creating Anchor", f"{e}")

    @Slot(int)
    def _on_edit_anchor(self, anchor_id):
        """Handles the 'Edit Synthesis Anchor' signal."""
        try:
            current_data = self.db.get_anchor_details(anchor_id)
            if not current_data:
                QMessageBox.critical(self, "Error", "Could not find anchor data to edit.")
                return

            tags = self.db.get_all_tags()
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

                tag_data = self.db.get_or_create_tag(new_tag_name, self.project_id)
                if not tag_data:
                    raise Exception(f"Could not get or create tag '{new_tag_name}'")
                new_tag_id = tag_data['id']

                update_data = {
                    "comment": new_comment,
                    "tags": [new_tag_id]  # update_anchor expects a list of tag IDs
                }
                self.db.update_anchor(anchor_id, update_data)

                self.notes_editor.find_and_update_anchor_format(
                    anchor_id=anchor_id,
                    tag_id=new_tag_id,
                    tag_name=new_tag_name,
                    comment=new_comment
                )
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
                self.db.delete_anchor(anchor_id)

                # [FIX] Call the new function that finds, selects, and removes format
                self.notes_editor.find_and_remove_anchor_format(anchor_id)

                self.save_current_outline_notes()
            except Exception as e:
                QMessageBox.critical(self, "Error Deleting Anchor", f"{e}")

    @Slot(QUrl)
    def _on_anchor_clicked(self, url):
        """Handles when a user clicks on a synthesis anchor link."""

        # [FIX] Use the URL scheme to check for our custom protocol
        if url.scheme() == "anchor":
            try:
                # [FIX] Get the ID from the path, which is safer than splitting
                anchor_id_str = url.path()

                # [FIX] This int() conversion is now protected by the try/except
                # It will fail on "0.0.0.22" and go to the ValueError block
                anchor_id = int(anchor_id_str)

                # We need the tag_id to switch tabs.
                details = self.db.get_anchor_details(anchor_id)
                if details and details.get('tag_id'):
                    tag_id = details['tag_id']
                    print(f"DEBUG: Anchor {anchor_id} clicked, emitting openSynthesisTab with tag_id {tag_id}")
                    self.openSynthesisTab.emit(tag_id)
                else:
                    print(f"DEBUG: Could not find tag_id for anchor {anchor_id}")

            except ValueError:
                # This catches the "invalid literal for int()" error
                print(f"DEBUG: Clicked anchor link with invalid ID: {url.toString()}")
            except Exception as e:
                # Catch any other unexpected errors
                print(f"DEBUG: Error in _on_anchor_clicked: {e}")

        # [FIX] Check for standard web links using their schemes
        elif url.scheme() in ("http", "https"):
            QDesktopServices.openUrl(url)

    def _create_reading_menu(self, menu_bar: QMenuBar):
        settings_menu = menu_bar.addMenu("Reading Settings")
        edit_instr_action = QAction("Edit Tab Instructions...", self)
        edit_instr_action.setEnabled(False)  # Not implemented yet
        settings_menu.addAction(edit_instr_action)