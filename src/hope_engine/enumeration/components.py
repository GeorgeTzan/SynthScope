"""Bottom-up component enumeration: complete subexpressions per nonterminal, by increasing size."""

from __future__ import annotations

import itertools
from collections.abc import Iterator

from hope_engine.syntax.ast import Node, Op
from hope_engine.syntax.grammar import Grammar


class ComponentMap:
    def __init__(self) -> None:
        self._by_size: dict[str, dict[int, list[Node]]] = {}
        self.max_size = 0

    def get(self, nt: str) -> tuple[Node, ...]:
        sizes = self._by_size.get(nt, {})
        return tuple(n for s in sorted(sizes) for n in sizes[s])

    def _of_size(self, nt: str, s: int) -> list[Node]:
        return self._by_size.get(nt, {}).get(s, [])

    def _add(self, nt: str, s: int, node: Node) -> None:
        self._by_size.setdefault(nt, {}).setdefault(s, []).append(node)


def _compositions(total: int, parts: int) -> Iterator[tuple[int, ...]]:
    if parts == 1:
        yield (total,)
        return
    for first in range(1, total - parts + 2):
        for rest in _compositions(total - first, parts - 1):
            yield (first, *rest)


def _nonterminals(grammar: Grammar) -> list[str]:
    seen: dict[str, None] = {}
    for p in grammar.productions:
        seen.setdefault(p.lhs)
        for r in p.rhs:
            seen.setdefault(r)
    return list(seen)


def add_components(grammar: Grammar, comps: ComponentMap, size_limit: int) -> None:
    """Extend comps with every complete program up to size_limit nodes (idempotent).

    [ponytail: no observational-equivalence pruning; exhaustive per size.]
    """
    for n in range(comps.max_size + 1, size_limit + 1):
        for nt in _nonterminals(grammar):
            for p in grammar.productions_for(nt):
                if not p.rhs:
                    leaf: Node = Op(p.label, ()) if isinstance(p.label, str) else p.label
                    if n == 1:
                        comps._add(nt, n, leaf)
                    continue
                if n < 1 + len(p.rhs) or not isinstance(p.label, str):
                    continue
                for sizes in _compositions(n - 1, len(p.rhs)):
                    pools = [comps._of_size(r, s) for r, s in zip(p.rhs, sizes, strict=True)]
                    for args in itertools.product(*pools):
                        comps._add(nt, n, Op(p.label, args))
    comps.max_size = max(comps.max_size, size_limit)
