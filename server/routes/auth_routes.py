import uuid
from flask import Blueprint, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from server.db import get_db
from server.auth import current_user, audit
from server.utils import _row_to_dict, _rows_to_list

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/api/auth/login", methods=["POST"])
def auth_login():
    """Authenticate a user and store their profile in the session."""
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()

    if user is None:
        return jsonify({"error": "Invalid credentials"}), 401

    if not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid credentials"}), 401
        
    if user["is_active"] == 0:
        return jsonify({"error": "Account pending admin approval"}), 403

    user_dict = _row_to_dict(user)
    user_dict.pop("password_hash", None)
    session["user"] = user_dict

    audit("LOGIN", f"User {username} logged in", "user", user_dict["id"])

    return jsonify({"message": "Login successful", "user": user_dict})


@auth_bp.route("/api/auth/register", methods=["POST"])
def auth_register():
    """Public registration endpoint (creates pending user)."""
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    full_name = data.get("full_name", "").strip()
    role = data.get("role", "cci_staff")
    district = data.get("district", "Hyderabad")
    
    if not username or not password or not full_name:
        return jsonify({"error": "Missing required fields"}), 400
        
    conn = get_db()
    existing = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    if existing:
        return jsonify({"error": "Username already exists"}), 400
        
    user_id = str(uuid.uuid4())
    pw_hash = generate_password_hash(password)
    
    conn.execute(
        "INSERT INTO users (id, username, password_hash, full_name, role, district, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, username, pw_hash, full_name, role, district, 0)
    )
    conn.commit()
    return jsonify({"message": "Registration successful. Pending admin approval."}), 201


@auth_bp.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    """Clear the current session."""
    user = current_user()
    if user:
        audit("LOGOUT", f"User {user['full_name']} logged out", "user", user["id"])
    session.clear()
    return jsonify({"message": "Logged out"})


@auth_bp.route("/api/auth/me")
def auth_me():
    """Return the currently logged-in user's profile."""
    user = current_user()
    if user is None:
        return jsonify({"error": "Not authenticated"}), 401
    return jsonify(user)


@auth_bp.route("/api/auth/users", methods=["GET"])
def auth_users():
    """List all users."""
    conn = get_db()
    rows = conn.execute(
        "SELECT id, username, full_name as name, role, district, is_active FROM users"
    ).fetchall()
    return jsonify(_rows_to_list(rows))


@auth_bp.route("/api/auth/users", methods=["POST"])
def admin_create_user():
    """Admin endpoint to create an instantly active user."""
    user = current_user()
    if not user or user["role"] != "system_admin":
        return jsonify({"error": "Unauthorized"}), 403
        
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    full_name = data.get("full_name", "").strip()
    role = data.get("role", "cci_staff")
    district = data.get("district", "Hyderabad")
    
    if not username or not password or not full_name:
        return jsonify({"error": "Missing required fields"}), 400
        
    conn = get_db()
    existing = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    if existing:
        return jsonify({"error": "Username already exists"}), 400
        
    user_id = str(uuid.uuid4())
    pw_hash = generate_password_hash(password)
    
    conn.execute(
        "INSERT INTO users (id, username, password_hash, full_name, role, district, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, username, pw_hash, full_name, role, district, 1)
    )
    conn.commit()
    audit("CREATE_USER", f"Admin created user {username}", "user", user_id)
    return jsonify({"message": "User created successfully"}), 201


@auth_bp.route("/api/auth/users/<user_id>/approve", methods=["PUT"])
def admin_approve_user(user_id):
    """Admin endpoint to approve a pending user."""
    user = current_user()
    if not user or user["role"] != "system_admin":
        return jsonify({"error": "Unauthorized"}), 403
        
    conn = get_db()
    conn.execute("UPDATE users SET is_active = 1 WHERE id = ?", (user_id,))
    conn.commit()
    audit("APPROVE_USER", f"Admin approved user ID {user_id}", "user", user_id)
    return jsonify({"message": "User approved successfully"})
