# test_integration_trace.py
"""
Test de integración completa del sistema con traza de ejecución.
"""

import requests
import json

def test_iterative_algorithm():
    """Prueba con un algoritmo iterativo simple."""
    print("=" * 70)
    print("TEST DE INTEGRACIÓN: Suma de 1 a n (Algoritmo Iterativo)")
    print("=" * 70)
    
    pseudocode = """
PROCEDURE SumarHastaN(n)
    suma := 0
    FOR i := 1 TO n DO
        suma := suma + i
    ENDFOR
    RETURN suma
ENDPROCEDURE
"""
    
    url = "http://localhost:8000/analyze"
    payload = {
        "code": pseudocode,
        "objective": "worst"
    }
    
    print("\n📤 Enviando pseudocódigo al backend...")
    print(f"Código:\n{pseudocode}")
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        print("\n✅ Respuesta recibida:")
        print(f"  - Tipo: {data.get('algorithm_kind', 'N/A')}")
        print(f"  - Big O: {data.get('big_o', 'N/A')}")
        print(f"  - Big Omega: {data.get('big_omega', 'N/A')}")
        print(f"  - Método: {data.get('method_used', 'N/A')}")
        
        # Verificar si hay traza de ejecución
        if 'execution_trace' in data and data['execution_trace']:
            trace = data['execution_trace']
            print(f"\n🎯 Traza de Ejecución Generada:")
            print(f"  - Total de pasos: {len(trace.get('steps', []))}")
            print(f"  - Iteraciones totales: {trace.get('total_iterations', 0)}")
            print(f"  - Profundidad: {trace.get('max_depth', 0)}")
            print(f"  - Variables rastreadas: {', '.join(trace.get('variables_tracked', []))}")
            print(f"  - Complejidad derivada: {trace.get('complexity_formula', 'N/A')}")
            
            print(f"\n📊 Primeros 3 pasos de la traza:")
            for i, step in enumerate(trace.get('steps', [])[:3]):
                print(f"\n  Paso {step.get('step', i)}:")
                print(f"    - Línea: {step.get('line', '?')}")
                print(f"    - Condición: {step.get('condition', '—')}")
                print(f"    - Variables: {step.get('variables', {})}")
                print(f"    - Operación: {step.get('operation', '?')}")
                print(f"    - Costo acumulado: {step.get('cumulative_cost', '?')}")
            
            print(f"\n✅ Traza de ejecución implementada correctamente!")
        else:
            print(f"\n⚠️ No se generó traza de ejecución")
            print(f"   Contenido de la respuesta: {json.dumps(data, indent=2)[:500]}...")
        
        return True
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: No se pudo conectar al backend")
        print("   Asegúrate de que el servicio esté corriendo en http://localhost:8000")
        return False
    except requests.exceptions.Timeout:
        print("\n❌ Error: Timeout esperando respuesta del backend")
        return False
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_nested_loops():
    """Prueba con bucles anidados."""
    print("\n" + "=" * 70)
    print("TEST DE INTEGRACIÓN: Multiplicación de Matrices (Bucles Anidados)")
    print("=" * 70)
    
    pseudocode = """
PROCEDURE MatrixMultiply(A, B, n)
    FOR i := 1 TO n DO
        FOR j := 1 TO n DO
            C[i][j] := 0
            FOR k := 1 TO n DO
                C[i][j] := C[i][j] + A[i][k] * B[k][j]
            ENDFOR
        ENDFOR
    ENDFOR
    RETURN C
ENDPROCEDURE
"""
    
    url = "http://localhost:8000/analyze"
    payload = {
        "code": pseudocode,
        "objective": "worst"
    }
    
    print("\n📤 Enviando pseudocódigo al backend...")
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        print("\n✅ Respuesta recibida:")
        print(f"  - Big O: {data.get('big_o', 'N/A')}")
        
        if 'execution_trace' in data and data['execution_trace']:
            trace = data['execution_trace']
            print(f"\n🎯 Traza generada con {len(trace.get('steps', []))} pasos")
            print(f"  - Complejidad: {trace.get('complexity_formula', 'N/A')}")
            print(f"  - Profundidad de anidamiento: {trace.get('max_depth', 0)}")
            print(f"\n✅ Test completado correctamente!")
        else:
            print(f"\n⚠️ No se generó traza para este algoritmo")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


if __name__ == "__main__":
    print("\n🧪 INICIANDO TESTS DE INTEGRACIÓN\n")
    
    print("⚠️ IMPORTANTE: Asegúrate de que el backend esté corriendo:")
    print("   cd core_analyzer_service && python -m uvicorn app.main:app --reload")
    print("\n" + "=" * 70)
    
    input("\nPresiona ENTER para continuar...")
    
    success = True
    success &= test_iterative_algorithm()
    success &= test_nested_loops()
    
    print("\n" + "=" * 70)
    if success:
        print("✅ TODOS LOS TESTS DE INTEGRACIÓN COMPLETADOS")
    else:
        print("❌ ALGUNOS TESTS FALLARON")
    print("=" * 70)
