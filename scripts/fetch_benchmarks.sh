#!/usr/bin/env bash
# Download the benchmark corpora used by the HOPE paper into ./benchmarks (git-ignored: GPL-3.0 data, not redistributed here).
# Source: github.com/yhyoon/simba, directory testcases/ (Simba's PLDI'23 artifact).
#   duet         205  string problems (the paper's Duet set)
#   bitvec-cond  750  conditional bitvector problems
#   deobfusc     500  deobfuscation problems
#   hd44          44  Hacker's Delight (reference-function style; needs Z3)
# Not available: HardBench (132 string problems).
set -euo pipefail
dest="${1:-benchmarks}"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
git clone --depth 1 https://github.com/yhyoon/simba.git "$tmp/simba"
src="$tmp/simba/testcases"
mkdir -p "$dest"
cp -r "$src/string" "$dest/duet"
cp -r "$src/bitvec-cond" "$dest/bitvec-cond"
cp -r "$src/bitvec/deobfusc" "$dest/deobfusc"
cp -r "$src/bitvec/hd" "$dest/hd44"
for d in duet bitvec-cond deobfusc hd44; do echo "$d: $(find "$dest/$d" -name '*.sl' | wc -l) files"; done
