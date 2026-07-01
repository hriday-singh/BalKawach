import traceback
from app import app

client = app.test_client()

try:
    print("Logging in...")
    r = client.post("/api/auth/login", json={"username": "admin", "password": "password123"})
    
    r_ccis = client.get("/api/ccis")
    ccis = r_ccis.json
    valid_cci_id = ccis[0]["id"] if ccis else "none"

    print("Registering child...")
    child_payload = {
        "name": "Test Child Auto",
        "date_of_birth": "2015-01-01",
        "gender": "Female",
        "admission_date": "2024-01-01",
        "admission_category": "abandoned",
        "physical_description": "Test description",
        "cci_id": valid_cci_id,
        "district": "Hyderabad"
    }
    r = client.post("/api/children", json=child_payload)
    print(r.status_code)
    if r.status_code != 200:
        print(r.text)
except Exception as e:
    traceback.print_exc()
