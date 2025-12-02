import os
import httpx
from typing import Dict
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Importaciones de esquemas internos
from .schemas import (
    AnalyzeRequest, 
    OrchestratorResponse, 
    ParseResp, 
    SemReq, 
    AnalyzeAstReq, 
    AnalyzerResult
)

# ---------------------------------------------------------------------------
# CONFIGURACIÓN Y CONSTANTES
# ---------------------------------------------------------------------------

LLM_URL = os.getenv("LLM_URL", "http://llm:8003")
PARSER_URL = os.getenv("PARSER_URL", "http://parser:8001")
ANALYZER_URL = os.getenv("ANALYZER_URL", "http://analyzer:8002")

GRAMMAR_RULES = """
// Reglas de sintaxis estricta para el pseudocódigo:
// Asignación: variable <- expresion
// Ciclo FOR: for variableContadora <- valorInicial to limite do begin ... end
// Ciclo WHILE: while (condicion) do begin ... end
// Condicional IF: if (condicion) then begin ... end else begin ... end
// Subrutinas: nombre_subrutina(parametros) begin ... end
// Llamada: CALL nombre_subrutina(parametros)
// Valores Booleanos: T (true) y F (false).
"""

app = FastAPI(
    title="Orchestrator Service", 
    description="Encadena el pre-procesamiento LLM, parseo y análisis de complejidad.",
    version="1.0.0"
)

# ---------------------------------------------------------------------------
# CLIENTE LLM
# ---------------------------------------------------------------------------

class LLMClient:
    """Cliente para comunicación con el servicio LLM."""
    
    def __init__(self, base_url: str, timeout: float = 60.0):
        self.base_url = base_url
        self.timeout = timeout
    
    async def generate(self, user_prompt: str, system_instruction: str, temperature: float = 0.1) -> str:
        """Llama al endpoint /generate del servicio LLM."""
        payload = {
            "user_prompt": user_prompt,
            "system_instruction": system_instruction,
            "temperature": temperature
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(f"{self.base_url}/generate", json=payload)
                response.raise_for_status()
                return response.json().get("text", "").strip()
            except httpx.HTTPStatusError as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Error del servicio LLM ({e.response.status_code}): {e.response.text}"
                )
            except Exception as e:
                raise HTTPException(
                    status_code=503,
                    detail=f"Fallo de conexión con LLM en {self.base_url}: {str(e)}"
                )

# Instancia del cliente LLM
llm_client = LLMClient(LLM_URL)

# ---------------------------------------------------------------------------
# FUNCIONES AUXILIARES
# ---------------------------------------------------------------------------

def _create_normalization_prompt(user_input: str) -> tuple:
    """Crea el prompt del sistema y el prompt del usuario para normalización."""
    
    system_prompt = f"""
Eres el Agente de Normalización de Pseudocódigo. Tu tarea es garantizar la calidad de entrada.

1. Si la entrada es lenguaje natural (ej: 'haz un bubble sort'), tradúcela al Pseudocódigo más eficiente que cumpla con las Reglas de Gramática.
2. Si es Pseudocódigo, revísalo y corrígelo sutilmente para que se ajuste PERFECTAMENTE a las Reglas de Gramática.
3. NO incluyas explicaciones, texto introductorio, ni Markdown (```). Solo devuelve el código limpio y corregido/traducido.

Reglas de Gramática OBLIGATORIAS:
{GRAMMAR_RULES}
"""
    
    return system_prompt, user_input

async def _call_service(url: str, endpoint: str, payload: dict, error_msg: str) -> dict:
    """Función genérica para llamar a microservicios con manejo de errores."""
    full_url = f"{url}{endpoint}"
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(full_url, json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=500, 
                detail=f"{error_msg} (Servicio {url} respondió con {e.response.status_code}): {e.response.text}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=503, 
                detail=f"Fallo de conexión con {error_msg} en {full_url}: {str(e)}"
            )

# ---------------------------------------------------------------------------
# ENDPOINT PRINCIPAL: ANÁLISIS COMPLETO
# ---------------------------------------------------------------------------

@app.post("/analyze", response_model=OrchestratorResponse)
async def analyze_full_pipeline(req: AnalyzeRequest) -> OrchestratorResponse:
    """
    Ejecuta el pipeline completo de análisis:
    1. Normalización (LLM / Agente de Gramática).
    2. Parseo Sintáctico (Parser Service).
    3. Análisis Semántico (Parser Service).
    4. Análisis de Complejidad (Analyzer Service).
    """
    normalized_code = req.code

    # --- PASO 1: AGENTE DE NORMALIZACIÓN (LLM) ---
    try:
        system_prompt, user_prompt = _create_normalization_prompt(req.code)
        normalized_code = await llm_client.generate(user_prompt, system_prompt, temperature=0.1)
        print(f"✓ Código normalizado por LLM:\n{normalized_code}")
    except HTTPException as e:
        print(f"⚠ Advertencia: Fallo al llamar al Agente de Gramática. Usando código original. Error: {e.detail}")
        normalized_code = req.code
    except Exception as e:
        print(f"⚠ Error inesperado en normalización: {str(e)}")
        normalized_code = req.code
    
    # --- PASO 2: PARSEO SINTÁCTICO ---
    parse_payload = {"code": normalized_code}
    parse_res = await _call_service(PARSER_URL, "/parse", parse_payload, "Parser Sintáctico")
    
    parse_resp = ParseResp.model_validate(parse_res)
    if not parse_resp.ok:
        raise HTTPException(status_code=400, detail=f"Error de Sintaxis: {parse_resp.errors}")

    ast_raw = parse_resp.ast
    
    # --- PASO 3: ANÁLISIS SEMÁNTICO ---
    sem_req = SemReq(ast=ast_raw)
    sem_res = await _call_service(PARSER_URL, "/semantic", sem_req.model_dump(), "Análisis Semántico")
    
    ast_sem = sem_res.get("ast_sem")
    if not ast_sem:
        raise HTTPException(status_code=500, detail="El servicio de análisis semántico no retornó AST")
    
    # --- PASO 4: ANÁLISIS DE COMPLEJIDAD ---
    analysis_req = AnalyzeAstReq(
        ast_sem=ast_sem, 
        objective=req.objective,
        cost_model=None
    )
    analysis_res = await _call_service(ANALYZER_URL, "/analyze-ast", analysis_req.model_dump(), "Análisis de Complejidad")
    
    analysis_result = AnalyzerResult.model_validate(analysis_res)
    
    # --- PASO 5: RESPUESTA FINAL ---
    return OrchestratorResponse(
        normalized_code=normalized_code,
        big_o=analysis_result.big_o,
        big_omega=analysis_result.big_omega,
        theta=analysis_result.theta,
        ir=analysis_result.ir,
        notes=analysis_result.notes
    )

# ---------------------------------------------------------------------------
# RUTA DE SALUD (HEALTH CHECK)
# ---------------------------------------------------------------------------

@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Verificación de estado del Orquestador."""
    return {"status": "ok", "service": "orchestrator"}