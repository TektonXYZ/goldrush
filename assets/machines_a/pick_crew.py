"""Gulch Labor Co. Pick & Barrow Crew (MOTHERLODE machines-A, depth 1 / tier 1).

No machine: a hand-mining setup at a coal face. A heap of glossy broken coal against the face, a dented steel-tray
wheelbarrow with a pneumatic tyre and wooden handles, a wooden coal tub on short 0.6 m-gauge rails (heaped with
coal), a crate with a spare shovel and pick leaning on it, a lantern hanging from a timber prop over the crate and a
galvanized water can. Two animated miners stand at crew_0 / crew_1 (the game places characters/miner.glb there).

    systemd-run --user --scope -q -p MemoryMax=3G -p MemorySwapMax=0 \
        bl assets/machines_a/pick_crew.py -- public/models/machines/pick_crew [--no-render] [--one]
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
from lib import V, aim, frame  # noqa: E402
from mathutils import Quaternion, noise  # noqa: E402

stem, flags = lib.args()
m = lib.Machine("pick_crew")
rng = random.Random(11)

# ------------------------------------------------------------------ decals
A_ = m.atlas
A_.add("gulch", 900, 160, lib.svg_text("GULCH LABOR CO.", font="Saira Stencil One", fill="#E9E5DA", wear=0.6,
                                       seed=7), fit=True)
A_.add("no3", 300, 160, lib.svg_text("No 3", font="Saira Stencil One", fill="#E9E5DA", wear=0.6, seed=9), fit=True)
A_.add("crate", 900, 160, lib.svg_text("GULCH LABOR CO.", font="Saira Stencil One", fill="#1A1A1A", wear=0.55,
                                       seed=13), fit=True)
A_.add("thisup", 600, 140, lib.svg_text("THIS SIDE UP", font="Barlow Condensed Black", fill="#1A1A1A", wear=0.55,
                                        seed=17), fit=True)
A_.add("water", 500, 140, lib.svg_text("DRINKING WATER", font="Barlow Condensed Black", fill="#1A1A1A", wear=0.4,
                                       seed=19), fit=True)
A_.build()

FACE_Y = -3.78     # toe of the coal heap at the face (the face itself is the mine's rock, not modelled here)
body = m.part("pick_crew_body")
coal = m.part("pick_crew_coal")
coal.sharp = 12.0  # broken coal: hard facets

# ================================================================== coal heap at the face
# base mound: a faceted, noise-displaced half-dome hugging the face
rings = []
NR, NA = 7, 22
for i in range(NR + 1):
    t = 0.93 * i / NR
    ring = []
    for k in range(NA):
        a = math.pi * k / (NA - 1)              # half ring: from +X round the back (+Y) to -X
        rx, ry = 1.55 * (1 - t ** 1.6), 0.62 * (1 - t ** 1.6)
        x = math.cos(a) * rx
        y = FACE_Y + 0.02 + math.sin(a) * ry
        z = 0.42 * math.sin(t * math.pi / 2) ** 0.9 * (0.75 + 0.25 * math.sin(a))
        n_ = noise.noise(V((x * 2.1, y * 2.1, z * 2.1 + 3.0)))
        ring.append((x * (1 + 0.08 * n_), y + 0.05 * n_, max(0.0, z + 0.07 * n_) if i else 0.0))
    rings.append(ring)
coal.loft(rings, mat="coal_ore", close=False, uv="box")

def on_heap(x, y):
    """Approximate heap surface height at (x, y)."""
    dx, dy = x / 1.55, (y - FACE_Y - 0.02) / 0.62
    rr = math.sqrt(dx * dx + dy * dy)
    if rr >= 1:
        return 0.0
    return 0.42 * (1 - rr ** 1.6) ** 0.8


for k in range(300):                    # lumps scattered over the heap, bigger near the face, some proud of the rim
    a = rng.uniform(0.02, math.pi - 0.02)
    rr = rng.uniform(0.0, 1.06) ** 0.6
    x = math.cos(a) * 1.55 * rr
    y = FACE_Y + 0.06 + math.sin(a) * 0.62 * rr
    size = rng.uniform(0.06, 0.17) * (1.3 - 0.55 * min(rr, 1.0))
    z = on_heap(x, y) + size * rng.uniform(0.15, 0.5)
    coal.rock(size, (x, y, z), seed=k, mat="coal_ore", detail=1 if size > 0.08 else 0, squash=(1, 0.9, 0.7),
              rough=0.3)
for k in range(26):                     # strays rolled onto the floor
    a = rng.uniform(0, math.tau)
    x = rng.uniform(-2.0, 2.0)
    y = FACE_Y + 0.8 + rng.uniform(0.0, 1.8)
    size = rng.uniform(0.03, 0.08)
    coal.rock(size, (x, y, size * 0.45), seed=500 + k, mat="coal_ore", detail=0, squash=(1, 0.9, 0.6), rough=0.3)

# ================================================================== rails + sleepers (0.6 m gauge)
RX = 1.62                                # track centre x
RY0, RY1 = -2.95, 0.75
for k in range(7):                       # sleepers
    y = RY0 + 0.15 + k * (RY1 - RY0 - 0.3) / 6
    body.box((1.05, 0.16, 0.1), c=(RX + rng.uniform(-0.02, 0.02), y, 0.05), rot=(0, 0, rng.uniform(-3, 3)),
             mat="wood_timber", bev=0.012)
    for sx in (1, -1):
        for dx in (-0.045, 0.045):
            body.cyl(0.011, 0.02, c=(RX + sx * 0.3 + dx, y, 0.105), mat="steel_dark", sides=6, bev=0)
for sx in (1, -1):                       # rails (head, web, foot)
    x = RX + sx * 0.3
    L = RY1 - RY0
    body.box((0.075, L, 0.01), c=(x, (RY0 + RY1) / 2, 0.105), mat="steel_dark", bev=0)
    body.box((0.014, L, 0.055), c=(x, (RY0 + RY1) / 2, 0.137), mat="steel_dark", bev=0)
    body.box((0.04, L, 0.024), c=(x, (RY0 + RY1) / 2, 0.176), mat="steel", bev=0.004, segs=1)
    body.box((0.03, 0.4, 0.04), c=(x + sx * 0.03, RY0 + 1.6, 0.14), mat="steel_dark", bev=0)        # fishplate
body.box((0.86, 0.22, 0.24), c=(RX, RY0 - 0.02, 0.24), mat="wood_timber", bev=0.015)            # stop block
for sx in (1, -1):
    body.box((0.1, 0.14, 0.3), c=(RX + sx * 0.38, RY0 + 0.04, 0.15), mat="wood_timber", bev=0.012)

# ================================================================== coal tub (animated: rocking as it is loaded)
TUB_Y = -1.35
TZ0, TL, TW, TH = 0.33, 1.15, 0.8, 0.62
tub = m.part("tub", origin=(RX, TUB_Y, 0.19))
for sx in (1, -1):                       # plank sides with straps
    for j in range(4):
        tub.box((0.035, TL, TH / 4 - 0.006), c=(RX + sx * (TW / 2 - 0.018), TUB_Y, TZ0 + TH / 8 + j * TH / 4),
                mat="wood_planks", bev=0.006)
    for yy in (-TL / 2 + 0.04, -0.2, 0.2, TL / 2 - 0.04):
        tub.box((0.012, 0.05, TH + 0.02), c=(RX + sx * (TW / 2 + 0.004), TUB_Y + yy, TZ0 + TH / 2), mat="steel_dark",
                bev=0)
        for zz in (0.08, TH - 0.08):
            tub.cyl(0.01, 0.01, c=(RX + sx * (TW / 2 + 0.013), TUB_Y + yy, TZ0 + zz), axis="X", mat="steel_dark",
                    sides=6, bev=0)
for sy in (1, -1):                       # plank ends
    for j in range(4):
        tub.box((TW - 0.07, 0.035, TH / 4 - 0.006), c=(RX, TUB_Y + sy * (TL / 2 - 0.018), TZ0 + TH / 8 + j * TH / 4),
                mat="wood_planks", bev=0.006)
    for xx in (-TW / 2 + 0.05, TW / 2 - 0.05):
        tub.box((0.05, 0.012, TH + 0.02), c=(RX + xx, TUB_Y + sy * (TL / 2 + 0.004), TZ0 + TH / 2), mat="steel_dark",
                bev=0)
    tub.box((0.4, 0.12, 0.14), c=(RX, TUB_Y + sy * (TL / 2 + 0.06), TZ0 + 0.12), mat="wood_timber", bev=0.012)  # buffer
    tub.rod((RX, TUB_Y + sy * (TL / 2 + 0.12), TZ0 + 0.12), (RX, TUB_Y + sy * (TL / 2 + 0.26), TZ0 + 0.12), 0.014,
            mat="steel_dark", sides=6)
    tub.lathe([(0.035, -0.01), (0.05, -0.01), (0.05, 0.01), (0.035, 0.01)], c=(RX, TUB_Y + sy * (TL / 2 + 0.29), TZ0 + 0.12),
              rot=(0, 90, 0), mat="steel_dark", sides=10, cap0=False, cap1=False)                   # coupling link
tub.box((TW, TL, 0.04), c=(RX, TUB_Y, TZ0 + 0.02), mat="wood_planks", bev=0.008)                 # floor
for sx in (1, -1):                       # top rim angle iron
    tub.box((0.05, TL + 0.05, 0.02), c=(RX + sx * (TW / 2), TUB_Y, TZ0 + TH + 0.005), mat="steel_dark", bev=0)
for sy in (1, -1):
    tub.box((TW + 0.05, 0.05, 0.02), c=(RX, TUB_Y + sy * (TL / 2), TZ0 + TH + 0.005), mat="steel_dark", bev=0)
for sy in (1, -1):                       # axles, axle boxes, flanged cast wheels
    yy = TUB_Y + sy * 0.32
    tub.cyl(0.025, 0.72, c=(RX, yy, 0.17), axis="X", mat="steel_dark", sides=8, bev=0)
    for sx in (1, -1):
        tub.box((0.09, 0.12, 0.1), c=(RX + sx * (TW / 2 - 0.02), yy, 0.27), mat="cast_iron", bev=0.008)
        with tub.at((RX + sx * 0.3, yy, 0.17), rot=(0, 90 * sx, 0)):
            tub.lathe([(0, -0.03), (0.15, -0.03), (0.17, -0.025), (0.17, -0.015), (0.15, -0.01), (0.145, 0.03),
                       (0.06, 0.035), (0, 0.035)], mat="cast_iron", sides=18, angle=30)
tub.decal("gulch", c=(RX + TW / 2 + 0.013, TUB_Y - 0.0, TZ0 + 0.42), n=(1, 0, 0), w=0.72)
tub.decal("no3", c=(RX + TW / 2 + 0.013, TUB_Y, TZ0 + 0.2), n=(1, 0, 0), w=0.18)
tub.decal("gulch", c=(RX - TW / 2 - 0.013, TUB_Y, TZ0 + 0.42), n=(-1, 0, 0), w=0.72)
tub_coal = m.part("tub_coal", origin=(RX, TUB_Y, 0.19), parent="tub")
tub_coal.sharp = 12.0
tub_coal.box((TW - 0.08, TL - 0.08, 0.02), c=(RX, TUB_Y, TZ0 + TH - 0.07), mat="coal_ore", bev=0)
for k in range(46):
    x = rng.uniform(-TW / 2 + 0.1, TW / 2 - 0.1)
    y = rng.uniform(-TL / 2 + 0.1, TL / 2 - 0.1)
    hump = 0.16 * (1 - (x / (TW / 2)) ** 2) * (1 - (y / (TL / 2)) ** 2)
    size = rng.uniform(0.05, 0.11)
    tub_coal.rock(size, (RX + x, TUB_Y + y, TZ0 + TH - 0.06 + hump + rng.uniform(0, 0.04)), seed=900 + k,
                  mat="coal_ore", detail=1 if size > 0.08 else 0, squash=(1, 0.9, 0.7), rough=0.3)

# ================================================================== wheelbarrow (dented steel tray)
BX, BY, BYAW = -1.62, -1.95, 18.0          # barrow centre on the floor, yaw (deg); wheel points toward the heap
barrow = m.part("barrow_mesh")
QB = Quaternion((0, 0, 1), math.radians(BYAW))


def bp(x, y, z):
    return V((BX, BY, 0)) + QB @ V((x, y, z))


with barrow.at((BX, BY, 0), q=QB):
    # tray: stacked rounded-rect rings bottom->rim, front wall sloped forward; dents by noise
    def rr_ring(w, l, z, fy, r=0.06, n=6):
        pts = []
        corners = [(w / 2 - r, -l / 2 - fy + r, -90), (w / 2 - r, l / 2 - r, 0), (-w / 2 + r, l / 2 - r, 90),
                   (-w / 2 + r, -l / 2 - fy + r, 180)]
        for cx, cy, a0 in corners:
            for k in range(n):
                a = math.radians(a0 + 90 * k / (n - 1))
                pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r, z))
        return pts
    outer, inner = [], []
    for i in range(6):
        t = i / 5
        w = lib.lerp(0.42, 0.66, t)
        ln = lib.lerp(0.5, 0.78, t)
        fy = lib.lerp(0.0, 0.22, t)       # front wall leans out
        z = 0.36 + t * 0.26
        ring = rr_ring(w, ln, z, fy)
        dented = []
        for (x, y, zz) in ring:
            d = noise.noise(V((x * 6.0, y * 6.0, zz * 6.0 + 9.0)))
            dent = -0.022 * max(0.0, d) * (1 - abs(2 * t - 1) * 0.6)
            nrm = V((x, y + 0.11 * t, 0)).normalized()
            dented.append(tuple(V((x, y, zz)) + nrm * dent))
        outer.append(dented)
        inner.append([tuple(V(p) + V((-p[0], -(p[1] + 0.11 * t), 0)).normalized() * 0.006 + V((0, 0, 0.004)))
                      for p in reversed(dented)])
    barrow.loft(outer, mat="paint_green", close=True, cap0=True, cap1=False, bev=0, uv="box")
    barrow.loft(inner, mat="paint_green", close=True, cap0=True, cap1=False, bev=0, uv="box")
    rim = outer[-1] + [outer[-1][0]]
    barrow.tube([V(p) + V((0, 0, 0.006)) for p in rim], 0.012, mat="paint_green", sides=6, caps=False)
    # frame: two tube rails from the axle to the legs, wooden handles beyond
    for sx in (1, -1):
        barrow.rod((sx * 0.07, -0.62, 0.2), (sx * 0.22, 0.2, 0.38), 0.014, mat="steel_dark", sides=8)
        barrow.rod((sx * 0.22, 0.2, 0.38), (sx * 0.27, 0.9, 0.56), 0.02, mat="wood_dark", sides=8)
        barrow.cyl(0.024, 0.13, c=(sx * 0.275, 0.88, 0.555), q=aim(V((0.07, 0.7, 0.18))), mat="rubber", sides=8,
                   bev=0)
        barrow.rod((sx * 0.2, 0.12, 0.36), (sx * 0.22, 0.2, 0.0), 0.012, mat="steel_dark", sides=6)   # legs
        barrow.box((0.04, 0.08, 0.012), c=(sx * 0.22, 0.2, 0.006), mat="steel_dark", bev=0)
        barrow.rod((sx * 0.07, -0.62, 0.2), (sx * 0.12, -0.3, 0.36), 0.01, mat="steel_dark", sides=6)  # stays
    barrow.rod((-0.2, 0.12, 0.36), (0.2, 0.12, 0.36), 0.01, mat="steel_dark", sides=6)
    # pneumatic tyre + hub at the front
    with barrow.at((0, -0.62, 0.2), rot=(0, 90, 0)):
        barrow.lathe([(0.08, -0.04), (0.13, -0.045), (0.18, -0.04), (0.2, -0.02), (0.2, 0.02), (0.18, 0.04),
                      (0.13, 0.045), (0.08, 0.04)], mat="rubber", sides=22, cap0=False, cap1=False, angle=40)
        for k in range(22):
            a = k / 22 * math.tau
            barrow.box((0.014, 0.022, 0.06), c=(math.cos(a) * 0.2, math.sin(a) * 0.2, 0), rot=(0, 0, math.degrees(a)),
                       mat="rubber", bev=0)
        barrow.cyl(0.08, 0.07, mat="paint_red", sides=14, bev=0, caps=False)
        barrow.cyl(0.03, 0.12, mat="steel_dark", sides=8, bev=0)
    barrow.decal("gulch", c=(0.0, 0.362, 0.56), n=(0, 0.88, -0.475), up=(0, 0.475, 0.88), w=0.32)

# ================================================================== crate, leaning tools, lantern post, water can
CR = V((-1.55, -0.25, 0.0))
body.box((0.62, 0.46, 0.44), c=CR + V((0, 0, 0.22)), mat="wood_planks", bev=0.006)
for sx in (1, -1):
    for sy in (1, -1):
        body.box((0.05, 0.05, 0.46), c=CR + V((sx * 0.29, sy * 0.21, 0.23)), mat="wood_dark", bev=0.006)
for sy in (1, -1):
    for zz in (0.08, 0.36):
        body.box((0.6, 0.02, 0.06), c=CR + V((0, sy * 0.235, zz)), mat="wood_dark", bev=0.004)
body.decal("crate", c=CR + V((0, -0.247, 0.22)), n=(0, -1, 0), w=0.48)
body.decal("thisup", c=CR + V((0.3125 + 0.001, 0, 0.27)), n=(1, 0, 0), w=0.3)
# shovel leaning on the crate side (+X face), pick leaning on its front
SHV0, SHV1 = CR + V((0.55, -0.12, 0.0)), CR + V((0.34, -0.1, 0.46))
d = (SHV1 - SHV0).normalized()
q = frame(d, (0, -1, 0))
with body.at(SHV0, q=q):
    body.box((0.25, 0.012, 0.3), c=(0, 0, 0.15), mat="steel", bev=0.003)                          # blade
    body.box((0.25, 0.04, 0.012), c=(0, 0.014, 0.3), mat="steel", bev=0)
    body.cyl(0.024, 0.12, c=(0, 0, 0.35), r2=0.017, mat="steel", sides=8, bev=0)                     # socket
body.rod(SHV0 + d * 0.38, SHV0 + d * 1.25, 0.017, mat="wood_planks", sides=8)
body.rod(SHV0 + d * 1.25, SHV0 + d * 1.32, 0.017, mat="wood_planks", sides=8)
with body.at(SHV0 + d * 1.36, q=q):
    body.box((0.13, 0.025, 0.025), c=(0, 0, 0.04), mat="wood_dark", bev=0)                          # D-grip
    for sx in (1, -1):
        body.rod((sx * 0.06, 0, -0.02), (sx * 0.065, 0, 0.04), 0.009, mat="steel_dark", sides=6)
PK0, PK1 = CR + V((-0.2, -0.62, 0.0)), CR + V((-0.2, -0.05, 0.67))
dp_ = (PK1 - PK0).normalized()
body.rod(PK0 + dp_ * 0.03, PK1, 0.02, mat="wood_planks", sides=8)                                  # hickory handle
with body.at(PK1 - dp_ * 0.05, q=frame(dp_, (1, 0, 0))):
    body.box((0.05, 0.05, 0.08), mat="steel_dark", bev=0.006)                                       # eye
    body.cyl(0.018, 0.28, c=(0.15, 0, 0.0), r2=0.004, rot=(0, 90, 0), mat="steel", sides=6, bev=0)   # pick point
    body.box((0.22, 0.045, 0.03), c=(-0.12, 0, 0.0), mat="steel", bev=0.004)                         # adze
# timber prop with a hook arm; the lantern hangs over the crate and sways
POST = CR + V((-0.24, 0.29, 0.0))
body.box((0.1, 0.1, 1.22), c=POST + V((0, 0, 0.61)), mat="wood_timber", bev=0.012)               # lantern stand
for zz in (0.12, 0.36):
    body.cyl(0.008, 0.02, c=POST + V((0, -0.06, zz)), axis="Y", mat="steel_dark", sides=6, bev=0)  # nails to crate
body.box((0.36, 0.07, 0.07), c=POST + V((0.17, 0, 1.18)), mat="wood_timber", bev=0.01)
HOOK = POST + V((0.31, 0, 1.12))
body.rod(POST + V((0.31, 0, 1.15)), HOOK, 0.005, mat="steel_dark", sides=6)
body.rod(POST + V((0.02, 0, 0.98)), POST + V((0.2, 0, 1.15)), 0.025, mat="wood_timber", sides=6)  # brace
lant = m.part("lantern", origin=HOOK)
with lant.at(HOOK, q=Quaternion()):
    lant.tube([V((math.sin(a) * 0.075, 0, -0.012 - 0.1 * (1 - math.cos(a)) ** 0.5)) for a in
               [math.radians(-80 + 160 * k / 10) for k in range(11)]], 0.004, mat="steel", sides=6, caps=False)  # bail
    lc = V((0, 0, -0.26))
    lant.lathe([(0, -0.1), (0.075, -0.1), (0.08, -0.09), (0.08, -0.05), (0.06, -0.04), (0, -0.04)], c=lc,
               mat="brass", sides=16, angle=25)                                                     # fuel fount
    lant.lathe([(0.045, -0.04), (0.062, 0.0), (0.066, 0.06), (0.05, 0.12), (0.03, 0.135)], c=lc, mat="glass", sides=16,
               cap0=False, cap1=False)                                                              # globe
    lant.sphere(0.022, c=lc + V((0, 0, 0.03)), mat="emit_warm", seg=10, rings=6, scale=(0.8, 0.8, 1.3))  # flame
    lant.lathe([(0, 0.13), (0.05, 0.13), (0.065, 0.15), (0.035, 0.185), (0.012, 0.2), (0, 0.2)], c=lc, mat="brass",
               sides=16, angle=25)                                                                  # top cap
    for k in range(4):                                                                              # guard wires
        a = k / 4 * math.tau + 0.4
        lant.rod(lc + V((math.cos(a) * 0.075, math.sin(a) * 0.075, -0.04)),
                 lc + V((math.cos(a) * 0.05, math.sin(a) * 0.05, 0.14)), 0.0035, mat="steel", sides=5, bev=0)
# galvanized water can
WC = CR + V((0.2, 0.62, 0.0))
body.lathe([(0, 0.0), (0.13, 0.0), (0.135, 0.02), (0.13, 0.3), (0.1, 0.36), (0.07, 0.38), (0.07, 0.4), (0, 0.4)],
           c=WC, mat="galvanized", sides=18, angle=25)
for zz in (0.08, 0.22):
    body.lathe([(0.131, zz - 0.01), (0.138, zz - 0.01), (0.138, zz + 0.01), (0.131, zz + 0.01)], c=WC,
               mat="galvanized", sides=18, cap0=False, cap1=False)
body.cyl(0.075, 0.02, c=WC + V((0, 0, 0.41)), mat="galvanized", sides=14, bev=0)
body.tube([WC + V((-0.07 + 0.14 * k / 8, 0, 0.42 + 0.09 * math.sin(math.pi * k / 8))) for k in range(9)], 0.007,
          mat="steel", sides=6, caps=False)
body.cyl(0.018, 0.16, c=WC + V((0.13, 0, 0.27)), r2=0.012, q=aim(V((0.6, 0, 0.8))), mat="galvanized", sides=8, bev=0)
body.decal("water", c=WC + V((0, -0.139, 0.16)), n=(0, -1, 0), w=0.18)
# a couple of short timber offcuts on the floor + a sledge leaning on the post
for k, (x, y, a) in enumerate(((-0.8, 0.45, 12), (-0.65, 0.62, -8))):
    body.box((0.9, 0.12, 0.08), c=(x, y, 0.04 + k * 0.08), rot=(0, 0, a), mat="wood_timber", bev=0.012)

# ================================================================== empties
m.empty("crew_0", (-0.8, -3.0, 0.0))
m.empty("crew_1", (0.8, -3.0, 0.0))
m.empty("barrow", bp(0, 0, 0), q=QB)
m.empty("fx_work", (0.0, -3.92, 1.15))
m.empty("fx_ore", (RX, TUB_Y, TZ0 + TH + 0.15), parent="tub")
m.empty("snd", (0.0, -3.0, 1.2))

lib.tick("build parts")
m.finish(rays=20, strength=1.15, low=0.35, noise_amt=0.18)
lib.tick("finish+grime")

ANIM = ["lantern", "tub"]


def work(t):
    sway = math.radians(5.5) * math.sin(math.tau * 3 * t) + math.radians(1.5) * math.sin(math.tau * 2 * t + 0.7)
    yaw = math.radians(2.5) * math.sin(math.tau * 3 * t + 1.3)
    roll = math.radians(1.3) * math.sin(math.tau * 2 * t)
    return {"lantern": {"q": Quaternion((0, 0, 1), yaw) @ Quaternion((1, 0, 0), sway)},
            "tub": {"q": Quaternion((0, 1, 0), roll)}}


m.clip("Work", 3.0, work, ANIM)
m.clip("Idle", 2.0, None, ANIM)
lib.tick("clips")
tris, size = m.report()
if stem:
    m.export(stem)
    lib.tick("export")
if "--no-render" not in flags:
    views = [
        ("front3q", (3.4, -6.6, 2.5), (0.0, -2.0, 0.5), 32),
        ("side", (-7.4, -1.6, 1.8), (0, -1.6, 0.5), 36),
        ("rear3q", (-3.8, 3.6, 2.4), (0.0, -1.4, 0.5), 32),
        ("close", (-0.2, 1.3, 1.45), (-1.45, -0.45, 0.6), 38),
        ("heap", (1.4, -0.6, 1.9), (-0.2, -3.3, 0.25), 34),
    ]
    if "--one" in flags:
        views = views[:1]
    m.render(views)
