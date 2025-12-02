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

from .routers import health, llm


def create_app() -> FastAPI:
    """
    Crea y configura la aplicación FastAPI.

    - Asigna nombre y versión de la api.
    - Registra los routers de salud y del servicio LLM.

    Returns:
        Instancia configurada de `FastAPI`.
    """
    app = FastAPI(title="llm_service", version="0.1.0")

    # Rutas de healthcheck
    app.include_router(health.router, prefix="/health", tags=["health"])

    # Rutas del servicio LLM (to-grammar, recurrence, classify, compare, etc.)
    app.include_router(llm.router, prefix="/llm", tags=["llm"])

    return app


# Instancia por defecto utilizada por Uvicorn
app = create_app()
