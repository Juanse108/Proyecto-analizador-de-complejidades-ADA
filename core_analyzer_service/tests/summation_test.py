"""
Pruebas de Sumatorias y Bucles Triangulares
===========================================

Casos donde el límite de un bucle interno depende del contador externo.
"""

import httpx
import json

PARSER_URL = "http://localhost:8001"
ANALYZER_URL = "http://localhost:8002"

# ============================================================================
# CASOS DE SUMATORIAS / BUCLES TRIANGULARES
# ============================================================================

SUMMATION_CASES = [
    # ========== TRIANGULAR BÁSICO ==========
    {
        "name": "Triangular simple: for j <- 1 to i",
        "pseudocode": """begin
  for i <- 1 to n do
  begin
    for j <- 1 to i do
    begin
      x <- x + 1
    end
  end
end""",
        "expected": {
            "big_o": "n^2",
            "big_omega": "n^2",
            "theta": "n^2"
        },
        "explanation": "Σᵢ₌₁ⁿ i = n(n+1)/2 ≈ O(n²)",
        "category": "triangular"
    },

    # ========== TRIANGULAR INVERSO ==========
    {
        "name": "Triangular inverso: for j <- i to n",
        "pseudocode": """begin
  for i <- 1 to n do
  begin
    for j <- i to n do
    begin
      x <- x + 1
    end
  end
end""",
        "expected": {
            "big_o": "n^2",
            "big_omega": "n^2",
            "theta": "n^2"
        },
        "explanation": "Σᵢ₌₁ⁿ (n-i+1) = n(n+1)/2 ≈ O(n²)",
        "category": "triangular"
    },

    # ========== INSERTION SORT (simplificado) ==========
    {
        "name": "Insertion Sort (bucle interno variable)",
        "pseudocode": """begin
  for i <- 2 to n do
  begin
    key <- A[i]
    j <- i
    while (j > 1) do
    begin
      A[j] <- A[j - 1]
      j <- j - 1
    end
  end
end""",
        "expected": {
            "big_o": "n^2",
            "big_omega": "n^2",
            "theta": "n^2"
        },
        "explanation": "While interno hace hasta i iteraciones",
        "category": "triangular_while"
    },

    # ========== TRIANGULAR CON TRABAJO INTERNO ==========
    {
        "name": "Triangular con bucle interno O(n)",
        "pseudocode": """begin
  for i <- 1 to n do
  begin
    for j <- 1 to i do
    begin
      for k <- 1 to n do
      begin
        x <- x + 1
      end
    end
  end
end""",
        "expected": {
            "big_o": "n^3",
            "big_omega": "n^3",
            "theta": "n^3"
        },
        "explanation": "Σᵢ₌₁ⁿ (i * n) = n * n²/2 ≈ O(n³)",
        "category": "triangular_nested"
    },

    # ========== MATRICES TRIANGULARES ==========
    {
        "name": "Matriz triangular superior",
        "pseudocode": """begin
  for i <- 1 to n do
  begin
    for j <- i to n do
    begin
      M[i][j] <- i + j
    end
  end
end""",
        "expected": {
            "big_o": "n^2",
            "big_omega": "n^2",
            "theta": "n^2"
        },
        "explanation": "Solo llena la mitad superior de la matriz",
        "category": "triangular"
    },

    # ========== DOBLE TRIANGULAR ==========
    {
        "name": "Doble triangular anidado",
        "pseudocode": """begin
  for i <- 1 to n do
  begin
    for j <- 1 to i do
    begin
      for k <- 1 to j do
      begin
        x <- x + 1
      end
    end
  end
end""",
        "expected": {
            "big_o": "n^3",
            "big_omega": "n^3",
            "theta": "n^3"
        },
        "explanation": "Σᵢ Σⱼ≤ᵢ j = Σᵢ i²/2 ≈ O(n³)",
        "category": "double_triangular"
    },

    # ========== COMPARACIÓN: NO TRIANGULAR ==========
    {
        "name": "Control: bucle cuadrado completo (no triangular)",
        "pseudocode": """begin
  for i <- 1 to n do
  begin
    for j <- 1 to n do
    begin
      x <- x + 1
    end
  end
end""",
        "expected": {
            "big_o": "n^2",
            "big_omega": "n^2",
            "theta": "n^2"
        },
        "explanation": "n * n = O(n²) (no es triangular)",
        "category": "control"
    },

    # ========== TRIANGULAR CON VARIABLE DIFERENTE ==========
    {
        "name": "Bucle hasta m (no triangular)",
        "pseudocode": """begin
  for i <- 1 to n do
  begin
    for j <- 1 to m do
    begin
      x <- x + 1
    end
  end
end""",
        "expected": {
            "big_o": "n m",
            "big_omega": "n m",
            "theta": "n m"
        },
        "explanation": "n * m (dos variables independientes)",
        "category": "multi_variable"
    },
]


# ============================================================================
# FUNCIONES DE PRUEBA
# ============================================================================

def parse_code(code: str):
    response = httpx.post(f"{PARSER_URL}/parse", json={"code": code}, timeout=10.0)
    response.raise_for_status()
    return response.json()


def analyze_ast(ast, detail="line-by-line"):
    response = httpx.post(
        f"{ANALYZER_URL}/analyze-ast",
        json={"ast": ast, "objective": "all", "detail": detail},
        timeout=10.0
    )
    response.raise_for_status()
    return response.json()


def run_test(test_case, verbose=True):
    name = test_case['name']

    if verbose:
        print(f"\n{'=' * 70}")
        print(f"TEST: {name}")
        print(f"{'=' * 70}")
        if 'explanation' in test_case:
            print(f"💡 {test_case['explanation']}")

    try:
        # Parse
        parse_result = parse_code(test_case["pseudocode"])
        if not parse_result.get("ok"):
            print(f"❌ ERROR DE PARSING:")
            print(json.dumps(parse_result.get("errors", []), indent=2))
            return {"status": "parse_error", "name": name}

        # Analyze
        analysis = analyze_ast(parse_result["ast"])

        expected = test_case.get("expected", {})

        if verbose:
            print(f"\n📊 Resultados:")
            print(f"   Big-O:  {analysis['big_o']}")
            print(f"   Big-Ω:  {analysis['big_omega']}")
            print(f"   Θ:      {analysis.get('theta', 'None')}")

            print(f"\n🎯 Esperado:")
            print(f"   Big-O:  {expected.get('big_o', '?')}")
            print(f"   Big-Ω:  {expected.get('big_omega', '?')}")
            print(f"   Θ:      {expected.get('theta', '?')}")

        # Verificar
        o_match = analysis['big_o'] == expected.get('big_o')
        omega_match = analysis['big_omega'] == expected.get('big_omega')

        if o_match and omega_match:
            print(f"\n✅ CORRECTO")
            return {"status": "success", "name": name}
        else:
            print(f"\n❌ INCORRECTO")
            if not o_match:
                print(f"   O: esperado {expected['big_o']}, obtenido {analysis['big_o']}")
            if not omega_match:
                print(f"   Ω: esperado {expected['big_omega']}, obtenido {analysis['big_omega']}")

            # Debug: líneas
            if analysis.get('lines'):
                print(f"\n📝 Últimas 5 líneas del análisis:")
                for line in analysis['lines'][-5:]:
                    print(
                        f"   L{line['line']:<3} {line['kind']:<10} "
                        f"mult={line['multiplier']:<10} worst={line['cost_worst']}"
                    )

            return {"status": "wrong_result", "name": name}

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "unexpected_error", "error": str(e), "name": name}


def main():
    print("\n🔺 PRUEBAS: SUMATORIAS Y BUCLES TRIANGULARES")
    print("=" * 70)

    results = []
    by_category = {}

    for i, test_case in enumerate(SUMMATION_CASES, 1):
        print(f"\n[{i}/{len(SUMMATION_CASES)}] {test_case['name']}", end=" ... ")
        result = run_test(test_case, verbose=False)

        # Print inline
        if result['status'] == 'success':
            print("✅")
        else:
            print(f"❌ ({result['status']})")
            # Re-run con verbose para ver detalles
            run_test(test_case, verbose=True)

        results.append(result)

        # Agrupar por categoría
        cat = test_case.get('category', 'general')
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(result)

    # Resumen
    print(f"\n\n{'=' * 70}")
    print("📊 RESUMEN POR CATEGORÍA")
    print(f"{'=' * 70}")

    for category in sorted(by_category.keys()):
        tests = by_category[category]
        success = sum(1 for t in tests if t['status'] == 'success')
        total = len(tests)
        pct = (success / total * 100) if total > 0 else 0

        icon = "✅" if success == total else "⚠️"
        print(f"\n{icon} {category.upper()}: {success}/{total} ({pct:.0f}%)")

        for test in tests:
            status_icon = "✅" if test['status'] == 'success' else "❌"
            print(f"   {status_icon} {test['name']}")

    # Global
    print(f"\n\n{'=' * 70}")
    print("🎯 RESUMEN GLOBAL")
    print(f"{'=' * 70}")

    success = sum(1 for r in results if r['status'] == 'success')
    total = len(results)
    pct = (success / total * 100) if total > 0 else 0

    print(f"\n✅ Tests exitosos: {success}/{total} ({pct:.1f}%)")

    if success < total:
        print(f"\n❌ Tests fallidos:")
        for r in results:
            if r['status'] != 'success':
                print(f"   - {r['name']}")


if __name__ == "__main__":
    main()