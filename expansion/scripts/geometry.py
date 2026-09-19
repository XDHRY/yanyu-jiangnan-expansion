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
