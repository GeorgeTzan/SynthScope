import itertools
import random

import pytest

from hope_engine.concrete.bitvector import BINARY, UNARY, UnsupportedOperator
from hope_engine.domains.bitvector.lattice import BV, alpha, bottom, join, reduce_, top
from hope_engine.domains.bitvector.ops import BitvectorDomain

UN = sorted(UNARY)
BIN = sorted(BINARY)


def gamma(a: BV) -> list[int]:
    return [v for v in range(1 << a.w) if a.contains(v)]


def of(vals: set[int], w: int) -> BV:
    out = bottom(w)
    for v in vals:
        out = join(out, alpha(w, v))
    return out


def elements(w: int, rng: random.Random, n: int) -> list[BV]:
    """Mix of join-of-constants elements, plain unsigned intervals, and top."""
    size = 1 << w
    out = [top(w)]
    for _ in range(n):
        k = rng.randint(1, size)
        out.append(of(set(rng.sample(range(size), k)), w))
    for lo in range(size):
        for hi in range(lo, size):
            half = 1 << (w - 1)
            out.append(reduce_(w, 0, 0, lo, hi, -half, half - 1))
    return out


def all_alpha_elements(w: int) -> list[BV]:
    size = 1 << w
    return [of(set(c), w) for r in range(1, size + 1) for c in itertools.combinations(range(size), r)]


@pytest.mark.parametrize("w", [1, 2, 3])
@pytest.mark.parametrize("op", UN)
def test_forward_unary_sound(op: str, w: int) -> None:
    d = BitvectorDomain(w)
    for a in all_alpha_elements(w) if w < 3 else elements(w, random.Random(1), 40):
        res = d.forward(op, [a])
        for x in gamma(a):
            assert res.contains(UNARY[op](x, w)), (op, a, x)


@pytest.mark.parametrize("w", [1, 2, 3])
@pytest.mark.parametrize("op", BIN)
def test_forward_binary_sound(op: str, w: int) -> None:
    d = BitvectorDomain(w)
    rng = random.Random(2)
    els = all_alpha_elements(w) if w < 3 else elements(w, rng, 25)
    pairs = list(itertools.product(els, repeat=2))
    if len(pairs) > 1500:
        pairs = rng.sample(pairs, 1500)
    for a, b in pairs:
        res = d.forward(op, [a, b])
        for x, y in itertools.product(gamma(a), gamma(b)):
            assert res.contains(BINARY[op](x, y, w)), (op, a, b, x, y)


@pytest.mark.parametrize("op", BIN)
def test_forward_constants_are_exact(op: str) -> None:
    w = 4
    d = BitvectorDomain(w)
    for x, y in [(0, 0), (3, 5), (15, 1), (8, 8), (7, 0)]:
        assert d.forward(op, [alpha(w, x), alpha(w, y)]) == alpha(w, BINARY[op](x, y, w))


@pytest.mark.parametrize("w", [1, 2, 3])
@pytest.mark.parametrize("op", UN)
def test_backward_unary_sound(op: str, w: int) -> None:
    d = BitvectorDomain(w)
    rng = random.Random(3)
    els = all_alpha_elements(w) if w < 3 else elements(w, rng, 25)
    for a, r in itertools.product(els, repeat=2):
        pre = d.backward(op, r, [a], 0)
        for x in gamma(a):
            if r.contains(UNARY[op](x, w)):
                assert pre.contains(x), (op, a, r, x)


@pytest.mark.parametrize("w", [1, 2, 3])
@pytest.mark.parametrize("op", BIN)
def test_backward_binary_sound(op: str, w: int) -> None:
    d = BitvectorDomain(w)
    rng = random.Random(4)
    els = all_alpha_elements(w) if w < 3 else elements(w, rng, 12)
    triples = list(itertools.product(els, repeat=3))
    if len(triples) > 1200:
        triples = rng.sample(triples, 1200)
    for a, b, r in triples:
        pre0 = d.backward(op, r, [a, b], 0)
        pre1 = d.backward(op, r, [a, b], 1)
        for x, y in itertools.product(gamma(a), gamma(b)):
            if r.contains(BINARY[op](x, y, w)):
                assert pre0.contains(x), (op, "arg0", a, b, r, x, y)
                assert pre1.contains(y), (op, "arg1", a, b, r, x, y)


def test_bottom_argument_gives_bottom() -> None:
    d = BitvectorDomain(3)
    assert d.forward("bvadd", [bottom(3), alpha(3, 1)]).is_bottom
    assert d.backward("bvadd", alpha(3, 1), [bottom(3), top(3)], 0).is_bottom


def test_unsupported_operator() -> None:
    d = BitvectorDomain(3)
    with pytest.raises(UnsupportedOperator):
        d.forward("bvcomp", [top(3), top(3)])
    with pytest.raises(UnsupportedOperator):
        d.backward("bvcomp", top(3), [top(3), top(3)], 0)


def test_bvmul_by_even_constant_clears_low_bit() -> None:
    d = BitvectorDomain(4)
    res = d.forward("bvmul", [top(4), alpha(4, 2)])
    assert not res.contains(1) and not res.contains(3) and res.contains(2)
