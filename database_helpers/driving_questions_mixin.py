# prospectcreek/3rdeditionreadingtracker/3rdEditionReadingTracker-d0eaa6c33c524aa054deaa3e5b81207eb93ba7d2/database_helpers/driving_questions_mixin.py

class DrivingQuestionsMixin:
    # ----------------------- reading driving questions -----------------------

    def get_driving_questions(self, reading_id, parent_id=None):
        # --- FIX: Added filter to exclude propositions, terms, and theories ---
        sql = "SELECT * FROM reading_driving_questions WHERE reading_id = ? AND (type IS NULL OR type NOT IN ('proposition', 'term', 'theory'))"
        params = [reading_id]

        if parent_id is None:
            sql += " AND parent_id IS NULL"
        elif parent_id is True:
            pass  # Get all items (already filtered by type)
        else:
            sql += " AND parent_id = ?"
            params.append(parent_id)

        sql += " ORDER BY display_order, id"
        self.cursor.execute(sql, tuple(params))
        return self._map_rows(self.cursor.fetchall())

    def get_driving_question_details(self, question_id):
        # --- FIX: Added filter to exclude propositions, terms, and theories ---
        self.cursor.execute(
            "SELECT * FROM reading_driving_questions WHERE id = ? AND (type IS NULL OR type NOT IN ('proposition', 'term', 'theory'))",
            (question_id,)
        )
        return self._rowdict(self.cursor.fetchone())

    def _next_driving_question_order(self, reading_id, parent_id):
        # --- FIX: Added filter to exclude propositions, terms, and theories ---
        sql = "SELECT COALESCE(MAX(display_order), -1) FROM reading_driving_questions WHERE reading_id = ? AND (type IS NULL OR type NOT IN ('proposition', 'term', 'theory'))"
        params = [reading_id]

        if parent_id is None:
            sql += " AND parent_id IS NULL"
        else:
            sql += " AND parent_id = ?"
            params.append(parent_id)

        self.cursor.execute(sql, tuple(params))
        return (self.cursor.fetchone()[0] or -1) + 1

    def add_driving_question(self, reading_id, data):
        parent_id = data.get("parent_id")
        new_order = self._next_driving_question_order(reading_id, parent_id)

        # Type is correctly passed in from the dialog ("Stated" or "Inferred")
        self.cursor.execute("""
            INSERT INTO reading_driving_questions (
                reading_id, parent_id, display_order, question_text, nickname, type, 
                question_category, scope, outline_id, pages, 
                why_question, synthesis_tags, is_working_question
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            reading_id, parent_id, new_order,
            data.get("question_text"), data.get("nickname"), data.get("type"),
            data.get("question_category"), data.get("scope"),
            data.get("outline_id"), data.get("pages"),
            data.get("why_question"), data.get("synthesis_tags"),
            1 if data.get("is_working_question") else 0
        ))
        self.conn.commit()
        return self.cursor.lastrowid

    def update_driving_question(self, question_id, data):
        # --- FIX: Added filter to exclude propositions, terms, and theories ---
        self.cursor.execute("""
            UPDATE reading_driving_questions SET
                parent_id = ?, question_text = ?, nickname = ?, type = ?, 
                question_category = ?, scope = ?, outline_id = ?, 
                pages = ?, why_question = ?, synthesis_tags = ?, 
                is_working_question = ?
            WHERE id = ? AND (type IS NULL OR type NOT IN ('proposition', 'term', 'theory'))
        """, (
            data.get("parent_id"), data.get("question_text"), data.get("nickname"), data.get("type"),
            data.get("question_category"), data.get("scope"),
            data.get("outline_id"), data.get("pages"),
            data.get("why_question"), data.get("synthesis_tags"),
            1 if data.get("is_working_question") else 0,
            question_id
        ))
        self.conn.commit()

    def delete_driving_question(self, question_id):
        # --- FIX: Added filter to exclude propositions, terms, and theories ---
        self.cursor.execute(
            "DELETE FROM reading_driving_questions WHERE id = ? AND (type IS NULL OR type NOT IN ('proposition', 'term', 'theory'))",
            (question_id,)
        )
        self.conn.commit()

    def update_driving_question_order(self, ordered_ids):
        for order, q_id in enumerate(ordered_ids):
            # --- FIX: Added filter to exclude propositions, terms, and theories ---
            self.cursor.execute(
                "UPDATE reading_driving_questions SET display_order = ? WHERE id = ? AND (type IS NULL OR type NOT IN ('proposition', 'term', 'theory'))",
                (order, q_id)
            )
        self.conn.commit()

    def find_current_working_question(self, reading_id):
        # --- FIX: Added filter to exclude propositions, terms, and theories ---
        self.cursor.execute(
            """SELECT * FROM reading_driving_questions 
               WHERE reading_id = ? AND is_working_question = 1 AND (type IS NULL OR type NOT IN ('proposition', 'term', 'theory'))
               LIMIT 1""",
            (reading_id,)
        )
        return self._rowdict(self.cursor.fetchone())

    def clear_all_working_questions(self, reading_id):
        # --- FIX: Added filter to exclude propositions, terms, and theories ---
        self.cursor.execute(
            "UPDATE reading_driving_questions SET is_working_question = 0 WHERE reading_id = ? AND (type IS NULL OR type NOT IN ('proposition', 'term', 'theory'))",
            (reading_id,)
        )
        self.conn.commit()