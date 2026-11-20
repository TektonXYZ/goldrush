"""Ironside LS-9 Longwall Shearer: a slice of a real longwall face.

    systemd-run --user --scope -q -p MemoryMax=3G -p MemorySwapMax=0 \
        bl assets/machines_b/longwall.py -- public/models/machines/longwall [--no-preview]

Blender axes: the face runs along X; -Y is the cut face (three.js +Z, working end); +Y the goaf side.
  y -3.30..-2.90  cut ore face (gold-bearing quartz band) the drums bite into
  y -2.88..-0.92  armoured face conveyor (AFC) with twin-chain flights on a closed loop + spill plate,
                  rack bar and cable trough; shearer riding on it with two ranging arms + spiral drums
  y -0.40..+2.45  three two-leg roof shields (base pontoons, legs, canopy, caving shield, lemniscates)
Work 6 s: shearer traverses +-1 m along X, drums 4 rev, AFC flights run toward +X (fx_ore end),
shield canopies breathe a centimetre with phase offsets, leg-pressure gauges flicker.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Matrix, Vector, noise  # noqa: E402

import bk  # noqa: E402
import lib  # noqa: E402
from lib import Part, V  # noqa: E402

ID = "longwall"
args = bk.args()
OUT = os.path.abspath(args[0]) if args and not args[0].startswith("--") else os.path.join(lib.PROJECT, "public/models/machines", ID)
PREVIEW = "--no-preview" not in args

bk.reset()
bpy.context.scene.render.fps = lib.FPS
WORK, IDLE = 180, 60
ATL = ID
lib.label(f"label_{ID}_decals", os.path.join(lib.DECALS, f"{ID}.png"))
lib.std_materials()
lib.label("custom_screen_ls9", os.path.join(lib.DECALS, f"scr_{ID}.png"), mode="OPAQUE", emit=2.2, rough=0.25)

YEL, DARK, STEEL, GALV = "paint_yellow", "steel_dark", "steel", "galvanized"
AY = -1.45            # AFC centreline
DECK = 0.30           # pan deck top
SX0 = -0.14           # shearer rest x (balances the high/low drum reach)
BY0, BY1 = -1.95, -0.98
SHX = (-1.75, 0.0, 1.75)
CTOP = 3.0            # canopy top
root = lib.root(ID)
static = []

# =============================================================================== cut ore face
fc = Part("face", smooth=False, wn=False)
NX, NZ = 24, 13
co = []
for j in range(NZ + 1):
    for i in range(NX + 1):
        x = -2.78 + 5.56 * i / NX
        z = 3.0 * j / NZ
        y = -2.905 - 0.05 * (noise.noise(Vector((x * 1.4, z * 1.4, 0.3))) + 0.6) - 0.025 * noise.noise(Vector((x * 4.1, z * 4.1, 2.0)))
        if 0.2 < z < 2.75:
            y -= 0.02 * math.sin(z * 10.0) ** 2           # drum-cut scallops
        if j == NZ:                                       # broken roof line
            z += 0.12 * noise.noise(Vector((x * 2.3, 7.0, 1.0))) - 0.05
        if i in (0, NX):                                  # ragged ends
            x = max(-2.79, min(2.79, x + 0.04 * noise.noise(Vector((z * 3.1, 3.0, 2.0))) - (0.04 if i else -0.04)))
        co.append((x, y, z))
for j in range(NZ):
    for i in range(NX):
        a = j * (NX + 1) + i
        zc = 3.0 * (j + 0.5) / NZ + 0.12 * noise.noise(Vector(((-2.78 + 5.56 * (i + 0.5) / NX) * 0.9, 0.0, 5.0)))
        m = "gold_ore" if 0.85 < zc < 2.05 else "rock_pale"
        fc.faces([co[k] for k in (a, a + 1, a + NX + 2, a + NX + 1)], [(0, 1, 2, 3)], m)
fc.box2((-2.7, -3.2, 0.0), (2.7, -2.94, 2.86), "rock_dark")
static.append(fc.finish(root))

# =============================================================================== armoured face conveyor
afc = Part("afc")
PANS = [(-2.25, -0.76), (-0.74, 0.74), (0.76, 2.25)]
for x0, x1 in PANS:
    afc.box2((x0, AY - 0.4, DECK - 0.025), (x1, AY + 0.4, DECK), STEEL, bevel=0.004, seg=1)
    afc.box2((x0, AY - 0.42, 0.04), (x1, AY + 0.42, 0.065), DARK)
    for s in (-1, 1):                                          # sigma side profiles
        y0 = AY + s * 0.4
        afc.box2((x0, min(y0, y0 + s * 0.07), 0.04), (x1, max(y0, y0 + s * 0.07), DECK + 0.07), DARK, bevel=0.008, seg=1)
        afc.box2((x0, min(y0 - s * 0.01, y0 + s * 0.02), DECK + 0.05), (x1, max(y0 - s * 0.01, y0 + s * 0.02), DECK + 0.075), STEEL)
    afc.prism((x0, 0, 0), (x1, 0, 0), [(AY - 0.47, DECK + 0.02), (AY - 0.47, 0.03), (AY - 0.7, 0.0), (AY - 0.7, 0.03)], DARK,
              up=(0, 0, 1), bevel=0.006, seg=1)                # face-side ramp/toe plate
    afc.box2((x0, AY + 0.47, 0.04), (x1, AY + 0.53, 0.88), YEL, bevel=0.008, seg=1)       # spill plate
    afc.box2((x0, AY + 0.43, 0.46), (x1, AY + 0.47, 0.62), DARK, bevel=0.004, seg=1)       # rack bar
    n = int((x1 - x0) / 0.125)
    for k in range(n):
        afc.box((x0 + 0.06 + k * 0.125, AY + 0.425, 0.54), (0.055, 0.03, 0.13), STEEL)
    afc.box2((x0, AY + 0.53, 0.6), (x1, AY + 0.92, 0.63), GALV)                            # cable trough
    afc.box2((x0, AY + 0.89, 0.63), (x1, AY + 0.92, 0.92), GALV, bevel=0.003, seg=1)
    for xb in (x0 + 0.25, (x0 + x1) / 2, x1 - 0.25):
        afc.box2((xb - 0.03, AY + 0.6, 0.0), (xb + 0.03, AY + 0.66, 0.6), DARK)
        afc.box2((xb - 0.03, AY + 0.53, 0.56), (xb + 0.03, AY + 0.9, 0.6), DARK)
    afc.bolts((x0 + 0.1, AY + 0.53, 0.8), (x1 - 0.1, AY + 0.53, 0.8), 5, (0, 1, 0), r=0.012)
for xj in (-0.75, 0.75):                                        # pan joints: dogbones + bolts
    for s in (-1, 1):
        afc.box((xj, AY + s * 0.49, 0.2), (0.16, 0.05, 0.12), STEEL, bevel=0.006, seg=1)
        afc.bolts((xj - 0.05, AY + s * 0.515, 0.2), (xj + 0.05, AY + s * 0.515, 0.2), 2, (0, s, 0), r=0.012)
# drive frames hiding the chain turn-arounds
for e in (-1, 1):
    xa, xb = (2.25, 2.8) if e > 0 else (-2.8, -2.25)
    xc = (xa + xb) / 2
    afc.box2((xa, AY - 0.5, 0.03), (xb, AY + 0.53, 0.48), DARK, bevel=0.02, seg=2)
    afc.cyl((xc, AY - 0.56, 0.36), (xc, AY + 0.58, 0.36), 0.25, DARK, sides=24, bevel=0.012, seg=2)
    afc.bolt_ring((xc, AY - 0.56, 0.36), (0, -1, 0), 0.2, 8, r=0.013)
    afc.box2((xa + 0.03, AY - 0.6, 0.06), (xb - 0.03, AY - 0.5, 0.3), DARK, bevel=0.01, seg=1)
    afc.box2((xa, AY + 0.53, 0.03), (xb, AY + 0.95, 0.66), YEL, bevel=0.02, seg=2)         # gearbox
    afc.bolts((xa + 0.05, AY + 0.95, 0.6), (xb - 0.05, AY + 0.95, 0.6), 4, (0, 1, 0), r=0.012)
    if e > 0:                                                  # main gate drive motor (vertical)
        afc.cyl((xc, AY + 0.74, 0.66), (xc, AY + 0.74, 1.45), 0.2, "paint_grey", sides=24, bevel=0.01, seg=2)
        for k in range(6):
            afc.torus((xc, AY + 0.74, 0.78 + k * 0.11), (0, 0, 1), 0.205, 0.01, "paint_grey", seg=20, rseg=4)
        afc.lathe((xc, AY + 0.74, 1.45), (0, 0, 1), [(0.2, 0), (0.17, 0.06), (0.0, 0.08)], "paint_grey", sides=24)
        afc.box2((xc - 0.12, AY + 0.86, 1.05), (xc + 0.12, AY + 0.99, 1.3), "paint_grey", bevel=0.01, seg=1)
        afc.cable([V(xc, AY + 0.99, 1.2), V(xc + 0.05, AY + 1.1, 1.0), V(xc + 0.08, AY + 1.12, 0.3), V(xc + 0.12, AY + 1.3, 0.04)], 0.04,
                  sides=8)
# cables lying in the trough (shearer trailing cable + water hose)
afc.cable([V(-2.25, AY + 0.66, 0.66), V(0.0, AY + 0.67, 0.665), V(2.25, AY + 0.66, 0.66)], 0.045, sides=8)
afc.cable([V(-2.25, AY + 0.78, 0.65), V(0.0, AY + 0.79, 0.655), V(2.25, AY + 0.78, 0.65)], 0.028, m="hose_yellow", sides=8)
static.append(afc.finish(root))

# AFC flights on a closed loop: top run (visible) -> drop in the head frame -> return run inside the
# pans -> rise in the tail frame. 24 evenly spaced segments, each carrying its twin-chain links.
XL, XR, ZT, ZB = -2.72, 2.3, DECK + 0.005, 0.115
LOOP = 2 * (XR - XL) + 2 * (ZT - ZB)
NSEG = 24
PITCH = LOOP / NSEG
STEP = 6                                     # segments advanced per Work loop


def loop_pos(s):
    s %= LOOP
    a = XR - XL
    if s < a:
        return V(XL + s, 0, ZT)
    s -= a
    if s < ZT - ZB:
        return V(XR, 0, ZT - s)
    s -= ZT - ZB
    if s < a:
        return V(XR - s, 0, ZB)
    s -= a
    return V(XL, 0, ZB + s)


def flight_part(name, lumps):
    p = Part(name, pivot=(0, AY, 0))
    p.box((0, AY, ZT + 0.03), (0.07, 0.74, 0.055), STEEL, bevel=0.008, seg=1)
    for s in (-1, 1):
        p.box((0, AY + s * 0.39, ZT + 0.03), (0.09, 0.05, 0.065), STEEL)
    for s in (-1, 1):                                   # chain links forward of the flight
        for k in range(3):
            x = 0.05 + k * (PITCH - 0.05) / 3
            ln = (PITCH - 0.05) / 3 + 0.015
            if k % 2 == 0:
                p.box((x + ln / 2, AY + s * 0.11, ZT + 0.022), (ln, 0.016, 0.042), STEEL)
            else:
                p.box((x + ln / 2, AY + s * 0.11, ZT + 0.016), (ln, 0.044, 0.016), STEEL)
    if lumps:
        for k, (dx, dy, r) in enumerate(((-0.12, -0.18, 0.065), (-0.2, 0.12, 0.055), (-0.1, 0.26, 0.05))):
            p.ico((dx, AY + dy, ZT + 0.03 + r * 0.6), r, "gold_ore", detail=0, scale=(1.2, 1, 0.75),
                  rot=(k * 30, k * 50, k * 70), seed=90 + k)
    return p


fl_a = flight_part("flight_a", False).finish(root)
fl_b = flight_part("flight_b", True).finish(root)
flights = []
for i in range(NSEG):
    src = fl_b if i % 2 else fl_a
    o = src.copy()
    o.name = f"flight_{i:02d}"
    bpy.context.scene.collection.objects.link(o)
    p0 = loop_pos(i * PITCH)
    o.location = (p0.x, AY, p0.z - ZT)            # geometry is built at the deck height
    o["_rest_loc"] = list(o.location)
    o["_rest_rot"] = [0, 0, 0]
    o["_rest_scale"] = [1, 1, 1]
    flights.append((o, i * PITCH))
for src in (fl_a, fl_b):
    bpy.data.objects.remove(src, do_unlink=True)

# =============================================================================== roof shields (built once, instanced x3)
LEGS = []
for s in (-1, 1):
    LEGS.append((s * 0.42, V(s * 0.42, 0.56, 0.42), V(s * 0.42, 0.2, 2.68)))


def leg_point(bot, top, z):
    t = (z - bot.z) / (top.z - bot.z)
    return bot.lerp(top, t)


sb = Part("shield_base")
for s in (-1, 1):
    px = s * 0.42
    sb.prism((px - 0.2, 0, 0), (px + 0.2, 0, 0), [(-0.4, 0.0), (2.42, 0.0), (2.42, 0.36), (2.32, 0.42), (0.25, 0.42), (-0.4, 0.13)], YEL,
             up=(0, 0, 1), bevel=0.016, seg=2)
    sb.box2((px - 0.16, 0.9, 0.42), (px + 0.16, 1.5, 0.44), YEL, bevel=0.004, seg=1)
    sb.bolts((px - 0.13, 0.95, 0.44), (px - 0.13, 1.45, 0.44), 4, (0, 0, 1), r=0.01)
    sb.bolts((px + 0.13, 0.95, 0.44), (px + 0.13, 1.45, 0.44), 4, (0, 0, 1), r=0.01)
sb.box2((-0.6, 1.95, 0.05), (0.6, 2.32, 0.36), YEL, bevel=0.014, seg=2)                       # rear bridge
sb.box2((-0.12, -0.92, 0.06), (0.12, 1.45, 0.27), DARK, bevel=0.012, seg=2)                   # relay bar
sb.box2((-0.16, -0.98, 0.04), (0.16, -0.86, 0.32), DARK, bevel=0.01, seg=1)
sb.cyl((-0.2, -0.92, 0.2), (0.2, -0.92, 0.2), 0.04, STEEL, sides=10)
sb.cyl(V(0, 1.9, 0.2), V(0, 1.5, 0.2), 0.065, YEL, sides=12)
sb.cyl(V(0, 1.5, 0.2), V(0, 1.3, 0.2), 0.04, "chrome", sides=10)
for _, bot, top in LEGS:                                                                  # leg barrels + first stage
    d = (top - bot).normalized()
    sb.sphere(bot + d * 0.02, 0.17, DARK, seg=12, rings=6)
    b1 = bot + d * 1.15
    sb.cyl(bot + d * 0.08, b1, 0.15, YEL, sides=20, bevel=0.01, seg=1)
    sb.cyl(bot + d * 0.1, bot + d * 0.2, 0.168, YEL, sides=20, bevel=0.006, seg=1)
    sb.cyl(b1 - d * 0.08, b1 + d * 0.02, 0.168, YEL, sides=20, bevel=0.006, seg=1)
    sb.cyl(b1, b1 + d * 0.76, 0.12, "chrome", sides=18, caps=(False, False))
    sb.cyl(b1 + d * 0.7, b1 + d * 0.8, 0.135, YEL, sides=18)
    a, b = lib.perp(d)
    for t in (0.25, 0.95):
        pp = bot + d * t
        sb.cyl(pp, pp + V(0, -0.2, 0), 0.025, STEEL, sides=8)
# lemniscate links + caving-shield pins
for s in (-1, 1):
    x = s * 0.32
    for (pb, pt) in ((V(x, 1.5, 0.38), V(x, 1.98, 1.26)), (V(x, 2.2, 0.36), V(x, 2.3, 1.16))):
        sb.cyl(pb + V(-0.07, 0, 0), pb + V(0.07, 0, 0), 0.07, DARK, sides=10)
        sb.prism(pb, pt, [(-0.05, -0.06), (0.05, -0.06), (0.05, 0.06), (-0.05, 0.06)], YEL, up=(1, 0, 0), bevel=0.01, seg=1)
        sb.cyl(pt + V(-0.07, 0, 0), pt + V(0.07, 0, 0), 0.065, DARK, sides=10)
# valve bank + controller housing on the left leg barrel (faces the walkway)
vb = leg_point(LEGS[0][1], LEGS[0][2], 1.05)
sb.box((vb.x, vb.y - 0.2, vb.z), (0.3, 0.12, 0.26), "paint_grey", bevel=0.01, seg=2)
sb.box((vb.x, vb.y - 0.2, vb.z + 0.27), (0.24, 0.1, 0.2), "paint_black", bevel=0.01, seg=2)
sb.box((vb.x, vb.y - 0.17, vb.z + 0.12), (0.06, 0.06, 0.06), DARK)
for k in range(4):
    sb.cyl((vb.x - 0.105 + k * 0.07, vb.y - 0.26, vb.z - 0.13), (vb.x - 0.105 + k * 0.07, vb.y - 0.26, vb.z - 0.17), 0.02, STEEL, sides=6)
for k, col in enumerate(("hose_red", "rubber", "hose_yellow", "rubber")):                # hoses valve bank -> legs/relay
    x0 = vb.x - 0.105 + k * 0.07
    if k < 2:
        tgt = LEGS[k][1] + (LEGS[k][2] - LEGS[k][1]).normalized() * (0.25 + 0.7 * k) + V(0, -0.2, 0)
        sb.hose(V(x0, vb.y - 0.26, vb.z - 0.19), V(0, 0, -1), tgt, V(0, -1, 0), 0.016, col, reach=0.25, sides=6, n=14)
    else:
        sb.hose(V(x0, vb.y - 0.26, vb.z - 0.19), V(0, 0, -1), V(0.0 + (k - 2) * 0.08, -0.6, 0.28), V(0, 0, 1), 0.016, col, reach=0.3,
                sides=6, n=14)
# inter-shield main lines (pressure/return) sagging between units
for k, (col, y) in enumerate((("hose_red", 1.62), ("rubber", 1.72))):
    sb.hose(V(-0.6, y, 0.46), V(-1, 0, 0), V(-1.04, y, 0.46), V(1, 0, 0), 0.028, col, sag=0.12, reach=0.22, n=12)
shield_base = sb.finish(root)

sc = Part("shield_canopy", pivot=(0, 0.2, 2.68))
sc.prism((-0.72, 0, 0), (0.72, 0, 0), [(-2.12, CTOP - 0.1), (-2.12, CTOP), (1.75, CTOP), (1.75, CTOP - 0.27), (0.6, 2.69), (-0.25, 2.69)],
         YEL, up=(0, 0, 1), bevel=0.016, seg=2)
for s in (-1, 1):                                                                         # side shields
    sc.box2((s * 0.72 - (0.014 if s > 0 else 0), -2.0, CTOP - 0.22), (s * 0.72 + (0.0 if s > 0 else 0.014), 1.7, CTOP - 0.02), YEL,
            bevel=0.004, seg=1)
for x in (-0.55, -0.2, 0.2, 0.55):                                                         # underside ribs
    sc.prism((x - 0.012, 0, 0), (x + 0.012, 0, 0), [(-1.9, CTOP - 0.1), (1.6, CTOP - 0.1), (1.6, CTOP - 0.3), (0.6, 2.62),
                                                     (-0.25, 2.62), (-1.9, CTOP - 0.14)], YEL, up=(0, 0, 1))
for _, bot, top in LEGS:                                                                  # leg sockets + 2nd stage
    d = (top - bot).normalized()
    sc.box((top.x, top.y, 2.66), (0.34, 0.36, 0.08), YEL, bevel=0.012, seg=1)
    sc.sphere(top - d * 0.02, 0.13, DARK, seg=10, rings=5)
    sc.cyl(top - d * 0.05, top - d * 0.75, 0.095, "chrome", sides=18)
sc.slab([V(-0.66, -2.12, CTOP - 0.02), V(0.66, -2.12, CTOP - 0.02), V(0.66, -2.3, CTOP - 0.5), V(-0.66, -2.3, CTOP - 0.5)], 0.04, YEL,
        bevel=0.008, seg=1)                                                               # face sprag (flipper)
sc.cyl((-0.68, -2.12, CTOP - 0.04), (0.68, -2.12, CTOP - 0.04), 0.035, DARK, sides=10)
sc.hyd_cyl(V(0, -1.6, 2.86), V(0, -2.2, 2.68), 0.045, 0.026, m_barrel=YEL, frac=0.55, eye=False, ports=False)
# caving (gob) shield hinged to the canopy rear
cs0, cs1 = V(0, 1.62, 2.76), V(0, 2.3, 1.18)
cdir = (cs1 - cs0).normalized()
cn = cdir.cross(V(1, 0, 0)).normalized()
if cn.y < 0:
    cn = -cn
pts = [V(-0.68, cs0.y, cs0.z), V(0.68, cs0.y, cs0.z), V(0.68, cs1.y, cs1.z), V(-0.68, cs1.y, cs1.z)]
sc.slab([p + cn * 0.1 for p in pts], 0.06, YEL, bevel=0.01, seg=1)
for s in (-1, 1):
    sc.slab([V(s * 0.68, cs0.y, cs0.z), V(s * 0.68, cs1.y, cs1.z), V(s * 0.68, cs1.y - cn.y * 0.0 - 0.15, cs1.z + 0.05),
             V(s * 0.68, cs0.y - 0.15, cs0.z - 0.05)], 0.04, YEL, normal=(1, 0, 0), bevel=0.006, seg=1)
for x in (-0.35, 0.0, 0.35):
    sc.prism(cs0 + V(x, 0, 0) - cdir * 0.0, cs1 + V(x, 0, 0), [(-0.012, 0.0), (0.012, 0.0), (0.012, 0.13), (-0.012, 0.13)], YEL,
             up=tuple(-cn))
sc.cyl((-0.7, 1.68, 2.74), (0.7, 1.68, 2.74), 0.07, DARK, sides=14)
outer = [p + cn * 0.13 for p in pts]                                                     # outer plate face
for x in (-0.45, 0.45):                                                                   # welded stiffener ribs
    sc.prism(V(x, cs0.y, cs0.z) + cn * 0.13 + cdir * 0.08, V(x, cs1.y, cs1.z) + cn * 0.13 - cdir * 0.06,
             [(-0.03, 0.0), (0.03, 0.0), (0.03, 0.05), (-0.03, 0.05)], YEL, up=tuple(cn), bevel=0.006, seg=1)
for t in (0.33, 0.66):                                                                    # plate seams + bolts
    q = cs0.lerp(cs1, t) + cn * 0.13
    sc.prism(V(-0.64, q.y, q.z), V(0.64, q.y, q.z), [(-0.012, 0.0), (0.012, 0.0), (0.012, 0.012), (-0.012, 0.012)], DARK, up=tuple(cn))
    sc.bolts(V(-0.55, q.y, q.z) + cn * 0.01, V(0.55, q.y, q.z) + cn * 0.01, 4, cn, r=0.011)
for s_ in (-1, 1):
    sc.prism(V(s_ * 0.66, cs0.y, cs0.z) + cn * 0.13, V(s_ * 0.66, cs1.y, cs1.z) + cn * 0.13,
             [(-0.02, 0.0), (0.02, 0.0), (0.02, 0.035), (-0.02, 0.035)], DARK, up=tuple(cn))
    lug = cs0.lerp(cs1, 0.12) + cn * 0.13 + V(s_ * 0.3, 0, 0)
    sc.slab([lug - cdir * 0.06, lug + cdir * 0.06, lug + cdir * 0.04 + cn * 0.09, lug - cdir * 0.04 + cn * 0.09], 0.03, YEL,
            normal=(1, 0, 0))
# work light under the tip + controller hose to the canopy
sc.led_light((0, -1.05, 2.64), (0, -0.25, -1.0), w=0.42, h=0.1, d=0.08)
shield_canopy = sc.finish(root)

# instance the shield units at -1.75 / 0 / +1.75
bases, canopies = [], []
for k, x in enumerate(SHX):
    if k == 1:
        ob, oc = shield_base, shield_canopy
    else:
        ob = shield_base.copy()
        ob.data = shield_base.data.copy()
        bpy.context.scene.collection.objects.link(ob)
        oc = shield_canopy.copy()
        bpy.context.scene.collection.objects.link(oc)
    ob.location = (x, 0, 0)
    oc.location = (x, 0.2, 2.68)
    ob.name = f"shield_base_{k}"
    oc.name = f"shield_canopy_{k}"
    for o in (ob, oc):
        o["_rest_loc"] = list(o.location)
        o["_rest_rot"] = [0, 0, 0]
        o["_rest_scale"] = [1, 1, 1]
    bases.append(ob)
    canopies.append(oc)
static += bases

# =============================================================================== shearer (traverses along X)
sh = Part("shearer", pivot=(SX0, AY, 0))
X = SX0
sh.box2((X - 0.78, BY0, 0.5), (X + 0.78, BY1, 1.45), YEL, bevel=0.035, seg=3)
sh.box2((X - 0.6, BY0 + 0.08, 1.45), (X + 0.6, BY1 - 0.08, 1.49), YEL, bevel=0.012, seg=1)
for s in (-1, 1):                                                          # haulage end units
    xa = X + s * 0.78
    sh.box2((min(xa, xa + s * 0.17), BY0 + 0.03, 0.45), (max(xa, xa + s * 0.17), BY1 - 0.02, 1.3), YEL, bevel=0.03, seg=2)
    sh.bolts((xa + s * 0.17, BY0 + 0.15, 1.2), (xa + s * 0.17, BY1 - 0.15, 1.2), 5, (s, 0, 0), r=0.012)
    sh.bolts((xa + s * 0.17, BY0 + 0.15, 0.55), (xa + s * 0.17, BY1 - 0.15, 0.55), 5, (s, 0, 0), r=0.012)
    gx = X + s * 0.62                                                      # haulage sprocket on the rack
    sh.cyl((gx, BY1 - 0.08, 0.55), (gx, BY1 - 0.03, 0.55), 0.13, DARK, sides=24)
    for k in range(12):
        a = k * math.tau / 12
        sh.box((gx + math.cos(a) * 0.14, BY1 - 0.055, 0.55 + math.sin(a) * 0.14), (0.04, 0.05, 0.035), STEEL, rot=(0, -math.degrees(a), 0))
    sh.box2((X + s * 0.45 - 0.16, BY0 + 0.01, 0.36), (X + s * 0.45 + 0.16, BY0 + 0.12, 0.52), DARK, bevel=0.01, seg=1)   # face skid
    sh.box2((X + s * 0.3 - 0.12, BY1 - 0.04, 0.82), (X + s * 0.3 + 0.12, BY1 + 0.07, 0.95), DARK, bevel=0.006, seg=1)   # guide shoe
for z0, z1, xs in ((0.62, 1.32, (-0.6, -0.05)), (0.62, 1.32, (0.05, 0.6))):                # bolted covers on both long faces
    for y, sgn in ((BY0, -1), (BY1, 1)):
        sh.box2((X + xs[0], min(y, y + sgn * 0.012), z0), (X + xs[1], max(y, y + sgn * 0.012), z1), YEL, bevel=0.006, seg=1)
        for zz in (z0 + 0.05, z1 - 0.05):
            sh.bolts((X + xs[0] + 0.05, y + sgn * 0.012, zz), (X + xs[1] - 0.05, y + sgn * 0.012, zz), 5, (0, sgn, 0), r=0.009)
for s in (-1, 1):                                                          # lifting eyes
    sh.torus((X + s * 0.45, AY, 1.52), (0, 1, 0), 0.05, 0.016, DARK, seg=12, rseg=6)
# control station on the goaf side
sh.box2((X - 0.25, BY1, 0.95), (X + 0.25, BY1 + 0.06, 1.3), "paint_black", bevel=0.008, seg=1)
for i, em in enumerate(("emit_green", "emit_red", "emit_amber", "emit_green")):
    sh.cyl((X - 0.18 + i * 0.05, BY1 + 0.06, 1.0), (X - 0.18 + i * 0.05, BY1 + 0.075, 1.0), 0.016, em, sides=10)
sh.lathe(V(X + 0.18, BY1 + 0.06, 1.0), (0, 1, 0), [(0.035, 0), (0.035, 0.02), (0.025, 0.035), (0, 0.04)], "paint_red", sides=14)
# cable connection + loop into the trough (moves with the shearer, lies on the static trough cable)
sh.box2((X + 0.2, AY + 0.25, 1.49), (X + 0.45, AY + 0.45, 1.6), DARK, bevel=0.008, seg=1)
sh.cable([V(X + 0.32, AY + 0.4, 1.6), V(X + 0.3, AY + 0.62, 1.55), V(X + 0.1, AY + 0.74, 1.0), V(X - 0.3, AY + 0.7, 0.72),
          V(X - 1.3, AY + 0.67, 0.67)], 0.045, sides=8)
sh.cable([V(X + 0.38, AY + 0.4, 1.58), V(X + 0.4, AY + 0.66, 1.5), V(X + 0.25, AY + 0.8, 0.95), V(X - 0.2, AY + 0.79, 0.7),
          V(X - 1.3, AY + 0.785, 0.655)], 0.028, m="hose_yellow", sides=8)
# ranging arms (static on the shearer): left high, right low
PIV_Z, AR = 1.15, 1.2
arms = {}
for s, ang in ((-1, 45.0), (1, -20.0)):
    pv = V(X + s * 0.75, 0, PIV_Z)
    a = math.radians(ang)
    dc = pv + V(s * AR * math.cos(a), 0, AR * math.sin(a))
    arms[s] = dc
    u = (dc - pv).normalized()
    nrm = V(-u.z, 0, u.x)
    pts = []
    for k in range(9):                                   # capsule outline (pivot end r .23, drum end r .17)
        t = math.pi / 2 + math.pi * k / 8
        pts.append(pv + (u * math.cos(t) + nrm * math.sin(t)) * 0.23)
    for k in range(9):
        t = -math.pi / 2 + math.pi * k / 8
        pts.append(dc + (u * math.cos(t) + nrm * math.sin(t)) * 0.17)
    pts = [V(p.x, -2.09, p.z) for p in pts]
    sh.slab(pts, 0.22, YEL, normal=(0, 1, 0), bevel=0.02, seg=2)
    sh.cyl(V(pv.x, -1.96, pv.z), V(pv.x, -2.22, pv.z), 0.21, DARK, sides=24, bevel=0.01, seg=1)
    sh.bolt_ring(V(pv.x, -2.22, pv.z), (0, -1, 0), 0.16, 8, r=0.012)
    sh.cyl(V(dc.x, -1.98, dc.z), V(dc.x, -2.22, dc.z), 0.25, DARK, sides=24, bevel=0.012, seg=2)
    mid = pv.lerp(dc, 0.55)
    sh.box((mid.x, -2.205, mid.z), (0.5, 0.012, 0.16), YEL, rot=(0, -ang, 0))
    sh.bolts(V(pv.x, -2.205, pv.z) + u * 0.35 + nrm * 0.12, V(pv.x, -2.205, pv.z) + u * 1.0 + nrm * 0.12, 4, (0, -1, 0), r=0.01)
    if s < 0:                                            # lift cylinder: under the raised arm, over the lowered one
        lo, hi = V(X + s * 0.55, -2.06, 0.62), pv.lerp(dc, 0.5) + nrm * 0.14
    else:
        lo, hi = V(X + s * 0.6, -2.06, 1.35), pv.lerp(dc, 0.5) + nrm * 0.15
    hi = V(hi.x, -2.06, hi.z)
    sh.hyd_cyl(lo, hi, 0.07, 0.04, m_barrel=YEL, frac=0.55, ports=False)
    for k in range(3):                                   # spray manifold on the arm tip
        sh.cyl(V(dc.x, -2.23, dc.z) + nrm * (0.2 + k * 0.03), V(dc.x, -2.3, dc.z) + nrm * (0.2 + k * 0.03), 0.01, "brass", sides=6)
sh.led_light(V(X - 0.95, AY - 0.25, 1.2), (-1, -0.3, 0.05), w=0.26, h=0.11)
sh.led_light(V(X + 0.95, AY - 0.25, 1.2), (1, -0.3, -0.1), w=0.26, h=0.11)
shearer = sh.finish(root)

# =============================================================================== spiral-vane drums
DR, DCORE = 0.6, 0.34
DY0, DY1 = -2.22, -2.87


def drum(name, c, hand):
    p = Part(name, pivot=c, axis=(0, 1, 0))
    cy = c.y
    p.cyl((c.x, DY0, c.z), (c.x, DY1 + 0.06, c.z), DCORE, DARK, sides=20)
    p.lathe(V(c.x, DY1 + 0.06, c.z), (0, -1, 0), [(DCORE, 0), (DR - 0.02, 0.0), (DR, 0.015), (DR, 0.05), (DR - 0.03, 0.065), (0.12, 0.065),
                                                    (0.0, 0.07)], DARK, sides=28)
    p.cyl((c.x, DY0 + 0.005, c.z), (c.x, DY0 - 0.04, c.z), DCORE + 0.06, DARK, sides=20, bevel=0.006, seg=1)
    nv, steps = 3, 14
    for j in range(nv):
        rings = []
        for i in range(steps + 1):
            t = i / steps
            th = j * math.tau / nv + hand * t * math.radians(150)
            y = DY0 - 0.06 - t * (DY0 - DY1 - 0.14)
            ca, sa = math.cos(th), math.sin(th)
            ring = []
            for rr, dy in ((DCORE - 0.01, -0.028), (DR - 0.05, -0.028), (DR - 0.05, 0.028), (DCORE - 0.01, 0.028)):
                ring.append(V(c.x + ca * rr, y + dy, c.z + sa * rr))
            rings.append(ring)
        p.loft(rings, DARK, closed=True, caps=True)
        for i in range(1, steps, 3):                    # picks along the vane tip
            t = i / steps
            th = j * math.tau / nv + hand * t * math.radians(150)
            y = DY0 - 0.06 - t * (DY0 - DY1 - 0.14)
            rad = V(math.cos(th), 0, math.sin(th))
            tan = V(-math.sin(th), 0, math.cos(th)) * hand
            q = V(c.x, y, c.z) + rad * (DR - 0.05)
            pd = (rad + tan * 0.35).normalized()
            p.box(q + rad * 0.02, (0.05, 0.05, 0.05), DARK, rot=lib.frame(pd, (0, 1, 0)))
            p.cyl(q + pd * 0.035, q + pd * 0.1, 0.019, STEEL, r1=0.012, sides=8)
            p.cyl(q + pd * 0.1, q + pd * 0.125, 0.012, "cast_iron", r1=0.0, sides=8)
    for k in range(10):                                  # end-ring picks (face side, splayed outward)
        th = k * math.tau / 10
        rad = V(math.cos(th), 0, math.sin(th))
        tan = V(-math.sin(th), 0, math.cos(th)) * hand
        q = V(c.x, DY1 + 0.03, c.z) + rad * (DR - 0.01)
        pd = (rad + tan * 0.3 + V(0, -0.45, 0)).normalized()
        p.box(q, (0.05, 0.05, 0.05), DARK, rot=lib.frame(pd, (0, 1, 0)))
        p.cyl(q + pd * 0.03, q + pd * 0.095, 0.019, STEEL, r1=0.012, sides=8)
        p.cyl(q + pd * 0.095, q + pd * 0.12, 0.012, "cast_iron", r1=0.0, sides=8)
    return p.finish(shearer)


drum_l = drum("drum_l", V(arms[-1].x, -2.545, arms[-1].z), 1)
drum_r = drum("drum_r", V(arms[1].x, -2.545, arms[1].z), -1)

# =============================================================================== gauges, decals, screens
dec = Part("decals", grime=False, smooth=False)
gz = Part("gauges")
needles = []
for k, x in enumerate(SHX):
    vbx = V(x + vb.x, vb.y - 0.26, vb.z + 0.27)
    needles.append(lib.gauge(gz, dec, ATL, "g_leg", vbx + V(0, -0.0, 0), (0, -1, 0), (0, 0, 1), 0.055, f"needle_{k}", root))
    lib.decal(dec, (x + vb.x, vb.y - 0.261, vb.z + 0.03), (0, -1, 0), (0, 0, 1), 0.2, 0.1, "custom_screen_ls9",
              lib.cell_uv(f"scr_{ID}", f"c{('087', '088', '089')[k]}"), off=0.0)
    lib.decal_cell(dec, ATL, f"n{('087', '088', '089')[k]}", (x, 2.0 + cn.y * 0.13, 2.0 + cn.z * 0.13), cn, cdir * -1, w=0.5)
    lib.decal_cell(dec, ATL, "warn_crush", leg_point(LEGS[1][1], LEGS[1][2], 1.0) + V(x, -0.16, 0), (0, -1, 0), (0, 0, 1), w=0.2)
    lib.stripe(dec, (x, -2.121, CTOP - 0.05), (0, -1, 0), (0, 0, 1), 1.4, 0.08, period=0.16)
    hb = cs0.lerp(cs1, 0.93) + cn * 0.131
    lib.stripe(dec, (x, hb.y, hb.z), cn, -cdir, 1.3, 0.1, period=0.2)
    mk = cs0.lerp(cs1, 0.18) + cn * 0.131
    lib.decal_cell(dec, ATL, "mk", (x, mk.y, mk.z), cn, -cdir, h=0.1)
static.append(gz.finish(root))
for x0, x1 in PANS:
    lib.decal_cell(dec, ATL, "afc", ((x0 + x1) / 2, AY + 0.531, 0.72), (0, 1, 0), (0, 0, 1), w=0.9)
lib.decal_cell(dec, ATL, "plate", (2.52, AY + 0.951, 0.35), (0, 1, 0), (0, 0, 1), w=0.26)
lib.decal_cell(dec, ATL, "warn_hyd", (-2.52, AY + 0.951, 0.35), (0, 1, 0), (0, 0, 1), w=0.32)
static.append(dec.finish(root))
ds = Part("decals_shearer", grime=False, smooth=False, pivot=(SX0, AY, 0))
lib.decal_cell(ds, ATL, "mk", (X - 0.33, BY1 + 0.013, 1.12), (0, 1, 0), (0, 0, 1), h=0.11)
lib.decal_cell(ds, ATL, "badge", (X + 0.4, BY1 + 0.013, 0.78), (0, 1, 0), (0, 0, 1), w=0.32)
lib.decal_cell(ds, ATL, "mk", (X, BY0 - 0.013, 1.0), (0, -1, 0), (0, 0, 1), h=0.17)
lib.decal_cell(ds, ATL, "plate", (X - 0.33, BY1 + 0.013, 0.8), (0, 1, 0), (0, 0, 1), w=0.2)
lib.decal(ds, (X, BY1 + 0.061, 1.17), (0, 1, 0), (0, 0, 1), 0.2, 0.11, "custom_screen_ls9", lib.cell_uv(f"scr_{ID}", "shearer"), off=0.0)
for s in (-1, 1):
    dc = arms[s]
    pv = V(X + s * 0.75, 0, PIV_Z)
    u = (dc - pv).normalized()
    mid = pv.lerp(dc, 0.42)
    lib.decal_cell(ds, ATL, "warn_drum", V(mid.x, -2.2125, mid.z), (0, -1, 0), (0, 0, 1), w=0.26)
    lib.stripe(ds, (X + s * 0.5, BY0 - 0.013, 0.56), (0, -1, 0), (0, 0, 1), 0.5, 0.08, period=0.16)
lib.decal_cell(ds, ATL, "l_estop", (X + 0.18, BY1 + 0.062, 1.07), (0, 1, 0), (0, 0, 1), w=0.08)
ds.finish(shearer)

# =============================================================================== empties
fxl = V(arms[-1].x, DY1 - 0.05, arms[-1].z)
fxr = V(arms[1].x, DY1 - 0.05, arms[1].z)
lib.empty("fx_work", fxl, shearer)
lib.empty("fx_work_1", fxr, shearer)
lib.empty("fx_ore", (2.55, AY, 0.62), root)
for k, x in enumerate(SHX):
    lib.empty(f"light_{k}", (x, -1.1, 2.6), root, aim=(0, -0.25, -1.0))
lib.empty("light_3", (SX0 - 1.0, AY - 0.25, 1.2), shearer, aim=(-1, -0.3, 0.05))
lib.empty("op", (0.875, -0.25, 0), root, face=(0, -1, 0))
lib.empty("snd", (SX0, AY, 1.0), shearer)

# =============================================================================== animation
lib.track(shearer, "Work", "location", 0, [(0, -1.0), (90, 1.0), (WORK, -1.0)])
lib.spin(drum_l, "Work", WORK, turns=4)
lib.spin(drum_r, "Work", WORK, turns=-4)
for o, s0 in flights:                                       # each segment advances STEP pitches along the loop
    dist = STEP * PITCH
    marks = {0.0, 1.0}
    a = XR - XL
    corners = [a, a + (ZT - ZB), 2 * a + (ZT - ZB), LOOP]
    for c in corners:
        for base in (0.0, LOOP):
            d = c + base - s0
            if 0 < d < dist:
                marks.add(d / dist)
    for t in sorted(marks):
        p = loop_pos(s0 + t * dist)
        lib.key(o, "Work", "location", 0, t * WORK, p.x, "LINEAR")
        lib.key(o, "Work", "location", 2, t * WORK, p.z - ZT, "LINEAR")
for k, oc in enumerate(canopies):                           # canopies breathe +-1.2 cm, phase-shifted
    pts = []
    for i in range(9):
        f = i * WORK / 8
        pts.append((f, 0.012 * math.sin(math.tau * (i / 8 + k / 3))))
    lib.track(oc, "Work", "location", 2, pts)
for k, nd in enumerate(needles):
    lib.needle_keys(nd, "Work", WORK, 168 + k * 6, 4, step=8, seed=31 + k)
for o in [shearer, drum_l, drum_r] + canopies + needles + [f for f, _ in flights]:
    lib.hold(o, "Idle", IDLE)
lib.bake_clips()
if "--debug" in args:
    for fr in (0, 54):
        lib.pose_at("Work", fr)
        bpy.context.view_layer.update()
        for o in lib.descendants(root):
            if o.type != "MESH":
                continue
            pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
            zmax = max(p.z for p in pts)
            ymin = min(p.y for p in pts)
            ymax = max(p.y for p in pts)
            if zmax > 3.05 or fr == 54 and o.name.startswith(("flight_00", "flight_01", "shield_canopy", "drum", "shearer")):
                print(f"[dbg] f{fr} {o.name}: z<= {zmax:.2f} y {ymin:.2f}..{ymax:.2f} loc {tuple(round(v, 3) for v in o.location)}")
    lib.clear_pose()

# =============================================================================== merge, grime, export
body = lib.merge(static, "body")
meshes = [o for o in lib.descendants(root) if o.type == "MESH" and o.get("grime")]
lib.bake_grime(meshes, distance=0.4, samples=48, floor_z=0.0)
path, js, anims, names = lib.export(root, OUT)
size = lib.report(root, "<= 5.6 W x 7.6 L x 3.9 H")
need = [ID, "fx_work", "fx_work_1", "fx_ore", "light_0", "light_1", "light_2", "op", "snd"]
print("[mb] missing nodes:", [n for n in need if n not in names])

if PREVIEW:
    lib.previews(ID, root, [
        dict(name="rear", az=205, el=18, fill=0.95),
        dict(name="side", az=90, el=8, fill=0.95),
        dict(name="walkway", az=160, el=10, target=(0.3, -1.2, 1.1), dist=3.4, lens=30),
        dict(name="drum", az=128, el=8, target=(arms[1].x, -2.4, 0.75), dist=2.3, lens=35),
        dict(name="shields", az=150, el=4, target=(0.0, 0.8, 1.5), dist=4.2, lens=28),
    ], frame=40)
