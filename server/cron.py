import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from server.db import get_db, _iso_now

async def cron_worker():
    """
    Background worker that runs periodically to evaluate rules for Workflow C.
    Checks for age-out alerts (17.5 years) and CCI visits (>90 days).
    """
    print("Cron engine started.")
    while True:
        try:
            now = datetime.now()
            today = now.strftime("%Y-%m-%d")
            db = get_db()
            
            # Rule 1: Age-Out Alerts (17.5 years is approx 17 years and 6 months)
            # Find children whose estimated_age >= 17.5 or who were born exactly 17.5 years ago.
            # In our DB, we have date_of_birth and estimated_age.
            # Let's find children who are 17+ and haven't had an AGE_OUT alert yet.
            children = db.execute("SELECT id, name, child_code, date_of_birth, estimated_age, admission_date FROM children WHERE legal_status != 'Aged Out'").fetchall()
            
            for child in children:
                # Calculate age
                age = child["estimated_age"]
                if child["date_of_birth"]:
                    try:
                        dob = datetime.strptime(child["date_of_birth"], "%Y-%m-%d")
                        age = (now - dob).days / 365.25
                    except:
                        pass
                
                if age and age >= 17.5:
                    # Check if an alert already exists
                    existing = db.execute(
                        "SELECT id FROM notifications WHERE entity_type = 'child' AND entity_id = ? AND type = 'AGE_OUT_ALERT'",
                        (child["id"],)
                    ).fetchone()
                    
                    if not existing:
                        # Find relevant DCPU officer
                        dcpus = db.execute("SELECT id FROM users WHERE role = 'dcpu_officer'").fetchall()
                        for dcpu in dcpus:
                            db.execute(
                                """INSERT INTO notifications (id, user_id, type, title, message, entity_type, entity_id, created_at)
                                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                                (str(uuid.uuid4()), dcpu["id"], "AGE_OUT_ALERT", "Child Approaching Age-Out", 
                                 f"Child {child['name']} ({child['child_code']}) is {age:.1f} years old. Mandatory review required.", "child", child["id"], _iso_now())
                            )
                        db.commit()

            # Rule 2: DCPU CCI Visit > 90 days
            ccis = db.execute("SELECT id, name FROM ccis").fetchall()
            for cci in ccis:
                last_visit = db.execute(
                    "SELECT visit_date FROM cci_visits WHERE cci_id = ? ORDER BY visit_date DESC LIMIT 1",
                    (cci["id"],)
                ).fetchone()
                
                needs_visit = False
                if not last_visit:
                    needs_visit = True
                else:
                    try:
                        lv_date = datetime.strptime(last_visit["visit_date"][:10], "%Y-%m-%d")
                        if (now - lv_date).days > 90:
                            needs_visit = True
                    except:
                        pass
                
                if needs_visit:
                    # Prevent spamming: only alert if we haven't alerted in the last 7 days
                    seven_days_ago = (now - timedelta(days=7)).strftime("%Y-%m-%d")
                    recent_alert = db.execute(
                        "SELECT id FROM notifications WHERE entity_type = 'cci' AND entity_id = ? AND type = 'CCI_VISIT_OVERDUE' AND created_at >= ?",
                        (cci["id"], seven_days_ago)
                    ).fetchone()
                    
                    if not recent_alert:
                        dcpus = db.execute("SELECT id FROM users WHERE role = 'dcpu_officer'").fetchall()
                        for dcpu in dcpus:
                            db.execute(
                                """INSERT INTO notifications (id, user_id, type, title, message, entity_type, entity_id, created_at)
                                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                                (str(uuid.uuid4()), dcpu["id"], "CCI_VISIT_OVERDUE", "CCI Inspection Overdue", 
                                 f"CCI {cci['name']} has not been inspected in over 90 days.", "cci", cci["id"], _iso_now())
                            )
                        db.commit()

            print(f"[{_iso_now()}] Cron sweep completed.")
        except Exception as e:
            print(f"Cron error: {e}")
            
        # Run every 24 hours (or 1 hour in production, using 60 seconds for prototype testing)
        await asyncio.sleep(86400) # 24 hours
