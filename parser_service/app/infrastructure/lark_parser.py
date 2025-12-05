"""Configuración y gestión del parser LALR.

Responsabilidad: configurar Lark y parsear texto a parse tree.
"""

from lark import Lark
from lark.exceptions import LarkError
from functools import lru_cache

from .grammar_loader import GrammarLoader


class LarkParserConfig:
    """Configuración del parser LALR."""

    START = "start"
    PARSER = "lalr"
    LEXER = "contextual"
    PROPAGATE_POSITIONS = True


class PseudocodeParser:
    """Parser de pseudocódigo basado en Lark.
    
    Singleton pattern para evitar recargar la gramática.
    """

    _instance = None
    _parser = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize_parser()
        return cls._instance

    def _initialize_parser(self) -> None:
        """Inicializa el parser Lark con la gramática cargada."""
        grammar = GrammarLoader.load()

        self._parser = Lark(
            grammar,
            start=LarkParserConfig.START,
            parser=LarkParserConfig.PARSER,
            lexer=LarkParserConfig.LEXER,
            propagate_positions=LarkParserConfig.PROPAGATE_POSITIONS,
        )

    def parse(self, code: str):
        """Parsea pseudocódigo a parse tree.
        
        Args:
            code: Pseudocódigo a parsear
        
        Returns:
            Lark Tree
        
        Raises:
            LarkError: Si hay errores de sintaxis
        """
        try:
            return self._parser.parse(code)
        except LarkError as e:
            raise ValueError(f"Error de sintaxis: {e}") from e


@lru_cache(maxsize=1)
def get_parser() -> PseudocodeParser:
    """Factory function para obtener instancia singleton del parser."""
    return PseudocodeParser()