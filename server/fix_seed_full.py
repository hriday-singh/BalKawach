import re

def main():
    file_path = "c:/Users/clash/OneDrive/Desktop/Codes/AI-ML/AI4Bharat/server/db.py"
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    new_seed_data = """def seed_data(conn: sqlite3.Connection) -> None:
    \"\"\"
    Populate the database with the initial setup:
    3 CCIs and multiple Users across the districts.
    No mock children or hearings are seeded.
    Idempotent: skips if any users already exist.
    \"\"\"
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

    conn.commit()"""

    pattern = re.compile(r'def seed_data\(conn: sqlite3\.Connection\) -> None:.*?conn\.commit\(\)', re.DOTALL)
    
    new_content, count = pattern.subn(new_seed_data, content)
    
    if count > 0:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print("Success!")
    else:
        print("Failed to match.")

if __name__ == "__main__":
    main()
