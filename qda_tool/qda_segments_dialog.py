import json
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QLabel,
    QMenu,
    QComboBox,
    QHeaderView,
    QStyledItemDelegate,
    QScrollArea,
    QAbstractScrollArea
)
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QColor, QBrush


# --- DELEGATE FOR PAINTING COLORS ---
class SegmentColorDelegate(QStyledItemDelegate):
    """
    Ensures background colors are painted correctly even with stylesheets applied.
    Copies the logic from the main window's delegate.
    """

    def paint(self, painter, option, index):
        painter.save()

        # 1. Draw Custom Background if present
        bg_data = index.data(Qt.BackgroundRole)
        if bg_data:
            if isinstance(bg_data, QColor):
                painter.fillRect(option.rect, bg_data)
            elif isinstance(bg_data, QBrush):
                painter.fillRect(option.rect, bg_data)

        painter.restore()

        # 2. Draw standard content
        super().paint(painter, option, index)


# --- PANNING SCROLL AREA (Same as Main App) ---
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

            # 1. MOUSE PRESS
            if event.type() == QEvent.MouseButtonPress:
                if event.button() == Qt.MiddleButton:
                    self._start_pan(event)
                    return True

                if event.button() == Qt.LeftButton:
                    # Check if we are clicking on a valid item
                    item = self.widget().itemAt(event.position().toPoint())
                    if item is None:
                        # Clicked empty space -> Pan
                        self._start_pan(event)
                        return True

            # 2. MOUSE MOVE
            elif event.type() == QEvent.MouseMove:
                if self._panning:
                    self._execute_pan(event)
                    return True
                else:
                    self._update_cursor_on_hover(event)

            # 3. MOUSE RELEASE
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


class SegmentsDialog(QDialog):
    """
    Manage multiple segments (sub-chunks) for a single scene (row).
    """

    def __init__(self, parent, db, row_record, columns):
        super().__init__(parent)
        self.db = db
        self.row_id = row_record["id"]
        self.columns = columns

        # Try to find a label for the window title
        row_data = {}
        try:
            row_data = json.loads(row_record["data_json"] or "{}")
        except:
            pass
        scene_label = row_data.get("10", str(row_record["id"]))

        self.setWindowTitle(f"Segments for Scene {scene_label}")
        self.resize(1100, 600)

        self.segments = []

        main_layout = QVBoxLayout(self)

        instructions = QLabel(
            "<b>Action Log:</b> Break this scene into specific actions.<br>"
            "Use this to code <i>who</i> did <i>what</i>. You can leave Context columns (Scene, Summary) blank."
        )
        main_layout.addWidget(instructions)

        # Toolbar
        toolbar = QHBoxLayout()
        self.btn_add = QPushButton("+ Add Segment")
        toolbar.addWidget(self.btn_add)
        toolbar.addStretch()
        main_layout.addLayout(toolbar)

        # --- SETUP DYNAMIC TABLE ---
        self.table = QTableWidget()

        # Apply the Color Delegate
        self.table.setItemDelegate(SegmentColorDelegate(self.table))

        headers = ["Seg Label"]
        for col in self.columns:
            headers.append(col["name"])
        headers.append("Segment Note")

        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setDefaultSectionSize(34)

        # Context Menu for deletion
        self.table.verticalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.verticalHeader().customContextMenuRequested.connect(self._row_menu)

        # Signals
        self.table.cellChanged.connect(self._on_cell_changed)

        # --- WRAP TABLE IN PAN SCROLL AREA ---
        # Instead of adding self.table directly, we wrap it
        self.pan_area = PanScrollArea()
        self.pan_area.setWidget(self.table)
        main_layout.addWidget(self.pan_area)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_close = QPushButton("Close")
        btn_row.addWidget(btn_close)
        main_layout.addLayout(btn_row)

        self.btn_add.clicked.connect(self._add_segment)
        btn_close.clicked.connect(self.accept)

        self._load_segments()

    # -------------------------
    # LOAD / REFRESH
    # -------------------------
    def _load_segments(self):
        self.table.blockSignals(True)
        self.table.clearContents()

        self.segments = self.db.get_segments(self.row_id)
        self.table.setRowCount(len(self.segments))

        for r_idx, seg in enumerate(self.segments):
            try:
                data = json.loads(seg["data_json"] or "{}")
            except Exception:
                data = {}

            # Vertical Header (ID)
            vh = QTableWidgetItem(str(r_idx + 1))
            vh.setData(Qt.UserRole, seg["id"])
            self.table.setVerticalHeaderItem(r_idx, vh)

            # 1. Segment Label (Column 0)
            label_val = data.get("_label", "")
            self.table.setItem(r_idx, 0, QTableWidgetItem(label_val))

            # 2. Dynamic Project Columns
            for c_idx, col_def in enumerate(self.columns):
                table_col = c_idx + 1
                col_id = str(col_def["id"])
                val = data.get(col_id, "")
                col_type = col_def["col_type"]

                # Prepare Color
                bg_color = None
                if col_def.get("color"):
                    bg_color = QColor(col_def.get("color"))

                if col_type == "dropdown":
                    combo = QComboBox()
                    opts_str = col_def.get("options_json") or "[]"
                    try:
                        options = json.loads(opts_str)
                    except:
                        options = []
                    combo.addItems(options)
                    combo.setEditable(True)
                    combo.setCurrentText(str(val))

                    # Properties for signal handling
                    combo.setProperty("row_idx", r_idx)
                    combo.setProperty("col_id", col_id)

                    # Apply Color to Dropdown Widget
                    if col_def.get("color"):
                        combo.setStyleSheet(f"background-color: {col_def.get('color')};")
                    else:
                        combo.setStyleSheet("background-color: #FFFFFF;")

                    combo.currentTextChanged.connect(self._on_combo_changed)
                    if combo.lineEdit():
                        combo.lineEdit().setCursorPosition(0)

                    self.table.setCellWidget(r_idx, table_col, combo)

                    # Backing item
                    item = QTableWidgetItem(str(val))
                    if bg_color: item.setBackground(bg_color)
                    self.table.setItem(r_idx, table_col, item)

                elif col_type == "checkbox":
                    item = QTableWidgetItem()
                    item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                    item.setCheckState(Qt.Checked if str(val) == "True" else Qt.Unchecked)
                    if bg_color: item.setBackground(bg_color)
                    self.table.setItem(r_idx, table_col, item)

                else:
                    # Text
                    item = QTableWidgetItem(str(val))
                    if bg_color: item.setBackground(bg_color)
                    self.table.setItem(r_idx, table_col, item)

            # 3. Segment Note (Last Column)
            note_val = data.get("_note", "")
            last_col = self.table.columnCount() - 1
            self.table.setItem(r_idx, last_col, QTableWidgetItem(note_val))

        self.table.resizeColumnsToContents()
        for c in range(self.table.columnCount()):
            w = self.table.columnWidth(c)
            self.table.setColumnWidth(c, w + 25)

        self.table.blockSignals(False)

    # -------------------------
    # ADD / DELETE
    # -------------------------
    def _add_segment(self):
        self.db.add_segment(self.row_id)
        self._load_segments()
        self.table.scrollToBottom()

    def _row_menu(self, pos):
        idx = self.table.verticalHeader().logicalIndexAt(pos)
        # FIX: use TABLE to get item, not header view directly (same fix as main app)
        vh_item = self.table.verticalHeaderItem(idx)
        if not vh_item:
            return
        seg_id = vh_item.data(Qt.UserRole)

        menu = QMenu()
        delete = menu.addAction("Delete Segment")
        choice = menu.exec(self.table.verticalHeader().mapToGlobal(pos))
        if choice == delete:
            self.db.delete_segment(seg_id)
            self._load_segments()

    # -------------------------
    # SAVE
    # -------------------------
    def _save_segment_row(self, r_idx):
        vh_item = self.table.verticalHeaderItem(r_idx)
        if not vh_item: return
        seg_id = vh_item.data(Qt.UserRole)
        if not seg_id: return

        data = {}

        # 1. Label (Col 0)
        item_0 = self.table.item(r_idx, 0)
        data["_label"] = item_0.text() if item_0 else ""

        # 2. Project Cols
        for c_idx, col_def in enumerate(self.columns):
            table_col = c_idx + 1
            col_id = str(col_def["id"])
            col_type = col_def["col_type"]

            if col_type == "dropdown":
                widget = self.table.cellWidget(r_idx, table_col)
                val = widget.currentText() if widget else ""
            elif col_type == "checkbox":
                item = self.table.item(r_idx, table_col)
                val = "True" if (item and item.checkState() == Qt.Checked) else "False"
            else:
                item = self.table.item(r_idx, table_col)
                val = item.text() if item else ""

            data[col_id] = val

        # 3. Note (Last Col)
        last_col = self.table.columnCount() - 1
        item_last = self.table.item(r_idx, last_col)
        data["_note"] = item_last.text() if item_last else ""

        print(f"[DEBUG][Segments] save seg_id={seg_id}, data={data}")
        self.db.update_segment_data(seg_id, data)

    def _on_cell_changed(self, row, col):
        if row < 0: return
        self._save_segment_row(row)

    def _on_combo_changed(self, text):
        sender = self.sender()
        if not sender: return
        row_idx = sender.property("row_idx")
        if row_idx is not None:
            self._save_segment_row(row_idx)