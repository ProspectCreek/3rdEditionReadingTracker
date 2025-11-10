import sqlite3
import shutil
import os


class DatabaseManager:
    def __init__(self, db_file="reading_tracker.db"):
        """Initialize and connect to the SQLite database."""
        self.conn = sqlite3.connect(db_file)
        # We still use Row; public getters coerce to dicts where needed.
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.cursor = self.conn.cursor()
        self.setup_database()

    # ----------------------- helpers: row → dict -----------------------

    @staticmethod
    def _rowdict(row):
        """Coerce a sqlite3.Row (or None) to a plain dict (or None)."""
        return dict(row) if row is not None else None

    @staticmethod
    def _map_rows(rows):
        """Coerce an iterable of sqlite3.Row to list[dict]."""
        return [dict(r) for r in rows] if rows else []

    # ----------------------------- schema -----------------------------

    def setup_database(self):
        # --- Items / Projects ---
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parent_id INTEGER,
            type TEXT NOT NULL,
            name TEXT NOT NULL,
            display_order INTEGER,
            is_assignment INTEGER DEFAULT 0,
            project_purpose_text TEXT,
            project_goals_text TEXT,
            key_questions_text TEXT,
            thesis_text TEXT,
            insights_text TEXT,
            unresolved_text TEXT,
            assignment_instructions_text TEXT,
            assignment_draft_text TEXT,
            FOREIGN KEY (parent_id) REFERENCES items(id) ON DELETE CASCADE
        )
        """)

        # Defensive additive migrations
        self.cursor.execute("PRAGMA table_info(items)")
        existing_item_cols = {row["name"] for row in self.cursor.fetchall()}
        for col_name, col_type in {
            "is_assignment": "INTEGER DEFAULT 0",
            "project_purpose_text": "TEXT",
            "project_goals_text": "TEXT",
            "key_questions_text": "TEXT",
            "thesis_text": "TEXT",
            "insights_text": "TEXT",
            "unresolved_text": "TEXT",
            "assignment_instructions_text": "TEXT",
            "assignment_draft_text": "TEXT",
        }.items():
            if col_name not in existing_item_cols:
                try:
                    self.cursor.execute(f"ALTER TABLE items ADD COLUMN {col_name} {col_type}")
                except sqlite3.OperationalError:
                    pass

        # --- Readings ---
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            author TEXT,
            display_order INTEGER,
            reading_notes_text TEXT,
            nickname TEXT,
            published TEXT,
            pages TEXT,
            assignment TEXT,
            level TEXT,
            classification TEXT,
            FOREIGN KEY (project_id) REFERENCES items(id) ON DELETE CASCADE
        )
        """)
        self.cursor.execute("PRAGMA table_info(readings)")
        existing_read_cols = {row["name"] for row in self.cursor.fetchall()}
        for col_name, col_type in {
            "nickname": "TEXT",
            "published": "TEXT",
            "pages": "TEXT",
            "assignment": "TEXT",
            "level": "TEXT",
            "classification": "TEXT",
        }.items():
            if col_name not in existing_read_cols:
                try:
                    self.cursor.execute(f"ALTER TABLE readings ADD COLUMN {col_name} {col_type}")
                except sqlite3.OperationalError:
                    pass

        # --- Rubric ---
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS rubric_components (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            component_text TEXT NOT NULL,
            is_checked INTEGER DEFAULT 0,
            display_order INTEGER,
            FOREIGN KEY (project_id) REFERENCES items(id) ON DELETE CASCADE
        )
        """)

        # --- Instructions ---
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS instructions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            key_questions_instr TEXT,
            thesis_instr TEXT,
            insights_instr TEXT,
            unresolved_instr TEXT,
            FOREIGN KEY (project_id) REFERENCES items(id) ON DELETE CASCADE,
            UNIQUE(project_id)
        )
        """)

        # --- Mindmaps ---
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS mindmaps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            display_order INTEGER,
            default_font_family TEXT,
            default_font_size INTEGER,
            default_font_weight TEXT,
            default_font_slant TEXT,
            FOREIGN KEY (project_id) REFERENCES items(id) ON DELETE CASCADE
        )
        """)

        self.cursor.execute("PRAGMA table_info(mindmaps)")
        existing_mindmap_cols = {row["name"] for row in self.cursor.fetchall()}
        if "title" in existing_mindmap_cols and "name" not in existing_mindmap_cols:
            self.cursor.execute("ALTER TABLE mindmaps RENAME COLUMN title TO name")

        if "default_font_family" not in existing_mindmap_cols:
            self.cursor.execute("ALTER TABLE mindmaps ADD COLUMN default_font_family TEXT")
            self.cursor.execute("ALTER TABLE mindmaps ADD COLUMN default_font_size INTEGER")
            self.cursor.execute("ALTER TABLE mindmaps ADD COLUMN default_font_weight TEXT")
            self.cursor.execute("ALTER TABLE mindmaps ADD COLUMN default_font_slant TEXT")
            self.cursor.execute("ALTER TABLE mindmaps ADD COLUMN display_order INTEGER")

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS mindmap_nodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mindmap_id INTEGER NOT NULL,
            node_id_text TEXT NOT NULL,
            x REAL NOT NULL,
            y REAL NOT NULL,
            width REAL NOT NULL,
            height REAL NOT NULL,
            text TEXT,
            shape_type TEXT,
            fill_color TEXT,
            outline_color TEXT,
            text_color TEXT,
            font_family TEXT,
            font_size INTEGER,
            font_weight TEXT,
            font_slant TEXT,
            FOREIGN KEY (mindmap_id) REFERENCES mindmaps(id) ON DELETE CASCADE,
            UNIQUE(mindmap_id, node_id_text)
        )
        """)

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS mindmap_edges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mindmap_id INTEGER NOT NULL,
            from_node_id_text TEXT NOT NULL,
            to_node_id_text TEXT NOT NULL,
            color TEXT,
            style TEXT,
            width INTEGER,
            arrow_style TEXT,
            FOREIGN KEY (mindmap_id) REFERENCES mindmaps(id) ON DELETE CASCADE
        )
        """)

        # --- Fix potential old bad schema for edges ---
        self.cursor.execute("PRAGMA table_info(mindmap_edges)")
        edge_cols = {row["name"] for row in self.cursor.fetchall()}
        if "from_node_id" in edge_cols:
            # This looks like the old, incorrect schema. Rebuild it.
            print("Detected old mindmap_edges schema, attempting to rebuild...")
            try:
                self.cursor.execute("DROP TABLE mindmap_edges")
                self.cursor.execute("""
                CREATE TABLE mindmap_edges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mindmap_id INTEGER NOT NULL,
                    from_node_id_text TEXT NOT NULL,
                    to_node_id_text TEXT NOT NULL,
                    color TEXT,
                    style TEXT,
                    width INTEGER,
                    arrow_style TEXT,
                    FOREIGN KEY (mindmap_id) REFERENCES mindmaps(id) ON DELETE CASCADE
                )
                """)
            except Exception as e:
                print(f"Error rebuilding mindmap_edges: {e}")

        # --- Reading Outline ---
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS reading_outline (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reading_id INTEGER NOT NULL,
            parent_id INTEGER,
            section_title TEXT NOT NULL,
            notes_html TEXT,
            display_order INTEGER,
            FOREIGN KEY (reading_id) REFERENCES readings(id) ON DELETE CASCADE,
            FOREIGN KEY (parent_id) REFERENCES reading_outline(id) ON DELETE CASCADE
        )
        """)

        # --- Reading Attachments ---
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS reading_attachments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reading_id INTEGER NOT NULL,
            display_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            display_order INTEGER,
            FOREIGN KEY (reading_id) REFERENCES readings(id) ON DELETE CASCADE
        )
        """)

        # --- Reading Driving Questions ---
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS reading_driving_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reading_id INTEGER NOT NULL,
            parent_id INTEGER,
            display_order INTEGER,
            question_text TEXT,
            nickname TEXT,
            type TEXT,
            question_category TEXT,
            scope TEXT,
            outline_id INTEGER,
            pages TEXT,
            why_question TEXT,
            synthesis_tags TEXT,
            is_working_question INTEGER,
            FOREIGN KEY (reading_id) REFERENCES readings(id) ON DELETE CASCADE,
            FOREIGN KEY (parent_id) REFERENCES reading_driving_questions(id) ON DELETE CASCADE,
            FOREIGN KEY (outline_id) REFERENCES reading_outline(id) ON DELETE SET NULL
        )
        """)

        # --- Migration: Drop old columns if they exist ---
        self.cursor.execute("PRAGMA table_info(reading_driving_questions)")
        existing_dq_cols = {row["name"] for row in self.cursor.fetchall()}
        if "reading_has_parts" in existing_dq_cols:
            self.cursor.execute("ALTER TABLE reading_driving_questions DROP COLUMN reading_has_parts")
        if "include_in_summary" in existing_dq_cols:
            self.cursor.execute("ALTER TABLE reading_driving_questions DROP COLUMN include_in_summary")
        if "where_in_book" in existing_dq_cols:
            # We can't just drop and add, so we rename if outline_id doesn't exist
            if "outline_id" not in existing_dq_cols:
                self.cursor.execute("ALTER TABLE reading_driving_questions RENAME COLUMN where_in_book TO outline_id")
                # This will break the foreign key, but it's the simplest migration.
                # A full migration would create a new table and copy data.
                # For now, let's just add the column if the rename wasn't possible
                self.cursor.execute("PRAGMA table_info(reading_driving_questions)")
                re_checked_cols = {row["name"] for row in self.cursor.fetchall()}
                if "outline_id" not in re_checked_cols:
                    self.cursor.execute(
                        "ALTER TABLE reading_driving_questions ADD COLUMN outline_id INTEGER REFERENCES reading_outline(id) ON DELETE SET NULL")

        self.conn.commit()

    # ---------------------- items / projects ----------------------

    def _next_item_order(self, parent_id):
        if parent_id is None:
            self.cursor.execute("SELECT COALESCE(MAX(display_order), -1) FROM items WHERE parent_id IS NULL")
        else:
            self.cursor.execute("SELECT COALESCE(MAX(display_order), -1) FROM items WHERE parent_id = ?", (parent_id,))
        return (self.cursor.fetchone()[0] or -1) + 1

    def add_item(self, parent_id, type_, name):
        """Legacy helper used by some UIs."""
        new_order = self._next_item_order(parent_id)
        self.cursor.execute(
            "INSERT INTO items (parent_id, type, name, display_order) VALUES (?, ?, ?, ?)",
            (parent_id, type_, name, new_order)
        )
        self.conn.commit()
        return self.cursor.lastrowid

    def create_item(self, name, item_type, parent_db_id=None, is_assignment=0):
        """UI-facing creator (signature used by ProjectListWidget)."""
        new_order = self._next_item_order(parent_db_id)
        self.cursor.execute("""
            INSERT INTO items (parent_id, type, name, display_order, is_assignment)
            VALUES (?, ?, ?, ?, ?)
        """, (parent_db_id, item_type, name, new_order, int(is_assignment)))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_items(self, parent_id=None):
        """Return children as list[dict] (safe for .get usage)."""
        if parent_id is None:
            self.cursor.execute("""
                SELECT * FROM items
                WHERE parent_id IS NULL
                ORDER BY display_order, id
            """)
        else:
            self.cursor.execute("""
                SELECT * FROM items
                WHERE parent_id = ?
                ORDER BY display_order, id
            """, (parent_id,))
        return self._map_rows(self.cursor.fetchall())

    def get_item_details(self, item_id):
        """Return a single item as dict (safe for .get usage)."""
        self.cursor.execute("SELECT * FROM items WHERE id = ?", (item_id,))
        return self._rowdict(self.cursor.fetchone())

    def rename_item(self, item_id, new_name):
        self.cursor.execute("UPDATE items SET name = ? WHERE id = ?", (new_name, item_id))
        self.conn.commit()

    def delete_item(self, item_id):
        self.cursor.execute("DELETE FROM items WHERE id = ?", (item_id,))
        self.conn.commit()

    def reorder_items(self, ordered_ids):
        for order, iid in enumerate(ordered_ids):
            self.cursor.execute("UPDATE items SET display_order = ? WHERE id = ?", (order, iid))
        self.conn.commit()

    def update_project_text_field(self, project_id, field_name, html_text):
        self.cursor.execute(f"UPDATE items SET {field_name} = ? WHERE id = ?", (html_text, project_id))
        self.conn.commit()

    # ------------------------- instructions -------------------------

    def get_or_create_instructions(self, project_id):
        self.cursor.execute("SELECT * FROM instructions WHERE project_id = ?", (project_id,))
        row = self.cursor.fetchone()
        if row:
            return self._rowdict(row)

        # Check if it's a legacy project (no row)
        self.cursor.execute("SELECT COUNT(*) FROM instructions WHERE project_id = ?", (project_id,))
        count = self.cursor.fetchone()[0]
        if count == 0:
            try:
                self.cursor.execute("""
                    INSERT INTO instructions (project_id, key_questions_instr, thesis_instr, insights_instr, unresolved_instr)
                    VALUES (?, '', '', '', '')
                """, (project_id,))
                self.conn.commit()
            except sqlite3.IntegrityError:
                # Race condition, another process inserted it. Ignore.
                pass

        self.cursor.execute("SELECT * FROM instructions WHERE project_id = ?", (project_id,))
        return self._rowdict(self.cursor.fetchone())

    def update_instructions(self, project_id, key_q, thesis, insights, unresolved):
        self.cursor.execute("""
            UPDATE instructions
            SET key_questions_instr = ?, thesis_instr = ?, insights_instr = ?, unresolved_instr = ?
            WHERE project_id = ?
        """, (key_q, thesis, insights, unresolved, project_id))
        self.conn.commit()

    # --------------------------- readings ---------------------------

    def add_reading(self, project_id, title, author, nickname):
        """Named params + computed display_order + verify presence."""
        self.cursor.execute(
            "SELECT COALESCE(MAX(display_order), -1) FROM readings WHERE project_id = ?",
            (project_id,)
        )
        new_order = (self.cursor.fetchone()[0] or -1) + 1

        payload = {
            "project_id": int(project_id),
            "title": (title or "").strip(),
            "author": (author or "").strip(),
            "nickname": (nickname or "").strip(),
            "display_order": int(new_order),
        }

        self.cursor.execute("""
            INSERT INTO readings (project_id, title, author, nickname, display_order)
            VALUES (:project_id, :title, :author, :nickname, :display_order)
        """, payload)
        self.conn.commit()

        new_id = self.cursor.lastrowid
        if self.get_reading_details(new_id) is None:
            raise RuntimeError("Insert verification failed: reading row not found after commit.")
        return new_id

    def get_readings(self, project_id):
        self.cursor.execute("""
            SELECT * FROM readings
            WHERE project_id = ?
            ORDER BY display_order ASC, id ASC
        """, (project_id,))
        return self._map_rows(self.cursor.fetchall())

    def get_reading_details(self, reading_id):
        self.cursor.execute("SELECT * FROM readings WHERE id = ?", (reading_id,))
        return self._rowdict(self.cursor.fetchone())

    def update_reading_details(self, reading_id, details_dict):
        self.cursor.execute("""
            UPDATE readings
            SET title = ?, author = ?, nickname = ?, published = ?, 
                pages = ?, assignment = ?, level = ?, classification = ?
            WHERE id = ?
        """, (
            details_dict.get('title', ''), details_dict.get('author', ''), details_dict.get('nickname', ''),
            details_dict.get('published', ''), details_dict.get('pages', ''),
            details_dict.get('assignment', ''), details_dict.get('level', ''),
            details_dict.get('classification', ''), reading_id
        ))
        self.conn.commit()

    def delete_reading(self, reading_id):
        """Deletes a reading and all its related data (outline, attachments) via cascade."""
        self.cursor.execute("DELETE FROM readings WHERE id = ?", (reading_id,))
        self.conn.commit()

    def update_reading_order(self, ordered_ids):
        """Reorders readings based on a list of IDs."""
        for order, reading_id in enumerate(ordered_ids):
            self.cursor.execute(
                "UPDATE readings SET display_order = ? WHERE id = ?",
                (order, reading_id)
            )
        self.conn.commit()

    # --------------------------- rubric ----------------------------

    def get_rubric_components(self, project_id):
        """Return rubric components for a project as list[dict]."""
        self.cursor.execute("""
            SELECT * FROM rubric_components
            WHERE project_id = ?
            ORDER BY display_order, id
        """, (project_id,))
        return self._map_rows(self.cursor.fetchall())

    def add_rubric_component(self, project_id, text):
        """Add a rubric component at the end of the current order."""
        self.cursor.execute("""
            SELECT COALESCE(MAX(display_order), -1)
            FROM rubric_components
            WHERE project_id = ?
        """, (project_id,))
        new_order = (self.cursor.fetchone()[0] or -1) + 1

        self.cursor.execute("""
            INSERT INTO rubric_components (project_id, component_text, is_checked, display_order)
            VALUES (?, ?, 0, ?)
        """, (project_id, text, new_order))
        self.conn.commit()
        return self.cursor.lastrowid

    def update_rubric_component_text(self, component_id, text):
        """Update the visible text of a rubric component."""
        self.cursor.execute("""
            UPDATE rubric_components
            SET component_text = ?
            WHERE id = ?
        """, (text, component_id))
        self.conn.commit()

    def update_rubric_component_checked(self, component_id, is_checked):
        """Set the checked flag (0/1) on a rubric component."""
        self.cursor.execute("""
            UPDATE rubric_components
            SET is_checked = ?
            WHERE id = ?
        """, (int(bool(is_checked)), component_id))
        self.conn.commit()

    def delete_rubric_component(self, component_id):
        """Delete a rubric component."""
        self.cursor.execute("DELETE FROM rubric_components WHERE id = ?", (component_id,))
        self.conn.commit()

    def update_rubric_component_order(self, ordered_ids):
        """Reorder rubric components by the given id sequence."""
        for order, cid in enumerate(ordered_ids):
            self.cursor.execute("""
                UPDATE rubric_components
                SET display_order = ?
                WHERE id = ?
            """, (order, cid))
        self.conn.commit()

    # ----------------------- reading outline -----------------------

    def get_reading_outline(self, reading_id, parent_id=None):
        """Gets outline items, in order."""
        if parent_id is None:
            self.cursor.execute("""
                SELECT * FROM reading_outline
                WHERE reading_id = ? AND parent_id IS NULL
                ORDER BY display_order, id
            """, (reading_id,))
        else:
            self.cursor.execute("""
                SELECT * FROM reading_outline
                WHERE reading_id = ? AND parent_id = ?
                ORDER BY display_order, id
            """, (reading_id, parent_id))
        # Return as list[dict] for dialogs
        return self._map_rows(self.cursor.fetchall())

    def add_outline_section(self, reading_id, title, parent_id=None):
        """Adds an outline section, calculating its display order."""
        if parent_id is None:
            self.cursor.execute("""
                SELECT COALESCE(MAX(display_order), -1) FROM reading_outline
                WHERE reading_id = ? AND parent_id IS NULL
            """, (reading_id,))
        else:
            self.cursor.execute("""
                SELECT COALESCE(MAX(display_order), -1) FROM reading_outline
                WHERE reading_id = ? AND parent_id = ?
            """, (reading_id, parent_id))
        new_order = (self.cursor.fetchone()[0] or -1) + 1

        self.cursor.execute("""
            INSERT INTO reading_outline (reading_id, parent_id, section_title, notes_html, display_order)
            VALUES (?, ?, ?, ?, ?)
        """, (reading_id, parent_id, title, "", new_order))
        self.conn.commit()

    def update_outline_section_title(self, section_id, new_title):
        self.cursor.execute("UPDATE reading_outline SET section_title = ? WHERE id = ?", (new_title, section_id))
        self.conn.commit()

    def delete_outline_section(self, section_id):
        self.cursor.execute("DELETE FROM reading_outline WHERE id = ?", (section_id,))
        self.conn.commit()

    def update_outline_section_order(self, ordered_ids):
        """Updates the display_order for a list of sibling IDs."""
        for order, sid in enumerate(ordered_ids):
            self.cursor.execute("UPDATE reading_outline SET display_order = ? WHERE id = ?", (order, sid))
        self.conn.commit()

    def get_outline_section_notes(self, section_id):
        self.cursor.execute("SELECT notes_html FROM reading_outline WHERE id = ?", (section_id,))
        row = self.cursor.fetchone()
        return row["notes_html"] if row else ""

    def update_outline_section_notes(self, section_id, html):
        self.cursor.execute("UPDATE reading_outline SET notes_html = ? WHERE id = ?", (html, section_id))
        self.conn.commit()

    # ----------------------- reading attachments -----------------------

    def get_attachments(self, reading_id):
        """Get all attachments for a specific reading."""
        self.cursor.execute("""
            SELECT * FROM reading_attachments
            WHERE reading_id = ?
            ORDER BY display_order, id
        """, (reading_id,))
        return self._map_rows(self.cursor.fetchall())

    def get_attachment_details(self, attachment_id):
        """Get the details for a single attachment."""
        self.cursor.execute("SELECT * FROM reading_attachments WHERE id = ?", (attachment_id,))
        return self._rowdict(self.cursor.fetchone())

    def _next_attachment_order(self, reading_id):
        self.cursor.execute(
            "SELECT COALESCE(MAX(display_order), -1) FROM reading_attachments WHERE reading_id = ?",
            (reading_id,)
        )
        return (self.cursor.fetchone()[0] or -1) + 1

    def add_attachment(self, reading_id, display_name, file_path):
        """Adds a new attachment record."""
        new_order = self._next_attachment_order(reading_id)
        self.cursor.execute("""
            INSERT INTO reading_attachments (reading_id, display_name, file_path, display_order)
            VALUES (?, ?, ?, ?)
        """, (reading_id, display_name, file_path, new_order))
        self.conn.commit()
        return self.cursor.lastrowid

    def rename_attachment(self, attachment_id, new_display_name):
        """Updates the display name of an attachment."""
        self.cursor.execute(
            "UPDATE reading_attachments SET display_name = ? WHERE id = ?",
            (new_display_name, attachment_id)
        )
        self.conn.commit()

    def delete_attachment(self, attachment_id):
        """Deletes an attachment record from the database."""
        self.cursor.execute("DELETE FROM reading_attachments WHERE id = ?", (attachment_id,))
        self.conn.commit()

    def update_attachment_order(self, ordered_ids):
        """Reorders attachments based on a list of IDs."""
        for order, att_id in enumerate(ordered_ids):
            self.cursor.execute(
                "UPDATE reading_attachments SET display_order = ? WHERE id = ?",
                (order, att_id)
            )
        self.conn.commit()

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
            # --- Nodes ---
            # Get existing node IDs from DB
            self.cursor.execute("SELECT node_id_text FROM mindmap_nodes WHERE mindmap_id = ?", (mindmap_id,))
            existing_node_ids = {row[0] for row in self.cursor.fetchall()}

            node_ids_to_keep = set()

            for node_data in nodes:
                node_id_text = str(node_data['id'])
                node_ids_to_keep.add(node_id_text)

                # Prep data for insertion/update
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
                    # Update
                    self.cursor.execute("""
                        UPDATE mindmap_nodes SET
                        x=:x, y=:y, width=:width, height=:height, text=:text, shape_type=:shape_type,
                        fill_color=:fill_color, outline_color=:outline_color, text_color=:text_color,
                        font_family=:font_family, font_size=:font_size, font_weight=:font_weight, font_slant=:font_slant
                        WHERE mindmap_id=:mindmap_id AND node_id_text=:node_id_text
                    """, params)
                else:
                    # Insert
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

            # Delete nodes that are in the DB but not in the save data
            nodes_to_delete = existing_node_ids - node_ids_to_keep
            if nodes_to_delete:
                for node_id_text in nodes_to_delete:
                    self.cursor.execute(
                        "DELETE FROM mindmap_nodes WHERE mindmap_id = ? AND node_id_text = ?",
                        (mindmap_id, node_id_text)
                    )

            # --- Edges ---
            # Simple approach: delete all existing edges and add the new ones.
            # (More complex logic could be used to update/insert/delete)
            self.cursor.execute("DELETE FROM mindmap_edges WHERE mindmap_id = ?", (mindmap_id,))

            edge_insert_params = []
            for i, edge_data in enumerate(edges):
                edge_id_text = f"edge_{i}"  # Generate a simple unique ID for this save
                params = {
                    'mindmap_id': mindmap_id,
                    'edge_id_text': edge_id_text,
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
                        width, style, arrow_style, edge_id_text
                    ) VALUES (
                        :mindmap_id, :from_node_id_text, :to_node_id_text, :color, 
                        :width, :style, :arrow_style, :edge_id_text
                    )
                """, edge_insert_params)

            self.conn.commit()

        except Exception as e:
            self.conn.rollback()
            print(f"Error saving mindmap data: {e}")
            raise

    # ----------------------- reading driving questions -----------------------

    def get_driving_questions(self, reading_id, parent_id=None):
        """Gets all driving questions for a reading, ordered."""
        sql = "SELECT * FROM reading_driving_questions WHERE reading_id = ?"
        params = [reading_id]

        if parent_id is None:
            sql += " AND parent_id IS NULL"
        else:
            sql += " AND parent_id = ?"
            params.append(parent_id)

        sql += " ORDER BY display_order, id"
        self.cursor.execute(sql, tuple(params))
        return self._map_rows(self.cursor.fetchall())

    def get_driving_question_details(self, question_id):
        """Gets all details for a single driving question."""
        self.cursor.execute("SELECT * FROM reading_driving_questions WHERE id = ?", (question_id,))
        return self._rowdict(self.cursor.fetchone())

    def _next_driving_question_order(self, reading_id, parent_id):
        sql = "SELECT COALESCE(MAX(display_order), -1) FROM reading_driving_questions WHERE reading_id = ?"
        params = [reading_id]

        if parent_id is None:
            sql += " AND parent_id IS NULL"
        else:
            sql += " AND parent_id = ?"
            params.append(parent_id)

        self.cursor.execute(sql, tuple(params))
        return (self.cursor.fetchone()[0] or -1) + 1

    def add_driving_question(self, reading_id, data):
        """Adds a new driving question."""
        parent_id = data.get("parent_id")
        new_order = self._next_driving_question_order(reading_id, parent_id)

        self.cursor.execute("""
            INSERT INTO reading_driving_questions (
                reading_id, parent_id, display_order, question_text, nickname, type, 
                question_category, scope, outline_id, pages, 
                why_question, synthesis_tags, is_working_question
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            reading_id, parent_id, new_order,
            data.get("question_text"), data.get("nickname"), data.get("type"),
            data.get("question_category"), data.get("scope"),
            data.get("outline_id"), data.get("pages"),
            data.get("why_question"), data.get("synthesis_tags"),
            1 if data.get("is_working_question") else 0
        ))
        self.conn.commit()
        return self.cursor.lastrowid

    def update_driving_question(self, question_id, data):
        """Updates an existing driving question."""
        self.cursor.execute("""
            UPDATE reading_driving_questions SET
                parent_id = ?, question_text = ?, nickname = ?, type = ?, 
                question_category = ?, scope = ?, outline_id = ?, 
                pages = ?, why_question = ?, synthesis_tags = ?, 
                is_working_question = ?
            WHERE id = ?
        """, (
            data.get("parent_id"), data.get("question_text"), data.get("nickname"), data.get("type"),
            data.get("question_category"), data.get("scope"),
            data.get("outline_id"), data.get("pages"),
            data.get("why_question"), data.get("synthesis_tags"),
            1 if data.get("is_working_question") else 0,
            question_id
        ))
        self.conn.commit()

    def delete_driving_question(self, question_id):
        """Deletes a driving question (and children, via cascade)."""
        self.cursor.execute("DELETE FROM reading_driving_questions WHERE id = ?", (question_id,))
        self.conn.commit()

    def update_driving_question_order(self, ordered_ids):
        """Reorders sibling driving questions based on a list of IDs."""
        for order, q_id in enumerate(ordered_ids):
            self.cursor.execute(
                "UPDATE reading_driving_questions SET display_order = ? WHERE id = ?",
                (order, q_id)
            )
        self.conn.commit()

    def find_current_working_question(self, reading_id):
        """Finds the one (if any) question marked as the working question."""
        self.cursor.execute(
            "SELECT * FROM reading_driving_questions WHERE reading_id = ? AND is_working_question = 1 LIMIT 1",
            (reading_id,)
        )
        return self._rowdict(self.cursor.fetchone())

    def clear_all_working_questions(self, reading_id):
        """Sets is_working_question = 0 for all questions for a specific reading."""
        self.cursor.execute(
            "UPDATE reading_driving_questions SET is_working_question = 0 WHERE reading_id = ?",
            (reading_id,)
        )
        self.conn.commit()

    # ---------------------------- utility ----------------------------

    def backup_database(self, dest_path):
        """Create a copy of the database file at dest_path."""
        self.conn.commit()
        src = self.conn.execute("PRAGMA database_list").fetchone()[2]
        shutil.copyfile(src, dest_path)

    def __del__(self):
        try:
            self.conn.close()
        except Exception:
            pass