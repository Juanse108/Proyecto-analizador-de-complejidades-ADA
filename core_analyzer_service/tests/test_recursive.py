# core_analyzer_service/tests/test_recursive_complete.py
"""
Suite COMPLETA de pruebas recursivas - 13 casos
===============================================

NOTA:
- Cada pseudocódigo va en una sola cadena con '\n' para evitar problemas de parseo.
- Esta suite está pensada para estresar el analizador recursivo en:
    * Recursión lineal
    * Divide y vencerás logarítmico
    * Divide y vencerás n log n
    * Recursión exponencial
    * Recursión múltiple (ramificación > 2)
"""

import httpx
from typing import Dict, Any, List

PARSER_URL = "http://localhost:8001"
ANALYZER_URL = "http://localhost:8002"

# ============================================================================
# CASOS DE PRUEBA
# ============================================================================

RECURSIVE_TEST_SUITE: List[Dict[str, Any]] = [
    # ============================================================
    # GRUPO 1: RECURSIÓN LINEAL (4 casos)
    # T(n) = T(n-1) + O(1)  ->  Θ(n)
    # ============================================================
    {
        "name": "Factorial recursivo",
        "pseudocode": (
            "FACTORIAL(n)\n"
            "begin\n"
            "  if (n <= 1) then\n"
            "  begin\n"
            "    return 1\n"
            "  end else\n"
            "  begin\n"
            "    return n * FACTORIAL(n - 1)\n"
            "  end\n"
            "end"
        ),
        "expected": {"big_o": "n", "big_omega": "n", "theta": "n"},
        "recurrence": "T(n) = T(n-1) + O(1)",
        "method": "linear_recurrence",
        "category": "linear",
    },

    {
        "name": "Suma recursiva de arreglo",
        "pseudocode": (
            "SUMA(A[1..n], i)\n"
            "begin\n"
            "  if (i > n) then\n"
            "  begin\n"
            "    return 0\n"
            "  end else\n"
            "  begin\n"
            "    return A[i] + SUMA(A, i + 1)\n"
            "  end\n"
            "end"
        ),
        "expected": {"big_o": "n", "big_omega": "n", "theta": "n"},
        "recurrence": "T(k) = T(k-1) + O(1) (n - i pasos)",
        "method": "linear_recurrence",
        "category": "linear",
    },

    {
        "name": "Potencia recursiva (naive)",
        "pseudocode": (
            "POTENCIA(base, exp)\n"
            "begin\n"
            "  if (exp = 0) then\n"
            "  begin\n"
            "    return 1\n"
            "  end else\n"
            "  begin\n"
            "    return base * POTENCIA(base, exp - 1)\n"
            "  end\n"
            "end"
        ),
        "expected": {"big_o": "n", "big_omega": "n", "theta": "n"},
        "recurrence": "T(exp) = T(exp-1) + O(1)",
        "method": "linear_recurrence",
        "category": "linear",
    },

    {
        "name": "Recursión de cola (factorial optimizado)",
        "pseudocode": (
            "FACTORIAL_TAIL(n, acum)\n"
            "begin\n"
            "  if (n <= 1) then\n"
            "  begin\n"
            "    return acum\n"
            "  end else\n"
            "  begin\n"
            "    return FACTORIAL_TAIL(n - 1, n * acum)\n"
            "  end\n"
            "end"
        ),
        "expected": {"big_o": "n", "big_omega": "n", "theta": "n"},
        "recurrence": "T(n) = T(n-1) + O(1)",
        "method": "linear_recurrence",
        "category": "linear",
        "notes": "Recursión de cola: tiempo O(n), espacio O(1) si el compilador optimiza tail-calls.",
    },

    # ============================================================
    # GRUPO 2: DIVIDE Y CONQUISTA - LOGARÍTMICO (3 casos)
    # T(n) = T(n/b) + O(1)  ->  Θ(log n)
    # ============================================================
    {
        "name": "Búsqueda binaria recursiva",
        "pseudocode": (
            "BINARY_SEARCH(A[1..n], x, inicio, fin)\n"
            "begin\n"
            "  if (inicio > fin) then\n"
            "  begin\n"
            "    return -1\n"
            "  end else\n"
            "  begin\n"
            "    medio <- (inicio + fin) div 2\n"
            "    if (A[medio] = x) then\n"
            "    begin\n"
            "      return medio\n"
            "    end else\n"
            "    begin\n"
            "      if (A[medio] < x) then\n"
            "      begin\n"
            "        return BINARY_SEARCH(A, x, medio + 1, fin)\n"
            "      end else\n"
            "      begin\n"
            "        return BINARY_SEARCH(A, x, inicio, medio - 1)\n"
            "      end\n"
            "    end\n"
            "  end\n"
            "end"
        ),
        "expected": {
            "big_o": "log n",   # Peor caso: baja toda la altura del árbol
            "big_omega": "1",   # Mejor caso: lo encuentra en la primera llamada
            "theta": None,      # No hay una única Θ(n) porque O ≠ Ω
        },
        "recurrence": "T(n) = T(n/2) + O(1)",
        "method": "master_theorem",
        "category": "logarithmic",
        "notes": "Peor caso Θ(log n): valor ausente o en una hoja. Mejor caso Θ(1): se encuentra en la primera comparación.",
    },

    {
        "name": "Potencia rápida (divide y conquista)",
        "pseudocode": (
            "POTENCIA_RAPIDA(base, exp)\n"
            "begin\n"
            "  if (exp = 0) then\n"
            "  begin\n"
            "    return 1\n"
            "  end else\n"
            "  begin\n"
            "    mitad <- POTENCIA_RAPIDA(base, exp div 2)\n"
            "    if (exp mod 2 = 0) then\n"
            "    begin\n"
            "      return mitad * mitad\n"
            "    end else\n"
            "    begin\n"
            "      return base * mitad * mitad\n"
            "    end\n"
            "  end\n"
            "end"
        ),
        "expected": {"big_o": "log n", "big_omega": "log n", "theta": "log n"},
        "recurrence": "T(exp) = T(exp/2) + O(1)",
        "method": "master_theorem",
        "category": "logarithmic",
    },

    {
        "name": "Búsqueda ternaria recursiva",
        "pseudocode": (
            "TERNARY_SEARCH(A[1..n], x, inicio, fin)\n"
            "begin\n"
            "  if (inicio > fin) then\n"
            "  begin\n"
            "    return -1\n"
            "  end else\n"
            "  begin\n"
            "    tercio <- (fin - inicio) div 3\n"
            "    mid1 <- inicio + tercio\n"
            "    mid2 <- fin - tercio\n"
            "    if (A[mid1] = x) then\n"
            "    begin\n"
            "      return mid1\n"
            "    end else\n"
            "    begin\n"
            "      if (A[mid2] = x) then\n"
            "      begin\n"
            "        return mid2\n"
            "      end else\n"
            "      begin\n"
            "        if (x < A[mid1]) then\n"
            "        begin\n"
            "          return TERNARY_SEARCH(A, x, inicio, mid1 - 1)\n"
            "        end else\n"
            "        begin\n"
            "          if (x > A[mid2]) then\n"
            "          begin\n"
            "            return TERNARY_SEARCH(A, x, mid2 + 1, fin)\n"
            "          end else\n"
            "          begin\n"
            "            return TERNARY_SEARCH(A, x, mid1 + 1, mid2 - 1)\n"
            "          end\n"
            "        end\n"
            "      end\n"
            "    end\n"
            "  end\n"
            "end"
        ),
        # Siempre se escoge exactamente uno de los 3 intervalos, tamaño ~n/3 → log n
        "expected": {"big_o": "log n", "big_omega": "log n", "theta": "log n"},
        "recurrence": "T(n) = T(n/3) + O(1)",
        "method": "master_theorem",
        "category": "logarithmic",
    },

    # ============================================================
    # GRUPO 3: DIVIDE Y CONQUISTA - N LOG N (2 casos)
    # T(n) = 2T(n/2) + O(n)  ->  Θ(n log n)
    # ============================================================
    {
        "name": "Merge Sort",
        "pseudocode": (
            "MERGE_SORT(A[1..n], inicio, fin)\n"
            "begin\n"
            "  if (inicio < fin) then\n"
            "  begin\n"
            "    medio <- (inicio + fin) div 2\n"
            "    CALL MERGE_SORT(A, inicio, medio)\n"
            "    CALL MERGE_SORT(A, medio + 1, fin)\n"
            "    CALL MERGE(A, inicio, medio, fin)\n"
            "  end else\n"
            "  begin\n"
            "    medio <- medio\n"
            "  end\n"
            "end"
        ),
        "expected": {"big_o": "n log n", "big_omega": "n log n", "theta": "n log n"},
        "recurrence": "T(n) = 2T(n/2) + O(n)",
        "method": "master_theorem",
        "category": "divide_conquer",
    },

    {
        "name": "Quick Sort (promedio, pivote balanceado)",
        "pseudocode": (
            "QUICK_SORT(A[1..n], inicio, fin)\n"
            "begin\n"
            "  if (inicio < fin) then\n"
            "  begin\n"
            "    pivote <- PARTITION(A, inicio, fin)\n"
            "    CALL QUICK_SORT(A, inicio, pivote - 1)\n"
            "    CALL QUICK_SORT(A, pivote + 1, fin)\n"
            "  end else\n"
            "  begin\n"
            "    pivote <- pivote\n"
            "  end\n"
            "end"
        ),
        # Aquí asumimos particiones balanceadas (caso promedio típico)
        "expected": {"big_o": "n log n", "big_omega": "n log n", "theta": "n log n"},
        "recurrence": "T(n) = 2T(n/2) + O(n)",
        "method": "master_theorem",
        "category": "divide_conquer",
        "notes": "Caso promedio / pivote aproximadamente balanceado. Peor caso clásico: O(n²) si el pivote queda muy desbalanceado.",
    },

    # ============================================================
    # GRUPO 4: RECURSIÓN EXPONENCIAL (3 casos)
    # ============================================================
    {
        "name": "Fibonacci ingenuo",
        "pseudocode": (
            "FIBONACCI(n)\n"
            "begin\n"
            "  if (n <= 1) then\n"
            "  begin\n"
            "    return n\n"
            "  end else\n"
            "  begin\n"
            "    return FIBONACCI(n - 1) + FIBONACCI(n - 2)\n"
            "  end\n"
            "end"
        ),
        "expected": {"big_o": "2^n", "big_omega": "2^n", "theta": "2^n"},
        "recurrence": "T(n) = T(n-1) + T(n-2) + O(1)",
        "method": "linear_recurrence",
        "category": "exponential",
        "notes": "En realidad es Θ(φ^n), pero 2^n es una cota estándar aceptable.",
    },

    {
        "name": "Torres de Hanoi",
        "pseudocode": (
            "HANOI(n, origen, destino, auxiliar)\n"
            "begin\n"
            "  if (n = 1) then\n"
            "  begin\n"
            "    x <- 1\n"
            "  end else\n"
            "  begin\n"
            "    CALL HANOI(n - 1, origen, auxiliar, destino)\n"
            "    x <- 1\n"
            "    CALL HANOI(n - 1, auxiliar, destino, origen)\n"
            "  end\n"
            "end"
        ),
        "expected": {"big_o": "2^n", "big_omega": "2^n", "theta": "2^n"},
        "recurrence": "T(n) = 2T(n-1) + O(1)",
        "method": "linear_recurrence",
        "category": "exponential",
    },

    {
        "name": "Subset Sum (2^n)",
        "pseudocode": (
            "SUBSET_SUM(A[1..n], i, suma_actual, objetivo)\n"
            "begin\n"
            "  if (i > n) then\n"
            "  begin\n"
            "    if (suma_actual = objetivo) then\n"
            "    begin\n"
            "      return 1\n"
            "    end else\n"
            "    begin\n"
            "      return 0\n"
            "    end\n"
            "  end else\n"
            "  begin\n"
            "    incluir <- SUBSET_SUM(A, i + 1, suma_actual + A[i], objetivo)\n"
            "    excluir <- SUBSET_SUM(A, i + 1, suma_actual, objetivo)\n"
            "    return incluir + excluir\n"
            "  end\n"
            "end"
        ),
        "expected": {"big_o": "2^n", "big_omega": "2^n", "theta": "2^n"},
        "recurrence": "T(n) = 2T(n-1) + O(1)",
        "method": "linear_recurrence",
        "category": "exponential",
    },

    # ============================================================
    # GRUPO 5: CASO ESPECIAL - RECURSIÓN MÚLTIPLE (1 caso)
    # ============================================================
    {
        "name": "Recursión múltiple ternaria",
        "pseudocode": (
            "TERNARY_TREE(n)\n"
            "begin\n"
            "  if (n <= 0) then\n"
            "  begin\n"
            "    return 1\n"
            "  end else\n"
            "  begin\n"
            "    return TERNARY_TREE(n - 1) + TERNARY_TREE(n - 1) + TERNARY_TREE(n - 1)\n"
            "  end\n"
            "end"
        ),
        "expected": {"big_o": "3^n", "big_omega": "3^n", "theta": "3^n"},
        "recurrence": "T(n) = 3T(n-1) + O(1)",
        "method": "linear_recurrence",
        "category": "exponential",
    },
]


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def parse_code(code: str) -> Dict[str, Any]:
    response = httpx.post(f"{PARSER_URL}/parse", json={"code": code}, timeout=10.0)
    response.raise_for_status()
    return response.json()


def analyze_ast(ast: Dict[str, Any]) -> Dict[str, Any]:
    response = httpx.post(
        f"{ANALYZER_URL}/analyze-ast",
        json={"ast": ast, "objective": "all"},
        timeout=10.0,
    )
    response.raise_for_status()
    return response.json()


def run_test(test_case: Dict[str, Any], verbose: bool = False) -> Dict[str, Any]:
    name = test_case["name"]
    category = test_case.get("category", "general")

    if verbose:
        print(f"\n{'=' * 70}")
        print(f"TEST: {name}")
        print(f"Categoría: {category}")
        if test_case.get("recurrence"):
            print(f"Recurrencia: {test_case['recurrence']}")
        if test_case.get("notes"):
            print(f"Nota: {test_case['notes']}")
        print(f"{'=' * 70}")

    try:
        # Parse
        parse_result = parse_code(test_case["pseudocode"])
        if not parse_result.get("ok"):
            if verbose:
                print("❌ ERROR DE PARSING")
                print(f"   Detalle: {parse_result.get('error', 'sin detalle')}")
            return {
                "name": name,
                "category": category,
                "status": "parse_error",
                "error": parse_result.get("error"),
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
                print("\n❌ INCORRECTO")
                if not o_ok:
                    print(f"   O: esperado {expected['big_o']}, obtenido {analysis['big_o']}")
                if not omega_ok:
                    print(f"   Ω: esperado {expected['big_omega']}, obtenido {analysis['big_omega']}")

        return result

    except Exception as e:
        if verbose:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
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
    print("\n🔄 SUITE COMPLETA: ALGORITMOS RECURSIVOS (13 CASOS)")
    print("=" * 70)
    print(f"Total de casos: {len(RECURSIVE_TEST_SUITE)}\n")

    results: List[Dict[str, Any]] = []
    by_category: Dict[str, List[Dict[str, Any]]] = {}

    # Ejecutar todos los tests
    for i, test_case in enumerate(RECURSIVE_TEST_SUITE, 1):
        print(f"[{i}/{len(RECURSIVE_TEST_SUITE)}] {test_case['name']}", end=" ... ")
        result = run_test(test_case, verbose=False)
        results.append(result)

        cat = result["category"]
        by_category.setdefault(cat, []).append(result)

        if result["status"] == "success":
            print("✅")
        else:
            print(f"❌ ({result['status']})")

    # Resumen por categoría
    print("\n" + "=" * 70)
    print("📊 RESUMEN POR CATEGORÍA")
    print("=" * 70)

    for category in sorted(by_category.keys()):
        tests = by_category[category]
        success = sum(1 for t in tests if t["status"] == "success")
        total = len(tests)
        pct = (success / total * 100) if total > 0 else 0

        status_icon = "✅" if success == total else "⚠️"
        print(f"\n{status_icon} {category.upper()}: {success}/{total} ({pct:.0f}%)")

        for test in tests:
            icon = "✅" if test["status"] == "success" else "❌"
            print(f"   {icon} {test['name']}")
            if test["status"] == "wrong_result":
                exp = test["expected"]
                act = test["actual"]
                print(f"      Esperado: O({exp.get('big_o')}), Ω({exp.get('big_omega')})")
                print(f"      Obtenido: O({act.get('big_o')}), Ω({act.get('big_omega')})")

    # Resumen global
    print("\n" + "=" * 70)
    print("🎯 RESUMEN GLOBAL")
    print("=" * 70)

    total_success = sum(1 for r in results if r["status"] == "success")
    total_tests = len(results)
    success_rate = (total_success / total_tests * 100) if total_tests > 0 else 0

    print(f"\n✅ Tests exitosos: {total_success}/{total_tests} ({success_rate:.1f}%)")

    if total_success < total_tests:
        print("\n❌ Tests fallidos:")
        for r in results:
            if r["status"] != "success":
                print(f"   - {r['name']} ({r['status']})")

    print("\n" + "=" * 70)
    return results


if __name__ == "__main__":
    main()
