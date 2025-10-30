# app/parser.py
from __future__ import annotations
from pathlib import Path
from typing import List, Iterable
from lark import Lark, Transformer, v_args, Token

from .ast_models import (
    Program, Block, Assign, Call, If, For, While, Repeat,
    Num, Bool, NullLit, Var, Range, Index, Field,
    UnOp, BinOp, FuncCall, Expr, LValue
)

__all__ = ["parse_to_ast"]

# =========================
# Carga gramática Lark
# =========================
GRAMMAR_PATH = Path(__file__).with_name("grammar").joinpath("pseudocode.lark")
with open(GRAMMAR_PATH, "r", encoding="utf-8") as f:
    _GRAMMAR = f.read()

_parser = Lark(
    _GRAMMAR,
    start="start",  # tu .lark tiene ?start: program
    parser="lalr",
    lexer="contextual",
    propagate_positions=True
)

# =========================
# Utilidades internas
# =========================
REL_MAP = {
    "EQ": "==",
    "NE": "!=",
    "NE2": "!=",
    "NE_U": "!=",
    "LT": "<",
    "LE": "<=",
    "LE_U": "<=",
    "GT": ">",
    "GE": ">=",
    "GE_U": ">=",
}


def _only_names_and_nodes(items: Iterable):
    """
    Ignora tokens que no nos interesan y conserva:
      - Token(NAME)
      - nodos ya transformados (Expr/Range/list)
    """
    out = []
    for it in items:
        if isinstance(it, Token):
            if it.type == "NAME":
                out.append(it)
        else:
            out.append(it)
    return out


def _fold_bin(first, rest_pairs):
    """
    Convierte secuencias (op, expr, op, expr, ...) en BinOp encadenados.
    """
    node = first
    ops = rest_pairs[::2]
    rhs = rest_pairs[1::2]
    for op_tok, right in zip(ops, rhs):
        op = op_tok.value
        node = BinOp(op=op, left=node, right=right)
    return node


@v_args(inline=True)
@v_args(inline=True)
class BuildAST(Transformer):
    # ========= programa / listas / bloque =========
    def program(self, *stmts):
        body = []
        for s in stmts:
            if s is None:
                continue
            if isinstance(s, list):
                body.extend(s)
            else:
                body.append(s)
        return Program(body=body)

    # IMPORTANTE: mantenemos stmt_list por si aparece explícito (como en repeat_loop)
    def stmt_list(self, *stmts):
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
        # Recibe: BEGIN, [stmt, stmt, ...], END (con ?stmt_list inline)
        from lark.lexer import Token
        stmts = []
        for it in items:
            if isinstance(it, Token):
                continue  # ignora BEGIN/END
            if isinstance(it, list):
                stmts.extend(it)
            else:
                stmts.append(it)
        return Block(stmts=stmts)

    def block_or_list(self, *items):
        # Puede venir un Block o N sentencias sueltas
        from .ast_models import Block
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

    # ============== literales / átomos ==============
    def NUMBER(self, tok: Token):
        return Num(value=int(tok.value))

    def true(self, _):
        return Bool(value=True)

    def false(self, _):
        return Bool(value=False)

    def NULL(self, _):
        return NullLit()

    def ceil_brackets(self, *items):
        from lark.lexer import Token
        expr = next(x for x in items if not isinstance(x, Token))
        return FuncCall(name="ceil", args=[expr])

    def floor_brackets(self, *items):
        from lark.lexer import Token
        expr = next(x for x in items if not isinstance(x, Token))
        return FuncCall(name="floor", args=[expr])

    def func_call(self, name_tok: Token, *maybe_args):
        args = list(maybe_args[0]) if (maybe_args and isinstance(maybe_args[0], list)) else []
        return FuncCall(name=str(name_tok), args=args)

    # ============== rel_op: evita "Tree(Token('RULE','rel_op'),...)" ==============
    def rel_op(self, tok):
        return tok

    # ============== lvalues e índices ==============
    def slice(self, *parts):
        if len(parts) == 1:
            return parts[0]
        return Range(lo=parts[0], hi=parts[1])

    def lvalue(self, *items):
        def _only_names_and_nodes(items):
            out = []
            for it in items:
                if isinstance(it, Token):
                    if it.type == "NAME":
                        out.append(it)
                else:
                    out.append(it)
            return out

        seq = _only_names_and_nodes(items)
        assert seq and isinstance(seq[0], Token) and seq[0].type == "NAME", "lvalue mal formado"
        node: LValue = Var(name=str(seq[0].value))
        for it in seq[1:]:
            if isinstance(it, Token) and it.type == "NAME":
                node = Field(base=node, field=str(it.value))
            else:
                # 'it' puede ser: Expr, Range, o lista de Expr/Range (subscript_list)
                if isinstance(it, list):
                    # M[i,j] => Index(Index(M, i), j)
                    for sub in it:
                        node = Index(base=node, index=sub)
                else:
                    node = Index(base=node, index=it)
        return node

    # ============== sentencias ==============
    def assign(self, target, _assign_tok, expr):
        return Assign(target=target, expr=expr)

    def call_stmt(self, _CALL, name_tok: Token, *maybe_args):
        args = list(maybe_args[0]) if (maybe_args and isinstance(maybe_args[0], list)) else []
        return Call(name=str(name_tok), args=args)

    def arg_list(self, *args):
        return list(args)

    def if_stmt(self, _IF, cond, _THEN, then_body, *rest):
        then_list = then_body if isinstance(then_body, list) else [then_body]
        else_list = None
        if rest and isinstance(rest[0], Token) and rest[0].type == "ELSE":
            raw = rest[1]
            else_list = raw if isinstance(raw, list) else [raw]
        return If(cond=cond, then_body=then_list, else_body=else_list)

    def for_loop(self, *items):
        # Tras la transformación de hijos, items ya no incluye keywords;
        # lo seguro: filtrar a NAME/Expr/list
        seq = []
        for it in items:
            if isinstance(it, Token):
                if it.type == "NAME":
                    seq.append(it)
            else:
                seq.append(it)
        name_tok = seq[0]
        start = seq[1]
        end = seq[2]
        if len(seq) == 5:
            step, body = seq[3], seq[4]
        else:
            step, body = None, seq[3]
        body_list = body if isinstance(body, list) else [body]
        return For(var=str(name_tok.value), start=start, end=end, step=step, inclusive=True, body=body_list)

    def while_loop(self, *items):
        seq = [it for it in items if not isinstance(it, Token)]
        cond, body = seq[0], seq[1]
        body_list = body if isinstance(body, list) else [body]
        return While(cond=cond, body=body_list)

    def repeat_loop(self, *items):
        # REPEAT stmt_list UNTIL "(" bool_expr ")"
        # Tras transformar, esperamos [body(list) , cond(Expr)]
        seq = [it for it in items if not isinstance(it, Token)]
        if len(seq) != 2:
            # Si el cuerpo llegó como Tree('stmt_list'), retransformarlo
            from lark import Tree
            body = seq[0]
            if isinstance(body, Tree) and body.data == "stmt_list":
                body = self.stmt_list(*body.children)
                cond = seq[-1]
                return Repeat(body=body, until=cond)
            # fallback defensivo
        body, cond = seq[0], seq[1]
        body_list = body if isinstance(body, list) else [body]
        return Repeat(body=body_list, until=cond)

    # ============== booleanas ==============
    def or_expr(self, first, *rest):
        return _fold_bin(first, rest)

    def and_expr(self, first, *rest):
        return _fold_bin(first, rest)

    def subscript_list(self, *items):
        # Devuelve lista de índices: cada ítem es Expr o Range
        return list(items)

    def not_expr(self, *items):
        if len(items) == 1:
            return items[0]
        expr = next(x for x in items if not isinstance(x, Token))
        return UnOp(op="not", expr=expr)

    def rel_expr(self, *items):
        if len(items) == 1:
            return items[0]
        left, op_tok, right = items
        op = op_tok.type if isinstance(op_tok, Token) else str(op_tok)
        # normaliza a símbolos canónicos
        REL_MAP = {"EQ": "==", "NE": "!=", "NE2": "!=", "NE_U": "!=", "LT": "<", "LE": "<=", "LE_U": "<=", "GT": ">",
                   "GE": ">=", "GE_U": ">="}
        op = REL_MAP.get(op, op)
        return BinOp(op=op, left=left, right=right)

    # ============== aritméticas ==============
    def sum(self, first, *rest):
        return _fold_bin(first, rest)

    def prod(self, first, *rest):
        return _fold_bin(first, rest)

    def neg(self, *items):
        from lark.lexer import Token
        expr = next(x for x in items if not isinstance(x, Token))
        return UnOp(op="-", expr=expr)


def parse_to_ast(code: str) -> Program:
    tree = _parser.parse(code)
    ast = BuildAST().transform(tree)
    assert isinstance(ast, Program)
    return ast
