# database_helpers/terminology_mixin.py

class TerminologyMixin:
    # ----------------------- NEW: Terminology Functions -----------------------

    def get_all_outline_items_for_project(self, project_id):
        """
        Gets all outline items for all readings in a project.
        Returns a dict mapping: { reading_id: [ (display_text, outline_id), ... ] }
        """
        readings_sql = "SELECT id FROM readings WHERE project_id = ?"
        self.cursor.execute(readings_sql, (project_id,))
        readings = self.cursor.fetchall()
        outline_map = {}

        for reading in readings:
            reading_id = reading['id']
            outline_map[reading_id] = []

            def build_flat_list(parent_id, indent_level):
                # Use _map_rows to get list[dict]
                items = self.get_reading_outline(reading_id, parent_id)
                for item in items:
                    display_text = ("  " * indent_level) + item['section_title']
                    outline_map[reading_id].append((display_text, item['id']))
                    # Recursive call
                    build_flat_list(item['id'], indent_level + 1)

            build_flat_list(None, 0)  # Start from root
        return outline_map

    def save_terminology_entry(self, project_id, terminology_id, data):
        """
        Saves a single terminology entry, including its term, meaning,
        and all associated references. This is a transactional operation.
        """
        try:
            # 1. Add or Update the main term
            if terminology_id:
                # Update existing term
                self.cursor.execute("""
                    UPDATE project_terminology
                    SET term = ?, meaning = ?
                    WHERE id = ? AND project_id = ?
                """, (data['term'], data['meaning'], terminology_id, project_id))
            else:
                # Insert new term and get its ID
                self.cursor.execute(
                    "SELECT COALESCE(MAX(display_order), -1) FROM project_terminology WHERE project_id = ?",
                    (project_id,))
                new_order = (self.cursor.fetchone()[0] or -1) + 1

                self.cursor.execute("""
                    INSERT INTO project_terminology (project_id, term, meaning, display_order)
                    VALUES (?, ?, ?, ?)
                """, (project_id, data['term'], data['meaning'], new_order))
                terminology_id = self.cursor.lastrowid

            if not terminology_id:
                raise Exception("Failed to create or find terminology ID.")

            # 2. Delete all existing references for this term
            self.cursor.execute("DELETE FROM terminology_references WHERE terminology_id = ?", (terminology_id,))

            # 3. Update or Insert the status for ALL readings
            status_data = []
            for status in data.get("statuses", []):
                status_data.append((
                    terminology_id,
                    status.get('reading_id'),
                    status.get('not_in_reading', 0)
                ))

            if status_data:
                self.cursor.executemany("""
                    INSERT INTO terminology_reading_links (terminology_id, reading_id, not_in_reading)
                    VALUES (?, ?, ?)
                    ON CONFLICT(terminology_id, reading_id) DO UPDATE SET
                    not_in_reading = excluded.not_in_reading
                """, status_data)

            # 4. Insert all new references
            not_in_reading_ids = {s['reading_id'] for s in data.get("statuses", []) if s['not_in_reading'] == 1}

            for ref in data.get("references", []):
                if ref.get('reading_id') not in not_in_reading_ids:
                    # Insert reference
                    self.cursor.execute("""
                        INSERT INTO terminology_references 
                        (terminology_id, reading_id, outline_id, page_number, author_address, notes)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        terminology_id,
                        ref.get('reading_id'),
                        ref.get('outline_id'),
                        ref.get('page_number', ''),
                        ref.get('author_address'),
                        ref.get('notes')
                    ))
                    new_ref_id = self.cursor.lastrowid

                    # Insert PDF links for this reference
                    pdf_links = ref.get('pdf_node_ids', [])
                    if pdf_links:
                        pdf_data = [(new_ref_id, pid) for pid in pdf_links]
                        self.cursor.executemany("""
                            INSERT INTO terminology_reference_pdf_links (reference_id, pdf_node_id)
                            VALUES (?, ?)
                        """, pdf_data)

            # 5. Commit transaction
            self.conn.commit()

        except Exception as e:
            self.conn.rollback()
            print(f"Error saving terminology entry: {e}")
            raise

    def get_project_terminology(self, project_id):
        """
        Gets a list of all terms for a project, ordered by display_order.
        """
        self.cursor.execute("""
            SELECT id, term
            FROM project_terminology
            WHERE project_id = ?
            ORDER BY display_order, id
        """, (project_id,))
        return self._map_rows(self.cursor.fetchall())

    def get_terminology_details(self, terminology_id):
        """
        Gets the full details for a single term, including its references and their PDF links.
        """
        # 1. Get the main term data
        self.cursor.execute("SELECT * FROM project_terminology WHERE id = ?", (terminology_id,))
        term_data = self._rowdict(self.cursor.fetchone())

        if not term_data:
            return None

        # 2. Get all associated references
        self.cursor.execute("""
            SELECT 
                tr.*, 
                ro.section_title
            FROM terminology_references tr
            LEFT JOIN reading_outline ro ON tr.outline_id = ro.id
            WHERE tr.terminology_id = ?
        """, (terminology_id,))
        references = self._map_rows(self.cursor.fetchall())

        # 3. Fetch PDF links for each reference
        for ref in references:
            self.cursor.execute("""
                SELECT n.id, n.label, n.page_number
                FROM pdf_nodes n
                JOIN terminology_reference_pdf_links l ON n.id = l.pdf_node_id
                WHERE l.reference_id = ?
            """, (ref['id'],))
            ref['pdf_nodes'] = self._map_rows(self.cursor.fetchall())
            # Also store list of IDs for the dialog
            ref['pdf_node_ids'] = [n['id'] for n in ref['pdf_nodes']]

        term_data['references'] = references

        # 4. Get all reading link statuses
        self.cursor.execute("""
            SELECT reading_id, not_in_reading
            FROM terminology_reading_links
            WHERE terminology_id = ?
        """, (terminology_id,))
        statuses = self.cursor.fetchall()
        term_data['statuses'] = {row['reading_id']: row['not_in_reading'] for row in statuses}

        return term_data

    def delete_terminology(self, terminology_id):
        """
        Deletes a terminology entry. Cascade delete handles references.
        """
        self.cursor.execute("DELETE FROM project_terminology WHERE id = ?", (terminology_id,))
        self.conn.commit()

    def update_terminology_order(self, ordered_ids):
        """
        Updates the display_order for a list of terminology IDs.
        """
        for order, term_id in enumerate(ordered_ids):
            self.cursor.execute(
                "UPDATE project_terminology SET display_order = ? WHERE id = ?",
                (order, term_id)
            )
        self.conn.commit()