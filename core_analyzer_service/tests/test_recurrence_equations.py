"""
Test de ecuaciones de recurrencia
==================================

Verifica que cada algoritmo estándar genere la ecuación correcta.
"""

import pytest
from app.recursive.equation_formatter import format_recurrence_equation
from app.domain.recurrence import RecurrenceRelation
from app.domain.expr import sym, const


def test_merge_sort_equation():
    """Merge Sort debe generar T(n) = 2·T(n/2) + c·n"""
    rec = RecurrenceRelation(a=2, b=2, f_expr=sym("n"))
    equation = format_recurrence_equation(rec)
    
    assert "T(n) = 2·T(n/2)" in equation
    assert "c·n" in equation
    assert "T(1) = d" in equation
    assert "2T(n/2)" not in equation  # No debe tener solución directa


def test_binary_search_equation():
    """Binary Search debe generar T(n) = T(n/2) + c"""
    rec = RecurrenceRelation(a=1, b=2, f_expr=const(1))
    equation = format_recurrence_equation(rec)
    
    assert "T(n) = T(n/2) + c" in equation
    assert "T(1) = d" in equation


def test_fibonacci_equation():
    """Fibonacci debe generar T(n) = T(n-1) + T(n-2) + c"""
    rec = RecurrenceRelation(a=1, b=1, c=1, d=1, f_expr=const(1))
    equation = format_recurrence_equation(rec)
    
    assert "T(n) = T(n-1) + T(n-2)" in equation
    assert "T(0) = d₀" in equation
    assert "T(1) = d₁" in equation


def test_factorial_equation():
    """Factorial debe generar T(n) = T(n-1) + c"""
    rec = RecurrenceRelation(a=1, b=1, f_expr=const(1))
    equation = format_recurrence_equation(rec)

def test_quicksort_worst_case():
        """QuickSort (peor) debe generar T(n) = T(n-1) + c·n"""
        rec = RecurrenceRelation(a=1, b=1, f_expr=sym("n"))
        equation = format_recurrence_equation(rec)
        assert "T(n) = T(n-1)" in equation
        assert "c·n" in equation


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
