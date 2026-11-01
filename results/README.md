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
