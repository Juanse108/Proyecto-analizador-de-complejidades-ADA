from .equation_formatter import get_recurrence_description
from ..domain import sym, const, mul, log
from ..domain.recurrence import RecursiveAnalysisResult

from .extractor import extract_recurrence
from .master_theorem import solve_master_theorem, solve_linear_recurrence
from .iteration_method import build_iteration_explanation
from .characteristic_equation import build_characteristic_explanation


def analyze_recursive_function(proc: dict, param_name: str = "n") -> RecursiveAnalysisResult:
    """Analiza una función recursiva y determina su complejidad asintótica.
    
    Utiliza diferentes métodos según el tipo de recurrencia:
    - Patrones conocidos (QuickSort)
    - Ecuación característica para recurrencias lineales
    - Método de la iteración
    - Teorema Maestro para divide y vencerás
    
    Args:
        proc: Diccionario representando el procedimiento recursivo
        param_name: Nombre del parámetro que representa el tamaño (por defecto: "n")
        
    Returns:
        Resultado del análisis incluyendo big-O, big-Ω, Θ y explicación
    """
    func_name = (proc.get("name") or "").upper()

    if "QUICK" in func_name and "SORT" in func_name:
        nlogn = mul(sym("n"), log(sym("n"), const(2)))
        n_squared = mul(sym("n"), sym("n"))
        
        from ..domain.recurrence import RecurrenceRelation
        
        rec_worst = RecurrenceRelation(
            a=1,
            b=1,
            c=0,
            d=0,
            f_expr=sym("n"),
            base_case=const(1),
        )
        rec_worst.equation_text = (
            "Peor caso (pivote desbalanceado):\n"
            "T(n) = T(n-1) + c·n,  n > 1\n"
            "T(1) = d"
        )
        
        rec_best = RecurrenceRelation(
            a=2,
            b=2,
            c=0,
            d=0,
            f_expr=sym("n"),
            base_case=const(1),
        )
        rec_best.equation_text = (
            "Mejor/Promedio caso (pivote balanceado):\n"
            "T(n) = 2·T(n/2) + c·n,  n > 1\n"
            "T(1) = d"
        )
        
        explanation = (
            "QuickSort tiene complejidad dependiente del caso:\n\n"
            f"{rec_worst.equation_text}\n"
            "Solución asintótica (peor caso): Θ(n²)\n\n"
            f"{rec_best.equation_text}\n"
            "Solución asintótica (mejor/promedio): Θ(n log n)\n\n"
            "El peor caso ocurre cuando el pivote siempre es el menor/mayor elemento, generando una partición desbalanceada.\n"
            "El caso promedio asume particiones razonablemente balanceadas, comportándose como Divide y Vencerás."
        )
        
        return RecursiveAnalysisResult(
            recurrence=rec_worst,
            big_o=n_squared,
            big_omega=nlogn,
            theta=nlogn,
            method_used="case_based_analysis",
            master_theorem_case=None,
            explanation=explanation,
            recurrence_equation=f"{rec_worst.equation_text}\n\n{rec_best.equation_text}",
        )

    rec = extract_recurrence(proc, param_name)

    if not rec:
        return RecursiveAnalysisResult(
            recurrence=None,
            big_o=sym("n"),
            big_omega=const(1),
            theta=None,
            method_used="fallback",
            master_theorem_case=None,
            explanation="No se detectó recurrencia. Asumiendo O(n) conservador.",
            recurrence_equation="No se pudo inferir una ecuación de recurrencia precisa a partir del código."
        )

    if rec.b == 1:
        lin_expr, explanation = solve_linear_recurrence(rec)
        if lin_expr is not None:
            char_explanation = build_characteristic_explanation(rec, lin_expr)
            iteration_explanation = build_iteration_explanation(rec, lin_expr)

            full_explanation = (
                f"Tipo: {get_recurrence_description(rec)}\n\n"
                f"Recurrencia:\n{rec.equation_text}\n\n"
                f"{explanation}\n\n"
                f"Método de la ecuación característica:\n{char_explanation}\n\n"
                f"Método de la iteración:\n{iteration_explanation}"
            )

            return RecursiveAnalysisResult(
                recurrence=rec,
                big_o=lin_expr,
                big_omega=lin_expr,
                theta=lin_expr,
                method_used="characteristic_equation + iteration",
                master_theorem_case=0,
                explanation=full_explanation,
                recurrence_equation=rec.equation_text,
            )
        
    if rec.c == 0 and rec.b > 1:
        result, case, explanation = solve_master_theorem(rec)

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
            recurrence_equation=rec.equation_text,
        )

    if rec.b == 1:
        result, case, explanation = solve_master_theorem(rec)
        
        equation_text = rec.equation_text if hasattr(rec, 'equation_text') and rec.equation_text else \
                       "No se pudo generar la ecuación de recurrencia con precisión."

        return RecursiveAnalysisResult(
            recurrence=rec,
            big_o=result,
            big_omega=result,
            theta=result,
            method_used="linear_recursion_fallback",
            master_theorem_case=0,
            explanation=explanation,
            recurrence_equation=equation_text
        )

    equation_text = rec.equation_text if hasattr(rec, 'equation_text') and rec.equation_text else \
                   "No se pudo generar la ecuación de recurrencia con precisión."
    
    return RecursiveAnalysisResult(
        recurrence=rec,
        big_o=sym("n"),
        big_omega=const(1),
        theta=None,
        method_used="conservative",
        master_theorem_case=None,
        explanation=f"Recurrencia compleja: T(n)={rec.a}T(n/{rec.b})+…+f(n)",
        recurrence_equation=equation_text
    )
