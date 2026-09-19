"""Expansion entry point. No legacy imports, no automatic overwrites.

Python:  python expansion/scripts/build_world.py --format obj --out /tmp/jnx-v2
Blender: blender -b --factory-startup --python expansion/scripts/build_world.py -- \
             --format blend --preview --out /tmp/jnx-v2

Two geometry stages share one asset contract. ``--stage detail`` is the default:
curved tile roofs, organic street layout, procedural shaders and mist. ``--stage
blockout`` keeps the layer-1 skeleton for comparison. Only the OBJ path runs
without Blender; the blend path needs bpy and is the one that carries shaders.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from kernel import SceneBuilder, PALETTE

ROOT = SCRIPT_DIR.parent

STAGE_LIMITS = {
    "blockout": [
        "Regular parcel grid, shared hall topology, prismatic roofs",
        "Flat colour slots only; no shader graphs",
        "No detailed interiors or PBR maps",
        "No production LOD/collision",
        "D07 legacy courtyard is reserved, not imported",
        "No animation, rain particles or navigation bake",
    ],
    "detail": [
        "Interiors are furnished enough to read through the door, not full rooms",
        "Procedural shaders plus packed albedo; not a scanned PBR set",
        "No production LOD/collision; no UV unwrap for baking",
        "D07 is the Tingyuxuan courtyard, not a reserved empty plinth",
        "No animation, rain particles or navigation bake",
        "Dougong, joinery and tile profiles are restrained stand-ins, not documented dynastic systems",
    ],
}


def make_scene(config, stage="detail"):
    """Build the scene graph for one geometry stage.

    ``blockout`` is the layer-1 skeleton kept for comparison; ``detail`` is the
    layer-2 pass, which replaces the geometry behind the same asset ids, socket
    names and district manifest counts.
    """
    if stage == "blockout":
        from layout import make_layout
        import architecture
        import infrastructure
        import props_nature
        import terrain_water

        plan = make_layout(config)
        builder = SceneBuilder(config["seed"])
        terrain_water.build(builder, config)
        architecture.build(builder, config, plan)
        infrastructure.build(builder, config, plan)
        props_nature.build(builder, config)
        return builder, plan

    from layout_organic import make_layout
    import architecture_detail
    import infrastructure_detail
    import landmarks_detail
    import props_nature_detail
    import terrain_water_detail

    plan = make_layout(config)
    builder = SceneBuilder(config["seed"])
    terrain_water_detail.build(builder, config, plan)
    architecture_detail.build(builder, config, plan)
    landmarks_detail.build(builder, config, plan)
    infrastructure_detail.build(builder, config, plan)
    props_nature_detail.build(builder, config, plan)
    return builder, plan


def write_obj(builder, folder, stage="detail"):
    with (folder / "JNX_Expansion.obj").open("w", encoding="utf-8") as f:
        f.write(f"# Jiangnan expansion; metre units; Z up; stage={stage}\n"
                "mtllib JNX_Expansion.mtl\n")
        offset = 1
        for obj in builder.objects:
            f.write(f"o {obj['name']}\nusemtl JNX_MAT_{obj['material']}\n")
            mesh = builder.meshes[obj["mesh"]]
            for x,y,z in builder.world_vertices(obj):
                f.write(f"v {x:.6f} {y:.6f} {z:.6f}\n")
            for face in mesh.faces:
                f.write("f " + " ".join(str(i+offset) for i in face) + "\n")
            offset += len(mesh.vertices)
    with (folder / "JNX_Expansion.mtl").open("w", encoding="utf-8") as f:
        for name,(color,roughness) in PALETTE.items():
            f.write(f"newmtl JNX_MAT_{name}\nKd {' '.join(map(str,color))}\nNs {(1-roughness)*50:.3f}\n\n")


def main():
    argv = sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else sys.argv[1:]
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", type=Path, default=ROOT/"config/world.json")
    p.add_argument("--out", type=Path, required=True, help="New, nonexistent output directory")
    p.add_argument("--format", choices=("obj","blend"), default="obj")
    p.add_argument("--stage", choices=tuple(STAGE_LIMITS), default="detail",
                   help="detail: layer-2 geometry and shaders; blockout: layer-1 skeleton")
    p.add_argument("--preview", action="store_true", help="Render the shot list; only with --format blend")
    p.add_argument("--samples", type=int, default=96, help="Cycles samples when previewing")
    args=p.parse_args(argv)
    if args.preview and args.format != "blend":
        p.error("--preview requires --format blend")
    if args.out.exists():
        p.error("output directory already exists; use a new version directory")
    config=json.loads(args.config.read_text(encoding="utf-8"))
    builder,plan=make_scene(config, args.stage)
    args.out.mkdir(parents=True, exist_ok=False)
    if args.format == "obj":
        write_obj(builder,args.out,args.stage)
    elif args.stage == "blockout":
        from blender_io import write_blend
        write_blend(builder,args.out,args.preview)
    else:
        from blender_io_detail import write_blend
        write_blend(builder,args.out,preview=args.preview,config=config,
                    samples=args.samples)
    report=dict(schema_version=1, stage=args.stage, config=config,
                counts=builder.counts(), layout=plan, instances=list(builder.roots.values()),
                limitations=STAGE_LIMITS[args.stage])
    (args.out/"scene_manifest.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(builder.counts(),ensure_ascii=False))


if __name__ == "__main__":
    main()
