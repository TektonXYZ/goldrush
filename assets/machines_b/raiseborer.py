"""Kessler RB-7 Raise Borer (modelled on a Sandvik Rhino / Robbins 73RH box-hole rig).

    systemd-run --user --scope -q -p MemoryMax=3G -p MemorySwapMax=0 \
        bl assets/machines_b/raiseborer.py -- public/models/machines/raiseborer [--no-preview]

Layout (Blender, front = -Y = three.js +Z): concrete pad 4.8 x 6.4 m; derrick toward the front with
twin thrust cylinders under a sliding crosshead/drive head at eye height; the striped drill string rises
through the crown centraliser and a muck deflector into the roof (pipe to z 4.86, roof at 4.5); cuttings
chute + pile -X; pipe rack + rod davit +X; hydraulic power unit rear +X; operator console rear -X facing
the derrick (op empty faces the machine front).
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

ID = "raiseborer"
args = bk.args()
OUT = os.path.abspath(args[0]) if args and not args[0].startswith("--") else os.path.join(lib.PROJECT, "public/models/machines", ID)
PREVIEW = "--no-preview" not in args

bk.reset()
bpy.context.scene.render.fps = lib.FPS
WORK, IDLE = 120, 60          # 4 s loop, 2 s idle
ATL = ID
lib.label(f"label_{ID}_decals", os.path.join(lib.DECALS, f"{ID}.png"))
lib.std_materials()
lib.label("custom_screen_rb7", os.path.join(lib.DECALS, f"scr_{ID}.png"), mode="OPAQUE", emit=2.2, rough=0.25)

root = lib.root(ID)
static = []                                          # merged into one body mesh at the end
PAD = 0.25            # pad top
B0 = 0.33             # derrick plinth top
DY = -1.0             # derrick centre (y)
HZ = 1.85             # crosshead underside at rest
CZ0, CZ1 = 3.1, 3.34  # crown underside / top
YEL, DARK, STEEL, GALV = "paint_yellow", "steel_dark", "steel", "galvanized"

# =============================================================================== concrete pad
pad = Part("pad")
pad.box2((-2.4, -2.6, 0), (2.4, 3.2, PAD), "concrete", bevel=0.035, seg=2)
pad.box2((-1.32, DY - 0.98, PAD), (1.32, DY + 0.98, B0), "concrete", bevel=0.02, seg=2)
pad.angle_iron((-2.38, 3.2, PAD - 0.05), (2.38, 3.2, PAD - 0.05), 0.06, STEEL, up=(0, 0, 1))
pad.box2((-2.2, 2.85, PAD - 0.004), (-0.95, 3.0, PAD + 0.004), "custom_grating")
for x, y in ((0.36, 1.1), (2.04, 1.1), (0.36, 2.9), (2.04, 2.9)):           # HPU hold-downs
    pad.bolt((x, y - 0.12, PAD), (0, 0, 1), r=0.014, washer=True)
static.append(pad.finish(root))

# =============================================================================== derrick (static)
st = Part("derrick")
st.box2((-1.06, DY - 0.82, B0), (1.06, DY + 0.82, B0 + 0.05), DARK, bevel=0.006, seg=1)
st.box2((-0.96, DY - 0.72, B0 + 0.05), (0.96, DY + 0.72, B0 + 0.36), YEL, bevel=0.016, seg=2)
st.box2((-0.9, DY - 0.66, B0 + 0.36), (0.9, DY + 0.66, B0 + 0.39), DARK, bevel=0.004, seg=1)
for sx in (-1, 1):
    for y in (DY - 0.45, DY, DY + 0.45):
        st.slab([(sx * 0.96, y, B0 + 0.05), (sx * 1.04, y, B0 + 0.05), (sx * 0.96, y, B0 + 0.33)], 0.024, YEL, normal=(0, 1, 0))
for sy in (-1, 1):
    for x in (-0.6, 0.0, 0.6):
        st.slab([(x, DY + sy * 0.72, B0 + 0.05), (x, DY + sy * 0.8, B0 + 0.05), (x, DY + sy * 0.72, B0 + 0.33)], 0.024, YEL, normal=(1, 0, 0))
for sx in (-1, 1):                                                       # levelling jacks + anchors
    for sy in (-1, 1):
        x, y = sx * 1.13, DY + sy * 0.66
        st.box2((x - 0.11, y - 0.11, B0), (x + 0.11, y + 0.11, B0 + 0.03), DARK, bevel=0.004, seg=1)
        st.cyl((x, y, B0 + 0.03), (x, y, B0 + 0.3), 0.075, YEL, sides=16, bevel=0.006, seg=1)
        st.cyl((x, y, B0 + 0.3), (x, y, B0 + 0.34), 0.05, "chrome", sides=12)
        st.box2((x - sx * 0.05 - 0.07, y - 0.05, B0 + 0.24), (x - sx * 0.05 + 0.07, y + 0.05, B0 + 0.33), YEL)
        for k in range(4):
            a = math.pi / 4 + k * math.pi / 2
            st.bolt((x + math.cos(a) * 0.078, y + math.sin(a) * 0.078, B0 + 0.03), (0, 0, 1), r=0.014, washer=True)
st.box2((0.25, DY + 0.72, B0 + 0.12), (0.7, DY + 0.82, B0 + 0.32), STEEL, bevel=0.006, seg=1)        # thrust valve block
for i in range(3):
    st.cyl((0.33 + i * 0.14, DY + 0.82, B0 + 0.24), (0.33 + i * 0.14, DY + 0.86, B0 + 0.24), 0.022, STEEL, sides=6)
for sx in (-1, 1):                                                       # accumulators
    x = sx * 0.72
    st.lathe((x, DY - 0.9, B0 + 0.05), (0, 0, 1), [(0.0, 0), (0.09, 0.0), (0.11, 0.06), (0.11, 0.52), (0.07, 0.62), (0.03, 0.66),
                                                     (0.03, 0.72), (0, 0.72)], "paint_grey", sides=18)
    st.box2((x - 0.12, DY - 0.84, B0 + 0.22), (x + 0.12, DY - 0.8, B0 + 0.28), DARK)
# columns: heavy box sections with guide rails, access plates, gussets
for sx in (-1, 1):
    x = sx * 0.86
    st.box2((x - 0.14, DY - 0.17, B0 + 0.39), (x + 0.14, DY + 0.17, CZ0), YEL, bevel=0.016, seg=2)
    xi = x - sx * 0.14
    st.box2((min(xi, xi - sx * 0.025), DY - 0.065, 0.75), (max(xi, xi - sx * 0.025), DY + 0.065, CZ0 - 0.04), STEEL, bevel=0.004, seg=1)
    for sy in (-1, 1):
        for xo in (-0.13, 0.13):
            st.slab([(x + xo, DY + sy * 0.17, B0 + 0.39), (x + xo, DY + sy * 0.44, B0 + 0.39), (x + xo, DY + sy * 0.17, B0 + 1.0)], 0.022, YEL,
                    normal=(1, 0, 0))
        st.bolts((x + sx * 0.14, DY + sy * 0.1, 1.1), (x + sx * 0.14, DY + sy * 0.1, CZ0 - 0.15), 6, (sx, 0, 0), r=0.011)
    for z0, z1 in ((1.0, 1.85), (2.0, 2.85)):
        st.box2((min(x + sx * 0.136, x + sx * 0.152), DY - 0.12, z0), (max(x + sx * 0.136, x + sx * 0.152), DY + 0.12, z1), YEL, bevel=0.004, seg=1)
    # rear tie brace between column and base (diagonal channel)
    st.channel((x, DY + 0.17, CZ0 - 0.9), (x, DY + 0.66, B0 + 0.39), 0.12, 0.06, YEL, up=(sx, 0, 0))
st.ladder((-1.07, DY, B0 + 0.4), (-1.07, DY, CZ0 - 0.05), w=0.4, m=YEL)
for z in (0.9, 1.9, 2.8):
    st.box2((-1.07, DY - 0.2, z - 0.02), (-1.0, DY + 0.2, z + 0.02), YEL)
# crown, centraliser, muck deflector
st.box2((-1.06, DY - 0.25, CZ0), (1.06, DY + 0.25, CZ1), YEL, bevel=0.016, seg=2)
st.box2((-1.08, DY - 0.27, CZ1 - 0.04), (1.08, DY + 0.27, CZ1 + 0.02), DARK, bevel=0.004, seg=1)
st.cyl((0, DY, CZ0 - 0.08), (0, DY, CZ0 + 0.01), 0.24, STEEL, sides=24, bevel=0.006, seg=1)
st.bolt_ring((0, DY, CZ0 - 0.08), (0, 0, -1), 0.2, 8, r=0.012)
st.lathe((0, DY, CZ1 + 0.02), (0, 0, 1), [(0.42, 0), (0.43, 0.03), (0.22, 0.2), (0.19, 0.22)], STEEL, sides=28, caps=False)
st.lathe((0, DY, CZ1 + 0.02), (0, 0, 1), [(0.43, 0.0), (0.43, -0.0001)], STEEL, sides=28, caps=False)
for sx in (-1, 1):
    for sy in (-1, 1):
        st.bolts((sx * 0.55, DY + sy * 0.25, CZ0 + 0.05), (sx * 0.98, DY + sy * 0.25, CZ0 + 0.05), 4, (0, sy, 0), r=0.01)
    st.slab([(sx * 0.72 - 0.07, DY, CZ1 + 0.02), (sx * 0.72 + 0.07, DY, CZ1 + 0.02), (sx * 0.72 + 0.04, DY, CZ1 + 0.13),
             (sx * 0.72 - 0.04, DY, CZ1 + 0.13)], 0.03, YEL, normal=(0, 1, 0))
    st.torus((sx * 0.72, DY, CZ1 + 0.1), (0, 1, 0), 0.03, 0.012, DARK, seg=12, rseg=6)
# cuttings chute: U trough from under the deflector rim (-X) down to the pile, with stiffeners + leg
c0, c1 = V(-0.36, DY - 0.08, CZ1 + 0.02), V(-1.5, DY - 0.78, 1.05)
cw = (c1 - c0).normalized()
side = cw.cross(V(0, 0, 1)).normalized()
nrm = side.cross(cw).normalized()
if nrm.z < 0:
    nrm = -nrm
TW, TH = 0.42, 0.2
st.prism(c0, c1, [(-TW / 2 - 0.008, -0.014), (TW / 2 + 0.008, -0.014), (TW / 2 + 0.008, 0.0), (-TW / 2 - 0.008, 0.0)], YEL, up=tuple(nrm))
st.prism(c0 + nrm * 0.001, c1 + nrm * 0.001, [(-TW / 2, 0.0), (TW / 2, 0.0), (TW / 2, 0.008), (-TW / 2, 0.008)], STEEL, up=tuple(nrm))
for s in (-1, 1):
    st.prism(c0 + side * s * TW / 2, c1 + side * s * TW / 2, [(-0.008, -0.014), (0.008, -0.014), (0.008, TH), (-0.008, TH)], YEL, up=tuple(nrm))
    st.prism(c0 + side * s * (TW / 2 + 0.02) + nrm * TH, c1 + side * s * (TW / 2 + 0.02) + nrm * TH,
             [(-0.025, -0.012), (0.025, -0.012), (0.025, 0.012), (-0.025, 0.012)], YEL, up=tuple(nrm))
st.prism(c1 - cw * 0.02, c1 + cw * 0.004, [(-TW / 2 - 0.03, -0.04), (TW / 2 + 0.03, -0.04), (TW / 2 + 0.03, TH + 0.02), (-TW / 2 - 0.03, TH + 0.02)],
         YEL, up=tuple(nrm))
for k in range(1, 5):
    q = c0.lerp(c1, k / 5)
    st.prism(q - side * (TW / 2 + 0.03) - cw * 0.02, q + side * (TW / 2 + 0.03) - cw * 0.02,
             [(-0.02, -0.03), (0.02, -0.03), (0.02, 0.0), (-0.02, 0.0)], YEL, up=tuple(nrm))
leg_top = c0.lerp(c1, 0.62) - nrm * 0.03
st.cyl(leg_top, V(leg_top.x, leg_top.y, PAD + 0.02), 0.045, YEL, sides=12)
st.box2((leg_top.x - 0.12, leg_top.y - 0.12, PAD), (leg_top.x + 0.12, leg_top.y + 0.12, PAD + 0.02), DARK)
st.cyl(leg_top + V(0, 0, -0.6), V(-0.96, DY - 0.5, B0 + 0.3), 0.03, YEL, sides=10)
# thrust cylinder barrels (rods ride with the head)
for sx in (-1, 1):
    x = sx * 0.5
    for s in (-1, 1):
        st.box2((x - 0.1, DY + s * 0.075 - 0.015, B0 + 0.39), (x + 0.1, DY + s * 0.075 + 0.015, B0 + 0.56), YEL, bevel=0.004, seg=1)
    st.cyl((x, DY - 0.11, B0 + 0.49), (x, DY + 0.11, B0 + 0.49), 0.035, STEEL, sides=10)
    st.cyl((x, DY, B0 + 0.46), (x, DY, B0 + 0.6), 0.11, DARK, sides=20, bevel=0.006, seg=1)
    st.cyl((x, DY, B0 + 0.6), (x, DY, 1.42), 0.135, YEL, sides=24, bevel=0.01, seg=2)
    st.cyl((x, DY, 1.4), (x, DY, 1.47), 0.15, YEL, sides=24, bevel=0.008, seg=1)
    st.cyl((x, DY, 1.47), (x, DY, 1.52), 0.1, STEEL, sides=20)
    st.bolt_ring((x, DY, 1.47), (0, 0, 1), 0.128, 8, r=0.009)
    for z in (1.0, 1.36):
        st.cyl((x, DY, z), (x, DY + 0.17, z), 0.025, STEEL, sides=8)
        st.cyl((x, DY + 0.17, z), (x, DY + 0.2, z), 0.032, STEEL, sides=6)
# rock collar casing where the string enters the roof
st.cyl((0, DY, 4.34), (0, DY, 4.86), 0.235, DARK, sides=24)
st.cyl((0, DY, 4.32), (0, DY, 4.38), 0.27, DARK, sides=24, bevel=0.006, seg=1)
# work lights
st.led_light((0.52, DY - 0.34, CZ0 + 0.14), (-0.15, -0.45, -1.0), w=0.34, h=0.13)
st.led_light((-0.86, DY - 0.26, CZ0 - 0.12), (0.55, 0.12, 1.0), w=0.28, h=0.11)
static.append(st.finish(root))

# =============================================================================== drive head (creeps up)
hd = Part("drive_head", pivot=(0, DY, HZ))
hd.box2((-0.72, DY - 0.3, HZ), (0.72, DY + 0.3, HZ + 0.32), YEL, bevel=0.02, seg=2)
hd.box2((-0.74, DY - 0.32, HZ + 0.12), (0.74, DY + 0.32, HZ + 0.2), YEL, bevel=0.006, seg=1)
for sx in (-1, 1):
    x = sx * 0.86
    hd.box2((min(sx * 0.7, sx * 0.725), DY - 0.22, HZ + 0.02), (max(sx * 0.7, sx * 0.725), DY + 0.22, HZ + 0.3), YEL, bevel=0.008, seg=1)
    for sy in (-1, 1):
        hd.box2((x - 0.17, DY + sy * 0.17, HZ + 0.03), (x + 0.17, DY + sy * 0.17 + sy * 0.05, HZ + 0.29), YEL, bevel=0.008, seg=1)
        hd.box2((x - 0.13, DY + sy * 0.17 - sy * 0.012, HZ + 0.06), (x + 0.13, DY + sy * 0.17, HZ + 0.26), "brass")
        hd.bolts((x - 0.13, DY + sy * 0.22, HZ + 0.07), (x + 0.13, DY + sy * 0.22, HZ + 0.07), 3, (0, sy, 0), r=0.01)
        hd.bolts((x - 0.13, DY + sy * 0.22, HZ + 0.25), (x + 0.13, DY + sy * 0.22, HZ + 0.25), 3, (0, sy, 0), r=0.01)
    hd.cyl((sx * 0.5, DY, 1.15), (sx * 0.5, DY, HZ - 0.08), 0.078, "chrome", sides=20)
    hd.cyl((sx * 0.5, DY, HZ - 0.12), (sx * 0.5, DY, HZ), 0.1, DARK, sides=20, bevel=0.005, seg=1)
# gearbox with ribs, bolted flanges, sight glass, breather
hd.lathe((0, DY, HZ + 0.32), (0, 0, 1), [(0.5, 0), (0.52, 0.02), (0.52, 0.07), (0.48, 0.09), (0.47, 0.32), (0.5, 0.34), (0.5, 0.39),
                                          (0.36, 0.42), (0.36, 0.44), (0, 0.44)], YEL, sides=36)
hd.bolt_ring((0, DY, HZ + 0.39), (0, 0, 1), 0.44, 16, r=0.011)
hd.bolt_ring((0, DY, HZ + 0.34), (0, 0, 1), 0.505, 18, r=0.01)
for k in range(10):
    a = k * math.tau / 10 + math.pi / 10
    d = V(math.cos(a), math.sin(a), 0)
    p = V(0, DY, 0) + d * 0.465
    hd.slab([p + V(0, 0, HZ + 0.41), p + d * 0.06 + V(0, 0, HZ + 0.41), p + d * 0.06 + V(0, 0, HZ + 0.45), p + V(0, 0, HZ + 0.64)],
            0.024, YEL, normal=d.cross(V(0, 0, 1)))
hd.cyl((0.4, DY - 0.29, HZ + 0.5), (0.43, DY - 0.32, HZ + 0.5), 0.05, STEEL, sides=12)
hd.cyl((0.43, DY - 0.32, HZ + 0.5), (0.44, DY - 0.33, HZ + 0.5), 0.038, "glass_dark", sides=12)
hd.cyl((-0.3, DY + 0.25, HZ + 0.76), (-0.3, DY + 0.25, HZ + 0.86), 0.035, DARK, sides=10)
hd.lathe((-0.3, DY + 0.25, HZ + 0.86), (0, 0, 1), [(0.06, 0), (0.06, 0.04), (0.02, 0.07), (0, 0.07)], DARK, sides=12)
for sy in (-1, 1):                                                        # two hydraulic drive motors
    y = DY + sy * 0.43
    hd.cyl((0, y, HZ + 0.66), (0, y, HZ + 0.72), 0.19, STEEL, sides=24, bevel=0.005, seg=1)
    hd.lathe((0, y, HZ + 0.72), (0, 0, 1), [(0.15, 0), (0.15, 0.32), (0.16, 0.33), (0.16, 0.38), (0.12, 0.41), (0, 0.41)], "paint_grey", sides=24)
    for k in range(3):
        hd.torus((0, y, HZ + 0.79 + k * 0.08), (0, 0, 1), 0.152, 0.009, "paint_grey", seg=20, rseg=4)
    hd.bolt_ring((0, y, HZ + 0.72), (0, 0, 1), 0.17, 8, r=0.01)
    hd.box2((-0.09, y + sy * 0.12, HZ + 0.86), (0.09, y + sy * 0.2, HZ + 1.02), STEEL, bevel=0.006, seg=1)
    hd.slab([(-0.16, y, HZ + 0.44), (0.16, y, HZ + 0.44), (0.12, y, HZ + 0.66), (-0.12, y, HZ + 0.66)], 0.05, YEL, normal=(0, 1, 0))
hd.box2((-0.42, DY - 0.16, HZ + 0.76), (-0.16, DY + 0.16, HZ + 0.9), YEL, bevel=0.01, seg=2)              # breakout wrench
hd.box2((0.16, DY - 0.16, HZ + 0.76), (0.42, DY + 0.16, HZ + 0.9), YEL, bevel=0.01, seg=2)
for sx in (-1, 1):
    hd.box2((min(sx * 0.16, sx * 0.19), DY - 0.06, HZ + 0.78), (max(sx * 0.16, sx * 0.19), DY + 0.06, HZ + 0.88), DARK)
    hd.cyl((sx * 0.42, DY, HZ + 0.83), (sx * 0.6, DY, HZ + 0.83), 0.05, YEL, sides=16, bevel=0.004, seg=1)
    hd.cyl((sx * 0.6, DY, HZ + 0.83), (sx * 0.68, DY, HZ + 0.83), 0.03, "chrome", sides=12)
for k, col in enumerate(("hose_red", "rubber")):                          # service loops (ride with the head)
    s = 1 if k else -1
    hd.hose((0.05 * s, DY + 0.63, HZ + 0.94), (0, 1, 0), (0.86 + 0.05 * s, DY + 0.26, HZ - 0.25), (0, 0, -1), 0.024, col, sag=0.15, reach=0.55)
    hd.hose((0.05 * s, DY - 0.63, HZ + 0.94), (0, -1, 0), (0.98 + 0.05 * s, DY - 0.05, HZ - 0.32), (0, 0, -1), 0.024,
            "hose_yellow" if k else "rubber", sag=0.2, reach=0.7)
head = hd.finish(root)

# drill string: spindle flange, saver sub, pipe through the crown into the roof (rotates)
sg = Part("drill_string", pivot=(0, DY, HZ + 0.76), axis=(0, 0, 1))
sg.cyl((0, DY, HZ + 0.72), (0, DY, HZ + 0.8), 0.26, STEEL, sides=28, bevel=0.008, seg=1)
sg.bolt_ring((0, DY, HZ + 0.8), (0, 0, 1), 0.21, 10, r=0.013)
sg.cyl((0, DY, HZ + 0.8), (0, DY, HZ + 1.0), 0.17, DARK, sides=24, bevel=0.006, seg=1)
for k in range(4):
    a = k * math.pi / 2
    sg.box((math.cos(a) * 0.165, DY + math.sin(a) * 0.165, HZ + 0.9), (0.03, 0.12, 0.14), STEEL, rot=(0, 0, math.degrees(a) + 90))
JZ = (HZ + 1.0, 4.05)                                                     # tool joints
for jz in JZ:
    sg.lathe((0, DY, jz), (0, 0, 1), [(0.14, -0.03), (0.158, 0), (0.158, 0.22), (0.15, 0.26), (0.14, 0.28)], STEEL, sides=24, caps=False)
    sg.cyl((0, DY, jz + 0.03), (0, DY, jz + 0.12), 0.161, DARK, sides=24, caps=(False, False))
sg.cyl((0, DY, HZ + 1.27), (0, DY, 4.9), 0.14, DARK, sides=24, caps=(False, True))
for k in range(2):                                                        # rotation stripes
    a = k * math.pi
    sg.box((math.cos(a) * 0.141, DY + math.sin(a) * 0.141, 3.5), (0.014, 0.05, 1.0), YEL, rot=(0, 0, math.degrees(a)))
string = sg.finish(head)

# =============================================================================== pipe rack, rod davit, spares pallet
rk = Part("rack")
RX = (1.42, 1.77, 2.12)
for y in (DY - 0.52, DY + 0.48):
    for sx in (1.27, 2.27):
        rk.box2((sx - 0.06, y - 0.06, PAD), (sx + 0.06, y + 0.06, PAD + 0.62), YEL, bevel=0.008, seg=1)
        rk.box2((sx - 0.11, y - 0.11, PAD), (sx + 0.11, y + 0.11, PAD + 0.015), DARK)
        rk.bolt((sx - 0.08, y, PAD + 0.015), (0, 0, 1), r=0.012)
        rk.bolt((sx + 0.08, y, PAD + 0.015), (0, 0, 1), r=0.012)
    rk.box2((1.2, y - 0.075, PAD + 0.6), (2.34, y + 0.075, PAD + 0.68), YEL, bevel=0.008, seg=1)
    for x in RX:
        for s in (-1, 1):
            rk.box((x + s * 0.1, y, PAD + 0.71), (0.12, 0.13, 0.03), "rubber", rot=(0, -s * 32, 0))
    for sx in (1.2, 2.34):
        rk.box2((sx - 0.025, y - 0.06, PAD + 0.68), (sx + 0.025, y + 0.06, PAD + 1.26), YEL, bevel=0.004, seg=1)
    rk.box2((1.27, y - 0.035, PAD + 0.2), (2.27, y + 0.035, PAD + 0.27), YEL, bevel=0.004, seg=1)
    for s in (-1, 1):                                                     # diagonal braces
        rk.cyl((1.77 + s * 0.06, y, PAD + 0.27), (1.77 + s * 0.46, y, PAD + 0.58), 0.02, YEL, sides=8)
rk.box2((1.2, DY - 0.6, PAD + 0.25), (1.25, DY + 0.56, PAD + 0.31), YEL)
rk.box2((2.29, DY - 0.6, PAD + 0.25), (2.34, DY + 0.56, PAD + 0.31), YEL)


def rod(part, x, z, y0, y1, flip=False):
    """1.5 m raise-bore rod lying along Y: body, box + pin tool joints, thread protectors."""
    a, b = (y1, y0) if flip else (y0, y1)
    s = 1 if b > a else -1
    part.cyl((x, a, z), (x, b, z), 0.14, DARK, sides=16, caps=(False, False))
    part.cyl((x, a, z), (x, a + s * 0.22, z), 0.158, STEEL, sides=16, bevel=0.006, seg=1)
    part.cyl((x, a + s * 0.24, z), (x, a + s * 0.3, z), 0.161, DARK, sides=16, caps=(False, False))
    part.lathe((x, a, z), (0, -s, 0), [(0.0, 0.03), (0.13, 0.03), (0.15, 0.0), (0.158, 0.0)], "plastic_black", sides=16, caps=False)
    part.cyl((x, b, z), (x, b - s * 0.16, z), 0.152, STEEL, sides=16, bevel=0.005, seg=1)
    part.lathe((x, b, z), (0, s, 0), [(0.1, 0), (0.115, 0.0), (0.112, 0.1), (0.075, 0.13), (0.0, 0.13)], "plastic_yellow", sides=16)
    for k in range(2):
        part.torus((x, b + s * (0.03 + k * 0.04), z), (0, 1, 0), 0.114, 0.006, "plastic_yellow", seg=16, rseg=4)


z1 = PAD + 0.74 + 0.14
for x in RX:
    rod(rk, x, z1, DY - 0.76, DY + 0.76, flip=(x == RX[1]))
for x in ((RX[0] + RX[1]) / 2, (RX[1] + RX[2]) / 2):
    rod(rk, x, z1 + 0.26, DY - 0.76, DY + 0.76, flip=(x > 1.8))
# rod davit (slewing jib with chain hoist)
rk.cyl((1.05, DY + 0.55, B0), (1.05, DY + 0.55, 3.0), 0.07, YEL, sides=18, bevel=0.006, seg=1)
rk.cyl((1.05, DY + 0.55, B0), (1.05, DY + 0.55, B0 + 0.03), 0.16, DARK, sides=18)
rk.bolt_ring((1.05, DY + 0.55, B0 + 0.03), (0, 0, 1), 0.13, 6, r=0.012, washer=True)
rk.cyl((1.05, DY + 0.55, 2.82), (1.05, DY + 0.55, 2.96), 0.1, DARK, sides=18)
rk.ibeam((1.0, DY + 0.55, 2.9), (2.3, DY + 0.1, 2.9), 0.16, 0.09, YEL)
rk.cyl((1.05, DY + 0.55, 2.98), (2.0, DY + 0.2, 2.84), 0.02, DARK, sides=6)
hx, hy = 1.82, DY + 0.26
rk.box2((hx - 0.08, hy - 0.06, 2.7), (hx + 0.08, hy + 0.06, 2.81), DARK, bevel=0.006, seg=1)
rk.box2((hx - 0.09, hy - 0.09, 2.48), (hx + 0.09, hy + 0.09, 2.68), "paint_red", bevel=0.012, seg=2)
for k in range(8):
    rk.torus((hx, hy, 2.46 - k * 0.055), (1, 0, 0) if k % 2 else (0, 1, 0), 0.02, 0.006, STEEL, seg=8, rseg=4)
rk.torus((hx, hy, 1.96), (0, 1, 0), 0.05, 0.016, YEL, seg=12, rseg=6, arc=300, phase=-60)
# pallet with a spare tricone pilot bit and a reamer cutter
PX, PY = 1.75, 0.3
for i in range(5):
    rk.box2((PX - 0.5, PY - 0.4 + i * 0.19, PAD + 0.1), (PX + 0.5, PY - 0.4 + i * 0.19 + 0.1, PAD + 0.125), "wood_planks", bevel=0.004, seg=1)
for j in (-1, 0, 1):
    rk.box2((PX + j * 0.43 - 0.045, PY - 0.4, PAD), (PX + j * 0.43 + 0.045, PY + 0.4, PAD + 0.1), "wood_planks", bevel=0.004, seg=1)
bx, by, bz = PX - 0.18, PY, PAD + 0.125
rk.lathe((bx, by, bz), (0, 0, 1), [(0.09, 0), (0.1, 0.02), (0.1, 0.12), (0.13, 0.16), (0.13, 0.19), (0.11, 0.2), (0.11, 0.3), (0.0, 0.3)],
         DARK, sides=18)
for k in range(3):
    a = k * math.tau / 3
    d = V(math.cos(a), math.sin(a), 0)
    cc = V(bx, by, bz + 0.33) + d * 0.075
    ax_ = (d * 0.75 + V(0, 0, 0.66)).normalized()
    rk.lathe(cc - ax_ * 0.02, ax_, [(0.085, 0), (0.095, 0.03), (0.07, 0.09), (0.03, 0.13), (0, 0.135)], STEEL, sides=12)
    b1, b2 = lib.perp(ax_)
    for row, (hh, rr) in enumerate(((0.03, 0.095), (0.08, 0.072))):
        for t in range(7):
            q = cc + ax_ * hh + (b1 * math.cos(t * math.tau / 7 + row) + b2 * math.sin(t * math.tau / 7 + row)) * rr
            nn = (q - (cc + ax_ * hh)).normalized()
            rk.cyl(q - nn * 0.005, q + nn * 0.02, 0.01, "cast_iron", sides=5)
cx_ = PX + 0.22
rk.cyl((cx_, PY, PAD + 0.125), (cx_, PY, PAD + 0.18), 0.12, DARK, sides=16)
rk.lathe((cx_, PY, PAD + 0.18), (0, 0, 1), [(0.19, 0), (0.2, 0.04), (0.16, 0.2), (0.11, 0.3), (0.0, 0.31)], STEEL, sides=20)
for row, (hh, rr) in enumerate(((0.06, 0.188), (0.13, 0.168), (0.2, 0.143), (0.26, 0.115))):
    for t in range(10 - row * 2):
        a = t * math.tau / (10 - row * 2) + row * 0.3
        q = V(cx_ + math.cos(a) * rr, PY + math.sin(a) * rr, PAD + 0.18 + hh)
        nn = V(math.cos(a), math.sin(a), 0.45).normalized()
        rk.cyl(q - nn * 0.004, q + nn * 0.016, 0.013, "cast_iron", sides=5)
static.append(rk.finish(root))

# =============================================================================== hydraulic power unit (rear +X)
hp = Part("hpu")
for x in (0.28, 2.12):
    hp.channel((x, 1.0, PAD + 0.07), (x, 3.0, PAD + 0.07), 0.14, 0.07, DARK, up=(0, 0, 1))
for y in (1.06, 2.0, 2.94):
    hp.box2((0.28, y - 0.04, PAD), (2.12, y + 0.04, PAD + 0.12), DARK, bevel=0.004, seg=1)
hp.box2((0.32, 1.1, PAD + 0.14), (2.08, 2.38, PAD + 0.78), YEL, bevel=0.02, seg=2)
hp.box2((0.36, 1.14, PAD + 0.78), (2.04, 2.34, PAD + 0.81), YEL, bevel=0.006, seg=1)
hp.cyl((1.9, 2.15, PAD + 0.81), (1.9, 2.15, PAD + 0.9), 0.06, DARK, sides=14)
hp.lathe((1.9, 2.15, PAD + 0.9), (0, 0, 1), [(0.075, 0), (0.075, 0.03), (0.0, 0.05)], "paint_black", sides=14)
for i in range(2):
    hp.lathe((1.55 + i * 0.18, 1.3, PAD + 0.81), (0, 0, 1), [(0.075, 0), (0.075, 0.28), (0.06, 0.31), (0, 0.32)], "paint_blue", sides=16)
hp.box2((2.08, 1.35, PAD + 0.3), (2.1, 1.43, PAD + 0.7), DARK)
hp.cyl((2.11, 1.39, PAD + 0.33), (2.11, 1.39, PAD + 0.67), 0.015, "glass", sides=8)
hp.cyl((2.08, 1.8, PAD + 0.2), (2.18, 1.8, PAD + 0.2), 0.03, STEEL, sides=10)
hp.box2((2.18, 1.76, PAD + 0.16), (2.2, 1.84, PAD + 0.24), "paint_red")
MZ = PAD + 0.81 + 0.3                                                     # electric motor, bell housing, pump
hp.cyl((0.52, 1.75, MZ), (1.26, 1.75, MZ), 0.25, "paint_blue", sides=28, bevel=0.012, seg=2)
for k in range(9):
    hp.cyl((0.58 + k * 0.075, 1.75, MZ), (0.6 + k * 0.075, 1.75, MZ), 0.272, "paint_blue", sides=28, caps=(False, False))
hp.lathe((0.52, 1.75, MZ), (-1, 0, 0), [(0.25, 0), (0.26, 0.02), (0.26, 0.12), (0.22, 0.15), (0.0, 0.16)], "paint_blue", sides=28)
for k in range(10):
    a = k * math.tau / 10
    hp.box((0.355, 1.75 + math.cos(a) * 0.12, MZ + math.sin(a) * 0.12), (0.012, 0.03, 0.09), "paint_black", rot=(math.degrees(a), 0, 0))
for sy in (-1, 1):
    hp.box2((0.6, 1.75 + sy * 0.17 - 0.06, PAD + 0.81), (1.2, 1.75 + sy * 0.17 + 0.06, MZ - 0.17), "paint_blue", bevel=0.006, seg=1)
hp.box2((0.75, 1.62, MZ + 0.24), (1.05, 1.88, MZ + 0.38), "paint_blue", bevel=0.01, seg=2)
hp.cyl((0.9, 1.88, MZ + 0.31), (0.9, 1.98, MZ + 0.31), 0.03, "plastic_black", sides=10)
hp.cyl((1.26, 1.75, MZ), (1.46, 1.75, MZ), 0.22, STEEL, r1=0.15, sides=24)
hp.cyl((1.46, 1.75, MZ), (1.86, 1.75, MZ), 0.14, DARK, sides=24, bevel=0.008, seg=1)
hp.cyl((1.86, 1.75, MZ), (1.92, 1.75, MZ), 0.12, DARK, sides=24)
hp.box2((1.48, 1.62, PAD + 0.81), (1.84, 1.88, MZ - 0.1), DARK, bevel=0.006, seg=1)
hp.hose((1.66, 1.62, MZ + 0.08), (0, -1, 0), (1.3, 1.02, PAD + 0.72), (0, 1, 0), 0.03, "hose_red", reach=0.3)
hp.box2((0.7, 1.02, PAD + 0.46), (1.56, 1.1, PAD + 0.72), STEEL, bevel=0.008, seg=1)       # valve manifold
for i in range(5):
    x = 0.82 + i * 0.16
    hp.box2((x - 0.05, 0.96, PAD + 0.5), (x + 0.05, 1.02, PAD + 0.68), "paint_black", bevel=0.004, seg=1)
    hp.cyl((x, 0.96, PAD + 0.62), (x, 0.9, PAD + 0.62), 0.02, STEEL, sides=6)
# oil cooler: exposed fin core in a frame, fan shroud + guard (fan spins separately)
CY0, CY1 = 2.46, 2.74
for x in (0.42, 1.98):
    hp.box2((x - 0.04, CY0, PAD + 0.14), (x + 0.04, CY1, PAD + 1.3), DARK, bevel=0.006, seg=1)
for z in (PAD + 0.14, PAD + 1.26):
    hp.box2((0.42, CY0, z), (1.98, CY1, z + 0.04), DARK, bevel=0.006, seg=1)
hp.box2((0.46, CY0 + 0.05, PAD + 0.18), (1.94, CY1 - 0.06, PAD + 1.26), "steel_dark")
for k in range(22):
    z = PAD + 0.22 + k * 0.047
    hp.box2((0.46, CY1 - 0.06, z), (1.94, CY1 - 0.045, z + 0.018), "aluminium")
for x in (0.62, 1.78):
    hp.cyl((x, 2.3, PAD + 1.2), (x, CY0, PAD + 1.2), 0.07, DARK, sides=14)
hp.lathe((1.2, CY1, PAD + 0.71), (0, 1, 0), [(0.52, 0), (0.52, 0.02), (0.47, 0.06), (0.47, 0.13), (0.49, 0.15)], DARK, sides=32, caps=False)
for k in range(5):
    hp.torus((1.2, CY1 + 0.16, PAD + 0.71), (0, 1, 0), 0.09 + k * 0.088, 0.006, STEEL, seg=32, rseg=4)
for k in range(8):
    a = k * math.tau / 8
    hp.cyl((1.2, CY1 + 0.16, PAD + 0.71), (1.2 + math.cos(a) * 0.46, CY1 + 0.16, PAD + 0.71 + math.sin(a) * 0.46), 0.006, STEEL, sides=4)
hp.cyl((1.2, CY1 + 0.16, PAD + 0.71), (1.2, CY1 + 0.06, PAD + 0.71), 0.06, DARK, sides=12)
for x in (0.3, 2.1):                                                      # lifting frame
    for y in (1.04, 2.96):
        hp.cyl((x, y, PAD + 0.12), (x, y, PAD + 1.7), 0.035, YEL, sides=12)
for y in (1.04, 2.96):
    hp.cyl((0.3, y, PAD + 1.7), (2.1, y, PAD + 1.7), 0.035, YEL, sides=12)
for x in (0.3, 2.1):
    hp.cyl((x, 1.04, PAD + 1.7), (x, 2.96, PAD + 1.7), 0.035, YEL, sides=12)
    for y in (1.04, 2.96):
        hp.torus((x, y, PAD + 1.76), (1, 0, 0), 0.04, 0.012, DARK, seg=12, rseg=6)
# fire extinguisher on the rear-right post
fx_, fy_ = 2.1, 3.04
hp.box2((fx_ - 0.06, fy_ - 0.06, PAD + 0.62), (fx_ + 0.06, fy_ - 0.02, PAD + 0.66), DARK)
hp.lathe((fx_, fy_ + 0.05, PAD + 0.38), (0, 0, 1), [(0.0, 0), (0.075, 0), (0.08, 0.02), (0.08, 0.42), (0.06, 0.48), (0.025, 0.5), (0, 0.5)],
         "paint_red", sides=16)
hp.cyl((fx_, fy_ + 0.05, PAD + 0.88), (fx_, fy_ + 0.05, PAD + 0.96), 0.022, STEEL, sides=8)
hp.box((fx_ + 0.04, fy_ + 0.05, PAD + 0.95), (0.1, 0.02, 0.015), "paint_black", rot=(0, -12, 0))
hp.tube(lib.catmull([V(fx_ + 0.02, fy_ + 0.05, PAD + 0.92), V(fx_ + 0.1, fy_ + 0.1, PAD + 0.85), V(fx_ + 0.09, fy_ + 0.12, PAD + 0.55),
                     V(fx_ + 0.06, fy_ + 0.12, PAD + 0.5)], 5), 0.01, "rubber", sides=6)
# electrical starter cabinet (faces the drift)
hp.box2((-0.78, 2.42, PAD), (0.12, 2.9, PAD + 0.1), DARK, bevel=0.004, seg=1)
hp.box2((-0.75, 2.45, PAD + 0.1), (0.09, 2.86, PAD + 1.42), "paint_grey", bevel=0.012, seg=2)
hp.box2((-0.72, 2.86, PAD + 0.14), (0.06, 2.88, PAD + 1.38), "paint_grey", bevel=0.006, seg=1)
for z in (0.3, 1.2):
    hp.cyl((-0.73, 2.875, PAD + z), (-0.73, 2.875, PAD + z + 0.1), 0.015, STEEL, sides=8)
hp.box2((-0.02, 2.88, PAD + 0.62), (0.02, 2.92, PAD + 0.86), "paint_black", bevel=0.004, seg=1)
hp.cyl((-0.33, 2.88, PAD + 1.0), (-0.33, 2.93, PAD + 1.0), 0.07, YEL, sides=16)
hp.box((-0.33, 2.945, PAD + 1.0), (0.12, 0.03, 0.03), "paint_red", rot=(0, 30, 0))
for i, em in enumerate(("emit_green", "emit_amber", "emit_red")):
    x = -0.58 + i * 0.09
    hp.cyl((x, 2.88, PAD + 1.22), (x, 2.9, PAD + 1.22), 0.026, STEEL, sides=12)
    hp.cyl((x, 2.9, PAD + 1.22), (x, 2.915, PAD + 1.22), 0.02, em, sides=12)
hp.box2((-0.78, 2.42, PAD + 1.42), (0.12, 2.92, PAD + 1.46), "paint_grey", bevel=0.004, seg=1)
hp.grille((-0.33, 2.455 - 0.0, PAD + 0.45), 0.4, 0.18, 5, (0, -1, 0), "paint_grey", depth=0.02)
static.append(hp.finish(root))

fan = Part("hpu_fan", pivot=(1.2, CY1 + 0.09, PAD + 0.71), axis=(0, 1, 0))
fan.cyl((1.2, CY1 + 0.05, PAD + 0.71), (1.2, CY1 + 0.13, PAD + 0.71), 0.07, DARK, sides=14)
for k in range(7):
    a = k * math.tau / 7
    with fan.at((1.2, CY1 + 0.09, PAD + 0.71), Matrix.Rotation(a, 4, "Y")):
        fan.box((0.24, 0, 0), (0.33, 0.012, 0.11), "plastic_black", rot=(28, 0, 0), bevel=0.003, seg=1)
fan_ob = fan.finish(root)

# =============================================================================== operator console (rear -X, faces the derrick)
cs = Part("console")
X0, X1 = -1.8, -0.9
prof = [(1.05, PAD), (1.40, PAD), (1.40, PAD + 0.08), (1.36, PAD + 0.1), (1.47, PAD + 0.73), (1.05, PAD + 0.97)]
cs.prism((X0, 0, 0), (X1, 0, 0), prof, "paint_grey", up=(0, 0, 1), bevel=0.012, seg=2)
cs.box2((X0 - 0.03, 1.02, PAD), (X1 + 0.03, 1.43, PAD + 0.05), DARK, bevel=0.004, seg=1)
# operator-side door with louvres, hinges, latch, nameplate recess
cs.slab([V(X0 + 0.07, 1.41, PAD + 0.16), V(X1 - 0.07, 1.41, PAD + 0.16), V(X1 - 0.07, 1.435, PAD + 0.6), V(X0 + 0.07, 1.435, PAD + 0.6)],
          0.012, "paint_grey", bevel=0.004, seg=1)
for k in range(6):
    z = PAD + 0.22 + k * 0.035
    cs.box((-1.35, 1.43 + (z - PAD - 0.16) * 0.06, z), (0.5, 0.012, 0.012), "paint_black", rot=(30, 0, 0))
for z in (PAD + 0.22, PAD + 0.54):
    cs.cyl((X0 + 0.06, 1.425, z), (X0 + 0.06, 1.425, z + 0.06), 0.012, STEEL, sides=8)
cs.box((X1 - 0.11, 1.445, PAD + 0.42), (0.03, 0.02, 0.08), "paint_black", bevel=0.004, seg=1)
PN = V(0, 0.496, 0.868)
PU = V(0, -0.868, 0.496)


def panel(x, t):
    return V(x, 1.47 - 0.42 * t, PAD + 0.73 + 0.24 * t)


with cs.at(V(-1.35, 1.0, PAD + 1.17), (-12, 0, 0)):                         # screen pod
    cs.box((0, 0, 0), (0.56, 0.1, 0.38), "paint_black", bevel=0.012, seg=2)
    cs.box((0, -0.02, 0.21), (0.6, 0.22, 0.03), "paint_black", bevel=0.006, seg=1)
    for s in (-1, 1):
        cs.box((s * 0.29, 0.04, 0.0), (0.02, 0.16, 0.4), "paint_black", bevel=0.004, seg=1)
cs.box((-1.35, 1.06, PAD + 0.96), (0.12, 0.08, 0.1), "paint_black")
for x in (-1.6, -1.15):                                                    # joysticks
    p = panel(x, 0.3)
    cs.cyl(p, p + PN * 0.012, 0.07, DARK, sides=16)
    cs.lathe(p + PN * 0.01, PN, [(0.055, 0), (0.05, 0.02), (0.035, 0.05), (0.015, 0.07), (0, 0.07)], "rubber", sides=14)
    cs.cyl(p + PN * 0.06, p + PN * 0.16 + V(0.0, -0.02, 0), 0.011, "chrome", sides=8)
    cs.sphere(p + PN * 0.17 + V(0, -0.02, 0), 0.03, "plastic_black", seg=12, rings=6, scale=(1, 1, 1.25))
for i, em in enumerate(("emit_green", "emit_amber", "emit_red")):          # push buttons
    p = panel(-1.455 + i * 0.075, 0.24)
    cs.cyl(p, p + PN * 0.012, 0.024, STEEL, sides=12)
    cs.cyl(p + PN * 0.012, p + PN * 0.026, 0.017, em, sides=12)
p = panel(-0.985, 0.6)                                                     # E-stop
cs.cyl(p, p + PN * 0.01, 0.055, "plastic_yellow", sides=16)
cs.cyl(p + PN * 0.01, p + PN * 0.04, 0.02, "plastic_black", sides=10)
cs.lathe(p + PN * 0.04, PN, [(0.045, 0), (0.045, 0.02), (0.035, 0.035), (0, 0.04)], "paint_red", sides=16)
p = panel(-1.36, 0.5)                                                      # key switch
cs.cyl(p, p + PN * 0.015, 0.02, "chrome", sides=10)
cs.box(p + PN * 0.02, (0.006, 0.03, 0.006), "brass", rot=(-60, 0, 0))
for i in range(3):
    cs.cyl((-1.55 + i * 0.12, 1.4, PAD + 0.1), (-1.55 + i * 0.12, 1.46, PAD + 0.1), 0.025, "plastic_black", sides=10)
for x, s in ((X0 - 0.02, 1), (X1 + 0.02, -1)):
    cs.tube([V(x, 1.42, PAD + 0.62), V(x - s * 0.05, 1.44, PAD + 0.62), V(x - s * 0.05, 1.2, PAD + 0.86), V(x, 1.18, PAD + 0.86)],
            0.012, "chrome", sides=8)
static.append(cs.finish(root))

# =============================================================================== cable trays + hoses + toolbox (static)
tr = Part("services")


def ladder_tray(path, w=0.3, z=PAD + 0.05, rung=0.3):
    for i in range(len(path) - 1):
        a, b = V(*path[i], z), V(*path[i + 1], z)
        d = (b - a).normalized()
        sd = d.cross(V(0, 0, 1))
        for s in (-1, 1):
            start = a - d * w / 2 if i == 0 else a
            tr.channel(start + sd * s * w / 2, b + sd * s * w / 2 + d * w / 2, 0.07, 0.025, GALV, up=(0, 0, 1))
        n = int((b - a).length / rung)
        for k in range(n + 1):
            q = a.lerp(b, k / max(n, 1))
            tr.box(q - V(0, 0, 0.028), tuple(abs(c) for c in (sd * w + d * 0.03 + V(0, 0, 0.012))), GALV)
        for s in (-1, 1):
            for k in range(0, n + 1, 2):
                q = a.lerp(b, k / max(n, 1)) + sd * s * (w / 2 + 0.02)
                tr.box2(q - V(0.02, 0.02, z - PAD), q + V(0.02, 0.02, -0.03), DARK)


ladder_tray([(-0.4, 2.3), (-1.35, 2.3), (-1.35, 1.55)])
ladder_tray([(0.62, 0.92), (0.62, -0.35)], w=0.34)
for k, off in enumerate((-0.08, 0.0, 0.08)):
    pts = [V(-0.34, 2.42, PAD + 0.6), V(-0.36, 2.36, PAD + 0.2), V(-0.5, 2.3 + off, PAD + 0.05), V(-1.25, 2.3 + off, PAD + 0.05),
           V(-1.35 + off, 2.2, PAD + 0.05), V(-1.35 + off, 1.65, PAD + 0.05), V(-1.55 + k * 0.12, 1.5, PAD + 0.1)]
    tr.cable(pts, 0.018 if k != 1 else 0.026, sides=6)
tr.cable([V(-0.1, 2.6, PAD + 0.12), V(-0.05, 2.9, PAD + 0.04), V(0.2, 3.15, PAD + 0.035), V(0.6, 3.28, 0.04), V(1.2, 3.45, 0.04)],
         0.034, sides=8)
cols = ["hose_red", "rubber", "hose_yellow", "rubber", "hose_red", "rubber"]
for i, col in enumerate(cols):
    x0 = 0.82 + (i % 5) * 0.16
    off = (i - 2.5) * 0.05
    ctrl = [V(x0, 0.9, PAD + 0.62), V(x0, 0.82, PAD + 0.55), V(0.62 + off * 0.9, 0.82, PAD + 0.1), V(0.62 + off, 0.5, PAD + 0.06),
            V(0.62 + off, -0.3, PAD + 0.06)]
    if i < 2:
        ctrl += [V(0.5 + i * 0.14, DY + 0.98, PAD + 0.1), V(0.33 + i * 0.14, DY + 0.9, B0 + 0.24)]
    else:
        ctrl += [V(0.75 + off * 0.4, DY + 0.5, PAD + 0.12), V(0.8 + off * 0.4, DY + 0.26, PAD + 0.5),
                 V(0.8 + off * 0.4, DY + 0.24, 1.3), V(0.86 + off * 0.5, DY + 0.26, HZ - 0.3)]
    tr.cable(ctrl, 0.022, m=col, sides=7, res=5)
for z in (0.9, 1.25, 1.5):
    tr.box2((0.68, DY + 0.19, z - 0.03), (1.0, DY + 0.32, z + 0.03), DARK, bevel=0.004, seg=1)
# toolbox by the console
tbx, tby = -2.0, 0.55
tr.box2((tbx - 0.28, tby - 0.14, PAD), (tbx + 0.28, tby + 0.14, PAD + 0.26), "paint_red", bevel=0.012, seg=2)
tr.box2((tbx - 0.29, tby - 0.15, PAD + 0.26), (tbx + 0.29, tby + 0.15, PAD + 0.3), "paint_red", bevel=0.01, seg=2)
tr.tube([V(tbx - 0.12, tby, PAD + 0.3), V(tbx - 0.1, tby, PAD + 0.36), V(tbx + 0.1, tby, PAD + 0.36), V(tbx + 0.12, tby, PAD + 0.3)],
        0.01, "plastic_black", sides=6)
for s in (-1, 1):
    tr.box2((tbx + s * 0.26 - 0.02, tby + 0.14, PAD + 0.2), (tbx + s * 0.26 + 0.02, tby + 0.16, PAD + 0.28), STEEL)
tr.box((tbx + 0.05, tby - 0.3, PAD + 0.01), (0.45, 0.04, 0.02), STEEL, rot=(0, 0, 12))           # pipe wrench on the pad
tr.box((tbx + 0.27, tby - 0.25, PAD + 0.025), (0.08, 0.06, 0.05), STEEL, rot=(0, 0, 12), bevel=0.006, seg=1)
static.append(tr.finish(root))

# =============================================================================== cuttings pile + lumps in the chute (fx_ore)
pl = Part("cuttings", smooth=False, wn=False)
lib.pile(pl, (-1.52, DY - 0.84, PAD), 0.75, 0.6, 0.36, ["gold_ore", "rock_pale", "gold_ore", "gravel"], n=40, seed=7)
for k in range(9):
    q = c0.lerp(c1, 0.55 + k * 0.05) + nrm * 0.04 + side * ((k % 3) - 1) * 0.1
    pl.ico(q, 0.045 + (k % 2) * 0.02, "rock_pale" if k % 2 else "gold_ore", detail=1, scale=(1, 1, 0.7), seed=40 + k,
           rot=(k * 20, k * 31, k * 47))
static.append(pl.finish(root))

# =============================================================================== gauges, decals, screen
dec = Part("decals", grime=False, smooth=False)
needles = []
gz = Part("gauges")
for i, cell in enumerate(("g_bar", "g_rpm", "g_knm", "g_temp")):
    p = panel((-1.68, -1.545, -1.26, -1.125)[i], 0.76)
    needles.append(lib.gauge(gz, dec, ATL, cell, p + PN * 0.02, PN, PU, 0.056, f"needle_{i}", root))
needles.append(lib.gauge(gz, dec, ATL, "g_bar", V(1.75, 1.055, PAD + 0.6), (0, -1, 0), (0, 0, 1), 0.06, "needle_4", root))
static.append(gz.finish(root))
with dec.at(V(-1.35, 1.0, PAD + 1.17), (-12, 0, 0)):
    lib.decal(dec, (0, 0.052, -0.01), (0, 1, 0), (0, 0, 1), 0.5, 0.3, "custom_screen_rb7", lib.cell_uv(f"scr_{ID}", "main"), off=0.0)
for x, t, cell, w in ((-1.6, 0.11, "l_rot", 0.15), (-1.15, 0.11, "l_thr", 0.15), (-1.38, 0.1, "l_pump", 0.15), (-0.985, 0.42, "l_estop", 0.12)):
    lib.decal_cell(dec, ATL, cell, panel(x, t) + PN * 0.001, PN, PU, w=w)
for sy, n in ((-1, (0, -1, 0)), (1, (0, 1, 0))):
    lib.decal_cell(dec, ATL, "mk", (0, DY + sy * 0.25, CZ0 + 0.13), n, (0, 0, 1), h=0.18)
for sx in (-1, 1):
    lib.decal_cell(dec, ATL, "badge", (sx * 0.86, DY - 0.17, 2.55), (0, -1, 0), (0, 0, 1), w=0.25)
    lib.decal_cell(dec, ATL, "warn_rot", (sx * (0.86 + 0.152), DY, 1.42), (sx, 0, 0), (0, 0, 1), w=0.22)
lib.decal_cell(dec, ATL, "warn_crush", (0.86, DY + 0.17, 1.1), (0, 1, 0), (0, 0, 1), w=0.25)
lib.decal_cell(dec, ATL, "plate", (-0.5, DY - 0.72, B0 + 0.22), (0, -1, 0), (0, 0, 1), w=0.27)
lib.decal_cell(dec, ATL, "serial", (0.45, DY - 0.72, B0 + 0.22), (0, -1, 0), (0, 0, 1), w=0.4)
lib.decal_cell(dec, ATL, "warn_hyd", (2.081, 1.75, PAD + 0.47), (1, 0, 0), (0, 0, 1), w=0.34)
lib.decal_cell(dec, ATL, "mk", (0.321, 1.75, PAD + 0.6), (-1, 0, 0), (0, 0, 1), h=0.1)
lib.decal_cell(dec, ATL, "oil", (0.321, 1.75, PAD + 0.38), (-1, 0, 0), (0, 0, 1), w=0.36)
lib.decal_cell(dec, ATL, "l_hpu", (-0.33, 2.881, PAD + 1.32), (0, 1, 0), (0, 0, 1), w=0.2)
lib.decal_cell(dec, ATL, "ppe", (-0.33, 2.881, PAD + 0.66), (0, 1, 0), (0, 0, 1), w=0.42)
lib.decal_cell(dec, ATL, "rods", (2.341, DY - 0.0, PAD + 0.97), (1, 0, 0), (0, 0, 1), w=0.9)
lib.decal_cell(dec, ATL, "lift", (0.72, DY + 0.27, CZ1 - 0.08), (0, 1, 0), (0, 0, 1), w=0.2)
lib.decal_cell(dec, ATL, "lift", (-0.72, DY + 0.27, CZ1 - 0.08), (0, 1, 0), (0, 0, 1), w=0.2)
for y in (DY - 0.98, DY + 0.98):
    lib.stripe(dec, (0, y + (0.06 if y < DY else -0.06), B0), (0, 0, 1), (0, 1, 0), 2.5, 0.12, period=0.24)
for x in (-1.32, 1.32):
    lib.stripe(dec, (x + (0.06 if x < 0 else -0.06), DY, B0), (0, 0, 1), (1, 0, 0), 1.84, 0.12, period=0.24)
lib.stripe(dec, (0, DY - 0.82 - 0.001, B0 + 0.025), (0, -1, 0), (0, 0, 1), 2.1, 0.05, period=0.1)
dec.finish(root)
dh = Part("decals_head", grime=False, smooth=False, pivot=(0, DY, HZ))
lib.decal_cell(dh, ATL, "mk", (0, DY - 0.32, HZ + 0.16), (0, -1, 0), (0, 0, 1), h=0.1)
lib.decal_cell(dh, ATL, "mk", (0, DY + 0.32, HZ + 0.16), (0, 1, 0), (0, 0, 1), h=0.1)
for sy in (-1, 1):
    lib.stripe(dh, (0, DY + sy * 0.301, HZ + 0.045), (0, sy, 0), (0, 0, 1), 1.4, 0.07, period=0.14)
dh.finish(head)

body = lib.merge(static, "body")

# =============================================================================== empties
lib.empty("fx_work", (0, DY, 4.45), root)
lib.empty("fx_ore", (-1.52, DY - 0.84, PAD + 0.36), root)
lib.empty("light_0", (0.52, DY - 0.39, CZ0 + 0.11), root, aim=(-0.15, -0.45, -1.0))
lib.empty("light_1", (-0.82, DY - 0.31, CZ0 - 0.09), root, aim=(0.55, 0.12, 1.0))
lib.empty("op", (-1.35, 1.9, PAD), root, face=(0, -1, 0))
lib.empty("snd", (0, DY, HZ + 0.6), root)

# =============================================================================== animation
# Work: string 2 rev / 4 s (30 rpm), head creeps up 8 cm then settles, HPU fan, gauges flicker
lib.spin(string, "Work", WORK, turns=2)
lib.track(head, "Work", "location", 2, [(0, 0.0), (96, 0.08), (WORK, 0.0)])
lib.spin(fan_ob, "Work", WORK, turns=-8)
for i, (ob, val, jit) in enumerate(zip(needles, (175, 126, 128, 101, 190), (6, 3, 10, 1.5, 8))):
    lib.needle_keys(ob, "Work", WORK, val, jit, step=7, seed=11 + i)
for ob in [string, head, fan_ob] + needles:          # Idle = power off: rest pose, needles on zero
    lib.hold(ob, "Idle", IDLE)
lib.bake_clips()

# =============================================================================== grime, export, report
meshes = [o for o in lib.descendants(root) if o.type == "MESH" and o.get("grime")]
lib.bake_grime(meshes, distance=0.4, samples=64, floor_z=0.0)
path, js, anims, names = lib.export(root, OUT)
size = lib.report(root, "<= 5.6 W x 7.6 L x 3.9 H (pipe to 4.9 by brief)")
missing = [n for n in (ID, "fx_work", "fx_ore", "light_0", "light_1", "op", "snd") if n not in names]
print("[mb] missing nodes:", missing)

if PREVIEW:
    lib.ceiling(4.5, 0, DY, 3.2, 3.0, hole=(0, DY, 0.25))
    lib.previews(ID, root, [
        dict(name="34", az=32, el=14, fill=0.95),
        dict(name="side", az=90, el=6, fill=0.95),
        dict(name="rear", az=205, el=15, fill=0.95),
        dict(name="close", az=25, el=6, target=(0, DY, 2.6), dist=2.8, lens=35),
        dict(name="console", az=200, el=24, target=(-1.35, 1.25, 1.05), dist=1.6, lens=35),
    ], frame=40)
