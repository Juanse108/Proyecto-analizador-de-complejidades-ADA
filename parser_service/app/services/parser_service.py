"""
parser_service.py — Servicio principal de parsing
=================================================

Responsabilidad: orquestar el flujo completo de parsing.
"""

from ..domain.ast_models import Program
from ..infrastructure.lark_parser import get_parser
from .ast_builder import build_ast_from_tree


class ParserService:
    """
    Servicio de parsing que orquesta todo el flujo.

    Flujo:
    1. Parser LALR (Lark) → parse tree
    2. Transformer BuildAST → AST dominio
    3. (Opcional) Semantic analysis
    """

    def __init__(self):
        self.parser = get_parser()

    def parse(self, code: str) -> Program:
        """
        Parsea pseudocódigo a AST.

        Args:
            code: Pseudocódigo a parsear

        Returns:
            Program: AST del dominio

        Raises:
            ValueError: Si hay errores de sintaxis
        """
        try:
            # Paso 1: Parsear a parse tree
            tree = self.parser.parse(code)

            # Paso 2: Construir AST del dominio
            ast = build_ast_from_tree(tree)

            return ast

        except Exception as e:
            raise ValueError(f"Error de análisis sintáctico: {e}") from e


# Instancia singleton para uso en routes
_parser_service = None


def get_parser_service() -> ParserService:
    """Factory para obtener instancia singleton del servicio."""
    global _parser_service
    if _parser_service is None:
        _parser_service = ParserService()
    return _parser_service