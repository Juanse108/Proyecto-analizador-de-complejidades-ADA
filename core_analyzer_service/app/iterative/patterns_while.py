from typing import List, Dict, Optional, Tuple, Any

from ..domain import Expr, sym, const, log
from ..domain.ast_utils import (
    is_var, is_num, is_binop, normalize_op,
    expr_uses_var, stmt_list_has_assign_to_var,
    collect_vars_in_expr, expr_has_logical_op
)


def assign_div_const(body: List[dict], varname: str) -> Optional[int]:
    for st in body:
        if st.get("kind") != "assign":
            continue
        tgt = st.get("target")
        expr = st.get("expr")
        if not is_var(tgt, varname):
            continue

        if (
            isinstance(expr, dict)
            and expr.get("kind") == "binop"
            and expr.get("op") in ("/", "div")
            and is_var(expr.get("left"), varname)
            and is_num(expr.get("right"))
        ):
            k = expr["right"]["value"]
            if isinstance(k, (int, float)) and k > 1:
                return int(k)
    return None


def assign_mul_const(body: List[dict], varname: str) -> Optional[int]:
    for st in body:
        if st.get("kind") != "assign":
            continue
        tgt = st.get("target")
        expr = st.get("expr")
        if not is_var(tgt, varname):
            continue
        if is_binop(expr, "*") and is_var(expr.get("left"), varname) and is_num(expr.get("right")):
            k = expr["right"]["value"]
            if isinstance(k, (int, float)) and k > 1:
                return int(k)
    return None


def assign_add_const(body: List[dict], varname: str) -> Optional[int]:
    for st in body:
        if st.get("kind") != "assign":
            continue
        tgt = st.get("target")
        expr = st.get("expr")
        if not is_var(tgt, varname):
            continue
        if is_binop(expr, "+") and is_var(expr.get("left"), varname) and is_num(expr.get("right")):
            k = expr["right"]["value"]
            if isinstance(k, (int, float)) and k > 0:
                return int(k)
    return None


def assign_sub_const(body: List[dict], varname: str) -> Optional[int]:
    for st in body:
        if st.get("kind") != "assign":
            continue
        tgt = st.get("target")
        expr = st.get("expr")
        if not is_var(tgt, varname):
            continue
        if is_binop(expr, "-") and is_var(expr.get("left"), varname) and is_num(expr.get("right")):
            k = expr["right"]["value"]
            if isinstance(k, (int, float)) and k > 0:
                return int(k)
    return None


def cond_var_lt_sym_or_const(cond: dict, varname: str) -> Optional[Tuple[str, Any]]:
    if is_binop(cond, "<") or is_binop(cond, "<="):
        left, right = cond.get("left"), cond.get("right")
        if is_var(left, varname):
            if is_num(right):
                return ("num", right["value"])
            if is_var(right):
                return ("sym", right["name"])
    return None


def cond_var_gt_const(cond: dict, varname: str) -> bool:
    if is_binop(cond, ">") or is_binop(cond, ">="):
        left, right = cond.get("left"), cond.get("right")
        return is_var(left, varname) and is_num(right)
    return False


def cond_var_lt_const(cond: dict, varname: str) -> bool:
    if is_binop(cond, "<") or is_binop(cond, "<="):
        left, right = cond.get("left"), cond.get("right")
        return is_var(left, varname) and is_num(right)
    return False


def is_found_flag_while(cond: dict, body: List[dict]) -> bool:
    """Detecta si el while tiene un flag de búsqueda.
    
    Casos:
    1. Condición usa "found": while (found) ...
    2. Body asigna "found = true": búsqueda con early exit
    """
    # Caso 1: Condición usa found directamente
    if expr_uses_var(cond, "found") and stmt_list_has_assign_to_var(body, "found"):
        return True
    
    # Caso 2: Búsqueda con early exit (encontrar e inmediatamente asignar found/break)
    # Buscar si el body contiene asignación a variables de bandera
    def has_early_exit_assignment(stmts: List[dict]) -> bool:
        """Busca 'found = true' o similar dentro de if statements"""
        for st in stmts:
            if st.get("kind") == "assign":
                tgt = st.get("target", {})
                expr = st.get("expr", {})
                tgt_name = tgt.get("name", "").lower() if isinstance(tgt, dict) else ""
                
                # Buscar asignaciones como: found <- true, found <- 1, etc.
                if tgt_name in ["found", "encontrado", "existe"]:
                    return True
            
            elif st.get("kind") == "if":
                if has_early_exit_assignment(st.get("then_body", [])):
                    return True
                if has_early_exit_assignment(st.get("else_body", [])):
                    return True
            
            elif st.get("kind") == "block":
                if has_early_exit_assignment(st.get("stmts", [])):
                    return True
        
        return False
    
    # Si hay asignación a "found" en el body, es una búsqueda con early exit
    if has_early_exit_assignment(body):
        return True
    
    return False


def find_linear_index_var(body: List[dict]) -> Optional[str]:
    def _visit(stmts: List[dict]) -> Optional[str]:
        for st in stmts:
            kind = st.get("kind")

            if kind == "assign":
                tgt = st.get("target")
                expr = st.get("expr")
                if not is_var(tgt):
                    continue
                if not isinstance(expr, dict):
                    continue
                varname = tgt.get("name")

                if is_binop(expr, "+") and is_var(expr.get("left"), varname) and is_num(expr.get("right")):
                    return varname

                if is_binop(expr, "-") and is_var(expr.get("left"), varname) and is_num(expr.get("right")):
                    return varname

            elif kind == "if":
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
                found = _visit(st.get("body", []))
                if found:
                    return found

        return None

    return _visit(body)


def body_has_nested_loops(body: List[dict]) -> bool:
    for st in body:
        kind = st.get("kind")
        if kind in ("for", "while", "repeat"):
            return True
        if kind == "if":
            if body_has_nested_loops(st.get("then_body", [])):
                return True
            if body_has_nested_loops(st.get("else_body", [])):
                return True
        elif kind == "block":
            if body_has_nested_loops(st.get("stmts", [])):
                return True
    return False


def is_search_like_while(cond: dict, body: List[dict]) -> bool:
    if not expr_has_logical_op(cond):
        return False

    if body_has_nested_loops(body):
        return False

    idx = find_linear_index_var(body)
    if not idx:
        return False

    vars_in_cond: set = set()
    collect_vars_in_expr(cond, vars_in_cond)

    if idx not in vars_in_cond:
        return False

    if len(vars_in_cond) <= 1:
        return False

    return True


def branch_has_index_jump_out(stmts: List[dict], idx: str, bound: str) -> bool:
    for st in stmts:
        if st.get("kind") != "assign":
            continue
        tgt = st.get("target")
        expr = st.get("expr")
        if not is_var(tgt, idx):
            continue
        if not (isinstance(expr, dict) and expr.get("kind") == "binop"):
            continue
        op = expr.get("op")
        if op not in ("+", "-"):
            continue
        left = expr.get("left")
        right = expr.get("right")
        if (is_var(left, bound) and is_num(right)) or (is_num(left) and is_var(right, bound)):
            return True
    return False


def branch_has_linear_step(stmts: List[dict], idx: str) -> bool:
    for st in stmts:
        if st.get("kind") != "assign":
            continue
        tgt = st.get("target")
        expr = st.get("expr")
        if not is_var(tgt, idx):
            continue
        if not (isinstance(expr, dict) and expr.get("kind") == "binop"):
            continue
        op = expr.get("op")
        if op not in ("+", "-"):
            continue
        left = expr.get("left")
        right = expr.get("right")
        if is_var(left, idx) and is_num(right):
            return True
    return False


def while_has_index_jump_exit(cond: dict, body: List[dict]) -> bool:
    if not (isinstance(cond, dict) and cond.get("kind") == "binop"):
        return False

    op = cond.get("op")
    if op == "≤":
        op = "<="
    if op not in ("<", "<="):
        return False

    left = cond.get("left")
    right = cond.get("right")
    if not (is_var(left) and is_var(right)):
        return False

    idx = left["name"]
    bound = right["name"]

    def _search(stmts: List[dict]) -> bool:
        for st in stmts:
            kind = st.get("kind")
            if kind == "if":
                then_body = st.get("then_body", [])
                else_body = st.get("else_body", [])

                if (branch_has_index_jump_out(then_body, idx, bound) and
                        branch_has_linear_step(else_body, idx)):
                    return True
                if (branch_has_index_jump_out(else_body, idx, bound) and
                        branch_has_linear_step(then_body, idx)):
                    return True

                if _search(then_body) or _search(else_body):
                    return True

            elif kind in ("while", "for", "repeat", "block"):
                inner = st.get("body") or st.get("stmts") or []
                if _search(inner):
                    return True

        return False

    return _search(body)


def insertion_sort_inner_while(cond: dict, body: List[dict]) -> bool:
    if body_has_nested_loops(body):
        return False

    idx_var = find_linear_index_var(body)
    if not idx_var:
        return False

    vars_in_cond: set = set()
    collect_vars_in_expr(cond, vars_in_cond)

    if idx_var not in vars_in_cond or len(vars_in_cond) <= 1:
        return False

    if not assign_sub_const(body, idx_var):
        return False

    return True


def is_adaptive_sort_while(cond: dict, body: List[dict]) -> bool:
    if not body_has_nested_loops(body):
        return False

    flag_vars = {"swapped", "changed", "sorted", "done", "modified", "intercambiado"}

    vars_in_cond: set = set()
    collect_vars_in_expr(cond, vars_in_cond)

    for flag in flag_vars:
        if flag in vars_in_cond:
            if stmt_list_has_assign_to_var(body, flag):
                return True

    return False


def is_sentinel_search_while(cond: dict, body: List[dict]) -> bool:
    if body_has_nested_loops(body):
        return False

    idx = find_linear_index_var(body)
    if not idx:
        return False

    if not (isinstance(cond, dict) and cond.get("kind") == "binop"):
        return False

    if cond.get("op") not in ("!=", "<>"):
        return False

    left = cond.get("left")
    right = cond.get("right")

    vars_left: set = set()
    vars_right: set = set()
    collect_vars_in_expr(left, vars_left)
    collect_vars_in_expr(right, vars_right)

    if idx not in vars_left and idx not in vars_right:
        return False

    all_vars = vars_left | vars_right
    if len(all_vars) <= 1:
        return False

    return True


def while_has_early_exit_condition(cond: dict, body: List[dict]) -> bool:
    if is_found_flag_while(cond, body):
        return False

    return is_search_like_while(cond, body)


def detect_binary_search_while(cond: dict, body: List[dict], env: Dict[str, Tuple[str, Any]]) -> Optional[Expr]:
    if not (isinstance(cond, dict) and cond.get("kind") == "binop"):
        return None

    op = normalize_op(cond.get("op", ""))
    left = cond.get("left")
    right = cond.get("right")

    if not (is_var(left) and is_var(right)):
        return None

    l_name = left["name"]
    r_name = right["name"]

    if op not in ("<", "<=", ">", ">="):
        return None

    mid_name = None
    for st in body:
        if st.get("kind") != "assign":
            continue

        tgt = st.get("target")
        expr = st.get("expr")

        if not is_var(tgt):
            continue

        if not (isinstance(expr, dict) and
                expr.get("kind") == "binop" and
                expr.get("op") in ("div", "/")):
            continue

        left2 = expr.get("left")
        right2 = expr.get("right")

        if not (isinstance(left2, dict) and
                left2.get("kind") == "binop" and
                left2.get("op") == "+"):
            continue

        a = left2.get("left")
        b = left2.get("right")

        vars_match = (
            (is_var(a, l_name) and is_var(b, r_name)) or
            (is_var(a, r_name) and is_var(b, l_name))
        )

        if not vars_match:
            continue

        if not is_num(right2, 2):
            continue

        mid_name = tgt["name"]
        break

    if not mid_name:
        return None

    updates_found = 0

    def _check_updates_recursive(stmts: List[dict]) -> int:
        count = 0
        for st in stmts:
            if not isinstance(st, dict):
                continue

            kind = st.get("kind")

            if kind == "assign":
                tgt = st.get("target")
                expr = st.get("expr")

                if not is_var(tgt):
                    continue

                tname = tgt["name"]

                if is_var(expr, mid_name) and tname in (l_name, r_name):
                    count += 1
                    continue

                if isinstance(expr, dict) and expr.get("kind") == "binop":
                    op = expr.get("op")
                    if op in ("+", "-"):
                        eleft = expr.get("left")
                        eright = expr.get("right")
                        if (is_var(eleft, mid_name) and
                                is_num(eright) and
                                tname in (l_name, r_name)):
                            count += 1
                            continue

                if isinstance(expr, dict) and expr.get("kind") == "binop":
                    if expr.get("op") == "+":
                        eleft = expr.get("left")
                        eright = expr.get("right")
                        if (is_var(eleft, r_name) and
                                is_num(eright, 1) and
                                tname == l_name):
                            count += 1
                            continue

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

    if updates_found < 2:
        return None

    hi_init = env.get(r_name)

    if hi_init and hi_init[0] == "sym":
        arg = sym(hi_init[1])
    else:
        arg = sym("n")

    return log(arg, const(2))