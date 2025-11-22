"""
routes.py - Endpoints del microservicio de análisis de complejidad
==================================================================

Define las rutas HTTP para analizar la complejidad de algoritmos,
integrando clasificación iterativo/recursivo y análisis línea por línea.
"""

from fastapi import FastAPI, HTTPException
from .schemas import AnalyzeAstReq, AnalyzeAstResp
from .ast_classifier import classify_algorithm, has_main_block
from .iterative_analyzer import analyze_program, serialize_line_costs
from .complexity_ir import big_o_str_from_expr, big_omega_str_from_expr, to_json

app = FastAPI(title="Core Analyzer Service")


@app.post("/analyze-ast", response_model=AnalyzeAstResp)
def analyze_ast(req: AnalyzeAstReq):
    """
    Analiza la complejidad de un algoritmo a partir de su AST.

    Flujo:
    1. Clasificar el algoritmo (iterativo/recursivo/mixto).
    2. Despachar al analizador correspondiente.
    3. Calcular complejidades (O, Ω, Θ) y opcionalmente costos línea por línea.

    Args:
        req: Petición con AST y opciones de análisis.

    Returns:
        Respuesta con complejidades, IR y opcionalmente análisis línea por línea.

    Raises:
        HTTPException: Si el algoritmo es recursivo (no soportado aún) o hay error interno.
    """
    try:
        ast = req.ast

        # Paso 1: Clasificar el algoritmo
        metadata = classify_algorithm(ast)

        # Paso 2: Verificar que sea iterativo (por ahora solo soportamos esto)
        if metadata.algorithm_kind == "recursive":
            raise HTTPException(
                status_code=501,
                detail="Análisis de algoritmos recursivos no implementado aún. "
                       f"Funciones recursivas detectadas: {[f for f, m in metadata.functions.items() if m.is_recursive]}"
            )

        if metadata.algorithm_kind == "mixed":
            raise HTTPException(
                status_code=501,
                detail="Algoritmos mixtos (iterativo + recursivo) no soportados aún."
            )

        # Paso 3: Analizar con el analizador iterativo
        result = analyze_program(ast)

        # Paso 4: Calcular notaciones asintóticas
        big_o = big_o_str_from_expr(result.worst)
        big_omega = big_omega_str_from_expr(result.best)

        # Θ solo si worst == best
        theta = big_o if big_o == big_omega else None

        # Paso 5: Serializar IR a JSON
        ir_worst = to_json(result.worst)
        ir_best = to_json(result.best)
        ir_avg = to_json(result.avg) if result.avg else None

        # Paso 6: Serializar líneas (SIEMPRE, no solo si detail="line-by-line")
        # Si el usuario NO quiere líneas, simplemente las ignora en el cliente
        lines = serialize_line_costs(result.lines)

        # ✅ FIX: Siempre incluir lines, independientemente del parámetro detail
        # El cliente decide si las usa o no

        # Paso 7: Construir respuesta
        return AnalyzeAstResp(
            algorithm_kind=metadata.algorithm_kind,
            big_o=big_o,
            big_omega=big_omega,
            theta=theta,
            strong_bounds=None,
            ir_worst=ir_worst,
            ir_best=ir_best,
            ir_avg=ir_avg,
            lines=lines,  # ← Siempre incluido
            notes=f"Análisis iterativo. Objetivo: {req.objective}. Detalle: {req.detail}.",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error interno durante el análisis: {str(e)}"
        )


@app.get("/health")
def health():
    """Endpoint de healthcheck."""
    return {"status": "ok", "service": "core_analyzer"}