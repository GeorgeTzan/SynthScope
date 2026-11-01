"""Golden tests: the worked example of paper §2 / Example 4.1 / Example 4.3 (pp. 5-7, 15-17)."""

from collections.abc import Sequence

from hope_engine.meta.analysis import meta_analyze
from hope_engine.meta.lattice import Meta
from hope_engine.meta.rank import choose, rank_holes
from hope_engine.syntax.ast import Hole, Op

MUST, MAY = Meta.MUST_TOP, Meta.MAY_NOT_TOP


class ToyConcat:
    """Abstract operators the paper gives for ConCat(a1, a2, a3) in Example 4.1."""

    def bottom(self) -> Meta:
        return Meta.BOT

    def must(self) -> Meta:
        return MUST

    def may(self) -> Meta:
        return MAY

    def join(self, a: Meta, b: Meta) -> Meta:
        return max(a, b)

    def is_may(self, a: Meta) -> bool:
        return a == MAY

    def is_must(self, a: Meta) -> bool:
        return a == MUST

    def forward(self, op: str, args: Sequence[Meta]) -> Meta:
        return args[2]

    def backward(self, op: str, result: Meta, args: Sequence[Meta], i: int) -> Meta:
        if i == 0:
            return MAY if args[1] != MUST and result != MUST else MUST
        return MUST


P = Op("ConCat", (Hole("S"), Hole("S"), Hole("S")))
D = ToyConcat()
ROOT, P1, P2, P3 = (), (0,), (1,), (2,)


def test_candidate_4_hole_at_position_1() -> None:
    r = meta_analyze(D, P, (P1,))
    assert r[ROOT] == (MUST, MAY)
    assert r[P1] == (MAY, MUST)
    assert r[P2] == (MUST, MUST)
    assert r[P3] == (MUST, MUST)


def test_candidate_5_hole_at_position_2() -> None:
    r = meta_analyze(D, P, (P2,))
    assert r[ROOT] == (MUST, MAY)
    assert r[P1] == (MUST, MAY)
    assert r[P2] == (MAY, MUST)
    assert r[P3] == (MUST, MUST)


def test_candidate_6_hole_at_position_3() -> None:
    r = meta_analyze(D, P, (P3,))
    assert r[ROOT] == (MAY, MAY)
    assert r[P1] == (MUST, MUST)
    assert r[P2] == (MUST, MUST)
    assert r[P3] == (MAY, MUST)


def test_rank1_is_position_3_rank2_is_position_2() -> None:
    ranks = rank_holes(P, D)
    assert ranks.rank1 == (P3,)
    assert ranks.rank2 == (P2,)


def test_pick_prefers_rank1_over_rank2() -> None:
    import random

    assert choose(rank_holes(P, D), P, random.Random(0)) == (P3, False)
