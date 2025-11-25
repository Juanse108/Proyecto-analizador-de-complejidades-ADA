# core_analyzer_service/app/cost_model.py
"""
Modelo de costos con constantes explícitas
===========================================

Define el costo real en operaciones elementales de cada instrucción.
Estas constantes son configurables y representan el número de operaciones
que ejecuta el hardware para cada sentencia.
"""

from .complexity_ir import Const, const, add

# ============================================================================
# MODELO DE COSTOS (operaciones elementales)
# ============================================================================

# Estos valores son configurables y representan el número de operaciones
# de bajo nivel que realiza cada instrucción en un procesador típico.

COST_MODEL = {
    # Operaciones básicas
    "assign": 1,  # Asignación simple: x <- 5
    "compare": 1,  # Comparación: x < y
    "add": 1,  # Suma/resta: x + y
    "mul": 2,  # Multiplicación: x * y
    "div": 3,  # División: x / y
    "mod": 3,  # Módulo: x mod y

    # Accesos a memoria
    "array_access": 2,  # Lectura/escritura: A[i]
    "deref": 1,  # Desreferencia de puntero

    # Control de flujo
    "jump": 1,  # Salto condicional (if/while)
    "call": 2,  # Llamada a función (overhead)
    "return": 1,  # Retorno de función
}


# ============================================================================
# FUNCIONES DE COSTO (retornan Expr con constantes)
# ============================================================================

def cost_assign():
    """Costo de una asignación simple: x <- valor"""
    return const(COST_MODEL["assign"])


def cost_compare():
    """Costo de una comparación: x < y"""
    return const(COST_MODEL["compare"])


def cost_array_access():
    """Costo de acceder a un elemento de arreglo: A[i]"""
    return const(COST_MODEL["array_access"])


def cost_arithmetic(op: str):
    """
    Costo de una operación aritmética.

    Args:
        op: Operador (+, -, *, /, mod, etc.)
    """
    if op in ("+", "-"):
        return const(COST_MODEL["add"])
    elif op in ("*"):
        return const(COST_MODEL["mul"])
    elif op in ("/", "div", "mod"):
        return const(COST_MODEL["div"])
    else:
        return const(1)  # Fallback genérico


def cost_seq(*costs):
    """
    Costo de una secuencia de operaciones (suma de costos).

    Args:
        *costs: Lista de expresiones de costo.

    Returns:
        Suma total de los costos.
    """
    return add(*costs)


# ============================================================================
# CONFIGURACIÓN DESDE VARIABLES DE ENTORNO (opcional)
# ============================================================================

def load_cost_model_from_env():
    """
    Permite configurar el modelo de costos desde variables de entorno.

    Ejemplo en .env:
        COST_ASSIGN=1
        COST_COMPARE=1
        COST_MUL=2
    """
    import os

    for key in COST_MODEL:
        env_key = f"COST_{key.upper()}"
        if env_key in os.environ:
            try:
                COST_MODEL[key] = int(os.environ[env_key])
            except ValueError:
                pass  # Ignorar valores inválidos


# Cargar configuración al importar el módulo
load_cost_model_from_env()