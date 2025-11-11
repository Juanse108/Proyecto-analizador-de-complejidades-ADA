from pydantic import BaseModel
from typing import Literal, Optional, Dict, Any


class AnalyzeAstReq(BaseModel):
    ast: Dict[str, Any]
    objective: Literal["worst", "best", "avg"] = "worst"
    cost_model: Optional[Dict[str, Any]] = None


class AnalyzeAstResp(BaseModel):
    big_o: str
    big_omega: Optional[str] = None
    theta: Optional[str] = None
    strong_bounds: Optional[str] = None
    ir: Dict[str, Any]
    notes: Optional[str] = None
