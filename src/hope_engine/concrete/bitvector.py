"""Exact fixed-width bitvector semantics (SMT-LIB v2.0). Values are unsigned ints in [0, 2**w)."""

from __future__ import annotations

from collections.abc import Callable

from hope_engine.syntax.ast import Const, Hole, Node, Var


class UnsupportedOperator(Exception):
    pass


def _signed(a: int, w: int) -> int:
    return a - (1 << w) if a >> (w - 1) else a


def _udiv(a: int, b: int, w: int) -> int:
    return (1 << w) - 1 if b == 0 else a // b


def _urem(a: int, b: int, w: int) -> int:
    return a if b == 0 else a % b


def _neg(a: int, w: int) -> int:
    return (-a) % (1 << w)


def _sdiv(a: int, b: int, w: int) -> int:
    an, bn = bool(a >> (w - 1)), bool(b >> (w - 1))
    ua, ub = (_neg(a, w) if an else a), (_neg(b, w) if bn else b)
    q = _udiv(ua, ub, w)
    return _neg(q, w) if an != bn else q


def _srem(a: int, b: int, w: int) -> int:
    """SMT-LIB bvsrem: the sign follows the dividend; remainder by zero is the dividend."""
    an, bn = bool(a >> (w - 1)), bool(b >> (w - 1))
    r = _urem(_neg(a, w) if an else a, _neg(b, w) if bn else b, w)
    return _neg(r, w) if an else r


def _ashr(a: int, b: int, w: int) -> int:
    return (_signed(a, w) >> min(b, w)) % (1 << w)


UNARY: dict[str, Callable[[int, int], int]] = {
    "bvneg": _neg,
    "bvnot": lambda a, w: ~a & ((1 << w) - 1),
}

BINARY: dict[str, Callable[[int, int, int], int]] = {
    "bvand": lambda a, b, w: a & b,
    "bvor": lambda a, b, w: a | b,
    "bvxor": lambda a, b, w: a ^ b,
    "bvadd": lambda a, b, w: (a + b) % (1 << w),
    "bvsub": lambda a, b, w: (a - b) % (1 << w),
    "bvmul": lambda a, b, w: (a * b) % (1 << w),
    "bvudiv": _udiv,
    "bvurem": _urem,
    "bvsdiv": _sdiv,
    "bvsrem": _srem,
    "bvshl": lambda a, b, w: (a << b) % (1 << w) if b < w else 0,
    "bvlshr": lambda a, b, w: a >> b if b < w else 0,
    "bvashr": _ashr,
}


# Booleans are the values 0 and 1 of the same width. name -> (arity, function on the argument values)
BOOL_OPS: dict[str, tuple[int, Callable[..., int]]] = {
    "not": (1, lambda a: 1 - a),
    "and": (2, lambda a, b: a & b),
    "or": (2, lambda a, b: a | b),
    "=": (2, lambda a, b: int(a == b)),
    "ite": (3, lambda c, a, b: a if c == 1 else b),
}


def eval_bv(node: Node, env: dict[str, int], width: int) -> int:
    """Evaluate a complete bitvector program. Raises UnsupportedOperator, ValueError on holes."""
    mask = (1 << width) - 1
    if isinstance(node, Const):
        assert isinstance(node.value, int)
        return node.value & mask
    if isinstance(node, Var):
        return env[node.name] & mask
    if isinstance(node, Hole):
        raise ValueError("cannot evaluate a partial program")  # noqa: TRY004
    args = [eval_bv(a, env, width) for a in node.args]
    if node.name in BOOL_OPS and len(args) == BOOL_OPS[node.name][0]:
        return BOOL_OPS[node.name][1](*args)
    if node.name in UNARY and len(args) == 1:
        return UNARY[node.name](args[0], width)
    if node.name in BINARY and len(args) == 2:
        return BINARY[node.name](args[0], args[1], width)
    raise UnsupportedOperator(f"{node.name}/{len(args)}")
