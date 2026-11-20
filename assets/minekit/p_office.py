"""Site-office set: desk, office_chair, monitor, pc_tower, keyboard, desk_lamp (front = -Y = three.js +Z)."""
import json
import math
import os

import bmesh
from mathutils import Matrix, Vector

import mk
import parts as P
from mk import DEG, MB, child, empty, rotm, trs

BUILD = {}
HERE = os.path.dirname(os.path.abspath(__file__))


def node(name, kind="floor", **meta):
    def deco(fn):
        BUILD[name] = (fn, dict(kind=kind, **meta))
        return fn
    return deco


DESK_H = 0.76


# ====================================================================== desk
def hard_hat(mb, c, yaw=0.0, mat="helmet_yellow", sticker=True, rot=None, sticker_name="helmet_ml"):
    """Hard hat resting on its brim at c (bottom), peak toward local -Y rotated by yaw (or a full rot)."""
    Mx = trs(c, rot if rot is not None else (0, 0, yaw))
    prof = [(0.0, 0.155), (0.04, 0.152), (0.075, 0.142), (0.1, 0.122), (0.113, 0.095), (0.118, 0.06), (0.12, 0.035),
            (0.122, 0.03)]
    mb.lathe(prof, mat, sides=20, Mx=Mx @ Matrix.Diagonal((1.0, 1.18, 1.0, 1.0)))
    # ribs along the crown
    for x in (-0.03, 0.0, 0.03):
        pts = []
        for k in range(9):
            t = -1.1 + 2.2 * k / 8
            y = math.sin(t) * 0.118 * 1.18
            z = 0.035 + math.cos(t) * 0.12
            pts.append(Mx @ Vector((x, y, z if z < 0.158 else 0.158)))
        mb.tube(pts, 0.006, mat, sides=5)
    # brim + peak
    brim = []
    for k in range(25):
        a = k / 24 * 2 * math.pi
        r = 0.135 + (0.04 if math.sin(a) < -0.5 else 0.0) * (-math.sin(a) - 0.5) * 2
        brim.append((r * math.cos(a), r * math.sin(a) * 1.12))
    pts_top = [Mx @ Vector((x, y, 0.028)) for x, y in brim[:-1]]
    pts_bot = [Mx @ Vector((x, y, 0.016)) for x, y in brim[:-1]]
    tb = bmesh.new()
    vt = [tb.verts.new(p) for p in pts_top]
    vb = [tb.verts.new(p) for p in pts_bot]
    n = len(vt)
    for i in range(n):
        j = (i + 1) % n
        tb.faces.new((vt[i], vt[j], vb[j], vb[i]))
    ct = tb.verts.new(Mx @ Vector((0, 0, 0.028)))
    cb = tb.verts.new(Mx @ Vector((0, 0, 0.016)))
    for i in range(n):
        j = (i + 1) % n
        tb.faces.new((vt[j], vt[i], ct))
        tb.faces.new((vb[i], vb[j], cb))
    bmesh.ops.recalc_face_normals(tb, faces=tb.faces[:])
    tb.normal_update()
    mb.commit(tb, Matrix.Identity(4), mat, mk.uv_world_box)
    # cap-lamp bracket at the front
    mb.box((0.05, 0.02, 0.035), "plastic_black", center=True, Mx=Mx @ Matrix.Translation((0, -0.125, 0.105)) @ rotm((14, 0, 0)),
           bevel=0.004)
    if sticker:
        mb.quad(None, 0.055, 0.034, "label_minekit", rect=sticker_name,
                Mx=Mx @ Matrix.Translation((0.0, 0.1215, 0.1)) @ rotm((-12, 0, 180)))


@node("desk", "floor", notes="site-office desk, top at y=0.76; keep x in [-0.45, 0.45] of the top free for monitor/keyboard")
def desk():
    mb = MB("desk")
    rng = mb.rng
    W, Dp, H = 1.6, 0.8, DESK_H
    top_t = 0.035
    # worn laminate top with aluminium edge trim
    mb.box((W, Dp, top_t), "wood_dark", loc=(0, 0, H - top_t), bevel=0.004, seg=2)
    for s in (-1, 1):
        mb.box((W + 0.004, 0.006, top_t + 0.004), "aluminium", loc=(0, s * (Dp / 2 + 0.002), H - top_t - 0.002), bevel=0.001,
               seg=1)
        mb.box((0.006, Dp, top_t + 0.004), "aluminium", loc=(s * (W / 2 + 0.002), 0, H - top_t - 0.002), bevel=0.001, seg=1)
    # steel carcass: right drawer pedestal, left panel leg, modesty panel, pencil drawer
    px = W / 2 - 0.23
    mb.box((0.44, Dp - 0.04, H - top_t - 0.06), "paint_grey", loc=(px, 0.01, 0.06), bevel=0.006, seg=2)
    mb.box((0.40, Dp - 0.1, 0.06), "paint_black", loc=(px, 0.03, 0.0), bevel=0.004, seg=1)
    for i, (z0, h) in enumerate(((0.07, 0.27), (0.35, 0.16), (0.52, 0.13))):
        mb.box((0.41, 0.018, h - 0.012), "paint_grey", loc=(px, -Dp / 2 + 0.01, z0), bevel=0.004, seg=2)
        P.handle_bar(mb, Vector((px - 0.08, -Dp / 2 + 0.0, z0 + h - 0.05)), Vector((px + 0.08, -Dp / 2 + 0.0, z0 + h - 0.05)),
                     (0, -1, 0), stand=0.025, r=0.006, mat="aluminium")
        mb.box((0.07, 0.004, 0.035), "aluminium", loc=(px, -Dp / 2 - 0.001, z0 + 0.03), bevel=0.001, seg=1)
    mb.box((0.03, Dp - 0.04, H - top_t), "paint_grey", loc=(-W / 2 + 0.03, 0.01, 0.0), bevel=0.005, seg=2)
    mb.box((W - 0.5, 0.02, 0.42), "paint_grey", loc=(-0.2, Dp / 2 - 0.05, 0.28), bevel=0.004, seg=1)
    mb.box((0.62, Dp - 0.06, 0.06), "paint_grey", loc=(-0.18, 0.01, H - top_t - 0.065), bevel=0.004, seg=1)
    mb.box((0.6, 0.016, 0.05), "paint_grey", loc=(-0.18, -Dp / 2 + 0.012, H - top_t - 0.06), bevel=0.003, seg=1)
    # papers (stack) + top page, clipboard, mug, radio, hard hat
    sx, sy = 0.56, 0.12
    for k in range(6):
        mb.box((0.21, 0.297, 0.0025), "paint_white", loc=(sx + rng.uniform(-0.01, 0.01), sy + rng.uniform(-0.01, 0.01), H + k * 0.0025),
               rot=(0, 0, rng.uniform(-6, 6)))
    mb.quad((sx, sy, H + 0.0158), 0.21, 0.297, "label_minekit", rot=(-90, 0, 8), rect="doc_page")
    cx, cy = -0.45, -0.2
    mb.box((0.23, 0.32, 0.004), "wood_dark", loc=(cx, cy, H), rot=(0, 0, -12), bevel=0.001, seg=1)
    mb.quad((cx, cy, H + 0.0045), 0.2, 0.27, "label_minekit", rot=(-90, 0, -12), rect="clip_form", Mx=trs((cx, cy - 0.01, H + 0.0045), (-90, 0, -12)) @ Matrix.Translation((0, 0, 0)) if False else None)
    mb.box((0.09, 0.03, 0.012), "steel", loc=(cx - 0.135 * math.sin(math.radians(12)), cy + 0.135 * math.cos(math.radians(12)), H + 0.004),
           rot=(0, 0, -12), bevel=0.003, seg=1)
    # mug
    mx, my = 0.36, -0.22
    mb.lathe([(0.0, 0.0), (0.038, 0.0), (0.041, 0.006), (0.042, 0.095), (0.038, 0.096), (0.036, 0.09), (0.036, 0.012),
              (0.0, 0.012)], "paint_white", sides=16, loc=(mx, my, H))
    mb.cyl(0.0362, 0.002, "plastic_black", sides=16, loc=(mx, my, H + 0.074))
    mb.tube([Vector((mx + 0.04, my, H + 0.08)), Vector((mx + 0.07, my, H + 0.075)), Vector((mx + 0.072, my, H + 0.045)),
             Vector((mx + 0.06, my, H + 0.025)), Vector((mx + 0.04, my, H + 0.025))], 0.0065, "paint_white", sides=6)
    mb.clabel("mug_logo", Matrix.Translation((mx, my, H)), 0.0428, theta=0, w=0.06, z=0.05, segs=6)
    # two-way radio on its charger
    rx, ry = 0.4, 0.3
    mb.box((0.09, 0.07, 0.03), "plastic_black", loc=(rx, ry, H), bevel=0.006, seg=2)
    mb.box((0.06, 0.035, 0.13), "plastic_black", loc=(rx, ry, H + 0.025), rot=(8, 0, 0), bevel=0.006, seg=2)
    mb.rod((rx + 0.018, ry + 0.02, H + 0.15), (rx + 0.02, ry + 0.035, H + 0.24), 0.005, "rubber", sides=6)
    mb.label("radio_label", (rx, ry - 0.022, H + 0.075), 0.05, rot=(8, 0, 0))
    mb.cyl(0.003, 0.004, "emit_green", sides=6, loc=(rx + 0.03, ry - 0.036, H + 0.018), rot=(90, 0, 0))
    # hard hat (left end)
    hard_hat(mb, (-0.6, 0.16, H), yaw=35)
    return mb.finish()


# ====================================================================== office_chair
@node("office_chair", "floor", notes="worn vinyl office chair, seat at y=0.48, faces +Z")
def office_chair():
    mb = MB("office_chair")
    rng = mb.rng
    # 5-star base + casters
    hub = Vector((0, 0, 0.1))
    for k in range(5):
        a = k / 5 * 2 * math.pi + math.pi / 2
        tip = Vector((math.cos(a) * 0.32, math.sin(a) * 0.32, 0.075))
        mb.beam(hub + Vector((0, 0, 0.0)), tip, 0.045, 0.035, "plastic_black", up=(0, 0, 1), bevel=0.008)
        mb.rod(tip, tip - Vector((0, 0, 0.035)), 0.008, "steel", sides=6)
        cpos = tip + Vector((0.02 * math.cos(a), 0.02 * math.sin(a), -0.042))
        for s in (-1, 1):
            mb.cyl(0.026, 0.012, "plastic_black", sides=12, Mx=trs(cpos + Vector((-math.sin(a) * 0.009 * s, math.cos(a) * 0.009 * s, 0)), (0, 90, math.degrees(a) + 90)) @ Matrix.Translation((0, 0, -0.006)))
        mb.boxc(cpos + Vector((0, 0, 0.026)), (0.03, 0.03, 0.02), "plastic_black", bevel=0.005)
    mb.cyl(0.05, 0.06, "plastic_black", sides=12, loc=(0, 0, 0.07), bevel=0.006)
    # gas lift: shroud + chrome piston
    mb.cyl(0.028, 0.22, "plastic_black", sides=12, loc=(0, 0, 0.12), r2=0.025)
    mb.cyl(0.014, 0.1, "chrome", sides=10, loc=(0, 0, 0.33))
    # seat mechanism + seat
    mb.boxc((0, 0.0, 0.425), (0.22, 0.24, 0.04), "steel_dark", bevel=0.006)
    mb.rod((0.11, -0.05, 0.42), (0.2, -0.12, 0.4), 0.006, "steel_dark", sides=6)
    mb.cyl(0.015, 0.02, "plastic_black", sides=8, Mx=trs((0.2, -0.12, 0.4), (0, 90, 0)))

    def cushion(v):
        dish = 0.012 * max(0.0, 1 - (v.x / 0.24) ** 2 - (v.y / 0.24) ** 2)
        if v.z > 0.04:
            v.z -= dish
        return v
    mb.box((0.48, 0.46, 0.075), "leather", loc=(0, 0.0, 0.445), bevel=0.03, seg=3, cuts=(3, 3, 0), warp=cushion)
    # backrest on a steel spine
    mb.beam((0, 0.2, 0.43), (0, 0.27, 0.58), 0.06, 0.012, "steel_dark", up=(0, -1, 0), bevel=0.003)
    mb.beam((0, 0.27, 0.58), (0, 0.27, 0.66), 0.06, 0.012, "steel_dark", up=(0, -1, 0), bevel=0.003)

    def curve(v):
        v.y += 0.03 * (v.x / 0.22) ** 2
        return v
    mb.box((0.44, 0.07, 0.42), "leather", loc=(0, 0.29, 0.6), rot=(-8, 0, 0), bevel=0.028, seg=3, cuts=(4, 0, 2), warp=curve)
    # armrests
    for s in (-1, 1):
        mb.beam((s * 0.2, 0.0, 0.43), (s * 0.255, 0.0, 0.63), 0.03, 0.05, "plastic_black", up=(0, 1, 0), bevel=0.006)
        mb.boxc((s * 0.255, -0.02, 0.645), (0.06, 0.25, 0.03), "plastic_black", bevel=0.012, seg=2)
    # a tear in the seat vinyl (lighter stuffing showing)
    mb.box((0.06, 0.02, 0.003), "canvas", loc=(0.09, -0.12, 0.519), rot=(0, 0, 25), bevel=0.0)
    return mb.finish()


# ====================================================================== monitor
SCREEN_W, SCREEN_H = 0.531, 0.299


@node("monitor", "floor", notes="rugged 24in monitor; child screen = 0.531 x 0.299 m display, emit_screen, UV 0-1 "
                                  "(glTF convention: uv(0,0) = top-left as seen from the front; CanvasTexture flipY=false)")
def monitor():
    mb = MB("monitor")
    sc = Vector((0, -0.035, 0.34))   # screen centre
    hw, hh, dp = SCREEN_W / 2 + 0.034, SCREEN_H / 2 + 0.036, 0.055
    # heavy base plate + VESA column + tilt hinge
    mb.box((0.28, 0.2, 0.018), "steel_dark", loc=(0, 0.01, 0.0), bevel=0.006, seg=2)
    for x in (-0.11, 0.11):
        for y in (-0.07, 0.09):
            mb.cyl(0.012, 0.004, "rubber", sides=8, loc=(x, y, -0.003))
    mb.box((0.06, 0.035, 0.27), "steel_dark", loc=(0, 0.06, 0.018), bevel=0.006, seg=2)
    mb.rod((-0.05, 0.06, sc.z - 0.02), (0.05, 0.06, sc.z - 0.02), 0.018, "steel", sides=10, bevel=0.003)
    mb.box((0.12, 0.012, 0.12), "steel_dark", loc=(0, 0.035, sc.z - 0.08), bevel=0.003, seg=1)
    # housing: rugged bezel with rubber corner bumpers
    mb.box((2 * hw, dp, 2 * hh), "plastic_black", loc=(0, sc.y + dp / 2 + 0.004, sc.z - hh), bevel=0.012, seg=2, cuts=(2, 0, 2))
    mb.box((2 * hw - 0.09, 0.03, 2 * hh - 0.09), "plastic_black", loc=(0, sc.y + dp + 0.02, sc.z - hh + 0.045), bevel=0.01, seg=2)
    for sx in (-1, 1):
        for sz in (-1, 1):
            mb.boxc((sx * (hw - 0.012), sc.y + dp / 2 + 0.004, sc.z + sz * (hh - 0.012)), (0.05, dp + 0.012, 0.05), "rubber",
                    bevel=0.014, seg=2)
    # recess frame around the panel
    for (cx, cz, w, h) in ((0, hh - 0.017, 2 * hw - 0.04, 0.014), (0, -hh + 0.024, 2 * hw - 0.04, 0.028),
                           (-hw + 0.017, 0, 0.014, 2 * hh - 0.04), (hw - 0.017, 0, 0.014, 2 * hh - 0.04)):
        mb.boxc((cx, sc.y - 0.0, sc.z + cz), (w, 0.006, h), "plastic_black", bevel=0.002, seg=1)
    mb.boxc((0, sc.y + 0.004, sc.z), (SCREEN_W + 0.01, 0.004, SCREEN_H + 0.01), "glass_dark")
    mb.label("kessler_logo", (0, sc.y - 0.0035, sc.z - hh + 0.022), 0.09)
    for i in range(4):
        mb.cyl(0.006, 0.004, "plastic_black", sides=8, loc=(hw - 0.07 - 0.02 * i, sc.y - 0.003, sc.z - hh + 0.022), rot=(90, 0, 0))
    mb.cyl(0.003, 0.003, "emit_green", sides=6, loc=(hw - 0.16, sc.y - 0.0035, sc.z - hh + 0.022), rot=(90, 0, 0))
    # cables out of the back down to the desk
    for i, x in enumerate((-0.04, 0.05)):
        mb.tube([Vector((x, sc.y + dp + 0.035, sc.z - 0.1)), Vector((x, sc.y + dp + 0.07, sc.z - 0.15)),
                 Vector((x * 1.5, 0.15, 0.06)), Vector((x * 2 + 0.05, 0.22, 0.005))], 0.004 if i else 0.0055, "cable", sides=6)
    root = mb.finish()
    sb = MB("screen")
    sb.quad((0, 0, 0), SCREEN_W, SCREEN_H, "emit_screen", rect=(0.0, 0.0, 1.0, 1.0))
    scr = sb.finish(grime=False, wn=False)
    child(scr, root, (sc.x, sc.y - 0.0, sc.z))
    return root


# ====================================================================== pc_tower
@node("pc_tower", "floor", notes="rugged industrial PC tower, front panel faces +Z")
def pc_tower():
    mb = MB("pc_tower")
    W, D, H = 0.22, 0.48, 0.46
    mb.box((W, D, H), "paint_black", loc=(0, 0, 0.025), bevel=0.008, seg=2, cuts=(0, 2, 2))
    for x in (-0.08, 0.08):
        for y in (-0.19, 0.19):
            mb.cyl(0.018, 0.025, "rubber", sides=10, loc=(x, y, 0.0))
    # front bezel with lockable louvred door
    fy = -D / 2
    mb.box((W + 0.01, 0.03, H + 0.01), "steel_dark", loc=(0, fy - 0.01, 0.02), bevel=0.008, seg=2)
    P.louvres(mb, Vector((0, fy - 0.026, 0.18)), W - 0.05, 0.22, 9, "steel_dark", depth=0.012, angle=35, t=0.003)
    mb.cyl(0.01, 0.01, "steel", sides=10, loc=(0.07, fy - 0.03, 0.34), rot=(90, 0, 0))
    mb.boxc((-0.02, fy - 0.0265, 0.4), (0.12, 0.003, 0.045), "plastic_black")
    mb.cyl(0.011, 0.006, "steel", sides=12, loc=(0.07, fy - 0.026, 0.44), rot=(90, 0, 0))
    mb.cyl(0.0035, 0.004, "emit_green", sides=6, loc=(0.04, fy - 0.027, 0.44), rot=(90, 0, 0))
    for i in range(2):
        mb.boxc((-0.06 + 0.035 * i, fy - 0.027, 0.44), (0.016, 0.003, 0.007), "plastic_black")
    mb.label("pc_badge", (-0.02, fy - 0.0285, 0.4), 0.11)
    # carry handles on the front
    for s in (-1, 1):
        P.handle_bar(mb, Vector((s * 0.095, fy - 0.025, 0.06)), Vector((s * 0.095, fy - 0.025, 0.42)), (0, -1, 0), stand=0.03,
                     r=0.0075, mat="steel")
    # side vents + rear cables
    for s in (-1, 1):
        for k in range(8):
            mb.boxc((s * (W / 2 + 0.001), -0.05 + 0.03 * k, 0.33), (0.002, 0.012, 0.12), "plastic_black")
    for i, z in enumerate((0.38, 0.33, 0.28)):
        mb.tube([Vector((0.03 * i - 0.03, D / 2, z)), Vector((0.03 * i - 0.03, D / 2 + 0.06, z - 0.02)),
                 Vector((0.04 * i - 0.04, D / 2 + 0.1, 0.03)), Vector((0.05 * i, D / 2 + 0.25, 0.005))], 0.004, "cable", sides=6)
    return mb.finish()


# ====================================================================== keyboard
@node("keyboard", "floor", notes="rugged compact keyboard, 77 keys with legends (label_minekit), faces +Z")
def keyboard():
    mb = MB("keyboard")
    kb = json.load(open(os.path.join(HERE, "build", "kb_layout.json")))
    A = mk.atlas()
    AW, AH = A["size"]
    ax, ay, aw, ah = A["rects"]["keyboard"]
    sw, shh = A["svg"]["keyboard"]
    sx, sy = aw / sw, ah / shh
    U = 0.019
    rows = kb["rows"]
    W = 15 * U + 0.03
    Dp = rows * U + 0.035
    mb.box((W, Dp, 0.018), "steel_dark", loc=(0, 0, 0.0), bevel=0.005, seg=2)
    mb.box((W - 0.012, Dp - 0.012, 0.004), "plastic_black", loc=(0, 0.0, 0.018), bevel=0.001, seg=1)
    for s in (-1, 1):
        mb.cyl(0.006, 0.004, "rubber", sides=6, loc=(s * (W / 2 - 0.02), Dp / 2 - 0.015, -0.003))
    x0 = -15 * U / 2
    y_top = (rows * U) / 2 - 0.004
    for k in kb["keys"]:
        kx, kyp, kw, khp = k["px"]
        u0 = (ax + kx * sx) / AW
        u1 = (ax + (kx + kw) * sx) / AW
        v1 = 1 - (ay + kyp * sy) / AH
        v0 = 1 - (ay + (kyp + khp) * sy) / AH
        cx = x0 + (k["x"] + k["w"] / 2) * U
        cy = y_top - (k["row"] + 0.5) * U
        w = k["w"] * U - 0.0025
        d = U - 0.0025
        tb = bmesh.new()
        uvl = tb.loops.layers.uv.new("uv")
        z0, z1 = 0.02, 0.031 - 0.0006 * k["row"]
        ins = 0.0018
        bot = [tb.verts.new(p) for p in ((-w / 2, -d / 2, z0), (w / 2, -d / 2, z0), (w / 2, d / 2, z0), (-w / 2, d / 2, z0))]
        top = [tb.verts.new(p) for p in ((-w / 2 + ins, -d / 2 + ins, z1), (w / 2 - ins, -d / 2 + ins, z1),
                                         (w / 2 - ins, d / 2 - ins, z1), (-w / 2 + ins, d / 2 - ins, z1))]
        ft = tb.faces.new(top)
        for lp, uv in zip(ft.loops, [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]):
            lp[uvl].uv = uv
        for i in range(4):
            j = (i + 1) % 4
            f = tb.faces.new((bot[i], bot[j], top[j], top[i]))
            for lp in f.loops:
                lp[uvl].uv = (lp.vert.co.x * 3, lp.vert.co.z * 3)
        bmesh.ops.recalc_face_normals(tb, faces=tb.faces[:])
        tb.normal_update()
        mb.commit(tb, Matrix.Translation((cx, cy, 0)), ["label_minekit"] + ["plastic_black"] * 4, None, uvoff=False)
    mb.label("kessler_logo", (W / 2 - 0.05, -Dp / 2 - 0.0005, 0.009), 0.05)
    mb.tube([Vector((0, Dp / 2, 0.01)), Vector((0, Dp / 2 + 0.05, 0.006)), Vector((0.05, Dp / 2 + 0.15, 0.004)),
             Vector((0.04, Dp / 2 + 0.3, 0.004))], 0.0028, "cable", sides=5)
    return mb.finish(angle=60)


# ====================================================================== desk_lamp
@node("desk_lamp", "floor", notes="articulated desk lamp; child bulb (emit_warm) inside the shade, shade aims down/+Z")
def desk_lamp():
    mb = MB("desk_lamp")
    mb.lathe([(0.0, 0.0), (0.085, 0.0), (0.088, 0.006), (0.082, 0.026), (0.03, 0.036), (0.022, 0.05), (0.0, 0.05)],
             "paint_black", sides=20, loc=(0, 0.05, 0))
    mb.cyl(0.012, 0.012, "steel", sides=8, loc=(0.04, 0.0, 0.03), rot=(90, 0, 0))
    j0 = Vector((0, 0.05, 0.06))
    j1 = Vector((0, -0.06, 0.32))
    j2 = Vector((0, -0.24, 0.42))
    mb.boxc(j0, (0.05, 0.03, 0.03), "paint_black", bevel=0.005)
    for s in (-1, 1):
        mb.rod(j0 + Vector((s * 0.016, 0, 0)), j1 + Vector((s * 0.016, 0, 0)), 0.005, "paint_black", sides=6)
        mb.rod(j1 + Vector((s * 0.016, 0, 0)), j2 + Vector((s * 0.016, 0, 0)), 0.005, "paint_black", sides=6)
    # springs
    for a, b in ((j0 + Vector((0.03, 0.01, 0.03)), j1 + Vector((0.03, 0.03, -0.05))),
                 (j1 + Vector((0.03, -0.03, 0.03)), j2 + Vector((0.03, 0.06, -0.03)))):
        d = b - a
        n = d.normalized()
        side = n.cross(Vector((1, 0, 0))).normalized()
        side2 = n.cross(side).normalized()
        pts = []
        for k in range(49):
            t = k / 48
            ang = t * 2 * math.pi * 12
            pts.append(a + d * t + (side * math.cos(ang) + side2 * math.sin(ang)) * 0.006)
        mb.tube(pts, 0.0012, "steel", sides=4)
    for j in (j1, j2):
        mb.cyl(0.012, 0.05, "steel", sides=10, Mx=trs(j - Vector((0.025, 0, 0)), (0, 90, 0)))
    # shade, aimed forward-down
    shade_M = Matrix.Translation(j2 + Vector((0, -0.04, -0.02))) @ rotm((-125, 0, 0))
    mb.lathe([(0.0, 0.0), (0.022, 0.0), (0.03, -0.02), (0.045, -0.06), (0.075, -0.11), (0.078, -0.114), (0.072, -0.114),
              (0.04, -0.062), (0.026, -0.024), (0.0, -0.02)], "paint_green", sides=20, Mx=shade_M)
    root = mb.finish()
    bb = MB("bulb")
    bb.lathe([(0.0, 0.0), (0.012, -0.004), (0.022, -0.02), (0.024, -0.035), (0.018, -0.05), (0.0, -0.056)], "emit_warm", sides=12)
    bulb = bb.finish(grime=False)
    bloc = shade_M @ Vector((0, 0, -0.035))
    child(bulb, root, (bloc.x, bloc.y, bloc.z))
    bulb.rotation_euler = (-125 * DEG, 0, 0)
    return root
