import json
import time
from pathlib import Path

import pytest

from hope_engine.bench import runner
from hope_engine.bench.runner import RunConfig, run_file, run_suite
from hope_engine.sygus.parser import load_problem

FIX = Path(__file__).parents[1] / "sygus" / "fixtures"
BV, STR = FIX / "bv.sl", FIX / "string.sl"
CFG = RunConfig(policy="hope", max_holes=1, max_nodes=20000, timeout_s=30.0, seed=0)


def test_solved_and_validated_bv() -> None:
    r = run_file(BV, CFG)
    assert r.status == "solved" and r.validated and r.program is not None
    assert r.nodes > 0 and r.analyzer_calls > 0 and r.program_size is not None


def test_solved_and_validated_string_with_every_policy() -> None:
    for pol in ("hope", "leftmost", "meta_off"):
        r = run_file(STR, RunConfig(pol, 1, 20000, 30.0, 0))
        assert r.status == "solved" and r.validated, pol


def test_hope_counts_meta_calls_and_leftmost_does_not() -> None:
    assert run_file(BV, CFG).meta_calls > 0
    assert run_file(BV, RunConfig("leftmost", 1, 20000, 30.0, 0)).meta_calls == 0


def test_exhausted_by_node_cap() -> None:
    r = run_file(BV, RunConfig("leftmost", 1, 3, 30.0, 0))
    assert r.status == "exhausted" and r.nodes == 3 and not r.validated


def test_cooperative_timeout_status() -> None:
    r = run_file(BV, RunConfig("leftmost", 1, 10**9, 0.0, 0))
    assert r.status == "timeout"


def test_hard_kill_of_stalled_child() -> None:
    t0 = time.monotonic()
    r = runner.run_problem(load_problem(BV), "stall", RunConfig("hope", 1, 10**6, 0.3, 0), pre=lambda: time.sleep(60))
    assert r.status == "timeout" and time.monotonic() - t0 < 10


def test_crashed_child_is_reported() -> None:
    def boom() -> None:
        raise SystemExit(3)

    r = runner.run_problem(load_problem(BV), "boom", CFG, pre=boom)
    assert r.status == "crashed"


def test_unsupported_operator(tmp_path: Path) -> None:
    f = tmp_path / "u.sl"
    f.write_text(
        "(synth-fun f ((x (BitVec 4))) (BitVec 4) ((Start (BitVec 4) (x (bvcomp Start Start)))))\n"
        "(constraint (= (f #x1) #x2))\n"
    )
    r = run_file(f, CFG)
    assert r.status == "unsupported" and not r.validated


def test_invalid_if_independent_validation_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runner, "validate", lambda program, examples, width: False)
    r = run_file(BV, CFG)
    assert r.status == "invalid" and not r.validated


def test_jsonl_has_environment_metadata(tmp_path: Path) -> None:
    out = tmp_path / "r.jsonl"
    recs = run_suite([BV, STR], CFG, out)
    rows = [json.loads(line) for line in out.read_text().splitlines()]
    assert len(rows) == len(recs) == 2
    for row in rows:
        assert {"python", "z3", "platform", "cpu", "git_sha"} <= set(row["env"])
        assert row["config"]["seed"] == 0 and row["config"]["timeout_s"] == 30.0
        assert {"benchmark", "status", "validated", "nodes", "seconds"} <= set(row)


def test_same_seed_same_record() -> None:
    a, b = run_file(STR, CFG), run_file(STR, CFG)
    assert (a.program, a.nodes, a.analyzer_calls, a.meta_calls) == (b.program, b.nodes, b.analyzer_calls, b.meta_calls)


class _IdentityOracle:
    """Reference function f(x) = x. Any program other than the variable x has a counterexample."""

    def output(self, inputs: dict[str, int]) -> int:
        return inputs["x"]

    def counterexample(self, program: object) -> dict[str, int] | None:
        from hope_engine.syntax.ast import Var

        return None if program == Var("x") else {"x": 5}


def test_spec_problem_adds_counterexamples_until_verified() -> None:
    from hope_engine.concrete.verify import Example
    from hope_engine.enumeration.search import Problem
    from hope_engine.syntax.ast import Const, Var
    from hope_engine.syntax.grammar import Grammar, Production

    g = Grammar((Production("S", Const(0, "bv")), Production("S", Var("x"))), "S")
    p = Problem(g, (Example({"x": 0}, 0),), "bv", 4, _IdentityOracle())
    r = runner.run_problem(p, "id", CFG)
    assert r.status == "solved" and r.validated and r.program == "x"


def test_spec_problem_that_cannot_be_verified_is_not_solved() -> None:
    from hope_engine.concrete.verify import Example
    from hope_engine.enumeration.search import Problem
    from hope_engine.syntax.ast import Const
    from hope_engine.syntax.grammar import Grammar, Production

    g = Grammar((Production("S", Const(0, "bv")),), "S")  # x is not expressible
    p = Problem(g, (Example({"x": 0}, 0),), "bv", 4, _IdentityOracle())
    r = runner.run_problem(p, "id", CFG)
    assert r.status != "solved" and not r.validated
