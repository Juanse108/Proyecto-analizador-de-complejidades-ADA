# orchestrator_service/app/logic.py (CORREGIDO - líneas críticas)
"""
CORRECCIÓN: Variable normalized_code debe inicializarse al principio
"""

import os
import httpx
import re
from typing import Dict, List
from fastapi import APIRouter, HTTPException
import asyncio

from .schemas import (
    AnalyzeRequest, 
    OrchestratorResponse, 
    ParseResp, 
    SemReq, 
    AnalyzeAstReq, 
    AnalyzerResult
)

# ... (configuración sin cambios) ...

router = APIRouter()

# ---------------------------------------------------------------------------
# ENDPOINT PRINCIPAL: ANÁLISIS COMPLETO
# ---------------------------------------------------------------------------

@router.post("/analyze", response_model=OrchestratorResponse)
async def analyze_full_pipeline(req: AnalyzeRequest) -> OrchestratorResponse:
    """
    Pipeline completo de análisis de complejidad algorítmica.
    
    CORRECCIÓN: normalized_code se inicializa al principio.
    """
    print(f"\n{'='*70}")
    print(f"🚀 INICIANDO ANÁLISIS DE COMPLEJIDAD")
    print(f"{'='*70}")
    print(f"Objetivo: {req.objective}")
    print(f"Código (primeros 200 chars):\n{req.code[:200]}...")
    
    # ✅ CORRECCIÓN: Inicializar normalized_code con el código original
    normalized_code = req.code
    correction_notes: List[str] = []

    # --- PASO 1: VALIDACIÓN Y CORRECCIÓN DE GRAMÁTICA (LLM) ---
    print(f"\n[1/4] 🔍 VALIDANDO Y CORRIGIENDO GRAMÁTICA CON LLM...")
    try:
        validation_res = await llm_client.validate_grammar(normalized_code)
        
        corrected_code = validation_res.get("corrected_pseudocode", normalized_code)
        is_valid = validation_res.get("is_valid", False)
        issues = validation_res.get("issues", [])
        
        correction_notes = issues if issues else []
        
        if not is_valid and corrected_code != normalized_code:
            print(f"   ⚠️ CÓDIGO CORREGIDO POR LLM ({len(issues)} correcciones)")
            for issue in issues[:3]:
                print(f"      - {issue}")
            normalized_code = corrected_code
        else:
            print(f"   ✅ CÓDIGO VÁLIDO (sin correcciones necesarias)")
        
        print(f"\n   📄 Pseudocódigo que se enviará al parser:")
        print(f"   {normalized_code[:200]}...")
            
    except Exception as e:
        print(f"   ⚠️ Error en validación LLM (continuando): {str(e)}")
        correction_notes.append(f"LLM validation warning: {str(e)}")

    # --- PASO 1.5: CORRECCIÓN DE 'end else' ---
    print(f"\n[1.5/4] 🔧 CORRIGIENDO FORMATO 'end else'...")
    normalized_code = _fix_end_else_format(normalized_code)
    print(f"   ✅ Formato 'end else' normalizado")

    # --- PASO 2: PARSING SINTÁCTICO ---
    print(f"\n[2/4] 📝 PARSEANDO PSEUDOCÓDIGO...")
    try:
        parse_payload = {"code": normalized_code}
        parse_res = await _call_service(PARSER_URL, "/parse", parse_payload, "Parser")
        
        parse_resp = ParseResp.model_validate(parse_res)
        if not parse_resp.ok:
            print(f"   ❌ ERRORES DE PARSING:")
            for error in parse_resp.errors:
                print(f"      - {error}")
            raise HTTPException(
                status_code=400, 
                detail=f"Parse error: {'; '.join(parse_resp.errors)}"
            )
        
        print(f"   ✅ PARSING EXITOSO - AST generado")
        ast_raw = parse_resp.ast
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"   ❌ Error de parseo: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Parser error: {str(e)}")

    # --- PASO 3: ANÁLISIS SEMÁNTICO ---
    print(f"\n[3/4] 🔎 ANÁLISIS SEMÁNTICO...")
    try:
        sem_req = SemReq(ast=ast_raw)
        sem_res = await _call_service(
            PARSER_URL, 
            "/semantic", 
            sem_req.model_dump(), 
            "Semantic Analysis"
        )
        
        ast_sem = sem_res.get("ast_sem")
        if not ast_sem:
            raise HTTPException(
                status_code=500, 
                detail="No semantic AST returned from parser"
            )
        
        print(f"   ✅ ANÁLISIS SEMÁNTICO COMPLETADO")
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"   ❌ Error semántico: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Semantic error: {str(e)}")

    # --- PASO 4: ANÁLISIS DE COMPLEJIDAD ---
    print(f"\n[4/4] 📊 ANÁLISIS DE COMPLEJIDAD...")
    try:
        # ✅ CORRECCIÓN: Aquí normalized_code ya está definido
        cost_model_with_source = {
            "source_code": normalized_code
        }
        
        analysis_req = AnalyzeAstReq(
            ast=ast_sem,
            objective=req.objective,
            cost_model=cost_model_with_source
        )
        analysis_res = await _call_service(
            ANALYZER_URL, 
            "/analyze-ast", 
            analysis_req.model_dump(), 
            "Complexity Analysis"
        )
        
        analysis_result = AnalyzerResult.model_validate(analysis_res)
        print(f"   ✅ COMPLEJIDAD ANALIZADA")
        print(f"      O(n):  {analysis_result.big_o}")
        print(f"      Ω(n):  {analysis_result.big_omega}")
        print(f"      Θ(n):  {analysis_result.theta}")
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"   ❌ Error de complejidad: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Complexity analysis error: {str(e)}")

    # --- RESPUESTA FINAL ---
    print(f"\n✅ ANÁLISIS COMPLETADO EXITOSAMENTE")
    print(f"{'='*70}\n")
    
    all_notes = []
    if correction_notes:
        all_notes.extend(correction_notes)
    
    if analysis_result.notes:
        if isinstance(analysis_result.notes, str):
            all_notes.append(analysis_result.notes)
        else:
            all_notes.extend(analysis_result.notes)

    return OrchestratorResponse(
        normalized_code=normalized_code,
        big_o=analysis_result.big_o,
        big_omega=analysis_result.big_omega or "N/A",
        theta=analysis_result.theta or "N/A",
        ir=analysis_result.ir,
        notes=all_notes if all_notes else None,
        algorithm_kind=analysis_result.algorithm_kind,
        ir_worst=analysis_result.ir_worst,
        ir_best=analysis_result.ir_best,
        ir_avg=analysis_result.ir_avg,
        lines=analysis_result.lines,
        method_used=analysis_result.method_used,
        strong_bounds=analysis_result.strong_bounds,
        summations=analysis_result.summations,
        recurrence_equation=analysis_result.recurrence_equation,
        execution_trace=analysis_result.execution_trace,  # 🆕 NUEVO - FORWARDING
    )

# ---------------------------------------------------------------------------
# HELPER: CORRECCIÓN DE FORMATO
# ---------------------------------------------------------------------------

def _fix_end_else_format(pseudocode: str) -> str:
    """
    Asegura que 'end else' esté en la MISMA línea.
    """
    result = re.sub(
        r'(?m)^\s*(end)\s*\n\s*(else)\b',
        r'\1 \2',
        pseudocode,
        flags=re.MULTILINE | re.IGNORECASE
    )
    
    result = re.sub(
        r'(?i)(end)\s{2,}(else)\b',
        r'\1 \2',
        result,
        flags=re.IGNORECASE
    )
    
    return result


# ---------------------------------------------------------------------------
# HELPER: LLAMADAS A SERVICIOS
# ---------------------------------------------------------------------------

async def _call_service(url: str, endpoint: str, payload: dict, error_msg: str) -> dict:
    """Llamar a microservicios con manejo de errores."""
    full_url = f"{url}{endpoint}"
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            print(f"📤 POST {full_url}")
            print(f"   Payload keys: {list(payload.keys())}")
            
            response = await client.post(full_url, json=payload)
            response.raise_for_status()
            result = response.json()
            
            print(f"✅ {error_msg}: OK")
            return result
            
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text
            print(f"❌ {error_msg} error ({e.response.status_code})")
            print(f"   Response: {error_detail[:300]}")
            raise HTTPException(
                status_code=500, 
                detail=f"{error_msg}: {error_detail[:300]}"
            )
        except asyncio.TimeoutError:
            print(f"❌ {error_msg}: Timeout (60s)")
            raise HTTPException(
                status_code=503, 
                detail=f"Timeout en {error_msg}"
            )
        except Exception as e:
            print(f"❌ {error_msg} error: {str(e)}")
            raise HTTPException(
                status_code=503, 
                detail=f"Error de conexión: {str(e)}"
            )


# ---------------------------------------------------------------------------
# CLIENTE LLM
# ---------------------------------------------------------------------------

class LLMClient:
    """Cliente para comunicación con el servicio LLM."""
    
    def __init__(self, base_url: str, timeout: float = 60.0):
        self.base_url = base_url
        self.timeout = timeout
    
    async def validate_grammar(self, pseudocode: str) -> dict:
        """Valida y corrige pseudocódigo según la gramática."""
        payload = {"pseudocode": pseudocode}
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                print(f"📤 LLM validate-grammar: {self.base_url}/llm/validate-grammar")
                print(f"   📝 Pseudocódigo enviado (primeros 150 chars):")
                print(f"   {pseudocode[:150]}...")
                
                response = await client.post(
                    f"{self.base_url}/llm/validate-grammar", 
                    json=payload
                )
                response.raise_for_status()
                result = response.json()
                
                print(f"✅ LLM validation OK")
                print(f"   is_valid: {result.get('is_valid')}")
                print(f"   issues: {len(result.get('issues', []))} encontrados")
                
                return result
            except httpx.HTTPStatusError as e:
                error_text = e.response.text
                print(f"⚠️ LLM validation error ({e.response.status_code}): {error_text[:200]}")
                return {
                    "corrected_pseudocode": pseudocode,
                    "is_valid": False,
                    "issues": [f"LLM error: {error_text[:100]}"]
                }
            except Exception as e:
                print(f"⚠️ LLM connection error: {str(e)}")
                return {
                    "corrected_pseudocode": pseudocode,
                    "is_valid": False,
                    "issues": [f"Connection error: {str(e)}"]
                }


# Instanciar cliente LLM
LLM_URL = os.getenv("LLM_URL", "http://localhost:8003")
PARSER_URL = os.getenv("PARSER_URL", "http://localhost:8001")
ANALYZER_URL = os.getenv("ANALYZER_URL", "http://localhost:8002")

llm_client = LLMClient(LLM_URL)


# ---------------------------------------------------------------------------
# HEALTH CHECK
# ---------------------------------------------------------------------------

@router.get("/health")
async def health_check() -> Dict[str, str]:
    """Verificación de estado del Orchestrator."""
    return {
        "status": "ok", 
        "service": "orchestrator",
        "version": "1.0.0"
    }