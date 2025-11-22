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
    """

    def __init__(self, db_name="qda_tool_db.db"):
        # Determine path relative to this script file to ensure it stays with the app
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_path = os.path.join(base_dir, db_name)

        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = dict_factory
        self.cursor = self.conn.cursor()
        self.cursor.execute("PRAGMA foreign_keys = ON")
        self.setup_tables()

    # ------------------------------------------------------------------
    # SCHEMA
    # ------------------------------------------------------------------
    def setup_tables(self):
        # Worksheets
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS qda_worksheets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # Columns
        self.cursor.execute(
            """
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
            """
        )

        # Rows
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS qda_rows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                worksheet_id INTEGER NOT NULL,
                data_json TEXT DEFAULT '{}',
                display_order INTEGER,
                FOREIGN KEY (worksheet_id) REFERENCES qda_worksheets(id) ON DELETE CASCADE
            )
            """
        )

        # Segments
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS qda_segments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                row_id INTEGER NOT NULL,
                data_json TEXT DEFAULT '{}',
                display_order INTEGER,
                FOREIGN KEY (row_id) REFERENCES qda_rows(id) ON DELETE CASCADE
            )
            """
        )

        self.cursor.execute(
            """
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
            """
        )

        self.conn.commit()

    # ------------------------------------------------------------------
    # WORKSHEETS
    # ------------------------------------------------------------------
    def get_worksheets(self):
        self.cursor.execute(
            "SELECT * FROM qda_worksheets ORDER BY created_at, name"
        )
        return self.cursor.fetchall()

    def get_worksheet_by_name(self, name):
        """Find a worksheet by exact name."""
        self.cursor.execute(
            "SELECT * FROM qda_worksheets WHERE name = ?",
            (name,)
        )
        return self.cursor.fetchone()

    def create_worksheet(self, name):
        self.cursor.execute(
            "INSERT INTO qda_worksheets (name) VALUES (?)",
            (name,),
        )
        ws_id = self.cursor.lastrowid
        self.conn.commit()
        return ws_id

    def delete_worksheet(self, ws_id):
        self.cursor.execute(
            "DELETE FROM qda_worksheets WHERE id = ?",
            (ws_id,),
        )
        self.conn.commit()

    # ------------------------------------------------------------------
    # COLUMNS
    # ------------------------------------------------------------------
    def get_columns(self, ws_id):
        self.cursor.execute(
            """
            SELECT * FROM qda_columns
            WHERE worksheet_id = ?
            ORDER BY display_order, id
            """,
            (ws_id,),
        )
        return self.cursor.fetchall()

    def get_column_by_id(self, col_id):
        self.cursor.execute("SELECT * FROM qda_columns WHERE id = ?", (col_id,))
        return self.cursor.fetchone()

    def add_column(self, ws_id, name, col_type, options_json="[]"):
        self.cursor.execute(
            """
            SELECT COALESCE(MAX(display_order), -1) + 1 AS next_order
            FROM qda_columns WHERE worksheet_id = ?
            """,
            (ws_id,),
        )
        res = self.cursor.fetchone()
        next_order = res["next_order"] if res else 0

        self.cursor.execute(
            """
            INSERT INTO qda_columns
                (worksheet_id, name, col_type, options_json, display_order)
            VALUES (?, ?, ?, ?, ?)
            """,
            (ws_id, name, col_type, options_json, next_order),
        )
        self.conn.commit()

    def update_column_def(self, col_id, name, col_type, options_json, color=None):
        self.cursor.execute(
            """
            UPDATE qda_columns
               SET name = ?, col_type = ?, options_json = ?, color = ?
             WHERE id = ?
            """,
            (name, col_type, options_json, color, col_id),
        )
        self.conn.commit()

    def get_codebook_meta(self, col_id):
        self.cursor.execute(
            """
            SELECT definition, inclusion, exclusion, examples, parent_id
              FROM qda_columns
             WHERE id = ?
            """,
            (col_id,),
        )
        return self.cursor.fetchone()

    def update_codebook_meta(self, col_id, definition, inclusion, exclusion, examples, parent_id):
        self.cursor.execute(
            """
            UPDATE qda_columns
               SET definition = ?, inclusion = ?, exclusion = ?, examples = ?, parent_id = ?
             WHERE id = ?
            """,
            (definition, inclusion, exclusion, examples, parent_id, col_id),
        )
        self.conn.commit()

    def update_column_order(self, col_id, display_order):
        self.cursor.execute(
            "UPDATE qda_columns SET display_order = ? WHERE id = ?",
            (display_order, col_id),
        )
        self.conn.commit()

    def move_column(self, ws_id, col_id, direction):
        """
        Move column up (-1) or down (+1) by swapping display_order.
        """
        # 1. Get current col
        self.cursor.execute("SELECT id, display_order FROM qda_columns WHERE id=?", (col_id,))
        current = self.cursor.fetchone()
        if not current: return

        curr_order = current["display_order"]

        # 2. Find neighbor
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
            # Swap
            neigh_id = neighbor["id"]
            neigh_order = neighbor["display_order"]

            self.cursor.execute("UPDATE qda_columns SET display_order=? WHERE id=?", (neigh_order, col_id))
            self.cursor.execute("UPDATE qda_columns SET display_order=? WHERE id=?", (curr_order, neigh_id))
            self.conn.commit()

    def delete_column(self, col_id):
        self.cursor.execute("DELETE FROM qda_columns WHERE id = ?", (col_id,))
        self.conn.commit()

    # ------------------------------------------------------------------
    # ROWS
    # ------------------------------------------------------------------
    def get_rows(self, ws_id):
        self.cursor.execute(
            """
            SELECT * FROM qda_rows
            WHERE worksheet_id = ?
            ORDER BY display_order, id
            """,
            (ws_id,),
        )
        return self.cursor.fetchall()

    def get_row(self, row_id):
        self.cursor.execute("SELECT * FROM qda_rows WHERE id = ?", (row_id,))
        return self.cursor.fetchone()

    def add_row(self, ws_id):
        self.cursor.execute(
            "SELECT COALESCE(MAX(display_order), -1) + 1 AS next_order FROM qda_rows WHERE worksheet_id = ?",
            (ws_id,),
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
        self.cursor.execute(
            "UPDATE qda_rows SET data_json = ? WHERE id = ?",
            (json_str, row_id),
        )
        self.conn.commit()

    def delete_row(self, row_id):
        self.cursor.execute("DELETE FROM qda_rows WHERE id = ?", (row_id,))
        self.conn.commit()

    # ------------------------------------------------------------------
    # SEGMENTS
    # ------------------------------------------------------------------
    def get_segments(self, row_id):
        self.cursor.execute(
            """
            SELECT * FROM qda_segments
            WHERE row_id = ?
            ORDER BY display_order, id
            """,
            (row_id,),
        )
        return self.cursor.fetchall()

    def get_segment_counts(self, ws_id):
        self.cursor.execute(
            """
            SELECT s.row_id, COUNT(s.id) as count
            FROM qda_segments s
            JOIN qda_rows r ON s.row_id = r.id
            WHERE r.worksheet_id = ?
            GROUP BY s.row_id
            """,
            (ws_id,),
        )
        rows = self.cursor.fetchall()
        return {r["row_id"]: r["count"] for r in rows}

    def add_segment(self, row_id):
        self.cursor.execute(
            "SELECT COALESCE(MAX(display_order), -1) + 1 AS next_order FROM qda_segments WHERE row_id = ?",
            (row_id,),
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
        self.cursor.execute(
            "UPDATE qda_segments SET data_json = ? WHERE id = ?",
            (json_str, seg_id),
        )
        self.conn.commit()

    def delete_segment(self, seg_id):
        self.cursor.execute("DELETE FROM qda_segments WHERE id = ?", (seg_id,))
        self.conn.commit()