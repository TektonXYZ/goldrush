"""Comstock Powder Co. powder crew, 40% dynamite (GoldRush machines-A, tier 2).

A blasting set-up at the face. Toward the rock (+Z in three.js, the contract's working end) stands a timber-framed
drill-pattern face panel with a burn-cut round of 18 charged holes (+ an uncharged relief hole), coloured leg wires
hanging out of every hole and gathered into a lead line that runs across the floor over a wire reel to a T-handle
plunger blasting machine on a crate toward the drift. Open crates of red paper dynamite (COMSTOCK label decals), a
pneumatic stoper on a tripod drilling a lifter, a hand steel + 4 lb single jack, a tamping stick, a DANGER BLASTING
sign on a stand and a red flag. crew_1 works the face, op stands at the plunger.

Clips: Work (stoper vibration + rod spin, reel slowly paying out, flag stirring), Idle, Fire (1 s, non-looping:
the T-handle plunges down then rises; the game spawns the blast at fx_work = centre of the drilled face).

    systemd-run --user --scope -q -p MemoryMax=3G -p MemorySwapMax=0 \
        bl assets/machines_a/powder.py -- public/models/machines/powder [--no-render]
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
m = lib.Machine("powder")
rng = random.Random(41)

# ------------------------------------------------------------------ decals + custom materials
LABEL = ('<rect width="1000" height="420" fill="#E9DFC6"/>'
         '<rect x="14" y="14" width="972" height="392" fill="none" stroke="#B3221A" stroke-width="12"/>'
         '<text x="500" y="128" text-anchor="middle" font-family="Barlow Condensed Black" font-size="104" '
         'letter-spacing="6" fill="#B3221A">COMSTOCK POWDER CO.</text>'
         '<rect x="60" y="160" width="880" height="8" fill="#1A1A1A"/>'
         '<text x="500" y="300" text-anchor="middle" font-family="Barlow Condensed Black" font-size="150" '
         'letter-spacing="10" fill="#1A1A1A">40% · EXPLOSIVES</text>'
         '<text x="500" y="378" text-anchor="middle" font-family="Barlow Condensed ExtraBold" font-size="50" '
         'letter-spacing="8" fill="#B3221A">HIGH EXPLOSIVES · DANGEROUS</text>')
SIGN = ('<rect width="800" height="600" rx="24" fill="#B8141B"/>'
        '<rect x="20" y="20" width="760" height="560" rx="16" fill="none" stroke="#ECE6DA" stroke-width="10"/>'
        '<text x="400" y="200" text-anchor="middle" font-family="Barlow Condensed Black" font-size="190" '
        'letter-spacing="12" fill="#ECE6DA">DANGER</text>'
        '<text x="400" y="380" text-anchor="middle" font-family="Barlow Condensed Black" font-size="150" '
        'letter-spacing="10" fill="#ECE6DA">BLASTING</text>'
        '<text x="400" y="510" text-anchor="middle" font-family="Barlow Condensed ExtraBold" font-size="70" '
        'letter-spacing="8" fill="#ECE6DA">KEEP OUT · FIRE IN THE HOLE</text>')
A_ = m.atlas
A_.add("label", 1000, 420, lib.svg(1000, 420, LABEL, wear=0.5, seed=5))
A_.add("sign", 800, 600, lib.svg(800, 600, SIGN, wear=0.45, seed=7))
A_.add("detonator", 600, 170, lib.svg_text("COMSTOCK", font="Saira Stencil One", fill="#EDE6D2", wear=0.5, seed=9),
       fit=True)
A_.add("caps", 600, 200, lib.svg_text("BLASTING CAPS", font="Barlow Condensed Black", fill="#F2EBD8", wear=0.45,
                                      seed=11), fit=True)
A_.add("rnd", 700, 150, lib.svg_text("ROUND 12 · 18 HOLES", font="Barlow Condensed ExtraBold", fill="#F2EEE4",
                                     wear=0.5, seed=13), fit=True)
A_.add("crate_side", 700, 160, lib.svg_text("HANDLE WITH CARE", font="Barlow Condensed Black", fill="#1A1A1A", wear=0.55,
                                            seed=15), fit=True)
A_.build()
WIRES = {"y": "custom_wire_yellow", "b": "custom_wire_blue", "r": "custom_wire_red", "g": "custom_wire_green"}
lib.custom_mat("custom_wire_yellow", "#E2BC1E", rough=0.45)
lib.custom_mat("custom_wire_blue", "#2B5DB2", rough=0.45)
lib.custom_mat("custom_wire_red", "#B3221E", rough=0.45)
lib.custom_mat("custom_wire_green", "#2F8A40", rough=0.45)
lib.custom_mat("custom_dynamite", "#B1271E", rough=0.78)
lib.custom_mat("custom_flag", "#C4161C", rough=0.85)

body = m.part("powder_body")
FY = -3.55                                  # face panel front surface (+Y side faces the crew)

# ================================================================== drill-pattern face panel (timber set + planks)
for sx in (1, -1):
    body.box((0.24, 0.24, 2.75), c=(sx * 1.6, FY - 0.06, 1.375), mat="wood_timber", bev=0.02)        # posts
body.box((3.5, 0.26, 0.26), c=(0, FY - 0.06, 2.88), mat="wood_timber", bev=0.02)                   # cap
for k in range(11):                                                                                # plank face
    x = -1.42 + k * 0.284
    body.box((0.27, 0.06, 2.62), c=(x + rng.uniform(-0.004, 0.004), FY - 0.03, 1.33), mat="wood_planks", bev=0.006)
for sx in (1, -1):                                                                                  # wedges/blocking
    body.box((0.2, 0.12, 0.12), c=(sx * 1.25, FY - 0.15, 2.7), mat="wood_timber", bev=0.01)
    body.box((0.34, 0.4, 0.08), c=(sx * 1.6, FY + 0.05, 0.04), mat="wood_timber", bev=0.01)          # sills
body.decal("rnd", c=(0, FY + 0.003, 2.6), n=(0, 1, 0), w=0.8)
HOLES = []
for x, z in ((-0.13, 1.42), (0.13, 1.42), (-0.13, 1.18), (0.13, 1.18)):                           # cut
    HOLES.append((x, z, "y"))
for x, z in ((-0.55, 1.3), (0.55, 1.3), (0.0, 1.85), (0.0, 0.75)):                                  # easers
    HOLES.append((x, z, "b"))
for x in (-0.95, 0.0, 0.95):                                                                        # back holes
    HOLES.append((x, 2.42, "r"))
for x, z in ((-1.3, 0.85), (-1.3, 1.75), (1.3, 0.85), (1.3, 1.75)):                                 # rib holes
    HOLES.append((x, z, "g"))
for x in (-0.95, 0.0, 0.95):                                                                        # lifters
    HOLES.append((x, 0.25, "y"))
RELIEF = (0.0, 1.3)
for x, z, _ in HOLES:
    body.cyl(0.028, 0.03, c=(x, FY - 0.004, z), axis="Y", mat="steel_dark", sides=10, bev=0)          # hole (dark)
    body.lathe([(0.027, 0.0), (0.036, 0.0), (0.036, 0.006), (0.027, 0.006)], c=(x, FY + 0.001, z), rot=(-90, 0, 0),
               mat="rock_dark", sides=10, cap0=False, cap1=False)                                     # rim
    body.cyl(0.026, 0.012, c=(x, FY + 0.004, z), axis="Y", mat="wood_dark", sides=8, bev=0)           # stemming
body.cyl(0.055, 0.03, c=(RELIEF[0], FY - 0.004, RELIEF[1]), axis="Y", mat="steel_dark", sides=14, bev=0)
body.lathe([(0.054, 0.0), (0.066, 0.0), (0.066, 0.006), (0.054, 0.006)], c=(RELIEF[0], FY + 0.001, RELIEF[1]),
           rot=(-90, 0, 0), mat="rock_dark", sides=14, cap0=False, cap1=False)
# gold-quartz muck at the foot of the face
for k in range(70):
    s = rng.uniform(0.04, 0.12)
    x = rng.uniform(-1.4, 1.4)
    y = FY + 0.12 + abs(rng.gauss(0, 0.25))
    z = max(0.0, 0.22 - (y - FY) * 0.35) * (1 - abs(x) / 1.6) + s * 0.3
    body.rock(s, (x, y, z), seed=700 + k, mat="gold_ore", detail=1 if s > 0.08 else 0, squash=(1, 0.85, 0.7),
              rough=0.3)

# ================================================================== leg wires -> bundle -> lead line
BUNDLE = V((0.25, FY + 0.35, 0.18))
for i, (x, z, col) in enumerate(HOLES):
    start = V((x, FY + 0.01, z))
    for side, cm in ((-1, WIRES[col]), (1, WIRES["y" if col != "y" else "b"])):
        p0 = start + V((side * 0.006, 0.0, 0.0))
        drop = 0.18 + 0.12 * rng.random()
        mid = V(((x + BUNDLE.x) / 2 + side * 0.01, FY + 0.12, min(z, BUNDLE.z) - drop + (z - BUNDLE.z) * 0.35))
        mid.z = max(0.05, mid.z)
        pts = [p0, p0 + V((0, 0.06, -0.04)), mid, BUNDLE + V((side * 0.008, 0.0, 0.0))]
        body.path(pts, r=0.003, mat=cm, sides=4, res=5, caps=False)
body.cyl(0.014, 0.12, c=BUNDLE + V((0, 0.06, 0)), axis="Y", mat="cable", sides=8, bev=0)            # twisted bundle
body.cyl(0.018, 0.05, c=BUNDLE + V((0, 0.13, 0)), axis="Y", mat="plastic_black", sides=8, bev=0)     # splice tape
REEL = V((0.45, 0.2, 0.0))
LEAD = [BUNDLE + V((0, 0.16, 0)), V((0.3, FY + 0.8, 0.012)), V((0.42, -1.5, 0.012)), V((0.35, -0.6, 0.012)),
        V((0.45, REEL.y - 0.3, 0.06)), REEL + V((0.0, -0.05, 0.32))]
body.path(LEAD, r=0.0055, mat="cable", sides=5, res=6, caps=False)

# ================================================================== wire reel on a stand (animated: pays out)
for sx in (1, -1):
    body.rod(REEL + V((sx * 0.24, -0.25, 0.0)), REEL + V((sx * 0.24, 0.0, 0.42)), 0.018, mat="steel_dark", sides=6)
    body.rod(REEL + V((sx * 0.24, 0.25, 0.0)), REEL + V((sx * 0.24, 0.0, 0.42)), 0.018, mat="steel_dark", sides=6)
    body.box((0.05, 0.56, 0.03), c=REEL + V((sx * 0.24, 0.0, 0.015)), mat="steel_dark", bev=0)
body.cyl(0.015, 0.56, c=REEL + V((0, 0, 0.42)), axis="X", mat="steel", sides=8, bev=0)
reel = m.part("reel", origin=REEL + V((0, 0, 0.42)))
with reel.at(REEL + V((0, 0, 0.42)), rot=(0, 90, 0)):
    for sz in (-0.16, 0.16):
        reel.cyl(0.24, 0.025, c=(0, 0, sz), mat="wood_planks", sides=24, bev=0.004)
        for k in range(6):                                                                         # flange holes
            a = k / 6 * math.tau
            reel.cyl(0.03, 0.03, c=(math.cos(a) * 0.15, math.sin(a) * 0.15, sz), mat="wood_dark", sides=8, bev=0)
    reel.cyl(0.15, 0.3, mat="cable", sides=20, bev=0)                                             # wound wire
    for k in range(5):
        reel.lathe([(0.15, -0.14 + k * 0.06), (0.157, -0.12 + k * 0.06), (0.15, -0.1 + k * 0.06)], mat="cable",
                   sides=20, cap0=False, cap1=False)
    reel.cyl(0.04, 0.34, mat="steel_dark", sides=10, bev=0)
    reel.box((0.03, 0.03, 0.12), c=(0.17, 0.0, 0.0), mat="steel", bev=0)                         # handle stub
body.path([REEL + V((0.1, 0.12, 0.3)), REEL + V((0.1, 0.6, 0.03)), V((0.3, 1.6, 0.012)), V((0.15, 2.25, 0.012)),
           V((0.2, 2.4, 0.3)), V((0.12, 2.6, 0.78)), V((0.07, 2.67, 0.83))], r=0.0055, mat="cable", sides=5, res=6,
          caps=False)

# ================================================================== detonator crate + blasting machine
CR = V((0.0, 2.65, 0.0))
body.box((0.62, 0.46, 0.5), c=CR + V((0, 0, 0.25)), mat="wood_planks", bev=0.008)
for sx in (1, -1):
    for sy in (1, -1):
        body.box((0.05, 0.05, 0.52), c=CR + V((sx * 0.29, sy * 0.21, 0.26)), mat="wood_dark", bev=0.006)
body.decal("crate_side", c=CR + V((0, -0.232, 0.25)), n=(0, -1, 0), w=0.5)
BM = CR + V((0.0, -0.05, 0.5))
body.box((0.3, 0.2, 0.28), c=BM + V((0, 0, 0.14)), mat="wood_dark", bev=0.012)                      # box
body.box((0.31, 0.21, 0.03), c=BM + V((0, 0, 0.28)), mat="wood_dark", bev=0.006)
for sx in (1, -1):
    body.box((0.012, 0.21, 0.28), c=BM + V((sx * 0.15, 0, 0.14)), mat="brass", bev=0)                # corner straps
    body.cyl(0.012, 0.03, c=BM + V((sx * 0.07, 0.07, 0.31)), mat="brass", sides=8, bev=0)            # binding posts
    body.cyl(0.018, 0.012, c=BM + V((sx * 0.07, 0.07, 0.33)), mat="brass", sides=8, bev=0)
body.cyl(0.022, 0.04, c=BM + V((0, 0, 0.31)), mat="brass", sides=10, bev=0)                         # plunger guide
body.decal("detonator", c=BM + V((0, -0.103, 0.14)), n=(0, -1, 0), w=0.24)
body.tube([BM + V((-0.155, 0.0, 0.2)), BM + V((-0.2, 0.0, 0.42)), BM + V((0.0, 0.0, 0.52)), BM + V((0.2, 0.0, 0.42)),
           BM + V((0.155, 0.0, 0.2))], 0.008, mat="leather", sides=5, caps=False)                    # carry strap
plunger = m.part("plunger", origin=BM + V((0, 0, 0.33)))
plunger.cyl(0.011, 0.28, c=BM + V((0, 0, 0.47)), mat="steel", sides=8, bev=0)
plunger.cyl(0.02, 0.26, c=BM + V((0, 0, 0.61)), axis="X", mat="steel", sides=8, bev=0)
for sx in (1, -1):
    plunger.cyl(0.026, 0.09, c=BM + V((sx * 0.085, 0, 0.61)), axis="X", mat="wood_dark", sides=10, bev=0)
CAPS = CR + V((0.2, 0.12, 0.5))
body.box((0.14, 0.09, 0.05), c=CAPS + V((0, 0, 0.025)), mat="paint_red", bev=0.006)                 # caps tin
body.decal("caps", c=CAPS + V((0, 0, 0.0515)), n=(0, 0, 1), up=(0, 1, 0), w=0.12)

# ================================================================== dynamite crates (open) + loose sticks
def dyn_crate(c, yaw, lid_off=True, seed=0):
    q = Quaternion((0, 0, 1), math.radians(yaw))
    with body.at(c, q=q):
        body.box((0.52, 0.34, 0.03), c=(0, 0, 0.015), mat="wood_planks", bev=0.004)
        for sx in (1, -1):
            body.box((0.03, 0.34, 0.28), c=(sx * 0.245, 0, 0.14), mat="wood_planks", bev=0.004)
        for sy in (1, -1):
            body.box((0.46, 0.03, 0.28), c=(0, sy * 0.155, 0.14), mat="wood_planks", bev=0.004)
        r2 = random.Random(seed)
        for row in range(3):                                                                       # sticks in layers
            for k in range(7):
                yk = -0.12 + k * 0.04
                body.cyl(0.017, 0.2, c=(-0.11 + row * 0.0, yk, 0.06 + row * 0.034), axis="X", mat="custom_dynamite",
                         sides=8, bev=0)
                body.cyl(0.017, 0.2, c=(0.11, yk, 0.06 + row * 0.034), axis="X", mat="custom_dynamite", sides=8, bev=0)
        body.decal("label", c=(0, -0.172, 0.14), n=(0, -1, 0), w=0.42)
        body.decal("label", c=(0.262, 0, 0.14), n=(1, 0, 0), w=0.3)
    return q


dyn_crate(V((-1.35, -2.35, 0.0)), 12, seed=1)
dyn_crate(V((-1.05, -1.6, 0.0)), -8, seed=2)
with body.at(V((-1.6, -1.75, 0.25)), rot=(0, -70, 20)):                                            # leaning lid
    body.box((0.52, 0.34, 0.025), c=(0, 0, 0.0), mat="wood_planks", bev=0.004)
    body.decal("label", c=(0, 0, 0.0135), n=(0, 0, 1), up=(1, 0, 0), w=0.4)
for k in range(5):                                                                                  # loose sticks
    a = rng.uniform(0, math.tau)
    body.cyl(0.017, 0.2, c=(-0.75 + rng.uniform(-0.15, 0.15), -2.75 + rng.uniform(-0.1, 0.1), 0.017),
             rot=(0, 90, math.degrees(a)), mat="custom_dynamite", sides=8, bev=0)
body.cyl(0.017, 0.2, c=V((-0.6, -2.95, 0.017)), rot=(0, 90, 25), mat="custom_dynamite", sides=8, bev=0)
body.cyl(0.006, 0.05, c=V((-0.5, -2.9, 0.02)), rot=(0, 90, 25), mat="aluminium", sides=6, bev=0)

# ================================================================== stoper drill on a tripod (animated)
HOLE_T = V((0.95, FY + 0.01, 0.25))                                                                 # lifter it drills
DDIR = V((0.0, -1.0, -0.06)).normalized()
DCH = HOLE_T - DDIR * 0.9                                                                            # chuck point
QD = frame(DDIR, (1, 0, 0))
TRI = V((0.98, -2.15, 0.0))
for k in range(3):
    a = k / 3 * math.tau + 0.3
    body.rod(TRI + V((math.cos(a) * 0.45, math.sin(a) * 0.45, 0.0)), DCH + V((0, 0.35, -0.08)), 0.02,
             mat="steel_dark", sides=6)
body.box((0.12, 0.3, 0.06), c=DCH + V((0, 0.35, -0.11)), mat="steel_dark", bev=0.008)               # cradle
stoper = m.part("stoper", origin=DCH)
with stoper.at(DCH, q=QD):
    stoper.cyl(0.04, 0.12, c=(0, 0, -0.06), mat="steel", sides=14, bev=0.004)
    stoper.cyl(0.058, 0.36, c=(0, 0, -0.3), mat="paint_grey", sides=16, bev=0.006)
    for sx in (1, -1):
        stoper.cyl(0.01, 0.52, c=(sx * 0.066, 0, -0.3), mat="steel", sides=6, bev=0)
    stoper.cyl(0.066, 0.12, c=(0, 0, -0.54), mat="steel", sides=16, bev=0.006)
    stoper.rod((0, 0, -0.6), (0, 0, -0.72), 0.016, mat="steel", sides=8)
    stoper.rod((-0.15, 0, -0.74), (0.15, 0, -0.74), 0.014, mat="steel", sides=8)
    for sx in (1, -1):
        stoper.cyl(0.022, 0.1, c=(sx * 0.11, 0, -0.74), rot=(0, 90, 0), mat="rubber", sides=10, bev=0)
    stoper.cyl(0.02, 0.08, c=(0, 0.07, -0.55), rot=(90, 0, 0), mat="brass", sides=8, bev=0)
    stoper.cyl(0.013, 0.9, c=(0, 0, 0.45), mat="steel", sides=6, bev=0)                            # drill steel
    stoper.cyl(0.019, 0.04, c=(0, 0, 0.02), mat="steel_dark", sides=8, bev=0)
AIR_IN = DCH + QD @ V((0, 0.11, -0.55))
body.path([AIR_IN, AIR_IN + V((0.0, 0.05, 0.1)), AIR_IN + V((0.1, 0.35, 0.0)), V((1.3, -1.2, 0.024)), V((1.5, 0.4, 0.024)),
           V((1.75, 2.0, 0.024)), V((2.05, 3.3, 0.024))], r=0.022, mat="hose_yellow", sides=10, res=5)

# ================================================================== hand steel, single jack, tamping stick
body.cyl(0.012, 0.55, c=V((-0.55, FY + 0.27, 1.3)), q=aim(V((0, 1, 0.12))), mat="steel", sides=6, bev=0)  # in a hole
with body.at(V((0.35, -2.6, 0.0)), rot=(0, 0, 35)):
    body.box((0.06, 0.06, 0.15), c=(0.0, 0.0, 0.03), rot=(0, 90, 0), mat="steel_dark", bev=0.006)      # 4 lb head
    body.rod((0.0, 0.03, 0.03), (0.0, 0.38, 0.03), 0.014, mat="wood_planks", sides=8)               # handle
body.rod(V((-0.95, FY + 0.12, 0.0)), V((-0.82, FY + 0.05, 1.55)), 0.022, mat="wood_planks", sides=8)  # tamping stick
body.cyl(0.026, 0.06, c=V((-0.82, FY + 0.05, 1.56)), q=aim(V((0.13, -0.07, 1.55))), mat="wood_dark", sides=8, bev=0)

# ================================================================== DANGER sign on a stand + red flag
SG = V((-1.55, 2.25, 0.0))
with body.at(SG, rot=(0, 0, 25)):
    for sx in (1, -1):
        body.rod((sx * 0.32, 0.0, 0.0), (sx * 0.3, 0.0, 1.55), 0.025, mat="wood_timber", sides=6)
        body.box((0.08, 0.45, 0.06), c=(sx * 0.32, 0.0, 0.03), mat="wood_timber", bev=0.008)
    body.box((0.8, 0.03, 0.6), c=(0, 0.0, 1.3), mat="wood_painted_red", bev=0.006)
    body.decal("sign", c=(0, 0.0165, 1.3), n=(0, 1, 0), w=0.78)
    body.decal("sign", c=(0, -0.0165, 1.3), n=(0, -1, 0), w=0.78)
    body.box((0.66, 0.03, 0.04), c=(0, 0.0, 0.5), mat="wood_timber", bev=0)
FLAGP = V((1.62, 1.9, 0.0))
body.box((0.3, 0.3, 0.16), c=FLAGP + V((0, 0, 0.08)), mat="canvas", bev=0.05)                       # sandbag
body.cyl(0.015, 1.9, c=FLAGP + V((0, 0, 1.05)), mat="wood_planks", sides=8, bev=0)
flag = m.part("flag", origin=FLAGP + V((0, 0, 1.92)))
for k in range(6):
    u0, u1 = k / 6, (k + 1) / 6
    w0, w1 = 0.04 * math.sin(u0 * 4.5), 0.04 * math.sin(u1 * 4.5)
    for (xa, xb, wa, wb) in ((u0 * 0.5, u1 * 0.5, w0, w1),):
        c = FLAGP + V(((xa + xb) / 2 + 0.01, (wa + wb) / 2, 1.73))
        flag.box((0.5 / 6 + 0.002, 0.006, 0.34 - k * 0.012), c=c, rot=(0, 0, math.degrees(math.atan2(wb - wa, 0.5 / 6))),
                 mat="custom_flag", bev=0)

# ================================================================== work light on a stand -> light_0
LS = V((-1.4, -0.4, 0.0))
for k in range(3):
    a = k / 3 * math.tau + 0.2
    body.rod(LS + V((math.cos(a) * 0.4, math.sin(a) * 0.4, 0.0)), LS + V((0, 0, 0.72)), 0.014, mat="steel_dark", sides=6)
body.cyl(0.022, 1.25, c=LS + V((0, 0, 1.22)), mat="aluminium", sides=8, bev=0)
LDIR = V((0.42, -1.0, -0.42)).normalized()
LENS = lib.work_light(body, LS + V((0, 0, 1.92)), LDIR, kind="bar", r=0.11)
body.path([LS + V((0, 0, 1.6)), LS + V((0.05, 0.03, 0.9)), LS + V((0.15, 0.1, 0.1)), LS + V((0.3, 0.4, 0.015)),
           V((-1.0, 1.4, 0.015)), V((-1.25, 3.3, 0.015))], r=0.01, mat="cable", sides=6, res=4)

# ================================================================== empties
m.empty("crew_1", (0.45, -2.75, 0.0))
m.empty("op", (0.0, 3.12, 0.0))
m.empty("fx_work", (0.0, FY + 0.15, 1.3))
m.empty("fx_ore", (0.0, FY + 0.45, 0.1))
m.empty("light_0", LENS, beam=LDIR)
m.empty("snd", (0.0, -1.0, 1.1))

lib.tick("build parts")
m.finish(rays=20, strength=1.1, low=0.35, noise_amt=0.18)
lib.tick("finish+grime")

ANIM = ["stoper", "reel", "flag", "plunger"]
NF = 120
JIT = [(rng.uniform(-1, 1), rng.uniform(-1, 1)) for _ in range(NF + 1)]
S0 = m.objs["stoper"].location.copy()
RIGHT = QD @ V((1, 0, 0))
UPV = QD @ V((0, 1, 0))
P0 = m.objs["plunger"].location.copy()


def work(t):
    f = int(round(t * NF)) % NF
    jx, jy = JIT[f]
    off = DDIR * (0.004 if f % 2 else -0.003) + RIGHT * 0.0012 * jx + UPV * 0.0012 * jy
    return {
        "stoper": {"loc": S0 + off},
        "reel": {"q": Quaternion((1, 0, 0), -math.radians(60) * t)},
        "flag": {"q": Quaternion((0, 0, 1), math.radians(6) * math.sin(math.tau * 2 * t))
                 @ Quaternion((1, 0, 0), math.radians(2) * math.sin(math.tau * 3 * t + 1.0))},
    }


def fire(t):
    if t < 0.12:
        d = lib.smooth(t / 0.12)
    elif t < 0.3:
        d = 1.0
    else:
        d = 1.0 - lib.smooth((t - 0.3) / 0.7)
    return {"plunger": {"loc": P0 + V((0, 0, -0.17 * d))}}


m.clip("Work", 4.0, work, ANIM)
m.clip("Idle", 2.0, None, ANIM)
m.clip("Fire", 1.0, fire, ["plunger"])
lib.tick("clips")
tris, size = m.report()
if stem:
    m.export(stem)
    lib.tick("export")
if "--no-render" not in flags:
    m.render([
        ("front3q", (3.4, -0.4, 2.6), (0.0, -2.6, 1.0), 32),
        ("side", (6.6, 0.0, 1.7), (0.0, 0.0, 0.8), 34),
        ("rear3q", (-3.2, 6.2, 2.8), (0.0, 0.5, 0.8), 32),
        ("close", (1.2, 1.4, 1.5), (0.0, 2.6, 0.75), 40),
        ("face", (0.6, -1.0, 1.6), (0.0, FY, 1.2), 40),
    ])
    m.pose("Fire", 0.2)
    m.render([("fire", (1.2, 1.4, 1.5), (0.0, 2.6, 0.75), 40)])
    m.unpose()
