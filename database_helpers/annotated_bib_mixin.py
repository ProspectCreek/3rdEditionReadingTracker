class AnnotatedBibMixin:
    """
    Mixin for managing Annotated Bibliography entries linked to readings.
    """

    def get_annotated_bib_entries(self, project_id):
        """
        Fetches all readings for a project, joining with their annotation entries.
        Returns a list of dicts containing reading info + annotation fields.
        """
        self.cursor.execute("""
            SELECT 
                r.id as reading_id,
                r.nickname,
                r.title,
                r.author,
                ab.id as annotation_id,
                ab.citation_text,
                ab.description,
                ab.analysis,
                ab.applicability,
                ab.status
            FROM readings r
            LEFT JOIN annotated_bib_entries ab ON r.id = ab.reading_id
            WHERE r.project_id = ?
            ORDER BY r.display_order, r.id
        """, (project_id,))
        return self._map_rows(self.cursor.fetchall())

    def update_annotated_bib_entry(self, reading_id, data):
        """
        Updates or Inserts an annotation entry for a specific reading.
        'data' is a dict containing citation_text, description, etc.
        """
        # Calculate status based on fields if not provided?
        # The requirements say: "Completed when all four fields have content (user may also manually override)"
        # We will trust the UI to pass the status or handle it here.
        # Let's expect 'status' in data, but default if missing.

        citation = data.get("citation_text", "")
        desc = data.get("description", "")
        analysis = data.get("analysis", "")
        applicability = data.get("applicability", "")
        status = data.get("status", "Not Started")

        try:
            # Check if exists
            self.cursor.execute("SELECT id FROM annotated_bib_entries WHERE reading_id = ?", (reading_id,))
            row = self.cursor.fetchone()

            if row:
                # Update
                self.cursor.execute("""
                    UPDATE annotated_bib_entries
                    SET citation_text = ?, description = ?, analysis = ?, applicability = ?, status = ?
                    WHERE reading_id = ?
                """, (citation, desc, analysis, applicability, status, reading_id))
            else:
                # Insert
                self.cursor.execute("""
                    INSERT INTO annotated_bib_entries (reading_id, citation_text, description, analysis, applicability, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (reading_id, citation, desc, analysis, applicability, status))

            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error saving annotated bib entry: {e}")
            self.conn.rollback()
            return False