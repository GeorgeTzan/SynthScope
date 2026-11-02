# Reproduction report

Paper: Lee, Lee & Yi, POPL 2026 (HOPE). Design: `docs/superpowers/specs/2026-11-01-synthscope-design.md`.
Status date: 2026-11-01. **No claim about the paper's benchmark results is made here: the paper's corpora were not run.**

## What was built and where it is tested

| Paper item | Code | Evidence |
|---|---|---|
| Algorithm 1 (queue, components, Analyze, PickHole, line 14 filter, noprune) | `enumeration/search.py`, `components.py` | `tests/enumeration` |
| Underlying forward/backward analysis (§4.2) | `domains/analysis.py` | `tests/domains/*/test_*pruning.py` |
| Bitvector domain (bitwise x signed x unsigned interval, reduction) | `domains/bitvector/` | exhaustive soundness, widths 1-3; mutation-checked |
| String domain (prefix/suffix with length) | `domains/string/` | soundness over all strings of {a,b} up to length 3 |
| Meta domain, Analyze#, Rank-1/2, Algorithm 2 | `meta/` | all 12 cells of Example 4.1 table reproduced exactly (`tests/meta/test_paper_examples.py`) |
| Meta soundness (Thm 4.2/4.4, tested not proved) | `meta/bitvector.py`, `meta/string.py` | randomized partial programs vs. the underlying analysis; fails under mutation |
| Multi-hole filling (§4.5.1), default 3 | `meta/rank.py`, `enumeration/multifill.py` | `(h+h)+(h+h)` needs 2 holes; single holes do not rank |
| Concrete semantics | `concrete/` | bitvector ops vs Z3 (widths 1-4, exhaustive); string ops vs Z3 (Hypothesis) |
| SyGuS-IF import | `sygus/parser.py` | hand-written fixtures; line/column errors |
| Ablations: HOPE (1/3 holes), leftmost, meta off | `bench/`, `cli.py`, `scripts/` | harness runs; see results below |

Test counts at the time of writing: 565 Python tests, 65 dashboard tests, all passing.

## Measured evidence

Real corpora fetched by `scripts/fetch_benchmarks.sh` (Simba artifact repo, GPL-3, not committed): Duet 205, Bitvec-cond 750,
Deobfusc 500, Hacker's Delight 44 problems. All parse. HardBench (132) was **not available** and is not run.

**Sampled ablation, not the paper's setup:** 24 random problems per corpus (`--limit 24 --sample-seed 0`), 20 s timeout,
50,000-node cap, Python engine. Solved counts out of 24 (every solution re-validated; Hacker's Delight is checked by a Z3
counterexample loop):

| corpus | HOPE, 1 hole | HOPE, up to 3 holes | leftmost | meta off |
|---|---|---|---|---|
| Duet (strings) | 5 | 5 | 5 | 5 |
| Bitvec-cond | 1 | 1 | 1 | 1 |
| Deobfusc | 5 | 6 | 5 | 4 |
| Hacker's Delight | 5 | 5 | 5 | 5 |

Reading, stated plainly: at this budget the four configurations solve almost the same problems. The only spread is
Deobfusc (6 vs 4–5), one problem, within noise at n = 24. Mean seconds on solved problems and node totals differ by config
but without a consistent winner (see `results/*/*.csv`). **The paper's claim that meta-analysis-guided hole picking solves
more problems or faster is neither reproduced nor refuted here.** Likely reasons: a Python engine 100x slower than the
authors' OCaml (strings run at 150-300 nodes/s) so most problems time out before the policy matters; a small sample; derived
(possibly less precise) abstract operators.

## Deviations and limitations (all also in `research/known_deviations.md` and the ledger rulings)

1. **Missing supplements.** The HOPE supplement and the Simba supplement (full operator tables, proofs) are not public. Underlying
   operators the paper text does not give were **derived** from the text plus standard known-bits and interval reasoning,
   and proved sound only by testing. They may be less precise than the authors', which can change how much is pruned.
2. **Meta operators** not printed in Figs 1, 2, 5, 6 use a conservative default (`MAY_NOT_TOP`). The string meta element
   (four flags) is an equivalent re-encoding of the paper's length chain, not a copy.
3. **Incremental meta analysis (§4.5.2)** is not implemented (speed only).
4. **Search details not in the paper:** no restart with larger component sets; unproductive partial programs dropped; per-step
   child cap at `max_nodes`; among ranked hole subsets the smallest is chosen. Rank-3 picks use a seeded RNG.
5. **Meta soundness is tested, not proved**, on random small programs (width 2, strings over {a,b}).
6. **Dashboard** follows the mockup (examples, grammar, AST graph, holes, abstract state, log, stats, chart, benchmark summary),
   all driven by real engine events; event counts may undercount because noisy events are throttled to 300/s. Checked in real
   Chrome via Playwright screenshots, not by automated browser tests.
7. Python is slower than the authors' OCaml; no timing parity is claimed.

## Not done

HardBench; a full-corpus run at the paper's budget; matplotlib figures; automated browser-level end-to-end tests.

Reference-function problems (Hacker's Delight) need Z3 at run time (sample plus counterexample loop).
