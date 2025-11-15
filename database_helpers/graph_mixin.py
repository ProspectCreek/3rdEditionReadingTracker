# prospectcreek/3rdeditionreadingtracker/3rdEditionReadingTracker-0eada8809e03f78f9e304f58f06c5f5a03a32c4f/database_helpers/graph_mixin.py
class GraphMixin:
    # --- Graph Data Functions ---
    def get_graph_data(self, project_id):
        """
        Gets all readings, tags, and the connections between them
        for a specific project.
        """
        # --- FIX: Use CASE to handle empty nickname string ---
        readings_sql = """
            SELECT id, title, author, 
                   CASE WHEN nickname IS NOT NULL AND nickname != '' THEN nickname ELSE title END as name 
            FROM readings 
            WHERE project_id = ?
        """
        self.cursor.execute(readings_sql, (project_id,))
        readings = self._map_rows(self.cursor.fetchall())

        tags_sql = """
            SELECT DISTINCT t.id, t.name 
            FROM synthesis_tags t
            LEFT JOIN project_tag_links ptl ON t.id = ptl.tag_id
            LEFT JOIN synthesis_anchors a ON a.project_id = ptl.project_id AND a.tag_id = t.id
            WHERE ptl.project_id = ? OR a.project_id = ?
            GROUP BY t.id, t.name
        """
        self.cursor.execute(tags_sql, (project_id, project_id))
        tags = self._map_rows(self.cursor.fetchall())

        # --- FIX: Join on anchor_tag_links to get all text anchor links ---
        edges_sql = """
            SELECT DISTINCT a.reading_id, atl.tag_id
            FROM synthesis_anchors a
            JOIN anchor_tag_links atl ON a.id = atl.anchor_id
            WHERE a.project_id = ? AND a.item_link_id IS NULL
        """
        # --- END FIX ---
        self.cursor.execute(edges_sql, (project_id,))
        edges = self._map_rows(self.cursor.fetchall())

        return {"readings": readings, "tags": tags, "edges": edges}

    def get_graph_data_full(self, project_id):
        """
        Gets all readings, tags, and *all* anchors (text and virtual)
        for a specific project.
        """
        # 1. Get Readings
        readings_sql = """
            SELECT id, title, author, 
                   CASE WHEN nickname IS NOT NULL AND nickname != '' THEN nickname ELSE title END as name 
            FROM readings 
            WHERE project_id = ?
        """
        self.cursor.execute(readings_sql, (project_id,))
        readings = self._map_rows(self.cursor.fetchall())

        # 2. Get Tags
        tags_sql = """
            SELECT DISTINCT t.id, t.name 
            FROM synthesis_tags t
            LEFT JOIN project_tag_links ptl ON t.id = ptl.tag_id
            LEFT JOIN synthesis_anchors a ON a.project_id = ptl.project_id AND a.tag_id = t.id
            WHERE ptl.project_id = ? OR a.project_id = ?
            GROUP BY t.id, t.name
        """
        self.cursor.execute(tags_sql, (project_id, project_id, project_id))
        tags = self._map_rows(self.cursor.fetchall())

        # 3. Get text-based anchor edges (Reading <-> Tag)
        edges_sql = """
            SELECT DISTINCT a.reading_id, atl.tag_id
            FROM synthesis_anchors a
            JOIN anchor_tag_links atl ON a.id = atl.anchor_id
            WHERE a.project_id = ? AND a.item_link_id IS NULL
        """
        self.cursor.execute(edges_sql, (project_id,))
        edges = self._map_rows(self.cursor.fetchall())

        # 4. Get "Virtual Anchors" (DQs, Terms, etc.)
        # This query gets all virtual anchors and their linked tags
        virtual_anchors_sql = """
            SELECT 
                a.id, 
                a.reading_id, 
                atl.tag_id, 
                a.item_link_id, 
                a.selected_text,
                a.item_type
            FROM synthesis_anchors a
            LEFT JOIN anchor_tag_links atl ON a.id = atl.anchor_id
            WHERE a.project_id = ? AND a.item_link_id IS NOT NULL
        """
        self.cursor.execute(virtual_anchors_sql, (project_id,))
        virtual_anchors = self._map_rows(self.cursor.fetchall())

        return {
            "readings": readings,
            "tags": tags,
            "edges": edges,
            "virtual_anchors": virtual_anchors
        }

    def get_global_graph_data(self):
        """
        Gets all tags, projects, and the links between them for the
        global connections graph.
        """
        # 1. Get all tags
        self.cursor.execute("SELECT id, name FROM synthesis_tags")
        tags = self._map_rows(self.cursor.fetchall())

        # Get project counts for tags (for scaling)
        self.cursor.execute("""
            SELECT atl.tag_id, COUNT(DISTINCT a.project_id) as project_count
            FROM synthesis_anchors a
            JOIN anchor_tag_links atl ON a.id = atl.anchor_id
            GROUP BY atl.tag_id
        """)
        counts = {row['tag_id']: row['project_count'] for row in self.cursor.fetchall()}

        for tag in tags:
            tag['project_count'] = counts.get(tag['id'], 0)

        # 2. Get all projects
        self.cursor.execute("SELECT id, name FROM items WHERE type = 'project' ORDER BY name")
        projects = self._map_rows(self.cursor.fetchall())

        # 3. Get all edges
        self.cursor.execute("""
            SELECT DISTINCT a.project_id, atl.tag_id 
            FROM synthesis_anchors a
            JOIN anchor_tag_links atl ON a.id = atl.anchor_id
            WHERE atl.tag_id IS NOT NULL
        """)
        edges = self._map_rows(self.cursor.fetchall())

        return {"tags": tags, "projects": projects, "edges": edges}


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
                i.name as project_name,
                a.item_link_id,
                a.item_type
            FROM synthesis_anchors a
            JOIN anchor_tag_links atl ON a.id = atl.anchor_id
            JOIN synthesis_tags t ON atl.tag_id = t.id
            LEFT JOIN readings r ON a.reading_id = r.id
            LEFT JOIN items i ON a.project_id = i.id
            LEFT JOIN reading_outline o ON a.outline_id = o.id
            WHERE t.name = ?
            ORDER BY i.name, r.display_order, o.display_order, a.id
        """
        self.cursor.execute(sql, (tag_name,))
        return self._map_rows(self.cursor.fetchall())