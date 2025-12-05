#!/usr/bin/env python3
"""
Test para diagnosticar análisis de multiplicación de matrices.
"""
import sys
sys.path.insert(0, '/app')

# Pseudocódigo de multiplicación de matrices
pseudocode = """MatrixMultiply(A, B, C, n)
begin
  for i <- 1 to n do
  begin
    for j <- 1 to n do
    begin
      C[i][j] <- 0
      for k <- 1 to n do
      begin
        C[i][j] <- C[i][j] + A[i][k] * B[k][j]
      end
    end
  end
end"""

print("=" * 80)
print("DIAGNÓSTICO: MULTIPLICACIÓN DE MATRICES")
print("=" * 80)

try:
    # Parsear
    print("\n1️⃣  PARSEANDO PSEUDOCÓDIGO...")
    import requests
    
    # Usar cliente HTTP para llamar al parser
    parse_resp = requests.post("http://parser:8001/parse", json={"pseudocode": pseudocode}, timeout=10)
    parse_resp.raise_for_status()
    ast = parse_resp.json()["ast"]
    print(f"✅ AST generado. Raíz: {ast.get('kind')}")
    
    # Analizar
    print("\n2️⃣  ANALIZANDO CON ANALYZER SERVICE...")
    
    analyze_req = {
        "ast": ast,
        "objective": "worst",
        "cost_model": {}
    }
    
    analyze_resp = requests.post("http://analyzer:8002/analyze-ast", json=analyze_req, timeout=10)
    analyze_resp.raise_for_status()
    result = analyze_resp.json()
    
    print(f"✅ Análisis completado")
    print(f"\nBig O (desde analyzer): {result.get('big_o')}")
    print(f"IR worst: {result.get('ir_worst')}")
    
    # Debugear la expresión
    print("\n3️⃣  ANALIZANDO LA EXPRESIÓN IR...")
    import json
    print(f"IR worst (full):")
    print(json.dumps(result.get('ir_worst'), indent=2))
    
    # Mostrar sumatorias
    print("\n4️⃣  SUMATORIAS GENERADAS...")
    summations = result.get('summations', {})
    if summations and 'worst' in summations:
        print(f"Worst case summation LaTeX:")
        print(f"{summations['worst'].get('latex', 'N/A')}")
        print(f"\nWorst case summation text:")
        print(f"{summations['worst'].get('text', 'N/A')}")
    else:
        print("❌ No se encontraron sumatorias")
    
    # Strong bounds
    print("\n5️⃣  STRONG BOUNDS...")
    sb = result.get('strong_bounds', {})
    print(f"Formula: {sb.get('formula', 'N/A')}")
    print(f"Dominant term: {sb.get('dominant_term', 'N/A')}")
    print(f"Terms: {sb.get('terms', 'N/A')}")
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
