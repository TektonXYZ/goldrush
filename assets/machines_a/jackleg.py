"""Brennan Pneumatics JL-50 jackleg drill + towable compressor (MOTHERLODE machines-A, depth 1 / tier 1).

A hand-held pneumatic rock drill (cylinder body with through-bolts, back head, T-handle + throttle, front head/chuck)
riding on a telescoping air leg braced against the floor, a 1.8 m hex drill steel with a carbide button bit into the
face, yellow air hose + red water hose snaking back to a two-wheel diesel compressor (canopy, louvres, cooler grille
with fan, exhaust stack, gauges, lifting bail, drawbar), and a work light on a tripod.

    systemd-run --user --scope -q -p MemoryMax=3G -p MemorySwapMax=0 \
        bl assets/machines_a/jackleg.py -- public/models/machines/jackleg [--no-render] [--one]
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
from lib import V, aim, frame  # noqa: E402
from mathutils import Quaternion  # noqa: E402

stem, flags = lib.args()
m = lib.Machine("jackleg")

# ------------------------------------------------------------------ decals
BADGE = ('<rect x="6" y="6" width="{w2}" height="{h2}" rx="18" fill="none" stroke="#151515" stroke-width="10"/>'
         '<text x="{cx}" y="{y1}" text-anchor="middle" font-family="Barlow Condensed Black" font-size="{s1}" '
         'letter-spacing="6" fill="#151515">BRENNAN</text>'
         '<text x="{cx}" y="{y2}" text-anchor="middle" font-family="Barlow Condensed ExtraBold" font-size="{s2}" '
         'letter-spacing="14" fill="#151515">PNEUMATICS</text>')
A_ = m.atlas
A_.add("brennan", 900, 300, lib.svg(900, 300, BADGE.format(w2=888, h2=288, cx=450, y1=170, s1=170, y2=262, s2=62),
                                    wear=0.4, seed=41))
A_.add("model", 640, 180, lib.svg_text("BP-185", font="Saira Stencil One", wear=0.35), fit=True)
A_.add("cfm", 640, 120, lib.svg_text("185 CFM  7 BAR", font="Barlow Condensed ExtraBold", wear=0.3), fit=True)
A_.add("jl50", 400, 120, lib.svg_text("JL-50", font="Saira Stencil One", wear=0.3, fill="#E8E6DF"), fit=True)
A_.add("danger_air", 512, 400, lib.svg_panel(512, 400, "DANGER", ["HIGH PRESSURE AIR", "BLEED OFF BEFORE",
                                                                  "UNCOUPLING HOSES"]))
A_.add("warn_fan", 512, 360, lib.svg_panel(512, 360, "WARNING", ["ROTATING FAN", "KEEP HANDS CLEAR"], seed=12))
A_.add("caution_hot", 512, 360, lib.svg_panel(512, 360, "CAUTION", ["HOT SURFACES", "EXHAUST"], seed=13))
A_.add("gauge", 256, 256, lib.svg_gauge(256, 256, vmax=200, unit="PSI", label="DISCHARGE", red=0.8))
A_.add("gauge2", 256, 256, lib.svg_gauge(256, 256, vmax=120, unit="C", label="OIL TEMP", red=0.85, seed=29))
A_.add("gauge3", 256, 256, lib.svg_gauge(256, 256, vmax=3000, unit="RPM", label="ENGINE", red=0.8, seed=31))
A_.add("lift", 400, 110, lib.svg_text("LIFT HERE", font="Barlow Condensed Black", wear=0.3), fit=True)
A_.add("chev", 1024, 128, lib.svg_chevron(1024, 128, wear=0.4))
A_.add("hazard", 1024, 128, lib.svg_hazard(1024, 128, band=64, wear=0.45))
A_.add("plate", 600, 360, lib.svg_plate(600, 360, ["MODEL   JL-50 JACKLEG", "SERIAL  JL50-11873", "AIR     90 PSI",
                                                   "WATER   60 PSI", "BRENNAN PNEUMATICS"], title="BRENNAN"))
A_.build()

body = m.part("jackleg_body")
rng = random.Random(5)

# ------------------------------------------------------------------ key geometry (Blender: front/face = -Y)
DIR = V((0, -1, 0.045)).normalized()      # drilling direction (slightly up-dip)
TIP = V((0.1, -3.62, 1.36))               # button bit tip at the face
STEEL_L = 1.8
CHUCK = TIP - DIR * (STEEL_L - 0.023)     # front of the drill's front head (bit tip lands on TIP)
QD = frame(DIR, (1, 0, 0))               # drill local: +Z along DIR, +X = machine X


def dp(x, y, z):
    """Point in drill-local coords (x right, y up-ish, z along the steel toward the face, 0 at the chuck)."""
    return CHUCK + QD @ V((x, y, z))


# ================================================================== rock drill (animated: percussion shake)
drill = m.part("drill", origin=CHUCK)
with drill.at(CHUCK, q=QD):
    # drill axis = local -Z (body extends backward from the chuck)
    drill.cyl(0.042, 0.13, c=(0, 0, -0.065), mat="steel", sides=16, bev=0.004)                   # front head
    drill.cyl(0.05, 0.03, c=(0, 0, -0.14), mat="steel_dark", sides=16, bev=0)
    drill.box((0.03, 0.02, 0.07), c=(0.045, 0, -0.04), mat="steel_dark", bev=0)                   # steel retainer
    drill.cyl(0.062, 0.34, c=(0, 0, -0.33), mat="paint_grey", sides=18, bev=0.008)                 # cylinder body
    for k in range(4):                                                                            # exhaust ports
        drill.box((0.13, 0.012, 0.02), c=(0, 0.058, -0.24 - k * 0.035), mat="steel_dark", bev=0)
    drill.lathe([(0.064, 0), (0.078, 0.01), (0.078, 0.07), (0.064, 0.08)], c=(0, 0, -0.29), mat="steel_dark",
                sides=18, cap0=False, cap1=False)                                                 # muffler ring
    for sx in (1, -1):                                                                            # side bolts
        drill.cyl(0.011, 0.58, c=(sx * 0.07, 0, -0.33), mat="steel", sides=6, bev=0)
        for zz in (-0.04, -0.62):
            drill.cyl(0.016, 0.02, c=(sx * 0.07, 0, zz), mat="steel_dark", sides=6, bev=0)
    drill.cyl(0.07, 0.12, c=(0, 0, -0.56), mat="steel", sides=18, bev=0.006)                      # back head
    drill.cyl(0.075, 0.03, c=(0, 0, -0.63), mat="steel_dark", sides=18, bev=0)
    drill.cyl(0.022, 0.09, c=(0, 0.075, -0.58), rot=(90, 0, 0), mat="brass", sides=10, bev=0)     # air swivel
    drill.cyl(0.015, 0.06, c=(0.05, 0.06, -0.6), rot=(60, 0, 0), mat="brass", sides=8, bev=0)    # water inlet
    # T-handle + throttle
    drill.rod((0, 0, -0.64), (0, 0, -0.78), 0.018, mat="steel", sides=8)
    drill.rod((-0.17, 0, -0.8), (0.17, 0, -0.8), 0.016, mat="steel", sides=8)
    for sx in (1, -1):
        drill.cyl(0.024, 0.11, c=(sx * 0.12, 0, -0.8), rot=(0, 90, 0), mat="rubber", sides=10, bev=0)
    drill.box((0.02, 0.09, 0.03), c=(0.0, 0.045, -0.7), rot=(25, 0, 0), mat="paint_red", bev=0)  # throttle lever
    # leg yoke (clevis under the body)
    for sx in (1, -1):
        drill.box((0.016, 0.08, 0.1), c=(sx * 0.04, -0.09, -0.36), mat="steel_dark", bev=0)
    drill.cyl(0.018, 0.11, c=(0, -0.12, -0.36), rot=(0, 90, 0), mat="steel", sides=8, bev=0)
    drill.box((0.04, 0.012, 0.11), c=(0.0, 0.064, -0.45), mat="aluminium", bev=0)                # data plate
    drill.decal("jl50", c=(0.0, 0.0705, -0.45), n=(0, 1, 0), up=(0, 0, -1), w=0.1)

# ================================================================== drill steel + bit (child of drill, spins)
steel = m.part("steel", origin=CHUCK, parent="drill")
with steel.at(CHUCK, q=QD):
    steel.cyl(0.014, STEEL_L - 0.02, c=(0, 0, (STEEL_L - 0.02) / 2 - 0.12), mat="steel", sides=6, bev=0)   # hex steel
    steel.cyl(0.02, 0.025, c=(0, 0, -0.02), mat="steel_dark", sides=8, bev=0)                    # collar
    steel.cyl(0.016, 0.06, c=(0, 0, STEEL_L - 0.15), r2=0.019, mat="steel_dark", sides=8, bev=0)  # taper
    steel.cyl(0.019, 0.07, c=(0, 0, STEEL_L - 0.085), mat="steel_dark", sides=10, bev=0)          # bit skirt
    steel.lathe([(0.019, 0), (0.0205, 0.012), (0.017, 0.02), (0, 0.022)], c=(0, 0, STEEL_L - 0.05),
                mat="steel_dark", sides=10, cap0=True, cap1=False)
    for k in range(5):                                                                            # carbide buttons
        a = k / 5 * math.tau
        steel.sphere(0.0045, c=(math.cos(a) * 0.012, math.sin(a) * 0.012, STEEL_L - 0.029), mat="cast_iron", seg=6,
                     rings=4)
    steel.sphere(0.005, c=(0, 0, STEEL_L - 0.027), mat="cast_iron", seg=6, rings=4)

# ================================================================== air leg
YOKE = dp(0, -0.12, -0.36)
FOOT = V((0.52, -0.78, 0.0))
LEGD = (YOKE - FOOT).normalized()
LEG_L = (YOKE - FOOT).length
leg_out = m.part("leg_outer", origin=YOKE)
with leg_out.at(YOKE, q=aim(-LEGD)):                       # local +Z runs down the leg from the yoke
    leg_out.cyl(0.03, 0.06, c=(0, 0, 0.0), rot=(0, 90, 0), mat="steel_dark", sides=10, bev=0)     # top eye
    leg_out.cyl(0.042, 0.06, c=(0, 0, 0.06), mat="steel_dark", sides=14, bev=0.004)               # top cap / valve
    leg_out.cyl(0.04, 0.92, c=(0, 0, 0.55), mat="paint_yellow", sides=16, bev=0.004)              # outer cylinder
    leg_out.cyl(0.044, 0.04, c=(0, 0, 1.02), mat="steel_dark", sides=16, bev=0)                   # gland nut
    leg_out.cyl(0.012, 0.05, c=(0.045, 0, 0.1), rot=(0, 90, 0), mat="brass", sides=8, bev=0)      # air inlet
    leg_out.box((0.014, 0.05, 0.12), c=(0.0, 0.042, 0.18), mat="paint_red", bev=0)               # leg control
leg_in = m.part("leg_inner", origin=FOOT)
with leg_in.at(FOOT, q=aim(LEGD)):                         # local +Z runs up the leg from the foot
    leg_in.cyl(0.028, LEG_L - 0.9, c=(0, 0, (LEG_L - 0.9) / 2 + 0.06), mat="chrome", sides=12, bev=0)
    leg_in.cyl(0.034, 0.05, c=(0, 0, 0.05), mat="steel_dark", sides=12, bev=0)
with leg_in.at(FOOT, q=Quaternion()):
    leg_in.extrude([(-0.07, -0.05), (0.07, -0.05), (0.09, 0.04), (0, 0.08), (-0.09, 0.04)], 0.025, c=(0, 0, 0.012),
                   mat="steel_dark", bev=0.004)                                                    # claw foot
    for k in range(3):
        leg_in.cyl(0.012, 0.03, c=(-0.05 + k * 0.05, -0.04, -0.005), r2=0.0, rot=(180, 0, 0), mat="steel", sides=6,
                   bev=0)

# ================================================================== hoses back to the compressor (floor snakes)
BACKHEAD = dp(0, 0.075 + 0.045, -0.58)
WATER_IN = dp(0.05 + 0.03, 0.06 + 0.02, -0.6)
AIR_OUT = V((-0.45, 1.2, 0.62))      # compressor service valve (front panel)
WATER_TANK = V((-1.33, 0.95, 0.55))


def snake(p0, p1, amp, waves, z):
    pts = []
    for i in range(1, 17):
        t = i / 17
        p = p0.lerp(p1, t)
        d = (p1 - p0).normalized()
        side = V((-d.y, d.x, 0))
        pts.append(V((p.x, p.y, z)) + side * amp * math.sin(t * math.pi * waves))
    return pts


def drop(p, x_floor, y_floor, r):
    """Hose leaving a fitting upward, arcing back and hanging down to the floor (no overshoot)."""
    return [p, p + V((0, 0.03, 0.06)), V((p.x * 0.6 + x_floor * 0.4, p.y + 0.2, p.z + 0.04)),
            V((p.x * 0.3 + x_floor * 0.7, p.y + 0.42, p.z * 0.55)), V((x_floor, y_floor - 0.12, 0.12)),
            V((x_floor, y_floor, r))]


air_pts = drop(BACKHEAD, -0.16, -0.62, 0.026) + \
    snake(V((-0.16, -0.62, 0.0)), V((-0.42, 0.98, 0.0)), 0.25, 3, 0.026) + \
    [V((-0.44, 1.06, 0.05)), V((-0.45, 1.1, 0.28)), AIR_OUT + V((0, -0.05, -0.04)), AIR_OUT]
body.path(air_pts, r=0.024, mat="hose_yellow", sides=10, res=4, tension=0.5)
water_pts = drop(WATER_IN, 0.02, -0.58, 0.017) + \
    snake(V((0.02, -0.58, 0.0)), V((-1.2, 0.8, 0.0)), 0.2, 4, 0.017) + \
    [V((-1.28, 0.86, 0.06)), WATER_TANK + V((0, -0.06, -0.12)), WATER_TANK + V((0, -0.04, -0.05))]
body.path(water_pts, r=0.016, mat="hose_red", sides=8, res=4)
for p_, r_ in ((BACKHEAD, 0.024), (AIR_OUT, 0.024)):          # claw couplings
    body.cyl(r_ * 1.5, 0.06, c=p_, q=aim(V((0, 0, 1))), mat="brass", sides=10, bev=0)

# ================================================================== compressor (trailer static, canopy shakes)
CX, CY0, CY1 = -0.75, 1.25, 3.15          # canopy centre x, front y, rear y
CW, CZ0, CZ1 = 1.25, 0.48, 1.38           # canopy width, bottom, top
AX_Y, WHL_R, TRK = 2.25, 0.32, 1.58
for sx in (1, -1):                                                                                 # chassis rails
    body.box((0.08, 2.1, 0.12), c=(CX + sx * 0.45, (CY0 + CY1) / 2, 0.42), mat="paint_black", bev=0.008)
body.box((0.98, 0.08, 0.12), c=(CX, CY0 + 0.05, 0.42), mat="paint_black", bev=0.008)
body.box((0.98, 0.08, 0.12), c=(CX, CY1 - 0.05, 0.42), mat="paint_black", bev=0.008)
body.cyl(0.04, TRK - 0.2, c=(CX, AX_Y, WHL_R), axis="X", mat="paint_black", sides=10, bev=0)       # axle
for sx in (1, -1):                                                                                 # leaf springs
    body.box((0.06, 0.75, 0.04), c=(CX + sx * 0.45, AX_Y, 0.36), mat="steel_dark", bev=0)
for sx in (1, -1):                                                                                 # road wheels
    c = V((CX + sx * TRK / 2, AX_Y, WHL_R))
    with body.at(c, q=lib.Euler((0, math.radians(90 * sx), 0)).to_quaternion()):
        body.lathe([(0.17, -0.09), (0.25, -0.1), (0.3, -0.095), (0.32, -0.06), (0.32, 0.06), (0.3, 0.095), (0.25, 0.1),
                    (0.17, 0.09)], mat="rubber", sides=24, cap0=False, cap1=False, angle=40)
        body.cyl(0.17, 0.17, mat="paint_grey", sides=20, bev=0, caps=False)
        body.lathe([(0.17, 0.085), (0.15, 0.09), (0.07, 0.06), (0, 0.06)], mat="paint_grey", sides=20, cap0=False,
                   cap1=False)
        for k in range(5):
            a = k / 5 * math.tau
            body.cyl(0.011, 0.02, c=(math.cos(a) * 0.05, math.sin(a) * 0.05, 0.07), mat="steel_dark", sides=6, bev=0)
        body.lathe([(0, -0.06), (0.15, -0.06)], mat="paint_grey", sides=16, cap0=False, cap1=False)
    body.box((0.26, 0.82, 0.03), c=(CX + sx * TRK / 2, AX_Y, 0.74), mat="paint_black", bev=0.006)  # mudguard
    for sy in (1, -1):
        body.box((0.26, 0.2, 0.03), c=(CX + sx * TRK / 2, AX_Y + sy * 0.48, 0.66), rot=(sy * -40, 0, 0),
                 mat="paint_black", bev=0.006)
    body.box((0.05, 0.05, 0.3), c=(CX + sx * (TRK / 2 - 0.12), AX_Y, 0.6), mat="paint_black", bev=0)
# drawbar (A-frame) + tow eye + jack stand + chains
for sx in (1, -1):
    body.rod((CX + sx * 0.42, CY1 - 0.1, 0.42), (CX, 3.62, 0.5), 0.035, mat="paint_black", sides=8)
body.box((0.12, 0.2, 0.1), c=(CX, 3.6, 0.5), mat="paint_black", bev=0.008)
body.lathe([(0.055, -0.02), (0.085, -0.02), (0.085, 0.02), (0.055, 0.02)], c=(CX, 3.74, 0.5), mat="steel_dark",
           sides=14, cap0=False, cap1=False)                                                     # tow eye ring
body.box((0.05, 0.12, 0.03), c=(CX, 3.66, 0.5), mat="steel_dark", bev=0)
body.cyl(0.035, 0.42, c=(CX + 0.12, 3.45, 0.3), mat="paint_black", sides=10, bev=0)                # jack stand
body.box((0.14, 0.14, 0.02), c=(CX + 0.12, 3.45, 0.01), mat="steel_dark", bev=0)
body.rod((CX + 0.12, 3.45, 0.52), (CX + 0.12, 3.45, 0.62), 0.008, mat="steel", sides=6)
body.rod((CX + 0.12, 3.45, 0.62), (CX + 0.2, 3.45, 0.62), 0.008, mat="steel", sides=6)
for sx in (1, -1):
    pts = [V((CX + sx * 0.06, 3.58, 0.46)) + V((sx * 0.02 * k, 0.03 * k, -0.06 * math.sin(k / 5 * math.pi)))
           for k in range(6)]
    body.tube(pts, 0.007, mat="steel", sides=6)
# water tank on the front of the chassis (red pressure vessel)
body.cyl(0.13, 0.4, c=WATER_TANK + V((0, 0.1, -0.2)), mat="paint_red", sides=16, bev=0.01)
body.lathe([(0.13, 0), (0.1, 0.05), (0, 0.07)], c=WATER_TANK + V((0, 0.1, 0.0)), mat="paint_red", sides=16, cap0=False)
body.cyl(0.02, 0.08, c=WATER_TANK + V((0, 0.1, 0.1)), mat="brass", sides=8, bev=0)
body.box((0.3, 0.3, 0.04), c=WATER_TANK + V((0, 0.1, -0.42)), mat="paint_black", bev=0)
for sx in (1, -1):
    for sy in (0.0, 0.2):
        body.box((0.03, 0.03, 0.13), c=V((WATER_TANK.x + sx * 0.12, WATER_TANK.y + sy, 0.065)), mat="paint_black",
                 bev=0)

# canopy (animated: engine vibration) - rounded body, louvres, doors, cooler grille + fan, stack, bail, panel
canopy = m.part("comp_canopy", origin=(CX, (CY0 + CY1) / 2, CZ0))
cy = (CY0 + CY1) / 2
SH = 0.22                                                                                      # open fan shroud
canopy.box((CW, CY1 - CY0 - SH, CZ1 - CZ0), c=(CX, cy - SH / 2, (CZ0 + CZ1) / 2), mat="paint_yellow", bev=0.07)
canopy.box((CW - 0.16, 0.02, CZ1 - CZ0 - 0.16), c=(CX, CY1 - SH + 0.005, (CZ0 + CZ1) / 2), mat="steel_dark",
           bev=0)                                                                                # cooler core
for sx in (1, -1):
    canopy.box((0.05, SH, CZ1 - CZ0), c=(CX + sx * (CW / 2 - 0.025), CY1 - SH / 2, (CZ0 + CZ1) / 2),
               mat="paint_yellow", bev=0.012)
for zz in (CZ0 + 0.025, CZ1 - 0.025):
    canopy.box((CW, SH, 0.05), c=(CX, CY1 - SH / 2, zz), mat="paint_yellow", bev=0.012)
canopy.box((CW + 0.04, CY1 - CY0 + 0.04, 0.05), c=(CX, cy, CZ0 + 0.025), mat="paint_black", bev=0.01)   # base frame
for sx in (1, -1):
    xs = CX + sx * (CW / 2 + 0.002)
    canopy.box((0.006, 0.8, 0.012), c=(xs, cy - 0.2, CZ1 - 0.12), mat="steel_dark", bev=0)        # door seams
    canopy.box((0.006, 0.8, 0.012), c=(xs, cy - 0.2, CZ0 + 0.1), mat="steel_dark", bev=0)
    for yy in (cy - 0.6, cy + 0.2):
        canopy.box((0.006, 0.012, CZ1 - CZ0 - 0.22), c=(xs, yy, (CZ0 + CZ1) / 2), mat="steel_dark", bev=0)
    canopy.grille((CX + sx * (CW / 2 + 0.005), cy + 0.62, (CZ0 + CZ1) / 2), 0.5, 0.55, 8, rot=(0, 0, 90 * sx),
                  depth=0.025, mat="paint_yellow", slat_mat="steel_dark", frame=0.025)
    for yy in (cy - 0.55, cy + 0.15):                                                             # hinges + latch
        canopy.box((0.02, 0.06, 0.04), c=(CX + sx * (CW / 2 + 0.01), yy, CZ1 - 0.2), mat="steel_dark", bev=0)
    canopy.box((0.025, 0.08, 0.05), c=(CX + sx * (CW / 2 + 0.012), cy - 0.2, (CZ0 + CZ1) / 2), mat="plastic_black",
               bev=0)
    canopy.decal("brennan", c=(CX + sx * (CW / 2 + 0.002), cy - 0.2, CZ1 - 0.38), n=(sx, 0, 0), w=0.78)
    canopy.decal("model", c=(CX + sx * (CW / 2 + 0.002), cy - 0.2, CZ0 + 0.26), n=(sx, 0, 0), w=0.34)
canopy.mesh_panel((CX, CY1 - 0.004, (CZ0 + CZ1) / 2), CW - 0.1, CZ1 - CZ0 - 0.1, cell=0.045, wire=0.006)
canopy.decal("warn_fan", c=(CX + 0.42, CY1 + 0.02, CZ1 - 0.1), n=(0, 1, 0), w=0.2)
canopy.decal("chev", c=(CX, CY1 + 0.02, CZ0 + 0.07), n=(0, 1, 0), w=CW - 0.1, h=0.07)
# front panel: gauges behind a window, service valves, decals
canopy.box((0.62, 0.02, 0.34), c=(CX + 0.12, CY0 - 0.008, CZ1 - 0.3), mat="paint_black", bev=0.004)
for k, key in enumerate(("gauge", "gauge2", "gauge3")):
    canopy.decal(key, c=(CX - 0.08 + k * 0.2, CY0 - 0.019, CZ1 - 0.3), n=(0, -1, 0), w=0.15)
canopy.box((0.6, 0.006, 0.3), c=(CX + 0.12, CY0 - 0.024, CZ1 - 0.3), mat="glass", bev=0)
canopy.box((0.05, 0.03, 0.05), c=(CX + 0.5, CY0 - 0.015, CZ1 - 0.3), mat="paint_red", bev=0)       # stop button
canopy.decal("danger_air", c=(CX - 0.38, CY0 - 0.004, CZ1 - 0.36), n=(0, -1, 0), w=0.22)
canopy.decal("cfm", c=(CX + 0.12, CY0 - 0.004, CZ0 + 0.2), n=(0, -1, 0), w=0.4)
for k in range(2):                                                                                 # service valves
    vx = AIR_OUT.x - 0.0 + k * 0.18 if k else AIR_OUT.x
    canopy.cyl(0.03, 0.1, c=(vx, CY0 - 0.04, AIR_OUT.z), axis="Y", mat="brass", sides=10, bev=0)
    canopy.box((0.12, 0.016, 0.02), c=(vx + 0.05, CY0 - 0.09, AIR_OUT.z + 0.03), mat="paint_red", bev=0)
# exhaust stack + rain cap, lifting bail, fuel cap
canopy.cyl(0.045, 0.32, c=(CX - 0.35, CY1 - 0.35, CZ1 + 0.14), mat="steel_dark", sides=12, bev=0)
canopy.box((0.1, 0.012, 0.09), c=(CX - 0.35, CY1 - 0.35, CZ1 + 0.33), rot=(-25, 0, 0), mat="steel_dark", bev=0)
canopy.decal("caution_hot", c=(CX - 0.35, CY1 - 0.62, CZ1 + 0.003), n=(0, 0, 1), up=(0, -1, 0), w=0.2)
for sy in (1, -1):
    canopy.rod((CX - 0.18, cy + sy * 0.18, CZ1 - 0.01), (CX - 0.18, cy + sy * 0.18, CZ1 + 0.28), 0.022,
               mat="galvanized", sides=10)
    canopy.rod((CX + 0.18, cy + sy * 0.18, CZ1 - 0.01), (CX + 0.18, cy + sy * 0.18, CZ1 + 0.28), 0.022,
               mat="galvanized", sides=10)
for sx in (-0.18, 0.18):
    canopy.rod((CX + sx, cy - 0.18, CZ1 + 0.28), (CX + sx, cy + 0.18, CZ1 + 0.28), 0.022, mat="galvanized", sides=10)
canopy.rod((CX - 0.18, cy, CZ1 + 0.28), (CX + 0.18, cy, CZ1 + 0.28), 0.03, mat="galvanized", sides=10)
lib.lift_eye(canopy, (CX, cy, CZ1 + 0.3), (0, 0, 1), r=0.045, mat="galvanized")
canopy.decal("lift", c=(CX, cy + 0.32, CZ1 + 0.002), n=(0, 0, 1), up=(0, 1, 0), w=0.22)
canopy.cyl(0.045, 0.03, c=(CX + 0.4, CY1 - 0.4, CZ1 + 0.01), mat="plastic_black", sides=12, bev=0)

# cooling fan behind the rear grille (animated spin)
FAN_C = V((CX, CY1 - 0.1, (CZ0 + CZ1) / 2))
fan = m.part("fan", origin=FAN_C)
with fan.at(FAN_C, rot=(90, 0, 0)):
    fan.cyl(0.07, 0.08, mat="steel_dark", sides=12, bev=0)
    for k in range(6):
        with fan.at((0, 0, 0), rot=(0, 0, k * 60)):
            fan.box((0.07, 0.3, 0.008), c=(0, 0.2, 0), rot=(0, 28, 0), mat="paint_black", bev=0)
canopy.lathe([(0.37, -0.05), (0.39, -0.05), (0.39, 0.05), (0.37, 0.05)], c=FAN_C, rot=(90, 0, 0), mat="paint_black",
             sides=24, cap0=False, cap1=False)

# ================================================================== work light on a tripod -> light_0
LS = V((1.25, -2.15, 0.0))
for k in range(3):
    a = k / 3 * math.tau + 0.4
    body.rod(LS + V((math.cos(a) * 0.42, math.sin(a) * 0.42, 0.0)), LS + V((0, 0, 0.75)), 0.014, mat="steel_dark",
             sides=6)
    body.box((0.05, 0.05, 0.015), c=LS + V((math.cos(a) * 0.42, math.sin(a) * 0.42, 0.007)), mat="rubber", bev=0)
body.cyl(0.022, 1.25, c=LS + V((0, 0, 1.22)), mat="aluminium", sides=8, bev=0)
body.cyl(0.03, 0.06, c=LS + V((0, 0, 0.78)), mat="steel_dark", sides=8, bev=0)
LDIR = V((-0.35, -1, -0.45)).normalized()
LC = LS + V((0, 0, 1.92))
body.box((0.24, 0.02, 0.03), c=LC + V((0, 0, -0.07)), mat="steel_dark", bev=0)
lens = lib.work_light(body, LC, LDIR, kind="bar", r=0.11)
body.path([LS + V((0, 0, 1.6)), LS + V((0.05, 0.03, 1.2)), LS + V((0.1, 0.05, 0.6)), LS + V((0.25, 0.2, 0.03)),
           V((1.0, -1.0, 0.02)), V((0.75, 0.2, 0.02)), V((0.2, 1.0, 0.02)), V((-0.2, 1.1, 0.25)),
           V((-0.2, 1.2, 0.6))], r=0.011, mat="cable", sides=6, res=4)

# ================================================================== props: spare steels, bit tin, oil can
for k in range(3):
    y0 = -1.6 + k * 0.05
    p0 = V((-0.75, y0, 0.016 + (0.028 if k == 2 else 0)))
    body.rod(p0, p0 + V((0.12, -1.6, 0.0)), 0.014, mat="steel", sides=6, bev=0)
    body.cyl(0.02, 0.025, c=p0 + V((0.12, -1.6, 0.0)) * 1.0, q=aim(V((0.12, -1.6, 0))), mat="steel_dark", sides=8,
             bev=0)
body.cyl(0.1, 0.16, c=(-0.95, -2.0, 0.08), mat="paint_red", sides=14, bev=0.006)                  # oil can
body.cyl(0.02, 0.06, c=(-0.95, -2.03, 0.19), mat="steel_dark", sides=8, bev=0)
body.box((0.3, 0.2, 0.14), c=(-0.4, -2.3, 0.07), mat="paint_red", bev=0.01)                       # bit box
body.box((0.31, 0.21, 0.02), c=(-0.4, -2.3, 0.15), mat="paint_red", bev=0.004)
body.rod((-0.48, -2.3, 0.165), (-0.32, -2.3, 0.165), 0.008, mat="steel", sides=6)

# ================================================================== empties
m.empty("fx_work", TIP + DIR * 0.01)
m.empty("fx_ore", V((TIP.x, TIP.y + 0.15, 0.15)))
m.empty("light_0", lens, beam=LDIR)
m.empty("op", (-0.22, -0.52, 0.0))
m.empty("snd", (CX, cy, 0.9))

lib.tick("build parts")
m.finish(rays=20, strength=1.15, low=0.4, noise_amt=0.2)
lib.tick("finish+grime")

# ================================================================== animation
ANIM = ["drill", "steel", "leg_outer", "comp_canopy", "fan"]
NF = 60
JIT = [(rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1)) for _ in range(NF)]
DR0 = m.objs["drill"].location.copy()
LO0 = m.objs["leg_outer"].location.copy()
CA0 = m.objs["comp_canopy"].location.copy()
RIGHT = QD @ V((1, 0, 0))
UPV = QD @ V((0, 1, 0))


def work(t):
    f = int(round(t * NF)) % NF
    jx, jy, jz = JIT[f]
    blow = 0.004 if f % 2 else -0.003                       # percussion: rattles along the steel axis
    drill_off = DIR * blow + RIGHT * 0.0012 * jx + UPV * 0.0012 * jy
    pump = 0.006 * math.sin(math.tau * 4 * t)
    return {
        "drill": {"loc": DR0 + drill_off},
        "steel": {"q": Quaternion(DIR, math.tau * 6 * t)},
        "leg_outer": {"loc": LO0 + drill_off - LEGD * pump},
        "comp_canopy": {"loc": CA0 + V((0.0015 * jx, 0.001 * jz, 0.0018 * (1 if f % 2 else -1)))},
        "fan": {"q": Quaternion((0, 1, 0), math.tau * 3 * t)},
    }


m.clip("Work", 2.0, work, ANIM)
m.clip("Idle", 2.0, None, ANIM)
lib.tick("clips")
tris, size = m.report()
if stem:
    m.export(stem)
    lib.tick("export")
if "--no-render" not in flags:
    views = [
        ("front3q", (3.6, -6.4, 2.6), (0.0, -1.2, 0.9), 32),
        ("side", (-8.6, 0.0, 1.6), (0, 0.0, 0.8), 36),
        ("rear3q", (-4.6, 6.0, 2.8), (-0.4, 1.0, 0.8), 32),
        ("close", (1.6, -3.0, 1.75), (0.1, -1.6, 1.25), 34),
    ]
    if "--one" in flags:
        views = views[:1]
    m.render(views)
