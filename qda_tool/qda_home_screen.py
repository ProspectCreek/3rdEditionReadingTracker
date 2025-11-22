import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QPushButton, QSplitter, QFrame,
    QMessageBox, QInputDialog
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QIcon, QFont


class QDAHomeScreen(QDialog):
    """
    The graphical launcher for QDA Projects.
    Designed to replicate the 'HomeScreenWidget' of the Reading Tracker.

    Structure:
    - Left Panel: Project List + CRUD Buttons
    - Right Panel: Title + Logo/Branding + 'Open' Button
    """

    def __init__(self, db):
        super().__init__()
        self.db = db
        self.selected_ws = None  # Tuple (id, name) if selected

        self.setWindowTitle("Radar's QDA Coding Tool")
        self.resize(800, 500)  # Match the default size of the tracker

        # Use the layout logic from HomeScreenWidget
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(1)  # Thin separator like the tracker
        main_layout.addWidget(self.splitter)

        # --- LEFT PANEL (Project List) ---
        left_panel = QFrame()
        left_panel.setStyleSheet("background-color: #FFFFFF; border-right: 1px solid #E5E7EB;")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(10)

        # Header
        # (Optional: The tracker usually hides the header for the tree, but we can add a label)
        # left_layout.addWidget(QLabel("<b>My Projects</b>"))

        # List
        self.project_list = QListWidget()
        self.project_list.setAlternatingRowColors(False)
        # Style matching the Reading Tracker tree
        self.project_list.setStyleSheet("""
            QListWidget {
                border: none;
                font-size: 14px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #F3F4F6;
            }
            QListWidget::item:selected {
                background-color: #E5F3FF;
                color: #000000;
            }
        """)
        self.project_list.itemDoubleClicked.connect(self.open_project)
        left_layout.addWidget(self.project_list)

        # Buttons (Bottom of Left Panel)
        btn_layout = QHBoxLayout()
        self.btn_new = QPushButton("Add Project")
        self.btn_delete = QPushButton("Delete Project")

        # Style to match the tracker buttons
        btn_style = """
            QPushButton {
                background-color: #FFFFFF;
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                padding: 6px 12px;
                color: #374151;
            }
            QPushButton:hover {
                background-color: #F9FAFB;
            }
        """
        self.btn_new.setStyleSheet(btn_style)
        self.btn_delete.setStyleSheet(btn_style)

        self.btn_new.clicked.connect(self.create_project)
        self.btn_delete.clicked.connect(self.delete_project)

        btn_layout.addWidget(self.btn_new)
        btn_layout.addWidget(self.btn_delete)
        left_layout.addLayout(btn_layout)

        # --- RIGHT PANEL (Welcome / Logo) ---
        right_panel = QFrame()
        right_panel.setStyleSheet("background-color: #F9FAFB;")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Add spacing at the top so it isn't jammed against the window edge
        right_layout.addStretch()

        # Title Label
        self.title_label = QLabel("Qualitative Data Analysis Tool 1.0")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Using standard Segoe UI font, large and bold, matching typical app headers
        self.title_label.setStyleSheet("font-family: 'Segoe UI'; font-size: 32px; font-weight: bold; color: #1F2937;")
        right_layout.addWidget(self.title_label)

        # Spacer between Title and Logo
        right_layout.addSpacing(20)

        # Logo
        self.logo_label = QLabel()
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Try to load 'qda_logo.png', fall back to text if missing
        logo_path = os.path.join(os.getcwd(), "qda_logo.png")
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            self.logo_label.setPixmap(pixmap.scaled(
                600, 600,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))
        else:
            # If logo missing, maybe show a smaller fallback or nothing since we have the title now
            self.logo_label.setText("(Logo Placeholder)")
            self.logo_label.setStyleSheet("font-size: 18px; color: #9CA3AF;")

        right_layout.addWidget(self.logo_label)

        right_layout.addStretch()

        # "Open" Button (Big, centered/bottom, like 'Global Knowledge' buttons)
        self.btn_open_big = QPushButton("Open Selected Project")
        self.btn_open_big.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open_big.setMinimumHeight(45)
        self.btn_open_big.setStyleSheet("""
            QPushButton {
                background-color: #003366; 
                color: white; 
                font-size: 14px; 
                font-weight: bold;
                border-radius: 6px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #004488;
            }
        """)
        self.btn_open_big.clicked.connect(self.open_project)

        # Container for the big button to control width
        big_btn_container = QHBoxLayout()
        big_btn_container.addStretch()
        big_btn_container.addWidget(self.btn_open_big)
        big_btn_container.addStretch()

        right_layout.addLayout(big_btn_container)
        right_layout.addSpacing(40)  # Bottom margin

        # Add panels to splitter
        self.splitter.addWidget(left_panel)
        self.splitter.addWidget(right_panel)

        # Set Splitter Ratios (approx 30% / 70%)
        self.splitter.setSizes([300, 700])

        self.refresh_list()

    def refresh_list(self):
        self.project_list.clear()
        worksheets = self.db.get_worksheets()

        for ws in worksheets:
            # Simple list item, just the name
            item = QListWidgetItem(ws["name"])
            item.setData(Qt.UserRole, ws["id"])
            self.project_list.addItem(item)

    def create_project(self):
        name, ok = QInputDialog.getText(self, "New Project", "Project Name:")
        if ok and name.strip():
            self.db.create_worksheet(name.strip())
            self.refresh_list()

    def delete_project(self):
        item = self.project_list.currentItem()
        if not item:
            QMessageBox.information(self, "Selection", "Please select a project to delete.")
            return

        confirm = QMessageBox.question(
            self,
            "Delete Project",
            f"Are you sure you want to delete '{item.text()}'?\n\n"
            "This will delete all scenes, segments, and codes permanently.",
            QMessageBox.Yes | QMessageBox.No
        )

        if confirm == QMessageBox.Yes:
            self.db.delete_worksheet(item.data(Qt.UserRole))
            self.refresh_list()

    def open_project(self):
        item = self.project_list.currentItem()
        if item:
            self.selected_ws = (item.data(Qt.UserRole), item.text())
            self.accept()  # Closes dialog with Accepted result
        else:
            QMessageBox.information(self, "Selection", "Please select a project to open.")