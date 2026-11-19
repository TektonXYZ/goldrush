"""Depth-4 claim vignette: the exported kits assembled on a 22 x 18 m pad against a terrace rock wall, golden hour.

    bl assets/claimkit/vignette.py            -> assets/claimkit/previews/vignette_{wide,close,far}.png

Appends the clean (export-source) nodes from out/claim-kit.blend + out/nature.blend, so what you see is what the
game gets (plus the preview-only procedural shading the game replaces with its texture library).
Pad centre = origin, the town is toward -Y; the portal sits at the back edge (y = +9), the sign at the front edge.
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bmesh  # noqa: E402
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import bk  # noqa: E402
import kit  # noqa: E402
from kit import MB, fbm3, smoothstep  # noqa: E402

bk.reset()
OUT = os.path.join(kit.HERE, "out")
POOL = {}


def load(blend):
    with bpy.data.libraries.load(blend, link=False) as (src, dst):
        dst.objects = list(src.objects)
    for o in dst.objects:
        if o is not None and o.parent is None:
            POOL[o.name] = o


load(os.path.join(OUT, "claim-kit.blend"))
load(os.path.join(OUT, "nature.blend"))
USED = set()


def link_tree(o):
    bpy.context.scene.collection.objects.link(o)
    for c in o.children:
        link_tree(c)


def copy_tree(o, parent=None):
    c = o.copy()
    if parent is not None:
        c.parent = parent
    bpy.context.scene.collection.objects.link(c)
    for ch in o.children:
        copy_tree(ch, c)
    return c


def inst(name, loc, yaw=0.0):
    src = POOL[name]
    if name not in USED:
        USED.add(name)
        link_tree(src)
        o = src
    else:
        o = copy_tree(src)
    o.location = loc
    o.rotation_euler = (0, 0, math.radians(yaw))
    return o


# ---------------------------------------------------------------- the claim (nothing crosses the portal axis)
inst("portal", (0, 9.0, 0))
inst("sign_company", (0, -7.8, 0))
inst("mill", (-6.5, -0.5, 0))
inst("shack", (-6.0, -8.0, 0))
inst("headframe_steel", (4.0, -4.5, 0), -90)
inst("hoist_house", (14.25, -4.5, 0), -90)
inst("conveyor", (7.8, 0.3, 0), 180)
inst("ore_bin", (7.8, -7.6, 0), 180)
inst("pile_rock", (7.9, 7.2, 0), -30)
inst("ore_cart", (0, 3.6, 0))
inst("pile_coal", (-2.8, 6.4, 0), 20)
inst("lamp_post", (2.7, -8.5, 0), 180)
inst("crates", (-1.3, -6.7, 0), 25)
inst("fuel_tank_small", (10.6, 1.5, 0), 90)
for x in (-1.0 - 2 * k for k in range(1)):
    pass
for x in (-10.0,):
    inst("fence_2m", (x, -9.4, 0))
for x in (5.0, 7.0, 9.0, 11.0):
    inst("fence_2m", (x, -9.4, 0))

# ---------------------------------------------------------------- nature dressing
rng = random.Random(4)
for n, p, yaw in (("pine_a", (-15.5, 5.0), 10), ("pine_b", (-19.5, -3.0), 80), ("pine_c", (-13.2, -12.5), 30),
                  ("pine_a", (17.5, 8.5), 200), ("pine_b", (21.0, -12.0), 140), ("pine_c", (-23.0, 10.0), 60),
                  ("pine_dead", (19.5, 2.0), 0), ("pine_b", (-9.0, 16.5), 250), ("pine_a", (7.5, 19.0), 120),
                  ("pine_c", (-17.5, 14.0), 300), ("pine_c", (13.5, 15.0), 90)):
    z = 0.0 if p[1] < 12 else 19.2
    inst(n, (p[0], p[1], z), yaw)
for n, p, yaw in (("boulder_b", (-12.5, -6.5), 40), ("boulder_a", (-10.6, 7.6), 10), ("boulder_c", (17.5, -14.0), 75),
                  ("boulder_a", (12.6, 1.2), 200), ("rock_cluster", (-17.0, 1.5), 0), ("boulder_b", (24.0, 4.0), 130)):
    inst(n, (p[0], p[1], 0), yaw)
for n, p in (("bush_a", (-11.5, -9.0)), ("bush_b", (12.2, -10.0)), ("bush_a", (-14.0, 2.5)), ("bush_b", (15.5, -3.0)),
             ("bush_b", (-8.5, 7.8)), ("stump", (-12.0, -1.5)), ("log_pile", (-15.0, -8.5))):
    inst(n, (p[0], p[1], 0), rng.uniform(0, 360))
for i in range(40):
    a = rng.uniform(0, math.tau)
    r = rng.uniform(11.5, 22)
    x, y = math.cos(a) * r * 1.1, math.sin(a) * r * 0.8 - 2
    if y > 9.5:
        continue
    inst("grass_tuft", (x, y, 0), rng.uniform(0, 360))
    o = bpy.context.scene.objects[-1]

# ---------------------------------------------------------------- terrace wall behind the pad (+ the slope above)
mb = MB("_vig_wall", seed=9)
xs = [-48 + i * 0.6 for i in range(161)]
zs = [0.0]
z = 0.0
P = {}
while z < 19.5:
    t = random.Random(int(z * 10)).uniform(0.5, 1.4)
    zs += [z + 0.03, z + t * 0.5]
    P[len(zs)] = random.Random(int(z * 7)).uniform(-0.35, 0.35)
    z += t
zs = sorted(set(round(v, 3) for v in zs if v < 19.5)) + [19.6]


def wall_y(x, zz, li):
    base = 10.7 + 0.55 * fbm3((x * 0.07, zz * 0.07, 3.0), 3) + 0.06 * zz
    # the terrain must stay out of the portal's tunnel stub: push the wall ~4 m behind the portal origin there
    base += 2.6 * (1 - smoothstep(6.5, 10.5, abs(x))) * (1 - smoothstep(11.0, 14.0, zz))
    layer = random.Random(li * 31 + int((x + 60) / 3.1)).uniform(-0.55, 0.55)
    bed = random.Random(li * 7).uniform(-0.35, 0.35)
    return base - layer - bed - 0.22 * fbm3((x * 0.6, zz * 0.6, 7.0), 2)


verts, faces = [], []
for j, zz in enumerate(zs):
    li = sum(1 for v in zs if v <= zz)
    for i, x in enumerate(xs):
        top = zz if j < len(zs) - 1 else zz + 1.4 * fbm3((x * 0.1, 1.0, 2.0), 3)
        verts.append((x, wall_y(x, zz, li // 2), top))
nx_ = len(xs)
for j in range(len(zs) - 1):
    for i in range(nx_ - 1):
        a = j * nx_ + i
        faces.append((a, a + 1, a + nx_ + 1, a + nx_))
mb.mesh(verts, faces, "rock")
# slope above the wall top, rising to the mountains
sv, sf = [], []
rows = 12
for j in range(rows):
    for i, x in enumerate(xs[::4]):
        y = 11.0 + j * 4.0 + 0.6 * fbm3((x * 0.05, j * 0.3, 5.0), 2)
        zz = 19.4 + j * 1.6 + 1.5 * fbm3((x * 0.04, j * 0.2, 8.0), 3)
        sv.append((x, y, zz))
nx2 = len(xs[::4])
for j in range(rows - 1):
    for i in range(nx2 - 1):
        a = j * nx2 + i
        sf.append((a, a + 1, a + nx2 + 1, a + nx2))
mb.mesh(sv, sf, "dirt")
wall = mb.finish(smooth=35, weighted=False)
kit.bake_grime([wall], distance=2.0, samples=32, floor=0.4, ground=True)

# ---------------------------------------------------------------- look + shots
kit.preview_materials()
kit.preview_signs([(bpy.data.objects["sign_face"], "preview_signface.png"), (bpy.data.objects["plaque_face"], "preview_plaque.png")])
kit.golden_rig(sun_elev=9.0, sun_az=-32.0, sun_power=7.0, sky_strength=0.2, ground_size=900, look="AgX - Punchy")
bpy.data.lights["_pv_sun"].color = bk.hex_lin("#ffaa58")[:3]
s = bpy.context.scene
s.eevee.use_shadows = True
pad = bpy.data.meshes.new("_pv_pad")
pad.from_pydata([(-11, -9, 0.004), (11, -9, 0.004), (11, 9, 0.004), (-11, 9, 0.004)], [], [(0, 1, 2, 3)])
po = bpy.data.objects.new("_pv_pad", pad)
s.collection.objects.link(po)
pm = bk.mat("_pv_pad_mat", "#8a7e6c", rough=0.95)
pad.materials.append(pm)
shots = [
    ("vignette_wide", (-2.0, -34.0, 10.0), (1.0, 3.0, 4.2), 28, (1920, 1080)),
    ("vignette_close", (0.9, -0.8, 1.75), (0.0, 9.0, 2.9), 30, (1600, 1000)),
    ("vignette_far", (-38.0, -135.0, 14.0), (0.0, 0.0, 8.0), 50, (1600, 1000)),
    ("vignette_right", (22.0, -24.0, 5.5), (3.0, 0.0, 6.0), 30, (1600, 1000)),
]
for name, cam, tgt, lens, res in shots:
    kit.camera(cam, tgt, lens)
    kit.render(os.path.join(kit.PREV, f"{name}.png"), res=res, samples=64)
