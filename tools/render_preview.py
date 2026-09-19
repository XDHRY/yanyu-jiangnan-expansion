"""Low-cost headless preview renderer for CI and remote iteration.

Examples:
  blender -b Jiangnan.blend --python tools/render_preview.py -- \
      --camera 三分之四 --weather 0 --engine BLENDER_EEVEE_NEXT \
      --resolution 640 --samples 16 --output ci_artifacts/preview.png

  blender -b Jiangnan.blend --python tools/render_preview.py -- \
      --camera 正面 --weather 1 --engine CYCLES \
      --resolution 800 --samples 24 --output ci_artifacts/snow.png
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import bpy

SCENE_NAME = "烟雨江南 · 雪月江南"
CONTROL_NAME = "JN_总控_天气0雨1雪_风力"


def args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--camera", default="三分之四")
    parser.add_argument("--weather", type=int, choices=[0, 1], default=0)
    parser.add_argument("--frame", type=int, default=80)
    parser.add_argument("--engine", choices=["BLENDER_EEVEE_NEXT", "CYCLES"], default="BLENDER_EEVEE_NEXT")
    parser.add_argument("--resolution", type=int, default=640, help="output width; height keeps 1.6 aspect")
    parser.add_argument("--samples", type=int, default=16)
    parser.add_argument("--output", default="ci_artifacts/preview.png")
    return parser.parse_args(argv)


def main() -> int:
    cfg = args()
    scene = bpy.data.scenes.get(SCENE_NAME)
    if scene is None:
        raise RuntimeError(f"missing scene: {SCENE_NAME}")
    control = bpy.data.objects.get(CONTROL_NAME)
    if control is None:
        raise RuntimeError(f"missing control: {CONTROL_NAME}")
    camera = bpy.data.objects.get("JN_" + cfg.camera)
    if camera is None or camera.type != "CAMERA":
        raise RuntimeError(f"missing camera: JN_{cfg.camera}")

    control["Weather"] = cfg.weather
    control.update_tag()
    scene.frame_set(cfg.frame)
    bpy.context.view_layer.update()

    scene.camera = camera
    scene.render.engine = cfg.engine
    scene.render.resolution_x = cfg.resolution
    scene.render.resolution_y = round(cfg.resolution / 1.6)
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"

    if cfg.engine == "CYCLES":
        scene.cycles.device = "CPU"
        scene.cycles.samples = cfg.samples
        scene.cycles.use_denoising = True
        scene.cycles.use_adaptive_sampling = True
        scene.cycles.adaptive_threshold = 0.08
    else:
        # Eevee is intentionally used only for composition/material smoke tests.
        # Formal delivery remains Cycles.
        scene.render.engine = "BLENDER_EEVEE_NEXT"
        if hasattr(scene, "eevee") and hasattr(scene.eevee, "taa_render_samples"):
            scene.eevee.taa_render_samples = cfg.samples

    out = Path(cfg.output)
    if not out.is_absolute():
        out = Path.cwd() / out
    out.parent.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(out)

    started = time.time()
    bpy.ops.render.render(write_still=True)
    elapsed = round(time.time() - started, 2)

    result = {
        "output": str(out),
        "camera": cfg.camera,
        "weather": cfg.weather,
        "frame": cfg.frame,
        "engine": scene.render.engine,
        "resolution": [scene.render.resolution_x, scene.render.resolution_y],
        "seconds": elapsed,
        "blender_version": bpy.app.version_string,
    }
    print("PREVIEW_RENDER", json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
