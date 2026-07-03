import sqlite3
import uuid
import random
import os
from datetime import datetime, timedelta, timezone

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.db import DB_PATH, get_db, _create_tables, _uuid, _iso_datetime, _iso_date, seed_data

def clear_transactional_data(conn: sqlite3.Connection):
    print("Clearing transactional data...")
    conn.execute("PRAGMA foreign_keys = OFF")
    tables_to_clear = [
        'notifications', 'reports', 'deadlines', 'cci_visits', 'family_visits', 
        'orders', 'hearings', 'case_history', 'children', 'audit_logs'
    ]
    for table in tables_to_clear:
        try:
            conn.execute(f"DROP TABLE {table}")
        except Exception as e:
            print(f"Error dropping {table}: {e}")
            pass
    _create_tables(conn)
    conn.execute("PRAGMA foreign_keys = ON")
    print("Transactional data cleared and tables recreated.")

def generate_mock_data():
    conn = get_db()
    seed_data(conn)
    clear_transactional_data(conn)

    now = datetime.now(timezone.utc)
    ccis = conn.execute("SELECT * FROM ccis").fetchall()
    users = conn.execute("SELECT * FROM users").fetchall()
    
    users_by_district = {}
    for user in users:
        dist = user['district']
        role = user['role']
        if dist not in users_by_district:
            users_by_district[dist] = {}
        if role not in users_by_district[dist]:
            users_by_district[dist][role] = []
        users_by_district[dist][role].append(user)

    names = {
        'Hyderabad': {
            'first': ["Sai Kiran", "Lakshmi Prasanna", "Karthik", "Anjali", "Venkatesh", "Bhavya", "Ramu", "Swathi", "Akhil", "Divya", "Sandeep", "Nandini"],
            'last': ["Reddy", "Rao", "Naidu", "Chowdary", "Goud", "Yadav", "Sharma"]
        },
        'Visakhapatnam': {
            'first': ["Surya Prakash", "Harika", "Gopi Chand", "Meenakshi", "Pavan Kumar", "Sravani", "Ravi Teja", "Kavya", "Mahesh", "Sita", "Rajesh", "Keerthi"],
            'last': ["Reddy", "Naidu", "Rao", "Varma", "Patnaik"]
        },
        'Noida': {
            'first': ["Rahul", "Pooja", "Amit", "Neha", "Rohan", "Sneha", "Karan", "Riya", "Vikash", "Aarti", "Manish", "Sonali"],
            'last': ["Sharma", "Singh", "Kumar", "Gupta", "Verma", "Das", "Malhotra", "Jain", "Yadav"]
        }
    }
    
    transcripts = {
        'hi': "बाल कल्याण समिति के समक्ष बच्चे को प्रस्तुत किया गया। पुलिस रिपोर्ट के अनुसार बच्चा लावारिस अवस्था में मिला था। बच्चे की उम्र लगभग 5 वर्ष प्रतीत होती है। समिति आदेश देती है कि बच्चे को बाल गृह में सुरक्षित रखा जाए और 30 दिन के भीतर जांच रिपोर्ट प्रस्तुत की जाए।",
        'te': "బాలల సంక్షేమ సమితి ముందు పిల్లను ప్రవేశపెట్టారు. పోలీసు నివేదిక ప్రకారం పిల్లవాడు అనాథగా దొరికాడు. వయస్సు సుమారు 5 సంవత్సరాలుగా అంచనా. పిల్లను సురక్షితంగా చిల్డ్రన్స్ హోమ్‌లో ఉంచాలని మరియు 30 రోజుల్లో దర్యాప్తు నివేదిక సమర్పించాలని సమితి ఆదేశిస్తోంది.",
        'ta': "குழந்தை நலக் குழுவின் முன் குழந்தை ஆஜர்படுத்தப்பட்டது. காவல்துறை அறிக்கையின்படி, குழந்தை அனாதையாகக் கண்டெடுக்கப்பட்டது. குழந்தையின் வயது சுமார் 5 ஆண்டுகள் என மதிப்பிடப்பட்டுள்ளது. குழந்தையை குழந்தைகள் இல்லத்தில் பாதுகாப்பாக வைக்கவும், 30 நாட்களுக்குள் விசாரணை அறிக்கையை சமர்ப்பிக்கவும் குழு உத்தரவிடுகிறது.",
        'en': "The child was produced before the Child Welfare Committee. As per the police report, the child was found abandoned. The estimated age is around 5 years. The Committee orders the child to be kept safe in the children's home and an inquiry report to be submitted within 30 days."
    }

    admission_categories = ['abandoned','surrendered','orphaned','guardian_surrendered','police_brought','runaway']

    total_children = 0
    print("Generating mock children and related records...")

    for cci in ccis:
        district = cci['district']
        cci_id = cci['id']
        cci_name = cci['name']
        
        cci_staff = users_by_district.get(district, {}).get('cci_staff', [None])[0]
        cwc_member = users_by_district.get(district, {}).get('cwc_member', [None])[0]
        cwc_chair = users_by_district.get(district, {}).get('cwc_chairperson', [None])[0]
        dcpu = users_by_district.get(district, {}).get('dcpu_officer', [None])[0]

        if not cci_staff: continue

        dist_names = names.get(district, names['Noida'])
        
        for i in range(15):
            child_id = _uuid()
            child_code = f"CH-{district[:3].upper()}-{total_children+1:04d}"
            name = random.choice(dist_names['first']) + " " + random.choice(dist_names['last'])
            estimated_age = random.randint(2, 17)
            
            scenario = random.choices(
                ['recent_inquiry', 'overdue_inquiry', 'surrendered_reconsideration', 'abandoned_no_contact', 'age_out', 'lfa', 'restored'],
                weights=[20, 15, 10, 15, 10, 20, 10], k=1
            )[0]

            admission_date = now - timedelta(days=random.randint(1, 300))
            status = 'Under Inquiry'
            category = random.choice(admission_categories)
            is_lfa_eligible = 0
            lfa_flag_reason = None
            
            if scenario == 'recent_inquiry':
                admission_date = now - timedelta(days=random.randint(25, 29))
                status = 'Under Inquiry'
            elif scenario == 'overdue_inquiry':
                admission_date = now - timedelta(days=random.randint(31, 40))
                status = 'Under Inquiry'
            elif scenario == 'surrendered_reconsideration':
                admission_date = now - timedelta(days=random.randint(10, 50))
                category = 'surrendered'
                status = 'Under Inquiry'
            elif scenario == 'abandoned_no_contact':
                admission_date = now - timedelta(days=random.randint(200, 300))
                category = 'abandoned'
                status = 'Under Review'
                is_lfa_eligible = 1
                lfa_flag_reason = "No family contact for > 6 months."
            elif scenario == 'age_out':
                estimated_age = 17
                date_of_birth = _iso_date(now - timedelta(days=(17*365 + 180 + random.randint(-30, 30))))
                admission_date = now - timedelta(days=random.randint(100, 200))
                status = 'Under Review'
            elif scenario == 'lfa':
                admission_date = now - timedelta(days=random.randint(150, 300))
                status = random.choice(['Legally Free for Adoption', 'In Adoption Pool'])
            elif scenario == 'restored':
                admission_date = now - timedelta(days=random.randint(200, 400))
                status = random.choice(['Restored to Family', 'Placed in Foster Care'])

            if scenario != 'age_out':
                date_of_birth = _iso_date(now - timedelta(days=estimated_age*365 + random.randint(1, 360)))

            gender = random.choice(['Male', 'Female'])

            conn.execute(
                "INSERT INTO children (id, child_code, name, date_of_birth, estimated_age, gender, admission_date, admission_category, physical_description, cci_id, district, legal_status, is_lfa_eligible, lfa_flag_reason) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (child_id, child_code, name, date_of_birth, estimated_age, gender, _iso_date(admission_date), category, "Average build", cci_id, district, status, is_lfa_eligible, lfa_flag_reason)
            )

            conn.execute(
                "INSERT INTO case_history (id, child_id, event_type, event_date, description, performed_by) VALUES (?,?,?,?,?,?)",
                (_uuid(), child_id, "Admission", _iso_datetime(admission_date), f"Admitted to {cci_name} as {category}", cci_staff['id'])
            )

            if scenario in ['recent_inquiry', 'overdue_inquiry']:
                due_date = admission_date + timedelta(days=30)
                d_status = 'pending' if scenario == 'recent_inquiry' else 'overdue'
                conn.execute(
                    "INSERT INTO deadlines (id, child_id, deadline_type, due_date, status, assigned_to) VALUES (?,?,?,?,?,?)",
                    (_uuid(), child_id, "30-day Inquiry", _iso_date(due_date), d_status, cwc_member['id'])
                )
                if d_status == 'overdue':
                    conn.execute(
                        "INSERT INTO notifications (id, user_id, type, title, message, entity_type, entity_id) VALUES (?,?,?,?,?,?,?)",
                        (_uuid(), dcpu['id'], 'deadline_overdue', 'Inquiry Overdue', f"30-day inquiry overdue for {name}", 'child', child_id)
                    )

            if scenario == 'surrendered_reconsideration':
                due_date = admission_date + timedelta(days=60)
                conn.execute(
                    "INSERT INTO deadlines (id, child_id, deadline_type, due_date, status, assigned_to) VALUES (?,?,?,?,?,?)",
                    (_uuid(), child_id, "60-day Reconsideration", _iso_date(due_date), 'pending', cwc_member['id'])
                )

            # Generate Hearings & Realistic Orders
            if admission_date < now - timedelta(days=5):
                hearing_date = admission_date + timedelta(days=random.randint(2, 5))
                hearing_id = _uuid()
                lang = random.choice(['hi', 'te', 'ta', 'en'])
                transcript = transcripts[lang]
                
                conn.execute(
                    "INSERT INTO hearings (id, child_id, hearing_date, status, attendees, transcript_raw, transcript_edited, transcript_language, notes, transcript_finalized, created_by, district) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (hearing_id, child_id, _iso_datetime(hearing_date), 'completed', f"{cwc_chair['full_name']}, {cwc_member['full_name']}", transcript, transcript, lang, "First production", 1, cwc_member['id'], district)
                )
                conn.execute(
                    "INSERT INTO case_history (id, child_id, event_type, event_date, description, performed_by) VALUES (?,?,?,?,?,?)",
                    (_uuid(), child_id, "Hearing", _iso_datetime(hearing_date), "CWC Hearing Conducted", cwc_member['id'])
                )

                # Order Logic based on Scenario
                order_id = _uuid()
                order_num = f"ORD/{now.year}/{uuid.uuid4().hex[:6].upper()}"
                
                if scenario == 'recent_inquiry':
                    # Might be draft or pending_approval placement
                    o_type = 'placement'
                    o_body = "Child to be placed in CCI for safe custody during the inquiry period. DCPU to submit SIR."
                    o_status = random.choice(['draft', 'pending_approval'])
                elif scenario == 'overdue_inquiry':
                    # Might have an inquiry_extension that is pending_approval or rejected
                    o_type = 'inquiry_extension'
                    o_body = "The inquiry period is extended by 15 days as the police verification report is still pending. DCPU must expedite."
                    o_status = random.choice(['pending_approval', 'rejected', 'approved'])
                elif scenario == 'restored':
                    o_type = random.choice(['restoration', 'foster_care'])
                    if o_type == 'restoration':
                        o_body = "Child ordered to be restored to biological parents. Counselling has been provided. Parents' identity verified."
                    else:
                        o_body = "Child deemed fit for foster care. DCPU instructed to map to a suitable foster family within the district."
                    o_status = 'approved'
                else:
                    o_type = 'placement'
                    o_body = "Initial placement order for care and protection in CCI."
                    o_status = 'approved'

                approved_by = None
                approved_at = None
                if o_status == 'approved':
                    approved_by = cwc_chair['id']
                    approved_at = _iso_datetime(hearing_date + timedelta(hours=random.randint(1, 48)))
                
                conn.execute(
                    "INSERT INTO orders (id, order_number, child_id, hearing_id, order_type, order_body, status, approved_by, approved_at, created_by, district) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (order_id, order_num, child_id, hearing_id, o_type, o_body, o_status, approved_by, approved_at, cwc_member['id'], district)
                )

            # LFA Specific Orders
            if scenario in ['lfa']:
                lfa_date = admission_date + timedelta(days=random.randint(45, 90))
                conn.execute(
                    "INSERT INTO case_history (id, child_id, event_type, event_date, description, performed_by) VALUES (?,?,?,?,?,?)",
                    (_uuid(), child_id, "Status Change", _iso_datetime(lfa_date), "Declared Legally Free for Adoption", cwc_chair['id'])
                )
                
                # Add an LFA order (approved)
                conn.execute(
                    "INSERT INTO orders (id, order_number, child_id, order_type, order_body, status, approved_by, approved_at, created_by, district) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (_uuid(), f"LFA/{now.year}/{uuid.uuid4().hex[:6].upper()}", child_id, 'lfa_declaration', "Child declared Legally Free for Adoption after exhaustive inquiry and 2-month appeal period. No claimants found.", 'approved', cwc_chair['id'], _iso_datetime(lfa_date), cwc_member['id'], district)
                )

            # Family Visits
            if scenario not in ['abandoned_no_contact', 'lfa'] and random.random() > 0.5:
                visit_date = admission_date + timedelta(days=random.randint(5, 20))
                conn.execute(
                    "INSERT INTO family_visits (id, child_id, visit_date, visitor_name, relationship, duration_minutes, logged_by) VALUES (?,?,?,?,?,?,?)",
                    (_uuid(), child_id, _iso_date(visit_date), "Raju", "Uncle", 45, cci_staff['id'])
                )

            total_children += 1

    # CCI Visits (DCPU Monitoring)
    for cci in ccis:
        district = cci['district']
        dcpu = users_by_district.get(district, {}).get('dcpu_officer', [None])[0]
        if dcpu:
            if random.random() > 0.3:
                visit_date = now - timedelta(days=random.randint(10, 40))
                conn.execute(
                    "INSERT INTO cci_visits (id, cci_id, visit_date, officer_id, findings, recommendations) VALUES (?,?,?,?,?,?)",
                    (_uuid(), cci['id'], _iso_date(visit_date), dcpu['id'], "Satisfactory conditions. Records updated.", "Maintain cleanliness in kitchen.")
                )
                conn.execute(f"UPDATE ccis SET last_inspection_date = ? WHERE id = ?", (_iso_date(visit_date), cci['id']))
            else:
                visit_date = now - timedelta(days=random.randint(100, 150))
                conn.execute(
                    "INSERT INTO cci_visits (id, cci_id, visit_date, officer_id, findings, recommendations) VALUES (?,?,?,?,?,?)",
                    (_uuid(), cci['id'], _iso_date(visit_date), dcpu['id'], "Some registers missing.", "Update registers immediately.")
                )
                conn.execute(f"UPDATE ccis SET last_inspection_date = ? WHERE id = ?", (_iso_date(visit_date), cci['id']))
                conn.execute(
                    "INSERT INTO notifications (id, user_id, type, title, message, entity_type, entity_id) VALUES (?,?,?,?,?,?,?)",
                    (_uuid(), dcpu['id'], 'cci_visit_overdue', 'CCI Visit Overdue', f"Inspection for {cci['name']} is overdue (>90 days).", 'cci', cci['id'])
                )

    conn.commit()
    conn.close()
    print(f"Successfully generated {total_children} children and related mock data!")

if __name__ == "__main__":
    generate_mock_data()
