# core_analyzer_service/app/domain/source_mapper.py
"""
source_mapper.py - Mapeo entre líneas del AST y código fuente
=============================================================

Permite asociar cada línea del análisis con su texto real del pseudocódigo.
"""

from typing import List, Dict, Optional, Any


class SourceMapper:
    """
    Mapea líneas del AST a su texto original del pseudocódigo.
    
    Uso:
        mapper = SourceMapper(pseudocode_text)
        text = mapper.get_line_text(5)  # "for j <- 1 to n - i do"
    """
    
    def __init__(self, source_code: str):
        """
        Inicializa el mapper con el pseudocódigo fuente.
        
        Args:
            source_code: Pseudocódigo completo como string
        """
        self.lines: List[str] = source_code.splitlines()
        self._line_cache: Dict[int, str] = {}
    
    def get_line_text(self, line_number: Optional[int]) -> Optional[str]:
        """
        Obtiene el texto de una línea específica.
        
        Args:
            line_number: Número de línea (1-indexed)
            
        Returns:
            Texto de la línea o None si no existe
        """
        if line_number is None:
            return None

        if line_number in self._line_cache:
            return self._line_cache[line_number]
        
        # Convertir a 0-indexed
        idx = line_number - 1
        
        if 0 <= idx < len(self.lines):
            text = self.lines[idx].strip()
            self._line_cache[line_number] = text
            return text
        
        return None
    
    def get_line_range(self, start: int, end: int) -> List[str]:
        """
        Obtiene múltiples líneas de código.
        
        Args:
            start: Línea inicial (1-indexed)
            end: Línea final (1-indexed, inclusive)
            
        Returns:
            Lista de textos de líneas
        """
        return [
            self.get_line_text(line_num)
            for line_num in range(start, end + 1)
            if self.get_line_text(line_num) is not None
        ]

    def annotate_line_costs(self, lines: List[Any]) -> List[Dict]:
        """
        Añade el campo 'text' a cada entrada de análisis línea por línea.

        Soporta tanto diccionarios como objetos Pydantic (LineCost).
        Devuelve siempre una lista de diccionarios.
        """
        annotated: List[Dict] = []

        for line_data in lines:
            # 1) Normalizar a diccionario + obtener número de línea
            if isinstance(line_data, dict):
                line_num = line_data.get("line")
                line_dict = dict(line_data)
            else:
                # Pydantic u otro objeto con atributo 'line'
                line_num = getattr(line_data, "line", None)
                # Si tiene model_dump() (Pydantic v2)
                if hasattr(line_data, "model_dump"):
                    line_dict = line_data.model_dump()
                # Si usa .dict() (Pydantic v1)
                elif hasattr(line_data, "dict"):
                    line_dict = line_data.dict()
                else:
                    # Fallback mínimo
                    line_dict = {"line": line_num}

            # 2) Añadir texto si hay número de línea válido
            if isinstance(line_num, int) and line_num > 0:
                text = self.get_line_text(line_num)
                line_dict["text"] = text

            annotated.append(line_dict)

        return annotated


def create_source_mapper(pseudocode: Optional[str]) -> Optional[SourceMapper]:
    """
    Factory function para crear un SourceMapper.
    
    Args:
        pseudocode: Código fuente del algoritmo (o None)
        
    Returns:
        Instancia configurada de SourceMapper o None si no hay pseudocódigo
    """
    if not pseudocode:
        return None
    return SourceMapper(pseudocode)
