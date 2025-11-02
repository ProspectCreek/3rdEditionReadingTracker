import sys
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTabWidget, QSplitter, QLabel, QTreeWidget,
    QFrame, QDialog, QTreeWidgetItem, QMenuBar
)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QAction

# Import our custom tab widget
from tabs.project_editor_tab import ProjectEditorTab
# Import the Quill editor directly for Purpose/Goals
from tabs.quill_editor_tab import QuillEditorTab

# Import the new Add Reading dialog
try:
    from dialogs.add_reading_dialog import AddReadingDialog
except ImportError:
    print("Error: Could not import AddReadingDialog")
    sys.exit(1)


class ProjectDashboardWidget(QWidget):
    """
    This is the main project dashboard "page".
    It replaces the HomeScreenWidget when a project is opened.
    """
    returnToHome = Signal()
    addReadingTab = Signal(str, int)  # Emits (title, db_id)

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.project_details = None
        self.project_id = -1
        self.bottom_tabs = []  # <-- FIX: Initialize list here

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)  # No spacing for menu bar

        # --- 0. Menu Bar ---
        self.menu_bar = QMenuBar()
        main_layout.addWidget(self.menu_bar)

        # --- 1. Top Button Bar ---
        button_bar = QWidget()
        button_bar.setStyleSheet("background-color: #f0f0f0; padding: 4px;")
        button_layout = QHBoxLayout(button_bar)

        btn_return_home = QPushButton("Return to Projects Home Screen")
        btn_add_reading = QPushButton("Add Reading")

        btn_return_home.clicked.connect(self.return_to_home)
        btn_add_reading.clicked.connect(self.add_reading)

        button_layout.addWidget(btn_return_home)
        button_layout.addWidget(btn_add_reading)
        button_layout.addStretch()

        main_layout.addWidget(button_bar)

        # --- 2. Top-Level Tab Widget ---
        self.top_tab_widget = QTabWidget()
        main_layout.addWidget(self.top_tab_widget)

        self.dashboard_tab = QWidget()
        self.mindmaps_tab = QWidget()  # Placeholder
        self.assignment_tab = QWidget()  # Placeholder

        self.setup_dashboard_tab()

        self.mindmaps_tab.setLayout(QVBoxLayout())
        self.mindmaps_tab.layout().addWidget(QLabel("Mindmaps will go here."))
        self.assignment_tab.setLayout(QVBoxLayout())
        self.assignment_tab.layout().addWidget(QLabel("Assignment details will go here."))

        # --- Auto-save connections ---
        self.top_tab_widget.currentChanged.connect(self.save_all_editors)

    def setup_dashboard_tab(self):
        """Builds the 50/50 split layout for the main dashboard tab."""
        dashboard_layout = QVBoxLayout(self.dashboard_tab)
        main_splitter = QSplitter(Qt.Orientation.Vertical)
        dashboard_layout.addWidget(main_splitter)

        # --- Top 50% Widget ---
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_splitter = QSplitter(Qt.Orientation.Horizontal)
        top_layout.addWidget(top_splitter)

        # Top-Left: Readings Viewer
        readings_widget = QFrame()
        readings_widget.setFrameShape(QFrame.Shape.StyledPanel)
        readings_layout = QVBoxLayout(readings_widget)
        readings_layout.addWidget(QLabel("Readings"))
        self.readings_tree = QTreeWidget()
        self.readings_tree.setHeaderLabels(["Title", "Author"])
        self.readings_tree.setColumnWidth(0, 200)
        # TODO: Add context menu for reordering
        readings_layout.addWidget(self.readings_tree)

        # Top-Right: Project Info
        info_widget = QFrame()
        info_widget.setFrameShape(QFrame.Shape.StyledPanel)
        info_layout = QVBoxLayout(info_widget)

        info_layout.addWidget(QLabel("Project Purpose"))
        self.purpose_text_editor = QuillEditorTab()
        info_layout.addWidget(self.purpose_text_editor)

        info_layout.addWidget(QLabel("My Goals"))
        self.goals_text_editor = QuillEditorTab()
        info_layout.addWidget(self.goals_text_editor)

        top_splitter.addWidget(readings_widget)
        top_splitter.addWidget(info_widget)
        top_splitter.setSizes([300, 300])

        # --- Bottom 50% Widget ---
        bottom_widget = QFrame()
        bottom_widget.setFrameShape(QFrame.Shape.StyledPanel)
        bottom_layout = QVBoxLayout(bottom_widget)
        self.editor_tab_widget = QTabWidget()
        bottom_layout.addWidget(self.editor_tab_widget)
        # --- Auto-save connection ---
        self.editor_tab_widget.currentChanged.connect(self.save_all_editors)

        main_splitter.addWidget(top_widget)
        main_splitter.addWidget(bottom_widget)
        main_splitter.setSizes([400, 400])

    def load_project(self, project_details):
        """Loads a new project's data into the dashboard."""
        self.project_details = dict(project_details)
        self.project_id = self.project_details['id']

        # --- 1. Clear old state ---
        self.top_tab_widget.clear()
        self.editor_tab_widget.clear()
        self.menu_bar.clear()

        # --- 2. Setup Menus ---
        settings_menu = self.menu_bar.addMenu("Settings")
        edit_instr_action = QAction("Edit Dashboard Instructions", self)
        edit_instr_action.triggered.connect(self.open_edit_instructions)
        settings_menu.addAction(edit_instr_action)

        # --- 3. Load top tabs ---
        self.top_tab_widget.addTab(self.dashboard_tab, "Project Dashboard")
        self.top_tab_widget.addTab(self.mindmaps_tab, "Mindmaps")
        if self.project_details['is_assignment'] == 1:
            self.top_tab_widget.addTab(self.assignment_tab, "Assignment")

        # --- 4. Load dashboard data ---
        self.purpose_text_editor.set_content(self.project_details.get('project_purpose_text', ''))
        self.goals_text_editor.set_content(self.project_details.get('project_goals_text', ''))

        self.load_readings()

        # --- 5. Load bottom editor tabs ---
        self.bottom_tabs = []  # Clear list before populating
        fields = [("Key Questions", "key_questions"),
                  ("Thesis/Argument", "thesis"),
                  ("Key Insights", "insights"),
                  ("Unresolved Questions", "unresolved")]

        for tab_title, field_name in fields:
            editor_tab = ProjectEditorTab(self.db, self.project_id, field_name)
            self.editor_tab_widget.addTab(editor_tab, tab_title)
            self.bottom_tabs.append(editor_tab)

    def load_readings(self):
        """Loads readings from DB into the tree widget."""
        self.readings_tree.clear()
        readings = self.db.get_readings(self.project_id)
        for reading in readings:
            item = QTreeWidgetItem([reading['title'], reading['author']])
            item.setData(0, Qt.ItemDataRole.UserRole, reading['id'])
            self.readings_tree.addTopLevelItem(item)

    def add_reading(self):
        """
        Shows a proper dialog and saves to DB.
        """
        dialog = AddReadingDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            title = dialog.title
            author = dialog.author

            # Save to database
            new_reading_id = self.db.add_reading(self.project_id, title, author)

            # Reload the list
            self.load_readings()

            # Tell MainWindow to create the new top-level tab
            self.addReadingTab.emit(title, new_reading_id)

    @Slot()
    def save_all_editors(self):
        """
        Asynchronously saves all text from all Quill editors.
        """
        if self.project_id == -1:  # No project loaded
            return

        print("Auto-saving project data...")

        # --- 1. Save Purpose and Goals ---
        def save_purpose(html):
            if html is not None:
                self.db.update_project_text_field(self.project_id, 'project_purpose_text', html)

        self.purpose_text_editor.get_content(save_purpose)

        def save_goals(html):
            if html is not None:
                self.db.update_project_text_field(self.project_id, 'project_goals_text', html)

        self.goals_text_editor.get_content(save_goals)

        # --- 2. Save Bottom Tabs ---
        for tab in self.bottom_tabs:
            # Need a closure to capture the correct text_field
            def create_save_callback(field_name):
                return lambda html: (
                    self.db.update_project_text_field(self.project_id, field_name, html)
                    if html is not None else None
                )

            save_callback = create_save_callback(tab.text_field)
            tab.get_editor_content(save_callback)

    @Slot()
    def open_edit_instructions(self):
        """
        Finds the current bottom tab and tells it to
        open the edit dialog.
        """
        current_tab = self.editor_tab_widget.currentWidget()
        if isinstance(current_tab, ProjectEditorTab):
            current_tab.open_edit_instructions_dialog()
            # Also update all other tabs
            for tab in self.bottom_tabs:
                if tab is not current_tab:
                    tab.load_data()

    @Slot()
    def return_to_home(self):
        """Save before emitting the signal."""
        self.save_all_editors()
        self.returnToHome.emit()

