from typing import Optional, Tuple, Dict, Any

from ..domain import Expr, sym, const
from ..domain.ast_utils import is_var, is_num, is_binop


def upper_bound_symbol(end: dict) -> Optional[Tuple[str, str]]:
    if is_var(end):
        return ("sym", end["name"])

    if (
        isinstance(end, dict)
        and end.get("kind") == "binop"
        and end.get("op") in ("+", "-")
    ):
        left = end.get("left")
        right = end.get("right")

        if is_var(left) and (is_num(right) or is_var(right)):
            return ("sym", left["name"])

    return None


def detect_triangular_loop(start, end, var: str, env: Dict[str, Tuple[str, Any]]) -> Tuple[bool, Optional[str]]:
    is_triangular = False
    triangular_var = None

    if is_var(end):
        end_var_name = end["name"]
        if end_var_name in ("i", "j", "k", "p", "q") and end_var_name != var:
            is_triangular = True
            triangular_var = end_var_name

    if is_var(start):
        start_var_name = start["name"]
        if start_var_name in ("i", "j", "k", "p", "q") and start_var_name != var:
            is_triangular = True
            triangular_var = start_var_name

    return is_triangular, triangular_var


def estimate_for_iterations(start, end, var: str, is_triangular: bool, triangular_var: Optional[str], env: Dict[str, Tuple[str, Any]]) -> Expr:
    if is_triangular:
        outer_sym = env.get(triangular_var)
        if outer_sym and outer_sym[0] == "sym":
            outer_limit = sym(outer_sym[1])
        else:
            outer_limit = sym("n")
        return outer_limit
    else:
        ub = upper_bound_symbol(end)

        if is_num(start, 1) and ub and ub[0] == "sym":
            return sym(ub[1])
        elif is_num(start, 1) and is_num(end):
            return const(max(0, end["value"]))
        elif ub and ub[0] == "sym":
            return sym(ub[1])
        else:
            return const(1)


def update_env_from_for(var: str, end, env: Dict[str, Tuple[str, Any]]) -> None:
    ub = upper_bound_symbol(end)
    if var and ub and ub[0] == "sym":
        env[var] = ("sym", ub[1])
    elif var and is_num(end):
        env[var] = ("num", end["value"])