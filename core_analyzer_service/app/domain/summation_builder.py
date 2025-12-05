"""Construcción de representaciones de sumatorias.

Genera fórmulas matemáticas correctas según el grado del polinomio detectado,
proporcionando análisis completo de sumatorias para algoritmos.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import re

@dataclass
class Summation:
    """Representa una sumatoria matemática.
    
    Attributes:
        index_var: Variable de índice
        lower_bound: Límite inferior
        upper_bound: Límite superior
        body: Cuerpo de la sumatoria
        nested: Sumatoria anidada opcional
    
    Ejemplo:
        Σ_{i=1}^{n-1} (n - i)
    """
    index_var: str
    lower_bound: str
    upper_bound: str
    body: str
    nested: Optional['Summation'] = None
    
    def to_latex(self) -> str:
        """Convierte la sumatoria a notación LaTeX.
        
        Returns:
            String con la representación LaTeX
        """
        result = f"\\sum_{{{self.index_var}={self.lower_bound}}}^{{{self.upper_bound}}} "
        if self.nested:
            result += self.nested.to_latex()
        else:
            result += self.body
        return result
    
    def to_text(self) -> str:
        """Convierte la sumatoria a texto plano legible.
        
        Returns:
            String con la representación en texto plano
        """
        result = f"Σ_{{{self.index_var}={self.lower_bound}}}^{{{self.upper_bound}}} "
        if self.nested:
            result += self.nested.to_text()
        else:
            result += f"({self.body})"
        return result


@dataclass
class SummationAnalysis:
    """Análisis completo de sumatorias para un algoritmo.
    
    Incluye representaciones de sumatorias, simplificaciones y polinomios
    para casos peor, mejor y promedio, en formatos texto y LaTeX.
    """
    worst_summation: str
    best_summation: str
    avg_summation: Optional[str]

    worst_simplified: str
    best_simplified: str
    avg_simplified: Optional[str]

    worst_polynomial: str
    best_polynomial: str
    avg_polynomial: Optional[str]

    # Propiedades clave para la visualización en la UI
    worst_summation_latex: str
    best_summation_latex: str
    avg_summation_latex: Optional[str]

    worst_simplified_latex: str
    best_simplified_latex: str
    avg_simplified_latex: Optional[str]

    worst_polynomial_latex: str
    best_polynomial_latex: str
    avg_polynomial_latex: Optional[str]


def _expr_to_string(expr: Any, context: Dict[str, str]) -> str:
    """Convierte una expresión del AST a string matemático.
    
    Args:
        expr: Expresión del AST a convertir
        context: Contexto con variables
        
    Returns:
        Representación en string de la expresión
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
        
        if op == "+":
            return f"{left} + {right}"
        elif op == "-":
            return f"{left} - {right}"
        elif op == "*":
            return f"({left})({right})"
        elif op == "/":
            return f"{left}/{right}"
    
    return "n"

def _count_loop_depth(stmts: List[dict], depth: int = 0) -> int:
    """Cuenta la profundidad máxima de bucles anidados.
    
    Args:
        stmts: Lista de sentencias a analizar
        depth: Profundidad actual (por defecto: 0)
        
    Returns:
        Profundidad máxima encontrada
    """
    max_depth = depth
    
    for stmt in stmts:
        if not isinstance(stmt, dict):
            continue
        
        kind = stmt.get("kind")
        
        if kind in ("for", "while", "repeat"):
            body = stmt.get("body", [])
            nested_depth = _count_loop_depth(body, depth + 1)
            max_depth = max(max_depth, nested_depth)
        
        elif kind == "if":
            then_depth = _count_loop_depth(stmt.get("then_body", []), depth)
            else_depth = _count_loop_depth(stmt.get("else_body", []), depth)
            max_depth = max(max_depth, then_depth, else_depth)
        
        elif kind == "block":
            block_depth = _count_loop_depth(stmt.get("stmts", []), depth)
            max_depth = max(max_depth, block_depth)
    
    return max_depth


def _find_outer_loop(stmts: List[dict]) -> Optional[dict]:
    """Encuentra el primer bucle del programa.
    
    Args:
        stmts: Lista de sentencias a buscar
        
    Returns:
        Primer bucle encontrado o None
    """
    for stmt in stmts:
        if isinstance(stmt, dict) and stmt.get("kind") in ("for", "while", "repeat"):
            return stmt
    return None


def _find_inner_loop(outer_loop: dict) -> Optional[dict]:
    """Encuentra el bucle anidado dentro de otro bucle.
    
    Args:
        outer_loop: Bucle externo donde buscar
        
    Returns:
        Bucle interno encontrado o None
    """
    body = outer_loop.get("body", [])
    return _find_outer_loop(body)


def _expr_uses_var(expr: dict, varname: str) -> bool:
    """Verifica si una expresión usa una variable específica."""
    if not isinstance(expr, dict):
        return False
    
    if expr.get("kind") == "var" and expr.get("name") == varname:
        return True
    
    for value in expr.values():
        if isinstance(value, dict):
            if _expr_uses_var(value, varname):
                return True
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict) and _expr_uses_var(item, varname):
                    return True
    
    return False


def _create_constant_analysis() -> SummationAnalysis:
    """Genera análisis para O(1)."""
    # Muestra 'c' para indicar que es constante.
    return SummationAnalysis(
        worst_summation="1",
        best_summation="1",
        avg_summation="1",
        worst_simplified="1",
        best_simplified="1",
        avg_simplified="1",
        worst_polynomial="c",
        best_polynomial="c",
        avg_polynomial="c",
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


def _create_linear_analysis(loop: dict) -> SummationAnalysis:
    """Genera análisis para O(n)."""
    var = loop.get("var", "i")
    
    # Sumatoria original
    summation_text = f"Σ_{{{var}=1}}^{{n}} 1"
    summation_latex = r"\sum_{i=1}^{n} 1"
    
    # Simplificación
    simplified = "n"
    simplified_latex = "n"
    
    # Polinomio
    polynomial = "n"
    polynomial_latex = "n"
    
    return SummationAnalysis(
        worst_summation=summation_text,
        best_summation=summation_text,
        avg_summation=summation_text,
        worst_simplified=simplified,
        best_simplified=simplified,
        avg_simplified=simplified,
        worst_polynomial=polynomial,
        best_polynomial=polynomial,
        avg_polynomial=polynomial,
        worst_summation_latex=summation_latex,
        best_summation_latex=summation_latex,
        avg_summation_latex=summation_latex,
        worst_simplified_latex=simplified_latex,
        best_simplified_latex=simplified_latex,
        avg_simplified_latex=simplified_latex,
        worst_polynomial_latex=polynomial_latex,
        best_polynomial_latex=polynomial_latex,
        avg_polynomial_latex=polynomial_latex,
    )


def _create_quadratic_analysis(outer_loop: dict, inner_loop: Optional[dict]) -> SummationAnalysis:
    """Genera análisis para O(n²)."""
    i_var = outer_loop.get("var", "i")
    j_var = inner_loop.get("var", "j") if inner_loop else "j"
    
    # Detectar si es triangular (j depende de i)
    is_triangular = False
    if inner_loop:
        end_expr = inner_loop.get("end", {})
        if isinstance(end_expr, dict) and end_expr.get("kind") == "binop":
            # Buscar si la expresión usa 'i' (ej. n-i)
            if _expr_uses_var(end_expr, i_var):
                is_triangular = True
    
    if is_triangular:
        # Bubble Sort style: Σ_{i=1}^{n-1} Σ_{j=1}^{n-i} 1
        summation_text = f"Σ_{{{i_var}=1}}^{{n-1}} Σ_{{{j_var}=1}}^{{n-{i_var}}} 1"
        summation_latex = r"\sum_{i=1}^{n-1} \sum_{j=1}^{n-i} 1"
        
        simplified = f"Σ_{{{i_var}=1}}^{{n-1}} (n - {i_var})"
        simplified_latex = r"\sum_{i=1}^{n-1} (n - i)"
        
        polynomial = "(n² - n)/2"
        polynomial_latex = r"\frac{n^2 - n}{2}"
    else:
        # Independientes: Σ_{i=1}^{n} Σ_{j=1}^{n} 1
        summation_text = f"Σ_{{{i_var}=1}}^{{n}} Σ_{{{j_var}=1}}^{{n}} 1"
        summation_latex = r"\sum_{i=1}^{n} \sum_{j=1}^{n} 1"
        
        simplified = f"Σ_{{{i_var}=1}}^{{n}} n = n²"
        simplified_latex = r"\sum_{i=1}^{n} n = n^2"
        
        polynomial = "n²"
        polynomial_latex = "n^2"
    
    return SummationAnalysis(
        worst_summation=summation_text,
        best_summation=summation_text,
        avg_summation=summation_text,
        worst_simplified=simplified,
        best_simplified=simplified,
        avg_simplified=simplified,
        worst_polynomial=polynomial,
        best_polynomial=polynomial,
        avg_polynomial=polynomial,
        worst_summation_latex=summation_latex,
        best_summation_latex=summation_latex,
        avg_summation_latex=summation_latex,
        worst_simplified_latex=simplified_latex,
        best_simplified_latex=simplified_latex,
        avg_simplified_latex=simplified_latex,
        worst_polynomial_latex=polynomial_latex,
        best_polynomial_latex=polynomial_latex,
        avg_polynomial_latex=polynomial_latex,
    )


def _create_cubic_analysis(stmts: List[dict]) -> SummationAnalysis:
    """Genera análisis para O(n³)."""
    # Triple bucle: Σ_{i=1}^{n} Σ_{j=1}^{n} Σ_{k=1}^{n} 1
    summation_text = "Σ_{i=1}^{n} Σ_{j=1}^{n} Σ_{k=1}^{n} 1"
    summation_latex = r"\sum_{i=1}^{n} \sum_{j=1}^{n} \sum_{k=1}^{n} 1"
    
    simplified = "Σ_{i=1}^{n} Σ_{j=1}^{n} n = Σ_{i=1}^{n} n² = n³"
    simplified_latex = r"\sum_{i=1}^{n} \sum_{j=1}^{n} n = \sum_{i=1}^{n} n^2 = n^3"
    
    polynomial = "n³"
    polynomial_latex = "n^3"
    
    return SummationAnalysis(
        worst_summation=summation_text,
        best_summation=summation_text,
        avg_summation=summation_text,
        worst_simplified=simplified,
        best_simplified=simplified,
        avg_simplified=simplified,
        worst_polynomial=polynomial,
        best_polynomial=polynomial,
        avg_polynomial=polynomial,
        worst_summation_latex=summation_latex,
        best_summation_latex=summation_latex,
        avg_summation_latex=summation_latex,
        worst_simplified_latex=simplified_latex,
        best_simplified_latex=simplified_latex,
        avg_simplified_latex=simplified_latex,
        worst_polynomial_latex=polynomial_latex,
        best_polynomial_latex=polynomial_latex,
        avg_polynomial_latex=polynomial_latex,
    )


def _create_polynomial_analysis(depth: int) -> SummationAnalysis:
    """Genera análisis para O(n^depth)."""
    # Generalización para N bucles
    vars_list = ["i", "j", "k", "p", "q"][:depth]
    
    summation_parts = [f"Σ_{{{v}=1}}^{{n}}" for v in vars_list]
    summation_text = " ".join(summation_parts) + " 1"
    
    summation_latex_parts = [f"\\sum_{{{v}=1}}^{{n}}" for v in vars_list]
    summation_latex = " ".join(summation_latex_parts) + " 1"
    
    simplified = f"n^{depth}"
    simplified_latex = f"n^{{{depth}}}"
    
    polynomial = f"n^{depth}"
    polynomial_latex = f"n^{{{depth}}}"
    
    return SummationAnalysis(
        worst_summation=summation_text,
        best_summation=summation_text,
        avg_summation=summation_text,
        worst_simplified=simplified,
        best_simplified=simplified,
        avg_simplified=simplified,
        worst_polynomial=polynomial,
        best_polynomial=polynomial,
        avg_polynomial=polynomial,
        worst_summation_latex=summation_latex,
        best_summation_latex=summation_latex,
        avg_summation_latex=summation_latex,
        worst_simplified_latex=simplified_latex,
        best_simplified_latex=simplified_latex,
        avg_simplified_latex=simplified_latex,
        worst_polynomial_latex=polynomial_latex,
        best_polynomial_latex=polynomial_latex,
        avg_polynomial_latex=polynomial_latex,
    )


def _detect_binary_search_pattern(stmts: List[dict]) -> bool:
    """Detecta si el código contiene un patrón de búsqueda binaria.
    
    Características buscadas:
    - Un while loop
    - Variables left/right o low/high
    - División por 2 del mid point
    - Asignaciones left = mid+1 o right = mid-1
    
    Args:
        stmts: Lista de sentencias a analizar
        
    Returns:
        True si se detecta el patrón
    """
    def _check_binary_search_recursive(statements: List[dict]) -> bool:
        for stmt in statements:
            if not isinstance(stmt, dict):
                continue
            
            if stmt.get("kind") == "while":
                cond = stmt.get("cond", {})
                body = stmt.get("body", [])
                
                # Buscar variables left/right en la condición
                cond_str = str(cond).lower()
                has_binary_vars = any(
                    var in cond_str 
                    for var in ["left", "right", "low", "high", "l", "r"]
                )
                
                if not has_binary_vars:
                    continue
                
                # Buscar división por 2 en el body (mid = (left+right)/2)
                has_division = False
                has_updates = False
                
                for body_stmt in body:
                    if body_stmt.get("kind") == "assign":
                        expr = body_stmt.get("expr", {})
                        expr_str = str(expr)
                        if "/2" in expr_str or "div 2" in expr_str.lower():
                            has_division = True
                        
                        # Buscar left = ... o right = ...
                        tgt = body_stmt.get("target", {})
                        tgt_name = tgt.get("name", "").lower() if isinstance(tgt, dict) else ""
                        if tgt_name in ["left", "right", "l", "r"]:
                            has_updates = True
                    elif body_stmt.get("kind") == "if":
                        # Recursar en ramas del if
                        if _check_binary_search_recursive(body_stmt.get("then_body", [])):
                            return True
                        if _check_binary_search_recursive(body_stmt.get("else_body", [])):
                            return True
                
                if has_division and has_updates:
                    return True
            
            elif stmt.get("kind") == "if":
                if _check_binary_search_recursive(stmt.get("then_body", [])):
                    return True
                if _check_binary_search_recursive(stmt.get("else_body", [])):
                    return True
            elif stmt.get("kind") == "block":
                if _check_binary_search_recursive(stmt.get("stmts", [])):
                    return True
        
        return False
    
    return _check_binary_search_recursive(stmts)


def _create_binary_search_analysis() -> SummationAnalysis:
    """Genera análisis para búsqueda binaria O(log n)."""
    summation_text = "Σ_{i=1}^{log n} 1"
    summation_latex = r"\sum_{i=1}^{\log n} 1"
    
    simplified = "log n"
    simplified_latex = r"\log n"
    
    polynomial = "log n"
    polynomial_latex = r"\log n"
    
    # Para best case (elemento encontrado en primer intento)
    best_polynomial = "1"
    best_polynomial_latex = "1"
    
    # Para promedio (típicamente también log n)
    avg_polynomial = "log n"
    avg_polynomial_latex = r"\log n"
    
    return SummationAnalysis(
        worst_summation=summation_text,
        best_summation="1 (elemento encontrado de inmediato)",
        avg_summation=summation_text,
        worst_simplified=simplified,
        best_simplified="1",
        avg_simplified=simplified,
        worst_polynomial=polynomial,
        best_polynomial=best_polynomial,
        avg_polynomial=avg_polynomial,
        worst_summation_latex=summation_latex,
        best_summation_latex="1",
        avg_summation_latex=summation_latex,
        worst_simplified_latex=simplified_latex,
        best_simplified_latex="1",
        avg_simplified_latex=simplified_latex,
        worst_polynomial_latex=polynomial_latex,
        best_polynomial_latex=best_polynomial_latex,
        avg_polynomial_latex=avg_polynomial_latex,
    )


def analyze_nested_loops(stmts: List[dict]) -> SummationAnalysis:
    """
    Analiza bucles anidados y genera sumatorias CORRECTAS.
    Ahora también detecta patrones de búsqueda binaria.
    """
    # PRIMERO: Detectar si es búsqueda binaria
    if _detect_binary_search_pattern(stmts):
        return _create_binary_search_analysis()
    
    # Detectar estructura de bucles
    loop_depth = _count_loop_depth(stmts)
    outer_loop = _find_outer_loop(stmts)
    
    if not outer_loop or loop_depth == 0:
        # Sin bucles = O(1)
        return _create_constant_analysis()
    
    if loop_depth == 1:
        # Un solo bucle = O(n)
        return _create_linear_analysis(outer_loop)
    
    elif loop_depth == 2:
        # Dos bucles anidados = O(n²)
        inner_loop = _find_inner_loop(outer_loop)
        return _create_quadratic_analysis(outer_loop, inner_loop)
    
    elif loop_depth == 3:
        # Tres bucles anidados = O(n³)
        return _create_cubic_analysis(stmts)
    
    else:
        # N bucles anidados = O(n^N)
        return _create_polynomial_analysis(loop_depth)


def format_summation_equation(case: str, analysis: SummationAnalysis) -> Dict[str, str]:
    """
    Formatea una ecuación completa de sumatoria para mostrar en UI,
    utilizando las propiedades de LaTeX del análisis.
    """
    
    # Seleccionar las propiedades correctas según el caso
    if case == "worst":
        summation = analysis.worst_summation_latex
        summation_text = analysis.worst_summation
        simplified = analysis.worst_simplified_latex
        simplified_text = analysis.worst_simplified
        polynomial = analysis.worst_polynomial_latex
        polynomial_text = analysis.worst_polynomial
    elif case == "best":
        summation = analysis.best_summation_latex
        summation_text = analysis.best_summation
        simplified = analysis.best_simplified_latex
        simplified_text = analysis.best_simplified
        polynomial = analysis.best_polynomial_latex
        polynomial_text = analysis.best_polynomial
    elif case == "avg":
        summation = analysis.avg_summation_latex or analysis.worst_summation_latex
        summation_text = analysis.avg_summation or analysis.worst_summation
        simplified = analysis.avg_simplified_latex or analysis.worst_simplified_latex
        simplified_text = analysis.avg_simplified or analysis.worst_simplified
        polynomial = analysis.avg_polynomial_latex or analysis.worst_polynomial_latex
        polynomial_text = analysis.avg_polynomial or analysis.worst_polynomial
    else:
        return {"latex": "", "text": "Análisis no disponible"}

    case_label = {
        "worst": "T_{worst}(n)",
        "best": "T_{best}(n)",
        "avg": "T_{avg}(n)"
    }.get(case, "T(n)")

    # 1. Formato LaTeX
    # Usamos \cdot y \qquad para espaciar las líneas.
    latex_lines = f"""
{case_label} = c \\cdot ({summation}) + d \\newline
\\qquad \\quad = c \\cdot ({simplified}) + d \\newline
\\qquad \\quad = {polynomial} \\cdot c + d
"""

    # 2. Formato Texto Plano (para logs o fallback)
    # Usamos el operador Sigma (Σ)
    text_lines = f"""
{case_label} = c * ({summation_text}) + d
         = c * ({simplified_text}) + d
         = {polynomial_text} * c + d
"""
    
    return {
        "latex": latex_lines.strip(),
        "text": text_lines.strip()
    }


def generate_summations_from_expressions(worst_expr: str, best_expr: str, avg_expr: str = None) -> Dict[str, Dict[str, str]]:
    """
    Genera sumatorias dinámicamente basadas en las expresiones de complejidad reales.
    
    Args:
        worst_expr: Expresión de peor caso (ej. "n", "log n")
        best_expr: Expresión de mejor caso (ej. "1", "log n")
        avg_expr: Expresión de caso promedio (ej. "n", None)
    
    Returns:
        Dict con sumatorias formateadas para worst, best, avg
    """
    
    # Helper para crear sumatoria de un tipo
    def create_case_summation(expr: str, case_name: str) -> Dict[str, str]:
        case_label = {
            "worst": "T_{worst}(n)",
            "best": "T_{best}(n)",
            "avg": "T_{avg}(n)"
        }[case_name]
        
        # Determinar la sumatoria basada en la expresión
        if expr in ("1", "constante", "O(1)"):
            sum_text = "1"
            sum_latex = "1"
            simplified_text = "1"
            simplified_latex = "1"
            poly_text = "1"
            poly_latex = "1"
        elif expr in ("n", "O(n)", "lineal"):
            sum_text = "Σ_{i=1}^{n} 1"
            sum_latex = r"\sum_{i=1}^{n} 1"
            simplified_text = "n"
            simplified_latex = "n"
            poly_text = "n"
            poly_latex = "n"
        elif "log" in expr.lower():
            sum_text = "Σ_{i=1}^{log n} 1"
            sum_latex = r"\sum_{i=1}^{\log n} 1"
            simplified_text = "log n"
            simplified_latex = r"\log n"
            poly_text = "log n"
            poly_latex = r"\log n"
        elif "²" in expr or "^2" in expr or "n²" in expr:
            sum_text = "Σ_{i=1}^{n} Σ_{j=1}^{n} 1"
            sum_latex = r"\sum_{i=1}^{n} \sum_{j=1}^{n} 1"
            simplified_text = "Σ_{i=1}^{n} n = n²"
            simplified_latex = r"\sum_{i=1}^{n} n = n^2"
            poly_text = "n²"
            poly_latex = "n^2"
        elif "³" in expr or "^3" in expr or "n³" in expr or "n^3" in expr:
            sum_text = "Σ_{i=1}^{n} Σ_{j=1}^{n} Σ_{k=1}^{n} 1"
            sum_latex = r"\sum_{i=1}^{n} \sum_{j=1}^{n} \sum_{k=1}^{n} 1"
            simplified_text = "Σ_{i=1}^{n} Σ_{j=1}^{n} n = Σ_{i=1}^{n} n² = n³"
            simplified_latex = r"\sum_{i=1}^{n} \sum_{j=1}^{n} n = \sum_{i=1}^{n} n^2 = n^3"
            poly_text = "n³"
            poly_latex = "n^3"
        else:
            # Fallback
            sum_text = expr
            sum_latex = expr
            simplified_text = expr
            simplified_latex = expr
            poly_text = expr
            poly_latex = expr
        
        latex = f"""
{case_label} = c \\cdot ({sum_latex}) + d \\newline
\\qquad \\quad = c \\cdot ({simplified_latex}) + d \\newline
\\qquad \\quad = {poly_latex} \\cdot c + d
"""
        
        text = f"""
{case_label} = c * ({sum_text}) + d
         = c * ({simplified_text}) + d
         = {poly_text} * c + d
"""
        
        return {"latex": latex.strip(), "text": text.strip()}
    
    result = {
        "worst": create_case_summation(worst_expr, "worst"),
        "best": create_case_summation(best_expr, "best"),
    }
    
    if avg_expr:
        result["avg"] = create_case_summation(avg_expr, "avg")
    
    return result
