# 8-bit experiments

Compares four hole-selection strategies on 8-bit bitvector synthesis. Regenerate everything with
`PYTHON=.venv/bin/python experiments/run_all.sh` (needs `scripts/fetch_benchmarks.sh` first for Suite A).

## Frozen parameters (2026-11-10, after the pilot, before the full run)

| | |
|---|---|
| Grammar `G8` | width 8; `x`, `y`; `#x00`, `#x01`, `#xFF`; `bvnot`, `bvneg`; `bvand`, `bvor`, `bvxor`, `bvadd`, `bvsub`, `bvshl`, `bvlshr` |
| Suite C (`experiments/suite8`, committed) | random targets of AST size 3, 5, 7, 9; 25 per size; generator seed 0; 6 examples each |
| Suite A (`benchmarks/hd8`, generated) | 44 Hacker's Delight problems rewritten from 64 to 8 bits, checked with Z3 |
| Strategies | `leftmost`; `random` (seeds 0, 1, 2); `meta` = paper's Algorithm 2, one hole at a time (seeds 0, 1, 2); `constrained` |
| Component size | 1 (plain top-down, main setting) and 3 |
| Budget | 30 s per run, no effective node cap, 3 configurations in parallel |

A problem counts as solved by `random` or `meta` only if every seed solves it; their per-problem numbers are medians over seeds.

## Pilot

20 problems sampled from Suite C (sample seed 0), 12 from Suite A, same budget.

| target size | runs solved, component size 1 | runs solved, component size 3 |
|---|---|---|
| 3 | 21/21 | 21/21 |
| 5 | 49/49 | 49/49 |
| 7 | 28/49 | 28/49 |
| 9 | 7/21 | 7/21 |

Suite A: 1 of 12 sampled problems solved by every configuration (5 of the 12 are the hardest `d5` variants).

None of the feasibility rules of the plan applied, so sizes, counts and the timeout are unchanged.

## Changes made at the pilot

- **Fourth strategy `constrained` added.** The pilot showed that on `G8` the paper's meta analysis ranks almost every hole
  Rank-1, so `meta` picks like `random`. `constrained` picks the hole whose necessary precondition, from the underlying
  analysis of the current candidate, admits the fewest values (ties: leftmost). It was added after seeing pilot results and
  before the full run; no suite parameter was changed for it.
- **Suite A rewrite:** the constant 63 (width minus one at 64 bits) becomes 7 instead of its low byte, so shift-by-sign-bit
  tasks keep their meaning.

Pilot timings are not reported: the pilot shared the machine with other runs.

## Files

- `gen_suite.py`, `hd8.py`: build the suites. `run.py`: run all configurations, resumable. `analyze.py`: CSV and figures.
- Results: `results/exp8/runs.csv`, `summary.csv`, `paired.csv`. Figures: `report/figures/`.
