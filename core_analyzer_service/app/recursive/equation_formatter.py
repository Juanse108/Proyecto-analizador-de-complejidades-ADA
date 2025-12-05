"""Formato de ecuaciones de recurrencia legibles.

Convierte los parámetros de RecurrenceRelation en ecuaciones matemáticas
claras y correctas para mostrar en la UI.
"""

from ..domain.recurrence import RecurrenceRelation
from ..domain.expr import Expr, Const, Sym, Pow, Log, Mul, Add

def format_f_expr(f: Expr) -> str:
    """Convierte una expresión simbólica a string matemático legible.
    
    Args:
        f: Expresión a formatear
        
    Returns:
        String con la representación matemática
    
    Ejemplos:
        - Const(1) → "c"
        - Sym("n") → "n"
        - Sym("2^n") → "2^n"
        - Mul(Const(2), Sym("n")) → "2n"
        - Pow(Sym("n"), 2) → "n²"
    """
    if f is None:
        return "c"
    
    if isinstance(f, Const):
        if f.k == 1:
            return "c"
        return f"c·{f.k}"
    
    if isinstance(f, Sym):
        if "^" in f.name or f.name in ["2^n", "φ^n", "log"]:
            return f.name
        return f"c·{f.name}"
    
    if isinstance(f, Pow):
        base = f.base.name if isinstance(f.base, Sym) else "n"
        if f.exp == 2:
            return f"c·{base}²"
        elif f.exp == 3:
            return f"c·{base}³"
        else:
            return f"c·{base}^{f.exp}"
    
    if isinstance(f, Log):
        arg = f.arg.name if isinstance(f.arg, Sym) else "n"
        if f.base == 2:
            return f"c·log₂({arg})"
        else:
            return f"c·log_{f.base}({arg})"
    
    if isinstance(f, Mul):
        coef = 1
        terms = []
        for factor in f.factors:
            if isinstance(factor, Const):
                coef *= factor.k
            else:
                terms.append(format_f_expr(factor))
        
        if coef == 1:
            return "·".join(terms) if terms else "c"
        else:
            return f"{coef}·{'·'.join(terms)}" if terms else f"c·{coef}"
    
    if isinstance(f, Add):
        parts = [format_f_expr(t) for t in f.terms]
        return f"({' + '.join(parts)})"
    
    s = str(f)
    s = s.replace("Sym(name='", "").replace("')", "")
    s = s.replace("Const(k=", "").replace(")", "")
    return s if s else "f(n)"

def format_recurrence_equation(rec: RecurrenceRelation) -> str:
    """
    Genera la ecuación de recurrencia COMPLETA como string.
    
    Ejemplos de salida:
    
    1. Merge Sort:
       T(n) = 2·T(n/2) + c·n,  n > 1
       T(1) = d
    
    2. Binary Search:
       T(n) = T(n/2) + c,  n > 1
       T(1) = d
    
    3. Fibonacci:
       T(n) = T(n-1) + T(n-2) + c,  n ≥ 2
       T(0) = d₀
       T(1) = d₁
    
    4. Factorial:
       T(n) = T(n-1) + c,  n > 1
       T(1) = d
    
    5. QuickSort (peor caso):
       T(n) = T(n-1) + c·n,  n > 1
       T(1) = d
    """
    lines = []
    
    # Formatear f(n)
    f_str = format_f_expr(rec.f_expr)
    
    # --- CASO 1: Divide & Conquer (a·T(n/b) + f(n)) ---
    if rec.b > 1 and rec.c == 0 and rec.d == 0:
        # T(n) = a·T(n/b) + f(n)
        if rec.a == 1:
            term = f"T(n/{rec.b})"
        else:
            term = f"{rec.a}·T(n/{rec.b})"
        
        lines.append(f"T(n) = {term} + {f_str},  n > 1")
        lines.append("T(1) = d")
        
        return "\n".join(lines)
    
    # --- CASO 2: Recursión Lineal Simple (c·T(n-1) + f(n)) ---
    if rec.b == 1 and rec.c == 0 and rec.d == 0:
        # T(n) = a·T(n-1) + f(n)
        if rec.a == 1:
            term = "T(n-1)"
        else:
            term = f"{rec.a}·T(n-1)"
        
        lines.append(f"T(n) = {term} + {f_str},  n > 1")
        lines.append("T(1) = d")
        
        return "\n".join(lines)
    
    # --- CASO 3: Recursión Lineal de Orden 2 (Fibonacci-like) ---
    if rec.b == 1 and rec.d > 0:
        # T(n) = a·T(n-1) + c·T(n-2) + f(n)
        # NOTA: Para Fibonacci simple, a=1 y c=1 (un término de cada uno)
        terms = []
        
        # Término T(n-1)
        if rec.a > 0:
            if rec.a == 1:
                terms.append("T(n-1)")
            else:
                terms.append(f"{rec.a}·T(n-1)")
        
        # Término T(n-2)
        if rec.c > 0:
            if rec.c == 1:
                terms.append("T(n-2)")
            else:
                terms.append(f"{rec.c}·T(n-2)")
        
        equation = " + ".join(terms)
        if f_str != "c" or rec.f_expr is not None:
            equation += f" + {f_str}"
        
        lines.append(f"T(n) = {equation},  n ≥ 2")
        lines.append("T(0) = d₀")
        lines.append("T(1) = d₁")
        
        return "\n".join(lines)
    
    # --- FALLBACK: Forma genérica ---
    lines.append(f"T(n) = {rec.a}·T(n-1) + {f_str},  n > 1")
    lines.append("T(1) = d")
    
    return "\n".join(lines)


def get_recurrence_description(rec: RecurrenceRelation) -> str:
    """
    Genera una descripción breve del tipo de recurrencia.
    
    Ejemplos:
    - "Divide y vencerás balanceado (2 subproblemas de tamaño n/2)"
    - "Recursión lineal simple (orden 1)"
    - "Recursión lineal de orden 2 (tipo Fibonacci)"
    """
    if rec.b > 1 and rec.c == 0:
        if rec.a == 2 and rec.b == 2:
            return "Divide y vencerás balanceado (2 subproblemas de tamaño n/2)"
        elif rec.a == 1:
            return f"División recursiva por {rec.b} (un subproblema)"
        else:
            return f"Divide y vencerás ({rec.a} subproblemas de tamaño n/{rec.b})"
    
    if rec.b == 1:
        if rec.d > 0:
            return "Recursión lineal de orden 2 (tipo Fibonacci)"
        elif rec.a == 1:
            return "Recursión lineal simple (orden 1)"
        else:
            return f"Recursión lineal con factor {rec.a}"
    
    return "Recurrencia compleja"