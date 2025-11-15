# prospectcreek/3rdeditionreadingtracker/3rdEditionReadingTracker-0eada8809e03f78f9e304f58f06c5f5a03a32c4f/database_helpers/key_terms_mixin.py
import sqlite3


class KeyTermsMixin:
    """
    Mixin for managing reading-specific Key Terms.
    This re-purposes the 'reading_driving_questions' table
    by storing items with type = 'term'.
    """

    # --- START: Copied Helper Functions ---
    def _get_project_id_for_reading(self, reading_id):
        self.cursor.execute("SELECT project_id FROM readings WHERE id = ?", (reading_id,))
        proj_data = self.cursor.fetchone()
        if not proj_data:
            raise Exception(f"Could not find project_id for reading_id {reading_id}")
        return proj_data['project_id']

    def _handle_virtual_anchor_tags(self, project_id, reading_id, item_id, item_type, data, summary_field_name):
        tags_text = data.get("synthesis_tags", "")
        tag_names = [tag.strip() for tag in tags_text.split(',') if tag.strip()]

        self.cursor.execute("SELECT id FROM synthesis_anchors WHERE item_link_id = ?", (item_id,))
        anchor_row = self.cursor.fetchone()

        if not tag_names:
            if anchor_row:
                self.cursor.execute("DELETE FROM synthesis_anchors WHERE id = ?", (anchor_row['id'],))
            return

        summary_text = data.get(summary_field_name, f'{item_type.capitalize()} Item')
        summary_text = f"{item_type.capitalize()}: {summary_text}"
        summary_text = (summary_text[:75] + '...') if len(summary_text) > 75 else summary_text

        if not anchor_row:
            self.cursor.execute("""
                INSERT INTO synthesis_anchors (project_id, reading_id, item_link_id, unique_doc_id, selected_text, item_type) 
                VALUES (?, ?, ?, ?, ?, ?)
            """, (project_id, reading_id, item_id, f"{item_type}_{item_id}", summary_text, item_type))
            anchor_id = self.cursor.lastrowid
        else:
            anchor_id = anchor_row['id']
            self.cursor.execute("UPDATE synthesis_anchors SET selected_text = ? WHERE id = ?",
                                (summary_text, anchor_id))

        self.cursor.execute("DELETE FROM anchor_tag_links WHERE anchor_id = ?", (anchor_id,))

        for tag_name in tag_names:
            tag = self.get_or_create_tag(tag_name, project_id)  # get_or_create_tag is in SynthesisMixin
            if tag:
                self.cursor.execute("""
                    INSERT OR IGNORE INTO anchor_tag_links (anchor_id, tag_id) 
                    VALUES (?, ?)
                """, (anchor_id, tag['id']))

    # --- END: Copied Helper Functions ---

    # ----------------- READING Key Term Functions -----------------

    def _get_next_reading_key_term_order(self, reading_id):
        self.cursor.execute(
            """SELECT COALESCE(MAX(display_order), -1) 
               FROM reading_driving_questions 
               WHERE reading_id = ? AND type = 'term'""",
            (reading_id,)
        )
        return (self.cursor.fetchone()[0] or -1) + 1

    def add_reading_key_term(self, reading_id, data):
        """Adds a simple, reading-level key term."""
        try:
            project_id = self._get_project_id_for_reading(reading_id)
            new_order = self._get_next_reading_key_term_order(reading_id)

            self.cursor.execute("""
                INSERT INTO reading_driving_questions (
                    reading_id, parent_id, display_order, 
                    question_text, question_category, nickname, 
                    scope, outline_id, pages, 
                    why_question, synthesis_tags, 
                    type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, 'term')
            """, (
                reading_id, None, new_order,
                data.get("term"),
                data.get("definition"),
                data.get("role"),
                data.get("quote"),
                data.get("outline_id"),
                data.get("pages"),
                data.get("notes")
            ))

            new_item_id = self.cursor.lastrowid

            # Handle tags
            self._handle_virtual_anchor_tags(project_id, reading_id, new_item_id, 'term', data, 'term')

            self.conn.commit()
            return new_item_id
        except Exception as e:
            print(f"Error in add_reading_key_term: {e}")
            self.conn.rollback()
            raise

    def update_reading_key_term(self, term_id, data):
        """Updates a simple, reading-level key term."""
        try:
            self.cursor.execute("SELECT reading_id FROM reading_driving_questions WHERE id = ?", (term_id,))
            reading_id = self.cursor.fetchone()['reading_id']
            project_id = self._get_project_id_for_reading(reading_id)

            self.cursor.execute("""
                UPDATE reading_driving_questions SET
                    question_text = ?, question_category = ?, nickname = ?, 
                    scope = ?, outline_id = ?, pages = ?, 
                    why_question = ?, synthesis_tags = NULL
                WHERE id = ? AND type = 'term'
            """, (
                data.get("term"),
                data.get("definition"),
                data.get("role"),
                data.get("quote"),
                data.get("outline_id"),
                data.get("pages"),
                data.get("notes"),
                term_id
            ))

            # Handle tags
            self._handle_virtual_anchor_tags(project_id, reading_id, term_id, 'term', data, 'term')

            self.conn.commit()
        except Exception as e:
            print(f"Error in update_reading_key_term: {e}")
            self.conn.rollback()
            raise

    def get_reading_key_terms(self, reading_id):
        """Gets all simple, reading-level key terms for the list view."""
        self.cursor.execute("""
            SELECT 
                id, 
                question_text as term, 
                question_category as definition, 
                nickname as role
            FROM reading_driving_questions
            WHERE reading_id = ? AND type = 'term'
            ORDER BY display_order, id
        """, (reading_id,))

        results = self._map_rows(self.cursor.fetchall())
        for item in results:
            self.cursor.execute("SELECT sa.id FROM synthesis_anchors sa WHERE sa.item_link_id = ?", (item['id'],))
            anchor_row = self.cursor.fetchone()

            if anchor_row:
                anchor_id = anchor_row['id']
                self.cursor.execute("""
                    SELECT t.name 
                    FROM anchor_tag_links atl
                    JOIN synthesis_tags t ON atl.tag_id = t.id
                    WHERE atl.anchor_id = ?
                """, (anchor_id,))
                tag_names = [row['name'] for row in self.cursor.fetchall()]
                item['synthesis_tags'] = ", ".join(tag_names)
            else:
                item['synthesis_tags'] = ""
        return results

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
                dq.why_question as notes
            FROM reading_driving_questions dq
            WHERE dq.id = ? AND dq.type = 'term'
        """, (term_id,))

        details = self._rowdict(self.cursor.fetchone())
        if not details:
            return None

        self.cursor.execute("SELECT sa.id FROM synthesis_anchors sa WHERE sa.item_link_id = ?", (term_id,))
        anchor_row = self.cursor.fetchone()

        if anchor_row:
            anchor_id = anchor_row['id']
            self.cursor.execute("""
                SELECT t.name 
                FROM anchor_tag_links atl
                JOIN synthesis_tags t ON atl.tag_id = t.id
                WHERE atl.anchor_id = ?
            """, (anchor_id,))
            tag_names = [row['name'] for row in self.cursor.fetchall()]
            details['synthesis_tags'] = ", ".join(tag_names)
        else:
            details['synthesis_tags'] = ""

        return details

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