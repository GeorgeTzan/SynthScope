"""Rank conditions (7), (8) and the PickHole procedure (paper Algorithm 2)."""

from __future__ import annotations

import itertools
import random
from collections.abc import Collection
from dataclasses import dataclass

from hope_engine.meta.analysis import meta_analyze
from hope_engine.meta.lattice import MetaDomain
from hope_engine.syntax.ast import Node, Path, holes


@dataclass(frozen=True)
class Ranks:
    rank1: tuple[Path, ...]
    rank2: tuple[Path, ...]


def may_infeasible[M](res: dict[Path, tuple[M, M]], domain: MetaDomain[M]) -> bool:
    """Condition (7): some position may be non-top both forward and backward (intersection may be bottom)."""
    return any(domain.is_may(f) and domain.is_may(b) for f, b in res.values())


def may_prune_components[M](
    res: dict[Path, tuple[M, M]],
    domain: MetaDomain[M],
    hypo: Collection[Path],
    hole_positions: Collection[Path],
) -> bool:
    """Condition (8): another hole is forward-top for sure but may get a non-trivial precondition."""
    return any(
        domain.is_must(res[p][0]) and domain.is_may(res[p][1]) for p in hole_positions if p not in hypo
    )


def rank_holes[M](partial: Node, domain: MetaDomain[M]) -> Ranks:
    hs = holes(partial)
    r1: list[Path] = []
    r2: list[Path] = []
    for pos in hs:
        res = meta_analyze(domain, partial, (pos,))
        if may_infeasible(res, domain):
            r1.append(pos)
        elif may_prune_components(res, domain, (pos,), hs):
            r2.append(pos)
    return Ranks(tuple(r1), tuple(r2))


def choose(ranks: Ranks, partial: Node, rng: random.Random) -> tuple[Path, bool]:
    """Algorithm 2 lines 12-18. The bool is `noprune`: True means the pruning power is provably 0."""
    if ranks.rank1:
        return rng.choice(ranks.rank1), False
    if ranks.rank2:
        return rng.choice(ranks.rank2), False
    return rng.choice(holes(partial)), True


def pick_hole[M](partial: Node, domain: MetaDomain[M], rng: random.Random) -> tuple[Path, bool]:
    return choose(rank_holes(partial, domain), partial, rng)


@dataclass(frozen=True)
class RankedSets:
    rank1: tuple[tuple[Path, ...], ...]
    rank2: tuple[tuple[Path, ...], ...]


def rank_hole_sets[M](partial: Node, domain: MetaDomain[M], max_holes: int) -> RankedSets:
    """Paper §4.5.1: rank every subset of holes of size 1..max_holes, hypothetically filled together."""
    hs = holes(partial)
    r1: list[tuple[Path, ...]] = []
    r2: list[tuple[Path, ...]] = []
    for k in range(1, min(max_holes, len(hs)) + 1):
        for subset in itertools.combinations(hs, k):
            res = meta_analyze(domain, partial, subset)
            if may_infeasible(res, domain):
                r1.append(subset)
            elif may_prune_components(res, domain, subset, hs):
                r2.append(subset)
    return RankedSets(tuple(r1), tuple(r2))


def choose_set(
    ranked: RankedSets, partial: Node, rng: random.Random
) -> tuple[tuple[Path, ...], bool]:
    """Algorithm 2 over sets: best rank wins, smallest subset within it (fewest combinations)."""
    for sets in (ranked.rank1, ranked.rank2):
        if sets:
            smallest = min(len(s) for s in sets)
            return rng.choice([s for s in sets if len(s) == smallest]), False
    return (rng.choice(holes(partial)),), True


def pick_holes[M](
    partial: Node, domain: MetaDomain[M], rng: random.Random, max_holes: int
) -> tuple[tuple[Path, ...], bool]:
    return choose_set(rank_hole_sets(partial, domain, max_holes), partial, rng)
