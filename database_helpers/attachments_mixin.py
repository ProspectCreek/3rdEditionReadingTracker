class AttachmentsMixin:
    # ----------------------- reading attachments -----------------------

    def get_attachments(self, reading_id):
        """Get all attachments for a specific reading."""
        self.cursor.execute("""
            SELECT * FROM reading_attachments
            WHERE reading_id = ?
            ORDER BY display_order, id
        """, (reading_id,))
        return self._map_rows(self.cursor.fetchall())

    def get_attachment_details(self, attachment_id):
        """Get the details for a single attachment."""
        self.cursor.execute("SELECT * FROM reading_attachments WHERE id = ?", (attachment_id,))
        return self._rowdict(self.cursor.fetchone())

    def _next_attachment_order(self, reading_id):
        self.cursor.execute(
            "SELECT COALESCE(MAX(display_order), -1) FROM reading_attachments WHERE reading_id = ?",
            (reading_id,)
        )
        return (self.cursor.fetchone()[0] or -1) + 1

    def add_attachment(self, reading_id, display_name, file_path):
        """Adds a new attachment record."""
        new_order = self._next_attachment_order(reading_id)
        self.cursor.execute("""
            INSERT INTO reading_attachments (reading_id, display_name, file_path, display_order)
            VALUES (?, ?, ?, ?)
        """, (reading_id, display_name, file_path, new_order))
        self.conn.commit()
        return self.cursor.lastrowid

    def rename_attachment(self, attachment_id, new_display_name):
        """Updates the display name of an attachment."""
        self.cursor.execute(
            "UPDATE reading_attachments SET display_name = ? WHERE id = ?",
            (new_display_name, attachment_id)
        )
        self.conn.commit()

    def delete_attachment(self, attachment_id):
        """Deletes an attachment record from the database."""
        self.cursor.execute("DELETE FROM reading_attachments WHERE id = ?", (attachment_id,))
        self.conn.commit()

    def update_attachment_order(self, ordered_ids):
        """Reorders attachments based on a list of IDs."""
        for order, att_id in enumerate(ordered_ids):
            self.cursor.execute(
                "UPDATE reading_attachments SET display_order = ? WHERE id = ?",
                (order, att_id)
            )
        self.conn.commit()