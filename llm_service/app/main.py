from fastapi import FastAPI
from .routers import health, llm


def create_app() -> FastAPI:
    app = FastAPI(title="llm_service", version="0.1.0")
    app.include_router(health.router, prefix="/health", tags=["health"])
    app.include_router(llm.router, prefix="/llm", tags=["llm"])
    return app


app = create_app()
