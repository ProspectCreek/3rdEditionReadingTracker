# qda_tool/qda_database_manager.py
import sqlite3
import json
import os


def dict_factory(cursor, row):
    """Return sqlite rows as plain dicts."""
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


class QDAManager:
    """
    Thin wrapper around sqlite for QDA worksheets.
    Also acts as a proxy to the main Reading Tracker DB for PDF features.
    """

    def __init__(self, db_name="qda_tool_db.db", tracker_db_path=None):
        # Determine path relative to this script file to ensure it stays with the app
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_path = os.path.join(base_dir, db_name)

        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = dict_factory
        self.cursor = self.conn.cursor()
        self.cursor.execute("PRAGMA foreign_keys = ON")
        self.setup_tables()

        # --- External DB Connection ---
        self.tracker_conn = None
        self.tracker_cursor = None

        # Try to find the tracker DB if not provided
        if not tracker_db_path:
            # Assume standard structure: ../reading_tracker.db
            potential_path = os.path.join(base_dir, "..", "reading_tracker.db")
            if os.path.exists(potential_path):
                tracker_db_path = potential_path

        if tracker_db_path and os.path.exists(tracker_db_path):
            self.connect_tracker_db(tracker_db_path)

    def setup_tables(self):
        # Worksheets
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS qda_worksheets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Columns
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS qda_columns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                worksheet_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                col_type TEXT NOT NULL,
                options_json TEXT DEFAULT '[]',
                display_order INTEGER,
                definition TEXT,
                inclusion TEXT,
                exclusion TEXT,
                examples TEXT,
                parent_id INTEGER,
                color TEXT,
                FOREIGN KEY (worksheet_id) REFERENCES qda_worksheets(id) ON DELETE CASCADE
            )
        """)

        # Rows
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS qda_rows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                worksheet_id INTEGER NOT NULL,
                data_json TEXT DEFAULT '{}',
                display_order INTEGER,
                FOREIGN KEY (worksheet_id) REFERENCES qda_worksheets(id) ON DELETE CASCADE
            )
        """)

        # Segments
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS qda_segments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                row_id INTEGER NOT NULL,
                data_json TEXT DEFAULT '{}',
                display_order INTEGER,
                FOREIGN KEY (row_id) REFERENCES qda_rows(id) ON DELETE CASCADE
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS qda_codebook_meta (
                col_id      INTEGER PRIMARY KEY,
                definition  TEXT,
                inclusion   TEXT,
                exclusion   TEXT,
                examples    TEXT,
                parent_id   INTEGER,
                FOREIGN KEY(col_id) REFERENCES qda_columns(id) ON DELETE CASCADE,
                FOREIGN KEY(parent_id) REFERENCES qda_columns(id) ON DELETE SET NULL
            )
        """)

        self.conn.commit()

    # --- External DB Methods (Tracker) ---
    def connect_tracker_db(self, db_path):
        """Connects to the main reading tracker database."""
        try:
            # Open in read-write mode so we can add nodes from QDA tool
            self.tracker_conn = sqlite3.connect(db_path)
            self.tracker_conn.row_factory = dict_factory
            self.tracker_cursor = self.tracker_conn.cursor()
            self.tracker_cursor.execute("PRAGMA foreign_keys = ON")
            print(f"Connected to Reading Tracker DB at: {db_path}")
        except Exception as e:
            print(f"Failed to connect to Reading Tracker DB: {e}")

    def get_tracker_projects(self):
        if not self.tracker_cursor: return []
        try:
            self.tracker_cursor.execute("SELECT * FROM items WHERE type='project' ORDER BY name")
            return self.tracker_cursor.fetchall()
        except Exception:
            return []

    def get_tracker_readings(self, project_id):
        if not self.tracker_cursor: return []
        try:
            self.tracker_cursor.execute("SELECT * FROM readings WHERE project_id = ? ORDER BY display_order",
                                        (project_id,))
            return self.tracker_cursor.fetchall()
        except Exception:
            return []

    def get_tracker_pdf_nodes(self, reading_id):
        """Fetches PDF nodes for a reading, including categories."""
        if not self.tracker_cursor: return []
        try:
            # --- UPDATED QUERY: Ensures 'category_color' is returned ---
            self.tracker_cursor.execute("""
                SELECT n.*, c.name as category_name, c.color_hex as category_color
                FROM pdf_nodes n
                LEFT JOIN pdf_node_categories c ON n.category_id = c.id
                WHERE n.reading_id = ? 
                ORDER BY n.page_number, n.id
            """, (reading_id,))
            return self.tracker_cursor.fetchall()
        except Exception as e:
            print(f"Error fetching tracker pdf nodes: {e}")
            return []

    def get_tracker_node_details(self, node_id):
        if not self.tracker_cursor: return None
        try:
            self.tracker_cursor.execute("""
                SELECT n.*, a.file_path, a.id as attachment_id, n.reading_id, c.name as category_name
                FROM pdf_nodes n
                JOIN reading_attachments a ON n.attachment_id = a.id
                LEFT JOIN pdf_node_categories c ON n.category_id = c.id
                WHERE n.id = ?
            """, (node_id,))
            return self.tracker_cursor.fetchone()
        except Exception:
            return None

    # --- Proxy Methods for PdfNodeViewer (READ & WRITE) ---

    def get_pdf_node_details(self, node_id):
        return self.get_tracker_node_details(node_id)

    def get_pdf_nodes_for_page(self, attachment_id, page_number):
        if not self.tracker_cursor: return []
        try:
            self.tracker_cursor.execute("""
                SELECT n.*, c.name as category_name, c.color_hex as category_color
                FROM pdf_nodes n
                LEFT JOIN pdf_node_categories c ON n.category_id = c.id
                WHERE n.attachment_id = ? AND n.page_number = ?
            """, (attachment_id, page_number))
            return self.tracker_cursor.fetchall()
        except Exception:
            return []

    def get_pdf_node_categories(self, project_id):
        if not self.tracker_cursor: return []
        try:
            self.tracker_cursor.execute("""
                SELECT * FROM pdf_node_categories 
                WHERE project_id = ?
                ORDER BY name
            """, (project_id,))
            return self.tracker_cursor.fetchall()
        except Exception:
            return []

    def add_pdf_node(self, reading_id, attachment_id, page_number, x_pos, y_pos,
                     node_type='Note', color_hex='#FFFF00', label='New Node', description='', category_id=None):
        if not self.tracker_cursor: return None
        try:
            self.tracker_cursor.execute("""
                INSERT INTO pdf_nodes (reading_id, attachment_id, page_number, x_pos, y_pos, node_type, color_hex, label, description, category_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (reading_id, attachment_id, page_number, x_pos, y_pos, node_type, color_hex, label, description,
                  category_id))
            self.tracker_conn.commit()
            return self.tracker_cursor.lastrowid
        except Exception as e:
            print(f"Error adding PDF node: {e}")
            return None

    def update_pdf_node(self, node_id, label=None, description=None, color_hex=None, node_type=None,
                        x_pos=None, y_pos=None, category_id=None):
        if not self.tracker_cursor: return
        updates = []
        params = []
        if label is not None: updates.append("label = ?"); params.append(label)
        if description is not None: updates.append("description = ?"); params.append(description)
        if color_hex is not None: updates.append("color_hex = ?"); params.append(color_hex)
        if node_type is not None: updates.append("node_type = ?"); params.append(node_type)
        if x_pos is not None: updates.append("x_pos = ?"); params.append(x_pos)
        if y_pos is not None: updates.append("y_pos = ?"); params.append(y_pos)
        if category_id is not None: updates.append("category_id = ?"); params.append(category_id)

        if not updates: return
        params.append(node_id)
        sql = f"UPDATE pdf_nodes SET {', '.join(updates)} WHERE id = ?"
        try:
            self.tracker_cursor.execute(sql, tuple(params))
            self.tracker_conn.commit()
        except Exception as e:
            print(f"Error updating PDF node: {e}")

    def delete_pdf_node(self, node_id):
        if not self.tracker_cursor: return
        try:
            self.tracker_cursor.execute("DELETE FROM pdf_nodes WHERE id = ?", (node_id,))
            self.tracker_conn.commit()
        except Exception as e:
            print(f"Error deleting PDF node: {e}")

    def add_pdf_node_category(self, project_id, name, color_hex):
        if not self.tracker_cursor: return
        try:
            self.tracker_cursor.execute("""
                INSERT INTO pdf_node_categories (project_id, name, color_hex)
                VALUES (?, ?, ?)
            """, (project_id, name, color_hex))
            self.tracker_conn.commit()
        except Exception as e:
            print(f"Error adding category: {e}")

    def update_pdf_node_category(self, category_id, name, color_hex):
        if not self.tracker_cursor: return
        try:
            self.tracker_cursor.execute("""
                UPDATE pdf_node_categories
                SET name = ?, color_hex = ?
                WHERE id = ?
            """, (name, color_hex, category_id))
            self.tracker_conn.commit()
        except Exception as e:
            print(f"Error updating category: {e}")

    def delete_pdf_node_category(self, category_id):
        if not self.tracker_cursor: return
        try:
            self.tracker_cursor.execute("DELETE FROM pdf_node_categories WHERE id = ?", (category_id,))
            self.tracker_conn.commit()
        except Exception as e:
            print(f"Error deleting category: {e}")

    # ------------------------------------------------------------------
    # QDA METHODS (Worksheets, Columns, Rows)
    # ------------------------------------------------------------------
    def get_worksheets(self):
        self.cursor.execute("SELECT * FROM qda_worksheets ORDER BY created_at, name")
        return self.cursor.fetchall()

    def create_worksheet(self, name):
        self.cursor.execute("INSERT INTO qda_worksheets (name) VALUES (?)", (name,))
        ws_id = self.cursor.lastrowid
        self.conn.commit()
        return ws_id

    def delete_worksheet(self, ws_id):
        self.cursor.execute("DELETE FROM qda_worksheets WHERE id = ?", (ws_id,))
        self.conn.commit()

    def get_columns(self, ws_id):
        self.cursor.execute("SELECT * FROM qda_columns WHERE worksheet_id = ? ORDER BY display_order, id", (ws_id,))
        return self.cursor.fetchall()

    def add_column(self, ws_id, name, col_type, options_json="[]"):
        self.cursor.execute(
            "SELECT COALESCE(MAX(display_order), -1) + 1 AS next_order FROM qda_columns WHERE worksheet_id = ?",
            (ws_id,)
        )
        res = self.cursor.fetchone()
        next_order = res["next_order"] if res else 0
        self.cursor.execute(
            "INSERT INTO qda_columns (worksheet_id, name, col_type, options_json, display_order) VALUES (?, ?, ?, ?, ?)",
            (ws_id, name, col_type, options_json, next_order),
        )
        self.conn.commit()

    def update_column_def(self, col_id, name, col_type, options_json, color=None):
        self.cursor.execute(
            "UPDATE qda_columns SET name = ?, col_type = ?, options_json = ?, color = ? WHERE id = ?",
            (name, col_type, options_json, color, col_id),
        )
        self.conn.commit()

    def delete_column(self, col_id):
        self.cursor.execute("DELETE FROM qda_columns WHERE id = ?", (col_id,))
        self.conn.commit()

    def move_column(self, ws_id, col_id, direction):
        self.cursor.execute("SELECT id, display_order FROM qda_columns WHERE id=?", (col_id,))
        current = self.cursor.fetchone()
        if not current: return
        curr_order = current["display_order"]

        if direction < 0:  # Up
            self.cursor.execute(
                "SELECT id, display_order FROM qda_columns WHERE worksheet_id=? AND display_order < ? ORDER BY display_order DESC LIMIT 1",
                (ws_id, curr_order)
            )
        else:  # Down
            self.cursor.execute(
                "SELECT id, display_order FROM qda_columns WHERE worksheet_id=? AND display_order > ? ORDER BY display_order ASC LIMIT 1",
                (ws_id, curr_order)
            )
        neighbor = self.cursor.fetchone()

        if neighbor:
            neigh_id = neighbor["id"]
            neigh_order = neighbor["display_order"]
            self.cursor.execute("UPDATE qda_columns SET display_order=? WHERE id=?", (neigh_order, col_id))
            self.cursor.execute("UPDATE qda_columns SET display_order=? WHERE id=?", (curr_order, neigh_id))
            self.conn.commit()

    def get_rows(self, ws_id):
        self.cursor.execute("SELECT * FROM qda_rows WHERE worksheet_id = ? ORDER BY display_order, id", (ws_id,))
        return self.cursor.fetchall()

    def get_row(self, row_id):
        self.cursor.execute("SELECT * FROM qda_rows WHERE id = ?", (row_id,))
        return self.cursor.fetchone()

    def add_row(self, ws_id):
        self.cursor.execute(
            "SELECT COALESCE(MAX(display_order), -1) + 1 AS next_order FROM qda_rows WHERE worksheet_id = ?",
            (ws_id,)
        )
        res = self.cursor.fetchone()
        next_order = res["next_order"] if res else 0
        self.cursor.execute(
            "INSERT INTO qda_rows (worksheet_id, data_json, display_order) VALUES (?, '{}', ?)",
            (ws_id, next_order),
        )
        self.conn.commit()

    def update_row_data(self, row_id, data_dict):
        json_str = json.dumps(data_dict)
        self.cursor.execute("UPDATE qda_rows SET data_json = ? WHERE id = ?", (json_str, row_id))
        self.conn.commit()

    def delete_row(self, row_id):
        self.cursor.execute("DELETE FROM qda_rows WHERE id = ?", (row_id,))
        self.conn.commit()

    def get_segments(self, row_id):
        self.cursor.execute("SELECT * FROM qda_segments WHERE row_id = ? ORDER BY display_order, id", (row_id,))
        return self.cursor.fetchall()

    def get_segment_counts(self, ws_id):
        self.cursor.execute("""
            SELECT s.row_id, COUNT(s.id) as count
            FROM qda_segments s
            JOIN qda_rows r ON s.row_id = r.id
            WHERE r.worksheet_id = ?
            GROUP BY s.row_id
        """, (ws_id,))
        rows = self.cursor.fetchall()
        return {r["row_id"]: r["count"] for r in rows}

    def add_segment(self, row_id):
        self.cursor.execute(
            "SELECT COALESCE(MAX(display_order), -1) + 1 AS next_order FROM qda_segments WHERE row_id = ?",
            (row_id,)
        )
        res = self.cursor.fetchone()
        next_order = res["next_order"] if res else 0
        self.cursor.execute(
            "INSERT INTO qda_segments (row_id, data_json, display_order) VALUES (?, '{}', ?)",
            (row_id, next_order),
        )
        self.conn.commit()

    def update_segment_data(self, seg_id, data_dict):
        json_str = json.dumps(data_dict)
        self.cursor.execute("UPDATE qda_segments SET data_json = ? WHERE id = ?", (json_str, seg_id))
        self.conn.commit()

    def delete_segment(self, seg_id):
        self.cursor.execute("DELETE FROM qda_segments WHERE id = ?", (seg_id,))
        self.conn.commit()

    def get_codebook_meta(self, col_id):
        self.cursor.execute("SELECT * FROM qda_codebook_meta WHERE col_id = ?", (col_id,))
        return self.cursor.fetchone()

    def update_codebook_meta(self, col_id, definition, inclusion, exclusion, examples, parent_id):
        self.cursor.execute(
            "INSERT OR REPLACE INTO qda_codebook_meta (col_id, definition, inclusion, exclusion, examples, parent_id) VALUES (?, ?, ?, ?, ?, ?)",
            (col_id, definition, inclusion, exclusion, examples, parent_id))
        self.conn.commit()