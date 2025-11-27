"""
real_algorithms_test.py - Pruebas con algoritmos "reales"
=========================================================

Cubre algoritmos clásicos iterativos:

- Búsqueda lineal
- Búsqueda binaria (iterativa)
- Máximo en arreglo
- Burbuja simple
- Burbuja optimizada con bandera
- Selección
- Multiplicación de matrices n x n
- Bucle mixto n log n
"""

import httpx
from typing import Dict, Any, List

PARSER_URL = "http://localhost:8001"
ANALYZER_URL = "http://localhost:8002"


# ============================================================================
# CASOS DE PRUEBA
# ============================================================================

REAL_ALGO_TEST_CASES: List[Dict[str, Any]] = [
    # ========== BÚSQUEDAS ==========
    {
        "name": "Búsqueda lineal en arreglo no ordenado",
        "category": "searching",
        "pseudocode": (
            "BusquedaLineal(A[1..n], x)\n"
            "begin\n"
            "  i <- 1\n"
            "  while (i <= n) do\n"
            "  begin\n"
            "    if (A[i] = x) then\n"
            "    begin\n"
            "      i <- n + 1\n"
            "    end else\n"
            "    begin\n"
            "      i <- i + 1\n"
            "    end\n"
            "  end\n"
            "end"
        ),
        # COMPLEJIDADES REALES:
        #   Mejor caso: Ω(1)  (lo encuentra en A[1])
        #   Peor caso:  O(n)  (no está o está al final)
        #   Promedio:   Θ(n)
        "expected": {
            "big_o": "n",     # peor caso
            "big_omega": "1", # mejor caso
            "theta": "n"      # promedio / orden típico
        },
        "notes": "Teórico: peor O(n), mejor Ω(1), promedio Θ(n). Aquí reflejamos mejores/peores reales."
    },
    {
        "name": "Búsqueda binaria iterativa",
        "category": "searching",
        "pseudocode": (
            "BusquedaBinaria(A[1..n], x)\n"
            "begin\n"
            "  l <- 1\n"
            "  r <- n\n"
            "  while (l <= r) do\n"
            "  begin\n"
            "    m <- (l + r) div 2\n"
            "    if (A[m] = x) then\n"
            "    begin\n"
            "      l <- r + 1\n"
            "    end else\n"
            "    begin\n"
            "      if (A[m] < x) then\n"
            "      begin\n"
            "        l <- m + 1\n"
            "      end else\n"
            "      begin\n"
            "        r <- m - 1\n"
            "      end\n"
            "    end\n"
            "  end\n"
            "end"
        ),
        # COMPLEJIDADES REALES:
        #   Mejor caso: Ω(1)       (lo encuentra en la primera comparación)
        #   Peor caso:  O(log n)
        #   Promedio:   Θ(log n)
        "expected": {
            "big_o": "log n",  # peor caso
            "big_omega": "1",  # mejor caso
            "theta": "log n"   # promedio
        },
        "notes": "Clásico while que reduce el intervalo a la mitad: peor Θ(log n), mejor Θ(1)."
    },

    # ========== ARREGLOS / LINEAL ==========
    {
        "name": "Máximo de un arreglo",
        "category": "arrays",
        "pseudocode": (
            "Maximo(A[1..n])\n"
            "begin\n"
            "  max <- A[1]\n"
            "  i <- 2\n"
            "  while (i <= n) do\n"
            "  begin\n"
            "    if (A[i] > max) then\n"
            "    begin\n"
            "      max <- A[i]\n"
            "    end else\n"
            "    begin\n"
            "      max <- max\n"
            "    end\n"
            "    i <- i + 1\n"
            "  end\n"
            "end"
        ),
        # COMPLEJIDADES REALES:
        #   Siempre recorre de 2..n sin early exit → n-1 comparaciones.
        #   Mejor = Peor = Promedio = Θ(n).
        "expected": {
            "big_o": "n",
            "big_omega": "n",
            "theta": "n"
        },
        "notes": "Recorre el arreglo una sola vez: mejor, peor y promedio son lineales."
    },

    # ========== ORDENAMIENTO: BURBUJA ==========
    {
        "name": "Burbuja simple (no optimizada)",
        "category": "sorting",
        "pseudocode": (
            "BurbujaSimple(A[1..n])\n"
            "begin\n"
            "  for i <- 1 to n - 1 do\n"
            "  begin\n"
            "    for j <- 1 to n - i do\n"
            "    begin\n"
            "      if (A[j] > A[j + 1]) then\n"
            "      begin\n"
            "        temp <- A[j]\n"
            "        A[j] <- A[j + 1]\n"
            "        A[j + 1] <- temp\n"
            "      end else\n"
            "      begin\n"
            "        temp <- temp\n"
            "      end\n"
            "    end\n"
            "  end\n"
            "end"
        ),
        # COMPLEJIDADES REALES:
        #   No hay bandera, siempre recorre la suma 1 + 2 + ... + (n-1) → Θ(n^2)
        #   Mejor = Peor = Promedio = Θ(n^2).
        "expected": {
            "big_o": "n^2",
            "big_omega": "n^2",
            "theta": "n^2"
        },
        "notes": "Doble bucle triangular clásico Θ(n^2) en todos los casos."
    },
    {
        "name": "Burbuja optimizada con bandera",
        "category": "sorting",
        "pseudocode": (
            "BurbujaOptimizada(A[1..n])\n"
            "begin\n"
            "  i <- 1\n"
            "  intercambiado <- true\n"
            "  while (i <= n - 1 and intercambiado) do\n"
            "  begin\n"
            "    intercambiado <- false\n"
            "    j <- 1\n"
            "    while (j <= n - i) do\n"
            "    begin\n"
            "      if (A[j] > A[j + 1]) then\n"
            "      begin\n"
            "        temp <- A[j]\n"
            "        A[j] <- A[j + 1]\n"
            "        A[j + 1] <- temp\n"
            "        intercambiado <- true\n"
            "      end else\n"
            "      begin\n"
            "        intercambiado <- intercambiado\n"
            "      end\n"
            "      j <- j + 1\n"
            "    end\n"
            "    i <- i + 1\n"
            "  end\n"
            "end"
        ),
        # COMPLEJIDADES REALES:
        #   Mejor caso (arreglo ya ordenado):
        #       Solo una pasada del while externo, inner hace ~n comparaciones → Θ(n).
        #   Peor caso (invertido):
        #       Se comporta como burbuja normal → Θ(n^2).
        #   Promedio:
        #       Sigue siendo Θ(n^2) en número de comparaciones.
        "expected": {
            "big_o": "n^2",  # peor caso
            "big_omega": "n",# mejor caso
            "theta": "n^2"   # promedio
        },
        "notes": "Burbuja con bandera: mejor caso Θ(n), pero peor y promedio siguen siendo Θ(n^2)."
    },

    # ========== ORDENAMIENTO: SELECCIÓN ==========
    {
        "name": "Selección (Selection Sort)",
        "category": "sorting",
        "pseudocode": (
            "Seleccion(A[1..n])\n"
            "begin\n"
            "  for i <- 1 to n - 1 do\n"
            "  begin\n"
            "    minIndex <- i\n"
            "    for j <- i + 1 to n do\n"
            "    begin\n"
            "      if (A[j] < A[minIndex]) then\n"
            "      begin\n"
            "        minIndex <- j\n"
            "      end else\n"
            "      begin\n"
            "        minIndex <- minIndex\n"
            "      end\n"
            "    end\n"
            "    if (minIndex != i) then\n"
            "    begin\n"
            "      temp <- A[i]\n"
            "      A[i] <- A[minIndex]\n"
            "      A[minIndex] <- temp\n"
            "    end else\n"
            "    begin\n"
            "      temp <- temp\n"
            "    end\n"
            "  end\n"
            "end"
        ),
        # COMPLEJIDADES REALES:
        #   El número de comparaciones no depende del contenido:
        #     sum_{i=1}^{n-1} (n-i) = Θ(n^2)
        #   Mejor = Peor = Promedio = Θ(n^2).
        "expected": {
            "big_o": "n^2",
            "big_omega": "n^2",
            "theta": "n^2"
        },
        "notes": "Bucle externo 1..n-1, interno i+1..n → Θ(n^2) en todos los casos."
    },

    # ========== MATRICES ==========
    {
        "name": "Multiplicación de matrices n x n",
        "category": "matrix",
        "pseudocode": (
            "MultiplicarMatrices(A[1..n][1..n], B[1..n][1..n], C[1..n][1..n])\n"
            "begin\n"
            "  for i <- 1 to n do\n"
            "  begin\n"
            "    for j <- 1 to n do\n"
            "    begin\n"
            "      C[i][j] <- 0\n"
            "      for k <- 1 to n do\n"
            "      begin\n"
            "        C[i][j] <- C[i][j] + A[i][k] * B[k][j]\n"
            "      end\n"
            "    end\n"
            "  end\n"
            "end"
        ),
        # COMPLEJIDADES REALES:
        #   Triple bucle completo → n * n * n iteraciones.
        #   Mejor = Peor = Promedio = Θ(n^3).
        "expected": {
            "big_o": "n^3",
            "big_omega": "n^3",
            "theta": "n^3"
        },
        "notes": "Triple bucle completo → Θ(n^3) siempre."
    },

    # ========== MIXTOS n log n ==========
    {
        "name": "Bucle mixto n log n",
        "category": "mixed",
        "pseudocode": (
            "BucleMixto(A[1..n])\n"
            "begin\n"
            "  for i <- 1 to n do\n"
            "  begin\n"
            "    j <- 1\n"
            "    while (j <= n) do\n"
            "    begin\n"
            "      x <- A[i]\n"
            "      j <- j * 2\n"
            "    end\n"
            "  end\n"
            "end"
        ),
        # COMPLEJIDADES REALES:
        #   Inner while: j = 1,2,4,8,... ≤ n → Θ(log n) iteraciones por cada i.
        #   Outer for: n iteraciones.
        #   Mejor = Peor = Promedio = Θ(n log n).
        "expected": {
            "big_o": "n log n",
            "big_omega": "n log n",
            "theta": "n log n"
        },
        "notes": "for externo n; while interno log n → Θ(n log n) en todos los casos."
    }
]


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def parse_code(code: str) -> Dict[str, Any]:
    """Llama al microservicio de parseo."""
    response = httpx.post(f"{PARSER_URL}/parse", json={"code": code}, timeout=10.0)
    response.raise_for_status()
    return response.json()


def analyze_ast(ast: Dict[str, Any], detail: str = "program") -> Dict[str, Any]:
    """Llama al microservicio de análisis iterativo."""
    response = httpx.post(
        f"{ANALYZER_URL}/analyze-ast",
        json={"ast": ast, "objective": "all", "detail": detail},
        timeout=10.0,
    )
    response.raise_for_status()
    return response.json()


def run_test(test_case: Dict[str, Any], verbose: bool = False) -> Dict[str, Any]:
    """Ejecuta un caso de prueba de algoritmo real."""
    name = test_case["name"]
    category = test_case.get("category", "general")

    if verbose:
        print("\n" + "=" * 70)
        print(f"TEST: {name}")
        print(f"Categoría: {category}")
        print("=" * 70)

    try:
        # 1) Parsear pseudocódigo → AST
        parse_result = parse_code(test_case["pseudocode"])
        if not parse_result.get("ok"):
            if verbose:
                print("❌ Error de parseo:")
                for err in parse_result.get("errors", []):
                    print("   ", err)
            return {
                "name": name,
                "category": category,
                "status": "parse_error",
                "errors": parse_result.get("errors"),
            }

        # 2) Analizar AST → complejidad
        analysis = analyze_ast(parse_result["ast"], detail="program")

        expected = test_case.get("expected", {})
        big_o_ok = analysis["big_o"] == expected.get("big_o")
        big_omega_ok = analysis["big_omega"] == expected.get("big_omega")

        matches = big_o_ok and big_omega_ok

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
            print("Pseudocódigo:\n")
            print(test_case["pseudocode"])
            print("\nResultados del analizador:")
            print(f"   big_o:      {analysis['big_o']}")
            print(f"   big_omega:  {analysis['big_omega']}")
            print(f"   theta:      {analysis.get('theta')}")
            print("\nEsperado:")
            print(f"   big_o:      {expected.get('big_o')}")
            print(f"   big_omega:  {expected.get('big_omega')}")
            print(f"   theta:      {expected.get('theta')}")

            if matches:
                print("\n✅ CORRECTO")
            else:
                print("\n❌ INCORRECTO")

        return result

    except Exception as e:
        if verbose:
            print("\n❌ Error inesperado:", str(e))
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
    """Ejecuta toda la suite de algoritmos reales."""
    total_tests = len(REAL_ALGO_TEST_CASES)
    print("\n🚀 SUITE DE PRUEBAS - ALGORITMOS REALES")
    print("=" * 70)
    print(f"Total de casos: {total_tests}\n")

    results: List[Dict[str, Any]] = []
    by_category: Dict[str, List[Dict[str, Any]]] = {}

    # Ejecutar todos los tests
    for i, test_case in enumerate(REAL_ALGO_TEST_CASES, 1):
        print(f"[{i}/{total_tests}] {test_case['name']}", end=" ... ")
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
        pct = (success / total * 100) if total > 0 else 0.0

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
    success_rate = (total_success / total_tests * 100) if total_tests > 0 else 0.0

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
