# prospectcreek/3rdeditionreadingtracker/tabs/rich_text_editor_tab.py
import sys
import uuid
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton,
    QTextEdit, QInputDialog, QMessageBox, QSizePolicy, QColorDialog,
    QMenu
)
from PySide6.QtCore import Qt, Signal, QPoint, Slot
from PySide6.QtGui import (
    QFontDatabase, QTextCharFormat, QTextCursor, QTextListFormat,
    QColor, QFont, QAction
)

_PT_SIZES = [10, 12, 14, 16, 18, 20, 24, 32]
_FONTS = [
    "Times New Roman",  # put first so we prefer it if available
    "Times",
    "Sans Serif", "Serif", "Monospace",
    "Arial", "Georgia",
    "Courier New", "Tahoma", "Verdana", "Segoe UI",
]

_CUSTOM = "__custom__"

BaseAnchorProperty = 1001
AnchorIDProperty = BaseAnchorProperty + 1
AnchorTagIDProperty = BaseAnchorProperty + 2
AnchorTagNameProperty = BaseAnchorProperty + 3
AnchorCommentProperty = BaseAnchorProperty + 4
AnchorUUIDProperty = BaseAnchorProperty + 5


def _apply_char_format(editor: QTextEdit, fmt: QTextCharFormat):
    c = editor.textCursor()
    if not c.hasSelection():
        editor.mergeCurrentCharFormat(fmt)
    else:
        c.mergeCharFormat(fmt)
        editor.setTextCursor(c)


def _set_indent(editor: QTextEdit, delta: int):
    c = editor.textCursor()
    bfmt = c.blockFormat()
    indent = max(0, bfmt.indent() + delta)
    bfmt.setIndent(indent)
    c.setBlockFormat(bfmt)
    editor.setTextCursor(c)


class RichTextEditorTab(QWidget):
    """
    Native Qt rich-text editor with a minimal, label-free toolbar.
    """
    anchorActionTriggered = Signal(str)
    anchorEditTriggered = Signal(int)
    anchorDeleteTriggered = Signal(int)

    def __init__(self, title: str = "Editor", parent=None):
        super().__init__(parent)
        self.editor_title = title

        main = QVBoxLayout(self)
        main.setContentsMargins(6, 4, 6, 6)
        main.setSpacing(4)

        bar = QWidget(self)
        bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        h = QHBoxLayout(bar)
        h.setContentsMargins(6, 4, 6, 4)
        h.setSpacing(6)

        bar.setStyleSheet("""
            QComboBox, QPushButton { height: 24px; font-size: 11px; }
            QComboBox::drop-down { width: 16px; }
        """)

        BTN_W = 26
        BTN_WW = 28
        COMBO_FONT_W = 120
        COMBO_SIZE_W = 70
        COMBO_HDR_W = 56
        COMBO_ALIGN_W = 80
        COMBO_TXTCLR_W = 110
        COMBO_BGCLR_W = 120

        self.fontCombo = QComboBox(bar);
        self.fontCombo.setToolTip("Font family")
        self.fontCombo.setMinimumWidth(COMBO_FONT_W);
        self.fontCombo.setMaximumWidth(COMBO_FONT_W)
        installed = set(QFontDatabase().families())
        for fam in _FONTS:
            mapped = fam
            if fam == "Sans Serif":
                mapped = QFont().defaultFamily()
            if fam == "Serif":
                mapped = "Times New Roman" if "Times New Roman" in installed else "Times"
            if fam == "Monospace":
                mapped = "Courier New" if "Courier New" in installed else "Courier"
            self.fontCombo.addItem(fam, mapped)
        h.addWidget(self.fontCombo)

        self.sizeCombo = QComboBox(bar);
        self.sizeCombo.setToolTip("Font size (pt)")
        self.sizeCombo.setMinimumWidth(COMBO_SIZE_W);
        self.sizeCombo.setMaximumWidth(COMBO_SIZE_W)
        for sz in _PT_SIZES:
            self.sizeCombo.addItem(f"{sz} pt", sz)
        idx_sz = self.sizeCombo.findData(16)
        if idx_sz != -1:
            self.sizeCombo.setCurrentIndex(idx_sz)
        h.addWidget(self.sizeCombo)

        self.headerCombo = QComboBox(bar);
        self.headerCombo.setToolTip("Paragraph / H1 / H2 / H3")
        self.headerCombo.setMinimumWidth(COMBO_HDR_W);
        self.headerCombo.setMaximumWidth(COMBO_HDR_W)
        self.headerCombo.addItem("¶", 0);
        self.headerCombo.addItem("H1", 1)
        self.headerCombo.addItem("H2", 2);
        self.headerCombo.addItem("H3", 3)
        h.addWidget(self.headerCombo)

        def mkbtn(text, tip):
            b = QPushButton(text);
            b.setCheckable(True);
            b.setToolTip(tip)
            b.setMinimumWidth(BTN_W);
            b.setMaximumWidth(BTN_W);
            return b

        self.boldBtn = mkbtn("B", "Bold")
        self.italicBtn = mkbtn("I", "Italic")
        self.underlineBtn = mkbtn("U", "Underline")
        self.strikeBtn = mkbtn("S", "Strikethrough")
        for w in (self.boldBtn, self.italicBtn, self.underlineBtn, self.strikeBtn): h.addWidget(w)

        self.textColorCombo = QComboBox(bar);
        self.textColorCombo.setToolTip("Text Color")
        self.textColorCombo.setMinimumWidth(COMBO_TXTCLR_W);
        self.textColorCombo.setMaximumWidth(COMBO_TXTCLR_W)
        self.textColorCombo.addItem("Text Color", None)
        for hexval, label in [("#000000", "Black"), ("#FF0000", "Red"), ("#008000", "Green"), ("#0000FF", "Blue"),
                              ("#FA8000", "Orange"), ("#8000FF", "Purple"), ("#808080", "Gray")]:
            self.textColorCombo.addItem(label, hexval)
        self.textColorCombo.addItem("Custom…", _CUSTOM)
        h.addWidget(self.textColorCombo)

        self.bgColorCombo = QComboBox(bar);
        self.bgColorCombo.setToolTip("Highlight")
        self.bgColorCombo.setMinimumWidth(COMBO_BGCLR_W);
        self.bgColorCombo.setMaximumWidth(COMBO_BGCLR_W)
        self.bgColorCombo.addItem("Highlight", None)
        self.bgColorCombo.addItem("No highlight (White)", "#FFFFFF")
        for hexval, label in [("#FFFF00", "Yellow"), ("#FFCCCC", "L.Red"), ("#CCFFCC", "L.Green"),
                              ("#CCCCFF", "L.Blue"), ("#FFF2CC", "L.Orange"), ("#F3E5F5", "Lavender")]:
            self.bgColorCombo.addItem(label, hexval)
        self.bgColorCombo.addItem("Custom…", _CUSTOM)
        h.addWidget(self.bgColorCombo)

        def mkbtn2(text, tip):
            b = QPushButton(text);
            b.setToolTip(tip)
            b.setMinimumWidth(BTN_WW);
            b.setMaximumWidth(BTN_WW);
            return b

        self.olBtn = mkbtn2("1.", "Numbered list")
        self.ulBtn = mkbtn2("•", "Bulleted list")
        self.outdentBtn = mkbtn2("⟵", "Outdent")
        self.indentBtn = mkbtn2("⟶", "Indent")
        for w in (self.olBtn, self.ulBtn, self.outdentBtn, self.indentBtn): h.addWidget(w)

        self.alignCombo = QComboBox(bar);
        self.alignCombo.setToolTip("Alignment")
        self.alignCombo.setMinimumWidth(COMBO_ALIGN_W);
        self.alignCombo.setMaximumWidth(COMBO_ALIGN_W)
        for val, label in [(Qt.AlignLeft, "Left"), (Qt.AlignCenter, "Center"),
                           (Qt.AlignRight, "Right"), (Qt.AlignJustify, "Justify")]:
            self.alignCombo.addItem(label, int(val))
        h.addWidget(self.alignCombo)

        def mkbtn1(text, tip):
            b = QPushButton(text);
            b.setToolTip(tip)
            b.setMinimumWidth(BTN_W);
            b.setMaximumWidth(BTN_W);
            return b

        self.linkBtn = mkbtn1("🔗", "Insert link…")
        self.unlinkBtn = mkbtn1("⛓", "Unlink")
        self.clearBtn = mkbtn1("⌫", "Clear formatting")
        for w in (self.linkBtn, self.unlinkBtn, self.clearBtn): h.addWidget(w)

        h.addStretch(1)
        main.addWidget(bar)

        self.editor = QTextEdit(self)
        self.editor.setAcceptRichText(True)
        self.editor.setPlaceholderText("Start typing…")
        self.editor.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.editor.customContextMenuRequested.connect(self.show_context_menu)
        main.addWidget(self.editor, 1)

        self.default_format = QTextCharFormat()
        default_font = "Times New Roman" if "Times New Roman" in installed else (
            "Times" if "Times" in installed else QFont().defaultFamily())
        idx = next((i for i in range(self.fontCombo.count()) if self.fontCombo.itemData(i) == default_font), 0)
        self.fontCombo.setCurrentIndex(idx)

        self.default_format.setFontFamily(self.fontCombo.currentData())
        self.default_format.setFontPointSize(float(self.sizeCombo.currentData()))
        _apply_char_format(self.editor, self.default_format)

        self.fontCombo.currentIndexChanged.connect(self._on_font)
        self.sizeCombo.currentIndexChanged.connect(self._on_size)
        self.boldBtn.clicked.connect(self._on_bold)
        self.italicBtn.clicked.connect(self._on_italic)
        self.underlineBtn.clicked.connect(self._on_underline)
        self.strikeBtn.clicked.connect(self._on_strike)
        self.textColorCombo.currentIndexChanged.connect(self._on_text_color)
        self.bgColorCombo.currentIndexChanged.connect(self._on_bg_color)
        self.headerCombo.currentIndexChanged.connect(self._on_header)
        self.olBtn.clicked.connect(lambda: self._on_list(True))
        self.ulBtn.clicked.connect(lambda: self._on_list(False))
        self.outdentBtn.clicked.connect(lambda: _set_indent(self.editor, -1))
        self.indentBtn.clicked.connect(lambda: _set_indent(self.editor, 1))
        self.alignCombo.currentIndexChanged.connect(self._on_align)
        self.linkBtn.clicked.connect(self._on_link)
        self.unlinkBtn.clicked.connect(self._on_unlink)
        self.clearBtn.clicked.connect(self._on_clear)

        self.editor.selectionChanged.connect(self._on_selection_changed)
        self.editor.textChanged.connect(self._on_text_changed)

    # ---- Public API ----
    def set_html(self, html: str):
        self.editor.setHtml(html or "")

    def get_html(self, callback):
        callback(self.editor.toHtml())

    def focus_editor(self):
        self.editor.setFocus()

    def setPlaceholderText(self, text: str):
        """Sets the placeholder text for the underlying QTextEdit."""
        self.editor.setPlaceholderText(text)

    # --- NEW: Anchor Formatting API ---
    def apply_anchor_format(self, anchor_id: int, tag_id: int, tag_name: str, comment: str, unique_doc_id: str):
        if not self.editor.textCursor().hasSelection():
            return
        fmt = QTextCharFormat()
        fmt.setBackground(QColor("#E0EFFF"))
        fmt.setProperty(AnchorIDProperty, anchor_id)
        fmt.setProperty(AnchorTagIDProperty, tag_id)
        fmt.setProperty(AnchorTagNameProperty, tag_name)
        fmt.setProperty(AnchorCommentProperty, comment)
        fmt.setProperty(AnchorUUIDProperty, unique_doc_id)
        tooltip = f"Tag: {tag_name}"
        if comment:
            tooltip += f"\n\nComment: {comment}"
        fmt.setToolTip(tooltip)
        _apply_char_format(self.editor, fmt)

    def remove_anchor_format(self):
        cursor = self.editor.textCursor()
        if not cursor.hasSelection():
            return
        fmt = cursor.charFormat()
        fmt.clearBackground()
        fmt.clearProperty(AnchorIDProperty)
        fmt.clearProperty(AnchorTagIDProperty)
        fmt.clearProperty(AnchorTagNameProperty)
        fmt.clearProperty(AnchorCommentProperty)
        fmt.clearProperty(AnchorUUIDProperty)
        fmt.setToolTip("")
        _apply_char_format(self.editor, fmt)

    def find_and_update_anchor_format(self, anchor_id: int, tag_id: int, tag_name: str, comment: str):
        cursor = self.editor.textCursor()
        cursor.setPosition(0)
        doc = self.editor.document()
        current_pos = 0
        while current_pos < doc.characterCount() - 1:
            cursor.setPosition(current_pos)
            cursor.movePosition(QTextCursor.MoveOperation.NextCharacter, QTextCursor.MoveMode.KeepAnchor, 1)
            fmt = cursor.charFormat()
            aid_qvar = fmt.property(AnchorIDProperty)
            aid = None
            if aid_qvar is not None:
                try:
                    if hasattr(aid_qvar, 'toInt'):
                        val, ok = aid_qvar.toInt()
                        if ok: aid = val
                    else:
                        aid = int(aid_qvar)
                except Exception:
                    pass
            if aid and aid == anchor_id:
                start_pos = cursor.position() - 1
                while not cursor.atEnd():
                    cursor.movePosition(QTextCursor.MoveOperation.NextCharacter, QTextCursor.MoveMode.KeepAnchor)
                    fmt = cursor.charFormat()
                    next_aid_qvar = fmt.property(AnchorIDProperty)
                    next_aid = None
                    if next_aid_qvar is not None:
                        try:
                            if hasattr(next_aid_qvar, 'toInt'):
                                val, ok = next_aid_qvar.toInt()
                                if ok: next_aid = val
                            else:
                                next_aid = int(next_aid_qvar)
                        except Exception:
                            pass
                    if next_aid != anchor_id:
                        cursor.movePosition(QTextCursor.MoveOperation.PreviousCharacter,
                                            QTextCursor.MoveMode.KeepAnchor)
                        break
                new_fmt = cursor.charFormat()
                new_fmt.setProperty(AnchorTagIDProperty, tag_id)
                new_fmt.setProperty(AnchorTagNameProperty, tag_name)
                new_fmt.setProperty(AnchorCommentProperty, comment)
                tooltip = f"Tag: {tag_name}"
                if comment:
                    tooltip += f"\n\nComment: {comment}"
                new_fmt.setToolTip(tooltip)
                cursor.setCharFormat(new_fmt)
                current_pos = cursor.position()
            else:
                current_pos += 1

    @Slot(QPoint)
    def show_context_menu(self, pos):
        menu = self.editor.createStandardContextMenu()
        cursor = self.editor.cursorForPosition(pos)
        char_format = cursor.charFormat()
        anchor_id_qvar = char_format.property(AnchorIDProperty)

        def to_int(qvar):
            if isinstance(qvar, int):
                return qvar if qvar > 0 else None
            try:
                if hasattr(qvar, 'toInt'):
                    val, ok = qvar.toInt()
                    if ok and val > 0:
                        return val
                elif qvar is not None:
                    val = int(qvar)
                    if val > 0:
                        return val
            except Exception:
                pass
            return None

        anchor_id = to_int(anchor_id_qvar)
        menu.addSeparator()

        if anchor_id:
            self.select_anchor_at_cursor(cursor)
            edit_action = QAction("Edit Synthesis Anchor...", self)
            edit_action.triggered.connect(lambda: self.anchorEditTriggered.emit(anchor_id))
            menu.addAction(edit_action)
            delete_action = QAction("Delete Synthesis Anchor", self)
            delete_action.triggered.connect(lambda: self.anchorDeleteTriggered.emit(anchor_id))
            menu.addAction(delete_action)
        else:
            anchor_action = QAction("Create Synthesis Anchor...", self)
            has_selection = self.editor.textCursor().hasSelection()
            anchor_action.setEnabled(has_selection)
            if has_selection:
                selected_text = self.editor.textCursor().selectedText()
                selected_text = selected_text.replace(u'\u2029', ' ').replace('\n', ' ').strip()
                anchor_action.triggered.connect(lambda: self.anchorActionTriggered.emit(selected_text))
            menu.addAction(anchor_action)
        menu.exec(self.editor.viewport().mapToGlobal(pos))

    def select_anchor_at_cursor(self, cursor):
        fmt = cursor.charFormat()
        anchor_id_qvar = fmt.property(AnchorIDProperty)
        anchor_id = None
        if anchor_id_qvar is not None:
            try:
                if hasattr(anchor_id_qvar, 'toInt'):
                    val, ok = anchor_id_qvar.toInt()
                    if ok: anchor_id = val
                else:
                    anchor_id = int(anchor_id_qvar)
            except Exception:
                pass
        if not anchor_id:
            return

        def get_anchor_id(fmt):
            qvar = fmt.property(AnchorIDProperty)
            if qvar is None: return None
            try:
                if hasattr(qvar, 'toInt'):
                    v, ok = qvar.toInt()
                    return v if ok else None
                return int(qvar)
            except Exception:
                return None

        while get_anchor_id(cursor.charFormat()) == anchor_id:
            if cursor.atBlockStart():
                break
            cursor.movePosition(QTextCursor.MoveOperation.PreviousCharacter, QTextCursor.MoveMode.MoveAnchor)
        if get_anchor_id(cursor.charFormat()) != anchor_id:
            cursor.movePosition(QTextCursor.MoveOperation.NextCharacter, QTextCursor.MoveMode.MoveAnchor)
        while get_anchor_id(cursor.charFormat()) == anchor_id:
            if cursor.atBlockEnd():
                break
            cursor.movePosition(QTextCursor.MoveOperation.NextCharacter, QTextCursor.MoveMode.KeepAnchor)
        if get_anchor_id(cursor.charFormat()) != anchor_id:
            cursor.movePosition(QTextCursor.MoveOperation.PreviousCharacter, QTextCursor.MoveMode.KeepAnchor)
        self.editor.setTextCursor(cursor)

    # ---- Handlers ----

    @Slot()
    def _on_text_changed(self):
        if self.editor.toPlainText() == "":
            self.editor.setCurrentCharFormat(self.default_format)

    @Slot()
    def _on_selection_changed(self):
        fmt = self.editor.currentCharFormat()
        self.boldBtn.setChecked(fmt.fontWeight() >= QFont.Weight.Bold)
        self.italicBtn.setChecked(fmt.fontItalic())
        self.underlineBtn.setChecked(fmt.fontUnderline())
        self.strikeBtn.setChecked(fmt.fontStrikeOut())

    def _on_font(self, idx: int):
        fam = self.fontCombo.itemData(idx)
        fmt = QTextCharFormat();
        fmt.setFontFamily(fam)
        _apply_char_format(self.editor, fmt)
        self.default_format.setFontFamily(fam)

    def _on_size(self, idx: int):
        pt = self.sizeCombo.itemData(idx)
        fmt = QTextCharFormat();
        fmt.setFontPointSize(float(pt))
        _apply_char_format(self.editor, fmt)
        self.default_format.setFontPointSize(float(pt))

    def _on_bold(self, on: bool):
        fmt = QTextCharFormat();
        fmt.setFontWeight(QFont.Weight.Bold if on else QFont.Weight.Normal)
        _apply_char_format(self.editor, fmt)

    def _on_italic(self, on: bool):
        fmt = QTextCharFormat();
        fmt.setFontItalic(on)
        _apply_char_format(self.editor, fmt)

    def _on_underline(self, on: bool):
        fmt = QTextCharFormat();
        fmt.setFontUnderline(on)
        _apply_char_format(self.editor, fmt)

    def _on_strike(self, on: bool):
        fmt = QTextCharFormat();
        fmt.setFontStrikeOut(on)
        _apply_char_format(self.editor, fmt)

    def _on_text_color(self, idx: int):
        data = self.textColorCombo.itemData(idx)
        if data == _CUSTOM:
            col = QColorDialog.getColor(parent=self)
            if not col.isValid():
                self.textColorCombo.setCurrentIndex(0)
                return
            fmt = QTextCharFormat();
            fmt.setForeground(col)
            _apply_char_format(self.editor, fmt)
        else:
            fmt = QTextCharFormat()
            if data:
                fmt.setForeground(QColor(data))
            else:
                fmt.clearForeground()
            _apply_char_format(self.editor, fmt)

    def _on_bg_color(self, idx: int):
        data = self.bgColorCombo.itemData(idx)
        if data == _CUSTOM:
            col = QColorDialog.getColor(parent=self)
            if not col.isValid():
                self.bgColorCombo.setCurrentIndex(0)
                return
            fmt = QTextCharFormat();
            fmt.setBackground(col)
            _apply_char_format(self.editor, fmt)
        else:
            fmt = QTextCharFormat()
            if data is None:
                current_bg = self.editor.currentCharFormat().background()
                if current_bg == QColor("#E0EFFF"):
                    self.bgColorCombo.setCurrentIndex(0)
                    return
                fmt.clearBackground()
            else:
                fmt.setBackground(QColor(data))
            _apply_char_format(self.editor, fmt)

    def _on_header(self, idx: int):
        level = self.headerCombo.itemData(idx)  # 0,1,2,3
        fmt = QTextCharFormat()
        fmt.setFontPointSize(self.default_format.fontPointSize())

        if level == 0:
            fmt.setFontWeight(QFont.Weight.Normal)
        else:
            sizes = {1: 24, 2: 18, 3: 16}
            fmt.setFontPointSize(sizes.get(level, 16));
            fmt.setFontWeight(QFont.Weight.Bold)
        _apply_char_format(self.editor, fmt)

    def _on_list(self, ordered: bool):
        c = self.editor.textCursor()
        if c.currentList():
            st = c.currentList().format().style()
            want = QTextListFormat.ListDecimal if ordered else QTextListFormat.ListDisc
            if st == want:
                start_block = c.selectionStart()
                end_block = c.selectionEnd()
                c.setPosition(start_block)

                while c.position() <= end_block or c.blockNumber() == c.document().findBlock(end_block).blockNumber():
                    list_item = c.block().textList()
                    if list_item:
                        list_item.remove(c.block())
                    if c.atEnd():
                        break
                    c.movePosition(QTextCursor.MoveOperation.NextBlock, QTextCursor.MoveMode.MoveAnchor)
            else:
                fmt = c.currentList().format();
                fmt.setStyle(want);
                c.currentList().setFormat(fmt)
        else:
            fmt = QTextListFormat()
            fmt.setStyle(QTextListFormat.ListDecimal if ordered else QTextListFormat.ListDisc)
            c.createList(fmt)
        self.editor.setTextCursor(c)

    def _on_align(self, idx: int):
        val = Qt.AlignmentFlag(self.alignCombo.itemData(idx))
        self.editor.setAlignment(val)

    def _on_link(self):
        c = self.editor.textCursor()
        if not c.hasSelection():
            QMessageBox.information(self, "Link", "Select text to make it a link.")
            return
        url, ok = QInputDialog.getText(self, "Insert Link", "URL:")
        if not ok or not url.strip():
            return
        fmt = QTextCharFormat()
        fmt.setAnchor(True);
        fmt.setAnchorHref(url.strip())
        fmt.setForeground(QColor("#0000EE"));
        fmt.setFontUnderline(True)
        _apply_char_format(self.editor, fmt)

    def _on_unlink(self):
        c = self.editor.textCursor()
        if not c.hasSelection(): return
        fmt = QTextCharFormat()
        fmt.setAnchor(False);
        fmt.clearForeground();
        fmt.setFontUnderline(False)
        _apply_char_format(self.editor, fmt)

    def _on_clear(self):
        c = self.editor.textCursor()
        # --- THIS IS THE FIX ---
        # Create a new format *by copying* the default.
        fmt = QTextCharFormat(self.default_format)
        # --- END FIX ---

        if not c.hasSelection():
            self.editor.setCurrentCharFormat(fmt)
        else:
            c.mergeCharFormat(fmt)
            self.editor.setTextCursor(c)