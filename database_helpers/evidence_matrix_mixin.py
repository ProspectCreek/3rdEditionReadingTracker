import sqlite3

class EvidenceMatrixMixin:
    """
    Mixin for managing Evidence Matrix themes and PDF links.
    """

    def get_evidence_matrix_themes(self, project_id):
        """Gets all themes for the evidence matrix of a project."""
        self.cursor.execute("""
            SELECT * FROM evidence_matrix_themes
            WHERE project_id = ?
            ORDER BY display_order, id
        """, (project_id,))
        return self._map_rows(self.cursor.fetchall())

    def add_evidence_matrix_theme(self, project_id, title):
        """Adds a new theme to the evidence matrix."""
        # Get next display order
        self.cursor.execute("SELECT COALESCE(MAX(display_order), -1) FROM evidence_matrix_themes WHERE project_id = ?", (project_id,))
        new_order = (self.cursor.fetchone()[0] or -1) + 1

        self.cursor.execute("""
            INSERT INTO evidence_matrix_themes (project_id, title, display_order)
            VALUES (?, ?, ?)
        """, (project_id, title, new_order))
        self.conn.commit()
        return self.cursor.lastrowid

    def update_evidence_matrix_theme_field(self, theme_id, field, value):
        """Updates a specific field for an evidence matrix theme."""
        allowed_fields = ['title', 'author_evidence', 'data_evidence', 'interpretation']
        if field not in allowed_fields:
            print(f"Error: Invalid field '{field}' for evidence_matrix_themes.")
            return

        self.cursor.execute(f"UPDATE evidence_matrix_themes SET {field} = ? WHERE id = ?", (value, theme_id))
        self.conn.commit()

    def delete_evidence_matrix_theme(self, theme_id):
        """Deletes a theme."""
        self.cursor.execute("DELETE FROM evidence_matrix_themes WHERE id = ?", (theme_id,))
        self.conn.commit()

    def update_evidence_matrix_theme_order(self, ordered_ids):
        """Updates display_order for a list of theme IDs."""
        for i, theme_id in enumerate(ordered_ids):
            self.cursor.execute("UPDATE evidence_matrix_themes SET display_order = ? WHERE id = ?", (i, theme_id))
        self.conn.commit()

    # --- PDF Linking ---

    def add_evidence_matrix_pdf_link(self, theme_id, pdf_node_id, link_type):
        """
        Links a PDF node to a theme for a specific column ('author' or 'data').
        """
        if link_type not in ['author', 'data']:
            print(f"Error: Invalid link_type '{link_type}'. Must be 'author' or 'data'.")
            return

        try:
            self.cursor.execute(
                "INSERT INTO evidence_matrix_pdf_links (theme_id, pdf_node_id, link_type) VALUES (?, ?, ?)",
                (theme_id, pdf_node_id, link_type)
            )
            self.conn.commit()
        except sqlite3.IntegrityError:
            pass  # Already exists

    def remove_evidence_matrix_pdf_link(self, theme_id, pdf_node_id, link_type):
        """Removes a PDF link."""
        self.cursor.execute(
            "DELETE FROM evidence_matrix_pdf_links WHERE theme_id = ? AND pdf_node_id = ? AND link_type = ?",
            (theme_id, pdf_node_id, link_type)
        )
        self.conn.commit()

    def get_evidence_matrix_pdf_links(self, theme_id, link_type):
        """Gets all linked PDF nodes for a theme and type."""
        self.cursor.execute("""
            SELECT n.*, l.theme_id, l.link_type
            FROM pdf_nodes n
            JOIN evidence_matrix_pdf_links l ON n.id = l.pdf_node_id
            WHERE l.theme_id = ? AND l.link_type = ?
        """, (theme_id, link_type))
        return self._map_rows(self.cursor.fetchall())