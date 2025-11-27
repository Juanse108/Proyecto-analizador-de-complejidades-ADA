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

from .analyzer import _make_log
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
    """Busca asignaciones tipo: var <- var / k o var <- var div k (k>1)."""
    for st in body:
        if st.get("kind") != "assign":
            continue
        tgt = st.get("target")
        expr = st.get("expr")
        if not _is_var(tgt, varname):
            continue

        # Aceptar tanto "/" como "div"
        if (
                isinstance(expr, dict)
                and expr.get("kind") == "binop"
                and expr.get("op") in ("/", "div")
                and _is_var(expr.get("left"), varname)
                and _is_num(expr.get("right"))
        ):
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


def _expr_uses_var(node, varname: str) -> bool:
    """
    Devuelve True si la expresión (AST) usa la variable con nombre `varname`.
    Recorre dicts y listas recursivamente.
    """
    if isinstance(node, dict):
        # Nodo variable
        if node.get("kind") == "var" and node.get("name") == varname:
            return True
        # Explorar todos los campos del nodo
        for v in node.values():
            if _expr_uses_var(v, varname):
                return True
        return False
    elif isinstance(node, list):
        return any(_expr_uses_var(elem, varname) for elem in node)
    else:
        return False


def _stmt_list_has_assign_to_var(body: List[dict], varname: str) -> bool:
    """
    Devuelve True si en la lista de sentencias hay alguna asignación a `varname`
    (directa o anidada en if / blocks / bucles).
    """

    def _visit(stmts: List[dict]) -> bool:
        for st in stmts:
            kind = st.get("kind")
            if kind == "assign":
                tgt = st.get("target")
                if _is_var(tgt, varname):
                    return True
            elif kind == "if":
                if _visit(st.get("then_body", [])):
                    return True
                if _visit(st.get("else_body", [])):
                    return True
            elif kind == "block":
                if _visit(st.get("stmts", [])):
                    return True
            elif kind in ("for", "while", "repeat"):
                if _visit(st.get("body", [])):
                    return True
        return False

    return _visit(body)


def _is_found_flag_while(cond: dict, body: List[dict]) -> bool:
    """
    Heurística MUY específica:
    - La condición del while usa una variable llamada `found`.
    - El cuerpo asigna a `found` en algún punto.

    Esto cubre casos como:
        while (idx <= n and found = F) do
            if (A[idx] = x) then
                found <- T
            else
                idx <- idx + 1
    """
    return _expr_uses_var(cond, "found") and _stmt_list_has_assign_to_var(body, "found")


# Agregar estas funciones DESPUÉS de _is_found_flag_while

def _collect_vars_in_expr(node, acc: set[str]) -> None:
    """
    Recorre recursivamente un nodo de expresión y acumula los nombres de variables.
    Sirve para saber qué variables aparecen en la condición del while.
    """
    if isinstance(node, dict):
        kind = node.get("kind")
        if kind == "var":
            name = node.get("name")
            if name is not None:
                acc.add(name)
        # Recorrer recursivamente todos los hijos
        for v in node.values():
            _collect_vars_in_expr(v, acc)
    elif isinstance(node, list):
        for elem in node:
            _collect_vars_in_expr(elem, acc)


def _find_linear_index_var(body: List[dict]) -> Optional[str]:
    """
    Busca una variable que se actualice de forma lineal en el cuerpo:
        i <- i + c   o   i <- i - c  (c constante)
    Recorre recursivamente if, blocks y bucles.
    """

    def _visit(stmts: List[dict]) -> Optional[str]:
        for st in stmts:
            kind = st.get("kind")

            if kind == "assign":
                tgt = st.get("target")
                expr = st.get("expr")
                if not _is_var(tgt):
                    continue
                if not isinstance(expr, dict):
                    continue
                varname = tgt.get("name")

                # Patrón: i <- i + k
                if _is_binop(expr, "+") and _is_var(expr.get("left"), varname) and _is_num(expr.get("right")):
                    return varname

                # Patrón: i <- i - k
                if _is_binop(expr, "-") and _is_var(expr.get("left"), varname) and _is_num(expr.get("right")):
                    return varname

            elif kind == "if":
                # Buscar dentro de then y else
                found = _visit(st.get("then_body", []))
                if found:
                    return found
                found = _visit(st.get("else_body", []))
                if found:
                    return found

            elif kind == "block":
                found = _visit(st.get("stmts", []))
                if found:
                    return found

            elif kind in ("for", "while", "repeat"):
                # Por generalidad, también miramos dentro de otros bucles
                found = _visit(st.get("body", []))
                if found:
                    return found

        return None

    return _visit(body)


def _body_has_nested_loops(body: List[dict]) -> bool:
    """
    Devuelve True si en el body hay algún for/while/repeat
    (directo o anidado).
    """
    for st in body:
        kind = st.get("kind")
        if kind in ("for", "while", "repeat"):
            return True
        # Mirar dentro de if / block
        if kind == "if":
            if _body_has_nested_loops(st.get("then_body", [])):
                return True
            if _body_has_nested_loops(st.get("else_body", [])):
                return True
        elif kind == "block":
            if _body_has_nested_loops(st.get("stmts", [])):
                return True
    return False


def _expr_has_logical_op(node) -> bool:
    """
    Devuelve True si en la expresión aparece algún operador lógico (and / or).
    Sirve para distinguir condiciones como:
        i <= n                  -> False
        i <= n and A[i] != x    -> True
    """
    if isinstance(node, dict):
        if node.get("kind") == "binop":
            op = node.get("op")
            if op in ("and", "or"):
                return True
            # Seguir buscando en hijos
            return _expr_has_logical_op(node.get("left")) or _expr_has_logical_op(node.get("right"))
        # Otros nodos dict: recorrer valores
        return any(_expr_has_logical_op(v) for v in node.values())
    elif isinstance(node, list):
        return any(_expr_has_logical_op(elem) for elem in node)
    else:
        return False


def _is_search_like_while(cond: dict, body: List[dict]) -> bool:
    """
    Heurística para detectar while de tipo "búsqueda lineal" / "centinela" / "threshold".
    ...
    """
    # ❌ Nuevo: si la condición NO tiene AND/OR, no la consideramos búsqueda adaptativa
    if not _expr_has_logical_op(cond):
        return False

    # 0) Si hay bucles anidados, descartamos (ej: Bubble Sort)
    if _body_has_nested_loops(body):
        return False

    # 1) Buscar variable índice actualizada linealmente en el cuerpo
    idx = _find_linear_index_var(body)
    if not idx:
        return False

    # 2) Ver qué variables aparecen en la condición
    vars_in_cond: set[str] = set()
    _collect_vars_in_expr(cond, vars_in_cond)

    if idx not in vars_in_cond:
        return False

    # Debe haber al menos otra variable en la condición (A, x, found, threshold, etc.)
    if len(vars_in_cond) <= 1:
        return False

    return True


def _while_has_early_exit_condition(cond: dict, body: List[dict]) -> bool:
    """
    Detecta si un while tiene condición de salida temprana IMPLÍCITA:
    - La condición tiene múltiples variables (idx AND algo_más)
    - NO hay bucles anidados
    - Hay actualización lineal de índice

    Casos:
    1. while (idx <= n and A[idx] != x)  -> búsqueda con centinela
    2. while (idx <= n and count < max) -> contador con límite
    3. while (idx <= n and found = F)   -> bandera (ya lo cubre _is_found_flag_while)
    """
    # Si ya detectamos bandera 'found', no hace falta esto
    if _is_found_flag_while(cond, body):
        return False

    return _is_search_like_while(cond, body)


def _branch_has_index_jump_out(stmts: List[dict], idx: str, bound: str) -> bool:
    """
    True si en la rama hay una asignación tipo:
        idx <- bound + c   o   idx <- c + bound
    con c constante numérica.
    """
    for st in stmts:
        if st.get("kind") != "assign":
            continue
        tgt = st.get("target")
        expr = st.get("expr")
        if not _is_var(tgt, idx):
            continue
        if not (isinstance(expr, dict) and expr.get("kind") == "binop"):
            continue
        op = expr.get("op")
        if op not in ("+", "-"):
            continue
        left = expr.get("left")
        right = expr.get("right")
        # bound + c   o   c + bound
        if (_is_var(left, bound) and _is_num(right)) or (_is_num(left) and _is_var(right, bound)):
            return True
    return False


def _branch_has_linear_step(stmts: List[dict], idx: str) -> bool:
    """
    True si en la rama hay una asignación tipo:
        idx <- idx + c   o   idx <- idx - c
    con c constante numérica > 0.
    """
    for st in stmts:
        if st.get("kind") != "assign":
            continue
        tgt = st.get("target")
        expr = st.get("expr")
        if not _is_var(tgt, idx):
            continue
        if not (isinstance(expr, dict) and expr.get("kind") == "binop"):
            continue
        op = expr.get("op")
        if op not in ("+", "-"):
            continue
        left = expr.get("left")
        right = expr.get("right")
        if _is_var(left, idx) and _is_num(right):
            return True
    return False


def _while_has_index_jump_exit(cond: dict, body: List[dict]) -> bool:
    """
    Detecta while de búsqueda lineal con salida temprana codificada como:
        while (i <= n) do
            if (A[i] = x) then
                i <- n + 1      // salto para salir
            else
                i <- i + 1      // avance normal

    - Condición simple i <= n
    - Una rama salta el índice más allá del límite
    - La otra rama avanza linealmente el índice
    """
    if not (isinstance(cond, dict) and cond.get("kind") == "binop"):
        return False

    op = cond.get("op")
    if op == "≤":
        op = "<="
    if op not in ("<", "<="):
        return False

    left = cond.get("left")
    right = cond.get("right")
    if not (_is_var(left) and _is_var(right)):
        return False

    idx = left["name"]
    bound = right["name"]

    def _search(stmts: List[dict]) -> bool:
        for st in stmts:
            kind = st.get("kind")
            if kind == "if":
                then_body = st.get("then_body", [])
                else_body = st.get("else_body", [])

                # then: saltar, else: paso lineal
                if (_branch_has_index_jump_out(then_body, idx, bound) and
                        _branch_has_linear_step(else_body, idx)):
                    return True
                # o al revés
                if (_branch_has_index_jump_out(else_body, idx, bound) and
                        _branch_has_linear_step(then_body, idx)):
                    return True

                # seguir buscando anidado
                if _search(then_body) or _search(else_body):
                    return True

            elif kind in ("while", "for", "repeat", "block"):
                inner = st.get("body") or st.get("stmts") or []
                if _search(inner):
                    return True

        return False

    return _search(body)


def _insertion_sort_inner_while(cond: dict, body: List[dict]) -> bool:
    """
    Detecta el while interno de Insertion Sort.
    """
    if _body_has_nested_loops(body):
        return False

    idx_var = _find_linear_index_var(body)
    if not idx_var:
        return False

    vars_in_cond: set[str] = set()
    _collect_vars_in_expr(cond, vars_in_cond)

    if idx_var not in vars_in_cond or len(vars_in_cond) <= 1:
        return False

    if not _assign_sub_const(body, idx_var):
        return False

    return True


def _is_adaptive_sort_while(cond: dict, body: List[dict]) -> bool:
    """
    Detecta while de algoritmos de ordenamiento adaptativos (Bubble, Cocktail, etc.):

    Características:
    - Tiene bucles for anidados (indicador de algoritmo cuadrático)
    - Usa bandera de control (swapped, changed, etc.) en la condición
    - La bandera se asigna en el cuerpo

    Ejemplos:
    - while (swapped = T and passes < n) do
    - while (swapped = T) do
    """
    # 1) Debe tener bucles anidados (Bubble/Cocktail tienen for interno)
    if not _body_has_nested_loops(body):
        return False

    # 2) Buscar variables de bandera comunes
    flag_vars = {"swapped", "changed", "sorted", "done", "modified", "intercambiado"}

    vars_in_cond: set[str] = set()
    _collect_vars_in_expr(cond, vars_in_cond)

    # Ver si alguna bandera aparece en la condición
    for flag in flag_vars:
        if flag in vars_in_cond:
            # Verificar que se asigne en el cuerpo
            if _stmt_list_has_assign_to_var(body, flag):
                return True

    return False


def _is_sentinel_search_while(cond: dict, body: List[dict]) -> bool:
    """
    Detecta el patrón de búsqueda con centinela:

        while (A[idx] != x) do
            idx <- idx + 1

    - No hay bucles anidados en el cuerpo
    - Hay una variable índice que se incrementa linealmente
    - La condición compara A[idx] con alguna otra variable (x)
    """
    if _body_has_nested_loops(body):
        return False

    idx = _find_linear_index_var(body)
    if not idx:
        return False

    # La condición debería ser una comparación != entre algo con idx y otra cosa
    if not (isinstance(cond, dict) and cond.get("kind") == "binop"):
        return False

    if cond.get("op") not in ("!=", "<>"):
        return False

    left = cond.get("left")
    right = cond.get("right")

    # Queremos que en alguno de los lados aparezca idx
    vars_left: set[str] = set()
    vars_right: set[str] = set()
    _collect_vars_in_expr(left, vars_left)
    _collect_vars_in_expr(right, vars_right)

    if idx not in vars_left and idx not in vars_right:
        return False

    # Y que haya, al menos, otra variable distinta de idx (el valor buscado x)
    all_vars = vars_left | vars_right
    if len(all_vars) <= 1:
        return False

    return True


def _analyze_while(
        stmt: dict,
        multiplier: Expr,
        env: Dict[str, Tuple[str, any]],
) -> Tuple[Expr, Expr, Expr, List[LineCostInternal]]:
    """Analiza un bucle WHILE con detección avanzada de patrones."""
    line = _get_line(stmt)
    cond = stmt.get("cond", {})
    body = stmt.get("body", [])

    # ------------------------------------------------------------
    # 1) Caso especial: Binary Search
    # ------------------------------------------------------------
    bs_iters = _detect_binary_search_while(cond, body, env)
    if bs_iters is not None:
        # Peor y promedio: log n iteraciones
        body_multiplier = mul(multiplier, bs_iters)
        body_w, body_b, body_a, body_lines = _analyze_stmt_list(body, body_multiplier, dict(env))

        # Ajuste de casos:
        #   - Peor caso: Θ(log n)
        #   - Mejor caso: Θ(1)  (lo encuentra en la primera comparación)
        #   - Promedio: Θ(log n)
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

    # ------------------------------------------------------------
    # 2) Caso general: inferir iteraciones
    # ------------------------------------------------------------
    ctrl_var: Optional[str] = None
    if isinstance(cond, dict) and cond.get("kind") == "binop":
        if _is_var(cond.get("left")):
            ctrl_var = cond.get("left").get("name")
        elif _is_var(cond.get("right")):
            ctrl_var = cond.get("right").get("name")

    iters: Optional[Expr] = None
    th: Optional[Tuple[str, any]] = None

    if ctrl_var:
        # Halving: i <- i / k, condición i > c
        if _cond_var_gt_const(cond, ctrl_var):
            k = _assign_div_const(body, ctrl_var)
            if k:
                init = env.get(ctrl_var)
                if init and init[0] == "sym":
                    iters = log(sym(init[1]), const(k))
                else:
                    iters = log(sym("n"), const(k))

        # Doubling: i <- i * k, condición i < límite
        th = _cond_var_lt_sym_or_const(cond, ctrl_var)
        if th and not iters:
            k = _assign_mul_const(body, ctrl_var)
            if k:
                if th[0] == "sym":
                    iters = log(sym(th[1]), const(k))
                else:
                    iters = const(1)

        # Decremento lineal: i <- i - k, condición i > c
        if not iters and _cond_var_gt_const(cond, ctrl_var) and _assign_sub_const(body, ctrl_var):
            iters = sym("n")

        # Incremento lineal: i <- i + k, condición i < límite
        if not iters and th and _assign_add_const(body, ctrl_var):
            iters = sym("n")

    # Fallback conservador: asumimos O(n) si no sabemos mejor
    if iters is None:
        iters = sym("n")

    body_multiplier = mul(multiplier, iters)
    body_w, body_b, body_a, body_lines = _analyze_stmt_list(body, body_multiplier, dict(env))

    total_w = body_w
    total_b = body_b
    total_a = body_a

    # ------------------------------------------------------------
    # 3) Ajustes para mejor/peor caso (early exits, adaptativos, etc.)
    # ------------------------------------------------------------

    # 🔍 Ordenamiento adaptativo (Bubble, Cocktail): mejor caso lineal, peor caso cuadrático
    if _is_adaptive_sort_while(cond, body):
        # Queremos reflejar el patrón típico:
        #   - Peor caso: Θ(n²) por el for anidado dentro del while
        #   - Mejor caso: Θ(n) si ya está ordenado (1 pasada)
        n_sym = sym("n")
        n2 = mul(n_sym, n_sym)

        total_w = mul(multiplier, n2)  # O(n²)
        total_a = total_w  # Promedio ~ n² también
        total_b = mul(multiplier, n_sym)  # Mejor caso O(n)

    # 🔍 Insertion Sort: while interno puede no ejecutarse (mejor caso)
    elif _insertion_sort_inner_while(cond, body):
        total_b = const(1)  # Mejor caso: ya ordenado, no entra

    # 🔍 Búsqueda con bandera 'found'
    elif _is_found_flag_while(cond, body):
        total_b = const(1)

    # 🔍 Búsqueda con early exit implícito (threshold, etc.)
    elif _while_has_early_exit_condition(cond, body):
        total_b = const(1)

    # 🔍 Búsqueda con centinela puro: while (A[idx] != x) idx++
    elif _is_sentinel_search_while(cond, body):
        total_b = const(1)

    # 🔍 Búsqueda lineal con salida por salto de índice (i <- n + 1)
    elif _while_has_index_jump_exit(cond, body):
        total_b = const(1)

    while_line = LineCostInternal(
        line=line, kind="while", text=None, multiplier=multiplier,
        cost_worst=const(0), cost_best=const(0), cost_avg=const(0),
    )

    return total_w, total_b, total_a, [while_line] + body_lines


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


def _detect_binary_search_while(cond: dict, body: List[dict], env: dict) -> Optional[Expr]:
    """
    Detecta búsqueda binaria iterativa:

    Patrón típico:
        l <- 1
        r <- n
        while (l <= r) do
        begin
            m <- (l + r) div 2
            if (A[m] = x) then
                l <- r + 1  (o terminar)
            else
                if (A[m] < x) then
                    l <- m + 1
                else
                    r <- m - 1
        end

    Returns:
        log n si detecta el patrón, None en caso contrario
    """
    if not (isinstance(cond, dict) and cond.get("kind") == "binop"):
        return None

    # Normalizar operador Unicode
    op = cond.get("op", "")
    if op == "≤":
        op = "<="
    elif op == "≥":
        op = ">="

    left = cond.get("left")
    right = cond.get("right")

    # Verificar que sea comparación entre dos variables (l <= r o r >= l)
    if not (_is_var(left) and _is_var(right)):
        return None

    if op not in ("<", "<=", ">", ">="):
        return None

    l_name = left["name"]
    r_name = right["name"]

    # 1) Buscar cálculo del punto medio: m <- (l + r) div 2
    mid_name = None
    for st in body:
        if st.get("kind") != "assign":
            continue

        tgt = st.get("target")
        expr = st.get("expr")

        if not _is_var(tgt):
            continue

        # Debe ser división (div o /)
        if not (isinstance(expr, dict) and
                expr.get("kind") == "binop" and
                expr.get("op") in ("div", "/")):
            continue

        left2 = expr.get("left")
        right2 = expr.get("right")

        # Verificar que sea (l + r) / 2
        if not (isinstance(left2, dict) and
                left2.get("kind") == "binop" and
                left2.get("op") == "+"):
            continue

        a = left2.get("left")
        b = left2.get("right")

        # Puede ser l + r o r + l
        vars_match = (
                (_is_var(a, l_name) and _is_var(b, r_name)) or
                (_is_var(a, r_name) and _is_var(b, l_name))
        )

        if not vars_match:
            continue

        # Debe dividir por 2
        if not _is_num(right2, 2):
            continue

        mid_name = tgt["name"]
        break

    if not mid_name:
        return None

    # 2) Verificar que se actualiza l o r basándose en m
    updates_found = 0

    def _check_updates_recursive(stmts: List[dict]) -> int:
        """Busca actualizaciones de l/r en cualquier nivel de anidación."""
        count = 0
        for st in stmts:
            if not isinstance(st, dict):
                continue

            kind = st.get("kind")

            # Verificar asignaciones directas
            if kind == "assign":
                tgt = st.get("target")
                expr = st.get("expr")

                if not _is_var(tgt):
                    continue

                tname = tgt["name"]

                # Caso 1: l <- m o r <- m
                if _is_var(expr, mid_name) and tname in (l_name, r_name):
                    count += 1
                    continue

                # Caso 2: l <- m + c o r <- m - c
                if isinstance(expr, dict) and expr.get("kind") == "binop":
                    op = expr.get("op")
                    if op in ("+", "-"):
                        eleft = expr.get("left")
                        eright = expr.get("right")
                        if (_is_var(eleft, mid_name) and
                                _is_num(eright) and
                                tname in (l_name, r_name)):
                            count += 1
                            continue

                # Caso 3: l <- r + 1 (para salir del loop)
                if isinstance(expr, dict) and expr.get("kind") == "binop":
                    if expr.get("op") == "+":
                        eleft = expr.get("left")
                        eright = expr.get("right")
                        if (_is_var(eleft, r_name) and
                                _is_num(eright, 1) and
                                tname == l_name):
                            count += 1
                            continue

            # Buscar recursivamente en estructuras anidadas
            elif kind == "if":
                count += _check_updates_recursive(st.get("then_body", []))
                if st.get("else_body"):
                    count += _check_updates_recursive(st["else_body"])

            elif kind in ("for", "while"):
                count += _check_updates_recursive(st.get("body", []))

            elif kind == "block":
                count += _check_updates_recursive(st.get("stmts", []))

        return count

    updates_found = _check_updates_recursive(body)

    if updates_found < 2:  # Necesitamos al menos 2 actualizaciones (para l y r)
        return None

    # 3) Estimar iteraciones: log(límite superior inicial)
    hi_init = env.get(r_name)

    if hi_init and hi_init[0] == "sym":
        arg = sym(hi_init[1])
    else:
        arg = sym("n")

    return _make_log(arg, 2)


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
