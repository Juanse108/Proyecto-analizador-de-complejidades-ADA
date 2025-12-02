from ..domain import Expr, sym, const, mul, log
from ..domain.recurrence import RecursiveAnalysisResult

from .extractor import extract_recurrence
from .master_theorem import solve_master_theorem, solve_linear_recurrence


def analyze_recursive_function(proc: dict, param_name: str = "n") -> RecursiveAnalysisResult:
    func_name = (proc.get("name") or "").upper()

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

    rec = extract_recurrence(proc, param_name)

    if not rec:
        print("No se pudo extraer recurrencia, usando fallback")
        return RecursiveAnalysisResult(
            recurrence=None,
            big_o=sym("n"),
            big_omega=const(1),
            theta=None,
            method_used="fallback",
            master_theorem_case=None,
            explanation="No se detectó recurrencia. Asumiendo O(n) conservador."
        )

    if rec.b == 1:
        print("Detectada recursión lineal (orden 1 u orden 2)")
        lin_expr, explanation = solve_linear_recurrence(rec)
        if lin_expr is not None:
            return RecursiveAnalysisResult(
                recurrence=rec,
                big_o=lin_expr,
                big_omega=lin_expr,
                theta=lin_expr,
                method_used="linear_recurrence",
                master_theorem_case=0,
                explanation=explanation
            )

    if rec.c == 0 and rec.b > 1:
        print(f"Aplicando Teorema Maestro...")
        result, case, explanation = solve_master_theorem(rec)

        print(f"Resultado: Caso {case} → {explanation}")

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
            method_used="master_theorem",
            master_theorem_case=case,
            explanation=explanation
        )

    if rec.b == 1:
        print(f"Detectada recursión lineal")
        result, case, explanation = solve_master_theorem(rec)

        return RecursiveAnalysisResult(
            recurrence=rec,
            big_o=result,
            big_omega=result,
            theta=result,
            method_used="linear_recursion",
            master_theorem_case=0,
            explanation=explanation
        )

    print(f"Recurrencia compleja, usando fallback conservador")
    return RecursiveAnalysisResult(
        recurrence=rec,
        big_o=sym("n"),
        big_omega=const(1),
        theta=None,
        method_used="conservative",
        master_theorem_case=None,
        explanation=f"Recurrencia compleja: T(n)={rec.a}T(n/{rec.b})+...+f(n)"
    )