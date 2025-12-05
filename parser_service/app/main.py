"""Punto de entrada del microservicio.

Punto de entrada simplificado que importa la app de api/routes.py

Usage:
    uvicorn app.main:app --reload
"""

from .api.routes import app

__all__ = ["app"]