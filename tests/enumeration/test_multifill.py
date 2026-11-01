import pytest

from hope_engine.concrete.verify import Example, satisfies
from hope_engine.domains.analysis import DomainAnalyzer
from hope_engine.domains.bitvector.ops import BitvectorDomain
from hope_engine.enumeration.multifill import fill_selected
from hope_engine.enumeration.search import (
    Budget,
    NullAnalyzer,
    PickContext,
    Problem,
    search,
)
from hope_engine.meta.bitvector import BitvectorMeta
from hope_engine.meta.policies import HopePolicy
from hope_engine.syntax.ast import Const, Hole, Node, Op, Path, Var, holes, replace_at
from hope_engine.syntax.grammar import Grammar, Production

P = Op("f", (Hole("A"), Hole("B")))
A1, A2 = Var("a1"), Var("a2")
B1, B2, B3 = Var("b1"), Var("b2"), Var("b3")


def test_cartesian_product_in_deterministic_order() -> None:
    got = list(fill_selected(P, ((0,), (1,)), [[A1, A2], [B1, B2, B3]]))
    assert got == [Op("f", (a, b)) for a in (A1, A2) for b in (B1, B2, B3)]


def test_single_position_equals_replace_at() -> None:
    assert list(fill_selected(P, ((1,),), [[B1, B2]])) == [replace_at(P, (1,), B1), replace_at(P, (1,), B2)]


def test_overlapping_positions_rejected() -> None:
    with pytest.raises(ValueError):
        list(fill_selected(Op("g", (Hole("A"),)), ((), (0,)), [[A1], [A2]]))
    with pytest.raises(ValueError):
        list(fill_selected(P, ((0,), (0,)), [[A1], [A2]]))


def test_empty_positions_rejected() -> None:
    with pytest.raises(ValueError):
        list(fill_selected(P, (), []))


def test_no_candidates_yields_nothing() -> None:
    assert list(fill_selected(P, ((0,), (1,)), [[A1], []])) == []


def test_is_lazy() -> None:
    it = fill_selected(P, ((0,), (1,)), [[A1] * 10**6, [B1] * 10**6])
    assert next(it) == Op("f", (A1, B1))


class AllHoles:
    def pick(self, partial: Node, ctx: PickContext) -> tuple[tuple[Path, ...], bool]:
        return holes(partial), False


G = Grammar(
    (
        Production("S", Var("x")),
        Production("S", Const(1, "bv")),
        Production("S", Const(2, "bv")),
        Production("S", "bvadd", ("S", "S")),
    ),
    "S",
)


def test_combination_cap_stops_cleanly() -> None:
    problem = Problem(G, (Example({"x": 3}, 0),), "bv", 4)
    r = search(problem, NullAnalyzer(), AllHoles(), Budget(5, 5.0))
    assert r.status == "exhausted" and r.nodes <= 5


@pytest.mark.parametrize("k", [1, 3, 5])
def test_ablation_hole_counts_find_valid_programs(k: int) -> None:
    exs = (Example({"x": 3}, 7), Example({"x": 5}, 11))
    problem = Problem(G, exs, "bv", 4)
    policy = HopePolicy(BitvectorMeta(), seed=0, max_holes=k)
    r = search(problem, DomainAnalyzer(BitvectorDomain(4)), policy, Budget(20000, 60.0))
    assert r.status == "solved" and r.program is not None
    assert satisfies(r.program, exs, 4)
