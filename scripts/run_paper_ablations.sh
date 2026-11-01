#!/usr/bin/env bash
# Paper-style ablations on one benchmark directory: HOPE (1 and 3 holes), leftmost, meta off.
# Usage: scripts/run_paper_ablations.sh DIR [TIMEOUT_S] [MAX_NODES]
set -euo pipefail
dir="${1:?benchmark directory}"; timeout="${2:-60}"; nodes="${3:-100000}"
py="${PYTHON:-python}"
mkdir -p results
run() { "$py" -m hope_engine.cli bench "$dir" --timeout "$timeout" --nodes "$nodes" --out "results/$1.jsonl" "${@:2}"; }
run hope_h1 --policy hope --holes 1
run hope_h3 --policy hope --holes 3
run leftmost --policy leftmost
run meta_off --policy meta_off
"$py" -m hope_engine.cli compare results/hope_h3.jsonl results/leftmost.jsonl --csv results/hope_vs_leftmost.csv
"$py" -m hope_engine.cli compare results/hope_h3.jsonl results/meta_off.jsonl --csv results/hope_vs_meta_off.csv
"$py" -m hope_engine.cli compare results/hope_h1.jsonl results/hope_h3.jsonl --csv results/h1_vs_h3.csv
"$py" -m hope_engine.cli report results/*.jsonl
