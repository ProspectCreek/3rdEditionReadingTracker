# prospectcreek/3rdeditionreadingtracker/3rdEditionReadingTracker-0eada8809e03f78f9e304f58f06c5f5a03a32c4f/database_helpers/arguments_mixin.py
import sqlite3


class ArgumentsMixin:
    """
    Mixin for managing reading-specific Arguments and their Evidence.
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

    # ----------------- READING Argument Functions -----------------

    def _get_next_argument_order(self, reading_id):
        """Gets the next display_order for a new argument."""
        self.cursor.execute(
            """SELECT COALESCE(MAX(display_order), -1) 
               FROM reading_arguments 
               WHERE reading_id = ?""",
            (reading_id,)
        )
        return (self.cursor.fetchone()[0] or -1) + 1

    def _save_argument_and_evidence(self, reading_id, argument_id, data):
        """
        Transactional save for an argument and its evidence.
        If argument_id is None, a new argument is created.
        """
        try:
            project_id = self._get_project_id_for_reading(reading_id)

            if argument_id is None:
                # Insert new argument
                new_order = self._get_next_argument_order(reading_id)
                self.cursor.execute("""
                    INSERT INTO reading_arguments (
                        reading_id, display_order, claim_text, because_text,
                        driving_question_id, is_insight, synthesis_tags
                    ) VALUES (?, ?, ?, ?, ?, ?, NULL)
                """, (
                    reading_id, new_order,
                    data.get("claim_text"),
                    data.get("because_text"),
                    data.get("driving_question_id"),
                    1 if data.get("is_insight") else 0
                ))
                argument_id = self.cursor.lastrowid
            else:
                # Update existing argument
                self.cursor.execute("""
                    UPDATE reading_arguments SET
                        claim_text = ?, because_text = ?,
                        driving_question_id = ?, is_insight = ?,
                        synthesis_tags = NULL
                    WHERE id = ? AND reading_id = ?
                """, (
                    data.get("claim_text"),
                    data.get("because_text"),
                    data.get("driving_question_id"),
                    1 if data.get("is_insight") else 0,
                    argument_id,
                    reading_id
                ))
                # Delete old evidence before adding new
                self.cursor.execute(
                    "DELETE FROM reading_argument_evidence WHERE argument_id = ?",
                    (argument_id,)
                )

            # --- Handle Tags ---
            self._handle_virtual_anchor_tags(project_id, reading_id, argument_id, 'argument', data, 'claim_text')

            # Insert new evidence items
            evidence_data = data.get("evidence", [])
            if evidence_data:
                evidence_to_insert = []
                for ev in evidence_data:
                    evidence_to_insert.append((
                        argument_id,
                        ev.get("outline_id"),
                        ev.get("pages_text"),
                        ev.get("argument_text"),
                        ev.get("reading_text"),
                        ev.get("role_in_argument"),
                        ev.get("evidence_type"),
                        ev.get("status"),
                        ev.get("rationale_text")
                    ))

                self.cursor.executemany("""
                    INSERT INTO reading_argument_evidence (
                        argument_id, outline_id, pages_text, argument_text,
                        reading_text, role_in_argument, evidence_type,
                        status, rationale_text
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, evidence_to_insert)

            self.conn.commit()
            return argument_id
        except Exception as e:
            self.conn.rollback()
            print(f"Error in _save_argument_and_evidence: {e}")
            raise

    def add_argument(self, reading_id, data):
        """Public method to add a new argument."""
        return self._save_argument_and_evidence(reading_id, None, data)

    def update_argument(self, argument_id, data):
        """Public method to update an existing argument."""
        self.cursor.execute("SELECT reading_id FROM reading_arguments WHERE id = ?", (argument_id,))
        res = self.cursor.fetchone()
        if not res:
            raise Exception(f"No argument found with id {argument_id}")
        reading_id = res['reading_id']
        return self._save_argument_and_evidence(reading_id, argument_id, data)

    def get_reading_arguments(self, reading_id):
        """Gets all arguments for the list view, creating a 'details' summary."""
        self.cursor.execute("""
            SELECT 
                ra.id, 
                ra.claim_text, 
                ra.because_text, 
                ra.is_insight,
                GROUP_CONCAT(rae.argument_text, '; ') as details
            FROM reading_arguments ra
            LEFT JOIN reading_argument_evidence rae ON ra.id = rae.argument_id
            WHERE ra.reading_id = ?
            GROUP BY ra.id
            ORDER BY ra.display_order, ra.id
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

    def get_argument_details(self, argument_id):
        """Gets full details for one argument and all its evidence."""
        self.cursor.execute("SELECT * FROM reading_arguments WHERE id = ?", (argument_id,))
        data = self._rowdict(self.cursor.fetchone())
        if not data:
            return None

        self.cursor.execute("SELECT sa.id FROM synthesis_anchors sa WHERE sa.item_link_id = ?", (argument_id,))
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
            data['synthesis_tags'] = ", ".join(tag_names)
        else:
            data['synthesis_tags'] = ""

        self.cursor.execute(
            "SELECT * FROM reading_argument_evidence WHERE argument_id = ?",
            (argument_id,)
        )
        data['evidence'] = self._map_rows(self.cursor.fetchall())
        return data

    def delete_argument(self, argument_id):
        """Deletes an argument. Evidence is deleted by cascade."""
        self.cursor.execute(
            "DELETE FROM reading_arguments WHERE id = ?",
            (argument_id,)
        )
        self.conn.commit()

    def update_argument_order(self, ordered_ids):
        """Updates the display_order for reading-level arguments."""
        for order, arg_id in enumerate(ordered_ids):
            self.cursor.execute(
                "UPDATE reading_arguments SET display_order = ? WHERE id = ?",
                (order, arg_id)
            )
        self.conn.commit()

    def update_argument_insight_status(self, argument_id, is_insight):
        """Updates the 'is_insight' flag for an argument."""
        self.cursor.execute(
            "UPDATE reading_arguments SET is_insight = ? WHERE id = ?",
            (1 if is_insight else 0, argument_id)
        )
        self.conn.commit()