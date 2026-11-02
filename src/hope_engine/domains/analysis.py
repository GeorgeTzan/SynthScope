"""Underlying forward-backward analysis (paper §4.2) and the Analyzer built on it."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from hope_engine.concrete.verify import Example
from hope_engine.domains.base import Domain
from hope_engine.enumeration.search import AnalysisResult
from hope_engine.syntax.ast import Const, Hole, Node, Op, Path, Var


def _tree(node: Node) -> tuple[list[Path], dict[Path, Node]]:
    order: list[Path] = []
    nodes: dict[Path, Node] = {}

    def walk(n: Node, p: Path) -> None:
        order.append(p)
        nodes[p] = n
        if isinstance(n, Op):
            for i, a in enumerate(n.args):
                walk(a, (*p, i))

    walk(node, ())
    return order, nodes


def _leaf_or_forward[A](
    domain: Domain[A], n: Node, env: Mapping[str, int | str], kids: list[A]
) -> A:
    if isinstance(n, Const):
        return domain.alpha(n.value)
    if isinstance(n, Var):
        return domain.alpha(env[n.name])
    if isinstance(n, Hole):
        return domain.top()
    return domain.forward(n.name, kids)


def forward_value[A](domain: Domain[A], node: Node, env: Mapping[str, int | str]) -> A:
    """Abstract value of a (possibly partial) program; holes are top."""
    kids = [forward_value(domain, a, env) for a in node.args] if isinstance(node, Op) else []
    return _leaf_or_forward(domain, node, env, kids)


def analyze_underlying[A](
    domain: Domain[A], partial: Node, env: Mapping[str, int | str], output: int | str
) -> dict[Path, A]:
    """Alternate forward (lfp) and backward (gfp) passes until nothing changes.

    Every pass only meets with the current state, so the iteration decreases in a finite lattice.
    Holes start at top and are refined only by the backward pass (their necessary precondition).
    """
    order, nodes = _tree(partial)
    kids = {p: [(*p, i) for i in range(len(n.args))] if isinstance(n, Op) else [] for p, n in nodes.items()}
    state: dict[Path, A] = {p: domain.top() for p in order}
    state[()] = domain.meet(state[()], domain.alpha(output))
    changed = True
    while changed:
        changed = False
        for p in reversed(order):  # children before parents
            v = _leaf_or_forward(domain, nodes[p], env, [state[k] for k in kids[p]])
            new = domain.meet(state[p], v)
            if new != state[p]:
                state[p], changed = new, True
        for p in order:  # parents before children
            n = nodes[p]
            if not isinstance(n, Op):
                continue
            args = [state[k] for k in kids[p]]
            for i, k in enumerate(kids[p]):
                new = domain.meet(state[k], domain.backward(n.name, state[p], args, i))
                if new != state[k]:
                    state[k], changed = new, True
        if any(domain.is_bottom(v) for v in state.values()):
            break
    return state


def _label(n: Node) -> str:
    if isinstance(n, Op | Var):
        return n.name
    return f"□ {n.nonterminal}" if isinstance(n, Hole) else str(n.value)


class DomainAnalyzer[A]:
    """Analyzer (search.py protocol) backed by a Domain; one analysis per example."""

    def __init__(self, domain: Domain[A]) -> None:
        self.domain = domain
        # Abstract value of a complete component per example, keyed by object identity: the component map keeps
        # the objects alive, and the stored node pins the id.  [ponytail: unbounded; one entry per component.]
        self._values: dict[tuple[int, int], tuple[Node, A]] = {}

    def _component_value(self, node: Node, i: int, env: Mapping[str, int | str]) -> A:
        hit = self._values.get((id(node), i))
        if hit is not None:
            return hit[1]
        kids = [self._component_value(a, i, env) for a in node.args] if isinstance(node, Op) else []
        value = _leaf_or_forward(self.domain, node, env, kids)
        self._values[(id(node), i)] = (node, value)
        return value

    def analyze(self, partial: Node, examples: tuple[Example, ...]) -> AnalysisResult:
        per_example = [analyze_underlying(self.domain, partial, ex.inputs, ex.output) for ex in examples]
        infeasible = any(self.domain.is_bottom(v) for st in per_example for v in st.values())
        _, nodes = _tree(partial)
        pre: dict[Path, object] = {
            p: tuple(st[p] for st in per_example) for p, n in nodes.items() if isinstance(n, Hole)
        }
        states: dict[Path, object] = dict(per_example[0]) if per_example else {}
        return AnalysisResult(infeasible, pre, states)

    def describe(self, result: AnalysisResult, partial: Node, examples: tuple[Example, ...]) -> dict[str, object]:
        """Event payload: the first example and the abstract value of every node of `partial` for it."""
        order, nodes = _tree(partial)
        rows: list[dict[str, object]] = []
        for p in order:
            n = nodes[p]
            state = result.states.get(p)
            shown = self.domain.show(cast("A", state)) if state is not None else "?"
            rows.append({"path": list(p), "label": _label(n), "state": shown})
        first = examples[0] if examples else None
        return {
            "inputs": dict(first.inputs) if first else {},
            "output": first.output if first else None,
            "infeasible": result.infeasible,
            "nodes": rows,
        }

    def compatible(
        self,
        result: AnalysisResult,
        partial: Node,
        pos: Path,
        component: Node,
        examples: tuple[Example, ...],
    ) -> bool:
        pres = result.preconditions[pos]
        assert isinstance(pres, tuple)
        return all(
            not self.domain.is_bottom(self.domain.meet(self._component_value(component, i, ex.inputs), pre))
            for i, (ex, pre) in enumerate(zip(examples, pres, strict=True))
        )
