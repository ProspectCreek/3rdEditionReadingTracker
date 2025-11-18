# prospectcreek/3rdeditionreadingtracker/database_helpers/graph_settings_mixin.py
import sqlite3
import json


class GraphSettingsMixin:
    """
    Mixin for saving and loading graph customization settings,
    like node colors, for each project.
    """

    NODE_TYPES = [
        'reading', 'tag', 'dq', 'term',
        'proposition', 'argument', 'theory', 'default'
    ]

    # --- NEW: Modern Pastel Palette ---
    DEFAULT_COLORS = {
        'reading': '#BFDBFE',      # Soft Blue
        'tag': '#A7F3D0',          # Soft Mint
        'proposition': '#FDE68A',  # Soft Yellow
        'dq': '#FECACA',           # Soft Red
        'term': '#FED7AA',         # Soft Orange
        'argument': '#C7D2FE',     # Soft Indigo
        'theory': '#E9D5FF',       # Soft Purple
        'default': '#E5E7EB'       # Cool Gray
    }
    # --- END NEW ---

    def create_graph_settings_table(self):
        """
        Creates the graph_settings table.
        """
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS graph_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            node_type TEXT NOT NULL,
            color_hex TEXT NOT NULL,
            FOREIGN KEY (project_id) REFERENCES items(id) ON DELETE CASCADE,
            UNIQUE(project_id, node_type)
        )
        """)

    def get_graph_settings(self, project_id):
        """
        Gets all graph settings for a project and returns a dictionary
        of node_type -> color_hex.
        """
        settings = self.DEFAULT_COLORS.copy()

        self.cursor.execute("""
            SELECT node_type, color_hex FROM graph_settings WHERE project_id = ?
        """, (project_id,))

        rows = self.cursor.fetchall()
        for row in rows:
            if row['node_type'] in self.NODE_TYPES:
                settings[row['node_type']] = row['color_hex']

        return settings

    def save_graph_setting(self, project_id, node_type, color_hex):
        """
        Saves or updates a single color setting for a project.
        """
        if node_type not in self.NODE_TYPES:
            print(f"Error: Invalid node_type '{node_type}'")
            return

        try:
            self.cursor.execute("""
                INSERT INTO graph_settings (project_id, node_type, color_hex)
                VALUES (?, ?, ?)
                ON CONFLICT(project_id, node_type) DO UPDATE SET
                color_hex = excluded.color_hex
            """, (project_id, node_type, color_hex))
            self.conn.commit()
        except Exception as e:
            print(f"Error saving graph setting: {e}")
            self.conn.rollback()