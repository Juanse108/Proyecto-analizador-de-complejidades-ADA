# core_analyzer_service/app/analyzer.py
from typing import Any, List
from .complexity_ir import (
    Expr, Const, Sym, Pow, Log, Add, Mul,
    const, sym, add, mul, big_o_str
)
from .cost_model import cost_assign, cost_compare, cost_seq

# -------- utilidades para leer expresiones del AST del parser --------

def _is_var(node: Any, name: str) -> bool:
    return isinstance(node, dict) and node.get("type") == "var" and node.get("name") == name

def _is_num(node: Any, val: int | None = None) -> bool:
    if isinstance(node, dict) and node.get("type") == "num":
        return True if val is None else node.get("value") == val
    return False

def _expr_to_ir(node: Any) -> Expr:
    # Solo lo usamos para contar 'n' cuando aparezca en límites / expresiones.
    if _is_var(node, "n"):
        return sym("n")
    if _is_num(node):
        return const(node["value"])
    if isinstance(node, dict) and node.get("type") == "bin":
        op = node["op"]
        L = _expr_to_ir(node["left"])
        R = _expr_to_ir(node["right"])
        if op == "+":
            return add(L, R)
        if op == "*":
            return mul(L, R)
        # para otros, devolvemos algo conservador
        return add(L, R)
    # por defecto no reconocido → tratamos como O(1)
    return const(1)

# -------- análisis de sentencias --------

def analyze_stmt_list(stmts: List[dict]) -> Expr:
    costs: List[Expr] = []
    for s in stmts:
        costs.append(analyze_stmt(s))
    return cost_seq(*costs) if costs else const(0)

def analyze_for(node: dict) -> Expr:
    # Asumimos patrón canónico: for i <- 1 to n do body
    start = node.get("start")
    end = node.get("end")
    step = node.get("step")  # puede ser None

    # Conteo de iteraciones (MVP):
    #  - si es 1..n con step 1 → n
    #  - si es 1..const m → m
    #  - si es const a .. const b → (b-a+1) (pero lo limitamos a O(1))
    iters: Expr
    if _is_num(start, 1) and isinstance(end, dict) and end.get("type") == "var" and end.get("name") == "n" and (step is None):
        iters = sym("n")
    elif _is_num(start, 1) and _is_num(end):
        iters = const(max(0, end["value"]))
    else:
        # Desconocido → depende de end; si es var n, usa n; en otro caso, 1
        iters = sym("n") if _is_var(end, "n") else const(1)

    body = node.get("body") or []
    body_cost = analyze_stmt_list(body)
    # Coste total ~ iters * body_cost (ignoramos +O(1) del control del loop, MVP)
    return mul(iters, body_cost if not isinstance(body_cost, Const) else add(body_cost))

def analyze_while(node: dict) -> Expr:
    # MVP: detecta patrón i <- n ; while i > 1 do i <- i / 2 ; body...
    cond = node.get("cond", {})
    body = node.get("body") or []

    # detecta "i > 1"
    is_i_gt_1 = (
        isinstance(cond, dict) and
        cond.get("op") == ">" and
        _is_var(cond.get("left"), "i") and
        _is_num(cond.get("right"), 1)
    )

    # detecta dentro del body "i <- i / 2"
    divides_by_2 = False
    body_cost_terms: List[Expr] = []
    for st in body:
        if st.get("kind") == "assign" and st.get("target") == "i":
            expr = st.get("expr")
            if isinstance(expr, dict) and expr.get("type") == "bin" and expr.get("op") == "/":
                if _is_var(expr.get("left"), "i") and _is_num(expr.get("right"), 2):
                    divides_by_2 = True
                    # cost de esa asignación cuenta como 1
                    body_cost_terms.append(cost_assign())
                    continue
        body_cost_terms.append(analyze_stmt(st))
    body_cost = cost_seq(*body_cost_terms) if body_cost_terms else const(0)

    if is_i_gt_1 and divides_by_2:
        # O(log n) * coste_body
        return mul(Log(sym("n")), body_cost if not isinstance(body_cost, Const) else add(body_cost))
    # Desconocido → conservador: coste del cuerpo (una iter) (MVP)
    return body_cost if not isinstance(body_cost, Const) else add(body_cost)

def analyze_if(node: dict) -> Expr:
    then_cost = analyze_stmt_list(node.get("then_body") or [])
    else_body = node.get("else_body")
    else_cost = analyze_stmt_list(else_body or [])
    # Tomamos el peor (worst-case); coste de comparar es O(1)
    # Para el Big-O usaremos el mayor por grado → basta con add
    return add(cost_compare(), then_cost, else_cost)

def analyze_stmt(node: dict) -> Expr:
    kind = node.get("kind")
    if kind == "assign":
        return cost_assign()
    if kind == "for":
        return analyze_for(node)
    if kind == "while":
        return analyze_while(node)
    if kind == "if":
        return analyze_if(node)
    # desconocido → O(1)
    return const(1)

# -------- API pública del analizador --------

def analyze_program(ast: dict) -> dict:
    """
    ast: {"kind":"program","body":[...]}
    """
    body = ast.get("body") or []
    total = analyze_stmt_list(body)
    return {
        "ir": total,
        "big_o": big_o_str(total),
    }
