import pytest
from fastapi.testclient import TestClient

def test_duplicate_hearing_prevention(client: TestClient, db):
    # First, get a child from the seeded DB
    child = db.execute("SELECT id FROM children LIMIT 1").fetchone()
    child_id = child["id"]

    # Delete any existing scheduled hearings for this child to ensure clean state
    db.execute("DELETE FROM hearings WHERE child_id = ? AND status = 'scheduled'", (child_id,))
    db.commit()

    # Create the first hearing
    response1 = client.post(
        "/api/hearings",
        json={
            "child_id": child_id,
            "hearing_date": "2026-10-01",
            "hearing_time": "10:00",
            "notes": "Test hearing",
            "attendees": "[]",
            "district": "Hyderabad"
        },
        headers={"X-Test-Role": "cwc_member"}
    )
    assert response1.status_code == 201
    assert response1.json()["status"] == "scheduled"

    # Try to create a second scheduled hearing for the same child
    response2 = client.post(
        "/api/hearings",
        json={
            "child_id": child_id,
            "hearing_date": "2026-10-15",
            "hearing_time": "11:00",
            "notes": "Second test hearing",
            "attendees": "[]",
            "district": "Hyderabad"
        },
        headers={"X-Test-Role": "cwc_member"}
    )
    # Should be rejected
    assert response2.status_code == 400
    assert "An active scheduled hearing already exists" in response2.json()["detail"]


def test_reports_endpoint(client: TestClient):
    response = client.get(
        "/api/reports",
        headers={"X-Test-Role": "system_admin"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "total_children" in data
    assert "total_ccis" in data
    assert "total_hearings" in data
    assert "status_distribution" in data
    assert isinstance(data["status_distribution"], dict)


def test_cci_details_endpoint(client: TestClient, db):
    # Get a CCI that exists
    cci = db.execute("SELECT id FROM ccis LIMIT 1").fetchone()
    cci_id = cci["id"]

    response = client.get(
        f"/api/ccis/{cci_id}/details",
        headers={"X-Test-Role": "dcpu_officer"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "cci" in data
    assert data["cci"]["id"] == cci_id
    assert "children" in data
    assert "staff" in data
    assert isinstance(data["children"], list)
    assert isinstance(data["staff"], list)

    # Test 404 for non-existent CCI
    response_404 = client.get(
        "/api/ccis/nonexistent-id/details",
        headers={"X-Test-Role": "dcpu_officer"}
    )
    assert response_404.status_code == 404
