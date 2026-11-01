import itertools

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

W = 3
M = (1 << W) - 1


def gamma(a: BV) -> set[int]:
    return {v for v in range(1 << a.w) if a.contains(v)}


def alpha_set(vals: set[int], w: int = W) -> BV:
    out = bottom(w)
    for v in vals:
        out = join(out, alpha(w, v))
    return out


def test_alpha_is_singleton() -> None:
    for v in range(1 << W):
        assert gamma(alpha(W, v)) == {v}


def test_top_and_bottom() -> None:
    assert gamma(top(W)) == set(range(1 << W))
    assert gamma(bottom(W)) == set() and bottom(W).is_bottom


def test_join_overapproximates_and_is_upper_bound() -> None:
    for s, t in itertools.product([{0}, {1, 2}, {3, 7}, {0, 1, 2, 3}], repeat=2):
        a, b = alpha_set(s), alpha_set(t)
        j = join(a, b)
        assert s | t <= gamma(j)
        assert leq(a, j) and leq(b, j)


def test_meet_is_sound() -> None:
    sets = [{0, 1}, {1, 2}, {2, 3, 4}, {1, 5, 7}, {6}]
    for s, t in itertools.product(sets, repeat=2):
        m = meet(alpha_set(s), alpha_set(t))
        assert s & t <= gamma(m)
        assert gamma(m) <= gamma(alpha_set(s)) & gamma(alpha_set(t))


def test_disjoint_constants_meet_to_bottom() -> None:
    assert meet(alpha(W, 1), alpha(W, 2)).is_bottom


def test_reduction_is_sound_and_tightens() -> None:
    # unsigned [4,5] forces bit pattern 10x => k1=100b
    r = reduce_(W, 0, 0, 4, 5, -4, 3)
    assert gamma(r) == {4, 5}
    assert r.k1 == 0b100 and r.k0 == 0b010


def test_reduction_empty_is_bottom() -> None:
    assert reduce_(W, 0b001, 0b001, 0, M, -4, 3).is_bottom
    assert reduce_(W, 0, 0, 5, 2, -4, 3).is_bottom


def test_leq_matches_gamma_inclusion_on_alpha_images() -> None:
    sets = [set(), {0}, {1}, {0, 1}, {2, 3}, {0, 1, 2, 3}, set(range(8))]
    for s, t in itertools.product(sets, repeat=2):
        if leq(alpha_set(s), alpha_set(t)):
            assert gamma(alpha_set(s)) <= gamma(alpha_set(t))
