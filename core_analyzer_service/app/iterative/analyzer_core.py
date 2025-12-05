"""Análisis de complejidad de algoritmos iterativos.

Provee funcionalidad central de análisis para algoritmos iterativos incluyendo:
- Manejo apropiado de ramas if para casos peor/mejor/promedio
- Propagación de casos de análisis a través del análisis
- Soporte para diferentes patrones de bucles
"""

from typing import List, Tuple, Dict, Any
from enum import Enum

from ..domain import (
    Expr, const, sym, mul, add,
    cost_assign, cost_compare, cost_seq,
    LineCostInternal, degree
)
from ..domain.ast_utils import is_var, is_num, get_line

from .patterns_for import (
    detect_triangular_loop,
    estimate_for_iterations,
    update_env_from_for
)

from .patterns_while import (
    assign_div_const, assign_mul_const, assign_add_const, assign_sub_const,
    cond_var_lt_sym_or_const, cond_var_gt_const,
    is_found_flag_while, while_has_early_exit_condition,
    while_has_index_jump_exit, insertion_sort_inner_while,
    is_adaptive_sort_while, is_sentinel_search_while,
    detect_binary_search_while
)

def branch_weight(lines: List[LineCostInternal]) -> int:
    """Cálculo heurístico del peso de una rama if.
    
    Actualmente utiliza el número de líneas como heurística simple.
    
    Args:
        lines: Lista de costos de línea de la rama
        
    Returns:
        Peso calculado (número de líneas)
    """
    return sum(1 for _ in lines)



class AnalysisCase(Enum):
    """Tipo de caso siendo analizado."""
    WORST = "worst"
    BEST = "best"
    AVG = "avg"


def env_record_assign(env: Dict[str, Tuple[str, Any]], stmt: dict) -> None:
    """Registra asignaciones en el entorno.
    
    Args:
        env: Entorno con variables y sus valores
        stmt: Sentencia de asignación a registrar
    """
    if stmt.get("kind") != "assign":
        return
    tgt = stmt.get("target")
    expr = stmt.get("expr")
    if not is_var(tgt):
        return
    vname = tgt["name"]
    if is_var(expr):
        env[vname] = ("sym", expr["name"])
    elif is_num(expr):
        env[vname] = ("num", expr["value"])
    else:
        env.pop(vname, None)


def analyze_stmt_list(
        stmts: List[dict],
        multiplier: Expr,
        env: Dict[str, Tuple[str, Any]],
) -> Tuple[Expr, Expr, Expr, List[LineCostInternal]]:
    """Analiza una lista de sentencias.
    
    Args:
        stmts: Lista de sentencias a analizar
        multiplier: Multiplicador de costo actual
        env: Entorno con variables
        
    Returns:
        Tupla con (costo_peor, costo_mejor, costo_promedio, líneas)
    """
    worst_costs: List[Expr] = []
    best_costs: List[Expr] = []
    avg_costs: List[Expr] = []
    all_lines: List[LineCostInternal] = []

    for stmt in stmts:
        w, b, a, lines = analyze_stmt(stmt, multiplier, env)
        worst_costs.append(w)
        best_costs.append(b)
        avg_costs.append(a)
        all_lines.extend(lines)

        if stmt.get("kind") == "assign":
            env_record_assign(env, stmt)

    total_worst = cost_seq(*worst_costs) if worst_costs else const(0)
    total_best = cost_seq(*best_costs) if best_costs else const(0)
    total_avg = cost_seq(*avg_costs) if avg_costs else const(0)

    return total_worst, total_best, total_avg, all_lines


def analyze_stmt(
        stmt: dict,
        multiplier: Expr,
        env: Dict[str, Tuple[str, Any]],
) -> Tuple[Expr, Expr, Expr, List[LineCostInternal]]:
    """Analiza una sentencia individual.
    
    Args:
        stmt: Sentencia a analizar
        multiplier: Multiplicador de costo actual
        env: Entorno con variables
        
    Returns:
        Tupla con (costo_peor, costo_mejor, costo_promedio, líneas)
    """
    kind = stmt.get("kind")

    if kind == "assign":
        return analyze_assign(stmt, multiplier)
    elif kind == "for":
        return analyze_for(stmt, multiplier, env)
    elif kind == "while":
        return analyze_while(stmt, multiplier, env)
    elif kind == "if":
        return analyze_if(stmt, multiplier, env)
    elif kind == "repeat":
        return analyze_repeat(stmt, multiplier, env)
    elif kind == "block":
        body = stmt.get("stmts", [])
        return analyze_stmt_list(body, multiplier, env)
    elif kind == "call":
        line = get_line(stmt)
        c = cost_assign()
        total = mul(multiplier, c)
        line_cost = LineCostInternal(
            line=line,
            kind="call",
            text=None,
            multiplier=multiplier,
            cost_worst=total,
            cost_best=total,
            cost_avg=total,
        )
        return total, total, total, [line_cost]

    c = const(1)
    return c, c, c, []


def analyze_assign(stmt: dict, multiplier: Expr) -> Tuple[Expr, Expr, Expr, List[LineCostInternal]]:
    """Analiza una sentencia de asignación.
    
    Args:
        stmt: Sentencia de asignación
        multiplier: Multiplicador de costo actual
        
    Returns:
        Tupla con (costo_peor, costo_mejor, costo_promedio, líneas)
    """
    line = get_line(stmt)
    c = cost_assign()
    total = mul(multiplier, c)

    line_cost = LineCostInternal(
        line=line,
        kind="assign",
        text=None,
        multiplier=multiplier,
        cost_worst=total,
        cost_best=total,
        cost_avg=total,
    )

    return total, total, total, [line_cost]


def analyze_for(
        stmt: dict,
        multiplier: Expr,
        env: Dict[str, Tuple[str, Any]],
) -> Tuple[Expr, Expr, Expr, List[LineCostInternal]]:
    """Analiza un bucle FOR.
    
    Args:
        stmt: Sentencia FOR
        multiplier: Multiplicador de costo actual
        env: Entorno con variables
        
    Returns:
        Tupla con (costo_peor, costo_mejor, costo_promedio, líneas)
    """
    line = get_line(stmt)
    start = stmt.get("start")
    end = stmt.get("end")
    var = stmt.get("var")

    is_triangular, triangular_var = detect_triangular_loop(start, end, var, env)
    iters = estimate_for_iterations(start, end, var, is_triangular, triangular_var, env)

    update_env_from_for(var, end, env)

    body = stmt.get("body", [])
    body_multiplier = mul(multiplier, iters)
    body_w, body_b, body_a, body_lines = analyze_stmt_list(body, body_multiplier, dict(env))

    total_w = body_w
    total_b = body_b
    total_a = body_a

    for_line = LineCostInternal(
        line=line,
        kind="for",
        text=None,
        multiplier=multiplier,
        cost_worst=const(0),
        cost_best=const(0),
        cost_avg=const(0),
    )

    return total_w, total_b, total_a, [for_line] + body_lines


def analyze_if(
    stmt: dict,
    multiplier: Expr,
    env: Dict[str, Tuple[str, Any]],
) -> Tuple[Expr, Expr, Expr, List[LineCostInternal]]:
    """Analiza una sentencia condicional IF.
    
    Estrategia:
    - Analiza ramas THEN y ELSE por separado
    - PEOR CASO: toma la rama con mayor grado; si son iguales, usa heurística de líneas
    - MEJOR CASO: toma la rama con menor grado; si son iguales, usa heurística inversa
    - PROMEDIO: usa combinación simple de ambas ramas como aproximación
    
    Args:
        stmt: Sentencia IF
        multiplier: Multiplicador de costo actual
        env: Entorno con variables
        
    Returns:
        Tupla con (costo_peor, costo_mejor, costo_promedio, líneas)
    """

    line = get_line(stmt)
    then_body = stmt.get("then_body", [])
    else_body = stmt.get("else_body", [])

    then_w, then_b, then_a, then_lines = analyze_stmt_list(
        then_body, multiplier, dict(env)
    )

    if else_body:
        else_w, else_b, else_a, else_lines = analyze_stmt_list(
            else_body, multiplier, dict(env)
        )
    else:
        else_w = else_b = else_a = const(0)
        else_lines: List[LineCostInternal] = []

    then_deg = degree(then_w)
    else_deg = degree(else_w)

    if then_deg > else_deg:
        total_w = cost_seq(cost_compare(), then_w)
        for lc in else_lines:
            lc.cost_worst = const(0)

    elif else_deg > then_deg:
        total_w = cost_seq(cost_compare(), else_w)
        for lc in then_lines:
            lc.cost_worst = const(0)

    else:
        then_weight = branch_weight(then_lines)
        else_weight = branch_weight(else_lines)

        if then_weight >= else_weight:
            total_w = cost_seq(cost_compare(), then_w)
            for lc in else_lines:
                lc.cost_worst = const(0)
        else:
            total_w = cost_seq(cost_compare(), else_w)
            for lc in then_lines:
                lc.cost_worst = const(0)

    then_deg_b = degree(then_b)
    else_deg_b = degree(else_b)

    if then_deg_b < else_deg_b:
        total_b = cost_seq(cost_compare(), then_b)
        for lc in else_lines:
            lc.cost_best = const(0)

    elif else_deg_b < then_deg_b:
        total_b = cost_seq(cost_compare(), else_b)
        for lc in then_lines:
            lc.cost_best = const(0)

    else:
        then_weight = branch_weight(then_lines)
        else_weight = branch_weight(else_lines)

        if then_weight <= else_weight:
            total_b = cost_seq(cost_compare(), then_b)
            for lc in else_lines:
                lc.cost_best = const(0)
        else:
            total_b = cost_seq(cost_compare(), else_b)
            for lc in then_lines:
                lc.cost_best = const(0)

    total_a = cost_seq(
        cost_compare(),
        add(then_a, else_a),
    )

    if_line = LineCostInternal(
        line=line,
        kind="if",
        text=None,
        multiplier=multiplier,
        cost_worst=mul(multiplier, cost_compare()),
        cost_best=mul(multiplier, cost_compare()),
        cost_avg=mul(multiplier, cost_compare()),
    )

    return total_w, total_b, total_a, [if_line] + then_lines + else_lines


def analyze_while(
        stmt: dict,
        multiplier: Expr,
        env: Dict[str, Tuple[str, Any]],
) -> Tuple[Expr, Expr, Expr, List[LineCostInternal]]:
    """Analiza un bucle WHILE.
    
    Args:
        stmt: Sentencia WHILE
        multiplier: Multiplicador de costo actual
        env: Entorno con variables
        
    Returns:
        Tupla con (costo_peor, costo_mejor, costo_promedio, líneas)
    """
    line = get_line(stmt)
    cond = stmt.get("cond", {})
    body = stmt.get("body", [])

    bs_iters = detect_binary_search_while(cond, body, env)
    if bs_iters is not None:
        body_multiplier = mul(multiplier, bs_iters)
        body_w, body_b, body_a, body_lines = analyze_stmt_list(body, body_multiplier, dict(env))

        total_w = body_w
        total_a = body_a
        total_b = const(1)

        while_line = LineCostInternal(
            line=line,
            kind="while",
            text=None,
            multiplier=multiplier,
            cost_worst=const(0),
            cost_best=const(0),
            cost_avg=const(0),
        )
        return total_w, total_b, total_a, [while_line] + body_lines

    ctrl_var = None
    if isinstance(cond, dict) and cond.get("kind") == "binop":
        if is_var(cond.get("left")):
            ctrl_var = cond.get("left").get("name")
        elif is_var(cond.get("right")):
            ctrl_var = cond.get("right").get("name")

    iters = None
    th = None

    if ctrl_var:
        if cond_var_gt_const(cond, ctrl_var):
            k = assign_div_const(body, ctrl_var)
            if k:
                init = env.get(ctrl_var)
                if init and init[0] == "sym":
                    from ..domain.expr import log as make_log
                    iters = make_log(sym(init[1]), const(k))
                else:
                    from ..domain.expr import log as make_log
                    iters = make_log(sym("n"), const(k))

        th = cond_var_lt_sym_or_const(cond, ctrl_var)
        if th and not iters:
            k = assign_mul_const(body, ctrl_var)
            if k:
                if th[0] == "sym":
                    from ..domain.expr import log as make_log
                    iters = make_log(sym(th[1]), const(k))
                else:
                    iters = const(1)

        if not iters and cond_var_gt_const(cond, ctrl_var) and assign_sub_const(body, ctrl_var):
            iters = sym("n")

        if not iters and th and assign_add_const(body, ctrl_var):
            iters = sym("n")

    if iters is None:
        iters = sym("n")

    body_multiplier = mul(multiplier, iters)
    body_w, body_b, body_a, body_lines = analyze_stmt_list(body, body_multiplier, dict(env))

    total_w = body_w
    total_b = body_b
    total_a = body_a

    if is_adaptive_sort_while(cond, body):
        n_sym = sym("n")
        n2 = mul(n_sym, n_sym)
        total_w = mul(multiplier, n2)
        total_a = total_w
        total_b = mul(multiplier, n_sym)
    elif insertion_sort_inner_while(cond, body):
        total_b = const(1)
    elif is_found_flag_while(cond, body):
        total_b = const(1)
    elif while_has_early_exit_condition(cond, body):
        total_b = const(1)
    elif is_sentinel_search_while(cond, body):
        total_b = const(1)
    elif while_has_index_jump_exit(cond, body):
        total_b = const(1)

    while_line = LineCostInternal(
        line=line, kind="while", text=None, multiplier=multiplier,
        cost_worst=const(0), cost_best=const(0), cost_avg=const(0),
    )

    return total_w, total_b, total_a, [while_line] + body_lines


def analyze_repeat(
        stmt: dict,
        multiplier: Expr,
        env: Dict[str, Tuple[str, Any]],
) -> Tuple[Expr, Expr, Expr, List[LineCostInternal]]:
    """Analiza un bucle REPEAT.
    
    Args:
        stmt: Sentencia REPEAT
        multiplier: Multiplicador de costo actual
        env: Entorno con variables
        
    Returns:
        Tupla con (costo_peor, costo_mejor, costo_promedio, líneas)
    """
    line = get_line(stmt)
    body = stmt.get("body", [])

    iters = sym("n")
    body_multiplier = mul(multiplier, iters)
    body_w, body_b, body_a, body_lines = analyze_stmt_list(body, body_multiplier, dict(env))

    total_w = body_w
    total_b = body_b
    total_a = body_a

    repeat_line = LineCostInternal(
        line=line,
        kind="repeat",
        text=None,
        multiplier=multiplier,
        cost_worst=const(0),
        cost_best=const(0),
        cost_avg=const(0),
    )

    return total_w, total_b, total_a, [repeat_line] + body_lines