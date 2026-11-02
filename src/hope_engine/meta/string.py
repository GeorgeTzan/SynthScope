"""String meta domain (paper §4.6.3, Figs 5-6, adapted).

An element has four Meta flags: prefix, suffix, length lower bound, length upper bound. MUST_TOP means
the underlying component is the top value (prefix/suffix empty, lower bound 0, upper bound infinite);
MAY_NOT_TOP means it may be non-trivial. This replaces the paper's {Con, Bnd, Unb} length chain with the
same information kept as two flags, because our underlying domain has a single length interval.

Rules not refined below fall back to MAY in every component, which is always sound.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from hope_engine.meta.lattice import Meta

BOT, MUST, MAY = Meta.BOT, Meta.MUST_TOP, Meta.MAY_NOT_TOP
_REFINED_BACKWARD = {"str.++", "ConCat", "str.at", "CharAt0", "str.len", "+", "-", "=", "ite"}


@dataclass(frozen=True)
class SM:
    pc: Meta  # prefix
    sc: Meta  # suffix
    lo: Meta  # length lower bound
    hi: Meta  # length upper bound


_BOTTOM = SM(BOT, BOT, BOT, BOT)
_MUST = SM(MUST, MUST, MUST, MUST)
_MAY = SM(MAY, MAY, MAY, MAY)


def _may_be_exact(a: SM) -> bool:
    return a.lo == MAY and a.hi == MAY


def _norm(a: SM) -> SM:
    """An exact-length string merges its prefix and suffix information."""
    if _may_be_exact(a):
        j = max(a.pc, a.sc)
        return SM(j, j, a.lo, a.hi)
    return a


def _concat2(a: SM, b: SM) -> SM:
    pc = max(a.pc, b.pc) if _may_be_exact(a) else a.pc
    sc = max(a.sc, b.sc) if _may_be_exact(b) else b.sc
    lo = max(a.lo, b.lo)
    hi = MUST if MUST in (a.hi, b.hi) else max(a.hi, b.hi)
    return _norm(SM(pc, sc, lo, hi))


class StringMeta:
    def bottom(self) -> SM:
        return _BOTTOM

    def must(self) -> SM:
        return _MUST

    def may(self) -> SM:
        return _MAY

    def const(self) -> SM:
        return _MAY

    def join(self, a: SM, b: SM) -> SM:
        return SM(max(a.pc, b.pc), max(a.sc, b.sc), max(a.lo, b.lo), max(a.hi, b.hi))

    def is_may(self, a: SM) -> bool:
        return MAY in (a.pc, a.sc, a.lo, a.hi)

    def is_must(self, a: SM) -> bool:
        return a == _MUST

    def forward(self, op: str, args: Sequence[SM]) -> SM:
        if any(a == _BOTTOM for a in args):
            return _BOTTOM
        if op in ("str.++", "ConCat"):
            acc = args[0]
            for nxt in args[1:]:
                acc = _concat2(acc, nxt)
            return acc
        if op in ("str.len", "str.indexof", "str.to.int"):
            # int results are bounded below (lengths >= 0, indexes >= -1); the upper bound follows the string
            return SM(MUST, MUST, MAY, args[0].hi)
        return _MAY

    def backward(self, op: str, result: SM, args: Sequence[SM], i: int) -> SM:
        if op in _REFINED_BACKWARD:
            return _MAY if self.is_may(result) else _MUST
        return _MUST
