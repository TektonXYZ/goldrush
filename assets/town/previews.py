"""Preview renders for town.glb nodes (EEVEE, golden hour, sun low in the west).
Each node: a 3/4 front shot. Vignettes lay several nodes out like the real town."""
import math
import os

import bpy

import pv

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "previews")

# node: (camera location, target, lens) with the node at the origin, front facing -Y
SHOTS = {
    "land_office": ((-10.5, -19.0, 2.4), (0.6, -1.5, 4.6), 30),
    "assay_office": ((-9.5, -17.0, 2.2), (0.5, -1.0, 4.2), 30),
    "general_store": ((-11.0, -19.5, 2.3), (0.6, -1.5, 4.6), 30),
    "saloon": ((-11.0, -20.0, 2.4), (0.6, -1.5, 5.0), 30),
    "depot": ((-17.0, 21.0, 3.2), (2.0, -1.5, 2.6), 30),
    "gas_station": ((-21.0, -22.0, 3.0), (0.0, 0.0, 3.0), 28),
    "monument": ((-7.5, -10.5, 1.7), (0.0, 0.0, 3.4), 32),
    "locomotive": ((-8.0, -12.5, 2.3), (0.0, -2.6, 1.9), 32),
    "coach": ((7.0, -9.0, 1.8), (0.0, 0.0, 1.9), 32),
    "boxcar": ((6.0, -8.0, 1.8), (0.0, 0.0, 1.8), 32),
    "track_10m": ((4.0, -5.0, 1.6), (0.0, 0.0, 0.2), 32),
    "water_tower": ((-9.0, -12.0, 2.0), (0.0, 0.0, 6.0), 28),
    "windmill": ((-8.0, -11.0, 1.8), (0.0, 0.0, 6.0), 28),
}


def _show_only(roots, keep):
    for n, r in roots.items():
        hide = n not in keep
        for o in [r] + list(r.children_recursive):
            o.hide_render = hide


def single(roots, n):
    if n not in roots:
        return
    for r in roots.values():
        r.location = (0, 0, 0)
    _show_only(roots, {n})
    pv.stage()
    loc, tgt, lens = SHOTS.get(n, ((-6.0, -8.0, 1.8), (0.0, 0.0, 0.8), 35))
    pv.camera(loc, tgt, lens)
    pv.render(os.path.join(OUT, f"{n}.png"))


def props_lineup(roots):
    names = [n for n in ("street_lamp", "bench", "barrels", "hitching_post", "telegraph_pole", "boardwalk_4m",
                         "wagon", "buffer_stop") if n in roots]
    if not names:
        return
    x = 0.0
    for n in names:
        roots[n].location = (x, 0, 0)
        x += 4.5
    _show_only(roots, set(names))
    pv.stage()
    pv.camera((x / 2 - 2.5, -24.0, 4.0), (x / 2 - 2.5, 0, 1.7), 26)
    pv.render(os.path.join(OUT, "props.png"))


def street(roots):
    """Main Street: two shops each side, street 18 m wide, looking east from the depot end."""
    names = {"land_office": (0, 16, 0), "assay_office": (18, 16, 0), "general_store": (0, -16, 180),
             "saloon": (18, -16, 180)}
    keep = set()
    for n, (x, y, yaw) in names.items():
        if n in roots:
            r = roots[n]
            r.location = (x, y, 0)
            r.rotation_euler = (0, 0, math.radians(yaw))
            keep.add(n)
    for n in ("street_lamp", "hitching_post", "wagon", "telegraph_pole", "barrels"):
        if n in roots:
            keep.add(n)
    if "street_lamp" in roots:
        roots["street_lamp"].location = (9.0, 8.2, 0)
    if "hitching_post" in roots:
        roots["hitching_post"].location = (-3.0, 8.0, 0)
    if "wagon" in roots:
        roots["wagon"].location = (12.0, -4.0, 0)
        roots["wagon"].rotation_euler = (0, 0, math.radians(80))
    if "telegraph_pole" in roots:
        roots["telegraph_pole"].location = (27.0, 8.6, 0)
    if "barrels" in roots:
        roots["barrels"].location = (6.0, -8.6, 0)
    _show_only(roots, keep)
    pv.stage(sun_from=(-0.97, -0.1), sun_el=9.0)
    pv.camera((-16.0, 1.5, 1.75), (14.0, 0.0, 3.4), 28)
    pv.render(os.path.join(OUT, "street.png"))
    for n in keep:
        roots[n].location = (0, 0, 0)
        roots[n].rotation_euler = (0, 0, 0)


def depot_train(roots):
    keep = set()
    if "depot" in roots:
        keep.add("depot")
    # track along X behind the platform; rolling stock faces +x (rotated -90 from its -y front)
    track_y = 5.15
    for i in range(-3, 4):
        if "track_10m" in roots and i == 0:
            pass
    extra = []
    if "track_10m" in roots:
        keep.add("track_10m")
        t = roots["track_10m"]
        t.location = (0, track_y, 0)
        for k in range(-4, 5):
            if k == 0:
                continue
            c = t.copy()
            bpy.context.scene.collection.objects.link(c)
            c.location = (k * 10.0, track_y, 0)
            extra.append(c)
    rail_top = 0.47
    xs = {"locomotive": 10.0, "coach": -9.0, "boxcar": -24.0}
    for n, x in xs.items():
        if n in roots:
            keep.add(n)
            roots[n].location = (x, track_y, rail_top)
            roots[n].rotation_euler = (0, 0, math.radians(90))
    _show_only(roots, keep)
    pv.stage(sun_from=(-0.9, 0.4), sun_el=10.0)
    pv.camera((-26.0, 2.4, 2.35), (8.0, 4.4, 2.2), 24)
    pv.render(os.path.join(OUT, "depot_train.png"))
    pv.camera((-14.0, 26.0, 7.5), (0.0, 2.0, 1.5), 28)
    pv.render(os.path.join(OUT, "depot_train_wide.png"))
    for c in extra:
        bpy.data.objects.remove(c, do_unlink=True)
    for n in keep:
        roots[n].location = (0, 0, 0)
        roots[n].rotation_euler = (0, 0, 0)


def run(roots, which="all"):
    pv.upgrade_materials()
    want = None if which == "all" else set(which.split(","))
    for n in roots:
        if want is None or n in want:
            single(roots, n)
    if want is None or "props" in want:
        props_lineup(roots)
    if want is None or "street" in want:
        street(roots)
    if want is None or "depot_train" in want:
        depot_train(roots)
    _show_only(roots, set(roots))
