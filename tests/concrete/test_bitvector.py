import itertools

import pytest
import z3

from hope_engine.concrete.bitvector import UnsupportedOperator, eval_bv
from hope_engine.concrete.verify import Example, satisfies
from hope_engine.syntax.ast import Const, Hole, Op, Var

UNARY = {
    "bvneg": lambda a: -a,
    "bvnot": lambda a: ~a,
}
BINARY = {
    "bvand": lambda a, b: a & b,
    "bvor": lambda a, b: a | b,
    "bvxor": lambda a, b: a ^ b,
    "bvadd": lambda a, b: a + b,
    "bvsub": lambda a, b: a - b,
    "bvmul": lambda a, b: a * b,
    "bvudiv": z3.UDiv,
    "bvurem": z3.URem,
    "bvsdiv": lambda a, b: a / b,
    "bvshl": lambda a, b: a << b,
    "bvlshr": z3.LShR,
    "bvashr": lambda a, b: a >> b,
}


def z3_value(expr: z3.BitVecRef) -> int:
    return int(z3.simplify(expr).as_long())


@pytest.mark.parametrize("width", [1, 2, 3, 4])
@pytest.mark.parametrize("op", sorted(UNARY))
def test_unary_matches_z3(op: str, width: int) -> None:
    for a in range(2**width):
        got = eval_bv(Op(op, (Var("x"),)), {"x": a}, width)
        assert got == z3_value(UNARY[op](z3.BitVecVal(a, width))), (op, a)


@pytest.mark.parametrize("width", [1, 2, 3, 4])
@pytest.mark.parametrize("op", sorted(BINARY))
def test_binary_matches_z3(op: str, width: int) -> None:
    for a, b in itertools.product(range(2**width), repeat=2):
        got = eval_bv(Op(op, (Var("x"), Var("y"))), {"x": a, "y": b}, width)
        want = z3_value(BINARY[op](z3.BitVecVal(a, width), z3.BitVecVal(b, width)))
        assert got == want, (op, a, b)


def test_constant_wraps_to_width() -> None:
    assert eval_bv(Const(17, "bv"), {}, 4) == 1


def test_unknown_operator_raises() -> None:
    with pytest.raises(UnsupportedOperator):
        eval_bv(Op("bvcomp", (Var("x"), Var("x"))), {"x": 1}, 4)


def test_hole_raises() -> None:
    with pytest.raises(ValueError):
        eval_bv(Hole("S"), {}, 4)


def test_satisfies_checks_all_examples() -> None:
    prog = Op("bvadd", (Var("x"), Const(1, "bv")))
    ok = (Example({"x": 3}, 4), Example({"x": 15}, 0))
    bad = (Example({"x": 3}, 4), Example({"x": 15}, 1))
    assert satisfies(prog, ok, 4)
    assert not satisfies(prog, bad, 4)
