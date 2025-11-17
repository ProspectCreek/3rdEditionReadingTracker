# prospectcreek/3rdeditionreadingtracker/widgets/project_dashboard_widget.py
import sys
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTabWidget, QSplitter, QLabel, QTreeWidget,
    QFrame, QDialog, QTreeWidgetItem, QMenuBar,
    QMessageBox, QMenu, QApplication
)
from PySide6.QtCore import Qt, Signal, Slot, QTimer, QPoint
from PySide6.QtGui import QAction, QIcon, QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer

# Import all the tab types
from tabs.project_editor_tab import ProjectEditorTab
from tabs.rich_text_editor_tab import RichTextEditorTab
from tabs.mindmap_tab import MindmapTab
from tabs.assignment_tab import AssignmentTab
from tabs.reading_notes_tab import ReadingNotesTab
from tabs.synthesis_tab import SynthesisTab
from tabs.graph_view_tab import GraphViewTab  # <-- This now imports the NEW Obsidian-style tab
from tabs.todo_list_tab import TodoListTab

# from tabs.obsidian_test_tab import ObsidianTestTab  # <-- REMOVED

try:
    from dialogs.add_reading_dialog import AddReadingDialog
    from dialogs.edit_instructions_dialog import EditInstructionsDialog
    from dialogs.reorder_dialog import ReorderDialog
except ImportError:
    print("Error: Could not import Dialogs")
    sys.exit(1)


class ProjectDashboardWidget(QWidget):
    """Main project dashboard page (native editors, compact, true 50/50)."""
    returnToHome = Signal()

    def __init__(self, db_manager, spell_checker_service=None, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.spell_checker_service = spell_checker_service  # <-- STORE SERVICE
        self.project_details = None
        self.project_id = -1
        self.bottom_tabs = []
        self.reading_tabs = {}  # Stores {reading_id: ReadingNotesTab}
        self.synthesis_tab = None
        self.graph_view_tab = None
        self.obsidian_test_tab = None  # <-- ADDED
        self.todo_list_tab = None
        self.assignment_tab = None
        self.mindmaps_tab = None

        # --- FIX: Add flag to prevent save-on-jump ---
        self._programmatic_tab_change = False
        # --- END FIX ---

        # --- NEW: Book Icon ---
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
        # --- END NEW ---

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Menu bar
        self.menu_bar = QMenuBar()
        main_layout.addWidget(self.menu_bar)

        # Top button bar (compact)
        button_bar = QWidget()
        button_bar.setStyleSheet("background-color:#f0f0f0; padding:4px;")
        button_layout = QHBoxLayout(button_bar)
        button_layout.setContentsMargins(6, 2, 6, 2)
        btn_return_home = QPushButton("Return to Projects Home Screen")
        btn_add_reading = QPushButton("Add Reading")
        btn_return_home.clicked.connect(self.return_to_home)
        btn_add_reading.clicked.connect(self.add_reading)
        button_layout.addWidget(btn_return_home)
        button_layout.addWidget(btn_add_reading)
        button_layout.addStretch()
        main_layout.addWidget(button_bar)

        # Tabs
        self.top_tab_widget = QTabWidget()
        main_layout.addWidget(self.top_tab_widget)

        self.dashboard_tab = QWidget()
        self._build_dashboard_tab()

        # Connect tab changed signal *after* building tabs
        self.top_tab_widget.currentChanged.connect(self.on_top_tab_changed)
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
        self.readings_tree.setColumnWidth(0, 150)
        self.readings_tree.setColumnWidth(1, 200)
        self.readings_tree.setSortingEnabled(False)  # --- FIX: Disable sorting ---
        rl.addWidget(self.readings_tree)

        # --- NEW: Context Menu and Double Click ---
        self.readings_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.readings_tree.customContextMenuRequested.connect(self.show_readings_context_menu)
        self.readings_tree.itemDoubleClicked.connect(self.on_reading_double_clicked)
        # --- END NEW ---

        # Right: Purpose + Goals (native editors)
        info_widget = QFrame()
        info_widget.setFrameShape(QFrame.Shape.StyledPanel)
        il = QVBoxLayout(info_widget)
        il.setContentsMargins(6, 6, 6, 6)
        il.setSpacing(6)
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
        bottom_widget = QFrame()
        bottom_widget.setFrameShape(QFrame.Shape.StyledPanel)
        bl = QVBoxLayout(bottom_widget)
        bl.setContentsMargins(6, 6, 6, 6)
        bl.setSpacing(6)
        self.editor_tab_widget = QTabWidget()
        bl.addWidget(self.editor_tab_widget)

        # --- FIX: Connect save signal ---
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
        # --- Disconnect signals to prevent premature saves ---
        try:
            self.top_tab_widget.currentChanged.disconnect()
        except RuntimeError:
            pass  # Already disconnected
        try:
            self.editor_tab_widget.currentChanged.disconnect()
        except RuntimeError:
            pass  # Already disconnected
        # ---

        self.project_details = dict(project_details)
        self.project_id = self.project_details['id']

        self.top_tab_widget.clear()
        self.editor_tab_widget.clear()
        self.menu_bar.clear()
        self.bottom_tabs.clear()
        self.reading_tabs.clear()
        self.synthesis_tab = None
        self.graph_view_tab = None
        # self.obsidian_test_tab = None  # <-- REMOVED
        self.todo_list_tab = None
        self.assignment_tab = None
        self.mindmaps_tab = None

        settings_menu = self.menu_bar.addMenu("Settings")
        edit_instr_action = QAction("Edit Dashboard Instructions", self)
        edit_instr_action.triggered.connect(self.open_edit_instructions)
        settings_menu.addAction(edit_instr_action)

        self.top_tab_widget.addTab(self.dashboard_tab, "Project Dashboard")

        # --- MODIFIED: Tab Order ---
        if self.project_details.get('is_assignment', 0) == 1:
            self.assignment_tab = AssignmentTab(self.db, self.project_id, spell_checker_service=self.spell_checker_service) # <-- PASS SERVICE
            self.top_tab_widget.addTab(self.assignment_tab, "Assignment")

        self.mindmaps_tab = MindmapTab(self.db, self.project_id)
        self.top_tab_widget.addTab(self.mindmaps_tab, "Mindmaps")
        # --- END MODIFIED: Tab Order ---

        # --- Add Synthesis Tab ---
        self.synthesis_tab = SynthesisTab(self.db, self.project_id, spell_checker_service=self.spell_checker_service) # <-- PASS SERVICE
        self.synthesis_tab.openReading.connect(self.open_reading_tab)
        self.synthesis_tab.tagsUpdated.connect(self._on_tags_updated)
        self.top_tab_widget.addTab(self.synthesis_tab, "Synthesis")

        # --- Add Graph View Tab (RENAMED) ---
        self.graph_view_tab = GraphViewTab(self.db, self.project_id) # No editor here
        self.graph_view_tab.readingDoubleClicked.connect(self.open_reading_tab)
        self.graph_view_tab.tagDoubleClicked.connect(self.open_tag_from_graph)
        self.graph_view_tab.tagsUpdated.connect(self._on_tags_updated)
        self.top_tab_widget.addTab(self.graph_view_tab, "Connections")

        # ---!!--- REMOVED OBSIDIAN TEST TAB ---!!---
        # self.obsidian_test_tab = ObsidianTestTab(self.db, self.project_id)
        # self.obsidian_test_tab.readingDoubleClicked.connect(self.open_reading_tab)
        # self.obsidian_test_tab.tagDoubleClicked.connect(self.open_tag_from_graph)
        # self.obsidian_test_tab.tagsUpdated.connect(self._on_tags_updated)
        # self.top_tab_widget.addTab(self.obsidian_test_tab, "Obsidian Test")
        # ---!!--- END REMOVED ---!!---

        # --- NEW: Add To-Do List Tab ---
        self.todo_list_tab = TodoListTab(self.db, self.project_id) # No editor here
        self.top_tab_widget.addTab(self.todo_list_tab, "To-Do List")
        # --- END NEW ---

        self.load_readings()  # This populates the tree

        readings = self.db.get_readings(self.project_id)
        for reading in readings:
            self._create_and_add_reading_tab(reading, set_current=False)

        # Load bottom dashboard editors
        fields = [
            ("Key Questions", "key_questions_text"),
            ("Thesis/Argument", "thesis_text"),
            ("Key Insights", "insights_text"),
            ("Unresolved Questions", "unresolved_text")
        ]
        for tab_title, field_name in fields:
            editor_tab = ProjectEditorTab(self.db, self.project_id, field_name, spell_checker_service=self.spell_checker_service) # <-- PASS SERVICE
            self.editor_tab_widget.addTab(editor_tab, tab_title)
            self.bottom_tabs.append(editor_tab)

        QTimer.singleShot(0, self._enforce_equal_splits)

        # --- Reconnect signals ---
        self.top_tab_widget.currentChanged.connect(self.on_top_tab_changed)
        self.editor_tab_widget.currentChanged.connect(self.save_all_editors)

    def load_all_editor_content(self):
        """
        Load HTML into all editors after the dashboard is shown.
        """
        if not self.project_details:
            return

        print("Loading all editor content...")
        try:
            # Load top editors
            self.purpose_text_editor.set_html(self.project_details.get('project_purpose_text', ''))
            self.goals_text_editor.set_html(self.project_details.get('project_goals_text', ''))

            # Load bottom editors
            for tab in self.bottom_tabs:
                html_content = self.project_details.get(tab.text_field, '')
                if hasattr(tab, 'set_html'):
                    tab.set_html(html_content)

            # Load data for AssignmentTab
            if hasattr(self, 'assignment_tab') and isinstance(self.assignment_tab, AssignmentTab):
                self.assignment_tab.load_data(self.project_details)

            if self.synthesis_tab:
                self.synthesis_tab.load_tab_data(self.project_details)

            if self.todo_list_tab:
                self.todo_list_tab.load_items()

            # Call load_data() on each reading tab
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
        """
        Creates a new ReadingNotesTab and adds it to the top tab widget
        and our internal list for tracking.
        """
        reading_data = dict(reading_row)
        nickname = (reading_data.get('nickname') or "").strip()
        title = (reading_data.get('title') or "Untitled").strip()
        tab_title = nickname if nickname else title

        reading_id = reading_data['id']

        # --- Avoid duplicates ---
        if reading_id in self.reading_tabs:
            tab = self.reading_tabs[reading_id]
            idx = self.top_tab_widget.indexOf(tab)
            if set_current:
                self.top_tab_widget.setCurrentIndex(idx)
            return tab

        tab = ReadingNotesTab(self.db, self.project_id, reading_id, spell_checker_service=self.spell_checker_service) # <-- PASS SERVICE

        # --- NEW: Add book icon ---
        idx = self.top_tab_widget.addTab(tab, self.book_icon, f" {tab_title}")
        # --- END NEW ---

        # Listen for nickname/title changes from within the tab
        tab.readingTitleChanged.connect(self._handle_reading_title_change)

        # --- NEW: Connect signal for anchor clicks ---
        tab.openSynthesisTab.connect(self.open_tag_from_graph)
        # --- END NEW ---

        self.reading_tabs[reading_id] = tab

        if set_current:
            self.top_tab_widget.setCurrentIndex(idx)

        return tab

    def _handle_reading_title_change(self, reading_id, tab_widget):
        """
        Refresh display title from DB and update tab + tree immediately.
        """
        details = self.db.get_reading_details(reading_id)
        if not details:
            return

        nickname = (details['nickname'] or "").strip() if 'nickname' in details.keys() else ""
        title = (details['title'] or "Untitled").strip() if 'title' in details.keys() else "Untitled"
        new_text = nickname if nickname else title
        author = (details.get('author') or "").strip()

        # Update tab text
        i = self.top_tab_widget.indexOf(tab_widget)
        if i != -1:
            # --- NEW: Add book icon ---
            self.top_tab_widget.setTabText(i, f" {new_text}")
            self.top_tab_widget.setTabIcon(i, self.book_icon)
            # --- END NEW ---

        # Update readings tree
        for j in range(self.readings_tree.topLevelItemCount()):
            item = self.readings_tree.topLevelItem(j)
            if item.data(0, Qt.ItemDataRole.UserRole) == reading_id:
                item.setText(0, nickname)
                item.setText(1, title)
                item.setText(2, author)
                break

    def add_reading(self):
        """
        Handles the "Add Reading" button click.
        Adds to DB, reloads the tree, and creates a new tab.
        Critically: we BLOCK autosave signals while creating & loading the tab.
        """
        if self.project_id == -1:
            return

        dialog = AddReadingDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            title = dialog.title
            author = dialog.author
            nickname = dialog.nickname

            # Save to DB
            new_id = self.db.add_reading(self.project_id, title, author, nickname)

            # Refresh the Readings tree
            self.load_readings()

            # Open tab for the new reading WITHOUT letting currentChanged fire save_all
            self.top_tab_widget.blockSignals(True)
            try:
                reading_row = self.db.get_reading_details(new_id)
                if reading_row:
                    new_tab = self._create_and_add_reading_tab(reading_row, set_current=True)
                    # Load data BEFORE we re-enable signals (so fields are not blank)
                    new_tab.load_data()
                else:
                    print(f"Error: Could not find new reading with id {new_id}")
            finally:
                self.top_tab_widget.blockSignals(False)

    @Slot(int)
    def on_top_tab_changed(self, index):
        """Called when the main tab (Dashboard, Mindmap, Reading, etc) changes."""
        if self._programmatic_tab_change:
            return

        # First, save everything (now only happens on USER clicks)
        self.save_all_editors()

        # Next, check if we switched *to* a specific tab
        current_widget = self.top_tab_widget.widget(index)
        if current_widget == self.synthesis_tab:
            self.synthesis_tab.load_tab_data(self.project_details)
        elif current_widget == self.mindmaps_tab:
            self.mindmaps_tab.load_mindmaps()
        elif current_widget == self.graph_view_tab:
            self.graph_view_tab.load_graph()
        # ---!!--- REMOVED OBSIDIAN TEST TAB ---!!---
        # elif current_widget == self.obsidian_test_tab:
        #     self.obsidian_test_tab.load_graph()
        # ---!!--- END REMOVED ---!!---
        elif current_widget == self.todo_list_tab:
            self.todo_list_tab.load_items()

    @Slot()
    def save_all_editors(self):
        if self.project_id == -1:
            return
        print("Auto-saving project data...")

        # Save dashboard editors
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

        # Save open reading tabs ONLY if they are fully loaded
        for tab in self.reading_tabs.values():
            if getattr(tab, "_is_loaded", False) and hasattr(tab, 'save_all'):
                tab.save_all()

        # Save assignment tab
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
                self.db.update_instructions(
                    self.project_id,
                    new_instr["key_questions_instr"],
                    new_instr["thesis_instr"],
                    new_instr["insights_instr"],
                    new_instr["unresolved_instr"]
                )
                for tab in self.bottom_tabs:
                    if hasattr(tab, 'update_instructions'):
                        tab.update_instructions()

    @Slot(QTreeWidgetItem, int)
    def on_reading_double_clicked(self, item, column):
        """Switches to the corresponding tab when a reading is double-clicked."""
        reading_id = item.data(0, Qt.ItemDataRole.UserRole)
        self.open_reading_from_graph(0, reading_id)

    @Slot(QPoint)
    def show_readings_context_menu(self, position):
        """Shows the right-click menu for the readings tree."""
        item = self.readings_tree.itemAt(position)
        if not item:
            return  # Clicked on empty space

        menu = QMenu(self)

        # Delete Action
        delete_action = QAction("Delete Reading", self)
        delete_action.triggered.connect(self.delete_reading)
        menu.addAction(delete_action)

        # Reorder Action
        if self.readings_tree.topLevelItemCount() >= 2:
            reorder_action = QAction("Reorder Readings", self)
            reorder_action.triggered.connect(self.reorder_readings)
            menu.addAction(reorder_action)

        menu.exec(self.readings_tree.viewport().mapToGlobal(position))

    @Slot()
    def delete_reading(self):
        """Deletes the currently selected reading."""
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
                # 1. Delete from DB (cascading delete handles outline/attachments)
                self.db.delete_reading(reading_id)

                # 2. Remove tab
                tab_widget = self.reading_tabs.pop(reading_id, None)
                if tab_widget:
                    self.top_tab_widget.removeTab(self.top_tab_widget.indexOf(tab_widget))

                # 3. Remove from tree
                self.readings_tree.takeTopLevelItem(self.readings_tree.indexOfTopLevelItem(item))
                del item

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not delete reading: {e}")

    @Slot()
    def reorder_readings(self):
        """Opens the reorder dialog for readings and reloads the project."""
        if not ReorderDialog:
            QMessageBox.critical(self, "Error", "Reorder dialog is not available.")
            return

        try:
            readings = self.db.get_readings(self.project_id)
            if not readings or len(readings) < 2:
                QMessageBox.information(self, "Reorder", "Not enough readings to reorder.")
                return

            # Use nickname, fallback to title for display in dialog
            items_to_reorder = []
            for r in readings:
                nickname = (r['nickname'] or "").strip()
                title = (r['title'] or "Untitled").strip()
                display = nickname if nickname else title
                items_to_reorder.append((display, r['id']))

            dialog = ReorderDialog(items_to_reorder, self)

            if dialog.exec() == QDialog.DialogCode.Accepted:
                ordered_ids = dialog.ordered_db_ids
                # 1. Save new order to DB
                self.db.update_reading_order(ordered_ids)

                # 2. Save all current work
                self.save_all_editors()

                # 3. Reload the entire project to rebuild tabs in the new order
                # Block signals to prevent save_all firing again
                self.top_tab_widget.blockSignals(True)
                self.editor_tab_widget.blockSignals(True)
                try:
                    current_project_details = self.db.get_item_details(self.project_id)
                    self.load_project(current_project_details)
                    self.load_all_editor_content()
                finally:
                    self.top_tab_widget.blockSignals(False)
                    self.editor_tab_widget.blockSignals(False)
                    # Re-connect the tab changed signal
                    self.top_tab_widget.currentChanged.connect(self.on_top_tab_changed)


        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not reorder readings: {e}")

    @Slot(int, int, int, int, str)
    def open_reading_tab(self, anchor_id, reading_id, outline_id, item_link_id=0, item_type=''):
        """
        Finds or creates a reading tab, switches to it,
        and tells it to select a specific outline item and/or item.
        """
        print(f"--- JUMP START ---")
        print(f"  Dashboard: Current focus is: {QApplication.instance().focusWidget()}")

        tab_widget = self.reading_tabs.get(reading_id)

        if not tab_widget:
            # Tab doesn't exist, create it
            reading_row = self.db.get_reading_details(reading_id)
            if not reading_row:
                QMessageBox.critical(self, "Error", f"Could not find reading data for ID {reading_id}")
                return

            self._programmatic_tab_change = True
            tab_widget = self._create_and_add_reading_tab(reading_row, set_current=True)
            self._programmatic_tab_change = False

            # Need to load data *before* trying to select item
            tab_widget.load_data()
        else:
            # Tab exists, just switch to it
            self._programmatic_tab_change = True
            self.top_tab_widget.setCurrentWidget(tab_widget)
            self._programmatic_tab_change = False

        # Tell the tab to select the outline item
        if hasattr(tab_widget, 'set_outline_selection'):
            print(f"  Dashboard: Queuing set_outline_selection with 50ms timer...")

            def _apply_selection(tab=tab_widget, aid=anchor_id, oid=outline_id,
                                 link_id=item_link_id, link_type=item_type):
                print(f"  Dashboard: 50ms timer FIRED. Calling set_outline_selection.")
                tab.set_outline_selection(aid, oid, link_id, link_type)

            QTimer.singleShot(50, _apply_selection)

    @Slot()
    def _on_tags_updated(self):
        """
        Called when the SynthesisTab emits a tagsUpdated signal
        (e.g., a tag was deleted or renamed).
        This forces all open reading tabs to refresh their anchor formatting.
        """
        print("Project Dashboard: Detected tag update. Refreshing UI...")
        # Refresh the synthesis tab itself (for counts)
        if self.synthesis_tab:
            self.synthesis_tab.load_tab_data(self.project_details)

        # Refresh all open reading tabs
        for reading_tab in self.reading_tabs.values():
            if hasattr(reading_tab, 'refresh_anchor_formatting'):
                reading_tab.refresh_anchor_formatting()

        if self.graph_view_tab:
            self.graph_view_tab.load_graph()

        # ---!!--- REMOVED OBSIDIAN TEST TAB ---!!---
        # if self.obsidian_test_tab:
        #     self.obsidian_test_tab.load_graph()
        # ---!!--- END REMOVED ---!!---

    @Slot(int, int, int, int, str)
    def open_reading_from_graph(self, anchor_id, reading_id, outline_id=0, item_link_id=0, item_type=''):
        """Slot to open a reading tab from the graph view."""
        self.open_reading_tab(anchor_id, reading_id, outline_id, item_link_id, item_type)

    @Slot(int)
    def open_tag_from_graph(self, tag_id):
        """Slot to open the Synthesis tab from the graph view."""
        if not self.synthesis_tab:
            return

        # 1. Switch to the Synthesis tab
        self._programmatic_tab_change = True
        self.top_tab_widget.setCurrentWidget(self.synthesis_tab)
        self.top_tab_widget.repaint()  # Force a repaint
        self._programmatic_tab_change = False

        # 2. Tell the synthesis tab to select the tag
        if hasattr(self.synthesis_tab, 'select_tag_by_id'):
            print(f"  Dashboard: Jumping to Synthesis. Loading tab data...")
            self.synthesis_tab.load_tab_data(self.project_details)
            print(f"  Dashboard: Telling Synthesis tab to select tag {tag_id}")
            self.synthesis_tab.select_tag_by_id(tag_id)
            print(f"  Dashboard: Synthesis jump complete.")

    @Slot()
    def return_to_home(self):
        # --- FIX: Close all open mindmap windows ---
        try:
            from dialogs.mindmap_editor_window import MindmapEditorWindow
            # Find all top-level widgets that are mindmap editors for *this* project
            for widget in QApplication.topLevelWidgets():
                if isinstance(widget, MindmapEditorWindow):
                    # We need to check if it belongs to this project.
                    # This requires the editor to store project_id, or we check its parent.
                    # For now, let's just save and close all of them.
                    print(f"Saving open mindmap: {widget.mindmap_name}...")
                    widget.save_mindmap(show_message=False)
                    widget.close()  # Close it
        except ImportError:
            pass  # MindmapEditorWindow not available
        except Exception as e:
            print(f"Error closing mindmap windows: {e}")
        # --- END FIX ---

        self.save_all_editors()
        self.returnToHome.emit()