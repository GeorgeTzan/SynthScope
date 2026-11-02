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


V2 = """(set-logic BV)
(synth-fun f ((x (_ BitVec 4))) (_ BitVec 4)
  ((Start (_ BitVec 4)))
  ((Start (_ BitVec 4) (x #x1 (bvadd Start Start)))))
(constraint (= (f #x3) #x4))
"""


def test_sygus_v2_grammar_with_predeclaration() -> None:
    p = parse_sygus(V2)
    assert p.grammar.start == "Start" and p.width == 4
    assert {x.label for x in p.grammar.productions_for("Start")} >= {Var("x"), "bvadd"}


@pytest.mark.parametrize(
    "text",
    [
        "(synth-fun f ((x (_ BitVec n))) (BitVec 4) ((Start (BitVec 4) (x))))\n(constraint (= (f #x1) #x2))",
        "(synth-fun f ((x (BitVec 4))) (BitVec 4) ())\n(constraint (= (f #x1) #x2))",
        "(synth-fun f ((x (BitVec 4))) (BitVec 4) ((Start (BitVec 4) (x)))\n(constraint (= (f #x1) #x2))",
    ],
)
def test_bad_input_is_always_a_sygus_error(text: str) -> None:
    with pytest.raises(SygusError):
        parse_sygus(text)


def test_mixed_bitvector_widths_are_rejected() -> None:
    text = (
        "(synth-fun f ((x (BitVec 4))) (BitVec 8) ((Start (BitVec 8) (x))))\n"
        "(constraint (= (f #x1) #x02))"
    )
    with pytest.raises(SygusError, match="width"):
        parse_sygus(text)


COND = """(set-logic BV)
(synth-fun f ((x (BitVec 8))) (BitVec 8)
  ((Start (BitVec 8) (x #x00 #x01 (bvadd Start Start) (bvsrem Start Start) (ite StartBool Start Start)))
   (StartBool Bool (true false (= Start Start) (not StartBool) (and StartBool StartBool) (or StartBool StartBool)))))
(constraint (= (f #x04) #x05))
(constraint (= (f #x07) #x00))
"""


def test_conditional_bitvector_grammar_parses() -> None:
    p = parse_sygus(COND)
    assert {x.label for x in p.grammar.productions_for("Start")} >= {"ite", "bvsrem"}
    assert {x.label for x in p.grammar.productions_for("StartBool")} >= {"=", "not", "and", "or"}
    assert Const(1, "bv") in {x.label for x in p.grammar.productions_for("StartBool")}


CHAIN = """(set-logic BV)
(synth-fun f ((x (BitVec 4))) (BitVec 4)
  ((Start (BitVec 4) (B)) (B (BitVec 4) (x (bvnot B)))))
(constraint (= (f #x1) #xe))
"""


def test_chain_rules_are_inlined() -> None:
    p = parse_sygus(CHAIN)
    assert {x.label for x in p.grammar.productions_for("Start")} == {Var("x"), "bvnot"}
    assert next(x for x in p.grammar.productions_for("Start") if x.label == "bvnot").rhs == ("B",)


def test_cyclic_chain_rules_terminate() -> None:
    text = "(synth-fun f ((x (BitVec 4))) (BitVec 4) ((A (BitVec 4) (B x)) (B (BitVec 4) (A))))\n(constraint (= (f #x1) #x1))"
    p = parse_sygus(text)
    assert {x.label for x in p.grammar.productions_for("A")} == {Var("x")}


BOOL_RET = """(set-logic SLIA)
(synth-fun f ((s String)) Bool
  ((Start Bool ((str.prefixof Str Str) (= Num Num)))
   (Str String (s "a")) (Num Int (0 (str.len Str)))))
(constraint (= (f "ab") true))
(constraint (= (f "ba") false))
"""


def test_bool_returning_string_function() -> None:
    p = parse_sygus(BOOL_RET)
    assert p.domain == "str"
    assert [e.output for e in p.examples] == [1, 0]
    r = search(p, DomainAnalyzer(StringDomain()), LeftmostPolicy(), Budget(5000, None))
    assert r.status == "solved" and r.program is not None
    assert satisfies(r.program, p.examples, None)
