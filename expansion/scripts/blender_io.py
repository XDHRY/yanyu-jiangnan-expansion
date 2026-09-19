"""Blender 4.5 adapter: create a new Scene and write only its dependency graph.

Never reset/open/save the user's legacy main file. No bpy import occurs until
this adapter is selected. This is initial framework code awaiting a Blender run.
"""
from __future__ import annotations
import math
from kernel import PALETTE


def write_blend(builder, folder, preview=False):
    import bpy
    from mathutils import Vector

    scene=bpy.data.scenes.new("JNX_Expansion_v1")
    scene.unit_settings.system="METRIC"
    scene.unit_settings.scale_length=1.0
    scene["stage"]="blockout"
    scene["legacy_imported"]=False
    scene["seed"]=builder.seed
    collections={}
    for district in sorted({r["district"] for r in builder.roots.values()}):
        col=bpy.data.collections.new("JNX_"+district)
        scene.collection.children.link(col)
        collections[district]=col
    materials={}
    for key,(color,roughness) in PALETTE.items():
        mat=bpy.data.materials.new("JNX_MAT_"+key)
        mat.diffuse_color=(*color,1)
        mat.use_nodes=True
        node=mat.node_tree.nodes.get("Principled BSDF")
        node.inputs["Base Color"].default_value=(*color,1)
        node.inputs["Roughness"].default_value=roughness
        materials[key]=mat
    roots={}
    for key,spec in builder.roots.items():
        col=collections[spec["district"]]
        obj=bpy.data.objects.new(key,None)
        col.objects.link(obj)
        obj.location=spec["location"]
        obj.rotation_euler.z=spec["rotation"]
        for tag in ("family","district","task","status"):
            obj[tag]=spec[tag]
        roots[key]=obj
        for s in spec["sockets"]:
            socket=bpy.data.objects.new(key+"__SOCKET_"+s["name"],None)
            col.objects.link(socket)
            socket.parent=obj
            socket.location=s["location"]
            socket.empty_display_type="ARROWS"
            socket.empty_display_size=.4
            socket["direction"]=s["direction"]
    meshes={}
    for key,mesh in builder.meshes.items():
        data=bpy.data.meshes.new("JNX_MESH_"+key)
        data.from_pydata(mesh.vertices,[],mesh.faces)
        data.update()
        meshes[key]=data
    for item in builder.objects:
        data=meshes[item["mesh"]]
        if not data.materials:
            data.materials.append(materials[item["material"]])
        obj=bpy.data.objects.new(item["name"],data)
        roots[item["root"]].users_collection[0].objects.link(obj)
        obj.parent=roots[item["root"]]
        obj.location=item["location"]
        obj.rotation_euler.z=item["rotation"]
    world=bpy.data.worlds.new("JNX_World")
    world.use_nodes=True
    world.node_tree.nodes["Background"].inputs["Color"].default_value=(.32,.39,.45,1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value=.6
    scene.world=world
    sun_data=bpy.data.lights.new("JNX_Sun","SUN")
    sun_data.energy=2.0
    sun_data.angle=math.radians(15)
    sun=bpy.data.objects.new("JNX_Sun",sun_data)
    scene.collection.objects.link(sun)
    sun.rotation_euler=(.4,-.6,-.5)
    camera_data=bpy.data.cameras.new("JNX_Overview")
    camera_data.type="ORTHO"
    camera_data.ortho_scale=920
    camera_data.clip_end=5000
    camera=bpy.data.objects.new("JNX_Overview",camera_data)
    scene.collection.objects.link(camera)
    camera.location=(650,-820,800)
    camera.rotation_euler=(Vector((0,0,0))-camera.location).to_track_quat("-Z","Y").to_euler()
    scene.camera=camera
    scene.render.engine="CYCLES"
    scene.cycles.samples=8
    scene.cycles.device="CPU"
    scene.render.resolution_x=1280
    scene.render.resolution_y=960
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG"
    scene.render.filepath=str((folder/"overview.png").resolve())
    bpy.data.libraries.write(str((folder/"JNX_Expansion.blend").resolve()),{scene},compress=True)
    if preview:
        bpy.ops.render.render(write_still=True,scene=scene.name)
