"""
parser.py — Analizador sintáctico del microservicio
===================================================

Este módulo implementa el parser encargado de convertir código
pseudocódigo en un Árbol de Sintaxis Abstracta (AST), utilizando la
librería Lark y los modelos definidos en `ast_models.py`.

El proceso general es:
1. Cargar la gramática Lark (`grammar/pseudocode.lark`).
2. Construir un parser LALR contextual.
3. Transformar el árbol sintáctico de Lark en un AST propio del dominio.
4. Devolver un nodo raíz `Program` representando todo el programa.


"""

from pathlib import Path
from typing import Optional, List
from lark import Lark, Transformer, v_args, Token

# Importación de clases del modelo AST
from .ast_models import (
    Program, Block, Assign, Call, If, For, While, Repeat, Proc,
    Num, Bool, NullLit, Var, Range, Index, Field,
    UnOp, BinOp, FuncCall, LValue, SrcLoc
)

__all__ = ["parse_to_ast"]

# ---------------------------------------------------------------------------
# CONFIGURACIÓN DEL PARSER
# ---------------------------------------------------------------------------

# Ruta de la gramática del pseudocódigo
GRAMMAR_PATH = Path(__file__).with_name("grammar").joinpath("pseudocode.lark")

# Cargar la gramática
with open(GRAMMAR_PATH, "r", encoding="utf-8") as f:
    _GRAMMAR = f.read()

# Inicialización del parser LALR (contextual)
_parser = Lark(
    _GRAMMAR,
    start="start",
    parser="lalr",
    lexer="contextual",
    propagate_positions=True
)

# Mapa de equivalencias para operadores relacionales
REL_MAP = {
    "EQ": "==", "NE": "!=", "LT": "<", "LE": "<=", "GT": ">", "GE": ">="
}


# ---------------------------------------------------------------------------
# FUNCIONES AUXILIARES
# ---------------------------------------------------------------------------

def _loc(tok: Token) -> SrcLoc:
    """
    Convierte un token en un objeto SrcLoc (línea y columna).

    Args:
        tok (Token): token de la gramática con atributos de posición.

    Returns:
        SrcLoc: ubicación fuente (línea y columna).
    """
    return SrcLoc(line=tok.line, column=tok.column)


def _fold_bin(first, rest_pairs):
    """
    Aplica una secuencia de operaciones binarias (por ejemplo: a+b+c)
    de izquierda a derecha, generando un árbol BinOp anidado.

    Args:
        first: expresión inicial.
        rest_pairs (list): lista alternada de operadores y operandos derechos.

    Returns:
        BinOp: árbol binario compuesto.
    """
    node = first
    ops = rest_pairs[::2]
    rhs = rest_pairs[1::2]
    for op_tok, right in zip(ops, rhs):
        node = BinOp(op=op_tok.value, left=node, right=right)
    return node


# ---------------------------------------------------------------------------
# CONSTRUCCIÓN DEL AST
# ---------------------------------------------------------------------------

@v_args(inline=True)
class BuildAST(Transformer):
    """
    Transformer que convierte el árbol sintáctico (parse tree) generado por Lark
    en una representación interna del AST basada en `ast_models.py`.
    """

    # ==============================
    # 1) Estructura de Programa
    # ==============================
    def program(self, *items):
        """Programa principal compuesto por una lista de sentencias o procedimientos."""
        body = []
        for it in items:
            if it is None:
                continue
            if isinstance(it, list):
                body.extend(it)
            else:
                body.append(it)
        return Program(body=body)

    def stmt_list(self, *stmts):
        """Lista de sentencias secuenciales."""
        out = []
        for s in stmts:
            if s is None:
                continue
            if isinstance(s, list):
                out.extend(s)
            else:
                out.append(s)
        return out

    def block(self, *items):
        """Bloque BEGIN...END que agrupa sentencias."""
        begin_tok: Optional[Token] = None
        stmts: List = []
        for it in items:
            if isinstance(it, Token):
                if it.type == "BEGIN":
                    begin_tok = it
                continue
            stmts.extend(it if isinstance(it, list) else [it])
        return Block(stmts=stmts, loc=_loc(begin_tok) if begin_tok else (stmts[0].loc if stmts else None))

    def block_or_list(self, *items):
        """Permite bloques explícitos o listas simples de sentencias."""
        if len(items) == 1 and isinstance(items[0], Block):
            return items[0].stmts
        out = []
        for it in items:
            if it is None:
                continue
            if isinstance(it, list):
                out.extend(it)
            else:
                out.append(it)
        return out

    # ==============================
    # 2) Procedimientos
    # ==============================
    def param_list(self, *names):
        """Lista de parámetros de un procedimiento."""
        return [str(t) for t in names]

    def proc_def(self, name_tok, *items):
        """Definición de un procedimiento."""
        params: List[str] = []
        body: List = []
        for it in items:
            if it is None:
                continue
            if isinstance(it, list):
                if it and isinstance(it[0], str):
                    params = it
                else:
                    body = it
        return Proc(name=str(name_tok), params=params, body=body)

    # ==============================
    # 3) Literales / Átomos
    # ==============================
    def NUMBER(self, tok):
        return Num(value=int(tok.value))

    def true(self, _):
        return Bool(value=True)

    def false(self, _):
        return Bool(value=False)

    def NULL(self, _):
        return NullLit()

    def ceil_brackets(self, *items):
        expr = next(x for x in items if not isinstance(x, Token))
        return FuncCall(name="ceil", args=[expr])

    def floor_brackets(self, *items):
        expr = next(x for x in items if not isinstance(x, Token))
        return FuncCall(name="floor", args=[expr])

    def func_call(self, name_tok: Token, *maybe_args):
        args = list(maybe_args[0]) if (maybe_args and isinstance(maybe_args[0], list)) else []
        return FuncCall(name=str(name_tok), args=args)

    def rel_op(self, tok):
        return tok

    # ==============================
    # 4) LValues / Accesos
    # ==============================
    def slice(self, *parts):
        """Genera un rango (slice) de índices."""
        return parts[0] if len(parts) == 1 else Range(lo=parts[0], hi=parts[1])

    def subscript_list(self, *items):
        return list(items)

    def lvalue(self, *items):
        """Construye una referencia a variable, índice o campo."""
        seq: List = []
        for it in items:
            if isinstance(it, Token) and it.type == "NAME":
                seq.append(it)
            elif not isinstance(it, Token):
                seq.append(it)
        node: LValue = Var(name=str(seq[0].value))
        for it in seq[1:]:
            if isinstance(it, Token) and it.type == "NAME":
                node = Field(base=node, field=str(it.value))
            else:
                if isinstance(it, list):
                    for sub in it:
                        node = Index(base=node, index=sub)
                else:
                    node = Index(base=node, index=it)
        return node

    # ==============================
    # 5) Sentencias (con ubicación)
    # ==============================
    def assign(self, target, assign_tok: Token, expr):
        """Asignación: <variable> <- <expresión>."""
        return Assign(target=target, expr=expr, loc=_loc(assign_tok))

    def call_stmt(self, call_tok: Token, name_tok: Token, *maybe_args):
        """Llamada a procedimiento."""
        args = list(maybe_args[0]) if (maybe_args and isinstance(maybe_args[0], list)) else []
        return Call(name=str(name_tok), args=args, loc=_loc(call_tok))

    def if_stmt(self, if_tok: Token, cond, _THEN, then_body, *rest):
        """Estructura condicional IF-THEN-(ELSE)."""
        then_list = then_body if isinstance(then_body, list) else [then_body]
        else_list = None
        if rest and isinstance(rest[0], Token) and rest[0].type == "ELSE":
            raw = rest[1]
            else_list = raw if isinstance(raw, list) else [raw]
        return If(cond=cond, then_body=then_list, else_body=else_list, loc=_loc(if_tok))

    def for_loop(self, *items):
        """Bucle contado FOR i <- inicio TO fin [STEP paso] DO ..."""
        for_tok: Optional[Token] = None
        name_tok: Optional[Token] = None
        parts: List = []
        for it in items:
            if isinstance(it, Token):
                if it.type == "FOR":
                    for_tok = it
                elif it.type == "NAME" and name_tok is None:
                    name_tok = it
                continue
            parts.append(it)
        start, end = parts[0], parts[1]
        step, body = (parts[2], parts[3]) if len(parts) == 4 else (None, parts[2])
        body_list = body if isinstance(body, list) else [body]
        return For(
            var=str(name_tok.value) if name_tok else "",
            start=start,
            end=end,
            step=step,
            inclusive=True,
            body=body_list,
            loc=_loc(for_tok) if for_tok else None
        )

    def while_loop(self, *items):
        """Bucle WHILE cond DO ..."""
        while_tok: Optional[Token] = None
        non_tokens: List = []
        for it in items:
            if isinstance(it, Token):
                if it.type == "WHILE":
                    while_tok = it
                continue
            non_tokens.append(it)
        cond, body = non_tokens[0], non_tokens[1]
        body_list = body if isinstance(body, list) else [body]
        return While(cond=cond, body=body_list, loc=_loc(while_tok) if while_tok else None)

    def repeat_loop(self, *items):
        """Bucle REPEAT ... UNTIL cond."""
        non_tokens: List = [it for it in items if not isinstance(it, Token)]
        body, cond = non_tokens[0], non_tokens[1]
        body_list = body if isinstance(body, list) else [body]
        rep_loc = body_list[0].loc if body_list else None
        return Repeat(body=body_list, until=cond, loc=rep_loc)

    # ==============================
    # 6) Expresiones Lógicas / Aritméticas
    # ==============================
    def or_expr(self, first, *rest):
        return _fold_bin(first, rest)

    def and_expr(self, first, *rest):
        return _fold_bin(first, rest)

    def not_expr(self, *items):
        if len(items) == 1:
            return items[0]
        expr = next(x for x in items if not isinstance(x, Token))
        return UnOp(op="not", expr=expr)

    def rel_expr(self, *items):
        """Expresiones relacionales: <, <=, =, !=, etc."""
        if len(items) == 1:
            return items[0]
        left, op_tok, right = items
        op = REL_MAP.get(op_tok.type, op_tok.value) if isinstance(op_tok, Token) else str(op_tok)
        return BinOp(op=op, left=left, right=right)

    def sum(self, first, *rest):
        return _fold_bin(first, rest)

    def prod(self, first, *rest):
        return _fold_bin(first, rest)

    def neg(self, *items):
        """Negación aritmética: -x"""
        expr = next(x for x in items if not isinstance(x, Token))
        return UnOp(op="-", expr=expr)


# ---------------------------------------------------------------------------
# FUNCIÓN PÚBLICA
# ---------------------------------------------------------------------------

def parse_to_ast(code: str) -> Program:
    """
    Analiza un pseudocódigo y devuelve su representación interna (AST).

    Args:
        code (str): pseudocódigo en formato texto.

    Returns:
        Program: nodo raíz del árbol sintáctico abstracto.

    Raises:
        ValueError: si se detecta un error sintáctico en la entrada.
    """
    try:
        tree = _parser.parse(code)
        ast = BuildAST().transform(tree)
        assert isinstance(ast, Program)
        return ast
    except Exception as e:
        raise ValueError(f"Error de análisis sintáctico: {e}") from e
