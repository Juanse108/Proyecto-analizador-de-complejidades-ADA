from __future__ import annotations
from typing import List, Tuple, Set
from pydantic import BaseModel
from .ast_models import (
    Program, Stmt, Block, Assign, Call, If, For, While, Repeat,
    Expr, Num, Bool, UnOp, BinOp
)


# ---------- Estructura de issues (útil para el cliente) ----------
class Issue(BaseModel):
    severity: str  # "error" | "warning"
    msg: str
    where: str | None = None  # opcional: "for(var=i)" / "while(...)" etc.


# ---------- Helpers de chequeo ----------
_REL_OPS: Set[str] = {"==", "!=", "<", "<=", ">", ">="}
_BOOL_BIN: Set[str] = {"and", "or"}


def _looks_boolean(e: Expr) -> bool:
    if isinstance(e, Bool):
        return True
    if isinstance(e, UnOp):
        return e.op == "not" and _looks_boolean(e.expr)
    if isinstance(e, BinOp):
        if e.op in _REL_OPS:  # comparaciones
            return True
        if e.op in _BOOL_BIN:  # and/or
            # Conservador: al menos uno “parece booleano”
            return _looks_boolean(e.left) or _looks_boolean(e.right)
    return False


def _normalize_for_step(s: For, issues: List[Issue]) -> For:
    step = s.step if s.step is not None else Num(value=1)
    if isinstance(step, Num) and step.value == 0:
        issues.append(Issue(severity="error", msg="El paso del for no puede ser 0", where=f"for(var={s.var})"))
    return For(var=s.var, start=s.start, end=s.end, step=step, inclusive=True,
               body=[_visit_stmt(b, issues) for b in s.body])


# ---------- Visitadores ----------
def _visit_stmt(s: Stmt, issues: List[Issue]) -> Stmt:
    if isinstance(s, For):
        return _normalize_for_step(s, issues)

    if isinstance(s, While):
        if not _looks_boolean(s.cond):
            issues.append(Issue(severity="warning",
                                msg="La condición del while no parece booleana (usa comparaciones o and/or/not)",
                                where="while"))
        return While(cond=s.cond, body=[_visit_stmt(b, issues) for b in s.body])

    if isinstance(s, If):
        if not _looks_boolean(s.cond):
            issues.append(Issue(severity="warning", msg="La condición del if no parece booleana", where="if"))
        then_b = [_visit_stmt(b, issues) for b in s.then_body]
        else_b = [_visit_stmt(b, issues) for b in s.else_body] if s.else_body else None
        return If(cond=s.cond, then_body=then_b, else_body=else_b)

    if isinstance(s, Repeat):
        if not _looks_boolean(s.until):
            issues.append(
                Issue(severity="warning", msg="La condición del until no parece booleana", where="repeat-until"))
        return Repeat(body=[_visit_stmt(b, issues) for b in s.body], until=s.until)

    if isinstance(s, Block):
        return Block(stmts=[_visit_stmt(b, issues) for b in s.stmts])

    # Assign / Call se devuelven igual (no hay normalización aún)
    return s


# ---------- API principal ----------
def run_semantic(ast: Program) -> tuple[Program, List[Issue]]:
    """
    Normaliza (p.ej., step por defecto en for) y realiza chequeos simples.
    Devuelve (ast_normalizado, issues).
    """
    issues: List[Issue] = []
    norm_body = [_visit_stmt(s, issues) for s in ast.body]
    return Program(body=norm_body), issues
