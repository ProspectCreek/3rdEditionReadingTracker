# tabs/parts_order_relation_tab.py
import sys
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QComboBox,
    QLabel, QMessageBox, QFrame, QHBoxLayout,
    QPushButton, QScrollArea, QTreeWidget, QTreeWidgetItemIterator,
    QGridLayout, QSizePolicy, QTreeWidgetItem, QTextEdit,  # --- FIX: Import QTextEdit ---
    QTextBrowser  # --- FIX: Import QTextBrowser ---
)
from PySide6.QtCore import Qt, Slot, QSize, QUrl
from PySide6.QtGui import QDesktopServices, QFont  # --- FIX: Import QDesktopServices, QFont ---


# --- REMOVED: RichTextEditorTab is no longer needed here ---


class PartsOrderRelationTab(QWidget):
    """
    PySide6 implementation of the Parts: Order and Relation tab.
    Uses plain QTextEdit widgets for input and a QTextBrowser for the flow view.
    """

    def __init__(self, db, project_id, reading_id, outline_tree_widget, parent=None):
        super().__init__(parent)
        self.db = db
        self.project_id = project_id
        self.reading_id = reading_id
        self.outline_tree = outline_tree_widget  # Reference to the main outline tree

        self._outline_map = {}  # {display_text: outline_id}
        self._id_to_outline_map = {}  # {outline_id: display_text}
        self._dq_map = {}  # {nickname: dq_id}
        self._parts_data = {}  # {outline_id: {data}}
        self._is_loaded = False

        # --- Main layout is a scroll area ---
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # --- The whole tab is a scroll area ---
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        main_layout.addWidget(scroll_area)

        content_widget = QWidget()
        scroll_area.setWidget(content_widget)

        content_layout = QVBoxLayout(content_widget)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.scroll_area = scroll_area
        self.selection_frame = QFrame()  # Placeholder for scrolling

        # --- Part Selection Row ---
        self.selection_frame.setFrameShape(QFrame.Shape.StyledPanel)
        selection_layout = QFormLayout(self.selection_frame)
        selection_layout.setContentsMargins(10, 10, 10, 10)

        self.part_combo = QComboBox()
        self.part_combo.activated.connect(self._on_part_selected)

        # Connect to the outline tree in the parent tab (ReadingNotesTab)
        self.outline_tree.itemClicked.connect(self._refresh_part_list)

        self.dq_combo = QComboBox()

        selection_layout.addRow("Select Part:", self.part_combo)
        selection_layout.addRow("Linked DQ:", self.dq_combo)
        content_layout.addWidget(self.selection_frame)

        # --- Detail Fields ---
        details_frame = QFrame()
        details_frame.setFrameShape(QFrame.Shape.StyledPanel)
        details_layout = QFormLayout(details_frame)
        details_layout.setContentsMargins(10, 10, 10, 10)

        # --- FIX (1): Use simple QTextEdit ---
        self.function_editor = QTextEdit()
        self.function_editor.setPlaceholderText("Defines the problem; introduces theory; presents data…")
        self.function_editor.setMinimumHeight(100)
        details_layout.addRow("Function:", self.function_editor)

        self.relation_editor = QTextEdit()
        self.relation_editor.setPlaceholderText("Bridges theory to evidence; answers prior question…")
        self.relation_editor.setMinimumHeight(100)
        details_layout.addRow("Relation:", self.relation_editor)

        self.dependency_editor = QTextEdit()
        self.dependency_editor.setPlaceholderText("Later claims lose context; conclusions lack base…")
        self.dependency_editor.setMinimumHeight(100)
        details_layout.addRow("Dependency:", self.dependency_editor)
        # --- END FIX (1) ---

        content_layout.addWidget(details_frame)

        # --- Action Buttons ---
        btn_frame = QHBoxLayout()
        btn_frame.addStretch()
        btn_clear = QPushButton("Clear")
        btn_save = QPushButton("Save / Update Part Details")
        btn_frame.addWidget(btn_clear)
        btn_frame.addWidget(btn_save)
        content_layout.addLayout(btn_frame)

        btn_clear.clicked.connect(self._clear_editor_fields)
        btn_save.clicked.connect(self._save_current_part)

        # --- FIX (2): Flow View Panel (rebuilt) ---
        flow_frame = QFrame()
        flow_frame.setFrameShape(QFrame.Shape.StyledPanel)
        flow_layout = QVBoxLayout(flow_frame)
        flow_layout.setContentsMargins(10, 10, 10, 10)

        flow_header_layout = QHBoxLayout()
        flow_header_label = QLabel("STRUCTURAL FLOW")
        flow_header_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        flow_header_layout.addWidget(flow_header_label)
        flow_header_layout.addStretch()

        flow_layout.addLayout(flow_header_layout)

        # --- Use QTextBrowser for professional look ---
        self.flow_viewer = QTextBrowser()
        self.flow_viewer.setMinimumHeight(300)
        self.flow_viewer.setOpenLinks(False)  # Handle links manually
        self.flow_viewer.anchorClicked.connect(self._on_flow_part_clicked)

        flow_layout.addWidget(self.flow_viewer)
        content_layout.addWidget(flow_frame, 1)  # Add stretch
        # --- END FIX (2) ---

        self._is_loaded = True

    @Slot(QTreeWidgetItem, int)
    def _refresh_part_list(self, item=None, column=None):
        """Refreshes the list of outline parts in the combobox."""
        current_selection_id = self.part_combo.currentData()
        self.part_combo.clear()
        self._outline_map.clear()
        self._id_to_outline_map.clear()

        self.part_combo.addItem("[Select a Part]", None)

        it = QTreeWidgetItemIterator(self.outline_tree)
        while it.value():
            item_iter = it.value()
            item_id = item_iter.data(0, Qt.ItemDataRole.UserRole)
            item_text = item_iter.text(0)

            # --- Build indented text ---
            level = 0
            temp_item = item_iter
            while temp_item.parent():
                level += 1
                temp_item = temp_item.parent()
            display_text = ("  " * level) + item_text
            # --- End indented text ---

            self._outline_map[display_text] = item_id
            self._id_to_outline_map[item_id] = display_text
            self.part_combo.addItem(display_text, item_id)
            it += 1

        if current_selection_id:
            idx = self.part_combo.findData(current_selection_id)
            if idx != -1:
                self.part_combo.setCurrentIndex(idx)

    def load_data(self):
        """Called by ReadingNotesTab to load all data."""
        if not self._is_loaded:
            return

        self._refresh_part_list()

        self._dq_map.clear()
        self.dq_combo.clear()
        self.dq_combo.addItem("None", None)

        all_dqs = self.db.get_driving_questions(self.reading_id, parent_id=True)

        for dq in all_dqs:
            nickname = dq.get('nickname')
            if nickname and nickname.strip():
                display_text = nickname
            else:
                q_text = (dq.get('question_text', '') or '')
                display_text = (q_text[:70] + "...") if len(q_text) > 70 else q_text
            self._dq_map[display_text] = dq['id']
            self.dq_combo.addItem(display_text, dq['id'])

        saved_parts_raw = self.db.get_parts_data(self.reading_id)
        self._parts_data = {part['id']: dict(part) for part in saved_parts_raw} if saved_parts_raw else {}

        self._refresh_flow_view()
        self._clear_editor_fields()

    @Slot()
    def _on_part_selected(self):
        outline_id = self.part_combo.currentData()
        if not outline_id:
            self._clear_editor_fields()
            return

        data = self._parts_data.get(outline_id, {})

        # --- FIX (1): Load plain text into QTextEdit ---
        self.function_editor.setPlainText(data.get('part_function_text_plain', ''))
        self.relation_editor.setPlainText(data.get('part_relation_text_plain', ''))
        self.dependency_editor.setPlainText(data.get('part_dependency_text_plain', ''))
        # --- END FIX (1) ---

        dq_id_to_select = data.get('part_dq_id')
        if dq_id_to_select:
            idx = self.dq_combo.findData(dq_id_to_select)
            if idx != -1:
                self.dq_combo.setCurrentIndex(idx)
        else:
            self.dq_combo.setCurrentIndex(0)  # "None"

    @Slot()
    def _save_current_part(self):
        """Saves the data in the editor fields to the selected outline part."""
        outline_id = self.part_combo.currentData()
        if not outline_id:
            QMessageBox.warning(self, "Error", "Please select a part from the dropdown first.")
            return

        # --- FIX (1): Get plain text from QTextEdit ---
        data_to_save = {
            'is_structural': True,
            'driving_question_id': self.dq_combo.currentData(),
            'function_text': self.function_editor.toPlainText().strip(),
            'relation_text': self.relation_editor.toPlainText().strip(),
            'dependency_text': self.dependency_editor.toPlainText().strip()
        }
        # --- END FIX (1) ---

        try:
            # --- FIX (1): Call the updated DB method ---
            self.db.save_part_data(self.reading_id, outline_id, data_to_save)
            # --- END FIX (1) ---

            # Update local cache
            self._parts_data[outline_id] = self.db.get_part_data(outline_id)

            self._refresh_flow_view()
            self._clear_editor_fields()
            print(f"Part data saved for outline_id {outline_id}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save part data: {e}")
            print(f"Error saving part data: {e}")

    def save_data(self):
        """Public method for autosave."""
        if self.part_combo.currentData():
            self._save_current_part()

    @Slot()
    def _clear_editor_fields(self):
        self.part_combo.setCurrentIndex(0)  # "[Select a Part]"
        self.dq_combo.setCurrentIndex(0)  # "None"
        # --- FIX (1): Use setPlainText ---
        self.function_editor.setPlainText("")
        self.relation_editor.setPlainText("")
        self.dependency_editor.setPlainText("")
        # --- END FIX (1) ---

    @Slot()
    def _load_part_for_editing(self, outline_id):
        idx = self.part_combo.findData(outline_id)
        if idx != -1:
            self.part_combo.setCurrentIndex(idx)
            self._on_part_selected()

            # --- FIX (3): Scroll to the top editor ---
            self.scroll_area.ensureWidgetVisible(self.selection_frame)
            # --- END FIX (3) ---

    # --- FIX (2): Flow View Logic (rebuilt) ---
    @Slot()
    def _refresh_flow_view(self):

        all_outline_items = self.db.get_all_outline_items(self.reading_id)
        if not all_outline_items:
            self.flow_viewer.setHtml("")
            return

        structural_parts = []
        for item in all_outline_items:
            outline_id = item.get('id')
            part_data = self._parts_data.get(outline_id)
            if part_data:  # If any data exists, it's considered structural
                structural_parts.append({
                    'outline_id': outline_id,
                    'text': item.get('section_title', ''),
                    'data': part_data
                })

        # Build professional HTML
        html = """
        <style>
            body { 
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; 
                line-height: 1.5;
            }
            .card {
                background: #ffffff;
                border: 1px solid #ddd;
                padding: 10px 15px;
                border-radius: 5px;
                margin-bottom: 8px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            }
            h4 {
                margin: 0 0 8px 0;
                font-size: 1.1em;
            }
            h4 a {
                color: #0055A4;
                text-decoration: none;
                font-weight: bold;
            }
            h4 a:hover {
                text-decoration: underline;
            }
            p {
                margin: 0 0 5px 0;
                color: #333;
                white-space: pre-wrap; /* This will respect newlines in the plain text */
            }
            b {
                color: #111;
            }
        </style>
        """

        if not structural_parts:
            html += "<i>No structural parts have been defined yet. Select a part from the dropdown, add details, and click 'Save'.</i>"
            self.flow_viewer.setHtml(html)
            return

        for i, part in enumerate(structural_parts):
            title = part['text']
            data = part['data']
            outline_id = part['outline_id']

            html += f"<div class='card'>"
            # --- Add clickable link that calls _load_part_for_editing ---
            html += f"<h4><a href='part:{outline_id}'>{i + 1}. {title}</a></h4>"

            # --- Use plain text fields ---
            func = data.get('part_function_text_plain', '')
            rel = data.get('part_relation_text_plain', '')
            dep = data.get('part_dependency_text_plain', '')

            if func:
                html += f"<p><b>Function:</b> {func}</p>"
            if rel:
                html += f"<p><b>Relation:</b> {rel}</p>"
            if dep:
                html += f"<p><b>Dependency:</b> {dep}</p>"

            html += "</div>"

        self.flow_viewer.setHtml(html)

    @Slot(QUrl)
    def _on_flow_part_clicked(self, url):
        """Handles clicks on 'part:ID' links in the flow viewer."""
        url_str = url.toString()
        if url_str.startswith("part:"):
            try:
                outline_id = int(url_str.split(":")[-1])
                self._load_part_for_editing(outline_id)
            except Exception as e:
                print(f"Error handling part link: {e}")
        else:
            # Open external links in browser
            QDesktopServices.openUrl(url)

    # --- END FIX (2) ---