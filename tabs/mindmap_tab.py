# tabs/mindmap_tab.py
import sys
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QPushButton, QInputDialog, QMessageBox, QListWidgetItem,
    QSplitter, QGraphicsView, QGraphicsScene, QFrame,
    QStackedWidget, QApplication, QMenu  # <--- IMPORT FIX
)
from PySide6.QtCore import Qt, Signal, QPointF
from PySide6.QtGui import QAction, QFont, QPainter

try:
    from dialogs.mindmap_editor_window import MindmapEditorWindow, MindmapNode, MindmapEdge
except ImportError as e:
    print(f"Could not import MindmapEditorWindow: {e}")
    print("Please ensure 'dialogs/mindmap_editor_window.py' exists.")
    MindmapEditorWindow = None
    MindmapNode = None
    MindmapEdge = None


class MindmapTab(QWidget):
    """
    This is the "Mindmaps" tab, which acts as a launcher
    for the mindmap editor window, with a list/preview layout.
    """

    def __init__(self, db_manager, project_id, parent=None):
        super().__init__(parent)

        self.db = db_manager
        self.project_id = project_id
        self.preview_nodes = {}
        self.preview_edges = []
        self.preview_default_font = QFont("Times New Roman", 12)

        # Main layout is now a QHBoxLayout to create the splitter directly
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)  # Use full tab space

        # Main splitter for list and preview
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(self.splitter)

        # --- Left Panel (List) ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)  # No margins
        left_layout.setSpacing(4)

        # Header for the list
        list_header = QLabel("Mind Map Name")
        list_header.setStyleSheet("font-weight: bold; padding: 4px 6px;")
        left_layout.addWidget(list_header)

        # List widget
        self.list_widget = QListWidget()
        self.list_widget.setAlternatingRowColors(True)
        # Add the context menu
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)
        left_layout.addWidget(self.list_widget)

        # --- Right Panel (Preview) ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)  # No margins

        # Stacked widget to switch between placeholder and preview
        self.preview_stack = QStackedWidget()
        right_layout.addWidget(self.preview_stack)

        # Page 0: Placeholder
        self.placeholder_label = QLabel("Select a mind map to preview it here.")
        self.placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder_label.setStyleSheet("color: #888; font-size: 14px; font-style: italic;")
        self.preview_stack.addWidget(self.placeholder_label)

        # Page 1: Preview Scene and View
        self.preview_scene = QGraphicsScene(self)
        self.preview_view = QGraphicsView(self.preview_scene)
        self.preview_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.preview_view.setEnabled(False)  # Make it read-only
        self.preview_view.setStyleSheet("background-color: #fdfdfd; border: none;")
        self.preview_stack.addWidget(self.preview_view)

        # Add panels to splitter
        self.splitter.addWidget(left_panel)
        self.splitter.addWidget(right_panel)
        self.splitter.setSizes([300, 600])  # 1/3 and 2/3 approx

        # Connect signals
        self.list_widget.itemDoubleClicked.connect(self.open_selected_mindmap)
        self.list_widget.currentItemChanged.connect(self.on_mindmap_selected)

        self.load_mindmaps()

    def show_context_menu(self, position):
        """Shows the right-click menu for the list."""
        menu = QMenu(self)

        # Action to create a new mindmap
        new_action = QAction("New Mind Map", self)
        new_action.triggered.connect(self.create_new_mindmap)
        menu.addAction(new_action)

        menu.addSeparator()

        # Get selected item
        selected_item = self.list_widget.itemAt(position)
        if selected_item:
            mindmap_id = selected_item.data(Qt.ItemDataRole.UserRole)
            if mindmap_id:  # Check if it's a real item, not the "No mindmaps" placeholder
                open_action = QAction("Open", self)
                open_action.triggered.connect(self.open_selected_mindmap)
                menu.addAction(open_action)

                rename_action = QAction("Rename", self)
                rename_action.triggered.connect(self.rename_selected_mindmap)
                menu.addAction(rename_action)

                delete_action = QAction("Delete", self)
                delete_action.triggered.connect(self.delete_selected_mindmap)
                menu.addAction(delete_action)

        menu.exec(self.list_widget.mapToGlobal(position))

    def on_mindmap_selected(self, current_item, previous_item):
        """Called when list selection changes, triggers preview load."""
        if current_item:
            mindmap_id = current_item.data(Qt.ItemDataRole.UserRole)
            if mindmap_id:
                self.load_preview(mindmap_id)
            else:
                self.clear_preview()
        else:
            self.clear_preview()

    def clear_preview(self):
        self.preview_scene.clear()
        self.preview_nodes.clear()
        self.preview_edges.clear()
        self.preview_stack.setCurrentWidget(self.placeholder_label)  # Show placeholder

    def load_preview(self, mindmap_id):
        """Loads a read-only version of the mindmap into the preview scene."""
        if MindmapNode is None or MindmapEdge is None:
            return  # Cannot load preview if editor classes failed to import

        self.clear_preview()

        # --- ERROR FIX ---
        # Get details and convert sqlite3.Row to a dict
        details_row = self.db.get_mindmap_details(mindmap_id)
        details = dict(details_row) if details_row else {}

        # Now we can safely use .get()
        if details and details.get('default_font_family'):
            font = QFont(details.get('default_font_family'), details.get('default_font_size', 12))
            font.setWeight(QFont.Weight.Bold if details.get('default_font_weight') == 'bold' else QFont.Weight.Normal)
            font.setItalic(details.get('default_font_slant') == 'italic')
            self.preview_default_font = font
        else:
            self.preview_default_font = QFont("Times New Roman", 12)
        # --- END FIX ---

        # Load nodes and edges
        data = self.db.get_mindmap_data(mindmap_id)

        for node_data in data.get('nodes', []):
            node_id_text = str(node_data['node_id_text'])
            pos = QPointF(node_data['x'], node_data['y'])
            # Create a NON-interactive node
            node_item = MindmapNode(node_id_text, node_data, self.preview_default_font, interactive=False)
            self.preview_scene.addItem(node_item)
            self.preview_nodes[node_id_text] = node_item

        for edge_data in data.get('edges', []):
            from_node = self.preview_nodes.get(str(edge_data['from_node_id_text']))
            to_node = self.preview_nodes.get(str(edge_data['to_node_id_text']))

            if from_node and to_node:
                edge_item = MindmapEdge(from_node, to_node, edge_data)
                self.preview_scene.addItem(edge_item)
                self.preview_edges.append(edge_item)

        # Show the preview widget
        self.preview_stack.setCurrentWidget(self.preview_view)

        # Fit view to content
        try:
            # Add a small margin so nodes aren't cut off
            bounds = self.preview_scene.itemsBoundingRect().adjusted(-20, -20, 20, 20)
            self.preview_view.fitInView(bounds, Qt.AspectRatioMode.KeepAspectRatio)
        except Exception as e:
            print(f"Error fitting preview: {e}")

    def load_mindmaps(self):
        """Reloads the list of mindmaps from the database."""
        self.list_widget.clear()
        self.clear_preview()
        try:
            mindmaps = self.db.get_mindmaps_for_project(self.project_id)
            if not mindmaps:
                placeholder_item = QListWidgetItem("No mindmaps created yet.")
                placeholder_item.setData(Qt.ItemDataRole.UserRole, None)  # No ID
                placeholder_item.setFlags(Qt.ItemFlag.NoItemFlags)  # Not selectable
                placeholder_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                placeholder_item.setStyleSheet("color: #888; font-style: italic;")
                self.list_widget.addItem(placeholder_item)
                self.list_widget.setEnabled(False)
            else:
                self.list_widget.setEnabled(True)
                for mm_map in mindmaps:
                    item = QListWidgetItem(mm_map['name'])
                    item.setData(Qt.ItemDataRole.UserRole, mm_map['id'])
                    self.list_widget.addItem(item)
        except Exception as e:
            self.list_widget.addItem(f"Error loading mindmaps: {e}")
            self.list_widget.setEnabled(False)

    def create_new_mindmap(self):
        """Prompts for a name and creates a new mindmap."""
        name, ok = QInputDialog.getText(self, "New Mindmap", "Enter a name for the new mindmap:")
        if ok and name:
            try:
                new_id = self.db.create_mindmap(self.project_id, name)
                self.load_mindmaps()
                # Find and select the new item
                for i in range(self.list_widget.count()):
                    item = self.list_widget.item(i)
                    if item.data(Qt.ItemDataRole.UserRole) == new_id:
                        self.list_widget.setCurrentItem(item)
                        break
                # Automatically open the new mindmap
                self.open_selected_mindmap()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not create mindmap: {e}")

    def get_selected_item_data(self):
        """Helper to get the selected list item and its data."""
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select a mindmap from the list first.")
            return None, None
        item = selected_items[0]
        mindmap_id = item.data(Qt.ItemDataRole.UserRole)

        if not mindmap_id:  # Check if it's the placeholder
            return None, None

        return item, mindmap_id

    def rename_selected_mindmap(self):
        item, mindmap_id = self.get_selected_item_data()
        if not item:
            return

        old_name = item.text()
        new_name, ok = QInputDialog.getText(self, "Rename Mindmap", "Enter new name:", text=old_name)

        if ok and new_name and new_name != old_name:
            try:
                self.db.rename_mindmap(mindmap_id, new_name)
                self.load_mindmaps()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not rename mindmap: {e}")

    def delete_selected_mindmap(self):
        item, mindmap_id = self.get_selected_item_data()
        if not item:
            return

        reply = QMessageBox.question(self, "Delete Mindmap",
                                     f"Are you sure you want to permanently delete '{item.text()}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.db.delete_mindmap(mindmap_id)
                self.load_mindmaps()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not delete mindmap: {e}")

    def open_selected_mindmap(self, item=None):
        """Opens the editor for the currently selected mindmap."""
        if not item:
            item, mindmap_id = self.get_selected_item_data()
            if not item:
                return

        mindmap_id = item.data(Qt.ItemDataRole.UserRole)
        if not mindmap_id:
            return

        self.open_mindmap_editor(item)

    def open_mindmap_editor(self, item):
        """Opens the MindmapEditorWindow."""
        if MindmapEditorWindow is None:
            QMessageBox.critical(self, "Error", "Mindmap Editor component could not be loaded.")
            return

        mindmap_id = item.data(Qt.ItemDataRole.UserRole)
        if not mindmap_id:
            return  # Ignore "No mindmaps" item

        mindmap_name = item.text()

        try:
            # Check if an editor for this mindmap is already open
            # We do this by searching the top-level widgets
            for widget in QApplication.topLevelWidgets():
                if isinstance(widget, MindmapEditorWindow) and widget.mindmap_id == mindmap_id:
                    widget.activateWindow()
                    widget.raise_()
                    return

            # We pass 'self' (the tab) as the parent
            # This makes the editor dialog stay on top of the main window
            editor_dialog = MindmapEditorWindow(self, self.db, mindmap_id, mindmap_name)

            # Use .open() instead of .exec() to make it non-modal
            # This allows you to interact with the main app while the editor is open
            editor_dialog.open()

            # We connect a signal to refresh the preview when the editor is closed
            # This is a lambda to ensure it re-loads the *correct* ID
            editor_dialog.finished.connect(lambda: self.refresh_preview_by_id(mindmap_id))

        except Exception as e:
            QMessageBox.critical(self, "Error Opening Editor", f"An error occurred: {e}")
            import traceback
            traceback.print_exc()

    def refresh_preview_by_id(self, mindmap_id):
        """Refreshes the preview if the closed mindmap is still the selected one."""
        item = self.list_widget.currentItem()
        if item and item.data(Qt.ItemDataRole.UserRole) == mindmap_id:
            self.load_preview(mindmap_id)