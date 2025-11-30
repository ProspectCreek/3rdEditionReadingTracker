import sqlite3


class SchemaSetup:
    """
    Handles the initial creation of all database tables for a fresh database.
    Contains migration logic to add new columns safely.
    """

    def _add_column_if_not_exists(self, table_name, column_name, column_type="TEXT", default_value="''"):
        """
        Safely adds a column to a table if it doesn't already exist.
        """
        try:
            self.cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [row['name'] for row in self.cursor.fetchall()]
            if column_name not in columns:
                self.cursor.execute(
                    f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type} DEFAULT {default_value}")
                print(f"Added column: {column_name} to {table_name}")
        except Exception as e:
            print(f"Warning: Could not add column {column_name} to {table_name}. {e}")

    def setup_database(self):
        """
        Creates all tables for the application.
        """
        print("--- Running SchemaSetup.setup_database() ---")

        # --- Level 0: Core Tables ---
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parent_id INTEGER,
            type TEXT NOT NULL,
            name TEXT NOT NULL,
            display_order INTEGER,
            is_assignment INTEGER DEFAULT 0,
            is_research INTEGER DEFAULT 0,
            is_annotated_bib INTEGER DEFAULT 0,
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

        # Migration for existing databases
        self._add_column_if_not_exists("items", "is_research", "INTEGER", "0")
        self._add_column_if_not_exists("items", "is_annotated_bib", "INTEGER", "0")

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

        # --- Instructions Migration ---
        new_instruction_columns = [
            ("synthesis_terminology_instr", "TEXT"),
            ("synthesis_propositions_instr", "TEXT"),
            ("synthesis_notes_instr", "TEXT"),
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
            ("reading_rules_html", "TEXT"),
            ("syntopic_rules_html", "TEXT"),
        ]
        for col_name, col_type in new_instruction_columns:
            self._add_column_if_not_exists("instructions", col_name, col_type, "''")

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

        # --- Annotated Bibliography Table ---
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS annotated_bib_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reading_id INTEGER NOT NULL,
            citation_text TEXT,
            description TEXT,
            analysis TEXT,
            applicability TEXT,
            status TEXT DEFAULT 'Not Started',
            FOREIGN KEY (reading_id) REFERENCES readings(id) ON DELETE CASCADE,
            UNIQUE(reading_id)
        )
        """)

        # --- Research Tab Tables ---
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS research_nodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            parent_id INTEGER,
            type TEXT NOT NULL, 
            title TEXT,
            display_order INTEGER,

            problem_statement TEXT,
            scope TEXT,
            frameworks TEXT,
            key_terms TEXT,
            working_thesis TEXT,
            open_issues TEXT,
            common_questions TEXT,
            agreements TEXT,
            disagreements TEXT,
            synthesis TEXT,

            role TEXT,
            evidence TEXT,
            contradictions TEXT,
            preliminary_conclusion TEXT,

            section_purpose TEXT,
            section_notes TEXT,

            pdf_node_id INTEGER,

            FOREIGN KEY (project_id) REFERENCES items(id) ON DELETE CASCADE,
            FOREIGN KEY (parent_id) REFERENCES research_nodes(id) ON DELETE CASCADE
        )
        """)
        self._add_column_if_not_exists("research_nodes", "pdf_node_id", "INTEGER", "NULL")

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS research_node_pdf_links (
            research_node_id INTEGER NOT NULL,
            pdf_node_id INTEGER NOT NULL,
            PRIMARY KEY (research_node_id, pdf_node_id),
            FOREIGN KEY (research_node_id) REFERENCES research_nodes(id) ON DELETE CASCADE,
            FOREIGN KEY (pdf_node_id) REFERENCES pdf_nodes(id) ON DELETE CASCADE
        )
        """)

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS research_node_terms (
            research_node_id INTEGER NOT NULL,
            terminology_id INTEGER NOT NULL,
            PRIMARY KEY (research_node_id, terminology_id),
            FOREIGN KEY (research_node_id) REFERENCES research_nodes(id) ON DELETE CASCADE,
            FOREIGN KEY (terminology_id) REFERENCES project_terminology(id) ON DELETE CASCADE
        )
        """)

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS research_memos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_id INTEGER NOT NULL,
            title TEXT,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (node_id) REFERENCES research_nodes(id) ON DELETE CASCADE
        )
        """)

        # --- NEW: Research Plans Table ---
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS research_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            title TEXT,
            status TEXT DEFAULT 'Not Started',
            research_question_id INTEGER, 
            methodological_approach TEXT,
            units_of_analysis TEXT,
            data_sources TEXT,
            sampling_strategy TEXT,
            coding_scheme TEXT,
            validity_limitations TEXT,
            display_order INTEGER,
            FOREIGN KEY (project_id) REFERENCES items(id) ON DELETE CASCADE
        )
        """)

        # --- User Settings Table ---
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            zotero_library_id TEXT,
            zotero_api_key TEXT,
            zotero_library_type TEXT DEFAULT 'user',
            citation_style TEXT DEFAULT 'apa'
        )
        """)
        self._add_column_if_not_exists("user_settings", "citation_style", "TEXT", "'apa'")

        # --- Level 1 Tables ---
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
            elevator_abstract_html TEXT,
            unity_kind_of_work TEXT,
            unity_driving_question_id INTEGER,
            zotero_item_key TEXT,
            FOREIGN KEY (project_id) REFERENCES items(id) ON DELETE CASCADE
        )
        """)
        self._add_column_if_not_exists("readings", "zotero_item_key", "TEXT", "NULL")
        self._add_column_if_not_exists("readings", "elevator_abstract_html", "TEXT", "NULL")

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS project_tag_links (
            project_id INTEGER NOT NULL,
            tag_id INTEGER NOT NULL,
            FOREIGN KEY (project_id) REFERENCES items(id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES synthesis_tags(id) ON DELETE CASCADE,
            PRIMARY KEY (project_id, tag_id)
        )
        """)

        # --- Level 2 Tables ---
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
            pdf_node_id INTEGER,
            FOREIGN KEY (reading_id) REFERENCES readings(id) ON DELETE CASCADE,
            FOREIGN KEY (parent_id) REFERENCES reading_driving_questions(id) ON DELETE CASCADE
        )
        """)
        self._add_column_if_not_exists("reading_driving_questions", "pdf_node_id", "INTEGER", "NULL")

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
        CREATE TABLE IF NOT EXISTS pdf_node_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            color_hex TEXT DEFAULT '#FFFF00',
            FOREIGN KEY (project_id) REFERENCES items(id) ON DELETE CASCADE
        )
        """)

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS pdf_nodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reading_id INTEGER NOT NULL,
            attachment_id INTEGER NOT NULL,
            category_id INTEGER, 
            page_number INTEGER NOT NULL,
            x_pos REAL NOT NULL,
            y_pos REAL NOT NULL,
            node_type TEXT DEFAULT 'Note',
            color_hex TEXT DEFAULT '#FFFF00',
            label TEXT,
            description TEXT,
            FOREIGN KEY (reading_id) REFERENCES readings(id) ON DELETE CASCADE,
            FOREIGN KEY (attachment_id) REFERENCES reading_attachments(id) ON DELETE CASCADE,
            FOREIGN KEY (category_id) REFERENCES pdf_node_categories(id) ON DELETE SET NULL
        )
        """)
        self._add_column_if_not_exists("pdf_nodes", "category_id", "INTEGER", "NULL")

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
            pdf_node_id INTEGER,
            FOREIGN KEY (reading_id) REFERENCES readings(id) ON DELETE CASCADE,
            FOREIGN KEY (driving_question_id) REFERENCES reading_driving_questions(id) ON DELETE SET NULL
        )
        """)
        self._add_column_if_not_exists("reading_arguments", "pdf_node_id", "INTEGER", "NULL")

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

        # --- Level 3 Tables ---
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
            pdf_node_id INTEGER,
            FOREIGN KEY (project_id) REFERENCES items(id) ON DELETE CASCADE,
            FOREIGN KEY (reading_id) REFERENCES readings(id) ON DELETE CASCADE,
            FOREIGN KEY (outline_id) REFERENCES reading_outline(id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES synthesis_tags(id) ON DELETE SET NULL,
            FOREIGN KEY (item_link_id) REFERENCES reading_driving_questions(id) ON DELETE CASCADE
        )
        """)
        self._add_column_if_not_exists("synthesis_anchors", "pdf_node_id", "INTEGER", "NULL")

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
            pdf_node_id INTEGER DEFAULT NULL,
            FOREIGN KEY (terminology_id) REFERENCES project_terminology(id) ON DELETE CASCADE,
            FOREIGN KEY (reading_id) REFERENCES readings(id) ON DELETE CASCADE,
            FOREIGN KEY (outline_id) REFERENCES reading_outline(id) ON DELETE SET NULL
        )
        """)
        self._add_column_if_not_exists("terminology_references", "pdf_node_id", "INTEGER", "NULL")

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS terminology_reference_pdf_links (
            reference_id INTEGER NOT NULL,
            pdf_node_id INTEGER NOT NULL,
            PRIMARY KEY (reference_id, pdf_node_id),
            FOREIGN KEY (reference_id) REFERENCES terminology_references(id) ON DELETE CASCADE,
            FOREIGN KEY (pdf_node_id) REFERENCES pdf_nodes(id) ON DELETE CASCADE
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

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS proposition_reference_pdf_links (
            reference_id INTEGER NOT NULL,
            pdf_node_id INTEGER NOT NULL,
            PRIMARY KEY (reference_id, pdf_node_id),
            FOREIGN KEY (reference_id) REFERENCES proposition_references(id) ON DELETE CASCADE,
            FOREIGN KEY (pdf_node_id) REFERENCES pdf_nodes(id) ON DELETE CASCADE
        )
        """)

        # --- Level 4 Tables ---
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS anchor_tag_links (
            anchor_id INTEGER NOT NULL,
            tag_id INTEGER NOT NULL,
            FOREIGN KEY (anchor_id) REFERENCES synthesis_anchors(id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES synthesis_tags(id) ON DELETE CASCADE,
            PRIMARY KEY (anchor_id, tag_id)
        )
        """)

        self.conn.commit()
        print("--- Schema setup complete. All tables created/updated. ---")