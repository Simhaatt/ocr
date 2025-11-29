from fastapi import APIRouter, Body

router = APIRouter(prefix="/api/extraction", tags=["extraction"])

@router.get("/ping")
def ping():
    return {"service": "extraction", "status": "ok"}

@router.post("/run")
def run_extraction(payload: dict = Body(default={})):
    # Placeholder: extract text from uploaded file
    return {"extracted": "<text>", "input_meta": payload}
