# widgets/project_dashboard_widget_v4.py
from PySide6.QtCore import Slot
from PySide6.QtWidgets import QDialog, QMessageBox

from dialogs.add_reading_dialog import AddReadingDialog
from tabs.rich_text_editor_tab import RichTextEditorTab
from widgets.project_dashboard_widget import ProjectDashboardWidget


class ProjectDashboardWidgetV4(ProjectDashboardWidget):
    """Version 4 dashboard additions and cleanup."""

    CLASS_NOTES_FIELD = "class_notes_html"

    def _ensure_class_notes_column(self):
        """Add the Class Notes storage column to existing databases."""
        try:
            self.db.cursor.execute("PRAGMA table_info(items)")
            columns = [row["name"] for row in self.db.cursor.fetchall()]
            if self.CLASS_NOTES_FIELD not in columns:
                self.db.cursor.execute(
                    f"ALTER TABLE items ADD COLUMN {self.CLASS_NOTES_FIELD} TEXT"
                )
                self.db.conn.commit()
                print("Added items.class_notes_html for Class Notes.")
        except Exception as e:
            print(f"Warning: Could not ensure Class Notes column. {e}")

    def _install_class_notes_tab(self):
        """Create the Class Notes tab with the standard rich text editor."""
        self.class_notes_tab = RichTextEditorTab(
            "Class Notes",
            spell_checker_service=self.spell_checker_service,
        )
        self.class_notes_tab.setPlaceholderText("Add class notes here…")

        self.class_notes_tab.linkPdfNodeTriggered.connect(
            lambda: self._on_link_pdf_node_triggered(self.class_notes_tab)
        )
        self.class_notes_tab.editor.smartAnchorClicked.connect(self._on_editor_link_clicked)

        # Put it immediately after the dashboard so it is easy to find.
        self.top_tab_widget.insertTab(1, self.class_notes_tab, "Class Notes")

    def load_project(self, project_details):
        self._ensure_class_notes_column()
        self.class_notes_tab = None
        super().load_project(project_details)
        self._install_class_notes_tab()

    def load_all_editor_content(self):
        super().load_all_editor_content()
        if not getattr(self, "class_notes_tab", None) or self.project_id == -1:
            return

        details = self.db.get_item_details(self.project_id) or {}
        self.class_notes_tab.set_html(details.get(self.CLASS_NOTES_FIELD, ""))

    @Slot()
    def save_all_editors(self):
        super().save_all_editors()
        if not getattr(self, "class_notes_tab", None) or self.project_id == -1:
            return

        def save_class_notes(html):
            if html is not None:
                self.db.update_project_text_field(self.project_id, self.CLASS_NOTES_FIELD, html)

        self.class_notes_tab.get_html(save_class_notes)

    @Slot()
    def add_reading(self):
        if self.project_id == -1:
            return

        dialog = AddReadingDialog(self.db, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_id = self.db.add_reading(
                self.project_id,
                dialog.title,
                dialog.author,
                dialog.nickname,
                dialog.published,
                dialog.pages,
                dialog.level,
                dialog.classification,
            )
            self.load_readings()

            if self.annotated_bib_tab:
                self.annotated_bib_tab.load_sources()

            self.top_tab_widget.blockSignals(True)
            try:
                reading_row = self.db.get_reading_details(new_id)
                if reading_row:
                    new_tab = self._create_and_add_reading_tab(reading_row, set_current=True)
                    new_tab.load_data()
                    self.top_tab_widget.setCurrentWidget(self.readings_container)
                else:
                    print(f"Error: Could not find new reading with id {new_id}")
            finally:
                self.top_tab_widget.blockSignals(False)

    def edit_reading(self):
        item = self.readings_tree.currentItem()
        if not item:
            return

        reading_id = item.data(0, self._qt_user_role())
        current_data = self.db.get_reading_details(reading_id)
        if not current_data:
            return

        dialog = AddReadingDialog(self.db, current_data=dict(current_data), parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            details = {
                "title": dialog.title,
                "author": dialog.author,
                "nickname": dialog.nickname,
                "published": dialog.published,
                "pages": dialog.pages,
                "level": dialog.level,
                "classification": dialog.classification,
            }

            self.db.update_reading_details(reading_id, details)
            self.load_readings()

            if reading_id in self.reading_tabs:
                tab = self.reading_tabs[reading_id]
                tab.load_data()
                self._handle_reading_title_change(reading_id, tab)

            if self.annotated_bib_tab:
                self.annotated_bib_tab.load_sources()

    @staticmethod
    def _qt_user_role():
        from PySide6.QtCore import Qt
        return Qt.ItemDataRole.UserRole
