from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional

from core.mapper import field_mapper

router = APIRouter(tags=["Field Extraction"])


class ExtractionRequest(BaseModel):
    raw_text: str
    document_type: Optional[str] = "general"

class ExtractionResponse(BaseModel):
    status: str
    extracted_fields: Dict[str, str]
    fields_count: int
    missing_fields: List[str]

@router.post("/extract-fields", response_model=ExtractionResponse)
async def extract_fields(request: ExtractionRequest):
   
    try:
       
        extracted_data = field_mapper.extract_fields(request.raw_text)
        missing_fields = field_mapper.get_missing_fields(extracted_data)
        
        return ExtractionResponse(
            status="success",
            extracted_fields=extracted_data,
            fields_count=len(extracted_data),
            missing_fields=missing_fields
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "field-extraction"}
