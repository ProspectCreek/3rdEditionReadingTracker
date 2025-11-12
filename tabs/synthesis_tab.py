# tabs/synthesis_tab.py
import sys
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QLabel,
    QListWidget, QListWidgetItem, QFrame, QTextEdit, QCheckBox,
    QTextBrowser, QMenu, QInputDialog, QMessageBox, QDialog
)
from PySide6.QtCore import Qt, Signal, Slot, QUrl, QPoint
from PySide6.QtGui import QColor, QFont, QAction
import sqlite3  # <-- Import for IntegrityError

# --- NEW: Import dialogs ---
try:
    from dialogs.edit_tag_dialog import EditTagDialog
except ImportError:
    print("Error: Could not import EditTagDialog")
    EditTagDialog = None

try:
    from dialogs.manage_anchors_dialog import ManageAnchorsDialog
except ImportError:
    print("Error: Could not import ManageAnchorsDialog")
    ManageAnchorsDialog = None
# --- END NEW ---


class SynthesisTab(QWidget):
    """
    A widget for synthesizing information.
    Shows a master list of tags and a detail view of anchors.
    """
    # Signal to open a reading tab: (reading_id, outline_id)
    openReading = Signal(int, int)

    # Signal that tags have been changed (deleted/renamed)
    tagsUpdated = Signal()

    def __init__(self, db, project_id, parent=None):
        super().__init__(parent)
        self.db = db
        self.project_id = project_id

        # Main layout is a horizontal splitter
        main_layout = QHBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # --- Left Panel (Tag List) ---
        left_panel = QFrame()
        left_panel.setFrameShape(QFrame.Shape.StyledPanel)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(4, 4, 4, 4)

        left_layout.addWidget(QLabel("Synthesis Tags"))

        # TODO: Add global checkbox

        self.tag_list = QListWidget()
        left_layout.addWidget(self.tag_list)
        left_panel.setLayout(left_layout)

        # --- Right Panel (Anchor Detail) ---
        right_panel = QFrame()
        right_panel.setFrameShape(QFrame.Shape.StyledPanel)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(4, 4, 4, 4)

        right_layout.addWidget(QLabel("Connected Anchors"))

        self.anchor_display = QTextBrowser()  # Use QTextBrowser for links
        self.anchor_display.setOpenExternalLinks(False)  # We handle links internally
        self.anchor_display.anchorClicked.connect(self.on_anchor_link_clicked)
        right_layout.addWidget(self.anchor_display)
        right_panel.setLayout(right_layout)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([250, 600])  # Initial sizes

        # --- Connections ---
        self.tag_list.currentItemChanged.connect(self.on_tag_selected)
        self.tag_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tag_list.customContextMenuRequested.connect(self.show_tag_context_menu)

    def load_tab_data(self):
        """Called by the dashboard to load this tab's data."""
        self.load_tags_list()
        self.anchor_display.clear()

    def load_tags_list(self):
        """Reloads the list of tags from the database."""
        self.tag_list.clear()
        try:
            tags = self.db.get_tags_with_counts(self.project_id)
            if not tags:
                item = QListWidgetItem("No tags created yet.")
                item.setFlags(Qt.ItemFlag.NoItemFlags)
                self.tag_list.addItem(item)
                return

            for tag in tags:
                display_text = f"{tag['name']} ({tag['anchor_count']})"
                item = QListWidgetItem(display_text)
                item.setData(Qt.ItemDataRole.UserRole, tag['id'])
                item.setData(Qt.ItemDataRole.UserRole + 1, tag['name'])  # Store name for editing
                self.tag_list.addItem(item)
        except Exception as e:
            QMessageBox.critical(self, "Error Loading Tags", f"Could not load tags: {e}")

    @Slot(QListWidgetItem, QListWidgetItem)
    def on_tag_selected(self, current_item, previous_item):
        """Called when a tag is clicked, loads anchors."""
        if current_item is None:
            self.anchor_display.clear()
            return

        tag_id = current_item.data(Qt.ItemDataRole.UserRole)
        if tag_id is None:
            self.anchor_display.clear()
            return

        try:
            anchors = self.db.get_anchors_for_tag_with_context(tag_id)
            if not anchors:
                self.anchor_display.setHtml("<i>No anchors found for this tag.</i>")
                return

            html = ""
            current_reading = None
            for anchor in anchors:
                # --- Group by reading ---
                reading_name = anchor['reading_nickname'] or anchor['reading_title']
                if reading_name != current_reading:
                    if current_reading is not None:
                        html += "<br>"  # Add space between readings
                    current_reading = reading_name
                    html += f"<h3>{current_reading}</h3>"

                # --- Build Context Link ---
                context_parts = []
                if anchor['outline_title']:
                    context_parts.append(f"Section: {anchor['outline_title']}")

                # Create a "jumpto" link
                # Format: jumpto:reading_id:outline_id
                jumpto_link = f"jumpto:{anchor['reading_id']}:{anchor['outline_id'] or 0}"

                if context_parts:
                    html += f"<p><i><a href='{jumpto_link}'>({', '.join(context_parts)})</a></i></p>"
                else:
                    html += f"<p><i><a href='{jumpto_link}'>(Reading-Level Note)</a></i></p>"

                # --- Build Anchor Body ---
                html += f"<blockquote>"
                html += f"<p>{anchor['selected_text']}</p>"
                if anchor['comment']:
                    # Format comment to preserve newlines
                    comment_html = anchor['comment'].replace("\n", "<br>")
                    html += f"<p><i>— {comment_html}</i></p>"
                html += "</blockquote>"

            self.anchor_display.setHtml(html)

        except Exception as e:
            self.anchor_display.setHtml(f"<p><b>Error loading anchors:</b><br>{e}</p>")
            QMessageBox.critical(self, "Error", f"Could not load anchors: {e}")

    @Slot(QUrl)
    def on_anchor_link_clicked(self, url):
        """Handles internal 'jumpto' links."""
        url_str = url.toString()
        if url_str.startswith("jumpto:"):
            try:
                parts = url_str.split(":")
                reading_id = int(parts[1])
                outline_id = int(parts[2])
                print(f"Emitting openReading signal for reading_id={reading_id}, outline_id={outline_id}")
                self.openReading.emit(reading_id, outline_id)
            except Exception as e:
                print(f"Error handling jumpto link: {e}")

    # --- Tag List Context Menu ---

    @Slot(QPoint)
    def show_tag_context_menu(self, position):
        """Shows the right-click menu for the tag list."""
        menu = QMenu(self)
        item = self.tag_list.itemAt(position)

        # Action to create a new tag (always available)
        create_action = QAction("Create New Tag...", self)
        create_action.triggered.connect(self._create_new_tag)
        menu.addAction(create_action)

        if item and item.data(Qt.ItemDataRole.UserRole) is not None:
            # Actions for a specific tag
            menu.addSeparator()

            # --- NEW: Manage Anchors Action ---
            manage_action = QAction("Manage Anchors for this Tag...", self)
            manage_action.triggered.connect(self._manage_tag_anchors)
            menu.addAction(manage_action)
            # --- END NEW ---

            rename_action = QAction("Rename Tag...", self)
            rename_action.triggered.connect(self._rename_tag)
            menu.addAction(rename_action)

            delete_action = QAction("Delete Tag and All Anchors...", self)
            delete_action.triggered.connect(self._delete_tag)
            menu.addAction(delete_action)

        menu.exec(self.tag_list.mapToGlobal(position))

    @Slot()
    def _create_new_tag(self):
        """Opens a dialog to create a new, empty tag."""
        if not EditTagDialog:
            QMessageBox.critical(self, "Error", "EditTagDialog could not be loaded.")
            return

        dialog = EditTagDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_name = dialog.get_tag_name()
            if not new_name:
                QMessageBox.warning(self, "Invalid Name", "Tag name cannot be empty.")
                return

            try:
                self.db.get_or_create_tag(self.project_id, new_name)
                self.load_tags_list()
            except sqlite3.IntegrityError:
                QMessageBox.warning(self, "Tag Exists", f"A tag named '{new_name}' already exists.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not create tag: {e}")

    @Slot()
    def _rename_tag(self):
        """Opens a dialog to rename the selected tag."""
        item = self.tag_list.currentItem()
        if not item or item.data(Qt.ItemDataRole.UserRole) is None:
            return

        tag_id = item.data(Qt.ItemDataRole.UserRole)
        tag_name = item.data(Qt.ItemDataRole.UserRole + 1)

        if not EditTagDialog:
            QMessageBox.critical(self, "Error", "EditTagDialog could not be loaded.")
            return

        dialog = EditTagDialog(current_name=tag_name, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_name = dialog.get_tag_name()
            if not new_name or new_name == tag_name:
                return

            try:
                self.db.rename_tag(tag_id, new_name, self.project_id)
                self.load_tags_list()  # Refresh list
                self.tagsUpdated.emit()  # Refresh anchors
            except sqlite3.IntegrityError:
                QMessageBox.warning(self, "Tag Exists", f"A tag named '{new_name}' already exists.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not rename tag: {e}")

    @Slot()
    def _delete_tag(self):
        """Deletes the selected tag and all its anchors."""
        item = self.tag_list.currentItem()
        if not item or item.data(Qt.ItemDataRole.UserRole) is None:
            return

        tag_id = item.data(Qt.ItemDataRole.UserRole)
        tag_name = item.data(Qt.ItemDataRole.UserRole + 1)

        reply = QMessageBox.question(
            self, "Delete Tag",
            f"Are you sure you want to delete the tag '{tag_name}'?\n\n"
            "This will delete the tag itself AND all anchors associated with it from all readings.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        # --- FIX: Indentation error was here ---
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.db.delete_tag_and_anchors(tag_id)
                # Emit signal *before* reloading list
                self.tagsUpdated.emit()
                # Manually reload list *after* emit
                self.load_tags_list()
                self.anchor_display.clear()  # Clear detail view
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not delete tag: {e}")
        # --- END FIX ---

    # --- NEW: Slot for Manage Anchors ---
    @Slot()
    def _manage_tag_anchors(self):
        """Opens the new dialog to manage/delete individual anchors."""
        item = self.tag_list.currentItem()
        if not item or item.data(Qt.ItemDataRole.UserRole) is None:
            return

        tag_id = item.data(Qt.ItemDataRole.UserRole)
        tag_name = item.data(Qt.ItemDataRole.UserRole + 1)

        if not ManageAnchorsDialog:
            QMessageBox.critical(self, "Error", "ManageAnchorsDialog could not be loaded.")
            return

        dialog = ManageAnchorsDialog(self.db, tag_id, tag_name, self)
        # Connect the dialog's signal to our refresh slot
        dialog.anchorDeleted.connect(self._on_anchor_deleted_from_dialog)
        dialog.exec()

    @Slot()
    def _on_anchor_deleted_from_dialog(self):
        """
        Called when the ManageAnchorsDialog emits a signal.
        This forces a full refresh of the UI.
        """
        # 1. Emit the main signal to update all open reading tabs
        self.tagsUpdated.emit()

        # 2. Refresh this tab's own views
        self.load_tags_list()  # Reloads tag counts

        # 3. Reload the anchor list for the currently selected tag
        # We need to check if the tag still exists or if the list is empty
        current_item = self.tag_list.currentItem()
        if current_item:
            self.on_tag_selected(current_item, None)
        else:
            self.anchor_display.clear()
    # --- END NEW ---