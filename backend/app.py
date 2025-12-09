from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes.extraction import router as extraction_router
from .routes.mapping import router as mapping_router
from .routes.verification import router as verification_router
from .routes.mosip import router as mosip_router  
from dotenv import load_dotenv
import os   

load_dotenv()  

app = FastAPI(
    title="MOSIP OCR Field Extraction API with Pre-registration Integration", 
    version="1.0.0",
    description="OCR system for text extraction, verification, and MOSIP pre-registration integration"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers
app.include_router(extraction_router, prefix="/api/v1")
app.include_router(mapping_router, prefix="/api/v1")
app.include_router(verification_router, prefix="/api/v1")
app.include_router(mosip_router, prefix="/api/v1/mosip")    

# API overview
@app.get("/")
async def home():
    return {
        "message": "MOSIP OCR System with Pre-registration Integration API",
        "version": "1.0.0",
        "endpoints": {
            "OCR Extraction": {
                "extract_text": "POST /api/v1/ocr/extract-text",
                "extract_and_map": "POST /api/v1/ocr/extract-and-map",
                "health": "GET /api/v1/ocr/health",
            },
            "Field Mapping": {
                "extract_fields": "POST /api/v1/extract-fields",
                "map_and_verify": "POST /api/v1/map-and-verify",
                "health": "GET /api/v1/health",
            },
            "Verification": {
                "verify": "POST /api/v1/verification/verify",
                "example": "GET /api/v1/verification/example",
            },
            "MOSIP Pre-registration": {  # NEW SECTION
                "integrate": "POST /api/v1/mosip/integrate",
                "verify_and_submit": "POST /api/v1/mosip/verify-and-submit",
                "status": "GET /api/v1/mosip/status/{pre_reg_id}",
                "test_connection": "GET /api/v1/mosip/test",
            },
        },
        "documentation": "/docs",
        "redoc": "/redoc",
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "mosip-ocr-api",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
