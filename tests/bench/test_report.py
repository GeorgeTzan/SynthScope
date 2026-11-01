import csv
from pathlib import Path

from hope_engine.bench.report import paired_csv, render_text, summarize
from hope_engine.bench.runner import RunConfig, RunRecord

CFG = RunConfig("hope", 1, 10, 1.0, 0)


def rec(name: str, status: str, seconds: float = 1.0, nodes: int = 5) -> RunRecord:
    return RunRecord(name, status, status == "solved", nodes, nodes, 0, seconds, 3 if status == "solved" else None, None, CFG, {})  # type: ignore[arg-type]


def test_summarize_counts_and_means() -> None:
    s = summarize([rec("a", "solved", 1.0), rec("b", "solved", 3.0), rec("c", "timeout", 60.0), rec("d", "unsupported")])
    assert s["total"] == 4 and s["solved"] == 2 and s["validated"] == 2
    assert s["by_status"] == {"solved": 2, "timeout": 1, "unsupported": 1}
    assert s["mean_seconds_solved"] == 2.0


def test_summarize_empty() -> None:
    assert summarize([])["total"] == 0 and summarize([])["mean_seconds_solved"] is None


def test_paired_csv_only_common_benchmarks(tmp_path: Path) -> None:
    out = tmp_path / "p.csv"
    paired_csv([rec("a", "solved", 1.0), rec("b", "timeout", 9.0)], [rec("b", "solved", 2.0), rec("c", "solved")], out)
    rows = list(csv.DictReader(out.open()))
    assert [r["benchmark"] for r in rows] == ["b"]
    assert rows[0]["status_a"] == "timeout" and rows[0]["status_b"] == "solved"


def test_render_text_mentions_totals() -> None:
    assert "solved 1/2" in render_text(summarize([rec("a", "solved"), rec("b", "timeout")]))
