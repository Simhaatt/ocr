from fastapi.testclient import TestClient
from backend.app import app

client = TestClient(app)

def test_direct_verify_fields_key():
    payload = {
        "ocr": {
            "name": "Ramesh Kumaar",
            "dob": "19/04/2001",
            "phone": "+91 98765-43210",
            "address": "Flat No B-12/3 Gandhi St.",
            "gender": "Male"
        },
        "user": {
            "name": "Ramesh Kumar",
            "dob": "19-04-2001",
            "phone": "9876543210",
            "address": "B12 Gandhi Street MG Road",
            "gender": "male"
        }
    }
    resp = client.post("/api/v1/verification/verify", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "fields" in data
    assert "field_scores" not in data
    assert set(data["fields"].keys()) >= {"name","dob","phone","address","gender"}
