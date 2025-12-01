import sys
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QListWidget, QListWidgetItem,
    QLabel, QTextEdit, QFrame, QPushButton, QMessageBox, QMenu, QInputDialog,
    QGroupBox, QScrollArea, QDialog, QDialogButtonBox, QStackedWidget
)
from PySide6.QtCore import Qt, Signal, Slot, QUrl
from PySide6.QtGui import QAction

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


class LargeTextEntryDialog(QDialog):
    """
    A dialog with a large QTextEdit for entering comprehensive text.
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


class EvidenceMatrixTab(QWidget):
    """
    Tab for the Evidence Matrix feature.
    Layout: Left (Theme List), Right (Three-Column Matrix: Author Evidence, Data Evidence, Interpretation)
    """

    linkUrlClicked = Signal(QUrl)

    def __init__(self, db, project_id, spell_checker_service=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.project_id = project_id
        self.spell_checker_service = spell_checker_service

        self._current_theme_id = None
        self._ignore_changes = False

        self._setup_ui()
        self.load_themes()

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(self.splitter)

        # --- Left Panel: Theme List ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(4, 4, 4, 4)

        left_label = QLabel("Themes")
        left_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #555;")
        left_layout.addWidget(left_label)

        self.theme_list = QListWidget()
        self.theme_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.theme_list.customContextMenuRequested.connect(self._show_context_menu)
        self.theme_list.currentItemChanged.connect(self._on_theme_selection_changed)
        left_layout.addWidget(self.theme_list)

        btn_add = QPushButton("Add Theme")
        btn_add.clicked.connect(self._add_theme)
        left_layout.addWidget(btn_add)

        self.splitter.addWidget(left_panel)

        # --- Right Panel: Matrix ---
        self.right_panel = QStackedWidget()

        # 0: Empty State
        self.page_empty = QLabel("Select a theme to view the evidence matrix.")
        self.page_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_empty.setStyleSheet("color: #888; font-style: italic;")
        self.right_panel.addWidget(self.page_empty)

        # 1: Matrix Editor
        self.page_matrix = self._create_matrix_page()
        self.right_panel.addWidget(self.page_matrix)

        self.splitter.addWidget(self.right_panel)
        self.splitter.setSizes([250, 750])

    def _create_matrix_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        # Matrix Header
        self.matrix_label = QLabel("Evidence Matrix")
        self.matrix_label.setStyleSheet("font-weight: bold; font-size: 16px; margin: 10px;")
        layout.addWidget(self.matrix_label)

        # Three-column grid using Splitter or HBox
        # Using HBox with Frames for clear column distinction
        matrix_layout = QHBoxLayout()
        matrix_layout.setSpacing(10)

        # Column A: Author Evidence
        col_a = self._create_column_widget("Author Evidence", "author_evidence", link_type='author')
        self.author_evidence_edit = col_a['editor']
        self.author_pdf_list = col_a['pdf_list']
        matrix_layout.addWidget(col_a['widget'])

        # Column B: Data Evidence
        col_b = self._create_column_widget("Data Evidence", "data_evidence", link_type='data')
        self.data_evidence_edit = col_b['editor']
        self.data_pdf_list = col_b['pdf_list']
        matrix_layout.addWidget(col_b['widget'])

        # Column C: Interpretation
        col_c = self._create_column_widget("Interpretation", "interpretation", link_type=None)
        self.interpretation_edit = col_c['editor']
        matrix_layout.addWidget(col_c['widget'])

        layout.addLayout(matrix_layout)
        return page

    def _create_column_widget(self, title, field_name, link_type=None):
        widget = QFrame()
        widget.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)

        # Header
        lbl = QLabel(title)
        lbl.setStyleSheet("font-weight: bold; font-size: 14px; color: #333; margin-bottom: 5px;")
        layout.addWidget(lbl)

        # Editor
        editor = QTextEdit()
        editor.setAcceptRichText(False)  # Keep it simple multiline text as requested? Or Rich?
        # User requested multiline text. Let's stick to QTextEdit.
        # But if they want to bold things, RichText is better.
        # Let's use basic QTextEdit for now as "Type: multiline text" usually implies plain text,
        # but consistency with app might suggest RichText.
        # Given "font/spacing as rest of app", standard QTextEdit matches other input fields nicely.
        editor.textChanged.connect(lambda: self._save_field_debounced(field_name, editor))
        layout.addWidget(editor)

        pdf_list = None
        if link_type:
            # PDF Links Section
            pdf_group = QGroupBox("Linked PDF Nodes")
            pdf_layout = QVBoxLayout(pdf_group)

            pdf_list_widget = QListWidget()
            pdf_list_widget.setMaximumHeight(150)
            pdf_list_widget.itemDoubleClicked.connect(self._on_pdf_list_item_clicked)
            pdf_list_widget.setToolTip("Double-click to jump to PDF")
            pdf_layout.addWidget(pdf_list_widget)

            btn_layout = QHBoxLayout()
            btn_add = QPushButton("Add Link")
            btn_add.clicked.connect(lambda: self._add_pdf_link(pdf_list_widget, link_type))
            btn_remove = QPushButton("Remove")
            btn_remove.clicked.connect(lambda: self._remove_pdf_link(pdf_list_widget, link_type))

            btn_layout.addWidget(btn_add)
            btn_layout.addWidget(btn_remove)
            pdf_layout.addLayout(btn_layout)

            layout.addWidget(pdf_group)
            pdf_list = pdf_list_widget

        return {'widget': widget, 'editor': editor, 'pdf_list': pdf_list}

    # --- Theme Management ---

    def load_themes(self):
        self.theme_list.clear()
        themes = self.db.get_evidence_matrix_themes(self.project_id)
        for t in themes:
            item = QListWidgetItem(t['title'])
            item.setData(Qt.UserRole, t['id'])
            self.theme_list.addItem(item)

    def _add_theme(self):
        # Use LargeTextEntryDialog instead of QInputDialog for wider field
        dialog = LargeTextEntryDialog("New Theme", "Enter Theme Title:", self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            title = dialog.get_text()
            if title:
                self.db.add_evidence_matrix_theme(self.project_id, title)
                self.load_themes()

    def _show_context_menu(self, pos):
        item = self.theme_list.itemAt(pos)
        menu = QMenu()
        menu.addAction("Add Theme", self._add_theme)

        if item:
            menu.addSeparator()
            menu.addAction("Rename Theme", self._rename_theme)
            menu.addAction("Delete Theme", self._delete_theme)

            if ReorderDialog:
                menu.addSeparator()
                menu.addAction("Reorder Themes...", self._reorder_themes)

        menu.exec(self.theme_list.viewport().mapToGlobal(pos))

    def _rename_theme(self):
        item = self.theme_list.currentItem()
        if not item: return
        theme_id = item.data(Qt.UserRole)

        # Use LargeTextEntryDialog instead of QInputDialog
        dialog = LargeTextEntryDialog("Rename Theme", "New Title:", self, default_text=item.text())
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_title = dialog.get_text()
            if new_title:
                self.db.update_evidence_matrix_theme_field(theme_id, 'title', new_title)
                self.load_themes()

    def _delete_theme(self):
        item = self.theme_list.currentItem()
        if not item: return
        theme_id = item.data(Qt.UserRole)

        if QMessageBox.question(self, "Delete",
                                "Delete this theme and all its evidence?") == QMessageBox.StandardButton.Yes:
            self.db.delete_evidence_matrix_theme(theme_id)
            self.load_themes()
            if self._current_theme_id == theme_id:
                self.right_panel.setCurrentIndex(0)
                self._current_theme_id = None

    def _reorder_themes(self):
        if not ReorderDialog: return
        themes = []
        for i in range(self.theme_list.count()):
            item = self.theme_list.item(i)
            themes.append((item.text(), item.data(Qt.UserRole)))

        if len(themes) < 2: return

        dialog = ReorderDialog(themes, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.db.update_evidence_matrix_theme_order(dialog.ordered_db_ids)
            self.load_themes()

    def _on_theme_selection_changed(self, current, previous):
        if not current:
            self.right_panel.setCurrentIndex(0)
            self._current_theme_id = None
            return

        theme_id = current.data(Qt.UserRole)
        self._current_theme_id = theme_id

        # Load Theme Data
        # We need fetch theme details. The mixin returns all.
        # Ideally we'd have get_theme_details(id), but filtering is fine for small sets.
        themes = self.db.get_evidence_matrix_themes(self.project_id)
        theme_data = next((t for t in themes if t['id'] == theme_id), None)

        if theme_data:
            self._load_matrix_content(theme_data)

    def _load_matrix_content(self, data):
        self._ignore_changes = True
        self.right_panel.setCurrentWidget(self.page_matrix)
        self.matrix_label.setText(f"Evidence Matrix: {data['title']}")

        self.author_evidence_edit.setPlainText(data['author_evidence'] or "")
        self.data_evidence_edit.setPlainText(data['data_evidence'] or "")
        self.interpretation_edit.setPlainText(data['interpretation'] or "")

        self._refresh_pdf_list(self.author_pdf_list, 'author')
        self._refresh_pdf_list(self.data_pdf_list, 'data')

        self._ignore_changes = False

    def _save_field_debounced(self, field, widget):
        if self._ignore_changes or not self._current_theme_id: return
        val = widget.toPlainText()
        self.db.update_evidence_matrix_theme_field(self._current_theme_id, field, val)

    # --- PDF Linking ---

    def _refresh_pdf_list(self, list_widget, link_type):
        if not list_widget or not self._current_theme_id: return
        list_widget.clear()
        links = self.db.get_evidence_matrix_pdf_links(self._current_theme_id, link_type)
        for link in links:
            label = f"{link['label']} (Pg {link['page_number'] + 1})"
            if link.get('category_name'):
                label = f"({link['category_name']}) {label}"

            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, link['id'])  # pdf_node_id is in link['id'] if we select n.* which includes id
            # Wait, PDF Node ID is n.id. Link table has (theme_id, pdf_node_id).
            # The query select n.*, so 'id' is pdf_node_id. Correct.
            list_widget.addItem(item)

    def _add_pdf_link(self, list_widget, link_type):
        if not PdfLinkDialog or not self._current_theme_id: return

        dialog = PdfLinkDialog(self.db, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            node_id = dialog.selected_node_id
            if node_id:
                self.db.add_evidence_matrix_pdf_link(self._current_theme_id, node_id, link_type)
                self._refresh_pdf_list(list_widget, link_type)

    def _remove_pdf_link(self, list_widget, link_type):
        item = list_widget.currentItem()
        if not item or not self._current_theme_id: return

        node_id = item.data(Qt.UserRole)
        self.db.remove_evidence_matrix_pdf_link(self._current_theme_id, node_id, link_type)
        self._refresh_pdf_list(list_widget, link_type)

    def _on_pdf_list_item_clicked(self, item):
        node_id = item.data(Qt.UserRole)
        if node_id:
            self.linkUrlClicked.emit(QUrl(f"pdfnode:///{node_id}"))