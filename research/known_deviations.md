# Known deviations from the paper

1. Incremental meta analysis (paper §4.5.2) not implemented. It is a speed optimization; results are unchanged.
2. Python, not OCaml; no timing parity claimed.
3. Underlying-domain operators marked MISSING in operator_matrix.csv are NOT in the paper text and not in the Simba text. See the audit decision recorded below.
4. Random Rank-3 pick uses a seeded `random.Random` so runs repeat.

## Audit decision (2026-11-01)
Author chose "derive and test": missing underlying-domain operators are written from the paper/Simba text plus textbook interval and bitwise abstract interpretation, each proven sound by exhaustive small-width tests. Precision may differ from the authors. The suffix-domain string operators are derived as duals of the prefix operators. The meta-analysis (paper core) is fully specified and implemented exactly.

## Bitvector underlying domain (Task 5)

Reduced product of known-bits, unsigned interval, signed interval (Simba §4.2) with iterated reduction.
Derived (not copied) operators; all proven sound by exhaustive tests at widths 1-3 plus mutation checks.
Precision gaps versus the authors' tool (all sound, may prune less):
- bvsdiv, bvudiv (bitwise part), bvashr backward, shift-amount backward, bvurem backward except msb case: no refinement.
- bvmul backward: only for odd constant operand (modular inverse) and zero constant; no trailing-zero reasoning.
- Signed intervals crossing the sign boundary are over-approximated by the full range.
- Shift semantics follow SMT-LIB (amounts >= width), not "mod width" as the Simba text writes for abstract shifts.

## String underlying domain (Task 9)

Prefix-with-length x suffix-with-length reduced product, plus int intervals and an untyped top (holes carry no type).
Derived rules; sound against exhaustive tests (strings over {a,b} up to length 3). The `alphabet` constructor argument in the plan is not needed.
Refined forward rules: concat, at, CharAt0, len, substr (constant args), to.int, int.to.str. Refined backward: concat, at, CharAt0, len.
All other operators use the paper's default (bottom if an argument is bottom, else top).
Unlike the paper's overview (suffix only), the prefix part already prunes ConCat(x,[],[]) for f("Jan","Kotas")="J.K".
