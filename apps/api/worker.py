"""Run manager: each synthesis runs in a child process; events are collected by a reader thread."""

from __future__ import annotations

import multiprocessing as mp
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from typing import Any

from hope_engine.bench.runner import MAX_CEGIS_ROUNDS, RunConfig, build_search
from hope_engine.concrete.trace import node_values
from hope_engine.concrete.verify import Example
from hope_engine.enumeration.search import Budget, Problem, search
from hope_engine.syntax.ast import pretty
from hope_engine.trace.events import Event, to_json

KILL_GRACE_S = 2.0
NOISY = {"candidate_expanded", "pruned", "hole_filled", "hole_ranked", "analysis"}
MAX_NOISY_PER_SECOND = 300


class TooManyRuns(Exception):
    pass


@dataclass
class Run:
    run_id: str
    config: RunConfig
    proc: Any = None
    status: str = "running"
    events: list[str] = field(default_factory=list)
    result: dict[str, Any] = field(default_factory=dict)
    cancel_requested: bool = False
    finished: bool = False
    last_seq: int = -1
    started: float = field(default_factory=time.monotonic)


def _child(conn: Any, problem: Problem, config: RunConfig, run_id: str, pre: Callable[[], None] | None) -> None:
    """Search, then (for reference-function problems) verify with Z3 and retry with each counterexample as a new example.

    One continuous event stream: later rounds are renumbered and offset in time and candidate ids, and the closing
    solution_found / run_finished events are held back until the program is verified.
    """
    if pre is not None:
        pre()
    started = time.monotonic()
    window, count, dropped = started, 0, 0
    seq, id_base, nodes = 0, 0, 0
    current = problem
    verified: bool | None = None
    final: dict[str, Any] | None = None

    def emit(kind: str, payload: dict[str, object], t: float) -> None:
        nonlocal seq
        conn.send(("event", seq, to_json(Event(run_id, seq, kind, payload, round(t, 4)))))
        seq += 1

    for round_no in range(MAX_CEGIS_ROUNDS + 1):
        round_start = time.monotonic() - started
        max_id = -1

        def sink(event: Event, round_start: float = round_start, base: int = id_base) -> None:
            nonlocal window, count, dropped, max_id
            if event.kind in ("solution_found", "run_finished"):
                return  # re-emitted once the program is verified
            if event.kind in NOISY:
                now = time.monotonic()
                if now - window >= 1.0:
                    window, count = now, 0
                count += 1
                if count > MAX_NOISY_PER_SECOND:
                    dropped += 1
                    return
            payload = dict(event.payload)
            if event.kind == "candidate_expanded":
                cid, parent = payload.get("id"), payload.get("parent")
                if isinstance(cid, int):
                    max_id = max(max_id, cid)
                    payload["id"] = cid + base
                if isinstance(parent, int):
                    payload["parent"] = parent + base
            emit(event.kind, payload, round_start + event.t)

        analyzer, policy = build_search(current, config)
        remaining = None if config.timeout_s is None else max(config.timeout_s - (time.monotonic() - started), 0.001)
        r = search(current, analyzer, policy, Budget(max(config.max_nodes - nodes, 1), remaining), sink, run_id)
        nodes += r.nodes
        id_base += max_id + 1
        now = time.monotonic() - started
        if r.program is None or problem.spec is None:
            final = {"status": r.status, "program": r.program}
            break
        try:
            cex = problem.spec.counterexample(r.program)
        except TimeoutError:
            cex, verified = None, False  # the verifier gave up: report the program, but not as verified
        else:
            if cex is None:
                verified = True
        if cex is None:
            final = {"status": r.status, "program": r.program}
            break
        emit("counterexample", {"program": pretty(r.program), "inputs": {k: v for k, v in cex.items()}}, now)
        current = replace(current, examples=(*current.examples, Example(dict(cex), problem.spec.output(cex))))
    now = time.monotonic() - started
    if final is None:  # still refuted after the last round
        final = {"status": "exhausted", "program": None}
    program = final["program"]
    if program is not None:
        emit("solution_found", {"program": pretty(program)}, now)
        emit("evaluation", {"examples": node_values(program, current.examples, problem.width)}, now)
        if problem.spec is not None:
            emit("verified", {"verified": bool(verified)}, now)
    emit("run_finished", {"status": final["status"], "nodes": nodes}, now)
    conn.send(
        (
            "done",
            {
                "status": final["status"],
                "nodes": nodes,
                "seconds": now,
                "program": pretty(program) if program is not None else None,
                "dropped": dropped,
                "verified": verified if problem.spec is not None and program is not None else None,
            },
        )
    )
    conn.close()


class RunManager:
    def __init__(self, pre_hook: Callable[[], None] | None = None, max_running: int = 4) -> None:
        self._pre_hook = pre_hook
        self._max_running = max_running
        self._runs: dict[str, Run] = {}
        self._lock = threading.Lock()

    def get(self, run_id: str) -> Run | None:
        return self._runs.get(run_id)

    def _running(self) -> int:
        return sum(1 for r in self._runs.values() if not r.finished)

    def start(self, problem: Problem, config: RunConfig) -> Run:
        with self._lock:
            if self._running() >= self._max_running:
                raise TooManyRuns
            run = Run(uuid.uuid4().hex[:12], config)
            self._runs[run.run_id] = run
            ctx = mp.get_context("fork")
            parent, child = ctx.Pipe(duplex=False)
            run.proc = ctx.Process(target=_child, args=(child, problem, config, run.run_id, self._pre_hook), daemon=True)
            run.proc.start()
            child.close()
        threading.Thread(target=self._pump, args=(run, parent), daemon=True).start()
        return run

    def cancel(self, run_id: str) -> bool:
        run = self._runs.get(run_id)
        if run is None:
            return False
        if not run.finished:
            run.cancel_requested = True
            if run.proc is not None and run.proc.is_alive():
                run.proc.kill()
        return True

    def _pump(self, run: Run, conn: Any) -> None:
        deadline = run.started + run.config.timeout_s + KILL_GRACE_S
        done: dict[str, Any] | None = None
        while done is None:
            try:
                if conn.poll(0.05):
                    msg = conn.recv()
                    if msg[0] == "event":
                        run.last_seq = msg[1]
                        run.events.append(msg[2])
                    else:
                        done = msg[1]
                    continue
            except (EOFError, OSError):
                break
            if not run.proc.is_alive() and not conn.poll(0):
                break
            if time.monotonic() > deadline:
                run.proc.kill()
                break
        run.proc.join(1.0)
        if done is not None:
            run.result, run.status = done, done["status"]
        else:
            run.status = "cancelled" if run.cancel_requested else ("timeout" if time.monotonic() > deadline else "error")
            run.events.append(
                to_json(Event(run.run_id, run.last_seq + 1, "run_finished", {"status": run.status, "nodes": 0}))
            )
        run.finished = True
