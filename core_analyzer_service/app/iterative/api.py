from typing import Dict, Tuple, Any

from ..domain import (
    Expr, const,
    big_o_str_from_expr, big_omega_str_from_expr,
    ProgramCost, LineCostInternal
)
from ..domain.ast_utils import extract_main_body
from ..schemas import LineCost

from .analyzer_core import analyze_stmt_list
from .execution_trace import generate_execution_trace, ExecutionTrace


def _detect_binary_search_in_lines(lines: list[LineCostInternal]) -> bool:
    """Detecta si los line costs muestran patrón de binary search (log n iteraciones)."""
    # Buscar multiplicadores con "log" que típicamente indican binary search
    for lc in lines:
        mult_str = big_o_str_from_expr(lc.multiplier)
        if "log" in mult_str.lower():
            return True
    return False


def analyze_iterative_program(ast: dict) -> ProgramCost:
    print(f"\n🔄 [analyze_iterative_program] INICIANDO análisis iterativo...")
    
    stmts = extract_main_body(ast)
    env: Dict[str, Tuple[str, Any]] = {}
    multiplier = const(1)

    worst, best, avg, lines = analyze_stmt_list(stmts, multiplier, env)

    # Detectar si binary search fue reconocido
    binary_search_detected = _detect_binary_search_in_lines(lines)
    
    # 🆕 Generar traza de ejecución para el seguimiento del pseudocódigo
    big_o_complexity = big_o_str_from_expr(worst)
    print(f"   📊 Big O detectado: {big_o_complexity}")
    
    # Agregar "O()" para que la detección funcione correctamente
    complexity_hint = f"O({big_o_complexity})"
    print(f"   🔍 Hint para traza: {complexity_hint}")
    print(f"   🎯 Generando execution_trace...")
    
    execution_trace = generate_execution_trace(ast, complexity_hint, "n")
    
    print(f"   ✅ execution_trace generado:")
    print(f"      - Pasos: {len(execution_trace.steps)}")
    print(f"      - Iteraciones: {execution_trace.total_iterations}")
    print(f"      - Fórmula: {execution_trace.complexity_formula}")

    return ProgramCost(
        worst=worst,
        best=best,
        avg=avg,
        lines=lines,
        binary_search_detected=binary_search_detected,
        method_used="binary_search" if binary_search_detected else "iteration",
        execution_trace=execution_trace,  # 🆕 Añadir traza
    )


def serialize_line_costs(lines: list[LineCostInternal]) -> list[LineCost]:
    return [
        LineCost(
            line=lc.line,
            kind=lc.kind,
            text=lc.text,
            multiplier=big_o_str_from_expr(lc.multiplier),
            cost_worst=big_o_str_from_expr(lc.cost_worst),
            cost_best=big_omega_str_from_expr(lc.cost_best),
            cost_avg=big_o_str_from_expr(lc.cost_avg) if lc.cost_avg else None,
        )
        for lc in lines
    ]