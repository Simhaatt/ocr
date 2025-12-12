from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes.extraction import router as extraction_router
from .routes.mapping import router as mapping_router
from .routes.verification import router as verification_router
from .routes.mosip import router as mosip_router

app = FastAPI(title="MOSIP OCR Field Extraction API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(extraction_router, prefix="/api/v1")
app.include_router(mapping_router, prefix="/api/v1")
app.include_router(verification_router, prefix="/api/v1")
app.include_router(mosip_router, prefix="/api/v1")
# API overview

@app.get("/")
def home():
    return {
        "message": "MOSIP OCR System API",
        "endpoints": {
            "A1 - OCR Extraction": {
                "extract_text": "POST /api/v1/ocr/extract-text",
                "extract_and_map": "POST /api/v1/ocr/extract-and-map",
                "health": "GET /api/v1/ocr/health",
            },
            "A2 - Field Mapping (YOU)": {
                "extract_fields": "POST /api/v1/extract-fields",
                "map_and_verify": "POST /api/v1/map-and-verify",
                "health": "GET /api/v1/health",
            },
            "A3 - Verification": {
                "verify": "POST /api/v1/verification/verify",
                "example": "GET /api/v1/verification/example",
            },
        },
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
