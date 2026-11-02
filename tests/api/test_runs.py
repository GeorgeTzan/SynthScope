import json
import subprocess
import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.main import create_app
from apps.api.worker import RunManager

FIX = Path(__file__).parents[1] / "sygus" / "fixtures"
BV = (FIX / "bv.sl").read_text()
CFG = {"policy": "hope", "max_holes": 2, "max_nodes": 20000, "timeout_s": 30.0, "seed": 0}
RUNAWAY = (
    "(synth-fun f ((x (BitVec 8))) (BitVec 8) ((Start (BitVec 8) (x #x01 (bvadd Start Start) (bvmul Start Start)))))\n"
    "(constraint (= (f #x03) #x00))\n(constraint (= (f #x05) #x07))\n"
)


def start(client: TestClient, problem: str = BV, **cfg: object) -> str:
    r = client.post("/api/runs", json={"problem": problem, "config": {**CFG, **cfg}})
    assert r.status_code == 200, r.text
    return str(r.json()["run_id"])


def collect(client: TestClient, run_id: str) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    with client.websocket_connect(f"/api/runs/{run_id}/ws") as ws:
        while True:
            msg = json.loads(ws.receive_text())
            out.append(msg)
            if msg["kind"] == "run_finished":
                return out


def wait_status(client: TestClient, run_id: str, want: str, secs: float = 5.0) -> dict[str, object]:
    end = time.monotonic() + secs
    while time.monotonic() < end:
        st = client.get(f"/api/runs/{run_id}").json()
        if st["status"] == want:
            return st  # type: ignore[no-any-return]
        time.sleep(0.05)
    raise AssertionError(f"never reached {want}: {client.get(f'/api/runs/{run_id}').json()}")


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(RunManager()))


def test_run_streams_ordered_events_to_finish(client: TestClient) -> None:
    run_id = start(client)
    events = collect(client, run_id)
    seqs = [int(e["seq"]) for e in events]  # type: ignore[call-overload]
    assert seqs == sorted(seqs) and len(set(seqs)) == len(seqs)
    kinds = {e["kind"] for e in events}
    assert {"search_started", "hole_ranked", "solution_found", "run_finished"} <= kinds
    assert all(e["run_id"] == run_id and e["schema_version"] == 1 for e in events)
    st = wait_status(client, run_id, "solved")
    assert st["program"] is not None


def test_late_subscriber_gets_full_history(client: TestClient) -> None:
    run_id = start(client)
    first = collect(client, run_id)
    again = collect(client, run_id)
    assert [e["seq"] for e in first] == [e["seq"] for e in again]


def test_unknown_run_is_404(client: TestClient) -> None:
    assert client.get("/api/runs/nope").status_code == 404
    assert client.delete("/api/runs/nope").status_code == 404


def test_cancel_kills_runaway_run(client: TestClient) -> None:
    run_id = start(client, RUNAWAY, max_nodes=10**6, timeout_s=300.0)
    time.sleep(0.3)
    t0 = time.monotonic()
    assert client.delete(f"/api/runs/{run_id}").status_code == 200
    st = wait_status(client, run_id, "cancelled", 3.0)
    assert time.monotonic() - t0 < 2.5 and st["status"] == "cancelled"
    events = collect(client, run_id)
    assert events[-1]["kind"] == "run_finished" and events[-1]["payload"]["status"] == "cancelled"  # type: ignore[index]


def test_websocket_cancel_command(client: TestClient) -> None:
    run_id = start(client, RUNAWAY, max_nodes=10**6, timeout_s=300.0)
    with client.websocket_connect(f"/api/runs/{run_id}/ws") as ws:
        ws.send_text(json.dumps({"cmd": "cancel"}))
        while json.loads(ws.receive_text())["kind"] != "run_finished":
            pass
    assert wait_status(client, run_id, "cancelled", 3.0)


def test_cancel_twice_is_ok(client: TestClient) -> None:
    run_id = start(client, RUNAWAY, max_nodes=10**6, timeout_s=300.0)
    assert client.delete(f"/api/runs/{run_id}").status_code == 200
    assert client.delete(f"/api/runs/{run_id}").status_code == 200
    wait_status(client, run_id, "cancelled", 3.0)
    assert client.delete(f"/api/runs/{run_id}").status_code == 200


def test_cancel_after_finish_keeps_result(client: TestClient) -> None:
    run_id = start(client)
    wait_status(client, run_id, "solved")
    assert client.delete(f"/api/runs/{run_id}").status_code == 200
    assert client.get(f"/api/runs/{run_id}").json()["status"] == "solved"


def test_child_death_reports_error() -> None:
    def die() -> None:
        raise SystemExit(3)

    client = TestClient(create_app(RunManager(pre_hook=die)))
    run_id = start(client)
    events = collect(client, run_id)
    assert events[-1]["kind"] == "run_finished" and events[-1]["payload"]["status"] == "error"  # type: ignore[index]
    assert client.get(f"/api/runs/{run_id}").json()["status"] == "error"


def test_engine_imports_no_web() -> None:
    code = (
        "import sys, hope_engine.cli, hope_engine.bench.runner, hope_engine.trace.events;"
        "bad=[m for m in ('fastapi','starlette','uvicorn') if m in sys.modules];"
        "sys.exit(1 if bad else 0)"
    )
    assert subprocess.run([sys.executable, "-c", code], check=False).returncode == 0


SPEC = (
    "(set-logic BV)\n"
    "(define-fun hd01 ((x (BitVec 8))) (BitVec 8) (bvand x (bvsub x #x01)))\n"
    "(synth-fun f ((x (BitVec 8))) (BitVec 8)\n"
    "  ((Start (BitVec 8) ((bvand Start Start) (bvsub Start Start) (bvadd Start Start) x #x00 #x01))))\n"
    "(declare-var x (BitVec 8))\n(constraint (= (hd01 x) (f x)))\n"
)


def test_reference_function_runs_are_verified_by_z3(client: TestClient) -> None:
    events = collect(client, start(client, SPEC))
    kinds = [e["kind"] for e in events]
    seqs = [int(str(e["seq"])) for e in events]
    assert seqs == list(range(len(seqs))), "one gapless stream even across counterexample rounds"
    assert kinds.count("run_finished") == 1 and kinds[-1] == "run_finished"
    assert kinds.count("solution_found") == 1
    verified = [e for e in events if e["kind"] == "verified"]
    assert [e["payload"] for e in verified] == [{"verified": True}]
    assert kinds.index("solution_found") < kinds.index("verified") < kinds.index("run_finished")


def test_example_only_runs_carry_no_verification_event(client: TestClient) -> None:
    events = collect(client, start(client))
    assert "verified" not in {e["kind"] for e in events}


RARE = (
    "(set-logic BV)\n"
    "(define-fun rare ((x (BitVec 8))) (BitVec 8) (ite (= x #x37) #x01 #x00))\n"
    "(synth-fun f ((x (BitVec 8))) (BitVec 8)\n"
    "  ((Start (BitVec 8) (x #x00 #x01 #x37 (ite StartBool Start Start)))\n"
    "   (StartBool Bool ((= Start Start)))))\n"
    "(declare-var x (BitVec 8))\n(constraint (= (rare x) (f x)))\n"
)


def test_a_program_that_fits_the_samples_but_not_the_spec_is_refuted_and_the_search_continues(client: TestClient) -> None:
    events = collect(client, start(client, RARE))
    kinds = [e["kind"] for e in events]
    seqs = [int(str(e["seq"])) for e in events]
    assert seqs == list(range(len(seqs)))
    assert "counterexample" in kinds, "the constant 0 matches every sampled input but x = 0x37"
    assert kinds.count("solution_found") == 1 and kinds[-1] == "run_finished"
    assert [e["payload"] for e in events if e["kind"] == "verified"] == [{"verified": True}]
    assert events[-1]["payload"]["status"] == "solved"  # type: ignore[index]


def test_solved_run_streams_node_values_for_every_example(client: TestClient) -> None:
    events = collect(client, start(client))
    kinds = [e["kind"] for e in events]
    assert kinds.index("solution_found") < kinds.index("evaluation") < kinds.index("run_finished")
    payload = next(e["payload"] for e in events if e["kind"] == "evaluation")
    rows = payload["examples"]  # type: ignore[index]
    assert len(rows) == 2 and all("" in r["values"] for r in rows)
    assert all(r["values"][""] == r["expected"] for r in rows), "the root value is the program's output"
