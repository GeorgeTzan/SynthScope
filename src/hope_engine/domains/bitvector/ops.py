"""Forward/backward abstract operators for fixed-width bitvectors.

Written from the Simba text plus standard known-bits and interval arithmetic (the Simba and HOPE
supplements with the full operator tables are not public); every operator is checked for
soundness by exhaustive tests. See research/known_deviations.md.
"""

from __future__ import annotations

import itertools
from collections.abc import Sequence

from hope_engine.concrete.bitvector import BINARY, BOOL_OPS, UNARY, UnsupportedOperator
from hope_engine.domains.bitvector.lattice import (
    BV,
    alpha,
    bottom,
    join,
    leq,
    meet,
    reduce_,
    top,
)

Tn = tuple[int, int]  # (value, mask): mask bits are unknown, value bits are known


def _tn(a: BV) -> Tn:
    return a.k1, ((1 << a.w) - 1) & ~(a.k0 | a.k1)


def _t_add(m: int, a: Tn, b: Tn) -> Tn:
    sv = (a[0] + b[0]) & m
    sm = (a[1] + b[1]) & m
    mu = (((sm + sv) & m) ^ sv) | a[1] | b[1]
    return sv & ~mu & m, mu


def _t_sub(m: int, a: Tn, b: Tn) -> Tn:
    dv = (a[0] - b[0]) & m
    mu = (((dv + a[1]) & m) ^ ((dv - b[1]) & m)) | a[1] | b[1]
    return dv & ~mu & m, mu


def _t_mul(m: int, a: Tn, b: Tn) -> Tn:
    acc_v = (a[0] * b[0]) & m
    acc_m: Tn = (0, 0)
    av, am, bv, bm = a[0], a[1], b[0], b[1]
    while av or am:
        if av & 1:
            acc_m = _t_add(m, acc_m, (0, bm))
        elif am & 1:
            acc_m = _t_add(m, acc_m, (0, bv | bm))
        av, am = av >> 1, am >> 1
        bv, bm = (bv << 1) & m, (bm << 1) & m
    return _t_add(m, (acc_v, 0), acc_m)


def _wrap(lo: int, hi: int, low: int, span: int) -> tuple[int, int]:
    """Map mathematical range [lo, hi] into the modular window [low, low+span-1], or the whole window."""
    k = (lo - low) // span
    if (hi - low) // span == k:
        return lo - k * span, hi - k * span
    return low, low + span - 1


def _mk(
    w: int,
    tn: Tn | None = None,
    u: tuple[int, int] | None = None,
    s: tuple[int, int] | None = None,
) -> BV:
    m, half = (1 << w) - 1, 1 << (w - 1)
    k1, k0 = (0, 0) if tn is None else (tn[0] & m, m & ~(tn[0] | tn[1]))
    ulo, uhi = u or (0, m)
    slo, shi = s or (-half, half - 1)
    return reduce_(w, k0, k1, ulo, uhi, slo, shi)


def _bits(w: int, k0: int, k1: int) -> Tn:
    return k1, ((1 << w) - 1) & ~(k0 | k1)


def _shift_const(op: str, a: BV, c: int) -> BV:
    w = a.w
    m, half = (1 << w) - 1, 1 << (w - 1)
    av, am = _tn(a)
    if op == "bvashr":
        c = min(c, w - 1)
        fill = ((1 << c) - 1) << (w - c)
        v, mk = av >> c, am >> c
        if av & half:
            v |= fill
        if am & half:
            mk |= fill
        return _mk(w, (v, mk), None, (a.slo >> c, a.shi >> c))
    if c >= w:
        return alpha(w, 0)
    if op == "bvshl":
        u = (a.ulo << c, a.uhi << c) if (a.uhi << c) <= m else None
        return _mk(w, ((av << c) & m, (am << c) & m), u)
    return _mk(w, (av >> c, am >> c), (a.ulo >> c, a.uhi >> c))


def _feasible_shifts(b: BV) -> list[int]:
    w = b.w
    shifts = [s for s in range(w) if b.contains(s)]
    if b.uhi >= w:
        shifts.append(w)
    return shifts


def _forward_shift(op: str, a: BV, b: BV) -> BV:
    out = bottom(a.w)
    for s in _feasible_shifts(b):
        out = join(out, _shift_const(op, a, s))
    return out


def _bool_values(a: BV) -> list[int]:
    return [v for v in (0, 1) if a.contains(v)]


def _bool_join(w: int, values: set[int]) -> BV:
    out = bottom(w)
    for v in values:
        out = join(out, alpha(w, v))
    return out


def _forward_bool(w: int, op: str, args: Sequence[BV]) -> BV:
    """Booleans are the values 0 and 1; enumerating the feasible ones is exact for and/or/not/ite."""
    if op == "=":
        if args[0].is_const and args[1].is_const:
            return alpha(w, int(args[0].k1 == args[1].k1))
        return _bool_join(w, {0, 1}) if not meet(args[0], args[1]).is_bottom else alpha(w, 0)
    if op == "ite":
        out = bottom(w)
        for c in _bool_values(args[0]):
            out = join(out, args[1] if c == 1 else args[2])
        return out
    fn = BOOL_OPS[op][1]
    return _bool_join(w, {fn(*vals) for vals in itertools.product(*(_bool_values(a) for a in args))})


def _backward_bool(w: int, op: str, res: BV, args: Sequence[BV], i: int) -> BV:
    """Necessary precondition for argument i of a Boolean operator."""
    if op == "=":
        return args[1 - i] if res.contains(1) and not res.contains(0) else top(w)
    if op == "ite":
        cond, then, other = args
        if i == 0:
            feasible: set[int] = set()
            if not meet(then, res).is_bottom:
                feasible.add(1)
            if not meet(other, res).is_bottom:
                feasible.add(0)
            return _bool_join(w, feasible & set(_bool_values(cond)))
        branch_taken, branch_other = (1, args[2]) if i == 1 else (0, args[1])
        if branch_taken not in _bool_values(cond):
            return top(w)  # this branch is never taken, so its value is irrelevant
        if (1 - branch_taken) in _bool_values(cond) and not meet(branch_other, res).is_bottom:
            return top(w)  # the other branch may produce the result, so this one is unconstrained
        return res
    fn = BOOL_OPS[op][1]
    feasible = set()
    others = [_bool_values(a) if j != i else [0, 1] for j, a in enumerate(args)]
    for vals in itertools.product(*others):
        if res.contains(fn(*vals)):
            feasible.add(vals[i])
    return _bool_join(w, feasible & set(_bool_values(args[i])))


def forward(w: int, op: str, args: Sequence[BV]) -> BV:
    if op in BOOL_OPS and len(args) == BOOL_OPS[op][0]:
        return bottom(w) if any(a.is_bottom for a in args) else _forward_bool(w, op, args)
    m, half, span = (1 << w) - 1, 1 << (w - 1), 1 << w
    if not ((op in UNARY and len(args) == 1) or (op in BINARY and len(args) == 2)):
        raise UnsupportedOperator(f"{op}/{len(args)}")
    if any(a.is_bottom for a in args):
        return bottom(w)
    if all(a.is_const for a in args):
        vals = [a.k1 for a in args]
        return alpha(w, UNARY[op](vals[0], w) if len(vals) == 1 else BINARY[op](vals[0], vals[1], w))
    a = args[0]
    if len(args) == 1:
        if op == "bvnot":
            return _mk(w, (a.k0, _tn(a)[1]), (m - a.uhi, m - a.ulo), (-a.shi - 1, -a.slo - 1))
        return _mk(  # bvneg
            w,
            _t_sub(m, (0, 0), _tn(a)),
            _wrap(-a.uhi, -a.ulo, 0, span),
            _wrap(-a.shi, -a.slo, -half, span),
        )
    b = args[1]
    ta, tb = _tn(a), _tn(b)
    if op == "bvand":
        return _mk(w, _bits(w, a.k0 | b.k0, a.k1 & b.k1), (0, min(a.uhi, b.uhi)))
    if op == "bvor":
        return _mk(w, _bits(w, a.k0 & b.k0, a.k1 | b.k1), (max(a.ulo, b.ulo), m))
    if op == "bvxor":
        k1 = (a.k1 & b.k0) | (a.k0 & b.k1)
        k0 = (a.k0 & b.k0) | (a.k1 & b.k1)
        return _mk(w, _bits(w, k0, k1))
    if op == "bvadd":
        return _mk(
            w,
            _t_add(m, ta, tb),
            _wrap(a.ulo + b.ulo, a.uhi + b.uhi, 0, span),
            _wrap(a.slo + b.slo, a.shi + b.shi, -half, span),
        )
    if op == "bvsub":
        return _mk(
            w,
            _t_sub(m, ta, tb),
            _wrap(a.ulo - b.uhi, a.uhi - b.ulo, 0, span),
            _wrap(a.slo - b.shi, a.shi - b.slo, -half, span),
        )
    if op == "bvmul":
        corners = [x * y for x in (a.slo, a.shi) for y in (b.slo, b.shi)]
        return _mk(
            w,
            _t_mul(m, ta, tb),
            _wrap(a.ulo * b.ulo, a.uhi * b.uhi, 0, span),
            _wrap(min(corners), max(corners), -half, span),
        )
    if op == "bvudiv":
        return _mk(w, None, (a.ulo // b.uhi, a.uhi // b.ulo) if b.ulo >= 1 else None)
    if op == "bvurem":
        hi = min(a.uhi, b.uhi - 1) if b.ulo >= 1 else a.uhi
        return _mk(w, None, (0, hi))
    if op in ("bvsdiv", "bvsrem"):
        return top(w)  # [ponytail: no refined signed division/remainder rule; top is sound]
    return _forward_shift(op, a, b)  # bvshl, bvlshr, bvashr


def _from_bits(w: int, k0: int, k1: int) -> BV:
    return reduce_(w, k0, k1, 0, (1 << w) - 1, -(1 << (w - 1)), (1 << (w - 1)) - 1)


def _backward_shift(op: str, res: BV, a_other_b: BV) -> BV:
    """Precondition for the shifted operand, joined over feasible shift amounts."""
    w = res.w
    m = (1 << w) - 1
    out = bottom(w)
    for s in _feasible_shifts(a_other_b):
        if s >= w:
            if res.contains(0):
                out = join(out, top(w))
            continue
        if op == "bvshl":
            if res.k1 & ((1 << s) - 1):
                continue
            low = (1 << (w - s)) - 1
            out = join(out, _from_bits(w, (res.k0 >> s) & low, (res.k1 >> s) & low))
        else:  # bvlshr
            if s > 0 and res.k1 >> (w - s):
                continue
            out = join(out, _from_bits(w, (res.k0 << s) & m, (res.k1 << s) & m))
    return out


def backward(w: int, op: str, res: BV, args: Sequence[BV], i: int) -> BV:
    half = 1 << (w - 1)
    if op in BOOL_OPS and len(args) == BOOL_OPS[op][0]:
        if res.is_bottom or any(a.is_bottom for a in args):
            return bottom(w)
        return _backward_bool(w, op, res, args, i)
    if not ((op in UNARY and len(args) == 1) or (op in BINARY and len(args) == 2)):
        raise UnsupportedOperator(f"{op}/{len(args)}")
    if res.is_bottom or any(a.is_bottom for a in args):
        return bottom(w)
    if len(args) == 1:
        return forward(w, op, [res])  # bvneg and bvnot are involutions
    other = args[1 - i]
    if op in ("bvadd", "bvxor"):
        return forward(w, "bvsub" if op == "bvadd" else "bvxor", [res, other])
    if op == "bvsub":
        return forward(w, "bvadd", [res, args[1]]) if i == 0 else forward(w, "bvsub", [args[0], res])
    if op == "bvand":
        return _from_bits(w, res.k0 & other.k1, res.k1)
    if op == "bvor":
        return _from_bits(w, res.k0, res.k1 & other.k0)
    if op == "bvmul":
        if other.is_const and other.k1 & 1:
            return forward(w, "bvmul", [res, alpha(w, pow(other.k1, -1, 1 << w))])
        if other.is_const and other.k1 == 0 and not res.contains(0):
            return bottom(w)
        return top(w)
    if op == "bvurem" and i == 0 and res.ulo >= half:
        return res
    if op in ("bvshl", "bvlshr") and i == 0:
        return _backward_shift(op, res, args[1])
    return top(w)


class BitvectorDomain:
    def __init__(self, width: int) -> None:
        self.w = width

    def top(self) -> BV:
        return top(self.w)

    def bottom(self) -> BV:
        return bottom(self.w)

    def alpha(self, value: int | str) -> BV:
        assert isinstance(value, int)
        return alpha(self.w, value)

    def is_bottom(self, a: BV) -> bool:
        return a.is_bottom

    def leq(self, a: BV, b: BV) -> bool:
        return leq(a, b)

    def join(self, a: BV, b: BV) -> BV:
        return join(a, b)

    def meet(self, a: BV, b: BV) -> BV:
        return meet(a, b)

    def forward(self, op: str, args: Sequence[BV]) -> BV:
        return forward(self.w, op, args)

    def backward(self, op: str, result: BV, args: Sequence[BV], i: int) -> BV:
        return backward(self.w, op, result, args, i)


