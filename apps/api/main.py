"""HTTP + websocket API. Run with: uvicorn apps.api.main:app"""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from apps.api.worker import RunManager, TooManyRuns
from hope_engine.bench.report import summarize
from hope_engine.bench.runner import RunConfig, load_records
from hope_engine.concrete.bitvector import UnsupportedOperator
from hope_engine.enumeration.search import Problem
from hope_engine.sygus.parser import SygusError, parse_sygus

MAX_PRODUCTIONS = 200
MAX_EXAMPLES = 50
MAX_WIDTH = 64


class ConfigModel(BaseModel):
    policy: Literal["hope", "leftmost", "meta_off"] = "hope"
    max_holes: int = Field(1, ge=1, le=5)
    max_nodes: int = Field(100_000, ge=1, le=1_000_000)
    timeout_s: float = Field(60.0, gt=0, le=300)
    seed: int = 0


class RunRequest(BaseModel):
    problem: str = Field(max_length=20_000)
    config: ConfigModel


def _parse(text: str) -> Problem:
    try:
        problem = parse_sygus(text)
    except SygusError as e:
        raise HTTPException(422, f"invalid problem: {e}") from e
    except UnsupportedOperator as e:
        raise HTTPException(422, f"unsupported operator: {e}") from e
    if len(problem.grammar.productions) > MAX_PRODUCTIONS:
        raise HTTPException(422, f"grammar has more than {MAX_PRODUCTIONS} productions")
    if len(problem.examples) > MAX_EXAMPLES:
        raise HTTPException(422, f"more than {MAX_EXAMPLES} examples")
    if problem.width is not None and problem.width > MAX_WIDTH:
        raise HTTPException(422, f"bitvector width above {MAX_WIDTH}")
    return problem


def _natural(name: str) -> list[object]:
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", name)]


def _corpora(root: Path) -> dict[str, list[str]]:
    if not root.is_dir():
        return {}
    out = {d.name: sorted((f.name for f in d.glob("*.sl")), key=_natural) for d in sorted(root.iterdir()) if d.is_dir()}
    return {k: v for k, v in out.items() if v}


def create_app(
    manager: RunManager | None = None,
    bench_dir: Path = Path("benchmarks"),
    results_dir: Path = Path("results"),
) -> FastAPI:
    mgr = manager or RunManager()
    app = FastAPI(title="SynthScope API")

    @app.get("/api/benchmarks")
    def list_benchmarks() -> dict[str, dict[str, list[str]]]:
        return {"corpora": _corpora(bench_dir)}

    @app.get("/api/benchmarks/{corpus}/{name}")
    def get_benchmark(corpus: str, name: str) -> dict[str, str]:
        # only names that appear in the directory listing are served, so a path can never leave the corpus folder
        if name not in _corpora(bench_dir).get(corpus, []):
            raise HTTPException(404, "unknown benchmark")
        return {"text": (bench_dir / corpus / name).read_text(encoding="utf-8")}

    @app.get("/api/results")
    def results() -> dict[str, list[dict[str, object]]]:
        rows: list[dict[str, object]] = []
        for f in sorted(results_dir.glob("*/*.jsonl")) if results_dir.is_dir() else []:
            s = summarize(load_records(f))
            rows.append(
                {
                    "corpus": f.parent.name,
                    "config": f.stem,
                    "total": s["total"],
                    "solved": s["solved"],
                    "validated": s["validated"],
                    "mean_seconds_solved": s["mean_seconds_solved"],
                    "total_nodes": s["total_nodes"],
                }
            )
        return {"results": rows}

    @app.post("/api/runs")
    def create_run(req: RunRequest) -> dict[str, str]:
        problem = _parse(req.problem)
        c = req.config
        try:
            run = mgr.start(problem, RunConfig(c.policy, c.max_holes, c.max_nodes, c.timeout_s, c.seed))
        except TooManyRuns as e:
            raise HTTPException(429, "too many concurrent runs") from e
        return {"run_id": run.run_id}

    @app.get("/api/runs/{run_id}")
    def get_run(run_id: str) -> dict[str, object]:
        run = mgr.get(run_id)
        if run is None:
            raise HTTPException(404, "unknown run")
        return {
            "run_id": run.run_id,
            "status": run.status,
            "events": len(run.events),
            "nodes": run.result.get("nodes"),
            "program": run.result.get("program"),
            "dropped": run.result.get("dropped"),
        }

    @app.delete("/api/runs/{run_id}")
    def cancel_run(run_id: str) -> dict[str, str]:
        if not mgr.cancel(run_id):
            raise HTTPException(404, "unknown run")
        return {"run_id": run_id, "status": "cancelling"}

    @app.websocket("/api/runs/{run_id}/ws")
    async def stream(ws: WebSocket, run_id: str) -> None:
        run = mgr.get(run_id)
        if run is None:
            await ws.close(code=4404)
            return
        await ws.accept()

        async def listen() -> None:
            try:
                while True:
                    msg = json.loads(await ws.receive_text())
                    if isinstance(msg, dict) and msg.get("cmd") == "cancel":
                        mgr.cancel(run_id)
            except (WebSocketDisconnect, ValueError, RuntimeError):
                return

        listener = asyncio.create_task(listen())
        sent = 0
        try:
            while True:
                while sent < len(run.events):
                    await ws.send_text(run.events[sent])
                    sent += 1
                if run.finished and sent >= len(run.events):
                    break
                await asyncio.sleep(0.02)
            await ws.close()
        except (WebSocketDisconnect, RuntimeError):
            pass
        finally:
            listener.cancel()

    return app


app = create_app()
