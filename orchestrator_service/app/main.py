"""
Punto de entrada principal del Orchestrator Service.

Orquestador del pipeline completo de análisis de complejidad:
1. Normalización de pseudocódigo con LLM
2. Validación y corrección de gramática con LLM
3. Parsing sintáctico
4. Análisis semántico
5. Análisis de complejidad algorítmica

La lógica principal se encuentra en `logic.py`.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os

from .logic import router
from .schemas import (
    AnalyzeRequest,
    OrchestratorResponse,
    ParseResp,
    SemReq,
    AnalyzeAstReq,
    AnalyzerResult
)


def create_app() -> FastAPI:
    """
    Crea y configura la aplicación FastAPI del Orchestrator.

    - Configura CORS para permitir peticiones desde el frontend.
    - Registra las rutas del orchestrador.
    - Imprime configuración de los microservicios.

    Returns:
        Instancia configurada de `FastAPI`.
    """
    app = FastAPI(
        title="Orchestrator Service",
        description="Orquestador del pipeline de análisis de complejidad algorítmica",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json"
    )

    # --- CORS Configuration ---
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # En producción, especificar orígenes
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Rutas del Orchestrador ---
    app.include_router(router, tags=["analysis"])

    # --- Configuración de microservicios ---
    llm_url = os.getenv("LLM_URL", "http://localhost:8003")
    parser_url = os.getenv("PARSER_URL", "http://localhost:8001")
    analyzer_url = os.getenv("ANALYZER_URL", "http://localhost:8002")

    print(f"""
╔════════════════════════════════════════════════════════════╗
║         ORCHESTRATOR SERVICE INITIALIZED                   ║
╠════════════════════════════════════════════════════════════╣
║ Service:      Orchestrator                                 ║
║ Version:      1.0.0                                        ║
║ Docs:         http://localhost:8000/docs                   ║
╠════════════════════════════════════════════════════════════╣
║ Microservicios:                                            ║
║ LLM_URL:      {llm_url:<43}║
║ PARSER_URL:   {parser_url:<43}║
║ ANALYZER_URL: {analyzer_url:<43}║
╚════════════════════════════════════════════════════════════╝
    """)

    return app


# Instancia por defecto utilizada por Uvicorn
app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )