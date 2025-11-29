from fastapi import APIRouter, HTTPException
from .schemas import AnalyzeRequest, AnalyzeResponse
from .logic import analyze_pipeline

router = APIRouter()

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_endpoint(req: AnalyzeRequest):
    try:
        # Llama a la lógica de orquestación
        result = await analyze_pipeline(req.code, req.objective, req.cost_model)
        return result
    except ValueError as ve:
        # Errores de validación o sintaxis
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        # Errores de conexión con otros microservicios
        print(f"Error interno: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del orquestador: {str(e)}")