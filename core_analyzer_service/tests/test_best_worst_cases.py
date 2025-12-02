"""
test_best_worst_different.py - Casos donde REALMENTE O ≠ Ω (o queremos comparar casos)
===========================================================

Principalmente algoritmos donde el mejor y peor caso son DISTINTOS:
- Búsqueda lineal con salida temprana
- Insertion sort (mejor O(n), peor O(n²))
- Bubble sort optimizado
- Búsqueda con centinela
- Cocktail sort

y varios de referencia donde mejor = peor:
- Suma simple 1..n
- Máximo en arreglo
- Bucles cuadráticos (rectangular / triangular)
- Partition de QuickSort
- Selection Sort
- Búsqueda lineal sin early exit
- Bucle logarítmico (halving)
- Contar sin early exit
- Binary Search (lo medimos por peor caso, pero tu analizador también distingue mejor caso)
"""

import httpx
from typing import Dict, Any

PARSER_URL = "http://localhost:8001"
ANALYZER_URL = "http://localhost:8002"

# ============================================================================
# CASOS DONDE MEJOR ≠ PEOR (o sirven para comparar casos)
# ============================================================================

DIFFERENT_CASES = [
    # ========== BÚSQUEDA CON SALIDA TEMPRANA ==========

    {
        "name": "Búsqueda lineal (early exit explícito)",
        "category": "search_early_exit",
        "pseudocode": """begin
  idx <- 1
  found <- F
  
  while (idx <= n and found = F) do
  begin
    if (A[idx] = x) then
    begin
      found <- T
    end else
    begin
      idx <- idx + 1
    end
  end
end""",
        "expected": {
            "big_o": "n",      # Peor: recorre todo
            "big_omega": "1",  # Mejor: encuentra de inmediato
            "theta": None
        },
        "notes": "Mejor caso: encuentra en primera posición. Peor: no existe."
    },

    # ========== INSERTION SORT (clásico mejor ≠ peor) ==========

    {
        "name": "Insertion Sort (arreglo casi ordenado vs inverso)",
        "category": "sort_adaptive",
        "pseudocode": """begin
  for idx <- 2 to n do
  begin
    key <- A[idx]
    jdx <- idx - 1
    
    while (jdx >= 1 and A[jdx] > key) do
    begin
      A[jdx + 1] <- A[jdx]
      jdx <- jdx - 1
    end
    
    A[jdx + 1] <- key
  end
end""",
        "expected": {
            "big_o": "n^2",    # Peor: arreglo inverso
            "big_omega": "n",  # Mejor: ya ordenado (while casi no entra)
            "theta": None
        },
        "notes": "Mejor: O(n) si ya ordenado. Peor: O(n²) si inverso."
    },

    # ========== BUBBLE SORT CON BANDERA (early exit) ==========

    {
        "name": "Bubble Sort optimizado (con bandera)",
        "category": "sort_adaptive",
        "pseudocode": """begin
  swapped <- T
  passes <- 0
  
  while (swapped = T and passes < n) do
  begin
    swapped <- F
    
    for idx <- 1 to n - passes - 1 do
    begin
      if (A[idx] > A[idx + 1]) then
      begin
        temp <- A[idx]
        A[idx] <- A[idx + 1]
        A[idx + 1] <- temp
        swapped <- T
      end else
      begin
        temp <- temp
      end
    end
    
    passes <- passes + 1
  end
end""",
        "expected": {
            "big_o": "n^2",    # Peor: arreglo inverso
            "big_omega": "n",  # Mejor: ya ordenado (1 pasada)
            "theta": None
        },
        "notes": "Mejor: O(n) si ordenado (sale tras 1 pasada). Peor: O(n²)."
    },

    # ========== PARTITION DE QUICKSORT (siempre lineal) ==========

    {
        "name": "Partición de QuickSort (pivote variable)",
        "category": "partition",
        "pseudocode": """begin
  pivot <- A[n]
  idx <- 1
  
  for jdx <- 1 to n - 1 do
  begin
    if (A[jdx] <= pivot) then
    begin
      temp <- A[idx]
      A[idx] <- A[jdx]
      A[jdx] <- temp
      idx <- idx + 1
    end else
    begin
      temp <- temp
    end
  end
  
  temp <- A[idx]
  A[idx] <- A[n]
  A[n] <- temp
end""",
        "expected": {
            "big_o": "n",      # Siempre lineal
            "big_omega": "n",
            "theta": "n"
        },
        "notes": "Partition siempre O(n), pero QuickSort completo depende del pivote."
    },

    # ========== SELECTION SORT (siempre igual) ==========

    {
        "name": "Selection Sort (siempre O(n²))",
        "category": "sort_non_adaptive",
        "pseudocode": """begin
  for idx <- 1 to n - 1 do
  begin
    minPos <- idx
    
    for jdx <- idx + 1 to n do
    begin
      if (A[jdx] < A[minPos]) then
      begin
        minPos <- jdx
      end else
      begin
        minPos <- minPos
      end
    end
    
    if (minPos != idx) then
    begin
      temp <- A[idx]
      A[idx] <- A[minPos]
      A[minPos] <- temp
    end else
    begin
      temp <- temp
    end
  end
end""",
        "expected": {
            "big_o": "n^2",
            "big_omega": "n^2",  # NO es adaptivo
            "theta": "n^2"
        },
        "notes": "Selection NO es adaptivo: siempre O(n²)."
    },

    # ========== BÚSQUEDA CON CENTINELA (early exit) ==========

    {
        "name": "Búsqueda lineal con centinela",
        "category": "search_sentinel",
        "pseudocode": """begin
  original <- A[n]
  A[n] <- x
  idx <- 1
  
  while (A[idx] != x) do
  begin
    idx <- idx + 1
  end
  
  A[n] <- original
  
  if (idx < n or original = x) then
  begin
    result <- idx
  end else
  begin
    result <- -1
  end
end""",
        "expected": {
            "big_o": "n",
            "big_omega": "1",  # Encuentra rápido
            "theta": None
        },
        "notes": "Mejor: O(1). Peor: O(n)."
    },

    # ========== BINARY SEARCH ==========
    # (tu analizador ya lo trata con mejor y peor caso distintos,
    #  pero aquí solo exigimos O y Ω)

    {
        "name": "Binary Search (siempre logarítmico)",
        "category": "search_deterministic",
        "pseudocode": """begin
  low <- 1
  high <- n
  
  while (low <= high) do
  begin
    mid <- (low + high) div 2
    
    if (A[mid] = x) then
    begin
      low <- high + 1
    end else
    begin
      if (A[mid] < x) then
      begin
        low <- mid + 1
      end else
      begin
        high <- mid - 1
      end
    end
  end
end""",
        "expected": {
            "big_o": "log n",  # Peor caso
            "big_omega": "1",  # Mejor caso: lo encuentra en la primera comparación
            "theta": None
        },
        "notes": "Peor caso Θ(log n), mejor caso Θ(1). La mayoría de análisis clásicos reportan O(log n) como peor caso."
    },

    # ========== COUNTING OCCURRENCES (early exit posible) ==========

    {
        "name": "Contar ocurrencias (puede salir temprano)",
        "category": "counting_early_exit",
        "pseudocode": """begin
  count <- 0
  idx <- 1
  maxCount <- 5
  
  while (idx <= n and count < maxCount) do
  begin
    if (A[idx] = x) then
    begin
      count <- count + 1
    end else
    begin
      count <- count
    end
    
    idx <- idx + 1
  end
end""",
        "expected": {
            "big_o": "n",      # Peor: recorre todo
            "big_omega": "1",  # Mejor: alcanza maxCount rápido (coste constante)
            "theta": None
        },
        "notes": "Mejor: encuentra 5 elementos rápido. Peor: recorre todo."
    },

    # ========== COCKTAIL SORT (bidireccional) ==========

    {
        "name": "Cocktail Sort (burbuja bidireccional)",
        "category": "sort_bidirectional",
        "pseudocode": """begin
  swapped <- T
  start <- 1
  final <- n
  
  while (swapped = T) do
  begin
    swapped <- F
    
    for idx <- start to final - 1 do
    begin
      if (A[idx] > A[idx + 1]) then
      begin
        temp <- A[idx]
        A[idx] <- A[idx + 1]
        A[idx + 1] <- temp
        swapped <- T
      end else
      begin
        temp <- temp
      end
    end
    
    if (swapped = F) then
    begin
      swapped <- F
    end else
    begin
      final <- final - 1
      swapped <- F
      
      for jdx <- final - 1 to start step -1 do
      begin
        if (A[jdx] > A[jdx + 1]) then
        begin
          temp <- A[jdx]
          A[jdx] <- A[jdx + 1]
          A[jdx + 1] <- temp
          swapped <- T
        end else
        begin
          temp <- temp
        end
      end
      
      start <- start + 1
    end
  end
end""",
        "expected": {
            "big_o": "n^2",
            "big_omega": "n",  # Ordenado: sale rápido
            "theta": None
        },
        "notes": "Mejor: O(n) si ordenado. Peor: O(n²)."
    },

    # ========== PARTITION FINDING (early exit) ==========

    {
        "name": "Encontrar primer elemento mayor que umbral",
        "category": "threshold_search",
        "pseudocode": """begin
  idx <- 1
  found <- F
  threshold <- 100
  
  while (idx <= n and found = F) do
  begin
    if (A[idx] > threshold) then
    begin
      found <- T
      result <- idx
    end else
    begin
      idx <- idx + 1
    end
  end
end""",
        "expected": {
            "big_o": "n",
            "big_omega": "1",
            "theta": None
        },
        "notes": "Mejor: primer elemento cumple. Peor: ninguno cumple."
    },

    # =======================================================================
    # NUEVOS CASOS: MEJOR = PEOR (REFERENCIA NO ADAPTATIVA)
    # =======================================================================

    # --- Lineal: suma simple ---

    {
        "name": "Suma simple 1..n",
        "category": "linear_non_adaptive",
        "pseudocode": """begin
  sum <- 0
  for idx <- 1 to n do
  begin
    sum <- sum + A[idx]
  end
end""",
        "expected": {
            "big_o": "n",
            "big_omega": "n",
            "theta": "n"
        },
        "notes": "Recorre el arreglo una vez, sin early exit: mejor = peor = Θ(n)."
    },

    # --- Lineal: máximo en arreglo ---

    {
        "name": "Máximo en arreglo (sin early exit)",
        "category": "linear_non_adaptive",
        "pseudocode": """begin
  max <- A[1]
  idx <- 2
  
  while (idx <= n) do
  begin
    if (A[idx] > max) then
    begin
      max <- A[idx]
    end else
    begin
      max <- max
    end
    idx <- idx + 1
  end
end""",
        "expected": {
            "big_o": "n",
            "big_omega": "n",
            "theta": "n"
        },
        "notes": "Siempre recorre de 2 a n, no hay condición de parada temprana."
    },

    # --- Cuadrático: doble bucle completo ---

    {
        "name": "Doble bucle completo n x n",
        "category": "nested_non_adaptive",
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
        "expected": {
            "big_o": "n^2",
            "big_omega": "n^2",
            "theta": "n^2"
        },
        "notes": "Dos bucles 1..n anidados: Θ(n²) en todos los casos."
    },

    # --- Cuadrático: doble bucle triangular ---

    {
        "name": "Doble bucle triangular (sumatoria)",
        "category": "nested_non_adaptive",
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
        "expected": {
            "big_o": "n^2",
            "big_omega": "n^2",
            "theta": "n^2"
        },
        "notes": "Σ i = n(n+1)/2: Θ(n²) mejor, peor y promedio."
    },

    # --- Logarítmico: halving ---

    {
        "name": "Bucle logarítmico por halving",
        "category": "log_non_adaptive",
        "pseudocode": """begin
  value <- n
  
  while (value > 1) do
  begin
    value <- value div 2
  end
end""",
        "expected": {
            "big_o": "log n",
            "big_omega": "log n",
            "theta": "log n"
        },
        "notes": "value se divide por 2 en cada iteración: ~log₂(n) pasos siempre."
    },

    # --- Lineal: búsqueda sin early exit ---

    {
        "name": "Búsqueda lineal sin salida temprana",
        "category": "search_non_adaptive",
        "pseudocode": """begin
  idx <- 1
  result <- -1
  
  while (idx <= n) do
  begin
    if (A[idx] = x) then
    begin
      result <- idx      
    end else
    begin
      result <- result
    end
    idx <- idx + 1
  end
end""",
        "expected": {
            "big_o": "n",
            "big_omega": "n",
            "theta": "n"
        },
        "notes": "Aunque encuentre x, sigue recorriendo todo: mejor = peor = Θ(n)."
    },

    # --- Lineal: contar mayores que umbral SIN early exit ---

    {
        "name": "Contar mayores que umbral (sin early exit)",
        "category": "counting_non_adaptive",
        "pseudocode": """begin
  count <- 0
  idx <- 1
  threshold <- 100
  
  while (idx <= n) do
  begin
    if (A[idx] > threshold) then
    begin
      count <- count + 1
    end else
    begin
      count <- count
    end
    idx <- idx + 1
  end
end""",
        "expected": {
            "big_o": "n",
            "big_omega": "n",
            "theta": "n"
        },
        "notes": "Siempre recorre todo el arreglo: no hay condición de parada anticipada."
    },
]


# ============================================================================
# FUNCIONES DE PRUEBA
# ============================================================================

def parse_code(code: str) -> Dict[str, Any]:
    """Llama al parser service."""
    response = httpx.post(f"{PARSER_URL}/parse", json={"code": code}, timeout=30.0)
    response.raise_for_status()
    return response.json()


def analyze_ast(ast: Dict[str, Any]) -> Dict[str, Any]:
    """Llama al analyzer service."""
    response = httpx.post(
        f"{ANALYZER_URL}/analyze-ast",
        json={"ast": ast, "objective": "all", "detail": "program"},
        timeout=30.0
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
        analysis = analyze_ast(parse_result["ast"])

        # Compare
        expected = test_case.get("expected", {})

        o_match = analysis["big_o"] == expected.get("big_o", "")
        omega_match = analysis["big_omega"] == expected.get("big_omega", "")

        theta_match = True
        if expected.get("theta") is not None:
            theta_match = analysis.get("theta") == expected.get("theta")

        success = o_match and omega_match and theta_match

        result = {
            "name": name,
            "category": category,
            "status": "success" if success else "wrong_result",
            "expected": expected,
            "actual": {
                "big_o": analysis["big_o"],
                "big_omega": analysis["big_omega"],
                "theta": analysis.get("theta")
            },
            "notes": test_case.get("notes", "")
        }

        if verbose:
            print(f"\n📊 Resultados:")
            print(f"   Big-O:  {analysis['big_o']}")
            print(f"   Big-Ω:  {analysis['big_omega']}")
            print(f"   Θ:      {analysis.get('theta', 'None')}")

            print(f"\n🎯 Esperado:")
            print(f"   Big-O:  {expected.get('big_o', '?')}")
            print(f"   Big-Ω:  {expected.get('big_omega', '?')}")

            if success:
                print(f"\n✅ CORRECTO")
            else:
                print(f"\n❌ INCORRECTO")

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
    print("\n🚀 SUITE: CASOS DONDE MEJOR ≠ PEOR")
    print("="*70)
    print(f"Total de casos: {len(DIFFERENT_CASES)}\n")
    print("⚠️  NOTA: Varios de estos casos tienen mejor ≠ peor.")
    print("    Tu analizador puede o no detectar salidas tempranas todavía.\n")

    results = []
    by_category = {}

    # Ejecutar todos los tests
    for i, test_case in enumerate(DIFFERENT_CASES, 1):
        print(f"[{i}/{len(DIFFERENT_CASES)}] {test_case['name']}", end=" ... ")
        result = run_test(test_case, verbose=False)
        results.append(result)

        cat = result['category']
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(result)

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
                    exp = test['expected']
                    act = test['actual']
                    print(f"      Esperado: O({exp.get('big_o')}), Ω({exp.get('big_omega')})")
                    print(f"      Obtenido: O({act.get('big_o')}), Ω({act.get('big_omega')})")

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

    # Análisis especial
    print(f"\n\n{'='*70}")
    print("💡 ANÁLISIS")
    print(f"{'='*70}")

    adaptive_count = sum(1 for r in results if 'adaptive' in r['category'])
    print(f"\nCasos adaptativos (mejor ≠ peor teórico): {adaptive_count}")
    print("Estos casos DEBERÍAN tener O ≠ Ω; si tu analizador aún no detecta")
    print("todas las salidas tempranas, verás que reporta siempre el peor caso en algunos.")

    print("\n" + "="*70)

    return results


if __name__ == "__main__":
    main()
