"""Render a neutral catalog preview for a generated asset-factory .blend."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--output", required=True)
    p.add_argument("--resolution", type=int, default=720)
    p.add_argument("--samples", type=int, default=12)
    return p.parse_args(argv)


def bounds():
    points=[]
    for obj in bpy.context.scene.objects:
        if obj.type not in {"MESH","CURVE","SURFACE","FONT","META"}:
            continue
        try:
            points.extend(obj.matrix_world @ Vector(c) for c in obj.bound_box)
        except Exception:
            pass
    if not points:
        raise RuntimeError("no renderable asset bounds found")
    lo=Vector((min(p.x for p in points),min(p.y for p in points),min(p.z for p in points)))
    hi=Vector((max(p.x for p in points),max(p.y for p in points),max(p.z for p in points)))
    return lo,hi


def look_at(obj,target):
    obj.rotation_euler=(target-obj.location).to_track_quat("-Z","Y").to_euler()


def create_plane(name,size,z,material):
    x=size/2
    verts=[(-x,-x,z),(x,-x,z),(x,x,z),(-x,x,z)]
    me=bpy.data.meshes.new(name+"_Mesh")
    me.from_pydata(verts,[],[(0,1,2,3)])
    me.update()
    me.materials.append(material)
    o=bpy.data.objects.new(name,me)
    bpy.context.scene.collection.objects.link(o)
    return o


def make_material(name,color,rough=.75):
    m=bpy.data.materials.new(name)
    m.use_nodes=True
    b=next(n for n in m.node_tree.nodes if n.type=="BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value=(*color,1)
    b.inputs["Roughness"].default_value=rough
    return m


def add_area(name,loc,target,energy,size,color):
    d=bpy.data.lights.new(name,"AREA")
    d.energy=energy;d.shape="DISK";d.size=size;d.color=color
    o=bpy.data.objects.new(name,d)
    bpy.context.scene.collection.objects.link(o)
    o.location=loc;look_at(o,target)
    return o


def main():
    a=parse_args()
    scene=bpy.context.scene
    lo,hi=bounds()
    center=(lo+hi)*.5
    ext=hi-lo
    diag=max(ext.length,1.0)
    floor_z=lo.z-.04

    floor_mat=make_material("CATALOG_FLOOR",(.08,.085,.085),.82)
    create_plane("CATALOG_FLOOR",max(ext.x,ext.y,2.0)*2.2,floor_z,floor_mat)

    cam_data=bpy.data.cameras.new("CATALOG_CAMERA")
    cam=bpy.data.objects.new("CATALOG_CAMERA",cam_data)
    scene.collection.objects.link(cam)
    scene.camera=cam
    cam.location=center+Vector((diag*.72,-diag*1.12,diag*.70))
    cam.data.lens=58
    look_at(cam,center+Vector((0,0,ext.z*.08)))

    add_area("CATALOG_KEY",center+Vector((-diag*.65,-diag*.45,diag*1.25)),center,1100,diag*.75,(.80,.88,1.0))
    add_area("CATALOG_FILL",center+Vector((diag*.85,-diag*.10,diag*.55)),center,650,diag*.9,(1.0,.72,.50))
    add_area("CATALOG_RIM",center+Vector((0,diag*.80,diag*.90)),center,900,diag*.65,(.65,.78,1.0))

    if scene.world is None:
        scene.world=bpy.data.worlds.new("CATALOG_WORLD")
    scene.world.use_nodes=True
    bg=next(n for n in scene.world.node_tree.nodes if n.type=="BACKGROUND")
    bg.inputs["Color"].default_value=(.025,.032,.04,1)
    bg.inputs["Strength"].default_value=.32

    scene.render.engine="BLENDER_EEVEE_NEXT"
    scene.render.resolution_x=a.resolution
    scene.render.resolution_y=round(a.resolution*.72)
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG"
    if hasattr(scene,"eevee") and hasattr(scene.eevee,"taa_render_samples"):
        scene.eevee.taa_render_samples=a.samples

    out=Path(a.output).resolve()
    out.parent.mkdir(parents=True,exist_ok=True)
    scene.render.filepath=str(out)
    bpy.ops.render.render(write_still=True)
    print("ASSET_PREVIEW_OK",out)


if __name__=="__main__":
    main()
