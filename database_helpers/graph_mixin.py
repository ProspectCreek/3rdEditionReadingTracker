class GraphMixin:
    # --- Graph Data Functions ---
    def get_graph_data(self, project_id):
        """
        Gets all readings, tags, and the connections between them
        for a specific project.
        """
        readings_sql = "SELECT id, title, author, COALESCE(nickname, title) as name FROM readings WHERE project_id = ?"
        self.cursor.execute(readings_sql, (project_id,))
        readings = self._map_rows(self.cursor.fetchall())

        tags_sql = """
            SELECT DISTINCT t.id, t.name 
            FROM synthesis_tags t
            LEFT JOIN project_tag_links ptl ON t.id = ptl.tag_id
            LEFT JOIN synthesis_anchors a ON t.id = a.tag_id AND a.project_id = ?
            WHERE ptl.project_id = ? OR a.project_id = ?
        """
        self.cursor.execute(tags_sql, (project_id, project_id, project_id))
        tags = self._map_rows(self.cursor.fetchall())

        edges_sql = """
            SELECT DISTINCT reading_id, tag_id
            FROM synthesis_anchors
            WHERE project_id = ? AND tag_id IS NOT NULL
        """
        self.cursor.execute(edges_sql, (project_id,))
        edges = self._map_rows(self.cursor.fetchall())

        return {"readings": readings, "tags": tags, "edges": edges}

    # --- THIS IS THE FIX ---
    def get_global_graph_data(self):
        """
        Gets all tags, projects, and the links between them for the
        global connections graph.
        This bypasses the project_tag_links table and queries
        the anchors directly for maximum reliability.
        """
        # 1. Get all tags
        self.cursor.execute("""
            SELECT id, name FROM synthesis_tags
        """)
        tags = self._map_rows(self.cursor.fetchall())

        # Get project counts for tags (for scaling)
        self.cursor.execute("""
            SELECT tag_id, COUNT(DISTINCT project_id) as project_count
            FROM synthesis_anchors
            WHERE tag_id IS NOT NULL
            GROUP BY tag_id
        """)
        counts = {row['tag_id']: row['project_count'] for row in self.cursor.fetchall()}

        # Add project_count to tag data
        for tag in tags:
            tag['project_count'] = counts.get(tag['id'], 0)

        # 2. Get all projects
        self.cursor.execute("SELECT id, name FROM items WHERE type = 'project' ORDER BY name")
        projects = self._map_rows(self.cursor.fetchall())

        # 3. Get all edges by querying the source of truth: synthesis_anchors
        self.cursor.execute("""
            SELECT DISTINCT project_id, tag_id 
            FROM synthesis_anchors
            WHERE tag_id IS NOT NULL
        """)
        edges = self._map_rows(self.cursor.fetchall())

        return {"tags": tags, "projects": projects, "edges": edges}

    # --- END FIX ---

    def get_global_anchors_for_tag_name(self, tag_name):
        """
        Gets all anchors matching a tag name from all projects,
        joining with reading and project info for context.
        """
        sql = """
            SELECT 
                a.id, 
                a.selected_text, 
                a.comment,
                r.id as reading_id,
                r.title as reading_title,
                r.nickname as reading_nickname,
                o.id as outline_id,
                o.section_title as outline_title,
                i.id as project_id,
                i.name as project_name
            FROM synthesis_anchors a
            JOIN synthesis_tags t ON a.tag_id = t.id
            LEFT JOIN readings r ON a.reading_id = r.id
            LEFT JOIN items i ON a.project_id = i.id
            LEFT JOIN reading_outline o ON a.outline_id = o.id
            WHERE t.name = ?
            ORDER BY i.name, r.display_order, o.display_order, a.id
        """
        self.cursor.execute(sql, (tag_name,))
        return self._map_rows(self.cursor.fetchall())