"""Validate a built scene_manifest.json without needing Blender.

    python expansion/scripts/check_scene.py OUT/scene_manifest.json

The OBJ path runs on plain Python, so this is the cheap gate that catches
geometry and contract regressions before a runner pays for a Cycles render.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent

# Floors, not targets: the scene may grow, but a silent collapse to a fraction
# of the town means a layout or asset regression.
MIN_COUNTS = {
    "instances": 800,
    "mesh_objects": 12000,
    "unique_meshes": 4000,
    "faces": 700_000,
    "sockets": 1000,
}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("manifest", type=Path)
    args = p.parse_args()

    report = json.loads(args.manifest.read_text(encoding="utf-8"))
    problems: list[str] = []

    if report.get("schema_version") != 1:
        problems.append(f"schema_version is {report.get('schema_version')!r}, expected 1")

    stage = report.get("stage")
    if stage not in ("blockout", "detail"):
        problems.append(f"stage is {stage!r}")

    counts = report.get("counts") or {}
    for key, floor in MIN_COUNTS.items():
        got = counts.get(key)
        if not isinstance(got, int):
            problems.append(f"counts.{key} missing")
        elif got < floor:
            problems.append(f"counts.{key}={got} below floor {floor}")

    instances = report.get("instances") or []
    if len(instances) != counts.get("instances"):
        problems.append(f"{len(instances)} instances listed, counts says {counts.get('instances')}")

    districts: dict[str, int] = {}
    seen_ids: set[str] = set()
    missing_tasks: set[str] = set()
    for entry in instances:
        name = entry.get("id")
        if not name:
            problems.append("instance without an id")
            continue
        if name in seen_ids:
            problems.append(f"duplicate instance id {name}")
        seen_ids.add(name)

        districts[entry.get("district", "?")] = districts.get(entry.get("district", "?"), 0) + 1

        task = entry.get("task")
        if task and not (ROOT / task).exists():
            missing_tasks.add(task)

        location = entry.get("location")
        if not (isinstance(location, (list, tuple)) and len(location) == 3):
            problems.append(f"{name} has a malformed location")

    for task in sorted(missing_tasks):
        problems.append(f"task brief not in repo: {task}")

    # WORLD holds the shared water and canal network; the twelve districts are
    # the authored ones and every id maps back to config/world.json.
    authored = {d for d in districts if d != "WORLD"}
    if len(authored) != 12:
        problems.append(f"{len(authored)} districts present, expected 12: {sorted(authored)}")

    for district, total in sorted(districts.items()):
        if district != "WORLD" and total < 10:
            problems.append(f"district {district} only has {total} instances")

    if not report.get("limitations"):
        problems.append("limitations list is empty; the delivery contract is unstated")

    print(f"stage={stage} instances={len(instances)} districts={len(districts)}")
    print("counts: " + json.dumps(counts, sort_keys=True))

    if problems:
        print("\nFAILED:")
        for line in problems:
            print("  - " + line)
        raise SystemExit(1)
    print("manifest OK")


if __name__ == "__main__":
    main()
