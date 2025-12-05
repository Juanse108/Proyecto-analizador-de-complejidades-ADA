"""Lógica de orquestación del pipeline de análisis.

Coordina la interacción entre los microservicios:
- LLM: validación y corrección de gramática
- Parser: análisis sintáctico y semántico
- Analyzer: cálculo de complejidad algorítmica
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

router = APIRouter()


@router.post("/analyze", response_model=OrchestratorResponse)
async def analyze_full_pipeline(req: AnalyzeRequest) -> OrchestratorResponse:
    """
    Pipeline completo de análisis de complejidad algorítmica.
    
    Pasos:
    1. Validación con LLM
    2. Parsing sintáctico
    3. Análisis semántico
    4. Cálculo de complejidad
    
    Args:
        req: Solicitud con código y objetivo de análisis
        
    Returns:
        Resultado completo del análisis incluyendo Big O, Omega, Theta
    """
    # Inicializar código normalizado
    normalized_code = req.code
    correction_notes: List[str] = []

    # PASO 1: Validación y corrección de gramática con LLM
    try:
        validation_res = await llm_client.validate_grammar(normalized_code)
        
        corrected_code = validation_res.get("corrected_pseudocode", normalized_code)
        is_valid = validation_res.get("is_valid", False)
        issues = validation_res.get("issues", [])
        
        correction_notes = issues if issues else []
        
        if not is_valid and corrected_code != normalized_code:
            normalized_code = corrected_code
            
    except Exception as e:
        correction_notes.append(f"LLM validation warning: {str(e)}")

    # PASO 1.5: Corrección de formato 'end else'
    normalized_code = _fix_end_else_format(normalized_code)

    # PASO 2: Parsing sintáctico
    try:
        parse_payload = {"code": normalized_code}
        parse_res = await _call_service(PARSER_URL, "/parse", parse_payload, "Parser")
        
        parse_resp = ParseResp.model_validate(parse_res)
        if not parse_resp.ok:
            raise HTTPException(
                status_code=400, 
                detail=f"Parse error: {'; '.join(parse_resp.errors)}"
            )
        
        ast_raw = parse_resp.ast
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Parser error: {str(e)}")

    # PASO 3: Análisis semántico
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
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Semantic error: {str(e)}")

    # PASO 4: Análisis de complejidad
    try:
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
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Complexity analysis error: {str(e)}")

    # Construir respuesta final
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
        execution_trace=analysis_result.execution_trace,
    )


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


async def _call_service(url: str, endpoint: str, payload: dict, error_msg: str) -> dict:
    """
    Llamar a microservicios con manejo de errores.
    
    Args:
        url: URL base del servicio
        endpoint: Ruta del endpoint
        payload: Datos a enviar
        error_msg: Mensaje descriptivo para errores
    
    Returns:
        Respuesta JSON del servicio
    
    Raises:
        HTTPException: Si ocurre error en la comunicación
    """
    full_url = f"{url}{endpoint}"
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(full_url, json=payload)
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text
            raise HTTPException(
                status_code=500, 
                detail=f"{error_msg}: {error_detail[:300]}"
            )
        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=503, 
                detail=f"Timeout en {error_msg}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=503, 
                detail=f"Error de conexión: {str(e)}"
            )


class LLMClient:
    """
    Cliente para comunicación con el servicio LLM.
    
    Gestiona la validación y corrección de pseudocódigo mediante el servicio LLM.
    """
    
    def __init__(self, base_url: str, timeout: float = 60.0):
        """
        Args:
            base_url: URL base del servicio LLM
            timeout: Tiempo máximo de espera en segundos
        """
        self.base_url = base_url
        self.timeout = timeout
    
    async def validate_grammar(self, pseudocode: str) -> dict:
        """
        Valida y corrige pseudocódigo según la gramática.
        
        Args:
            pseudocode: Código pseudocódigo a validar
            
        Returns:
            Diccionario con: corrected_pseudocode, is_valid, issues
        """
        payload = {"pseudocode": pseudocode}
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/llm/validate-grammar", 
                    json=payload
                )
                response.raise_for_status()
                return response.json()
                
            except httpx.HTTPStatusError as e:
                error_text = e.response.text
                return {
                    "corrected_pseudocode": pseudocode,
                    "is_valid": False,
                    "issues": [f"LLM error: {error_text[:100]}"]
                }
            except Exception as e:
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


@router.get("/health")
async def health_check() -> Dict[str, str]:
    """Verificación de estado del Orchestrator."""
    return {
        "status": "ok", 
        "service": "orchestrator",
        "version": "1.0.0"
    }