"""Hole-picking policies: HOPE (paper Algorithm 2), leftmost, and meta-off (seeded random)."""

from __future__ import annotations

import random

from hope_engine.enumeration.search import LeftmostPolicy, PickContext
from hope_engine.meta.lattice import MetaDomain
from hope_engine.meta.rank import choose_set, rank_hole_sets
from hope_engine.syntax.ast import Node, Path, holes

__all__ = ["HopePolicy", "LeftmostPolicy", "MetaOffPolicy"]


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


class MetaOffPolicy:
    """No meta analysis: a seeded random hole, pruning always on (the HOPE- ablation)."""

    def __init__(self, seed: int = 0) -> None:
        self.rng = random.Random(seed)

    def pick(self, partial: Node, ctx: PickContext) -> tuple[tuple[Path, ...], bool]:
        return (self.rng.choice(holes(partial)),), False
