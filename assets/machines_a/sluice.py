"""Placer & Sons SB-12 riffle box (GoldRush machines-A, tier 1).

A 4.5 m wooden sluice on timber trestles sloped 8 deg toward the front (the face): ribbed rubber matting under
steel riffles, a translucent water sheet (custom_sluice_water, scrolled by the game), a head box at the high end
with a rocking classifier screen fed by a lay-flat hose from a little gas pump (tube frame, recoil starter, tank)
that draws from a sump puddle. A gold-quartz gravel pile with a shovel, a loaded wheelbarrow, a tailings fan at
the low end and a work light. crew_1 = the shovelling miner.

    systemd-run --user --scope -q -p MemoryMax=3G -p MemorySwapMax=0 \
        bl assets/machines_a/sluice.py -- public/models/machines/sluice [--no-render]
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
m = lib.Machine("sluice")
rng = random.Random(7)

# ------------------------------------------------------------------ decals + water texture
A_ = m.atlas
A_.add("maker", 900, 170, lib.svg_text("PLACER & SONS", font="Saira Stencil One", fill="#EDE8DC", wear=0.6, seed=7),
       fit=True)
A_.add("model", 600, 150, lib.svg_text("SB-12  RIFFLE BOX", font="Barlow Condensed Black", fill="#EDE8DC", wear=0.55,
                                       seed=9), fit=True)
A_.add("sacramento", 700, 120, lib.svg_text("SACRAMENTO CAL.", font="Barlow Condensed ExtraBold", fill="#EDE8DC",
                                            wear=0.6, seed=11), fit=True)
A_.add("pump", 600, 200, lib.svg_logo(600, 200, "PLACER", kind="slab", wear=0.3, seed=13))
A_.add("hot", 512, 360, lib.svg_panel(512, 360, "CAUTION", ["HOT MUFFLER", "STOP ENGINE TO FUEL"], seed=15))
A_.build()
WATER = lib.Atlas("sluice_water", width=256, mat_name="custom_sluice_water", rough=0.06)
WATER.add("w", 256, 512, lib.svg(256, 512, (
    '<filter id="t" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency="0.05 0.011" '
    'numOctaves="4" seed="3" stitchTiles="stitch"/>'
    '<feColorMatrix type="matrix" values="0.45 0 0 0 0.14  0.43 0 0 0 0.135  0.36 0 0 0 0.11  0.5 0 0 0 0.1"/></filter>'
    '<rect width="256" height="512" filter="url(#t)"/>')))
WATER.build()
lib.CLEAN.add("custom_sluice_water")

body = m.part("sluice_body")
SLOPE = math.radians(8.0)
HI = V((0, 1.9, 0.95))                     # trough floor at the high end (centre)
LEN = 4.5
DIR = V((0, -math.cos(SLOPE), -math.sin(SLOPE)))   # downhill along the trough
LO = HI + DIR * LEN                        # trough floor at the low end
MID = (HI + LO) / 2
QT = Quaternion((1, 0, 0), SLOPE)          # trough frame: local +Y uphill, +Z up from the floor


def zfloor(y):
    return HI.z + (y - HI.y) * math.tan(SLOPE)


# ================================================================== trough (planks, cleats, matting, riffles)
with body.at(MID, q=QT):
    body.box((0.7, LEN, 0.045), c=(0, 0, -0.0225), mat="wood_planks", bev=0.006)                    # floor
    for sx in (1, -1):
        for j in range(2):
            body.box((0.045, LEN, 0.16), c=(sx * 0.3225, 0, 0.06 + j * 0.162), mat="wood_planks", bev=0.006)
        body.box((0.07, LEN + 0.02, 0.035), c=(sx * 0.335, 0, 0.36), mat="wood_timber", bev=0.008)  # top rail
        for k in range(7):                                                                          # cleats
            body.box((0.035, 0.06, 0.4), c=(sx * 0.362, -LEN / 2 + 0.25 + k * (LEN - 0.5) / 6, 0.17),
                     mat="wood_timber", bev=0.006)
            for zz in (0.06, 0.28):
                body.cyl(0.008, 0.012, c=(sx * 0.381, -LEN / 2 + 0.25 + k * (LEN - 0.5) / 6, zz), axis="X",
                         mat="steel_dark", sides=6, bev=0)
    body.box((0.6, LEN - 0.35, 0.012), c=(0, -0.1, 0.006), mat="rubber", bev=0)                    # matting
    for k in range(64):                                                                            # mat ribs
        body.box((0.6, 0.012, 0.01), c=(0, -LEN / 2 + 0.12 + k * 0.064, 0.016), mat="rubber", bev=0)
    for sx in (1, -1):                                                                             # riffle rails
        body.box((0.02, LEN - 0.5, 0.05), c=(sx * 0.285, -0.2, 0.037), mat="steel_dark", bev=0)
    for k in range(25):                                                                            # angle riffles
        y = -LEN / 2 + 0.3 + k * 0.155
        body.box((0.55, 0.004, 0.04), c=(0, y, 0.034), rot=(-40, 0, 0), mat="steel", bev=0)
        body.box((0.55, 0.03, 0.004), c=(0, y + 0.014, 0.05), mat="steel", bev=0)
    body.box((0.66, 0.08, 0.004), c=(0, -LEN / 2 + 0.03, 0.002), rot=(-10, 0, 0), mat="steel", bev=0)  # spill lip
    for k in range(3):                                                                             # gold catch
        body.box((0.5, 0.02, 0.012), c=(0, -LEN / 2 + 0.12 + k * 0.05, 0.03), mat="gold", bev=0)
    body.decal("maker", c=(0.346, 0.333, 0.16), n=(1, 0, 0), w=0.56)
    body.decal("model", c=(0.346, -1.0, 0.16), n=(1, 0, 0), w=0.54)
    body.decal("maker", c=(-0.346, 0.333, 0.16), n=(-1, 0, 0), w=0.56)
    # water sheet over the riffles (scrolled by the game): quads along the flow, slight ripple
    rows = []
    NL = 18
    for i in range(NL + 1):
        y = LEN / 2 - 0.42 - i * (LEN - 0.48) / NL
        row = []
        for j in range(5):
            x = -0.285 + j * 0.1425
            dz = 0.004 * noise.noise(V((x * 9, y * 3, 1.7)))
            row.append((x, y, 0.062 + dz))
        rows.append(row)
    for i in range(NL):
        for j in range(4):
            a, b, c, d = rows[i][j], rows[i][j + 1], rows[i + 1][j + 1], rows[i + 1][j]
            va, vc = (LEN / 2 - 0.42 - a[1]) / 1.2, (LEN / 2 - 0.42 - c[1]) / 1.2
            body.quad([d, c, b, a], "custom_sluice_water", [(j / 4, vc), ((j + 1) / 4, vc), ((j + 1) / 4, va), (j / 4, va)])
    # falling sheet over the lip
    ylip = -LEN / 2 + 0.06
    kz = LO.z - 0.015
    curve = [(ylip, 0.062), (ylip - 0.05, 0.05), (ylip - 0.1, 0.0), (ylip - 0.13, -0.3 * kz), (ylip - 0.15, -0.62 * kz),
             (ylip - 0.16, -0.97 * kz)]
    for i in range(len(curve) - 1):
        (y0, z0), (y1, z1) = curve[i], curve[i + 1]
        w0, w1 = 0.29 - i * 0.01, 0.29 - (i + 1) * 0.01
        body.quad([(-w1, y1, z1), (w1, y1, z1), (w0, y0, z0), (-w0, y0, z0)], "custom_sluice_water",
                  [(0, 3.0 + i * 0.15 + 0.15), (1, 3.0 + i * 0.15 + 0.15), (1, 3.0 + i * 0.15), (0, 3.0 + i * 0.15)])

# trestles (3 A-frames)
for yy in (LO.y + 0.5, (LO.y + HI.y) / 2, HI.y - 0.55):
    zt = zfloor(yy) - 0.05
    body.box((1.0, 0.12, 0.1), c=(0, yy, zt - 0.05), mat="wood_timber", bev=0.012)                   # cap
    for sx in (1, -1):
        for sy in (1, -1):
            body.rod((sx * 0.45, yy + sy * 0.18, 0.0), (sx * 0.38, yy + sy * 0.05, zt - 0.08), 0.045,
                     mat="wood_timber", sides=6, bev=0.004)
        body.box((0.08, 0.5, 0.08), c=(sx * 0.42, yy, 0.35), mat="wood_timber", bev=0.01)            # tie
    body.rod((-0.43, yy, 0.35), (0.38, yy, zt - 0.1), 0.03, mat="wood_timber", sides=6, bev=0)        # brace
    for sx in (1, -1):
        body.cyl(0.012, 0.012, c=(sx * 0.46, yy, zt - 0.05), axis="X", mat="steel_dark", sides=6, bev=0)

# ================================================================== head box + spray bar
HB = HI + V((0, 0.35, 0.02))
body.box((0.86, 0.7, 0.04), c=HB + V((0, 0, 0.0)), mat="wood_planks", bev=0.006)
for sx in (1, -1):
    body.box((0.04, 0.7, 0.35), c=HB + V((sx * 0.43, 0, 0.175)), mat="wood_planks", bev=0.006)
body.box((0.86, 0.04, 0.35), c=HB + V((0, 0.35, 0.175)), mat="wood_planks", bev=0.006)
body.box((0.86, 0.04, 0.22), c=HB + V((0, -0.35, 0.24)), mat="wood_planks", bev=0.006)               # weir (gap below)
for sx in (1, -1):                                                                                  # corner posts
    for sy in (1, -1):
        body.box((0.07, 0.07, HB.z + 0.37), c=(sx * 0.43, HB.y + sy * 0.33, (HB.z + 0.37) / 2), mat="wood_timber",
                 bev=0.01)
for sx in (1, -1):
    body.box((0.05, 0.75, 0.05), c=HB + V((sx * 0.43, 0, 0.37)), mat="steel_dark", bev=0)            # rocker rails
body.decal("sacramento", c=HB + V((0, 0.3725, 0.17)), n=(0, 1, 0), w=0.6)
SPRAY = HB + V((0, 0.42, 0.62))
body.cyl(0.024, 0.8, c=SPRAY, axis="X", mat="galvanized", sides=10, bev=0)
for k in range(7):
    body.cyl(0.008, 0.03, c=SPRAY + V((-0.33 + k * 0.11, -0.025, -0.012)), rot=(60, 0, 0), mat="brass", sides=6,
             bev=0)
for sx in (1, -1):
    body.rod(V((sx * 0.43, HB.y + 0.37, HB.z + 0.35)), SPRAY + V((sx * 0.4, 0, 0)), 0.014, mat="galvanized", sides=6)
body.cyl(0.03, 0.12, c=SPRAY + V((0.46, 0, 0)), axis="X", mat="brass", sides=10, bev=0)               # hose tail

# ================================================================== classifier (animated rocker)
CL = HB + V((0, 0.0, 0.395))                                                                        # rail contact
cls = m.part("classifier", origin=CL)
with cls.at(CL, q=Quaternion()):
    arc = [(math.sin(a) * 0.5, 0.5 - math.cos(a) * 0.5) for a in [math.radians(-42 + 84 * i / 10) for i in range(11)]]
    for sx in (1, -1):
        cls.plate(arc + [(arc[-1][0], 0.15), (arc[0][0], 0.15)], 0.04, "YZ", at=sx * 0.43, mat="wood_timber",
                  bev=0.006)                                                                         # curved rocker
        cls.box((0.035, 0.82, 0.22), c=(sx * 0.41, 0, 0.21), mat="wood_planks", bev=0.006)
    for sy in (1, -1):
        cls.box((0.86, 0.035, 0.22), c=(0, sy * 0.4, 0.21), mat="wood_planks", bev=0.006)
    cls.mesh_panel((0, 0, 0.11), 0.8, 0.78, cell=0.035, wire=0.004, rot=(90, 0, 0), mat="steel")
    cls.rod((-0.36, 0.4, 0.3), (-0.36, 0.7, 0.5), 0.02, mat="wood_dark", sides=8)                     # rocking handle
    cls.rod((-0.36, 0.7, 0.5), (-0.2, 0.7, 0.5), 0.02, mat="wood_dark", sides=8)
    for k in range(18):                                                                            # gravel on screen
        sz = rng.uniform(0.03, 0.06)
        cls.rock(sz, (rng.uniform(-0.32, 0.32), rng.uniform(-0.3, 0.3), 0.13 + sz * 0.4), seed=300 + k, mat="gold_ore",
                 detail=0, squash=(1, 0.9, 0.7), rough=0.3)

# ================================================================== pump (animated vibration) + hoses
PC = V((1.3, 1.55, 0.0))
pump = m.part("pump", origin=PC)
with pump.at(PC, rot=(0, 0, -15)):
    for sx in (1, -1):                                                                              # tube frame
        pump.path([(sx * 0.2, -0.3, 0.02), (sx * 0.2, 0.3, 0.02), (sx * 0.2, 0.32, 0.42), (sx * 0.2, -0.32, 0.42),
                   (sx * 0.2, -0.3, 0.02)], r=0.014, mat="paint_red", sides=8, res=3)
    for yy, zz in ((-0.3, 0.02), (0.3, 0.02), (0.32, 0.42), (-0.32, 0.42)):
        pump.rod((-0.2, yy, zz), (0.2, yy, zz), 0.014, mat="paint_red", sides=8)
    for sx in (1, -1):
        for sy in (1, -1):
            pump.box((0.05, 0.05, 0.02), c=(sx * 0.2, sy * 0.28, 0.0), mat="rubber", bev=0)
    pump.box((0.24, 0.22, 0.2), c=(0.0, 0.05, 0.16), mat="aluminium", bev=0.02)                     # crankcase
    with pump.at((0.06, 0.05, 0.3), rot=(0, 30, 0)):                                                 # finned cylinder
        pump.cyl(0.06, 0.16, c=(0, 0, 0.08), mat="aluminium", sides=12, bev=0)
        for k in range(6):
            pump.box((0.15, 0.15, 0.008), c=(0, 0, 0.02 + k * 0.024), mat="aluminium", bev=0)
        pump.box((0.13, 0.13, 0.04), c=(0, 0, 0.18), mat="steel_dark", bev=0.01)
    pump.lathe([(0.0, 0.0), (0.11, 0.0), (0.11, 0.05), (0.09, 0.07), (0.0, 0.07)], c=(-0.13, 0.05, 0.17),
               rot=(0, -90, 0), mat="paint_black", sides=18, angle=25)                               # recoil starter
    pump.rod((-0.2, 0.05, 0.19), (-0.24, 0.05, 0.19), 0.006, mat="cable", sides=5)
    pump.cyl(0.012, 0.08, c=(-0.25, 0.05, 0.19), axis="Y", mat="plastic_black", sides=8, bev=0)       # T-handle
    pump.box((0.26, 0.22, 0.11), c=(0.0, 0.08, 0.47), mat="paint_red", bev=0.03)                     # fuel tank
    pump.cyl(0.028, 0.025, c=(0.06, 0.12, 0.535), mat="plastic_black", sides=12, bev=0.004)
    pump.box((0.1, 0.08, 0.12), c=(-0.06, -0.12, 0.32), mat="plastic_black", bev=0.015)              # air filter
    pump.cyl(0.045, 0.16, c=(0.15, 0.2, 0.25), axis="Y", mat="steel_dark", sides=12, bev=0)          # muffler
    pump.box((0.11, 0.18, 0.006), c=(0.15, 0.2, 0.3), mat="steel", bev=0)
    pump.decal("hot", c=(0.15, 0.2, 0.304), n=(0, 0, 1), up=(0, 1, 0), w=0.1)
    pump.lathe([(0.0, 0.0), (0.12, 0.0), (0.13, 0.03), (0.13, 0.09), (0.1, 0.11), (0.0, 0.11)],
               c=(0.0, -0.08, 0.16), rot=(90, 0, 0), mat="aluminium", sides=18, angle=25)            # pump volute
    pump.cyl(0.035, 0.08, c=(0.0, -0.22, 0.12), axis="Y", mat="aluminium", sides=12, bev=0)          # suction port
    pump.cyl(0.03, 0.1, c=(0.0, -0.13, 0.31), mat="aluminium", sides=12, bev=0)                      # discharge port
    pump.decal("pump", c=(0.1205 + 0.002, 0.05, 0.16), n=(1, 0, 0), w=0.14)
SUCK = PC + Quaternion((0, 0, 1), math.radians(-15)) @ V((0.0, -0.26, 0.12))
DIS = PC + Quaternion((0, 0, 1), math.radians(-15)) @ V((0.0, -0.13, 0.36))
SUMP = V((1.85, 0.55, 0.0))
SP = body.path([SUCK, SUCK + V((0.05, -0.25, -0.02)), V((1.7, 0.95, 0.05)), V((1.82, 0.7, 0.04)),
                SUMP + V((0, 0.0, 0.04))], r=0.032, mat="rubber", sides=10, res=6)
for k in range(2, len(SP) - 2, 2):                                                                   # corrugations
    body.cyl(0.037, 0.012, c=SP[k], q=aim(SP[k + 1] - SP[k - 1]), mat="rubber", sides=10, bev=0)
body.cyl(0.05, 0.12, c=SUMP + V((0, 0, 0.06)), mat="steel_dark", sides=12, bev=0)                    # strainer
body.mesh_panel(SUMP + V((0, -0.052, 0.06)), 0.08, 0.1, cell=0.02, wire=0.003)
# sump puddle: mud ring + water surface
ring = []
for k in range(20):
    a = k / 20 * math.tau
    rr = 0.42 + 0.07 * noise.noise(V((math.cos(a) * 2, math.sin(a) * 2, 4.0)))
    ring.append((SUMP.x + math.cos(a) * rr, SUMP.y + math.sin(a) * rr * 0.8))
mud = [[(SUMP.x + (x - SUMP.x) * s, SUMP.y + (y - SUMP.y) * s, z) for (x, y) in ring]
       for s, z in ((1.25, 0.0), (1.08, 0.035), (0.98, 0.02))]
body.loft(mud, mat="dirt", close=True, cap0=False, cap1=False, uv="box")
for k in range(20):
    x0, y0 = ring[k]
    x1, y1 = ring[(k + 1) % 20]
    body.quad([(x1, y1, 0.012), (x0, y0, 0.012), (SUMP.x, SUMP.y, 0.012), (SUMP.x + 0.0001, SUMP.y, 0.012)],
              "custom_sluice_water",
              [(0.5 + (x1 - SUMP.x), 0.5 + (y1 - SUMP.y)), (0.5 + (x0 - SUMP.x), 0.5 + (y0 - SUMP.y)), (0.5, 0.5),
               (0.5, 0.5)])
# lay-flat discharge hose: floor run (static) + the climb to the spray bar (wobbles)
CLIMB0 = V((0.62, HB.y + 0.46, 0.03))
FLOOR_PTS = [DIS, DIS + V((0.0, 0.0, 0.1)), DIS + V((-0.08, 0.15, 0.05)), V((1.0, 2.35, 0.03)), CLIMB0]
body.path(FLOOR_PTS, r=0.035, mat="hose_red", sides=10, res=6, flat=0.45)
hose = m.part("hose_climb", origin=CLIMB0)
hose.path([CLIMB0, CLIMB0 + V((-0.06, -0.02, 0.18)), V((0.51, HB.y + 0.43, 0.75)), V((0.52, HB.y + 0.43, SPRAY.z - 0.2)),
           SPRAY + V((0.53, 0.0, -0.06)), SPRAY + V((0.52, 0, 0))], r=0.035, mat="hose_red", sides=10, res=6, flat=0.8)
for zz in (0.45, 0.85):                                                                              # hose clips
    body.box((0.03, 0.09, 0.03), c=(0.47, HB.y + 0.4, zz), mat="steel_dark", bev=0)
hose.cyl(0.042, 0.06, c=SPRAY + V((0.5, 0, 0)), axis="X", mat="steel", sides=10, bev=0)

# ================================================================== gravel pile, shovel, barrow, tailings, light
PILE = V((1.15, 2.85, 0.0))
pile = []
for i in range(7):
    t = 0.93 * i / 6
    ring_ = []
    for k in range(16):
        a = k / 16 * math.tau
        rr = 0.75 * (1 - t ** 1.5)
        x, y = PILE.x + math.cos(a) * rr, PILE.y + math.sin(a) * rr * 0.85
        n_ = noise.noise(V((x * 2.5, y * 2.5, 5.0)))
        ring_.append((x + 0.05 * n_, y + 0.05 * n_, 0.55 * math.sin(t * math.pi / 2) + 0.04 * n_ if i else 0.0))
    pile.append(ring_)
gravel = m.part("gravel")
gravel.sharp = 14.0
gravel.loft(pile, mat="gravel", close=True, cap0=False, cap1=False, uv="box")
for k in range(150):
    a = rng.uniform(0, math.tau)
    rr = rng.uniform(0, 1.02) ** 0.65
    x, y = PILE.x + math.cos(a) * 0.75 * rr, PILE.y + math.sin(a) * 0.64 * rr
    s = rng.uniform(0.03, 0.09)
    z = 0.55 * max(0.0, 1 - rr ** 1.5) ** 0.75 + s * 0.25
    gravel.rock(s, (x, y, z), seed=600 + k, mat="gold_ore" if rng.random() < 0.6 else "gravel",
                detail=1 if s > 0.06 else 0, squash=(1, 0.9, 0.7), rough=0.3)
SH0 = PILE + V((-0.25, -0.2, 0.42))
d = V((0.35, 0.25, 0.95)).normalized()
with body.at(SH0, q=frame(-d, (1, 0, 0))):
    body.box((0.25, 0.012, 0.3), c=(0, 0, 0.15), mat="steel", bev=0.003)
body.rod(SH0 - d * 0.02, SH0 + d * 1.05, 0.017, mat="wood_planks", sides=8)
with body.at(SH0 + d * 1.1, q=frame(d, (1, 0, 0))):
    body.box((0.13, 0.025, 0.025), c=(0, 0, 0.04), mat="wood_dark", bev=0)
lib.wheelbarrow(body, V((-1.35, 2.75, 0.0)), yaw=200.0, tray="paint_green", load="gold_ore", load_seed=3)
# tailings fan (washed gravel + spreading water film) at the low end
TF = LO + V((0, -0.25, 0))
fan_rings = []
for i, (sc, zz) in enumerate(((1.0, 0.0), (0.82, 0.06), (0.55, 0.1))):
    rr = []
    for k in range(13):
        a = math.radians(-160 + 140 * k / 12)
        rad = (1.1 + 0.12 * noise.noise(V((k * 0.7, 2.0, 1.0)))) * sc
        rr.append((TF.x + math.cos(a) * rad * 1.1, TF.y + 0.15 + math.sin(a) * rad, zz))
    fan_rings.append(rr)
body.loft(fan_rings, mat="gravel", close=False, uv="box")
for k in range(10):
    a0, a1 = math.radians(-155 + 130 * k / 10), math.radians(-155 + 130 * (k + 1) / 10)
    p0 = (TF.x, TF.y + 0.1, 0.105)
    q0 = (TF.x + math.cos(a0) * 0.7, TF.y + 0.15 + math.sin(a0) * 0.62, 0.075)
    q1 = (TF.x + math.cos(a1) * 0.7, TF.y + 0.15 + math.sin(a1) * 0.62, 0.075)
    body.quad([q1, q0, p0, (p0[0] + 0.0001, p0[1], p0[2])], "custom_sluice_water",
              [(k / 10 + 0.1, 1.2), (k / 10, 1.2), (k / 10, 0.0), (k / 10 + 0.05, 0.0)])
for k in range(30):
    a = rng.uniform(math.radians(-160), math.radians(-20))
    rad = rng.uniform(0.2, 1.1)
    s = rng.uniform(0.02, 0.05)
    body.rock(s, (TF.x + math.cos(a) * rad * 1.1, TF.y + 0.15 + math.sin(a) * rad, 0.03 + s * 0.3), seed=900 + k,
              mat="gravel", detail=0, squash=(1, 0.9, 0.6), rough=0.3)
# work light on a tripod -> light_0
LS = V((-1.55, -0.6, 0.0))
for k in range(3):
    a = k / 3 * math.tau + 0.4
    body.rod(LS + V((math.cos(a) * 0.4, math.sin(a) * 0.4, 0.0)), LS + V((0, 0, 0.72)), 0.014, mat="steel_dark", sides=6)
body.cyl(0.022, 1.2, c=LS + V((0, 0, 1.2)), mat="aluminium", sides=8, bev=0)
LDIR = V((0.75, -0.35, -0.55)).normalized()
LENS = lib.work_light(body, LS + V((0, 0, 1.86)), LDIR, kind="bar", r=0.1)
body.path([LS + V((0, 0, 1.5)), LS + V((0.06, 0.04, 1.0)), LS + V((0.12, 0.08, 0.3)), LS + V((0.3, 0.3, 0.02)),
           V((-1.0, 1.4, 0.02)), V((0.4, 1.3, 0.02)), PC + V((-0.25, 0.0, 0.1))], r=0.01, mat="cable", sides=6, res=4)

# ================================================================== empties
m.empty("crew_1", (0.3, 3.05, 0.0), q=Quaternion((0, 0, 1), math.radians(-15)))
m.empty("fx_work", CL + V((0, 0, 0.25)))
m.empty("fx_ore", LO + V((0, -0.12, 0.02)))
m.empty("light_0", LENS, beam=LDIR)
m.empty("snd", PC + V((0, 0, 0.35)))

lib.tick("build parts")
m.finish(rays=20, strength=1.1, low=0.35, noise_amt=0.18)
lib.tick("finish+grime")

ANIM = ["pump", "classifier", "hose_climb"]
NF = 150
JIT = [(rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1)) for _ in range(NF)]
P0 = m.objs["pump"].location.copy()


def work(t):
    f = int(round(t * NF)) % NF
    jx, jy, jz = JIT[f]
    shake = V((0.0018 * jx, 0.0018 * jy, 0.0022 * (1 if f % 2 else -1)))
    return {
        "pump": {"loc": P0 + shake, "q": Quaternion((0, 1, 0), 0.006 * jz)},
        "classifier": {"q": Quaternion((1, 0, 0), math.radians(4.5) * math.sin(math.tau * 5 * t))},
        "hose_climb": {"q": Quaternion((0, 0, 1), math.radians(1.2) * math.sin(math.tau * 5 * t + 0.6))
                       @ Quaternion((1, 0, 0), math.radians(0.8) * math.sin(math.tau * 10 * t))},
    }


m.clip("Work", 5.0, work, ANIM)
m.clip("Idle", 2.0, None, ANIM)
lib.tick("clips")
tris, size = m.report()
if stem:
    m.export(stem)
    lib.tick("export")
if "--no-render" not in flags:
    m.render([
        ("front3q", (3.6, -6.0, 2.8), (0.2, -0.2, 0.7), 32),
        ("side", (6.8, 0.0, 1.6), (0.2, 0.0, 0.7), 36),
        ("rear3q", (-3.8, 6.2, 2.9), (0.2, 0.8, 0.7), 32),
        ("close", (1.6, 0.2, 1.9), (0.1, 1.8, 1.1), 40),
    ])
