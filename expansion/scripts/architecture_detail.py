"""Layer-2 building geometry: real bays, openings, tiled roofs and gables.

Replaces the shared hall() topology of layer 1 while keeping every external
contract from docs/05_socket_pairs.md: asset ids, entry/sign/roof_ridge sockets
and the parcel rectangle are unchanged, so district assembly still resolves.

Vertical datum inside a building, per docs/02_spatial_contract.md:
  local z=0   parcel datum (ground_z in world)
  +0.00..0.52 stone plinth (台基)
  +0.52       finished floor level (FFL)
  +0.52+h     eave springing, where h is storey height * floors
Nothing below the plinth is modelled; the terrain owns that.
"""
from __future__ import annotations

import math

import geometry as g
from kernel import rng

STOREY = 3.25
PLINTH = 0.52
FFL = PLINTH
BAY = 3.2


def _bays(width: float) -> int:
    """Odd bay count so a centred door lands on a bay, per 02_spatial_contract."""
    n = max(1, int(round(width / BAY)))
    return n if n % 2 else n + 1


def _plinth(b, root, prefix, width, depth, stream):
    """Stone base with a chamfered top course; slight settle on one corner."""
    b.box(root, prefix + "plinth", (width + 0.72, depth + 0.72, PLINTH - 0.12),
          (0, 0, (PLINTH - 0.12) / 2), "stone")
    b.box(root, prefix + "plinth_cap", (width + 0.52, depth + 0.52, 0.12),
          (0, 0, PLINTH - 0.06), "stone")
    # Damp course reads as a different material band at the wall foot.
    b.box(root, prefix + "damp_course", (width + 0.06, depth + 0.06, 0.34),
          (0, 0, FFL + 0.17), "stone")


def _floor_plate(b, root, prefix, width, depth, z, material="timber"):
    b.box(root, prefix + "floor", (width - 0.18, depth - 0.18, 0.14),
          (0, 0, z + 0.07), material)


def _post_row(b, root, prefix, width, depth, height, bays, stream, side):
    """Timber post row with stone bases; the frame reads as structure."""
    y = side * (depth / 2 - 0.16)
    for i in range(bays + 1):
        x = -width / 2 + i * width / bays
        verts, faces = g.column_base(0.25, 0.17)
        b.mesh(root, prefix + f"base_{side}_{i}", verts, faces, "stone", (x, y, FFL))
        lean = stream.uniform(-0.012, 0.012)
        b.cylinder(root, prefix + f"post_{side}_{i}", 0.155, height,
                   (x + lean, y, FFL + 0.17), "timber", 10, 0.135)
    b.box(root, prefix + f"beam_{side}", (width + 0.3, 0.24, 0.32),
          (0, y, FFL + 0.17 + height + 0.16), "timber")
    # Bracket blocks only on the street side; back elevations stay plain.
    if side < 0:
        for i in range(bays + 1):
            x = -width / 2 + i * width / bays
            verts, faces = g.bracket_block(0.32, 0.46, 0.16, 3, 0.2)
            b.mesh(root, prefix + f"bracket_{i}", verts, faces, "timber",
                   (x, y - 0.08, FFL + 0.17 + height))


def _shopfront(b, root, prefix, width, depth, height, bays, stream):
    """Open timber shopfront: removable boards, counter, no plaster wall."""
    y = -depth / 2 + 0.12
    board_h = height - 2.5
    for i in range(bays):
        x = -width / 2 + (i + 0.5) * width / bays
        w = width / bays - 0.18
        if i == bays // 2:
            continue  # the centre bay is the doorway
        b.box(root, prefix + f"board_{i}", (w, 0.08, board_h),
              (x, y, FFL + 2.5 + board_h / 2), "timber")
        b.box(root, prefix + f"counter_{i}", (w, 0.55, 0.14),
              (x, y - 0.2, FFL + 0.92), "timber")
        verts, faces = g.lattice_window(w, 1.5, 0.05, 4, 3)
        b.mesh(root, prefix + f"grille_{i}", verts, faces, "timber",
               (x, y - 0.03, FFL + 1.0))


def _plaster_walls(b, root, prefix, width, depth, height, bays, stream, family):
    """Plaster envelope with a real door void and upper lattice windows."""
    door_w = 1.5 if family == "house" else 2.0
    door_h = 2.25
    verts, faces = g.wall_with_opening(width, height, 0.24,
                                       (0.0, door_w, door_h))
    b.mesh(root, prefix + "wall_front", verts, faces, "plaster",
           (0, -depth / 2 + 0.12, FFL))
    b.box(root, prefix + "door_frame_head", (door_w + 0.34, 0.32, 0.22),
          (0, -depth / 2 + 0.12, FFL + door_h + 0.11), "timber")
    for s in (-1, 1):
        b.box(root, prefix + f"door_jamb_{s}", (0.16, 0.3, door_h),
              (s * (door_w / 2 + 0.08), -depth / 2 + 0.12, FFL + door_h / 2), "timber")
    b.box(root, prefix + "threshold", (door_w + 0.3, 0.42, 0.1),
          (0, -depth / 2 - 0.06, FFL + 0.05), "stone")
    # Ground-floor windows flank the door; upper floor gets a lattice band.
    if bays >= 3:
        for i in (0, bays - 1):
            x = -width / 2 + (i + 0.5) * width / bays
            w = min(1.5, width / bays - 0.5)
            verts, faces = g.lattice_window(w, 1.25, 0.06, 3, 3)
            b.mesh(root, prefix + f"window_{i}", verts, faces, "timber",
                   (x, -depth / 2 + 0.02, FFL + 1.15))
            b.box(root, prefix + f"window_sill_{i}", (w + 0.24, 0.2, 0.1),
                  (x, -depth / 2 + 0.06, FFL + 1.1), "stone")
    b.box(root, prefix + "wall_back", (width, 0.24, height),
          (0, depth / 2 - 0.12, FFL + height / 2), "plaster")
    for s in (-1, 1):
        b.box(root, prefix + f"wall_side_{s}", (0.24, depth - 0.48, height),
              (s * (width / 2 - 0.12), 0, FFL + height / 2), "plaster")


def _upper_gallery(b, root, prefix, width, depth, stream):
    """Second-storey balcony: the motif that makes a canal street read."""
    z = FFL + STOREY
    b.box(root, prefix + "gallery_deck", (width + 0.7, 1.15, 0.12),
          (0, -depth / 2 - 0.5, z + 0.06), "timber")
    verts, faces = g.railing(width + 0.7, 0.92, max(4, int(width / 1.3)))
    b.mesh(root, prefix + "gallery_rail", verts, faces, "timber",
           (0, -depth / 2 - 1.05, z + 0.12))
    # 美人靠: the outward-curving bench that makes a canal gallery read as lived-in.
    bv, bf = g.beauty_lean(width + 0.4, height=0.78, curve=0.18,
                           posts=max(4, int(width / 1.5)))
    b.mesh(root, prefix + "gallery_lean", bv, bf, "timber",
           (0, -depth / 2 - 0.95, z + 0.12))
    for i in range(3):
        x = -width / 2 + i * width / 2
        b.cylinder(root, prefix + f"gallery_brace_{i}", 0.07, 0.95,
                   (x, -depth / 2 - 0.45, z - 0.9), "timber", 6)
    verts, faces = g.lattice_window(min(2.4, width - 1.2), 1.6, 0.06, 5, 4)
    b.mesh(root, prefix + "gallery_window", verts, faces, "timber",
           (0, -depth / 2 + 0.06, z + 0.55))


def _roof(b, root, prefix, width, depth, height, stream, hip=False, gable=True):
    """Curved tiled roof plus ridge; optional horse-head gable walls."""
    z = FFL + height + 0.46
    rise = depth * 0.30 + 0.35
    over = 0.95
    lift = 0.5 + stream.uniform(-0.06, 0.1)
    flare = 0.34
    if hip:
        verts, faces = g.hip_roof_surface(width, depth, rise, over, lift, flare)
    else:
        verts, faces = g.roof_surface(width, depth, rise, over, lift, flare)
    b.mesh(root, prefix + "roof", verts, faces, "tile", (0, 0, z))
    verts, faces = g.roof_courses(width, depth, rise, over, lift, flare)
    b.mesh(root, prefix + "roof_tiles", verts, faces, "tile", (0, 0, z))
    verts, faces = g.ridge_tile(width, rise, lift, flare)
    b.mesh(root, prefix + "ridge", verts, faces, "tile", (0, 0, z))
    if gable and not hip:
        for s in (-1, 1):
            verts, faces = g.horse_head_gable(depth, height, 3, 0.26, 0.55)
            b.mesh(root, prefix + f"gable_{s}", verts, faces, "plaster",
                   (s * (width / 2 - 0.06), 0, FFL), rotation=0.0 if s > 0 else math.pi)
    # Eave gutter board reads the wet edge without a particle system.
    b.box(root, prefix + "eave_board", (width + 2 * over, 0.1, 0.18),
          (0, -(depth / 2 + over), z + 0.04), "timber")

    # Bronze wind chimes hanging under the 4 upturned eave corners
    chime_w = width / 2.0 + flare * 0.55
    chime_d = depth / 2.0 + over + flare
    chime_z = z + lift * 0.85
    for c_sx in (-1, 1):
        for c_sy in (-1, 1):
            cv, cf = g.eaves_chime()
            b.mesh(root, prefix + f"eave_chime_{c_sx}_{c_sy}", cv, cf, "iron",
                   (c_sx * chime_w, c_sy * chime_d, chime_z))

    # Chiwen / 鸱吻 sit on the actual ridge ends, not the floating eave corners.
    if hip:
        beast_x = max(0.0, (width - depth) / 2.0) + 0.32
        beast_z = z + rise + 0.12
        beast_s = 0.88
    else:
        beast_x = width / 2.0 + flare * 0.45 + 0.18
        beast_z = z + rise + lift * 0.45 + 0.18
        beast_s = 0.72
    for sx in (-1, 1):
        bv, bf = g.ridge_beast(scale=beast_s)
        b.mesh(root, prefix + f"chiwen_{sx}", bv, bf, "ceramic",
               (sx * beast_x, 0.0, beast_z), 0.0 if sx > 0 else math.pi)

    # Carved hanging fascia under the street-side eave beam (挂落).
    fv, ff = g.hanging_fascia(width * 0.92, height=0.46, cols=max(4, int(width / 1.4)))
    b.mesh(root, prefix + "fascia", fv, ff, "timber",
           (0.0, -(depth / 2 - 0.22), FFL + 0.17 + height + 0.10))


def _entry_steps(b, root, prefix, depth, stream):
    n = 3
    for i in range(n):
        h = PLINTH * (i + 1) / n
        b.box(root, prefix + f"step_{i}",
              (2.2 - i * 0.12, 0.38, h),
              (0, -depth / 2 - 0.9 + i * 0.38, h / 2), "stone")


def building(b, root, spec, stream):
    """One layer-2 building. Keeps the layer-1 socket contract."""
    width, depth = spec["width"], spec["depth"]
    floors = spec["floors"]
    family = spec["family"]
    height = STOREY * floors
    bays = _bays(width)

    _plinth(b, root, "", width, depth, stream)
    _floor_plate(b, root, "", width, depth, FFL)

    if family == "pavilion":
        for s in (-1, 1):
            _post_row(b, root, "", width, depth, height, bays, stream, s)
        verts, faces = g.railing(width, 0.82, max(4, bays * 2))
        b.mesh(root, "rail_front", verts, faces, "timber", (0, -depth / 2 + 0.2, FFL))
        _roof(b, root, "", width, depth, height, stream, hip=True, gable=False)
    else:
        for s in (-1, 1):
            _post_row(b, root, "", width, depth, height, bays, stream, s)
        if family in ("shop", "inn") and floors == 2:
            _shopfront(b, root, "", width, depth, height, bays, stream)
            b.box(root, "wall_back", (width, 0.24, height),
                  (0, depth / 2 - 0.12, FFL + height / 2), "plaster")
            for s in (-1, 1):
                b.box(root, f"wall_side_{s}", (0.24, depth - 0.48, height),
                      (s * (width / 2 - 0.12), 0, FFL + height / 2), "plaster")
            _floor_plate(b, root, "upper_", width, depth, FFL + STOREY)
            _upper_gallery(b, root, "", width, depth, stream)
        elif family == "warehouse":
            _plaster_walls(b, root, "", width, depth, height, bays, stream, family)
            b.box(root, "loading_door", (2.6, 0.1, 2.8),
                  (0, -depth / 2 - 0.02, FFL + 1.4), "timber")
        else:
            _plaster_walls(b, root, "", width, depth, height, bays, stream, family)
            if floors == 2:
                _floor_plate(b, root, "upper_", width, depth, FFL + STOREY)
        _roof(b, root, "", width, depth, height, stream,
              gable=family in ("house", "shop", "inn"))

    _entry_steps(b, root, "", depth, stream)
    return height


def build(b, config, plan):
    """Same entry signature as layer-1 architecture.build."""
    for spec in plan["buildings"]:
        stream = rng(config["seed"], spec["id"] + ":detail")
        r = b.root(spec["id"], spec["family"], spec["district"], spec["location"],
                   spec["rotation"],
                   task=f"tasks/assets/{config['family_tasks'][spec['family']]}.md",
                   dimensions_m=[spec["width"], spec["depth"], spec["floors"] * STOREY],
                   parcel=spec["parcel"], frontage=spec.get("frontage", "spine"),
                   detail_level=2)
        height = building(b, r, spec, stream)
        rise = spec["depth"] * 0.30 + 0.35
        b.socket(r, "entry", (0, -spec["depth"] / 2 - 1.6, 0))
        b.socket(r, "sign", (0, -spec["depth"] / 2 - 0.3, 2.7))
        b.socket(r, "roof_ridge", (0, 0, FFL + height + 0.46 + rise), (0, 0, 1))
