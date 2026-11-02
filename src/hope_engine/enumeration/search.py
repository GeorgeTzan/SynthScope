"""Algorithm 1 (paper p.9): top-down search over partial programs with abstract-interpretation pruning."""

from __future__ import annotations

import heapq
import itertools
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal, Protocol

from hope_engine.concrete.bitvector import UnsupportedOperator
from hope_engine.concrete.verify import Example, satisfies
from hope_engine.enumeration.components import ComponentMap, add_components
from hope_engine.enumeration.multifill import fill_selected
from hope_engine.syntax.ast import (
    Hole,
    Node,
    Op,
    Path,
    holes,
    pretty,
    size,
    subterm,
)
from hope_engine.syntax.grammar import Grammar
from hope_engine.trace.events import Emitter, EventSink


class SpecOracle(Protocol):
    """Reference function behind a specification-style problem (see sygus/spec.py)."""

    def output(self, inputs: dict[str, int]) -> int: ...
    def counterexample(self, program: Node) -> dict[str, int] | None: ...


@dataclass(frozen=True)
class Problem:
    grammar: Grammar
    examples: tuple[Example, ...]
    domain: Literal["bv", "str"]
    width: int | None = None
    spec: SpecOracle | None = None


@dataclass(frozen=True)
class Budget:
    max_nodes: int
    timeout_s: float | None


@dataclass
class AnalysisResult:
    infeasible: bool
    preconditions: dict[Path, object] = field(default_factory=dict)
    states: dict[Path, object] = field(default_factory=dict)  # abstract value of every node, first example


class Analyzer(Protocol):
    def analyze(self, partial: Node, examples: tuple[Example, ...]) -> AnalysisResult: ...

    def compatible(
        self,
        result: AnalysisResult,
        partial: Node,
        pos: Path,
        component: Node,
        examples: tuple[Example, ...],
    ) -> bool:
        """Paper line 14: False iff P[pos <- component] is infeasible given analysis `result` of P."""
        ...


Emit = Callable[[str, dict[str, object] | None], None]


def _no_emit(kind: str, payload: dict[str, object] | None = None) -> None:
    return None


@dataclass(frozen=True)
class PickContext:
    problem: Problem
    comps: ComponentMap
    emit: Emit = _no_emit


class HolePolicy(Protocol):
    def pick(self, partial: Node, ctx: PickContext) -> tuple[tuple[Path, ...], bool]:
        """Return (positions to fill, noprune). noprune=True means pruning power is provably 0."""
        ...


class NullAnalyzer:
    """Never prunes. Baseline and test double."""

    def analyze(self, partial: Node, examples: tuple[Example, ...]) -> AnalysisResult:
        return AnalysisResult(False)

    def compatible(
        self,
        result: AnalysisResult,
        partial: Node,
        pos: Path,
        component: Node,
        examples: tuple[Example, ...],
    ) -> bool:
        return True


class LeftmostPolicy:
    def pick(self, partial: Node, ctx: PickContext) -> tuple[tuple[Path, ...], bool]:
        return (holes(partial)[0],), False


@dataclass(frozen=True)
class SearchResult:
    status: Literal["solved", "exhausted", "timeout", "unsupported"]
    program: Node | None
    nodes: int
    seconds: float


def _expansions(grammar: Grammar, nt: str) -> tuple[Node, ...]:
    """One-step top-down expansions: operator applied to fresh holes."""
    return tuple(
        Op(p.label, tuple(Hole(r) for r in p.rhs))
        for p in grammar.productions_for(nt)
        if isinstance(p.label, str) and p.rhs
    )


def productive_nonterminals(grammar: Grammar) -> frozenset[str]:
    """Nonterminals that derive at least one complete program (fixpoint)."""
    prod: set[str] = set()
    changed = True
    while changed:
        changed = False
        for p in grammar.productions:
            if p.lhs not in prod and all(r in prod for r in p.rhs):
                prod.add(p.lhs)
                changed = True
    return frozenset(prod)


def search(
    problem: Problem,
    analyzer: Analyzer,
    policy: HolePolicy,
    budget: Budget,
    sink: EventSink | None = None,
    run_id: str = "run",
    component_size: int = 3,
) -> SearchResult:
    """'exhausted' means the queue emptied or the node cap hit; it is not a proof of unsatisfiability."""
    start = time.monotonic()
    em = Emitter(run_id, sink)
    comps = ComponentMap()
    add_components(problem.grammar, comps, component_size)
    ctx = PickContext(problem, comps, em.emit)
    productive = productive_nonterminals(problem.grammar)
    root: Node = Hole(problem.grammar.start)
    if problem.grammar.start not in productive:
        em.emit("search_started", {"start": problem.grammar.start})
        em.emit("run_finished", {"status": "exhausted", "nodes": 0})
        return SearchResult("exhausted", None, 0, time.monotonic() - start)
    queue: list[tuple[int, int, Node]] = [(size(root), 0, root)]
    parent_of: dict[int, int] = {}  # queue id -> id of the candidate it was made from (only kept when tracing)
    seen: set[Node] = {root}
    counter = 1
    nodes = 0
    status: Literal["solved", "exhausted", "timeout", "unsupported"] = "exhausted"
    solution: Node | None = None
    em.emit("search_started", {"start": problem.grammar.start})

    try:
        while queue:
            if budget.timeout_s is not None and time.monotonic() - start >= budget.timeout_s:
                status = "timeout"
                break
            if nodes >= budget.max_nodes:
                break
            _, cid, partial = heapq.heappop(queue)
            nodes += 1
            hs = holes(partial)
            if not hs:
                if satisfies(partial, problem.examples, problem.width):
                    status, solution = "solved", partial
                    em.emit("solution_found", {"program": pretty(partial)})
                    break
                continue
            em.emit(
                "candidate_expanded",
                {"program": pretty(partial), "holes": len(hs), "id": cid, "parent": parent_of.get(cid)},
            )
            result = analyzer.analyze(partial, problem.examples)
            describe = getattr(analyzer, "describe", None) if em.enabled else None
            if describe is not None:
                em.emit("analysis", describe(result, partial, problem.examples))
            if result.infeasible:
                em.emit("pruned", {"program": pretty(partial), "reason": "infeasible"})
                continue
            positions, noprune = policy.pick(partial, ctx)
            cand_lists: list[list[Node]] = []
            for pos in positions:
                hole = subterm(partial, pos)
                assert isinstance(hole, Hole)
                every = (*comps.get(hole.nonterminal), *_expansions(problem.grammar, hole.nonterminal))
                kept = [
                    c
                    for c in every
                    if noprune or analyzer.compatible(result, partial, pos, c, problem.examples)
                ]
                if len(kept) < len(every):
                    em.emit("pruned", {"position": list(pos), "count": len(every) - len(kept), "reason": "component"})
                cand_lists.append(kept)
            # [ponytail: cap children per step at max_nodes instead of enumerating huge products]
            for child in itertools.islice(fill_selected(partial, positions, cand_lists), budget.max_nodes):
                if child in seen or any(
                    h.nonterminal not in productive
                    for h in (subterm(child, q) for q in holes(child))
                    if isinstance(h, Hole)
                ):
                    continue
                seen.add(child)
                if em.enabled:
                    parent_of[counter] = cid
                heapq.heappush(queue, (size(child), counter, child))
                counter += 1
            em.emit("hole_filled", {"positions": [list(p) for p in positions], "noprune": noprune})
    except (UnsupportedOperator, TypeError):  # TypeError: ill-typed grammar, e.g. an Int where a String belongs
        status = "unsupported"

    seconds = time.monotonic() - start
    em.emit("run_finished", {"status": status, "nodes": nodes})
    return SearchResult(status, solution, nodes, seconds)
