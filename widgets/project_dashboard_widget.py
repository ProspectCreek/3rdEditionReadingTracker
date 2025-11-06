# widgets/project_dashboard_widget.py
import sys
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTabWidget, QSplitter, QLabel, QTreeWidget,
    QFrame, QDialog, QTreeWidgetItem, QMenuBar
)
from PySide6.QtCore import Qt, Signal, Slot, QTimer
from PySide6.QtGui import QAction
from tabs.project_editor_tab import ProjectEditorTab
from tabs.rich_text_editor_tab import RichTextEditorTab

try:
    from dialogs.add_reading_dialog import AddReadingDialog
    # MODIFIED: Import the EditInstructionsDialog
    from dialogs.edit_instructions_dialog import EditInstructionsDialog
except ImportError:
    print("Error: Could not import Dialogs")
    sys.exit(1)


class ProjectDashboardWidget(QWidget):
    """Main project dashboard page (native editors, compact, true 50/50)."""
    returnToHome = Signal()
    addReadingTab = Signal(str, int)

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.project_details = None
        self.project_id = -1
        self.bottom_tabs = []

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Menu bar
        self.menu_bar = QMenuBar()
        main_layout.addWidget(self.menu_bar)

        # Top button bar (compact)
        button_bar = QWidget()
        button_bar.setStyleSheet("background-color:#f0f0f0; padding:4px;")
        button_layout = QHBoxLayout(button_bar); button_layout.setContentsMargins(6,2,6,2)
        btn_return_home = QPushButton("Return to Projects Home Screen")
        btn_add_reading = QPushButton("Add Reading")
        btn_return_home.clicked.connect(self.return_to_home)
        btn_add_reading.clicked.connect(self.add_reading)
        button_layout.addWidget(btn_return_home); button_layout.addWidget(btn_add_reading); button_layout.addStretch()
        main_layout.addWidget(button_bar)

        # Tabs
        self.top_tab_widget = QTabWidget()
        main_layout.addWidget(self.top_tab_widget)

        self.dashboard_tab = QWidget()
        self.mindmaps_tab = QWidget()
        self.assignment_tab = QWidget()

        self._build_dashboard_tab()

        self.mindmaps_tab.setLayout(QVBoxLayout()); self.mindmaps_tab.layout().addWidget(QLabel("Mindmaps will go here."))
        self.assignment_tab.setLayout(QVBoxLayout()); self.assignment_tab.layout().addWidget(QLabel("Assignment details will go here."))

        self.top_tab_widget.currentChanged.connect(self.save_all_editors)

        # Ensure splitter sizes are set after the first paint
        QTimer.singleShot(0, self._enforce_equal_splits)

    def _build_dashboard_tab(self):
        """Top/Bottom split, each half left/right split — all equal on show."""
        outer = QVBoxLayout(self.dashboard_tab)
        outer.setContentsMargins(4, 4, 4, 4)
        outer.setSpacing(4)

        # Vertical split: top/bottom
        self.main_splitter = QSplitter(Qt.Orientation.Vertical)
        self.main_splitter.setHandleWidth(4)
        outer.addWidget(self.main_splitter)

        # ----- Top half -----
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget); top_layout.setContentsMargins(4,4,4,4); top_layout.setSpacing(4)

        self.top_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.top_splitter.setHandleWidth(4)
        top_layout.addWidget(self.top_splitter)

        # Left: Readings viewer
        readings_widget = QFrame(); readings_widget.setFrameShape(QFrame.Shape.StyledPanel)
        rl = QVBoxLayout(readings_widget); rl.setContentsMargins(6,6,6,6); rl.setSpacing(6)
        rl.addWidget(QLabel("Readings"))
        self.readings_tree = QTreeWidget(); self.readings_tree.setHeaderLabels(["Title","Author"]); self.readings_tree.setColumnWidth(0, 200)
        rl.addWidget(self.readings_tree)

        # Right: Purpose + Goals (native editors)
        info_widget = QFrame(); info_widget.setFrameShape(QFrame.Shape.StyledPanel)
        il = QVBoxLayout(info_widget); il.setContentsMargins(6,6,6,6); il.setSpacing(6)
        il.addWidget(QLabel("Project Purpose"))
        self.purpose_text_editor = RichTextEditorTab("Project Purpose")
        il.addWidget(self.purpose_text_editor)
        il.addWidget(QLabel("My Goals"))
        self.goals_text_editor = RichTextEditorTab("Project Goals")
        il.addWidget(self.goals_text_editor)

        self.top_splitter.addWidget(readings_widget)
        self.top_splitter.addWidget(info_widget)
        self.top_splitter.setStretchFactor(0, 1)
        self.top_splitter.setStretchFactor(1, 1)

        # ----- Bottom half -----
        bottom_widget = QFrame(); bottom_widget.setFrameShape(QFrame.Shape.StyledPanel)
        bl = QVBoxLayout(bottom_widget); bl.setContentsMargins(6,6,6,6); bl.setSpacing(6)
        self.editor_tab_widget = QTabWidget()
        bl.addWidget(self.editor_tab_widget)
        self.editor_tab_widget.currentChanged.connect(self.save_all_editors)

        self.main_splitter.addWidget(top_widget)
        self.main_splitter.addWidget(bottom_widget)
        self.main_splitter.setStretchFactor(0, 1)
        self.main_splitter.setStretchFactor(1, 1)

    def _enforce_equal_splits(self):
        """Force true 50/50 splits once widgets have sizes."""
        total_h = max(2, self.main_splitter.size().height())
        self.main_splitter.setSizes([total_h // 2, total_h - total_h // 2])
        total_w = max(2, self.top_splitter.size().width())
        self.top_splitter.setSizes([total_w // 2, total_w - total_w // 2])

    def load_project(self, project_details):
        self.project_details = dict(project_details)
        self.project_id = self.project_details['id']

        self.top_tab_widget.clear()
        self.editor_tab_widget.clear()
        self.menu_bar.clear()

        settings_menu = self.menu_bar.addMenu("Settings")
        edit_instr_action = QAction("Edit Dashboard Instructions", self)
        edit_instr_action.triggered.connect(self.open_edit_instructions)
        settings_menu.addAction(edit_instr_action)

        self.top_tab_widget.addTab(self.dashboard_tab, "Project Dashboard")
        self.top_tab_widget.addTab(self.mindmaps_tab, "Mindmaps")
        if self.project_details.get('is_assignment', 0) == 1:
            self.top_tab_widget.addTab(self.assignment_tab, "Assignment")

        self.load_readings()

        self.bottom_tabs = []
        # MODIFIED: Use the full database column names
        fields = [
            ("Key Questions", "key_questions_text"),
            ("Thesis/Argument", "thesis_text"),
            ("Key Insights", "insights_text"),
            ("Unresolved Questions", "unresolved_text")
        ]
        for tab_title, field_name in fields:
            editor_tab = ProjectEditorTab(self.db, self.project_id, field_name)
            self.editor_tab_widget.addTab(editor_tab, tab_title)
            self.bottom_tabs.append(editor_tab)

        QTimer.singleShot(0, self._enforce_equal_splits)

    def load_all_editor_content(self):
        """
        Load HTML into all editors after the dashboard is shown.
        Prevents hidden-widget issues and keeps parity with older API.
        """
        if not self.project_details:
            return
        self.purpose_text_editor.set_html(self.project_details.get('project_purpose_text', ''))
        self.goals_text_editor.set_html(self.project_details.get('project_goals_text', ''))
        for tab in self.bottom_tabs:
            tab.load_data()

    def load_readings(self):
        self.readings_tree.clear()
        readings = self.db.get_readings(self.project_id)
        for r in readings:
            item = QTreeWidgetItem([r['title'], r['author']]); item.setData(0, Qt.ItemDataRole.UserRole, r['id'])
            self.readings_tree.addTopLevelItem(item)

    def add_reading(self):
        dialog = AddReadingDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            title = dialog.title; author = dialog.author
            new_id = self.db.add_reading(self.project_id, title, author)
            self.load_readings(); self.addReadingTab.emit(title, new_id)

    @Slot()
    def save_all_editors(self):
        if self.project_id == -1: return
        print("Auto-saving project data...")

        def save_purpose(html):
            if html is not None: self.db.update_project_text_field(self.project_id, 'project_purpose_text', html)
        self.purpose_text_editor.get_html(save_purpose)

        def save_goals(html):
            if html is not None: self.db.update_project_text_field(self.project_id, 'project_goals_text', html)
        self.goals_text_editor.get_html(save_goals)

        for tab in self.bottom_tabs:
            def cb(field):
                # This 'field' now correctly holds 'key_questions_text', etc.
                return lambda html: self.db.update_project_text_field(self.project_id, field, html) if html is not None else None
            tab.get_editor_content(cb(tab.text_field))

    @Slot()
    def open_edit_instructions(self):
        """
        MODIFIED: This slot now handles opening the dialog, saving
        to the database, and telling the tabs to update their prompts.
        """
        if self.project_id == -1:
            return

        # 1. Get current instructions
        instructions = self.db.get_or_create_instructions(self.project_id)

        # 2. Open the dialog
        dialog = EditInstructionsDialog(instructions, self)

        # 3. If user clicked OK, save the new instructions
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_instr = dialog.result
            if new_instr:
                self.db.update_instructions(
                    self.project_id,
                    new_instr["key_questions_instr"],
                    new_instr["thesis_instr"],
                    new_instr["insights_instr"],
                    new_instr["unresolved_instr"]
                )

                # 4. Tell all bottom tabs to reload their prompt text
                for tab in self.bottom_tabs:
                    if hasattr(tab, 'update_instructions'):
                        tab.update_instructions()

    @Slot()
    def return_to_home(self):
        self.save_all_editors()
        self.returnToHome.emit()

