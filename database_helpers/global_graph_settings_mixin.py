# prospectcreek/3rdeditionreadingtracker/database_helpers/global_graph_settings_mixin.py
import sqlite3


class GlobalGraphSettingsMixin:
    """
    Mixin for saving and loading GLOBAL graph customization settings,
    like node colors for projects and tags.
    """

    GLOBAL_NODE_TYPES = ['project', 'tag']

    # --- NEW: Modern Pastel Palette ---
    DEFAULT_GLOBAL_COLORS = {
        'project': '#BFDBFE',  # Soft Blue (Matches Reading color)
        'tag': '#A7F3D0'       # Soft Mint
    }
    # --- END NEW ---

    def create_global_graph_settings_table(self):
        """
        Creates the global_graph_settings table.
        This table is NOT project-specific.
        """
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS global_graph_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_type TEXT NOT NULL,
            item_id INTEGER NOT NULL,
            color_hex TEXT NOT NULL,
            UNIQUE(item_type, item_id)
        )
        """)

    def get_global_graph_settings(self):
        """
        Gets all global graph settings and returns a dictionary
        of { 'project_colors': {project_id: color}, 'tag_color': color }
        """
        settings = {
            'project_colors': {},
            'tag_color': self.DEFAULT_GLOBAL_COLORS['tag']
        }

        self.cursor.execute("SELECT item_type, item_id, color_hex FROM global_graph_settings")
        rows = self.cursor.fetchall()

        for row in rows:
            if row['item_type'] == 'project':
                settings['project_colors'][row['item_id']] = row['color_hex']
            elif row['item_type'] == 'tag':
                # For now, we only support one global color for all tags
                settings['tag_color'] = row['color_hex']

        return settings

    def save_global_graph_setting(self, item_type, item_id, color_hex):
        """
        Saves or updates a single color setting for the global graph.
        'item_id' is the project_id for 'project' type, or 0 for 'tag' type.
        """
        if item_type not in self.GLOBAL_NODE_TYPES:
            print(f"Error: Invalid global node_type '{item_type}'")
            return

        try:
            self.cursor.execute("""
                INSERT INTO global_graph_settings (item_type, item_id, color_hex)
                VALUES (?, ?, ?)
                ON CONFLICT(item_type, item_id) DO UPDATE SET
                color_hex = excluded.color_hex
            """, (item_type, item_id, color_hex))
            self.conn.commit()
        except Exception as e:
            print(f"Error saving global graph setting: {e}")
            self.conn.rollback()