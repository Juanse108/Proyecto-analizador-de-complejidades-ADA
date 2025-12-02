"""
semantic_pass.py — Análisis y normalización semántica del pseudocódigo
======================================================================

Este módulo implementa una pasada semántica sobre el Árbol de Sintaxis
Abstracta (AST) generado por el parser.

Su propósito es **detectar inconsistencias y aplicar normalizaciones**,
por ejemplo:

- Asignar `step = 1` por defecto en bucles `for`.
- Verificar que las condiciones en `if`, `while` o `repeat` sean booleanas.
- Reportar advertencias o errores semánticos básicos.

La función principal `run_semantic()` recibe un `Program` y devuelve:
1. Un AST normalizado.
2. Una lista de issues (`Issue`) con errores o advertencias semánticas.


"""

from typing import List, Set, Tuple
from pydantic import BaseModel
from .ast_models import (
    Program, Stmt, Block, Assign, Call, If, For, While, Repeat,
    Expr, Num, Bool, UnOp, BinOp
)


# ---------------------------------------------------------------------------
# 1️. ESTRUCTURA DE ISSUE
# ---------------------------------------------------------------------------

class Issue(BaseModel):
    """
    Representa una advertencia o error detectado durante el análisis semántico.

    Atributos:
        severity (str): nivel de severidad ("error" o "warning").
        msg (str): descripción legible del problema.
        where (Optional[str]): referencia contextual (por ejemplo "for(var=i)").
    """
    severity: str
    msg: str
    where: str | None = None


# ---------------------------------------------------------------------------
# 2️. CONJUNTOS DE OPERADORES PERMITIDOS
# ---------------------------------------------------------------------------

# Operadores relacionales aceptados en expresiones booleanas
_REL_OPS: Set[str] = {"==", "!=", "<", "<=", ">", ">="}

# Operadores booleanos lógicos
_BOOL_BIN: Set[str] = {"and", "or"}


# ---------------------------------------------------------------------------
# 3️. FUNCIONES AUXILIARES
# ---------------------------------------------------------------------------

def _looks_boolean(e: Expr) -> bool:
    """
    Determina heurísticamente si una expresión `Expr` parece ser booleana.

    Reglas:
        - Literales `Bool` siempre son booleanos.
        - UnOp "not" → depende de su subexpresión.
        - BinOp con operadores relacionales o lógicos → booleano probable.
        - Otros tipos → no booleanos.

    Args:
        e (Expr): expresión a verificar.

    Returns:
        bool: True si la expresión parece booleana, False en caso contrario.
    """
    if isinstance(e, Bool):
        return True
    if isinstance(e, UnOp):
        return e.op == "not" and _looks_boolean(e.expr)
    if isinstance(e, BinOp):
        if e.op in _REL_OPS:
            return True
        if e.op in _BOOL_BIN:
            # Conservador: se considera booleano si alguno de los operandos lo parece
            return _looks_boolean(e.left) or _looks_boolean(e.right)
    return False


def _normalize_for_step(s: For, issues: List[Issue]) -> For:
    """
    Normaliza un bucle FOR asegurando que tenga un `step` válido.

    - Si no se especifica, se asigna `step = 1`.
    - Si `step = 0`, se genera un error semántico.

    Args:
        s (For): nodo del bucle FOR.
        issues (List[Issue]): lista de issues acumuladas.

    Returns:
        For: nodo FOR normalizado.
    """
    step = s.step if s.step is not None else Num(value=1)

    if isinstance(step, Num) and step.value == 0:
        issues.append(Issue(
            severity="error",
            msg="El paso del for no puede ser 0",
            where=f"for(var={s.var})"
        ))

    # Normaliza el cuerpo recursivamente
    return For(
        var=s.var,
        start=s.start,
        end=s.end,
        step=step,
        inclusive=True,
        body=[_visit_stmt(b, issues) for b in s.body]
    )


# ---------------------------------------------------------------------------
# 4️. VISITADORES (recorrido del AST)
# ---------------------------------------------------------------------------

def _visit_stmt(s: Stmt, issues: List[Issue]) -> Stmt:
    """
    Visita recursivamente una sentencia (`Stmt`) aplicando chequeos
    semánticos y normalizaciones.

    Args:
        s (Stmt): sentencia a visitar.
        issues (List[Issue]): lista acumulativa de advertencias/errores.

    Returns:
        Stmt: sentencia posiblemente modificada (normalizada).
    """
    # ---- Caso: bucle FOR ----
    if isinstance(s, For):
        return _normalize_for_step(s, issues)

    # ---- Caso: WHILE ----
    if isinstance(s, While):
        if not _looks_boolean(s.cond):
            issues.append(Issue(
                severity="warning",
                msg="La condición del while no parece booleana (usa comparaciones o and/or/not)",
                where="while"
            ))
        return While(cond=s.cond, body=[_visit_stmt(b, issues) for b in s.body])

    # ---- Caso: IF ----
    if isinstance(s, If):
        if not _looks_boolean(s.cond):
            issues.append(Issue(
                severity="warning",
                msg="La condición del if no parece booleana",
                where="if"
            ))
        then_b = [_visit_stmt(b, issues) for b in s.then_body]
        else_b = [_visit_stmt(b, issues) for b in s.else_body] if s.else_body else None
        return If(cond=s.cond, then_body=then_b, else_body=else_b)

    # ---- Caso: REPEAT-UNTIL ----
    if isinstance(s, Repeat):
        if not _looks_boolean(s.until):
            issues.append(Issue(
                severity="warning",
                msg="La condición del until no parece booleana",
                where="repeat-until"
            ))
        return Repeat(body=[_visit_stmt(b, issues) for b in s.body], until=s.until)

    # ---- Caso: BLOQUE ----
    if isinstance(s, Block):
        return Block(stmts=[_visit_stmt(b, issues) for b in s.stmts])

    # ---- Otros casos (Assign / Call): sin modificación ----
    return s


# ---------------------------------------------------------------------------
# 5️. api PRINCIPAL
# ---------------------------------------------------------------------------

def run_semantic(ast: Program) -> Tuple[Program, List[Issue]]:
    """
    Ejecuta la pasada semántica sobre un programa completo.

    - Normaliza estructuras (e.g. step en FOR).
    - Verifica condiciones booleanas.
    - Acumula advertencias y errores semánticos.

    Args:
        ast (Program): árbol raíz del programa.

    Returns:
        Tuple[Program, List[Issue]]:
            - AST normalizado.
            - Lista de issues encontrados.
    """
    issues: List[Issue] = []
    norm_body = [_visit_stmt(s, issues) for s in ast.body]
    return Program(body=norm_body), issues
