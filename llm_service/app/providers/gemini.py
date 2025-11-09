# Esqueleto sin lógica real; levanta NotImplemented en cada método.

from ..schemas import (
    ToGrammarRequest, ToGrammarResponse,
    RecurrenceRequest, RecurrenceResponse,
    ClassifyRequest, ClassifyResponse,
    CompareRequest, CompareResponse,
)
from ..config import settings


class GeminiProvider:
    def __init__(self) -> None:
        self.model = settings.GEMINI_MODEL
        self.api_key = settings.GEMINI_API_KEY
        self.timeout = settings.GEMINI_TIMEOUT
        # TODO: inicializar cliente google-generativeai cuando implementemos

    async def to_grammar(self, req: ToGrammarRequest) -> ToGrammarResponse:
        raise NotImplementedError("to-grammar (Gemini) pendiente de implementación")

    async def recurrence(self, req: RecurrenceRequest) -> RecurrenceResponse:
        raise NotImplementedError("recurrence (Gemini) pendiente de implementación")

    async def classify(self, req: ClassifyRequest) -> ClassifyResponse:
        raise NotImplementedError("classify (Gemini) pendiente de implementación")

    async def compare(self, req: CompareRequest) -> CompareResponse:
        raise NotImplementedError("compare (Gemini) pendiente de implementación")
