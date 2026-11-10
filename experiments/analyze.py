"""Turn experiment JSONL into committed CSV tables and figures."""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, TypedDict

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

STRATEGIES = ("leftmost", "random", "meta", "constrained")
COLORS = {"leftmost": "#1f77b4", "random": "#ff7f0e", "meta": "#d62728", "constrained": "#2ca02c"}
MEASURES = ("seconds", "nodes", "analyzer_calls", "analysis_seconds", "meta_seconds", "program_size")
FILE = re.compile(r"c(\d+)_(leftmost|random|meta|constrained)(?:_s(\d+))?\.jsonl")


class Row(TypedDict):
    suite: str
    component_size: int
    strategy: str
    seed: int | None
    benchmark: str
    status: str
    seconds: float
    nodes: int
    analyzer_calls: int
    meta_calls: int
    analysis_seconds: float
    meta_seconds: float
    program_size: int | None


Key = tuple[str, int, str, str]
PerProblem = dict[Key, dict[str, Any]]


def load(root: Path) -> list[Row]:
    rows: list[Row] = []
    for path in sorted(root.glob("*/*.jsonl")):
        m = FILE.fullmatch(path.name)
        if m is None:
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            d = json.loads(line)
            rows.append({
                "suite": path.parent.name,
                "component_size": int(m.group(1)),
                "strategy": m.group(2),
                "seed": int(m.group(3)) if m.group(3) is not None else None,
                "benchmark": d["benchmark"],
                "status": d["status"],
                "seconds": d["seconds"],
                "nodes": d["nodes"],
                "analyzer_calls": d["analyzer_calls"],
                "meta_calls": d["meta_calls"],
                "analysis_seconds": d.get("analysis_seconds", 0.0),
                "meta_seconds": d.get("meta_seconds", 0.0),
                "program_size": d["program_size"],
            })
    order = {s: i for i, s in enumerate(STRATEGIES)}
    rows.sort(key=lambda r: (r["suite"], r["component_size"], order[r["strategy"]], r["seed"] or 0, r["benchmark"]))
    return rows


def per_problem(rows: list[Row]) -> PerProblem:
    groups: dict[Key, list[Row]] = defaultdict(list)
    for r in rows:
        groups[(r["suite"], r["component_size"], r["strategy"], r["benchmark"])].append(r)
    out: PerProblem = {}
    for key, runs in groups.items():
        solved = [r for r in runs if r["status"] == "solved"]
        entry: dict[str, Any] = {"solved": len(solved) == len(runs)}
        for m in MEASURES:
            values = [r[m] for r in solved if r[m] is not None]  # type: ignore[literal-required]
            entry[m] = statistics.median(values) if values else None
        out[key] = entry
    return out


def _strategies(pp: PerProblem, suite: str, c: int) -> list[str]:
    present = {k[2] for k in pp if k[0] == suite and k[1] == c}
    return [s for s in STRATEGIES if s in present]


def common(pp: PerProblem, suite: str, component_size: int) -> set[str]:
    names = _strategies(pp, suite, component_size)
    sets = [
        {k[3] for k, v in pp.items() if k[:3] == (suite, component_size, s) and v["solved"]} for s in names
    ]
    return set.intersection(*sets) if sets else set()


def summary(rows: list[Row]) -> list[dict[str, Any]]:
    pp = per_problem(rows)
    out: list[dict[str, Any]] = []
    groups = sorted({(r["suite"], r["component_size"]) for r in rows})
    for suite, c in groups:
        shared = common(pp, suite, c)
        for s in _strategies(pp, suite, c):
            mine = [r for r in rows if (r["suite"], r["component_size"], r["strategy"]) == (suite, c, s)]
            by_seed: dict[int | None, int] = defaultdict(int)
            for r in mine:
                by_seed[r["seed"]] += r["status"] == "solved"
            counts = list(by_seed.values())
            cells = [pp[(suite, c, s, b)] for b in sorted(shared)]
            total = sum(x["seconds"] for x in cells)

            def med(measure: str, cells: list[dict[str, Any]] = cells) -> float | None:
                return statistics.median(x[measure] for x in cells) if cells else None

            out.append({
                "suite": suite,
                "component_size": c,
                "strategy": s,
                "problems": len({r["benchmark"] for r in mine}),
                "seeds": len(counts),
                "solved_mean": statistics.mean(counts),
                "solved_min": min(counts),
                "solved_max": max(counts),
                "common": len(shared),
                "median_seconds": med("seconds"),
                "mean_seconds": total / len(cells) if cells else None,
                "median_nodes": med("nodes"),
                "median_analyzer_calls": med("analyzer_calls"),
                "analysis_share": sum(x["analysis_seconds"] for x in cells) / total if total else None,
                "meta_share": sum(x["meta_seconds"] for x in cells) / total if total else None,
            })
    return out


def paired(pp: PerProblem, suite: str, component_size: int, a: str, b: str) -> tuple[int, int, int]:
    fewer = equal = more = 0
    for (su, c, s, bench), va in pp.items():
        vb = pp.get((su, c, b, bench))
        if (su, c, s) != (suite, component_size, a) or vb is None or not (va["solved"] and vb["solved"]):
            continue
        fewer += va["nodes"] < vb["nodes"]
        equal += va["nodes"] == vb["nodes"]
        more += va["nodes"] > vb["nodes"]
    return fewer, equal, more


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        for r in rows:
            w.writerow({k: "" if v is None else (f"{v:.6g}" if isinstance(v, float) else v) for k, v in r.items()})


def _panels(sizes: list[int]) -> tuple[Any, list[Any]]:
    fig, axes = plt.subplots(1, len(sizes), figsize=(4.2 * len(sizes), 3.2), squeeze=False)
    return fig, list(axes[0])


def _save(fig: Any, path: Path, drawn: bool) -> None:
    if drawn:
        fig.tight_layout()
        fig.savefig(path)
    else:
        print(f"no data for {path.name}, skipped", file=sys.stderr)
    plt.close(fig)


def _figures(pp: PerProblem, suite: str, out: Path) -> None:
    sizes = sorted({k[1] for k in pp if k[0] == suite})
    title = "Μέγεθος components = {}"

    fig, axes = _panels(sizes)
    drawn = False
    for ax, c in zip(axes, sizes, strict=True):
        for s in _strategies(pp, suite, c):
            times = sorted(v["seconds"] for k, v in pp.items() if k[:3] == (suite, c, s) and v["solved"])
            if times:
                drawn = True
                ax.plot(range(1, len(times) + 1), list(itertools.accumulate(times)), color=COLORS[s], label=s)
        ax.set(title=title.format(c), xlabel="Λυμένα προβλήματα", ylabel="Αθροιστικός χρόνος (s)")
        ax.legend()
    _save(fig, out / f"cactus_{suite}.pdf", drawn)

    fig, axes = _panels(sizes)
    drawn = False
    for ax, c in zip(axes, sizes, strict=True):
        names = _strategies(pp, suite, c)
        shared = common(pp, suite, c)
        by_size: dict[int, list[str]] = defaultdict(list)
        for b in shared:
            by_size[int(min(pp[(suite, c, s, b)]["program_size"] for s in names))].append(b)
        for s in names:
            xs = sorted(by_size)
            if xs:
                drawn = True
                ys = [statistics.median(pp[(suite, c, s, b)]["nodes"] for b in by_size[x]) for x in xs]
                ax.plot(xs, ys, marker="o", color=COLORS[s], label=s)
        ax.set(title=title.format(c), xlabel="Μέγεθος λύσης", ylabel="Κόμβοι (διάμεσος)", yscale="log")
        ax.legend()
    _save(fig, out / f"nodes_by_size_{suite}.pdf", drawn)

    fig, axes = _panels(sizes)
    drawn = False
    for ax, c in zip(axes, sizes, strict=True):
        hi = 1.0
        for s in ("meta", "constrained"):
            pts = [
                (pp[(suite, c, "leftmost", k[3])]["nodes"], v["nodes"])
                for k, v in pp.items()
                if k[:3] == (suite, c, s) and v["solved"] and pp.get((suite, c, "leftmost", k[3]), {}).get("solved")
            ]
            if pts:
                drawn = True
                hi = max(hi, max(max(p) for p in pts) * 1.5)
                ax.scatter([p[0] for p in pts], [p[1] for p in pts], s=14, color=COLORS[s], alpha=0.6, label=s)
        ax.plot([1, hi], [1, hi], color="grey", linewidth=0.8)
        ax.set(title=title.format(c), xlabel="Κόμβοι, leftmost", ylabel="Κόμβοι, άλλη στρατηγική", xscale="log", yscale="log")
        ax.legend()
    _save(fig, out / f"scatter_{suite}.pdf", drawn)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--results", type=Path, default=Path("results/exp8"))
    ap.add_argument("--figures", type=Path, default=Path("report/figures"))
    args = ap.parse_args(argv)
    rows = load(args.results)
    if not rows:
        print(f"no result files under {args.results}", file=sys.stderr)
        return 1
    pp = per_problem(rows)
    _write_csv(args.results / "runs.csv", [dict(r) for r in rows])
    _write_csv(args.results / "summary.csv", summary(rows))
    pairs: list[dict[str, Any]] = []
    for suite, c in sorted({(r["suite"], r["component_size"]) for r in rows}):
        for a, b in itertools.combinations(reversed(_strategies(pp, suite, c)), 2):
            fewer, equal, more = paired(pp, suite, c, a, b)
            pairs.append({"suite": suite, "component_size": c, "a": a, "b": b,
                          "a_fewer_nodes": fewer, "equal": equal, "a_more_nodes": more})
    _write_csv(args.results / "paired.csv", pairs)
    args.figures.mkdir(parents=True, exist_ok=True)
    for suite in sorted({r["suite"] for r in rows}):
        _figures(pp, suite, args.figures)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
