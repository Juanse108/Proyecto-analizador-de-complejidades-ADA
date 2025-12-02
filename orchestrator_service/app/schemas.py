"""
Esquemas Pydantic para el Orquestador.
Reutiliza estructuras de otros servicios.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# ENTRADA AL ORQUESTADOR
# ---------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    """Solicitud de análisis completo."""
    code: str = Field(..., description="Código o pseudocódigo a analizar")
    objective: str = Field(default="worst", description="worst, best o average")


# ---------------------------------------------------------------------------
# ESQUEMAS DEL PARSER SERVICE
# ---------------------------------------------------------------------------

class ParseResp(BaseModel):
    """Respuesta del servicio de Parsing."""
    ok: bool
    ast: Optional[dict] = None
    errors: Optional[List[str]] = None


class SemReq(BaseModel):
    """Solicitud de análisis semántico."""
    ast: dict


# ---------------------------------------------------------------------------
# ESQUEMAS DEL ANALYZER SERVICE
# ---------------------------------------------------------------------------

class AnalyzeAstReq(BaseModel):
    """Solicitud de análisis de complejidad."""
    ast_sem: dict
    objective: str = "worst"
    cost_model: Optional[dict] = None


class AnalyzerResult(BaseModel):
    """Resultado del análisis de complejidad."""
    big_o: str
    big_omega: str
    theta: str
    ir: Optional[str] = None
    notes: Optional[List[str]] = None


# ---------------------------------------------------------------------------
# RESPUESTA FINAL DEL ORQUESTADOR
# ---------------------------------------------------------------------------

class OrchestratorResponse(BaseModel):
    """Respuesta completa del pipeline de análisis."""
    normalized_code: str = Field(..., description="Código normalizado por el LLM")
    big_o: str = Field(..., description="Cota superior O(n)")
    big_omega: str = Field(..., description="Cota inferior Ω(n)")
    theta: str = Field(..., description="Cota ajustada Θ(n)")
    ir: Optional[str] = Field(default=None, description="Información adicional")
    notes: Optional[List[str]] = Field(default=None, description="Notas del análisis")