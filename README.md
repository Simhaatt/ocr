# ocr
mosip-ocr-project/
├── 📁 backend/
│   ├── app.py                 # Main Flask app initialization
│   ├── requirements.txt
│   ├── 📁 routes/             # API endpoints (separate files!)
│   │   ├── __init__.py
│   │   ├── extraction.py      # A1's endpoints
│   │   ├── mapping.py         # A2's endpoints  
│   │   └── verification.py    # A3's endpoints
│   │
│   ├── 📁 core/               # Business logic (separate files!)
│   │   ├── __init__.py
│   │   ├── ocr.py            # A1's OCR logic
│   │   ├── mapper.py         # A2's mapping logic  
│   │   └── verifier.py       # A3's verification logic
│   │
│   └── 📁 uploads/
│
└── 📁 frontend/            # TEAM B WORKSPACE (You)
     ├── index.html          # Your Single Page Application
     ├── styles.css          # Your Custom CSS
     ├── app.js              # API Calls & UI Logic
     └── 📁 assets/          # Images/Icons

## Testing

This project uses `pytest` for minimal verification of mapper + verifier integration.

Current tests (combined in `tests/test_age_note.py`):
- `test_age_mismatch_note`: Ensures an `age_mismatch(...)` note is added when the stated age differs from the age derived from `DOB` by more than 1 year.
- `test_age_consistent_no_mismatch`: Verifies no `age_mismatch` note is produced when the stated age matches the derived age (computed dynamically to avoid drifting with time).

### Running Tests

1. Activate the virtual environment (if present):
    ```powershell
    .\.venv\Scripts\Activate.ps1
    ```
2. Install backend dependencies:
    ```powershell
    python -m pip install -r backend\requirements.txt
    ```
3. Run pytest:
    ```powershell
    python -m pytest -q
    ```

### Notes
- Age is not part of the verification confidence score; it only contributes informational notes.
- The test file derives the expected age from the DOB to remain stable over time.
- Add more tests if field coverage (e.g., address/phone edge cases) becomes necessary.
