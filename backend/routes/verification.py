from fastapi import APIRouter, Body
from ..core.verifier import verify

router = APIRouter(prefix="/api/verification", tags=["verification"])

@router.get("/ping")
def ping():
    return {"service": "verification", "status": "ok"}

@router.post("/run")
def run_verification(payload: dict = Body(default={})):
    ocr_data = payload.get("ocr", {})
    user_data = payload.get("user", {})
    result = verify(ocr_data, user_data)
    return result
