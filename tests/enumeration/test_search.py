from typing import cast

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


def test_ill_typed_string_grammar_is_unsupported_not_a_crash() -> None:
    g = Grammar(
        (
            Production("S", Var("x")),
            Production("S", "str.++", ("S", "I")),  # int where a string belongs
            Production("I", Const(0, "int")),
        ),
        "S",
    )
    p = Problem(g, (Example({"x": "ab"}, "abab"),), "str", None)
    r = search(p, NullAnalyzer(), LeftmostPolicy(), Budget(2000, None))
    assert r.status == "unsupported"


def test_events_carry_time_and_a_parent_chain() -> None:
    got: list[Event] = []
    _, r = run(REC, (Example({"x": 3}, 4),), sink=got.append)
    assert r.status == "solved"
    assert all(e.t >= 0 for e in got) and [e.t for e in got] == sorted(e.t for e in got)
    expanded = [e.payload for e in got if e.kind == "candidate_expanded"]
    assert expanded[0]["parent"] is None and expanded[0]["id"] == 0
    ids = {p["id"] for p in expanded}
    assert all(p["parent"] in ids for p in expanded[1:])
    assert len(ids) == len(expanded)


def test_analysis_event_describes_node_states() -> None:
    from hope_engine.domains.analysis import DomainAnalyzer
    from hope_engine.domains.bitvector.ops import BitvectorDomain

    got: list[Event] = []
    p = Problem(REC, (Example({"x": 3}, 4),), "bv", 4)
    search(p, DomainAnalyzer(BitvectorDomain(4)), LeftmostPolicy(), Budget(200, None), got.append)
    analysis = [e.payload for e in got if e.kind == "analysis"]
    assert analysis, "the analyzer describes its states"
    first = analysis[0]
    assert first["inputs"] == {"x": 3} and first["output"] == 4
    nodes = cast("list[dict[str, object]]", first["nodes"])
    assert nodes[0]["path"] == [] and nodes[0]["state"] == "#x4"  # the root hole is refined to the output
    assert {"path", "label", "state"} <= set(nodes[0])


def test_null_analyzer_emits_no_analysis_events() -> None:
    got: list[Event] = []
    run(REC, (Example({"x": 3}, 4),), sink=got.append)
    assert not any(e.kind == "analysis" for e in got)
