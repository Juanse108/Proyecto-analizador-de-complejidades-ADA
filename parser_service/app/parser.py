"""
parser.py — Analizador sintáctico del microservicio de pseudocódigo
===================================================================

Este módulo implementa el parser encargado de convertir el pseudocódigo
(definido por la gramática `grammar/pseudocode.lark`) en un Árbol de
Sintaxis Abstracta (AST) propio del dominio, usando Lark y los modelos
definidos en `ast_models.py`.

Flujo general de análisis
-------------------------

1. Carga de la gramática
   - Se lee el archivo `grammar/pseudocode.lark` desde el mismo paquete.

2. Construcción del parser LALR contextual (`lark.Lark`)
   - Se configura con:
       * `start="start"`   → símbolo inicial de la gramática.
       * `parser="lalr"`   → algoritmo LALR(1).
       * `lexer="contextual"` → resuelve conflictos léxicos según contexto.
       * `propagate_positions=True` → cada token conserva línea y columna.

3. Transformación a AST
   - Lark produce un *parse tree*.
   - La clase `BuildAST`, que hereda de `lark.Transformer`, recorre el árbol
     y construye instancias de las clases de `ast_models.py`
     (`Program`, `Block`, `Assign`, `For`, `If`, etc.).

4. Función pública
   - `parse_to_ast(code: str) -> Program` es el punto de entrada
     utilizado por el microservicio.
"""

from pathlib import Path
from typing import Optional, List

from lark import Lark, Transformer, v_args, Token

# Importación de clases del modelo AST
from .ast_models import (
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


# ============================================================================
# 1. CONFIGURACIÓN DEL PARSER
# ============================================================================

# Ruta del archivo de gramática del pseudocódigo
GRAMMAR_PATH = Path(__file__).with_name("grammar").joinpath("pseudocode.lark")

# Carga del contenido de la gramática
with open(GRAMMAR_PATH, "r", encoding="utf-8") as f:
    _GRAMMAR = f.read()

# Instancia global de Lark (parser LALR) para evitar recarga repetida
_parser = Lark(
    _GRAMMAR,
    start="start",
    parser="lalr",
    lexer="contextual",
    propagate_positions=True,
)

# Mapa de equivalencias para operadores relacionales.
# Algunos tokens se normalizan a los operadores de Python, el resto
# se deja con su representación textual original.
REL_MAP = {
    "EQ": "==",
    "NE": "!=",
    "LT": "<",
    "LE": "<=",
    "GT": ">",
    "GE": ">=",
}


# ============================================================================
# 2. FUNCIONES AUXILIARES DE SOPORTE
# ============================================================================

def _loc(tok: Token) -> SrcLoc:
    """
    Convierte un token de Lark en un objeto `SrcLoc` (línea y columna).

    Args:
        tok: Token de Lark que contiene atributos de posición.

    Returns:
        Instancia de `SrcLoc` con línea y columna del token.
    """
    return SrcLoc(line=tok.line, column=tok.column)


def _fold_bin(first, rest_pairs):
    """
    Plegado de operaciones binarias asociativas de izquierda a derecha.

    Ejemplos de entrada lógica:
        - Regla sum:   a + b - c
        - Regla prod:  a * b / c
        - Reglas lógicas: expr1 and expr2 and expr3

    Recibe el primer operando y una lista alternada de
    [operador, operando_derecho, operador, operando_derecho, ...]
    y construye un árbol BinOp anidado.

    Args:
        first: Expresión inicial (lado izquierdo del primer operador).
        rest_pairs: Secuencia alternada de tokens de operador y expresiones.

    Returns:
        Nodo `BinOp` que representa la expresión binaria compuesta.
    """
    node = first
    ops = rest_pairs[::2]
    rhs = rest_pairs[1::2]
    for op_tok, right in zip(ops, rhs):
        node = BinOp(op=op_tok.value, left=node, right=right)
    return node


# ============================================================================
# 3. TRANSFORMER: CONSTRUCCIÓN DEL AST
# ============================================================================

@v_args(inline=True)
class BuildAST(Transformer):
    """
    Transformer de Lark → AST.

    Esta clase recorre el árbol sintáctico generado por Lark y lo transforma
    en una representación interna basada en los modelos de `ast_models.py`.

    Características:
        - Maneja el toplevel como un `Program`.
        - Ignora elementos que no afectan el análisis de complejidad
          (clases, declaraciones de objetos, etc.).
        - Asigna información de ubicación (`loc`) a las sentencias relevantes
          para mejorar la reportabilidad de errores posteriores.
    """

    # ----------------------------------------------------------------------
    # 3.1. Estructura de programa / toplevel
    # ----------------------------------------------------------------------

    def program(self, *items):
        """
        Nodo raíz del programa.

        Agrupa unidades de nivel superior (bloques, procedimientos, etc.)
        en una lista `body` del nodo `Program`.
        """
        body = []
        for it in items:
            if it is None:
                continue

            # Ignorar separadores de línea a nivel toplevel, si aparecieran
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

        Después de transformar los hijos, `item` ya es un nodo de AST,
        por lo que simplemente se reenvía.
        """
        return item

    def stmt_list(self, *stmts):
        """
        Lista secuencial de sentencias dentro de un bloque o repeat.

        Normaliza a una lista plana de sentencias, filtrando `None`
        y separadores de línea.
        """
        out = []
        for s in stmts:
            if s is None:
                continue

            # Ignorar tokens SEP que actúan solo como separadores de línea
            if isinstance(s, Token) and s.type == "SEP":
                continue

            if isinstance(s, list):
                out.extend(s)
            else:
                out.append(s)

        return out

    def line(self, *items):
        """
        Regla de línea: `line: stmt? SEP`.

        Comportamiento deseado:
            - Línea en blanco (solo SEP)  → []
            - Línea con sentencia         → [sentencia]
        """
        out = []
        for it in items:
            if it is None:
                continue
            # Ignorar el SEP de fin de línea
            if isinstance(it, Token) and it.type == "SEP":
                continue
            if isinstance(it, list):
                out.extend(it)
            else:
                out.append(it)
        return out

    def block(self, *items):
        """
        Bloque BEGIN ... END que agrupa sentencias.

        Localización:
            - Si existe token `BEGIN`, se toma su línea/columna.
            - En caso contrario, se usa la de la primera sentencia del bloque.
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
        Variante auxiliar que permite bloques explícitos o listas simples
        de sentencias.

        Si se recibe un `Block`, se devuelven sus sentencias; en caso
        contrario, se aplanan los ítems en una lista.
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

    def expr_stmt(self, expr_node):
        """
        Sentencia de expresión (p. ej. `A[n]`, `A[10][m]`).

        Para el analizador de complejidades estas sentencias suelen ser
        irrelevantes, por lo que se devuelven como `None` para que
        `stmt_list` pueda filtrarlas.
        """
        return None

    # ----------------------------------------------------------------------
    # 3.2. Declaraciones / clases (normalmente ignoradas para complejidad)
    # ----------------------------------------------------------------------

    def array_decl(self, name_tok: Token, *dims):
        """
        Declaración de arreglo (si la gramática lo soporta), por ejemplo:

            A[n]
            A[10][m]

        Actualmente no se modela en el AST porque no afecta al análisis
        de complejidad; se devuelve `None`.
        """
        return None

    # ==============================
    # Sentencia return (ignorada)
    # ==============================
    def return_stmt(self, *items):
        """
        Sentencia 'return' [expr].

        Para el análisis de complejidad, un 'return' no aporta estructura
        relevante, así que la tratamos como una sentencia vacía.
        """
        return None

    def object_decl(self, type_tok: Token, name_tok: Token):
        """
        Declaración de objeto: `Clase nombre_objeto`.

        Para el análisis de complejidad no se necesitan instancias
        explícitas de objetos, por lo que la declaración se ignora.
        """
        return None

    def decl_stmt(self, item):
        """
        Normalización de declaraciones como sentencias.

        Si la declaración fue ignorada (devuelve `None`), esta regla
        retorna una lista vacía para que `stmt_list` pueda aplanar sin
        introducir valores nulos.
        """
        if item is None:
            return []
        # Si en el futuro se quisieran modelar, aquí podría envolverse
        # en un nodo específico. Por ahora se ignoran.
        return []

    def class_def(self, *items):
        """
        Definición de clase, por ejemplo:

            Casa {Area color propietario}

        Para el analizador de complejidad la estructura interna de la
        clase no es relevante, por lo que se devuelve `None`.
        """
        return None

    def attr_list(self, *names):
        """
        Lista de atributos de una clase.

        Aunque la gramática los reconoce, el AST de complejidad no los
        utiliza, así que se devuelve `None`.
        """
        return None

    # ----------------------------------------------------------------------
    # 3.3. Procedimientos y parámetros
    # ----------------------------------------------------------------------

    def param(self, name_tok, *rest):
        """
        Parámetro formal de un procedimiento.

        Ejemplos aceptados por la gramática:
            a
            a[1..n]
            A[1..n]

        En el AST sólo se conserva el nombre base (cadena).
        """
        return str(name_tok)

    def param_list(self, *names):
        """
        Lista de parámetros de un procedimiento.

        Returns:
            Lista de cadenas con los nombres de los parámetros.
        """
        return [str(t) for t in names]

    def proc_def(self, name_tok, *items):
        """
        Definición de procedimiento.

        Estructura general:
            nombre(param1, param2, ...) begin ... end

        Separamos el vector de parámetros y el cuerpo, y construimos un
        nodo `Proc`.
        """
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

    # ----------------------------------------------------------------------
    # 3.4. Literales y átomos
    # ----------------------------------------------------------------------

    def NUMBER(self, tok):
        """Literal numérico entero."""
        return Num(value=int(tok.value))

    def true(self, _):
        """Literal booleano verdadero (T / true)."""
        return Bool(value=True)

    def false(self, _):
        """Literal booleano falso (F / false)."""
        return Bool(value=False)

    def NULL(self, _):
        """Literal null."""
        return NullLit()

    def ceil_brackets(self, *items):
        """
        Operador de techo con brackets Unicode: ⌈expr⌉.

        Se traduce a una llamada de función genérica:
            ceil(expr)
        """
        expr = next(x for x in items if not isinstance(x, Token))
        return FuncCall(name="ceil", args=[expr])

    def floor_brackets(self, *items):
        """
        Operador de piso con brackets Unicode: ⌊expr⌋.

        Se traduce a una llamada de función genérica:
            floor(expr)
        """
        expr = next(x for x in items if not isinstance(x, Token))
        return FuncCall(name="floor", args=[expr])

    def func_call(self, name_tok: Token, *maybe_args):
        """
        Llamada a función en una expresión: nombre(expr1, expr2, ...).
        """
        args = list(maybe_args[0]) if (maybe_args and isinstance(maybe_args[0], list)) else []
        return FuncCall(name=str(name_tok), args=args)

    def rel_op(self, tok):
        """
        Operador relacional.

        Se deja como token para que `rel_expr` pueda decidir cómo
        normalizarlo (por ejemplo, usando `REL_MAP`).
        """
        return tok

    # ----------------------------------------------------------------------
    # 3.5. L-values: variables, índices y campos
    # ----------------------------------------------------------------------

    def slice(self, *parts):
        """
        Slice o rango de índices.

        Ejemplos:
            i
            1..n

        Si sólo hay una expresión, se devuelve tal cual.
        Si hay dos, se construye un `Range(lo, hi)`.
        """
        return parts[0] if len(parts) == 1 else Range(lo=parts[0], hi=parts[1])

    def subscript_list(self, *items):
        """Lista de índices/slices dentro de un acceso a arreglo."""
        return list(items)

    def lvalue(self, *items):
        """
        Construye un LValue (referencia a variable / campo / índice).

        Soporta formas como:
            x
            A[i]
            A[i, j+1, 3..k]
            objeto.campo
            objeto.campo[i].otro[j]
        """
        seq: List = []
        for it in items:
            if isinstance(it, Token) and it.type == "NAME":
                seq.append(it)
            elif not isinstance(it, Token):
                seq.append(it)

        # Punto de partida: variable base
        node: LValue = Var(name=str(seq[0].value))

        # Resto de componentes: campos o índices
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

    # ----------------------------------------------------------------------
    # 3.6. Sentencias con información de ubicación
    # ----------------------------------------------------------------------

    def assign(self, target, assign_tok: Token, expr):
        """
        Sentencia de asignación:

            <lvalue> <- <expr>
            <lvalue> 🡨 <expr>
        """
        return Assign(target=target, expr=expr, loc=_loc(assign_tok))

    def call_stmt(self, call_tok: Token, name_tok: Token, *maybe_args):
        """
        Llamada a procedimiento como sentencia:

            call nombre(arg1, arg2, ...)
        """
        args = list(maybe_args[0]) if (maybe_args and isinstance(maybe_args[0], list)) else []
        return Call(name=str(name_tok), args=args, loc=_loc(call_tok))

    def if_stmt(self, *items):
        """
        Estructura condicional IF-THEN-[ELSE].

        La gramática es:
            if_stmt: IF "(" bool_expr ")" THEN SEP? block_or_list (ELSE SEP? block_or_list)?

        Con @v_args(inline=True), aquí llegan:
            - Tokens: IF, '(', ')', THEN, ELSE, SEP...
            - Nodos AST: bool_expr, block_or_list (then), block_or_list (else opcional).

        Estrategia:
        - Nos quedamos solo con los nodos AST en orden.
        - El 1º es la condición.
        - El 2º es el cuerpo del THEN.
        - El 3º (si existe) es el cuerpo del ELSE.
        - Ignoramos todos los Token('SEP', ...), paréntesis, THEN, ELSE, etc.
        """
        if_tok: Optional[Token] = None
        ast_items = []

        for it in items:
            if isinstance(it, Token):
                # Guardamos la posición del IF para loc
                if it.type == "IF":
                    if_tok = it
                # TODO: ignoramos THEN, ELSE, SEP, paréntesis...
                continue
            else:
                # Es un nodo de AST (condición o cuerpos)
                ast_items.append(it)

        if not ast_items:
            raise ValueError("if_stmt sin nodos AST (condición/cuerpo).")

        # ast_items[0] = condición booleana
        cond = ast_items[0]

        # ast_items[1] = cuerpo del THEN (block_or_list), si existe
        then_raw = ast_items[1] if len(ast_items) > 1 else []

        # ast_items[2] = cuerpo del ELSE (block_or_list), si existe
        else_raw = ast_items[2] if len(ast_items) > 2 else None

        def _to_list(node):
            if node is None:
                return []
            return node if isinstance(node, list) else [node]

        then_list = _to_list(then_raw)
        else_list = _to_list(else_raw) if else_raw is not None else None

        return If(
            cond=cond,
            then_body=then_list,
            else_body=else_list,
            loc=_loc(if_tok) if if_tok else None,
        )

    def for_loop(self, *items):
        """
        Bucle contado FOR:

            for i <- inicio to fin [step paso] do
              begin
                ...
              end
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
        step, body = (parts[2], parts[3]) if len(parts) == 4 else (None, parts[2])
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

            while (cond) do
              begin
                ...
              end
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

        return While(
            cond=cond,
            body=body_list,
            loc=_loc(while_tok) if while_tok else None,
        )

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

    # ----------------------------------------------------------------------
    # 3.7. Expresiones lógicas y aritméticas
    # ----------------------------------------------------------------------

    def or_expr(self, first, *rest):
        """Expresión booleana con OR (asociación por la izquierda)."""
        return _fold_bin(first, rest)

    def and_expr(self, first, *rest):
        """Expresión booleana con AND (asociación por la izquierda)."""
        return _fold_bin(first, rest)

    def not_expr(self, *items):
        """
        Negación lógica.

        Si sólo se recibe una expresión, se devuelve tal cual.
        Si aparece el token NOT, se envuelve en un `UnOp("not", expr)`.
        """
        if len(items) == 1:
            return items[0]
        expr = next(x for x in items if not isinstance(x, Token))
        return UnOp(op="not", expr=expr)

    def rel_expr(self, *items):
        """
        Expresiones relacionales: <, <=, =, !=, etc.

        - Con un solo operando se devuelve tal cual (no hay comparación).
        - Con tres elementos se interpreta como: <expr1> <op> <expr2>.
        """
        if len(items) == 1:
            return items[0]

        left, op_tok, right = items
        op = REL_MAP.get(op_tok.type, op_tok.value) if isinstance(op_tok, Token) else str(op_tok)
        return BinOp(op=op, left=left, right=right)

    def sum(self, first, *rest):
        """Expresiones de suma y resta (+, -)."""
        return _fold_bin(first, rest)

    def prod(self, first, *rest):
        """Expresiones de producto y división (*, /, div, mod)."""
        return _fold_bin(first, rest)

    def neg(self, *items):
        """
        Negación aritmética unaria: `-x`.
        """
        expr = next(x for x in items if not isinstance(x, Token))
        return UnOp(op="-", expr=expr)


# ============================================================================
# 4. FUNCIÓN PÚBLICA DE ENTRADA
# ============================================================================

def parse_to_ast(code: str) -> Program:
    """
    Analiza un pseudocódigo y devuelve su representación interna (AST).

    Args:
        code:
            Cadena de texto con el pseudocódigo a analizar.

    Returns:
        Program:
            Nodo raíz del árbol sintáctico abstracto correspondiente al
            programa completo.

    Raises:
        ValueError:
            Si se produce cualquier error durante el análisis sintáctico
            o la transformación a AST.
    """
    try:
        tree = _parser.parse(code)
        ast = BuildAST().transform(tree)
        assert isinstance(ast, Program)
        return ast
    except Exception as e:
        # Se encapsula la excepción original para ofrecer un mensaje
        # más homogéneo hacia el microservicio que consume este módulo.
        raise ValueError(f"Error de análisis sintáctico: {e}") from e
