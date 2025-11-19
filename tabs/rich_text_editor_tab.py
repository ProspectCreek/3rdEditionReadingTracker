import sys
import uuid  # <-- NEW: For synthesis anchors
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton,
    QTextBrowser, QInputDialog, QMessageBox, QSizePolicy, QColorDialog,
    QMenu
)
from PySide6.QtCore import Qt, Signal, QPoint, Slot, QUrl  # <-- Added Slot
from PySide6.QtGui import (
    QFontDatabase, QTextCharFormat, QTextCursor, QTextListFormat,
    QColor, QFont, QAction, QBrush
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

# --- NEW: Custom Property IDs for Anchors ---
# Qt reserves property IDs up to 1000. User properties should start above that.
BaseAnchorProperty = 1001
AnchorIDProperty = BaseAnchorProperty + 1
AnchorTagIDProperty = BaseAnchorProperty + 2
AnchorTagNameProperty = BaseAnchorProperty + 3
AnchorCommentProperty = BaseAnchorProperty + 4
AnchorUUIDProperty = BaseAnchorProperty + 5
# --- END NEW ---


def _apply_char_format(editor: QTextBrowser, fmt: QTextCharFormat):
    c = editor.textCursor()
    if not c.hasSelection():
        # This modifies the *current* format for new text
        editor.mergeCurrentCharFormat(fmt)
    else:
        # This modifies the *selected* text
        c.mergeCharFormat(fmt)
        editor.setTextCursor(c)


def _set_indent(editor: QTextBrowser, delta: int):
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

    # --- NEW: Signals for Synthesis Anchors ---
    anchorActionTriggered = Signal(str)  # Emits selected_text
    anchorEditTriggered = Signal(int)  # Emits anchor_id
    anchorDeleteTriggered = Signal(int)  # Emits anchor_id
    anchorClicked = Signal(QUrl)  # --- NEW SIGNAL ---

    # --- END NEW ---

    def __init__(self, title: str = "Editor", spell_checker_service=None, parent=None):
        super().__init__(parent)
        self.editor_title = title
        self.spell_checker_service = spell_checker_service  # <-- STORE SERVICE

        main = QVBoxLayout(self)
        main.setContentsMargins(6, 4, 6, 6)
        main.setSpacing(4)

        # ===== Toolbar (compact, no labels) =====
        bar = QWidget(self)
        bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        h = QHBoxLayout(bar)
        h.setContentsMargins(6, 4, 6, 4)
        h.setSpacing(6)

        # --- FIX: Stylesheet Override ---
        # We explicitly define borders for both QComboBox and QPushButton here
        # to ensure they look consistent and visible.
        bar.setStyleSheet("""
            QComboBox, QPushButton { 
                height: 24px; 
                font-size: 11px; 
                padding: 2px 4px;     /* Slight horizontal padding for text */
                margin: 0px;
                border-radius: 3px;
                background-color: #FFFFFF;
                border: 1px solid #D1D5DB; /* Define explicit border */
                color: #374151;
            }
            QPushButton {
                min-width: 20px;
            }
            QPushButton:hover, QComboBox:hover {
                background-color: #F3F4F6;
                border-color: #9CA3AF;
            }
            QPushButton:checked {
                background-color: #E5E7EB;
                border-color: #6B7280;
            }
            QComboBox::drop-down { 
                width: 16px;
                border: none; /* Let main border handle it */
                background: transparent;
            }
        """)
        # --- END FIX ---

        BTN_W = 26
        BTN_WW = 28
        COMBO_FONT_W = 120
        COMBO_SIZE_W = 70
        COMBO_HDR_W = 56
        COMBO_ALIGN_W = 80
        COMBO_TXTCLR_W = 110
        COMBO_BGCLR_W = 120

        # Font family (default: Times New Roman if present, else Times)
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

        # Size (default 16 pt)
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

        # Header level
        self.headerCombo = QComboBox(bar);
        self.headerCombo.setToolTip("Paragraph / H1 / H2 / H3")
        self.headerCombo.setMinimumWidth(COMBO_HDR_W);
        self.headerCombo.setMaximumWidth(COMBO_HDR_W)
        self.headerCombo.addItem("¶", 0);
        self.headerCombo.addItem("H1", 1)
        self.headerCombo.addItem("H2", 2);
        self.headerCombo.addItem("H3", 3)
        h.addWidget(self.headerCombo)

        # Inline toggles
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

        # Text Color (with Custom…)
        self.textColorCombo = QComboBox(bar);
        self.textColorCombo.setToolTip("Text Color")
        self.textColorCombo.setMinimumWidth(COMBO_TXTCLR_W);
        self.textColorCombo.setMaximumWidth(COMBO_TXTCLR_W)
        self.textColorCombo.addItem("Text Color", None)  # default/clear
        for hexval, label in [("#000000", "Black"), ("#FF0000", "Red"), ("#008000", "Green"), ("#0000FF", "Blue"),
                              ("#FA8000", "Orange"), ("#8000FF", "Purple"), ("#808080", "Gray")]:
            self.textColorCombo.addItem(label, hexval)
        self.textColorCombo.addItem("Custom…", _CUSTOM)
        h.addWidget(self.textColorCombo)

        # Highlight (with No highlight + Custom…)
        self.bgColorCombo = QComboBox(bar);
        self.bgColorCombo.setToolTip("Highlight")
        self.bgColorCombo.setMinimumWidth(COMBO_BGCLR_W);
        self.bgColorCombo.setMaximumWidth(COMBO_BGCLR_W)
        self.bgColorCombo.addItem("Highlight", None)  # clear highlight
        self.bgColorCombo.addItem("No highlight (White)", "#FFFFFF")
        for hexval, label in [("#FFFF00", "Yellow"), ("#FFCCCC", "L.Red"), ("#CCFFCC", "L.Green"),
                              ("#CCCCFF", "L.Blue"), ("#FFF2CC", "L.Orange"), ("#F3E5F5", "Lavender")]:
            self.bgColorCombo.addItem(label, hexval)
        self.bgColorCombo.addItem("Custom…", _CUSTOM)
        h.addWidget(self.bgColorCombo)

        # Lists / Indent
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

        # Alignment
        self.alignCombo = QComboBox(bar);
        self.alignCombo.setToolTip("Alignment")
        self.alignCombo.setMinimumWidth(COMBO_ALIGN_W);
        self.alignCombo.setMaximumWidth(COMBO_ALIGN_W)
        for val, label in [(Qt.AlignLeft, "Left"), (Qt.AlignCenter, "Center"),
                           (Qt.AlignRight, "Right"), (Qt.AlignJustify, "Justify")]:
            self.alignCombo.addItem(label, int(val))
        h.addWidget(self.alignCombo)

        # Links + Clear
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

        # ===== Editor =====
        # --- FIX: Use QTextBrowser to get anchorClicked signal ---
        self.editor = QTextBrowser(self)
        self.editor.setReadOnly(False)  # Make it editable

        # We need BOTH flags: TextEditorInteraction for editing,
        # and LinksAccessibleByMouse for the hand cursor and click signal.
        self.editor.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextEditorInteraction |
            Qt.TextInteractionFlag.LinksAccessibleByMouse
        )

        self.editor.setOpenLinks(False)  # Intercept link clicks
        # --- END FIX ---

        self.editor.setAcceptRichText(True)
        self.editor.setPlaceholderText("Start typing…")
        # --- NEW: Enable custom context menu ---
        self.editor.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.editor.customContextMenuRequested.connect(self.show_context_menu)
        # --- Connect the editor's built-in signal ---
        self.editor.anchorClicked.connect(self.anchorClicked)
        # --- END NEW ---
        # --- NEW: Add Spell Check Highlighter ---
        if self.spell_checker_service:
            try:
                from .spell_check_highlighter import SpellCheckHighlighter
                self.highlighter = SpellCheckHighlighter(self.editor.document(), self.spell_checker_service)
            except ImportError as e:
                print(f"Could not import SpellCheckHighlighter: {e}")
        # --- END NEW ---

        main.addWidget(self.editor, 1)

        # Apply defaults to the current typing format immediately
        # --- FIX: Store the default format as an instance attribute ---
        self.default_format = QTextCharFormat()
        installed_families = set(QFontDatabase().families())
        default_font = "Times New Roman" if "Times New Roman" in installed_families else (
            "Times" if "Times" in installed_families else QFont().defaultFamily())
        idx = next((i for i in range(self.fontCombo.count()) if self.fontCombo.itemData(i) == default_font), 0)
        self.fontCombo.setCurrentIndex(idx)

        # Set font family and size from the combo boxes
        self.default_format.setFontFamily(self.fontCombo.currentData())
        self.default_format.setFontPointSize(float(self.sizeCombo.currentData()))
        _apply_char_format(self.editor, self.default_format)
        # --- END FIX ---

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

        self.editor.selectionChanged.connect(self._on_selection_changed)

        # --- NEW FIX: Connect textChanged signal ---
        self.editor.textChanged.connect(self._on_text_changed)
        # --- END NEW FIX ---

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

    # --- NEW: Spell Check Context Menu Methods ---


    def correct_word(self, cursor, new_word):
        """Replaces the selected word with the suggestion."""

        # We need to re-select the word the cursor was on,
        # as the cursor itself doesn't retain the selection
        # after the menu closes.
        cursor.select(QTextCursor.SelectionType.WordUnderCursor)

        cursor.beginEditBlock()
        cursor.removeSelectedText()
        cursor.insertText(new_word)
        cursor.endEditBlock()

        # Manually trigger a re-highlight of the current block
        if hasattr(self, 'highlighter'):
            self.highlighter.rehighlightBlock(cursor.block())



    def add_to_dictionary(self, word):
        """Adds a word to the custom dictionary and re-highlights."""
        if self.spell_checker_service:
            # Clean the word before adding
            cleaned_word = word.lower().strip(".,!?;:()[]{}'\"")

            if not cleaned_word:
                return

            print(f"Adding '{cleaned_word}' to dictionary...")
            self.spell_checker_service.add_to_dictionary(cleaned_word)

            # Re-highlight the entire document to remove underlines
            # from the newly added word.

            if hasattr(self, 'highlighter'):
                self.highlighter.rehighlight()
    # --- END NEW ---

    # --- NEW: Anchor Formatting API ---
    def apply_anchor_format(self, anchor_id: int, tag_id: int, tag_name: str, comment: str, unique_doc_id: str):
        """
        Applies a special format to the current selection to mark it as an anchor.
        This now makes it a "link" with a blue background.
        """
        if not self.editor.textCursor().hasSelection():
            return

        # --- FIX for Font Reverting ---
        # We don't want the format of the selection. We want the
        # user's *default typing format*, which is stored in self.default_format
        # (and is updated by the font/size dropdowns).
        # We grab this *before* applying the new format.
        pre_anchor_typing_format = self.default_format
        # --- END FIX ---

        fmt = QTextCharFormat()

        # 1. Visual style: Standard hyperlink style
        fmt.setForeground(QColor("#0000EE"))  # Standard link blue
        fmt.setFontUnderline(True)

        # 2. Persist anchor ID in HTML as an href
        fmt.setAnchor(True)
        fmt.setAnchorHref(f"anchor:{anchor_id}")

        # 3. Store in-memory properties (for live editing)
        fmt.setProperty(AnchorIDProperty, anchor_id)
        fmt.setProperty(AnchorTagIDProperty, tag_id)
        fmt.setProperty(AnchorTagNameProperty, tag_name)
        fmt.setProperty(AnchorCommentProperty, comment)
        fmt.setProperty(AnchorUUIDProperty, unique_doc_id)

        # 4. Tooltip (This *is* saved in the HTML as a title attribute)
        tooltip = f"Tag: {tag_name}"
        if comment:
            tooltip += f"\n\nComment: {comment}"
        fmt.setToolTip(tooltip)

        # 5. Apply format
        _apply_char_format(self.editor, fmt)

        # --- FIX for Font Reverting ---
        # Move cursor to the end of the selection (unselecting it)
        cursor = self.editor.textCursor()
        cursor.setPosition(cursor.selectionEnd())
        self.editor.setTextCursor(cursor)

        # Reset the current format for *new* typing to be
        # the user's default format (TNR 16pt).
        self.editor.setCurrentCharFormat(pre_anchor_typing_format)
        # --- END FIX ---

    def remove_anchor_format(self):
        """
        Clears ONLY the anchor formatting (background, properties, tooltip, link)
        from the current selection, preserving all other formatting
        (font, size, bold, etc.).
        """
        cursor = self.editor.textCursor()
        if not cursor.hasSelection():
            return

        fmt = cursor.charFormat()

        # Clear *only* the anchor properties and link-specific styling
        fmt.clearProperty(AnchorIDProperty)
        fmt.clearProperty(AnchorTagIDProperty)
        fmt.clearProperty(AnchorTagNameProperty)
        fmt.clearProperty(AnchorCommentProperty)
        fmt.clearProperty(AnchorUUIDProperty)

        fmt.setAnchor(False)
        fmt.setAnchorHref("")
        fmt.setToolTip("")

        # Revert link styling to default, preserving other colors
        if fmt.foreground() == QBrush(QColor("#0000EE")):
            fmt.setForeground(self.default_format.foreground())

        fmt.setFontUnderline(False)
        fmt.clearBackground()

        cursor.setCharFormat(fmt)
        self.editor.setTextCursor(cursor)

    def find_and_update_anchor_format(self, anchor_id: int, tag_id: int, tag_name: str, comment: str):
        """
        Finds an anchor by its ID anywhere in the document and updates its
        format and metadata.
        """
        cursor = self.editor.textCursor()
        cursor.setPosition(0)  # Start at the beginning
        doc = self.editor.document()

        current_pos = 0
        while current_pos < doc.characterCount() - 1:
            cursor.setPosition(current_pos)
            cursor.movePosition(QTextCursor.MoveOperation.NextCharacter, QTextCursor.MoveMode.KeepAnchor, 1)
            fmt = cursor.charFormat()

            aid = self._get_anchor_id_from_format(fmt)

            if aid and aid == anchor_id:
                # Found the start of an anchor. Expand selection until property changes.
                start_pos = cursor.position() - 1
                while not cursor.atEnd():
                    cursor.movePosition(QTextCursor.MoveOperation.NextCharacter, QTextCursor.MoveMode.KeepAnchor)
                    fmt = cursor.charFormat()
                    next_aid = self._get_anchor_id_from_format(fmt)

                    if next_aid != anchor_id:
                        # We went one char too far
                        cursor.movePosition(QTextCursor.MoveOperation.PreviousCharacter,
                                            QTextCursor.MoveMode.KeepAnchor)
                        break

                # Now, 'cursor' holds the full selection of the anchor
                # Apply the new format.
                new_fmt = cursor.charFormat()  # Get format of the whole selection
                new_fmt.setProperty(AnchorTagIDProperty, tag_id)
                new_fmt.setProperty(AnchorTagNameProperty, tag_name)
                new_fmt.setProperty(AnchorCommentProperty, comment)

                new_fmt.setAnchorHref(f"anchor:{anchor_id}")  # Ensure href is correct

                tooltip = f"Tag: {tag_name}"
                if comment:
                    tooltip += f"\n\nComment: {comment}"
                new_fmt.setToolTip(tooltip)

                # Also re-apply hyperlink styles in case they were cleared
                new_fmt.setForeground(QColor("#0000EE"))
                new_fmt.setFontUnderline(True)
                new_fmt.clearBackground()  # Ensure no background

                cursor.setCharFormat(new_fmt)
                current_pos = cursor.position()
            else:
                current_pos += 1

    def find_and_remove_anchor_format(self, anchor_id):
        """
        Finds an anchor by its ID, selects it, and then calls
        remove_anchor_format() to correctly strip its formatting.
        """
        cursor = self.editor.textCursor()
        cursor.setPosition(0)
        doc = self.editor.document()

        current_pos = 0
        while current_pos < doc.characterCount() - 1:
            cursor.setPosition(current_pos)
            cursor.movePosition(QTextCursor.MoveOperation.NextCharacter, QTextCursor.MoveMode.KeepAnchor, 1)
            fmt = cursor.charFormat()
            aid = self._get_anchor_id_from_format(fmt)

            if aid and aid == anchor_id:
                # Found the start. Now find the end.
                while not cursor.atEnd():
                    cursor.movePosition(QTextCursor.MoveOperation.NextCharacter, QTextCursor.MoveMode.KeepAnchor)
                    fmt = cursor.charFormat()
                    next_aid = self._get_anchor_id_from_format(fmt)
                    if next_aid != anchor_id:
                        # We went one char too far
                        cursor.movePosition(QTextCursor.MoveOperation.PreviousCharacter,
                                            QTextCursor.MoveMode.KeepAnchor)
                        break

                # 'cursor' now has the full anchor selected
                self.editor.setTextCursor(cursor)
                self.remove_anchor_format()
                return  # Done
            else:
                current_pos += 1

    def focus_anchor_by_id(self, anchor_id: int) -> bool:
        """Selects and scrolls to the anchor with the given ID if it exists."""
        if not anchor_id or anchor_id <= 0:
            return False

        cursor = self.editor.textCursor()
        cursor.setPosition(0)
        doc = self.editor.document()

        current_pos = 0
        while current_pos < doc.characterCount() - 1:
            cursor.setPosition(current_pos)
            cursor.movePosition(QTextCursor.MoveOperation.NextCharacter, QTextCursor.MoveMode.KeepAnchor, 1)
            fmt = cursor.charFormat()
            aid = self._get_anchor_id_from_format(fmt)

            if aid and aid == anchor_id:
                anchor_cursor = QTextCursor(cursor)
                self.select_anchor_at_cursor(anchor_cursor)
                self.editor.setTextCursor(anchor_cursor)
                self.editor.ensureCursorVisible()
                self.editor.setFocus()  # <--- ADD THIS LINE
                return True

            current_pos += 1

        return False

    def _get_anchor_id_from_format(self, char_format: QTextCharFormat):
        """Helper to find anchor_id, prioritizing persistent href."""

        # 1. Try persistent href first (survives save/load)
        href = char_format.anchorHref()

        if href and href.startswith("anchor:"):
            try:
                anchor_id = int(href.split(":")[-1])  # Get last part
                return anchor_id
            except Exception as e:
                pass  # Not a valid anchor href

        # 2. Try in-memory property (for newly created anchors)
        anchor_id_qvar = char_format.property(AnchorIDProperty)
        if anchor_id_qvar is not None:
            try:
                if hasattr(anchor_id_qvar, 'toInt'):
                    val, ok = anchor_id_qvar.toInt()
                    if ok and val > 0:
                        return val
                elif anchor_id_qvar > 0:
                    return int(anchor_id_qvar)
            except Exception:
                pass  # Not a valid property

        return None

    @Slot(QPoint)
    def show_context_menu(self, pos):
        """Shows a custom context menu."""
        menu = self.editor.createStandardContextMenu()
        cursor = self.editor.cursorForPosition(pos)
        char_format = cursor.charFormat()

        anchor_id = self._get_anchor_id_from_format(char_format)

        # --- NEW: Spell Check Logic ---
        spell_menu = None
        if self.spell_checker_service and not anchor_id:  # Don't spellcheck anchors
            spell_cursor = self.editor.cursorForPosition(pos)
            spell_cursor.select(QTextCursor.SelectionType.WordUnderCursor)
            word = spell_cursor.selectedText()

            # Clean punctuation from word
            cleaned_word = word.strip(".,!?;:()[]{}'\"")


            if cleaned_word and self.spell_checker_service.is_misspelled(cleaned_word):
                suggestions = self.spell_checker_service.suggest(cleaned_word)
                spell_menu = QMenu("Spelling Suggestions")

                if suggestions:
                    for sug in suggestions:
                        # We pass a *copy* of the cursor to the lambda
                        action = QAction(sug, self)
                        action.triggered.connect(
                            lambda checked=False, c=QTextCursor(spell_cursor), w=sug: self.correct_word(c, w)
                                )
                        spell_menu.addAction(action)
                else:
                    no_sug_action = QAction("No suggestions found", self)
                    no_sug_action.setEnabled(False)
                    spell_menu.addAction(no_sug_action)

            spell_menu.addSeparator()
            add_dict_action = QAction(f"Add '{cleaned_word}' to Dictionary", self)
            add_dict_action.triggered.connect(
                lambda checked=False, w=cleaned_word: self.add_to_dictionary(w)
                    )
            spell_menu.addAction(add_dict_action)

        if spell_menu:
            menu.insertMenu(menu.actions()[0], spell_menu)
            menu.insertSeparator(menu.actions()[1])
        # --- END NEW ---

        menu.addSeparator()

        if anchor_id:
            # Clicked on an existing anchor.
            # We need to select the whole anchor to operate on it.
            self.select_anchor_at_cursor(cursor) # This also sets the editor's cursor

            edit_action = QAction("Edit Synthesis Anchor...", self)
            edit_action.triggered.connect(lambda: self.anchorEditTriggered.emit(anchor_id))
            menu.addAction(edit_action)

            delete_action = QAction("Delete Synthesis Anchor", self)
            delete_action.triggered.connect(lambda: self.anchorDeleteTriggered.emit(anchor_id))
            menu.addAction(delete_action)

        else:
            # Not on an anchor, check for selection
            anchor_action = QAction("Create Synthesis Anchor...", self)
            has_selection = self.editor.textCursor().hasSelection()
            anchor_action.setEnabled(has_selection)
            if has_selection:
                selected_text = self.editor.textCursor().selectedText()
                # Clean up text (replace line separators with spaces)
                selected_text = selected_text.replace(u'\u2029', ' ').replace('\n', ' ').strip()
                anchor_action.triggered.connect(lambda: self.anchorActionTriggered.emit(selected_text))

            menu.addAction(anchor_action)

        menu.exec(self.editor.viewport().mapToGlobal(pos))

    def select_anchor_at_cursor(self, cursor):
        """Expands the given cursor to select the entire anchor it's in."""

        def get_anchor_id(fmt):
            return self._get_anchor_id_from_format(fmt)

        anchor_id = get_anchor_id(cursor.charFormat())
        if not anchor_id:
            return

        # Move back to the start of the anchor
        while get_anchor_id(cursor.charFormat()) == anchor_id:
            if cursor.atBlockStart():
                break
            cursor.movePosition(QTextCursor.MoveOperation.PreviousCharacter, QTextCursor.MoveMode.MoveAnchor)

        # We moved one char too far (or are at the start)
        if get_anchor_id(cursor.charFormat()) != anchor_id:
            cursor.movePosition(QTextCursor.MoveOperation.NextCharacter, QTextCursor.MoveMode.MoveAnchor)

        # Move forward to the end of the anchor
        # (Manual loop since StartOfAnchor is not supported)
        start_pos = cursor.position()
        while get_anchor_id(cursor.charFormat()) == anchor_id:
            if cursor.atBlockEnd():
                break
            cursor.movePosition(QTextCursor.MoveOperation.NextCharacter, QTextCursor.MoveMode.KeepAnchor)

        # We might have moved one char too far
        if get_anchor_id(cursor.charFormat()) != anchor_id:
            cursor.movePosition(QTextCursor.MoveOperation.PreviousCharacter, QTextCursor.MoveMode.KeepAnchor)

        self.editor.setTextCursor(cursor)

    # ---- Handlers ----

    @Slot()
    def _on_text_changed(self):
        """
        When text is changed, check if the editor became empty OR
        if the cursor is in a new, empty block.
        If so, reset the current char format to our user default.
        This prevents the "backspace all text" bug AND the
        "double enter" bug shown in image_637e67.png.
        """
        cursor = self.editor.textCursor()

        # Check 1: Is the whole document empty? (The "backspace all" bug)
        if self.editor.toPlainText() == "":
            self.editor.setCurrentCharFormat(self.default_format)
            return

        # Check 2: Is the cursor's current block empty? (The "double-enter" bug)
        # An "empty" block still has a length of 1 (the newline char).
        # Its text(), however, is empty.
        current_block = cursor.block()
        if current_block.length() == 1 and current_block.text() == "":
            # We are on a new, empty line.
            # Check if the current format is *not* our default.
            if self.editor.currentCharFormat() != self.default_format:
                # It's wrong (e.g., reverted to system default). Force it back.
                self.editor.setCurrentCharFormat(self.default_format)

    @Slot()
    def _on_selection_changed(self):
        """Updates toolbar button states to reflect cursor's format."""
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
                # --- MODIFIED: Check href as well ---
                href = self.editor.currentCharFormat().anchorHref()
                if (href and href.startswith("anchor:")):
                    # --- END MODIFIED ---
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
                # --- FIX: properly remove list ---
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
                # --- END FIX ---
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

        href = c.charFormat().anchorHref()
        if href and href.startswith("anchor:"):
            QMessageBox.warning(self, "Action Not Allowed", "Cannot turn a synthesis anchor into a regular link.")
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

        href = c.charFormat().anchorHref()
        if href and href.startswith("anchor:"):
            QMessageBox.warning(self, "Action Not Allowed",
                                "Cannot unlink a synthesis anchor. Use 'Delete Synthesis Anchor' from the context menu.")
            return  # Do not allow unlink to clear anchors

        fmt = QTextCharFormat()
        fmt.setAnchor(False);
        fmt.clearForeground();
        fmt.setFontUnderline(False)
        _apply_char_format(self.editor, fmt)

    def _on_clear(self):
        c = self.editor.textCursor()
        if not c.hasSelection():
            self.editor.setCurrentCharFormat(self.default_format)
        else:
            # This new logic clears all formatting (including anchors)
            # and reverts to the default font and size.
            fmt = QTextCharFormat(self.default_format)
            c.setCharFormat(fmt)
            self.editor.setTextCursor(c)