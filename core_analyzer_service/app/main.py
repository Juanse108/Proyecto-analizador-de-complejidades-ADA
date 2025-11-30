from fastapi import FastAPI

from .api.analyzer_routes import router as analyzer_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Core Analyzer Service",
        version="1.0.0",
        description=(
            "Microservice for algorithmic complexity analysis. "
            "Analyzes iterative and recursive algorithms from Abstract Syntax Trees (AST), "
            "providing Big-O, Big-Omega, and Theta complexity bounds with detailed breakdowns."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.include_router(analyzer_router)

    return app


app = create_app()