from __future__ import annotations
from typing import List, Optional, Dict, Any
from pydantic import BaseModel


# Peticiones
class ParseReq(BaseModel):
    code: str


class SemReq(BaseModel):
    ast: Dict[str, Any]  # Program serializado (Program.model_dump())


# Respuestas
class ParseResp(BaseModel):
    ok: bool
    ast: Optional[Dict[str, Any]] = None
    errors: List[str] = []  # mensajes sintácticos (si falla el parseo)


class Issue(BaseModel):
    severity: str  # "error" | "warning"
    msg: str
    where: str | None = None


class SemResp(BaseModel):
    ast_sem: Dict[str, Any]  # Program normalizado
    issues: List[Issue] = []  # advertencias/errores semánticos
