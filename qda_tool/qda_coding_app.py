# qda_tool/qda_coding_app.py
import sys
import json
import os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QPushButton, QHeaderView, QMenu,
    QInputDialog, QMessageBox, QComboBox, QLabel, QDialog, QListWidget,
    QListWidgetItem, QSplitter, QFrame, QLineEdit, QCheckBox, QTextEdit,
    QPlainTextEdit, QScrollArea, QStyledItemDelegate, QAbstractScrollArea,
    QColorDialog, QTreeWidget, QTreeWidgetItem, QDialogButtonBox, QFileDialog
)
from PySide6.QtCore import Qt, QPoint, QObject, Signal, QEvent, QTimer
from PySide6.QtGui import QKeySequence, QShortcut, QTextOption, QCursor, QColor, QBrush

from qda_database_manager import QDAManager
from qda_row_dialog import RowDetailDialog
from qda_segments_dialog import SegmentsDialog
from qda_codebook_dialog import CodeDetailsDialog
from qda_home_screen import QDAHomeScreen
from qda_styles import MODERN_LIGHT_STYLESHEET

# --- Import PdfNodeViewer dynamically ---
# Since QDA Tool is in a subfolder, we need to add parent dir to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from tabs.pdf_node_viewer import PdfNodeViewer
except ImportError:
    PdfNodeViewer = None


# -------------------------------------------------
# Helper: Delegate for Truncating Text in View
# -------------------------------------------------
class TextTruncateDelegate(QStyledItemDelegate):
    """
    Displays only the first ~30 characters of text in the cell,
    but keeps the full text available for editing and tooltips.
    """

    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        # Get the full text stored in the model
        full_text = index.data(Qt.DisplayRole)
        if full_text and isinstance(full_text, str):
            # Set tooltip to full text so user can hover to read
            option.toolTip = full_text
            # Truncate the text displayed in the cell
            if len(full_text) > 30:
                option.text = full_text[:30] + "…"

    def paint(self, painter, option, index):
        """
        Manually paint background to support custom colors when using Stylesheets.
        Stylesheets often override the default background painting of Items.
        """
        painter.save()

        # 1. Draw Custom Background if present
        bg_data = index.data(Qt.BackgroundRole)
        if bg_data:
            if isinstance(bg_data, QColor):
                painter.fillRect(option.rect, bg_data)
            elif isinstance(bg_data, QBrush):
                painter.fillRect(option.rect, bg_data)

        painter.restore()

        # 2. Draw standard content (Text, Selection, Focus, CSS Borders)
        super().paint(painter, option, index)


# -------------------------------------------------
# Helper: Smart Pan Scroll Area
# -------------------------------------------------
class PanScrollArea(QScrollArea):
    """
    A ScrollArea that allows panning by dragging in empty space.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self._panning = False
        self._start_pos = None
        self._is_hand_mode = False

    def setWidget(self, w):
        super().setWidget(w)
        if w:
            w.viewport().installEventFilter(self)
            w.setMouseTracking(True)

    def eventFilter(self, source, event):
        if self.widget() and source is self.widget().viewport():
            if event.type() == QEvent.MouseButtonPress:
                if event.button() == Qt.MiddleButton:
                    self._start_pan(event)
                    return True
                if event.button() == Qt.LeftButton:
                    item = self.widget().itemAt(event.position().toPoint())
                    if item is None:
                        self._start_pan(event)
                        return True
            elif event.type() == QEvent.MouseMove:
                if self._panning:
                    self._execute_pan(event)
                    return True
                else:
                    self._update_cursor_on_hover(event)
            elif event.type() == QEvent.MouseButtonRelease:
                if self._panning:
                    self._stop_pan()
                    self._update_cursor_on_hover(event)
                    return True
        return super().eventFilter(source, event)

    def _start_pan(self, event):
        self._panning = True
        self._start_pos = event.globalPosition()
        self.widget().viewport().setCursor(Qt.ClosedHandCursor)

    def _execute_pan(self, event):
        if not self._start_pos: return
        delta = event.globalPosition() - self._start_pos
        self._start_pos = event.globalPosition()
        inner = self.widget()
        if isinstance(inner, QAbstractScrollArea):
            hbar = inner.horizontalScrollBar()
            vbar = inner.verticalScrollBar()
        else:
            hbar = self.horizontalScrollBar()
            vbar = self.verticalScrollBar()
        hbar.setValue(hbar.value() - int(delta.x()))
        vbar.setValue(vbar.value() - int(delta.y()))

    def _stop_pan(self):
        self._panning = False
        self._start_pos = None
        self.widget().viewport().setCursor(Qt.ArrowCursor)

    def _update_cursor_on_hover(self, event):
        item = self.widget().itemAt(event.position().toPoint())
        if item is None:
            if not self._is_hand_mode:
                self.widget().viewport().setCursor(Qt.OpenHandCursor)
                self._is_hand_mode = True
        else:
            if self._is_hand_mode:
                self.widget().viewport().setCursor(Qt.ArrowCursor)
                self._is_hand_mode = False


# -------------------------------------------------
# Filter model to keep filter state & signals
# -------------------------------------------------
class FilterState(QObject):
    filter_changed = Signal()

    def __init__(self):
        super().__init__()
        self.col_id = None
        self.text = ""

    def set_filter(self, col_id, text):
        self.col_id = col_id
        self.text = text.strip()
        self.filter_changed.emit()

    def clear_filter(self):
        self.col_id = None
        self.text = ""
        self.filter_changed.emit()


# -------------------------------------------------
# QDA PDF Link Dialog (Simplified for QDA Context)
# -------------------------------------------------
class QDAPdfLinkDialog(QDialog):
    """
    Dialog to select a PDF node from the external tracker DB.
    """

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db  # This is QDAManager, which has access to tracker_db
        self.selected_node_id = None
        self.selected_node_label = None

        self.setWindowTitle("Link to PDF Node")
        self.resize(800, 600)

        main_layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # Left: Project/Reading Tree
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.addWidget(QLabel("<b>Readings</b>"))
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.itemClicked.connect(self._on_tree_item_clicked)
        left_layout.addWidget(self.tree)
        splitter.addWidget(left_widget)

        # Right: Node List
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.addWidget(QLabel("<b>Nodes</b>"))
        self.node_list = QListWidget()
        self.node_list.itemDoubleClicked.connect(self._on_node_double_clicked)
        self.node_list.itemClicked.connect(self._update_buttons)
        right_layout.addWidget(self.node_list)
        splitter.addWidget(right_widget)

        splitter.setSizes([300, 500])

        # Buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.button(QDialogButtonBox.Ok).setEnabled(False)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

        self._load_data()

    def _load_data(self):
        if not self.db.tracker_conn:
            QMessageBox.warning(self, "No Connection", "Could not connect to Reading Tracker database.")
            return

        projects = self.db.get_tracker_projects()
        for proj in projects:
            p_item = QTreeWidgetItem([proj['name']])
            p_item.setData(0, Qt.UserRole, "project")
            self.tree.addTopLevelItem(p_item)

            readings = self.db.get_tracker_readings(proj['id'])
            for r in readings:
                r_name = r['nickname'] if r['nickname'] else r['title']
                r_item = QTreeWidgetItem([r_name])
                r_item.setData(0, Qt.UserRole, "reading")
                r_item.setData(0, Qt.UserRole + 1, r['id'])
                p_item.addChild(r_item)

    def _on_tree_item_clicked(self, item, column):
        type_ = item.data(0, Qt.UserRole)
        if type_ == "reading":
            reading_id = item.data(0, Qt.UserRole + 1)
            self._load_nodes(reading_id)
        else:
            self.node_list.clear()

    def _load_nodes(self, reading_id):
        self.node_list.clear()
        nodes = self.db.get_tracker_pdf_nodes(reading_id)
        for node in nodes:
            # Format: (Category) Label (Pg X)
            label = node['label']
            if node.get('category_name'):
                label = f"({node['category_name']}) {label}"

            label += f" (Pg {node['page_number'] + 1})"

            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, node['id'])
            item.setData(Qt.UserRole + 1, node['label'])  # Just label for the table display if preferred
            # Or store full display label if you want the table to show category:
            # item.setData(Qt.UserRole + 1, label)

            self.node_list.addItem(item)

    def _update_buttons(self):
        self.button_box.button(QDialogButtonBox.Ok).setEnabled(bool(self.node_list.currentItem()))

    def _on_node_double_clicked(self, item):
        self.accept()

    def accept(self):
        item = self.node_list.currentItem()
        if item:
            self.selected_node_id = item.data(Qt.UserRole)
            self.selected_node_label = item.text()  # Use the full formatted text for display in the table
        super().accept()


# -------------------------------------------------
# Main QDA coding window
# -------------------------------------------------
class QDAWindow(QMainWindow):
    def __init__(self, db: QDAManager, ws_id: int, ws_name: str):
        super().__init__()
        self.db = db
        self.ws_id = ws_id
        self.ws_name = ws_name
        self.setWindowTitle(f"Radar's QDA Coding Tool – {ws_name}")
        self.resize(1300, 800)
        self.columns = []
        self.rows = []
        self.filtered_rows = []
        self.selected_col_id = None
        self.current_col_color = None
        self.filter_state = FilterState()
        self.filter_state.filter_changed.connect(self._apply_filter_and_refresh)

        # Store open viewers
        self.pdf_viewers = []

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # --- LEFT PANEL ---
        left_panel = QFrame()
        left_panel.setFrameShape(QFrame.StyledPanel)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(8, 8, 8, 8)
        left_layout.setSpacing(8)
        left_layout.addWidget(QLabel("<b>Codebook (Structure)</b>"))
        self.col_list_widget = QListWidget()
        self.col_list_widget.itemClicked.connect(self._on_col_list_clicked)
        left_layout.addWidget(self.col_list_widget)

        order_layout = QHBoxLayout()
        self.btn_move_up = QPushButton("Move Column Up")
        self.btn_move_down = QPushButton("Move Column Down")
        order_layout.addWidget(self.btn_move_up)
        order_layout.addWidget(self.btn_move_down)
        left_layout.addLayout(order_layout)
        self.btn_move_up.clicked.connect(self._move_column_up)
        self.btn_move_down.clicked.connect(self._move_column_down)

        btn_box = QHBoxLayout()
        self.btn_add_col = QPushButton("Add Column")
        self.btn_del_col = QPushButton("Delete")
        btn_box.addWidget(self.btn_add_col)
        btn_box.addWidget(self.btn_del_col)
        left_layout.addLayout(btn_box)

        self.props_group = QFrame()
        props_layout = QVBoxLayout(self.props_group)
        props_layout.setContentsMargins(0, 0, 0, 0)
        props_layout.setSpacing(4)
        props_layout.addWidget(QLabel("<b>Column Properties</b>"))

        form_row1 = QHBoxLayout()
        form_row1.addWidget(QLabel("Name:"))
        self.edit_col_name = QLineEdit()
        form_row1.addWidget(self.edit_col_name)
        props_layout.addLayout(form_row1)

        form_row2 = QHBoxLayout()
        form_row2.addWidget(QLabel("Type:"))
        self.edit_col_type = QComboBox()
        self.edit_col_type.addItems(["text", "dropdown", "checkbox", "link"])
        self.edit_col_type.currentTextChanged.connect(self._on_type_changed)
        form_row2.addWidget(self.edit_col_type)
        props_layout.addLayout(form_row2)

        form_row3 = QHBoxLayout()
        self.btn_col_color = QPushButton("Set Color")
        self.btn_col_color.setFixedWidth(100)
        self.lbl_col_color_preview = QLabel()
        self.lbl_col_color_preview.setFixedSize(24, 24)
        self.lbl_col_color_preview.setStyleSheet("border: 1px solid #999; background-color: transparent;")
        form_row3.addWidget(QLabel("Color:"))
        form_row3.addWidget(self.lbl_col_color_preview)
        form_row3.addWidget(self.btn_col_color)
        form_row3.addStretch()
        props_layout.addLayout(form_row3)
        self.btn_col_color.clicked.connect(self._pick_col_color)

        self.edit_col_options_lbl = QLabel("Options (comma/newline):")
        props_layout.addWidget(self.edit_col_options_lbl)
        self.edit_col_options = QPlainTextEdit()
        self.edit_col_options.setPlaceholderText("Enter dropdown options...")
        props_layout.addWidget(self.edit_col_options)

        self.btn_code_details = QPushButton("Code Details…")
        props_layout.addWidget(self.btn_code_details)
        self.btn_save_props = QPushButton("Update Properties")
        props_layout.addWidget(self.btn_save_props)
        left_layout.addWidget(self.props_group)
        self.props_group.setEnabled(False)

        self.btn_codebook_report = QPushButton("Show Codebook Structure")
        left_layout.addWidget(self.btn_codebook_report)

        # --- RIGHT PANEL ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(8, 8, 8, 8)
        right_layout.setSpacing(6)

        toolbar = QHBoxLayout()
        self.btn_add_row = QPushButton("+ Add Row")
        self.btn_export = QPushButton("Export CSV")
        # Removed "Scene Reports..." button per request
        toolbar.addWidget(self.btn_add_row)
        toolbar.addStretch()
        toolbar.addWidget(self.btn_export)
        right_layout.addLayout(toolbar)

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter by column:"))
        self.filter_col_combo = QComboBox()
        filter_layout.addWidget(self.filter_col_combo)
        filter_layout.addWidget(QLabel("Contains:"))
        self.filter_text = QLineEdit()
        filter_layout.addWidget(self.filter_text)
        self.btn_apply_filter = QPushButton("Apply")
        self.btn_clear_filter = QPushButton("Clear")
        filter_layout.addWidget(self.btn_apply_filter)
        filter_layout.addWidget(self.btn_clear_filter)
        right_layout.addLayout(filter_layout)

        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectItems)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._grid_context_menu)
        self.table.setItemDelegate(TextTruncateDelegate(self.table))
        self.table.setColumnCount(0)
        self.table.setRowCount(0)
        self.table.verticalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.verticalHeader().customContextMenuRequested.connect(self._row_menu)
        self.table.cellChanged.connect(self._on_cell_changed)
        self.table.cellDoubleClicked.connect(self._open_row_detail)

        pan_area = PanScrollArea()
        pan_area.setWidget(self.table)
        right_layout.addWidget(pan_area)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([320, 980])

        self.btn_add_col.clicked.connect(self._add_new_col)
        self.btn_del_col.clicked.connect(self._delete_col)
        self.btn_save_props.clicked.connect(self._save_col_props)
        self.btn_code_details.clicked.connect(self._open_code_details)
        self.btn_add_row.clicked.connect(self._add_new_row)
        self.btn_export.clicked.connect(self._export_csv)
        # self.btn_reports.clicked.connect(self._show_reports)  # Removed
        self.btn_apply_filter.clicked.connect(self._on_apply_filter_clicked)
        self.btn_clear_filter.clicked.connect(self._on_clear_filter_clicked)
        self.btn_codebook_report.clicked.connect(self._show_codebook_report)

        new_row_shortcut = QShortcut(QKeySequence("Ctrl+N"), self)
        new_row_shortcut.activated.connect(self._add_new_row)

        self.load_schema()
        self.load_data()

    # --- SCHEMA ---
    def load_schema(self):
        cols = self.db.get_columns(self.ws_id)
        self.columns = cols
        self.col_list_widget.clear()
        self.filter_col_combo.clear()
        self.filter_col_combo.addItem("(All columns)", None)
        for col in self.columns:
            label = f"{col['name']} ({col['col_type']})"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, col["id"])
            self.col_list_widget.addItem(item)
            self.filter_col_combo.addItem(col["name"], col["id"])

    def _on_col_list_clicked(self, item):
        col_id = item.data(Qt.UserRole)
        self.selected_col_id = col_id
        col_data = next((c for c in self.columns if c["id"] == col_id), None)
        if not col_data: return
        self.props_group.setEnabled(True)
        self.edit_col_name.setText(col_data["name"])
        idx = self.edit_col_type.findText(col_data["col_type"])
        if idx != -1: self.edit_col_type.setCurrentIndex(idx)
        self.current_col_color = col_data.get("color")
        self._update_color_preview()
        self._update_options_ui(col_data["col_type"], col_data.get("options_json"))

    def _on_type_changed(self, new_type):
        self._update_options_ui(new_type, None)

    def _update_options_ui(self, col_type, options_json):
        if col_type == "dropdown":
            self.edit_col_options.setEnabled(True)
            self.edit_col_options_lbl.setText("Options (comma/newline):")
            if options_json:
                try:
                    opts = json.loads(options_json)
                    self.edit_col_options.setPlainText("\n".join(opts))
                except:
                    self.edit_col_options.setPlainText("")
            else:
                self.edit_col_options.setPlainText("")
        else:
            self.edit_col_options.setPlainText("")
            self.edit_col_options.setEnabled(False)
            self.edit_col_options_lbl.setText("Options (N/A):")

    def _pick_col_color(self):
        initial = QColor(self.current_col_color) if self.current_col_color else QColor("white")
        c = QColorDialog.getColor(initial, self, "Pick Code Color")
        if c.isValid():
            self.current_col_color = c.name()
            self._update_color_preview()

    def _update_color_preview(self):
        if self.current_col_color:
            self.lbl_col_color_preview.setStyleSheet(
                f"background-color: {self.current_col_color}; border: 1px solid #555;")
        else:
            self.lbl_col_color_preview.setStyleSheet("background-color: transparent; border: 1px solid #999;")

    def _save_col_props(self):
        if not self.selected_col_id: return
        new_name = self.edit_col_name.text().strip()
        if not new_name: return
        new_type = self.edit_col_type.currentText()
        new_options_json = "[]"
        if new_type == "dropdown":
            text = self.edit_col_options.toPlainText()
            opts = [x.strip() for x in text.replace(",", "\n").split("\n") if x.strip()]
            new_options_json = json.dumps(opts)
        self.db.update_column_def(self.selected_col_id, new_name, new_type, new_options_json, self.current_col_color)
        self.load_schema()
        self.load_data()

    def _add_new_col(self):
        name, ok = QInputDialog.getText(self, "New Column", "Column Name:")
        if ok and name.strip():
            self.db.add_column(self.ws_id, name.strip(), "text")
            self.load_schema()
            self.load_data()

    def _delete_col(self):
        item = self.col_list_widget.currentItem()
        if not item: return
        confirm = QMessageBox.question(self, "Delete Column", f"Delete column '{item.text()}'?")
        if confirm == QMessageBox.Yes:
            self.db.delete_column(item.data(Qt.UserRole))
            self.selected_col_id = None
            self.props_group.setEnabled(False)
            self.edit_col_name.clear()
            self.edit_col_options.clear()
            self.current_col_color = None
            self._update_color_preview()
            self.load_schema()
            self.load_data()

    def _move_column_up(self):
        if self.col_list_widget.currentItem():
            self.db.move_column(self.ws_id, self.col_list_widget.currentItem().data(Qt.UserRole), -1)
            self.load_schema()
            self.load_data()

    def _move_column_down(self):
        if self.col_list_widget.currentItem():
            self.db.move_column(self.ws_id, self.col_list_widget.currentItem().data(Qt.UserRole), 1)
            self.load_schema()
            self.load_data()

    # --- DATA ---
    def load_data(self):
        all_rows = self.db.get_rows(self.ws_id)
        self.rows = all_rows
        self._apply_filter_and_refresh()

    def _apply_filter_and_refresh(self):
        col_id = self.filter_state.col_id
        text = self.filter_state.text.lower()
        if col_id is None or not text:
            self.filtered_rows = list(self.rows)
        else:
            col_key = str(col_id)
            filtered = []
            for row in self.rows:
                try:
                    data = json.loads(row["data_json"] or "{}")
                except:
                    data = {}
                val = str(data.get(col_key, "")).lower()
                if text in val: filtered.append(row)
            self.filtered_rows = filtered
        self._populate_table()

    def _populate_table(self):
        self.table.blockSignals(True)
        self.table.clear()
        seg_counts = self.db.get_segment_counts(self.ws_id)

        self.table.setColumnCount(len(self.columns) + 2)
        self.table.setRowCount(len(self.filtered_rows))

        headers = ["★", "Segs"] + [c["name"] for c in self.columns]
        self.table.setHorizontalHeaderLabels(headers)
        self.table.verticalHeader().setDefaultSectionSize(34)

        for r_index, row in enumerate(self.filtered_rows):
            row_id = row["id"]
            try:
                data = json.loads(row["data_json"] or "{}")
            except:
                data = {}

            # V Header
            vh = QTableWidgetItem(str(r_index + 1))
            vh.setData(Qt.UserRole, row_id)
            self.table.setVerticalHeaderItem(r_index, vh)

            # Star (0)
            star_val = data.get("_star", "False")
            star_item = QTableWidgetItem()
            star_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            star_item.setCheckState(Qt.Checked if star_val == "True" else Qt.Unchecked)
            star_item.setData(Qt.UserRole, row_id)
            self.table.setItem(r_index, 0, star_item)

            # Segs (1)
            count = seg_counts.get(row_id, 0)
            seg_item = QTableWidgetItem(str(count) if count > 0 else "")
            seg_item.setTextAlignment(Qt.AlignCenter)
            seg_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            seg_item.setData(Qt.UserRole, row_id)
            if count > 0:
                seg_item.setBackground(QColor("#BFDBFE"))
                seg_item.setToolTip(f"{count} segments.")
            self.table.setItem(r_index, 1, seg_item)

            # Data
            for offset, col in enumerate(self.columns, start=2):
                col_id = str(col["id"])
                col_type = col["col_type"]
                val = data.get(col_id, "")

                # Detect if this is a LINK
                is_link = False
                link_target_id = None
                if val.startswith("LINK|"):
                    try:
                        _, target_id, label = val.split("|", 2)
                        val = label  # Display label
                        link_target_id = target_id
                        is_link = True
                    except:
                        pass

                col_color = col.get("color")
                bg_brush = QColor(col_color) if col_color else None

                if col_type == "checkbox":
                    item = QTableWidgetItem()
                    item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                    item.setCheckState(Qt.Checked if val == "True" else Qt.Unchecked)
                    item.setData(Qt.UserRole, row_id)
                    if bg_brush: item.setBackground(bg_brush)
                    self.table.setItem(r_index, offset, item)
                elif col_type == "dropdown":
                    combo = QComboBox()
                    try:
                        opts = json.loads(col.get("options_json") or "[]")
                    except:
                        opts = []
                    combo.addItems(opts)
                    combo.setEditable(True)
                    combo.setCurrentText(str(val))
                    combo.setProperty("row_id", row_id)
                    combo.setProperty("col_id", col["id"])
                    combo.setProperty("col_offset", offset)
                    combo.currentTextChanged.connect(self._on_combo_changed)
                    if col_color:
                        combo.setStyleSheet(f"background-color: {col_color};")
                    else:
                        combo.setStyleSheet("background-color: #FFFFFF;")
                    if combo.lineEdit(): combo.lineEdit().setCursorPosition(0)
                    self.table.setCellWidget(r_index, offset, combo)

                    item = QTableWidgetItem(str(val))
                    item.setData(Qt.UserRole, row_id)
                    if bg_brush: item.setBackground(bg_brush)
                    self.table.setItem(r_index, offset, item)
                elif col_type == "link":
                    # Render link column
                    display_text = val
                    item = QTableWidgetItem(display_text)
                    item.setData(Qt.UserRole, row_id)

                    if is_link:
                        item.setForeground(QColor("blue"))
                        font = item.font()
                        font.setUnderline(True)
                        item.setFont(font)
                        item.setData(Qt.UserRole + 1, link_target_id)
                        item.setToolTip("Double-click to open PDF Node")
                    else:
                        item.setToolTip("Double-click to set link")

                    if bg_brush: item.setBackground(bg_brush)
                    self.table.setItem(r_index, offset, item)
                else:
                    item = QTableWidgetItem(str(val))
                    item.setData(Qt.UserRole, row_id)

                    if is_link:
                        item.setForeground(QColor("blue"))
                        font = item.font()
                        font.setUnderline(True)
                        item.setFont(font)
                        item.setData(Qt.UserRole + 1, link_target_id)  # Store link ID
                        item.setToolTip("Double-click to open PDF Node")

                    if bg_brush: item.setBackground(bg_brush)
                    self.table.setItem(r_index, offset, item)

        self.table.resizeColumnsToContents()
        self.table.setColumnWidth(1, 40)
        for c in range(2, self.table.columnCount()):
            self.table.setColumnWidth(c, self.table.columnWidth(c) + 35)
        self.table.blockSignals(False)

    # --- INTERACTIONS ---
    def _on_apply_filter_clicked(self):
        idx = self.filter_col_combo.currentIndex()
        self.filter_state.set_filter(self.filter_col_combo.itemData(idx), self.filter_text.text())

    def _on_clear_filter_clicked(self):
        self.filter_text.clear()
        self.filter_state.clear_filter()

    def _add_new_row(self):
        self.db.add_row(self.ws_id)
        self.load_data()
        if self.table.rowCount() > 0: self.table.scrollToBottom()

    def _save_row(self, row_index):
        vh_item = self.table.verticalHeaderItem(row_index)
        if not vh_item: return
        row_id = vh_item.data(Qt.UserRole)
        if not row_id: return

        row_rec = self.db.get_row(row_id)
        try:
            data = json.loads(row_rec["data_json"] or "{}") if row_rec else {}
        except:
            data = {}

        item_0 = self.table.item(row_index, 0)
        if item_0: data["_star"] = "True" if item_0.checkState() == Qt.Checked else "False"

        for offset, col in enumerate(self.columns, start=2):
            col_id = str(col["id"])
            if col["col_type"] == "dropdown":
                w = self.table.cellWidget(row_index, offset)
                val = w.currentText() if w else ""
            elif col["col_type"] == "checkbox":
                it = self.table.item(row_index, offset)
                val = "True" if (it and it.checkState() == Qt.Checked) else "False"
            else:
                it = self.table.item(row_index, offset)
                # Preserve link data if present
                link_id = it.data(Qt.UserRole + 1)
                text = it.text()
                if link_id and text:
                    val = f"LINK|{link_id}|{text}"
                else:
                    val = text if it else ""

            data[col_id] = val

        self.db.update_row_data(row_id, data)

    def _save_row_by_id(self, row_id):
        for r in range(self.table.rowCount()):
            vh = self.table.verticalHeaderItem(r)
            if vh and vh.data(Qt.UserRole) == row_id:
                self._save_row(r)
                return

    def _on_cell_changed(self, row, col):
        if row < 0 or col == 1: return
        self._save_row(row)

    def _on_combo_changed(self, text):
        sender = self.sender()
        if not sender: return
        row_id = sender.property("row_id")
        self._save_row_by_id(row_id)

        off = sender.property("col_offset")
        if off is not None:
            self.table.resizeColumnToContents(off)
            self.table.setColumnWidth(off, self.table.columnWidth(off) + 35)

    def _open_row_detail(self, row, col):
        # If row passed as arg is actually a QModelIndex or int, handle it
        # But here signature implies row index (int)
        if isinstance(row, int) and row < 0: return

        # For manual call from context menu, we need row index
        if not isinstance(row, int):
            # If called without arguments or wrong types
            return

        vh = self.table.verticalHeaderItem(row)
        if not vh: return
        row_id = vh.data(Qt.UserRole)

        if col == 1:
            self._open_segments_dialog(row_id)
            return

        # Check if clicking a LINK
        item = self.table.item(row, col)
        if item:
            # Handle "link" column double click
            if col >= 2:
                col_def = self.columns[col - 2]
                if col_def['col_type'] == 'link':
                    link_id = item.data(Qt.UserRole + 1)
                    if link_id:
                        self._jump_to_pdf_node(link_id)
                    else:
                        self._link_cell_to_pdf(row, col)
                    return

            # Handle manual links in text columns
            link_id = item.data(Qt.UserRole + 1)
            if link_id:
                self._jump_to_pdf_node(link_id)
                return

        rec = self.db.get_row(row_id)
        if not rec: return
        dlg = RowDetailDialog(self, self.db, rec, self.columns)
        if dlg.exec() == QDialog.Accepted: self.load_data()

    def _open_segments_dialog(self, row_id):
        rec = self.db.get_row(row_id)
        if not rec: return
        dlg = SegmentsDialog(self, self.db, rec, self.columns)
        if dlg.exec() == QDialog.Accepted: self.load_data()

    def _grid_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if not item: return

        row = item.row()
        col = item.column()

        # Calculate col index in self.columns
        # Columns start at index 2 in table
        if col < 2: return
        col_def = self.columns[col - 2]

        menu = QMenu()
        link_action = menu.addAction("Link to PDF Node...")
        clear_link_action = menu.addAction("Clear Link")

        action = menu.exec(self.table.viewport().mapToGlobal(pos))
        if action == link_action:
            self._link_cell_to_pdf(row, col)
        elif action == clear_link_action:
            self.table.item(row, col).setText("")
            # This triggers cellChanged which triggers save,
            # clearing the data in _save_row because text is empty

    def _link_cell_to_pdf(self, row, col):
        # Open Link Dialog
        dlg = QDAPdfLinkDialog(self.db, parent=self)
        if dlg.exec() == QDialog.Accepted:
            node_id = dlg.selected_node_id
            label = dlg.selected_node_label

            if node_id:
                # Update the item immediately to show the link
                item = self.table.item(row, col)
                self.table.blockSignals(True)  # Prevent premature save
                item.setText(label)
                item.setData(Qt.UserRole + 1, node_id)

                # Style it
                item.setForeground(QColor("blue"))
                font = item.font()
                font.setUnderline(True)
                item.setFont(font)
                item.setToolTip("Double-click to open PDF Node")
                self.table.blockSignals(False)

                # Now trigger save manually to persist it properly
                self._save_row(row)

    def _jump_to_pdf_node(self, node_id):
        """Launch separate PDF viewer window."""
        if PdfNodeViewer is None:
            QMessageBox.warning(self, "Error", "PDF Viewer component missing.")
            return

        # Get details from tracker DB
        node = self.db.get_tracker_node_details(node_id)
        if not node:
            QMessageBox.warning(self, "Error", "Node not found in Reading Tracker.")
            return

        # Reconstruct path assuming standard layout
        tracker_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        att_path = node['file_path']  # Now provided by updated get_tracker_node_details
        full_path = os.path.join(tracker_root, "Attachments", att_path)

        if not os.path.exists(full_path):
            QMessageBox.warning(self, "Error", f"PDF file not found at:\n{full_path}")
            return

        try:
            # Check existing viewers
            for v in self.pdf_viewers:
                if v.attachment_id == node['attachment_id']:
                    v.show()
                    v.raise_()
                    v.activateWindow()
                    v.jump_to_node(node_id)
                    return

            # Open new
            viewer = PdfNodeViewer(self.db, node['reading_id'], node['attachment_id'], full_path, parent=None)
            viewer.show()
            self.pdf_viewers.append(viewer)

            # Clean up
            viewer.finished.connect(lambda: self.pdf_viewers.remove(viewer) if viewer in self.pdf_viewers else None)

            # Jump
            QTimer.singleShot(100, lambda: viewer.jump_to_node(node_id))

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to launch viewer: {e}")

    def _row_menu(self, pos):
        vh = self.table.verticalHeader()
        row = vh.logicalIndexAt(pos)
        if row < 0: return

        # CORRECT: Get item from TABLE, not HEADER VIEW
        item = self.table.verticalHeaderItem(row)
        if not item: return
        row_id = item.data(Qt.UserRole)

        menu = QMenu(self)

        # --- NEW: Edit Entry Details ---
        act_details = menu.addAction("Edit Entry Details")

        act_seg = menu.addAction("Edit Segments…")
        act_del = menu.addAction("Delete Row")

        res = menu.exec(vh.mapToGlobal(pos))

        if res == act_details:
            # Reuse existing method, pass dummy col=2 (first data col) to trigger logic
            self._open_row_detail(row, 2)
        elif res == act_seg:
            self._open_segments_dialog(row_id)
        elif res == act_del:
            if QMessageBox.question(self, "Delete", "Delete Scene?") == QMessageBox.Yes:
                self.db.delete_row(row_id)
                self.load_data()

    def _open_code_details(self):
        if not self.selected_col_id: return
        col = next((c for c in self.columns if c["id"] == self.selected_col_id), None)
        if not col: return
        dlg = CodeDetailsDialog(self, self.db, self.selected_col_id, col["name"], self.columns)
        if dlg.exec() == QDialog.Accepted:
            self.load_schema()
            self.load_data()

    def _show_codebook_report(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Codebook Structure", "codebook_structure.txt",
                                              "Text Files (*.txt)")
        if not path:
            return

        try:
            # Columns are already ordered in self.columns
            # But we need to reconstruct parent-child relationships for the structure view
            # QDA columns don't strictly have a 'parent' field in qda_columns table unless
            # we check meta data or assume a flat list.
            # Wait, the user mentioned "parents and children".
            # The qda_database_manager setup_tables has `parent_id` in `qda_columns` (or `qda_codebook_meta`?)
            # Let's check the schema provided in qda_database_manager.py
            # qda_columns table has `parent_id INTEGER`.

            # Build tree
            cols = self.columns  # Already loaded and sorted by display order
            col_map = {c['id']: c for c in cols}
            children_map = {c['id']: [] for c in cols}
            roots = []

            for c in cols:
                pid = c.get('parent_id')
                if pid and pid in children_map:
                    children_map[pid].append(c)
                else:
                    roots.append(c)

            lines = []
            lines.append(f"Codebook Structure for Worksheet: {self.ws_name}")
            lines.append("=" * 50)
            lines.append("")

            def print_node(node, depth=0):
                indent = "    " * depth
                lines.append(f"{indent}- {node['name']} ({node['col_type']})")

                # --- ADD DROPDOWN OPTIONS TO REPORT ---
                if node['col_type'] == 'dropdown':
                    try:
                        opts = json.loads(node.get('options_json') or "[]")
                        if opts:
                            for opt in opts:
                                lines.append(f"{indent}    * {opt}")
                    except:
                        pass

                for child in children_map.get(node['id'], []):
                    print_node(child, depth + 1)

            for root in roots:
                print_node(root)

            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))

            QMessageBox.information(self, "Success", f"Codebook structure exported to:\n{path}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export codebook: {e}")

    def _show_reports(self):
        QMessageBox.information(self, "Reports", "Reports not implemented yet.")

    # --- EXPORT CSV (FLATTENED) ---
    def _export_csv(self):
        from PySide6.QtWidgets import QFileDialog
        import csv

        path, _ = QFileDialog.getSaveFileName(self, "Export CSV", "qda_export.csv", "CSV (*.csv)")
        if not path: return

        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)

                # Headers: Scene ID, Type (Main/Segment), Segment Label, [Project Columns...], Segment Note
                header = ["Row ID", "Type", "Segment Label"] + [c["name"] for c in self.columns] + ["Segment Note"]
                writer.writerow(header)

                # We need to fetch segments for ALL rows
                for row in self.rows:
                    row_id = row["id"]
                    try:
                        rdata = json.loads(row["data_json"] or "{}")
                    except:
                        rdata = {}

                    # 1. Main Row
                    # "Type" = "Scene"
                    main_line = [row_id, "Scene", ""]  # No seg label
                    for col in self.columns:
                        cid = str(col["id"])
                        main_line.append(rdata.get(cid, ""))
                    main_line.append("")  # No segment note
                    writer.writerow(main_line)

                    # 2. Segments
                    segs = self.db.get_segments(row_id)
                    for seg in segs:
                        try:
                            sdata = json.loads(seg["data_json"] or "{}")
                        except:
                            sdata = {}

                        # "Type" = "Segment"
                        seg_line = [row_id, "Segment", sdata.get("_label", "")]
                        for col in self.columns:
                            cid = str(col["id"])
                            seg_line.append(sdata.get(cid, ""))
                        seg_line.append(sdata.get("_note", ""))
                        writer.writerow(seg_line)

            QMessageBox.information(self, "Export", "Export complete.\nSegments included as sub-rows.")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))

    def _grid_context_menu(self, pos):
        # Handled in customContextMenuRequested above
        pass


# -------------------------------------------------
# Launcher / Main (REPLACED BY QDAHomeScreen)
# -------------------------------------------------
def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(MODERN_LIGHT_STYLESHEET)
    db = QDAManager()

    # Use the new Home Screen instead of the old Launcher
    launcher = QDAHomeScreen(db)

    if launcher.exec() == QDialog.Accepted and launcher.selected_ws:
        win = QDAWindow(db, *launcher.selected_ws)
        win.show()
        sys.exit(app.exec())
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()