"""Layer-2 bridges and docks: real arch openings, worn steps, mooring gear.

Layer 1 gave every crossing the same extruded hump and every dock a stack of
boxes. Here each link gets a voussoir arch with a clear waterway, approach
ramps that land on the district road at Z=2.12, and balustrades that follow the
deck curve. Docks step down to the water datum at Z=0 so boats sit correctly.

External contract is unchanged: instance ids, ``road_a``/``road_b``/``channel``
sockets on bridges and ``land``/``moor`` on docks keep their meaning from
docs/05_socket_pairs.md.
"""
from __future__ import annotations

import math

import geometry as g
from kernel import rng

ROAD_TOP = 0.12          # district path surface above ground datum (Z=2.12)
DECK_RISE = 2.7          # crown height above the road for the 24 m spans


def _approach(b, root, prefix, span, width, rise, sign, stream):
    """Ramp from the bridge abutment back into the district road.

    The bridge root sits at the channel centre with ground Z=2, so the ramp
    descends from the abutment to the road surface over a few metres of land.
    This is what keeps the crossing from floating at the shoreline.
    """
    runs = 4
    reach = 7.2
    for k in range(runs):
        t0 = k / runs
        t1 = (k + 1) / runs
        # Height tapers from the abutment down to the road top.
        z0 = ROAD_TOP + (rise * 0.16) * (1.0 - t0)
        z1 = ROAD_TOP + (rise * 0.16) * (1.0 - t1)
        length = reach / runs
        x = sign * (span / 2 + reach * (t0 + t1) / 2)
        b.box(root, f"{prefix}ramp_{sign}_{k}", (length, width, max(z0, z1)),
              (x, 0.0, max(z0, z1) / 2), "stone")
    # Kerb bands so the ramp reads as built, not as a wedge of ground.
    for side in (-1, 1):
        b.box(root, f"{prefix}kerb_{sign}_{side}",
              (reach, 0.34, 0.20),
              (sign * (span / 2 + reach / 2), side * (width / 2 - 0.17),
               ROAD_TOP + 0.10), "stone")


def bridge(b, link, stream):
    """One stone arch bridge with deck, spandrels, rails and approaches."""
    root = b.root(link["id"], "bridge", "WORLD", link["location"],
                  link["rotation"], task="tasks/assets/A041.md",
                  connects=[link["a"], link["b"]])
    span = link["span"]
    width = link["width"]
    rise = DECK_RISE if span <= 26 else DECK_RISE * 1.18

    verts, faces = g.arch_bridge_body(span, width, rise=rise,
                                      thickness=0.55, sections=25,
                                      arch_segments=14)
    b.mesh(root, "arch", verts, faces, "stone", (0.0, 0.0, ROAD_TOP))

    # Deck paving strip: slightly proud of the structural slab, worn smooth.
    steps = 18
    for k in range(steps):
        t0, t1 = k / steps, (k + 1) / steps
        z = rise * math.sin(math.pi * (t0 + t1) / 2) ** 0.85
        seg = span / steps
        b.box(root, f"tread_{k}", (seg * 0.92, width - 0.5, 0.09),
              (-span / 2 + span * (t0 + t1) / 2, 0.0, ROAD_TOP + z + 0.045),
              "stone")

    # Balustrades follow the deck curve; posts carry a continuous coping.
    for side in (-1, 1):
        posts = 9
        for k in range(posts):
            t = k / (posts - 1)
            x = -span / 2 + span * t
            z = rise * math.sin(math.pi * t) ** 0.85
            h = stream.uniform(0.92, 1.0)
            b.box(root, f"rail_post_{side}_{k}", (0.24, 0.24, h),
                  (x, side * (width / 2 - 0.18), ROAD_TOP + z + h / 2),
                  "stone")
        for k in range(posts - 1):
            t0, t1 = k / (posts - 1), (k + 1) / (posts - 1)
            x0 = -span / 2 + span * t0
            x1 = -span / 2 + span * t1
            z0 = rise * math.sin(math.pi * t0) ** 0.85
            z1 = rise * math.sin(math.pi * t1) ** 0.85
            mid_z = ROAD_TOP + (z0 + z1) / 2 + 0.84
            length = math.hypot(x1 - x0, z1 - z0)
            pitch = math.atan2(z1 - z0, x1 - x0)
            # Coping panels are boxes tilted to the local deck slope.
            vs, fs = _tilted_slab(length, 0.18, 0.22, pitch)
            b.mesh(root, f"rail_coping_{side}_{k}", vs, fs, "stone",
                   ((x0 + x1) / 2, side * (width / 2 - 0.18), mid_z))

    for sign in (-1, 1):
        _approach(b, root, "", span, width, rise, sign, stream)
        # Wing walls retain the embankment either side of the abutment.
        for side in (-1, 1):
            b.box(root, f"wing_{sign}_{side}", (1.1, 2.4, 2.3),
                  (sign * (span / 2 - 0.3), side * (width / 2 + 0.9), 1.15),
                  "stone")

    for sign, name in ((-1, "road_a"), (1, "road_b")):
        b.socket(root, name, (sign * (span / 2 + 7.2), 0.0, ROAD_TOP),
                 (sign, 0, 0))
    # Navigable channel under the crown, measured down to the water datum.
    b.socket(root, "channel", (0.0, 0.0, -link["location"][2]), (0, 1, 0))
    b.roots[root]["status"] = "detailed"
    b.roots[root]["clear_height_m"] = round(rise * 0.92, 2)


def _tilted_slab(length, height, depth, pitch):
    """A box rotated about local Y, used for sloping copings and gangways."""
    hx, hy, hz = length / 2, depth / 2, height / 2
    raw = [(-hx, -hy, -hz), (hx, -hy, -hz), (hx, hy, -hz), (-hx, hy, -hz),
           (-hx, -hy, hz), (hx, -hy, hz), (hx, hy, hz), (-hx, hy, hz)]
    c, s = math.cos(pitch), math.sin(pitch)
    verts = [(x * c - z * s, y, x * s + z * c) for x, y, z in raw]
    faces = [(3, 2, 1, 0), (4, 5, 6, 7), (0, 1, 5, 4),
             (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return verts, faces


def dock(b, district, index, location, stream):
    """Water steps (河埠头) descending from the quay to below the waterline."""
    root = b.root(f"JNX_{district}_DOCK_{index:02d}", "dock", district,
                  location, task="tasks/assets/A043.md")
    width = stream.choice((3.4, 4.0, 4.6))
    # Landing platform at quay level.
    b.box(root, "landing", (width + 1.2, 2.2, 0.28), (0.0, 1.1, 1.86), "stone")

    verts, faces = g.stepped_quay(width, 2.0, steps=9, tread=0.52)
    b.mesh(root, "steps", verts, faces, "stone", (0.0, -0.1, 0.0))

    # Two courses continue below the datum so the stair never ends in air.
    for k in range(2):
        b.box(root, f"submerged_{k}", (width, 0.52, 0.22),
              (0.0, -0.1 + 9 * 0.52 + k * 0.52, -0.11 - k * 0.22), "stone")

    for side in (-1, 1):
        b.box(root, f"cheek_{side}", (0.42, 9 * 0.52, 2.1),
              (side * (width / 2 + 0.21), -0.1 + 9 * 0.26, 1.05), "stone")
        verts, faces = g.revolve([(0.0, 0.0), (0.17, 0.0), (0.15, 0.62),
                                  (0.21, 0.72), (0.0, 0.78)], sides=10)
        b.mesh(root, f"bollard_{side}", verts, faces, "stone",
               (side * (width / 2 + 0.2), 1.4, 2.0))

    # Mooring line from the near bollard down toward the water.
    rope = g.rope_catenary((-(width / 2 + 0.2), 1.4, 2.72),
                           (-(width / 2 + 0.9), -1.6, 0.18),
                           sag=0.42, segments=12)
    b.mesh(root, "mooring_rope", rope[0], rope[1], "cloth")

    b.socket(root, "land", (0.0, 2.2, 2.0), (0, 1, 0))
    b.socket(root, "moor", (0.0, -0.1 + 9 * 0.52 + 1.0, 0.0), (0, -1, 0))
    b.roots[root]["status"] = "detailed"
    return root


def build(b, config, plan):
    seed = config["seed"]
    for link in plan["links"]:
        bridge(b, link, rng(seed, link["id"] + ":bridge"))

    for d in config["districts"]:
        cx, cy = d["center"]
        for i in range(d["dock_count"]):
            stream = rng(seed, f"{d['id']}:dock:{i}")
            # Spread docks along the south quay, off the road axis and the
            # bridge approaches.
            slots = (-52.0, -18.0, 22.0, 54.0)
            dx = slots[i % len(slots)] + stream.uniform(-3.0, 3.0)
            dock(b, d["id"], i, (cx + dx, cy - 78.5, 0.0), stream)
