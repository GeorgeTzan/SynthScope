# HOPE Studio — Research Reproduction Design

**Date:** 2026-10-30  
**Status:** Proposed, pending academic requirements and design approval  
**Reference:** Lee, Lee & Yi, *Inductive Program Synthesis by Meta-Analysis-Guided Hole Filling*, POPL 2026, DOI: https://doi.org/10.1145/3776694

## 1. Intent

Reproduce HOPE's central research algorithms as an **independent Python implementation**, then offer a polished, instrumented SvelteKit 5 workbench. Success has two inseparable axes: scientific credibility (correct implementation and reproducible ablations) and a useful visualization (real events from the engine, not a simulation). The professor's exact rubric and deadline are not yet available.

## 2. Evidence and fidelity boundaries

The original system is about 14K lines of OCaml and uses Z3. The paper describes: (1) SyGuS-like grammar-constrained inductive synthesis; (2) top-down enumeration of sketches/partial programs with holes; (3) bottom-up enumeration of closed components; (4) forward/backward abstract-interpretation pruning; (5) a separate meta abstract interpreter that overapproximates the behavior of that pruning analysis to rank hole positions; (6) multi-hole filling; (7) bitvector and string instantiations; and (8) comparisons/ablations. **These are required reproduction targets, not optional UX features.** Source material includes the ACM paper and its supplementary material (proofs and definitions for string and meta domains). Do not implement operators or ranking rules from memory: extract and track exact mathematical definitions before writing domain logic.

A faithful independent *algorithmic* reproduction is the target. Exact performance replication is not guaranteed with a different language, machine, solver build, or benchmark implementation. Results must identify these deviations.

## 3. Goals and acceptance criteria

1. For supported input grammars and examples, synthesize a valid AST program and independently check all examples (plus optional solver-based checks).
2. Implement the paper's algorithmic structure, including search, components, pruning, paper-defined hole rankings, and simultaneous hole filling.
3. Implement the original paper's bitvector and string abstract semantics to the documented extent; track unsupported operators explicitly and reject unsupported instances (never silently approximate unsoundly).
4. Verify abstract operators are sound: every concrete result belongs to the abstraction; every backward restriction retains all valid solutions; meta predictions must not cause an unsound loss of solutions.
5. Compare at least: paper-style meta policy, fixed leftmost policy, meta disabled, and single versus up-to-three-hole filling, with identical grammar, resources, dataset, and evaluation harness.
6. Reproduce reported experiments as far as obtainable benchmark corpora and machine resources allow, publishing per-instance statuses and honest deviations.
7. Web UX supports example editing, grammar selection, start/cancel, live AST and pruning events, comparative plots, run export, and benchmark explorer.
8. CLI execution and reporting work without a frontend or API server.

## 4. Non-goals

No LLM program generation, arbitrary user Python evaluation, multi-user SaaS, paid accounts, cloud infrastructure, or a promise of bit-for-bit matching the OCaml engine. No hand-authored visualization data passed off as solver events. No database at first.

## 5. Approaches considered

- **A: Browser-only TypeScript:** simple deployment; weak fit for exhaustive, solver-heavy experiment reproduction and process isolation.
- **B: Independent Python engine + Z3 + FastAPI + SvelteKit 5 (proposed):** easy research iteration and testing, clear service boundary; potential search-loop performance penalty must be measured.
- **C: OCaml/Z3 engine + SvelteKit:** closest implementation stack and potentially stronger speed; additional learning/setup burden and risks turning independent reproduction into a port of the authors' source.

Choose B provisionally. Revisit only if pilot experiments demonstrate unacceptable performance or the academic rubric requires another approach.

## 6. Architecture

```text
SyGuS benchmark files ──────────┐
CLI / experiment harness ────────┤
                                 ▼
                        Python hope_engine package
       grammar/parser → typed AST + semantics → component enumerator
                                  ↓
                        sketch/partial search queue
                           ├→ underlying forward/backward AI
                           ├→ meta abstract interpreter → ranked positions
                           └→ component filling / bounded combinations
                                  ↓
                       independent concrete validation
                                  │
                     result + structured trace events
                           /               \
                  CLI/artifacts           FastAPI
                                            │ REST + event stream
                                         SvelteKit 5
```

**Core boundaries:** `hope_engine` has no dependency on FastAPI or Svelte. All strategies share precisely the same search, components, and pruning implementation. Only the hole-selection policy changes. Event emission is opt-in; benchmark timing uses disabled/minimal instrumentation. API runs solver in separate worker **processes**, with concurrency/time/memory quotas; never block its event loop with synthesis. Browser does not evaluate arbitrary user code.

### Engine modules

- `syntax/`: typed AST, holes and tree paths, regular tree grammar, canonical serialization; strict type/arity checks.
- `concrete/`: bitvector semantics with exact width/modulo behavior, signed/unsigned operators where specified; string semantics with exact Unicode/length/index conventions as specified by the paper/benchmark.
- `enumeration/`: bottom-up component generation (cost/size ordering, observational equivalence only when sound), initial sketches, worklist and fill operations.
- `domains/bitvector/`, `domains/string/`: paper-defined forward/backward abstract operators, transfer rules and refinements; implement per paper and supplement.
- `meta/`: distinct paper-defined meta abstract domains and analysis, rank computation, tie handling, admissible hole selection, multi-hole behavior.
- `solver/`: Z3 adapter only where the paper requires it; separate SMT timeouts and record versions.
- `bench/`: benchmark importer, runner, summaries, per-instance outputs and reproducibility manifest.
- `trace/`: versioned, structured events with node IDs, candidates, analysis outcomes and measured times.

### Backend protocol

- `POST /api/runs`: accept bounded, validated synthesis requests; return `run_id`.
- `GET /api/runs/{run_id}`: pending/running/solved/unsat-or-exhausted/timeout/error/cancelled state with counters. Distinguish **exhausted within bounds** from mathematically unsatisfiable.
- `GET /api/runs/{run_id}/events`: server-sent events (SSE) for ordered events (`search_started`, `candidate_considered`, `hole_ranked`, `analysis_pruned`, `hole_filled`, `solution_found`, `run_finished`). SSE is one-way and sufficient initially; WebSocket is unnecessary.
- `DELETE /api/runs/{run_id}`: cancellation, terminating child process if necessary.
- `GET /api/benchmarks` and `GET /api/reports/{id}`: index and report downloads; protect file paths.
- Pydantic models are the canonical wire schema; generate TypeScript types/OpenAPI client.

### UI

Single-page workbench with sections: Examples & Grammar; AST/holes and ranking detail; Search/abstract interpretation trace; solution/validation; experiment comparison and exported evidence. Svelte 5 runes for local UI state; components remain presentation-only. Provide pause/replay/step **of recorded traces** (not pause of live engine unless separately implemented). Virtualize or aggregate event logs.

## 7. Correctness and evaluation

- **Concrete oracle:** fixed-width bitvector semantics must match Z3 for supported ops, including overflow and shifts; string edge cases must match defined semantics.
- **Domain soundness:** property-based finite-universe tests for small widths/alphabet; exhaustive small-domain cross checks of forward/backward/meta analysis; randomized differential tests where possible.
- **Completeness within bounds:** compare strategy outcome sets against brute force for small grammars, controlling enumeration caps; if not, discover a soundness bug.
- **Reproduction:** obtain supplementary PDF and any published artifact, benchmark lists, configuration, seeds, and timeout rules. Maintain a paper-to-code table mapping each algorithm, definition, operator, and experimental figure to code/test/manifest. Generate cold-run and warmed-run distributions separately if relevant.
- **Outcome tracking:** solved, valid solution, timeout, crashed, unsupported, out-of-memory, exhausted within configured bound. Record CPU model, OS, Python, Z3, git SHA, grammar size, seed, timeout, memory cap, event trace setting and elapsed wall/CPU time.
- **Primary metrics:** solves within 60 s, time on solved instances, search states, pruned states, meta overhead, abstract-interpreter calls, and peak RSS. Comparisons always use paired instances and same hardware.

## 8. Security and operational constraints

No `eval`/`exec`, shelling out with user strings, or unconstrained benchmark uploads. Validate AST/grammar limits, integer widths, string lengths and file sizes. Child process isolation, CPU/memory/time caps, rate/concurrency limits for public deployment. No personal-data collection. Local-first reproducibility; Docker Compose for demo only, CLI as research source of truth. Lock dependency versions before publishing results.

## 9. Delivery phases and exit criteria

**P0 — Paper fidelity audit:** paper and supplemental definitions collected, algorithm/operator matrix checked, reproducible benchmarks inventoried. **Gate:** no unknown core operator/rank formula.

**P1 — Bitvector scientific kernel:** typed AST, concrete semantics, components, search, forward/backward AI, meta AI, selection policies, multi-hole filling. **Gate:** exhaustive toy correctness/soundness checks.

**P2 — String scientific kernel:** paper-defined abstract string domains/operators, examples, real benchmark parsing. **Gate:** string oracle and property tests.

**P3 — Research evaluation:** original benchmark subset/full obtainable sets, fair ablations, comparison to published tables, reproducibility manifests. **Gate:** independent rerun from clean checkout.

**P4 — Studio:** FastAPI worker API, trace schema, SvelteKit 5 AST workbench, comparison visualization and export. **Gate:** UI renders exact machine-generated trace and cancels a runaway run.

**P5 — Submission:** report, known deviations, video/live demo script, public README, license and attribution. **Gate:** fresh-machine walkthrough succeeds.

## 10. Risks and decisions needing confirmation

- Paper supplement, official artifact, and exact corpus availability are an early verification task; sources not yet conclusively located for all datasets.
- The professor's rubric may demand only a subset, or forbid using the authors' implementation. Assume independent implementation and document any use of the original as an oracle only.
- Solver and Python performance may be a major bottleneck. Profile before considering Rust/Cython; do not optimize by changing semantics.
- Precise formal abstract domain definitions must be transcribed from the PDF/supplement before implementing them; this design intentionally avoids inventing their lattice details.
- Timeline and grading criteria remain unannounced; milestones are scope gates rather than time promises.

## 11. Sources

- https://doi.org/10.1145/3776694
- https://popl26.sigplan.org/details/POPL-2026-popl-research-papers/54/Inductive-Program-Synthesis-by-Meta-Analysis-Guided-Hole-Filling
