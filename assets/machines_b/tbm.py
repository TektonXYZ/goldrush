"""Kessler MOLE-1 Tunnel Boring Machine (compact hard-rock TBM + backup gantry), Level-4 cavern machine.

    systemd-run --user --scope -q -p MemoryMax=3G -p MemorySwapMax=0 \
        bl assets/machines_b/tbm.py -- public/models/machines/tbm [--no-preview]

Blender axes: front (cutterhead, working end) = -Y = three.js +Z.
  y -4.95..-4.05  5.2 m cutterhead: spokes, face plates, 34 disc cutters, centre cone, buckets, scrapers
  y -4.05..-0.65  shield (on a launch cradle); open tail shows main drive motors, 16 thrust cylinders,
                  segment erector holding a lining segment, conveyor tail hopper
  y -0.40..+4.80  backup gantry on rails: two grated decks, lit control cabin, transformer, MCC,
                  HPU, cable reel, water tank, vent duct + cassette, stairs; inclined belt conveyor to fx_ore
Work 4 s: cutterhead 1 rev, muck clusters ride the belt (closed loop, hidden return), erector nods.
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

ID = "tbm"
args = bk.args()
OUT = os.path.abspath(args[0]) if args and not args[0].startswith("--") else os.path.join(lib.PROJECT, "public/models/machines", ID)
PREVIEW = "--no-preview" not in args

bk.reset()
bpy.context.scene.render.fps = lib.FPS
WORK, IDLE = 120, 60
ATL = ID
lib.label(f"label_{ID}_decals", os.path.join(lib.DECALS, f"{ID}.png"))
lib.std_materials()
lib.label("custom_screen_mole1", os.path.join(lib.DECALS, f"scr_{ID}.png"), mode="OPAQUE", emit=2.2, rough=0.25)

YEL, DARK, STEEL, GALV = "paint_yellow", "steel_dark", "steel", "galvanized"
CZ = 2.8              # machine axis height
RH = 2.6              # cutterhead radius
YF = -4.6             # cutterhead face plane
YB = -3.95            # cutterhead back / shield front
YT = -0.55            # shield tail
RS = 2.55             # shield radius
AXF = V(0, -1, 0)     # forward axis
root = lib.root(ID)
static = []


def pol(r, th, y):
    """Point on a plane normal to Y, at radius r and angle th (deg) around the machine axis."""
    t = math.radians(th)
    return V(r * math.cos(t), y, CZ + r * math.sin(t))


def rad(th):
    t = math.radians(th)
    return V(math.cos(t), 0, math.sin(t))


# =============================================================================== cutterhead (rotates about Y)
ch = Part("cutterhead", pivot=(0, YF, CZ), axis=(0, 1, 0))
ch.lathe(V(0, YB, CZ), AXF, [(2.36, 0.0), (2.52, 0.0), (2.52, 0.43), (2.6, 0.5), (2.6, 0.59), (2.5, 0.67), (2.36, 0.67), (2.36, 0.0)],
         YEL, sides=72, caps=False)
ch.lathe(V(0, YF + 0.02, CZ), AXF, [(2.5, 0.0), (2.6, 0.08), (2.6, 0.1), (2.5, 0.1)], STEEL, sides=72, caps=False)   # wear band
ch.cyl(V(0, -4.14, CZ), V(0, -4.06, CZ), 2.38, DARK, sides=48)
ch.cyl(V(0, -4.1, CZ), V(0, YF, CZ), 0.62, YEL, sides=32, bevel=0.01, seg=1)
ch.lathe(V(0, YF, CZ), AXF, [(0.62, 0), (0.6, 0.04), (0.46, 0.09), (0.22, 0.12), (0.0, 0.13)], YEL, sides=32)
SPOKES = [30 + 60 * k for k in range(6)]
for th in SPOKES:
    c = pol(1.5, th, (YF + 0.02 - 4.12) / 2)
    ch.box(c, (1.78, 0.5, 0.44), YEL, rot=(0, -th, 0), bevel=0.02, seg=2)
    for k in range(5):                                                       # bolted wear strips on the spoke front
        q = pol(0.85 + k * 0.33, th, YF + 0.0)
        ch.box(q, (0.26, 0.02, 0.36), STEEL, rot=(0, -th, 0))
for k in range(6):                                                           # face plates with muck openings
    t0, t1 = SPOKES[k], SPOKES[(k + 1) % 6] + (360 if k == 5 else 0)
    pts = []
    for i in range(9):
        r = 1.92
        half = math.degrees(math.atan2(0.24, r))
        th = t0 + half + (t1 - t0 - 2 * half) * i / 8
        pts.append(pol(r, th, YF + 0.03))
    for i in range(5):
        r = 0.66
        half = math.degrees(math.atan2(0.24, r))
        th = t1 - half - (t1 - t0 - 2 * half) * i / 4
        pts.append(pol(r, th, YF + 0.03))
    ch.slab(pts, 0.06, DARK, normal=(0, 1, 0), bevel=0.008, seg=1)
    mid = (t0 + t1) / 2
    for j in range(4):                                                       # scraper teeth along the opening edge
        th = mid - 18 + j * 12
        q = pol(1.95, th, YF - 0.01)
        ch.box(q, (0.1, 0.09, 0.07), "cast_iron", rot=(0, -th, 0))
    for side in (-1, 1):                                                     # muck buckets at the rim
        th = mid + side * 15
        q = pol(2.2, th, YF + 0.08)
        ch.box(q, (0.36, 0.3, 0.16), DARK, rot=(0, -th, 0), bevel=0.01, seg=1)
        for j in range(3):
            tq = pol(2.08 + j * 0.13, th + side * 3.5, YF - 0.06)
            ch.box(tq, (0.08, 0.06, 0.06), "cast_iron", rot=(0, -th, 0))
for k in range(36):                                                          # hardfacing studs on the rim front
    q = pol(2.56, k * 10 + 5, YF + 0.03)
    ch.box(q, (0.05, 0.04, 0.12), "cast_iron", rot=(0, -(k * 10 + 5), 0))


def cutter(r, th, tilt=0.0, y=YF):
    """17-inch disc cutter in a U saddle: base plate on the face, two cheeks either side of the disc, thick
    disc (axis radial, so it rolls on its circular track) seated two-thirds deep."""
    t_ = math.radians(th)
    a = V(math.cos(t_), 0, math.sin(t_))
    tg = V(-math.sin(t_), 0, math.cos(t_))
    if tilt:
        a = (a * math.cos(math.radians(tilt)) + AXF * math.sin(math.radians(tilt))).normalized()
    w = a.cross(tg).normalized()
    R = Matrix((a, w, tg)).transposed()
    base = pol(r, th, y)
    c = base - AXF * 0.03                      # disc centre 3 cm behind the face: ~18 cm of edge exposed
    ch.box(base + AXF * -0.02, (0.44, 0.07, 0.32), DARK, rot=R, bevel=0.008, seg=1)
    for s_ in (-1, 1):
        ch.box(base + a * s_ * 0.09 + AXF * 0.04, (0.035, 0.17, 0.3), DARK, rot=R, bevel=0.006, seg=1)
        ch.bolt(base + a * s_ * 0.108 + AXF * 0.06, a * s_, r=0.014, m=STEEL)
    ch.lathe(c, a, [(0.0, -0.065), (0.09, -0.065), (0.09, -0.042), (0.17, -0.026), (0.212, -0.007), (0.212, 0.007), (0.17, 0.026),
                    (0.09, 0.042), (0.09, 0.065), (0.0, 0.065)], STEEL, sides=16)


for k in range(4):                                                           # centre (twin) cutters on the nose
    cutter(0.34, k * 90 + 15, y=YF - 0.06)
NFACE = 24
for i in range(NFACE):                                                       # face cutters on concentric tracks
    r = 0.78 + i * (2.22 - 0.78) / (NFACE - 1)
    th = SPOKES[(i * 5) % 6] + (6 if i % 2 else -6)
    cutter(r, th)
for k in range(6):                                                           # gauge cutters, tilted out at the rim
    cutter(2.38, SPOKES[k] + 14, tilt=-35)
cutterhead = ch.finish(root)

# =============================================================================== shield on its launch cradle
sh = Part("shield")
sh.lathe(V(0, YT, CZ), AXF, [(2.47, 0.0), (RS, 0.0), (RS, 3.4), (2.47, 3.4), (2.47, 0.0)], YEL, sides=64, caps=False)
for h, w in ((0.75, 0.1), (0.25, 0.03), (2.75, 0.03)):                       # articulation band + weld seams
    sh.lathe(V(0, YT - h, CZ), AXF, [(RS, 0.0), (RS + 0.015, 0.0), (RS + 0.015, w), (RS, w)], DARK if w > 0.05 else YEL, sides=64,
             caps=False)
sh.lathe(V(0, YT, CZ), AXF, [(2.3, -0.02), (2.47, -0.02), (2.47, 0.14), (2.3, 0.14), (2.3, -0.02)], "rubber", sides=48, caps=False)  # tail brushes
hz = []                                                                      # painted hazard ring at the front edge
for i in range(65):
    t_ = math.tau * i / 64
    hz.append((V(math.cos(t_) * (RS + 0.004), YB + 0.05, CZ + math.sin(t_) * (RS + 0.004)),
               V(math.cos(t_) * (RS + 0.004), YB + 0.33, CZ + math.sin(t_) * (RS + 0.004))))
for i in range(64):
    (a0_, a1_), (b0_, b1_) = hz[i], hz[i + 1]
    u0, u1 = RS * math.tau * i / 64 / 0.28, RS * math.tau * (i + 1) / 64 / 0.28
    f = sh.faces([a0_, b0_, b1_, a1_], [(0, 1, 2, 3)], "label_hazard", [[(u0, 0), (u1, 0), (u1, 1), (u0, 1)]])
    for ff in f:
        ff.normal_update()
        if ff.normal.dot(ff.calc_center_median() - V(0, ff.calc_center_median().y, CZ)) < 0:
            import bmesh as _bm
            _bm.ops.reverse_faces(sh.bm, faces=[ff])
for k in range(32):                                                          # articulation joint bolts
    sh.bolt(pol(RS + 0.015, k * 11.25 + 5, YT - 0.8), rad(k * 11.25 + 5), r=0.02, m=STEEL)
for s in (-1, 1):                                                            # lifting lugs on the crown
    x = s * 0.6
    sh.slab([V(x, -3.4, CZ + RS - 0.02), V(x, -2.9, CZ + RS - 0.02), V(x, -3.0, CZ + RS + 0.16), V(x, -3.3, CZ + RS + 0.16)], 0.05, YEL,
            normal=(1, 0, 0), bevel=0.006, seg=1)
    sh.torus(V(x, -3.15, CZ + RS + 0.11), (1, 0, 0), 0.05, 0.016, DARK, seg=12, rseg=6)
for k in range(10):                                                          # grout ports along the tail
    sh.cyl(pol(RS, 25 + k * 13, YT - 0.25), pol(RS + 0.05, 25 + k * 13, YT - 0.25), 0.03, STEEL, sides=8)
# cradle: two beams + three saddles following the shield curve
for s in (-1, 1):
    sh.ibeam(V(s * 1.25, -4.2, 0.11), V(s * 1.25, -0.45, 0.11), 0.22, 0.22, DARK)
for y in (-3.6, -2.2, -0.9):
    pts = [V(-1.75, y, 0.22), V(1.75, y, 0.22)]
    for i in range(13):
        x = 1.75 - 3.5 * i / 12
        pts.append(V(x, y, CZ - math.sqrt(max(0.0, (RS + 0.01) ** 2 - x * x))))
    sh.slab(pts, 0.06, YEL, normal=(0, 1, 0), bevel=0.006, seg=1)
    sh.box2((-1.8, y - 0.25, 0.0), (1.8, y + 0.25, 0.02), DARK)
# gantry rails + sleepers
for s in (-1, 1):
    sh.prism(V(s * 2.3, -0.7, 0.06), V(s * 2.3, 4.62, 0.06), [(-0.035, 0.0), (0.035, 0.0), (0.035, 0.02), (0.012, 0.03), (0.012, 0.09),
                                                             (0.032, 0.1), (0.032, 0.13), (-0.032, 0.13), (-0.032, 0.1), (-0.012, 0.09),
                                                             (-0.012, 0.03), (-0.035, 0.02)], STEEL, up=(0, 0, 1))
for k in range(10):
    y = -0.6 + k * 0.6
    sh.box2((-2.55, y - 0.1, 0.0), (2.55, y + 0.1, 0.06), "concrete", bevel=0.008, seg=1)
static.append(sh.finish(root))

# =============================================================================== inside the shield: drive, thrust ring, erector
dv = Part("drive")
dv.cyl(V(0, -3.05, CZ), V(0, -2.95, CZ), 2.47, DARK, sides=48)
dv.cyl(V(0, -2.95, CZ), V(0, -2.40, CZ), 1.05, "paint_grey", sides=36, bevel=0.012, seg=2)
dv.bolt_ring(V(0, -2.40, CZ), (0, 1, 0), 0.95, 24, r=0.014)
for k in range(8):                                                           # main drive motors
    th = k * 45 + 22.5
    c0, c1 = pol(1.62, th, -2.95), pol(1.62, th, -2.20)
    dv.cyl(c0, c0 + V(0, 0.08, 0), 0.26, STEEL, sides=20)
    dv.cyl(c0 + V(0, 0.08, 0), c1, 0.21, "paint_blue", sides=20, bevel=0.01, seg=1)
    for j in range(4):
        dv.torus(c0 + V(0, 0.2 + j * 0.13, 0), (0, 1, 0), 0.213, 0.008, "paint_blue", seg=18, rseg=4)
    dv.box(c1 - V(0, 0.25, 0) + rad(th) * 0.22, (0.16, 0.2, 0.12), "paint_blue", rot=(0, -th, 0))
    dv.cable([c1 - V(0, 0.25, 0) + rad(th) * 0.3, c1 + V(0, 0.2, 0) + rad(th) * 0.35, V(rad(th).x * 1.9, -1.2, CZ + rad(th).z * 1.9)], 0.025,
             sides=6)
for k in range(16):                                                          # thrust cylinders
    th = k * 22.5 + 11.25
    b0, b1 = pol(2.18, th, -2.85), pol(2.18, th, -1.65)
    dv.box(pol(2.18, th, -2.90), (0.3, 0.12, 0.26), YEL, rot=(0, -th, 0))
    dv.cyl(b0, b1, 0.105, YEL, sides=14, bevel=0.006, seg=1)
    dv.cyl(b1, b1 + V(0, 0.05, 0), 0.118, YEL, sides=14)
    dv.cyl(b1 + V(0, 0.05, 0), pol(2.18, th, -0.80), 0.065, "chrome", sides=12)
    dv.box(pol(2.2, th, -0.74), (0.3, 0.1, 0.42), DARK, rot=(0, -th, 0), bevel=0.01, seg=1)
# erector ring rail
dv.lathe(V(0, -1.45, CZ), (0, 1, 0), [(1.62, 0.0), (1.78, 0.0), (1.78, 0.14), (1.62, 0.14), (1.62, 0.0)], STEEL, sides=48, caps=False)
# conveyor tail hopper (muck chute from the cutterhead)
dv.prism(V(0, -2.95, CZ - 0.25), V(0, -2.30, CZ - 0.25), [(-0.5, 0.0), (0.5, 0.0), (0.32, -0.42), (-0.32, -0.42)], DARK, up=(0, 0, 1),
         bevel=0.01, seg=1)
# shield interior lights + hose festoon to the gantry
for k in (-1, 1):
    dv.box(pol(2.4, 90 + k * 25, -1.80), (0.08, 1.2, 0.05), "emit_white", rot=(0, -(90 + k * 25), 0))
for k, col in enumerate(("hose_red", "rubber", "hose_yellow", "rubber", "hose_red")):
    x = -1.6 + k * 0.08
    dv.hose(V(x, -1.50, 1.0), V(0, 1, 0), V(-1.3 + k * 0.06, 0.0, 1.45), V(0, -1, 0), 0.022, col, sag=0.25, reach=0.5)
static.append(dv.finish(root))

er = Part("erector", pivot=(0, -1.38, CZ), axis=(0, 1, 0))
er.lathe(V(0, -1.38, CZ), (0, 1, 0), [(1.55, -0.1), (1.68, -0.1), (1.68, 0.1), (1.55, 0.1), (1.55, -0.1)], YEL, sides=48, caps=False)
for th in (60, 120):                                                         # arm + gripper to the segment at 12 o'clock
    er.box(pol(1.85, th, -1.25), (0.35, 0.18, 0.2), YEL, rot=(0, -th, 0), bevel=0.01, seg=1)
er.box(pol(1.9, 90, -1.20), (0.6, 0.24, 0.3), YEL, bevel=0.015, seg=2)
er.hyd_cyl(pol(1.72, 75, -1.20), pol(2.05, 88, -1.15), 0.05, 0.03, m_barrel=YEL, frac=0.55, eye=False, ports=False)
er.hyd_cyl(pol(1.72, 105, -1.20), pol(2.05, 92, -1.15), 0.05, 0.03, m_barrel=YEL, frac=0.55, eye=False, ports=False)
seg = []                                                                     # concrete lining segment in the grip
for h in (-1.65, -0.75):
    ring = []
    for i in range(9):
        th = 62 + 56 * i / 8
        ring.append(pol(2.42, th, h))
    for i in range(9):
        th = 118 - 56 * i / 8
        ring.append(pol(2.12, th, h))
    seg.append(ring)
er.loft(seg, "concrete", closed=True, caps=True)
er.bolt(pol(2.12, 90, -1.20), V(0, 0, -1), r=0.03, m=STEEL)
erector = er.finish(root)

# =============================================================================== belt conveyor (static frame)
P0, P1 = V(0, -2.8, 2.15), V(0, 4.45, 3.2)
U = (P1 - P0).normalized()
LEN = (P1 - P0).length
RC = lib.frame(U, (0, 0, 1))                    # conveyor frame: +Y along the belt, +Z up from the belt
NU = (RC @ V(0, 0, 1)).normalized()
cv = Part("conveyor")
with cv.at(P0, RC):
    for s in (-1, 1):                                                         # stringers
        cv.channel(V(s * 0.56, -0.1, -0.18), V(s * 0.56, LEN + 0.1, -0.18), 0.2, 0.07, STEEL, up=(s, 0, 0))
    cv.prism(V(0, 0.15, 0), V(0, LEN - 0.15, 0), [(-0.53, 0.2), (-0.2, 0.025), (0.2, 0.025), (0.53, 0.2), (0.53, 0.212), (0.2, 0.037),
                                                     (-0.2, 0.037), (-0.53, 0.212)], "rubber", up=(0, 0, 1))      # troughed top belt
    cv.box((0, LEN / 2, -0.22), (1.02, LEN - 0.2, 0.26), GALV, bevel=0.006, seg=1)                               # belt guard (return)
    n = int(LEN / 0.9)
    for k in range(n + 1):                                                    # troughed idler sets
        y = 0.25 + k * (LEN - 0.5) / n
        cv.cyl((-0.19, y, -0.035), (0.19, y, -0.035), 0.055, STEEL, sides=10)
        for s in (-1, 1):
            a0, a1 = V(s * 0.21, y, -0.025), V(s * 0.5, y, 0.14)
            cv.cyl(a0, a1, 0.055, STEEL, sides=10)
        cv.box((0, y, -0.11), (1.1, 0.05, 0.04), DARK)
        for s in (-1, 1):
            cv.box((s * 0.53, y, 0.02), (0.04, 0.05, 0.3), DARK)
    cv.box((0, LEN + 0.05, 0.15), (1.2, 0.5, 0.75), DARK, bevel=0.015, seg=2)                                   # head hood + chute
    cv.prism(V(0, LEN + 0.1, -0.15), V(0, LEN + 0.26, -0.55), [(-0.4, -0.12), (0.4, -0.12), (0.4, 0.12), (-0.4, 0.12)], DARK, up=(0, 1, 0))
    cv.cyl((0.6, LEN + 0.05, 0.1), (1.05, LEN + 0.05, 0.1), 0.2, "paint_blue", sides=18, bevel=0.008, seg=1)    # head drive
    cv.box((0.62, LEN + 0.05, 0.1), (0.14, 0.42, 0.42), YEL, bevel=0.01, seg=1)
    cv.box((0, -0.02, 0.25), (1.15, 0.5, 0.55), DARK, bevel=0.012, seg=1)                                        # tail box
static.append(cv.finish(root))

# muck clusters on a closed loop (top run visible, return hidden in the guard box)
frame_e = lib.empty("conveyor_frame", P0, root, aim=U)
LOOPL = 2 * LEN + 2 * 0.36
NCL = 16
CPITCH = LOOPL / NCL


def belt_pos(s):
    s %= LOOPL
    if s < LEN:
        return V(0, s, 0.0)
    s -= LEN
    if s < 0.36:
        return V(0, LEN, -s)
    s -= 0.36
    if s < LEN:
        return V(0, LEN - s, -0.36)
    s -= LEN
    return V(0, 0, -0.36 + s)


def cluster(name, seed):
    p = Part(name, pivot=P0)
    with p.at(P0, RC):
        p.box((0, 0, 0.055), (0.38, 0.03, 0.035), "rubber")
        for k, (dx, dy, r) in enumerate(((-0.1, -0.1, 0.07), (0.08, -0.2, 0.06), (0.0, -0.32, 0.075), (0.14, -0.38, 0.05))):
            p.ico((dx, dy, 0.05 + r * 0.6), r, "gold_ore" if (k + seed) % 2 else "rock_pale", detail=0, scale=(1.2, 1, 0.8),
                  rot=(k * 40, k * 60 + seed * 10, k * 25), seed=seed * 10 + k)
    return p.finish(frame_e)


c_a, c_b = cluster("muck_a", 1), cluster("muck_b", 2)
clusters = []
for i in range(NCL):
    src = c_b if i % 2 else c_a
    o = src.copy()
    o.name = f"muck_{i:02d}"
    bpy.context.scene.collection.objects.link(o)
    bp = belt_pos(i * CPITCH)
    o.location = (bp.x, bp.y, bp.z)
    o["_rest_loc"] = list(o.location)
    o["_rest_rot"] = list(o.rotation_euler)
    o["_rest_scale"] = [1, 1, 1]
    clusters.append((o, i * CPITCH))
for src in (c_a, c_b):
    bpy.data.objects.remove(src, do_unlink=True)

# =============================================================================== backup gantry
gt = Part("gantry")
GY = (-0.2, 1.4, 3.0, 4.4)
DZ = 1.15                                     # deck height
for y in GY:
    for s in (-1, 1):
        x = s * 2.3
        gt.ibeam(V(x, y, 0.42), V(x, y, 3.72), 0.22, 0.2, YEL, up=(0, 1, 0))
        gt.box2((x - 0.16, y - 0.3, 0.13), (x + 0.16, y + 0.3, 0.42), DARK, bevel=0.012, seg=1)        # bogie
        for dy in (-0.18, 0.18):
            gt.cyl(V(x - 0.12, y + dy, 0.31), V(x + 0.12, y + dy, 0.31), 0.17, STEEL, sides=16, bevel=0.006, seg=1)
        gt.prism(V(x - s * 0.1, y, 3.0), V(x - s * 0.6, y, 3.6), [(-0.05, -0.05), (0.05, -0.05), (0.05, 0.05), (-0.05, 0.05)], YEL,
                 up=(0, 1, 0))                                                                       # knee brace
    gt.ibeam(V(-2.42, y, 3.66), V(2.42, y, 3.66), 0.22, 0.2, YEL, up=(0, 0, 1))
for s in (-1, 1):
    gt.ibeam(V(s * 2.3, GY[0] - 0.12, 3.66), V(s * 2.3, GY[-1] + 0.12, 3.66), 0.2, 0.16, YEL, up=(0, 0, 1))
    for x in (s * 2.3, s * 1.12):
        gt.channel(V(x, GY[0] - 0.1, DZ - 0.12), V(x, GY[-1] + 0.15, DZ - 0.12), 0.18, 0.07, YEL, up=(0, 0, 1))
    for y in GY:
        gt.box2((min(s * 1.12, s * 2.3), y - 0.05, DZ - 0.2), (max(s * 1.12, s * 2.3), y + 0.05, DZ - 0.04), YEL)
        gt.ibeam(V(s * 1.12, y, 0.0), V(s * 1.12, y, DZ - 0.2), 0.14, 0.12, YEL, up=(0, 1, 0))
    x0, x1 = (1.08, 2.58) if s > 0 else (-2.58, -1.08)
    gt.deck(V(x0, GY[0] - 0.12, DZ - 0.04), V(x1, GY[-1] + 0.15, DZ), top="custom_grating", side=STEEL)
    gt.handrail([V(s * 2.56, GY[0] - 0.1, DZ), V(s * 2.56, GY[-1] + 0.12, DZ)], h=1.05, posts=1.2)
    gt.handrail([V(s * 1.1, GY[0] - 0.1, DZ), V(s * 1.1, GY[-1] + 0.12, DZ)], h=1.05, posts=1.2, toe=True)
# stairs down from the left deck (outside, toward the rear)
ST0, ST1 = V(-2.92, 2.4, DZ), V(-2.92, 4.2, 0.0)
nst = 7
for k in range(nst):
    t = (k + 0.5) / nst
    q = ST0.lerp(ST1, t)
    gt.box2((q.x - 0.32, q.y - 0.12, q.z - 0.03), (q.x + 0.32, q.y + 0.12, q.z), "custom_grating")
    gt.box2((q.x - 0.32, q.y + 0.08, q.z - 0.03), (q.x + 0.32, q.y + 0.12, q.z), YEL)
for s in (-1, 1):
    gt.channel(ST0 + V(s * 0.34, -0.15, 0.0), ST1 + V(s * 0.34, 0.05, 0.08), 0.16, 0.06, YEL, up=(s, 0, 0))
    gt.tube([ST0 + V(s * 0.34, -0.1, 1.0), ST1 + V(s * 0.34, 0.1, 1.0)], 0.022, YEL, sides=8)
    for t in (0.0, 0.5, 1.0):
        q = ST0.lerp(ST1, t) + V(s * 0.34, 0, 0)
        gt.cyl(q, q + V(0, 0, 1.0), 0.022, YEL, sides=8)
gt.box2((-2.92 - 0.36, ST1.y + 0.0, 0.0), (-2.92 + 0.36, ST1.y + 0.35, 0.03), "custom_chequer")
gt.box2((-2.58, 2.35, DZ - 0.04), (-2.58 + 0.01, 2.75, DZ), STEEL)
# ---- right deck: operator cabin (lit), MCC cabinets, transformer
CX0, CX1, CY0, CY1, CZ0, CZ1 = 1.22, 2.5, -0.32, 1.72, DZ, 3.38
gt.box2((CX0, CY0, CZ0), (CX1, CY1, CZ0 + 0.06), DARK)                                               # cabin floor
WALL = "paint_white"
gt.box2((CX0, CY0, CZ1 - 0.1), (CX1, CY1, CZ1), WALL, bevel=0.02, seg=2)                              # roof
for (xa, xb, ya, yb) in ((CX0, CX1, CY0, CY0 + 0.06), (CX0, CX1, CY1 - 0.06, CY1)):                   # front/back walls with windows
    gt.box2((xa, ya, CZ0), (xb, yb, CZ0 + 0.85), WALL, bevel=0.01, seg=1)
    gt.box2((xa, ya, CZ1 - 0.25), (xb, yb, CZ1 - 0.1), WALL)
    gt.box2((xa, ya, CZ0 + 0.85), (xa + 0.1, yb, CZ1 - 0.25), WALL)
    gt.box2((xb - 0.1, ya, CZ0 + 0.85), (xb, yb, CZ1 - 0.25), WALL)
    gt.box2((xa + 0.1, (ya + yb) / 2 - 0.006, CZ0 + 0.85), (xb - 0.1, (ya + yb) / 2 + 0.006, CZ1 - 0.25), "glass")
for xa, xb in ((CX0, CX0 + 0.06), (CX1 - 0.06, CX1)):                                                 # side walls
    gt.box2((xa, CY0, CZ0), (xb, CY1, CZ0 + 0.85), WALL, bevel=0.01, seg=1)
    gt.box2((xa, CY0, CZ1 - 0.25), (xb, CY1, CZ1 - 0.1), WALL)
    for y0, y1 in ((CY0, CY0 + 0.1), (0.62, 0.78), (CY1 - 0.1, CY1)):
        gt.box2((xa, y0, CZ0 + 0.85), (xb, y1, CZ1 - 0.25), WALL)
    for y0, y1 in ((CY0 + 0.1, 0.62), (0.78, CY1 - 0.1)):
        gt.box2(((xa + xb) / 2 - 0.006, y0, CZ0 + 0.85), ((xa + xb) / 2 + 0.006, y1, CZ1 - 0.25), "glass")
gt.box2((CX0 - 0.02, CY0 - 0.02, CZ0 + 0.84), (CX1 + 0.02, CY1 + 0.02, CZ0 + 0.88), YEL)              # yellow belt line
gt.box2((CX0 + 0.12, CY0 + 0.08, CZ0 + 0.06), (CX1 - 0.12, CY0 + 0.6, CZ0 + 0.78), "paint_grey", bevel=0.01, seg=1)   # console
gt.box2((CX0 + 0.15, CY0 + 0.1, CZ0 + 0.78), (CX1 - 0.15, CY0 + 0.3, CZ0 + 1.15), "paint_black", bevel=0.01, seg=1)   # screen bank
gt.box2((CX0 + 0.25, CY0 + 0.6, CZ1 - 0.13), (CX1 - 0.25, CY1 - 0.4, CZ1 - 0.1), "emit_warm")                        # ceiling light
gt.box2((1.65, 0.75, CZ0 + 0.06), (2.05, 1.15, CZ0 + 0.48), "plastic_black", bevel=0.02, seg=2)                      # seat
gt.box2((1.65, 1.1, CZ0 + 0.48), (2.05, 1.2, CZ0 + 1.05), "plastic_black", bevel=0.02, seg=2)
gt.box2((1.45, 0.2, CZ1), (2.25, 1.0, CZ1 + 0.32), "paint_grey", bevel=0.02, seg=2)                                   # roof AC
gt.grille(V(1.85, 1.005, CZ1 + 0.16), 0.6, 0.22, 4, (0, 1, 0), "paint_grey", depth=0.02)
gt.cyl(V(2.32, 1.4, CZ1), V(2.32, 1.4, CZ1 + 0.06), 0.07, "paint_black", sides=12)                                  # beacon
gt.lathe(V(2.32, 1.4, CZ1 + 0.06), (0, 0, 1), [(0.06, 0), (0.06, 0.1), (0.04, 0.14), (0, 0.15)], "emit_amber", sides=12)
gt.box2((CX1 + 0.0, 0.62, CZ0 + 0.9), (CX1 + 0.03, 0.78, CZ0 + 1.0), "paint_black")                                 # door handle side
# MCC cabinets along the right deck
for k in range(3):
    y0 = 1.95 + k * 0.4
    gt.box2((2.0, y0, DZ), (2.5, y0 + 0.38, DZ + 2.0), "paint_grey", bevel=0.01, seg=1)
    gt.box2((1.98, y0 + 0.03, DZ + 0.08), (2.0, y0 + 0.35, DZ + 1.92), "paint_grey")
    gt.box2((1.965, y0 + 0.3, DZ + 0.9), (1.98, y0 + 0.33, DZ + 1.1), "paint_black")
    for j, em in enumerate(("emit_green", "emit_amber")):
        gt.cyl(V(1.98, y0 + 0.1 + j * 0.08, DZ + 1.7), V(1.965, y0 + 0.1 + j * 0.08, DZ + 1.7), 0.018, em, sides=10)
# transformer with cooling fins
gt.box2((1.5, 3.15, DZ), (2.5, 4.25, DZ + 1.65), "paint_grey", bevel=0.02, seg=2)
for k in range(9):
    gt.box2((1.42, 3.25 + k * 0.11, DZ + 0.15), (1.5, 3.29 + k * 0.11, DZ + 1.45), "paint_grey")
for k in range(3):
    gt.cyl(V(1.75 + k * 0.25, 3.6, DZ + 1.65), V(1.75 + k * 0.25, 3.6, DZ + 1.85), 0.05, "plastic_black", sides=10)
    for j in range(3):
        gt.cyl(V(1.75 + k * 0.25, 3.6, DZ + 1.7 + j * 0.05), V(1.75 + k * 0.25, 3.6, DZ + 1.72 + j * 0.05), 0.07, "plastic_black", sides=10)
# ---- left deck: HPU, cable reel, water tank
gt.box2((-2.45, -0.2, DZ), (-1.3, 1.3, DZ + 0.7), YEL, bevel=0.02, seg=2)                                         # tank
for k in range(2):
    y = 0.15 + k * 0.7
    gt.cyl(V(-2.25, y, DZ + 0.95), V(-1.6, y, DZ + 0.95), 0.2, "paint_blue", sides=20, bevel=0.01, seg=1)
    for j in range(5):
        gt.torus(V(-2.15 + j * 0.11, y, DZ + 0.95), (1, 0, 0), 0.205, 0.008, "paint_blue", seg=18, rseg=4)
    gt.cyl(V(-1.6, y, DZ + 0.95), V(-1.4, y, DZ + 0.95), 0.12, DARK, sides=16)
    gt.box2((-2.2, y - 0.14, DZ + 0.7), (-1.65, y + 0.14, DZ + 0.78), "paint_blue")
gt.box2((-1.42, 0.2, DZ + 0.3), (-1.3, 0.9, DZ + 0.62), STEEL, bevel=0.006, seg=1)
for k, col in enumerate(("hose_red", "rubber", "hose_yellow")):
    gt.hose(V(-1.3, 0.3 + k * 0.2, DZ + 0.46), V(1, 0, 0), V(-1.18, -0.35, DZ + 0.2 + k * 0.08), V(0, 1, 0), 0.022, col, reach=0.3)
gt.cyl(V(-2.45, 2.2, DZ + 0.95), V(-1.35, 2.2, DZ + 0.95), 0.62, DARK, sides=36)                                 # cable reel
gt.cyl(V(-2.3, 2.2, DZ + 0.95), V(-1.5, 2.2, DZ + 0.95), 0.5, "cable", sides=36)
for x in (-2.38, -1.42):
    gt.slab([V(x, 1.65, DZ), V(x, 2.75, DZ), V(x, 2.25, DZ + 0.98), V(x, 2.15, DZ + 0.98)], 0.04, YEL, normal=(1, 0, 0))
gt.cyl(V(-2.0, 2.95, DZ + 0.55), V(-2.0, 4.25, DZ + 0.55), 0.45, "paint_white", sides=28, bevel=0.02, seg=2)      # water tank
for y in (3.15, 4.05):
    gt.box2((-2.4, y - 0.06, DZ), (-1.6, y + 0.06, DZ + 0.25), YEL)
gt.cyl(V(-1.55, 3.5, DZ + 0.3), V(-1.55, 3.5, DZ + 0.62), 0.12, "paint_blue", sides=14)                         # pump
# ---- vent duct along the top + cassette at the rear
for y in (0.0, 1.4, 3.0):
    gt.cyl(V(-1.0, y, 3.77), V(-1.0, y, 3.95), 0.02, DARK, sides=6)
gt.cyl(V(-1.0, -0.3, 4.2), V(-1.0, 3.45, 4.2), 0.38, "hose_yellow", sides=20, caps=(True, False))
for k in range(18):
    gt.torus(V(-1.0, -0.2 + k * 0.2, 4.2), (0, 1, 0), 0.385, 0.012, "hose_yellow", seg=20, rseg=4)
gt.cyl(V(-1.0, 3.45, 4.2), V(-1.0, 4.45, 4.2), 0.55, YEL, sides=28, bevel=0.02, seg=2)
gt.cyl(V(-1.0, -0.35, 4.2), V(-1.0, -0.25, 4.2), 0.44, DARK, sides=20)
# ---- cable trays along the top beams
for s in (-1, 1):
    gt.box2((s * 2.0 - 0.15, GY[0], 3.83), (s * 2.0 + 0.15, GY[-1], 3.85), GALV)
    for x in (s * 2.0 - 0.15, s * 2.0 + 0.15):
        gt.box2((x - 0.005, GY[0], 3.85), (x + 0.005, GY[-1], 3.92), GALV)
    for k in range(3):
        gt.cable([V(s * 2.0 - 0.08 + k * 0.07, GY[0], 3.88), V(s * 2.0 - 0.08 + k * 0.07, GY[-1], 3.88)], 0.025, sides=6)
# ---- floodlights on the gantry
for x, y, aim in ((-1.7, GY[0] - 0.08, (0.2, -1.0, -0.55)), (1.7, GY[0] - 0.08, (-0.2, -1.0, -0.55)),
                  (-1.7, GY[-1] + 0.1, (0.15, 1.0, -0.6)), (1.7, GY[-1] + 0.1, (-0.15, 1.0, -0.6))):
    gt.led_light(V(x, y, 3.45), aim, w=0.36, h=0.13)
static.append(gt.finish(root))

# =============================================================================== decals + screens
dec = Part("decals", grime=False, smooth=False)
for s in (-1, 1):
    lib.decal_wrap(dec, ATL, "mk", V(0, -2.47, CZ), (0, 1, 0), RS, 90 - s * 76, 0.0, h=0.4, mode="along", ref=(1, 0, 0), segs=10)
    lib.decal_wrap(dec, ATL, "mole", V(0, -2.47, CZ), (0, 1, 0), RS, 90 - s * 60, 0.0, h=0.28, mode="along", ref=(1, 0, 0), segs=8)
    lib.decal_wrap(dec, ATL, "warn_head", V(0, -3.7, CZ), (0, 1, 0), RS, 90 - s * 75, 0.0, w=0.5, mode="around", ref=(1, 0, 0))
lib.decal_wrap(dec, ATL, "plate", V(0, YT - 0.6, CZ), (0, 1, 0), RS, 180 + 35, 0.0, w=0.42, mode="around", ref=(1, 0, 0))
lib.decal_cell(dec, ATL, "warn_hv", (2.0, 4.251, DZ + 0.75), (0, 1, 0), (0, 0, 1), w=0.5)
lib.decal_cell(dec, ATL, "l_tr", (2.0, 4.251, DZ + 1.35), (0, 1, 0), (0, 0, 1), w=0.32)
lib.decal_cell(dec, ATL, "l_cab", (1.86, CY1 + 0.001, CZ1 - 0.17), (0, 1, 0), (0, 0, 1), w=0.3)
lib.decal_cell(dec, ATL, "l_hpu", (-1.875, 1.301, DZ + 0.5), (0, 1, 0), (0, 0, 1), w=0.3)
lib.decal_cell(dec, ATL, "l_mcc", (1.979, 2.75, DZ + 1.82), (-1, 0, 0), (0, 0, 1), w=0.28)
lib.decal_cell(dec, ATL, "warn_crush", (2.3, GY[0] - 0.111, 2.2), (0, -1, 0), (0, 0, 1), w=0.2)
for k, y in enumerate(GY[:3]):
    lib.decal_cell(dec, ATL, f"gantry{k + 1}", (-2.42, y, 2.4), (-1, 0, 0), (0, 0, 1), w=0.42)
lib.decal_cell(dec, ATL, "vent", (-1.0, 4.451, 4.2), (0, 1, 0), (0, 0, 1), w=0.6)
lib.decal_cell(dec, ATL, "badge", (2.51, 0.7, CZ0 + 0.45), (1, 0, 0), (0, 0, 1), w=0.5)
for k, (cell, x) in enumerate((("head", 1.55), ("ring", 1.86), ("guide", 2.17))):
    lib.decal(dec, (x, CY0 + 0.301, CZ0 + 0.965), (0, 1, 0), (0, 0, 1), 0.28 if k == 0 else 0.22, 0.2 if k == 0 else 0.22,
              "custom_screen_mole1", lib.cell_uv(f"scr_{ID}", cell), off=0.0)
for s in (-1, 1):
    lib.stripe(dec, (s * 1.8, GY[-1] + 0.151, DZ - 0.02), (0, 1, 0), (0, 0, 1), 1.5, 0.08, period=0.16)
static.append(dec.finish(root))

# =============================================================================== empties
lib.empty("fx_work", (0, YF - 0.25, CZ), root)
lib.empty("fx_ore", P1 + V(0, 0.32, -0.75), root)
lib.empty("light_0", (-1.7, GY[0] - 0.15, 3.43), root, aim=(0.2, -1.0, -0.55))
lib.empty("light_1", (1.7, GY[0] - 0.15, 3.43), root, aim=(-0.2, -1.0, -0.55))
lib.empty("light_2", (-1.7, GY[-1] + 0.17, 3.43), root, aim=(0.15, 1.0, -0.6))
lib.empty("light_3", (1.7, GY[-1] + 0.17, 3.43), root, aim=(-0.15, 1.0, -0.6))
lib.empty("op", (1.85, 0.95, CZ0 + 0.06), root, face=(0, -1, 0))
lib.empty("snd", (0, -2.7, CZ), root)

# =============================================================================== animation
lib.spin(cutterhead, "Work", WORK, turns=1)
for o, s0 in clusters:
    dist = 4 * CPITCH
    marks = {0.0, 1.0}
    for c in (LEN, LEN + 0.36, 2 * LEN + 0.36, LOOPL):
        for base in (0.0, LOOPL):
            d = c + base - s0
            if 0 < d < dist:
                marks.add(d / dist)
    for t in sorted(marks):
        p = belt_pos(s0 + t * dist)
        lib.key(o, "Work", "location", 1, t * WORK, p.y, "LINEAR")
        lib.key(o, "Work", "location", 2, t * WORK, p.z, "LINEAR")
lib.track(erector, "Work", "rotation_euler", 2, [(0, 0.0), (40, math.radians(6)), (80, math.radians(-4)), (WORK, 0.0)])
for o in [cutterhead, erector] + [c for c, _ in clusters]:
    lib.hold(o, "Idle", IDLE)
lib.bake_clips()

# =============================================================================== merge, grime, export
body = lib.merge([o for o in static if o.get("grime")], "body")
meshes = [o for o in lib.descendants(root) if o.type == "MESH" and o.get("grime")]
lib.bake_grime(meshes, distance=0.5, samples=48, floor_z=0.0)
path, js, anims, names = lib.export(root, OUT)
size = lib.report(root, "<= 8 W x 10 L x 5.6 H")
need = [ID, "fx_work", "fx_ore", "light_0", "light_1", "light_2", "light_3", "op", "snd"]
print("[mb] missing nodes:", [n for n in need if n not in names])

if PREVIEW:
    lib.previews(ID, root, [
        dict(name="34", az=35, el=14, fill=0.95),
        dict(name="rear", az=200, el=16, fill=0.95),
        dict(name="side", az=90, el=6, fill=0.95),
        dict(name="tail", az=168, el=12, target=(0, -1.8, CZ + 0.2), dist=5.6, lens=30),
        dict(name="head", az=-20, el=8, target=(0.6, YF, CZ + 0.4), dist=3.4, lens=35),
    ], frame=30)
