import json
from pathlib import Path

from experiments.run import configs, main

FIX = Path(__file__).parents[1] / "sygus" / "fixtures"


def test_configs() -> None:
    cs = configs()
    names = [n for n, _ in cs]
    assert len(cs) == 14 and len(set(names)) == 14
    assert dict(cs)["c1_meta_s2"] == ["--policy", "hope", "--holes", "1", "--seed", "2", "--component-size", "1"]
    assert dict(cs)["c3_random_s0"] == ["--policy", "meta_off", "--seed", "0", "--component-size", "3"]
    assert dict(cs)["c1_leftmost"] == ["--policy", "leftmost", "--component-size", "1"]


def test_run_and_resume(tmp_path: Path) -> None:
    suite = tmp_path / "suite"
    suite.mkdir()
    (suite / "bv.sl").write_text((FIX / "bv.sl").read_text())
    out = tmp_path / "out"
    args = [str(suite), "--out", str(out), "--timeout", "20", "--jobs", "2"]
    assert main(args) == 0
    files = sorted(out.glob("*.jsonl"))
    assert len(files) == 14
    assert all(json.loads(f.read_text().splitlines()[0])["status"] == "solved" for f in files)
    stamp = {f: f.stat().st_mtime_ns for f in files}
    assert main(args) == 0
    assert {f: f.stat().st_mtime_ns for f in files} == stamp
