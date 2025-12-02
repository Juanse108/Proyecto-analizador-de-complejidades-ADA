"""
api
===

FastAPI routers and HTTP endpoint definitions for the complexity analyzer service.

This package contains all HTTP-facing components of the microservice, including
request/response handling, input validation, and endpoint routing.

Modules
-------
analyzer_routes
    Main router for complexity analysis endpoints (/analyze-ast, /health).

Design
------
The API layer follows the principle of thin controllers: endpoints receive requests,
delegate business logic to domain/service layers, and format responses. This ensures
clear separation of concerns and testability.

Usage
-----
Import the router in main.py to register endpoints:

    from app.api.analyzer_routes import router
    app.include_router(router)
"""

from .analyzer_routes import router

__all__ = ["router"]