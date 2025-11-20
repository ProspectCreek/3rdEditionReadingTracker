# prospectcreek/3rdeditionreadingtracker/database_helpers/settings_mixin.py
import sqlite3


class SettingsMixin:
    """
    Mixin for managing global user settings (like Zotero credentials).
    """

    def get_user_settings(self):
        """Retrieves the single row of user settings."""
        try:
            self.cursor.execute("SELECT * FROM user_settings WHERE id = 1")
            return self._rowdict(self.cursor.fetchone())
        except Exception as e:
            print(f"Error fetching user settings: {e}")
            return None

    def save_user_settings(self, library_id, api_key, library_type='user'):
        """Saves or updates the Zotero credentials."""
        try:
            self.cursor.execute("""
                INSERT INTO user_settings (id, zotero_library_id, zotero_api_key, zotero_library_type)
                VALUES (1, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                zotero_library_id = excluded.zotero_library_id,
                zotero_api_key = excluded.zotero_api_key,
                zotero_library_type = excluded.zotero_library_type
            """, (library_id, api_key, library_type))
            self.conn.commit()
        except Exception as e:
            print(f"Error saving user settings: {e}")
            self.conn.rollback()

    def save_citation_style(self, style):
        """Saves the selected citation style preference."""
        try:
            # Ensure the row exists first
            self.cursor.execute("INSERT OR IGNORE INTO user_settings (id) VALUES (1)")

            self.cursor.execute("""
                UPDATE user_settings SET citation_style = ? WHERE id = 1
            """, (style,))
            self.conn.commit()
        except Exception as e:
            print(f"Error saving citation style: {e}")
            self.conn.rollback()