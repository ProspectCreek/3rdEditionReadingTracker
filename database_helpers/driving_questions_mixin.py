# prospectcreek/3rdeditionreadingtracker/database_helpers/driving_questions_mixin.py
import sqlite3


class DrivingQuestionsMixin:
    # ----------------------- reading driving questions -----------------------

    def get_driving_questions(self, reading_id, parent_id=None):
        """
        Gets driving questions.
        - If parent_id is True: Returns ALL questions (flat list).
        - If parent_id is None: Returns root questions only.
        - If parent_id is int: Returns children of that id.

        Includes PDF Node ID and filters out other types (terms, props, etc.).
        """
        # Fetch all valid questions first
        self.cursor.execute("""
            SELECT 
                dq.id, 
                dq.reading_id, 
                dq.parent_id, 
                dq.display_order, 
                dq.question_text, 
                dq.nickname,
                dq.type,
                dq.question_category,
                dq.scope,
                dq.outline_id,
                dq.pages,
                dq.why_question,
                dq.synthesis_tags,
                dq.is_working_question,
                dq.extra_notes_text,
                dq.pdf_node_id,
                o.section_title as outline_title
            FROM reading_driving_questions dq
            LEFT JOIN reading_outline o ON dq.outline_id = o.id
            WHERE dq.reading_id = ? 
              AND (dq.type IS NULL OR dq.type NOT IN ('proposition', 'term', 'theory', 'argument'))
            ORDER BY dq.display_order, dq.id
        """, (reading_id,))

        all_rows = self._map_rows(self.cursor.fetchall())

        # Return based on parent_id filter
        if parent_id is True:
            return all_rows

        if parent_id is None:
            return [r for r in all_rows if r['parent_id'] is None]

        return [r for r in all_rows if r['parent_id'] == parent_id]

    def get_driving_question_details(self, question_id):
        """ MODIFIED TO LOAD TAGS FROM VIRTUAL ANCHOR """
        self.cursor.execute(
            "SELECT * FROM reading_driving_questions WHERE id = ? AND (type IS NULL OR type NOT IN ('proposition', 'term', 'theory', 'argument'))",
            (question_id,)
        )
        details = self._rowdict(self.cursor.fetchone())
        if not details:
            return None

        # Find the virtual anchor for this DQ
        self.cursor.execute("""
            SELECT sa.id 
            FROM synthesis_anchors sa
            WHERE sa.item_link_id = ?
        """, (question_id,))
        anchor_row = self.cursor.fetchone()

        if anchor_row:
            anchor_id = anchor_row['id']
            # Get all tag names linked to this anchor
            self.cursor.execute("""
                SELECT t.name 
                FROM anchor_tag_links atl
                JOIN synthesis_tags t ON atl.tag_id = t.id
                WHERE atl.anchor_id = ?
            """, (anchor_id,))
            tag_names = [row['name'] for row in self.cursor.fetchall()]
            details['synthesis_tags'] = ", ".join(tag_names)
        else:
            details['synthesis_tags'] = ""  # No anchor, so no tags

        return details

    def _next_driving_question_order(self, reading_id, parent_id):
        sql = "SELECT COALESCE(MAX(display_order), -1) FROM reading_driving_questions WHERE reading_id = ? AND (type IS NULL OR type NOT IN ('proposition', 'term', 'theory', 'argument'))"
        params = [reading_id]

        if parent_id is None:
            sql += " AND parent_id IS NULL"
        else:
            sql += " AND parent_id = ?"
            params.append(parent_id)

        self.cursor.execute(sql, tuple(params))
        return (self.cursor.fetchone()[0] or -1) + 1

    def _get_project_id_for_reading(self, reading_id):
        # Helper to find project_id from reading_id
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
            tag = self.get_or_create_tag(tag_name, project_id)
            if tag:
                self.cursor.execute("""
                    INSERT OR IGNORE INTO anchor_tag_links (anchor_id, tag_id) 
                    VALUES (?, ?)
                """, (anchor_id, tag['id']))

    def add_driving_question(self, reading_id, data=None):
        """ MODIFIED TO CREATE VIRTUAL ANCHOR """
        try:
            if data is None:
                # Default blank question (from button click)
                data = {
                    "question_text": "New Question",
                    "nickname": "",
                    "type": "Inferred",
                    "is_working_question": False
                }

            project_id = self._get_project_id_for_reading(reading_id)
            parent_id = data.get("parent_id")
            new_order = self._next_driving_question_order(reading_id, parent_id)

            self.cursor.execute("""
                INSERT INTO reading_driving_questions (
                    reading_id, parent_id, display_order, question_text, nickname, type, 
                    question_category, scope, outline_id, pages, 
                    why_question, is_working_question, synthesis_tags
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
            """, (
                reading_id, parent_id, new_order,
                data.get("question_text"), data.get("nickname"), data.get("type"),
                data.get("question_category"), data.get("scope"),
                data.get("outline_id"), data.get("pages"),
                data.get("why_question"),
                1 if data.get("is_working_question") else 0
            ))
            new_question_id = self.cursor.lastrowid

            # Now, handle the tags by creating/linking the virtual anchor
            self._handle_virtual_anchor_tags(project_id, reading_id, new_question_id, 'dq', data, 'question_text')

            self.conn.commit()
            return new_question_id
        except Exception as e:
            print(f"Error in add_driving_question: {e}")
            self.conn.rollback()
            raise

    def update_driving_question(self, question_id, data):
        """ MODIFIED TO UPDATE VIRTUAL ANCHOR """
        try:
            # Get project_id and reading_id
            self.cursor.execute("SELECT reading_id FROM reading_driving_questions WHERE id = ?", (question_id,))
            row = self.cursor.fetchone()
            if not row: return
            reading_id = row['reading_id']
            project_id = self._get_project_id_for_reading(reading_id)

            # Filter data keys to only valid columns to prevent SQL injection or errors
            valid_cols = [
                'parent_id', 'question_text', 'nickname', 'type', 'question_category',
                'scope', 'outline_id', 'pages', 'why_question', 'is_working_question',
                'synthesis_tags', 'extra_notes_text', 'pdf_node_id'
            ]

            updates = []
            params = []
            for k, v in data.items():
                if k in valid_cols:
                    if k == 'is_working_question':
                        updates.append(f"{k} = ?")
                        params.append(1 if v else 0)
                    else:
                        updates.append(f"{k} = ?")
                        params.append(v)

            if updates:
                # Explicitly ensure we don't overwrite synthesis_tags column (it's managed via anchors)
                # unless we want to store a cached string there.
                # But we also update the anchor below.
                params.append(question_id)
                sql = f"UPDATE reading_driving_questions SET {', '.join(updates)} WHERE id = ? AND (type IS NULL OR type NOT IN ('proposition', 'term', 'theory', 'argument'))"
                self.cursor.execute(sql, tuple(params))

            # Update the virtual anchor
            self._handle_virtual_anchor_tags(project_id, reading_id, question_id, 'dq', data, 'question_text')

            self.conn.commit()
        except Exception as e:
            print(f"Error in update_driving_question: {e}")
            self.conn.rollback()
            raise

    def delete_driving_question(self, question_id):
        """ Deletes the question. The virtual anchor is deleted by schema CASCADE. """
        self.cursor.execute(
            "DELETE FROM reading_driving_questions WHERE id = ? AND (type IS NULL OR type NOT IN ('proposition', 'term', 'theory', 'argument'))",
            (question_id,)
        )
        self.conn.commit()

    def update_driving_question_order(self, ordered_ids):
        for order, q_id in enumerate(ordered_ids):
            self.cursor.execute(
                "UPDATE reading_driving_questions SET display_order = ? WHERE id = ? AND (type IS NULL OR type NOT IN ('proposition', 'term', 'theory', 'argument'))",
                (order, q_id)
            )
        self.conn.commit()

    def find_current_working_question(self, reading_id):
        self.cursor.execute(
            """SELECT * FROM reading_driving_questions 
               WHERE reading_id = ? AND is_working_question = 1 AND (type IS NULL OR type NOT IN ('proposition', 'term', 'theory', 'argument'))
               LIMIT 1""",
            (reading_id,)
        )
        return self._rowdict(self.cursor.fetchone())

    def clear_all_working_questions(self, reading_id):
        self.cursor.execute(
            "UPDATE reading_driving_questions SET is_working_question = 0 WHERE reading_id = ? AND (type IS NULL OR type NOT IN ('proposition', 'term', 'theory', 'argument'))",
            (reading_id,)
        )
        self.conn.commit()