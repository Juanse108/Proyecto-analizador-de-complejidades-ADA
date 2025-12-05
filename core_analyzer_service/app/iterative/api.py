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
    """Detecta si los costos de línea muestran patrón de búsqueda binaria.
    
    Busca multiplicadores con "log" que típicamente indican binary search.
    
    Args:
        lines: Lista de costos de línea internos
        
    Returns:
        True si se detecta patrón de búsqueda binaria
    """
    # Buscar multiplicadores con "log" que típicamente indican binary search
    for lc in lines:
        mult_str = big_o_str_from_expr(lc.multiplier)
        if "log" in mult_str.lower():
            return True
    return False


def analyze_iterative_program(ast: dict) -> ProgramCost:
    """Analiza un programa iterativo y calcula su complejidad.
    
    Args:
        ast: Árbol de sintaxis abstracta del programa
        
    Returns:
        Objeto ProgramCost con análisis de complejidad y traza de ejecución
    """
    stmts = extract_main_body(ast)
    env: Dict[str, Tuple[str, Any]] = {}
    multiplier = const(1)

    worst, best, avg, lines = analyze_stmt_list(stmts, multiplier, env)

    binary_search_detected = _detect_binary_search_in_lines(lines)
    
    big_o_complexity = big_o_str_from_expr(worst)
    complexity_hint = f"O({big_o_complexity})"
    
    execution_trace = generate_execution_trace(ast, complexity_hint, "n")

    return ProgramCost(
        worst=worst,
        best=best,
        avg=avg,
        lines=lines,
        binary_search_detected=binary_search_detected,
        method_used="binary_search" if binary_search_detected else "iteration",
        execution_trace=execution_trace,
    )


def serialize_line_costs(lines: list[LineCostInternal]) -> list[LineCost]:
    """Serializa costos de línea internos a formato público.
    
    Args:
        lines: Lista de costos de línea internos
        
    Returns:
        Lista de objetos LineCost serializados
    """
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