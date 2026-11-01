"""Simultaneous filling of several holes (paper §4.5.1)."""

from __future__ import annotations

import itertools
from collections.abc import Iterator, Sequence

from hope_engine.syntax.ast import Node, Path, replace_at


def fill_selected(
    partial: Node, positions: Sequence[Path], candidates: Sequence[Sequence[Node]]
) -> Iterator[Node]:
    """Lazily yield partial with every combination of candidates[i] placed at positions[i].

    `candidates` are already filtered by the caller. Positions must be distinct and non-nested,
    so replacing one never moves another.
    """
    if not positions or len(positions) != len(candidates):
        raise ValueError("need one candidate list per position")
    for a, b in itertools.combinations(positions, 2):
        if a[: len(b)] == b or b[: len(a)] == a:
            raise ValueError(f"overlapping positions {a} and {b}")
    for combo in itertools.product(*candidates):
        out = partial
        for pos, c in zip(positions, combo, strict=True):
            out = replace_at(out, pos, c)
        yield out
