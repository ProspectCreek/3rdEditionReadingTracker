# prospectcreek/3rdeditionreadingtracker/3rdEditionReadingTracker-f9372c7f456315b9a3fa82060c18255c8574e1ea/database_helpers/schema.py
import sqlite3


class SchemaSetup:

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
        # --- NEW: Print statement to confirm this function is running ---
        print("--- Running SchemaSetup.setup_database() ---")

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

            -- NEW UNITY FIELDS --
            unity_kind_of_work TEXT,
            unity_driving_question_id INTEGER,

            FOREIGN KEY (project_id) REFERENCES items(id) ON DELETE CASCADE,
            FOREIGN KEY (unity_driving_question_id) REFERENCES reading_driving_questions(id) ON DELETE SET NULL
        )
        """)

        # --- FIX: Check for and correct the bad _dq_old foreign key ---
        needs_fk_fix = False
        try:
            self.cursor.execute("PRAGMA foreign_key_list(readings)")
            f_keys = self.cursor.fetchall()
            # --- NEW: Print all found foreign keys for debugging ---
            if f_keys:
                print(f"DEBUG: Found foreign keys for 'readings' table: {[dict(k) for k in f_keys]}")

            for key in f_keys:
                # Check if any foreign key points to the old table
                # --- MODIFIED: Changed key['to'] to key['table'] ---
                if (key['table'] in ('_dq_old', '"_dq_old"', 'main._dq_old')) and key[
                    'from'] == 'unity_driving_question_id':
                    needs_fk_fix = True
                    print(f"DEBUG: Found bad foreign key: {dict(key)}")
                    break
        except Exception as e:
            print(f"Note: Could not inspect foreign keys (may be new db): {e}")

        if needs_fk_fix:
            print("MIGRATION: Detected bad foreign key in 'readings' table. Rebuilding...")
            try:
                self.cursor.execute("PRAGMA foreign_keys = OFF")
                # We must commit before schema changes
                self.conn.commit()

                # 1. Rename old table
                self.cursor.execute("ALTER TABLE readings RENAME TO _readings_old_fk_fix")

                # 2. Create new table with correct schema (copied from above)
                self.cursor.execute("""
                CREATE TABLE readings (
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
                    unity_kind_of_work TEXT,
                    unity_driving_question_id INTEGER,
                    FOREIGN KEY (project_id) REFERENCES items(id) ON DELETE CASCADE,
                    FOREIGN KEY (unity_driving_question_id) REFERENCES reading_driving_questions(id) ON DELETE SET NULL
                )
                """)

                # 3. Get columns from old table to copy
                self.cursor.execute("PRAGMA table_info(_readings_old_fk_fix)")
                old_cols = [row['name'] for row in self.cursor.fetchall()]

                # Get columns from new table
                self.cursor.execute("PRAGMA table_info(readings)")
                new_cols = [row['name'] for row in self.cursor.fetchall()]

                # Find common columns
                cols_to_copy = [col for col in old_cols if col in new_cols]
                cols_str = ", ".join(cols_to_copy)

                # 4. Copy data
                self.cursor.execute(f"INSERT INTO readings ({cols_str}) SELECT {cols_str} FROM _readings_old_fk_fix")

                # 5. Drop old table
                self.cursor.execute("DROP TABLE _readings_old_fk_fix")

                self.conn.commit()  # Commit the schema change
                self.cursor.execute("PRAGMA foreign_keys = ON")
                print("MIGRATION: 'readings' table rebuilt successfully.")
            except Exception as e:
                print(f"CRITICAL MIGRATION ERROR (readings fk): {e}. Rolling back...")
                self.conn.rollback()
                # Try to restore
                try:
                    self.cursor.execute("DROP TABLE IF EXISTS readings")
                    self.cursor.execute("ALTER TABLE _readings_old_fk_fix RENAME TO readings")
                except Exception as re:
                    print(f"CRITICAL ROLLBACK FAILED: {re}")
            self.cursor.execute("PRAGMA foreign_keys = ON")
        # --- END FIX ---

        self.cursor.execute("PRAGMA table_info(readings)")
        existing_read_cols = {row["name"] for row in self.cursor.fetchall()}

        # --- MODIFIED: Added new columns to this check ---
        cols_to_add_readings = {
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
            "unity_kind_of_work": "TEXT",
            "unity_driving_question_id": "INTEGER REFERENCES reading_driving_questions(id) ON DELETE SET NULL"
        }

        for col_name, col_type in cols_to_add_readings.items():
            if col_name not in existing_read_cols:
                try:
                    self.cursor.execute(f"ALTER TABLE readings ADD COLUMN {col_name} {col_type}")
                except sqlite3.OperationalError:
                    pass
        # --- END MODIFIED ---

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
        # --- MODIFIED: Added new columns for Parts tab ---
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS reading_outline (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reading_id INTEGER NOT NULL,
            parent_id INTEGER,
            section_title TEXT NOT NULL,
            notes_html TEXT,
            display_order INTEGER,

            -- NEW PARTS TAB FIELDS --
            part_function_html TEXT,
            part_relation_html TEXT,
            part_dependency_html TEXT,
            part_function_text_plain TEXT,
            part_relation_text_plain TEXT,
            part_dependency_text_plain TEXT,
            part_is_structural INTEGER DEFAULT 0,
            part_dq_id INTEGER,

            FOREIGN KEY (reading_id) REFERENCES readings(id) ON DELETE CASCADE,
            FOREIGN KEY (parent_id) REFERENCES reading_outline(id) ON DELETE CASCADE,
            FOREIGN KEY (part_dq_id) REFERENCES reading_driving_questions(id) ON DELETE SET NULL
        )
        """)

        # --- ADDITIVE MIGRATION FOR NEW OUTLINE COLUMNS ---
        self.cursor.execute("PRAGMA table_info(reading_outline)")
        existing_outline_cols = {row["name"] for row in self.cursor.fetchall()}

        cols_to_add_outline = {
            "part_function_html": "TEXT",
            "part_relation_html": "TEXT",
            "part_dependency_html": "TEXT",
            "part_function_text_plain": "TEXT",
            "part_relation_text_plain": "TEXT",
            "part_dependency_text_plain": "TEXT",
            "part_is_structural": "INTEGER DEFAULT 0",
            "part_dq_id": "INTEGER REFERENCES reading_driving_questions(id) ON DELETE SET NULL"
        }

        for col_name, col_type in cols_to_add_outline.items():
            if col_name not in existing_outline_cols:
                try:
                    self.cursor.execute(f"ALTER TABLE reading_outline ADD COLUMN {col_name} {col_type}")
                except sqlite3.OperationalError:
                    pass
        # --- END ADDITIVE MIGRATION ---

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
            extra_notes_text TEXT,
            FOREIGN KEY (reading_id) REFERENCES readings(id) ON DELETE CASCADE,
            FOREIGN KEY (parent_id) REFERENCES reading_driving_questions(id) ON DELETE CASCADE,
            FOREIGN KEY (outline_id) REFERENCES reading_outline(id) ON DELETE SET NULL
        )
        """)

        self.cursor.execute("PRAGMA foreign_keys = OFF")
        try:
            self.cursor.execute("PRAGMA table_info(reading_driving_questions)")
            existing_dq_cols = {row["name"] for row in self.cursor.fetchall()}

            # --- MODIFIED: Added check for new column to trigger rebuild if needed ---
            migration_needed = False
            if "reading_has_parts" in existing_dq_cols or \
                    "include_in_summary" in existing_dq_cols or \
                    "where_in_book" in existing_dq_cols or \
                    "extra_notes_text" not in existing_dq_cols:
                migration_needed = True

            if migration_needed:
                # --- MODIFIED: Use a unique temp name to avoid conflicts ---
                self.cursor.execute("ALTER TABLE reading_driving_questions RENAME TO _dq_temp_migration")

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
                    extra_notes_text TEXT, -- <-- ADDED
                    FOREIGN KEY (reading_id) REFERENCES readings(id) ON DELETE CASCADE,
                    FOREIGN KEY (parent_id) REFERENCES reading_driving_questions(id) ON DELETE CASCADE,
                    FOREIGN KEY (outline_id) REFERENCES reading_outline(id) ON DELETE SET NULL
                )
                """)

                # --- MODIFIED: Use a unique temp name ---
                self.cursor.execute("PRAGMA table_info(_dq_temp_migration)")
                old_cols = [row["name"] for row in self.cursor.fetchall()]

                new_cols = [
                    "id", "reading_id", "parent_id", "display_order", "question_text", "nickname",
                    "type", "question_category", "scope", "pages", "why_question",
                    "synthesis_tags", "is_working_question", "outline_id", "extra_notes_text"  # <-- ADDED
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

                # --- MODIFIED: Use a unique temp name ---
                self.cursor.execute(
                    f"INSERT INTO reading_driving_questions ({cols_str}) SELECT {cols_str} FROM _dq_temp_migration")

                # --- THIS IS THE FIX ---
                # It now drops the correct temporary table name
                self.cursor.execute("DROP TABLE _dq_temp_migration")
                # --- END OF THE FIX ---

                print("Successfully migrated reading_driving_questions table.")

        except Exception as e:
            print(f"Warning: Could not perform migration on reading_driving_questions. {e}")
            # --- FIX: Added rollback to ensure connection is clean ---
            self.conn.rollback()
            try:
                # We still want to try to restore the old table if it's in a half-migrated state
                # --- MODIFIED: Use a unique temp name ---
                self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='_dq_temp_migration'")
                if self.cursor.fetchone():
                    self.cursor.execute("DROP TABLE IF EXISTS reading_driving_questions")
                    # --- MODIFIED: Use a unique temp name ---
                    self.cursor.execute("ALTER TABLE _dq_temp_migration RENAME TO reading_driving_questions")
                    print("Rolled back reading_driving_questions migration.")
                    self.conn.commit()  # Commit the successful rollback
                else:
                    print("Rollback skipped: _dq_temp_migration not found.")
            except Exception as re:
                print(f"Critical error: Could not roll back migration. DB may be unstable. {re}")
                self.conn.rollback()  # Rollback the failed rollback

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

        # --- NEW: Proposition Tables ---
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS project_propositions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            display_name TEXT NOT NULL,
            proposition_html TEXT,
            display_order INTEGER,
            FOREIGN KEY (project_id) REFERENCES items(id) ON DELETE CASCADE
        )
        """)

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
            how_addressed TEXT,
            notes TEXT,
            FOREIGN KEY (proposition_id) REFERENCES project_propositions(id) ON DELETE CASCADE,
            FOREIGN KEY (reading_id) REFERENCES readings(id) ON DELETE CASCADE,
            FOREIGN KEY (outline_id) REFERENCES reading_outline(id) ON DELETE SET NULL
        )
        """)
        # --- END NEW ---

        # --- NEW: Argument Tables ---
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS reading_arguments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reading_id INTEGER NOT NULL,
            display_order INTEGER,
            claim_text TEXT,
            because_text TEXT,
            driving_question_id INTEGER,
            is_insight INTEGER DEFAULT 0,
            synthesis_tags TEXT, 
            FOREIGN KEY (reading_id) REFERENCES readings(id) ON DELETE CASCADE,
            FOREIGN KEY (driving_question_id) REFERENCES reading_driving_questions(id) ON DELETE SET NULL
        )
        """)

        # --- ADDITIVE MIGRATION FOR reading_arguments ---
        self.cursor.execute("PRAGMA table_info(reading_arguments)")
        existing_arg_cols = {row["name"] for row in self.cursor.fetchall()}

        if "synthesis_tags" not in existing_arg_cols:
            try:
                self.cursor.execute(f"ALTER TABLE reading_arguments ADD COLUMN synthesis_tags TEXT")
            except sqlite3.OperationalError:
                pass
        # --- END ADDITIVE MIGRATION ---

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS reading_argument_evidence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            argument_id INTEGER NOT NULL,
            outline_id INTEGER,
            pages_text TEXT,
            argument_text TEXT,
            reading_text TEXT,
            role_in_argument TEXT,
            evidence_type TEXT,
            status TEXT,
            rationale_text TEXT,
            FOREIGN KEY (argument_id) REFERENCES reading_arguments(id) ON DELETE CASCADE,
            FOREIGN KEY (outline_id) REFERENCES reading_outline(id) ON DELETE SET NULL
        )
        """)
        # --- END NEW ---

        # --- NEW: To-Do List Table ---
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS project_todo_list (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            display_name TEXT NOT NULL,
            task_html TEXT,
            notes_html TEXT,
            is_checked INTEGER DEFAULT 0,
            display_order INTEGER,
            FOREIGN KEY (project_id) REFERENCES items(id) ON DELETE CASCADE
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