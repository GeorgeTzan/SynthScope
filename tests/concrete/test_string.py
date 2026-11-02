import pytest
import z3
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from hope_engine.concrete.bitvector import UnsupportedOperator
from hope_engine.concrete.string import eval_str
from hope_engine.concrete.verify import Example, satisfies
from hope_engine.syntax.ast import Const, Hole, Node, Op, Var


def s(v: str) -> Const:
    return Const(v, "str")


def i(v: int) -> Const:
    return Const(v, "int")


def run(op: str, *args: Node) -> str | int:
    return eval_str(Op(op, tuple(args)), {})


@pytest.mark.parametrize(
    ("node", "want"),
    [
        (Op("str.at", (s(""), i(0))), ""),
        (Op("str.at", (s("abc"), i(-1))), ""),
        (Op("str.at", (s("abc"), i(3))), ""),
        (Op("str.at", (s("abc"), i(1))), "b"),
        (Op("str.substr", (s("abc"), i(2), i(5))), "c"),
        (Op("str.substr", (s("abc"), i(-1), i(2))), ""),
        (Op("str.substr", (s("abc"), i(1), i(0))), ""),
        (Op("str.substr", (s("abc"), i(3), i(1))), ""),
        (Op("str.indexof", (s("abc"), s(""), i(1))), 1),
        (Op("str.indexof", (s("abc"), s(""), i(4))), -1),
        (Op("str.indexof", (s("abcb"), s("b"), i(2))), 3),
        (Op("str.indexof", (s("abc"), s("z"), i(0))), -1),
        (Op("str.to.int", (s(""),)), -1),
        (Op("str.to.int", (s("12a"),)), -1),
        (Op("str.to.int", (s("0042"),)), 42),
        (Op("int.to.str", (i(-3),)), ""),
        (Op("int.to.str", (i(0),)), "0"),
        (Op("str.len", (s("héllo"),)), 5),
        (Op("str.++", (s("a"), s("b"), s("c"))), "abc"),
        (Op("ConCat", (s("J"), s("."), s("K"))), "J.K"),
        (Op("CharAt0", (s("Jan"),)), "J"),
        (Op("CharAt0", (s(""),)), ""),
        (Op("str.replace", (s("aXbX"), s("X"), s("-"))), "a-bX"),
        (Op("str.replace", (s("ab"), s(""), s("Z"))), "Zab"),
    ],
)
def test_edge_cases(node: Node, want: str | int) -> None:
    assert eval_str(node, {}) == want


def test_variables_and_paper_example() -> None:
    prog = Op("ConCat", (Op("CharAt0", (Var("x"),)), s("."), Op("CharAt0", (Var("y"),))))
    assert eval_str(prog, {"x": "Jan", "y": "Kotas"}) == "J.K"


def test_unknown_operator_raises() -> None:
    with pytest.raises(UnsupportedOperator):
        run("str.rev", s("a"))


def test_wrong_arity_or_type_raises() -> None:
    with pytest.raises(UnsupportedOperator):
        run("str.at", s("a"))
    with pytest.raises(TypeError):
        run("str.at", i(1), i(1))


def test_hole_raises() -> None:
    with pytest.raises(ValueError):
        eval_str(Hole("S"), {})


def test_satisfies_for_strings() -> None:
    prog = Op("ConCat", (Op("CharAt0", (Var("x"),)), s("."), Op("CharAt0", (Var("y"),))))
    ok = (Example({"x": "Jan", "y": "Kotas"}, "J.K"),)
    bad = (Example({"x": "Jan", "y": "Kotas"}, "J.k"),)
    assert satisfies(prog, ok)
    assert not satisfies(prog, bad)


TEXT = st.text(alphabet="ab", max_size=5)
IDX = st.integers(min_value=-2, max_value=7)
Z3_SETTINGS = settings(max_examples=120, deadline=None, suppress_health_check=[HealthCheck.too_slow])


def zs(v: str) -> z3.SeqRef:
    return z3.StringVal(v)


def zv(e: z3.ExprRef) -> str | int:
    e = z3.simplify(e)
    return e.as_string() if z3.is_string_value(e) else int(e.as_long())


@Z3_SETTINGS
@given(TEXT, IDX)
def test_at_matches_z3(a: str, k: int) -> None:
    assert run("str.at", s(a), i(k)) == zv(z3.SubString(zs(a), k, 1))


@Z3_SETTINGS
@given(TEXT, IDX, IDX)
def test_substr_matches_z3(a: str, k: int, n: int) -> None:
    assert run("str.substr", s(a), i(k), i(n)) == zv(z3.SubString(zs(a), k, n))


@Z3_SETTINGS
@given(TEXT, TEXT, IDX)
def test_indexof_matches_z3(a: str, b: str, k: int) -> None:
    assert run("str.indexof", s(a), s(b), i(k)) == zv(z3.IndexOf(zs(a), zs(b), k))


@Z3_SETTINGS
@given(st.text(alphabet="0123ab", max_size=5))
def test_to_int_matches_z3(a: str) -> None:
    assert run("str.to.int", s(a)) == zv(z3.StrToInt(zs(a)))


@Z3_SETTINGS
@given(st.integers(min_value=-5, max_value=120))
def test_int_to_str_matches_z3(n: int) -> None:
    assert run("int.to.str", i(n)) == zv(z3.IntToStr(z3.IntVal(n)))


@Z3_SETTINGS
@given(TEXT, TEXT, TEXT)
def test_replace_matches_z3(a: str, b: str, c: str) -> None:
    assert run("str.replace", s(a), s(b), s(c)) == zv(z3.Replace(zs(a), zs(b), zs(c)))


@Z3_SETTINGS
@given(TEXT, TEXT)
def test_concat_and_len_match_z3(a: str, b: str) -> None:
    assert run("str.++", s(a), s(b)) == zv(z3.Concat(zs(a), zs(b)))
    assert run("str.len", s(a)) == zv(z3.Length(zs(a)))


def test_arithmetic_comparison_and_conditional_ops() -> None:
    from hope_engine.syntax.ast import Const, Op, Var

    env: dict[str, str | int] = {"s": "abc", "n": 4}
    s, n = Var("s"), Var("n")
    assert eval_str(Op("+", (n, Const(2, "int"))), env) == 6
    assert eval_str(Op("-", (n, Const(5, "int"))), env) == -1
    assert eval_str(Op("str.prefixof", (Const("ab", "str"), s)), env) == 1
    assert eval_str(Op("str.prefixof", (Const("bc", "str"), s)), env) == 0
    assert eval_str(Op("str.suffixof", (Const("bc", "str"), s)), env) == 1
    assert eval_str(Op("str.contains", (s, Const("b", "str"))), env) == 1
    assert eval_str(Op("=", (n, Const(4, "int"))), env) == 1
    assert eval_str(Op("=", (s, Const("x", "str"))), env) == 0
    yes, no = Const(1, "int"), Const(0, "int")
    assert eval_str(Op("ite", (yes, s, Const("z", "str"))), env) == "abc"
    assert eval_str(Op("ite", (no, s, Const("z", "str"))), env) == "z"
