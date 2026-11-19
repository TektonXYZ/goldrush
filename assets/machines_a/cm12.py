"""Ironside CM-12 continuous miner (MOTHERLODE machines-A, depth 1 / tier 1).

Modeled on a Joy 14CM / Komatsu 12CM: full-width pick-studded cutter drum on a hydraulic boom, gathering pan with
two rotary spinners, a centre chain conveyor through the body to a swinging tail boom, crawler tracks, a deck-mounted
operator compartment, scrubber duct and flameproof electrics. The real machine is ~10.9 m long; this one is
compressed to 6.8 x 3.3 x 2.2 m so it fits a work-face alcove.

    systemd-run --user --scope -q -p MemoryMax=3G -p MemorySwapMax=0 \
        bl assets/machines_a/cm12.py -- public/models/machines/cm12 [--no-render] [--one] [--blend]
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
from lib import V, aim, frame  # noqa: E402
from mathutils import Matrix, Quaternion  # noqa: E402

stem, flags = lib.args()
m = lib.Machine("cm12")

# ------------------------------------------------------------------ decals
A = m.atlas
A.add("logo", 1024, 256, lib.svg_logo(1024, 256, "IRONSIDE", wear=0.4))
A.add("model", 640, 200, lib.svg_text("CM-12", font="Saira Stencil One", wear=0.35), fit=True)
A.add("unit", 360, 260, lib.svg_text("07", font="Saira Stencil One", wear=0.4, seed=5), fit=True)
A.add("hazard", 1024, 128, lib.svg_hazard(1024, 128, band=64, wear=0.45))
A.add("danger_cut", 512, 360, lib.svg_panel(512, 360, "DANGER", ["STAY CLEAR OF", "CUTTER HEAD"]))
A.add("warn_swing", 512, 360, lib.svg_panel(512, 360, "WARNING", ["TAIL BOOM SWINGS", "PINCH POINT"], seed=12))
A.add("caution_hyd", 512, 360, lib.svg_panel(512, 360, "CAUTION", ["HIGH PRESSURE", "HYDRAULIC OIL"], seed=13))
A.add("danger_volt", 512, 400, lib.svg_panel(512, 400, "DANGER", ["995 VOLTS", "LOCK OUT BEFORE", "OPENING COVER"],
                                             seed=14))
A.add("plate", 600, 360, lib.svg_plate(600, 360, ["MODEL   CM-12 CONT. MINER", "SERIAL  CM12-0417",
                                                  "MSHA    2G-4123A-0", "SUPPLY  995 VAC 3PH 60HZ",
                                                  "BUILT   2019 GULCH WORKS"], title="IRONSIDE MINING MACHINERY"))
A.add("iso", 256, 230, lib.svg_iso(256, 230))
A.add("iso_bolt", 256, 230, lib.svg_iso(256, 230, "bolt"))
A.add("oil", 640, 110, lib.svg_text("HYDRAULIC OIL ONLY", font="Barlow Condensed ExtraBold", wear=0.3), fit=True)
A.add("water", 400, 110, lib.svg_text("WATER IN", font="Barlow Condensed ExtraBold", wear=0.3), fit=True)
A.add("nostep", 400, 110, lib.svg_text("NO STEP", font="Barlow Condensed Black", wear=0.45), fit=True)
A.add("chev", 1024, 128, lib.svg_chevron(1024, 128, wear=0.4))
A.add("gauge", 256, 256, lib.svg_gauge(256, 256, vmax=300, unit="BAR", label="HYD"))
A.add("gauge_w", 256, 256, lib.svg_gauge(256, 256, vmax=20, unit="BAR", label="WATER", red=0.85, seed=23))
A.build()

# ------------------------------------------------------------------ key dimensions (metres; Blender front = -Y)
YD, ZD = -2.83, 0.62           # drum axis with the boom lowered (rest pose)
RC = 0.42                      # drum core radius (pick tips reach ~0.58)
PIV = V((0, -1.25, 0.95))      # boom pivot
XC = 1.33                      # crawler centre |x|
CY0, CY1, CZ, CR = -1.15, 1.70, 0.362, 0.315   # idler y, sprocket y, wheel centre z, track pitch radius
DECK = 0.84                    # deck top
YR = 1.95                      # body rear face
ROOF = 1.97                    # canopy roof underside
SWP = V((0, 1.98, 0.6))        # tail boom swing pivot
TB = math.tan(math.atan2(0.31, 1.05))
BETA = math.atan(TB)           # gathering pan slope


def zpan(y):
    return 0.025 + (y + 2.45) * TB


body = m.part("cm12_body")


# ================================================================== crawlers
def race(s, y0, y1, zc, R):
    Ls, arc = y1 - y0, math.pi * R
    s %= 2 * Ls + 2 * arc
    if s < Ls:
        return y0 + s, zc + R, (1.0, 0.0), (0.0, 1.0)
    s -= Ls
    if s < arc:
        f = math.pi / 2 - s / R
        return y1 + R * math.cos(f), zc + R * math.sin(f), (math.sin(f), -math.cos(f)), (math.cos(f), math.sin(f))
    s -= arc
    if s < Ls:
        return y1 - s, zc - R, (-1.0, 0.0), (0.0, -1.0)
    s -= Ls
    f = -math.pi / 2 - s / R
    return y0 + R * math.cos(f), zc + R * math.sin(f), (math.sin(f), -math.cos(f)), (math.cos(f), math.sin(f))


def crawler(p, side):
    xc = side * XC
    L = 2 * (CY1 - CY0) + 2 * math.pi * CR
    n = 42
    pitch = L / n
    for i in range(n):
        y, z, t, nn = race(i * pitch, CY0, CY1, CZ, CR)
        with p.at((xc, y, z), q=lib.track_frame_q(t, nn)):
            p.box((0.6, pitch * 0.9, 0.034), mat="steel_dark", bev=0.006, segs=1)          # shoe plate
            p.box((0.58, 0.036, 0.03), c=(0, -pitch * 0.2, 0.031), mat="steel_dark", bev=0)  # grouser
    Ri = CR - 0.1
    pts = [(CY1 + Ri * math.cos(math.pi / 2 - math.pi * k / 6), CZ + Ri * math.sin(math.pi / 2 - math.pi * k / 6))
           for k in range(7)]
    pts += [(CY0 + Ri * math.cos(-math.pi / 2 - math.pi * k / 6), CZ + Ri * math.sin(-math.pi / 2 - math.pi * k / 6))
            for k in range(7)]
    xo = xc + side * 0.215
    p.plate(pts, 0.05, "YZ", at=xo, mat="paint_yellow", bev=0.012)
    p.plate([(CY0 + 0.25, CZ - 0.12), (CY1 - 0.25, CZ - 0.12), (CY1 - 0.35, CZ + 0.12), (CY0 + 0.35, CZ + 0.12)],
            0.03, "YZ", at=xo + side * 0.035, mat="paint_yellow", bev=0.008)
    p.bolt_row((xo + side * 0.05, CY0 + 0.45, CZ + 0.07), (xo + side * 0.05, CY1 - 0.45, CZ + 0.07), 7,
               (side, 0, 0), r=0.012)
    p.bolt_row((xo + side * 0.05, CY0 + 0.37, CZ - 0.07), (xo + side * 0.05, CY1 - 0.37, CZ - 0.07), 8,
               (side, 0, 0), r=0.012)
    for yy, big in ((CY1, True), (CY0, False)):
        rr = 0.235 if big else 0.2
        p.lathe([(0, 0.0), (rr, 0.0), (rr, 0.035), (rr * 0.72, 0.06), (rr * 0.72, 0.085), (rr * 0.38, 0.095),
                 (0, 0.095)], c=(xc + side * 0.24, yy, CZ), rot=(0, 90 * side, 0),
                mat="steel_dark" if big else "paint_yellow", sides=18, angle=28)
        p.bolt_circle((xc + side * 0.3, yy, CZ), (side, 0, 0), rr * 0.55, 6, r=0.013)
    p.box((0.08, 0.5, 0.12), c=(xc + side * 0.27, CY0 + 0.45, CZ), mat="steel_dark", bev=0.01)       # tensioner
    p.cyl(0.012, 0.03, c=(xc + side * 0.32, CY0 + 0.3, CZ), axis="X", mat="brass", sides=6, bev=0)


for sd in (1, -1):
    crawler(body, sd)


# ================================================================== main frame, deck, conveyor channel
def mx(pts, sx):
    return [(sx * x, y) for x, y in pts]


for sx in (1, -1):
    body.box((0.5, 3.35, 0.5), c=(sx * 0.74, 0.25, 0.53), mat="paint_yellow", bev=0.015)               # sill
    body.box((0.04, 2.875, 0.62), c=(sx * 0.46, 0.4875, 0.53), mat="paint_yellow", bev=0.006)          # channel wall
    body.plate(mx([(0.48, -0.95), (1.65, -0.95), (1.65, 1.78), (1.48, YR), (0.48, YR)], sx), 0.06, "XY",
               at=DECK - 0.03, mat="paint_yellow", bev=0.012)                                         # deck
    body.plate(mx([(0.98, -1.45), (1.5, -1.45), (1.65, -1.3), (1.65, -0.95), (0.98, -0.95)], sx), 0.06, "XY",
               at=DECK - 0.03, mat="paint_yellow", bev=0.012)                                         # front deck
    body.box((0.52, 0.05, 0.14), c=(sx * 1.24, -1.475, DECK - 0.07), mat="paint_yellow", bev=0.01)    # front lip
    body.box((0.22, 0.05, 0.14), c=(sx * 1.575, -1.375, DECK - 0.07), rot=(0, 0, -45 * sx), mat="paint_yellow",
             bev=0.01)
    body.box((0.5, 0.03, 0.42), c=(sx * 0.75, YR + 0.015, 0.63), mat="paint_yellow", bev=0.006)       # rear plate
    body.box((0.62, 0.03, 0.12), c=(sx * 1.34, YR + 0.015, 0.78), mat="paint_yellow", bev=0.006)      # fender lip
    body.box((0.05, 3.08, 0.08), c=(sx * 1.625, 0.24, DECK - 0.07), mat="paint_yellow", bev=0.008)     # edge rail
    body.plate([(-0.95, 0.55), (-0.95, 1.12), (-1.15, 1.17), (-1.42, 1.07), (-1.42, 0.8), (-1.28, 0.55)], 0.1, "YZ",
               at=sx * 0.92, mat="paint_yellow", bev=0.015)                                         # boom bracket
    body.cyl(0.12, 0.05, c=(sx * 0.995, PIV.y, PIV.z), axis="X", mat="steel_dark", sides=16, bev=0.008, segs=1)
    body.bolt_circle((sx * 1.02, PIV.y, PIV.z), (sx, 0, 0), 0.08, 6, r=0.012)
    for dx in (-0.06, 0.06):                                                                      # lift clevis
        body.box((0.025, 0.12, 0.16), c=(sx * 0.5 + dx, -1.44, 0.46), mat="paint_yellow", bev=0.004)
    body.cyl(0.03, 0.16, c=(sx * 0.5, -1.40, 0.46), axis="X", mat="steel_dark", sides=8, bev=0)
lib.cover(body, (0.78, -0.62, DECK), (0, 0, 1), 0.42, 0.5, pitch=0.12)
lib.cover(body, (-0.76, -0.86, DECK), (0, 0, 1), 0.4, 0.26, pitch=0.12)

body.box((0.6, 0.3, 0.16), c=(0, YR - 0.02, 0.37), mat="paint_yellow", bev=0.012)               # tail pivot bracket
body.box((0.86, 0.18, 0.1), c=(0, YR - 0.05, 0.27), mat="steel_dark", bev=0.008)
for sx in (1, -1):
    for dz in (-0.06, 0.06):
        body.box((0.12, 0.12, 0.025), c=(sx * 0.72, YR + 0.07, 0.7 + dz), mat="paint_yellow", bev=0.004)
    body.cyl(0.028, 0.15, c=(sx * 0.72, YR + 0.09, 0.7), mat="steel_dark", sides=8, bev=0)
    body.box((0.16, 0.12, 0.16), c=(sx * 0.75, YR + 0.06, 0.5), mat="steel_dark", bev=0.01)       # tow pocket
    body.cyl(0.035, 0.24, c=(sx * 0.75, YR + 0.07, 0.5), mat="steel", sides=10, bev=0.004)

# ================================================================== conveyor trough through the body
slope = math.atan2(0.56 - 0.364, YR + 1.3)
Lc = YR + 1.3
with body.at((0, (YR - 1.3) / 2, (0.364 + 0.56) / 2), rot=(math.degrees(slope), 0, 0)):
    body.box((0.8, Lc, 0.03), c=(0, 0, -0.015), mat="steel", bev=0.004)            # deck plate (coal-polished)
    for sx in (1, -1):
        body.box((0.03, Lc, 0.22), c=(sx * 0.415, 0, 0.09), mat="steel_dark", bev=0.004)
        body.box((0.07, Lc, 0.02), c=(sx * 0.44, 0, 0.2), mat="steel_dark", bev=0.003)
    body.box((0.8, Lc, 0.02), c=(0, 0, -0.2), mat="steel_dark", bev=0)            # return-run floor
    for k in range(5):
        body.box((0.86, 0.06, 0.05), c=(0, -Lc / 2 + 0.6 + k * 0.62, -0.11), mat="steel_dark", bev=0)

# ================================================================== gathering pan
body.plate([(-2.5, 0.0), (-1.3, 0.0), (-1.3, zpan(-1.3)), (-2.45, zpan(-2.45)), (-2.5, 0.012)], 2.0, "YZ",
           at=0, mat="steel", bev=0.01)
for sx in (1, -1):
    body.plate([(-2.5, 0.0), (-1.6, 0.0), (-1.6, zpan(-1.6)), (-2.45, zpan(-2.45)), (-2.5, 0.012)], 0.56, "YZ",
               at=sx * 1.28, mat="steel", bev=0.01)
    body.plate([(-2.5, 0.0), (-1.6, 0.0), (-1.6, 0.6), (-1.82, 0.62), (-2.5, 0.27)], 0.05, "YZ", at=sx * 1.585,
               mat="paint_yellow", bev=0.012)                                                       # apron
    body.plate([(-2.45, 0.27), (-1.82, 0.6), (-1.82, 0.66), (-2.45, 0.33)], 0.08, "YZ", at=sx * 1.6,
               mat="paint_yellow", bev=0.01)                                                        # apron rim
    for yy, hh in ((-2.2, 0.36), (-1.95, 0.5)):                                                    # stiffeners
        body.box((0.035, 0.05, hh), c=(sx * 1.625, yy, hh / 2), mat="paint_yellow", bev=0.006)
    body.box((0.5, 0.06, 0.03), c=(sx * 0.68, -2.47, 0.03), mat="steel", bev=0.006)
    with body.at((0, -1.8, zpan(-1.8)), rot=(math.degrees(BETA), 0, 0)):
        body.box((0.03, 1.0, 0.045), c=(sx * 0.415, 0, 0.022), mat="steel_dark", bev=0.004)
    cpos = V((sx * 0.95, -1.98, zpan(-1.98)))
    body.lathe([(0.5, 0.0), (0.53, 0.0), (0.53, 0.02), (0.5, 0.02)], c=cpos, q=Quaternion((1, 0, 0), BETA),
               mat="steel_dark", sides=28, cap0=False, cap1=False)
body.box((3.1, 0.07, 0.025), c=(0, -2.49, 0.0125), mat="steel", bev=0.006)                     # hardened lip

# ================================================================== right side (-X): tank, scrubber, electrics
body.box((0.62, 1.15, 0.52), c=(-0.84, -0.12, DECK + 0.26), mat="paint_yellow", bev=0.04)       # hydraulic tank
body.box((0.66, 1.19, 0.03), c=(-0.84, -0.12, DECK + 0.015), mat="paint_yellow", bev=0.008)
body.cyl(0.07, 0.05, c=(-0.7, -0.45, DECK + 0.545), mat="steel_dark", sides=14)
body.cyl(0.085, 0.035, c=(-0.7, -0.45, DECK + 0.585), mat="plastic_black", sides=14, bev=0.008)
body.cyl(0.03, 0.08, c=(-1.0, -0.5, DECK + 0.56), mat="steel", sides=8)
body.sphere(0.04, c=(-1.0, -0.5, DECK + 0.62), mat="steel", seg=8, rings=5)
body.cyl(0.09, 0.26, c=(-0.75, 0.22, DECK + 0.65), mat="paint_grey", sides=14, bev=0.01)        # return filter
body.cyl(0.1, 0.04, c=(-0.75, 0.22, DECK + 0.54), mat="steel_dark", sides=14)
body.box((0.03, 0.06, 0.3), c=(-1.152, -0.2, DECK + 0.27), mat="steel_dark", bev=0.004)          # sight gauge
body.box((0.01, 0.035, 0.26), c=(-1.165, -0.2, DECK + 0.27), mat="glass_dark", bev=0)
body.hose((-0.62, -0.695, DECK + 0.12), (0, -1, 0), (-0.62, -0.92, DECK + 0.005), (0, 0, -1), r=0.035,
          mat="rubber", sides=10, steps=12, k=0.5)
body.hose((-0.98, -0.695, DECK + 0.2), (0, -1, 0), (-0.95, -0.98, DECK + 0.005), (0, 0, -1), r=0.022,
          mat="rubber", sides=8, steps=12, k=0.5)
body.box((0.42, 2.0, 0.42), c=(-1.41, -0.05, DECK + 0.21), mat="paint_yellow", bev=0.025)       # scrubber duct
for yy in (-1.04, -0.72, 0.64, 0.94):
    body.box((0.47, 0.05, 0.47), c=(-1.41, yy, DECK + 0.21), mat="paint_yellow", bev=0.008, segs=1)
    body.bolts([(-1.645, yy, DECK + z) for z in (0.06, 0.21, 0.36)], (-1, 0, 0), r=0.01)
    body.bolts([(x, yy, DECK + 0.445) for x in (-1.56, -1.26)], (0, 0, 1), r=0.01)
body.lathe([(0, 0), (0.24, 0), (0.3, 0.05), (0.3, 0.5), (0.27, 0.55), (0, 0.55)], c=(-1.32, 1.0, DECK + 0.31),
           rot=(-90, 0, 0), mat="paint_yellow", sides=24, angle=25)                                # scrubber fan
body.lathe([(0.3, 0.12), (0.325, 0.12), (0.325, 0.16), (0.3, 0.16)], c=(-1.32, 1.0, DECK + 0.31), rot=(-90, 0, 0),
           mat="paint_yellow", sides=24, cap0=False, cap1=False)
body.bolt_circle((-1.32, 1.118, DECK + 0.31), (0, -1, 0), 0.312, 12, r=0.009)
body.box((0.56, 0.36, 0.58), c=(-1.32, 1.74, DECK + 0.3), mat="paint_yellow", bev=0.02)
body.grille((-1.32, 1.925, DECK + 0.3), 0.5, 0.5, 7, rot=(0, 0, 180), depth=0.04, mat="paint_yellow",
            slat_mat="steel_dark")
body.box((0.26, 0.24, 0.26), c=(-1.05, -1.32, 1.22), mat="paint_yellow", bev=0.015)              # scrubber inlet
body.mesh_panel((-1.05, -1.445, 1.22), 0.22, 0.22, cell=0.044, wire=0.005)
body.path([(-1.41, -1.07, DECK + 0.22), (-1.41, -1.2, DECK + 0.26), (-1.3, -1.3, 1.16), (-1.18, -1.32, 1.21)],
          r=0.1, mat="rubber", sides=12, res=5)
lib.fp_box(body, (-0.78, 1.22, DECK), (0.5, 1.3, 0.58), n=(0, 0, 1), up=(0, 1, 0), pitch=0.14)   # electrics
for k in range(3):
    body.cyl(0.035, 0.09, c=(-0.6 - k * 0.09, 1.915, DECK + 0.1), axis="Y", mat="brass", sides=8, bev=0)
    if k:
        body.hose((-0.6 - k * 0.09, 1.96, DECK + 0.1), (0, 1, 0), (-0.75 - k * 0.12, YR + 0.04, 0.5), (0, 0, -1),
                  r=0.018, mat="cable", sides=8, fittings=None, k=0.4)
body.box((0.12, 0.08, 0.1), c=(-0.55, 1.6, DECK + 0.62), mat="steel_dark", bev=0.008)            # isolator
body.cyl(0.02, 0.12, c=(-0.55, 1.6, DECK + 0.72), mat="paint_red", sides=8, bev=0)
body.path([(-0.6, 1.96, DECK + 0.1), (-0.6, 2.06, DECK + 0.02), (-0.78, 2.3, 0.4), (-0.98, 2.6, 0.1),
           (-1.15, 2.95, 0.045), (-1.3, 3.36, 0.045)], r=0.042, mat="cable", sides=10, res=7)
body.box((0.16, 0.1, 0.2), c=(-0.6, 2.0, DECK + 0.04), mat="steel_dark", bev=0.01)               # cable anchor

# ================================================================== left side (+X): valve bank, compartment
body.box((0.5, 0.65, 0.32), c=(1.33, -0.75, DECK + 0.16), mat="paint_grey", bev=0.02)           # valve bank
for k in range(6):
    yy = -1.0 + k * 0.1
    body.cyl(0.028, 0.06, c=(1.2, yy, DECK + 0.35), mat="steel", sides=8, bev=0)
    body.rod((1.58, yy, DECK + 0.22), (1.64, yy, DECK + 0.42), 0.01, mat="steel", sides=6)
    body.sphere(0.022, c=(1.64, yy, DECK + 0.43), mat="plastic_black", seg=8, rings=5)
for k in range(4):
    body.hose((1.16 + k * 0.08, -1.075, DECK + 0.2), (0, -1, 0), (1.03 + k * 0.035, -1.3, DECK + 0.005), (0, 0, -1),
              r=0.017, mat="rubber", sides=8, steps=12, k=0.5)
body.cyl(0.09, 0.012, c=(1.08, -1.3, DECK + 0.006), mat="steel_dark", sides=14, bev=0)
body.cyl(0.09, 0.32, c=(1.45, -0.18, DECK + 0.16), mat="paint_blue", sides=14, bev=0.01)          # water filter
body.cyl(0.1, 0.04, c=(1.45, -0.18, DECK + 0.33), mat="steel_dark", sides=14)
body.hose((1.45, -0.18, DECK + 0.35), (0, 0, 1), (1.56, -1.25, DECK + 0.12), (0, -1, 0), r=0.022, mat="hose_yellow",
          sides=10, k=0.45)
body.box((0.2, 0.02, 0.26), c=(1.5, -1.28, DECK + 0.13), mat="paint_yellow", bev=0.004)             # bulkhead
body.cyl(0.03, 0.08, c=(1.56, -1.3, DECK + 0.12), axis="Y", mat="brass", sides=8, bev=0)
body.box((0.42, 0.4, 0.2), c=(1.12, 1.02, DECK + 0.1), mat="steel_dark", bev=0.01)               # seat base
body.box((0.5, 0.48, 0.1), c=(1.12, 1.0, DECK + 0.25), mat="plastic_black", bev=0.035)           # cushion
body.box((0.5, 0.1, 0.56), c=(1.12, 1.27, DECK + 0.55), rot=(-12, 0, 0), mat="plastic_black", bev=0.035)
body.box((0.7, 0.3, 0.44), c=(1.12, 0.42, DECK + 0.22), mat="paint_yellow", bev=0.015)            # console
with body.at((1.12, 0.45, DECK + 0.47), rot=(-28, 0, 0)):
    body.box((0.7, 0.34, 0.05), mat="steel_dark", bev=0.008)
    for k in range(5):
        x = -0.24 + k * 0.12
        body.rod((x, 0.07, 0.02), (x, 0.09, 0.17), 0.009, mat="steel", sides=6)
        body.sphere(0.022, c=(x, 0.09, 0.18), mat="paint_red" if k == 2 else "plastic_black", seg=8, rings=5)
    body.cyl(0.035, 0.03, c=(0.27, -0.08, 0.04), mat="paint_red", sides=12, bev=0.006)
    body.cyl(0.02, 0.03, c=(0.27, -0.08, 0.02), mat="paint_yellow", sides=8, bev=0)
    body.decal("gauge", c=(-0.2, -0.08, 0.026), n=(0, 0, 1), up=(0, -1, 0), w=0.1)
    body.decal("gauge_w", c=(-0.06, -0.08, 0.026), n=(0, 0, 1), up=(0, -1, 0), w=0.1)
body.box((0.04, 1.4, 0.5), c=(1.63, 0.9, DECK + 0.25), mat="paint_yellow", bev=0.008)             # outer wall
body.box((1.05, 0.04, 0.5), c=(1.12, 1.6, DECK + 0.25), mat="paint_yellow", bev=0.008)            # rear wall
body.box((0.07, 1.42, 0.05), c=(1.635, 0.9, DECK + 0.5), mat="paint_yellow", bev=0.008)           # wall cap
POSTS = ((0.62, 0.22), (1.6, 0.22), (0.62, 1.58), (1.6, 1.58))
for (x, y) in POSTS:
    body.box((0.11, 0.11, ROOF - DECK), c=(x, y, (ROOF + DECK) / 2), mat="paint_yellow", bev=0.012)
    body.box((0.18, 0.18, 0.025), c=(x, y, DECK + 0.0125), mat="paint_yellow", bev=0.004)
    body.bolts([(x + 0.065, y + 0.065, DECK + 0.025), (x - 0.065, y - 0.065, DECK + 0.025)], (0, 0, 1), r=0.01)
body.box((1.12, 1.5, 0.05), c=(1.11, 0.9, ROOF + 0.025), mat="paint_yellow", bev=0.01)            # roof plate
for (cx_, cy_, sx_, sy_) in ((1.11, 0.15, 1.16, 0.06), (1.11, 1.65, 1.16, 0.06), (0.53, 0.9, 0.06, 1.56),
                             (1.69, 0.9, 0.06, 1.56)):
    body.box((sx_, sy_, 0.1), c=(cx_, cy_, ROOF + 0.04), mat="paint_yellow", bev=0.01)            # roof rim
for yy in (0.6, 1.2):
    body.box((1.1, 0.05, 0.05), c=(1.11, yy, ROOF + 0.075), mat="paint_yellow", bev=0.006)       # roof ribs
for (x, y) in POSTS:                                                                              # gussets
    sy = 1 if y < 1 else -1
    body.plate([(y, ROOF), (y + sy * 0.22, ROOF), (y, ROOF - 0.22)], 0.03, "YZ", at=x, mat="paint_yellow",
               bev=0.004)
body.mesh_panel((1.66, 1.1, 1.66), 0.9, 0.56, cell=0.075, wire=0.008, rot=(0, 0, 90))
for yy in (0.32, 1.48):
    body.handrail([(1.7, yy, DECK + 0.62), (1.7, yy, DECK + 0.9)], r=0.017)
    for zz in (DECK + 0.64, DECK + 0.88):
        body.rod((1.655, yy, zz), (1.7, yy, zz), 0.012, mat="paint_yellow", sides=6)
lib.work_light(body, (0.82, 0.14, ROOF + 0.06), (0, -1, -0.28), kind="bar", r=0.09)
lib.work_light(body, (1.42, 0.14, ROOF + 0.06), (0, -1, -0.28), kind="bar", r=0.09)
body.box((0.26, 0.2, 0.24), c=(1.33, 1.76, DECK + 0.12), mat="paint_grey", bev=0.015)           # status box
body.cyl(0.016, 0.012, c=(1.33, 1.66, DECK + 0.18), axis="Y", mat="emit_green", sides=8, bev=0)
body.box((0.14, 0.12, 0.2), c=(0.92, -1.48, 1.0), mat="paint_red", bev=0.012)                   # methane monitor
body.cyl(0.03, 0.06, c=(0.92, -1.55, 0.97), axis="Y", mat="steel", sides=8, bev=0)
body.cyl(0.012, 0.01, c=(0.95, -1.545, 1.07), axis="Y", mat="emit_green", sides=6, bev=0)
for sx in (1, -1):                                                                                # rear lights
    lib.work_light(body, (sx * 1.46, YR + 0.04, 1.02), (0, 1, -0.1), kind="round", r=0.06, guard=False, sides=12)
    body.box((0.1, 0.06, 0.06), c=(sx * 1.46, YR + 0.03, 0.93), mat="paint_black", bev=0.008)
    body.box((0.08, 0.012, 0.04), c=(sx * 1.46, YR + 0.062, 0.93), mat="emit_red", bev=0)
    body.box((0.06, 0.1, 0.22), c=(sx * 1.46, YR - 0.04, 0.93), mat="paint_yellow", bev=0.006)
for xx, yy in ((1.56, 1.86), (-1.08, -0.84)):
    lib.lift_eye(body, (xx, yy, DECK), (0, 0, 1), r=0.045)
lib.step_plate(body, (1.33, YR + 0.12, 0.45), 0.4, 0.18)
for dx in (-0.18, 0.18):
    body.box((0.02, 0.03, 0.4), c=(1.33 + dx, YR + 0.06, 0.64), mat="paint_yellow", bev=0.004)

LIGHTS = []                                                                                      # headlights
for sx in (1, -1):
    c = V((sx * 1.3, -1.55, 1.0))
    d = V((sx * 0.05, -1, -0.22)).normalized()
    body.box((0.06, 0.09, 0.2), c=(sx * 1.3, -1.49, DECK + 0.02), mat="paint_yellow", bev=0.006)
    lens = lib.work_light(body, c, d, kind="round", r=0.085)
    LIGHTS.append((lens, d))

# ================================================================== decals on the body
body.decal("logo", c=(-1.621, -0.05, DECK + 0.2), n=(-1, 0, 0), w=1.25)
body.decal("model", c=(-1.601, 1.74, DECK + 0.3), n=(-1, 0, 0), w=0.32)
body.decal("logo", c=(1.651, 0.72, DECK + 0.24), n=(1, 0, 0), w=0.9)
body.decal("model", c=(1.651, 1.38, DECK + 0.24), n=(1, 0, 0), w=0.26)
body.decal("caution_hyd", c=(-0.84, -0.698, DECK + 0.3), n=(0, -1, 0), w=0.3)
body.decal("oil", c=(-0.84, -0.1, DECK + 0.521), n=(0, 0, 1), up=(0, 1, 0), w=0.28)
body.decal("danger_volt", c=(-0.527, 1.2, DECK + 0.28), n=(1, 0, 0), w=0.32)
body.decal("iso_bolt", c=(-0.527, 0.8, DECK + 0.3), n=(1, 0, 0), w=0.12)
body.decal("plate", c=(1.12, 0.267, DECK + 0.25), n=(0, -1, 0), w=0.26)
body.decal("water", c=(1.48, -1.291, DECK + 0.22), n=(0, -1, 0), up=(0, 0, 1), w=0.14)
body.decal("nostep", c=(-1.41, 0.2, DECK + 0.423), n=(0, 0, 1), up=(0, 1, 0), w=0.22)
body.decal("nostep", c=(-0.9, 0.38, DECK + 0.521), n=(0, 0, 1), up=(0, 1, 0), w=0.2)
for sx in (1, -1):
    body.decal("hazard", c=(sx * 1.24, -1.501, DECK - 0.07), n=(0, -1, 0), w=0.5, h=0.08)
    body.decal("chev", c=(sx * 0.75, YR + 0.031, 0.805), n=(0, 1, 0), w=0.48, h=0.06)
    body.decal("danger_cut", c=(sx * 1.611, -1.75, 0.36), n=(sx, 0, 0), w=0.26)
    body.decal("hazard", c=V((sx * 1.641, -2.14, 0.46)), n=(sx, 0, 0), up=V((0, -0.33, 0.63)).normalized(),
               w=0.72, h=0.07)
    body.decal("iso", c=(sx * 0.971, -1.2, 0.68), n=(sx, 0, 0), w=0.1)
body.decal("unit", c=(-0.78, 1.871, DECK + 0.36), n=(0, 1, 0), w=0.2)
body.decal("unit", c=(1.3, 0.117, ROOF + 0.04), n=(0, -1, 0), w=0.11)
body.decal("hazard", c=(1.11, 1.682, ROOF + 0.04), n=(0, 1, 0), w=1.0, h=0.07)
body.decal("warn_swing", c=(0.9, YR + 0.031, 0.62), n=(0, 1, 0), w=0.15)

# ================================================================== boom (animated: lift) - one heavy wedge
boom = m.part("boom", origin=PIV)
bprof = [(-1.02, 0.74), (-1.02, 1.17), (-1.22, 1.29), (-1.9, 1.2), (-2.2, 0.98), (-2.2, 0.62), (-2.05, 0.5),
         (-1.5, 0.56), (-1.15, 0.62)]
boom.plate(bprof, 1.70, "YZ", at=0, mat="paint_yellow", bev=0.03)
for sx in (1, -1):
    boom.plate([(-1.12, 0.79), (-1.12, 1.14), (-1.27, 1.23), (-1.86, 1.15), (-2.1, 0.97), (-2.1, 0.66),
                (-1.97, 0.58), (-1.5, 0.62), (-1.2, 0.68)], 0.012, "YZ", at=sx * 0.856, mat="paint_yellow",
               bev=0.004)
boom.cyl(0.15, 1.73, c=PIV, axis="X", mat="steel_dark", sides=16, bev=0.01, segs=1)              # pivot tube
TOPANG = math.degrees(math.atan2(0.09, 0.68))


def ztop(y):
    return 1.29 - (-1.22 - y) * (0.09 / 0.68)


for sx in (1, -1):                       # enclosed cutter motors: raised housings, bolted lids, end bells
    with boom.at((sx * 0.56, -1.6, ztop(-1.6) + 0.1), rot=(TOPANG, 0, 0)):
        boom.box((0.42, 0.72, 0.2), mat="paint_yellow", bev=0.045)
        lib.cover(boom, (0, -0.02, 0.1), (0, 0, 1), 0.3, 0.56, t=0.014, pitch=0.11)
        boom.lathe([(0, 0), (0.15, 0), (0.15, 0.05), (0.12, 0.09), (0, 0.09)], c=(0, 0.36, 0), rot=(-90, 0, 0),
                   mat="paint_yellow", sides=16, angle=25)
        boom.box((0.12, 0.14, 0.12), c=(sx * 0.27, 0.2, 0.0), mat="paint_yellow", bev=0.012)       # junction box
        boom.cyl(0.026, 0.05, c=(sx * 0.34, 0.2, 0.0), axis="X", mat="brass", sides=8, bev=0)
    boom.hose((sx * 0.92, -1.4, ztop(-1.4) + 0.1), (sx, 0.2, 0), (sx * 0.6, -1.06, 1.08), (0, 0.3, -1), r=0.03,
              mat="cable", sides=8, fittings=None, k=0.5)
arm = [(-1.6, 0.6), (-1.6, 1.15), (-2.55, 0.97)]                                                  # gearcase arms
arm += [(YD + 0.37 * math.cos(math.radians(f)), ZD + 0.37 * math.sin(math.radians(f))) for f in range(75, 290, 15)]
arm += [(-2.3, 0.42)]
for sx in (1, -1):
    boom.plate(arm, 0.24, "YZ", at=sx * 1.02, mat="paint_yellow", bev=0.02)
    boom.cyl(0.3, 0.27, c=(sx * 1.02, YD, ZD), axis="X", mat="steel_dark", sides=16, bev=0)
    boom.plate([(-1.75, 0.66), (-1.75, 1.08), (-2.45, 0.95), (-2.45, 0.7)], 0.02, "YZ", at=sx * 1.14,
               mat="paint_yellow", bev=0.005)
for sx in (1, -1):                                                                                # rod-eye brackets
    for dx in (-0.055, 0.055):
        boom.plate([(-1.9, 0.53), (-2.1, 0.53), (-2.05, 0.4), (-1.95, 0.4)], 0.025, "YZ", at=sx * 0.5 + dx,
                   mat="paint_yellow", bev=0.004)
    boom.cyl(0.028, 0.15, c=(sx * 0.5, -2.0, 0.44), axis="X", mat="steel_dark", sides=8, bev=0)
NOSE_N = V((0, -0.59, 0.81))                                                                       # spray bar
SB = V((0, -2.12, 1.035)) + NOSE_N * 0.04
boom.cyl(0.024, 1.6, c=SB, axis="X", mat="steel", sides=10, bev=0)
nd = (V((0, YD, ZD)) - SB).normalized()
for k in range(9):
    base = SB + V((-0.76 + k * 0.19, 0, 0)) + nd * 0.018
    boom.cyl(0.011, 0.05, c=base + nd * 0.025, q=aim(nd), r2=0.006, mat="brass", sides=6, bev=0)
for sx in (1, -1):
    boom.box((0.04, 0.06, 0.08), c=V((sx * 0.8, 0, 0)) + SB - NOSE_N * 0.03, mat="paint_yellow", bev=0.006)
boom.hose(SB + V((0.8, 0, 0)), (1, 0, 0), (0.75, -1.25, ztop(-1.25) + 0.02), (0, 1, 0.1), r=0.02,
          mat="hose_yellow", sides=8, k=0.4, fittings="brass")
for sx in (1, -1):
    lib.lift_eye(boom, (sx * 0.72, -1.95, ztop(-1.95)), (0, -0.13, 0.99), r=0.04)
lib.cover(boom, (0, -1.15, 1.235), (0, 0.6, 1), 0.5, 0.12, pitch=0.1)
top_n = V((0, -0.0918, 0.68)).normalized()
top_up = V((0, 0.68, 0.0918)).normalized()
boom.decal("logo", c=V((0, -1.62, ztop(-1.62))) + top_n * 0.001, n=top_n, up=top_up, w=0.6)
boom.decal("hazard", c=V((0, -2.0, 1.125)), n=NOSE_N, up=V((0, 0.81, 0.59)), w=1.62, h=0.09)

# ================================================================== drum (animated: spin, child of boom)
drum = m.part("drum", origin=(0, YD, ZD), parent="boom")
SECS = [(-1.6, -1.16), (-0.88, 0.88), (1.16, 1.6)]
for x0, x1 in SECS:
    drum.cyl(RC, x1 - x0, c=((x0 + x1) / 2, YD, ZD), axis="X", mat="paint_yellow", sides=24, bev=0.01, segs=1)
for sx in (1, -1):
    drum.cyl(0.505, 0.07, c=(sx * 1.6, YD, ZD), axis="X", mat="paint_yellow", sides=24, bev=0.01, segs=1)  # end ring
    drum.cyl(0.2, 0.05, c=(sx * 1.64, YD, ZD), axis="X", mat="steel_dark", sides=14, bev=0.008, segs=1)
    drum.bolt_circle((sx * 1.665, YD, ZD), (sx, 0, 0), 0.13, 8, r=0.014)
    for k in range(6):                                                                          # end-face ribs
        with drum.at((sx * 1.645, YD, ZD), rot=(k * 60 + 15, 0, 0)):
            drum.box((0.035, 0.26, 0.035), c=(0, 0.34, 0), mat="steel_dark", bev=0)
    for xx in (0.87, 1.17):
        drum.cyl(0.47, 0.03, c=(sx * xx, YD, ZD), axis="X", mat="steel_dark", sides=24, bev=0)


def pick(p, x, th, splay=0.0):
    rad = V((0, math.cos(th), math.sin(th)))
    tan = V((0, -math.sin(th), math.cos(th)))  # direction of travel for +X spin (front moves down)
    ax = (rad * math.cos(math.radians(42)) + tan * math.sin(math.radians(42)) + V((splay, 0, 0))).normalized()
    with p.at(V((x, YD, ZD)) + rad * 0.43, q=frame(ax, (1, 0, 0))):
        p.box((0.05, 0.062, 0.088), c=(0, 0, 0.03), mat="steel_dark", bev=0)              # lug box
        p.cyl(0.018, 0.05, c=(0, 0, 0.098), r2=0.012, mat="steel", sides=6, bev=0)         # pick body
        p.cyl(0.012, 0.026, c=(0, 0, 0.136), r2=0.0, mat="cast_iron", sides=6, bev=0)      # carbide tip


K = math.tau / 1.62
for hand in (1, -1):              # +X half and -X half mirror (chevron lacing toward the centre)
    for start in (0.0, math.pi):
        for xa, xb in ((0.02, 0.86), (1.18, 1.57)):
            rings = []
            N = max(4, int((xb - xa) / 0.05))
            for i in range(N + 1):
                x = xa + (xb - xa) * i / N
                th = start + K * x
                rings.append([(hand * (x + dx), YD + r * math.cos(th), ZD + r * math.sin(th))
                              for dx, r in ((-0.018, RC - 0.01), (0.018, RC - 0.01), (0.018, 0.5), (-0.018, 0.5))])
            drum.loft(rings, mat="steel", bev=0.0)
            nP = max(1, round((xb - xa - 0.06) / 0.075))
            for j in range(nP + 1):
                x = xa + 0.03 + j * (xb - xa - 0.06) / nP
                pick(drum, hand * x, start + K * x, splay=hand * (0.25 if x > 1.45 else 0.05))
    for k in range(8):            # gauge picks on the cutting ring, splayed outward
        pick(drum, hand * 1.6, k / 8 * math.tau + 0.2, splay=hand * 0.9)
for th in (0.6, 0.6 + math.pi):   # centre breaker picks
    pick(drum, 0.0, th)

# ================================================================== gathering spinners (animated)
NP = V((0, -math.sin(BETA), math.cos(BETA)))
QT = Quaternion((1, 0, 0), BETA)


def arm_poly(sgn):
    cl = []
    for i in range(7):
        u = i / 6
        r = 0.13 + 0.33 * u
        a = -sgn * math.radians(42) * u ** 1.3
        cl.append(V((r * math.cos(a), r * math.sin(a), 0)))
    left, right = [], []
    for i, c in enumerate(cl):
        t = (cl[min(i + 1, 6)] - cl[max(i - 1, 0)]).normalized()
        nrm = V((-t.y, t.x, 0))
        w = 0.058 - 0.026 * (i / 6)
        left.append((c + nrm * w).to_2d())
        right.append((c - nrm * w).to_2d())
    return [tuple(p) for p in left] + [tuple(p) for p in reversed(right)]


SPIN = {}
for name, sx, sgn in (("gather_l", 1, -1), ("gather_r", -1, 1)):
    cpos = V((sx * 0.95, -1.98, zpan(-1.98)))
    sp = m.part(name, origin=cpos)
    SPIN[name] = sgn
    with sp.at(cpos, q=QT):
        sp.cyl(0.2, 0.05, c=(0, 0, 0.045), mat="steel_dark", sides=16, bev=0.008, segs=1)
        sp.lathe([(0, 0.05), (0.16, 0.05), (0.16, 0.1), (0.13, 0.15), (0.05, 0.175), (0, 0.178)], mat="paint_yellow",
                 sides=16, angle=25)
        sp.bolt_circle((0, 0, 0.15), (0, 0, 1), 0.085, 6, r=0.012)
        poly = arm_poly(sgn)
        for k in range(4):
            with sp.at((0, 0, 0.075), rot=(0, 0, k * 90)):
                sp.extrude(poly, 0.075, mat="paint_yellow", bev=0.01)
                ang = -sgn * math.radians(42)
                sp.box((0.07, 0.07, 0.08), c=(0.46 * math.cos(ang), 0.46 * math.sin(ang), 0),
                       rot=(0, 0, math.degrees(ang)), mat="steel", bev=0.008)

# ================================================================== lift cylinders (animated, follow the boom)
LIFT = {}
for suf, sx in (("l", 1), ("r", -1)):
    b = V((sx * 0.5, -1.40, 0.46))
    e = V((sx * 0.5, -2.0, 0.44))
    d = e - b
    bar = m.part(f"lift_barrel_{suf}", origin=b)
    with bar.at(b, q=aim(d)):
        lib.hydraulic_barrel(bar, 0.4, 0.07)
    rod = m.part(f"lift_rod_{suf}", origin=e)
    with rod.at(e, q=aim(-d)):
        lib.hydraulic_rod(rod, 0.4, 0.042)
    LIFT[suf] = (b, e)

# ================================================================== tail boom (animated: swing)
tail = m.part("tail_boom", origin=SWP)
TS, TE = V((0, 2.0, 0.62)), V((0, 3.25, 1.12))
tang = math.degrees(math.atan2(TE.z - TS.z, TE.y - TS.y))
tl = (TE - TS).length
with tail.at((TS + TE) / 2, rot=(tang, 0, 0)):
    tail.box((0.8, tl, 0.03), c=(0, 0, -0.015), mat="steel", bev=0.004)
    for sx in (1, -1):
        tail.box((0.04, tl + 0.04, 0.34), c=(sx * 0.42, 0, 0.1), mat="paint_yellow", bev=0.01)
        tail.box((0.07, tl + 0.04, 0.03), c=(sx * 0.445, 0, 0.27), mat="paint_yellow", bev=0.006)
        for k in range(4):
            tail.box((0.03, 0.05, 0.3), c=(sx * 0.455, -tl / 2 + 0.2 + k * 0.38, 0.09), mat="paint_yellow", bev=0.005)
        tail.decal("hazard", c=(sx * 0.4415, 0.477, 0.15), n=(sx, 0, 0), up=(0, 0, 1), w=0.33, h=0.07)
        tail.decal("warn_swing", c=(sx * 0.4415, -0.283, 0.1), n=(sx, 0, 0), up=(0, 0, 1), w=0.16)
    tail.box((0.5, tl - 0.1, 0.16), c=(0, -0.05, -0.12), mat="paint_yellow", bev=0.015)
    tail.box((0.8, tl, 0.02), c=(0, 0, -0.2), mat="steel_dark", bev=0)
tail.cyl(0.15, 0.92, c=(0, 3.25, 1.05), axis="X", mat="steel_dark", sides=16, bev=0.01, segs=1)   # head shaft
for sx in (1, -1):
    tail.lathe([(0, 0), (0.12, 0), (0.13, 0.02), (0.13, 0.08), (0.08, 0.11), (0, 0.11)], c=(sx * 0.46, 3.25, 1.05),
               rot=(0, 90 * sx, 0), mat="paint_yellow", sides=14, angle=28)
    tail.bolt_circle((sx * 0.565, 3.25, 1.05), (sx, 0, 0), 0.075, 6, r=0.009)
with tail.at((0, 3.28, 1.26), rot=(-35, 0, 0)):                                                    # head hood
    tail.box((0.92, 0.3, 0.025), mat="paint_yellow", bev=0.006)
    tail.decal("chev", c=(0, 0, 0.0126), n=(0, 0, 1), up=(0, -1, 0), w=0.86, h=0.12)
tail.cyl(0.15, 0.32, c=(0, 1.98, 0.43), mat="steel_dark", sides=14)                              # pivot hub
tail.cyl(0.19, 0.04, c=(0, 1.98, 0.6), mat="paint_yellow", sides=16, bev=0.008)
for sx in (1, -1):
    for dz in (-0.06, 0.06):
        tail.box((0.1, 0.12, 0.022), c=(sx * 0.49, 2.6, 0.84 + dz), mat="paint_yellow", bev=0.004)
    tail.cyl(0.026, 0.14, c=(sx * 0.49, 2.6, 0.84), mat="steel_dark", sides=8, bev=0)
    tail.box((0.06, 0.05, 0.05), c=(sx * 0.47, 3.13, 1.33), mat="paint_black", bev=0.006)          # tail lamps
    tail.box((0.045, 0.012, 0.035), c=(sx * 0.47, 3.158, 1.33), mat="emit_red", bev=0)

# ================================================================== swing cylinders (animated)
SWING = {}
for suf, sx in (("l", 1), ("r", -1)):
    b = V((sx * 0.72, YR + 0.09, 0.7))
    e = V((sx * 0.49, 2.6, 0.84))
    d = e - b
    bar = m.part(f"swing_barrel_{suf}", origin=b)
    with bar.at(b, q=aim(d)):
        lib.hydraulic_barrel(bar, 0.36, 0.045, sides=10)
    rod = m.part(f"swing_rod_{suf}", origin=e)
    with rod.at(e, q=aim(-d)):
        lib.hydraulic_rod(rod, 0.4, 0.026, sides=10)
    SWING[suf] = (b, e)

# ================================================================== conveyor flights (animated, ride the chain)
FP = [V((0, -2.42, -0.02)), V((0, -2.3, zpan(-2.3) + 0.03)), V((0, -1.3, 0.364 + 0.03)), V((0, YR, 0.56 + 0.03)),
      V((0, 2.02, 0.65)), V((0, 3.2, 1.13)), V((0, 3.31, 1.0))]
SEG = [(FP[i + 1] - FP[i]).length for i in range(len(FP) - 1)]
LP = sum(SEG)
VIS0, VIS1 = SEG[0] + 0.01, LP - SEG[-1] - 0.03
NF = 15
FPITCH = LP / NF


def path_at(s):
    s %= LP
    for i, L in enumerate(SEG):
        if s <= L or i == len(SEG) - 1:
            t = min(1.0, s / L)
            return FP[i].lerp(FP[i + 1], t), (FP[i + 1] - FP[i]).normalized()
        s -= L


def flight_pose(s, psi):
    p, tg = path_at(s)
    nrm = V((1, 0, 0)).cross(tg).normalized()
    q = Matrix(((1, 0, 0), (0, tg.y, nrm.y), (0, tg.z, nrm.z))).to_quaternion()
    if p.y > SWP.y + 0.02:
        qs = Quaternion((0, 0, 1), psi)
        p = SWP + qs @ (p - SWP)
        q = qs @ q
    return p, q, VIS0 <= (s % LP) <= VIS1


FLIGHTS = []
for i in range(NF):
    fp = m.part(f"flight_{i:02d}")
    fp.box((0.74, 0.05, 0.045), mat="steel_dark", bev=0.006, segs=1)
    for sx in (1, -1):
        fp.box((0.05, FPITCH - 0.1, 0.022), c=(sx * 0.27, FPITCH / 2, 0), mat="steel_dark", bev=0)   # chain strand
    p0, q0, vis = flight_pose(i * FPITCH, 0.0)
    fp.place = (p0, q0)
    FLIGHTS.append(fp.name)

# ================================================================== empties
m.empty("fx_work", (0, YD - 0.62, ZD), parent="boom")
m.empty("fx_ore", (0, 3.36, 1.0), parent="tail_boom")
for i, (lens, d) in enumerate(LIGHTS):
    m.empty(f"light_{i}", lens, beam=d)
m.empty("op", (1.12, 0.74, DECK))
m.empty("snd", (0, 0.0, 1.0))

lib.tick("build parts")
m.finish(rays=20, strength=1.2, low=0.42, noise_amt=0.2)
lib.tick("finish+grime")
for i, nm in enumerate(FLIGHTS):
    if not flight_pose(i * FPITCH, 0.0)[2]:
        m.objs[nm].scale = (0.0, 0.0, 0.0)

# ================================================================== animation
ANIM = ["boom", "drum", "gather_l", "gather_r", "tail_boom"] + \
       [f"lift_barrel_{s}" for s in "lr"] + [f"lift_rod_{s}" for s in "lr"] + \
       [f"swing_barrel_{s}" for s in "lr"] + [f"swing_rod_{s}" for s in "lr"] + FLIGHTS
BOOM_UP = math.radians(15)


def solve(t):
    out = {}
    a = -BOOM_UP * (0.5 - 0.5 * math.cos(math.tau * t))
    qb = Quaternion((1, 0, 0), a)
    out["boom"] = {"q": qb}
    out["drum"] = {"q": Quaternion((1, 0, 0), math.tau * 4 * t)}
    for nm, sgn in SPIN.items():
        out[nm] = {"q": Quaternion(NP, sgn * math.tau * 3 * t)}
    psi = math.radians(6) * math.sin(math.tau * t)
    qs = Quaternion((0, 0, 1), psi)
    out["tail_boom"] = {"q": qs}
    for suf, (b, e0) in LIFT.items():
        e = PIV + qb @ (e0 - PIV)
        out[f"lift_barrel_{suf}"] = {"q": aim(e - b) @ aim(e0 - b).inverted()}
        out[f"lift_rod_{suf}"] = {"loc": e, "q": aim(b - e) @ aim(b - e0).inverted()}
    for suf, (b, e0) in SWING.items():
        e = SWP + qs @ (e0 - SWP)
        out[f"swing_barrel_{suf}"] = {"q": aim(e - b) @ aim(e0 - b).inverted()}
        out[f"swing_rod_{suf}"] = {"loc": e, "q": aim(b - e) @ aim(b - e0).inverted()}
    for i, nm in enumerate(FLIGHTS):
        p, q, vis = flight_pose(i * FPITCH + 4 * FPITCH * t, psi)
        out[nm] = {"loc": p, "q": q, "s": (1, 1, 1) if vis else (0, 0, 0)}
    return out


m.clip("Work", 4.0, solve, ANIM)
m.clip("Idle", 2.0, None, ANIM)
lib.tick("clips")
tris, size = m.report()
if stem:
    m.export(stem)
    lib.tick("export")
if "--blend" in flags:
    m.save_blend()
if "--no-render" not in flags:
    views = [
        ("front3q", (-5.4, -6.9, 3.1), (0, -0.7, 0.75), 32),
        ("side", (-9.0, -0.3, 1.55), (0, -0.1, 0.8), 36),
        ("rear3q", (5.2, 7.0, 3.3), (0, 0.4, 0.8), 32),
        ("close", (-2.5, -5.2, 1.55), (-0.45, -2.55, 0.7), 34),
    ]
    if "--one" in flags:
        views = views[:1]
    m.render(views)
    if "--one" not in flags:
        m.pose("Work", 0.5)
        m.render([("work", (-5.4, -6.9, 3.1), (0, -0.7, 0.75), 32)])
        m.unpose()
