# app/routes.py
from __future__ import annotations
from fastapi import FastAPI
from lark.exceptions import LarkError

from .parser import parse_to_ast
from .semantic_pass import run_semantic
from .schemas import ParseReq, ParseResp, SemReq, SemResp, Issue as IssueSchema
from .ast_models import Program

app = FastAPI(title="Parser Service")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/parse", response_model=ParseResp)
def parse(req: ParseReq) -> ParseResp:
    """
    Parseo sintáctico -> AST (Pydantic serializable).
    Devuelve ok=False y lista de errores si falla el parseo.
    """
    try:
        ast = parse_to_ast(req.code)
        return ParseResp(ok=True, ast=ast.model_dump(), errors=[])
    except LarkError as e:
        # Mensaje legible de Lark (incluye línea/columna cuando aplica)
        return ParseResp(ok=False, ast=None, errors=[str(e)])
    except Exception as e:
        # Falla inesperada (no de gramática)
        return ParseResp(ok=False, ast=None, errors=[f"internal-error: {e}"])


@app.post("/semantic", response_model=SemResp)
def semantic(req: SemReq) -> SemResp:
    """
    Normalización + chequeos semánticos mínimos (step por defecto, bools, etc.).
    """
    program = Program.model_validate(req.ast)
    ast_norm, issues = run_semantic(program)

    # Asegura que las issues sean del tipo de schemas (por si semantic_pass usa su propio Issue)
    issues_out = []
    for it in issues:
        if isinstance(it, IssueSchema):
            issues_out.append(it)
        else:
            # Intentar convertir desde BaseModel compatible o atributos sueltos
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
