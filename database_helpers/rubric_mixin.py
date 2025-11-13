class RubricMixin:
    # --------------------------- rubric ----------------------------

    def get_rubric_components(self, project_id):
        """Return rubric components for a project as list[dict]."""
        self.cursor.execute("""
            SELECT * FROM rubric_components
            WHERE project_id = ?
            ORDER BY display_order, id
        """, (project_id,))
        return self._map_rows(self.cursor.fetchall())

    def add_rubric_component(self, project_id, text):
        """Add a rubric component at the end of the current order."""
        self.cursor.execute("""
            SELECT COALESCE(MAX(display_order), -1)
            FROM rubric_components
            WHERE project_id = ?
        """, (project_id,))
        new_order = (self.cursor.fetchone()[0] or -1) + 1

        self.cursor.execute("""
            INSERT INTO rubric_components (project_id, component_text, is_checked, display_order)
            VALUES (?, ?, 0, ?)
        """, (project_id, text, new_order))
        self.conn.commit()
        return self.cursor.lastrowid

    def update_rubric_component_text(self, component_id, text):
        """Update the visible text of a rubric component."""
        self.cursor.execute("""
            UPDATE rubric_components
            SET component_text = ?
            WHERE id = ?
        """, (text, component_id))
        self.conn.commit()

    def update_rubric_component_checked(self, component_id, is_checked):
        """Set the checked flag (0/1) on a rubric component."""
        self.cursor.execute("""
            UPDATE rubric_components
            SET is_checked = ?
            WHERE id = ?
        """, (int(bool(is_checked)), component_id))
        self.conn.commit()

    def delete_rubric_component(self, component_id):
        """Delete a rubric component."""
        self.cursor.execute("DELETE FROM rubric_components WHERE id = ?", (component_id,))
        self.conn.commit()

    def update_rubric_component_order(self, ordered_ids):
        """Reorder rubric components by the given id sequence."""
        for order, cid in enumerate(ordered_ids):
            self.cursor.execute("""
                UPDATE rubric_components
                SET display_order = ?
                WHERE id = ?
            """, (order, cid))
        self.conn.commit()