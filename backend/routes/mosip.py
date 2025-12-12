from __future__ import annotations

import json
import logging
import os
import tempfile
from typing import Any, Dict, Optional, List

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from ..core.mosip_client import MOSIPClient
from ..core.ocr import process_input as extract_text
from ..core.verifier import verify as verify_data
from ..core.mapper import field_mapper
from .verification import map_input_keys

router = APIRouter(prefix="/mosip", tags=["MOSIP Pre-registration"])
logger = logging.getLogger(__name__)

MOSIP_BASE_URL = os.getenv("MOSIP_BASE_URL", "https://sandbox.mosip.net")
MOSIP_AUTH_TOKEN = os.getenv("MOSIP_AUTH_TOKEN", "")

if not MOSIP_AUTH_TOKEN:
    logger.warning("MOSIP_AUTH_TOKEN not set. MOSIP integration will fail.")

mosip_client = MOSIPClient(MOSIP_BASE_URL, MOSIP_AUTH_TOKEN)


def _passes_verification(verification_results: Dict[str, Any], threshold: float = 0.85) -> bool:
    """Decide pass/fail using overall score when available, else field minimum."""
    if not verification_results:
        return True

    overall = verification_results.get("overall_confidence")
    if isinstance(overall, (int, float)):
        return overall >= threshold

    fields = verification_results.get("fields") or verification_results
    numeric_scores = [float(v) for v in fields.values() if isinstance(v, (int, float))]
    if not numeric_scores:
        return True
    return min(numeric_scores) >= threshold


@router.post("/integrate", summary="Complete OCR → Verification → MOSIP Registration")
async def integrate_with_mosip(
    file: UploadFile = File(..., description="Document to process (PDF/PNG/JPG)"),
    manual_data: Optional[str] = Form(None, description="Optional manual data for verification"),
    verification_threshold: float = Form(0.8, description="Verification confidence threshold"),
):
    """
    Workflow:
    1) OCR extract text from the document
    2) Optionally verify against provided manual data
    3) Submit to MOSIP pre-registration
    4) Upload the document
    """
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name

        logger.info("Processing file for MOSIP integration: %s", file.filename)

        extracted_data = extract_text(tmp_path)
        if not extracted_data:
            raise HTTPException(status_code=400, detail="Failed to extract data from document")

        # Map raw OCR text into structured fields before verification
        mapped_fields = field_mapper.extract_fields(extracted_data) if isinstance(extracted_data, str) else {}

        verification_results: Dict[str, Any] = {}
        if manual_data:
            try:
                raw_manual = json.loads(manual_data)
                manual_lower = { (k or "").lower(): v for k, v in raw_manual.items() }
                manual_dict = map_input_keys(manual_lower)

                # Verify only when we have overlapping fields extracted; otherwise skip blocking
                overlap = {k: v for k, v in mapped_fields.items() if k in manual_dict and v}
                if overlap:
                    user_overlap = {k: manual_dict[k] for k in overlap.keys() if manual_dict.get(k) not in (None, "")}
                    verification_results = verify_data(overlap, user_overlap)
                    if verification_results and not _passes_verification(verification_results, verification_threshold):
                        return JSONResponse(
                            status_code=400,
                            content={
                                "status": "verification_failed",
                                "message": "Data verification failed. Confidence below threshold.",
                                "extracted_data": extracted_data,
                                "mapped_fields": mapped_fields,
                                "manual_data": manual_dict,
                                "verification_results": verification_results,
                                "threshold": verification_threshold,
                            },
                        )
                else:
                    verification_results = {"status": "skipped", "reason": "no_overlap_fields"}
            except json.JSONDecodeError:
                logger.warning("Invalid manual_data JSON format")
            except Exception as err:
                logger.warning("Verification error: %s", err)

        try:
            pre_reg_response = mosip_client.create_pre_registration({"raw_text": extracted_data})
            pre_reg_id = pre_reg_response.get("response", {}).get("preRegistrationId")
            if not pre_reg_id:
                logger.error("No pre-registration ID returned: %s", pre_reg_response)
                return JSONResponse(
                    status_code=500,
                    content={
                        "status": "mosip_error",
                        "message": "MOSIP did not return a pre-registration ID",
                        "mosip_response": pre_reg_response,
                        "extracted_data": extracted_data,
                    },
                )

            upload_response = mosip_client.upload_document(pre_reg_id, tmp_path)
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
                    "mosip_portal": f"{MOSIP_BASE_URL}/pre-registration",
                },
            }
        except Exception as mosip_error:
            logger.error("MOSIP integration error: %s", mosip_error)
            return JSONResponse(
                status_code=502,
                content={
                    "status": "mosip_integration_error",
                    "message": f"Failed to integrate with MOSIP: {mosip_error}",
                    "extracted_data": extracted_data,
                    "verification_results": verification_results,
                },
            )
    except Exception as e:
        logger.error("Integration error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/verify-and-submit", summary="Verify extracted data and submit to MOSIP")
async def verify_and_submit_to_mosip(
    extracted_data: Dict[str, Any],
    manual_data: Optional[Dict[str, Any]] = None,
    skip_verification: bool = False,
):
    try:
        verification_results: Dict[str, Any] = {}
        if not skip_verification and manual_data:
            verification_results = verify_data(extracted_data, manual_data)

        pre_reg_response = mosip_client.create_pre_registration(extracted_data)
        return {
            "status": "success",
            "verification_results": verification_results,
            "pre_registration_response": pre_reg_response,
            "pre_registration_id": pre_reg_response.get("response", {}).get("preRegistrationId"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{pre_reg_id}", summary="Get MOSIP pre-registration status")
async def get_mosip_status(pre_reg_id: str):
    try:
        status = mosip_client.get_application_status(pre_reg_id)
        return {"pre_registration_id": pre_reg_id, "status": status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/test", summary="Test MOSIP connection")
async def test_mosip_connection():
    try:
        test_data = {"Name": "Test User", "Gender": "Male", "Date_of_Birth": "1990-01-01"}
        response = mosip_client.create_pre_registration(test_data)
        return {"status": "connected", "mosip_base_url": MOSIP_BASE_URL, "test_response": response}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to connect to MOSIP: {e}")


@router.post("/batch-submit", summary="Submit multiple documents to MOSIP")
async def batch_submit_to_mosip(
    files: List[UploadFile] = File(..., description="Multiple documents to process"),
    verification_data: Optional[str] = Form(None, description="JSON array of verification data"),
):
    results = []
    verification_list = []
    if verification_data:
        try:
            verification_list = json.loads(verification_data)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid verification_data JSON")

    for i, file in enumerate(files):
        try:
            manual_data = verification_list[i] if i < len(verification_list) else None
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp_file:
                content = await file.read()
                tmp_file.write(content)
                tmp_path = tmp_file.name

            extracted_data = extract_text(tmp_path)
            pre_reg_response = mosip_client.create_pre_registration({"raw_text": extracted_data})
            pre_reg_id = pre_reg_response.get("response", {}).get("preRegistrationId")
            upload_response = mosip_client.upload_document(pre_reg_id, tmp_path) if pre_reg_id else {}
            os.unlink(tmp_path)

            results.append(
                {
                    "file": file.filename,
                    "status": "success",
                    "pre_registration_id": pre_reg_id,
                    "extracted_data": extracted_data,
                    "manual_data": manual_data,
                    "upload": upload_response,
                }
            )
        except Exception as e:
            results.append({"file": file.filename, "status": "error", "error": str(e)})

    return {
        "batch_id": f"batch_{os.urandom(4).hex()}",
        "total_files": len(files),
        "successful": sum(1 for r in results if r["status"] == "success"),
        "failed": sum(1 for r in results if r["status"] == "error"),
        "results": results,
    }
