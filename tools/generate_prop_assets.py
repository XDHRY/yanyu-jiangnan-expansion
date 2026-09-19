"""Procedural Jiangnan inn prop/interior asset factory for Blender 4.5+."""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy

ASSETS = [
    ("JN_PROP_LANTERN_01", "标准灯笼"),
    ("JN_PROP_SIGN_01", "客栈招牌"),
    ("JN_PROP_TABLE_01", "方桌"),
    ("JN_PROP_BENCH_01", "长凳"),
    ("JN_PROP_WINE_JAR_01", "酒坛"),
    ("JN_INT_COUNTER_01", "客栈柜台"),
    ("JN_INT_BED_01", "木床榻"),
]


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="ci_artifacts/JN_PropFactory.blend")
    p.add_argument("--report", default="ci_artifacts/prop-report.json")
    return p.parse_args(argv)


def reset_scene():
    scene = bpy.context.scene
    for obj in list(scene.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for collection in list(bpy.data.collections):
        if collection.name != scene.collection.name:
            bpy.data.collections.remove(collection)
    scene.name = "JN_Prop_Factory"
    return scene


def material(name, color, roughness=.6, metallic=0.0, emission=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*color, 1.0)
    b.inputs["Roughness"].default_value = roughness
    b.inputs["Metallic"].default_value = metallic
    if emission:
        b.inputs["Emission Color"].default_value = (*emission[0], 1.0)
        b.inputs["Emission Strength"].default_value = emission[1]
    return m


def cube_mesh(name, size):
    x,y,z = (v/2 for v in size)
    verts = [(-x,-y,-z),(-x,-y,z),(-x,y,-z),(-x,y,z),
             (x,-y,-z),(x,-y,z),(x,y,-z),(x,y,z)]
    faces = [(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)]
    me = bpy.data.meshes.new(name+"_Mesh")
    me.from_pydata(verts, [], faces)
    me.update()
    return me


def box(name, size, loc, mat, col, parent=None, bevel=0.0):
    o = bpy.data.objects.new(name, cube_mesh(name, size))
    col.objects.link(o)
    o.location = loc
    o.data.materials.append(mat)
    if parent:
        o.parent = parent
    if bevel:
        m = o.modifiers.new("EdgeSoftening","BEVEL")
        m.width = bevel
        m.segments = 2
    return o


def cylinder(name, radius, height, loc, mat, col, parent=None, sides=20):
    verts, faces = [], []
    for z in (-height/2, height/2):
        for i in range(sides):
            a = math.tau*i/sides
            verts.append((radius*math.cos(a), radius*math.sin(a), z))
    for i in range(sides):
        ni=(i+1)%sides
        faces.append((i,ni,sides+ni,sides+i))
    faces.append(tuple(reversed(range(sides))))
    faces.append(tuple(range(sides,2*sides)))
    me=bpy.data.meshes.new(name+"_Mesh")
    me.from_pydata(verts,[],faces)
    me.update()
    for p in me.polygons:
        p.use_smooth=True
    o=bpy.data.objects.new(name,me)
    col.objects.link(o)
    o.location=loc
    o.data.materials.append(mat)
    if parent:
        o.parent=parent
    return o


def lathe(name, profile, loc, mat, col, parent=None, sides=32):
    verts=[];faces=[]
    rows=len(profile)
    for r,z in profile:
        for i in range(sides):
            a=math.tau*i/sides
            verts.append((r*math.cos(a),r*math.sin(a),z))
    for j in range(rows-1):
        for i in range(sides):
            ni=(i+1)%sides
            a=j*sides+i;b=j*sides+ni;c=(j+1)*sides+ni;d=(j+1)*sides+i
            faces.append((a,b,c,d))
    me=bpy.data.meshes.new(name+"_Mesh")
    me.from_pydata(verts,[],faces)
    me.update()
    for p in me.polygons:
        p.use_smooth=True
    o=bpy.data.objects.new(name,me)
    col.objects.link(o)
    o.location=loc
    o.data.materials.append(mat)
    if parent:
        o.parent=parent
    return o


def root(asset_id,name_cn,offset,col):
    r=bpy.data.objects.new(asset_id,None)
    col.objects.link(r)
    r.location=offset
    r["asset_id"]=asset_id
    r["name_cn"]=name_cn
    r["region"]="jiangnan_bamboo_inn"
    r["production_level"]="blockout"
    return r


def lantern(r, wood, paper, iron, col):
    cylinder(r.name+"_PAPER", .28, .72, (0,0,1.0), paper,col,r,24)
    for z in (.62,1.38):
        cylinder(r.name+f"_RIM_{z:.2f}", .33,.08,(0,0,z),wood,col,r,24)
    for a in range(4):
        angle=a*math.pi/2
        x=.29*math.cos(angle);y=.29*math.sin(angle)
        box(r.name+f"_FRAME_{a}",(.035,.035,.76),(x,y,1.0),wood,col,r)
    cylinder(r.name+"_TOP",.12,.06,(0,0,1.49),iron,col,r,20)
    cylinder(r.name+"_BOTTOM",.10,.06,(0,0,.51),iron,col,r,20)
    r["height_m"]=1.02
    r["hanging_socket_z"]=1.55


def sign(r, wood, iron, col):
    box(r.name+"_BOARD",(1.75,.12,.65),(0,0,.85),wood,col,r,bevel=.035)
    for x in (-.65,.65):
        cylinder(r.name+f"_RING_{x:+.2f}",.055,.05,(x,0,1.28),iron,col,r,16).rotation_euler.x=math.pi/2
        box(r.name+f"_HANGER_{x:+.2f}",(.05,.05,.42),(x,0,1.49),iron,col,r)
    r["sign_face_m"]=[1.75,.65]


def table(r, wood, col):
    box(r.name+"_TOP",(1.18,1.18,.10),(0,0,.82),wood,col,r,bevel=.025)
    for x in (-.46,.46):
        for y in (-.46,.46):
            box(r.name+f"_LEG_{x:+.2f}_{y:+.2f}",(.10,.10,.76),(x,y,.39),wood,col,r,bevel=.012)
    for y in (-.46,.46):
        box(r.name+f"_APRON_X_{y:+.2f}",(.92,.08,.16),(0,y,.69),wood,col,r)
    for x in (-.46,.46):
        box(r.name+f"_APRON_Y_{x:+.2f}",(.08,.92,.16),(x,0,.69),wood,col,r)
    r["dimensions_m"]=[1.18,1.18,.87]


def bench(r,wood,col):
    box(r.name+"_SEAT",(1.65,.42,.09),(0,0,.53),wood,col,r,bevel=.02)
    for x in (-.62,.62):
        box(r.name+f"_LEG_{x:+.2f}",(.10,.32,.50),(x,0,.25),wood,col,r,bevel=.012)
    box(r.name+"_STRETCHER",(1.28,.08,.10),(0,0,.24),wood,col,r)
    r["dimensions_m"]=[1.65,.42,.58]


def wine_jar(r, clay, rope, col):
    profile=[(.22,0),(.36,.10),(.43,.34),(.40,.62),(.29,.82),(.20,.88),(.18,.98),(.24,1.02)]
    lathe(r.name+"_BODY",profile,(0,0,0),clay,col,r,36)
    cylinder(r.name+"_ROPE",.255,.035,(0,0,.86),rope,col,r,28)
    r["height_m"]=1.02


def counter(r,wood,col):
    box(r.name+"_BODY",(2.25,.72,.92),(0,0,.46),wood,col,r,bevel=.025)
    box(r.name+"_TOP",(2.42,.82,.10),(0,0,.97),wood,col,r,bevel=.025)
    for x in (-.7,0,.7):
        box(r.name+f"_PANEL_{x:+.2f}",(.52,.03,.58),(x,-.375,.46),wood,col,r,bevel=.01)
    r["dimensions_m"]=[2.42,.82,1.02]


def bed(r,wood,cloth,col):
    box(r.name+"_PLATFORM",(2.05,1.18,.18),(0,0,.34),wood,col,r,bevel=.018)
    for x in (-.94,.94):
        for y in (-.50,.50):
            box(r.name+f"_LEG_{x:+.2f}_{y:+.2f}",(.10,.10,.34),(x,y,.17),wood,col,r)
    box(r.name+"_MATTRESS",(1.92,1.07,.16),(0,0,.51),cloth,col,r,bevel=.035)
    box(r.name+"_HEAD",(2.05,.12,.95),(0,.53,.91),wood,col,r,bevel=.018)
    box(r.name+"_PILLOW",(.65,.78,.12),(0,.24,.67),cloth,col,r,bevel=.05)
    r["dimensions_m"]=[2.05,1.18,1.39]


def main():
    a=parse_args()
    out=Path(a.output);report_path=Path(a.report)
    out.parent.mkdir(parents=True,exist_ok=True)
    report_path.parent.mkdir(parents=True,exist_ok=True)
    scene=reset_scene()
    col=bpy.data.collections.new("JN_Inn_Props")
    scene.collection.children.link(col)

    wood=material("JN_MAT_AgedWood_Blockout",(.13,.075,.04),.66)
    paper=material("JN_MAT_LanternPaper_Blockout",(.72,.24,.08),.62,0,((1.0,.35,.08),1.2))
    iron=material("JN_MAT_Iron_Blockout",(.07,.065,.06),.40,.60)
    clay=material("JN_MAT_WineJarClay_Blockout",(.24,.19,.14),.74)
    rope=material("JN_MAT_Rope_Blockout",(.22,.16,.09),.88)
    cloth=material("JN_MAT_CoarseCloth_Blockout",(.30,.27,.22),.92)

    builders=[
        (lantern,(wood,paper,iron)),
        (sign,(wood,iron)),
        (table,(wood,)),
        (bench,(wood,)),
        (wine_jar,(clay,rope)),
        (counter,(wood,)),
        (bed,(wood,cloth)),
    ]
    records=[]
    for idx,((asset_id,name_cn),(build,mats)) in enumerate(zip(ASSETS,builders)):
        x=(idx%4-1.5)*4.0
        y=(idx//4-.5)*4.0
        r=root(asset_id,name_cn,(x,y,0),col)
        build(r,*mats,col)
        records.append({"asset_id":asset_id,"name_cn":name_cn,"child_objects":len(r.children)})
    report={
        "scene":scene.name,
        "asset_count":len(records),
        "expected_asset_count":len(ASSETS),
        "assets":records,
        "objects":len(scene.objects),
        "mesh_objects":sum(o.type=="MESH" for o in scene.objects),
        "materials":len(bpy.data.materials),
        "status":"blockout",
    }
    assert report["asset_count"]==7
    assert all(x["child_objects"]>0 for x in records)
    report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    bpy.ops.wm.save_as_mainfile(filepath=str(out.resolve()))
    print("PROP_FACTORY_OK",json.dumps(report,ensure_ascii=False))


if __name__=="__main__":
    main()
