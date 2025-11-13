class MindmapMixin:
    # ----------------------- mindmaps -----------------------

    def get_mindmaps_for_project(self, project_id):
        """Gets all mindmaps for a project, ordered by name."""
        self.cursor.execute("""
            SELECT * FROM mindmaps 
            WHERE project_id = ? 
            ORDER BY display_order, name
        """, (project_id,))
        return self._map_rows(self.cursor.fetchall())

    def get_mindmap_details(self, mindmap_id):
        """Gets details for a single mindmap."""
        self.cursor.execute("SELECT * FROM mindmaps WHERE id = ?", (mindmap_id,))
        return self._rowdict(self.cursor.fetchone())

    def create_mindmap(self, project_id, name, defaults=None):
        """Creates a new mindmap and returns its ID."""
        if defaults is None:
            defaults = {}

        self.cursor.execute("SELECT COALESCE(MAX(display_order), -1) FROM mindmaps WHERE project_id = ?", (project_id,))
        new_order = (self.cursor.fetchone()[0] or -1) + 1

        self.cursor.execute("""
            INSERT INTO mindmaps (project_id, name, display_order, 
                                  default_font_family, default_font_size, 
                                  default_font_weight, default_font_slant)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            project_id, name, new_order,
            defaults.get('family'), defaults.get('size'),
            defaults.get('weight'), defaults.get('slant')
        ))
        self.conn.commit()
        return self.cursor.lastrowid

    def rename_mindmap(self, mindmap_id, new_name):
        self.cursor.execute("UPDATE mindmaps SET name = ? WHERE id = ?", (new_name, mindmap_id))
        self.conn.commit()

    def delete_mindmap(self, mindmap_id):
        self.cursor.execute("DELETE FROM mindmaps WHERE id = ?", (mindmap_id,))
        self.conn.commit()

    def update_mindmap_defaults(self, mindmap_id, font_details):
        self.cursor.execute("""
            UPDATE mindmaps 
            SET default_font_family = ?, default_font_size = ?, 
                default_font_weight = ?, default_font_slant = ?
            WHERE id = ?
        """, (
            font_details.get('family'), font_details.get('size'),
            font_details.get('weight'), font_details.get('slant'),
            mindmap_id
        ))
        self.conn.commit()

    def get_mindmap_data(self, mindmap_id):
        """Fetches all nodes and edges for a given mindmap ID."""
        nodes = []
        edges = []

        self.cursor.execute("SELECT * FROM mindmap_nodes WHERE mindmap_id = ?", (mindmap_id,))
        nodes = self._map_rows(self.cursor.fetchall())

        self.cursor.execute("SELECT * FROM mindmap_edges WHERE mindmap_id = ?", (mindmap_id,))
        edges = self._map_rows(self.cursor.fetchall())

        return {"nodes": nodes, "edges": edges}

    def save_mindmap_data(self, mindmap_id, nodes, edges):
        """Saves a complete snapshot of a mindmap (nodes and edges)."""
        try:
            self.cursor.execute("SELECT node_id_text FROM mindmap_nodes WHERE mindmap_id = ?", (mindmap_id,))
            existing_node_ids = {row[0] for row in self.cursor.fetchall()}

            node_ids_to_keep = set()

            for node_data in nodes:
                node_id_text = str(node_data['id'])
                node_ids_to_keep.add(node_id_text)

                params = {
                    'mindmap_id': mindmap_id,
                    'node_id_text': node_id_text,
                    'x': node_data['x'], 'y': node_data['y'],
                    'width': node_data['width'], 'height': node_data['height'],
                    'text': node_data['text'],
                    'shape_type': node_data.get('shape_type'),
                    'fill_color': node_data.get('fill_color'),
                    'outline_color': node_data.get('outline_color'),
                    'text_color': node_data.get('text_color'),
                    'font_family': node_data.get('font_family'),
                    'font_size': node_data.get('font_size'),
                    'font_weight': node_data.get('font_weight'),
                    'font_slant': node_data.get('font_slant')
                }

                if node_id_text in existing_node_ids:
                    self.cursor.execute("""
                        UPDATE mindmap_nodes SET
                        x=:x, y=:y, width=:width, height=:height, text=:text, shape_type=:shape_type,
                        fill_color=:fill_color, outline_color=:outline_color, text_color=:text_color,
                        font_family=:font_family, font_size=:font_size, font_weight=:font_weight, font_slant=:font_slant
                        WHERE mindmap_id=:mindmap_id AND node_id_text=:node_id_text
                    """, params)
                else:
                    self.cursor.execute("""
                        INSERT INTO mindmap_nodes (
                        mindmap_id, node_id_text, x, y, width, height, text, shape_type,
                        fill_color, outline_color, text_color, font_family, font_size,
                        font_weight, font_slant
                        ) VALUES (
                        :mindmap_id, :node_id_text, :x, :y, :width, :height, :text, :shape_type,
                        :fill_color, :outline_color, :text_color, :font_family, :font_size,
                        :font_weight, :font_slant
                        )
                    """, params)

            nodes_to_delete = existing_node_ids - node_ids_to_keep
            if nodes_to_delete:
                for node_id_text in nodes_to_delete:
                    self.cursor.execute(
                        "DELETE FROM mindmap_nodes WHERE mindmap_id = ? AND node_id_text = ?",
                        (mindmap_id, node_id_text)
                    )

            self.cursor.execute("DELETE FROM mindmap_edges WHERE mindmap_id = ?", (mindmap_id,))

            edge_insert_params = []
            for i, edge_data in enumerate(edges):
                params = {
                    'mindmap_id': mindmap_id,
                    'from_node_id_text': str(edge_data['from_node_id']),
                    'to_node_id_text': str(edge_data['to_node_id']),
                    'color': edge_data.get('color'),
                    'width': edge_data.get('width'),
                    'style': edge_data.get('style'),
                    'arrow_style': edge_data.get('arrow_style')
                }
                edge_insert_params.append(params)

            if edge_insert_params:
                self.cursor.executemany("""
                    INSERT INTO mindmap_edges (
                        mindmap_id, from_node_id_text, to_node_id_text, color, 
                        width, style, arrow_style
                    ) VALUES (
                        :mindmap_id, :from_node_id_text, :to_node_id_text, :color, 
                        :width, :style, :arrow_style
                    )
                """, edge_insert_params)

            self.conn.commit()

        except Exception as e:
            self.conn.rollback()
            print(f"Error saving mindmap data: {e}")
            raise