from pydantic import BaseModel
from typing import Literal, Optional, Dict, Any


class AnalyzeRequest(BaseModel):
    code: str
    language: Literal["pseudocode"] = "pseudocode"
    objective: Literal["worst", "avg", "best"] = "worst"
    cost_model: Optional[Dict[str, Any]] = None


class AnalyzeResponse(BaseModel):
    big_o: str
    big_omega: Optional[str] = None
    theta: Optional[str] = None
    strong_bounds: Optional[str] = None
    ir: Dict[str, Any]
    notes: Optional[str] = None
