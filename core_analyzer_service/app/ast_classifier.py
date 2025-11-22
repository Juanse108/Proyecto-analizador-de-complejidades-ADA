"""
ast_classifier.py - Clasificación de algoritmos iterativos/recursivos
=====================================================================

Analiza el AST para determinar:
- Qué funciones son recursivas (directa o indirectamente).
- Si el programa es iterativo, recursivo o mixto.

Este módulo NO calcula complejidades, solo clasifica estructuras.
"""

from typing import Dict, Set, List
from .schemas import ProgramMetadata, FunctionMetadata


def _build_call_graph(ast: dict) -> Dict[str, Set[str]]:
    """
    Construye el grafo de llamadas del programa.

    Args:
        ast: AST del programa (puede ser "program" con body de procs/stmts).

    Returns:
        Diccionario donde cada clave es un nombre de función y el valor
        es el conjunto de funciones que llama.

    Ejemplo:
        {"factorial": {"factorial", "print"}, "main": {"factorial"}}
    """
    call_graph: Dict[str, Set[str]] = {}

    def _extract_calls_from_body(body: List[dict]) -> Set[str]:
        """Extrae nombres de funciones llamadas en un cuerpo de sentencias."""
        calls: Set[str] = set()

        for stmt in body:
            if not isinstance(stmt, dict):
                continue

            kind = stmt.get("kind")

            # Llamada explícita a procedimiento: call nombre(args)
            if kind == "call":
                calls.add(stmt.get("name", ""))

            # For/While/If: recursivamente buscar en sus cuerpos
            elif kind == "for":
                calls.update(_extract_calls_from_body(stmt.get("body", [])))
            elif kind == "while":
                calls.update(_extract_calls_from_body(stmt.get("body", [])))
            elif kind == "if":
                calls.update(_extract_calls_from_body(stmt.get("then_body", [])))
                if stmt.get("else_body"):
                    calls.update(_extract_calls_from_body(stmt["else_body"]))
            elif kind == "repeat":
                calls.update(_extract_calls_from_body(stmt.get("body", [])))
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

    Args:
        call_graph: Grafo de llamadas {función: {funciones_que_llama}}.

    Returns:
        Conjunto de nombres de funciones recursivas.
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

    Args:
        ast: AST del programa completo.

    Returns:
        ProgramMetadata con clasificación y metadatos de funciones.
    """
    call_graph = _build_call_graph(ast)
    recursive_funcs = _find_recursive_functions(call_graph)

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
        # Todas las funciones son recursivas (o el programa solo tiene una función recursiva)
        algorithm_kind = "recursive"
    else:
        # Algunas son recursivas, otras no
        algorithm_kind = "mixed"

    return ProgramMetadata(
        algorithm_kind=algorithm_kind,
        functions=functions_meta,
    )


def has_main_block(ast: dict) -> bool:
    """
    Verifica si el programa tiene un bloque principal (begin...end) sin procedimientos.

    Args:
        ast: AST del programa.

    Returns:
        True si hay al menos un bloque/stmt que no sea "proc".
    """
    body = ast.get("body", [])

    for item in body:
        if not isinstance(item, dict):
            continue
        if item.get("kind") != "proc":
            return True

    return False
