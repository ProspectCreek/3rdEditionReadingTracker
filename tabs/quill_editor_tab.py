import os
import json
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QUrl, Slot, Qt


# --- NEW: Custom Web View to handle focus ---
class FocusableWebEngineView(QWebEngineView):
    """
    A custom QWebEngineView that automatically focuses the
    Quill editor inside the webpage when the widget gets focus.
    """

    def focusInEvent(self, event):
        """Overrides the focus event."""
        # Run our new JS function to focus the editor
        self.page().runJavaScript("focusEditor();")
        # Call the parent event
        super().focusInEvent(event)


class QuillEditorTab(QWidget):
    """
    A widget for a single editor tab, containing a QWebEngineView
    to load the Quill.js editor.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # --- UPDATED: Use our new custom class ---
        self.webview = FocusableWebEngineView()
        self.setup_webview()

        self.layout.addWidget(self.webview)
        self.setLayout(self.layout)

        # Flag to ensure we don't try to set content before loaded
        self.is_loaded = False
        self.webview.loadFinished.connect(self._on_load_finished)

    def setup_webview(self):
        """Initializes the QWebEngineView and loads the editor."""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        html_file_path = os.path.join(project_root, "editor.html")

        if not os.path.exists(html_file_path):
            print(f"Error: Could not find editor.html at {html_file_path}")
            return

        self.webview.load(QUrl.fromLocalFile(html_file_path))

    def _on_load_finished(self, ok):
        """Internal slot to track when the page is ready."""
        if ok:
            self.is_loaded = True
        else:
            print("Error: Could not load editor.html")

    # --- Public Methods for Python Communication ---

    @Slot(str)
    def set_content(self, html_content):
        """
        Sets the content of the Quill editor.
        """
        if self.is_loaded:
            # We need to escape the string for JavaScript
            js_safe_content = json.dumps(html_content)
            self.webview.page().runJavaScript(f"setEditorContent({js_safe_content});")
        else:
            # If not loaded, wait and try again
            self.webview.loadFinished.connect(
                lambda ok: self.set_content(html_content) if ok else None
            )

    def get_content(self, callback):
        """
        Asynchronously gets the HTML content from the Quill editor.
        The 'callback' function will be called with the HTML string as its argument.
        """
        if self.is_loaded:
            self.webview.page().runJavaScript("getEditorContent();", 0, callback)
        else:
            print("Warning: Tried to get content before editor was loaded.")
            callback(None)  # Return None if not ready

