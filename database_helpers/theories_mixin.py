# prospectcreek/3rdeditionreadingtracker/3rdEditionReadingTracker-d0eaa6c33c524aa054deaa3e5b81207eb93ba7d2/database_helpers/theories_mixin.py

class TheoriesMixin:
    """
    Mixin for managing reading-specific Theories.

    This re-purposes the 'reading_driving_questions' table
    by storing items with type = 'theory'.

    Field mapping:
    - Theory Name: question_text
    - Theory Author: nickname
    - Year: scope
    - Location: outline_id
    - Page(s): pages
    - Description: question_category
    - Purpose: why_question
    - Synthesis Tags: synthesis_tags
    - Notes: extra_notes_text  <-- MODIFIED
    """

    # ----------------- READING Theory Functions -----------------

    def _get_next_reading_theory_order(self, reading_id):
        """Gets the next display_order for a new theory."""
        self.cursor.execute(
            """SELECT COALESCE(MAX(display_order), -1) 
               FROM reading_driving_questions 
               WHERE reading_id = ? AND type = 'theory'""",
            (reading_id,)
        )
        return (self.cursor.fetchone()[0] or -1) + 1

    def add_reading_theory(self, reading_id, data):
        """Adds a simple, reading-level theory."""
        new_order = self._get_next_reading_theory_order(reading_id)

        self.cursor.execute("""
            INSERT INTO reading_driving_questions (
                reading_id, parent_id, display_order, 
                question_text, nickname, scope, 
                outline_id, pages, question_category, 
                why_question, synthesis_tags, extra_notes_text,
                type
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'theory')
        """, (
            reading_id, None, new_order,
            data.get("theory_name"),
            data.get("theory_author"),
            data.get("year"),
            data.get("outline_id"),
            data.get("pages"),
            data.get("description"),
            data.get("purpose"),
            data.get("synthesis_tags"),
            data.get("notes")  # <-- ADDED
        ))
        self.conn.commit()
        return self.cursor.lastrowid

    def update_reading_theory(self, theory_id, data):
        """Updates a simple, reading-level theory."""
        self.cursor.execute("""
            UPDATE reading_driving_questions SET
                question_text = ?, nickname = ?, scope = ?,
                outline_id = ?, pages = ?, question_category = ?,
                why_question = ?, synthesis_tags = ?, extra_notes_text = ?
            WHERE id = ? AND type = 'theory'
        """, (
            data.get("theory_name"),
            data.get("theory_author"),
            data.get("year"),
            data.get("outline_id"),
            data.get("pages"),
            data.get("description"),
            data.get("purpose"),
            data.get("synthesis_tags"),
            data.get("notes"),  # <-- ADDED
            theory_id
        ))
        self.conn.commit()

    def get_reading_theories(self, reading_id):
        """Gets all simple, reading-level theories for the list view."""
        self.cursor.execute("""
            SELECT 
                id, 
                question_text as theory_name, 
                nickname as theory_author, 
                why_question as purpose
            FROM reading_driving_questions
            WHERE reading_id = ? AND type = 'theory'
            ORDER BY display_order, id
        """, (reading_id,))
        return self._map_rows(self.cursor.fetchall())

    def get_reading_theory_details(self, theory_id):
        """Gets full details for a single reading-level theory."""
        self.cursor.execute("""
            SELECT 
                dq.id, 
                dq.question_text as theory_name,
                dq.nickname as theory_author,
                dq.scope as year,
                dq.outline_id,
                dq.pages,
                dq.question_category as description,
                dq.why_question as purpose,
                dq.synthesis_tags,
                dq.extra_notes_text as notes -- <-- ADDED
            FROM reading_driving_questions dq
            WHERE dq.id = ? AND dq.type = 'theory'
        """, (theory_id,))
        return self._rowdict(self.cursor.fetchone())

    def delete_reading_theory(self, theory_id):
        """Deletes a simple, reading-level theory."""
        self.cursor.execute(
            "DELETE FROM reading_driving_questions WHERE id = ? AND type = 'theory'",
            (theory_id,)
        )
        self.conn.commit()

    def update_reading_theory_order(self, ordered_ids):
        """Updates the display_order for reading-level theories."""
        for order, theory_id in enumerate(ordered_ids):
            self.cursor.execute(
                "UPDATE reading_driving_questions SET display_order = ? WHERE id = ? AND type = 'theory'",
                (order, theory_id)
            )
        self.conn.commit()