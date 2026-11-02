import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.main import create_app
from apps.api.worker import RunManager
from hope_engine.bench.runner import RunConfig, RunRecord

FIX = Path(__file__).parents[1] / "sygus" / "fixtures"


def record(name: str, status: str, nodes: int = 10, seconds: float = 1.0) -> str:
    cfg = RunConfig("hope", 3, 1000, 5.0, 0)
    rec = RunRecord(name, status, status == "solved", nodes, nodes, 0, seconds, 3, None, cfg, {})  # type: ignore[arg-type]
    from dataclasses import asdict

    return json.dumps(asdict(rec))


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    bench = tmp_path / "benchmarks"
    (bench / "bvset").mkdir(parents=True)
    (bench / "bvset" / "b.sl").write_text((FIX / "bv.sl").read_text())
    (bench / "bvset" / "a.sl").write_text((FIX / "bv.sl").read_text())
    (bench / "notes.txt").write_text("not a corpus")
    res = tmp_path / "results" / "bvset"
    res.mkdir(parents=True)
    (res / "hope_h3.jsonl").write_text("\n".join([record("a.sl", "solved"), record("b.sl", "timeout")]) + "\n")
    return TestClient(create_app(RunManager(), tmp_path / "benchmarks", tmp_path / "results"))


def test_lists_corpora_and_sorted_files(client: TestClient) -> None:
    body = client.get("/api/benchmarks").json()
    assert body == {"corpora": {"bvset": ["a.sl", "b.sl"]}}


def test_returns_one_problem_text(client: TestClient) -> None:
    r = client.get("/api/benchmarks/bvset/a.sl")
    assert r.status_code == 200 and r.json()["text"] == (FIX / "bv.sl").read_text()


@pytest.mark.parametrize("path", ["bvset/missing.sl", "nope/a.sl", "bvset/..%2Fnotes.txt", "..%2F/notes.txt"])
def test_unknown_or_escaping_names_are_not_found(client: TestClient, path: str) -> None:
    assert client.get(f"/api/benchmarks/{path}").status_code == 404


def test_results_summary_per_corpus_and_config(client: TestClient) -> None:
    rows = client.get("/api/results").json()["results"]
    assert rows == [
        {
            "corpus": "bvset",
            "config": "hope_h3",
            "total": 2,
            "solved": 1,
            "validated": 1,
            "mean_seconds_solved": 1.0,
            "total_nodes": 20,
        }
    ]


def test_missing_directories_give_empty_lists(tmp_path: Path) -> None:
    c = TestClient(create_app(RunManager(), tmp_path / "none", tmp_path / "nothing"))
    assert c.get("/api/benchmarks").json() == {"corpora": {}}
    assert c.get("/api/results").json() == {"results": []}
