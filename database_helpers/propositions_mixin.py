class PropositionsMixin:
    # ----------------------- PROJECT Proposition Functions (Complex) -----------------------

    def save_proposition_entry(self, project_id, proposition_id, data):
        """
        Saves a single project-level proposition entry, including its text, and
        all associated references. This is a transactional operation.
        """
        try:
            # 1. Add or Update the main proposition
            if proposition_id:
                # Update existing proposition
                self.cursor.execute("""
                    UPDATE project_propositions
                    SET display_name = ?, proposition_html = ?
                    WHERE id = ? AND project_id = ?
                """, (data['display_name'], data['proposition_html'], proposition_id, project_id))
            else:
                # Insert new proposition and get its ID
                self.cursor.execute(
                    "SELECT COALESCE(MAX(display_order), -1) FROM project_propositions WHERE project_id = ?",
                    (project_id,))
                new_order = (self.cursor.fetchone()[0] or -1) + 1

                self.cursor.execute("""
                    INSERT INTO project_propositions (project_id, display_name, proposition_html, display_order)
                    VALUES (?, ?, ?, ?)
                """, (project_id, data['display_name'], data['proposition_html'], new_order))
                proposition_id = self.cursor.lastrowid

            if not proposition_id:
                raise Exception("Failed to create or find proposition ID.")

            # 2. Delete all existing references for this proposition
            self.cursor.execute("DELETE FROM proposition_references WHERE proposition_id = ?", (proposition_id,))

            # 3. Update or Insert the status for ALL readings
            status_data = []
            for status in data.get("statuses", []):
                status_data.append((
                    proposition_id,
                    status.get('reading_id'),
                    status.get('not_in_reading', 0)
                ))

            if status_data:
                self.cursor.executemany("""
                    INSERT INTO proposition_reading_links (proposition_id, reading_id, not_in_reading)
                    VALUES (?, ?, ?)
                    ON CONFLICT(proposition_id, reading_id) DO UPDATE SET
                    not_in_reading = excluded.not_in_reading
                """, status_data)

            # 4. Insert all new references
            references_data = []
            not_in_reading_ids = {s['reading_id'] for s in data.get("statuses", []) if s['not_in_reading'] == 1}

            for ref in data.get("references", []):
                if ref.get('reading_id') not in not_in_reading_ids:
                    references_data.append((
                        proposition_id,
                        ref.get('reading_id'),
                        ref.get('outline_id'),
                        ref.get('page_number'),
                        ref.get('how_addressed'),
                        ref.get('notes')
                    ))

            if references_data:
                self.cursor.executemany("""
                    INSERT INTO proposition_references 
                    (proposition_id, reading_id, outline_id, page_number, how_addressed, notes)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, references_data)

            # 5. Commit transaction
            self.conn.commit()

        except Exception as e:
            self.conn.rollback()
            print(f"Error saving proposition entry: {e}")
            raise

    def get_project_propositions(self, project_id):
        """
        Gets a list of all propositions for a project, ordered by display_order.
        """
        self.cursor.execute("""
            SELECT id, display_name
            FROM project_propositions
            WHERE project_id = ?
            ORDER BY display_order, id
        """, (project_id,))
        return self._map_rows(self.cursor.fetchall())

    # --- ALIAS for backwards compatibility ---
    get_reading_propositions = get_project_propositions

    def get_proposition_details(self, proposition_id):
        """
        Gets the full details for a single proposition, including its references.
        """
        self.cursor.execute("SELECT * FROM project_propositions WHERE id = ?", (proposition_id,))
        prop_data = self._rowdict(self.cursor.fetchone())

        if not prop_data:
            return None

        self.cursor.execute("""
            SELECT 
                pr.*, 
                ro.section_title 
            FROM proposition_references pr
            LEFT JOIN reading_outline ro ON pr.outline_id = ro.id
            WHERE pr.proposition_id = ?
        """, (proposition_id,))
        references = self._map_rows(self.cursor.fetchall())
        prop_data['references'] = references

        self.cursor.execute("""
            SELECT reading_id, not_in_reading
            FROM proposition_reading_links
            WHERE proposition_id = ?
        """, (proposition_id,))
        statuses = self.cursor.fetchall()
        prop_data['statuses'] = {row['reading_id']: row['not_in_reading'] for row in statuses}

        return prop_data

    def delete_proposition(self, proposition_id):
        """
        Deletes a project-level proposition entry. Cascade delete handles references.
        """
        self.cursor.execute("DELETE FROM project_propositions WHERE id = ?", (proposition_id,))
        self.conn.commit()

    def update_proposition_order(self, ordered_ids):
        """
        Updates the display_order for a list of proposition IDs.
        """
        for order, prop_id in enumerate(ordered_ids):
            self.cursor.execute(
                "UPDATE project_propositions SET display_order = ? WHERE id = ?",
                (order, prop_id)
            )
        self.conn.commit()

    # ----------------- READING Proposition Functions (Simple) -----------------
    # These methods are for the 'Leading Propositions' tab inside a reading
    # and will store data in the 'reading_driving_questions' table
    # with a special type.
    #
    # NOTE: This is a re-purposing of the driving questions table to
    # match the UI from your screenshot.
    # ------------------------------------------------------------------------

    def _get_next_reading_proposition_order(self, reading_id):
        self.cursor.execute(
            """SELECT COALESCE(MAX(display_order), -1) 
               FROM reading_driving_questions 
               WHERE reading_id = ? AND type = 'proposition'""",
            (reading_id,)
        )
        return (self.cursor.fetchone()[0] or -1) + 1

    def add_reading_proposition(self, reading_id, data):
        """Adds a simple, reading-level proposition."""
        new_order = self._get_next_reading_proposition_order(reading_id)
        self.cursor.execute("""
            INSERT INTO reading_driving_questions (
                reading_id, parent_id, display_order, question_text, 
                outline_id, pages, why_question, synthesis_tags, type
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'proposition')
        """, (
            reading_id, None, new_order,
            data.get("proposition_text"),
            data.get("outline_id"),
            data.get("pages"),
            data.get("why_important"),
            data.get("synthesis_tags")
        ))
        self.conn.commit()

    def update_reading_proposition(self, proposition_id, data):
        """Updates a simple, reading-level proposition."""
        self.cursor.execute("""
            UPDATE reading_driving_questions SET
                question_text = ?, outline_id = ?, pages = ?, 
                why_question = ?, synthesis_tags = ?
            WHERE id = ? AND type = 'proposition'
        """, (
            data.get("proposition_text"),
            data.get("outline_id"),
            data.get("pages"),
            data.get("why_important"),
            data.get("synthesis_tags"),
            proposition_id
        ))
        self.conn.commit()

    def get_reading_propositions_simple(self, reading_id):
        """Gets all simple, reading-level propositions."""
        self.cursor.execute("""
            SELECT id, question_text as proposition_text 
            FROM reading_driving_questions
            WHERE reading_id = ? AND type = 'proposition'
            ORDER BY display_order, id
        """, (reading_id,))
        return self._map_rows(self.cursor.fetchall())

    def get_reading_proposition_details(self, proposition_id):
        """Gets details for a single reading-level proposition."""
        self.cursor.execute("""
            SELECT 
                dq.id, 
                dq.question_text as proposition_text,
                dq.outline_id,
                dq.pages,
                dq.why_question as why_important,
                dq.synthesis_tags,
                ro.section_title as outline_title
            FROM reading_driving_questions dq
            LEFT JOIN reading_outline ro ON dq.outline_id = ro.id
            WHERE dq.id = ? AND dq.type = 'proposition'
        """, (proposition_id,))
        return self._rowdict(self.cursor.fetchone())

    def delete_reading_proposition(self, proposition_id):
        """Deletes a simple, reading-level proposition."""
        self.cursor.execute(
            "DELETE FROM reading_driving_questions WHERE id = ? AND type = 'proposition'",
            (proposition_id,)
        )
        self.conn.commit()

    def update_reading_proposition_order(self, ordered_ids):
        """Updates the display_order for reading-level propositions."""
        for order, prop_id in enumerate(ordered_ids):
            self.cursor.execute(
                "UPDATE reading_driving_questions SET display_order = ? WHERE id = ? AND type = 'proposition'",
                (order, prop_id)
            )
        self.conn.commit()