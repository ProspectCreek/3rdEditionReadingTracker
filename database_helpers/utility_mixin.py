import shutil

class UtilityMixin:
    # ---------------------------- utility ----------------------------

    def backup_database(self, dest_path):
        """Create a copy of the database file at dest_path."""
        self.conn.commit()
        src = self.conn.execute("PRAGMA database_list").fetchone()[2]
        shutil.copyfile(src, dest_path)

    def __del__(self):
        try:
            self.conn.close()
        except Exception:
            pass