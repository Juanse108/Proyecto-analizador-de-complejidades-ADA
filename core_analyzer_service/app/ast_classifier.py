# core_analyzer_service/app/ast_classifier.py
"""
ast_classifier.py - Clasificación de algoritmos iterativos/recursivos
=====================================================================

ARREGLADO: Ahora detecta funcall en TODAS las expresiones, incluyendo
condiciones de if y asignaciones anidadas.
"""

from typing import Dict, Set, List
from .schemas import ProgramMetadata, FunctionMetadata


def _build_call_graph(ast: dict) -> Dict[str, Set[str]]:
    """
    Construye el grafo de llamadas del programa.

    CORREGIDO: Busca exhaustivamente en todas las expresiones.
    """
    call_graph: Dict[str, Set[str]] = {}

    def _extract_calls_from_expr(expr) -> Set[str]:
        """
        Extrae llamadas dentro de expresiones (recursivo profundo).
        """
        calls: Set[str] = set()

        if not isinstance(expr, dict):
            return calls

        kind = expr.get("kind")

        # ✅ Llamada dentro de expresión (funcall)
        if kind == "funcall":
            calls.add(expr.get("name", ""))
            # También buscar en argumentos (llamadas anidadas)
            for arg in expr.get("args", []):
                calls.update(_extract_calls_from_expr(arg))

        # Operadores binarios
        elif kind == "binop":
            calls.update(_extract_calls_from_expr(expr.get("left")))
            calls.update(_extract_calls_from_expr(expr.get("right")))

        # Operadores unarios
        elif kind == "unop":
            calls.update(_extract_calls_from_expr(expr.get("expr")))

        # Variables con índices pueden contener llamadas
        elif kind == "index":
            calls.update(_extract_calls_from_expr(expr.get("base")))
            calls.update(_extract_calls_from_expr(expr.get("index")))

        return calls

    def _extract_calls_from_body(body: List[dict]) -> Set[str]:
        """Extrae nombres de funciones llamadas en un cuerpo de sentencias."""
        calls: Set[str] = set()

        for stmt in body:
            if not isinstance(stmt, dict):
                continue

            kind = stmt.get("kind")

            # ✅ Llamada explícita: CALL nombre(args)
            if kind == "call":
                calls.add(stmt.get("name", ""))
                # Buscar llamadas en argumentos
                for arg in stmt.get("args", []):
                    calls.update(_extract_calls_from_expr(arg))

            # ✅ Asignación: puede contener funcall
            elif kind == "assign":
                expr = stmt.get("expr")
                if expr:
                    calls.update(_extract_calls_from_expr(expr))

            # ✅ If: buscar en CONDICIÓN + cuerpos
            elif kind == "if":
                # ⚠️ CRÍTICO: También buscar en la condición
                cond = stmt.get("cond")
                if cond:
                    calls.update(_extract_calls_from_expr(cond))

                calls.update(_extract_calls_from_body(stmt.get("then_body", [])))
                if stmt.get("else_body"):
                    calls.update(_extract_calls_from_body(stmt["else_body"]))

            # ✅ While/Repeat: buscar en condición + cuerpo
            elif kind == "while":
                cond = stmt.get("cond")
                if cond:
                    calls.update(_extract_calls_from_expr(cond))
                calls.update(_extract_calls_from_body(stmt.get("body", [])))

            elif kind == "repeat":
                calls.update(_extract_calls_from_body(stmt.get("body", [])))
                until = stmt.get("until")
                if until:
                    calls.update(_extract_calls_from_expr(until))

            # For
            elif kind == "for":
                # Buscar en límites del for (raramente tienen llamadas, pero...)
                start = stmt.get("start")
                end = stmt.get("end")
                if start:
                    calls.update(_extract_calls_from_expr(start))
                if end:
                    calls.update(_extract_calls_from_expr(end))

                calls.update(_extract_calls_from_body(stmt.get("body", [])))

            # Block
            elif kind == "block":
                calls.update(_extract_calls_from_body(stmt.get("stmts", [])))

        return calls

    # Extraer todas las funciones/procedimientos del programa
    body = ast.get("body", [])

    for item in body:
        if not isinstance(item, dict):
            continue

        # Es un procedimiento/función
        if item.get("kind") == "proc":
            name = item.get("name", "")
            proc_body = item.get("body", [])
            call_graph[name] = _extract_calls_from_body(proc_body)

    return call_graph


def _find_recursive_functions(call_graph: Dict[str, Set[str]]) -> Set[str]:
    """
    Detecta qué funciones son recursivas (directa o indirectamente).

    Usa DFS para encontrar ciclos en el grafo de llamadas.
    """
    recursive: Set[str] = set()

    def _dfs(func: str, path: Set[str]) -> None:
        """DFS para detectar ciclos."""
        if func in path:
            # Ciclo encontrado: todas las funciones en el camino son recursivas
            recursive.update(path)
            return

        if func not in call_graph:
            return

        path.add(func)
        for called in call_graph[func]:
            _dfs(called, path.copy())

    for func in call_graph:
        _dfs(func, set())

    return recursive


def classify_algorithm(ast: dict) -> ProgramMetadata:
    """
    Clasifica un programa según su estructura de llamadas.

    Pasos:
    1. Construir el grafo de llamadas entre funciones.
    2. Detectar funciones recursivas (directa o indirectamente).
    3. Clasificar el programa como:
       - "iterative": ninguna función es recursiva.
       - "recursive": al menos una función es recursiva.
       - "mixed": tiene funciones recursivas y no recursivas (raro, futuro).
    """
    call_graph = _build_call_graph(ast)
    recursive_funcs = _find_recursive_functions(call_graph)

    # 🔍 DEBUG
    print(f"\n🔍 CLASIFICADOR:")
    print(f"   Grafo de llamadas: {call_graph}")
    print(f"   Funciones recursivas: {recursive_funcs}")

    # Construir metadatos por función
    functions_meta: Dict[str, FunctionMetadata] = {}

    for func_name, calls in call_graph.items():
        functions_meta[func_name] = FunctionMetadata(
            name=func_name,
            is_recursive=(func_name in recursive_funcs),
            calls=list(calls),
        )

    # Determinar clasificación global
    if not recursive_funcs:
        algorithm_kind = "iterative"
    elif len(recursive_funcs) == len(call_graph):
        algorithm_kind = "recursive"
    else:
        algorithm_kind = "mixed"

    print(f"   Clasificación: {algorithm_kind}")

    return ProgramMetadata(
        algorithm_kind=algorithm_kind,
        functions=functions_meta,
    )


def has_main_block(ast: dict) -> bool:
    """
    Verifica si el programa tiene un bloque principal (begin...end) sin procedimientos.
    """
    body = ast.get("body", [])

    for item in body:
        if not isinstance(item, dict):
            continue
        if item.get("kind") != "proc":
            return True

    return False