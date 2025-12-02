# backend/routes/verification.py
"""
FastAPI router for A3 verification.
Thin API layer that:
 - validates request with Pydantic
 - maps common/variant keys from A2 to canonical keys
 - calls core.verifier.aggregate_confidence() and decision_from_confidence()
 - logs requests/results to a JSONL file for tuning
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
import logging
import json
from datetime import datetime, UTC
import os

# Import your core verification logic (make sure path is correct)
# core/verifier.py must expose: aggregate_confidence, decision_from_confidence
from ..core.verifier import aggregate_confidence, decision_from_confidence

router = APIRouter(prefix="/verification", tags=["verification"])

# ----------------------------
# Pydantic models (request / response)
# ----------------------------
class VerifyRequest(BaseModel):
    """
    Expected request:
    {
      "ocr": { "name": "...", "dob": "...", "phone": "...", "address": "...", "gender": "..." },
      "user": { ... same keys ... },
      "weights": { optional override }
    }
    """
    ocr: Dict[str, Any]
    user: Dict[str, Any]
    weights: Optional[Dict[str, float]] = None

class VerifyResponse(BaseModel):
    overall_confidence: float
    decision: str
    fields: Dict[str, float]
    notes: Optional[list]
    version: str

# ----------------------------
# Common key mapping helper
# Accepts common alternative keys that A2 might send (english + some hindi variants)
# ----------------------------
COMMON_KEY_MAP = {
    # English variants
    "full_name": "name",
    "given_name": "name",
    "first_name": "name",
    "last_name": "surname",
    "mobile": "phone",
    "phone_no": "phone",
    "phoneNumber": "phone",
    "phoneNumberE164": "phone",
    "date_of_birth": "dob",
    "birth_date": "dob",
    
}

def map_input_keys(d: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map alternative keys to canonical keys expected by core.verifier.
    Leaves unknown keys as-is (so forward-compatible).
    """
    if not d:
        return {}
    out = {}
    for k, v in d.items():
        canonical = COMMON_KEY_MAP.get(k, k)
        out[canonical] = v
    return out

# ----------------------------
# Logging helper (append JSONL)
# ----------------------------
LOG_FILE = os.path.join(os.path.dirname(__file__), "..", "verification_requests.jsonl")
# Ensure directory exists
try:
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
except Exception:
    pass

def log_request(ocr: Dict[str, Any], user: Dict[str, Any], response: Dict[str, Any]) -> None:
    """
    Append JSONL entry with timestamp, raw ocr, user, and response.
    Use ensure_ascii=False to keep unicode (Hindi) readable.
    """
    try:
        entry = {
            "ts": datetime.now(UTC).isoformat(),
            "ocr": ocr,
            "user": user,
            "response": response
        }
        # open in append mode
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        logging.exception("Failed to write verification log")

# ----------------------------
# Main endpoint
# ----------------------------
@router.post("/verify", response_model=VerifyResponse)
def verify_endpoint(req: VerifyRequest):
    """
    POST /verification/verify
    Body: VerifyRequest
    Returns: VerifyResponse
    """
    try:
        # Map keys in both ocr and user payloads so A2/frontend can use variants
        ocr = map_input_keys(req.ocr or {})
        user = map_input_keys(req.user or {})
        weights = req.weights if req.weights is not None else None

        # Call core A3 logic (pure functions)
        # Pass weights only if provided; aggregate_confidence expects a dict or defaults internally
        final_score, field_scores, notes = aggregate_confidence(ocr, user, weights if weights else None)

        # Optional age consistency note (mirror map-and-verify behavior)
        # Age does not affect scoring; purely informational.
        if ocr.get("dob") and ocr.get("age"):
            dob_norm = str(ocr["dob"]).strip()
            parsed = None
            for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%y", "%d/%m/%y"):
                try:
                    parsed = datetime.strptime(dob_norm.replace('/', '-'), fmt.replace('/', '-')).date()
                    break
                except Exception:
                    continue
            if parsed:
                today = datetime.now(UTC).date()
                derived_age = int((today - parsed).days / 365.25)
                try:
                    stated_age = int(ocr["age"])
                    if abs(derived_age - stated_age) > 1:
                        notes.append(f"age_mismatch(derived={derived_age}, stated={stated_age})")
                except ValueError:
                    notes.append("age_parse_error")
        decision = decision_from_confidence(final_score)

        response = {
            "overall_confidence": round(final_score, 4),
            "decision": decision,
            "fields": {k: round(v, 4) for k, v in field_scores.items()},
            "notes": notes,
            "version": "a3-v1"
        }

        # Log request + response for offline tuning/analysis
        try:
            log_request(ocr, user, response)
        except Exception:
            # logging already handled inside log_request
            pass

        return response

    except Exception as exc:
        logging.exception("Verification endpoint error")
        # In development it's useful to return the exception text; in production prefer a generic message
        raise HTTPException(status_code=500, detail=f"Verification failed: {str(exc)}")

# ----------------------------
# Quick example endpoint (manual testing)
# ----------------------------
@router.get("/example")
def example():
    """
    GET /verification/example
    Returns: a sample verification run using built-in sample data.
    Useful for quick smoke tests in the browser.
    """
    ocr = {"name":"Ramesh Kumaar","dob":"19/04/2001","phone":"+91 98765-43210","address":"Flat No B-12/3 Gandhi St.","gender":"Male"}
    user = {"name":"Ramesh Kumar","dob":"19-04-2001","phone":"9876543210","address":"B12 Gandhi Street MG Road","gender":"male"}
    final, scores, notes = aggregate_confidence(ocr, user)
    decision = decision_from_confidence(final)
    return {
        "overall_confidence": round(final,4),
        "decision": decision,
        "fields": {k: round(v,4) for k,v in scores.items()},
        "notes": notes,
        "version": "a3-v1"
    }
