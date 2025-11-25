import sys
import uuid
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QLabel, QFrame,
    QTreeWidget, QTreeWidgetItem, QFormLayout, QLineEdit, QComboBox,
    QPushButton, QMenu, QStackedWidget, QInputDialog, QMessageBox, QDialog,
    QTabWidget, QTextEdit, QApplication, QAbstractItemView,
    QTreeWidgetItemIterator, QListWidget, QListWidgetItem
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

# --- NEW: Import EditInstructionsDialog ---
try:
    from dialogs.edit_instructions_dialog import EditInstructionsDialog
except ImportError:
    print("Error: Could not import EditInstructionsDialog")
    EditInstructionsDialog = None
# --- END NEW ---

# --- NEW: Import Reading Rules Dialogs ---
try:
    from dialogs.view_reading_rules_dialog import ViewReadingRulesDialog
except ImportError:
    print("Error: Could not import ViewReadingRulesDialog")
    ViewReadingRulesDialog = None

# --- NEW: Default Reading Rules Text ---
DEFAULT_READING_RULES_HTML = """
<p><b>I. The First Stage of Analytical Reading: Rules for Finding What a Book Is About</b></p>
<ol>
    <li>Classify the book according to kind and subject matter.</li>
    <li>State what the whole book is about with the utmost brevity.</li>
    <li>Enumerate its major parts in their order and relation and outline these parts as you have outlined the whole.</li>
    <li>Define the problem or problems the author has tried to solve.</li>
</ol>
<p>&nbsp;</p>
<p><b>II. The Second Stage of Analytical Reading: Rules for Interpreting a Book's Contents</b></p>
<ol start="5">
    <li>Come to terms with the author by interpreting his key words.</li>
    <li>Grasp the author's leading propositions by dealing with his most important sentences.</li>
    <li>Know the author's arguments, by finding them in, or constructing them out of, sequences of sentences.</li>
    <li>Determine which of his problems the author has solved, and which he has not; and of the latter, decide which the author knew he had failed to solve.</li>
</ol>
<p>&nbsp;</p>
<p><b>The Third Stage of Analytical Reading: Rules for Criticizing a Book as a Communication of Knowledge</b></p>
<p><b>A. General Maxims of Intellectual Etiquette</b></p>
<ol start="9">
    <li>Do not begin criticism until you have completed your outline and your interpretation of the book. (Do not say you agree, disagree, or suspend judgment, until you can say "I understand.")</li>
    <li>Do not disagree disputatiously or contentiously.</li>
    <li>Demonstrate that you recognize the difference between knowledge and mere personal opinion by presenting good reasons for any critical judgment you make.</li>
</ol>
<p>&nbsp;</p>
<p><b>B. Special Criteria for Points of Criticism</b></p>
<ol start="12">
    <li>Show wherein the author is uninformed.</li>
    <li>Show wherein the author is misinformed.</li>
    <li>Show wherein the author is illogical.</li>
    <li>Show wherein the author's analysis or account is incomplete.</li>
</ol>
<p>&nbsp;</p>
<p><i>Note: Of these last four, the first three are criteria for disagreement. Failing in all of these, you must agree, at least in part, although you may suspend judgment on the whole, in the light of the last point.</i></p>
"""


# --- END NEW ---


class ReadingNotesTab(QWidget):
    """
    This tab holds the complex layout for managing a single reading,
    including details, outline, and notes.
    """

    readingTitleChanged = Signal(int, object)  # (reading_id, self)
    openSynthesisTab = Signal(int)  # --- NEW: Signal to open synth tab ---

    def __init__(self, db, project_id: int, reading_id: int, spell_checker_service=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.project_id = project_id
        self.spell_checker_service = spell_checker_service  # <-- STORE SERVICE
        self.reading_id = reading_id

        self.reading_details_row = None  # sqlite3.Row
        self.current_outline_id = None
        self._block_outline_save = False  # prevent save-on-switch loops
        self._is_loaded = False  # <<< guard to avoid saving blanks

        # --- CRITICAL FIX: Recursion Guard ---
        self._is_loading = False
        # -------------------------------------

        self.bottom_tabs_with_editors = []
        self._pending_anchor_focus = None
        self.instruction_labels = {}  # --- NEW: To store simple editor labels ---

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

        # --- NEW: Enable inline editing ---
        self.outline_tree.setEditTriggers(
            QTreeWidget.EditTrigger.DoubleClicked | QTreeWidget.EditTrigger.EditKeyPressed)
        self.outline_tree.itemChanged.connect(self.on_outline_item_changed)
        # ----------------------------------

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
        self.notes_editor = RichTextEditorTab("Outline Notes",
                                              spell_checker_service=self.spell_checker_service)  # <-- PASS SERVICE
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

        # --- MODIFIED: Use QTextEdit for Title ---
        self.edit_title = QTextEdit()
        self.edit_title.setMaximumHeight(60)
        self.edit_title.setTabChangesFocus(True)  # Allow tabbing out
        self.edit_title.setPlaceholderText("Title of the work...")
        # Force border style to match QLineEdit exactly
        self.edit_title.setStyleSheet("""
            QTextEdit {
                background-color: #FFFFFF;
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                padding: 6px;
                color: #111827;
            }
            QTextEdit:focus {
                border: 1px solid #2563EB;
            }
        """)
        # --- END MODIFIED ---

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

        # --- NEW: Connect Reading Rules Button ---
        if ViewReadingRulesDialog:
            self.btn_reading_rules.clicked.connect(self._show_reading_rules)
        else:
            self.btn_reading_rules.setEnabled(False)
        # --- END NEW ---

    def _add_bottom_tabs(self):
        """Creates and adds all the tabs for the bottom-right panel."""

        self.bottom_tabs_with_editors.clear()
        self.instruction_labels.clear()  # --- NEW ---

        if DrivingQuestionTab:
            self.driving_question_tab = DrivingQuestionTab(self.db, self.reading_id)
            self.bottom_right_tabs.addTab(self.driving_question_tab, "Driving Question")
        else:
            self.bottom_right_tabs.addTab(QLabel("Driving Question (Failed to load)"), "Driving Question")

        # --- MODIFIED: Fallback now includes storing the label ---
        def create_editor_tab(title, instructions, field_name, instr_key):
            # This is a fallback for if the main tab modules fail to import
            widget = QWidget()
            layout = QVBoxLayout(widget)
            layout.setContentsMargins(4, 4, 4, 4)
            layout.setSpacing(4)

            # Create a label, and store it for updates
            instr_label = QLabel(instructions)
            instr_label.setWordWrap(True)
            instr_label.setStyleSheet("font-style: italic; color: #555;")
            instr_label.setVisible(False)  # Start hidden
            layout.addWidget(instr_label)
            self.instruction_labels[instr_key] = instr_label  # Store the label

            editor = RichTextEditorTab(title, spell_checker_service=self.spell_checker_service)  # <-- PASS SERVICE
            self.bottom_tabs_with_editors.append((field_name, editor))
            layout.addWidget(editor)
            self.bottom_right_tabs.addTab(widget, title)

        # --- END MODIFIED ---

        if LeadingPropositionsTab:
            self.leading_propositions_tab = LeadingPropositionsTab(
                self.db, self.project_id, self.reading_id
            )
            self.bottom_right_tabs.addTab(self.leading_propositions_tab, "Leading Propositions")
        else:
            create_editor_tab("Leading Propositions", "Instructions for Leading Propositions go here.",
                              "propositions_html", "reading_lp_instr")

        if UnityTab:
            self.unity_tab = UnityTab(self.db, self.project_id, self.reading_id)
            self.bottom_right_tabs.addTab(self.unity_tab, "Unity")
        else:
            create_editor_tab("Unity", "Instructions for Unity go here.", "unity_html", "reading_unity_instr")

        if ElevatorAbstractTab:
            self.elevator_abstract_tab = ElevatorAbstractTab(
                spell_checker_service=self.spell_checker_service)  # <-- PASS SERVICE
            self.bottom_right_tabs.addTab(self.elevator_abstract_tab, "Elevator Abstract")
            # This tab's editor saves to 'personal_dialogue_html' in the DB
            self.bottom_tabs_with_editors.append(("personal_dialogue_html", self.elevator_abstract_tab.editor))
        else:
            create_editor_tab("Elevator Abstract", "Instructions for Elevator Abstract go here.",
                              "personal_dialogue_html", "reading_elevator_instr")

        if PartsOrderRelationTab:
            self.parts_order_relation_tab = PartsOrderRelationTab(
                self.db, self.project_id, self.reading_id
            )
            self.bottom_right_tabs.addTab(self.parts_order_relation_tab, "Parts: Order and Relation")
        else:
            # This fallback is incorrect as Parts tab doesn't use a rich text editor
            create_editor_tab("Parts: Order and Relation", "Instructions for Parts: Order and Relation go here.",
                              "personal_dialogue_html", "reading_parts_instr")  # Key is wrong, but it's a fallback

        if KeyTermsTab:
            self.key_terms_tab = KeyTermsTab(self.db, self.project_id, self.reading_id)
            self.bottom_right_tabs.addTab(self.key_terms_tab, "Key Terms")
        else:
            create_editor_tab("Key Terms", "Instructions for Key Terms go here.", "key_terms_html",
                              "reading_key_terms_instr")

        if ArgumentsTab:
            self.arguments_tab = ArgumentsTab(self.db, self.project_id, self.reading_id)
            self.bottom_right_tabs.addTab(self.arguments_tab, "Arguments")
        else:
            create_editor_tab("Arguments", "Instructions for Arguments go here.", "arguments_html",
                              "reading_arguments_instr")

        if GapsTab:
            self.gaps_tab = GapsTab(spell_checker_service=self.spell_checker_service)  # <-- PASS SERVICE
            self.bottom_right_tabs.addTab(self.gaps_tab, "Gaps")
            self.bottom_tabs_with_editors.append(("gaps_html", self.gaps_tab.editor))
        else:
            create_editor_tab("Gaps", "Instructions for Gaps go here.", "gaps_html", "reading_gaps_instr")

        if TheoriesTab:
            self.theories_tab = TheoriesTab(self.db, self.project_id, self.reading_id)
            self.bottom_right_tabs.addTab(self.theories_tab, "Theories")
        else:
            create_editor_tab("Theories", "Instructions for Theories go here.", "theories_html",
                              "reading_theories_instr")

        if PersonalDialogueTab:
            self.personal_dialogue_tab = PersonalDialogueTab(
                spell_checker_service=self.spell_checker_service)  # <-- PASS SERVICE
            self.bottom_right_tabs.addTab(self.personal_dialogue_tab, "Personal Dialogue")
            self.bottom_tabs_with_editors.append(("personal_dialogue_html", self.personal_dialogue_tab.editor))
        else:
            create_editor_tab("Personal Dialogue", "Instructions for Personal Dialogue go here.",
                              "personal_dialogue_html", "reading_dialogue_instr")

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
            # --- SAFETY: LOCK UI UPDATES ---
            self._is_loading = True

            details = self.db.get_reading_details(self.reading_id)
            if not details:
                QMessageBox.critical(self, "Error", f"Could not load details for reading ID {self.reading_id}")
                return

            self.reading_details_row = details

            title = self._get_detail('title')
            author = self._get_detail('author')
            nickname = self._get_detail('nickname')

            # --- MODIFIED: Use setPlainText for QTextEdit ---
            self.edit_title.setPlainText(title)
            # --- END MODIFIED ---

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

            # --- NEW: Load instructions for all tabs ---
            instructions = self.db.get_or_create_instructions(self.project_id)
            self.update_all_tab_instructions(instructions)
            # --- END NEW ---

        except Exception as e:
            QMessageBox.critical(self, "Error Loading Reading", f"An error occurred: {e}")
            import traceback;
            traceback.print_exc()
        finally:
            self._is_loading = False  # UNLOCK

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

            # --- MODIFIED: Use new simple tab logic ---
            if field_name == 'personal_dialogue_html' and ElevatorAbstractTab and hasattr(self,
                                                                                          'elevator_abstract_tab') and editor.editor_title == "Elevator Abstract":
                html = self._get_detail(field_name, default="")
                editor.set_html(html)
                continue
            if field_name == 'gaps_html' and GapsTab and hasattr(self, 'gaps_tab') and editor.editor_title == "Gaps":
                html = self._get_detail(field_name, default="")
                editor.set_html(html)
                continue
            if field_name == 'personal_dialogue_html' and PersonalDialogueTab and hasattr(self,
                                                                                          'personal_dialogue_tab') and editor.editor_title == "Personal Dialogue":
                html = self._get_detail(field_name, default="")
                editor.set_html(html)
                continue
            # --- END MODIFIED ---

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

            # --- MODIFIED: Use new simple tab logic ---
            if field_name == 'personal_dialogue_html' and ElevatorAbstractTab and hasattr(self,
                                                                                          'elevator_abstract_tab') and editor.editor_title == "Elevator Abstract":
                def create_callback(fname):
                    return lambda html: self.db.update_reading_field(
                        self.reading_id, fname, html
                    ) if html is not None else None

                editor.get_html(create_callback(field_name))
                continue
            if field_name == 'gaps_html' and GapsTab and hasattr(self, 'gaps_tab') and editor.editor_title == "Gaps":
                def create_callback(fname):
                    return lambda html: self.db.update_reading_field(
                        self.reading_id, fname, html
                    ) if html is not None else None

                editor.get_html(create_callback(field_name))
                continue
            if field_name == 'personal_dialogue_html' and PersonalDialogueTab and hasattr(self,
                                                                                          'personal_dialogue_tab') and editor.editor_title == "Personal Dialogue":
                def create_callback(fname):
                    return lambda html: self.db.update_reading_field(
                        self.reading_id, fname, html
                    ) if html is not None else None

                editor.get_html(create_callback(field_name))
                continue

            # --- END MODIFIED ---

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
            # --- MODIFIED: Use toPlainText() for QTextEdit ---
            'title': self.edit_title.toPlainText(),
            # --- END MODIFIED ---
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
        # --- SAFETY: LOCK UI UPDATES ---
        was_loading = self._is_loading
        self._is_loading = True

        # Stop signals to prevent crash on clear()
        self.outline_tree.blockSignals(True)
        self.outline_tree.clear()

        try:
            root_items = self.db.get_reading_outline(self.reading_id, parent_id=None)
            for item_data in root_items:
                parent_widget = self.outline_tree
                self._add_outline_item(parent_widget, item_data)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load reading outline: {e}")
        finally:
            # Restore signals
            self.outline_tree.blockSignals(False)
            if not was_loading:
                self._is_loading = False

    def _add_outline_item(self, parent_widget, item_data: dict):
        """Recursive helper to add items to the outline tree."""
        item = QTreeWidgetItem(parent_widget, [item_data['section_title']])
        item.setData(0, Qt.ItemDataRole.UserRole, item_data['id'])

        # --- ENABLE INLINE EDITING ---
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
        # -----------------------------

        children_data = self.db.get_reading_outline(self.reading_id, parent_id=item_data['id'])
        for child_data in children_data:
            self._add_outline_item(item, child_data)

        item.setExpanded(True)

    def on_outline_item_changed(self, item, column):
        """
        Handles edits to the tree cells (Rename).
        CRITICAL: Do NOT reload the tree here, or it loops/crashes.
        """
        # --- CRITICAL: Recursion Check ---
        if self._is_loading:
            return

        item_id = item.data(0, Qt.ItemDataRole.UserRole)
        new_text = item.text(column)

        # Determine field based on column (0=Title)
        if column == 0 and item_id:
            try:
                # Update DB directly
                self.db.update_outline_section_title(item_id, new_text)
                # DO NOT CALL self.load_outline() HERE
            except Exception as e:
                print(f"Error updating outline title: {e}")

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

    # --- NEW: Helper to open a wider QInputDialog ---
    def _get_text_input_wide(self, title, label, text_value=""):
        """Helper to open a wider QInputDialog."""
        dialog = QInputDialog(self)
        dialog.setWindowTitle(title)
        dialog.setLabelText(label)
        dialog.setTextValue(text_value)
        dialog.setInputMode(QInputDialog.InputMode.TextInput)

        # Force a larger width
        dialog.resize(500, dialog.height())

        # Sometimes resize isn't enough before show, so we set a min width on the input box if we can find it
        # or just the dialog itself
        dialog.setMinimumWidth(500)

        ok = dialog.exec() == QDialog.DialogCode.Accepted
        return dialog.textValue(), ok

    # --- END NEW ---

    def add_section(self):
        """Adds a new root-level section."""
        text, ok = self._get_text_input_wide("Add Section", "Section Title:")
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
        text, ok = self._get_text_input_wide("Add Subsection", "Subsection Title:")
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

        new_title, ok = self._get_text_input_wide("Rename Section", "New Title:", text_value=current_title)
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

    # --- NEW: Reading Rules Methods ---

    def _get_reading_rules_html(self):
        """Fetches rules from DB, falling back to default."""
        instructions = self.db.get_or_create_instructions(self.project_id)
        html = instructions.get("reading_rules_html", "")
        if not html or html.isspace():
            html = DEFAULT_READING_RULES_HTML
        return html

    @Slot()
    def _show_reading_rules(self):
        """
        Opens the read-only dialog to display the reading rules.
        """
        if not ViewReadingRulesDialog:
            QMessageBox.critical(self, "Error", "ViewReadingRulesDialog not loaded.")
            return

        html = self._get_reading_rules_html()
        dialog = ViewReadingRulesDialog(html, self)
        dialog.exec()

    # --- NEW: Instruction Methods ---
    @Slot()
    def open_edit_reading_instructions(self):
        """
        Opens the main instructions dialog. This is called by the menu item.
        """
        if self.project_id == -1 or not EditInstructionsDialog:
            QMessageBox.warning(self, "Error", "Instruction Dialog could not be loaded.")
            return

        # 1. Get all current instructions
        instructions = self.db.get_or_create_instructions(self.project_id)

        # 2. Open the (now tabbed) dialog
        dialog = EditInstructionsDialog(instructions, self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_instr = dialog.result
            if new_instr:
                # 3. Save ALL instructions back to the DB
                self.db.update_instructions(self.project_id, new_instr)

                # 4. Refresh all child tabs
                self.update_all_tab_instructions(new_instr)

    def update_all_tab_instructions(self, instructions_data):
        """
        Pushes new instruction text to all child tabs.
        """

        # Define the mapping of tab objects to their instruction key
        tab_key_map = [
            (getattr(self, 'driving_question_tab', None), "reading_dq_instr"),
            (getattr(self, 'leading_propositions_tab', None), "reading_lp_instr"),
            (getattr(self, 'unity_tab', None), "reading_unity_instr"),
            (getattr(self, 'elevator_abstract_tab', None), "reading_elevator_instr"),
            (getattr(self, 'parts_order_relation_tab', None), "reading_parts_instr"),
            (getattr(self, 'key_terms_tab', None), "reading_key_terms_instr"),
            (getattr(self, 'arguments_tab', None), "reading_arguments_instr"),
            (getattr(self, 'gaps_tab', None), "reading_gaps_instr"),
            (getattr(self, 'theories_tab', None), "reading_theories_instr"),
            (getattr(self, 'personal_dialogue_tab', None), "reading_dialogue_instr"),
        ]

        # Call update_instructions on each tab that exists
        for tab_widget, key in tab_key_map:
            # --- MODIFIED: Store simple editor labels for fallback ---
            if tab_widget is None and key in self.instruction_labels:
                # This is a fallback editor created in _add_bottom_tabs
                label = self.instruction_labels[key]
                text = instructions_data.get(key, "")
                label.setText(text)
                label.setVisible(bool(text))
            elif tab_widget and hasattr(tab_widget, 'update_instructions'):
                tab_widget.update_instructions(instructions_data, key)
            elif tab_widget:
                print(f"Warning: Tab {tab_widget.objectName()} is missing 'update_instructions' method.")
            # --- END MODIFIED ---

    # --- END NEW ---

    # ##################################################################
    # #
    # #                      --- MODIFICATION START (Focus Fix v3) ---
    # #
    # ##################################################################
    @Slot(int, int, int, str)
    def set_outline_selection(self, anchor_id: int, outline_id: int, item_link_id: int, item_type: str = ''):
        """
        Finds and selects an item in the outline tree.
        If item_link_id is provided, it tries to find and select
        the item in the corresponding bottom tab.
        """
        print(
            f"    ReadingTab.set_outline_selection: START (anchor={anchor_id}). Current focus: {QApplication.instance().focusWidget()}")

        self._pending_anchor_focus = anchor_id if (anchor_id and (
                outline_id is not None and outline_id > 0)) else None  # --- FIX: Only queue if outline_id is valid ---

        # --- Part 1: Select Outline Item ---
        if outline_id == 0 or outline_id is None:  # --- FIX: Handle None ---
            self._pending_anchor_focus = None

            # ---!!--- THIS IS THE FIX V4 ---!!---
            # DO NOT block signals. Let clearSelection() emit its
            # currentItemChanged signal normally.
            self.outline_tree.clearSelection()

            # --- FIX: Manually call if selection is *already* None ---
            if self.outline_tree.currentItem() is None:
                self.on_outline_selection_changed(None, None)
            # ---!!--- END OF FIX V4 ---!!---

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
                # (Tab object, Tab index, widget_name)
                (getattr(self, 'driving_question_tab', None),
                 self.bottom_right_tabs.indexOf(getattr(self, 'driving_question_tab', None)),
                 'tree_widget'),
                (getattr(self, 'leading_propositions_tab', None),
                 self.bottom_right_tabs.indexOf(getattr(self, 'leading_propositions_tab', None)),
                 'item_list'),  # <-- This is a QListWidget
                (getattr(self, 'key_terms_tab', None),
                 self.bottom_right_tabs.indexOf(getattr(self, 'key_terms_tab', None)),
                 'tree_widget'),
                (getattr(self, 'arguments_tab', None),
                 self.bottom_right_tabs.indexOf(getattr(self, 'arguments_tab', None)),
                 'tree_widget'),
                (getattr(self, 'theories_tab', None),
                 self.bottom_right_tabs.indexOf(getattr(self, 'theories_tab', None)),
                 'tree_widget'),
            ]

            for tab, tab_index, widget_name in tabs_to_check:
                if tab and tab_index != -1 and hasattr(tab, widget_name):
                    tree_or_list_widget = getattr(tab, widget_name)  # Get the tree/list widget

                    # ---!!--- THIS IS THE FIX ---!!---
                    found_item = None
                    if isinstance(tree_or_list_widget, QTreeWidget):
                        it = QTreeWidgetItemIterator(tree_or_list_widget)
                        while it.value():
                            item = it.value()
                            if item.data(0, Qt.ItemDataRole.UserRole) == item_link_id:
                                found_item = item
                                break
                            it += 1
                    elif isinstance(tree_or_list_widget, QListWidget):
                        for i in range(tree_or_list_widget.count()):
                            item = tree_or_list_widget.item(i)
                            if item.data(Qt.ItemDataRole.UserRole) == item_link_id:
                                found_item = item
                                break
                    # ---!!--- END OF FIX ---!!---

                    if found_item:
                        # 1. Switch the bottom tab
                        self.bottom_right_tabs.setCurrentIndex(tab_index)

                        # 2. Select the item in that tab's tree
                        tree_or_list_widget.setCurrentItem(found_item)
                        tree_or_list_widget.scrollToItem(found_item, QAbstractItemView.ScrollHint.PositionAtCenter)
                        print(
                            f"    ReadingTab.set_outline_selection: Set item in BOTTOM tab. Focus is now: {QApplication.instance().focusWidget()}")

                        # --- FIX: Re-introduce 0ms timer to set focus ---
                        print(f"    ReadingTab.set_outline_selection: Queuing 0ms timer to focus BOTTOM TAB's widget.")
                        QTimer.singleShot(0, lambda widget=tree_or_list_widget: (  # <--- CAPTURE 'tree_or_list_widget'
                            print(
                                f"    ReadingTab.set_outline_selection: 0ms timer FIRED. Setting focus to BOTTOM TAB's widget."),
                            widget.setFocus(),  # <--- THIS IS THE FIX
                            print(
                                f"    ReadingTab.set_outline_selection: FINAL focus is: {QApplication.instance().focusWidget()}")
                        ))
                        # --- END FIX ---
                        return  # We are done.

        # --- Part 3: Fallback Focus ---
        if outline_id != 0 and outline_id is not None:  # --- FIX: Handle None ---
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
            anchor_id = self.notes_editor._get_id(fmt)
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
                        next_anchor_id = self.notes_editor._get_id(fmt)
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

        # --- MODIFIED: Pass self.db ---
        dialog = CreateAnchorDialog(selected_text, project_tags_list=tags, db=self.db, parent=self)
        # --- END MODIFICATION ---

        if dialog.exec() == QDialog.DialogCode.Accepted:
            tag_name = dialog.get_tag_text()
            # --- REMOVED: comment = dialog.get_comment() ---

            # --- ADDED: Get PDF ID ---
            pdf_node_id = dialog.get_pdf_node_id()
            # --- END ADDED ---

            if not tag_name:
                QMessageBox.warning(self, "Tag Required", "An anchor must have a tag.")
                return

            try:
                tag_data = self.db.get_or_create_tag(tag_name, self.project_id)
                if not tag_data:
                    raise Exception(f"Could not get or create tag '{tag_name}'")
                tag_id = tag_data['id']
                unique_doc_id = str(uuid.uuid4())

                # --- MODIFIED: Pass pdf_node_id ---
                anchor_id = self.db.create_anchor(
                    project_id=self.project_id,
                    reading_id=self.reading_id,
                    outline_id=self.current_outline_id,
                    tag_id=tag_id,
                    selected_text=selected_text,
                    comment="",  # No longer used
                    unique_doc_id=unique_doc_id,
                    item_link_id=None,
                    pdf_node_id=pdf_node_id
                )
                # --- END MODIFICATION ---

                if not anchor_id:
                    raise Exception("Failed to create anchor in database.")

                self.notes_editor.apply_anchor_format(
                    anchor_id=anchor_id,
                    tag_id=tag_id,
                    tag_name=tag_name,
                    comment="",  # No comment
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

            # --- MODIFIED: Pass db and current_data ---
            dialog = CreateAnchorDialog(
                selected_text=current_data['selected_text'],
                project_tags_list=tags,
                current_data=current_data,
                db=self.db,
                parent=self
            )
            # --- END MODIFICATION ---

            if dialog.exec() == QDialog.DialogCode.Accepted:
                new_tag_name = dialog.get_tag_text()
                # --- REMOVED: new_comment = dialog.get_comment() ---
                new_pdf_node_id = dialog.get_pdf_node_id()

                if not new_tag_name:
                    QMessageBox.warning(self, "Tag Required", "An anchor must have a tag.")
                    return

                tag_data = self.db.get_or_create_tag(new_tag_name, self.project_id)
                if not tag_data:
                    raise Exception(f"Could not get or create tag '{new_tag_name}'")
                new_tag_id = tag_data['id']

                # --- MODIFIED: Save pdf_node_id ---
                update_data = {
                    "comment": "",  # Cleared
                    "tags": [new_tag_id],
                    "pdf_node_id": new_pdf_node_id
                }
                self.db.update_anchor(anchor_id, update_data)
                # --- END MODIFICATION ---

                self.notes_editor.find_and_update_anchor_format(
                    anchor_id=anchor_id,
                    tag_id=new_tag_id,
                    tag_name=new_tag_name,
                    comment=""
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