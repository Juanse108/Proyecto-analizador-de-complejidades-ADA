from fastapi import FastAPI
from .schemas import AnalyzeRequest, AnalyzeResponse
from .logic import analyze_pipeline

app = FastAPI(title="Analizador – Orchestrator")


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest):
    res = await analyze_pipeline(req.code, req.objective, req.cost_model)
    return res
