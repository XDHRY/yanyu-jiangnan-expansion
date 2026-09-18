"""Render the cameras stored in a built .blend.

Run under Blender's own Python:

    blender --background --python render_shots.py -- --blend OUT/JNX_Expansion.blend

Kept separate from ``build_world.py`` so a look change can be re-rendered
without paying the 800k-face rebuild again.
"""

import argparse
import sys
from pathlib import Path

import bpy


def _args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--blend", type=Path, required=True)
    p.add_argument("--out", type=Path, default=None,
                   help="defaults to the .blend's own folder")
    p.add_argument("--samples", type=int, default=None,
                   help="override the sample count baked into the scene")
    p.add_argument("--resolution", type=int, nargs=2, default=None)
    p.add_argument("--only", nargs="*", default=None,
                   help="camera names; default renders every camera")
    return p.parse_args(argv)


def main():
    args = _args()
    bpy.ops.wm.open_mainfile(filepath=str(args.blend))

    out = args.out or args.blend.parent
    out.mkdir(parents=True, exist_ok=True)

    scene = next((s for s in bpy.data.scenes if s.name.startswith("JNX_")),
                 bpy.data.scenes[0])
    bpy.context.window.scene = scene

    if args.samples:
        scene.cycles.samples = args.samples
    if args.resolution:
        scene.render.resolution_x, scene.render.resolution_y = args.resolution

    cameras = [o for o in scene.objects if o.type == "CAMERA"]
    if args.only:
        wanted = set(args.only)
        cameras = [c for c in cameras if c.name in wanted]
    cameras.sort(key=lambda c: c.name)

    if not cameras:
        raise SystemExit("no cameras matched")

    for camera in cameras:
        scene.camera = camera
        scene.render.filepath = str(out / camera.name) + ".png"
        bpy.ops.render.render(write_still=True)
        print("rendered", camera.name, flush=True)


if __name__ == "__main__":
    main()
