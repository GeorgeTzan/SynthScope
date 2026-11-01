import random

from hope_engine.meta.bitvector import BitvectorMeta
from hope_engine.meta.rank import choose, pick_holes, rank_hole_sets, rank_holes
from hope_engine.syntax.ast import Hole, Op, Var

D = BitvectorMeta()
H = Hole("S")
SUM3 = Op("bvadd", (Op("bvadd", (H, H)), H))  # the paper's "hole + hole + hole"


def test_one_hole_equals_single_hole_algorithm() -> None:
    for prog in (SUM3, Op("bvxor", (Var("x"), H)), Op("bvand", (H, H))):
        for seed in range(5):
            (pos,), noprune = pick_holes(prog, D, random.Random(seed), 1)
            assert (pos, noprune) == choose(rank_holes(prog, D), prog, random.Random(seed))


SUM4 = Op("bvadd", (Op("bvadd", (H, H)), Op("bvadd", (H, H))))
PAIRS = {((0, 0), (0, 1)), ((1, 0), (1, 1))}


def test_single_holes_cannot_help_on_sum_of_sums() -> None:
    ranked = rank_hole_sets(SUM4, D, 1)
    assert ranked.rank1 == () and ranked.rank2 == ()
    positions, noprune = pick_holes(SUM4, D, random.Random(0), 1)
    assert len(positions) == 1 and noprune is True


def test_sibling_pair_helps_when_two_holes_allowed() -> None:
    for k in (2, 3):
        positions, noprune = pick_holes(SUM4, D, random.Random(0), k)
        assert positions in PAIRS and noprune is False


def test_smallest_ranked_set_is_preferred() -> None:
    ranked = rank_hole_sets(SUM4, D, 3)
    assert min(len(s) for s in ranked.rank1) == 2
    assert all(len(pick_holes(SUM4, D, random.Random(i), 3)[0]) == 2 for i in range(6))


def test_single_hole_when_one_hole_already_ranks() -> None:
    prog = Op("bvxor", (Var("x"), H))
    assert rank_hole_sets(prog, D, 3).rank1 == (((1,),),)
    positions, _ = pick_holes(prog, D, random.Random(0), 3)
    assert positions == ((1,),)


def test_no_holes_gives_no_sets() -> None:
    ranked = rank_hole_sets(Op("bvnot", (Var("x"),)), D, 3)
    assert ranked.rank1 == () and ranked.rank2 == ()
