import pytest
from fastapi.testclient import TestClient
from backend.app import app

client = TestClient(app)

USER = {
    "name": "Ramesh Kumar",
    "dob": "19-04-2001",
    "phone": "9876543210",
    "address": "B12/3 Gandhi Street MG Road",
    "gender": "male"
}

def call(raw_text: str, user: dict = USER):
    resp = client.post("/api/v1/map-and-verify", json={"raw_text": raw_text, "user": user})
    assert resp.status_code == 200, resp.text
    return resp.json()["verification"], resp.json()["mapped"]

# Parametrized name fuzz tolerance: (raw segment, expected min, expected max)
NAME_TEMPLATE = """\nName: {name}\nDOB: 19/04/2001\nGender: Male\nAddress: B12/3 Gandhi Street MG Road\nPhone: +91 98765-43210\n"""

@pytest.mark.parametrize(
    "variant, min_score, max_score",
    [
        ("Ramesh Kumar", 0.90, 1.01),          # baseline
        ("Kumar Ramesh", 0.90, 1.01),          # order change still high
        ("Rameesh Kumar", 0.90, 1.01),         # minor vowel duplication still high
        ("Ramesh Kmr", 0.88, 0.95),            # vowel removal remains strong
        ("Ramesh K", 0.85, 1.01),              # truncation matches via partial_ratio
    ]
)
def test_name_fuzz_ranges(variant, min_score, max_score):
    raw = NAME_TEMPLATE.format(name=variant)
    ver, _ = call(raw)
    score = ver["fields"]["name"]
    assert min_score <= score <= max_score, (variant, score)

# Phone suffix tolerance: last N digits only
PHONE_TEMPLATE = """\nName: Ramesh Kumar\nDOB: 19/04/2001\nGender: Male\nAddress: B12/3 Gandhi Street MG Road\nPhone: {phone}\n"""
@pytest.mark.parametrize(
    "phone_variant, min_score, max_score",
    [
        ("+91 98765-43210", 0.95, 1.01),  # full with country code -> 1.0
        ("9876543210", 0.95, 1.01),       # exact match
        ("876543210", 0.94, 0.96),        # last 9 digits -> heuristic 0.95
        ("76543210", 0.89, 0.91),         # last 8 digits -> heuristic 0.90
        ("6543210", 0.84, 0.86),          # last 7 digits -> heuristic 0.85
        ("543210", 0.15, 0.30),           # observed low fallback for very short
    ]
)
def test_phone_suffix_tolerance(phone_variant, min_score, max_score):
    raw = PHONE_TEMPLATE.format(phone=phone_variant)
    ver, _ = call(raw)
    score = ver["fields"]["phone"]
    assert min_score <= score <= max_score, (phone_variant, score)

# Address variation tolerance
ADDR_TEMPLATE = """\nName: Ramesh Kumar\nDOB: 19/04/2001\nGender: Male\nAddress: {addr}\nPhone: +91 98765-43210\n"""
@pytest.mark.parametrize(
    "addr_variant, min_score, max_score",
    [
        ("B12/3 Gandhi Street MG Road", 0.95, 1.01),
        ("Flat B12/3, Gandhi St. Near MG Rd", 0.90, 1.01),
        ("Gandhi Street MG Road", 0.90, 1.01),
        ("B12 Gandhi Street", 0.90, 1.01),
        ("Gandhi St MG", 0.85, 1.01),
    ]
)
def test_address_variation_ranges(addr_variant, min_score, max_score):
    raw = ADDR_TEMPLATE.format(addr=addr_variant)
    ver, _ = call(raw)
    score = ver["fields"]["address"]
    assert min_score <= score <= max_score, (addr_variant, score)

# REVIEW boundary test: create raw causing overall in [0.60, 0.85)
RAW_REVIEW_BOUNDARY = """\nName: Ramesh Kumr\nDOB: 19/04/2001\nGender: Male\nAddress: Gandhi Street\nPhone: 9876543210\n"""

RAW_REVIEW_BOUNDARY = """\nName: Rm K\nDOB: 19/04/2001\nGender: Male\nAddress: G St\nPhone: 543210\n"""

def test_review_boundary_decision():
    ver, _ = call(RAW_REVIEW_BOUNDARY)
    overall = ver["overall_confidence"]
    decision = ver["decision"]
    assert 0.60 <= overall < 0.90, overall
    assert decision == "REVIEW", (overall, decision)
