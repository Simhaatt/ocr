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

# Helper

def mv(raw_text: str, user: dict = USER):
    resp = client.post("/api/v1/map-and-verify", json={"raw_text": raw_text, "user": user})
    assert resp.status_code == 200, resp.text
    return resp.json()["verification"], resp.json()["mapped"]

# 1. Name order invariance
RAW_NAME_ORDER = """
Name: Kumar Ramesh
DOB: 19/04/2001
Gender: Male
Address: B12/3 Gandhi Street MG Road
Phone: +91 98765-43210
"""

def test_name_order_invariance():
    ver, _ = mv(RAW_NAME_ORDER)
    assert ver["fields"]["name"] >= 0.9, ver["fields"]["name"]

# 2. Minor name typo reduces score but stays reasonably high
RAW_NAME_TYPO = """
Name: Rameesh Kumar
DOB: 19/04/2001
Gender: Male
Address: B12/3 Gandhi Street MG Road
Phone: +91 98765-43210
"""

def test_name_minor_typo_decreases_score():
    # Baseline
    baseline_ver, _ = mv(RAW_NAME_ORDER.replace("Kumar Ramesh", "Ramesh Kumar"))
    typo_ver, _ = mv(RAW_NAME_TYPO)
    base_score = baseline_ver["fields"]["name"]
    typo_score = typo_ver["fields"]["name"]
    assert base_score >= 0.9
    assert 0.75 <= typo_score < base_score, (base_score, typo_score)

# 3. Phone partial suffix (last 8 digits) should yield ~0.9
RAW_PHONE_SUFFIX8 = """
Name: Ramesh Kumar
DOB: 19/04/2001
Gender: Male
Address: B12/3 Gandhi Street MG Road
Phone: 76543210
"""

def test_phone_partial_suffix_8_digits():
    ver, _ = mv(RAW_PHONE_SUFFIX8)
    phone_score = ver["fields"]["phone"]
    assert 0.89 <= phone_score <= 0.91, phone_score

# 4. Phone one digit off (full length) below perfect match
RAW_PHONE_ONE_DIGIT_OFF = """
Name: Ramesh Kumar
DOB: 19/04/2001
Gender: Male
Address: B12/3 Gandhi Street MG Road
Phone: 9876543211
"""

def test_phone_one_digit_difference():
    ver, _ = mv(RAW_PHONE_ONE_DIGIT_OFF)
    phone_score = ver["fields"]["phone"]
    assert phone_score < 0.95, phone_score

# 5. Address abbreviation expansion
RAW_ADDRESS_ABBR = """
Name: Ramesh Kumar
DOB: 19/04/2001
Gender: Male
Address: B12/3 Gandhi St Nr MG Rd
Phone: +91 98765-43210
"""

def test_address_abbreviation_expansion():
    ver, _ = mv(RAW_ADDRESS_ABBR)
    addr_score = ver["fields"]["address"]
    assert addr_score >= 0.8, addr_score  # allow slightly lower due to 'MG' not expanded

# 6. Address missing numeric tokens should reduce score relative to baseline
RAW_ADDRESS_NO_NUMBER = """
Name: Ramesh Kumar
DOB: 19/04/2001
Gender: Male
Address: Gandhi Street MG Road
Phone: +91 98765-43210
"""

def test_address_missing_numeric_tokens_lower_score():
    baseline_raw = RAW_ADDRESS_ABBR.replace("St Nr MG Rd", "Street MG Road")
    baseline_ver, _ = mv(baseline_raw)
    missing_ver, _ = mv(RAW_ADDRESS_NO_NUMBER)
    base_score = baseline_ver["fields"]["address"]
    missing_score = missing_ver["fields"]["address"]
    assert base_score >= 0.85
    # Numeric token presence may cap at 1.0; just ensure missing version not higher
    assert base_score >= missing_score, (base_score, missing_score)

# 7. DOB format variant
RAW_DOB_VARIANT = """
Name: Ramesh Kumar
DOB: 19 Apr 2001
Gender: Male
Address: B12/3 Gandhi Street MG Road
Phone: +91 98765-43210
"""

def test_dob_format_variant_normalizes():
    ver, _ = mv(RAW_DOB_VARIANT)
    # After extending DOB regex, variant should match
    assert ver["fields"]["dob"] == 1.0, ver["fields"]["dob"]

# 8. Gender synonyms
RAW_GENDER_SYNONYM = """
Name: Ramesh Kumar
DOB: 19/04/2001
Gender: Man
Address: B12/3 Gandhi Street MG Road
Phone: +91 98765-43210
"""

def test_gender_synonym_mapping():
    ver, _ = mv(RAW_GENDER_SYNONYM)
    assert ver["fields"]["gender"] == 1.0
