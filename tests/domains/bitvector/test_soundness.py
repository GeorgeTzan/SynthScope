import itertools
import random

import pytest

from hope_engine.concrete.bitvector import BINARY, BOOL_OPS, UNARY, UnsupportedOperator
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


BOOLS = sorted(BOOL_OPS)


def _typed(op: str, i: int) -> bool:
    """True when argument i of op holds a Boolean (0 or 1); ite branches and = operands hold any value."""
    return op in ("and", "or", "not") or (op == "ite" and i == 0)


def _tuples(op: str, args: list[BV]) -> list[tuple[int, ...]]:
    pools = [[v for v in gamma(a) if not _typed(op, i) or v in (0, 1)] for i, a in enumerate(args)]
    return list(itertools.product(*pools))


def _arg_sets(op: str, w: int, rng: random.Random) -> list[list[BV]]:
    els = elements(w, rng, 6)
    n = BOOL_OPS[op][0]
    out = [list(c) for c in itertools.product(els, repeat=n)]
    return out if len(out) <= 600 else rng.sample(out, 600)


@pytest.mark.parametrize("w", [1, 2, 3])
@pytest.mark.parametrize("op", BOOLS)
def test_bool_forward_sound(op: str, w: int) -> None:
    d = BitvectorDomain(w)
    for args in _arg_sets(op, w, random.Random(5)):
        res = d.forward(op, args)
        for vals in _tuples(op, args):
            assert res.contains(BOOL_OPS[op][1](*vals)), (op, args, vals)


@pytest.mark.parametrize("w", [1, 2, 3])
@pytest.mark.parametrize("op", BOOLS)
def test_bool_backward_sound(op: str, w: int) -> None:
    d = BitvectorDomain(w)
    rng = random.Random(6)
    els = elements(w, rng, 4)
    for args in _arg_sets(op, w, rng):
        for r in rng.sample(els, min(5, len(els))):
            pres = [d.backward(op, r, args, i) for i in range(len(args))]
            for vals in _tuples(op, args):
                if r.contains(BOOL_OPS[op][1](*vals)):
                    for i, v in enumerate(vals):
                        unused = op == "ite" and (i, vals[0]) in ((1, 0), (2, 1))  # untaken branch: unconstrained
                        assert unused or pres[i].contains(v), (op, i, args, r, vals)


def test_bool_forward_decides_when_it_can() -> None:
    d = BitvectorDomain(4)
    one, zero = alpha(4, 1), alpha(4, 0)
    assert d.forward("=", [alpha(4, 3), alpha(4, 5)]) == zero
    assert d.forward("and", [zero, top(4)]) == zero
    assert d.forward("or", [one, top(4)]) == one
    assert d.forward("ite", [one, alpha(4, 7), alpha(4, 2)]) == alpha(4, 7)
    assert d.backward("ite", alpha(4, 7), [top(4), alpha(4, 7), alpha(4, 2)], 0) == one


def test_ite_untaken_branch_is_unconstrained() -> None:
    d = BitvectorDomain(4)
    pre = d.backward("ite", alpha(4, 7), [alpha(4, 1), alpha(4, 7), top(4)], 2)
    assert not pre.is_bottom
