"""Ironside LH-410 LHD mucker (MOTHERLODE machines-A, depth 2 / tier 2).

Modeled on a Sandvik LH410 / Epiroc ST14 underground loader: articulated centre hinge, big front bucket on lift
arms with a single-cylinder Z-bar tilt linkage, side operator cab under a ROPS/FOPS canopy, rear engine bay with
grilles, radiator and exhaust purifier, four deep-lug tyres. The real 10.2 m machine is shortened to 7.4 m (wheelbase
and overhangs compressed, height/width/tyres kept) so it fits the alcove.

    systemd-run --user --scope -q -p MemoryMax=3G -p MemorySwapMax=0 \
        bl assets/machines_a/lhd.py -- public/models/machines/lhd [--no-render] [--one]
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
from lib import V, aim  # noqa: E402
from mathutils import Quaternion  # noqa: E402

stem, flags = lib.args()
m = lib.Machine("lhd")

# ------------------------------------------------------------------ decals
A_ = m.atlas
A_.add("logo", 1024, 256, lib.svg_logo(1024, 256, "IRONSIDE", wear=0.45))
A_.add("logo_plain", 1024, 200, lib.svg_logo(1024, 200, "IRONSIDE", kind="plain", wear=0.6, seed=31))
A_.add("model", 640, 200, lib.svg_text("LH-410", font="Saira Stencil One", wear=0.35), fit=True)
A_.add("unit", 360, 260, lib.svg_text("12", font="Saira Stencil One", wear=0.4, seed=5), fit=True)
A_.add("hazard", 1024, 128, lib.svg_hazard(1024, 128, band=64, wear=0.45))
A_.add("chev", 1024, 128, lib.svg_chevron(1024, 128, wear=0.4))
A_.add("danger_crush", 512, 400, lib.svg_panel(512, 400, "DANGER", ["CRUSH ZONE", "STAY CLEAR OF", "ARTICULATION"]))
A_.add("warn_hot", 512, 360, lib.svg_panel(512, 360, "WARNING", ["HOT SURFACE", "DO NOT TOUCH"], seed=12))
A_.add("caution_arm", 512, 360, lib.svg_panel(512, 360, "CAUTION", ["NEVER WORK UNDER", "RAISED BUCKET"], seed=13))
A_.add("plate", 600, 360, lib.svg_plate(600, 360, ["MODEL   LH-410 LHD", "SERIAL  LH410-2281", "BUCKET  4.6 M3  10 T",
                                                   "ENGINE  220 KW TIER 4F", "BUILT   2021 GULCH WORKS"],
                                         title="IRONSIDE MINING MACHINERY"))
A_.add("iso", 256, 230, lib.svg_iso(256, 230))
A_.add("iso_crush", 256, 230, lib.svg_iso(256, 230, "crush"))
A_.add("diesel", 400, 110, lib.svg_text("DIESEL", font="Barlow Condensed Black", wear=0.4), fit=True)
A_.add("nostep", 400, 110, lib.svg_text("NO STEP", font="Barlow Condensed Black", wear=0.45), fit=True)
A_.add("gauge", 256, 256, lib.svg_gauge(256, 256, vmax=4000, unit="RPM", label="ENGINE", red=0.75))
A_.add("gauge2", 256, 256, lib.svg_gauge(256, 256, vmax=120, unit="C", label="COOLANT", red=0.85, seed=29))
A_.build()

# ------------------------------------------------------------------ key geometry (Blender, front = -Y)
H = V((0, -0.1, 0.0))          # articulation hinge (vertical axis)
WR, WW = 0.68, 0.55            # tyre crown radius (+0.05 lugs), width
WZ = WR + 0.05                 # axle height
YF, YRA = -1.5, 1.4            # front / rear axle y
XW = 1.03                      # wheel centre |x|
A = V((0, -0.6, 1.45))         # lift-arm pivot (x = +-XA)
PB = V((0, -2.36, 0.40))       # bucket pivot on the arm ends (rest: bucket flat on the floor)
R0 = V((0, -1.58, 1.08))       # rocker pivot on the arm crossmember
C0 = R0 + V((0, 0.12, 0.40))   # rocker top: tilt-cylinder rod eye
D0 = R0 + V((0, -0.10, -0.33))  # rocker bottom: link
E0 = V((0, -2.42, 0.98))       # link hinge on the bucket back
B0 = V((0, -0.45, 1.55))       # tilt-cylinder base on the front frame
LINK = (E0 - D0).length
XA = 0.56                      # arm plane |x|   (lateral stack: frame 0.30, lift cyl 0.40, arms 0.56, hubs 0.64+)
XL = 0.40                      # lift cylinder |x|
LB = [V((s * XL, -0.62, 0.45)) for s in (1, -1)]      # lift-cylinder bases (front frame)
LE = [V((s * XL, -1.55, 0.80)) for s in (1, -1)]      # lift-cylinder rod eyes (on the arms)
ROOF = 2.2


def mxp(pts, s):
    return [(s * x, y) for x, y in pts]


def thick(pts, t):
    """Polyline (2D) -> closed polygon of thickness t (offset to the left of travel)."""
    left, right = [], []
    for i, p in enumerate(pts):
        a, b = V(pts[max(i - 1, 0)]), V(pts[min(i + 1, len(pts) - 1)])
        d = (b - a).normalized()
        nrm = V((-d.y, d.x))
        left.append(tuple(V(p) + nrm * t / 2))
        right.append(tuple(V(p) - nrm * t / 2))
    return left + right[::-1]


body = m.part("lhd_body")

# ================================================================== rear frame, hinge, axle
for s in (1, -1):
    body.plate([(0.05, 0.36), (0.05, 1.02), (3.3, 1.02), (3.3, 0.36)], 0.06, "YZ", at=s * 0.5, mat="paint_yellow",
               bev=0.012)
body.box((0.94, 3.2, 0.06), c=(0, 1.68, 0.39), mat="paint_yellow", bev=0.01)                   # belly plate
for zz in (1.27, 0.33):                                                                          # hinge plates
    body.box((0.42, 0.42, 0.08), c=(0, 0.06, zz), mat="paint_yellow", bev=0.012)
    body.cyl(0.065, 0.16, c=(H.x, H.y, zz), mat="steel_dark", sides=12, bev=0.006)
    body.cyl(0.085, 0.02, c=(H.x, H.y, zz + 0.09), mat="steel_dark", sides=12, bev=0)
body.cyl(0.12, 1.3, c=(0, YRA, WZ), axis="X", mat="steel_dark", sides=16, bev=0.01, segs=1)       # rear axle
body.sphere(0.25, c=(0, YRA, WZ), mat="steel_dark", seg=16, rings=8, scale=(1, 1.15, 1))
for s in (1, -1):
    body.lathe([(0.0, 0), (0.2, 0), (0.22, 0.03), (0.22, 0.09), (0.17, 0.12), (0, 0.12)], c=(s * 0.64, YRA, WZ),
               rot=(0, 90 * s, 0), mat="steel_dark", sides=16)
# ================================================================== engine hood, radiator, counterweight
body.box((1.44, 2.45, 0.62), c=(0, 1.97, 1.3), mat="paint_yellow", bev=0.06)                    # hood
body.box((1.5, 2.48, 0.04), c=(0, 1.97, 1.0), mat="paint_yellow", bev=0.01)                     # hood sill
lib.cover(body, (0, 1.35, 1.61), (0, 0, 1), 1.1, 0.7, t=0.014, pitch=0.16)
body.grille((0.12, 2.15, 1.62), 0.7, 0.42, 6, rot=(-90, 0, 0), depth=0.03, mat="paint_yellow", slat_mat="steel_dark")
for s in (1, -1):
    for yy in (1.1, 2.0):                                                                        # hinges/latches
        body.box((0.03, 0.1, 0.05), c=(s * 0.728, yy, 1.52), mat="steel_dark", bev=0)
    body.handrail([(s * 0.66, 1.0, 1.61), (s * 0.66, 1.0, 1.73), (s * 0.66, 2.6, 1.73), (s * 0.66, 2.6, 1.61)],
                  r=0.016)
    body.grille((s * 0.856, 3.33, 1.07), 0.26, 0.8, 7, rot=(0, 0, 90 * s), depth=0.03, mat="paint_yellow",
                slat_mat="steel_dark")
body.mesh_panel((0, 2.82, 1.615), 1.0, 0.5, cell=0.06, wire=0.007, rot=(90, 0, 0))
body.box((1.7, 0.33, 1.06), c=(0, 3.33, 1.07), mat="paint_yellow", bev=0.03)                   # radiator housing
body.grille((0, 3.5, 1.1), 1.42, 0.78, 9, rot=(0, 0, 180), depth=0.04, mat="paint_yellow", slat_mat="steel_dark")
for k in range(7):                                                                                # guard bars
    body.box((0.035, 0.035, 0.82), c=(-0.6 + k * 0.2, 3.55, 1.1), mat="paint_yellow", bev=0)
body.box((1.5, 0.05, 0.05), c=(0, 3.55, 1.53), mat="paint_yellow", bev=0)
body.box((1.5, 0.05, 0.05), c=(0, 3.55, 0.68), mat="paint_yellow", bev=0)
body.plate([(3.05, 0.28), (3.55, 0.28), (3.58, 0.38), (3.58, 0.6), (3.47, 0.68), (3.05, 0.68)], 2.0, "YZ", at=0,
           mat="paint_yellow", bev=0.02)                                                         # counterweight
body.box((0.26, 0.06, 0.18), c=(0, 3.6, 0.46), mat="steel_dark", bev=0.01)                      # tow hitch
body.cyl(0.035, 0.24, c=(0, 3.6, 0.46), mat="steel", sides=10, bev=0.004)
# exhaust purifier + air cleaner on the hood
body.cyl(0.15, 0.78, c=(-0.48, 2.05, 1.84), axis="Y", mat="steel", sides=16, bev=0.012, segs=1)
for yy in (1.78, 2.32):
    body.box((0.36, 0.08, 0.12), c=(-0.48, yy, 1.66), mat="steel_dark", bev=0.008)
body.lathe([(0.15, 0), (0.12, 0.06), (0.06, 0.1), (0, 0.11)], c=(-0.48, 2.44, 1.84), rot=(-90, 0, 0), mat="steel",
           sides=16, cap0=False)
body.path([(-0.48, 2.52, 1.84), (-0.48, 2.7, 1.84), (-0.5, 2.82, 1.95), (-0.52, 2.86, 2.05)], r=0.05, mat="steel",
          sides=10, res=4)
body.path([(-0.48, 1.62, 1.84), (-0.48, 1.5, 1.8), (-0.45, 1.42, 1.68), (-0.45, 1.42, 1.6)], r=0.055,
          mat="steel_dark", sides=10, res=4)
body.cyl(0.13, 0.34, c=(0.52, 2.5, 1.79), mat="paint_black", sides=16, bev=0.01)
body.lathe([(0.15, 0), (0.15, 0.04), (0.08, 0.08), (0, 0.09)], c=(0.52, 2.5, 1.96), mat="paint_black", sides=16,
           cap0=True, cap1=False)
body.cyl(0.05, 0.2, c=(0.52, 2.2, 1.7), axis="Y", mat="rubber", sides=10, bev=0)
# rear fenders + fuel tank + steps
for s in (1, -1):
    body.box((0.58, 1.3, 0.035), c=(s * 1.04, YRA, 1.5), mat="paint_yellow", bev=0.008)
    for sy in (1, -1):
        body.box((0.58, 0.32, 0.035), c=(s * 1.04, YRA + sy * 0.76, 1.39), rot=(sy * -42, 0, 0), mat="paint_yellow",
                 bev=0.008)
    body.box((0.25, 0.05, 0.06), c=(s * 0.86, YRA - 0.5, 1.47), mat="paint_yellow", bev=0)
    body.box((0.25, 0.05, 0.06), c=(s * 0.86, YRA + 0.5, 1.47), mat="paint_yellow", bev=0)
body.box((0.72, 0.95, 0.78), c=(-0.91, 0.12, 0.96), mat="paint_yellow", bev=0.035)             # fuel tank
body.cyl(0.06, 0.06, c=(-0.75, -0.15, 1.38), mat="steel_dark", sides=12)
body.cyl(0.075, 0.035, c=(-0.75, -0.15, 1.425), mat="plastic_black", sides=12, bev=0.006)
body.box((0.02, 0.05, 0.4), c=(-1.275, 0.3, 0.96), mat="glass_dark", bev=0)
for zz in (0.42, 0.72):
    lib.step_plate(body, (-1.2, 0.1, zz), 0.2, 0.32)
for yy in (-0.05, 0.25):
    body.box((0.16, 0.03, 0.4), c=(-1.2, yy, 0.6), mat="paint_yellow", bev=0)
# ================================================================== cab (left side) with ROPS/FOPS canopy
body.box((0.84, 1.26, 0.06), c=(0.91, 0.0, 0.95), mat="paint_yellow", bev=0.01)                 # cab floor
body.box((0.8, 0.5, 0.45), c=(0.91, 0.0, 0.7), mat="paint_yellow", bev=0.015)                   # cab mount
POSTS = [(0.55, -0.58), (1.27, -0.58), (0.55, 0.58), (1.27, 0.58)]
for x, y in POSTS:
    body.box((0.1, 0.1, ROOF - 0.95), c=(x, y, (ROOF + 0.95) / 2), mat="paint_yellow", bev=0.012)
body.box((0.96, 1.4, 0.07), c=(0.91, 0.0, ROOF + 0.035), mat="paint_yellow", bev=0.015)        # FOPS roof
for (cx_, cy_, sx_, sy_) in ((0.91, -0.71, 1.0, 0.05), (0.91, 0.71, 1.0, 0.05), (0.42, 0.0, 0.05, 1.46),
                             (1.4, 0.0, 0.05, 1.46)):
    body.box((sx_, sy_, 0.1), c=(cx_, cy_, ROOF + 0.05), mat="paint_yellow", bev=0.008)
body.box((0.04, 1.16, 0.4), c=(1.28, 0.0, 1.17), mat="paint_yellow", bev=0.006)                 # outer lower wall
body.box((0.66, 0.04, 0.5), c=(0.91, -0.58, 1.22), mat="paint_yellow", bev=0.006)               # dash wall
body.box((0.66, 0.04, 0.65), c=(0.91, 0.58, 1.3), mat="paint_yellow", bev=0.006)                # rear wall
body.box((0.04, 1.16, ROOF - 0.98), c=(0.55, 0.0, (ROOF + 0.98) / 2), mat="paint_yellow", bev=0.006)  # inner wall
body.box((0.62, 0.012, 0.7), c=(0.91, -0.585, 1.83), mat="glass", bev=0)                          # windscreen
body.box((0.012, 1.06, 0.8), c=(1.285, 0.0, 1.78), mat="glass", bev=0)                            # side window
body.box((0.62, 0.012, 0.56), c=(0.91, 0.585, 1.9), mat="glass", bev=0)                           # rear window
for z in (1.42, 2.17):
    body.box((0.03, 1.16, 0.04), c=(1.29, 0.0, z), mat="paint_black", bev=0)
body.box((0.03, 0.04, 0.8), c=(1.29, 0.0, 1.81), mat="paint_black", bev=0)
body.box((0.42, 0.42, 0.2), c=(0.91, 0.1, 1.08), mat="steel_dark", bev=0.01)                     # seat
body.box((0.48, 0.46, 0.1), c=(0.91, 0.08, 1.23), mat="plastic_black", bev=0.035)
body.box((0.48, 0.1, 0.55), c=(0.91, 0.33, 1.55), rot=(-10, 0, 0), mat="plastic_black", bev=0.035)
for s in (1, -1):                                                                                # armrests + sticks
    body.box((0.08, 0.36, 0.06), c=(0.91 + s * 0.29, 0.05, 1.42), mat="plastic_black", bev=0.012)
    body.rod((0.91 + s * 0.29, -0.06, 1.45), (0.91 + s * 0.29, -0.07, 1.58), 0.012, mat="plastic_black", sides=6)
    body.sphere(0.028, c=(0.91 + s * 0.29, -0.07, 1.6), mat="plastic_black", seg=8, rings=5)
with body.at((0.91, -0.5, 1.5), rot=(-35, 0, 0)):
    body.box((0.6, 0.2, 0.05), mat="steel_dark", bev=0.008)
    body.decal("gauge", c=(-0.15, 0.0, 0.026), n=(0, 0, 1), up=(0, -1, 0), w=0.11)
    body.decal("gauge2", c=(0.0, 0.0, 0.026), n=(0, 0, 1), up=(0, -1, 0), w=0.11)
    body.box((0.12, 0.08, 0.01), c=(0.17, 0.0, 0.03), mat="glass_dark", bev=0)
body.cyl(0.05, 0.04, c=(0.62, 0.45, ROOF + 0.09), mat="paint_black", sides=12, bev=0)           # beacon
body.sphere(0.045, c=(0.62, 0.45, ROOF + 0.13), mat="emit_amber", seg=12, rings=6, scale=(1, 1, 1.1))
for (x, y) in ((1.33, -0.52), (1.33, 0.52)):                                                     # grab rails
    body.handrail([(x, y, 1.15), (x + 0.05, y, 1.2), (x + 0.05, y, 1.95), (x, y, 2.0)], r=0.016)
for zz in (0.42, 0.72):                                                                          # cab steps
    lib.step_plate(body, (1.2, 0.0, zz), 0.2, 0.36)
for yy in (-0.2, 0.2):
    body.box((0.16, 0.03, 0.45), c=(1.2, yy, 0.62), mat="paint_yellow", bev=0)
# hoses across the articulation (static loops)
for k in range(3):
    body.hose((0.12 + k * 0.08, 0.15, 1.02), (0, -1, 0.2), (0.12 + k * 0.08, -0.35, 1.0), (0, -1, -0.2), r=0.018,
              mat="rubber", sides=8, sag=0.08, k=0.5)
# rear lights -> light_2, light_3; tail lamps
LIGHTS = []
for s in (1, -1):
    d = V((s * 0.06, 1, -0.12)).normalized()
    lens = lib.work_light(body, (s * 0.72, 3.53, 1.44), d, kind="round", r=0.075)
    body.box((0.1, 0.04, 0.06), c=(s * 0.6, 3.6, 0.62), mat="paint_black", bev=0)
    body.box((0.08, 0.01, 0.04), c=(s * 0.6, 3.622, 0.62), mat="emit_red", bev=0)
    LIGHTS.append((lens, d))
# body decals
for s in (1, -1):
    body.decal("logo", c=(s * 0.721, 2.66, 1.3), n=(s, 0, 0), w=0.95)
    body.decal("danger_crush", c=(s * 0.531, 0.2, 0.72), n=(s, 0, 0), w=0.26)
    body.decal("iso_crush", c=(s * 0.531, 0.5, 0.78), n=(s, 0, 0), w=0.12)
    body.decal("nostep", c=(s * 1.04, YRA, 1.519), n=(0, 0, 1), up=(0, 1, 0), w=0.24)
body.decal("model", c=(0, 3.586, 0.6), n=(0, 1, 0), w=0.4)
body.decal("chev", c=(-0.62, 3.586, 0.48), n=(0, 1, 0), w=0.62, h=0.08)
body.decal("chev", c=(0.62, 3.586, 0.48), n=(0, 1, 0), w=0.62, h=0.08)
body.decal("unit", c=(0.91, -0.737, ROOF + 0.05), n=(0, -1, 0), w=0.12)
body.decal("unit", c=(0.0, 3.501, 1.565), n=(0, 1, 0), w=0.14)
body.decal("model", c=(1.305, 0.0, 1.14), n=(1, 0, 0), w=0.36)
body.decal("warn_hot", c=(-0.721, 2.18, 1.52), n=(-1, 0, 0), w=0.16)
body.decal("diesel", c=(-0.91, 0.25, 1.351), n=(0, 0, 1), up=(0, 1, 0), w=0.22)
body.decal("plate", c=(0.553 + 0.024, 0.2, 1.62), n=(1, 0, 0), w=0.22)
body.decal("hazard", c=(0.0, 3.501, 0.61), n=(0, 1, 0), w=1.2, h=0.05)

# ================================================================== rear wheels (animated: creep)
WHEELS = {}
for nm, s, yy, parent in (("wheel_rl", 1, YRA, None), ("wheel_rr", -1, YRA, None)):
    w = m.part(nm, origin=(s * XW, yy, WZ))
    lib.wheel(w, (s * XW, yy, WZ), side=s, R=WR, W=WW)
    WHEELS[nm] = None

# ================================================================== front frame (animated: articulation sway)
ff = m.part("front_frame", origin=H)
for s in (1, -1):
    ff.plate([(-0.14, 0.34), (-0.14, 1.12), (-0.4, 1.22), (-1.05, 1.0), (-2.05, 0.92), (-2.26, 0.78),
              (-2.26, 0.42), (-2.0, 0.32), (-0.5, 0.32)], 0.06, "YZ", at=s * 0.30, mat="paint_yellow", bev=0.012)
    for xx in (0.49, 0.63):                                                                     # arm towers
        ff.plate([(-0.3, 1.0), (-0.42, 1.62), (-0.78, 1.62), (-0.95, 1.1), (-0.95, 0.88), (-0.3, 0.88)], 0.025,
                 "YZ", at=s * xx, mat="paint_yellow", bev=0.006)
    ff.box((0.36, 0.62, 0.05), c=(s * 0.47, -0.62, 0.89), mat="paint_yellow", bev=0.008)
    ff.cyl(0.07, 0.2, c=(s * XA, A.y, A.z), axis="X", mat="steel_dark", sides=12, bev=0.006)
    ff.cyl(0.09, 0.015, c=(s * 0.65, A.y, A.z), axis="X", mat="steel_dark", sides=12, bev=0)
    for dx in (-0.055, 0.055):                                                                  # lift cyl clevis
        ff.box((0.025, 0.16, 0.16), c=(s * XL + dx, LB[0].y, LB[0].z), mat="paint_yellow", bev=0.004)
    ff.cyl(0.03, 0.15, c=(s * XL, LB[0].y, LB[0].z), axis="X", mat="steel_dark", sides=8, bev=0)
    ff.box((0.1, 0.1, 0.12), c=(s * 0.36, -0.5, 0.78), mat="paint_yellow", bev=0.006)          # steering eye
    # fenders on struts (outboard of the arms)
    ff.box((0.58, 1.3, 0.035), c=(s * 1.04, YF, 1.5), mat="paint_yellow", bev=0.008)
    for sy in (1, -1):
        ff.box((0.58, 0.32, 0.035), c=(s * 1.04, YF + sy * 0.76, 1.39), rot=(sy * -42, 0, 0), mat="paint_yellow",
               bev=0.008)
        ff.rod((s * 0.735, YF + sy * 0.35, 0.82), (s * 0.78, YF + sy * 0.35, 1.49), 0.022, mat="paint_yellow",
               sides=8)
    ff.decal("nostep", c=(s * 1.04, YF, 1.519), n=(0, 0, 1), up=(0, 1, 0), w=0.24)
for zz in (1.15, 0.45):                                                                          # hinge plates
    ff.box((0.3, 0.36, 0.07), c=(0, -0.2, zz), mat="paint_yellow", bev=0.01)
ff.box((0.54, 1.95, 0.08), c=(0, -1.2, 0.37), mat="paint_yellow", bev=0.01)                     # belly
ff.box((0.54, 0.5, 0.06), c=(0, -0.55, 1.17), mat="paint_yellow", bev=0.01)                     # top deck
for dx in (-0.08, 0.08):                                                                        # tilt cyl base
    ff.box((0.03, 0.2, 0.3), c=(dx, B0.y, B0.z - 0.12), mat="paint_yellow", bev=0.006)
ff.cyl(0.035, 0.22, c=B0, axis="X", mat="steel_dark", sides=8, bev=0)
ff.box((1.0, 0.1, 0.4), c=(0, -2.25, 0.62), mat="paint_yellow", bev=0.015)                      # bumper
ff.decal("hazard", c=(0, -2.301, 0.62), n=(0, -1, 0), w=0.94, h=0.12)
ff.cyl(0.12, 1.3, c=(0, YF, WZ), axis="X", mat="steel_dark", sides=16, bev=0.01, segs=1)         # front axle
ff.sphere(0.25, c=(0, YF, WZ), mat="steel_dark", seg=16, rings=8, scale=(1, 1.15, 1))
for s in (1, -1):
    ff.lathe([(0.0, 0), (0.2, 0), (0.22, 0.03), (0.22, 0.09), (0.17, 0.12), (0, 0.12)], c=(s * 0.64, YF, WZ),
             rot=(0, 90 * s, 0), mat="steel_dark", sides=16)
    d = V((s * 0.05, -1, -0.12)).normalized()
    ff.box((0.06, 0.08, 0.12), c=(s * 0.63, -0.68, 1.66), mat="paint_yellow", bev=0)
    lens = lib.work_light(ff, (s * 0.63, -0.74, 1.76), d, kind="round", r=0.075)
    LIGHTS.insert(0 if s > 0 else 1, (lens, d, "front_frame"))
ff.hose((0.2, -0.3, 1.2), (0, -1, 0), (0.0, -0.62, 1.47), (0, -1, 0.3), r=0.016, mat="rubber", sides=8, k=0.5)
ff.hose((-0.2, -0.3, 1.2), (0, -1, 0), (-0.05, -0.62, 1.47), (0, -1, 0.3), r=0.016, mat="rubber", sides=8, k=0.5)
for s in (1, -1):
    ff.decal("caution_arm", c=(s * 0.331, -1.75, 0.62), n=(s, 0, 0), w=0.22)

for nm, s in (("wheel_fl", 1), ("wheel_fr", -1)):
    w = m.part(nm, origin=(s * XW, YF, WZ), parent="front_frame")
    lib.wheel(w, (s * XW, YF, WZ), side=s, R=WR, W=WW)

# ================================================================== lift arms (animated: lift)
arms = m.part("lift_arms", origin=A, parent="front_frame")
u = (PB - A).normalized()
nu = V((0, -u.z, u.y))           # perpendicular, pointing up
if nu.z < 0:
    nu = -nu


def arm_pts():
    top, bot = [], []
    for i in range(7):
        t = i / 6
        p = A.lerp(PB, t)
        d = 0.17 - 0.05 * t
        bulge = 0.09 * math.sin(math.pi * t)
        top.append(p + nu * (d + bulge))
        bot.append(p - nu * (d - bulge))
    pts = [(p.y, p.z) for p in top]
    for k in range(1, 6):        # front round end around PB
        a = math.atan2(nu.z, nu.y) - math.pi * k / 6
        pts.append((PB.y + 0.11 * math.cos(a), PB.z + 0.11 * math.sin(a)))
    pts += [(p.y, p.z) for p in reversed(bot)]
    for k in range(1, 6):        # rear round end around A
        a = math.atan2(-nu.z, -nu.y) - math.pi * k / 6
        pts.append((A.y + 0.17 * math.cos(a), A.z + 0.17 * math.sin(a)))
    return pts


AP = arm_pts()
CM = A.lerp(PB, 0.52)
cm_ang = math.degrees(math.atan2(-u.z, -u.y))
for s in (1, -1):
    arms.plate(AP, 0.1, "YZ", at=s * XA, mat="paint_yellow", bev=0.018)
    arms.cyl(0.13, 0.1, c=(s * XA, A.y, A.z), axis="X", mat="steel_dark", sides=16, bev=0.008, segs=1)
    arms.cyl(0.11, 0.1, c=(s * XA, PB.y, PB.z), axis="X", mat="steel_dark", sides=16, bev=0.008, segs=1)
    e = LE[0 if s > 0 else 1]
    for dx in (-0.05, 0.05):                                                                     # lift cyl lugs
        arms.plate([(e.y + 0.1, e.z - 0.06), (e.y - 0.1, e.z - 0.06), (e.y - 0.08, e.z + 0.2), (e.y + 0.12, e.z + 0.2)],
                   0.025, "YZ", at=s * XL + dx, mat="paint_yellow", bev=0.004)
    arms.box((0.16, 0.24, 0.05), c=(s * (XL + XA) / 2, e.y + 0.01, e.z + 0.2), mat="paint_yellow", bev=0.006)
    arms.cyl(0.03, 0.14, c=(s * XL, e.y, e.z), axis="X", mat="steel_dark", sides=8, bev=0)
    p0 = A.lerp(PB, 0.12) + V((s * (XA + 0.055), 0, 0)) + nu * 0.08
    p1 = A.lerp(PB, 0.82) + V((s * (XA + 0.055), 0, 0)) + nu * 0.05
    arms.hose(p0, u, p1, u, r=0.016, mat="rubber", sides=8, k=0.3, fittings=None)
with arms.at(CM, rot=(cm_ang, 0, 0)):
    arms.box((XA * 2 - 0.04, 0.22, 0.24), mat="paint_yellow", bev=0.02)                           # crossmember
for dx in (-0.1, 0.1):                                                                          # rocker clevis
    arms.plate([(R0.y + 0.1, R0.z - 0.25), (R0.y - 0.12, R0.z - 0.25), (R0.y - 0.06, R0.z + 0.06),
                (R0.y + 0.06, R0.z + 0.06)], 0.03, "YZ", at=dx, mat="paint_yellow", bev=0.005)
arms.cyl(0.04, 0.26, c=R0, axis="X", mat="steel_dark", sides=10, bev=0)

# rocker (bell crank, child of arms)
rocker = m.part("rocker", origin=R0, parent="lift_arms")
for dx in (-0.055, 0.055):
    rocker.plate(thick([(C0.y, C0.z), (R0.y, R0.z), (D0.y, D0.z)], 0.12), 0.035, "YZ", at=dx, mat="paint_yellow",
                 bev=0.006)
for p_ in (C0, R0, D0):
    rocker.cyl(0.055, 0.15, c=p_, axis="X", mat="steel_dark", sides=12, bev=0.004)

# bucket (child of arms)
bucket = m.part("bucket", origin=PB, parent="lift_arms")
side = [(-3.73, 0.02), (-3.6, 0.0), (-2.78, 0.0), (-2.58, 0.07), (-2.47, 0.28), (-2.44, 0.6), (-2.47, 1.02),
        (-2.62, 1.12), (-3.55, 0.62), (-3.73, 0.15)]
for s in (1, -1):
    bucket.plate(side, 0.05, "YZ", at=s * 1.235, mat="paint_yellow", bev=0.012)
    bucket.plate([(-3.72, 0.03), (-3.45, 0.0), (-3.4, 0.1), (-3.56, 0.6), (-3.72, 0.15)], 0.03, "YZ",
                 at=s * 1.272, mat="steel", bev=0.006)                                           # side cutter
    bucket.decal("logo_plain", c=(s * 1.262, -3.0, 0.42), n=(s, 0, 0), w=0.82)
bucket.box((2.42, 1.0, 0.05), c=(0, -3.2, 0.025), mat="paint_yellow", bev=0.01)                 # floor
bucket.box((2.36, 0.95, 0.012), c=(0, -3.2, 0.056), mat="steel", bev=0)                         # wear liner
bucket.plate(thick([(-2.8, 0.03), (-2.62, 0.08), (-2.52, 0.24), (-2.48, 0.5), (-2.49, 1.04)], 0.05), 2.42, "YZ",
             at=0, mat="paint_yellow", bev=0.01)                                                  # back
bucket.plate(thick([(-2.5, 1.05), (-2.7, 1.12), (-2.95, 1.1)], 0.05), 2.42, "YZ", at=0, mat="paint_yellow",
             bev=0.01)                                                                           # spill guard
bucket.plate([(-3.76, 0.015), (-3.58, 0.0), (-3.5, 0.075), (-3.64, 0.075)], 2.48, "YZ", at=0, mat="steel",
             bev=0.006)                                                                          # cutting lip
for k in range(8):                                                                              # lip shrouds
    x = -1.05 + k * 0.3
    bucket.box((0.16, 0.2, 0.05), c=(x, -3.58, 0.09), mat="steel_dark", bev=0.006)
    bucket.cyl(0.012, 0.01, c=(x, -3.58, 0.12), mat="steel_dark", sides=6, bev=0)
for x in (-0.8, 0.0, 0.8):                                                                      # wear bars
    bucket.box((0.1, 0.9, 0.03), c=(x, -3.15, -0.0), mat="steel", bev=0)
for s in (1, -1):                                                                               # pivot lugs
    for dx in (-0.075, 0.075):
        bucket.plate([(-2.52, 0.2), (-2.3, 0.28), (-2.28, 0.5), (-2.5, 0.62)], 0.03, "YZ", at=s * XA + dx,
                     mat="paint_yellow", bev=0.005)
for dx in (-0.08, 0.08):                                                                        # link lugs
    bucket.plate([(-2.52, 0.82), (-2.36, 0.88), (-2.36, 1.06), (-2.52, 1.12)], 0.03, "YZ", at=dx, mat="paint_yellow",
                 bev=0.005)
bucket.cyl(0.035, 0.22, c=E0, axis="X", mat="steel_dark", sides=8, bev=0)

# ================================================================== kinematics + animation
def rotx(p, piv, ang):
    q = Quaternion((1, 0, 0), ang)
    return piv + q @ (p - piv)


def solve_rocker(alpha, beta):
    """Rocker angle (about R, relative to arms) that keeps the link length; returns (gamma, C, D, E) in front-frame
    (machine-at-rest) coordinates."""
    E = rotx(rotx(E0, PB, beta), A, alpha)
    R = rotx(R0, A, alpha)

    def Dg(g):
        return rotx(rotx(D0, R0, g), A, alpha)

    def f(g):
        return (Dg(g) - E).length - LINK
    lo, hi = -1.2, 1.2
    best = min((abs(f(lo + (hi - lo) * i / 48)), lo + (hi - lo) * i / 48) for i in range(49))[1]
    a, b = best - 0.05, best + 0.05
    for _ in range(40):          # refine (bisection when bracketed, else golden-ish shrink toward best)
        fa, fb = f(a), f(b)
        if fa * fb < 0:
            mid = (a + b) / 2
            if f(mid) * fa <= 0:
                b = mid
            else:
                a = mid
        else:
            a, b = (a + best) / 2, (b + best) / 2
    g = (a + b) / 2
    return g, rotx(rotx(C0, R0, g), A, alpha), Dg(g), E, R


KEYS = [(0.0, -0.12, -0.35, 0.0), (0.13, 0.0, 0.06, 0.0), (0.42, -0.07, -0.45, 0.45), (0.65, -0.75, 0.15, 0.45),
        (0.75, -0.75, 0.15, 0.45), (1.0, -0.12, -0.35, 0.0)]


def pose_at(t):
    for (t0, a0, b0, w0), (t1, a1, b1, w1) in zip(KEYS, KEYS[1:]):
        if t0 <= t <= t1:
            k = lib.smooth((t - t0) / (t1 - t0))
            return lib.lerp(a0, a1, k), lib.lerp(b0, b1, k), lib.lerp(w0, w1, k)
    return KEYS[-1][1:]




def stroke(fn):
    vals = [fn(t / 60) for t in range(61)]
    return min(vals), max(vals)


LIFT_MM = stroke(lambda t: (rotx(LE[0], A, pose_at(t)[0]) - LB[0]).length)
TILT_MM = stroke(lambda t: (solve_rocker(*pose_at(t)[:2])[1] - B0).length)
print(f"[lhd] lift cyl {LIFT_MM[0]:.3f}..{LIFT_MM[1]:.3f} m  tilt cyl {TILT_MM[0]:.3f}..{TILT_MM[1]:.3f} m")


def fit(mm, eye=0.1, overlap=0.08):
    barrel = mm[0] - eye
    return barrel, mm[1] - barrel + overlap


# ================================================================== cylinders + link (front-frame children)
def cyl_pair(name, b, e, Lb, rb, Lr, rr, parent="front_frame", sides=12):
    d = e - b
    bar = m.part(f"{name}_barrel", origin=b, parent=parent)
    with bar.at(b, q=aim(d)):
        lib.hydraulic_barrel(bar, Lb, rb, sides=sides)
    rod = m.part(f"{name}_rod", origin=e, parent=parent)
    with rod.at(e, q=aim(-d)):
        lib.hydraulic_rod(rod, Lr, rr, sides=sides)


def world(p):  # authored machine coords; front-frame children are given in machine coords too (origin-relative)
    return p


LBR, LRD = fit(LIFT_MM)
TBR, TRD = fit(TILT_MM)
cyl_pair("lift_l", LB[0], LE[0], LBR, 0.075, LRD, 0.048)
cyl_pair("lift_r", LB[1], LE[1], LBR, 0.075, LRD, 0.048)
cyl_pair("tilt", B0, C0, TBR, 0.095, TRD, 0.06)
link = m.part("link", origin=D0, parent="front_frame")
dl = E0 - D0
with link.at(D0, q=aim(dl)):
    for dx in (-0.07, 0.07):
        link.box((0.03, 0.09, LINK), c=(dx, 0, LINK / 2), mat="paint_yellow", bev=0.006)
        link.cyl(0.05, 0.035, c=(dx, 0, 0), rot=(0, 90, 0), mat="steel_dark", sides=10, bev=0)
        link.cyl(0.05, 0.035, c=(dx, 0, LINK), rot=(0, 90, 0), mat="steel_dark", sides=10, bev=0)
# steering cylinders: rear frame -> front frame (root children, follow the articulation)
STEER = []
for s, suf in ((1, "l"), (-1, "r")):
    b, e = V((s * 0.4, 0.42, 0.78)), V((s * 0.4, -0.5, 0.78))
    d = e - b
    bar = m.part(f"steer_barrel_{suf}", origin=b)
    with bar.at(b, q=aim(d)):
        lib.hydraulic_barrel(bar, 0.5, 0.055, sides=10)
    rod = m.part(f"steer_rod_{suf}", origin=e)
    with rod.at(e, q=aim(-d)):
        lib.hydraulic_rod(rod, 0.55, 0.032, sides=10)
    STEER.append((suf, b, e))
    body.box((0.08, 0.12, 0.12), c=(s * 0.4, 0.45, 0.78), mat="paint_yellow", bev=0.006)

# ================================================================== empties
m.empty("fx_work", (0, -3.78, 0.05), parent="bucket")
m.empty("fx_ore", (0, -3.1, 0.45), parent="bucket")
front_lights = [L for L in LIGHTS if len(L) == 3]
rear_lights = [L for L in LIGHTS if len(L) == 2]
for i, (lens, d, par) in enumerate(front_lights):
    m.empty(f"light_{i}", lens, parent=par, beam=d)
for i, (lens, d) in enumerate(rear_lights):
    m.empty(f"light_{i + 2}", lens, beam=d)
m.empty("op", (0.91, -0.2, 0.98))
m.empty("snd", (0, 2.4, 1.2))

lib.tick("build parts")
m.finish(rays=20, strength=1.2, low=0.42, noise_amt=0.2)
lib.tick("finish+grime")


ANIM = ["front_frame", "lift_arms", "rocker", "bucket", "wheel_fl", "wheel_fr", "wheel_rl", "wheel_rr",
        "lift_l_barrel", "lift_l_rod", "lift_r_barrel", "lift_r_rod", "tilt_barrel", "tilt_rod", "link",
        "steer_barrel_l", "steer_rod_l", "steer_barrel_r", "steer_rod_r"]
worst = [0.0]


def rig(alpha, beta, wheel, psi):
    out = {}
    out["front_frame"] = {"q": Quaternion((0, 0, 1), psi)}
    out["lift_arms"] = {"q": Quaternion((1, 0, 0), alpha)}
    out["bucket"] = {"q": Quaternion((1, 0, 0), beta)}
    g, C, D, E, Rr = solve_rocker(alpha, beta)
    worst[0] = max(worst[0], abs((D - E).length - LINK))
    out["rocker"] = {"q": Quaternion((1, 0, 0), g)}
    for nm in ("wheel_fl", "wheel_fr", "wheel_rl", "wheel_rr"):
        out[nm] = {"q": Quaternion((1, 0, 0), wheel)}
    # front-frame children: positions relative to the front frame origin H
    for i, nm in enumerate(("lift_l", "lift_r")):
        b, e0 = LB[i], LE[i]
        e = rotx(e0, A, alpha)
        out[f"{nm}_barrel"] = {"q": aim(e - b) @ aim(e0 - b).inverted()}
        out[f"{nm}_rod"] = {"loc": e - H, "q": aim(b - e) @ aim(b - e0).inverted()}
    out["tilt_barrel"] = {"q": aim(C - B0) @ aim(C0 - B0).inverted()}
    out["tilt_rod"] = {"loc": C - H, "q": aim(B0 - C) @ aim(B0 - C0).inverted()}
    out["link"] = {"loc": D - H, "q": aim(E - D) @ aim(E0 - D0).inverted()}
    qs = Quaternion((0, 0, 1), psi)
    for suf, b, e0 in STEER:
        e = H + qs @ (e0 - H)
        out[f"steer_barrel_{suf}"] = {"q": aim(e - b) @ aim(e0 - b).inverted()}
        out[f"steer_rod_{suf}"] = {"loc": e, "q": aim(b - e) @ aim(b - e0).inverted()}
    return out


def work(t):
    a, b, w = pose_at(t)
    return rig(a, b, w, math.radians(3) * math.sin(math.tau * t))


def idle(t):
    return rig(KEYS[0][1], KEYS[0][2], 0.0, 0.0)


m.clip("Work", 6.0, work, ANIM)
m.clip("Idle", 2.0, idle, ANIM)
print(f"[lhd] z-bar link residual max {worst[0] * 1000:.1f} mm")
lib.tick("clips")
tris, size = m.report()
if stem:
    m.export(stem)
    lib.tick("export")
if "--no-render" not in flags:
    views = [
        ("front3q", (-5.6, -7.2, 3.3), (0, -0.6, 1.0), 32),
        ("rear3q", (5.2, 7.2, 3.4), (0, 0.6, 1.0), 32),
        ("side", (8.8, -0.3, 1.7), (0, 0.0, 1.05), 36),
    ]
    if "--one" in flags:
        views = views[:1]
    m.pose("Idle", 0.0)
    m.render(views)
    if "--one" not in flags:
        m.pose("Work", 0.36)
        m.render([("scoop", (-5.6, -7.2, 3.3), (0, -0.6, 1.0), 32)])
        m.pose("Work", 0.7)
        m.render([("lift", (-6.2, -6.6, 3.0), (0, -1.0, 1.3), 32)])
    m.unpose()
