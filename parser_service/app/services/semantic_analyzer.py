"""Análisis semántico del AST.

Responsabilidad: normalización y validación semántica.
"""

from typing import List, Set, Tuple
from pydantic import BaseModel

from ..domain.ast_models import (
    Program, Stmt, Block, Assign, Call, If, For, While, Repeat,
    Expr, Num, Bool, UnOp, BinOp
)


class Issue(BaseModel):
    """Advertencia o error semántico.
    
    Attributes:
        severity: Nivel de severidad (error, warning)
        msg: Mensaje descriptivo
        where: Ubicación opcional del problema
    """
    severity: str
    msg: str
    where: str | None = None


_REL_OPS: Set[str] = {"==", "!=", "<", "<=", ">", ">="}
_BOOL_BIN: Set[str] = {"and", "or"}


class SemanticValidator:
    """Validador semántico con métodos auxiliares."""

    @staticmethod
    def looks_boolean(e: Expr) -> bool:
        """Determina si una expresión parece booleana.
        
        Args:
            e: Expresión a evaluar
            
        Returns:
            True si la expresión parece ser booleana
        """
        if isinstance(e, Bool):
            return True
        if isinstance(e, UnOp):
            return e.op == "not" and SemanticValidator.looks_boolean(e.expr)
        if isinstance(e, BinOp):
            if e.op in _REL_OPS:
                return True
            if e.op in _BOOL_BIN:
                return (
                    SemanticValidator.looks_boolean(e.left) or
                    SemanticValidator.looks_boolean(e.right)
                )
        return False


class SemanticNormalizer:
    """Normalizador de estructuras del AST."""

    def __init__(self):
        self.validator = SemanticValidator()
        self.issues: List[Issue] = []

    def normalize_for_step(self, s: For) -> For:
        """Normaliza step del FOR."""
        step = s.step if s.step is not None else Num(value=1)

        if isinstance(step, Num) and step.value == 0:
            self.issues.append(Issue(
                severity="error",
                msg="El paso del for no puede ser 0",
                where=f"for(var={s.var})"
            ))

        return For(
            var=s.var,
            start=s.start,
            end=s.end,
            step=step,
            inclusive=True,
            body=[self.visit_stmt(b) for b in s.body]
        )

    def visit_stmt(self, s: Stmt) -> Stmt:
        """Visita y normaliza una sentencia."""
        if isinstance(s, For):
            return self.normalize_for_step(s)

        if isinstance(s, While):
            if not self.validator.looks_boolean(s.cond):
                self.issues.append(Issue(
                    severity="warning",
                    msg="La condición del while no parece booleana",
                    where="while"
                ))
            return While(
                cond=s.cond,
                body=[self.visit_stmt(b) for b in s.body]
            )

        if isinstance(s, If):
            if not self.validator.looks_boolean(s.cond):
                self.issues.append(Issue(
                    severity="warning",
                    msg="La condición del if no parece booleana",
                    where="if"
                ))
            then_b = [self.visit_stmt(b) for b in s.then_body]
            else_b = [self.visit_stmt(b) for b in s.else_body] if s.else_body else None
            return If(cond=s.cond, then_body=then_b, else_body=else_b)

        if isinstance(s, Repeat):
            if not self.validator.looks_boolean(s.until):
                self.issues.append(Issue(
                    severity="warning",
                    msg="La condición del until no parece booleana",
                    where="repeat-until"
                ))
            return Repeat(
                body=[self.visit_stmt(b) for b in s.body],
                until=s.until
            )

        if isinstance(s, Block):
            return Block(stmts=[self.visit_stmt(b) for b in s.stmts])

        return s


# ---------------------------------------------------------------------------
# API PÚBLICA
# ---------------------------------------------------------------------------

def run_semantic(ast: Program) -> Tuple[Program, List[Issue]]:
    """
    Ejecuta análisis semántico sobre un programa.

    Args:
        ast: Programa a analizar

    Returns:
        (AST normalizado, lista de issues)
    """
    normalizer = SemanticNormalizer()
    norm_body = [normalizer.visit_stmt(s) for s in ast.body]
    return Program(body=norm_body), normalizer.issues