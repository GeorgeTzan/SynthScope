import itertools
from pathlib import Path

from hope_engine.bench.runner import RunConfig, run_file
from hope_engine.domains.bitvector.lattice import (
    BV,
    alpha,
    cardinality,
    meet,
    reduce_,
    top,
)
from hope_engine.enumeration.components import ComponentMap
from hope_engine.enumeration.search import AnalysisResult, PickContext, Problem
from hope_engine.meta.policies import ConstrainedPolicy
from hope_engine.syntax.ast import Hole, Op
from hope_engine.syntax.grammar import Grammar, Production

FIX = Path(__file__).parents[1] / "sygus" / "fixtures"
PARTIAL = Op("bvadd", (Hole("S"), Op("bvand", (Hole("S"), Hole("S")))))
PROBLEM = Problem(Grammar((Production("S", "bvadd", ("S", "S")),), "S"), (), "bv", 8)


def ctx(pre: dict[tuple[int, ...], tuple[BV, ...]]) -> PickContext:
    return PickContext(PROBLEM, ComponentMap(), analysis=AnalysisResult(False, dict(pre)))


def test_cardinality_examples() -> None:
    assert cardinality(top(8)) == 256 and cardinality(alpha(8, 5)) == 1
    assert cardinality(reduce_(8, 0xF0, 0, 0, 255, -128, 127)) == 16
    assert cardinality(reduce_(8, 0, 0, 10, 12, -128, 127)) == 3
    assert cardinality(meet(alpha(8, 1), alpha(8, 2))) == 0


def test_cardinality_is_an_upper_bound() -> None:
    w = 3
    values = [reduce_(w, k0, k1, lo, hi, -4, 3) for k0, k1, lo, hi in itertools.product(range(8), range(8), range(8), range(8))]
    for a in values:
        assert sum(a.contains(v) for v in range(8)) <= cardinality(a)


def test_picks_the_tightest_hole() -> None:
    t, one, few = top(8), alpha(8, 3), reduce_(8, 0xF0, 0, 0, 255, -128, 127)
    pre = {(0,): (t, t), (1, 0): (few, t), (1, 1): (one, few)}
    assert ConstrainedPolicy(cardinality).pick(PARTIAL, ctx(pre)) == (((1, 1),), False)


def test_ties_go_to_the_leftmost_hole() -> None:
    t = top(8)
    pre = {(0,): (t,), (1, 0): (t,), (1, 1): (t,)}
    assert ConstrainedPolicy(cardinality).pick(PARTIAL, ctx(pre)) == (((0,),), False)


def test_without_analysis_falls_back_to_leftmost() -> None:
    assert ConstrainedPolicy(cardinality).pick(PARTIAL, PickContext(PROBLEM, ComponentMap())) == (((0,),), False)


def test_runner_supports_constrained_on_bitvectors_only() -> None:
    r = run_file(FIX / "bv.sl", RunConfig("constrained", 1, 200000, 30.0, 0))
    assert r.status == "solved" and r.validated and r.meta_calls == 0
    assert run_file(FIX / "string.sl", RunConfig("constrained", 1, 200000, 30.0, 0)).status == "unsupported"
