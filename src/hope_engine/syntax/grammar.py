"""Regular tree grammar (paper §3.1) and partial-program validation."""

from __future__ import annotations

from dataclasses import dataclass

from hope_engine.syntax.ast import Const, Hole, Node, Op, Var


class GrammarError(ValueError):
    pass


@dataclass(frozen=True)
class Production:
    """lhs -> label(rhs...). A str label is an operator; a Const or Var is a leaf."""

    lhs: str
    label: str | Const | Var
    rhs: tuple[str, ...] = ()


@dataclass(frozen=True)
class Grammar:
    productions: tuple[Production, ...]
    start: str

    def productions_for(self, nt: str) -> tuple[Production, ...]:
        return tuple(p for p in self.productions if p.lhs == nt)


def _matches(node: Node, nt: str, g: Grammar) -> bool:
    if isinstance(node, Hole):
        return node.nonterminal == nt
    for p in g.productions_for(nt):
        if isinstance(node, Op):
            if (
                p.label == node.name
                and len(p.rhs) == len(node.args)
                and all(_matches(a, r, g) for a, r in zip(node.args, p.rhs, strict=True))
            ):
                return True
        elif p.label == node:
            return True
    return False


def validate(node: Node, grammar: Grammar) -> None:
    """Raise GrammarError unless node is a (partial) program derivable from the start symbol."""
    if not _matches(node, grammar.start, grammar):
        raise GrammarError(f"{node!r} is not derivable from {grammar.start!r}")
