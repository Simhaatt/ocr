import pytest

from backend.core.verifier import dob_score


@pytest.mark.parametrize(
    "a,b,expected",
    [
        ("19/04/2001", "19-04-2001", 1.0),
        ("2001/04/19", "2001-04-19", 1.0),
        ("19 Apr 2001", "19-04-2001", 1.0),
        ("19-4-2001", "19/04/2001", 1.0),
        ("", "19/04/2001", 0.0),
        ("19/04/2001", "", 0.0),
        ("19/04/2001", "20/04/2001", 0.0),
    ],
)
def test_dob_score_formats_and_mismatch(a, b, expected):
    assert dob_score(a, b) == expected
