import pytest

from hope_engine.concrete.verify import Example, satisfies
from hope_engine.domains.analysis import DomainAnalyzer
from hope_engine.domains.string.lattice import contains
from hope_engine.domains.string.ops import StringDomain
from hope_engine.enumeration.search import Budget, LeftmostPolicy, Problem, search
from hope_engine.syntax.ast import Const, Hole, Op, Var, replace_at
from hope_engine.syntax.grammar import Grammar, Production

A = DomainAnalyzer(StringDomain())
EX = (Example({"x": "Jan", "y": "Kotas"}, "J.K"),)
H = Hole("S")
DOT = Const(".", "str")
FIRST_X = Op("CharAt0", (Var("x"),))
FIRST_Y = Op("CharAt0", (Var("y"),))
SOLUTION = Op("ConCat", (FIRST_X, DOT, FIRST_Y))


def test_paper_overview_candidates() -> None:
    assert A.analyze(Op("ConCat", (H, H, Const(" ", "str"))), EX).infeasible
    assert A.analyze(Op("ConCat", (Var("x"), H, H)), EX).infeasible
    assert not A.analyze(Op("ConCat", (FIRST_X, H, H)), EX).infeasible


@pytest.mark.parametrize("pos", [(), (0,), (1,), (2,), (0, 0), (2, 0)])
def test_known_solution_parts_never_pruned(pos: tuple[int, ...]) -> None:
    assert satisfies(SOLUTION, EX)
    partial = replace_at(SOLUTION, pos, H)
    assert not A.analyze(partial, EX).infeasible


def test_hole_precondition_is_exact() -> None:
    partial = Op("ConCat", (FIRST_X, DOT, H))
    res = A.analyze(partial, EX)
    pres = res.preconditions[(2,)]
    assert isinstance(pres, tuple)
    (pre,) = pres
    assert contains(pre, "K") and not contains(pre, "Z") and not contains(pre, "KK")


def test_search_solves_overview_problem_with_pruning() -> None:
    g = Grammar(
        (
            Production("S", Var("x")),
            Production("S", Var("y")),
            Production("S", DOT),
            Production("S", "CharAt0", ("S",)),
            Production("S", "ConCat", ("S", "S", "S")),
        ),
        "S",
    )
    r = search(Problem(g, EX, "str"), A, LeftmostPolicy(), Budget(5000, 60.0))
    assert r.status == "solved" and r.program is not None
    assert satisfies(r.program, EX)

