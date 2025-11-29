from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes.extraction import router as extraction_router
from .routes.mapping import router as mapping_router
from .routes.verification import router as verification_router

app = FastAPI(title="MOSIP OCR Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(extraction_router)
app.include_router(mapping_router)
app.include_router(verification_router)

@app.get("/health")
def health():
    return {"status": "ok"}

# Run with: python -m uvicorn backend.app:app --reload --port 5000
