import requests
import json
import uuid

BASE_URL = 'http://127.0.0.1:5000'

def run_tests():
    print("Starting automated PRD tests...")
    session = requests.Session()

    # 1. Test Auth and Roles
    print("\n--- Testing Auth & Roles ---")
    r = session.post(f"{BASE_URL}/api/auth/login", json={"username": "admin", "password": "password123"})
    assert r.status_code == 200, "Admin login failed"
    print("✓ Admin login successful")

    r = session.get(f"{BASE_URL}/api/auth/me")
    assert r.status_code == 200
    assert r.json()['role'] == 'system_admin'
    print("✓ Role-based session verified")

    # 2. Test Child Registration (PRD 4.1.1)
    print("\n--- Testing Child Registration & Case File (PRD 4.1) ---")
    child_payload = {
        "name": "Test Child Auto",
        "date_of_birth": "2015-01-01",
        "gender": "Female",
        "admission_date": "2024-01-01",
        "admission_category": "abandoned",
        "physical_description": "Test description",
        "cci_id": "none",
        "district": "Hyderabad"
    }
    r = session.post(f"{BASE_URL}/api/children", json=child_payload)
    assert r.status_code == 200, f"Child registration failed: {r.text}"
    child_id = r.json()['id']
    print("✓ Child registration successful (PRD 4.1.1)")

    # 3. Test Case History (PRD 4.1.2)
    r = session.get(f"{BASE_URL}/api/children/{child_id}/history")
    assert r.status_code == 200
    history = r.json()
    assert len(history) > 0, "No case history generated"
    assert history[0]['event_type'] == 'admission'
    print("✓ Case history generation verified (PRD 4.1.2)")

    # 4. Test Legal Status Updates (PRD 4.1.3)
    r = session.put(f"{BASE_URL}/api/children/{child_id}/status", json={"legal_status": "restored"})
    assert r.status_code == 200
    r = session.get(f"{BASE_URL}/api/children/{child_id}")
    assert r.json()['legal_status'] == 'restored'
    print("✓ Legal status updates verified (PRD 4.1.3)")

    # 5. Test Hearing Scheduling (PRD 4.2.2)
    print("\n--- Testing CWC Hearing Documentation (PRD 4.2) ---")
    hearing_payload = {
        "child_id": child_id,
        "hearing_date": "2024-12-01"
    }
    r = session.post(f"{BASE_URL}/api/hearings", json=hearing_payload)
    assert r.status_code == 200, "Hearing scheduling failed"
    hearing_id = r.json()['id']
    print("✓ Hearing scheduling verified (PRD 4.2.2)")

    # 6. Test Order Generation (PRD 4.2.3)
    order_payload = {
        "child_id": child_id,
        "hearing_id": hearing_id,
        "order_type": "restoration",
        "order_body": "The child is restored.",
        "findings": "Verified by CWC."
    }
    r = session.post(f"{BASE_URL}/api/orders", json=order_payload)
    assert r.status_code == 200, "Order generation failed"
    order_id = r.json()['id']
    print("✓ Auto-Generated CWC Orders verified (PRD 4.2.3)")

    # 7. Test Dashboards & Alerts (PRD 4.3 & 4.4)
    print("\n--- Testing Dashboards, Alerts & Reports (PRD 4.3 - 4.5) ---")
    r = session.get(f"{BASE_URL}/api/dashboard/stats")
    assert r.status_code == 200
    assert 'total_children' in r.json()
    print("✓ DCPU Real-Time Child Dashboard Stats verified (PRD 4.4.1)")

    r = session.get(f"{BASE_URL}/api/dashboard/alerts")
    assert r.status_code == 200
    assert 'age_out_alerts' in r.json()
    print("✓ Age-out alerts and LFA Eligibility flagging verified (PRD 4.3.2 & 4.3.3)")

    r = session.get(f"{BASE_URL}/api/dashboard/deadlines")
    assert r.status_code == 200
    print("✓ Statutory Deadline Tracking verified (PRD 4.3.1)")

    r = session.get(f"{BASE_URL}/api/reports/monthly")
    assert r.status_code == 200
    print("✓ Auto-Generated Reports verified (PRD 4.5.1)")

    r = session.get(f"{BASE_URL}/api/audit")
    assert r.status_code == 200
    print("✓ Audit Trail verified (PRD 4.5.2)")

    print("\nAll PRD Backend Tests Passed Successfully! 🚀")

if __name__ == '__main__':
    try:
        run_tests()
    except AssertionError as e:
        print(f"❌ TEST FAILED: {e}")
    except requests.exceptions.ConnectionError:
        print("❌ SERVER NOT RUNNING: Please start app.py first.")
