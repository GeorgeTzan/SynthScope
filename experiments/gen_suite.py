"""Generate the 8-bit benchmark suite: random target programs of fixed size and examples computed from them."""

from __future__ import annotations

import argparse
import random
from pathlib import Path

from hope_engine.concrete.bitvector import eval_bv
from hope_engine.concrete.verify import Example
from hope_engine.syntax.ast import Const, Node, Op, Var

WIDTH = 8
UNARY = ("bvnot", "bvneg")
BINARY = ("bvand", "bvor", "bvxor", "bvadd", "bvsub", "bvshl", "bvlshr")
CONSTS = (0x00, 0x01, 0xFF)
VARS = ("x", "y")
TOP = (1 << WIDTH) - 1
_PROBE = random.Random(0)
PROBES = tuple((_PROBE.randint(0, TOP), _PROBE.randint(0, TOP)) for _ in range(1024))


class SuiteError(RuntimeError):
    pass


def _leaf(rng: random.Random) -> Node:
    pick = rng.randrange(len(VARS) + len(CONSTS))
    return Var(VARS[pick]) if pick < len(VARS) else Const(CONSTS[pick - len(VARS)], "bv")


def random_program(rng: random.Random, size: int) -> Node:
    if size == 1:
        return _leaf(rng)
    if size == 2 or rng.random() < 0.25:
        return Op(rng.choice(UNARY), (random_program(rng, size - 1),))
    left = rng.randint(1, size - 2)
    return Op(rng.choice(BINARY), (random_program(rng, left), random_program(rng, size - 1 - left)))


def _run(program: Node, x: int, y: int) -> int:
    return eval_bv(program, {"x": x, "y": y}, WIDTH)


def fingerprint(program: Node) -> tuple[int, ...]:
    return tuple(_run(program, x, y) for x, y in PROBES)


def _examples(target: Node, seed: int, name: str) -> tuple[Example, ...]:
    rng = random.Random(f"{seed}:{name}")
    inputs = [(0, 0), (TOP, TOP), *((rng.randint(0, TOP), rng.randint(0, TOP)) for _ in range(4))]
    return tuple(Example({"x": x, "y": y}, _run(target, x, y)) for x, y in inputs)


def make_suite(
    seed: int = 0, sizes: tuple[int, ...] = (3, 5, 7, 9), per_size: int = 25, max_tries: int = 20000
) -> list[tuple[str, Node, tuple[Example, ...]]]:
    rng = random.Random(seed)
    seen = {fingerprint(Var(v)) for v in VARS}
    suite: list[tuple[str, Node, tuple[Example, ...]]] = []
    for size in sizes:
        accepted = 0
        for _ in range(max_tries):
            if accepted == per_size:
                break
            target = random_program(rng, size)
            print_ = fingerprint(target)
            if len(set(print_)) == 1 or print_ in seen:
                continue
            seen.add(print_)
            name = f"s{size}_{accepted:02d}"
            suite.append((name, target, _examples(target, seed, name)))
            accepted += 1
        if accepted < per_size:
            raise SuiteError(f"only {accepted} of {per_size} distinct non-trivial targets at size {size}")
    return suite


def _hex(value: int) -> str:
    return f"#x{value:02X}"


def _sexpr(node: Node) -> str:
    if isinstance(node, Op):
        return "(" + " ".join([node.name, *(_sexpr(a) for a in node.args)]) + ")"
    if isinstance(node, Const):
        assert isinstance(node.value, int)
        return _hex(node.value)
    assert isinstance(node, Var)
    return node.name


def to_sygus(name: str, target: Node, examples: tuple[Example, ...], seed: int) -> str:
    sort = f"(BitVec {WIDTH})"
    symbols = [
        *VARS,
        *(_hex(c) for c in CONSTS),
        *(f"({op} Start)" for op in UNARY),
        *(f"({op} Start Start)" for op in BINARY),
    ]
    params = " ".join(f"({v} {sort})" for v in VARS)
    lines = [
        f"; suite8 name={name} seed={seed} target={_sexpr(target)}",
        "(set-logic BV)",
        f"(synth-fun f ({params}) {sort}",
        f"  ((Start {sort} ({' '.join(symbols)}))))",
    ]
    for ex in examples:
        args = " ".join(_hex(int(ex.inputs[v])) for v in VARS)
        lines.append(f"(constraint (= (f {args}) {_hex(int(ex.output))}))")
    lines.append("(check-synth)")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=Path("experiments/suite8"))
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--per-size", type=int, default=25)
    args = ap.parse_args(argv)
    suite = make_suite(seed=args.seed, per_size=args.per_size)
    args.out.mkdir(parents=True, exist_ok=True)
    for old in args.out.glob("s[0-9]*_[0-9][0-9].sl"):
        old.unlink()
    for name, target, examples in suite:
        (args.out / f"{name}.sl").write_text(to_sygus(name, target, examples, args.seed), encoding="utf-8")
    print(f"{len(suite)} problems written to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
