"""Turn the world manifest into deterministic parcels and shared boundaries."""
from __future__ import annotations

from kernel import rng


def overlaps(a, b, gap=0.0):
    return (a[0] < b[2]+gap and a[2] > b[0]-gap and
            a[1] < b[3]+gap and a[3] > b[1]-gap)


def make_layout(config):
    buildings, links = [], []
    district_ids = {d["id"] for d in config["districts"]}
    if len(district_ids) != len(config["districts"]):
        raise ValueError("duplicate district id")
    for d in config["districts"]:
        x, y = d["center"]
        stream = rng(config["seed"], d["id"] + ":parcels")
        candidates = [(px,py) for py in (-60,-36,-12,12,36,60)
                      for px in (-60,-36,-12,12,36,60)
                      if not overlaps((px-10,py-10,px+10,py+10), (-34,20,34,74))]
        stream.shuffle(candidates)
        if d["building_count"] > len(candidates):
            raise ValueError(f"{d['id']}: parcel capacity exceeded")
        for i, (px, py) in enumerate(candidates[:d["building_count"]]):
            stream_i = rng(config["seed"], f"{d['id']}:building:{i}")
            family = d["building_families"][i % len(d["building_families"])]
            width = stream_i.choice((9.6, 12.8, 16.0))
            depth = stream_i.choice((8.0, 10.0, 12.0))
            buildings.append(dict(id=f"JNX_{d['id']}_BLD_{i:03d}", district=d["id"],
                                  family=family, location=[x+px,y+py,config["ground_z"]],
                                  width=width, depth=depth, floors=2 if family in ("shop","inn") else 1,
                                  rotation=0 if py > 0 else 3.141592653589793,
                                  parcel=[x+px-10,y+py-10,x+px+10,y+py+10]))
    for a in config["districts"]:
        ax, ay = a["center"]
        for b in config["districts"]:
            bx, by = b["center"]
            if (bx-ax, by-ay) not in ((180,0),(0,180)):
                continue
            horizontal = bx != ax
            links.append(dict(id=f"JNX_LINK_{a['id']}_{b['id']}", a=a["id"], b=b["id"],
                              location=[(ax+bx)/2,(ay+by)/2,config["ground_z"]],
                              span=24.0 if horizontal else 32.0, width=6.0,
                              rotation=0.0 if horizontal else 1.5707963267948966))
    return dict(buildings=buildings, links=links,
                reserved_legacy=dict(district="D07", center=[90,46], footprint=[60,48],
                                     status="reserved_not_imported"))
