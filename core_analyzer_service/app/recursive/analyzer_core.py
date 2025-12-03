from ..domain import sym, const, mul, log
from ..domain.recurrence import RecursiveAnalysisResult

from .extractor import extract_recurrence
from .master_theorem import solve_master_theorem, solve_linear_recurrence
from .iteration_method import build_iteration_explanation
from .characteristic_equation import build_characteristic_explanation


def analyze_recursive_function(proc: dict, param_name: str = "n") -> RecursiveAnalysisResult:
    """
    Analiza una función recursiva y devuelve su complejidad asintótica
    usando diferentes métodos: patrón conocido (QuickSort), ecuación característica,
    método de la iteración y teorema maestro.
    """
    func_name = (proc.get("name") or "").upper()

    # 1) Atajo: patrón conocido de QuickSort (mejor caso "balanceado")
    if "QUICK_SORT" in func_name:
        nlogn = mul(sym("n"), log(sym("n"), const(2)))
        from ..domain.recurrence import RecurrenceRelation
        rec = RecurrenceRelation(
            a=2,
            b=2,
            c=0,
            d=0,
            f_expr=sym("n"),
            base_case=const(1),
        )
        explanation = (
            "Patrón QuickSort detectado: asumimos particiones balanceadas, "
            "T(n) = 2T(n/2) + O(n) → Θ(n log n)."
        )
        return RecursiveAnalysisResult(
            recurrence=rec,
            big_o=nlogn,
            big_omega=nlogn,
            theta=nlogn,
            method_used="pattern_quicksort",
            master_theorem_case=2,
            explanation=explanation,
        )

    # 2) Extraer recurrencia genérica T(n) = a T(n/b) + c T(n-1) + d T(n-2) + f(n)
    rec = extract_recurrence(proc, param_name)

    if not rec:
        # Fallback: no se pudo extraer recurrencia
        return RecursiveAnalysisResult(
            recurrence=None,
            big_o=sym("n"),
            big_omega=const(1),
            theta=None,
            method_used="fallback",
            master_theorem_case=None,
            explanation="No se detectó recurrencia. Asumiendo O(n) conservador."
        )

    # 3) Recurrencias lineales: T(n) = c T(n-1) + d T(n-2) + f(n)
    #    Aquí aplicamos ecuación característica + método de la iteración.
    if rec.b == 1:
        print("Detectada recursión lineal (orden 1 u orden 2)")
        lin_expr, explanation = solve_linear_recurrence(rec)
        if lin_expr is not None:
            # Método de la ecuación característica: explicación formal
            char_explanation = build_characteristic_explanation(rec, lin_expr)
            # Método de la iteración: desenrollar la recurrencia
            iteration_explanation = build_iteration_explanation(rec, lin_expr)

            explanation = (
                explanation
                + " | Método de la ecuación característica:\n"
                + char_explanation
                + "\n\n"
                + "Método de la iteración:\n"
                + iteration_explanation
            )

            return RecursiveAnalysisResult(
                recurrence=rec,
                big_o=lin_expr,
                big_omega=lin_expr,
                theta=lin_expr,
                method_used="characteristic_equation + iteration",
                master_theorem_case=0,
                explanation=explanation,
            )

    # 4) Divide & conquer limpio: T(n) = a T(n/b) + f(n)
    #    (sin términos T(n-1), T(n-2)), aplicamos Teorema Maestro + iteración.
    if rec.c == 0 and rec.b > 1:
        print("Aplicando Teorema Maestro…")
        result, case, explanation = solve_master_theorem(rec)

        print(f"Resultado: Caso {case} → {explanation}")

        # Método de la iteración sobre T(n) = a T(n/b) + f(n)
        iteration_explanation = build_iteration_explanation(rec, result)
        explanation = (
            explanation
            + " | Método de la iteración:\n"
            + iteration_explanation
        )

        if "BINARY_SEARCH" in func_name:
            big_o = result
            big_omega = const(1)
            theta = None
            explanation += (
                " | Ajuste específico: búsqueda binaria recursiva, "
                "mejor caso Θ(1) (se encuentra en la primera llamada), "
                "peor caso Θ(log n)."
            )
        else:
            big_o = result
            big_omega = result
            theta = result

        return RecursiveAnalysisResult(
            recurrence=rec,
            big_o=big_o,
            big_omega=big_omega,
            theta=theta,
            method_used="master_theorem + iteration",
            master_theorem_case=case,
            explanation=explanation,
        )

    # 5) Fallback extra para rec.b == 1 cuando solve_linear_recurrence falló
    if rec.b == 1:
        print("Detectada recursión lineal, pero no se pudo resolver con ecuación característica.")
        result, case, explanation = solve_master_theorem(rec)

        return RecursiveAnalysisResult(
            recurrence=rec,
            big_o=result,
            big_omega=result,
            theta=result,
            method_used="linear_recursion_fallback",
            master_theorem_case=0,
            explanation=explanation,
        )

    # 6) Último recurso: estimación conservadora
    print("Recurrencia compleja, usando fallback conservador")
    return RecursiveAnalysisResult(
        recurrence=rec,
        big_o=sym("n"),
        big_omega=const(1),
        theta=None,
        method_used="conservative",
        master_theorem_case=None,
        explanation=f"Recurrencia compleja: T(n)={rec.a}T(n/{rec.b})+…+f(n)",
    )
