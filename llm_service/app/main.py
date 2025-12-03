"""
Punto de entrada principal del microservicio LLM.

Expone una función `create_app` para facilitar el testeo y la integración
con servidores ASGI (Uvicorn, Gunicorn, etc.), y una instancia global
`app` usada por defecto cuando se ejecuta directamente con Uvicorn.

Las rutas se definen en el paquete `routers`:
    - health: endpoints de salud / ready / live.
    - llm:    endpoints que consumen el proveedor Gemini.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .routers import health, llm


def create_app() -> FastAPI:
    """
    Crea y configura la aplicación FastAPI.

    - Asigna nombre y versión de la api.
    - Configura CORS para permitir peticiones desde el frontend.
    - Registra los routers de salud y del servicio LLM.

    Returns:
        Instancia configurada de `FastAPI`.
    """
    app = FastAPI(
        title="LLM Service",
        description="Servicio de corrección y validación de pseudocódigo con Gemini 2.0",
        version="1.0.0"
    )

    # --- CORS Configuration ---
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # En producción, especificar orígenes
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Rutas de healthcheck ---
    app.include_router(health.router, prefix="/health", tags=["health"])

    # --- Rutas del servicio LLM (to-grammar, validate-grammar, recurrence, classify, compare, etc.) ---
    app.include_router(llm.router, prefix="/llm", tags=["llm"])

    print(f"""
╔════════════════════════════════════════════════════════════╗
║           LLM SERVICE INITIALIZED                          ║
╠════════════════════════════════════════════════════════════╣
║ Service:  LLM Service (Gemini 2.0)                         ║
║ Version:  1.0.0                                            ║
║ Docs:     http://localhost:8003/docs                       ║
╚════════════════════════════════════════════════════════════╝
    """)

    return app


# Instancia por defecto utilizada por Uvicorn
app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8003,
        reload=True,
        log_level="info"
    )
