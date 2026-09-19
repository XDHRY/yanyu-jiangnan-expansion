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
    if hip:
        beast_x = max(0.0, (rw - rd) / 2.0) + 0.38
        beast_z = eave + rise + 0.14
        beast_s = 1.15
    else:
        beast_x = rw / 2.0 + flare * 0.4
        beast_z = eave + rise + lift * 0.4 + 0.22
        beast_s = 0.9
    for sx in (-1, 1):
        bv, bf = g.ridge_beast(scale=beast_s)
        b.mesh(root, prefix + f"chiwen_{sx}", bv, bf, "ceramic",
               (ox + sx * beast_x, oy, beast_z), 0.0 if sx > 0 else math.pi)
    if not open_sides:
        fv, ff = g.hanging_fascia(width * 0.78, height=0.55, cols=max(5, int(width / 2.2)))
        b.mesh(root, prefix + "fascia", fv, ff, "timber",
               (ox, -depth / 2 + 0.42 + oy, eave - 0.35))
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


def _build_tingyuxuan_courtyard(b, root, stream):
    """The central artistic showcase: Moon gate, Tingyuxuan pavilion, scholar rocks, leaning plum."""
    # 1. Base courtyard plinth & pond
    b.box(root, "court_plinth", (42.0, 36.0, 0.45), (0.0, 0.0, 0.225), "stone")
    b.box(root, "pond", (22.0, 12.0, 0.12), (0.0, -4.0, 0.40), "water")
    # Pond stone borders
    for side in (-1, 1):
        for j in range(12):
            b.box(root, f"pond_border_y_{side}_{j}", (0.55, 1.0, 0.32),
                  (side * 11.2, -9.5 + j * 1.0, 0.45), "stone")
    for j in range(22):
        b.box(root, f"pond_border_x_{j}", (1.0, 0.55, 0.32),
              (-10.5 + j * 1.0, -10.2, 0.45), "stone")
    # S-curved stepping stones crossing the quiet pond
    for i in range(10):
        sy = -8.5 + i * 0.95
        sx = 1.6 * math.sin(i * 0.42) - 0.8
        b.box(root, f"stepping_stone_{i}", (1.2, 0.6, 0.25), (sx, sy, 0.46), "stone")

    # 2. Moon gate wall with true circular aperture
    gx, gy, zc = 1.4, 7.5, 2.7
    rad, H = 2.0, 5.0
    wall_thick = 0.46
    # West wall & East wall
    b.box(root, "wall_west", (12.0, wall_thick, H), (gx - rad - 6.0, gy, H / 2), "plaster")
    b.box(root, "wall_east", (10.0, wall_thick, H), (gx + rad + 5.0, gy, H / 2), "plaster")
    # Wall footing stone
    b.box(root, "wall_footing_w", (12.2, wall_thick + 0.12, 0.46), (gx - rad - 6.0, gy, 0.23), "stone")
    b.box(root, "wall_footing_e", (10.2, wall_thick + 0.12, 0.46), (gx + rad + 5.0, gy, 0.23), "stone")
    # Wall top tile cap
    b.roof(root, "wall_tiles_w", 12.4, 1.4, 0.35, (gx - rad - 6.0, gy, H))
    b.roof(root, "wall_tiles_e", 10.4, 1.4, 0.35, (gx + rad + 5.0, gy, H))

    # Circular moon gate aperture mesh
    v, f = [], []
    n_seg = 64
    for i in range(n_seg):
        a = 2 * math.pi * i / n_seg
        b_ang = 2 * math.pi * (i + 1) / n_seg
        inner = [(gx + rad * math.cos(t), zc + rad * math.sin(t)) for t in [a, b_ang]]
        outer = []
        for t in [a, b_ang]:
            dx, dz = math.cos(t), math.sin(t)
            fac = min(rad * 1.01 / max(abs(dx), 1e-6),
                      ((H - zc) if dz > 0 else zc) / max(abs(dz), 1e-6))
            outer.append((gx + fac * dx, zc + fac * dz))
        k = len(v)
        for y in [gy - wall_thick / 2, gy + wall_thick / 2]:
            v.extend([
                (inner[0][0], y, inner[0][1]),
                (inner[1][0], y, inner[1][1]),
                (outer[1][0], y, outer[1][1]),
                (outer[0][0], y, outer[0][1]),
            ])
        f.extend([
            (k, k + 1, k + 2, k + 3),
            (k + 7, k + 6, k + 5, k + 4),
            (k, k + 4, k + 5, k + 1),
        ])
    b.mesh(root, "moon_gate_wall", v, f, "plaster")

    # Segmented brick voussoir: discrete wedges with recessed mortar joints.
    v_arch, f_arch = g.segmented_arch_voussoir(
        rad, wall_thick + 0.10, brick_depth=0.22, n_bricks=40, mortar=0.018)
    b.mesh(root, "moon_gate_voussoir", v_arch, f_arch, "stone", (gx, gy, zc))
    # Inner reveal ring so the aperture reads as masonry, not a cut plaster hole.
    v_rev, f_rev = g.segmented_arch_voussoir(
        rad - 0.04, wall_thick - 0.08, brick_depth=0.05, n_bricks=32, mortar=0.012)
    b.mesh(root, "moon_gate_reveal", v_rev, f_rev, "stone", (gx, gy, zc))

    # East lattice window on return wall
    b.box(root, "east_return_wall", (0.46, 12.0, 3.8), (gx + rad + 10.0, gy - 6.0, 1.9), "plaster")
    for wy in (gy - 3.0, gy - 8.0):
        wv, wf = g.lattice_window(1.4, 1.6, 0.06, 4, 4)
        b.mesh(root, f"lattice_window_{int(wy)}", wv, wf, "timber", (gx + rad + 10.0, wy, 2.0), math.pi / 2)

    # 3. Tingyuxuan open tea pavilion (West side of the pond)
    tx, ty = -9.5, 0.5
    b.box(root, "tingyu_plinth", (7.0, 7.0, 0.42), (tx, ty, 0.66), "stone")
    # Four corner stone bases and wooden pillars
    for cx in (tx - 2.5, tx + 2.5):
        for cy_col in (ty - 2.5, ty + 2.5):
            verts, faces = g.column_base(0.30, 0.22)
            b.mesh(root, f"tingyu_base_{int(cx)}_{int(cy_col)}", verts, faces, "stone", (cx, cy_col, 0.87))
            b.cylinder(root, f"tingyu_post_{int(cx)}_{int(cy_col)}", 0.18, 3.8, (cx, cy_col, 1.09), "timber")
    # Pavilion roof beams
    b.box(root, "tingyu_beam_x1", (6.4, 0.28, 0.36), (tx, ty - 2.5, 4.89), "timber")
    b.box(root, "tingyu_beam_x2", (6.4, 0.28, 0.36), (tx, ty + 2.5, 4.89), "timber")
    b.box(root, "tingyu_beam_y1", (0.28, 6.4, 0.36), (tx - 2.5, ty, 4.89), "timber")
    b.box(root, "tingyu_beam_y2", (0.28, 6.4, 0.36), (tx + 2.5, ty, 4.89), "timber")
    # Carved hanging fascia (挂落) on the four eave beams
    for side, rot, loc in (
        (0.0, 0.0, (tx, ty - 2.5, 4.71)),
        (math.pi, 0.0, (tx, ty + 2.5, 4.71)),
        (math.pi / 2, 0.0, (tx - 2.5, ty, 4.71)),
        (-math.pi / 2, 0.0, (tx + 2.5, ty, 4.71)),
    ):
        fv, ff = g.hanging_fascia(5.6, height=0.48, cols=5)
        b.mesh(root, f"tingyu_fascia_{int(side * 10)}", fv, ff, "timber", loc, side)
    # 美人靠 benches facing the pond on the south and east openings
    bv, bf = g.beauty_lean(5.2, height=0.78, curve=0.22, posts=5)
    b.mesh(root, "tingyu_lean_south", bv, bf, "timber", (tx, ty - 2.55, 0.87))
    b.mesh(root, "tingyu_lean_east", bv, bf, "timber",
           (tx + 2.55, ty, 0.87), -math.pi / 2)
    # Hip roof over Tingyuxuan
    rv, rf = g.hip_roof_surface(8.2, 8.2, 2.4, 1.1, 0.65, 0.4)
    b.mesh(root, "tingyu_roof", rv, rf, "tile", (tx, ty, 5.05))
    rcv, rcf = g.roof_courses(8.2, 8.2, 2.4, 1.1, 0.65, 0.4, pitch=0.45)
    b.mesh(root, "tingyu_roof_courses", rcv, rcf, "tile", (tx, ty, 5.07))
    rtv, rtf = g.ridge_tile(8.4, 2.4, 0.65, 0.4, 0.32, 0.24)
    b.mesh(root, "tingyu_ridge", rtv, rtf, "tile", (tx, ty, 5.05))
    # Square hip: a short pair of 正吻 sitting on the peak, not the eaves.
    for sx in (-1, 1):
        cv, cf = g.ridge_beast(scale=0.95)
        b.mesh(root, f"tingyu_chiwen_{sx}", cv, cf, "ceramic",
               (tx + sx * 0.42, ty, 7.57), 0.0 if sx > 0 else math.pi)
    # Tea table and bench
    b.box(root, "tea_table", (2.4, 1.0, 0.16), (tx, ty, 1.60), "timber")
    b.box(root, "tea_leg_1", (0.16, 0.8, 0.72), (tx - 0.9, ty, 1.24), "timber")
    b.box(root, "tea_leg_2", (0.16, 0.8, 0.72), (tx + 0.9, ty, 1.24), "timber")
    # Ceramic tea pot and cups
    b.cylinder(root, "tea_pot", 0.15, 0.22, (tx, ty, 1.68), "ceramic", sides=10)
    for cup_x in (tx - 0.4, tx + 0.4):
        b.cylinder(root, f"tea_cup_{int(cup_x*10)}", 0.06, 0.08, (cup_x, ty - 0.1, 1.68), "ceramic", sides=8)
    # Lit lantern under pavilion eave
    b.cylinder(root, "tingyu_lantern_post", 0.05, 0.6, (tx, ty, 4.3), "iron", sides=6)
    sv, sf = g.revolve([(0.04, 0), (0.24, 0.1), (0.26, 0.35), (0.20, 0.5), (0.05, 0.55)], sides=12)
    b.mesh(root, "tingyu_lantern_shade", sv, sf, "paper", (tx, ty, 3.75))

    # 4. Scholar rocks (Taihu stones, 瘦漏透皱) by the water
    for idx, (rx, ry, h_scale, r_scale) in enumerate([
        (-4.8, -1.2, 2.6, 0.85),
        (7.5, -2.5, 3.1, 0.95),
        (-6.2, -6.0, 1.8, 0.65),
    ]):
        sv, sf = g.scholar_rock_sculpt(h_scale, r_scale, stream)
        b.mesh(root, f"scholar_stone_{idx}", sv, sf, "stone", (rx, ry, 0.45))
        # Moss footings around rocks
        for mi in range(6):
            ma = stream.uniform(0, math.tau)
            mr = stream.uniform(0.4, 0.9)
            b.box(root, f"rock_moss_{idx}_{mi}", (0.35, 0.25, 0.12),
                  (rx + mr * math.cos(ma), ry + mr * math.sin(ma), 0.46), "leaf")

    # 5. The iconic leaning plum tree (老梅苍干与主景横斜枝)
    tree_base = (-3.8, 2.5, 0.45)
    (trunk_v, trunk_f), spine = g.branch_skeleton(5.8, stream, taper=0.22, base_radius=0.34, bends=6)
    b.mesh(root, "plum_trunk", trunk_v, trunk_f, "timber", tree_base)
    # Lateral arching boughs crossing over the pond and toward the moon gate
    bough_pts = [
        (-3.8, 2.5, 2.8),
        (-2.2, 2.0, 3.4),
        (-0.5, 2.4, 4.0),
        (1.2, 3.2, 4.5),
        (2.8, 3.8, 4.7),
        (4.2, 4.4, 5.1),
    ]
    bough_v, bough_f = g.sweep([(0.14, 0), (0.10, 0.10), (0, 0.14), (-0.10, 0.10),
                                (-0.14, 0), (-0.10, -0.10), (0, -0.14), (0.10, -0.10)],
                               bough_pts, close_profile=True)
    b.mesh(root, "plum_bough", bough_v, bough_f, "timber")
    # Secondary hanging twigs (垂梢)
    for tw_idx, t_pos in enumerate([( -1.2, 2.2, 3.6), ( 0.8, 3.0, 4.2), ( 2.5, 3.6, 4.4)]):
        tw_pts = [t_pos, (t_pos[0]+0.3, t_pos[1]-0.4, t_pos[2]-0.7), (t_pos[0]+0.5, t_pos[1]-0.6, t_pos[2]-1.3)]
        tw_v, tw_f = g.sweep([(0.04, 0), (0, 0.04), (-0.04, 0), (0, -0.04)], tw_pts, close_profile=True)
        b.mesh(root, f"plum_twig_{tw_idx}", tw_v, tw_f, "timber")

    # Five-petal ivory blossoms along the bough — night-readable, not leafy blobs.
    def _orient_blossom(verts, yaw, pitch):
        cy, sy = math.cos(yaw), math.sin(yaw)
        cp, sp = math.cos(pitch), math.sin(pitch)
        out = []
        for x, y, z in verts:
            x1, z1 = x * cp + z * sp, -x * sp + z * cp
            out.append((x1 * cy - y * sy, x1 * sy + y * cy, z1))
        return out

    for b_idx in range(72):
        t = (b_idx + 0.5) / 72.0
        bx = -3.8 + t * 8.0 + stream.uniform(-0.28, 0.28)
        by = 2.0 + t * 2.4 + stream.uniform(-0.28, 0.28)
        bz = 2.6 + t * 2.5 + stream.uniform(-0.18, 0.28)
        size = stream.uniform(0.07, 0.12)
        cv, cf = g.plum_blossom(size, angle=stream.uniform(0, math.tau))
        cv = _orient_blossom(cv, stream.uniform(-0.4, 0.4), stream.uniform(-0.9, -0.25))
        b.mesh(root, f"plum_blossom_{b_idx}", cv, cf, "leaf", (bx, by, bz))

    # Petals scattered across the quiet pond surface (水上落梅)
    for p_idx in range(64):
        px = stream.uniform(-8.5, 8.5)
        py = stream.uniform(-9.5, -0.2)
        pv, pf = g.plum_blossom(stream.uniform(0.05, 0.08), angle=stream.uniform(0, math.tau))
        pv = _orient_blossom(pv, stream.uniform(0, math.tau), -math.pi / 2 + stream.uniform(-0.15, 0.15))
        b.mesh(root, f"pond_petal_{p_idx}", pv, pf, "cloth", (px, py, 0.455))

    # Stone bench for contemplating the water (观水石榻)
    b.box(root, "stone_bench", (2.4, 0.75, 0.22), (5.5, 1.2, 0.68), "stone")
    b.box(root, "stone_bench_leg1", (0.35, 0.55, 0.46), (4.6, 1.2, 0.34), "stone")
    b.box(root, "stone_bench_leg2", (0.35, 0.55, 0.46), (6.4, 1.2, 0.34), "stone")

    # Stroll path extending behind the moon gate toward the borrowed landscape
    for p_idx in range(8):
        b.box(root, f"north_stone_path_{p_idx}", (1.6, 0.9, 0.14),
              (gx + 0.3 * math.sin(p_idx * 0.6), gy + 2.5 + p_idx * 1.1, 0.46), "stone")
    # Calligraphic bamboo beyond the wall: the 借景 that the moon gate is for.
    for i in range(9):
        bx = gx + stream.uniform(-3.2, 3.2)
        by = gy + 5.5 + stream.uniform(0.0, 7.0)
        h = stream.uniform(4.6, 7.8)
        lean = stream.uniform(-0.18, 0.18)
        b.cylinder(root, f"borrowed_bamboo_{i}", 0.045, h,
                   (bx + lean, by, 0.45), "bamboo", sides=8)
        fv, ff = g.willow_fronds(5, stream.uniform(0.7, 1.2), stream, radius=0.018)
        b.mesh(root, f"borrowed_bamboo_frond_{i}", fv, ff, "leaf",
               (bx + lean, by, 0.45 + h * 0.72))

    b.socket(root, "legacy_anchor", (0.0, 0.0, 0.45), (0.0, -1.0, 0.0))
    b.socket(root, "moon_gate", (gx, gy, zc), (0.0, -1.0, 0.0))
    b.socket(root, "forecourt", (0.0, -18.0, 0.0))


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
            _build_tingyuxuan_courtyard(b, root, stream)
            b.roots[root]["status"] = "detailed_legacy_courtyard"
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
