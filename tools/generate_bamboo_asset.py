"""Procedural Jiangnan bamboo asset factory for Blender 4.5+.

Designed to run both interactively and headless:

  blender -b --factory-startup --python tools/generate_bamboo_asset.py -- \
      --count 8 --seed 36 \
      --output ci_artifacts/JN_BambooFactory.blend \
      --report ci_artifacts/bamboo-report.json

The first version intentionally uses only editable Blender geometry/materials.
Image textures can be attached later through asset_db/materials.json.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path

import bpy
from mathutils import Vector

PREFIX = "JN_BAMBOO_"


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--count", type=int, default=8)
    p.add_argument("--seed", type=int, default=36)
    p.add_argument("--output", default="ci_artifacts/JN_BambooFactory.blend")
    p.add_argument("--report", default="ci_artifacts/bamboo-report.json")
    return p.parse_args(argv)


def reset_scene():
    scene = bpy.context.scene
    for obj in list(scene.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for collection in list(bpy.data.collections):
        if collection.name != scene.collection.name:
            bpy.data.collections.remove(collection)
    scene.name = "JN_Bamboo_Factory"
    return scene


def material(name, color, roughness):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    return mat


def make_culm_mesh(name: str, height: float, radius: float, bend_x: float, bend_y: float,
                   node_spacing: float, material_ref, collection, sides: int = 12):
    ring_count = max(6, round(height / node_spacing) + 1)
    verts = []
    faces = []
    ring_meta = []

    for j in range(ring_count):
        t = j / (ring_count - 1)
        z = height * t
        # Young bamboo bends smoothly instead of kinking at every node.
        cx = bend_x * (t ** 1.75) + 0.035 * math.sin(t * math.pi * 2.3)
        cy = bend_y * (t ** 1.6) + 0.025 * math.sin(t * math.pi * 1.7 + 0.7)
        taper = 1.0 - 0.27 * t
        # Slight swelling at segment boundaries reads as bamboo nodes in silhouette.
        local_radius = radius * taper * (1.055 if 0 < j < ring_count - 1 else 1.0)
        ring_meta.append((cx, cy, z, local_radius))
        for i in range(sides):
            a = 2 * math.pi * i / sides
            verts.append((cx + local_radius * math.cos(a), cy + local_radius * math.sin(a), z))

    for j in range(ring_count - 1):
        for i in range(sides):
            a = j * sides + i
            b = j * sides + (i + 1) % sides
            c = (j + 1) * sides + (i + 1) % sides
            d = (j + 1) * sides + i
            faces.append((a, b, c, d))

    # Close ends.
    bottom_center = len(verts)
    verts.append((ring_meta[0][0], ring_meta[0][1], 0.0))
    top_center = len(verts)
    verts.append((ring_meta[-1][0], ring_meta[-1][1], height))
    for i in range(sides):
        ni = (i + 1) % sides
        faces.append((bottom_center, ni, i))
        a = (ring_count - 1) * sides + i
        b = (ring_count - 1) * sides + ni
        faces.append((top_center, a, b))

    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    for poly in mesh.polygons:
        poly.use_smooth = True
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    mesh.materials.append(material_ref)
    obj["asset_family"] = "bamboo_system"
    obj["height_m"] = round(height, 3)
    obj["node_spacing_m"] = round(node_spacing, 3)
    obj["bend_xy"] = [round(bend_x, 3), round(bend_y, 3)]
    return obj, ring_meta


def make_branch(name, start: Vector, end: Vector, material_ref, collection, radius=0.013):
    curve = bpy.data.curves.new(name + "_Curve", "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 2
    curve.bevel_depth = radius
    curve.bevel_resolution = 2
    spline = curve.splines.new("POLY")
    spline.points.add(1)
    spline.points[0].co = (*start, 1.0)
    spline.points[1].co = (*end, 1.0)
    obj = bpy.data.objects.new(name, curve)
    collection.objects.link(obj)
    curve.materials.append(material_ref)
    return obj


def make_leaf(name: str, center: Vector, direction: Vector, size: float, material_ref, collection):
    direction = direction.normalized()
    side = direction.cross(Vector((0, 0, 1)))
    if side.length < 1e-5:
        side = Vector((1, 0, 0))
    side.normalize()
    up = Vector((0, 0, 1))
    half_w = size * 0.11
    half_l = size * 0.5
    tip = center + direction * half_l
    base = center - direction * half_l
    mid_left = center + side * half_w + up * size * 0.02
    mid_right = center - side * half_w - up * size * 0.02
    verts = [tuple(base), tuple(mid_left), tuple(tip), tuple(mid_right)]
    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata(verts, [], [(0, 1, 2, 3)])
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    mesh.materials.append(material_ref)
    return obj


def build_bamboo(index: int, rng: random.Random, culm_mat, leaf_mat, collection):
    height = rng.uniform(4.6, 7.3)
    radius = rng.uniform(0.038, 0.068)
    node_spacing = rng.uniform(0.36, 0.52)
    bend_mag = rng.uniform(0.15, 0.72)
    bend_angle = rng.uniform(0, math.tau)
    bend_x = bend_mag * math.cos(bend_angle)
    bend_y = bend_mag * math.sin(bend_angle)

    name = f"{PREFIX}{index:03d}"
    culm, rings = make_culm_mesh(
        name, height, radius, bend_x, bend_y, node_spacing, culm_mat, collection
    )

    branch_count = rng.randint(4, 8)
    leaf_count = 0
    for branch_idx in range(branch_count):
        t = rng.uniform(0.52, 0.94)
        ring_idx = min(len(rings) - 2, max(1, round(t * (len(rings) - 1))))
        cx, cy, z, _ = rings[ring_idx]
        start = Vector((cx, cy, z))
        angle = rng.uniform(0, math.tau)
        length = rng.uniform(0.45, 1.15)
        end = start + Vector((math.cos(angle) * length, math.sin(angle) * length, rng.uniform(0.08, 0.42)))
        make_branch(f"{name}_BR_{branch_idx:02d}", start, end, culm_mat, collection, radius * 0.22)

        leaves_here = rng.randint(4, 8)
        for leaf_idx in range(leaves_here):
            u = (leaf_idx + 1) / (leaves_here + 1)
            center = start.lerp(end, u)
            spread = rng.uniform(-0.65, 0.65)
            direction = (end - start).normalized() + Vector((
                -math.sin(angle) * spread,
                math.cos(angle) * spread,
                rng.uniform(-0.25, 0.25),
            ))
            make_leaf(
                f"{name}_LF_{branch_idx:02d}_{leaf_idx:02d}",
                center,
                direction,
                rng.uniform(0.22, 0.42),
                leaf_mat,
                collection,
            )
            leaf_count += 1

    culm["branch_count"] = branch_count
    culm["leaf_count"] = leaf_count
    return {
        "name": name,
        "height_m": round(height, 3),
        "radius_m": round(radius, 4),
        "node_spacing_m": round(node_spacing, 3),
        "bend_m": round(bend_mag, 3),
        "branches": branch_count,
        "leaves": leaf_count,
    }


def set_preview(scene, collection):
    # Arrange generated culms into a small readable cluster.
    culms = [o for o in collection.objects if o.name.startswith(PREFIX) and "_BR_" not in o.name and "_LF_" not in o.name]
    cols = max(1, math.ceil(math.sqrt(len(culms))))
    spacing = 1.2
    for i, obj in enumerate(culms):
        obj.location.x = (i % cols - (cols - 1) / 2) * spacing
        obj.location.y = (i // cols - (math.ceil(len(culms) / cols) - 1) / 2) * spacing

    world = bpy.data.worlds.new("JN_Bamboo_World")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.035, 0.055, 0.05, 1)
    bg.inputs["Strength"].default_value = 0.35
    scene.world = world


def stats(scene, generated):
    meshes = [o for o in scene.objects if o.type == "MESH"]
    curves = [o for o in scene.objects if o.type == "CURVE"]
    return {
        "blender_version": bpy.app.version_string,
        "asset_family": "bamboo_system",
        "culms": generated,
        "objects": len(scene.objects),
        "mesh_objects": len(meshes),
        "curve_objects": len(curves),
        "vertices": sum(len(o.data.vertices) for o in meshes),
        "polygons": sum(len(o.data.polygons) for o in meshes),
        "materials": sorted({m.name for o in scene.objects if getattr(o, "data", None) and hasattr(o.data, "materials") for m in o.data.materials if m}),
    }


def main() -> int:
    cfg = parse_args()
    rng = random.Random(cfg.seed)
    scene = reset_scene()
    collection = bpy.data.collections.new("JN_ASSET_Bamboo_System")
    scene.collection.children.link(collection)

    culm_mat = material("JN_MAT_Bamboo_Culm", (0.16, 0.28, 0.12), 0.55)
    leaf_mat = material("JN_MAT_Bamboo_Leaf", (0.08, 0.20, 0.07), 0.68)

    generated = [build_bamboo(i + 1, rng, culm_mat, leaf_mat, collection) for i in range(cfg.count)]
    set_preview(scene, collection)
    report = stats(scene, generated)

    report_path = Path(cfg.report)
    if not report_path.is_absolute():
        report_path = Path.cwd() / report_path
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    output_path = Path(cfg.output)
    if not output_path.is_absolute():
        output_path = Path.cwd() / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output_path))

    print("BAMBOO_FACTORY", json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
