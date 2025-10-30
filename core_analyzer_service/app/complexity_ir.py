# core_analyzer_service/app/complexity_ir.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple, Union, List

# -------- IR de complejidad (muy simple) --------

class Expr:
    pass

@dataclass(frozen=True)
class Const(Expr):
    k: int

@dataclass(frozen=True)
class Sym(Expr):
    name: str  # usualmente "n"

@dataclass(frozen=True)
class Pow(Expr):
    base: Sym
    exp: int

@dataclass(frozen=True)
class Log(Expr):
    arg: Sym         # log(n)
    base: int = 2

@dataclass(frozen=True)
class Add(Expr):
    terms: Tuple[Expr, ...]

@dataclass(frozen=True)
class Mul(Expr):
    factors: Tuple[Expr, ...]

def const(k: int) -> Expr:
    return Const(int(k))

def sym(name: str = "n") -> Expr:
    return Sym(name)

def add(*xs: Expr) -> Expr:
    # aplanar, quitar 0s y sumar constantes
    terms: List[Expr] = []
    csum = 0
    for x in xs:
        if isinstance(x, Add):
            for t in x.terms:
                terms.append(t)
        else:
            terms.append(x)
    new_terms: List[Expr] = []
    for t in terms:
        if isinstance(t, Const):
            csum += t.k
        else:
            new_terms.append(t)
    if csum != 0:
        new_terms.append(Const(csum))
    if not new_terms:
        return Const(0)
    if len(new_terms) == 1:
        return new_terms[0]
    return Add(tuple(new_terms))

def mul(*xs: Expr) -> Expr:
    # aplanar, manejar 0s/1s, combinar potencias de n
    factors: List[Expr] = []
    cprod = 1
    n_exp = 0  # acumulamos potencias de n
    logs: List[Log] = []
    for x in xs:
        if isinstance(x, Const):
            if x.k == 0:
                return Const(0)
            cprod *= x.k
        elif isinstance(x, Mul):
            for f in x.factors:
                factors.append(f)
        elif isinstance(x, Pow) and isinstance(x.base, Sym) and x.base.name == "n":
            n_exp += x.exp
        elif isinstance(x, Sym) and x.name == "n":
            n_exp += 1
        elif isinstance(x, Log):
            logs.append(x)
        else:
            factors.append(x)
    # reconstruir
    out: List[Expr] = []
    if cprod != 1:
        out.append(Const(cprod))
    if n_exp == 1:
        out.append(Sym("n"))
    elif n_exp > 1:
        out.append(Pow(Sym("n"), n_exp))
    out.extend(logs)
    out.extend([f for f in factors if not (isinstance(f, Const) and f.k == 1)])
    if not out:
        return Const(1)
    if len(out) == 1:
        return out[0]
    return Mul(tuple(out))

def degree(e: Expr) -> Tuple[int, int]:  # (poly_deg, log_deg)
    if isinstance(e, Const):
        return (0, 0)
    if isinstance(e, Sym) and e.name == "n":
        return (1, 0)
    if isinstance(e, Pow) and isinstance(e.base, Sym) and e.base.name == "n":
        return (e.exp, 0)
    if isinstance(e, Log):
        return (0, 1)
    if isinstance(e, Mul):
        d_poly, d_log = 0, 0
        for f in e.factors:
            p, l = degree(f)
            d_poly += p
            d_log += l
        return (d_poly, d_log)
    if isinstance(e, Add):
        # mayor grado entre términos
        degs = [degree(t) for t in e.terms]
        return max(degs)
    # por defecto conservador
    return (0, 0)

def big_o_expr(e: Expr) -> Expr:
    # tomar el término dominante (para Add), pasar constantes
    if isinstance(e, Add):
        # escoge por (poly_deg, log_deg)
        best = None
        best_deg = (-10**9, -10**9)
        for t in e.terms:
            dt = degree(t)
            if dt > best_deg:
                best, best_deg = t, dt
        return big_o_expr(best) if best is not None else Const(1)
    if isinstance(e, Mul):
        # O(producto) = producto de O(factores) sin constantes
        cleaned = [big_o_expr(f) for f in e.factors if not (isinstance(f, Const))]
        if not cleaned:
            return Const(1)
        return mul(*cleaned)
    # resto: ya es "forma" de O
    return e

def big_o_str(e: Expr) -> str:
    e = big_o_expr(e)
    if isinstance(e, Const):
        return "1"
    if isinstance(e, Sym) and e.name == "n":
        return "n"
    if isinstance(e, Pow) and e.base.name == "n":
        return f"n^{e.exp}"
    if isinstance(e, Log):
        return "log n"
    if isinstance(e, Mul):
        parts = [big_o_str(f) for f in e.factors if not (isinstance(f, Const) and f.k == 1)]
        return " ".join(parts)
    if isinstance(e, Add):
        # debería venir simplificado por big_o_expr, pero por si acaso
        parts = sorted({big_o_str(t) for t in e.terms})
        return " + ".join(parts)
    return "1"
# ----- Serializador JSON para exponer el IR en la API -----

def to_json(e: Expr):
    if isinstance(e, Const):
        return {"k": e.k}
    if isinstance(e, Sym):
        return {"name": e.name}
    if isinstance(e, Pow):
        return {"pow": {"name": e.base.name, "exp": e.exp}}
    if isinstance(e, Log):
        return {"log": {"arg": to_json(e.arg), "base": e.base}}
    if isinstance(e, Add):
        return {"terms": [to_json(t) for t in e.terms]}
    if isinstance(e, Mul):
        return {"factors": [to_json(f) for f in e.factors]}
    # fallback
    return str(e)
