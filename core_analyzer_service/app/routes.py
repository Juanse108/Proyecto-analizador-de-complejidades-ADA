# Reemplazar el endpoint /analyze-ast en routes.py

"""
routes.py - Endpoints con cotas fuertes
"""

from fastapi import FastAPI, HTTPException
from .schemas import (
    AnalyzeAstReq, analyzeAstResp, StrongBounds
)
from .ast_classifier import classify_algorithm
from .iterative_analyzer import analyze_program, serialize_line_costs
from .recursive_analyzer import analyze_recursive_function
from .complexity_ir import (
    big_o_str_from_expr, big_omega_str_from_expr, to_json,
    to_explicit_formula, to_explicit_formula_verbose
)

app = FastAPI(title="Core Analyzer Service")


def generate_strong_bounds(expr, name: str = "T(n)") -> StrongBounds:
    """
    Genera la estructura de cotas fuertes desde una expresión IR.

    Args:
        expr: Expresión del IR (Expr)
        name: Nombre de la función (default: "T(n)")

    Returns:
        StrongBounds con fórmula completa y metadata
    """
    # Obtener fórmula y detalles
    details = to_explicit_formula_verbose(expr)


    return StrongBounds(
        formula=f"{name} = {details['formula']}",
        terms=details['terms'],
        dominant_term=details.get('dominant'),
        constant=details.get('constant', 0),
    )



@app.post("/analyze-ast", response_model=analyzeAstResp)
def analyze_ast(req: AnalyzeAstReq):
    """
    Analiza la complejidad de un algoritmo (iterativo o recursivo).

    ✅ NUEVO: Devuelve cotas fuertes y timing estimates.
    """
    try:
        ast = req.ast

        # Paso 1: Clasificar
        metadata = classify_algorithm(ast)

        # Paso 2: Despachar según tipo

        # ========== CASO ITERATIVO ==========
        if metadata.algorithm_kind == "iterative":
            result = analyze_program(ast)

            big_o = big_o_str_from_expr(result.worst)
            big_omega = big_omega_str_from_expr(result.best)
            theta = big_o if big_o == big_omega else None

            # ✅ GENERAR COTAS FUERTES
            strong_bounds = generate_strong_bounds(result.worst, name="T(n)")

            return analyzeAstResp(
                algorithm_kind="iterative",
                big_o=big_o,
                big_omega=big_omega,
                theta=theta,
                strong_bounds=strong_bounds,  # ✅ NUEVO
                ir_worst=to_json(result.worst),
                ir_best=to_json(result.best),
                ir_avg=to_json(result.avg) if result.avg else None,
                lines=serialize_line_costs(result.lines),
                notes=f"Análisis iterativo. Objetivo: {req.objective}."
            )

        # ========== CASO RECURSIVO ==========
        elif metadata.algorithm_kind == "recursive":
            body = ast.get("body", [])
            recursive_procs = [
                item for item in body
                if isinstance(item, dict) and
                item.get("kind") == "proc" and
                metadata.functions.get(item.get("name", ""), None) and
                metadata.functions[item["name"]].is_recursive
            ]

            if not recursive_procs:
                raise HTTPException(
                    status_code=500,
                    detail="Clasificado como recursivo pero no se encontró procedimiento recursivo"
                )

            proc = recursive_procs[0]
            params = proc.get("params", [])
            param_name = params[0] if params else "n"

            result = analyze_recursive_function(proc, param_name)

            big_o = big_o_str_from_expr(result.big_o)
            big_omega = big_omega_str_from_expr(result.big_omega)
            theta = big_o_str_from_expr(result.theta) if result.theta else None

            # ✅ GENERAR COTAS FUERTES
            strong_bounds = generate_strong_bounds(result.big_o, name="T(n)")


            notes = [f"Análisis recursivo: {result.explanation}"]

            if result.recurrence:
                rec = result.recurrence
                notes.append(
                    f"Recurrencia detectada: T(n) = {rec.a}T(n/{rec.b}) + f(n)"
                )
                if result.master_theorem_case:
                    notes.append(f"Teorema Maestro caso {result.master_theorem_case}")

            return analyzeAstResp(
                algorithm_kind="recursive",
                big_o=big_o,
                big_omega=big_omega,
                theta=theta,
                strong_bounds=strong_bounds,  # ✅ NUEVO
                ir_worst=to_json(result.big_o),
                ir_best=to_json(result.big_omega),
                ir_avg=to_json(result.theta) if result.theta else None,
                lines=None,
                notes=" | ".join(notes)
            )

        # ========== CASO MIXTO ==========
        else:
            raise HTTPException(
                status_code=501,
                detail="Algoritmos mixtos (iterativo + recursivo) no soportados aún."
            )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )


@app.get("/health")
def health():
    """Endpoint de healthcheck."""
    return {"status": "ok", "service": "core_analyzer"}