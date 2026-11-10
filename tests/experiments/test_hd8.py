from pathlib import Path

import pytest

from experiments.hd8 import main, rewrite
from hope_engine.sygus.parser import parse_sygus

HD01 = """(set-logic BV)
(define-fun hd01 ((x (BitVec 64))) (BitVec 64) (bvand x (bvsub x #x0000000000000001)))
(synth-fun f ((x (BitVec 64))) (BitVec 64)
    ((Start (BitVec 64) ((bvand Start Start) (bvsub Start Start) x #x0000000000000000 #xFFFFFFFFFFFFFFFF #x0000000000000001))))
(declare-var x (BitVec 64))
(constraint (= (hd01 x) (f x)))
(check-synth)
"""


def test_rewrite_to_width_8() -> None:
    out = rewrite(HD01)
    assert "64" not in out and "#x01" in out and "#xFF" in out and "#x00" in out
    p = parse_sygus(out)
    assert p.width == 8 and p.spec is not None
    assert p.spec.output({"x": 0b1100}) == 0b1000


def test_main_writes_files(tmp_path: Path) -> None:
    src, out = tmp_path / "hd44", tmp_path / "hd8"
    src.mkdir()
    (src / "hd-01-d1-prog.sl").write_text(HD01)
    assert main(["--src", str(src), "--out", str(out)]) == 0
    assert (out / "hd-01-d1-prog.sl").read_text() == rewrite(HD01)


def test_missing_source(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--src", str(tmp_path / "nope"), "--out", str(tmp_path / "o")]) == 2
    assert "scripts/fetch_benchmarks.sh" in capsys.readouterr().err


def test_width_minus_one_constant_follows_the_width() -> None:
    assert rewrite("(bvashr x #x000000000000003F)") == "(bvashr x #x07)"
