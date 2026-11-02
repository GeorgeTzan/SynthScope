"""Specification-style SyGuS problems (Hacker's Delight): `(constraint (= (spec x) (f x)))`."""

import pytest

from hope_engine.bench.runner import RunConfig, run_problem
from hope_engine.concrete.bitvector import eval_bv
from hope_engine.sygus.parser import SygusError, parse_sygus
from hope_engine.syntax.ast import Const, Op, Var

HD = """(set-logic BV)
(define-fun hd01 ((x (BitVec 8))) (BitVec 8) (bvand x (bvsub x #x01)))
(synth-fun f ((x (BitVec 8))) (BitVec 8)
  ((Start (BitVec 8) ((bvand Start Start) (bvsub Start Start) (bvadd Start Start) x #x00 #x01))))
(declare-var x (BitVec 8))
(constraint (= (hd01 x) (f x)))
(check-synth)
"""

TWO = """(set-logic BV)
(define-fun avg ((x (BitVec 8)) (y (BitVec 8))) (BitVec 8) (bvadd (bvand x y) (bvlshr (bvxor x y) #x01)))
(synth-fun f ((x (BitVec 8)) (y (BitVec 8))) (BitVec 8)
  ((Start (BitVec 8) ((bvand Start Start) (bvxor Start Start) (bvadd Start Start) (bvlshr Start Start) x y #x01))))
(declare-var x (BitVec 8))
(declare-var y (BitVec 8))
(constraint (= (avg x y) (f x y)))
"""


def test_examples_are_sampled_from_the_reference_function() -> None:
    p = parse_sygus(HD)
    assert p.spec is not None and len(p.examples) >= 6
    for ex in p.examples:
        x = int(ex.inputs["x"])
        assert ex.output == x & ((x - 1) % 256)
    assert {0, 255} <= {ex.inputs["x"] for ex in p.examples}


def test_oracle_accepts_the_reference_and_rejects_a_near_miss() -> None:
    p = parse_sygus(HD)
    assert p.spec is not None
    x = Var("x")
    good = Op("bvand", (x, Op("bvsub", (x, Const(1, "bv")))))
    assert p.spec.counterexample(good) is None
    bad = Op("bvand", (x, Op("bvadd", (x, Const(1, "bv")))))
    cex = p.spec.counterexample(bad)
    assert cex is not None
    v = cex["x"]
    assert eval_bv(bad, {"x": v}, 8) != p.spec.output(cex)


def test_two_variable_spec_and_argument_order() -> None:
    p = parse_sygus(TWO)
    assert p.spec is not None
    for ex in p.examples:
        x, y = int(ex.inputs["x"]), int(ex.inputs["y"])
        assert ex.output == ((x & y) + ((x ^ y) >> 1)) % 256


def test_spec_problem_is_solved_with_verification() -> None:
    p = parse_sygus(HD)
    r = run_problem(p, "hd01", RunConfig("hope", 2, 50_000, 30.0, 0))
    assert r.status == "solved" and r.validated and r.program is not None


def test_mixing_spec_and_example_constraints_is_rejected() -> None:
    with pytest.raises(SygusError, match="mix"):
        parse_sygus(HD + "(constraint (= (f #x01) #x00))")


def test_unknown_spec_operator_is_unsupported() -> None:
    from hope_engine.concrete.bitvector import UnsupportedOperator

    with pytest.raises(UnsupportedOperator):
        parse_sygus(HD.replace("(bvand x (bvsub x #x01))", "(bvredor x)"))
