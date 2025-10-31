"""
schemas.py — Modelos de datos (Pydantic) para las rutas del microservicio
=========================================================================

Este módulo define los **esquemas de entrada y salida (request/response)**
utilizados por el microservicio del parser y analizador semántico.

Los modelos están basados en `pydantic.BaseModel` para garantizar:
- Validación automática de tipos.
- Serialización/Deserialización a JSON.
- Documentación automática en Swagger/OpenAPI.


"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 1️. PETICIONES (Request Models)
# ---------------------------------------------------------------------------

class ParseReq(BaseModel):
    """
    Modelo de solicitud para el endpoint `/parse`.

    Atributos:
        code (str): pseudocódigo a analizar.
    """
    code: str


class SemReq(BaseModel):
    """
    Modelo de solicitud para el endpoint `/semantic`.

    Atributos:
        ast (Dict[str, Any]): Árbol de Sintaxis Abstracta (AST) serializado,
                              generado por el endpoint `/parse`.
    """
    ast: Dict[str, Any]


# ---------------------------------------------------------------------------
# 2️. MODELOS AUXILIARES
# ---------------------------------------------------------------------------

class Issue(BaseModel):
    """
    Representa una advertencia o error detectado durante el análisis semántico.

    Atributos:
        severity (str): nivel de severidad ("error" o "warning").
        msg (str): descripción legible del problema.
        where (Optional[str]): ubicación textual o referencia (opcional).
    """
    severity: str  # "error" | "warning"
    msg: str
    where: Optional[str] = None


# ---------------------------------------------------------------------------
# 3️. RESPUESTAS (Response Models)
# ---------------------------------------------------------------------------

class ParseResp(BaseModel):
    """
    Respuesta del endpoint `/parse`.

    Atributos:
        ok (bool): indica si el parseo fue exitoso.
        ast (Optional[Dict[str, Any]]): representación del AST en caso de éxito.
        errors (List[str]): lista de errores sintácticos (vacía si ok=True).
    """
    ok: bool
    ast: Optional[Dict[str, Any]] = None
    errors: List[str] = Field(default_factory=list)


class SemResp(BaseModel):
    """
    Respuesta del endpoint `/semantic`.

    Atributos:
        ast_sem (Dict[str, Any]): AST normalizado tras el análisis semántico.
        issues (List[Issue]): lista de advertencias o errores detectados.
    """
    ast_sem: Dict[str, Any]
    issues: List[Issue] = Field(default_factory=list)
