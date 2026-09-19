"""Layer-2 props and planting: real hulls, awnings, lanterns, crowns, reeds.

Layer 1 used cylinder trunks with cone crowns on a straight perimeter belt, and
placed boats as folded plates. The silhouette of a canal town comes mostly from
willows leaning over water, bamboo clumps of uneven height and moored boats with
an actual open interior, so those are the three things rebuilt here.

Planting is scattered with a Poisson-ish dart throw that respects the street
polylines, so nothing grows in the middle of a road or on a bridge landing.
"""
from __future__ import annotations

import math

from kernel import rng
import geometry as g

LAND_HALF_X = 84.0
LAND_HALF_Y = 80.0


def _street_clearance(streets, x, y):
    """Shortest distance from a local point to any street centreline."""
    best = 1e9
    for street in streets:
        pts = street["points"]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            dx, dy = x1 - x0, y1 - y0
            seg = dx * dx + dy * dy
            if seg < 1e-9:
                continue
            t = max(0.0, min(1.0, ((x - x0) * dx + (y - y0) * dy) / seg))
            px, py = x0 + dx * t, y0 + dy * t
            best = min(best, math.hypot(x - px, y - py) - street["width"] / 2.0)
    return best


def _scatter(count, stream, streets, parcels, cx, cy, margin=5.0, tries=60,
             outline=None):
    """Dart-throw positions that avoid roads, plots and the landmark block."""
    out = []
    while len(out) < count and tries > 0:
        tries -= 1
        for _ in range(count * 8):
            if len(out) >= count:
                break
            x = stream.uniform(-LAND_HALF_X + margin, LAND_HALF_X - margin)
            y = stream.uniform(-LAND_HALF_Y + margin, LAND_HALF_Y - margin)
            # Keep trunks on the built bank, not on the nominal envelope.
            if outline is not None and g.polygon_clearance(outline, x, y) < 3.0:
                continue
            if _street_clearance(streets, x, y) < 2.2:
                continue
            if -36.0 < x < 36.0 and 18.0 < y < 76.0:
                continue
            wx, wy = cx + x, cy + y
            if any(p[0] - 1.5 < wx < p[2] + 1.5 and p[1] - 1.5 < wy < p[3] + 1.5
                   for p in parcels):
                continue
            if any(math.hypot(x - ox, y - oy) < 5.0 for ox, oy in out):
                continue
            out.append((x, y))
    return out


def _willow(b, r, height, stream):
    (tv, tf), spine = g.branch_skeleton(height * 0.62, stream, taper=0.2,
                                        base_radius=0.3, bends=5)
    b.mesh(r, "trunk", tv, tf, "timber")
    tipx, tipy, _ = spine[-1]
    for i in range(3):
        a = stream.uniform(0, math.tau)
        rad = stream.uniform(1.1, 2.0)
        cv, cf = g.leaf_cluster(stream.uniform(1.5, 2.3), stream, lobes=4,
                               squash=0.6)
        b.mesh(r, f"canopy_{i}", cv, cf, "leaf",
               (tipx + math.cos(a) * rad, tipy + math.sin(a) * rad, height * 0.58))
    fv, ff = g.willow_fronds(26, height * 0.42, stream)
    b.mesh(r, "fronds", fv, ff, "leaf", (tipx, tipy, height * 0.66))


def _broadleaf(b, r, height, stream):
    (tv, tf), spine = g.branch_skeleton(height * 0.58, stream, bends=5,
                                        base_radius=0.24, taper=0.22)
    b.mesh(r, "trunk", tv, tf, "timber")
    tipx, tipy, _ = spine[-1]
    # Several smaller overlapping crowns read as foliage masses instead of the
    # old four-lobed low-poly ball, especially in eye-level street shots.
    count = stream.randint(7, 10)
    for i in range(count):
        a = stream.uniform(0, math.tau)
        rad = stream.uniform(0.35, 2.15) * (0.72 if i < 2 else 1.0)
        z = height * stream.uniform(0.48, 0.83)
        size = stream.uniform(1.0, 1.85) * (1.18 if i < 2 else 1.0)
        cv, cf = g.leaf_cluster(size, stream, lobes=stream.randint(5, 8),
                               squash=stream.uniform(0.58, 0.88))
        b.mesh(r, f"canopy_{i}", cv, cf, "leaf",
               (tipx + math.cos(a) * rad, tipy + math.sin(a) * rad, z))


def _bamboo_clump(b, r, stream):
    for n in range(stream.randint(5, 9)):
        h = stream.uniform(6.0, 11.0)
        ox, oy = stream.uniform(-1.1, 1.1), stream.uniform(-1.1, 1.1)
        lean = stream.uniform(-0.09, 0.09)
        (cv, cf), spine = g.branch_skeleton(h, stream, taper=0.35,
                                            base_radius=0.075, bends=2, sides=6)
        b.mesh(r, f"culm_{n}", cv, cf, "bamboo", (ox, oy, 0), lean)
        tipx, tipy, _ = spine[-1]
        for k in range(2):
            lv, lf = g.leaf_cluster(stream.uniform(0.7, 1.15), stream, lobes=3,
                                    squash=0.5)
            b.mesh(r, f"sprig_{n}_{k}", lv, lf, "leaf",
                   (ox + tipx, oy + tipy, h * stream.uniform(0.68, 0.93)))


def _boat(b, r, stream, awning=True):
    hv, hf = g.boat_hull(stream.uniform(6.4, 8.0), stream.uniform(1.9, 2.3), 0.85)
    b.mesh(r, "hull", hv, hf, "timber")
    if awning:
        av, af = g.arched_awning(stream.uniform(3.0, 3.8), 1.85, 0.62)
        b.mesh(r, "awning", av, af, "bamboo", (stream.uniform(-0.5, 0.5), 0, 0.42))
    b.cylinder(r, "pole", 0.05, stream.uniform(2.6, 3.4), (2.3, 0, 0.35), "bamboo", 6)
    b.box(r, "bench", (0.9, 1.3, 0.09), (-1.4, 0, 0.36), "timber")
    # Sculling oar mounted at the stern
    ov, of = g.boat_oar()
    b.mesh(r, "sculling_oar", ov, of, "timber", (-3.1, 0.45, 0.65), rotation=0.35)
    # Fish basket on the deck
    b.cylinder(r, "fish_basket", 0.22, 0.35, (2.1, 0.35, 0.38), "bamboo", sides=8)
    b.socket(r, "moor_bow", (-3.2, 0, 0.5), (-1, 0, 0))


def build(b, config, plan):
    parcels = [x["parcel"] for x in plan["buildings"]]
    centers = plan["centers"]
    outlines = plan["land"]
    for d in config["districts"]:
        cx, cy = centers[d["id"]]
        outline = outlines[d["id"]]
        z = config["ground_z"]
        streets = [dict(kind=s["kind"], width=s["width"],
                        points=[[x - cx, y - cy] for x, y in s["points"]])
                   for s in plan["streets"][d["id"]]]
        district_parcels = [p for p in parcels]

        stream = rng(config["seed"], d["id"] + ":stalls")
        for i in range(d["stall_count"]):
            spine = next(s for s in streets if s["kind"] == "spine")
            frac = (i + 0.5) / max(1, d["stall_count"])
            pts = spine["points"]
            idx = min(int(frac * (len(pts) - 1)), len(pts) - 2)
            (x0, y0), (x1, y1) = pts[idx], pts[idx + 1]
            f = frac * (len(pts) - 1) - idx
            px, py = x0 + (x1 - x0) * f, y0 + (y1 - y0) * f
            tx, ty = x1 - x0, y1 - y0
            tl = math.hypot(tx, ty) or 1.0
            nx, ny = -ty / tl, tx / tl
            side = 1 if i % 2 else -1
            px += nx * side * (spine["width"] / 2 + 1.6)
            py += ny * side * (spine["width"] / 2 + 1.6)
            rot = math.atan2(ty, tx)
            r = b.root(f"JNX_{d['id']}_STALL_{i:02d}", "stall", d["id"],
                       (cx + px, cy + py, z), rot, task="tasks/assets/A053.md")
            # Street stalls used to be identical 3.3 x 2.2 m blue canopies,
            # which read as modern industrial awnings in close shots. Give each
            # one a smaller, slightly irregular footprint and denser wares.
            stall_w = stream.uniform(2.35, 2.80)
            stall_d = stream.uniform(1.05, 1.35)
            canopy_h = stream.uniform(2.02, 2.24)
            b.box(r, "table", (stall_w - 0.18, stall_d * 0.78, 0.11),
                  (0, 0, 0.88), "timber")
            px_post = stall_w * 0.44
            py_post = stall_d * 0.42
            for xx in (-px_post, px_post):
                for yy in (-py_post, py_post):
                    b.cylinder(r, f"post_{xx}_{yy}", 0.05, canopy_h,
                               (xx, yy, 0), "timber", 6)
            av, af = g.arched_awning(stall_w + 0.20, stall_d + 0.18,
                                     stream.uniform(0.10, 0.18), ribs=4)
            # Name intentionally avoids the "awning" material variant so market
            # covers use weathered hemp rather than saturated indigo banner dye.
            b.mesh(r, "hemp_cover", av, af, "cloth", (0, 0, canopy_h))

            # Layered small-scale clutter makes the market read as inhabited
            # without introducing expensive unique meshes.
            for ci in range(2):
                cw = stream.uniform(0.42, 0.62)
                cd = stream.uniform(0.38, 0.55)
                ch = stream.uniform(0.30, 0.48)
                b.box(r, f"crate_{ci}", (cw, cd, ch),
                      (stream.uniform(-0.9, 0.9),
                       -stall_d * 0.56 - ci * 0.12,
                       ch * 0.5), "timber")
            for bi, bx in enumerate((-0.72, 0.70)):
                b.cylinder(r, f"basket_{bi}", stream.uniform(0.18, 0.24),
                           stream.uniform(0.22, 0.30),
                           (bx, stream.uniform(-0.05, 0.22), 1.02),
                           "bamboo", 8)
            for ji, jx in enumerate((-0.45, 0.05, 0.48)):
                b.cylinder(r, f"jar_{ji}", stream.uniform(0.10, 0.15),
                           stream.uniform(0.23, 0.34),
                           (jx, stream.uniform(0.00, 0.25), 1.00),
                           "ceramic", 8)
            b.box(r, "cloth_bolt", (0.48, 0.16, 0.10),
                  (0.05, 0.32, 1.01), "cloth")
            b.box(r, "hanging_sign", (0.34, 0.05, 0.48),
                  (-px_post + 0.10, -py_post - 0.04, canopy_h - 0.62),
                  "timber")
            b.socket(r, "wares", (0, 0, 0.96), (0, 0, 1))

        for i in range(d["dock_count"]):
            bs = rng(config["seed"], f"{d['id']}:boat:{i}")
            r = b.root(f"JNX_{d['id']}_BOAT_{i:02d}", "boat", d["id"],
                       (cx - 48 + i * 32, cy - LAND_HALF_Y - 6.5, 0.30),
                       bs.uniform(-0.12, 0.12), task="tasks/assets/A047.md")
            _boat(b, r, bs, awning=i % 3 != 2)

        ls = rng(config["seed"], d["id"] + ":lanterns")
        spine = next(s for s in streets if s["kind"] == "spine")
        for i in range(12):
            frac = (i + 0.5) / 12.0
            pts = spine["points"]
            idx = min(int(frac * (len(pts) - 1)), len(pts) - 2)
            (x0, y0), (x1, y1) = pts[idx], pts[idx + 1]
            f = frac * (len(pts) - 1) - idx
            px, py = x0 + (x1 - x0) * f, y0 + (y1 - y0) * f
            tx, ty = x1 - x0, y1 - y0
            tl = math.hypot(tx, ty) or 1.0
            nx, ny = -ty / tl, tx / tl
            side = 1 if i % 2 else -1
            r = b.root(f"JNX_{d['id']}_LANTERN_{i:02d}", "lantern", d["id"],
                       (cx + px + nx * side * (spine["width"] / 2 + 0.9),
                        cy + py + ny * side * (spine["width"] / 2 + 0.9), z),
                       task="tasks/assets/A057.md")
            b.cylinder(r, "post", 0.07, 2.9, (0, 0, 0), "timber", 8)
            b.box(r, "arm", (0.6, 0.08, 0.08), (0.3, 0, 2.86), "iron")
            shade, sf = g.revolve([(0.02, 0), (0.26, 0.1), (0.29, 0.34),
                                   (0.22, 0.52), (0.04, 0.58)], sides=12)
            b.mesh(r, "paper", shade, sf, "paper", (0.55, 0, 2.28))
            b.box(r, "cap", (0.2, 0.2, 0.05), (0.55, 0, 2.88), "iron")
            b.socket(r, "light", (0.55, 0, 2.5), (0, 0, -1))

        ps = rng(config["seed"], d["id"] + ":plants")
        spots = _scatter(d["tree_count"], ps, streets, district_parcels, cx, cy,
                         outline=outline)
        bamboo_district = d["id"] in ("D03", "D11")
        for i, (px, py) in enumerate(spots):
            is_bamboo = bamboo_district and i % 3 != 2
            near_water = (abs(px) > LAND_HALF_X - 16 or abs(py) > LAND_HALF_Y - 16)
            h = ps.uniform(6.0, 10.5)
            r = b.root(f"JNX_{d['id']}_TREE_{i:03d}",
                       "bamboo" if is_bamboo else "tree", d["id"],
                       (cx + px, cy + py, z), ps.uniform(0, math.tau),
                       task="tasks/assets/A074.md" if is_bamboo else "tasks/assets/A073.md")
            if is_bamboo:
                _bamboo_clump(b, r, ps)
            elif near_water and i % 2 == 0:
                _willow(b, r, h, ps)
            else:
                _broadleaf(b, r, h, ps)
            b.socket(r, "ground", (0, 0, 0), (0, 0, 1))

        # Reed tufts soften the shoreline. They are pushed in until they stand
        # on the bank that was built; the nominal envelope reaches several
        # metres past it wherever the outline is bitten back.
        rs = rng(config["seed"], d["id"] + ":reeds")
        for i in range(14):
            edge = i % 4
            if edge == 0:
                px, py = rs.uniform(-70, 70), -LAND_HALF_Y + rs.uniform(0.4, 1.6)
            elif edge == 1:
                px, py = rs.uniform(-70, 70), LAND_HALF_Y - rs.uniform(0.4, 1.6)
            elif edge == 2:
                px, py = -LAND_HALF_X + rs.uniform(0.4, 1.6), rs.uniform(-66, 66)
            else:
                px, py = LAND_HALF_X - rs.uniform(0.4, 1.6), rs.uniform(-66, 66)
            clearance = g.polygon_clearance(outline, px, py)
            if clearance < 1.0:
                norm = math.hypot(px, py) or 1.0
                pull = 1.0 - clearance
                px -= px / norm * pull
                py -= py / norm * pull
            r = b.root(f"JNX_{d['id']}_REED_{i:02d}", "reeds", d["id"],
                       (cx + px, cy + py, z - 1.4), rs.uniform(0, math.tau),
                       task="tasks/assets/A080.md")
            rv, rf = g.reed_tuft(rs.randint(7, 13), rs.uniform(1.5, 2.4), rs)
            b.mesh(r, "tuft", rv, rf, "bamboo")
            # Flattened weed mat at ground level; hides the seam where the
            # reed stems pass through the bank and carries the moss shader.
            wv, wf = g.leaf_cluster(rs.uniform(0.7, 1.1), rs, lobes=3,
                                    squash=0.16)
            b.mesh(r, "weed_base", wv, wf, "leaf", (0, 0, 1.4))
            # Floating water lilies near the bank
            lv, lf = g.lily_pad_cluster(radius=0.42, count=5, stream=rs)
            b.mesh(r, "lily_pads", lv, lf, "leaf", (rs.uniform(-0.8, 0.8), rs.uniform(-0.8, 0.8), 1.41))

        # --- Canal-bank life: wells, laundry, benches, fishing nets, bollards ---
        # These populate the quay edge so the waterfront reads as lived-in rather
        # than a bare retaining wall. Placed along the south quay street with
        # deterministic spacing so they survive re-seeds.
        ls = rng(config["seed"], d["id"] + ":bank_life")
        quay_streets = [s for s in streets if s["kind"].startswith("quay")]
        life_idx = 0
        for qs in quay_streets:
            pts = qs["points"]
            if len(pts) < 2:
                continue
            total_len = sum(math.hypot(pts[k+1][0]-pts[k][0], pts[k+1][1]-pts[k][1])
                            for k in range(len(pts)-1))
            spacing = ls.uniform(12.0, 18.0)
            count = max(1, int(total_len / spacing))
            for j in range(count):
                frac = (j + 0.5) / count
                idx = min(int(frac * (len(pts)-1)), len(pts)-2)
                (x0, y0), (x1, y1) = pts[idx], pts[idx+1]
                f = frac * (len(pts)-1) - idx
                px = x0 + (x1 - x0) * f
                py = y0 + (y1 - y0) * f
                tx, ty = x1 - x0, y1 - y0
                tl = math.hypot(tx, ty) or 1.0
                nx, ny = -ty / tl, tx / tl
                rot = math.atan2(ty, tx)
                # Offset toward the water side of the quay
                qx = cx + px + nx * (qs["width"] / 2 + ls.uniform(0.8, 2.0))
                qy = cy + py + ny * (qs["width"] / 2 + ls.uniform(0.8, 2.0))
                # ...but keep it on the quay. The offset reaches past the bank
                # wherever the shoreline is bitten inland, which used to leave
                # benches and wells standing in the canal.
                lx, ly = qx - cx, qy - cy
                clear = g.polygon_clearance(outline, lx, ly)
                if clear < 1.2:
                    norm = math.hypot(lx, ly) or 1.0
                    pull = 1.2 - clear
                    lx -= lx / norm * pull
                    ly -= ly / norm * pull
                    qx, qy = cx + lx, cy + ly

                kind = life_idx % 5
                if kind == 0:
                    # Well with stone surround and bucket
                    r = b.root(f"JNX_{d['id']}_WELL_{life_idx:02d}", "well", d["id"],
                               (qx, qy, z), rot, task="tasks/wave2/A161.md")
                    b.cylinder(r, "well_wall", 0.55, 0.72, (0, 0, 0), "stone", 12)
                    b.cylinder(r, "well_rim", 0.62, 0.08, (0, 0, 0.72), "stone", 12)
                    b.cylinder(r, "well_void", 0.42, 0.10, (0, 0, 0.64), "stone", 12)
                    b.cylinder(r, "bucket", 0.14, 0.28, (0.7, 0, 0.14), "timber", 8)
                    b.box(r, "bucket_handle", (0.22, 0.02, 0.12), (0.7, 0, 0.36), "iron")
                    b.socket(r, "draw", (0, 0, 0.80), (0, 0, 1))
                elif kind == 1:
                    # Laundry pole with cloth strips
                    r = b.root(f"JNX_{d['id']}_LAUNDRY_{life_idx:02d}", "laundry", d["id"],
                               (qx, qy, z), rot, task="tasks/wave2/A162.md")
                    b.cylinder(r, "pole_a", 0.04, 2.6, (-1.2, 0, 0), "bamboo", 6)
                    b.cylinder(r, "pole_b", 0.04, 2.6, (1.2, 0, 0), "bamboo", 6)
                    b.box(r, "crossbar", (2.6, 0.04, 0.04), (0, 0, 2.58), "bamboo")
                    for ci in range(4):
                        cx_cloth = -0.9 + ci * 0.6
                        b.box(r, f"cloth_{ci}", (0.45, 0.02, ls.uniform(0.6, 1.1)),
                              (cx_cloth, ls.uniform(-0.06, 0.06), 2.58 - ls.uniform(0.3, 0.55)),
                              "cloth")
                elif kind == 2:
                    # Stone bench for resting
                    r = b.root(f"JNX_{d['id']}_BENCH_{life_idx:02d}", "bench", d["id"],
                               (qx, qy, z), rot + ls.uniform(-0.15, 0.15),
                               task="tasks/wave2/A163.md")
                    b.box(r, "seat", (1.4, 0.45, 0.08), (0, 0, 0.42), "stone")
                    b.box(r, "leg_a", (0.12, 0.40, 0.42), (-0.55, 0, 0.21), "stone")
                    b.box(r, "leg_b", (0.12, 0.40, 0.42), (0.55, 0, 0.21), "stone")
                elif kind == 3:
                    # Fishing net rack with draped net
                    r = b.root(f"JNX_{d['id']}_NETRACK_{life_idx:02d}", "net_rack", d["id"],
                               (qx, qy, z), rot, task="tasks/wave2/A132.md")
                    b.cylinder(r, "upright_a", 0.05, 2.2, (-0.9, 0, 0), "timber", 6)
                    b.cylinder(r, "upright_b", 0.05, 2.2, (0.9, 0, 0), "timber", 6)
                    b.box(r, "bar", (2.0, 0.05, 0.05), (0, 0, 2.18), "timber")
                    nv, nf = g.draped_net(1.6, 1.4, sag=0.35, nx=8, nz=6)
                    b.mesh(r, "net", nv, nf, "cloth", (0, 0.08, 0.9))
                else:
                    # Mooring bollard
                    r = b.root(f"JNX_{d['id']}_BOLLARD_{life_idx:02d}", "bollard", d["id"],
                               (qx, qy, z), rot, task="tasks/assets/A050.md")
                    b.cylinder(r, "post", 0.09, 0.65, (0, 0, 0), "stone", 8)
                    b.cylinder(r, "cap", 0.14, 0.06, (0, 0, 0.65), "stone", 8)
                    # Rope coil around the bollard
                    b.cylinder(r, "rope_coil", 0.13, 0.18, (0, 0, 0.32), "cloth", 10)
                life_idx += 1
