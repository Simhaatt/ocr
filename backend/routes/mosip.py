from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any
import json
import os
import tempfile
import logging
from ..core.mosip_client import MOSIPClient
from ..core.ocr import extract_text  # Import your existing OCR function
from ..core.verifier import verify_data  # Import your existing verification function

router = APIRouter(prefix="/mosip", tags=["MOSIP Pre-registration"])

logger = logging.getLogger(__name__)

# Initialize MOSIP client (configure with environment variables)
MOSIP_BASE_URL = os.getenv("MOSIP_BASE_URL", "https://sandbox.mosip.net")
MOSIP_AUTH_TOKEN = os.getenv("MOSIP_AUTH_TOKEN", "")

if not MOSIP_AUTH_TOKEN:
    print("⚠️ WARNING: MOSIP_AUTH_TOKEN not set in .env file")
    print("   Add 'MOSIP_AUTH_TOKEN=your_token_here' to .env file")
    print("   MOSIP integration will fail without a valid token")
    logger.warning("MOSIP_AUTH_TOKEN not set. MOSIP integration will fail.")

mosip_client = MOSIPClient(MOSIP_BASE_URL, MOSIP_AUTH_TOKEN)

@router.post("/integrate", summary="Complete OCR → Verification → MOSIP Registration")
async def integrate_with_mosip(
    file: UploadFile = File(..., description="Document to process (PDF/PNG/JPG)"),
    manual_data: Optional[str] = Form(None, description="Optional manual data for verification"),
    verification_threshold: float = Form(0.85, description="Verification confidence threshold")
):
    """
    Complete workflow:
    1. Extract data from document using OCR
    2. Verify with manual data (if provided)
    3. Submit to MOSIP pre-registration
    4. Upload document to MOSIP
    """
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        logger.info(f"Processing file: {file.filename}")
        
        # Step 1: Extract data using OCR
        extracted_data = extract_text(tmp_path)
        
        if not extracted_data:
            raise HTTPException(status_code=400, detail="Failed to extract data from document")
        
        verification_results = {}
        
        # Step 2: Optional verification with manual data
        if manual_data:
            try:
                manual_dict = json.loads(manual_data)
                verification_results = verify_data(extracted_data, manual_dict)
                
                # Check verification threshold
                if not _passes_verification(verification_results, verification_threshold):
                    return JSONResponse(
                        status_code=400,
                        content={
                            "status": "verification_failed",
                            "message": "Data verification failed. Confidence below threshold.",
                            "extracted_data": extracted_data,
                            "verification_results": verification_results,
                            "threshold": verification_threshold
                        }
                    )
            except json.JSONDecodeError:
                logger.warning("Invalid manual_data JSON format")
        
        # Step 3: Submit to MOSIP
        try:
            pre_reg_response = mosip_client.create_pre_registration(extracted_data)
            
            # Extract pre-registration ID
            pre_reg_id = pre_reg_response.get('response', {}).get('preRegistrationId')
            
            if not pre_reg_id:
                logger.error(f"No pre-registration ID in response: {pre_reg_response}")
                return JSONResponse(
                    status_code=500,
                    content={
                        "status": "mosip_error",
                        "message": "MOSIP did not return a pre-registration ID",
                        "mosip_response": pre_reg_response,
                        "extracted_data": extracted_data
                    }
                )
            
            # Step 4: Upload document
            upload_response = mosip_client.upload_document(pre_reg_id, tmp_path)
            
            # Clean up temp file
            os.unlink(tmp_path)
            
            return {
                "status": "success",
                "message": "Successfully registered with MOSIP",
                "pre_registration_id": pre_reg_id,
                "extracted_data": extracted_data,
                "verification_results": verification_results,
                "pre_registration_response": pre_reg_response,
                "document_upload_response": upload_response,
                "next_steps": {
                    "check_status": f"/api/v1/mosip/status/{pre_reg_id}",
                    "mosip_portal": f"{MOSIP_BASE_URL}/pre-registration"
                }
            }
            
        except Exception as mosip_error:
            logger.error(f"MOSIP integration error: {str(mosip_error)}")
            return JSONResponse(
                status_code=502,
                content={
                    "status": "mosip_integration_error",
                    "message": f"Failed to integrate with MOSIP: {str(mosip_error)}",
                    "extracted_data": extracted_data,
                    "verification_results": verification_results
                }
            )
            
    except Exception as e:
        logger.error(f"Integration error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/verify-and-submit", summary="Verify extracted data and submit to MOSIP")
async def verify_and_submit_to_mosip(
    extracted_data: Dict[str, Any],
    manual_data: Optional[Dict[str, Any]] = None,
    skip_verification: bool = False
):
    """
    Verify already extracted data and submit to MOSIP.
    Useful when OCR extraction is done separately.
    """
    try:
        verification_results = {}
        
        if not skip_verification and manual_data:
            verification_results = verify_data(extracted_data, manual_data)
        
        # Submit to MOSIP
        pre_reg_response = mosip_client.create_pre_registration(extracted_data)
        
        return {
            "status": "success",
            "verification_results": verification_results,
            "pre_registration_response": pre_reg_response,
            "pre_registration_id": pre_reg_response.get('response', {}).get('preRegistrationId')
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{pre_reg_id}", summary="Get MOSIP pre-registration status")
async def get_mosip_status(pre_reg_id: str):
    """Check the status of a MOSIP pre-registration application"""
    try:
        status = mosip_client.get_application_status(pre_reg_id)
        return {
            "pre_registration_id": pre_reg_id,
            "status": status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/test", summary="Test MOSIP connection")
async def test_mosip_connection():
    """Test connectivity to MOSIP sandbox"""
    try:
        # Simple test - try to create a minimal application
        test_data = {
            "Name": "Test User",
            "Gender": "Male",
            "Date_of_Birth": "1990-01-01"
        }
        
        response = mosip_client.create_pre_registration(test_data)
        
        return {
            "status": "connected",
            "mosip_base_url": MOSIP_BASE_URL,
            "test_response": response
        }
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to connect to MOSIP: {str(e)}"
        )

@router.post("/batch-submit", summary="Submit multiple documents to MOSIP")
async def batch_submit_to_mosip(
    files: list[UploadFile] = File(..., description="Multiple documents to process"),
    verification_data: Optional[str] = Form(None, description="JSON array of verification data")
):
    """
    Process and submit multiple documents to MOSIP in batch.
    Returns individual results for each document.
    """
    results = []
    
    verification_list = []
    if verification_data:
        try:
            verification_list = json.loads(verification_data)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid verification_data JSON")
    
    for i, file in enumerate(files):
        try:
            # Process each file
            manual_data = verification_list[i] if i < len(verification_list) else None
            
            # Save file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp_file:
                content = await file.read()
                tmp_file.write(content)
                tmp_path = tmp_file.name
            
            # Extract data
            extracted_data = extract_text(tmp_path)
            
            # Submit to MOSIP
            pre_reg_response = mosip_client.create_pre_registration(extracted_data)
            pre_reg_id = pre_reg_response.get('response', {}).get('preRegistrationId')
            
            # Upload document if successful
            upload_response = {}
            if pre_reg_id:
                upload_response = mosip_client.upload_document(pre_reg_id, tmp_path)
            
            # Clean up
            os.unlink(tmp_path)
            
            results.append({
                "file": file.filename,
                "status": "success",
                "pre_registration_id": pre_reg_id,
                "extracted_data": extracted_data
            })
            
        except Exception as e:
            results.append({
                "file": file.filename,
                "status": "error",
                "error": str(e)
            })
    
    return {
        "batch_id": f"batch_{os.urandom(4).hex()}",
        "total_files": len(files),
        "successful": sum(1 for r in results if r["status"] == "success"),
        "failed": sum(1 for r in results if r["status"] == "error"),
        "results": results
    }

def _passes_verification(verification_results: Dict[str, float], threshold: float = 0.85) -> bool:
    """Check if verification scores meet threshold"""
    if not verification_results:
        return True
    
    for field, score in verification_results.items():
        if isinstance(score, (int, float)) and score < threshold:
            return False
    return True
