from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
from datetime import datetime, date

from ..core.mapper import field_mapper
from ..core.verifier import verify

router = APIRouter(tags=["Field Extraction"])


class ExtractionRequest(BaseModel):
    raw_text: str
    document_type: Optional[str] = "general"

class ExtractionResponse(BaseModel):
    status: str
    extracted_fields: Dict[str, str]
    fields_count: int
    missing_fields: List[str]

class MapAndVerifyRequest(BaseModel):
    raw_text: str
    user: Dict[str, str]

class MapAndVerifyResponse(BaseModel):
    status: str
    mapped: Dict[str, str]
    missing_fields: List[str]
    verification: Dict[str, object]

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

@router.post("/map-and-verify", response_model=MapAndVerifyResponse)
async def map_and_verify(req: MapAndVerifyRequest):
    try:
        mapped = field_mapper.extract_fields(req.raw_text)
        missing = field_mapper.get_missing_fields(mapped)
        # Only pass relevant verification keys
        ocr_subset = {k: v for k, v in mapped.items() if k in ("name", "dob", "phone", "address", "gender")}
        user_subset = {k: v for k, v in req.user.items() if k in ("name", "dob", "phone", "address", "gender")}
        verification = verify(ocr_subset, user_subset)

        # Age consistency note (auxiliary; does not affect scoring)
        if mapped.get("dob") and mapped.get("age"):
            dob_norm = mapped["dob"].strip()
            # Try multiple date formats already handled in verifier; reuse normalization by simple parse attempts
            parsed = None
            for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%y", "%d/%m/%y"):
                try:
                    parsed = datetime.strptime(dob_norm.replace('/', '-'), fmt.replace('/', '-')).date()
                    break
                except Exception:
                    continue
            if parsed:
                today = date.today()
                derived_age = int((today - parsed).days / 365.25)
                try:
                    stated_age = int(mapped["age"])
                    if abs(derived_age - stated_age) > 1:
                        verification.setdefault("notes", []).append(
                            f"age_mismatch(derived={derived_age}, stated={stated_age})"
                        )
                except ValueError:
                    verification.setdefault("notes", []).append("age_parse_error")
        return MapAndVerifyResponse(
            status="success",
            mapped=mapped,
            missing_fields=missing,
            verification=verification
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Map+Verify failed: {e}")

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "field-extraction"}
