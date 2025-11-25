# tabs/rich_text_editor_tab.py
import sys
import uuid
import json
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton,
    QTextEdit, QInputDialog, QMessageBox, QSizePolicy, QColorDialog,
    QMenu
)
from PySide6.QtCore import Qt, Signal, QPoint, Slot, QUrl
from PySide6.QtGui import (
    QFontDatabase, QTextCharFormat, QTextCursor, QTextListFormat,
    QColor, QFont, QAction, QBrush
)

_PT_SIZES = [10, 12, 14, 16, 18, 20, 24, 32]
_FONTS = [
    "Times New Roman",
    "Times",
    "Sans Serif", "Serif", "Monospace",
    "Arial", "Georgia",
    "Courier New", "Tahoma", "Verdana", "Segoe UI",
]

_CUSTOM = "__custom__"

# --- Custom Property IDs ---
BaseAnchorProperty = 1001
AnchorIDProperty = BaseAnchorProperty + 1
AnchorTagIDProperty = BaseAnchorProperty + 2
AnchorTagNameProperty = BaseAnchorProperty + 3
AnchorCommentProperty = BaseAnchorProperty + 4
AnchorUUIDProperty = BaseAnchorProperty + 5
CitationDataProperty = BaseAnchorProperty + 10


def _apply_char_format(editor: QTextEdit, fmt: QTextCharFormat):
    """
    Applies formatting to the editor.
    Blocks signals to prevent 'Stack Overflow' crashes (0xC00000FD)
    when modifying large selections.
    """
    editor.blockSignals(True)
    try:
        c = editor.textCursor()
        if not c.hasSelection():
            editor.mergeCurrentCharFormat(fmt)
        else:
            c.mergeCharFormat(fmt)
            editor.setTextCursor(c)
    finally:
        editor.blockSignals(False)


def _set_indent(editor: QTextEdit, delta: int):
    c = editor.textCursor()
    bfmt = c.blockFormat()
    indent = max(0, bfmt.indent() + delta)
    bfmt.setIndent(indent)
    c.setBlockFormat(bfmt)
    editor.setTextCursor(c)


# --- SmartEditor Class ---
class SmartEditor(QTextEdit):
    """
    A customized QTextEdit that:
    1. Enforces default formatting on new lines (Enter key).
    2. Detects clicks on anchors/links and emits a signal.
    3. Shows a hand cursor when hovering over links, and reverts otherwise.
    """
    # Define a signal on the editor itself to bubble up clicks
    smartAnchorClicked = Signal(QUrl)

    def __init__(self, parent_tab, parent=None):
        super().__init__(parent)
        self.parent_tab = parent_tab
        self.setMouseTracking(True)  # Required for mouseMoveEvent without holding click

    def keyPressEvent(self, event):
        super().keyPressEvent(event)
        # If Enter/Return was pressed, force the default format onto the new block
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if self.parent_tab and hasattr(self.parent_tab, 'default_format'):
                self.setCurrentCharFormat(self.parent_tab.default_format)

    def mouseMoveEvent(self, event):
        # 1. Execute standard behavior first
        super().mouseMoveEvent(event)

        # 2. Check if hovering over a link/anchor
        pos = event.position().toPoint()
        anchor = self.anchorAt(pos)

        if anchor:
            # Hovering over a link -> Hand Cursor
            self.viewport().setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            # NOT hovering over a link -> Revert to standard text cursor (IBeam)
            self.viewport().setCursor(Qt.CursorShape.IBeamCursor)

    def mouseReleaseEvent(self, event):
        # Detect link/anchor clicks
        pos = event.position().toPoint()
        anchor = self.anchorAt(pos)

        if anchor:
            self.smartAnchorClicked.emit(QUrl(anchor))

        super().mouseReleaseEvent(event)


class RichTextEditorTab(QWidget):
    """
    Native Qt rich-text editor with support for Synthesis Anchors AND Citations.
    """

    anchorActionTriggered = Signal(str)
    anchorEditTriggered = Signal(int)
    anchorDeleteTriggered = Signal(int)
    anchorClicked = Signal(QUrl)
    citationEditTriggered = Signal(str)

    # --- NEW: Signal for linking PDF Node ---
    linkPdfNodeTriggered = Signal()

    # --- END NEW ---

    def __init__(self, title: str = "Editor", spell_checker_service=None, parent=None):
        super().__init__(parent)
        self.editor_title = title
        self.spell_checker_service = spell_checker_service

        main = QVBoxLayout(self)
        main.setContentsMargins(6, 4, 6, 6)
        main.setSpacing(4)

        # ===== Toolbar =====
        bar = QWidget(self)
        bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        h = QHBoxLayout(bar)
        h.setContentsMargins(6, 4, 6, 4)
        h.setSpacing(6)

        bar.setStyleSheet("""
            QComboBox, QPushButton { 
                height: 24px; 
                font-size: 11px; 
                padding: 2px 4px;
                margin: 0px;
                border-radius: 3px;
                background-color: #FFFFFF;
                border: 1px solid #D1D5DB;
                color: #374151;
            }
            QPushButton { min-width: 20px; }
            QPushButton:hover, QComboBox:hover { background-color: #F3F4F6; border-color: #9CA3AF; }
            QPushButton:checked { background-color: #E5E7EB; border-color: #6B7280; }
            QComboBox::drop-down { width: 16px; border: none; background: transparent; }
        """)

        # Font Family
        self.fontCombo = QComboBox(bar)
        self.fontCombo.setMinimumWidth(120)
        installed = set(QFontDatabase().families())
        for fam in _FONTS:
            mapped = fam
            if fam == "Sans Serif": mapped = QFont().defaultFamily()
            if fam == "Serif": mapped = "Times New Roman" if "Times New Roman" in installed else "Times"
            self.fontCombo.addItem(fam, mapped)
        h.addWidget(self.fontCombo)

        # Font Size
        self.sizeCombo = QComboBox(bar)
        self.sizeCombo.setMinimumWidth(70)
        for sz in _PT_SIZES: self.sizeCombo.addItem(f"{sz} pt", sz)
        h.addWidget(self.sizeCombo)

        # Headers
        self.headerCombo = QComboBox(bar)
        self.headerCombo.setMinimumWidth(56)
        self.headerCombo.addItem("¶", 0)
        self.headerCombo.addItem("H1", 1)
        self.headerCombo.addItem("H2", 2)
        self.headerCombo.addItem("H3", 3)
        h.addWidget(self.headerCombo)

        # Format Buttons
        def mkbtn(t, tip):
            b = QPushButton(t)
            b.setCheckable(True)
            b.setToolTip(tip)
            b.setFixedWidth(26)
            return b

        self.boldBtn = mkbtn("B", "Bold")
        self.italicBtn = mkbtn("I", "Italic")
        self.underlineBtn = mkbtn("U", "Underline")
        self.strikeBtn = mkbtn("S", "Strikethrough")
        for w in (self.boldBtn, self.italicBtn, self.underlineBtn, self.strikeBtn): h.addWidget(w)

        # Colors
        self.textColorCombo = QComboBox(bar)
        self.textColorCombo.setMinimumWidth(110)
        self.textColorCombo.addItem("Text Color", None)
        self.textColorCombo.addItem("Custom…", _CUSTOM)
        h.addWidget(self.textColorCombo)

        self.bgColorCombo = QComboBox(bar)
        self.bgColorCombo.setMinimumWidth(120)
        self.bgColorCombo.addItem("Highlight", None)
        self.bgColorCombo.addItem("No highlight", "#FFFFFF")
        self.bgColorCombo.addItem("Custom…", _CUSTOM)
        h.addWidget(self.bgColorCombo)

        # Alignment
        self.alignCombo = QComboBox(bar)
        self.alignCombo.addItem("Left", int(Qt.AlignLeft))
        self.alignCombo.addItem("Center", int(Qt.AlignCenter))
        h.addWidget(self.alignCombo)

        # Links/Clear
        def mkbtn1(t, tip):
            b = QPushButton(t)
            b.setToolTip(tip)
            b.setFixedWidth(26)
            return b

        self.linkBtn = mkbtn1("🔗", "Link")
        self.unlinkBtn = mkbtn1("⛓", "Unlink")
        self.clearBtn = mkbtn1("⌫", "Clear")

        # Lists
        self.ulBtn = mkbtn1("•", "Bulleted List")
        self.olBtn = mkbtn1("1.", "Numbered List")

        for w in (self.ulBtn, self.olBtn, self.linkBtn, self.unlinkBtn, self.clearBtn): h.addWidget(w)

        h.addStretch(1)
        main.addWidget(bar)

        # ===== Editor (Using SmartEditor) =====
        self.editor = SmartEditor(self, self)  # Pass self as parent_tab
        self.editor.setAcceptRichText(True)
        self.editor.setPlaceholderText("Start typing…")

        self.editor.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.editor.customContextMenuRequested.connect(self.show_context_menu)

        # Connect the custom SmartEditor signal to the Tab's signal
        self.editor.smartAnchorClicked.connect(self.anchorClicked)

        if self.spell_checker_service:
            try:
                from .spell_check_highlighter import SpellCheckHighlighter
                self.highlighter = SpellCheckHighlighter(self.editor.document(), self.spell_checker_service)
            except ImportError:
                pass

        main.addWidget(self.editor, 1)

        # Defaults
        self.default_format = QTextCharFormat()
        installed_families = set(QFontDatabase().families())
        default_font = "Times New Roman" if "Times New Roman" in installed_families else QFont().defaultFamily()

        idx = next((i for i in range(self.fontCombo.count()) if self.fontCombo.itemData(i) == default_font), 0)
        self.fontCombo.setCurrentIndex(idx)
        self.sizeCombo.setCurrentIndex(self.sizeCombo.findData(16))

        self.default_format.setFontFamily(self.fontCombo.currentData())
        self.default_format.setFontPointSize(16.0)

        _apply_char_format(self.editor, self.default_format)

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
        self.alignCombo.currentIndexChanged.connect(self._on_align)

        self.ulBtn.clicked.connect(lambda: self._on_list(False))
        self.olBtn.clicked.connect(lambda: self._on_list(True))

        self.linkBtn.clicked.connect(self._on_link)
        self.unlinkBtn.clicked.connect(self._on_unlink)
        self.clearBtn.clicked.connect(self._on_clear)

        self.editor.selectionChanged.connect(self._on_selection_changed)
        self.editor.textChanged.connect(self._on_text_changed)

    # ---- Public API ----
    def set_html(self, html):
        self.editor.setHtml(html or "")

    def get_html(self, cb):
        cb(self.editor.toHtml())

    def focus_editor(self):
        self.editor.setFocus()

    def setPlaceholderText(self, text: str):
        self.editor.setPlaceholderText(text)

    # --- Anchor API ---
    def apply_anchor_format(self, anchor_id, tag_id, tag_name, comment, unique_doc_id):
        if not self.editor.textCursor().hasSelection(): return
        # Save typing format
        pre = self.default_format

        fmt = QTextCharFormat()
        fmt.setForeground(QColor("#0000EE"))
        fmt.setFontUnderline(True)
        fmt.setAnchor(True)
        fmt.setAnchorHref(f"anchor:{anchor_id}")
        fmt.setProperty(AnchorIDProperty, anchor_id)
        fmt.setProperty(AnchorTagIDProperty, tag_id)
        fmt.setProperty(AnchorTagNameProperty, tag_name)
        fmt.setProperty(AnchorCommentProperty, comment)
        fmt.setProperty(AnchorUUIDProperty, unique_doc_id)
        fmt.setToolTip(f"Tag: {tag_name}\n{comment}")
        _apply_char_format(self.editor, fmt)

        # Reset typing format
        c = self.editor.textCursor()
        c.setPosition(c.selectionEnd())
        self.editor.setTextCursor(c)
        self.editor.setCurrentCharFormat(pre)

    def remove_anchor_format(self):
        cursor = self.editor.textCursor()
        if not cursor.hasSelection(): return

        fmt = cursor.charFormat()
        fmt.clearBackground()
        fmt.clearProperty(AnchorIDProperty)
        fmt.clearProperty(AnchorTagIDProperty)
        fmt.clearProperty(AnchorTagNameProperty)
        fmt.clearProperty(AnchorCommentProperty)
        fmt.clearProperty(AnchorUUIDProperty)
        fmt.setAnchor(False)
        fmt.setAnchorHref("")
        fmt.setToolTip("")

        if fmt.foreground().color() == QColor("#0000EE"):
            fmt.setForeground(self.default_format.foreground())
            fmt.setFontUnderline(False)

        _apply_char_format(self.editor, fmt)

    def find_and_update_anchor_format(self, anchor_id, tag_id, tag_name, comment):
        c = self.editor.textCursor()
        c.setPosition(0)
        doc = self.editor.document()
        pos = 0
        while pos < doc.characterCount() - 1:
            c.setPosition(pos)
            c.movePosition(QTextCursor.NextCharacter, QTextCursor.KeepAnchor)
            aid = self._get_id(c.charFormat())
            if aid == anchor_id:
                while not c.atEnd():
                    c.movePosition(QTextCursor.NextCharacter, QTextCursor.KeepAnchor)
                    if self._get_id(c.charFormat()) != anchor_id:
                        c.movePosition(QTextCursor.PreviousCharacter, QTextCursor.KeepAnchor)
                        break

                f = c.charFormat()
                f.setProperty(AnchorTagIDProperty, tag_id)
                f.setProperty(AnchorTagNameProperty, tag_name)
                f.setProperty(AnchorCommentProperty, comment)
                f.setToolTip(f"Tag: {tag_name}\n{comment}")
                c.setCharFormat(f)
                pos = c.position()
            else:
                pos += 1

    def find_and_remove_anchor_format(self, anchor_id):
        c = self.editor.textCursor()
        c.setPosition(0)
        doc = self.editor.document()
        pos = 0
        while pos < doc.characterCount() - 1:
            c.setPosition(pos)
            c.movePosition(QTextCursor.NextCharacter, QTextCursor.KeepAnchor)
            if self._get_id(c.charFormat()) == anchor_id:
                while not c.atEnd():
                    c.movePosition(QTextCursor.NextCharacter, QTextCursor.KeepAnchor)
                    if self._get_id(c.charFormat()) != anchor_id:
                        c.movePosition(QTextCursor.PreviousCharacter, QTextCursor.KeepAnchor)
                        break
                self.editor.setTextCursor(c)
                self.remove_anchor_format()
                return
            else:
                pos += 1

    def focus_anchor_by_id(self, anchor_id):
        if not anchor_id: return False
        c = self.editor.textCursor()
        c.setPosition(0)
        doc = self.editor.document()
        pos = 0
        while pos < doc.characterCount() - 1:
            c.setPosition(pos)
            c.movePosition(QTextCursor.NextCharacter, QTextCursor.KeepAnchor)
            if self._get_id(c.charFormat()) == anchor_id:
                self.editor.setTextCursor(c)
                self.editor.ensureCursorVisible()
                self.editor.setFocus()
                return True
            pos += 1
        return False

    def _get_id(self, fmt):
        href = fmt.anchorHref()
        if href and href.startswith("anchor:"):
            try:
                return int(href.split(":")[-1])
            except:
                pass
        val = fmt.property(AnchorIDProperty)
        try:
            if hasattr(val, 'toInt'): val = val.toInt()[0]
            return int(val) if val else None
        except:
            return None

    # --- Citation API ---
    def apply_citation_format(self, citation_data_json):
        if not self.editor.textCursor().hasSelection(): return
        fmt = QTextCharFormat()
        fmt.setProperty(CitationDataProperty, citation_data_json)
        fmt.setToolTip("Right-click to Edit Citation")
        _apply_char_format(self.editor, fmt)

    # --- Spell Check ---
    def correct_word(self, cursor, new_word):
        cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        cursor.beginEditBlock()
        cursor.removeSelectedText()
        cursor.insertText(new_word)
        cursor.endEditBlock()
        if hasattr(self, 'highlighter'): self.highlighter.rehighlightBlock(cursor.block())

    def add_to_dictionary(self, word):
        if self.spell_checker_service:
            self.spell_checker_service.add_to_dictionary(word.lower().strip(".,!?;:()[]{}'\""))
            if hasattr(self, 'highlighter'): self.highlighter.rehighlight()

    @Slot(QPoint)
    def show_context_menu(self, pos):
        menu = self.editor.createStandardContextMenu()
        cursor = self.editor.cursorForPosition(pos)
        fmt = cursor.charFormat()

        aid = self._get_id(fmt)
        cit_data = fmt.property(CitationDataProperty)

        # Fallback check for citation if cursor is at the edge
        if not cit_data:
            cursor.movePosition(QTextCursor.PreviousCharacter, QTextCursor.KeepAnchor)
            fmt_prev = cursor.charFormat()
            if fmt_prev.property(CitationDataProperty):
                cit_data = fmt_prev.property(CitationDataProperty)
                cursor = self.editor.cursorForPosition(pos)

        # Spell Check
        if self.spell_checker_service and not aid and not cit_data:
            sc = self.editor.cursorForPosition(pos)
            sc.select(QTextCursor.WordUnderCursor)
            w = sc.selectedText().strip(".,!?;:()[]{}'\"")
            if w and self.spell_checker_service.is_misspelled(w):
                sugs = self.spell_checker_service.suggest(w)
                sm = QMenu("Spelling Suggestions", self)
                if sugs:
                    for s in sugs:
                        a = QAction(s, self)
                        a.triggered.connect(lambda c=False, cu=QTextCursor(sc), word=s: self.correct_word(cu, word))
                        sm.addAction(a)
                else:
                    na = QAction("No suggestions", self);
                    na.setEnabled(False);
                    sm.addAction(na)

                sm.addSeparator()
                ad = QAction(f"Add '{w}'", self)
                ad.triggered.connect(lambda c=False, word=w: self.add_to_dictionary(word))
                sm.addAction(ad)

                menu.insertMenu(menu.actions()[0], sm)
                menu.insertSeparator(menu.actions()[1])

        menu.addSeparator()

        if aid:
            self.select_anchor_at_cursor(cursor)
            ea = QAction("Edit Synthesis Anchor...", self)
            ea.triggered.connect(lambda: self.anchorEditTriggered.emit(aid))
            menu.addAction(ea)
            da = QAction("Delete Synthesis Anchor", self)
            da.triggered.connect(lambda: self.anchorDeleteTriggered.emit(aid))
            menu.addAction(da)

        elif cit_data:
            self._select_citation_at_cursor(cursor)
            ec = QAction("Edit Citation...", self)
            ec.triggered.connect(lambda: self.citationEditTriggered.emit(str(cit_data)))
            menu.addAction(ec)

        else:
            # --- NEW: Add Link to PDF Node Option ---
            link_pdf_action = QAction("Link to PDF Node...", self)
            # Only enable if there is a selection
            if self.editor.textCursor().hasSelection():
                link_pdf_action.triggered.connect(self.linkPdfNodeTriggered.emit)
            else:
                link_pdf_action.setEnabled(False)
            menu.addAction(link_pdf_action)
            menu.addSeparator()
            # --- END NEW ---

            ca = QAction("Create Synthesis Anchor...", self)
            if self.editor.textCursor().hasSelection():
                txt = self.editor.textCursor().selectedText().strip()
                ca.triggered.connect(lambda: self.anchorActionTriggered.emit(txt))
            else:
                ca.setEnabled(False)
            menu.addAction(ca)

        menu.exec(self.editor.viewport().mapToGlobal(pos))

    def select_anchor_at_cursor(self, cursor):
        fmt = cursor.charFormat()
        aid = self._get_id(fmt)
        if not aid: return

        while self._get_id(cursor.charFormat()) == aid:
            if cursor.atBlockStart(): break
            cursor.movePosition(QTextCursor.PreviousCharacter, QTextCursor.MoveAnchor)
        if self._get_id(cursor.charFormat()) != aid:
            cursor.movePosition(QTextCursor.NextCharacter, QTextCursor.MoveAnchor)

        while self._get_id(cursor.charFormat()) == aid:
            if cursor.atBlockEnd(): break
            cursor.movePosition(QTextCursor.NextCharacter, QTextCursor.KeepAnchor)
        if self._get_id(cursor.charFormat()) != aid:
            cursor.movePosition(QTextCursor.PreviousCharacter, QTextCursor.KeepAnchor)

        self.editor.setTextCursor(cursor)

    def _select_citation_at_cursor(self, cursor):
        fmt = cursor.charFormat()
        target = fmt.property(CitationDataProperty)
        if not target: return

        while cursor.charFormat().property(CitationDataProperty) == target:
            if cursor.atBlockStart(): break
            cursor.movePosition(QTextCursor.PreviousCharacter, QTextCursor.MoveAnchor)
        if cursor.charFormat().property(CitationDataProperty) != target:
            cursor.movePosition(QTextCursor.NextCharacter, QTextCursor.MoveAnchor)

        while cursor.charFormat().property(CitationDataProperty) == target:
            if cursor.atBlockEnd(): break
            cursor.movePosition(QTextCursor.NextCharacter, QTextCursor.KeepAnchor)

        self.editor.setTextCursor(cursor)

    # --- Formatting Handlers ---
    def _on_font(self, i):
        self.default_format.setFontFamily(self.fontCombo.itemData(i))
        _apply_char_format(self.editor, self.default_format)

    def _on_size(self, i):
        self.default_format.setFontPointSize(float(self.sizeCombo.itemData(i)))
        _apply_char_format(self.editor, self.default_format)

    def _on_bold(self, c):
        f = QTextCharFormat();
        f.setFontWeight(QFont.Weight.Bold if c else QFont.Weight.Normal);
        _apply_char_format(self.editor, f)

    def _on_italic(self, c):
        f = QTextCharFormat();
        f.setFontItalic(c);
        _apply_char_format(self.editor, f)

    def _on_underline(self, c):
        f = QTextCharFormat();
        f.setFontUnderline(c);
        _apply_char_format(self.editor, f)

    def _on_strike(self, c):
        f = QTextCharFormat();
        f.setFontStrikeOut(c);
        _apply_char_format(self.editor, f)

    def _on_text_color(self, i):
        d = self.textColorCombo.itemData(i)
        if d == _CUSTOM:
            c = QColorDialog.getColor(parent=self);
            if c.isValid(): f = QTextCharFormat(); f.setForeground(c); _apply_char_format(self.editor, f)
        else:
            f = QTextCharFormat();
            if d:
                f.setForeground(QColor(d))
            else:
                f.clearForeground()
            _apply_char_format(self.editor, f)

    def _on_bg_color(self, i):
        d = self.bgColorCombo.itemData(i)
        if d == _CUSTOM:
            c = QColorDialog.getColor(parent=self)
            if c.isValid(): f = QTextCharFormat(); f.setBackground(c); _apply_char_format(self.editor, f)
        else:
            f = QTextCharFormat()
            href = self.editor.currentCharFormat().anchorHref()
            if href and href.startswith("anchor:"):
                self.bgColorCombo.setCurrentIndex(0);
                return

            if d:
                f.setBackground(QColor(d))
            else:
                f.clearBackground()
            _apply_char_format(self.editor, f)

    def _on_header(self, i):
        lvl = self.headerCombo.itemData(i)
        f = QTextCharFormat()
        f.setFontPointSize(self.default_format.fontPointSize())
        if lvl > 0:
            f.setFontWeight(QFont.Weight.Bold);
            f.setFontPointSize({1: 24, 2: 18, 3: 16}.get(lvl))
        else:
            f.setFontWeight(QFont.Weight.Normal)
        _apply_char_format(self.editor, f)

    def _on_align(self, i):
        self.editor.setAlignment(Qt.AlignmentFlag(self.alignCombo.itemData(i)))

    def _on_list(self, ordered):
        c = self.editor.textCursor()
        if c.currentList():
            style = c.currentList().format().style()
            target = QTextListFormat.ListDecimal if ordered else QTextListFormat.ListDisc
            if style == target:
                block = c.block()
                if block.textList(): block.textList().remove(block)
            else:
                fmt = c.currentList().format();
                fmt.setStyle(target);
                c.currentList().setFormat(fmt)
        else:
            fmt = QTextListFormat();
            fmt.setStyle(QTextListFormat.ListDecimal if ordered else QTextListFormat.ListDisc);
            c.createList(fmt)
        self.editor.setTextCursor(c)

    def _on_link(self):
        c = self.editor.textCursor()
        if not c.hasSelection(): QMessageBox.information(self, "Link", "Select text."); return
        url, ok = QInputDialog.getText(self, "Link", "URL:")
        if not ok or not url.strip(): return
        href = c.charFormat().anchorHref()
        if href and href.startswith("anchor:"): QMessageBox.warning(self, "No", "Cannot edit anchor link."); return
        f = QTextCharFormat();
        f.setAnchor(True);
        f.setAnchorHref(url.strip());
        f.setForeground(QColor("#0000EE"));
        f.setFontUnderline(True)
        _apply_char_format(self.editor, f)

    def _on_unlink(self):
        c = self.editor.textCursor();
        href = c.charFormat().anchorHref()
        if href and href.startswith("anchor:"): QMessageBox.warning(self, "No", "Cannot unlink anchor."); return
        f = QTextCharFormat();
        f.setAnchor(False);
        f.clearForeground();
        f.setFontUnderline(False)
        _apply_char_format(self.editor, f)

    def _on_clear(self):
        c = self.editor.textCursor()
        if not c.hasSelection():
            self.editor.setCurrentCharFormat(self.default_format)
        else:
            f = self.default_format.clone()
            c.mergeCharFormat(f)
            self.editor.setTextCursor(c)

    def _on_selection_changed(self):
        fmt = self.editor.currentCharFormat()
        self.boldBtn.setChecked(fmt.fontWeight() >= QFont.Weight.Bold)
        self.italicBtn.setChecked(fmt.fontItalic())
        self.underlineBtn.setChecked(fmt.fontUnderline())
        self.strikeBtn.setChecked(fmt.fontStrikeOut())

    # --- FORCE FORMAT ON EMPTY LINE ---
    def _on_text_changed(self):
        cursor = self.editor.textCursor()
        block = cursor.block()
        if block.length() <= 1:
            self.editor.setCurrentCharFormat(self.default_format)