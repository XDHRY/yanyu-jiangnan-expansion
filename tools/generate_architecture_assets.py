"""Procedural Jiangnan modular architecture asset factory for Blender 4.5+.

Headless example:
  blender -b --factory-startup --python-exit-code 1 \
    --python tools/generate_architecture_assets.py -- \
    --output ci_artifacts/JN_ArchitectureFactory.blend \
    --report ci_artifacts/architecture-report.json
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy

ASSETS = [
    ("JN_BLD_BASE_01", "石基直段"),
    ("JN_BLD_STEP_01", "石阶短段"),
    ("JN_COL_01", "木柱标准段"),
    ("JN_BEAM_01", "横梁标准段"),
    ("JN_WALL_01", "木板墙直段"),
    ("JN_DOOR_01", "单扇木门"),
    ("JN_WIN_01", "木格窗标准型"),
    ("JN_ROOF_TILE_01", "灰瓦屋顶平段"),
]


def args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="ci_artifacts/JN_ArchitectureFactory.blend")
    p.add_argument("--report", default="ci_artifacts/architecture-report.json")
    return p.parse_args(argv)


def reset_scene():
    scene = bpy.context.scene
    for obj in list(scene.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for collection in list(bpy.data.collections):
        if collection.name != scene.collection.name:
            bpy.data.collections.remove(collection)
    scene.name = "JN_Architecture_Factory"
    return scene


def mat(name, color, roughness=0.65, metallic=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*color, 1.0)
    b.inputs["Roughness"].default_value = roughness
    b.inputs["Metallic"].default_value = metallic
    return m


def cube_mesh(name, size):
    x, y, z = (v / 2 for v in size)
    verts = [
        (-x,-y,-z), (-x,-y,z), (-x,y,-z), (-x,y,z),
        (x,-y,-z), (x,-y,z), (x,y,-z), (x,y,z),
    ]
    faces = [
        (0,4,6,2), (1,3,7,5), (0,1,5,4),
        (2,6,7,3), (0,2,3,1), (4,5,7,6),
    ]
    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    return mesh


def box(name, size, location, material, collection, parent=None, rotation=(0,0,0), bevel=0.0):
    obj = bpy.data.objects.new(name, cube_mesh(name, size))
    collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = rotation
    obj.data.materials.append(material)
    if parent:
        obj.parent = parent
    if bevel:
        mod = obj.modifiers.new("EdgeSoftening", "BEVEL")
        mod.width = bevel
        mod.segments = 2
    return obj


def cylinder(name, radius, height, location, material, collection, parent=None, sides=16):
    verts, faces = [], []
    for z in (-height/2, height/2):
        for i in range(sides):
            a = math.tau * i / sides
            verts.append((radius*math.cos(a), radius*math.sin(a), z))
    for i in range(sides):
        ni = (i + 1) % sides
        faces.append((i, ni, sides + ni, sides + i))
    faces.append(tuple(reversed(range(sides))))
    faces.append(tuple(range(sides, 2*sides)))
    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    for p in mesh.polygons:
        p.use_smooth = True
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    obj.location = location
    obj.data.materials.append(material)
    if parent:
        obj.parent = parent
    return obj


def root(asset_id, name_cn, offset, collection):
    r = bpy.data.objects.new(asset_id, None)
    collection.objects.link(r)
    r.location = offset
    r["asset_id"] = asset_id
    r["name_cn"] = name_cn
    r["region"] = "jiangnan_bamboo_inn"
    r["production_level"] = "blockout"
    r["parametric"] = True
    return r


def foundation(r, stone, col):
    box(r.name+"_STONE", (3.2, 1.25, .34), (0,0,.17), stone, col, r, bevel=.035)
    r["dimensions_m"] = [3.2,1.25,.34]


def steps(r, stone, col):
    widths = [2.6, 2.25, 1.9]
    for i, w in enumerate(widths):
        box(f"{r.name}_STEP_{i}", (w, .52, .18), (0, -.52 + i*.38, .09 + i*.18), stone, col, r, bevel=.025)
    r["step_count"] = 3


def column_asset(r, wood, stone, col):
    box(r.name+"_BASE", (.42,.42,.18), (0,0,.09), stone, col, r, bevel=.025)
    cylinder(r.name+"_POST", .16, 3.05, (0,0,1.70), wood, col, r, sides=20)
    box(r.name+"_CAP", (.42,.42,.16), (0,0,3.30), wood, col, r, bevel=.015)
    r["height_m"] = 3.38


def beam_asset(r, wood, col):
    box(r.name+"_MAIN", (3.4,.24,.30), (0,0,0), wood, col, r, bevel=.025)
    for x in (-1.35, 1.35):
        box(r.name+f"_BRACKET_{x:+.2f}", (.48,.34,.22), (x,0,-.20), wood, col, r, rotation=(0, math.radians(18 if x < 0 else -18), 0), bevel=.02)
    r["span_m"] = 3.4


def wall_asset(r, wood, col):
    for i in range(8):
        x = -1.225 + i*.35
        box(r.name+f"_PLANK_{i:02d}", (.32,.12,2.45), (x,0,1.225), wood, col, r, bevel=.012)
    box(r.name+"_TOP", (2.8,.16,.18), (0,0,2.48), wood, col, r)
    box(r.name+"_BOTTOM", (2.8,.16,.18), (0,0,.09), wood, col, r)
    r["bay_width_m"] = 2.8


def door_asset(r, wood, iron, col):
    box(r.name+"_JAMB_L", (.18,.22,2.55), (-.64,0,1.275), wood, col, r, bevel=.012)
    box(r.name+"_JAMB_R", (.18,.22,2.55), (.64,0,1.275), wood, col, r, bevel=.012)
    box(r.name+"_LINTEL", (1.46,.22,.20), (0,0,2.48), wood, col, r, bevel=.012)
    for i in range(4):
        x = -.45 + i*.30
        box(r.name+f"_LEAF_{i:02d}", (.28,.10,2.16), (x,-.08,1.12), wood, col, r, bevel=.01)
    for z in (.55, 1.50):
        box(r.name+f"_BRACE_{z:.2f}", (1.15,.13,.12), (0,-.15,z), wood, col, r, bevel=.008)
    cylinder(r.name+"_RING", .055, .04, (.36,-.20,1.18), iron, col, r, sides=16).rotation_euler.x = math.pi/2
    r["opening_m"] = [1.28, 2.38]


def window_asset(r, wood, col):
    for x in (-.85,.85):
        box(r.name+f"_SIDE_{x:+.2f}", (.13,.16,1.55), (x,0,.775), wood, col, r, bevel=.008)
    for z in (.06,1.49):
        box(r.name+f"_RAIL_{z:.2f}", (1.83,.16,.13), (0,0,z), wood, col, r, bevel=.008)
    for x in (-.52,-.17,.17,.52):
        box(r.name+f"_V_{x:+.2f}", (.055,.11,1.34), (x,-.02,.775), wood, col, r)
    for z in (.34,.68,1.02,1.36):
        box(r.name+f"_H_{z:.2f}", (1.58,.11,.055), (0,-.02,z), wood, col, r)
    r["opening_m"] = [1.7,1.55]


def roof_asset(r, tile, edge, col):
    pitch = math.radians(24)
    panel_depth = 1.7
    panel_width = 3.6
    rise = math.sin(pitch) * panel_depth/2
    for side in (-1,1):
        y = side * math.cos(pitch) * panel_depth/4
        z = 1.05 + rise/2
        box(
            r.name+f"_SLOPE_{side:+d}",
            (panel_width, panel_depth/2, .10),
            (0,y,z),
            tile,col,r,
            rotation=(side*pitch,0,0),
            bevel=.01,
        )
    cylinder(r.name+"_RIDGE", .09, panel_width+0.18, (0,0,1.05+rise), edge, col, r, sides=16).rotation_euler.y = math.pi/2
    for side in (-1,1):
        for j in range(6):
            frac = (j + .5) / 6
            y = side * math.cos(pitch) * (panel_depth/2) * frac
            z = 1.05 + rise * (1-frac)
            ridge = cylinder(
                r.name+f"_COURSE_{side:+d}_{j:02d}", .027, panel_width,
                (0,y,z+.055), edge,col,r,sides=10
            )
            ridge.rotation_euler.y = math.pi/2
    r["module_m"] = [panel_width, panel_depth]
    r["roof_pitch_deg"] = 24


def main():
    a = args()
    out = Path(a.output)
    report_path = Path(a.report)
    out.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    scene = reset_scene()
    col = bpy.data.collections.new("JN_Architecture_Modules")
    scene.collection.children.link(col)

    stone = mat("JN_MAT_WetStone_Blockout", (.23,.25,.24), .72)
    wood = mat("JN_MAT_AgedWood_Blockout", (.13,.075,.04), .66)
    tile = mat("JN_MAT_GrayTile_Blockout", (.075,.09,.095), .48)
    edge = mat("JN_MAT_RoofEdge_Blockout", (.055,.065,.07), .52)
    iron = mat("JN_MAT_Iron_Blockout", (.08,.07,.06), .38, .55)

    builders = [
        foundation, steps, column_asset, beam_asset, wall_asset,
        door_asset, window_asset, roof_asset,
    ]
    material_args = [
        (stone,), (stone,), (wood,stone), (wood,), (wood,),
        (wood,iron), (wood,), (tile,edge),
    ]

    records = []
    spacing_x, spacing_y = 5.0, 5.0
    for idx, ((asset_id, name_cn), build, mats) in enumerate(zip(ASSETS, builders, material_args)):
        x = (idx % 4 - 1.5) * spacing_x
        y = (idx // 4 - .5) * spacing_y
        r = root(asset_id, name_cn, (x,y,0), col)
        build(r, *mats, col)
        records.append({
            "asset_id": asset_id,
            "name_cn": name_cn,
            "root": r.name,
            "child_objects": len(r.children),
            "location": [round(v,3) for v in r.location],
        })

    report = {
        "scene": scene.name,
        "asset_count": len(records),
        "expected_asset_count": len(ASSETS),
        "assets": records,
        "objects": len(scene.objects),
        "mesh_objects": sum(o.type == "MESH" for o in scene.objects),
        "materials": len(bpy.data.materials),
        "status": "blockout",
    }
    assert report["asset_count"] == 8
    assert all(item["child_objects"] > 0 for item in records)

    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    bpy.ops.wm.save_as_mainfile(filepath=str(out.resolve()))
    print("ARCHITECTURE_FACTORY_OK", json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
