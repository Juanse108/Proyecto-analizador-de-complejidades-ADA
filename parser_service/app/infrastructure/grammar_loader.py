"""
grammar_loader.py — Gestión de carga de gramática Lark
======================================================

Responsabilidad única: cargar y cachear la gramática desde el archivo.
"""

from pathlib import Path
from functools import lru_cache


class GrammarLoader:
    """Cargador de gramática Lark con cache."""

    _grammar_path = Path(__file__).parents[1] / "grammar" / "pseudocode.lark"

    @classmethod
    @lru_cache(maxsize=1)
    def load(cls) -> str:
        """
        Carga la gramática desde el archivo .lark

        Returns:
            str: Contenido de la gramática

        Raises:
            FileNotFoundError: Si no se encuentra el archivo
        """
        if not cls._grammar_path.exists():
            raise FileNotFoundError(
                f"Archivo de gramática no encontrado: {cls._grammar_path}"
            )

        with open(cls._grammar_path, "r", encoding="utf-8") as f:
            return f.read()

    @classmethod
    def get_path(cls) -> Path:
        """Retorna la ruta del archivo de gramática."""
        return cls._grammar_path