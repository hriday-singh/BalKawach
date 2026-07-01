"""
db.py — SQLite Database Layer for Child Protection Case Management Platform
=============================================================================
Used by Child Welfare Committees (CWCs) and District Child Protection Units
(DCPUs) in India. Fully self-contained: import and call init_db() to create
and seed everything.

Tables (10):
  users, ccis, children, case_history (immutable), hearings, orders,
  family_visits, cci_visits, deadlines, audit_logs (immutable)

Usage:
    from db import init_db, get_db
    init_db()
    conn = get_db()
"""

import sqlite3
import uuid
import json
import os
from datetime import datetime, timedelta, timezone

from werkzeug.security import generate_password_hash

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cpms.db")


def _uuid() -> str:
    """Generate a new UUID4 string."""
    return str(uuid.uuid4())


def _iso_now() -> str:
    """Current UTC timestamp in ISO 8601."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _iso_date(dt: datetime) -> str:
    """Format a datetime as an ISO 8601 date string."""
    return dt.strftime("%Y-%m-%d")


def _iso_datetime(dt: datetime) -> str:
    """Format a datetime as an ISO 8601 datetime string."""
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Connection helper
# ---------------------------------------------------------------------------

def get_db() -> sqlite3.Connection:
    """
    Return a new SQLite connection with:
      - foreign keys enforced
      - row_factory = sqlite3.Row (dict-like access)
    """
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# Schema creation
# ---------------------------------------------------------------------------

_SCHEMA_SQL = """
-- ==========================================================================
-- 1. users — User accounts
-- ==========================================================================
CREATE TABLE IF NOT EXISTS users (
    id              TEXT PRIMARY KEY,
    username        TEXT UNIQUE NOT NULL,
    password_hash   TEXT NOT NULL,
    full_name       TEXT NOT NULL,
    role            TEXT NOT NULL CHECK(role IN (
                        'cci_staff','cwc_member','cwc_chairperson',
                        'dcpu_officer','wcd_official','system_admin')),
    district        TEXT NOT NULL,
    cci_id          TEXT,
    email           TEXT,
    phone           TEXT,
    is_active       INTEGER DEFAULT 1,
    created_at      TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (cci_id) REFERENCES ccis(id)
);

-- ==========================================================================
-- 2. ccis — Child Care Institutions
-- ==========================================================================
CREATE TABLE IF NOT EXISTS ccis (
    id                  TEXT PRIMARY KEY,
    name                TEXT NOT NULL,
    district            TEXT NOT NULL,
    state               TEXT NOT NULL DEFAULT 'Telangana',
    address             TEXT,
    capacity            INTEGER NOT NULL,
    current_occupancy   INTEGER DEFAULT 0,
    contact_person      TEXT,
    contact_phone       TEXT,
    last_inspection_date TEXT,
    created_at          TEXT DEFAULT (datetime('now'))
);

-- ==========================================================================
-- 3. children — Child profiles
-- ==========================================================================
CREATE TABLE IF NOT EXISTS children (
    id                  TEXT PRIMARY KEY,
    child_code          TEXT UNIQUE NOT NULL,
    name                TEXT NOT NULL,
    date_of_birth       TEXT,
    estimated_age       INTEGER,
    gender              TEXT CHECK(gender IN ('Male','Female','Other')),
    admission_date      TEXT NOT NULL,
    admission_category  TEXT NOT NULL CHECK(admission_category IN (
                            'abandoned','surrendered','orphaned',
                            'guardian_surrendered','police_brought',
                            'runaway','other')),
    physical_description TEXT,
    cci_id              TEXT NOT NULL,
    district            TEXT NOT NULL,
    legal_status        TEXT NOT NULL DEFAULT 'Under Inquiry' CHECK(legal_status IN (
                            'Under Inquiry',
                            'Legally Free for Adoption',
                            'In Adoption Pool',
                            'Restored to Family',
                            'Placed in Foster Care',
                            'Placed in Sponsorship',
                            'Aged Out',
                            'Under Review')),
    is_lfa_eligible     INTEGER DEFAULT 0,
    lfa_flag_reason     TEXT,
    created_at          TEXT DEFAULT (datetime('now')),
    updated_at          TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (cci_id) REFERENCES ccis(id)
);

-- ==========================================================================
-- 4. case_history — Immutable event log (INSERT only)
-- ==========================================================================
CREATE TABLE IF NOT EXISTS case_history (
    id              TEXT PRIMARY KEY,
    child_id        TEXT NOT NULL,
    event_type      TEXT NOT NULL,
    event_date      TEXT NOT NULL,
    description     TEXT NOT NULL,
    performed_by    TEXT NOT NULL,
    metadata        TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (child_id) REFERENCES children(id)
);

-- Prevent UPDATE on case_history
CREATE TRIGGER IF NOT EXISTS trg_case_history_no_update
BEFORE UPDATE ON case_history
BEGIN
    SELECT RAISE(ABORT, 'case_history is immutable — UPDATE not allowed');
END;

-- Prevent DELETE on case_history
CREATE TRIGGER IF NOT EXISTS trg_case_history_no_delete
BEFORE DELETE ON case_history
BEGIN
    SELECT RAISE(ABORT, 'case_history is immutable — DELETE not allowed');
END;

-- ==========================================================================
-- 5. hearings — CWC hearing / sitting records
-- ==========================================================================
CREATE TABLE IF NOT EXISTS hearings (
    id                  TEXT PRIMARY KEY,
    child_id            TEXT NOT NULL,
    hearing_date        TEXT NOT NULL,
    scheduled_time      TEXT,
    status              TEXT DEFAULT 'scheduled' CHECK(status IN (
                            'scheduled','in_progress','completed',
                            'rescheduled','cancelled')),
    reschedule_reason   TEXT,
    attendees           TEXT,
    transcript_raw      TEXT,
    transcript_edited   TEXT,
    transcript_language TEXT DEFAULT 'hi',
    notes               TEXT,
    created_by          TEXT NOT NULL,
    district            TEXT NOT NULL,
    created_at          TEXT DEFAULT (datetime('now')),
    updated_at          TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (child_id) REFERENCES children(id)
);

-- ==========================================================================
-- 6. orders — CWC orders
-- ==========================================================================
CREATE TABLE IF NOT EXISTS orders (
    id              TEXT PRIMARY KEY,
    order_number    TEXT UNIQUE NOT NULL,
    child_id        TEXT NOT NULL,
    hearing_id      TEXT,
    order_type      TEXT NOT NULL CHECK(order_type IN (
                        'placement','inquiry_extension','restoration',
                        'lfa_declaration','foster_care','repatriation','other')),
    order_body      TEXT NOT NULL,
    findings        TEXT,
    status          TEXT DEFAULT 'draft' CHECK(status IN (
                        'draft','pending_approval','approved','rejected')),
    approved_by     TEXT,
    approved_at     TEXT,
    created_by      TEXT NOT NULL,
    district        TEXT NOT NULL,
    created_at      TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (child_id) REFERENCES children(id),
    FOREIGN KEY (hearing_id) REFERENCES hearings(id)
);

-- ==========================================================================
-- 7. family_visits — Family / guardian contact log
-- ==========================================================================
CREATE TABLE IF NOT EXISTS family_visits (
    id              TEXT PRIMARY KEY,
    child_id        TEXT NOT NULL,
    visit_date      TEXT NOT NULL,
    visitor_name    TEXT NOT NULL,
    relationship    TEXT NOT NULL,
    duration_minutes INTEGER,
    notes           TEXT,
    logged_by       TEXT NOT NULL,
    created_at      TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (child_id) REFERENCES children(id)
);

-- ==========================================================================
-- 8. cci_visits — DCPU inspection visits to CCIs
-- ==========================================================================
CREATE TABLE IF NOT EXISTS cci_visits (
    id              TEXT PRIMARY KEY,
    cci_id          TEXT NOT NULL,
    visit_date      TEXT NOT NULL,
    officer_id      TEXT NOT NULL,
    findings        TEXT,
    recommendations TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (cci_id) REFERENCES ccis(id),
    FOREIGN KEY (officer_id) REFERENCES users(id)
);

-- ==========================================================================
-- 9. deadlines — Statutory deadline tracking
-- ==========================================================================
CREATE TABLE IF NOT EXISTS deadlines (
    id              TEXT PRIMARY KEY,
    child_id        TEXT NOT NULL,
    deadline_type   TEXT NOT NULL,
    due_date        TEXT NOT NULL,
    status          TEXT DEFAULT 'pending' CHECK(status IN (
                        'pending','completed','overdue','escalated')),
    assigned_to     TEXT,
    completed_at    TEXT,
    notes           TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (child_id) REFERENCES children(id)
);

-- ==========================================================================
-- 10. audit_logs — Immutable system audit trail (INSERT only)
-- ==========================================================================
CREATE TABLE IF NOT EXISTS audit_logs (
    id              TEXT PRIMARY KEY,
    user_id         TEXT,
    action          TEXT NOT NULL,
    entity_type     TEXT,
    entity_id       TEXT,
    details         TEXT,
    ip_address      TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);

-- Prevent UPDATE on audit_logs
CREATE TRIGGER IF NOT EXISTS trg_audit_logs_no_update
BEFORE UPDATE ON audit_logs
BEGIN
    SELECT RAISE(ABORT, 'audit_logs is immutable — UPDATE not allowed');
END;

-- Prevent DELETE on audit_logs
CREATE TRIGGER IF NOT EXISTS trg_audit_logs_no_delete
BEFORE DELETE ON audit_logs
BEGIN
    SELECT RAISE(ABORT, 'audit_logs is immutable — DELETE not allowed');
END;
"""


def _create_tables(conn: sqlite3.Connection) -> None:
    """Execute the full schema DDL."""
    conn.executescript(_SCHEMA_SQL)


# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

def seed_data(conn: sqlite3.Connection) -> None:
    """
    Populate the database with realistic mock data.
    Idempotent: skips if any CCI rows already exist.
    """
    row = conn.execute("SELECT COUNT(*) AS cnt FROM ccis").fetchone()
    if row["cnt"] > 0:
        return  # already seeded

    now = datetime.now(timezone.utc)
    password = generate_password_hash("password123")

    # -----------------------------------------------------------------------
    # CCIs (3 in Hyderabad)
    # -----------------------------------------------------------------------
    cci_ids = [_uuid(), _uuid(), _uuid()]
    ccis = [
        (cci_ids[0], "Sishu Vihar CCI", "Hyderabad", "Telangana",
         "Plot 14, Nampally, Hyderabad 500001", 50, 38,
         "Lakshmi Devi", "9876543210", _iso_date(now - timedelta(days=45))),
        (cci_ids[1], "Rainbow Children Home", "Hyderabad", "Telangana",
         "12-2-831, Mehdipatnam, Hyderabad 500028", 40, 32,
         "Suresh Rao", "9876543211", _iso_date(now - timedelta(days=90))),
        (cci_ids[2], "Bal Sadhan CCI", "Hyderabad", "Telangana",
         "H.No 5-9-22, Secunderabad 500003", 35, 27,
         "Kavitha Nair", "9876543212", _iso_date(now - timedelta(days=120))),
    ]
    conn.executemany(
        "INSERT INTO ccis (id, name, district, state, address, capacity, "
        "current_occupancy, contact_person, contact_phone, last_inspection_date) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)", ccis,
    )

    # -----------------------------------------------------------------------
    # Users (8)
    # -----------------------------------------------------------------------
    user_ids = {role: _uuid() for role in [
        "cci_staff_1", "cci_staff_2", "cci_staff_3",
        "cwc_member_1", "cwc_member_2",
        "cwc_chairperson", "dcpu_officer",
        "wcd_official", "system_admin",
    ]}
    # We only need 8: 3 cci_staff + 2 cwc_member + 1 chairperson + 1 dcpu + 1 admin = 8
    # wcd_official is 9th, but the spec says 8 across *all* roles. Let's include
    # all listed: that gives 9 users which still covers the requirement.
    users = [
        # CCI staff — one per CCI
        (user_ids["cci_staff_1"], "lakshmi.devi", password,
         "Lakshmi Devi", "cci_staff", "Hyderabad", cci_ids[0],
         "lakshmi.devi@cpms.gov.in", "9876543210"),
        (user_ids["cci_staff_2"], "suresh.rao", password,
         "Suresh Rao", "cci_staff", "Hyderabad", cci_ids[1],
         "suresh.rao@cpms.gov.in", "9876543211"),
        (user_ids["cci_staff_3"], "kavitha.nair", password,
         "Kavitha Nair", "cci_staff", "Hyderabad", cci_ids[2],
         "kavitha.nair@cpms.gov.in", "9876543212"),
        # CWC members
        (user_ids["cwc_member_1"], "priya.sharma", password,
         "Priya Sharma", "cwc_member", "Hyderabad", None,
         "priya.sharma@cwc.gov.in", "9800000001"),
        (user_ids["cwc_member_2"], "vikram.singh", password,
         "Vikram Singh", "cwc_member", "Hyderabad", None,
         "vikram.singh@cwc.gov.in", "9800000002"),
        # CWC chairperson
        (user_ids["cwc_chairperson"], "deepak.joshi", password,
         "Deepak Joshi", "cwc_chairperson", "Hyderabad", None,
         "deepak.joshi@cwc.gov.in", "9800000003"),
        # DCPU officer
        (user_ids["dcpu_officer"], "meera.patel", password,
         "Meera Patel", "dcpu_officer", "Hyderabad", None,
         "meera.patel@dcpu.gov.in", "9800000004"),
        # WCD official (kept for completeness even though spec says 8)
        (user_ids["wcd_official"], "ananya.reddy", password,
         "Ananya Reddy", "wcd_official", "Hyderabad", None,
         "ananya.reddy@wcd.gov.in", "9800000005"),
        # System admin
        (user_ids["system_admin"], "admin", password,
         "System Administrator", "system_admin", "Hyderabad", None,
         "admin@cpms.gov.in", "9800000000"),
    ]
    conn.executemany(
        "INSERT INTO users (id, username, password_hash, full_name, role, "
        "district, cci_id, email, phone) VALUES (?,?,?,?,?,?,?,?,?)", users,
    )

    # -----------------------------------------------------------------------
    # Children (12)
    # -----------------------------------------------------------------------
    child_ids = [_uuid() for _ in range(12)]
    # Helper: admission dates spread across 3 years
    three_years_ago = now - timedelta(days=3 * 365)
    two_weeks_ago = now - timedelta(days=14)

    def _admission(days_ago: int) -> str:
        return _iso_date(now - timedelta(days=days_ago))

    children = [
        # --- CCI 1 (Sishu Vihar) — 4 children ---
        (child_ids[0], "CWC-HYD-2023-0001", "Rohan Verma",
         _iso_date(now - timedelta(days=365 * 10)), 10, "Male",
         _admission(900), "abandoned",
         "Medium build, scar on left forearm",
         cci_ids[0], "Hyderabad", "Legally Free for Adoption", 1,
         "No family contact for over 12 months"),

        (child_ids[1], "CWC-HYD-2024-0001", "Sita Kumari",
         _iso_date(now - timedelta(days=365 * 7)), 7, "Female",
         _admission(400), "surrendered",
         "Thin build, birthmark on right shoulder",
         cci_ids[0], "Hyderabad", "Under Inquiry", 0, None),

        (child_ids[2], "CWC-HYD-2024-0002", "Arjun Kumar",
         _iso_date(now - timedelta(days=365 * 17)), 17, "Male",
         _admission(1050), "orphaned",
         "Tall, wears spectacles",
         cci_ids[0], "Hyderabad", "Aged Out", 0, None),

        (child_ids[3], "CWC-HYD-2026-0001", "Unknown",
         None, 4, "Female",
         _admission(14), "abandoned",
         "Small build, wearing green frock when found near Charminar",
         cci_ids[0], "Hyderabad", "Under Inquiry", 0, None),

        # --- CCI 2 (Rainbow Children Home) — 4 children ---
        (child_ids[4], "CWC-HYD-2023-0002", "Rahul Prasad",
         _iso_date(now - timedelta(days=365 * 12)), 12, "Male",
         _admission(800), "police_brought",
         "Sturdy build, speaks Telugu and Hindi",
         cci_ids[1], "Hyderabad", "Under Review", 0, None),

        (child_ids[5], "CWC-HYD-2024-0003", "Ananya Reddy",
         _iso_date(now - timedelta(days=365 * 9)), 9, "Female",
         _admission(300), "guardian_surrendered",
         "Fair complexion, quiet demeanour",
         cci_ids[1], "Hyderabad", "Placed in Foster Care", 0, None),

        (child_ids[6], "CWC-HYD-2025-0001", "Vikram Singh Jr",
         _iso_date(now - timedelta(days=365 * 6)), 6, "Male",
         _admission(180), "abandoned",
         "Dark curly hair, energetic",
         cci_ids[1], "Hyderabad", "Under Inquiry", 0, None),

        (child_ids[7], "CWC-HYD-2024-0004", "Meera Patel Jr",
         _iso_date(now - timedelta(days=365 * 11)), 11, "Female",
         _admission(500), "surrendered",
         "Speaks Marathi, has a limp in left leg",
         cci_ids[1], "Hyderabad", "In Adoption Pool", 1,
         "Mother signed surrender deed; no contact in 8 months"),

        # --- CCI 3 (Bal Sadhan) — 4 children ---
        (child_ids[8], "CWC-HYD-2023-0003", "Priya Kumari",
         _iso_date(now - timedelta(days=365 * 8)), 8, "Female",
         _admission(700), "orphaned",
         "Cheerful, loves drawing",
         cci_ids[2], "Hyderabad", "Placed in Sponsorship", 0, None),

        (child_ids[9], "CWC-HYD-2024-0005", "Deepak Jr",
         _iso_date(now - timedelta(days=365 * 5)), 5, "Male",
         _admission(200), "police_brought",
         "Found near Secunderabad railway station",
         cci_ids[2], "Hyderabad", "Under Inquiry", 0, None),

        (child_ids[10], "CWC-HYD-2025-0002", "Kavitha Baby",
         _iso_date(now - timedelta(days=365 * 3)), 3, "Female",
         _admission(100), "abandoned",
         "Small, malnourished on admission",
         cci_ids[2], "Hyderabad", "Legally Free for Adoption", 1,
         "Abandoned; no family traced after 4 months of inquiry"),

        (child_ids[11], "CWC-HYD-2022-0001", "Suresh Kumar",
         _iso_date(now - timedelta(days=365 * 17 + 200)), 17, "Male",
         _admission(1100), "orphaned",
         "Tall, good at cricket, approaching 18",
         cci_ids[2], "Hyderabad", "Restored to Family", 0, None),
    ]
    conn.executemany(
        "INSERT INTO children (id, child_code, name, date_of_birth, "
        "estimated_age, gender, admission_date, admission_category, "
        "physical_description, cci_id, district, legal_status, "
        "is_lfa_eligible, lfa_flag_reason) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", children,
    )

    # -----------------------------------------------------------------------
    # Case history (16 entries — immutable)
    # -----------------------------------------------------------------------
    cwc_member_1 = user_ids["cwc_member_1"]
    cwc_chair = user_ids["cwc_chairperson"]
    cci_staff_1 = user_ids["cci_staff_1"]
    cci_staff_2 = user_ids["cci_staff_2"]
    cci_staff_3 = user_ids["cci_staff_3"]
    dcpu_off = user_ids["dcpu_officer"]

    case_history = [
        (_uuid(), child_ids[0], "admission", _admission(900),
         "Child found abandoned near Nampally bus station. Produced before CWC by police.",
         cci_staff_1, json.dumps({"fir_number": "PS-NMP-2023-4421"})),

        (_uuid(), child_ids[0], "cwc_production", _admission(899),
         "Child produced before CWC Hyderabad. Inquiry initiated under JJ Act Sec 36.",
         cwc_member_1, None),

        (_uuid(), child_ids[0], "inquiry_order", _admission(870),
         "30-day inquiry order issued. Social investigation report requested from DCPU.",
         cwc_chair, None),

        (_uuid(), child_ids[0], "status_change", _admission(600),
         "Declared Legally Free for Adoption after completion of inquiry. No family traced.",
         cwc_chair,
         json.dumps({"previous_status": "Under Inquiry",
                      "new_status": "Legally Free for Adoption"})),

        (_uuid(), child_ids[1], "admission", _admission(400),
         "Mother surrendered child at Sishu Vihar citing inability to care. "
         "Surrender deed executed.",
         cci_staff_1, json.dumps({"surrender_deed": True})),

        (_uuid(), child_ids[1], "cwc_production", _admission(399),
         "Child produced before CWC. 60-day reconsideration period initiated.",
         cwc_member_1, None),

        (_uuid(), child_ids[2], "admission", _admission(1050),
         "Orphan child admitted. Both parents deceased in road accident.",
         cci_staff_1,
         json.dumps({"parents_death_certificate": "DC-2022-78901"})),

        (_uuid(), child_ids[2], "status_change", _admission(200),
         "Child aged out. Rehabilitation and aftercare plan initiated.",
         cwc_chair,
         json.dumps({"previous_status": "Under Inquiry",
                      "new_status": "Aged Out"})),

        (_uuid(), child_ids[3], "admission", _admission(14),
         "Unidentified female child found near Charminar by police patrol. "
         "Estimated age 4 years.",
         cci_staff_1,
         json.dumps({"found_location": "Near Charminar, Hyderabad",
                      "found_by": "Charminar PS patrol"})),

        (_uuid(), child_ids[4], "admission", _admission(800),
         "Child brought by railway police. Found unaccompanied at "
         "Secunderabad Junction.",
         cci_staff_2,
         json.dumps({"police_station": "RPF Secunderabad"})),

        (_uuid(), child_ids[5], "placement", _admission(100),
         "Child placed with foster family — Mr. & Mrs. Narasimha Rao, "
         "Banjara Hills.",
         cwc_chair,
         json.dumps({"foster_family": "Narasimha Rao",
                      "address": "Banjara Hills, Hyderabad"})),

        (_uuid(), child_ids[7], "lfa_declared", _admission(150),
         "Child declared LFA. Surrender deed signed 8 months ago; "
         "no family contact since.",
         cwc_chair,
         json.dumps({"previous_status": "Under Inquiry",
                      "new_status": "In Adoption Pool"})),

        (_uuid(), child_ids[8], "admission", _admission(700),
         "Orphan child admitted. Father unknown; mother deceased.",
         cci_staff_3, None),

        (_uuid(), child_ids[9], "admission", _admission(200),
         "Child found begging near Secunderabad railway station by "
         "Childline volunteer.",
         cci_staff_3,
         json.dumps({"childline_ref": "1098-HYD-2024-5567"})),

        (_uuid(), child_ids[10], "lfa_declared", _admission(30),
         "Child declared LFA. Abandoned at birth; no family traced "
         "after 4 months of social investigation.",
         cwc_chair, None),

        (_uuid(), child_ids[11], "restoration", _admission(60),
         "Child restored to paternal uncle Mr. Ramesh Kumar after "
         "home study and CWC approval.",
         cwc_chair,
         json.dumps({"guardian": "Ramesh Kumar",
                      "relationship": "Paternal uncle"})),
    ]
    conn.executemany(
        "INSERT INTO case_history (id, child_id, event_type, event_date, "
        "description, performed_by, metadata) VALUES (?,?,?,?,?,?,?)",
        case_history,
    )

    # -----------------------------------------------------------------------
    # Hearings (5)
    # -----------------------------------------------------------------------
    hearing_ids = [_uuid() for _ in range(5)]
    hearings = [
        # Completed hearing 1 — child 0
        (hearing_ids[0], child_ids[0],
         _iso_date(now - timedelta(days=610)), "10:30",
         "completed", None,
         json.dumps([cwc_member_1, user_ids["cwc_member_2"], cwc_chair]),
         "बच्चा 900 दिन पहले मिला था। पुलिस ने चारमीनार के पास पाया। "
         "कोई परिवार नहीं मिला।",
         "The child was found 900 days ago near Nampally. No family "
         "traced after extensive inquiry. CWC recommends LFA declaration.",
         "hi",
         "All members unanimously recommended LFA status.",
         cwc_member_1, "Hyderabad"),

        # Completed hearing 2 — child 7
        (hearing_ids[1], child_ids[7],
         _iso_date(now - timedelta(days=160)), "11:00",
         "completed", None,
         json.dumps([cwc_member_1, cwc_chair]),
         "माँ ने समर्पण विलेख पर हस्ताक्षर किए। 8 महीने से कोई संपर्क नहीं।",
         "Mother signed surrender deed. No contact for 8 months. "
         "Social worker confirmed no extended family willing to take custody.",
         "hi",
         "LFA declared. Child to be placed in adoption pool.",
         cwc_member_1, "Hyderabad"),

        # Scheduled hearing — child 1
        (hearing_ids[2], child_ids[1],
         _iso_date(now + timedelta(days=7)), "10:00",
         "scheduled", None,
         json.dumps([cwc_member_1, user_ids["cwc_member_2"], cwc_chair]),
         None, None, "hi",
         "First inquiry hearing. Social investigation report awaited.",
         cwc_member_1, "Hyderabad"),

        # Scheduled hearing — child 9
        (hearing_ids[3], child_ids[9],
         _iso_date(now + timedelta(days=14)), "14:00",
         "scheduled", None,
         json.dumps([cwc_member_1, cwc_chair]),
         None, None, "te",
         "Follow-up hearing. Family tracing in progress.",
         cwc_member_1, "Hyderabad"),

        # Rescheduled hearing — child 6
        (hearing_ids[4], child_ids[6],
         _iso_date(now + timedelta(days=3)), "11:30",
         "rescheduled",
         "CWC Chairperson unavailable due to state-level review meeting.",
         json.dumps([cwc_member_1, cwc_chair]),
         None, None, "hi",
         "Originally scheduled for last week. Rescheduled.",
         cwc_member_1, "Hyderabad"),
    ]
    conn.executemany(
        "INSERT INTO hearings (id, child_id, hearing_date, scheduled_time, "
        "status, reschedule_reason, attendees, transcript_raw, "
        "transcript_edited, transcript_language, notes, created_by, district) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", hearings,
    )

    # -----------------------------------------------------------------------
    # Orders (3)
    # -----------------------------------------------------------------------
    order_ids = [_uuid() for _ in range(3)]
    orders = [
        # Approved order — LFA declaration for child 0
        (order_ids[0], "ORD-HYD-2024-0001", child_ids[0], hearing_ids[0],
         "lfa_declaration",
         "ORDER\n\nIn the matter of child Rohan Verma (CWC-HYD-2023-0001), "
         "the CWC Hyderabad, after completing inquiry under Section 36 of "
         "the Juvenile Justice Act, 2015, and being satisfied that no family "
         "has been traced despite efforts over 12 months, hereby declares "
         "the child Legally Free for Adoption under Section 38.",
         "No family traced. Police and DCPU inquiry exhausted. Child has "
         "been in institutional care for over 2 years.",
         "approved", cwc_chair,
         _iso_datetime(now - timedelta(days=600)),
         cwc_member_1, "Hyderabad"),

        # Pending approval — placement order for child 5
        (order_ids[1], "ORD-HYD-2024-0002", child_ids[5], None,
         "foster_care",
         "ORDER\n\nThe CWC Hyderabad orders placement of child Ananya Reddy "
         "(CWC-HYD-2024-0003) with the foster family of Mr. & Mrs. "
         "Narasimha Rao, Banjara Hills, Hyderabad, subject to periodic "
         "review every 6 months.",
         "Guardian unable to care. Foster family vetted by DCPU. Home study "
         "report satisfactory.",
         "pending_approval", None, None,
         cwc_member_1, "Hyderabad"),

        # Draft order — inquiry extension for child 6
        (order_ids[2], "ORD-HYD-2025-0001", child_ids[6], hearing_ids[4],
         "inquiry_extension",
         "DRAFT ORDER\n\nThe CWC Hyderabad extends the inquiry period for "
         "child Vikram Singh Jr (CWC-HYD-2025-0001) by an additional "
         "30 days to allow completion of family tracing.",
         None,
         "draft", None, None,
         cwc_member_1, "Hyderabad"),
    ]
    conn.executemany(
        "INSERT INTO orders (id, order_number, child_id, hearing_id, "
        "order_type, order_body, findings, status, approved_by, "
        "approved_at, created_by, district) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", orders,
    )

    # -----------------------------------------------------------------------
    # Family visits (8)
    # -----------------------------------------------------------------------
    family_visits = [
        (_uuid(), child_ids[1], _iso_date(now - timedelta(days=350)),
         "Geeta Kumari", "Mother", 45,
         "Mother visited. Emotional but stable. Expressed interest "
         "in reclaiming custody.",
         cci_staff_1),
        (_uuid(), child_ids[1], _iso_date(now - timedelta(days=200)),
         "Geeta Kumari", "Mother", 30,
         "Second visit. Mother asked about legal process for reclaiming.",
         cci_staff_1),
        (_uuid(), child_ids[4], _iso_date(now - timedelta(days=600)),
         "Ramesh Prasad", "Paternal uncle", 60,
         "Uncle visited. Said he cannot take custody but wants to stay "
         "in touch.",
         cci_staff_2),
        (_uuid(), child_ids[4], _iso_date(now - timedelta(days=300)),
         "Ramesh Prasad", "Paternal uncle", 40,
         "Follow-up visit. Brought clothes and books for the child.",
         cci_staff_2),
        (_uuid(), child_ids[5], _iso_date(now - timedelta(days=250)),
         "Savitri Devi", "Grandmother", 50,
         "Grandmother visited before foster placement. Said goodbye.",
         cci_staff_2),
        (_uuid(), child_ids[8], _iso_date(now - timedelta(days=500)),
         "Kamala Devi", "Maternal aunt", 35,
         "Aunt visited once. Has not returned since.",
         cci_staff_3),
        (_uuid(), child_ids[11], _iso_date(now - timedelta(days=90)),
         "Ramesh Kumar", "Paternal uncle", 90,
         "Pre-restoration visit. Uncle demonstrated readiness to take "
         "custody. Home study completed.",
         cci_staff_3),
        (_uuid(), child_ids[11], _iso_date(now - timedelta(days=60)),
         "Ramesh Kumar", "Paternal uncle", 120,
         "Final visit before restoration. Child enthusiastic about "
         "going home.",
         cci_staff_3),
    ]
    conn.executemany(
        "INSERT INTO family_visits (id, child_id, visit_date, visitor_name, "
        "relationship, duration_minutes, notes, logged_by) "
        "VALUES (?,?,?,?,?,?,?,?)", family_visits,
    )

    # -----------------------------------------------------------------------
    # CCI visits (2)
    # -----------------------------------------------------------------------
    cci_visits = [
        (_uuid(), cci_ids[0], _iso_date(now - timedelta(days=45)),
         dcpu_off,
         "Infrastructure satisfactory. Kitchen clean. Records maintained. "
         "2 children without updated medical records.",
         "Update medical records for all children. Install CCTV in "
         "common areas as per NCPCR guidelines."),
        (_uuid(), cci_ids[1], _iso_date(now - timedelta(days=90)),
         dcpu_off,
         "Overcrowding noted (32/40 capacity but 5 children sleeping on "
         "floor mats). Education records incomplete for 3 children.",
         "Procure additional beds. Complete Individual Care Plans for all "
         "children. Submit compliance report within 30 days."),
    ]
    conn.executemany(
        "INSERT INTO cci_visits (id, cci_id, visit_date, officer_id, "
        "findings, recommendations) VALUES (?,?,?,?,?,?)", cci_visits,
    )

    # -----------------------------------------------------------------------
    # Deadlines (varied statutory timelines)
    # -----------------------------------------------------------------------
    deadlines = [
        # 30-day inquiry — child 3 (recently admitted)
        (_uuid(), child_ids[3], "30_day_inquiry",
         _iso_date(now - timedelta(days=14) + timedelta(days=30)),
         "pending", cwc_member_1, None,
         "Inquiry to be completed within 30 days of admission."),

        # 60-day reconsideration — child 1 (surrendered)
        (_uuid(), child_ids[1], "60_day_reconsideration",
         _iso_date(now - timedelta(days=400) + timedelta(days=60)),
         "completed",
         cwc_member_1,
         _iso_datetime(now - timedelta(days=340)),
         "60-day period expired. Mother did not reclaim."),

        # Periodic review — child 4
        (_uuid(), child_ids[4], "periodic_review",
         _iso_date(now + timedelta(days=30)),
         "pending", cwc_member_1, None,
         "Quarterly review due for child under 'Under Review' status."),

        # Age-out alert — child 2 (already aged out)
        (_uuid(), child_ids[2], "age_out_alert",
         _iso_date(now - timedelta(days=200)),
         "completed", dcpu_off,
         _iso_datetime(now - timedelta(days=200)),
         "Child turned 18. Aftercare plan activated."),

        # Age-out alert — child 11 (approaching 18)
        (_uuid(), child_ids[11], "age_out_alert",
         _iso_date(now + timedelta(days=90)),
         "pending", dcpu_off, None,
         "Child approaching 18. Prepare aftercare / restoration plan."),

        # Follow-up hearing — child 6
        (_uuid(), child_ids[6], "follow_up_hearing",
         _iso_date(now + timedelta(days=3)),
         "pending", cwc_member_1, None,
         "Rescheduled hearing coming up. Family tracing still pending."),

        # 30-day inquiry — child 9
        (_uuid(), child_ids[9], "30_day_inquiry",
         _iso_date(now - timedelta(days=200) + timedelta(days=30)),
         "overdue", cwc_member_1, None,
         "30-day inquiry deadline passed. Escalation needed."),

        # Periodic review — child 8
        (_uuid(), child_ids[8], "periodic_review",
         _iso_date(now + timedelta(days=60)),
         "pending", cwc_member_1, None,
         "Sponsorship review due in 60 days."),
    ]
    conn.executemany(
        "INSERT INTO deadlines (id, child_id, deadline_type, due_date, "
        "status, assigned_to, completed_at, notes) "
        "VALUES (?,?,?,?,?,?,?,?)", deadlines,
    )

    # -----------------------------------------------------------------------
    # Audit logs (12 entries — immutable)
    # -----------------------------------------------------------------------
    audit_logs = [
        (_uuid(), user_ids["system_admin"], "system_init",
         None, None, "Database initialised and seeded with mock data.",
         "127.0.0.1"),
        (_uuid(), cci_staff_1, "child_admitted",
         "children", child_ids[0],
         "Admitted Rohan Verma (CWC-HYD-2023-0001) to Sishu Vihar CCI.",
         "10.0.0.51"),
        (_uuid(), cwc_member_1, "hearing_created",
         "hearings", hearing_ids[0],
         "Scheduled hearing for child Rohan Verma.",
         "10.0.0.52"),
        (_uuid(), cwc_chair, "order_approved",
         "orders", order_ids[0],
         "Approved LFA declaration order ORD-HYD-2024-0001.",
         "10.0.0.53"),
        (_uuid(), cci_staff_1, "child_admitted",
         "children", child_ids[3],
         "Admitted unidentified child (CWC-HYD-2026-0001) to Sishu Vihar CCI.",
         "10.0.0.51"),
        (_uuid(), cwc_member_1, "hearing_created",
         "hearings", hearing_ids[2],
         "Scheduled inquiry hearing for Sita Kumari.",
         "10.0.0.52"),
        (_uuid(), dcpu_off, "cci_inspection",
         "cci_visits", None,
         "Conducted inspection of Sishu Vihar CCI.",
         "10.0.0.60"),
        (_uuid(), cwc_chair, "status_change",
         "children", child_ids[0],
         "Changed status of Rohan Verma to Legally Free for Adoption.",
         "10.0.0.53"),
        (_uuid(), cwc_chair, "lfa_declared",
         "children", child_ids[10],
         "Declared Kavitha Baby as Legally Free for Adoption.",
         "10.0.0.53"),
        (_uuid(), user_ids["system_admin"], "user_login",
         "users", user_ids["system_admin"],
         "Admin login from management console.",
         "192.168.1.1"),
        (_uuid(), cci_staff_3, "family_visit_logged",
         "family_visits", None,
         "Logged family visit for Suresh Kumar by paternal uncle.",
         "10.0.0.55"),
        (_uuid(), cwc_chair, "order_created",
         "orders", order_ids[2],
         "Created draft inquiry extension order for Vikram Singh Jr.",
         "10.0.0.53"),
    ]
    conn.executemany(
        "INSERT INTO audit_logs (id, user_id, action, entity_type, "
        "entity_id, details, ip_address) VALUES (?,?,?,?,?,?,?)",
        audit_logs,
    )

    conn.commit()


# ---------------------------------------------------------------------------
# Initialisation (idempotent)
# ---------------------------------------------------------------------------

def init_db() -> None:
    """
    Create all tables (if they don't exist) and seed with mock data
    (if the database is empty). Safe to call multiple times.
    """
    conn = get_db()
    try:
        _create_tables(conn)
        seed_data(conn)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# CLI convenience
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(f"Initialising database at {DB_PATH} …")
    init_db()
    # Quick verification
    conn = get_db()
    tables = [
        "users", "ccis", "children", "case_history",
        "hearings", "orders", "family_visits", "cci_visits",
        "deadlines", "audit_logs",
    ]
    for t in tables:
        count = conn.execute(f"SELECT COUNT(*) AS cnt FROM {t}").fetchone()["cnt"]
        print(f"  {t:20s} -> {count} rows")
    conn.close()
    print("Done.")
