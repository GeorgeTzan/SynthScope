from hope_engine.concrete.verify import Example, satisfies
from hope_engine.enumeration.search import (
    Budget,
    LeftmostPolicy,
    NullAnalyzer,
    Problem,
    search,
)
from hope_engine.syntax.ast import Const, Var
from hope_engine.syntax.grammar import Grammar, Production
from hope_engine.trace.events import Event

REC = Grammar(
    (
        Production("S", Var("x")),
        Production("S", Const(1, "bv")),
        Production("S", "bvadd", ("S", "S")),
    ),
    "S",
)


def run(g: Grammar, exs: tuple[Example, ...], budget: Budget | None = None, sink=None):  # type: ignore[no-untyped-def]
    p = Problem(g, exs, "bv", 4)
    return p, search(p, NullAnalyzer(), LeftmostPolicy(), budget or Budget(2000, None), sink)


def test_search_finds_known_solution() -> None:
    exs = (Example({"x": 3}, 4), Example({"x": 7}, 8))
    _, r = run(REC, exs)
    assert r.status == "solved" and r.program is not None
    assert satisfies(r.program, exs, 4)


def test_search_is_deterministic() -> None:
    exs = (Example({"x": 3}, 4),)
    assert run(REC, exs)[1].program == run(REC, exs)[1].program


def test_exhausted_not_unsat() -> None:
    g = Grammar((Production("S", Var("x")), Production("S", Const(1, "bv"))), "S")
    _, r = run(g, (Example({"x": 3}, 9),))
    assert r.status == "exhausted" and r.program is None


def test_leaf_only_grammar_solves() -> None:
    g = Grammar((Production("S", Var("x")),), "S")
    _, r = run(g, (Example({"x": 2}, 2),))
    assert r.status == "solved" and r.program == Var("x")


def test_nonterminal_without_productions() -> None:
    g = Grammar((Production("S", "bvadd", ("S", "T")), Production("S", Var("x"))), "S")
    _, r = run(g, (Example({"x": 3}, 9),))
    assert r.status == "exhausted"


def test_node_budget_stops_infinite_grammar() -> None:
    _, r = run(REC, (Example({"x": 3}, 0),), Budget(50, None))
    assert r.status == "exhausted" and r.nodes == 50


def test_timeout_status() -> None:
    _, r = run(REC, (Example({"x": 3}, 0),), Budget(10**9, 0.0))
    assert r.status == "timeout"


def test_unsupported_operator_status() -> None:
    g = Grammar((Production("S", Var("x")), Production("S", "bvcomp", ("S", "S"))), "S")
    _, r = run(g, (Example({"x": 3}, 9),))
    assert r.status == "unsupported"


def test_events_off_by_default() -> None:
    _, r = run(REC, (Example({"x": 3}, 4),))
    assert r.status == "solved"


def test_events_monotonic_seq() -> None:
    got: list[Event] = []
    _, r = run(REC, (Example({"x": 3}, 4),), sink=got.append)
    assert [e.seq for e in got] == list(range(len(got)))
    assert got[0].kind == "search_started" and got[-1].kind == "run_finished"
    assert "solution_found" in {e.kind for e in got}
    assert r.status == "solved"
