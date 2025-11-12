import os
import sys
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QSplitter,
    QStackedWidget, QLabel, QPushButton, QHBoxLayout,
    QMessageBox
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

    # --- FIX: Add the missing signal definition ---
    globalJumpRequested = Signal(int, int, int)  # project_id, reading_id, outline_id

    # --- END FIX ---

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager  # --- NEW: Store db_manager ---

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(self.splitter)

        # --- 1. Left Panel (The Project List) ---
        self.project_list = ProjectListWidget(db_manager)
        self.splitter.addWidget(self.project_list)

        # --- 2. Right Panel (Logo) ---
        # Note: We are *not* using a QStackedWidget here anymore,
        # as this *entire widget* will be hidden.

        self.welcome_widget = QWidget()
        welcome_layout = QVBoxLayout(self.welcome_widget)
        welcome_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo_label = QLabel()

        logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logo.png")
        pixmap = QPixmap(logo_path)

        if pixmap.isNull():
            print(f"Warning: Could not load logo.png from {logo_path}")
            self.logo_label.setText("logo.png not found")
        else:
            self.logo_label.setPixmap(pixmap.scaled(
                600, 600,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))

        welcome_layout.addWidget(self.logo_label)

        # --- NEW: Add Global Graph Button ---
        welcome_layout.addStretch(1)  # Add stretch before button

        # --- RENAMED ---
        self.btn_global_graph = QPushButton("Open Global Knowledge Connections")
        font = self.btn_global_graph.font()
        font.setPointSize(12)
        self.btn_global_graph.setFont(font)
        self.btn_global_graph.setMinimumHeight(40)
        self.btn_global_graph.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_global_graph.setStyleSheet("""
            QPushButton {
                background-color: #003366;
                color: white;
                border-radius: 5px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #004488;
            }
        """)

        # --- NEW: Manage Tags Button ---
        self.btn_manage_tags = QPushButton("Manage All Tags")
        self.btn_manage_tags.setFont(font)
        self.btn_manage_tags.setMinimumHeight(40)
        self.btn_manage_tags.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_manage_tags.setStyleSheet("""
            QPushButton {
                background-color: #444444;
                color: white;
                border-radius: 5px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #666666;
            }
        """)
        # --- END NEW ---

        # Center button
        button_layout = QHBoxLayout()
        button_layout.addStretch(1)
        button_layout.addWidget(self.btn_global_graph)
        button_layout.addWidget(self.btn_manage_tags)  # <-- Add new button
        button_layout.addStretch(1)
        welcome_layout.addLayout(button_layout)
        welcome_layout.addStretch(1)  # Add stretch after button

        self.btn_global_graph.clicked.connect(self.open_global_graph)
        self.btn_manage_tags.clicked.connect(self.open_global_tag_manager)  # <-- Connect new button
        # --- END NEW ---

        self.splitter.addWidget(self.welcome_widget)

        # --- FIX: Set correct splitter size ---
        # 300 for list + 650 for logo panel (600px logo + 50px padding)
        self.splitter.setSizes([300, 650])
        # --- END FIX ---

        # --- Connect the signal ---
        self.project_list.projectSelected.connect(self.projectSelected.emit)

    # --- NEW: Public method to fix splitter ---
    def reset_splitter_sizes(self):
        """Forces the splitter back to its default 300:650 ratio."""
        # --- FIX: Set correct splitter size ---
        self.splitter.setSizes([300, 650])
        # --- END FIX ---

    # --- END NEW ---

    # --- NEW: Slot to open global graph ---
    @Slot()
    def open_global_graph(self):
        """
        Imports and opens the GlobalGraphDialog.
        Imported locally to prevent circular dependencies.
        """
        try:
            from dialogs.global_graph_dialog import GlobalGraphDialog

            # Pass the db manager to the dialog
            dialog = GlobalGraphDialog(self.db, self)

            # --- FIX: Connect the jumpToAnchor signal ---
            dialog.jumpToAnchor.connect(self.globalJumpRequested.emit)
            # --- END FIX ---

            dialog.exec()  # Open as a modal dialog

        except ImportError:
            QMessageBox.critical(self, "Error",
                                 # --- RENAMED ---
                                 "GlobalGraphDialog could not be loaded. Please check 'dialogs/global_graph_dialog.py'.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open global connections: {e}")

    # --- END NEW ---

    # --- NEW: Slot to open global tag manager ---
    @Slot()
    def open_global_tag_manager(self):
        """
        Imports and opens the GlobalTagManagerDialog.
        """
        try:
            from dialogs.global_tag_manager_dialog import GlobalTagManagerDialog

            # Pass the db manager to the dialog
            dialog = GlobalTagManagerDialog(self.db, self)

            # Connect the accepted signal to refresh the project list,
            # in case this impacts any future UI elements there.
            dialog.accepted.connect(self.project_list.load_data_to_tree)
            dialog.exec()  # Open as a modal dialog

        except ImportError:
            QMessageBox.critical(self, "Error",
                                 "GlobalTagManagerDialog could not be loaded. Please check 'dialogs/global_tag_manager_dialog.py'.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open global tag manager: {e}")
    # --- END NEW ---