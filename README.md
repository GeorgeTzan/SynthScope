# SynthScope

An independent Python reimplementation of **HOPE** (Lee, Lee & Yi, *Inductive Program Synthesis by Meta-Analysis-Guided
Hole Filling*, POPL 2026; `docs/paper.pdf`) for bitvectors and strings, plus an extra SvelteKit 5 dashboard that shows
a run live. The engine is the deliverable; the dashboard only draws events the engine emitted.

## Setup

```bash
uv venv --python 3.12 .venv && uv pip install -p .venv/bin/python -e '.[dev]'
.venv/bin/pytest -q                     # engine, API tests
cd apps/web && npm install && npx vitest run
```

## Use

```bash
.venv/bin/python -m hope_engine.cli solve tests/sygus/fixtures/bv.sl --policy hope --holes 3
.venv/bin/python -m hope_engine.cli bench tests/sygus/fixtures --policy leftmost --out results/leftmost.jsonl
scripts/run_paper_ablations.sh tests/sygus/fixtures 30 20000          # PYTHON=.venv/bin/python
.venv/bin/python -m hope_engine.cli report results/*.jsonl
```

Real corpora (not committed, GPL): `scripts/fetch_benchmarks.sh`, then e.g.
`scripts/run_paper_ablations.sh duet 20 50000 24 0` (dir, timeout s, node cap, sample size, seed). Results: `results/README.md`.
Hacker's Delight problems are checked with Z3 at run time.

Dashboard: `.venv/bin/uvicorn apps.api.main:app --port 8000`, then `cd apps/web && npm run dev`
(set `API_URL=http://localhost:PORT` if the API is on another port).

## Layout

`src/hope_engine/` engine (no web imports) · `apps/api` FastAPI + websocket · `apps/web` SvelteKit 5 ·
`research/` paper audit and deviations · `docs/reproduction_report.md` claims, evidence, limits.
