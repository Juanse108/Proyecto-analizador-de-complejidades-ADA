# app/api/analyzer_routes.py
"""
analyzer_routes.py
==================

FastAPI router for algorithm complexity analysis endpoints.
"""

from typing import Dict

from fastapi import APIRouter, HTTPException

from ..schemas import AnalyzeAstReq, analyzeAstResp
from ..services import analyze_ast_core


router = APIRouter(
    prefix="",
    tags=["complexity-analysis"],
    responses={
        404: {"description": "Resource not found"},
        500: {"description": "Internal server error"},
    },
)


@router.post("/analyze-ast", response_model=analyzeAstResp)
def analyze_ast(req: AnalyzeAstReq) -> analyzeAstResp:
    try:
        return analyze_ast_core(req)
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal analysis error: {str(e)}")


@router.get("/health")
def health_check() -> Dict[str, str]:
    return {"status": "ok", "service": "core_analyzer"}
