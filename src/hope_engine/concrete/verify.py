"""Independent solution check: evaluates a complete program on every example."""

from __future__ import annotations

from dataclasses import dataclass

from hope_engine.concrete.bitvector import eval_bv
from hope_engine.concrete.string import eval_str
from hope_engine.syntax.ast import Node


@dataclass(frozen=True)
class Example:
    inputs: dict[str, int | str]
    output: int | str


def satisfies(program: Node, examples: tuple[Example, ...], width: int | None = None) -> bool:
    """Check every example. width=None means a string/int program; otherwise a bitvector program."""
    if width is None:
        return all(eval_str(program, ex.inputs) == ex.output for ex in examples)
    mask = (1 << width) - 1
    for ex in examples:
        env = {k: v for k, v in ex.inputs.items() if isinstance(v, int)}
        assert isinstance(ex.output, int)
        if eval_bv(program, env, width) != ex.output & mask:
            return False
    return True
