"""Parser Service Application.

Microservicio de análisis sintáctico y semántico de pseudocódigo.

Arquitectura:
    - api/: FastAPI endpoints (HTTP layer)
    - domain/: Modelos del dominio (AST)
    - infrastructure/: Dependencias externas (Lark parser, file I/O)
    - services/: Lógica de negocio y orquestación
    - schemas.py: Request/Response models (Pydantic)

Usage:
    from app.api import app
    # uvicorn app.api:app --reload
"""

__version__ = "1.2.0"