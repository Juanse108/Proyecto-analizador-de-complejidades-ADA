from pydantic import BaseModel, Field
from typing import Any, List, Optional, Dict

# --- Estructuras para la COMUNICACIÓN INTERNA ---

# Estructura de respuesta del servicio Parser /parse
class ParseResp(BaseModel):
    ok: bool = Field(..., description="Indica si el parseo sintáctico fue exitoso.")
    ast: Optional[Dict[str, Any]] = Field(None, description="Árbol de Sintaxis Abstracta (AST) si el parseo fue exitoso.")
    errors: List[str] = Field(default_factory=list, description="Lista de errores de sintaxis.")

# Estructura de request para el servicio Parser /semantic
class SemReq(BaseModel):
    ast: Dict[str, Any] = Field(..., description="AST del código a analizar.")

# Estructura de request para el servicio Analyzer /analyze-ast
class AnalyzeAstReq(BaseModel):
    ast_sem: Dict[str, Any] = Field(..., description="AST semánticamente validado.")
    objective: str = Field("worst", description="Objetivo de análisis (e.g., 'worst', 'best', 'average').")
    cost_model: Optional[str] = Field(None, description="Modelo de costo opcional.")

# Estructura de respuesta del servicio Analyzer /analyze-ast
class AnalyzerResult(BaseModel):
    big_o: str = Field(..., description="Notación O (Peor Caso).")
    big_omega: Optional[str] = Field(None, description="Notación Omega (Mejor Caso).")
    theta: Optional[str] = Field(None, description="Notación Theta (Caso Promedio).")
    ir: Optional[Dict[str, Any]] = Field(None, description="Representación Intermedia (IR) usada para el cálculo.")
    notes: Optional[str] = Field(None, description="Notas o explicaciones del análisis.")

# --- Estructuras para el ENDPOINT PÚBLICO del Orchestrator ---

# Petición de entrada al Orchestrator
class AnalyzeRequest(BaseModel):
    code: str = Field(..., description="Pseudocódigo o Lenguaje Natural a analizar.")
    objective: str = Field("worst", description="Objetivo de análisis (e.g., 'worst', 'best', 'average').")

# Respuesta final que el Orchestrator envía al Frontend
class OrchestratorResponse(AnalyzerResult):
    normalized_code: str = Field(..., description="El código final, corregido por el LLM, que fue enviado al parser.")
    # El resto de campos son heredados de AnalyzerResult