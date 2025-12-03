"""
main.py — Entry point del microservicio
=======================================

Punto de entrada simplificado que importa la app de api/routes.py
"""

from .api.routes import app

# Re-exportar para que Uvicorn pueda encontrarlo:
# uvicorn app.main:app --reload

__all__ = ["app"]