from fastapi import APIRouter

router = APIRouter()

@router.get("", summary="Healthcheck")
def health():
    return {"status": "ok", "service": "llm_service"}
