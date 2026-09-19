"""Render one of twelve final-gallery shots from a built JNX expansion blend."""
from __future__ import annotations
import argparse, json, sys, time
from pathlib import Path
import bpy
from mathutils import Vector

BASE = {
  1: ("01-overview-hero", "JNX_Overview", None),
  2: ("02-market-lane", "JNX_Lane", None),
  3: ("03-canal-hero", "JNX_Canal_Hero", None),
  4: ("04-water-level", "JNX_Water_Level", None),
  5: ("05-moon-gate-vista", "JNX_MoonGate_Vista", None),
  6: ("06-tingyu-pavilion", "JNX_TingYuXuan", None),
  7: ("07-market-close", "JNX_Lane", (-3.0, 8.0, .35, 58)),
  8: ("08-canal-bank-tele", "JNX_Canal_Hero", (7.0, 11.0, 1.2, 58)),
  9: ("09-water-compressed", "JNX_Water_Level", (-7.0, 10.0, 1.0, 72)),
 10: ("10-moon-gate-detail", "JNX_MoonGate_Vista", (2.0, 7.0, .35, 86)),
 11: ("11-tingyu-architecture", "JNX_TingYuXuan", (-3.5, 5.5, 1.0, 74)),
 12: ("12-town-compressed", "JNX_Overview", (14.0, 46.0, -5.0, 105)),
}

def parse():
    argv=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    p=argparse.ArgumentParser()
    p.add_argument("--shot",type=int,required=True,choices=range(1,13))
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--width",type=int,default=2560)
    p.add_argument("--height",type=int,default=1440)
    p.add_argument("--samples",type=int,default=320)
    return p.parse_args(argv)

def clone_variant(scene,base,name,variant):
    if variant is None:
        return base
    right_off,forward_off,up_off,lens=variant
    q=base.matrix_world.to_quaternion()
    right=q @ Vector((1,0,0))
    forward=q @ Vector((0,0,-1))
    up=q @ Vector((0,1,0))
    loc=base.location + right*right_off + forward*forward_off + up*up_off
    target=base.location + forward*32.0
    data=bpy.data.cameras.new("FINAL_"+name)
    cam=bpy.data.objects.new("FINAL_"+name,data)
    scene.collection.objects.link(cam)
    cam.location=loc
    cam.rotation_euler=(Vector(target)-cam.location).to_track_quat("-Z","Y").to_euler()
    data.lens=lens
    data.sensor_width=36
    data.clip_start=.05
    data.clip_end=1600
    data.dof.use_dof=False
    return cam

def main():
    cfg=parse()
    scene=next((s for s in bpy.data.scenes if s.name.startswith("JNX_")),bpy.context.scene)
    bpy.context.window.scene=scene
    file_name,base_name,variant=BASE[cfg.shot]
    base=bpy.data.objects.get(base_name)
    if base is None or base.type!="CAMERA":
        raise RuntimeError(f"missing base camera {base_name}")
    cam=clone_variant(scene,base,file_name,variant)
    scene.camera=cam
    scene.render.engine="CYCLES"
    scene.cycles.device="CPU"
    scene.cycles.samples=cfg.samples
    scene.cycles.use_denoising=True
    scene.cycles.use_adaptive_sampling=True
    scene.cycles.adaptive_threshold=.025
    scene.cycles.max_bounces=12
    scene.cycles.diffuse_bounces=4
    scene.cycles.glossy_bounces=4
    scene.cycles.transmission_bounces=6
    scene.render.resolution_x=cfg.width
    scene.render.resolution_y=cfg.height
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG"
    scene.render.image_settings.color_mode="RGB"
    scene.render.image_settings.color_depth="16"
    scene.render.film_transparent=False
    cfg.out.mkdir(parents=True,exist_ok=True)
    out=(cfg.out/(file_name+".png")).resolve()
    scene.render.filepath=str(out)
    started=time.time()
    bpy.ops.render.render(write_still=True)
    print("FINAL_GALLERY",json.dumps({
      "shot":cfg.shot,"file":str(out),"camera":cam.name,
      "base":base_name,"resolution":[cfg.width,cfg.height],
      "samples":cfg.samples,"seconds":round(time.time()-started,2)
    },ensure_ascii=False),flush=True)

if __name__=="__main__":
    main()
