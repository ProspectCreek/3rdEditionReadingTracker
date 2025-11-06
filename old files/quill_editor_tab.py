# tabs/quill_editor_tab.py

import os
import warnings
from PySide6.QtCore import Qt, QUrl
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QInputDialog, QMessageBox, QSizePolicy
)
from PySide6.QtWebEngineWidgets import QWebEngineView


def _auto_project_root_dir():
    """
    Try to find the project root that contains editor.html and web_resources/.
    Strategy:
      1) Start at this file's directory, walk up a few levels.
      2) Fallback to CWD.
    """
    here = os.path.abspath(os.path.dirname(__file__))
    candidates = [
        here,
        os.path.abspath(os.path.join(here, "..")),
        os.path.abspath(os.path.join(here, "..", "..")),
        os.getcwd(),
    ]
    for base in candidates:
        editor = os.path.join(base, "editor.html")
        wres = os.path.join(base, "web_resources")
        if os.path.isfile(editor) and os.path.isdir(wres):
            return base
    # Last resort: return parent of this file
    return os.path.abspath(os.path.join(here, ".."))


class QuillEditorTab(QWidget):
    """
    Qt-side toolbar + QWebEngineView hosting editor.html (Quill inside).
    SAFE CONSTRUCTOR: works with or without args to prevent TypeError crashes.

    Args (optional):
        editor_title (str): Label shown on the Qt toolbar (e.g., "Project Purpose").
        project_root_dir (str): Folder containing editor.html and web_resources/.
    """
    def __init__(self, editor_title: str = None, project_root_dir: str = None, parent=None):
        super().__init__(parent)

        # --- Make args optional & robust ---
        if editor_title is None:
            editor_title = "Editor"
            warnings.warn("QuillEditorTab: 'editor_title' was not provided; defaulting to 'Editor'.", RuntimeWarning)

        if project_root_dir is None:
            project_root_dir = _auto_project_root_dir()
            warnings.warn(
                f"QuillEditorTab: 'project_root_dir' not provided; auto-detected '{project_root_dir}'.",
                RuntimeWarning
            )

        self.editor_title = editor_title
        self.project_root_dir = project_root_dir

        # ---------- Layout ----------
        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        # ---------- Qt Toolbar (FULL feature set) ----------
        bar = QWidget(self)
        bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        h = QHBoxLayout(bar)
        h.setContentsMargins(8, 6, 8, 6)
        h.setSpacing(8)

        h.addWidget(QLabel(f"{self.editor_title} — Format:"))

        # Font family (tokens must match editor.html whitelist)
        self.fontCombo = QComboBox(bar); self.fontCombo.setEditable(False)
        fonts = [
            ("", "Sans Serif"),
            ("serif", "Serif"),
            ("monospace", "Monospace"),
            ("arial", "Arial"),
            ("georgia", "Georgia"),
            ("times-new-roman", "Times New Roman"),
            ("courier-new", "Courier New"),
            ("tahoma", "Tahoma"),
            ("verdana", "Verdana"),
            ("segoe-ui", "Segoe UI"),
        ]
        for token, label in fonts:
            self.fontCombo.addItem(label, userData=token)

        # Size
        self.sizeCombo = QComboBox(bar); self.sizeCombo.setEditable(False)
        for sz in ["", "10px","12px","14px","16px","18px","20px","24px","32px"]:
            self.sizeCombo.addItem("Normal" if sz == "" else sz, userData=sz)
        idx_14 = self.sizeCombo.findData("14px")
        if idx_14 != -1:
            self.sizeCombo.setCurrentIndex(idx_14)

        # Header
        self.headerCombo = QComboBox(bar); self.headerCombo.setEditable(False)
        self.headerCombo.addItem("Paragraph", userData="")
        self.headerCombo.addItem("H1", userData="1")
        self.headerCombo.addItem("H2", userData="2")
        self.headerCombo.addItem("H3", userData="3")

        # Inline style buttons
        self.boldBtn = QPushButton("B"); self.boldBtn.setCheckable(True); self.boldBtn.setToolTip("Bold")
        self.italicBtn = QPushButton("I"); self.italicBtn.setCheckable(True); self.italicBtn.setToolTip("Italic")
        self.underlineBtn = QPushButton("U"); self.underlineBtn.setCheckable(True); self.underlineBtn.setToolTip("Underline")
        self.strikeBtn = QPushButton("S"); self.strikeBtn.setCheckable(True); self.strikeBtn.setToolTip("Strikethrough")

        # Colors (simple presets via comboboxes)
        self.colorCombo = QComboBox(bar)
        self.bgCombo = QComboBox(bar)
        preset_colors = [
            ("", "Text: Default"),
            ("#000000", "Black"),
            ("#ff0000", "Red"),
            ("#00aa00", "Green"),
            ("#0000ff", "Blue"),
            ("#ffaa00", "Orange"),
            ("#aa00ff", "Purple"),
            ("#808080", "Gray"),
        ]
        for val, label in preset_colors:
            self.colorCombo.addItem(label, userData=val)
        preset_bgs = [
            ("", "Background: Default"),
            ("#ffff00", "Yellow"),
            ("#ffcccc", "Light Red"),
            ("#ccffcc", "Light Green"),
            ("#ccccff", "Light Blue"),
            ("#fff2cc", "Light Orange"),
            ("#f3e5f5", "Lavender"),
        ]
        for val, label in preset_bgs:
            self.bgCombo.addItem(label, userData=val)

        # Lists
        self.olBtn = QPushButton("1·"); self.olBtn.setToolTip("Ordered list")
        self.ulBtn = QPushButton("•");  self.ulBtn.setToolTip("Bullet list")

        # Indent
        self.outdentBtn = QPushButton("⟵"); self.outdentBtn.setToolTip("Outdent")
        self.indentBtn = QPushButton("⟶");  self.indentBtn.setToolTip("Indent")

        # Align
        self.alignCombo = QComboBox(bar); self.alignCombo.setEditable(False)
        for val, label in [("","Left"), ("center","Center"), ("right","Right"), ("justify","Justify")]:
            self.alignCombo.addItem(label, userData=val)

        # Links & Embeds
        self.linkBtn = QPushButton("Link…")
        self.unlinkBtn = QPushButton("Unlink")
        self.imageBtn = QPushButton("Image URL…")
        self.videoBtn = QPushButton("Video URL…")

        # Clean / Undo / Redo
        self.cleanBtn = QPushButton("Clear")
        self.undoBtn = QPushButton("Undo")
        self.redoBtn = QPushButton("Redo")

        # Add controls to toolbar row
        h.addWidget(QLabel("Font:")); h.addWidget(self.fontCombo)
        h.addWidget(QLabel("Size:")); h.addWidget(self.sizeCombo)
        h.addWidget(QLabel("Header:")); h.addWidget(self.headerCombo)
        h.addWidget(self.boldBtn); h.addWidget(self.italicBtn); h.addWidget(self.underlineBtn); h.addWidget(self.strikeBtn)
        h.addWidget(self.colorCombo); h.addWidget(self.bgCombo)
        h.addWidget(self.olBtn); h.addWidget(self.ulBtn)
        h.addWidget(self.outdentBtn); h.addWidget(self.indentBtn)
        h.addWidget(QLabel("Align:")); h.addWidget(self.alignCombo)
        h.addWidget(self.linkBtn); h.addWidget(self.unlinkBtn); h.addWidget(self.imageBtn); h.addWidget(self.videoBtn)
        h.addWidget(self.cleanBtn); h.addWidget(self.undoBtn); h.addWidget(self.redoBtn)
        h.addStretch(1)
        # Add toolbar to main layout
        main.addWidget(bar)

        # ---------- WebView ----------
        self.webview = QWebEngineView(self)
        self.webview.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        main.addWidget(self.webview, 1)

        editor_path = os.path.join(self.project_root_dir, "editor.html")
        self.webview.load(QUrl.fromLocalFile(os.path.abspath(editor_path)))

        # ---------- Wire signals ----------
        self.fontCombo.currentIndexChanged.connect(self._on_font)
        self.sizeCombo.currentIndexChanged.connect(self._on_size)
        self.headerCombo.currentIndexChanged.connect(self._on_header)

        self.boldBtn.clicked.connect(lambda on: self._apply_bool('bold', on))
        self.italicBtn.clicked.connect(lambda on: self._apply_bool('italic', on))
        self.underlineBtn.clicked.connect(lambda on: self._apply_bool('underline', on))
        self.strikeBtn.clicked.connect(lambda on: self._apply_bool('strike', on))

        self.colorCombo.currentIndexChanged.connect(self._on_color)
        self.bgCombo.currentIndexChanged.connect(self._on_background)

        self.olBtn.clicked.connect(lambda: self._run_js("window.RT_setList('ordered')"))
        self.ulBtn.clicked.connect(lambda: self._run_js("window.RT_setList('bullet')"))

        self.outdentBtn.clicked.connect(lambda: self._run_js("window.RT_indent(-1)"))
        self.indentBtn.clicked.connect(lambda: self._run_js("window.RT_indent(1)"))

        self.alignCombo.currentIndexChanged.connect(self._on_align)

        self.linkBtn.clicked.connect(self._on_link)
        self.unlinkBtn.clicked.connect(lambda: self._run_js("window.RT_setLink('')"))
        self.imageBtn.clicked.connect(lambda: self._prompt_and_embed('image'))
        self.videoBtn.clicked.connect(lambda: self._prompt_and_embed('video'))

        self.cleanBtn.clicked.connect(lambda: self._run_js("window.RT_clean()"))
        self.undoBtn.clicked.connect(lambda: self._run_js("window.RT_undo()"))
        self.redoBtn.clicked.connect(lambda: self._run_js("window.RT_redo()"))

    # ---------- Public API (used by dashboard) ----------
    def set_html(self, html: str):
        js = f"window.setEditorContent({self._js_quote(html)})"
        self._run_js(js)

    def get_html(self, callback):
        self.webview.page().runJavaScript("window.getEditorContent()", callback)

    def focus_editor(self):
        self._run_js("window.focusEditor()")

    # ---------- Toolbar handlers ----------
    def _on_font(self, idx: int):
        token = self.fontCombo.itemData(idx)
        if token is None:
            return
        self._run_js(f"window.RT_applyFormat('font', {self._js_quote(token)})")

    def _on_size(self, idx: int):
        sz = self.sizeCombo.itemData(idx)
        if sz is None:
            return
        self._run_js(f"window.RT_applyFormat('size', {self._js_quote(sz)})")

    def _on_header(self, idx: int):
        val = self.headerCombo.itemData(idx)
        val_js = "''" if (val is None or val == "") else self._js_quote(val)
        self._run_js(f"window.RT_setHeader({val_js})")

    def _apply_bool(self, name: str, on: bool):
        val = "true" if on else "false"
        self._run_js(f"window.RT_applyFormat('{name}', {val})")

    def _on_color(self, idx: int):
        val = self.colorCombo.itemData(idx)
        if val is None:
            return
        self._run_js(f"window.RT_applyFormat('color', {self._js_quote(val)})")

    def _on_background(self, idx: int):
        val = self.bgCombo.itemData(idx)
        if val is None:
            return
        self._run_js(f"window.RT_applyFormat('background', {self._js_quote(val)})")

    def _on_align(self, idx: int):
        val = self.alignCombo.itemData(idx)
        val_js = "''" if (val is None) else self._js_quote(val)
        self._run_js(f"window.RT_setAlign({val_js})")

    def _on_link(self):
        url, ok = QInputDialog.getText(self, "Insert Link", "URL:")
        if not ok:
            return
        url = url.strip()
        if url == "":
            QMessageBox.warning(self, "Invalid URL", "Please enter a URL or press Cancel.")
            return
        self._run_js(f"window.RT_setLink({self._js_quote(url)})")

    def _prompt_and_embed(self, kind: str):
        label = "Image URL" if kind == 'image' else "Video URL"
        url, ok = QInputDialog.getText(self, f"Insert {label}", f"{label}:")
        if not ok:
            return
        url = url.strip()
        if url == "":
            return
        if kind == 'image':
            self._run_js(f"window.RT_insertImage({self._js_quote(url)})")
        else:
            self._run_js(f"window.RT_insertVideo({self._js_quote(url)})")

    # ---------- Utilities ----------
    def _run_js(self, script: str):
        self.webview.page().runJavaScript(script)

    @staticmethod
    def _js_quote(s: str) -> str:
        if s is None:
            return "null"
        s = s.replace("\\", "\\\\").replace("\n", "\\n").replace("\r", "\\r")
        s = s.replace("'", "\\'").replace("\"", "\\\"")
        return f"'{s}'"
