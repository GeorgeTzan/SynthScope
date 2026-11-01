from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.main import create_app
from apps.api.worker import RunManager

FIX = Path(__file__).parents[1] / "sygus" / "fixtures"
BV = (FIX / "bv.sl").read_text()
CFG = {"policy": "hope", "max_holes": 2, "max_nodes": 1000, "timeout_s": 5.0, "seed": 0}


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(RunManager()))


def post(client: TestClient, problem: str, **cfg: object) -> int:
    r = client.post("/api/runs", json={"problem": problem, "config": {**CFG, **cfg}})
    return int(r.status_code)


def test_oversized_grammar_rejected(client: TestClient) -> None:
    alts = " ".join(f"#x{i % 16:x}" for i in range(400))
    big = f"(synth-fun f ((x (BitVec 4))) (BitVec 4) ((Start (BitVec 4) (x {alts}))))\n(constraint (= (f #x1) #x2))"
    assert post(client, big) == 422


def test_oversized_text_rejected(client: TestClient) -> None:
    assert post(client, BV + " " * 100_000) == 422


def test_too_many_examples_rejected(client: TestClient) -> None:
    cons = "\n".join(f"(constraint (= (f #x{i % 16:x}) #x{i % 16:x}))" for i in range(80))
    head = "(synth-fun f ((x (BitVec 4))) (BitVec 4) ((Start (BitVec 4) (x #x1))))\n"
    assert post(client, head + cons) == 422


def test_wide_bitvectors_rejected(client: TestClient) -> None:
    wide = "(synth-fun f ((x (BitVec 128))) (BitVec 128) ((Start (BitVec 128) (x))))\n(constraint (= (f #x1) #x1))"
    assert post(client, wide) == 422


def test_malformed_and_unsupported_rejected(client: TestClient) -> None:
    assert post(client, "(synth-fun f") == 422
    bad = (
        "(synth-fun f ((x (BitVec 4))) (BitVec 4) ((Start (BitVec 4) (x (bvcomp Start Start)))))\n"
        "(constraint (= (f #x1) #x2))"
    )
    assert post(client, bad) == 422


@pytest.mark.parametrize(
    "cfg",
    [{"max_nodes": 10**9}, {"timeout_s": 10_000.0}, {"max_holes": 50}, {"policy": "nope"}, {"timeout_s": -1.0}],
)
def test_config_limits(client: TestClient, cfg: dict[str, object]) -> None:
    assert post(client, BV, **cfg) == 422


def test_concurrency_limit() -> None:
    client = TestClient(create_app(RunManager(max_running=1)))
    runaway = (
        "(synth-fun f ((x (BitVec 8))) (BitVec 8) ((Start (BitVec 8) (x #x01 (bvadd Start Start) (bvmul Start Start)))))\n"
        "(constraint (= (f #x03) #x00))\n(constraint (= (f #x05) #x07))\n"
    )
    big = {**CFG, "max_nodes": 10**6, "timeout_s": 60.0}
    r1 = client.post("/api/runs", json={"problem": runaway, "config": big})
    assert r1.status_code == 200
    assert client.post("/api/runs", json={"problem": runaway, "config": big}).status_code == 429
    client.delete(f"/api/runs/{r1.json()['run_id']}")
