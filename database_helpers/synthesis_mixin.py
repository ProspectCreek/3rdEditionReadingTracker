# prospectcreek/3rdeditionreadingtracker/3rdEditionReadingTracker-0eada8809e03f78f9e304f58f06c5f5a03a32c4f/database_helpers/synthesis_mixin.py
class SynthesisMixin:

    def get_all_tags(self):
        self.cursor.execute("SELECT id, name FROM synthesis_tags ORDER BY name")
        return self.cursor.fetchall()

    def get_project_tags(self, project_id):
        self.cursor.execute("""
            SELECT t.id, t.name 
            FROM synthesis_tags t
            JOIN project_tag_links ptl ON t.id = ptl.tag_id
            WHERE ptl.project_id = ?
            ORDER BY t.name
        """, (project_id,))
        return self.cursor.fetchall()

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
        try:
            self.cursor.execute("INSERT INTO synthesis_tags (name) VALUES (?)", (name,))
            self.conn.commit()
            return self.cursor.lastrowid
        except Exception as e:
            print(f"Error in add_tag: {e}")
            self.conn.rollback()
            return None

    def update_tag(self, tag_id, name):
        try:
            self.cursor.execute("UPDATE synthesis_tags SET name = ? WHERE id = ?", (name, tag_id))
            self.conn.commit()
        except Exception as e:
            print(f"Error in update_tag: {e}")
            self.conn.rollback()

    def delete_tag(self, tag_id):
        try:
            # Anchor links and project links will be deleted by CASCADE
            self.cursor.execute("DELETE FROM synthesis_tags WHERE id = ?", (tag_id,))
            self.conn.commit()
        except Exception as e:
            print(f"Error in delete_tag: {e}")
            self.conn.rollback()

    def get_anchors_for_tag(self, project_id, tag_id):
        self.cursor.execute("""
            SELECT a.* FROM synthesis_anchors a
            JOIN anchor_tag_links l ON a.id = l.anchor_id
            WHERE a.project_id = ? AND l.tag_id = ?
        """, (project_id, tag_id))
        return self.cursor.fetchall()

    def get_anchors_and_tags_for_project(self, project_id):
        # Get all tags for the project
        tags = self.get_project_tags(project_id)
        tags_dict = {tag['id']: dict(tag) for tag in tags}

        # Get all anchors for the project
        self.cursor.execute("""
            SELECT id, reading_id, outline_id, selected_text, comment, unique_doc_id, item_link_id 
            FROM synthesis_anchors 
            WHERE project_id = ?
        """, (project_id,))
        anchors_raw = self.cursor.fetchall()

        anchors_dict = {}
        for anchor in anchors_raw:
            anchor_id = anchor['id']
            anchor_data = dict(anchor)

            # --- FIX: Check for virtual anchors and format them for display ---
            if anchor['item_link_id']:
                # This is a virtual anchor, let's get the DQ text
                self.cursor.execute("SELECT nickname, question_text FROM reading_driving_questions WHERE id = ?",
                                    (anchor['item_link_id'],))
                dq_data = self.cursor.fetchone()
                if dq_data:
                    display_text = dq_data['nickname'] if dq_data['nickname'] else dq_data['question_text']
                    # Overwrite 'selected_text' with the DQ text for display
                    anchor_data['selected_text'] = f"Driving Question: {display_text}"
                    anchor_data['comment'] = ""  # Clear comment
                else:
                    # DQ was deleted, but anchor remains?
                    anchor_data['selected_text'] = "Orphaned Driving Question"
            # --- END FIX ---

            # Get links for this anchor
            self.cursor.execute("SELECT tag_id FROM anchor_tag_links WHERE anchor_id = ?", (anchor_id,))
            anchor_data['tags'] = [row['tag_id'] for row in self.cursor.fetchall()]

            anchors_dict[anchor_id] = anchor_data

        return {'tags': tags_dict, 'anchors': anchors_dict}

    def create_anchor(self, project_id, reading_id, outline_id, tag_id, unique_doc_id, selected_text, comment):
        try:
            self.cursor.execute("""
                INSERT INTO synthesis_anchors 
                (project_id, reading_id, outline_id, tag_id, unique_doc_id, selected_text, comment)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (project_id, reading_id, outline_id, tag_id, unique_doc_id, selected_text, comment))
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
        try:
            self.cursor.execute("""
                UPDATE synthesis_anchors SET
                selected_text = ?,
                comment = ?
                WHERE id = ?
            """, (data['selected_text'], data['comment'], anchor_id))

            # Handle tag links
            self.cursor.execute("DELETE FROM anchor_tag_links WHERE anchor_id = ?", (anchor_id,))
            if data.get('tags'):
                for tag_id in data['tags']:
                    self.cursor.execute("INSERT INTO anchor_tag_links (anchor_id, tag_id) VALUES (?, ?)",
                                        (anchor_id, tag_id))

            self.conn.commit()
        except Exception as e:
            print(f"Error in update_anchor: {e}")
            self.conn.rollback()

    def delete_anchor(self, anchor_id):
        try:
            # Links in anchor_tag_links will be deleted by CASCADE
            self.cursor.execute("DELETE FROM synthesis_anchors WHERE id = ?", (anchor_id,))
            self.conn.commit()
        except Exception as e:
            print(f"Error in delete_anchor: {e}")
            self.conn.rollback()