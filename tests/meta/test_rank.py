import random
from collections.abc import Sequence

from hope_engine.concrete.verify import Example
from hope_engine.enumeration.search import Budget, NullAnalyzer, Problem, search
from hope_engine.meta.analysis import meta_analyze
from hope_engine.meta.bitvector import BitvectorMeta
from hope_engine.meta.lattice import Meta
from hope_engine.meta.policies import HopePolicy, MetaOffPolicy
from hope_engine.meta.rank import (
    choose,
    may_infeasible,
    may_prune_components,
    rank_holes,
)
from hope_engine.syntax.ast import Const, Hole, Op, Var
from hope_engine.syntax.grammar import Grammar, Production
from hope_engine.trace.events import Event

MUST, MAY = Meta.MUST_TOP, Meta.MAY_NOT_TOP


class Inert(BitvectorMeta):
    """Operator 'id0' ignores its arguments: no hole can ever help pruning."""

    def forward(self, op: str, args: Sequence[Meta]) -> Meta:
        return MUST

    def backward(self, op: str, result: Meta, args: Sequence[Meta], i: int) -> Meta:
        return MUST


INERT = Op("id0", (Hole("S"), Hole("S")))


def test_all_rank3_returns_noprune_true() -> None:
    ranks = rank_holes(INERT, Inert())
    assert ranks.rank1 == () and ranks.rank2 == ()
    pos, noprune = choose(ranks, INERT, random.Random(0))
    assert pos in ((0,), (1,)) and noprune is True


def test_rank3_pick_is_seeded() -> None:
    ranks = rank_holes(INERT, Inert())
    a = [choose(ranks, INERT, random.Random(7))[0] for _ in range(5)]
    b = [choose(ranks, INERT, random.Random(7))[0] for _ in range(5)]
    assert a == b


def test_policy_sequence_is_reproducible() -> None:
    p1, p2 = MetaOffPolicy(seed=3), MetaOffPolicy(seed=3)
    prog = Op("bvadd", (Hole("S"), Hole("S")))
    ctx = None  # MetaOffPolicy ignores the context
    picks1 = [p1.pick(prog, ctx) for _ in range(8)]  # type: ignore[arg-type]
    picks2 = [p2.pick(prog, ctx) for _ in range(8)]  # type: ignore[arg-type]
    assert picks1 == picks2
    assert all(noprune is False for _, noprune in picks1)


def test_conditions_on_bitvector_meta() -> None:
    d = BitvectorMeta()
    # bvxor(x, hole): forward of a hole alone is May, so the root may be non-top and may be pruned.
    prog = Op("bvxor", (Var("x"), Hole("S")))
    res = meta_analyze(d, prog, ((1,),))
    assert may_infeasible(res, d)
    assert not may_prune_components(res, d, ((1,),), ((1,),))


def test_no_holes_has_no_ranks() -> None:
    ranks = rank_holes(Op("bvnot", (Var("x"),)), BitvectorMeta())
    assert ranks.rank1 == () and ranks.rank2 == ()


def test_hope_policy_emits_hole_ranked_and_solves() -> None:
    g = Grammar(
        (
            Production("S", Var("x")),
            Production("S", Const(1, "bv")),
            Production("S", "bvadd", ("S", "S")),
        ),
        "S",
    )
    problem = Problem(g, (Example({"x": 3}, 4),), "bv", 4)
    got: list[Event] = []
    r = search(problem, NullAnalyzer(), HopePolicy(BitvectorMeta(), seed=0), Budget(2000, None), got.append)
    assert r.status == "solved"
    assert "hole_ranked" in {e.kind for e in got}
