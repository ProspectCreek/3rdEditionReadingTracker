# prospectcreek/3rdeditionreadingtracker/3rdEditionReadingTracker-d0eaa6c33c524aa054deaa3e5b81207eb93ba7d2/database_helpers/key_terms_mixin.py

class KeyTermsMixin:
    """
    Mixin for managing reading-specific Key Terms.

    This re-purposes the 'reading_driving_questions' table
    by storing items with type = 'term'.
    """

    # ----------------- READING Key Term Functions -----------------

    def _get_next_reading_key_term_order(self, reading_id):
        """Gets the next display_order for a new key term."""
        self.cursor.execute(
            """SELECT COALESCE(MAX(display_order), -1) 
               FROM reading_driving_questions 
               WHERE reading_id = ? AND type = 'term'""",
            (reading_id,)
        )
        return (self.cursor.fetchone()[0] or -1) + 1

    def add_reading_key_term(self, reading_id, data):
        """Adds a simple, reading-level key term."""
        new_order = self._get_next_reading_key_term_order(reading_id)

        # Map data fields to schema columns
        # question_text = Term
        # question_category = My Definition
        # nickname = Role in Argument
        # scope = Quote
        # outline_id = Location
        # pages = Page(s)
        # why_question = Notes
        # synthesis_tags = Synthesis Tags

        self.cursor.execute("""
            INSERT INTO reading_driving_questions (
                reading_id, parent_id, display_order, 
                question_text, question_category, nickname, 
                scope, outline_id, pages, 
                why_question, synthesis_tags, 
                type
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'term')
        """, (
            reading_id, None, new_order,
            data.get("term"),
            data.get("definition"),
            data.get("role"),
            data.get("quote"),
            data.get("outline_id"),
            data.get("pages"),
            data.get("notes"),
            data.get("synthesis_tags")
        ))
        self.conn.commit()
        return self.cursor.lastrowid

    def update_reading_key_term(self, term_id, data):
        """Updates a simple, reading-level key term."""
        self.cursor.execute("""
            UPDATE reading_driving_questions SET
                question_text = ?, question_category = ?, nickname = ?, 
                scope = ?, outline_id = ?, pages = ?, 
                why_question = ?, synthesis_tags = ?
            WHERE id = ? AND type = 'term'
        """, (
            data.get("term"),
            data.get("definition"),
            data.get("role"),
            data.get("quote"),
            data.get("outline_id"),
            data.get("pages"),
            data.get("notes"),
            data.get("synthesis_tags"),
            term_id
        ))
        self.conn.commit()

    def get_reading_key_terms(self, reading_id):
        """Gets all simple, reading-level key terms for the list view."""
        self.cursor.execute("""
            SELECT 
                id, 
                question_text as term, 
                question_category as definition, 
                nickname as role, 
                synthesis_tags
            FROM reading_driving_questions
            WHERE reading_id = ? AND type = 'term'
            ORDER BY display_order, id
        """, (reading_id,))
        return self._map_rows(self.cursor.fetchall())

    def get_reading_key_term_details(self, term_id):
        """Gets full details for a single reading-level key term."""
        self.cursor.execute("""
            SELECT 
                dq.id, 
                dq.question_text as term,
                dq.question_category as definition,
                dq.nickname as role,
                dq.scope as quote,
                dq.outline_id,
                dq.pages,
                dq.why_question as notes,
                dq.synthesis_tags
            FROM reading_driving_questions dq
            WHERE dq.id = ? AND dq.type = 'term'
        """, (term_id,))
        return self._rowdict(self.cursor.fetchone())

    def delete_reading_key_term(self, term_id):
        """Deletes a simple, reading-level key term."""
        self.cursor.execute(
            "DELETE FROM reading_driving_questions WHERE id = ? AND type = 'term'",
            (term_id,)
        )
        self.conn.commit()

    def update_reading_key_term_order(self, ordered_ids):
        """Updates the display_order for reading-level key terms."""
        for order, term_id in enumerate(ordered_ids):
            self.cursor.execute(
                "UPDATE reading_driving_questions SET display_order = ? WHERE id = ? AND type = 'term'",
                (order, term_id)
            )
        self.conn.commit()
