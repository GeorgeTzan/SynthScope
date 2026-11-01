"""Summaries and paired comparisons of benchmark records (no web dependencies)."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
from typing import Any

from hope_engine.bench.runner import RunRecord


def summarize(records: list[RunRecord]) -> dict[str, Any]:
    solved = [r for r in records if r.status == "solved"]
    return {
        "total": len(records),
        "solved": len(solved),
        "validated": sum(r.validated for r in records),
        "by_status": dict(Counter(r.status for r in records)),
        "mean_seconds_solved": sum(r.seconds for r in solved) / len(solved) if solved else None,
        "total_nodes": sum(r.nodes for r in records),
        "total_analyzer_calls": sum(r.analyzer_calls for r in records),
        "total_meta_calls": sum(r.meta_calls for r in records),
    }


def render_text(summary: dict[str, Any]) -> str:
    mean = summary["mean_seconds_solved"]
    return (
        f"solved {summary['solved']}/{summary['total']} (validated {summary['validated']}), "
        f"mean time on solved: {'n/a' if mean is None else f'{mean:.3f}s'}, "
        f"nodes {summary['total_nodes']}, analyzer calls {summary['total_analyzer_calls']}, "
        f"meta calls {summary['total_meta_calls']}, statuses {summary['by_status']}"
    )


def paired_csv(a: list[RunRecord], b: list[RunRecord], out: Path) -> None:
    """One row per benchmark present in both runs (paired comparison)."""
    bm = {r.benchmark: r for r in b}
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["benchmark", "status_a", "status_b", "seconds_a", "seconds_b", "nodes_a", "nodes_b"])
        for r in a:
            o = bm.get(r.benchmark)
            if o is not None:
                w.writerow([r.benchmark, r.status, o.status, f"{r.seconds:.6f}", f"{o.seconds:.6f}", r.nodes, o.nodes])
