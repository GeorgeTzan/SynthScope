import json
from dataclasses import asdict
from pathlib import Path

from experiments.analyze import Row, main, paired, per_problem, summary
from hope_engine.bench.runner import RunConfig, RunRecord


def row(
    strategy: str, seed: int | None, benchmark: str, status: str, nodes: int, seconds: float, size: int = 3, c: int = 1
) -> Row:
    return {
        "suite": "s", "component_size": c, "strategy": strategy, "seed": seed, "benchmark": benchmark,
        "status": status, "seconds": seconds, "nodes": nodes, "analyzer_calls": nodes, "meta_calls": 0,
        "analysis_seconds": seconds / 2, "meta_seconds": 0.0, "program_size": size if status == "solved" else None,
    }


def test_per_problem_needs_every_seed() -> None:
    rows = [row("random", 0, "a", "solved", 10, 1.0), row("random", 1, "a", "timeout", 0, 30.0),
            row("random", 0, "b", "solved", 10, 1.0), row("random", 1, "b", "solved", 30, 3.0)]
    pp = per_problem(rows)
    assert pp[("s", 1, "random", "a")]["solved"] is False
    assert pp[("s", 1, "random", "b")]["solved"] is True and pp[("s", 1, "random", "b")]["nodes"] == 20


def test_summary_uses_common_set_only() -> None:
    rows = [row("leftmost", None, "a", "solved", 100, 1.0), row("leftmost", None, "b", "solved", 999, 9.0),
            row("random", 0, "a", "solved", 50, 0.5), row("random", 0, "b", "timeout", 0, 30.0),
            row("meta", 0, "a", "solved", 20, 0.4), row("meta", 0, "b", "solved", 5, 0.1)]
    s = {d["strategy"]: d for d in summary(rows)}
    assert s["leftmost"]["common"] == 1 and s["leftmost"]["median_nodes"] == 100
    assert s["random"]["solved_mean"] == 1 and s["meta"]["solved_mean"] == 2
    assert s["meta"]["median_nodes"] == 20 and s["meta"]["analysis_share"] == 0.5


def test_solved_counts_over_seeds() -> None:
    rows = [row("random", 0, "a", "solved", 1, 1.0), row("random", 0, "b", "solved", 1, 1.0),
            row("random", 1, "a", "solved", 1, 1.0), row("random", 1, "b", "timeout", 0, 30.0)]
    s = summary(rows)[0]
    assert (s["problems"], s["solved_mean"], s["solved_min"], s["solved_max"]) == (2, 1.5, 1, 2)


def test_paired() -> None:
    rows = [row("leftmost", None, "a", "solved", 100, 1.0), row("meta", 0, "a", "solved", 20, 0.4),
            row("leftmost", None, "b", "solved", 7, 1.0), row("meta", 0, "b", "solved", 7, 0.4),
            row("leftmost", None, "c", "solved", 3, 1.0), row("meta", 0, "c", "timeout", 0, 30.0)]
    assert paired(per_problem(rows), "s", 1, "meta", "leftmost") == (1, 1, 0)


def test_nothing_solved_and_missing_strategy() -> None:
    rows = [row("leftmost", None, "a", "timeout", 0, 30.0), row("random", 0, "a", "crashed", 0, 32.0)]
    s = {d["strategy"]: d for d in summary(rows)}
    assert s["leftmost"]["common"] == 0 and s["leftmost"]["median_nodes"] is None
    assert "meta" not in s


def _write(path: Path, policy: str, seed: int, nodes: tuple[int, int]) -> None:
    cfg = RunConfig(policy, 1, 10**9, 30.0, seed, 1)
    recs = [
        RunRecord("a.sl", "solved", True, nodes[0], nodes[0], 0, 0.5, 3, "(bvnot x)", cfg, {}, 0.2, 0.1),
        RunRecord("b.sl", "solved", True, nodes[1], nodes[1], 0, 1.5, 5, "(bvadd x (bvnot y))", cfg, {}, 0.7, 0.2),
        RunRecord("c.sl", "timeout", False, 0, 0, 0, 32.0, None, None, cfg, {}),
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(asdict(r)) + "\n" for r in recs))


def test_main_end_to_end(tmp_path: Path) -> None:
    res, figs = tmp_path / "res", tmp_path / "figs"
    _write(res / "suite8" / "c1_leftmost.jsonl", "leftmost", 0, (40, 400))
    _write(res / "suite8" / "c1_meta_s0.jsonl", "hope", 0, (30, 100))
    assert main(["--results", str(res), "--figures", str(figs)]) == 0
    assert (res / "summary.csv").exists() and (res / "paired.csv").exists()
    lines = (res / "runs.csv").read_text().splitlines()
    assert len(lines) == 7 and "suite8,1,meta,0,b.sl,solved" in lines[5] + lines[4]
    for name in ("cactus_suite8.pdf", "nodes_by_size_suite8.pdf", "scatter_suite8.pdf"):
        assert (figs / name).stat().st_size > 0, name
