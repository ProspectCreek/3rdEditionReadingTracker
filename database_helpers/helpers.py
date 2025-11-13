class DbHelpers:
    @staticmethod
    def _rowdict(row):
        """Coerce a sqlite3.Row (or None) to a plain dict (or None)."""
        return dict(row) if row is not None else None

    @staticmethod
    def _map_rows(rows):
        """Coerce an iterable of sqlite3.Row to list[dict]."""
        return [dict(r) for r in rows] if rows else []