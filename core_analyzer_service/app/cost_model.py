# core_analyzer_service/app/cost_model.py
from .complexity_ir import Const, const, add

# Puedes expandir esto luego con modelos configurables
def cost_assign():
    return const(1)

def cost_compare():
    return const(1)

def cost_seq(*costs):
    return add(*costs)


