# HOPE Engine and Studio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Independently reproduce HOPE's paper-defined synthesis algorithms and benchmarks in Python, and expose accurate real-time traces via a SvelteKit 5 research workbench.

**Architecture:** Standalone pure Python engine with typed syntax, two concrete domains, underlying forward/backward interpretation and distinct meta interpretation; reproducible CLI benchmark harness; separate FastAPI worker-process service and SvelteKit 5 UI. Everything presented by the UI derives from structured engine events.

**Tech Stack:** Python 3.12+, pytest, Hypothesis, z3-solver, Pydantic v2, FastAPI, uvicorn, SvelteKit 5, TypeScript, Vitest, Playwright, Docker Compose. Pin exact dependency versions after P0 environment audit.

**Spec:** `docs/superpowers/specs/2026-10-30-hope-studio-design.md`

## Global Constraints

- Research algorithms and abstract domains MUST match the paper and supplement; exact definitions are extracted and audited during Task 1.
- Engine must run headlessly. UI/API cannot modify core mathematical semantics.
- No program `eval`/`exec`, fabricated traces, or unbounded user resource consumption.
- Baseline and HOPE policies must share enumeration, pruning, benchmark parameters and solver environment.
- The rubric/deadline are pending; consider this a proposed plan, not authorization to begin implementation.

## Review Focus

1. Width-1/overflow/shift corner cases: concrete semantics agree with solver — Task 3.
2. Empty strings, absent characters, overlapping prefixes/suffixes: sound string analysis — Task 9.
3. Ties, no informative holes, and multi-hole combination explosion: admissible deterministic bounded behavior — Tasks 7–8.
4. Extremely large grammars or stalled solvers: bounded rejection, cancellation and terminal status — Task 12.
5. Missing benchmarks and timeouts: report unsupported/timeout distinctly from unsatisfiable — Task 11.

---

## Phase P0 — Establish the exact research contract

### Task 1: Paper-to-code fidelity matrix

**Files:** Create `research/paper_mapping.md`, `research/operator_matrix.csv`, `research/experiment_manifest.yaml`, `research/known_deviations.md`.

**Interfaces:** Produces audited list of paper algorithms, abstract operators, lemmas/proofs, benchmark families, parameters and exact expected outcomes; later tasks implement ONLY audited entries.

- [ ] Read §3–§5 and the supplementary material; transcribe definitions of all paper-specific lattices, transfer operators, rank rules, and multi-hole selection, citing section/page in `paper_mapping.md`.
- [ ] Record all concrete operators, arities, types and relevant corner-case semantics in `operator_matrix.csv`.
- [ ] Locate available official artifact/benchmark source and verify provenance; record unavailable items without inventing equivalents.
- [ ] For every applicable Algorithm 1/2 branch, note its future module and test name; review against paper text.
- [ ] Commit: `docs: map HOPE paper algorithms and experiments`.

### Task 2: Reproducible Python project and typed grammar

**Files:** Create `pyproject.toml`, `src/hope_engine/syntax/{ast.py,grammar.py,codec.py}`, `tests/syntax/test_grammar.py`, `tests/syntax/test_codec.py`.

**Interfaces:** `Node` tagged frozen AST types, `Hole(nonterminal: str)`, `Grammar(productions: tuple[Production, ...], start: str)`, `validate_ast(node: Node, grammar: Grammar) -> None`, `holes(node: Node) -> tuple[Path,...]`, `replace_at(node: Node, path: Path, subtree: Node) -> Node`; `Path = tuple[int,...]`.

- [ ] Write tests for empty path/root, nested replacement, invalid production arity/types, and canonical serialize/deserialize round trip.
- [ ] Run `pytest tests/syntax -q`; verify tests fail for missing implementations.
- [ ] Implement immutable typed nodes and grammar validation without a parser dependency; run same suite until green.
- [ ] Run `ruff check .` and `mypy src/hope_engine` (configure tooling); commit `feat: typed grammar and partial programs`.

## Phase P1 — Bitvector kernel

### Task 3: Exact concrete semantics

**Files:** Create `src/hope_engine/concrete/{bitvector.py,verify.py}`, `tests/concrete/test_bitvector.py`.

**Interfaces:** `eval_bv(expr: Node, inputs: dict[str,int], width: int) -> int`, `matches_examples(expr: Node, examples: tuple[Example,...]) -> bool`, `z3_equivalent(expr: Node, reference: Node, width: int) -> bool` when supported.

- [ ] Write parametrized tests for operators in `operator_matrix.csv`, zero/one-width policy, wraparound, signed/unsigned behavior and defined shifts; compare exhaustive small-width cases with Z3.
- [ ] Run `pytest tests/concrete/test_bitvector.py -q` expecting failures.
- [ ] Implement width-masked operations and concrete oracle; reject unsupported operators explicitly.
- [ ] Run tests and commit `feat: exact bitvector evaluator`.

### Task 4: Bottom-up components and top-down search

**Files:** Create `src/hope_engine/enumeration/{components.py,sketches.py,search.py}`, `tests/enumeration/{test_components.py,test_search.py}`.

**Interfaces:** `enumerate_components(grammar: Grammar, budget: Budget) -> Iterator[ComponentBatch]`, `initial_sketches(grammar: Grammar) -> Iterator[Node]`, `search(problem: Problem, policy: HolePolicy, budget: Budget, sink: EventSink | None = None) -> SearchResult`.

- [ ] Write tiny-grammar tests for component ordering/size, deterministic search, and exact returned solutions.
- [ ] Run failing tests; implement paper-defined queue/sketch/component iteration before optimizations.
- [ ] Verify bounded exhaustion is distinct from proof of unsatisfiability; commit `feat: enumerative synthesis baseline`.

### Task 5: Underlying bitvector abstract interpreter

**Files:** Create `src/hope_engine/domains/bitvector/{lattice.py,forward.py,backward.py,analysis.py}`, `tests/domains/bitvector/{test_soundness.py,test_pruning.py}`.

**Interfaces:** `forward_bv(partial: Node, env: AbstractEnv) -> BVAbstract`, `backward_bv(partial: Node, target: BVAbstract, env: AbstractEnv) -> dict[Path,BVAbstract]`, `analyze_bv(partial: Node, examples: tuple[Example,...]) -> AnalysisResult`.

- [ ] Based on Task 1 matrix, test lattice partial order/join/top/bottom and forward/backward transfer rules against exhaustive width-2–4 concrete values.
- [ ] Run failures; implement exact paper-defined abstract operators and fixed-point protocol if specified.
- [ ] Test that known feasible partial programs never get pruned; commit `feat: sound bitvector abstract pruning`.

### Task 6: Wire safe pruning into baseline

**Files:** Modify `src/hope_engine/enumeration/search.py`; create `tests/enumeration/test_pruning_integration.py`.

**Interfaces:** Search accepts `analyzer: Analyzer`, calls it at paper-specified points, emits reasons, and preserves solver-valid solutions.

- [ ] Write regression tests comparing pruned vs exhaustive enumeration for all tiny width-2 grammars and satisfiable examples.
- [ ] Run failing tests; add analysis calls and pruning results; verify all baselines retain solutions.
- [ ] Commit `feat: integrate bidirectional pruning into synthesis`.

### Task 7: Exact meta-analysis hole ranking

**Files:** Create `src/hope_engine/meta/{bitvector.py,ranking.py,policies.py}`, `tests/meta/{test_rank.py,test_admissibility.py}`.

**Interfaces:** `rank_holes(partial: Node, components: ComponentInventory, examples: tuple[Example,...], domain: MetaDomain) -> tuple[HoleRank,...]`; `pick_holes(ranks: tuple[HoleRank,...], max_holes: int) -> tuple[Path,...]`; `HolePolicy` includes `leftmost`, `hope`, `meta_disabled`.

- [ ] Convert paper's Algorithm 2 and rank-1/rank-2 conditions into golden tests, including tie/no-benefit scenarios.
- [ ] Run failures; implement the **separate meta abstract domain**, not an ad-hoc scoring rule or rerun of the underlying analysis.
- [ ] Exhaustive tiny-universe cross-check meta soundness/admissibility against hypothetical fills; commit `feat: paper-guided hole ordering`.

### Task 8: Multiple-hole filling

**Files:** Create `src/hope_engine/enumeration/multifill.py`, `tests/enumeration/test_multifill.py`.

**Interfaces:** `fill_selected_holes(partial: Node, positions: tuple[Path,...], inventory: ComponentInventory, budget: Budget) -> Iterator[Node]`.

- [ ] Test one/three/five-hole settings, rank ties, overlapping positions (reject), no suitable components, finite combination limits.
- [ ] Run failures; implement paper-described simultaneous filling and integrate into `search()`.
- [ ] Compare solution validity/completeness for bounded tiny grammars and commit `feat: multi-hole synthesis`.

## Phase P2 — Strings

### Task 9: String semantics and underlying/meta domains

**Files:** Create `src/hope_engine/concrete/string.py`, `src/hope_engine/domains/string/{lattice.py,forward.py,backward.py,analysis.py}`, `src/hope_engine/meta/string.py`, `tests/domains/string/{test_concrete.py,test_soundness.py,test_meta.py}`.

**Interfaces:** `eval_string(expr: Node, inputs: dict[str,str]) -> str`, `analyze_string(partial: Node, examples: tuple[Example,...]) -> AnalysisResult`, `rank_string_holes(...) -> tuple[HoleRank,...]`.

- [ ] Extract paper+supplement string prefix/suffix/length operators; write exact forward/backward and meta golden cases including empty/missing-character conditions.
- [ ] Run failing tests; implement concrete semantics, abstract string domains and meta domain (including length categories as specified).
- [ ] Exhaustively check short strings over a tiny alphabet; verify supported real examples, commit `feat: string HOPE domains`.

### Task 10: SyGuS input and benchmark fixtures

**Files:** Create `src/hope_engine/sygus/{lexer.py,parser.py,adapter.py}`, `tests/sygus/test_import.py`, `benchmarks/README.md`.

**Interfaces:** `parse_sygus(text: str) -> Problem`, `load_problem(path: Path) -> Problem`; unsupported constructs return typed errors with line/column.

- [ ] Write golden tests from legally obtained benchmark files and malformed input (recursive grammars, strings with escaping, BV widths).
- [ ] Run failing tests; implement only audited SyGuS grammar subset needed by selected benchmarks.
- [ ] Verify parse/re-encode and oracle validation; commit `feat: SyGuS benchmark import`.

## Phase P3 — Evaluation

### Task 11: Reproducible CLI, ablations and reports

**Files:** Create `src/hope_engine/bench/{runner.py,report.py,manifest.py}`, `src/hope_engine/cli.py`, `tests/bench/{test_runner.py,test_report.py}`, `scripts/run_paper_ablations.sh`.

**Interfaces:** `run_suite(manifest: SuiteManifest, config: RunConfig) -> list[RunRecord]`, `summarize(records: list[RunRecord]) -> Summary`; command `python -m hope_engine.cli benchmark --manifest research/experiment_manifest.yaml --policy hope --timeout 60 --output results/hope.jsonl`.

- [ ] Test manifest parsing, fixed seed, timeout, cancellation, unsupported case, failed validation, and stable JSONL metadata.
- [ ] Run failures; implement process-level timeout and report renderer without web dependencies.
- [ ] Compare fixed-leftmost, HOPE, meta-off and multi-hole configurations with equal budgets; generate paired CSV and figures.
- [ ] Run clean-checkout `pytest -q` and CLI smoke suite; commit `feat: reproducible HOPE ablations`.

## Phase P4 — Web workbench

### Task 12: FastAPI worker process + bounded event protocol

**Files:** Create `apps/api/main.py`, `apps/api/models.py`, `apps/api/worker.py`, `src/hope_engine/trace/events.py`, `tests/api/{test_runs.py,test_limits.py}`.

**Interfaces:** `POST /api/runs`, `GET /api/runs/{id}`, `GET /api/runs/{id}/events`, `DELETE /api/runs/{id}`; events have monotonic `seq`, `run_id`, `kind`, `payload`, `schema_version`.

- [ ] Write API tests for valid runs, oversized grammar rejection, malformed AST, process death, idempotent cancel and terminal SSE completion.
- [ ] Run failures; implement bounded child processes, status polling and SSE with ordered events, no shell interpretation.
- [ ] Assert no engine dependency on FastAPI; commit `feat: isolated synthesis run API`.

### Task 13: SvelteKit 5 research workbench

**Files:** Create `apps/web/src/routes/+page.svelte`, `apps/web/src/lib/{api.ts,types.ts}`, `apps/web/src/lib/components/{ExamplesEditor.svelte,GrammarEditor.svelte,ASTViewer.svelte,AnalysisLog.svelte,RunControls.svelte}`, `apps/web/src/lib/state/run.svelte.ts`, `apps/web/src/lib/components/*.test.ts`.

**Interfaces:** UI calls only typed API; trace component consumes exact `SynthesisEvent` structures; no fake pruning predictions.

- [ ] Write Vitest tests for example/grammar validation, live event order, disconnect/reconnect, terminal run, and cancellation.
- [ ] Run failing tests; implement Svelte 5 reactive components, keyboard-accessible controls and a clear trace of ranked hole decisions.
- [ ] Run `npm run check` / `npm test`; commit `feat: interactive synthesis workbench`.

### Task 14: Comparative explorer and end-to-end evidence

**Files:** Create `apps/web/src/routes/experiments/+page.svelte`, `apps/web/tests/e2e/hope.spec.ts`, `docker-compose.yml`, `README.md`.

**Interfaces:** Compare identical benchmark runs by policy; export manifest + records + validation outcome. E2E demo from examples to verified solution.

- [ ] Write Playwright scenarios for one BV and one string example, changed policy comparison, export, cancelled long job and malformed example.
- [ ] Run failures; implement reports UI and demo compose setup.
- [ ] Run Playwright, pytest, frontend checks, and container smoke test; commit `feat: experiment explorer and reproducible demo`.

## Phase P5 — Submission and quality gate

### Task 15: Scientific report and repeatable packaging

**Files:** Create `docs/reproduction_report.md`, `docs/demo_script.md`, `results/README.md`, `LICENSE` (after choosing appropriate licensing).

**Interfaces:** Report maps paper claims to exact code, tests and measured evidence; transparent limitations and quantitative disagreements.

- [ ] Re-run paper subset and full available benchmarks using locked dependencies and recorded machine information.
- [ ] Verify every reported solution independently, check results for invalid/timeout/unsupported cases, include raw machine-readable data.
- [ ] Compare published vs reproduced figures with hardware/language caveats; no claims of achieved fidelity without test evidence.
- [ ] Follow clean-install README on a separate environment; deliver recorded demo and academic presentation; commit `docs: publish reproducibility evidence`.

## Execution handoff

First review the design and this provisional plan. **Do not implement until the user approves the design and confirms the professor's exact requirements when announced.** Start with Task 1: paper/supplement/operator audit; if material assumptions fail, revise both documents before engine coding. Default to subagent-driven execution if independent reviewer agents are available, otherwise native execution with targeted review gates.
