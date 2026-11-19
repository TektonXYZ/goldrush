"""Brennan DJ-2 twin-boom drill jumbo (MOTHERLODE machines-A, depth 2 / tier 2).

Modeled on a Sandvik DD321 / Epiroc Boomer 282: articulated four-wheel carrier, operator canopy, two hydraulic booms
each carrying a ~3.9 m feed beam with a rock drill (hammer) that slides along it, drill rods through front
centralisers, front + rear stabiliser jacks, hose reel, cable reel, water tank, lights. Compressed to 7.4 m.

    systemd-run --user --scope -q -p MemoryMax=3G -p MemorySwapMax=0 \
        bl assets/machines_a/jumbo.py -- public/models/machines/jumbo [--no-render] [--one]
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402
from lib import V, aim, frame  # noqa: E402
from mathutils import Quaternion  # noqa: E402

stem, flags = lib.args()
m = lib.Machine("jumbo")

# ------------------------------------------------------------------ decals
BADGE = ('<rect x="6" y="6" width="{w2}" height="{h2}" rx="18" fill="none" stroke="#151515" stroke-width="10"/>'
         '<text x="{cx}" y="{y1}" text-anchor="middle" font-family="Barlow Condensed Black" font-size="{s1}" '
         'letter-spacing="6" fill="#151515">BRENNAN</text>')
A_ = m.atlas
A_.add("brennan", 900, 230, lib.svg(900, 230, BADGE.format(w2=888, h2=218, cx=450, y1=178, s1=180), wear=0.4,
                                    seed=41))
A_.add("model", 640, 200, lib.svg_text("DJ-2", font="Saira Stencil One", wear=0.35), fit=True)
A_.add("unit", 360, 260, lib.svg_text("21", font="Saira Stencil One", wear=0.4, seed=5), fit=True)
A_.add("feedtxt", 900, 140, lib.svg_text("BRENNAN BF-400", font="Barlow Condensed Black", wear=0.45, seed=9),
       fit=True)
A_.add("hazard", 1024, 128, lib.svg_hazard(1024, 128, band=64, wear=0.45))
A_.add("chev", 1024, 128, lib.svg_chevron(1024, 128, wear=0.4))
A_.add("danger_rod", 512, 400, lib.svg_panel(512, 400, "DANGER", ["ROTATING DRILL STEEL", "STAY CLEAR OF", "FEED BEAMS"]))
A_.add("warn_reel", 512, 360, lib.svg_panel(512, 360, "WARNING", ["CABLE REEL", "1000 V"], seed=12))
A_.add("caution", 512, 360, lib.svg_panel(512, 360, "CAUTION", ["STABILISERS", "MUST BE DOWN"], seed=13))
A_.add("plate", 600, 360, lib.svg_plate(600, 360, ["MODEL   DJ-2 TWIN BOOM", "SERIAL  DJ2-0756", "DRILLS  2 X 20 KW",
                                                   "SUPPLY  1000 VAC 3PH", "BUILT   2022 BRENNAN"],
                                         title="BRENNAN DRILLING"))
A_.add("gauge", 256, 256, lib.svg_gauge(256, 256, vmax=250, unit="BAR", label="PERCUSSION"))
A_.add("gauge2", 256, 256, lib.svg_gauge(256, 256, vmax=150, unit="BAR", label="FEED", red=0.85, seed=29))
A_.add("water", 400, 110, lib.svg_text("WATER", font="Barlow Condensed Black", wear=0.4), fit=True)
A_.build()

# ------------------------------------------------------------------ carrier layout (Blender, front = -Y)
WR, WW, XW = 0.49, 0.42, 0.81             # tyre crown radius, width, wheel centre |x|
WZ = WR + 0.04
YF, YRA = -1.05, 1.95                     # axles
HINGE = V((0, 0.55, 0))
DECK_F = 1.02                             # front frame deck top
FRONT = -1.78                             # front frame nose
body = m.part("jumbo_body")


def mx(pts, s):
    return [(s * x, y) for x, y in pts]


# front frame
for s in (1, -1):
    body.plate([(0.45, 0.32), (0.45, 0.95), (FRONT + 0.05, 0.95), (FRONT, 0.8), (FRONT, 0.42), (FRONT + 0.25, 0.3),
                (0.3, 0.3)], 0.06, "YZ", at=s * 0.42, mat="paint_yellow", bev=0.012)
body.plate([(-0.95, FRONT), (0.95, FRONT), (1.02, FRONT + 0.15), (1.02, 0.45), (-1.02, 0.45), (-1.02, FRONT + 0.15)],
           0.06, "XY", at=DECK_F - 0.03, mat="paint_yellow", bev=0.012)
body.box((1.9, 0.12, 0.45), c=(0, FRONT - 0.02, 0.62), mat="paint_yellow", bev=0.015)               # bumper
body.decal("hazard", c=(0, FRONT - 0.081, 0.62), n=(0, -1, 0), w=1.8, h=0.12)
# rear frame + hood + hinge
for s in (1, -1):
    body.plate([(0.62, 0.32), (0.62, 0.95), (3.0, 0.95), (3.0, 0.32)], 0.06, "YZ", at=s * 0.45, mat="paint_yellow",
               bev=0.012)
for zz in (0.9, 0.4):
    body.box((0.4, 0.4, 0.07), c=(0, HINGE.y + (0.08 if zz > 0.5 else -0.08), zz), mat="paint_yellow", bev=0.01)
    body.cyl(0.06, 0.14, c=(0, HINGE.y, zz), mat="steel_dark", sides=12, bev=0.006)
body.box((1.5, 1.85, 0.62), c=(0, 1.75, 1.25), mat="paint_yellow", bev=0.06)                       # power-pack hood
body.box((1.56, 1.88, 0.04), c=(0, 1.75, 0.95), mat="paint_yellow", bev=0.01)
for s in (1, -1):
    body.grille((s * 0.755, 2.25, 1.25), 0.65, 0.36, 6, rot=(0, 0, 90 * s), depth=0.03, mat="paint_yellow",
                slat_mat="steel_dark")
    body.decal("brennan", c=(s * 0.751, 1.3, 1.27), n=(s, 0, 0), w=0.85)
    body.handrail([(s * 0.68, 0.95, 1.56), (s * 0.68, 0.95, 1.68), (s * 0.68, 2.5, 1.68), (s * 0.68, 2.5, 1.56)],
                  r=0.015)
body.mesh_panel((0, 2.25, 1.565), 0.9, 0.5, cell=0.06, wire=0.007, rot=(90, 0, 0))
lib.cover(body, (0.25, 1.25, 1.56), (0, 0, 1), 0.6, 0.6, t=0.014, pitch=0.14)
lib.fp_box(body, (-0.42, 1.05, 1.56), (0.5, 0.55, 0.4), n=(0, 0, 1), up=(0, 1, 0), pitch=0.12)    # electrics
body.decal("warn_reel", c=(-0.42 + 0.26, 1.05, 1.76), n=(1, 0, 0), w=0.18)
body.box((0.42, 1.1, 0.55), c=(0.78, 0.15, 0.82), mat="galvanized", bev=0.02)                      # water tank
body.decal("water", c=(0.991, 0.15, 0.9), n=(1, 0, 0), w=0.3)
body.cyl(0.06, 0.04, c=(0.78, -0.2, 1.11), mat="steel_dark", sides=12, bev=0)
for k in range(3):
    body.box((0.02, 1.1, 0.03), c=(0.992, 0.15, 0.62 + k * 0.18), mat="galvanized", bev=0)
# axles + wheels (static)
for yy in (YF, YRA):
    body.cyl(0.11, 1.22, c=(0, yy, WZ), axis="X", mat="steel_dark", sides=14, bev=0.008, segs=1)
    body.sphere(0.21, c=(0, yy, WZ), mat="steel_dark", seg=14, rings=7, scale=(1, 1.15, 1))
    for s in (1, -1):
        body.lathe([(0, 0), (0.17, 0), (0.19, 0.03), (0.19, 0.08), (0.14, 0.1), (0, 0.1)], c=(s * 0.48, yy, WZ),
                   rot=(0, 90 * s, 0), mat="steel_dark", sides=14)
        lib.wheel(body, (s * XW, yy, WZ), side=s, R=WR, W=WW, rim=0.27, lugs=22, lug_h=0.04, sides=28, nuts=8)
for s in (1, -1):                                                                                  # fenders
    for yy in (YF, YRA):
        body.box((0.46, 1.08, 0.03), c=(s * 0.82, yy, 1.1), mat="paint_yellow", bev=0.006)
        for sy in (1, -1):
            body.box((0.46, 0.24, 0.03), c=(s * 0.82, yy + sy * 0.62, 1.02), rot=(sy * -40, 0, 0), mat="paint_yellow",
                     bev=0.006)
# stabiliser jacks (front pair + rear pair), down on the floor
for s in (1, -1):
    for (yy, zt) in ((FRONT + 0.12, 0.95), (2.95, 0.95)):
        body.box((0.22, 0.24, 0.3), c=(s * 0.92, yy, zt - 0.1), mat="paint_yellow", bev=0.015)
        body.hyd(V((s * 0.92, yy, zt - 0.22)), V((s * 0.92, yy, 0.07)), rb=0.065, rr=0.045, frac=0.5)
        body.box((0.28, 0.3, 0.05), c=(s * 0.92, yy, 0.025), mat="steel_dark", bev=0.008)
        body.decal("hazard", c=(s * 0.92, yy - 0.121, zt - 0.1), n=(0, -1, 0), w=0.2, h=0.06)
body.decal("caution", c=(0.453, -1.0, 0.75), n=(1, 0, 0), w=0.2)
# hose reel (water) on the rear deck + cable reel at the very back
HR = V((0, 2.2, 1.95))
with body.at(HR, rot=(0, 90, 0)):
    body.cyl(0.36, 0.05, c=(0, 0, 0.36), mat="paint_yellow", sides=24, bev=0.006)
    body.cyl(0.36, 0.05, c=(0, 0, -0.36), mat="paint_yellow", sides=24, bev=0.006)
    body.cyl(0.25, 0.68, mat="hose_yellow", sides=24, bev=0)                                       # wound hose
    for k in range(6):
        body.lathe([(0.25, -0.34 + k * 0.115), (0.262, -0.29 + k * 0.115), (0.25, -0.24 + k * 0.115)],
                   mat="hose_yellow", sides=24, cap0=False, cap1=False)
    body.cyl(0.07, 0.86, mat="steel_dark", sides=12, bev=0)
for s in (1, -1):
    body.box((0.05, 0.14, 0.42), c=(s * 0.44, HR.y, HR.z - 0.2), mat="paint_yellow", bev=0.006)
CRL = V((0, 3.25, 0.95))
with body.at(CRL, rot=(0, 90, 0)):
    body.cyl(0.55, 0.05, c=(0, 0, 0.5), mat="paint_yellow", sides=28, bev=0.006)
    body.cyl(0.55, 0.05, c=(0, 0, -0.5), mat="paint_yellow", sides=28, bev=0.006)
    body.cyl(0.4, 0.95, mat="cable", sides=28, bev=0)                                              # wound cable
    for k in range(8):
        body.lathe([(0.4, -0.46 + k * 0.12), (0.418, -0.4 + k * 0.12), (0.4, -0.34 + k * 0.12)], mat="cable",
                   sides=28, cap0=False, cap1=False)
    body.cyl(0.12, 1.12, mat="steel_dark", sides=14, bev=0)
    for k in range(6):
        a = k / 6 * math.tau
        with body.at((0, 0, 0.53), rot=(0, 0, math.degrees(a))):
            body.box((0.04, 0.45, 0.02), c=(0, 0.28, 0), mat="paint_yellow", bev=0)
for s in (1, -1):
    body.plate([(2.72, 0.33), (3.6, 0.33), (3.6, 0.6), (3.35, 1.05), (3.15, 1.05), (2.9, 0.6), (2.72, 0.6)],
               0.06, "YZ", at=s * 0.6, mat="paint_yellow", bev=0.01)                               # reel arms
body.box((1.26, 0.22, 0.2), c=(0, 3.62, 0.22), mat="paint_yellow", bev=0.015)                     # rear bumper
body.decal("chev", c=(0, 3.731, 0.22), n=(0, 1, 0), w=1.2, h=0.09)
body.path([(0.0, 3.25, 0.4), (0.1, 3.45, 0.2), (0.3, 3.6, 0.06), (0.55, 3.66, 0.04)], r=0.035, mat="cable",
          sides=10, res=4)
# operator canopy (centre, behind the booms)
CZ0, ROOF = DECK_F, 2.3
body.box((0.42, 0.4, 0.22), c=(0, 0.05, CZ0 + 0.11), mat="steel_dark", bev=0.01)
body.box((0.48, 0.46, 0.1), c=(0, 0.03, CZ0 + 0.27), mat="plastic_black", bev=0.035)
body.box((0.48, 0.1, 0.55), c=(0, 0.3, CZ0 + 0.58), rot=(-10, 0, 0), mat="plastic_black", bev=0.035)
body.box((0.9, 0.32, 0.5), c=(0, -0.52, CZ0 + 0.25), mat="paint_yellow", bev=0.015)               # console
with body.at((0, -0.48, CZ0 + 0.53), rot=(-30, 0, 0)):
    body.box((0.9, 0.36, 0.05), mat="steel_dark", bev=0.008)
    for sx in (1, -1):
        body.rod((sx * 0.3, 0.05, 0.02), (sx * 0.3, 0.06, 0.15), 0.013, mat="plastic_black", sides=6)
        body.sphere(0.03, c=(sx * 0.3, 0.06, 0.17), mat="plastic_black", seg=8, rings=5)
        for k in range(3):
            body.rod((sx * (0.08 + k * 0.05), 0.08, 0.02), (sx * (0.08 + k * 0.05), 0.09, 0.12), 0.007, mat="steel",
                     sides=6)
    body.decal("gauge", c=(-0.12, -0.1, 0.026), n=(0, 0, 1), up=(0, -1, 0), w=0.1)
    body.decal("gauge2", c=(0.12, -0.1, 0.026), n=(0, 0, 1), up=(0, -1, 0), w=0.1)
    body.box((0.16, 0.1, 0.01), c=(0.0, -0.1, 0.03), mat="glass_dark", bev=0)
body.decal("plate", c=(0, -0.682, CZ0 + 0.25), n=(0, -1, 0), w=0.24)
POSTS = [(-0.5, -0.72), (0.5, -0.72), (-0.5, 0.45), (0.5, 0.45)]
for x, y in POSTS:
    body.box((0.09, 0.09, ROOF - CZ0), c=(x, y, (ROOF + CZ0) / 2), mat="paint_yellow", bev=0.012)
body.box((1.12, 1.3, 0.06), c=(0, -0.13, ROOF + 0.03), mat="paint_yellow", bev=0.012)
for (cx_, cy_, sx_, sy_) in ((0, -0.8, 1.14, 0.05), (0, 0.54, 1.14, 0.05), (-0.58, -0.13, 0.05, 1.38),
                             (0.58, -0.13, 0.05, 1.38)):
    body.box((sx_, sy_, 0.09), c=(cx_, cy_, ROOF + 0.045), mat="paint_yellow", bev=0.008)
body.mesh_panel((0, 0.47, CZ0 + 0.75), 0.92, 0.6, cell=0.075, wire=0.008)
body.decal("unit", c=(0, -0.827, ROOF + 0.045), n=(0, -1, 0), w=0.11)
LIGHTS = []
for s in (1, -1):
    d = V((s * 0.08, -1, -0.18)).normalized()
    lens = lib.work_light(body, (s * 0.38, -0.84, ROOF + 0.04), d, kind="bar", r=0.08)
    LIGHTS.append((lens, d))
for s in (1, -1):
    d = V((s * 0.08, 1, -0.2)).normalized()
    lens = lib.work_light(body, (s * 0.68, 3.5, 1.2), d, kind="round", r=0.07)
    LIGHTS.append((lens, d))
    body.box((0.08, 0.1, 0.16), c=(s * 0.68, 3.44, 1.12), mat="paint_yellow", bev=0)
body.decal("model", c=(0, 2.676, 1.3), n=(0, 1, 0), w=0.36)
body.decal("danger_rod", c=(0.55, FRONT + 0.05, 0.851), n=(0, 0, 1), up=(0, 1, 0), w=0.26)

# ================================================================== booms + feeds + hammers + rods
BOOMS = {}
SPEC = {  # side: (base pivot, boom head, feed direction)
    "l": (V((0.5, FRONT - 0.06, 1.12)), V((0.86, -3.0, 1.78)), V((0.06, -1, 0.05)).normalized()),
    "r": (V((-0.5, FRONT - 0.06, 1.12)), V((-0.86, -3.0, 1.22)), V((-0.06, -1, -0.03)).normalized()),
}
FEED_L, FRONT_AHEAD = 3.9, 0.7            # feed length, feed front ahead of the holder
HAM_L = 0.9
Z_H0, Z_H1 = -(FEED_L - FRONT_AHEAD) + 0.12, -HAM_L                     # hammer rear-end travel (feed local z)
BIT_Z = FRONT_AHEAD + 0.035
ROD_L0 = BIT_Z - (Z_H0 + HAM_L)
for suf, (B, Hh, D) in SPEC.items():
    sx = 1 if suf == "l" else -1
    # boom: base bracket, swing pivot, box boom, head rotator, feed holder
    body.box((0.3, 0.2, 0.36), c=B + V((0, 0.1, -0.05)), mat="paint_yellow", bev=0.015)
    boom = m.part(f"boom_{suf}", origin=B)
    boom.cyl(0.11, 0.3, c=B, mat="steel_dark", sides=14, bev=0.008)                                # swing pivot
    db = (Hh - B).normalized()
    Lb = (Hh - B).length
    qb = frame(db, (1, 0, 0))
    with boom.at(B, q=qb):
        boom.box((0.24, 0.26, Lb * 0.62), c=(0, 0, Lb * 0.31), mat="paint_yellow", bev=0.025)          # outer boom
        boom.box((0.19, 0.2, Lb * 0.45), c=(0, 0, Lb * 0.72), mat="steel", bev=0.015)                 # extension
        boom.box((0.26, 0.28, 0.12), c=(0, 0, Lb * 0.62), mat="paint_yellow", bev=0.012)
        for k in range(2):
            boom.hose(V((0.12, 0.1, 0.1 + k * 0.05)), (0, 0, 1), V((0.1, 0.12, Lb - 0.05)), (0, 0, 1), r=0.014,
                      mat="rubber", sides=8, k=0.3, fittings=None)
        for dx in (-0.06, 0.06):                                                                      # lift lugs
            boom.box((0.025, 0.16, 0.14), c=(dx, -0.15, Lb * 0.45), mat="paint_yellow", bev=0)
    boom.cyl(0.13, 0.22, c=Hh, axis="X", mat="steel_dark", sides=16, bev=0.008)                       # head rotator
    F = Hh + V((0, 0, 0.24))                                                                          # feed holder pt
    boom.box((0.16, 0.22, 0.3), c=Hh + V((0, 0, 0.1)), mat="paint_yellow", bev=0.012)
    qf = frame(D, (1, 0, 0))
    with boom.at(F, q=qf):                                                                            # holder clamps
        for zz in (-0.25, 0.25):
            boom.box((0.24, 0.26, 0.08), c=(0, -0.02, zz), mat="steel_dark", bev=0.008)
    upf = qf @ V((0, 1, 0))
    boom.hyd(Hh + V((0, 0.16, -0.06)), F - D * 1.05 - upf * 0.12, rb=0.045, rr=0.028)              # feed tilt cyl
    boom.box((0.1, 0.12, 0.1), c=F - D * 1.05 - upf * 0.1, mat="paint_yellow", bev=0.008)
    for k in range(3):                                                                               # boom -> feed
        boom.hose(Hh + V((sx * (0.1 + k * 0.03), 0.08, 0.12)), (0, 0.3, 1), F - D * (0.55 + k * 0.12) + upf * 0.02
                  + V((sx * 0.08, 0, 0)), -D, r=0.013, mat="rubber", sides=6, k=0.45, fittings=None)
    for k in range(3):                                                                               # carrier -> boom
        body.hose(V((sx * (0.18 + k * 0.06), -1.15, DECK_F + 0.01)), (0, -0.3, 1),
                  B + V((sx * (-0.06 + k * 0.05), 0.12, 0.2)), (0, -0.6, -0.4), r=0.016, mat="rubber", sides=8,
                  k=0.45, sag=0.05)
    # lift cylinder (static base on the carrier, eye on the boom)
    Lb_ = B + V((0, 0.3, -0.42))
    Le_ = B.lerp(Hh, 0.45) + qb @ V((0, -0.15, 0))
    BOOMS[suf] = dict(B=B, H=Hh, D=D, F=F, qf=qf, LB=Lb_, LE=Le_, sx=sx)
    # feed (child of boom): beam, centralisers, stinger, hose chain, feed cylinder
    feed = m.part(f"feed_{suf}", parent=f"boom_{suf}")
    feed.place = (F - B, qf)
    zr, zf = -(FEED_L - FRONT_AHEAD), FRONT_AHEAD
    feed.box((0.14, 0.17, FEED_L), c=(0, 0, (zr + zf) / 2), mat="aluminium", bev=0.012)
    feed.box((0.2, 0.025, FEED_L - 0.1), c=(0, 0.095, (zr + zf) / 2), mat="steel_dark", bev=0)          # slide rails
    for zz in (zf - 0.06, zf - 0.62):                                                                # centralisers
        feed.box((0.26, 0.26, 0.12), c=(0, 0.13, zz), mat="paint_yellow", bev=0.015)
        feed.cyl(0.05, 0.13, c=(0, 0.17, zz), mat="rubber", sides=10, bev=0)
    feed.box((0.2, 0.08, 0.06), c=(0, 0.17, zf + 0.03), mat="rubber", bev=0.006)                      # stinger pad
    feed.cyl(0.05, FEED_L - 0.6, c=(0, -0.12, (zr + zf) / 2 - 0.2), mat="paint_yellow", sides=12, bev=0)  # feed cyl
    feed.cyl(0.025, 0.5, c=(0, -0.12, zf - 0.52), mat="chrome", sides=10, bev=0)
    for k in range(22):                                                                              # hose chain
        zz = zr + 0.2 + k * (FEED_L - 1.2) / 21
        feed.box((0.05, 0.07, 0.15), c=(sx * 0.11, 0.08, zz), mat="plastic_black", bev=0)
    feed.decal("feedtxt", c=(-sx * 0.071, 0.0, zr + 1.3), n=(-sx, 0, 0), up=(0, 1, 0), w=0.7)
    feed.decal("hazard", c=(-sx * 0.071, 0.0, zf - 0.3), n=(-sx, 0, 0), up=(0, 1, 0), w=0.4, h=0.07)
    # hammer (child of feed) slides along local z
    ham = m.part(f"hammer_{suf}", parent=f"feed_{suf}")
    ham.place = (V((0, 0.2, Z_H0)), Quaternion())
    ham.box((0.22, 0.06, HAM_L * 0.9), c=(0, -0.07, HAM_L / 2), mat="steel_dark", bev=0.008)           # cradle
    ham.box((0.17, 0.17, HAM_L * 0.72), c=(0, 0.04, HAM_L * 0.45), mat="paint_yellow", bev=0.02)       # drill body
    ham.cyl(0.075, 0.2, c=(0, 0.04, HAM_L * 0.08), mat="steel", sides=14, bev=0.008)                  # rotation motor
    ham.cyl(0.04, 0.16, c=(0, 0.0, HAM_L * 0.9), mat="steel", sides=12, bev=0)                        # front head
    ham.cyl(0.03, 0.08, c=(0, 0.0, HAM_L), mat="steel_dark", sides=10, bev=0)                         # shank
    for k in range(3):
        ham.hose(V((0.06 - k * 0.06, 0.12, 0.05)), (0, 0.3, -1), V((sx * 0.11, 0.0, -0.22)), (0, -0.5, -1),
                 r=0.012, mat="rubber", sides=6, k=0.4, fittings=None)
    # rod (scales along -z from the bit) + bit (spins)
    rod = m.part(f"rod_{suf}", parent=f"feed_{suf}")
    rod.place = (V((0, 0.2, BIT_Z)), Quaternion())
    rod.cyl(0.019, ROD_L0, c=(0, 0, -ROD_L0 / 2), mat="steel", sides=6, bev=0)
    bit = m.part(f"bit_{suf}", parent=f"feed_{suf}")
    bit.place = (V((0, 0.2, BIT_Z)), Quaternion())
    bit.cyl(0.026, 0.05, c=(0, 0, -0.02), mat="steel_dark", sides=10, bev=0)
    bit.lathe([(0.026, 0.005), (0.027, 0.015), (0.02, 0.024), (0, 0.026)], mat="steel_dark", sides=10, cap0=True,
              cap1=False)
    for k in range(5):
        a = k / 5 * math.tau
        bit.sphere(0.005, c=(math.cos(a) * 0.015, math.sin(a) * 0.015, 0.024), mat="cast_iron", seg=6, rings=4)

# lift cylinders sized from the reposition stroke (small)
for suf, bd in BOOMS.items():
    b, e = bd["LB"], bd["LE"]
    L = (e - b).length
    bar = m.part(f"lift_barrel_{suf}", origin=b)
    with bar.at(b, q=aim(e - b)):
        lib.hydraulic_barrel(bar, L * 0.62, 0.07)
    rod = m.part(f"lift_rod_{suf}", origin=e)
    with rod.at(e, q=aim(b - e)):
        lib.hydraulic_rod(rod, L * 0.55, 0.045)
    body.box((0.16, 0.14, 0.14), c=b, mat="paint_yellow", bev=0.01)

# ================================================================== empties
for suf, nm in (("l", "fx_work"), ("r", "fx_work_1")):
    bd = BOOMS[suf]
    m.empties[nm] = (V((0, 0.2, BIT_Z + 0.03)), f"feed_{suf}", None)
m.empty("fx_ore", (0, -3.6, 0.15))
for i, (lens, d) in enumerate(LIGHTS):
    m.empty(f"light_{i}", lens, beam=d)
m.empty("op", (0, -0.25, CZ0))
m.empty("snd", (0, 1.7, 1.3))

lib.tick("build parts")
# feed-local empties: Machine.finish subtracts the parent's origin; feeds use `place`, so pre-compensate
for nm in ("fx_work", "fx_work_1"):
    loc, par, q = m.empties[nm]
    m.empties[nm] = (loc + m.parts[par].origin, par, q)
m.finish(rays=20, strength=1.2, low=0.42, noise_amt=0.2)
lib.tick("finish+grime")

ANIM = []
for suf in BOOMS:
    ANIM += [f"boom_{suf}", f"hammer_{suf}", f"rod_{suf}", f"bit_{suf}", f"lift_barrel_{suf}", f"lift_rod_{suf}"]
REST = {nm: (m.objs[nm].location.copy(), m.objs[nm].rotation_quaternion.copy()) for nm in ANIM
        if m.objs[nm].rotation_mode == "QUATERNION"}


def boom_state(u):
    """u = phase 0..1 -> (hammer travel 0..1, swing, lift)."""
    if u < 0.68:
        s = u / 0.68
        return s, 0.0, 0.0
    if u < 0.8:
        return 1.0 - lib.smooth((u - 0.68) / 0.12), 0.0, 0.0
    k = math.sin(math.pi * (u - 0.8) / 0.2)
    return 0.0, math.radians(3.0) * k, math.radians(-2.0) * k


def work(t):
    out = {}
    for suf, phase in (("l", 0.0), ("r", 0.5)):
        bd = BOOMS[suf]
        s, sw, lf = boom_state((t + phase) % 1.0)
        qb = Quaternion((0, 0, 1), bd["sx"] * sw) @ Quaternion((1, 0, 0), lf)
        out[f"boom_{suf}"] = {"q": qb}
        zh = lib.lerp(Z_H0, Z_H1, s)
        out[f"hammer_{suf}"] = {"loc": V((0, 0.2, zh))}
        spin = Quaternion((0, 0, 1), math.tau * 8 * t)
        out[f"rod_{suf}"] = {"q": spin, "s": (1, 1, (BIT_Z - (zh + HAM_L)) / ROD_L0)}
        out[f"bit_{suf}"] = {"q": spin}
        b, e0, B = bd["LB"], bd["LE"], bd["B"]
        e = B + qb @ (e0 - B)
        out[f"lift_barrel_{suf}"] = {"q": aim(e - b) @ aim(e0 - b).inverted()}
        out[f"lift_rod_{suf}"] = {"loc": e, "q": aim(b - e) @ aim(b - e0).inverted()}
    return out


m.clip("Work", 6.0, work, ANIM)
m.clip("Idle", 2.0, None, ANIM)
lib.tick("clips")
tris, size = m.report()
if stem:
    m.export(stem)
    lib.tick("export")
if "--no-render" not in flags:
    views = [
        ("front3q", (-5.2, -7.0, 3.4), (0, -1.0, 1.2), 32),
        ("side", (-9.0, -0.2, 1.8), (0, 0.0, 1.2), 36),
        ("rear3q", (5.0, 7.0, 3.4), (0, 0.6, 1.0), 32),
        ("close", (2.6, -5.0, 2.3), (0.4, -2.8, 1.5), 34),
    ]
    if "--one" in flags:
        views = views[:1]
    m.render(views)
    if "--one" not in flags:
        m.pose("Work", 0.4)
        m.render([("drill", (-5.2, -7.0, 3.4), (0, -1.0, 1.2), 32)])
        m.unpose()
