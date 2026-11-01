# Known deviations from the paper

1. Incremental meta analysis (paper §4.5.2) not implemented. It is a speed optimization; results are unchanged.
2. Python, not OCaml; no timing parity claimed.
3. Underlying-domain operators marked MISSING in operator_matrix.csv are NOT in the paper text and not in the Simba text. See the audit decision recorded below.
4. Random Rank-3 pick uses a seeded `random.Random` so runs repeat.

## Audit decision (2026-11-01)
Author chose "derive and test": missing underlying-domain operators are written from the paper/Simba text plus textbook interval and bitwise abstract interpretation, each proven sound by exhaustive small-width tests. Precision may differ from the authors. The suffix-domain string operators are derived as duals of the prefix operators. The meta-analysis (paper core) is fully specified and implemented exactly.
