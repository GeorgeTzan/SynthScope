import pytest

from hope_engine.syntax.ast import Const, Hole, Op, Var
from hope_engine.syntax.grammar import Grammar, GrammarError, Production, validate

G = Grammar(
    productions=(
        Production("S", Var("x")),
        Production("S", Const(1, "bv")),
        Production("S", "bvadd", ("S", "S")),
        Production("S", "bvnot", ("S",)),
    ),
    start="S",
)


def test_productions_for() -> None:
    assert len(G.productions_for("S")) == 4
    assert G.productions_for("T") == ()


def test_validate_accepts_complete_program() -> None:
    validate(Op("bvadd", (Var("x"), Const(1, "bv"))), G)


def test_validate_accepts_partial() -> None:
    validate(Op("bvadd", (Hole("S"), Var("x"))), G)


def test_validate_rejects_wrong_arity() -> None:
    with pytest.raises(GrammarError):
        validate(Op("bvnot", (Var("x"), Var("x"))), G)


def test_validate_rejects_unknown_operator() -> None:
    with pytest.raises(GrammarError):
        validate(Op("bvmul", (Var("x"), Var("x"))), G)


def test_validate_rejects_unknown_nonterminal_hole() -> None:
    with pytest.raises(GrammarError):
        validate(Hole("T"), G)
