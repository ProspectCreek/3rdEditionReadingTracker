# dialogs/global_tag_details_dialog.py
import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QTextBrowser, QDialogButtonBox, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QUrl


class GlobalTagDetailsDialog(QDialog):
    """
    Displays all anchors for a specific global tag across all projects.
    Allows jumping to the specific location.
    """
    # Signal to tell the main window to jump to a specific location
    jumpToAnchor = Signal(int, int, int)  # project_id, reading_id, outline_id

    def __init__(self, db, tag_name, parent=None):
        super().__init__(parent)
        self.db = db
        self.tag_name = tag_name
        self.setWindowTitle(f"Global Tag Details: {tag_name}")
        self.setMinimumSize(600, 700)

        main_layout = QVBoxLayout(self)

        self.text_browser = QTextBrowser()
        self.text_browser.setOpenExternalLinks(False)
        self.text_browser.anchorClicked.connect(self._on_link_clicked)
        main_layout.addWidget(self.text_browser)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

        self._load_data()

    def _load_data(self):
        """Fetches and formats the anchors for this tag."""
        try:
            anchors = self.db.get_global_anchors_for_tag_name(self.tag_name)

            html = f"<h2>Global Synthesis for: {self.tag_name}</h2>"

            current_project = None
            current_reading = None

            for anchor in anchors:
                project_name = anchor['project_name']
                if project_name != current_project:
                    current_project = project_name
                    html += f"<hr style='border-top: 2px solid #555;'><h3>Project: {current_project}</h3>"
                    current_reading = None  # Reset reading for new project

                reading_name = anchor['reading_nickname'] or anchor['reading_title']
                if reading_name != current_reading:
                    current_reading = reading_name
                    html += f"<h4 style='color: #0055A4; margin-top: 10px;'>{current_reading}</h4>"

                context_parts = []
                if anchor['outline_title']:
                    context_parts.append(f"Section: {anchor['outline_title']}")

                # Construct jump link: jumpto:project_id:reading_id:outline_id
                jumpto_link = f"jumpto:{anchor['project_id']}:{anchor['reading_id']}:{anchor['outline_id'] or 0}"

                if context_parts:
                    html += f"<p><i><a href='{jumpto_link}'>({', '.join(context_parts)})</a></i></p>"
                else:
                    html += f"<p><i><a href='{jumpto_link}'>(Reading-Level Note)</a></i></p>"

                html += "<blockquote style='border-left: 3px solid #ccc; margin-left: 15px; padding-left: 10px;'>"

                # Use selected_text, which contains the summary for virtual anchors
                selected_text_html = (anchor['selected_text'] or "Anchor").replace("\n", "<br>")
                html += f"<p>{selected_text_html}</p>"

                if anchor['comment']:
                    comment_html = anchor['comment'].replace("\n", "<br>")
                    html += f"<p><i>— {comment_html}</i></p>"
                html += "</blockquote>"

            if not anchors:
                html += "<i>No anchors found for this tag.</i>"

            self.text_browser.setHtml(html)

        except Exception as e:
            self.text_browser.setHtml(f"Error loading data: {e}")

    def _on_link_clicked(self, url):
        """Handles clicking a 'jumpto' link."""
        url_str = url.toString()
        if url_str.startswith("jumpto:"):
            try:
                parts = url_str.split(":")
                project_id = int(parts[1])
                reading_id = int(parts[2])
                outline_id = int(parts[3])

                # Emit signal to jump
                self.jumpToAnchor.emit(project_id, reading_id, outline_id)

                # Close this dialog (and the parent manager) so we can see the dashboard
                self.accept()
            except Exception as e:
                print(f"Error jumping: {e}")

