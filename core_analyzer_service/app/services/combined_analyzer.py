# core_analyzer_service/app/services/combined_analyzer.py (CORREGIDO)
"""
combined_analyzer.py - Orquestación CORREGIDA
==============================================

CAMBIOS PRINCIPALES:
1. Integra módulo de sumatorias
2. Usa SourceMapper para añadir campo 'text' a líneas
3. Genera strong_bounds sin max() innecesario
4. Añade campo 'summations' a la respuesta
"""

from __future__ import annotations

from typing import Dict, Any, List

from fastapi import HTTPException

from ..schemas import AnalyzeAstReq, analyzeAstResp, StrongBounds, LineCost
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
    to_explicit_formula_verbose,  # puede quedar aunque no se use
)
# ✅ NUEVO: Importar módulos para sumatorias y source mapping
from ..domain.summation_builder import analyze_nested_loops, format_summation_equation
from ..domain.source_mapper import create_source_mapper


def _generate_strong_bounds_fixed(expr: Expr, name: str = "T(n)") -> StrongBounds:
    """
    Construye la estructura de cotas fuertes CORREGIDA.
    
    CAMBIO: Ya no usa to_explicit_formula_verbose que genera max(),
    sino que construye directamente la forma polinómica.
    """
    # Usar to_explicit_formula en lugar de to_explicit_formula_verbose
    from ..domain.expr import to_explicit_formula

    formula_str = to_explicit_formula(expr)

    # Extraer información de términos manualmente
    terms = []
    dominant_term_str = None
    constant_val = 0

    # Si es Add, extraer cada término
    from ..domain.expr import Add, Const, Pow, Sym, Mul

    if isinstance(expr, Add):
        for term in expr.terms:
            if isinstance(term, Const):
                constant_val = term.k
            elif isinstance(term, Pow):
                terms.append(
                    {
                        "expr": to_explicit_formula(term),
                        "degree": (term.exp, 0),
                    }
                )
                if dominant_term_str is None:
                    dominant_term_str = to_explicit_formula(term)
            elif isinstance(term, Mul):
                # Calcular degree del Mul
                deg = 0
                for factor in term.factors:
                    if isinstance(factor, Pow):
                        deg += factor.exp
                    elif isinstance(factor, Sym):
                        deg += 1
                terms.append(
                    {
                        "expr": to_explicit_formula(term),
                        "degree": (deg, 0),
                    }
                )
                if dominant_term_str is None:
                    dominant_term_str = to_explicit_formula(term)
    elif isinstance(expr, Pow):
        terms.append(
            {
                "expr": to_explicit_formula(expr),
                "degree": (expr.exp, 0),
            }
        )
        dominant_term_str = to_explicit_formula(expr)
    elif isinstance(expr, Const):
        constant_val = expr.k

    return StrongBounds(
        formula=f"{name} = {formula_str}",
        terms=terms,
        dominant_term=dominant_term_str,
        constant=constant_val,
    )


def _select_recursive_proc(ast: Dict[str, Any], metadata) -> Dict[str, Any]:
    """Selecciona el primer procedimiento recursivo."""
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
    Analiza la complejidad de un algoritmo - VERSIÓN CORREGIDA.
    
    CAMBIOS:
    1. Genera sumatorias explícitas
    2. Añade texto a cada línea usando SourceMapper
    3. strong_bounds sin max() innecesario
    4. Devuelve campo 'summations' para la UI
    """
    ast = req.ast

    # ✅ NUEVO: Obtener pseudocódigo original si está disponible
    pseudocode_source = req.cost_model.get("source_code") if req.cost_model else None
    source_mapper = create_source_mapper(pseudocode_source) if pseudocode_source else None

    # 1) Clasificación global
    metadata = classify_algorithm(ast)

    # ---------------------------------------------------------------
    # CASO ITERATIVO
    # ---------------------------------------------------------------
    if metadata.algorithm_kind == "iterative":
        result = analyze_iterative_program(ast)

        big_o = big_o_str_from_expr(result.worst)
        big_omega = big_omega_str_from_expr(result.best)
        theta = big_o if big_o == big_omega else None

        # ✅ NUEVO: Generar strong_bounds corregido
        strong_bounds = _generate_strong_bounds_fixed(result.worst, name="T(n)")

        # ✅ NUEVO: Generar sumatorias explícitas
        from ..domain.ast_utils import extract_main_body

        main_body = extract_main_body(ast)
        summation_analysis = analyze_nested_loops(main_body)

        # Formatear ecuaciones de sumatorias (texto plano, multilinea)
        summations = {
            "worst": format_summation_equation(
                "worst",
                summation_analysis.worst_summation,
                summation_analysis.worst_simplified,
                summation_analysis.worst_polynomial,
            ),
            "best": format_summation_equation(
                "best",
                summation_analysis.best_summation,
                summation_analysis.best_simplified,
                summation_analysis.best_polynomial,
            ),
        }
        if summation_analysis.avg_summation:
            summations["avg"] = format_summation_equation(
                "avg",
                summation_analysis.avg_summation,
                summation_analysis.avg_simplified,
                summation_analysis.avg_polynomial,
            )

        # ✅ NUEVO: Añadir texto a líneas usando SourceMapper
        public_lines = serialize_line_costs(result.lines)
        if source_mapper:
            lines_as_dicts = [lc.model_dump() for lc in public_lines]
            lines_as_dicts = source_mapper.annotate_line_costs(lines_as_dicts)
            public_lines = [LineCost(**lc_dict) for lc_dict in lines_as_dicts]

        method_used = getattr(result, "method_used", "iteration")

        # Notas sin duplicar sumatorias (la UI tiene una sección propia para ellas)
        notes_list = [f"Análisis iterativo. Objetivo: {req.objective}."]

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
            notes=" | ".join(notes_list),
            method_used=method_used,
            summations=summations,  # 👈 IMPORTANTE: se expone summations para el front
        )


    # ---------------------------------------------------------------
    # CASO RECURSIVO
    # ---------------------------------------------------------------
    if metadata.algorithm_kind == "recursive":
        proc = _select_recursive_proc(ast, metadata)
        rec_result: RecursiveAnalysisResult = analyze_recursive_function(proc)

        big_o = big_o_str_from_expr(rec_result.big_o)
        big_omega = big_omega_str_from_expr(rec_result.big_omega)
        theta = big_o_str_from_expr(rec_result.theta) if rec_result.theta else None

        strong_bounds = _generate_strong_bounds_fixed(rec_result.big_o, name="T(n)")

        notes = [f"Análisis recursivo: {rec_result.explanation}"]

        if rec_result.recurrence:
            rec: RecurrenceRelation = rec_result.recurrence
            # Ya no duplicamos la info, la ecuación está en recurrence_equation
            if rec_result.master_theorem_case:
                notes.append(f"Teorema Maestro caso {rec_result.master_theorem_case}")

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
            recurrence_equation=rec_result.recurrence_equation,  # 🆕 NUEVO
        )

    # ---------------------------------------------------------------
    # CASO MIXTO
    # ---------------------------------------------------------------
    if metadata.algorithm_kind == "mixed":
        iter_result = analyze_iterative_program(ast)
        proc = _select_recursive_proc(ast, metadata)
        rec_result: RecursiveAnalysisResult = analyze_recursive_function(proc)

        total_worst_expr = add(iter_result.worst, rec_result.big_o)
        total_best_expr = add(iter_result.best, rec_result.big_omega)

        big_o = big_o_str_from_expr(total_worst_expr)
        big_omega = big_omega_str_from_expr(total_best_expr)
        theta = big_o if big_o == big_omega else None

        strong_bounds = _generate_strong_bounds_fixed(total_worst_expr, name="T(n)")

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

        # Ojo: en mixto usamos las líneas iterativas
        public_lines = serialize_line_costs(iter_result.lines)
        if source_mapper:
            lines_as_dicts = [lc.model_dump() for lc in public_lines]
            lines_as_dicts = source_mapper.annotate_line_costs(lines_as_dicts)
            public_lines = [LineCost(**lc_dict) for lc_dict in lines_as_dicts]

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
            ir_avg=None,
            lines=public_lines,
            notes=" | ".join(notes),
            method_used=method_used,
        )
