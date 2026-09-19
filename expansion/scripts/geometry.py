"""Second-layer geometry primitives: curved roofs, tile courses, joinery, foliage.

Implements the shapes the first-layer kernel deliberately left as tasks
(06_geometry_levels.md layer 2). Everything here is pure Python and returns
``(vertices, faces)`` tuples in the *local* space of the calling asset, so it
plugs into ``SceneBuilder.mesh()`` without touching the layer-1 contract.

Winding is counter-clockwise seen from outside, matching kernel.box().

The roof model follows three traits that read as Jiangnan at a glance:
  concave slope (举折) - steeper at the ridge, flattening toward the eave;
  corner lift (起翘)  - the eave line rises and flares at the gable ends;
  tile courses (瓦垄) - alternating pan/cover tiles running down the slope.
Bracket sets are expressed as stacked blocks, not carved dougong: the
art direction asks for restrained structural expression over invented detail.
"""
from __future__ import annotations

import math

TAU = math.tau


# --------------------------------------------------------------------------
# surface helpers
# --------------------------------------------------------------------------

def grid_faces(nu: int, nv: int, flip: bool = False):
    """Quad indices for a nu x nv vertex grid addressed as i*nv + j."""
    faces = []
    for i in range(nu - 1):
        for j in range(nv - 1):
            a = i * nv + j
            quad = (a, a + nv, a + nv + 1, a + 1)
            faces.append(quad[::-1] if flip else quad)
    return faces


def sweep(profile, path, close_profile=True, cap=False):
    """Sweep a 2-D profile [(y, z), ...] along a 3-D path [(x, y, z), ...].

    The profile's y runs along the path's local left, z along world up. Used
    for beams, ridge tiles, handrails and mooring ropes.
    """
    vertices, n = [], len(profile)
    for k, (px, py, pz) in enumerate(path):
        nxt = path[min(k + 1, len(path) - 1)]
        prv = path[max(k - 1, 0)]
        dx, dy = nxt[0] - prv[0], nxt[1] - prv[1]
        length = math.hypot(dx, dy) or 1.0
        tx, ty = dx / length, dy / length
        for oy, oz in profile:
            vertices.append((px - ty * oy, py + tx * oy, pz + oz))
    faces = []
    span = n if close_profile else n - 1
    for k in range(len(path) - 1):
        a, b = k * n, (k + 1) * n
        for j in range(span):
            jn = (j + 1) % n
            faces.append((a + j, b + j, b + jn, a + jn))
    if cap and n >= 3:
        faces.append(tuple(range(n - 1, -1, -1)))
        base = (len(path) - 1) * n
        faces.append(tuple(range(base, base + n)))
    return vertices, faces


def revolve(profile, sides=16, close=False):
    """Revolve a profile [(radius, z), ...] about local Z. Jars, drums, bases."""
    vertices = []
    for r, z in profile:
        for i in range(sides):
            a = TAU * i / sides
            vertices.append((r * math.cos(a), r * math.sin(a), z))
    faces = []
    for k in range(len(profile) - 1):
        a, b = k * sides, (k + 1) * sides
        for i in range(sides):
            j = (i + 1) % sides
            faces.append((a + i, b + i, b + j, a + j))
    if close:
        faces.append(tuple(reversed(range(sides))))
        base = (len(profile) - 1) * sides
        faces.append(tuple(range(base, base + sides)))
    return vertices, faces


# --------------------------------------------------------------------------
# roof
# --------------------------------------------------------------------------

def _slope_z(t: float, rise: float, curve: float = 2.2) -> float:
    """Height at cross-slope parameter t in [0, 1]; 0 at eave, 1 at ridge."""
    return rise * (0.34 * t + 0.66 * t ** curve)


def _corner_lift(s: float, lift: float) -> float:
    """Eave rise at along-ridge parameter s in [-1, 1]; concentrated at ends."""
    return lift * abs(s) ** 3.0


def _corner_flare(s: float, flare: float) -> float:
    """Extra outward reach of the eave near the gable ends (翼角)."""
    return flare * abs(s) ** 2.6


def roof_surface(width, depth, rise, overhang=0.9, lift=0.55, flare=0.35,
                 nu=9, nv=13, thickness=0.14):
    """A closed concave gable shell with lifted, flared eave corners.

    ``width`` runs along the ridge (X), ``depth`` across the slope (Y).
    Returns (vertices, faces) for a solid shell: outer surface, inner surface
    and a rim, so the roof reads correctly from inside a street as well.
    """
    half_w, half_d = width / 2, depth / 2

    def point(i, j, drop):
        s = -1.0 + 2.0 * i / (nu - 1)           # along ridge
        q = -1.0 + 2.0 * j / (nv - 1)           # across slope, 0 = ridge
        t = 1.0 - abs(q)                         # 1 at ridge, 0 at eave
        reach = half_d + overhang + _corner_flare(s, flare)
        x = s * (half_w + _corner_flare(s, flare) * 0.55)
        y = q * reach
        z = _slope_z(t, rise) + _corner_lift(s, lift) * (1.0 - t) ** 1.5
        return (x, y, z - drop)

    outer = [point(i, j, 0.0) for i in range(nu) for j in range(nv)]
    inner = [point(i, j, thickness) for i in range(nu) for j in range(nv)]
    vertices = outer + inner
    faces = grid_faces(nu, nv)
    offset = len(outer)
    faces += [tuple(reversed([v + offset for v in f])) for f in grid_faces(nu, nv)]
    # rim around all four borders
    def rim(a, b):
        faces.append((a, b, b + offset, a + offset))
    for i in range(nu - 1):
        rim(i * nv, (i + 1) * nv)
        rim((i + 1) * nv + nv - 1, i * nv + nv - 1)
    for j in range(nv - 1):
        rim((nu - 1) * nv + j, (nu - 1) * nv + j + 1)
        rim(j + 1, j)
    return vertices, faces


def roof_courses(width, depth, rise, overhang=0.9, lift=0.55, flare=0.35,
                 pitch=0.42, radius=0.075, segments=7):
    """Cover-tile courses (筒瓦) running down both slopes of a roof_surface.

    Returned as one merged mesh; a cheap half-round sweep per course keeps the
    face budget low enough to apply across every building in the world.
    """
    half_w, half_d = width / 2, depth / 2
    count = max(2, int(width / pitch))
    vertices, faces = [], []
    ring = [(radius * math.cos(a), radius * math.sin(a))
            for a in (TAU * k / 12 for k in range(7))]
    for c in range(count + 1):
        s = -1.0 + 2.0 * c / count
        lift_s = _corner_lift(s, lift)
        flare_s = _corner_flare(s, flare)
        x = s * (half_w + flare_s * 0.55)
        for sign in (-1, 1):
            path = []
            for k in range(segments):
                t = k / (segments - 1)
                reach = half_d + overhang + flare_s
                y = sign * (1.0 - t) * reach
                z = _slope_z(t, rise) + lift_s * (1.0 - t) ** 1.5 + radius * 0.5
                path.append((x, y, z))
            base = len(vertices)
            pv, pf = sweep([(o[0], o[1]) for o in ring], path, close_profile=True)
            vertices += pv
            faces += [tuple(v + base for v in f) for f in pf]
    return vertices, faces


def ridge_tile(width, rise, lift=0.55, flare=0.35, height=0.26, thickness=0.2):
    """Ridge cap with slightly raised ends, following the roof's corner lift."""
    nu = 11
    path = []
    for i in range(nu):
        s = -1.0 + 2.0 * i / (nu - 1)
        x = s * (width / 2 + _corner_flare(s, flare) * 0.55 + 0.1)
        path.append((x, 0.0, rise + _corner_lift(s, lift) * 0.45))
    profile = [(-thickness / 2, 0.0), (-thickness / 2, height * 0.62),
               (0.0, height), (thickness / 2, height * 0.62), (thickness / 2, 0.0)]
    return sweep(profile, path, close_profile=True)


def hip_roof_surface(width, depth, rise, overhang=0.95, lift=0.6, flare=0.4,
                     n=13, thickness=0.14):
    """Four-sided hip roof for halls, temples and tower tiers."""
    half_w, half_d = width / 2, depth / 2
    ridge = max(0.0, width - depth) / 2

    def point(u, v, drop):
        # u, v in [-1, 1] over the plan; radial falloff toward the ridge line
        ax = abs(u) * (half_w + overhang)
        ay = abs(v) * (half_d + overhang)
        edge = max(ax / (half_w + overhang), ay / (half_d + overhang)) or 1e-6
        t = 1.0 - edge
        corner = min(abs(u), abs(v))
        x = u * (half_w + overhang + _corner_flare(corner, flare))
        y = v * (half_d + overhang + _corner_flare(corner, flare))
        if ridge and abs(x) < ridge:
            pass
        z = _slope_z(t, rise) + _corner_lift(corner, lift) * (1.0 - t) ** 1.5
        return (x, y, z - drop)

    outer, inner = [], []
    for i in range(n):
        u = -1.0 + 2.0 * i / (n - 1)
        for j in range(n):
            v = -1.0 + 2.0 * j / (n - 1)
            outer.append(point(u, v, 0.0))
            inner.append(point(u, v, thickness))
    vertices = outer + inner
    faces = grid_faces(n, n)
    offset = len(outer)
    faces += [tuple(reversed([v + offset for v in f])) for f in grid_faces(n, n)]
    for i in range(n - 1):
        faces.append((i * n, (i + 1) * n, (i + 1) * n + offset, i * n + offset))
        faces.append(((i + 1) * n + n - 1, i * n + n - 1,
                      i * n + n - 1 + offset, (i + 1) * n + n - 1 + offset))
    for j in range(n - 1):
        faces.append(((n - 1) * n + j, (n - 1) * n + j + 1,
                      (n - 1) * n + j + 1 + offset, (n - 1) * n + j + offset))
        faces.append((j + 1, j, j + offset, j + 1 + offset))
    return vertices, faces


# --------------------------------------------------------------------------
# walls, openings, joinery
# --------------------------------------------------------------------------

def wall_with_opening(width, height, thickness, opening, sill=0.0):
    """A wall panel pierced by one rectangular opening.

    ``opening`` is (centre_x, width, height). Produces a single watertight
    mesh with a reveal, so door and window holes read with real depth instead
    of a face-mapped decal.
    """
    cx, ow, oh = opening
    x0, x1 = -width / 2, width / 2
    a0, a1 = cx - ow / 2, cx + ow / 2
    z0, z1 = sill, sill + oh
    t = thickness / 2
    panels = [
        (x0, a0, 0.0, height),      # left of opening
        (a1, x1, 0.0, height),      # right of opening
        (a0, a1, 0.0, z0),          # below opening
        (a0, a1, z1, height),       # above opening
    ]
    vertices, faces = [], []
    for px0, px1, pz0, pz1 in panels:
        if px1 - px0 <= 1e-6 or pz1 - pz0 <= 1e-6:
            continue
        base = len(vertices)
        vertices += [(px0, -t, pz0), (px1, -t, pz0), (px1, t, pz0), (px0, t, pz0),
                     (px0, -t, pz1), (px1, -t, pz1), (px1, t, pz1), (px0, t, pz1)]
        faces += [tuple(base + i for i in f) for f in
                  ((3, 2, 1, 0), (4, 5, 6, 7), (0, 1, 5, 4),
                   (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7))]
    return vertices, faces


def lattice_window(width, height, thickness=0.06, cols=4, rows=5, frame=0.09):
    """Muntin grid for a paper window (槛窗). Frame plus thin bars."""
    vertices, faces = [], []

    def bar(x0, x1, z0, z1, depth):
        base = len(vertices)
        vertices.extend([(x0, -depth, z0), (x1, -depth, z0), (x1, depth, z0), (x0, depth, z0),
                         (x0, -depth, z1), (x1, -depth, z1), (x1, depth, z1), (x0, depth, z1)])
        faces.extend(tuple(base + i for i in f) for f in
                     ((3, 2, 1, 0), (4, 5, 6, 7), (0, 1, 5, 4),
                      (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)))

    hw, hh, d = width / 2, height / 2, thickness / 2
    bar(-hw, hw, -hh, -hh + frame, d)
    bar(-hw, hw, hh - frame, hh, d)
    bar(-hw, -hw + frame, -hh, hh, d)
    bar(hw - frame, hw, -hh, hh, d)
    inner_w, inner_h = width - 2 * frame, height - 2 * frame
    for c in range(1, cols):
        x = -inner_w / 2 + inner_w * c / cols
        bar(x - 0.018, x + 0.018, -hh + frame, hh - frame, d * 0.6)
    for r in range(1, rows):
        z = -inner_h / 2 + inner_h * r / rows
        bar(-hw + frame, hw - frame, z - 0.018, z + 0.018, d * 0.6)
    return vertices, faces


def bracket_block(width=0.34, depth=0.5, height=0.17, tiers=3, spread=0.22):
    """Stacked bearing blocks under an eave: restrained dougong stand-in."""
    vertices, faces = [], []
    for k in range(tiers):
        w = width + k * spread
        d = depth + k * spread * 0.8
        z0 = k * height
        base = len(vertices)
        vertices.extend([(-w / 2, -d / 2, z0), (w / 2, -d / 2, z0),
                         (w / 2, d / 2, z0), (-w / 2, d / 2, z0),
                         (-w / 2, -d / 2, z0 + height), (w / 2, -d / 2, z0 + height),
                         (w / 2, d / 2, z0 + height), (-w / 2, d / 2, z0 + height)])
        faces.extend(tuple(base + i for i in f) for f in
                     ((3, 2, 1, 0), (4, 5, 6, 7), (0, 1, 5, 4),
                      (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)))
    return vertices, faces


def column_base(radius=0.26, height=0.18, sides=12):
    """Stone drum under a timber post (柱础)."""
    return revolve([(radius * 1.25, 0.0), (radius * 1.22, height * 0.35),
                    (radius * 1.02, height * 0.72), (radius * 0.96, height)],
                   sides=sides, close=True)


def horse_head_gable(depth, height, steps=3, thickness=0.26, rise=0.5):
    """Stepped gable wall (马头墙) rising above the roofline on a side wall."""
    vertices, faces = [], []
    half_d = depth / 2
    for k in range(steps):
        frac0, frac1 = k / steps, (k + 1) / steps
        y0 = -half_d + depth * frac0
        y1 = -half_d + depth * frac1
        peak = 1.0 - abs(frac0 + frac1 - 1.0)
        z1 = height + rise * peak
        base = len(vertices)
        t = thickness / 2
        vertices.extend([(-t, y0, 0.0), (t, y0, 0.0), (t, y1, 0.0), (-t, y1, 0.0),
                         (-t, y0, z1), (t, y0, z1), (t, y1, z1), (-t, y1, z1)])
        faces.extend(tuple(base + i for i in f) for f in
                     ((3, 2, 1, 0), (4, 5, 6, 7), (0, 1, 5, 4),
                      (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)))
    return vertices, faces


def railing(length, height=0.95, posts=6, rail_thickness=0.07):
    """Balustrade for galleries, bridges and boat decks."""
    vertices, faces = [], []

    def box(x0, x1, y0, y1, z0, z1):
        base = len(vertices)
        vertices.extend([(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                         (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)])
        faces.extend(tuple(base + i for i in f) for f in
                     ((3, 2, 1, 0), (4, 5, 6, 7), (0, 1, 5, 4),
                      (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)))

    t = rail_thickness / 2
    for i in range(posts + 1):
        x = -length / 2 + length * i / posts
        box(x - 0.05, x + 0.05, -0.05, 0.05, 0.0, height)
    box(-length / 2, length / 2, -t, t, height - rail_thickness, height)
    box(-length / 2, length / 2, -t * 0.7, t * 0.7, height * 0.45, height * 0.45 + 0.05)
    return vertices, faces


# --------------------------------------------------------------------------
# terrain and water edge
# --------------------------------------------------------------------------

def organic_slab(outline, top_z, bottom_z):
    """Extrude a closed 2-D outline into a solid land mass with vertical banks."""
    n = len(outline)
    vertices = [(x, y, top_z) for x, y in outline] + \
               [(x, y, bottom_z) for x, y in outline]
    faces = [tuple(reversed(range(n)))]
    faces.append(tuple(range(n, 2 * n)))
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, j + n, i + n))
    return vertices, faces


def bank_outline(half_x, half_y, wobble, stream, points=48):
    """Rectangleish parcel outline with an irregular, hand-cut water edge.

    ``wobble`` is a *fraction* of the half-extent that the edge may be bitten
    back by, not a distance in metres. It is clamped: above 0.5 the scale factor
    would go negative and fling points across the origin, which shows up as
    star-shaped spikes rather than a shoreline.
    """
    outline = []
    wobble = min(max(float(wobble), 0.0), 0.45)
    phase = [stream.uniform(0, TAU) for _ in range(4)]
    for k in range(points):
        a = TAU * k / points
        cx, cy = math.cos(a), math.sin(a)
        m = max(abs(cx), abs(cy)) or 1e-6
        # project onto the rectangle, then pull the edge in by a smooth noise
        x, y = cx / m * half_x, cy / m * half_y
        n = (math.sin(a * 3 + phase[0]) * 0.5 + math.sin(a * 5 + phase[1]) * 0.3 +
             math.sin(a * 8 + phase[2]) * 0.2)
        scale = 1.0 - wobble * (0.5 + 0.5 * n)
        outline.append((x * scale, y * scale))
    return outline


def _pin_release(angle, pinned, half_angle):
    """0 at a pinned angle, easing to 1 past twice ``half_angle``.

    Smoothstepped so a held stretch of bank meets a bitten one without a crease.
    """
    best = TAU
    for p in pinned:
        best = min(best, abs((angle - p + math.pi) % TAU - math.pi))
    if best <= half_angle:
        return 0.0
    t = min(1.0, (best - half_angle) / half_angle)
    return t * t * (3.0 - 2.0 * t)


def district_bank(half_x, half_y, stream, wobble=0.17, points=72,
                  pinned=(0.0, TAU / 4, TAU / 2, TAU * 3 / 4),
                  pin_half_angle=0.075):
    """Island outline that differs per district but keeps its bridge landings.

    ``bank_outline`` drives its edge with harmonics 3/5/8 at a 6% amplitude,
    which averages out: measured over the twelve districts it returns areas
    within 0.1% and half-widths within 1.4 m of each other, so the town reads as
    one rectangle tiled twelve times no matter how the buildings on it vary.
    Here the shape is carried mainly by the first two harmonics at a larger
    amplitude, so a bank can lose a dozen metres to one bay and keep its full
    extent at the next headland.

    The four ``pinned`` angles are the road ends of
    ``docs/02_spatial_contract.md``. A deck overlaps its bank by only
    ``BRIDGE_BEARING`` metres, so a bite there would leave the bridge ending over
    open water; the edge is held at full extent within ``pin_half_angle`` of each
    road end and eased back out over twice that.

    Callers must not build this per module. Two modules drawing their own bank
    for the same district is what left buildings hanging over water before;
    the authoritative outline per district is ``plan["land"]``.
    """
    outline = []
    wobble = min(max(float(wobble), 0.0), 0.45)
    phase = [stream.uniform(0, TAU) for _ in range(3)]
    gain = [stream.uniform(0.60, 1.0) for _ in range(3)]
    for k in range(points):
        a = TAU * k / points
        cx, cy = math.cos(a), math.sin(a)
        m = max(abs(cx), abs(cy)) or 1e-6
        # Project onto the planning rectangle, then bite the water edge inward.
        x, y = cx / m * half_x, cy / m * half_y
        n = (math.sin(a + phase[0]) * 0.62 * gain[0] +
             math.sin(a * 2 + phase[1]) * 0.44 * gain[1] +
             math.sin(a * 5 + phase[2]) * 0.16 * gain[2])
        n = max(-1.0, min(1.0, n))
        bite = wobble * (0.5 + 0.5 * n) * _pin_release(a, pinned, pin_half_angle)
        outline.append((x * (1.0 - bite), y * (1.0 - bite)))
    return outline


def point_in_polygon(outline, x, y):
    """Crossing-number test; the outline is treated as closed."""
    inside = False
    n = len(outline)
    for i in range(n):
        x0, y0 = outline[i]
        x1, y1 = outline[(i + 1) % n]
        if (y0 > y) != (y1 > y):
            if x < x0 + (y - y0) / (y1 - y0) * (x1 - x0):
                inside = not inside
    return inside


def polygon_clearance(outline, x, y):
    """Distance from a point to the outline: positive inside, negative outside.

    Used to keep footprints and paving on the land that was actually built,
    rather than on the nominal rectangle the land is cut from.
    """
    best = float("inf")
    n = len(outline)
    for i in range(n):
        x0, y0 = outline[i]
        x1, y1 = outline[(i + 1) % n]
        dx, dy = x1 - x0, y1 - y0
        seg = dx * dx + dy * dy
        t = 0.0 if seg < 1e-12 else max(0.0, min(1.0,
                                                 ((x - x0) * dx + (y - y0) * dy) / seg))
        best = min(best, math.hypot(x - (x0 + dx * t), y - (y0 + dy * t)))
    return best if point_in_polygon(outline, x, y) else -best


def polygon_ray_hit(outline, origin, direction):
    """Nearest forward intersection of a ray with the outline, or None.

    Lets a quay find the shoreline it is supposed to run along.
    """
    ox, oy = origin
    dx, dy = direction
    best = None
    n = len(outline)
    for i in range(n):
        ax, ay = outline[i]
        bx, by = outline[(i + 1) % n]
        ex, ey = bx - ax, by - ay
        den = dx * ey - dy * ex
        if abs(den) < 1e-12:
            continue
        wx, wy = ax - ox, ay - oy
        t = (wx * ey - wy * ex) / den
        u = (wx * dy - wy * dx) / den
        if t >= 0.0 and 0.0 <= u <= 1.0 and (best is None or t < best):
            best = t
    return best


def shore_revetment(outline, top_z, steps=4, tread=0.55):
    """Stone course stepping from the bank top down into the water.

    Follows ``outline`` so the revetment meets the water at the bank that was
    actually built. Each step is the outline pushed outward by one more tread,
    which reads as a quay stair from the canal and keeps the whole ring
    connected however irregular the shoreline is.
    """
    n = len(outline)
    verts = [(x, y, top_z) for x, y in outline]
    faces = []
    for k in range(steps):
        z = top_z * (1.0 - (k + 1) / steps) - (k + 1) * 0.02
        reach = (k + 1) * tread
        for x, y in outline:
            norm = math.hypot(x, y) or 1.0
            verts.append((x + x / norm * reach, y + y / norm * reach, z))
    # Connect the bank top to the first step, then step to step.
    for ring in range(steps):
        a = ring * n
        b = (ring + 1) * n
        for i in range(n):
            j = (i + 1) % n
            faces.append((a + i, a + j, b + j, b + i))
    return verts, faces


def stepped_quay(length, height, steps=4, tread=0.55):
    """Revetment that steps down to the water instead of a single flat wall."""
    vertices, faces = [], []
    for k in range(steps):
        z1 = height * (1.0 - k / steps)
        y0 = k * tread
        y1 = y0 + tread
        base = len(vertices)
        vertices.extend([(-length / 2, y0, 0.0), (length / 2, y0, 0.0),
                         (length / 2, y1, 0.0), (-length / 2, y1, 0.0),
                         (-length / 2, y0, z1), (length / 2, y0, z1),
                         (length / 2, y1, z1), (-length / 2, y1, z1)])
        faces.extend(tuple(base + i for i in f) for f in
                     ((3, 2, 1, 0), (4, 5, 6, 7), (0, 1, 5, 4),
                      (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)))
    return vertices, faces


# --------------------------------------------------------------------------
# vegetation
# --------------------------------------------------------------------------

def branch_skeleton(height, stream, taper=0.14, base_radius=0.26, bends=4, sides=7):
    """A leaning, tapering trunk; the spine also feeds crown placement."""
    path, radii = [], []
    x = y = 0.0
    lean_x = stream.uniform(-0.1, 0.1)
    lean_y = stream.uniform(-0.1, 0.1)
    for k in range(bends + 1):
        t = k / bends
        x += lean_x * height / bends + stream.uniform(-0.06, 0.06) * height / bends
        y += lean_y * height / bends + stream.uniform(-0.06, 0.06) * height / bends
        path.append((x, y, t * height))
        radii.append(base_radius * (1.0 - t) + taper * t)
    vertices, faces = [], []
    for k, ((px, py, pz), r) in enumerate(zip(path, radii)):
        for i in range(sides):
            a = TAU * i / sides
            vertices.append((px + r * math.cos(a), py + r * math.sin(a), pz))
    for k in range(len(path) - 1):
        a, b = k * sides, (k + 1) * sides
        for i in range(sides):
            j = (i + 1) % sides
            faces.append((a + i, b + i, b + j, a + j))
    faces.append(tuple(reversed(range(sides))))
    return (vertices, faces), path


def plum_blossom(size=0.085, angle=0.0):
    """Five-petal plum blossom (五瓣梅). Local +Z is the face normal.

    Thin overlapping ellipses, not a leafy blob: at canal distance this has to
    read as pale flowers against dark bark, which a clustered icosphere never
    does under moonlight.
    """
    vertices, faces = [], []
    for k in range(5):
        a = angle + TAU * k / 5
        ax, ay = math.cos(a), math.sin(a)
        sx, sy = -ay, ax
        idx = len(vertices)
        vertices.append((0.0, 0.0, 0.008 * size / 0.085))
        n = 8
        for j in range(n):
            t = TAU * j / n
            px = ax * size * (0.53 + 0.53 * math.cos(t)) + sx * size * 0.43 * math.sin(t)
            py = ay * size * (0.53 + 0.53 * math.cos(t)) + sy * size * 0.43 * math.sin(t)
            pz = size * 0.16 * (1.0 + math.cos(t))
            vertices.append((px, py, pz))
        for j in range(n):
            faces.append((idx, idx + 1 + j, idx + 1 + ((j + 1) % n)))
    # Raised pollen centre.
    c = len(vertices)
    r = size * 0.14
    vertices.extend([(0.0, 0.0, size * 0.20),
                     (r, 0.0, size * 0.12), (-r, 0.0, size * 0.12),
                     (0.0, r, size * 0.12), (0.0, -r, size * 0.12)])
    faces.extend([(c, c + 1, c + 3), (c, c + 3, c + 2),
                  (c, c + 2, c + 4), (c, c + 4, c + 1)])
    return vertices, faces


def leaf_cluster(radius, stream, lobes=5, sides=7, squash=0.72):
    """A crown built from overlapping blobs so the silhouette is not a cone."""
    vertices, faces = [], []
    for _ in range(lobes):
        cx = stream.uniform(-radius * 0.55, radius * 0.55)
        cy = stream.uniform(-radius * 0.55, radius * 0.55)
        cz = stream.uniform(-radius * 0.3, radius * 0.45)
        r = radius * stream.uniform(0.45, 0.72)
        rings = 4
        base = len(vertices)
        for ri in range(rings + 1):
            phi = math.pi * ri / rings
            rz = math.cos(phi) * r * squash + cz
            rr = math.sin(phi) * r
            for i in range(sides):
                a = TAU * i / sides
                vertices.append((cx + rr * math.cos(a), cy + rr * math.sin(a), rz))
        for ri in range(rings):
            a0, b0 = base + ri * sides, base + (ri + 1) * sides
            for i in range(sides):
                j = (i + 1) % sides
                faces.append((a0 + i, a0 + j, b0 + j, b0 + i))
    return vertices, faces


def willow_fronds(count, length, stream, radius=0.035, sides=4):
    """Drooping willow withies; the shape that sells a canal bank."""
    vertices, faces = [], []
    for _ in range(count):
        a = stream.uniform(0, TAU)
        reach = stream.uniform(0.5, 1.0)
        segs = 6
        path = []
        for k in range(segs):
            t = k / (segs - 1)
            r = reach * length * 0.5 * math.sin(t * 1.4)
            path.append((math.cos(a) * r, math.sin(a) * r, -t * t * length))
        ring = [(radius * math.cos(TAU * i / sides), radius * math.sin(TAU * i / sides))
                for i in range(sides)]
        base = len(vertices)
        pv, pf = sweep(ring, path, close_profile=True)
        vertices += pv
        faces += [tuple(v + base for v in f) for f in pf]
    return vertices, faces


def reed_tuft(count, height, stream, radius=0.022):
    """Bank reeds; cheap vertical accents that break a hard shoreline."""
    vertices, faces = [], []
    for _ in range(count):
        ox, oy = stream.uniform(-0.6, 0.6), stream.uniform(-0.6, 0.6)
        h = height * stream.uniform(0.6, 1.2)
        lean = stream.uniform(-0.25, 0.25)
        path = [(ox, oy, 0.0), (ox + lean * h * 0.3, oy, h * 0.55),
                (ox + lean * h, oy + lean * h * 0.4, h)]
        ring = [(radius * math.cos(TAU * i / 4), radius * math.sin(TAU * i / 4))
                for i in range(4)]
        base = len(vertices)
        pv, pf = sweep(ring, path, close_profile=True)
        vertices += pv
        faces += [tuple(v + base for v in f) for f in pf]
    return vertices, faces


# --------------------------------------------------------------------------
# vessels
# --------------------------------------------------------------------------

def boat_hull(length=7.2, beam=2.1, depth=0.85, sheer=0.32, sections=11, thickness=0.09):
    """Flat-bottomed river hull with a rockered keel and an open interior.

    Sampan-like: the bottom lifts toward bow and stern, the sides tumble in,
    and the gunwale sweeps up so the boat sits in water rather than on it.
    """
    vertices, faces = [], []
    outer, inner = [], []
    for k in range(sections):
        t = -1.0 + 2.0 * k / (sections - 1)
        x = t * length / 2
        pinch = 1.0 - abs(t) ** 2.1 * 0.82
        half_beam = beam / 2 * pinch
        keel = -depth * (1.0 - abs(t) ** 2.4) + sheer * abs(t) ** 2.4
        top = sheer * abs(t) ** 1.6
        outer.append([(x, -half_beam, top), (x, -half_beam * 0.92, keel + 0.06),
                      (x, 0.0, keel), (x, half_beam * 0.92, keel + 0.06),
                      (x, half_beam, top)])
        inner.append([(x, -half_beam + thickness, top),
                      (x, -half_beam * 0.92 + thickness, keel + 0.06 + thickness),
                      (x, 0.0, keel + thickness),
                      (x, half_beam * 0.92 - thickness, keel + 0.06 + thickness),
                      (x, half_beam - thickness, top)])
    n = 5
    for ring in outer:
        vertices.extend(ring)
    offset = len(vertices)
    for ring in inner:
        vertices.extend(ring)
    for k in range(sections - 1):
        a, b = k * n, (k + 1) * n
        for j in range(n - 1):
            faces.append((a + j, a + j + 1, b + j + 1, b + j))
            faces.append((offset + a + j, offset + b + j,
                          offset + b + j + 1, offset + a + j + 1))
    for k in range(sections - 1):
        a, b = k * n, (k + 1) * n
        faces.append((a, b, offset + b, offset + a))
        faces.append((a + n - 1, offset + a + n - 1, offset + b + n - 1, b + n - 1))
    for j in range(n - 1):
        faces.append((j, offset + j, offset + j + 1, j + 1))
        last = (sections - 1) * n
        faces.append((last + j + 1, offset + last + j + 1, offset + last + j, last + j))
    return vertices, faces


def arched_awning(length=3.4, beam=1.9, rise=0.62, ribs=6, thickness=0.05):
    """Half-barrel bamboo mat cabin (乌篷) over a boat's midships."""
    n = 9
    outer, inner = [], []
    for k in range(ribs):
        x = -length / 2 + length * k / (ribs - 1)
        for j in range(n):
            a = math.pi * j / (n - 1)
            outer.append((x, math.cos(a) * beam / 2, math.sin(a) * rise))
            inner.append((x, math.cos(a) * (beam / 2 - thickness),
                          math.sin(a) * (rise - thickness)))
    vertices = outer + inner
    faces = grid_faces(ribs, n)
    offset = len(outer)
    faces += [tuple(reversed([v + offset for v in f])) for f in grid_faces(ribs, n)]
    for j in range(n - 1):
        faces.append((j + 1, j, j + offset, j + 1 + offset))
        last = (ribs - 1) * n
        faces.append((last + j, last + j + 1, last + j + 1 + offset, last + j + offset))
    return vertices, faces


def rope_catenary(start, end, sag=0.5, segments=10, radius=0.025, sides=4):
    """Mooring line between two local points; sags under its own weight."""
    path = []
    for k in range(segments + 1):
        t = k / segments
        x = start[0] + (end[0] - start[0]) * t
        y = start[1] + (end[1] - start[1]) * t
        z = start[2] + (end[2] - start[2]) * t - sag * math.sin(math.pi * t)
        path.append((x, y, z))
    ring = [(radius * math.cos(TAU * i / sides), radius * math.sin(TAU * i / sides))
            for i in range(sides)]
    return sweep(ring, path, close_profile=True)


# --------------------------------------------------------------------------
# bridge
# --------------------------------------------------------------------------

def arch_bridge_body(span, width, rise=2.7, thickness=0.55, sections=21,
                     arch_segments=12):
    """Stone arch bridge: curved deck over a real voussoir opening."""
    vertices, faces = [], []

    def deck_z(t):
        return rise * math.sin(math.pi * t) ** 0.85

    # deck slab
    outer, inner = [], []
    for k in range(sections):
        t = k / (sections - 1)
        x = -span / 2 + span * t
        z = deck_z(t)
        outer.append((x, -width / 2, z))
        outer.append((x, width / 2, z))
        inner.append((x, -width / 2, z - thickness))
        inner.append((x, width / 2, z - thickness))
    base = len(vertices)
    vertices += outer + inner
    off = len(outer)
    for k in range(sections - 1):
        a, b = base + k * 2, base + (k + 1) * 2
        faces.append((a, a + 1, b + 1, b))
        faces.append((a + off, b + off, b + 1 + off, a + 1 + off))
        faces.append((a, b, b + off, a + off))
        faces.append((a + 1, a + 1 + off, b + 1 + off, b + 1))
    faces.append((base, base + off, base + 1 + off, base + 1))
    last = base + (sections - 1) * 2
    faces.append((last + 1, last + 1 + off, last + off, last))

    # spandrel walls with an arched opening on each face
    for side in (-1, 1):
        y = side * width / 2
        wall = []
        for k in range(arch_segments + 1):
            t = k / arch_segments
            x = -span / 2 + span * t
            # underside of the arch: a raised semicircle clearing the water
            clearance = max(0.0, rise * 0.92 * math.sin(math.pi * t) ** 0.6)
            wall.append((x, y, clearance, deck_z(t) - thickness))
        b0 = len(vertices)
        for x, yy, z_low, z_high in wall:
            vertices.append((x, yy, z_low))
            vertices.append((x, yy, z_high))
        for k in range(arch_segments):
            a, b = b0 + k * 2, b0 + (k + 1) * 2
            quad = (a, a + 1, b + 1, b)
            faces.append(quad if side > 0 else quad[::-1])
    return vertices, faces


def scholar_rock_sculpt(height, radius, stream, segments=22, rings=18):
    """Sculpted scholar rock (太湖石) with waist pinch, surface furrows and erosion hollows."""
    verts = []
    faces = []
    p1 = stream.uniform(0, math.tau)
    p2 = stream.uniform(0, math.tau)
    for ri in range(rings + 1):
        v_fac = ri / rings
        z = v_fac * height
        phi = math.pi * v_fac
        # waist pinch at mid-height (瘦)
        waist = 0.62 + 0.45 * math.sin(phi)
        for si in range(segments):
            theta = math.tau * si / segments
            # bumps and erosion furrows (皱与透)
            distort = (1.0 + 0.26 * math.sin(theta * 3 + v_fac * 4.0 + p1)
                           + 0.18 * math.cos(theta * 5 - v_fac * 5.5 + p2))
            r = radius * waist * distort
            x = r * math.cos(theta) + 0.18 * math.sin(v_fac * math.pi)
            y = r * math.sin(theta) * 0.72
            verts.append((x, y, z))
    for ri in range(rings):
        for si in range(segments):
            si_next = (si + 1) % segments
            a = ri * segments + si
            b = ri * segments + si_next
            c = (ri + 1) * segments + si_next
            d = (ri + 1) * segments + si
            faces.append((a, b, c, d))
    # Cap bottom and top
    faces.append(tuple(reversed(range(segments))))
    top_base = rings * segments
    faces.append(tuple(range(top_base, top_base + segments)))
    return verts, faces


def eaves_chime(drop=0.42, bell_r=0.075, bell_h=0.13):
    """Bronze wind chime (铁马铜铎) hanging under an upturned eave corner."""
    verts = []
    faces = []
    # cord
    verts.extend([(-0.01, 0, 0), (0.01, 0, 0), (0.01, 0, -drop * 0.6), (-0.01, 0, -drop * 0.6)])
    faces.append((0, 1, 2, 3))
    # bell body (revolve)
    bz = -drop * 0.6
    n = 10
    profile = [(0.02, bz), (bell_r * 0.6, bz - bell_h * 0.3), (bell_r, bz - bell_h), (bell_r * 1.15, bz - bell_h * 1.15)]
    base_idx = len(verts)
    for p_r, p_z in profile:
        for i in range(n):
            a = math.tau * i / n
            verts.append((p_r * math.cos(a), p_r * math.sin(a), p_z))
    for k in range(len(profile) - 1):
        a = base_idx + k * n
        b = base_idx + (k + 1) * n
        for i in range(n):
            j = (i + 1) % n
            faces.append((a + i, b + i, b + j, a + j))
    # wind leaf plate
    lz = bz - bell_h * 1.15
    leaf_idx = len(verts)
    verts.extend([(0, -0.035, lz), (0, 0.035, lz), (0, 0.045, lz - 0.20), (0, -0.045, lz - 0.20)])
    faces.append((leaf_idx, leaf_idx + 1, leaf_idx + 2, leaf_idx + 3))
    return verts, faces


def boat_oar(length=3.4, blade_len=1.2, blade_w=0.22):
    """Traditional sculling oar (摇橹) mounted on the boat stern."""
    verts = []
    faces = []
    shaft_l = length - blade_len
    r = 0.035
    n = 6
    for z_pos in (0, shaft_l):
        for i in range(n):
            a = math.tau * i / n
            verts.append((r * math.cos(a), r * math.sin(a), z_pos))
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, j + n, i + n))
    base = len(verts)
    w = blade_w / 2
    t = 0.015
    for z_pos in (shaft_l, length):
        verts.extend([(-w, -t, z_pos), (w, -t, z_pos), (w, t, z_pos), (-w, t, z_pos)])
    faces.extend([
        (base, base + 1, base + 5, base + 4),
        (base + 1, base + 2, base + 6, base + 5),
        (base + 2, base + 3, base + 7, base + 6),
        (base + 3, base, base + 4, base + 7),
        (base + 4, base + 5, base + 6, base + 7),
    ])
    return verts, faces


def draped_net(width=2.0, height=1.6, sag=0.4, nx=6, nz=5):
    """A rectangular fishing net draped between two top corners.

    The net hangs from the top edge and sags in the middle, giving a catenary
    look. Returns (verts, faces) as a single-sided quad grid — light enough
    for background props.
    """
    verts = []
    for iz in range(nz):
        fz = iz / max(nz - 1, 1)
        z = height * (1.0 - fz)
        droop = sag * math.sin(math.pi * fz)
        for ix in range(nx):
            fx = ix / max(nx - 1, 1)
            belly = 4.0 * fx * (1.0 - fx)
            x = -width / 2 + width * fx
            y = -droop * belly
            verts.append((x, y, z))
    faces = grid_faces(nz, nx)
    return verts, faces


def lily_pad_cluster(radius=0.45, count=6, stream=None):
    """Floating water lily pads (浮萍与睡莲) softening the stone water edges."""
    import random
    s = stream or random.Random(1)
    verts = []
    faces = []
    for k in range(count):
        ox = s.uniform(-0.6, 0.6)
        oy = s.uniform(-0.6, 0.6)
        r = radius * s.uniform(0.65, 1.15)
        base = len(verts)
        n = 10
        verts.append((ox, oy, 0.0))
        for i in range(n):
            a = 0.25 + (math.tau - 0.5) * i / (n - 1)
            verts.append((ox + r * math.cos(a), oy + r * math.sin(a), 0.0))
        for i in range(1, n):
            faces.append((base, base + i, base + i + 1))
    return verts, faces


def _box_mesh(vertices, faces, x0, x1, y0, y1, z0, z1):
    """Append an axis-aligned box; winding matches kernel.box()."""
    base = len(vertices)
    vertices.extend([
        (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
        (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1),
    ])
    faces.extend(tuple(base + i for i in f) for f in
                 ((3, 2, 1, 0), (4, 5, 6, 7), (0, 1, 5, 4),
                  (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)))


def segmented_arch_voussoir(rad, width, brick_depth=0.22, n_bricks=40, mortar=0.016):
    """Circular brick ring: discrete voussoirs with recessed mortar gaps.

    Local origin at the aperture centre; the ring lives in XZ, Y is the wall
    thickness. Each wedge is inset on the radial faces so the joint reads at
    street distance instead of a smooth torus.
    """
    vertices, faces = [], []
    half = width / 2
    mid_r = rad + brick_depth * 0.5
    sector = TAU / n_bricks
    mortar_ang = mortar / max(mid_r, 1e-4)
    for i in range(n_bricks):
        a0 = i * sector + mortar_ang * 0.5
        a1 = (i + 1) * sector - mortar_ang * 0.5
        if a1 <= a0:
            continue
        # Slight weathering so the ring is not a perfect extrusion.
        wear = 0.01 * math.sin(i * 2.17 + 0.4)
        r0 = rad + 0.004 * abs(math.sin(i * 1.7))
        r1 = rad + brick_depth + wear
        y0, y1 = -half, half
        k = len(vertices)

        def pt(r, a, y):
            return (r * math.cos(a), y, r * math.sin(a))

        vertices.extend([
            pt(r0, a0, y0), pt(r0, a1, y0), pt(r1, a1, y0), pt(r1, a0, y0),
            pt(r0, a0, y1), pt(r0, a1, y1), pt(r1, a1, y1), pt(r1, a0, y1),
        ])
        faces.extend(tuple(k + i for i in f) for f in (
            (0, 1, 2, 3),      # -Y face
            (4, 7, 6, 5),      # +Y face
            (0, 4, 5, 1),      # inner reveal
            (3, 2, 6, 7),      # outer arris
            (1, 5, 6, 2),      # joint face a1
            (0, 3, 7, 4),      # joint face a0
        ))
    return vertices, faces


def ridge_beast(scale=1.0):
    """Glazed chiwen / 鸱吻 sitting on a ridge end.

    Local +X faces the ridge tip, +Z is up, z=0 is the tile bed. Blocky on
    purpose: the silhouette has to read against mist at canal distance.
    """
    s = scale
    vertices, faces = [], []
    _box_mesh(vertices, faces, -0.24 * s, 0.20 * s, -0.11 * s, 0.11 * s, 0.00, 0.22 * s)
    _box_mesh(vertices, faces, -0.16 * s, 0.26 * s, -0.07 * s, 0.07 * s, 0.16 * s, 0.34 * s)
    _box_mesh(vertices, faces, 0.14 * s, 0.40 * s, -0.08 * s, 0.08 * s, 0.20 * s, 0.46 * s)
    _box_mesh(vertices, faces, 0.32 * s, 0.56 * s, -0.10 * s, 0.10 * s, 0.34 * s, 0.56 * s)
    _box_mesh(vertices, faces, 0.48 * s, 0.66 * s, -0.05 * s, 0.05 * s, 0.44 * s, 0.54 * s)
    _box_mesh(vertices, faces, 0.46 * s, 0.62 * s, -0.05 * s, 0.05 * s, 0.30 * s, 0.40 * s)
    _box_mesh(vertices, faces, -0.06 * s, 0.30 * s, -0.018 * s, 0.018 * s, 0.30 * s, 0.52 * s)
    _box_mesh(vertices, faces, -0.42 * s, -0.18 * s, -0.045 * s, 0.045 * s, 0.06 * s, 0.24 * s)
    return vertices, faces


def hanging_fascia(width, height=0.52, thickness=0.055, cols=5):
    """Carved hanging fascia (挂落) under an eave beam.

    Origin at the top centre; the panel hangs in -Z. Thin in Y so it sits
    against the lintel without colliding with the walkway.
    """
    vertices, faces = [], []
    hw, d = width / 2, thickness / 2
    frame = 0.045
    _box_mesh(vertices, faces, -hw, hw, -d, d, -0.055, 0.0)
    _box_mesh(vertices, faces, -hw, -hw + frame, -d, d, -height, 0.0)
    _box_mesh(vertices, faces, hw - frame, hw, -d, d, -height, 0.0)
    _box_mesh(vertices, faces, -hw + 0.03, hw - 0.03, -d, d, -height, -height + 0.05)
    inner_w = width - 2 * frame
    for c in range(1, cols):
        x = -hw + frame + inner_w * c / cols
        _box_mesh(vertices, faces, x - 0.012, x + 0.012, -d * 0.7, d * 0.7,
                  -height + 0.05, -0.055)
    rows = 2
    for r in range(1, rows + 1):
        z = -height + 0.05 + (height - 0.10) * r / (rows + 1)
        _box_mesh(vertices, faces, -hw + frame, hw - frame, -d * 0.7, d * 0.7,
                  z - 0.012, z + 0.012)
    for x in (-hw + 0.10, 0.0, hw - 0.10):
        _box_mesh(vertices, faces, x - 0.028, x + 0.028, -d, d,
                  -height - 0.14, -height)
        _box_mesh(vertices, faces, x - 0.018, x + 0.018, -d * 0.8, d * 0.8,
                  -height - 0.22, -height - 0.14)
    return vertices, faces


def beauty_lean(length, height=0.74, curve=0.20, posts=6):
    """美人靠 / 吴王靠: outward-curving gallery bench.

    Origin at the deck; the seat runs along X and the backrest bulges toward
    -Y (the street / water side).
    """
    vertices, faces = [], []
    n = max(3, posts + 1)
    _box_mesh(vertices, faces, -length / 2, length / 2, -0.20, 0.16, 0.34, 0.42)
    for i in range(n):
        x = -length / 2 + length * i / (n - 1)
        _box_mesh(vertices, faces, x - 0.04, x + 0.04, -0.14, 0.12, 0.0, 0.34)
        path = [
            (x, 0.10, 0.42),
            (x, 0.10 - curve * 0.55, 0.42 + (height - 0.42) * 0.55),
            (x, 0.10 - curve, height),
        ]
        pv, pf = sweep([(0.028, 0.0), (0.0, 0.028), (-0.028, 0.0), (0.0, -0.028)],
                       path, close_profile=True)
        k = len(vertices)
        vertices.extend(pv)
        faces.extend(tuple(i + k for i in face) for face in pf)
    rail = [( -length / 2 + length * i / (n - 1), 0.10 - curve, height) for i in range(n)]
    rv, rf = sweep([(0.03, 0.0), (0.0, 0.03), (-0.03, 0.0), (0.0, -0.03)],
                   rail, close_profile=True)
    k = len(vertices)
    vertices.extend(rv)
    faces.extend(tuple(i + k for i in face) for face in rf)
    return vertices, faces
