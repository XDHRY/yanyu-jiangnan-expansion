"""Procedural Jiangnan ground/path asset factory for Blender 4.5+."""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path

import bpy

ASSETS = [
    ("JN_PATH_STONE_01", "石板路直段"),
    ("JN_PATH_DIRT_01", "泥地过渡段"),
]


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, default=36)
    p.add_argument("--output", default="ci_artifacts/JN_GroundFactory.blend")
    p.add_argument("--report", default="ci_artifacts/ground-report.json")
    return p.parse_args(argv)


def reset_scene():
    scene=bpy.context.scene
    for o in list(scene.objects):
        bpy.data.objects.remove(o,do_unlink=True)
    for c in list(bpy.data.collections):
        if c.name != scene.collection.name:
            bpy.data.collections.remove(c)
    scene.name="JN_Ground_Factory"
    return scene


def material(name,color,roughness):
    m=bpy.data.materials.new(name)
    m.use_nodes=True
    b=next(n for n in m.node_tree.nodes if n.type=="BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value=(*color,1)
    b.inputs["Roughness"].default_value=roughness
    return m


def cube_mesh(name,size):
    x,y,z=(v/2 for v in size)
    verts=[(-x,-y,-z),(-x,-y,z),(-x,y,-z),(-x,y,z),(x,-y,-z),(x,-y,z),(x,y,-z),(x,y,z)]
    faces=[(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)]
    me=bpy.data.meshes.new(name+"_Mesh");me.from_pydata(verts,[],faces);me.update();return me


def box(name,size,loc,mat,col,parent=None,rotation=(0,0,0),bevel=0):
    o=bpy.data.objects.new(name,cube_mesh(name,size));col.objects.link(o)
    o.location=loc;o.rotation_euler=rotation;o.data.materials.append(mat)
    if parent:o.parent=parent
    if bevel:
        mod=o.modifiers.new("EdgeSoftening","BEVEL");mod.width=bevel;mod.segments=2
    return o


def root(asset_id,name_cn,offset,col):
    r=bpy.data.objects.new(asset_id,None);col.objects.link(r);r.location=offset
    r["asset_id"]=asset_id;r["name_cn"]=name_cn;r["region"]="jiangnan_bamboo_inn"
    r["production_level"]="blockout";r["parametric"]=True
    return r


def build_stone_path(r,rng,stone,moss,col):
    rows=6
    for j in range(rows):
        y=-1.45+j*.58
        count=3 if j%2==0 else 2
        total_width=1.45
        widths=[]
        remaining=total_width
        for i in range(count):
            if i==count-1:
                w=remaining
            else:
                nominal=total_width/count
                w=max(.34,min(.66,nominal+rng.uniform(-.10,.10)))
                remaining-=w
            widths.append(w)
        x=-total_width/2
        for i,w in enumerate(widths):
            cx=x+w/2+rng.uniform(-.018,.018)
            depth=.49+rng.uniform(-.05,.04)
            height=.10+rng.uniform(-.025,.022)
            slab=box(
                f"{r.name}_SLAB_{j:02d}_{i:02d}",
                (w-.035,depth,height),
                (cx,y+rng.uniform(-.02,.02),height/2+rng.uniform(-.008,.008)),
                stone,col,r,
                rotation=(rng.uniform(-.012,.012),rng.uniform(-.012,.012),rng.uniform(-.018,.018)),
                bevel=.025,
            )
            slab["wetness"]=round(rng.uniform(.55,.85),3)
            if rng.random()<.38:
                box(
                    f"{r.name}_MOSS_{j:02d}_{i:02d}",
                    (max(.08,w*.45),.025,.012),
                    (cx,y-depth*.48,height+.008),
                    moss,col,r,
                    bevel=.006,
                )
            x+=w
    r["module_length_m"]=3.4;r["module_width_m"]=1.5;r["slab_pattern"]="staggered"


def terrain_mesh(name,width,length,nx,ny,height_fn,mat,col,parent):
    verts=[];faces=[]
    for j in range(ny):
        y=-length/2+length*j/(ny-1)
        for i in range(nx):
            x=-width/2+width*i/(nx-1)
            verts.append((x,y,height_fn(x,y)))
            if i and j:
                a=j*nx+i
                faces.append((a,a-1,a-1-nx,a-nx))
    me=bpy.data.meshes.new(name+"_Mesh");me.from_pydata(verts,[],faces);me.update()
    for p in me.polygons:p.use_smooth=True
    o=bpy.data.objects.new(name,me);col.objects.link(o);me.materials.append(mat);o.parent=parent
    return o


def build_dirt_transition(r,rng,dirt,water,col):
    phase=rng.random()*math.tau
    def h(x,y):
        edge=(abs(x)/1.4)**2
        return .025*math.sin(x*3.7+phase)*math.cos(y*2.9-phase)+.012*edge
    terrain_mesh(r.name+"_GROUND",2.8,3.4,15,18,h,dirt,col,r)
    for i,(x,y,sx,sy) in enumerate([(-.55,-.45,.72,.38),(.62,.78,.54,.31)]):
        box(r.name+f"_PUDDLE_{i}",(sx,sy,.008),(x,y,.018),water,col,r,bevel=.06)
    r["module_length_m"]=3.4;r["module_width_m"]=2.8;r["weather_response"]="rain_darkens_and_puddles"


def main():
    a=parse_args();rng=random.Random(a.seed)
    out=Path(a.output);report_path=Path(a.report)
    out.parent.mkdir(parents=True,exist_ok=True);report_path.parent.mkdir(parents=True,exist_ok=True)
    scene=reset_scene()
    col=bpy.data.collections.new("JN_Ground_Modules");scene.collection.children.link(col)
    stone=material("JN_MAT_WetStone_Blockout",(.23,.25,.24),.68)
    moss=material("JN_MAT_Moss_Blockout",(.08,.13,.075),.92)
    dirt=material("JN_MAT_WetDirt_Blockout",(.115,.09,.065),.88)
    water=material("JN_MAT_Puddle_Blockout",(.055,.075,.075),.16)

    records=[]
    specs=[(ASSETS[0],build_stone_path,(stone,moss)),(ASSETS[1],build_dirt_transition,(dirt,water))]
    for idx,((asset_id,name_cn),build,mats) in enumerate(specs):
        r=root(asset_id,name_cn,((idx-.5)*4.5,0,0),col);build(r,rng,*mats,col)
        records.append({"asset_id":asset_id,"name_cn":name_cn,"child_objects":len(r.children)})
    report={
        "scene":scene.name,"asset_count":len(records),"expected_asset_count":2,
        "assets":records,"objects":len(scene.objects),
        "mesh_objects":sum(o.type=="MESH" for o in scene.objects),
        "materials":len(bpy.data.materials),"status":"blockout",
    }
    assert report["asset_count"]==2 and all(x["child_objects"]>0 for x in records)
    report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    bpy.ops.wm.save_as_mainfile(filepath=str(out.resolve()))
    print("GROUND_FACTORY_OK",json.dumps(report,ensure_ascii=False))


if __name__=="__main__":
    main()
