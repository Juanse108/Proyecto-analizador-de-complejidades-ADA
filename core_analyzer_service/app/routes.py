from fastapi import FastAPI
from pydantic import BaseModel
from typing import Any
from .analyzer import analyze_program
from .complexity_ir import to_json  # <--- importa el serializador

app = FastAPI(title="Analyzer")

class AnalyzeAstReq(BaseModel):
    ast: dict
    objective: str | None = "worst"
    cost_model: dict | None = None

class AnalyzeAstResp(BaseModel):
    big_o: str
    big_omega: str | None = None
    theta: str | None = None
    strong_bounds: Any | None = None
    ir: Any
    notes: str | None = "Iterativo MVP (seq/assign/if/for/while canónico)."

@app.post("/analyze-ast", response_model=AnalyzeAstResp)
def analyze_ast(req: AnalyzeAstReq):
    res = analyze_program(req.ast)
    return {
        "big_o": res["big_o"],
        "big_omega": None,
        "theta": None,
        "strong_bounds": None,
        "ir": to_json(res["ir"]),  # <--- aquí
        "notes": "Iterativo MVP (seq/assign/if/for/while canónico)."
    }

@app.get("/health")
def health():
    return {"status": "ok"}
