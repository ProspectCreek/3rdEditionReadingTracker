import os
import sys
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QSplitter,
    QStackedWidget, QLabel
)
from PySide6.QtCore import Qt, Signal
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

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)

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
        self.splitter.addWidget(self.welcome_widget)

        # Set initial sizes from your main.py
        self.splitter.setSizes([300, 500])

        # --- Connect the signal ---
        self.project_list.projectSelected.connect(self.projectSelected.emit)
