#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
pandoc report.md -o report.pdf --pdf-engine=xelatex \
  -V geometry:margin=2.2cm -V fontsize=11pt -V lang=el \
  -V mainfont="Liberation Serif" -V monofont="Liberation Mono" -V colorlinks=true
pages="$(pdfinfo report.pdf | awk '/^Pages:/ {print $2}')"
echo "report.pdf: $pages pages"
if [ "$pages" -lt 3 ] || [ "$pages" -gt 5 ]; then
  echo "the report must be 3 to 5 pages" >&2
  exit 1
fi
