"""Hole-picking policies: HOPE (paper Algorithm 2), leftmost, and meta-off (seeded random)."""

from __future__ import annotations

import math
import random
from collections.abc import Callable
from typing import Any

from hope_engine.enumeration.search import LeftmostPolicy, PickContext
from hope_engine.meta.lattice import MetaDomain
from hope_engine.meta.rank import choose_set, rank_hole_sets
from hope_engine.syntax.ast import Node, Path, holes

__all__ = ["ConstrainedPolicy", "HopePolicy", "LeftmostPolicy", "MetaOffPolicy"]


class HopePolicy[M]:
    def __init__(self, domain: MetaDomain[M], seed: int = 0, max_holes: int = 1) -> None:
        self.domain = domain
        self.rng = random.Random(seed)
        self.max_holes = max_holes

    def pick(self, partial: Node, ctx: PickContext) -> tuple[tuple[Path, ...], bool]:
        ranks = rank_hole_sets(partial, self.domain, self.max_holes)
        positions, noprune = choose_set(ranks, partial, self.rng)
        ctx.emit(
            "hole_ranked",
            {
                "rank1": [[list(p) for p in s] for s in ranks.rank1],
                "rank2": [[list(p) for p in s] for s in ranks.rank2],
                "picked": [list(p) for p in positions],
                "noprune": noprune,
            },
        )
        return positions, noprune


class ConstrainedPolicy:
    """Most constrained hole first: the hole whose necessary precondition, taken from the underlying analysis of
    the current candidate, admits the fewest concrete values over all examples. Ties go to the leftmost hole."""

    def __init__(self, cardinality: Callable[[Any], int]) -> None:
        self.cardinality = cardinality

    def pick(self, partial: Node, ctx: PickContext) -> tuple[tuple[Path, ...], bool]:
        hs = holes(partial)
        if ctx.analysis is None:
            return (hs[0],), False
        pre = ctx.analysis.preconditions

        def freedom(pos: Path) -> int:
            values = pre.get(pos)
            return math.prod(self.cardinality(v) for v in values) if isinstance(values, tuple) else -1

        scores = [freedom(p) for p in hs]
        known = [s for s in scores if s >= 0]
        if not known:
            return (hs[0],), False
        return (hs[scores.index(min(known))],), False


class MetaOffPolicy:
    """No meta analysis: a seeded random hole, pruning always on (the HOPE- ablation)."""

    def __init__(self, seed: int = 0) -> None:
        self.rng = random.Random(seed)

    def pick(self, partial: Node, ctx: PickContext) -> tuple[tuple[Path, ...], bool]:
        return (self.rng.choice(holes(partial)),), False
