"""Exhaustive-universe soundness of the string domain: strings over {a,b} up to length 3, ints -2..5."""

import itertools
import random

import pytest

from hope_engine.concrete.bitvector import UnsupportedOperator
from hope_engine.concrete.string import OPS, Value
from hope_engine.domains.string.lattice import (
    BOT,
    INF,
    TOP,
    A,
    Itv,
    Str,
    alpha,
    contains,
    join,
    leq,
    meet,
    mk_str,
)
from hope_engine.domains.string.ops import StringDomain

D = StringDomain()
STRS = [""] + ["".join(p) for n in (1, 2, 3) for p in itertools.product("ab", repeat=n)]
INTS = list(range(-2, 6))

SIGS: dict[str, tuple[str, ...]] = {
    "str.++": ("s", "s"),
    "str.at": ("s", "i"),
    "CharAt0": ("s",),
    "str.substr": ("s", "i", "i"),
    "str.indexof": ("s", "s", "i"),
    "str.len": ("s",),
    "str.to.int": ("s",),
    "int.to.str": ("i",),
    "str.replace": ("s", "s", "s"),
    "+": ("i", "i"),
    "-": ("i", "i"),
    "str.prefixof": ("s", "s"),
    "str.suffixof": ("s", "s"),
    "str.contains": ("s", "s"),
}
THREE = ("str.++3", ("s", "s", "s"))


def rand_str(rng: random.Random):  # type: ignore[no-untyped-def]
    if rng.random() < 0.4:
        out: A = BOT
        for v in rng.sample(STRS, rng.randint(1, 4)):
            out = join(out, alpha(v))
        return out
    pre = "".join(rng.choice("ab*") for _ in range(rng.randint(0, 2)))
    suf = "".join(rng.choice("ab*") for _ in range(rng.randint(0, 2)))
    lo = rng.randint(0, 3)
    hi = rng.choice([lo, lo + 1, lo + 3, INF])
    return mk_str(pre, suf, lo, hi)


def rand_int(rng: random.Random):  # type: ignore[no-untyped-def]
    if rng.random() < 0.3:
        return alpha(rng.choice(INTS))
    lo = rng.randint(-3, 3)
    return Itv(lo, rng.choice([lo, lo + 2, 5, INF]))


def rand_arg(rng: random.Random, kind: str):  # type: ignore[no-untyped-def]
    if rng.random() < 0.05:
        return TOP
    return rand_str(rng) if kind == "s" else rand_int(rng)


def gamma(a, kind: str) -> list[Value]:  # type: ignore[no-untyped-def]
    return [v for v in (STRS if kind == "s" else INTS) if contains(a, v)]


def concrete(op: str, vals: tuple[Value, ...]) -> Value:
    return OPS["str.++" if op == "str.++3" else op][2](*vals)


CASES = [*SIGS.items(), THREE]


@pytest.mark.parametrize(("op", "kinds"), CASES)
def test_forward_sound(op: str, kinds: tuple[str, ...]) -> None:
    rng = random.Random(21)
    real = "str.++" if op == "str.++3" else op
    for _ in range(40 if len(kinds) == 3 else 120):
        args = [rand_arg(rng, k) for k in kinds]
        res = D.forward(real, args)
        pools = [gamma(a, k) for a, k in zip(args, kinds, strict=True)]
        for vals in itertools.product(*pools):
            assert contains(res, concrete(op, vals)), (op, args, vals)


@pytest.mark.parametrize(("op", "kinds"), CASES)
def test_backward_sound(op: str, kinds: tuple[str, ...]) -> None:
    rng = random.Random(22)
    real = "str.++" if op == "str.++3" else op
    for _ in range(40 if len(kinds) == 3 else 100):
        args = [rand_arg(rng, k) for k in kinds]
        pools = [gamma(a, k) for a, k in zip(args, kinds, strict=True)]
        if any(not p for p in pools):
            continue
        outs = [concrete(op, tuple(rng.choice(p) for p in pools)) for _ in range(rng.randint(1, 3))]
        res: A = BOT
        for o in outs:
            res = join(res, alpha(o))
        pres = [D.backward(real, res, args, i) for i in range(len(kinds))]
        for vals in itertools.product(*pools):
            if contains(res, concrete(op, vals)):
                for i, v in enumerate(vals):
                    assert contains(pres[i], v), (op, i, args, res, vals)


def test_alpha_contains_and_join_upper_bound() -> None:
    rng = random.Random(3)
    for _ in range(100):
        sub = rng.sample(STRS, rng.randint(1, 5))
        a: A = BOT
        for v in sub:
            a = join(a, alpha(v))
        assert all(contains(a, v) for v in sub)
        b = rand_str(rng)
        j = join(a, b)
        assert leq(a, j) and leq(b, j)


def test_meet_sound() -> None:
    rng = random.Random(4)
    for _ in range(300):
        a, b = rand_str(rng), rand_str(rng)
        m = meet(a, b)
        for v in STRS:
            if contains(a, v) and contains(b, v):
                assert contains(m, v), (a, b, v)


def test_constants_fold_exactly() -> None:
    a = D.forward("str.++", [alpha("ab"), alpha("b")])
    assert a == alpha("abb")
    assert D.forward("str.len", [alpha("abb")]) == Itv(3, 3)


def test_bottom_propagates_and_unsupported() -> None:
    assert D.forward("str.++", [BOT, alpha("a")]) is BOT
    with pytest.raises(UnsupportedOperator):
        D.forward("str.rev", [alpha("a")])


def test_wildcard_and_length_invariants() -> None:
    e = mk_str("ab", "", 0, 5)
    assert isinstance(e, Str) and e.lo == 2
    assert mk_str("ab", "aa", 3, 3) is BOT  # exact length 3: position 1 is b vs a
    assert mk_str("ab", "ba", 3, 3) == Str("aba", "aba", 3, 3)
    assert mk_str("a*", "*b", 2, 2) == Str("ab", "ab", 2, 2)


BOOLS = [alpha(0), alpha(1), Itv(0, 1), TOP, Itv(-1, 3)]


def _poly_cases(rng: random.Random):  # type: ignore[no-untyped-def]
    """(op, kinds, args) for the type-polymorphic operators = and ite, over strings and ints."""
    for kind in ("s", "i"):
        for _ in range(80):
            yield "=", (kind, kind), [rand_arg(rng, kind), rand_arg(rng, kind)]
            yield "ite", ("b", kind, kind), [rng.choice(BOOLS), rand_arg(rng, kind), rand_arg(rng, kind)]


def _pool(a, kind: str) -> list[Value]:  # type: ignore[no-untyped-def]
    return [v for v in (0, 1) if contains(a, v)] if kind == "b" else gamma(a, kind)


@pytest.mark.parametrize("op", ["=", "ite"])
def test_polymorphic_forward_sound(op: str) -> None:
    for o, kinds, args in _poly_cases(random.Random(31)):
        if o != op:
            continue
        res = D.forward(op, args)
        for vals in itertools.product(*(_pool(a, k) for a, k in zip(args, kinds, strict=True))):
            assert contains(res, OPS[op][2](*vals)), (op, args, vals)


@pytest.mark.parametrize("op", ["=", "ite"])
def test_polymorphic_backward_sound(op: str) -> None:
    rng = random.Random(32)
    for o, kinds, args in _poly_cases(rng):
        if o != op:
            continue
        pools = [_pool(a, k) for a, k in zip(args, kinds, strict=True)]
        if any(not p for p in pools):
            continue
        res: A = BOT
        for _ in range(rng.randint(1, 3)):
            res = join(res, alpha(OPS[op][2](*(rng.choice(p) for p in pools))))
        pres = [D.backward(op, res, args, i) for i in range(len(kinds))]
        for vals in itertools.product(*pools):
            if contains(res, OPS[op][2](*vals)):
                for i, v in enumerate(vals):
                    unused = op == "ite" and (i, vals[0]) in ((1, 0), (2, 1))  # untaken branch is unconstrained
                    assert unused or contains(pres[i], v), (op, i, args, res, vals)


def test_conditional_and_comparison_decide_when_they_can() -> None:
    assert D.forward("=", [alpha("a"), alpha("b")]) == alpha(0)
    assert D.forward("=", [Itv(0, 2), Itv(5, 6)]) == alpha(0)
    assert D.forward("ite", [alpha(1), alpha("x"), alpha("y")]) == alpha("x")
    assert D.forward("+", [Itv(1, 2), Itv(10, 10)]) == Itv(11, 12)
    assert D.backward("=", alpha(1), [TOP, alpha("q")], 0) == alpha("q")
