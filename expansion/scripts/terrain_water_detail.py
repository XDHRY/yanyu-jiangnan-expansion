"""Layer-2 terrain: irregular banks, stepped quays, paved curved streets.

Layer 1 shipped each district as a 168x160 box with two straight stone bands.
That reads as a grid of identical tiles from any distance. Here the land keeps
its planning envelope but gets a hand-cut water edge, the quay steps down to the
water datum instead of presenting one flat wall, and the roads are paved along
the same polylines the layout used to place buildings, so pavement and frontage
agree by construction.

The road_* sockets keep their layer-1 world positions because bridges resolve
against them (docs/05_socket_pairs.md).
"""
from __future__ import annotations

import math

from kernel import rng
import geometry as g

LAND_HALF_X = 84.0
LAND_HALF_Y = 80.0


def _pave(b, root, street, stream, top_z, ordinal):
    """Lay a jointed wet-stone street along the planning polyline.

    A single continuous ribbon looked like a green plastic floor in close review.
    Keep a dark base strip, then float individually gapped slabs over it.  The
    geometry is still lightweight (two slab rows, ~1.8 m longitudinal modules)
    but now carries a human-scale paving rhythm and real shadowed joints.
    """
    points = street["points"]
    if len(points) < 2:
        return
    half = street["width"] / 2.0
    base_verts, base_faces = [], []
    sections = []
    cum = [0.0]
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        cum.append(cum[-1] + math.hypot(x1 - x0, y1 - y0))
    total = cum[-1]
    samples = max(10, int(total / 1.8))
    for i in range(samples + 1):
        s = total * i / samples
        for k in range(len(cum) - 1):
            if s <= cum[k + 1] or k == len(cum) - 2:
                seg = max(cum[k + 1] - cum[k], 1e-9)
                f = (s - cum[k]) / seg
                (x0, y0), (x1, y1) = points[k], points[k + 1]
                px, py = x0 + (x1 - x0) * f, y0 + (y1 - y0) * f
                tx, ty = (x1 - x0) / seg, (y1 - y0) / seg
                break
        nx, ny = -ty, tx
        w = half * stream.uniform(0.95, 1.04)
        crown = 0.035 if street["kind"] in ("spine", "cross") else 0.018
        left = (px - nx * w, py - ny * w, top_z)
        centre = (px, py, top_z + crown)
        right = (px + nx * w, py + ny * w, top_z)
        sections.append((left, centre, right))
        base_verts.extend((left, right, centre))

    for i in range(len(sections) - 1):
        a = 3 * i
        q = a + 3
        base_faces.append((a, q, q + 2, a + 2))
        base_faces.append((a + 2, q + 2, q + 1, a + 1))
    # The base is intentionally earth-dark so the gaps between stones remain visible.
    b.mesh(root, f"road_base_{street['kind']}_{ordinal:02d}",
           base_verts, base_faces, "earth")

    slab_verts, slab_faces = [], []
    def slab(quad):
        cx = sum(p[0] for p in quad) / 4.0
        cy = sum(p[1] for p in quad) / 4.0
        cz = sum(p[2] for p in quad) / 4.0 + stream.uniform(0.012, 0.028)
        shrink = stream.uniform(0.925, 0.955)
        idx = len(slab_verts)
        for x, y, z in quad:
            slab_verts.append((
                cx + (x-cx) * shrink,
                cy + (y-cy) * shrink,
                z + (cz - sum(p[2] for p in quad)/4.0),
            ))
        slab_faces.append((idx, idx+1, idx+2, idx+3))

    for i in range(len(sections) - 1):
        l0, c0, r0 = sections[i]
        l1, c1, r1 = sections[i+1]
        # Alternate the centre joint slightly so the road avoids a perfect grid.
        if i % 2:
            m0 = tuple(c0[j] * .86 + r0[j] * .14 for j in range(3))
            m1 = tuple(c1[j] * .86 + r1[j] * .14 for j in range(3))
            slab((l0, l1, m1, m0))
            slab((m0, m1, r1, r0))
        else:
            m0 = tuple(c0[j] * .86 + l0[j] * .14 for j in range(3))
            m1 = tuple(c1[j] * .86 + l1[j] * .14 for j in range(3))
            slab((l0, l1, m1, m0))
            slab((m0, m1, r1, r0))
    b.mesh(root, f"paving_slabs_{street['kind']}_{ordinal:02d}",
           slab_verts, slab_faces, "stone")


def build(b, config, plan):
    ground = config["ground_z"]

    water = b.root("JNX_WORLD_WATER", "canal_network", "WORLD", (0, 0, 0),
                   task="tasks/systems/S01_water_network.md")
    # The slab has to outrun every camera. At 760 x 580 it ended inside the
    # overview frame, and its straight edge read as a hard rectangle laid over
    # the water; the overview ortho frame spans ~800 m, so cover it with room.
    x0, y0, x1, y1 = config["bounds"]
    span = max(x1 - x0, y1 - y0) + 900.0
    b.box(water, "water", (span, span, 0.15), (0, 0, -0.075), "water")
    b.socket(water, "water_datum", (0, 0, 0), (0, 0, 1))

    outlines = plan["land"]
    centers = plan["centers"]
    for d in config["districts"]:
        cx, cy = centers[d["id"]]
        stream = rng(config["seed"], d["id"] + ":terrain")
        r = b.root(f"JNX_{d['id']}_GROUND", "terrain", d["id"], (cx, cy, 0),
                   task=f"tasks/districts/{d['id']}.md")

        # The bank the layout placed against. Cutting a second outline here is
        # what used to put paving and whole plots over open water.
        outline = outlines[d["id"]]
        verts, faces = g.organic_slab(outline, ground, ground - 3.5)
        b.mesh(r, "land", verts, faces, "earth")

        # Stepped revetment walking the same bank as the land, so the stone
        # course meets the water wherever the outline happens to run. Four
        # straight walls at the nominal envelope left the revetment stranded
        # inland wherever the bank was bitten back.
        rv, rf = g.shore_revetment(outline, ground, steps=4)
        b.mesh(r, "revetment", rv, rf, "stone")

        # Paved streets follow the layout polylines (converted to local space).
        for ordinal, street in enumerate(plan["streets"][d["id"]]):
            local = dict(street)
            local["points"] = [[x - cx, y - cy] for x, y in street["points"]]
            _pave(b, r, local, stream, ground + 0.12, ordinal)

        # Road end sockets keep the layer-1 contract for bridge resolution.
        for label, pos, direction in (
            ("west", (-84, 0, ground), (-1, 0, 0)),
            ("east", (84, 0, ground), (1, 0, 0)),
            ("south", (0, -80, ground), (0, -1, 0)),
            ("north", (0, 80, ground), (0, 1, 0)),
        ):
            b.socket(r, "road_" + label, pos, direction)
