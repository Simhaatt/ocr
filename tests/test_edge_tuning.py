from backend.core.verifier import verify


def test_phone_partial_6_digits():
    ocr = {"phone": "+91 9876543210"}
    user = {"phone": "6543210"}  # last 7 actually, ensure fallback lower than full
    r = verify(ocr, user)
    # Should not be full match but >= 0.80 due to 6/7 partial credit logic
    assert 0.80 <= r["fields"]["phone"] < 1.0


def test_mixed_script_address():
    ocr = {"address": "मकान 12 Gandhi Road"}
    user = {"address": "House 12 Gandhi Road"}
    r = verify(ocr, user)
    assert r["fields"]["address"] > 0.85


def test_name_middle_initial():
    ocr = {"name": "Ramesh A Kumar"}
    user = {"name": "Ramesh Kumar"}
    r = verify(ocr, user)
    assert r["fields"]["name"] > 0.9


def test_dob_mismatch_review_boundary():
    ocr = {"name": "Ramesh Kumar", "dob": "01/01/2000", "phone": "9876543210", "address": "12 Gandhi Road", "gender": "male"}
    user = {"name": "Ramesh Kumar", "dob": "02/01/2000", "phone": "9876543210", "address": "12 Gandhi Road", "gender": "male"}
    r = verify(ocr, user)
    # dob mismatches -> score 0 for dob (30% weight) others perfect => overall ~0.70 -> REVIEW
    assert r["decision"] == "REVIEW"
    assert 0.65 <= r["overall_confidence"] <= 0.75


def test_unknown_gender_exclusion():
    ocr = {"name": "Ramesh Kumar", "dob": "19/04/2001", "phone": "9876543210", "address": "12 Gandhi Road"}
    user = {"name": "Ramesh Kumar", "dob": "19/04/2001", "phone": "9876543210", "address": "12 Gandhi Road", "gender": "female"}
    r = verify(ocr, user)
    # gender missing on ocr side => excluded from weighting; remaining fields perfect => MATCH
    assert r["decision"] == "MATCH"
    assert r["overall_confidence"] > 0.85


def test_devanagari_digits_in_address():
    ocr = {"address": "मकान १२ गांधी रोड"}  # uses Devanagari digits for 12
    user = {"address": "House 12 Gandhi Road"}
    r = verify(ocr, user)
    # Allow slightly lower threshold due to semantic mismatch 'makan' vs 'house'
    assert r["fields"]["address"] >= 0.75
