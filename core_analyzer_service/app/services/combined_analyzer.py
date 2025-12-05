"""Orquestación del análisis de complejidad algorítmica.

Este módulo coordina el análisis de algoritmos mediante:
- Integración de análisis de sumatorias
- Uso de SourceMapper para añadir campos de texto a costos de línea
- Generación de representaciones de cotas fuertes
- Provisión de datos completos de sumatorias en respuestas
"""

from __future__ import annotations

from typing import Dict, Any, List

from fastapi import HTTPException

from ..schemas import AnalyzeAstReq, analyzeAstResp, StrongBounds, LineCost
from ..ast_classifier import classify_algorithm
from ..iterative.api import analyze_iterative_program, serialize_line_costs
from ..recursive import analyze_recursive_function
from ..domain.recurrence import RecurrenceRelation, RecursiveAnalysisResult
from ..domain.summation_builder import analyze_nested_loops, format_summation_equation
from ..domain.expr import (
    Expr,
    add,
    big_o_str_from_expr,
    big_omega_str_from_expr,
    to_json,
)
from ..domain.summation_builder import analyze_nested_loops, format_summation_equation
from ..domain.source_mapper import create_source_mapper


def _generate_strong_bounds_fixed(expr: Expr, name: str = "T(n)") -> StrongBounds:
    """Construye la estructura de cotas fuertes a partir de una expresión de complejidad.
    
    Args:
        expr: Expresión de complejidad a analizar
        name: Nombre de la función (por defecto: "T(n)")
        
    Returns:
        Objeto StrongBounds con fórmula, términos, término dominante y constante
    """
    from ..domain.expr import to_explicit_formula, Add, Const, Pow, Sym, Mul

    formula_str = to_explicit_formula(expr)

    terms = []
    dominant_term_str = None
    constant_val = 0

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
    """Selecciona el primer procedimiento recursivo del AST.
    
    Args:
        ast: Árbol de sintaxis abstracta
        metadata: Metadatos del programa con información de funciones
        
    Returns:
        Diccionario representando el procedimiento recursivo
        
    Raises:
        HTTPException: Si no se encuentra ningún procedimiento recursivo
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
    """Analiza la complejidad de un algoritmo desde su AST.
    
    Esta función:
    - Genera representaciones explícitas de sumatorias
    - Añade texto fuente a cada línea usando SourceMapper
    - Proporciona cotas fuertes sin expresiones redundantes
    - Retorna datos de sumatorias para visualización en UI
    
    Args:
        req: Solicitud de análisis conteniendo AST y modelo de costos
        
    Returns:
        Respuesta de análisis con cotas de complejidad e información detallada
    """
    ast = req.ast

    pseudocode_source = req.cost_model.get("source_code") if req.cost_model else None
    source_mapper = create_source_mapper(pseudocode_source) if pseudocode_source else None

    metadata = classify_algorithm(ast)

    if metadata.algorithm_kind == "iterative":
        result = analyze_iterative_program(ast)

        big_o = big_o_str_from_expr(result.worst)
        big_omega = big_omega_str_from_expr(result.best)
        
        if big_o == big_omega:
            theta = big_o
        elif result.avg is not None:
            theta = big_o_str_from_expr(result.avg)
        else:
            theta = None

        strong_bounds = _generate_strong_bounds_fixed(result.worst, name="T(n)")

        from ..domain.summation_builder import generate_summations_from_expressions
        
        summations = generate_summations_from_expressions(
            worst_expr=big_o,
            best_expr=big_omega,
            avg_expr=theta if theta else None
        )

        public_lines = serialize_line_costs(result.lines)
        if source_mapper:
            lines_as_dicts = [lc.model_dump() for lc in public_lines]
            lines_as_dicts = source_mapper.annotate_line_costs(lines_as_dicts)
            public_lines = [LineCost(**lc_dict) for lc_dict in lines_as_dicts]

        method_used = getattr(result, "method_used", "iteration")

        notes_list = [f"Análisis iterativo. Objetivo: {req.objective}."]
        if getattr(result, "binary_search_detected", False):
            notes_list.append(
                "Patrón detectado: Búsqueda Binaria. "
                "Peor caso O(log n), mejor caso Ω(1), caso promedio Θ(log n)."
            )
        
        execution_trace_dict = None
        if hasattr(result, 'execution_trace') and result.execution_trace:
            from ..schemas import ExecutionTrace as ExecutionTraceSchema
            trace = result.execution_trace
            execution_trace_dict = ExecutionTraceSchema(
                steps=[{
                    "step": step.step,
                    "line": step.line,
                    "kind": step.kind,
                    "condition": step.condition,
                    "variables": step.variables,
                    "operation": step.operation,
                    "cost": step.cost,
                    "cumulative_cost": step.cumulative_cost
                } for step in trace.steps],
                total_iterations=trace.total_iterations,
                max_depth=trace.max_depth,
                variables_tracked=trace.variables_tracked,
                complexity_formula=trace.complexity_formula,
                description=trace.description
            )
        
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
            summations=summations,
            execution_trace=execution_trace_dict,
        )

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
            if rec_result.master_theorem_case:
                notes.append(f"Master Theorem case {rec_result.master_theorem_case}")

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
            recurrence_equation=rec_result.recurrence_equation,
        )

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
