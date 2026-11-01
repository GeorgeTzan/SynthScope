import random

import pytest

from hope_engine.concrete.verify import Example, satisfies
from hope_engine.domains.analysis import DomainAnalyzer
from hope_engine.domains.string.lattice import TOP, TOP_INT, TOP_STR
from hope_engine.domains.string.ops import StringDomain
from hope_engine.enumeration.components import ComponentMap, add_components
from hope_engine.enumeration.search import Budget, Problem, search
from hope_engine.meta.analysis import meta_analyze
from hope_engine.meta.lattice import Meta
from hope_engine.meta.policies import HopePolicy
from hope_engine.meta.rank import may_infeasible, may_prune_components, rank_holes
from hope_engine.meta.string import SM, StringMeta
from hope_engine.syntax.ast import (
    Const,
    Hole,
    Node,
    Op,
    Var,
    holes,
    replace_at,
    subterm,
)
from hope_engine.syntax.grammar import Grammar, Production

D = StringMeta()
MUST, MAY = Meta.MUST_TOP, Meta.MAY_NOT_TOP


def test_predicates_and_join() -> None:
    assert D.is_must(D.must()) and not D.is_may(D.must())
    assert D.is_may(D.may()) and not D.is_must(D.may())
    assert D.join(D.must(), D.may()) == D.may()
    assert D.join(D.bottom(), D.must()) == D.must()
    assert D.join(D.must(), D.must()) == D.must()
    partial = SM(MUST, MAY, MUST, MUST)
    assert D.is_may(partial) and not D.is_must(partial)


def test_concat_of_top_values_is_top() -> None:
    assert D.forward("str.++", [D.must(), D.must()]) == D.must()


def test_concat_with_known_value_is_not_top() -> None:
    assert D.is_may(D.forward("str.++", [D.const(), D.must()]))
    assert D.is_may(D.forward("str.++", [D.must(), D.const()]))


def test_backward_of_top_result_is_top() -> None:
    assert D.backward("str.++", D.must(), [D.must(), D.must()], 0) == D.must()
    assert D.is_may(D.backward("str.++", D.may(), [D.must(), D.must()], 0))


G = Grammar(
    (
        Production("S", Var("x")),
        Production("S", Const("a", "str")),
        Production("S", Const("b", "str")),
        Production("S", "ConCat", ("S", "S")),
        Production("S", "CharAt0", ("S",)),
        Production("S", "str.at", ("S", "I")),
        Production("S", "str.substr", ("S", "I", "I")),
        Production("S", "int.to.str", ("I",)),
        Production("I", Const(0, "int")),
        Production("I", Const(1, "int")),
        Production("I", "str.len", ("S",)),
        Production("I", "str.indexof", ("S", "S", "I")),
        Production("I", "str.to.int", ("S",)),
    ),
    "S",
)
CM = ComponentMap()
add_components(G, CM, 3)
FILLS = {nt: random.Random(5).sample(list(CM.get(nt)), min(20, len(CM.get(nt)))) for nt in ("S", "I")}
UNDER = DomainAnalyzer(StringDomain())
TOPS = (TOP, TOP_STR, TOP_INT)
EXAMPLES = [(Example({"x": x}, y),) for x in ("", "ab", "b") for y in ("", "a", "ab", "ba")][::2]


def random_partial(rng: random.Random) -> Node:
    prog: Node = rng.choice([c for c in CM.get("S") if isinstance(c, Op)])
    spots: list[tuple[int, ...]] = []

    def walk(n: Node, p: tuple[int, ...]) -> None:
        spots.append(p)
        if isinstance(n, Op):
            for i, a in enumerate(n.args):
                walk(a, (*p, i))

    walk(prog, ())
    for p in rng.sample(spots, k=min(len(spots), rng.randint(1, 3))):
        try:
            sub = subterm(prog, p)
        except IndexError:
            continue
        nt = "I" if isinstance(sub, Op) and sub.name in ("str.len", "str.indexof", "str.to.int") else "S"
        if isinstance(sub, Const) and sub.type == "int":
            nt = "I"
        prog = replace_at(prog, p, Hole(nt))
    return prog


def partials(n: int) -> list[Node]:
    rng = random.Random(17)
    out: list[Node] = []
    while len(out) < n:
        q = random_partial(rng)
        if holes(q):
            out.append(q)
    return out


@pytest.mark.parametrize("q", partials(40))
def test_string_meta_overapproximates_underlying_pruning(q: Node) -> None:
    hs = holes(q)
    for pos in hs:
        res = meta_analyze(D, q, (pos,))
        rank1 = may_infeasible(res, D)
        rank2 = may_prune_components(res, D, (pos,), hs)
        hole = subterm(q, pos)
        assert isinstance(hole, Hole)
        for c in FILLS[hole.nonterminal]:
            filled = replace_at(q, pos, c)
            for exs in EXAMPLES:
                try:
                    got = UNDER.analyze(filled, exs)
                except TypeError:
                    continue  # ill-typed random program
                if not rank1:
                    assert not got.infeasible, ("rank1 missed", q, pos, c, exs)
                if not rank1 and not rank2:
                    for h in holes(filled):
                        pre = got.preconditions[h]
                        assert isinstance(pre, tuple) and all(p in TOPS for p in pre), (q, pos, c, exs, h)


def test_hope_policy_solves_overview_problem() -> None:
    g = Grammar(
        (
            Production("S", Var("x")),
            Production("S", Var("y")),
            Production("S", Const(".", "str")),
            Production("S", "CharAt0", ("S",)),
            Production("S", "ConCat", ("S", "S", "S")),
        ),
        "S",
    )
    ex = (Example({"x": "Jan", "y": "Kotas"}, "J.K"),)
    r = search(Problem(g, ex, "str"), UNDER, HopePolicy(D, seed=0), Budget(5000, 60.0))
    assert r.status == "solved" and r.program is not None and satisfies(r.program, ex)
    assert rank_holes(Hole("S"), D).rank1 == ((),)
