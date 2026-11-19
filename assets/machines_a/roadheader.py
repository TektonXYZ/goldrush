"""Kessler RH-40 roadheader (MOTHERLODE machines-A, depth 2 / tier 2).

Modeled on a Sandvik MT720 / Eickhoff ET210: crawler chassis, front gathering apron with two rotating star loading
wheels, centre conveyor through the body to a rear tail, a slewing turret carrying a telescopic cutter boom with an
axial, pick-studded conical cutting head, slew + lift cylinders, operator seat under a canopy at the rear side,
flameproof electrics cabinet, trailing cable and lights. The real ~12.5 m machine is compressed to 7.4 m.

    systemd-run --user --scope -q -p MemoryMax=3G -p MemorySwapMax=0 \
        bl assets/machines_a/roadheader.py -- public/models/machines/roadheader [--no-render] [--one]
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
from lib import V, aim, frame  # noqa: E402
from mathutils import Quaternion  # noqa: E402

stem, flags = lib.args()
m = lib.Machine("roadheader")

# ------------------------------------------------------------------ decals
KESSLER = ('<path d="M40,30 L1010,30 L980,150 L10,150 Z" fill="#151515"/>'
           '<path d="M10,170 L700,170 L692,200 L2,200 Z" fill="#C21D16"/>'
           '<text x="505" y="132" text-anchor="middle" font-family="Barlow Condensed Black" font-style="italic" '
           'font-size="118" letter-spacing="14" fill="#E8B400">KESSLER</text>')
A_ = m.atlas
A_.add("logo", 1024, 210, lib.svg(1024, 210, KESSLER, wear=0.4, seed=51))
A_.add("model", 640, 200, lib.svg_text("RH-40", font="Saira Stencil One", wear=0.35), fit=True)
A_.add("unit", 360, 260, lib.svg_text("04", font="Saira Stencil One", wear=0.4, seed=5), fit=True)
A_.add("hazard", 1024, 128, lib.svg_hazard(1024, 128, band=64, wear=0.45))
A_.add("danger_cut", 512, 400, lib.svg_panel(512, 400, "DANGER", ["ROTATING CUTTER", "STAY OUT OF", "BOOM SWING AREA"]))
A_.add("warn_volt", 512, 400, lib.svg_panel(512, 400, "DANGER", ["1000 VOLTS", "ISOLATE BEFORE", "OPENING"], seed=14))
A_.add("caution", 512, 360, lib.svg_panel(512, 360, "CAUTION", ["HIGH PRESSURE", "HYDRAULICS"], seed=13))
A_.add("plate", 600, 360, lib.svg_plate(600, 360, ["MODEL   RH-40 ROADHEADER", "SERIAL  RH40-0388", "CUTTER  250 KW",
                                                   "SUPPLY  1000 VAC 3PH", "BUILT   2020 KESSLER AG"],
                                         title="KESSLER MINING SYSTEMS"))
A_.add("iso", 256, 230, lib.svg_iso(256, 230))
A_.add("iso_bolt", 256, 230, lib.svg_iso(256, 230, "bolt"))
A_.add("gauge", 256, 256, lib.svg_gauge(256, 256, vmax=350, unit="BAR", label="SYSTEM"))
A_.add("gauge2", 256, 256, lib.svg_gauge(256, 256, vmax=600, unit="A", label="CUTTER", red=0.85, seed=29))
A_.add("chev", 1024, 128, lib.svg_chevron(1024, 128, wear=0.4))
A_.build()

# ------------------------------------------------------------------ key geometry (Blender, front = -Y)
XC, CW = 1.02, 0.56                       # crawler centre |x|, shoe width
CY0, CY1, CZ, CR = -1.25, 1.55, 0.37, 0.33
DECK = 1.24                               # chassis deck top
YF, YR = -1.3, 1.95                       # chassis front / rear
SLEW = V((0, -0.85, DECK))                # turret slew axis (vertical) foot
PIV = V((0, -1.15, 1.62))                 # boom lift pivot (axis X) on the turret
HB = V((0, -2.78, 0.98))                  # head base centre at rest
DIRB = (HB - PIV).normalized()
QB = frame(DIRB, (1, 0, 0))               # boom local: +Z along the boom, +X = machine X
UPB = QB @ V((0, 1, 0))
SHB = (HB - PIV).length                   # s of the head base along the boom
TB = math.tan(math.atan2(0.42, 1.48))
BETA = math.atan(TB)                      # apron slope


def zap(y):
    return 0.02 + (y + 2.78) * TB


def bpt(x, y, s):
    """Boom-local point (x right, y up, s along the boom from the pivot) -> machine coords at rest."""
    return PIV + QB @ V((x, y, s))


body = m.part("roadheader_body")

# ================================================================== crawlers + chassis
for sd in (1, -1):
    lib.crawler(body, sd * XC, sd, CY0, CY1, CZ, CR, width=CW, n=42)
for sx in (1, -1):
    body.box((0.46, 3.2, 0.62), c=(sx * 0.5, 0.3, 0.62), mat="paint_yellow", bev=0.02)              # side frames
body.plate([(-1.3, YF + 0.15), (1.3, YF + 0.15), (1.3, YR - 0.15), (1.15, YR), (-1.15, YR), (-1.3, YR - 0.15)],
           0.07, "XY", at=DECK - 0.035, mat="paint_yellow", bev=0.015)                              # deck
body.plate([(-0.9, YF - 0.15), (0.9, YF - 0.15), (1.3, YF + 0.15), (-1.3, YF + 0.15)], 0.07, "XY",
           at=DECK - 0.035, mat="paint_yellow", bev=0.015)                                          # deck nose
for sx in (1, -1):
    body.box((0.05, 3.3, 0.3), c=(sx * 1.305, 0.32, DECK - 0.17), mat="paint_yellow", bev=0.01)       # deck skirt
body.box((1.0, 0.1, 0.62), c=(0, YF - 0.02, 0.78), mat="paint_yellow", bev=0.015)                  # front plate
body.box((1.4, 0.12, 0.5), c=(0, YR - 0.05, 0.85), mat="paint_yellow", bev=0.015)                  # rear plate
# slewing ring on the deck
body.lathe([(0, 0.0), (0.66, 0.0), (0.66, 0.08), (0.6, 0.1), (0, 0.1)], c=SLEW, mat="steel_dark", sides=32, angle=25)
body.bolt_circle(SLEW + V((0, 0, 0.1)), (0, 0, 1), 0.63, 24, r=0.012)
# lift cylinder clevis on the deck nose
LB = [V((s * 0.36, -1.42, 1.06)) for s in (1, -1)]
LE = [bpt(s * 0.36, -0.32, 1.0) for s in (1, -1)]
# slew cylinders: base on the deck sides, eye on the turret
SB = [V((s * 1.0, -0.2, DECK + 0.16)) for s in (1, -1)]
SE = [V((s * 0.5, -1.02, DECK + 0.16)) for s in (1, -1)]
for i, s in enumerate((1, -1)):
    for dz in (-0.07, 0.07):
        body.box((0.14, 0.14, 0.03), c=SB[i] + V((0, 0, dz)), mat="paint_yellow", bev=0.004)
    body.cyl(0.03, 0.18, c=SB[i], mat="steel_dark", sides=8, bev=0)

# ================================================================== gathering apron + conveyor + tail
body.plate([(-2.8, 0.0), (-1.3, 0.0), (-1.3, zap(-1.3)), (-2.78, zap(-2.78)), (-2.8, 0.01)], 2.0, "YZ", at=0,
           mat="steel", bev=0.01)
for sx in (1, -1):
    with body.at((sx * 1.0, 0, 0), rot=(0, sx * -10, 0)):
        body.plate([(-2.8, 0.0), (-1.55, 0.0), (-1.55, zap(-1.55)), (-2.78, zap(-2.78)), (-2.8, 0.01)], 0.62, "YZ",
                   at=sx * 0.31, mat="steel", bev=0.01)                                            # side wings
    body.plate([(-2.8, 0.0), (-1.55, 0.0), (-1.55, 0.62), (-1.75, 0.66), (-2.8, 0.28)], 0.05, "YZ", at=sx * 1.6,
               mat="paint_yellow", bev=0.012)                                                       # wing plates
    body.plate([(-2.75, 0.28), (-1.75, 0.62), (-1.75, 0.68), (-2.75, 0.34)], 0.08, "YZ", at=sx * 1.61,
               mat="paint_yellow", bev=0.01)
    body.hyd(V((sx * 0.75, -1.6, 0.12)), V((sx * 0.75, -1.25, 0.6)), rb=0.06, rr=0.035)            # apron lift
    with body.at((0, -1.95, zap(-1.95)), rot=(math.degrees(BETA), 0, 0)):                          # channel guides
        body.box((0.03, 1.25, 0.05), c=(sx * 0.35, 0, 0.025), mat="steel_dark", bev=0.004)
    cpos = V((sx * 0.62, -2.05, zap(-2.05)))
    body.lathe([(0.48, 0.0), (0.51, 0.0), (0.51, 0.02), (0.48, 0.02)], c=cpos, q=Quaternion((1, 0, 0), BETA),
               mat="steel_dark", sides=26, cap0=False, cap1=False)
body.box((3.2, 0.07, 0.025), c=(0, -2.8, 0.0125), mat="steel", bev=0.006)
for k in range(5):                                                                                 # static flights
    y = -2.55 + k * 0.28
    with body.at((0, y, zap(y) + 0.025), rot=(math.degrees(BETA), 0, 0)):
        body.box((0.64, 0.045, 0.04), mat="steel_dark", bev=0.004, segs=1)
# tail conveyor out the back
TS, TE = V((0, YR - 0.05, 0.92)), V((0, 3.62, 1.48))
tang = math.degrees(math.atan2(TE.z - TS.z, TE.y - TS.y))
tl = (TE - TS).length
with body.at((TS + TE) / 2, rot=(tang, 0, 0)):
    body.box((0.72, tl, 0.03), c=(0, 0, -0.015), mat="steel", bev=0.004)
    for sx in (1, -1):
        body.box((0.04, tl, 0.3), c=(sx * 0.38, 0, 0.09), mat="paint_yellow", bev=0.01)
        body.box((0.06, tl, 0.025), c=(sx * 0.4, 0, 0.24), mat="paint_yellow", bev=0.006)
    body.box((0.48, tl - 0.1, 0.16), c=(0, -0.05, -0.12), mat="paint_yellow", bev=0.015)
    for k in range(5):
        body.box((0.6, 0.045, 0.035), c=(0, -tl / 2 + 0.2 + k * 0.38, 0.02), mat="steel_dark", bev=0)
body.cyl(0.14, 0.82, c=TE + V((0, 0.0, -0.06)), axis="X", mat="steel_dark", sides=16, bev=0.008, segs=1)
for sx in (1, -1):
    body.rod(V((sx * 0.45, YR + 0.02, 0.66)), V((sx * 0.22, 2.75, 1.08)), 0.04, mat="paint_yellow", sides=10)  # braces
    body.box((0.1, 0.08, 0.12), c=(sx * 0.45, YR + 0.03, 0.66), mat="paint_yellow", bev=0)
    body.decal("hazard", c=(sx * 0.401, 3.3, 1.38), n=(sx, 0, 0), up=(0, -math.sin(math.radians(tang)),
               math.cos(math.radians(tang))), w=0.5, h=0.07)
body.decal("chev", c=(0, 3.705, 1.43), n=(0, 1, 0), w=0.7, h=0.08)

# ================================================================== equipment on the deck
lib.fp_box(body, (-0.82, 1.15, DECK), (0.7, 1.3, 0.72), n=(0, 0, 1), up=(0, 1, 0), pitch=0.14)    # electrics
for k in range(3):
    body.cyl(0.035, 0.09, c=(-0.62 - k * 0.12, 1.83, DECK + 0.14), axis="Y", mat="brass", sides=8, bev=0)
body.path([(-0.62, 1.88, DECK + 0.14), (-0.62, 2.05, DECK + 0.0), (-0.85, 2.25, 0.6), (-1.0, 2.6, 0.1),
           (-1.15, 3.0, 0.045), (-1.3, 3.66, 0.045)], r=0.042, mat="cable", sides=10, res=7)
body.box((0.62, 0.7, 0.55), c=(-0.85, 0.05, DECK + 0.275), mat="paint_yellow", bev=0.035)        # hydraulic tank
body.cyl(0.07, 0.05, c=(-0.7, -0.15, DECK + 0.575), mat="steel_dark", sides=14)
body.cyl(0.085, 0.035, c=(-0.7, -0.15, DECK + 0.615), mat="plastic_black", sides=14, bev=0.006)
body.cyl(0.09, 0.25, c=(-1.0, 0.25, DECK + 0.68), mat="paint_grey", sides=14, bev=0.01)
body.lathe([(0, -0.42), (0.2, -0.42), (0.23, -0.38), (0.23, 0.36), (0.2, 0.42), (0, 0.42)],
           c=(0.82, 0.0, DECK + 0.27), rot=(-90, 0, 0), mat="paint_yellow", sides=20, angle=25)     # pump motor
for k in range(9):
    body.lathe([(0.23, -0.3 + k * 0.075), (0.245, -0.3 + k * 0.075), (0.245, -0.28 + k * 0.075),
                (0.23, -0.28 + k * 0.075)], c=(0.82, 0.0, DECK + 0.27), rot=(-90, 0, 0), mat="paint_yellow",
               sides=20, cap0=False, cap1=False)
body.box((0.5, 0.3, 0.22), c=(0.82, -0.55, DECK + 0.11), mat="paint_grey", bev=0.015)            # pump
body.box((0.16, 0.14, 0.12), c=(0.82, 0.12, DECK + 0.55), mat="paint_yellow", bev=0.01)
for k in range(4):
    body.hose(V((0.62 + k * 0.05, -0.55, DECK + 0.22)), (0, -1, 0.3), V((0.3 + k * 0.04, -0.65, DECK + 0.02)),
              (0, 0, -1), r=0.016, mat="rubber", sides=8, k=0.5)
# operator station (rear left) under a canopy
body.box((0.42, 0.4, 0.22), c=(0.85, 1.32, DECK + 0.11), mat="steel_dark", bev=0.01)
body.box((0.48, 0.46, 0.1), c=(0.85, 1.3, DECK + 0.27), mat="plastic_black", bev=0.035)
body.box((0.48, 0.1, 0.55), c=(0.85, 1.56, DECK + 0.58), rot=(-10, 0, 0), mat="plastic_black", bev=0.035)
body.box((0.7, 0.3, 0.5), c=(0.85, 0.82, DECK + 0.25), mat="paint_yellow", bev=0.015)            # console
with body.at((0.85, 0.86, DECK + 0.53), rot=(-30, 0, 0)):
    body.box((0.7, 0.34, 0.05), mat="steel_dark", bev=0.008)
    for k in range(6):
        x = -0.27 + k * 0.1
        body.rod((x, 0.06, 0.02), (x, 0.08, 0.16), 0.008, mat="steel", sides=6)
        body.sphere(0.02, c=(x, 0.08, 0.17), mat="paint_red" if k == 0 else "plastic_black", seg=8, rings=5)
    body.decal("gauge", c=(-0.15, -0.09, 0.026), n=(0, 0, 1), up=(0, -1, 0), w=0.1)
    body.decal("gauge2", c=(0.0, -0.09, 0.026), n=(0, 0, 1), up=(0, -1, 0), w=0.1)
    body.cyl(0.034, 0.03, c=(0.22, -0.09, 0.04), mat="paint_red", sides=12, bev=0.006)
POSTS = [(0.42, 0.62), (1.28, 0.62), (0.42, 1.88), (1.28, 1.88)]
ROOF = 2.32
for x, y in POSTS:
    body.box((0.1, 0.1, ROOF - DECK), c=(x, y, (ROOF + DECK) / 2), mat="paint_yellow", bev=0.012)
body.box((1.0, 1.4, 0.06), c=(0.85, 1.25, ROOF + 0.03), mat="paint_yellow", bev=0.012)
for (cx_, cy_, sx_, sy_) in ((0.85, 0.55, 1.02, 0.05), (0.85, 1.95, 1.02, 0.05), (0.35, 1.25, 0.05, 1.45),
                             (1.35, 1.25, 0.05, 1.45)):
    body.box((sx_, sy_, 0.09), c=(cx_, cy_, ROOF + 0.045), mat="paint_yellow", bev=0.008)
body.mesh_panel((1.32, 1.25, DECK + 0.75), 1.18, 0.6, cell=0.075, wire=0.008, rot=(0, 0, 90))
lib.work_light(body, (0.6, 0.53, ROOF + 0.02), (0, -1, -0.35), kind="bar", r=0.08)
# rear stabiliser jacks
for sx in (1, -1):
    body.box((0.2, 0.22, 0.3), c=(sx * 1.15, YR - 0.12, DECK - 0.2), mat="paint_yellow", bev=0.015)
    body.hyd(V((sx * 1.15, YR - 0.12, DECK - 0.32)), V((sx * 1.15, YR - 0.12, 0.08)), rb=0.065, rr=0.045,
             frac=0.55)
    body.box((0.26, 0.3, 0.05), c=(sx * 1.15, YR - 0.12, 0.025), mat="steel_dark", bev=0.008)
# headlights on the deck nose -> light_0 / light_1; rear lamps
LIGHTS = []
for sx in (1, -1):
    d = V((sx * 0.05, -1, -0.25)).normalized()
    body.box((0.08, 0.08, 0.14), c=(sx * 1.12, YF - 0.05, DECK + 0.07), mat="paint_yellow", bev=0)
    lens = lib.work_light(body, (sx * 1.12, YF - 0.1, DECK + 0.22), d, kind="round", r=0.08)
    LIGHTS.append((lens, d))
    body.box((0.1, 0.05, 0.06), c=(sx * 1.12, YR + 0.01, 0.98), mat="paint_black", bev=0)
    body.box((0.08, 0.01, 0.04), c=(sx * 1.12, YR + 0.037, 0.98), mat="emit_red", bev=0)
# body decals
for sx in (1, -1):
    body.decal("logo", c=(sx * 1.331, 0.55, DECK - 0.17), n=(sx, 0, 0), w=1.25)
    body.decal("hazard", c=V((sx * 1.651, -2.3, 0.47)), n=(sx, 0, 0), up=V((0, -0.34, 0.94)).normalized(), w=0.95,
               h=0.07)
    body.decal("danger_cut", c=(sx * 1.611, -1.72, 0.32), n=(sx, 0, 0), w=0.24)
body.decal("model", c=(-0.82, 1.802, DECK + 0.42), n=(0, 1, 0), w=0.34)
body.decal("warn_volt", c=(-0.467, 1.15, DECK + 0.35), n=(1, 0, 0), w=0.28)
body.decal("iso_bolt", c=(-0.467, 0.65, DECK + 0.4), n=(1, 0, 0), w=0.12)
body.decal("caution", c=(-0.85, -0.302, DECK + 0.3), n=(0, -1, 0), w=0.26)
body.decal("plate", c=(0.85, 0.667, DECK + 0.25), n=(0, -1, 0), w=0.24)
body.decal("unit", c=(0.85, 0.523, ROOF + 0.045), n=(0, -1, 0), w=0.11)
body.decal("chev", c=(0, YR + 0.011, 0.8), n=(0, 1, 0), w=1.3, h=0.08)
body.decal("hazard", c=(0, YF - 0.072, 0.98), n=(0, -1, 0), w=0.95, h=0.07)

# ================================================================== star loading wheels (animated)
NPN = V((0, -math.sin(BETA), math.cos(BETA)))
QT = Quaternion((1, 0, 0), BETA)
STARS = {}
for name, sx, sgn in (("star_l", 1, -1), ("star_r", -1, 1)):
    cpos = V((sx * 0.62, -2.05, zap(-2.05)))
    st = m.part(name, origin=cpos)
    STARS[name] = sgn
    with st.at(cpos, q=QT):
        st.cyl(0.2, 0.06, c=(0, 0, 0.05), mat="steel_dark", sides=16, bev=0.008)
        st.lathe([(0, 0.06), (0.15, 0.06), (0.15, 0.11), (0.1, 0.16), (0, 0.17)], mat="paint_yellow", sides=16,
                 angle=25)
        st.bolt_circle((0, 0, 0.14), (0, 0, 1), 0.08, 6, r=0.011)
        for k in range(5):
            with st.at((0, 0, 0.07), rot=(0, 0, k * 72)):
                pts = []
                for i in range(6):
                    u = i / 5
                    r = 0.14 + 0.34 * u
                    a = -sgn * math.radians(38) * u ** 1.4
                    pts.append((r * math.cos(a), r * math.sin(a)))
                left = [(x + 0.05 * (1 - 0.4 * i / 5) * -math.sin(math.atan2(y, x)),
                         y + 0.05 * (1 - 0.4 * i / 5) * math.cos(math.atan2(y, x))) for i, (x, y) in enumerate(pts)]
                right = [(x - 0.05 * (1 - 0.4 * i / 5) * -math.sin(math.atan2(y, x)),
                          y - 0.05 * (1 - 0.4 * i / 5) * math.cos(math.atan2(y, x))) for i, (x, y) in enumerate(pts)]
                st.extrude(left + right[::-1], 0.07, mat="paint_yellow", bev=0.008)
                ang = -sgn * math.radians(38)
                st.box((0.06, 0.06, 0.075), c=(0.47 * math.cos(ang), 0.47 * math.sin(ang), 0),
                       rot=(0, 0, math.degrees(ang)), mat="steel", bev=0.006)

# ================================================================== turret (animated: slew)
tur = m.part("turret", origin=SLEW)
tur.lathe([(0, 0.1), (0.6, 0.1), (0.6, 0.2), (0.52, 0.26), (0, 0.26)], c=SLEW, mat="paint_yellow", sides=28,
          angle=25)
tur.box((0.95, 0.75, 0.42), c=(0, -0.9, DECK + 0.45), mat="paint_yellow", bev=0.04)              # turret casting
for sx in (1, -1):
    tur.plate([(-0.6, DECK + 0.25), (-0.6, DECK + 0.62), (-0.95, 1.86), (-1.32, 1.82), (-1.4, 1.5), (-1.42, 0.98),
               (-1.25, DECK + 0.2)], 0.08, "YZ", at=sx * 0.33, mat="paint_yellow", bev=0.015)      # boom clevis
    tur.cyl(0.11, 0.1, c=(sx * 0.42, PIV.y, PIV.z), axis="X", mat="steel_dark", sides=14, bev=0.006)
    for dx in (-0.055, 0.055):                                                                    # lift cyl lugs
        tur.box((0.025, 0.14, 0.18), c=(sx * 0.36 + dx + sx * 0.0, LB[0].y, LB[0].z), mat="paint_yellow", bev=0)
    tur.cyl(0.03, 0.16, c=(sx * 0.36, LB[0].y, LB[0].z), axis="X", mat="steel_dark", sides=8, bev=0)
    for dz in (-0.07, 0.07):                                                                      # slew cyl lugs
        tur.box((0.14, 0.12, 0.03), c=SE[0 if sx > 0 else 1] + V((0, 0, dz)), mat="paint_yellow", bev=0)
    tur.cyl(0.03, 0.18, c=SE[0 if sx > 0 else 1], mat="steel_dark", sides=8, bev=0)
lib.cover(tur, (0, -0.85, DECK + 0.66), (0, 0, 1), 0.6, 0.45, pitch=0.12)
for k in range(3):
    tur.hose(V((0.2 - k * 0.12, -0.6, DECK + 0.66)), (0, 0, 1), V((0.12 - k * 0.12, -1.0, 1.88)), (0, -1, 0.2), r=0.018,
             mat="rubber", sides=8, k=0.5, sag=0.0)

# ================================================================== boom (animated: lift, child of turret)
boom = m.part("boom", origin=PIV, parent="turret")
with boom.at(PIV, q=QB):
    boom.box((0.72, 0.64, 1.15), c=(0, 0, 0.175), mat="paint_yellow", bev=0.05)                    # motor housing
    boom.cyl(0.13, 0.86, c=(0, 0, 0.0), rot=(0, 90, 0), mat="steel_dark", sides=16, bev=0.008)       # pivot boss
    boom.lathe([(0, 0), (0.28, 0), (0.28, 0.04), (0.2, 0.08), (0, 0.09)], c=(0, 0, -0.42), rot=(180, 0, 0),
               mat="paint_yellow", sides=20, angle=25)                                             # motor end cover
    for k in range(5):                                                                             # cooling ribs
        boom.box((0.76, 0.03, 0.04), c=(0, 0.33, -0.25 + k * 0.2), mat="paint_yellow", bev=0)
    lib.cover(boom, (0, 0.32, 0.15), (0, 1, 0), 0.5, 0.6, up=(0, 0, 1), pitch=0.12)
    boom.box((0.62, 0.54, 0.6), c=(0, 0, 1.05), mat="paint_yellow", bev=0.04)                      # telescope outer
    boom.box((0.52, 0.45, 0.22), c=(0, 0, 1.45), mat="steel", bev=0.02)                            # telescope inner
    boom.lathe([(0, 0), (0.33, 0), (0.38, 0.05), (0.38, 0.2), (0.33, 0.25), (0, 0.25)], c=(0, 0, 1.53),
               mat="paint_yellow", sides=24, angle=25)                                             # gearbox
    boom.bolt_circle((0, 0, 1.531), (0, 0, -1), 0.355, 12, r=0.011)
    for sx in (1, -1):                                                                              # side guards
        boom.box((0.03, 0.4, 0.95), c=(sx * 0.375, -0.05, 0.25), mat="paint_yellow", bev=0.008)
        boom.decal("logo", c=(sx * 0.3915, -0.02, 0.26), n=(sx, 0, 0), up=(0, 1, 0), w=0.8)
        boom.hose(V((sx * 0.2, 0.33, 0.6)), (0, 0, 1), V((sx * 0.2, 0.28, 1.35)), (0, -0.4, 1), r=0.016,
                  mat="rubber", sides=8, k=0.4)
    for sx in (1, -1):                                                                              # lift eyes
        for dx in (-0.055, 0.055):
            boom.box((0.025, 0.2, 0.16), c=(sx * 0.36 + dx, -0.29, 1.0), mat="paint_yellow", bev=0)
        boom.cyl(0.03, 0.16, c=(sx * 0.36, -0.32, 1.0), rot=(0, 90, 0), mat="steel_dark", sides=8, bev=0)
    boom.box((0.12, 0.1, 0.16), c=(0.0, 0.32, 1.25), mat="paint_red", bev=0.01)                    # methane sensor
    boom.decal("hazard", c=(0, 0.3215, 0.9), n=(0, 1, 0), up=(0, 0, 1), w=0.5, h=0.06)
    boom.decal("danger_cut", c=(0.3115, 0.0, 1.05), n=(1, 0, 0), up=(0, 1, 0), w=0.22)

# ================================================================== cutting head (animated: spin, child of boom)
head = m.part("head", origin=HB, parent="boom")
PROF = [(0, 0.0), (0.46, 0.0), (0.48, 0.05), (0.47, 0.18), (0.43, 0.42), (0.36, 0.64), (0.27, 0.8), (0.16, 0.9),
        (0.06, 0.95), (0, 0.96)]


def head_r(s):
    for (r0, z0), (r1, z1) in zip(PROF, PROF[1:]):
        if z0 <= s <= z1 and z1 > z0:
            return r0 + (r1 - r0) * (s - z0) / (z1 - z0)
    return 0.0


with head.at(HB, q=QB):
    head.lathe(PROF, mat="paint_yellow", sides=28, angle=20)
    head.lathe([(0.0, -0.02), (0.36, -0.02), (0.36, 0.0), (0.0, 0.0)], mat="steel_dark", sides=24, cap0=False,
               cap1=False)
    for start in range(3):                                                                         # 3-start lacing
        for j in range(24):
            s = 0.06 + j * 0.036
            if s > 0.9:
                break
            th = start * math.tau / 3 + s * (math.tau * 1.15 / 0.9)
            r = head_r(s)
            dr = (head_r(s + 0.01) - head_r(s - 0.01)) / 0.02
            nrm = V((math.cos(th), math.sin(th), -dr)).normalized()                                 # surface normal
            tan = V((-math.sin(th), math.cos(th), 0))
            ax = (nrm * 0.75 + tan * 0.45 + V((0, 0, 0.35))).normalized()
            base = V((math.cos(th) * r, math.sin(th) * r, s)) - nrm * 0.02
            with head.at(base, q=frame(ax, (0, 0, 1))):
                head.box((0.045, 0.055, 0.075), c=(0, 0, 0.03), mat="steel_dark", bev=0)
                head.cyl(0.016, 0.045, c=(0, 0, 0.088), r2=0.011, mat="steel", sides=6, bev=0)
                head.cyl(0.011, 0.024, c=(0, 0, 0.122), r2=0.0, mat="cast_iron", sides=6, bev=0)
    for k in range(6):                                                                              # spray nozzles
        a = k / 6 * math.tau
        head.cyl(0.012, 0.03, c=(math.cos(a) * 0.25, math.sin(a) * 0.25, 0.835), mat="brass", sides=6, bev=0)

# ================================================================== cylinders (lift: turret children; slew: root)
def stroke_fit(lens):
    lo, hi = min(lens), max(lens)
    barrel = lo - 0.1
    return barrel, hi - barrel + 0.08


SLEW_MAX, LIFT_LO, LIFT_HI = math.radians(18), math.radians(4), math.radians(-14)


def lift_angle(t):
    return -0.07 - 0.11 * math.sin(math.tau * 2 * t)


def slew_angle(t):
    return SLEW_MAX * math.sin(math.tau * t)


def rotx(p, piv, a):
    return piv + Quaternion((1, 0, 0), a) @ (p - piv)


def rotz(p, piv, a):
    return piv + Quaternion((0, 0, 1), a) @ (p - piv)


L_LEN = [(rotx(LE[0], PIV, lift_angle(t / 60)) - LB[0]).length for t in range(61)]
S_LEN = [(rotz(SE[0], SLEW, slew_angle(t / 60)) - SB[0]).length for t in range(61)]
LBR, LRD = stroke_fit(L_LEN + [(LE[0] - LB[0]).length])
SBR, SRD = stroke_fit(S_LEN + [(SE[0] - SB[0]).length])
print(f"[roadheader] lift cyl {min(L_LEN):.3f}..{max(L_LEN):.3f}  slew cyl {min(S_LEN):.3f}..{max(S_LEN):.3f}")
for i, suf in enumerate("lr"):
    b, e = LB[i], LE[i]
    bar = m.part(f"lift_barrel_{suf}", origin=b, parent="turret")
    with bar.at(b, q=aim(e - b)):
        lib.hydraulic_barrel(bar, LBR, 0.075)
    rod = m.part(f"lift_rod_{suf}", origin=e, parent="turret")
    with rod.at(e, q=aim(b - e)):
        lib.hydraulic_rod(rod, LRD, 0.048)
    b, e = SB[i], SE[i]
    bar = m.part(f"slew_barrel_{suf}", origin=b)
    with bar.at(b, q=aim(e - b)):
        lib.hydraulic_barrel(bar, SBR, 0.07)
    rod = m.part(f"slew_rod_{suf}", origin=e)
    with rod.at(e, q=aim(b - e)):
        lib.hydraulic_rod(rod, SRD, 0.045)

# ================================================================== empties
m.empty("fx_work", HB + DIRB * 1.0, parent="boom")
m.empty("fx_ore", (0, 3.66, 1.42))
for i, (lens, d) in enumerate(LIGHTS):
    m.empty(f"light_{i}", lens, beam=d)
m.empty("op", (0.85, 1.05, DECK))
m.empty("snd", (0, 0.2, 1.4))

lib.tick("build parts")
m.finish(rays=20, strength=1.2, low=0.42, noise_amt=0.2)
lib.tick("finish+grime")

ANIM = ["turret", "boom", "head", "star_l", "star_r", "lift_barrel_l", "lift_rod_l", "lift_barrel_r", "lift_rod_r",
        "slew_barrel_l", "slew_rod_l", "slew_barrel_r", "slew_rod_r"]


def rig(lift, slew, spin, stars):
    out = {"turret": {"q": Quaternion((0, 0, 1), slew)},
           "boom": {"q": Quaternion((1, 0, 0), lift)},
           "head": {"q": Quaternion(DIRB, spin)}}
    for nm, sgn in STARS.items():
        out[nm] = {"q": Quaternion(NPN, sgn * stars)}
    for i, suf in enumerate("lr"):
        b, e0 = LB[i], LE[i]
        e = rotx(e0, PIV, lift)                       # turret-local
        out[f"lift_barrel_{suf}"] = {"q": aim(e - b) @ aim(e0 - b).inverted()}
        out[f"lift_rod_{suf}"] = {"loc": e - SLEW, "q": aim(b - e) @ aim(b - e0).inverted()}
        b, e0 = SB[i], SE[i]
        e = rotz(e0, SLEW, slew)                      # machine space
        out[f"slew_barrel_{suf}"] = {"q": aim(e - b) @ aim(e0 - b).inverted()}
        out[f"slew_rod_{suf}"] = {"loc": e, "q": aim(b - e) @ aim(b - e0).inverted()}
    return out


def work(t):
    return rig(lift_angle(t), slew_angle(t), math.tau * 6 * t, math.tau * 3 * t)


def idle(t):
    return rig(0.0, 0.0, 0.0, 0.0)


m.clip("Work", 6.0, work, ANIM)
m.clip("Idle", 2.0, idle, ANIM)
lib.tick("clips")
tris, size = m.report()
if stem:
    m.export(stem)
    lib.tick("export")
if "--no-render" not in flags:
    views = [
        ("front3q", (-5.4, -7.2, 3.4), (0, -0.9, 1.0), 32),
        ("side", (-9.0, -0.2, 1.7), (0, 0.0, 1.0), 36),
        ("rear3q", (5.2, 7.0, 3.6), (0, 0.5, 1.0), 32),
        ("close", (-2.4, -5.2, 1.9), (-0.2, -2.6, 0.9), 34),
    ]
    if "--one" in flags:
        views = views[:1]
    m.render(views)
    if "--one" not in flags:
        m.pose("Work", 0.2)
        m.render([("sweep", (-5.4, -7.2, 3.4), (0, -0.9, 1.0), 32)])
        m.unpose()
