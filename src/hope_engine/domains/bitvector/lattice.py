"""Reduced product of bitwise, signed-interval and unsigned-interval domains (Simba §4.2).

Bitwise: k0 / k1 are masks of bits known to be 0 / known to be 1 (k0 & k1 != 0 means empty).
Unsigned interval [ulo, uhi] in [0, 2**w); signed interval [slo, shi] in [-2**(w-1), 2**(w-1)).
Bottom is canonical: ulo > uhi.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class BV:
    w: int
    k0: int
    k1: int
    ulo: int
    uhi: int
    slo: int
    shi: int

    @property
    def is_bottom(self) -> bool:
        return self.ulo > self.uhi

    @property
    def is_const(self) -> bool:
        return not self.is_bottom and (self.k0 | self.k1) == (1 << self.w) - 1

    def contains(self, v: int) -> bool:
        w = self.w
        if self.is_bottom or not 0 <= v < (1 << w):
            return False
        sv = v - (1 << w) if v >> (w - 1) else v
        return (
            v & self.k0 == 0
            and v & self.k1 == self.k1
            and self.ulo <= v <= self.uhi
            and self.slo <= sv <= self.shi
        )


def bottom(w: int) -> BV:
    return BV(w, 0, 0, 1, 0, 1, 0)


@lru_cache(maxsize=1 << 18)  # pure function of ints; the search repeats the same meets thousands of times
def reduce_(w: int, k0: int, k1: int, ulo: int, uhi: int, slo: int, shi: int) -> BV:
    """Iterated reduction rho: propagate information between the three domains to a fixpoint."""
    m = (1 << w) - 1
    half = 1 << (w - 1)
    span = 1 << w
    while True:
        if k0 & k1 or ulo > uhi or slo > shi:
            return bottom(w)
        # bitwise -> unsigned
        nulo, nuhi = max(ulo, k1), min(uhi, m & ~k0)
        # signed -> unsigned
        if slo >= 0:
            lo, hi = slo, shi
        elif shi < 0:
            lo, hi = slo + span, shi + span
        else:
            lo, hi = 0, m
        nulo, nuhi = max(nulo, lo), min(nuhi, hi)
        if nulo > nuhi:
            return bottom(w)
        # unsigned -> signed
        if nuhi < half:
            s_lo, s_hi = nulo, nuhi
        elif nulo >= half:
            s_lo, s_hi = nulo - span, nuhi - span
        else:
            s_lo, s_hi = -half, half - 1
        nslo, nshi = max(slo, s_lo), min(shi, s_hi)
        if nslo > nshi:
            return bottom(w)
        # unsigned -> bitwise: common prefix of the interval bounds is known
        diff = nulo ^ nuhi
        prefix = m & ~((1 << diff.bit_length()) - 1)
        nk1 = k1 | (nulo & prefix)
        nk0 = k0 | (~nulo & prefix & m)
        if (nk0, nk1, nulo, nuhi, nslo, nshi) == (k0, k1, ulo, uhi, slo, shi):
            return BV(w, k0, k1, ulo, uhi, slo, shi)
        k0, k1, ulo, uhi, slo, shi = nk0, nk1, nulo, nuhi, nslo, nshi


def top(w: int) -> BV:
    half = 1 << (w - 1)
    return BV(w, 0, 0, 0, (1 << w) - 1, -half, half - 1)


def alpha(w: int, v: int) -> BV:
    m = (1 << w) - 1
    v &= m
    sv = v - (1 << w) if v >> (w - 1) else v
    return BV(w, m & ~v, v, v, v, sv, sv)


def meet(a: BV, b: BV) -> BV:
    if a.is_bottom or b.is_bottom:
        return bottom(a.w)
    if a == b:
        return a
    return reduce_(
        a.w,
        a.k0 | b.k0,
        a.k1 | b.k1,
        max(a.ulo, b.ulo),
        min(a.uhi, b.uhi),
        max(a.slo, b.slo),
        min(a.shi, b.shi),
    )


def join(a: BV, b: BV) -> BV:
    if a.is_bottom:
        return b
    if b.is_bottom:
        return a
    return reduce_(
        a.w,
        a.k0 & b.k0,
        a.k1 & b.k1,
        min(a.ulo, b.ulo),
        max(a.uhi, b.uhi),
        min(a.slo, b.slo),
        max(a.shi, b.shi),
    )


def leq(a: BV, b: BV) -> bool:
    if a.is_bottom:
        return True
    if b.is_bottom:
        return False
    return (
        b.k0 & ~a.k0 == 0
        and b.k1 & ~a.k1 == 0
        and b.ulo <= a.ulo
        and a.uhi <= b.uhi
        and b.slo <= a.slo
        and a.shi <= b.shi
    )
