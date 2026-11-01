"""Immutable typed partial programs (paper §3.1). A Hole stands for a nonterminal."""

from __future__ import annotations

from dataclasses import dataclass

Path = tuple[int, ...]


@dataclass(frozen=True)
class Op:
    name: str
    args: tuple[Node, ...]


@dataclass(frozen=True)
class Const:
    value: int | str
    type: str


@dataclass(frozen=True)
class Var:
    name: str


@dataclass(frozen=True)
class Hole:
    nonterminal: str


Node = Op | Const | Var | Hole


def holes(node: Node) -> tuple[Path, ...]:
    """Hole positions, left-to-right depth-first."""
    if isinstance(node, Hole):
        return ((),)
    if isinstance(node, Op):
        return tuple((i, *p) for i, a in enumerate(node.args) for p in holes(a))
    return ()


def subterm(node: Node, path: Path) -> Node:
    for i in path:
        if not isinstance(node, Op):
            raise IndexError(f"path {path} leaves the tree")
        node = node.args[i]
    return node


def replace_at(node: Node, path: Path, subtree: Node) -> Node:
    if not path:
        return subtree
    if not isinstance(node, Op):
        raise IndexError(f"path {path} leaves the tree")
    i, rest = path[0], path[1:]
    args = node.args
    return Op(node.name, (*args[:i], replace_at(args[i], rest, subtree), *args[i + 1 :]))


def size(node: Node) -> int:
    """Number of AST nodes."""
    if isinstance(node, Op):
        return 1 + sum(size(a) for a in node.args)
    return 1


def pretty(node: Node) -> str:
    """S-expression rendering; holes print as □:Nonterminal."""
    if isinstance(node, Op):
        return "(" + " ".join([node.name, *(pretty(a) for a in node.args)]) + ")"
    if isinstance(node, Const):
        return f'"{node.value}"' if isinstance(node.value, str) else str(node.value)
    if isinstance(node, Var):
        return node.name
    return f"□:{node.nonterminal}"
