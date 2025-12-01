from typing import Dict, Tuple, Any

from ..domain import (
    Expr, const,
    big_o_str_from_expr, big_omega_str_from_expr,
    ProgramCost, LineCostInternal
)
from ..domain.ast_utils import extract_main_body
from ..schemas import LineCost

from .analyzer_core import analyze_stmt_list


def analyze_iterative_program(ast: dict) -> ProgramCost:
    stmts = extract_main_body(ast)
    env: Dict[str, Tuple[str, Any]] = {}
    multiplier = const(1)

    worst, best, avg, lines = analyze_stmt_list(stmts, multiplier, env)

    return ProgramCost(
        worst=worst,
        best=best,
        avg=avg,
        lines=lines,
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