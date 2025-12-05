"""
Esquemas Pydantic para el Orchestrator Service.

Define todas las estructuras de datos utilizadas en la comunicación
entre el Orchestrator y los microservicios, así como las estructuras
públicas para el cliente (Frontend).
"""

from pydantic import BaseModel, Field, field_validator
from typing import Any, List, Optional, Dict, Union


# ---------------------------------------------------------------------------
# ESTRUCTURAS PARA COMUNICACIÓN CON MICROSERVICIOS
# ---------------------------------------------------------------------------

# Estructura de respuesta del servicio Parser /parse
class ParseResp(BaseModel):
    """Respuesta del servicio Parser (parseo sintáctico)."""
    ok: bool = Field(..., description="Indica si el parseo sintáctico fue exitoso.")
    ast: Optional[Dict[str, Any]] = Field(
        None, 
        description="Árbol de Sintaxis Abstracta (AST) si el parseo fue exitoso."
    )
    errors: Optional[List[str]] = Field(
        default_factory=list, 
        description="Lista de errores de sintaxis."
    )


# Estructura de request para el servicio Parser /semantic
class SemReq(BaseModel):
    """Petición de análisis semántico al Parser."""
    ast: Dict[str, Any] = Field(..., description="AST del código a analizar.")


# Estructura de request para el servicio Analyzer /analyze-ast
class AnalyzeAstReq(BaseModel):
    """Petición de análisis de complejidad al Analyzer."""
    ast: Dict[str, Any] = Field(..., description="AST semánticamente validado.")
    objective: str = Field(
        "worst", 
        description="Objetivo de análisis: 'worst', 'best' o 'average'."
    )
    cost_model: Optional[Dict[str, Any]] = Field(
        None, 
        description="Modelo de costo opcional."
    )
# Estructura de respuesta del servicio Analyzer /analyze-ast
class AnalyzerResult(BaseModel):
    """Resultado del análisis de complejidad."""
    big_o: str = Field(..., description="Notación O (Cota Superior - Peor Caso).")
    big_omega: Optional[str] = Field(
        None, 
        description="Notación Ω (Cota Inferior - Mejor Caso)."
    )
    theta: Optional[str] = Field(
        None, 
        description="Notación Θ (Cota Ajustada - Caso Promedio)."
    )
    ir: Optional[Union[str, Dict[str, Any]]] = Field(
        None, 
        description="Representación Intermedia (IR) usada para el cálculo."
    )
    notes: Optional[Union[List[str], str]] = Field(
        None, 
        description="Notas o explicaciones del análisis."
    )
    # Nuevos campos del backend analyzer
    algorithm_kind: Optional[str] = Field(
        None,
        description="Tipo de algoritmo: 'recursive' o 'iterative'"
    )
    ir_worst: Optional[Dict[str, Any]] = Field(
        None,
        description="Representación IR del peor caso"
    )
    ir_best: Optional[Dict[str, Any]] = Field(
        None,
        description="Representación IR del mejor caso"
    )
    ir_avg: Optional[Dict[str, Any]] = Field(
        None,
        description="Representación IR del caso promedio"
    )
    lines: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Análisis línea por línea del código"
    )
    method_used: Optional[str] = Field(
        None,
        description="Método utilizado para el análisis"
    )
    strong_bounds: Optional[Dict[str, Any]] = Field(
        None,
        description="Fórmula explícita con cotas ajustadas"
    )
    summations: Optional[Dict[str, Dict[str, str]]] = Field(
        None,
        description="Sumatorias explícitas por caso (worst, best, avg). Cada caso contiene {latex, text}."
    )
    
    recurrence_equation: Optional[str] = Field(
        None,
        description="Ecuación de recurrencia completa (solo algoritmos recursivos)"
    )
    
    execution_trace: Optional[Dict[str, Any]] = Field(
        None,
        description="Diagrama de seguimiento de ejecución paso a paso (solo algoritmos iterativos)"
    )

    @field_validator('notes', mode='before')
    @classmethod
    def convert_notes_to_list(cls, v):
        """Convierte notes a lista si llega como string."""
        if isinstance(v, str):
            return [v]
        elif isinstance(v, list):
            return v
        elif v is None:
            return None
        return v
    
# ---------------------------------------------------------------------------
# ESTRUCTURAS PÚBLICAS PARA EL CLIENTE (FRONTEND)
# ---------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    """Petición de análisis enviada por el Frontend."""
    code: str = Field(
        ..., 
        description="Pseudocódigo o descripción en lenguaje natural a analizar."
    )
    objective: str = Field(
        "worst", 
        description="Objetivo de análisis: 'worst', 'best' o 'average'."
    )

    class Config:
        json_schema_extra = {
            "example": {
                "code": "for i <- 1 to n do begin for j <- 1 to n do begin print(i*j) end end",
                "objective": "worst"
            }
        }



class OrchestratorResponse(BaseModel):
    """Respuesta final del Orchestrator al Frontend."""
    normalized_code: str
    big_o: str
    big_omega: str
    theta: str
    ir: Optional[Dict[str, Any]] = None
    notes: Optional[List[str]] = None
    
    algorithm_kind: Optional[str] = None
    ir_worst: Optional[Dict[str, Any]] = None
    ir_best: Optional[Dict[str, Any]] = None
    ir_avg: Optional[Dict[str, Any]] = None
    lines: Optional[List[Dict[str, Any]]] = None
    method_used: Optional[str] = None
    strong_bounds: Optional[Dict[str, Any]] = None
    summations: Optional[Dict[str, Dict[str, str]]] = None
    
    recurrence_equation: Optional[str] = Field(
        None,
        description="Ecuación de recurrencia completa (solo algoritmos recursivos)"
    )
    
    execution_trace: Optional[Dict[str, Any]] = Field(
        None,
        description="Diagrama de seguimiento de ejecución paso a paso (solo algoritmos iterativos)"
    )