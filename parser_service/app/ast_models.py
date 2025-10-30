# app/ast_models.py
from __future__ import annotations
from typing import List, Optional, Union, Literal
from pydantic import BaseModel


# ===========
# EXPRESIONES
# ===========
class Num(BaseModel):
    kind: Literal["num"] = "num"
    value: int


class Bool(BaseModel):
    kind: Literal["bool"] = "bool"
    value: bool


class NullLit(BaseModel):
    kind: Literal["null"] = "null"


class Var(BaseModel):
    # Referencia simple a variable
    kind: Literal["var"] = "var"
    name: str


class Range(BaseModel):
    # A[lo..hi]
    kind: Literal["range"] = "range"
    lo: "Expr"
    hi: "Expr"


class Index(BaseModel):
    # A[i]  o  A[lo..hi] (Range)
    kind: Literal["index"] = "index"
    base: "LValue"
    index: "IndexKey"  # Expr | Range


class Field(BaseModel):
    # x.f
    kind: Literal["field"] = "field"
    base: "LValue"
    field: str


LValue = Union[Var, Index, Field]
IndexKey = Union["Expr", Range]


class UnOp(BaseModel):
    # -x, not x
    kind: Literal["unop"] = "unop"
    op: str  # "-", "not"
    expr: "Expr"


class BinOp(BaseModel):
    # x + y, x div y, x and y, x <= y, etc.
    kind: Literal["binop"] = "binop"
    op: str  # "+","-","*","/","div","mod","and","or","==","!=","<","<=",">",">="
    left: "Expr"
    right: "Expr"


class FuncCall(BaseModel):
    # length(A), ceil(x), floor(x) o cualquier f(x) usada como expresión
    kind: Literal["funcall"] = "funcall"
    name: str
    args: List["Expr"] = []


Expr = Union[
    Num, Bool, NullLit, LValue, UnOp, BinOp, FuncCall, Range]  # Range solo aparece dentro de Index, pero se mantiene por tipado


# ===========
# SENTENCIAS
# ===========
class Assign(BaseModel):
    kind: Literal["assign"] = "assign"
    target: LValue
    expr: Expr


class Call(BaseModel):
    # CALL f(x, y)  (llamada "void")
    kind: Literal["call"] = "call"
    name: str
    args: List[Expr] = []


class Block(BaseModel):
    kind: Literal["block"] = "block"
    stmts: List["Stmt"] = []


class If(BaseModel):
    kind: Literal["if"] = "if"
    cond: Expr
    then_body: List["Stmt"]
    else_body: Optional[List["Stmt"]] = None


class For(BaseModel):
    kind: Literal["for"] = "for"
    var: str
    start: Expr
    end: Expr
    step: Optional[Expr] = None
    inclusive: bool = True  # "to" inclusivo, por si luego agregas variantes
    body: List["Stmt"]


class While(BaseModel):
    kind: Literal["while"] = "while"
    cond: Expr
    body: List["Stmt"]


class Repeat(BaseModel):
    kind: Literal["repeat"] = "repeat"
    body: List["Stmt"]
    until: Expr


Stmt = Union[Assign, Call, Block, If, For, While, Repeat]


# ===========
# PROGRAMA
# ===========
class Program(BaseModel):
    kind: Literal["program"] = "program"
    body: List[Stmt]


# Reconstruye referencias hacia delante (Pydantic v2)
for _M in (Range, Index, Field, UnOp, BinOp, FuncCall, Assign, Call, Block, If, For, While, Repeat, Program):
    _M.model_rebuild()
