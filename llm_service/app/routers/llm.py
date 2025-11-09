from fastapi import APIRouter
from ..schemas import (
    ToGrammarRequest, ToGrammarResponse,
    RecurrenceRequest, RecurrenceResponse,
    ClassifyRequest, ClassifyResponse,
    CompareRequest, CompareResponse,
)
from ..providers.gemini import GeminiProvider

router = APIRouter()


def provider() -> GeminiProvider:
    # Instancia simple; si luego quieres singleton, lo movemos.
    return GeminiProvider()


@router.post("/to-grammar", response_model=ToGrammarResponse)
async def to_grammar(payload: ToGrammarRequest):
    return await provider().to_grammar(payload)


@router.post("/recurrence", response_model=RecurrenceResponse)
async def recurrence(payload: RecurrenceRequest):
    return await provider().recurrence(payload)


@router.post("/classify", response_model=ClassifyResponse)
async def classify(payload: ClassifyRequest):
    return await provider().classify(payload)


@router.post("/compare", response_model=CompareResponse)
async def compare(payload: CompareRequest):
    return await provider().compare(payload)
