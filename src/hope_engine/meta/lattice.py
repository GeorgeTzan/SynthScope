"""Meta abstract domain D# = {BOT, MUST_TOP, MAY_NOT_TOP} (paper §4.3) and the MetaDomain interface."""

from __future__ import annotations

from collections.abc import Sequence
from enum import IntEnum
from typing import Protocol


class Meta(IntEnum):
    """BOT ⊑ MUST_TOP ⊑ MAY_NOT_TOP. gamma: BOT={}, MUST_TOP={top}, MAY_NOT_TOP=everything."""

    BOT = 0
    MUST_TOP = 1
    MAY_NOT_TOP = 2


class MetaDomain[M](Protocol):
    """A meta domain over an underlying domain: coarse 'is the underlying value top?' abstraction."""

    def bottom(self) -> M: ...
    def must(self) -> M: ...
    def may(self) -> M: ...
    def const(self) -> M:
        """Meta value of a constant or input variable (a known, non-top value)."""
        ...

    def join(self, a: M, b: M) -> M: ...
    def is_may(self, a: M) -> bool: ...
    def is_must(self, a: M) -> bool: ...
    def forward(self, op: str, args: Sequence[M]) -> M: ...

    def backward(self, op: str, result: M, args: Sequence[M], i: int) -> M:
        """Backward meta operator: reads the parent's state `result` and all children's states."""
        ...
