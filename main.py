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
    from widgets.home_screen_widget import HomeScreenWidget
    from widgets.project_dashboard_widget import ProjectDashboardWidget
    # We only import this for the type hint in closeEvent
    # from dialogs.mindmap_editor_window import MindmapEditorWindow # <-- REMOVED
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)


class MainWindow(QMainWindow):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.setWindowTitle("Reading Tracker (PySide6 Edition)")

        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        # --- Page 0: Home Screen ---
        self.home_screen = HomeScreenWidget(self.db)
        self.stacked_widget.addWidget(self.home_screen)

        # --- Page 1: Project Dashboard ---
        self.project_dashboard = ProjectDashboardWidget(self.db)
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

            # Tell dashboard to open the tab
            # Use QTimer to run *after* the dashboard is fully loaded and visible
            QTimer.singleShot(150, lambda: self.project_dashboard.open_reading_tab(0, reading_id, outline_id))
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

    profile = QWebEngineProfile.defaultProfile()
    profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.MemoryHttpCache)

    db = DatabaseManager()
    window = MainWindow(db)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()