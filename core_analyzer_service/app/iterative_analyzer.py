"""
iterative_analyzer.py - Analizador de complejidad para algoritmos iterativos
============================================================================

Analiza algoritmos que NO contienen recursión, calculando:
- Costo línea por línea (worst, best, avg).
- Complejidad global en notaciones O, Ω, Θ.

Estrategia:
- Propagar un "multiplier" (cuántas veces se ejecuta cada línea).
- Para bucles: estimar iteraciones (n, log n, n², etc.).
- Para if: considerar peor/mejor caso según ramas.
"""

from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass

from .complexity_ir import (
    Expr, const, sym, mul, add, alt, log,
    big_o_str_from_expr, big_omega_str_from_expr,
)
from .cost_model import cost_assign, cost_compare, cost_seq
from .schemas import LineCost


# ---------------------------------------------------------------------------
# ESTRUCTURAS DE DATOS INTERNAS
# ---------------------------------------------------------------------------

@dataclass
class LineCostInternal:
    """Representa el costo de una línea internamente (con IR)."""
    line: int
    kind: str
    text: Optional[str]
    multiplier: Expr
    cost_worst: Expr
    cost_best: Expr
    cost_avg: Expr


@dataclass
class ProgramCost:
    """Resultado completo del análisis de un programa."""
    worst: Expr
    best: Expr
    avg: Expr
    lines: List[LineCostInternal]


# ---------------------------------------------------------------------------
# UTILIDADES AST
# ---------------------------------------------------------------------------

def _is_var(node, name: str = None) -> bool:
    """Verifica si un nodo es una variable (opcionalmente con nombre específico)."""
    return isinstance(node, dict) and node.get("kind") == "var" and (name is None or node.get("name") == name)


def _is_num(node, value=None) -> bool:
    """Verifica si un nodo es un número literal."""
    return isinstance(node, dict) and node.get("kind") == "num" and (value is None or node.get("value") == value)


def _is_binop(node, op: str) -> bool:
    """Verifica si un nodo es un operador binario."""
    if not (isinstance(node, dict) and node.get("kind") == "binop"):
        return False
    node_op = node.get("op", "")
    # Normalizar operadores Unicode
    if node_op == "≤":
        node_op = "<="
    elif node_op == "≥":
        node_op = ">="
    elif node_op == "≠":
        node_op = "!="
    return node_op == op


def _get_line(node: dict) -> int:
    """Extrae el número de línea de un nodo del AST."""
    loc = node.get("loc")
    if loc and isinstance(loc, dict):
        return loc.get("line", 0)
    return 0


# ---------------------------------------------------------------------------
# ANÁLISIS DE EXPRESIONES (para inferir iteraciones)
# ---------------------------------------------------------------------------

def _cond_var_lt_sym_or_const(cond: dict, varname: str) -> Tuple[str, any] | None:
    """Detecta condiciones tipo: var < límite."""
    if _is_binop(cond, "<") or _is_binop(cond, "<="):
        left, right = cond.get("left"), cond.get("right")
        if _is_var(left, varname):
            if _is_num(right):
                return ("num", right["value"])
            if _is_var(right):
                return ("sym", right["name"])
    return None


def _cond_var_gt_const(cond: dict, varname: str) -> bool:
    """Detecta condiciones tipo: var > constante."""
    if _is_binop(cond, ">") or _is_binop(cond, ">="):
        left, right = cond.get("left"), cond.get("right")
        return _is_var(left, varname) and _is_num(right)
    return False


def _assign_div_const(body: List[dict], varname: str) -> int | None:
    """Busca asignaciones tipo: var <- var / k (k>1)."""
    for st in body:
        if st.get("kind") != "assign":
            continue
        tgt = st.get("target")
        expr = st.get("expr")
        if not _is_var(tgt, varname):
            continue
        if _is_binop(expr, "/") and _is_var(expr.get("left"), varname) and _is_num(expr.get("right")):
            k = expr["right"]["value"]
            if isinstance(k, (int, float)) and k > 1:
                return int(k)
    return None


def _assign_mul_const(body: List[dict], varname: str) -> int | None:
    """Busca asignaciones tipo: var <- var * k (k>1)."""
    for st in body:
        if st.get("kind") != "assign":
            continue
        tgt = st.get("target")
        expr = st.get("expr")
        if not _is_var(tgt, varname):
            continue
        if _is_binop(expr, "*") and _is_var(expr.get("left"), varname) and _is_num(expr.get("right")):
            k = expr["right"]["value"]
            if isinstance(k, (int, float)) and k > 1:
                return int(k)
    return None


def _assign_add_const(body: List[dict], varname: str) -> int | None:
    """Busca asignaciones tipo: var <- var + k (k>0)."""
    for st in body:
        if st.get("kind") != "assign":
            continue
        tgt = st.get("target")
        expr = st.get("expr")
        if not _is_var(tgt, varname):
            continue
        if _is_binop(expr, "+") and _is_var(expr.get("left"), varname) and _is_num(expr.get("right")):
            k = expr["right"]["value"]
            if isinstance(k, (int, float)) and k > 0:
                return int(k)
    return None


def _assign_sub_const(body: List[dict], varname: str) -> int | None:
    """Busca asignaciones tipo: var <- var - k (k>0)."""
    for st in body:
        if st.get("kind") != "assign":
            continue
        tgt = st.get("target")
        expr = st.get("expr")
        if not _is_var(tgt, varname):
            continue
        if _is_binop(expr, "-") and _is_var(expr.get("left"), varname) and _is_num(expr.get("right")):
            k = expr["right"]["value"]
            if isinstance(k, (int, float)) and k > 0:
                return int(k)
    return None


# ---------------------------------------------------------------------------
# ANALIZADORES POR TIPO DE SENTENCIA
# ---------------------------------------------------------------------------

def _analyze_stmt_list(
        stmts: List[dict],
        multiplier: Expr,
        env: Dict[str, Tuple[str, any]],
) -> Tuple[Expr, Expr, Expr, List[LineCostInternal]]:
    """
    Analiza una lista secuencial de sentencias.

    Args:
        stmts: Lista de sentencias del AST.
        multiplier: Factor de repetición heredado (cuántas veces se ejecuta esta secuencia).
        env: Entorno con valores iniciales de variables (para inferir límites de bucles).

    Returns:
        Tupla (worst, best, avg, lines) donde lines es el costo línea por línea.
    """
    worst_costs: List[Expr] = []
    best_costs: List[Expr] = []
    avg_costs: List[Expr] = []
    all_lines: List[LineCostInternal] = []

    for stmt in stmts:
        w, b, a, lines = _analyze_stmt(stmt, multiplier, env)
        worst_costs.append(w)
        best_costs.append(b)
        avg_costs.append(a)
        all_lines.extend(lines)

        # Actualizar entorno si es asignación simple
        if stmt.get("kind") == "assign":
            _env_record_assign(env, stmt)

    total_worst = cost_seq(*worst_costs) if worst_costs else const(0)
    total_best = cost_seq(*best_costs) if best_costs else const(0)
    total_avg = cost_seq(*avg_costs) if avg_costs else const(0)

    return total_worst, total_best, total_avg, all_lines


def _analyze_stmt(
        stmt: dict,
        multiplier: Expr,
        env: Dict[str, Tuple[str, any]],
) -> Tuple[Expr, Expr, Expr, List[LineCostInternal]]:
    """
    Analiza una sentencia individual.

    Returns:
        (worst, best, avg, lines)
    """
    kind = stmt.get("kind")

    if kind == "assign":
        return _analyze_assign(stmt, multiplier)
    elif kind == "for":
        return _analyze_for(stmt, multiplier, env)
    elif kind == "while":
        return _analyze_while(stmt, multiplier, env)
    elif kind == "if":
        return _analyze_if(stmt, multiplier, env)
    elif kind == "repeat":
        return _analyze_repeat(stmt, multiplier, env)
    elif kind == "block":
        body = stmt.get("stmts", [])
        return _analyze_stmt_list(body, multiplier, env)
    elif kind == "call":
        # Llamadas a procedimiento: asumir costo constante (mejorar después)
        line = _get_line(stmt)
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

    # Otros casos (desconocidos): costo constante
    c = const(1)
    return c, c, c, []


def _analyze_assign(stmt: dict, multiplier: Expr) -> Tuple[Expr, Expr, Expr, List[LineCostInternal]]:
    """Analiza una asignación: costo constante."""
    line = _get_line(stmt)
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


from typing import Optional, Tuple


def _upper_bound_symbol(end: dict) -> Optional[Tuple[str, str]]:
    """
    Intenta extraer un símbolo dominante del límite superior de un for.

    Casos típicos:
    - end = n            -> ("sym", "n")
    - end = n - 1        -> ("sym", "n")
    - end = n - i        -> ("sym", "n")
    - end = n + 10       -> ("sym", "n")
    - end = m            -> ("sym", "m")
    """
    # Caso simple: variable
    if _is_var(end):
        return ("sym", end["name"])

    # Caso binop +/- con algo más
    if (
            isinstance(end, dict)
            and end.get("kind") == "binop"
            and end.get("op") in ("+", "-")
    ):
        left = end.get("left")
        right = end.get("right")

        # n - 1, n + 1, n - i, n + i, ...
        if _is_var(left) and (_is_num(right) or _is_var(right)):
            return ("sym", left["name"])

    return None


def _analyze_for(
        stmt: dict,
        multiplier: Expr,
        env: Dict[str, Tuple[str, any]],
) -> Tuple[Expr, Expr, Expr, List[LineCostInternal]]:
    """Analiza un bucle FOR, incluyendo bucles triangulares."""
    line = _get_line(stmt)
    start = stmt.get("start")
    end = stmt.get("end")
    var = stmt.get("var")

    # ========== DETECCIÓN DE BUCLES TRIANGULARES ==========
    # Caso 1: for j <- 1 to i (donde i es variable del bucle externo)
    # Caso 2: for j <- i to n (bucle inverso triangular)

    is_triangular = False
    triangular_var = None

    # Verificar si el límite superior es una variable (no 'n', 'm', etc. globales)
    if _is_var(end):
        end_var_name = end["name"]
        # Si el límite es una variable que NO es un parámetro del programa
        # (asumimos que n, m, k son globales, pero i, j son locales)
        if end_var_name in ("i", "j", "k", "p", "q") and end_var_name != var:
            is_triangular = True
            triangular_var = end_var_name

    # Verificar si el inicio es una variable (caso: for j <- i to n)
    if _is_var(start):
        start_var_name = start["name"]
        if start_var_name in ("i", "j", "k", "p", "q") and start_var_name != var:
            is_triangular = True
            triangular_var = start_var_name

    # ========== ESTIMACIÓN DE ITERACIONES ==========

    if is_triangular:
        # Bucle triangular: el efecto Σ ya lo mete el multiplicador externo.
        outer_sym = env.get(triangular_var)
        if outer_sym and outer_sym[0] == "sym":
            outer_limit = sym(outer_sym[1])
        else:
            outer_limit = sym("n")

        # Aquí SOLO usamos ~ outer_limit (≈ n).
        # El n²/n³ sale de multiplicar con el bucle externo (ya lo probaste con summation_test).
        iters = outer_limit

    else:
        ub = _upper_bound_symbol(end)

        if _is_num(start, 1) and ub and ub[0] == "sym":
            # for i <- 1 to n
            # for i <- 1 to n - 1
            # for j <- 1 to n - i   (peor caso ~ n)
            iters = sym(ub[1])

        elif _is_num(start, 1) and _is_num(end):
            # for i <- 1 to 10  (constante)
            iters = const(max(0, end["value"]))

        elif ub and ub[0] == "sym":
            # Otros casos, pero al menos usamos el símbolo dominante
            iters = sym(ub[1])

        else:
            # Fallback muy conservador
            iters = const(1)

    # Actualizar entorno con la variable del for
    # Actualizar entorno con la variable del for
    ub = _upper_bound_symbol(end)
    if var and ub and ub[0] == "sym":
        # i -> n, j -> n, etc. incluso si el límite era n-1, n-i, ...
        env[var] = ("sym", ub[1])
    elif var and _is_num(end):
        env[var] = ("num", end["value"])

    # Analizar el cuerpo con el nuevo multiplicador
    body = stmt.get("body", [])

    if is_triangular:
        # Para bucles triangulares, el multiplicador del cuerpo es diferente
        # Ejemplo: outer loop multiplier = n, inner loop = i
        # Total = Σᵢ₌₁ⁿ (multiplier * i) ≈ multiplier * n²
        body_multiplier = mul(multiplier, iters)
    else:
        body_multiplier = mul(multiplier, iters)

    body_w, body_b, body_a, body_lines = _analyze_stmt_list(body, body_multiplier, dict(env))

    # ✅ El cuerpo YA tiene el costo total (multiplicado por iters)
    total_w = body_w
    total_b = body_b
    total_a = body_a

    # Línea del for: NO suma al total
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


def _analyze_while(
        stmt: dict,
        multiplier: Expr,
        env: Dict[str, Tuple[str, any]],
) -> Tuple[Expr, Expr, Expr, List[LineCostInternal]]:
    """Analiza un bucle WHILE con detección de patrones."""
    line = _get_line(stmt)
    cond = stmt.get("cond", {})
    body = stmt.get("body", [])

    # Detectar variable de control
    ctrl_var = None
    if isinstance(cond, dict) and cond.get("kind") == "binop":
        if _is_var(cond.get("left")):
            ctrl_var = cond.get("left").get("name")
        elif _is_var(cond.get("right")):
            ctrl_var = cond.get("right").get("name")

    # Intentar inferir número de iteraciones
    iters = None

    if ctrl_var:
        # Patrón: halving (i <- i / 2)
        if _cond_var_gt_const(cond, ctrl_var):
            k = _assign_div_const(body, ctrl_var)
            if k:
                init = env.get(ctrl_var)
                if init and init[0] == "sym":
                    iters = log(sym(init[1]), const(k))
                else:
                    iters = log(sym("n"), const(k))

        # Patrón: doubling (i <- i * 2)
        th = _cond_var_lt_sym_or_const(cond, ctrl_var)
        if th and not iters:
            k = _assign_mul_const(body, ctrl_var)
            if k:
                if th[0] == "sym":
                    iters = log(sym(th[1]), const(k))
                else:
                    iters = const(1)

        # Patrón: decremento lineal (i <- i - k)
        if not iters and _cond_var_gt_const(cond, ctrl_var) and _assign_sub_const(body, ctrl_var):
            iters = sym("n")

        # Patrón: incremento lineal (i <- i + k)
        if not iters and th and _assign_add_const(body, ctrl_var):
            iters = sym("n")

    # Si no se reconoció el patrón, asumir lineal (conservador)
    if iters is None:
        iters = sym("n")

    # Analizar el cuerpo
    body_multiplier = mul(multiplier, iters)
    body_w, body_b, body_a, body_lines = _analyze_stmt_list(body, body_multiplier, dict(env))

    # ✅ El cuerpo YA tiene el costo multiplicado
    total_w = body_w
    total_b = body_b
    total_a = body_a

    # Línea del while: NO suma al total (ya está en body)
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


def _analyze_if(
        stmt: dict,
        multiplier: Expr,
        env: Dict[str, Tuple[str, any]],
) -> Tuple[Expr, Expr, Expr, List[LineCostInternal]]:
    """Analiza un condicional IF."""
    line = _get_line(stmt)
    then_body = stmt.get("then_body", [])
    else_body = stmt.get("else_body", [])

    # Analizar ambas ramas
    then_w, then_b, then_a, then_lines = _analyze_stmt_list(then_body, multiplier, dict(env))

    if else_body:
        else_w, else_b, else_a, else_lines = _analyze_stmt_list(else_body, multiplier, dict(env))
    else:
        else_w = else_b = else_a = const(0)
        else_lines = []

    # Peor caso: la rama más costosa
    total_w = cost_seq(cost_compare(), alt(then_w, else_w))
    # Mejor caso: la rama más barata
    total_b = cost_seq(cost_compare(), alt(then_b, else_b))
    # Promedio: mitad y mitad (aproximación simple)
    total_a = cost_seq(cost_compare(), add(mul(then_a, const(1)), mul(else_a, const(1))))

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


def _analyze_repeat(
        stmt: dict,
        multiplier: Expr,
        env: Dict[str, Tuple[str, any]],
) -> Tuple[Expr, Expr, Expr, List[LineCostInternal]]:
    """Analiza un bucle REPEAT-UNTIL (asume lineal por ahora)."""
    line = _get_line(stmt)
    body = stmt.get("body", [])

    # Conservador: asumir n iteraciones
    iters = sym("n")
    body_multiplier = mul(multiplier, iters)
    body_w, body_b, body_a, body_lines = _analyze_stmt_list(body, body_multiplier, dict(env))

    # ✅ El cuerpo YA tiene el costo multiplicado
    total_w = body_w
    total_b = body_b
    total_a = body_a

    # Línea del repeat: NO suma al total
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


def _env_record_assign(env: Dict[str, Tuple[str, any]], stmt: dict) -> None:
    """Registra asignaciones simples en el entorno (para inferir límites)."""
    if stmt.get("kind") != "assign":
        return
    tgt = stmt.get("target")
    expr = stmt.get("expr")
    if not _is_var(tgt):
        return
    vname = tgt["name"]
    if _is_var(expr):
        env[vname] = ("sym", expr["name"])
    elif _is_num(expr):
        env[vname] = ("num", expr["value"])
    else:
        env.pop(vname, None)


# ---------------------------------------------------------------------------
# API PRINCIPAL
# ---------------------------------------------------------------------------

def _extract_main_body(ast: dict) -> List[dict]:
    """Extrae el cuerpo principal del programa (lista de sentencias)."""
    if not isinstance(ast, dict):
        return []

    kind = ast.get("kind")

    if kind == "program":
        body = ast.get("body", [])

        # Si hay un procedimiento único, analizamos su cuerpo
        if len(body) == 1 and isinstance(body[0], dict) and body[0].get("kind") == "proc":
            return body[0].get("body", [])

        # Si hay sentencias sueltas, las analizamos
        if body and isinstance(body[0], dict) and body[0].get("kind") != "proc":
            return body

        return []

    if kind == "proc":
        return ast.get("body", [])

    return ast.get("body", []) if isinstance(ast.get("body"), list) else []


def analyze_program(ast: dict) -> ProgramCost:
    """
    Analiza un programa iterativo completo.

    Args:
        ast: AST del programa (ya clasificado como iterativo).

    Returns:
        ProgramCost con costos globales y línea por línea.
    """
    stmts = _extract_main_body(ast)
    env: Dict[str, Tuple[str, any]] = {}
    multiplier = const(1)

    worst, best, avg, lines = _analyze_stmt_list(stmts, multiplier, env)

    return ProgramCost(
        worst=worst,
        best=best,
        avg=avg,
        lines=lines,
    )


def serialize_line_costs(lines: List[LineCostInternal]) -> List[LineCost]:
    """Convierte costos internos (con IR) a formato de respuesta (strings)."""
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
