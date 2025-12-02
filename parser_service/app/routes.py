"""
routes.py — Definición de endpoints del microservicio de parser
===============================================================

Este módulo define las rutas HTTP del microservicio de análisis sintáctico
y semántico de pseudocódigo.
Se implementa usando **FastAPI** y expone dos endpoints principales:

1. `/parse`   → Análisis sintáctico → Árbol de Sintaxis Abstracta (AST)
2. `/semantic` → Normalización y chequeos semánticos del AST

"""

from fastapi import FastAPI
from lark.exceptions import LarkError

# Importaciones internas del microservicio (relative imports)
from .parser import parse_to_ast
from .semantic_pass import run_semantic
from .schemas import ParseReq, ParseResp, SemReq, SemResp, Issue as IssueSchema
from .ast_models import Program


# ---------------------------------------------------------------------------
# INSTANCIA DE LA APLICACIÓN FASTAPI
# ---------------------------------------------------------------------------

app = FastAPI(title="Parser Service", description="Microservicio de análisis sintáctico y semántico de pseudocódigo.")




# ---------------------------------------------------------------------------
# ENDPOINT: PARSEO SINTÁCTICO
# ---------------------------------------------------------------------------

@app.post("/parse", response_model=ParseResp)
def parse(req: ParseReq) -> ParseResp:
    """
    Realiza el **análisis sintáctico** del pseudocódigo recibido y devuelve
    su representación como Árbol de Sintaxis Abstracta (AST).

    Args:
        req (ParseReq): cuerpo del request con el campo `code` (pseudocódigo).

    Returns:
        ParseResp:
            - ok=True si el parseo fue exitoso.
            - ast: representación serializable del árbol.
            - errors: lista de errores (vacía si todo salió bien).
    """
    try:
        ast = parse_to_ast(req.code)
        return ParseResp(ok=True, ast=ast.model_dump(), errors=[])

    except LarkError as e:
        # Error de gramática o sintaxis detectado por Lark
        return ParseResp(ok=False, ast=None, errors=[str(e)])

    except Exception as e:
        # Error inesperado (por ejemplo, fallo interno)
        return ParseResp(ok=False, ast=None, errors=[f"internal-error: {e}"])


# ---------------------------------------------------------------------------
# ENDPOINT: ANÁLISIS SEMÁNTICO
# ---------------------------------------------------------------------------

@app.post("/semantic", response_model=SemResp)
def semantic(req: SemReq) -> SemResp:
    """
    Realiza la **normalización y verificación semántica** del AST.

    Este paso complementa el análisis sintáctico corrigiendo y validando:
    - Tipos de datos y operaciones básicas.
    - Parámetros de bucles (p.ej., step por defecto).
    - Valores booleanos y null.
    - Estructuras inválidas o inconsistentes.

    Args:
        req (SemReq): cuerpo del request con el campo `ast` (AST previamente generado).

    Returns:
        SemResp:
            - ast_sem: AST normalizado (serializable a JSON).
            - issues: lista de advertencias o errores semánticos.
    """
    # Validar el AST de entrada
    program = Program.model_validate(req.ast)

    # Ejecutar el análisis semántico
    ast_norm, issues = run_semantic(program)

    # Normalizar la lista de "issues" a un formato compatible con schemas
    issues_out = []
    for it in issues:
        if isinstance(it, IssueSchema):
            # Ya está en el formato correcto
            issues_out.append(it)
        else:
            # Intentar convertir objetos similares o diccionarios
            try:
                issues_out.append(IssueSchema.model_validate(getattr(it, "model_dump", it)()))
            except Exception:
                issues_out.append(
                    IssueSchema(
                        severity=getattr(it, "severity", "warning"),
                        msg=getattr(it, "msg", str(it)),
                        where=getattr(it, "where", None),
                    )
                )

    return SemResp(ast_sem=ast_norm.model_dump(), issues=issues_out)
