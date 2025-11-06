import sys
import os
from pathlib import Path  # <-- added
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QStackedWidget, QWidget,
    QLabel, QVBoxLayout
)
from PySide6.QtCore import Qt, Slot, QUrl  # <-- added QUrl
# --- NEW: Import for Web Engine ---
from PySide6.QtWebEngineCore import QWebEngineProfile

# --- Dependency Checks ---
try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
except ImportError:
    print("--- FATAL ERROR ---")
    print("PySide6-WebEngine is not installed.")
    print("Please install it by running: pip install PySide6")
    sys.exit(1)

# Add widgets and tabs directories to the Python path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'widgets'))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tabs'))

try:
    from database_manager import DatabaseManager
    from widgets.home_screen_widget import HomeScreenWidget
    from widgets.project_dashboard_widget import ProjectDashboardWidget
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
        self.project_dashboard.addReadingTab.connect(self.add_reading_tab)

        self.resize(1200, 800)
        self.center_window()

    @Slot(dict)
    def show_project_dashboard(self, project_details):
        """Switches to the project dashboard and loads its data."""
        try:
            # --- NEW WORKFLOW ---
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
        # --- NEW: Save data before switching ---
        self.project_dashboard.save_all_editors()

        self.stacked_widget.setCurrentIndex(0)
        self.showNormal()
        self.setGeometry(self.initial_geometry)
        self.center_window()

    @Slot(str, int)
    def add_reading_tab(self, reading_title, reading_id):
        """
        Adds a new top-level tab for a reading.

        Change: instead of a placeholder label, embed a QWebEngineView that loads
        ./editor.html via file:// (so web_resources/quill.js & quill.snow.css work offline).
        We preserve your original container QWidget + QVBoxLayout structure so any code
        in ProjectDashboard that expects a QWidget tab still works as before.
        """
        # Container (keeps your original structure intact)
        reading_widget = QWidget()
        layout = QVBoxLayout(reading_widget)

        # Create the web view
        view = QWebEngineView(reading_widget)

        # Resolve local editor.html next to main.py
        html_path = Path(__file__).with_name("editor.html")
        if not html_path.exists():
            # If editor.html is missing, fall back to the original label so nothing breaks
            fallback = QLabel(f"Editor for '{reading_title}' (ID: {reading_id}) will go here.")
            layout.addWidget(fallback)
        else:
            # Load the local HTML (offline)
            view.setUrl(QUrl.fromLocalFile(str(html_path)))

            # After the page loads, set starter content (you can swap to DB content later)
            def _on_load_finished(ok: bool):
                if not ok:
                    # Graceful fallback: show a simple label if the page failed to load
                    layout.removeWidget(view)
                    view.deleteLater()
                    layout.addWidget(QLabel(
                        f"Failed to load editor.html for '{reading_title}' (ID: {reading_id})."
                    ))
                    return

                # JS bridge defined in editor.html:
                #   window.setEditorContent(htmlString)
                starter_html = f"<p><em>{reading_title}</em> — ready to edit.</p>"
                view.page().runJavaScript(f"setEditorContent({repr(starter_html)})")

            view.loadFinished.connect(_on_load_finished)
            layout.addWidget(view)

        index = self.project_dashboard.top_tab_widget.addTab(reading_widget, reading_title)
        self.project_dashboard.top_tab_widget.setCurrentIndex(index)

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


def main():
    # --- NEW: Enable Remote Debugging ---
    # This MUST be set before QApplication is created
    os.environ["QTWEBENGINE_REMOTE_DEBUGGING"] = "9222"

    app = QApplication(sys.argv)

    # --- NEW: Initialize Web Engine Profile ---
    # This MUST be done after QApplication is created and
    # before any QWebEngineView is created.
    profile = QWebEngineProfile.defaultProfile()
    profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.MemoryHttpCache)

    db = DatabaseManager()
    window = MainWindow(db)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

