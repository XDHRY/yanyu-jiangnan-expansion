"""Main editable building masses: houses, shops, halls, courtyards and towers.

Generated wall pieces leave a real opening in the south facade. Foundations,
posts, wall pieces, floor plates and roofs remain separate named meshes.
Decorative brackets, interiors, UV and individual tiles are intentionally tasks.
"""
from __future__ import annotations

from kernel import rng


def hall(b, root, prefix, width, depth, floors=1, location=(0,0,0), open_sides=False):
    ox,oy,oz = location
    h = 3.2 * floors
    def box(label, size, p, material):
        b.box(root, prefix+label, size, (p[0]+ox,p[1]+oy,p[2]+oz), material)
    box("foundation", (width+.6,depth+.6,.48), (0,0,.24), "stone")
    box("floor", (width,depth,.16), (0,0,.56), "timber")
    if not open_sides:
        for side in (-1,1):
            box(f"wall_side_{side}", (.22,depth,h), (side*(width/2-.11),0,.64+h/2), "plaster")
        box("wall_back", (width,.22,h), (0,depth/2-.11,.64+h/2), "plaster")
        door=2.4
        for side in (-1,1):
            box(f"wall_front_{side}", ((width-door)/2,.22,h),
                (side*(width+door)/4,-depth/2+.11,.64+h/2), "plaster")
        box("door_lintel", (door,.30,h-2.4), (0,-depth/2,.64+2.4+(h-2.4)/2), "timber")
    for side in (-1,1):
        for n in range(4):
            x=-width/2+n*width/3
            b.cylinder(root, prefix+f"post_{side}_{n}", .16,h,
                       (x+ox,side*(depth/2-.1)+oy,.64+oz), "timber")
        box(f"beam_{side}", (width+.2,.26,.34), (0,side*(depth/2-.1),h+.54), "timber")
    if floors == 2:
        box("upper_floor", (width-.3,depth-.3,.16), (0,0,3.84), "timber")
    b.roof(root, prefix+"roof", width+1.6,depth+1.6,depth*.24,
           (ox,oy,oz+h+.78))
    box("ridge", (width+1.7,.20,.20), (0,0,h+.78+depth*.24), "tile")
    # Rise from parcel datum to the finished floor; no hidden ground transform.
    for i in range(4):
        box(f"entry_step_{i}", (2.5,.4,.16*(i+1)),
            (0,-depth/2-1.4+i*.4,.08*(i+1)), "stone")


def build(b, config, plan):
    for spec in plan["buildings"]:
        r=b.root(spec["id"], spec["family"], spec["district"], spec["location"],
                 spec["rotation"], task=f"tasks/assets/{config['family_tasks'][spec['family']]}.md",
                 dimensions_m=[spec["width"],spec["depth"],spec["floors"]*3.2],
                 parcel=spec["parcel"])
        hall(b,r,"",spec["width"],spec["depth"],spec["floors"],
             open_sides=spec["family"]=="pavilion")
        b.socket(r,"entry",(0,-spec["depth"]/2-1.6,0))
        b.socket(r,"sign",(0,-spec["depth"]/2-.2,3.0))
        b.socket(r,"roof_ridge",(0,0,spec["floors"]*3.2+.78+spec["depth"]*.24),(0,0,1))
    for d in config["districts"]:
        x,y=d["center"]
        r=b.root(f"JNX_{d['id']}_LANDMARK", d["landmark"], d["id"],
                 (x,y+46,config["ground_z"]), task=f"tasks/districts/{d['id']}.md")
        if d["landmark"] == "legacy_reserve":
            # Reserve the old courtyard without invoking destructive legacy scripts.
            b.box(r,"reserve_plinth",(60,48,.15),(0,0,.075),"stone")
            b.roots[r]["status"]="reserved_not_imported"
        elif d["landmark"] == "tower":
            for level in range(3):
                hall(b,r,f"tier_{level}_",20-level*4,16-level*3,1,
                     (0,0,level*4.5),open_sides=level==2)
        elif d["landmark"] in ("courtyard","academy","temple","inn"):
            hall(b,r,"main_",28,14,2 if d["landmark"]=="inn" else 1,(0,10,0))
            hall(b,r,"wing_w_",10,30,1,(-22,0,0))
            hall(b,r,"wing_e_",10,30,1,(22,0,0))
            hall(b,r,"gate_",12,7,1,(0,-19,0),open_sides=True)
            b.box(r,"court",(31,27,.10),(0,-4,.05),"stone")
        else:
            hall(b,r,"main_",28,18,1,open_sides=d["landmark"]=="pavilion")
        b.socket(r,"forecourt",(0,-25,0))
