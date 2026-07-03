"""
db.py — SQLite Database Layer for Child Protection Case Management Platform
=============================================================================
Used by Child Welfare Committees (CWCs) and District Child Protection Units
(DCPUs) in India. Fully self-contained: import and call init_db() to create
and seed everything.

Tables (11):
  users, ccis, children, case_history (immutable), hearings, orders,
  family_visits, cci_visits, deadlines, audit_logs (immutable),
  notifications

Usage:
    from server.db import init_db, get_db
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

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cpms.db")


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
    conn = sqlite3.connect(DB_PATH, timeout=15.0, isolation_level=None)
    conn.execute("PRAGMA journal_mode=WAL;")
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
    location        TEXT,
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
    staffing_details    TEXT,
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
    audio_url           TEXT,
    transcript_finalized     INTEGER DEFAULT 0,
    transcript_finalized_at  TEXT,
    transcript_finalized_by  TEXT,
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
    updated_at      TEXT DEFAULT (datetime('now')),
    updated_by      TEXT,
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
    escalated_to    TEXT,
    escalated_at    TEXT,
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

-- ==========================================================================
-- 11. notifications — User notification inbox
-- ==========================================================================
CREATE TABLE IF NOT EXISTS notifications (
    id              TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL,
    type            TEXT NOT NULL,
    title           TEXT NOT NULL,
    message         TEXT NOT NULL,
    entity_type     TEXT,
    entity_id       TEXT,
    is_read         INTEGER DEFAULT 0,
    created_at      TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- ==========================================================================
-- 12. reports — Async background jobs for PDF generation
-- ==========================================================================
CREATE TABLE IF NOT EXISTS reports (
    id              TEXT PRIMARY KEY,
    type            TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'processing', 'completed', 'failed')),
    file_path       TEXT,
    error_message   TEXT,
    requested_by    TEXT,
    requested_at    TEXT DEFAULT (datetime('now')),
    completed_at    TEXT,
    FOREIGN KEY (requested_by) REFERENCES users(id)
);

-- ==========================================================================
-- Performance indexes
-- ==========================================================================
CREATE INDEX IF NOT EXISTS idx_children_cci_id ON children(cci_id);
CREATE INDEX IF NOT EXISTS idx_children_district ON children(district);
CREATE INDEX IF NOT EXISTS idx_children_legal_status ON children(legal_status);
CREATE INDEX IF NOT EXISTS idx_children_admission_date ON children(admission_date);
CREATE INDEX IF NOT EXISTS idx_case_history_child_id ON case_history(child_id);
CREATE INDEX IF NOT EXISTS idx_case_history_event_date ON case_history(event_date);
CREATE INDEX IF NOT EXISTS idx_hearings_child_id ON hearings(child_id);
CREATE INDEX IF NOT EXISTS idx_hearings_hearing_date ON hearings(hearing_date);
CREATE INDEX IF NOT EXISTS idx_hearings_district ON hearings(district);
CREATE INDEX IF NOT EXISTS idx_orders_child_id ON orders(child_id);
CREATE INDEX IF NOT EXISTS idx_orders_district ON orders(district);
CREATE INDEX IF NOT EXISTS idx_family_visits_child_id ON family_visits(child_id);
CREATE INDEX IF NOT EXISTS idx_family_visits_visit_date ON family_visits(visit_date);
CREATE INDEX IF NOT EXISTS idx_deadlines_child_id ON deadlines(child_id);
CREATE INDEX IF NOT EXISTS idx_deadlines_due_date ON deadlines(due_date);
CREATE INDEX IF NOT EXISTS idx_deadlines_status ON deadlines(status);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_cci_visits_cci_id ON cci_visits(cci_id);
CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_is_read ON notifications(is_read);
"""


def _create_tables(conn: sqlite3.Connection) -> None:
    """Execute the full schema DDL."""
    conn.executescript(_SCHEMA_SQL)


# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

def seed_data(conn: sqlite3.Connection) -> None:
    """
    Populate the database with the initial setup:
    3 CCIs and multiple Users across the districts.
    No mock children or hearings are seeded.
    Idempotent: skips if any users already exist.
    """
    row = conn.execute("SELECT COUNT(*) AS cnt FROM users").fetchone()
    if row["cnt"] > 0:
        return  # already seeded

    now = datetime.now(timezone.utc)
    password = generate_password_hash("password123")

    # -----------------------------------------------------------------------
    # CCIs (Hyderabad, Visakhapatnam, Noida)
    # -----------------------------------------------------------------------
    cci_ids = {
        "Hyderabad": _uuid(),
        "Visakhapatnam": _uuid(),
        "Noida": _uuid()
    }
    
    ccis = [
        (cci_ids["Hyderabad"], "Sishu Vihar CCI", "Hyderabad", "Telangana",
         "Plot 14, Nampally, Hyderabad 500001", 50, 0,
         "Lakshmi Devi", "9876543210", _iso_date(now - timedelta(days=45))),
        (cci_ids["Visakhapatnam"], "Visakha Children's Home", "Visakhapatnam", "Andhra Pradesh",
         "Beach Road, Visakhapatnam, AP 530003", 35, 0,
         "Rao Garu", "9876543211", _iso_date(now - timedelta(days=120))),
        (cci_ids["Noida"], "Rainbow Children Home", "Noida", "Uttar Pradesh",
         "Sector 62, Noida, UP 201309", 40, 0,
         "Suresh Rao", "9876543212", _iso_date(now - timedelta(days=90))),
    ]
    conn.executemany(
        "INSERT INTO ccis (id, name, district, state, address, capacity, "
        "current_occupancy, contact_person, contact_phone, last_inspection_date) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)", ccis,
    )

    # -----------------------------------------------------------------------
    # Users
    # -----------------------------------------------------------------------
    admin_id = _uuid()
    users = [
        # System Admin & WCD Official (Global/State)
        (admin_id, "admin", password,
         "System Administrator", "system_admin", "System", "HQ, New Delhi", None,
         "admin@cpms.gov.in", "9800000000"),
        (_uuid(), "wcd.official", password,
         "State Director", "wcd_official", "System", "State HQ", None,
         "wcd@cpms.gov.in", "9800000001"),
         
        # Hyderabad Users
        (_uuid(), "hyd.staff", password,
         "Lakshmi Devi", "cci_staff", "Hyderabad", "Sishu Vihar CCI, Hyderabad", cci_ids["Hyderabad"],
         "hyd.staff@cpms.gov.in", "9800000011"),
        (_uuid(), "hyd.cwc", password,
         "Priya Sharma", "cwc_member", "Hyderabad", "CWC Member, Hyderabad", None,
         "hyd.cwc@cwc.gov.in", "9800000012"),
        (_uuid(), "hyd.chair", password,
         "Deepak Joshi", "cwc_chairperson", "Hyderabad", "CWC Chairperson, Hyderabad", None,
         "hyd.chair@cwc.gov.in", "9800000013"),
        (_uuid(), "hyd.dcpu", password,
         "Meera Patel", "dcpu_officer", "Hyderabad", "DCPU, Hyderabad", None,
         "hyd.dcpu@dcpu.gov.in", "9800000014"),

        # Visakhapatnam Users
        (_uuid(), "vizag.staff", password,
         "Rao Garu", "cci_staff", "Visakhapatnam", "Visakha Children's Home, Visakhapatnam", cci_ids["Visakhapatnam"],
         "vizag.staff@cpms.gov.in", "9800000021"),
        (_uuid(), "vizag.cwc", password,
         "Kavitha Nair", "cwc_member", "Visakhapatnam", "CWC Member, Visakhapatnam", None,
         "vizag.cwc@cwc.gov.in", "9800000022"),
        (_uuid(), "vizag.chair", password,
         "Srinivas Reddy", "cwc_chairperson", "Visakhapatnam", "CWC Chairperson, Visakhapatnam", None,
         "vizag.chair@cwc.gov.in", "9800000023"),
        (_uuid(), "vizag.dcpu", password,
         "Arjun Kumar", "dcpu_officer", "Visakhapatnam", "DCPU, Visakhapatnam", None,
         "vizag.dcpu@dcpu.gov.in", "9800000024"),

        # Noida Users
        (_uuid(), "noida.staff", password,
         "Suresh Rao", "cci_staff", "Noida", "Rainbow Children Home, Noida", cci_ids["Noida"],
         "noida.staff@cpms.gov.in", "9800000031"),
        (_uuid(), "noida.cwc", password,
         "Vikram Singh", "cwc_member", "Noida", "CWC Member, Noida", None,
         "noida.cwc@cwc.gov.in", "9800000032"),
        (_uuid(), "noida.chair", password,
         "Ananya Sharma", "cwc_chairperson", "Noida", "CWC Chairperson, Noida", None,
         "noida.chair@cwc.gov.in", "9800000033"),
        (_uuid(), "noida.dcpu", password,
         "Ramesh Prasad", "dcpu_officer", "Noida", "DCPU, Noida", None,
         "noida.dcpu@dcpu.gov.in", "9800000034"),
    ]
    
    conn.executemany(
        "INSERT INTO users (id, username, password_hash, full_name, role, district, location, cci_id, email, phone) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)", users,
    )

    # -----------------------------------------------------------------------
    # Audit logs (1 entry)
    # -----------------------------------------------------------------------
    audit_logs = [
        (_uuid(), admin_id, "system_init",
         None, None, "Database initialised with multi-district CCIs and Users.",
         "127.0.0.1"),
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
        "deadlines", "audit_logs", "notifications",
    ]
    for t in tables:
        count = conn.execute(f"SELECT COUNT(*) AS cnt FROM {t}").fetchone()["cnt"]
        print(f"  {t:20s} -> {count} rows")
    conn.close()
    print("Done.")
