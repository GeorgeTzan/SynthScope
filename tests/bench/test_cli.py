from pathlib import Path

import pytest

from hope_engine.bench.runner import load_records
from hope_engine.cli import main

FIX = Path(__file__).parents[1] / "sygus" / "fixtures"


def test_solve_prints_program(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["solve", str(FIX / "bv.sl"), "--policy", "hope"]) == 0
    out = capsys.readouterr().out
    assert "solved" in out and "(" in out


def test_solve_unsupported_returns_nonzero(tmp_path: Path) -> None:
    f = tmp_path / "u.sl"
    f.write_text(
        "(synth-fun f ((x (BitVec 4))) (BitVec 4) ((Start (BitVec 4) (x (bvcomp Start Start)))))\n"
        "(constraint (= (f #x1) #x2))\n"
    )
    assert main(["solve", str(f)]) == 2


def test_bench_then_report_and_compare(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    a, b = tmp_path / "a.jsonl", tmp_path / "b.jsonl"
    assert main(["bench", str(FIX), "--policy", "hope", "--holes", "3", "--out", str(a)]) == 0
    assert main(["bench", str(FIX), "--policy", "leftmost", "--out", str(b)]) == 0
    assert len(load_records(a)) == 2 and load_records(a)[0].config.max_holes == 3
    capsys.readouterr()
    assert main(["report", str(a), str(b)]) == 0
    assert capsys.readouterr().out.count("solved 2/2") == 2
    assert main(["compare", str(a), str(b), "--csv", str(tmp_path / "p.csv")]) == 0
    assert (tmp_path / "p.csv").read_text().count("\n") == 3


def _suite(tmp_path: Path, n: int) -> Path:
    d = tmp_path / "suite"
    d.mkdir()
    for i in range(n):
        (d / f"p{i:02d}.sl").write_text((FIX / "bv.sl").read_text())
    return d


def test_bench_limit_samples_the_same_files_for_the_same_seed(tmp_path: Path) -> None:
    d = _suite(tmp_path, 8)
    a, b, c = tmp_path / "a.jsonl", tmp_path / "b.jsonl", tmp_path / "c.jsonl"
    assert main(["bench", str(d), "--limit", "3", "--sample-seed", "1", "--out", str(a)]) == 0
    assert main(["bench", str(d), "--limit", "3", "--sample-seed", "1", "--policy", "leftmost", "--out", str(b)]) == 0
    assert main(["bench", str(d), "--limit", "3", "--sample-seed", "2", "--out", str(c)]) == 0
    names = [r.benchmark for r in load_records(a)]
    assert len(names) == 3 and names == [r.benchmark for r in load_records(b)]
    assert names != [r.benchmark for r in load_records(c)]


def test_bench_rejects_a_non_positive_limit(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        main(["bench", str(_suite(tmp_path, 2)), "--limit", "0", "--out", str(tmp_path / "x.jsonl")])
