"""Render one of 36 final 4K shots from a built JNX expansion blend."""
from __future__ import annotations
import argparse, json, sys, time
from pathlib import Path
import bpy
from mathutils import Vector

GROUPS = [
    ("overview","JNX_Overview", [
        ("hero",None), ("left",(-18,-6,4,1.05)), ("right",(18,-6,3,1.05)),
        ("low",(0,-10,-6,.88)), ("tele",(10,28,1,1.35)), ("far",(-8,-26,10,.82)),
    ]),
    ("market-lane","JNX_Lane", [
        ("hero",None), ("left",(-6,-1,.7,1.12)), ("right",(6,-1,.7,1.12)),
        ("low",(0,-2,-1.2,.92)), ("close",(2,8,.2,1.28)), ("long",(-3,-10,2,.82)),
    ]),
    ("canal","JNX_Canal_Hero", [
        ("hero",None), ("left",(-10,-2,1,1.05)), ("right",(10,-2,1,1.05)),
        ("water-low",(0,-3,-1.6,.90)), ("tele",(6,14,1.3,1.35)), ("bank",(-7,8,2,.95)),
    ]),
    ("water-level","JNX_Water_Level", [
        ("hero",None), ("left",(-9,-1,.6,1.10)), ("right",(9,-1,.6,1.10)),
        ("surface",(0,-2,-1.1,.92)), ("compressed",(4,15,1,1.45)), ("far",(-5,-12,3,.86)),
    ]),
    ("moon-gate","JNX_MoonGate_Vista", [
        ("hero",None), ("left",(-5,-1,.4,1.10)), ("right",(5,-1,.4,1.10)),
        ("low",(0,-2,-.8,.95)), ("detail",(1.5,8,.2,1.45)), ("context",(-4,-10,3,.84)),
    ]),
    ("tingyu","JNX_TingYuXuan", [
        ("hero",None), ("left",(-6,-1,.8,1.10)), ("right",(6,-1,.8,1.10)),
        ("low",(0,-2,-1,.92)), ("architecture",(-2,7,1,1.42)), ("garden",(5,-9,3,.86)),
    ]),
]

SHOTS={}
n=1
for group,base,variants in GROUPS:
    for variant,spec in variants:
        SHOTS[n]=(f"{n:02d}-{group}-{variant}",base,spec)
        n+=1

HERO_SHOTS={1,4,7,10,13,16,19,22,25,28,31,34}

def parse():
    argv=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    p=argparse.ArgumentParser()
    p.add_argument("--shot",type=int,required=True,choices=range(1,37))
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--width",type=int,default=3840)
    p.add_argument("--height",type=int,default=2160)
    p.add_argument("--samples",type=int,default=256)
    return p.parse_args(argv)

def clone_variant(scene,base,name,variant):
    if variant is None:
        return base
    right_off,forward_off,up_off,lens_mul=variant
    q=base.matrix_world.to_quaternion()
    right=q @ Vector((1,0,0))
    forward=q @ Vector((0,0,-1))
    up=q @ Vector((0,1,0))
    loc=base.location + right*right_off + forward*forward_off + up*up_off
    focus=42.0 if "Overview" in base.name else 30.0
    target=base.location + forward*focus
    data=bpy.data.cameras.new("FINAL4K_"+name)
    cam=bpy.data.objects.new("FINAL4K_"+name,data)
    scene.collection.objects.link(cam)
    cam.location=loc
    cam.rotation_euler=(Vector(target)-cam.location).to_track_quat("-Z","Y").to_euler()
    data.lens=max(28.0,min(135.0,base.data.lens*lens_mul))
    data.sensor_width=36
    data.clip_start=.04
    data.clip_end=1800
    data.dof.use_dof=False
    return cam

def main():
    cfg=parse()
    scene=next((s for s in bpy.data.scenes if s.name.startswith("JNX_")),bpy.context.scene)
    bpy.context.window.scene=scene
    file_name,base_name,variant=SHOTS[cfg.shot]
    base=bpy.data.objects.get(base_name)
    if base is None or base.type!="CAMERA":
        raise RuntimeError(f"missing base camera {base_name}")
    cam=clone_variant(scene,base,file_name,variant)
    scene.camera=cam

    samples=max(cfg.samples,384 if cfg.shot in HERO_SHOTS else cfg.samples)
    scene.render.engine="CYCLES"
    scene.cycles.device="CPU"
    scene.cycles.samples=samples
    scene.cycles.use_denoising=True
    scene.cycles.use_adaptive_sampling=True
    scene.cycles.adaptive_threshold=.010
    scene.cycles.max_bounces=12
    scene.cycles.diffuse_bounces=4
    scene.cycles.glossy_bounces=5
    scene.cycles.transmission_bounces=6
    scene.cycles.volume_bounces=2
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
    print("FINAL_4K_GALLERY",json.dumps({
      "shot":cfg.shot,"file":str(out),"camera":cam.name,"base":base_name,
      "resolution":[cfg.width,cfg.height],"samples":samples,
      "seconds":round(time.time()-started,2)
    },ensure_ascii=False),flush=True)

if __name__=="__main__":
    main()
