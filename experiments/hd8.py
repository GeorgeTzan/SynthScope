"""Rewrite the 64-bit Hacker's Delight problems to 8 bits: sorts become (BitVec 8), constants keep their low byte, 63 becomes 7."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def rewrite(text: str) -> str:
    text = text.replace("(BitVec 64)", "(BitVec 8)")
    text = re.sub(r"#x0{14}3[Ff]\b", "#x07", text)
    return re.sub(r"#x[0-9A-Fa-f]{14}([0-9A-Fa-f]{2})\b", r"#x\1", text)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--src", type=Path, default=Path("benchmarks/hd44"))
    ap.add_argument("--out", type=Path, default=Path("benchmarks/hd8"))
    args = ap.parse_args(argv)
    files = sorted(args.src.glob("*.sl")) if args.src.is_dir() else []
    if not files:
        print(f"no .sl files in {args.src}; run scripts/fetch_benchmarks.sh first", file=sys.stderr)
        return 2
    args.out.mkdir(parents=True, exist_ok=True)
    for f in files:
        (args.out / f.name).write_text(rewrite(f.read_text(encoding="utf-8")), encoding="utf-8")
    print(f"{len(files)} problems written to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
