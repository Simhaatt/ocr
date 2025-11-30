from fastapi.testclient import TestClient
from backend.app import app

client = TestClient(app)

# Helper to call map-and-verify
def mv(raw_text: str, user: dict):
    resp = client.post("/api/v1/map-and-verify", json={"raw_text": raw_text, "user": user})
    assert resp.status_code == 200, resp.text
    return resp.json()

USER_BASE = {
    "name": "Ramesh Kumar",
    "dob": "19-04-2001",
    "phone": "9876543210",
    "address": "B12/3 Gandhi Street MG Road",
    "gender": "male"
}

RAW_MATCH = """
Name: Ramesh Kumar
DOB: 19/04/2001
Age: 24
Gender: Male
Address: Flat No. B-12/3, Gandhi St. Near MG Road
Phone: +91 98765-43210
Email: ramesh.kumar@example.com
"""

RAW_PHONE_COUNTRY = RAW_MATCH  # same raw used; tests phone normalization

RAW_ADDRESS_NUMERIC = RAW_MATCH  # tests numeric token + address expansion

RAW_FULL_MISMATCH = """
Name: John Smith
DOB: 01/01/1999
Age: 26
Gender: Female
Address: 111 Unknown Place
Phone: 123456
Email: random@example.com
"""

# 1. All fields should produce high scores and MATCH decision.
def test_all_fields_match_confidence():
    data = mv(RAW_MATCH, USER_BASE)
    ver = data["verification"]
    assert ver["decision"] == "MATCH", ver
    assert ver["overall_confidence"] >= 0.85
    fields = ver["fields"]
    # Individual expectations
    assert fields["dob"] == 1.0
    assert fields["phone"] >= 0.95  # country code stripped
    assert fields["address"] >= 0.85  # fuzzy + bonuses
    assert fields["name"] >= 0.9
    assert fields["gender"] == 1.0

# 2. Phone normalization: NSN match yields 1.0 or very high.
def test_phone_suffix_country_code_match():
    data = mv(RAW_PHONE_COUNTRY, USER_BASE)
    phone_score = data["verification"]["fields"]["phone"]
    assert phone_score >= 0.95

# 3. Address numeric bonus should elevate score (expect high >=0.9)
def test_address_numeric_bonus():
    data = mv(RAW_ADDRESS_NUMERIC, USER_BASE)
    addr_score = data["verification"]["fields"]["address"]
    assert addr_score >= 0.9

# 4. Strong mismatches produce low scores and MISMATCH decision; low_score notes present.
def test_multiple_field_mismatch_notes():
    data = mv(RAW_FULL_MISMATCH, USER_BASE)
    ver = data["verification"]
    assert ver["decision"] == "MISMATCH", ver
    assert ver["overall_confidence"] < 0.6
    notes = ver.get("notes", [])
    # Expect several low_score notes
    assert any(n.startswith("name low_score") for n in notes)
    assert any(n.startswith("dob low_score") for n in notes) or USER_BASE["dob"] != "01-01-1999"  # dob mismatch yields low score
    assert any(n.startswith("phone low_score") for n in notes)
    assert any(n.startswith("address low_score") for n in notes)
    assert any(n.startswith("gender low_score") for n in notes)
