"""Low-cost boat, stall, lantern, tree and bamboo masses with stable streams."""
from __future__ import annotations
import math
from kernel import rng


def boat(b, r):
    vertices=[]
    for x,w,z in [(-3,.08,.5),(-2,1,.05),(0,1.2,0),(2,1,.05),(3,.08,.5)]:
        vertices.extend([(x,-w,z),(x,w,z),(x,0,z-.65)])
    faces=[(0,2,1),(12,13,14)]
    for i in range(4):
        a=3*i; q=a+3
        faces += [(a,q,q+1,a+1),(a,a+2,q+2,q),(a+1,q+1,q+2,a+2)]
    b.mesh(r,"hull",vertices,faces,"timber")
    b.roof(r,"awning",3.6,2.0,.65,(0,0,1.1))
    for x in (-1.5,1.5):
        for y in (-.8,.8):
            b.cylinder(r,f"pole_{x}_{y}",.04,1.1,(x,y,0),"bamboo",8)
    b.socket(r,"moor_bow",(-3,0,.5),(-1,0,0))


def build(b, config):
    for d in config["districts"]:
        x,y=d["center"]; z=config["ground_z"]
        for i in range(d["stall_count"]):
            # All stalls fit in unbuilt southwest apron; no house parcel overlap.
            px=-68+(i%8)*8
            py=-73+(i//8)*8
            r=b.root(f"JNX_{d['id']}_STALL_{i:02d}","stall",d["id"],(x+px,y+py,z),
                     task="tasks/assets/A053.md")
            b.box(r,"table",(3,1.5,.15),(0,0,1),"timber")
            for xx in (-1.4,1.4):
                for yy in (-.65,.65):
                    b.cylinder(r,f"post_{xx}_{yy}",.065,2.4,(xx,yy,0),"timber",8)
            b.roof(r,"canopy",3.7,2.4,.5,(0,0,2.4))
            b.socket(r,"wares",(0,0,1.075),(0,0,1))
        for i in range(d["dock_count"]):
            r=b.root(f"JNX_{d['id']}_BOAT_{i:02d}","boat",d["id"],
                     (x-48+i*32,y-86,.28),task="tasks/assets/A047.md")
            boat(b,r)
        for i in range(12):
            side=-1 if i%2 else 1
            r=b.root(f"JNX_{d['id']}_LANTERN_{i:02d}","lantern",d["id"],
                     (x+side*4.0,y-65+(i//2)*24,z),task="tasks/assets/A057.md")
            b.cylinder(r,"post",.075,3.0,(0,0,0),"timber",8)
            b.cylinder(r,"paper",.28,.55,(0,0,2.35),"paper",10)
            b.socket(r,"light",(0,0,2.62),(0,0,-1))
        stream=rng(config["seed"],d["id"]+":plants")
        for i in range(d["tree_count"]):
            # A separate perimeter belt leaves plots, paths and bridge ends clear.
            side=-1 if i%2 else 1
            px=side*76
            py=-66+(i//2)*132/max(1,math.ceil(d["tree_count"]/2)-1)
            if abs(py)<7:
                py=9 if py>=0 else -9
            is_bamboo=d["id"] in ("D03","D11")
            h=stream.uniform(5,9)
            r=b.root(f"JNX_{d['id']}_TREE_{i:03d}","bamboo" if is_bamboo else "tree",
                     d["id"],(x+px,y+py,z),
                     task="tasks/assets/A074.md" if is_bamboo else "tasks/assets/A073.md")
            if is_bamboo:
                for n in range(3):
                    b.cylinder(r,f"culm_{n}",.10,h,(n*.45-.45,0,0),"bamboo",8)
                    b.cylinder(r,f"crown_{n}",1.0,2.8,(n*.45-.45,0,h-1.8),"leaf",8,.05)
            else:
                b.cylinder(r,"trunk",.24,h*.6,(0,0,0),"timber",10,.12)
                b.cylinder(r,"crown",2.2,h*.65,(0,0,h*.4),"leaf",10,.18)
            b.socket(r,"ground",(0,0,0),(0,0,1))
