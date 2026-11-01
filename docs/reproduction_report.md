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

Test counts at the time of writing: 468 Python tests, 21 dashboard tests, all passing.

## Measured evidence

`results/README.md`: on two **hand-written** fixtures (one bitvector, one string) every policy solved both problems.
HOPE expanded more nodes than the leftmost policy (213 vs 105). Two tiny problems say nothing about the paper's
claims; they only show the harness works. The paper's benchmark corpora (Duet, HardBench, Bitvec-cond, Deobfusc,
Hacker's Delight) were **not downloaded or run**. Paper Fig. 7/10 numbers are therefore **not reproduced or refuted**.

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
6. **Dashboard** is reduced from the mockup (no separate examples/grammar/analysis-state/benchmark panels); event counts shown
   may undercount because noisy events are throttled to 300/s; verified through the dev proxy with a websocket client, not in a browser.
7. Python is slower than the authors' OCaml; no timing parity is claimed.

## Not done

Running the real benchmark corpora and comparing to the paper; matplotlib figures; browser-level end-to-end tests.
