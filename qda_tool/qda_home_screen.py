import os
import sys
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QSplitter,
    QStackedWidget, QLabel, QPushButton, QHBoxLayout,
    QMessageBox, QApplication, QDialog
)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QPixmap

try:
    from widgets.project_list_widget import ProjectListWidget
except ImportError:
    print("Error: Could not import ProjectListWidget")
    sys.exit(1)


class HomeScreenWidget(QWidget):
    """
    This is the main "Home" page (Page 0) of the application.
    It contains the splitter with the project list on the left
    and the logo/welcome screen on the right.
    """

    # Relay the projectSelected signal up to the MainWindow
    projectSelected = Signal(dict)

    # Signal to jump to a specific anchor (project, reading, outline)
    globalJumpRequested = Signal(int, int, int)

    def __init__(self, db_manager, spell_checker_service=None, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.spell_checker_service = spell_checker_service

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(self.splitter)

        # --- Left Panel: Project Tree ---
        self.project_list = ProjectListWidget(self.db, self)
        # When user double-clicks project in the tree, we emit projectSelected
        self.project_list.projectSelected.connect(self.projectSelected.emit)

        self.splitter.addWidget(self.project_list)

        # --- Right Panel: Logo & Global Actions ---
        right_panel_widget = QWidget()
        right_layout = QVBoxLayout(right_panel_widget)
        right_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.setSpacing(20)

        # Logo
        self.logo_label = QLabel()
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # FIX: Look for logo in current directory OR qda_tool directory
        logo_path = os.path.join(os.getcwd(), "logo.png")
        if not os.path.exists(logo_path):
            # Fallback: check if it's in qda_tool
            logo_path = os.path.join(os.getcwd(), "qda_tool", "logo.png")

        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            # Scale it nicely
            scaled_pixmap = pixmap.scaled(
                400, 400,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.logo_label.setPixmap(scaled_pixmap)
        else:
            self.logo_label.setText("Reading Tracker 3.0")
            self.logo_label.setStyleSheet("font-size: 32px; font-weight: bold; color: #555;")

        right_layout.addStretch()
        right_layout.addWidget(self.logo_label)
        right_layout.addSpacing(20)

        # "Global Knowledge Graph" Button
        self.btn_global_graph = QPushButton("Global Knowledge Graph")
        self.btn_global_graph.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_global_graph.setMinimumHeight(50)
        self.btn_global_graph.setMinimumWidth(250)
        self.btn_global_graph.setStyleSheet("""
            QPushButton {
                background-color: #2563EB; 
                color: white; 
                font-size: 16px; 
                font-weight: bold;
                border-radius: 8px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #1D4ED8;
            }
        """)
        self.btn_global_graph.clicked.connect(self.open_global_graph)
        right_layout.addWidget(self.btn_global_graph)

        # "Global Tag Manager" Button
        self.btn_global_tags = QPushButton("Global Tag Manager")
        self.btn_global_tags.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_global_tags.setMinimumHeight(50)
        self.btn_global_tags.setMinimumWidth(250)
        self.btn_global_tags.setStyleSheet("""
            QPushButton {
                background-color: #10B981; 
                color: white; 
                font-size: 16px; 
                font-weight: bold;
                border-radius: 8px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #059669;
            }
        """)
        self.btn_global_tags.clicked.connect(self.open_global_tag_manager)
        right_layout.addWidget(self.btn_global_tags)

        # --- CHANGED: "Connections" -> "Launch QDA Tool" ---
        self.btn_connections = QPushButton("Launch QDA Tool")
        self.btn_connections.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_connections.setMinimumHeight(50)
        self.btn_connections.setMinimumWidth(250)
        self.btn_connections.setStyleSheet("""
            QPushButton {
                background-color: #F59E0B; 
                color: white; 
                font-size: 16px; 
                font-weight: bold;
                border-radius: 8px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #D97706;
            }
        """)
        # Connect to the new launch method
        self.btn_connections.clicked.connect(self.launch_qda_tool)
        right_layout.addWidget(self.btn_connections)

        right_layout.addStretch()

        self.splitter.addWidget(right_panel_widget)
        self.splitter.setSizes([300, 700])

    @Slot()
    def launch_qda_tool(self):
        """Launches the QDA Home Screen."""
        try:
            # 1. Define the path to the qda_tool directory
            qda_path = os.path.join(os.getcwd(), "qda_tool")

            # 2. Check if it exists
            if not os.path.exists(qda_path):
                QMessageBox.critical(self, "Error",
                                     f"Could not find the 'qda_tool' folder at:\n{qda_path}\n\n"
                                     "Please ensure the QDA tool files are in a subdirectory named 'qda_tool'.")
                return

            # 3. CRITICAL FIX: Add qda_tool to sys.path so internal imports work
            # This fixes "No module named 'qda_database_manager'"
            if qda_path not in sys.path:
                sys.path.insert(0, qda_path)

            # 4. Import directly from the package
            from qda_tool.qda_database_manager import QDAManager
            from qda_tool.qda_home_screen import QDAHomeScreen
            from qda_tool.qda_coding_app import QDAWindow

            # 5. Initialize
            qda_db = QDAManager()

            # 6. Launch
            launcher = QDAHomeScreen(qda_db)
            if launcher.exec() == QDialog.Accepted and launcher.selected_ws:
                ws_id, ws_name = launcher.selected_ws
                self.qda_window = QDAWindow(qda_db, ws_id, ws_name)
                self.qda_window.show()

        except Exception as e:
            import traceback
            error_msg = traceback.format_exc()
            QMessageBox.critical(self, "Launch Error", f"Failed to launch QDA Tool:\n\n{error_msg}")

    @Slot()
    def open_global_graph(self):
        """
        Imports and opens the GlobalGraphDialog.
        """
        try:
            from dialogs.global_graph_dialog import GlobalGraphDialog

            # Check if already open?
            for widget in QApplication.topLevelWidgets():
                if isinstance(widget, GlobalGraphDialog):
                    widget.activateWindow()
                    widget.raise_()
                    widget.showMaximized()
                    return

            dialog = GlobalGraphDialog(self.db, self)
            dialog.jumpToAnchor.connect(self.globalJumpRequested.emit)
            dialog.showMaximized()

        except ImportError:
            QMessageBox.critical(self, "Error", "GlobalGraphDialog could not be loaded.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open global connections: {e}")

    @Slot()
    def open_global_tag_manager(self):
        """
        Imports and opens the GlobalTagManagerDialog.
        """
        try:
            from dialogs.global_tag_manager_dialog import GlobalTagManagerDialog

            dialog = GlobalTagManagerDialog(self.db, self)

            # Connect the jump signal
            dialog.jumpToAnchor.connect(self.globalJumpRequested.emit)

            # Connect accepted to refresh list (in case tags changed)
            dialog.accepted.connect(self.project_list.load_data_to_tree)

            dialog.exec()

        except ImportError:
            QMessageBox.critical(self, "Error", "GlobalTagManagerDialog could not be loaded.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open global tag manager: {e}")