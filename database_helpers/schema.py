# prospectcreek/3rdeditionreadingtracker/database_helpers/schema.py
import sqlite3


class SchemaSetup:
    """
    Handles the initial creation of all database tables for a fresh database.
    Contains migration logic to add new columns safely.
    """

    def _add_column_if_not_exists(self, table_name, column_name, column_type="TEXT", default_value="''"):
        """
        Safely adds a column to a table if it doesn't already exist.
        Defaults to TEXT with a default value of an empty string.
        """
        try:
            self.cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [row['name'] for row in self.cursor.fetchall()]
            if column_name not in columns:
                self.cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type} DEFAULT {default_value}")
                print(f"Added column: {column_name} to {table_name}")
        except Exception as e:
            # This might fail if in a transaction, but it's okay for setup
            print(f"Warning: Could not add column {column_name} to {table_name}. {e}")


    def setup_database(self):
        """
        Creates all 23 tables for the application in an order that
        respects foreign key dependencies.
        """
        print("--- Running SchemaSetup.setup_database() ---")

        # --- Level 0: Core Tables (No dependencies on other app tables) ---

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

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS synthesis_tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
        """)

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

        # --- START: Add new instruction columns (Migration) ---
        # This list contains all the new instruction fields we need.
        new_instruction_columns = [
            # Synthesis Tabs
            ("synthesis_terminology_instr", "TEXT"),
            ("synthesis_propositions_instr", "TEXT"),
            ("synthesis_notes_instr", "TEXT"),
            # Reading Tabs
            ("reading_dq_instr", "TEXT"),
            ("reading_lp_instr", "TEXT"),
            ("reading_unity_instr", "TEXT"),
            ("reading_elevator_instr", "TEXT"),
            ("reading_parts_instr", "TEXT"),
            ("reading_key_terms_instr", "TEXT"),
            ("reading_arguments_instr", "TEXT"),
            ("reading_gaps_instr", "TEXT"),
            ("reading_theories_instr", "TEXT"),
            ("reading_dialogue_instr", "TEXT"),
            # --- NEW: Add Reading Rules Column ---
            ("reading_rules_html", "TEXT"),
        ]

        # Safely add each new column to the 'instructions' table
        for col_name, col_type in new_instruction_columns:
            self._add_column_if_not_exists("instructions", col_name, col_type, "''")
        # --- END: Add new instruction columns ---


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

        # --- Level 1: Depends on items ---

        if hasattr(self, 'create_graph_settings_table'):
            self.create_graph_settings_table()
        if hasattr(self, 'create_global_graph_settings_table'):
            self.create_global_graph_settings_table()

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
            FOREIGN KEY (project_id) REFERENCES items(id) ON DELETE CASCADE
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

        # --- Level 2: Depends on readings, mindmaps ---

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
            FOREIGN KEY (parent_id) REFERENCES reading_driving_questions(id) ON DELETE CASCADE
        )
        """)

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

        # --- Level 3: Depends on tables from Level 2 ---

        # This is the key table for virtual anchors.
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
            item_type TEXT,
            FOREIGN KEY (project_id) REFERENCES items(id) ON DELETE CASCADE,
            FOREIGN KEY (reading_id) REFERENCES readings(id) ON DELETE CASCADE,
            FOREIGN KEY (outline_id) REFERENCES reading_outline(id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES synthesis_tags(id) ON DELETE SET NULL,
            FOREIGN KEY (item_link_id) REFERENCES reading_driving_questions(id) ON DELETE CASCADE
        )
        """)

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

        # --- Level 4: Depends on synthesis_anchors ---

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS anchor_tag_links (
            anchor_id INTEGER NOT NULL,
            tag_id INTEGER NOT NULL,
            FOREIGN KEY (anchor_id) REFERENCES synthesis_anchors(id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES synthesis_tags(id) ON DELETE CASCADE,
            PRIMARY KEY (anchor_id, tag_id)
        )
        """)

        # --- Finalize ---
        self.conn.commit()
        print("--- Schema setup complete. All tables created/updated. ---")