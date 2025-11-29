import pytest
from backend.core.verifier import (
    name_score,
    address_score,
    phone_score,
    dob_score,
    aggregate_confidence,
)


def test_exact_match():
    ocr = {"name":"A B", "dob":"2000-01-01", "phone":"1234567890", "address":"10 Road St", "gender":"male"}
    user= {"name":"A B", "dob":"2000-01-01", "phone":"1234567890", "address":"10 Road Street", "gender":"Male"}
    final, fields, _ = aggregate_confidence(ocr, user)
    assert final >= 0.95


def test_near_match():
    assert name_score("Ramesh Kumaar", "Ramesh Kumar") >= 0.9


def test_mismatch():
    ocr = {"name":"Alice", "dob":"01/01/1990", "phone":"5551112222", "address":"123 Main St", "gender":"female"}
    user= {"name":"Bob",   "dob":"02/02/1991", "phone":"9998887777", "address":"99 Elm Ave", "gender":"male"}
    final, _, _ = aggregate_confidence(ocr, user)
    assert final < 0.6


def test_phone_country_code():
    assert phone_score("+91 98765 43210", "9876543210") == pytest.approx(1.0)


def test_dob_variants():
    assert dob_score("19/04/2001", "19-04-2001") == 1.0
