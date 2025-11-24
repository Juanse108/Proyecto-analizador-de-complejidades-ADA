# core_analyzer_service/tests/test_recursive_analyzer.py
"""
Suite de pruebas para algoritmos recursivos
"""

import httpx
from typing import Dict, Any

PARSER_URL = "http://localhost:8001"
ANALYZER_URL = "http://localhost:8002"


# ============================================================================
# CASOS DE PRUEBA RECURSIVOS
# ============================================================================

RECURSIVE_TEST_CASES = [
    # ========== RECURSIÓN LINEAL ==========
    {
        "name": "Factorial recursivo",
        "pseudocode": "FACTORIAL(n)\nbegin\n  if (n <= 1) then\n  begin\n    return 1\n  end else\n  begin\n    return n * FACTORIAL(n - 1)\n  end\nend",
        "expected": {"big_o": "n", "big_omega": "n", "theta": "n"},
        "recurrence": "T(n) = T(n-1) + O(1)",
        "category": "linear",
    },

    # ========== RECURSIÓN LOGARÍTMICA ==========
    {
        "name": "Búsqueda binaria recursiva",
        "pseudocode": "BINARY_SEARCH(A[1..n], x, inicio, fin)\nbegin\n  if (inicio > fin) then\n  begin\n    return -1\n  end else\n  begin\n    medio <- (inicio + fin) div 2\n    if (A[medio] = x) then\n    begin\n      return medio\n    end else\n    begin\n      if (A[medio] < x) then\n      begin\n        return BINARY_SEARCH(A, x, medio + 1, fin)\n      end else\n      begin\n        return BINARY_SEARCH(A, x, inicio, medio - 1)\n      end\n    end\n  end\nend",
        "expected": {"big_o": "log n", "big_omega": "log n", "theta": "log n"},
        "recurrence": "T(n) = T(n/2) + O(1)",
        "category": "logarithmic",
    },

    # ========== DIVIDE Y CONQUISTA ==========
    {
        "name": "Merge Sort",
        "pseudocode": "MERGE_SORT(A[1..n], inicio, fin)\nbegin\n  if (inicio < fin) then\n  begin\n    medio <- (inicio + fin) div 2\n    CALL MERGE_SORT(A, inicio, medio)\n    CALL MERGE_SORT(A, medio + 1, fin)\n    CALL MERGE(A, inicio, medio, fin)\n  end else\n  begin\n    medio <- medio\n  end\nend",
        "expected": {"big_o": "n log n", "big_omega": "n log n", "theta": "n log n"},
        "recurrence": "T(n) = 2T(n/2) + O(n)",
        "category": "divide_conquer",
    },

    # ========== RECURSIÓN EXPONENCIAL ==========
    {
        "name": "Fibonacci ingenuo",
        "pseudocode": "FIBONACCI(n)\nbegin\n  if (n <= 1) then\n  begin\n    return n\n  end else\n  begin\n    return FIBONACCI(n - 1) + FIBONACCI(n - 2)\n  end\nend",
        "expected": {"big_o": "2^n", "big_omega": "2^n", "theta": "2^n"},
        "recurrence": "T(n) = T(n-1) + T(n-2) + O(1)",
        "category": "exponential",
    },

    # ========== DIVISIÓN POR 3 ==========
    {
        "name": "Búsqueda ternaria",
        "pseudocode": "TERNARY_SEARCH(A[1..n], x, inicio, fin)\nbegin\n  if (inicio > fin) then\n  begin\n    return -1\n  end else\n  begin\n    tercio <- (fin - inicio) div 3\n    mid1 <- inicio + tercio\n    mid2 <- fin - tercio\n    if (A[mid1] = x) then\n    begin\n      return mid1\n    end else\n    begin\n      if (A[mid2] = x) then\n      begin\n        return mid2\n      end else\n      begin\n        if (x < A[mid1]) then\n        begin\n          return TERNARY_SEARCH(A, x, inicio, mid1 - 1)\n        end else\n        begin\n          return TERNARY_SEARCH(A, x, mid1 + 1, fin)\n        end\n      end\n    end\n  end\nend",
        "expected": {"big_o": "log n", "big_omega": "log n", "theta": "log n"},
        "recurrence": "T(n) = T(n/3) + O(1)",
        "category": "logarithmic",
    },
]


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def parse_code(code: str) -> Dict[str, Any]:
    """Llama al parser service."""
    response = httpx.post(f"{PARSER_URL}/parse", json={"code": code}, timeout=10.0)
    response.raise_for_status()
    return response.json()


def analyze_ast(ast: Dict[str, Any]) -> Dict[str, Any]:
    """Llama al analyzer service."""
    response = httpx.post(
        f"{ANALYZER_URL}/analyze-ast",
        json={"ast": ast, "objective": "all"},
        timeout=10.0,
    )
    response.raise_for_status()
    return response.json()


def run_test(test_case: Dict[str, Any], verbose: bool = False) -> Dict[str, Any]:
    """Ejecuta un caso de prueba recursivo."""
    name = test_case["name"]
    category = test_case.get("category", "general")

    if verbose:
        print(f"\n{'='*70}")
        print(f"TEST: {name}")
        print(f"Categoría: {category}")
        if test_case.get("recurrence"):
            print(f"Recurrencia: {test_case['recurrence']}")
        print(f"{'='*70}")

    try:
        # Parse
        parse_result = parse_code(test_case["pseudocode"])
        if not parse_result.get("ok"):
            print("❌ ERROR DE PARSING")
            print("   Respuesta completa del parser:", parse_result)
            detalle = parse_result.get("error") or parse_result.get("errors") or "sin detalle"
            print("   Detalle:", detalle)
            if "line" in parse_result or "column" in parse_result:
                print(
                    "   Línea:",
                    parse_result.get("line", "?"),
                    "Col:",
                    parse_result.get("column", "?"),
                )
            return {
                "name": name,
                "category": category,
                "status": "parse_error",
                "error": detalle,
            }

        # Analyze
        analysis = analyze_ast(parse_result["ast"])
        expected = test_case.get("expected", {})

        o_ok = analysis["big_o"] == expected.get("big_o")
        omega_ok = analysis["big_omega"] == expected.get("big_omega")

        matches = o_ok and omega_ok

        result = {
            "name": name,
            "category": category,
            "status": "success" if matches else "wrong_result",
            "expected": expected,
            "actual": {
                "big_o": analysis["big_o"],
                "big_omega": analysis["big_omega"],
                "theta": analysis.get("theta"),
            },
        }

        if verbose:
            print("\n📊 Resultados:")
            print(f"   Big-O: {analysis['big_o']}")
            print(f"   Big-Ω: {analysis['big_omega']}")
            print(f"   Θ: {analysis.get('theta')}")
            print("\n🎯 Esperado:")
            print(f"   Big-O: {expected.get('big_o')}")
            print(f"   Big-Ω: {expected.get('big_omega')}")
            if matches:
                print("\n✅ CORRECTO")
            else:
                print("\n❌ INCORRECTO:")
                print(f"   Esperado: O({expected.get('big_o')}), Ω({expected.get('big_omega')})")
                print(f"   Obtenido: O({analysis['big_o']}), Ω({analysis['big_omega']})")

        return result

    except Exception as e:
        if verbose:
            print(f"\n❌ ERROR: {e}")
        return {
            "name": name,
            "category": category,
            "status": "unexpected_error",
            "error": str(e),
        }


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Ejecuta la suite de pruebas recursivas."""
    print("\n🔄 PRUEBAS: ALGORITMOS RECURSIVOS")
    print("="*70)

    results = []

    for i, test_case in enumerate(RECURSIVE_TEST_CASES, 1):
        print(f"\n[{i}/{len(RECURSIVE_TEST_CASES)}] {test_case['name']}", end=" ... ")
        result = run_test(test_case, verbose=False)
        results.append(result)

        if result["status"] == "success":
            print("✅")
        elif result["status"] == "wrong_result":
            print("⚠️ (resultado distinto)")
            run_test(test_case, verbose=True)
        else:
            print(f"❌ ({result['status']})")
            run_test(test_case, verbose=True)

    print("\n" + "="*70)
    print("📊 RESUMEN GLOBAL")
    print("="*70)

    total_success = sum(1 for r in results if r["status"] == "success")
    total_wrong = sum(1 for r in results if r["status"] == "wrong_result")
    total_parse = sum(1 for r in results if r["status"] == "parse_error")
    total_unexpected = sum(1 for r in results if r["status"] == "unexpected_error")
    total_tests = len(results)

    print(f"\n✅ Correctos: {total_success}/{total_tests}")
    print(f"⚠️ Resultado diferente: {total_wrong}/{total_tests}")
    print(f"❌ Errores de parsing: {total_parse}/{total_tests}")
    print(f"❌ Errores inesperados: {total_unexpected}/{total_tests}")
    print("\n" + "="*70)

    return results


if __name__ == "__main__":
    main()
