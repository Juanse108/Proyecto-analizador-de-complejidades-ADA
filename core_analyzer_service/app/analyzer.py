# app/analyzer.py
# --------------------------------------------------------------
# Analizador de complejidades (MVP) para AST iterativo:
# - assign, if, for, while
# - for: estima iteraciones y multiplica por coste del cuerpo
# - while: detecta patrones lineales (±k) y logarítmicos (/k, *k)
# --------------------------------------------------------------

from typing import Any, List, Tuple, Optional

from .complexity_ir import (
    Expr, Log, const, sym, mul,
    big_o_str_from_expr, big_omega_str_from_expr
)
from .cost_model import cost_assign, cost_compare, cost_seq


# -------------------- utilidades AST --------------------

def _is_var(node: Any, name: str | None = None) -> bool:
    return isinstance(node, dict) and node.get("kind") == "var" and (name is None or node.get("name") == name)


def _is_num(node: Any, value: Any | None = None) -> bool:
    return isinstance(node, dict) and node.get("kind") == "num" and (value is None or node.get("value") == value)


def _is_binop(node: Any, op: str) -> bool:
    """
    Helper flexible para comparar operadores binarios.
    Soporta equivalentes Unicode como ≤ / ≥ / ≠.
    """
    if not (isinstance(node, dict) and node.get("kind") == "binop"):
        return False

    node_op = node.get("op")

    # Normalizamos algunos operadores Unicode que suele sacar el parser/LLM
    if node_op == "≤":
        node_op = "<="
    elif node_op == "≥":
        node_op = ">="
    elif node_op == "≠":
        node_op = "!="

    # También normalizamos el op esperado por si algún día le pasamos Unicode
    if op == "≤":
        op = "<="
    elif op == "≥":
        op = ">="
    elif op == "≠":
        op = "!="

    return node_op == op


# -------------------- utilidades IR --------------------

def _make_log(arg: Expr, base_k: int = 2) -> Expr:
    """
    Construye un nodo log(arg, base). Si la firma de Log difiere, cae
    a un símbolo 'log n' para no romper.
    """
    try:
        # Si tienes helper 'log' en complexity_ir, úsalo:
        from .complexity_ir import log  # type: ignore
        return log(arg, const(base_k))
    except Exception:
        try:
            # Muchas implementaciones modelan Log(arg, base)
            return Log(arg, const(base_k))  # type: ignore
        except Exception:
            # Fallback simbólico (degradación amable)
            return mul(sym("log"), arg)  # aparecerá como "log n"


def _cond_var_lt_sym_or_const(cond: dict, varname: str) -> Tuple[str, Any] | None:
    # Devuelve ("num", c) si var < c numérico, o ("sym", name) si var < name
    if _is_binop(cond, "<") or _is_binop(cond, "<="):
        L, R = cond.get("left"), cond.get("right")
        if _is_var(L, varname):
            if _is_num(R):
                return "num", R["value"]
            if _is_var(R):
                return "sym", R["name"]
    return None


# -------------------- entorno (valores iniciales) --------------------

# Guardamos asignaciones "simples" vistas: var <- <sym|num>
# env[var] = ("sym", nombre)  |  ("num", valor)
def _env_record_assign(env: dict, st: dict) -> None:
    if st.get("kind") != "assign":
        return
    tgt = st.get("target")
    expr = st.get("expr")
    if not _is_var(tgt):
        return
    vname = tgt["name"]
    if _is_var(expr):  # var <- m  (símbolo)
        env[vname] = ("sym", expr["name"])
    elif _is_num(expr):  # var <- 42 (constante)
        env[vname] = ("num", expr["value"])
    else:
        # expresión no soportada para inferir tope
        env.pop(vname, None)


# -------------------- análisis de listas --------------------

def analyze_stmt_list(stmts: List[dict], env: dict | None = None) -> Tuple[Expr, Expr]:
    """
    Devuelve (worst, best) para una lista secuencial.
    'env' propaga asignaciones simples para que while reconozca inicializaciones.
    """
    if env is None:
        env = {}

    worst_costs: List[Expr] = []
    best_costs: List[Expr] = []

    for s in stmts:
        w_cost, b_cost = analyze_stmt(s, env)  # <-- pasa env
        worst_costs.append(w_cost)
        best_costs.append(b_cost)

        # Si es una asignación simple, actualiza el entorno (para el siguiente stmt)
        if s.get("kind") == "assign":
            _env_record_assign(env, s)

    total_worst = cost_seq(*worst_costs) if worst_costs else const(0)
    total_best = cost_seq(*best_costs) if best_costs else const(0)
    return total_worst, total_best


# -------------------- análisis de FOR --------------------

def analyze_for(node: dict) -> Tuple[Expr, Expr]:
    start = node.get("start")
    end = node.get("end")
    step = node.get("step")

    if _is_num(start, 1) and _is_var(end) and (step is None):
        iters = sym(end["name"])
    elif _is_num(start, 1) and _is_num(end):
        iters = const(max(0, end["value"]))
    elif _is_var(end):
        iters = sym(end["name"])
    else:
        iters = const(1)

    body = node.get("body") or []
    # Env local para el cuerpo: así capturamos `j <- m` antes del while interno
    body_env: dict = {}
    body_worst, body_best = analyze_stmt_list(body, env=body_env)

    total = mul(iters, body_worst)
    return total, total  # Θ: for determinista


# -------------------- patrones para WHILE --------------------

def _assign_div_const(body: List[dict], varname: str) -> int | None:
    """Busca: var <- var / k  (k>1). Devuelve k si lo encuentra."""
    for st in body:
        if st.get("kind") != "assign":
            continue
        tgt = st.get("target")
        expr = st.get("expr")
        if not _is_var(tgt, varname):
            continue
        if _is_binop(expr, "/") and _is_var(expr.get("left"), varname) and _is_num(expr.get("right")):
            k = expr["right"]["value"]
            try:
                k = int(k)
            except Exception:
                return None
            if k > 1:
                return k
    return None


def _assign_mul_const(body: List[dict], varname: str) -> int | None:
    """Busca: var <- var * k (k>1)."""
    for st in body:
        if st.get("kind") != "assign":
            continue
        tgt = st.get("target")
        expr = st.get("expr")
        if not _is_var(tgt, varname):
            continue
        if _is_binop(expr, "*") and _is_var(expr.get("left"), varname) and _is_num(expr.get("right")):
            k = expr["right"]["value"]
            try:
                k = int(k)
            except Exception:
                return None
            if k > 1:
                return k
    return None


def _assign_add_const(body: List[dict], varname: str) -> int | None:
    """Busca: var <- var + k (k>0)."""
    for st in body:
        if st.get("kind") != "assign":
            continue
        tgt = st.get("target")
        expr = st.get("expr")
        if not _is_var(tgt, varname):
            continue
        if _is_binop(expr, "+") and _is_var(expr.get("left"), varname) and _is_num(expr.get("right")):
            k = expr["right"]["value"]
            try:
                k = int(k)
            except Exception:
                return None
            if k > 0:
                return k
    return None


def _assign_sub_const(body: List[dict], varname: str) -> int | None:
    """Busca: var <- var - k (k>0)."""
    for st in body:
        if st.get("kind") != "assign":
            continue
        tgt = st.get("target")
        expr = st.get("expr")
        if not _is_var(tgt, varname):
            continue
        if _is_binop(expr, "-") and _is_var(expr.get("left"), varname) and _is_num(expr.get("right")):
            k = expr["right"]["value"]
            try:
                k = int(k)
            except Exception:
                return None
            if k > 0:
                return k
    return None


def _cond_var_gt_const(cond: dict, varname: str) -> bool:
    """Detecta (var > c) o (var >= c) con c numérico."""
    if _is_binop(cond, ">") or _is_binop(cond, ">="):
        l, r = cond.get("left"), cond.get("right")
        return _is_var(l, varname) and _is_num(r)
    return False


def _cond_var_lt_const(cond: dict, varname: str) -> bool:
    """Detecta (var < c) o (var <= c) con c numérico."""
    if _is_binop(cond, "<") or _is_binop(cond, "<="):
        l, r = cond.get("left"), cond.get("right")
        return _is_var(l, varname) and _is_num(r)
    return False

def _normalize_op(op: str) -> str:
    """Normaliza algunos operadores Unicode a ASCII."""
    if op == "≤":
        return "<="
    if op == "≥":
        return ">="
    if op == "≠":
        return "!="
    return op


def _detect_binary_search_while(cond: dict, body: List[dict], env: dict) -> Optional[Expr]:
    """
    Intenta detectar un while típico de búsqueda binaria:

        l <- 1
        r <- n
        while (l <= r) do
            m <- (l + r) div 2
            ... (ifs)
            l <- m + 1   o   r <- m - 1   o   r <- m

    Devuelve una expresión con el número de iteraciones (~ log n),
    o None si no reconoce el patrón.
    """
    if not (isinstance(cond, dict) and cond.get("kind") == "binop"):
        return None

    op = _normalize_op(cond.get("op", ""))
    left = cond.get("left")
    right = cond.get("right")

    # Condición tipo l <= r o r >= l (dos variables)
    if not (_is_var(left) and _is_var(right)):
        return None

    l_name = left["name"]
    r_name = right["name"]

    if op not in ("<", "<=", ">", ">="):
        return None

    # 1) Buscar m <- (l + r) div 2
    mid_name = None
    for st in body:
        if st.get("kind") != "assign":
            continue
        tgt = st.get("target")
        expr = st.get("expr")
        if not _is_var(tgt):
            continue

        # expr debe ser binop "div" o "/"
        if not (isinstance(expr, dict) and expr.get("kind") == "binop" and expr.get("op") in ("div", "/")):
            continue

        left2 = expr.get("left")
        right2 = expr.get("right")

        # (l + r) div 2  o  (r + l) div 2
        if not (isinstance(left2, dict) and left2.get("kind") == "binop" and left2.get("op") == "+"):
            continue

        a = left2.get("left")
        b = left2.get("right")
        if not ((_is_var(a, l_name) and _is_var(b, r_name)) or (_is_var(a, r_name) and _is_var(b, l_name))):
            continue

        if not _is_num(right2, 2):
            continue

        mid_name = tgt["name"]
        break

    if not mid_name:
        return None

    # 2) Ver que se actualiza l o r en función de m
    updated_low_or_high = False
    for st in body:
        if st.get("kind") != "assign":
            continue
        tgt = st.get("target")
        expr = st.get("expr")
        if not _is_var(tgt):
            continue

        tname = tgt["name"]

        # l <- m  o  r <- m
        if _is_var(expr, mid_name) and tname in (l_name, r_name):
            updated_low_or_high = True
            continue

        # l <- m +/- c  o  r <- m +/- c
        if isinstance(expr, dict) and expr.get("kind") == "binop" and expr.get("op") in ("+", "-"):
            if _is_var(expr.get("left"), mid_name) and _is_num(expr.get("right")) and tname in (l_name, r_name):
                updated_low_or_high = True
                continue

    if not updated_low_or_high:
        return None

    # 3) Estimar iteraciones: log_2(longitud intervalo inicial)
    # Usamos r inicial; si no sabemos, caemos a log n.
    hi_init = env.get(r_name)
    if hi_init and hi_init[0] == "sym":
        # p.ej., r <- n
        arg = sym(hi_init[1])
    else:
        arg = sym("n")

    iters = _make_log(arg, 2)
    return iters


def analyze_while(node: dict, env: dict | None = None) -> Tuple[Expr, Expr]:
    if env is None:
        env = {}

    cond = node.get("cond", {})
    body = node.get("body") or []
    # Env anidado para el cuerpo (no contaminar el exterior)
    body_env = dict(env)
    body_worst, body_best = analyze_stmt_list(body, env=body_env)

    # 1) Búsqueda binaria
    bs_iters = _detect_binary_search_while(cond, body, env)
    if bs_iters is not None:
        total = mul(bs_iters, body_worst)
        return total, total
    # 2) Resto de patrones (halving, doubling, lineal, fallback Θ(n))
    ctrl_var = None
    if isinstance(cond, dict) and cond.get("kind") == "binop":
        if _is_var(cond.get("left")):
            ctrl_var = cond.get("left").get("name")
        elif _is_var(cond.get("right")):
            ctrl_var = cond.get("right").get("name")

    # Helper: lee init de env para ctrl_var (("sym","m") o ("num",C))
    def _init_of(vname: str):
        return env.get(vname)

    if ctrl_var:
        # ---- Halving: i > c  &  i <- i / k (k>1)  => log(init)
        if _cond_var_gt_const(cond, ctrl_var):
            k = _assign_div_const(body, ctrl_var)
            if k:
                init = _init_of(ctrl_var)
                if init and init[0] == "sym":
                    arg = sym(init[1])  # p.ej., m  -> log m
                    iters = _make_log(arg, k)
                    total = mul(iters, body_worst)
                    return total, total
                if init and init[0] == "num":
                    # init constante => log(const) = O(1)
                    return body_worst, body_worst
                # sin info: asumimos n
                iters = _make_log(sym("n"), k)
                total = mul(iters, body_worst)
                return total, total

        # ---- Doubling: i < TH  &  i <- i * k (k>1)
        th = _cond_var_lt_sym_or_const(cond, ctrl_var)
        if th:
            k = _assign_mul_const(body, ctrl_var)
            if k:
                if th[0] == "sym":
                    arg = sym(th[1])  # p.ej., m
                    iters = _make_log(arg, k)
                    total = mul(iters, body_worst)
                    return total, total
                else:
                    # TH constante => O(1)
                    return body_worst, body_worst

        # ---- Lineal decremento: i > c  &  i <- i - k
        if _cond_var_gt_const(cond, ctrl_var) and _assign_sub_const(body, ctrl_var):
            total = mul(sym("n"), body_worst)
            return total, total

        # ---- Lineal incremento: i < c  &  i <- i + k
        if _cond_var_lt_const(cond, ctrl_var) and _assign_add_const(body, ctrl_var):
            total = mul(sym("n"), body_worst)
            return total, total

    # desconocido → conservador Θ(n)
    total = mul(sym("n"), body_worst)
    return total, total


# -------------------- análisis de IF --------------------

def analyze_if(node: dict, env: dict | None = None) -> Tuple[Expr, Expr]:
    if env is None:
        env = {}
    then_worst, then_best = analyze_stmt_list(node.get("then_body") or [], env=dict(env))
    else_worst, else_best = analyze_stmt_list(node.get("else_body") or [], env=dict(env))

    total_worst = cost_seq(cost_compare(), then_worst, else_worst)
    total_best  = cost_seq(cost_compare(), then_best,  else_best)
    return total_worst, total_best


def analyze_stmt(node: dict, env: dict | None = None) -> Tuple[Expr, Expr]:
    if env is None:
        env = {}

    kind = node.get("kind")

    if kind == "assign":
        c = cost_assign()
        # registra en env la asignación simple (para el stmt siguiente)
        _env_record_assign(env, node)
        return c, c

    if kind == "for":
        return analyze_for(node)

    if kind == "while":
        return analyze_while(node, env=env)

    if kind == "if":
        return analyze_if(node, env=env)

    c = const(1)
    return c, c

def _extract_main_body(ast: dict) -> List[dict]:
    """
    Adapta el AST que viene del microservicio de parseo a la forma
    que espera el analizador iterativo (lista de sentencias).

    Casos soportados:
    - program -> [proc] -> body
    - program -> body con sentencias sueltas
    - proc -> body
    """
    if not isinstance(ast, dict):
        return []

    kind = ast.get("kind")

    # Caso típico: raíz "program"
    if kind == "program":
        body = ast.get("body") or []

        # Caso más común: un solo procedimiento con el algoritmo
        if len(body) == 1 and isinstance(body[0], dict) and body[0].get("kind") == "proc":
            return body[0].get("body") or []

        # Si hay varios procs, por ahora analizamos solo el primero
        if body and isinstance(body[0], dict) and body[0].get("kind") == "proc":
            return body[0].get("body") or []

        # Si el body ya son sentencias sueltas
        return body

    # Si nos pasan directamente un "proc"
    if kind == "proc":
        return ast.get("body") or []

    # Fallback: intenta usar .body si existe
    body = ast.get("body")
    if isinstance(body, list):
        return body

    return []


# -------------------- API pública --------------------

def analyze_program(ast: dict) -> dict:
    # Adaptamos el AST (program/proc) a una lista de sentencias planas
    stmts = _extract_main_body(ast)

    # Reutilizamos toda la lógica que ya tienes para listas de stmts
    total_worst, total_best = analyze_stmt_list(stmts, env={})

    big_o = big_o_str_from_expr(total_worst)
    big_omega = big_omega_str_from_expr(total_best)
    theta = big_o if big_o == big_omega else None

    return {
        "ir_worst": total_worst,
        "ir_best": total_best,
        "big_o": big_o,
        "big_omega": big_omega,
        "theta": theta,
    }