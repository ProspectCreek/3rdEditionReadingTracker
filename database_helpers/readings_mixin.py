# prospectcreek/3rdeditionreadingtracker/database_helpers/readings_mixin.py
class ReadingsMixin:
    # --------------------------- readings ---------------------------

    def add_reading(self, project_id, title, author, nickname, zotero_key=None,
                    published="", pages="", level="", classification=""):
        """Named params + computed display_order + verify presence."""
        self.cursor.execute(
            "SELECT COALESCE(MAX(display_order), -1) FROM readings WHERE project_id = ?",
            (project_id,)
        )
        new_order = (self.cursor.fetchone()[0] or -1) + 1

        payload = {
            "project_id": int(project_id),
            "title": (title or "").strip(),
            "author": (author or "").strip(),
            "nickname": (nickname or "").strip(),
            "display_order": int(new_order),
            "zotero_item_key": zotero_key,
            "published": published,
            "pages": pages,
            "level": level,
            "classification": classification
        }

        self.cursor.execute("""
            INSERT INTO readings (
                project_id, title, author, nickname, display_order, zotero_item_key,
                published, pages, level, classification
            )
            VALUES (
                :project_id, :title, :author, :nickname, :display_order, :zotero_item_key,
                :published, :pages, :level, :classification
            )
        """, payload)
        self.conn.commit()

        new_id = self.cursor.lastrowid
        if self.get_reading_details(new_id) is None:
            raise RuntimeError("Insert verification failed: reading row not found after commit.")
        return new_id

    def get_readings(self, project_id):
        self.cursor.execute("""
            SELECT * FROM readings
            WHERE project_id = ?
            ORDER BY display_order ASC, id ASC
        """, (project_id,))
        return self._map_rows(self.cursor.fetchall())

    def get_reading_details(self, reading_id):
        self.cursor.execute("SELECT * FROM readings WHERE id = ?", (reading_id,))
        return self._rowdict(self.cursor.fetchone())

    def update_reading_details(self, reading_id, details_dict):
        """Updated to include zotero_item_key in the update."""
        self.cursor.execute("""
            UPDATE readings
            SET title = ?, author = ?, nickname = ?, published = ?, 
                pages = ?, assignment = ?, level = ?, classification = ?,
                zotero_item_key = ?
            WHERE id = ?
        """, (
            details_dict.get('title', ''),
            details_dict.get('author', ''),
            details_dict.get('nickname', ''),
            details_dict.get('published', ''),
            details_dict.get('pages', ''),
            details_dict.get('assignment', ''),
            details_dict.get('level', ''),
            details_dict.get('classification', ''),
            details_dict.get('zotero_item_key'), # <-- Added this
            reading_id
        ))
        self.conn.commit()

    def update_reading_nickname(self, reading_id, new_name):
        self.cursor.execute("UPDATE readings SET nickname = ? WHERE id = ?", (new_name, reading_id))
        self.conn.commit()

    def update_reading_field(self, reading_id, field_name, html):
        """Updates a single text field for a reading, using a whitelist."""
        allowed_fields = [
            'propositions_html', 'unity_html', 'key_terms_html',
            'arguments_html', 'gaps_html', 'theories_html',
            'personal_dialogue_html',
            # --- FIX: Add the new column to the whitelist ---
            'elevator_abstract_html'
            # --- END FIX ---
        ]
        if field_name not in allowed_fields:
            print(f"Error: Attempt to update invalid field {field_name}")
            return

        self.cursor.execute(
            f"UPDATE readings SET {field_name} = ? WHERE id = ?",
            (html, reading_id)
        )
        self.conn.commit()

    # --- NEW METHOD FOR UNITY TAB ---
    def save_reading_unity_data(self, reading_id, html_content, kind_of_work, dq_id):
        """Saves all data from the custom Unity tab."""
        try:
            self.cursor.execute("""
                UPDATE readings
                SET 
                    unity_html = ?, 
                    unity_kind_of_work = ?, 
                    unity_driving_question_id = ?
                WHERE id = ?
            """, (html_content, kind_of_work, dq_id, reading_id))
            self.conn.commit()
        except Exception as e:
            print(f"Error in save_reading_unity_data: {e}")
            self.conn.rollback()

    # --- END NEW METHOD ---

    def delete_reading(self, reading_id):
        """Deletes a reading and all its related data (outline, attachments) via cascade."""
        self.cursor.execute("DELETE FROM readings WHERE id = ?", (reading_id,))
        self.conn.commit()

    def update_reading_order(self, ordered_ids):
        """Reorders readings based on a list of IDs."""
        for order, reading_id in enumerate(ordered_ids):
            self.cursor.execute(
                "UPDATE readings SET display_order = ? WHERE id = ?",
                (order, reading_id)
            )
        self.conn.commit()