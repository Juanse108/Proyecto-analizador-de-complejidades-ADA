"""
ast_builder.py — Construcción del AST desde el parse tree
=========================================================

Responsabilidad: transformar el parse tree de Lark en AST del dominio.

Nota: Este archivo contiene el Transformer BuildAST extraído de parser.py
pero ahora con responsabilidades más claras y métodos auxiliares separados.
"""

from typing import List, Optional
from lark import Transformer, v_args, Token

from ..domain.ast_models import *


# ============================================================================
# UTILIDADES DE CONSTRUCCIÓN
# ============================================================================

class ASTBuilderUtils:
    """Métodos auxiliares para construcción del AST."""

    @staticmethod
    def extract_location(tok: Token) -> SrcLoc:
        """Extrae ubicación de un token."""
        return SrcLoc(line=tok.line, column=tok.column)

    @staticmethod
    def fold_binary_ops(first, rest_pairs):
        """
        Pliega operaciones binarias asociativas de izquierda a derecha.

        Args:
            first: Primer operando
            rest_pairs: [op, operando, op, operando, ...]
        """
        node = first
        ops = rest_pairs[::2]
        rhs = rest_pairs[1::2]
        for op_tok, right in zip(ops, rhs):
            node = BinOp(op=op_tok.value, left=node, right=right)
        return node

    @staticmethod
    def normalize_relational_op(op_token: Token) -> str:
        """Normaliza operadores relacionales a su forma estándar."""
        rel_map = {
            "EQ": "==",
            "NE": "!=",
            "LT": "<",
            "LE": "<=",
            "GT": ">",
            "GE": ">=",
        }
        return rel_map.get(op_token.type, op_token.value)

    @staticmethod
    def filter_tokens(*items):
        """Filtra tokens y devuelve solo nodos AST."""
        return [it for it in items if not isinstance(it, Token)]


# ============================================================================
# TRANSFORMER PRINCIPAL
# ============================================================================

@v_args(inline=True)
class BuildAST(Transformer):
    """
    Transformer de Lark → AST del dominio.

    Cada método corresponde a una regla de la gramática.
    """

    def __init__(self):
        super().__init__()
        self.utils = ASTBuilderUtils()

    # ------------------------------------------------------------------------
    # PROGRAMA Y TOPLEVEL
    # ------------------------------------------------------------------------

    def program(self, *items):
        """Nodo raíz del programa."""
        body = []
        for it in items:
            if it is None or (isinstance(it, Token) and it.type == "SEP"):
                continue
            if isinstance(it, list):
                body.extend(it)
            else:
                body.append(it)
        return Program(body=body)

    def top_unit(self, item):
        """Unidad toplevel (proc, class, block)."""
        return item

    def stmt_list(self, *stmts):
        """Lista de sentencias."""
        out = []
        for s in stmts:
            if s is None or (isinstance(s, Token) and s.type == "SEP"):
                continue
            if isinstance(s, list):
                out.extend(s)
            else:
                out.append(s)
        return out

    def line(self, *items):
        """Línea individual."""
        out = []
        for it in items:
            if it is None or (isinstance(it, Token) and it.type == "SEP"):
                continue
            if isinstance(it, list):
                out.extend(it)
            else:
                out.append(it)
        return out

    # ------------------------------------------------------------------------
    # BLOQUES
    # ------------------------------------------------------------------------

    def block(self, *items):
        """Bloque BEGIN...END."""
        begin_tok = None
        stmts = []

        for it in items:
            if isinstance(it, Token):
                if it.type == "BEGIN":
                    begin_tok = it
                continue
            stmts.extend(it if isinstance(it, list) else [it])

        loc = self.utils.extract_location(begin_tok) if begin_tok else None
        return Block(stmts=stmts, loc=loc)

    def block_or_list(self, *items):
        """Variante: block o lista simple."""
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

    # ------------------------------------------------------------------------
    # LITERALES
    # ------------------------------------------------------------------------

    def NUMBER(self, tok):
        return Num(value=int(tok.value))

    def true(self, _):
        return Bool(value=True)

    def false(self, _):
        return Bool(value=False)

    def NULL(self, _):
        return NullLit()

    # ------------------------------------------------------------------------
    # EXPRESIONES
    # ------------------------------------------------------------------------

    def or_expr(self, first, *rest):
        return self.utils.fold_binary_ops(first, rest)

    def and_expr(self, first, *rest):
        return self.utils.fold_binary_ops(first, rest)

    def not_expr(self, *items):
        if len(items) == 1:
            return items[0]
        expr = next(x for x in items if not isinstance(x, Token))
        return UnOp(op="not", expr=expr)

    def rel_expr(self, *items):
        if len(items) == 1:
            return items[0]
        left, op_tok, right = items
        op = self.utils.normalize_relational_op(op_tok)
        return BinOp(op=op, left=left, right=right)

    def sum(self, first, *rest):
        return self.utils.fold_binary_ops(first, rest)

    def prod(self, first, *rest):
        return self.utils.fold_binary_ops(first, rest)

    def neg(self, *items):
        expr = next(x for x in items if not isinstance(x, Token))
        return UnOp(op="-", expr=expr)

    # ------------------------------------------------------------------------
    # LVALUES
    # ------------------------------------------------------------------------

    def lvalue(self, *items):
        """Construye LValue (var/index/field)."""
        seq = []
        for it in items:
            if isinstance(it, Token) and it.type == "NAME":
                seq.append(it)
            elif not isinstance(it, Token):
                seq.append(it)

        node = Var(name=str(seq[0].value))

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

    def slice(self, *parts):
        """Slice o rango."""
        return parts[0] if len(parts) == 1 else Range(lo=parts[0], hi=parts[1])

    def subscript_list(self, *items):
        return list(items)

    # ------------------------------------------------------------------------
    # SENTENCIAS
    # ------------------------------------------------------------------------

    def assign(self, target, assign_tok, expr):
        return Assign(
            target=target,
            expr=expr,
            loc=self.utils.extract_location(assign_tok)
        )

    def for_loop(self, *items):
        """Bucle FOR."""
        for_tok = None
        name_tok = None
        parts = []

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
            loc=self.utils.extract_location(for_tok) if for_tok else None
        )

    def while_loop(self, *items):
        """Bucle WHILE."""
        while_tok = None
        non_tokens = []

        for it in items:
            if isinstance(it, Token):
                if it.type == "WHILE":
                    while_tok = it
                continue
            non_tokens.append(it)

        cond, body = non_tokens[0], non_tokens[1]
        body_list = body if isinstance(body, list) else [body]

        return While(
            cond=cond,
            body=body_list,
            loc=self.utils.extract_location(while_tok) if while_tok else None
        )

    def repeat_loop(self, *items):
        """Bucle REPEAT...UNTIL."""
        non_tokens = [it for it in items if not isinstance(it, Token)]
        body, cond = non_tokens[0], non_tokens[1]
        body_list = body if isinstance(body, list) else [body]
        rep_loc = body_list[0].loc if body_list else None

        return Repeat(body=body_list, until=cond, loc=rep_loc)

    def if_stmt(self, *items):
        """Condicional IF."""
        if_tok = None
        ast_items = []

        for it in items:
            if isinstance(it, Token):
                if it.type == "IF":
                    if_tok = it
                continue
            else:
                ast_items.append(it)

        if not ast_items:
            raise ValueError("if_stmt sin nodos AST")

        cond = ast_items[0]
        then_raw = ast_items[1] if len(ast_items) > 1 else []
        else_raw = ast_items[2] if len(ast_items) > 2 else None

        def to_list(node):
            if node is None:
                return []
            return node if isinstance(node, list) else [node]

        then_list = to_list(then_raw)
        else_list = to_list(else_raw) if else_raw is not None else None

        return If(
            cond=cond,
            then_body=then_list,
            else_body=else_list,
            loc=self.utils.extract_location(if_tok) if if_tok else None
        )

    def call_stmt(self, call_tok, name_tok, *maybe_args):
        """Llamada a procedimiento."""
        args = list(maybe_args[0]) if (maybe_args and isinstance(maybe_args[0], list)) else []
        return Call(
            name=str(name_tok),
            args=args,
            loc=self.utils.extract_location(call_tok)
        )

    # ------------------------------------------------------------------------
    # FUNCIONES Y PROCEDIMIENTOS
    # ------------------------------------------------------------------------

    def func_call(self, name_tok, *maybe_args):
        """Llamada a función en expresión."""
        args = []
        if maybe_args and isinstance(maybe_args[0], list):
            args = list(maybe_args[0])
        return FuncCall(name=str(name_tok), args=args)

    def arg_list(self, *items):
        args = []
        for it in items:
            if isinstance(it, Token):
                continue
            if isinstance(it, list):
                args.extend(it)
            else:
                args.append(it)
        return args

    def param(self, name_tok, *rest):
        return str(name_tok)

    def param_list(self, *names):
        return [str(t) for t in names]

    def proc_def(self, name_tok, *items):
        """Definición de procedimiento."""
        params = []
        body = []
        for it in items:
            if it is None:
                continue
            if isinstance(it, list):
                if it and isinstance(it[0], str):
                    params = it
                else:
                    body = it
        return Proc(name=str(name_tok), params=params, body=body)

    # ------------------------------------------------------------------------
    # ELEMENTOS IGNORADOS
    # ------------------------------------------------------------------------

    def expr_stmt(self, expr_node):
        """Sentencias de expresión (ignoradas)."""
        return None

    def return_stmt(self, *items):
        """Return (convertido a asignación ficticia)."""
        expr_nodes = [it for it in items if not isinstance(it, Token)]
        if not expr_nodes:
            return None
        return Assign(
            target=Var(name="_return"),
            expr=expr_nodes[0],
            loc=None
        )

    def object_decl(self, type_tok, name_tok):
        return None

    def decl_stmt(self, item):
        return [] if item is None else []

    def class_def(self, *items):
        return None

    def attr_list(self, *names):
        return None

    def ceil_brackets(self, *items):
        expr = next(x for x in items if not isinstance(x, Token))
        return FuncCall(name="ceil", args=[expr])

    def floor_brackets(self, *items):
        expr = next(x for x in items if not isinstance(x, Token))
        return FuncCall(name="floor", args=[expr])

    def rel_op(self, tok):
        return tok


def build_ast_from_tree(tree) -> Program:
    """
    Función pública para construir AST desde parse tree.

    Args:
        tree: Parse tree de Lark

    Returns:
        Program: AST del dominio
    """
    ast = BuildAST().transform(tree)
    assert isinstance(ast, Program), "El resultado debe ser un Program"
    return ast