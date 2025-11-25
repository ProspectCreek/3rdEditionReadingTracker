# widgets/project_dashboard_widget.py
import sys
import os
import subprocess
import traceback
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTabWidget, QSplitter, QLabel, QTreeWidget,
    QFrame, QDialog, QTreeWidgetItem, QMenuBar,
    QMessageBox, QMenu, QApplication, QFileDialog,
    QHeaderView, QStyledItemDelegate, QStyle, QStyleOptionViewItem
)
from PySide6.QtCore import Qt, Signal, Slot, QTimer, QPoint, QUrl, QSize, QRectF
from PySide6.QtGui import (
    QAction, QIcon, QPixmap, QPainter, QDesktopServices,
    QTextDocument, QAbstractTextDocumentLayout, QPalette, QColor, QTextCharFormat
)
from PySide6.QtSvg import QSvgRenderer

# Import all the tab types
from tabs.project_editor_tab import ProjectEditorTab
from tabs.rich_text_editor_tab import RichTextEditorTab
from tabs.mindmap_tab import MindmapTab
from tabs.assignment_tab import AssignmentTab
from tabs.reading_notes_tab import ReadingNotesTab, DEFAULT_READING_RULES_HTML
from tabs.synthesis_tab import SynthesisTab, DEFAULT_SYNTOPIC_RULES_HTML
from tabs.graph_view_tab import GraphViewTab
from tabs.todo_list_tab import TodoListTab

try:
    from dialogs.add_reading_dialog import AddReadingDialog
    from dialogs.edit_instructions_dialog import EditInstructionsDialog
    from dialogs.reorder_dialog import ReorderDialog
except ImportError:
    print("Error: Could not import Dialogs")
    sys.exit(1)

try:
    from dialogs.export_project_dialog import ExportProjectDialog
except ImportError:
    ExportProjectDialog = None

try:
    from utils.export_engine import ExportEngine
except ImportError:
    ExportEngine = None

try:
    from dialogs.edit_syntopic_rules_dialog import EditSyntopicRulesDialog
except ImportError:
    EditSyntopicRulesDialog = None

try:
    from dialogs.edit_reading_rules_dialog import EditReadingRulesDialog
except ImportError:
    EditReadingRulesDialog = None

# --- UPDATED IMPORT BLOCK FOR DEBUGGING ---
try:
    from tabs.pdf_node_viewer import PdfNodeViewer
except ImportError as e:
    print("-" * 60)
    print("CRITICAL ERROR: Could not import PdfNodeViewer.")
    print(f"Error Details: {e}")
    traceback.print_exc()  # This prints the file and line number
    print("-" * 60)
    PdfNodeViewer = None
# ------------------------------------------

try:
    from dialogs.pdf_link_dialog import PdfLinkDialog
except ImportError:
    print("Error: Could not import PdfLinkDialog")
    PdfLinkDialog = None


# --- Word Wrap Delegate (FIXED FOR COMPACTNESS & COLOR & WRAPPING) ---
class WordWrapDelegate(QStyledItemDelegate):
    """
    A delegate that renders HTML/Rich text with wrapping in a QTreeWidget.
    """

    def paint(self, painter, option, index):
        # Use QStyleOptionViewItem directly
        if isinstance(option, QStyleOptionViewItem):
            opt = QStyleOptionViewItem(option)
        else:
            opt = QStyleOptionViewItem()
        self.initStyleOption(opt, index)

        painter.save()

        doc = QTextDocument()
        doc.setHtml(opt.text)
        doc.setDefaultFont(opt.font)

        # Remove default margins for compactness
        doc.setDocumentMargin(0)

        # --- CHANGE 1: RIGHT PADDING ---
        # Subtract total horizontal padding (Left + Right) from the available width.
        horizontal_padding = 20
        doc.setTextWidth(opt.rect.width() - horizontal_padding)

        # Handle Selection Highlight manually to match the light theme
        if opt.state & QStyle.State_Selected:
            # Use a soft, light blue instead of the system dark blue
            painter.fillRect(opt.rect, QColor("#E5F3FF"))
            # Ensure text is black by default for the doc

        # Calculate Vertical Centering
        content_height = doc.size().height()
        rect_height = opt.rect.height()
        y_offset = (rect_height - content_height) / 2

        # Clamp to 0 if content is larger than rect (shouldn't happen with sizeHint, but safe)
        if y_offset < 0: y_offset = 0

        # --- CHANGE 2: LEFT PADDING ---
        left_padding = 10
        painter.translate(opt.rect.left() + left_padding, opt.rect.top() + y_offset)

        # Draw the text
        doc.drawContents(painter)

        painter.restore()

    def sizeHint(self, option, index):
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)

        doc = QTextDocument()
        doc.setHtml(opt.text)
        doc.setDefaultFont(opt.font)
        doc.setDocumentMargin(0)

        # --- FIX 1: Get the actual column width from the TreeWidget ---
        # This ensures sizeHint calculates the height based on the REAL column width,
        # forcing the row to expand vertically if the text wraps.
        tree_widget = option.widget
        if tree_widget:
            column_width = tree_widget.columnWidth(index.column())
            # --- CHANGE 3: MATCH PADDING ---
            doc.setTextWidth(column_width - 20)
        else:
            doc.setTextWidth(opt.rect.width())
        # ---------------------------------------------------------------

        vertical_padding = 14
        return QSize(int(doc.idealWidth()), int(doc.size().height()) + vertical_padding)
    # --- END DELEGATE ---


class ProjectDashboardWidget(QWidget):
    """Main project dashboard page (native editors, compact, true 50/50)."""
    returnToHome = Signal()

    def __init__(self, db_manager, spell_checker_service=None, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.spell_checker_service = spell_checker_service
        self.project_details = None
        self.project_id = -1
        self.bottom_tabs = []
        self.reading_tabs = {}  # Stores {reading_id: ReadingNotesTab}
        self.synthesis_tab = None
        self.graph_view_tab = None
        self.todo_list_tab = None
        self.assignment_tab = None
        self.mindmaps_tab = None

        # Store open PDF viewers to prevent garbage collection
        self.pdf_viewers = []  # List of PdfNodeViewer instances

        self._programmatic_tab_change = False

        # --- Book Icon ---
        self.book_icon = QIcon()
        book_svg = """
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
          <path d="M20 5v14.5a.5.5 0 0 1-.5.5h-15a.5.5 0 0 1-.5-.5v-16a.5.5 0 0 1 .5-.5H19a1 1 0 0 1 1 1zm-1-2H4.5a2.5 2.5 0 0 0-2.5 2.5v16A2.5 2.5 0 0 0 4.5 22h15a2.5 2.5 0 0 0 2.5-2.5V5a3 3 0 0 0-3-3z"/>
          <path d="M6 8.5h8v-1H6v1zm6 3H6v-1h6v1zm-6 3h8v-1H6v1z"/>
        </svg>
        """
        renderer = QSvgRenderer(book_svg.encode('utf-8'))
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        self.book_icon = QIcon(pixmap)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.menu_bar = QMenuBar()
        main_layout.addWidget(self.menu_bar)

        button_bar = QWidget()
        button_bar.setStyleSheet("background-color:#f0f0f0; padding:4px;")
        button_layout = QHBoxLayout(button_bar)
        button_layout.setContentsMargins(6, 2, 6, 2)

        btn_return_home = QPushButton("Return to Projects Home Screen")

        # --- MODIFIED: Add Launch QDA Tool button ---
        btn_launch_qda = QPushButton("Launch QDA Tool")

        btn_add_reading = QPushButton("Add Reading")

        btn_return_home.clicked.connect(self.return_to_home)
        btn_launch_qda.clicked.connect(self.launch_qda_tool)
        btn_add_reading.clicked.connect(self.add_reading)

        button_layout.addWidget(btn_return_home)
        button_layout.addWidget(btn_launch_qda)
        button_layout.addWidget(btn_add_reading)
        button_layout.addStretch()
        main_layout.addWidget(button_bar)

        self.top_tab_widget = QTabWidget()
        main_layout.addWidget(self.top_tab_widget)

        self.dashboard_tab = QWidget()
        self._build_dashboard_tab()

        self.top_tab_widget.currentChanged.connect(self.on_top_tab_changed)
        QTimer.singleShot(0, self._enforce_equal_splits)

    @Slot()
    def launch_qda_tool(self):
        """
        Launches the separate QDA Coding App via subprocess.
        Sets the CWD to the qda_tool directory so it finds its logo and DB.
        """
        try:
            # Calculate path: root/widgets/project_dashboard_widget.py -> root/qda_tool/qda_coding_app.py
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            qda_dir = os.path.join(base_dir, 'qda_tool')
            script_name = "qda_coding_app.py"
            script_path = os.path.join(qda_dir, script_name)

            if not os.path.exists(script_path):
                QMessageBox.critical(self, "Error", f"Could not find QDA Tool at:\n{script_path}")
                return

            # Launch as a separate process
            subprocess.Popen([sys.executable, script_name], cwd=qda_dir)

        except Exception as e:
            QMessageBox.critical(self, "Launch Error", f"Failed to launch QDA Tool:\n{e}")

    def _build_dashboard_tab(self):
        """Top/Bottom split, each half left/right split — all equal on show."""
        outer = QVBoxLayout(self.dashboard_tab)
        outer.setContentsMargins(4, 4, 4, 4)
        outer.setSpacing(4)

        self.main_splitter = QSplitter(Qt.Orientation.Vertical)
        self.main_splitter.setHandleWidth(4)
        outer.addWidget(self.main_splitter)

        # ----- Top half -----
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(4, 4, 4, 4)
        top_layout.setSpacing(4)

        self.top_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.top_splitter.setHandleWidth(4)
        top_layout.addWidget(self.top_splitter)

        # Left: Readings viewer
        readings_widget = QFrame()
        readings_widget.setFrameShape(QFrame.Shape.StyledPanel)
        rl = QVBoxLayout(readings_widget)
        rl.setContentsMargins(6, 6, 6, 6)
        rl.setSpacing(6)
        rl.addWidget(QLabel("Readings"))

        self.readings_tree = QTreeWidget()
        self.readings_tree.setHeaderLabels(["Nickname", "Title", "Author"])
        self.readings_tree.setStyleSheet("""
            QTreeView::item {
                padding-top: 0px;
                padding-bottom: 0px;
            }
        """)

        # Use WordWrapDelegate for ALL columns
        delegate = WordWrapDelegate(self.readings_tree)
        self.readings_tree.setItemDelegate(delegate)

        # Formatting logic
        self.readings_tree.setWordWrap(True)
        self.readings_tree.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.readings_tree.setUniformRowHeights(False)  # Allow variable height for wrapping
        self.readings_tree.setSortingEnabled(False)

        header = self.readings_tree.header()
        header.setStretchLastSection(False)

        # --- FIX 2: Enable Interactive Resizing for ALL columns ---

        # Column 0 (Nickname): Interactive
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.readings_tree.setColumnWidth(0, 220)

        # Column 1 (Title): Interactive (Changed from Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.readings_tree.setColumnWidth(1, 550)

        # Column 2 (Author): Interactive (Changed from Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.readings_tree.setColumnWidth(2, 120)
        # ----------------------------------------------------------

        rl.addWidget(self.readings_tree)

        self.readings_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.readings_tree.customContextMenuRequested.connect(self.show_readings_context_menu)
        self.readings_tree.itemDoubleClicked.connect(self.on_reading_double_clicked)

        # Right: Purpose + Goals
        info_widget = QFrame()
        info_widget.setFrameShape(QFrame.Shape.StyledPanel)
        il = QVBoxLayout(info_widget)
        il.setContentsMargins(6, 6, 6, 6)
        il.setSpacing(6)
        il.addWidget(QLabel("Project Purpose"))
        self.purpose_text_editor = RichTextEditorTab("Project Purpose",
                                                     spell_checker_service=self.spell_checker_service)
        il.addWidget(self.purpose_text_editor)
        il.addWidget(QLabel("My Goals"))
        self.goals_text_editor = RichTextEditorTab("Project Goals", spell_checker_service=self.spell_checker_service)
        il.addWidget(self.goals_text_editor)

        # --- NEW: Connect link to PDF signal ---
        self.purpose_text_editor.linkPdfNodeTriggered.connect(
            lambda: self._on_link_pdf_node_triggered(self.purpose_text_editor))
        self.goals_text_editor.linkPdfNodeTriggered.connect(
            lambda: self._on_link_pdf_node_triggered(self.goals_text_editor))
        self.purpose_text_editor.editor.smartAnchorClicked.connect(self._on_editor_link_clicked)
        self.goals_text_editor.editor.smartAnchorClicked.connect(self._on_editor_link_clicked)
        # --- END NEW ---

        self.top_splitter.addWidget(readings_widget)
        self.top_splitter.addWidget(info_widget)
        self.top_splitter.setStretchFactor(0, 1)
        self.top_splitter.setStretchFactor(1, 1)

        # ----- Bottom half -----
        bottom_widget = QFrame()
        bottom_widget.setFrameShape(QFrame.Shape.StyledPanel)
        bl = QVBoxLayout(bottom_widget)
        bl.setContentsMargins(6, 6, 6, 6)
        bl.setSpacing(6)
        self.editor_tab_widget = QTabWidget()
        bl.addWidget(self.editor_tab_widget)

        self.editor_tab_widget.currentChanged.connect(self.save_all_editors)

        self.main_splitter.addWidget(top_widget)
        self.main_splitter.addWidget(bottom_widget)
        self.main_splitter.setStretchFactor(0, 1)
        self.main_splitter.setStretchFactor(1, 1)

    def _enforce_equal_splits(self):
        """Force true 50/50 splits once widgets have sizes."""
        try:
            total_h = max(2, self.main_splitter.size().height())
            self.main_splitter.setSizes([total_h // 2, total_h - total_h // 2])
            total_w = max(2, self.top_splitter.size().width())
            self.top_splitter.setSizes([total_w // 2, total_w - total_w // 2])
        except Exception as e:
            print(f"Warning: Could not enforce splits: {e}")

    def load_project(self, project_details):
        try:
            self.top_tab_widget.currentChanged.disconnect()
        except RuntimeError:
            pass
        try:
            self.editor_tab_widget.currentChanged.disconnect()
        except RuntimeError:
            pass

        self.project_details = dict(project_details)
        self.project_id = self.project_details['id']

        self.top_tab_widget.clear()
        self.editor_tab_widget.clear()
        self.menu_bar.clear()
        self.bottom_tabs.clear()
        self.reading_tabs.clear()
        self.synthesis_tab = None
        self.graph_view_tab = None
        self.todo_list_tab = None
        self.assignment_tab = None
        self.mindmaps_tab = None

        settings_menu = self.menu_bar.addMenu("Settings")

        edit_instr_action = QAction("Edit Dashboard Instructions", self)
        edit_instr_action.triggered.connect(self.open_edit_instructions)
        settings_menu.addAction(edit_instr_action)

        edit_read_rules_action = QAction("Edit Reading Rules...", self)
        if EditReadingRulesDialog:
            edit_read_rules_action.setEnabled(True)
            edit_read_rules_action.triggered.connect(self._edit_reading_rules)
        else:
            edit_read_rules_action.setEnabled(False)
        settings_menu.addAction(edit_read_rules_action)

        edit_syntopic_action = QAction("Edit Syntopic Guidelines...", self)
        if EditSyntopicRulesDialog:
            edit_syntopic_action.setEnabled(True)
            edit_syntopic_action.triggered.connect(self._edit_syntopic_rules)
        else:
            edit_syntopic_action.setEnabled(False)
        settings_menu.addAction(edit_syntopic_action)

        export_menu = self.menu_bar.addMenu("Export")
        export_action = QAction("Export Project...", self)
        export_action.triggered.connect(self._open_export_dialog)
        export_menu.addAction(export_action)

        self.top_tab_widget.addTab(self.dashboard_tab, "Project Dashboard")

        if self.project_details.get('is_assignment', 0) == 1:
            self.assignment_tab = AssignmentTab(self.db, self.project_id,
                                                spell_checker_service=self.spell_checker_service)
            self.top_tab_widget.addTab(self.assignment_tab, "Assignment")
            # --- NEW: Connect Assignment Editors ---
            self.assignment_tab.instructions_editor.linkPdfNodeTriggered.connect(
                lambda: self._on_link_pdf_node_triggered(self.assignment_tab.instructions_editor))
            self.assignment_tab.draft_editor.linkPdfNodeTriggered.connect(
                lambda: self._on_link_pdf_node_triggered(self.assignment_tab.draft_editor))
            self.assignment_tab.instructions_editor.editor.smartAnchorClicked.connect(self._on_editor_link_clicked)
            self.assignment_tab.draft_editor.editor.smartAnchorClicked.connect(self._on_editor_link_clicked)
            # --- END NEW ---

        self.mindmaps_tab = MindmapTab(self.db, self.project_id)
        self.top_tab_widget.addTab(self.mindmaps_tab, "Mindmaps")

        self.synthesis_tab = SynthesisTab(self.db, self.project_id,
                                          spell_checker_service=self.spell_checker_service)
        self.synthesis_tab.openReading.connect(self.open_reading_tab)
        self.synthesis_tab.tagsUpdated.connect(self._on_tags_updated)
        self.top_tab_widget.addTab(self.synthesis_tab, "Synthesis")

        # --- NEW: Connect Synthesis Editors ---
        if hasattr(self.synthesis_tab, 'notes_editor'):
            self.synthesis_tab.notes_editor.linkPdfNodeTriggered.connect(
                lambda: self._on_link_pdf_node_triggered(self.synthesis_tab.notes_editor))
            self.synthesis_tab.notes_editor.editor.smartAnchorClicked.connect(self._on_editor_link_clicked)
        # --- END NEW ---

        self.graph_view_tab = GraphViewTab(self.db, self.project_id)
        self.graph_view_tab.readingDoubleClicked.connect(self.open_reading_tab)
        self.graph_view_tab.tagDoubleClicked.connect(self.open_tag_from_graph)
        self.graph_view_tab.tagsUpdated.connect(self._on_tags_updated)
        self.top_tab_widget.addTab(self.graph_view_tab, "Connections")

        self.todo_list_tab = TodoListTab(self.db, self.project_id)
        self.top_tab_widget.addTab(self.todo_list_tab, "To-Do List")

        self.load_readings()

        readings = self.db.get_readings(self.project_id)
        for reading in readings:
            self._create_and_add_reading_tab(reading, set_current=False)

        fields = [
            ("Key Questions", "key_questions_text"),
            ("Thesis/Argument", "thesis_text"),
            ("Key Insights", "insights_text"),
            ("Unresolved Questions", "unresolved_text")
        ]
        for tab_title, field_name in fields:
            editor_tab = ProjectEditorTab(self.db, self.project_id, field_name,
                                          spell_checker_service=self.spell_checker_service)
            self.editor_tab_widget.addTab(editor_tab, tab_title)
            self.bottom_tabs.append(editor_tab)

            # --- NEW: Connect Bottom Tab Editors ---
            editor_tab.editor.linkPdfNodeTriggered.connect(
                lambda e=editor_tab.editor: self._on_link_pdf_node_triggered(e))
            editor_tab.editor.editor.smartAnchorClicked.connect(self._on_editor_link_clicked)
            # --- END NEW ---

        QTimer.singleShot(0, self._enforce_equal_splits)

        self.top_tab_widget.currentChanged.connect(self.on_top_tab_changed)
        self.editor_tab_widget.currentChanged.connect(self.save_all_editors)

    def load_all_editor_content(self):
        if not self.project_details:
            return

        print("Loading all editor content...")
        try:
            self.purpose_text_editor.set_html(self.project_details.get('project_purpose_text', ''))
            self.goals_text_editor.set_html(self.project_details.get('project_goals_text', ''))

            for tab in self.bottom_tabs:
                html_content = self.project_details.get(tab.text_field, '')
                if hasattr(tab, 'set_html'):
                    tab.set_html(html_content)

            if hasattr(self, 'assignment_tab') and isinstance(self.assignment_tab, AssignmentTab):
                self.assignment_tab.load_data(self.project_details)

            if self.synthesis_tab:
                self.synthesis_tab.load_tab_data(self.project_details)

            if self.todo_list_tab:
                self.todo_list_tab.load_items()

            for tab in self.reading_tabs.values():
                tab.load_data()

        except Exception as e:
            QMessageBox.critical(self, "Error Loading Content", f"Error: {e}")
            import traceback
            traceback.print_exc()

    def load_readings(self):
        self.readings_tree.clear()
        readings = self.db.get_readings(self.project_id)
        for r in readings:
            nickname = (r['nickname'] or "").strip()
            title = (r['title'] or "Untitled").strip()
            author = (r['author'] or "").strip()

            item = QTreeWidgetItem([nickname, title, author])
            item.setData(0, Qt.ItemDataRole.UserRole, r['id'])
            self.readings_tree.addTopLevelItem(item)

    def _create_and_add_reading_tab(self, reading_row, set_current=True):
        reading_data = dict(reading_row)
        nickname = (reading_data.get('nickname') or "").strip()
        title = (reading_data.get('title') or "Untitled").strip()
        tab_title = nickname if nickname else title

        reading_id = reading_data['id']

        if reading_id in self.reading_tabs:
            tab = self.reading_tabs[reading_id]
            idx = self.top_tab_widget.indexOf(tab)
            if set_current:
                self.top_tab_widget.setCurrentIndex(idx)
            return tab

        tab = ReadingNotesTab(self.db, self.project_id, reading_id,
                              spell_checker_service=self.spell_checker_service)

        idx = self.top_tab_widget.addTab(tab, self.book_icon, f" {tab_title}")

        tab.readingTitleChanged.connect(self._handle_reading_title_change)
        tab.openSynthesisTab.connect(self.open_tag_from_graph)

        # --- Connect AttachmentsTab PDF signal ---
        if hasattr(tab, 'attachments_tab'):
            tab.attachments_tab.openPdfNodesRequested.connect(self.open_pdf_node_viewer)

        # --- NEW: Connect Editors inside Reading Tab (Notes + Bottom Tabs) ---
        if hasattr(tab, 'notes_editor'):
            tab.notes_editor.linkPdfNodeTriggered.connect(lambda: self._on_link_pdf_node_triggered(tab.notes_editor))
            tab.notes_editor.editor.smartAnchorClicked.connect(self._on_editor_link_clicked)

        # Iterate through bottom tabs that have editors and connect them
        # Note: This relies on ReadingNotesTab exposing them or us iterating them
        for _, editor in tab.bottom_tabs_with_editors:
            editor.linkPdfNodeTriggered.connect(lambda e=editor: self._on_link_pdf_node_triggered(e))
            editor.editor.smartAnchorClicked.connect(self._on_editor_link_clicked)
        # --- END NEW ---

        self.reading_tabs[reading_id] = tab

        if set_current:
            self.top_tab_widget.setCurrentIndex(idx)

        return tab

    def _handle_reading_title_change(self, reading_id, tab_widget):
        details = self.db.get_reading_details(reading_id)
        if not details:
            return

        nickname = (details['nickname'] or "").strip() if 'nickname' in details.keys() else ""
        title = (details['title'] or "Untitled").strip() if 'title' in details.keys() else "Untitled"
        new_text = nickname if nickname else title
        author = (details.get('author') or "").strip()

        i = self.top_tab_widget.indexOf(tab_widget)
        if i != -1:
            self.top_tab_widget.setTabText(i, f" {new_text}")
            self.top_tab_widget.setTabIcon(i, self.book_icon)

        for j in range(self.readings_tree.topLevelItemCount()):
            item = self.readings_tree.topLevelItem(j)
            if item.data(0, Qt.ItemDataRole.UserRole) == reading_id:
                item.setText(0, nickname)
                item.setText(1, title)
                item.setText(2, author)
                break

    def add_reading(self):
        if self.project_id == -1:
            return

        # Pass self.db to the dialog so it can access settings
        # FIX: Pass parent as keyword argument to avoid it being interpreted as current_data
        dialog = AddReadingDialog(self.db, parent=self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Pass all new fields to add_reading
            new_id = self.db.add_reading(
                self.project_id,
                dialog.title,
                dialog.author,
                dialog.nickname,
                dialog.zotero_key,
                dialog.published,
                dialog.pages,
                dialog.level,
                dialog.classification
            )
            self.load_readings()

            self.top_tab_widget.blockSignals(True)
            try:
                reading_row = self.db.get_reading_details(new_id)
                if reading_row:
                    new_tab = self._create_and_add_reading_tab(reading_row, set_current=True)
                    new_tab.load_data()
                else:
                    print(f"Error: Could not find new reading with id {new_id}")
            finally:
                self.top_tab_widget.blockSignals(False)

    @Slot(int)
    def on_top_tab_changed(self, index):
        if self._programmatic_tab_change:
            return

        self.save_all_editors()

        current_widget = self.top_tab_widget.widget(index)
        if current_widget == self.synthesis_tab:
            self.synthesis_tab.load_tab_data(self.project_details)
        elif current_widget == self.mindmaps_tab:
            self.mindmaps_tab.load_mindmaps()
        elif current_widget == self.graph_view_tab:
            self.graph_view_tab.load_graph()
        elif current_widget == self.todo_list_tab:
            self.todo_list_tab.load_items()

    @Slot()
    def save_all_editors(self):
        if self.project_id == -1:
            return
        print("Auto-saving project data...")

        def save_purpose(html):
            if html is not None:
                self.db.update_project_text_field(self.project_id, 'project_purpose_text', html)

        self.purpose_text_editor.get_html(save_purpose)

        def save_goals(html):
            if html is not None:
                self.db.update_project_text_field(self.project_id, 'project_goals_text', html)

        self.goals_text_editor.get_html(save_goals)

        for tab in self.bottom_tabs:
            def cb(field):
                return lambda html: self.db.update_project_text_field(self.project_id, field,
                                                                      html) if html is not None else None

            tab.get_editor_content(cb(tab.text_field))

        for tab in self.reading_tabs.values():
            if getattr(tab, "_is_loaded", False) and hasattr(tab, 'save_all'):
                tab.save_all()

        if hasattr(self, 'assignment_tab') and isinstance(self.assignment_tab, AssignmentTab):
            self.assignment_tab.save_editors()

        if self.synthesis_tab and hasattr(self.synthesis_tab, 'save_editors'):
            self.synthesis_tab.save_editors()

    @Slot()
    def open_edit_instructions(self):
        if self.project_id == -1:
            return
        instructions = self.db.get_or_create_instructions(self.project_id)
        dialog = EditInstructionsDialog(instructions, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_instr = dialog.result
            if new_instr:
                self.db.update_instructions(self.project_id, new_instr)
                for tab in self.bottom_tabs:
                    if hasattr(tab, 'update_instructions'):
                        tab.update_instructions()

                if hasattr(self.synthesis_tab, 'update_all_instructions'):
                    self.synthesis_tab.update_all_instructions(new_instr)

                for reading_tab in self.reading_tabs.values():
                    if hasattr(reading_tab, 'update_all_tab_instructions'):
                        reading_tab.update_all_tab_instructions(new_instr)

    @Slot()
    def _edit_reading_rules(self):
        if self.project_id == -1:
            return
        if not EditReadingRulesDialog:
            QMessageBox.critical(self, "Error", "EditReadingRulesDialog not loaded.")
            return

        instructions = self.db.get_or_create_instructions(self.project_id)
        html = instructions.get("reading_rules_html", "")
        if not html or html.isspace():
            html = DEFAULT_READING_RULES_HTML

        dialog = EditReadingRulesDialog(html, self.spell_checker_service, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_html = dialog.get_html()
            instructions = self.db.get_or_create_instructions(self.project_id)
            instructions["reading_rules_html"] = new_html
            self.db.update_instructions(self.project_id, instructions)
            QMessageBox.information(self, "Success", "Reading Rules updated.")

    @Slot()
    def _edit_syntopic_rules(self):
        if self.project_id == -1:
            return
        if not EditSyntopicRulesDialog:
            QMessageBox.critical(self, "Error", "EditSyntopicRulesDialog not loaded.")
            return

        instructions = self.db.get_or_create_instructions(self.project_id)
        html = instructions.get("syntopic_rules_html", "")
        if not html or html.isspace():
            html = DEFAULT_SYNTOPIC_RULES_HTML

        dialog = EditSyntopicRulesDialog(html, self.spell_checker_service, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_html = dialog.get_html()
            instructions = self.db.get_or_create_instructions(self.project_id)
            instructions["syntopic_rules_html"] = new_html
            self.db.update_instructions(self.project_id, instructions)
            QMessageBox.information(self, "Success", "Syntopical Reading Rules updated.")

    @Slot()
    def _open_export_dialog(self):
        if self.project_id == -1:
            return

        if not ExportProjectDialog or not ExportEngine:
            QMessageBox.critical(self, "Error", "Export components could not be loaded.")
            return

        self.save_all_editors()

        dialog = ExportProjectDialog(self.db, self.project_id, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            config = dialog.get_export_config()
            file_format = config['format']

            ext_map = {"html": "HTML (*.html)", "docx": "Word Document (*.docx)", "txt": "Text File (*.txt)"}
            project_name = self.project_details.get('name', 'Export')
            safe_project_name = "".join(c for c in project_name if c.isalnum() or c in (' ', '_')).rstrip()
            default_filename = f"{safe_project_name}.{file_format}"

            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save Export", default_filename, ext_map[file_format]
            )

            if not file_path:
                return

            try:
                engine = ExportEngine(self.db, self.project_id)
                engine.export_to_file(file_path, config)

                reply = QMessageBox.information(self,
                                                "Export Successful",
                                                f"Project exported successfully to:\n{file_path}\n\nDo you want to open the file now?",
                                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                                QMessageBox.StandardButton.Yes
                                                )

                if reply == QMessageBox.StandardButton.Yes:
                    QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))

            except ImportError as e:
                QMessageBox.critical(self, "Export Error",
                                     f"A required library is missing: {e}\nPlease install 'python-docx' and 'beautifulsoup4'.")
            except Exception as e:
                QMessageBox.critical(self, "Export Error",
                                     f"An error occurred during export: {e}\n\n{traceback.format_exc()}")

    @Slot(QTreeWidgetItem, int)
    def on_reading_double_clicked(self, item, column):
        reading_id = item.data(0, Qt.ItemDataRole.UserRole)
        self.open_reading_from_graph(0, reading_id)

    @Slot(QPoint)
    def show_readings_context_menu(self, position):
        item = self.readings_tree.itemAt(position)

        menu = QMenu(self)

        if item:
            edit_action = QAction("Edit Reading...", self)
            edit_action.triggered.connect(self.edit_reading)
            menu.addAction(edit_action)

            menu.addSeparator()

            delete_action = QAction("Delete Reading", self)
            delete_action.triggered.connect(self.delete_reading)
            menu.addAction(delete_action)

            if self.readings_tree.topLevelItemCount() >= 2:
                reorder_action = QAction("Reorder Readings", self)
                reorder_action.triggered.connect(self.reorder_readings)
                menu.addAction(reorder_action)
        else:
            # Clicked on empty space
            add_action = QAction("Add New Reading", self)
            add_action.triggered.connect(self.add_reading)
            menu.addAction(add_action)

            if self.readings_tree.topLevelItemCount() >= 2:
                reorder_action = QAction("Reorder Readings", self)
                reorder_action.triggered.connect(self.reorder_readings)
                menu.addAction(reorder_action)

        menu.exec(self.readings_tree.viewport().mapToGlobal(position))

    def edit_reading(self):
        item = self.readings_tree.currentItem()
        if not item: return

        reading_id = item.data(0, Qt.ItemDataRole.UserRole)

        # Fetch current data
        current_data = self.db.get_reading_details(reading_id)
        if not current_data: return

        # Convert Row to dict and ensure all keys exist
        data_dict = dict(current_data)

        # Open Dialog
        dialog = AddReadingDialog(self.db, current_data=data_dict, parent=self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Prepare update dict
            details = {
                'title': dialog.title,
                'author': dialog.author,
                'nickname': dialog.nickname,
                'published': dialog.published,
                'pages': dialog.pages,
                'level': dialog.level,
                'classification': dialog.classification,
                'zotero_item_key': dialog.zotero_key
            }

            # Save to DB
            self.db.update_reading_details(reading_id, details)

            # Refresh Tree
            self.load_readings()

            # Refresh Tab if open
            if reading_id in self.reading_tabs:
                tab = self.reading_tabs[reading_id]
                tab.load_data()
                self._handle_reading_title_change(reading_id, tab)  # Force title update

    @Slot()
    def delete_reading(self):
        item = self.readings_tree.currentItem()
        if not item:
            return

        reading_id = item.data(0, Qt.ItemDataRole.UserRole)
        nickname = item.text(0)
        title = item.text(1)
        display_name = nickname if nickname else title

        reply = QMessageBox.question(
            self, "Delete Reading",
            f"Are you sure you want to permanently delete '{display_name}'?\n\nThis will delete the reading, its outline, and all its attachments.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.db.delete_reading(reading_id)
                tab_widget = self.reading_tabs.pop(reading_id, None)
                if tab_widget:
                    self.top_tab_widget.removeTab(self.top_tab_widget.indexOf(tab_widget))
                self.readings_tree.takeTopLevelItem(self.readings_tree.indexOfTopLevelItem(item))
                del item

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not delete reading: {e}")

    @Slot()
    def reorder_readings(self):
        if not ReorderDialog:
            QMessageBox.critical(self, "Error", "Reorder dialog is not available.")
            return

        try:
            readings = self.db.get_readings(self.project_id)
            if not readings or len(readings) < 2:
                QMessageBox.information(self, "Reorder", "Not enough readings to reorder.")
                return

            items_to_reorder = []
            for r in readings:
                nickname = (r['nickname'] or "").strip()
                title = (r['title'] or "Untitled").strip()
                display = nickname if nickname else title
                items_to_reorder.append((display, r['id']))

            dialog = ReorderDialog(items_to_reorder, self)

            if dialog.exec() == QDialog.DialogCode.Accepted:
                ordered_ids = dialog.ordered_db_ids
                self.db.update_reading_order(ordered_ids)
                self.save_all_editors()
                self.top_tab_widget.blockSignals(True)
                self.editor_tab_widget.blockSignals(True)
                try:
                    current_project_details = self.db.get_item_details(self.project_id)
                    self.load_project(current_project_details)
                    self.load_all_editor_content()
                finally:
                    self.top_tab_widget.blockSignals(False)
                    self.editor_tab_widget.blockSignals(False)
                    self.top_tab_widget.currentChanged.connect(self.on_top_tab_changed)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not reorder readings: {e}")

    @Slot(int, int, int, int, str)
    def open_reading_tab(self, anchor_id, reading_id, outline_id, item_link_id=0, item_type=''):
        print(f"--- JUMP START ---")
        print(f"  Dashboard: Current focus is: {QApplication.instance().focusWidget()}")

        tab_widget = self.reading_tabs.get(reading_id)

        if not tab_widget:
            reading_row = self.db.get_reading_details(reading_id)
            if not reading_row:
                QMessageBox.critical(self, "Error", f"Could not find reading data for ID {reading_id}")
                return

            self._programmatic_tab_change = True
            tab_widget = self._create_and_add_reading_tab(reading_row, set_current=True)
            self._programmatic_tab_change = False
            tab_widget.load_data()
        else:
            self._programmatic_tab_change = True
            self.top_tab_widget.setCurrentWidget(tab_widget)
            self._programmatic_tab_change = False

        if hasattr(tab_widget, 'set_outline_selection'):
            print(f"  Dashboard: Queuing set_outline_selection with 50ms timer...")

            def _apply_selection(tab=tab_widget, aid=anchor_id, oid=outline_id,
                                 link_id=item_link_id, link_type=item_type):
                print(f"  Dashboard: 50ms timer FIRED. Calling set_outline_selection.")
                tab.set_outline_selection(aid, oid, link_id, link_type)

            QTimer.singleShot(50, _apply_selection)

    @Slot()
    def _on_tags_updated(self):
        print("Project Dashboard: Detected tag update. Refreshing UI...")
        if self.synthesis_tab:
            self.synthesis_tab.load_tab_data(self.project_details)

        for reading_tab in self.reading_tabs.values():
            if hasattr(reading_tab, 'refresh_anchor_formatting'):
                reading_tab.refresh_anchor_formatting()

        if self.graph_view_tab:
            self.graph_view_tab.load_graph()

    @Slot(int, int, int, int, str)
    def open_reading_from_graph(self, anchor_id, reading_id, outline_id=0, item_link_id=0, item_type=''):
        self.open_reading_tab(anchor_id, reading_id, outline_id, item_link_id, item_type)

    @Slot(int)
    def open_tag_from_graph(self, tag_id):
        if not self.synthesis_tab:
            return

        self._programmatic_tab_change = True
        self.top_tab_widget.setCurrentWidget(self.synthesis_tab)
        self.top_tab_widget.repaint()
        self._programmatic_tab_change = False

        if hasattr(self.synthesis_tab, 'select_tag_by_id'):
            print(f"  Dashboard: Jumping to Synthesis. Loading tab data...")
            self.synthesis_tab.load_tab_data(self.project_details)
            print(f"  Dashboard: Telling Synthesis tab to select tag {tag_id}")
            self.synthesis_tab.select_tag_by_id(tag_id)
            print(f"  Dashboard: Synthesis jump complete.")

    # --- NEW: Open PDF Node Viewer ---
    @Slot(int, int, str)
    def open_pdf_node_viewer(self, reading_id, attachment_id, file_path):
        """Opens a new PDF viewer for the given attachment."""
        if PdfNodeViewer is None:
            QMessageBox.critical(self, "Error", "PdfNodeViewer module not loaded.")
            return

        try:
            # Check if already open? (Optional optimization)
            # For now, let's allow multiple windows so user can view different PDFs

            viewer = PdfNodeViewer(self.db, reading_id, attachment_id, file_path, parent=None)  # Parent=None for popout
            viewer.show()

            # Keep reference to prevent garbage collection
            self.pdf_viewers.append(viewer)

            # Clean up closed viewers
            def cleanup():
                if viewer in self.pdf_viewers:
                    self.pdf_viewers.remove(viewer)

            viewer.finished.connect(cleanup)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open PDF viewer: {e}")

    # --- NEW: Handle Link to PDF Node ---
    @Slot()
    def _on_link_pdf_node_triggered(self, editor_widget):
        """
        Opens the PdfLinkDialog and inserts the link into the editor
        if selected.
        """
        if not PdfLinkDialog:
            QMessageBox.critical(self, "Error", "PdfLinkDialog not loaded.")
            return

        cursor = editor_widget.editor.textCursor()
        if not cursor.hasSelection():
            return

        dialog = PdfLinkDialog(self.db, self.project_id, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            node_id = dialog.selected_node_id
            node_label = dialog.selected_node_label

            if node_id:
                # FIX 2: Use 3 slashes to avoid IP address normalization (0.0.0.1)
                url_str = f"pdfnode:///{node_id}"

                # FIX 1: Use formatting instead of raw HTML to preserve font
                # Get current format to preserve font family/size
                fmt = cursor.charFormat()

                # Apply link style
                fmt.setAnchor(True)
                fmt.setAnchorHref(url_str)
                fmt.setForeground(QColor("#800080"))  # Purple as per user snippet
                fmt.setFontUnderline(True)

                # Re-insert text with new format
                # We are replacing the selection with itself, but styled
                selected_text = cursor.selectedText()
                cursor.insertText(selected_text, fmt)

    @Slot(QUrl)
    def _on_editor_link_clicked(self, url):
        """Handles clicks on pdfnode:// links."""
        # Fix: Use .scheme() and .path() for robust parsing
        if url.scheme() == "pdfnode":
            try:
                # Try path first (new format: pdfnode:///123 -> path is /123)
                path = url.path()
                if path.startswith('/'):
                    node_id_str = path[1:]
                else:
                    node_id_str = path

                if node_id_str and node_id_str.isdigit():
                    node_id = int(node_id_str)
                else:
                    # Fallback to host (old format: pdfnode://123 -> 0.0.0.123 or similar)
                    host = url.host()
                    # If it looks like an IP, it's complicated, but if it's a simple int it might work
                    if host:
                        node_id = int(host)  # This raises the error the user saw for "0.0.0.1" but catches valid ints

                self._jump_to_pdf_node(node_id)

            except Exception as e:
                print(f"Error handling pdfnode link: {e}")

    def _jump_to_pdf_node(self, node_id):
        """Opens the viewer and jumps to the node."""
        try:
            # 1. Get node details
            node = self.db.get_pdf_node_details(node_id)
            if not node:
                QMessageBox.warning(self, "Error", "Node not found.")
                return

            reading_id = node['reading_id']
            attachment_id = node['attachment_id']

            # 2. Get file path
            attachment = self.db.get_attachment_details(attachment_id)
            if not attachment:
                QMessageBox.warning(self, "Error", "Attachment file not found.")
                return

            # Construct full path
            project_root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            attachments_dir = os.path.join(project_root_dir, "Attachments")
            file_path = os.path.join(attachments_dir, attachment['file_path'])

            if not os.path.exists(file_path):
                QMessageBox.warning(self, "Error", f"File not found on disk:\n{file_path}")
                return

            # 3. Open Viewer (or find existing)
            # Check if viewer for this file is already open
            target_viewer = None
            for v in self.pdf_viewers:
                if v.attachment_id == attachment_id:
                    target_viewer = v
                    break

            if not target_viewer:
                # Open new
                self.open_pdf_node_viewer(reading_id, attachment_id, file_path)
                # The new viewer is the last one added
                if self.pdf_viewers:
                    target_viewer = self.pdf_viewers[-1]

            if target_viewer:
                target_viewer.show()
                target_viewer.raise_()
                target_viewer.activateWindow()

                # 4. Jump to Node
                # Use a small timer to allow window to show/load
                QTimer.singleShot(100, lambda: target_viewer.jump_to_node(node_id))

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Jump failed: {e}")

    # --- END NEW ---

    @Slot()
    def return_to_home(self):
        try:
            from dialogs.mindmap_editor_window import MindmapEditorWindow
            # Close mindmaps
            for widget in QApplication.topLevelWidgets():
                if isinstance(widget, MindmapEditorWindow):
                    print(f"Saving open mindmap: {widget.mindmap_name}...")
                    widget.save_mindmap(show_message=False)
                    widget.close()

            # Close PDF viewers
            for viewer in list(self.pdf_viewers):
                viewer.close()

        except ImportError:
            pass
        except Exception as e:
            print(f"Error closing windows: {e}")

        self.save_all_editors()
        self.returnToHome.emit()