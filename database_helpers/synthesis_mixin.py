# prospectcreek/3rdeditionreadingtracker/database_helpers/synthesis_mixin.py
import sqlite3


class SynthesisMixin:

    # --- Tag Functions ---

    def get_all_tags(self):
        """Gets all tags in the entire database."""
        self.cursor.execute("SELECT id, name FROM synthesis_tags ORDER BY name")
        return self._map_rows(self.cursor.fetchall())

    def get_project_tags(self, project_id):
        """Gets all tags that are linked to a specific project."""
        self.cursor.execute("""
            SELECT t.id, t.name 
            FROM synthesis_tags t
            JOIN project_tag_links ptl ON t.id = ptl.tag_id
            WHERE ptl.project_id = ?
            ORDER BY t.name
        """, (project_id,))
        return self._map_rows(self.cursor.fetchall())

    def get_tags_with_counts(self, project_id):
        """
        Gets all tags for a project, with a count of how many anchors
        are linked to them *within that project*.
        """
        sql = """
            SELECT
                t.id,
                t.name,
                (SELECT COUNT(a.id) 
                 FROM synthesis_anchors a
                 JOIN anchor_tag_links atl ON a.id = atl.anchor_id
                 WHERE a.project_id = ? AND atl.tag_id = t.id) as anchor_count
            FROM synthesis_tags t
            JOIN project_tag_links ptl ON t.id = ptl.tag_id
            WHERE ptl.project_id = ?
            GROUP BY t.id, t.name
            ORDER BY t.name
        """
        self.cursor.execute(sql, (project_id, project_id))
        return self._map_rows(self.cursor.fetchall())

    def get_or_create_tag(self, tag_name, project_id):
        """
        Finds a tag by name or creates it, and links it to the project.
        Returns the tag's row.
        """
        try:
            # 1. Find tag
            self.cursor.execute("SELECT * FROM synthesis_tags WHERE name = ?", (tag_name,))
            tag = self._rowdict(self.cursor.fetchone())

            if not tag:
                # 2. Create tag if it doesn't exist
                self.cursor.execute("INSERT INTO synthesis_tags (name) VALUES (?)", (tag_name,))
                tag_id = self.cursor.lastrowid
                tag = {"id": tag_id, "name": tag_name}

            # 3. Link tag to project (does nothing if link already exists)
            self.cursor.execute("""
                INSERT OR IGNORE INTO project_tag_links (project_id, tag_id) 
                VALUES (?, ?)
            """, (project_id, tag['id']))

            self.conn.commit()
            return tag
        except Exception as e:
            self.conn.rollback()
            print(f"Error in get_or_create_tag: {e}")
            raise

    def add_project_tag(self, project_id, tag_id):
        try:
            self.cursor.execute("INSERT OR IGNORE INTO project_tag_links (project_id, tag_id) VALUES (?, ?)",
                                (project_id, tag_id))
            self.conn.commit()
        except Exception as e:
            print(f"Error in add_project_tag: {e}")
            self.conn.rollback()

    def remove_project_tag(self, project_id, tag_id):
        try:
            self.cursor.execute("DELETE FROM project_tag_links WHERE project_id = ? AND tag_id = ?",
                                (project_id, tag_id))
            self.conn.commit()
        except Exception as e:
            print(f"Error in remove_project_tag: {e}")
            self.conn.rollback()

    def add_tag(self, name):
        """DEPRECATED - Use get_or_create_tag instead."""
        try:
            self.cursor.execute("INSERT INTO synthesis_tags (name) VALUES (?)", (name,))
            self.conn.commit()
            return self.cursor.lastrowid
        except Exception as e:
            print(f"Error in add_tag: {e}")
            self.conn.rollback()
            return None

    def rename_tag(self, tag_id, name):
        """Renames a tag globally."""
        try:
            self.cursor.execute("UPDATE synthesis_tags SET name = ? WHERE id = ?", (name, tag_id))
            self.conn.commit()
        except Exception as e:
            print(f"Error in update_tag/rename_tag: {e}")
            self.conn.rollback()
            raise

    # Alias for compatibility
    update_tag = rename_tag

    def delete_tag_and_anchors(self, tag_id):
        """
        Deletes a tag, all its links, and all text anchors (non-virtual)
        that are now orphaned as a result.
        """
        try:
            # 1. Find all anchors linked *only* to this tag
            self.cursor.execute("""
                SELECT a.id, a.item_link_id
                FROM synthesis_anchors a
                JOIN anchor_tag_links atl ON a.id = atl.anchor_id
                WHERE atl.tag_id = ?
            """, (tag_id,))
            anchors_to_check = self._map_rows(self.cursor.fetchall())

            # 2. Delete the tag. This will cascade-delete all links
            # in anchor_tag_links and project_tag_links.
            self.cursor.execute("DELETE FROM synthesis_tags WHERE id = ?", (tag_id,))

            # 3. Re-check all affected anchors
            for anchor in anchors_to_check:
                anchor_id = anchor['id']
                item_link_id = anchor['item_link_id']

                # Check if this anchor has any *other* tags
                self.cursor.execute("SELECT COUNT(*) FROM anchor_tag_links WHERE anchor_id = ?", (anchor_id,))
                remaining_tag_count = self.cursor.fetchone()[0]

                if remaining_tag_count == 0 and item_link_id is None:
                    # This is a TEXT anchor (not virtual) and is now orphaned.
                    # Delete the anchor row itself.
                    self.cursor.execute("DELETE FROM synthesis_anchors WHERE id = ?", (anchor_id,))

            self.conn.commit()
        except Exception as e:
            print(f"Error in delete_tag_and_anchors: {e}")
            self.conn.rollback()

    def merge_tags(self, source_tag_id, target_tag_id):
        """Merges one tag into another, then deletes the source tag."""
        try:
            # 1. Re-link project_tag_links (ignore conflicts)
            self.cursor.execute("""
                UPDATE project_tag_links SET tag_id = ? WHERE tag_id = ?
            """, (target_tag_id, source_tag_id))
            # Clean up duplicates
            self.cursor.execute("""
                DELETE FROM project_tag_links 
                WHERE rowid NOT IN (
                    SELECT MIN(rowid) 
                    FROM project_tag_links 
                    GROUP BY project_id, tag_id
                )
            """)

            # 2. Re-link anchor_tag_links (ignore conflicts)
            self.cursor.execute("""
                UPDATE anchor_tag_links SET tag_id = ? WHERE tag_id = ?
            """, (target_tag_id, source_tag_id))
            # Clean up duplicates
            self.cursor.execute("""
                DELETE FROM anchor_tag_links 
                WHERE rowid NOT IN (
                    SELECT MIN(rowid) 
                    FROM anchor_tag_links 
                    GROUP BY anchor_id, tag_id
                )
            """)

            # 3. Delete the source tag
            self.cursor.execute("DELETE FROM synthesis_tags WHERE id = ?", (source_tag_id,))

            self.conn.commit()
        except sqlite3.IntegrityError:
            # This happens if a link already exists, safe to ignore and proceed
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            raise

    # --- Anchor Functions ---

    def get_anchor_by_id(self, anchor_id):
        """Checks if an anchor exists."""
        self.cursor.execute("SELECT id FROM synthesis_anchors WHERE id = ?", (anchor_id,))
        return self._rowdict(self.cursor.fetchone())

    def get_anchor_details(self, anchor_id):
        """Gets anchor details and ONE tag (for editing dialog)."""
        self.cursor.execute("""
            SELECT a.id, a.selected_text, a.comment, t.name as tag_name, t.id as tag_id
            FROM synthesis_anchors a
            LEFT JOIN anchor_tag_links atl ON a.id = atl.anchor_id
            LEFT JOIN synthesis_tags t ON atl.tag_id = t.id
            WHERE a.id = ?
            LIMIT 1
        """, (anchor_id,))
        return self._rowdict(self.cursor.fetchone())

    # ##################################################################
    # #
    # #                 --- NEW FUNCTION START ---
    # #
    # ##################################################################
    def get_anchor_navigation_details(self, anchor_id):
        """
        Gets all necessary IDs from an anchor for navigation.
        """
        self.cursor.execute("""
            SELECT 
                id,
                reading_id,
                outline_id,
                item_link_id,
                item_type
            FROM synthesis_anchors
            WHERE id = ?
        """, (anchor_id,))
        return self._rowdict(self.cursor.fetchone())

    # ##################################################################
    # #
    # #                 --- NEW FUNCTION END ---
    # #
    # ##################################################################

    def get_anchors_for_tag_simple(self, tag_id):
        """Gets simple anchor data for the ManageAnchorsDialog."""
        self.cursor.execute("""
            SELECT a.id, a.selected_text, a.comment
            FROM synthesis_anchors a
            JOIN anchor_tag_links atl ON a.id = atl.anchor_id
            WHERE atl.tag_id = ?
        """, (tag_id,))
        return self._map_rows(self.cursor.fetchall())

    def get_anchors_for_tag_with_context(self, tag_id, project_id):
        """
        Gets all anchors for a tag (in a project), joining with context
        like reading and outline titles, and the *content* of virtual anchors.
        """
        self.cursor.execute("""
            SELECT 
                a.id, a.project_id, a.reading_id, a.outline_id, 
                a.unique_doc_id, a.selected_text, a.comment, 
                a.item_link_id, a.item_type,
                r.title as reading_title,
                r.nickname as reading_nickname,
                o.section_title as outline_title,

                -- THIS IS THE FIX: Get nickname from the DQ table --
                dq.nickname, 

                dq.question_text as dq_question_text,
                dq.question_category as dq_definition,
                arg.claim_text as arg_claim_text
            FROM synthesis_anchors a
            JOIN anchor_tag_links l ON a.id = l.anchor_id
            LEFT JOIN readings r ON a.reading_id = r.id
            LEFT JOIN items i ON a.project_id = i.id
            LEFT JOIN reading_outline o ON a.outline_id = o.id
            LEFT JOIN reading_driving_questions dq ON a.item_link_id = dq.id
            LEFT JOIN reading_arguments arg ON a.item_link_id = arg.id AND a.item_type = 'argument'
            WHERE l.tag_id = ? AND a.project_id = ?
            ORDER BY r.display_order, o.display_order, a.id
        """, (tag_id, project_id))
        return self._map_rows(self.cursor.fetchall())

    def get_anchors_and_tags_for_project(self, project_id):
        """
        Gets all anchors and tags for a project, used by
        ReadingNotesTab to re-apply formatting.
        """
        # Get all tags for the project
        tags = self.get_project_tags(project_id)
        tags_dict = {tag['id']: dict(tag) for tag in tags}

        # Get all anchors for the project
        self.cursor.execute("""
            SELECT * FROM synthesis_anchors WHERE project_id = ?
        """, (project_id,))
        anchors_raw = self._map_rows(self.cursor.fetchall())

        anchors_dict = {}
        for anchor_data in anchors_raw:
            anchor_id = anchor_data['id']

            # Get links for this anchor
            self.cursor.execute("SELECT tag_id FROM anchor_tag_links WHERE anchor_id = ?", (anchor_id,))
            anchor_data['tags'] = [row['tag_id'] for row in self.cursor.fetchall()]

            # Get the first tag's name for tooltip (if available)
            first_tag_id = anchor_data['tags'][0] if anchor_data['tags'] else None
            if first_tag_id and first_tag_id in tags_dict:
                anchor_data['tag_name'] = tags_dict[first_tag_id]['name']
            else:
                anchor_data['tag_name'] = "Uncategorized"

            anchors_dict[anchor_id] = anchor_data

        return {'tags': tags_dict, 'anchors': anchors_dict}

    def create_anchor(self, project_id, reading_id, outline_id, tag_id, unique_doc_id, selected_text, comment,
                      item_link_id=None, item_type=None):
        """Creates a new text or virtual anchor and links its tag."""
        try:
            self.cursor.execute("""
                INSERT INTO synthesis_anchors 
                (project_id, reading_id, outline_id, tag_id, unique_doc_id, selected_text, comment, item_link_id, item_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (project_id, reading_id, outline_id, tag_id, unique_doc_id, selected_text, comment, item_link_id,
                  item_type))
            anchor_id = self.cursor.lastrowid

            # Also create the link in anchor_tag_links
            if tag_id:
                self.cursor.execute("""
                    INSERT INTO anchor_tag_links (anchor_id, tag_id) VALUES (?, ?)
                """, (anchor_id, tag_id))

            self.conn.commit()
            return anchor_id
        except Exception as e:
            print(f"Error in create_anchor: {e}")
            self.conn.rollback()
            return None

    def update_anchor(self, anchor_id, data):
        """Updates an anchor's comment and tag list."""
        try:
            self.cursor.execute("""
                UPDATE synthesis_anchors SET
                comment = ?
                WHERE id = ?
            """, (data.get('comment', ''), anchor_id))

            # Handle tag links
            self.cursor.execute("DELETE FROM anchor_tag_links WHERE anchor_id = ?", (anchor_id,))
            if data.get('tags'):
                for tag_id in data['tags']:
                    self.cursor.execute("INSERT INTO anchor_tag_links (anchor_id, tag_id) VALUES (?, ?)",
                                        (anchor_id, tag_id))

            # Update the (deprecated) single tag_id field for compatibility
            new_tag_id = data['tags'][0] if data.get('tags') else None
            self.cursor.execute("UPDATE synthesis_anchors SET tag_id = ? WHERE id = ?", (new_tag_id, anchor_id))

            self.conn.commit()
        except Exception as e:
            print(f"Error in update_anchor: {e}")
            self.conn.rollback()

    def delete_anchor(self, anchor_id):
        """Deletes a single anchor."""
        try:
            # Links in anchor_tag_links will be deleted by CASCADE
            self.cursor.execute("DELETE FROM synthesis_anchors WHERE id = ?", (anchor_id,))
            self.conn.commit()
        except Exception as e:
            print(f"Error in delete_anchor: {e}")
            self.conn.rollback()

    def delete_anchors_by_item_link_id(self, item_link_id):
        """Deletes all virtual anchors associated with a specific item."""
        try:
            self.cursor.execute("DELETE FROM synthesis_anchors WHERE item_link_id = ?", (item_link_id,))
            self.conn.commit()
        except Exception as e:
            print(f"Error in delete_anchors_by_item_link_id: {e}")
            self.conn.rollback()