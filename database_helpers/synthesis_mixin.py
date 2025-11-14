import sqlite3

class SynthesisMixin:
    # --- Synthesis Functions (NOW GLOBAL) ---

    def get_all_tags(self):
        """Gets all tags from the global table."""
        self.cursor.execute("SELECT id, name FROM synthesis_tags ORDER BY name")
        return self._map_rows(self.cursor.fetchall())

    def get_or_create_tag(self, tag_name, project_id=None):
        tag_name = tag_name.strip()
        if not tag_name:
            return None

        self.cursor.execute(
            "SELECT * FROM synthesis_tags WHERE name = ?",
            (tag_name,)
        )
        tag = self._rowdict(self.cursor.fetchone())

        if not tag:
            try:
                self.cursor.execute(
                    "INSERT INTO synthesis_tags (name) VALUES (?)",
                    (tag_name,)
                )
                self.conn.commit()
                new_id = self.cursor.lastrowid
                tag = {'id': new_id, 'name': tag_name}
            except sqlite3.IntegrityError:
                self.cursor.execute(
                    "SELECT * FROM synthesis_tags WHERE name = ?",
                    (tag_name,)
                )
                tag = self._rowdict(self.cursor.fetchone())
            except Exception as e:
                print(f"Error in get_or_create_tag: {e}")
                return None

        if not tag:
            return None

        if project_id:
            try:
                self.cursor.execute(
                    "INSERT OR IGNORE INTO project_tag_links (project_id, tag_id) VALUES (?, ?)",
                    (project_id, tag['id'])
                )
                self.conn.commit()
            except Exception as e:
                print(f"Error linking tag {tag['id']} to project {project_id}: {e}")

        return tag

    def get_project_tags(self, project_id):
        self.cursor.execute("""
            SELECT DISTINCT t.id, t.name 
            FROM synthesis_tags t
            JOIN synthesis_anchors a ON t.id = a.tag_id
            WHERE a.project_id = ?

            UNION

            SELECT DISTINCT t.id, t.name
            FROM synthesis_tags t
            JOIN project_tag_links ptl ON t.id = ptl.tag_id
            WHERE ptl.project_id = ?

            ORDER BY t.name
        """, (project_id, project_id))
        return self._map_rows(self.cursor.fetchall())

    def create_anchor(self, project_id, reading_id, outline_id, tag_id, selected_text, comment, unique_doc_id, item_link_id=None):
        try:
            self.cursor.execute("""
                INSERT INTO synthesis_anchors 
                (project_id, reading_id, outline_id, selected_text, comment, unique_doc_id, tag_id, item_link_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                project_id, reading_id, outline_id, selected_text, comment, unique_doc_id, tag_id, item_link_id
            ))
            anchor_id = self.cursor.lastrowid

            self.cursor.execute(
                "INSERT OR IGNORE INTO anchor_tag_links (anchor_id, tag_id) VALUES (?, ?)",
                (anchor_id, tag_id)
            )

            self.cursor.execute(
                "INSERT OR IGNORE INTO project_tag_links (project_id, tag_id) VALUES (?, ?)",
                (project_id, tag_id)
            )

            self.conn.commit()
            return anchor_id
        except Exception as e:
            self.conn.rollback()
            print(f"Error creating anchor: {e}")
            return None

    def update_anchor(self, anchor_id, new_tag_id, new_comment):
        try:
            self.cursor.execute(
                "UPDATE synthesis_anchors SET comment = ?, tag_id = ? WHERE id = ?",
                (new_comment, new_tag_id, anchor_id)
            )

            self.cursor.execute("DELETE FROM anchor_tag_links WHERE anchor_id = ?", (anchor_id,))

            self.cursor.execute(
                "INSERT OR IGNORE INTO anchor_tag_links (anchor_id, tag_id) VALUES (?, ?)",
                (anchor_id, new_tag_id)
            )

            self.cursor.execute("SELECT project_id FROM synthesis_anchors WHERE id = ?", (anchor_id,))
            res = self.cursor.fetchone()
            if res:
                project_id = res['project_id']
                self.cursor.execute(
                    "INSERT OR IGNORE INTO project_tag_links (project_id, tag_id) VALUES (?, ?)",
                    (project_id, new_tag_id)
                )

            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            print(f"Error updating anchor: {e}")

    def delete_anchor(self, anchor_id):
        self.cursor.execute("DELETE FROM synthesis_anchors WHERE id = ?", (anchor_id,))
        self.conn.commit()

    def delete_anchors_by_item_link_id(self, item_id):
        """Deletes all virtual anchors linked to a specific item_id."""
        if not item_id:
            return
        self.cursor.execute("DELETE FROM synthesis_anchors WHERE item_link_id = ?", (item_id,))
        self.conn.commit()

    def get_anchor_details(self, anchor_id):
        self.cursor.execute("""
            SELECT a.*, t.name as tag_name, t.id as tag_id
            FROM synthesis_anchors a
            LEFT JOIN synthesis_tags t ON a.tag_id = t.id
            WHERE a.id = ?
        """, (anchor_id,))
        return self._rowdict(self.cursor.fetchone())

    def get_anchor_by_id(self, anchor_id):
        self.cursor.execute("SELECT id FROM synthesis_anchors WHERE id = ?", (anchor_id,))
        return self._rowdict(self.cursor.fetchone())

    def get_anchors_for_project(self, project_id):
        self.cursor.execute(
            "SELECT * FROM synthesis_anchors WHERE project_id = ?", (project_id,)
        )
        return self._map_rows(self.cursor.fetchall())

    def get_anchors_for_tag(self, tag_id):
        self.cursor.execute("""
            SELECT a.* FROM synthesis_anchors a
            JOIN anchor_tag_links l ON a.id = l.anchor_id
            WHERE l.tag_id = ?
        """, (tag_id,))
        return self._map_rows(self.cursor.fetchall())

    # --- Synthesis Tab Functions ---

    def get_tags_with_counts(self, project_id):
        sql = """
            SELECT 
                t.id, 
                t.name, 
                COUNT(a.id) as anchor_count
            FROM synthesis_tags t
            LEFT JOIN project_tag_links ptl ON t.id = ptl.tag_id
            LEFT JOIN synthesis_anchors a ON t.id = a.tag_id AND a.project_id = ?
            WHERE ptl.project_id = ? OR a.project_id = ?
            GROUP BY t.id, t.name
            ORDER BY t.name
        """
        self.cursor.execute(sql, (project_id, project_id, project_id))
        return self._map_rows(self.cursor.fetchall())

    def get_anchors_for_tag_with_context(self, tag_id, project_id):
        """
        Modified to accept project_id and join with reading_driving_questions
        to get the item type (e.g., 'term', 'proposition').
        """
        sql = """
            SELECT 
                a.id, 
                a.selected_text, 
                a.comment,
                a.item_link_id,
                r.id as reading_id,
                r.title as reading_title,
                r.nickname as reading_nickname,
                o.id as outline_id,
                o.section_title as outline_title,
                dq.type as item_type
            FROM synthesis_anchors a
            JOIN anchor_tag_links l ON a.id = l.anchor_id
            LEFT JOIN readings r ON a.reading_id = r.id
            LEFT JOIN reading_outline o ON a.outline_id = o.id
            LEFT JOIN reading_driving_questions dq ON a.item_link_id = dq.id
            WHERE l.tag_id = ? AND a.project_id = ?
            ORDER BY r.display_order, o.display_order, a.id
        """
        self.cursor.execute(sql, (tag_id, project_id))
        return self._map_rows(self.cursor.fetchall())

    def get_anchors_for_tag_simple(self, tag_id):
        sql = """
            SELECT a.id, a.selected_text, a.comment
            FROM synthesis_anchors a
            JOIN anchor_tag_links l ON a.id = l.anchor_id
            WHERE l.tag_id = ?
            ORDER BY a.id
        """
        self.cursor.execute(sql, (tag_id,))
        return self._map_rows(self.cursor.fetchall())

    # --- Tag Management Functions (now global) ---
    def rename_tag(self, tag_id, new_name):
        """Renames a tag globally. Checks for uniqueness conflict."""
        try:
            self.cursor.execute(
                "UPDATE synthesis_tags SET name = ? WHERE id = ?",
                (new_name, tag_id)
            )
            self.conn.commit()
        except sqlite3.IntegrityError:
            raise Exception(f"A tag named '{new_name}' already exists.")

    def delete_tag_and_anchors(self, tag_id):
        try:
            self.cursor.execute("SELECT anchor_id FROM anchor_tag_links WHERE tag_id = ?", (tag_id,))
            anchor_ids = [row[0] for row in self.cursor.fetchall()]

            if anchor_ids:
                self.cursor.executemany(
                    "DELETE FROM synthesis_anchors WHERE id = ?",
                    [(aid,) for aid in anchor_ids]
                )

            self.cursor.execute("DELETE FROM project_tag_links WHERE tag_id = ?", (tag_id,))

            self.cursor.execute("DELETE FROM synthesis_tags WHERE id = ?", (tag_id,))

            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            print(f"Error deleting tag and anchors: {e}")
            raise

    def merge_tags(self, source_tag_id, target_tag_id):
        """Merges one tag into another, updating all anchors and links."""
        try:
            self.cursor.execute(
                "UPDATE synthesis_anchors SET tag_id = ? WHERE tag_id = ?",
                (target_tag_id, source_tag_id)
            )
            # --- FIX: Typo was here ---
            self.cursor.execute(
                "UPDATE OR IGNORE anchor_tag_links SET tag_id = ? WHERE tag_id = ?",
                (target_tag_id, source_tag_id)
            )
            # --- END FIX ---
            self.cursor.execute(
                "DELETE FROM anchor_tag_links WHERE tag_id = ?", (source_tag_id,)
            )
            self.cursor.execute(
                "UPDATE OR IGNORE project_tag_links SET tag_id = ? WHERE tag_id = ?",
                (target_tag_id, source_tag_id)
            )
            self.cursor.execute(
                "DELETE FROM project_tag_links WHERE tag_id = ?", (source_tag_id,)
            )
            self.cursor.execute("DELETE FROM synthesis_tags WHERE id = ?", (source_tag_id,))
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            raise Exception(f"Failed to merge tags: {e}")