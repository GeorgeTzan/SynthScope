#!/usr/bin/env bash
set -euo pipefail
py="${PYTHON:-python}"
"$py" experiments/gen_suite.py
"$py" experiments/hd8.py
"$py" experiments/run.py experiments/suite8
"$py" experiments/run.py benchmarks/hd8
"$py" experiments/analyze.py
