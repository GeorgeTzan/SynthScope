"""Soundness of the meta analysis against our underlying analysis (paper Thm 4.2 / 4.4, tested)."""

import random

import pytest

from hope_engine.concrete.bitvector import BINARY, UNARY
from hope_engine.concrete.verify import Example
from hope_engine.domains.analysis import DomainAnalyzer
from hope_engine.domains.bitvector.ops import BitvectorDomain
from hope_engine.enumeration.components import ComponentMap, add_components
from hope_engine.meta.analysis import meta_analyze
from hope_engine.meta.bitvector import BitvectorMeta
from hope_engine.meta.rank import may_infeasible, may_prune_components
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

W = 2
OPS1 = sorted(UNARY)
OPS2 = sorted(BINARY)
G = Grammar(
    (
        Production("S", Var("x")),
        Production("S", Const(1, "bv")),
        Production("S", Const(2, "bv")),
        *(Production("S", o, ("S",)) for o in OPS1),
        *(Production("S", o, ("S", "S")) for o in OPS2),
    ),
    "S",
)
CM = ComponentMap()
add_components(G, CM, 3)
FILLS = random.Random(5).sample(CM.get("S"), 24)
ANALYZER = DomainAnalyzer(BitvectorDomain(W))
META = BitvectorMeta()


def random_partial(rng: random.Random) -> Node:
    comps = CM.get("S")
    base = rng.choice([c for c in comps if isinstance(c, Op)])
    prog: Node = (
        Op(base.name, tuple(rng.choice(comps) for _ in base.args)) if rng.random() < 0.5 else base
    )
    # grow once by wrapping, to get deeper trees
    if rng.random() < 0.5:
        op = rng.choice(OPS2)
        prog = Op(op, (prog, rng.choice(comps)))
    spots = []

    def walk(n: Node, p: tuple[int, ...]) -> None:
        spots.append(p)
        if isinstance(n, Op):
            for i, a in enumerate(n.args):
                walk(a, (*p, i))

    walk(prog, ())
    for p in rng.sample(spots, k=min(len(spots), rng.randint(1, 3))):
        try:
            sub = subterm(prog, p)
        except IndexError:  # an ancestor was already replaced by a hole
            continue
        if isinstance(sub, Op) or rng.random() < 0.7:
            prog = replace_at(prog, p, Hole("S"))
    return prog


def partials(n: int) -> list[Node]:
    rng = random.Random(11)
    out: list[Node] = []
    while len(out) < n:
        q = random_partial(rng)
        if holes(q):
            out.append(q)
    return out


EXAMPLES = [(Example({"x": x}, y),) for x in range(4) for y in range(4)][::3]


@pytest.mark.parametrize("q", partials(60))
def test_meta_overapproximates_underlying_pruning(q: Node) -> None:
    hs = holes(q)
    for pos in hs:
        res = meta_analyze(META, q, (pos,))
        rank1 = may_infeasible(res, META)
        rank2 = may_prune_components(res, META, (pos,), hs)
        for c in FILLS:
            filled = replace_at(q, pos, c)
            for exs in EXAMPLES:
                got = ANALYZER.analyze(filled, exs)
                if not rank1:
                    assert not got.infeasible, ("rank1 missed", q, pos, c, exs)
                if not rank1 and not rank2:
                    others = [h for h in holes(filled)]
                    for h in others:
                        pre = got.preconditions[h]
                        assert isinstance(pre, tuple)
                        assert all(p == ANALYZER.domain.top() for p in pre), ("rank2 missed", q, pos, c, exs, h)
