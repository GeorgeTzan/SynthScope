# Paper-to-code mapping

Paper = `docs/paper.pdf` (HOPE, POPL 2026). Page numbers are PDF page numbers (journal numbering 52:N = PDF page N).
Simba = Yoon, Lee, Yi, PLDI 2023 (arXiv 2304.10768, `research/sources/simba/simba.pdf`).
Status: SPEC = fully given in text; PARTIAL = selected cases only; EXTERNAL = lives in supplement or Simba; MISSING = not found.

| Item | Source | Status | Planned module / test |
|---|---|---|---|
| RTG, partial program, positions, holes | Paper p.7-8 §3.1 | SPEC | `syntax/` Task 2 |
| Algorithm 1 (synthesis loop, queue, C, Analyze, PickHole) | p.9 | SPEC | `enumeration/search.py` Task 4 |
| Pruning power Θ, Θ̂, admissible strategy (Defs 3.1-3.7), `noprune` change to lines 12-13 | p.9-11 | SPEC | `meta/rank.py` Task 6 |
| Underlying Analyze: forward lfp F, backward gfp B, alternating chain Ẋ | p.13-14 §4.2 | SPEC | `domains/analysis.py` Task 5 |
| Infeasible(P,A,i↦o) = ∃p. A(p)=⊥ | p.14 | SPEC | `DomainAnalyzer` Task 5 |
| Meta domain D# = {⊥, Must⊤, May⊤̸}; γ | p.14 §4.3 | SPEC | `meta/lattice.py` Task 6 |
| Meta forward F##/F# (hole pos and constants ↦ May⊤̸, nonterminals ↦ Must⊤) | p.14-15 | SPEC | `meta/analysis.py` Task 6 |
| Meta backward B#/B## (root ↦ May⊤̸, others ↦ Must⊤); chain with ⊔ and lfp | p.15 | SPEC | `meta/analysis.py` Task 6 |
| Analyze#(P,i↦o) returns pair (A#_F, A#_B) per position | p.15 | SPEC | `meta_analyze` Task 6 |
| Worked ConCat example, tables (4)-(6) | p.5-6, 15-16 | SPEC | golden test Task 6 |
| Theorem 4.2 (meta soundness), Thm 4.4 (admissible); proofs | p.16-17 | proof EXTERNAL | tested by exhaustive search, Tasks 6, 10 |
| Rank-1 condition (7), Rank-2 condition (8) | p.17 §4.4 | SPEC | `may_infeasible`, `may_prune_components` |
| Algorithm 2 PickHole (Rank-1, else Rank-2, else random + noprune) | p.13 | SPEC | `meta/rank.py` Task 6 |
| Multi-hole subsets, max holes default 3 | p.17-18 §4.5.1 | SPEC (prose only) | `enumeration/multifill.py` Task 7 |
| Incremental meta analysis | p.18 §4.5.2 | SPEC (prose) | SKIPPED, see known_deviations.md |
| Bitvector underlying domain: bitwise x signed interval x unsigned interval, reduction ρ | Paper p.18 → Simba §4.2 p.11-12 | PARTIAL | `domains/bitvector/` Task 5 |
| Bitvector underlying operators (full tables) | Simba supplement | EXTERNAL / MISSING | see operator_matrix.csv |
| Bitvector meta operators | Paper Fig 1, Fig 2 (p.19) | PARTIAL (Fig 2 "selected", rest "similar") | `meta/bitvector.py` Task 6 |
| String underlying domain: prefix+length x suffix+length | Paper p.19 §4.6.3, α/γ given | SPEC (domain), PARTIAL (operators) | `domains/string/` Task 9 |
| String forward ops ConCat, CharAt, StrToInt (prefix) | Paper Fig 3 p.20 | PARTIAL ("selected") | Task 9 |
| String backward ops ConCat 1/2, CharAt 1/2, StrToInt 1 (prefix) | Paper Fig 4 p.20 | PARTIAL | Task 9 |
| Suffix-domain operators | not shown | MISSING (dual of prefix, to derive) | Task 9 |
| String meta domain: (Ĉ# x I#) per prefix/suffix, I# = {⊥,Con,Bnd,Unb} | Paper p.20-21 | SPEC | `meta/string.py` Task 10 |
| String meta operators | Paper Fig 5, 6 p.21 | PARTIAL ("selected") | Task 10 |
| Default rule for unlisted operators: ⊥ if any arg ⊥ else ⊤ | Paper p.20 | SPEC | all domains |
| Evaluation: 60 s timeout; ablations HOPE vs HOPE⁻; 1 / up-to-3 / up-to-5 holes | Paper p.22-26 §5 | SPEC | Task 12 |
