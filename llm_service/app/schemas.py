from typing import List, Literal, Optional
from pydantic import BaseModel, Field


# ---- to-grammar ----
class ToGrammarRequest(BaseModel):
    text: str = Field(..., description="Texto o pseudocódigo a normalizar")
    hints: Optional[str] = None


class ToGrammarResponse(BaseModel):
    pseudocode_normalizado: str
    issues: List[str] = []


# ---- recurrence ----
class RecurrenceRequest(BaseModel):
    pseudocode: str


class RecurrenceResponse(BaseModel):
    recurrence: Optional[str] = None
    base_cases: List[str] = []
    a: Optional[int] = None
    b: Optional[int] = None
    f: Optional[str] = None
    master_case: Optional[str] = None
    big_o: Optional[str] = None
    big_omega: Optional[str] = None
    big_theta: Optional[str] = None
    explanation: Optional[str] = None


# ---- classify ----
PatternLabel = Literal[
    "divide_and_conquer", "dynamic_programming", "backtracking", "greedy",
    "search", "scan", "counting", "unknown"
]


class ClassifyRequest(BaseModel):
    pseudocode: str


class ClassifyResponse(BaseModel):
    pattern: PatternLabel = "unknown"
    confidence: float = 0.0
    hints: List[str] = []


# ---- compare ----
class BigBounds(BaseModel):
    big_o: Optional[str] = None
    big_omega: Optional[str] = None
    big_theta: Optional[str] = None


class CompareRequest(BaseModel):
    core: BigBounds
    llm: BigBounds


class CompareResponse(BaseModel):
    agree: bool
    deltas: List[str] = []
    next_checks: List[str] = []
