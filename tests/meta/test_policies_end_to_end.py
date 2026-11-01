import pytest

from hope_engine.concrete.verify import Example, satisfies
from hope_engine.domains.analysis import DomainAnalyzer
from hope_engine.domains.bitvector.ops import BitvectorDomain
from hope_engine.enumeration.search import (
    Budget,
    HolePolicy,
    LeftmostPolicy,
    Problem,
    search,
)
from hope_engine.meta.bitvector import BitvectorMeta
from hope_engine.meta.policies import HopePolicy, MetaOffPolicy
from hope_engine.syntax.ast import Const, Var
from hope_engine.syntax.grammar import Grammar, Production

W = 4
G = Grammar(
    (
        Production("S", Var("x")),
        Production("S", Const(1, "bv")),
        Production("S", Const(2, "bv")),
        Production("S", "bvadd", ("S", "S")),
        Production("S", "bvxor", ("S", "S")),
        Production("S", "bvshl", ("S", "S")),
    ),
    "S",
)
EXAMPLES = (Example({"x": 3}, 7), Example({"x": 5}, 11), Example({"x": 0}, 1))


@pytest.mark.parametrize("name", ["leftmost", "hope", "meta_off"])
def test_every_policy_solves_with_pruning(name: str) -> None:
    policies: dict[str, HolePolicy] = {
        "leftmost": LeftmostPolicy(),
        "hope": HopePolicy(BitvectorMeta(), seed=0),
        "meta_off": MetaOffPolicy(seed=0),
    }
    policy = policies[name]
    problem = Problem(G, EXAMPLES, "bv", W)
    r = search(problem, DomainAnalyzer(BitvectorDomain(W)), policy, Budget(20000, 60.0))
    assert r.status == "solved" and r.program is not None
    assert satisfies(r.program, EXAMPLES, W)
