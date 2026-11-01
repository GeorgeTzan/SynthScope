"""Reproducible benchmark runs: one child process per problem, JSONL records with environment metadata."""

from __future__ import annotations

import json
import multiprocessing as mp
import platform
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from hope_engine.concrete.bitvector import UnsupportedOperator
from hope_engine.concrete.verify import Example, satisfies
from hope_engine.domains.analysis import DomainAnalyzer
from hope_engine.domains.bitvector.ops import BitvectorDomain
from hope_engine.domains.string.ops import StringDomain
from hope_engine.enumeration.search import (
    AnalysisResult,
    Analyzer,
    Budget,
    HolePolicy,
    LeftmostPolicy,
    PickContext,
    Problem,
    search,
)
from hope_engine.meta.bitvector import BitvectorMeta
from hope_engine.meta.policies import HopePolicy, MetaOffPolicy
from hope_engine.meta.string import StringMeta
from hope_engine.sygus.parser import SygusError, load_problem
from hope_engine.syntax.ast import Node, pretty, size
from hope_engine.syntax.ast import Path as TreePath

Status = Literal["solved", "exhausted", "timeout", "unsupported", "invalid", "crashed"]
KILL_GRACE_S = 2.0


@dataclass(frozen=True)
class RunConfig:
    policy: Literal["hope", "leftmost", "meta_off"]
    max_holes: int
    max_nodes: int
    timeout_s: float
    seed: int


@dataclass(frozen=True)
class RunRecord:
    benchmark: str
    status: Status
    validated: bool
    nodes: int
    analyzer_calls: int
    meta_calls: int
    seconds: float
    program_size: int | None
    program: str | None
    config: RunConfig
    env: dict[str, str]


def validate(program: Node, examples: tuple[Example, ...], width: int | None) -> bool:
    """Independent re-check of a returned solution (separate from the search's own acceptance test)."""
    return satisfies(program, examples, width)


class _CountingAnalyzer:
    def __init__(self, inner: Analyzer) -> None:
        self.inner, self.calls = inner, 0

    def analyze(self, partial: Node, examples: tuple[Example, ...]) -> AnalysisResult:
        self.calls += 1
        return self.inner.analyze(partial, examples)

    def compatible(
        self, result: AnalysisResult, partial: Node, pos: TreePath, component: Node, examples: tuple[Example, ...]
    ) -> bool:
        return self.inner.compatible(result, partial, pos, component, examples)


class _CountingPolicy:
    def __init__(self, inner: HolePolicy) -> None:
        self.inner, self.calls = inner, 0

    def pick(self, partial: Node, ctx: PickContext) -> tuple[tuple[TreePath, ...], bool]:
        self.calls += 1
        return self.inner.pick(partial, ctx)


def _git_sha() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True)
        return out.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _cpu() -> str:
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or "unknown"


def environment() -> dict[str, str]:
    import z3

    return {
        "python": sys.version.split()[0],
        "z3": z3.get_version_string(),
        "platform": platform.platform(),
        "cpu": _cpu(),
        "git_sha": _git_sha(),
    }


def _work(problem: Problem, config: RunConfig, pre: Callable[[], None] | None) -> dict[str, Any]:
    if pre is not None:
        pre()
    bv = problem.domain == "bv"
    assert not bv or problem.width is not None
    base: Analyzer = (
        DomainAnalyzer(BitvectorDomain(problem.width or 1)) if bv else DomainAnalyzer(StringDomain())
    )
    analyzer = _CountingAnalyzer(base)
    meta: Any = BitvectorMeta() if bv else StringMeta()
    inner: HolePolicy
    if config.policy == "hope":
        inner = HopePolicy(meta, config.seed, config.max_holes)
    elif config.policy == "meta_off":
        inner = MetaOffPolicy(config.seed)
    else:
        inner = LeftmostPolicy()
    policy = _CountingPolicy(inner)
    r = search(problem, analyzer, policy, Budget(config.max_nodes, config.timeout_s))
    status: Status = r.status
    validated = False
    if r.program is not None:
        validated = validate(r.program, problem.examples, problem.width)
        if not validated:
            status = "invalid"
    return {
        "status": status,
        "validated": validated,
        "nodes": r.nodes,
        "analyzer_calls": analyzer.calls,
        "meta_calls": policy.calls if config.policy == "hope" else 0,
        "seconds": r.seconds,
        "program": pretty(r.program) if r.program is not None else None,
        "program_size": size(r.program) if r.program is not None else None,
    }


def _child(conn: Any, problem: Problem, config: RunConfig, pre: Callable[[], None] | None) -> None:
    conn.send(_work(problem, config, pre))
    conn.close()


def run_problem(
    problem: Problem, name: str, config: RunConfig, pre: Callable[[], None] | None = None
) -> RunRecord:
    """Run one problem in a child process; kill it if it overruns the timeout plus a grace period."""
    ctx = mp.get_context("fork")
    parent, child = ctx.Pipe(duplex=False)
    proc = ctx.Process(target=_child, args=(child, problem, config, pre))
    start = time.monotonic()
    proc.start()
    child.close()
    data: dict[str, Any] | None = None
    if parent.poll(config.timeout_s + KILL_GRACE_S):
        try:
            data = parent.recv()
        except EOFError:
            data = None
    if proc.is_alive():
        proc.kill()
    proc.join()
    elapsed = time.monotonic() - start
    env = environment()
    if data is not None:
        return RunRecord(name, data["status"], data["validated"], data["nodes"], data["analyzer_calls"],
                         data["meta_calls"], data["seconds"], data["program_size"], data["program"], config, env)
    status: Status = "timeout" if elapsed >= config.timeout_s + KILL_GRACE_S else "crashed"
    return RunRecord(name, status, False, 0, 0, 0, elapsed, None, None, config, env)


def run_file(path: Path, config: RunConfig) -> RunRecord:
    try:
        problem = load_problem(path)
    except (UnsupportedOperator, SygusError):
        return RunRecord(path.name, "unsupported", False, 0, 0, 0, 0.0, None, None, config, environment())
    return run_problem(problem, path.name, config)


def run_suite(paths: Sequence[Path], config: RunConfig, out: Path) -> list[RunRecord]:
    out.parent.mkdir(parents=True, exist_ok=True)
    records: list[RunRecord] = []
    with out.open("w", encoding="utf-8") as fh:
        for p in paths:
            rec = run_file(p, config)
            records.append(rec)
            fh.write(json.dumps(asdict(rec), sort_keys=True) + "\n")
            fh.flush()
    return records


def load_records(path: Path) -> list[RunRecord]:
    out: list[RunRecord] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        d = json.loads(line)
        d["config"] = RunConfig(**d["config"])
        out.append(RunRecord(**d))
    return out


