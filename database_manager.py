import sqlite3
import shutil
import os


class DatabaseManager:
    def __init__(self, db_file="reading_tracker.db"):
        """Initialize and connect to the SQLite database."""
        self.conn = sqlite3.connect(db_file)
        # Use Row for name-based access; public getters coerce to dicts where needed.
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

    # ----------------------- helpers: migrations -----------------------

    def _has_column(self, table_name: str, column_name: str) -> bool:
        self.cursor.execute(f"PRAGMA table_info({table_name})")
        return any(row["name"] == column_name for row in self.cursor.fetchall())

    def _ensure_column(self, table_name: str, column_name: str, column_type: str):
        """
        Add a column if it does not exist. column_type like 'TEXT', 'INTEGER', etc.
        """
        if not self._has_column(table_name, column_name):
            self.cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
            self.conn.commit()
            print(f"[DB] Added missing column {table_name}.{column_name} ({column_type})")

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

        # --- Mindmaps (tables only) ---
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS mindmaps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            title TEXT,
            FOREIGN KEY (project_id) REFERENCES items(id) ON DELETE CASCADE
        )
        """)
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS mindmap_nodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mindmap_id INTEGER NOT NULL,
            node_id_text TEXT NOT NULL,
            x REAL, y REAL, width REAL, height REAL,
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
            edge_id_text TEXT NOT NULL,
            from_node_id TEXT NOT NULL,
            to_node_id TEXT NOT NULL,
            color TEXT,
            thickness REAL,
            line_style TEXT,
            arrow_start INTEGER DEFAULT 0,
            arrow_end INTEGER DEFAULT 0,
            FOREIGN KEY (mindmap_id) REFERENCES mindmaps(id) ON DELETE CASCADE,
            UNIQUE(mindmap_id, edge_id_text)
        )
        """)

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
        # Ensure columns exist for older DBs that predate these fields
        self._ensure_column("reading_outline", "notes_html", "TEXT")
        self._ensure_column("reading_outline", "display_order", "INTEGER")

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
        self.cursor.execute("""
            INSERT INTO instructions (project_id, key_questions_instr, thesis_instr, insights_instr, unresolved_instr)
            VALUES (?, '', '', '', '')
        """, (project_id,))
        self.conn.commit()
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
            details_dict.get('published', ''), details_dict.get('pages', ''), details_dict.get('assignment', ''),
            details_dict.get('level', ''), details_dict.get('classification', ''), reading_id
        ))
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
            # commit batched after loop to reduce I/O
        self.conn.commit()

    # ----------------------- reading outline -----------------------

    # These return Row objects (callers use ['field']); change to dicts on request.

    def get_reading_outline(self, reading_id, parent_id=None):
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
        return self.cursor.fetchall()

    def add_outline_section(self, reading_id, title, parent_id=None):
        # compute order
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
