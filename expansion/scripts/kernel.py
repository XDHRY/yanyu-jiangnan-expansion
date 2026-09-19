"""Pure-Python geometry and scene contract; one Blender unit is one metre.

This module deliberately has no bpy dependency. A blockout can be exported as
OBJ on any Python 3.10+ host and the same mesh graph can be written to .blend.
All coordinates passed to mesh()/box() are relative to an instance root.
"""
from __future__ import annotations

import hashlib
import math
import random
from dataclasses import dataclass, field


PALETTE = {
    "plaster": ((.64, .65, .60), .88),
    "tile": ((.07, .10, .11), .62),
    "timber": ((.16, .105, .065), .78),
    "stone": ((.30, .34, .33), .75),
    "earth": ((.22, .24, .16), .96),
    "water": ((.075, .18, .18), .25),
    "leaf": ((.12, .24, .13), .89),
    "bamboo": ((.29, .33, .15), .78),
    "cloth": ((.38, .30, .21), .96),
    "paper": ((.68, .44, .20), .82),
    "ceramic": ((.25, .16, .11), .55),
    "iron": ((.075, .08, .075), .62),
}


def rng(seed: int, key: str) -> random.Random:
    """An instance stream unaffected by the creation order of other districts."""
    digest = hashlib.sha256(f"{seed}:{key}".encode()).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


@dataclass
class Mesh:
    vertices: list
    faces: list


@dataclass
class SceneBuilder:
    seed: int
    meshes: dict[str, Mesh] = field(default_factory=dict)
    objects: list[dict] = field(default_factory=list)
    roots: dict[str, dict] = field(default_factory=dict)
    _names: set = field(default_factory=set)

    def root(self, instance: str, family: str, district: str, location,
             rotation=0.0, task="", **metadata) -> str:
        if instance in self.roots:
            raise ValueError(f"duplicate instance: {instance}")
        self.roots[instance] = dict(id=instance, family=family, district=district,
                                    location=list(location), rotation=rotation,
                                    task=task, status="blockout", sockets=[], **metadata)
        return instance

    def socket(self, root: str, name: str, location, direction=(0, -1, 0)):
        sockets = self.roots[root]["sockets"]
        if any(s["name"] == name for s in sockets):
            raise ValueError(f"duplicate socket {root}/{name}")
        sockets.append(dict(name=name, location=list(location), direction=list(direction)))

    def mesh(self, root: str, label: str, vertices, faces, material: str,
             location=(0, 0, 0), rotation=0.0):
        name = f"{root}__{label}"
        if name in self._names:
            raise ValueError(f"duplicate object {name}")
        if material not in PALETTE:
            raise ValueError(f"unknown material {material}")
        self._names.add(name)
        vertices = [tuple(float(v) for v in p) for p in vertices]
        faces = [tuple(f) for f in faces]
        key = hashlib.sha256(repr((vertices, faces, material)).encode()).hexdigest()[:24]
        self.meshes.setdefault(key, Mesh(vertices, faces))
        self.objects.append(dict(name=name, root=root, mesh=key, material=material,
                                 location=list(location), rotation=rotation))

    def box(self, root, label, size, location, material, rotation=0.0):
        if min(size) <= 0:
            raise ValueError(f"nonpositive box size {size}")
        x, y, z = (v / 2 for v in size)
        vertices = [(-x,-y,-z),(x,-y,-z),(x,y,-z),(-x,y,-z),
                    (-x,-y,z),(x,-y,z),(x,y,z),(-x,y,z)]
        faces = [(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
        self.mesh(root, label, vertices, faces, material, location, rotation)

    def cylinder(self, root, label, radius, height, location, material, sides=12,
                 top_radius=None):
        top = radius if top_radius is None else top_radius
        vertices = [(r * math.cos(math.tau*i/sides), r * math.sin(math.tau*i/sides), z)
                    for r,z in ((radius, 0), (top, height)) for i in range(sides)]
        faces = [(i,(i+1)%sides,(i+1)%sides+sides,i+sides) for i in range(sides)]
        faces += [tuple(reversed(range(sides))), tuple(range(sides, sides*2))]
        self.mesh(root, label, vertices, faces, material, location)

    def roof(self, root, label, width, depth, rise, location):
        """Closed gable volume. Tile rows and curved eaves are future tasks."""
        x, y = width/2, depth/2
        v = [(-x,-y,0),(x,-y,0),(x,y,0),(-x,y,0),(-x,0,rise),(x,0,rise)]
        f = [(3,2,1,0),(0,1,5,4),(4,5,2,3),(0,4,3),(1,2,5)]
        self.mesh(root, label, v, f, "tile", location)

    def world_vertices(self, obj):
        root = self.roots[obj["root"]]
        ca, sa = math.cos(obj["rotation"]), math.sin(obj["rotation"])
        cb, sb = math.cos(root["rotation"]), math.sin(root["rotation"])
        ox, oy, oz = obj["location"]
        rx, ry, rz = root["location"]
        for x, y, z in self.meshes[obj["mesh"]].vertices:
            a, b = ca*x-sa*y+ox, sa*x+ca*y+oy
            yield (cb*a-sb*b+rx, sb*a+cb*b+ry, z+oz+rz)

    def counts(self):
        return dict(instances=len(self.roots), mesh_objects=len(self.objects),
                    unique_meshes=len(self.meshes),
                    faces=sum(len(self.meshes[o["mesh"]].faces) for o in self.objects),
                    sockets=sum(len(r["sockets"]) for r in self.roots.values()))
