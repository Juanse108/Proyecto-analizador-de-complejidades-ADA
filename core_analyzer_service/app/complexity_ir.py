# core_analyzer_service/app/complexity_ir.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple, Union, List, Dict


# -------- IR de complejidad (ligero y multi-símbolo) --------

class Expr:
    pass


@dataclass(frozen=True)
class Const(Expr):
    k: int


@dataclass(frozen=True)
class Sym(Expr):
    name: str  # p.ej., "n", "m", "k"


@dataclass(frozen=True)
class Pow(Expr):
    base: Sym
    exp: int


@dataclass(frozen=True)
class Log(Expr):
    arg: Sym  # log(arg)
    base: int = 2  # base (no cambia la clase O/Ω/Θ)


@dataclass(frozen=True)
class Add(Expr):
    terms: Tuple[Expr, ...]


@dataclass(frozen=True)
class Mul(Expr):
    factors: Tuple[Expr, ...]


@dataclass(frozen=True)
class Alt(Expr):
    options: Tuple[Expr, ...]


# -------- Constructores --------

def const(k: int) -> Expr:
    return Const(int(k))


def sym(name: str = "n") -> Expr:
    return Sym(name)


def log(arg: Expr, base: Expr | int = 2) -> Expr:
    """
    Helper para construir Log compatible con analyzer._make_log.
    Requiere arg como Sym y base entero (o Const entero).
    """
    b: int
    if isinstance(base, Const):
        b = int(base.k)
    elif isinstance(base, int):
        b = int(base)
    else:
        # degradación conservadora: si la base no es entera, fija 2
        b = 2
    if isinstance(arg, Sym):
        return Log(arg, b)
    # Si no es símbolo, degradamos a "log(arg)" como multiplicación simbólica
    # para no romper flujo (muy raro en tu pipeline).
    return mul(Sym("log"), arg)


def add(*xs: Expr) -> Expr:
    """Aplana sumas, elimina 0 y suma constantes."""
    terms: List[Expr] = []
    csum = 0
    for x in xs:
        if isinstance(x, Add):
            terms.extend(x.terms)
        else:
            terms.append(x)
    keep: List[Expr] = []
    for t in terms:
        if isinstance(t, Const):
            csum += t.k
        else:
            keep.append(t)
    if csum != 0:
        keep.append(Const(csum))
    if not keep:
        return Const(0)
    if len(keep) == 1:
        return keep[0]
    return Add(tuple(keep))


def mul(*xs: Expr) -> Expr:
    """
    Aplana productos, combina constantes y acumula potencias por símbolo.
    Soporta múltiples símbolos: n^a * m^b * (logs) * ...
    """
    cprod = 1
    syms_exp: Dict[str, int] = {}  # acumulador de exponentes por símbolo
    logs: List[Log] = []
    others: List[Expr] = []

    def _add_sym_power(name: str, exp: int = 1):
        if exp == 0:
            return
        syms_exp[name] = syms_exp.get(name, 0) + exp

    for x in xs:
        if isinstance(x, Const):
            if x.k == 0:
                return Const(0)
            cprod *= x.k
        elif isinstance(x, Mul):
            # aplanar
            for f in x.factors:
                others.append(f)
        elif isinstance(x, Pow) and isinstance(x.base, Sym):
            _add_sym_power(x.base.name, x.exp)
        elif isinstance(x, Sym):
            _add_sym_power(x.name, 1)
        elif isinstance(x, Log):
            logs.append(x)
        else:
            others.append(x)

    # reconstrucción ordenada: const · símbolos · logs · otros
    out: List[Expr] = []

    if cprod != 1:
        out.append(Const(cprod))

    # símbolos: orden alfabético para determinismo
    for name in sorted(syms_exp.keys()):
        e = syms_exp[name]
        if e == 1:
            out.append(Sym(name))
        elif e > 1:
            out.append(Pow(Sym(name), e))
        # (si e<0, en este IR no contemplamos fracciones; no debería ocurrir)

    # logs se mantienen (no combinamos bases; para O/Ω la base no importa)
    out.extend(logs)

    # otros factores (descarta Const(1) residuales)
    for f in others:
        if isinstance(f, Const) and f.k == 1:
            continue
        out.append(f)

    if not out:
        return Const(1)
    if len(out) == 1:
        return out[0]
    return Mul(tuple(out))


# ===== AÑADE ESTE CONSTRUCTOR =====
def alt(*xs: Expr) -> Expr:
    """Alternativas: O = max(opciones), Ω = min(opciones)."""
    opts: List[Expr] = []
    for x in xs:
        if isinstance(x, Alt):
            opts.extend(x.options)  # aplanar
        else:
            opts.append(x)
    if not opts:
        return Const(1)
    if len(opts) == 1:
        return opts[0]
    return Alt(tuple(opts))


# -------- Métrica de “grado” para comparación asintótica --------

def degree(e: Expr) -> Tuple[int, int]:
    """
    Retorna (grado_polinomial_total, grado_logaritmico_total).
    - Cualquier Sym cuenta como 1 en el grado polinomial.
    - Pow(base=Sym, exp=k) suma k al grado polinomial.
    - Log contribuye 1 al grado logarítmico.
    - Mul suma grados; Add toma el máximo (término dominante).
    """
    if isinstance(e, Const):
        return (0, 0)
    if isinstance(e, Sym):
        return (1, 0)
    if isinstance(e, Pow) and isinstance(e.base, Sym):
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
        if not e.terms:
            return (0, 0)
        return max((degree(t) for t in e.terms), default=(0, 0))
    # por defecto conservador
    return (0, 0)


# -------- Big-O sobre el IR --------

def big_o_expr(e: Expr) -> Expr:
    """
    Para Add: toma el término dominante por (poly_deg, log_deg).
    Para Mul: producto de big-O de factores, quitando constantes.
    """
    if isinstance(e, Add):
        best = None
        best_deg = (-10 ** 9, -10 ** 9)
        for t in e.terms:
            dt = degree(t)
            if dt > best_deg:
                best, best_deg = t, dt
        return big_o_expr(best) if best is not None else Const(1)

    if isinstance(e, Mul):
        cleaned = [big_o_expr(f) for f in e.factors if not isinstance(f, Const)]
        if not cleaned:
            return Const(1)
        return mul(*cleaned)
    if isinstance(e, Alt):
        # O(Alt) = max O(opciones)
        cleaned = [big_o_expr(o) for o in e.options]
        best = max(cleaned, key=degree) if cleaned else Const(1)
        return best
    return e


def big_o_str(e: Expr) -> str:
    """String amigable para Big-O de un término ya simplificado."""
    e = big_o_expr(e)

    if isinstance(e, Const):
        return "1"

    if isinstance(e, Sym):
        return e.name  # soporta n, m, k, ...

    if isinstance(e, Pow) and isinstance(e.base, Sym):
        return f"{e.base.name}^{e.exp}"

    if isinstance(e, Log):
        # Mostrar el argumento (n, m, ...)
        arg = e.arg.name if isinstance(e.arg, Sym) else "n"
        return f"log {arg}"

    if isinstance(e, Mul):
        parts = [big_o_str(f) for f in e.factors if not (isinstance(f, Const) and f.k == 1)]
        # Evitar "1" en productos: filtra aquí también
        parts = [p for p in parts if p != "1"]
        return " ".join(parts) if parts else "1"

    if isinstance(e, Add):
        # Normalmente no llega aquí (big_o_expr colapsa), por seguridad:
        parts = sorted({big_o_str(t) for t in e.terms})
        return " + ".join(parts) if parts else "1"

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
    if isinstance(e, Alt):
        return {"alt": [to_json(o) for o in e.options]}
    # fallback
    return str(e)


# ----- Utilidades para extraer término dominante -----

def get_dominant_term(e: Expr, dominant_func=max) -> Expr:
    """
    Extrae el término dominante de una suma usando una función de comparación:
    - max para Big-O (peor caso)
    - min para Big-Omega (mejor caso)
    Se compara por (grado_polinomial_total, grado_logaritmico_total).
    """
    if isinstance(e, Add):
        terms = e.terms
        if not terms:
            return Const(1)
        dominant_term = dominant_func(
            terms,
            key=lambda t: degree(t) if not (isinstance(t, Const) and t.k <= 0) else (-float("inf"), -float("inf"))
        )
        return dominant_term
    return e


def big_o_str_from_expr(e: Expr) -> str:
    """Devuelve la cadena Big-O (peor caso) para una expresión arbitraria."""
    dominant_term = get_dominant_term(e, dominant_func=max)
    return big_o_str(dominant_term)


# --- reemplaza por completo esta función ---

def big_omega_str_from_expr(e: Expr) -> str:
    """Devuelve la cadena de Big-Ω (mejor caso) para una expresión."""
    # Ω(Alt) = min Ω(opciones); para secuencias (Add) sigue dominando el mayor término.
    if isinstance(e, Alt):
        # Reutilizamos big_o_expr para normalizar cada opción (Add→término dominante)
        cleaned = [big_o_expr(o) for o in e.options]
        pick = min(cleaned, key=degree) if cleaned else Const(1)
        return big_o_str(pick)

    dominant_term = get_dominant_term(e, dominant_func=max)  # secuencia ⇒ max
    return big_o_str(dominant_term)