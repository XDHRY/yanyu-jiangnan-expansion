"""Assert the 340-card board is well-formed and the loop is honest.

    python expansion/scripts/check_board.py
    python expansion/scripts/check_board.py --require-implemented 80
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOARD = ROOT / "catalog" / "board.json"
LEGAL = {"planned", "implemented", "validated", "integrated"}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--board", type=Path, default=BOARD)
    p.add_argument("--require-implemented", type=int, default=80)
    args = p.parse_args()

    board = json.loads(args.board.read_text(encoding="utf-8"))
    problems: list[str] = []

    if board.get("schema_version") != 1:
        problems.append(f"schema_version {board.get('schema_version')!r}")
    if board.get("loop") != ["planned", "implemented", "validated", "integrated"]:
        problems.append(f"loop is {board.get('loop')!r}")

    tasks = board.get("tasks") or []
    if len(tasks) != 340:
        problems.append(f"{len(tasks)} cards, expected 340")

    seen: set[str] = set()
    counts: dict[str, int] = {}
    for card in tasks:
        tid = card.get("id")
        if not tid:
            problems.append("card without id")
            continue
        if tid in seen:
            problems.append(f"duplicate {tid}")
        seen.add(tid)
        status = card.get("status")
        if status not in LEGAL:
            problems.append(f"{tid} status {status!r}")
        counts[status] = counts.get(status, 0) + 1
        if status in ("validated", "integrated") and not card.get("evidence"):
            problems.append(f"{tid} is {status} but has no evidence")

    implemented = counts.get("implemented", 0) + counts.get("validated", 0) + counts.get("integrated", 0)
    if implemented < args.require_implemented:
        problems.append(f"implemented-or-better={implemented} below {args.require_implemented}")

    print("board total={0} counts={1}".format(len(tasks), json.dumps(counts, sort_keys=True)))
    if problems:
        print("\nFAILED:")
        for line in problems:
            print("  - " + line)
        raise SystemExit(1)
    print("board OK")


if __name__ == "__main__":
    main()
