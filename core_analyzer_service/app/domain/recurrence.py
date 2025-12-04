"""
recurrence.py - Modelos de recurrencia mejorados
================================================

CAMBIO PRINCIPAL: Añadimos campo 'equation_text' para la ecuación completa.
"""

from typing import Optional
from dataclasses import dataclass

from .expr import Expr


@dataclass
class RecurrenceRelation:
    """
    Representa una relación de recurrencia.
    
    Formas soportadas:
    1. Divide & Conquer: T(n) = a·T(n/b) + f(n)
    2. Lineal simple: T(n) = c·T(n-1) + f(n)
    3. Lineal doble: T(n) = c·T(n-1) + d·T(n-2) + f(n)
    
    Atributos:
        a: Número de subproblemas (en divide & conquer)
        b: Factor de división del tamaño (n/b)
        c: Coeficiente de T(n-1) (en recursión lineal)
        d: Coeficiente de T(n-2) (en recursión lineal de orden 2)
        f_expr: Trabajo no recursivo (expresión simbólica)
        base_case: Caso base T(1) o T(0)
        equation_text: 🆕 ECUACIÓN COMPLETA como string legible
    """
    a: int
    b: int
    c: int = 0
    d: int = 0
    f_expr: Expr = None
    base_case: Expr = None
    equation_text: str = ""  # 🆕 NUEVO CAMPO


@dataclass
class RecursiveAnalysisResult:
    """
    Resultado completo del análisis recursivo.
    
    🆕 NUEVO: Incluye la ecuación de recurrencia formateada.
    """
    recurrence: RecurrenceRelation
    big_o: Expr
    big_omega: Expr
    theta: Optional[Expr]
    method_used: str
    master_theorem_case: Optional[int]
    explanation: str
    recurrence_equation: str = ""  # 🆕 NUEVO: ecuación lista para mostrar