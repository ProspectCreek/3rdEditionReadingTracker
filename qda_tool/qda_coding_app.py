import sys
import json
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QPushButton, QHeaderView, QMenu,
    QInputDialog, QMessageBox, QComboBox, QLabel, QDialog, QListWidget,
    QListWidgetItem, QSplitter, QFrame, QLineEdit, QCheckBox, QTextEdit,
    QPlainTextEdit, QScrollArea, QStyledItemDelegate, QAbstractScrollArea,
    QColorDialog
)
from PySide6.QtCore import Qt, QPoint, QObject, Signal, QEvent
from PySide6.QtGui import QKeySequence, QShortcut, QTextOption, QCursor, QColor, QBrush

from qda_database_manager import QDAManager
from qda_row_dialog import RowDetailDialog
from qda_segments_dialog import SegmentsDialog
from qda_codebook_dialog import CodeDetailsDialog
from qda_home_screen import QDAHomeScreen  # Import new launcher
from qda_styles import MODERN_LIGHT_STYLESHEET


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
        # We rely on the CSS 'background-color: transparent' on QTableWidget::item
        # so that the standard paint doesn't overwrite our fillRect above.
        super().paint(painter, option, index)


# -------------------------------------------------
# Helper: Smart Pan Scroll Area
# -------------------------------------------------
class PanScrollArea(QScrollArea):
    """
    A ScrollArea that allows panning by dragging in empty space.
    - Middle Click: Pan anywhere.
    - Left Click: Pan only if clicking 'empty space' (not a cell).
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
        self.edit_col_type.addItems(["text", "dropdown", "checkbox"])
        self.edit_col_type.currentTextChanged.connect(self._on_type_changed)
        form_row2.addWidget(self.edit_col_type)
        props_layout.addLayout(form_row2)

        form_row3 = QHBoxLayout()
        self.btn_col_color = QPushButton("Set Color")
        self.btn_col_color.setFixedWidth(80)
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
        self.btn_reports = QPushButton("Scene Reports…")
        toolbar.addWidget(self.btn_add_row)
        toolbar.addStretch()
        toolbar.addWidget(self.btn_export)
        toolbar.addWidget(self.btn_reports)
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
        self.btn_reports.clicked.connect(self._show_reports)
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
                else:
                    item = QTableWidgetItem(str(val))
                    item.setData(Qt.UserRole, row_id)
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
                val = it.text() if it else ""
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
        if row < 0: return
        vh = self.table.verticalHeaderItem(row)
        if not vh: return
        row_id = vh.data(Qt.UserRole)

        if col == 1:
            self._open_segments_dialog(row_id)
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

    def _row_menu(self, pos):
        vh = self.table.verticalHeader()
        row = vh.logicalIndexAt(pos)
        if row < 0: return

        # --- FIX IS HERE ---
        # WRONG: row_id = vh.verticalHeaderItem(row).data(Qt.UserRole)
        # CORRECT: Get item from TABLE, not HEADER VIEW
        item = self.table.verticalHeaderItem(row)
        if not item: return
        row_id = item.data(Qt.UserRole)

        menu = QMenu(self)
        act_seg = menu.addAction("Edit Segments…")
        act_del = menu.addAction("Delete Row")
        res = menu.exec(vh.mapToGlobal(pos))
        if res == act_seg:
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
        # (Codebook report logic same as before)
        pass

    def _show_reports(self):
        # (Reports logic same as before)
        pass

    def _run_coding_summary_report(self):
        # (Summary report same as before)
        pass

    def _run_full_scene_report(self):
        # (Full scene report same as before)
        pass

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