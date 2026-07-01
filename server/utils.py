import uuid
from datetime import datetime

def _now_iso():
    """Current UTC-ish timestamp as ISO string."""
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

def _row_to_dict(row):
    """Convert a sqlite3.Row to a plain dict."""
    if row is None:
        return None
    return dict(row)

def _rows_to_list(rows):
    """Convert a list of sqlite3.Row objects to a list of dicts."""
    return [_row_to_dict(r) for r in rows]
