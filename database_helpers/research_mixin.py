# database_helpers/research_mixin.py
import sqlite3


class ResearchMixin:
    """
    Mixin for managing Research tab nodes and memos.
    """

    # --- Node CRUD ---

    def get_research_nodes(self, project_id):
        """Gets all research nodes for a project, flat list."""
        self.cursor.execute("""
            SELECT * FROM research_nodes
            WHERE project_id = ?
            ORDER BY display_order, id
        """, (project_id,))
        return self._map_rows(self.cursor.fetchall())

    def get_research_node_details(self, node_id):
        """Gets a single node's full data."""
        self.cursor.execute("SELECT * FROM research_nodes WHERE id = ?", (node_id,))
        return self._rowdict(self.cursor.fetchone())

    def _get_next_research_order(self, project_id, parent_id):
        if parent_id is None:
            self.cursor.execute(
                "SELECT COALESCE(MAX(display_order), -1) FROM research_nodes WHERE project_id = ? AND parent_id IS NULL",
                (project_id,))
        else:
            self.cursor.execute(
                "SELECT COALESCE(MAX(display_order), -1) FROM research_nodes WHERE project_id = ? AND parent_id = ?",
                (project_id, parent_id))
        return (self.cursor.fetchone()[0] or -1) + 1

    def add_research_node(self, project_id, parent_id, node_type, title):
        """Creates a new research node."""
        new_order = self._get_next_research_order(project_id, parent_id)
        self.cursor.execute("""
            INSERT INTO research_nodes (project_id, parent_id, type, title, display_order)
            VALUES (?, ?, ?, ?, ?)
        """, (project_id, parent_id, node_type, title, new_order))
        self.conn.commit()
        return self.cursor.lastrowid

    def update_research_node_field(self, node_id, field, value):
        """Updates a specific field for a node."""
        allowed_fields = [
            'title', 'problem_statement', 'scope', 'frameworks', 'key_terms',
            'working_thesis', 'open_issues', 'common_questions', 'agreements',
            'disagreements', 'synthesis', 'role', 'evidence', 'contradictions',
            'preliminary_conclusion', 'section_purpose', 'section_notes',
            'pdf_node_id'
        ]
        if field not in allowed_fields:
            print(f"Error: Invalid field '{field}' for research_nodes.")
            return

        query = f"UPDATE research_nodes SET {field} = ? WHERE id = ?"
        self.cursor.execute(query, (value, node_id))
        self.conn.commit()

    def delete_research_node(self, node_id):
        """Deletes a node (and cascading children/memos)."""
        self.cursor.execute("DELETE FROM research_nodes WHERE id = ?", (node_id,))
        self.conn.commit()

    def update_research_node_order(self, ordered_ids):
        """Updates display_order for a list of sibling IDs."""
        for i, node_id in enumerate(ordered_ids):
            self.cursor.execute("UPDATE research_nodes SET display_order = ? WHERE id = ?", (i, node_id))
        self.conn.commit()

    # --- PDF Linking (Many-to-Many) ---
    def add_research_pdf_link(self, research_node_id, pdf_node_id):
        """Links a PDF node to a research node."""
        try:
            self.cursor.execute(
                "INSERT INTO research_node_pdf_links (research_node_id, pdf_node_id) VALUES (?, ?)",
                (research_node_id, pdf_node_id)
            )
            self.conn.commit()
        except sqlite3.IntegrityError:
            pass  # Already exists

    def remove_research_pdf_link(self, research_node_id, pdf_node_id):
        """Removes a PDF link."""
        self.cursor.execute(
            "DELETE FROM research_node_pdf_links WHERE research_node_id = ? AND pdf_node_id = ?",
            (research_node_id, pdf_node_id)
        )
        self.conn.commit()

    def get_research_pdf_links(self, research_node_id):
        """Gets all linked PDF nodes for a research node."""
        self.cursor.execute("""
            SELECT n.*, l.research_node_id 
            FROM pdf_nodes n
            JOIN research_node_pdf_links l ON n.id = l.pdf_node_id
            WHERE l.research_node_id = ?
        """, (research_node_id,))
        return self._map_rows(self.cursor.fetchall())

    # --- NEW: Terminology Linking (Many-to-Many) ---
    def add_research_term_link(self, research_node_id, terminology_id):
        """Links a term to a research node."""
        try:
            self.cursor.execute(
                "INSERT INTO research_node_terms (research_node_id, terminology_id) VALUES (?, ?)",
                (research_node_id, terminology_id)
            )
            self.conn.commit()
        except sqlite3.IntegrityError:
            pass

    def remove_research_term_link(self, research_node_id, terminology_id):
        """Removes a term link."""
        self.cursor.execute(
            "DELETE FROM research_node_terms WHERE research_node_id = ? AND terminology_id = ?",
            (research_node_id, terminology_id)
        )
        self.conn.commit()

    def get_research_term_links(self, research_node_id):
        """Gets all linked terms for a research node."""
        self.cursor.execute("""
            SELECT t.id, t.term, t.meaning 
            FROM project_terminology t
            JOIN research_node_terms l ON t.id = l.terminology_id
            WHERE l.research_node_id = ?
            ORDER BY t.term
        """, (research_node_id,))
        return self._map_rows(self.cursor.fetchall())

    # --- Memo CRUD ---

    def get_research_memos(self, node_id):
        """Gets all memos for a node."""
        self.cursor.execute("""
            SELECT * FROM research_memos 
            WHERE node_id = ? 
            ORDER BY created_at DESC
        """, (node_id,))
        return self._map_rows(self.cursor.fetchall())

    def add_research_memo(self, node_id, title, content=""):
        """Adds a new memo."""
        self.cursor.execute("""
            INSERT INTO research_memos (node_id, title, content)
            VALUES (?, ?, ?)
        """, (node_id, title, content))
        self.conn.commit()
        return self.cursor.lastrowid

    def update_research_memo(self, memo_id, title, content):
        """Updates a memo."""
        self.cursor.execute("""
            UPDATE research_memos 
            SET title = ?, content = ?
            WHERE id = ?
        """, (title, content, memo_id))
        self.conn.commit()

    def delete_research_memo(self, memo_id):
        """Deletes a memo."""
        self.cursor.execute("DELETE FROM research_memos WHERE id = ?", (memo_id,))
        self.conn.commit()