"""
Definición alternativa de la aplicación FastAPI.

Este módulo crea directamente una instancia global de `FastAPI` y registra
las mismas rutas que en `main.py`. Es útil, por ejemplo, cuando se quiere
montar esta app como subaplicación dentro de otro proyecto, o para mantener
compatibilidad con despliegues anteriores que esperaban `routes.app`.

Nota:
    La lógica de negocio está en los routers `health` y `llm`. Aquí solo
    se centraliza el registro de rutas sobre un `FastAPI` ya creado.
"""

from fastapi import FastAPI

from .routers import health, llm


# Instancia principal de la aplicación para este módulo
app = FastAPI(title="llm_service (Gemini)", version="0.1.0")

# Rutas de healthcheck
app.include_router(health.router, prefix="/health", tags=["health"])

# Rutas del servicio LLM
app.include_router(llm.router, prefix="/llm", tags=["llm"])
