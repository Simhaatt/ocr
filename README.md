# ocr
mosip-ocr-project/
│
├── 📁 backend/             # TEAM A WORKSPACE
│   ├── venv/
│   ├── app.py              # The Flask Server (Main Entry Point)
│   ├── requirements.txt    # flask, flask-cors, opencv-python, easyocr, rapidfuzz
│   │
│   ├── 📁 core/            # The Logic Modules
│   │   ├── ocr.py          # (A1) OCR extraction logic
│   │   ├── mapper.py       # (A2) JSON mapping logic
│   │   └── verifier.py     # (A3) Verification logic
│   │
│   └── 📁 uploads/         # Temp folder to store uploaded ID cards
│
└── 📁 frontend/            # TEAM B WORKSPACE (You)
    ├── index.html          # Your Single Page Application
    ├── styles.css          # Your Custom CSS
    ├── app.js              # API Calls & UI Logic
    └── 📁 assets/          # Images/Icons
