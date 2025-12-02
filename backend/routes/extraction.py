"""
A1 - OCR Extraction API Endpoints
Provides OCR services for both images and PDFs
"""
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional
import tempfile
import os

# Import A1's OCR logic
from ..core.ocr import process_input
from ..core.mapper import field_mapper

router = APIRouter(prefix="/ocr", tags=["OCR Extraction"])

class OCRResponse(BaseModel):
    status: str
    extracted_text: str
    file_type: str

@router.post("/extract-text", response_model=OCRResponse)
async def extract_text_from_file(file: UploadFile = File(...)):
    """
    Extract text from uploaded image or PDF
    
    - **file**: Image or PDF file
    
    Returns raw extracted text for A2 to process
    """
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        try:
            # Process with A1's OCR logic
            extracted_text = process_input(tmp_path)
            
            # Determine file type
            file_ext = os.path.splitext(file.filename)[1].lower()
            file_type = "pdf" if file_ext == ".pdf" else "image"
            
            return OCRResponse(
                status="success",
                extracted_text=extracted_text,
                file_type=file_type
            )
            
        finally:
            # Clean up temp file
            os.unlink(tmp_path)
            
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"OCR extraction failed: {str(e)}"
        )

@router.post("/extract-and-map")
async def extract_and_map(file: UploadFile = File(...)):
    """
    Combined endpoint: OCR extraction + A2 field mapping in one call
    
    - **file**: Image or PDF file
    
    Returns both raw text and mapped fields
    """
    try:
        # First, extract text using A1's OCR (reuse local function to avoid self-HTTP deadlock)
        # Save file temporarily and call process_input
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name

        try:
            extracted_text = process_input(tmp_path)
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

        # Then map fields locally via field_mapper (A2 logic as library)
        extracted_fields = field_mapper.extract_fields(extracted_text or "")
        missing_fields = field_mapper.get_missing_fields(extracted_fields)

        return {
            "status": "success",
            "ocr_extraction": {
                "raw_text": extracted_text,
                "file_type": (os.path.splitext(file.filename)[1].lower() == ".pdf") and "pdf" or "image",
            },
            "field_extraction": {
                "status": "success",
                "extracted_fields": extracted_fields,
                "fields_count": len(extracted_fields),
                "missing_fields": missing_fields,
            },
        }
            
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Extract and map failed: {str(e)}"
        )

@router.get("/health")
async def health_check():
    """Health check for OCR service"""
    return {
        "status": "healthy",
        "service": "ocr-extraction"
    }
