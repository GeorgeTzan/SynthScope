"""Command line: `python -m hope_engine.cli {solve,bench,report,compare}`."""

from __future__ import annotations

import argparse
from pathlib import Path

from hope_engine.bench.report import paired_csv, render_text, summarize
from hope_engine.bench.runner import RunConfig, load_records, run_file, run_suite


def _add_run_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--policy", choices=["hope", "leftmost", "meta_off"], default="hope")
    p.add_argument("--holes", type=int, default=3, help="max holes filled at once (hope only)")
    p.add_argument("--timeout", type=float, default=60.0)
    p.add_argument("--nodes", type=int, default=100_000)
    p.add_argument("--seed", type=int, default=0)


def _config(a: argparse.Namespace) -> RunConfig:
    return RunConfig(a.policy, a.holes, a.nodes, a.timeout, a.seed)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="hope_engine")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("solve", help="solve one SyGuS-IF file")
    s.add_argument("file", type=Path)
    _add_run_args(s)
    b = sub.add_parser("bench", help="run every .sl file in a directory (or the given files)")
    b.add_argument("inputs", type=Path, nargs="+")
    b.add_argument("--out", type=Path, required=True)
    _add_run_args(b)
    r = sub.add_parser("report", help="summarize JSONL result files")
    r.add_argument("files", type=Path, nargs="+")
    c = sub.add_parser("compare", help="paired CSV of two JSONL result files")
    c.add_argument("a", type=Path)
    c.add_argument("b", type=Path)
    c.add_argument("--csv", type=Path, required=True)
    args = ap.parse_args(argv)

    if args.cmd == "solve":
        rec = run_file(args.file, _config(args))
        print(f"{rec.status}: {rec.program or '-'}  ({rec.nodes} nodes, {rec.seconds:.3f}s)")
        return 0 if rec.status == "solved" else 2
    if args.cmd == "bench":
        paths = sorted(p for i in args.inputs for p in (i.glob("*.sl") if i.is_dir() else [i]))
        recs = run_suite(paths, _config(args), args.out)
        print(render_text(summarize(recs)))
        return 0
    if args.cmd == "report":
        for f in args.files:
            print(f"{f.name}: {render_text(summarize(load_records(f)))}")
        return 0
    paired_csv(load_records(args.a), load_records(args.b), args.csv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
