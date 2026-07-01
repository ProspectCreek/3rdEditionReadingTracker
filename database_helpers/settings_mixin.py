# prospectcreek/3rdeditionreadingtracker/database_helpers/settings_mixin.py


class SettingsMixin:
    """Mixin for managing simple application-level settings."""

    def get_user_settings(self):
        """Retrieves the single row of application settings."""
        try:
            self.cursor.execute("SELECT * FROM user_settings WHERE id = 1")
            return self._rowdict(self.cursor.fetchone())
        except Exception as e:
            print(f"Error fetching user settings: {e}")
            return None

    def save_user_settings(self, **settings):
        """Saves supported application settings."""
        if not settings:
            return

        allowed = {"citation_style", "app_version"}
        clean = {k: v for k, v in settings.items() if k in allowed}
        if not clean:
            return

        try:
            self.cursor.execute("INSERT OR IGNORE INTO user_settings (id) VALUES (1)")
            set_clause = ", ".join([f"{key} = ?" for key in clean])
            values = list(clean.values())
            values.append(1)
            self.cursor.execute(
                f"UPDATE user_settings SET {set_clause} WHERE id = ?",
                tuple(values),
            )
            self.conn.commit()
        except Exception as e:
            print(f"Error saving user settings: {e}")
            self.conn.rollback()

    def save_citation_style(self, style):
        """Saves the selected citation style preference."""
        self.save_user_settings(citation_style=style)
