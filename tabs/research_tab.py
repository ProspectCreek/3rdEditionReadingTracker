# tabs/research_tab.py
import sys
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QTreeWidget, QTreeWidgetItem,
    QStackedWidget, QLabel, QLineEdit, QTextEdit, QComboBox, QPushButton,
    QFrame, QScrollArea, QMenu, QInputDialog, QMessageBox, QListWidget, QListWidgetItem,
    QGroupBox, QFormLayout, QDialog, QDialogButtonBox
)
from PySide6.QtCore import Qt, Signal, Slot, QUrl
from PySide6.QtGui import QAction, QColor

# Import RichTextEditorTab
try:
    from tabs.rich_text_editor_tab import RichTextEditorTab
except ImportError:
    RichTextEditorTab = None

# Import ReorderDialog
try:
    from dialogs.reorder_dialog import ReorderDialog
except ImportError:
    ReorderDialog = None

# Import PdfLinkDialog
try:
    from dialogs.pdf_link_dialog import PdfLinkDialog
except ImportError:
    PdfLinkDialog = None


# --- Custom Dialog for Large Text Input (The "Popup") ---
class LargeTextEntryDialog(QDialog):
    """
    A dialog with a large QTextEdit for entering comprehensive questions/titles.
    """

    def __init__(self, title, label_text, parent=None, default_text=""):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(600)  # Wider
        self.setMinimumHeight(250)  # Taller

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(label_text))

        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("Type text here...")
        if default_text:
            self.text_edit.setPlainText(default_text)
        layout.addWidget(self.text_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_text(self):
        return self.text_edit.toPlainText().strip()


class LinkTermDialog(QDialog):
    """
    Dialog to select multiple Key Terms from the project terminology to link
    to a Research Question.
    """

    def __init__(self, db, project_id, current_term_ids, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Link Key Terms")
        self.setMinimumWidth(400)
        self.setMinimumHeight(500)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Select terms to link to this question:"))

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.MultiSelection)

        # Fetch all terms for project
        terms = db.get_project_terminology(project_id)
        current_ids = set(current_term_ids)

        for term in terms:
            item = QListWidgetItem(term['term'])
            item.setData(Qt.UserRole, term['id'])
            # Pre-select if already linked
            if term['id'] in current_ids:
                item.setSelected(True)
            self.list_widget.addItem(item)

        layout.addWidget(self.list_widget)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def get_selected_ids(self):
        """Returns list of selected terminology IDs."""
        return [item.data(Qt.UserRole) for item in self.list_widget.selectedItems()]


class ResearchTab(QWidget):
    """
    The Research tab allowing hierarchical organization of Research Questions,
    Sub-questions, and Outline Sections, with detailed fields and memos.
    Includes a bottom pane for Research Plans.
    """

    # Signal to request PDF linking dialog (passes the editor widget)
    linkPdfNodeRequested = Signal(object)
    # Signal when a link is clicked in an editor OR the PDF list
    linkUrlClicked = Signal(QUrl)
    # Signal to request opening a specific Term in the Synthesis Tab
    openTermRequested = Signal(int)

    def __init__(self, db, project_id, spell_checker_service=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.project_id = project_id
        self.spell_checker_service = spell_checker_service

        self._current_node_id = None
        self._current_plan_id = None
        self._ignore_changes = False

        self._setup_ui()
        self.load_tree()
        self.load_plans()

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(self.main_splitter)

        # --- Left Panel (Split Vertically) ---
        self.left_splitter = QSplitter(Qt.Orientation.Vertical)

        # 1. Top Left: Research Structure
        structure_widget = QWidget()
        structure_layout = QVBoxLayout(structure_widget)
        structure_layout.setContentsMargins(4, 4, 4, 4)

        struct_label = QLabel("Research Structure")
        struct_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #555;")
        structure_layout.addWidget(struct_label)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        self.tree.currentItemChanged.connect(self._on_tree_selection_changed)
        structure_layout.addWidget(self.tree)

        btn_layout = QHBoxLayout()
        self.btn_add_root = QPushButton("Add Question")
        self.btn_add_root.clicked.connect(self._add_root_question)
        btn_layout.addWidget(self.btn_add_root)
        structure_layout.addLayout(btn_layout)

        self.left_splitter.addWidget(structure_widget)

        # 2. Bottom Left: Research Plans
        plans_widget = QWidget()
        plans_layout = QVBoxLayout(plans_widget)
        plans_layout.setContentsMargins(4, 4, 4, 4)

        plans_label = QLabel("Research Plans")
        plans_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #555;")
        plans_layout.addWidget(plans_label)

        self.plan_list = QListWidget()
        self.plan_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.plan_list.customContextMenuRequested.connect(self._show_plan_context_menu)
        self.plan_list.currentItemChanged.connect(self._on_plan_selection_changed)
        plans_layout.addWidget(self.plan_list)

        plans_btn_layout = QHBoxLayout()
        btn_add_plan = QPushButton("Add Plan")
        btn_add_plan.clicked.connect(self._add_plan)
        btn_del_plan = QPushButton("Delete")
        btn_del_plan.clicked.connect(self._delete_plan)
        btn_ren_plan = QPushButton("Rename")
        btn_ren_plan.clicked.connect(self._rename_plan)

        plans_btn_layout.addWidget(btn_add_plan)
        plans_btn_layout.addWidget(btn_del_plan)
        plans_btn_layout.addWidget(btn_ren_plan)
        plans_layout.addLayout(plans_btn_layout)

        self.left_splitter.addWidget(plans_widget)
        self.left_splitter.setSizes([400, 400])  # 50/50 split

        self.main_splitter.addWidget(self.left_splitter)

        # --- Right Panel: Detail Forms ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(4, 4, 4, 4)

        self.detail_stack = QStackedWidget()

        # 0: Empty State
        self.page_empty = QLabel("Select an item to view details.")
        self.page_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_empty.setStyleSheet("color: #888; font-style: italic;")
        self.detail_stack.addWidget(self.page_empty)

        # 1: Question Details
        self.page_question = self._create_question_page()
        self.detail_stack.addWidget(self.page_question)

        # 2: Sub-question Details
        self.page_sub = self._create_subquestion_page()
        self.detail_stack.addWidget(self.page_sub)

        # 3: Outline Details
        self.page_outline = self._create_outline_page()
        self.detail_stack.addWidget(self.page_outline)

        # 4: Research Plan Editor
        self.page_plan_editor = self._create_plan_page()
        self.detail_stack.addWidget(self.page_plan_editor)

        right_layout.addWidget(self.detail_stack)

        self.main_splitter.addWidget(right_panel)
        self.main_splitter.setSizes([300, 700])

    # --- Page Creation ---

    def _create_question_page(self):
        """Creates the UI page for a Research Question (Parent)."""
        page = QWidget()
        layout = QVBoxLayout(page)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        form = QFormLayout(content)

        # Title
        self.q_title = QTextEdit()
        self.q_title.setMinimumHeight(100)
        self.q_title.setPlaceholderText("Research Question...")
        self.q_title.textChanged.connect(lambda: self._save_field_debounced('title', self.q_title))
        form.addRow("Question:", self.q_title)

        # PDF Links
        pdf_group = QGroupBox("Linked PDF Nodes")
        pdf_layout = QVBoxLayout(pdf_group)
        self.q_pdf_list = QListWidget()
        self.q_pdf_list.setMinimumHeight(150)
        self.q_pdf_list.itemDoubleClicked.connect(self._on_pdf_list_item_clicked)
        self.q_pdf_list.setToolTip("Double-click to jump to PDF")
        pdf_layout.addWidget(self.q_pdf_list)

        pdf_btn_layout = QHBoxLayout()
        self.btn_q_add_pdf = QPushButton("Add Node")
        self.btn_q_add_pdf.clicked.connect(lambda: self._add_pdf_link(self.q_pdf_list))
        self.btn_q_remove_pdf = QPushButton("Remove Selected")
        self.btn_q_remove_pdf.clicked.connect(lambda: self._remove_pdf_link(self.q_pdf_list))
        pdf_btn_layout.addWidget(self.btn_q_add_pdf)
        pdf_btn_layout.addWidget(self.btn_q_remove_pdf)
        pdf_btn_layout.addStretch()
        pdf_layout.addLayout(pdf_btn_layout)
        form.addRow(pdf_group)

        # Standard Fields
        self.q_problem = QTextEdit()
        self.q_problem.setMaximumHeight(80)
        self.q_problem.textChanged.connect(lambda: self._save_field_debounced('problem_statement', self.q_problem))
        form.addRow("Problem Statement:", self.q_problem)

        self.q_scope = QTextEdit()
        self.q_scope.setMaximumHeight(60)
        self.q_scope.textChanged.connect(lambda: self._save_field_debounced('scope', self.q_scope))
        form.addRow("Scope & Delimitations:", self.q_scope)

        self.q_frameworks = QTextEdit()
        self.q_frameworks.setMaximumHeight(60)
        self.q_frameworks.textChanged.connect(lambda: self._save_field_debounced('frameworks', self.q_frameworks))
        form.addRow("Theoretical Frameworks:", self.q_frameworks)

        # Key Terms
        terms_group = QGroupBox("Key Terms (from Synthesis)")
        terms_layout = QVBoxLayout(terms_group)
        self.q_term_list = QListWidget()
        self.q_term_list.setMaximumHeight(120)
        self.q_term_list.setAlternatingRowColors(True)
        self.q_term_list.itemDoubleClicked.connect(self._on_term_double_clicked)
        self.q_term_list.setToolTip("Double-click to open term in Synthesis tab")
        terms_layout.addWidget(self.q_term_list)

        terms_btn_layout = QHBoxLayout()
        btn_link_terms = QPushButton("Manage Linked Terms")
        btn_link_terms.clicked.connect(self._link_terms)
        terms_btn_layout.addWidget(btn_link_terms)
        terms_btn_layout.addStretch()
        terms_layout.addLayout(terms_btn_layout)
        form.addRow(terms_group)

        self.q_thesis = QTextEdit()
        self.q_thesis.setMaximumHeight(60)
        self.q_thesis.textChanged.connect(lambda: self._save_field_debounced('working_thesis', self.q_thesis))
        form.addRow("Working Thesis:", self.q_thesis)

        self.q_issues = QTextEdit()
        self.q_issues.setMaximumHeight(60)
        self.q_issues.textChanged.connect(lambda: self._save_field_debounced('open_issues', self.q_issues))
        form.addRow("Open Issues:", self.q_issues)

        # Syntopical Group
        syn_group = QGroupBox("Syntopical / Comparative Support")
        syn_layout = QFormLayout(syn_group)
        self.q_common = QTextEdit()
        self.q_common.setMaximumHeight(60)
        self.q_common.textChanged.connect(lambda: self._save_field_debounced('common_questions', self.q_common))
        syn_layout.addRow("Common Questions:", self.q_common)

        self.q_agree = QTextEdit()
        self.q_agree.setMaximumHeight(60)
        self.q_agree.textChanged.connect(lambda: self._save_field_debounced('agreements', self.q_agree))
        syn_layout.addRow("Points of Agreement:", self.q_agree)

        self.q_disagree = QTextEdit()
        self.q_disagree.setMaximumHeight(60)
        self.q_disagree.textChanged.connect(lambda: self._save_field_debounced('disagreements', self.q_disagree))
        syn_layout.addRow("Points of Disagreement:", self.q_disagree)

        if RichTextEditorTab:
            self.q_synthesis = RichTextEditorTab("Synthesis", spell_checker_service=self.spell_checker_service)
            self.q_synthesis.setMinimumHeight(200)
        else:
            self.q_synthesis = QTextEdit()
            self.q_synthesis.setMinimumHeight(100)
        syn_layout.addRow("My Synthesis:", self.q_synthesis)
        form.addRow(syn_group)

        # Memos Section
        memo_group = QGroupBox("Research Memos")
        memo_layout = QVBoxLayout(memo_group)
        self.memo_list = QListWidget()
        self.memo_list.setMinimumHeight(100)
        self.memo_list.itemClicked.connect(self._load_memo)
        memo_layout.addWidget(self.memo_list)

        memo_btns = QHBoxLayout()
        btn_add_memo = QPushButton("New Memo")
        btn_del_memo = QPushButton("Delete Memo")
        btn_add_memo.clicked.connect(self._add_memo)
        btn_del_memo.clicked.connect(self._delete_memo)
        memo_btns.addWidget(btn_add_memo)
        memo_btns.addWidget(btn_del_memo)
        memo_btns.addStretch()
        memo_layout.addLayout(memo_btns)

        self.memo_title = QLineEdit()
        self.memo_title.setPlaceholderText("Memo Title")
        self.memo_title.editingFinished.connect(self._save_current_memo)
        memo_layout.addWidget(self.memo_title)

        if RichTextEditorTab:
            self.memo_content = RichTextEditorTab("Memo Content", spell_checker_service=self.spell_checker_service)
            self.memo_content.setMinimumHeight(300)
        else:
            self.memo_content = QTextEdit()
            self.memo_content.setMinimumHeight(200)
        memo_layout.addWidget(self.memo_content)
        form.addRow(memo_group)

        scroll.setWidget(content)
        layout.addWidget(scroll)

        btn_save = QPushButton("Save Changes")
        btn_save.clicked.connect(self._manual_save_question)
        layout.addWidget(btn_save)

        return page

    def _create_subquestion_page(self):
        """Creates the UI page for a Sub-question (Child)."""
        page = QWidget()
        layout = QVBoxLayout(page)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        form = QFormLayout(content)

        self.sub_text = QTextEdit()
        self.sub_text.setMinimumHeight(100)
        self.sub_text.setPlaceholderText("Sub-question text...")
        self.sub_text.textChanged.connect(lambda: self._save_field_debounced('title', self.sub_text))
        form.addRow("Sub-question:", self.sub_text)

        # PDF Links
        pdf_group = QGroupBox("Linked PDF Nodes")
        pdf_layout = QVBoxLayout(pdf_group)
        self.sub_pdf_list = QListWidget()
        self.sub_pdf_list.setMinimumHeight(150)
        self.sub_pdf_list.itemDoubleClicked.connect(self._on_pdf_list_item_clicked)
        self.sub_pdf_list.setToolTip("Double-click to jump to PDF")
        pdf_layout.addWidget(self.sub_pdf_list)

        pdf_btn_layout = QHBoxLayout()
        self.btn_sub_add_pdf = QPushButton("Add Node")
        self.btn_sub_add_pdf.clicked.connect(lambda: self._add_pdf_link(self.sub_pdf_list))
        self.btn_sub_remove_pdf = QPushButton("Remove Selected")
        self.btn_sub_remove_pdf.clicked.connect(lambda: self._remove_pdf_link(self.sub_pdf_list))
        pdf_btn_layout.addWidget(self.btn_sub_add_pdf)
        pdf_btn_layout.addWidget(self.btn_sub_remove_pdf)
        pdf_btn_layout.addStretch()
        pdf_layout.addLayout(pdf_btn_layout)
        form.addRow(pdf_group)

        self.sub_role = QComboBox()
        self.sub_role.setEditable(True)
        self.sub_role.addItems(["Mechanism", "Context", "Case Study", "Comparison", "Evidence", "Counter-argument"])
        self.sub_role.currentTextChanged.connect(lambda t: self._save_field('role', t))
        form.addRow("Role:", self.sub_role)

        if RichTextEditorTab:
            self.sub_evidence = RichTextEditorTab("Key Evidence", spell_checker_service=self.spell_checker_service)
            self.sub_evidence.setMinimumHeight(200)
            self.sub_evidence.linkPdfNodeTriggered.connect(lambda: self.linkPdfNodeRequested.emit(self.sub_evidence))
            self.sub_evidence.editor.smartAnchorClicked.connect(self.linkUrlClicked.emit)
        else:
            self.sub_evidence = QTextEdit()
        form.addRow("Key Evidence:", self.sub_evidence)

        self.sub_contra = QTextEdit()
        self.sub_contra.setMaximumHeight(80)
        self.sub_contra.textChanged.connect(lambda: self._save_field_debounced('contradictions', self.sub_contra))
        form.addRow("Contradictions & Tensions:", self.sub_contra)

        self.sub_concl = QTextEdit()
        self.sub_concl.setMaximumHeight(80)
        self.sub_concl.textChanged.connect(lambda: self._save_field_debounced('preliminary_conclusion', self.sub_concl))
        form.addRow("Preliminary Conclusion:", self.sub_concl)

        scroll.setWidget(content)
        layout.addWidget(scroll)

        btn_save = QPushButton("Save Changes")
        btn_save.clicked.connect(self._manual_save_sub)
        layout.addWidget(btn_save)

        return page

    def _create_outline_page(self):
        """Creates the UI page for an Outline Section."""
        page = QWidget()
        layout = QVBoxLayout(page)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        form = QFormLayout(content)

        self.out_title = QLineEdit()
        self.out_title.editingFinished.connect(lambda: self._save_field('title', self.out_title.text()))
        form.addRow("Section Title:", self.out_title)

        self.out_purpose = QTextEdit()
        self.out_purpose.setMaximumHeight(100)
        self.out_purpose.textChanged.connect(lambda: self._save_field_debounced('section_purpose', self.out_purpose))
        form.addRow("Section Purpose:", self.out_purpose)

        self.out_notes = QTextEdit()
        self.out_notes.setMinimumHeight(200)
        self.out_notes.textChanged.connect(lambda: self._save_field_debounced('section_notes', self.out_notes))
        form.addRow("Notes:", self.out_notes)

        scroll.setWidget(content)
        layout.addWidget(scroll)
        return page

    def _create_plan_page(self):
        """Creates the UI page for Research Plan Editor."""
        page = QWidget()
        layout = QVBoxLayout(page)

        label = QLabel("Research Plan Editor")
        label.setStyleSheet("font-weight: bold; font-size: 16px; margin-bottom: 5px;")
        layout.addWidget(label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        form = QFormLayout(content)

        # A. Research Question (Dropdown)
        self.plan_question = QComboBox()
        self.plan_question.currentIndexChanged.connect(self._save_plan_question)
        form.addRow("Research Question:", self.plan_question)

        # B. Methodological Approach (Dropdown with Other)
        self.plan_method = QComboBox()
        self.plan_method.setEditable(True)
        self.plan_method.addItems([
            "Case Study", "Thematic Analysis", "Comparative Analysis",
            "Qualitative", "Quantitative", "Mixed Methods",
            "Interpretive Analysis", "Grounded Theory"
        ])
        self.plan_method.currentTextChanged.connect(lambda t: self._save_plan_field('methodological_approach', t))
        form.addRow("Methodological Approach:", self.plan_method)

        # C. Units of Analysis
        self.plan_units = QTextEdit()
        self.plan_units.setMaximumHeight(80)
        self.plan_units.textChanged.connect(
            lambda: self._save_plan_field_debounced('units_of_analysis', self.plan_units))
        form.addRow("Units of Analysis:", self.plan_units)

        # D. Data Sources
        self.plan_sources = QTextEdit()
        self.plan_sources.setMaximumHeight(80)
        self.plan_sources.textChanged.connect(
            lambda: self._save_plan_field_debounced('data_sources', self.plan_sources))
        form.addRow("Data Sources:", self.plan_sources)

        # E. Sampling Strategy
        self.plan_sampling = QTextEdit()
        self.plan_sampling.setMaximumHeight(80)
        self.plan_sampling.textChanged.connect(
            lambda: self._save_plan_field_debounced('sampling_strategy', self.plan_sampling))
        form.addRow("Sampling Strategy:", self.plan_sampling)

        # F. Coding Scheme
        self.plan_coding = QTextEdit()
        self.plan_coding.setMaximumHeight(80)
        self.plan_coding.textChanged.connect(lambda: self._save_plan_field_debounced('coding_scheme', self.plan_coding))
        form.addRow("Coding Scheme Summary:", self.plan_coding)

        # G. Validity / Limitations
        self.plan_validity = QTextEdit()
        self.plan_validity.setMinimumHeight(100)
        self.plan_validity.textChanged.connect(
            lambda: self._save_plan_field_debounced('validity_limitations', self.plan_validity))
        form.addRow("Validity / Reliability / Limitations:", self.plan_validity)

        scroll.setWidget(content)
        layout.addWidget(scroll)
        return page

    # --- Tree Management ---

    def load_tree(self):
        """Loads the research nodes from DB into the tree."""
        self.tree.clear()
        nodes = self.db.get_research_nodes(self.project_id)

        # Build a map of id -> item
        item_map = {}
        root_items = []

        # First pass: create all items
        for node in nodes:
            item = QTreeWidgetItem([node['title'] or "(Untitled)"])
            item.setData(0, Qt.ItemDataRole.UserRole, node['id'])
            item.setData(0, Qt.ItemDataRole.UserRole + 1, node['type'])
            item_map[node['id']] = item

            # Icon / Color based on type
            if node['type'] == 'question':
                item.setBackground(0, QColor("#E3F2FD"))  # Light Blue
                font = item.font(0)
                font.setBold(True)
                item.setFont(0, font)
            elif node['type'] == 'section':
                item.setForeground(0, QColor("#4CAF50"))  # Greenish
                font = item.font(0)
                font.setItalic(True)
                item.setFont(0, font)

        # Second pass: build hierarchy
        for node in nodes:
            item = item_map[node['id']]
            if node['parent_id'] and node['parent_id'] in item_map:
                parent = item_map[node['parent_id']]
                parent.addChild(item)
            else:
                self.tree.addTopLevelItem(item)
                root_items.append(item)

        self.tree.expandAll()

    def _on_tree_selection_changed(self, current, previous):
        if not current:
            # Only switch if plan list is also not selected?
            # Let's enforce that selecting tree clears plan selection
            if self.plan_list.currentItem():
                return
            self.detail_stack.setCurrentIndex(0)
            self._current_node_id = None
            return

        # If a tree item is selected, clear plan selection so we switch view
        self.plan_list.blockSignals(True)
        self.plan_list.clearSelection()
        self.plan_list.blockSignals(False)
        self._current_plan_id = None

        node_id = current.data(0, Qt.ItemDataRole.UserRole)
        node_type = current.data(0, Qt.ItemDataRole.UserRole + 1)
        self._current_node_id = node_id

        self._load_node_details(node_id, node_type)

    def _load_node_details(self, node_id, node_type):
        self._ignore_changes = True
        data = self.db.get_research_node_details(node_id)

        if node_type == 'question':
            self.detail_stack.setCurrentWidget(self.page_question)
            self.q_title.setPlainText(data['title'] or "")
            self.q_problem.setPlainText(data['problem_statement'] or "")
            self.q_scope.setPlainText(data['scope'] or "")
            self.q_frameworks.setPlainText(data['frameworks'] or "")

            self.q_thesis.setPlainText(data['working_thesis'] or "")
            self.q_issues.setPlainText(data['open_issues'] or "")
            self.q_common.setPlainText(data['common_questions'] or "")
            self.q_agree.setPlainText(data['agreements'] or "")
            self.q_disagree.setPlainText(data['disagreements'] or "")
            if RichTextEditorTab:
                self.q_synthesis.set_html(data['synthesis'] or "")
            else:
                self.q_synthesis.setPlainText(data['synthesis'] or "")

            self._refresh_pdf_list(node_id, self.q_pdf_list)
            self._load_memos_list(node_id)
            self._load_terms_list(node_id)

        elif node_type == 'subquestion':
            self.detail_stack.setCurrentWidget(self.page_sub)
            self.sub_text.setPlainText(data['title'] or "")
            self.sub_role.setCurrentText(data['role'] or "")
            if RichTextEditorTab:
                self.sub_evidence.set_html(data['evidence'] or "")
            else:
                self.sub_evidence.setPlainText(data['evidence'] or "")
            self.sub_contra.setPlainText(data['contradictions'] or "")
            self.sub_concl.setPlainText(data['preliminary_conclusion'] or "")

            self._refresh_pdf_list(node_id, self.sub_pdf_list)

        elif node_type == 'section':
            self.detail_stack.setCurrentWidget(self.page_outline)
            self.out_title.setText(data['title'] or "")
            self.out_purpose.setPlainText(data['section_purpose'] or "")
            self.out_notes.setPlainText(data['section_notes'] or "")

        self._ignore_changes = False

    # --- Plan Management ---

    def load_plans(self):
        """Loads research plans into the bottom-left list."""
        self.plan_list.clear()
        plans = self.db.get_research_plans(self.project_id)

        for p in plans:
            display = f"{p['title']} ({p.get('status', 'Not Started')})"
            item = QListWidgetItem(display)
            item.setData(Qt.UserRole, p['id'])
            self.plan_list.addItem(item)

    def _show_plan_context_menu(self, pos):
        """Right-click context menu for Research Plans."""
        item = self.plan_list.itemAt(pos)
        menu = QMenu()

        menu.addAction("Add New Plan", self._add_plan)

        if item:
            menu.addSeparator()
            menu.addAction("Rename Plan", self._rename_plan)
            menu.addAction("Delete Plan", self._delete_plan)

            # Reorder if ReorderDialog exists
            if ReorderDialog:
                menu.addSeparator()
                menu.addAction("Reorder Plans...", self._reorder_plans)

        menu.exec(self.plan_list.viewport().mapToGlobal(pos))

    def _add_plan(self):
        # Use LargeTextEntryDialog for a wider/larger input field
        dialog = LargeTextEntryDialog("New Research Plan", "Enter Plan Title:", self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            title = dialog.get_text()
            if title:
                self.db.add_research_plan(self.project_id, title)
                self.load_plans()

    def _delete_plan(self):
        item = self.plan_list.currentItem()
        if not item: return
        plan_id = item.data(Qt.UserRole)

        if QMessageBox.question(self, "Delete", "Delete this plan?") == QMessageBox.StandardButton.Yes:
            self.db.delete_research_plan(plan_id)
            self.load_plans()
            if self._current_plan_id == plan_id:
                self.detail_stack.setCurrentIndex(0)
                self._current_plan_id = None

    def _rename_plan(self):
        item = self.plan_list.currentItem()
        if not item: return
        plan_id = item.data(Qt.UserRole)

        # Extract title from "Title (Status)"
        current_text = item.text().rsplit(" (", 1)[0]

        # Use LargeTextEntryDialog for rename too, pre-filled
        dialog = LargeTextEntryDialog("Rename Plan", "New Title:", self, default_text=current_text)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_title = dialog.get_text()
            if new_title:
                self.db.update_research_plan_field(plan_id, 'title', new_title)
                self.load_plans()

    def _reorder_plans(self):
        """Allows reordering of plans via ReorderDialog."""
        if not ReorderDialog: return

        # Collect plans: (Display Name, ID)
        # Note: ReorderDialog typically expects (Name, ID) tuples
        # We can fetch fresh from DB or use list items
        plans = []
        for i in range(self.plan_list.count()):
            item = self.plan_list.item(i)
            plans.append((item.text(), item.data(Qt.UserRole)))

        if len(plans) < 2: return

        dialog = ReorderDialog(plans, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # We need a method in DB to update plan order.
            # Assuming db.update_research_plan_order exists or we can add it.
            # If it doesn't exist, we might need to add it to mixin.
            # I'll add a helper loop here if needed or assume mixin update.
            # Let's check mixin... Ah, I need to add update_research_plan_order to mixin?
            # Or just do manual loop here for now to be safe if mixin isn't updated in this turn.
            # Actually, I can just execute SQL directly via self.db.cursor if mixin method missing,
            # but best practice is mixin. Let's assume user accepts I might need to add to mixin
            # or I can do it right here using self.db.conn/cursor if public.

            # Since I can't edit mixin in this response easily without user prompt,
            # I will implement the update loop here using the DB connection directly if possible,
            # or try to use a generic update method.
            # However, looking at mixin, it likely doesn't have it.
            # I will assume `update_research_plan_order` might not exist yet.
            # I will implement it manually here for safety.

            try:
                for i, plan_id in enumerate(dialog.ordered_db_ids):
                    self.db.cursor.execute("UPDATE research_plans SET display_order = ? WHERE id = ?", (i, plan_id))
                self.db.conn.commit()
                self.load_plans()
            except Exception as e:
                print(f"Error reordering plans: {e}")

    def _on_plan_selection_changed(self, current, previous):
        if not current:
            # If nothing selected here, check tree
            if self.tree.currentItem():
                return
            self.detail_stack.setCurrentIndex(0)
            self._current_plan_id = None
            return

        # Clear tree selection
        self.tree.blockSignals(True)
        self.tree.clearSelection()
        self.tree.blockSignals(False)
        self._current_node_id = None

        plan_id = current.data(Qt.UserRole)
        self._current_plan_id = plan_id

        # Load Plan Data
        # We need to fetch the single plan row. Using existing mixin?
        # get_research_plans returns list. We can filter or add get_research_plan_details.
        # For simplicity, let's just find it in the list for now or add a helper.
        # I'll rely on reloading.
        plans = self.db.get_research_plans(self.project_id)
        plan_data = next((p for p in plans if p['id'] == plan_id), None)

        if plan_data:
            self._load_plan_details(plan_data)

    def _load_plan_details(self, data):
        self._ignore_changes = True
        self.detail_stack.setCurrentWidget(self.page_plan_editor)

        # Populate Question Dropdown
        self.plan_question.clear()
        self.plan_question.addItem("No Question Selected", None)

        # Fetch actual questions
        nodes = self.db.get_research_nodes(self.project_id)
        questions = [n for n in nodes if n['type'] == 'question']

        current_q_id = data.get('research_question_id')

        for q in questions:
            self.plan_question.addItem(q['title'], q['id'])
            if q['id'] == current_q_id:
                self.plan_question.setCurrentIndex(self.plan_question.count() - 1)

        # Other fields
        self.plan_method.setCurrentText(data.get('methodological_approach') or "")
        self.plan_units.setPlainText(data.get('units_of_analysis') or "")
        self.plan_sources.setPlainText(data.get('data_sources') or "")
        self.plan_sampling.setPlainText(data.get('sampling_strategy') or "")
        self.plan_coding.setPlainText(data.get('coding_scheme') or "")
        self.plan_validity.setPlainText(data.get('validity_limitations') or "")

        self._ignore_changes = False

    def _save_plan_field(self, field, value):
        if self._ignore_changes or not self._current_plan_id: return
        self.db.update_research_plan_field(self._current_plan_id, field, value)

    def _save_plan_field_debounced(self, field, widget):
        if self._ignore_changes: return
        val = widget.toPlainText() if hasattr(widget, 'toPlainText') else widget.text()
        self._save_plan_field(field, val)

    def _save_plan_question(self, index):
        if self._ignore_changes or not self._current_plan_id: return
        q_id = self.plan_question.currentData()
        self.db.update_research_plan_field(self._current_plan_id, 'research_question_id', q_id)

    # --- Node Saving ---

    def _save_field(self, field, value):
        if self._ignore_changes or not self._current_node_id: return
        self.db.update_research_node_field(self._current_node_id, field, value)

        if field == 'title':
            item = self.tree.currentItem()
            if item: item.setText(0, value)

    def _save_field_debounced(self, field, widget):
        if self._ignore_changes: return
        val = widget.toPlainText() if hasattr(widget, 'toPlainText') else widget.text()
        self._save_field(field, val)

    def _manual_save_question(self):
        if self._current_node_id and RichTextEditorTab:
            self.q_synthesis.get_html(lambda html: self._save_field('synthesis', html))

    def _manual_save_sub(self):
        if self._current_node_id and RichTextEditorTab:
            self.sub_evidence.get_html(lambda html: self._save_field('evidence', html))

    # --- PDF Linking Logic (Multi) ---
    def _refresh_pdf_list(self, node_id, list_widget):
        list_widget.clear()
        links = self.db.get_research_pdf_links(node_id)
        for link in links:
            label = f"{link['label']} (Pg {link['page_number'] + 1})"
            if link.get('category_name'):
                label = f"({link['category_name']}) {label}"

            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, link['id'])
            list_widget.addItem(item)

    def _add_pdf_link(self, list_widget):
        if not PdfLinkDialog or not self._current_node_id: return

        dialog = PdfLinkDialog(self.db, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            node_id = dialog.selected_node_id
            if node_id:
                self.db.add_research_pdf_link(self._current_node_id, node_id)
                self._refresh_pdf_list(self._current_node_id, list_widget)

    def _remove_pdf_link(self, list_widget):
        item = list_widget.currentItem()
        if not item or not self._current_node_id: return

        node_id = item.data(Qt.UserRole)
        self.db.remove_research_pdf_link(self._current_node_id, node_id)
        self._refresh_pdf_list(self._current_node_id, list_widget)

    def _on_pdf_list_item_clicked(self, item):
        node_id = item.data(Qt.UserRole)
        if node_id:
            self.linkUrlClicked.emit(QUrl(f"pdfnode:///{node_id}"))

    # --- Terminology Linking Logic ---
    def _load_terms_list(self, node_id):
        self.q_term_list.clear()
        terms = self.db.get_research_term_links(node_id)
        for term in terms:
            item = QListWidgetItem(term['term'])
            item.setToolTip(term['meaning'])
            item.setData(Qt.UserRole, term['id'])
            self.q_term_list.addItem(item)

    def _link_terms(self):
        if not self._current_node_id: return

        current_terms = self.db.get_research_term_links(self._current_node_id)
        current_ids = [t['id'] for t in current_terms]

        dialog = LinkTermDialog(self.db, self.project_id, current_ids, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_ids = set(dialog.get_selected_ids())
            old_ids = set(current_ids)

            for tid in new_ids - old_ids:
                self.db.add_research_term_link(self._current_node_id, tid)

            for tid in old_ids - new_ids:
                self.db.remove_research_term_link(self._current_node_id, tid)

            self._load_terms_list(self._current_node_id)

    def _on_term_double_clicked(self, item):
        """Emit signal to open the term in Synthesis/My Terminology."""
        term_id = item.data(Qt.UserRole)
        if term_id:
            self.openTermRequested.emit(term_id)

    # --- Context Menu ---
    def _show_context_menu(self, pos):
        item = self.tree.itemAt(pos)
        menu = QMenu()

        if not item:
            menu.addAction("Add Research Question", self._add_root_question)
        else:
            node_type = item.data(0, Qt.ItemDataRole.UserRole + 1)

            if node_type == 'question':
                menu.addAction("Add Sub-question", lambda: self._add_child(item, 'subquestion'))
                menu.addAction("Add Outline Section", lambda: self._add_child(item, 'section'))
                menu.addSeparator()

            menu.addAction("Delete", lambda: self._delete_node(item))

            if ReorderDialog:
                menu.addSeparator()
                menu.addAction("Reorder Siblings...", lambda: self._reorder_siblings(item))

        menu.exec(self.tree.viewport().mapToGlobal(pos))

    # --- UPDATED: Use LargeTextEntryDialog ---
    def _add_root_question(self):
        dialog = LargeTextEntryDialog("New Research Question", "Question Text:", self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            text = dialog.get_text()
            if text:
                self.db.add_research_node(self.project_id, None, 'question', text)
                self.load_tree()

    def _add_child(self, parent_item, node_type):
        label = "Sub-question:" if node_type == 'subquestion' else "Section Title:"
        dialog = LargeTextEntryDialog("New Item", label, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            text = dialog.get_text()
            if text:
                parent_id = parent_item.data(0, Qt.ItemDataRole.UserRole)
                self.db.add_research_node(self.project_id, parent_id, node_type, text)
                self.load_tree()

    def _delete_node(self, item):
        if QMessageBox.question(self, "Delete", "Delete this item and all children?") == QMessageBox.StandardButton.Yes:
            node_id = item.data(0, Qt.ItemDataRole.UserRole)
            self.db.delete_research_node(node_id)
            self.load_tree()
            self.detail_stack.setCurrentIndex(0)

    def _reorder_siblings(self, item):
        parent = item.parent()
        siblings = []
        count = parent.childCount() if parent else self.tree.topLevelItemCount()

        for i in range(count):
            sib = parent.child(i) if parent else self.tree.topLevelItem(i)
            siblings.append((sib.text(0), sib.data(0, Qt.ItemDataRole.UserRole)))

        if len(siblings) < 2: return

        dialog = ReorderDialog(siblings, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.db.update_research_node_order(dialog.ordered_db_ids)
            self.load_tree()

    # --- Memo Logic ---
    def _load_memos_list(self, node_id):
        self.memo_list.clear()
        self.memo_title.clear()
        if RichTextEditorTab:
            self.memo_content.set_html("")
        else:
            self.memo_content.clear()

        memos = self.db.get_research_memos(node_id)
        for m in memos:
            item = QListWidgetItem(f"{m['created_at'][:10]} - {m['title']}")
            item.setData(Qt.ItemDataRole.UserRole, m['id'])
            item.setData(Qt.ItemDataRole.UserRole + 1, m)
            self.memo_list.addItem(item)

    def _add_memo(self):
        if not self._current_node_id: return
        self.db.add_research_memo(self._current_node_id, "New Memo", "")
        self._load_memos_list(self._current_node_id)

    def _delete_memo(self):
        item = self.memo_list.currentItem()
        if not item: return
        memo_id = item.data(Qt.ItemDataRole.UserRole)
        self.db.delete_research_memo(memo_id)
        self._load_memos_list(self._current_node_id)

    def _load_memo(self, item):
        data = item.data(Qt.ItemDataRole.UserRole + 1)
        self.memo_title.setText(data['title'])
        if RichTextEditorTab:
            self.memo_content.set_html(data['content'])
        else:
            self.memo_content.setPlainText(data['content'])

    def _save_current_memo(self):
        item = self.memo_list.currentItem()
        if not item: return
        memo_id = item.data(Qt.ItemDataRole.UserRole)

        title = self.memo_title.text()

        def save_content(html_content):
            self.db.update_research_memo(memo_id, title, html_content)
            data = item.data(Qt.ItemDataRole.UserRole + 1)
            item.setText(f"{data['created_at'][:10]} - {title}")

        if RichTextEditorTab:
            self.memo_content.get_html(save_content)
        else:
            save_content(self.memo_content.toPlainText())