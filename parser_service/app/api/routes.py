"""
routes.py — Endpoints del microservicio de parser
=================================================

Responsabilidad única: manejar HTTP requests/responses.
"""

from fastapi import FastAPI, HTTPException

from ..schemas import ParseReq, ParseResp, SemReq, SemResp, Issue as IssueSchema
from ..services.parser_service import get_parser_service
from ..services.semantic_analyzer import run_semantic
from ..domain.ast_models import Program

# ============================================================================
# APLICACIÓN
# ============================================================================

app = FastAPI(
    title="Parser Service",
    description="Microservicio de análisis sintáctico y semántico de pseudocódigo.",
    version="1.2.0"
)


# ============================================================================
# ENDPOINTS
# ============================================================================

@app.post("/parse", response_model=ParseResp)
def parse(req: ParseReq) -> ParseResp:
    """
    Realiza el análisis sintáctico del pseudocódigo.

    Returns:
        ParseResp con:
        - ok=True + ast si éxito
        - ok=False + errors si fallo
    """
    try:
        parser_service = get_parser_service()
        ast = parser_service.parse(req.code)

        return ParseResp(
            ok=True,
            ast=ast.model_dump(),
            errors=[]
        )

    except ValueError as e:
        # Error de sintaxis/parsing
        return ParseResp(
            ok=False,
            ast=None,
            errors=[str(e)]
        )

    except Exception as e:
        # Error inesperado
        return ParseResp(
            ok=False,
            ast=None,
            errors=[f"internal-error: {e}"]
        )


@app.post("/semantic", response_model=SemResp)
def semantic(req: SemReq) -> SemResp:
    """
    Realiza la normalización y verificación semántica del AST.

    Returns:
        SemResp con:
        - ast_sem: AST normalizado
        - issues: advertencias/errores
    """
    try:
        # Validar AST de entrada
        program = Program.model_validate(req.ast)

        # Análisis semántico
        ast_norm, issues = run_semantic(program)

        # Normalizar issues al formato de schema
        issues_out = []
        for it in issues:
            if isinstance(it, IssueSchema):
                issues_out.append(it)
            else:
                try:
                    issues_out.append(
                        IssueSchema.model_validate(
                            getattr(it, "model_dump", it)()
                        )
                    )
                except Exception:
                    issues_out.append(
                        IssueSchema(
                            severity=getattr(it, "severity", "warning"),
                            msg=getattr(it, "msg", str(it)),
                            where=getattr(it, "where", None),
                        )
                    )

        return SemResp(
            ast_sem=ast_norm.model_dump(),
            issues=issues_out
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error en análisis semántico: {e}"
        )


@app.get("/health")
def health():
    """Endpoint de salud del servicio."""
    return {
        "status": "ok",
        "service": "parser_service",
        "version": "1.2.0"
    }