"""Rebuild the authoritative Jiangnan scene from jiangnan.py in headless Blender.

The current generator is headless-safe. This wrapper still understands two
legacy source defects so older commits can be diagnosed/rebuilt, but it only
patches them when those exact legacy anchors are present. Current repaired
source executes without runtime modification.

Usage:
  blender -b --factory-startup --python-exit-code 1 \
      --python tools/headless_rebuild.py -- \
      --source jiangnan.py \
      --output ci_artifacts/Jiangnan-rebuilt.blend \
      --report ci_artifacts/rebuild-report.json \
      --stage 5
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import bpy


INTERACTIVE_SCENE_ASSIGN = "S=bpy.data.scenes.new(SCENE);bpy.context.window.scene=S"
BACKGROUND_SCENE_FIXED = "if bpy.app.background:\n        S=bpy.context.scene;S.name=SCENE\n    else:\n        S=bpy.data.scenes.new(SCENE);bpy.context.window.scene=S"
UV_LAYER_ASSIGN = "uv=o.data.uv_layers.new(name='远山全景UV')"
UV_LAYER_ASSIGN_FIXED = "uv_layer=o.data.uv_layers.new(name='远山全景UV')"
UV_LAYER_USE = "for loop in o.data.loops:uv.data[loop.index].uv=uvs[loop.vertex_index]"
UV_LAYER_USE_FIXED = "for loop in o.data.loops:uv_layer.data[loop.index].uv=uvs[loop.vertex_index]"


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--source", default="jiangnan.py")
    p.add_argument("--output", default="ci_artifacts/Jiangnan-rebuilt.blend")
    p.add_argument("--report", default="ci_artifacts/rebuild-report.json")
    p.add_argument("--stage", type=int, choices=range(1, 6), default=5)
    p.add_argument("--seed", type=int, default=None)
    return p.parse_args(argv)


def resolve(path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else Path.cwd() / p


def prepare_factory_scene() -> None:
    scene = bpy.context.scene
    for obj in list(scene.objects):
        bpy.data.objects.remove(obj, do_unlink=True)


def repair_if_legacy(text: str, old: str, new: str, label: str, applied: list[str]) -> str:
    """Accept a repaired source first; otherwise repair exactly one legacy anchor.

    Some repaired forms intentionally contain the original substring (the
    interactive branch remains inside an if/else), so checking old/new counts as
    mutually exclusive is incorrect. Presence of exactly one repaired anchor is
    authoritative.
    """
    new_count = text.count(new)
    if new_count == 1:
        return text
    if new_count > 1:
        raise RuntimeError(f"{label} repaired anchor duplicated: {new_count}")

    old_count = text.count(old)
    if old_count == 1:
        applied.append(label)
        return text.replace(old, new, 1)
    raise RuntimeError(
        f"{label} source state ambiguous; legacy={old_count}, repaired={new_count}. "
        "Refuse to guess so CI cannot hide a new generator defect."
    )


def load_generator(source_path: Path) -> tuple[dict, list[str]]:
    text = source_path.read_text(encoding="utf-8")
    applied: list[str] = []
    patched = repair_if_legacy(
        text,
        INTERACTIVE_SCENE_ASSIGN,
        BACKGROUND_SCENE_FIXED,
        "interactive_scene_assignment_to_background_scene",
        applied,
    )
    patched = repair_if_legacy(
        patched,
        UV_LAYER_ASSIGN,
        UV_LAYER_ASSIGN_FIXED,
        "art_upgrade_uv_layer_assignment",
        applied,
    )
    patched = repair_if_legacy(
        patched,
        UV_LAYER_USE,
        UV_LAYER_USE_FIXED,
        "art_upgrade_uv_layer_use",
        applied,
    )
    namespace = {
        "__name__": "jiangnan_headless_generator",
        "__file__": str(source_path),
    }
    exec(compile(patched, str(source_path), "exec"), namespace)
    return namespace, applied


def main() -> int:
    cfg = parse_args()
    source_path = resolve(cfg.source)
    output_path = resolve(cfg.output)
    report_path = resolve(cfg.report)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    prepare_factory_scene()
    module, runtime_repairs = load_generator(source_path)

    params = module["PARAMS"]
    params["output_dir"] = str(Path.cwd())
    params["stage"] = cfg.stage
    params["render"] = False
    if cfg.seed is not None:
        params["seed"] = cfg.seed

    started = time.time()
    module["build"](cfg.stage)
    elapsed = round(time.time() - started, 2)
    scene = module["S"]

    bpy.ops.wm.save_as_mainfile(filepath=str(output_path), compress=True)

    stats = module["statistics"]()
    images = [
        {
            "name": image.name,
            "filepath": image.filepath,
            "packed": bool(image.packed_file),
            "size": list(image.size),
        }
        for image in bpy.data.images
        if image.type == "IMAGE" and image.name not in {"Render Result", "Viewer Node"}
    ]
    scholar_stones = [obj.name for obj in scene.objects if "太湖石_瘦透漏皱" in obj.name]
    report = {
        "ok": True,
        "blender_version": bpy.app.version_string,
        "source": str(source_path),
        "output": str(output_path),
        "stage": cfg.stage,
        "seconds": elapsed,
        "statistics": stats,
        "images": images,
        "image_count": len(images),
        "packed_image_count": sum(bool(i["packed"]) for i in images),
        "upgraded_scholar_stones": scholar_stones,
        "runtime_repairs": runtime_repairs,
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("HEADLESS_REBUILD", json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
