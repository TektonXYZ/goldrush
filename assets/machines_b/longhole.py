"""Brennan LH-3 Longhole Drill (modelled on a Sandvik DL432 / Epiroc Simba ring-drilling rig).

    systemd-run --user --scope -q -p MemoryMax=3G -p MemorySwapMax=0 \
        bl assets/machines_b/longhole.py -- public/models/machines/longhole [--no-preview]

Fits the small alcove (<= 5.6 W x 7.6 L x 3.9 H). Blender axes, front (drilling end) = -Y = three.js +Z.
Articulated 4-wheel carrier: front frame with the operator cab (left), power-pack side (right) and a
roll-over unit carrying a 3.25 m feed mast across the front; rear frame with the diesel power pack,
exhaust scrubber, radiator and twin cable/water-hose reels; four stabiliser jacks set down.
Work 6 s: mast rolls through a +-25 deg fan, rock drill advances 0.8 m up the feed with the rod spinning
(the bit drives into the roof), then returns.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import bk  # noqa: E402
import lib  # noqa: E402
from lib import Part, V  # noqa: E402

ID = "longhole"
args = bk.args()
OUT = os.path.abspath(args[0]) if args and not args[0].startswith("--") else os.path.join(lib.PROJECT, "public/models/machines", ID)
PREVIEW = "--no-preview" not in args

bk.reset()
bpy.context.scene.render.fps = lib.FPS
WORK, IDLE = 180, 60
ATL = ID
lib.label(f"label_{ID}_decals", os.path.join(lib.DECALS, f"{ID}.png"))
lib.std_materials()
lib.label("custom_screen_lh3", os.path.join(lib.DECALS, f"scr_{ID}.png"), mode="OPAQUE", emit=2.2, rough=0.25)

YEL, DARK, STEEL = "paint_yellow", "steel_dark", "steel"
root = lib.root(ID)
static = []

FY, RYA = -1.85, 2.35            # axle y (front, rear)
TR, TW, TXO = 0.645, 0.42, 0.97  # axle height (tyre r 0.6 + lugs), width, track half-width
MX, MY, MZ = 0.25, -3.3, 1.22    # mast roll pivot
FEEDY = MY - 0.2                 # feed beam centre plane (y)
F0, F1 = 0.55, 3.66              # feed beam bottom / top (z, mast vertical)


# =============================================================================== carrier (static)
cr = Part("carrier")
cr.box2((-0.62, -3.05, 0.55), (0.62, -0.28, 1.15), YEL, bevel=0.025, seg=2)          # front frame
cr.box2((-0.64, 0.05, 0.55), (0.64, 3.45, 1.02), YEL, bevel=0.025, seg=2)            # rear frame
cr.box2((-0.7, -3.25, 0.62), (0.7, -3.02, 1.05), YEL, bevel=0.02, seg=2)             # front bumper
cr.box2((-0.75, 3.38, 0.6), (0.75, 3.55, 1.0), DARK, bevel=0.015, seg=1)              # rear bumper
for z in (0.72, 0.95):                                                                # articulation hinge
    cr.cyl(V(0, -0.2, z - 0.07), V(0, -0.2, z + 0.07), 0.16, DARK, sides=18, bevel=0.008, seg=1)
    cr.cyl(V(0, -0.2, z - 0.12), V(0, -0.2, z + 0.12), 0.05, STEEL, sides=10)
for s in (-1, 1):                                                                     # steering cylinders
    cr.hyd_cyl(V(s * 0.45, -0.7, 0.8), V(s * 0.42, 0.45, 0.8), 0.06, 0.035, m_barrel=YEL, frac=0.55, ports=False)
for y in (FY, RYA):                                                                   # axles + diff housings
    cr.cyl(V(-TXO + 0.15, y, TR), V(TXO - 0.15, y, TR), 0.11, DARK, sides=16)
    cr.lathe(V(0, y - 0.22, TR), (0, 1, 0), [(0.0, 0.0), (0.2, 0.0), (0.24, 0.12), (0.24, 0.3), (0.18, 0.42), (0.0, 0.42)], DARK, sides=18)
# fenders over the tyres
for y in (FY, RYA):
    for s in (-1, 1):
        pts = []
        for k in range(9):
            t = math.radians(20 + 140 * k / 8)
            pts.append(V(0, y - math.cos(t) * (TR + 0.1), TR + math.sin(t) * (TR + 0.1)))
        rings = [[V(s * (TXO - TW / 2 - 0.04), p.y, p.z) for p in pts], [V(s * (TXO + TW / 2 + 0.03), p.y, p.z) for p in pts]]
        cr.loft(rings, YEL, closed=False, caps=False)
        cr.loft([list(reversed(r)) for r in rings], YEL, closed=False, caps=False)
# front stabiliser jacks (down) + rear jacks
for (x, y, z0) in ((-1.05, -2.92, 1.0), (1.05, -2.92, 1.0), (-0.82, 3.3, 0.95), (0.82, 3.3, 0.95)):
    xa, xb = (x, -0.55) if x < 0 else (0.55, x)                                       # outrigger beam from the frame
    cr.box2((xa, y - 0.14, z0 - 0.15), (xb, y + 0.14, z0 + 0.05), YEL, bevel=0.012, seg=1)
    cr.cyl(V(x, y, z0 + 0.05), V(x, y, 0.55), 0.09, YEL, sides=16, bevel=0.006, seg=1)
    cr.cyl(V(x, y, 0.58), V(x, y, 0.12), 0.055, "chrome", sides=14)
    cr.cyl(V(x, y, 0.0), V(x, y, 0.12), 0.18, DARK, sides=16, bevel=0.01, seg=1)
    cr.cyl(V(x, y + 0.11, 0.45), V(x, y + 0.11, 0.85), 0.018, STEEL, sides=6)
# right side of the front frame: hydraulic tank, valve bank, compressor receiver, battery box
cr.box2((0.28, -2.95, 1.15), (1.12, -2.05, 1.85), YEL, bevel=0.02, seg=2)            # hydraulic tank
cr.cyl(V(0.95, -2.3, 1.85), V(0.95, -2.3, 1.93), 0.06, DARK, sides=12)
cr.box2((0.3, -1.95, 1.15), (1.1, -1.35, 1.6), "paint_grey", bevel=0.015, seg=2)      # valve cabinet
for k in range(6):
    cr.box2((0.4 + k * 0.11, -1.36, 1.25), (0.48 + k * 0.11, -1.34, 1.5), "paint_black")
cr.cyl(V(0.7, -1.2, 1.38), V(0.7, -0.4, 1.38), 0.24, YEL, sides=20, bevel=0.01, seg=1)   # air receiver
cr.lathe(V(0.7, -1.2, 1.38), (0, -1, 0), [(0.24, 0.0), (0.2, 0.08), (0.0, 0.11)], YEL, sides=20)
cr.lathe(V(0.7, -0.4, 1.38), (0, 1, 0), [(0.24, 0.0), (0.2, 0.08), (0.0, 0.11)], YEL, sides=20)
cr.box2((-0.6, -0.95, 1.15), (-0.25, -0.4, 1.45), DARK, bevel=0.01, seg=1)            # battery box
# roll-over unit (turntable) at the front, mast pivots on it
cr.box2((MX - 0.32, -3.3, 0.85), (MX + 0.32, -3.02, 1.6), YEL, bevel=0.02, seg=2)
cr.cyl(V(MX, -3.3, MZ), V(MX, -3.36, MZ), 0.34, DARK, sides=28, bevel=0.008, seg=1)
cr.bolt_ring(V(MX, -3.36, MZ), (0, -1, 0), 0.29, 12, r=0.014)
# operator cab (front left): posts, roof, glass, door, step, mirrors, lit interior
CX0, CX1, CY0, CY1, CZ0, CZ1 = -1.18, -0.24, -2.85, -1.35, 1.32, 2.86
cr.box2((CX0, CY0, CZ0 - 0.12), (CX1, CY1, CZ0), DARK, bevel=0.01, seg=1)
for x in (CX0, CX1 - 0.06):
    for y in (CY0, CY1 - 0.06):
        cr.box2((x, y, CZ0), (x + 0.06, y + 0.06, CZ1 - 0.08), YEL, bevel=0.008, seg=1)
cr.box2((CX0 - 0.04, CY0 - 0.06, CZ1 - 0.1), (CX1 + 0.04, CY1 + 0.04, CZ1), YEL, bevel=0.02, seg=2)
cr.box2((CX0 + 0.06, CY0 - 0.02, CZ0 + 0.05), (CX1 - 0.06, CY0, CZ1 - 0.12), "glass")
cr.box2((CX0 + 0.06, CY1 - 0.03, CZ0 + 0.55), (CX1 - 0.06, CY1 - 0.01, CZ1 - 0.12), "glass")
cr.box2((CX0 - 0.005, CY0 + 0.06, CZ0 + 0.05), (CX0 + 0.01, CY1 - 0.06, CZ1 - 0.12), "glass")
cr.box2((CX1 - 0.01, CY0 + 0.06, CZ0 + 0.5), (CX1 + 0.005, CY1 - 0.06, CZ1 - 0.12), "glass")
cr.box2((CX0 - 0.012, -2.2, CZ0 + 0.05), (CX0 - 0.002, -1.45, CZ1 - 0.15), YEL)        # door frame strips
cr.box2((CX0 - 0.03, -1.55, CZ0 + 0.7), (CX0 - 0.012, -1.5, CZ0 + 0.85), "paint_black")
for k in range(3):                                                                      # step ladder
    cr.box2((CX0 - 0.25, -1.95, 0.3 + k * 0.33), (CX0 - 0.02, -1.6, 0.33 + k * 0.33), "custom_grating")
cr.box2((CX0 - 0.27, -1.97, 0.25), (CX0 - 0.24, -1.58, 1.3), YEL)
cr.tube([V(CX0 - 0.05, -1.62, 1.4), V(CX0 - 0.25, -1.62, 1.4), V(CX0 - 0.25, -1.62, 0.6)], 0.018, YEL, sides=8)
cr.box2((CX0 + 0.1, CY0 + 0.15, CZ0), (CX1 - 0.1, CY0 + 0.45, CZ0 + 0.55), "paint_grey", bevel=0.01, seg=1)   # console
cr.box2((CX0 + 0.2, CY0 + 0.1, CZ0 + 0.55), (CX1 - 0.2, CY0 + 0.18, CZ0 + 0.85), "paint_black", bevel=0.008, seg=1)
cr.box2((-0.88, -1.95, CZ0), (-0.52, -1.6, CZ0 + 0.42), "plastic_black", bevel=0.02, seg=2)     # seat
cr.box2((-0.88, -1.62, CZ0 + 0.42), (-0.52, -1.52, CZ0 + 0.95), "plastic_black", bevel=0.02, seg=2)
cr.box2((CX0 + 0.25, -2.35, CZ1 - 0.13), (CX1 - 0.25, -1.85, CZ1 - 0.11), "emit_warm")
for x in (CX0 + 0.18, CX1 - 0.18):                                                      # roof work lights (front)
    cr.led_light(V(x, CY0 + 0.02, CZ1 + 0.08), (0.25 if x > -0.7 else 0.15, -1.0, 0.25), w=0.22, h=0.1)
cr.led_light(V(-0.71, CY1 - 0.05, CZ1 + 0.08), (0, 1.0, -0.2), w=0.22, h=0.1)
cr.cyl(V(CX0 - 0.02, CY0 + 0.05, CZ1 - 0.2), V(CX0 - 0.3, CY0 - 0.1, CZ1 - 0.2), 0.012, DARK, sides=6)    # mirror arm
cr.box((CX0 - 0.32, CY0 - 0.11, CZ1 - 0.25), (0.04, 0.16, 0.22), "paint_black", bevel=0.01, seg=1)
# rear frame: power pack hood, grilles, exhaust scrubber, radiator, reels
cr.box2((-0.88, 0.25, 1.0), (0.88, 1.75, 1.92), YEL, bevel=0.035, seg=3)
for s in (-1, 1):
    cr.grille(V(s * 0.885, 1.0, 1.45), 0.9, 0.5, 6, (s, 0, 0), DARK, depth=0.03)
cr.box2((-0.6, 0.45, 1.92), (0.6, 1.55, 1.96), YEL, bevel=0.01, seg=1)
for s in (-1, 1):                                                                           # bolted access doors on the hood
    for y0, y1 in ((0.35, 0.75), (1.25, 1.65)):
        cr.box2((min(s * 0.882, s * 0.895), y0, 1.1), (max(s * 0.882, s * 0.895), y1, 1.82), YEL, bevel=0.004, seg=1)
        cr.bolts(V(s * 0.896, y0 + 0.04, 1.14), V(s * 0.896, y0 + 0.04, 1.78), 4, (s, 0, 0), r=0.009)
        cr.box2((min(s * 0.895, s * 0.91), (y0 + y1) / 2 - 0.05, 1.42), (max(s * 0.895, s * 0.91), (y0 + y1) / 2 + 0.05, 1.47), "paint_black")
cr.handrail([V(-0.84, 0.3, 1.96), V(-0.84, 1.7, 1.96)], h=0.75, posts=0.7, toe=False, mid=False)
cr.handrail([V(0.84, 0.3, 1.96), V(0.84, 1.7, 1.96)], h=0.75, posts=0.7, toe=False, mid=False)
cr.box2((1.12, -2.8, 1.3), (1.13, -2.74, 1.75), DARK)                                        # tank sight gauge
cr.cyl(V(1.135, -2.77, 1.33), V(1.135, -2.77, 1.72), 0.012, "glass", sides=8)
cr.cyl(V(0.45, -2.25, 1.85), V(0.45, -2.25, 1.95), 0.07, "paint_black", sides=12)             # filler cap
cr.cyl(V(-0.3, CY1 - 0.25, CZ1), V(-0.3, CY1 - 0.25, CZ1 + 0.06), 0.07, "paint_black", sides=12)   # beacon
cr.lathe(V(-0.3, CY1 - 0.25, CZ1 + 0.06), (0, 0, 1), [(0.06, 0), (0.06, 0.1), (0.04, 0.14), (0, 0.15)], "emit_amber", sides=12)
for y in (-2.65, -0.75):                                                                      # side steps (right)
    cr.box2((0.62, y - 0.18, 0.62), (0.9, y + 0.18, 0.66), "custom_grating")
fx_, fy_ = 0.68, -0.25                                                                       # fire extinguisher on the deck
cr.lathe(V(fx_, fy_, 1.02), (0, 0, 1), [(0.0, 0), (0.07, 0), (0.075, 0.02), (0.075, 0.4), (0.055, 0.46), (0.022, 0.48), (0, 0.48)], "paint_red", sides=14)
cr.cyl(V(fx_, fy_, 1.5), V(fx_, fy_, 1.57), 0.02, STEEL, sides=8)
for k, (col, x) in enumerate((("hose_red", -0.66), ("rubber", -0.66), ("hose_yellow", 0.66), ("rubber", 0.66))):   # frame hose runs
    zz = 0.75 + (k % 2) * 0.07
    cr.tube([V(x, -2.9, zz), V(x, -0.6, zz), V(x * 0.7, -0.2, zz + 0.05), V(x, 0.3, zz), V(x, 2.0, zz)], 0.02, col, sides=6)
for s in (-1, 1):                                                                             # front frame gussets
    cr.slab([V(s * 0.62, -3.02, 0.62), V(s * 0.62, -2.5, 0.62), V(s * 0.62, -3.02, 1.12)], 0.025, YEL, normal=(1, 0, 0))
cr.cyl(V(0.55, 1.45, 1.96), V(0.55, 1.45, 2.3), 0.05, STEEL, sides=10)                     # exhaust + scrubber
cr.cyl(V(0.45, 0.6, 2.0), V(0.45, 1.3, 2.0), 0.16, STEEL, sides=18, bevel=0.01, seg=1)
cr.cyl(V(0.55, 1.4, 2.0), V(0.55, 1.45, 1.96), 0.05, STEEL, sides=10)
cr.box2((-0.75, 3.38, 1.02), (0.75, 3.46, 1.75), DARK, bevel=0.01, seg=1)                   # radiator
cr.grille(V(0.0, 3.47, 1.38), 1.3, 0.6, 9, (0, 1, 0), DARK, depth=0.025)
for x in (-0.55, 0.55):                                                                     # rear lights
    cr.led_light(V(x, 3.5, 1.82), (0, 1.0, -0.25), w=0.22, h=0.1)
for x in (-0.82, 0.82):                                                                     # reel A-frames
    cr.slab([V(x, 2.0, 1.02), V(x, 3.1, 1.02), V(x, 2.62, 1.75), V(x, 2.48, 1.75)], 0.05, YEL, normal=(1, 0, 0), bevel=0.006, seg=1)
cr.cyl(V(-0.85, 2.55, 1.58), V(0.85, 2.55, 1.58), 0.05, STEEL, sides=10)
cr.lathe(V(-0.72, 2.55, 1.58), (1, 0, 0), [(0.08, 0.0), (0.52, 0.0), (0.52, 0.03), (0.24, 0.03), (0.24, 0.72), (0.52, 0.72), (0.52, 0.75),
                                             (0.08, 0.75)], DARK, sides=32, caps=False)                 # cable reel drum
cr.cyl(V(-0.69, 2.55, 1.58), V(-0.0, 2.55, 1.58), 0.44, "cable", sides=32)
cr.lathe(V(0.08, 2.55, 1.58), (1, 0, 0), [(0.08, 0.0), (0.42, 0.0), (0.42, 0.03), (0.2, 0.03), (0.2, 0.62), (0.42, 0.62), (0.42, 0.65),
                                            (0.08, 0.65)], "paint_red", sides=28, caps=False)            # water hose reel
cr.cyl(V(0.11, 2.55, 1.58), V(0.7, 2.55, 1.58), 0.34, "hose_yellow", sides=28)
# steps + rail on the engine deck, fuel tank under the cab side
cr.box2((-0.62, 0.1, 0.98), (-0.3, 0.22, 1.02), "custom_grating")
cr.box2((-1.05, -1.25, 0.6), (-0.65, -0.4, 1.12), YEL, bevel=0.02, seg=2)
cr.cyl(V(-0.85, -0.82, 1.12), V(-0.85, -0.82, 1.18), 0.06, "paint_black", sides=12)
# hose bundle from the carrier into the roll-over unit
for k, col in enumerate(("hose_red", "rubber", "hose_yellow", "rubber")):
    cr.hose(V(0.62 - k * 0.07, -2.05, 1.16), V(0, -1, 0.3), V(MX + 0.2 - k * 0.06, -3.05, 1.5), V(0, 1, 0), 0.03, col, sag=0.1, reach=0.45)
static.append(cr.finish(root))

# tyres: lugged tread on a lathe carcass + painted rim
ty = Part("tyres")
for y in (FY, RYA):
    for s in (-1, 1):
        cx = s * TXO
        c = V(cx - TW / 2, y, TR)
        ty.lathe(c, (1, 0, 0), [(0.33, 0.0), (0.5, 0.0), (0.58, 0.02), (0.6, 0.06), (0.6, TW - 0.06), (0.58, TW - 0.02), (0.5, TW),
                                (0.33, TW)], "rubber", sides=28, caps=False)
        for k in range(24):
            t = k * math.tau / 24
            for row in (-1, 1):
                q = V(cx + row * TW * 0.24, y + math.cos(t) * 0.595, TR + math.sin(t) * 0.595)
                ty.box(q, (TW * 0.42, 0.09, 0.06), "rubber", rot=Matrix.Rotation(-t, 3, "X") @ Matrix.Rotation(math.radians(row * 15), 3, "Z"))
        ty.lathe(V(cx - TW / 2 + 0.02, y, TR), (1, 0, 0), [(0.0, 0.03), (0.3, 0.03), (0.34, 0.0), (0.34, TW - 0.04), (0.3, TW - 0.07),
                                                         (0.0, TW - 0.07)], YEL, sides=24, caps=False)
        ty.bolt_ring(V(cx + s * (TW / 2 - 0.05), y, TR), (s, 0, 0), 0.16, 10, r=0.016)
        ty.cyl(V(cx + s * (TW / 2 - 0.06), y, TR), V(cx + s * (TW / 2 - 0.0), y, TR), 0.1, DARK, sides=12)
static.append(ty.finish(root))

# =============================================================================== mast (rolls about Y) + drill + rod
ms = Part("mast", pivot=(MX, MY, MZ), axis=(0, 1, 0))
ms.cyl(V(MX, MY - 0.06, MZ), V(MX, MY - 0.16, MZ), 0.3, YEL, sides=28, bevel=0.01, seg=1)      # rotating flange
ms.box2((MX - 0.22, MY - 0.22, MZ - 0.55), (MX + 0.22, MY - 0.1, MZ + 0.55), YEL, bevel=0.015, seg=2)   # cradle
for s in (-1, 1):                                                                                     # cradle gussets + clamp bolts
    ms.slab([V(MX + s * 0.22, MY - 0.16, MZ - 0.5), V(MX + s * 0.22, MY - 0.16, MZ + 0.5), V(MX + s * 0.11, FEEDY + 0.1, MZ + 0.3),
             V(MX + s * 0.11, FEEDY + 0.1, MZ - 0.3)], 0.03, YEL, normal=(1, 0, 0))
    ms.bolts(V(MX + s * 0.16, MY - 0.225, MZ - 0.45), V(MX + s * 0.16, MY - 0.225, MZ + 0.45), 4, (0, -1, 0), r=0.013)
ms.box2((MX - 0.11, FEEDY - 0.12, F0), (MX + 0.11, FEEDY + 0.12, F1), YEL, bevel=0.014, seg=2)  # feed beam
for z in (F0 + 0.4, 1.5, 2.6, F1 - 0.4):                                                            # bolted splice plates
    for s in (-1, 1):
        ms.box((MX + s * 0.115, FEEDY, z), (0.012, 0.2, 0.18), YEL)
        ms.bolts(V(MX + s * 0.122, FEEDY - 0.06, z - 0.06), V(MX + s * 0.122, FEEDY + 0.06, z + 0.06), 2, (s, 0, 0), r=0.009)
ms.box2((MX - 0.03, FEEDY + 0.12, F0 + 0.15), (MX + 0.03, FEEDY + 0.15, F1 - 0.15), STEEL)                # feed chain run
for k in range(20):
    ms.box((MX, FEEDY + 0.16, F0 + 0.2 + k * 0.155), (0.05, 0.02, 0.06), DARK)
ms.cyl(V(MX - 0.15, FEEDY + 0.2, F1 + 0.02), V(MX + 0.15, FEEDY + 0.2, F1 + 0.02), 0.12, DARK, sides=20, bevel=0.006, seg=1)  # hose sheave
ms.box2((MX - 0.16, FEEDY + 0.05, F1 - 0.12), (MX + 0.16, FEEDY + 0.2, F1 + 0.02), YEL, bevel=0.01, seg=1)
for s in (-1, 1):
    ms.box2((MX + s * 0.09 - (0.02 if s > 0 else 0.0), FEEDY - 0.06, F0 + 0.1), (MX + s * 0.09 + (0.0 if s > 0 else 0.02), FEEDY + 0.06, F1 - 0.1),
            STEEL)                                                                                  # slide rails
ms.cyl(V(MX - 0.12, FEEDY, F1 - 0.08), V(MX + 0.12, FEEDY, F1 - 0.08), 0.07, DARK, sides=16)      # top pulley
ms.cyl(V(MX - 0.12, FEEDY, F0 + 0.08), V(MX + 0.12, FEEDY, F0 + 0.08), 0.07, DARK, sides=16)      # bottom pulley
for z in (F1 - 0.14, 2.3):                                                                          # centralizers
    ms.box((MX, FEEDY - 0.17, z), (0.3, 0.16, 0.12), YEL, bevel=0.01, seg=1)
    for s in (-1, 1):
        ms.box((MX + s * 0.05, FEEDY - 0.26, z), (0.06, 0.08, 0.1), STEEL)
        ms.cyl(V(MX + s * 0.15, FEEDY - 0.17, z), V(MX + s * 0.26, FEEDY - 0.17, z), 0.035, "chrome", sides=10)
ms.cyl(V(MX, FEEDY - 0.24, F1 - 0.02), V(MX, FEEDY - 0.24, F1 + 0.04), 0.07, "rubber", sides=14)   # dust/stinger collar
# rod carousel beside the feed (8 spare rods)
CAX = MX + 0.33
for z in (1.05, 3.25):
    ms.cyl(V(CAX, FEEDY - 0.15, z), V(CAX, FEEDY - 0.15, z + 0.06), 0.17, YEL, sides=20, bevel=0.006, seg=1)
ms.cyl(V(CAX, FEEDY - 0.15, 0.95), V(CAX, FEEDY - 0.15, 3.4), 0.035, STEEL, sides=10)
for k in range(8):
    t = k * math.tau / 8
    q = V(CAX + math.cos(t) * 0.12, FEEDY - 0.15 + math.sin(t) * 0.12, 0)
    ms.cyl(q + V(0, 0, 1.0), q + V(0, 0, 3.3), 0.022, DARK, sides=8)
    ms.cyl(q + V(0, 0, 3.12), q + V(0, 0, 3.22), 0.032, STEEL, sides=8)
for z in (1.6, 2.9):                                                                                # rod handler arms
    ms.box((MX + 0.2, FEEDY - 0.17, z), (0.26, 0.06, 0.06), YEL, bevel=0.006, seg=1)
    ms.box((MX + 0.08, FEEDY - 0.24, z), (0.06, 0.06, 0.1), STEEL)
ms.hyd_cyl(V(MX + 0.12, MY - 0.15, MZ - 0.35), V(CAX, FEEDY - 0.15, 1.0), 0.04, 0.025, m_barrel=YEL, frac=0.55, eye=False, ports=False)
# hoses from the cradle up the feed to the hose guide
for k, col in enumerate(("hose_red", "rubber")):
    ms.hose(V(MX - 0.12 + k * 0.06, MY - 0.22, MZ + 0.3), V(0, 0, 1), V(MX - 0.14 + k * 0.05, FEEDY + 0.12, 2.1), V(0, 0, -1), 0.022, col,
            reach=0.45)
ms.box((MX, FEEDY + 0.13, 2.15), (0.16, 0.06, 0.12), DARK)
ms.led_light(V(MX - 0.2, FEEDY - 0.12, 1.15), (0.0, -0.25, 1.0), w=0.2, h=0.09)
mast = ms.finish(root)

DZ0 = 0.78                                                                                            # rock drill at rest
dr = Part("rock_drill", pivot=(MX, FEEDY, DZ0))
dr.box2((MX - 0.2, FEEDY - 0.38, DZ0 - 0.12), (MX + 0.2, FEEDY - 0.08, DZ0 + 0.48), "paint_grey", bevel=0.03, seg=2)
dr.box2((MX - 0.16, FEEDY - 0.4, DZ0 + 0.0), (MX + 0.16, FEEDY - 0.38, DZ0 + 0.36), DARK)                     # side cover
dr.cyl(V(MX, FEEDY - 0.38, DZ0 + 0.55), V(MX, FEEDY - 0.38, DZ0 + 0.7), 0.075, "paint_black", sides=14)       # accumulator
dr.bolts(V(MX - 0.17, FEEDY - 0.381, DZ0 - 0.05), V(MX - 0.17, FEEDY - 0.381, DZ0 + 0.42), 4, (0, -1, 0), r=0.01)
dr.bolts(V(MX + 0.17, FEEDY - 0.381, DZ0 - 0.05), V(MX + 0.17, FEEDY - 0.381, DZ0 + 0.42), 4, (0, -1, 0), r=0.01)
dr.box2((MX - 0.13, FEEDY - 0.08, DZ0 - 0.05), (MX + 0.13, FEEDY + 0.12, DZ0 + 0.38), YEL, bevel=0.012, seg=1)   # cradle slide
for s in (-1, 1):
    dr.lathe(V(MX + s * 0.17, FEEDY - 0.2, DZ0 + 0.18), (s, 0, 0), [(0.06, 0.0), (0.06, 0.06), (0.04, 0.09), (0.0, 0.1)], "paint_black", sides=12)
dr.cyl(V(MX, FEEDY - 0.2, DZ0 + 0.42), V(MX, FEEDY - 0.2, DZ0 + 0.52), 0.06, STEEL, sides=14)        # shank adapter
for k, col in enumerate(("hose_red", "rubber", "hose_yellow")):                                       # hose loop under the drill
    dr.hose(V(MX - 0.1 + k * 0.08, FEEDY - 0.33, DZ0 + 0.05), V(0, -0.4, -1), V(MX - 0.08 + k * 0.06, FEEDY + 0.12, DZ0 - 0.15),
            V(0, 0.3, -1), 0.02, col, sag=0.2, reach=0.35)
drill = dr.finish(mast)

RODTOP = 3.83
rd = Part("drill_rod", pivot=(MX, FEEDY - 0.2, DZ0 + 0.52), axis=(0, 0, 1))
rd.cyl(V(MX, FEEDY - 0.2, DZ0 + 0.52), V(MX, FEEDY - 0.2, RODTOP - 0.08), 0.026, STEEL, sides=10)
for z in (DZ0 + 0.6, 2.2):                                                                              # coupling sleeves
    rd.cyl(V(MX, FEEDY - 0.2, z), V(MX, FEEDY - 0.2, z + 0.14), 0.036, DARK, sides=10)
rd.lathe(V(MX, FEEDY - 0.2, RODTOP - 0.1), (0, 0, 1), [(0.03, 0.0), (0.046, 0.03), (0.046, 0.08), (0.03, 0.1), (0.0, 0.1)], DARK, sides=12)
for k in range(6):                                                                                      # bit buttons
    t = k * math.tau / 6
    rd.sphere(V(MX + math.cos(t) * 0.028, FEEDY - 0.2 + math.sin(t) * 0.028, RODTOP - 0.002), 0.009, "cast_iron", seg=6, rings=3)
rd.box(V(MX + 0.027, FEEDY - 0.2, 1.8), (0.008, 0.012, 0.5), YEL)                                     # paint stripe (spin reads)
rod = rd.finish(drill)

# =============================================================================== decals + screen
dec = Part("decals", grime=False, smooth=False)
for s in (-1, 1):
    lib.decal_cell(dec, ATL, "mk", (s * 0.881, 0.62, 1.62), (s, 0, 0), (0, 0, 1), h=0.11)
    lib.decal_cell(dec, ATL, "lh3", (s * 0.881, 1.45, 1.2), (s, 0, 0), (0, 0, 1), h=0.12)
lib.decal_cell(dec, ATL, "plate", (0.62 + 0.001, -2.55, 0.85), (1, 0, 0), (0, 0, 1), w=0.22)
lib.decal_cell(dec, ATL, "warn_crush", (0.0, -3.251, 0.84), (0, -1, 0), (0, 0, 1), w=0.26)
lib.decal_cell(dec, ATL, "warn_hot", (0.45, 0.95, 2.161), (0, 0, 1), (0, -1, 0), w=0.22)
lib.decal_cell(dec, ATL, "reel", (-0.36, 2.55 - 0.443, 1.58), (0, -1, 0), (0, 0, 1), w=0.5)
lib.decal_cell(dec, ATL, "fuel", (-1.051, -0.82, 0.9), (-1, 0, 0), (0, 0, 1), w=0.3)
lib.decal_cell(dec, ATL, "badge", (0.7, -1.2 - 0.001, 1.38), (0, -1, 0), (0, 0, 1), w=0.3)
lib.decal_cell(dec, ATL, "ppe", (CX0 - 0.271, -1.78, 1.05), (-1, 0, 0), (0, 0, 1), w=0.28)
lib.decal(dec, (-0.71, CY0 + 0.181, CZ0 + 0.7), (0, 1, 0), (0, 0, 1), 0.48, 0.28, "custom_screen_lh3", lib.cell_uv(f"scr_{ID}", "main"), off=0.001)
lib.stripe(dec, (0.0, -3.251, 0.68), (0, -1, 0), (0, 0, 1), 1.38, 0.08, period=0.16)
lib.stripe(dec, (0.0, 3.551, 0.75), (0, 1, 0), (0, 0, 1), 1.48, 0.1, period=0.2)
static.append(dec.finish(root))
dm = Part("decals_mast", grime=False, smooth=False, pivot=(MX, MY, MZ))
lib.decal_cell(dm, ATL, "warn_rod", (MX, FEEDY + 0.101, 2.75), (0, 1, 0), (0, 0, 1), w=0.17)
lib.decal_cell(dm, ATL, "mk_w", (MX, FEEDY + 0.101, 1.75), (0, 1, 0), (1, 0, 0), h=0.13)
dm.finish(mast)

# =============================================================================== empties
lib.empty("fx_work", (MX, FEEDY - 0.2, RODTOP + 0.05), drill)
lib.empty("fx_ore", (MX, -3.75, 0.05), root)
lib.empty("light_0", (CX0 + 0.18, CY0 - 0.05, CZ1 + 0.08), root, aim=(0.15, -1.0, 0.25))
lib.empty("light_1", (MX - 0.2, FEEDY - 0.18, 1.15), mast, aim=(0.0, -0.25, 1.0))
lib.empty("light_2", (-0.55, 3.56, 1.82), root, aim=(0, 1.0, -0.25))
lib.empty("op", (-0.7, -1.78, CZ0 + 0.0), root, face=(0, -1, 0))
lib.empty("snd", (MX, MY, 1.4), root)

# =============================================================================== animation
A = math.radians(25)
lib.track(mast, "Work", "rotation_euler", 2, [(0, -A), (90, A), (WORK, -A)])
lib.track(drill, "Work", "location", 1, [(0, 0.0), (20, 0.0), (120, 0.8), (150, 0.8), (WORK, 0.0)])
lib.spin(rod, "Work", WORK, turns=12)
for o in (mast, drill, rod):
    lib.hold(o, "Idle", IDLE)
lib.bake_clips()

# =============================================================================== merge, grime, export
body = lib.merge([o for o in static if o.get("grime")], "body")
meshes = [o for o in lib.descendants(root) if o.type == "MESH" and o.get("grime")]
lib.bake_grime(meshes, distance=0.4, samples=48, floor_z=0.0)
path, js, anims, names = lib.export(root, OUT)
size = lib.report(root, "<= 5.6 W x 7.6 L x 3.9 H")
need = [ID, "fx_work", "fx_ore", "light_0", "light_1", "light_2", "op", "snd"]
print("[mb] missing nodes:", [n for n in need if n not in names])

if PREVIEW:
    lib.previews(ID, root, [
        dict(name="34", az=35, el=14, fill=0.95),
        dict(name="rear", az=210, el=16, fill=0.95),
        dict(name="side", az=-90, el=6, fill=0.95),
        dict(name="mast", az=25, el=6, target=(MX, -3.4, 2.2), dist=3.4, lens=32, frame=100),
        dict(name="cab", az=-50, el=10, target=(-0.7, -2.1, 1.9), dist=2.8, lens=32),
    ], frame=0)
