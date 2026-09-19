"""Procedural Jiangnan waterside asset pack for Blender 4.5+."""
from __future__ import annotations
import argparse, json, math, sys
from pathlib import Path
import bpy

ASSETS = [
    ("JN_WATER_DOCK_01", "青石水埠头", "waterside_access"),
    ("JN_WATER_MOONGATE_01", "月洞门墙段", "wall_gate"),
    ("JN_WATER_BRIDGE_01", "小型石拱桥", "bridge"),
    ("JN_WATER_CORRIDOR_01", "临水穿廊", "corridor"),
    ("JN_WATER_BOAT_01", "乌篷船", "boat"),
    ("JN_WATER_WELL_01", "青石井栏", "well"),
    ("JN_WATER_FLUME_01", "竹制引水槽", "water_feature"),
    ("JN_WATER_LAMPPOST_01", "临水灯架", "lighting_prop"),
]

def parse_args():
    argv = sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="generated_assets/JN_WatersideFactory.blend")
    p.add_argument("--report", default="generated_assets/waterside-report.json")
    return p.parse_args(argv)

def reset():
    s=bpy.context.scene
    for o in list(s.objects): bpy.data.objects.remove(o, do_unlink=True)
    for c in list(bpy.data.collections):
        if c.name != s.collection.name: bpy.data.collections.remove(c)
    s.name="JN_Waterside_Factory"; return s

def mat(name,c,r=.65,m=0.0,e=None):
    x=bpy.data.materials.new(name); x.use_nodes=True
    p=next(n for n in x.node_tree.nodes if n.type=="BSDF_PRINCIPLED")
    p.inputs["Base Color"].default_value=(*c,1); p.inputs["Roughness"].default_value=r; p.inputs["Metallic"].default_value=m
    if e:
        p.inputs["Emission Color"].default_value=(*e[0],1); p.inputs["Emission Strength"].default_value=e[1]
    return x

def cube_mesh(name,size):
    x,y,z=(v/2 for v in size)
    v=[(-x,-y,-z),(-x,-y,z),(-x,y,-z),(-x,y,z),(x,-y,-z),(x,-y,z),(x,y,-z),(x,y,z)]
    f=[(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)]
    me=bpy.data.meshes.new(name+"_Mesh"); me.from_pydata(v,[],f); me.update(); return me

def box(name,size,loc,ma,col,parent=None,rot=(0,0,0),bev=0):
    o=bpy.data.objects.new(name,cube_mesh(name,size)); col.objects.link(o); o.location=loc; o.rotation_euler=rot; o.data.materials.append(ma)
    if parent: o.parent=parent
    if bev:
        q=o.modifiers.new("EdgeSoftening","BEVEL"); q.width=bev; q.segments=2
    return o

def cyl(name,rad,h,loc,ma,col,parent=None,sides=20):
    v=[]; f=[]
    for z in (-h/2,h/2):
        for i in range(sides):
            a=math.tau*i/sides; v.append((rad*math.cos(a),rad*math.sin(a),z))
    for i in range(sides):
        n=(i+1)%sides; f.append((i,n,sides+n,sides+i))
    f += [tuple(reversed(range(sides))), tuple(range(sides,2*sides))]
    me=bpy.data.meshes.new(name+"_Mesh"); me.from_pydata(v,[],f); me.update()
    o=bpy.data.objects.new(name,me); col.objects.link(o); o.location=loc; o.data.materials.append(ma)
    if parent: o.parent=parent
    return o

def root(a,n,cat,loc,col):
    r=bpy.data.objects.new(a,None); col.objects.link(r); r.location=loc
    r["asset_id"]=a; r["name_cn"]=n; r["category"]=cat; r["region"]="jiangnan_waterside"
    r["production_level"]="midpoly_blockout"; r["parametric"]=True
    r["historical_intent"]="late_imperial_jiangnan_vernacular"
    return r

def dock(r,stone,moss,col):
    for i in range(5): box(f"{r.name}_STEP_{i}",(2.25-i*.1,.58,.18),(0,-.92+i*.42,.09+i*.16),stone,col,r,bev=.028)
    for x in (-.92,.92): cyl(f"{r.name}_MOOR_{x}",.09,.75,(x,.72,.70),stone,col,r,16)
    box(r.name+"_MOSS",(1.65,.05,.025),(0,-.92,.18),moss,col,r,bev=.01)

def moongate(r,plaster,brick,stone,col):
    w,h,t,rr=4.2,3.2,.42,1.16
    cw,ch=w/14,h/11
    for ix in range(14):
        x=-w/2+cw*(ix+.5)
        for iz in range(11):
            z=ch*(iz+.5)
            if x*x+(z-1.46)**2 < rr**2: continue
            box(f"{r.name}_W_{ix}_{iz}",(cw*1.02,t,ch*1.02),(x,0,z),brick if iz in (0,10) else plaster,col,r)
    for i in range(18):
        a=math.tau*i/18
        box(f"{r.name}_RING_{i}",(.34,t+.08,.15),(rr*math.cos(a),0,1.46+rr*math.sin(a)),stone,col,r,rot=(0,-a,0),bev=.012)

def bridge(r,stone,moss,col):
    span,width=4.6,1.75
    for i in range(15):
        t=i/14; x=-span/2+span*t; z=.22+.78*math.sin(math.pi*t)
        box(f"{r.name}_DECK_{i}",(span/15*1.08,width,.22),(x,0,z),stone,col,r,rot=(0,math.radians(-18+36*t),0),bev=.02)
    for s in (-1,1):
        y=s*(width/2-.08)
        for i in range(8):
            t=i/7; x=-span/2+span*t; z=.55+.78*math.sin(math.pi*t)
            cyl(f"{r.name}_POST_{s}_{i}",.055,.58,(x,y,z),stone,col,r,12)
    box(r.name+"_MOSS",(1,.08,.025),(-1.6,-.88,.34),moss,col,r)

def corridor(r,wood,tile,stone,col):
    L,W=4.8,1.9
    box(r.name+"_FLOOR",(L,W,.18),(0,0,.22),stone,col,r,bev=.02)
    for x in (-2.05,-.68,.68,2.05):
        for y in (-.72,.72): cyl(f"{r.name}_POST_{x}_{y}",.10,2.65,(x,y,1.62),wood,col,r,16)
    for y in (-.72,.72): box(f"{r.name}_BEAM_{y}",(L-.25,.16,.20),(0,y,2.85),wood,col,r,bev=.012)
    for s in (-1,1): box(f"{r.name}_ROOF_{s}",(L+.36,W/2+.22,.10),(0,s*.40,3.15),tile,col,r,rot=(s*math.radians(25),0,0),bev=.01)

def boat(r,wood,awning,bamboo,col):
    L=4.8; widths=[.08,.30,.48,.58,.60,.58,.48,.30,.08]; zs=[.18,.04,-.04,-.10,-.12,-.10,-.04,.04,.18]
    v=[]; f=[]; n=len(widths)
    for i,(hw,z) in enumerate(zip(widths,zs)):
        x=-L/2+L*i/(n-1); v.extend([(x,-hw,z),(x,hw,z),(x,0,z-.30)])
    for i in range(n-1):
        a=3*i; b=a+3
        f += [(a,b,b+1,a+1),(a,a+2,b+2,b),(a+1,b+1,b+2,a+2)]
    me=bpy.data.meshes.new(r.name+"_HULL_Mesh"); me.from_pydata(v,[],f); me.update()
    o=bpy.data.objects.new(r.name+"_HULL",me); col.objects.link(o); o.parent=r; me.materials.append(wood)
    for i in range(5): box(f"{r.name}_AWNING_{i}",(.43,1.05,.08),(-.95+i*.48,0,.78),awning,col,r,rot=(0,math.radians(11*(i-2)),0),bev=.02)
    p=cyl(r.name+"_POLE",.025,3.0,(-1.75,.38,.95),bamboo,col,r,10); p.rotation_euler.y=math.radians(68)

def well(r,stone,wood,col):
    for i in range(16):
        a=math.tau*i/16
        box(f"{r.name}_STONE_{i}",(.42,.25,.26),(.72*math.cos(a),.72*math.sin(a),.32),stone,col,r,rot=(0,0,a),bev=.025)
    for x in (-.95,.95): cyl(f"{r.name}_POST_{x}",.08,2.1,(x,0,1.2),wood,col,r,14)
    box(r.name+"_BEAM",(2.15,.14,.16),(0,0,2.18),wood,col,r,bev=.018)

def flume(r,bamboo,stone,col):
    for i in range(4):
        x=-1.75+i*1.15; z=1.50-i*.18
        o=box(f"{r.name}_CHANNEL_{i}",(1.25,.34,.10),(x,0,z),bamboo,col,r,bev=.04); o.rotation_euler.y=math.radians(-9)
        for y in (-.42,.42): cyl(f"{r.name}_LEG_{i}_{y}",.04,max(.45,z-.10),(x,y,(z-.10)/2),bamboo,col,r,10)
    box(r.name+"_CATCHSTONE",(.85,.85,.18),(2.05,0,.09),stone,col,r,bev=.04)

def lamp(r,wood,iron,paper,col):
    cyl(r.name+"_POST",.085,3.05,(0,0,1.53),wood,col,r,16)
    box(r.name+"_ARM",(1.05,.10,.10),(.43,0,2.92),wood,col,r,bev=.012)
    cyl(r.name+"_HOOK",.035,.38,(.88,0,2.68),iron,col,r,12)
    cyl(r.name+"_LANTERN",.22,.58,(.88,0,2.28),paper,col,r,20)

def main():
    a=parse_args(); out=Path(a.output); rep=Path(a.report); out.parent.mkdir(parents=True,exist_ok=True); rep.parent.mkdir(parents=True,exist_ok=True)
    s=reset(); col=bpy.data.collections.new("JN_Waterside_Modules"); s.collection.children.link(col)
    stone=mat("JN_MAT_WetStone_Waterside",(.20,.235,.23),.72); moss=mat("JN_MAT_Moss_Waterside",(.07,.12,.065),.94)
    plaster=mat("JN_MAT_WhitePlaster_Waterside",(.55,.56,.52),.84); brick=mat("JN_MAT_GrayBrick_Waterside",(.16,.18,.18),.78)
    wood=mat("JN_MAT_AgedWood_Waterside",(.115,.065,.035),.70); tile=mat("JN_MAT_GrayTile_Waterside",(.065,.078,.082),.50)
    awning=mat("JN_MAT_BlackAwning_Waterside",(.035,.030,.025),.90); bamboo=mat("JN_MAT_Bamboo_Waterside",(.30,.34,.14),.72)
    iron=mat("JN_MAT_Iron_Waterside",(.06,.055,.05),.42,.58); paper=mat("JN_MAT_LanternPaper_Waterside",(.72,.23,.07),.62,0,((1,.30,.07),.8))
    specs=[(dock,(stone,moss)),(moongate,(plaster,brick,stone)),(bridge,(stone,moss)),(corridor,(wood,tile,stone)),(boat,(wood,awning,bamboo)),(well,(stone,wood)),(flume,(bamboo,stone)),(lamp,(wood,iron,paper))]
    rec=[]
    for i,((aid,n,cat),(fn,mats)) in enumerate(zip(ASSETS,specs)):
        r=root(aid,n,cat,((i%4-1.5)*6.2,(i//4-.5)*6,0),col); fn(r,*mats,col)
        rec.append({"asset_id":aid,"name_cn":n,"category":cat,"child_objects":len(r.children)})
    report={"scene":s.name,"asset_count":len(rec),"expected_asset_count":8,"assets":rec,"objects":len(s.objects),"mesh_objects":sum(o.type=="MESH" for o in s.objects),"materials":len(bpy.data.materials),"status":"midpoly_blockout","rebuild_contract":"deterministic_geometry_no_llm_required"}
    assert len(rec)==8 and all(x["child_objects"]>0 for x in rec)
    rep.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    bpy.ops.wm.save_as_mainfile(filepath=str(out.resolve()))
    print("WATERSIDE_FACTORY_OK",json.dumps(report,ensure_ascii=False))
if __name__=="__main__": main()
