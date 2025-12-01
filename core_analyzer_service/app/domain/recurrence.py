from typing import Optional
from dataclasses import dataclass

from .expr import Expr


@dataclass
class RecurrenceRelation:
    a: int
    b: int
    c: int = 0
    d: int = 0
    f_expr: Expr = None
    base_case: Expr = None


@dataclass
class RecursiveAnalysisResult:
    recurrence: RecurrenceRelation
    big_o: Expr
    big_omega: Expr
    theta: Optional[Expr]
    method_used: str
    master_theorem_case: Optional[int]
    explanation: str