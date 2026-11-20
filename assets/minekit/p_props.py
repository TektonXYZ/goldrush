"""Remaining mine props (front = -Y = three.js +Z). Wall items: origin at the centre of the back face (wall)."""
import math
import random

import bmesh
from mathutils import Matrix, Vector, noise

import mk
import parts as P
from mk import DEG, MB, child, empty, frame, rotm, trs
from p_office import hard_hat
from parts import board, timber

BUILD = {}


def node(name, kind="floor", **meta):
    def deco(fn):
        BUILD[name] = (fn, dict(kind=kind, **meta))
        return fn
    return deco


WALLG = dict(floor=False)


# ====================================================================== tool_rack
def pickaxe(mb, Mx):
    """Pickaxe in local coords: handle along -Z from the head at the origin, head along X."""
    mb.lathe([(0.0, 0.0), (0.018, 0.0), (0.02, -0.05), (0.017, -0.6), (0.021, -0.86), (0.0, -0.87)], "wood_timber", sides=8,
             Mx=Mx @ Matrix.Translation((0, 0, 0.03)))
    pts = []
    for k in range(9):
        t = -1 + 2 * k / 8
        pts.append(Mx @ Vector((t * 0.3, 0, -0.035 * t * t + 0.02)))
    radii = [0.006 + 0.022 * (1 - abs(-1 + 2 * k / 8)) ** 0.7 for k in range(9)]
    mb.tube(pts, 0.02, "steel_dark", sides=6, radii=radii, caps=True)
    mb.box((0.07, 0.05, 0.07), "steel_dark", center=True, Mx=Mx @ Matrix.Translation((0, 0, 0.0)), bevel=0.008, seg=1)


def shovel(mb, Mx):
    """Round-point shovel: blade at the bottom (local -Z), D-grip at the top."""
    mb.lathe([(0.0, 0.0), (0.016, 0.0), (0.018, -0.9), (0.02, -0.98), (0.0, -0.99)], "wood_timber", sides=8, Mx=Mx)
    grip = [Mx @ Vector((-0.06, 0, 0.12)), Mx @ Vector((-0.07, 0, 0.04)), Mx @ Vector((-0.02, 0, -0.01)),
            Mx @ Vector((0.02, 0, -0.01)), Mx @ Vector((0.07, 0, 0.04)), Mx @ Vector((0.06, 0, 0.12)), Mx @ Vector((-0.06, 0, 0.12))]
    mb.tube(grip, 0.012, "steel_dark", sides=6)
    mb.cyl(0.022, 0.16, "steel_dark", sides=8, Mx=Mx @ Matrix.Translation((0, 0, -1.1)), r2=0.019)

    def dish(u, v):
        x = (u - 0.5) * 0.28
        z = (v - 0.5) * 0.32
        taper = 1.0 - 0.6 * max(0.0, -(v - 0.5) * 2) ** 2 * abs(x) / 0.14
        return Vector((x * taper - x, -0.03 * (1 - (2 * u - 1) ** 2), 0))
    mb.grid(0.28, 0.32, 6, 6, "rust", Mx @ Matrix.Translation((0, 0.0, -1.27)), fn=dish)
    mb.grid(0.28, 0.32, 6, 6, "steel", Mx @ Matrix.Translation((0, 0.0025, -1.27)) @ rotm((0, 0, 180)), fn=dish)


def sledge(mb, Mx):
    mb.lathe([(0.0, 0.0), (0.017, 0.0), (0.016, -0.5), (0.02, -0.82), (0.0, -0.83)], "wood_timber", sides=8, Mx=Mx)
    mb.box((0.2, 0.065, 0.065), "cast_iron", center=True, Mx=Mx @ Matrix.Translation((0, 0, 0.0)), bevel=0.01, seg=2)


@node("tool_rack", "wall", grime=WALLG, notes="wall rack: pickaxe, shovel, sledgehammer, pry bar on two timber rails; "
                                              "origin = wall surface at the rack centre, mount ~1.35 m")
def tool_rack():
    mb = MB("tool_rack")
    for z in (0.32, -0.28):
        timber(mb, (-0.72, -0.045, z), (0.72, -0.045, z), 0.09, 0.13, up=(0, 0, 1), bevel=0.01, cuts=2, bow=0.002)
        for x in (-0.6, 0.6):
            P.bolt(mb, (x, -0.0905, z), (0, -1, 0), r=0.008, head=0.014, stud=0.0)
    pegs = [(-0.52, 0.36), (-0.36, 0.36), (-0.05, 0.36), (0.12, 0.36), (0.4, 0.36), (0.5, 0.36), (0.62, -0.24), (0.62, 0.36)]
    for x, z in pegs:
        mb.rod((x, -0.09, z), (x, -0.2, z + 0.03), 0.011, "steel_dark", sides=6)
    pickaxe(mb, trs((-0.44, -0.17, 0.42), (0, 0, 0)))
    shovel(mb, trs((0.035, -0.16, 0.5), (0, 0, 0)))
    sledge(mb, trs((0.45, -0.17, 0.42), (0, 0, 0)))
    bar = [Vector((0.66, -0.2, 0.48)), Vector((0.66, -0.22, 0.42)), Vector((0.66, -0.2, -0.75)), Vector((0.67, -0.24, -0.8)),
           Vector((0.68, -0.28, -0.79))]
    mb.tube(bar, 0.013, "steel", sides=6)
    return mb.finish()


# ====================================================================== ore_bin
FILL_Z = 0.58


@node("ore_bin", "floor", grime=dict(dirt=0.3, streaks=0.1),
      notes=f"hand-ore drop bin (rim at 1.12 m) on legs with a front chute; child fill = ore heap, origin on the bin floor "
            f"(y={FILL_Z}): scale fill.scale.y 0 -> 1 for empty -> full (material coal_ore: swap per ore)")
def ore_bin():
    mb = MB("ore_bin")
    W, Dp = 1.3, 1.1
    top = 1.12
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.boxc((sx * (W / 2 - 0.03), sy * (Dp / 2 - 0.03), top / 2), (0.07, 0.07, top), "steel_dark", bevel=0.005, seg=1)
            mb.box((0.16, 0.16, 0.012), "steel_dark", loc=(sx * (W / 2 - 0.03), sy * (Dp / 2 - 0.03), 0.0), bevel=0.003, seg=1)
    walls = ((0, -Dp / 2, W, 0.008), (0, Dp / 2, W, 0.008), (-W / 2, 0, 0.008, Dp), (W / 2, 0, 0.008, Dp))
    for cx, cy, sx_, sy_ in walls:
        mb.box((sx_, sy_, top - FILL_Z + 0.02), "steel_dark", loc=(cx, cy, FILL_Z - 0.02), bevel=0.002, seg=1, cuts=(2, 0, 1))
    mb.box((W - 0.01, Dp - 0.01, 0.012), "rust", loc=(0, 0, FILL_Z - 0.012))
    for cx, cy, sx_, sy_ in ((0, -Dp / 2, W + 0.02, 0.05), (0, Dp / 2, W + 0.02, 0.05), (-W / 2, 0, 0.05, Dp), (W / 2, 0, 0.05, Dp)):
        mb.box((sx_, sy_, 0.035), "paint_yellow", loc=(cx, cy, top - 0.01), bevel=0.004, seg=1)
    # hopper under the bin floor down to a front chute with a slide gate
    hp = [Vector((-W / 2, -Dp / 2, FILL_Z - 0.02)), Vector((W / 2, -Dp / 2, FILL_Z - 0.02)), Vector((0.2, -Dp / 2 - 0.05, 0.32)),
          Vector((-0.2, -Dp / 2 - 0.05, 0.32))]
    mb.poly(hp, "steel_dark", thick=0.008)
    mb.poly([Vector((-W / 2, Dp / 2, FILL_Z - 0.02)), Vector((-0.2, -Dp / 2 - 0.05, 0.32)), Vector((0.2, -Dp / 2 - 0.05, 0.32)),
             Vector((W / 2, Dp / 2, FILL_Z - 0.02))], "steel_dark", thick=0.008)
    mb.box((0.46, 0.3, 0.012), "steel_dark", loc=(0, -Dp / 2 - 0.18, 0.3), rot=(-20, 0, 0), bevel=0.003, seg=1)
    for s in (-1, 1):
        mb.box((0.012, 0.32, 0.1), "steel_dark", loc=(s * 0.23, -Dp / 2 - 0.18, 0.3), rot=(-20, 0, 0))
    mb.box((0.44, 0.012, 0.16), "galvanized", loc=(0, -Dp / 2 - 0.045, 0.34), bevel=0.003, seg=1)
    mb.rod((0.0, -Dp / 2 - 0.06, 0.5), (0.0, -Dp / 2 - 0.2, 0.72), 0.014, "steel", sides=8)
    mb.cyl(0.024, 0.06, "plastic_black", sides=8, Mx=trs((0.0, -Dp / 2 - 0.2, 0.72), (-58, 0, 0)))
    mb.label("ore_drop", (0, -Dp / 2 - 0.006, top - 0.17), 0.6)
    root = mb.finish()
    # ore heap (child, grows from the bin floor)
    fb = MB("fill")
    rng = random.Random(5)
    tb = bmesh.new()
    nx, ny = 8, 7
    hgt = top - 0.04 - FILL_Z
    vs = []
    for j in range(ny + 1):
        row = []
        for i in range(nx + 1):
            u, v = i / nx * 2 - 1, j / ny * 2 - 1
            r = max(abs(u), abs(v))
            h = hgt * (1 - 0.55 * r ** 2) + 0.03 * noise.noise(Vector((u * 3, v * 3, 2.0)))
            row.append(tb.verts.new((u * (W / 2 - 0.02), v * (Dp / 2 - 0.02), max(0.0, h) if r < 1 else 0.0)))
        vs.append(row)
    for j in range(ny):
        for i in range(nx):
            tb.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
    bmesh.ops.recalc_face_normals(tb, faces=tb.faces[:])
    for f in tb.faces:
        if f.normal.z < 0:
            f.normal_flip()
    tb.normal_update()
    fb.commit(tb, Matrix.Identity(4), "coal_ore", mk.uv_world_box, flat=True)
    for k in range(26):
        u, v = rng.uniform(-0.9, 0.9), rng.uniform(-0.9, 0.9)
        r = max(abs(u), abs(v))
        z = hgt * (1 - 0.55 * r ** 2)
        s = rng.uniform(0.07, 0.14)
        fb.rock((u * (W / 2 - 0.1), v * (Dp / 2 - 0.1), z - s * 0.3), (s, s * rng.uniform(0.7, 1.1), s * 0.7), "coal_ore",
                seed=k + 40, detail=0)
    fill = fb.finish(grime=True)
    child(fill, root, (0, 0, FILL_Z))
    return root


# ====================================================================== lockers
@node("lockers", "floor", notes="bank of four steel lockers (numbered 01-04) on a plinth, doors on +Z")
def lockers():
    mb = MB("lockers")
    W, Dp, H = 1.2, 0.5, 1.85
    mb.box((W, Dp - 0.04, 0.1), "paint_black", loc=(0, 0.02, 0.0), bevel=0.004, seg=1)
    mb.box((W, Dp, H - 0.1), "paint_grey", loc=(0, 0, 0.1), bevel=0.006, seg=2)
    dw = (W - 0.03) / 4
    for i in range(4):
        x = -W / 2 + 0.015 + dw * (i + 0.5)
        mb.box((dw - 0.012, 0.016, H - 0.16), "paint_grey", loc=(x, -Dp / 2 - 0.006, 0.13), bevel=0.004, seg=2)
        for k in range(6):
            mb.boxc((x, -Dp / 2 - 0.0145, H - 0.18 - 0.03 * k), (dw * 0.55, 0.002, 0.012), "plastic_black")
        for k in range(6):
            mb.boxc((x, -Dp / 2 - 0.0145, 0.3 + 0.03 * k), (dw * 0.55, 0.002, 0.012), "plastic_black")
        mb.box((0.025, 0.035, 0.12), "steel", loc=(x + dw / 2 - 0.05, -Dp / 2 - 0.03, 0.95), bevel=0.004, seg=1)
        mb.cyl(0.012, 0.012, "brass", sides=8, loc=(x + dw / 2 - 0.05, -Dp / 2 - 0.016, 1.12), rot=(90, 0, 0))
        mb.label(f"locker_{i + 1}", (x, -Dp / 2 - 0.0145, H - 0.38), 0.07)
        for z in (0.35, 1.45):
            mb.rod((x - dw / 2 + 0.012, -Dp / 2 - 0.012, z - 0.05), (x - dw / 2 + 0.012, -Dp / 2 - 0.012, z + 0.05), 0.007,
                   "steel_dark", sides=6)
    # stuff on top: a helmet and a cardboard-ish box
    hard_hat(mb, (-0.25, 0.0, H), yaw=-20, mat="helmet_white", sticker_name="helmet_cross")
    mb.box((0.38, 0.3, 0.22), "wood_planks", loc=(0.3, 0.02, H), rot=(0, 0, 6), bevel=0.004, seg=1)
    return mb.finish()


# ====================================================================== first_aid
@node("first_aid", "wall", grime=WALLG, notes="wall first-aid cabinet, origin = back centre, mount ~1.4 m")
def first_aid():
    mb = MB("first_aid")
    W, D, H = 0.42, 0.15, 0.5
    mb.box((W, D, H), "paint_green", loc=(0, -D / 2, -H / 2), bevel=0.008, seg=2)
    mb.box((W - 0.03, 0.012, H - 0.03), "paint_green", loc=(0, -D - 0.006, -H / 2 + 0.015), bevel=0.006, seg=2)
    mb.label("first_aid", (0, -D - 0.0125, 0.02), 0.3)
    for z in (-0.15, 0.15):
        mb.rod((-W / 2 - 0.004, -D, z - 0.03), (-W / 2 - 0.004, -D, z + 0.03), 0.007, "steel_dark", sides=6)
    mb.box((0.02, 0.03, 0.08), "steel", loc=(W / 2 - 0.04, -D - 0.025, -0.04), bevel=0.004, seg=1)
    return mb.finish()


# ====================================================================== phone_box
@node("phone_box", "wall", grime=WALLG, notes="emergency mine phone in a hooded box with a strobe, origin = back centre, "
                                              "mount ~1.45 m")
def phone_box():
    mb = MB("phone_box")
    W, D, H = 0.34, 0.2, 0.46
    mb.box((W, D, H), "paint_orange", loc=(0, -D / 2, -H / 2), bevel=0.008, seg=2, cuts=(1, 0, 1))
    mb.box((W - 0.06, D - 0.04, H - 0.12), "plastic_black", loc=(0, -D / 2 - 0.0, -H / 2 + 0.05), bevel=0.004, seg=1)
    mb.box((W - 0.1, 0.004, 0.12), "steel", loc=(0, -D - 0.002, -0.16), bevel=0.0015, seg=1)
    # handset on its cradle + coiled cord
    hs = trs((-0.03, -D - 0.035, 0.04), (0, 0, 0))
    mb.box((0.05, 0.05, 0.22), "plastic_black", center=True, Mx=hs, bevel=0.012, seg=2)
    for s in (-1, 1):
        mb.box((0.075, 0.07, 0.055), "plastic_black", center=True, Mx=hs @ Matrix.Translation((0, -0.01, s * 0.12)), bevel=0.012, seg=2)
    mb.box((0.03, 0.04, 0.05), "steel_dark", loc=(0.06, -D - 0.02, 0.15), bevel=0.004, seg=1)
    coil = []
    for k in range(60):
        t = k / 59
        a = t * 2 * math.pi * 14
        c = Vector((-0.03 + 0.02 * t, -D - 0.06, -0.08 - 0.12 * t))
        coil.append(c + Vector((math.cos(a) * 0.012, math.sin(a) * 0.012, 0)))
    mb.tube(coil, 0.0025, "plastic_black", sides=4)
    for i in range(12):
        mb.boxc((0.07 + 0.024 * (i % 3), -D - 0.004, 0.02 - 0.024 * (i // 3)), (0.018, 0.006, 0.018), "steel")
    # label on a plate above the box + strobe
    mb.box((0.3, 0.01, 0.17), "paint_white", loc=(0, -0.005, H / 2 + 0.02), bevel=0.003, seg=1)
    mb.label("phone_label", (0, -0.0106, H / 2 + 0.105), 0.28)
    mb.cyl(0.035, 0.03, "plastic_black", sides=12, loc=(0.12, -0.06, H / 2))
    mb.lathe([(0.0, 0.07), (0.022, 0.065), (0.03, 0.04), (0.031, 0.0), (0.0, 0.0)], "emit_red", sides=12, loc=(0.12, -0.06, H / 2 + 0.03))
    mb.tube([Vector((0.1, -0.1, -H / 2)), Vector((0.1, -0.1, -H / 2 - 0.12)), Vector((0.1, -0.03, -H / 2 - 0.25)),
             Vector((0.1, -0.02, -H / 2 - 0.6))], 0.008, "cable", sides=6)
    return mb.finish()


# ====================================================================== map_board
@node("map_board", "wall", grime=WALLG, notes="framed mine-plan board, child board_face (sign_face, UV 0-1, 1.5 x 0.98 m), "
                                              "origin = back centre, mount ~1.5 m")
def map_board():
    mb = MB("map_board")
    W, H, t = 1.6, 1.08, 0.05
    mb.box((W - 0.08, 0.018, H - 0.08), "wood_planks", loc=(0, -0.025, -(H - 0.08) / 2))
    for (cx, cz, w, h) in ((0, H / 2 - 0.035, W, 0.07), (0, -H / 2 + 0.035, W, 0.07), (-W / 2 + 0.035, 0, 0.07, H),
                           (W / 2 - 0.035, 0, 0.07, H)):
        mb.boxc((cx, -t / 2, cz), (w, t, h), "wood_dark", bevel=0.008, seg=2)
    mb.boxc((0, -0.055, -H / 2 + 0.03), (W - 0.1, 0.06, 0.02), "wood_dark", bevel=0.004)
    for x in (-0.2, -0.12, 0.3):
        mb.rod((x, -0.07, -H / 2 + 0.045), (x + 0.11, -0.07, -H / 2 + 0.047), 0.005, ("paint_red" if x > 0 else "plastic_black"), sides=6)
    for x in (-0.6, 0.6):
        P.bolt(mb, (x, -t - 0.001, H / 2 - 0.035), (0, -1, 0), r=0.006, head=0.011, stud=0.0, washer=False)
    root = mb.finish()
    fb = MB("board_face")
    fb.quad((0, 0, 0), W - 0.1, H - 0.1, "sign_face", rect=(0.0, 0.0, 1.0, 1.0))
    face = fb.finish(grime=False, wn=False)
    child(face, root, (0, -0.0345, 0.0))
    return root


# ====================================================================== explosives_crate
@node("explosives_crate", "floor", notes="wooden case of explosives with stencils and the 1.1D diamond, rope handles")
def explosives_crate():
    mb = MB("explosives_crate")
    W, Dp, H = 0.6, 0.4, 0.34
    rng = mb.rng
    for z in (0.0, 0.11, 0.22):
        for s in (-1, 1):
            board(mb, (-W / 2, s * (Dp / 2 - 0.01), z + 0.055), (W / 2, s * (Dp / 2 - 0.01), z + 0.055), 0.02, 0.105,
                  "wood_planks", up=(0, 0, 1), bevel=0.003)
        for s in (-1, 1):
            board(mb, (s * (W / 2 - 0.01), -Dp / 2 + 0.02, z + 0.055), (s * (W / 2 - 0.01), Dp / 2 - 0.02, z + 0.055), 0.02,
                  0.105, "wood_planks", up=(0, 0, 1), bevel=0.003)
    for k in range(4):
        board(mb, (-W / 2 - 0.005, -Dp / 2 + 0.05 + 0.1 * k, H - 0.0), (W / 2 + 0.005, -Dp / 2 + 0.05 + 0.1 * k, H - 0.0),
              0.098, 0.018, "wood_planks", up=(0, 0, 1), bevel=0.003)
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.boxc((sx * (W / 2 + 0.005), sy * (Dp / 2 + 0.005), H / 2), (0.03, 0.03, H), "wood_dark", bevel=0.004, seg=1)
    for s in (-1, 1):
        rope = [Vector((s * (W / 2 + 0.012), -0.07, 0.24)), Vector((s * (W / 2 + 0.04), -0.05, 0.2)),
                Vector((s * (W / 2 + 0.045), 0.0, 0.18)), Vector((s * (W / 2 + 0.04), 0.05, 0.2)), Vector((s * (W / 2 + 0.012), 0.07, 0.24))]
        mb.tube(rope, 0.008, "canvas", sides=6)
    mb.label("explosives_diamond", (0.0, -Dp / 2 - 0.0015, 0.17), 0.2, 0.2)
    mb.label("explosives_stencil", (0.0, Dp / 2 + 0.0015, 0.19), 0.5, rot=(0, 0, 180))
    mb.label("keep_fire_away", (0.0, 0.0, H + 0.0105), 0.5, rot=(-90, 0, 0))
    mb.label("explosives_stencil", (W / 2 + 0.0015, 0.0, 0.17), 0.34, rot=(0, 0, 90))
    return mb.finish()


# ====================================================================== detonator
@node("detonator", "floor", notes="plunger blasting machine (plunger up), terminals on top, brass plate on +Z")
def detonator():
    mb = MB("detonator")
    W, Dp, H = 0.26, 0.19, 0.24
    mb.box((W, Dp, H), "wood_dark", loc=(0, 0, 0), bevel=0.008, seg=2)
    for s in (-1, 1):
        mb.box((W + 0.01, 0.02, 0.02), "brass", loc=(0, s * (Dp / 2 - 0.0), H - 0.025), bevel=0.003, seg=1)
    mb.box((W - 0.02, Dp - 0.02, 0.012), "steel_dark", loc=(0, 0, H), bevel=0.003, seg=1)
    mb.cyl(0.024, 0.03, "brass", sides=10, loc=(0, 0, H + 0.012))
    mb.rod((0, 0, H + 0.04), (0, 0, H + 0.24), 0.011, "steel", sides=10)
    mb.rod((-0.12, 0, H + 0.25), (0.12, 0, H + 0.25), 0.017, "wood_timber", sides=10, bevel=0.004)
    for x in (-0.09, 0.09):
        mb.cyl(0.012, 0.02, "brass", sides=8, loc=(x, 0.06, H + 0.012))
        mb.cyl(0.016, 0.006, "brass", sides=6, loc=(x, 0.06, H + 0.026))
        wire = [Vector((x, 0.06, H + 0.032)), Vector((x * 1.2, 0.12, H + 0.05)), Vector((x * 1.8, 0.22, 0.12)),
                Vector((x * 2.0, 0.34, 0.01)), Vector((x * 2.5, 0.6, 0.006))]
        mb.tube(wire, 0.0035, "hose_red" if x > 0 else "cable", sides=5)
    mb.label("detonator_plate", (0, -Dp / 2 - 0.0015, 0.12), 0.2)
    for s in (-1, 1):
        P.handle_bar(mb, Vector((s * (W / 2 + 0.0), -0.05, 0.16)), Vector((s * (W / 2 + 0.0), 0.05, 0.16)), (s, 0, 0), stand=0.03,
                     r=0.006, mat="steel_dark")
    return mb.finish()


# ====================================================================== barrel
@node("barrel", "floor", grime=dict(dirt=0.3, streaks=0.15), notes="205 L steel drum (hydraulic oil label)")
def barrel():
    mb = MB("barrel")
    R, H = 0.2925, 0.88
    prof = [(0.0, 0.008), (R - 0.02, 0.008), (R - 0.012, 0.0), (R, 0.012), (R + 0.006, 0.02), (R, 0.03), (R, 0.27),
            (R + 0.012, 0.285), (R, 0.3), (R, 0.58), (R + 0.012, 0.595), (R, 0.61), (R, H - 0.03), (R + 0.006, H - 0.02),
            (R, H - 0.012), (R - 0.012, H), (R - 0.02, H - 0.008), (0.0, H - 0.008)]
    rng = random.Random(3)

    def dent(v):
        d = (Vector((v.x, v.y, v.z)) - Vector((0.2, -0.2, 0.45))).length
        if d < 0.12:
            k = (1 - (d / 0.12) ** 2) ** 2
            v.x *= 1 - 0.06 * k
            v.y *= 1 - 0.06 * k
        return v
    faces = mb.lathe(prof, "paint_blue", sides=24)
    for v in {v for f in faces for v in f.verts}:
        v.co = dent(v.co)
    mb.cyl(0.028, 0.012, "steel", sides=8, loc=(0.17, 0.0, H - 0.008))
    mb.cyl(0.018, 0.01, "steel", sides=8, loc=(-0.17, 0.0, H - 0.008))
    mb.clabel("barrel_label", Matrix.Identity(4), R + 0.0018, theta=0, w=0.46, z=0.44, segs=10)
    return mb.finish()


# ====================================================================== crate
@node("crate", "floor", notes="wooden shipping crate, stencilled IRONSIDE MINING CO.")
def crate():
    mb = MB("crate")
    W, Dp, H = 1.0, 0.8, 0.72
    mb.box((W - 0.04, Dp - 0.04, H - 0.04), "wood_planks", loc=(0, 0, 0.02), bevel=0.004, seg=1, cuts=(2, 2, 2))
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.boxc((sx * (W / 2 - 0.03), sy * (Dp / 2 - 0.03), H / 2), (0.07, 0.07, H), "wood_planks", bevel=0.006, seg=1)
    for z in (0.035, H - 0.035):
        for s in (-1, 1):
            mb.boxc((0, s * (Dp / 2 - 0.01), z), (W, 0.03, 0.07), "wood_planks", bevel=0.005, seg=1)
            mb.boxc((s * (W / 2 - 0.01), 0, z), (0.03, Dp, 0.07), "wood_planks", bevel=0.005, seg=1)
    for s in (-1, 1):
        mb.beam((-W / 2 + 0.07, s * (Dp / 2 - 0.005), 0.07), (W / 2 - 0.07, s * (Dp / 2 - 0.005), H - 0.07), 0.025, 0.08,
                "wood_planks", up=(0, s, 0), bevel=0.004)
    for x in (-0.3, 0.0, 0.3):
        mb.boxc((x, 0, H + 0.005), (0.09, Dp, 0.02), "wood_planks", bevel=0.003, seg=1)
    mb.label("crate_stencil", (0.0, -Dp / 2 + 0.02 - 0.0015, 0.42), 0.62)
    mb.label("this_side_up", (0.33, -Dp / 2 + 0.02 - 0.0015, 0.16), 0.18)
    mb.label("crate_stencil", (W / 2 - 0.02 + 0.0015, 0.0, 0.42), 0.5, rot=(0, 0, 90))
    return mb.finish()


# ====================================================================== pallet
@node("pallet", "floor", notes="1.2 x 0.8 m EUR pallet")
def pallet():
    mb = MB("pallet")
    rng = mb.rng
    for x in (-0.555, 0.0, 0.555):
        for y in (-0.345, 0.0, 0.345):
            mb.boxc((x, y, 0.022 + 0.0389), (0.145 if x == 0 else 0.1, 0.1 if y else 0.145, 0.078), "wood_planks", bevel=0.004, seg=1)
    for y in (-0.345, 0.0, 0.345):
        board(mb, (-0.6, y, 0.022 + 0.078 + 0.011), (0.6, y, 0.022 + 0.078 + 0.011), 0.145 if y == 0 else 0.1, 0.022,
              "wood_planks", up=(0, 0, 1), bevel=0.003)
    for k, y in enumerate((-0.3275, -0.1638, 0.0, 0.1638, 0.3275)):
        board(mb, (-0.6, y, 0.122 + 0.011), (0.6, y, 0.122 + 0.011), 0.145 if k in (0, 2, 4) else 0.1, 0.022, "wood_planks",
              up=(0, 0, 1), bevel=0.003)
    for x in (-0.555, 0.0, 0.555):
        board(mb, (x, -0.4, 0.011), (x, 0.4, 0.011), 0.1 if x else 0.145, 0.022, "wood_planks", up=(0, 0, 1), bevel=0.003)
    return mb.finish()


# ====================================================================== signs
def plate_sign(name, label, w, glow=False, frame_mat="steel_dark", plate_mat="paint_white"):
    mb = MB(name)
    A = mk.atlas()
    x, y, rw, rh = A["rects"][label]
    h = w * rh / rw
    mb.box((w + 0.02, 0.006, h + 0.02), plate_mat, loc=(0, -0.003, -(h + 0.02) / 2), bevel=0.003, seg=1)
    mb.label(label, (0, -0.0065, 0.0), w, mat="label_minekit_glow" if glow else "label_minekit")
    for sx in (-1, 1):
        for sz in (-1, 1):
            mb.cyl(0.006, 0.004, "steel", sides=6, loc=(sx * (w / 2 - 0.005), -0.006, sz * (h / 2 - 0.005)), rot=(90, 0, 0))
    return mb


@node("sign_danger", "wall", grime=WALLG, notes="DANGER UNSUPPORTED GROUND / KEEP OUT plate, origin = back centre")
def sign_danger():
    return plate_sign("sign_danger", "danger_ground", 0.6).finish()


@node("sign_exit", "wall", grime=WALLG, notes="photoluminescent/lit EXIT sign in a housing (label glows on its own, also "
                                              "during power cuts), origin = back centre")
def sign_exit():
    mb = MB("sign_exit")
    w, h = 0.52, 0.23
    mb.box((w + 0.06, 0.06, h + 0.06), "plastic_black", loc=(0, -0.03, -(h + 0.06) / 2), bevel=0.01, seg=2)
    mb.label("exit_sign", (0, -0.0615, 0.0), w, h, mat="label_minekit_glow")
    for s in (-1, 1):
        mb.box((0.03, 0.04, 0.05), "steel_dark", loc=(s * (w / 2 - 0.02), -0.02, h / 2 + 0.03), bevel=0.003, seg=1)
    return mb.finish()


@node("sign_level", "wall", grime=WALLG, notes="level sign; child face (sign_face, UV 0-1, 0.84 x 0.44 m) for the game "
                                               "to paint 'LEVEL 1 · COAL' etc., origin = back centre")
def sign_level():
    mb = MB("sign_level")
    W, H = 0.9, 0.5
    mb.box((W, 0.02, H), "paint_black", loc=(0, -0.01, -H / 2), bevel=0.006, seg=2)
    for sx in (-1, 1):
        for sz in (-1, 1):
            P.bolt(mb, (sx * (W / 2 - 0.025), -0.02, sz * (H / 2 - 0.025)), (0, -1, 0), r=0.006, head=0.011, stud=0.0,
                   washer=False)
    root = mb.finish()
    fb = MB("face")
    fb.quad((0, 0, 0), W - 0.06, H - 0.06, "sign_face", rect=(0.0, 0.0, 1.0, 1.0))
    face = fb.finish(grime=False, wn=False)
    child(face, root, (0, -0.0205, 0.0))
    return root


# ====================================================================== fan_unit
@node("fan_unit", "floor", grime=dict(dirt=0.28),
      notes="auxiliary axial fan (0.8 m duct size), blows toward +Z; child blades spins about local Z (hub centre)")
def fan_unit():
    mb = MB("fan_unit")
    R, L, cz = 0.42, 1.0, 0.62
    Mx = Matrix.Translation((0, 0.0, cz)) @ rotm((90, 0, 0))  # cylinder axis along -Y (front)
    mb.lathe([(R, -L / 2), (R, L / 2)], "paint_yellow", sides=24, Mx=Mx)
    mb.lathe([(R - 0.006, L / 2), (R - 0.006, -L / 2)], "steel_dark", sides=24, Mx=Mx)
    for z in (-L / 2, L / 2):
        mb.lathe([(R - 0.006, z - 0.012), (R + 0.045, z - 0.012), (R + 0.045, z + 0.012), (R - 0.006, z + 0.012)], "paint_yellow",
                 sides=24, Mx=Mx)
        for k in range(12):
            a = k / 12 * 2 * math.pi
            P.hexnut(mb, Mx @ Vector(((R + 0.025) * math.cos(a), (R + 0.025) * math.sin(a), z + (0.016 if z > 0 else -0.016))),
                     0.009, 0.008, Mx.to_3x3() @ Vector((0, 0, 1 if z > 0 else -1)), "steel_dark")
    # intake bellmouth + guard at the back (+Y)
    mb.lathe([(R - 0.006, L / 2 + 0.012), (R + 0.03, L / 2 + 0.06), (R + 0.09, L / 2 + 0.1)], "paint_yellow", sides=24, Mx=Mx)
    for rr in (0.1, 0.2, 0.3, 0.42):
        P.ring(mb, Mx @ Vector((0, 0, L / 2 + 0.1)), rr, 0.004, axis=Mx.to_3x3() @ Vector((0, 0, 1)), mat="steel_dark", segs=20, sides=4)
    for k in range(8):
        a = k / 8 * 2 * math.pi
        mb.rod(Mx @ Vector((0, 0, L / 2 + 0.1)), Mx @ Vector((math.cos(a) * 0.48, math.sin(a) * 0.48, L / 2 + 0.1)), 0.004,
               "steel_dark", sides=4)
    # motor (inside, behind the blades) on struts
    mb.lathe([(0.0, 0.05), (0.16, 0.05), (0.17, 0.08), (0.17, 0.36), (0.12, 0.42), (0.0, 0.42)], "paint_grey", sides=16, Mx=Mx)
    for k in range(3):
        a = k / 3 * 2 * math.pi + 0.3
        mb.rod(Mx @ Vector((math.cos(a) * 0.16, math.sin(a) * 0.16, 0.25)), Mx @ Vector((math.cos(a) * (R - 0.01), math.sin(a) * (R - 0.01), 0.25)),
               0.012, "steel_dark", sides=6)
    # skid + cradle legs + junction box + cable
    for s in (-1, 1):
        mb.box((0.08, L + 0.3, 0.08), "steel_dark", loc=(s * 0.32, 0.0, 0.0), bevel=0.005, seg=1)
        for y in (-0.32, 0.32):
            mb.beam((s * 0.32, y, 0.08), (s * 0.25, y, cz - R * 0.8), 0.06, 0.06, "steel_dark", up=(0, 1, 0), bevel=0.004)
    for y in (-0.32, 0.32):
        mb.boxc((0, y, 0.12), (0.7, 0.06, 0.06), "steel_dark", bevel=0.004)
    jb = Vector((R + 0.02, 0.12, cz + 0.12))
    mb.boxc(jb + Vector((0.04, 0, 0)), (0.08, 0.16, 0.14), "paint_grey", bevel=0.008)
    mb.tube([jb + Vector((0.06, 0.08, -0.06)), jb + Vector((0.08, 0.2, -0.2)), Vector((0.55, 0.45, 0.03)), Vector((0.7, 0.9, 0.03))],
            0.016, "cable", sides=8)
    mb.label("fan_label", (-R - 0.003, 0.05, cz + 0.05), 0.4, rot=(0, 0, -90))
    mb.label("airflow_arrow", (R + 0.003, 0.0, cz + 0.22), 0.3, rot=(0, 0, 90))
    root = mb.finish()
    bb = MB("blades")
    bb.cyl(0.11, 0.09, "steel_dark", sides=16, Mx=rotm((90, 0, 0)) @ Matrix.Translation((0, 0, -0.045)), bevel=0.01)
    bb.lathe([(0.0, -0.05), (0.06, -0.05), (0.1, -0.03), (0.11, 0.0)], "steel_dark", sides=16, Mx=rotm((90, 0, 0)) @ Matrix.Translation((0, 0, -0.045)))
    for k in range(8):
        a = k / 8 * 360

        def twist(v):
            t = (v.x - 0.1) / 0.3
            ang = (35 - 18 * t) * DEG
            y, z = v.y, v.z
            return Vector((v.x, y * math.cos(ang) - z * math.sin(ang) * 0.0, z * math.cos(ang) + y * math.sin(ang)))
        bb.box((0.3, 0.012, 0.13), "aluminium", center=True,
               Mx=rotm((0, a, 0)) @ Matrix.Translation((0.11 + 0.15, 0, 0)) @ rotm((40, 0, 0)), bevel=0.003, seg=1, cuts=(2, 0, 0))
    blades = bb.finish()
    child(blades, root, (0, -0.12, cz))
    return root


# ====================================================================== light_stand
@node("light_stand", "floor", notes="tripod work light; child bulb = lamp lens (emit_warm) aimed +Z and 20 deg down")
def light_stand():
    mb = MB("light_stand")
    hub = Vector((0, 0, 0.75))
    for k in range(3):
        a = k / 3 * 2 * math.pi + math.pi / 2
        foot = Vector((math.cos(a) * 0.5, math.sin(a) * 0.5, 0.02))
        mb.rod(hub, foot, 0.016, "paint_yellow", sides=8)
        mb.cyl(0.03, 0.02, "rubber", sides=8, loc=foot - Vector((0, 0, 0.02)))
        mid = hub.lerp(foot, 0.5)
        mb.rod(mid, Vector((0, 0, 0.42)), 0.009, "paint_yellow", sides=6)
    mb.cyl(0.03, 0.1, "steel_dark", sides=10, loc=(0, 0, 0.7))
    mb.cyl(0.024, 1.0, "paint_yellow", sides=10, loc=(0, 0, 0.75))
    mb.cyl(0.018, 0.55, "aluminium", sides=10, loc=(0, 0, 1.72))
    mb.cyl(0.03, 0.04, "steel_dark", sides=10, loc=(0, 0, 1.72))
    mb.rod((0.03, 0, 1.4), (0.08, 0, 1.4), 0.01, "steel_dark", sides=6)
    mb.cyl(0.02, 0.03, "plastic_black", sides=8, loc=(0.09, 0, 1.4), rot=(0, 90, 0))
    top = Vector((0, 0, 2.27))
    mb.rod((-0.2, 0, 2.27), (0.2, 0, 2.27), 0.015, "steel_dark", sides=8)
    head_M = Matrix.Translation(top + Vector((0, 0, 0.0))) @ rotm((20, 0, 0))
    mb.box((0.36, 0.12, 0.26), "paint_black", center=True, Mx=head_M @ Matrix.Translation((0, -0.03, 0.0)), bevel=0.015, seg=2)
    for k in range(6):
        mb.box((0.33, 0.012, 0.006), "paint_black", center=True, Mx=head_M @ Matrix.Translation((0, 0.035, -0.09 + 0.036 * k)))
    for s in (-1, 1):
        mb.box((0.012, 0.06, 0.06), "steel_dark", center=True, Mx=Matrix.Translation(top + Vector((s * 0.19, 0, 0))), bevel=0.003, seg=1)
    mb.box((0.33, 0.012, 0.23), "steel_dark", center=True, Mx=head_M @ Matrix.Translation((0, -0.093, 0.0)))
    for k in range(4):
        mb.box((0.004, 0.006, 0.23), "steel_dark", center=True, Mx=head_M @ Matrix.Translation((-0.12 + 0.08 * k, -0.1, 0.0)))
    cab = [top + Vector((0.1, 0.06, -0.08)), top + Vector((0.06, 0.05, -0.3)), Vector((0.035, 0.03, 1.6)), Vector((0.035, 0.03, 0.85)),
           Vector((0.1, 0.1, 0.5)), Vector((0.25, 0.3, 0.02)), Vector((0.5, 0.6, 0.02))]
    mb.tube(cab, 0.007, "cable", sides=6)
    mb.label("kessler_logo", (0, 0, 0), 0.12, Mx=head_M @ Matrix.Translation((0, 0.0425, 0.1)) @ rotm((0, 0, 180)))
    root = mb.finish()
    bb = MB("bulb")
    bb.quad((0, 0, 0), 0.3, 0.2, "emit_warm", rect=(0.0, 0.0, 1.0, 1.0))
    bulb = bb.finish(grime=False, wn=False)
    p = head_M @ Vector((0, -0.088, 0.0))
    child(bulb, root, (p.x, p.y, p.z), rot=(20, 0, 0))
    return root


# ====================================================================== wheelbarrow
@node("wheelbarrow", "floor", grime=dict(dirt=0.35), notes="steel wheelbarrow, wheel toward +Z")
def wheelbarrow():
    mb = MB("wheelbarrow")
    # tray: tapered body from polys with a rolled rim
    zb, zt = 0.36, 0.62
    bot = [(-0.2, -0.3), (0.2, -0.3), (0.22, 0.22), (-0.22, 0.22)]
    top = [(-0.32, -0.52), (0.32, -0.52), (0.33, 0.34), (-0.33, 0.34)]
    B = [Vector((x, y, zb)) for x, y in bot]
    T = [Vector((x, y, zt)) for x, y in top]
    mb.poly(list(reversed(B)), "paint_green", thick=0.004)
    for i in range(4):
        j = (i + 1) % 4
        mb.poly([B[i], B[j], T[j], T[i]], "paint_green", thick=0.004)
    mb.tube(T, 0.012, "paint_green", sides=6, closed=True)
    # inner rust floor
    mb.poly([Vector((x * 0.95, y * 0.95, zb + 0.005)) for x, y in bot], "rust")
    # handles + legs
    for s in (-1, 1):
        h = [Vector((s * 0.12, -0.62, 0.2)), Vector((s * 0.17, -0.3, 0.34)), Vector((s * 0.25, 0.3, 0.38)), Vector((s * 0.28, 0.85, 0.5))]
        mb.tube(h, 0.016, "steel_dark", sides=8)
        mb.cyl(0.022, 0.14, "rubber", sides=8, Mx=trs(h[-1], (-76, 0, 0)))
        mb.tube([Vector((s * 0.22, 0.12, 0.37)), Vector((s * 0.24, 0.2, 0.15)), Vector((s * 0.25, 0.26, 0.0)), Vector((s * 0.25, 0.4, 0.0))],
                0.012, "steel_dark", sides=6)
    # wheel: tyre + rim + axle in the fork at the front
    wc = Vector((0, -0.68, 0.2))
    mb.lathe([(0.12, -0.04), (0.17, -0.045), (0.2, -0.03), (0.205, 0.0), (0.2, 0.03), (0.17, 0.045), (0.12, 0.04)], "rubber", sides=20,
             Mx=trs(wc, (0, 90, 0)), cap0=False)
    mb.lathe([(0.0, -0.05), (0.03, -0.05), (0.04, -0.02), (0.12, -0.035), (0.125, 0.0), (0.12, 0.035), (0.04, 0.02), (0.03, 0.05), (0.0, 0.05)],
             "steel", sides=16, Mx=trs(wc, (0, 90, 0)))
    mb.rod(wc + Vector((-0.12, 0, 0)), wc + Vector((0.12, 0, 0)), 0.01, "steel_dark", sides=6)
    return mb.finish()


# ====================================================================== helmet_rack
@node("helmet_rack", "wall", grime=WALLG, notes="timber rack with pegs, three hard hats and a cap lamp; origin = back "
                                                "centre, mount ~1.6 m")
def helmet_rack():
    mb = MB("helmet_rack")
    timber(mb, (-0.55, -0.025, 0.0), (0.55, -0.025, 0.0), 0.05, 0.16, up=(0, 0, 1), bevel=0.008, cuts=2)
    xs = (-0.38, -0.13, 0.13, 0.38)
    for x in xs:
        mb.rod((x, -0.05, 0.0), (x, -0.14, 0.03), 0.012, "wood_dark", sides=8)
    for x in (-0.48, 0.48):
        P.bolt(mb, (x, -0.0505, 0.0), (0, -1, 0), r=0.006, head=0.011, stud=0.0, washer=False)
    hats = (("helmet_yellow", "helmet_ml"), ("helmet_white", "helmet_cross"), ("helmet_yellow", "helmet_ml"))
    for (mat, st), x in zip(hats, xs[:3]):
        hard_hat(mb, (x, -0.11, -0.07), mat=mat, sticker_name=st, rot=(75, 0, 0))
    # cap lamp + battery hanging on the last peg
    mb.box((0.07, 0.035, 0.11), "plastic_black", loc=(xs[3], -0.1, -0.32), bevel=0.008, seg=2)
    mb.tube([Vector((xs[3], -0.12, 0.03)), Vector((xs[3] + 0.01, -0.13, -0.1)), Vector((xs[3], -0.12, -0.21))], 0.005, "cable", sides=5)
    mb.cyl(0.03, 0.04, "plastic_black", sides=12, loc=(xs[3], -0.14, 0.02), rot=(90, 0, 0))
    mb.cyl(0.022, 0.004, "glass", sides=12, loc=(xs[3], -0.18, 0.02), rot=(90, 0, 0))
    return mb.finish()


# ====================================================================== stretcher
@node("stretcher", "floor", notes="folding canvas rescue stretcher on its feet, head toward +Z")
def stretcher():
    mb = MB("stretcher")
    L = 2.1
    for s in (-1, 1):
        mb.rod((s * 0.28, -L / 2, 0.12), (s * 0.28, L / 2, 0.12), 0.016, "aluminium", sides=10)
        for y in (-L / 2 + 0.05, L / 2 - 0.05):
            mb.cyl(0.019, 0.12, "rubber", sides=10, Mx=trs((s * 0.28, y, 0.12), (90, 0, 0)) @ Matrix.Translation((0, 0, -0.06)))
        for y in (-0.62, 0.62):
            mb.tube([Vector((s * 0.28, y - 0.08, 0.12)), Vector((s * 0.28, y - 0.06, 0.02)), Vector((s * 0.28, y + 0.06, 0.02)),
                     Vector((s * 0.28, y + 0.08, 0.12))], 0.008, "aluminium", sides=6)
    for y in (-0.82, 0.82):
        mb.rod((-0.28, y, 0.11), (0.28, y, 0.11), 0.01, "aluminium", sides=6)

    tb = bmesh.new()
    nx, ny = 6, 10
    grid = []
    for j in range(ny + 1):
        y = -0.85 + 1.7 * j / ny
        row = []
        for i in range(nx + 1):
            x = -0.27 + 0.54 * i / nx
            z = 0.12 - 0.035 * (1 - (x / 0.27) ** 2) * math.sin(math.pi * j / ny) ** 0.5
            row.append(tb.verts.new((x, y, z)))
        grid.append(row)
    for j in range(ny):
        for i in range(nx):
            tb.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
    bmesh.ops.recalc_face_normals(tb, faces=tb.faces[:])
    tb.normal_update()
    mb.commit(tb, Matrix.Identity(4), "canvas", mk.uv_world_box)
    for y in (-0.3, 0.35):
        strap = [Vector((-0.3, y, 0.13)), Vector((-0.15, y, 0.1)), Vector((0.15, y, 0.1)), Vector((0.3, y, 0.13))]
        mb.sweep([(-0.001, -0.025), (0.004, -0.025), (0.004, 0.025), (-0.001, 0.025)], strap, "leather", up=(0, 1, 0))
        mb.box((0.04, 0.05, 0.008), "steel", loc=(0.2, y, 0.105), bevel=0.002, seg=1)
    mb.quad(None, 0.34, 0.077, "label_minekit", rect="rescue_label", Mx=trs((0, 0.68, 0.112), (-90, 0, 180)))
    return mb.finish()


# ====================================================================== water_tank
@node("water_tank", "floor", grime=dict(dirt=0.25), notes="galvanised drinking-water tank on a stand with a tap and cup "
                                                          "dispenser on +Z")
def water_tank():
    mb = MB("water_tank")
    R, z0, H = 0.36, 0.62, 0.86
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.boxc((sx * 0.26, sy * 0.26, z0 / 2), (0.05, 0.05, z0), "steel_dark", bevel=0.004, seg=1)
    for z in (0.15, z0 - 0.02):
        for s in (-1, 1):
            mb.boxc((0, s * 0.26, z), (0.57, 0.04, 0.04), "steel_dark", bevel=0.003, seg=1)
            mb.boxc((s * 0.26, 0, z), (0.04, 0.57, 0.04), "steel_dark", bevel=0.003, seg=1)
    mb.lathe([(0.0, z0), (R - 0.02, z0), (R, z0 + 0.02)] + [(R + (0.008 if k % 2 else 0.0), z0 + 0.02 + (H - 0.04) * k / 8) for k in range(1, 8)] +
             [(R, z0 + H - 0.02), (R - 0.02, z0 + H), (0.0, z0 + H)], "galvanized", sides=24)
    mb.cyl(R * 0.55, 0.04, "galvanized", sides=20, loc=(0, 0, z0 + H), bevel=0.006)
    mb.cyl(0.03, 0.03, "plastic_black", sides=10, loc=(0, 0, z0 + H + 0.04))
    # tap + drip tray + cups
    tz = z0 + 0.1
    mb.rod((0, -R + 0.01, tz), (0, -R - 0.06, tz), 0.014, "brass", sides=8)
    mb.rod((0, -R - 0.06, tz), (0, -R - 0.06, tz - 0.06), 0.011, "brass", sides=8)
    mb.box((0.012, 0.06, 0.012), "brass", loc=(0, -R - 0.04, tz + 0.012), rot=(0, 0, 0))
    mb.box((0.18, 0.14, 0.03), "steel", loc=(0, -R - 0.06, z0 - 0.17), bevel=0.003, seg=1)
    mb.cyl(0.04, 0.3, "plastic_black", sides=12, loc=(0.24, -R - 0.03, z0 + 0.25))
    mb.cyl(0.036, 0.06, "paint_white", sides=12, loc=(0.24, -R - 0.03, z0 + 0.19), r2=0.042)
    mb.clabel("water_label", Matrix.Identity(4), R + 0.0095, theta=0, w=0.34, z=z0 + 0.5, segs=8)
    return mb.finish()
