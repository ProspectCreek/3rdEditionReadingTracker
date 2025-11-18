import sqlite3


class ItemsMixin:
    # ---------------------- items / projects ----------------------

    def _next_item_order(self, parent_id):
        if parent_id is None:
            self.cursor.execute("SELECT COALESCE(MAX(display_order), -1) FROM items WHERE parent_id IS NULL")
        else:
            self.cursor.execute("SELECT COALESCE(MAX(display_order), -1) FROM items WHERE parent_id = ?", (parent_id,))
        return (self.cursor.fetchone()[0] or -1) + 1

    def add_item(self, parent_id, type_, name):
        """Legacy helper used by some UIs."""
        new_order = self._next_item_order(parent_id)
        self.cursor.execute(
            "INSERT INTO items (parent_id, type, name, display_order) VALUES (?, ?, ?, ?)",
            (parent_id, type_, name, new_order)
        )
        self.conn.commit()
        return self.cursor.lastrowid

    def create_item(self, name, item_type, parent_db_id=None, is_assignment=0):
        """UI-facing creator (signature used by ProjectListWidget)."""
        new_order = self._next_item_order(parent_db_id)
        self.cursor.execute("""
            INSERT INTO items (parent_id, type, name, display_order, is_assignment)
            VALUES (?, ?, ?, ?, ?)
        """, (parent_db_id, item_type, name, new_order, int(is_assignment)))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_items(self, parent_id=None):
        """Return children as list[dict] (safe for .get usage)."""
        if parent_id is None:
            self.cursor.execute("""
                SELECT * FROM items
                WHERE parent_id IS NULL
                ORDER BY display_order, id
            """)
        else:
            self.cursor.execute("""
                SELECT * FROM items
                WHERE parent_id = ?
                ORDER BY display_order, id
            """, (parent_id,))
        return self._map_rows(self.cursor.fetchall())

    def get_all_classes(self):
        """Gets all items that are of type 'class'."""
        self.cursor.execute("""
            SELECT * FROM items 
            WHERE type = 'class' 
            ORDER BY display_order, name
        """)
        return self._map_rows(self.cursor.fetchall())

    def move_item(self, item_id, new_parent_id):
        """Moves an item to a new parent."""
        new_order = self._next_item_order(new_parent_id)

        self.cursor.execute("""
            UPDATE items 
            SET parent_id = ?, display_order = ? 
            WHERE id = ?
        """, (new_parent_id, new_order, item_id))
        self.conn.commit()

    def update_order(self, ordered_ids):
        """
        Updates the display_order for a list of sibling IDs.
        Assumes all items in the list have the same parent.
        """
        for order, item_id in enumerate(ordered_ids):
            self.cursor.execute(
                "UPDATE items SET display_order = ? WHERE id = ?",
                (order, item_id)
            )
        self.conn.commit()

    def update_assignment_status(self, project_id, new_status_val):
        """Updates the is_assignment flag and clears data if set to 0."""
        self.cursor.execute(
            "UPDATE items SET is_assignment = ? WHERE id = ?",
            (int(new_status_val), project_id)
        )
        if int(new_status_val) == 0:
            self.cursor.execute("DELETE FROM rubric_components WHERE project_id = ?", (project_id,))
            self.cursor.execute(
                "UPDATE items SET assignment_instructions_text = NULL, assignment_draft_text = NULL WHERE id = ?",
                (project_id,)
            )
        self.conn.commit()

    def duplicate_item(self, item_id):
        """Duplicates an item (project) and its children (readings, etc.)."""
        original_project = self.get_item_details(item_id)
        if not original_project:
            return

        new_name = f"{original_project['name']} (Copy)"
        new_project_id = self.create_item(
            new_name,
            original_project['type'],
            original_project['parent_id'],
            original_project['is_assignment']
        )

        fields_to_copy = [
            'project_purpose_text', 'project_goals_text', 'key_questions_text',
            'thesis_text', 'insights_text', 'unresolved_text',
            'assignment_instructions_text', 'assignment_draft_text'
        ]
        set_clause = ", ".join([f"{field} = ?" for field in fields_to_copy])
        values = [original_project[field] for field in fields_to_copy]
        values.append(new_project_id)

        self.cursor.execute(f"UPDATE items SET {set_clause} WHERE id = ?", tuple(values))

        original_readings = self.get_readings(item_id)
        for reading in original_readings:
            new_reading_id = self.add_reading(
                new_project_id,
                reading['title'],
                reading['author'],
                reading['nickname']
            )
            reading_details = {
                'title': reading['title'], 'author': reading['author'], 'nickname': reading['nickname'],
                'published': reading['published'], 'pages': reading['pages'], 'assignment': reading['assignment'],
                'level': reading['level'], 'classification': reading['classification']
            }
            self.update_reading_details(new_reading_id, reading_details)

            self._copy_reading_outline(reading['id'], new_reading_id, None, None)

        original_rubric = self.get_rubric_components(item_id)
        for comp in original_rubric:
            self.add_rubric_component(new_project_id, comp['component_text'])

        original_instr = self.get_or_create_instructions(item_id)
        if original_instr:
            # --- MODIFIED: Pass all instructions as a dict ---
            self.update_instructions(new_project_id, original_instr)
            # --- END MODIFIED ---

        self.conn.commit()

    def _copy_reading_outline(self, old_reading_id, new_reading_id, old_parent_id, new_parent_id):
        """Recursive helper to duplicate reading outline."""
        original_items = self.get_reading_outline(old_reading_id, old_parent_id)
        for item in original_items:
            self.cursor.execute("""
                INSERT INTO reading_outline (reading_id, parent_id, section_title, notes_html, display_order)
                VALUES (?, ?, ?, ?, ?)
            """, (new_reading_id, new_parent_id, item['section_title'], item['notes_html'], item['display_order']))

            new_item_id = self.cursor.lastrowid
            self._copy_reading_outline(old_reading_id, new_reading_id, item['id'], new_item_id)

    def get_item_details(self, item_id):
        """Return a single item as dict (safe for .get usage)."""
        self.cursor.execute("SELECT * FROM items WHERE id = ?", (item_id,))
        return self._rowdict(self.cursor.fetchone())

    def rename_item(self, item_id, new_name):
        self.cursor.execute("UPDATE items SET name = ? WHERE id = ?", (new_name, item_id))
        self.conn.commit()

    def delete_item(self, item_id):
        self.cursor.execute("DELETE FROM items WHERE id = ?", (item_id,))
        self.conn.commit()

    def update_project_text_field(self, project_id, field_name, html_text):
        self.cursor.execute(f"UPDATE items SET {field_name} = ? WHERE id = ?", (html_text, project_id))
        self.conn.commit()

    # --- START OF MODIFICATIONS ---

    # List of all 17 instruction columns
    INSTRUCTION_COLUMNS = [
        "key_questions_instr", "thesis_instr", "insights_instr", "unresolved_instr",
        "synthesis_terminology_instr", "synthesis_propositions_instr", "synthesis_notes_instr",
        "reading_dq_instr", "reading_lp_instr", "reading_unity_instr", "reading_elevator_instr",
        "reading_parts_instr", "reading_key_terms_instr", "reading_arguments_instr",
        "reading_gaps_instr", "reading_theories_instr", "reading_dialogue_instr",
        "reading_rules_html"  # --- NEW ---
    ]

    # ------------------------- instructions -------------------------

    def get_or_create_instructions(self, project_id):
        """
        Gets all instructions for a project.
        If no row exists, creates one with all fields set to empty strings.
        """
        self.cursor.execute("SELECT * FROM instructions WHERE project_id = ?", (project_id,))
        row = self.cursor.fetchone()
        if row:
            # Convert to dict to ensure all keys exist, even if they are NULL in DB
            # (which they shouldn't be, but this is safer)
            row_dict = self._rowdict(row)
            all_data = {}
            for col in self.INSTRUCTION_COLUMNS:
                all_data[col] = row_dict.get(col, '')
            return all_data

        # Row not found, check again with count to be safe (prevents race conditions)
        self.cursor.execute("SELECT COUNT(*) FROM instructions WHERE project_id = ?", (project_id,))
        count = self.cursor.fetchone()[0]
        if count == 0:
            try:
                # Create a new row with all 17 columns explicitly set to ''
                all_cols = ", ".join(self.INSTRUCTION_COLUMNS)
                # Create a string of 17 placeholders ('')
                all_placeholders = ", ".join(["''" for _ in self.INSTRUCTION_COLUMNS])

                self.cursor.execute(f"""
                    INSERT INTO instructions (project_id, {all_cols})
                    VALUES (?, {all_placeholders})
                """, (project_id,))
                self.conn.commit()
            except sqlite3.IntegrityError:
                pass  # Race condition, another process inserted it.
            except Exception as e:
                print(f"Error creating default instructions: {e}")
                return {col: '' for col in self.INSTRUCTION_COLUMNS}  # Return empty dict on failure

        # Fetch the newly created (or just-found) row
        self.cursor.execute("SELECT * FROM instructions WHERE project_id = ?", (project_id,))
        row = self.cursor.fetchone()

        # Convert to dict and fill in any missing keys
        row_dict = self._rowdict(row) if row else {}
        all_data = {}
        for col in self.INSTRUCTION_COLUMNS:
            all_data[col] = row_dict.get(col, '')
        return all_data

    def update_instructions(self, project_id, instructions_data: dict):
        """
        Updates all 17 instruction fields from a data dictionary.
        """

        # Build the SET clause
        set_clause = ", ".join([f"{col} = ?" for col in self.INSTRUCTION_COLUMNS])

        # Build the parameters tuple in the correct order
        # Use .get() to safely handle missing keys, defaulting to empty string
        params = [instructions_data.get(col, '') for col in self.INSTRUCTION_COLUMNS]

        # Add the project_id for the WHERE clause
        params.append(project_id)

        try:
            self.cursor.execute(f"""
                UPDATE instructions
                SET {set_clause}
                WHERE project_id = ?
            """, tuple(params))
            self.conn.commit()
        except Exception as e:
            print(f"Error updating instructions: {e}")
            self.conn.rollback()

    # --- END OF MODIFICATIONS ---