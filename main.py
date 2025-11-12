import sys
import os
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QStackedWidget, QWidget,
    QLabel, QVBoxLayout
)
from PySide6.QtCore import Qt, Slot, QUrl
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

        self.initial_geometry = self.geometry()
        self.stacked_widget.setCurrentIndex(0)

        # --- Connect Signals ---
        self.home_screen.projectSelected.connect(self.show_project_dashboard)
        self.project_dashboard.returnToHome.connect(self.show_home_screen)

        # --- FIX: Removed self.resize(1200, 800) ---
        self.center_window()

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
        self.showNormal()
        self.setGeometry(self.initial_geometry)
        self.center_window()

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