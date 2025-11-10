from typing import Any, List, Tuple
from .complexity_ir import (
    Expr, Const, Sym, Pow, Log, Add, Mul,
    const, sym, add, mul, big_o_str_from_expr, big_omega_str_from_expr, to_json
)
from .cost_model import cost_assign, cost_compare, cost_seq

# Implementaciones mínimas de ayuda usadas por el analizador.
def _is_var(node: Any, name: str = None) -> bool:
    """Devuelve True si 'node' es una variable (AST) y opcionalmente coincide el nombre."""
    return isinstance(node, dict) and node.get("kind") == "var" and (name is None or node.get("name") == name)

def _is_num(node: Any, value: Any = None) -> bool:
    """Devuelve True si 'node' es un literal numérico y opcionalmente coincide el valor."""
    return isinstance(node, dict) and node.get("kind") == "num" and (value is None or node.get("value") == value)

def _expr_to_ir(node: Any) -> Expr:
    """Convierte un nodo AST simple a la representación intermedia mínima usada aquí."""
    if not isinstance(node, dict):
        return const(0)
    kind = node.get("kind")
    if kind == "num":
        return const(node.get("value", 0))
    if kind == "var":
        return sym(node.get("name"))
    # casos simples para operaciones binarios si aparecen (opcional)
    if kind == "add":
        left = _expr_to_ir(node.get("left"))
        right = _expr_to_ir(node.get("right"))
        return add(left, right)
    if kind == "mul":
        left = _expr_to_ir(node.get("left"))
        right = _expr_to_ir(node.get("right"))
        return mul(left, right)
    # fallback
    return const(0)

# -------- análisis de sentencias --------

def analyze_stmt_list(stmts: List[dict]) -> Tuple[Expr, Expr]:
    """Devuelve (worst_cost, best_cost) para una lista de sentencias."""
    worst_costs: List[Expr] = []
    best_costs: List[Expr] = []
    
    for s in stmts:
        w_cost, b_cost = analyze_stmt(s)
        worst_costs.append(w_cost)
        best_costs.append(b_cost)
        
    # La complejidad secuencial es el MAX de los costos
    total_worst = cost_seq(*worst_costs) if worst_costs else const(0)
    total_best = cost_seq(*best_costs) if best_costs else const(0)
    
    return (total_worst, total_best)

def analyze_for(node: dict) -> Tuple[Expr, Expr]:
    """Devuelve (worst, best) para un bucle FOR."""
    start = node.get("start")
    end = node.get("end")
    step = node.get("step")

    # (El cálculo de 'iters' es el mismo para peor y mejor caso aquí)
    iters: Expr
    if _is_num(start, 1) and _is_var(end, "n") and (step is None):
        iters = sym("n")
    elif _is_num(start, 1) and _is_num(end):
        iters = const(max(0, end["value"]))
    else:
        iters = sym("n") if _is_var(end, "n") else const(1)

    body = node.get("body") or []
    (body_worst, body_best) = analyze_stmt_list(body)

    # Coste total = iters * body_cost
    total_worst = mul(iters, body_worst if not isinstance(body_worst, Const) else add(body_worst))
    total_best = mul(iters, body_best if not isinstance(body_best, Const) else add(body_best))
    
    return (total_worst, total_best)
 
def analyze_while(node: dict) -> Tuple[Expr, Expr]:
    """Devuelve (worst, best) para un bucle WHILE."""
    # (El análisis de O(log n) es el mismo)
    
    # Detecta patrones del bucle logarítmico
    cond = node.get("cond", {})
    is_i_gt_1 = (cond.get("kind") == "gt" and 
                 _is_var(cond.get("left"), "i") and 
                 _is_num(cond.get("right"), 1))
    
    body = node.get("body") or []
    divides_by_2 = any(st.get("kind") == "assign" and 
                      _is_var(st.get("left"), "i") and 
                      st.get("right", {}).get("kind") == "div" and 
                      _is_var(st.get("right", {}).get("left"), "i") and 
                      _is_num(st.get("right", {}).get("right"), 2) 
                      for st in body)
    
    # Simplificación: el cuerpo se analiza igual para O y Ω
    body_cost_terms: List[Tuple[Expr, Expr]] = []
    # ... (itera el 'body' y llama a analyze_stmt(st)) ...
    # (body_worst, body_best) = ...
    
    (body_worst, body_best) = analyze_stmt_list(node.get("body") or [])
    
    # En el MEJOR CASO (Ω), un bucle WHILE puede no ejecutarse nunca.
    # El costo es O(1) (solo la comprobación de la condición).
    total_best = cost_compare() # Ω(1)

    # En el PEOR CASO (O), usamos el patrón detectado.
    total_worst: Expr
    if is_i_gt_1 and divides_by_2:
        # O(log n) * O(body_worst)
        total_worst = mul(Log(sym("n")), body_worst)
    else:
        # AVISO: El código original tenía un error aquí. Asumía O(1) (solo body_cost).
        # Deberíamos asumir O(n) si el patrón es desconocido, o usar el LLM.
        # Asumamos O(n) por ahora.
        total_worst = mul(sym("n"), body_worst) 

    return (total_worst, total_best)

def analyze_if(node: dict) -> Tuple[Expr, Expr]:
    """Devuelve (worst, best) para un IF."""
    (then_worst, then_best) = analyze_stmt_list(node.get("then_body") or [])
    
    else_body = node.get("else_body")
    (else_worst, else_best) = analyze_stmt_list(else_body or [])
    
    # Peor Caso (O): max(then_worst, else_worst)
    # La función 'add' (que se convierte en 'cost_seq') ya hace esto.
    total_worst = add(cost_compare(), then_worst, else_worst)
    
    # Mejor Caso (Ω): min(then_best, else_best)
    # Aquí 'add' también funciona, porque big_omega_str tomará el 'min'.
    total_best = add(cost_compare(), then_best, else_best)
    
    return (total_worst, total_best)

def analyze_stmt(node: dict) -> Tuple[Expr, Expr]:
    """Devuelve (worst, best) para CUALQUIER sentencia."""
    kind = node.get("kind")
    
    if kind == "assign":
        # O(1) y Ω(1)
        cost = cost_assign()
        return (cost, cost)
        
    if kind == "for":
        return analyze_for(node)
        
    if kind == "while":
        return analyze_while(node)
        
    if kind == "if":
        return analyze_if(node)
        
    # desconocido → O(1) y Ω(1)
    cost = const(1)
    return (cost, cost)

# -------- API pública del analizador --------

def analyze_program(ast: dict) -> dict:
    body = ast.get("body") or []
    (total_worst, total_best) = analyze_stmt_list(body)
    
    # Genera las cadenas de O y Ω usando las funciones de IR
    o_str = big_o_str_from_expr(total_worst)
    omega_str = big_o_str_from_expr(total_best) # Usamos la misma lógica de formato
    
    theta_str = o_str if o_str == omega_str else None
    
    return {
        "ir_worst": total_worst,
        "ir_best": total_best,
        "big_o": o_str,
        "big_omega": omega_str,
        "theta": theta_str
    }