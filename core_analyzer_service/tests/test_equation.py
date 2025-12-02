"""
test_equation.py - Casos que generan T(n) con constantes explícitas
=========================================================================

Objetivo:
    Forzar al analizador a producir fórmulas estilo:
        T(n) = 5n² + 3n + 7
    con términos y constantes visibles.
"""

import httpx

PARSER_URL = "http://localhost:8001"
ANALYZER_URL = "http://localhost:8002"

# ============================================================================
# CASOS CON CONSTANTES EXPLÍCITAS
# ============================================================================

CONSTANT_TEST_CASES = [
    # ========== CASO 1: CONSTANTES INICIALES ==========
    {
        "name": "Constantes iniciales: T(n) = n + 3",
        "pseudocode": (
            "begin\n"
            "  x <- 1\n"
            "  y <- 2\n"
            "  z <- 3\n"
            "  for i <- 1 to n do\n"
            "  begin\n"
            "    a <- a + 1\n"
            "  end\n"
            "end"
        ),
        "expected_pattern": "n",
        "explanation": """
        3 asignaciones iniciales (costo 3)
        + bucle de n iteraciones (costo n)
        = T(n) = n + 3
        """
    },

    # ========== CASO 2: MÚLTIPLES OPERACIONES POR ITERACIÓN ==========
    {
        "name": "Múltiples operaciones: T(n) = 3n + 2",
        "pseudocode": (
            "begin\n"
            "  x <- 0\n"
            "  y <- 0\n"
            "  for i <- 1 to n do\n"
            "  begin\n"
            "    x <- x + 1\n"
            "    y <- y + 2\n"
            "    z <- x + y\n"
            "  end\n"
            "end"
        ),
        "expected_pattern": "n",
        "explanation": """
        2 asignaciones iniciales (costo 2)
        + bucle con 3 operaciones por iteración (costo 3n)
        = T(n) = 3n + 2
        """
    },

    # ========== CASO 3: BUCLE DOBLE CON OPERACIONES ==========
    {
        "name": "Bucle doble: T(n) = 2n² + n + 1",
        "pseudocode": (
            "begin\n"
            "  s <- 0\n"
            "  for i <- 1 to n do\n"
            "  begin\n"
            "    for j <- 1 to n do\n"
            "    begin\n"
            "      s <- s + 1\n"
            "      u <- s * 2\n"
            "    end\n"
            "  end\n"
            "end"
        ),
        "expected_pattern": "n^2",
        "explanation": """
        1 asignación inicial (costo 1)
        + bucle externo n veces
          + bucle interno n veces
            + 2 operaciones (s <- s+1, u <- s*2)
        = T(n) = 2n² + 1
        """
    },

    # ========== CASO 4: INICIALIZACIÓN + BUCLE + FINALIZACIÓN ==========
    {
        "name": "Setup-Loop-Teardown: T(n) = 5n + 10",
        "pseudocode": (
            "begin\n"
            "  a <- 1\n"
            "  b <- 2\n"
            "  c <- 3\n"
            "  d <- 4\n"
            "  e <- 5\n"
            "  for i <- 1 to n do\n"
            "  begin\n"
            "    x <- a + b\n"
            "    y <- c + d\n"
            "    z <- x * y\n"
            "    w <- z - e\n"
            "    r <- w / 2\n"
            "  end\n"
            "  u <- 1\n"
            "  v <- 2\n"
            "  w <- 3\n"
            "  x <- 4\n"
            "  y <- 5\n"
            "end"
        ),
        "expected_pattern": "n",
        "explanation": """
        5 asignaciones iniciales (costo 5)
        + bucle con 5 operaciones por iteración (costo 5n)
        + 5 asignaciones finales (costo 5)
        = T(n) = 5n + 10
        """
    },

    # ========== CASO 5: BUCLE CON CONDICIONAL ==========
    {
        "name": "Bucle con if (peor caso): T(n) = 4n + 1",
        "pseudocode": (
            "begin\n"
            "  s <- 0\n"
            "  for i <- 1 to n do\n"
            "  begin\n"
            "    if (i > 5) then\n"
            "    begin\n"
            "      x <- i + 1\n"
            "      y <- i * 2\n"
            "    end else\n"
            "    begin\n"
            "      x <- i - 1\n"
            "      y <- i / 2\n"
            "    end\n"
            "  end\n"
            "end"
        ),
        "expected_pattern": "n",
        "explanation": """
        1 asignación inicial (costo 1)
        + bucle n veces
          + comparación (costo 1)
          + peor caso: 2 operaciones
        = T(n) ≈ 3n + 1
        """
    },

    # ========== CASO 6: ACCESOS A ARREGLOS ==========
    {
        "name": "Accesos a arreglo: T(n) = 2n² + n",
        "pseudocode": (
            "begin\n"
            "  for i <- 1 to n do\n"
            "  begin\n"
            "    sum <- 0\n"
            "    for j <- 1 to n do\n"
            "    begin\n"
            "      sum <- sum + A[j]\n"
            "    end\n"
            "    B[i] <- sum\n"
            "  end\n"
            "end"
        ),
        "expected_pattern": "n^2",
        "explanation": """
        Bucle externo n veces
          + asignación sum <- 0 (n veces)
          + bucle interno n veces
            + acceso A[j] y suma (2n² operaciones)
          + asignación B[i] <- sum (n veces)
        = T(n) = 2n² + 2n
        """
    },

    # ========== CASO 7: TRIPLE BUCLE CON POCAS OPERACIONES ==========
    {
        "name": "Triple bucle simple: T(n) = n³ + n² + n + 1",
        "pseudocode": (
            "begin\n"
            "  c <- 0\n"
            "  for i <- 1 to n do\n"
            "  begin\n"
            "    for j <- 1 to n do\n"
            "    begin\n"
            "      for k <- 1 to n do\n"
            "      begin\n"
            "        c <- c + 1\n"
            "      end\n"
            "    end\n"
            "  end\n"
            "end"
        ),
        "expected_pattern": "n^3",
        "explanation": """
        1 asignación inicial (costo 1)
        + triple bucle con 1 operación interna
        = T(n) = n³ + 1

        Nota: El analizador podría sumar overhead de los bucles
        """
    },

    # ========== CASO 8: BÚSQUEDA LINEAL DETALLADA ==========
    {
        "name": "Búsqueda lineal: T(n) = 3n + 3",
        "pseudocode": (
            "begin\n"
            "  i <- 1\n"
            "  encontrado <- false\n"
            "  resultado <- -1\n"
            "  while (i <= n) do\n"
            "  begin\n"
            "    if (A[i] = x) then\n"
            "    begin\n"
            "      encontrado <- true\n"
            "      resultado <- i\n"
            "    end else\n"
            "    begin\n"
            "      encontrado <- false\n"
            "    end\n"
            "    i <- i + 1\n"
            "  end\n"
            "end"
        ),
        "expected_pattern": "n",
        "explanation": """
        3 asignaciones iniciales (costo 3)
        + while hasta n iteraciones
          + comparación + condicional + asignación
        ≈ T(n) = 3n + 3
        """
    },

    # ========== CASO 9: SUMA DE MATRIZ ==========
    {
        "name": "Suma de matriz: T(n) = n² + 1",
        "pseudocode": (
            "begin\n"
            "  sum <- 0\n"
            "  for i <- 1 to n do\n"
            "  begin\n"
            "    for j <- 1 to n do\n"
            "    begin\n"
            "      sum <- sum + M[i][j]\n"
            "    end\n"
            "  end\n"
            "end"
        ),
        "expected_pattern": "n^2",
        "explanation": """
        1 asignación inicial (costo 1)
        + doble bucle con 1 operación (suma + acceso)
        = T(n) = n² + 1
        """
    },

    # ========== CASO 10: ALGORITMO CON OVERHEAD VISIBLE ==========
    {
        "name": "Overhead visible: T(n) = n² + 4n + 6",
        "pseudocode": (
            "begin\n"
            "  a <- 1\n"
            "  b <- 2\n"
            "  c <- 3\n"
            "  for i <- 1 to n do\n"
            "  begin\n"
            "    x <- a + b\n"
            "    y <- b + c\n"
            "    for j <- 1 to n do\n"
            "    begin\n"
            "      z <- x + y\n"
            "    end\n"
            "    w <- x - y\n"
            "  end\n"
            "  d <- 4\n"
            "  e <- 5\n"
            "  g <- 6\n"
            "end"
        ),
        "expected_pattern": "n^2",
        "explanation": """
        3 asignaciones iniciales (costo 3)
        + bucle externo n veces
          + 2 operaciones antes del bucle interno (2n)
          + bucle interno n² operaciones
          + 1 operación después (n)
        + 3 asignaciones finales (costo 3)
        = T(n) = n² + 3n + 6
        """
    },
]


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def parse_code(code: str):
    response = httpx.post(f"{PARSER_URL}/parse", json={"code": code}, timeout=10.0)
    response.raise_for_status()
    return response.json()


def analyze_ast(ast):
    response = httpx.post(
        f"{ANALYZER_URL}/analyze-ast",
        json={"ast": ast, "objective": "all", "detail": "line-by-line"},
        timeout=10.0,
    )
    response.raise_for_status()
    return response.json()


def run_test(test_case, verbose=True):
    name = test_case["name"]

    if verbose:
        print(f"\n{'='*70}")
        print(f"TEST: {name}")
        print(f"{'='*70}")
        print(f"💡 {test_case['explanation']}")

    try:
        # Parse
        parse_result = parse_code(test_case["pseudocode"])
        if not parse_result.get("ok"):
            print("❌ ERROR DE PARSING")
            print("   Respuesta completa del parser:", parse_result)
            detail = parse_result.get("error") or parse_result.get("errors") or "sin detalle"
            print("   Detalle:", detail)
            if "line" in parse_result or "column" in parse_result:
                print(
                    "   Línea:",
                    parse_result.get("line", "?"),
                    "Col:",
                    parse_result.get("column", "?"),
                )
            return {"status": "parse_error", "name": name}

        # Analyze
        analysis = analyze_ast(parse_result["ast"])

        if verbose:
            print(f"\n📐 RESULTADO:")
            print(f"   Big-O: {analysis['big_o']}")

            if analysis.get("strong_bounds"):
                sb = analysis["strong_bounds"]
                print(f"\n📝 FÓRMULA EXPLÍCITA:")
                print(f"   {sb.get('formula', 'N/A')}")

                if sb.get("terms"):
                    print(f"\n   Términos:")
                    for term in sb["terms"]:
                        print(f"      • {term.get('expr')} (grado: {term.get('degree')})")

                if sb.get("constant") is not None:
                    print(f"\n   Constante aditiva: {sb['constant']}")

                if sb.get("evaluated_at"):
                    print(f"\n   Evaluaciones (primeros n):")
                    items = list(sb["evaluated_at"].items())[:3]
                    for k, v in items:
                        print(f"      {k}: {v:,} operaciones")

        # Verificar patrón esperado
        pattern = test_case["expected_pattern"]
        if pattern in analysis["big_o"]:
            print(f"\n✅ CORRECTO: Contiene '{pattern}'")
            return {"status": "success", "name": name}
        else:
            print(f"\n⚠️ Esperaba '{pattern}', obtuvo '{analysis['big_o']}'")
            return {"status": "different_result", "name": name}

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "unexpected_error", "error": str(e), "name": name}


def main():
    print("\n🔢 PRUEBAS: CONSTANTES EXPLÍCITAS EN FÓRMULAS")
    print("=" * 70)
    print("Objetivo: Generar T(n) = 5n² + 3n + 7 (con constantes visibles)\n")

    results = []

    for i, test_case in enumerate(CONSTANT_TEST_CASES, 1):
        print(f"\n[{i}/{len(CONSTANT_TEST_CASES)}] {test_case['name']}")
        result = run_test(test_case, verbose=True)
        results.append(result)

        if result["status"] != "success":
            input("\nPresiona Enter para continuar...")

    # Resumen
    print(f"\n\n{'='*70}")
    print("🎯 RESUMEN")
    print(f"{'='*70}")

    success = sum(1 for r in results if r["status"] == "success")
    total = len(results)
    pct = (success / total * 100) if total > 0 else 0

    print(f"\n✅ Tests exitosos: {success}/{total} ({pct:.0f}%)")

    if success < total:
        print(f"\n⚠️  Tests con resultados diferentes o error:")
        for r in results:
            if r["status"] != "success":
                print(f"   - {r['name']} ({r['status']})")


if __name__ == "__main__":
    main()
