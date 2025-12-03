from typing import Optional

from ..domain import Expr


def _format_recurrence(rec) -> str:
    """
    Construye una representación textual sencilla de la recurrencia, del estilo:
        T(n) = a T(n/b) + c T(n-1) + d T(n-2) + f(n)
    usando los atributos típicos de RecurrenceRelation (a, b, c, d, f_expr).
    """
    parts = []

    a = getattr(rec, "a", 0)
    b = getattr(rec, "b", None)
    c = getattr(rec, "c", 0)
    d = getattr(rec, "d", 0)
    f_expr = getattr(rec, "f_expr", None)

    if a:
        if b:
            parts.append(f"{a}·T(n/{b})")
        else:
            parts.append(f"{a}·T(n)")

    if c:
        parts.append(f"{c}·T(n-1)")

    if d:
        parts.append(f"{d}·T(n-2)")

    if f_expr is not None:
        parts.append(str(f_expr))

    if not parts:
        return "T(n) = ?"

    return "T(n) = " + " + ".join(parts)


def build_iteration_explanation(rec, solution_expr: Optional[Expr]) -> str:
    """
    Genera una explicación en español aplicando el método de la iteración
    (desenrollar la recurrencia) a la relación 'rec'.

    No intenta resolver simbólicamente la suma: asume que otra rutina
    (p.ej. teorema maestro o ecuaciones lineales) ya obtuvo una expresión
    asintótica aproximada 'solution_expr', y la usa solo como cierre.
    """
    lines = []

    recurrence_str = _format_recurrence(rec)
    lines.append("Método de la iteración aplicado a la recurrencia:")
    lines.append(recurrence_str)

    a = getattr(rec, "a", 0)
    b = getattr(rec, "b", 1)
    c = getattr(rec, "c", 0)
    d = getattr(rec, "d", 0)

    # Caso típico divide & conquer: T(n) = a T(n/b) + f(n)
    if a and b > 1 and c == 0 and d == 0:
        lines.append("")
        lines.append("Desenrollando k veces (divide y vencerás):")
        lines.append("T(n) = a·T(n/b) + f(n)")
        lines.append("     = a·[a·T(n/b²) + f(n/b)] + f(n)")
        lines.append("     = a²·T(n/b²) + a·f(n/b) + f(n)")
        lines.append("     = …")
        lines.append("     = aᵏ·T(n/bᵏ) + ∑_{i=0}^{k-1} aⁱ·f(n/bⁱ).")
        lines.append("")
        lines.append("Cuando el tamaño del subproblema es aproximadamente 1,")
        lines.append("n/bᵏ ≈ 1 ⇒ k ≈ log_b(n).")
        lines.append("Sustituyendo k ≈ log_b(n), se obtiene:")
        lines.append("T(n) = a^{log_b(n)}·T(1) + ∑_{i=0}^{log_b(n)-1} aⁱ·f(n/bⁱ).")
    else:
        # Caso lineal / paso 1 típico: T(n) = T(n-1) + f(n)
        lines.append("")
        lines.append("Desenrollando algunas veces (caso lineal típico):")
        lines.append("T(n) = T(n-1) + f(n)")
        lines.append("     = T(n-2) + f(n-1) + f(n)")
        lines.append("     = T(n-3) + f(n-2) + f(n-1) + f(n)")
        lines.append("     = …")
        lines.append("     = T(1) + ∑_{j=2}^{n} f(j).")
        lines.append("")
        lines.append("La complejidad se obtiene estudiando asintóticamente dicha suma")
        lines.append("(por ejemplo, usando fórmulas conocidas para series).")

    if solution_expr is not None:
        lines.append("")
        lines.append(f"En este problema concreto, la suma anterior es Θ({solution_expr}).")
        lines.append(f"Por tanto, T(n) = Θ({solution_expr}).")

    return "\n".join(lines)
