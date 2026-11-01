# SynthScope Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reimplement HOPE (POPL 2026, meta-analysis-guided hole filling) as a Python engine for bitvectors and strings, evaluate it with ablations, then add a SvelteKit 5 live dashboard.

**Architecture:** Pure-Python `hope_engine` package (no web imports) runs Algorithm 1 (queue of partial programs, bottom-up components, forward/backward abstract-interpretation pruning) with a pluggable hole policy (paper Algorithm 2, leftmost, meta-off). An optional event sink feeds a FastAPI websocket, which feeds the SvelteKit UI. CLI and JSONL reports are the research source of truth.

**Tech Stack:** Python 3.12, pytest, Hypothesis, z3-solver (test oracle only), ruff, mypy, FastAPI + uvicorn (websocket), SvelteKit 5 + TypeScript + Vitest.

**Spec:** `docs/superpowers/specs/2026-11-01-synthscope-design.md` (paper: `docs/paper.pdf`). The older ChatGPT drafts in `docs/` are superseded.

## Global Constraints

- Abstract domains, transfer functions, and rank rules come from the paper, its supplement, and the Simba paper (ref [38]); never from memory. If a definition exists nowhere, stop and ask the author.
- `hope_engine` never imports FastAPI, Svelte, or anything web. Events are opt-in and off during benchmark timing.
- All policies share the same search, components, and pruning code; only hole selection differs.
- Unsupported operators raise `UnsupportedOperator`; never approximate them.
- Soundness: pruning must never discard a program that could be a solution.
- Every solution is checked by a separate concrete evaluator. Z3 is a test oracle only.
- Budget = node-count cap plus 60 s wall-clock timeout (paper value); both logged. Random choices (paper Rank-3 pick) use a seeded `random.Random`.
- Max holes filled per step defaults to 3 (paper §4.5.1).
- No `eval`/`exec`, no database, no Docker, no Playwright.
- Faithful algorithm beats speed and coverage. Cut order if short: dashboard, big benchmark runs, extra ablations. Never cut strings.
- Folder is not a git repo; Task 1 runs `git init`.

## Review Focus

1. Width-1 bitvectors, shift amounts at or above width, division by zero: concrete evaluator and Z3 agree (Task 3).
2. Empty string, index past end, missing character, negative index: string semantics follow SMT-LIB v2.0 and abstract operators stay sound (Tasks 8-9).
3. No Rank-1 or Rank-2 hole (all Rank-3): policy returns a seeded random hole with `noprune=True` and the run is reproducible (Task 6).
4. Partial program with no holes, or grammar with no productions for a nonterminal: search ends with a clear status, no crash (Task 4).
5. Unsupported operator in an imported benchmark: reported as `unsupported`, never `unsat` or silently skipped (Task 11).

---

## File Structure

```
pyproject.toml
research/{paper_mapping.md,operator_matrix.csv,known_deviations.md,benchmarks.md}
src/hope_engine/
  syntax/{ast.py,grammar.py}          # Node, Path, Grammar, replace_at, holes
  concrete/{bitvector.py,string.py,verify.py}
  domains/base.py                     # Domain protocol
  domains/analysis.py                 # forward/backward alternating fixpoint (underlying)
  domains/bitvector/{lattice.py,ops.py}
  domains/string/{lattice.py,ops.py}
  meta/{lattice.py,analysis.py,rank.py,policies.py,bitvector.py,string.py}
  enumeration/{components.py,search.py,multifill.py}
  sygus/{parser.py,adapter.py}
  bench/{runner.py,report.py}
  trace/events.py
  cli.py
apps/api/{main.py,worker.py}
apps/web/                             # SvelteKit 5
tests/<mirrors src>
```

---

### Task 1: Project setup and paper audit

**Files:**
- Create: `pyproject.toml`, `research/paper_mapping.md`, `research/operator_matrix.csv`, `research/known_deviations.md`, `research/benchmarks.md`

**Interfaces:**
- Produces: audited list of every definition later tasks implement. Later tasks implement only audited entries.

- [ ] **Step 1:** `git init`; write `pyproject.toml` (Python 3.12, package `hope_engine` under `src/`, dev deps pytest, hypothesis, z3-solver, ruff, mypy); `pip install -e .[dev]`.
- [ ] **Step 2:** In `research/paper_mapping.md`, record with page citations: Algorithm 1, Algorithm 2, Defs 3.1-3.7, underlying `Analyze` fixpoints (§4.2), meta `Analyze#` and `F##`/`B##` (§4.3), Rank-1/2 conditions (7), (8), multi-hole subsets (§4.5.1), string domains and Figs 3-6 (§4.6.3), bitvector meta Figs 1-2.
- [ ] **Step 3:** Locate the **supplement** (full string and meta operator tables, soundness proofs) and the **Simba paper** (Yoon, Lee, Yi, PLDI 2023, ref [38], DOI 10.1145/3591288, source of the bitvector underlying domain: bitwise domain plus signed and unsigned intervals). Record each source in `research/benchmarks.md` with where it was found, or "not found".
- [ ] **Step 4:** Fill `research/operator_matrix.csv` with columns `domain,operator,arity,types,concrete_semantics,forward_underlying,backward_underlying,forward_meta,backward_meta,source_page`. Mark any cell with no source `MISSING`.
- [ ] **Step 5:** Record in `research/benchmarks.md` which of Duet (205 strings), HardBench (132), Bitvec-cond (750), Deobfusc (500), Hacker's Delight (44) can be obtained, with licence and link.
- [ ] **Step 6: Gate.** Count `MISSING` cells. If any `MISSING` blocks a Task 5, 6, 9, or 10 operator, stop and ask the author. Do not invent. Commit: `git add -A && git commit -m "docs: paper audit and project setup"`.

---

### Task 2: Typed partial programs and grammar

**Files:**
- Create: `src/hope_engine/syntax/ast.py`, `src/hope_engine/syntax/grammar.py`
- Test: `tests/syntax/test_ast.py`, `tests/syntax/test_grammar.py`

**Interfaces:**
- Produces:
  - `Path = tuple[int, ...]`; frozen dataclasses `Op(name: str, args: tuple[Node, ...])`, `Const(value: int | str, type: str)`, `Var(name: str)`, `Hole(nonterminal: str)`; `Node = Op | Const | Var | Hole`.
  - `holes(node) -> tuple[Path, ...]` (left-to-right), `subterm(node, path) -> Node`, `replace_at(node, path, subtree) -> Node`, `size(node) -> int`.
  - `Production(lhs: str, label: str | Const | Var, rhs: tuple[str, ...] = ())` (a `str` label is an operator name); `Grammar(productions: tuple[Production, ...], start: str)` with `productions_for(nt: str) -> tuple[Production, ...]`; `validate(node, grammar) -> None` raising `GrammarError`.

- [ ] **Step 1: Write failing tests:** `test_replace_at_root` (empty path returns subtree); `test_replace_at_nested` (replace `Op("bvadd",(Hole("S"),Var("x")))` at `(0,)` gives `Op("bvadd",(Var("x"),Var("x")))`); `test_holes_order` (returns `((0,),(1,))` for two holes); `test_validate_rejects_wrong_arity` raises `GrammarError`; `test_validate_accepts_partial` (hole of correct nonterminal accepted).
- [ ] **Step 2:** `pytest tests/syntax -q` → FAIL (import error).
- [ ] **Step 3:** Implement as signed above; frozen dataclasses so nodes hash.
- [ ] **Step 4:** `pytest tests/syntax -q` → PASS; `ruff check . && mypy src` clean.
- [ ] **Step 5:** Commit `feat: typed partial programs and grammar`.

---

### Task 3: Bitvector concrete semantics and validator

**Files:**
- Create: `src/hope_engine/concrete/bitvector.py`, `src/hope_engine/concrete/verify.py`
- Test: `tests/concrete/test_bitvector.py`

**Interfaces:**
- Consumes: Task 2 nodes; operator list from `operator_matrix.csv` (paper names include `bvneg bvnot bvand bvor bvxor bvadd bvsub bvmul bvudiv bvurem bvsdiv bvlshr bvshl`; final set from audit).
- Produces: `UnsupportedOperator(Exception)`; `eval_bv(node, env: dict[str, int], width: int) -> int` (result in `[0, 2**width)`); `Example(inputs: dict[str, int | str], output: int | str)` in `concrete/verify.py`; `satisfies(program: Node, examples: tuple[Example, ...], width: int | None = None) -> bool` (dispatches on `Const.type`).

- [ ] **Step 1: Write failing tests:** parametrized over every audited operator for widths 1-4, exhaustively over all inputs, comparing `eval_bv` to a Z3 `BitVec` evaluation (SMT-LIB semantics: division by zero, shift ≥ width follow SMT-LIB); `test_unknown_operator_raises` (`UnsupportedOperator`); `test_satisfies_checks_all_examples`.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement width-masked operators; recursion only, no `eval`.
- [ ] **Step 4:** Run → PASS. Commit `feat: bitvector evaluator and validator`.

---

### Task 4: Search (Algorithm 1) with components and budget

**Files:**
- Create: `src/hope_engine/enumeration/components.py`, `src/hope_engine/enumeration/search.py`, `src/hope_engine/trace/events.py`
- Test: `tests/enumeration/test_components.py`, `tests/enumeration/test_search.py`

**Interfaces:**
- Consumes: Task 2 grammar, Task 3 `satisfies`.
- Produces:
  - `Problem(grammar: Grammar, examples: tuple[Example, ...], domain: Literal["bv","str"], width: int | None)`.
  - `Budget(max_nodes: int, timeout_s: float | None)`.
  - `Event(run_id: str, seq: int, kind: str, payload: dict)` and `EventSink = Callable[[Event], None]` with kinds from the spec (`search_started`, `candidate_expanded`, `forward_analysis`, `backward_analysis`, `hole_ranked`, `pruned`, `hole_filled`, `solution_found`, `run_finished`).
  - `Analyzer` protocol: `analyze(partial: Node, examples) -> AnalysisResult` where `AnalysisResult(infeasible: bool, preconditions: dict[Path, object])`.
  - `HolePolicy` protocol: `pick(partial: Node, ctx: PickContext) -> tuple[tuple[Path, ...], bool]` (positions, `noprune`).
  - `ComponentMap`: `get(nonterminal: str) -> tuple[Node, ...]`; `add_components(grammar, comps: ComponentMap, size_limit: int) -> None` (bottom-up, increasing size, observational equivalence only if sound).
  - `SearchResult(status: Literal["solved","exhausted","timeout","unsupported"], program: Node | None, nodes: int, seconds: float)`; `search(problem, analyzer, policy, budget, sink=None) -> SearchResult`. `exhausted` means "within budget", not "unsat".
  - `LeftmostPolicy` and `NullAnalyzer` (never infeasible) as baseline.

- [ ] **Step 1: Write failing tests:** `test_components_by_increasing_size`; `test_search_finds_known_solution` (width-4 grammar `S → x | 1 | bvadd(S,S)`, example `x=3 ↦ 4`, expects `bvadd(x,1)` or an equivalent that `satisfies`); `test_exhausted_not_unsat` (impossible example returns `status="exhausted"`); `test_no_holes_program` (complete program with no holes does not crash); `test_nonterminal_without_productions` returns `exhausted`; `test_events_off_by_default` (no sink, no events); `test_events_monotonic_seq`.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement Algorithm 1 (paper p.9): queue init with sketches from the grammar start; per iteration `add_components`; pop `P`; complete and satisfies → return; else `analyze`; if infeasible continue; `policy.pick`; if `noprune` enqueue every component fill with no analysis; else enqueue only fills whose `analyze` is not infeasible. Check budget each iteration.
- [ ] **Step 4:** Run → PASS. Commit `feat: algorithm 1 search baseline`.

---

### Task 5: Bitvector underlying analysis

**Files:**
- Create: `src/hope_engine/domains/base.py`, `src/hope_engine/domains/analysis.py`, `src/hope_engine/domains/bitvector/lattice.py`, `src/hope_engine/domains/bitvector/ops.py`
- Test: `tests/domains/bitvector/test_soundness.py`, `tests/domains/bitvector/test_pruning.py`

**Interfaces:**
- Consumes: Task 4 `Analyzer`, `AnalysisResult`; the bitvector rows of `operator_matrix.csv` (from Simba paper [38]).
- Produces:
  - `Domain[A]` protocol: `top`, `bottom`, `alpha(value) -> A`, `leq`, `join`, `meet`, `forward(op: str, args: Sequence[A]) -> A`, `backward(op: str, result: A, args: Sequence[A], i: int) -> A`.
  - `analyze_underlying(domain: Domain[A], partial: Node, example: Example) -> dict[Path, A]` implementing paper §4.2: forward lfp, backward gfp, alternating chain until it converges; holes map to ⊤ in forward and are constrained backward.
  - `BitvectorDomain(width: int)`: reduced product of bitwise, signed-interval, unsigned-interval domains.
  - `DomainAnalyzer(domain)`: `Analyzer` that is infeasible when any position is ⊥, and returns per-hole preconditions.

- [ ] **Step 1: Write failing tests:** at widths 2-3, exhaustively: `test_forward_sound` (for every operator and all abstract-value pairs in a sampled set, each concrete result of concretized inputs lies in `forward` output); `test_backward_sound` (every concrete argument that yields a result in the target stays in the restricted abstract argument); `test_known_feasible_never_pruned` (for every tiny grammar program that satisfies an example, all its prefixes-as-partial-programs analyze as feasible); `test_analyze_alternation_converges`.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement operator by operator from the audit; unlisted operators raise `UnsupportedOperator`.
- [ ] **Step 4:** Run → PASS. Wire `DomainAnalyzer` into `search` tests: pruned search returns the same solved/unsolved outcome as `NullAnalyzer` for all width-2 tiny grammars.
- [ ] **Step 5:** Commit `feat: bitvector forward-backward pruning`.

---

### Task 6: Meta analysis, ranking, and hole policy (core of the paper)

**Files:**
- Create: `src/hope_engine/meta/lattice.py`, `src/hope_engine/meta/analysis.py`, `src/hope_engine/meta/rank.py`, `src/hope_engine/meta/policies.py`, `src/hope_engine/meta/bitvector.py`
- Test: `tests/meta/test_lattice.py`, `tests/meta/test_paper_examples.py`, `tests/meta/test_rank.py`, `tests/meta/test_admissible.py`

**Interfaces:**
- Consumes: Task 4 `HolePolicy`; Task 5 `Domain`; paper §4.3-4.4, Algorithm 2, Figs 1-2.
- Produces:
  - `Meta` enum `{BOT, MUST_TOP, MAY_NOT_TOP}`; order `BOT ⊑ MUST_TOP ⊑ MAY_NOT_TOP`; `join`, `meet`.
  - `MetaDomain` protocol: `forward(op, args) -> M`, `backward(op, result, args, i) -> M`, constants → `MAY_NOT_TOP`.
  - `meta_analyze(domain: MetaDomain, partial: Node, pos: Path) -> dict[Path, tuple[M, M]]`: pair `(forward, backward)` per position, per `F#`, `F##`, `B#`, `B##` with `I_F#`, `I_B#` and the increasing chain `X0 = lfp F#`, `X(2n+1) = lfp ⊔B#`, `X(2n+2) = lfp ⊔F#`.
  - `may_infeasible(res) -> bool` (condition (7): some position equals `(MAY_NOT_TOP, MAY_NOT_TOP)`), `may_prune_components(res, pos, holes) -> bool` (condition (8): another hole has `(MUST_TOP, MAY_NOT_TOP)`).
  - `pick_hole(partial, meta_domain, rng: random.Random) -> tuple[Path, bool]` per Algorithm 2.
  - Policies: `HopePolicy(meta_domain, seed: int = 0, max_holes: int = 1)`, `LeftmostPolicy`, `MetaOffPolicy(seed)` (random hole, `noprune=False`).
  - `BitvectorMeta` implementing Figs 1-2 rules, e.g. forward `bvand/bvor/bvmul/bvsdiv/bvlshr/bvshl` → `MAY_NOT_TOP` if any arg is `MAY_NOT_TOP`; `bvneg/bvnot` → same as arg; `bvxor/bvadd/bvsub` → `MAY_NOT_TOP` only if both args are.

- [ ] **Step 1: Write failing golden tests reproducing the paper's worked example (pp. 5-7, 15-17):** for `ConCat(□,□,□)` with abstract operators from the paper's example (`ConCat##` forward returns the third argument's value; backward 1 is `MAY_NOT_TOP` if arg2 ≠ `MUST_TOP` and result ≠ `MUST_TOP`, else `MUST_TOP`; backward 2 and 3 return `MUST_TOP`), assert `meta_analyze` results `ε: (MUST_TOP, MAY_NOT_TOP)` etc. exactly as the paper's table on p. 6; `test_rank1_is_position_3`, `test_rank2_is_position_2`, `test_position_1_unranked`; `test_pick_prefers_rank1_over_rank2`; `test_all_rank3_returns_seeded_random_and_noprune_true` (same seed same pick across runs); `test_lattice_laws` (join commutative, associative, idempotent over the three elements).
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement the separate meta domain; do not reuse the underlying analysis or invent a scoring rule.
- [ ] **Step 4: Soundness test `test_meta_sound_against_underlying`:** for tiny width-2 grammars and every partial program and hole, whenever the underlying `DomainAnalyzer` reports infeasible after filling `pos` with *any* component, `may_infeasible` is true (Theorem 4.2 and 4.4); and when `pick_hole` returns `noprune=True`, no fill of any hole is pruned by the underlying analysis (admissible).
- [ ] **Step 5:** Run → PASS. Wire `HopePolicy` into `search` and check on the width-4 grammar that all three policies return a program that `satisfies` the examples. Commit `feat: meta-analysis hole ranking`.

---

### Task 7: Multi-hole filling

**Files:**
- Create: `src/hope_engine/enumeration/multifill.py`
- Modify: `src/hope_engine/meta/rank.py`, `src/hope_engine/enumeration/search.py`
- Test: `tests/enumeration/test_multifill.py`, `tests/meta/test_multihole_rank.py`

**Interfaces:**
- Consumes: Tasks 4, 6.
- Produces: `pick_holes(partial, meta_domain, rng, max_holes: int) -> tuple[tuple[Path, ...], bool]` per §4.5.1: iterate subsets `H ⊆ Holes(P)` of size 1..`max_holes`, run `meta_analyze` with all of `H` hypothetically filled, collect Rank-1 and Rank-2 subsets, same fallback; `fill_selected(partial, positions, comps: ComponentMap) -> Iterator[Node]` (cartesian product of compatible components, no duplicate nodes); `search` fills all returned positions at once.

- [ ] **Step 1: Write failing tests:** `test_one_hole_equals_single` (`max_holes=1` matches Task 6 pick); `test_three_holes_on_plus_example` (partial program `□+□+□` with `max_holes=3` returns a subset of size ≥ 2 when one exists that yields Rank-1/2); `test_fill_no_components_yields_nothing`; `test_combination_cap` (product larger than `Budget.max_nodes` stops cleanly); `test_ablation_outcomes_agree` (1-, 3-, 5-hole runs on a tiny grammar find a satisfying program or all report `exhausted`).
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat: simultaneous multi-hole filling`.

> Shortcut: skip the paper's incremental meta analysis (§4.5.2). It is a speed optimization, not part of the algorithm's meaning. Note it in `research/known_deviations.md`.

---

### Task 8: String concrete semantics

**Files:**
- Create: `src/hope_engine/concrete/string.py`
- Modify: `src/hope_engine/concrete/verify.py`
- Test: `tests/concrete/test_string.py`

**Interfaces:**
- Consumes: Task 3 `UnsupportedOperator`, `Example`, `satisfies`.
- Produces: `eval_str(node, env: dict[str, str | int]) -> str | int` for the audited operators (SMT-LIB v2.0 strings: at least `str.++`, `str.at`, `str.substr`, `str.indexof`, `str.len`, `str.to.int`, `int.to.str`; final set from the matrix). Out-of-range `str.at`/`str.substr` return `""` per SMT-LIB.

- [ ] **Step 1: Write failing tests:** edge cases `str.at("",0)==""`, `str.substr("abc",2,5)=="c"`, `str.substr("abc",-1,2)==""`, `str.indexof("abc","",1)==1`, `str.to.int("")==-1`, `str.to.int("12a")==-1`; plus a Hypothesis check that `eval_str` agrees with Z3's string solver for random short strings over alphabet `"ab"`.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat: string evaluator`.

---

### Task 9: String underlying analysis

**Files:**
- Create: `src/hope_engine/domains/string/lattice.py`, `src/hope_engine/domains/string/ops.py`
- Test: `tests/domains/string/test_lattice.py`, `tests/domains/string/test_soundness.py`

**Interfaces:**
- Consumes: Task 5 `Domain`, `analyze_underlying`, `DomainAnalyzer`; paper §4.6.3 and the supplement's full operator tables.
- Produces: `StringDomain(alphabet: frozenset[str])` implementing `Domain`. Elements are the reduced product of prefix-with-length `(s, i)` and suffix-with-length `(s, i)`, where `s ∈ (Σ ∪ {*})*` and `i = [l, h]` with `h ∈ ℕ ∪ {∞}`. `alpha` and `gamma` follow the paper: LCP / LCS and `[ℓmin, ℓmax]`. Operators implemented from the matrix (selected in paper: forward `ConCat`, `CharAt`, `StrToInt`; backward `ConCat` 1 and 2, `CharAt` 1 and 2, `StrToInt` 1). Anything not listed uses the paper's default rule: bottom if any arg is bottom, else top.

- [ ] **Step 1: Write failing tests:** `test_alpha_gamma_galois` (for every set of strings over `{a,b}` up to length 3, `S ⊆ γ(α(S))`); `test_forward_sound` and `test_backward_sound` exhaustively over all strings up to length 3 over `{a,b}` for each operator; `test_overview_example_pruned` (paper §2: partial program `ConCat(x,□,□)` with suffix `"K"` target for `f("Jan","Kotas")="J.K"` is *not* pruned, while `ConCat(□,□," ")` *is* pruned); `test_empty_and_wildcard_prefix`.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement from the audit. **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat: string abstract domain and pruning`.

---

### Task 10: String meta analysis

**Files:**
- Create: `src/hope_engine/meta/string.py`
- Test: `tests/meta/test_string_meta.py`

**Interfaces:**
- Consumes: Task 6 `Meta`, `MetaDomain`, `meta_analyze`; paper Figs 5-6 and the supplement.
- Produces: `StringMeta` implementing `MetaDomain`. Element is the product of prefix and suffix domains; each is `(c, i)` with `c ∈ {BOT, MUST_TOP, MAY_NOT_TOP}` and length `i ∈ {BOT, Con, Bnd, Unb}` ordered `BOT ⊑ Con ⊑ Bnd ⊑ Unb`. Forward `ConCat` uses `⊙` (`MAY_NOT_TOP` if either arg is) and adds lengths; `CharAt` per Fig 5; `StrToInt` returns `Bnd` length when the input length is `Con` or `Bnd`, else `Unb`.

- [ ] **Step 1: Write failing tests:** `test_overview_ranks` (paper §2 `ConCat(□,□,□)` with string meta gives the same ranks as Task 6's golden test); `test_meta_sound_against_string_underlying` (for tiny alphabet grammars, every infeasible underlying result implies `may_infeasible`); `test_length_domain_order`.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** Run → PASS.
- [ ] **Step 5:** Wire strings into `search`; run all three policies on a 3-example string grammar; all solutions pass `satisfies`. Commit `feat: string meta analysis`.

---

### Task 11: SyGuS-IF import

**Files:**
- Create: `src/hope_engine/sygus/parser.py`, `src/hope_engine/sygus/adapter.py`
- Test: `tests/sygus/test_import.py`, `tests/sygus/fixtures/*.sl`

**Interfaces:**
- Consumes: Tasks 2, 4; `research/benchmarks.md` for the fixture source.
- Produces: `parse_sygus(text: str) -> Problem`, `load_problem(path: Path) -> Problem`; `SygusError(line: int, col: int, message: str)` and `UnsupportedOperator` for constructs outside the audited set, surfaced as status `unsupported`.

- [ ] **Step 1: Write failing tests** with 1 bitvector and 1 string fixture (real benchmark files if obtainable, otherwise hand-written and labelled): `test_parse_bv_fixture`, `test_parse_string_fixture`, `test_malformed_reports_line_col`, `test_unsupported_operator_is_unsupported_not_unsat`.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement a small S-expression reader (no parser library); support only constructs the audited benchmarks need. **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat: sygus-if import`.

---

### Task 12: CLI, ablations, and reports

**Files:**
- Create: `src/hope_engine/bench/runner.py`, `src/hope_engine/bench/report.py`, `src/hope_engine/cli.py`
- Test: `tests/bench/test_runner.py`, `tests/bench/test_report.py`

**Interfaces:**
- Consumes: Tasks 4-11.
- Produces:
  - `RunConfig(policy: Literal["hope","leftmost","meta_off"], max_holes: int, max_nodes: int, timeout_s: float, seed: int)`.
  - `RunRecord(benchmark: str, status: Literal["solved","exhausted","timeout","unsupported","invalid","crashed"], validated: bool, nodes: int, analyzer_calls: int, meta_calls: int, seconds: float, program_size: int | None, config: RunConfig, env: dict[str, str])` (env: Python, Z3, OS, CPU, seed).
  - `run_one(problem, config) -> RunRecord` (child process enforces timeout); `run_suite(paths: list[Path], config, out: Path) -> list[RunRecord]` writes JSONL; `summarize(records) -> dict`; `paired_csv(a: list[RunRecord], b: list[RunRecord], out: Path) -> None`.
  - CLI: `python -m hope_engine.cli solve FILE` and `python -m hope_engine.cli bench DIR --policy hope --holes 3 --timeout 60 --nodes 100000 --out results/hope.jsonl`, plus `report results/*.jsonl`.

- [ ] **Step 1: Write failing tests:** `test_timeout_status` (long run killed, status `timeout`); `test_unsupported_status`; `test_invalid_if_validation_fails`; `test_jsonl_has_env_metadata`; `test_same_seed_same_record` (nodes and program identical); `test_paired_csv_only_common_benchmarks`.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** Run → PASS.
- [ ] **Step 5:** Run the four ablation configs (hope, leftmost, meta_off, and `--holes 1` vs `3`) on the fixtures and any obtained benchmark subset; write `results/README.md` listing them. Commit `feat: reproducible ablation harness`.

---

### Task 13: Event stream and websocket API

**Files:**
- Create: `apps/api/main.py`, `apps/api/worker.py`
- Modify: `src/hope_engine/trace/events.py` (adds `to_json(event) -> str`)
- Test: `tests/api/test_runs.py`, `tests/api/test_limits.py`

**Interfaces:**
- Consumes: Task 4 `Event`, `EventSink`; Task 12 `RunConfig`.
- Produces: `POST /api/runs` body `{problem: <sygus text or JSON problem>, config: RunConfig}` → `{run_id}` with limits (grammar size, example count, width ≤ 64, string length) returning 422 when exceeded; `GET /api/runs/{id}` → status and counters; `WS /api/runs/{id}/ws` sends JSON events in `seq` order then `run_finished`, accepts `{"cmd":"cancel"}`; `DELETE /api/runs/{id}` idempotent cancel. Worker runs `search` in a `multiprocessing` child; the sink batches `forward_analysis` and `backward_analysis` events and caps events per second.

- [ ] **Step 1: Write failing tests:** `test_run_streams_ordered_events_to_finish`; `test_oversized_grammar_rejected`; `test_cancel_kills_runaway_run` (long-running problem ends with `cancelled` within 2 s); `test_cancel_twice_ok`; `test_child_death_reports_error`; `test_engine_imports_no_web` (importing `hope_engine` leaves `fastapi` out of `sys.modules`).
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement; never run synthesis on the API event loop. **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat: websocket run api`.

---

### Task 14: SvelteKit 5 dashboard (extra)

**Files:**
- Create: `apps/web/` (SvelteKit + TS), `apps/web/src/lib/{types.ts,socket.ts}`, `apps/web/src/lib/state/run.svelte.ts`, `apps/web/src/lib/components/{ExamplesPanel,GrammarPanel,AstView,HolesPanel,AnalysisState,SynthLog,BestCandidate,Stats,ProgressChart,BenchSummary}.svelte`, `apps/web/src/routes/+page.svelte`
- Test: `apps/web/src/lib/state/run.test.ts`, `apps/web/src/lib/components/*.test.ts`

**Interfaces:**
- Consumes: Task 13 websocket and REST; layout from `docs/Untitled.png`.
- Produces: `RunState` (Svelte 5 runes class) with `events: SynthEvent[]`, `status`, `best`, `start(problem, config)`, `cancel()`, `replay(events)`; `SynthEvent` mirrors the Python `Event` JSON.

- [ ] **Step 1: Write failing Vitest tests:** `run.test.ts` — events apply in `seq` order; an out-of-order event is buffered; a dropped socket marks status `disconnected`; `cancel` sends `{"cmd":"cancel"}`; `replay` rebuilds the same state as live; components render holes with rank and pruning event counts from real event payloads (no hard-coded values).
- [ ] **Step 2:** `npm test` → FAIL. **Step 3:** Implement with Svelte 5 runes; panels are presentation-only; virtualize or window the log. **Step 4:** `npm run check && npm test` pass; manually run API plus UI against one bitvector and one string fixture and confirm the dashboard matches the CLI result.
- [ ] **Step 5:** Commit `feat: live synthesis dashboard`.

---

### Task 15: Reproduction report

**Files:**
- Create: `docs/reproduction_report.md`, `README.md`, `research/known_deviations.md` (update)

**Interfaces:** consumes all results; no code.

- [ ] **Step 1:** Map every paper algorithm, definition, and figure to code, test, and result in `docs/reproduction_report.md`.
- [ ] **Step 2:** Compare measured vs paper numbers (Fig 7, Fig 10: ablation, 1/3/5 holes) with hardware and language caveats; do not claim fidelity without test evidence.
- [ ] **Step 3:** List every deviation (skipped incremental meta analysis, missing benchmarks, Python speed, any `MISSING` operator).
- [ ] **Step 4:** Follow `README.md` from a clean checkout in a fresh venv; fix gaps. Commit `docs: reproduction report`.

---

## Self-review notes

- Spec coverage: goals 1-6 → Tasks 4-14; non-goals respected (no DB, no eval); P0-P5 → Tasks 1, 4-7, 8-10, 11-12, 13-14, 15.
- Names checked across tasks: `Domain`, `DomainAnalyzer`, `MetaDomain`, `HolePolicy.pick`, `pick_hole`/`pick_holes`, `Budget`, `RunConfig`, `RunRecord`, `Event`.
- Risk: Tasks 5, 9, 10 depend on the supplement and Simba paper. Task 1's gate stops work if cells stay `MISSING`.
