"""Bitvector meta operators (paper Figs 1 and 2).

Listed in the paper: forward for neg/not, and/or/mul/sdiv/lshr/shl, xor/add/sub; backward for
and/or and xor/add/sub. Not listed (udiv, ashr, urem, mul/shift/div backward, ...): the safe default
MAY_NOT_TOP, which only ever claims "pruning is possible", never "impossible".
"""

from __future__ import annotations

from collections.abc import Sequence

from hope_engine.meta.lattice import Meta

MAY, MUST, BOT = Meta.MAY_NOT_TOP, Meta.MUST_TOP, Meta.BOT

_UNARY = {"bvneg", "bvnot"}
_EITHER = {"bvand", "bvor", "bvmul", "bvsdiv", "bvlshr", "bvshl", "bvudiv", "bvashr"}
_BOTH = {"bvxor", "bvadd", "bvsub"}


class BitvectorMeta:
    def bottom(self) -> Meta:
        return BOT

    def must(self) -> Meta:
        return MUST

    def may(self) -> Meta:
        return MAY

    def join(self, a: Meta, b: Meta) -> Meta:
        return max(a, b)

    def is_may(self, a: Meta) -> bool:
        return a == MAY

    def is_must(self, a: Meta) -> bool:
        return a == MUST

    def forward(self, op: str, args: Sequence[Meta]) -> Meta:
        if op in _UNARY:
            return MAY if args[0] == MAY else MUST
        if op in _EITHER:
            return MAY if args[0] == MAY or args[1] == MAY else MUST
        if op in _BOTH:
            return MAY if args[0] == MAY and args[1] == MAY else MUST
        if op == "bvurem":
            return MAY if args[1] == MAY else MUST
        return MAY

    def backward(self, op: str, result: Meta, args: Sequence[Meta], i: int) -> Meta:
        if op in _UNARY:
            return MAY if result == MAY else MUST
        if op in ("bvand", "bvor"):
            return MAY if result == MAY else MUST
        if op in _BOTH:
            return MAY if result == MAY and args[1 - i] == MAY else MUST
        return MAY
