# tabs/attachments_tab.py
import sys
import os
import shutil
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QMenu, QInputDialog, QMessageBox, QFileDialog, QLabel, QDialog
)
from PySide6.QtCore import Qt, Signal, QUrl, QSize
from PySide6.QtGui import QAction, QDesktopServices, QIcon, QPixmap, QColor, QFont

# Import dialogs
try:
    from dialogs.reorder_dialog import ReorderDialog
except ImportError:
    print("Error: Could not import ReorderDialog for AttachmentsTab")
    ReorderDialog = None


class AttachmentsTab(QWidget):
    """
    A widget for adding, removing, and opening file attachments
    associated with a specific reading.
    """
    # Signal to tell the dashboard/main window to open the PDF Node Viewer
    # Sends: (reading_id, attachment_id, file_path)
    openPdfNodesRequested = Signal(int, int, str)

    def __init__(self, db, reading_id: int, parent=None):
        super().__init__(parent)
        self.db = db
        self.reading_id = reading_id

        # Define project root and attachments directory
        self.project_root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.attachments_dir = os.path.join(self.project_root_dir, "Attachments")
        self.reading_attachments_dir = os.path.join(self.attachments_dir, str(self.reading_id))
        os.makedirs(self.reading_attachments_dir, exist_ok=True)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(4)

        # List widget to display attachments
        self.list_widget = QListWidget()
        self.list_widget.setSpacing(2)
        main_layout.addWidget(self.list_widget)

        # Button layout
        button_layout = QHBoxLayout()
        self.btn_add_attachment = QPushButton("Add Attachment...")

        # --- NEW BUTTON ---
        self.btn_open_nodes = QPushButton("Open Selected PDF in Nodes")
        self.btn_open_nodes.setToolTip("Open the selected PDF in the spatial node viewer.")
        self.btn_open_nodes.setEnabled(False)  # Disabled until selection
        # ------------------

        button_layout.addWidget(self.btn_open_nodes)  # Add to left
        button_layout.addStretch()
        button_layout.addWidget(self.btn_add_attachment)
        main_layout.addLayout(button_layout)

        # --- Connections ---
        self.btn_add_attachment.clicked.connect(self._add_attachment)
        self.btn_open_nodes.clicked.connect(self._open_pdf_nodes)  # Connect new button

        self.list_widget.itemDoubleClicked.connect(self._open_attachment)
        self.list_widget.currentItemChanged.connect(self._update_button_state)

        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)

        self.load_attachments()

    def load_attachments(self):
        """Reloads the list of attachments from the database."""
        self.list_widget.clear()
        try:
            attachments = self.db.get_attachments(self.reading_id)
            if not attachments:
                item = QListWidgetItem("No attachments added.")
                item.setFlags(Qt.ItemFlag.NoItemFlags)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                item.setForeground(QColor("#888888"))
                font = item.font()
                font.setItalic(True)
                item.setFont(font)

                self.list_widget.addItem(item)
                self.btn_open_nodes.setEnabled(False)
                return

            for att in attachments:
                item = QListWidgetItem(att['display_name'])
                item.setData(Qt.ItemDataRole.UserRole, att['id'])
                item.setData(Qt.ItemDataRole.UserRole + 1, att['file_path'])
                self.list_widget.addItem(item)

            self._update_button_state()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load attachments: {e}")

    def _update_button_state(self):
        """Enable/Disable the PDF Node button based on selection."""
        item = self.list_widget.currentItem()
        if not item or item.data(Qt.ItemDataRole.UserRole) is None:
            self.btn_open_nodes.setEnabled(False)
            return

        # Check file extension
        relative_path = item.data(Qt.ItemDataRole.UserRole + 1)
        if relative_path and relative_path.lower().endswith(".pdf"):
            self.btn_open_nodes.setEnabled(True)
        else:
            self.btn_open_nodes.setEnabled(False)

    def show_context_menu(self, position):
        """Shows the right-click menu."""
        menu = QMenu(self)
        item = self.list_widget.itemAt(position)

        add_action = QAction("Add Attachment...", self)
        add_action.triggered.connect(self._add_attachment)
        menu.addAction(add_action)

        if item and item.data(Qt.ItemDataRole.UserRole) is not None:
            # Item-specific actions
            menu.addSeparator()

            # --- NEW: Open in Nodes Action ---
            relative_path = item.data(Qt.ItemDataRole.UserRole + 1)
            if relative_path and relative_path.lower().endswith(".pdf"):
                nodes_action = QAction("Open Selected PDF in Nodes", self)
                nodes_action.triggered.connect(self._open_pdf_nodes)
                menu.addAction(nodes_action)
                menu.addSeparator()
            # ---------------------------------

            rename_action = QAction("Rename Display Name...", self)
            rename_action.triggered.connect(self._rename_attachment)
            menu.addAction(rename_action)

            delete_action = QAction("Delete Attachment", self)
            delete_action.triggered.connect(self._delete_attachment)
            menu.addAction(delete_action)

        if self.list_widget.count() > 1 and item and item.data(Qt.ItemDataRole.UserRole) is not None:
            menu.addSeparator()
            reorder_action = QAction("Reorder Attachments...", self)
            reorder_action.triggered.connect(self._reorder_attachments)
            menu.addAction(reorder_action)

        menu.exec(self.list_widget.mapToGlobal(position))

    def _add_attachment(self):
        """Opens a file dialog to select and copy an attachment."""
        source_path, _ = QFileDialog.getOpenFileName(self, "Select File to Attach")
        if not source_path:
            return

        try:
            original_filename = os.path.basename(source_path)
            target_path = os.path.join(self.reading_attachments_dir, original_filename)

            # Handle file conflicts
            if os.path.exists(target_path):
                reply = QMessageBox.question(
                    self, "File Exists",
                    f"'{original_filename}' already exists in this reading's attachments.\nOverwrite it?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.No:
                    return

            shutil.copy(source_path, target_path)

            # Store the relative path for cross-platform/machine use
            relative_path = os.path.join(str(self.reading_id), original_filename).replace("\\", "/")

            # Add to database
            self.db.add_attachment(self.reading_id, original_filename, relative_path)
            self.load_attachments()

        except Exception as e:
            QMessageBox.critical(self, "Error Attaching File", f"Could not copy file: {e}")

    def _open_attachment(self, item):
        """Opens the selected attachment with the system's default program."""
        if item.data(Qt.ItemDataRole.UserRole) is None: return

        relative_path = item.data(Qt.ItemDataRole.UserRole + 1)
        full_path = os.path.join(self.attachments_dir, relative_path)

        if not os.path.exists(full_path):
            QMessageBox.critical(self, "Error", f"File not found:\n{full_path}")
            return

        try:
            QDesktopServices.openUrl(QUrl.fromLocalFile(full_path))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open file: {e}")

    def _open_pdf_nodes(self):
        """Emits signal to open the PDF Node Viewer."""
        item = self.list_widget.currentItem()
        if not item or item.data(Qt.ItemDataRole.UserRole) is None:
            return

        attachment_id = item.data(Qt.ItemDataRole.UserRole)
        relative_path = item.data(Qt.ItemDataRole.UserRole + 1)

        # Validate extension
        if not relative_path.lower().endswith(".pdf"):
            QMessageBox.warning(self, "Invalid File Type", "Only PDF files can be opened in the Node Viewer.")
            return

        full_path = os.path.join(self.attachments_dir, relative_path)
        if not os.path.exists(full_path):
            QMessageBox.critical(self, "Error", f"File not found:\n{full_path}")
            return

        # Emit Signal
        self.openPdfNodesRequested.emit(self.reading_id, attachment_id, full_path)

    def _rename_attachment(self):
        """Renames the display name (not the file) of the selected attachment."""
        item = self.list_widget.currentItem()
        if not item or item.data(Qt.ItemDataRole.UserRole) is None:
            return

        attachment_id = item.data(Qt.ItemDataRole.UserRole)
        current_name = item.text()

        new_name, ok = QInputDialog.getText(self, "Rename Attachment", "New display name:", text=current_name)

        if ok and new_name and new_name != current_name:
            try:
                self.db.rename_attachment(attachment_id, new_name)
                self.load_attachments()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not rename attachment: {e}")

    def _delete_attachment(self):
        """Deletes the attachment from the database and the filesystem."""
        item = self.list_widget.currentItem()
        if not item or item.data(Qt.ItemDataRole.UserRole) is None:
            return

        attachment_id = item.data(Qt.ItemDataRole.UserRole)
        relative_path = item.data(Qt.ItemDataRole.UserRole + 1)
        display_name = item.text()

        reply = QMessageBox.question(
            self, "Delete Attachment",
            f"Are you sure you want to delete '{display_name}'?\n\nThis will remove the file from the attachments folder.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.No:
            return

        try:
            # 1. Delete file from disk
            full_path = os.path.join(self.attachments_dir, relative_path)
            if os.path.exists(full_path):
                os.remove(full_path)
            else:
                print(f"Warning: File not found for deletion, but removing from DB: {full_path}")

            # 2. Delete from DB
            self.db.delete_attachment(attachment_id)

            # 3. Refresh list
            self.load_attachments()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not delete attachment: {e}")

    def _reorder_attachments(self):
        """Opens the reorder dialog for all attachments."""
        if not ReorderDialog:
            QMessageBox.critical(self, "Error", "Reorder dialog is not available.")
            return

        try:
            attachments = self.db.get_attachments(self.reading_id)
            if len(attachments) < 2:
                return

            items_to_reorder = [(att['display_name'], att['id']) for att in attachments]
            dialog = ReorderDialog(items_to_reorder, self)

            if dialog.exec() == QDialog.DialogCode.Accepted:
                ordered_ids = dialog.ordered_db_ids
                self.db.update_attachment_order(ordered_ids)
                self.load_attachments()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not reorder attachments: {e}")