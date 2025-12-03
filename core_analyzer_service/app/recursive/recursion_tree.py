# core_analyzer_service/app/recursive/recursion_tree.py

from dataclasses import dataclass
from enum import Enum
from typing import Optional
import math


class NonRecursiveWorkKind(str, Enum):
    POLY = "poly"       # f(n) ~ n^k
    POLY_LOG = "poly_log"  # f(n) ~ n^k (log n)^p
    OTHER = "other"     # cualquier otra cosa más rara


@dataclass
class NonRecursiveWork:
    """
    Representa el trabajo no recursivo f(n) ~ n^k (log n)^p.
    """
    kind: NonRecursiveWorkKind
    poly_exp: float = 0.0  # exponente k en n^k
    log_exp: float = 0.0   # exponente p en (log n)^p
    repr: str = ""         # representación textual de f(n), p.ej. "n", "n^2", "n log n"


@dataclass
class DivideConquerRecurrence:
    """
    Modelo de recurrencia de divide & conquer:

        T(n) = a * T(n / b) + f(n)

    donde f(n) se modela con NonRecursiveWork.
    """
    a: int
    b: int
    work: NonRecursiveWork


@dataclass
class RecursionTreeResult:
    """
    Resultado del método del árbol de recursión.
    """
    big_o: str                    # p.ej. "O(n log n)"
    height_expr: str              # p.ej. "log_2(n)"
    per_level_cost_expr: str      # p.ej. "C_i(n) = a^i * f(n / b^i) ≈ ..."
    dominant_part: str            # "root", "leaves", "all-levels" o "unknown"
    method_case: Optional[int]    # 1, 2, 3 (casos estilo teorema maestro) o None
    explanation: str              # explicación en español, human-friendly


def _format_poly_log_term(n_exp: float, log_exp: float) -> str:
    """
    Construye una representación tipo:
      n^k (log n)^p
    omitiendo factores con exponente 0.
    """
    parts = []

    # n^k
    if abs(n_exp) > 1e-9:
        if abs(n_exp - 1.0) < 1e-9:
            parts.append("n")
        else:
            exp_str = f"{n_exp:.3g}".rstrip("0").rstrip(".")
            parts.append(f"n^{exp_str}")

    # (log n)^p
    if abs(log_exp) > 1e-9:
        if abs(log_exp - 1.0) < 1e-9:
            parts.append("log n")
        else:
            exp_str = f"{log_exp:.3g}".rstrip("0").rstrip(".")
            parts.append(f"(log n)^{exp_str}")

    if not parts:
        return "1"

    return " ".join(parts)


def _format_big_o(n_exp: float, log_exp: float) -> str:
    """
    Devuelve un string tipo O(n^k (log n)^p).
    """
    return f"O({_format_poly_log_term(n_exp, log_exp)})"


def analyze_recursion_tree(rec: DivideConquerRecurrence) -> RecursionTreeResult:
    """
    Aplica el método del árbol de recursión a una recurrencia:

        T(n) = a T(n/b) + f(n)

    donde f(n) se modela como:

        f(n) ≈ n^k (log n)^p

    usando los parámetros de `rec.work`.

    Devuelve:
      - big-O asintótico
      - altura del árbol
      - coste por nivel
      - parte dominante (raíz/hojas/todos los niveles)
      - explicación textual
    """
    # Validación básica
    if rec.a <= 0 or rec.b <= 1:
        explanation = (
            "No se puede aplicar el método del árbol de recursión: "
            f"los parámetros a={rec.a}, b={rec.b} no definen un divide and conquer estándar."
        )
        return RecursionTreeResult(
            big_o="O(?)",
            height_expr="?",
            per_level_cost_expr="?",
            dominant_part="unknown",
            method_case=None,
            explanation=explanation,
        )

    height_expr = f"log_{rec.b}(n)"

    # Expresión genérica del costo por nivel usando el modelo n^k (log n)^p
    per_level_cost_expr = (
        "C_i(n) = a^i * f(n / b^i) ≈ "
        f"a^i * (n / {rec.b}^i)^{rec.work.poly_exp}"
    )
    if rec.work.log_exp:
        per_level_cost_expr += f" * (log(n / {rec.b}^i))^{rec.work.log_exp}"

    # Si f(n) no es de tipo polinómico/logarítmico simple, no clasificamos
    if rec.work.kind not in (NonRecursiveWorkKind.POLY, NonRecursiveWorkKind.POLY_LOG):
        explanation = (
            "Se construye conceptualmente el árbol de recursión con altura "
            f"{height_expr}, pero f(n) = '{rec.work.repr}' no es polinómica/logarítmica "
            "simple, por lo que el analizador no clasifica automáticamente qué nivel domina."
        )
        return RecursionTreeResult(
            big_o="O(?)",
            height_expr=height_expr,
            per_level_cost_expr=per_level_cost_expr,
            dominant_part="unknown",
            method_case=None,
            explanation=explanation,
        )

    # Parámetros del modelo f(n) ~ n^k (log n)^p
    k = rec.work.poly_exp
    p = rec.work.log_exp

    # Exponente crítico n^{log_b a}
    n_exp_tree = math.log(rec.a, rec.b)
    eps = 1e-6

    # Clasificación tipo teorema maestro, pero explicada con árbol.
    if k < n_exp_tree - eps:
        # Caso 1: hojas dominan
        big_o = _format_big_o(n_exp_tree, 0.0)
        dominant_part = "leaves"
        method_case = 1
        explanation = (
            f"Árbol de recursión para T(n) = {rec.a} T(n/{rec.b}) + f(n) con "
            f"f(n) ≈ n^{k} (log n)^{p}.\n"
            f"La altura del árbol es {height_expr}.\n"
            "El costo del nivel i es C_i ≈ a^i * (n/b^i)^k.\n"
            f"Como k = {k:.3g} < log_{rec.b}({rec.a}) ≈ {n_exp_tree:.3g}, "
            "los costos por nivel decrecen y el costo total está dominado "
            "por las hojas, con complejidad "
            f"{big_o}."
        )

    elif abs(k - n_exp_tree) <= eps:
        # Caso 2: todos los niveles aportan casi lo mismo
        big_o = _format_big_o(k, p + 1.0)
        dominant_part = "all-levels"
        method_case = 2
        explanation = (
            f"Árbol de recursión para T(n) = {rec.a} T(n/{rec.b}) + f(n) con "
            f"f(n) ≈ n^{k} (log n)^{p}.\n"
            f"La altura del árbol es {height_expr}.\n"
            "El costo del nivel i es C_i ≈ a^i * (n/b^i)^k (log(n/b^i))^p.\n"
            f"Como k = {k:.3g} ≈ log_{rec.b}({rec.a}) ≈ {n_exp_tree:.3g}, "
            "cada nivel del árbol tiene costo Θ(f(n)), por lo que hay "
            f"log_{rec.b}(n) niveles que contribuyen casi lo mismo.\n"
            f"El costo total es la suma de todos los niveles: {big_o}."
        )

    else:
        # Caso 3: raíz domina
        big_o = _format_big_o(k, p)
        dominant_part = "root"
        method_case = 3
        explanation = (
            f"Árbol de recursión para T(n) = {rec.a} T(n/{rec.b}) + f(n) con "
            f"f(n) ≈ n^{k} (log n)^{p}.\n"
            f"La altura del árbol es {height_expr}.\n"
            "El costo del nivel i es C_i ≈ a^i * (n/b^i)^k (log(n/b^i))^p.\n"
            f"Como k = {k:.3g} > log_{rec.b}({rec.a}) ≈ {n_exp_tree:.3g}, "
            "los costos por nivel crecen al bajar en el árbol y el trabajo "
            "no recursivo de la raíz domina.\n"
            f"Por tanto, el costo total está gobernado por f(n): {big_o}."
        )

    return RecursionTreeResult(
        big_o=big_o,
        height_expr=height_expr,
        per_level_cost_expr=per_level_cost_expr,
        dominant_part=dominant_part,
        method_case=method_case,
        explanation=explanation,
    )
