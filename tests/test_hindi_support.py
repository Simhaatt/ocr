from backend.core.verifier import verify


def test_hindi_name_address_gender_match():
    ocr = {
        "name": "रमेश कुमार",
        "address": "मकान 12 गांधी रोड",
        "gender": "पुरुष"
    }
    user = {
        "name": "Ramesh Kumar",
        "address": "12 Gandhi Road",
        "gender": "male"
    }
    result = verify(ocr, user)
    assert result["fields"]["gender"] == 1.0
    assert result["fields"]["name"] > 0.9
    assert result["fields"]["address"] > 0.85
    assert result["decision"] in ("MATCH", "REVIEW")


def test_hindi_female_and_other():
    ocr = {"gender": "महिला"}
    user = {"gender": "female"}
    r1 = verify(ocr, user)
    assert r1["fields"]["gender"] == 1.0

    ocr2 = {"gender": "अन्य"}
    user2 = {"gender": "other"}
    r2 = verify(ocr2, user2)
    assert r2["fields"]["gender"] == 1.0
