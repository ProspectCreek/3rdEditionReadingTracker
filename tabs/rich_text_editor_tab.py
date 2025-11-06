# tabs/rich_text_editor_tab.py
from PySide6.QtCore import Qt
from PySide6.QtGui import (
    QFontDatabase, QTextCharFormat, QTextCursor, QTextListFormat,
    QColor, QFont
)
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton,
    QTextEdit, QInputDialog, QMessageBox, QSizePolicy, QColorDialog
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
    Public API:
      - set_html(html: str)
      - get_html(callback)
      - focus_editor()
    """
    def __init__(self, title: str = "Editor", parent=None):
        super().__init__(parent)

        main = QVBoxLayout(self)
        main.setContentsMargins(6, 4, 6, 6)
        main.setSpacing(4)

        # ===== Toolbar (compact, no labels) =====
        bar = QWidget(self)
        bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        h = QHBoxLayout(bar)
        h.setContentsMargins(6, 4, 6, 4)
        h.setSpacing(6)

        bar.setStyleSheet("""
            QComboBox, QPushButton { height: 24px; font-size: 11px; }
            QComboBox::drop-down { width: 16px; }
        """)

        BTN_W  = 26
        BTN_WW = 28
        COMBO_FONT_W   = 120
        COMBO_SIZE_W   = 70
        COMBO_HDR_W    = 56
        COMBO_ALIGN_W  = 80
        COMBO_TXTCLR_W = 110
        COMBO_BGCLR_W  = 120

        # Font family (default: Times New Roman if present, else Times)
        self.fontCombo = QComboBox(bar); self.fontCombo.setToolTip("Font family")
        self.fontCombo.setMinimumWidth(COMBO_FONT_W); self.fontCombo.setMaximumWidth(COMBO_FONT_W)
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
        # choose default
        default_font = "Times New Roman" if "Times New Roman" in installed else ("Times" if "Times" in installed else QFont().defaultFamily())
        idx = next((i for i in range(self.fontCombo.count()) if self.fontCombo.itemData(i) == default_font), 0)
        self.fontCombo.setCurrentIndex(idx)
        h.addWidget(self.fontCombo)

        # Size (default 16 pt)
        self.sizeCombo = QComboBox(bar); self.sizeCombo.setToolTip("Font size (pt)")
        self.sizeCombo.setMinimumWidth(COMBO_SIZE_W); self.sizeCombo.setMaximumWidth(COMBO_SIZE_W)
        for sz in _PT_SIZES:
            self.sizeCombo.addItem(f"{sz} pt", sz)
        idx_sz = self.sizeCombo.findData(16)
        if idx_sz != -1:
            self.sizeCombo.setCurrentIndex(idx_sz)
        h.addWidget(self.sizeCombo)

        # Header level
        self.headerCombo = QComboBox(bar); self.headerCombo.setToolTip("Paragraph / H1 / H2 / H3")
        self.headerCombo.setMinimumWidth(COMBO_HDR_W); self.headerCombo.setMaximumWidth(COMBO_HDR_W)
        self.headerCombo.addItem("¶", 0); self.headerCombo.addItem("H1", 1)
        self.headerCombo.addItem("H2", 2); self.headerCombo.addItem("H3", 3)
        h.addWidget(self.headerCombo)

        # Inline toggles
        def mkbtn(text, tip):
            b = QPushButton(text); b.setCheckable(True); b.setToolTip(tip)
            b.setMinimumWidth(BTN_W); b.setMaximumWidth(BTN_W); return b
        self.boldBtn = mkbtn("B", "Bold")
        self.italicBtn = mkbtn("I", "Italic")
        self.underlineBtn = mkbtn("U", "Underline")
        self.strikeBtn = mkbtn("S", "Strikethrough")
        for w in (self.boldBtn, self.italicBtn, self.underlineBtn, self.strikeBtn): h.addWidget(w)

        # Text Color (with Custom…)
        self.textColorCombo = QComboBox(bar); self.textColorCombo.setToolTip("Text Color")
        self.textColorCombo.setMinimumWidth(COMBO_TXTCLR_W); self.textColorCombo.setMaximumWidth(COMBO_TXTCLR_W)
        self.textColorCombo.addItem("Text Color", None)  # default/clear
        for hexval, label in [("#000000","Black"),("#FF0000","Red"),("#008000","Green"),("#0000FF","Blue"),
                              ("#FA8000","Orange"),("#8000FF","Purple"),("#808080","Gray")]:
            self.textColorCombo.addItem(label, hexval)
        self.textColorCombo.addItem("Custom…", _CUSTOM)
        h.addWidget(self.textColorCombo)

        # Highlight (with No highlight + Custom…)
        self.bgColorCombo = QComboBox(bar); self.bgColorCombo.setToolTip("Highlight")
        self.bgColorCombo.setMinimumWidth(COMBO_BGCLR_W); self.bgColorCombo.setMaximumWidth(COMBO_BGCLR_W)
        self.bgColorCombo.addItem("Highlight", None)              # clear highlight
        self.bgColorCombo.addItem("No highlight (White)", "#FFFFFF")
        for hexval, label in [("#FFFF00","Yellow"),("#FFCCCC","L.Red"),("#CCFFCC","L.Green"),
                              ("#CCCCFF","L.Blue"),("#FFF2CC","L.Orange"),("#F3E5F5","Lavender")]:
            self.bgColorCombo.addItem(label, hexval)
        self.bgColorCombo.addItem("Custom…", _CUSTOM)
        h.addWidget(self.bgColorCombo)

        # Lists / Indent
        def mkbtn2(text, tip):
            b = QPushButton(text); b.setToolTip(tip)
            b.setMinimumWidth(BTN_WW); b.setMaximumWidth(BTN_WW); return b
        self.olBtn = mkbtn2("1.", "Numbered list")
        self.ulBtn = mkbtn2("•",  "Bulleted list")
        self.outdentBtn = mkbtn2("⟵", "Outdent")
        self.indentBtn  = mkbtn2("⟶", "Indent")
        for w in (self.olBtn, self.ulBtn, self.outdentBtn, self.indentBtn): h.addWidget(w)

        # Alignment
        self.alignCombo = QComboBox(bar); self.alignCombo.setToolTip("Alignment")
        self.alignCombo.setMinimumWidth(COMBO_ALIGN_W); self.alignCombo.setMaximumWidth(COMBO_ALIGN_W)
        for val, label in [(Qt.AlignLeft, "Left"), (Qt.AlignCenter, "Center"),
                           (Qt.AlignRight, "Right"), (Qt.AlignJustify, "Justify")]:
            self.alignCombo.addItem(label, int(val))
        h.addWidget(self.alignCombo)

        # Links + Clear
        def mkbtn1(text, tip):
            b = QPushButton(text); b.setToolTip(tip)
            b.setMinimumWidth(BTN_W); b.setMaximumWidth(BTN_W); return b
        self.linkBtn   = mkbtn1("🔗", "Insert link…")
        self.unlinkBtn = mkbtn1("⛓", "Unlink")
        self.clearBtn  = mkbtn1("⌫", "Clear formatting")
        for w in (self.linkBtn, self.unlinkBtn, self.clearBtn): h.addWidget(w)

        h.addStretch(1)
        main.addWidget(bar)

        # ===== Editor =====
        self.editor = QTextEdit(self)
        self.editor.setAcceptRichText(True)
        self.editor.setPlaceholderText("Start typing…")
        main.addWidget(self.editor, 1)

        # Apply defaults to the current typing format immediately
        default_fmt = QTextCharFormat()
        default_fmt.setFontFamily(self.fontCombo.currentData())
        default_fmt.setFontPointSize(float(self.sizeCombo.currentData()))
        _apply_char_format(self.editor, default_fmt)

        # Wire signals
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

    # ---- Public API ----
    def set_html(self, html: str):
        self.editor.setHtml(html or "")

    def get_html(self, callback):
        callback(self.editor.toHtml())

    def focus_editor(self):
        self.editor.setFocus()

    # ---- Handlers ----
    def _on_font(self, idx: int):
        fam = self.fontCombo.itemData(idx)
        fmt = QTextCharFormat(); fmt.setFontFamily(fam)
        _apply_char_format(self.editor, fmt)

    def _on_size(self, idx: int):
        pt = self.sizeCombo.itemData(idx)
        fmt = QTextCharFormat(); fmt.setFontPointSize(float(pt))
        _apply_char_format(self.editor, fmt)

    def _on_bold(self, on: bool):
        fmt = QTextCharFormat(); fmt.setFontWeight(QFont.Weight.Bold if on else QFont.Weight.Normal)
        _apply_char_format(self.editor, fmt)

    def _on_italic(self, on: bool):
        fmt = QTextCharFormat(); fmt.setFontItalic(on)
        _apply_char_format(self.editor, fmt)

    def _on_underline(self, on: bool):
        fmt = QTextCharFormat(); fmt.setFontUnderline(on)
        _apply_char_format(self.editor, fmt)

    def _on_strike(self, on: bool):
        fmt = QTextCharFormat(); fmt.setFontStrikeOut(on)
        _apply_char_format(self.editor, fmt)

    def _on_text_color(self, idx: int):
        data = self.textColorCombo.itemData(idx)
        if data == _CUSTOM:
            col = QColorDialog.getColor(parent=self)
            if not col.isValid():
                self.textColorCombo.setCurrentIndex(0)
                return
            fmt = QTextCharFormat(); fmt.setForeground(col)
            _apply_char_format(self.editor, fmt)
        else:
            fmt = QTextCharFormat()
            if data: fmt.setForeground(QColor(data))
            else:    fmt.clearForeground()
            _apply_char_format(self.editor, fmt)

    def _on_bg_color(self, idx: int):
        data = self.bgColorCombo.itemData(idx)
        if data == _CUSTOM:
            col = QColorDialog.getColor(parent=self)
            if not col.isValid():
                self.bgColorCombo.setCurrentIndex(0)
                return
            fmt = QTextCharFormat(); fmt.setBackground(col)
            _apply_char_format(self.editor, fmt)
        else:
            fmt = QTextCharFormat()
            if data is None:
                # "Highlight" default = clear any highlight
                fmt.clearBackground()
            else:
                fmt.setBackground(QColor(data))
            _apply_char_format(self.editor, fmt)

    def _on_header(self, idx: int):
        level = self.headerCombo.itemData(idx)  # 0,1,2,3
        fmt = QTextCharFormat()
        if level == 0:
            fmt.setFontPointSize(16); fmt.setFontWeight(QFont.Weight.Normal)
        else:
            sizes = {1: 24, 2: 18, 3: 16}
            fmt.setFontPointSize(sizes.get(level, 16)); fmt.setFontWeight(QFont.Weight.Bold)
        _apply_char_format(self.editor, fmt)

    def _on_list(self, ordered: bool):
        c = self.editor.textCursor()
        if c.currentList():
            st = c.currentList().format().style()
            want = QTextListFormat.ListDecimal if ordered else QTextListFormat.ListDisc
            if st == want:
                c.currentList().remove(c.block())
            else:
                fmt = c.currentList().format(); fmt.setStyle(want); c.currentList().setFormat(fmt)
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
        fmt.setAnchor(True); fmt.setAnchorHref(url.strip())
        fmt.setForeground(QColor("#0000EE")); fmt.setFontUnderline(True)
        _apply_char_format(self.editor, fmt)

    def _on_unlink(self):
        c = self.editor.textCursor()
        if not c.hasSelection(): return
        fmt = QTextCharFormat()
        fmt.setAnchor(False); fmt.clearForeground(); fmt.setFontUnderline(False)
        _apply_char_format(self.editor, fmt)

    def _on_clear(self):
        c = self.editor.textCursor()
        if not c.hasSelection():
            self.editor.setCurrentCharFormat(QTextCharFormat())
        else:
            fmt = QTextCharFormat(); c.mergeCharFormat(fmt); self.editor.setTextCursor(c)
