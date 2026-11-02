#!/usr/bin/env bash
# Paper-style ablations on one benchmark directory: HOPE (1 and 3 holes), leftmost, meta off.
# Usage: scripts/run_paper_ablations.sh DIR [TIMEOUT_S] [MAX_NODES] [LIMIT] [SAMPLE_SEED]
# Results go to results/<dir name>/. LIMIT runs a seeded random sample (same seed = same problems in every config).
set -euo pipefail
dir="${1:?benchmark directory}"; timeout="${2:-60}"; nodes="${3:-100000}"; limit="${4:-}"; seed="${5:-0}"
py="${PYTHON:-python}"
out="results/$(basename "$dir")"
mkdir -p "$out"
sample=(); [ -n "$limit" ] && sample=(--limit "$limit" --sample-seed "$seed")
run() { "$py" -m hope_engine.cli bench "$dir" --timeout "$timeout" --nodes "$nodes" "${sample[@]}" --out "$out/$1.jsonl" "${@:2}"; }
run hope_h1 --policy hope --holes 1
run hope_h3 --policy hope --holes 3
run leftmost --policy leftmost
run meta_off --policy meta_off
"$py" -m hope_engine.cli compare "$out/hope_h3.jsonl" "$out/leftmost.jsonl" --csv "$out/hope_vs_leftmost.csv"
"$py" -m hope_engine.cli compare "$out/hope_h3.jsonl" "$out/meta_off.jsonl" --csv "$out/hope_vs_meta_off.csv"
"$py" -m hope_engine.cli compare "$out/hope_h1.jsonl" "$out/hope_h3.jsonl" --csv "$out/h1_vs_h3.csv"
"$py" -m hope_engine.cli report "$out"/*.jsonl
