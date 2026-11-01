# SynthScope Design

**Date:** 2026-11-01
**Status:** Draft, awaiting approval
**Paper:** Lee, Lee & Yi, *Inductive Program Synthesis by Meta-Analysis-Guided Hole Filling*, POPL 2026 (`docs/paper.pdf`). The tool in the paper is called HOPE.
**Supersedes:** `docs/2026-10-30-hope-studio-design.md` and `docs/2026-10-30-hope-engine-and-studio.md` (ChatGPT drafts). Kept for reference only. This doc wins on conflict.

## 1. Intent and why

The course assignment: hand in an independent reimplementation of the paper. The engine is what gets graded. The paper's idea: when top-down synthesis fills holes in a partial program, the order matters. A "meta analysis" predicts which hole, once filled, lets the pruning analysis (forward-backward abstract interpretation) discard infeasible candidates earliest. Fill that hole first.

The author also wants a SvelteKit 5 dashboard (mockup: `docs/Untitled.png`) that shows a synthesis run live. This is an extra. It must never delay or distort the engine.

## 2. Goals

1. Engine reimplements the paper's algorithm: top-down partial-program search with holes, bottom-up component enumeration, forward/backward abstract-interpretation pruning, meta analysis for hole ranking, multi-hole filling.
2. Both domains: **bitvectors and strings**, including the paper's new string abstract domain.
3. Every synthesized program is checked against the examples by an independent concrete evaluator.
4. Ablations on the same harness, grammar, and budget: paper policy (meta analysis on), fixed leftmost order, meta analysis off, and 1 vs several holes filled at once.
5. CLI runs a synthesis problem or a benchmark set and writes a machine-readable report, with no web dependencies.
6. Extra: SvelteKit 5 dashboard shows real engine events live over a websocket.

## 3. Non-goals and anti-goals

- No LLM program generation. No `eval`/`exec` of user input. No accounts, cloud, or database.
- No promise of matching the authors' OCaml timings. Report deviations honestly.
- **Anti-goal:** fabricated or simulated visualization data. The UI draws only events the engine emitted.
- **Anti-goal:** an unsound speedup. Pruning must never discard a program that could be a solution. Silently approximating an unsupported operator is a failure; reject it with a clear error instead.
- **Anti-goal:** UI work before the engine passes its tests.

## 4. Constraints

- Language and tools are unrestricted by the assignment. Deadline and grading rubric unknown. Phases are scope gates, not date promises.
- Definitions of abstract domains, transfer functions, and ranking rules must be transcribed from the paper (and its supplement if obtainable), never written from memory.
- The folder is not a git repository yet. Run `git init` before the first commit.

## 5. Approaches considered

| | Approach | Trade-off |
|---|---|---|
| **A (chosen)** | Python engine, FastAPI + websocket, SvelteKit 5 | Fast to write, strong testing tools (pytest, Hypothesis). Slower search loop than OCaml; measure before optimizing. |
| B | OCaml engine, like the authors | Closest and fastest. Learning cost, and risks becoming a port of their code. UI needs a bridge. |
| C | TypeScript engine, SvelteKit only | One language. Weaker solver and test tooling, slow search. |

Chosen: **A**, per the author's pick, and it was my recommendation.

Trimmed from the ChatGPT plan (ponytail): no Docker, no Playwright, no generated API client, no database, no process-pool service in v1. Websocket instead of SSE because the author asked for it, and it enables pause, step, and cancel commands later.

## 6. Architecture

```text
SyGuS files / CLI  -->  hope_engine (pure Python, no web imports)
                          grammar + typed AST (holes, paths)
                          concrete semantics (bitvector, string)
                          component enumeration (bottom-up)
                          search (top-down, worklist of partial programs)
                            underlying analysis: forward + backward abstract interp
                            meta analysis: ranks holes
                            hole policy: paper | leftmost | meta-off
                            multi-hole filling
                          independent validation
                          event sink (optional, off by default)
                               |                    \
                         CLI + JSONL report        FastAPI websocket
                                                        |
                                                   SvelteKit 5 UI
```

Rules:
- `hope_engine` never imports FastAPI or anything web. All policies share the same search, components, and pruning code. Only hole selection differs.
- Events are opt-in. Benchmark timing runs with events off.
- Synthesis runs in a child process so it can be cancelled and never blocks the API.
- Event schema: `{run_id, seq, kind, payload}`. Kinds: `search_started`, `candidate_expanded`, `forward_analysis`, `backward_analysis`, `hole_ranked`, `pruned`, `hole_filled`, `solution_found`, `run_finished`.

## 7. Phases and gates

- **P0 Paper audit.** Read the full paper (and supplement if found). Write down every domain, operator, transfer rule, rank rule, and algorithm step with page citations. *Gate:* no unknown formula remains.
- **P1 Bitvector engine.** AST, concrete semantics, components, search, forward/backward analysis, meta analysis, policies, multi-hole. *Gate:* exhaustive small-width soundness tests pass.
- **P2 String engine.** String semantics, abstract domain, meta analysis. *Gate:* exhaustive short-string soundness tests pass.
- **P3 Evaluation.** SyGuS import, CLI, ablation runs, report. *Gate:* clean rerun reproduces the report.
- **P4 Dashboard (extra).** Event websocket, SvelteKit 5 UI matching the mockup with real operators. *Gate:* UI shows a real recorded and a live run; cancel works.
- **P5 Writeup.** Report, known deviations, README.

## 8. Testing and correctness

- Concrete bitvector operators checked against Z3 for small widths (Z3 is a test oracle only, unless the paper needs it inside search).
- Abstract operators: over small finite universes, every concrete result lies in the abstraction, and every backward restriction keeps all valid solutions.
- Pruned search returns the same solutions as exhaustive search on tiny grammars.
- Record outcome per instance: solved, validated, timeout, unsupported, exhausted within bound. Exhausted within a bound is not proof of unsatisfiable.
- Record environment: Python, Z3 version, machine, seed, timeout.

## 9. Dashboard (extra)

Follows `docs/Untitled.png`: examples panel, grammar panel, partial-program AST with holes and their ranks, analysis state, live synthesis log, best candidate, statistics, search-progress chart, benchmark summary. Svelte 5 runes for state; components are presentation only. Mockup uses toy arithmetic; the real UI shows the paper's operators and domain states. Pause means replay of the recorded trace unless live pause is added later.

## 10. What is left to the builder

Module layout inside `hope_engine`, exact data structures, Python version, test layout, chart library, styling details. Decide the benchmark subset after P0 finds what is obtainable.

## 11. Open risks

- Paper supplement and the authors' benchmark corpus may be hard to obtain. P0 checks this first.
- Python search speed may limit benchmark coverage.
- Rubric may ask for specific experiments; adjust P3 when known.

## 12. What the paper already fixes (read 2026-11-01, pages 1-14 and 21-30)

Given in the paper body, so P0 only transcribes it:
- **Algorithm 1** (generic synthesis loop with queue, component map, `Analyze`, `PickHole`) and **Algorithm 2** (meta-analysis hole picking: Rank-1, Rank-2, else random Rank-3 with a "no pruning possible" flag that skips the underlying analysis). Defs 3.1-3.7 (pruning power, admissible strategy).
- **Underlying analysis** (§4.2): forward least fixpoint, backward greatest fixpoint, alternating chain until it converges.
- **Meta domain** (§4.3): `D# = {⊥, Must⊤, May⊤̸}`, hypothetical hole `pos` maps to `May⊤̸`, constants map to `May⊤̸`, other nonterminals to `Must⊤`. Strings use the product of the prefix/suffix meta domains with a length domain `{Con, Bnd, Unb}` (Figs. 5 and 6, "selected" operators).
- **Evaluation setup** (§5): 60 s timeout. Strings: 337 problems (Duet 205, HardBench 132). Bitvectors: 1,294 problems (Bitvec-cond 750, Deobfusc 500, Hacker's Delight 44). Ablations: HOPE vs HOPE⁻ (no meta analysis), and 1 / up-to-3 / up-to-5 holes at once on strings.

**Not yet read:** pages 15-20 (§4.4 onward: bitvector and string underlying domains and operators, §4.5 multi-hole filling). P0 reads them before any domain code. The ACM supplement was not located; if it holds definitions the paper body lacks, P0 records that in `research/known_deviations.md`. **If a needed definition exists nowhere, stop and ask the author rather than invent it.**

## 13. Decisions from the builder check

My calls (author can overrule):
- **Validation:** a small separate concrete evaluator checks every solution. The search's analysis code never evaluates final answers. Z3 is a test oracle only; it is not needed at runtime.
- **Budget:** each run has a node-count cap (partial programs expanded) and the paper's 60 s wall-clock timeout. Both are logged. Ablation comparisons use the node cap, so reruns are reproducible.
- **Benchmarks:** use whatever of the paper's suites (SyGuS-IF format) can be obtained. If the corpus is unavailable, fall back to a small hand-written set per domain, labelled as such, and say so in the report.
- **Dashboard fidelity:** follow the mockup layout loosely. v1 has cancel and trace replay, no live pause or step. The engine batches analysis events and caps events per second so big runs do not flood the socket.
- **Priority (author confirmed):** a faithful algorithm matters most. No deadline yet. Benchmark numbers matter less than correctness.
- **Scope-cut order if time runs short:** drop the dashboard first, then large benchmark runs, then extra ablation variants. Never drop strings, because the assignment needs both domains. Never trade algorithm fidelity for speed or coverage.
