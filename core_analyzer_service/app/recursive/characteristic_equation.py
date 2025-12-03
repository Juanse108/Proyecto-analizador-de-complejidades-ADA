from typing import Optional

from ..domain import Expr


def _format_linear_recurrence(rec) -> str:
    """
    Construye una representación textual de una recurrencia lineal
    con coeficientes constantes, usando los campos típicos:
        T(n) = c·T(n-1) + d·T(n-2) + f(n)
    """
    parts = []

    c = getattr(rec, "c", 0)
    d = getattr(rec, "d", 0)
    f_expr = getattr(rec, "f_expr", None)

    if c:
        parts.append(f"{c}·T(n-1)")
    if d:
        parts.append(f"{d}·T(n-2)")
    if f_expr is not None:
        parts.append(str(f_expr))

    if not parts:
        return "T(n) = ?"

    return "T(n) = " + " + ".join(parts)


def _is_zero(coeff) -> bool:
    """
    Intenta decidir de forma robusta si un coeficiente es 0.
    Soporta enteros y expresiones simbólicas sencillas cuyo str sea '0'.
    """
    if coeff is None:
        return True
    if isinstance(coeff, (int, float)):
        return abs(coeff) < 1e-9
    s = str(coeff).strip()
    return s in {"0", "0.0", "0.000"}


def build_characteristic_explanation(rec, solution_expr: Optional[Expr]) -> str:
    """
    Genera una explicación del método de la ecuación característica aplicado
    a una recurrencia lineal de primer o segundo orden con coeficientes
    constantes:

        T(n) = c·T(n-1) + d·T(n-2) + f(n)

    No intenta volver a resolver la recurrencia: asume que 'solution_expr'
    ya representa la solución asintótica (por ejemplo devuelta por
    solve_linear_recurrence) y la usa solo como cierre.
    """
    lines = []

    recurrence_str = _format_linear_recurrence(rec)
    lines.append("Método de la ecuación característica aplicado a la recurrencia lineal:")
    lines.append(recurrence_str)
    lines.append("")

    c = getattr(rec, "c", 0)
    d = getattr(rec, "d", 0)

    # Decidimos si es primer orden (sin T(n-2)) o segundo orden.
    if _is_zero(d):
        # Primer orden: T(n) = c T(n-1) + f(n)
        lines.append("1) Parte homogénea (sin término f(n)):")
        lines.append("   T_h(n) = c·T_h(n-1)")
        lines.append("   Proponemos una solución de la forma T_h(n) = r^n.")
        lines.append("   Sustituyendo en la recurrencia homogénea:")
        lines.append("      r^n = c·r^{n-1}")
        lines.append("   Dividimos por r^{n-1} (r ≠ 0):")
        lines.append("      r = c")
        lines.append("")
        lines.append("   La ecuación característica es:")
        lines.append("      r - c = 0")
        lines.append("   con raíz r = c.")
        lines.append("")
        lines.append("   Por tanto, la solución homogénea tiene la forma:")
        lines.append("      T_h(n) = C·c^n")
    else:
        # Segundo orden: T(n) = c T(n-1) + d T(n-2) + f(n)
        lines.append("1) Parte homogénea (sin término f(n)):")
        lines.append("   T_h(n) = c·T_h(n-1) + d·T_h(n-2)")
        lines.append("   Proponemos una solución de la forma T_h(n) = r^n.")
        lines.append("   Sustituyendo en la recurrencia homogénea:")
        lines.append("      r^n = c·r^{n-1} + d·r^{n-2}")
        lines.append("   Dividimos por r^{n-2} (r ≠ 0):")
        lines.append("      r^2 = c·r + d")
        lines.append("")
        lines.append("   La ecuación característica asociada es:")
        lines.append("      r^2 - c·r - d = 0")
        lines.append("")
        lines.append("   Sus raíces r₁, r₂ determinan la forma de la solución homogénea:")
        lines.append("      - Si r₁ ≠ r₂:  T_h(n) = C₁·r₁^n + C₂·r₂^n")
        lines.append("      - Si r₁ = r₂:  T_h(n) = (C₁ + C₂·n)·r₁^n")
        lines.append("      - Si las raíces son complejas conjugadas,")
        lines.append("        la solución se puede escribir en términos de senos/cosenos,")
        lines.append("        pero asintóticamente domina |r|^n.")

    lines.append("")
    lines.append("2) Parte particular:")
    lines.append(
        "   A la solución homogénea se le suma una solución particular T_p(n) "
        "que depende de la forma de f(n) (constante, polinómica, exponencial, etc.)."
    )
    lines.append("   El analizador resuelve esta parte de forma automática y combina")
    lines.append("   T_h(n) + T_p(n), quedándose con el término dominante.")

    if solution_expr is not None:
        lines.append("")
        lines.append(
            f"3) Conclusión asintótica: la solución resultante es Θ({solution_expr})."
        )
        lines.append(f"   Por tanto, T(n) = Θ({solution_expr}).")

    return "\n".join(lines)
