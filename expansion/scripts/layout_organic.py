"""Street-following parcel layout that replaces the layer-1 lattice.

Layer 1 (``layout.py``) placed buildings on a fixed 6x6 candidate lattice, which
reads as a subdivision plot rather than a canal town. This module keeps every
external promise of that layout -- instance id format, district centres, the
reserved landmark rectangle, the 6 m road endpoints named in
``docs/02_spatial_contract.md`` -- and changes only how parcels are chosen.

Contract preserved
    ids            JNX_<district>_BLD_<nnn>, JNX_LINK_<a>_<b>
    road endpoints west (-84,0) east (84,0) south (0,-80) north (0,80)
    landmark keep-out  x in [-34,34], y in [20,74]
    bridge spans   24 m east-west, 32 m north-south

What changes
    Streets are polylines with curvature, so rows of houses follow a bend.
    Buildings front the street they belong to and are packed shoulder to
    shoulder along it with irregular gaps, which is what produces the
    continuous eave line of a Jiangnan street.
    Quay frontage is treated as its own street class: narrow, deep plots with
    their gable to the water.
"""
from __future__ import annotations

import math

from kernel import rng

LANDMARK_KEEPOUT = (-34.0, 20.0, 34.0, 74.0)
ROAD_ENDS = {
    "west": ((-84.0, 0.0), (-1.0, 0.0)),
    "east": ((84.0, 0.0), (1.0, 0.0)),
    "south": ((0.0, -80.0), (0.0, -1.0)),
    "north": ((0.0, 80.0), (0.0, 1.0)),
}
# Land half-extents from the spatial contract (168 x 160 m of ground).
LAND_HALF_X = 84.0
LAND_HALF_Y = 80.0


def _rect_overlap(a, b, gap=0.0):
    return (a[0] < b[2] + gap and a[2] > b[0] - gap and
            a[1] < b[3] + gap and a[3] > b[1] - gap)


def _oriented_bounds(cx, cy, width, depth, angle):
    """Axis-aligned bounds of a rotated footprint, used for cheap rejection."""
    ca, sa = abs(math.cos(angle)), abs(math.sin(angle))
    hx = (width * ca + depth * sa) / 2.0
    hy = (width * sa + depth * ca) / 2.0
    return (cx - hx, cy - hy, cx + hx, cy + hy)


class Street:
    """A polyline with a frontage normal, sampled by arc length.

    ``side`` is +1 or -1 and selects which flank of the polyline receives
    buildings. Facing is derived from the tangent so a building on a curved
    street rotates with the curve instead of staying axis-aligned.
    """

    def __init__(self, points, width, kind="lane"):
        self.points = [(float(x), float(y)) for x, y in points]
        self.width = float(width)
        self.kind = kind
        self._cum = [0.0]
        for (x0, y0), (x1, y1) in zip(self.points, self.points[1:]):
            self._cum.append(self._cum[-1] + math.hypot(x1 - x0, y1 - y0))

    @property
    def length(self):
        return self._cum[-1]

    def sample(self, s):
        """Position and unit tangent at arc length ``s``."""
        s = min(max(s, 0.0), self.length)
        for i in range(len(self._cum) - 1):
            if s <= self._cum[i + 1] or i == len(self._cum) - 2:
                t0, t1 = self._cum[i], self._cum[i + 1]
                (x0, y0), (x1, y1) = self.points[i], self.points[i + 1]
                seg = max(t1 - t0, 1e-9)
                f = (s - t0) / seg
                tx, ty = (x1 - x0) / seg, (y1 - y0) / seg
                return (x0 + (x1 - x0) * f, y0 + (y1 - y0) * f), (tx, ty)
        return self.points[-1], (1.0, 0.0)

    def frontage(self, s, side, setback):
        """Centre of a plot whose front face looks back at the street.

        Returns the plot anchor and the rotation that points local -Y at the
        street, matching the "front faces local -Y" rule in the spatial
        contract.
        """
        (px, py), (tx, ty) = self.sample(s)
        nx, ny = -ty * side, tx * side
        ax = px + nx * (self.width / 2.0 + setback)
        ay = py + ny * (self.width / 2.0 + setback)
        # local -Y must point along (-nx,-ny): rotation of atan2 gives +Y, so add pi
        rot = math.atan2(ny, nx) + math.pi / 2.0
        return (ax, ay), rot


def _spine(stream):
    """Curved main street from the west road end to the east road end."""
    bend = stream.uniform(-16.0, 16.0)
    sag = stream.uniform(-9.0, 9.0)
    return Street([
        ROAD_ENDS["west"][0],
        (-46.0, bend * 0.35),
        (-12.0, bend),
        (16.0, sag),
        (50.0, sag * 0.4),
        ROAD_ENDS["east"][0],
    ], 6.0, "spine")


def _cross(stream):
    """Curved secondary street from the south road end to the north road end."""
    lean = stream.uniform(-13.0, 13.0)
    return Street([
        ROAD_ENDS["south"][0],
        (lean * 0.4, -52.0),
        (lean, -20.0),
        (lean * 0.6, 6.0),
        (0.0, 44.0),
        ROAD_ENDS["north"][0],
    ], 6.0, "cross")


def _quay_streets():
    """Water frontage lines on the south and the two flanks."""
    inset = 6.5
    return [
        Street([(-70.0, -LAND_HALF_Y + inset), (-24.0, -LAND_HALF_Y + inset + 1.2),
                (24.0, -LAND_HALF_Y + inset - 0.8), (70.0, -LAND_HALF_Y + inset + 1.0)],
               4.0, "quay_s"),
        Street([(-LAND_HALF_X + inset, -58.0), (-LAND_HALF_X + inset + 1.1, -18.0),
                (-LAND_HALF_X + inset - 0.6, 18.0)], 3.5, "quay_w"),
        Street([(LAND_HALF_X - inset, -58.0), (LAND_HALF_X - inset - 1.1, -18.0),
                (LAND_HALF_X - inset + 0.6, 18.0)], 3.5, "quay_e"),
    ]


def _alleys(stream):
    """Short back lanes that break the block into workable depths."""
    out = []
    for x in (-58.0, -30.0, 30.0, 58.0):
        jitter = stream.uniform(-4.0, 4.0)
        out.append(Street([(x + jitter, -66.0), (x + jitter * 0.5, -40.0),
                           (x + jitter, -16.0)], 2.6, "alley"))
    return out


def _street_plan(district_id, seed):
    stream = rng(seed, district_id + ":streets")
    plan = [_spine(stream), _cross(stream)]
    plan.extend(_quay_streets())
    plan.extend(_alleys(stream))
    return plan


def _family_dimensions(family, kind, stream):
    """Plot size by use. Quay plots are narrow and deep; halls are wide."""
    if kind.startswith("quay"):
        width = stream.choice((5.6, 6.4, 7.2, 8.0))
        depth = stream.choice((9.0, 10.5, 12.0))
    elif family == "warehouse":
        width = stream.choice((13.0, 15.5, 18.0))
        depth = stream.choice((10.0, 12.0, 14.0))
    elif family == "inn":
        width = stream.choice((12.0, 14.5, 17.0))
        depth = stream.choice((11.0, 13.0))
    elif family == "shop":
        width = stream.choice((6.0, 7.0, 8.2, 9.4))
        depth = stream.choice((9.5, 11.0, 12.5))
    elif family == "pavilion":
        width = stream.choice((6.0, 7.5, 9.0))
        depth = stream.choice((6.0, 7.5, 9.0))
    else:
        width = stream.choice((7.5, 9.0, 10.5, 12.0))
        depth = stream.choice((8.5, 10.0, 11.5))
    return width, depth


def _floors(family, kind, stream):
    if family in ("shop", "inn"):
        return 2
    if family == "pavilion":
        return 1
    if kind == "spine" and stream.random() < 0.45:
        return 2
    if kind.startswith("quay") and stream.random() < 0.3:
        return 2
    return 1


QUOTA_ORDER = ("quay_s", "spine", "cross", "quay_flank", "alley")

# Base split of a district's buildings across frontage classes.
_BASE_SHARE = {"quay_s": 0.30, "spine": 0.32, "cross": 0.16,
               "quay_flank": 0.12, "alley": 0.10}


def _quota_class(kind):
    return "quay_flank" if kind in ("quay_w", "quay_e") else kind


def _frontage_quota(district, want):
    """Split a district's building count across frontage classes.

    Shares come from the district manifest rather than hardcoded ids: dock_count
    stands for water activity and pulls plots onto the quay, a shop-heavy family
    list pulls them onto the spine. Largest remainder keeps the sum exact.
    """
    families = district["building_families"]
    commerce = sum(1 for f in families
                   if f in ("shop", "inn", "warehouse")) / len(families)
    water = min(district.get("dock_count", 0), 3) / 3.0
    share = dict(_BASE_SHARE)
    share["spine"] += 0.10 * commerce
    share["quay_s"] += 0.10 * water
    share["alley"] += 0.04 * (1.0 - commerce)

    total = sum(share.values())
    raw = {k: want * v / total for k, v in share.items()}
    out = {k: int(v) for k, v in raw.items()}
    rest = want - sum(out.values())
    for key, _ in sorted(raw.items(), key=lambda kv: kv[1] - int(kv[1]),
                         reverse=True):
        if rest <= 0:
            break
        out[key] += 1
        rest -= 1
    return out


def make_layout(config):
    """Deterministic organic layout with the same output schema as layer 1."""
    buildings, links = [], []
    seed = config["seed"]
    ground = config["ground_z"]
    ids = {d["id"] for d in config["districts"]}
    if len(ids) != len(config["districts"]):
        raise ValueError("duplicate district id")

    for d in config["districts"]:
        # Jitter district centres so the overview doesn't read as a checkerboard
        # of identical islands. The jitter is seeded per-district and capped at
        # ±18 m so road endpoints (±84/±80 from centre) still land in the
        # district's land envelope and bridges still span the gap.
        jitter_stream = rng(seed, d["id"] + ":center_jitter")
        cx = d["center"][0] + jitter_stream.uniform(-18.0, 18.0)
        cy = d["center"][1] + jitter_stream.uniform(-18.0, 18.0)
        want = d["building_count"]
        families = d["building_families"]
        streets = _street_plan(d["id"], seed)
        stream = rng(seed, d["id"] + ":parcels")
        placed = []
        index = 0
        quota = _frontage_quota(d, want)
        filled = {k: 0 for k in quota}

        by_class = {}
        for street in streets:
            by_class.setdefault(_quota_class(street.kind), []).append(street)

        def run(street, cap):
            """Pack both sides of a street, stopping after cap placements.

            Returns the number placed so the caller can carry unmet quota over
            to the next class instead of losing it.
            """
            nonlocal index
            klass = _quota_class(street.kind)
            done = 0
            for side in (-1, 1):
                if index >= want or done >= cap:
                    break
                # Walk the street, packing plots with irregular gaps.
                s = stream.uniform(6.0, 14.0)
                guard = 0
                while s < street.length - 6.0 and index < want and done < cap and guard < 400:
                    guard += 1
                    istream = rng(seed, f"{d['id']}:building:{index}:{street.kind}:{side}")
                    family = families[index % len(families)]
                    kind = street.kind
                    width, depth = _family_dimensions(family, kind, istream)
                    setback = istream.uniform(0.6, 2.4) if kind != "alley" else istream.uniform(0.4, 1.2)
                    (ax, ay), rot = street.frontage(s + width / 2.0, side, setback + depth / 2.0)
                    rot += istream.uniform(-0.05, 0.05)

                    bounds = _oriented_bounds(ax, ay, width + 1.8, depth + 1.8, rot)
                    if (abs(ax) + (bounds[2] - bounds[0]) / 2 > LAND_HALF_X - 4.0 or
                            abs(ay) + (bounds[3] - bounds[1]) / 2 > LAND_HALF_Y - 4.0):
                        s += width + istream.uniform(1.0, 3.0)
                        continue
                    if _rect_overlap(bounds, LANDMARK_KEEPOUT, 2.0):
                        s += width + istream.uniform(1.0, 3.0)
                        continue
                    if any(_rect_overlap(bounds, other, 0.0) for other in placed):
                        s += istream.uniform(1.5, 4.0)
                        continue

                    placed.append(bounds)
                    floors = _floors(family, kind, istream)
                    buildings.append(dict(
                        id=f"JNX_{d['id']}_BLD_{index:03d}",
                        district=d["id"], family=family,
                        location=[cx + ax, cy + ay, ground],
                        width=width, depth=depth, floors=floors,
                        rotation=rot, frontage=kind,
                        parcel=[cx + bounds[0], cy + bounds[1], cx + bounds[2], cy + bounds[3]],
                    ))
                    index += 1
                    done += 1
                    filled[klass] += 1
                    # Party-wall packing: shops touch, houses leave a drip gap.
                    gap = istream.uniform(0.15, 0.6) if family == "shop" else istream.uniform(0.8, 3.2)
                    s += width + gap
            return done

        # Pass one: each frontage class gets its own quota, so the waterside row
        # survives even in districts where the spine could absorb everything.
        carry = 0
        for klass in QUOTA_ORDER:
            cap = quota.get(klass, 0) + carry
            got = 0
            for street in by_class.get(klass, []):
                if got >= cap:
                    break
                got += run(street, cap - got)
            carry = cap - got

        # Pass two: relief sweep for whatever the quotas could not seat.
        if index < want:
            for klass in QUOTA_ORDER:
                for street in by_class.get(klass, []):
                    if index >= want:
                        break
                    run(street, want - index)

        if index < want:
            # Never silently drop buildings the district manifest promises.
            raise ValueError(f"{d['id']}: placed {index} of {want} parcels")

    for a in config["districts"]:
        ax, ay = a["center"]
        for b in config["districts"]:
            bx, by = b["center"]
            if (bx - ax, by - ay) not in ((180, 0), (0, 180)):
                continue
            horizontal = bx != ax
            links.append(dict(
                id=f"JNX_LINK_{a['id']}_{b['id']}", a=a["id"], b=b["id"],
                location=[(ax + bx) / 2, (ay + by) / 2, ground],
                span=24.0 if horizontal else 32.0, width=6.0,
                rotation=0.0 if horizontal else math.pi / 2,
            ))

    # Recompute jittered centres for the street world-space export so
    # street polylines match building placement, not the raw grid.
    _jittered = {}
    for d in config["districts"]:
        js = rng(seed, d["id"] + ":center_jitter")
        _jittered[d["id"]] = (d["center"][0] + js.uniform(-18.0, 18.0),
                              d["center"][1] + js.uniform(-18.0, 18.0))

    return dict(buildings=buildings, links=links,
                streets={d["id"]: [dict(kind=s.kind, width=s.width,
                                        points=[[_jittered[d["id"]][0] + x,
                                                 _jittered[d["id"]][1] + y]
                                                for x, y in s.points])
                                   for s in _street_plan(d["id"], seed)]
                         for d in config["districts"]},
                reserved_legacy=dict(district="D07", center=[90, 46], footprint=[60, 48],
                                     status="reserved_not_imported"))
