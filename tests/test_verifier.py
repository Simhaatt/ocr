import pytest

from backend.core.verifier import (
    normalize_full,
    address_score,
    phone_score,
    dob_score,
    name_score,
    aggregate_confidence,
)


def test_phone_country_code_matches():
    assert phone_score("+91 98765 43210", "9876543210") == pytest.approx(1.0)
    assert phone_score("0091-98765-43210", "09876543210") == pytest.approx(1.0)


def test_address_abbreviations_and_numbers():
    a = "Flat No. B-12/3, Gandhi St. (Near MG Rd)"
    b = "B12/3 Gandhi Street MG Road"
    s = address_score(a, b)
    assert s >= 0.9


def test_address_numeric_bonus():
    a = "Flat 23, Tower 9, Sector 14"
    b = "Twr 9, Sec 14, Flat No 23"
    s = address_score(a, b)
    assert s >= 0.9


def test_name_small_variation():
    assert name_score("Ramesh Kumaar", "Ramesh Kumar") >= 0.9


def test_dob_variants():
    assert dob_score("19/04/2001", "19-04-2001") == 1.0


def test_aggregate_example():
    ocr = {
        "name": "Ramesh Kumaar",
        "dob": "19/04/2001",
        "phone": "+91 98765-43210",
        "address": "Flat No. B-12/3, Gandhi St. (Near MG Road)",
        "gender": "Male",
    }
    user = {
        "name": "Ramesh Kumar",
        "dob": "19-04-2001",
        "phone": "9876543210",
        "address": "B12/3 Gandhi Street MG Road",
        "gender": "male",
    }
    final, fields, notes = aggregate_confidence(ocr, user)
    assert final >= 0.9
    assert fields["phone"] == pytest.approx(1.0)
    assert fields["address"] >= 0.9


def test_gender_synonyms():
    from backend.core.verifier import gender_score
    assert gender_score("M", "male") == 1.0
    assert gender_score("F", "Female") == 1.0
    assert gender_score("Other", "others") == 1.0


def test_phone_partial_suffix_credit():
    # 7-8-9 digit suffix alignment should yield partial credit
    from backend.core.verifier import phone_score
    assert phone_score("2125551212", "5551212") >= 0.85
    assert phone_score("+1 212-555-1212", "2125551212") >= 0.95


def test_aggregate_mismatch():
    from backend.core.verifier import verify
    ocr = {
        "name": "Alice Johnson",
        "dob": "01/01/1990",
        "phone": "+1 555 123 4567",
        "address": "123 Main Street",
        "gender": "female",
    }
    user = {
        "name": "Ramesh Kumar",
        "dob": "19-04-2001",
        "phone": "9876543210",
        "address": "99 Elm Avenue",
        "gender": "male",
    }
    result = verify(ocr, user)
    assert result["decision"] == "MISMATCH"
    assert result["overall_confidence"] < 0.6


def test_intentional_failure():
    """This test is intentionally wrong to demonstrate a failing build."""
    from backend.core.verifier import verify
    ocr = {
        "name": "Alice Johnson",
        "dob": "01/01/1990",
        "phone": "+1 555 123 4567",
        "address": "123 Main Street",
        "gender": "female",
    }
    user = {
        "name": "Ramesh Kumar",
        "dob": "19-04-2001",
        "phone": "9876543210",
        "address": "99 Elm Avenue",
        "gender": "male",
    }
    result = verify(ocr, user)
    # Intentionally incorrect expectation: this should be MISMATCH
    assert result["decision"] == "MATCH"
