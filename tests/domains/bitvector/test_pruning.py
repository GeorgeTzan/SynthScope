import itertools

import pytest

from hope_engine.concrete.bitvector import eval_bv
from hope_engine.concrete.verify import Example, satisfies
from hope_engine.domains.analysis import DomainAnalyzer, analyze_underlying
from hope_engine.domains.bitvector.lattice import BV, alpha, top
from hope_engine.domains.bitvector.ops import BitvectorDomain
from hope_engine.enumeration.search import (
    Budget,
    LeftmostPolicy,
    NullAnalyzer,
    Problem,
    search,
)
from hope_engine.syntax.ast import Const, Hole, Node, Op, Var, replace_at
from hope_engine.syntax.grammar import Grammar, Production

W = 3
D = BitvectorDomain(W)
ANALYZER = DomainAnalyzer(D)


def c(v: int) -> Const:
    return Const(v, "bv")


PROGRAMS: list[Node] = [
    Op("bvadd", (Var("x"), c(1))),
    Op("bvmul", (Op("bvxor", (Var("x"), c(3))), c(5))),
    Op("bvshl", (Var("x"), c(1))),
    Op("bvand", (Op("bvnot", (Var("x"),)), c(6))),
    Op("bvlshr", (Op("bvsub", (Var("x"), c(2))), c(1))),
    Op("bvor", (Op("bvneg", (Var("x"),)), Op("bvurem", (Var("x"), c(3))))),
    Op("bvudiv", (Op("bvadd", (Var("x"), Var("x"))), c(2))),
]


def examples_for(p: Node, xs: range) -> tuple[Example, ...]:
    return tuple(Example({"x": x}, eval_bv(p, {"x": x}, W)) for x in xs)


def positions(node: Node, prefix: tuple[int, ...] = ()) -> list[tuple[int, ...]]:
    out = [prefix]
    if isinstance(node, Op):
        for i, a in enumerate(node.args):
            out += positions(a, (*prefix, i))
    return out


@pytest.mark.parametrize("prog", PROGRAMS)
def test_known_feasible_never_pruned(prog: Node) -> None:
    exs = examples_for(prog, range(1 << W))
    assert satisfies(prog, exs, W)
    ps = positions(prog)
    for p in ps:
        partial = replace_at(prog, p, Hole("S"))
        assert not ANALYZER.analyze(partial, exs).infeasible, (prog, p)
    for p, q in itertools.combinations(ps, 2):
        if q[: len(p)] == p or p[: len(q)] == q:
            continue
        partial = replace_at(replace_at(prog, p, Hole("S")), q, Hole("S"))
        assert not ANALYZER.analyze(partial, exs).infeasible, (prog, p, q)


def test_parity_contradiction_is_pruned() -> None:
    partial = Op("bvmul", (Hole("S"), c(2)))
    assert ANALYZER.analyze(partial, (Example({"x": 1}, 3),)).infeasible
    assert not ANALYZER.analyze(partial, (Example({"x": 1}, 2),)).infeasible


def test_hole_precondition_is_exact_for_add() -> None:
    partial = Op("bvadd", (Hole("S"), c(1)))
    res = ANALYZER.analyze(partial, (Example({"x": 0}, 5),))
    pres = res.preconditions[(0,)]
    assert isinstance(pres, tuple)
    (pre,) = pres
    assert isinstance(pre, BV) and [v for v in range(8) if pre.contains(v)] == [4]


def test_backward_chains_through_nested_ops() -> None:
    partial = Op("bvadd", (Op("bvadd", (Hole("S"), c(1))), c(1)))
    states = analyze_underlying(D, partial, {"x": 0}, 5)
    assert states[(0, 0)] == alpha(W, 3)
    assert states[()] == alpha(W, 5)


def test_analysis_terminates_with_unconstrained_holes() -> None:
    states = analyze_underlying(D, Op("bvadd", (Hole("S"), Hole("S"))), {"x": 0}, 5)
    assert states[()] == alpha(W, 5)
    assert states[(0,)] == states[(1,)] == D.forward("bvsub", [alpha(W, 5), D.top()])


def test_compatible_filters_components() -> None:
    partial = Op("bvadd", (Hole("S"), c(1)))
    exs = (Example({"x": 3}, 4),)
    res = ANALYZER.analyze(partial, exs)
    assert ANALYZER.compatible(res, partial, (0,), c(3), exs)
    assert not ANALYZER.compatible(res, partial, (0,), c(5), exs)
    assert ANALYZER.compatible(res, partial, (0,), Var("x"), exs)


def test_compatible_accepts_partial_component() -> None:
    partial = Op("bvadd", (Hole("S"), c(1)))
    exs = (Example({"x": 3}, 4),)
    res = ANALYZER.analyze(partial, exs)
    assert ANALYZER.compatible(res, partial, (0,), Op("bvadd", (Hole("S"), Hole("S"))), exs)


def test_top_is_unconstrained() -> None:
    assert top(W) == D.top()


GRAMS = [
    ("bvadd", "bvmul"),
    ("bvand", "bvxor"),
    ("bvshl", "bvsub"),
    ("bvor", "bvlshr"),
]


@pytest.mark.parametrize("ops", GRAMS)
def test_pruned_search_keeps_every_solution_found_without_pruning(ops: tuple[str, str]) -> None:
    w = 2
    g = Grammar(
        (
            Production("S", Var("x")),
            Production("S", Const(1, "bv")),
            Production("S", Const(2, "bv")),
            *(Production("S", op, ("S", "S")) for op in ops),
        ),
        "S",
    )
    for a, b in itertools.product(range(4), repeat=2):
        problem = Problem(g, (Example({"x": a}, b),), "bv", w)
        budget = Budget(300, None)
        plain = search(problem, NullAnalyzer(), LeftmostPolicy(), budget)
        pruned = search(problem, DomainAnalyzer(BitvectorDomain(w)), LeftmostPolicy(), budget)
        if plain.status == "solved":
            assert pruned.status == "solved", (ops, a, b)
        if pruned.program is not None:
            assert satisfies(pruned.program, problem.examples, w)


def test_component_values_are_computed_once() -> None:
    """The line-14 filter asks about the same complete components for every hole; the value is cached."""
    from hope_engine.concrete.verify import Example
    from hope_engine.domains.analysis import DomainAnalyzer
    from hope_engine.domains.bitvector.ops import BitvectorDomain
    from hope_engine.syntax.ast import Const, Hole, Op, Var

    class Counting(BitvectorDomain):
        calls = 0

        def forward(self, op, args):  # type: ignore[no-untyped-def]
            Counting.calls += 1
            return super().forward(op, args)

    analyzer = DomainAnalyzer(Counting(4))
    exs = (Example({"x": 3}, 5),)
    partial = Op("bvadd", (Hole("S"), Const(1, "bv")))
    res = analyzer.analyze(partial, exs)
    comp = Op("bvadd", (Var("x"), Const(1, "bv")))
    first = analyzer.compatible(res, partial, (0,), comp, exs)
    before = Counting.calls
    again = analyzer.compatible(res, partial, (0,), comp, exs)
    assert first == again and Counting.calls == before
