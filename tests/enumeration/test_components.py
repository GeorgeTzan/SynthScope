from hope_engine.enumeration.components import ComponentMap, add_components
from hope_engine.syntax.ast import Const, Var, size
from hope_engine.syntax.grammar import Grammar, Production

G = Grammar(
    (
        Production("S", Var("x")),
        Production("S", Const(1, "bv")),
        Production("S", "bvadd", ("S", "S")),
    ),
    "S",
)


def test_components_by_increasing_size() -> None:
    cm = ComponentMap()
    add_components(G, cm, 3)
    assert [size(n) for n in cm.get("S")] == [1, 1, 3, 3, 3, 3]


def test_add_components_is_incremental() -> None:
    cm = ComponentMap()
    add_components(G, cm, 3)
    add_components(G, cm, 3)
    assert len(cm.get("S")) == 6
    add_components(G, cm, 5)
    assert len(cm.get("S")) == 6 + 16


def test_unknown_nonterminal_has_no_components() -> None:
    assert ComponentMap().get("T") == ()


def test_components_are_deterministic() -> None:
    a, b = ComponentMap(), ComponentMap()
    add_components(G, a, 5)
    add_components(G, b, 5)
    assert a.get("S") == b.get("S")
