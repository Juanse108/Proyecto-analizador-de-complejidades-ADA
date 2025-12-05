"""Clasificación de algoritmos en iterativos, recursivos o mixtos.

Este módulo analiza la estructura de llamadas del programa para determinar
si contiene funciones recursivas y clasifica el algoritmo en consecuencia.
"""

from typing import Dict, Set, List
from .schemas import ProgramMetadata, FunctionMetadata


def _build_call_graph(ast: dict) -> Dict[str, Set[str]]:
    """Construye el grafo de llamadas entre funciones del programa.
    
    Args:
        ast: Árbol de sintaxis abstracta del programa
        
    Returns:
        Diccionario que mapea cada función a las funciones que invoca
    """
    call_graph: Dict[str, Set[str]] = {}

    def _extract_calls_from_expr(expr) -> Set[str]:
        """Extrae nombres de funciones llamadas dentro de expresiones.
        
        Args:
            expr: Expresión a analizar
            
        Returns:
            Conjunto de nombres de funciones encontradas
        """
        calls: Set[str] = set()

        if not isinstance(expr, dict):
            return calls

        kind = expr.get("kind")

        if kind == "funcall":
            calls.add(expr.get("name", ""))
            for arg in expr.get("args", []):
                calls.update(_extract_calls_from_expr(arg))

        elif kind == "binop":
            calls.update(_extract_calls_from_expr(expr.get("left")))
            calls.update(_extract_calls_from_expr(expr.get("right")))

        elif kind == "unop":
            calls.update(_extract_calls_from_expr(expr.get("expr")))

        elif kind == "index":
            calls.update(_extract_calls_from_expr(expr.get("base")))
            calls.update(_extract_calls_from_expr(expr.get("index")))

        return calls

    def _extract_calls_from_body(body: List[dict]) -> Set[str]:
        """Extrae nombres de funciones llamadas en un cuerpo de sentencias.
        
        Args:
            body: Lista de sentencias a analizar
            
        Returns:
            Conjunto de nombres de funciones llamadas
        """
        calls: Set[str] = set()

        for stmt in body:
            if not isinstance(stmt, dict):
                continue

            kind = stmt.get("kind")

            if kind == "call":
                calls.add(stmt.get("name", ""))
                for arg in stmt.get("args", []):
                    calls.update(_extract_calls_from_expr(arg))

            elif kind == "assign":
                expr = stmt.get("expr")
                if expr:
                    calls.update(_extract_calls_from_expr(expr))

            elif kind == "if":
                cond = stmt.get("cond")
                if cond:
                    calls.update(_extract_calls_from_expr(cond))

                calls.update(_extract_calls_from_body(stmt.get("then_body", [])))
                if stmt.get("else_body"):
                    calls.update(_extract_calls_from_body(stmt["else_body"]))

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

            elif kind == "for":
                start = stmt.get("start")
                end = stmt.get("end")
                if start:
                    calls.update(_extract_calls_from_expr(start))
                if end:
                    calls.update(_extract_calls_from_expr(end))

                calls.update(_extract_calls_from_body(stmt.get("body", [])))

            elif kind == "block":
                calls.update(_extract_calls_from_body(stmt.get("stmts", [])))

        return calls

    body = ast.get("body", [])

    for item in body:
        if not isinstance(item, dict):
            continue

        if item.get("kind") == "proc":
            name = item.get("name", "")
            proc_body = item.get("body", [])
            call_graph[name] = _extract_calls_from_body(proc_body)

    return call_graph


def _find_recursive_functions(call_graph: Dict[str, Set[str]]) -> Set[str]:
    """Detecta funciones recursivas mediante búsqueda de ciclos.
    
    Utiliza DFS (Depth-First Search) para encontrar ciclos en el grafo de llamadas.
    Una función es recursiva si existe un camino desde ella misma de vuelta a ella.
    
    Args:
        call_graph: Grafo de llamadas entre funciones
        
    Returns:
        Conjunto de nombres de funciones recursivas
    """
    recursive: Set[str] = set()

    def _dfs(func: str, path: Set[str]) -> None:
        """Búsqueda en profundidad para detectar ciclos.
        
        Args:
            func: Función actual siendo visitada
            path: Conjunto de funciones en el camino actual
        """
        if func in path:
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
    """Clasifica un algoritmo según su estructura de llamadas.
    
    Analiza el grafo de llamadas del programa para determinar si contiene
    funciones recursivas y clasifica el algoritmo en una de tres categorías:
    
    - iterative: Ninguna función es recursiva
    - recursive: Al menos una función es recursiva
    - mixed: Contiene funciones recursivas y no recursivas
    
    Args:
        ast: Árbol de sintaxis abstracta del programa
        
    Returns:
        Metadatos del programa incluyendo clasificación y datos de funciones
    """
    call_graph = _build_call_graph(ast)
    recursive_funcs = _find_recursive_functions(call_graph)

    functions_meta: Dict[str, FunctionMetadata] = {}

    for func_name, calls in call_graph.items():
        functions_meta[func_name] = FunctionMetadata(
            name=func_name,
            is_recursive=(func_name in recursive_funcs),
            calls=list(calls),
        )

    if not recursive_funcs:
        algorithm_kind = "iterative"
    elif len(recursive_funcs) == len(call_graph):
        algorithm_kind = "recursive"
    else:
        algorithm_kind = "mixed"

    return ProgramMetadata(
        algorithm_kind=algorithm_kind,
        functions=functions_meta,
    )


def has_main_block(ast: dict) -> bool:
    """Verifica si el programa tiene un bloque principal sin procedimientos.
    
    Args:
        ast: Árbol de sintaxis abstracta del programa
        
    Returns:
        True si existe un bloque principal, False en caso contrario
    """
    body = ast.get("body", [])

    for item in body:
        if not isinstance(item, dict):
            continue
        if item.get("kind") != "proc":
            return True

    return False