"""
parser.py — Analizador sintáctico del microservicio
===================================================

Este módulo implementa el parser encargado de convertir pseudocódigo
en un Árbol de Sintaxis Abstracta (AST), utilizando la librería Lark
y los modelos definidos en `ast_models.py`.

Flujo general:
1. Cargar la gramática Lark (`grammar/pseudocode.lark`).
2. Construir un parser LALR contextual.
3. Transformar el árbol sintáctico de Lark en un AST propio del dominio.
4. Devolver un nodo raíz `Program` representando todo el programa.
"""

from pathlib import Path
from typing import Optional, List

from lark import Lark, Transformer, v_args, Token

# Importación de clases del modelo AST
from ast_models import (
    Program,
    Block,
    Assign,
    Call,
    If,
    For,
    While,
    Repeat,
    Proc,
    Num,
    Bool,
    NullLit,
    Var,
    Range,
    Index,
    Field,
    UnOp,
    BinOp,
    FuncCall,
    LValue,
    SrcLoc,
)

__all__ = ["parse_to_ast"]

# ---------------------------------------------------------------------------
# CONFIGURACIÓN DEL PARSER
# ---------------------------------------------------------------------------

# Ruta de la gramática del pseudocódigo
GRAMMAR_PATH = Path(__file__).with_name("grammar").joinpath("pseudocode.lark")

# Cargar la gramática desde disco
with open(GRAMMAR_PATH, "r", encoding="utf-8") as f:
    _GRAMMAR = f.read()

# Inicialización del parser LALR (contextual)
_parser = Lark(
    _GRAMMAR,
    start="start",
    parser="lalr",
    lexer="contextual",
    propagate_positions=True,
)

# Mapa de equivalencias para operadores relacionales
REL_MAP = {
    "EQ": "==",
    "NE": "!=",
    "LT": "<",
    "LE": "<=",
    "GT": ">",
    "GE": ">=",
}


# ---------------------------------------------------------------------------
# FUNCIONES AUXILIARES
# ---------------------------------------------------------------------------

def _loc(tok: Token) -> SrcLoc:
    """
    Convierte un token en un objeto SrcLoc (línea y columna).

    Args:
        tok: Token de la gramática con atributos de posición.

    Returns:
        SrcLoc: ubicación fuente (línea y columna).
    """
    return SrcLoc(line=tok.line, column=tok.column)


def _fold_bin(first, rest_pairs):
    """
    Aplica una secuencia de operaciones binarias (por ejemplo: a+b+c)
    de izquierda a derecha, generando un árbol BinOp anidado.

    Args:
        first: Expresión inicial.
        rest_pairs: Lista alternada [op1, rhs1, op2, rhs2, ...].

    Returns:
        BinOp: Árbol binario compuesto a partir de todos los términos.
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
    # 1) Programa y unidades toplevel
    # ==============================

    def program(self, *items):
        """
        Nodo raíz del programa.

        Agrupa top_units (bloques, procedimientos, clases) ya transformados
        en una lista `body` del modelo `Program`.
        """
        body = []
        for it in items:
            if it is None:
                continue

            # Ignorar separadores de línea a nivel toplevel, si aparecen.
            if isinstance(it, Token) and it.type == "SEP":
                continue

            if isinstance(it, list):
                body.extend(it)
            else:
                body.append(it)

        return Program(body=body)

    def top_unit(self, item):
        """
        Regla toplevel: `top_unit: class_def | proc_def | block`.

        Después de transformar los hijos, `item` ya es un AST (Block, Proc, etc.),
        así que simplemente se devuelve tal cual (o None si se ignora).
        """
        return item

    # ==============================
    # 2) Listas de sentencias y líneas
    # ==============================

    def expr_stmt(self, expr_node):
        """
        Sentencia de expresión (p.ej. `A[n]`, `A[10][m]`).

        Para el analizador de complejidades no aporta información,
        por lo que se ignora en el AST.
        """
        return None

    def line(self, *items):
        """
        Representa una línea dentro de un bloque: `line: stmt? SEP`.

        - Si la línea está vacía (solo SEP), devuelve [].
        - Si contiene una sentencia, devuelve [stmt].
        """
        out = []
        for it in items:
            if it is None:
                continue
            # Ignorar el token SEP final de la línea
            if isinstance(it, Token) and it.type == "SEP":
                continue
            if isinstance(it, list):
                out.extend(it)
            else:
                out.append(it)
        return out

    def stmt_list(self, *stmts):
        """
        Lista de sentencias secuenciales dentro de un bloque / repeat.

        Se encarga de:
        - Ignorar SEP sueltos.
        - Ignorar elementos None.
        - Aplanar las listas devueltas por `line`.
        """
        out = []
        for s in stmts:
            if s is None:
                continue

            # Ignorar los tokens SEP que son solo separadores de línea
            if isinstance(s, Token) and s.type == "SEP":
                continue

            if isinstance(s, list):
                out.extend(s)
            else:
                out.append(s)

        return out

    def block(self, *items):
        """
        Bloque BEGIN...END que agrupa sentencias.

        La ubicación (loc) del bloque se toma del token BEGIN, si está
        disponible; en su defecto, del primer statement.
        """
        begin_tok: Optional[Token] = None
        stmts: List = []
        for it in items:
            if isinstance(it, Token):
                if it.type == "BEGIN":
                    begin_tok = it
                continue
            stmts.extend(it if isinstance(it, list) else [it])

        loc = _loc(begin_tok) if begin_tok else (stmts[0].loc if stmts else None)
        return Block(stmts=stmts, loc=loc)

    def block_or_list(self, *items):
        """
        Permite bloques explícitos o listas simples de sentencias.

        Aunque actualmente la gramática no usa esta regla, se mantiene
        por compatibilidad con diseños anteriores.
        """
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
    # 3) Declaraciones (ignoradas en el AST)
    # ==============================

    def array_decl(self, name_tok: Token, *dims):
        """
        Declaración de arreglo: A[n], A[10][m], etc.

        La gramática actual valida estas formas, pero para el analizador
        de complejidades no son relevantes, por lo que se ignoran.
        """
        return None  # no genera nodo de AST

    def object_decl(self, type_tok: Token, name_tok: Token):
        """
        Declaración de objeto: `Clase nombre_objeto`.

        También se ignora en el AST (no afecta la complejidad).
        """
        return None

    def decl_stmt(self, item):
        """
        Normaliza declaraciones dentro de `stmt_list`.

        Si la declaración fue ignorada (None), se devuelve una lista vacía,
        de modo que no aparezca ningún nodo en la lista de sentencias.
        """
        if item is None:
            return []
        # Si en algún momento se decidiera modelarlas, aquí podría
        # construirse un nodo específico. Por ahora, se ignoran.
        return []

    # ==============================
    # 4) Clases (toplevel) — ignoradas en AST
    # ==============================

    def class_def(self, *items):
        """
        Definición de clase: `Casa {Area color propietario}`.

        Para el analizador de complejidades no se requiere modelar
        las clases, por lo que esta construcción se ignora en el AST.
        """
        return None

    def attr_list(self, *names):
        """
        Lista de atributos dentro de una definición de clase.

        No se utiliza en el AST de complejidad, de modo que se ignora.
        """
        return None

    # ==============================
    # 5) Procedimientos
    # ==============================

    def param(self, name_tok, *rest):
        """
        Parámetro formal de procedimiento.

        Ejemplos admitidos:
            a
            a[1..n]
            A[1..n]

        Aunque la sintaxis permite índices/rangos, en el AST solo se
        conserva el nombre base del parámetro.
        """
        return str(name_tok)

    def param_list(self, *names):
        """
        Lista de parámetros de un procedimiento.

        Devuelve una lista de nombres (str).
        """
        return [str(t) for t in names]

    def proc_def(self, name_tok, *items):
        """
        Definición de un procedimiento.

        Forma general:
            Nombre(params) begin
                ...
            end
        """
        params: List[str] = []
        body: List = []
        for it in items:
            if it is None:
                continue
            if isinstance(it, list):
                # Si la lista contiene strings, se asume que son nombres de parámetros
                if it and isinstance(it[0], str):
                    params = it
                else:
                    body = it
        return Proc(name=str(name_tok), params=params, body=body)

    # ==============================
    # 6) Literales / Átomos
    # ==============================

    def NUMBER(self, tok):
        """Literal numérico entero."""
        return Num(value=int(tok.value))

    def true(self, _):
        """Literal booleano True."""
        return Bool(value=True)

    def false(self, _):
        """Literal booleano False."""
        return Bool(value=False)

    def NULL(self, _):
        """Literal nulo."""
        return NullLit()

    def ceil_brackets(self, *items):
        """
        Expresión de techo: ⌈ expr ⌉

        Se modela como una llamada a función `ceil(expr)`.
        """
        expr = next(x for x in items if not isinstance(x, Token))
        return FuncCall(name="ceil", args=[expr])

    def floor_brackets(self, *items):
        """
        Expresión de piso: ⌊ expr ⌋

        Se modela como una llamada a función `floor(expr)`.
        """
        expr = next(x for x in items if not isinstance(x, Token))
        return FuncCall(name="floor", args=[expr])

    def func_call(self, name_tok: Token, *maybe_args):
        """
        Llamada a función en expresiones: `f(x, y, ...)`.
        """
        args = list(maybe_args[0]) if (maybe_args and isinstance(maybe_args[0], list)) else []
        return FuncCall(name=str(name_tok), args=args)

    def rel_op(self, tok):
        """
        Operador relacional crudo.

        Se devuelve el token tal cual para que `rel_expr` lo traduzca
        usando `REL_MAP`.
        """
        return tok

    # ==============================
    # 7) LValues / Accesos
    # ==============================

    def slice(self, *parts):
        """
        Genera un rango (slice) de índices.

        - Un solo término: índice simple.
        - Dos términos: rango `lo..hi`.
        """
        return parts[0] if len(parts) == 1 else Range(lo=parts[0], hi=parts[1])

    def subscript_list(self, *items):
        """Lista de índices/slices usados entre corchetes."""
        return list(items)

    def lvalue(self, *items):
        """
        Construye una referencia a variable, índice o campo.

        Soporta combinaciones como:
            A
            A[i]
            A[i][j]
            objeto.campo
            objeto.campo[i]
            ...
        """
        seq: List = []
        for it in items:
            if isinstance(it, Token) and it.type == "NAME":
                seq.append(it)
            elif not isinstance(it, Token):
                seq.append(it)

        # Base: variable simple
        node: LValue = Var(name=str(seq[0].value))

        # Resto: campos e índices encadenados
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
    # 8) Sentencias (con ubicación)
    # ==============================

    def assign(self, target, assign_tok: Token, expr):
        """
        Asignación:

            <lvalue> <- <expr>
        """
        return Assign(target=target, expr=expr, loc=_loc(assign_tok))

    def call_stmt(self, call_tok: Token, name_tok: Token, *maybe_args):
        """
        Llamada a procedimiento (statement):

            CALL Nombre(args)
        """
        args = list(maybe_args[0]) if (maybe_args and isinstance(maybe_args[0], list)) else []
        return Call(name=str(name_tok), args=args, loc=_loc(call_tok))

    def if_stmt(self, if_tok: Token, cond, _THEN, then_body, *rest):
        """
        Estructura condicional IF-THEN-(ELSE).

        Soporta la forma:

            if (cond) then begin
                ...
            end
            else begin
                ...
            end

        permitiendo que `else` vaya en la línea siguiente (SEP opcional).
        """
        # Cuerpo del THEN siempre es una lista de sentencias
        then_list = then_body if isinstance(then_body, list) else [then_body]

        # Filtrar SEP que pueda venir antes de ELSE
        filtered_rest = [
            r for r in rest
            if not (isinstance(r, Token) and r.type == "SEP")
        ]

        else_list = None
        # Si hay ELSE, estará en filtered_rest[0]
        if (
            len(filtered_rest) >= 2
            and isinstance(filtered_rest[0], Token)
            and filtered_rest[0].type == "ELSE"
        ):
            raw = filtered_rest[1]
            else_list = raw if isinstance(raw, list) else [raw]

        return If(cond=cond, then_body=then_list, else_body=else_list, loc=_loc(if_tok))

    def for_loop(self, *items):
        """
        Bucle contado:

            for i <- inicio to fin [step paso] do begin ... end
        """
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
        if len(parts) == 4:
            step, body = parts[2], parts[3]
        else:
            step, body = None, parts[2]

        body_list = body if isinstance(body, list) else [body]

        return For(
            var=str(name_tok.value) if name_tok else "",
            start=start,
            end=end,
            step=step,
            inclusive=True,
            body=body_list,
            loc=_loc(for_tok) if for_tok else None,
        )

    def while_loop(self, *items):
        """
        Bucle WHILE:

            while (cond) do begin ... end
        """
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
        """
        Bucle REPEAT ... UNTIL:

            repeat
                ...
            until (cond)
        """
        non_tokens: List = [it for it in items if not isinstance(it, Token)]
        body, cond = non_tokens[0], non_tokens[1]
        body_list = body if isinstance(body, list) else [body]
        rep_loc = body_list[0].loc if body_list else None
        return Repeat(body=body_list, until=cond, loc=rep_loc)

    # ==============================
    # 9) Expresiones lógicas y aritméticas
    # ==============================

    def or_expr(self, first, *rest):
        """Expresión OR encadenada."""
        return _fold_bin(first, rest)

    def and_expr(self, first, *rest):
        """Expresión AND encadenada."""
        return _fold_bin(first, rest)

    def not_expr(self, *items):
        """
        Negación lógica: `not expr`.

        Si solo hay un elemento, se devuelve directamente (paréntesis).
        """
        if len(items) == 1:
            return items[0]
        expr = next(x for x in items if not isinstance(x, Token))
        return UnOp(op="not", expr=expr)

    def rel_expr(self, *items):
        """
        Expresiones relacionales: <, <=, =, !=, etc.

        Si solo hay un operando, se devuelve tal cual.
        Caso contrario, se construye un `BinOp`.
        """
        if len(items) == 1:
            return items[0]
        left, op_tok, right = items
        op = REL_MAP.get(op_tok.type, op_tok.value) if isinstance(op_tok, Token) else str(op_tok)
        return BinOp(op=op, left=left, right=right)

    def sum(self, first, *rest):
        """Suma/resta encadenada."""
        return _fold_bin(first, rest)

    def prod(self, first, *rest):
        """Producto/división/mod encadenados."""
        return _fold_bin(first, rest)

    def neg(self, *items):
        """
        Negación aritmética: `-x`.

        Se traduce como un `UnOp` con operador "-".
        """
        expr = next(x for x in items if not isinstance(x, Token))
        return UnOp(op="-", expr=expr)


# ---------------------------------------------------------------------------
# FUNCIÓN PÚBLICA
# ---------------------------------------------------------------------------

def parse_to_ast(code: str) -> Program:
    """
    Analiza un pseudocódigo y devuelve su representación interna (AST).

    Args:
        code: Pseudocódigo en formato texto.

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
    except Exception as e:  # noqa: BLE001
        raise ValueError(f"Error de análisis sintáctico: {e}") from e
