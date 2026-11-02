"""Reference-function specs: `(define-fun spec ...)` plus `(constraint (= (spec x) (f x)))`.

The reference function is read as an SMT-LIB bitvector term and handled by Z3, so that
(1) example inputs can be sampled from it and (2) a candidate can be checked for equivalence over all
inputs. Used only for such problems; example-based problems never touch Z3.

[ponytail: Z3 is the verifier here; the search itself never calls it.]
"""

from __future__ import annotations

import random
from collections.abc import Callable
from typing import Any

import z3

from hope_engine.concrete.bitvector import BOOL_OPS, UnsupportedOperator
from hope_engine.concrete.verify import Example
from hope_engine.syntax.ast import Const, Hole, Node, Var

SOLVER_TIMEOUT_MS = 10_000
SAMPLES = 8

_BIN: dict[str, Callable[[Any, Any], Any]] = {
    "bvand": lambda a, b: a & b,
    "bvor": lambda a, b: a | b,
    "bvxor": lambda a, b: a ^ b,
    "bvadd": lambda a, b: a + b,
    "bvsub": lambda a, b: a - b,
    "bvmul": lambda a, b: a * b,
    "bvudiv": z3.UDiv,
    "bvurem": z3.URem,
    "bvsdiv": lambda a, b: a / b,
    "bvsrem": z3.SRem,
    "bvshl": lambda a, b: a << b,
    "bvlshr": z3.LShR,
    "bvashr": lambda a, b: a >> b,
}
_CMP: dict[str, Callable[[Any, Any], Any]] = {
    "bvult": z3.ULT,
    "bvule": z3.ULE,
    "bvugt": z3.UGT,
    "bvuge": z3.UGE,
    "bvslt": lambda a, b: a < b,
    "bvsle": lambda a, b: a <= b,
    "bvsgt": lambda a, b: a > b,
    "bvsge": lambda a, b: a >= b,
    "=": lambda a, b: a == b,
}


def term(program: Node, env: dict[str, Any], width: int) -> Any:
    """Z3 value of one of our programs; Booleans are the bitvector values 0 and 1."""
    one, zero = z3.BitVecVal(1, width), z3.BitVecVal(0, width)
    if isinstance(program, Const):
        assert isinstance(program.value, int)
        return z3.BitVecVal(program.value, width)
    if isinstance(program, Var):
        return env[program.name]
    if isinstance(program, Hole):
        raise ValueError("cannot verify a partial program")  # noqa: TRY004
    a = [term(x, env, width) for x in program.args]
    name = program.name
    if name == "bvnot" and len(a) == 1:
        return ~a[0]
    if name == "bvneg" and len(a) == 1:
        return -a[0]
    if name in _BIN and len(a) == 2:
        return _BIN[name](a[0], a[1])
    if name in BOOL_OPS and len(a) == BOOL_OPS[name][0]:
        if name == "=":
            return z3.If(a[0] == a[1], one, zero)
        if name == "not":
            return z3.If(a[0] == one, zero, one)
        if name == "and":
            return a[0] & a[1]
        if name == "or":
            return a[0] | a[1]
        return z3.If(a[0] == one, a[1], a[2])  # ite
    raise UnsupportedOperator(f"{name}/{len(a)}")


class Spec:
    """Reference function of a synthesis problem, over `params` (the synthesized function's parameters)."""

    def __init__(self, params: tuple[str, ...], width: int, body: Any, vars_: dict[str, Any]) -> None:
        self.params, self.width, self._body, self._vars = params, width, body, vars_

    def output(self, inputs: dict[str, int]) -> int:
        sub = [(self._vars[p], z3.BitVecVal(inputs[p], self.width)) for p in self.params]
        return int(z3.simplify(z3.substitute(self._body, *sub)).as_long())

    def counterexample(self, program: Node) -> dict[str, int] | None:
        """An input where the program differs from the reference, or None if they are equivalent."""
        solver = z3.Solver()
        solver.set("timeout", SOLVER_TIMEOUT_MS)
        solver.add(term(program, self._vars, self.width) != self._body)
        verdict = solver.check()
        if verdict == z3.unsat:
            return None
        if verdict == z3.unknown:
            raise TimeoutError("equivalence check inconclusive")
        model = solver.model()
        return {p: int(model.eval(self._vars[p], model_completion=True).as_long()) for p in self.params}

    def sample(self, count: int = SAMPLES, seed: int = 0) -> tuple[Example, ...]:
        """Corner inputs plus seeded random ones, with outputs from the reference function."""
        top = (1 << self.width) - 1
        rng = random.Random(seed)
        corners = [0, 1, top, 1 << (self.width - 1), top - 1]
        rows = [{p: c for p in self.params} for c in corners]
        rows += [{p: rng.randint(0, top) for p in self.params} for _ in range(count)]
        return tuple(Example(dict(r), self.output(r)) for r in rows)


def sexpr_to_z3(x: Any, env: dict[str, Any], width: int, pos: Callable[[Any], str]) -> Any:
    """Convert a parsed SMT-LIB term (parser.Atom / parser.SList) to Z3."""
    items = getattr(x, "items", None)
    if items is None:
        text = x.tok.text
        if text in env:
            return env[text]
        if text.startswith("#x"):
            return z3.BitVecVal(int(text.replace("#x", "0x"), 0), 4 * (len(text) - 2))
        if text.startswith("#b"):
            return z3.BitVecVal(int(text.replace("#b", "0b"), 0), len(text) - 2)
        raise UnsupportedOperator(f"{text} at {pos(x)}")
    head = items[0].tok.text if items and getattr(items[0], "items", None) is None else ""
    args = [sexpr_to_z3(i, env, width, pos) for i in items[1:]]
    if head == "bvnot" and len(args) == 1:
        return ~args[0]
    if head == "bvneg" and len(args) == 1:
        return -args[0]
    if head in _BIN and len(args) == 2:
        return _BIN[head](args[0], args[1])
    if head in _CMP and len(args) == 2:
        return _CMP[head](args[0], args[1])
    if head == "not" and len(args) == 1:
        return z3.Not(args[0])
    if head in ("and", "or") and args:
        return (z3.And if head == "and" else z3.Or)(*args)
    if head == "ite" and len(args) == 3:
        return z3.If(args[0], args[1], args[2])
    raise UnsupportedOperator(f"{head or '?'} at {pos(x)}")
