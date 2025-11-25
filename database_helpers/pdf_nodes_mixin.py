# prospectcreek/3rdeditionreadingtracker/database_helpers/pdf_nodes_mixin.py
import sqlite3


class PdfNodesMixin:
    """
    Mixin for managing spatial nodes on PDF attachments and their categories.
    """

    # --- Category Management ---

    def get_pdf_node_categories(self, project_id):
        """Gets all node categories for a project."""
        self.cursor.execute("""
            SELECT * FROM pdf_node_categories 
            WHERE project_id = ?
            ORDER BY name
        """, (project_id,))
        return self._map_rows(self.cursor.fetchall())

    def add_pdf_node_category(self, project_id, name, color_hex):
        """Adds a new category."""
        self.cursor.execute("""
            INSERT INTO pdf_node_categories (project_id, name, color_hex)
            VALUES (?, ?, ?)
        """, (project_id, name, color_hex))
        self.conn.commit()
        return self.cursor.lastrowid

    def update_pdf_node_category(self, category_id, name, color_hex):
        """Updates an existing category."""
        self.cursor.execute("""
            UPDATE pdf_node_categories
            SET name = ?, color_hex = ?
            WHERE id = ?
        """, (name, color_hex, category_id))
        self.conn.commit()

    def delete_pdf_node_category(self, category_id):
        """Deletes a category. Nodes with this category will have category_id set to NULL."""
        self.cursor.execute("DELETE FROM pdf_node_categories WHERE id = ?", (category_id,))
        self.conn.commit()

    # --- Node Management ---

    def add_pdf_node(self, reading_id, attachment_id, page_number, x_pos, y_pos,
                     node_type='Note', color_hex='#FFFF00', label='New Node', description='', category_id=None):
        """Adds a new node to a PDF attachment."""
        self.cursor.execute("""
            INSERT INTO pdf_nodes (reading_id, attachment_id, page_number, x_pos, y_pos, node_type, color_hex, label, description, category_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (reading_id, attachment_id, page_number, x_pos, y_pos, node_type, color_hex, label, description, category_id))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_pdf_nodes_for_page(self, attachment_id, page_number):
        """
        Gets all nodes for a specific page, joining with categories to get the
        category name and color (overriding instance color if category exists).
        """
        self.cursor.execute("""
            SELECT 
                n.*, 
                c.name as category_name,
                c.color_hex as category_color
            FROM pdf_nodes n
            LEFT JOIN pdf_node_categories c ON n.category_id = c.id
            WHERE n.attachment_id = ? AND n.page_number = ?
        """, (attachment_id, page_number))
        return self._map_rows(self.cursor.fetchall())

    def get_all_pdf_nodes_for_attachment(self, attachment_id):
        """Gets all nodes for an attachment."""
        self.cursor.execute("""
            SELECT n.*, c.name as category_name, c.color_hex as category_color
            FROM pdf_nodes n
            LEFT JOIN pdf_node_categories c ON n.category_id = c.id
            WHERE n.attachment_id = ?
            ORDER BY n.page_number, n.id
        """, (attachment_id,))
        return self._map_rows(self.cursor.fetchall())

    def get_all_pdf_nodes_for_reading(self, reading_id):
        """Gets all nodes for a reading across all attachments."""
        self.cursor.execute("""
            SELECT n.*, c.name as category_name, c.color_hex as category_color 
            FROM pdf_nodes n
            LEFT JOIN pdf_node_categories c ON n.category_id = c.id
            WHERE n.reading_id = ?
            ORDER BY n.id
        """, (reading_id,))
        return self._map_rows(self.cursor.fetchall())

    def get_pdf_node_details(self, node_id):
        """Gets details for a single node."""
        self.cursor.execute("""
            SELECT n.*, c.name as category_name, c.color_hex as category_color 
            FROM pdf_nodes n
            LEFT JOIN pdf_node_categories c ON n.category_id = c.id
            WHERE n.id = ?
        """, (node_id,))
        return self._rowdict(self.cursor.fetchone())

    def update_pdf_node(self, node_id, label=None, description=None, color_hex=None, node_type=None,
                        x_pos=None, y_pos=None, category_id=None):
        """Updates properties of a PDF node."""
        updates = []
        params = []

        if label is not None:
            updates.append("label = ?")
            params.append(label)
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        if color_hex is not None:
            updates.append("color_hex = ?")
            params.append(color_hex)
        if node_type is not None:
            updates.append("node_type = ?")
            params.append(node_type)
        if x_pos is not None:
            updates.append("x_pos = ?")
            params.append(x_pos)
        if y_pos is not None:
            updates.append("y_pos = ?")
            params.append(y_pos)
        if category_id is not None:
            updates.append("category_id = ?")
            params.append(category_id)

        if not updates:
            return

        params.append(node_id)
        sql = f"UPDATE pdf_nodes SET {', '.join(updates)} WHERE id = ?"

        self.cursor.execute(sql, tuple(params))
        self.conn.commit()

    def delete_pdf_node(self, node_id):
        """Deletes a PDF node."""
        self.cursor.execute("DELETE FROM pdf_nodes WHERE id = ?", (node_id,))
        self.conn.commit()