"""String/int abstract values (paper §4.6.3).

Str = reduced product of the prefix-with-length and suffix-with-length domains:
  pre / suf are patterns over characters and '*' (an unknown character), aligned at the start / end;
  [lo, hi] bounds the string length (hi == INF means unbounded).
When the length is exact (lo == hi) both patterns are padded to the full length and merged.
Itv is an integer interval. TOP is the untyped top (any string or int); BOT is empty.
"""

from __future__ import annotations

from dataclasses import dataclass

INF = 1 << 62


@dataclass(frozen=True)
class Str:
    pre: str
    suf: str
    lo: int
    hi: int


@dataclass(frozen=True)
class Itv:
    lo: int
    hi: int


@dataclass(frozen=True)
class _Special:
    name: str


TOP = _Special("top")
BOT = _Special("bot")
type A = Str | Itv | _Special

TOP_STR = Str("", "", 0, INF)
TOP_INT = Itv(-INF, INF)


def mk_str(pre: str, suf: str, lo: int, hi: int) -> A:
    lo = max(lo, len(pre), len(suf), 0)
    if lo > hi:
        return BOT
    if lo == hi:
        merged: list[str] = []
        for a, b in zip(pre.ljust(lo, "*"), suf.rjust(lo, "*"), strict=True):
            if a == "*":
                merged.append(b)
            elif b in ("*", a):
                merged.append(a)
            else:
                return BOT
        pre = suf = "".join(merged)
    return Str(pre, suf, lo, hi)


def mk_itv(lo: int, hi: int) -> A:
    return BOT if lo > hi else Itv(max(lo, -INF), min(hi, INF))


def alpha(value: int | str) -> A:
    if isinstance(value, str):
        return mk_str(value, value, len(value), len(value))
    return Itv(value, value)


def _match_pre(pat: str, v: str) -> bool:
    return len(pat) <= len(v) and all(c == "*" or c == v[i] for i, c in enumerate(pat))


def _match_suf(pat: str, v: str) -> bool:
    return len(pat) <= len(v) and all(
        c == "*" or c == v[len(v) - len(pat) + i] for i, c in enumerate(pat)
    )


def contains(a: A, v: int | str) -> bool:
    if a is TOP:
        return True
    if a is BOT:
        return False
    if isinstance(a, Itv):
        return isinstance(v, int) and a.lo <= v <= a.hi
    assert isinstance(a, Str)
    return isinstance(v, str) and a.lo <= len(v) <= a.hi and _match_pre(a.pre, v) and _match_suf(a.suf, v)


def _meet_pat(a: str, b: str) -> str | None:
    out: list[str] = []
    for i in range(max(len(a), len(b))):
        x = a[i] if i < len(a) else "*"
        y = b[i] if i < len(b) else "*"
        if x == "*":
            out.append(y)
        elif y in ("*", x):
            out.append(x)
        else:
            return None
    return "".join(out)


def _join_pat(a: str, b: str) -> str:
    return "".join(x if x == y else "*" for x, y in zip(a, b, strict=False))


def meet(a: A, b: A) -> A:
    if a is BOT or b is BOT:
        return BOT
    if a is TOP:
        return b
    if b is TOP:
        return a
    if isinstance(a, Itv) and isinstance(b, Itv):
        return mk_itv(max(a.lo, b.lo), min(a.hi, b.hi))
    if isinstance(a, Str) and isinstance(b, Str):
        pre = _meet_pat(a.pre, b.pre)
        rsuf = _meet_pat(a.suf[::-1], b.suf[::-1])
        if pre is None or rsuf is None:
            return BOT
        return mk_str(pre, rsuf[::-1], max(a.lo, b.lo), min(a.hi, b.hi))
    return BOT  # type clash


def join(a: A, b: A) -> A:
    if a is BOT:
        return b
    if b is BOT:
        return a
    if a is TOP or b is TOP:
        return TOP
    if isinstance(a, Itv) and isinstance(b, Itv):
        return Itv(min(a.lo, b.lo), max(a.hi, b.hi))
    if isinstance(a, Str) and isinstance(b, Str):
        pre = _join_pat(a.pre, b.pre)
        suf = _join_pat(a.suf[::-1], b.suf[::-1])[::-1]
        return mk_str(pre, suf, min(a.lo, b.lo), max(a.hi, b.hi))
    return TOP


def leq(a: A, b: A) -> bool:
    """Conservative inclusion test: True implies gamma(a) is a subset of gamma(b)."""
    if a is BOT or b is TOP:
        return True
    if b is BOT or a is TOP:
        return False
    if isinstance(a, Itv) and isinstance(b, Itv):
        return b.lo <= a.lo and a.hi <= b.hi
    if isinstance(a, Str) and isinstance(b, Str):
        return (
            b.lo <= a.lo
            and a.hi <= b.hi
            and len(b.pre) <= len(a.pre)
            and all(c == "*" or c == a.pre[i] for i, c in enumerate(b.pre))
            and len(b.suf) <= len(a.suf)
            and all(c == "*" or c == a.suf[len(a.suf) - len(b.suf) + i] for i, c in enumerate(b.suf))
        )
    return False
