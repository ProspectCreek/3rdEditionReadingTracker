class OutlineMixin:
    # ----------------------- reading outline -----------------------

    def get_reading_outline(self, reading_id, parent_id=None):
        """Gets outline items, in order."""
        if parent_id is None:
            self.cursor.execute("""
                SELECT * FROM reading_outline
                WHERE reading_id = ? AND parent_id IS NULL
                ORDER BY display_order, id
            """, (reading_id,))
        else:
            self.cursor.execute("""
                SELECT * FROM reading_outline
                WHERE reading_id = ? AND parent_id = ?
                ORDER BY display_order, id
            """, (reading_id, parent_id))
        return self._map_rows(self.cursor.fetchall())

    def get_all_outline_items(self, reading_id):
        """Gets all outline items for a reading, ordered by display_order."""
        self.cursor.execute("""
            SELECT * FROM reading_outline
            WHERE reading_id = ?
            ORDER BY display_order, id
        """, (reading_id,))
        return self._map_rows(self.cursor.fetchall())

    def add_outline_section(self, reading_id, title, parent_id=None):
        """Adds an outline section, calculating its display order."""
        if parent_id is None:
            self.cursor.execute("""
                SELECT COALESCE(MAX(display_order), -1) FROM reading_outline
                WHERE reading_id = ? AND parent_id IS NULL
            """, (reading_id,))
        else:
            self.cursor.execute("""
                SELECT COALESCE(MAX(display_order), -1) FROM reading_outline
                WHERE reading_id = ? AND parent_id = ?
            """, (reading_id, parent_id))
        new_order = (self.cursor.fetchone()[0] or -1) + 1

        self.cursor.execute("""
            INSERT INTO reading_outline (reading_id, parent_id, section_title, notes_html, display_order)
            VALUES (?, ?, ?, ?, ?)
        """, (reading_id, parent_id, title, "", new_order))
        self.conn.commit()

    def update_outline_section_title(self, section_id, new_title):
        self.cursor.execute("UPDATE reading_outline SET section_title = ? WHERE id = ?", (new_title, section_id))
        self.conn.commit()

    def delete_outline_section(self, section_id):
        self.cursor.execute("DELETE FROM reading_outline WHERE id = ?", (section_id,))
        self.conn.commit()

    def update_outline_section_order(self, ordered_ids):
        """Updates the display_order for a list of sibling IDs."""
        for order, sid in enumerate(ordered_ids):
            self.cursor.execute("UPDATE reading_outline SET display_order = ? WHERE id = ?", (order, sid))
        self.conn.commit()

    def get_outline_section_notes(self, section_id):
        self.cursor.execute("SELECT notes_html FROM reading_outline WHERE id = ?", (section_id,))
        row = self.cursor.fetchone()
        return row["notes_html"] if row else ""

    def update_outline_section_notes(self, section_id, html):
        self.cursor.execute("UPDATE reading_outline SET notes_html = ? WHERE id = ?", (html, section_id))
        self.conn.commit()

    # --- METHODS FOR PARTS TAB ---

    def get_parts_data(self, reading_id):
        """Gets all outline items for a reading that are marked as structural parts."""
        # --- FIX: Select the correct plain text fields ---
        self.cursor.execute("""
            SELECT 
                id, section_title,
                part_function_text_plain, 
                part_relation_text_plain,
                part_dependency_text_plain,
                part_dq_id
            FROM reading_outline
            WHERE reading_id = ? AND part_is_structural = 1
            ORDER BY display_order, id
        """, (reading_id,))
        return self._map_rows(self.cursor.fetchall())

    def get_part_data(self, outline_id):
        """Gets the part data for a single outline item."""
        self.cursor.execute("SELECT * FROM reading_outline WHERE id = ?", (outline_id,))
        return self._rowdict(self.cursor.fetchone())

    def save_part_data(self, reading_id, outline_id, data):
        """
        Saves the structural part data (as plain text)
        for a specific outline item.
        """

        # --- FIX (1): Save plain text directly ---
        function_text = data.get('function_text', '')
        relation_text = data.get('relation_text', '')
        dependency_text = data.get('dependency_text', '')

        self.cursor.execute("""
            UPDATE reading_outline
            SET 
                part_function_text_plain = ?,
                part_relation_text_plain = ?,
                part_dependency_text_plain = ?,
                part_is_structural = ?,
                part_dq_id = ?,

                -- Set HTML fields to null as they are no longer used
                part_function_html = NULL,
                part_relation_html = NULL,
                part_dependency_html = NULL

            WHERE id = ? AND reading_id = ?
        """, (
            function_text,
            relation_text,
            dependency_text,
            1 if data.get('is_structural') else 0,
            data.get('driving_question_id'),
            outline_id,
            reading_id
        ))
        # --- END FIX (1) ---
        self.conn.commit()