from typing import List, Dict, Any, Tuple, Optional, Set

from ..domain import Expr, sym, const, Pow, Sym
from ..domain.recurrence import RecurrenceRelation


def count_calls_in_expr(expr: Dict[str, Any], func_name: str) -> int:
    if not isinstance(expr, dict):
        return 0

    kind = expr.get("kind")

    if kind == "funcall":
        count = 1 if expr.get("name") == func_name else 0
        for arg in expr.get("args", []):
            count += count_calls_in_expr(arg, func_name)
        return count

    if kind == "binop":
        return (
            count_calls_in_expr(expr.get("left"), func_name) +
            count_calls_in_expr(expr.get("right"), func_name)
        )

    if kind == "unop":
        return count_calls_in_expr(expr.get("expr"), func_name)

    if kind == "index":
        return (
            count_calls_in_expr(expr.get("base"), func_name) +
            count_calls_in_expr(expr.get("index"), func_name)
        )

    return 0


def count_calls_in_stmts(stmts: List[Dict[str, Any]], func_name: str) -> int:
    total = 0

    for stmt in stmts or []:
        if not isinstance(stmt, dict):
            continue

        kind = stmt.get("kind")

        if kind == "call":
            if stmt.get("name") == func_name:
                total += 1

        elif kind == "assign":
            total += count_calls_in_expr(stmt.get("expr"), func_name)

        elif kind == "if":
            then_c = count_calls_in_stmts(stmt.get("then_body", []), func_name)
            else_body = stmt.get("else_body")
            else_c = count_calls_in_stmts(else_body, func_name) if else_body else 0
            total += max(then_c, else_c)

        elif kind in ("while", "repeat", "for"):
            total += count_calls_in_stmts(stmt.get("body", []), func_name)

        elif kind == "block":
            total += count_calls_in_stmts(stmt.get("stmts", []), func_name)

    return total


def collect_divisors_expr(expr: Dict[str, Any], divisors: Set[int]) -> None:
    if not isinstance(expr, dict):
        return

    kind = expr.get("kind")

    if kind == "binop":
        op = expr.get("op")
        if op in ("/", "div"):
            right = expr.get("right")
            if isinstance(right, dict) and right.get("kind") == "num":
                try:
                    val = int(right.get("value"))
                    if val > 1:
                        divisors.add(val)
                except Exception:
                    pass

        collect_divisors_expr(expr.get("left"), divisors)
        collect_divisors_expr(expr.get("right"), divisors)

    elif kind == "unop":
        collect_divisors_expr(expr.get("expr"), divisors)

    elif kind == "index":
        collect_divisors_expr(expr.get("base"), divisors)
        collect_divisors_expr(expr.get("index"), divisors)

    elif kind == "funcall":
        for arg in expr.get("args", []):
            collect_divisors_expr(arg, divisors)


def collect_divisors_stmts(stmts: List[Dict[str, Any]], divisors: Set[int]) -> None:
    for stmt in stmts or []:
        if not isinstance(stmt, dict):
            continue

        kind = stmt.get("kind")

        if kind == "assign":
            collect_divisors_expr(stmt.get("expr"), divisors)

        elif kind == "call":
            for arg in stmt.get("args", []):
                collect_divisors_expr(arg, divisors)

        elif kind == "if":
            collect_divisors_expr(stmt.get("cond"), divisors)
            collect_divisors_stmts(stmt.get("then_body", []), divisors)
            else_body = stmt.get("else_body")
            if else_body:
                collect_divisors_stmts(else_body, divisors)

        elif kind in ("while", "repeat", "for"):
            if kind == "while":
                collect_divisors_expr(stmt.get("cond"), divisors)
            elif kind == "repeat":
                collect_divisors_expr(stmt.get("until"), divisors)
            collect_divisors_stmts(stmt.get("body", []), divisors)

        elif kind == "block":
            collect_divisors_stmts(stmt.get("stmts", []), divisors)


def extract_all_calls(body: List[Dict[str, Any]], func_name: str) -> List[Tuple[int, int]]:
    a = count_calls_in_stmts(body, func_name)

    divisors: Set[int] = set()
    collect_divisors_stmts(body, divisors)

    b = min(divisors) if divisors else 1

    if a == 0:
        print("   Llamadas detectadas: []")
        return []

    calls = [(a, b)]
    print(f"   Llamadas detectadas (a,b): {calls}")
    return calls


def count_nested_loops(stmts: List[Dict[str, Any]], depth: int = 0) -> int:
    max_depth = depth

    for stmt in stmts or []:
        if not isinstance(stmt, dict):
            continue

        kind = stmt.get("kind")

        if kind in ("for", "while", "repeat"):
            body = stmt.get("body", [])
            nested_depth = count_nested_loops(body, depth + 1)
            max_depth = max(max_depth, nested_depth)

        elif kind == "if":
            then_depth = count_nested_loops(stmt.get("then_body", []), depth)
            else_body = stmt.get("else_body")
            else_depth = count_nested_loops(else_body, depth) if else_body else depth
            max_depth = max(max_depth, then_depth, else_depth)

        elif kind == "block":
            block_depth = count_nested_loops(stmt.get("stmts", []), depth)
            max_depth = max(max_depth, block_depth)

    return max_depth


def has_external_function_call(stmts: List[Dict[str, Any]], func_name: str) -> bool:
    for stmt in stmts or []:
        if not isinstance(stmt, dict):
            continue

        kind = stmt.get("kind")

        if kind == "call":
            if stmt.get("name") != func_name:
                return True

        elif kind == "assign":
            expr = stmt.get("expr")
            if isinstance(expr, dict) and expr.get("kind") == "funcall":
                if expr.get("name") != func_name:
                    return True

        elif kind == "if":
            if has_external_function_call(stmt.get("then_body", []), func_name):
                return True
            else_body = stmt.get("else_body")
            if else_body and has_external_function_call(else_body, func_name):
                return True

        elif kind in ("for", "while", "repeat", "block"):
            body = stmt.get("body", []) if kind != "block" else stmt.get("stmts", [])
            if has_external_function_call(body, func_name):
                return True

    return False


def estimate_non_recursive_work(body: List[Dict[str, Any]], func_name: str) -> Expr:
    loop_depth = count_nested_loops(body)
    has_external_call = has_external_function_call(body, func_name)

    if has_external_call:
        result = sym("n")
        print(f"   f(n): Llamada externa detectada → O(n)")

    elif loop_depth >= 3:
        result = Pow(Sym("n"), 3)
        print(f"   f(n): {loop_depth} bucles anidados → O(n³)")

    elif loop_depth == 2:
        result = Pow(Sym("n"), 2)
        print(f"   f(n): 2 bucles anidados → O(n²)")

    elif loop_depth == 1:
        result = sym("n")
        print(f"   f(n): 1 bucle → O(n)")

    else:
        result = const(1)
        print(f"   f(n): Sin bucles → O(1)")

    return result


def extract_recurrence(proc: dict, param_name: str = "n") -> Optional[RecurrenceRelation]:
    func_name = proc.get("name", "")
    body = proc.get("body", [])

    print(f"\n{'=' * 70}")
    print(f"ANALIZANDO FUNCION: {func_name}")
    print(f"{'=' * 70}")

    calls = extract_all_calls(body, func_name)

    if not calls:
        print(f"No se detectaron llamadas recursivas")
        return None

    f_expr = estimate_non_recursive_work(body, func_name)

    rec = None

    if len(calls) == 1:
        a, b = calls[0]
        if b < 0:
            b = abs(b)
        rec = RecurrenceRelation(a=a, b=b, f_expr=f_expr)
        print(f"\nRecurrencia detectada: T(n) = {a}T(n/{b}) + f(n)")

    elif len(calls) == 2:
        (a1, b1), (a2, b2) = calls
        if b1 < 0:
            b1 = abs(b1)
        if b2 < 0:
            b2 = abs(b2)
        rec = RecurrenceRelation(a=a1, b=b1, c=a2, d=b2, f_expr=f_expr)
        print(f"\nRecurrencia múltiple: T(n) = {a1}T(n-{b1}) + {a2}T(n-{b2}) + f(n)")

    else:
        total_a = sum(abs(a) for a, _ in calls)
        avg_b = abs(calls[0][1])
        rec = RecurrenceRelation(a=total_a, b=avg_b, f_expr=f_expr)
        print(f"\nRecurrencia múltiple simplificada: T(n) = {total_a}T(n/{avg_b}) + f(n)")

    print(f"   a={rec.a}, b={rec.b}, c={rec.c}, d={rec.d}")
    print(f"   f(n)={rec.f_expr}")
    print(f"{'=' * 70}\n")

    return rec