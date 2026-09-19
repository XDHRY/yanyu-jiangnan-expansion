"""Pixel-level visual QA on rendered PNGs. Stdlib + optional Pillow.

Night Jiangnan is allowed to be dark; it is not allowed to be crushed, milky
or blown. This is a tripwire, not a beauty score.

    python expansion/scripts/check_visual_qa.py shots/
"""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

try:
    from PIL import Image
except ImportError:  # pragma: no cover - CI installs pillow
    Image = None

CAMERAS = (
    "JNX_TingYuXuan",
    "JNX_MoonGate_Vista",
    "JNX_Canal_Hero",
    "JNX_Lane",
    "JNX_Water_Level",
    "JNX_Overview",
)


def _stats(path: Path) -> dict:
    if Image is None:
        raise SystemExit("Pillow is required for visual QA")
    im = Image.open(path).convert("L")
    px = list(im.getdata())
    n = len(px)
    ordered = sorted(px)
    mean = sum(px) / n
    return {
        "file": path.name,
        "width": im.size[0],
        "height": im.size[1],
        "mean": round(mean, 2),
        "p01": ordered[max(0, n // 100)],
        "p50": ordered[n // 2],
        "p99": ordered[min(n - 1, 99 * n // 100)],
        "stdev": round(statistics.pstdev(px), 2),
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("shots", type=Path)
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    files = sorted(args.shots.glob("*.png"))
    if not files:
        raise SystemExit(f"no PNGs in {args.shots}")

    report = {"shots": [], "problems": []}
    for path in files:
        row = _stats(path)
        report["shots"].append(row)
        name = path.stem
        # Dead black: a night shot may have p01 of 1-8; 0 across the board
        # means the volume ate the frame or lights failed.
        if row["p01"] <= 0 and row["mean"] < 8:
            report["problems"].append(f"{name} crushed black mean={row['mean']}")
        # Milky fog: previous bug sat at mean 180+.
        if row["mean"] > 140:
            report["problems"].append(f"{name} milky mean={row['mean']}")
        # Blown AgX: night highlights should stay under ~200.
        if row["p99"] > 230:
            report["problems"].append(f"{name} blown p99={row['p99']}")
        # Flat: no contrast, plastic or fog wash.
        if row["stdev"] < 8:
            report["problems"].append(f"{name} flat stdev={row['stdev']}")

    present = {Path(s["file"]).stem for s in report["shots"]}
    if len(files) >= 4:
        for cam in CAMERAS:
            if cam not in present:
                report["problems"].append(f"missing camera {cam}")

    text = json.dumps(report, ensure_ascii=False, indent=2)
    print(text)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    if report["problems"]:
        raise SystemExit(1)
    print("visual QA OK")


if __name__ == "__main__":
    main()
