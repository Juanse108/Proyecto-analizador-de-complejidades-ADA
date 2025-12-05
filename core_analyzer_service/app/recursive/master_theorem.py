import math
from typing import Tuple, Optional

from ..domain import Expr, sym, const, mul, log, Pow, Sym, degree
from ..domain.recurrence import RecurrenceRelation


def solve_master_theorem(rec: RecurrenceRelation) -> Tuple[Expr, int, str]:
    a, b = rec.a, rec.b

    if b == 1:
        poly_deg, _ = degree(rec.f_expr)

        if poly_deg == 0:
            result = sym("n")
            explanation = "Recursión lineal: T(n) = T(n-1) + c → Θ(n)"
            return result, 0, explanation
        else:
            result = Pow(Sym("n"), 2)
            explanation = "Recursión lineal con trabajo O(n) → Θ(n²)"
            return result, 0, explanation

    log_b_a = math.log(a) / math.log(b)
    poly_deg, _ = degree(rec.f_expr)

    epsilon = 0.01
    if poly_deg < log_b_a - epsilon:
        exp = round(log_b_a)
        if abs(exp - log_b_a) < 0.01:
            if exp == 1:
                result = sym("n")
            else:
                result = Pow(Sym("n"), exp)
        else:
            result = sym("n")

        explanation = (
            f"Teorema Maestro Caso 1: f(n)=O(n^{poly_deg}) < n^{log_b_a:.2f} → Θ(n^{exp})"
        )
        return result, 1, explanation

    elif abs(poly_deg - log_b_a) < epsilon:
        exp = round(log_b_a)
        if exp == 1:
            result = mul(sym("n"), log(sym("n"), const(2)))
        else:
            result = mul(Pow(Sym("n"), exp), log(sym("n"), const(2)))

        explanation = (
            f"Teorema Maestro Caso 2: f(n)=Θ(n^{log_b_a:.2f}) → Θ(n^{exp} log n)"
        )
        return result, 2, explanation

    else:
        result = rec.f_expr
        explanation = (
            f"Teorema Maestro Caso 3: f(n)=Ω(n^{poly_deg}) > n^{log_b_a:.2f} → Θ(f(n))"
        )
        return result, 3, explanation

def solve_linear_recurrence(rec: RecurrenceRelation) -> Tuple[Optional[Expr], str]:
    """
    Resuelve recurrencias lineales.
    """
    if rec.b != 1:
        return None, ""

    if rec.f_expr is not None:
        poly_deg, _ = degree(rec.f_expr)
    else:
        poly_deg = 0

    if rec.c == 0:
        a = rec.a
        k = poly_deg

        if k == 0:
            if a == 1:
                expr = sym("n")
                explanation = (
                    "Recursión lineal de orden 1: T(n) = T(n-1) + Θ(1) ⇒ T(n) = Θ(n)"
                )
            elif a > 1:
                expr = sym(f"{a}^n")
                explanation = (
                    f"Recursión lineal de orden 1: T(n) = {a}·T(n-1) + Θ(1) "
                    f"⇒ T(n) = Θ({a}^n)"
                )
            else:
                expr = sym("n")
                explanation = (
                    "Recursión lineal degenerada (a≤0), asumimos T(n) = Θ(n)"
                )
            return expr, explanation

        exp = k + 1
        if exp == 1:
            expr = sym("n")
        else:
            expr = Pow(Sym("n"), exp)

        explanation = (
            f"Recursión lineal de orden 1: T(n) = a·T(n-1) + Θ(n^{k}) "
            f"⇒ T(n) = Θ(n^{k + 1})"
        )
        return expr, explanation

    if rec.d == 2:
        a = rec.a
        c_coef = rec.c

        disc = a * a + 4 * c_coef

        if disc < 0:
            expr = sym("2^n")
            explanation = (
                "Recurrencia lineal de orden 2 con raíces complejas; "
                "asumimos crecimiento exponencial Θ(2^n)"
            )
            return expr, explanation

        sqrt_disc = math.sqrt(disc)
        r1 = (a + sqrt_disc) / 2.0
        r2 = (a - sqrt_disc) / 2.0
        rho = max(abs(r1), abs(r2))

        if a == 1 and c_coef == 1 and poly_deg == 0:
            expr = sym("2^n")
            explanation = (
                "Fibonacci ingenuo: T(n) = T(n-1) + T(n-2) + Θ(1) ⇒ "
                "T(n) = Θ(φ^n) ≈ Θ(2^n)"
            )
            return expr, explanation

        base_int = max(2, int(round(rho)))
        expr = sym(f"{base_int}^n")
        explanation = (
            "Recurrencia lineal de orden 2: T(n) = a·T(n-1) + c·T(n-2) + f(n) ⇒ "
            f"T(n) = Θ(ρ^n), con ρ≈{rho:.2f} ≈ {base_int}^n"
        )
        return expr, explanation

    return None, ""