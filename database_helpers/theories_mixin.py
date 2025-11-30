# database_helpers/theories_mixin.py
import sqlite3


class TheoriesMixin:
    """
    Mixin for managing reading-specific Theories.
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
        pdf_node_id = data.get("pdf_node_id")

        self.cursor.execute("SELECT id FROM synthesis_anchors WHERE item_link_id = ?", (item_id,))
        anchor_row = self.cursor.fetchone()

        if not tag_names and not pdf_node_id:
            if anchor_row:
                self.cursor.execute("DELETE FROM synthesis_anchors WHERE id = ?", (anchor_row['id'],))
            return

        summary_text = data.get(summary_field_name, f'{item_type.capitalize()} Item')
        summary_text = f"{item_type.capitalize()}: {summary_text}"
        summary_text = (summary_text[:75] + '...') if len(summary_text) > 75 else summary_text

        if not anchor_row:
            self.cursor.execute("""
                INSERT INTO synthesis_anchors (
                    project_id, reading_id, item_link_id, unique_doc_id, 
                    selected_text, item_type, pdf_node_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (project_id, reading_id, item_id, f"{item_type}_{item_id}",
                  summary_text, item_type, pdf_node_id))
            anchor_id = self.cursor.lastrowid
        else:
            anchor_id = anchor_row['id']
            self.cursor.execute("""
                UPDATE synthesis_anchors 
                SET selected_text = ?, pdf_node_id = ? 
                WHERE id = ?
            """, (summary_text, pdf_node_id, anchor_id))

        self.cursor.execute("DELETE FROM anchor_tag_links WHERE anchor_id = ?", (anchor_id,))

        for tag_name in tag_names:
            tag = self.get_or_create_tag(tag_name, project_id)  # get_or_create_tag is in SynthesisMixin
            if tag:
                self.cursor.execute("""
                    INSERT OR IGNORE INTO anchor_tag_links (anchor_id, tag_id) 
                    VALUES (?, ?)
                """, (anchor_id, tag['id']))

    # --- END: Copied Helper Functions ---

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
        try:
            project_id = self._get_project_id_for_reading(reading_id)
            new_order = self._get_next_reading_theory_order(reading_id)

            self.cursor.execute("""
                INSERT INTO reading_driving_questions (
                    reading_id, parent_id, display_order, 
                    question_text, nickname, scope, 
                    outline_id, pages, question_category, 
                    why_question, synthesis_tags, extra_notes_text,
                    type, pdf_node_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, 'theory', ?)
            """, (
                reading_id, None, new_order,
                data.get("theory_name"),
                data.get("theory_author"),
                data.get("year"),
                data.get("outline_id"),
                data.get("pages"),
                data.get("description"),
                data.get("purpose"),
                data.get("notes"),
                data.get("pdf_node_id")
            ))

            new_item_id = self.cursor.lastrowid

            # Handle tags
            self._handle_virtual_anchor_tags(project_id, reading_id, new_item_id, 'theory', data, 'theory_name')

            self.conn.commit()
            return new_item_id
        except Exception as e:
            print(f"Error in add_reading_theory: {e}")
            self.conn.rollback()
            raise

    def update_reading_theory(self, theory_id, data):
        """Updates a simple, reading-level theory."""
        try:
            self.cursor.execute("SELECT reading_id FROM reading_driving_questions WHERE id = ?", (theory_id,))
            reading_id = self.cursor.fetchone()['reading_id']
            project_id = self._get_project_id_for_reading(reading_id)

            self.cursor.execute("""
                UPDATE reading_driving_questions SET
                    question_text = ?, nickname = ?, scope = ?,
                    outline_id = ?, pages = ?, question_category = ?,
                    why_question = ?, synthesis_tags = NULL, extra_notes_text = ?,
                    pdf_node_id = ?
                WHERE id = ? AND type = 'theory'
            """, (
                data.get("theory_name"),
                data.get("theory_author"),
                data.get("year"),
                data.get("outline_id"),
                data.get("pages"),
                data.get("description"),
                data.get("purpose"),
                data.get("notes"),
                data.get("pdf_node_id"),
                theory_id
            ))

            # Handle tags
            self._handle_virtual_anchor_tags(project_id, reading_id, theory_id, 'theory', data, 'theory_name')

            self.conn.commit()
        except Exception as e:
            print(f"Error in update_reading_theory: {e}")
            self.conn.rollback()
            raise

    def get_reading_theories(self, reading_id):
        """Gets all simple, reading-level theories for the list view."""
        self.cursor.execute("""
            SELECT 
                id, 
                question_text as theory_name, 
                nickname as theory_author, 
                why_question as purpose,
                pdf_node_id
            FROM reading_driving_questions
            WHERE reading_id = ? AND type = 'theory'
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
                dq.extra_notes_text as notes,
                dq.pdf_node_id
            FROM reading_driving_questions dq
            WHERE dq.id = ? AND dq.type = 'theory'
        """, (theory_id,))

        details = self._rowdict(self.cursor.fetchone())
        if not details:
            return None

        self.cursor.execute("SELECT sa.id FROM synthesis_anchors sa WHERE sa.item_link_id = ?", (theory_id,))
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