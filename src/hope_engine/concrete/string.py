"""Exact string semantics (SMT-LIB strings). Values are str or int; out-of-range accesses give ""."""

from __future__ import annotations

from collections.abc import Callable, Mapping

from hope_engine.concrete.bitvector import UnsupportedOperator
from hope_engine.syntax.ast import Const, Hole, Node, Var

Value = str | int


def _str(v: Value) -> str:
    if not isinstance(v, str):
        raise TypeError(f"expected string, got {v!r}")
    return v


def _int(v: Value) -> int:
    if isinstance(v, bool) or not isinstance(v, int):
        raise TypeError(f"expected int, got {v!r}")
    return v


def _at(s: Value, i: Value) -> Value:
    a, k = _str(s), _int(i)
    return a[k] if 0 <= k < len(a) else ""


def _substr(s: Value, i: Value, n: Value) -> Value:
    a, k, m = _str(s), _int(i), _int(n)
    return "" if k < 0 or k >= len(a) or m <= 0 else a[k : k + m]


def _indexof(s: Value, t: Value, i: Value) -> Value:
    a, b, k = _str(s), _str(t), _int(i)
    return -1 if k < 0 or k > len(a) else a.find(b, k)


def _to_int(s: Value) -> Value:
    a = _str(s)
    return int(a) if a.isascii() and a.isdigit() else -1


def _replace(s: Value, t: Value, u: Value) -> Value:
    a, b, c = _str(s), _str(t), _str(u)
    return c + a if b == "" else a.replace(b, c, 1)


def _concat(*args: Value) -> Value:
    return "".join(_str(a) for a in args)


# name -> (min arity, max arity or None for variadic, function)
OPS: dict[str, tuple[int, int | None, Callable[..., Value]]] = {
    "str.++": (2, None, _concat),
    "ConCat": (2, None, _concat),
    "str.at": (2, 2, _at),
    "CharAt0": (1, 1, lambda s: _at(s, 0)),
    "str.substr": (3, 3, _substr),
    "str.indexof": (3, 3, _indexof),
    "str.len": (1, 1, lambda s: len(_str(s))),
    "str.to.int": (1, 1, _to_int),
    "int.to.str": (1, 1, lambda n: str(_int(n)) if _int(n) >= 0 else ""),
    "str.replace": (3, 3, _replace),
}


def eval_str(node: Node, env: Mapping[str, Value]) -> Value:
    """Evaluate a complete string/int program. Raises UnsupportedOperator, TypeError, ValueError (holes)."""
    if isinstance(node, Const):
        return node.value
    if isinstance(node, Var):
        return env[node.name]
    if isinstance(node, Hole):
        raise ValueError("cannot evaluate a partial program")  # noqa: TRY004
    spec = OPS.get(node.name)
    if spec is None or len(node.args) < spec[0] or (spec[1] is not None and len(node.args) > spec[1]):
        raise UnsupportedOperator(f"{node.name}/{len(node.args)}")
    return spec[2](*(eval_str(a, env) for a in node.args))
