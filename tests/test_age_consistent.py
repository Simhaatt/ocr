from datetime import datetime, date
from fastapi.testclient import TestClient
from backend.app import app

client = TestClient(app)

DOB_STR = "19/04/2001"
# Derive age with same logic as route (int of days/365.25)
parsed = datetime.strptime(DOB_STR.replace('/', '-'), "%d-%m-%Y").date()
derived_age = int((date.today() - parsed).days / 365.25)

SAMPLE_TEXT_TEMPLATE = """
Name: Ramesh Kumar
DOB: {dob}
Age: {age}
Gender: Male
Address: B12/3 Gandhi Street MG Road
Phone: +91 98765-43210
Email: ramesh.kumar@example.com
"""

SAMPLE_TEXT = SAMPLE_TEXT_TEMPLATE.format(dob=DOB_STR, age=derived_age)

USER = {
    "name": "Ramesh Kumar",
    "dob": DOB_STR.replace('/', '-'),
    "phone": "9876543210",
    "address": "B12/3 Gandhi Street MG Road",
    "gender": "male"
}

def test_age_consistent_no_mismatch():
    resp = client.post("/api/v1/map-and-verify", json={"raw_text": SAMPLE_TEXT, "user": USER})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    notes = data["verification"].get("notes", [])
    assert not any(n.startswith("age_mismatch") for n in notes), f"Unexpected age_mismatch note found: {notes}"
