from datetime import datetime, date
from fastapi.testclient import TestClient
from backend.app import app

client = TestClient(app)

SAMPLE_TEXT_MISMATCH = """
Name: Ramesh Kumar
DOB: 19/04/2001
Age: 10
Gender: Male
Address: B12/3 Gandhi Street MG Road
Phone: +91 98765-43210
Email: ramesh.kumar@example.com
"""

# Build consistent sample dynamically to avoid future age drift
DOB_STR = "19/04/2001"
parsed = datetime.strptime(DOB_STR.replace('/', '-'), "%d-%m-%Y").date()
derived_age = int((date.today() - parsed).days / 365.25)
SAMPLE_TEXT_CONSISTENT = f"""
Name: Ramesh Kumar
DOB: {DOB_STR}
Age: {derived_age}
Gender: Male
Address: B12/3 Gandhi Street MG Road
Phone: +91 98765-43210
Email: ramesh.kumar@example.com
"""

USER = {
    "name": "Ramesh Kumar",
    "dob": "19-04-2001",
    "phone": "9876543210",
    "address": "B12/3 Gandhi Street MG Road",
    "gender": "male"
}

def test_age_mismatch_note():
    resp = client.post("/api/v1/map-and-verify", json={"raw_text": SAMPLE_TEXT_MISMATCH, "user": USER})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    notes = data["verification"].get("notes", [])
    # Expect age_mismatch note since derived age will not match stated age 10
    assert any(n.startswith("age_mismatch") for n in notes)
    # Ensure overall_confidence unaffected by age
    assert "overall_confidence" in data["verification"]
    assert "age" in data["mapped"]

def test_age_consistent_no_mismatch():
    resp = client.post("/api/v1/map-and-verify", json={"raw_text": SAMPLE_TEXT_CONSISTENT, "user": {
        "name": USER["name"],
        "dob": USER["dob"],
        "phone": USER["phone"],
        "address": USER["address"],
        "gender": USER["gender"],
    }})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    notes = data["verification"].get("notes", [])
    assert not any(n.startswith("age_mismatch") for n in notes), f"Unexpected age_mismatch note found: {notes}"
