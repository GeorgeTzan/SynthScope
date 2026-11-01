"""Forward/backward abstract operators for strings and ints.

Derived from the paper's §4.6.3 description and Figs 3-4 (prefix domain; the suffix domain is the
mirror image) plus plain interval reasoning; the HOPE supplement's full tables are not public.
Operators without a refined rule fall back to the paper's default: bottom if any argument is bottom,
else top. All rules are checked for soundness by exhaustive tests. See research/known_deviations.md.
"""

from __future__ import annotations

from collections.abc import Sequence

from hope_engine.concrete.bitvector import UnsupportedOperator
from hope_engine.concrete.string import OPS
from hope_engine.domains.string.lattice import (
    BOT,
    INF,
    TOP,
    TOP_INT,
    TOP_STR,
    A,
    Itv,
    Str,
    alpha,
    join,
    leq,
    meet,
    mk_itv,
    mk_str,
)

# argument kinds and result kind per operator: s = string, i = int
SIGNATURES: dict[str, tuple[str, str]] = {
    "str.++": ("s*", "s"),
    "ConCat": ("s*", "s"),
    "str.at": ("si", "s"),
    "CharAt0": ("s", "s"),
    "str.substr": ("sii", "s"),
    "str.indexof": ("ssi", "i"),
    "str.len": ("s", "i"),
    "str.to.int": ("s", "i"),
    "int.to.str": ("i", "s"),
    "str.replace": ("sss", "s"),
}


def _kinds(op: str, n: int) -> str:
    if op not in SIGNATURES or op not in OPS:
        raise UnsupportedOperator(f"{op}/{n}")
    kinds = SIGNATURES[op][0]
    lo, hi, _ = OPS[op]
    if n < lo or (hi is not None and n > hi):
        raise UnsupportedOperator(f"{op}/{n}")
    return kinds.replace("*", "") * n if kinds.endswith("*") else kinds


def _as_str(a: A) -> Str | None:
    if a is TOP:
        return TOP_STR
    if a is BOT:
        return None
    if isinstance(a, Str):
        return a
    raise TypeError(f"expected a string abstraction, got {a!r}")


def _as_int(a: A) -> Itv | None:
    if a is TOP:
        return TOP_INT
    if a is BOT:
        return None
    if isinstance(a, Itv):
        return a
    raise TypeError(f"expected an int abstraction, got {a!r}")


def _exact(a: A) -> int | str | None:
    if isinstance(a, Str) and a.lo == a.hi and "*" not in a.pre:
        return a.pre
    if isinstance(a, Itv) and a.lo == a.hi:
        return a.lo
    return None


def _add(x: int, y: int) -> int:
    return INF if x >= INF or y >= INF else min(INF, x + y)


def _sub(x: int, y: int) -> int:
    """x - y for an upper bound x (INF-safe)."""
    return INF if x >= INF else x - y


def _concat2(a: Str, b: Str) -> A:
    pre = a.pre + b.pre if a.lo == a.hi else a.pre
    suf = a.suf + b.suf if b.lo == b.hi else b.suf
    return mk_str(pre, suf, a.lo + b.lo, _add(a.hi, b.hi))


def _at_one(s: Str, k: int) -> A:
    if k < 0 or k >= s.hi:
        return alpha("")
    if k < s.lo:
        c = s.pre[k] if k < len(s.pre) else "*"
        return mk_str(c, c, 1, 1)
    return mk_str("", "", 0, 1)


def _forward_at(s: Str, i: Itv) -> A:
    hi_k = max(min(i.hi, s.hi) if s.hi < INF else i.hi, -1)  # indexes past the end behave like s.hi
    lo_k = min(max(i.lo, -1), hi_k)  # negative indexes all behave like -1
    if hi_k >= INF or hi_k - lo_k > 16:
        return mk_str("", "", 0, 1)
    out: A = BOT
    for k in range(lo_k, hi_k + 1):
        out = join(out, _at_one(s, k))
    return out


def _forward_substr(s: Str, i: Itv, n: Itv) -> A:
    k, m = _exact(i), _exact(n)
    if not isinstance(k, int) or not isinstance(m, int):
        return mk_str("", "", 0, s.hi)
    if k < 0 or m <= 0 or k >= s.hi:
        return alpha("")
    if s.lo == s.hi:  # exact length: the pattern is the whole string
        sub = s.pre[k : k + m]
        return mk_str(sub, sub, len(sub), len(sub))
    lo_len = 0 if k >= s.lo else min(m, s.lo - k)
    hi_len = min(m, _sub(s.hi, k)) if s.hi < INF else m
    return mk_str(s.pre[k : k + m] if k < len(s.pre) else "", "", lo_len, hi_len)


def _forward_to_int(s: Str) -> A:
    if any(c not in "*0123456789" for c in s.pre + s.suf):
        return Itv(-1, -1)
    hi = 10**s.hi - 1 if s.hi <= 18 else INF
    return Itv(-1, hi)


def _forward_int_to_str(n: Itv) -> A:
    if n.lo == n.hi:
        return alpha(str(n.lo) if n.lo >= 0 else "")
    out: A = BOT
    if n.lo < 0:
        out = alpha("")
    if n.hi >= 0:
        lo_d = len(str(max(n.lo, 0)))
        hi_d = INF if n.hi >= INF else len(str(n.hi))
        out = join(out, mk_str("", "", lo_d, hi_d))
    return out


def forward(op: str, args: Sequence[A]) -> A:
    kinds = _kinds(op, len(args))
    if any(a is BOT for a in args):
        return BOT
    exact = [_exact(a) for a in args]
    if all(e is not None for e in exact):
        return alpha(OPS[op][2](*exact))
    typed: list[Str | Itv] = []
    for a, k in zip(args, kinds, strict=True):
        t = _as_str(a) if k == "s" else _as_int(a)
        assert t is not None
        typed.append(t)
    if op in ("str.++", "ConCat"):
        acc = typed[0]
        for nxt in typed[1:]:
            assert isinstance(acc, Str) and isinstance(nxt, Str)
            r = _concat2(acc, nxt)
            if not isinstance(r, Str):
                return BOT
            acc = r
        return acc
    s0 = typed[0]
    if op == "str.at" and isinstance(s0, Str) and isinstance(typed[1], Itv):
        return _forward_at(s0, typed[1])
    if op == "CharAt0" and isinstance(s0, Str):
        return _forward_at(s0, Itv(0, 0))
    if op == "str.len" and isinstance(s0, Str):
        return mk_itv(s0.lo, s0.hi)
    if op == "str.substr" and isinstance(s0, Str) and isinstance(typed[1], Itv) and isinstance(typed[2], Itv):
        return _forward_substr(s0, typed[1], typed[2])
    if op == "str.indexof" and isinstance(s0, Str):
        return Itv(-1, s0.hi)
    if op == "str.to.int" and isinstance(s0, Str):
        return _forward_to_int(s0)
    if op == "int.to.str" and isinstance(s0, Itv):
        return _forward_int_to_str(s0)
    if op == "str.replace":
        hi = _add(s0.hi, typed[2].hi) if isinstance(s0, Str) and isinstance(typed[2], Str) else INF
        return mk_str("", "", 0, hi)
    return TOP_STR if SIGNATURES[op][1] == "s" else TOP_INT


def _backward_concat2(r: Str, a: Str, b: Str, i: int) -> A:
    if i == 0:
        need = max(0, r.lo - b.hi) if b.hi < INF else 0
        lo, hi = need, _sub(r.hi, b.lo)
        pre = r.pre[:need]
        suf = r.suf[: len(r.suf) - b.lo] if b.lo == b.hi and b.lo > 0 else (r.suf if b.lo == b.hi else "")
        return mk_str(pre, suf, lo, hi)
    need = max(0, r.lo - a.hi) if a.hi < INF else 0
    lo, hi = need, _sub(r.hi, a.lo)
    suf = r.suf[len(r.suf) - min(need, len(r.suf)) :] if need > 0 else ""
    pre = r.pre[a.lo :] if a.lo == a.hi else ""
    return mk_str(pre, suf, lo, hi)


def _backward_concat(r: Str, parts: list[Str], i: int) -> A:
    if len(parts) == 2:
        return _backward_concat2(r, parts[0], parts[1], i)
    left_parts, last = parts[:-1], parts[-1]
    left: A = left_parts[0]
    for p in left_parts[1:]:
        assert isinstance(left, Str)
        left = _concat2(left, p)
    if not isinstance(left, Str):
        return BOT
    if i == len(parts) - 1:
        return _backward_concat2(r, left, last, 1)
    refined = meet(left, _backward_concat2(r, left, last, 0))
    if not isinstance(refined, Str):
        return BOT
    return _backward_concat(refined, left_parts, i)


def _backward_at_string(r: Str, k: int | None, i: Itv) -> A:
    if r.lo < 1:
        return TOP_STR
    if k is not None and k >= 0:
        c = r.pre[0] if r.pre else "*"
        return mk_str("*" * k + c, "", k + 1, INF)
    return mk_str("", "", max(1, i.lo + 1) if i.lo >= 0 else 1, INF)


def backward(op: str, result: A, args: Sequence[A], i: int) -> A:
    kinds = _kinds(op, len(args))
    if result is BOT or any(a is BOT for a in args):
        return BOT
    kind = kinds[i]
    top = TOP_STR if kind == "s" else TOP_INT
    r = _as_str(result) if SIGNATURES[op][1] == "s" else _as_int(result)
    assert r is not None
    if op in ("str.++", "ConCat") and isinstance(r, Str):
        parts = [_as_str(a) for a in args]
        assert all(p is not None for p in parts)
        return _backward_concat(r, [p for p in parts if p is not None], i)
    if op in ("str.at", "CharAt0") and isinstance(r, Str):
        if i == 0:
            idx = _as_int(args[1]) if op == "str.at" else Itv(0, 0)
            assert idx is not None
            k = _exact(idx)
            return _backward_at_string(r, k if isinstance(k, int) else None, idx)
        s = _as_str(args[0])
        assert s is not None
        return mk_itv(0, max(0, s.hi - 1) if s.hi < INF else INF) if r.lo >= 1 else TOP_INT
    if op == "str.len" and isinstance(r, Itv):
        return mk_str("", "", max(0, r.lo), r.hi)
    return top


__all__ = ["SIGNATURES", "StringDomain", "backward", "forward"]


class StringDomain:
    def top(self) -> A:
        return TOP

    def bottom(self) -> A:
        return BOT

    def alpha(self, value: int | str) -> A:
        return alpha(value)

    def is_bottom(self, a: A) -> bool:
        return a is BOT

    def leq(self, a: A, b: A) -> bool:
        return leq(a, b)

    def join(self, a: A, b: A) -> A:
        return join(a, b)

    def meet(self, a: A, b: A) -> A:
        return meet(a, b)

    def forward(self, op: str, args: Sequence[A]) -> A:
        return forward(op, args)

    def backward(self, op: str, result: A, args: Sequence[A], i: int) -> A:
        return backward(op, result, args, i)
