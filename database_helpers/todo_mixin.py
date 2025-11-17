class TodoMixin:
    # ----------------------- NEW: To-Do List Functions -----------------------

    def get_project_todo_items(self, project_id):
        """Gets a list of all to-do items for a project, ordered."""
        self.cursor.execute("""
            SELECT id, display_name, is_checked
            FROM project_todo_list
            WHERE project_id = ?
            ORDER BY display_order, id
        """, (project_id,))
        return self._map_rows(self.cursor.fetchall())

    # --- ALIASES to prevent future errors ---
    get_project_todos = get_project_todo_items
    get_todo_items = get_project_todo_items
    # --- END ALIASES ---

    def get_todo_item_details(self, item_id):
        """Gets the full details for a single to-do item."""
        self.cursor.execute("SELECT * FROM project_todo_list WHERE id = ?", (item_id,))
        return self._rowdict(self.cursor.fetchone())

    def add_todo_item(self, project_id, data):
        """Adds a new to-do item."""
        self.cursor.execute(
            "SELECT COALESCE(MAX(display_order), -1) FROM project_todo_list WHERE project_id = ?",
            (project_id,)
        )
        new_order = (self.cursor.fetchone()[0] or -1) + 1

        self.cursor.execute("""
            INSERT INTO project_todo_list (project_id, display_name, task_html, notes_html, is_checked, display_order)
            VALUES (?, ?, ?, ?, 0, ?)
        """, (
            project_id,
            data.get('display_name'),
            data.get('task_html'),
            data.get('notes_html'),
            new_order
        ))
        self.conn.commit()
        return self.cursor.lastrowid

    def update_todo_item(self, item_id, data):
        """Updates the text content of a to-do item."""
        self.cursor.execute("""
            UPDATE project_todo_list
            SET display_name = ?, task_html = ?, notes_html = ?
            WHERE id = ?
        """, (
            data.get('display_name'),
            data.get('task_html'),
            data.get('notes_html'),
            item_id
        ))
        self.conn.commit()

    def update_todo_item_checked(self, item_id, is_checked):
        """Updates the check state of a to-do item."""
        self.cursor.execute(
            "UPDATE project_todo_list SET is_checked = ? WHERE id = ?",
            (int(bool(is_checked)), item_id)
        )
        self.conn.commit()

    def delete_todo_item(self, item_id):
        """Deletes a to-do item."""
        self.cursor.execute("DELETE FROM project_todo_list WHERE id = ?", (item_id,))
        self.conn.commit()

    def update_todo_order(self, ordered_ids):
        """Updates the display_order for a list of to-do item IDs."""
        for order, item_id in enumerate(ordered_ids):
            self.cursor.execute(
                "UPDATE project_todo_list SET display_order = ? WHERE id = ?",
                (order, item_id)
            )
        self.conn.commit()