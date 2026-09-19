"""Layer-3 Blender adapter: procedural materials, wet-weather grading, mist.

Scope split from :mod:`blender_io` (layer 1, flat viewport colours):

* every palette slot becomes a node network instead of a diffuse colour;
* the slots that ``docs/07_material_mapping.md`` requires to be split are split
  here, at the shader adapter, keyed on object name — one geometry slot such as
  ``timber`` resolves to old structural wood *or* tree bark, ``stone`` to brick,
  paving or wet revetment. Geometry keeps the stable slot name, so no upstream
  contract changes;
* wetness is driven by world-space Z against the water datum, so the band just
  above the canal darkens and gains specular without painting it into base
  colour (``docs/01_art_direction.md``: shadow and highlight must not be baked);
* mist is a bounded, height-graded volume rather than a world-wide fog, which
  is what gives the distance read the art direction asks of the far field.

Never opens, resets or saves the user's legacy file. ``bpy`` is imported inside
the functions so the pure-Python OBJ path keeps working on hosts with no
Blender at all.
"""
from __future__ import annotations

import math

from kernel import PALETTE


# --------------------------------------------------------------------------
# material slot resolution
# --------------------------------------------------------------------------

# (slot, keyword tuple) -> variant name. First match wins, so order matters.
_VARIANTS = (
    ("timber", ("trunk", "branch", "culm", "stem", "bough"), "bark"),
    ("timber", ("hull", "strake", "keel", "gunwale", "deck_plank"), "boat_timber"),
    ("stone", ("quay", "revetment", "bank", "step", "slip", "landing",
               "bollard", "mooring"), "wet_stone"),
    ("stone", ("path", "paving", "road", "court", "apron", "deck", "plinth_cap",
               "threshold", "flag"), "paving"),
    ("leaf", ("moss", "weed", "grass", "reed_base"), "moss"),
    ("leaf", ("frond", "willow"), "willow_leaf"),
    ("paper", ("lantern", "shade", "globe"), "lantern_paper"),
    ("cloth", ("banner", "sign", "flag", "awning", "curtain", "net"), "dyed_cloth"),
)

# Slots whose geometry is genuinely curved; these get angle-based smoothing.
_SMOOTH_HINTS = ("roof", "tile", "hull", "crown", "trunk", "culm", "water",
                 "awning", "arch", "jar", "drum", "frond", "reed", "rope",
                 "bank", "land", "canopy", "eave")


def resolve_slot(slot: str, object_name: str) -> str:
    """Map a geometry palette slot plus an object name onto a shader variant."""
    lowered = object_name.lower()
    for want_slot, keywords, variant in _VARIANTS:
        if slot == want_slot and any(k in lowered for k in keywords):
            return variant
    return slot


def wants_smooth(object_name: str) -> bool:
    lowered = object_name.lower()
    return any(k in lowered for k in _SMOOTH_HINTS)


# --------------------------------------------------------------------------
# node graph helpers
# --------------------------------------------------------------------------

class _Graph:
    """Thin wrapper that keeps node creation and layout readable."""

    def __init__(self, node_tree):
        self.tree = node_tree
        self.nodes = node_tree.nodes
        self.links = node_tree.links
        self._column = 0
        self._world_vector = None

    def add(self, kind, column=None, row=0.0, **attrs):
        node = self.nodes.new(kind)
        col = self._column if column is None else column
        node.location = (col * 220.0 - 1500.0, row * 190.0)
        for key, value in attrs.items():
            setattr(node, key, value)
        return node

    def link(self, a, a_socket, b, b_socket):
        self.links.new(a.outputs[a_socket], b.inputs[b_socket])

    def value(self, node, socket, value):
        node.inputs[socket].default_value = value

    def world_vector(self):
        """Shared world-space Position output, created once per graph."""
        if self._world_vector is None:
            self._world_vector = self.add("ShaderNodeNewGeometry",
                                         column=-6, row=-5.0)
        return self._world_vector


def _noise(graph, scale, detail=6.0, roughness=0.55, column=0, row=0.0,
           dimension="3D", world=True):
    """Noise driven by world-space position, so ``scale`` is cycles per metre.

    An unlinked Vector input makes Blender fall back to Generated coordinates,
    which are normalised across each object's bounding box. That made grain size
    depend on object size and stretch along the long axis: the 168 m paving
    strips and the quays turned into smeared bright ramps. Every authored scale
    here is a real-world frequency, so the position is linked explicitly.
    """
    node = graph.add("ShaderNodeTexNoise", column=column, row=row)
    node.noise_dimensions = dimension
    graph.value(node, "Scale", scale)
    graph.value(node, "Detail", detail)
    graph.value(node, "Roughness", roughness)
    if world:
        graph.link(graph.world_vector(), "Position", node, "Vector")
    return node


def _ramp(graph, stops, column=0, row=0.0, interpolation="LINEAR"):
    """Colour ramp from [(position, (r,g,b,a)), ...]."""
    node = graph.add("ShaderNodeValToRGB", column=column, row=row)
    node.color_ramp.interpolation = interpolation
    elements = node.color_ramp.elements
    while len(elements) > len(stops):
        elements.remove(elements[-1])
    for i, (position, colour) in enumerate(stops):
        if i < len(elements):
            elements[i].position = position
            elements[i].color = colour
        else:
            element = elements.new(position)
            element.color = colour
    return node


def _map_range(graph, from_min, from_max, to_min, to_max, column=0, row=0.0,
               clamp=True):
    node = graph.add("ShaderNodeMapRange", column=column, row=row)
    node.clamp = clamp
    graph.value(node, "From Min", from_min)
    graph.value(node, "From Max", from_max)
    graph.value(node, "To Min", to_min)
    graph.value(node, "To Max", to_max)
    return node


def _math(graph, operation, a=None, b=None, column=0, row=0.0):
    node = graph.add("ShaderNodeMath", column=column, row=row)
    node.operation = operation
    if a is not None:
        graph.value(node, 0, a)
    if b is not None:
        graph.value(node, 1, b)
    return node


def _mix_rgb(graph, column=0, row=0.0):
    node = graph.add("ShaderNodeMix", column=column, row=row)
    node.data_type = "RGBA"
    node.blend_type = "MIX"
    return node


def _tint_base(graph, bsdf, colour, column=3, row=2.6,
               blend="MULTIPLY", fac=1.0):
    """Blend a tint into whatever already drives Base Color.

    Variant recipes reuse a parent recipe and then need a different hue. Setting
    ``default_value`` would be silently ignored because the socket is linked, so
    the existing link is rerouted through a mix node instead. MULTIPLY darkens
    or shifts a tone; COLOR replaces hue and saturation while keeping the
    parent's luminance variation, which is what dyeing a woven cloth does.
    """
    socket = bsdf.inputs["Base Color"]
    upstream = socket.links[0].from_socket if socket.links else None
    node = graph.add("ShaderNodeMixRGB", column=column, row=row)
    node.blend_type = blend
    graph.value(node, "Fac", fac)
    node.inputs["Color2"].default_value = colour
    if upstream is not None:
        graph.tree.links.new(upstream, node.inputs["Color1"])
    else:
        node.inputs["Color1"].default_value = (1.0, 1.0, 1.0, 1.0)
    graph.link(node, "Color", bsdf, "Base Color")
    return node


def _world_z(graph, column=-4, row=-3.0):
    """World-space Z of the shading point, used for the damp/wet gradient."""
    geometry = graph.add("ShaderNodeNewGeometry", column=column, row=row)
    split = graph.add("ShaderNodeSeparateXYZ", column=column + 1, row=row)
    graph.link(geometry, "Position", split, "Vector")
    return split, geometry


def _object_random(graph, column=-4, row=3.0):
    """Per-instance random value; breaks up repeated tile and plaster tones."""
    info = graph.add("ShaderNodeObjectInfo", column=column, row=row)
    return info


# --------------------------------------------------------------------------
# per-variant recipes
# --------------------------------------------------------------------------


def _find_texture(name: str):
    import os
    candidates = [
        os.path.abspath(os.path.join("textures", f"{name}.png")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "textures", f"{name}.png")),
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    return None


def _load_texture_image(name: str):
    import bpy
    p = _find_texture(name)
    if not p:
        return None
    try:
        img = bpy.data.images.load(p, check_existing=True)
        img.pack()
        return img
    except Exception:
        return None


def _triplanar_albedo(graph, tex_name, scale=1.0, blend=0.25, column=-3, row=3.0):
    """Triplanar box-projected image texture for seamless macro grain without UV."""
    img = _load_texture_image(tex_name)
    if not img:
        return None
    tex_node = graph.add("ShaderNodeTexImage", column=column, row=row)
    tex_node.image = img
    tex_node.projection = "BOX"
    tex_node.projection_blend = blend
    coords = graph.add("ShaderNodeTexCoord", column=column - 2, row=row)
    mapping = graph.add("ShaderNodeMapping", column=column - 1, row=row)
    graph.value(mapping, "Scale", (scale, scale, scale))
    graph.link(coords, "Object", mapping, "Vector")
    graph.link(mapping, "Vector", tex_node, "Vector")
    return tex_node


def _base_principled(graph):
    output = graph.add("ShaderNodeOutputMaterial", column=6, row=0.0)
    bsdf = graph.add("ShaderNodeBsdfPrincipled", column=4, row=0.0)
    graph.link(bsdf, "BSDF", output, "Surface")
    return bsdf


def _apply_wetness(graph, bsdf, water_z=0.0, dry_z=3.4, max_wet=0.85,
                   darken=0.55):
    """Darken and polish geometry near the water line.

    Returns the wetness factor so callers can reuse it. The gradient is a real
    shading input: base colour is multiplied, roughness is reduced, nothing is
    painted in.
    """
    split, _ = _world_z(graph)
    wet = _map_range(graph, water_z, dry_z, max_wet, 0.0, column=-2, row=-3.0)
    graph.link(split, "Z", wet, "Value")
    # Splash line is uneven, not a ruled band.
    blotch = _noise(graph, 1.6, detail=4.0, column=-2, row=-4.6)
    blotch_scale = _map_range(graph, 0.35, 0.7, 0.55, 1.25, column=-1, row=-4.6)
    graph.link(blotch, "Fac", blotch_scale, "Value")
    wet_final = _math(graph, "MULTIPLY", column=0, row=-3.6)
    graph.link(wet, "Result", wet_final, 0)
    graph.link(blotch_scale, "Result", wet_final, 1)
    return wet_final


def _plaster(graph):
    """M01: old lime render. Light value field, damp foot, patch repairs."""
    bsdf = _base_principled(graph)
    stain = _noise(graph, 2.4, detail=8.0, roughness=0.62, column=-2, row=1.0)
    patch = _noise(graph, 9.0, detail=4.0, column=-2, row=2.4)
    tone = _ramp(graph, [
        (0.30, (0.44, 0.45, 0.42, 1.0)),
        (0.48, (0.63, 0.63, 0.59, 1.0)),
        (0.70, (0.76, 0.75, 0.70, 1.0)),
    ], column=-1, row=1.0)
    graph.link(stain, "Fac", tone, "Fac")
    repair = _ramp(graph, [
        (0.42, (0.50, 0.49, 0.46, 1.0)),
        (0.58, (0.69, 0.67, 0.61, 1.0)),
    ], column=-1, row=2.4)
    graph.link(patch, "Fac", repair, "Fac")
    blend = _mix_rgb(graph, column=0, row=1.6)
    graph.value(blend, "Factor", 0.35)
    graph.link(tone, "Color", blend, "A")
    graph.link(repair, "Color", blend, "B")

    # Rising damp: a real darkening near the ground, strongest at the skirting.
    split, _ = _world_z(graph)
    damp = _map_range(graph, 2.0, 4.2, 0.62, 0.0, column=-1, row=-2.4)
    graph.link(split, "Z", damp, "Value")
    damp_noise = _noise(graph, 3.2, detail=5.0, column=-2, row=-3.4)
    damp_mod = _math(graph, "MULTIPLY", column=0, row=-2.8)
    graph.link(damp, "Result", damp_mod, 0)
    graph.link(damp_noise, "Fac", damp_mod, 1)
    damp_colour = _mix_rgb(graph, column=2, row=1.0)
    graph.link(damp_mod, "Value", damp_colour, "Factor")
    graph.link(blend, "Result", damp_colour, "A")
    damp_tint = graph.add("ShaderNodeRGB", column=1, row=-0.6)
    damp_tint.outputs[0].default_value = (0.26, 0.28, 0.26, 1.0)
    graph.link(damp_tint, "Color", damp_colour, "B")

    tex = _triplanar_albedo(graph, "plaster", scale=0.35, column=2, row=2.4)
    if tex:
        mix_tex = _mix_rgb(graph, column=3, row=1.0)
        graph.value(mix_tex, "Factor", 0.75)
        mix_tex.blend_type = "MULTIPLY"
        graph.link(damp_colour, "Result", mix_tex, "A")
        graph.link(tex, "Color", mix_tex, "B")
        graph.link(mix_tex, "Result", bsdf, "Base Color")
    else:
        graph.link(damp_colour, "Result", bsdf, "Base Color")

    rough = _map_range(graph, 0.0, 1.0, 0.94, 0.72, column=2, row=-2.0)
    graph.link(stain, "Fac", rough, "Value")
    graph.link(rough, "Result", bsdf, "Roughness")

    bump = graph.add("ShaderNodeBump", column=3, row=-3.0)
    graph.value(bump, "Strength", 0.22)
    graph.value(bump, "Distance", 0.02)
    graph.link(stain, "Fac", bump, "Height")
    graph.link(bump, "Normal", bsdf, "Normal")
    return bsdf


def _tile(graph):
    """M03: dark fired roof tile. Per-roof tone shift plus course-scale bump."""
    bsdf = _base_principled(graph)
    info = _object_random(graph)
    variation = _map_range(graph, 0.0, 1.0, -0.035, 0.045, column=-2, row=3.0)
    graph.link(info, "Random", variation, "Value")

    grain = _noise(graph, 26.0, detail=6.0, roughness=0.7, column=-2, row=0.6)
    tone = _ramp(graph, [
        (0.34, (0.035, 0.050, 0.058, 1.0)),
        (0.52, (0.085, 0.105, 0.115, 1.0)),
        (0.74, (0.150, 0.168, 0.170, 1.0)),
    ], column=-1, row=0.6)
    graph.link(grain, "Fac", tone, "Fac")
    lift = graph.add("ShaderNodeMixRGB", column=0, row=0.6)
    lift.blend_type = "ADD"
    graph.value(lift, "Fac", 1.0)
    graph.link(tone, "Color", lift, "Color1")
    tint = graph.add("ShaderNodeCombineColor", column=-1, row=3.0)
    graph.link(variation, "Result", tint, "Red")
    graph.link(variation, "Result", tint, "Green")
    graph.link(variation, "Result", tint, "Blue")
    graph.link(tint, "Color", lift, "Color2")

    # Moss creeps into the shaded courses rather than coating the whole roof.
    moss_mask = _noise(graph, 5.5, detail=7.0, column=-2, row=-1.0)
    moss_gate = _map_range(graph, 0.58, 0.74, 0.0, 0.7, column=-1, row=-1.0)
    graph.link(moss_mask, "Fac", moss_gate, "Value")
    moss_mix = _mix_rgb(graph, column=2, row=0.6)
    graph.link(moss_gate, "Result", moss_mix, "Factor")
    graph.link(lift, "Color", moss_mix, "A")
    moss_colour = graph.add("ShaderNodeRGB", column=1, row=-1.4)
    moss_colour.outputs[0].default_value = (0.10, 0.16, 0.085, 1.0)
    graph.link(moss_colour, "Color", moss_mix, "B")

    tex = _triplanar_albedo(graph, "clay", scale=1.1, column=2, row=1.8)
    if tex:
        mix_tex = _mix_rgb(graph, column=3, row=0.6)
        graph.value(mix_tex, "Factor", 0.70)
        mix_tex.blend_type = "MULTIPLY"
        graph.link(moss_mix, "Result", mix_tex, "A")
        graph.link(tex, "Color", mix_tex, "B")
        graph.link(mix_tex, "Result", bsdf, "Base Color")
    else:
        graph.link(moss_mix, "Result", bsdf, "Base Color")

    wet = _apply_wetness(graph, bsdf, dry_z=2.6, max_wet=0.35)
    rough = _map_range(graph, 0.0, 1.0, 0.58, 0.20, column=2, row=-2.4)
    graph.link(wet, "Value", rough, "Value")
    graph.link(rough, "Result", bsdf, "Roughness")

    bump = graph.add("ShaderNodeBump", column=3, row=-3.4)
    graph.value(bump, "Strength", 0.35)
    graph.value(bump, "Distance", 0.012)
    graph.link(grain, "Fac", bump, "Height")
    graph.link(bump, "Normal", bsdf, "Normal")
    return bsdf


def _timber(graph):
    """M04: structural old wood. Grain stretched along the member's long axis."""
    bsdf = _base_principled(graph)
    coords = graph.add("ShaderNodeTexCoord", column=-4, row=1.0)
    stretch = graph.add("ShaderNodeMapping", column=-3, row=1.0)
    graph.value(stretch, "Scale", (1.0, 0.14, 0.14))
    graph.link(coords, "Object", stretch, "Vector")
    grain = _noise(graph, 12.0, detail=9.0, roughness=0.68, column=-2, row=1.0)
    graph.link(stretch, "Vector", grain, "Vector")
    tone = _ramp(graph, [
        (0.32, (0.075, 0.048, 0.030, 1.0)),
        (0.50, (0.165, 0.105, 0.062, 1.0)),
        (0.72, (0.245, 0.160, 0.095, 1.0)),
    ], column=-1, row=1.0)
    graph.link(grain, "Fac", tone, "Fac")

    info = _object_random(graph)
    shift = _map_range(graph, 0.0, 1.0, 0.86, 1.16, column=-2, row=3.0)
    graph.link(info, "Random", shift, "Value")
    scaled = graph.add("ShaderNodeMixRGB", column=0, row=1.0)
    scaled.blend_type = "MULTIPLY"
    graph.value(scaled, "Fac", 1.0)
    graph.link(tone, "Color", scaled, "Color1")
    shift_colour = graph.add("ShaderNodeCombineColor", column=-1, row=3.0)
    graph.link(shift, "Result", shift_colour, "Red")
    graph.link(shift, "Result", shift_colour, "Green")
    graph.link(shift, "Result", shift_colour, "Blue")
    graph.link(shift_colour, "Color", scaled, "Color2")

    tex = _triplanar_albedo(graph, "wood", scale=0.85, column=1, row=2.2)
    if tex:
        mix_tex = _mix_rgb(graph, column=2, row=1.0)
        graph.value(mix_tex, "Factor", 0.65)
        mix_tex.blend_type = "MULTIPLY"
        graph.link(scaled, "Color", mix_tex, "A")
        graph.link(tex, "Color", mix_tex, "B")
        graph.link(mix_tex, "Result", bsdf, "Base Color")
    else:
        graph.link(scaled, "Color", bsdf, "Base Color")

    wet = _apply_wetness(graph, bsdf, dry_z=3.0, max_wet=0.5)
    rough = _map_range(graph, 0.0, 1.0, 0.80, 0.34, column=2, row=-2.4)
    graph.link(wet, "Value", rough, "Value")
    graph.link(rough, "Result", bsdf, "Roughness")

    bump = graph.add("ShaderNodeBump", column=3, row=-3.4)
    graph.value(bump, "Strength", 0.30)
    graph.value(bump, "Distance", 0.010)
    graph.link(grain, "Fac", bump, "Height")
    graph.link(bump, "Normal", bsdf, "Normal")
    return bsdf


def _bark(graph):
    """M08: tree bark. Split from the timber slot per the mapping table."""
    bsdf = _base_principled(graph)
    coords = graph.add("ShaderNodeTexCoord", column=-4, row=1.0)
    stretch = graph.add("ShaderNodeMapping", column=-3, row=1.0)
    graph.value(stretch, "Scale", (0.22, 0.22, 1.0))
    graph.link(coords, "Object", stretch, "Vector")
    fissures = graph.add("ShaderNodeTexNoise", column=-2, row=1.0)
    graph.value(fissures, "Scale", 14.0)
    graph.value(fissures, "Detail", 8.0)
    graph.value(fissures, "Roughness", 0.72)
    graph.link(stretch, "Vector", fissures, "Vector")
    tone = _ramp(graph, [
        (0.28, (0.055, 0.045, 0.035, 1.0)),
        (0.52, (0.115, 0.095, 0.072, 1.0)),
        (0.78, (0.185, 0.160, 0.125, 1.0)),
    ], column=-1, row=1.0)
    graph.link(fissures, "Fac", tone, "Fac")

    tex = _triplanar_albedo(graph, "bark", scale=0.6, column=0, row=2.4)
    if tex:
        mix_tex = _mix_rgb(graph, column=1, row=1.0)
        graph.value(mix_tex, "Factor", 0.72)
        mix_tex.blend_type = "MULTIPLY"
        graph.link(tone, "Color", mix_tex, "A")
        graph.link(tex, "Color", mix_tex, "B")
        graph.link(mix_tex, "Result", bsdf, "Base Color")
    else:
        graph.link(tone, "Color", bsdf, "Base Color")
    graph.value(bsdf, "Roughness", 0.93)
    bump = graph.add("ShaderNodeBump", column=3, row=-2.0)
    graph.value(bump, "Strength", 0.6)
    graph.value(bump, "Distance", 0.03)
    graph.link(fissures, "Fac", bump, "Height")
    graph.link(bump, "Normal", bsdf, "Normal")
    return bsdf


def _boat_timber(graph):
    """Tarred hull planking: darker and wetter than building timber."""
    bsdf = _timber(graph)
    _tint_base(graph, bsdf, (0.42, 0.34, 0.30, 1.0))
    graph.value(bsdf, "Roughness", 0.42)
    return bsdf


def _brick(graph):
    """M02: grey brick and stonework above the splash line."""
    bsdf = _base_principled(graph)
    coarse = _noise(graph, 4.5, detail=7.0, column=-2, row=1.0)
    fine = _noise(graph, 34.0, detail=4.0, column=-2, row=2.4)
    tone = _ramp(graph, [
        (0.30, (0.175, 0.195, 0.190, 1.0)),
        (0.52, (0.285, 0.310, 0.300, 1.0)),
        (0.76, (0.385, 0.405, 0.390, 1.0)),
    ], column=-1, row=1.0)
    graph.link(coarse, "Fac", tone, "Fac")

    tex = _triplanar_albedo(graph, "stone", scale=0.55, column=0, row=2.0)
    if tex:
        mix_tex = _mix_rgb(graph, column=1, row=1.0)
        graph.value(mix_tex, "Factor", 0.68)
        mix_tex.blend_type = "MULTIPLY"
        graph.link(tone, "Color", mix_tex, "A")
        graph.link(tex, "Color", mix_tex, "B")
        graph.link(mix_tex, "Result", bsdf, "Base Color")
    else:
        graph.link(tone, "Color", bsdf, "Base Color")
    wet = _apply_wetness(graph, bsdf, dry_z=3.2, max_wet=0.55)
    rough = _map_range(graph, 0.0, 1.0, 0.86, 0.30, column=2, row=-2.4)
    graph.link(wet, "Value", rough, "Value")
    graph.link(rough, "Result", bsdf, "Roughness")
    bump = graph.add("ShaderNodeBump", column=3, row=-3.4)
    graph.value(bump, "Strength", 0.34)
    graph.value(bump, "Distance", 0.014)
    graph.link(fine, "Fac", bump, "Height")
    graph.link(bump, "Normal", bsdf, "Normal")
    return bsdf


def _paving(graph):
    """M05: worn flagstones. Footfall polishes the centre of a path."""
    bsdf = _base_principled(graph)
    slabs = _noise(graph, 7.0, detail=3.0, roughness=0.4, column=-2, row=1.0)
    wear = _noise(graph, 1.1, detail=6.0, column=-2, row=2.6)
    tone = _ramp(graph, [
        (0.32, (0.165, 0.180, 0.178, 1.0)),
        (0.55, (0.265, 0.285, 0.278, 1.0)),
        (0.80, (0.360, 0.375, 0.360, 1.0)),
    ], column=-1, row=1.0)
    graph.link(slabs, "Fac", tone, "Fac")

    tex = _triplanar_albedo(graph, "stone", scale=0.45, column=0, row=2.0)
    if tex:
        mix_tex = _mix_rgb(graph, column=1, row=1.0)
        graph.value(mix_tex, "Factor", 0.65)
        mix_tex.blend_type = "MULTIPLY"
        graph.link(tone, "Color", mix_tex, "A")
        graph.link(tex, "Color", mix_tex, "B")
        graph.link(mix_tex, "Result", bsdf, "Base Color")
    else:
        graph.link(tone, "Color", bsdf, "Base Color")
    # Polished where feet fall, rough at the edges; wetness stacks on top.
    polish = _map_range(graph, 0.35, 0.75, 0.88, 0.42, column=-1, row=2.6)
    graph.link(wear, "Fac", polish, "Value")
    wet = _apply_wetness(graph, bsdf, dry_z=2.9, max_wet=0.6)
    combine = _math(graph, "MULTIPLY", column=1, row=-2.0)
    graph.link(polish, "Result", combine, 0)
    inverse = _math(graph, "SUBTRACT", a=1.0, column=0, row=-2.8)
    graph.link(wet, "Value", inverse, 1)
    graph.link(inverse, "Value", combine, 1)
    graph.link(combine, "Value", bsdf, "Roughness")
    bump = graph.add("ShaderNodeBump", column=3, row=-3.4)
    graph.value(bump, "Strength", 0.28)
    graph.value(bump, "Distance", 0.02)
    graph.link(slabs, "Fac", bump, "Height")
    graph.link(bump, "Normal", bsdf, "Normal")
    return bsdf


def _wet_stone(graph):
    """M06: revetment and steps in the tide band. Algae at the water line."""
    bsdf = _base_principled(graph)
    rock = _noise(graph, 6.0, detail=8.0, column=-2, row=1.0)
    tone = _ramp(graph, [
        (0.30, (0.115, 0.130, 0.125, 1.0)),
        (0.55, (0.205, 0.225, 0.215, 1.0)),
        (0.80, (0.300, 0.315, 0.300, 1.0)),
    ], column=-1, row=1.0)
    graph.link(rock, "Fac", tone, "Fac")

    split, _ = _world_z(graph)
    algae_band = _map_range(graph, 0.05, 1.5, 1.0, 0.0, column=-2, row=-1.4)
    graph.link(split, "Z", algae_band, "Value")
    algae_break = _noise(graph, 3.0, detail=6.0, column=-2, row=-2.6)
    algae_mask = _math(graph, "MULTIPLY", column=-1, row=-1.8)
    graph.link(algae_band, "Result", algae_mask, 0)
    graph.link(algae_break, "Fac", algae_mask, 1)
    algae_mix = _mix_rgb(graph, column=2, row=1.0)
    graph.link(algae_mask, "Value", algae_mix, "Factor")
    graph.link(tone, "Color", algae_mix, "A")
    algae_colour = graph.add("ShaderNodeRGB", column=1, row=-0.8)
    algae_colour.outputs[0].default_value = (0.055, 0.105, 0.060, 1.0)
    graph.link(algae_colour, "Color", algae_mix, "B")

    tex = _triplanar_albedo(graph, "stone", scale=0.5, column=2, row=2.5)
    if tex:
        mix_tex = _mix_rgb(graph, column=3, row=1.0)
        graph.value(mix_tex, "Factor", 0.70)
        mix_tex.blend_type = "MULTIPLY"
        graph.link(algae_mix, "Result", mix_tex, "A")
        graph.link(tex, "Color", mix_tex, "B")
        graph.link(mix_tex, "Result", bsdf, "Base Color")
    else:
        graph.link(algae_mix, "Result", bsdf, "Base Color")

    wet = _apply_wetness(graph, bsdf, dry_z=3.6, max_wet=0.95)
    rough = _map_range(graph, 0.0, 1.0, 0.82, 0.12, column=3, row=-2.4)
    graph.link(wet, "Value", rough, "Value")
    graph.link(rough, "Result", bsdf, "Roughness")
    bump = graph.add("ShaderNodeBump", column=3, row=-3.6)
    graph.value(bump, "Strength", 0.42)
    graph.value(bump, "Distance", 0.022)
    graph.link(rock, "Fac", bump, "Height")
    graph.link(bump, "Normal", bsdf, "Normal")
    return bsdf


def _earth(graph):
    """M14: damp ground. Reads as soil and turf, not a green carpet."""
    bsdf = _base_principled(graph)
    macro = _noise(graph, 1.5, detail=8.0, column=-2, row=1.0)
    micro = _noise(graph, 22.0, detail=5.0, column=-2, row=2.6)
    tone = _ramp(graph, [
        (0.26, (0.085, 0.095, 0.055, 1.0)),
        (0.46, (0.140, 0.155, 0.085, 1.0)),
        (0.62, (0.195, 0.205, 0.120, 1.0)),
        (0.82, (0.150, 0.130, 0.085, 1.0)),
    ], column=-1, row=1.0)
    graph.link(macro, "Fac", tone, "Fac")
    graph.link(tone, "Color", bsdf, "Base Color")
    wet = _apply_wetness(graph, bsdf, dry_z=2.8, max_wet=0.5)
    rough = _map_range(graph, 0.0, 1.0, 0.97, 0.55, column=2, row=-2.4)
    graph.link(wet, "Value", rough, "Value")
    graph.link(rough, "Result", bsdf, "Roughness")
    bump = graph.add("ShaderNodeBump", column=3, row=-3.4)
    graph.value(bump, "Strength", 0.5)
    graph.value(bump, "Distance", 0.05)
    graph.link(micro, "Fac", bump, "Height")
    graph.link(bump, "Normal", bsdf, "Normal")
    return bsdf


def _water(graph):
    """Canal surface: glossy, slightly absorbing, with a fine ripple normal."""
    output = graph.add("ShaderNodeOutputMaterial", column=6, row=0.0)
    bsdf = graph.add("ShaderNodeBsdfPrincipled", column=4, row=0.0)
    graph.link(bsdf, "BSDF", output, "Surface")
    graph.value(bsdf, "Base Color", (0.055, 0.105, 0.105, 1.0))
    graph.value(bsdf, "Roughness", 0.055)
    graph.value(bsdf, "IOR", 1.333)
    # Enough transmission to read as water without paying for deep refraction.
    if "Transmission Weight" in bsdf.inputs:
        graph.value(bsdf, "Transmission Weight", 0.55)

    # World-space, like every other surface: on a single 760 m plane, Generated
    # coordinates turned these into 18 m and 5.8 m swells instead of ripples.
    # Scales are cycles per metre, so these are ~17 cm wind ripples with ~6 cm
    # chop on top. The original 42/130 became 2 cm and 8 mm features once the
    # coordinates were metric, which aliases into shimmer instead of reading
    # as water at these camera distances.
    ripple_a = _noise(graph, 6.0, detail=5.0, roughness=0.5, column=-2, row=1.0)
    ripple_b = _noise(graph, 17.0, detail=3.0, column=-2, row=2.4)
    mix = _math(graph, "ADD", column=0, row=1.6)
    graph.link(ripple_a, "Fac", mix, 0)
    graph.link(ripple_b, "Fac", mix, 1)
    bump = graph.add("ShaderNodeBump", column=3, row=-1.0)
    graph.value(bump, "Strength", 0.12)
    graph.value(bump, "Distance", 0.006)
    graph.link(mix, "Value", bump, "Height")
    graph.link(bump, "Normal", bsdf, "Normal")

    volume = graph.add("ShaderNodeVolumeAbsorption", column=4, row=-3.0)
    graph.value(volume, "Color", (0.10, 0.20, 0.17, 1.0))
    graph.value(volume, "Density", 0.55)
    graph.link(volume, "Volume", output, "Volume")
    return bsdf


def _leaf(graph):
    """M16: foliage. Translucent, varied per cluster, darker at the core."""
    bsdf = _base_principled(graph)
    variation = _noise(graph, 3.0, detail=7.0, column=-2, row=1.0)
    tone = _ramp(graph, [
        (0.28, (0.045, 0.085, 0.040, 1.0)),
        (0.50, (0.090, 0.165, 0.075, 1.0)),
        (0.74, (0.150, 0.250, 0.105, 1.0)),
    ], column=-1, row=1.0)
    graph.link(variation, "Fac", tone, "Fac")
    info = _object_random(graph)
    shift = _map_range(graph, 0.0, 1.0, 0.80, 1.22, column=-2, row=3.0)
    graph.link(info, "Random", shift, "Value")
    scaled = graph.add("ShaderNodeMixRGB", column=0, row=1.0)
    scaled.blend_type = "MULTIPLY"
    graph.value(scaled, "Fac", 1.0)
    graph.link(tone, "Color", scaled, "Color1")
    shift_colour = graph.add("ShaderNodeCombineColor", column=-1, row=3.0)
    for channel in ("Red", "Green", "Blue"):
        graph.link(shift, "Result", shift_colour, channel)
    graph.link(shift_colour, "Color", scaled, "Color2")

    tex = _triplanar_albedo(graph, "wood", scale=0.85, column=1, row=2.2)
    if tex:
        mix_tex = _mix_rgb(graph, column=2, row=1.0)
        graph.value(mix_tex, "Factor", 0.65)
        mix_tex.blend_type = "MULTIPLY"
        graph.link(scaled, "Color", mix_tex, "A")
        graph.link(tex, "Color", mix_tex, "B")
        graph.link(mix_tex, "Result", bsdf, "Base Color")
    else:
        graph.link(scaled, "Color", bsdf, "Base Color")
    graph.value(bsdf, "Roughness", 0.78)
    # Backlit leaves glow; approximated with translucency, not emission.
    if "Subsurface Weight" in bsdf.inputs:
        graph.value(bsdf, "Subsurface Weight", 0.22)
        graph.value(bsdf, "Subsurface Radius", (0.06, 0.12, 0.04))
    return bsdf


def _willow_leaf(graph):
    """Willow foliage: yellower and lighter than the generic leaf slot."""
    bsdf = _leaf(graph)
    _tint_base(graph, bsdf, (0.62, 0.78, 0.42, 1.0), blend="COLOR", fac=0.75)
    return bsdf


def _moss(graph):
    """M15: moss on stone and roof edges."""
    bsdf = _base_principled(graph)
    tufts = _noise(graph, 18.0, detail=8.0, column=-2, row=1.0)
    tone = _ramp(graph, [
        (0.34, (0.050, 0.085, 0.035, 1.0)),
        (0.62, (0.105, 0.150, 0.060, 1.0)),
    ], column=-1, row=1.0)
    graph.link(tufts, "Fac", tone, "Fac")
    graph.link(tone, "Color", bsdf, "Base Color")
    graph.value(bsdf, "Roughness", 0.95)
    bump = graph.add("ShaderNodeBump", column=3, row=-2.0)
    graph.value(bump, "Strength", 0.55)
    graph.value(bump, "Distance", 0.012)
    graph.link(tufts, "Fac", bump, "Height")
    graph.link(bump, "Normal", bsdf, "Normal")
    return bsdf


def _bamboo(graph):
    """M07: bamboo culm. Yellow-green, smoother than timber, node banding."""
    bsdf = _base_principled(graph)
    coords = graph.add("ShaderNodeTexCoord", column=-4, row=1.0)
    bands = graph.add("ShaderNodeMapping", column=-3, row=1.0)
    graph.value(bands, "Scale", (0.2, 0.2, 3.0))
    graph.link(coords, "Object", bands, "Vector")
    grain = _noise(graph, 9.0, detail=5.0, column=-2, row=1.0)
    graph.link(bands, "Vector", grain, "Vector")
    tone = _ramp(graph, [
        (0.32, (0.175, 0.205, 0.085, 1.0)),
        (0.56, (0.290, 0.330, 0.150, 1.0)),
        (0.80, (0.395, 0.420, 0.215, 1.0)),
    ], column=-1, row=1.0)
    graph.link(grain, "Fac", tone, "Fac")
    graph.link(tone, "Color", bsdf, "Base Color")
    graph.value(bsdf, "Roughness", 0.55)
    bump = graph.add("ShaderNodeBump", column=3, row=-2.0)
    graph.value(bump, "Strength", 0.18)
    graph.value(bump, "Distance", 0.008)
    graph.link(grain, "Fac", bump, "Height")
    graph.link(bump, "Normal", bsdf, "Normal")
    return bsdf


def _cloth(graph):
    """M09: coarse hemp. Woven, matte, sheen at grazing angles."""
    bsdf = _base_principled(graph)
    weave = _noise(graph, 90.0, detail=3.0, column=-2, row=1.0)
    tone = _ramp(graph, [
        (0.36, (0.255, 0.205, 0.145, 1.0)),
        (0.64, (0.425, 0.350, 0.250, 1.0)),
    ], column=-1, row=1.0)
    graph.link(weave, "Fac", tone, "Fac")
    graph.link(tone, "Color", bsdf, "Base Color")
    graph.value(bsdf, "Roughness", 0.96)
    if "Sheen Weight" in bsdf.inputs:
        graph.value(bsdf, "Sheen Weight", 0.35)
    bump = graph.add("ShaderNodeBump", column=3, row=-2.0)
    graph.value(bump, "Strength", 0.25)
    graph.value(bump, "Distance", 0.004)
    graph.link(weave, "Fac", bump, "Height")
    graph.link(bump, "Normal", bsdf, "Normal")
    return bsdf


def _dyed_cloth(graph):
    """M10: indigo-dyed cloth for banners and shop signs.

    Dyeing keeps the weave's luminance variation and replaces the hue, so this
    blends in COLOR mode rather than multiplying the hemp tone down to black.
    """
    bsdf = _cloth(graph)
    _tint_base(graph, bsdf, (0.105, 0.145, 0.315, 1.0), blend="COLOR", fac=0.9)
    return bsdf


def _paper(graph):
    """M11: oiled lantern paper, translucent but not self-lit."""
    bsdf = _base_principled(graph)
    fibre = _noise(graph, 45.0, detail=6.0, column=-2, row=1.0)
    tone = _ramp(graph, [
        (0.35, (0.520, 0.320, 0.150, 1.0)),
        (0.65, (0.760, 0.520, 0.250, 1.0)),
    ], column=-1, row=1.0)
    graph.link(fibre, "Fac", tone, "Fac")
    graph.link(tone, "Color", bsdf, "Base Color")
    graph.value(bsdf, "Roughness", 0.82)
    if "Transmission Weight" in bsdf.inputs:
        graph.value(bsdf, "Transmission Weight", 0.25)
    return bsdf


def _lantern_paper(graph):
    """Lit lantern: emission carries the warm accent the art direction wants.

    Emissive geometry rather than added point lights keeps 144 lanterns
    affordable and lets the bounded mist volume pick up the glow.
    """
    bsdf = _paper(graph)
    graph.value(bsdf, "Emission Color", (1.0, 0.62, 0.28, 1.0))
    graph.value(bsdf, "Emission Strength", 12.0)
    return bsdf


def _ceramic(graph):
    """M12: unglazed coarse pottery with a partial glaze run."""
    bsdf = _base_principled(graph)
    body = _noise(graph, 14.0, detail=6.0, column=-2, row=1.0)
    tone = _ramp(graph, [
        (0.34, (0.150, 0.095, 0.065, 1.0)),
        (0.62, (0.290, 0.190, 0.125, 1.0)),
    ], column=-1, row=1.0)
    graph.link(body, "Fac", tone, "Fac")
    graph.link(tone, "Color", bsdf, "Base Color")
    glaze = _map_range(graph, 0.45, 0.62, 0.72, 0.18, column=0, row=-1.0)
    graph.link(body, "Fac", glaze, "Value")
    graph.link(glaze, "Result", bsdf, "Roughness")
    return bsdf


def _iron(graph):
    """M13: old wrought iron, rusting unevenly at the fixings."""
    bsdf = _base_principled(graph)
    rust = _noise(graph, 20.0, detail=7.0, column=-2, row=1.0)
    tone = _ramp(graph, [
        (0.38, (0.050, 0.052, 0.050, 1.0)),
        (0.60, (0.105, 0.085, 0.062, 1.0)),
        (0.80, (0.185, 0.105, 0.058, 1.0)),
    ], column=-1, row=1.0)
    graph.link(rust, "Fac", tone, "Fac")
    graph.link(tone, "Color", bsdf, "Base Color")
    metallic = _map_range(graph, 0.40, 0.70, 0.85, 0.10, column=0, row=-0.6)
    graph.link(rust, "Fac", metallic, "Value")
    graph.link(metallic, "Result", bsdf, "Metallic")
    rough = _map_range(graph, 0.40, 0.75, 0.42, 0.88, column=0, row=-1.8)
    graph.link(rust, "Fac", rough, "Value")
    graph.link(rough, "Result", bsdf, "Roughness")
    bump = graph.add("ShaderNodeBump", column=3, row=-3.0)
    graph.value(bump, "Strength", 0.3)
    graph.value(bump, "Distance", 0.006)
    graph.link(rust, "Fac", bump, "Height")
    graph.link(bump, "Normal", bsdf, "Normal")
    return bsdf


_RECIPES = {
    "plaster": _plaster,
    "tile": _tile,
    "timber": _timber,
    "bark": _bark,
    "boat_timber": _boat_timber,
    "stone": _brick,
    "paving": _paving,
    "wet_stone": _wet_stone,
    "earth": _earth,
    "water": _water,
    "leaf": _leaf,
    "willow_leaf": _willow_leaf,
    "moss": _moss,
    "bamboo": _bamboo,
    "cloth": _cloth,
    "dyed_cloth": _dyed_cloth,
    "paper": _paper,
    "lantern_paper": _lantern_paper,
    "ceramic": _ceramic,
    "iron": _iron,
}


def build_materials():
    """Create one Blender material per shader variant. Returns name -> material."""
    import bpy

    out = {}
    for variant, recipe in _RECIPES.items():
        material = bpy.data.materials.new("JNX_MAT_" + variant)
        material.use_nodes = True
        material.node_tree.nodes.clear()
        graph = _Graph(material.node_tree)
        recipe(graph)
        # Viewport fallback keeps solid mode legible for whoever opens the file.
        base_slot = variant if variant in PALETTE else "stone"
        colour, roughness = PALETTE.get(base_slot, ((0.5, 0.5, 0.5), 0.8))
        material.diffuse_color = (*colour, 1.0)
        material.roughness = roughness
        if variant == "water":
            material.blend_method = "BLEND" if hasattr(material, "blend_method") else "OPAQUE"
        out[variant] = material
    return out


# --------------------------------------------------------------------------
# atmosphere
# --------------------------------------------------------------------------

#: Per-mood atmosphere. Each entry drives sky, mist and lighting together so a
#: mood is one decision rather than three that can drift apart.
MOODS = {
    # Cold moon through thin rain: the reference look.
    "drizzle": dict(zenith=(0.008, 0.013, 0.026), horizon=(0.042, 0.056, 0.080),
                    sky_strength=1.0, moon_energy=2.4, moon_k=(0.62, 0.74, 1.00),
                    moon_elev=52.0, moon_azim=214.0, moon_angle=1.8,
                    bounce=0.09, mist=0.0026, mist_top=17.0,
                    mist_k=(0.52, 0.60, 0.72)),
    # Mist sits heavier and the moon is further veiled.
    "fog": dict(zenith=(0.010, 0.015, 0.026), horizon=(0.055, 0.068, 0.088),
                sky_strength=1.3, moon_energy=1.5, moon_k=(0.66, 0.76, 0.98),
                moon_elev=58.0, moon_azim=200.0, moon_angle=6.0,
                bounce=0.13, mist=0.0052, mist_top=22.0,
                mist_k=(0.58, 0.65, 0.74)),
    # Snow: brighter bounce off the ground, colder key, still night.
    "snow": dict(zenith=(0.011, 0.018, 0.034), horizon=(0.060, 0.074, 0.100),
                 sky_strength=1.2, moon_energy=3.0, moon_k=(0.70, 0.80, 1.00),
                 moon_elev=46.0, moon_azim=228.0, moon_angle=2.4,
                 bounce=0.16, mist=0.0030, mist_top=15.0,
                 mist_k=(0.62, 0.70, 0.82)),
}


def mood_spec(mood):
    return MOODS.get(mood, MOODS["drizzle"])


def build_world(scene, mood="drizzle"):
    """Night sky: a dim cool gradient. Brightness comes from the moon and the
    lanterns, never from the dome.

    A Nishita daytime dome was the first attempt and it lit the whole town
    evenly, which killed the contrast the art direction depends on. A hand-set
    gradient keeps the sky as a dark backdrop that the mist can catch.
    """
    import bpy

    spec = mood_spec(mood)
    world = bpy.data.worlds.new("JNX_World_" + mood)
    world.use_nodes = True
    tree = world.node_tree
    tree.nodes.clear()
    graph = _Graph(tree)
    output = graph.add("ShaderNodeOutputWorld", column=6)
    background = graph.add("ShaderNodeBackground", column=4)
    graph.link(background, "Background", output, "Surface")

    # View direction, so the gradient runs horizon -> zenith.
    coord = graph.add("ShaderNodeTexCoord", column=-2)
    split = graph.add("ShaderNodeSeparateXYZ", column=-1)
    graph.link(coord, "Generated", split, "Vector")
    height = _map_range(graph, -0.10, 0.55, 0.0, 1.0, column=0, row=0.0)
    graph.link(split, "Z", height, "Value")
    tone = _ramp(graph, [
        (0.00, spec["horizon"] + (1.0,)),
        (1.00, spec["zenith"] + (1.0,)),
    ], column=2, row=0.0)
    graph.link(height, "Result", tone, "Fac")
    graph.link(tone, "Color", background, "Color")
    graph.value(background, "Strength", spec["sky_strength"])
    scene.world = world
    return world


def build_distant_scenery(scene, bounds, radius=540.0, height=155.0):
    """Panoramic ink landscape screen borrowing Song dynasty scenery beyond the canals."""
    import bpy, os, math

    p = _find_texture("landscape")
    if not p:
        return None

    try:
        img = bpy.data.images.load(p, check_existing=True)
        img.pack()
    except Exception:
        return None

    # Cylindrical panorama screen on the northern horizon
    mesh_data = bpy.data.meshes.new("JNX_MESH_distant_landscape")
    n_segments = 80
    verts = []
    faces = []
    uvs = []
    for j in range(2):
        z = -15.0 if j == 0 else height
        for i in range(n_segments + 1):
            a = -math.pi * 0.68 + (math.pi * 1.36) * i / n_segments
            x = radius * math.sin(a)
            y = radius * math.cos(a) + 60.0
            verts.append((x, y, z))
            uvs.append((i / n_segments, j))

    for i in range(n_segments):
        a = i
        b = i + 1
        c = i + 1 + (n_segments + 1)
        d = i + (n_segments + 1)
        faces.append((a, b, c, d))

    mesh_data.from_pydata(verts, [], faces)
    mesh_data.update()

    uv_layer = mesh_data.uv_layers.new(name="LandscapeUV")
    for loop in mesh_data.loops:
        uv_layer.data[loop.index].uv = uvs[loop.vertex_index]

    obj = bpy.data.objects.new("JNX_DISTANT_LANDSCAPE", mesh_data)
    scene.collection.objects.link(obj)

    mat = bpy.data.materials.new("JNX_MAT_distant_landscape")
    mat.use_nodes = True
    mat.node_tree.nodes.clear()
    graph = _Graph(mat.node_tree)

    output = graph.add("ShaderNodeOutputMaterial", column=6)
    bsdf = graph.add("ShaderNodeBsdfPrincipled", column=4)
    graph.link(bsdf, "BSDF", output, "Surface")

    tex = graph.add("ShaderNodeTexImage", column=0)
    tex.image = img
    uv_node = graph.add("ShaderNodeUVMap", column=-2)
    uv_node.uv_map = "LandscapeUV"
    graph.link(uv_node, "UV", tex, "Vector")

    graph.link(tex, "Color", bsdf, "Base Color")
    graph.link(tex, "Color", bsdf, "Emission Color")
    graph.value(bsdf, "Emission Strength", 0.45)
    graph.value(bsdf, "Roughness", 1.0)
    if "Specular IOR Level" in bsdf.inputs:
        graph.value(bsdf, "Specular IOR Level", 0.0)

    mesh_data.materials.append(mat)
    return obj


def build_mist(scene, bounds, water_z=0.0, top=None, density=None,
               mood="drizzle"):
    """A bounded, height-graded scatter volume: low mist over the canals.

    A world volume would fog the whole sky and cost far more; this cube covers
    the planned area only, and the density ramp keeps the haze in the first few
    metres above the water where it reads as 烟雨.

    Density and ceiling come from the mood: the first pass used a 52 m tall,
    0.0055-dense volume that washed every shot to a flat grey (p01 brightness
    138/255 at eye level), so the mist now stays below the eaves and lets the
    roofline read against the dark sky.
    """
    import bpy

    spec = mood_spec(mood)
    if top is None:
        top = spec["mist_top"]
    if density is None:
        density = spec["mist"]

    x0, y0, x1, y1 = bounds
    pad = 40.0
    width = (x1 - x0) + pad * 2
    depth = (y1 - y0) + pad * 2
    height = top - water_z + 8.0

    mesh = bpy.data.meshes.new("JNX_MESH_mist_volume")
    hx, hy, hz = width / 2, depth / 2, height / 2
    verts = [(-hx, -hy, -hz), (hx, -hy, -hz), (hx, hy, -hz), (-hx, hy, -hz),
             (-hx, -hy, hz), (hx, -hy, hz), (hx, hy, hz), (-hx, hy, hz)]
    faces = [(3, 2, 1, 0), (4, 5, 6, 7), (0, 1, 5, 4),
             (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    mesh.from_pydata(verts, [], faces)
    mesh.update()

    obj = bpy.data.objects.new("JNX_MIST", mesh)
    obj.location = ((x0 + x1) / 2, (y0 + y1) / 2, water_z - 4.0 + hz)
    obj.display_type = "WIRE"
    obj.hide_select = True
    scene.collection.objects.link(obj)

    material = bpy.data.materials.new("JNX_MAT_mist")
    material.use_nodes = True
    material.node_tree.nodes.clear()
    graph = _Graph(material.node_tree)
    output = graph.add("ShaderNodeOutputMaterial", column=6)
    scatter = graph.add("ShaderNodeVolumeScatter", column=4)
    graph.value(scatter, "Color", spec["mist_k"] + (1.0,))
    # Forward scattering: mist glows where a lantern sits behind it.
    graph.value(scatter, "Anisotropy", 0.55)
    graph.link(scatter, "Volume", output, "Volume")

    split, _ = _world_z(graph, column=-4, row=0.0)
    ramp = _map_range(graph, water_z - 2.0, top, 1.0, 0.0,
                      column=-1, row=0.0)
    graph.link(split, "Z", ramp, "Value")
    # Drifting banks rather than a uniform grey wash.
    drift = _noise(graph, 0.010, detail=5.0, roughness=0.6, column=-2, row=-2.0)
    drift_range = _map_range(graph, 0.35, 0.68, 0.45, 1.5, column=-1, row=-2.0)
    graph.link(drift, "Fac", drift_range, "Value")
    mixed = _math(graph, "MULTIPLY", column=1, row=0.0)
    graph.link(ramp, "Result", mixed, 0)
    graph.link(drift_range, "Result", mixed, 1)
    scaled = _math(graph, "MULTIPLY", b=density, column=2, row=0.0)
    graph.link(mixed, "Value", scaled, 0)
    graph.link(scaled, "Value", scatter, "Density")

    mesh.materials.append(material)
    return obj


def build_lighting(scene, mood="drizzle"):
    """Cold moon shapes the form; the only warm light is the lantern geometry.

    The first pass used a warm 2.6-strength sun plus a daylight fill, which read
    as bright overcast noon and left nothing for the 144 emissive lanterns to do.
    Here the moon is the single key and the fill is a dim upward bounce standing
    in for light coming back off wet paving, not a second source.
    """
    import bpy

    spec = mood_spec(mood)

    moon_data = bpy.data.lights.new("JNX_Moon", "SUN")
    moon_data.energy = spec["moon_energy"]
    # A wide angular diameter keeps shadow edges soft, as if through cloud.
    moon_data.angle = math.radians(spec["moon_angle"])
    moon_data.color = spec["moon_k"]
    moon = bpy.data.objects.new("JNX_Moon", moon_data)
    scene.collection.objects.link(moon)
    moon.rotation_euler = (math.radians(spec["moon_elev"]), 0.0,
                           math.radians(spec["moon_azim"]))

    # Faint bounce from below so undersides of eaves and hulls are not pure black.
    bounce_data = bpy.data.lights.new("JNX_Bounce", "SUN")
    bounce_data.energy = spec["bounce"]
    bounce_data.angle = math.radians(70.0)
    bounce_data.color = (0.50, 0.60, 0.74)
    bounce = bpy.data.objects.new("JNX_Bounce", bounce_data)
    scene.collection.objects.link(bounce)
    bounce.rotation_euler = (math.radians(-64.0), 0.0, math.radians(30.0))

    # Warm intimate point light hanging inside Tingyuxuan pavilion (D07)
    tingyu_lamp_data = bpy.data.lights.new("JNX_Tingyu_Lamp", "POINT")
    tingyu_lamp_data.energy = 85.0
    tingyu_lamp_data.shadow_soft_size = 0.25
    tingyu_lamp_data.color = (1.0, 0.62, 0.28)
    tingyu_lamp = bpy.data.objects.new("JNX_Tingyu_Lamp", tingyu_lamp_data)
    scene.collection.objects.link(tingyu_lamp)
    tingyu_lamp.location = (80.5, 46.5, 5.75)

    return moon, bounce


# --------------------------------------------------------------------------
# cameras
# --------------------------------------------------------------------------

def _look_at(obj, target):
    from mathutils import Vector

    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def build_cameras(scene, shots):
    """Create every requested shot; returns name -> camera object."""
    import bpy

    cameras = {}
    for shot in shots:
        data = bpy.data.cameras.new(shot["name"])
        if shot.get("ortho"):
            data.type = "ORTHO"
            data.ortho_scale = shot.get("ortho_scale", 900.0)
        else:
            data.lens = shot.get("lens", 35.0)
        data.clip_start = 0.1
        data.clip_end = 6000.0
        if shot.get("dof_distance"):
            data.dof.use_dof = True
            data.dof.focus_distance = shot["dof_distance"]
            data.dof.aperture_fstop = shot.get("fstop", 2.8)
        camera = bpy.data.objects.new(shot["name"], data)
        scene.collection.objects.link(camera)
        camera.location = shot["location"]
        _look_at(camera, shot["target"])
        cameras[shot["name"]] = camera
    return cameras


def configure_render(scene, samples=96, resolution=(1600, 900), denoise=True):
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = denoise
    scene.cycles.max_bounces = 8
    scene.cycles.diffuse_bounces = 3
    scene.cycles.glossy_bounces = 4
    scene.cycles.transmission_bounces = 4
    scene.cycles.volume_bounces = 2
    scene.cycles.volume_step_rate = 4.0
    scene.cycles.volume_max_steps = 256
    scene.cycles.use_fast_gi = True
    scene.render.resolution_x, scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "AgX"
    try:
        scene.view_settings.look = "AgX - Medium Contrast"
    except TypeError:
        # Look names differ between 4.x point releases; the transform matters more.
        pass
    return scene


# --------------------------------------------------------------------------
# assembly
# --------------------------------------------------------------------------

def _smooth_by_angle(data, threshold):
    """Shade smooth, then re-sharpen edges over ``threshold`` radians.

    Blender 4.1 removed mesh auto-smooth, so the split-normal decision is baked
    into edge flags here instead of relying on a modifier being present.
    """
    import bmesh

    for poly in data.polygons:
        poly.use_smooth = True
    bm = bmesh.new()
    bm.from_mesh(data)
    for edge in bm.edges:
        if len(edge.link_faces) == 2 and edge.calc_face_angle() > threshold:
            edge.smooth = False
    bm.to_mesh(data)
    bm.free()
    data.update()


def _mesh_for(cache, builder, key, variant, smooth, materials):
    """One mesh datablock per (geometry, shader, shading) triple.

    The kernel already deduplicates geometry, but two objects sharing geometry
    can resolve to different shaders, and a mesh datablock carries its own
    material slot. Keying the cache on all three keeps instancing without
    letting a sign steal a wall's plaster.
    """
    import bpy

    ident = (key, variant, smooth)
    if ident in cache:
        return cache[ident]
    source = builder.meshes[key]
    data = bpy.data.meshes.new(f"JNX_MESH_{key}_{variant}")
    data.from_pydata(source.vertices, [], source.faces)
    data.validate(verbose=False)
    data.update()
    data.materials.append(materials[variant])
    if smooth:
        _smooth_by_angle(data, math.radians(38.0))
    cache[ident] = data
    return data


def _planned_bounds(builder, pad=110.0):
    """Planning-area extent in XY, derived from instance roots."""
    xs = [r["location"][0] for r in builder.roots.values()]
    ys = [r["location"][1] for r in builder.roots.values()]
    return (min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)


def _hero_district(builder, config):
    """Centre of the district worth a close shot: the densest one."""
    if config:
        pick = max(config["districts"], key=lambda d: d["building_count"])
        return pick["id"], tuple(pick["center"])
    counts, sums = {}, {}
    for spec in builder.roots.values():
        d = spec["district"]
        if d == "WORLD":
            continue
        counts[d] = counts.get(d, 0) + 1
        sx, sy = sums.get(d, (0.0, 0.0))
        sums[d] = (sx + spec["location"][0], sy + spec["location"][1])
    best = max(counts, key=lambda d: counts[d])
    n = counts[best]
    return best, (sums[best][0] / n, sums[best][1] / n)


def _channels(config):
    """Water centrelines, derived from the district grid.

    Land parcels are cut to an 84 x 80 envelope, so the gaps between adjacent
    district centres are open water. Returning the midlines lets the eye-level
    cameras stand in a canal instead of at a coordinate that happened to look
    plausible on paper.
    """
    xs = sorted({float(d["center"][0]) for d in config["districts"]})
    ys = sorted({float(d["center"][1]) for d in config["districts"]})
    vx = [(a + b) / 2 for a, b in zip(xs, xs[1:])]
    hy = [(a + b) / 2 for a, b in zip(ys, ys[1:])]
    return vx, hy


def _world_aabbs(builder, skip=frozenset({
        "water", "leaf", "willow_leaf", "moss", "lantern_paper"})):
    """World-space bounding boxes of solid geometry, for camera clearance.

    Foliage and the water slab are skipped: a camera brushing a willow canopy is
    wanted foreground, a camera inside a wall is not.
    """
    boxes = []
    for item in builder.objects:
        if item["material"] in skip:
            continue
        root = builder.roots[item["root"]]
        rx, ry, rz = root["location"]
        ox, oy, oz = item["location"]
        ra = root["rotation"]
        ca, sa = math.cos(ra), math.sin(ra)
        wx = rx + ox * ca - oy * sa
        wy = ry + ox * sa + oy * ca
        wz = rz + oz
        ta = ra + item["rotation"]
        ct, st = math.cos(ta), math.sin(ta)
        verts = builder.meshes[item["mesh"]].vertices
        if not verts:
            continue
        x0 = y0 = z0 = 1e18
        x1 = y1 = z1 = -1e18
        for vx, vy, vz in verts:
            px = wx + vx * ct - vy * st
            py = wy + vx * st + vy * ct
            pz = wz + vz
            if px < x0: x0 = px
            if px > x1: x1 = px
            if py < y0: y0 = py
            if py > y1: y1 = py
            if pz < z0: z0 = pz
            if pz > z1: z1 = pz
        boxes.append((x0, y0, z0, x1, y1, z1))
    return boxes


def _blocked(boxes, point, margin=1.1):
    x, y, z = point
    for x0, y0, z0, x1, y1, z1 in boxes:
        if (x0 - margin <= x <= x1 + margin and y0 - margin <= y <= y1 + margin
                and z0 - margin <= z <= z1 + margin):
            return True
    return False


def _clear_shots(builder, shots):
    """Pull any perspective camera that starts inside solid geometry back out.

    The first render put JNX_Canal_Hero inside a plaster wall and returned a
    frame that was 100% wall, so shot positions are now verified against real
    geometry rather than trusted. Orthographic shots sit far outside the model
    and are left alone.
    """
    boxes = _world_aabbs(builder)
    out = []
    for shot in shots:
        if shot.get("ortho"):
            out.append(shot)
            continue
        loc = tuple(float(v) for v in shot["location"])
        tgt = tuple(float(v) for v in shot["target"])
        if not _blocked(boxes, loc):
            out.append(shot)
            continue
        dx, dy, dz = (loc[0] - tgt[0], loc[1] - tgt[1], loc[2] - tgt[2])
        norm = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0
        dx, dy, dz = dx / norm, dy / norm, dz / norm
        fixed = None
        for lift in (0.0, 2.5, 6.0):
            for step in range(1, 41):
                cand = (loc[0] + dx * step * 2.0,
                        loc[1] + dy * step * 2.0,
                        loc[2] + dz * step * 2.0 + lift)
                if not _blocked(boxes, cand):
                    fixed = cand
                    break
            if fixed:
                break
        shot = dict(shot)
        shot["location"] = fixed or (loc[0], loc[1], loc[2] + 30.0)
        out.append(shot)
    return out


def _shots(builder, config, water_z):
    """Overview plus eye-level shots that test the things we rebuilt.

    The close shots stand in the canal midlines and look along them, so the
    frame is built out of receding banks, quays, bridges and lantern light
    rather than a single facade filling the lens.
    """
    x0, y0, x1, y1 = _planned_bounds(builder, pad=40.0)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    span = max(x1 - x0, y1 - y0)
    hero_id, (hx, hy) = _hero_district(builder, config)

    if config:
        vx, hz = _channels(config)
    else:
        vx, hz = [], []
    # Canal nearest the hero district, and the cross canal beside it.
    lane_y = min(hz, key=lambda v: abs(v - hy)) if hz else hy - 90.0
    lane_x = min(vx, key=lambda v: abs(v - hx)) if vx else hx + 90.0

    return [
        dict(name="JNX_Overview", ortho=True, ortho_scale=span * 1.15,
             location=(cx + span * 0.55, cy - span * 0.62, span * 0.55),
             target=(cx, cy, 6.0)),
        # Boat height in the canal, looking along it: eave curve, wet plaster,
        # quay steps and the bridge all stack up in depth. The bridge over this
        # canal sits at the hero district's x, ~46 m ahead, framing the shot.
        dict(name="JNX_Canal_Hero", lens=35.0,
             location=(hx - 46.0, lane_y - 3.2, water_z + 2.3),
             target=(hx + 62.0, lane_y + 1.5, water_z + 5.2),
             dof_distance=48.0, fstop=3.2),
        # The cross canal, aimed back at the town so the far bank recedes into
        # mist: this is the shot that tells us whether depth is reading.
        dict(name="JNX_Water_Level", lens=50.0,
             location=(lane_x - 2.0, lane_y - 112.0, water_z + 2.0),
             target=(lane_x + 1.0, lane_y + 40.0, water_z + 6.0),
             dof_distance=90.0, fstop=4.0),
        # Inside the hero district at walking height, down the spine street:
        # this is the "can you stand here" test the brief asks for.
        dict(name="JNX_Lane", lens=40.0, district=hero_id,
             location=(hx - 64.0, hy + 2.0, 3.7),
             target=(hx + 60.0, hy - 1.0, 5.4),
             dof_distance=34.0, fstop=2.8),
        # Central garden showcase in D07: Tingyuxuan pavilion, moon gate, leaning plum and distant mountains
        dict(name="JNX_TingYuXuan", lens=42.0,
             location=(88.5, 34.0, 3.4),
             target=(91.4, 53.5, 4.5),
             dof_distance=20.0, fstop=3.0),
        # Close artistic framing: gazing through the circular moon gate into borrowed landscape
        dict(name="JNX_MoonGate_Vista", lens=52.0,
             location=(91.0, 42.5, 3.2),
             target=(91.4, 60.0, 4.2),
             dof_distance=12.0, fstop=2.6),
    ]


def write_blend(builder, folder, preview=False, config=None, mood="drizzle",
                samples=96):
    """Assemble the layer-3 scene: shaders, atmosphere, lighting, cameras.

    Writes only this scene's dependency graph, so the user's legacy main file is
    never opened or saved.
    """
    import bpy

    water_z = float(config.get("water_z", 0.0)) if config else 0.0
    scene = bpy.data.scenes.new("JNX_Expansion_v2")
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene["stage"] = "detail"
    scene["legacy_imported"] = False
    scene["seed"] = builder.seed

    collections = {}
    for district in sorted({r["district"] for r in builder.roots.values()}):
        col = bpy.data.collections.new("JNX_" + district)
        scene.collection.children.link(col)
        collections[district] = col

    materials = build_materials()

    roots = {}
    for key, spec in builder.roots.items():
        col = collections[spec["district"]]
        obj = bpy.data.objects.new(key, None)
        col.objects.link(obj)
        obj.location = spec["location"]
        obj.rotation_euler.z = spec["rotation"]
        obj.empty_display_size = 0.6
        for tag in ("family", "district", "task", "status"):
            obj[tag] = spec[tag]
        roots[key] = obj
        for s in spec["sockets"]:
            socket = bpy.data.objects.new(key + "__SOCKET_" + s["name"], None)
            col.objects.link(socket)
            socket.parent = obj
            socket.location = s["location"]
            socket.empty_display_type = "ARROWS"
            socket.empty_display_size = 0.4
            socket.hide_render = True
            socket["direction"] = s["direction"]

    cache = {}
    for item in builder.objects:
        variant = resolve_slot(item["material"], item["name"])
        if variant not in materials:
            variant = item["material"]
        data = _mesh_for(cache, builder, item["mesh"], variant,
                         wants_smooth(item["name"]), materials)
        obj = bpy.data.objects.new(item["name"], data)
        parent = roots[item["root"]]
        parent.users_collection[0].objects.link(obj)
        obj.parent = parent
        obj.location = item["location"]
        obj.rotation_euler.z = item["rotation"]

    build_world(scene, mood)
    build_distant_scenery(scene, _planned_bounds(builder))
    build_mist(scene, _planned_bounds(builder), water_z=water_z, mood=mood)
    build_lighting(scene, mood)
    cameras = build_cameras(scene, _clear_shots(builder, _shots(builder, config, water_z)))
    scene.camera = cameras.get("JNX_TingYuXuan", cameras["JNX_Canal_Hero"])
    configure_render(scene, samples=samples)

    target = str((folder / "JNX_Expansion.blend").resolve())
    bpy.data.libraries.write(target, {scene}, compress=True)

    if preview:
        for name in ("JNX_TingYuXuan", "JNX_Canal_Hero", "JNX_MoonGate_Vista", "JNX_Lane", "JNX_Water_Level", "JNX_Overview"):
            scene.camera = cameras[name]
            scene.render.filepath = str((folder / f"{name}.png").resolve())
            bpy.ops.render.render(write_still=True, scene=scene.name)
    return scene
