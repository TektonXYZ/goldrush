"""Sutter Works ML-X "The Motherlode Rig": deep drill + crusher + induction smelter + ingot casting line.

    systemd-run --user --scope -q -p MemoryMax=3G -p MemorySwapMax=0 \
        bl assets/machines_b/motherlode.py -- public/models/machines/motherlode [--no-preview]

Level-4 cavern machine (<= 8 W x 10 L x 5.6 H). Blender axes, front (drill end) = -Y = three.js +Z.
One green Sutter skid with a chequer deck:
  back-right   derrick: lattice mast, top drive with swivel + rotary hose, drill string down through
               the drill floor into the ground (fx_work), pipe rack + handling arm
  back-left    ore bin, cone crusher (belt drive), bucket elevator and charge chute to the furnace
  centre       induction furnace tilting on trunnions at its spout lip (pour point fixed: fx_pour),
               heat shields, fume hood + duct to a scrubber tower and stack, induction power cabinet
               with copper bus bars and water-cooled cables
  front        indexing ingot-mold conveyor (molten fill -> cooled gold bar), quench tank, caged
               gold room with a pallet of stamped bars (fx_ore), lit control cabin (op)
Work 6 s: drill string spins, crucible tilts, pours a glowing stream, returns; molds index one pitch.
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

ID = "motherlode"
args = bk.args()
OUT = os.path.abspath(args[0]) if args and not args[0].startswith("--") else os.path.join(lib.PROJECT, "public/models/machines", ID)
PREVIEW = "--no-preview" not in args

bk.reset()
bpy.context.scene.render.fps = lib.FPS
WORK, IDLE = 180, 60
ATL = ID
lib.label(f"label_{ID}_decals", os.path.join(lib.DECALS, f"{ID}.png"))
lib.std_materials()
lib.water_material()
lib.molten_material()
lib.label("custom_screen_mlx", os.path.join(lib.DECALS, f"scr_{ID}.png"), mode="OPAQUE", emit=2.2, rough=0.25)

GRN, YEL, DARK, STEEL, GALV = "paint_green", "paint_yellow", "steel_dark", "steel", "galvanized"
root = lib.root(ID)
static = []
rng = random.Random(9)
DZ = 0.4                                        # deck top

WX, WY = 2.1, -3.15                             # drill centre
FX, FY, FZ = -0.45, -0.15, 2.7                  # furnace trunnion / spout lip (pour pivot)
FR, FH = 0.72, 1.45                             # furnace shell radius, height
FCY = FY - FR                                   # furnace axis y
MY = FY + 0.42                                  # mold line y
P = 0.42                                        # mold pitch
XS = [FX - P + s * P for s in range(7)]         # station x: s=0..6 (s=1 under the spout, s=6 drops into the tank)
MZ = 0.95                                       # mold seat height (top of the rails)

# =============================================================================== skid + deck + front steps
sk = Part("skid")
for x in (-3.65, 0.0, 3.65):
    sk.ibeam(V(x, -4.75, 0.18), V(x, 4.75, 0.18), 0.36, 0.22, GRN)
for y in (-4.65, -2.3, 0.0, 2.3, 4.65):
    sk.ibeam(V(-3.65, y, 0.18), V(3.65, y, 0.18), 0.32, 0.18, GRN)
sk.deck(V(-3.75, -4.75, DZ - 0.04), V(3.75, 4.75, DZ), top="custom_chequer", side=STEEL)
for k in range(2):
    sk.box2((-0.9, 4.75, DZ * (1 - (k + 1) / 3) - 0.04), (0.9, 4.95 - k * 0.1, DZ * (1 - (k + 1) / 3)), "custom_chequer")
sk.handrail([V(-3.72, 4.7, DZ), V(-3.72, -4.7, DZ)], h=1.05, posts=1.3)
sk.handrail([V(3.72, -4.7, DZ), V(3.72, 4.7, DZ)], h=1.05, posts=1.3)
static.append(sk.finish(root))

# =============================================================================== derrick: mast, drill floor, wellhead, pipe rack, handler
dk = Part("derrick")
MXc, MYc = WX, WY - 0.72                       # mast centre (behind the drill centre)
for sx in (-1, 1):
    for sy in (-1, 1):
        dk.angle_iron(V(MXc + sx * 0.34, MYc + sy * 0.3, DZ + 0.25), V(MXc + sx * 0.34, MYc + sy * 0.3, 5.3), 0.09, YEL,
                      up=(sx, 0, 0) if sy > 0 else (0, sy, 0))
for k in range(8):                                                                  # lacing + diagonals
    z = DZ + 0.5 + k * 0.56
    for sy in (-1, 1):
        dk.cyl(V(MXc - 0.34, MYc + sy * 0.3, z), V(MXc + 0.34, MYc + sy * 0.3, z), 0.018, YEL, sides=6)
        dk.cyl(V(MXc - 0.34, MYc + sy * 0.3, z), V(MXc + 0.34, MYc + sy * 0.3, z + 0.56), 0.016, YEL, sides=6)
    for sx in (-1, 1):
        dk.cyl(V(MXc + sx * 0.34, MYc - 0.3, z), V(MXc + sx * 0.34, MYc + 0.3, z), 0.018, YEL, sides=6)
        dk.cyl(V(MXc + sx * 0.34, MYc - 0.3, z), V(MXc + sx * 0.34, MYc + 0.3, z + 0.56), 0.016, YEL, sides=6)
dk.box2((MXc - 0.45, MYc - 0.4, 5.25), (MXc + 0.45, WY + 0.15, 5.45), YEL, bevel=0.015, seg=2)        # crown
for k in range(3):
    dk.cyl(V(MXc - 0.3 + k * 0.3, WY - 0.05, 5.38), V(MXc - 0.3 + k * 0.3, WY + 0.12, 5.38), 0.1, DARK, sides=14)
for sx in (-1, 1):                                                                    # guide rails for the top drive
    dk.box2((MXc + sx * 0.28 - 0.04, MYc + 0.3, DZ + 0.8), (MXc + sx * 0.28 + 0.04, MYc + 0.38, 5.2), STEEL)
dk.cyl(V(MXc + 0.42, MYc + 0.2, DZ + 0.3), V(MXc + 0.42, MYc + 0.2, 4.6), 0.05, STEEL, sides=10)      # standpipe
dk.ladder(V(MXc - 0.5, MYc - 0.1, DZ + 0.3), V(MXc - 0.5, MYc - 0.1, 5.1), w=0.36, m=YEL)
# drill floor, rotary table, slips, wellhead below
dk.deck(V(WX - 0.85, WY - 0.75, DZ + 0.22), V(WX + 0.85, WY + 0.75, DZ + 0.28), top="custom_chequer", side=GRN)
for sx in (-1, 1):
    for sy in (-1, 1):
        dk.box2((WX + sx * 0.78 - 0.05, WY + sy * 0.68 - 0.05, DZ), (WX + sx * 0.78 + 0.05, WY + sy * 0.68 + 0.05, DZ + 0.22), GRN)
dk.cyl(V(WX, WY, DZ + 0.28), V(WX, WY, DZ + 0.36), 0.46, DARK, sides=28, bevel=0.008, seg=1)
dk.bolt_ring(V(WX, WY, DZ + 0.36), (0, 0, 1), 0.4, 12, r=0.014)
dk.cyl(V(WX, WY, 0.0), V(WX, WY, DZ + 0.22), 0.26, DARK, sides=20)
dk.cyl(V(WX, WY, DZ - 0.02), V(WX, WY, DZ + 0.06), 0.34, STEEL, sides=20, bevel=0.006, seg=1)
dk.handrail([V(WX - 0.82, WY + 0.72, DZ + 0.28), V(WX + 0.82, WY + 0.72, DZ + 0.28)], h=0.95, posts=0.8)
# pipe rack behind the mast + spare drill pipe
for x in (0.35, 1.55, 2.95):
    dk.box2((x - 0.05, -4.62, DZ), (x + 0.05, -4.18, DZ + 0.62), YEL, bevel=0.006, seg=1)
    dk.box2((x - 0.06, -4.66, DZ + 0.62), (x + 0.06, -4.14, DZ + 0.68), YEL)
for k in range(5):
    y = -4.58 + k * 0.1 + (0.05 if k > 2 else 0)
    z = DZ + 0.77 + (0.16 if k > 2 else 0)
    if k > 2:
        y = -4.53 + (k - 3) * 0.2
    dk.cyl(V(0.15, y, z), V(3.2, y, z), 0.085, DARK, sides=12)
    dk.cyl(V(0.15, y, z), V(0.4, y, z), 0.1, STEEL, sides=12)
    dk.lathe(V(3.2, y, z), (1, 0, 0), [(0.085, 0.0), (0.09, 0.0), (0.09, 0.08), (0.0, 0.1)], "plastic_yellow", sides=12)
# pipe handling arm from the mast base
dk.cyl(V(MXc - 0.75, MYc + 0.2, DZ), V(MXc - 0.75, MYc + 0.2, DZ + 1.2), 0.11, GRN, sides=16, bevel=0.008, seg=1)
dk.prism(V(MXc - 0.75, MYc + 0.2, DZ + 1.15), V(1.0, -4.0, DZ + 1.75), [(-0.08, -0.08), (0.08, -0.08), (0.08, 0.08), (-0.08, 0.08)], YEL,
         up=(0, 0, 1), bevel=0.01, seg=1)
dk.hyd_cyl(V(MXc - 0.75, MYc + 0.05, DZ + 0.6), V(1.6, -3.85, DZ + 1.55), 0.05, 0.03, m_barrel=YEL, frac=0.55, ports=False)
dk.box2((0.85, -4.12, DZ + 1.55), (1.15, -3.88, DZ + 1.82), YEL, bevel=0.01, seg=1)
dk.cyl(V(0.6, -4.0, DZ + 1.45), V(1.45, -4.0, DZ + 1.45), 0.085, DARK, sides=12)
dk.led_light(V(MXc, WY + 0.1, 5.18), (0, 0.2, -1.0), w=0.34, h=0.12)
static.append(dk.finish(root))

# top drive (creeps) + drill string (spins)
TDZ = 3.25
td = Part("top_drive", pivot=(WX, WY, TDZ))
td.box2((WX - 0.38, WY - 0.3, TDZ), (WX + 0.38, WY + 0.32, TDZ + 0.62), GRN, bevel=0.03, seg=2)
td.box2((WX - 0.34, WY - 0.72, TDZ + 0.05), (WX + 0.34, WY - 0.3, TDZ + 0.55), GRN, bevel=0.015, seg=1)     # carriage to the rails
for sx in (-1, 1):
    td.cyl(V(WX + sx * 0.2, WY, TDZ + 0.62), V(WX + sx * 0.2, WY, TDZ + 1.12), 0.15, "paint_grey", sides=20, bevel=0.008, seg=1)
    for k in range(3):
        td.torus(V(WX + sx * 0.2, WY, TDZ + 0.72 + k * 0.13), (0, 0, 1), 0.152, 0.008, "paint_grey", seg=18, rseg=4)
td.cyl(V(WX, WY, TDZ + 0.62), V(WX, WY, TDZ + 0.95), 0.1, STEEL, sides=16)                                    # swivel
td.tube(lib.catmull([V(WX, WY, TDZ + 0.95), V(WX, WY + 0.15, TDZ + 1.25), V(WX + 0.25, WY + 0.4, TDZ + 1.2),
                     V(MXc + 0.42, MYc + 0.35, 4.2), V(MXc + 0.42, MYc + 0.2, 4.6)], 6), 0.045, "rubber", sides=10)   # rotary hose
for sx in (-1, 1):                                                                                             # bails + elevator
    td.cyl(V(WX + sx * 0.2, WY + 0.05, TDZ), V(WX + sx * 0.22, WY + 0.05, TDZ - 0.75), 0.025, STEEL, sides=8)
td.box2((WX - 0.28, WY - 0.08, TDZ - 0.85), (WX + 0.28, WY + 0.18, TDZ - 0.72), YEL, bevel=0.01, seg=1)
top_drive = td.finish(root)

ds = Part("drill_string", pivot=(WX, WY, TDZ), axis=(0, 0, 1))
ds.cyl(V(WX, WY, TDZ + 0.02), V(WX, WY, TDZ - 0.25), 0.13, STEEL, sides=20, bevel=0.006, seg=1)
ds.cyl(V(WX, WY, TDZ - 0.25), V(WX, WY, 0.01), 0.085, DARK, sides=16, caps=(False, True))
for z in (1.75, TDZ - 0.4):
    ds.cyl(V(WX, WY, z), V(WX, WY, z + 0.2), 0.105, STEEL, sides=16)
for k in range(2):
    a = k * math.pi
    ds.box(V(WX + math.cos(a) * 0.086, WY + math.sin(a) * 0.086, 1.0), (0.012, 0.03, 1.1), YEL, rot=(0, 0, math.degrees(a)))
drill_string = ds.finish(top_drive)

# =============================================================================== ore bin, cone crusher, bucket elevator, charge chute
oc = Part("ore_line")
OBX, OBY = -2.1, -3.6
top_ = [V(OBX - 0.75, OBY - 0.75, 2.75), V(OBX + 0.75, OBY - 0.75, 2.75), V(OBX + 0.75, OBY + 0.75, 2.75), V(OBX - 0.75, OBY + 0.75, 2.75)]
bot_ = [V(OBX - 0.25, OBY - 0.25, 2.0), V(OBX + 0.25, OBY - 0.25, 2.0), V(OBX + 0.25, OBY + 0.25, 2.0), V(OBX - 0.25, OBY + 0.25, 2.0)]
oc.loft([bot_, top_], GRN, closed=True, caps=False)
import bmesh  # noqa: E402
fs = oc.loft([[p + (V(OBX, OBY, p.z) - p) * 0.04 for p in bot_], [p + (V(OBX, OBY, p.z) - p) * 0.04 for p in top_]], DARK, closed=True, caps=False)
bmesh.ops.reverse_faces(oc.bm, faces=fs)
for sx in (-1, 1):
    for sy in (-1, 1):
        oc.ibeam(V(OBX + sx * 0.75, OBY + sy * 0.75, DZ), V(OBX + sx * 0.75, OBY + sy * 0.75, 2.75), 0.14, 0.12, GRN, up=(0, 1, 0))
lib.pile(oc, V(OBX, OBY, 2.55), 0.62, 0.62, 0.32, ["gold_ore", "rock_pale", "gold_ore"], n=14, seed=4, lump=(0.07, 0.14))
oc.lathe(V(OBX, OBY, DZ + 0.15), (0, 0, 1), [(0.55, 0.0), (0.55, 0.55), (0.62, 0.62), (0.62, 0.75), (0.5, 0.95), (0.32, 1.15), (0.3, 1.3),
                                              (0.0, 1.3)], GRN, sides=28)                                   # cone crusher
oc.bolt_ring(V(OBX, OBY, DZ + 0.83), (0, 0, 1), 0.6, 16, r=0.016)
oc.box2((OBX - 0.6, OBY - 0.6, DZ), (OBX + 0.6, OBY + 0.6, DZ + 0.15), DARK, bevel=0.01, seg=1)
oc.cyl(V(OBX + 0.95, OBY - 0.3, DZ + 0.45), V(OBX + 0.95, OBY + 0.4, DZ + 0.45), 0.2, "paint_blue", sides=18, bevel=0.008, seg=1)   # motor
oc.box2((OBX + 0.7, OBY - 0.3, DZ), (OBX + 1.2, OBY + 0.4, DZ + 0.25), DARK)
for k in range(3):                                                                                           # V-belts
    y = OBY - 0.28 + k * 0.035
    oc.tube([V(OBX + 0.95, y, DZ + 0.6), V(OBX + 0.35, y, DZ + 0.75), V(OBX + 0.35, y, DZ + 0.45), V(OBX + 0.95, y, DZ + 0.3),
             V(OBX + 0.95, y, DZ + 0.6)], 0.012, "rubber", sides=5)
EX, EY = -1.95, -2.35                                                                                        # bucket elevator
oc.box2((EX - 0.3, EY - 0.42, DZ), (EX + 0.3, EY + 0.42, 4.55), GRN, bevel=0.015, seg=1)
for z in (1.2, 2.2, 3.2):
    oc.box2((EX - 0.32, EY - 0.44, z), (EX + 0.32, EY + 0.44, z + 0.06), GRN)
oc.box2((EX - 0.36, EY - 0.5, 4.55), (EX + 0.36, EY + 0.5, 5.05), GRN, bevel=0.03, seg=2)
oc.cyl(V(EX + 0.36, EY, 4.8), V(EX + 0.7, EY, 4.8), 0.16, "paint_blue", sides=16, bevel=0.008, seg=1)
oc.prism(V(OBX, OBY + 0.3, DZ + 0.5), V(EX, EY - 0.42, DZ + 0.3), [(-0.2, -0.02), (0.2, -0.02), (0.2, 0.15), (-0.2, 0.15)], DARK, up=(0, 0, 1))
oc.prism(V(EX + 0.3, EY + 0.2, 4.6), V(FX - 0.25, FCY - 0.2, 3.62), [(-0.2, -0.02), (0.2, -0.02), (0.2, 0.18), (-0.2, 0.18)], GRN, up=(0, 0, 1))
oc.ladder(V(EX - 0.32, EY + 0.3, DZ), V(EX - 0.32, EY + 0.3, 4.5), w=0.34, m=YEL)
static.append(oc.finish(root))
pul = Part("crusher_pulley", pivot=(OBX + 0.35, OBY - 0.26, DZ + 0.6), axis=(0, 1, 0))
pul.cyl(V(OBX + 0.35, OBY - 0.32, DZ + 0.6), V(OBX + 0.35, OBY - 0.18, DZ + 0.6), 0.16, "cast_iron", sides=18)
pul.box(V(OBX + 0.35, OBY - 0.33, DZ + 0.74), (0.03, 0.01, 0.04), YEL)
crusher_pulley = pul.finish(root)

# =============================================================================== furnace support, heat shields, hood, scrubber, power
fs_ = Part("smelter")
for sx in (-1, 1):                                                                    # trunnion pedestals + bearings
    x = FX + sx * 1.02
    fs_.box2((x - 0.16, FY - 0.25, DZ), (x + 0.16, FY + 0.25, FZ - 0.18), GRN, bevel=0.015, seg=2)
    fs_.box2((x - 0.2, FY - 0.28, FZ - 0.2), (x + 0.2, FY + 0.28, FZ + 0.18), DARK, bevel=0.02, seg=2)
    fs_.cyl(V(x - 0.21, FY, FZ), V(x + 0.21, FY, FZ), 0.12, STEEL, sides=18, bevel=0.006, seg=1)
    fs_.bolt_ring(V(x + sx * 0.2, FY, FZ), (sx, 0, 0), 0.15, 6, r=0.015)
fs_.box2((FX + 1.2, FY - 0.35, FZ - 0.25), (FX + 1.55, FY + 0.3, FZ + 0.2), GRN, bevel=0.012, seg=1)        # tilt gear drive
fs_.cyl(V(FX + 1.55, FY - 0.0, FZ), V(FX + 1.9, FY - 0.0, FZ), 0.16, "paint_blue", sides=16, bevel=0.008, seg=1)
fs_.box2((FX - 0.95, FCY - 0.95, DZ), (FX + 0.95, FCY + 0.85, DZ + 0.12), DARK)                              # spill pit plate
fs_.box2((FX - 0.85, FCY - 0.85, DZ + 0.12), (FX + 0.85, FCY + 0.75, DZ + 0.16), "brick")
for sx, ya, yb in ((-1, FCY - 1.1, FY + 0.05), (1, FCY - 1.1, FCY + 0.1)):                                    # heat shields
    x = FX + sx * 1.35
    for y in (ya, (ya + yb) / 2, yb):
        fs_.box2((x - 0.04, y - 0.04, DZ), (x + 0.04, y + 0.04, 2.7), GRN)
    fs_.box2((x - 0.01 + sx * 0.06, ya, DZ + 0.3), (x + 0.01 + sx * 0.06, yb, 2.6), "aluminium", bevel=0.004, seg=1)
    for z in (0.9, 1.7, 2.4):
        fs_.box2((x - 0.03, ya, z - 0.02), (x + 0.03, yb, z + 0.02), GRN)
# fume hood + duct + scrubber tower + stack
HZ = 4.0
hb = [V(FX - 1.05, FCY - 1.05, HZ), V(FX + 1.05, FCY - 1.05, HZ), V(FX + 1.05, FY + 0.35, HZ), V(FX - 1.05, FY + 0.35, HZ)]
ht = [V(FX - 0.38, FCY - 0.38, HZ + 0.62), V(FX + 0.38, FCY - 0.38, HZ + 0.62), V(FX + 0.38, FCY + 0.38, HZ + 0.62), V(FX - 0.38, FCY + 0.38, HZ + 0.62)]
fs_.loft([hb, ht], GALV, closed=True, caps=False)
fs_.loft([[p + V(0, 0, -0.005) for p in reversed(hb)], [p + V(0, 0, -0.005) for p in reversed(ht)]], GALV, closed=True, caps=False)
for p in hb:
    fs_.box(p + V(0, 0, 0.03), (0.08, 0.08, 0.06), GRN)
    fs_.ibeam(V(p.x, p.y, DZ), V(p.x, p.y, HZ), 0.14, 0.12, GRN, up=(0, 1, 0))
fs_.cyl(V(FX, FCY, HZ + 0.6), V(FX, FCY, 5.05), 0.34, GALV, sides=20)
fs_.lathe(V(FX, FCY, 5.05), (0, 0, 1), [(0.34, 0.0), (0.34, 0.08), (0.0, 0.12)], GALV, sides=20)
fs_.cyl(V(FX, FCY, 4.85), V(-2.85, FCY, 4.85), 0.3, GALV, sides=20)
for x in (FX - 0.6, -1.6, -2.3):
    fs_.torus(V(x, FCY, 4.85), (1, 0, 0), 0.305, 0.02, GALV, seg=20, rseg=4)
SCX, SCY = -3.05, FCY
fs_.cyl(V(SCX, SCY, DZ + 0.6), V(SCX, SCY, 4.55), 0.55, "paint_grey", sides=28, bevel=0.015, seg=2)
fs_.lathe(V(SCX, SCY, 4.55), (0, 0, 1), [(0.55, 0.0), (0.2, 0.42), (0.2, 0.46)], "paint_grey", sides=28, caps=False)
fs_.cyl(V(SCX, SCY, 4.95), V(SCX, SCY, 5.55), 0.17, STEEL, sides=16)
fs_.torus(V(SCX, SCY, 5.5), (0, 0, 1), 0.18, 0.02, DARK, seg=16, rseg=4)
fs_.cyl(V(SCX + 0.55, SCY, 4.85), V(-2.85, FCY, 4.85), 0.3, GALV, sides=20)
for z in (1.6, 2.8, 3.9):
    fs_.torus(V(SCX, SCY, z), (0, 0, 1), 0.555, 0.015, "paint_grey", seg=28, rseg=4)
fs_.lathe(V(SCX + 0.62, SCY, DZ + 0.3), (1, 0, 0), [(0.0, 0.0), (0.38, 0.0), (0.38, 0.3), (0.0, 0.3)], "paint_grey", sides=24)     # fan scroll
fs_.cyl(V(SCX + 0.62 + 0.3, SCY, DZ + 0.3), V(SCX + 1.25, SCY, DZ + 0.3), 0.17, "paint_blue", sides=16)
fs_.box2((SCX - 0.6, SCY - 0.6, DZ), (SCX + 1.3, SCY + 0.6, DZ + 0.12), DARK)
fs_.cyl(V(SCX, SCY, DZ + 0.12), V(SCX, SCY, DZ + 0.6), 0.45, GRN, sides=20)
fs_.ladder(V(SCX - 0.6, SCY - 0.3, DZ), V(SCX - 0.6, SCY - 0.3, 4.4), w=0.34, m=YEL)
# induction power cabinet + cooling + copper bus bars + water-cooled leads
for k in range(2):
    y0 = -2.05 + k * 0.72
    fs_.box2((1.25, y0, DZ), (2.05, y0 + 0.7, 2.55), "paint_grey", bevel=0.012, seg=2)
    fs_.box2((1.23, y0 + 0.04, DZ + 0.1), (1.25, y0 + 0.66, 2.45), "paint_grey")
    fs_.box2((1.215, y0 + 0.55, DZ + 1.1), (1.23, y0 + 0.6, DZ + 1.4), "paint_black")
    fs_.grille(V(1.24, y0 + 0.35, DZ + 2.1), 0.5, 0.3, 5, (-1, 0, 0), "paint_grey", depth=0.02)
    for j, em in enumerate(("emit_green", "emit_amber", "emit_red")):
        fs_.cyl(V(1.23, y0 + 0.15 + j * 0.08, DZ + 1.9), V(1.215, y0 + 0.15 + j * 0.08, DZ + 1.9), 0.018, em, sides=10)
fs_.box2((1.3, -2.0, 2.55), (2.0, -0.7, 2.75), "paint_grey", bevel=0.01, seg=1)                          # cooling unit on top
for k in range(2):
    fs_.cyl(V(1.65, -1.7 + k * 0.6, 2.75), V(1.65, -1.7 + k * 0.6, 2.8), 0.24, DARK, sides=20)
    for j in range(3):
        fs_.torus(V(1.65, -1.7 + k * 0.6, 2.81), (0, 0, 1), 0.08 + j * 0.07, 0.005, STEEL, seg=20, rseg=3)
for k in range(3):                                                                                      # copper bus bars on insulators
    z = 1.75 + k * 0.12
    fs_.box2((FX + 1.25, FY - 0.28 - k * 0.0, z), (1.25, FY - 0.24, z + 0.07), "copper")
    for x in (0.95, 0.4):
        fs_.cyl(V(x, FY - 0.26, z - 0.1), V(x, FY - 0.26, z), 0.025, "paint_white", sides=10)
for k in range(2):                                                                                      # water-cooled leads
    fs_.hose(V(1.25, -1.2 + k * 0.15, 1.3), V(-1, 0, 0), V(FX + 1.2, FY - 0.15 - k * 0.12, FZ - 0.35), V(1, 0, 0.2), 0.04, "rubber",
             sag=0.25, reach=0.4)
static.append(fs_.finish(root))

# =============================================================================== furnace (tilts about X at the spout lip)
fu = Part("furnace", pivot=(FX, FY, FZ), axis=(1, 0, 0))
fu.lathe(V(FX, FCY, FZ - FH), (0, 0, 1), [(0.0, 0.0), (FR - 0.04, 0.0), (FR, 0.04), (FR, FH - 0.06), (FR + 0.02, FH - 0.04), (FR + 0.02, FH),
                                            (0.52, FH), (0.5, FH - 0.04), (0.5, FH - 0.3), (0.0, FH - 0.3)], "steel_dark", sides=36)
fu.lathe(V(FX, FCY, FZ - 0.3), (0, 0, 1), [(0.495, 0.0), (0.495, 0.27)], "brick", sides=36, caps=False)                   # crucible lining
fu.lathe(V(FX, FCY, FZ - 0.05), (0, 0, 1), [(0.5, 0.0), (FR + 0.01, 0.0), (FR + 0.01, 0.07), (0.5, 0.07)], "brick", sides=36, caps=False)
fu.cyl(V(FX, FCY, FZ - 0.2), V(FX, FCY, FZ - 0.13), 0.49, "custom_molten", sides=32)                    # the melt
for k in range(8):                                                                                       # magnetic yokes
    a = k * math.tau / 8 + math.tau / 16
    d = V(math.cos(a), math.sin(a), 0)
    fu.box(V(FX, FCY, FZ - FH / 2) + d * (FR + 0.05), (0.1, 0.16, FH - 0.2), "paint_grey", rot=(0, 0, math.degrees(a)), bevel=0.01, seg=1)
for z in (FZ - FH + 0.08, FZ - 0.12):
    fu.lathe(V(FX, FCY, z), (0, 0, 1), [(FR + 0.08, -0.05), (FR + 0.14, -0.05), (FR + 0.14, 0.05), (FR + 0.08, 0.05), (FR + 0.08, -0.05)],
             GRN, sides=36, caps=False)
for sx in (-1, 1):                                                                                       # cradle arms to the trunnions
    fu.slab([V(FX + sx * 0.86, FY + 0.12, FZ + 0.12), V(FX + sx * 0.86, FY + 0.12, FZ - 0.25), V(FX + sx * 0.86, FCY - 0.4, FZ - FH + 0.2),
             V(FX + sx * 0.86, FCY + 0.1, FZ - FH + 0.05), V(FX + sx * 0.86, FCY + 0.5, FZ - 0.3)], 0.08, GRN, normal=(1, 0, 0), bevel=0.012, seg=1)
    fu.cyl(V(FX + sx * 0.82, FY, FZ), V(FX + sx * 0.92, FY, FZ), 0.15, STEEL, sides=18)
    fu.box(V(FX + sx * (FR + 0.12) * 0.98, FCY, FZ - FH + 0.1), (0.16, 0.5, 0.1), GRN)
fu.prism(V(FX, FY - 0.25, FZ - 0.05), V(FX, FY + 0.08, FZ - 0.02), [(-0.13, -0.08), (0.13, -0.08), (0.18, 0.04), (-0.18, 0.04)], "brick", up=(0, 0, 1))   # spout
fu.prism(V(FX, FY - 0.25, FZ - 0.03), V(FX, FY + 0.07, FZ), [(-0.07, -0.05), (0.07, -0.05), (0.08, 0.0), (-0.08, 0.0)], "custom_molten", up=(0, 0, 1))
fu.box2((FX + FR + 0.08, FCY - 0.3, FZ - 0.9), (FX + FR + 0.22, FCY + 0.1, FZ - 0.5), "copper", bevel=0.01, seg=1)   # coil terminals
for k in range(2):
    fu.cyl(V(FX + FR + 0.22, FCY - 0.2 + k * 0.2, FZ - 0.7), V(FX + FR + 0.4, FCY - 0.2 + k * 0.2, FZ - 0.7), 0.035, "copper", sides=10)
furnace = fu.finish(root)

# pour stream: hangs from the lip, scales open during the pour
st = Part("pour_stream", pivot=(FX, FY + 0.06, FZ - 0.04), grime=False)
pts = lib.catmull([V(FX, FY + 0.06, FZ - 0.04), V(FX, FY + 0.18, FZ - 0.2), V(FX, FY + 0.32, FZ - 0.75), V(FX, MY - 0.02, MZ + 0.45),
                   V(FX, MY, MZ + 0.12)], 6)
st.tube(pts, 0.065, "custom_molten", sides=12, r_end=0.04)
st.ico(V(FX, MY, MZ + 0.12), 0.07, "custom_molten", detail=1, scale=(1.4, 1.4, 0.35))
stream = st.finish(root)

# =============================================================================== ingot mold conveyor + quench tank
mc = Part("mold_line")
for sy in (-1, 1):
    mc.box2((XS[0] - 0.55, MY + sy * 0.16 - 0.015, DZ), (XS[5] + 0.45, MY + sy * 0.16 + 0.015, MZ - 0.03), GRN, bevel=0.006, seg=1)
    mc.box2((XS[0] - 0.55, MY + sy * 0.13 - 0.02, MZ - 0.05), (XS[5] + 0.45, MY + sy * 0.13 + 0.02, MZ), STEEL)
mc.box2((XS[0] - 0.55, MY - 0.06, MZ - 0.12), (XS[5] + 0.45, MY + 0.06, MZ - 0.08), DARK)                   # chain
for k in range(int((XS[5] - XS[0] + 1.0) / 0.1)):
    mc.box((XS[0] - 0.5 + k * 0.1, MY, MZ - 0.1), (0.05, 0.13, 0.03), STEEL)
for x in (XS[0] - 0.5, XS[5] + 0.4):
    mc.cyl(V(x, MY - 0.2, MZ - 0.1), V(x, MY + 0.2, MZ - 0.1), 0.12, DARK, sides=16)
mc.box2((XS[0] - 0.55, MY - 0.2, DZ), (XS[5] + 0.45, MY + 0.2, DZ + 0.05), DARK)
QX0, QX1 = XS[5] + 0.25, XS[5] + 0.95
mc.box2((QX0, MY - 0.42, DZ), (QX1, MY + 0.42, MZ + 0.02), STEEL, bevel=0.01, seg=1)
mc.box2((QX0 + 0.04, MY - 0.38, DZ + 0.05), (QX1 - 0.04, MY + 0.38, MZ - 0.1), DARK)
for k in range(4):
    mc.box((QX0 + 0.2 + (k % 2) * 0.3, MY - 0.2 + (k // 2) * 0.35, DZ + 0.1), (0.26, 0.1, 0.05), "gold", rot=(0, 0, 10 * k))
mc.box2((XS[0] - 0.62, MY - 0.24, MZ + 0.0), (XS[0] - 0.55, MY + 0.24, MZ + 0.12), YEL)
static.append(mc.finish(root))
wq = Part("quench_water", grime=False, smooth=False)
wq.faces([V(QX0 + 0.04, MY - 0.38, MZ - 0.12), V(QX1 - 0.04, MY - 0.38, MZ - 0.12), V(QX1 - 0.04, MY + 0.38, MZ - 0.12),
          V(QX0 + 0.04, MY + 0.38, MZ - 0.12)], [(0, 1, 2, 3)], "custom_water", [[(0, 0), (1.3, 0), (1.3, 1.5), (0, 1.5)]])
static.append(wq.finish(root))


def bar_prism(part, c, m, L=0.26, W=0.09, H=0.05, taper=0.82):
    """Trapezoid ingot (wider at the base, as cast)."""
    L2, W2 = L * taper, W * taper
    b = [V(-L / 2, -W / 2, 0), V(L / 2, -W / 2, 0), V(L / 2, W / 2, 0), V(-L / 2, W / 2, 0)]
    t = [V(-L2 / 2, -W2 / 2, H), V(L2 / 2, -W2 / 2, H), V(L2 / 2, W2 / 2, H), V(-L2 / 2, W2 / 2, H)]
    with part.at(c):
        part.loft([b, t], m, closed=True, caps=True, bevel=0.006, seg=1)


def mold(name, x, contents):
    """Cast-iron ingot mold; contents: 'none' | 'bar' (bar baked in)."""
    p = Part(name, pivot=(x, MY, MZ))
    p.box((x, MY, MZ), (0.36, 0.22, 0.11), "cast_iron", bevel=0.01, seg=1)
    p.box((x, MY, MZ + 0.11 - 0.012), (0.28, 0.12, 0.026), "steel_dark")
    for sx in (-1, 1):
        p.box((x + sx * 0.2, MY, MZ + 0.04), (0.04, 0.12, 0.05), "cast_iron")
    if contents == "bar":
        bar_prism(p, V(x, MY, MZ + 0.055), "gold", L=0.26, W=0.1, H=0.052)
    return p.finish(root)


def fill(name, x, m, H=0.052):
    p = Part(name, pivot=(x, MY, MZ + 0.055), grime=False)
    if m == "gold":
        bar_prism(p, V(x, MY, MZ + 0.055), "gold", L=0.26, W=0.1, H=H)
    else:
        p.box((x, MY, MZ + 0.055), (0.25, 0.095, H), "custom_molten")
    return p


molds = {}
for j in range(-1, 6):
    xs = XS[j] if j >= 0 else XS[0]
    molds[j] = mold(f"mold_{j + 1}", xs, "bar" if j >= 3 else "none")
molten_1 = fill("molten_1", XS[1], "molten")
molten_1 = molten_1.finish(molds[1])
molten_2 = fill("molten_2", XS[2], "molten").finish(molds[2])
bar_2 = fill("bar_2", XS[2], "gold").finish(molds[2])

# =============================================================================== gold room cage + bar pallet
GX, GY = 2.72, 2.62
BL, BW, BH = 0.3, 0.12, 0.062                                                         # big cast bars
gr = Part("gold_room")
for i in range(6):
    gr.box2((GX - 0.82, GY - 0.62 + i * 0.235, DZ + 0.1), (GX + 0.82, GY - 0.62 + i * 0.235 + 0.1, DZ + 0.125), "wood_planks", bevel=0.004, seg=1)
for j in (-1, 0, 1):
    gr.box2((GX + j * 0.72 - 0.05, GY - 0.62, DZ), (GX + j * 0.72 + 0.05, GY + 0.62, DZ + 0.1), "wood_planks", bevel=0.004, seg=1)
# pyramid: layers alternate bar direction (rot 0 = bars along X, rot 1 = along Y); (count x, count y, rot)
layers = [(4, 8, 0), (9, 3, 1), (3, 6, 0), (6, 2, 1), (2, 4, 0), (3, 1, 1), (1, 2, 0)]
GAP = 0.02
z = DZ + 0.125
tops = []
for nx, ny, rot in layers:
    sx_, sy_ = (BL + GAP, BW + GAP) if rot == 0 else (BW + GAP, BL + GAP)
    for ix in range(nx):
        for iy in range(ny):
            c = V(GX + (ix - (nx - 1) / 2) * sx_, GY + (iy - (ny - 1) / 2) * sy_, z)
            with gr.at(c, (0, 0, 90 * rot)):
                bar_prism(gr, V(0, 0, 0), "gold", L=BL, W=BW, H=BH)
            tops.append((c + V(0, 0, BH), 90 * rot))
    z += BH
STACK_TOP = z
CG0, CG1 = V(GX - 0.95, GY - 0.85, DZ), V(GX + 0.95, GY + 0.85, DZ)
for x in (CG0.x, CG1.x):                                                              # cage frame + mesh walls
    for y in (CG0.y, CG1.y):
        gr.box2((x - 0.04, y - 0.04, DZ), (x + 0.04, y + 0.04, DZ + 2.3), YEL, bevel=0.006, seg=1)
for (a, b) in (((CG0.x, CG0.y), (CG1.x, CG0.y)), ((CG1.x, CG0.y), (CG1.x, CG1.y))):
    a3, b3 = V(a[0], a[1], DZ), V(b[0], b[1], DZ)
    for zz in (DZ + 0.08, DZ + 1.15, DZ + 2.26):
        gr.box2((min(a3.x, b3.x) - 0.03, min(a3.y, b3.y) - 0.03, zz - 0.03), (max(a3.x, b3.x) + 0.03, max(a3.y, b3.y) + 0.03, zz + 0.03), YEL)
    lo = V(min(a3.x, b3.x), min(a3.y, b3.y), DZ + 0.12)
    hi = V(max(a3.x, b3.x), max(a3.y, b3.y), DZ + 2.22)
    if abs(hi.x - lo.x) < 0.01:
        co = [V(lo.x, lo.y, lo.z), V(lo.x, hi.y, lo.z), V(lo.x, hi.y, hi.z), V(lo.x, lo.y, hi.z)]
        uvw = hi.y - lo.y
    else:
        co = [V(lo.x, lo.y, lo.z), V(hi.x, lo.y, lo.z), V(hi.x, lo.y, hi.z), V(lo.x, lo.y, hi.z)]
        uvw = hi.x - lo.x
    gr.faces(co, [(0, 1, 2, 3)], "custom_grating", [[(0, 0), (uvw, 0), (uvw, hi.z - lo.z), (0, hi.z - lo.z)]])
for (a, b) in (((CG0.x, CG1.y), (CG1.x, CG1.y)), ((CG0.x, CG0.y), (CG0.x, CG1.y))):            # open sides: top rail only
    gr.box2((min(a[0], b[0]) - 0.03, min(a[1], b[1]) - 0.03, DZ + 2.23), (max(a[0], b[0]) + 0.03, max(a[1], b[1]) + 0.03, DZ + 2.29), YEL)
# front deck: roller table from the quench tank, stamping press, cart of fresh bars (gold near the player)
RTX = 1.12
for y in (MY + 0.5, MY + 1.55):
    for sx in (-1, 1):
        gr.box2((RTX + sx * 0.2 - 0.03, y - 0.03, DZ), (RTX + sx * 0.2 + 0.03, y + 0.03, DZ + 0.72), GRN)
for sx in (-1, 1):
    gr.box2((RTX + sx * 0.2 - 0.02, MY + 0.45, DZ + 0.7), (RTX + sx * 0.2 + 0.02, MY + 1.6, DZ + 0.78), GRN)
for k in range(10):
    gr.cyl(V(RTX - 0.18, MY + 0.52 + k * 0.115, DZ + 0.8), V(RTX + 0.18, MY + 0.52 + k * 0.115, DZ + 0.8), 0.035, STEEL, sides=8)
for k, y in enumerate((MY + 0.8, MY + 1.3)):
    with gr.at(V(RTX, y, DZ + 0.835), (0, 0, 90)):
        bar_prism(gr, V(0, 0, 0), "gold", L=BL, W=BW, H=BH)
PRX, PRY = RTX, MY + 1.98                                                            # C-frame stamping press
gr.box2((PRX - 0.35, PRY - 0.3, DZ), (PRX + 0.35, PRY + 0.3, DZ + 0.75), GRN, bevel=0.02, seg=2)
gr.box2((PRX - 0.3, PRY + 0.12, DZ + 0.75), (PRX + 0.3, PRY + 0.3, DZ + 1.75), GRN, bevel=0.02, seg=2)
gr.box2((PRX - 0.3, PRY - 0.3, DZ + 1.45), (PRX + 0.3, PRY + 0.3, DZ + 1.75), GRN, bevel=0.02, seg=2)
gr.cyl(V(PRX, PRY - 0.05, DZ + 1.45), V(PRX, PRY - 0.05, DZ + 1.05), 0.07, "chrome", sides=14)
gr.cyl(V(PRX, PRY - 0.05, DZ + 1.05), V(PRX, PRY - 0.05, DZ + 0.98), 0.1, STEEL, sides=14)
gr.box2((PRX - 0.22, PRY - 0.22, DZ + 0.75), (PRX + 0.22, PRY + 0.1, DZ + 0.8), DARK)
with gr.at(V(PRX, PRY - 0.06, DZ + 0.8), (0, 0, 90)):
    bar_prism(gr, V(0, 0, 0), "gold", L=BL, W=BW, H=BH)
CTX, CTY = -0.6, 3.25                                                                # ingot cart with fresh bars
gr.box2((CTX - 0.45, CTY - 0.3, DZ + 0.25), (CTX + 0.45, CTY + 0.3, DZ + 0.32), STEEL, bevel=0.008, seg=1)
for sx in (-1, 1):
    for sy in (-1, 1):
        gr.cyl(V(CTX + sx * 0.36, CTY + sy * 0.32, DZ + 0.1), V(CTX + sx * 0.36, CTY + sy * 0.25, DZ + 0.1), 0.1, "rubber", sides=12)
gr.tube([V(CTX - 0.45, CTY - 0.25, DZ + 0.32), V(CTX - 0.62, CTY - 0.25, DZ + 0.95), V(CTX - 0.62, CTY + 0.25, DZ + 0.95),
         V(CTX - 0.45, CTY + 0.25, DZ + 0.32)], 0.02, STEEL, sides=8)
for ix in range(2):
    for iy in range(4):
        with gr.at(V(CTX - 0.17 + ix * 0.34, CTY - 0.21 + iy * 0.14, DZ + 0.32), (0, 0, 0)):
            bar_prism(gr, V(0, 0, 0), "gold", L=BL, W=BW, H=BH)
for iy in range(3):
    with gr.at(V(CTX, CTY - 0.14 + iy * 0.14, DZ + 0.32 + BH), (0, 0, 0)):
        bar_prism(gr, V(0, 0, 0), "gold", L=BL, W=BW, H=BH)
static.append(gr.finish(root))

# =============================================================================== control cabin (front left)
cb = Part("cabin")
KX0, KX1, KY0, KY1, KZ1 = -3.55, -2.0, 1.75, 3.75, 3.0
W = "paint_white"
cb.box2((KX0, KY0, DZ), (KX1, KY1, DZ + 0.9), W, bevel=0.015, seg=1)
cb.box2((KX0, KY0, KZ1 - 0.25), (KX1, KY1, KZ1), W, bevel=0.02, seg=2)
for x in (KX0, KX1 - 0.08):
    for y in (KY0, KY1 - 0.08):
        cb.box2((x, y, DZ + 0.9), (x + 0.08, y + 0.08, KZ1 - 0.25), W)
cb.box2((KX1 - 0.08, 2.65, DZ + 0.9), (KX1, 2.75, KZ1 - 0.25), W)
cb.box2((KX0, 2.65, DZ + 0.9), (KX0 + 0.08, 2.75, KZ1 - 0.25), W)
cb.box2((KX1 - 0.045, KY0 + 0.08, DZ + 0.9), (KX1 - 0.035, KY1 - 0.08, KZ1 - 0.25), "glass")                 # toward the casting line
cb.box2((KX0 + 0.08, KY0 + 0.035, DZ + 0.9), (KX1 - 0.08, KY0 + 0.045, KZ1 - 0.25), "glass")                 # toward the furnace
cb.box2((KX0 + 0.08, KY1 - 0.045, DZ + 0.9), (KX1 - 0.08, KY1 - 0.035, KZ1 - 0.25), "glass")                 # toward the drift
cb.box2((KX0 + 0.035, KY0 + 0.08, DZ + 0.9), (KX0 + 0.045, KY1 - 0.08, KZ1 - 0.25), W)
cb.box2((KX0 - 0.02, KY0 - 0.02, DZ + 0.88), (KX1 + 0.02, KY1 + 0.02, DZ + 0.94), GRN)
cb.box2((KX1 - 0.65, KY0 + 0.1, DZ), (KX1 - 0.1, KY1 - 0.1, DZ + 0.82), "paint_grey", bevel=0.01, seg=1)    # desk along the window
cb.box2((KX1 - 0.42, KY0 + 0.25, DZ + 0.82), (KX1 - 0.3, KY1 - 0.25, DZ + 1.3), "paint_black", bevel=0.008, seg=1)
cb.box2((-3.1, 2.55, DZ), (-2.75, 2.95, DZ + 0.45), "plastic_black", bevel=0.02, seg=2)                       # seat
cb.box2((-3.2, 2.55, DZ + 0.45), (-3.1, 2.95, DZ + 1.0), "plastic_black", bevel=0.02, seg=2)
cb.box2((KX0 + 0.3, KY0 + 0.4, KZ1 - 0.27), (KX1 - 0.3, KY1 - 0.4, KZ1 - 0.25), "emit_warm")
cb.box2((-3.3, 2.2, KZ1), (-2.4, 3.3, KZ1 + 0.32), "paint_grey", bevel=0.02, seg=2)
cb.grille(V(-2.85, 3.305, KZ1 + 0.16), 0.7, 0.22, 4, (0, 1, 0), "paint_grey", depth=0.02)
cb.cyl(V(-2.2, 3.55, KZ1), V(-2.2, 3.55, KZ1 + 0.06), 0.07, "paint_black", sides=12)
cb.lathe(V(-2.2, 3.55, KZ1 + 0.06), (0, 0, 1), [(0.06, 0), (0.06, 0.1), (0.04, 0.14), (0, 0.15)], "emit_amber", sides=12)
static.append(cb.finish(root))

# light masts at the front corners + hood light
lm = Part("lights")
for x in (-3.55, 3.55):
    lm.cyl(V(x, 4.45, DZ), V(x, 4.45, 4.9), 0.06, GRN, sides=10)
    lm.cyl(V(x, 4.45, DZ), V(x, 4.45, DZ + 0.06), 0.16, DARK, sides=10)
    lm.led_light(V(x, 4.45, 4.95), (-x * 0.25, -1.0, -0.55), w=0.4, h=0.13)
lm.led_light(V(FX, FY + 0.38, HZ - 0.06), (0, 0.25, -1.0), w=0.4, h=0.12)
static.append(lm.finish(root))

# =============================================================================== decals + screens
dec = Part("decals", grime=False, smooth=False)
lib.decal_wrap(dec, ATL, "mk", V(SCX, SCY, 0.0), (0, 0, 1), 0.55, 0.0, 3.2, h=0.2, mode="around", ref=(1, 0, 0), segs=12)
lib.decal_wrap(dec, ATL, "mlx", V(SCX, SCY, 0.0), (0, 0, 1), 0.55, 0.0, 2.6, h=0.32, mode="around", ref=(1, 0, 0), segs=8)
lib.decal_wrap(dec, ATL, "l_scrub", V(SCX, SCY, 0.0), (0, 0, 1), 0.55, 0.0, 1.3, h=0.1, mode="around", ref=(1, 0, 0), segs=6)
lib.decal_cell(dec, ATL, "mk", (MXc, WY + 0.155, 5.35), (0, 1, 0), (0, 0, 1), h=0.15)
lib.decal_cell(dec, ATL, "warn_molten", (FX - 1.42, FCY - 0.5, 1.6), (-1, 0, 0), (0, 0, 1), w=0.45)
lib.decal_cell(dec, ATL, "warn_molten", (FX + 1.42, FCY - 0.5, 1.6), (1, 0, 0), (0, 0, 1), w=0.45)
lib.decal_cell(dec, ATL, "warn_hv", (1.229, -1.3, DZ + 1.55), (-1, 0, 0), (0, 0, 1), w=0.32)
lib.decal_cell(dec, ATL, "l_ind", (1.229, -1.7, DZ + 2.32), (-1, 0, 0), (0, 0, 1), w=0.26)
lib.decal_cell(dec, ATL, "warn_rot", (WX + 0.86, WY, DZ + 0.8), (1, 0, 0), (0, 0, 1), w=0.3)
lib.decal_cell(dec, ATL, "warn_hot", (XS[2], MY - 0.176, DZ + 0.45), (0, -1, 0), (0, 0, 1), w=0.28)
lib.decal_cell(dec, ATL, "goldroom", (GX, CG1.y + 0.05, DZ + 2.0), (0, 1, 0), (0, 0, 1), w=0.9)
lib.decal_cell(dec, ATL, "plate", (OBX + 0.551, OBY, DZ + 0.4), (1, 0, 0), (0, 0, 1), w=0.22)
lib.decal_cell(dec, ATL, "badge", (KX1 + 0.001, 3.25, DZ + 0.55), (1, 0, 0), (0, 0, 1), w=0.5)
lib.decal_cell(dec, ATL, "mk_w", (EX + 0.301, EY, 3.7), (1, 0, 0), (0, 0, 1), h=0.12)
lib.decal_cell(dec, ATL, "ppe", (-1.2, 4.751, DZ + 0.5), (0, 1, 0), (0, 0, 1), w=0.5)
for c, rz in tops[-20:]:                                                                     # stamps on the top bars
    up = V(0, 1, 0) if rz == 0 else V(-1, 0, 0)
    lib.decal_cell(dec, ATL, "stamp", c + V(0, 0, 0.0005), (0, 0, 1), up, w=0.2, off=0.001)
lib.decal(dec, (KX1 - 0.299, 2.35, DZ + 1.06), (1, 0, 0), (0, 0, 1), 0.6, 0.38, "custom_screen_mlx", lib.cell_uv(f"scr_{ID}", "furnace"), off=0.0)
lib.decal(dec, (KX1 - 0.299, 3.15, DZ + 1.06), (1, 0, 0), (0, 0, 1), 0.6, 0.38, "custom_screen_mlx", lib.cell_uv(f"scr_{ID}", "drill"), off=0.0)
lib.stripe(dec, (0.0, 4.751, DZ - 0.02), (0, 1, 0), (0, 0, 1), 1.8, 0.04, period=0.08)
for x in (-1.15, 1.15):                                                                     # walkway lines on the deck
    lib.decal(dec, (x * 0.85, 2.6, DZ), (0, 0, 1), (0, 1, 0), 0.08, 4.2, "paint_yellow", off=0.002)
for x in (WX - 0.85, WX + 0.85):
    lib.stripe(dec, (x + (0.001 if x > WX else -0.001), WY, DZ + 0.25), (1 if x > WX else -1, 0, 0), (0, 0, 1), 1.5, 0.05, period=0.1)
static.append(dec.finish(root))
gz = Part("gauges")
dg = Part("decals_gauge", grime=False, smooth=False)
needle = lib.gauge(gz, dg, ATL, "g_temp", V(1.229, -0.6, DZ + 1.75), (-1, 0, 0), (0, 0, 1), 0.07, "needle_0", root)
static.append(gz.finish(root))
static.append(dg.finish(root))

# =============================================================================== empties
lib.empty("fx_work", (WX, WY, DZ + 0.4), root)
lib.empty("fx_ore", (GX, GY, STACK_TOP + 0.05), root)
lib.empty("fx_pour", (FX, FY + 0.06, FZ - 0.05), root)
lib.empty("light_0", (MXc, WY + 0.05, 5.12), root, aim=(0, 0.2, -1.0))
lib.empty("light_1", (FX, FY + 0.43, HZ - 0.12), root, aim=(0, 0.25, -1.0))
lib.empty("light_2", (3.55, 4.38, 4.92), root, aim=(-0.9, -1.0, -0.55))
lib.empty("light_3", (-3.55, 4.38, 4.92), root, aim=(0.9, -1.0, -0.55))
lib.empty("light_4", (0.0, 4.6, 3.0), root, aim=(0, 1.0, -0.35))
lib.empty("op", (-2.9, 2.75, DZ), root, face=(1, -0.35, 0))
lib.empty("snd", (FX, FCY, 2.0), root)

# =============================================================================== animation
lib.spin(drill_string, "Work", WORK, turns=3)
lib.track(top_drive, "Work", "location", 2, [(0, 0.0), (150, -0.06), (WORK, 0.0)])
lib.spin(crusher_pulley, "Work", WORK, turns=-9)
TILT = math.radians(-70)
lib.track(furnace, "Work", "rotation_euler", 2, [(0, 0.0), (40, TILT), (110, TILT), (145, 0.0), (WORK, 0.0)])
lib.key(stream, "Work", "scale", 2, 0, 0.001, "LINEAR")
lib.key(stream, "Work", "scale", 2, 38, 0.001, "LINEAR")
lib.key(stream, "Work", "scale", 2, 46, 1.0, "LINEAR")
lib.key(stream, "Work", "scale", 2, 106, 1.0, "LINEAR")
lib.key(stream, "Work", "scale", 2, 112, 0.001, "LINEAR")
lib.key(stream, "Work", "scale", 2, WORK, 0.001, "LINEAR")
for i in (0, 1):
    lib.key(stream, "Work", "scale", i, 0, 1.0, "LINEAR")
    lib.key(stream, "Work", "scale", i, WORK, 1.0, "LINEAR")
I0, I1 = 146, 178                                                              # index window
for j, ob in molds.items():
    start = V(XS[j] if j >= 0 else XS[0], MY, MZ)
    ob.location = start
    if j == -1:
        ob.location = start - V(0, 0, 0.42)
    ob["_rest_loc"] = list(ob.location)
    dx = P if j >= 0 else 0.0
    dz_end = 0.0
    if j == -1:
        dz_end = 0.42                                                           # rises into station 0
    if j == 5:
        dz_end = -0.42                                                          # drops into the quench tank
    lib.move(ob, "Work", [(0, (0, 0, 0)), (I0, (0, 0, 0)), (I1, (dx, 0, dz_end)), (WORK, (dx, 0, dz_end))], interp="BEZIER")
for ob, pts_ in ((molten_1, [(0, 0.001), (46, 0.001), (104, 1.0), (WORK, 1.0)]),
                 (molten_2, [(0, 1.0), (30, 1.0), (140, 0.001), (WORK, 0.001)]),
                 (bar_2, [(0, 0.001), (30, 0.001), (140, 1.0), (WORK, 1.0)])):
    for f, v in pts_:
        lib.key(ob, "Work", "scale", 2, f, v, "LINEAR")
    ob.scale = (1, 1, pts_[0][1])
    ob["_rest_scale"] = [1, 1, pts_[0][1]]
lib.needle_keys(needle, "Work", WORK, 220, 3, step=9, seed=91)
stream.scale = (1, 1, 0.001)
stream["_rest_scale"] = [1, 1, 0.001]
anim = [drill_string, top_drive, crusher_pulley, furnace, stream, needle, molten_1, molten_2, bar_2] + list(molds.values())
for o in anim:
    lib.hold(o, "Idle", IDLE)
    for i in range(3):
        lib.key(o, "Idle", "scale", i, 0, lib.rest(o, "scale", i), "LINEAR")
        lib.key(o, "Idle", "scale", i, IDLE, lib.rest(o, "scale", i), "LINEAR")
lib.bake_clips()

# =============================================================================== merge, grime, export
body = lib.merge([o for o in static if o.get("grime")], "body")
meshes = [o for o in lib.descendants(root) if o.type == "MESH" and o.get("grime")]
lib.bake_grime(meshes, distance=0.5, samples=48, floor_z=0.0)
path, js, anims, names = lib.export(root, OUT)
size = lib.report(root, "<= 8 W x 10 L x 5.6 H")
need = [ID, "fx_work", "fx_ore", "fx_pour", "light_0", "op", "snd"]
print("[mb] missing nodes:", [n for n in need if n not in names])

if PREVIEW:
    lib.previews(ID, root, [
        dict(name="34", az=32, el=18, fill=0.95, frame=80),
        dict(name="rear", az=205, el=20, fill=0.95, frame=80),
        dict(name="pour", az=160, el=12, target=(FX, FY + 0.2, 1.7), dist=3.6, lens=32, frame=80),
        dict(name="gold", az=200, el=24, target=(GX - 0.4, GY - 0.3, 1.0), dist=3.2, lens=32, frame=80),
        dict(name="side", az=-90, el=8, fill=0.95, frame=80),
    ], frame=80)
