# ... (importaciones) ...
from typing import Any, Optional
from fastapi import FastAPI
from pydantic import BaseModel
from .analyzer import analyze_program
from .complexity_ir import to_json 

app = FastAPI()

class AnalyzeAstReq(BaseModel):  
    ast: dict

class AnalyzeAstResp(BaseModel):
    big_o: str
    big_omega: str
    theta: Optional[str] = None
    strong_bounds: Any | None = None
    ir_worst: Any # Representación IR del peor caso
    ir_best: Any  # Representación IR del mejor caso
    notes: Optional[str] = "Iterativo MVP (O y Ω para seq/assign/if/for/while)."

@app.post("/analyze-ast", response_model=AnalyzeAstResp)
def analyze_ast(req: AnalyzeAstReq):
    res = analyze_program(req.ast) # Esta función ahora devuelve todo
    
    return {
        "big_o": res["big_o"],
        "big_omega": res["big_omega"],
        "theta": res["theta"],
        "strong_bounds": None,
        "ir_worst": to_json(res["ir_worst"]),
        "ir_best": to_json(res["ir_best"]),
        "notes": "Iterativo MVP (O y Ω para seq/assign/if/for/while)."
    }