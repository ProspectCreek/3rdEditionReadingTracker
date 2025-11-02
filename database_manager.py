import sqlite3
import shutil
import os


class DatabaseManager:
    def __init__(self, db_file="reading_tracker.db"):
        """Initialize and connect to the SQLite database."""
        self.conn = sqlite3.connect(db_file)
        self.conn.row_factory = sqlite3.Row  # Access columns by name
        self.conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign key cascade
        self.cursor = self.conn.cursor()
        self.setup_database()

    def setup_database(self):
        """
        Create the necessary tables if they don't exist.
        """
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parent_id INTEGER,
            type TEXT NOT NULL,
            name TEXT NOT NULL,
            display_order INTEGER,
            FOREIGN KEY (parent_id) REFERENCES items(id) ON DELETE CASCADE
        )
        """)

        # --- Schema Migration ---
        expected_columns = {
            "is_assignment": "INTEGER DEFAULT 0",
            "project_purpose_text": "TEXT",
            "project_goals_text": "TEXT",
            "key_questions_text": "TEXT",
            "thesis_text": "TEXT",
            "insights_text": "TEXT",
            "unresolved_text": "TEXT"
        }
        self.cursor.execute("PRAGMA table_info(items)")
        existing_columns = [row['name'] for row in self.cursor.fetchall()]
        for col_name, col_type in expected_columns.items():
            if col_name not in existing_columns:
                try:
                    print(f"Adding missing column: {col_name}...")
                    self.cursor.execute(f"ALTER TABLE items ADD COLUMN {col_name} {col_type}")
                except sqlite3.OperationalError as e:
                    print(f"Warning: Could not add column {col_name}. {e}")

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS instructions (
            project_id INTEGER PRIMARY KEY,
            key_questions_instr TEXT NOT NULL,
            thesis_instr TEXT NOT NULL,
            insights_instr TEXT NOT NULL,
            unresolved_instr TEXT NOT NULL,
            FOREIGN KEY (project_id) REFERENCES items(id) ON DELETE CASCADE
        )
        """)

        # --- NEW: Readings Table ---
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            author TEXT,
            display_order INTEGER,
            reading_notes_text TEXT,
            FOREIGN KEY (project_id) REFERENCES items(id) ON DELETE CASCADE
        )
        """)
        # --- END NEW ---

        self.conn.commit()

    # --- Instructions Functions ---
    def get_or_create_instructions(self, project_id):
        """
        Gets instructions for a project. If they don't exist,
        creates and returns the default instructions.
        """
        self.cursor.execute("SELECT * FROM instructions WHERE project_id = ?", (project_id,))
        instr = self.cursor.fetchone()
        if instr:
            return dict(instr)
        else:
            defaults = {
                "project_id": project_id,
                "key_questions_instr": "What is the central question this project aims to answer?",
                "thesis_instr": "State your current working thesis/argument.",
                "insights_instr": "Capture 3-7 key insights that are shaping your thinking.",
                "unresolved_instr": "List open questions, unresolved questions, or uncertainties to be revisited."
            }
            self.cursor.execute("""
                INSERT INTO instructions 
                (project_id, key_questions_instr, thesis_instr, insights_instr, unresolved_instr)
                VALUES (:project_id, :key_questions_instr, :thesis_instr, :insights_instr, :unresolved_instr)
            """, defaults)
            self.conn.commit()
            self.cursor.execute("SELECT * FROM instructions WHERE project_id = ?", (project_id,))
            return dict(self.cursor.fetchone())

    def update_instructions(self, project_id, key_questions, thesis, insights, unresolved):
        """Updates the instruction text for a given project."""
        self.cursor.execute("""
            UPDATE instructions
            SET key_questions_instr = ?, thesis_instr = ?, insights_instr = ?, unresolved_instr = ?
            WHERE project_id = ?
        """, (key_questions, thesis, insights, unresolved, project_id))
        self.conn.commit()

    # --- Project Text Field Functions ---
    def update_project_text_field(self, project_id, field_name, content):
        """
        Dynamically updates a single text field for a project in the items table.
        """
        if field_name not in ['project_purpose_text', 'project_goals_text',
                              'key_questions_text', 'thesis_text',
                              'insights_text', 'unresolved_text']:
            print(f"Error: Invalid field name {field_name}")
            return
        query = f"UPDATE items SET {field_name} = ? WHERE id = ?"
        self.cursor.execute(query, (content, project_id))
        self.conn.commit()

    def update_assignment_status(self, project_id, new_status):
        """Updates the is_assignment status for a project."""
        self.cursor.execute(
            "UPDATE items SET is_assignment = ? WHERE id = ?",
            (new_status, project_id)
        )
        self.conn.commit()

    # --- Item Functions (Projects/Classes) ---
    def get_items(self, parent_id=None):
        """
        Get all items under a specific parent.
        """
        query = "SELECT * FROM items WHERE parent_id IS ? ORDER BY display_order"
        params = (parent_id,)
        if parent_id is None:
            query = "SELECT * FROM items WHERE parent_id IS NULL ORDER BY display_order"
            params = ()
        self.cursor.execute(query, params)
        return self.cursor.fetchall()

    def create_item(self, name, item_type, parent_id=None, is_assignment=1):
        """
        Create a new class or project.
        """
        query = "SELECT MAX(display_order) FROM items WHERE parent_id IS ?"
        params = (parent_id,)
        if parent_id is None:
            query = "SELECT MAX(display_order) FROM items WHERE parent_id IS NULL"
            params = ()
        self.cursor.execute(query, params)
        max_order = self.cursor.fetchone()[0]
        new_order = 0 if max_order is None else max_order + 1
        self.cursor.execute(
            "INSERT INTO items (parent_id, type, name, display_order, is_assignment) VALUES (?, ?, ?, ?, ?)",
            (parent_id, item_type, name, new_order, is_assignment)
        )
        self.conn.commit()
        return self.cursor.lastrowid

    def rename_item(self, item_id, new_name):
        self.cursor.execute("UPDATE items SET name = ? WHERE id = ?", (new_name, item_id))
        self.conn.commit()

    def move_item(self, item_id, new_parent_id=None):
        query = "SELECT MAX(display_order) FROM items WHERE parent_id IS ?"
        params = (new_parent_id,)
        if new_parent_id is None:
            query = "SELECT MAX(display_order) FROM items WHERE parent_id IS NULL"
            params = ()
        self.cursor.execute(query, params)
        max_order = self.cursor.fetchone()[0]
        new_order = 0 if max_order is None else max_order + 1
        self.cursor.execute(
            "UPDATE items SET parent_id = ?, display_order = ? WHERE id = ?",
            (new_parent_id, new_order, item_id)
        )
        self.conn.commit()

    def update_order(self, ordered_db_ids):
        for index, item_id in enumerate(ordered_db_ids):
            self.cursor.execute("UPDATE items SET display_order = ? WHERE id = ?", (index, item_id))
        self.conn.commit()

    def get_item_details(self, item_id):
        self.cursor.execute("SELECT * FROM items WHERE id = ?", (item_id,))
        return self.cursor.fetchone()

    def delete_item(self, item_id):
        self.cursor.execute("DELETE FROM items WHERE id = ?", (item_id,))
        self.conn.commit()

    def get_all_classes(self):
        self.cursor.execute("SELECT id, name FROM items WHERE type = 'class' ORDER BY name")
        return self.cursor.fetchall()

    def duplicate_item(self, item_id, new_parent_id=None):
        original = self.get_item_details(item_id)
        if not original:
            return
        parent_id = new_parent_id if new_parent_id is not None else original['parent_id']
        new_name = f"{original['name']} (Copy)"
        new_id = self.create_item(
            new_name,
            original['type'],
            parent_id,
            original['is_assignment']
        )
        if original['type'] == 'class':
            children = self.get_items(original['id'])
            for child in children:
                self.duplicate_item(child['id'], new_parent_id=new_id)

    # --- NEW: Reading Functions ---
    def add_reading(self, project_id, title, author):
        """Adds a new reading to a project."""
        query = "SELECT MAX(display_order) FROM readings WHERE project_id = ?"
        self.cursor.execute(query, (project_id,))
        max_order = self.cursor.fetchone()[0]
        new_order = 0 if max_order is None else max_order + 1

        self.cursor.execute(
            "INSERT INTO readings (project_id, title, author, display_order) VALUES (?, ?, ?, ?)",
            (project_id, title, author, new_order)
        )
        self.conn.commit()
        return self.cursor.lastrowid

    def get_readings(self, project_id):
        """Gets all readings for a project, in order."""
        self.cursor.execute(
            "SELECT * FROM readings WHERE project_id = ? ORDER BY display_order",
            (project_id,)
        )
        return self.cursor.fetchall()

    def update_reading_order(self, ordered_db_ids):
        """
        Updates the display_order for a list of reading IDs.
        """
        for index, item_id in enumerate(ordered_db_ids):
            self.cursor.execute("UPDATE items SET display_order = ? WHERE id = ?", (index, item_id))
        self.conn.commit()

    # --- END NEW ---

    def __del__(self):
        """Close the database connection on object deletion."""
        self.conn.close()

