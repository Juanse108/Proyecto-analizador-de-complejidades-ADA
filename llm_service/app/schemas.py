"""
Esquemas Pydantic utilizados por la capa de api del microservicio LLM.

Agrupa los modelos de entrada/salida de los distintos endpoints:

- to-grammar:
    Convierte texto o pseudocódigo libre en pseudocódigo normalizado
    compatible con la gramática de análisis.

- recurrence:
    Representa la extracción y análisis de recurrencias T(n).

- classify:
    Clasifica patrones de algoritmos (divide & conquer, DP, backtracking, etc.).

- compare:
    Compara resultados de complejidad (núcleo vs. LLM) y sugiere siguientes pasos.
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# to-grammar
# ---------------------------------------------------------------------------


class ToGrammarRequest(BaseModel):
    """
    Petición para normalizar texto a pseudocódigo.

    Atributos:
        text:
            Texto fuente en lenguaje natural o pseudocódigo informal que se
            quiere transformar a pseudocódigo estricto.
        hints:
            Pistas opcionales para el LLM (por ejemplo, tipo de algoritmo,
            parámetros relevantes, contexto, etc.).
    """

    text: str = Field(..., description="Texto o pseudocódigo a normalizar")
    hints: Optional[str] = None


class ToGrammarResponse(BaseModel):
    """
    Respuesta del endpoint de normalización a gramática.

    Atributos:
        pseudocode_normalizado:
            Pseudocódigo final generado por el LLM y postprocesado para que
            cumpla la gramática `pseudocode.lark`.
        issues:
            Lista de comentarios, advertencias o decisiones tomadas durante
            el proceso (modelo usado, fallbacks, correcciones de sintaxis, etc.).
    """

    pseudocode_normalizado: str
    issues: List[str] = []


# ---------------------------------------------------------------------------
# recurrence
# ---------------------------------------------------------------------------


class RecurrenceRequest(BaseModel):
    """
    Petición para extraer/analizar una recurrencia a partir de pseudocódigo.

    Atributos:
        pseudocode:
            Pseudocódigo del algoritmo del que se desea extraer T(n).
    """

    pseudocode: str


class RecurrenceResponse(BaseModel):
    """
    Respuesta con la recurrencia estimada para un algoritmo.

    Atributos:
        recurrence:
            Representación textual de la recurrencia T(n), por ejemplo:
            "T(n) = 2T(n/2) + n".
        base_cases:
            Casos base identificados (por ejemplo T(1) = c).
        a, b, f:
            Parámetros de la recurrencia tipo Maestro (a subproblemas, tamaño
            n/b, término no recursivo f(n)).
        master_case:
            Caso identificable de la Master Theorem, si aplica (caso 1, 2, 3...).
        big_o, big_omega, big_theta:
            Cotas asintóticas propuestas a partir de la recurrencia.
        explanation:
            Explicación textual del razonamiento seguido por el LLM.
    """

    recurrence: Optional[str] = None
    base_cases: List[str] = []
    a: Optional[int] = None
    b: Optional[int] = None
    f: Optional[str] = None
    master_case: Optional[str] = None
    big_o: Optional[str] = None
    big_omega: Optional[str] = None
    big_theta: Optional[str] = None
    explanation: Optional[str] = None


# ---------------------------------------------------------------------------
# classify
# ---------------------------------------------------------------------------

PatternLabel = Literal[
    "divide_and_conquer",
    "dynamic_programming",
    "backtracking",
    "greedy",
    "search",
    "scan",
    "counting",
    "unknown",
]


class ClassifyRequest(BaseModel):
    """
    Petición para clasificar el patrón de un algoritmo.

    Atributos:
        pseudocode:
            Pseudocódigo del algoritmo a clasificar según su patrón dominante.
    """

    pseudocode: str


class ClassifyResponse(BaseModel):
    """
    Respuesta de clasificación de patrones algorítmicos.

    Atributos:
        pattern:
            Etiqueta principal asociada al patrón del algoritmo (divide and
            conquer, DP, backtracking, etc.).
        confidence:
            Confianza (0–1) con la que el LLM asigna la etiqueta.
        hints:
            Comentarios adicionales sobre los indicios que llevaron a esa
            clasificación (uso de recursión, subproblemas, memoización, etc.).
    """

    pattern: PatternLabel = "unknown"
    confidence: float = 0.0
    hints: List[str] = []


# ---------------------------------------------------------------------------
# compare
# ---------------------------------------------------------------------------


class BigBounds(BaseModel):
    """
    Grupo de cotas asintóticas para un mismo algoritmo.

    Atributos:
        big_o:
            Cota superior asintótica (O).
        big_omega:
            Cota inferior asintótica (Ω).
        big_theta:
            Cota ajustada (Θ) si se dispone de ella.
    """

    big_o: Optional[str] = None
    big_omega: Optional[str] = None
    big_theta: Optional[str] = None


class CompareRequest(BaseModel):
    """
    Petición para comparar dos conjuntos de cotas de complejidad.

    Pensado típicamente para comparar:
        - core: resultados del analizador "clásico" o heurístico.
        - llm:  resultados estimados por el LLM.

    Atributos:
        core:
            Cotas calculadas por el núcleo tradicional del sistema.
        llm:
            Cotas sugeridas por el modelo de lenguaje (LLM).
    """

    core: BigBounds
    llm: BigBounds


class CompareResponse(BaseModel):
    """
    Resultado de la comparación de complejidades entre dos fuentes.

    Atributos:
        agree:
            Indica si las cotas son compatibles o coinciden lo suficiente.
        deltas:
            Lista de diferencias detectadas (por ejemplo,
            "core: O(n), llm: O(n^2)").
        next_checks:
            Sugerencias de pasos siguientes (casos de prueba, análisis manual,
            revisión de heurísticas, etc.).
    """

    agree: bool
    deltas: List[str] = []
    next_checks: List[str] = []


# ---------------------------------------------------------------------------
# compare-analysis (endpoint frontend)
# ---------------------------------------------------------------------------


class AnalyzerResult(BaseModel):
    """Resultado del analizador de complejidad."""
    big_o: str
    big_omega: str
    theta: str


class LLMAnalysisResult(BaseModel):
    """Análisis de complejidad hecho por el LLM."""
    big_o: str
    big_omega: str
    theta: str
    reasoning: str


class LineCostDetail(BaseModel):
    """Detalle de costo de análisis línea por línea."""
    line: int
    kind: str
    multiplier: str = "1"
    analyzer_cost_worst: Optional[str] = None
    llm_cost_worst: Optional[str] = None
    cost_match: bool = False


class ComparisonDetails(BaseModel):
    """Detalles de la comparación entre resultados."""
    big_o_match: bool
    big_omega_match: bool
    theta_match: bool
    overall_agreement: float
    differences: List[str] = []
    recommendations: List[str] = []


class CompareAnalysisRequest(BaseModel):
    """
    Petición para comparar análisis del LLM con el analizador del backend.
    
    Atributos:
        pseudocode: Pseudocódigo a analizar
        analyzer_result: Resultado del analizador del backend
    """
    pseudocode: str
    analyzer_result: AnalyzerResult


class CompareAnalysisResponse(BaseModel):
    """
    Respuesta de la comparación entre LLM y analizador.
    
    Atributos:
        llm_analysis: Análisis independiente del LLM
        comparison: Detalles de la comparación
        summary: Resumen ejecutivo
        line_analysis: Análisis línea por línea (opcional)
    """
    llm_analysis: LLMAnalysisResult
    comparison: ComparisonDetails
    summary: str
    line_analysis: Optional[List[LineCostDetail]] = None
