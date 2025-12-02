from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes.extraction import router as extraction_router    
from .routes.mapping import router as mapping_router          
from .routes.verification import router as verification_router 

app = FastAPI(title="MOSIP OCR Field Extraction API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
)


app.include_router(mapping_router, prefix="/api/v1")
app.include_router(verification_router, prefix="/api/v1")
app.include_router(extraction_router, prefix="/api/v1")
#add A1 and A3 shit 

@app.get("/")
def home():
    return {
        "message": "MOSIP OCR Field Extraction API",
        "endpoints": {
            "A2 - Field Extraction": "POST /api/v1/extract-fields",
            "A3 - Verification": "POST /api/v1/verification/verify",
            "Health Check": "GET /api/v1/health"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
