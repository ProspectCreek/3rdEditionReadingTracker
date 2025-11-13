import sqlite3
import shutil
import os
import json


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

    def _migrate_to_global_tags(self):
        """
        Performs a one-time migration from project-specific tags to
        a global, de-duplicated tag table.
        """
        print("MIGRATION: Starting migration to global tag system...")
        try:
            self.cursor.execute("PRAGMA foreign_keys = OFF")

            # 1. Rename old tables
            self.cursor.execute("ALTER TABLE synthesis_tags RENAME TO _tags_old")
            self.cursor.execute("ALTER TABLE synthesis_anchors RENAME TO _anchors_old")
            self.cursor.execute("ALTER TABLE anchor_tag_links RENAME TO _links_old")

            # 2. Create new global synthesis_tags table
            self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS synthesis_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
            """)

            # 3. Populate new global tags table with unique names
            self.cursor.execute("INSERT INTO synthesis_tags (name) SELECT DISTINCT name FROM _tags_old")
            print("MIGRATION: Global tags table created.")

            # 4. Re-create synthesis_anchors table with new foreign key
            self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS synthesis_anchors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                reading_id INTEGER NOT NULL,
                outline_id INTEGER,
                tag_id INTEGER,
                unique_doc_id TEXT NOT NULL,
                selected_text TEXT,
                comment TEXT,
                FOREIGN KEY (project_id) REFERENCES items(id) ON DELETE CASCADE,
                FOREIGN KEY (reading_id) REFERENCES readings(id) ON DELETE CASCADE,
                FOREIGN KEY (outline_id) REFERENCES reading_outline(id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES synthesis_tags(id) ON DELETE SET NULL
            )
            """)

            # 5. Re-map and insert anchors
            self.cursor.execute("""
                INSERT INTO synthesis_anchors 
                    (id, project_id, reading_id, outline_id, unique_doc_id, selected_text, comment, tag_id)
                SELECT 
                    a.id, a.project_id, a.reading_id, a.outline_id, a.unique_doc_id, a.selected_text, a.comment, new_tags.id
                FROM _anchors_old a
                LEFT JOIN _tags_old ON a.tag_id = _tags_old.id
                LEFT JOIN synthesis_tags new_tags ON _tags_old.name = new_tags.name
            """)
            print("MIGRATION: Anchors re-mapped to new tag IDs.")

            # 6. Re-create anchor_tag_links table
            self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS anchor_tag_links (
                anchor_id INTEGER NOT NULL,
                tag_id INTEGER NOT NULL,
                FOREIGN KEY (anchor_id) REFERENCES synthesis_anchors(id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES synthesis_tags(id) ON DELETE CASCADE,
                PRIMARY KEY (anchor_id, tag_id)
            )
            """)

            # 7. Re-map and insert links
            self.cursor.execute("""
                INSERT INTO anchor_tag_links (anchor_id, tag_id)
                SELECT 
                    l.anchor_id, 
                    new_tags.id
                FROM _links_old l
                JOIN _tags_old ON l.tag_id = _tags_old.id
                JOIN synthesis_tags new_tags ON _tags_old.name = new_tags.name
            """)
            print("MIGRATION: Tag links re-mapped.")

            self.cursor.execute("""
                INSERT OR IGNORE INTO project_tag_links (project_id, tag_id)
                SELECT DISTINCT 
                    a.project_id, 
                    a.tag_id
                FROM synthesis_anchors a
                WHERE a.tag_id IS NOT NULL
            """)
            print("MIGRATION: Populated project_tag_links from existing anchors.")

            # 8. Drop old tables
            self.cursor.execute("DROP TABLE _tags_old")
            self.cursor.execute("DROP TABLE _anchors_old")
            self.cursor.execute("DROP TABLE _links_old")

            self.conn.commit()
            print("MIGRATION: Global tag migration successful.")

        except Exception as e:
            print(f"CRITICAL MIGRATION ERROR: {e}. Rolling back...")
            self.conn.rollback()
            # Try to restore original tables
            try:
                self.cursor.execute("DROP TABLE IF EXISTS synthesis_tags")
                self.cursor.execute("DROP TABLE IF EXISTS synthesis_anchors")
                self.cursor.execute("DROP TABLE IF EXISTS anchor_tag_links")
                self.cursor.execute("ALTER TABLE _tags_old RENAME TO synthesis_tags")
                self.cursor.execute("ALTER TABLE _anchors_old RENAME TO synthesis_anchors")
                self.cursor.execute("ALTER TABLE _links_old RENAME TO anchor_tag_links")
                print("MIGRATION: Rollback successful.")
            except Exception as re:
                print(f"CRITICAL MIGRATION ROLLBACK FAILED: {re}. Database may be in an inconsistent state.")
        finally:
            self.cursor.execute("PRAGMA foreign_keys = ON")

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

        # --- MODIFIED: Removed old HTML columns, added new ones ---
        cols_to_add = {
            "is_assignment": "INTEGER DEFAULT 0",
            "project_purpose_text": "TEXT",
            "project_goals_text": "TEXT",
            "key_questions_text": "TEXT",
            "thesis_text": "TEXT",
            "insights_text": "TEXT",
            "unresolved_text": "TEXT",
            "assignment_instructions_text": "TEXT",
            "assignment_draft_text": "TEXT",
            "synthesis_notes_html": "TEXT",  # Keep this one
        }

        for col_name, col_type in cols_to_add.items():
            if col_name not in existing_item_cols:
                try:
                    self.cursor.execute(f"ALTER TABLE items ADD COLUMN {col_name} {col_type}")
                except sqlite3.OperationalError:
                    pass

        # --- NEW: Drop old, unused HTML columns ---
        cols_to_drop = [
            "synthesis_terminology_html",
            "synthesis_propositions_html",
            "synthesis_issues_html"
        ]
        for col_name in cols_to_drop:
            if col_name in existing_item_cols:
                try:
                    # Note: SQLite < 3.35 doesn't support DROP COLUMN.
                    # This might fail, but it's low-risk.
                    self.cursor.execute(f"ALTER TABLE items DROP COLUMN {col_name}")
                except sqlite3.OperationalError as e:
                    print(f"Note: Could not drop old column {col_name} (this is often ok): {e}")
        # --- END MODIFICATION ---

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
            propositions_html TEXT,
            unity_html TEXT,
            key_terms_html TEXT,
            arguments_html TEXT,
            gaps_html TEXT,
            theories_html TEXT,
            personal_dialogue_html TEXT,
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
            "propositions_html": "TEXT",
            "unity_html": "TEXT",
            "key_terms_html": "TEXT",
            "arguments_html": "TEXT",
            "gaps_html": "TEXT",
            "theories_html": "TEXT",
            "personal_dialogue_html": "TEXT",
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

        self.cursor.execute("PRAGMA table_info(mindmap_edges)")
        edge_cols = {row["name"] for row in self.cursor.fetchall()}
        if "from_node_id" in edge_cols:
            print("Detected old mindmap_edges schema, attempting to rebuild...")
            try:
                self.cursor.execute("DROP TABLE mindmap_edges")
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

        self.cursor.execute("PRAGMA foreign_keys = OFF")
        try:
            self.cursor.execute("PRAGMA table_info(reading_driving_questions)")
            existing_dq_cols = {row["name"] for row in self.cursor.fetchall()}

            if "reading_has_parts" in existing_dq_cols or "include_in_summary" in existing_dq_cols or "where_in_book" in existing_dq_cols:

                self.cursor.execute("ALTER TABLE reading_driving_questions RENAME TO _dq_old")

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

                self.cursor.execute("PRAGMA table_info(_dq_old)")
                old_cols = [row["name"] for row in self.cursor.fetchall()]

                new_cols = [
                    "id", "reading_id", "parent_id", "display_order", "question_text", "nickname",
                    "type", "question_category", "scope", "pages", "why_question",
                    "synthesis_tags", "is_working_question", "outline_id"
                ]

                if "where_in_book" in old_cols:
                    try:
                        idx = old_cols.index("where_in_book")
                        if 'outline_id' not in old_cols:
                            old_cols[idx] = "outline_id"
                        else:
                            old_cols.pop(idx)
                    except ValueError:
                        pass

                cols_to_copy = [col for col in new_cols if col in old_cols]
                cols_str = ", ".join(cols_to_copy)

                self.cursor.execute(
                    f"INSERT INTO reading_driving_questions ({cols_str}) SELECT {cols_str} FROM _dq_old")
                self.cursor.execute("DROP TABLE _dq_old")
                print("Successfully migrated reading_driving_questions table.")

        except Exception as e:
            print(f"Warning: Could not perform migration on reading_driving_questions. {e}")
            try:
                self.cursor.execute("DROP TABLE IF EXISTS reading_driving_questions")
                self.cursor.execute("ALTER TABLE _dq_old RENAME TO reading_driving_questions")
                print("Rolled back reading_driving_questions migration.")
            except Exception as re:
                print(f"Critical error: Could not roll back migration. DB may be unstable. {re}")

        self.cursor.execute("PRAGMA foreign_keys = ON")

        # --- Synthesis Tables ---
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS synthesis_tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
        """)

        self.cursor.execute("PRAGMA table_info(synthesis_tags)")
        tag_cols = {row["name"] for row in self.cursor.fetchall()}
        if "project_id" in tag_cols:
            self._migrate_to_global_tags()

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS synthesis_anchors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            reading_id INTEGER NOT NULL,
            outline_id INTEGER,
            tag_id INTEGER,
            unique_doc_id TEXT NOT NULL,
            selected_text TEXT,
            comment TEXT,
            FOREIGN KEY (project_id) REFERENCES items(id) ON DELETE CASCADE,
            FOREIGN KEY (reading_id) REFERENCES readings(id) ON DELETE CASCADE,
            FOREIGN KEY (outline_id) REFERENCES reading_outline(id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES synthesis_tags(id) ON DELETE SET NULL
        )
        """)

        self.cursor.execute("PRAGMA table_info(synthesis_anchors)")
        anchor_cols = {row["name"] for row in self.cursor.fetchall()}
        if "tag_id" not in anchor_cols:
            print("Migrating synthesis_anchors: adding tag_id column...")
            try:
                self.cursor.execute(
                    "ALTER TABLE synthesis_anchors ADD COLUMN tag_id INTEGER REFERENCES synthesis_tags(id) ON DELETE SET NULL")
            except sqlite3.OperationalError as e:
                print(f"Migration warning: {e}")

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS anchor_tag_links (
            anchor_id INTEGER NOT NULL,
            tag_id INTEGER NOT NULL,
            FOREIGN KEY (anchor_id) REFERENCES synthesis_anchors(id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES synthesis_tags(id) ON DELETE CASCADE,
            PRIMARY KEY (anchor_id, tag_id)
        )
        """)

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS project_tag_links (
            project_id INTEGER NOT NULL,
            tag_id INTEGER NOT NULL,
            FOREIGN KEY (project_id) REFERENCES items(id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES synthesis_tags(id) ON DELETE CASCADE,
            PRIMARY KEY (project_id, tag_id)
        )
        """)

        # --- NEW: Terminology Tables ---
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS project_terminology (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            term TEXT NOT NULL,
            meaning TEXT,
            display_order INTEGER,
            FOREIGN KEY (project_id) REFERENCES items(id) ON DELETE CASCADE
        )
        """)

        # --- NEW: Table to link terminology to readings and store status ---
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS terminology_reading_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            terminology_id INTEGER NOT NULL,
            reading_id INTEGER NOT NULL,
            not_in_reading INTEGER DEFAULT 0,
            FOREIGN KEY (terminology_id) REFERENCES project_terminology(id) ON DELETE CASCADE,
            FOREIGN KEY (reading_id) REFERENCES readings(id) ON DELETE CASCADE,
            UNIQUE(terminology_id, reading_id)
        )
        """)
        # --- END NEW ---

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS terminology_references (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            terminology_id INTEGER NOT NULL,
            reading_id INTEGER NOT NULL,
            outline_id INTEGER,
            page_number TEXT,
            author_address TEXT,
            notes TEXT,
            FOREIGN KEY (terminology_id) REFERENCES project_terminology(id) ON DELETE CASCADE,
            FOREIGN KEY (reading_id) REFERENCES readings(id) ON DELETE CASCADE,
            FOREIGN KEY (outline_id) REFERENCES reading_outline(id) ON DELETE SET NULL
        )
        """)
        # --- END NEW ---

        # --- NEW: Project To-Do List Table ---
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS project_todo_list (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            display_name TEXT,
            task TEXT,
            notes TEXT,
            is_checked INTEGER DEFAULT 0,
            display_order INTEGER,
            FOREIGN KEY (project_id) REFERENCES items(id) ON DELETE CASCADE
        )
        """)
        # --- END NEW ---

        # --- NEW: Project Propositions ---
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS project_propositions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            proposition_text TEXT,
            importance_text TEXT,
            display_order INTEGER,
            FOREIGN KEY (project_id) REFERENCES items(id) ON DELETE CASCADE
        )
        """)
        # --- FIX: Defensively add proposition_text if proposition exists ---
        self.cursor.execute("PRAGMA table_info(project_propositions)")
        prop_cols = {row["name"] for row in self.cursor.fetchall()}
        if "proposition" in prop_cols and "proposition_text" not in prop_cols:
            try:
                self.cursor.execute("ALTER TABLE project_propositions ADD COLUMN proposition_text TEXT")
                self.cursor.execute("UPDATE project_propositions SET proposition_text = proposition")
                # We can't safely drop 'proposition' in one go, so we'll just leave it
                # and new code will use 'proposition_text'
                print("MIGRATION: Added 'proposition_text' to 'project_propositions' and copied data.")
            except sqlite3.OperationalError as e:
                print(f"Warning: Could not migrate 'project_propositions' table: {e}")
        elif "proposition" not in prop_cols and "proposition_text" not in prop_cols:
            try:
                # This handles the case where the table was created but somehow is missing BOTH
                self.cursor.execute("ALTER TABLE project_propositions ADD COLUMN proposition_text TEXT")
            except sqlite3.OperationalError as e:
                print(f"Warning: Could not add 'proposition_text' to 'project_propositions' table: {e}")
        # --- END FIX ---

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS proposition_reading_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proposition_id INTEGER NOT NULL,
            reading_id INTEGER NOT NULL,
            not_in_reading INTEGER DEFAULT 0,
            FOREIGN KEY (proposition_id) REFERENCES project_propositions(id) ON DELETE CASCADE,
            FOREIGN KEY (reading_id) REFERENCES readings(id) ON DELETE CASCADE,
            UNIQUE(proposition_id, reading_id)
        )
        """)
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS proposition_references (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proposition_id INTEGER NOT NULL,
            reading_id INTEGER NOT NULL,
            outline_id INTEGER,
            page_number TEXT,
            author_address TEXT,
            notes TEXT,
            FOREIGN KEY (proposition_id) REFERENCES project_propositions(id) ON DELETE CASCADE,
            FOREIGN KEY (reading_id) REFERENCES readings(id) ON DELETE CASCADE,
            FOREIGN KEY (outline_id) REFERENCES reading_outline(id) ON DELETE SET NULL
        )
        """)
        # --- END NEW ---

        # --- NEW: Reading Leading Propositions ---
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS reading_leading_propositions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reading_id INTEGER NOT NULL,
            proposition_text TEXT,
            outline_id INTEGER,
            pages TEXT,
            importance_text TEXT,
            synthesis_tags TEXT,
            display_order INTEGER,
            FOREIGN KEY (reading_id) REFERENCES readings(id) ON DELETE CASCADE,
            FOREIGN KEY (outline_id) REFERENCES reading_outline(id) ON DELETE SET NULL
        )
        """)
        # --- END NEW ---

        self.cursor.execute("PRAGMA user_version")
        user_version = self.cursor.fetchone()[0]
        if user_version < 1:
            try:
                print("MIGRATION (v1): Populating project_tag_links from existing anchors...")
                self.cursor.execute("""
                    INSERT OR IGNORE INTO project_tag_links (project_id, tag_id)
                    SELECT DISTINCT 
                        a.project_id, 
                        a.tag_id
                    FROM synthesis_anchors a
                    WHERE a.tag_id IS NOT NULL
                """)
                self.cursor.execute("PRAGMA user_version = 1")
                self.conn.commit()
                print("MIGRATION (v1): project_tag_links population complete.")
            except Exception as e:
                print(f"MIGRATION ERROR (user_version 1): {e}")
                self.conn.rollback()

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

    def get_all_classes(self):
        """Gets all items that are of type 'class'."""
        self.cursor.execute("""
            SELECT * FROM items 
            WHERE type = 'class' 
            ORDER BY display_order, name
        """)
        return self._map_rows(self.cursor.fetchall())

    def move_item(self, item_id, new_parent_id):
        """Moves an item to a new parent."""
        new_order = self._next_item_order(new_parent_id)

        self.cursor.execute("""
            UPDATE items 
            SET parent_id = ?, display_order = ? 
            WHERE id = ?
        """, (new_parent_id, new_order, item_id))
        self.conn.commit()

    def update_order(self, ordered_ids):
        """
        Updates the display_order for a list of sibling IDs.
        Assumes all items in the list have the same parent.
        """
        for order, item_id in enumerate(ordered_ids):
            self.cursor.execute(
                "UPDATE items SET display_order = ? WHERE id = ?",
                (order, item_id)
            )
        self.conn.commit()

    def update_assignment_status(self, project_id, new_status_val):
        """Updates the is_assignment flag and clears data if set to 0."""
        self.cursor.execute(
            "UPDATE items SET is_assignment = ? WHERE id = ?",
            (int(new_status_val), project_id)
        )
        if int(new_status_val) == 0:
            self.cursor.execute("DELETE FROM rubric_components WHERE project_id = ?", (project_id,))
            self.cursor.execute(
                "UPDATE items SET assignment_instructions_text = NULL, assignment_draft_text = NULL WHERE id = ?",
                (project_id,)
            )
        self.conn.commit()

    def duplicate_item(self, item_id):
        """Duplicates an item (project) and its children (readings, etc.)."""
        original_project = self.get_item_details(item_id)
        if not original_project:
            return

        new_name = f"{original_project['name']} (Copy)"
        new_project_id = self.create_item(
            new_name,
            original_project['type'],
            original_project['parent_id'],
            original_project['is_assignment']
        )

        fields_to_copy = [
            'project_purpose_text', 'project_goals_text', 'key_questions_text',
            'thesis_text', 'insights_text', 'unresolved_text',
            'assignment_instructions_text', 'assignment_draft_text'
        ]
        set_clause = ", ".join([f"{field} = ?" for field in fields_to_copy])
        values = [original_project[field] for field in fields_to_copy]
        values.append(new_project_id)

        self.cursor.execute(f"UPDATE items SET {set_clause} WHERE id = ?", tuple(values))

        original_readings = self.get_readings(item_id)
        for reading in original_readings:
            new_reading_id = self.db.add_reading(
                new_project_id,
                reading['title'],
                reading['author'],
                reading['nickname']
            )
            reading_details = {
                'title': reading['title'], 'author': reading['author'], 'nickname': reading['nickname'],
                'published': reading['published'], 'pages': reading['pages'], 'assignment': reading['assignment'],
                'level': reading['level'], 'classification': reading['classification']
            }
            self.update_reading_details(new_reading_id, reading_details)

            self._copy_reading_outline(reading['id'], new_reading_id, None, None)

        original_rubric = self.get_rubric_components(item_id)
        for comp in original_rubric:
            self.add_rubric_component(new_project_id, comp['component_text'])

        original_instr = self.get_or_create_instructions(item_id)
        if original_instr:
            self.update_instructions(
                new_project_id,
                original_instr['key_questions_instr'],
                original_instr['thesis_instr'],
                original_instr['insights_instr'],
                original_instr['unresolved_instr']
            )

        self.conn.commit()

    def _copy_reading_outline(self, old_reading_id, new_reading_id, old_parent_id, new_parent_id):
        """Recursive helper to duplicate reading outline."""
        original_items = self.get_reading_outline(old_reading_id, old_parent_id)
        for item in original_items:
            self.cursor.execute("""
                INSERT INTO reading_outline (reading_id, parent_id, section_title, notes_html, display_order)
                VALUES (?, ?, ?, ?, ?)
            """, (new_reading_id, new_parent_id, item['section_title'], item['notes_html'], item['display_order']))

            new_item_id = self.cursor.lastrowid
            self._copy_reading_outline(old_reading_id, new_reading_id, item['id'], new_item_id)

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

    def update_project_text_field(self, project_id, field_name, html_text):
        self.cursor.execute(f"UPDATE items SET {field_name} = ? WHERE id = ?", (html_text, project_id))
        self.conn.commit()

    # ------------------------- instructions -------------------------

    def get_or_create_instructions(self, project_id):
        self.cursor.execute("SELECT * FROM instructions WHERE project_id = ?", (project_id,))
        row = self.cursor.fetchone()
        if row:
            return self._rowdict(row)

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
                pass
            except Exception as e:
                print(f"Error creating default instructions: {e}")
                return {}

        self.cursor.execute("SELECT * FROM instructions WHERE project_id = ?", (project_id,))
        row = self.cursor.fetchone()
        return self._rowdict(row) if row else {}

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

    def update_reading_nickname(self, reading_id, new_name):
        self.cursor.execute("UPDATE readings SET nickname = ? WHERE id = ?", (new_name, reading_id))
        self.conn.commit()

    def update_reading_field(self, reading_id, field_name, html):
        """Updates a single text field for a reading, using a whitelist."""
        allowed_fields = [
            'propositions_html', 'unity_html', 'key_terms_html',
            'arguments_html', 'gaps_html', 'theories_html',
            'personal_dialogue_html'
        ]
        if field_name not in allowed_fields:
            print(f"Error: Attempt to update invalid field {field_name}")
            return

        self.cursor.execute(
            f"UPDATE readings SET {field_name} = ? WHERE id = ?",
            (html, reading_id)
        )
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

    # ----------------------- reading driving questions -----------------------

    def get_driving_questions(self, reading_id, parent_id=None):
        sql = "SELECT * FROM reading_driving_questions WHERE reading_id = ?"
        params = [reading_id]

        if parent_id is None:
            sql += " AND parent_id IS NULL"
        elif parent_id is True:
            pass
        else:
            sql += " AND parent_id = ?"
            params.append(parent_id)

        sql += " ORDER BY display_order, id"
        self.cursor.execute(sql, tuple(params))
        return self._map_rows(self.cursor.fetchall())

    def get_driving_question_details(self, question_id):
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
        self.cursor.execute("DELETE FROM reading_driving_questions WHERE id = ?", (question_id,))
        self.conn.commit()

    def update_driving_question_order(self, ordered_ids):
        for order, q_id in enumerate(ordered_ids):
            self.cursor.execute(
                "UPDATE reading_driving_questions SET display_order = ? WHERE id = ?",
                (order, q_id)
            )
        self.conn.commit()

    def find_current_working_question(self, reading_id):
        self.cursor.execute(
            "SELECT * FROM reading_driving_questions WHERE reading_id = ? AND is_working_question = 1 LIMIT 1",
            (reading_id,)
        )
        return self._rowdict(self.cursor.fetchone())

    def clear_all_working_questions(self, reading_id):
        self.cursor.execute(
            "UPDATE reading_driving_questions SET is_working_question = 0 WHERE reading_id = ?",
            (reading_id,)
        )
        self.conn.commit()

    # --- Synthesis Functions (NOW GLOBAL) ---

    def get_all_tags(self):
        """Gets all tags from the global table."""
        self.cursor.execute("SELECT id, name FROM synthesis_tags ORDER BY name")
        return self._map_rows(self.cursor.fetchall())

    def get_or_create_tag(self, tag_name, project_id=None):
        tag_name = tag_name.strip()
        if not tag_name:
            return None

        self.cursor.execute(
            "SELECT * FROM synthesis_tags WHERE name = ?",
            (tag_name,)
        )
        tag = self._rowdict(self.cursor.fetchone())

        if not tag:
            try:
                self.cursor.execute(
                    "INSERT INTO synthesis_tags (name) VALUES (?)",
                    (tag_name,)
                )
                self.conn.commit()
                new_id = self.cursor.lastrowid
                tag = {'id': new_id, 'name': tag_name}
            except sqlite3.IntegrityError:
                self.cursor.execute(
                    "SELECT * FROM synthesis_tags WHERE name = ?",
                    (tag_name,)
                )
                tag = self._rowdict(self.cursor.fetchone())
            except Exception as e:
                print(f"Error in get_or_create_tag: {e}")
                return None

        if not tag:
            return None

        if project_id:
            try:
                self.cursor.execute(
                    "INSERT OR IGNORE INTO project_tag_links (project_id, tag_id) VALUES (?, ?)",
                    (project_id, tag['id'])
                )
                self.conn.commit()
            except Exception as e:
                print(f"Error linking tag {tag['id']} to project {project_id}: {e}")

        return tag

    def get_project_tags(self, project_id):
        self.cursor.execute("""
            SELECT DISTINCT t.id, t.name 
            FROM synthesis_tags t
            LEFT JOIN synthesis_anchors a ON t.id = a.tag_id AND a.project_id = ?
            LEFT JOIN project_tag_links ptl ON t.id = ptl.tag_id
            WHERE ptl.project_id = ? OR a.project_id = ?
            ORDER BY t.name
        """, (project_id, project_id, project_id))
        return self._map_rows(self.cursor.fetchall())

    def create_anchor(self, project_id, reading_id, outline_id, tag_id, selected_text, comment, unique_doc_id):
        try:
            self.cursor.execute("""
                INSERT INTO synthesis_anchors 
                (project_id, reading_id, outline_id, selected_text, comment, unique_doc_id, tag_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                project_id, reading_id, outline_id, selected_text, comment, unique_doc_id, tag_id
            ))
            anchor_id = self.cursor.lastrowid

            self.cursor.execute(
                "INSERT OR IGNORE INTO anchor_tag_links (anchor_id, tag_id) VALUES (?, ?)",
                (anchor_id, tag_id)
            )

            self.cursor.execute(
                "INSERT OR IGNORE INTO project_tag_links (project_id, tag_id) VALUES (?, ?)",
                (project_id, tag_id)
            )

            self.conn.commit()
            return anchor_id
        except Exception as e:
            self.conn.rollback()
            print(f"Error creating anchor: {e}")
            return None

    def update_anchor(self, anchor_id, new_tag_id, new_comment):
        try:
            self.cursor.execute(
                "UPDATE synthesis_anchors SET comment = ?, tag_id = ? WHERE id = ?",
                (new_comment, new_tag_id, anchor_id)
            )

            self.cursor.execute("DELETE FROM anchor_tag_links WHERE anchor_id = ?", (anchor_id,))

            self.cursor.execute(
                "INSERT OR IGNORE INTO anchor_tag_links (anchor_id, tag_id) VALUES (?, ?)",
                (anchor_id, new_tag_id)
            )

            self.cursor.execute("SELECT project_id FROM synthesis_anchors WHERE id = ?", (anchor_id,))
            res = self.cursor.fetchone()
            if res:
                project_id = res['project_id']
                self.cursor.execute(
                    "INSERT OR IGNORE INTO project_tag_links (project_id, tag_id) VALUES (?, ?)",
                    (project_id, new_tag_id)
                )

            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            print(f"Error updating anchor: {e}")

    def delete_anchor(self, anchor_id):
        self.cursor.execute("DELETE FROM synthesis_anchors WHERE id = ?", (anchor_id,))
        self.conn.commit()

    def get_anchor_details(self, anchor_id):
        self.cursor.execute("""
            SELECT a.*, t.name as tag_name, t.id as tag_id
            FROM synthesis_anchors a
            LEFT JOIN synthesis_tags t ON a.tag_id = t.id
            WHERE a.id = ?
        """, (anchor_id,))
        return self._rowdict(self.cursor.fetchone())

    def get_anchor_by_id(self, anchor_id):
        self.cursor.execute("SELECT id FROM synthesis_anchors WHERE id = ?", (anchor_id,))
        return self._rowdict(self.cursor.fetchone())

    def get_anchors_for_project(self, project_id):
        self.cursor.execute(
            "SELECT * FROM synthesis_anchors WHERE project_id = ?", (project_id,)
        )
        return self._map_rows(self.cursor.fetchall())

    def get_anchors_for_tag(self, tag_id):
        self.cursor.execute("""
            SELECT a.* FROM synthesis_anchors a
            JOIN anchor_tag_links l ON a.id = l.anchor_id
            WHERE l.tag_id = ?
        """, (tag_id,))
        return self._map_rows(self.cursor.fetchall())

    # --- Synthesis Tab Functions ---

    def get_tags_with_counts(self, project_id):
        sql = """
            SELECT 
                t.id, 
                t.name, 
                COUNT(a.id) as anchor_count
            FROM synthesis_tags t
            LEFT JOIN project_tag_links ptl ON t.id = ptl.tag_id
            LEFT JOIN synthesis_anchors a ON t.id = a.tag_id AND a.project_id = ?
            WHERE ptl.project_id = ? OR a.project_id = ?
            GROUP BY t.id, t.name
            ORDER BY t.name
        """
        self.cursor.execute(sql, (project_id, project_id, project_id))
        return self._map_rows(self.cursor.fetchall())

    def get_anchors_for_tag_with_context(self, tag_id):
        sql = """
            SELECT 
                a.id, 
                a.selected_text, 
                a.comment,
                r.id as reading_id,
                r.title as reading_title,
                r.nickname as reading_nickname,
                o.id as outline_id,
                o.section_title as outline_title
            FROM synthesis_anchors a
            JOIN anchor_tag_links l ON a.id = l.anchor_id
            LEFT JOIN readings r ON a.reading_id = r.id
            LEFT JOIN reading_outline o ON a.outline_id = o.id
            WHERE l.tag_id = ?
            ORDER BY r.display_order, o.display_order, a.id
        """
        self.cursor.execute(sql, (tag_id,))
        return self._map_rows(self.cursor.fetchall())

    def get_anchors_for_tag_simple(self, tag_id):
        sql = """
            SELECT a.id, a.selected_text, a.comment
            FROM synthesis_anchors a
            JOIN anchor_tag_links l ON a.id = l.anchor_id
            WHERE l.tag_id = ?
            ORDER BY a.id
        """
        self.cursor.execute(sql, (tag_id,))
        return self._map_rows(self.cursor.fetchall())

    # --- Tag Management Functions (now global) ---
    def rename_tag(self, tag_id, new_name):
        """Renames a tag globally. Checks for uniqueness conflict."""
        try:
            self.cursor.execute(
                "UPDATE synthesis_tags SET name = ? WHERE id = ?",
                (new_name, tag_id)
            )
            self.conn.commit()
        except sqlite3.IntegrityError:
            raise Exception(f"A tag named '{new_name}' already exists.")

    def delete_tag_and_anchors(self, tag_id):
        try:
            self.cursor.execute("SELECT anchor_id FROM anchor_tag_links WHERE tag_id = ?", (tag_id,))
            anchor_ids = [row[0] for row in self.cursor.fetchall()]

            if anchor_ids:
                self.cursor.executemany(
                    "DELETE FROM synthesis_anchors WHERE id = ?",
                    [(aid,) for aid in anchor_ids]
                )

            self.cursor.execute("DELETE FROM project_tag_links WHERE tag_id = ?", (tag_id,))

            self.cursor.execute("DELETE FROM synthesis_tags WHERE id = ?", (tag_id,))

            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            print(f"Error deleting tag and anchors: {e}")
            raise

    def merge_tags(self, source_tag_id, target_tag_id):
        """Merges one tag into another, updating all anchors and links."""
        try:
            self.cursor.execute(
                "UPDATE synthesis_anchors SET tag_id = ? WHERE tag_id = ?",
                (target_tag_id, source_tag_id)
            )
            # --- FIX: Typo was here ---
            self.cursor.execute(
                "UPDATE OR IGNORE anchor_tag_links SET tag_id = ? WHERE tag_id = ?",
                (target_tag_id, source_tag_id)
            )
            # --- END FIX ---
            self.cursor.execute(
                "DELETE FROM anchor_tag_links WHERE tag_id = ?", (source_tag_id,)
            )
            self.cursor.execute(
                "UPDATE OR IGNORE project_tag_links SET tag_id = ? WHERE tag_id = ?",
                (target_tag_id, source_tag_id)
            )
            self.cursor.execute(
                "DELETE FROM project_tag_links WHERE tag_id = ?", (source_tag_id,)
            )
            self.cursor.execute("DELETE FROM synthesis_tags WHERE id = ?", (source_tag_id,))
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            raise Exception(f"Failed to merge tags: {e}")

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

    # ----------------------- NEW: Terminology Functions -----------------------

    def get_all_outline_items_for_project(self, project_id):
        """
        Gets all outline items for all readings in a project.
        Returns a dict mapping: { reading_id: [ (display_text, outline_id), ... ] }
        """
        readings_sql = "SELECT id FROM readings WHERE project_id = ?"
        self.cursor.execute(readings_sql, (project_id,))
        readings = self.cursor.fetchall()
        outline_map = {}

        for reading in readings:
            reading_id = reading['id']
            outline_map[reading_id] = []

            def build_flat_list(parent_id, indent_level):
                # Use _map_rows to get list[dict]
                items = self.get_reading_outline(reading_id, parent_id)
                for item in items:
                    display_text = ("  " * indent_level) + item['section_title']
                    outline_map[reading_id].append((display_text, item['id']))
                    # Recursive call
                    build_flat_list(item['id'], indent_level + 1)

            build_flat_list(None, 0)  # Start from root
        return outline_map

    def save_terminology_entry(self, project_id, terminology_id, data):
        """
        Saves a single terminology entry, including its term, meaning,
        and all associated references. This is a transactional operation.
        """
        try:
            # 1. Add or Update the main term
            if terminology_id:
                # Update existing term
                self.cursor.execute("""
                    UPDATE project_terminology
                    SET term = ?, meaning = ?
                    WHERE id = ? AND project_id = ?
                """, (data['term'], data['meaning'], terminology_id, project_id))
            else:
                # Insert new term and get its ID
                self.cursor.execute(
                    "SELECT COALESCE(MAX(display_order), -1) FROM project_terminology WHERE project_id = ?",
                    (project_id,))
                new_order = (self.cursor.fetchone()[0] or -1) + 1

                self.cursor.execute("""
                    INSERT INTO project_terminology (project_id, term, meaning, display_order)
                    VALUES (?, ?, ?, ?)
                """, (project_id, data['term'], data['meaning'], new_order))
                terminology_id = self.cursor.lastrowid

            if not terminology_id:
                raise Exception("Failed to create or find terminology ID.")

            # 2. Delete all existing references for this term
            self.cursor.execute("DELETE FROM terminology_references WHERE terminology_id = ?", (terminology_id,))

            # 3. Update or Insert the status for ALL readings
            status_data = []
            for status in data.get("statuses", []):
                status_data.append((
                    terminology_id,
                    status.get('reading_id'),
                    status.get('not_in_reading', 0)
                ))

            if status_data:
                self.cursor.executemany("""
                    INSERT INTO terminology_reading_links (terminology_id, reading_id, not_in_reading)
                    VALUES (?, ?, ?)
                    ON CONFLICT(terminology_id, reading_id) DO UPDATE SET
                    not_in_reading = excluded.not_in_reading
                """, status_data)

            # 4. Insert all new references
            references_data = []
            # Get the set of readings marked as "not in reading"
            not_in_reading_ids = {s['reading_id'] for s in data.get("statuses", []) if s['not_in_reading'] == 1}

            for ref in data.get("references", []):
                if ref.get('reading_id') not in not_in_reading_ids:
                    references_data.append((
                        terminology_id,
                        ref.get('reading_id'),
                        ref.get('outline_id'),
                        ref.get('page_number'),
                        ref.get('author_address'),
                        ref.get('notes')
                    ))

            if references_data:
                self.cursor.executemany("""
                    INSERT INTO terminology_references 
                    (terminology_id, reading_id, outline_id, page_number, author_address, notes)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, references_data)

            # 5. Commit transaction
            self.conn.commit()

        except Exception as e:
            self.conn.rollback()
            print(f"Error saving terminology entry: {e}")
            raise

    def get_project_terminology(self, project_id):
        """
        Gets a list of all terms for a project, ordered by display_order.
        """
        self.cursor.execute("""
            SELECT id, term
            FROM project_terminology
            WHERE project_id = ?
            ORDER BY display_order, id
        """, (project_id,))
        return self._map_rows(self.cursor.fetchall())

    def get_terminology_details(self, terminology_id):
        """
        Gets the full details for a single term, including its references.
        """
        # 1. Get the main term data
        self.cursor.execute("SELECT * FROM project_terminology WHERE id = ?", (terminology_id,))
        term_data = self._rowdict(self.cursor.fetchone())

        if not term_data:
            return None

        # 2. Get all associated references, joining to get outline title
        self.cursor.execute("""
            SELECT 
                tr.*, 
                ro.section_title 
            FROM terminology_references tr
            LEFT JOIN reading_outline ro ON tr.outline_id = ro.id
            WHERE tr.terminology_id = ?
        """, (terminology_id,))
        references = self._map_rows(self.cursor.fetchall())
        term_data['references'] = references

        # 3. Get all reading link statuses
        self.cursor.execute("""
            SELECT reading_id, not_in_reading
            FROM terminology_reading_links
            WHERE terminology_id = ?
        """, (terminology_id,))
        statuses = self.cursor.fetchall()
        term_data['statuses'] = {row['reading_id']: row['not_in_reading'] for row in statuses}

        return term_data

    def delete_terminology(self, terminology_id):
        """
        Deletes a terminology entry. Cascade delete handles references.
        """
        self.cursor.execute("DELETE FROM project_terminology WHERE id = ?", (terminology_id,))
        self.conn.commit()

    def update_terminology_order(self, ordered_ids):
        """
        Updates the display_order for a list of terminology IDs.
        """
        for order, term_id in enumerate(ordered_ids):
            self.cursor.execute(
                "UPDATE project_terminology SET display_order = ? WHERE id = ?",
                (order, term_id)
            )
        self.conn.commit()

    # --- NEW: Project To-Do List Functions ---

    def get_project_todo_items(self, project_id):
        """Gets all to-do items for a project."""
        self.cursor.execute("""
            SELECT * FROM project_todo_list
            WHERE project_id = ?
            ORDER BY display_order, id
        """, (project_id,))
        return self._map_rows(self.cursor.fetchall())

    def get_todo_item_details(self, item_id):
        """Gets details for a single to-do item."""
        self.cursor.execute("SELECT * FROM project_todo_list WHERE id = ?", (item_id,))
        return self._rowdict(self.cursor.fetchone())

    def add_todo_item(self, project_id, data):
        """Adds a new to-do item."""
        self.cursor.execute(
            "SELECT COALESCE(MAX(display_order), -1) FROM project_todo_list WHERE project_id = ?",
            (project_id,))
        new_order = (self.cursor.fetchone()[0] or -1) + 1
        self.cursor.execute("""
            INSERT INTO project_todo_list (project_id, display_name, task, notes, is_checked, display_order)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            project_id, data.get('display_name'), data.get('task'),
            data.get('notes'), 0, new_order
        ))
        self.conn.commit()
        return self.cursor.lastrowid

    def update_todo_item(self, item_id, data):
        """Updates an existing to-do item."""
        self.cursor.execute("""
            UPDATE project_todo_list
            SET display_name = ?, task = ?, notes = ?
            WHERE id = ?
        """, (
            data.get('display_name'), data.get('task'), data.get('notes'), item_id
        ))
        self.conn.commit()

    def update_todo_item_checked(self, item_id, is_checked):
        """Updates the 'is_checked' status of a to-do item."""
        self.cursor.execute(
            "UPDATE project_todo_list SET is_checked = ? WHERE id = ?",
            (int(bool(is_checked)), item_id)
        )
        self.conn.commit()

    def delete_todo_item(self, item_id):
        """Deletes a to-do item."""
        self.cursor.execute("DELETE FROM project_todo_list WHERE id = ?", (item_id,))
        self.conn.commit()

    def update_todo_item_order(self, ordered_ids):
        """Updates the display_order for a list of to-do item IDs."""
        for order, item_id in enumerate(ordered_ids):
            self.cursor.execute(
                "UPDATE project_todo_list SET display_order = ? WHERE id = ?",
                (order, item_id)
            )
        self.conn.commit()

    # --- END NEW ---

    # --- NEW: Project Propositions Functions ---

    def get_project_propositions(self, project_id):
        """Gets all propositions for a project."""
        # --- FIX: Select proposition_text and alias it ---
        self.cursor.execute("""
            SELECT id, proposition_text AS proposition, display_order
            FROM project_propositions
            WHERE project_id = ?
            ORDER BY display_order, id
        """, (project_id,))
        return self._map_rows(self.cursor.fetchall())

    def get_proposition_details(self, proposition_id):
        """Gets details for a single proposition."""
        # --- FIX: Select proposition_text and alias it ---
        self.cursor.execute("""
            SELECT id, project_id, proposition_text AS proposition, importance_text, display_order
            FROM project_propositions 
            WHERE id = ?
        """, (proposition_id,))
        prop_data = self._rowdict(self.cursor.fetchone())
        # --- END FIX ---

        if not prop_data:
            return None

        self.cursor.execute("""
            SELECT 
                pr.*, 
                ro.section_title 
            FROM proposition_references pr
            LEFT JOIN reading_outline ro ON pr.outline_id = ro.id
            WHERE pr.proposition_id = ?
        """, (proposition_id,))
        references = self._map_rows(self.cursor.fetchall())
        prop_data['references'] = references

        self.cursor.execute("""
            SELECT reading_id, not_in_reading
            FROM proposition_reading_links
            WHERE proposition_id = ?
        """, (proposition_id,))
        statuses = self.cursor.fetchall()
        prop_data['statuses'] = {row['reading_id']: row['not_in_reading'] for row in statuses}

        return prop_data

    def save_proposition_entry(self, project_id, proposition_id, data):
        """Saves a single proposition entry and its references."""
        try:
            if proposition_id:
                # --- FIX: Update proposition_text column ---
                self.cursor.execute("""
                    UPDATE project_propositions
                    SET proposition_text = ?, importance_text = ?
                    WHERE id = ? AND project_id = ?
                """, (data['proposition'], data['importance_text'], proposition_id, project_id))
            else:
                self.cursor.execute(
                    "SELECT COALESCE(MAX(display_order), -1) FROM project_propositions WHERE project_id = ?",
                    (project_id,))
                new_order = (self.cursor.fetchone()[0] or -1) + 1
                # --- FIX: Insert into proposition_text column ---
                self.cursor.execute("""
                    INSERT INTO project_propositions (project_id, proposition_text, importance_text, display_order)
                    VALUES (?, ?, ?, ?)
                """, (project_id, data['proposition'], data['importance_text'], new_order))
                proposition_id = self.cursor.lastrowid

            if not proposition_id:
                raise Exception("Failed to create or find proposition ID.")

            self.cursor.execute("DELETE FROM proposition_references WHERE proposition_id = ?", (proposition_id,))
            self.cursor.execute("DELETE FROM proposition_reading_links WHERE proposition_id = ?", (proposition_id,))

            status_data = []
            for status in data.get("statuses", []):
                status_data.append((
                    proposition_id,
                    status.get('reading_id'),
                    status.get('not_in_reading', 0)
                ))

            if status_data:
                self.cursor.executemany("""
                    INSERT INTO proposition_reading_links (proposition_id, reading_id, not_in_reading)
                    VALUES (?, ?, ?)
                """, status_data)

            references_data = []
            not_in_reading_ids = {s['reading_id'] for s in data.get("statuses", []) if s['not_in_reading'] == 1}

            for ref in data.get("references", []):
                if ref.get('reading_id') not in not_in_reading_ids:
                    references_data.append((
                        proposition_id,
                        ref.get('reading_id'),
                        ref.get('outline_id'),
                        ref.get('page_number'),
                        ref.get('author_address'),
                        ref.get('notes')
                    ))

            if references_data:
                self.cursor.executemany("""
                    INSERT INTO proposition_references 
                    (proposition_id, reading_id, outline_id, page_number, author_address, notes)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, references_data)

            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            print(f"Error saving proposition entry: {e}")
            raise

    def delete_proposition(self, proposition_id):
        """Deletes a proposition entry."""
        self.cursor.execute("DELETE FROM project_propositions WHERE id = ?", (proposition_id,))
        self.conn.commit()

    def update_proposition_order(self, ordered_ids):
        """Updates the display_order for a list of proposition IDs."""
        for order, prop_id in enumerate(ordered_ids):
            self.cursor.execute(
                "UPDATE project_propositions SET display_order = ? WHERE id = ?",
                (order, prop_id)
            )
        self.conn.commit()

    # --- END NEW ---

    # --- NEW: Reading Leading Propositions Functions ---

    def get_reading_propositions(self, reading_id):
        """Gets all leading propositions for a specific reading."""
        self.cursor.execute("""
            SELECT * FROM reading_leading_propositions
            WHERE reading_id = ?
            ORDER BY display_order, id
        """, (reading_id,))
        return self._map_rows(self.cursor.fetchall())

    def get_reading_proposition_details(self, proposition_id):
        """Gets details for a single leading proposition."""
        self.cursor.execute("SELECT * FROM reading_leading_propositions WHERE id = ?", (proposition_id,))
        return self._rowdict(self.cursor.fetchone())

    def add_reading_proposition(self, reading_id, data):
        """Adds a new leading proposition to a reading."""
        self.cursor.execute(
            "SELECT COALESCE(MAX(display_order), -1) FROM reading_leading_propositions WHERE reading_id = ?",
            (reading_id,))
        new_order = (self.cursor.fetchone()[0] or -1) + 1

        self.cursor.execute("""
            INSERT INTO reading_leading_propositions (
                reading_id, proposition_text, outline_id, pages, 
                importance_text, synthesis_tags, display_order
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            reading_id, data.get("proposition_text"), data.get("outline_id"),
            data.get("pages"), data.get("importance_text"),
            data.get("synthesis_tags"), new_order
        ))
        self.conn.commit()
        return self.cursor.lastrowid

    def update_reading_proposition(self, proposition_id, data):
        """Updates an existing leading proposition."""
        self.cursor.execute("""
            UPDATE reading_leading_propositions SET
                proposition_text = ?, outline_id = ?, pages = ?, 
                importance_text = ?, synthesis_tags = ?
            WHERE id = ?
        """, (
            data.get("proposition_text"), data.get("outline_id"),
            data.get("pages"), data.get("importance_text"),
            data.get("synthesis_tags"), proposition_id
        ))
        self.conn.commit()

    def delete_reading_proposition(self, proposition_id):
        """Deletes a leading proposition."""
        self.cursor.execute("DELETE FROM reading_leading_propositions WHERE id = ?", (proposition_id,))
        self.conn.commit()

    def update_reading_proposition_order(self, ordered_ids):
        """Updates the display_order for a list of leading proposition IDs."""
        for order, item_id in enumerate(ordered_ids):
            self.cursor.execute(
                "UPDATE reading_leading_propositions SET display_order = ? WHERE id = ?",
                (order, item_id)
            )
        self.conn.commit()

    # --- END NEW ---

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