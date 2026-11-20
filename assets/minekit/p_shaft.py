"""Shaft set: elevator_cage, shaft_frame (+ shaft_frame_landing), call_panel. Front = -Y (three.js +Z)."""
import math

import bmesh
from mathutils import Matrix, Vector

import mk
import parts as P
from mk import DEG, MB, child, empty, rotm, trs
from parts import board, timber

BUILD = {}


def node(name, kind="floor", **meta):
    def deco(fn):
        BUILD[name] = (fn, dict(kind=kind, **meta))
        return fn
    return deco


CAGE_FLOOR = 0.18   # walking surface height above the cage origin
CAGE_HALF = 1.2
GATE_X0, GATE_X1 = -1.12, 0.0
GATE_TRAVEL = 1.12


def mesh_card(mb, mat, Mx, w, h, tile=(0.10, 0.05)):
    """Alpha-cut expanded-metal/mesh panel in local XZ (facing -Y), centred, UV in texture tiles."""
    faces = mb.grid(w, h, 1, 1, mat, Mx, uvoff=False)
    for f in faces:
        for lp in f.loops:
            u, v = lp[mb.uvl].uv
            lp[mb.uvl].uv = (u / tile[0], v / tile[1])
    return faces


def angle_post(mb, c, h, mat, size=0.06, t=0.008, rot=0.0):
    """Vertical steel angle (L) post resting on c."""
    prof = [(0, 0), (size, 0), (size, t), (t, t), (t, size), (0, size)]
    Mx = trs(c, (0, 0, rot))
    tb_faces = mb.extrude([(x - size / 2, z - size / 2) for x, z in prof], 0.0, h, mat,
                          Mx=Mx @ rotm((-90, 0, 0)) @ Matrix.Translation((0, 0, 0)))
    return tb_faces


# ====================================================================== elevator_cage
@node("elevator_cage", "floor", grime=dict(dirt=0.25),
      notes=f"origin = bottom of the underframe; walking surface (chequer plate) at y={CAGE_FLOOR}; gate on the +Z face "
            f"(door opening x {GATE_X0}..{GATE_X1}): child gate slides +{GATE_TRAVEL} m along local X to open; guide shoes at "
            "x=+-1.30 (shaft guides at +-1.32); child cage_light (emit_warm) under the roof")
def elevator_cage():
    mb = MB("elevator_cage")
    mk.custom_mat("custom_expanded_metal", "mesh_expanded.png", rough=0.5, metal=0.85)
    mk.custom_mat("custom_chequer_plate", "chequer.png", rough=0.45, metal=0.85, double=False, alpha_clip=False)
    H = CAGE_HALF
    top = 2.72
    # ---------------------------------------------------------------- underframe + floor
    for s in (-1, 1):
        mb.boxc((0, s * (H - 0.05), 0.08), (2 * H, 0.1, 0.16), "steel_dark", bevel=0.006)
        mb.boxc((s * (H - 0.05), 0, 0.08), (0.1, 2 * H - 0.2, 0.16), "steel_dark", bevel=0.006)
    for x in (-0.4, 0.4):
        mb.boxc((x, 0, 0.08), (0.08, 2 * H - 0.2, 0.14), "steel_dark", bevel=0.005)
    fl = mb.box((2 * H - 0.02, 2 * H - 0.02, 0.02), "custom_chequer_plate", loc=(0, 0, 0.16), bevel=0.003, seg=1, uvoff=False)
    for f in fl:
        for lp in f.loops:
            u, v = lp[mb.uvl].uv
            lp[mb.uvl].uv = (u * 10.0, v * 10.0)
    # ---------------------------------------------------------------- frame: corner posts, mid rails, kick plates
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.boxc((sx * (H - 0.03), sy * (H - 0.03), (CAGE_FLOOR + top) / 2), (0.06, 0.06, top - CAGE_FLOOR), "paint_yellow",
                    bevel=0.006, seg=2)
    # door posts on the front
    for x in (GATE_X0 - 0.04, GATE_X1 + 0.02):
        mb.boxc((x, -H + 0.03, (CAGE_FLOOR + top) / 2), (0.05, 0.06, top - CAGE_FLOOR), "paint_yellow", bevel=0.006, seg=2)
    walls = [((0, H - 0.03), 2 * H - 0.12, 180), ((-H + 0.03, 0), 2 * H - 0.12, 90), ((H - 0.03, 0), 2 * H - 0.12, -90)]
    for (cx, cy), w, ang in walls:
        for z in (1.1, 2.2, top - 0.03):
            mb.box((w, 0.05, 0.05), "paint_yellow", center=True, Mx=trs((cx, cy, z), (0, 0, ang)), bevel=0.005, seg=1)
        mb.box((w, 0.006, 0.22), "steel_dark", center=True, Mx=trs((cx, cy, CAGE_FLOOR + 0.11), (0, 0, ang)), bevel=0.002, seg=1)
        mesh_card(mb, "custom_expanded_metal", trs((cx, cy, (CAGE_FLOOR + 0.22 + top - 0.06) / 2), (0, 0, ang)), w,
                  top - 0.06 - CAGE_FLOOR - 0.22)
    # fixed front panel right of the door
    fw = H - 0.03 - (GATE_X1 + 0.045)
    fcx = (GATE_X1 + 0.045 + H - 0.03) / 2
    for z in (1.1, 2.2, top - 0.03):
        mb.boxc((fcx, -H + 0.03, z), (fw, 0.05, 0.05), "paint_yellow", bevel=0.005, seg=1)
    mb.boxc((fcx, -H + 0.03, CAGE_FLOOR + 0.11), (fw, 0.006, 0.22), "steel_dark", bevel=0.002, seg=1)
    mesh_card(mb, "custom_expanded_metal", trs((fcx, -H + 0.03, (CAGE_FLOOR + 0.22 + top - 0.06) / 2)), fw,
              top - 0.06 - CAGE_FLOOR - 0.22)
    # header over the door + gate tracks (top and bottom) running the full front
    mb.boxc(((GATE_X0 + GATE_X1) / 2, -H + 0.03, 2.25), (GATE_X1 - GATE_X0 + 0.08, 0.06, 0.1), "paint_yellow", bevel=0.006)
    for z in (CAGE_FLOOR + 0.01, 2.17):
        mb.boxc((0, -H - 0.06, z), (2 * H + 0.04, 0.04, 0.03), "steel_dark", bevel=0.004)
        for x in (-H + 0.05, 0.0, H - 0.05):
            mb.boxc((x, -H - 0.025, z), (0.04, 0.05, 0.03), "steel_dark", bevel=0.003)
    # ---------------------------------------------------------------- roof + bonnet + bridle
    mb.box((2 * H + 0.04, 2 * H + 0.04, 0.03), "steel_dark", loc=(0, 0, top), bevel=0.005, seg=1)
    # bonnet: shallow gable of plate on a ridge beam
    ridge = top + 0.22
    for s in (-1, 1):
        quad = [Vector((-H - 0.06, 0, ridge)), Vector((H + 0.06, 0, ridge)), Vector((H + 0.06, s * (H + 0.08), top + 0.05)),
                Vector((-H - 0.06, s * (H + 0.08), top + 0.05))]
        if s < 0:
            quad = list(reversed(quad))
        mb.poly(quad, "steel_dark", thick=0.008)
    mb.boxc((0, 0, ridge - 0.04), (2 * H + 0.12, 0.08, 0.08), "steel_dark", bevel=0.005)
    # crosshead/sling: drawbar to the rope socket
    mb.boxc((0, 0, ridge + 0.06), (0.5, 0.14, 0.12), "steel_dark", bevel=0.01, seg=2)
    for sx in (-1, 1):
        for sy in (-1, 1):
            P.chain(mb, (sx * 0.2, sy * 0.05, ridge + 0.04), (sx * 0.32, sy * 0.42, top + 0.12), link_len=0.07, wire=0.009,
                    mat="steel_dark", sides=5, segs=8)
    mb.rod((0, 0, ridge + 0.12), (0, 0, 3.0), 0.035, "steel", sides=10)
    P.ring(mb, (0, 0, 3.0 - 0.035), 0.05, 0.016, axis=(1, 0, 0), mat="steel", segs=12)
    # ---------------------------------------------------------------- guide shoes (both sides, top and bottom)
    for s in (-1, 1):
        for z in (0.32, 2.55):
            mb.boxc((s * (H + 0.04), 0, z), (0.08, 0.26, 0.22), "steel_dark", bevel=0.01, seg=2)
            for sy in (-1, 1):
                mb.boxc((s * (H + 0.095), sy * 0.075, z), (0.07, 0.03, 0.2), "steel_dark", bevel=0.006, seg=1)
            mb.boxc((s * (H + 0.1), 0, z), (0.04, 0.12, 0.2), "rubber", bevel=0.004)
    # ---------------------------------------------------------------- inside: handrails, bell, plates, light base
    for s in (-1, 1):
        mb.rod((s * (H - 0.09), -0.8, 1.05), (s * (H - 0.09), 0.8, 1.05), 0.018, "steel", sides=8)
        for y in (-0.8, 0.8):
            mb.rod((s * (H - 0.09), y, 1.05), (s * (H - 0.03), y, 1.05), 0.014, "steel", sides=8)
    bx, by, bz = -0.75, H - 0.08, 2.4
    mb.boxc((bx, by + 0.02, bz), (0.12, 0.05, 0.16), "paint_red", bevel=0.008)
    mb.lathe([(0.0, 0.0), (0.03, -0.004), (0.065, -0.03), (0.078, -0.07), (0.082, -0.075), (0.0, -0.075)], "brass", sides=16,
             Mx=trs((bx + 0.15, by - 0.0, bz + 0.04), (-90, 0, 0)))
    mb.rod((bx + 0.15, by, bz + 0.04), (bx + 0.15, by + 0.06, bz + 0.04), 0.01, "steel_dark", sides=6)
    mb.tube([Vector((bx, by - 0.01, bz - 0.08)), Vector((bx + 0.01, by - 0.05, bz - 0.5)), Vector((bx + 0.005, by - 0.04, 1.35))],
            0.006, "canvas", sides=5)
    mb.cyl(0.02, 0.06, "wood_dark", sides=8, loc=(bx + 0.005, by - 0.04, 1.29))
    mb.label("bell_code", (0.35, H - 0.07, 1.65), 0.3, rot=(0, 0, 180))
    mb.boxc((0.35, H - 0.062, 1.65), (0.31, 0.006, 0.405), "steel_dark")
    mb.label("cage_plate", (-0.25, H - 0.07, 1.65), 0.3, rot=(0, 0, 180))
    mb.boxc((-0.25, H - 0.062, 1.65), (0.31, 0.006, 0.155), "steel_dark")
    lx, ly, lz = 0.0, 0.35, top
    mb.cyl(0.11, 0.035, "cast_iron", sides=16, loc=(lx, ly, lz - 0.035), bevel=0.006)
    for k in range(4):
        a = k / 4 * 2 * math.pi
        mb.tube([Vector((lx + math.cos(a) * 0.1, ly + math.sin(a) * 0.06, lz - 0.035)),
                 Vector((lx + math.cos(a) * 0.1, ly + math.sin(a) * 0.065, lz - 0.08)),
                 Vector((lx + math.cos(a) * 0.04, ly + math.sin(a) * 0.03, lz - 0.115))], 0.006, "cast_iron", sides=5)
    root = mb.finish()
    # cage light lens
    lb = MB("cage_light")
    lb.lathe([(0.0, 0.0), (0.085, 0.0), (0.08, -0.03), (0.055, -0.06), (0.0, -0.072)], "emit_warm", sides=16)
    lens = lb.finish(grime=False)
    lens.scale = (1.0, 0.65, 1.0)
    child(lens, root, (lx, ly, lz - 0.035))
    # gate: framed expanded-metal panel on rollers, closed position over the door opening
    gb = MB("gate")
    gw, gh = GATE_X1 - GATE_X0 + 0.06, 2.0
    for (cx, cz, w, h) in ((0, 0.02, gw, 0.04), (0, gh - 0.02, gw, 0.04), (-gw / 2 + 0.02, gh / 2, 0.04, gh),
                           (gw / 2 - 0.02, gh / 2, 0.04, gh), (0, gh * 0.5, gw, 0.035)):
        gb.boxc((cx, 0, cz), (w, 0.035, h), "paint_yellow", bevel=0.005, seg=1)
    mesh_card(gb, "custom_expanded_metal", Matrix.Translation((0, 0, gh / 2)), gw - 0.06, gh - 0.06)
    P.handle_bar(gb, Vector((gw / 2 - 0.08, -0.018, gh * 0.5 - 0.15)), Vector((gw / 2 - 0.08, -0.018, gh * 0.5 + 0.15)),
                 (0, -1, 0), stand=0.04, r=0.012, mat="steel")
    for x in (-gw / 2 + 0.15, gw / 2 - 0.15):
        gb.cyl(0.025, 0.02, "steel_dark", sides=10, Mx=trs((x, 0.0, gh + 0.0), (90, 0, 0)))
        gb.rod((x, 0, gh - 0.02), (x, 0, gh + 0.0), 0.008, "steel_dark", sides=6)
    gb.label("chevron", (0, -0.019, 0.1), gw - 0.1, 0.07)
    gate = gb.finish()
    child(gate, root, ((GATE_X0 + GATE_X1) / 2, -H - 0.1, CAGE_FLOOR + 0.03))
    return root


# ====================================================================== shaft_frame (+ landing variant)
def _shaft(name, landing=False):
    mb = MB(name)
    rng = mb.rng
    c = 1.525          # set centre lines
    t = 0.25
    SEG = 4.0
    for zs in (0.0, 2.0):
        for s in (-1, 1):
            # end plates (along Y) on the guide sides, wall plates (along X) front/back
            timber(mb, (s * c, -c - t / 2, zs + t / 2), (s * c, c + t / 2, zs + t / 2), t, t, up=(0, 0, 1), bevel=0.018,
                   cuts=4, bow=0.003, ends=0.01)
            if landing and s < 0 and zs == 2.0:
                timber(mb, (-c - t / 2, -c, 2.62 + t / 2), (c + t / 2, -c, 2.62 + t / 2), t, t, up=(0, 0, 1), bevel=0.018,
                       cuts=4, bow=0.003, ends=0.01)
                continue
            if landing and s < 0 and zs == 0.0:
                # sill timber stays (it is the landing edge)
                pass
            timber(mb, (-c - t / 2, s * c, zs + t / 2 + 0.002), (c + t / 2, s * c, zs + t / 2 + 0.002), t, t, up=(0, 0, 1),
                   bevel=0.018, cuts=4, bow=0.003, ends=0.01)
    # studdles (corner posts) between the sets
    for sx in (-1, 1):
        for sy in (-1, 1):
            for z0, z1 in ((t, 2.0), (2.0 + t, SEG)):
                timber(mb, (sx * c, sy * c, z0), (sx * c, sy * c, z1 + 0.004), 0.2, 0.2, up=(0, 1, 0), bevel=0.014, cuts=2,
                       bow=0.002, ends=0.006)
    # guides: steel top-hat sections on the end plates (cage shoes run on them)
    for s in (-1, 1):
        gx = s * (c - t / 2 - 0.04)
        mb.boxc((gx, 0, SEG / 2), (0.08, 0.13, SEG), "steel_dark", bevel=0.006, seg=1)
        mb.boxc((gx - s * 0.045, 0, SEG / 2), (0.012, 0.09, SEG), "steel", bevel=0.002, seg=1)
        for zs in (0.0, 2.0):
            for dy in (-0.045, 0.045):
                P.bolt(mb, (gx - s * 0.052, dy, zs + t / 2), (-s, 0, 0), r=0.008, head=0.014, stud=0.0, washer=False)
    # lagging: vertical boards behind the sets on all four sides (gaps show the rock)
    for side in range(4):
        if landing and side == 0:
            continue
        ang = (0, 90, 180, 270)[side] * DEG
        nrm = Vector((math.sin(ang), -math.cos(ang), 0))
        along = Vector((math.cos(ang), math.sin(ang), 0))
        off = c + t / 2 + 0.022
        u = -1.62
        while u < 1.6:
            w = rng.uniform(0.17, 0.24)
            if rng.random() > 0.08:
                p = nrm * off + along * (u + w / 2)
                board(mb, (p.x, p.y, 0.0 + rng.uniform(0, 0.01)), (p.x, p.y, SEG - rng.uniform(0, 0.01)), w - 0.006, 0.04,
                      "wood_planks", up=(nrm.x, nrm.y, 0), bevel=0.005)
            u += w + rng.uniform(0.006, 0.03)
    # services in the back-right corner: water column + power cable on cleats
    px, py = 1.18, 1.28
    mb.rod((px, py, 0.0), (px, py, SEG), 0.055, "galvanized", sides=12, cap=False)
    mb.rod((px, py, 0.05), (px, py, 0.13), 0.085, "galvanized", sides=12, bevel=0.006)
    for zs in (1.0, 3.0):
        P.ring(mb, (px, py, zs), 0.062, 0.008, mat="steel_dark", segs=12)
        mb.boxc((px, py + 0.1, zs), (0.05, 0.14, 0.03), "steel_dark", bevel=0.003)
    cx_, cy_ = 0.85, 1.36
    mb.rod((cx_, cy_, 0.0), (cx_, cy_, SEG), 0.026, "cable", sides=10, cap=False)
    mb.rod((cx_ + 0.07, cy_ + 0.01, 0.0), (cx_ + 0.07, cy_ + 0.01, SEG), 0.008, "hose_red", sides=6, cap=False)
    for zs in (0.6, 1.6, 2.6, 3.6):
        mb.boxc((cx_ + 0.03, cy_ + 0.02, zs), (0.16, 0.05, 0.05), "wood_dark", bevel=0.005, seg=1)
    # one bulkhead lamp per segment on the back wall (passes by as the cage rides)
    lx, ly, lz = -0.6, c - t / 2 - 0.01, 3.1
    mb.boxc((lx, ly - 0.03, lz), (0.22, 0.06, 0.13), "cast_iron", bevel=0.01, seg=2)
    mb.boxc((lx, ly - 0.065, lz), (0.17, 0.02, 0.085), "emit_warm", bevel=0.008, seg=2)
    for k in range(3):
        mb.boxc((lx - 0.06 + 0.06 * k, ly - 0.08, lz), (0.008, 0.012, 0.1), "cast_iron")
    return mb.finish()


@node("shaft_frame", "floor", notes="3.4 x 3.4 x 4 m timber shaft lining, stack every 4 m (sets at y=0 and 2); guides "
                                     "(steel) on the +-X sides with running faces at x=+-1.32; lagged on all four sides")
def shaft_frame():
    return _shaft("shaft_frame")


@node("shaft_frame_landing", "floor", notes="EXTRA (not in contract): shaft_frame with the +Z (landing) side open and "
                                             "the upper +Z wall plate raised to 2.62-2.87 m so a cage door fits")
def shaft_frame_landing():
    return _shaft("shaft_frame_landing", landing=True)


# ====================================================================== call_panel (wall: origin back-centre)
@node("call_panel", "wall", grime=dict(floor=False),
      notes="wall box, origin = back centre at the wall, faces +Z; children btn_1..btn_4 (push along local -Z to press; swap "
            "their material to emit_green/emit_red for lit states) and panel_screen (emit_screen, UV 0-1 glTF convention)")
def call_panel():
    mb = MB("call_panel")
    W, D, H = 0.34, 0.12, 0.52
    # enclosure + door + drip hood
    mb.box((W, D, H), "paint_yellow", loc=(0, -D / 2, -H / 2), center=False, bevel=0.008, seg=2)
    mb.box((W - 0.03, 0.012, H - 0.03), "paint_yellow", loc=(0, -D - 0.006, -H / 2 + 0.015 + (H - 0.03) / 2 - (H - 0.03) / 2),
           center=False, bevel=0.005, seg=2)
    hood = [Vector((-W / 2 - 0.02, 0.0, H / 2 + 0.06)), Vector((W / 2 + 0.02, 0.0, H / 2 + 0.06)),
            Vector((W / 2 + 0.02, -D - 0.06, H / 2 + 0.005)), Vector((-W / 2 - 0.02, -D - 0.06, H / 2 + 0.005))]
    mb.poly(list(reversed(hood)), "paint_yellow", thick=0.006)
    for s in (-1, 1):
        mb.poly([Vector((s * (W / 2 + 0.02), 0.0, H / 2 + 0.06)), Vector((s * (W / 2 + 0.02), -D - 0.06, H / 2 + 0.005)),
                 Vector((s * (W / 2 + 0.02), 0.0, H / 2 - 0.02))][::(1 if s > 0 else -1)], "paint_yellow", thick=0.004)
    for sx in (-1, 1):
        for sz in (-1, 1):
            mb.cyl(0.009, 0.008, "steel", sides=8, loc=(sx * (W / 2 - 0.03), -D - 0.012, sz * (H / 2 - 0.03)), rot=(90, 0, 0))
    for sz in (-0.15, 0.15):
        mb.rod((-W / 2 - 0.006, -D + 0.01, sz - 0.04), (-W / 2 - 0.006, -D + 0.01, sz + 0.04), 0.009, "steel_dark", sides=6)
    fy = -D - 0.012
    mb.label("call_title", (0, fy - 0.0015, H / 2 - 0.055), 0.2)
    # display
    mb.boxc((0, fy - 0.006, 0.12), (0.2, 0.012, 0.1), "plastic_black", bevel=0.004)
    mb.boxc((0, fy - 0.0125, 0.12), (0.17, 0.002, 0.072), "glass_dark")
    # button rows: plate label + guard ring (buttons are children)
    rows = [0.03, -0.055, -0.14, -0.225]
    for i, z in enumerate(rows):
        mb.label(f"btn_{i + 1}", (-0.065, fy - 0.0015, z), 0.15)
        mb.lathe([(0.03, 0.0), (0.036, 0.0), (0.038, 0.012), (0.034, 0.016), (0.03, 0.016)], "plastic_black", sides=16,
                 Mx=trs((0.1, fy, z), (90, 0, 0)))
    # conduit + gland at the bottom
    mb.cyl(0.018, 0.03, "plastic_black", sides=10, loc=(0.08, -D / 2, -H / 2 - 0.03))
    mb.tube([Vector((0.08, -D / 2, -H / 2 - 0.03)), Vector((0.08, -D / 2, -H / 2 - 0.12)), Vector((0.08, -0.03, -H / 2 - 0.2)),
             Vector((0.08, -0.02, -H / 2 - 0.6))], 0.011, "cable", sides=8)
    root = mb.finish()
    for i, z in enumerate(rows):
        bb = MB(f"btn_{i + 1}")
        bb.lathe([(0.0, 0.0), (0.027, 0.0), (0.027, 0.012), (0.025, 0.018), (0.016, 0.022), (0.0, 0.023)], "paint_green",
                 sides=16, Mx=rotm((90, 0, 0)))
        b = bb.finish(grime=False)
        child(b, root, (0.1, fy - 0.002, z))
    sb = MB("panel_screen")
    sb.quad((0, 0, 0), 0.16, 0.064, "emit_screen", rect=(0.0, 0.0, 1.0, 1.0))
    scr = sb.finish(grime=False, wn=False)
    child(scr, root, (0, fy - 0.0136, 0.12))
    return root
