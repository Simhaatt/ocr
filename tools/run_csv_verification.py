import csv
import sys
from pathlib import Path
from backend.core.verifier import verify

CSV_PATH = Path(__file__).resolve().parents[1] / "data" / "verification_samples.csv"


def main(csv_path=CSV_PATH):
    rows = []
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            ocr = {
                "name": r.get("name_ocr"),
                "dob": r.get("dob_ocr"),
                "phone": r.get("phone_ocr"),
                "address": r.get("address_ocr"),
                "gender": r.get("gender_ocr"),
            }
            user = {
                "name": r.get("name_user"),
                "dob": r.get("dob_user"),
                "phone": r.get("phone_user"),
                "address": r.get("address_user"),
                "gender": r.get("gender_user"),
            }
            res = verify(ocr, user)
            rows.append({
                "label": r.get("label"),
                "overall_confidence": res["overall_confidence"],
                "decision": res["decision"],
                **{f"field_{k}": v for k, v in res["fields"].items()},
            })
    # Print summary
    print("label,decision,overall_confidence,field_name,field_dob,field_phone,field_address,field_gender")
    for ri in rows:
        print(
            f"{ri['label']},{ri['decision']},{ri['overall_confidence']},"+
            f"{ri.get('field_name', '')},{ri.get('field_dob', '')},{ri.get('field_phone', '')},{ri.get('field_address', '')},{ri.get('field_gender', '')}"
        )


if __name__ == "__main__":
    arg = Path(sys.argv[1]) if len(sys.argv) > 1 else CSV_PATH
    main(arg)
