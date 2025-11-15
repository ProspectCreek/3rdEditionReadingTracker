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
        print("--- Running SchemaSetup.setup_database() ---")

        # --- FIX: Check version *before* creating tables ---
        self.cursor.execute("PRAGMA user_version")
        user_version = self.cursor.fetchone()[0]
        is_new_db = user_version == 0
        # --- END FIX ---

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
            synthesis_notes_html TEXT,
            FOREIGN KEY (parent_id) REFERENCES items(id) ON DELETE CASCADE
        )
        """)

        # Defensive additive migrations
        self.cursor.execute("PRAGMA table_info(items)")
        existing_item_cols = {row["name"] for row in self.cursor.fetchall()}

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
            "synthesis_notes_html": "TEXT",
        }

        for col_name, col_type in cols_to_add.items():
            if col_name not in existing_item_cols:
                try:
                    self.cursor.execute(f"ALTER TABLE items ADD COLUMN {col_name} {col_type}")
                except sqlite3.OperationalError:
                    pass

        cols_to_drop = [
            "synthesis_terminology_html",
            "synthesis_propositions_html",
            "synthesis_issues_html"
        ]
        for col_name in cols_to_drop:
            if col_name in existing_item_cols:
                try:
                    self.cursor.execute(f"ALTER TABLE items DROP COLUMN {col_name}")
                except sqlite3.OperationalError as e:
                    print(f"Note: Could not drop old column {col_name} (this is often ok): {e}")

        # --- Reading Driving Questions (CREATE EARLY - referenced by readings, outline) ---
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

        # --- Reading Outline (CREATE EARLY - referenced by driving_questions) ---
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS reading_outline (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reading_id INTEGER NOT NULL,
            parent_id INTEGER,
            section_title TEXT NOT NULL,
            notes_html TEXT,
            display_order INTEGER,
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

        # --- Readings (CREATE AFTER driving_questions and outline) ---
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
            unity_kind_of_work TEXT,
            unity_driving_question_id INTEGER,
            FOREIGN KEY (project_id) REFERENCES items(id) ON DELETE CASCADE,
            FOREIGN KEY (unity_driving_question_id) REFERENCES reading_driving_questions(id) ON DELETE SET NULL
        )
        """)

        self.cursor.execute("PRAGMA table_info(readings)")
        existing_read_cols = {row["name"] for row in self.cursor.fetchall()}
        cols_to_add_readings = {
            "nickname": "TEXT", "published": "TEXT", "pages": "TEXT",
            "assignment": "TEXT", "level": "TEXT", "classification": "TEXT",
            "propositions_html": "TEXT", "unity_html": "TEXT", "key_terms_html": "TEXT",
            "arguments_html": "TEXT", "gaps_html": "TEXT", "theories_html": "TEXT",
            "personal_dialogue_html": "TEXT", "unity_kind_of_work": "TEXT",
            "unity_driving_question_id": "INTEGER REFERENCES reading_driving_questions(id) ON DELETE SET NULL"
        }
        for col_name, col_type in cols_to_add_readings.items():
            if col_name not in existing_read_cols:
                try:
                    self.cursor.execute(f"ALTER TABLE readings ADD COLUMN {col_name} {col_type}")
                except sqlite3.OperationalError:
                    pass

        # --- ADDITIVE MIGRATION FOR NEW OUTLINE COLUMNS ---
        self.cursor.execute("PRAGMA table_info(reading_outline)")
        existing_outline_cols = {row["name"] for row in self.cursor.fetchall()}
        cols_to_add_outline = {
            "part_function_html": "TEXT", "part_relation_html": "TEXT", "part_dependency_html": "TEXT",
            "part_function_text_plain": "TEXT", "part_relation_text_plain": "TEXT",
            "part_dependency_text_plain": "TEXT", "part_is_structural": "INTEGER DEFAULT 0",
            "part_dq_id": "INTEGER REFERENCES reading_driving_questions(id) ON DELETE SET NULL"
        }
        for col_name, col_type in cols_to_add_outline.items():
            if col_name not in existing_outline_cols:
                try:
                    self.cursor.execute(f"ALTER TABLE reading_outline ADD COLUMN {col_name} {col_type}")
                except sqlite3.OperationalError:
                    pass

        # --- ADDITIVE MIGRATION FOR reading_driving_questions ---
        self.cursor.execute("PRAGMA table_info(reading_driving_questions)")
        existing_dq_cols = {row["name"] for row in self.cursor.fetchall()}
        cols_to_add_dq = {
            "nickname": "TEXT", "type": "TEXT", "question_category": "TEXT", "scope": "TEXT",
            "outline_id": "INTEGER REFERENCES reading_outline(id) ON DELETE SET NULL",
            "pages": "TEXT", "why_question": "TEXT", "synthesis_tags": "TEXT",
            "is_working_question": "INTEGER", "extra_notes_text": "TEXT"
        }
        for col_name, col_type in cols_to_add_dq.items():
            if col_name not in existing_dq_cols:
                try:
                    self.cursor.execute(f"ALTER TABLE reading_driving_questions ADD COLUMN {col_name} {col_type}")
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

        # --- Synthesis Tables ---
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS synthesis_tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
        """)
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
            item_link_id INTEGER,
            FOREIGN KEY (project_id) REFERENCES items(id) ON DELETE CASCADE,
            FOREIGN KEY (reading_id) REFERENCES readings(id) ON DELETE CASCADE,
            FOREIGN KEY (outline_id) REFERENCES reading_outline(id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES synthesis_tags(id) ON DELETE SET NULL,
            FOREIGN KEY (item_link_id) REFERENCES reading_driving_questions(id) ON DELETE CASCADE
        )
        """)
        self.cursor.execute("PRAGMA table_info(synthesis_anchors)")
        anchor_cols = {row["name"] for row in self.cursor.fetchall()}
        if "tag_id" not in anchor_cols:
            try:
                self.cursor.execute(
                    "ALTER TABLE synthesis_anchors ADD COLUMN tag_id INTEGER REFERENCES synthesis_tags(id) ON DELETE SET NULL")
            except sqlite3.OperationalError as e:
                pass
        if "item_link_id" not in anchor_cols:
            try:
                self.cursor.execute("""
                    ALTER TABLE synthesis_anchors 
                    ADD COLUMN item_link_id INTEGER 
                    REFERENCES reading_driving_questions(id) ON DELETE CASCADE
                """)
            except sqlite3.OperationalError as e:
                pass
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

        # --- Terminology Tables ---
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

        # --- Proposition Tables ---
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

        # --- Argument Tables ---
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
        self.cursor.execute("PRAGMA table_info(reading_arguments)")
        existing_arg_cols = {row["name"] for row in self.cursor.fetchall()}
        if "synthesis_tags" not in existing_arg_cols:
            try:
                self.cursor.execute(f"ALTER TABLE reading_arguments ADD COLUMN synthesis_tags TEXT")
            except sqlite3.OperationalError:
                pass
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

        # --- To-Do List Table ---
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

        # --- MIGRATION LOGIC ---

        # If this is a brand new DB, set version to 2 and exit.
        if is_new_db:
            print("MIGRATION: New database detected. Setting to latest version (v2) and skipping migrations.")
            self.cursor.execute("PRAGMA user_version = 2")
            self.conn.commit()
            return  # <-- EXIT EARLY

        # --- If it's an old DB, run migrations in order ---

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

        # Re-check version in case it was just updated
        self.cursor.execute("PRAGMA user_version")
        user_version = self.cursor.fetchone()[0]

        if user_version < 2:
            print("MIGRATION (v2): Checking for and fixing broken foreign key references...")
            self.conn.commit()
            self.cursor.execute("PRAGMA foreign_keys = OFF")
            try:
                # --- THIS IS THE FIX: Re-ordered list. Dependents come AFTER dependencies. ---
                tables_to_fix = [
                    # Level 0 (no FKs to other tables in this list)
                    'reading_outline',
                    'reading_driving_questions',

                    # Level 1 (depend on Level 0)
                    'readings',
                    'reading_arguments',
                    'synthesis_anchors',

                    # Level 2 (depend on Level 1)
                    'reading_attachments',
                    'terminology_reading_links',
                    'terminology_references',
                    'proposition_reading_links',
                    'proposition_references',
                    'reading_argument_evidence'
                ]
                # --- END FIX ---

                for table_name in tables_to_fix:
                    self.cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
                    if not self.cursor.fetchone():
                        print(f"MIGRATION (v2): Table '{table_name}' does not exist, skipping rebuild.")
                        continue

                    print(f"MIGRATION (v2): Rebuilding table '{table_name}'...")
                    temp_table_name = f"_{table_name}_old_fk_fix"

                    try:
                        self.cursor.execute(f"DROP TABLE IF EXISTS {temp_table_name}")
                    except sqlite3.OperationalError:
                        pass

                    self.cursor.execute(f"ALTER TABLE {table_name} RENAME TO {temp_table_name}")

                    self.cursor.execute(f"""
                        SELECT sql FROM sqlite_master 
                        WHERE type='table' AND name='{temp_table_name}'
                    """)
                    create_sql_row = self.cursor.fetchone()
                    if not create_sql_row:
                        print(f"MIGRATION (v2) ERROR: Could not get SQL for temp table {temp_table_name}. Skipping.")
                        continue
                    create_sql = create_sql_row[0]

                    # --- THIS IS THE CRITICAL FIX ---
                    # More robustly replace all known old/temp table names with the correct new ones.
                    fixed_sql = create_sql.replace(
                        'REFERENCES "_readings_old_fk_fix"', 'REFERENCES "readings"'
                    ).replace(
                        'REFERENCES _readings_old_fk_fix', 'REFERENCES readings'
                    ).replace(
                        'REFERENCES "_reading_outline_old_fk_fix"', 'REFERENCES "reading_outline"'
                    ).replace(
                        'REFERENCES _reading_outline_old_fk_fix', 'REFERENCES reading_outline'
                    ).replace(
                        'REFERENCES "_dq_old"', 'REFERENCES "reading_driving_questions"'
                    ).replace(
                        'REFERENCES _dq_old', 'REFERENCES reading_driving_questions'
                    ).replace(
                        'REFERENCES "_reading_driving_questions_old_fk_fix"', 'REFERENCES "reading_driving_questions"'
                    ).replace(
                        'REFERENCES _reading_driving_questions_old_fk_fix', 'REFERENCES reading_driving_questions'
                    ).replace(
                        'REFERENCES "_reading_arguments_old_fk_fix"', 'REFERENCES "reading_arguments"'
                    ).replace(
                        'REFERENCES _reading_arguments_old_fk_fix', 'REFERENCES reading_arguments'
                    )
                    # --- END CRITICAL FIX ---

                    fixed_sql = fixed_sql.replace(f"CREATE TABLE \"{temp_table_name}\"",
                                                  f"CREATE TABLE \"{table_name}\"")
                    fixed_sql = fixed_sql.replace(f"CREATE TABLE {temp_table_name}", f"CREATE TABLE {table_name}")

                    if fixed_sql == create_sql:
                        print(f"MIGRATION (v2): No change needed for {table_name}, skipping rebuild.")
                        self.cursor.execute(f"ALTER TABLE {temp_table_name} RENAME TO {table_name}")
                        continue

                    self.cursor.execute(fixed_sql)

                    self.cursor.execute(f"PRAGMA table_info({temp_table_name})")
                    old_cols = [row['name'] for row in self.cursor.fetchall()]

                    self.cursor.execute(f"PRAGMA table_info({table_name})")
                    new_cols = [row['name'] for row in self.cursor.fetchall()]

                    cols_to_copy = [col for col in old_cols if col in new_cols]
                    cols_str = ", ".join([f'"{col}"' for col in cols_to_copy])

                    self.cursor.execute(
                        f"INSERT INTO {table_name} ({cols_str}) SELECT {cols_str} FROM {temp_table_name}")

                    self.cursor.execute(f"DROP TABLE {temp_table_name}")
                    print(f"MIGRATION (v2): Successfully rebuilt {table_name}.")

                self.cursor.execute("PRAGMA user_version = 2")
                self.conn.commit()
                print("MIGRATION (v2): All foreign keys fixed.")
            except Exception as e:
                print(f"CRITICAL MIGRATION ERROR (user_version 2): {e}")
                self.conn.rollback()
            finally:
                self.cursor.execute("PRAGMA foreign_keys = ON")
        # --- END MIGRATION (v2) ---

        self.conn.commit()