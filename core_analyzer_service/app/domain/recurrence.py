"""
Recurrence relation models.

Defines data structures for representing and analyzing recurrence relations
in recursive algorithms.
"""

from typing import Optional
from dataclasses import dataclass

from .expr import Expr


@dataclass
class RecurrenceRelation:
    """
    Represents a recurrence relation.
    
    Supported forms:
    1. Divide & Conquer: T(n) = a·T(n/b) + f(n)
    2. Simple linear: T(n) = c·T(n-1) + f(n)
    3. Double linear: T(n) = c·T(n-1) + d·T(n-2) + f(n)
    
    Attributes:
        a: Number of subproblems (in divide & conquer)
        b: Division factor (n/b)
        c: Coefficient of T(n-1) (in linear recursion)
        d: Coefficient of T(n-2) (in order-2 linear recursion)
        f_expr: Non-recursive work (symbolic expression)
        base_case: Base case T(1) or T(0)
        equation_text: Full equation as readable string
    """
    a: int
    b: int
    c: int = 0
    d: int = 0
    f_expr: Expr = None
    base_case: Expr = None
    equation_text: str = ""


@dataclass
class RecursiveAnalysisResult:
    """
    Complete result of recursive analysis.
    
    Includes the formatted recurrence equation for display.
    """
    recurrence: RecurrenceRelation
    big_o: Expr
    big_omega: Expr
    theta: Optional[Expr]
    method_used: str
    master_theorem_case: Optional[int]
    explanation: str
    recurrence_equation: str = ""