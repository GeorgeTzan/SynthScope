import random

import pytest

from experiments.gen_suite import (
    SuiteError,
    fingerprint,
    make_suite,
    random_program,
    to_sygus,
)
from hope_engine.concrete.verify import satisfies
from hope_engine.sygus.parser import parse_sygus
from hope_engine.syntax.ast import Var, size


def test_random_program_has_exact_size() -> None:
    rng = random.Random(1)
    for s in (1, 2, 3, 5, 7, 9):
        assert all(size(random_program(rng, s)) == s for _ in range(50))


def test_suite_is_deterministic_and_filtered() -> None:
    a = make_suite(seed=0, sizes=(3, 5), per_size=5)
    assert a == make_suite(seed=0, sizes=(3, 5), per_size=5)
    assert [n for n, _, _ in a] == [f"s{s}_{i:02d}" for s in (3, 5) for i in range(5)]
    prints = [fingerprint(t) for _, t, _ in a]
    assert len(set(prints)) == len(prints)
    assert all(len(set(p)) > 1 and p not in (fingerprint(Var("x")), fingerprint(Var("y"))) for p in prints)
    assert all(size(t) == int(n[1]) and len(ex) == 6 for n, t, ex in a)


def test_other_seed_gives_other_suite() -> None:
    assert make_suite(seed=1, sizes=(5,), per_size=5) != make_suite(seed=0, sizes=(5,), per_size=5)


def test_sygus_round_trip() -> None:
    name, target, examples = make_suite(seed=0, sizes=(5,), per_size=1)[0]
    p = parse_sygus(to_sygus(name, target, examples, 0))
    assert p.domain == "bv" and p.width == 8 and len(p.examples) == 6
    assert satisfies(target, p.examples, 8)


def test_impossible_request_raises() -> None:
    with pytest.raises(SuiteError, match="size 1"):
        make_suite(seed=0, sizes=(1,), per_size=25, max_tries=500)


def test_main_replaces_only_its_own_files(tmp_path) -> None:  # type: ignore[no-untyped-def]
    from experiments.gen_suite import main

    other, stale = tmp_path / "hd-01.sl", tmp_path / "s3_99.sl"
    other.write_text("keep")
    stale.write_text("old")
    assert main(["--out", str(tmp_path), "--per-size", "2"]) == 0
    assert other.read_text() == "keep" and not stale.exists()
    assert len(list(tmp_path.glob("s*_*.sl"))) == 8
