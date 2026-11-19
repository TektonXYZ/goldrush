"""Sierra Foundry five-stamp battery (GoldRush machines-A, tier 3).

The iconic gold-rush stamp mill compressed to <= 3.9 m: a heavy timber battery frame with five iron stems (tappet
on each, head + shoe dropping into a cast-iron mortar box) under a cam shaft with five double cams; a big bull
pulley on the shaft driven by a flat belt from a small hit-and-miss engine on the side; an ore bin + feed chute
behind; a sloped copper amalgamation apron in front with a water trickle into a launder; hang-up fingers; a hanging
lamp; a belt-clutch lever for the op.

Work (5 s): cam shaft 3 turns, stamps drop in firing order 1-3-5-2-4 at 1.2 drops/s each (one drop every
P/5 = 0.167 s overall, impact at phase 0.8 of each stamp's cycle), bull pulley + belt + engine flywheels turning,
engine rocking on its skids. Idle: stamps hung up on the fingers, everything still.

    systemd-run --user --scope -q -p MemoryMax=3G -p MemorySwapMax=0 \
        bl assets/machines_a/stampmill.py -- public/models/machines/stampmill [--no-render]
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
from lib import V, aim, frame  # noqa: E402
from mathutils import Matrix, Quaternion, noise  # noqa: E402

stem, flags = lib.args()
m = lib.Machine("stampmill")
rng = random.Random(23)

# ------------------------------------------------------------------ decals
A_ = m.atlas
A_.add("foundry", 1000, 170, lib.svg_text("SIERRA FOUNDRY", font="Barlow Condensed Black", fill="#2A2724", wear=0.35,
                                          seed=3), fit=True)
A_.add("sf", 700, 120, lib.svg_text("SAN FRANCISCO · CAL.", font="Barlow Condensed ExtraBold", fill="#2A2724", wear=0.4,
                                    seed=5), fit=True)
A_.add("battery", 900, 160, lib.svg_text("5-STAMP BATTERY  No 1", font="Saira Stencil One", fill="#EFE8D6", wear=0.5,
                                         seed=7), fit=True)
A_.add("engine", 600, 170, lib.svg_text("SIERRA", font="Barlow Condensed Black", fill="#E3C45A", wear=0.35, seed=9),
       fit=True)
A_.add("hp", 400, 120, lib.svg_text("6 H.P.", font="Barlow Condensed Black", fill="#E3C45A", wear=0.35, seed=11),
       fit=True)
A_.build()
WATER = lib.Atlas("sluice_water", width=256, mat_name="custom_sluice_water", rough=0.06)
WATER.add("w", 256, 512, lib.svg(256, 512, (
    '<filter id="t" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency="0.05 0.011" '
    'numOctaves="4" seed="3" stitchTiles="stitch"/>'
    '<feColorMatrix type="matrix" values="0.45 0 0 0 0.14  0.43 0 0 0 0.135  0.36 0 0 0 0.11  0.5 0 0 0 0.1"/></filter>'
    '<rect width="256" height="512" filter="url(#t)"/>')))
WATER.build()
lib.CLEAN.add("custom_sluice_water")

body = m.part("stampmill_body")

# ------------------------------------------------------------------ key geometry (Blender, front/apron = -Y)
XS = [-0.56, -0.28, 0.0, 0.28, 0.56]       # stamp stems (stamp 1 at -X ... stamp 5 at +X)
ORDER = [1, 3, 5, 2, 4]                    # firing order
PHI = {s: ORDER.index(s) / 5 for s in range(1, 6)}
DIE = 0.5                                  # die top inside the mortar (shoe bottom when down)
SHAFT = V((0, 0.33, 2.47))                 # cam shaft axis (along X)
TAP0 = 2.38                                # tappet bottom when the stamp is down
HMAX, HUNG = 0.165, 0.205                  # lift height, hung-up height
RB = 0.85                                  # bull pulley radius
XB = 1.42                                  # belt plane x
ENG = V((XB, 1.55, 0.55))                  # engine crankshaft / pulley centre (y, z)
RE = RB * 3 / 16                           # engine pulley: 16 turns per 3 shaft turns
TURNS = 3

# ================================================================== foundation + mortar
for sx in (1, -1):
    body.box((0.32, 2.2, 0.3), c=(sx * 0.62, 0.0, 0.15), mat="wood_timber", bev=0.02)               # sills
body.box((1.9, 0.9, 0.32), c=(0, 0, 0.16), mat="wood_timber", bev=0.02)                             # mortar block
for k in range(4):
    body.box((1.92, 0.02, 0.008), c=(0, -0.3 + k * 0.2, 0.324), mat="steel_dark", bev=0)
MZ0, MZ1 = 0.32, 1.22
body.box((1.62, 0.62, 0.06), c=(0, 0, MZ0 + 0.03), mat="cast_iron", bev=0.012)                    # base flange
body.box((1.5, 0.56, MZ1 - MZ0), c=(0, 0, (MZ0 + MZ1) / 2), mat="cast_iron", bev=0.025)            # mortar
for sx in (1, -1):
    for sy in (1, -1):
        body.cyl(0.03, 0.06, c=(sx * 0.74, sy * 0.29, MZ0 + 0.08), mat="steel_dark", sides=6, bev=0)  # hold-downs
        body.rod((sx * 0.74, sy * 0.29, MZ0 + 0.1), (sx * 0.74, sy * 0.29, MZ0 + 0.22), 0.016, mat="steel", sides=6)
body.box((1.25, 0.03, 0.32), c=(0, -0.29, 0.98), mat="steel_dark", bev=0.004)                       # screen frame
body.mesh_panel((0, -0.305, 0.98), 1.15, 0.26, cell=0.03, wire=0.004)                               # screen
for x in (-0.66, 0.66):
    body.box((0.05, 0.05, 0.34), c=(x, -0.3, 0.98), mat="wood_timber", bev=0.006)                    # keys
body.box((1.3, 0.12, 0.05), c=(0, -0.33, 0.8), mat="cast_iron", bev=0.008)                          # lip
for sx in (1, -1):                                                                                  # cast lettering
    body.decal("foundry", c=(sx * 0.753, 0, 0.86), n=(sx, 0, 0), up=(0, 0, 1), w=0.5)
    body.decal("sf", c=(sx * 0.753, 0, 0.74), n=(sx, 0, 0), up=(0, 0, 1), w=0.36)
body.box((1.3, 0.1, 0.12), c=(0, 0.3, 1.12), mat="cast_iron", bev=0.01)                             # feed lip
body.box((1.44, 0.5, 0.05), c=(0, 0, MZ1 + 0.025), mat="wood_planks", bev=0.006)
for x in XS:
    body.cyl(0.05, 0.052, c=(x, 0, MZ1 + 0.026), mat="steel_dark", sides=10, bev=0)
    body.box((0.2, 0.2, 0.05), c=(x, 0, DIE - 0.025), mat="steel_dark", bev=0.006)                   # dies (hidden)
body.path([(1.25, 0.6, 0.35), (1.15, 0.45, 0.9), (0.9, 0.38, 1.28), (0.5, 0.2, 1.3), (0.3, 0.15, 1.27)], r=0.02,
          mat="galvanized", sides=8, res=4)                                                          # battery water
body.cyl(0.035, 0.06, c=(1.17, 0.47, 0.82), axis="Y", mat="brass", sides=8, bev=0)
body.rod((1.17, 0.44, 0.82), (1.17, 0.36, 0.9), 0.008, mat="steel", sides=6)
body.cyl(0.035, 0.012, c=(1.17, 0.35, 0.91), axis="Y", mat="paint_red", sides=10, bev=0)            # valve wheel

# ================================================================== battery frame (timber)
for sx in (1, -1):
    body.box((0.3, 0.32, 3.3), c=(sx * 0.95, 0.0, 1.65), mat="wood_timber", bev=0.025)              # battery posts
    body.box((0.26, 0.26, 2.0), c=(sx * 0.95, 0.42, 1.95), mat="wood_timber", bev=0.02)             # shaft posts
    body.rod((sx * 0.95, 0.15, 3.0), (sx * 0.95, 1.9, 0.12), 0.11, mat="wood_timber", sides=8, bev=0.01)  # knee brace
    body.box((0.34, 0.4, 0.12), c=(sx * 0.95, 1.95, 0.06), mat="wood_timber", bev=0.012)
    body.rod((sx * 0.95, -0.12, 2.3), (sx * 0.95, -1.05, 0.08), 0.09, mat="wood_timber", sides=8, bev=0.01)  # front
    body.box((0.3, 0.34, 0.1), c=(sx * 0.95, -1.1, 0.05), mat="wood_timber", bev=0.01)
    for z in (0.7, 1.9, 2.95):                                                                      # tie bolts
        body.cyl(0.018, 0.4, c=(sx * 0.95, 0.0, z), axis="Y", mat="steel", sides=6, bev=0)
        for sy in (1, -1):
            body.cyl(0.03, 0.02, c=(sx * 0.95, sy * 0.17, z), axis="Y", mat="steel_dark", sides=6, bev=0)
    with body.at((sx * 0.95, SHAFT.y, SHAFT.z - 0.12), q=Quaternion()):                            # pillow block
        body.box((0.28, 0.24, 0.1), c=(0, 0, 0.0), mat="cast_iron", bev=0.012)
        body.cyl(0.11, 0.2, c=(0, 0, 0.12), rot=(0, 90, 0), mat="cast_iron", sides=16, bev=0.006)
        body.box((0.2, 0.18, 0.04), c=(0, 0, 0.2), mat="cast_iron", bev=0.006)
        for sy in (1, -1):
            body.cyl(0.012, 0.03, c=(0, sy * 0.09, 0.22), mat="steel_dark", sides=6, bev=0)
body.box((2.3, 0.3, 0.2), c=(0, -0.25, 3.3), mat="wood_timber", bev=0.02)                           # cap (in front)
for z, name in ((1.58, "lower"), (3.12, "upper")):                                                  # stem guides
    body.box((2.2, 0.24, 0.14), c=(0, 0.0, z), mat="wood_timber", bev=0.015)
    for x in XS:
        body.cyl(0.055, 0.02, c=(x, 0, z + 0.075), mat="cast_iron", sides=12, bev=0)
body.box((2.2, 0.2, 0.18), c=(0, 0.42, 1.0), mat="wood_timber", bev=0.015)                          # back girt
body.decal("battery", c=(0, -0.401, 3.3), n=(0, -1, 0), w=1.15)
# finger shaft (fingers animated)
FING = V((0, -0.24, TAP0 + HUNG - 0.035))
body.cyl(0.03, 2.0, c=FING, axis="X", mat="steel", sides=8, bev=0)
for sx in (1, -1):
    body.box((0.06, 0.12, 0.12), c=FING + V((sx * 0.85, 0.06, 0)), mat="cast_iron", bev=0.006)

# ================================================================== ore bin + feed chute (behind)
BIN = V((0, 1.3, 1.25))
for sx in (1, -1):
    for sy in (1, -1):
        body.box((0.12, 0.12, BIN.z + 0.9), c=(sx * 0.62, BIN.y + sy * 0.42, (BIN.z + 0.9) / 2), mat="wood_timber",
                 bev=0.012)
body.plate([(-0.62, BIN.z + 0.12), (0.62, BIN.z + 0.12), (0.62, BIN.z + 0.9), (-0.62, BIN.z + 0.9)], 0.04, "XZ",
           at=BIN.y + 0.45, mat="wood_planks", bev=0.006)                                           # back wall
for sx in (1, -1):
    body.plate([(BIN.y - 0.45, BIN.z), (BIN.y + 0.45, BIN.z + 0.12), (BIN.y + 0.45, BIN.z + 0.9),
                (BIN.y - 0.45, BIN.z + 0.9)], 0.04, "YZ", at=sx * 0.62, mat="wood_planks", bev=0.006)
body.plate([(-0.62, BIN.z + 0.25), (0.62, BIN.z + 0.25), (0.62, BIN.z + 0.9), (-0.62, BIN.z + 0.9)], 0.04, "XZ",
           at=BIN.y - 0.45, mat="wood_planks", bev=0.006)                                           # front wall
with body.at((0, BIN.y, BIN.z + 0.06), rot=(-8, 0, 0)):
    body.box((1.22, 0.92, 0.04), mat="wood_planks", bev=0.006)                                      # sloped floor
for k in range(4):                                                                                  # planks lines
    body.box((0.03, 0.92, 0.045), c=(-0.45 + k * 0.3, BIN.y, BIN.z + 0.9), mat="wood_timber", bev=0)
CH0, CH1 = V((0, BIN.y - 0.45, BIN.z + 0.05)), V((0, 0.36, 1.2))
d = (CH1 - CH0)
cang = math.degrees(math.atan2(d.z, -d.y))
with body.at((CH0 + CH1) / 2, rot=(-cang, 0, 0)):
    body.box((0.46, d.length, 0.03), mat="steel", bev=0.004)
    for sx in (1, -1):
        body.box((0.03, d.length, 0.14), c=(sx * 0.245, 0, 0.06), mat="wood_planks", bev=0.004)
ore = m.part("ore")
ore.sharp = 14.0
for k in range(90):
    s = rng.uniform(0.05, 0.12)
    x = rng.uniform(-0.5, 0.5)
    y = rng.uniform(BIN.y - 0.35, BIN.y + 0.35)
    hump = 0.18 * (1 - (x / 0.62) ** 2)
    ore.rock(s, (x, y, BIN.z + 0.62 + hump + rng.uniform(0, 0.12)), seed=100 + k, mat="gold_ore",
             detail=1 if s > 0.08 else 0, squash=(1, 0.9, 0.75), rough=0.3)
ore.box((1.1, 0.8, 0.5), c=(0, BIN.y, BIN.z + 0.4), mat="gold_ore", bev=0.0)                         # fill under
for k in range(12):
    t = rng.uniform(0.1, 0.9)
    p = CH0.lerp(CH1, t)
    s = rng.uniform(0.04, 0.07)
    ore.rock(s, (rng.uniform(-0.15, 0.15), p.y, p.z + 0.04 + s * 0.3), seed=300 + k, mat="gold_ore", detail=0,
             squash=(1, 0.9, 0.7), rough=0.3)

# ================================================================== copper apron + launder (front)
AP0, AP1 = V((0, -0.36, 0.8)), V((0, -1.62, 0.52))
ad = AP1 - AP0
aang = math.degrees(math.atan2(-ad.z, -ad.y))
with body.at((AP0 + AP1) / 2, rot=(aang, 0, 0)):
    body.box((1.44, ad.length, 0.012), c=(0, 0, 0.0), mat="copper", bev=0)                          # copper plate
    body.box((1.5, ad.length + 0.04, 0.05), c=(0, 0, -0.032), mat="wood_planks", bev=0.006)          # table top
    for sx in (1, -1):
        body.box((0.04, ad.length, 0.07), c=(sx * 0.74, 0, 0.03), mat="wood_timber", bev=0.006)
    for k in range(3):                                                                              # cleats
        body.box((1.44, 0.02, 0.012), c=(0, -ad.length / 2 + 0.3 + k * 0.42, 0.012), mat="wood_timber", bev=0)
    rows = 10
    for j, (xc, w0) in enumerate(((-0.5, 0.07), (-0.18, 0.11), (0.12, 0.08), (0.45, 0.1))):          # trickles
        for i in range(rows):
            y0 = ad.length / 2 - 0.02 - i * (ad.length - 0.04) / rows
            y1 = ad.length / 2 - 0.02 - (i + 1) * (ad.length - 0.04) / rows
            wob0 = 0.03 * math.sin(i * 1.3 + j * 2.0)
            wob1 = 0.03 * math.sin((i + 1) * 1.3 + j * 2.0)
            wa = w0 * (1 + 0.6 * i / rows)
            wb = w0 * (1 + 0.6 * (i + 1) / rows)
            v0, v1 = (ad.length / 2 - y0) / 1.2, (ad.length / 2 - y1) / 1.2
            body.quad([(xc + wob1 - wb, y1, 0.009), (xc + wob1 + wb, y1, 0.009), (xc + wob0 + wa, y0, 0.009),
                       (xc + wob0 - wa, y0, 0.009)], "custom_sluice_water", [(0, v1), (1, v1), (1, v0), (0, v0)])
for sx in (1, -1):                                                                                  # apron legs
    body.box((0.08, 0.08, AP1.z - 0.02), c=(sx * 0.7, AP1.y + 0.08, (AP1.z - 0.02) / 2), mat="wood_timber", bev=0.008)
    body.box((0.08, 0.08, AP0.z - 0.25), c=(sx * 0.7, AP0.y - 0.25, (AP0.z - 0.25) / 2), mat="wood_timber", bev=0.008)
LA = V((0, -1.78, 0.36))
with body.at(LA, rot=(0, -3, 0)):
    body.box((2.0, 0.26, 0.03), c=(0.1, 0, 0.0), mat="wood_planks", bev=0.005)
    for sy in (1, -1):
        body.box((2.0, 0.03, 0.14), c=(0.1, sy * 0.13, 0.07), mat="wood_planks", bev=0.005)
    body.box((0.03, 0.26, 0.14), c=(-0.9, 0, 0.07), mat="wood_planks", bev=0.005)
    body.quad([(-0.88, -0.11, 0.05), (1.08, -0.11, 0.05), (1.08, 0.11, 0.05), (-0.88, 0.11, 0.05)], "custom_sluice_water",
              [(0, 0), (0, 1.6), (1, 1.6), (1, 0)])
for x in (-0.6, 0.5):
    body.box((0.06, 0.06, 0.34), c=(x, LA.y, 0.17), mat="wood_timber", bev=0.006)
body.quad([(-0.6, AP1.y - 0.08, 0.41), (0.6, AP1.y - 0.08, 0.41), (0.6, AP1.y - 0.03, AP1.z - 0.01),
           (-0.6, AP1.y - 0.03, AP1.z - 0.01)], "custom_sluice_water", [(0, 0), (1, 0), (1, 0.15), (0, 0.15)])

# ================================================================== clutch lever (op) + hanging lamp
LV = V((1.28, -0.55, 0.0))
body.box((0.14, 0.3, 0.1), c=LV + V((0, 0, 0.05)), mat="cast_iron", bev=0.008)
lever = (LV + V((0, 0, 0.08)), LV + V((0, -0.22, 1.25)))
body.rod(lever[0], lever[1], 0.03, mat="wood_dark", sides=8)
body.cyl(0.04, 0.12, c=lever[1], q=aim(lever[1] - lever[0]), mat="wood_dark", sides=8, bev=0)
body.box((0.04, 0.22, 0.06), c=LV + V((0, 0.05, 0.6)), mat="cast_iron", bev=0)                       # quadrant
body.rod(LV + V((0, -0.08, 0.7)), V((XB, ENG.y - 0.6, 0.9)), 0.012, mat="steel", sides=6)             # link rod
HOOK = V((-0.45, -0.18, 3.2))
body.rod(HOOK, HOOK + V((0, 0, -0.06)), 0.006, mat="steel_dark", sides=6)
lamp = m.part("lamp", origin=HOOK)
with lamp.at(HOOK + V((0, 0, -0.38)), q=Quaternion()):
    lamp.tube([V((math.sin(a) * 0.075, 0, 0.32 - 0.1 * (1 - math.cos(a)) ** 0.5)) for a in
               [math.radians(-80 + 160 * k / 10) for k in range(11)]], 0.004, mat="steel", sides=6, caps=False)
    lamp.rod((0, 0, 0.32), (0, 0, 0.38), 0.004, mat="steel", sides=5)
    lamp.lathe([(0, -0.1), (0.075, -0.1), (0.08, -0.09), (0.08, -0.05), (0.06, -0.04), (0, -0.04)], mat="brass", sides=14,
               angle=25)
    lamp.lathe([(0.045, -0.04), (0.062, 0.0), (0.066, 0.06), (0.05, 0.12), (0.03, 0.135)], mat="glass", sides=14,
               cap0=False, cap1=False)
    lamp.sphere(0.022, c=(0, 0, 0.03), mat="emit_warm", seg=10, rings=6, scale=(0.8, 0.8, 1.3))
    lamp.lathe([(0, 0.13), (0.05, 0.13), (0.065, 0.15), (0.035, 0.185), (0.012, 0.2), (0, 0.2)], mat="brass", sides=14,
               angle=25)
    for k in range(4):
        a = k / 4 * math.tau + 0.4
        lamp.rod((math.cos(a) * 0.075, math.sin(a) * 0.075, -0.04), (math.cos(a) * 0.05, math.sin(a) * 0.05, 0.14),
                 0.0035, mat="steel", sides=5, bev=0)
LAMP_C = HOOK + V((0, 0, -0.38))

# ================================================================== cam shaft + cams + bull pulley (animated)
shaft = m.part("camshaft", origin=SHAFT)
shaft.cyl(0.075, 3.0, c=SHAFT + V((0.25, 0, 0)), axis="X", mat="steel", sides=16, bev=0.006)
for sx in (-1.12, 0.78):
    shaft.cyl(0.11, 0.08, c=SHAFT + V((sx, 0, 0)), axis="X", mat="cast_iron", sides=14, bev=0.004)   # collars


def cam_poly():
    """Double-armed involute-ish cam outline (local XY, arms along +-X)."""
    pts = []
    for half in (0, 1):
        for i in range(10):
            u = i / 9
            a = math.pi * half + u * math.pi * 0.62
            r = 0.11 + 0.17 * (u ** 0.85) if u < 0.92 else 0.11 + 0.17 * 0.93
            pts.append((r * math.cos(a), r * math.sin(a)))
        for i in range(4):
            a = math.pi * half + math.pi * 0.62 + (math.pi * 0.38) * (i + 1) / 5
            pts.append((0.11 * math.cos(a), 0.11 * math.sin(a)))
    return pts


CAMP = cam_poly()
for s, x in enumerate(XS, start=1):
    gamma = math.pi * (0.275 + PHI[s])                                                              # arm angle at rest
    q = Quaternion((1, 0, 0), gamma) @ Quaternion((0, 1, 0), math.pi / 2)
    with shaft.at(SHAFT + V((x, -0.0, 0)), q=q):
        shaft.extrude(CAMP, 0.07, mat="cast_iron", bev=0.008)
    shaft.cyl(0.125, 0.11, c=SHAFT + V((x, 0, 0)), axis="X", mat="cast_iron", sides=14, bev=0.006)    # hub
    shaft.box((0.02, 0.05, 0.03), c=SHAFT + V((x - 0.05, 0, 0.125)), mat="steel_dark", bev=0)         # key
with shaft.at(SHAFT + V((XB - SHAFT.x, 0, 0)), rot=(0, 90, 0)):                                    # bull pulley
    shaft.lathe([(RB - 0.06, -0.12), (RB, -0.12), (RB + 0.012, 0.0), (RB, 0.12), (RB - 0.06, 0.12)], mat="cast_iron",
                sides=40, cap0=False, cap1=False, angle=30)
    shaft.lathe([(RB - 0.06, 0.12), (RB - 0.06, -0.12)], mat="cast_iron", sides=40, cap0=False, cap1=False)
    shaft.cyl(0.16, 0.22, mat="cast_iron", sides=16, bev=0.008)
    for k in range(6):
        a = k / 6 * math.tau
        with shaft.at((0, 0, 0), rot=(0, 0, math.degrees(a))):
            shaft.box((0.07, RB - 0.18, 0.06), c=(0, 0.11 + (RB - 0.18) / 2, 0), mat="cast_iron", bev=0.01)
for sx in (1, -1):
    shaft.bolt_circle(SHAFT + V((XB - SHAFT.x + sx * 0.11, 0, 0)), (sx, 0, 0), 0.1, 6, r=0.014)

# ================================================================== stamps (animated)
STAMPS = []
for s, x in enumerate(XS, start=1):
    sp = m.part(f"stamp_{s}", origin=(x, 0, DIE))
    sp.cyl(0.103, 0.16, c=(x, 0, DIE + 0.08), mat="steel_dark", sides=14, bev=0.008)               # shoe
    sp.lathe([(0, 0.0), (0.112, 0.0), (0.112, 0.33), (0.085, 0.38), (0.05, 0.4), (0, 0.4)], c=(x, 0, DIE + 0.16),
             mat="cast_iron", sides=14, angle=25)                                                    # head / boss
    sp.cyl(0.036, 3.62 - (DIE + 0.5), c=(x, 0, (DIE + 0.5 + 3.62) / 2), mat="steel", sides=10, bev=0)  # stem
    sp.lathe([(0, 0.0), (0.1, 0.0), (0.105, 0.02), (0.105, 0.22), (0.1, 0.24), (0, 0.24)], c=(x, 0, TAP0),
             mat="cast_iron", sides=14, angle=25)                                                    # tappet
    for k in range(3):                                                                              # gib keys
        a = k / 3 * math.tau
        sp.box((0.03, 0.02, 0.18), c=(x + math.cos(a) * 0.106, math.sin(a) * 0.106, TAP0 + 0.12),
               rot=(0, 0, math.degrees(a)), mat="steel_dark", bev=0)
    STAMPS.append(sp.name)
fing = m.part("fingers", origin=FING)
for x in XS:
    fing.box((0.07, 0.34, 0.06), c=FING + V((x, 0.15, 0.0)), mat="wood_dark", bev=0.008)
    fing.cyl(0.042, 0.08, c=FING + V((x, 0, 0)), axis="X", mat="cast_iron", sides=10, bev=0)

# ================================================================== engine (animated rock) + flywheels/pulley + con rod
eng = m.part("engine", origin=ENG + V((0.25, 0.25, -ENG.z)))
EX = XB + 0.42                                                                                       # engine centreline x
with eng.at((EX, ENG.y + 0.45, 0.0), q=Quaternion()):
    for sx in (1, -1):
        eng.box((0.1, 1.2, 0.1), c=(sx * 0.2, 0.0, 0.05), mat="wood_timber", bev=0.012)             # skids
    eng.box((0.36, 0.95, 0.12), c=(0, 0.0, 0.16), mat="cast_iron", bev=0.015)                        # bed
    eng.box((0.3, 0.32, 0.28), c=(0, -0.42, 0.36), mat="paint_green", bev=0.03)                      # crank frame
    eng.lathe([(0, 0.0), (0.13, 0.0), (0.13, 0.04), (0.115, 0.06), (0.115, 0.5), (0.13, 0.52), (0.13, 0.56),
               (0, 0.56)], c=(0, -0.28, 0.55), rot=(-90, 0, 0), mat="paint_green", sides=18, angle=25)  # cylinder
    eng.box((0.32, 0.4, 0.26), c=(0, 0.06, 0.82), mat="paint_green", bev=0.03)                       # water hopper
    eng.box((0.28, 0.36, 0.02), c=(0, 0.06, 0.95), mat="steel_dark", bev=0)
    eng.decal("engine", c=(0.161, 0.06, 0.82), n=(1, 0, 0), w=0.26)
    eng.decal("hp", c=(-0.161, 0.06, 0.84), n=(-1, 0, 0), w=0.14)
    eng.cyl(0.05, 0.12, c=(0, 0.36, 0.55), axis="Y", mat="brass", sides=10, bev=0)                  # head / igniter
    eng.cyl(0.03, 0.08, c=(-0.1, 0.3, 0.7), mat="brass", sides=8, bev=0)
    eng.path([(0.12, 0.25, 0.62), (0.22, 0.3, 0.75), (0.25, 0.45, 0.85), (0.25, 0.55, 1.05)], r=0.025, mat="steel_dark",
             sides=8, res=4)                                                                         # exhaust
    eng.cyl(0.05, 0.16, c=(0.25, 0.55, 1.12), mat="steel_dark", sides=10, bev=0)                     # muffler
    eng.box((0.08, 0.08, 0.2), c=(-0.12, -0.15, 0.5), mat="brass", bev=0)                            # oiler
CRANK = V((EX, ENG.y + 0.03, ENG.z))                                                                 # crankshaft axis
fw = m.part("flywheels", origin=CRANK, parent="engine")
fw.cyl(0.035, 0.75, c=CRANK + V((-0.18, 0, 0)), axis="X", mat="steel", sides=10, bev=0)
for dx in (-0.2, 0.2):
    with fw.at(CRANK + V((dx, 0, 0)), rot=(0, 90, 0)):
        fw.lathe([(0.36, -0.04), (0.42, -0.04), (0.42, 0.04), (0.36, 0.04)], mat="cast_iron", sides=32, cap0=False,
                 cap1=False, angle=30)
        fw.lathe([(0.36, 0.04), (0.36, -0.04)], mat="cast_iron", sides=32, cap0=False, cap1=False)
        fw.cyl(0.07, 0.1, mat="cast_iron", sides=12, bev=0.006)
        for k in range(5):
            with fw.at((0, 0, 0), rot=(0, 0, k * 72)):
                fw.box((0.045, 0.3, 0.03), c=(0, 0.21, 0), mat="cast_iron", bev=0.006)
with fw.at(V((XB, CRANK.y, CRANK.z)), rot=(0, 90, 0)):                                               # belt pulley
    fw.lathe([(RE - 0.03, -0.1), (RE, -0.1), (RE + 0.006, 0.0), (RE, 0.1), (RE - 0.03, 0.1)], mat="cast_iron", sides=20,
             cap0=False, cap1=False, angle=30)
    fw.cyl(RE - 0.03, 0.2, mat="cast_iron", sides=20, bev=0)
CR_R, ROD_L = 0.075, 0.38


def crank_rod(theta):
    """Con rod (engine-local): pin on the crank circle (YZ, about X), small end slides along +Y."""
    pin = V((0, CR_R * math.sin(theta), CR_R * math.cos(theta)))
    ylen = math.sqrt(max(1e-6, ROD_L ** 2 - pin.z ** 2))
    return pin, V((0, pin.y + ylen, 0.0))


PIN0, SMALL0 = crank_rod(0.0)
fw.cyl(0.05, 0.1, c=CRANK + V((0, 0.0, 0)), axis="X", mat="steel_dark", sides=12, bev=0)             # crank web
fw.cyl(0.02, 0.06, c=CRANK + PIN0, axis="X", mat="steel", sides=8, bev=0)                            # crank pin
rod = m.part("conrod", origin=CRANK + PIN0, parent="engine")
rod.box((0.035, 0.035, ROD_L), c=CRANK + (PIN0 + SMALL0) / 2, q=frame(SMALL0 - PIN0, (1, 0, 0)), mat="steel",
        bev=0.006)
rod.cyl(0.032, 0.05, c=CRANK + PIN0, axis="X", mat="steel_dark", sides=10, bev=0)

# ================================================================== flat belt (static runs) + lacing markers
B_C = V((XB, SHAFT.y, SHAFT.z))
E_C = V((XB, CRANK.y, CRANK.z))


def tangents(c1, r1, c2, r2):
    """External tangent points (YZ) of two circles for an open belt: returns [(p1, p2) upper, (p1, p2) lower]."""
    d = V((0, c2.y - c1.y, c2.z - c1.z))
    L = d.length
    ang = math.atan2(d.z, d.y)
    beta = math.acos((r1 - r2) / L)
    out = []
    for sgn in (1, -1):
        a = ang + sgn * beta
        n = V((0, math.cos(a), math.sin(a)))
        out.append((c1 + n * r1, c2 + n * r2))
    return out


(TU1, TU2), (TL1, TL2) = tangents(B_C, RB + 0.006, E_C, RE + 0.006)
BELT_W, BELT_T = 0.2, 0.008


def arc_pts(c, r, a0, a1, n):
    return [V((XB, c.y + r * math.cos(a0 + (a1 - a0) * i / n), c.z + r * math.sin(a0 + (a1 - a0) * i / n)))
            for i in range(n + 1)]


def ang_of(p, c):
    return math.atan2(p.z - c.z, p.y - c.y)


aU1, aL1 = ang_of(TU1, B_C), ang_of(TL1, B_C)
aU2, aL2 = ang_of(TU2, E_C), ang_of(TL2, E_C)
# wrap around the big pulley goes the long way (away from the engine), around the small one the short way
big_a0, big_a1 = aU1, aL1 + (math.tau if aL1 < aU1 else 0)
if big_a1 - big_a0 < math.pi:
    big_a0, big_a1 = aL1, aU1 + (math.tau if aU1 < aL1 else 0)
sm_a0, sm_a1 = aL2, aU2 + (math.tau if aU2 < aL2 else 0)
if sm_a1 - sm_a0 > math.pi * 1.5:
    sm_a0, sm_a1 = aU2, aL2 + (math.tau if aL2 < aU2 else 0)
SMALL = arc_pts(E_C, RE + 0.006, sm_a0, sm_a1, 10)
# belt path for the lacing markers (closed polyline), direction = belt travel
BIG = arc_pts(B_C, RB + 0.008, big_a0, big_a1, 40)
LOOP = BIG + list(reversed(SMALL)) if (BIG[-1] - SMALL[-1]).length < (BIG[-1] - SMALL[0]).length else BIG + SMALL
LOOP = [V((XB, p.y, p.z)) for p in LOOP]
SEGL = [(LOOP[(i + 1) % len(LOOP)] - LOOP[i]).length for i in range(len(LOOP))]
BRINGS = []                                                                                          # belt strip
for i, p in enumerate(LOOP):
    tg = (LOOP[(i + 1) % len(LOOP)] - LOOP[i - 1]).normalized()
    nrm = V((1, 0, 0)).cross(tg).normalized()
    BRINGS.append([p + V((-BELT_W / 2, 0, 0)) - nrm * BELT_T / 2, p + V((BELT_W / 2, 0, 0)) - nrm * BELT_T / 2,
                   p + V((BELT_W / 2, 0, 0)) + nrm * BELT_T / 2, p + V((-BELT_W / 2, 0, 0)) + nrm * BELT_T / 2])
body.loft(BRINGS + [BRINGS[0]], mat="leather", close=True, cap0=False, cap1=False, uv="box")
BELT_LEN = sum(SEGL)
NM = 4
belt_travel = TURNS * math.tau * RB                                                                  # 3 shaft turns
k_sp = max(1, round(belt_travel / (BELT_LEN / NM)))
MARK_TRAVEL = k_sp * BELT_LEN / NM


def belt_at(s):
    s %= BELT_LEN
    for i, L in enumerate(SEGL):
        if s <= L:
            a, b = LOOP[i], LOOP[(i + 1) % len(LOOP)]
            return a.lerp(b, s / L if L > 1e-9 else 0), (b - a).normalized()
        s -= L
    return LOOP[0], (LOOP[1] - LOOP[0]).normalized()


MARKS = []
for i in range(NM):
    mk = m.part(f"lacing_{i}")
    mk.box((BELT_W + 0.01, 0.026, 0.05), mat="steel_dark", bev=0)
    p, t = belt_at(i * BELT_LEN / NM)
    nrm = V((1, 0, 0)).cross(t).normalized()
    mk.place = (p, Matrix(((1, 0, 0), (0, nrm.y, t.y), (0, nrm.z, t.z))).to_quaternion())
    MARKS.append(mk.name)

# ================================================================== empties
m.empty("fx_work", (0, -0.31, 0.98))
m.empty("fx_ore", (0, -1.6, 0.55))
m.empty("op", (1.58, -0.98, 0.0))
m.empty("light_0", LAMP_C + V((0, 0, -0.06)), beam=V((0, -0.35, -1.0)))
m.empty("snd", (0, 0.0, 1.6))

lib.tick("build parts")
m.finish(rays=20, strength=1.15, low=0.38, noise_amt=0.2)
lib.tick("finish+grime")

# ================================================================== animation
G = 9.81
P = 1.0 / 1.2
T_CLIP = 5.0


def stamp_h(u):
    """Height above the die for stamp phase u in [0,1): cam lift, hold, free fall, rest."""
    if u < 0.55:
        k = u / 0.55
        return HMAX * (k * k * (3 - 2 * k) * 0.35 + k * 0.65)
    if u < 0.58:
        return HMAX
    if u < 0.8:
        tau = (u - 0.58) * P
        return max(0.0, HMAX - 0.5 * G * tau * tau)
    return 0.0


ANIM = ["camshaft", "fingers", "engine", "flywheels", "conrod", "lamp"] + STAMPS + MARKS
REST = {nm: m.objs[nm].location.copy() for nm in ANIM}
EOFF = m.objs["engine"].location.copy()
ROD_REST = m.objs["conrod"].location.copy()


def rig(t, working):
    out = {}
    th = -math.tau * TURNS * t if working else 0.0
    out["camshaft"] = {"q": Quaternion((1, 0, 0), th)}
    for s in range(1, 6):
        nm = f"stamp_{s}"
        if working:
            u = (TURNS * 2 * t - PHI[s]) % 1.0
            h = stamp_h(u)
        else:
            h = HUNG
        out[nm] = {"loc": REST[nm] + V((0, 0, h))}
    out["fingers"] = {"q": Quaternion((1, 0, 0), math.radians(-80) if working else 0.0)}
    the = -math.tau * 16 * t if working else 0.0
    out["flywheels"] = {"q": Quaternion((1, 0, 0), the)}
    pin, small = crank_rod(-the)
    pin0, small0 = crank_rod(0.0)
    d0 = (small0 - pin0).normalized()
    d1 = (small - pin).normalized()
    out["conrod"] = {"loc": ROD_REST - V((0, pin0.y, pin0.z)) + V((0, pin.y, pin.z)), "q": d0.rotation_difference(d1)}
    if working:
        rock = math.radians(0.7) * math.sin(math.tau * 10 * t) + math.radians(0.25) * math.sin(math.tau * 16 * t)
        out["engine"] = {"loc": EOFF + V((0, 0, 0.002 * math.sin(math.tau * 16 * t))), "q": Quaternion((1, 0, 0), rock)}
        out["lamp"] = {"q": Quaternion((1, 0, 0), math.radians(1.8) * math.sin(math.tau * 6 * t + 0.5))}
    for i, nm in enumerate(MARKS):
        s_ = i * BELT_LEN / NM - (MARK_TRAVEL * t if working else 0.0)
        p, tg = belt_at(s_)
        nrm = V((1, 0, 0)).cross(tg).normalized()
        out[nm] = {"loc": p, "q": Matrix(((1, 0, 0), (0, nrm.y, tg.y), (0, nrm.z, tg.z))).to_quaternion()}
    return out


m.clip("Work", T_CLIP, lambda t: rig(t, True), ANIM)
m.clip("Idle", 2.0, lambda t: rig(0.0, False), ANIM)
lib.tick("clips")
print(f"[stampmill] belt {BELT_LEN:.2f} m, markers advance {k_sp} spacings/loop "
      f"({MARK_TRAVEL / T_CLIP:.2f} m/s vs pulley {belt_travel / T_CLIP:.2f} m/s)")
print("[stampmill] impacts (s): " + ", ".join(f"S{s}@{((0.8 + PHI[s]) * P) % P:.3f}" for s in ORDER))
tris, size = m.report()
if stem:
    m.export(stem)
    lib.tick("export")
if "--no-render" not in flags:
    m.render([
        ("front3q", (-3.6, -5.6, 2.8), (0.2, 0.0, 1.6), 30),
        ("side", (6.4, -0.2, 2.0), (0.4, 0.2, 1.6), 34),
        ("rear3q", (4.4, 5.6, 3.0), (0.4, 0.4, 1.5), 30),
        ("close", (-1.3, -2.3, 2.3), (0.0, 0.0, 2.1), 36),
    ])
    m.pose("Work", 0.13)
    m.render([("work", (-3.6, -5.6, 2.8), (0.2, 0.0, 1.6), 30)])
    m.unpose()
