from pathlib import Path

import pytest

from hope_engine.concrete.bitvector import UnsupportedOperator
from hope_engine.concrete.verify import Example, satisfies
from hope_engine.domains.analysis import DomainAnalyzer
from hope_engine.domains.bitvector.ops import BitvectorDomain
from hope_engine.domains.string.ops import StringDomain
from hope_engine.enumeration.search import Budget, LeftmostPolicy, search
from hope_engine.sygus.parser import SygusError, load_problem, parse_sygus
from hope_engine.syntax.ast import Const, Var

FIX = Path(__file__).parent / "fixtures"


def test_parse_bv_fixture() -> None:
    p = load_problem(FIX / "bv.sl")
    assert p.domain == "bv" and p.width == 4
    assert p.examples == (Example({"x": 0b1011}, 0b1000), Example({"x": 0b0111}, 0))
    assert p.grammar.start == "Start"
    labels = {x.label for x in p.grammar.productions_for("Start")}
    assert Var("x") in labels and Const(1, "bv") in labels and "bvadd" in labels


def test_parse_string_fixture() -> None:
    p = load_problem(FIX / "string.sl")
    assert p.domain == "str" and p.width is None
    assert p.examples[0] == Example({"x": "Jan", "y": "Kotas"}, "J.K")
    assert p.examples[1].inputs["x"] == 'Ann "A"'
    assert Const(0, "int") in {x.label for x in p.grammar.productions_for("Idx")}
    assert any(x.rhs == ("Start", "Start", "Start") for x in p.grammar.productions_for("Start"))


def test_bv_fixture_is_solvable() -> None:
    p = load_problem(FIX / "bv.sl")
    r = search(p, DomainAnalyzer(BitvectorDomain(4)), LeftmostPolicy(), Budget(20000, 60.0))
    assert r.status == "solved" and r.program is not None
    assert satisfies(r.program, p.examples, 4)


def test_string_fixture_is_solvable() -> None:
    p = load_problem(FIX / "string.sl")
    r = search(p, DomainAnalyzer(StringDomain()), LeftmostPolicy(), Budget(20000, 60.0))
    assert r.status == "solved" and r.program is not None
    assert satisfies(r.program, p.examples)


def test_malformed_reports_line_and_column() -> None:
    with pytest.raises(SygusError) as e:
        parse_sygus("(set-logic BV)\n(synth-fun f ((x (BitVec 4))) (BitVec 4)\n  ((Start (BitVec 4) (x #q1))))\n")
    assert (e.value.line, e.value.col) == (3, 25)


def test_unbalanced_parenthesis() -> None:
    with pytest.raises(SygusError) as e:
        parse_sygus("(synth-fun f")
    assert e.value.line == 1


def test_unsupported_operator_is_unsupported_not_unsat() -> None:
    text = """(synth-fun f ((x (BitVec 4))) (BitVec 4) ((Start (BitVec 4) (x (bvcomp Start Start)))))
(constraint (= (f #x1) #x2))"""
    with pytest.raises(UnsupportedOperator):
        parse_sygus(text)


def test_missing_grammar_is_error() -> None:
    with pytest.raises(SygusError):
        parse_sygus("(synth-fun f ((x (BitVec 4))) (BitVec 4))\n(constraint (= (f #x1) #x2))")


def test_non_example_constraint_is_error() -> None:
    text = """(synth-fun f ((x (BitVec 4))) (BitVec 4) ((Start (BitVec 4) (x))))
(constraint (bvule (f #x1) #x2))"""
    with pytest.raises(SygusError):
        parse_sygus(text)
