"""Sutter Works GW-11 Gold Wash Plant (Level-4 cavern machine).

    systemd-run --user --scope -q -p MemoryMax=3G -p MemorySwapMax=0 \
        bl assets/machines_b/washplant.py -- public/models/machines/washplant [--no-preview]

Blender axes, front (ore comes in) = -Y = three.js +Z. Process line, folded to fit 6 x 10 m:
  front-right   grizzly feed hopper over a jaw crusher (twin flywheels, V-belt drive, motor)   fx_work
  diagonal      chevron-belt conveyor (30 deg) up to the trommel feed chute
  left          rotating perforated trommel on trunnion rollers, spray bar, undersize hopper,
                oversize chute + pile, steel walkway with handrails + stairs, control cabinet (op)
  middle/right  launder across to a long riffled sluice with running water
  rear-right    Wilfley shaking table (oscillates) with a gold band, catch pan of gold concentrate fx_ore
  rear-left     process-water tank, pump, valved pipework
Sutter Works livery: green structure, yellow guarding, galvanized wet steel.
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import bk  # noqa: E402
import lib  # noqa: E402
from lib import Part, V  # noqa: E402

ID = "washplant"
args = bk.args()
OUT = os.path.abspath(args[0]) if args and not args[0].startswith("--") else os.path.join(lib.PROJECT, "public/models/machines", ID)
PREVIEW = "--no-preview" not in args

bk.reset()
bpy.context.scene.render.fps = lib.FPS
WORK, IDLE = 120, 60
ATL = ID
lib.label(f"label_{ID}_decals", os.path.join(lib.DECALS, f"{ID}.png"))
lib.std_materials()
lib.water_material()
lib.trommel_material()
lib.label("custom_screen_gw11", os.path.join(lib.DECALS, f"scr_{ID}.png"), mode="OPAQUE", emit=2.2, rough=0.25)

GRN, YEL, DARK, STEEL, GALV = "paint_green", "paint_yellow", "steel_dark", "steel", "galvanized"
root = lib.root(ID)
static = []
rng = random.Random(5)

CRX, CRY = 1.75, -3.8                         # jaw crusher centre (plan)
TX = -1.55                                    # trommel axis x
T0, T1 = V(TX, 0.0, 2.45), V(TX, 3.6, 2.15)   # trommel axis: feed -> discharge
TAX = (T1 - T0).normalized()
TLEN = (T1 - T0).length
TR = 0.62
SX = 1.35                                     # sluice centreline x
S0, S1 = V(SX, 0.15, 1.42), V(SX, 3.35, 1.0)  # sluice bed: head -> tail
SAX = (S1 - S0).normalized()
SLEN = (S1 - S0).length


def tpt(h, r=0.0, ang=0.0):
    """Point on the trommel: h metres along the axis, radius r, angle ang (deg, 90 = top)."""
    a, b = lib.perp(TAX)
    t = math.radians(ang)
    up = V(0, 0, 1) - TAX * TAX.z
    up.normalize()
    side = TAX.cross(up).normalized()
    return T0 + TAX * h + (side * math.cos(t) + up * math.sin(t)) * r


# =============================================================================== skid base
sk = Part("skid")
for x in (-2.85, 2.85):
    sk.ibeam(V(x, -4.75, 0.11), V(x, 4.75, 0.11), 0.22, 0.16, GRN)
for y in (-4.7, -2.4, 0.0, 2.4, 4.7):
    sk.ibeam(V(-2.85, y, 0.11), V(2.85, y, 0.11), 0.2, 0.14, GRN)
sk.deck(V(-2.95, -4.8, 0.2), V(2.95, 4.8, 0.23), top="custom_chequer", side=STEEL)
for x in (-2.95, 2.95):                                                  # kick plates along the skid edges
    sk.box2((min(x, x - 0.02 * (1 if x > 0 else -1)), -4.8, 0.23), (max(x, x - 0.02 * (1 if x > 0 else -1)), 4.8, 0.33), GRN)
# MCC / switch room container in the front-left corner
MCX, MCY = -1.85, -3.55
sk.box2((MCX - 0.95, MCY - 1.15, 0.23), (MCX + 0.95, MCY + 1.15, 2.55), GRN, bevel=0.02, seg=2)
for k in range(9):                                                       # corrugations on the long sides
    y = MCY - 1.0 + k * 0.25
    for s_ in (-1, 1):
        sk.box2((MCX + s_ * 0.95 - 0.015, y - 0.05, 0.3), (MCX + s_ * 0.95 + 0.015, y + 0.05, 2.45), GRN)
sk.box2((MCX - 0.97, MCY - 1.17, 2.5), (MCX + 0.97, MCY + 1.17, 2.6), GRN, bevel=0.01, seg=1)
sk.box2((MCX + 0.955, MCY + 0.2, 0.3), (MCX + 0.975, MCY + 1.0, 2.25), "paint_grey", bevel=0.006, seg=1)     # door
sk.box2((MCX + 0.975, MCY + 0.85, 1.15), (MCX + 1.0, MCY + 0.92, 1.3), "paint_black")
sk.grille(V(MCX + 0.965, MCY - 0.6, 1.9), 0.6, 0.35, 5, (1, 0, 0), "paint_grey", depth=0.02)
sk.box2((MCX - 0.5, MCY - 1.35, 1.7), (MCX + 0.5, MCY - 1.15, 2.2), "paint_grey", bevel=0.01, seg=1)           # AC unit
sk.cyl(V(MCX + 0.7, MCY + 0.7, 2.6), V(MCX + 0.7, MCY + 0.7, 2.66), 0.07, "paint_black", sides=12)
sk.lathe(V(MCX + 0.7, MCY + 0.7, 2.66), (0, 0, 1), [(0.06, 0), (0.06, 0.1), (0.04, 0.14), (0, 0.15)], "emit_amber", sides=12)
sk.box2((MCX + 0.95, MCY - 0.15, 0.24), (CRX - 0.5, MCY + 0.15, 0.27), GALV)
for k in range(3):
    sk.cable([V(MCX + 0.95, MCY - 0.08 + k * 0.08, 0.6), V(MCX + 1.05, MCY - 0.08 + k * 0.08, 0.29), V(CRX - 0.6, MCY - 0.08 + k * 0.08, 0.29),
              V(CRX - 0.45, -4.4 + k * 0.05, 0.5)], 0.02, sides=6)
# fire extinguisher on the MCC wall
fx_, fy_ = MCX + 1.0, MCY - 0.3
sk.lathe(V(fx_ + 0.06, fy_, 0.85), (0, 0, 1), [(0.0, 0), (0.075, 0), (0.08, 0.02), (0.08, 0.42), (0.06, 0.48), (0.025, 0.5), (0, 0.5)], "paint_red", sides=16)
sk.cyl(V(fx_ + 0.06, fy_, 1.35), V(fx_ + 0.06, fy_, 1.43), 0.022, STEEL, sides=8)
sk.box((fx_ + 0.1, fy_, 1.42), (0.1, 0.02, 0.015), "paint_black", rot=(0, -12, 0))
static.append(sk.finish(root))

# =============================================================================== feed hopper + grizzly (front right)
hp = Part("hopper")
HZ0, HZ1 = 1.95, 2.65
top = [V(CRX - 0.95, -4.75, HZ1), V(CRX + 0.95, -4.75, HZ1), V(CRX + 0.95, -3.35, HZ1), V(CRX - 0.95, -3.35, HZ1)]
bot = [V(CRX - 0.4, -4.15, HZ0), V(CRX + 0.4, -4.15, HZ0), V(CRX + 0.4, -3.65, HZ0), V(CRX - 0.4, -3.65, HZ0)]
hp.loft([bot, top], GRN, closed=True, caps=False)
inset = [p + (V(CRX, -4.05, p.z) - p) * 0.03 for p in top]
binset = [p + (V(CRX, -3.9, p.z) - p) * 0.03 for p in bot]
fs = hp.loft([binset, inset], DARK, closed=True, caps=False)
import bmesh  # noqa: E402
bmesh.ops.reverse_faces(hp.bm, faces=fs)
for a_, b_ in ((0, 1), (1, 2), (2, 3), (3, 0)):                                  # top rim
    p, q = top[a_], top[b_]
    d = (q - p)
    hp.box((p + q) / 2 + V(0, 0, 0.04), (abs(d.x) + 0.12, abs(d.y) + 0.12, 0.08) if abs(d.x) > abs(d.y) else (0.12, abs(d.y) + 0.12, 0.08),
           GRN, bevel=0.01, seg=1)
for k in range(8):                                                                 # grizzly bars
    x = CRX - 0.8 + k * 0.23
    hp.prism(V(x, -4.78, HZ1 + 0.12), V(x, -3.32, HZ1 + 0.02), [(-0.025, -0.05), (0.025, -0.05), (0.025, 0.05), (-0.025, 0.05)],
             STEEL, up=(0, 0, 1))
for x in (CRX - 0.95, CRX + 0.95):
    for y in (-4.75, -3.35):
        hp.ibeam(V(x, y, 0.22), V(x, y, HZ1), 0.18, 0.16, GRN, up=(0, 1, 0))
    hp.cyl(V(x, -4.75, 0.5), V(x, -3.35, 1.8), 0.03, GRN, sides=8)
for k in range(3):                                                                 # side stiffeners
    y = -4.55 + k * 0.5
    hp.box((CRX + 0.95 * 0.75 + 0.02, y, (HZ0 + HZ1) / 2 + 0.1), (0.05, 0.06, 0.62), GRN, rot=(0, 30, 0))
for k in range(5):                                                                 # gold-quartz feed resting on the grizzly
    hp.ico(V(CRX - 0.5 + rng.uniform(0, 1.0), rng.uniform(-4.6, -3.5), HZ1 + 0.16), rng.uniform(0.08, 0.15),
           "gold_ore" if k % 2 else "rock_pale", detail=1, scale=(1.2, 1, 0.7), rot=(k * 20, k * 33, k * 51), seed=k + 3)
static.append(hp.finish(root))

# =============================================================================== jaw crusher + drive
cr = Part("crusher")
for s in (-1, 1):                                                                  # side cheeks
    x = CRX + s * 0.38
    cr.slab([V(x, -4.35, 0.35), V(x, -3.2, 0.35), V(x, -3.2, 1.35), V(x, -3.5, 1.85), V(x, -4.35, 1.85)], 0.1, GRN, normal=(1, 0, 0),
            bevel=0.015, seg=2)
    cr.cyl(V(x, -3.55, 1.45), V(x + s * 0.1, -3.55, 1.45), 0.2, STEEL, sides=20, bevel=0.008, seg=1)       # bearing housings
    cr.bolt_ring(V(x + s * 0.1, -3.55, 1.45), (s, 0, 0), 0.15, 6, r=0.016)
cr.box2((CRX - 0.33, -4.35, 0.35), (CRX + 0.33, -4.2, 1.8), GRN, bevel=0.01, seg=1)           # fixed jaw frame
cr.box2((CRX - 0.33, -3.45, 0.55), (CRX + 0.33, -3.25, 1.3), GRN, bevel=0.01, seg=1)          # pitman back
cr.box2((CRX - 0.3, -4.2, 1.82), (CRX + 0.3, -3.5, 1.86), DARK)                              # mouth (dark)
cr.cyl(V(CRX - 0.62, -3.55, 1.45), V(CRX + 0.62, -3.55, 1.45), 0.09, STEEL, sides=16)        # eccentric shaft
cr.box2((CRX - 0.45, -4.4, 0.22), (CRX + 0.45, -3.15, 0.35), DARK, bevel=0.01, seg=1)         # base frame
cr.prism(V(CRX, -3.3, 0.6), V(CRX, -3.05, 0.6), [(-0.35, 0.0), (0.35, 0.0), (0.25, -0.35), (-0.25, -0.35)], DARK, up=(0, 0, 1))  # discharge
cr.cyl(V(CRX, -3.25, 0.95), V(CRX, -2.9, 0.95), 0.03, "chrome", sides=10)                      # tension rod + spring
for k in range(8):
    cr.torus(V(CRX, -3.15 + k * 0.03, 0.95), (0, 1, 0), 0.07, 0.01, "paint_red", seg=12, rseg=4)
# drive motor + V-belts to the right flywheel sheave
MX, MY, MZ = CRX + 0.62, -4.45, 0.55
cr.box2((MX - 0.3, MY - 0.32, 0.22), (MX + 0.42, MY + 0.32, 0.3), DARK)
cr.cyl(V(MX - 0.25, MY, MZ), V(MX + 0.4, MY, MZ), 0.22, "paint_blue", sides=24, bevel=0.01, seg=1)
for k in range(6):
    cr.torus(V(MX - 0.15 + k * 0.09, MY, MZ), (1, 0, 0), 0.222, 0.008, "paint_blue", seg=20, rseg=4)
fly_r, fly_z, fly_y = 0.55, 1.45, -3.55
for k in range(3):                                                                   # belts: stadium loops in the Y-Z plane
    x = MX - 0.38 - k * 0.035 + 0.035
    c0, c1 = V(x, MY, MZ), V(x, fly_y, fly_z)
    dd = (c1 - c0).normalized()
    nn = V(0, -dd.z, dd.y)
    pts = []
    for i in range(9):
        t = math.pi / 2 + math.pi * i / 8
        pts.append(c0 + (dd * math.cos(t) + nn * math.sin(t)) * 0.11)
    for i in range(9):
        t = -math.pi / 2 + math.pi * i / 8
        pts.append(c1 + (dd * math.cos(t) + nn * math.sin(t)) * (fly_r - 0.06))
    pts.append(pts[0])
    cr.tube(pts, 0.012, "rubber", sides=5)
static.append(cr.finish(root))

flywheels = []
for s, name in ((-1, "flywheel_l"), (1, "flywheel_r")):
    fw = Part(name, pivot=(CRX + s * 0.62, fly_y, fly_z), axis=(1, 0, 0))
    cx = CRX + s * 0.62
    fw.lathe(V(cx - 0.07, fly_y, fly_z), (1, 0, 0), [(0.46, 0.0), (fly_r, 0.0), (fly_r, 0.14), (0.46, 0.14), (0.46, 0.0)], "cast_iron", sides=32,
             caps=False)
    if s > 0:
        for k in range(3):
            fw.torus(V(cx - 0.035 + k * 0.035, fly_y, fly_z), (1, 0, 0), fly_r - 0.005, 0.011, DARK, seg=32, rseg=4)
    fw.cyl(V(cx - 0.09, fly_y, fly_z), V(cx + 0.09, fly_y, fly_z), 0.13, "cast_iron", sides=16, bevel=0.01, seg=1)
    for k in range(6):
        t = k * math.tau / 6
        d = V(0, math.cos(t), math.sin(t))
        fw.prism(V(cx, fly_y, fly_z) + d * 0.1, V(cx, fly_y, fly_z) + d * 0.47, [(-0.03, -0.045), (0.03, -0.045), (0.03, 0.045), (-0.03, 0.045)],
                 "cast_iron", up=(1, 0, 0))
    fw.box(V(cx, fly_y, fly_z) + V(0, 0, fly_r - 0.02), (0.15, 0.06, 0.03), YEL)    # painted mark so the spin reads
    flywheels.append(fw.finish(root))
mp = Part("motor_pulley", pivot=(MX - 0.38 + 0.035, MY, MZ), axis=(1, 0, 0))
mp.cyl(V(MX - 0.5, MY, MZ), V(MX - 0.32, MY, MZ), 0.12, "cast_iron", sides=16)
mp.box(V(MX - 0.5, MY, MZ + 0.1), (0.02, 0.04, 0.03), YEL)
motor_pulley = mp.finish(root)

# =============================================================================== diagonal chevron conveyor
C0, C1 = V(CRX, -3.0, 0.55), V(TX + 0.15, -0.38, 2.95)
CU = (C1 - C0).normalized()
CLEN = (C1 - C0).length
RC = lib.frame(CU, (0, 0, 1))
cv = Part("conveyor")
with cv.at(C0, RC):
    for s in (-1, 1):
        cv.channel(V(s * 0.38, -0.1, -0.12), V(s * 0.38, CLEN + 0.1, -0.12), 0.18, 0.06, GRN, up=(s, 0, 0))
    cv.box((0, CLEN / 2, 0.0), (0.62, CLEN - 0.1, 0.014), "rubber")
    cv.box((0, CLEN / 2, -0.26), (0.62, CLEN - 0.25, 0.012), "rubber")                    # return belt
    n = int(CLEN / 0.7)
    for k in range(n + 1):
        y = 0.15 + k * (CLEN - 0.3) / n
        cv.cyl((-0.33, y, -0.055), (0.33, y, -0.055), 0.048, STEEL, sides=10)
        if k % 2 == 0:
            cv.cyl((-0.33, y, -0.3), (0.33, y, -0.3), 0.04, STEEL, sides=8)
            for s in (-1, 1):
                cv.box((s * 0.36, y, -0.18), (0.03, 0.04, 0.26), GRN)
    cv.cyl((-0.36, CLEN, 0.0), (0.36, CLEN, 0.0), 0.15, DARK, sides=18)                    # head pulley
    cv.cyl((0.42, CLEN, 0.0), (0.78, CLEN, 0.0), 0.16, "paint_blue", sides=18, bevel=0.008, seg=1)
    cv.box((0.46, CLEN, 0.0), (0.12, 0.32, 0.32), GRN, bevel=0.01, seg=1)
    cv.box((0, -0.05, 0.12), (0.8, 0.5, 0.3), GRN, bevel=0.01, seg=1)                        # tail skirt box
    for s in (-1, 1):                                                                        # skirt boards
        cv.box((s * 0.33, CLEN * 0.15, 0.08), (0.02, CLEN * 0.3, 0.14), "rubber")
static.append(cv.finish(root))
for t, h in ((0.33, 1.0), (0.7, 2.0)):                                                     # support A-frames
    q = C0.lerp(C1, t)
    ps = Part(f"_leg{t}")
    for s in (-1, 1):
        side = CU.cross(V(0, 0, 1)).normalized() * s * 0.4
        ps.cyl(V(q.x, q.y, 0.2) + side * 1.35, q + side - V(0, 0, 0.25), 0.04, GRN, sides=10)
    ps.box(q - V(0, 0, 0.28), (0.95, 0.12, 0.1), GRN, rot=lib.frame(CU.cross(V(0, 0, 1)), (0, 0, 1)))
    static.append(ps.finish(root))
frame_c = lib.empty("conveyor_frame", C0, root, aim=CU)
CLOOP = 2 * CLEN + 2 * 0.25
NCLT = 10
CP = CLOOP / NCLT


def belt_pos(s):
    s %= CLOOP
    if s < CLEN:
        return V(0, s, 0.0)
    s -= CLEN
    if s < 0.25:
        return V(0, CLEN, -s)
    s -= 0.25
    if s < CLEN:
        return V(0, CLEN - s, -0.25)
    return V(0, 0, -0.25 + s - CLEN)


def cleat(name, seed):
    p = Part(name, pivot=C0)
    with p.at(C0, RC):
        for s in (-1, 1):                                                     # chevron
            p.box((s * 0.14, -0.06, 0.03), (0.3, 0.025, 0.04), "rubber", rot=(0, 0, s * 30))
        for k in range(3):
            p.ico((-0.12 + k * 0.12, -0.18 - (k % 2) * 0.06, 0.07), 0.06 + 0.012 * k, "gold_ore",
                  detail=0, scale=(1.2, 1, 0.75), rot=(k * 30, seed * 40, k * 70), seed=seed * 7 + k)
    return p.finish(frame_c)


cl_a, cl_b = cleat("cleat_a", 1), cleat("cleat_b", 2)
cleats = []
for i in range(NCLT):
    src = cl_b if i % 2 else cl_a
    o = src.copy()
    o.name = f"cleat_{i:02d}"
    bpy.context.scene.collection.objects.link(o)
    bp = belt_pos(i * CP)
    o.location = (bp.x, bp.y, bp.z)
    sp = (i * CP) % CLOOP
    sc_ = 1.0 if sp <= CLEN else 0.0
    o.scale = (sc_, sc_, sc_)
    o["_rest_loc"] = list(o.location)
    o["_rest_rot"] = list(o.rotation_euler)
    o["_rest_scale"] = [sc_, sc_, sc_]
    cleats.append((o, i * CP))
for src in (cl_a, cl_b):
    bpy.data.objects.remove(src, do_unlink=True)

# =============================================================================== trommel stand, chutes, hopper, rollers (static)
ts = Part("trommel_stand")
for h in (0.55, 3.0):                                                             # trunnion roller pairs + bearing blocks
    for s in (-1, 1):
        q = tpt(h, 0.72 + 0.14, -90 + s * 35)
        ts.box(q - V(0, 0, 0.16), (0.2, 0.22, 0.16), GRN, bevel=0.01, seg=1)
        ts.box(V(q.x, q.y, 0.6) + V(0, 0, (q.z - 0.24 - 0.6) / 2), (0.14, 0.14, q.z - 0.24 - 0.6), GRN)
for y in (0.15, 3.45):
    for s in (-1, 1):
        ts.ibeam(V(TX + s * 0.75, y, 0.22), V(TX + s * 0.75, y, 1.72), 0.16, 0.14, GRN, up=(0, 1, 0))
for s in (-1, 1):
    ts.ibeam(V(TX + s * 0.75, 0.05, 1.62), V(TX + s * 0.75, 3.55, 1.62), 0.16, 0.12, GRN)
    ts.ibeam(V(TX + s * 0.75, 0.05, 0.62), V(TX + s * 0.75, 3.55, 0.62), 0.14, 0.12, GRN)
# undersize hopper (V trough draining to the front)
uh = []
for y, zb in ((0.35, 1.18), (3.25, 1.4)):
    uh.append([V(TX - 0.7, y, 1.72), V(TX - 0.18, y, zb), V(TX + 0.18, y, zb), V(TX + 0.7, y, 1.72)])
ts.loft(uh, GALV, closed=False, caps=False)
ts.loft([[p + V(0, 0, -0.01) for p in reversed(r)] for r in uh], GALV, closed=False, caps=False)
for y in (0.35, 3.25):
    zb = 1.18 if y < 1 else 1.4
    ts.slab([V(TX - 0.7, y, 1.72), V(TX - 0.18, y, zb), V(TX + 0.18, y, zb), V(TX + 0.7, y, 1.72)], 0.02, GALV, normal=(0, 1, 0))
# feed chute from the conveyor head into the trommel mouth
ts.prism(V(TX + 0.12, -0.5, 2.8), tpt(0.35, 0.0) + V(0, 0, 0.0), [(-0.28, -0.04), (0.28, -0.04), (0.28, 0.22), (-0.28, 0.22)], GRN,
         up=(0, 0, 1))
# oversize chute + pile
ts.prism(tpt(TLEN + 0.05, 0.0) - V(0, 0, 0.3), V(TX, 4.25, 0.55), [(-0.35, -0.02), (0.35, -0.02), (0.35, 0.25), (-0.35, 0.25)], GRN,
         up=(0, 0, 1))
# spray bar inside the drum (static) fed from the pipe rack
ts.cyl(tpt(-0.4, 0.35, 90), tpt(TLEN - 0.3, 0.35, 90), 0.03, GALV, sides=8)
for k in range(9):
    q = tpt(0.45 + k * 0.32, 0.35, 90)
    ts.cyl(q, q - V(0, 0, 0.05), 0.012, "brass", sides=6)
# trommel drive: motor + gearbox + chain guard on the feed-end roller
q = tpt(0.55, 0.86, -90 + 35)
ts.box2((q.x + 0.12, q.y - 0.35, 0.6), (q.x + 0.55, q.y + 0.35, 0.95), GRN, bevel=0.01, seg=1)
ts.cyl(V(q.x + 0.3, q.y - 0.3, 1.2), V(q.x + 0.3, q.y + 0.4, 1.2), 0.17, "paint_blue", sides=18, bevel=0.008, seg=1)
ts.box2((q.x + 0.05, q.y - 0.2, q.z - 0.25), (q.x + 0.15, q.y + 0.2, 1.3), YEL, bevel=0.008, seg=1)
lib.pile(ts, V(TX, 4.4, 0.22), 0.55, 0.4, 0.3, ["rock_pale", "gravel", "gold_ore", "rock_pale"], n=22, seed=12)
static.append(ts.finish(root))

rollers = []
for k, (h, s) in enumerate(((0.55, -1), (0.55, 1), (3.0, -1), (3.0, 1))):
    q = tpt(h, 0.72 + 0.14, -90 + s * 35)
    rp = Part(f"roller_{k}", pivot=q, axis=TAX)
    rp.cyl(q - TAX * 0.08, q + TAX * 0.08, 0.14, STEEL, sides=16, bevel=0.008, seg=1)
    rp.cyl(q - TAX * 0.13, q + TAX * 0.13, 0.04, STEEL, sides=8)
    rp.box(q + V(0, 0, 0.13), (0.03, 0.02, 0.02), DARK)
    rollers.append(rp.finish(root))

# =============================================================================== trommel drum (rotates about its inclined axis)
tm = Part("trommel", pivot=T0 + TAX * (TLEN / 2), axis=TAX)
a_, b_ = lib.perp(TAX)
tm.lathe(T0, TAX, [(TR, 0.0), (TR, 0.5), (TR - 0.03, 0.5), (TR - 0.03, 0.0), (TR, 0.0)], STEEL, sides=40, caps=False)          # scrubber
tm.lathe(T0 - TAX * 0.06, TAX, [(0.3, 0.0), (TR + 0.03, 0.0), (TR + 0.03, 0.08), (0.36, 0.08), (0.3, 0.0)], GRN, sides=40, caps=False)
tm.cyl(T0 + TAX * 0.5, T0 + TAX * 3.1, TR - 0.01, "custom_trommel", sides=40, caps=(False, False))                         # screen
tm.lathe(T0 + TAX * 3.1, TAX, [(TR, 0.0), (TR, TLEN - 3.1), (TR - 0.03, TLEN - 3.1), (TR - 0.03, 0.0), (TR, 0.0)], STEEL, sides=40,
         caps=False)
tm.lathe(T1 - TAX * 0.04, TAX, [(0.42, 0.0), (TR + 0.05, 0.0), (TR + 0.05, 0.06), (0.42, 0.06), (0.42, 0.0)], GRN, sides=40, caps=False)
for h in (0.55, 3.0):                                                             # riding tyres
    tm.lathe(T0 + TAX * (h - 0.08), TAX, [(TR, 0.0), (0.72, 0.0), (0.72, 0.16), (TR, 0.16), (TR, 0.0)], STEEL, sides=40, caps=False)
for k in range(5):                                                                # screen stiffener rings
    h = 0.85 + k * 0.55
    tm.lathe(T0 + TAX * h, TAX, [(TR - 0.01, 0.0), (TR + 0.03, 0.0), (TR + 0.03, 0.05), (TR - 0.01, 0.05), (TR - 0.01, 0.0)], GRN, sides=40,
             caps=False)
for k in range(6):                                                                # longitudinal straps
    t = k * math.tau / 6
    d = a_ * math.cos(t) + b_ * math.sin(t)
    tm.prism(T0 + TAX * 0.5 + d * (TR + 0.012), T0 + TAX * 3.1 + d * (TR + 0.012), [(-0.03, -0.012), (0.03, -0.012), (0.03, 0.012), (-0.03, 0.012)],
             GRN, up=tuple(d))
for k in range(4):                                                                # lifter bars inside the scrubber
    t = k * math.tau / 4
    d = a_ * math.cos(t) + b_ * math.sin(t)
    tm.prism(T0 + TAX * 0.05 + d * (TR - 0.08), T0 + TAX * 0.48 + d * (TR - 0.08), [(-0.03, 0.0), (0.03, 0.0), (0.03, 0.06), (-0.03, 0.06)],
             DARK, up=tuple(-d))
for k in range(6):                                                                # ore tumbling inside
    t = math.radians(-90 + rng.uniform(-35, 35))
    d = a_ * math.cos(t) + b_ * math.sin(t)
    tm.ico(T0 + TAX * rng.uniform(0.3, 2.8) + d * (TR - 0.12), rng.uniform(0.06, 0.1), "gold_ore" if k % 2 else "rock_pale", detail=0,
           scale=(1.2, 1, 0.8), seed=50 + k)
trommel = tm.finish(root)

# =============================================================================== launder + sluice (static), water planes
sl = Part("sluice")
L0, L1 = V(TX + 0.2, 0.45, 1.2), V(SX - 0.2, 0.3, 1.47)                       # launder: hopper outlet -> sluice head
LU = (L1 - L0).normalized()
sl.prism(L0, L1, [(-0.18, -0.01), (0.18, -0.01), (0.18, 0.0), (-0.18, 0.0)], GALV, up=(0, 0, 1))
for s in (-1, 1):
    sl.prism(L0 + V(0, s * 0.18, 0), L1 + V(0, s * 0.18, 0), [(-0.006, 0.0), (0.006, 0.0), (0.006, 0.18), (-0.006, 0.18)], GALV, up=(0, 0, 1))
sl.box2((SX - 0.45, -0.15, 1.2), (SX + 0.45, 0.42, 1.72), GALV, bevel=0.01, seg=1)                       # head box
RS = lib.frame(SAX, (0, 0, 1))
with sl.at(S0, RS):
    sl.box((0, SLEN / 2, -0.01), (0.72, SLEN, 0.02), GALV)
    for s in (-1, 1):
        sl.box((s * 0.36, SLEN / 2, 0.12), (0.02, SLEN, 0.27), GALV, bevel=0.003, seg=1)
        sl.box((s * 0.37, SLEN / 2, 0.255), (0.04, SLEN, 0.015), GALV)
    sl.box((0, SLEN / 2, 0.006), (0.68, SLEN - 0.1, 0.012), "rubber")                                    # riffle matting
    for k in range(22):                                                                                  # riffles
        y = 0.25 + k * (SLEN - 0.4) / 21
        sl.angle_iron(V(-0.34, y, 0.012), V(0.34, y, 0.012), 0.035, STEEL, up=(0, 0, 1))
        for j in range(rng.randint(1, 3)):                                                               # trapped gold
            sl.box((rng.uniform(-0.3, 0.3), y - 0.02, 0.016), (0.012, 0.01, 0.006), "gold", rot=(0, 0, rng.uniform(0, 90)))
for t in (0.1, 0.5, 0.9):                                                                                # sluice legs
    q = S0.lerp(S1, t)
    for s in (-1, 1):
        sl.cyl(V(q.x + s * 0.32, q.y, 0.22), V(q.x + s * 0.32, q.y, q.z - 0.02), 0.035, GRN, sides=10)
    sl.box((q.x, q.y, q.z - 0.04), (0.8, 0.06, 0.05), GRN)
static.append(sl.finish(root))


def water_strip(name, p0, axis, length, width, z_off=0.0, period=0.5, extra=0.5):
    """Flowing sheet along `axis` from p0; UVs repeat every `period` m so a one-period slide loops seamlessly."""
    R = lib.frame(axis, (0, 0, 1))
    w = Part(name, pivot=p0, grime=False, smooth=False)
    with w.at(p0, R):
        L = length + extra
        co = [(-width / 2, -extra, z_off), (width / 2, -extra, z_off), (width / 2, length, z_off), (-width / 2, length, z_off)]
        w.faces(co, [(0, 1, 2, 3)], "custom_water", [[(0, 0), (width / period, 0), (width / period, L / period), (0, L / period)]])
    return w.finish(root)


wat_s = water_strip("water_sluice", S0, SAX, SLEN, 0.68, z_off=0.05)
wat_l = water_strip("water_launder", L0, LU, (L1 - L0).length, 0.34, z_off=0.05)
# waterfall off the sluice tail into the table feed box
wf = Part("waterfall", pivot=S1 + SAX * 0.0, grime=False, smooth=False)
fall = [S1 + V(-0.3, 0, 0.05), S1 + V(0.3, 0, 0.05), S1 + V(0.3, 0.22, -0.18), S1 + V(-0.3, 0.22, -0.18)]
wf.faces(fall, [(0, 1, 2, 3)], "custom_water", [[(0, 0), (1.2, 0), (1.2, 0.6), (0, 0.6)]])
waterfall = wf.finish(root)

# =============================================================================== shaking table (deck oscillates) + catch pan
TBX, TBY, TBZ = 1.75, 4.08, 0.86
tb = Part("table_base")
tb.box2((TBX - 1.05, TBY - 0.42, 0.22), (TBX + 0.95, TBY + 0.42, 0.62), GRN, bevel=0.015, seg=2)
for x in (TBX - 0.9, TBX + 0.8):
    tb.box2((x - 0.06, TBY - 0.36, 0.62), (x + 0.06, TBY + 0.36, TBZ - 0.08), DARK)
tb.box2((TBX + 1.0, TBY - 0.3, 0.22), (TBX + 1.38, TBY + 0.3, 0.95), GRN, bevel=0.012, seg=2)             # head motion box
tb.cyl(V(TBX + 1.19, TBY - 0.62, 0.62), V(TBX + 1.19, TBY - 0.3, 0.62), 0.15, "paint_blue", sides=18, bevel=0.008, seg=1)
tb.box2((TBX - 1.05, TBY + 0.43, TBZ + 0.02), (TBX + 0.95, TBY + 0.55, TBZ + 0.14), GALV)                # wash-water launder
for k in range(9):
    tb.cyl(V(TBX - 0.95 + k * 0.23, TBY + 0.43, TBZ + 0.08), V(TBX - 0.95 + k * 0.23, TBY + 0.38, TBZ + 0.05), 0.01, "brass", sides=5)
tb.box2((SX - 0.35, 3.38, 0.82), (SX + 0.35, 3.62, 1.0), GALV, bevel=0.006, seg=1)                          # feed box under the falls
# catch pan of gold concentrate at the table's low end, raised so the gold is seen
PX, PY, PZ = 0.25, 4.35, 0.62
for s in (-1, 1):
    for t in (-1, 1):
        tb.cyl(V(PX + s * 0.26, PY + t * 0.26, 0.23), V(PX + s * 0.26, PY + t * 0.26, PZ), 0.03, DARK, sides=8)
tb.box2((PX - 0.32, PY - 0.32, PZ - 0.04), (PX + 0.32, PY + 0.32, PZ), DARK)
tb.lathe(V(PX, PY, PZ), (0, 0, 1), [(0.0, 0.0), (0.3, 0.0), (0.34, 0.02), (0.44, 0.15), (0.46, 0.17), (0.44, 0.17), (0.33, 0.035), (0.0, 0.035)],
         STEEL, sides=36)
tb.ico(V(PX, PY, PZ + 0.03), 1.0, "gold", detail=2, scale=(0.34, 0.34, 0.11), deform=lambda v, r_: V(v.x, v.y, max(v.z, 0) * (1 + r_.uniform(-0.3, 0.3))),
       seed=21)
for k in range(16):                                                                                         # nuggets
    a = rng.uniform(0, math.tau)
    rr = rng.uniform(0.04, 0.34)
    zz = PZ + 0.04 + 0.1 * max(0.0, 1 - (rr / 0.34) ** 2)
    tb.ico(V(PX + math.cos(a) * rr, PY + math.sin(a) * rr, zz), rng.uniform(0.014, 0.03), "gold", detail=1, scale=(1.3, 1, 0.7), seed=30 + k)
tb.prism(V(TBX - 1.05, TBY - 0.2, TBZ - 0.04), V(PX + 0.25, PY - 0.05, PZ + 0.2), [(-0.07, -0.01), (0.07, -0.01), (0.07, 0.06), (-0.07, 0.06)],
         GALV, up=(0, 0, 1))                                                                                 # concentrate launder
tb.cyl(V(PX + 0.5, PY + 0.25, 0.23), V(PX + 0.5, PY + 0.25, 1.45), 0.025, GRN, sides=8)                     # sign post
tb.box2((PX + 0.1, PY + 0.22, 1.2), (PX + 0.9, PY + 0.25, 1.42), "paint_white")
static.append(tb.finish(root))

dk = Part("table_deck", pivot=(TBX, TBY, TBZ))
deck = [V(TBX - 1.0, TBY - 0.42, TBZ), V(TBX + 0.92, TBY - 0.42, TBZ + 0.02), V(TBX + 0.92, TBY + 0.4, TBZ + 0.05), V(TBX - 0.8, TBY + 0.4, TBZ + 0.04)]
dk.slab(deck, 0.04, "paint_white", bevel=0.006, seg=1)
for k in range(14):                                                                  # tapering riffles
    y = TBY - 0.36 + k * 0.055
    L = 1.75 - k * 0.07
    dk.box((TBX - 0.05 + (1.75 - L) / 2, y, TBZ + 0.035 + k * 0.0025), (L, 0.012, 0.012 + (13 - k) * 0.0006), "paint_black")
for k in range(5):                                                                   # gold band on the deck
    dk.box((TBX - 0.7 + k * 0.03, TBY - 0.3 + k * 0.12, TBZ + 0.03), (0.2, 0.05, 0.005), "gold", rot=(0, 0, -20))
dk.faces([V(TBX - 0.95, TBY - 0.38, TBZ + 0.045), V(TBX + 0.85, TBY - 0.38, TBZ + 0.06), V(TBX + 0.85, TBY + 0.36, TBZ + 0.085),
          V(TBX - 0.75, TBY + 0.36, TBZ + 0.075)], [(0, 1, 2, 3)], "custom_water", [[(0, 0), (3.6, 0), (3.6, 1.4), (0, 1.4)]])
dk.box2((TBX + 0.92, TBY - 0.1, TBZ - 0.06), (TBX + 1.02, TBY + 0.1, TBZ + 0.04), DARK)                       # drive rod
table_deck = dk.finish(root)

# =============================================================================== water tank, pump, pipework
wt = Part("water")
WX, WY = -2.25, 4.0
for s in (-1, 1):
    for t in (-1, 1):
        wt.cyl(V(WX + s * 0.42, WY + t * 0.42, 0.22), V(WX + s * 0.42, WY + t * 0.42, 0.6), 0.04, GRN, sides=8)
wt.box2((WX - 0.62, WY - 0.62, 0.6), (WX + 0.62, WY + 0.62, 0.66), GRN)
wt.cyl(V(WX, WY, 0.66), V(WX, WY, 2.45), 0.58, "paint_white", sides=36, bevel=0.02, seg=2)
for z in (1.1, 1.8):
    wt.torus(V(WX, WY, z), (0, 0, 1), 0.585, 0.012, "paint_white", seg=36, rseg=4)
wt.lathe(V(WX, WY, 2.45), (0, 0, 1), [(0.58, 0.0), (0.5, 0.08), (0.12, 0.14), (0.0, 0.14)], "paint_white", sides=36)
wt.ladder(V(WX + 0.62, WY - 0.2, 0.6), V(WX + 0.62, WY - 0.2, 2.5), w=0.36, m=YEL)
PUX, PUY = -1.2, 4.45
wt.box2((PUX - 0.45, PUY - 0.2, 0.22), (PUX + 0.45, PUY + 0.2, 0.3), DARK)
wt.cyl(V(PUX - 0.4, PUY, 0.48), V(PUX + 0.05, PUY, 0.48), 0.16, "paint_blue", sides=18, bevel=0.008, seg=1)
wt.lathe(V(PUX + 0.05, PUY, 0.48), (1, 0, 0), [(0.12, 0.0), (0.2, 0.04), (0.2, 0.18), (0.1, 0.24), (0.0, 0.24)], GRN, sides=18)
pipes = [
    [V(WX + 0.5, WY + 0.3, 0.75), V(PUX - 0.6, PUY, 0.48), V(PUX + 0.29, PUY, 0.48)],
    [V(PUX + 0.18, PUY, 0.7), V(PUX + 0.18, PUY, 3.05), V(PUX + 0.18, 3.7, 3.05), V(TX, 3.7, 3.05), V(TX, 3.3, 2.95)],
    [V(PUX + 0.18, 3.7, 3.05), V(SX - 0.3, 3.7, 3.05), V(SX - 0.3, 0.0, 3.05), V(SX - 0.3, 0.0, 1.75)],
    [V(SX - 0.3, 3.7, 3.05), V(TBX - 1.0, 3.7, 3.05), V(TBX - 1.0, TBY + 0.5, 1.05)],
]
for pl in pipes:
    wt.tube(pl, 0.045, GALV, sides=10)
for p in (V(PUX + 0.18, PUY, 1.6), V(SX - 0.3, 1.5, 3.05), V(TX + 0.6, 3.7, 3.05)):                         # valves with red wheels
    if p.z < 2:
        wt.cyl(p - V(0, 0, 0.08), p + V(0, 0, 0.08), 0.07, GALV, sides=10)
    else:
        wt.box(p, (0.16, 0.16, 0.14), GALV)
    wt.torus(p + V(0, 0, 0.16), (0, 0, 1), 0.08, 0.01, "paint_red", seg=14, rseg=4)
    wt.cyl(p, p + V(0, 0, 0.16), 0.012, STEEL, sides=6)
for y in (0.5, 2.0, 3.7):                                                                                     # pipe rack posts
    wt.cyl(V(SX - 0.3, y, 0.22), V(SX - 0.3, y, 3.0), 0.035, GRN, sides=8)
wt.cyl(V(PUX + 0.18, 3.7, 0.22), V(PUX + 0.18, 3.7, 3.0), 0.035, GRN, sides=8)
static.append(wt.finish(root))

# =============================================================================== walkway, stairs, control cabinet, lights
wk = Part("walkway")
WZ = 1.35
wk.deck(V(-0.82, 0.0, WZ - 0.05), V(-0.12, 3.45, WZ), top="custom_chequer", side=GRN)
for y in (0.1, 1.75, 3.35):
    for x in (-0.78, -0.16):
        wk.box2((x - 0.04, y - 0.04, 0.22), (x + 0.04, y + 0.04, WZ - 0.05), GRN)
wk.handrail([V(-0.14, 0.02, WZ), V(-0.14, 3.43, WZ)], h=1.05, posts=1.15)
wk.handrail([V(-0.8, 3.43, WZ), V(-0.8, 0.02, WZ), V(-0.14, 0.02, WZ)], h=1.05, posts=1.15)
STA, STB = V(-0.47, 3.45, WZ), V(-0.47, 4.7, 0.23)
for k in range(6):
    q = STA.lerp(STB, (k + 0.5) / 6)
    wk.box2((q.x - 0.3, q.y - 0.1, q.z - 0.03), (q.x + 0.3, q.y + 0.1, q.z), "custom_grating")
    wk.box2((q.x - 0.3, q.y + 0.07, q.z - 0.03), (q.x + 0.3, q.y + 0.1, q.z), YEL)
for s in (-1, 1):
    wk.channel(STA + V(s * 0.32, -0.05, -0.05), STB + V(s * 0.32, 0.05, 0.0), 0.14, 0.05, GRN, up=(s, 0, 0))
    wk.tube([STA + V(s * 0.32, 0, 1.0), STB + V(s * 0.32, 0, 1.0)], 0.022, YEL, sides=8)
    wk.cyl(STB + V(s * 0.32, 0, 0), STB + V(s * 0.32, 0, 1.0), 0.022, YEL, sides=8)
# control cabinet at the front of the walkway (faces the operator, op looks -Y at it)
CBX, CBY = -0.47, -0.25
wk.box2((CBX - 0.06, CBY - 0.06, 0.22), (CBX + 0.06, CBY + 0.06, WZ + 0.35), GRN)
wk.box2((CBX - 0.34, CBY - 0.12, WZ + 0.35), (CBX + 0.34, CBY + 0.12, WZ + 1.1), "paint_grey", bevel=0.012, seg=2)
wk.box2((CBX - 0.38, CBY - 0.16, WZ + 1.1), (CBX + 0.38, CBY + 0.2, WZ + 1.14), "paint_grey")
for i, em in enumerate(("emit_green", "emit_red", "emit_amber")):
    wk.cyl(V(CBX - 0.22 + i * 0.08, CBY + 0.12, WZ + 0.48), V(CBX - 0.22 + i * 0.08, CBY + 0.135, WZ + 0.48), 0.02, em, sides=10)
wk.lathe(V(CBX + 0.2, CBY + 0.12, WZ + 0.48), (0, 1, 0), [(0.035, 0), (0.035, 0.02), (0.025, 0.035), (0, 0.04)], "paint_red", sides=14)
# light poles
for x, y, aim in ((CRX + 1.05, -2.9, (-0.5, -0.4, -1.0)), (TX - 1.05, 1.7, (0.6, 0.0, -1.0)), (2.6, 2.4, (-0.6, 0.6, -1.0)),
                  (-2.85, 4.6, (0.3, 1.0, -0.4))):
    wk.cyl(V(x, y, 0.22), V(x, y, 3.25), 0.05, GRN, sides=10)
    wk.cyl(V(x, y, 0.22), V(x, y, 0.27), 0.14, DARK, sides=10)
    wk.led_light(V(x, y, 3.3), aim, w=0.34, h=0.12)
static.append(wk.finish(root))

# =============================================================================== gauges, decals, screen
dec = Part("decals", grime=False, smooth=False)
gz = Part("gauges")
needles = [
    lib.gauge(gz, dec, ATL, "g_amp", V(CBX - 0.15, CBY + 0.121 + 0.0, WZ + 0.9), (0, 1, 0), (0, 0, 1), 0.05, "needle_0", root),
    lib.gauge(gz, dec, ATL, "g_bar", V(PUX + 0.18 + 0.0, PUY - 0.06, 1.25), (0, -1, 0), (0, 0, 1), 0.055, "needle_1", root),
]
static.append(gz.finish(root))
lib.decal(dec, (CBX + 0.1, CBY + 0.121, WZ + 0.86), (0, 1, 0), (0, 0, 1), 0.3, 0.19, "custom_screen_gw11", lib.cell_uv(f"scr_{ID}", "main"),
          off=0.001)
lib.decal_cell(dec, ATL, "l_start", (CBX - 0.14, CBY + 0.121, WZ + 0.56), (0, 1, 0), (0, 0, 1), w=0.14)
lib.decal_cell(dec, ATL, "l_stop", (CBX + 0.2, CBY + 0.121, WZ + 0.56), (0, 1, 0), (0, 0, 1), w=0.14)
hd_ = V(0.55, 0, 0.7).normalized()                                     # hopper +X face (sloped)
hn_ = V(0.7, 0, -0.55).normalized()
lib.decal_cell(dec, ATL, "mk", V(CRX + 0.675, -4.0, 2.3) + hn_ * 0.004, hn_, hd_, w=0.82)
lib.decal_cell(dec, ATL, "badge", (CRX + 0.431, -3.95, 1.0), (1, 0, 0), (0, 0, 1), w=0.34)
lib.decal_cell(dec, ATL, "plate", (CRX + 0.431, -3.95, 0.62), (1, 0, 0), (0, 0, 1), w=0.2)
lib.decal_cell(dec, ATL, "warn_crush", (CRX - 0.431, -3.95, 1.05), (-1, 0, 0), (0, 0, 1), w=0.3)
lib.decal_cell(dec, ATL, "warn_rot", (TX + 0.83, 0.15, 1.2), (1, 0, 0), (0, 0, 1), w=0.29)
lib.decal_cell(dec, ATL, "warn_slip", (-0.47 + 0.35, 4.2, 1.15), (1, 0, 0), (0, 0, 1), w=0.25)
lib.decal_cell(dec, ATL, "ppe", (-0.47, 4.73, 0.95), (0, 1, 0), (0, 0, 1), w=0.36)
lib.decal_cell(dec, ATL, "warn_hv", (CBX + 0.341, CBY, WZ + 0.75), (1, 0, 0), (0, 0, 1), w=0.18)
lib.decal_cell(dec, ATL, "gold", (PX + 0.5, PY + 0.219, 1.31), (0, -1, 0), (0, 0, 1), w=0.76)
lib.decal_wrap(dec, ATL, "mk", V(WX, WY, 0.66), (0, 0, 1), 0.58, 0.0, 1.45, h=0.2, mode="around", ref=(1, 0, 0), segs=12)
lib.decal_wrap(dec, ATL, "water", V(WX, WY, 0.66), (0, 0, 1), 0.58, 0.0, 1.0, h=0.14, mode="around", ref=(1, 0, 0), segs=8)
lib.stripe(dec, (-0.47, 3.451, WZ - 0.02), (0, 1, 0), (0, 0, 1), 0.66, 0.06, period=0.12)
for y in (0.0, 3.45):
    lib.stripe(dec, (-0.47, y + (0.001 if y > 1 else -0.001), WZ - 0.025), (0, 1 if y > 1 else -1, 0), (0, 0, 1), 0.7, 0.05, period=0.1)
static.append(dec.finish(root))

# =============================================================================== empties
lib.empty("fx_work", (CRX, -3.85, 1.95), root)
lib.empty("fx_ore", (PX, PY, PZ + 0.16), root)
for k, (x, y, aim) in enumerate(((CRX + 1.05, -2.9, (-0.5, -0.4, -1.0)), (TX - 1.05, 1.7, (0.6, 0.0, -1.0)), (2.6, 2.4, (-0.6, 0.6, -1.0)),
                                 (-2.85, 4.6, (0.3, 1.0, -0.4)))):
    lib.empty(f"light_{k}", (x, y, 3.24), root, aim=aim)
lib.empty("op", (CBX, 0.35, WZ), root, face=(0, -1, 0))
lib.empty("snd", (CRX, -3.8, 1.2), root)

# =============================================================================== animation
for fw in flywheels:
    lib.spin(fw, "Work", WORK, turns=6)
lib.spin(motor_pulley, "Work", WORK, turns=27)
lib.spin(trommel, "Work", WORK, turns=1)
for k, rl in enumerate(rollers):
    lib.spin(rl, "Work", WORK, turns=-5)
for o, s0 in cleats:
    dist = 4 * CP
    marks = {0.0, 1.0}
    for c in (CLEN, CLEN + 0.25, 2 * CLEN + 0.25, CLOOP):
        for base in (0.0, CLOOP):
            d = c + base - s0
            if 0 < d < dist:
                marks.add(d / dist)
    for t in sorted(marks):
        sp = (s0 + t * dist) % CLOOP
        p = belt_pos(s0 + t * dist)
        vis = 1.0 if (sp <= CLEN + 1e-6 or sp >= CLOOP - 1e-6) else 0.0
        lib.key(o, "Work", "location", 1, t * WORK, p.y, "LINEAR")
        lib.key(o, "Work", "location", 2, t * WORK, p.z, "LINEAR")
        for i in range(3):
            lib.key(o, "Work", "scale", i, t * WORK, vis, "LINEAR")
for w_, ax in ((wat_s, SAX), (wat_l, LU)):                                 # water slides one texture period downstream
    for i in range(3):
        lib.key(w_, "Work", "location", i, 0, lib.rest(w_, "location", i), "LINEAR")
        lib.key(w_, "Work", "location", i, WORK, lib.rest(w_, "location", i) + ax[i] * 0.5, "LINEAR")
lib.track(waterfall, "Work", "scale", 2, [(0, 0.0), (30, 0.12), (60, -0.04), (90, 0.1), (WORK, 0.0)])
pts = []
for i in range(41):                                                        # shaking table: 10 strokes, 12 mm
    pts.append((i * WORK / 40, 0.012 * math.sin(math.tau * 10 * i / 40)))
lib.track(table_deck, "Work", "location", 0, pts, interp="LINEAR")
for k, nd in enumerate(needles):
    lib.needle_keys(nd, "Work", WORK, (150, 160)[k], 6, step=7, seed=70 + k)
anim = flywheels + [motor_pulley, trommel, wat_s, wat_l, waterfall, table_deck] + rollers + needles + [c for c, _ in cleats]
for o in anim:
    lib.hold(o, "Idle", IDLE)
    for i in range(3):
        lib.key(o, "Idle", "scale", i, 0, lib.rest(o, "scale", i), "LINEAR")
        lib.key(o, "Idle", "scale", i, IDLE, lib.rest(o, "scale", i), "LINEAR")
lib.bake_clips()

# =============================================================================== merge, grime, export
body = lib.merge([o for o in static if o.get("grime")], "body")
meshes = [o for o in lib.descendants(root) if o.type == "MESH" and o.get("grime")]
lib.bake_grime(meshes, distance=0.45, samples=48, floor_z=0.0)
path, js, anims, names = lib.export(root, OUT)
size = lib.report(root, "<= 8 W x 10 L x 5.6 H")
need = [ID, "fx_work", "fx_ore", "light_0", "op", "snd"]
print("[mb] missing nodes:", [n for n in need if n not in names])

if PREVIEW:
    lib.previews(ID, root, [
        dict(name="rear", az=200, el=22, fill=0.95),
        dict(name="34", az=40, el=24, fill=0.95),
        dict(name="side", az=-90, el=14, fill=0.95),
        dict(name="sluice", az=150, el=20, target=(1.2, 2.6, 1.0), dist=3.6, lens=32),
        dict(name="crusher", az=70, el=10, target=(CRX, -3.7, 1.3), dist=3.2, lens=32),
    ], frame=40)
