# main.py
import os
import sys

from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget
from PySide6.QtCore import Slot, QTimer, QSize
from PySide6.QtWebEngineCore import QWebEngineProfile

# Add widgets and tabs directories to the Python path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(BASE_DIR, "widgets"))
sys.path.append(os.path.join(BASE_DIR, "tabs"))

try:
    from database_manager import DatabaseManager
    from utils.spell_checker import GlobalSpellChecker
    from widgets.home_screen_widget import HomeScreenWidget
    from widgets.project_dashboard_widget_v4 import ProjectDashboardWidgetV4 as ProjectDashboardWidget
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)

APP_VERSION = "4.0"
APP_TITLE = f"Moose's Reading Tracker {APP_VERSION}"

MODERN_LIGHT_STYLESHEET = """
QMainWindow, QDialog, QWidget {
    background-color: #F9FAFB;
    color: #374151;
    font-family: "Segoe UI", "Helvetica Neue", sans-serif;
    font-size: 14px;
}
QLabel { color: #374151; background: transparent; }
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
QListWidget, QTreeWidget {
    background-color: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 6px;
    outline: none;
}
QListWidget::item:selected, QTreeWidget::item:selected {
    background-color: #E5F3FF;
    color: #000000;
}
QPushButton {
    background-color: #FFFFFF;
    border: 1px solid #D1D5DB;
    border-radius: 6px;
    padding: 6px 12px;
    color: #374151;
    font-weight: 600;
}
QPushButton:hover { background-color: #F3F4F6; border-color: #9CA3AF; }
QPushButton:pressed { background-color: #E5E7EB; }
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
    border-bottom: 1px solid #FFFFFF;
    font-weight: bold;
}
QMenuBar { background-color: #FFFFFF; border-bottom: 1px solid #E5E7EB; }
QMenuBar::item { padding: 6px 10px; background: transparent; }
QMenuBar::item:selected { background-color: #F3F4F6; }
QMenu { background-color: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 6px; padding: 4px; }
QMenu::item { padding: 6px 24px; border-radius: 4px; }
QMenu::item:selected { background-color: #EFF6FF; color: #1E3A8A; }
QSplitter::handle { background-color: #E5E7EB; }
QHeaderView::section {
    background-color: #F3F4F6;
    padding: 4px;
    border: none;
    font-weight: bold;
    color: #4B5563;
}
QRadioButton, QCheckBox {
    background: transparent;
    spacing: 6px;
    color: #374151;
    padding: 4px;
    min-height: 20px;
}
"""


class MainWindow(QMainWindow):
    def __init__(self, db, spell_checker_service):
        super().__init__()
        self.db = db
        self.spell_checker_service = spell_checker_service
        self.base_title = APP_TITLE
        self.setWindowTitle(self.base_title)

        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        self.home_screen = HomeScreenWidget(self.db, self.spell_checker_service)
        self.stacked_widget.addWidget(self.home_screen)

        self.project_dashboard = ProjectDashboardWidget(self.db, self.spell_checker_service)
        self.stacked_widget.addWidget(self.project_dashboard)

        self.stacked_widget.setCurrentIndex(0)
        self.setMinimumSize(1000, 700)
        self.home_screen_size = QSize(1000, 700)
        self.resize(self.home_screen_size)
        self.center_window()

        self.home_screen.projectSelected.connect(self.show_project_dashboard)
        self.project_dashboard.returnToHome.connect(self.show_home_screen)
        self.home_screen.globalJumpRequested.connect(self.open_project_from_global)

    @Slot(dict)
    def show_project_dashboard(self, project_details):
        try:
            self.project_dashboard.load_project(project_details)
            project_name = project_details.get("name", "Untitled Project")
            self.setWindowTitle(f"{self.base_title}: {project_name}")
            self.stacked_widget.setCurrentIndex(1)
            self.showMaximized()
            self.project_dashboard.load_all_editor_content()
        except Exception as e:
            print(f"Error loading project dashboard: {e}")

    @Slot()
    def show_home_screen(self):
        self.project_dashboard.save_all_editors()
        self.stacked_widget.setCurrentIndex(0)
        self.setWindowTitle(self.base_title)
        self.showNormal()
        self.resize(self.home_screen_size)
        self.center_window()
        QTimer.singleShot(0, self.home_screen.reset_splitter_sizes)

    def center_window(self):
        try:
            screen_geo = self.screen().availableGeometry()
            self.move(
                (screen_geo.width() - self.width()) // 2,
                (screen_geo.height() - self.height()) // 2,
            )
        except Exception as e:
            print(f"Warning: Could not center window. {e}")

    @Slot(int, int, int)
    def open_project_from_global(self, project_id, reading_id, outline_id):
        try:
            project_details = self.db.get_item_details(project_id)
            if not project_details:
                print(f"Error in open_project_from_global: Could not find project {project_id}")
                return

            self.show_project_dashboard(project_details)
            if reading_id and reading_id > 0:
                QTimer.singleShot(
                    150,
                    lambda: self.project_dashboard.open_reading_tab(0, reading_id, outline_id),
                )
        except Exception as e:
            print(f"Error in open_project_from_global: {e}")

    def closeEvent(self, event):
        print("Closing application, saving all data...")
        if self.project_dashboard:
            self.project_dashboard.save_all_editors()

        try:
            from dialogs.mindmap_editor_window import MindmapEditorWindow

            for widget in QApplication.topLevelWidgets():
                if isinstance(widget, MindmapEditorWindow):
                    print(f"Saving open mindmap: {widget.mindmap_name}...")
                    widget.save_mindmap(show_message=False)
                    widget.close()
        except ImportError:
            print("Could not import MindmapEditorWindow for saving.")
        except Exception as e:
            print(f"Error during mindmap save on close: {e}")

        print("Save complete. Exiting.")
        event.accept()


def main():
    os.environ["QTWEBENGINE_REMOTE_DEBUGGING"] = "9222"
    app = QApplication(sys.argv)
    app.setApplicationName(APP_TITLE)
    app.setApplicationVersion(APP_VERSION)
    app.setStyleSheet(MODERN_LIGHT_STYLESHEET)

    profile = QWebEngineProfile.defaultProfile()
    profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.MemoryHttpCache)

    spell_checker_service = GlobalSpellChecker()
    db = DatabaseManager()
    window = MainWindow(db, spell_checker_service)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
