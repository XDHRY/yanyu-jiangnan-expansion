"""Seventeen bridges join district roads; docks descend to the water datum."""
from __future__ import annotations
import math


def arch_bridge(b, link):
    r=b.root(link["id"],"bridge","WORLD",link["location"],link["rotation"],
             task="tasks/assets/A041.md", connects=[link["a"],link["b"]])
    length,width=link["span"],link["width"]
    n=20
    vertices=[]
    for i in range(n+1):
        t=i/n
        z=.12+2.6*math.sin(math.pi*t)
        vertices.extend([(-length/2+length*t,-width/2,z-.45),
                         (-length/2+length*t,width/2,z-.45),
                         (-length/2+length*t,-width/2,z),
                         (-length/2+length*t,width/2,z)])
    faces=[(0,2,3,1),(4*n,4*n+1,4*n+3,4*n+2)]
    for i in range(n):
        a=4*i; q=a+4
        faces += [(a,a+1,q+1,q),(a+2,q+2,q+3,a+3),
                  (a,q,q+2,a+2),(a+1,a+3,q+3,q+1)]
    b.mesh(r,"arch_deck",vertices,faces,"stone")
    for side in (-1,1):
        for i in range(11):
            t=i/10; z=.12+2.6*math.sin(math.pi*t)
            b.box(r,f"rail_post_{side}_{i}",(.22,.22,.95),
                  (-length/2+length*t,side*(width/2-.18),z+.475),"stone")
    for side in (-1,1):
        b.socket(r,"road_"+("a" if side<0 else "b"),(side*length/2,0,.12),(side,0,0))
    b.socket(r,"channel",(0,0,-link["location"][2]),(0,1,0))


def build(b, config, plan):
    for link in plan["links"]:
        arch_bridge(b,link)
    for d in config["districts"]:
        x,y=d["center"]
        for i in range(d["dock_count"]):
            dx=-48+i*32
            r=b.root(f"JNX_{d['id']}_DOCK_{i:02d}","dock",d["id"],
                     (x+dx,y-79,0), task="tasks/assets/A043.md")
            for step in range(10):
                height=.2*(step+1)
                b.box(r,f"step_{step}",(4,.5,height),(0,-4.5+step*.5,height/2),"stone")
            for side in (-1,1):
                b.cylinder(r,f"bollard_{side}",.16,.8,(side*1.7,0,2),"stone")
            b.socket(r,"land",(0,0,2),(0,1,0))
            b.socket(r,"moor",(0,-5,.4))
