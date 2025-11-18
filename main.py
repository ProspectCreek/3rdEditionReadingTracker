# prospectcreek/3rdeditionreadingtracker/3rdEditionReadingTracker-0eada8809e03f78f9e304f58f06c5f5a03a32c4f/main.py
import sys
import os
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QStackedWidget, QWidget,
    QLabel, QVBoxLayout
)
# --- FIX: Import QSize ---
from PySide6.QtCore import Qt, Slot, QUrl, QTimer, QSize
# --- END FIX ---
from PySide6.QtWebEngineCore import QWebEngineProfile
from PySide6.QtWebEngineWidgets import QWebEngineView

# Add widgets and tabs directories to the Python path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'widgets'))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tabs'))

try:
    from database_manager import DatabaseManager
    from utils.spell_checker import GlobalSpellChecker  # <-- IMPORT NEW
    from widgets.home_screen_widget import HomeScreenWidget
    from widgets.project_dashboard_widget import ProjectDashboardWidget
    # We only import this for the type hint in closeEvent
    # from dialogs.mindmap_editor_window import MindmapEditorWindow # <-- REMOVED
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)

# --- NEW: Modern Light Theme Stylesheet ---
MODERN_LIGHT_STYLESHEET = """
/* General Window & Background */
QMainWindow, QDialog {
    background-color: #F9FAFB;
    color: #374151;
}

QWidget {
    background-color: #F9FAFB;
    color: #374151;
    font-family: "Segoe UI", "Helvetica Neue", sans-serif;
    font-size: 14px;
}

/* Text Areas */
QLabel {
    color: #374151;
    background: transparent;
}

QLineEdit, QTextEdit, QPlainTextEdit, QTextBrowser {
    background-color: #FFFFFF;
    border: 1px solid #D1D5DB;
    border-radius: 6px;
    padding: 6px;
    color: #111827;
    selection-background-color: #BFDBFE;
    selection-color: #111827;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QTextBrowser:focus {
    border: 1px solid #2563EB;
}

/* Lists & Trees */
QListWidget, QTreeWidget {
    background-color: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 6px;
    outline: none;
}

QListWidget::item, QTreeWidgetItem {
    padding: 6px;
    border-bottom: 1px solid #F3F4F6;
}

QListWidget::item:selected, QTreeWidget::item:selected {
    background-color: #EFF6FF;
    color: #1E40AF;
    border-left: 3px solid #2563EB;
}

/* --- Style Checkboxes INSIDE Lists/Trees (To-Do List) --- */
QListWidget::indicator, QTreeWidget::indicator {
    width: 18px;
    height: 18px;
    border: 1px solid #D1D5DB;
    border-radius: 4px;
    background-color: #FFFFFF;
}

QListWidget::indicator:checked, QTreeWidget::indicator:checked {
    background-color: #2563EB;
    border: 1px solid #2563EB;
    image: url(data:image/svg+xml;base64,PHN2ZyB2aWV3Qm94PSIwIDAgMjQgMjQiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyIgZmlsbD0ibm9uZSIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLXdpZHRoPSIzIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiPjxwb2x5bGluZSBwb2ludHM9IjIwIDYgOSAxNyA0IDEyIi8+PC9zdmc+);
}

QListWidget::indicator:hover, QTreeWidget::indicator:hover {
    border-color: #2563EB;
}
/* --------------------------------------------------------- */

QHeaderView::section {
    background-color: #F3F4F6;
    padding: 4px;
    border: none;
    font-weight: bold;
    color: #4B5563;
}

/* Buttons */
QPushButton {
    background-color: #FFFFFF;
    border: 1px solid #D1D5DB;
    border-radius: 6px;
    padding: 6px 12px;
    color: #374151;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #F3F4F6;
    border-color: #9CA3AF;
}

QPushButton:pressed {
    background-color: #E5E7EB;
}

/* Tab Widget */
QTabWidget::pane {
    border: 1px solid #E5E7EB;
    background-color: #FFFFFF;
    border-radius: 6px;
}

QTabBar::tab {
    background-color: #F3F4F6;
    color: #6B7280;
    padding: 8px 16px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    border: 1px solid #E5E7EB;
    margin-right: 2px;
}

QTabBar::tab:selected {
    background-color: #FFFFFF;
    color: #2563EB;
    border-bottom: 1px solid #FFFFFF; /* Blend with pane */
    font-weight: bold;
}

QTabBar::tab:hover {
    background-color: #FFFFFF;
}

/* Menus */
QMenuBar {
    background-color: #FFFFFF;
    border-bottom: 1px solid #E5E7EB;
}

QMenuBar::item {
    padding: 6px 10px;
    background: transparent;
}

QMenuBar::item:selected {
    background-color: #F3F4F6;
}

QMenu {
    background-color: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 6px;
    padding: 4px;
}

QMenu::item {
    padding: 6px 24px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: #EFF6FF;
    color: #1E3A8A;
}

/* Splitter */
QSplitter::handle {
    background-color: #E5E7EB;
}

/* Group Box / Frames */
QGroupBox {
    border: 1px solid #E5E7EB;
    border-radius: 6px;
    margin-top: 1.5em;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 3px;
    color: #374151;
    font-weight: bold;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background: #F3F4F6;
    width: 10px;
    margin: 0px 0px 0px 0px;
}
QScrollBar::handle:vertical {
    background: #D1D5DB;
    min-height: 20px;
    border-radius: 5px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* --- Radio Buttons & Standalone Checkboxes --- */

QRadioButton, QCheckBox {
    background: transparent;
    spacing: 6px;
    color: #374151;
    padding: 4px;
    min-height: 20px;
}

/* Radio Button: Use SVG images to guarantee perfect circles */
QRadioButton::indicator {
    width: 18px;
    height: 18px;
    border: none;
    background: transparent;
    /* Unchecked: Gray Circle */
    image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTgiIGhlaWdodD0iMTgiIHZpZXdCb3g9IjAgMCAxOCAxOCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48Y2lyY2xlIGN4PSI5IiBjeT0iOSIgcj0iOC41IiBmaWxsPSJ3aGl0ZSIgc3Ryb2tlPSIjOTQ5NDk0IiBzdHJva2Utd2lkdGg9IjEiLz48L3N2Zz4=);
}

QRadioButton::indicator:checked {
    /* Checked: Blue Donut */
    image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTgiIGhlaWdodD0iMTgiIHZpZXdCb3g9IjAgMCAxOCAxOCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48Y2lyY2xlIGN4PSI5IiBjeT0iOSIgcj0iOC41IiBmaWxsPSJ3aGl0ZSIgc3Ryb2tlPSIjMjU2M0VCIiBzdHJva2Utd2lkdGg9IjEiLz48Y2lyY2xlIGN4PSI5IiBjeT0iOSIgcj0iNCIgZmlsbD0iIzI1NjNFQiIvPjwvc3ZnPg==);
}

QRadioButton::indicator:hover {
    /* Hover: Slightly darker gray outline */
    image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTgiIGhlaWdodD0iMTgiIHZpZXdCb3g9IjAgMCAxOCAxOCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48Y2lyY2xlIGN4PSI5IiBjeT0iOSIgcj0iOC41IiBmaWxsPSJ3aGl0ZSIgc3Ryb2tlPSIjNjY2NjY2IiBzdHJva2Utd2lkdGg9IjEiLz48L3N2Zz4=);
}

/* Checkbox: Square with Checkmark */
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1px solid #D1D5DB;
    border-radius: 3px;
    background-color: #FFFFFF;
}

QCheckBox::indicator:checked {
    background-color: #2563EB;
    border: 1px solid #2563EB;
    image: url(data:image/svg+xml;base64,PHN2ZyB2aWV3Qm94PSIwIDAgMjQgMjQiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyIgZmlsbD0ibm9uZSIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLXdpZHRoPSIzIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiPjxwb2x5bGluZSBwb2ludHM9IjIwIDYgOSAxNyA0IDEyIi8+PC9zdmc+);
}

QCheckBox::indicator:hover {
    border-color: #2563EB;
}
"""


# --- END NEW ---


class MainWindow(QMainWindow):
    def __init__(self, db, spell_checker_service):
        super().__init__()
        self.db = db
        self.spell_checker_service = spell_checker_service  # <-- STORE SERVICE

        # --- MODIFIED: Set initial title ---
        self.base_title = "Tyler's Reading Tracker"
        self.setWindowTitle(self.base_title)
        # --- END MODIFIED ---

        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        # --- Page 0: Home Screen ---
        self.home_screen = HomeScreenWidget(self.db, self.spell_checker_service)  # <-- PASS SERVICE
        self.stacked_widget.addWidget(self.home_screen)

        # --- Page 1: Project Dashboard ---
        self.project_dashboard = ProjectDashboardWidget(self.db, self.spell_checker_service)  # <-- PASS SERVICE
        self.stacked_widget.addWidget(self.project_dashboard)

        self.stacked_widget.setCurrentIndex(0)

        # --- FIX: Store the "correct" home screen size ---
        # 300px (list) + 650px (logo panel) = 950px width
        self.setMinimumSize(950, 750)
        self.home_screen_size = QSize(950, 750)  # <-- Store the correct size
        self.resize(self.home_screen_size)  # <-- Apply it
        # --- END FIX ---

        self.center_window()

        # --- Connect Signals ---
        self.home_screen.projectSelected.connect(self.show_project_dashboard)
        self.project_dashboard.returnToHome.connect(self.show_home_screen)

        # --- MODIFIED: Connect home screen's jump request (Step 3.3) ---
        self.home_screen.globalJumpRequested.connect(self.open_project_from_global)
        # --- END MODIFIED ---

    @Slot(dict)
    def show_project_dashboard(self, project_details):
        """Switches to the project dashboard and loads its data."""
        try:
            # 1. Load project structure (creates tabs, but doesn't load text)
            self.project_dashboard.load_project(project_details)

            # --- NEW: Update Window Title ---
            project_name = project_details.get('name', 'Untitled Project')
            self.setWindowTitle(f"{self.base_title}: {project_name}")
            # --- END NEW ---

            # 2. Switch stack to make dashboard visible
            self.stacked_widget.setCurrentIndex(1)
            self.showMaximized()
            # 3. NOW, load content into the (visible) editors
            self.project_dashboard.load_all_editor_content()
        except Exception as e:
            print(f"Error loading project dashboard: {e}")

    @Slot()
    def show_home_screen(self):
        """
        Saves data, then switches back to the home screen.
        """
        self.project_dashboard.save_all_editors()

        self.stacked_widget.setCurrentIndex(0)

        # --- NEW: Reset Window Title ---
        self.setWindowTitle(self.base_title)
        # --- END NEW ---

        # --- FIX: Explicitly resize to the "correct" smaller size ---
        self.showNormal()
        self.resize(self.home_screen_size)  # <-- Force the size back
        # --- END FIX ---

        self.center_window()

        # --- FIX 2: Reset the splitter sizes ---
        QTimer.singleShot(0, self.home_screen.reset_splitter_sizes)
        # --- END FIX 2 ---

    def center_window(self):
        """Centers the main window on the screen."""
        try:
            screen_geo = self.screen().availableGeometry()
            self.move(
                (screen_geo.width() - self.width()) // 2,
                (screen_geo.height() - self.height()) // 2
            )
        except Exception as e:
            print(f"Warning: Could not center window. {e}")

    # --- NEW: Slot for Global Connections jump (Step 3.3) ---
    @Slot(int, int, int)
    def open_project_from_global(self, project_id, reading_id, outline_id):
        """
        Receives a signal from the Global Connections graph and jumps to
        the specified project/reading/anchor.
        """
        try:
            project_details = self.db.get_item_details(project_id)
            if not project_details:
                print(f"Error in open_project_from_global: Could not find project {project_id}")
                return

            # Switch to dashboard
            self.show_project_dashboard(project_details)

            # --- FIX: Only open reading tab if ID is valid ---
            if reading_id and reading_id > 0:
                QTimer.singleShot(150, lambda: self.project_dashboard.open_reading_tab(0, reading_id, outline_id))
            # --- END FIX ---

        except Exception as e:
            print(f"Error in open_project_from_global: {e}")

    # --- END NEW ---

    # --- NEW: Save on Close ---
    def closeEvent(self, event):
        """Overrides the main window's close event to save all data."""
        print("Closing application, saving all data...")

        # 1. Save all editors in the main project dashboard
        if self.project_dashboard:
            self.project_dashboard.save_all_editors()

        # 2. Find and save any open Mindmap editor windows
        # --- FIX: Import locally inside the function ---
        try:
            from dialogs.mindmap_editor_window import MindmapEditorWindow
            # Find all top-level widgets that are mindmap editors
            for widget in QApplication.topLevelWidgets():
                if isinstance(widget, MindmapEditorWindow):
                    print(f"Saving open mindmap: {widget.mindmap_name}...")
                    widget.save_mindmap(show_message=False)
                    widget.close()  # Close it
        except ImportError:
            print("Could not import MindmapEditorWindow for saving.")
        except Exception as e:
            print(f"Error during mindmap save on close: {e}")
        # --- END FIX ---

        print("Save complete. Exiting.")
        event.accept()  # Proceed with closing
    # --- END NEW ---


def main():
    os.environ["QTWEBENGINE_REMOTE_DEBUGGING"] = "9222"
    app = QApplication(sys.argv)

    # --- NEW: Apply the stylesheet ---
    app.setStyleSheet(MODERN_LIGHT_STYLESHEET)
    # --- END NEW ---

    profile = QWebEngineProfile.defaultProfile()
    profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.MemoryHttpCache)

    spell_checker_service = GlobalSpellChecker()  # <-- CREATE INSTANCE
    db = DatabaseManager()
    window = MainWindow(db, spell_checker_service)  # <-- PASS INSTANCE
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
