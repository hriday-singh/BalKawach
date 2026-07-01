from flask import session, jsonify, request
import uuid
from .db import get_db

def current_user():
    """Return the user dict stored in session, or None."""
    return session.get("user")

def require_login():
    """Return (user_dict, None) or (None, error_response)."""
    user = current_user()
    if user is None:
        return None, (jsonify({"error": "Not authenticated"}), 401)
    return user, None

def audit(action: str, details: str = "", entity_type: str = "", entity_id: str = ""):
    """Write one row to the audit_logs table."""
    user = current_user()
    conn = get_db()
    conn.execute(
        """INSERT INTO audit_logs
           (id, user_id, action, entity_type, entity_id, details, ip_address)
           VALUES (?,?,?,?,?,?,?)""",
        (
            str(uuid.uuid4()),
            user["id"] if user else "system",
            action,
            entity_type,
            entity_id,
            details,
            request.remote_addr,
        ),
    )
    conn.commit()
