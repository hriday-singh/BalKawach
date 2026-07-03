import uuid
import json
import os
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Request, HTTPException, Depends, UploadFile, File, BackgroundTasks
from werkzeug.security import generate_password_hash

from server.db import get_db, _iso_now
from server.utils import _row_to_dict, _rows_to_list, compute_age
from server.fastapi_routes.dependencies import (
    get_current_user, require_roles, audit,
    DATA_READ_ROLES, DATA_ENTRY_ROLES, CHAIR_ROLES, ADMIN_ROLES, DCPU_ROLES
)
from server.fastapi_routes.api_schemas import *

import socket

router = APIRouter()


def _parse_due_date(value: str) -> datetime:
    """Deadline due_date is stored as YYYY-MM-DD, but tolerate a full ISO datetime too."""
    return datetime.strptime(value[:10], "%Y-%m-%d")

@router.get("/api/system/network-info")
def get_network_info():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return {"lan_ip": IP}
# ════════════════════════════════════════════════════════════════════════
#  Users (System Admin only)
# ════════════════════════════════════════════════════════════════════════

@router.get("/api/users", response_model=List[User])
def list_users(
    request: Request,
    user=Depends(require_roles(DATA_READ_ROLES))
):
    db = get_db()
    rows = db.execute("SELECT id, username, full_name, role, district, location, cci_id, email, phone, is_active, created_at FROM users").fetchall()
    return _rows_to_list(rows)

@router.post("/api/users", response_model=User)
def create_user(
    req: UserCreate,
    request: Request,
    user=Depends(require_roles(["system_admin"]))
):
    db = get_db()
    
    # Check if username exists
    existing = db.execute("SELECT id FROM users WHERE username = ?", (req.username,)).fetchone()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
        
    user_id = str(uuid.uuid4())
    password_hash = generate_password_hash(req.password)
    
    db.execute("""
        INSERT INTO users (id, username, password_hash, full_name, role, district, location, cci_id, email, phone, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id, req.username, password_hash, req.full_name, req.role,
        req.district, req.location, req.cci_id, req.email, req.phone, 1 if req.is_active else 0
    ))
    db.commit()
    
    audit(db, user["id"], "CREATE_USER", "users", user_id, f"Created user {req.username}", request.client.host)
    
    new_user = db.execute("SELECT id, username, full_name, role, district, location, cci_id, email, phone, is_active, created_at FROM users WHERE id = ?", (user_id,)).fetchone()
    return _row_to_dict(new_user)

# ════════════════════════════════════════════════════════════════════════
#  Children
# ════════════════════════════════════════════════════════════════════════

@router.get("/api/children", response_model=List[ChildResponse])
def list_children(
    request: Request,
    cci_id: Optional[str] = None,
    district: Optional[str] = None,
    legal_status: Optional[str] = None,
    admission_category: Optional[str] = None,
    is_lfa_eligible: Optional[int] = None,
    user: dict = Depends(require_roles(DATA_READ_ROLES))
):
    conn = get_db()
    auth_sql, auth_params = get_dashboard_filter(user)
    
    query = f"SELECT * FROM children WHERE {auth_sql}"
    params = list(auth_params)

    filters = {
        "cci_id": cci_id,
        "district": district,
        "legal_status": legal_status,
        "admission_category": admission_category,
        "is_lfa_eligible": is_lfa_eligible
    }

    for col, val in filters.items():
        if val is not None:
            query += f" AND {col} = ?"
            params.append(val)

    rows = conn.execute(query + " ORDER BY created_at DESC", params).fetchall()
    return _rows_to_list(rows)


@router.get("/api/children/search", response_model=List[ChildResponse])
def search_children(q: str = "", user: dict = Depends(require_roles(DATA_READ_ROLES))):
    q = q.strip()
    if not q:
        return []

    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM children WHERE name LIKE ? OR child_code LIKE ? ORDER BY created_at DESC LIMIT 50",
        (f"%{q}%", f"%{q}%")
    ).fetchall()
    return _rows_to_list(rows)


@router.get("/api/children/{child_id}", response_model=ChildResponse)
def get_child(child_id: str, user: dict = Depends(require_roles(DATA_READ_ROLES))):
    conn = get_db()
    child = conn.execute(
        """SELECT children.*, ccis.name as cci_name, ccis.district as cci_district 
           FROM children 
           LEFT JOIN ccis ON children.cci_id = ccis.id 
           WHERE children.id = ?""", 
        (child_id,)
    ).fetchone()
    if child is None:
        raise HTTPException(status_code=404, detail="Child not found")

    history = conn.execute(
        """SELECT h.*, 
                  u.full_name as performed_by_name, 
                  u.role as performed_by_role,
                  u.location as performed_by_location
           FROM case_history h
           LEFT JOIN users u ON h.performed_by = u.id
           WHERE h.child_id = ? ORDER BY h.event_date DESC""",
        (child_id,),
    ).fetchall()

    result = _row_to_dict(child)
    result["case_history"] = _rows_to_list(history)
    return result


@router.post("/api/children", response_model=ChildResponse, status_code=201)
def register_child(data: ChildRegisterRequest, request: Request, user: dict = Depends(require_roles(DATA_ENTRY_ROLES))):
    conn = get_db()
    now = _iso_now()

    year = datetime.now().year
    # Dynamically generate prefix based on assigned CCI's district
    cci = conn.execute("SELECT district FROM ccis WHERE id = ?", (data.cci_id,)).fetchone()
    cci_district = cci["district"] if (cci and cci["district"]) else "Unknown"
    district_prefix = cci_district[:3].upper() if cci_district != "Unknown" else "UNK"
    
    count = conn.execute("SELECT COUNT(*) as cnt FROM children WHERE child_code LIKE ?", (f"CWC-{district_prefix}-{year}-%",)).fetchone()["cnt"]
    child_code = f"CWC-{district_prefix}-{year}-{count + 1:04d}"

    child_id = str(uuid.uuid4())
    
    conn.execute(
        """INSERT INTO children
           (id, child_code, name, date_of_birth, estimated_age, gender, admission_date,
            admission_category, physical_description, cci_id, district, legal_status,
            is_lfa_eligible, lfa_flag_reason, created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            child_id, child_code, data.name, data.date_of_birth, data.age,
            data.gender, data.admission_date or now[:10], data.admission_category,
            data.physical_description, data.cci_id, cci_district,
            "Under Inquiry", data.is_lfa_eligible, data.lfa_flag_reason, now, now,
        ),
    )

    conn.execute(
        """INSERT INTO case_history
           (id, child_id, event_type, event_date, description, performed_by)
           VALUES (?,?,?,?,?,?)""",
        (
            str(uuid.uuid4()), child_id, "ADMISSION", now,
            f"Child registered with code {child_code}",
            user.get("id"),
        ),
    )

    due_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    
    if (data.admission_category or "").lower() == "surrendered":
        reconsideration_due = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")
        conn.execute(
            """INSERT INTO deadlines
               (id, child_id, deadline_type, notes, due_date, status, created_at)
               VALUES (?,?,?,?,?,?,?)""",
            (str(uuid.uuid4()), child_id, "60_DAY_RECONSIDERATION",
             "60-day reconsideration period for surrendered child", reconsideration_due, "pending", now),
        )

    conn.execute(
        """INSERT INTO deadlines
           (id, child_id, deadline_type, notes, due_date, status, created_at)
           VALUES (?,?,?,?,?,?,?)""",
        (str(uuid.uuid4()), child_id, "CWC_HEARING",
         "First CWC hearing within 30 days of admission", due_date, "pending", now),
    )

    conn.commit()
    audit(request, "REGISTER_CHILD", f"Registered child {child_code}", "child", child_id)

    child = conn.execute("SELECT * FROM children WHERE id = ?", (child_id,)).fetchone()
    return _row_to_dict(child)


@router.put("/api/children/{child_id}/status", response_model=ChildResponse)
def update_child_status(child_id: str, data: ChildStatusUpdateRequest, request: Request, user: dict = Depends(require_roles(DATA_ENTRY_ROLES))):
    new_status = data.legal_status.strip()
    if not new_status:
        raise HTTPException(status_code=400, detail="legal_status is required")

    conn = get_db()
    print("USER DICT IN UPDATE_CHILD_STATUS:", user)
    child = conn.execute("SELECT * FROM children WHERE id = ?", (child_id,)).fetchone()
    if child is None:
        raise HTTPException(status_code=404, detail="Child not found")

    old_status = child["legal_status"]
    now = _iso_now()

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

    conn.execute("UPDATE children SET legal_status = ?, updated_at = ? WHERE id = ?", (new_status, now, child_id))
    conn.execute(
        """INSERT INTO case_history
           (id, child_id, event_type, event_date, description, performed_by)
           VALUES (?,?,?,?,?,?)""",
        (str(uuid.uuid4()), child_id, "STATUS_CHANGE", now, f"{old_status} -> {new_status}. {data.notes}", user.get("id")),
    )
    conn.commit()
    audit(request, "UPDATE_CHILD_STATUS", f"Child {child['child_code']}: {old_status} → {new_status}", "child", child_id)

    updated = conn.execute("SELECT * FROM children WHERE id = ?", (child_id,)).fetchone()
    return _row_to_dict(updated)

@router.get("/api/test-user")
def test_user(user: dict = Depends(require_roles(DATA_ENTRY_ROLES))):
    return user


@router.put("/api/children/{child_id}", response_model=ChildResponse)
def update_child(child_id: str, data: ChildUpdateRequest, request: Request, user: dict = Depends(require_roles(DATA_ENTRY_ROLES))):
    conn = get_db()
    row = conn.execute("SELECT * FROM children WHERE id = ?", (child_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Child not found")

    updates = []
    params = []
    
    fields = {
        "name": data.name,
        "date_of_birth": data.date_of_birth,
        "estimated_age": data.estimated_age,
        "gender": data.gender,
        "physical_description": data.physical_description,
        "cci_id": data.cci_id,
        "district": data.district,
        "is_lfa_eligible": data.is_lfa_eligible,
        "lfa_flag_reason": data.lfa_flag_reason
    }

    for col, val in fields.items():
        if val is not None:
            updates.append(f"{col} = ?")
            params.append(val)

    if updates:
        updates.append("updated_at = ?")
        params.append(_iso_now())
        params.append(child_id)
        conn.execute(f"UPDATE children SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()

    audit(request, "UPDATE_CHILD", f"Child {child_id} updated", "child", child_id)
    updated = conn.execute("SELECT * FROM children WHERE id = ?", (child_id,)).fetchone()
    return _row_to_dict(updated)



# ════════════════════════════════════════════════════════════════════════
#  Case History
# ════════════════════════════════════════════════════════════════════════

@router.get("/api/children/{child_id}/history", response_model=List[CaseHistoryEntry])
def child_history(child_id: str, user: dict = Depends(require_roles(DATA_READ_ROLES))):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM case_history WHERE child_id = ? ORDER BY event_date DESC",
        (child_id,),
    ).fetchall()
    return _rows_to_list(rows)

# ════════════════════════════════════════════════════════════════════════
#  Hearings
# ════════════════════════════════════════════════════════════════════════

@router.get("/api/hearings", response_model=List[HearingResponse])
def list_hearings(
    district: Optional[str] = None,
    status: Optional[str] = None,
    child_id: Optional[str] = None,
    user: dict = Depends(require_roles(DATA_READ_ROLES))
):
    conn = get_db()
    query = """
        SELECT h.*, c.name as child_name, c.child_code 
        FROM hearings h
        LEFT JOIN children c ON h.child_id = c.id
        WHERE 1=1
    """
    params = []

    filters = {"h.district": district, "h.status": status, "h.child_id": child_id}

    for col, val in filters.items():
        if val is not None:
            query += f" AND {col} = ?"
            params.append(val)

    rows = conn.execute(query + " ORDER BY h.hearing_date DESC", params).fetchall()
    return _rows_to_list(rows)


@router.get("/api/hearings/{hearing_id}", response_model=HearingResponse)
def get_hearing(hearing_id: str, user: dict = Depends(require_roles(DATA_READ_ROLES))):
    conn = get_db()
    row = conn.execute("SELECT * FROM hearings WHERE id = ?", (hearing_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Hearing not found")
    return _row_to_dict(row)


@router.post("/api/hearings", response_model=HearingResponse, status_code=201)
def create_hearing(data: HearingCreateRequest, request: Request, user: dict = Depends(require_roles(DATA_ENTRY_ROLES))):
    conn = get_db()
    
    # Check duplicate active hearings
    existing = conn.execute("SELECT * FROM hearings WHERE child_id = ? AND status = 'scheduled'", (data.child_id,)).fetchone()
    if existing:
        raise HTTPException(status_code=400, detail="An active scheduled hearing already exists for this child.")
        
    hearing_id = str(uuid.uuid4())
    now = _iso_now()

    conn.execute(
        """INSERT INTO hearings
           (id, child_id, hearing_date, scheduled_time, status, reschedule_reason, attendees, transcript_raw, transcript_edited, transcript_language, notes, created_by, district, created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            hearing_id, data.child_id, data.hearing_date or now[:10],
            data.hearing_time, "scheduled", "", data.attendees,
            "", "", "hi", data.notes, user.get("full_name", "Unknown"),
            data.district, now, now,
        ),
    )
    conn.commit()
    audit(request, "SCHEDULE_HEARING", f"Hearing scheduled for child {data.child_id}", "hearing", hearing_id)

    row = conn.execute("SELECT * FROM hearings WHERE id = ?", (hearing_id,)).fetchone()
    return _row_to_dict(row)


@router.put("/api/hearings/{hearing_id}", response_model=HearingResponse)
def update_hearing(hearing_id: str, data: HearingUpdateRequest, request: Request, user: dict = Depends(require_roles(DATA_ENTRY_ROLES))):
    conn = get_db()
    row = conn.execute("SELECT * FROM hearings WHERE id = ?", (hearing_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Hearing not found")

    updates = []
    params = []
    
    fields = {
        "status": data.status,
        "transcript_raw": data.transcript_raw,
        "transcript_edited": data.transcript_edited,
        "transcript_finalized": data.transcript_finalized,
        "notes": data.notes,
        "attendees": data.attendees,
        "hearing_date": data.hearing_date,
        "scheduled_time": data.scheduled_time,
        "district": data.district
    }

    for db_col, val in fields.items():
        if val is not None:
            updates.append(f"{db_col} = ?")
            params.append(val)
            
    if data.transcript is not None and data.transcript_raw is None:
        updates.append("transcript_raw = ?")
        params.append(data.transcript)
    if data.location is not None and data.district is None:
        updates.append("district = ?")
        params.append(data.location)
    if data.hearing_time is not None and data.scheduled_time is None:
        updates.append("scheduled_time = ?")
        params.append(data.hearing_time)

    # Workflow B: Hydration & Finalization
    if data.transcript_finalized and not row["transcript_finalized"]:
        now_str = _iso_now()
        updates.append("transcript_finalized_at = ?")
        params.append(now_str)
        updates.append("transcript_finalized_by = ?")
        params.append(user.get("id"))
        
        try:
            from weasyprint import HTML
            import os
            
            # Fetch child for template
            child = conn.execute("SELECT * FROM children WHERE id = ?", (row["child_id"],)).fetchone()
            
            # Simple keyword extraction to determine new status
            new_status = child["legal_status"]
            transcript_text = (data.transcript_edited or data.transcript_raw or row["transcript_edited"] or row["transcript_raw"] or "").lower()
            
            if "lfa" in transcript_text or "legally free" in transcript_text:
                new_status = "Legally Free for Adoption"
            elif "foster" in transcript_text:
                new_status = "Placed in Foster Care"
            elif "restore" in transcript_text:
                new_status = "Restored to Family"
            
            if new_status != child["legal_status"]:
                conn.execute("UPDATE children SET legal_status = ?, updated_at = ? WHERE id = ?", (new_status, now_str, row["child_id"]))
                conn.execute(
                    "INSERT INTO case_history (id, child_id, event_type, event_date, description, performed_by) VALUES (?,?,?,?,?,?)",
                    (str(uuid.uuid4()), row["child_id"], "STATUS_CHANGE", now_str, f"Status updated to {new_status} from transcript findings", user.get("id")),
                )
                
            # HTML Template for PDF
            html_content = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Helvetica, Arial, sans-serif; padding: 40px; }}
                    h1 {{ text-align: center; color: #2c3e50; }}
                    .meta {{ margin-bottom: 20px; border-bottom: 1px solid #ccc; padding-bottom: 10px; }}
                    .meta p {{ margin: 5px 0; }}
                    .transcript {{ margin-top: 20px; white-space: pre-wrap; }}
                    .footer {{ margin-top: 50px; font-size: 0.8em; color: #7f8c8d; text-align: center; }}
                </style>
            </head>
            <body>
                <h1>CWC Hearing Order</h1>
                <div class="meta">
                    <p><strong>Child Name:</strong> {child['name']}</p>
                    <p><strong>Child Code:</strong> {child['child_code']}</p>
                    <p><strong>Hearing Date:</strong> {data.hearing_date or row['hearing_date']}</p>
                    <p><strong>Attendees:</strong> {data.attendees or row['attendees']}</p>
                    <p><strong>New Status:</strong> {new_status}</p>
                </div>
                <div class="transcript">
                    <h3>Final Transcript & Findings</h3>
                    <p>{data.transcript_edited or data.transcript_raw or row["transcript_edited"] or row["transcript_raw"]}</p>
                </div>
                <div class="footer">
                    Generated by AI4Bharat BalKawach Platform at {now_str}
                </div>
            </body>
            </html>
            """
            
            orders_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "uploads", "orders")
            os.makedirs(orders_dir, exist_ok=True)
            
            order_id = str(uuid.uuid4())
            pdf_filename = f"order_{order_id}.pdf"
            pdf_path = os.path.join(orders_dir, pdf_filename)
            
            HTML(string=html_content).write_pdf(pdf_path)
            
            year = datetime.now().year
            count = conn.execute("SELECT COUNT(*) as cnt FROM orders").fetchone()["cnt"]
            order_number = f"ORD-HYD-{year}-{count + 1:04d}"
            
            conn.execute(
                "INSERT INTO orders (id, order_number, child_id, hearing_id, order_type, district, status, order_body, findings, created_by, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (order_id, order_number, row["child_id"], hearing_id, "other", data.district or row["district"], "approved", f"/api/audio/orders/{pdf_filename}", "Generated from finalized transcript.", user.get("full_name", "Unknown"), now_str)
            )
            
        except Exception as e:
            print(f"Failed to generate PDF order: {e}")

    if updates:
        updates.append("updated_at = ?")
        params.append(_iso_now())
        params.append(hearing_id)
        conn.execute(f"UPDATE hearings SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()

    audit(request, "UPDATE_HEARING", f"Hearing {hearing_id} updated", "hearing", hearing_id)
    updated = conn.execute(
        "SELECT h.*, c.name as child_name, c.child_code as child_code FROM hearings h LEFT JOIN children c ON h.child_id = c.id WHERE h.id = ?", 
        (hearing_id,)
    ).fetchone()
    return _row_to_dict(updated)


@router.post("/api/hearings/{hearing_id}/audio", response_model=HearingResponse)
def upload_hearing_audio(hearing_id: str, request: Request, audio: UploadFile = File(...), user: dict = Depends(require_roles(DATA_ENTRY_ROLES))):
    conn = get_db()
    row = conn.execute("SELECT * FROM hearings WHERE id = ?", (hearing_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Hearing not found")

    upload_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "uploads", "hearings")
    os.makedirs(upload_dir, exist_ok=True)

    filename = f"{hearing_id}.wav"
    filepath = os.path.join(upload_dir, filename)
    
    with open(filepath, "wb") as f:
        f.write(audio.file.read())

    audio_url = f"/uploads/hearings/{filename}"

    conn.execute(
        "UPDATE hearings SET audio_url = ?, updated_at = ? WHERE id = ?",
        (audio_url, _iso_now(), hearing_id),
    )
    conn.commit()
    audit(request, "UPLOAD_HEARING_AUDIO", f"Audio uploaded for hearing {hearing_id}", "hearing", hearing_id)

    updated = conn.execute("SELECT * FROM hearings WHERE id = ?", (hearing_id,)).fetchone()
    return _row_to_dict(updated)


# ════════════════════════════════════════════════════════════════════════
#  Orders
# ════════════════════════════════════════════════════════════════════════

@router.get("/api/orders", response_model=List[OrderResponse])
def list_orders(
    district: Optional[str] = None,
    status: Optional[str] = None,
    child_id: Optional[str] = None,
    user: dict = Depends(require_roles(DATA_READ_ROLES))
):
    conn = get_db()
    query = """
        SELECT o.*, c.name as child_name, c.child_code 
        FROM orders o
        LEFT JOIN children c ON o.child_id = c.id
        WHERE 1=1
    """
    params = []

    filters = {"o.district": district, "o.status": status, "o.child_id": child_id}
    for col, val in filters.items():
        if val is not None:
            query += f" AND {col} = ?"
            params.append(val)

    rows = conn.execute(query + " ORDER BY o.created_at DESC", params).fetchall()
    
    result = []
    for r in rows:
        rd = dict(r)
        rd["child"] = {"name": r["child_name"], "id": r["child_id"], "child_code": r["child_code"]}
        result.append(rd)
    return result


@router.get("/api/orders/{order_id}", response_model=OrderResponse)
def get_order(order_id: str, user: dict = Depends(require_roles(DATA_READ_ROLES))):
    conn = get_db()
    row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return _row_to_dict(row)


@router.post("/api/orders", response_model=OrderResponse, status_code=201)
def create_order(data: OrderCreateRequest, request: Request, user: dict = Depends(require_roles(DATA_ENTRY_ROLES))):
    conn = get_db()
    now = _iso_now()

    child_id = data.child_id
    
    district_name = data.district
    if child_id:
        child_row = conn.execute("SELECT district FROM children WHERE id = ?", (child_id,)).fetchone()
        if child_row and child_row["district"]:
            district_name = child_row["district"]
            
    dist_code = district_name[:3].upper() if district_name else "UNK"

    year = datetime.now().year
    count = conn.execute("SELECT COUNT(*) as cnt FROM orders WHERE order_number LIKE ?", (f"ORD-{dist_code}-{year}-%",)).fetchone()["cnt"]
    order_number = f"ORD-{dist_code}-{year}-{count + 1:04d}"
    order_id = str(uuid.uuid4())

    transcript = data.transcript

    if child_id and not transcript:
        latest_hearing = conn.execute(
            """SELECT transcript_raw FROM hearings
               WHERE child_id = ? AND transcript_raw != ''
               ORDER BY hearing_date DESC LIMIT 1""",
            (child_id,),
        ).fetchone()
        if latest_hearing:
            transcript = latest_hearing["transcript_raw"]

    hearing_id_val = data.hearing_id if data.hearing_id else None

    conn.execute(
        """INSERT INTO orders
           (id, order_number, child_id, hearing_id, order_type,
            district, status, order_body, findings, created_by,
            created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (
            order_id, order_number, child_id, hearing_id_val, data.order_type,
            district_name, "draft", data.order_body, data.findings,
            user.get("full_name", "Unknown"), now,
        ),
    )
    conn.commit()
    audit(request, "CREATE_ORDER", f"Order {order_number} created", "order", order_id)

    row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    return _row_to_dict(row)


@router.put("/api/orders/{order_id}/approve", response_model=OrderResponse)
def approve_order(order_id: str, request: Request, user: dict = Depends(require_roles(CHAIR_ROLES + ("system_admin",)))):
    conn = get_db()
    row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Order not found")

    now = _iso_now()
    conn.execute(
        """UPDATE orders SET status = 'approved', approved_by = ?,
           updated_at = ? WHERE id = ?""",
        (user.get("full_name", "Unknown"), now, order_id),
    )
    conn.commit()
    audit(request, "APPROVE_ORDER", f"Order {row['order_number']} approved by {user.get('full_name', 'Unknown')}", "order", order_id)

    updated = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    return _row_to_dict(updated)


@router.get("/api/orders/{order_id}/print", response_model=OrderResponse)
def print_order(order_id: str, user: dict = Depends(require_roles(DATA_READ_ROLES))):
    conn = get_db()
    order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    order_dict = _row_to_dict(order)

    if order_dict.get("child_id"):
        child = conn.execute("SELECT * FROM children WHERE id = ?", (order_dict["child_id"],)).fetchone()
        if child:
            order_dict["child"] = _row_to_dict(child)

    if not order_dict.get("approved_by"):
        chairperson = conn.execute(
            "SELECT full_name FROM users WHERE role = 'cwc_chairperson' AND district = ?",
            (order_dict.get("district"),)
        ).fetchone()
        if chairperson:
            order_dict["approved_by"] = chairperson["full_name"]

    order_dict["print_format"] = True
    order_dict["generated_at"] = _iso_now()
    return order_dict


@router.put("/api/orders/{order_id}", response_model=SuccessResponse)
def update_order(order_id: str, data: OrderUpdateRequest, request: Request, user: dict = Depends(require_roles(CHAIR_ROLES))):
    conn = get_db()
    conn.execute(
        "UPDATE orders SET order_body = ?, findings = ?, updated_at = ?, updated_by = ? WHERE id = ?",
        (data.order_body, data.findings, _iso_now(), user.get("full_name", "Unknown"), order_id)
    )
    conn.commit()
    audit(request, "UPDATE_ORDER", f"Updated order {order_id}", "order", order_id)
    return {"success": True}


@router.put("/api/orders/{order_id}/reject", response_model=SuccessResponse)
def reject_order(order_id: str, request: Request, user: dict = Depends(require_roles(CHAIR_ROLES))):
    conn = get_db()
    conn.execute(
        "UPDATE orders SET status = 'rejected', updated_at = ? WHERE id = ?",
        (_iso_now(), order_id)
    )
    conn.commit()
    audit(request, "REJECT_ORDER", f"Rejected order {order_id}", "order", order_id)
    return {"success": True}


# ════════════════════════════════════════════════════════════════════════
#  CCIs  (Child Care Institutions)
# ════════════════════════════════════════════════════════════════════════

@router.get("/api/ccis", response_model=List[CCIResponse])
def list_ccis(user: dict = Depends(require_roles(DATA_READ_ROLES))):
    conn = get_db()
    conn.execute('''
        UPDATE ccis 
        SET current_occupancy = (
            SELECT COUNT(*) FROM children WHERE children.cci_id = ccis.id
        )
    ''')
    conn.commit()
    rows = conn.execute("SELECT * FROM ccis ORDER BY name").fetchall()
    return _rows_to_list(rows)

@router.get("/api/ccis/{cci_id}/details")
def get_cci_details(cci_id: str, user: dict = Depends(require_roles(DATA_READ_ROLES))):
    conn = get_db()
    cci = conn.execute("SELECT * FROM ccis WHERE id = ?", (cci_id,)).fetchone()
    if not cci:
        raise HTTPException(status_code=404, detail="CCI not found")
        
    children_rows = conn.execute("SELECT id, name, gender, date_of_birth, estimated_age, legal_status FROM children WHERE cci_id = ?", (cci_id,)).fetchall()
    staff = conn.execute("SELECT id, full_name as name, role, email, phone FROM users WHERE cci_id = ?", (cci_id,)).fetchall()
    
    children = []
    for r in children_rows:
        rd = _row_to_dict(r)
        rd["age"] = compute_age(rd.get("date_of_birth"), rd.get("estimated_age"))
        children.append(rd)

    return {
        "cci": dict(cci),
        "children": children,
        "staff": _rows_to_list(staff)
    }


@router.get("/api/ccis/{cci_id}", response_model=CCIResponse)
def get_cci(cci_id: str, user: dict = Depends(require_roles(DATA_READ_ROLES))):
    conn = get_db()
    cci = conn.execute("SELECT * FROM ccis WHERE id = ?", (cci_id,)).fetchone()
    if cci is None:
        raise HTTPException(status_code=404, detail="CCI not found")

    result = _row_to_dict(cci)

    children_count = conn.execute("SELECT COUNT(*) as cnt FROM children WHERE cci_id = ?", (cci_id,)).fetchone()["cnt"]
    result["children_count"] = children_count
    result["occupancy_pct"] = round(children_count / result["capacity"] * 100, 1) if result.get("capacity") and result["capacity"] > 0 else 0

    visits = conn.execute("SELECT * FROM cci_visits WHERE cci_id = ? ORDER BY visit_date DESC", (cci_id,)).fetchall()
    result["inspections"] = _rows_to_list(visits)

    return result


@router.post("/api/ccis", response_model=CCIResponse, status_code=201)
def create_cci(data: CCICreateRequest, request: Request, user: dict = Depends(require_roles(ADMIN_ROLES + DCPU_ROLES))):
    conn = get_db()
    cci_id = str(uuid.uuid4())
    
    conn.execute(
        """INSERT INTO ccis (id, name, district, capacity, contact_person, contact_phone, staffing_details)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (cci_id, data.name, data.district, data.capacity, data.contact_person, data.contact_phone, data.staffing_details)
    )
    conn.commit()
    audit(request, "CREATE_CCI", f"CCI {data.name} registered", "cci", cci_id)
    row = conn.execute("SELECT * FROM ccis WHERE id = ?", (cci_id,)).fetchone()
    return _row_to_dict(row)


@router.put("/api/ccis/{cci_id}", response_model=CCIResponse)
def update_cci(cci_id: str, data: CCIUpdateRequest, request: Request, user: dict = Depends(require_roles(ADMIN_ROLES + DCPU_ROLES))):
    conn = get_db()
    
    updates = []
    params = []
    fields = {
        "name": data.name, "district": data.district,
        "capacity": data.capacity, "contact_person": data.contact_person,
        "contact_phone": data.contact_phone, "staffing_details": data.staffing_details
    }
    
    for col, val in fields.items():
        if val is not None:
            updates.append(f"{col} = ?")
            params.append(val)
            
    if updates:
        params.append(cci_id)
        conn.execute(f"UPDATE ccis SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()
        
    audit(request, "UPDATE_CCI", f"CCI {cci_id} updated", "cci", cci_id)
    row = conn.execute("SELECT * FROM ccis WHERE id = ?", (cci_id,)).fetchone()
    return _row_to_dict(row)


@router.delete("/api/ccis/{cci_id}", response_model=SuccessResponse)
def delete_cci(cci_id: str, request: Request, user: dict = Depends(require_roles(ADMIN_ROLES))):
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) as cnt FROM children WHERE cci_id = ?", (cci_id,)).fetchone()["cnt"]
    if count > 0:
        raise HTTPException(status_code=400, detail=f"Cannot delete CCI with {count} children assigned")
        
    conn.execute("DELETE FROM ccis WHERE id = ?", (cci_id,))
    conn.commit()
    audit(request, "DELETE_CCI", f"CCI {cci_id} deleted", "cci", cci_id)
    return {"success": True}

# ════════════════════════════════════════════════════════════════════════
#  Family Visits
# ════════════════════════════════════════════════════════════════════════

@router.get("/api/children/{child_id}/visits", response_model=List[FamilyVisitResponse])
def list_family_visits(child_id: str, user: dict = Depends(require_roles(DATA_READ_ROLES))):
    conn = get_db()
    rows = conn.execute("SELECT * FROM family_visits WHERE child_id = ? ORDER BY visit_date DESC", (child_id,)).fetchall()
    return _rows_to_list(rows)


@router.post("/api/children/{child_id}/visits", response_model=FamilyVisitResponse, status_code=201)
def log_family_visit(child_id: str, data: FamilyVisitRequest, request: Request, user: dict = Depends(require_roles(DATA_ENTRY_ROLES))):
    conn = get_db()
    visit_id = str(uuid.uuid4())
    now = _iso_now()

    conn.execute(
        """INSERT INTO family_visits
           (id, child_id, visit_date, visitor_name, relationship,
            duration_minutes, notes, logged_by, created_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (visit_id, child_id, data.visit_date or now[:10], data.visitor_name,
         data.relationship, data.duration_minutes, data.notes,
         user.get("full_name", "Unknown"), now),
    )
    conn.commit()
    audit(request, "LOG_FAMILY_VISIT", f"Family visit logged for child {child_id}", "family_visit", visit_id)

    row = conn.execute("SELECT * FROM family_visits WHERE id = ?", (visit_id,)).fetchone()
    return _row_to_dict(row)


# ════════════════════════════════════════════════════════════════════════
#  CCI Inspections
# ════════════════════════════════════════════════════════════════════════

@router.get("/api/ccis/{cci_id}/inspections")
def list_inspections(cci_id: str, user: dict = Depends(require_roles(DATA_READ_ROLES))):
    conn = get_db()
    rows = conn.execute("""
        SELECT v.*, u.full_name as officer_name, u.district as officer_district
        FROM cci_visits v 
        LEFT JOIN users u ON v.officer_id = u.id 
        WHERE v.cci_id = ? 
        ORDER BY v.visit_date DESC
    """, (cci_id,)).fetchall()
    return _rows_to_list(rows)


@router.post("/api/ccis/{cci_id}/inspections", response_model=CCIVisitResponse, status_code=201)
def log_inspection(cci_id: str, data: CCIVisitRequest, request: Request, user: dict = Depends(require_roles(DATA_ENTRY_ROLES))):
    conn = get_db()
    inspection_id = str(uuid.uuid4())
    now = _iso_now()

    conn.execute(
        """INSERT INTO cci_visits
           (id, cci_id, visit_date, officer_id, findings, recommendations, created_at)
           VALUES (?,?,?,?,?,?,?)""",
        (inspection_id, cci_id, data.visit_date or now[:10], user.get("id"),
         data.findings, data.recommendations, now),
    )
    conn.commit()
    audit(request, "LOG_INSPECTION", f"Inspection logged for CCI {cci_id}", "cci_inspection", inspection_id)

    row = conn.execute("SELECT * FROM cci_visits WHERE id = ?", (inspection_id,)).fetchone()
    return _row_to_dict(row)


# ════════════════════════════════════════════════════════════════════════
#  Dashboard & Alerts
# ════════════════════════════════════════════════════════════════════════

def get_dashboard_filter(user: dict, child_table_alias: str = ""):
    prefix = f"{child_table_alias}." if child_table_alias else ""
    if user["role"] in ["system_admin", "wcd_official"]:
        return "1=1", []
    
    if user["role"] in ["cwc_member", "cwc_chairperson", "dcpu_officer"] and user.get("district"):
        return f"{prefix}district = ?", [user["district"]]
    elif user.get("cci_id"):
        return f"{prefix}cci_id = ?", [user["cci_id"]]
        
    return "1=0", []

@router.get("/api/dashboard/stats", response_model=DashboardStatsResponse)
def dashboard_stats(user: dict = Depends(require_roles(DATA_READ_ROLES))):
    conn = get_db()
    now = datetime.now()
    six_months_ago = (now - timedelta(days=180)).strftime("%Y-%m-%d")

    where_clause, params = get_dashboard_filter(user, "")
    where_clause_c, params_c = get_dashboard_filter(user, "c")

    total_children = conn.execute(f"SELECT COUNT(*) as cnt FROM children WHERE {where_clause}", params).fetchone()["cnt"]

    status_rows = conn.execute(f"SELECT legal_status, COUNT(*) as cnt FROM children WHERE {where_clause} GROUP BY legal_status", params).fetchall()
    by_status = {r["legal_status"]: r["cnt"] for r in status_rows}

    cat_rows = conn.execute(f"SELECT admission_category, COUNT(*) as cnt FROM children WHERE {where_clause} GROUP BY admission_category", params).fetchall()
    by_category = {r["admission_category"]: r["cnt"] for r in cat_rows}

    if user["role"] == "system_admin":
        total_ccis = conn.execute("SELECT COUNT(*) as cnt FROM ccis").fetchone()["cnt"]
    elif user["role"] in ["cwc_member", "cwc_chairperson", "dcpu_officer"] and user.get("district"):
        total_ccis = conn.execute("SELECT COUNT(*) as cnt FROM ccis WHERE district = ?", (user["district"],)).fetchone()["cnt"]
    elif user.get("cci_id"):
        total_ccis = conn.execute("SELECT COUNT(*) as cnt FROM ccis WHERE id = ?", (user["cci_id"],)).fetchone()["cnt"]
    else:
        total_ccis = 0

    total_hearings = conn.execute(f"SELECT COUNT(*) as cnt FROM hearings h JOIN children c ON h.child_id = c.id WHERE {where_clause_c}", params_c).fetchone()["cnt"]
    total_orders = conn.execute(f"SELECT COUNT(*) as cnt FROM orders o JOIN children c ON o.child_id = c.id WHERE {where_clause_c}", params_c).fetchone()["cnt"]

    today = now.strftime("%Y-%m-%d")
    seven_days = (now + timedelta(days=7)).strftime("%Y-%m-%d")

    overdue = conn.execute(f"SELECT COUNT(*) as cnt FROM deadlines d JOIN children c ON d.child_id = c.id WHERE d.status = 'pending' AND d.due_date < ? AND {where_clause_c}", (today, *params_c)).fetchone()["cnt"]
    approaching = conn.execute(f"SELECT COUNT(*) as cnt FROM deadlines d JOIN children c ON d.child_id = c.id WHERE d.status = 'pending' AND d.due_date >= ? AND d.due_date <= ? AND {where_clause_c}", (today, seven_days, *params_c)).fetchone()["cnt"]
    ageout = conn.execute(f"SELECT COUNT(*) as cnt FROM children WHERE estimated_age >= 17 AND {where_clause}", params).fetchone()["cnt"]

    no_contact_args = [six_months_ago] + params_c
    no_contact = conn.execute(
        f"""SELECT COUNT(*) as cnt FROM children c
           WHERE NOT EXISTS (
               SELECT 1 FROM family_visits fv
               WHERE fv.child_id = c.id AND fv.visit_date >= ?
           ) AND {where_clause_c}""",
        no_contact_args,
    ).fetchone()["cnt"]

    lfa = conn.execute(f"SELECT COUNT(*) as cnt FROM children WHERE is_lfa_eligible = 1 AND {where_clause}", params).fetchone()["cnt"]

    return {
        "total_children": total_children,
        "by_status": by_status,
        "by_category": by_category,
        "total_ccis": total_ccis,
        "total_hearings": total_hearings,
        "total_orders": total_orders,
        "overdue_deadlines": overdue,
        "approaching_deadlines": approaching,
        "children_approaching_ageout": ageout,
        "children_no_family_contact": no_contact,
        "lfa_eligible_count": lfa,
    }

@router.get("/api/dashboard/deadlines", response_model=List[DeadlineResponse])
def dashboard_deadlines(user: dict = Depends(require_roles(DATA_READ_ROLES))):
    conn = get_db()
    where_clause_c, params_c = get_dashboard_filter(user, "c")
    query = f"""
        SELECT d.*, c.name as child_name, c.child_code 
        FROM deadlines d 
        JOIN children c ON d.child_id = c.id
        WHERE {where_clause_c}
        ORDER BY d.due_date ASC
    """
    rows = conn.execute(query, params_c).fetchall()

    now = datetime.now()
    seven_days = now + timedelta(days=7)
    result = []

    for r in rows:
        d = _row_to_dict(r)
        try:
            due = _parse_due_date(d["due_date"])
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

    return result


@router.get("/api/dashboard/alerts", response_model=List[AlertResponse])
def dashboard_alerts(user: dict = Depends(require_roles(DATA_READ_ROLES))):
    conn = get_db()
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    six_months_ago = (now - timedelta(days=180)).strftime("%Y-%m-%d")
    alerts = []

    where_clause, params = get_dashboard_filter(user, "")
    where_clause_c, params_c = get_dashboard_filter(user, "c")

    ageout_children = conn.execute(f"SELECT id, child_code, name, date_of_birth, estimated_age FROM children WHERE {where_clause}", params).fetchall()
    for c in ageout_children:
        age = compute_age(c["date_of_birth"], c["estimated_age"])
        if age and age >= 17:
            time_metric = None
            if c["date_of_birth"]:
                try:
                    dob = datetime.strptime(c["date_of_birth"], "%Y-%m-%d")
                    # Handle leap year birthday when adding 18 years
                    turn_18 = dob.replace(year=dob.year + 18) if not (dob.month == 2 and dob.day == 29) else dob.replace(year=dob.year + 18, day=28)
                    days = (turn_18 - now).days
                    if days > 0:
                        time_metric = f"{days} Days Until 18"
                    elif days < 0:
                        time_metric = f"{abs(days)} Days Past 18"
                    else:
                        time_metric = "Turns 18 Today"
                except Exception:
                    pass
            
            # Severity logic for AGE_OUT: red if < 30 days, else medium
            sev = "high" if days and days < 30 else "medium"
            
            alerts.append({
                "type": "AGE_OUT", "severity": sev, "child_id": c["id"],
                "child_code": c["child_code"], "message": f"{c['name']} (age {age}) is approaching age-out",
                "time_metric": time_metric,
                "days_diff": abs(days) if days is not None else 999,
                "title": f"Age Out Alert For {c['name']}",
                "subtitle": f"Due on {turn_18.strftime('%m/%d/%Y')}" if time_metric and c["date_of_birth"] else f"Estimated Age: {age}"
            })

    lfa_children = conn.execute(f"SELECT id, child_code, name FROM children WHERE is_lfa_eligible = 1 AND {where_clause}", params).fetchall()
    for c in lfa_children:
        alerts.append({
            "type": "LFA_ELIGIBLE", "severity": "medium", "child_id": c["id"],
            "child_code": c["child_code"], "message": f"{c['name']} is eligible for Legal Free for Adoption",
            "days_diff": 0,
            "title": f"LFA Eligible For {c['name']}",
            "subtitle": "Child is eligible for Legal Free for Adoption"
        })

    no_contact_args = [six_months_ago] + params_c
    no_contact = conn.execute(
        f"""SELECT c.id, c.child_code, c.name,
               (SELECT MAX(visit_date) FROM family_visits WHERE child_id = c.id) as last_contact
           FROM children c
           WHERE NOT EXISTS (
               SELECT 1 FROM family_visits fv
               WHERE fv.child_id = c.id AND fv.visit_date >= ?
           ) AND {where_clause_c}""",
        no_contact_args,
    ).fetchall()
    for c in no_contact:
        time_metric = "No Contact Recorded"
        if c["last_contact"]:
            try:
                last_contact = datetime.strptime(c["last_contact"], "%Y-%m-%d")
                days = (now - last_contact).days
                time_metric = f"{days} Days Since Contact"
            except Exception:
                pass
                
        alerts.append({
            "type": "NO_FAMILY_CONTACT", "severity": "medium", "child_id": c["id"],
            "child_code": c["child_code"], "message": f"{c['name']} has had no family contact for 6+ months",
            "time_metric": time_metric,
            "days_diff": abs(days) if c["last_contact"] and 'days' in locals() else 999,
            "title": f"No Family Contact For {c['name']}",
            "subtitle": f"Last Contact: {c['last_contact']}" if c["last_contact"] else "Never visited"
        })

    overdue_args = [today] + params_c
    overdue = conn.execute(
        f"""SELECT d.*, c.child_code, c.name as child_name
           FROM deadlines d
           JOIN children c ON d.child_id = c.id
           WHERE d.status = 'pending' AND d.due_date < ? AND {where_clause_c}""",
        overdue_args,
    ).fetchall()
    for d in overdue:
        due_date = _parse_due_date(d["due_date"])
        days = (due_date - now).days
        time_metric = f"{abs(days)} Days Overdue" if days < 0 else "Due Today"
        alerts.append({
            "type": "OVERDUE_DEADLINE", "severity": "high", "child_id": d["child_id"],
            "child_code": d["child_code"] or "",
            "message": f"Overdue: {d['notes']} for {d['child_name'] or 'unknown'} (due {d['due_date']})",
            "time_metric": time_metric,
            "days_diff": abs(days),
            "title": f"{d['notes']} For {d['child_name'] or 'Child'}",
            "subtitle": f"Due on {due_date.strftime('%m/%d/%Y')}"
        })

    upcoming_args = [today, (now + timedelta(days=7)).strftime("%Y-%m-%d")] + params_c
    upcoming = conn.execute(
        f"""SELECT d.*, c.child_code, c.name as child_name
           FROM deadlines d
           JOIN children c ON d.child_id = c.id
           WHERE d.status = 'pending' AND d.due_date >= ? AND d.due_date <= ? AND {where_clause_c}""",
        upcoming_args,
    ).fetchall()
    for d in upcoming:
        due_date = _parse_due_date(d["due_date"])
        days = (due_date - now).days
        time_metric = f"{days} Days Left" if days > 0 else "Due Today"
        alerts.append({
            "type": "UPCOMING_DEADLINE", "severity": "medium", "child_id": d["child_id"],
            "child_code": d["child_code"] or "",
            "message": f"Due Soon: {d['notes']} for {d['child_name'] or 'unknown'} (due {d['due_date']})",
            "time_metric": time_metric,
            "days_diff": abs(days),
            "title": f"{d['notes']} For {d['child_name'] or 'Child'}",
            "subtitle": f"Due on {due_date.strftime('%m/%d/%Y')}"
        })

    return alerts

# ════════════════════════════════════════════════════════════════════════
#  Reports
# ════════════════════════════════════════════════════════════════════════

@router.get("/api/reports/monthly", response_model=MonthlyReportResponse)
def monthly_report(month: Optional[int] = None, year: Optional[int] = None, user: dict = Depends(require_roles(DATA_READ_ROLES))):
    if month is None: month = datetime.now().month
    if year is None: year = datetime.now().year

    start = f"{year}-{month:02d}-01"
    if month == 12:
        end = f"{year + 1}-01-01"
    else:
        end = f"{year}-{month + 1:02d}-01"

    conn = get_db()
    admissions = conn.execute("SELECT COUNT(*) as cnt FROM children WHERE admission_date >= ? AND admission_date < ?", (start, end)).fetchone()["cnt"]
    hearings = conn.execute("SELECT COUNT(*) as cnt FROM hearings WHERE hearing_date >= ? AND hearing_date < ?", (start, end)).fetchone()["cnt"]
    orders = conn.execute("SELECT COUNT(*) as cnt FROM orders WHERE created_at >= ? AND created_at < ?", (start, end)).fetchone()["cnt"]

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

    return {
        "month": month, "year": year, "admissions": admissions,
        "hearings_held": hearings, "orders_issued": orders,
        "restorations": restorations, "adoptions": adoptions,
    }


@router.get("/api/reports/quarterly", response_model=QuarterlyReportResponse)
def quarterly_report(quarter: Optional[int] = 1, year: Optional[int] = None, user: dict = Depends(require_roles(DATA_READ_ROLES))):
    if year is None: year = datetime.now().year

    quarter_starts = {1: 1, 2: 4, 3: 7, 4: 10}
    start_month = quarter_starts.get(quarter, 1)
    end_month = start_month + 3

    start = f"{year}-{start_month:02d}-01"
    if end_month > 12:
        end = f"{year + 1}-01-01"
    else:
        end = f"{year}-{end_month:02d}-01"

    conn = get_db()
    total_children = conn.execute("SELECT COUNT(*) as cnt FROM children").fetchone()["cnt"]
    new_admissions = conn.execute("SELECT COUNT(*) as cnt FROM children WHERE admission_date >= ? AND admission_date < ?", (start, end)).fetchone()["cnt"]
    hearings = conn.execute("SELECT COUNT(*) as cnt FROM hearings WHERE hearing_date >= ? AND hearing_date < ?", (start, end)).fetchone()["cnt"]
    orders = conn.execute("SELECT COUNT(*) as cnt FROM orders WHERE created_at >= ? AND created_at < ?", (start, end)).fetchone()["cnt"]

    status_rows = conn.execute("SELECT legal_status, COUNT(*) as cnt FROM children GROUP BY legal_status").fetchall()
    by_status = {r["legal_status"]: r["cnt"] for r in status_rows}

    ccis = conn.execute("SELECT * FROM ccis").fetchall()
    cci_summary = []
    for cci in ccis:
        count = conn.execute("SELECT COUNT(*) as cnt FROM children WHERE cci_id = ?", (cci["id"],)).fetchone()["cnt"]
        cci_summary.append({
            "name": cci["name"], "capacity": cci["capacity"], "current": count,
            "occupancy": round(count / cci["capacity"] * 100, 1) if cci["capacity"] and cci["capacity"] > 0 else 0,
        })

    return {
        "quarter": quarter, "year": year, "total_children": total_children,
        "new_admissions": new_admissions, "hearings_held": hearings,
        "orders_issued": orders, "by_status": by_status, "cci_occupancy": cci_summary,
    }

# ════════════════════════════════════════════════════════════════════════
#  Async Reports (PDF Generation Simulation)
# ════════════════════════════════════════════════════════════════════════
import time

def generate_pdf_report(report_id: str, report_type: str):
    """Generate a real PDF using reportlab"""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        import os
        
        # Ensure directory exists
        os.makedirs("downloads/reports", exist_ok=True)
        file_path = f"downloads/reports/{report_type}_{report_id[:8]}.pdf"
        
        c = canvas.Canvas(file_path, pagesize=letter)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, 750, f"BalKawach {report_type.capitalize()} Report")
        
        c.setFont("Helvetica", 12)
        c.drawString(50, 710, f"Report ID: {report_id}")
        c.drawString(50, 690, f"Generated At: {_iso_now()}")
        
        c.drawString(50, 650, "This is an automatically generated system report.")
        c.drawString(50, 630, "System metrics and indicators are attached.")
        
        # Mock some data based on DB
        db = get_db()
        count = db.execute("SELECT COUNT(*) as c FROM children").fetchone()["c"]
        c.drawString(50, 590, f"Total Children Registered: {count}")
        
        c.save()
        
        db.execute("UPDATE reports SET status = 'completed', file_path = ?, completed_at = ? WHERE id = ?", (file_path, _iso_now(), report_id))
        db.commit()
    except Exception as e:
        db = get_db()
        db.execute("UPDATE reports SET status = 'failed', error_message = ?, completed_at = ? WHERE id = ?", (str(e), _iso_now(), report_id))
        db.commit()

@router.post("/api/reports/async")
def request_async_report(
    background_tasks: BackgroundTasks,
    request: Request,
    report_type: str = "monthly",
    user=Depends(require_roles(["dcpu_officer", "wcd_official", "system_admin"]))
):
    db = get_db()
    report_id = str(uuid.uuid4())
    
    db.execute("""
        INSERT INTO reports (id, type, status, requested_by)
        VALUES (?, ?, 'processing', ?)
    """, (report_id, report_type, user["id"]))
    db.commit()
    
    background_tasks.add_task(generate_pdf_report, report_id, report_type)
    
    return {"message": "Report generation started", "report_id": report_id, "status": "processing"}


@router.get("/api/reports/download/{report_id}")
def download_report(report_id: str):
    db = get_db()
    report = db.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
    if not report or not report["file_path"]:
        raise HTTPException(status_code=404, detail="Report not found or not completed")
    
    file_path = report["file_path"]
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Report file missing on server")
        
    return FileResponse(file_path, filename=f"Report_{report_id[:8]}.pdf", media_type="application/pdf")

@router.get("/api/reports/async")
def get_async_reports(
    user=Depends(require_roles(["dcpu_officer", "wcd_official", "system_admin"]))
):
    db = get_db()
    rows = db.execute("SELECT * FROM reports WHERE requested_by = ? ORDER BY requested_at DESC LIMIT 20", (user["id"],)).fetchall()
    return _rows_to_list(rows)


# ════════════════════════════════════════════════════════════════════════
#  Audit Log & Miscellaneous
# ════════════════════════════════════════════════════════════════════════

@router.get("/api/audit", response_model=List[AuditLogResponse])
def audit_log(limit: int = 200, user: dict = Depends(require_roles(DATA_READ_ROLES))):
    conn = get_db()
    rows = conn.execute("""
        SELECT a.*, u.username as user_name 
        FROM audit_logs a 
        LEFT JOIN users u ON a.user_id = u.id 
        ORDER BY a.created_at DESC 
        LIMIT ?
    """, (limit,)).fetchall()
    return _rows_to_list(rows)


@router.get("/api/notifications", response_model=List[NotificationResponse])
def get_notifications(user: dict = Depends(require_roles(DATA_READ_ROLES))):
    conn = get_db()
    rows = conn.execute("SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC LIMIT 100", (user["id"],)).fetchall()
    return _rows_to_list(rows)


@router.put("/api/notifications/{notif_id}/read", response_model=SuccessResponse)
def mark_notification_read(notif_id: str, user: dict = Depends(require_roles(DATA_READ_ROLES))):
    conn = get_db()
    conn.execute("UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?", (notif_id, user["id"]))
    conn.commit()
    return {"success": True}


@router.put("/api/deadlines/{deadline_id}/complete", response_model=SuccessResponse)
def complete_deadline(deadline_id: str, request: Request, user: dict = Depends(require_roles(DATA_ENTRY_ROLES))):
    conn = get_db()
    conn.execute("UPDATE deadlines SET status = 'completed', completed_at = ? WHERE id = ?", (_iso_now(), deadline_id))
    conn.commit()
    audit(request, "COMPLETE_DEADLINE", f"Completed deadline {deadline_id}", "deadline", deadline_id)
    return {"success": True}


@router.put("/api/deadlines/{deadline_id}/escalate", response_model=SuccessResponse)
def escalate_deadline(deadline_id: str, request: Request, user: dict = Depends(require_roles(DATA_ENTRY_ROLES))):
    conn = get_db()
    conn.execute("UPDATE deadlines SET status = 'escalated', escalated_at = ?, escalated_to = ? WHERE id = ?", (_iso_now(), "system_admin", deadline_id))
    conn.commit()
    audit(request, "ESCALATE_DEADLINE", f"Escalated deadline {deadline_id}", "deadline", deadline_id)
    return {"success": True}

@router.get("/api/reports")
def get_reports(user: dict = Depends(require_roles(["system_admin", "dcpu_officer", "wcd_official", "cwc_chairperson"]))):
    conn = get_db()
    # Basic statistics for the reports page
    total_children = conn.execute("SELECT COUNT(*) as cnt FROM children").fetchone()["cnt"]
    total_ccis = conn.execute("SELECT COUNT(*) as cnt FROM ccis").fetchone()["cnt"]
    total_hearings = conn.execute("SELECT COUNT(*) as cnt FROM hearings").fetchone()["cnt"]
    
    status_distribution = conn.execute("SELECT legal_status, COUNT(*) as cnt FROM children GROUP BY legal_status").fetchall()
    
    return {
        "total_children": total_children,
        "total_ccis": total_ccis,
        "total_hearings": total_hearings,
        "status_distribution": {row["legal_status"]: row["cnt"] for row in status_distribution}
    }
