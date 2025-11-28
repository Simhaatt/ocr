# ocr
mosip-ocr-project/
├── 📁 backend/
│   ├── app.py                 # Main Flask app initialization
│   ├── requirements.txt
│   ├── 📁 routes/             # API endpoints (separate files!)
│   │   ├── __init__.py
│   │   ├── extraction.py      # A1's endpoints
│   │   ├── mapping.py         # A2's endpoints  ✅ YOUR ENDPOINT FILE!
│   │   └── verification.py    # A3's endpoints
│   │
│   ├── 📁 core/               # Business logic (separate files!)
│   │   ├── __init__.py
│   │   ├── ocr.py            # A1's OCR logic
│   │   ├── mapper.py         # A2's mapping logic  ✅ YOUR LOGIC FILE!
│   │   └── verifier.py       # A3's verification logic
│   │
│   └── 📁 uploads/
│
└── 📁 frontend/            # TEAM B WORKSPACE (You)
    ├── index.html          # Your Single Page Application
    ├── styles.css          # Your Custom CSS
    ├── app.js              # API Calls & UI Logic
    └── 📁 assets/          # Images/Icons
