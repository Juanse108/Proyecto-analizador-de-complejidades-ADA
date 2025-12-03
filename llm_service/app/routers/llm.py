from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..schemas import (
    ToGrammarRequest, ToGrammarResponse,
    RecurrenceRequest, RecurrenceResponse,
    ClassifyRequest, ClassifyResponse,
    CompareRequest, CompareResponse,
)
from ..providers.gemini import GeminiProvider

router = APIRouter()


class ValidateGrammarRequest(BaseModel):
    """Petición para validar/corregir pseudocódigo."""
    pseudocode: str


class ValidateGrammarResponse(BaseModel):
    """Respuesta de validación/corrección de pseudocódigo."""
    corrected_pseudocode: str
    is_valid: bool
    issues: list


def provider() -> GeminiProvider:
    return GeminiProvider()


@router.post("/to-grammar", response_model=ToGrammarResponse)
async def to_grammar(payload: ToGrammarRequest):
    return await provider().to_grammar(payload)


@router.post("/validate-grammar", response_model=ValidateGrammarResponse)
async def validate_grammar(payload: ValidateGrammarRequest):
    """Valida y corrige pseudocódigo."""
    try:
        result = await provider().validate_grammar(payload.pseudocode)
        return ValidateGrammarResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recurrence", response_model=RecurrenceResponse)
async def recurrence(payload: RecurrenceRequest):
    return await provider().recurrence(payload)


@router.post("/classify", response_model=ClassifyResponse)
async def classify(payload: ClassifyRequest):
    return await provider().classify(payload)


@router.post("/compare", response_model=CompareResponse)
async def compare(payload: CompareRequest):
    return await provider().compare(payload)


@router.get("/health")
async def health():
    return {"status": "ok", "service": "llm"}
