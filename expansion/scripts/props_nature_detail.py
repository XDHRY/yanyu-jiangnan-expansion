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


def _scatter(count, stream, streets, parcels, cx, cy, margin=5.0, tries=60):
    """Dart-throw positions that avoid roads, plots and the landmark block."""
    out = []
    while len(out) < count and tries > 0:
        tries -= 1
        for _ in range(count * 8):
            if len(out) >= count:
                break
            x = stream.uniform(-LAND_HALF_X + margin, LAND_HALF_X - margin)
            y = stream.uniform(-LAND_HALF_Y + margin, LAND_HALF_Y - margin)
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
    (tv, tf), spine = g.branch_skeleton(height * 0.55, stream, bends=4)
    b.mesh(r, "trunk", tv, tf, "timber")
    tipx, tipy, _ = spine[-1]
    for i in range(4):
        a = stream.uniform(0, math.tau)
        rad = stream.uniform(0.4, 1.7)
        z = height * stream.uniform(0.5, 0.78)
        cv, cf = g.leaf_cluster(stream.uniform(1.7, 2.8), stream, lobes=5)
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
    for d in config["districts"]:
        cx, cy = d["center"]
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
            b.box(r, "table", (2.9, 1.4, 0.12), (0, 0, 0.92), "timber")
            for xx in (-1.3, 1.3):
                for yy in (-0.6, 0.6):
                    b.cylinder(r, f"post_{xx}_{yy}", 0.06, 2.3, (xx, yy, 0), "timber", 6)
            av, af = g.arched_awning(3.3, 2.2, 0.45, ribs=5)
            b.mesh(r, "awning", av, af, "cloth", (0, 0, 2.3))
            b.box(r, "crate", (0.7, 0.6, 0.5), (stream.uniform(-1, 1), -0.9, 0.25), "timber")
            b.socket(r, "wares", (0, 0, 0.98), (0, 0, 1))

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
        spots = _scatter(d["tree_count"], ps, streets, district_parcels, cx, cy)
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

        # Reed tufts soften the shoreline where there is no quay stair.
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
