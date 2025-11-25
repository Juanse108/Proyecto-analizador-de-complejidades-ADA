"""
schemas.py - Modelos de datos para el microservicio de análisis de complejidad
==============================================================================

Define los esquemas de entrada/salida para los endpoints del analizador,
incluyendo análisis línea por línea y soporte para iterativo/recursivo.
"""

from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 1. REQUEST MODELS
# ---------------------------------------------------------------------------

class AnalyzeAstReq(BaseModel):
    """
    Petición para analizar la complejidad de un AST.

    Atributos:
        ast: Árbol de sintaxis abstracta del programa.
        objective: Qué caso analizar ("worst", "best", "avg", o "all").
        detail: Nivel de detalle ("program" solo global, "line-by-line" incluye cada línea).
        cost_model: Diccionario opcional con costos personalizados para operaciones.
    """
    ast: Dict[str, Any]
    objective: Literal["worst", "best", "avg", "all"] = "all"
    detail: Literal["program", "line-by-line"] = "program"
    cost_model: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# 2. INTERMEDIATE MODELS (metadatos del AST)
# ---------------------------------------------------------------------------

class FunctionMetadata(BaseModel):
    """
    Metadatos de una función/procedimiento del programa.

    Atributos:
        name: Nombre de la función.
        is_recursive: Indica si la función se llama a sí misma (directa o indirectamente).
        calls: Lista de nombres de funciones que esta función llama.
    """
    name: str
    is_recursive: bool = False
    calls: List[str] = Field(default_factory=list)


class ProgramMetadata(BaseModel):
    """
    Metadatos globales del programa analizado.

    Atributos:
        algorithm_kind: Clasificación del programa según sus funciones.
        functions: Diccionario de metadatos por función.
    """
    algorithm_kind: Literal["iterative", "recursive", "mixed"]
    functions: Dict[str, FunctionMetadata] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# 3. LINE-BY-LINE COST MODELS
# ---------------------------------------------------------------------------

class LineCost(BaseModel):
    """
    Representa el costo de una línea individual de código.

    Atributos:
        line: Número de línea en el pseudocódigo original.
        kind: Tipo de sentencia (assign, for, while, if, call, etc.).
        text: Texto de la línea (opcional, para debugging/UI).
        multiplier: Cuántas veces se ejecuta esta línea (representación textual).
        cost_worst: Costo en el peor caso (representación textual del IR).
        cost_best: Costo en el mejor caso.
        cost_avg: Costo en el caso promedio (puede ser None si no aplica).
    """
    line: int
    kind: str
    text: Optional[str] = None
    multiplier: str = "1"
    cost_worst: str
    cost_best: str
    cost_avg: Optional[str] = None


# ---------------------------------------------------------------------------
# 4. RESPONSE MODELS
# ---------------------------------------------------------------------------

class AnalyzeAstResp(BaseModel):
    """
    Respuesta del análisis de complejidad.

    Atributos:
        algorithm_kind: Clasificación del algoritmo (iterativo/recursivo/mixto).
        big_o: Notación Big-O (peor caso).
        big_omega: Notación Big-Ω (mejor caso).
        theta: Notación Θ (caso promedio / ajustado).
        strong_bounds: Cotas más precisas (futuro: con constantes).
        ir_worst: Representación IR del peor caso (JSON).
        ir_best: Representación IR del mejor caso (JSON).
        ir_avg: Representación IR del caso promedio (JSON, opcional).
        lines: Costos línea por línea (solo si detail="line-by-line").
        notes: Comentarios o advertencias del análisis.
    """
    algorithm_kind: str
    big_o: str
    big_omega: str
    theta: Optional[str] = None
    strong_bounds: Optional[str] = None

    ir_worst: Dict[str, Any]
    ir_best: Dict[str, Any]
    ir_avg: Optional[Dict[str, Any]] = None

    lines: Optional[List[LineCost]] = None
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# 5. ERROR MODELS
# ---------------------------------------------------------------------------

class AnalysisError(BaseModel):
    """
    Representa un error durante el análisis.

    Atributos:
        severity: Nivel de severidad ("error" detiene el análisis, "warning" solo informa).
        message: Descripción del error.
        location: Ubicación en el código (línea/nodo) donde ocurrió.
    """
    severity: Literal["error", "warning"]
    message: str
    location: Optional[str] = None


# Agregar a schemas.py (nuevos modelos)

# ---------------------------------------------------------------------------
# STRONG BOUNDS (COTAS FUERTES)
# ---------------------------------------------------------------------------

class StrongBounds(BaseModel):
    """
    Representación de cotas fuertes con constantes explícitas.

    Ejemplo:
        T(n) = 5n² + 3n + 7

    Atributos:
        formula: Fórmula completa como string ("5n² + 3n + 7")
        terms: Lista de términos individuales con sus coeficientes
        dominant_term: Término que domina la complejidad ("5n²")
        constant: Término constante (7)
        evaluated_at: Ejemplos de valores concretos para n pequeños
    """
    formula: str = Field(
        description="Fórmula completa: T(n) = 5n² + 3n + 7"
    )
    terms: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Lista de términos: [{coef: 5, expr: 'n²', degree: (2,0)}, ...]"
    )
    dominant_term: Optional[str] = Field(
        default=None,
        description="Término dominante para Big-O"
    )
    constant: int = Field(
        default=0,
        description="Término constante aditivo"
    )
    evaluated_at: Optional[Dict[str, int]] = Field(
        default=None,
        description="Valores evaluados: {n=10: 537, n=100: 50307, ...}"
    )


# Modificar AnalyzeAstResp para incluir strong_bounds como objeto

class analyzeAstResp(BaseModel):
    """
    Respuesta del análisis de complejidad (ACTUALIZADA).
    """
    algorithm_kind: str
    big_o: str
    big_omega: str
    theta: Optional[str] = None

    # ✅ NUEVO: Cotas fuertes con fórmula explícita
    strong_bounds: Optional[StrongBounds] = Field(
        default=None,
        description="Fórmula explícita: T(n) = 5n² + 3n + 7"
    )

    ir_worst: Dict[str, Any]
    ir_best: Dict[str, Any]
    ir_avg: Optional[Dict[str, Any]] = None

    lines: Optional[List[LineCost]] = None
    notes: Optional[str] = None
