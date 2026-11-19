"""Lineup sheets of every exported node (golden-hour EEVEE), straight from the export-source .blend files.

    bl assets/claimkit/lineup.py     -> previews/lineup_claimkit.png, previews/lineup_nature.png
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402

import bk  # noqa: E402
import kit  # noqa: E402

OUT = os.path.join(kit.HERE, "out")


def sheet(blend, rows, png, cam, tgt, lens, res):
    bk.reset()
    with bpy.data.libraries.load(blend, link=False) as (src, dst):
        dst.objects = list(src.objects)
    roots = {o.name: o for o in dst.objects if o is not None and o.parent is None}

    def link(o):
        bpy.context.scene.collection.objects.link(o)
        for c in o.children:
            link(c)

    for row in rows:
        for name, x, y, yaw in row:
            o = roots[name]
            link(o)
            o.location = (x, y, 0)
            o.rotation_euler = (0, 0, math.radians(yaw))
    kit.preview_materials()
    kit.golden_rig(sun_elev=14.0, sun_az=-35.0, sun_power=6.0, sky_strength=0.25, ground_size=900, look="AgX - Punchy")
    bpy.data.lights["_pv_sun"].color = bk.hex_lin("#ffb46a")[:3]
    kit.camera(cam, tgt, lens)
    kit.render(os.path.join(kit.PREV, png), res=res, samples=64)


# claim kit: back row big structures, middle row buildings, front row props (fronts face the camera, -Y)
sheet(os.path.join(OUT, "claim-kit.blend"), [
    [("portal", -40, 16, 0), ("mill", -19, 18, 0), ("headframe_steel", -4, 18, 0), ("headframe_wood", 8, 18, 0), ("conveyor", 20, 16, -90)],
    [("shack", -31, 2, 0), ("hoist_house", -22, 2, 0), ("ore_bin", -13, 2, 0), ("sign_company", -4, 2, 0), ("sign_forsale", 3, 2, 0),
     ("lamp_post", 8, 2, 0), ("fuel_tank_small", 13, 2, 0)],
    [("ore_cart", -14, -8, 0), ("pile_coal", -9, -8, 0), ("pile_rock", -3, -8, 0), ("fence_2m", 2, -8, 0), ("crates", 6.5, -8, 0)],
], "lineup_claimkit.png", (-8, -62, 17), (-8, 6, 5.5), 30, (2400, 1200))

sheet(os.path.join(OUT, "nature.blend"), [
    [("pine_a", -16, 10, 0), ("pine_b", -5, 10, 0), ("pine_c", 4, 10, 0), ("pine_dead", 11, 10, 0)],
    [("boulder_c", -14, 0, 0), ("boulder_b", -8, 0, 0), ("boulder_a", -4, 0, 0), ("rock_cluster", 2, 0, 0), ("log_pile", 8, 0, 0)],
    [("bush_a", -10, -6, 0), ("bush_b", -6, -6, 0), ("stump", -2.5, -6, 0), ("grass_tuft", 0.5, -6, 0)],
], "lineup_nature.png", (-2, -40, 9), (-2, 3, 5.0), 30, (2400, 1200))
