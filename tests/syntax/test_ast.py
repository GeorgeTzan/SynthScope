from hope_engine.syntax.ast import (
    Const,
    Hole,
    Op,
    Var,
    holes,
    replace_at,
    size,
    subterm,
)


def test_replace_at_root() -> None:
    assert replace_at(Hole("S"), (), Var("x")) == Var("x")


def test_replace_at_nested() -> None:
    p = Op("bvadd", (Hole("S"), Var("x")))
    assert replace_at(p, (0,), Var("x")) == Op("bvadd", (Var("x"), Var("x")))


def test_holes_left_to_right() -> None:
    p = Op("bvadd", (Hole("S"), Hole("S")))
    assert holes(p) == ((0,), (1,))


def test_holes_nested_order() -> None:
    p = Op("f", (Op("g", (Hole("A"), Const(1, "bv"))), Hole("B")))
    assert holes(p) == ((0, 0), (1,))


def test_holes_none_for_complete() -> None:
    assert holes(Op("bvnot", (Var("x"),))) == ()


def test_subterm_and_size() -> None:
    p = Op("bvadd", (Var("x"), Op("bvnot", (Var("x"),))))
    assert subterm(p, (1, 0)) == Var("x")
    assert size(p) == 4


def test_nodes_hashable() -> None:
    assert len({Var("x"), Var("x"), Hole("S")}) == 2


def test_pretty_sexpr() -> None:
    from hope_engine.syntax.ast import pretty

    p = Op("bvadd", (Hole("S"), Op("bvnot", (Var("x"),))))
    assert pretty(p) == "(bvadd □:S (bvnot x))"
    assert pretty(Const(1, "bv")) == "1"
    assert pretty(Const("a b", "str")) == '"a b"'


def test_pretty_escapes_quotes_in_string_constants() -> None:
    from hope_engine.syntax.ast import pretty

    assert pretty(Const('a"b', "str")) == '"a""b"'
