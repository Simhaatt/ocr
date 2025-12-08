# MOSIP OCR Field Extraction & Verification

This project provides an end-to-end flow for document OCR, field mapping, and verification against an applicant form.

**Key Features**
- OCR via PaddleOCR for images and PDFs, with dynamic preprocessing and PDF rasterization
- Document-type aware field mapping (Aadhaar/Voter → Name, DL/Passport → Address, Birth/SLC → DOB, Handwritten → All)
- Robust normalization and fuzzy verification for names, addresses, phones, DOB, and gender
- Simple frontend to collect applicant details, upload docs, and review confidence
- Inline edit/save of extracted text per document on the review page; saving re-runs map+verify to refresh confidence scores

## Project Structure
- `backend/` FastAPI service
    - `core/ocr.py` OCR utilities: instance cache, preprocess, image/PDF handling
    - `core/mapper.py` Field mapping: regex + label-value fallback, doc-type filtering
    - `core/verifier.py` Normalization and scoring + aggregation and decision
    - `routes/` FastAPI routes for extraction, mapping, verification
    - `app.py` FastAPI app with CORS and router setup
- `frontend/` Static SPA
    - `index.html`, `styles.css`, `app.js`
- `tests/` Pytest suite for mapping/verification logic

## Requirements
Backend dependencies (see `backend/requirements.txt`):
- `fastapi`, `uvicorn`
- `paddleocr`
- `numpy`, `opencv-python`
- `PyMuPDF` (imported as `fitz`)
- `rapidfuzz` (optional but recommended)
- `unidecode`
- `pydantic`

## Setup
Create a virtual environment and install dependencies.

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r backend\requirements.txt
```

## Running
- Start the backend API (FastAPI + Uvicorn):

```powershell
cd backend
uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

- Serve the frontend (static):

```powershell
cd frontend
python -m http.server 5500
```

- Open the app at `http://127.0.0.1:5500/index.html`
- Backend docs: `http://127.0.0.1:8000/docs`

## API Overview
Base prefix: `/api/v1`

- OCR
    - `POST /api/v1/ocr/extract-text` → returns extracted raw text from uploaded file (`file`)
- Mapping + Verification
    - `POST /api/v1/extract-fields` → maps fields from `raw_text` (supports `document_type`)
    - `POST /api/v1/map-and-verify` → maps and verifies against `user`, filtered by `document_type`
- Direct Verification
    - `POST /api/v1/verification/verify` → verifies `ocr` vs `user` payloads

## Document-Type Behavior
- `aadhar` or `voter`: extract and show only `name`; confidence equals name match vs form
- `dl` or `passport`: extract and show only `address`; confidence equals address match
- `birth` or `slc`: extract and show only `dob`; confidence equals date match
- `handwritten`: show all fields found; confidence aggregates available fields

## Mapping Details (`backend/core/mapper.py`)
- Combines English and Hindi regex patterns for core fields
- Fallback label-value parser for lines like `Name: John Smith`, `Address: 123 Elm St`, `Phone number: 555-12345`, etc.
- Document-type filtering ensures the review displays only relevant fields
- Cleaning:
    - Phone → digits only (strip punctuation/spaces)
    - Email → lowercase, trim spaces, fix common typos (`qmail` → `gmail`)
    - Pincode → digits only, up to 6

## Verification Details (`backend/core/verifier.py`)
- Normalization:
    - Unicode (NFKD + transliteration via `unidecode`)
    - Names/Addresses → lowercase, punctuation removal, abbreviation expansion (e.g., `st.` → `street`), stopword removal
    - Phone → digits-only; NSN (last 10 digits) logic
    - DOB → parse common formats to ISO `YYYY-MM-DD`
- Scoring per field (0..1): name, address, phone, dob, gender
- Aggregation:
    - Weighted average over available fields (default weights: name 0.35, dob 0.30, phone 0.15, address 0.15, gender 0.05)
    - Decision thresholds: `MATCH (>=0.85)`, `REVIEW (>=0.6)`, else `MISMATCH`

## Frontend Details (`frontend/app.js`)
- Applicant form with required fields (all except Middle Name)
- Document uploads per type; processes OCR then mapping+verification
- Review panel shows mapped-only fields per doc type and confidence badge
- Edit/Save UX: only Edit on top; Save appears at bottom when editing applicant data
- Review page extracted-text panel now has Edit/Save to adjust OCR text per doc and recompute confidence

## Testing
- Run tests:

```powershell
pytest -q
```

## Notes
- If PaddleOCR flags differ across versions, `core/ocr.py` handles new vs old APIs.
- CORS is open by default; adjust `backend/app.py` for production.

## License
Proprietary project. Do not redistribute without permission.
