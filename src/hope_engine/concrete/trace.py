"""Per-node concrete values of a program on each example (for the dashboard's "with input" view)."""

from __future__ import annotations

from typing import Any

from hope_engine.concrete.bitvector import UnsupportedOperator, eval_bv
from hope_engine.concrete.string import eval_str
from hope_engine.concrete.verify import Example
from hope_engine.syntax.ast import Node, Op

Value = int | str | None


def _walk(node: Node, path: tuple[int, ...], out: list[tuple[str, Node]]) -> None:
    out.append((".".join(map(str, path)), node))
    if isinstance(node, Op):
        for i, a in enumerate(node.args):
            _walk(a, (*path, i), out)


def _value(node: Node, example: Example, width: int | None) -> Value:
    """Value of one subtree, or None when it cannot be computed (a hole below it, or an unsupported operation)."""
    try:
        if width is None:
            return eval_str(node, example.inputs)
        env = {k: v for k, v in example.inputs.items() if isinstance(v, int)}
        return eval_bv(node, env, width)
    except (ValueError, TypeError, KeyError, UnsupportedOperator):
        return None


def node_values(program: Node, examples: tuple[Example, ...], width: int | None) -> list[dict[str, Any]]:
    """For each example: its inputs, expected output and the value at every node, keyed by dotted child path ('' = root)."""
    nodes: list[tuple[str, Node]] = []
    _walk(program, (), nodes)
    return [
        {"inputs": dict(ex.inputs), "expected": ex.output, "values": {p: _value(n, ex, width) for p, n in nodes}}
        for ex in examples
    ]
