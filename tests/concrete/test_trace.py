from hope_engine.concrete.trace import node_values
from hope_engine.concrete.verify import Example
from hope_engine.syntax.ast import Const, Hole, Op, Var


def test_bitvector_values_at_every_node() -> None:
    prog = Op("bvmul", (Var("x"), Op("bvadd", (Var("x"), Const(1, "bv")))))
    out = node_values(prog, (Example({"x": 3}, 12), Example({"x": 255}, 0)), 8)
    assert out[0]["inputs"] == {"x": 3} and out[0]["expected"] == 12
    assert out[0]["values"] == {"": 12, "0": 3, "1": 4, "1.0": 3, "1.1": 1}
    assert out[1]["values"][""] == 0  # 255 * 0 wraps at 8 bits


def test_string_values_and_failing_nodes() -> None:
    prog = Op("str.++", (Op("str.at", (Var("s"), Const(0, "int"))), Const(".", "str")))
    out = node_values(prog, (Example({"s": "Jan"}, "J."),), None)
    assert out[0]["values"] == {"": "J.", "0": "J", "0.0": "Jan", "0.1": 0, "1": "."}


def test_partial_programs_report_no_value_for_nodes_over_holes() -> None:
    prog = Op("bvadd", (Var("x"), Hole("Start")))
    out = node_values(prog, (Example({"x": 3}, 5),), 8)
    assert out[0]["values"] == {"": None, "0": 3, "1": None}
