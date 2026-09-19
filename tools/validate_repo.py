#!/usr/bin/env python3
"""Fast repository-level validation that does not require Blender.

Run this before any expensive Blender job. It checks source syntax, required
files, texture prompt metadata, and the material/asset manifests introduced by
the AI asset pipeline.
"""
from __future__ import annotations

import json
import py_compile
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ERRORS: list[str] = []
WARNINGS: list[str] = []


def require(path: str, min_bytes: int = 1) -> Path:
    p = ROOT / path
    if not p.exists():
        ERRORS.append(f"missing: {path}")
        return p
    if p.is_file() and p.stat().st_size < min_bytes:
        ERRORS.append(f"too small: {path} ({p.stat().st_size} bytes)")
    return p


def load_json(path: str):
    p = require(path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - validator should report all errors
        ERRORS.append(f"invalid json: {path}: {exc}")
        return None


def compile_python(path: str):
    p = require(path, 100)
    if not p.exists():
        return
    try:
        py_compile.compile(str(p), doraise=True)
    except Exception as exc:  # noqa: BLE001
        ERRORS.append(f"python compile failed: {path}: {exc}")


require("Jiangnan.blend", 1_000_000)
require("README.md", 500)

python_sources = [
    "jiangnan.py",
    "tools/ci_validate.py",
    "tools/render_preview.py",
    "tools/render_asset_preview.py",
    "tools/headless_rebuild.py",
    "tools/repair_jiangnan_source.py",
    "tools/generate_bamboo_asset.py",
    "tools/generate_architecture_assets.py",
    "tools/generate_prop_assets.py",
    "tools/generate_ground_assets.py",
]
for source in python_sources:
    compile_python(source)

expected_textures = ["plaster", "stone", "bark", "clay", "wood", "petal", "landscape"]
for name in expected_textures:
    require(f"textures/{name}.png", 10_000)

prompts = load_json("textures/generation_prompts.json")
if prompts is not None:
    text = json.dumps(prompts, ensure_ascii=False).lower()
    for name in expected_textures:
        if name not in text:
            WARNINGS.append(f"texture prompt metadata does not mention '{name}'")

texture_jobs = load_json("textures/texture_jobs.json")
if isinstance(texture_jobs, dict):
    jobs = texture_jobs.get("jobs", [])
    if not jobs:
        WARNINGS.append("texture job queue is empty")

materials = load_json("asset_db/materials.json")
if isinstance(materials, dict):
    rows = materials.get("materials", [])
    ids = {row.get("id") for row in rows if isinstance(row, dict)}
    for material_id in ["plaster", "stone", "bark", "clay", "wood", "petal"]:
        if material_id not in ids:
            ERRORS.append(f"material manifest missing id: {material_id}")

assets = load_json("asset_db/assets.json")
if isinstance(assets, dict):
    rows = [row for row in assets.get("assets", []) if isinstance(row, dict)]
    if len(rows) < 20:
        ERRORS.append(f"asset manifest expected >=20 MVP assets, found {len(rows)}")

    ids = [row.get("id") for row in rows]
    duplicates = sorted(k for k, n in Counter(ids).items() if k and n > 1)
    if duplicates:
        ERRORS.append(f"duplicate asset ids: {duplicates}")

    p0 = [row for row in rows if row.get("priority") == "P0"]
    planned_p0 = [row.get("id") for row in p0 if row.get("status") == "planned"]
    if planned_p0:
        ERRORS.append(f"P0 assets still lack blockout implementation: {planned_p0}")

    for row in p0:
        asset_id = row.get("id", "<missing-id>")
        factory = row.get("factory")
        if not factory:
            ERRORS.append(f"P0 asset missing factory mapping: {asset_id}")
            continue
        if not (ROOT / factory).exists():
            ERRORS.append(f"P0 asset factory does not exist: {asset_id} -> {factory}")

    status_counts = Counter(row.get("status", "missing") for row in rows)
    if status_counts.get("blockout", 0) < 20:
        WARNINGS.append(f"only {status_counts.get('blockout', 0)} MVP assets are at blockout or beyond")

print(json.dumps({
    "ok": not ERRORS,
    "errors": ERRORS,
    "warnings": WARNINGS,
}, ensure_ascii=False, indent=2))

sys.exit(1 if ERRORS else 0)
