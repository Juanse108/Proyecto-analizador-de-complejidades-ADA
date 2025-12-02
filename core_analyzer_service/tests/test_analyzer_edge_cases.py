"""
test_analyzer_edge_cases.py - Batería de casos "tóxicos" para el analizador
===========================================================================

Objetivo:
    - Detectar vacíos de lógica en el analizador iterativo y recursivo.
    - Incluir casos donde la complejidad teórica es clara, pero el analizador
      probablemente falle (n log n raros, master theorem no estándar, etc.).

NOTA:
    - No pasa nada si muchos tests salen en rojo al principio: la idea es
      precisamente revelar debilidades del analizador.
"""

import httpx
from typing import Dict, Any, List

PARSER_URL = "http://localhost:8001"
ANALYZER_URL = "http://localhost:8002"

# ============================================================================
# CASOS DE PRUEBA
# ============================================================================

EDGE_CASES: List[Dict[str, Any]] = [
    # ============================================================
    # 1. ITERATIVOS LINEALES Y NO TAN LINEALES
    # ============================================================

    {
        "name": "For simple 1..n (sumatoria básica)",
        "category": "iter_linear",
        "pseudocode": """begin
  suma <- 0
  for i <- 1 to n do
  begin
    suma <- suma + A[i]
  end
end""",
        "expected": {"big_o": "n", "big_omega": "n", "theta": "n"},
        "notes": "Caso base lineal; debería ser trivial para el analizador."
    },

    {
        "name": "While con incremento de 2 (no logarítmico)",
        "category": "iter_linear",
        "pseudocode": """begin
  i <- 1
  while (i <= n) do
  begin
    x <- x + 1
    i <- i + 2
  end
end""",
        "expected": {"big_o": "n", "big_omega": "n", "theta": "n"},
        "notes": "Si la heurística confunde i<-i+2 con halving/doubling, aquí se ve."
    },

    # ============================================================
    # 2. LOGARÍTMICOS ITERATIVOS (HALVING / DOUBLING)
    # ============================================================

    {
        "name": "While halving por div (value div 2)",
        "category": "iter_log",
        "pseudocode": """begin
  value <- n
  while (value > 1) do
  begin
    x <- x + 1
    value <- value div 2
  end
end""",
        "expected": {"big_o": "log n", "big_omega": "log n", "theta": "log n"},
        "notes": "Prueba directa de la detección de halving con 'div'."
    },

    {
        "name": "While halving por / 3",
        "category": "iter_log",
        "pseudocode": """begin
  value <- n
  while (value > 1) do
  begin
    x <- x + 1
    value <- value / 3
  end
end""",
        "expected": {"big_o": "log n", "big_omega": "log n", "theta": "log n"},
        "notes": "Halving genérico con /3; debería seguir siendo log n."
    },

    {
        "name": "For con doubling interno (n log n)",
        "category": "iter_nlogn",
        "pseudocode": """begin
  for i <- 1 to n do
  begin
    j <- 1
    while (j <= n) do
    begin
      x <- x + 1
      j <- j * 2
    end
  end
end""",
        "expected": {"big_o": "n log n", "big_omega": "n log n", "theta": "n log n"},
        "notes": "Caso clásico n * log n; bueno para probar combinación de patrones."
    },

    # ============================================================
    # 3. ANIDADOS CUADRÁTICOS Y CÚBICOS
    # ============================================================

    {
        "name": "Doble bucle completo n x n (rectangular)",
        "category": "iter_quadratic",
        "pseudocode": """begin
  count <- 0
  for i <- 1 to n do
  begin
    for j <- 1 to n do
    begin
      count <- count + 1
    end
  end
end""",
        "expected": {"big_o": "n^2", "big_omega": "n^2", "theta": "n^2"},
        "notes": "Rectangular completo; debería ser cuadrático estable."
    },

    {
        "name": "Doble bucle triangular (sumatoria)",
        "category": "iter_quadratic",
        "pseudocode": """begin
  count <- 0
  for i <- 1 to n do
  begin
    for j <- 1 to i do
    begin
      count <- count + 1
    end
  end
end""",
        "expected": {"big_o": "n^2", "big_omega": "n^2", "theta": "n^2"},
        "notes": "Σi = n(n+1)/2 ≈ n^2; tu analizador antes aquí sufría."
    },

    {
        "name": "Triple bucle completo n x n x n",
        "category": "iter_cubic",
        "pseudocode": """begin
  count <- 0
  for i <- 1 to n do
  begin
    for j <- 1 to n do
    begin
      for k <- 1 to n do
      begin
        count <- count + 1
      end
    end
  end
end""",
        "expected": {"big_o": "n^3", "big_omega": "n^3", "theta": "n^3"},
        "notes": "Cúbico puro; prueba de que el analizador propaga exponentes."
    },

    # ============================================================
    # 4. EARLY EXIT vs NO EARLY EXIT (ITERATIVO)
    # ============================================================

    {
        "name": "Búsqueda lineal con early exit (bandera found)",
        "category": "iter_early_exit",
        "pseudocode": """begin
  i <- 1
  found <- F
  while (i <= n and found = F) do
  begin
    if (A[i] = x) then
    begin
      found <- T
    end else
    begin
      i <- i + 1
    end
  end
end""",
        "expected": {"big_o": "n", "big_omega": "1", "theta": None},
        "notes": "Mejor caso O(1), peor O(n); buen test de detección de early exit."
    },

    {
        "name": "Búsqueda lineal sin early exit (recorre todo)",
        "category": "iter_non_adaptive",
        "pseudocode": """begin
  i <- 1
  result <- -1
  while (i <= n) do
  begin
    if (A[i] = x) then
    begin
      result <- i
    end else
    begin
      result <- result
    end
    i <- i + 1
  end
end""",
        "expected": {"big_o": "n", "big_omega": "n", "theta": "n"},
        "notes": "Aunque encuentre, NO sale temprano; mejor = peor = n."
    },

    # ============================================================
    # 5. RECURSIVOS: LINEALES Y NO LINEALES
    # ============================================================

    {
        "name": "Recursión lineal T(n) = T(n-1) + O(1)",
        "category": "rec_linear",
        "pseudocode": """LINEAL(n)
begin
  if (n <= 1) then
  begin
    return 1
  end else
  begin
    return 1 + LINEAL(n - 1)
  end
end""",
        "expected": {"big_o": "n", "big_omega": "n", "theta": "n"},
        "notes": "Factorial-like pero más simple; sanity check de recursión lineal."
    },

    {
        "name": "Recursión lineal con trabajo creciente T(n)=T(n-1)+n",
        "category": "rec_superlinear",
        "pseudocode": """LINEAL_PESADA(n)
begin
  if (n <= 1) then
  begin
    return 1
  end else
  begin
    for i <- 1 to n do
    begin
      x <- x + 1
    end
    return LINEAL_PESADA(n - 1)
  end
end""",
        # T(n) = T(n-1) + n => T(n) ~ n(n+1)/2 => Θ(n^2)
        "expected": {"big_o": "n^2", "big_omega": "n^2", "theta": "n^2"},
        "notes": "Buen test para ver si el analizador suma correctamente el trabajo del for dentro de la recursión."
    },

    # ============================================================
    # 6. DIVIDE & CONQUER NO TÍPICOS (MASTER THEOREM)
    # ============================================================

    {
        "name": "T(n) = 2T(n/2) + O(1) (árbol perfecto)",
        "category": "rec_master",
        "pseudocode": """PERFECT_SPLIT(n)
begin
  if (n <= 1) then
  begin
    return 1
  end else
  begin
    left <- PERFECT_SPLIT(n / 2)
    right <- PERFECT_SPLIT(n / 2)
    return left + right
  end
end""",
        # a=2, b=2, f(n)=O(1) => n^{log_b a} = n => f(n) = O(n^{log_b a - 1}) => T(n)=Θ(n)
        "expected": {"big_o": "n", "big_omega": "n", "theta": "n"},
        "notes": "Clásico ejemplo de master theorem caso 1 (subtrabajo domina)."
    },

    {
        "name": "T(n) = 2T(n/2) + O(n) (merge sort)",  # duplicamos pero más limpio
        "category": "rec_master",
        "pseudocode": """MERGE_STYLE(n)
begin
  if (n <= 1) then
  begin
    return 1
  end else
  begin
    left <- MERGE_STYLE(n / 2)
    right <- MERGE_STYLE(n / 2)
    for i <- 1 to n do
    begin
      x <- x + 1
    end
    return left + right
  end
end""",
        "expected": {"big_o": "n log n", "big_omega": "n log n", "theta": "n log n"},
        "notes": "Equivalente a merge sort pero sin arrays; prueba de n log n recursivo."
    },

    {
        "name": "T(n) = 4T(n/2) + O(n) (n^2)",
        "category": "rec_master",
        "pseudocode": """FOUR_BRANCH(n)
begin
  if (n <= 1) then
  begin
    return 1
  end else
  begin
    a <- FOUR_BRANCH(n / 2)
    b <- FOUR_BRANCH(n / 2)
    c <- FOUR_BRANCH(n / 2)
    d <- FOUR_BRANCH(n / 2)
    for i <- 1 to n do
    begin
      x <- x + 1
    end
    return a + b + c + d
  end
end""",
        # a=4, b=2 => n^{log_b a} = n^{log_2 4} = n^2
        # f(n)=n = O(n^{log_b a - 1}) = O(n) => caso 1 de master => Θ(n^2)
        "expected": {"big_o": "n^2", "big_omega": "n^2", "theta": "n^2"},
        "notes": "Buen indicador de si el master theorem está bien generalizado."
    },

    {
        "name": "T(n) = T(n/2) + O(n) (lineal)",
        "category": "rec_master",
        "pseudocode": """HALF_AND_LINEAR(n)
begin
  if (n <= 1) then
  begin
    return 1
  end else
  begin
    sub <- HALF_AND_LINEAR(n / 2)
    for i <- 1 to n do
    begin
      x <- x + 1
    end
    return sub
  end
end""",
        # T(n)=T(n/2)+n => solución Θ(n)
        "expected": {"big_o": "n", "big_omega": "n", "theta": "n"},
        "notes": "Caso típico donde el trabajo fuera de la recursión domina al árbol."
    },

    # ============================================================
    # 7. RECURSIONES MIXTAS MUY TÓXICAS
    # ============================================================

    {
        "name": "T(n) = T(n-1) + T(n/2) + O(n)",
        "category": "rec_mixed",
        "pseudocode": """MIXED_REC(n)
begin
  if (n <= 1) then
  begin
    return 1
  end else
  begin
    a <- MIXED_REC(n - 1)
    b <- MIXED_REC(n / 2)
    for i <- 1 to n do
    begin
      x <- x + 1
    end
    return a + b
  end
end""",
        # Teóricamente esto crece más que n^2 y menos que 2^n (aprox),
        # pero lo ponemos como "n^2" para ver cómo se comporta el analizador.
        "expected": {"big_o": "n log n", "big_omega": "n log n", "theta": None},
        "notes": "Recurrencia híbrida difícil; es más para ver qué hace el analizador que para esperar un match exacto."
    },

    # ============================================================
    # 8. EXPONENCIALES CLÁSICOS
    # ============================================================

    {
        "name": "Fibonacci ingenuo (2^n)",
        "category": "rec_exponential",
        "pseudocode": """FIBO(n)
begin
  if (n <= 1) then
  begin
    return n
  end else
  begin
    return FIBO(n - 1) + FIBO(n - 2)
  end
end""",
        "expected": {"big_o": "2^n", "big_omega": "2^n", "theta": "2^n"},
        "notes": "Sanity check de detección exponencial."
    },

    {
        "name": "Recursión ternaria T(n) = 3T(n-1) + O(1)",
        "category": "rec_exponential",
        "pseudocode": """TERNARY(n)
begin
  if (n <= 0) then
  begin
    return 1
  end else
  begin
    return TERNARY(n - 1) + TERNARY(n - 1) + TERNARY(n - 1)
  end
end""",
        "expected": {"big_o": "3^n", "big_omega": "3^n", "theta": "3^n"},
        "notes": "Exponencial base 3; buen contraste con Fibonacci."
    },
]


# ============================================================================
# INFRA: LLAMADAS A PARSER Y ANALYZER
# ============================================================================

def parse_code(code: str) -> Dict[str, Any]:
    response = httpx.post(f"{PARSER_URL}/parse", json={"code": code}, timeout=15.0)
    response.raise_for_status()
    return response.json()


def analyze_ast(ast: Dict[str, Any]) -> Dict[str, Any]:
    response = httpx.post(
        f"{ANALYZER_URL}/analyze-ast",
        json={"ast": ast, "objective": "all", "detail": "program"},
        timeout=20.0,
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
        if test_case.get("notes"):
            print(f"Nota: {test_case['notes']}")
        print(f"{'=' * 70}")

    try:
        parse_result = parse_code(test_case["pseudocode"])
        if not parse_result.get("ok"):
            if verbose:
                print("❌ Error de parseo:")
                print(parse_result)
            return {
                "name": name,
                "category": category,
                "status": "parse_error",
                "error": parse_result,
            }

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
            "notes": test_case.get("notes", ""),
        }

        if verbose:
            print("\n📊 Resultados del analizador:")
            print(f"   Big-O:     {analysis['big_o']}")
            print(f"   Big-Ω:     {analysis['big_omega']}")
            print(f"   Θ:         {analysis.get('theta')}")
            print("\n🎯 Esperado:")
            print(f"   Big-O:     {expected.get('big_o')}")
            print(f"   Big-Ω:     {expected.get('big_omega')}")

            if matches:
                print("\n✅ CORRECTO")
            else:
                print("\n❌ INCORRECTO")
                if not o_ok:
                    print(f"   O: esperado {expected.get('big_o')}, obtenido {analysis['big_o']}")
                if not omega_ok:
                    print(f"   Ω: esperado {expected.get('big_omega')}, obtenido {analysis['big_omega']}")

        return result

    except Exception as e:
        if verbose:
            print(f"\n❌ ERROR inesperado: {e}")
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
    print("\n🧪 SUITE: EDGE CASES DEL ANALIZADOR")
    print("=" * 70)
    print(f"Total de casos: {len(EDGE_CASES)}\n")

    results: List[Dict[str, Any]] = []
    by_category: Dict[str, List[Dict[str, Any]]] = {}

    for i, test_case in enumerate(EDGE_CASES, 1):
        print(f"[{i}/{len(EDGE_CASES)}] {test_case['name']}", end=" ... ")
        result = run_test(test_case, verbose=False)
        results.append(result)

        cat = result["category"]
        by_category.setdefault(cat, []).append(result)

        if result["status"] == "success":
            print("✅")
        else:
            print(f"❌ ({result['status']})")

    print("\n" + "=" * 70)
    print("📊 RESUMEN POR CATEGORÍA")
    print("=" * 70)

    for category in sorted(by_category.keys()):
        tests = by_category[category]
        success = sum(1 for t in tests if t["status"] == "success")
        total = len(tests)
        pct = (success / total * 100) if total > 0 else 0.0

        icon_cat = "✅" if success == total else "⚠️"
        print(f"\n{icon_cat} {category.upper()}: {success}/{total} ({pct:.0f}%)")
        for t in tests:
            icon = "✅" if t["status"] == "success" else "❌"
            print(f"   {icon} {t['name']}")
            if t["status"] == "wrong_result":
                exp = t["expected"]
                act = t["actual"]
                print(f"      Esperado: O({exp.get('big_o')}), Ω({exp.get('big_omega')})")
                print(f"      Obtenido: O({act.get('big_o')}), Ω({act.get('big_omega')})")

    print("\n" + "=" * 70)
    print("🎯 RESUMEN GLOBAL")
    print("=" * 70)

    total_success = sum(1 for r in results if r["status"] == "success")
    total_tests = len(results)
    rate = (total_success / total_tests * 100.0) if total_tests > 0 else 0.0

    print(f"\n✅ Tests exitosos: {total_success}/{total_tests} ({rate:.1f}%)")

    if total_success < total_tests:
        print("\n❌ Tests fallidos:")
        for r in results:
            if r["status"] != "success":
                print(f"   - {r['name']} ({r['status']})")

    print("\n" + "=" * 70)
    return results


if __name__ == "__main__":
    main()
