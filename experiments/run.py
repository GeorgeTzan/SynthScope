"""Run every strategy, seed and component size over one suite: one `hope_engine.cli bench` process per configuration."""

from __future__ import annotations

import argparse
import random
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


def configs(
    seeds: tuple[int, ...] = (0, 1, 2), component_sizes: tuple[int, ...] = (1, 3)
) -> list[tuple[str, list[str]]]:
    out: list[tuple[str, list[str]]] = []
    for c in component_sizes:
        tail = ["--component-size", str(c)]
        out.append((f"c{c}_leftmost", ["--policy", "leftmost", *tail]))
        out += [(f"c{c}_random_s{s}", ["--policy", "meta_off", "--seed", str(s), *tail]) for s in seeds]
        out += [(f"c{c}_meta_s{s}", ["--policy", "hope", "--holes", "1", "--seed", str(s), *tail]) for s in seeds]
    return out


def _lines(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines()) if path.exists() else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("suite", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--timeout", type=float, default=30.0)
    ap.add_argument("--nodes", type=int, default=1_000_000_000)
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--sample-seed", type=int, default=0)
    args = ap.parse_args(argv)
    out: Path = args.out or Path("results/exp8") / args.suite.resolve().name
    out.mkdir(parents=True, exist_ok=True)
    paths = sorted(args.suite.glob("*.sl"))
    if args.limit is not None and args.limit < len(paths):
        paths = sorted(random.Random(args.sample_seed).sample(paths, args.limit))
    if not paths:
        print(f"no .sl files in {args.suite}", file=sys.stderr)
        return 1

    def one(config: tuple[str, list[str]]) -> int:
        name, extra = config
        target = out / f"{name}.jsonl"
        if _lines(target) == len(paths):
            print(f"{name}: already complete, skipped", flush=True)
            return 0
        cmd = [sys.executable, "-m", "hope_engine.cli", "bench", *map(str, paths), "--out", str(target),
               "--timeout", str(args.timeout), "--nodes", str(args.nodes), *extra]
        done = subprocess.run(cmd, capture_output=True, text=True, check=False)
        print(f"{name}: {done.stdout.strip() or done.stderr.strip()}", flush=True)
        return done.returncode

    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        codes = list(pool.map(one, configs()))
    return 1 if any(codes) else 0


if __name__ == "__main__":
    raise SystemExit(main())
