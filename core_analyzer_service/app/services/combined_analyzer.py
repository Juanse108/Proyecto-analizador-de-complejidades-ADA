# app/services/combined_analyzer.py
"""
combined_analyzer.py - Orquestación de análisis iterativo y recursivo
=====================================================================

Servicio de alto nivel que:

- Clasifica el programa (iterativo / recursivo / mixto).
- Invoca al analizador iterativo o recursivo según corresponda.
- Construye la respuesta `analyzeAstResp` con Big-O, Big-Ω, Θ,
  cotas fuertes y costos línea por línea.
"""

from __future__ import annotations

from typing import Dict, Any, List

from fastapi import HTTPException

from ..schemas import AnalyzeAstReq, analyzeAstResp, StrongBounds
from ..ast_classifier import classify_algorithm
from ..iterative.api import analyze_iterative_program, serialize_line_costs
from ..recursive import analyze_recursive_function
from ..domain.recurrence import RecurrenceRelation, RecursiveAnalysisResult
from ..domain.expr import (
    Expr,
    add,
    big_o_str_from_expr,
    big_omega_str_from_expr,
    to_json,
    to_explicit_formula_verbose,
)



def _generate_strong_bounds(expr: Expr, name: str = "T(n)") -> StrongBounds:
    """
    Construye la estructura de cotas fuertes a partir de una expresión IR.
    """
    details = to_explicit_formula_verbose(expr)

    return StrongBounds(
        formula=f"{name} = {details['formula']}",
        terms=details["terms"],
        dominant_term=details.get("dominant"),
        constant=details.get("constant", 0),
    )


def _select_recursive_proc(ast: Dict[str, Any], metadata) -> Dict[str, Any]:
    """
    Selecciona el primer procedimiento marcado como recursivo en la metadata.

    Esto es crucial: el analizador recursivo trabaja sobre un nodo `proc`,
    no sobre el AST completo del programa.
    """
    body: List[Dict[str, Any]] = ast.get("body", [])

    recursive_procs = [
        item
        for item in body
        if isinstance(item, dict)
        and item.get("kind") == "proc"
        and metadata.functions.get(item.get("name", ""), None)
        and metadata.functions[item["name"]].is_recursive
    ]

    if not recursive_procs:
        raise HTTPException(
            status_code=500,
            detail=(
                "Clasificado como recursivo, pero no se encontró ningún "
                "procedimiento recursivo en el AST."
            ),
        )

    return recursive_procs[0]


def analyze_ast_core(req: AnalyzeAstReq) -> analyzeAstResp:
    """
    Analiza la complejidad de un algoritmo a partir de su AST.

    Flujo:

    1. Clasificar el programa (iterativo / recursivo / mixto).
    2. Delegar al analizador iterativo o recursivo.
    3. Calcular Big-O, Big-Ω y Θ.
    4. Generar cotas fuertes.
    5. Construir `analyzeAstResp`.
    """
    ast = req.ast

    # 1) Clasificación global
    metadata = classify_algorithm(ast)

    # ---------------------------------------------------------------
    # CASO ITERATIVO
    # ---------------------------------------------------------------
    if metadata.algorithm_kind == "iterative":
        # ProgramCost: worst, best, avg, lines (internas)
        result = analyze_iterative_program(ast)

        big_o = big_o_str_from_expr(result.worst)
        big_omega = big_omega_str_from_expr(result.best)
        theta = big_o if big_o == big_omega else None

        strong_bounds = _generate_strong_bounds(result.worst, name="T(n)")

        # LineCostInternal -> LineCost (modelo Pydantic)
        public_lines = serialize_line_costs(result.lines)

        # Método usado: para parte iterativa
        method_used = getattr(result, "method_used", "iteration")

        return analyzeAstResp(
            algorithm_kind="iterative",
            big_o=big_o,
            big_omega=big_omega,
            theta=theta,
            strong_bounds=strong_bounds,
            ir_worst=to_json(result.worst),
            ir_best=to_json(result.best),
            ir_avg=to_json(result.avg) if result.avg else None,
            lines=public_lines,
            notes=f"Análisis iterativo. Objetivo: {req.objective}.",
            method_used=method_used,
        )

    # ---------------------------------------------------------------
    # CASO RECURSIVO
    # ---------------------------------------------------------------
    if metadata.algorithm_kind == "recursive":
        # Seleccionar el `proc` recursivo correcto
        proc = _select_recursive_proc(ast, metadata)

        # Ahora sí: analizar ESA función
        rec_result: RecursiveAnalysisResult = analyze_recursive_function(proc)

        big_o = big_o_str_from_expr(rec_result.big_o)
        big_omega = big_omega_str_from_expr(rec_result.big_omega)
        theta = big_o_str_from_expr(rec_result.theta) if rec_result.theta else None

        strong_bounds = _generate_strong_bounds(rec_result.big_o, name="T(n)")

        notes = [f"Análisis recursivo: {rec_result.explanation}"]

        if rec_result.recurrence:
            rec: RecurrenceRelation = rec_result.recurrence
            notes.append(
                f"Recurrencia detectada: T(n) = {rec.a}T(n/{rec.b}) + f(n)"
            )
            if rec_result.master_theorem_case:
                notes.append(
                    f"Teorema Maestro caso {rec_result.master_theorem_case}"
                )

        # Método usado viene del analizador recursivo
        method_used = getattr(rec_result, "method_used", None)

        return analyzeAstResp(
            algorithm_kind="recursive",
            big_o=big_o,
            big_omega=big_omega,
            theta=theta,
            strong_bounds=strong_bounds,
            ir_worst=to_json(rec_result.big_o),
            ir_best=to_json(rec_result.big_omega),
            ir_avg=to_json(rec_result.theta) if rec_result.theta else None,
            lines=None,
            notes=" | ".join(notes),
            method_used=method_used,
        )

    # ---------------------------------------------------------------
    # CASO MIXTO (iterativo + recursivo)
    # ---------------------------------------------------------------
    if metadata.algorithm_kind == "mixed":
        # 1) Análisis iterativo sobre todo el programa
        iter_result = analyze_iterative_program(ast)

        # 2) Seleccionar procedimiento recursivo principal
        proc = _select_recursive_proc(ast, metadata)

        # 3) Análisis recursivo sobre ese proc
        rec_result: RecursiveAnalysisResult = analyze_recursive_function(proc)

        # 4) Combinar costos en el IR:
        #    T_total(n) = T_iter(n) + T_rec(n)
        total_worst_expr = add(iter_result.worst, rec_result.big_o)
        total_best_expr = add(iter_result.best, rec_result.big_omega)

        big_o = big_o_str_from_expr(total_worst_expr)
        big_omega = big_omega_str_from_expr(total_best_expr)
        theta = big_o if big_o == big_omega else None

        strong_bounds = _generate_strong_bounds(total_worst_expr, name="T(n)")

        notes = ["Análisis mixto (iterativo + recursivo)."]
        notes.append(
            f"Parte iterativa: peor {big_o_str_from_expr(iter_result.worst)}, "
            f"mejor {big_omega_str_from_expr(iter_result.best)}."
        )
        notes.append(
            f"Parte recursiva: peor {big_o_str_from_expr(rec_result.big_o)}, "
            f"mejor {big_omega_str_from_expr(rec_result.big_omega)}."
        )

        if rec_result.recurrence:
            rec: RecurrenceRelation = rec_result.recurrence
            notes.append(
                f"Recurrencia detectada en parte recursiva: "
                f"T(n) = {rec.a}T(n/{rec.b}) + f(n)"
            )
            if rec_result.master_theorem_case:
                notes.append(
                    f"Teorema Maestro (parte recursiva) caso {rec_result.master_theorem_case}"
                )

        # Para las líneas detalladas, mostramos las del análisis iterativo,
        # que es donde tenemos breakdown línea por línea.
        public_lines = serialize_line_costs(iter_result.lines)

        # Combinar métodos usados, si existen
        iter_method = getattr(iter_result, "method_used", "iteration")
        rec_method = getattr(rec_result, "method_used", None)
        if rec_method:
            method_used = f"mixed({iter_method} + {rec_method})"
        else:
            method_used = f"mixed({iter_method} + recursive_core)"

        return analyzeAstResp(
            algorithm_kind="mixed",
            big_o=big_o,
            big_omega=big_omega,
            theta=theta,
            strong_bounds=strong_bounds,
            ir_worst=to_json(total_worst_expr),
            ir_best=to_json(total_best_expr),
            ir_avg=None,  # si no estás calculando caso promedio
            lines=public_lines,
            notes=" | ".join(notes),
            method_used=method_used,
        )

