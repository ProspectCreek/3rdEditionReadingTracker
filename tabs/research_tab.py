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

    def __init__(self, title, label_text, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(600)  # Wider
        self.setMinimumHeight(250)  # Taller

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(label_text))

        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("Type text here...")
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
        self._ignore_changes = False

        self._setup_ui()
        self.load_tree()

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(self.splitter)

        # --- Left Panel: Tree ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(4, 4, 4, 4)

        left_label = QLabel("Research Structure")
        left_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #555;")
        left_layout.addWidget(left_label)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        self.tree.currentItemChanged.connect(self._on_tree_selection_changed)
        left_layout.addWidget(self.tree)

        # Add Button Bar
        btn_layout = QHBoxLayout()
        self.btn_add_root = QPushButton("Add Question")
        self.btn_add_root.clicked.connect(self._add_root_question)
        btn_layout.addWidget(self.btn_add_root)
        left_layout.addLayout(btn_layout)

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

        right_layout.addWidget(self.detail_stack)

        self.splitter.addWidget(left_panel)
        self.splitter.addWidget(right_panel)
        self.splitter.setSizes([300, 700])

    def _create_question_page(self):
        """Creates the UI page for a Research Question (Parent)."""
        page = QWidget()
        layout = QVBoxLayout(page)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        form = QFormLayout(content)

        # --- 1. Title (Wider) ---
        self.q_title = QTextEdit()
        self.q_title.setMinimumHeight(100)  # Increased height
        self.q_title.setPlaceholderText("Research Question...")
        self.q_title.textChanged.connect(lambda: self._save_field_debounced('title', self.q_title))
        form.addRow("Question:", self.q_title)

        # --- 2. PDF Links (Multi) ---
        pdf_group = QGroupBox("Linked PDF Nodes")
        pdf_layout = QVBoxLayout(pdf_group)

        self.q_pdf_list = QListWidget()
        self.q_pdf_list.setMinimumHeight(150)  # Taller viewer
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

        # --- 3. Standard Fields ---
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

        # --- 4. Key Terms (List instead of Textbox) ---
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

        # --- 5. Syntopical Group ---
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

        # Rich Text for Synthesis
        if RichTextEditorTab:
            self.q_synthesis = RichTextEditorTab("Synthesis", spell_checker_service=self.spell_checker_service)
            self.q_synthesis.setMinimumHeight(200)
        else:
            self.q_synthesis = QTextEdit()
            self.q_synthesis.setMinimumHeight(100)

        syn_layout.addRow("My Synthesis:", self.q_synthesis)
        form.addRow(syn_group)

        # --- 6. Memos Section ---
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
            self.memo_content.setMinimumHeight(300)  # Taller body
        else:
            self.memo_content = QTextEdit()
            self.memo_content.setMinimumHeight(200)
        memo_layout.addWidget(self.memo_content)

        form.addRow(memo_group)

        scroll.setWidget(content)
        layout.addWidget(scroll)

        # Add save button for rich text fields
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

        # --- 1. Title (Wider) ---
        self.sub_text = QTextEdit()
        self.sub_text.setMinimumHeight(100)  # Increased height
        self.sub_text.setPlaceholderText("Sub-question text...")
        self.sub_text.textChanged.connect(lambda: self._save_field_debounced('title', self.sub_text))
        form.addRow("Sub-question:", self.sub_text)

        # --- 2. PDF Links (Multi) ---
        pdf_group = QGroupBox("Linked PDF Nodes")
        pdf_layout = QVBoxLayout(pdf_group)

        self.sub_pdf_list = QListWidget()
        # Requirement: Taller node viewer
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

        # --- 3. Standard Fields ---
        self.sub_role = QComboBox()
        self.sub_role.setEditable(True)
        self.sub_role.addItems(["Mechanism", "Context", "Case Study", "Comparison", "Evidence", "Counter-argument"])
        self.sub_role.currentTextChanged.connect(lambda t: self._save_field('role', t))
        form.addRow("Role:", self.sub_role)

        # Rich Text for Evidence (supports PDF linking)
        if RichTextEditorTab:
            self.sub_evidence = RichTextEditorTab("Key Evidence", spell_checker_service=self.spell_checker_service)
            self.sub_evidence.setMinimumHeight(200)
            # Forward signal to dashboard
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
            self.detail_stack.setCurrentIndex(0)
            self._current_node_id = None
            return

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