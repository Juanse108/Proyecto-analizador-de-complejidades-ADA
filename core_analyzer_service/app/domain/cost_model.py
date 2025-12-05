from typing import Optional, List, TYPE_CHECKING
from dataclasses import dataclass

from .expr import Expr, const, add

if TYPE_CHECKING:
    from ..iterative.execution_trace import ExecutionTrace


COST_MODEL = {
    "assign": 1,
    "compare": 1,
    "add": 1,
    "mul": 2,
    "div": 3,
    "mod": 3,
    "array_access": 2,
    "deref": 1,
    "jump": 1,
    "call": 2,
    "return": 1,
}


def cost_assign():
    return const(COST_MODEL["assign"])


def cost_compare():
    return const(COST_MODEL["compare"])


def cost_array_access():
    return const(COST_MODEL["array_access"])


def cost_arithmetic(op: str):
    if op in ("+", "-"):
        return const(COST_MODEL["add"])
    elif op in ("*"):
        return const(COST_MODEL["mul"])
    elif op in ("/", "div", "mod"):
        return const(COST_MODEL["div"])
    else:
        return const(1)


def cost_seq(*costs):
    return add(*costs)


def load_cost_model_from_env():
    import os

    for key in COST_MODEL:
        env_key = f"COST_{key.upper()}"
        if env_key in os.environ:
            try:
                COST_MODEL[key] = int(os.environ[env_key])
            except ValueError:
                pass


load_cost_model_from_env()


@dataclass
class LineCostInternal:
    line: int
    kind: str
    text: Optional[str]
    multiplier: Expr
    cost_worst: Expr
    cost_best: Expr
    cost_avg: Expr


@dataclass
class ProgramCost:
    worst: Expr
    best: Expr
    avg: Expr
    lines: List[LineCostInternal]
    binary_search_detected: bool = False
    method_used: str = "iteration"
    execution_trace: Optional['ExecutionTrace'] = None  # 🆕 Traza de ejecución