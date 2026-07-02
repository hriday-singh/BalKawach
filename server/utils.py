from datetime import datetime, timezone

def _iso_now():
    """Current UTC timestamp as ISO 8601 string. Single source of truth."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def _row_to_dict(row):
    """Convert a sqlite3.Row to a plain dict."""
    if row is None:
        return None
    return dict(row)

def _rows_to_list(rows):
    """Convert a list of sqlite3.Row objects to a list of dicts."""
    return [_row_to_dict(r) for r in rows]

def compute_age(date_of_birth_str, estimated_age=None):
    """Compute current age from DOB string (YYYY-MM-DD). Falls back to estimated_age."""
    if date_of_birth_str:
        try:
            dob = datetime.strptime(date_of_birth_str, "%Y-%m-%d")
            today = datetime.now(timezone.utc)
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            return age
        except (ValueError, TypeError):
            pass
    return estimated_age

def district_code(district):
    """Convert a district name to a 3-letter code for child_code generation."""
    codes = {
        "hyderabad": "HYD",
        "mumbai": "MUM",
        "pune": "PUN",
        "bangalore": "BLR",
        "bengaluru": "BLR",
        "chennai": "CHN",
        "delhi": "DEL",
        "kolkata": "KOL",
    }
    return codes.get(district.lower().strip(), district[:3].upper()) if district else "UNK"
