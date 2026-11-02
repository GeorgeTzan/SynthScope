# Results

Raw JSONL (`*.jsonl`) is git-ignored; regenerate with `scripts/run_paper_ablations.sh DIR [timeout_s] [max_nodes]`.
Each record carries its configuration and environment (Python, Z3, platform, CPU, git SHA, seed).

## Smoke run (2026-11-01, `tests/sygus/fixtures`, hand-written, 2 problems)

| config | solved | nodes | analyzer calls | meta calls |
|---|---|---|---|---|
| hope, 1 hole | 2/2 | 213 | 211 | 101 |
| hope, 3 holes | 2/2 | 213 | 211 | 101 |
| leftmost | 2/2 | 105 | 103 | 0 |
| meta off (seeded random) | 2/2 | 213 | 211 | 0 |

These fixtures are tiny and not the paper's benchmarks, so they show only that the harness works. On them
the meta policy does not reduce nodes (leftmost is cheaper). No claim about the paper's results can be made
until the real Duet/HardBench/Bitvec corpora are run (see `research/benchmarks.md`).

## Sampled ablation (2026-11-02)

24 problems per corpus (seed 0), 20 s timeout, 50,000 nodes. Solved of 24 for hope_h1 / hope_h3 / leftmost / meta_off:
Duet 5/5/5/5, Bitvec-cond 1/1/1/1, Deobfusc 5/6/5/4, Hacker's Delight 5/5/5/5. No consistent advantage for HOPE at this
budget; this is a sample on a slow Python engine, not a reproduction of the paper's figures. CSV comparisons are in each
corpus folder; JSONL is git-ignored. Regenerate: `scripts/fetch_benchmarks.sh` then `scripts/run_paper_ablations.sh DIR 20 50000 24 0`.
