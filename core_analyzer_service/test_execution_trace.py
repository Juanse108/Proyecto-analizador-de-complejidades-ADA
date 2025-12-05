# test_execution_trace.py
"""
Script de prueba para verificar la generación de trazas de ejecución.
"""

import sys
import os

# Añadir el path del proyecto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.iterative.execution_trace import (
    generate_trace_for_simple_loop,
    generate_trace_for_nested_loops,
    generate_trace_for_binary_search,
    generate_execution_trace
)


def test_simple_loop():
    """Prueba con un bucle simple."""
    print("=" * 60)
    print("TEST 1: Bucle Simple (for i = 1 to n)")
    print("=" * 60)
    
    ast = {
        "body": [
            {
                "kind": "for",
                "var": {"kind": "var", "name": "i"},
                "from": {"kind": "number", "value": 1},
                "to": {"kind": "var", "name": "n"},
                "body": [
                    {"kind": "assign", "line": 3}
                ]
            }
        ]
    }
    
    trace = generate_trace_for_simple_loop(ast, "n")
    
    print(f"\nTotal de iteraciones: {trace.total_iterations}")
    print(f"Complejidad: {trace.complexity_formula}")
    print(f"\nPrimeros 3 pasos:")
    for step in trace.steps[:3]:
        print(f"  Paso {step.step}: {step.operation} | Variables: {step.variables} | Costo acumulado: {step.cumulative_cost}")
    
    print(f"\n✅ Test completado: {len(trace.steps)} pasos generados")


def test_nested_loops():
    """Prueba con bucles anidados."""
    print("\n" + "=" * 60)
    print("TEST 2: Bucles Anidados (for i, for j)")
    print("=" * 60)
    
    ast = {"body": []}
    
    trace = generate_trace_for_nested_loops(ast, "n")
    
    print(f"\nTotal de iteraciones: {trace.total_iterations}")
    print(f"Profundidad máxima: {trace.max_depth}")
    print(f"Complejidad: {trace.complexity_formula}")
    print(f"\nPrimeros 5 pasos:")
    for step in trace.steps[:5]:
        vars_str = ", ".join(f"{k}={v}" for k, v in step.variables.items())
        print(f"  Paso {step.step}: {step.operation} | {vars_str}")
    
    print(f"\n✅ Test completado: {len(trace.steps)} pasos generados")


def test_binary_search():
    """Prueba con búsqueda binaria."""
    print("\n" + "=" * 60)
    print("TEST 3: Búsqueda Binaria")
    print("=" * 60)
    
    ast = {"body": []}
    
    trace = generate_trace_for_binary_search(ast, "n")
    
    print(f"\nTotal de iteraciones: {trace.total_iterations}")
    print(f"Complejidad: {trace.complexity_formula}")
    print(f"\nTodos los pasos:")
    for step in trace.steps:
        if 'space' in step.variables:
            space = step.variables['space']
            print(f"  Paso {step.step}: Espacio={space} | {step.operation}")
    
    print(f"\n✅ Test completado: {len(trace.steps)} pasos generados")


def test_auto_detection():
    """Prueba la detección automática de tipo de algoritmo."""
    print("\n" + "=" * 60)
    print("TEST 4: Detección Automática")
    print("=" * 60)
    
    test_cases = [
        ("O(n)", "Bucle simple"),
        ("O(n^2)", "Bucles anidados"),
        ("O(log n)", "Búsqueda binaria"),
    ]
    
    for complexity, description in test_cases:
        trace = generate_execution_trace({}, complexity, "n")
        print(f"\n{description} ({complexity}):")
        print(f"  - Pasos: {len(trace.steps)}")
        print(f"  - Iteraciones: {trace.total_iterations}")
        print(f"  - Complejidad derivada: {trace.complexity_formula}")
    
    print(f"\n✅ Test de detección completado")


if __name__ == "__main__":
    print("\n🧪 INICIANDO PRUEBAS DE TRAZA DE EJECUCIÓN\n")
    
    try:
        test_simple_loop()
        test_nested_loops()
        test_binary_search()
        test_auto_detection()
        
        print("\n" + "=" * 60)
        print("✅ TODAS LAS PRUEBAS COMPLETADAS EXITOSAMENTE")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ ERROR EN LAS PRUEBAS: {e}")
        import traceback
        traceback.print_exc()
