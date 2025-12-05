"""Modelos del Árbol de Sintaxis Abstracta (AST).

Define las clases Pydantic que representan la estructura del AST:
- SrcLoc: ubicación en código fuente
- Expresiones: Num, Bool, Var, UnOp, BinOp, FuncCall, Range, etc.
- Sentencias: Assign, For, While, If, Repeat, Call, Block
- Procedimientos: Proc, Program

Permite validación y serialización JSON automática.
"""

from typing import List, Optional, Union, Literal
from pydantic import BaseModel, Field as PydField


# UBICACIÓN EN CÓDIGO FUENTE

class SrcLoc(BaseModel):
    """
    Representa la posición de un token en el código fuente.

    Atributos:
        line (int): número de línea (1-based).
        column (int): número de columna (1-based).
    """
    line: int
    column: int


class NodeWithLoc(BaseModel):
    """
    Clase base para nodos que incluyen ubicación opcional (`loc`).
    """
    loc: Optional[SrcLoc] = None


# ---------------------------------------------------------------------------
# 2. EXPRESIONES (sin ubicación)
# ---------------------------------------------------------------------------

class Num(BaseModel):
    """Literal numérico (entero)."""
    kind: Literal["num"] = "num"
    value: int


class Bool(BaseModel):
    """Literal booleano (true / false)."""
    kind: Literal["bool"] = "bool"
    value: bool


class NullLit(BaseModel):
    """Literal nulo (NULL)."""
    kind: Literal["null"] = "null"


class Var(BaseModel):
    """Referencia a una variable por nombre."""
    kind: Literal["var"] = "var"
    name: str


class Range(BaseModel):
    """
    Rango de valores (por ejemplo, en bucles o subíndices).

    Ejemplo:
        1..10  →  Range(lo=1, hi=10)
    """
    kind: Literal["range"] = "range"
    lo: "Expr"
    hi: "Expr"


class Index(BaseModel):
    """
    Acceso a un índice o rango de un arreglo.

    Atributos:
        base (LValue): expresión base (p. ej. variable o campo).
        index (IndexKey): índice único o rango.
    """
    kind: Literal["index"] = "index"
    base: "LValue"
    index: "IndexKey"  # Expr | Range


class Field(BaseModel):
    """Acceso a un campo dentro de un registro u objeto."""
    kind: Literal["field"] = "field"
    base: "LValue"
    field: str


# Aliases para tipos expresivos
LValue = Union[Var, Index, Field]
IndexKey = Union["Expr", Range]


class UnOp(BaseModel):
    """Operador unario (not, -)."""
    kind: Literal["unop"] = "unop"
    op: str
    expr: "Expr"


class BinOp(BaseModel):
    """Operador binario (por ejemplo: +, -, *, /, <, and, or, etc.)."""
    kind: Literal["binop"] = "binop"
    op: str
    left: "Expr"
    right: "Expr"


class FuncCall(BaseModel):
    """Llamada a función integrada o definida."""
    kind: Literal["funcall"] = "funcall"
    name: str
    args: List["Expr"] = PydField(default_factory=list)


# Conjunto total de expresiones válidas
Expr = Union[Num, Bool, NullLit, LValue, UnOp, BinOp, FuncCall, Range]


# SENTENCIAS

class Assign(NodeWithLoc):
    """Sentencia de asignación: <variable> <- <expresión>."""
    kind: Literal["assign"] = "assign"
    target: LValue
    expr: Expr


class Call(NodeWithLoc):
    """Llamada a procedimiento sin valor de retorno."""
    kind: Literal["call"] = "call"
    name: str
    args: List[Expr] = PydField(default_factory=list)


class Block(NodeWithLoc):
    """Bloque de sentencias BEGIN ... END."""
    kind: Literal["block"] = "block"
    stmts: List["Stmt"] = PydField(default_factory=list)


class If(NodeWithLoc):
    """Estructura condicional IF-THEN-(ELSE)."""
    kind: Literal["if"] = "if"
    cond: Expr
    then_body: List["Stmt"]
    else_body: Optional[List["Stmt"]] = None


class For(NodeWithLoc):
    """Bucle FOR con contador."""
    kind: Literal["for"] = "for"
    var: str
    start: Expr
    end: Expr
    step: Optional[Expr] = None
    inclusive: bool = True
    body: List["Stmt"]


class While(NodeWithLoc):
    """Bucle WHILE cond DO ..."""
    kind: Literal["while"] = "while"
    cond: Expr
    body: List["Stmt"]


class Repeat(NodeWithLoc):
    """Bucle REPEAT ... UNTIL cond."""
    kind: Literal["repeat"] = "repeat"
    body: List["Stmt"]
    until: Expr


# PROCEDIMIENTOS Y PROGRAMA

class Proc(BaseModel):
    """
    Definición de un procedimiento.

    Atributos:
        name (str): nombre del procedimiento.
        params (List[str]): parámetros formales.
        body (List[Stmt]): cuerpo del procedimiento.
    """
    kind: Literal["proc"] = "proc"
    name: str
    params: List[str] = PydField(default_factory=list)
    body: List["Stmt"] = PydField(default_factory=list)


# Tipo unión de todas las sentencias válidas (sin incluir Proc)
Stmt = Union[Assign, For, While, If, Repeat, Call, Block]


class Program(BaseModel):
    """
    Nodo raíz del programa, compuesto por sentencias y/o procedimientos.

    Atributos:
        body (List[Union[Stmt, Proc]]): lista de instrucciones principales.
    """
    kind: Literal["program"] = "program"
    body: List[Union[Stmt, Proc]] = PydField(default_factory=list)


# RECONSTRUCCIÓN DE REFERENCIAS CIRCULARES

# Pydantic requiere este paso para resolver forward refs
for _M in (
        Range, Index, Field, UnOp, BinOp, FuncCall,
        Assign, Call, Block, If, For, While, Repeat,
        Proc, Program,
):
    _M.model_rebuild()
