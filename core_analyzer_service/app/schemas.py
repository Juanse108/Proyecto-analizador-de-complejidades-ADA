"""Modelos de datos para el microservicio de análisis de complejidad.

Define los esquemas de entrada/salida para los endpoints del analizador,
incluyendo análisis línea por línea y soporte para iterativo/recursivo.
"""

from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field


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


class TraceStep(BaseModel):
    """
    Representa un paso en la traza de ejecución de un algoritmo iterativo.
    
    Atributos:
        step: Número de paso en la ejecución
        line: Línea de código ejecutada
        kind: Tipo de sentencia
        condition: Condición evaluada (para bucles/ifs)
        variables: Estado de las variables en este punto
        operation: Descripción de la operación realizada
        cost: Costo de este paso
        cumulative_cost: Costo acumulado hasta este paso
    """
    step: int
    line: int
    kind: str
    condition: Optional[str] = None
    variables: Dict[str, Any] = Field(default_factory=dict)
    operation: str = ""
    cost: str = "1"
    cumulative_cost: str = "1"


class ExecutionTrace(BaseModel):
    """Traza completa de ejecución de un algoritmo iterativo.
    
    Proporciona seguimiento del pseudocódigo iterativo,
    equivalente al árbol de recursión para algoritmos recursivos.
    
    Atributos:
        steps: Lista de pasos de la ejecución
        total_iterations: Total de iteraciones realizadas
        max_depth: Profundidad máxima de anidamiento alcanzada
        variables_tracked: Variables rastreadas durante la ejecución
        complexity_formula: Fórmula de complejidad derivada de la traza
        description: Explicación textual de la traza
    """
    steps: List[TraceStep]
    total_iterations: int
    max_depth: int
    variables_tracked: List[str]
    complexity_formula: str
    description: str = ""


class StrongBounds(BaseModel):
    """
    Representación de cotas fuertes con constantes explícitas.

    Ejemplo:
        T(n) = 5n² + 3n + 7

    Atributos:
        formula: Fórmula completa como string ("T(n) = 5n² + 3n + 7")
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
        description="Lista de términos: [{expr: 'n²', degree: (2,0)}, ...]"
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
        description="Valores evaluados: {10: 537, 100: 50307, ...}"
    )


class analyzeAstResp(BaseModel):
    """Respuesta del análisis de complejidad.
    
    Incluye cotas asintóticas, ecuación de recurrencia (si es recursivo),
    traza de ejecución (si es iterativo), y análisis detallado.
    """
    algorithm_kind: str
    big_o: str
    big_omega: str
    theta: Optional[str] = None

    strong_bounds: Optional[StrongBounds] = Field(
        default=None,
        description="Fórmula explícita: T(n) = 5n² + 3n + 7"
    )

    ir_worst: Dict[str, Any]
    ir_best: Dict[str, Any]
    ir_avg: Optional[Dict[str, Any]] = None

    lines: Optional[List[LineCost]] = None
    notes: Optional[str] = None

    method_used: Optional[str] = Field(
        default=None,
        description="Método principal utilizado en el análisis."
    )

    summations: Optional[Dict[str, Dict[str, str]]] = Field(
        default=None,
        description="Sumatorias y derivación por caso: worst/best/avg. Cada caso contiene {latex, text}."
    )

    recurrence_equation: Optional[str] = Field(
        default=None,
        description="Ecuación de recurrencia completa (solo para algoritmos recursivos). Ejemplo: 'T(n) = 2·T(n/2) + c·n,  n > 1\\nT(1) = d'"
    )
    
    execution_trace: Optional[ExecutionTrace] = Field(
        default=None,
        description="Traza de ejecución paso a paso (solo para algoritmos iterativos). Muestra el seguimiento del pseudocódigo con estados de variables."
    )


# Alias opcional para compatibilidad con código que use el nombre antiguo
AnalyzeAstResp = analyzeAstResp


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