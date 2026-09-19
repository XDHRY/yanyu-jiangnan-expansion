"""Headless-safe Blender validation for Jiangnan.blend.

Usage:
  blender -b Jiangnan.blend --python tools/ci_validate.py -- \
      --output validation/ci-validation.json

This script never saves the .blend and never renders. It is designed for CI.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import bpy

SCENE_NAME = "烟雨江南 · 雪月江南"
CONTROL_NAME = "JN_总控_天气0雨1雪_风力"
EXPECTED_TEXTURE_STEMS = {"plaster", "stone", "bark", "clay", "wood", "petal", "landscape"}


def cli_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="validation/ci-validation.json")
    parser.add_argument("--min-objects", type=int, default=2500)
    return parser.parse_args(argv)


def fail(report: dict, message: str) -> None:
    report.setdefault("errors", []).append(message)


def update_scene(scene) -> None:
    scene.frame_set(scene.frame_current)
    # In background mode there is no Window. The loaded file has one scene,
    # so the current view layer is already the correct dependency graph.
    bpy.context.view_layer.update()


def count_visible(scene, prefix: str) -> int:
    return sum(not obj.hide_render for obj in scene.objects if obj.name.startswith(prefix))


def mesh_signed_volume(obj) -> float:
    mesh = obj.data
    mesh.calc_loop_triangles()
    return sum(
        mesh.vertices[t.vertices[0]].co.dot(
            mesh.vertices[t.vertices[1]].co.cross(mesh.vertices[t.vertices[2]].co)
        ) / 6.0
        for t in mesh.loop_triangles
    )


def image_stem(image) -> str:
    candidates = [image.name, os.path.basename(image.filepath or "")]
    for value in candidates:
        stem = Path(value).stem.lower()
        if stem:
            return stem
    return ""


def main() -> int:
    args = cli_args()
    report: dict = {
        "ok": False,
        "blender_version": bpy.app.version_string,
        "background": bool(bpy.app.background),
        "errors": [],
        "warnings": [],
    }

    scene = bpy.data.scenes.get(SCENE_NAME)
    if scene is None:
        fail(report, f"missing scene: {SCENE_NAME}")
        return finish(report, args.output)

    control = bpy.data.objects.get(CONTROL_NAME)
    if control is None:
        fail(report, f"missing control object: {CONTROL_NAME}")
        return finish(report, args.output)

    report["scene_count"] = len(bpy.data.scenes)
    if len(bpy.data.scenes) != 1:
        fail(report, f"expected exactly one scene, got {len(bpy.data.scenes)}")

    report["objects"] = len(scene.objects)
    if len(scene.objects) < args.min_objects:
        fail(report, f"object count below baseline: {len(scene.objects)} < {args.min_objects}")

    report["cameras"] = sum(obj.type == "CAMERA" for obj in scene.objects)
    report["lights"] = sum(obj.type == "LIGHT" for obj in scene.objects)
    if report["cameras"] < 3:
        fail(report, f"expected >=3 cameras, got {report['cameras']}")
    if report["lights"] < 8:
        fail(report, f"expected >=8 lights, got {report['lights']}")

    # Weather exclusivity.
    report["weather"] = {}
    original_weather = control.get("Weather", 0)
    for state in (0, 1):
        control["Weather"] = state
        control.update_tag()
        scene.frame_set(80)
        update_scene(scene)
        values = {
            key: count_visible(scene, "JN_" + key)
            for key in ["雨丝", "雨落涟漪", "雪粒", "瓦上薄雪", "汀步薄雪"]
        }
        report["weather"][str(state)] = values
    rain = report["weather"]["0"]
    snow = report["weather"]["1"]
    if not (rain["雨丝"] > 0 and rain["雪粒"] == 0):
        fail(report, f"rain state invalid: {rain}")
    if not (snow["雪粒"] > 0 and snow["雨丝"] == 0):
        fail(report, f"snow state invalid: {snow}")

    # Motion driver smoke test.
    control["Weather"] = 0
    samples = {}
    for prefix in ["JN_风动枝组", "JN_雨丝", "JN_雪粒", "JN_云团"]:
        obj = next((o for o in scene.objects if o.name.startswith(prefix)), None)
        if obj is None:
            fail(report, f"missing motion sample: {prefix}")
            continue
        samples[prefix] = obj

    def snapshot(frame: int) -> dict:
        scene.frame_set(frame)
        update_scene(scene)
        return {
            name: list(obj.location) + list(obj.rotation_euler)
            for name, obj in samples.items()
        }

    a = snapshot(1)
    b = snapshot(100)
    report["motion_changed"] = {
        name: any(abs(x - y) > 1e-6 for x, y in zip(a[name], b[name]))
        for name in a
    }
    for name, changed in report["motion_changed"].items():
        if not changed:
            fail(report, f"motion did not change: {name}")

    # Driver validity.
    invalid = []
    driver_count = 0
    for obj in scene.objects:
        if obj.animation_data:
            for fcurve in obj.animation_data.drivers:
                driver_count += 1
                if not fcurve.driver.is_valid:
                    invalid.append(f"{obj.name}:{fcurve.data_path}")
    report["driver_count"] = driver_count
    report["invalid_object_drivers"] = invalid
    if invalid:
        fail(report, f"invalid drivers: {len(invalid)}")

    # Packed source textures and image integrity. Packed images can keep an empty
    # filepath depending on how the library was written, so match on datablock
    # name as well as filepath rather than requiring '/textures/' in filepath.
    report["image_datablocks"] = [
        {
            "name": im.name,
            "filepath": im.filepath,
            "packed": bool(im.packed_file),
            "size": list(im.size),
        }
        for im in bpy.data.images
        if im.type == "IMAGE" and im.name not in {"Render Result", "Viewer Node"}
    ]
    texture_images = [im for im in bpy.data.images if image_stem(im) in EXPECTED_TEXTURE_STEMS]
    report["packed_textures"] = {
        image_stem(im): bool(im.packed_file)
        for im in texture_images
    }
    missing_texture_stems = sorted(EXPECTED_TEXTURE_STEMS - set(report["packed_textures"]))
    if missing_texture_stems:
        fail(report, f"missing texture datablocks: {missing_texture_stems}")
    unpacked = [name for name, packed in report["packed_textures"].items() if not packed]
    if unpacked:
        fail(report, f"unpacked textures: {unpacked}")

    # Scholar stones and representative outward normals. Keep candidates in the
    # report so a stale .blend can be distinguished from a bad name assertion.
    report["scholar_stone_candidates"] = [
        o.name for o in scene.objects if "太湖" in o.name or "叠石" in o.name or "湖石" in o.name
    ]
    stones = [o for o in scene.objects if o.name.startswith("JN_太湖石_瘦透漏皱")]
    report["pierced_scholar_stones"] = len(stones)
    if len(stones) != 3:
        fail(report, f"expected 3 upgraded scholar stones, got {len(stones)}")

    report["outward_normals"] = {}
    for prefix in ["JN_云团", "JN_明月", "JN_花尖露珠"]:
        obj = next((o for o in scene.objects if o.name.startswith(prefix) and o.type == "MESH"), None)
        if obj is None:
            fail(report, f"missing mesh for normal test: {prefix}")
            continue
        ok = mesh_signed_volume(obj) > 0
        report["outward_normals"][obj.name] = ok
        if not ok:
            fail(report, f"inward/degenerate normals: {obj.name}")

    # Restore interactive defaults before exit.
    control["Weather"] = original_weather
    scene.frame_set(80)
    update_scene(scene)

    return finish(report, args.output)


def finish(report: dict, output: str) -> int:
    report["ok"] = not report.get("errors")
    path = Path(output)
    if not path.is_absolute():
        path = Path.cwd() / path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("CI_VALIDATION", json.dumps(report, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
