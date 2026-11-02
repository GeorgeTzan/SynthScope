"""Run manager: each synthesis runs in a child process; events are collected by a reader thread."""

from __future__ import annotations

import multiprocessing as mp
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from hope_engine.bench.runner import RunConfig, build_search
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
    if pre is not None:
        pre()
    analyzer, policy = build_search(problem, config)
    window, count, dropped = time.monotonic(), 0, 0

    def sink(event: Event) -> None:
        nonlocal window, count, dropped
        if event.kind in NOISY:
            now = time.monotonic()
            if now - window >= 1.0:
                window, count = now, 0
            count += 1
            if count > MAX_NOISY_PER_SECOND:
                dropped += 1
                return
        conn.send(("event", event.seq, to_json(event)))

    r = search(problem, analyzer, policy, Budget(config.max_nodes, config.timeout_s), sink, run_id)
    conn.send(
        (
            "done",
            {
                "status": r.status,
                "nodes": r.nodes,
                "seconds": r.seconds,
                "program": pretty(r.program) if r.program is not None else None,
                "dropped": dropped,
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
