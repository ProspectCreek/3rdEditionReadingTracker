MODERN_LIGHT_STYLESHEET = """
/* General Window & Background */
QMainWindow, QDialog { background-color: #F9FAFB; color: #374151; }
QWidget { background-color: #F9FAFB; color: #374151; font-family: "Segoe UI", "Helvetica Neue", sans-serif; font-size: 14px; }

/* Text Areas */
QLabel { color: #374151; background: transparent; }
QLineEdit, QTextEdit, QPlainTextEdit, QTextBrowser {
    background-color: #FFFFFF; border: 1px solid #D1D5DB; border-radius: 6px; padding: 6px; color: #111827;
    selection-background-color: #BFDBFE; selection-color: #111827;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus { border: 1px solid #2563EB; }

/* --- COMBO BOXES --- */
QComboBox {
    background-color: #FFFFFF;
    border: 1px solid #D1D5DB;
    border-radius: 6px;
    padding: 5px;
    color: #111827;
}
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 20px;
    border-left-width: 0px;
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
}
QComboBox::down-arrow {
    image: none;
    border-left: 2px solid #6B7280;
    border-bottom: 2px solid #6B7280;
    width: 6px;
    height: 6px;
    margin-right: 8px;
    transform: rotate(-45deg); /* Crude arrow using borders if no icon available, or rely on default */
}

/* --- FIX FOR GRID WIDGETS (Editors & Combos) --- */
/* Reset style for widgets inside tables to prevent clipping.
   We strip borders and padding so they fill the cell completely.
*/
QTableWidget QLineEdit {
    border: none;
    border-radius: 0;
    padding: 0;
    margin: 0;
    background-color: transparent;
    color: #111827;
}

QTableWidget QComboBox {
    border: none;
    border-radius: 0;
    /* Zero vertical padding is crucial to prevent text cutoff */
    padding: 0px 4px; 
    margin: 0;
    /* FIX: Must be opaque WHITE to cover the underlying item text, otherwise it looks garbled */
    background-color: #FFFFFF; 
}
QTableWidget QComboBox::drop-down {
    border: none;
    width: 20px;
    background-color: transparent;
}

/* Lists & Trees */
QListWidget, QTreeWidget, QTableWidget {
    background-color: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 6px; outline: none;
}

/* FIX: Split ListWidget and TableWidget item styles. 
   We set TableWidget items to transparent background so our custom Delegate 
   can paint the user-defined color underneath. */
QListWidget::item { padding: 6px; border-bottom: 1px solid #F3F4F6; }

QTableWidget::item { 
    padding: 6px; 
    border-bottom: 1px solid #F3F4F6; 
    background-color: transparent; 
}

QListWidget::item:selected, QTableWidget::item:selected {
    background-color: #E5F3FF; color: #000000; border: none;
}
QHeaderView::section { background-color: #F3F4F6; padding: 4px; border: none; font-weight: bold; color: #4B5563; }

/* Buttons */
QPushButton {
    background-color: #FFFFFF; border: 1px solid #D1D5DB; border-radius: 6px; padding: 6px 12px; color: #374151; font-weight: 600;
}
QPushButton:hover { background-color: #F3F4F6; border-color: #9CA3AF; }
QPushButton:pressed { background-color: #E5E7EB; }

/* Splitter */
QSplitter::handle { background-color: #E5E7EB; }

/* Group Box */
QGroupBox { border: 1px solid #E5E7EB; border-radius: 6px; margin-top: 1.5em; padding: 10px; }
QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 3px; color: #374151; font-weight: bold; }
"""