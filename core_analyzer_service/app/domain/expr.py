from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple, List, Dict
import math


class Expr:
    pass


@dataclass(frozen=True)
class Const(Expr):
    k: int


@dataclass(frozen=True)
class Sym(Expr):
    name: str


@dataclass(frozen=True)
class Pow(Expr):
    base: Sym
    exp: int


@dataclass(frozen=True)
class Log(Expr):
    arg: Sym
    base: int = 2


@dataclass(frozen=True)
class Add(Expr):
    terms: Tuple[Expr, ...]


@dataclass(frozen=True)
class Mul(Expr):
    factors: Tuple[Expr, ...]


@dataclass(frozen=True)
class Alt(Expr):
    options: Tuple[Expr, ...]


def const(k: int) -> Expr:
    return Const(int(k))


def sym(name: str = "n") -> Expr:
    return Sym(name)


def log(arg: Expr, base: Expr | int = 2) -> Expr:
    b: int
    if isinstance(base, Const):
        b = int(base.k)
    elif isinstance(base, int):
        b = int(base)
    else:
        b = 2
    if isinstance(arg, Sym):
        return Log(arg, b)
    return mul(Sym("log"), arg)


def add(*xs: Expr) -> Expr:
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
    cprod = 1
    syms_exp: Dict[str, int] = {}
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

    out: List[Expr] = []

    if cprod != 1:
        out.append(Const(cprod))

    def _sym_order(name: str):
        if name == "n":
            return (0, name)
        return (1, name)

    for name in sorted(syms_exp.keys(), key=_sym_order):
        e = syms_exp[name]
        if e == 1:
            out.append(Sym(name))
        elif e > 1:
            out.append(Pow(Sym(name), e))

    out.extend(logs)

    for f in others:
        if isinstance(f, Const) and f.k == 1:
            continue
        out.append(f)

    if not out:
        return Const(1)
    if len(out) == 1:
        return out[0]
    return Mul(tuple(out))


def alt(*xs: Expr) -> Expr:
    opts: List[Expr] = []
    for x in xs:
        if isinstance(x, Alt):
            opts.extend(x.options)
        else:
            opts.append(x)
    if not opts:
        return Const(1)
    if len(opts) == 1:
        return opts[0]
    return Alt(tuple(opts))


def degree(e: Expr) -> Tuple[int, int]:
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
        return max((degree(t) for t in e.terms), key=lambda dl: dl)
    if isinstance(e, Alt):
        if not e.options:
            return (0, 0)
        return max((degree(o) for o in e.options), key=lambda dl: dl)
    return (0, 0)


LOCAL_INDEX_VARS = {"i", "j", "k", "p", "q", "l", "h", "t"}


def canonicalize_for_big_o(e: Expr) -> Expr:
    if isinstance(e, Sym):
        if e.name in LOCAL_INDEX_VARS:
            return Sym("n")
        return e

    if isinstance(e, Pow):
        base = canonicalize_for_big_o(e.base)
        if isinstance(base, Sym):
            return Pow(base, e.exp)
        return base

    if isinstance(e, Log):
        return Log(canonicalize_for_big_o(e.arg))

    if isinstance(e, Mul):
        return mul(*(canonicalize_for_big_o(f) for f in e.factors))

    if isinstance(e, Add):
        return add(*(canonicalize_for_big_o(t) for t in e.terms))

    if isinstance(e, Alt):
        return alt(*(canonicalize_for_big_o(o) for o in e.options))

    return e


def big_o_expr(e: Expr) -> Expr:
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
        cleaned = [big_o_expr(o) for o in e.options]
        best = max(cleaned, key=degree) if cleaned else Const(1)
        return best

    return e


def big_o_str(e: Expr) -> str:
    e = big_o_expr(e)

    if isinstance(e, Const):
        return "1"

    if isinstance(e, Sym):
        return e.name

    if isinstance(e, Pow) and isinstance(e.base, Sym):
        return f"{e.base.name}^{e.exp}"

    if isinstance(e, Log):
        arg = e.arg.name if isinstance(e.arg, Sym) else "n"
        return f"log {arg}"

    if isinstance(e, Mul):
        parts = [big_o_str(f) for f in e.factors if not (isinstance(f, Const) and f.k == 1)]
        parts = [p for p in parts if p != "1"]
        return " ".join(parts) if parts else "1"

    if isinstance(e, Add):
        parts = sorted({big_o_str(t) for t in e.terms})
        return " + ".join(parts) if parts else "1"

    return "1"


def to_json(e: Expr):
    if isinstance(e, Const):
        return {"k": e.k}
    if isinstance(e, Sym):
        return {"name": e.name}
    if isinstance(e, Pow):
        if isinstance(e.base, Sym):
            return {"pow": {"name": e.base.name, "exp": e.exp}}
        else:
            return {"pow": {"base": to_json(e.base), "exp": e.exp}}
    if isinstance(e, Log):
        return {"log": {"arg": to_json(e.arg), "base": e.base}}
    if isinstance(e, Add):
        return {"terms": [to_json(t) for t in e.terms]}
    if isinstance(e, Mul):
        return {"factors": [to_json(f) for f in e.factors]}
    if isinstance(e, Alt):
        return {"alt": [to_json(o) for o in e.options]}
    return str(e)


def get_dominant_term(e: Expr, dominant_func=max) -> Expr:
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
    e = canonicalize_for_big_o(e)
    dominant_term = get_dominant_term(e, dominant_func=max)
    return big_o_str(dominant_term)


def big_omega_str_from_expr(e: Expr) -> str:
    e = canonicalize_for_big_o(e)

    if isinstance(e, Alt):
        cleaned = [big_o_expr(o) for o in e.options]
        pick = min(cleaned, key=degree) if cleaned else Const(1)
        return big_o_str(pick)

    dominant_term = get_dominant_term(e, dominant_func=max)
    return big_o_str(dominant_term)


def to_explicit_formula(e: Expr) -> str:
    e = canonicalize_for_big_o(e)

    if isinstance(e, Const):
        return str(e.k)

    if isinstance(e, Sym):
        return e.name

    if isinstance(e, Pow):
        base = e.base.name if isinstance(e.base, Sym) else str(e.base)
        if e.exp == 2:
            return f"{base}²"
        elif e.exp == 3:
            return f"{base}³"
        else:
            return f"{base}^{e.exp}"

    if isinstance(e, Log):
        arg = e.arg.name if isinstance(e.arg, Sym) else str(e.arg)
        if e.base == 2:
            return f"log {arg}"
        else:
            return f"log_{e.base} {arg}"

    if isinstance(e, Mul):
        coef = 1
        terms = []

        for f in e.factors:
            if isinstance(f, Const):
                coef *= f.k
            else:
                terms.append(to_explicit_formula(f))

        if coef == 1 and terms:
            return "".join(terms)
        elif coef == 0:
            return "0"
        elif not terms:
            return str(coef)
        else:
            term_str = "".join(terms)
            return f"{coef}{term_str}"

    if isinstance(e, Add):
        sorted_terms = sorted(e.terms, key=lambda t: degree(t), reverse=True)

        parts = []
        for i, t in enumerate(sorted_terms):
            term_str = to_explicit_formula(t)

            if i == 0:
                parts.append(term_str)
            else:
                if term_str.startswith("-"):
                    parts.append(f" {term_str}")
                else:
                    parts.append(f" + {term_str}")

        return "".join(parts)

    if isinstance(e, Alt):
        options = [to_explicit_formula(o) for o in e.options]
        return f"max({', '.join(options)})"

    return str(e)


def to_explicit_formula_verbose(e: Expr) -> dict:
    e = canonicalize_for_big_o(e)

    result = {
        "formula": to_explicit_formula(e),
        "terms": [],
        "dominant": None,
        "constant": 0,
    }

    if isinstance(e, Add):
        for t in e.terms:
            if isinstance(t, Const):
                result["constant"] = t.k
            else:
                result["terms"].append({
                    "expr": to_explicit_formula(t),
                    "degree": degree(t),
                })

        result["terms"].sort(key=lambda x: x["degree"], reverse=True)

        if result["terms"]:
            result["dominant"] = result["terms"][0]["expr"]

    elif isinstance(e, Const):
        result["constant"] = e.k

    else:
        result["terms"].append({
            "expr": to_explicit_formula(e),
            "degree": degree(e),
        })
        result["dominant"] = result["terms"][0]["expr"]

    return result