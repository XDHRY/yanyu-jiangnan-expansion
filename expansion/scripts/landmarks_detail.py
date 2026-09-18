"""District landmarks: halls, courtyards, temples, towers, academies, inns.

Landmarks carry the district silhouette, so they get hip roofs, bracket sets,
raised plinths and real courtyard walls rather than the shared hall topology of
layer 1. The external contract is unchanged: every landmark root keeps its
asset id, its ``forecourt`` socket and the reserved status of D07.
"""
from __future__ import annotations

import math

import geometry as g
from kernel import rng
import architecture_detail as ad


def _courtyard_wall(b, root, prefix, half_x, half_y, height, stream, gate_width=0.0):
    """Enclosing plaster wall with a tile cap; optional gap on the south side."""
    thickness = 0.34
    cap = 0.16
    for side in (-1, 1):
        b.box(root, prefix + f"wall_x_{side}", (thickness, half_y * 2, height),
              (side * half_x, 0.0, height / 2.0), "plaster")
        b.box(root, prefix + f"cap_x_{side}", (thickness + 0.26, half_y * 2, cap),
              (side * half_x, 0.0, height + cap / 2.0), "tile")
    b.box(root, prefix + "wall_y_north", (half_x * 2 + thickness, thickness, height),
          (0.0, half_y, height / 2.0), "plaster")
    b.box(root, prefix + "cap_y_north", (half_x * 2 + thickness, thickness + 0.26, cap),
          (0.0, half_y, height + cap / 2.0), "tile")
    if gate_width <= 0.0:
        b.box(root, prefix + "wall_y_south", (half_x * 2 + thickness, thickness, height),
              (0.0, -half_y, height / 2.0), "plaster")
        return
    run = (half_x * 2 + thickness - gate_width) / 2.0
    for side in (-1, 1):
        cx = side * (gate_width / 2.0 + run / 2.0)
        b.box(root, prefix + f"wall_y_south_{side}", (run, thickness, height),
              (cx, -half_y, height / 2.0), "plaster")
        b.box(root, prefix + f"cap_y_south_{side}", (run, thickness + 0.26, cap),
              (cx, -half_y, height + cap / 2.0), "tile")


def _paving(b, root, prefix, width, depth, stream, material="stone"):
    """Flagstone court laid as discrete slabs so joints read at middle distance."""
    cols = max(3, int(width // 2.6))
    rows = max(3, int(depth // 2.6))
    sx, sy = width / cols, depth / rows
    for i in range(cols):
        for j in range(rows):
            if stream.random() < 0.06:
                continue  # A missing flag reads as wear, not as a hole.
            jx = stream.uniform(-0.05, 0.05)
            jy = stream.uniform(-0.05, 0.05)
            b.box(root, prefix + f"flag_{i}_{j}",
                  (sx - 0.12, sy - 0.12, 0.09 + stream.uniform(0.0, 0.03)),
                  (-width / 2 + sx * (i + 0.5) + jx,
                   -depth / 2 + sy * (j + 0.5) + jy, 0.045), material)


def _hall(b, root, prefix, width, depth, stream, floors=1, height=None,
          location=(0.0, 0.0, 0.0), hip=True, open_sides=False, plinth_h=0.9):
    """A monumental hall: stone plinth, bracket eaves, hip roof, open bays."""
    ox, oy, oz = location
    h = height if height is not None else 4.6 * floors
    bays = max(3, int(width // 3.4) | 1)  # odd bay count centres the door

    b.box(root, prefix + "plinth", (width + 2.4, depth + 2.4, plinth_h),
          (ox, oy, oz + plinth_h / 2.0), "stone")
    b.box(root, prefix + "plinth_cap", (width + 2.8, depth + 2.8, 0.14),
          (ox, oy, oz + plinth_h + 0.07), "stone")
    b.box(root, prefix + "floor", (width, depth, 0.2),
          (ox, oy, oz + plinth_h + 0.24), "timber")

    base = oz + plinth_h + 0.34
    for sx in (-1, 1):
        for i in range(bays + 1):
            px = -width / 2 + width * i / bays
            verts, faces = g.column_base(0.34, 0.2)
            b.mesh(root, prefix + f"base_{sx}_{i}", verts, faces, "stone",
                   (px + ox, sx * (depth / 2 - 0.5) + oy, base))
            b.cylinder(root, prefix + f"post_{sx}_{i}", 0.26, h,
                       (px + ox, sx * (depth / 2 - 0.5) + oy, base + 0.2), "timber", 12, 0.23)
            verts, faces = g.bracket_block(0.42, 0.6, 0.19, 3, 0.26)
            b.mesh(root, prefix + f"bracket_{sx}_{i}", verts, faces, "timber",
                   (px + ox, sx * (depth / 2 - 0.5) + oy, base + h + 0.2))
        b.box(root, prefix + f"beam_{sx}", (width + 0.6, 0.34, 0.44),
              (ox, sx * (depth / 2 - 0.5) + oy, base + h + 0.98), "timber")
    b.box(root, prefix + "beam_mid", (0.3, depth - 0.6, 0.4),
          (ox, oy, base + h + 0.96), "timber")

    if not open_sides:
        door = min(3.2, width * 0.3)
        for sx in (-1, 1):
            b.box(root, prefix + f"wall_side_{sx}", (0.36, depth - 1.0, h),
                  (sx * (width / 2 - 0.18) + ox, oy, base + h / 2.0), "plaster")
        b.box(root, prefix + "wall_back", (width - 1.0, 0.36, h),
              (ox, depth / 2 - 0.18 + oy, base + h / 2.0), "plaster")
        verts, faces = g.wall_with_opening(width - 1.0, h, 0.36, (0.0, door, 3.4), 0.0)
        b.mesh(root, prefix + "wall_front", verts, faces, "plaster",
               (ox, -depth / 2 + 0.18 + oy, base))
        b.box(root, prefix + "door_frame", (door + 0.5, 0.46, 0.3),
              (ox, -depth / 2 + 0.18 + oy, base + 3.55), "timber")
        for sx in (-1, 1):
            b.box(root, prefix + f"door_jamb_{sx}", (0.24, 0.46, 3.4),
                  (sx * door / 2 + ox, -depth / 2 + 0.18 + oy, base + 1.7), "timber")
        for sx in (-1, 1):
            wx = (width - 1.0 - door) / 2.0 - 1.4
            if wx > 1.0:
                verts, faces = g.lattice_window(wx, 1.9, 0.07, max(3, int(wx // 0.5)), 4)
                b.mesh(root, prefix + f"window_{sx}", verts, faces, "timber",
                       (sx * (door / 2 + 0.7 + wx / 2) + ox,
                        -depth / 2 + 0.06 + oy, base + 1.3))

    rise = depth * 0.30
    eave = oz + plinth_h + 0.34 + h + 1.2
    # Courses must be laid on the same envelope as the shell, or they sink into it.
    rw, rd, over, lift, flare = ((width + 3.4, depth + 3.4, 1.35, 0.8, 0.5) if hip
                                 else (width + 3.2, depth + 3.2, 1.25, 0.75, 0.45))
    if hip:
        verts, faces = g.hip_roof_surface(rw, rd, rise, over, lift, flare)
    else:
        verts, faces = g.roof_surface(rw, rd, rise, over, lift, flare)
    b.mesh(root, prefix + "roof", verts, faces, "tile", (ox, oy, eave))
    verts, faces = g.roof_courses(rw, rd, rise, over, lift, flare, pitch=0.5)
    b.mesh(root, prefix + "roof_tiles", verts, faces, "tile", (ox, oy, eave + 0.02))
    verts, faces = g.ridge_tile(rw + 0.2, rise, lift, flare, 0.42, 0.34)
    b.mesh(root, prefix + "ridge", verts, faces, "tile", (ox, oy, eave))
    return eave + rise


def _tiered_tower(b, root, stream, tiers=3):
    """Lakeside watchtower: shrinking hip-roofed tiers over a stone podium."""
    b.box(root, "podium", (24.0, 20.0, 1.6), (0.0, 0.0, 0.8), "stone")
    verts, faces = g.stepped_quay(24.0, 1.6, 4, 0.6)
    b.mesh(root, "podium_steps", verts, faces, "stone", (0.0, -10.0, 0.0), math.pi)
    z = 1.6
    for level in range(tiers):
        width = 19.0 - level * 3.6
        depth = 15.0 - level * 2.8
        height = 4.2 - level * 0.3
        top = _hall(b, root, f"tier{level}_", width, depth, stream, height=height,
                    location=(0.0, 0.0, z), hip=True,
                    open_sides=level > 0, plinth_h=0.34 if level else 0.7)
        if level:
            for sx in (-1, 1):
                verts, faces = g.railing(depth - 1.0, 0.95, max(4, int(depth // 2.2)))
                b.mesh(root, f"tier{level}_rail_{sx}", verts, faces, "timber",
                       (sx * (width / 2 + 0.5), 0.0, z + 0.7), math.pi / 2)
        z = top - 0.5
    b.socket(root, "lookout", (0.0, 0.0, z), (0.0, -1.0, 0.0))


def _courtyard_complex(b, root, stream, kind):
    """Three-sided courtyard: gate house, main hall, flanking wings, paved court."""
    axis_strong = kind == "temple"
    court_w, court_d = 34.0, 30.0
    _paving(b, root, "court_", court_w - 2.0, court_d - 6.0, stream,
            "stone" if axis_strong else "earth")
    _courtyard_wall(b, root, "enc_", court_w / 2 + 3.0, court_d / 2 + 4.0,
                    3.2 if axis_strong else 2.6, stream, gate_width=10.0)

    main_floors = 2 if kind == "inn" else 1
    _hall(b, root, "main_", 26.0, 14.0, stream, floors=main_floors,
          height=6.4 if axis_strong else None,
          location=(0.0, court_d / 2 - 2.0, 0.0), hip=True,
          plinth_h=1.3 if axis_strong else 0.9)
    for sx in (-1, 1):
        _hall(b, root, f"wing_{sx}_", 9.0, 22.0, stream, floors=1,
              location=(sx * (court_w / 2 - 1.0), -2.0, 0.0), hip=False,
              open_sides=True, plinth_h=0.6)
    _hall(b, root, "gate_", 12.0, 7.0, stream, floors=1,
          location=(0.0, -court_d / 2 - 4.0, 0.0), hip=True,
          open_sides=True, plinth_h=0.7)

    # Axis furniture: a censer for temples, a well for living courtyards.
    if axis_strong:
        verts, faces = g.revolve([(0.0, 0.0), (1.1, 0.0), (1.25, 0.5), (0.95, 1.05),
                                  (1.15, 1.2), (0.0, 1.3)], 18)
        b.mesh(root, "censer", verts, faces, "iron", (0.0, -4.0, 0.1))
    else:
        verts, faces = g.revolve([(0.9, 0.0), (0.9, 0.62), (0.72, 0.62), (0.72, 0.0)], 20)
        b.mesh(root, "well_ring", verts, faces, "stone", (0.0, -5.0, 0.1))
        b.box(root, "well_lip", (2.3, 2.3, 0.1), (0.0, -5.0, 0.1), "stone")
    b.socket(root, "court_centre", (0.0, -4.0, 0.1), (0.0, 0.0, 1.0))


def build(b, config, plan):
    """One landmark per district, keyed by the manifest's landmark field."""
    for d in config["districts"]:
        cx, cy = d["center"]
        kind = d["landmark"]
        stream = rng(config["seed"], d["id"] + ":landmark")
        root = b.root(f"JNX_{d['id']}_LANDMARK", kind, d["id"],
                      (cx, cy + 46.0, config["ground_z"]),
                      task=f"tasks/districts/{d['id']}.md")

        if kind == "legacy_reserve":
            # Reserve the old courtyard's footprint; never import or run legacy.
            b.box(root, "reserve_plinth", (60.0, 48.0, 0.2), (0.0, 0.0, 0.1), "stone")
            for sx in (-1, 1):
                verts, faces = g.stepped_quay(48.0, 0.9, 3, 0.5)
                b.mesh(root, f"reserve_step_{sx}", verts, faces, "stone",
                       (sx * 30.0, 0.0, 0.0), math.pi / 2 if sx > 0 else -math.pi / 2)
            b.roots[root]["status"] = "reserved_not_imported"
            b.socket(root, "legacy_anchor", (0.0, 0.0, 0.2), (0.0, -1.0, 0.0))
            b.socket(root, "forecourt", (0.0, -26.0, 0.0))
            continue

        if kind == "tower":
            _tiered_tower(b, root, stream)
        elif kind in ("courtyard", "academy", "temple", "inn"):
            _courtyard_complex(b, root, stream, kind)
        elif kind == "pavilion":
            _hall(b, root, "main_", 12.0, 12.0, stream, floors=1,
                  hip=True, open_sides=True, plinth_h=1.1)
            for sx in (-1, 1):
                verts, faces = g.railing(11.0, 0.9, 6)
                b.mesh(root, f"rail_{sx}", verts, faces, "timber",
                       (sx * 5.6, 0.0, 1.24), math.pi / 2)
        elif kind == "warehouse":
            _hall(b, root, "main_", 30.0, 18.0, stream, floors=1, height=6.0,
                  hip=False, plinth_h=0.8)
            for i in range(3):
                b.box(root, f"crate_{i}", (1.8, 1.6, 1.4),
                      (-10.0 + i * 9.0, -13.0, 0.7), "timber",
                      stream.uniform(-0.3, 0.3))
        elif kind == "workshop":
            _hall(b, root, "main_", 26.0, 16.0, stream, floors=1, hip=False,
                  open_sides=True, plinth_h=0.7)
            for sx in (-1, 1):
                _hall(b, root, f"shed_{sx}_", 8.0, 12.0, stream, floors=1,
                      location=(sx * 19.0, -4.0, 0.0), hip=False,
                      open_sides=True, plinth_h=0.45)
            for i in range(4):
                verts, faces = g.revolve([(0.0, 0.0), (0.85, 0.05), (0.95, 0.75),
                                          (0.8, 0.95), (0.0, 0.98)], 16)
                b.mesh(root, f"vat_{i}", verts, faces, "ceramic",
                       (-9.0 + i * 6.0, -12.0, 0.0))
        else:  # hall
            _hall(b, root, "main_", 28.0, 16.0, stream, floors=1, hip=True,
                  plinth_h=1.0)
            _paving(b, root, "fore_", 26.0, 10.0, stream)

        b.socket(root, "forecourt", (0.0, -25.0, 0.0))
