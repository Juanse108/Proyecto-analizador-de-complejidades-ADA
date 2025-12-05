"""Generación de tablas de seguimiento de ejecución de algoritmos iterativos.

Este módulo simula la ejecución del pseudocódigo paso a paso, registrando:
- Estado de variables en cada iteración
- Condiciones evaluadas
- Operaciones ejecutadas
- Costo acumulado en cada paso

Es el equivalente al árbol de recursión, pero para algoritmos iterativos.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass


@dataclass
class TraceStep:
    """Representa un paso en la traza de ejecución.
    
    Atributos:
        step: Número de paso (0, 1, 2, ...)
        line: Línea de código ejecutada
        kind: Tipo de sentencia (assign, for, while, if, etc.)
        condition: Condición evaluada (para bucles/ifs)
        variables: Estado de las variables en este punto
        operation: Operación realizada
        cost: Costo de este paso
        cumulative_cost: Costo acumulado hasta este paso
    """
    step: int
    line: int
    kind: str
    condition: Optional[str] = None
    variables: Dict[str, Any] = None
    operation: str = ""
    cost: str = "1"
    cumulative_cost: str = "1"
    
    def __post_init__(self):
        if self.variables is None:
            self.variables = {}


@dataclass
class ExecutionTrace:
    """Resultado completo de la traza de ejecución.
    
    Atributos:
        steps: Lista de pasos de la ejecución
        total_iterations: Total de iteraciones del algoritmo
        max_depth: Profundidad máxima de anidamiento alcanzada
        variables_tracked: Variables rastreadas durante la ejecución
        complexity_formula: Fórmula de complejidad derivada de la traza
        description: Descripción textual de la traza
    """
    steps: List[TraceStep]
    total_iterations: int
    max_depth: int
    variables_tracked: List[str]
    complexity_formula: str
    description: str = ""


def generate_trace_for_simple_loop(
    ast: dict,
    param_name: str = "n"
) -> ExecutionTrace:
    """Genera una traza de ejecución para un bucle simple.
    
    Maneja bucles for (for i = 1 to n) y while.
    
    Args:
        ast: Árbol de sintaxis abstracta del programa
        param_name: Nombre del parámetro que representa el tamaño
        
    Returns:
        ExecutionTrace con los pasos de ejecución simulados
    """
    # Buscar el primer bucle (for o while) en el AST
    loop_stmt, loop_kind = _find_first_loop(ast)
    
    if not loop_stmt or not loop_kind:
        return _generate_trace_fallback(ast, param_name)
    
    if loop_kind == "while":
        return _generate_trace_for_while_loop(ast, param_name)
    
    # Generar pasos de ejemplo con n=5
    n_value = 5
    steps: List[TraceStep] = []
    
    # Paso 0: Inicialización
    steps.append(TraceStep(
        step=0,
        line=1,
        kind="init",
        condition=None,
        variables={param_name: n_value},
        operation=f"Inicializar {param_name}={n_value}",
        cost="1",
        cumulative_cost="1"
    ))
    
    # Pasos 1..n: Iteraciones del bucle FOR
    var_name = _extract_loop_var(loop_stmt)
    start = _extract_loop_start(loop_stmt)
    end_expr = _extract_loop_end(loop_stmt)
    
    cumulative = 1
    for i in range(start, n_value + 1):
        step_num = i - start + 1
        condition = f"{var_name} ≤ {param_name}"
        
        steps.append(TraceStep(
            step=step_num,
            line=2,
            kind="for",
            condition=condition,
            variables={var_name: i, param_name: n_value},
            operation=f"Ejecutar cuerpo del bucle (iteración {i})",
            cost="1",
            cumulative_cost=str(cumulative + 1)
        ))
        cumulative += 1
    
    # Paso final: Salida del bucle
    steps.append(TraceStep(
        step=len(steps),
        line=3,
        kind="exit",
        condition=f"{var_name} > {param_name}",
        variables={var_name: n_value + 1, param_name: n_value},
        operation="Salir del bucle",
        cost="0",
        cumulative_cost=str(cumulative)
    ))
    
    return ExecutionTrace(
        steps=steps,
        total_iterations=n_value,
        max_depth=1,
        variables_tracked=[param_name, var_name],
        complexity_formula=f"O({param_name})",
        description=f"Bucle simple que ejecuta {param_name} iteraciones. Cada iteración realiza operaciones O(1)."
    )


def generate_trace_for_nested_loops(
    ast: dict,
    param_name: str = "n"
) -> ExecutionTrace:
    """
    Genera una traza de ejecución para bucles anidados.
    
    Para bucles como:
        for i = 1 to n:
            for j = 1 to n:
                operations
    
    Genera una tabla mostrando todas las combinaciones (i, j).
    """
    n_value = 4  # Valor pequeño para visualizar
    steps: List[TraceStep] = []
    
    # Paso 0: Inicialización
    steps.append(TraceStep(
        step=0,
        line=1,
        kind="init",
        condition=None,
        variables={param_name: n_value},
        operation=f"Inicializar {param_name}={n_value}",
        cost="1",
        cumulative_cost="1"
    ))
    
    cumulative = 1
    step_num = 1
    
    # Bucle externo
    for i in range(1, n_value + 1):
        # Inicio de iteración externa
        steps.append(TraceStep(
            step=step_num,
            line=2,
            kind="for_outer",
            condition=f"i ≤ {param_name}",
            variables={"i": i, param_name: n_value},
            operation=f"Iteración externa i={i}",
            cost="1",
            cumulative_cost=str(cumulative + 1)
        ))
        cumulative += 1
        step_num += 1
        
        # Bucle interno
        for j in range(1, n_value + 1):
            steps.append(TraceStep(
                step=step_num,
                line=3,
                kind="for_inner",
                condition=f"j ≤ {param_name}",
                variables={"i": i, "j": j, param_name: n_value},
                operation=f"Operación en (i={i}, j={j})",
                cost="1",
                cumulative_cost=str(cumulative + 1)
            ))
            cumulative += 1
            step_num += 1
    
    return ExecutionTrace(
        steps=steps,
        total_iterations=n_value * n_value,
        max_depth=2,
        variables_tracked=[param_name, "i", "j"],
        complexity_formula=f"O({param_name}²)",
        description=f"Bucles anidados: el bucle externo ejecuta {param_name} veces, "
                   f"y el interno {param_name} veces por cada iteración externa, "
                   f"resultando en {param_name}² operaciones totales."
    )


def generate_trace_for_binary_search(
    ast: dict,
    param_name: str = "n"
) -> ExecutionTrace:
    """
    Genera una traza de ejecución para búsqueda binaria iterativa.
    
    Muestra cómo se reduce el espacio de búsqueda en cada iteración.
    """
    n_value = 16  # Potencia de 2 para visualizar mejor
    steps: List[TraceStep] = []
    
    # Paso 0: Inicialización
    left, right = 0, n_value - 1
    steps.append(TraceStep(
        step=0,
        line=1,
        kind="init",
        condition=None,
        variables={param_name: n_value, "left": left, "right": right},
        operation=f"Inicializar búsqueda: left=0, right={n_value-1}",
        cost="1",
        cumulative_cost="1"
    ))
    
    cumulative = 1
    step_num = 1
    
    # Simular búsqueda binaria
    while left <= right:
        mid = (left + right) // 2
        search_space = right - left + 1
        
        steps.append(TraceStep(
            step=step_num,
            line=2,
            kind="while",
            condition=f"left ≤ right",
            variables={
                param_name: n_value,
                "left": left,
                "right": right,
                "mid": mid,
                "space": search_space
            },
            operation=f"Calcular mid={mid}, espacio de búsqueda={search_space}",
            cost="1",
            cumulative_cost=str(cumulative + 1)
        ))
        cumulative += 1
        step_num += 1
        
        # Simular comparación (asumimos que no encontramos el elemento)
        # y ajustamos left o right
        if step_num % 2 == 0:
            right = mid - 1
        else:
            left = mid + 1
    
    import math
    iterations = math.ceil(math.log2(n_value)) if n_value > 0 else 0
    
    return ExecutionTrace(
        steps=steps,
        total_iterations=iterations,
        max_depth=1,
        variables_tracked=[param_name, "left", "right", "mid"],
        complexity_formula=f"O(log {param_name})",
        description=f"Búsqueda binaria: en cada iteración se divide el espacio de búsqueda "
                   f"a la mitad. Con {param_name}={n_value} elementos, se requieren "
                   f"aproximadamente log₂({n_value}) ≈ {iterations} iteraciones."
    )


def generate_execution_trace(
    ast: dict,
    complexity_hint: str = "",
    param_name: str = "n"
) -> ExecutionTrace:
    """
    Punto de entrada principal para generar trazas de ejecución.
    
    Detecta automáticamente el tipo de algoritmo y genera la traza apropiada.
    
    Args:
        ast: AST del programa
        complexity_hint: Pista sobre la complejidad (O(n), O(n²), O(log n), etc.)
        param_name: Nombre del parámetro principal (por defecto "n")
    
    Returns:
        ExecutionTrace con los pasos de ejecución simulados
    """
    hint = complexity_hint.lower().replace(" ", "")
    
    # Detectar tipo de algoritmo por la complejidad
    if "log" in hint and "n" in hint and "n^2" not in hint and "n²" not in hint:
        return generate_trace_for_binary_search(ast, param_name)
    elif "n^2" in hint or "n²" in hint or "n*n" in hint:
        return generate_trace_for_nested_loops(ast, param_name)
    elif "n" in hint:
        return generate_trace_for_simple_loop(ast, param_name)
    else:
        return _generate_trace_fallback(ast, param_name)


def _extract_loop_var(for_stmt: dict) -> str:
    """Extrae el nombre de la variable del bucle for."""
    var = for_stmt.get("var", {})
    return var.get("name", "i") if isinstance(var, dict) else "i"


def _extract_loop_start(for_stmt: dict) -> int:
    """Extrae el valor inicial del bucle."""
    from_expr = for_stmt.get("from", {})
    if isinstance(from_expr, dict) and from_expr.get("kind") == "number":
        return from_expr.get("value", 1)
    return 1


def _extract_loop_end(for_stmt: dict) -> str:
    """Extrae la expresión final del bucle."""
    to_expr = for_stmt.get("to", {})
    if isinstance(to_expr, dict):
        if to_expr.get("kind") == "number":
            return str(to_expr.get("value", "n"))
        elif to_expr.get("kind") == "var":
            return to_expr.get("name", "n")
    return "n"


def _find_first_loop(ast: dict) -> tuple[dict | None, str | None]:
    """Busca el primer bucle (for o while) en el AST.
    
    Returns:
        Tupla (loop_stmt, loop_kind) donde loop_kind es 'for' o 'while'
    """
    def search_recursive(node):
        if isinstance(node, dict):
            kind = node.get("kind")
            if kind == "for":
                return node, "for"
            elif kind == "while":
                return node, "while"
            
            # Buscar en valores del diccionario
            for value in node.values():
                result = search_recursive(value)
                if result[0]:
                    return result
        
        elif isinstance(node, list):
            for item in node:
                result = search_recursive(item)
                if result[0]:
                    return result
        
        return None, None
    
    return search_recursive(ast)


def _generate_trace_for_while_loop(ast: dict, param_name: str) -> ExecutionTrace:
    """Genera traza específica para bucles while como LinearSearch."""
    n_value = 5  # Tamaño de ejemplo
    steps: List[TraceStep] = []
    
    # Paso 0: Inicialización
    steps.append(TraceStep(
        step=0,
        line=1,
        kind="init",
        condition=None,
        variables={param_name: n_value, "i": 1, "found": "F"},
        operation=f"Inicializar i=1, found=F, {param_name}={n_value}",
        cost="1",
        cumulative_cost="1"
    ))
    
    cumulative = 1
    
    # Simular iteraciones del while (peor caso: recorrer todo el arreglo)
    for i in range(1, n_value + 1):
        condition = f"i ≤ {param_name} and found = F"
        
        steps.append(TraceStep(
            step=i,
            line=2,
            kind="while",
            condition=condition,
            variables={"i": i, "found": "F", param_name: n_value},
            operation=f"Comparar A[{i}] con x",
            cost="1",
            cumulative_cost=str(cumulative + 1)
        ))
        cumulative += 1
    
    # Paso final: Encontrar elemento en la última posición
    steps.append(TraceStep(
        step=n_value + 1,
        line=3,
        kind="assign",
        condition=None,
        variables={"i": n_value, "found": "T", param_name: n_value},
        operation="Elemento encontrado: found <- T",
        cost="1",
        cumulative_cost=str(cumulative + 1)
    ))
    cumulative += 1
    
    # Paso de salida
    steps.append(TraceStep(
        step=n_value + 2,
        line=4,
        kind="exit",
        condition="i > n or found = T",
        variables={"i": n_value, "found": "T", param_name: n_value},
        operation="Salir del bucle while",
        cost="0",
        cumulative_cost=str(cumulative)
    ))
    
    return ExecutionTrace(
        steps=steps,
        total_iterations=n_value,
        max_depth=1,
        variables_tracked=[param_name, "i", "found"],
        complexity_formula=f"O({param_name})",
        description=f"Búsqueda lineal con bucle while: en el peor caso, recorre los {param_name} elementos hasta encontrar el objetivo en la última posición."
    )


def _generate_trace_fallback(ast: dict, param_name: str) -> ExecutionTrace:
    """Genera una traza genérica cuando no se puede analizar específicamente."""
    return ExecutionTrace(
        steps=[
            TraceStep(
                step=0,
                line=1,
                kind="unknown",
                condition=None,
                variables={param_name: "n"},
                operation="Análisis de traza no disponible para este algoritmo",
                cost="?",
                cumulative_cost="?"
            )
        ],
        total_iterations=0,
        max_depth=0,
        variables_tracked=[param_name],
        complexity_formula="O(?)",
        description="No se pudo generar una traza de ejecución detallada para este algoritmo."
    )
