"""Build the water grid, twelve land tiles and continuous cross-shaped paths."""


def build(builder, config):
    ground = config["ground_z"]
    root = builder.root("JNX_WORLD_WATER", "canal_network", "WORLD", (0,0,0),
                        task="tasks/systems/S01_water_network.md")
    builder.box(root, "water", (720,540,.15), (0,0,-.075), "water")
    builder.socket(root, "water_datum", (0,0,0), (0,0,1))
    for d in config["districts"]:
        x,y = d["center"]
        r = builder.root(f"JNX_{d['id']}_GROUND", "terrain", d["id"], (x,y,0),
                         task=f"tasks/districts/{d['id']}.md")
        builder.box(r, "land", (168,160,3.5), (0,0,ground-1.75), "earth")
        builder.box(r, "path_ew", (168,6,.12), (0,0,ground+.06), "stone")
        builder.box(r, "path_ns", (6,160,.12), (0,0,ground+.061), "stone")
        # Separate quay bands preserve the wet edge as a future refinement seam.
        for side in (-1,1):
            builder.box(r, f"quay_x_{side}", (2.5,160,ground+.4),
                        (side*82.75,0,(ground-.4)/2), "stone")
            builder.box(r, f"quay_y_{side}", (163,2.5,ground+.4),
                        (0,side*78.75,(ground-.4)/2), "stone")
        for label, pos, direction in (
            ("west",(-84,0,ground),(-1,0,0)),("east",(84,0,ground),(1,0,0)),
            ("south",(0,-80,ground),(0,-1,0)),("north",(0,80,ground),(0,1,0))):
            builder.socket(r, "road_"+label, pos, direction)
