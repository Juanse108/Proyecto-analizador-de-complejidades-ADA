# core_analyzer_service/app/domain/complexity_normalizer.py
"""
complexity_normalizer.py - Normalización de strings de complejidad
==================================================================

Resuelve el problema de comparación entre diferentes formatos:
- "1" vs "O(1)"
- "n" vs "O(n)"
- "n^2" vs "O(n²)"
- "log n" vs "O(log n)"

Esto previene falsos negativos en la comparación Analyzer vs LLM.

UBICACIÓN: core_analyzer_service/app/domain/complexity_normalizer.py
"""

import re
from typing import Optional


def normalize_complexity(complexity_str: Optional[str]) -> str:
    """
    Normaliza un string de complejidad a formato estándar O(...).
    
    Casos manejados:
    - "1", "c", "constant", "constante" → "O(1)"
    - "n", "1n" → "O(n)"
    - "n^2", "n²", "n*n" → "O(n²)"
    - "n^3", "n³" → "O(n³)"
    - "log n", "log(n)", "logn" → "O(log n)"
    - "n log n", "nlogn", "n*log(n)" → "O(n log n)"
    - "2^n", "2**n" → "O(2^n)"
    - Ya normalizados: "O(n)", "O(n²)" → sin cambios
    
    Args:
        complexity_str: String de complejidad en cualquier formato
        
    Returns:
        String normalizado en formato "O(...)"
        
    Examples:
        >>> normalize_complexity("1")
        'O(1)'
        >>> normalize_complexity("n²")
        'O(n²)'
        >>> normalize_complexity("O(n)")
        'O(n)'
    """
    if not complexity_str:
        return "O(?)"
    
    # Limpiar espacios extra
    s = complexity_str.strip()
    
    # Si ya está en formato O(...), dejarlo como está
    if s.startswith("O(") or s.startswith("Ω(") or s.startswith("Θ("):
        return s
    
    # Convertir a minúsculas para comparación (pero preservar en resultado)
    s_lower = s.lower()
    
    # === CONSTANTE ===
    if s_lower in ("1", "c", "constant", "constante", "o(1)"):
        return "O(1)"
    
    # === LOGARÍTMICO ===
    # Variantes: "log n", "log(n)", "logn", "lg n"
    if re.match(r"^(log|lg)\s*\(?\s*n\s*\)?$", s_lower):
        return "O(log n)"
    
    # === LINEAL ===
    # Variantes: "n", "1n", "1*n"
    if re.match(r"^(1\s*\*?\s*)?n$", s_lower):
        return "O(n)"
    
    # === N LOG N ===
    # Variantes: "n log n", "nlogn", "n*log(n)", "n log(n)"
    if re.search(r"n\s*\*?\s*(log|lg)\s*\(?\s*n\s*\)?", s_lower):
        return "O(n log n)"
    
    # === CUADRÁTICO ===
    # Variantes: "n^2", "n²", "n*n", "n**2"
    if re.match(r"^n\s*(\^|(\*\*)|\*)\s*2$", s_lower) or "n²" in s:
        return "O(n²)"
    
    # === CÚBICO ===
    # Variantes: "n^3", "n³", "n**3"
    if re.match(r"^n\s*(\^|(\*\*))\s*3$", s_lower) or "n³" in s:
        return "O(n³)"
    
    # === EXPONENCIAL ===
    # Variantes: "2^n", "2**n"
    if re.match(r"^2\s*(\^|(\*\*))\s*n$", s_lower):
        return "O(2^n)"
    
    # === POLINOMIOS GENERALES ===
    # "n^4", "n^5", etc.
    match = re.match(r"^n\s*(\^|(\*\*))\s*(\d+)$", s_lower)
    if match:
        exp = match.group(3)
        return f"O(n^{exp})"
    
    # === FALLBACK ===
    # Si no reconocimos el patrón, envolver en O(...)
    return f"O({s})"


def complexities_match(complexity1: Optional[str], complexity2: Optional[str]) -> bool:
    """
    Compara dos strings de complejidad después de normalizarlos.
    
    Resuelve el bug donde "1" != "O(1)" causaba falsos negativos.
    
    Args:
        complexity1: Primera complejidad (ej. del Analyzer)
        complexity2: Segunda complejidad (ej. del LLM)
        
    Returns:
        True si son equivalentes después de normalizar
        
    Examples:
        >>> complexities_match("1", "O(1)")
        True
        >>> complexities_match("n²", "O(n^2)")
        True
        >>> complexities_match("n", "O(n²)")
        False
    """
    norm1 = normalize_complexity(complexity1)
    norm2 = normalize_complexity(complexity2)
    
    # Normalizar también los caracteres especiales
    norm1 = _normalize_special_chars(norm1)
    norm2 = _normalize_special_chars(norm2)
    
    return norm1 == norm2


def _normalize_special_chars(s: str) -> str:
    """
    Normaliza caracteres especiales para comparación.
    
    - n² → n^2
    - n³ → n^3
    - Eliminar espacios dentro de O(...)
    """
    # Normalizar superíndices Unicode
    s = s.replace("²", "^2")
    s = s.replace("³", "^3")
    s = s.replace("⁴", "^4")
    
    # Eliminar espacios dentro de O(...)
    # "O( n )" → "O(n)"
    s = re.sub(r"O\(\s*([^)]+?)\s*\)", lambda m: f"O({m.group(1).replace(' ', '')})", s)
    
    return s


def extract_degree(complexity_str: Optional[str]) -> tuple[int, int]:
    """
    Extrae el grado polinómico y logarítmico de una complejidad.
    
    Útil para comparaciones de dominancia.
    
    Args:
        complexity_str: String de complejidad
        
    Returns:
        (grado_polinómico, grado_logarítmico)
        
    Examples:
        >>> extract_degree("O(n²)")
        (2, 0)
        >>> extract_degree("O(n log n)")
        (1, 1)
        >>> extract_degree("O(1)")
        (0, 0)
    """
    if not complexity_str:
        return (0, 0)
    
    s = normalize_complexity(complexity_str).lower()
    
    # Constante
    if "o(1)" in s:
        return (0, 0)
    
    # Log n puro
    if s == "o(logn)" or s == "o(log n)":
        return (0, 1)
    
    # n log n
    if "nlogn" in s.replace(" ", "") or "n log n" in s:
        return (1, 1)
    
    # Polinomios puros
    match = re.search(r"n\^(\d+)", s)
    if match:
        return (int(match.group(1)), 0)
    
    if "n²" in s or "n^2" in s:
        return (2, 0)
    
    if "n³" in s or "n^3" in s:
        return (3, 0)
    
    if re.search(r"\bn\b", s):
        return (1, 0)
    
    # Exponencial (tratar como grado muy alto)
    if "2^n" in s:
        return (999, 0)
    
    return (0, 0)


# === TESTS UNITARIOS (ejecutar con pytest) ===

def test_normalize_complexity():
    """Tests de normalización básica."""
    assert normalize_complexity("1") == "O(1)"
    assert normalize_complexity("n") == "O(n)"
    assert normalize_complexity("n²") == "O(n²)"
    assert normalize_complexity("n^2") == "O(n²)"
    assert normalize_complexity("log n") == "O(log n)"
    assert normalize_complexity("n log n") == "O(n log n)"
    assert normalize_complexity("O(n)") == "O(n)"  # Ya normalizado
    print("✅ test_normalize_complexity passed")


def test_complexities_match():
    """Tests de comparación."""
    assert complexities_match("1", "O(1)") == True
    assert complexities_match("n", "O(n)") == True
    assert complexities_match("n²", "O(n^2)") == True
    assert complexities_match("log n", "O(log n)") == True
    assert complexities_match("n", "O(n²)") == False
    assert complexities_match("1", "O(n)") == False
    print("✅ test_complexities_match passed")


def test_extract_degree():
    """Tests de extracción de grado."""
    assert extract_degree("O(1)") == (0, 0)
    assert extract_degree("O(n)") == (1, 0)
    assert extract_degree("O(n²)") == (2, 0)
    assert extract_degree("O(n^3)") == (3, 0)
    assert extract_degree("O(log n)") == (0, 1)
    assert extract_degree("O(n log n)") == (1, 1)
    print("✅ test_extract_degree passed")


if __name__ == "__main__":
    # Ejecutar tests
    test_normalize_complexity()
    test_complexities_match()
    test_extract_degree()
    print("\n🎉 Todos los tests pasaron correctamente")