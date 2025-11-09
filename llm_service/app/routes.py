from fastapi import FastAPI
from .routers import health, llm

app = FastAPI(title="llm_service (Gemini)", version="0.1.0")

# Rutas
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(llm.router, prefix="/llm", tags=["llm"])
