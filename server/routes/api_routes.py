import uuid
import json
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request
from server.db import get_db
from server.auth import current_user, require_login, audit
from server.utils import _row_to_dict, _rows_to_list, _now_iso

api_bp = Blueprint("api", __name__)

# ════════════════════════════════════════════════════════════════════════
#  Children
# ════════════════════════════════════════════════════════════════════════

@api_bp.route("/api/children")
def list_children():
    """List children with optional filters."""
    conn = get_db()
    query = "SELECT * FROM children WHERE 1=1"
    params = []

    for col in ("cci_id", "district", "legal_status",
                "admission_category", "is_lfa_eligible"):
        val = request.args.get(col)
        if val is not None:
            query += f" AND {col} = ?"
            params.append(val)

    rows = conn.execute(query + " ORDER BY created_at DESC", params).fetchall()
    return jsonify(_rows_to_list(rows))


@api_bp.route("/api/children/<child_id>")
def get_child(child_id):
    """Get a single child's details with their case history."""
    conn = get_db()
    child = conn.execute(
        "SELECT * FROM children WHERE id = ?", (child_id,)
    ).fetchone()
    if child is None:
        return jsonify({"error": "Child not found"}), 404

    history = conn.execute(
        "SELECT * FROM case_history WHERE child_id = ? ORDER BY event_date ASC",
        (child_id,),
    ).fetchall()

    result = _row_to_dict(child)
    result["case_history"] = _rows_to_list(history)
    return jsonify(result)


@api_bp.route("/api/children", methods=["POST"])
def register_child():
    """Register a new child, auto-generate child_code, create case history
    entry and a 30-day CWC hearing deadline."""
    user, err = require_login()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    conn = get_db()

    # Auto-generate child code
    year = datetime.now().year
    count = conn.execute(
        "SELECT COUNT(*) as cnt FROM children"
    ).fetchone()["cnt"]
    child_code = f"CWC-HYD-{year}-{count + 1:04d}"

    child_id = str(uuid.uuid4())
    now = _now_iso()

    conn.execute(
        """INSERT INTO children
           (id, child_code, name, date_of_birth, estimated_age, gender, admission_date,
            admission_category, physical_description, cci_id, district, legal_status,
            is_lfa_eligible, lfa_flag_reason, created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            child_id,
            child_code,
            data.get("name", ""),
            data.get("date_of_birth", ""),
            int(data.get("age", 0)) if data.get("age") else None,
            data.get("gender", "Other"),
            data.get("admission_date", now[:10]),
            data.get("admission_category", "other"),
            data.get("physical_description", ""),
            data.get("cci_id", "none"),
            data.get("district", "Hyderabad"),
            "Under Inquiry",
            data.get("is_lfa_eligible", 0),
            data.get("lfa_flag_reason", ""),
            now,
            now,
        ),
    )

    # Case history entry for admission
    conn.execute(
        """INSERT INTO case_history
           (id, child_id, event_type, event_date, description, performed_by)
           VALUES (?,?,?,?,?,?)""",
        (
            str(uuid.uuid4()),
            child_id,
            "ADMISSION",
            now,
            f"Child registered with code {child_code}",
            user.get("full_name", "Unknown"),
        ),
    )

    # 30-day CWC hearing deadline
    due_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    conn.execute(
        """INSERT INTO deadlines
           (id, child_id, deadline_type, notes, due_date, status, created_at)
           VALUES (?,?,?,?,?,?,?)""",
        (
            str(uuid.uuid4()),
            child_id,
            "CWC_HEARING",
            "First CWC hearing within 30 days of admission",
            due_date,
            "pending",
            now,
        ),
    )

    conn.commit()

    audit("REGISTER_CHILD", f"Registered child {child_code}",
           "child", child_id)

    child = conn.execute(
        "SELECT * FROM children WHERE id = ?", (child_id,)
    ).fetchone()
    return jsonify(_row_to_dict(child)), 201


@api_bp.route("/api/children/<child_id>/status", methods=["PUT"])
def update_child_status(child_id):
    """Update a child's legal status and record it in case history."""
    user, err = require_login()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    new_status = data.get("legal_status", "").strip()
    if not new_status:
        return jsonify({"error": "legal_status is required"}), 400

    conn = get_db()
    child = conn.execute(
        "SELECT * FROM children WHERE id = ?", (child_id,)
    ).fetchone()
    if child is None:
        return jsonify({"error": "Child not found"}), 404

    old_status = child["legal_status"]
    now = _now_iso()

    status_map = {
        "under_inquiry": "Under Inquiry",
        "care_and_protection": "Under Review",
        "conflict_with_law": "Under Review",
        "restored": "Restored to Family",
        "foster_care": "Placed in Foster Care",
        "adopted": "Legally Free for Adoption",
        "aftercare": "Aged Out"
    }
    
    new_status = status_map.get(new_status, "Under Inquiry")

    conn.execute(
        "UPDATE children SET legal_status = ?, updated_at = ? WHERE id = ?",
        (new_status, now, child_id),
    )

    conn.execute(
        """INSERT INTO case_history
           (id, child_id, event_type, event_date, description, performed_by)
           VALUES (?,?,?,?,?,?)""",
        (
            str(uuid.uuid4()),
            child_id,
            "STATUS_CHANGE",
            now,
            f"{old_status} -> {new_status}. {data.get('notes', '')}",
            user.get("full_name", "Unknown"),
        ),
    )
    conn.commit()

    audit("UPDATE_CHILD_STATUS",
           f"Child {child['child_code']}: {old_status} → {new_status}",
           "child", child_id)

    updated = conn.execute(
        "SELECT * FROM children WHERE id = ?", (child_id,)
    ).fetchone()
    return jsonify(_row_to_dict(updated))


# ════════════════════════════════════════════════════════════════════════
#  Case History
# ════════════════════════════════════════════════════════════════════════

@api_bp.route("/api/children/<child_id>/history")
def child_history(child_id):
    """Return the immutable case-history timeline for a child."""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM case_history WHERE child_id = ? ORDER BY event_date ASC",
        (child_id,),
    ).fetchall()
    return jsonify(_rows_to_list(rows))


# ════════════════════════════════════════════════════════════════════════
#  Hearings
# ════════════════════════════════════════════════════════════════════════

@api_bp.route("/api/hearings")
def list_hearings():
    """List hearings with optional filters."""
    conn = get_db()
    query = "SELECT * FROM hearings WHERE 1=1"
    params = []

    for col in ("district", "status", "child_id"):
        val = request.args.get(col)
        if val is not None:
            query += f" AND {col} = ?"
            params.append(val)

    rows = conn.execute(
        query + " ORDER BY hearing_date DESC", params
    ).fetchall()
    return jsonify(_rows_to_list(rows))


@api_bp.route("/api/hearings/<hearing_id>")
def get_hearing(hearing_id):
    """Get a single hearing's details."""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM hearings WHERE id = ?", (hearing_id,)
    ).fetchone()
    if row is None:
        return jsonify({"error": "Hearing not found"}), 404
    return jsonify(_row_to_dict(row))


@api_bp.route("/api/hearings", methods=["POST"])
def create_hearing():
    """Schedule a new hearing."""
    user, err = require_login()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    conn = get_db()
    hearing_id = str(uuid.uuid4())
    now = _now_iso()

    conn.execute(
        """INSERT INTO hearings
           (id, child_id, hearing_date, scheduled_time, status, reschedule_reason, attendees, transcript_raw, transcript_edited, transcript_language, notes, created_by, district, created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            hearing_id,
            data.get("child_id", ""),
            data.get("hearing_date", now[:10]),
            data.get("hearing_time", ""),
            "scheduled",
            "",
            data.get("attendees", "[]"),
            "",
            "",
            "hi",
            data.get("notes", ""),
            user.get("full_name", "Unknown"),
            data.get("district", "Hyderabad"),
            now,
            now,
        ),
    )
    conn.commit()

    audit("SCHEDULE_HEARING", f"Hearing scheduled for child {data.get('child_id','')}",
           "hearing", hearing_id)

    row = conn.execute(
        "SELECT * FROM hearings WHERE id = ?", (hearing_id,)
    ).fetchone()
    return jsonify(_row_to_dict(row)), 201


@api_bp.route("/api/hearings/<hearing_id>", methods=["PUT"])
def update_hearing(hearing_id):
    """Update hearing details (status, transcript, notes, attendees)."""
    user, err = require_login()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    conn = get_db()

    row = conn.execute(
        "SELECT * FROM hearings WHERE id = ?", (hearing_id,)
    ).fetchone()
    if row is None:
        return jsonify({"error": "Hearing not found"}), 404

    updates = []
    params = []
    for col in ("status", "transcript", "notes", "attendees",
                "hearing_date", "hearing_time", "location"):
        if col in data:
            updates.append(f"{col} = ?")
            params.append(data[col])

    if updates:
        updates.append("updated_at = ?")
        params.append(_now_iso())
        params.append(hearing_id)
        conn.execute(
            f"UPDATE hearings SET {', '.join(updates)} WHERE id = ?",
            params,
        )
        conn.commit()

    audit("UPDATE_HEARING", f"Hearing {hearing_id} updated",
           "hearing", hearing_id)

    updated = conn.execute(
        "SELECT * FROM hearings WHERE id = ?", (hearing_id,)
    ).fetchone()
    return jsonify(_row_to_dict(updated))


@api_bp.route("/api/hearings/<hearing_id>/audio", methods=["POST"])
def upload_hearing_audio(hearing_id):
    """Upload and permanently save the final complete audio recording for a hearing."""
    user, err = require_login()
    if err:
        return err

    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    file = request.files["audio"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    conn = get_db()
    row = conn.execute("SELECT * FROM hearings WHERE id = ?", (hearing_id,)).fetchone()
    if row is None:
        return jsonify({"error": "Hearing not found"}), 404

    # Ensure uploads directory exists
    import os
    upload_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "uploads", "hearings")
    os.makedirs(upload_dir, exist_ok=True)

    filename = f"{hearing_id}.wav"
    filepath = os.path.join(upload_dir, filename)
    file.save(filepath)

    audio_url = f"/uploads/hearings/{filename}"

    conn.execute(
        "UPDATE hearings SET audio_url = ?, updated_at = ? WHERE id = ?",
        (audio_url, _now_iso(), hearing_id),
    )
    conn.commit()

    audit("UPLOAD_HEARING_AUDIO", f"Audio uploaded for hearing {hearing_id}", "hearing", hearing_id)

    updated = conn.execute("SELECT * FROM hearings WHERE id = ?", (hearing_id,)).fetchone()
    return jsonify(_row_to_dict(updated))


# ════════════════════════════════════════════════════════════════════════
#  Orders
# ════════════════════════════════════════════════════════════════════════

@api_bp.route("/api/orders")
def list_orders():
    """List orders with optional filters."""
    conn = get_db()
    query = "SELECT * FROM orders WHERE 1=1"
    params = []

    for col in ("district", "status", "child_id"):
        val = request.args.get(col)
        if val is not None:
            query += f" AND {col} = ?"
            params.append(val)

    rows = conn.execute(
        query + " ORDER BY created_at DESC", params
    ).fetchall()
    return jsonify(_rows_to_list(rows))


@api_bp.route("/api/orders/<order_id>")
def get_order(order_id):
    """Get a single order's details."""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM orders WHERE id = ?", (order_id,)
    ).fetchone()
    if row is None:
        return jsonify({"error": "Order not found"}), 404
    return jsonify(_row_to_dict(row))


@api_bp.route("/api/orders", methods=["POST"])
def create_order():
    """Create a new order. Auto-generates order_number and pre-fills from
    child data and the latest hearing transcript."""
    user, err = require_login()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    conn = get_db()

    # Auto-generate order number
    year = datetime.now().year
    count = conn.execute(
        "SELECT COUNT(*) as cnt FROM orders"
    ).fetchone()["cnt"]
    order_number = f"ORD-HYD-{year}-{count + 1:04d}"

    order_id = str(uuid.uuid4())
    now = _now_iso()

    # Pre-fill from child data if child_id provided
    child_id = data.get("child_id", "")
    child_name = ""
    child_code = ""
    transcript = data.get("transcript", "")

    if child_id:
        child = conn.execute(
            "SELECT * FROM children WHERE id = ?", (child_id,)
        ).fetchone()
        if child:
            child_name = child["name"]
            child_code = child["child_code"]

        # Grab latest hearing transcript if not supplied
        if not transcript:
            latest_hearing = conn.execute(
                """SELECT transcript_raw FROM hearings
                   WHERE child_id = ? AND transcript_raw != ''
                   ORDER BY hearing_date DESC LIMIT 1""",
                (child_id,),
            ).fetchone()
            if latest_hearing:
                transcript = latest_hearing["transcript_raw"]

    conn.execute(
        """INSERT INTO orders
           (id, order_number, child_id, hearing_id, order_type,
            district, status, order_body, findings, created_by,
            created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (
            order_id,
            order_number,
            child_id,
            data.get("hearing_id", ""),
            data.get("order_type", "other"),
            data.get("district", "Hyderabad"),
            "draft",
            data.get("order_body", ""),
            data.get("findings", ""),
            user.get("full_name", "Unknown"),
            now,
        ),
    )
    conn.commit()

    audit("CREATE_ORDER", f"Order {order_number} created",
           "order", order_id)

    row = conn.execute(
        "SELECT * FROM orders WHERE id = ?", (order_id,)
    ).fetchone()
    return jsonify(_row_to_dict(row)), 201


@api_bp.route("/api/orders/<order_id>/approve", methods=["PUT"])
def approve_order(order_id):
    """Approve an order. In production, only chairperson; in prototype any
    authenticated user may approve."""
    user, err = require_login()
    if err:
        return err

    conn = get_db()
    row = conn.execute(
        "SELECT * FROM orders WHERE id = ?", (order_id,)
    ).fetchone()
    if row is None:
        return jsonify({"error": "Order not found"}), 404

    now = _now_iso()
    conn.execute(
        """UPDATE orders SET status = 'approved', approved_by = ?,
           updated_at = ? WHERE id = ?""",
        (user.get("full_name", "Unknown"), now, order_id),
    )
    conn.commit()

    audit("APPROVE_ORDER",
           f"Order {row['order_number']} approved by {user['name']}",
           "order", order_id)

    updated = conn.execute(
        "SELECT * FROM orders WHERE id = ?", (order_id,)
    ).fetchone()
    return jsonify(_row_to_dict(updated))


@api_bp.route("/api/orders/<order_id>/print")
def print_order(order_id):
    """Return the order data formatted for print / PDF generation."""
    conn = get_db()
    order = conn.execute(
        "SELECT * FROM orders WHERE id = ?", (order_id,)
    ).fetchone()
    if order is None:
        return jsonify({"error": "Order not found"}), 404

    order_dict = _row_to_dict(order)

    # Enrich with child data if available
    if order_dict.get("child_id"):
        child = conn.execute(
            "SELECT * FROM children WHERE id = ?",
            (order_dict["child_id"],),
        ).fetchone()
        if child:
            order_dict["child"] = _row_to_dict(child)

    order_dict["print_format"] = True
    order_dict["generated_at"] = _now_iso()
    return jsonify(order_dict)


# ════════════════════════════════════════════════════════════════════════
#  CCIs  (Child Care Institutions)
# ════════════════════════════════════════════════════════════════════════

@api_bp.route("/api/ccis")
def list_ccis():
    """List all registered CCIs."""
    conn = get_db()
    rows = conn.execute("SELECT * FROM ccis ORDER BY name").fetchall()
    return jsonify(_rows_to_list(rows))


@api_bp.route("/api/ccis/<cci_id>")
def get_cci(cci_id):
    """Get CCI detail with occupancy, children count, and visit history."""
    conn = get_db()
    cci = conn.execute(
        "SELECT * FROM ccis WHERE id = ?", (cci_id,)
    ).fetchone()
    if cci is None:
        return jsonify({"error": "CCI not found"}), 404

    result = _row_to_dict(cci)

    children_count = conn.execute(
        "SELECT COUNT(*) as cnt FROM children WHERE cci_id = ?", (cci_id,)
    ).fetchone()["cnt"]
    result["children_count"] = children_count
    result["occupancy_pct"] = (
        round(children_count / result["capacity"] * 100, 1)
        if result.get("capacity") and result["capacity"] > 0 else 0
    )

    visits = conn.execute(
        """SELECT * FROM cci_visits WHERE cci_id = ?
           ORDER BY visit_date DESC""",
        (cci_id,),
    ).fetchall()
    result["inspections"] = _rows_to_list(visits)

    return jsonify(result)


# ════════════════════════════════════════════════════════════════════════
#  Family Visits
# ════════════════════════════════════════════════════════════════════════

@api_bp.route("/api/children/<child_id>/visits")
def list_family_visits(child_id):
    """Get the family-visit log for a child."""
    conn = get_db()
    rows = conn.execute(
        """SELECT * FROM family_visits WHERE child_id = ?
           ORDER BY visit_date DESC""",
        (child_id,),
    ).fetchall()
    return jsonify(_rows_to_list(rows))


@api_bp.route("/api/children/<child_id>/visits", methods=["POST"])
def log_family_visit(child_id):
    """Log a new family visit for a child."""
    user, err = require_login()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    conn = get_db()

    visit_id = str(uuid.uuid4())
    now = _now_iso()

    conn.execute(
        """INSERT INTO family_visits
           (id, child_id, visit_date, visitor_name, relationship,
            duration_minutes, notes, logged_by, created_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (
            visit_id,
            child_id,
            data.get("visit_date", now[:10]),
            data.get("visitor_name", ""),
            data.get("relationship", ""),
            data.get("duration_minutes", 0),
            data.get("notes", ""),
            user.get("full_name", "Unknown"),
            now,
        ),
    )

    conn.commit()

    audit("LOG_FAMILY_VISIT",
           f"Family visit logged for child {child_id}",
           "family_visit", visit_id)

    row = conn.execute(
        "SELECT * FROM family_visits WHERE id = ?", (visit_id,)
    ).fetchone()
    return jsonify(_row_to_dict(row)), 201


# ════════════════════════════════════════════════════════════════════════
#  CCI Inspections
# ════════════════════════════════════════════════════════════════════════

@api_bp.route("/api/ccis/<cci_id>/inspections")
def list_inspections(cci_id):
    """Get the inspection visit log for a CCI."""
    conn = get_db()
    rows = conn.execute(
        """SELECT * FROM cci_visits WHERE cci_id = ?
           ORDER BY visit_date DESC""",
        (cci_id,),
    ).fetchall()
    return jsonify(_rows_to_list(rows))


@api_bp.route("/api/ccis/<cci_id>/inspections", methods=["POST"])
def log_inspection(cci_id):
    """Log a DCPU inspection visit to a CCI."""
    user, err = require_login()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    conn = get_db()

    inspection_id = str(uuid.uuid4())
    now = _now_iso()

    conn.execute(
        """INSERT INTO cci_visits
           (id, cci_id, visit_date, officer_id, findings, recommendations, created_at)
           VALUES (?,?,?,?,?,?,?)""",
        (
            inspection_id,
            cci_id,
            data.get("visit_date", now[:10]),
            user.get("id"),
            data.get("findings", ""),
            data.get("recommendations", ""),
            now,
        ),
    )

    conn.commit()

    audit("LOG_INSPECTION",
           f"Inspection logged for CCI {cci_id}",
           "cci_inspection", inspection_id)

    row = conn.execute(
        "SELECT * FROM cci_visits WHERE id = ?", (inspection_id,)
    ).fetchone()
    return jsonify(_row_to_dict(row)), 201


# ════════════════════════════════════════════════════════════════════════
#  Dashboard & Alerts
# ════════════════════════════════════════════════════════════════════════

@api_bp.route("/api/dashboard/stats")
def dashboard_stats():
    """Return aggregate statistics for the dashboard."""
    conn = get_db()
    now = datetime.now()
    six_months_ago = (now - timedelta(days=180)).strftime("%Y-%m-%d")

    total_children = conn.execute(
        "SELECT COUNT(*) as cnt FROM children"
    ).fetchone()["cnt"]

    # By legal status
    status_rows = conn.execute(
        """SELECT legal_status, COUNT(*) as cnt FROM children
           GROUP BY legal_status"""
    ).fetchall()
    by_status = {r["legal_status"]: r["cnt"] for r in status_rows}

    # By admission category
    cat_rows = conn.execute(
        """SELECT admission_category, COUNT(*) as cnt FROM children
           GROUP BY admission_category"""
    ).fetchall()
    by_category = {r["admission_category"]: r["cnt"] for r in cat_rows}

    total_ccis = conn.execute(
        "SELECT COUNT(*) as cnt FROM ccis"
    ).fetchone()["cnt"]
    total_hearings = conn.execute(
        "SELECT COUNT(*) as cnt FROM hearings"
    ).fetchone()["cnt"]
    total_orders = conn.execute(
        "SELECT COUNT(*) as cnt FROM orders"
    ).fetchone()["cnt"]

    # Deadline statistics
    today = now.strftime("%Y-%m-%d")
    seven_days = (now + timedelta(days=7)).strftime("%Y-%m-%d")

    overdue = conn.execute(
        """SELECT COUNT(*) as cnt FROM deadlines
           WHERE status = 'pending' AND due_date < ?""",
        (today,),
    ).fetchone()["cnt"]

    approaching = conn.execute(
        """SELECT COUNT(*) as cnt FROM deadlines
           WHERE status = 'pending' AND due_date >= ? AND due_date <= ?""",
        (today, seven_days),
    ).fetchone()["cnt"]

    # Children approaching age-out (17+ years old)
    ageout = conn.execute(
        "SELECT COUNT(*) as cnt FROM children WHERE estimated_age >= 17"
    ).fetchone()["cnt"]

    # Children with no family contact for 6+ months
    no_contact = conn.execute(
        """SELECT COUNT(*) as cnt FROM children c
           WHERE NOT EXISTS (
               SELECT 1 FROM family_visits fv
               WHERE fv.child_id = c.id AND fv.visit_date >= ?
           )""",
        (six_months_ago,),
    ).fetchone()["cnt"]

    # LFA eligible
    lfa = conn.execute(
        "SELECT COUNT(*) as cnt FROM children WHERE is_lfa_eligible = 1"
    ).fetchone()["cnt"]

    return jsonify({
        "total_children":               total_children,
        "by_status":                    by_status,
        "by_category":                  by_category,
        "total_ccis":                   total_ccis,
        "total_hearings":               total_hearings,
        "total_orders":                 total_orders,
        "overdue_deadlines":            overdue,
        "approaching_deadlines":        approaching,
        "children_approaching_ageout":  ageout,
        "children_no_family_contact":   no_contact,
        "lfa_eligible_count":           lfa,
    })


@api_bp.route("/api/dashboard/deadlines")
def dashboard_deadlines():
    """List all deadlines with urgency colour coding."""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM deadlines ORDER BY due_date ASC"
    ).fetchall()

    now = datetime.now()
    seven_days = now + timedelta(days=7)
    result = []

    for r in rows:
        d = _row_to_dict(r)
        try:
            due = datetime.strptime(d["due_date"], "%Y-%m-%d")
        except (ValueError, TypeError):
            due = now

        if d.get("status") == "completed":
            d["urgency"] = "green"
        elif due < now:
            d["urgency"] = "red"
        elif due <= seven_days:
            d["urgency"] = "amber"
        else:
            d["urgency"] = "green"

        result.append(d)

    return jsonify(result)


@api_bp.route("/api/dashboard/alerts")
def dashboard_alerts():
    """Generate alerts: age-out, LFA flags, no-contact, overdue deadlines."""
    conn = get_db()
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    six_months_ago = (now - timedelta(days=180)).strftime("%Y-%m-%d")
    alerts = []

    # Age-out alerts (children aged 17+)
    ageout_children = conn.execute(
        "SELECT id, child_code, name, estimated_age FROM children WHERE estimated_age >= 17"
    ).fetchall()
    for c in ageout_children:
        alerts.append({
            "type":     "AGE_OUT",
            "severity": "high",
            "child_id": c["id"],
            "child_code": c["child_code"],
            "message":  f"{c['name']} (age {c['estimated_age']}) is approaching age-out",
        })

    # LFA eligible children
    lfa_children = conn.execute(
        """SELECT id, child_code, name FROM children
           WHERE is_lfa_eligible = 1"""
    ).fetchall()
    for c in lfa_children:
        alerts.append({
            "type":     "LFA_ELIGIBLE",
            "severity": "medium",
            "child_id": c["id"],
            "child_code": c["child_code"],
            "message":  f"{c['name']} is eligible for Legal Free for Adoption",
        })

    # No family contact for 6+ months
    no_contact = conn.execute(
        """SELECT c.id, c.child_code, c.name FROM children c
           WHERE NOT EXISTS (
               SELECT 1 FROM family_visits fv
               WHERE fv.child_id = c.id AND fv.visit_date >= ?
           )""",
        (six_months_ago,),
    ).fetchall()
    for c in no_contact:
        alerts.append({
            "type":     "NO_FAMILY_CONTACT",
            "severity": "medium",
            "child_id": c["id"],
            "child_code": c["child_code"],
            "message":  f"{c['name']} has had no family contact for 6+ months",
        })

    # Overdue deadlines
    overdue = conn.execute(
        """SELECT d.*, c.child_code, c.name as child_name
           FROM deadlines d
           LEFT JOIN children c ON d.child_id = c.id
           WHERE d.status = 'pending' AND d.due_date < ?""",
        (today,),
    ).fetchall()
    for d in overdue:
        alerts.append({
            "type":     "OVERDUE_DEADLINE",
            "severity": "high",
            "child_id": d["child_id"],
            "child_code": d["child_code"] or "",
            "message":  (f"Overdue: {d['notes']} for "
                         f"{d['child_name'] or 'unknown'} "
                         f"(due {d['due_date']})"),
        })

    return jsonify(alerts)


# ════════════════════════════════════════════════════════════════════════
#  Reports
# ════════════════════════════════════════════════════════════════════════

@api_bp.route("/api/reports/monthly")
def monthly_report():
    """Generate monthly district report data."""
    month = request.args.get("month", datetime.now().month, type=int)
    year  = request.args.get("year", datetime.now().year, type=int)

    # Build date range for the month
    start = f"{year}-{month:02d}-01"
    if month == 12:
        end = f"{year + 1}-01-01"
    else:
        end = f"{year}-{month + 1:02d}-01"

    conn = get_db()

    admissions = conn.execute(
        """SELECT COUNT(*) as cnt FROM children
           WHERE admission_date >= ? AND admission_date < ?""",
        (start, end),
    ).fetchone()["cnt"]

    hearings = conn.execute(
        """SELECT COUNT(*) as cnt FROM hearings
           WHERE hearing_date >= ? AND hearing_date < ?""",
        (start, end),
    ).fetchone()["cnt"]

    orders = conn.execute(
        """SELECT COUNT(*) as cnt FROM orders
           WHERE created_at >= ? AND created_at < ?""",
        (start, end),
    ).fetchone()["cnt"]

    restorations = conn.execute(
        """SELECT COUNT(*) as cnt FROM case_history
           WHERE event_type = 'status_change' 
             AND (description LIKE '%Restored%' OR metadata LIKE '%Restored%')
             AND event_date >= ? AND event_date < ?""",
        (start, end),
    ).fetchone()["cnt"]

    adoptions = conn.execute(
        """SELECT COUNT(*) as cnt FROM case_history
           WHERE event_type = 'status_change' 
             AND (description LIKE '%Adopted%' OR metadata LIKE '%Adopted%' OR description LIKE '%Adoption%' OR metadata LIKE '%Adoption%')
             AND event_date >= ? AND event_date < ?""",
        (start, end),
    ).fetchone()["cnt"]

    return jsonify({
        "month":          month,
        "year":           year,
        "admissions":     admissions,
        "hearings_held":  hearings,
        "orders_issued":  orders,
        "restorations":   restorations,
        "adoptions":      adoptions,
    })


@api_bp.route("/api/reports/quarterly")
def quarterly_report():
    """Generate quarterly state report data."""
    quarter = request.args.get("quarter", 1, type=int)
    year    = request.args.get("year", datetime.now().year, type=int)

    quarter_starts = {1: 1, 2: 4, 3: 7, 4: 10}
    start_month = quarter_starts.get(quarter, 1)
    end_month   = start_month + 3

    start = f"{year}-{start_month:02d}-01"
    if end_month > 12:
        end = f"{year + 1}-01-01"
    else:
        end = f"{year}-{end_month:02d}-01"

    conn = get_db()

    total_children = conn.execute(
        "SELECT COUNT(*) as cnt FROM children"
    ).fetchone()["cnt"]

    new_admissions = conn.execute(
        """SELECT COUNT(*) as cnt FROM children
           WHERE admission_date >= ? AND admission_date < ?""",
        (start, end),
    ).fetchone()["cnt"]

    hearings = conn.execute(
        """SELECT COUNT(*) as cnt FROM hearings
           WHERE hearing_date >= ? AND hearing_date < ?""",
        (start, end),
    ).fetchone()["cnt"]

    orders = conn.execute(
        """SELECT COUNT(*) as cnt FROM orders
           WHERE created_at >= ? AND created_at < ?""",
        (start, end),
    ).fetchone()["cnt"]

    # Status breakdown at current point
    status_rows = conn.execute(
        """SELECT legal_status, COUNT(*) as cnt FROM children
           GROUP BY legal_status"""
    ).fetchall()
    by_status = {r["legal_status"]: r["cnt"] for r in status_rows}

    # CCI occupancy summary
    ccis = conn.execute("SELECT * FROM ccis").fetchall()
    cci_summary = []
    for cci in ccis:
        count = conn.execute(
            "SELECT COUNT(*) as cnt FROM children WHERE cci_id = ?",
            (cci["id"],),
        ).fetchone()["cnt"]
        cci_summary.append({
            "name":       cci["name"],
            "capacity":   cci["capacity"],
            "current":    count,
            "occupancy":  round(count / cci["capacity"] * 100, 1)
                          if cci["capacity"] and cci["capacity"] > 0 else 0,
        })

    return jsonify({
        "quarter":          quarter,
        "year":             year,
        "total_children":   total_children,
        "new_admissions":   new_admissions,
        "hearings_held":    hearings,
        "orders_issued":    orders,
        "by_status":        by_status,
        "cci_occupancy":    cci_summary,
    })


# ════════════════════════════════════════════════════════════════════════
#  Audit Log
# ════════════════════════════════════════════════════════════════════════

@api_bp.route("/api/audit")
def audit_log():
    """Return audit log entries (all roles may view in prototype)."""
    conn = get_db()
    limit = request.args.get("limit", 200, type=int)
    rows = conn.execute(
        "SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return jsonify(_rows_to_list(rows))
