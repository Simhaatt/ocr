import os
import json

from backend.core.ocr import process_input, image_path as default_image_path
from backend.core.mapper import field_mapper
from backend.core.verifier import verify as verify_fields


def main():
    img_path = os.environ.get("OCR_IMAGE_PATH", default_image_path)
    print(f"[flow] Using image: {img_path}")

    # 1) OCR extraction
    text = process_input(img_path)
    print("\n[flow] Extracted text (first 500 chars):\n" + (text[:500] if text else "<empty>"))

    # 2) Field mapping
    mapped = field_mapper.extract_fields(text or "")
    print("\n[flow] Mapped fields:\n" + json.dumps(mapped, ensure_ascii=False, indent=2))

    # 3) Verification (self-compare as a placeholder)
    # If you want to compare with a reference/user object, set OCR_USER_JSON env var
    user_json = os.environ.get("OCR_USER_JSON")
    if user_json:
        try:
            user = json.loads(user_json)
            print("\n[flow] Using provided USER for verification")
        except Exception as e:
            print(f"[flow] Failed to parse OCR_USER_JSON: {e}; falling back to self-compare")
            user = mapped
    else:
        user = mapped

    result = verify_fields(mapped, user)
    print("\n[flow] Verification result:\n" + json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
