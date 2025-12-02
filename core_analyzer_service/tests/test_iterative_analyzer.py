"""
extended_test_suite.py - Suite completa de 20 casos de prueba
=============================================================

Cubre todas las complejidades comunes:
- O(1): constante
- O(log n): logarítmica
- O(n): lineal
- O(n log n): lineal-logarítmica
- O(n²): cuadrática
- O(n³): cúbica
- Casos especiales: búsqueda binaria, triangular, etc.
"""

import httpx
import json
from typing import Dict, Any

PARSER_URL = "http://localhost:8001"
ANALYZER_URL = "http://localhost:8002"

# ============================================================================
# SUITE DE PRUEBAS EXTENDIDA
# ============================================================================

EXTENDED_TEST_CASES = [
    # ========== O(1) - CONSTANTE ==========
    {
        "name": "O(1) - Asignaciones simples",
        "pseudocode": "begin\n  x <- 5\n  y <- x + 3\n  z <- y * 2\nend",
        "expected": {"big_o": "1", "big_omega": "1", "theta": "1"},
        "category": "constante"
    },
    {
        "name": "O(1) - Condicional sin bucles",
        "pseudocode": "begin\n  if (x > 0) then\n  begin\n    y <- x + 1\n  end else\n  begin\n    y <- x - 1\n  end\nend",
        "expected": {"big_o": "1", "big_omega": "1", "theta": "1"},
        "category": "constante"
    },
    {
        "name": "O(1) - Operaciones aritméticas",
        "pseudocode": "begin\n  a <- 10\n  b <- 20\n  c <- a + b\n  d <- c * 2\n  e <- d / 4\nend",
        "expected": {"big_o": "1", "big_omega": "1", "theta": "1"},
        "category": "constante"
    },

    # ========== O(log n) - LOGARÍTMICA ==========
    {
        "name": "O(log n) - Halving (división por 2)",
        "pseudocode": "begin\n  i <- n\n  while (i > 1) do\n  begin\n    i <- i / 2\n  end\nend",
        "expected": {"big_o": "log n", "big_omega": "log n", "theta": "log n"},
        "category": "logaritmica"
    },
    {
        "name": "O(log n) - Doubling (multiplicación por 2)",
        "pseudocode": "begin\n  i <- 1\n  while (i < n) do\n  begin\n    i <- i * 2\n  end\nend",
        "expected": {"big_o": "log n", "big_omega": "log n", "theta": "log n"},
        "category": "logaritmica"
    },
    {
        "name": "O(log n) - División por 3",
        "pseudocode": "begin\n  i <- n\n  while (i > 1) do\n  begin\n    i <- i / 3\n  end\nend",
        "expected": {"big_o": "log n", "big_omega": "log n", "theta": "log n"},
        "category": "logaritmica"
    },

    # ========== O(n) - LINEAL ==========
    {
        "name": "O(n) - Bucle simple for",
        "pseudocode": "begin\n  s <- 0\n  for i <- 1 to n do\n  begin\n    s <- s + i\n  end\nend",
        "expected": {"big_o": "n", "big_omega": "n", "theta": "n"},
        "category": "lineal"
    },
    {
        "name": "O(n) - While con incremento",
        "pseudocode": "begin\n  i <- 1\n  while (i < n) do\n  begin\n    i <- i + 1\n  end\nend",
        "expected": {"big_o": "n", "big_omega": "n", "theta": "n"},
        "category": "lineal"
    },
    {
        "name": "O(n) - Repeat-until con decremento",
        "pseudocode": "begin\n  x <- n\n  repeat\n    x <- x - 1\n  until (x = 0)\nend",
        "expected": {"big_o": "n", "big_omega": "n", "theta": "n"},
        "category": "lineal"
    },
    {
        "name": "O(n) - Dos bucles secuenciales",
        "pseudocode": "begin\n  for i <- 1 to n do\n  begin\n    x <- x + 1\n  end\n  for j <- 1 to n do\n  begin\n    y <- y + 1\n  end\nend",
        "expected": {"big_o": "n", "big_omega": "n", "theta": "n"},
        "category": "lineal"
    },

    # ========== O(n log n) - LINEAL-LOGARÍTMICA ==========
    {
        "name": "O(n log n) - Bucle externo lineal, interno logarítmico",
        "pseudocode": "begin\n  for i <- 1 to n do\n  begin\n    j <- n\n    while (j > 1) do\n    begin\n      j <- j / 2\n    end\n  end\nend",
        "expected": {"big_o": "n log n", "big_omega": "n log n", "theta": "n log n"},
        "category": "lineal_logaritmica"
    },
    {
        "name": "O(n log n) - Bucle logarítmico externo, lineal interno",
        "pseudocode": "begin\n  i <- n\n  while (i > 1) do\n  begin\n    for j <- 1 to n do\n    begin\n      x <- x + 1\n    end\n    i <- i / 2\n  end\nend",
        "expected": {"big_o": "n log n", "big_omega": "n log n", "theta": "n log n"},
        "category": "lineal_logaritmica"
    },

    # ========== O(n²) - CUADRÁTICA ==========
    {
        "name": "O(n²) - Doble bucle completo",
        "pseudocode": "begin\n  for i <- 1 to n do\n  begin\n    for j <- 1 to n do\n    begin\n      x <- 1\n    end\n  end\nend",
        "expected": {"big_o": "n^2", "big_omega": "n^2", "theta": "n^2"},
        "category": "cuadratica"
    },
    {
        "name": "O(n²) - While anidado (ambos lineales)",
        "pseudocode": "begin\n  i <- 1\n  while (i < n) do\n  begin\n    j <- 1\n    while (j < n) do\n    begin\n      x <- x + 1\n      j <- j + 1\n    end\n    i <- i + 1\n  end\nend",
        "expected": {"big_o": "n^2", "big_omega": "n^2", "theta": "n^2"},
        "category": "cuadratica"
    },
    {
        "name": "O(n²) - Tres bucles secuenciales con uno cuadrático",
        "pseudocode": "begin\n  for i <- 1 to n do\n  begin\n    x <- x + 1\n  end\n  for i <- 1 to n do\n  begin\n    for j <- 1 to n do\n    begin\n      y <- y + 1\n    end\n  end\n  for i <- 1 to n do\n  begin\n    z <- z + 1\n  end\nend",
        "expected": {"big_o": "n^2", "big_omega": "n^2", "theta": "n^2"},
        "category": "cuadratica"
    },

    # ========== O(n³) - CÚBICA ==========
    {
        "name": "O(n³) - Triple bucle",
        "pseudocode": "begin\n  for i <- 1 to n do\n  begin\n    for j <- 1 to n do\n    begin\n      for k <- 1 to n do\n      begin\n        sum <- sum + 1\n      end\n    end\n  end\nend",
        "expected": {"big_o": "n^3", "big_omega": "n^3", "theta": "n^3"},
        "category": "cubica"
    },

    # ========== CASOS ESPECIALES ==========
    {
        "name": "O(n) - Bucle con step de 2",
        "pseudocode": "begin\n  for i <- 1 to n step 2 do\n  begin\n    x <- x + 1\n  end\nend",
        "expected": {"big_o": "n", "big_omega": "n", "theta": "n"},
        "category": "lineal"
    },
    {
        "name": "O(n²) - Matriz cuadrada",
        "pseudocode": "begin\n  for i <- 1 to n do\n  begin\n    for j <- 1 to n do\n    begin\n      M[i][j] <- i * j\n    end\n  end\nend",
        "expected": {"big_o": "n^2", "big_omega": "n^2", "theta": "n^2"},
        "category": "cuadratica"
    },
    {
        "name": "O(n) - Condicional dentro de bucle",
        "pseudocode": "begin\n  for i <- 1 to n do\n  begin\n    if (i > 5) then\n    begin\n      x <- x + i\n    end else\n    begin\n      x <- x - i\n    end\n  end\nend",
        "expected": {"big_o": "n", "big_omega": "n", "theta": "n"},
        "category": "lineal"
    },
    {
        "name": "O(1) - Múltiples condicionales anidados",
        "pseudocode": "begin\n  if (x > 0) then\n  begin\n    if (y > 0) then\n    begin\n      z <- x + y\n    end else\n    begin\n      z <- x - y\n    end\n  end else\n  begin\n    z <- 0\n  end\nend",
        "expected": {"big_o": "1", "big_omega": "1", "theta": "1"},
        "category": "constante"
    },
]


# ============================================================================
# FUNCIONES DE PRUEBA
# ============================================================================

def parse_code(code: str) -> Dict[str, Any]:
    """Llama al parser service."""
    response = httpx.post(f"{PARSER_URL}/parse", json={"code": code}, timeout=10.0)
    response.raise_for_status()
    return response.json()


def analyze_ast(ast: Dict[str, Any], detail: str = "program") -> Dict[str, Any]:
    """Llama al analyzer service."""
    response = httpx.post(
        f"{ANALYZER_URL}/analyze-ast",
        json={"ast": ast, "objective": "all", "detail": detail},
        timeout=10.0
    )
    response.raise_for_status()
    return response.json()


def run_test(test_case: Dict[str, Any], verbose: bool = False) -> Dict[str, Any]:
    """Ejecuta un caso de prueba."""
    name = test_case['name']
    category = test_case.get('category', 'general')

    if verbose:
        print(f"\n{'='*70}")
        print(f"TEST: {name}")
        print(f"Categoría: {category}")
        print(f"{'='*70}")

    try:
        # Parse
        parse_result = parse_code(test_case["pseudocode"])
        if not parse_result.get("ok"):
            return {
                "name": name,
                "category": category,
                "status": "parse_error",
                "errors": parse_result.get("errors")
            }

        # Analyze
        analysis = analyze_ast(parse_result["ast"], detail="program")

        # Compare
        expected = test_case.get("expected", {})
        matches = (
            analysis["big_o"] == expected.get("big_o", "")
            and analysis["big_omega"] == expected.get("big_omega", "")
        )

        result = {
            "name": name,
            "category": category,
            "status": "success" if matches else "wrong_result",
            "expected": expected,
            "actual": {
                "big_o": analysis["big_o"],
                "big_omega": analysis["big_omega"],
                "theta": analysis.get("theta")
            }
        }

        if verbose:
            if matches:
                print(f"✅ CORRECTO: O({expected['big_o']}), Ω({expected['big_omega']})")
            else:
                print(f"❌ INCORRECTO:")
                print(f"   Esperado: O({expected['big_o']}), Ω({expected['big_omega']})")
                print(f"   Obtenido: O({analysis['big_o']}), Ω({analysis['big_omega']})")

        return result

    except Exception as e:
        return {
            "name": name,
            "category": category,
            "status": "unexpected_error",
            "error": str(e)
        }


def main():
    """Ejecuta toda la suite."""
    print("\n🚀 SUITE EXTENDIDA DE PRUEBAS - 20 CASOS")
    print("="*70)

    results = []
    by_category = {}

    # Ejecutar todos los tests
    for i, test_case in enumerate(EXTENDED_TEST_CASES, 1):
        print(f"\n[{i}/20] {test_case['name']}", end=" ... ")
        result = run_test(test_case, verbose=False)
        results.append(result)

        # Agrupar por categoría
        cat = result['category']
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(result)

        # Mostrar resultado inline
        if result['status'] == 'success':
            print("✅")
        else:
            print(f"❌ ({result['status']})")

    # Resumen por categoría
    print(f"\n\n{'='*70}")
    print("📊 RESUMEN POR CATEGORÍA")
    print(f"{'='*70}")

    for category in sorted(by_category.keys()):
        tests = by_category[category]
        success = sum(1 for t in tests if t['status'] == 'success')
        total = len(tests)
        pct = (success / total * 100) if total > 0 else 0

        status_icon = "✅" if success == total else "⚠️"
        print(f"\n{status_icon} {category.upper()}: {success}/{total} ({pct:.0f}%)")

        for test in tests:
            icon = "✅" if test['status'] == 'success' else "❌"
            print(f"   {icon} {test['name']}")
            if test['status'] != 'success':
                if 'expected' in test and 'actual' in test:
                    print(f"      Esperado: O({test['expected']['big_o']})")
                    print(f"      Obtenido: O({test['actual']['big_o']})")

    # Resumen global
    print(f"\n\n{'='*70}")
    print("🎯 RESUMEN GLOBAL")
    print(f"{'='*70}")

    total_success = sum(1 for r in results if r['status'] == 'success')
    total_tests = len(results)
    success_rate = (total_success / total_tests * 100) if total_tests > 0 else 0

    print(f"\n✅ Tests exitosos: {total_success}/{total_tests} ({success_rate:.1f}%)")

    if total_success < total_tests:
        print(f"\n❌ Tests fallidos:")
        for r in results:
            if r['status'] != 'success':
                print(f"   - {r['name']} ({r['status']})")

    print("\n" + "="*70)

    return results


if __name__ == "__main__":
    results = main()