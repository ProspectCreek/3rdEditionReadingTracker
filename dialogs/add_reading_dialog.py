import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QDialogButtonBox, QPushButton, QHBoxLayout, QMessageBox,
    QListWidget, QListWidgetItem, QInputDialog, QLabel, QWidget,
    QComboBox
)
from PySide6.QtCore import Qt

# Import PyZotero
try:
    from pyzotero import zotero
except ImportError:
    zotero = None


class ZoteroSearchDialog(QDialog):
    """
    Dialog to search Zotero library and select an item.
    """

    def __init__(self, zot_instance, parent=None):
        super().__init__(parent)
        self.zot = zot_instance
        self.selected_item_data = None
        self.setWindowTitle("Search Zotero")
        self.setMinimumSize(600, 400)

        layout = QVBoxLayout(self)

        # Search Bar
        search_layout = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search title, author, year...")
        self.search_edit.returnPressed.connect(self._perform_search)

        btn_search = QPushButton("Search")
        btn_search.clicked.connect(self._perform_search)

        search_layout.addWidget(self.search_edit)
        search_layout.addWidget(btn_search)
        layout.addLayout(search_layout)

        # Results List
        self.results_list = QListWidget()
        self.results_list.itemDoubleClicked.connect(self.accept)
        layout.addWidget(self.results_list)

        # Buttons
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

        self.items_map = {}  # Store full item data keyed by list row

    def _perform_search(self):
        query = self.search_edit.text().strip()
        if not query: return

        self.results_list.clear()
        self.items_map = {}
        self.results_list.addItem("Searching...")

        # Process events to show "Searching..." immediately
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()

        try:
            # Limit to 20 results for speed
            items = self.zot.items(q=query, limit=20)

            self.results_list.clear()
            if not items:
                self.results_list.addItem("No results found.")
                return

            for i, item in enumerate(items):
                data = item['data']
                title = data.get('title', 'No Title')

                # --- UPDATED AUTHOR PARSING ---
                creators = data.get('creators', [])
                authors_display = []  # For list view (shorter)
                authors_full = []  # For population (Last, First)

                for c in creators:
                    if 'lastName' in c and 'firstName' in c:
                        authors_display.append(c['lastName'])
                        authors_full.append(f"{c['lastName']}, {c['firstName']}")
                    elif 'lastName' in c:
                        authors_display.append(c['lastName'])
                        authors_full.append(c['lastName'])
                    elif 'name' in c:  # For organizations
                        authors_display.append(c['name'])
                        authors_full.append(c['name'])

                author_str_display = ", ".join(authors_display)
                author_str_full = "; ".join(authors_full)  # Semicolon for multiple full authors

                # Format Date
                date = data.get('date', '')

                display_text = f"{title} | {author_str_display} | {date}"

                list_item = QListWidgetItem(display_text)
                list_item.setData(Qt.ItemDataRole.UserRole, i)
                self.results_list.addItem(list_item)

                # Store relevant data map
                self.items_map[i] = {
                    'title': title,
                    'author': author_str_full,  # Use the full "Last, First" version
                    'date': date,
                    'pages': data.get('pages', ''),
                    'key': data.get('key')
                }

        except Exception as e:
            self.results_list.clear()
            QMessageBox.critical(self, "Zotero Error", f"Search failed: {e}")

    def accept(self):
        current_item = self.results_list.currentItem()
        if current_item:
            idx = current_item.data(Qt.ItemDataRole.UserRole)
            if idx is not None and idx in self.items_map:
                self.selected_item_data = self.items_map[idx]
                super().accept()
        else:
            if self.results_list.count() > 0 and self.results_list.item(0).text() != "No results found.":
                QMessageBox.warning(self, "Selection", "Please select an item from the list.")
            else:
                super().reject()


class AddReadingDialog(QDialog):
    """
    Dialog to add a new reading or edit an existing one.
    """

    def __init__(self, db_manager, current_data=None, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.current_data = current_data

        if current_data:
            self.setWindowTitle("Edit Reading")
        else:
            self.setWindowTitle("Add New Reading")

        self.setMinimumWidth(600)

        # Results
        self.title = ""
        self.author = ""
        self.nickname = ""
        self.published = ""
        self.pages = ""
        self.level = ""
        self.classification = ""
        self.zotero_key = None

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        # --- Title Row ---
        title_widget = QWidget()
        title_layout = QHBoxLayout(title_widget)
        title_layout.setContentsMargins(0, 0, 0, 0)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("e.g. How to Read a Book")

        self.btn_zotero = QPushButton("Search Zotero")
        self.btn_zotero_config = QPushButton("⚙")
        self.btn_zotero_config.setFixedWidth(30)
        self.btn_zotero_config.setToolTip("Configure Zotero ID/Key")

        if zotero is None:
            self.btn_zotero.setEnabled(False)
            self.btn_zotero.setToolTip("PyZotero library not installed.")
            self.btn_zotero_config.setEnabled(False)
        else:
            self.btn_zotero.clicked.connect(self._open_zotero_search)
            self.btn_zotero_config.clicked.connect(self._configure_zotero_credentials)

        title_layout.addWidget(self.title_edit)
        title_layout.addWidget(self.btn_zotero)
        title_layout.addWidget(self.btn_zotero_config)

        form_layout.addRow("Title:", title_widget)

        # --- Other Fields ---
        self.author_edit = QLineEdit()
        self.author_edit.setPlaceholderText("Lastname, Firstname")
        form_layout.addRow("Author:", self.author_edit)

        self.published_edit = QLineEdit()
        self.published_edit.setPlaceholderText("YYYY or YYYY-MM-DD")
        form_layout.addRow("Published Date:", self.published_edit)

        self.nickname_edit = QLineEdit()
        self.nickname_edit.setPlaceholderText("e.g. Adler 1972")
        form_layout.addRow("Citation Nickname:", self.nickname_edit)

        self.pages_edit = QLineEdit()
        self.pages_edit.setPlaceholderText("Total pages or range")
        form_layout.addRow("Pages:", self.pages_edit)

        self.level_combo = QComboBox()
        self.level_combo.addItems([
            "Elementary (Entertainment)",
            "Inspectional (Information)",
            "Analytical (Understanding)",
            "Syntopic (Mastery)"
        ])
        form_layout.addRow("Level:", self.level_combo)

        self.classification_edit = QLineEdit()
        self.classification_edit.setPlaceholderText("e.g. History, Science, Fiction")
        form_layout.addRow("Classification:", self.classification_edit)

        layout.addLayout(form_layout)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        # --- Pre-populate if editing ---
        if self.current_data:
            self.title_edit.setText(self.current_data.get('title', ''))
            self.author_edit.setText(self.current_data.get('author', ''))
            self.nickname_edit.setText(self.current_data.get('nickname', ''))
            self.published_edit.setText(self.current_data.get('published', ''))
            self.pages_edit.setText(self.current_data.get('pages', ''))
            self.classification_edit.setText(self.current_data.get('classification', ''))

            level = self.current_data.get('level', '')
            if level:
                self.level_combo.setCurrentText(level)

            self.zotero_key = self.current_data.get('zotero_item_key')

        self.title_edit.setFocus()

    def _configure_zotero_credentials(self):
        self._get_zotero_creds(force_prompt=True)

    def _get_zotero_creds(self, force_prompt=False):
        """Fetches credentials from DB or prompts user."""
        settings = self.db.get_user_settings()

        lib_id = None
        api_key = None
        lib_type = 'user'

        if settings and not force_prompt:
            lib_id = settings.get('zotero_library_id')
            api_key = settings.get('zotero_api_key')
            lib_type = settings.get('zotero_library_type', 'user')

        if force_prompt or not lib_id or not api_key:
            if not force_prompt:
                reply = QMessageBox.question(
                    self, "Zotero Setup",
                    "Zotero Library ID and API Key are not set.\nDo you want to enter them now?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.No:
                    return None, None, None

            current_id = lib_id if lib_id else ""
            lib_id, ok1 = QInputDialog.getText(self, "Zotero Config", "Enter Library ID (Numeric):", text=current_id)
            if not ok1 or not lib_id: return None, None, None

            current_key = api_key if api_key else ""
            api_key, ok2 = QInputDialog.getText(self, "Zotero Config", "Enter API Key:", text=current_key)
            if not ok2 or not api_key: return None, None, None

            types = ["User (Personal Library)", "Group (Shared Library)"]
            current_index = 0 if lib_type == 'user' else 1
            item, ok3 = QInputDialog.getItem(self, "Zotero Config", "Library Type:", types, current_index, False)
            if ok3 and item:
                lib_type = 'user' if item.startswith("User") else 'group'
                self.db.save_user_settings(lib_id, api_key, lib_type)
                return lib_id, api_key, lib_type

            return None, None, None

        return lib_id, api_key, lib_type

    def _open_zotero_search(self):
        lib_id, api_key, lib_type = self._get_zotero_creds()
        if not lib_id or not api_key:
            return

        try:
            zot = zotero.Zotero(lib_id, lib_type, api_key)

            search_dlg = ZoteroSearchDialog(zot, self)
            if search_dlg.exec() == QDialog.DialogCode.Accepted:
                data = search_dlg.selected_item_data
                if data:
                    self.title_edit.setText(data['title'])
                    self.author_edit.setText(data['author'])
                    self.published_edit.setText(data['date'])
                    self.pages_edit.setText(data['pages'])

                    # Auto-generate nickname (Lastname Year)
                    # Handle "Last, First" format for nickname generation
                    author_part = data['author'].split(';')[0]  # Take first author
                    if ',' in author_part:
                        lastname = author_part.split(',')[0].strip()
                    else:
                        lastname = author_part.strip()  # Fallback

                    year = data['date'][:4] if data['date'] else ""
                    self.nickname_edit.setText(f"{lastname} {year}")

                    self.zotero_key = data['key']

        except Exception as e:
            QMessageBox.critical(self, "Connection Error",
                                 f"Could not connect to Zotero: {e}\n\nCheck your Library ID, Key, and Library Type.")

    def accept(self):
        self.title = self.title_edit.text().strip()
        self.author = self.author_edit.text().strip()
        self.nickname = self.nickname_edit.text().strip()
        self.published = self.published_edit.text().strip()
        self.pages = self.pages_edit.text().strip()
        self.level = self.level_combo.currentText()
        self.classification = self.classification_edit.text().strip()
        super().accept()