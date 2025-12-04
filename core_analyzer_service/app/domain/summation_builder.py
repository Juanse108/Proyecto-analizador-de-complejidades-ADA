# core_analyzer_service/app/domain/summation_builder.py
"""
summation_builder.py - Construcción de representaciones de sumatorias
=====================================================================

Genera expresiones matemáticas explícitas de sumatorias a partir del AST,
permitiendo mostrar el razonamiento paso a paso desde bucles hasta polinomios.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class Summation:
    """
    Representa una sumatoria matemática.
    
    Ejemplo: Σ_{i=1}^{n-1} (n - i)
    """
    index_var: str  # Variable de índice (i, j, k, ...)
    lower_bound: str  # Límite inferior (1, 0, i+1, ...)
    upper_bound: str  # Límite superior (n, n-1, n-i, ...)
    body: str  # Cuerpo de la suma (1, n-i, ...)
    nested: Optional['Summation'] = None  # Sumatoria anidada
    
    def to_latex(self) -> str:
        """Convierte a notación LaTeX."""
        result = f"\\sum_{{{self.index_var}={self.lower_bound}}}^{{{self.upper_bound}}} "
        if self.nested:
            result += self.nested.to_latex()
        else:
            result += self.body
        return result
    
    def to_text(self) -> str:
        """Convierte a texto plano legible."""
        result = f"Σ_{{{self.index_var}={self.lower_bound}}}^{{{self.upper_bound}}} "
        if self.nested:
            result += self.nested.to_text()
        else:
            result += f"({self.body})"
        return result


@dataclass
class SummationAnalysis:
    """
    Análisis completo de sumatorias para un algoritmo.

    Incluye:
    - Sumatorias originales derivadas del código
    - Simplificaciones paso a paso
    - Forma polinómica final
    - (Opcional) Versiones en LaTeX para renderizado matemático
    """
    # Texto plano (lo que ya usas)
    worst_summation: str
    best_summation: str
    avg_summation: Optional[str]

    worst_simplified: str
    best_simplified: str
    avg_simplified: Optional[str]

    worst_polynomial: str
    best_polynomial: str
    avg_polynomial: Optional[str]

    # 🔢 NUEVO: versiones LaTeX
    worst_summation_latex: str
    best_summation_latex: str
    avg_summation_latex: Optional[str]

    worst_simplified_latex: str
    best_simplified_latex: str
    avg_simplified_latex: Optional[str]

    worst_polynomial_latex: str
    best_polynomial_latex: str
    avg_polynomial_latex: Optional[str]



def build_summation_from_for(stmt: dict, context_vars: Dict[str, str]) -> Optional[Summation]:
    """
    Construye una sumatoria a partir de un bucle FOR del AST.
    
    Args:
        stmt: Nodo del AST tipo 'for'
        context_vars: Variables del contexto externo (para límites superiores)
        
    Returns:
        Objeto Summation o None si no se puede construir
    """
    if stmt.get("kind") != "for":
        return None
    
    var = stmt.get("var", "i")
    
    # Extraer límite inferior
    start = stmt.get("start")
    if isinstance(start, dict) and start.get("kind") == "num":
        lower = str(start.get("value", 1))
    else:
        lower = "1"  # Default
    
    # Extraer límite superior
    end = stmt.get("end")
    upper = _expr_to_string(end, context_vars)
    
    # El cuerpo de la suma es simplemente 1 por cada iteración
    # (el costo real se multiplica después)
    body = "1"
    
    return Summation(
        index_var=var,
        lower_bound=lower,
        upper_bound=upper,
        body=body
    )


def _expr_to_string(expr: Any, context: Dict[str, str]) -> str:
    """
    Convierte una expresión del AST a string matemático.
    
    Args:
        expr: Nodo de expresión del AST
        context: Variables disponibles en el contexto
        
    Returns:
        String representando la expresión (ej: "n-1", "n-i")
    """
    if not isinstance(expr, dict):
        return str(expr)
    
    kind = expr.get("kind")
    
    if kind == "num":
        return str(expr.get("value", 0))
    
    if kind == "var":
        return expr.get("name", "n")
    
    if kind == "binop":
        op = expr.get("op", "+")
        left = _expr_to_string(expr.get("left"), context)
        right = _expr_to_string(expr.get("right"), context)
        
        # Normalizar operadores
        if op == "+":
            return f"{left} + {right}"
        elif op == "-":
            return f"{left} - {right}"
        elif op == "*":
            return f"({left})({right})"
        elif op == "/":
            return f"{left}/{right}"
    
    return "n"  # Fallback


def analyze_nested_loops(stmts: List[dict]) -> SummationAnalysis:
    """
    Analiza bucles anidados y genera sumatorias.
    
    Args:
        stmts: Lista de sentencias del cuerpo principal
        
    Returns:
        SummationAnalysis con todas las representaciones
    """
    # Buscar estructura de bucles anidados
    outer_loop = None
    inner_loop = None
    
    for stmt in stmts:
        if stmt.get("kind") == "for":
            outer_loop = stmt
            # Buscar bucle interno
            for inner_stmt in stmt.get("body", []):
                if inner_stmt.get("kind") == "for":
                    inner_loop = inner_stmt
                    break
            break
    
    if not outer_loop:
        return SummationAnalysis(
            # Texto plano
            worst_summation="1",
            best_summation="1",
            avg_summation="1",
            worst_simplified="1",
            best_simplified="1",
            avg_simplified="1",
            worst_polynomial="c",
            best_polynomial="c",
            avg_polynomial="c",
            # LaTeX (trivial)
            worst_summation_latex="1",
            best_summation_latex="1",
            avg_summation_latex="1",
            worst_simplified_latex="1",
            best_simplified_latex="1",
            avg_simplified_latex="1",
            worst_polynomial_latex="c",
            best_polynomial_latex="c",
            avg_polynomial_latex="c",
        )

    
    # Construir sumatoria del bucle externo
    outer_sum = build_summation_from_for(outer_loop, {})
    
    if inner_loop:
        # Bucles anidados
        context = {outer_sum.index_var: outer_sum.upper_bound}
        inner_sum = build_summation_from_for(inner_loop, context)
        outer_sum.nested = inner_sum

        # Para BubbleSort: Σ_{i=1}^{n-1} Σ_{j=1}^{n-i} 1
        worst_text = outer_sum.to_text()
        worst_latex = outer_sum.to_latex()

        # Simplificación paso a paso: Σ_{i=1}^{n-1} (n - i)
        simplified = (
            f"Σ_{{{outer_sum.index_var}={outer_sum.lower_bound}}}^"
            f"{{{outer_sum.upper_bound}}} ({inner_sum.upper_bound})"
        )

        # Versión LaTeX de la simplificación
        simplified_sum = Summation(
            index_var=outer_sum.index_var,
            lower_bound=outer_sum.lower_bound,
            upper_bound=outer_sum.upper_bound,
            body=inner_sum.upper_bound,
        )
        simplified_latex = simplified_sum.to_latex()

        # Forma cerrada: n(n-1)/2
        polynomial = "n(n-1)/2 = (n² - n)/2"
        polynomial_latex = r"\frac{n(n-1)}{2} = \frac{n^2 - n}{2}"

        return SummationAnalysis(
            # Texto plano
            worst_summation=worst_text,
            best_summation=worst_text,  # Mismo para BubbleSort sin optimización
            avg_summation=worst_text,
            worst_simplified=simplified,
            best_simplified=simplified,
            avg_simplified=simplified,
            worst_polynomial=polynomial,
            best_polynomial=polynomial,
            avg_polynomial=polynomial,
            # LaTeX
            worst_summation_latex=worst_latex,
            best_summation_latex=worst_latex,
            avg_summation_latex=worst_latex,
            worst_simplified_latex=simplified_latex,
            best_simplified_latex=simplified_latex,
            avg_simplified_latex=simplified_latex,
            worst_polynomial_latex=polynomial_latex,
            best_polynomial_latex=polynomial_latex,
            avg_polynomial_latex=polynomial_latex,
        )
    else:
        # Bucle simple
        worst_text = outer_sum.to_text()
        worst_latex = outer_sum.to_latex()

        simplified = f"n - {outer_sum.lower_bound}"
        simplified_latex = f"n - {outer_sum.lower_bound}"

        polynomial = f"n - {outer_sum.lower_bound}"
        polynomial_latex = f"n - {outer_sum.lower_bound}"

        return SummationAnalysis(
            # Texto plano
            worst_summation=worst_text,
            best_summation=worst_text,
            avg_summation=worst_text,
            worst_simplified=simplified,
            best_simplified=simplified,
            avg_simplified=simplified,
            worst_polynomial=polynomial,
            best_polynomial=polynomial,
            avg_polynomial=polynomial,
            # LaTeX
            worst_summation_latex=worst_latex,
            best_summation_latex=worst_latex,
            avg_summation_latex=worst_latex,
            worst_simplified_latex=simplified_latex,
            best_simplified_latex=simplified_latex,
            avg_simplified_latex=simplified_latex,
            worst_polynomial_latex=polynomial_latex,
            best_polynomial_latex=polynomial_latex,
            avg_polynomial_latex=polynomial_latex,
        )



def format_summation_equation(case: str, summation: str, simplified: str, polynomial: str) -> str:
    """
    Formatea una ecuación completa de sumatoria para mostrar en UI.
    
    Args:
        case: "worst", "best" o "avg"
        summation: Sumatoria original
        simplified: Forma simplificada
        polynomial: Polinomio final
        
    Returns:
        String formateado con múltiples líneas mostrando la derivación
    """
    case_label = {
        "worst": "T_worst(n)",
        "best": "T_best(n)",
        "avg": "T_avg(n)"
    }.get(case, "T(n)")
    
    lines = [
        f"{case_label} = c · {summation} + d",
        f"        = c · {simplified} + d",
        f"        = {polynomial}",
    ]
    
    return "\n".join(lines)