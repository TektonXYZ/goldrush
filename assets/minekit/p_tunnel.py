"""Tunnel pieces: timber_set, steel_arch, rail_2m, rail_bumper, cable_2m, vent_duct_2m, pipe_2m, bolt_plate,
mesh_panel. Drift frame: x across (centre 0), floor z = 0, tunnel runs along Blender Y (three.js Z);
front = -Y (three.js +Z)."""
import math

import bmesh
from mathutils import Matrix, Vector, noise

import mk
from mk import MB, DEG, child, empty, frame, rotm, trs
from parts import (DRIFT_H, DRIFT_SPRING, DRIFT_W, board, bolt, chain, drift_roof, hexnut, j_hook, rivet,
                   staple, timber, wedge)

BUILD = {}


def node(name, kind="tunnel", **meta):
    def deco(fn):
        BUILD[name] = (fn, dict(kind=kind, **meta))
        return fn
    return deco


# ====================================================================== timber_set
@node("timber_set", "tunnel")
def timber_set():
    mb = MB("timber_set")
    rng = mb.rng
    cap_bot, cap_h, cap_w = 2.80, 0.30, 0.28
    post = 0.25
    # footblocks + battered posts (feet wider than the tops, as real sets are stood)
    for s in (-1, 1):
        fx = s * 1.97
        mb.box((0.42, 0.34, 0.055), "wood_planks", loc=(fx + s * 0.02, rng.uniform(-0.02, 0.02), 0),
               rot=(0, 0, rng.uniform(-6, 6)), bevel=0.006, seg=1)
        timber(mb, (fx, 0, 0.05), (s * 1.895, 0, cap_bot + 0.035), post, post, up=(0, 1, 0), bevel=0.018,
               cuts=5, bow=0.004, twist=2.0, ends=0.012)
    # cap beam (ends hitched into the rock)
    timber(mb, (-2.07, 0, cap_bot + cap_h / 2), (2.07, 0, cap_bot + cap_h / 2), cap_w, cap_h, up=(0, 0, 1),
           bevel=0.02, cuts=6, bow=0.003, twist=1.0, ends=0.015)
    top = cap_bot + cap_h
    # roof lagging: boards from this cap to the next set (sets every 1.5 m toward three.js +Z = Blender -Y)
    x = -1.87
    k = 0
    while x < 1.85:
        w = rng.uniform(0.15, 0.24)
        if x + w > 1.88:
            w = 1.88 - x
        if w > 0.08 and not (k == 6):
            th = rng.uniform(0.04, 0.052)
            y0 = rng.uniform(-0.005, 0.0)
            y1 = -1.5 + rng.uniform(-0.01, 0.008)
            board(mb, (x + w / 2, y0, top), (x + w / 2, y1, top), w - 0.004, th, "wood_planks", up=(0, 0, 1),
                  bevel=0.006)
        x += w + rng.uniform(0.012, 0.045)
        k += 1
    # side lagging behind the posts at the top of each rib
    for s in (-1, 1):
        for z in (2.30, 2.56):
            xb = s * (1.895 + post / 2 + 0.03 + (z - 2.3) * 0.0)
            board(mb, (xb, 0.0, z), (xb, -1.5 + rng.uniform(-0.01, 0.01), z), 0.045, 0.22, "wood_planks",
                  up=(0, 0, 1), bevel=0.005)
    # spreaders (collar braces) to the next set, just under the cap, and a lower one
    for s in (-1, 1):
        for z in (cap_bot - 0.12, 1.25):
            xs = s * (1.905 if z > 2 else 1.94)
            timber(mb, (xs, -0.125, z), (xs, -1.375, z), 0.12, 0.14, up=(0, 0, 1), bevel=0.01, cuts=2,
                   bow=0.004, twist=2.0, ends=0.008)
    # wedges driven into the post/cap joints and on top of the cap ends
    for s in (-1, 1):
        px = s * 1.895
        for yy in (-0.07, 0.07):
            wedge(mb, (px - s * (post / 2 + 0.035), yy, cap_bot - 0.004), 0.16, 0.07, 0.03,
                  rot=(180, 0, 180 if s > 0 else 0))
        wedge(mb, (s * 1.80, -0.02, top), 0.22, 0.09, 0.05, rot=(0, 0, 90 if s > 0 else -90))
    # timber dogs across each joint, front and back
    for s in (-1, 1):
        px = s * 1.895
        for yf in (-1, 1):
            staple(mb, (px + s * 0.03, yf * (post / 2 + 0.002), cap_bot - 0.16),
                   (px + s * 0.03, yf * (cap_w / 2 + 0.002), cap_bot + 0.12), (0, yf, 0), r=0.009)
    return mb.finish()


# ====================================================================== rail_2m
RAIL_TOP = 0.200
GAUGE = 0.60
RAIL_H = 0.069


def rail_profile():
    """Flat-bottom rail (~15 kg/m), centred on x = 0, base at z = 0, top at RAIL_H. CCW from the base."""
    h = RAIL_H
    pts = [(-0.0325, 0.0), (0.0325, 0.0), (0.0325, 0.006), (0.013, 0.0125), (0.0048, 0.019), (0.0048, 0.047),
           (0.0165, 0.0535), (0.0172, 0.0655), (0.0125, h), (-0.0125, h), (-0.0172, 0.0655), (-0.0165, 0.0535),
           (-0.0048, 0.047), (-0.0048, 0.019), (-0.013, 0.0125), (-0.0325, 0.006)]
    mats = []
    for k in range(len(pts)):
        a, b = pts[k], pts[(k + 1) % len(pts)]
        top = min(a[1], b[1]) > 0.064
        mats.append("steel" if top else "rust")
    return pts, mats


@node("rail_2m", "tunnel")
def rail_2m():
    mb = MB("rail_2m")
    rng = mb.rng
    sl_bot, sl_h = 0.035, 0.092
    plate_t = 0.006
    base_z = sl_bot + sl_h + plate_t
    rail_x = GAUGE / 2 + 0.0125  # gauge measured between the inner faces of the heads
    prof, pm = rail_profile()
    s_scale = (RAIL_TOP - base_z) / RAIL_H
    prof = [(x, z * s_scale) for x, z in prof]
    for s in (-1, 1):
        mb.extrude([(x + s * rail_x, z + base_z) for x, z in prof], -1.0, 1.0, pm)
    for i, y in enumerate((-2 / 3, 0.0, 2 / 3)):
        dy = rng.uniform(-0.012, 0.012)
        rz = rng.uniform(-1.8, 1.8)
        dx = rng.uniform(-0.02, 0.02)
        Ms = trs((dx, y + dy, 0), (0, 0, rz))
        L = rng.uniform(1.02, 1.08)
        timber(mb, Ms @ Vector((-L / 2, 0, sl_bot + sl_h / 2)), Ms @ Vector((L / 2, 0, sl_bot + sl_h / 2)), 0.145,
               sl_h, up=(0, 0, 1), bevel=0.012, cuts=2, bow=0.003, twist=1.5, ends=0.01)
        for s in (-1, 1):
            c = Vector((s * rail_x, y + dy * 0.5, sl_bot + sl_h))
            mb.box((0.18, 0.125, plate_t), "steel_dark", loc=c, rot=(0, 0, rz * 0.4), bevel=0.0015, seg=1)
            # dog spikes on both sides of the rail foot, staggered
            for side, off in ((-1, -0.03), (1, 0.03)):
                sx = c.x + side * 0.042
                sy = c.y + off
                mb.box((0.026, 0.017, 0.012), "steel_dark", loc=(sx, sy, base_z), bevel=0.002, seg=1)
                mb.box((0.015, 0.016, 0.01), "steel_dark", loc=(sx - side * 0.013, sy, base_z + 0.004), bevel=0.0015,
                       seg=1)
    root = mb.finish()
    # ballast bed (separate child so the game can drop it on concrete floors)
    bb = MB("ballast", seed=3)
    W, nx, ny = 1.5, 14, 12

    def h(x, y):
        t = abs(x) / (W / 2)
        crown = 0.075 * (1 - t ** 2.2)
        ang = y / 2.0 * 2 * math.pi
        n = noise.noise(Vector((x * 3.1, math.cos(ang) * 1.6, math.sin(ang) * 1.6)))
        return max(0.0, crown + 0.018 * n * (1 - t ** 4))
    tb = bmesh.new()
    uvl = tb.loops.layers.uv.new("uv")
    grid = []
    for j in range(ny + 1):
        y = -1.0 + 2.0 * j / ny
        row = []
        for i in range(nx + 1):
            x = -W / 2 + W * i / nx
            row.append(tb.verts.new((x, y, h(x, y))))
        grid.append(row)
    for j in range(ny):
        for i in range(nx):
            f = tb.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
            for lp in f.loops:
                lp[uvl].uv = (lp.vert.co.x, lp.vert.co.y)
    tb.normal_update()
    bb.commit(tb, Matrix.Identity(4), "gravel", None, uvoff=False)
    for k in range(22):
        x = rng.choice((-1, 1)) * rng.uniform(0.38, 0.66)
        y = rng.uniform(-0.95, 0.95)
        sz = rng.uniform(0.025, 0.055)
        bb.rock((x, y, h(x, y) + sz * 0.15), (sz, sz * rng.uniform(0.7, 1.2), sz * 0.6), "gravel", seed=k + 11,
                detail=0)
    ballast = bb.finish()
    child(ballast, root)
    return root


# ====================================================================== steel_arch
@node("steel_arch", "tunnel")
def steel_arch():
    """Horseshoe arch of rolled I-beam (TH-style) in three segments with fish-plate joints."""
    mb = MB("steel_arch")
    rng = mb.rng
    fl, dp, web, tf = 0.11, 0.13, 0.009, 0.012  # flange width (along tunnel), depth (radial), web, flange thk

    # centreline: legs up to the springline, then an arch to the crown (stays inside the drift profile)
    cx_leg = 2.03
    spring = 2.35
    crown = 3.62
    pts = []
    for k in range(5):
        pts.append(Vector((-cx_leg + 0.03 * k / 4, 0, 0.012 + (spring - 0.012) * k / 4)))
    a, b = cx_leg - 0.03, crown - spring
    for k in range(1, 24):
        t = math.pi - math.pi * k / 24
        pts.append(Vector((a * math.cos(t), 0, spring + b * math.sin(t))))
    for k in range(5):
        pts.append(Vector((cx_leg - 0.03 + 0.03 * k / 4, 0, spring - (spring - 0.012) * k / 4)))
    # I-section: profile local x -> path normal (in XZ plane, radial), local y -> along tunnel (Y)
    hw, hd = fl / 2, dp / 2
    prof = [(-hd, -hw), (-hd + tf, -hw), (-hd + tf, -web / 2), (hd - tf, -web / 2), (hd - tf, -hw), (hd, -hw),
            (hd, hw), (hd - tf, hw), (hd - tf, web / 2), (-hd + tf, web / 2), (-hd + tf, hw), (-hd, hw)]
    # sweep() maps profile x to (tangent x up) and y to up-ish; use up = +Y so profile y runs along the tunnel
    n = len(pts)
    seg_bounds = [0, 11, n - 12, n - 1]  # leg+shoulder / crown / shoulder+leg
    for si in range(3):
        i0, i1 = seg_bounds[si], seg_bounds[si + 1]
        part = pts[max(0, i0 - (0 if si == 0 else 0)):i1 + 1]
        # shorten at joints so the fish plates cover a small gap
        mb.sweep(prof, part, "steel_dark", up=(0, 1, 0))
    # fish-plate joints with 4 bolts each
    for ji in (seg_bounds[1], seg_bounds[2]):
        p = pts[ji]
        t = (pts[ji + 1] - pts[ji - 1]).normalized()
        nrm = Vector((0, 1, 0)).cross(t).normalized()  # radial-ish in XZ
        for side in (-1, 1):
            c = p + Vector((0, side * (web / 2 + 0.006), 0))
            Mx = Matrix.Translation(c) @ frame(t, Vector((0, side, 0)))
            mb.box((0.40, dp - 2 * tf - 0.012, 0.012), "steel_dark", center=True, Mx=Mx, bevel=0.003, seg=1)
            for u in (-0.14, -0.05, 0.05, 0.14):
                for v in (-0.022, 0.022):
                    bp = c + t * u + nrm * v + Vector((0, side * 0.006, 0))
                    bolt(mb, bp, (0, side, 0), r=0.007, head=0.011, stud=0.014 if side > 0 else 0.0, washer=False)
    # foot plates
    for s in (-1, 1):
        mb.box((0.26, 0.22, 0.014), "steel_dark", loc=(s * cx_leg, 0, 0), bevel=0.003, seg=1)
        for dx in (-0.08, 0.08):
            bolt(mb, (s * cx_leg + dx, 0.07 * (1 if dx > 0 else -1), 0.014), (0, 0, 1), r=0.009, head=0.014, stud=0.0)
    # timber blocking/wedges between arch and rock at crown and shoulders
    for ang in (90, 52, 128):
        t = ang * DEG
        p = Vector((a * math.cos(t), 0, spring + b * math.sin(t)))
        nr = Vector((math.cos(t) * b, 0, math.sin(t) * a)).normalized()
        c = p + nr * (hd + 0.045)
        Mx = Matrix.Translation(c) @ frame(Vector((0, 1, 0)), nr)
        mb.box((0.36, 0.2, 0.08), "wood_timber", center=True, Mx=Mx, bevel=0.008, seg=1)
        mb.box((0.26, 0.09, 0.05), "wood_timber", center=True, Mx=Mx @ Matrix.Translation((0.04, 0, 0.065)) @ rotm((0, 4, 0)),
               bevel=0.004, seg=1)
    return mb.finish()


# ====================================================================== lantern (origin = hang point at the top)
@node("lantern", "hang", notes="origin = screw-eye hang point (top); hang it under a cap beam")
def lantern():
    mb = MB("lantern")
    import parts as P
    # screw eye into the timber above + chain + S-hook
    mb.rod((0, 0, 0.035), (0, 0, -0.004), 0.0045, "galvanized", sides=6)
    P.ring(mb, (0, 0, -0.024), 0.017, 0.0048, axis=(0, 1, 0), mat="galvanized", segs=12)
    P.chain(mb, (0, 0, -0.036), (0, 0, -0.205), link_len=0.046, wire=0.0042, mat="steel_dark", segs=8, sides=5)
    low = P.s_hook(mb, (0, 0, -0.205), r=0.017, wire=0.0042, mat="steel_dark", side=(0, 1, 0))
    ztop = low.z - 0.082  # bail radius
    # wire bail
    bail = [Vector((0.082 * math.cos(t), 0, ztop + 0.082 * math.sin(t))) for t in [math.pi * k / 14 for k in range(15)]]
    mb.tube(bail, 0.0035, "galvanized", sides=6)
    for s in (-1, 1):
        mb.cyl(0.008, 0.012, "brass", sides=8, Mx=trs((s * 0.082, 0, ztop - 0.012), (0, 90, 0)) @ Matrix.Translation((0, 0, -0.006)))
    # top cap (dark green enamel) with vent collar
    zc = ztop - 0.02
    mb.lathe([(0.0, zc + 0.03), (0.018, zc + 0.03), (0.022, zc + 0.022), (0.03, zc + 0.012), (0.034, zc), (0.074, zc - 0.032),
              (0.086, zc - 0.045), (0.088, zc - 0.056), (0.072, zc - 0.058)], "paint_green", sides=16)
    mb.lathe([(0.072, zc - 0.058), (0.072, zc - 0.07), (0.064, zc - 0.07)], "brass", sides=16)
    # glass globe (fresnel-ish bulge) + wire guard
    g0, g1 = zc - 0.07, zc - 0.215
    prof = []
    for k in range(9):
        t = k / 8
        prof.append((0.052 + 0.016 * math.sin(t * math.pi), g0 - (g0 - g1) * t))
    mb.lathe(prof[::2], "glass", sides=16)
    for k in range(6):
        a = k / 6 * 2 * math.pi + 0.26
        pts = [Vector(((r + 0.011) * math.cos(a), (r + 0.011) * math.sin(a), z)) for r, z in prof[::2]]
        mb.tube(pts, 0.0026, "galvanized", sides=4)
    for z, r in ((g0 - 0.004, 0.065), ((g0 + g1) / 2, 0.081), (g1 + 0.004, 0.065)):
        P.ring(mb, (0, 0, z), r, 0.0028, mat="galvanized", segs=16, sides=4)
    # base with battery/cable gland
    mb.lathe([(0.064, g1), (0.07, g1 - 0.004), (0.078, g1 - 0.012), (0.078, g1 - 0.05), (0.072, g1 - 0.058),
              (0.03, g1 - 0.062), (0.0, g1 - 0.062)], "paint_green", sides=16)
    mb.lathe([(0.079, g1 - 0.02), (0.081, g1 - 0.022), (0.081, g1 - 0.03), (0.079, g1 - 0.032)], "brass", sides=16)
    # cable gland on the cap, feed cable loosely following the chain up to the hang point
    mb.cyl(0.009, 0.02, "brass", sides=8, Mx=trs((0.03, 0.0, zc + 0.002), (0, 35, 0)))
    cpts = [Vector((0.042, 0.0, zc + 0.018))]
    for k in range(1, 12):
        t = k / 11
        z = lerp(zc + 0.03, -0.012, t)
        cpts.append(Vector((0.05 * (1 - t) ** 1.5 + 0.012 + 0.006 * math.sin(t * 9), 0.01 * math.sin(t * 7), z)))
    mb.tube(cpts, 0.0042, "cable", sides=5)
    root = mb.finish()
    # bulb (child, emit_warm): pear-shaped lamp at the globe centre
    bb = MB("bulb")
    zb = (g0 + g1) / 2
    bb.lathe([(0.0, 0.034), (0.012, 0.032), (0.024, 0.018), (0.027, 0.0), (0.02, -0.02), (0.011, -0.03), (0.011, -0.04),
              (0.0, -0.04)], "emit_warm", sides=16)
    bulb = bb.finish(grime=False)
    child(bulb, root, (0, 0, zb))
    return root


def lerp(a, b, t):
    return a + (b - a) * t


# ====================================================================== bulb_cage (origin = ceiling attachment)
@node("bulb_cage", "hang", notes="origin = ceiling/cap attachment point; child bulb = lamp position")
def bulb_cage():
    mb = MB("bulb_cage")
    import parts as P
    # junction box screwed to the timber + gland + cable drop
    mb.box((0.11, 0.11, 0.05), "plastic_black", loc=(0, 0, -0.05), bevel=0.006, seg=2)
    for x in (-0.04, 0.04):
        for y in (-0.04, 0.04):
            mb.cyl(0.005, 0.004, "steel", sides=6, loc=(x, y, -0.054))
    mb.cyl(0.012, 0.022, "plastic_black", sides=8, loc=(0, 0, -0.072))
    drop = [Vector((0.003 * math.sin(k * 0.9), 0.002 * math.cos(k * 0.7), -0.072 - 0.033 * k)) for k in range(12)]
    mb.tube(drop, 0.0055, "cable", sides=6)
    zh = drop[-1].z
    # lampholder (bakelite) + guard clamp
    mb.lathe([(0.0, zh), (0.014, zh), (0.019, zh - 0.012), (0.021, zh - 0.05), (0.025, zh - 0.056), (0.025, zh - 0.066),
              (0.0, zh - 0.066)], "plastic_black", sides=12)
    mb.lathe([(0.027, zh - 0.05), (0.031, zh - 0.05), (0.031, zh - 0.066), (0.027, zh - 0.066)], "galvanized", sides=12)
    # wire cage: 6 meridians + 2 rings + bottom hoop
    z0 = zh - 0.066
    prof = [(0.031, z0), (0.05, z0 - 0.02), (0.058, z0 - 0.06), (0.054, z0 - 0.1), (0.036, z0 - 0.128), (0.0, z0 - 0.14)]
    for k in range(6):
        a = k / 6 * 2 * math.pi
        pts = [Vector((r * math.cos(a), r * math.sin(a), z)) for r, z in prof]
        mb.tube(pts, 0.0021, "galvanized", sides=5)
    P.ring(mb, (0, 0, z0 - 0.06), 0.058, 0.0024, mat="galvanized", segs=18, sides=5)
    P.ring(mb, (0, 0, z0 - 0.105), 0.052, 0.0024, mat="galvanized", segs=18, sides=5)
    root = mb.finish()
    bb = MB("bulb")
    bb.lathe([(0.0, 0.0), (0.013, -0.002), (0.016, -0.016), (0.03, -0.045), (0.031, -0.062), (0.024, -0.08),
              (0.0, -0.088)], "emit_warm", sides=16)
    bulb = bb.finish(grime=False)
    child(bulb, root, (0, 0, z0 + 0.004))
    return root


# ====================================================================== cable_2m (left rib)
CABLE_WALL_X = -2.2


@node("cable_2m", "tunnel", occ=[((CABLE_WALL_X - 0.002, 0, 1.9), (2.4, 1.4), "x")],
      notes="drift frame: J-hook in the -X rib (x=-2.2) at y=1.95 m (below timber_set's side lagging), power cable + red "
            "comms cable sag to the tile joints at z=+-1. Rotate yaw pi for the +X rib.")
def cable_2m():
    mb = MB("cable_2m")
    import parts as P
    hz = 1.95
    rest = P.j_hook(mb, (CABLE_WALL_X, 0, hz), (1, 0, 0), reach=0.1, rr=0.036, wire=0.0075, mat="galvanized")
    sag = 0.07
    pts, pts2 = [], []
    for k in range(25):
        y = -1.0 + 2.0 * k / 24
        z = rest.z - sag * (1 - math.cos(math.pi * y)) / 2
        pts.append(Vector((rest.x, y, z)))
        pts2.append(Vector((rest.x + 0.026, y, z + 0.012 + 0.004 * math.sin(y * 3.0))))
    mb.tube(pts, 0.021, "cable", sides=10)
    mb.tube(pts2, 0.0075, "hose_red", sides=6)
    # cable tag (440 V) hanging off the power cable beside the hook
    tag_c = Vector((rest.x + 0.004, -0.16, rest.z - 0.075))
    mb.rod(Vector((rest.x, -0.16, rest.z - 0.02)), tag_c + Vector((0, 0, 0.032)), 0.0015, "plastic_black", sides=4)
    mb.box((0.004, 0.07, 0.035), "plastic_yellow", center=True, loc=tag_c, bevel=0.001, seg=1)
    mb.label("voltage_440", tag_c + Vector((0.0025, 0, 0)), 0.066, rot=(0, 0, 90))
    mb.label("voltage_440", tag_c - Vector((0.0025, 0, 0)), 0.066, rot=(0, 0, -90))
    return mb.finish()


# ====================================================================== vent_duct_2m (upper right corner)
DUCT_X, DUCT_Z, DUCT_R = 1.30, 2.36, 0.40


@node("vent_duct_2m", "tunnel", grime=dict(floor=False),
      notes="drift frame: 0.8 m duct centred x=+1.30, y=2.36 (upper +X corner), hung from a messenger wire at y=2.79 (just "
            "under the timber caps); hangers at z=+-0.5 so 2 m tiles repeat seamlessly. Rotate yaw pi for the -X side.")
def vent_duct_2m():
    mb = MB("vent_duct_2m")
    import bmesh
    sides, per_pitch, pitch = 16, 5, 1.0 / 6.0
    rings = int(round(2.0 / pitch * per_pitch))
    tb = bmesh.new()
    uvl = tb.loops.layers.uv.new("uv")
    grid = []
    for j in range(rings + 1):
        y = -1.0 + 2.0 * j / rings
        sagz = -0.035 * (1 - math.cos(2 * math.pi * (y - 0.5))) / 2  # hangers at y = +-0.5
        row = []
        for i in range(sides):
            a = i / sides * 2 * math.pi
            ph = (y / pitch - a / (2 * math.pi)) % 1.0
            d = min(ph, 1 - ph)  # 0 at the wire, 0.5 mid-span
            r = DUCT_R + 0.004 - 0.02 * math.sin(min(1.0, d / 0.5) * math.pi / 2) ** 0.6
            # fabric hangs a little flat under its own weight, slack at the bottom
            x = r * math.cos(a)
            z = r * math.sin(a) * (0.95 if math.sin(a) < 0 else 0.99)
            row.append(tb.verts.new((DUCT_X + x, y, DUCT_Z + z + sagz)))
        grid.append(row)
    for j in range(rings):
        for i in range(sides):
            i2 = (i + 1) % sides
            f = tb.faces.new((grid[j][i], grid[j][i2], grid[j + 1][i2], grid[j + 1][i]))
            for lp, (u, v) in zip(f.loops, [(j, i), (j, i + 1), (j + 1, i + 1), (j + 1, i)]):
                lp[uvl].uv = (-1.0 + 2.0 * u / rings, v / sides * 2 * math.pi * DUCT_R)
    bmesh.ops.recalc_face_normals(tb, faces=tb.faces[:])
    tb.normal_update()
    mb.commit(tb, Matrix.Identity(4), "hose_yellow", None, uvoff=False)
    # suspension strip along the top + messenger wire + hangers
    top_z = DUCT_Z + DUCT_R * 0.99
    strip = []
    for k in range(21):
        y = -1.0 + 0.1 * k
        sagz = -0.035 * (1 - math.cos(2 * math.pi * (y - 0.5))) / 2
        strip.append(Vector((DUCT_X, y, top_z + sagz + 0.004)))
    mb.sweep([(-0.03, 0.0), (0.03, 0.0), (0.03, 0.006), (-0.03, 0.006)], strip, "hose_yellow", up=(0, 0, 1))
    wz = 2.79
    mb.rod((DUCT_X, -1.0, wz), (DUCT_X, 1.0, wz), 0.0035, "galvanized", sides=6, cap=False)
    for y in (-0.5, 0.5):
        mb.tube([Vector((DUCT_X, y, top_z + 0.006)), Vector((DUCT_X, y, wz - 0.03)), Vector((DUCT_X + 0.008, y, wz + 0.006)),
                 Vector((DUCT_X - 0.01, y, wz + 0.008)), Vector((DUCT_X - 0.01, y, wz - 0.01))], 0.0028, "galvanized", sides=5)
        mb.cyl(0.012, 0.006, "steel_dark", sides=8, loc=(DUCT_X, y, top_z + 0.004))
    return mb.finish()


# ====================================================================== pipe_2m (right rib, low)
@node("pipe_2m", "tunnel", occ=[((2.202, 0, 1.0), (2.4, 2.0), "x")],
      notes="drift frame: compressed-air (blue, 114 mm) at x=+2.13 y=1.25 and water (green, 60 mm) at x=+2.15 y=0.86 "
            "on a bracket in the +X rib (x=+2.2); coupling at z=+1 (tile joint), air outlet valve at z=-0.5.")
def pipe_2m():
    mb = MB("pipe_2m")
    import parts as P
    ax, az, ar = 2.13, 1.25, 0.057
    wx, wz, wr = 2.15, 0.86, 0.030
    mb.rod((ax, -1.0, az), (ax, 1.0, az), ar, "paint_blue", sides=16, cap=False)
    mb.rod((wx, -1.0, wz), (wx, 1.0, wz), wr, "paint_green", sides=12, cap=False)
    # grooved couplings at the tile joint (y = -1 = three.js z = +1)
    for (x, z, r) in ((ax, az, ar), (wx, wz, wr)):
        for yy in (-1.0,):
            mb.rod((x, yy - 0.045, z), (x, yy + 0.045, z), r + 0.016, "paint_red", sides=16, bevel=0.004)
            for s in (-1, 1):
                Mx = trs((x, yy, z), (0, 0, 0))
                mb.box((0.03, 0.05, 0.03), "paint_red", center=True,
                       Mx=Matrix.Translation((x + s * (r + 0.024), yy, z)), bevel=0.004, seg=1)
                bolt_c = Vector((x + s * (r + 0.024), yy, z + 0.018))
                P.hexnut(mb, bolt_c, 0.009, 0.008, (0, 0, 1), "steel_dark")
    # bracket in the rib: steel angle shelves + U-bolts
    by = 0.0
    mb.box((0.012, 0.09, 0.62), "steel_dark", loc=(2.194, by, 0.66), bevel=0.002, seg=1)
    for (x, z, r) in ((ax, az, ar), (wx, wz, wr)):
        mb.box((2.2 - (x - r - 0.02), 0.07, 0.008), "steel_dark", loc=((2.2 + x - r - 0.02) / 2, by, z - r - 0.008),
               bevel=0.0015, seg=1)
        mb.box((2.2 - (x - r - 0.02), 0.008, 0.05), "steel_dark", loc=((2.2 + x - r - 0.02) / 2, by - 0.031, z - r - 0.05),
               bevel=0.0015, seg=1)
        ub = [Vector((x - r - 0.006, by, z - r - 0.0)), Vector((x - r - 0.006, by, z))]
        for k in range(1, 8):
            t = math.pi - math.pi * k / 7
            ub.append(Vector((x + (r + 0.006) * math.cos(t), by, z + (r + 0.006) * math.sin(t))))
        ub.append(Vector((x + r + 0.006, by, z - r - 0.0)))
        mb.tube(ub, 0.005, "galvanized", sides=6)
        for s in (-1, 1):
            P.hexnut(mb, (x + s * (r + 0.006), by, z - r - 0.016), 0.008, 0.008, (0, 0, 1), "galvanized")
    for z in (0.42, 0.9):
        P.bolt(mb, (2.188, by, z), (-1, 0, 0), r=0.008, head=0.012, stud=0.015)
    # air outlet: tee down, ball valve with red lever, hose tail
    oy = -0.5
    mb.rod((ax, oy, az - ar + 0.01), (ax, oy, az - ar - 0.07), 0.021, "steel", sides=10)
    mb.rod((ax, oy - 0.04, az - ar - 0.07), (ax, oy + 0.04, az - ar - 0.07), 0.026, "brass", sides=10, bevel=0.003)
    mb.box((0.012, 0.14, 0.012), "paint_red", center=True, loc=(ax - 0.035, oy - 0.05, az - ar - 0.07), rot=(0, 0, 18))
    mb.rod((ax, oy, az - ar - 0.07), (ax, oy, az - ar - 0.16), 0.016, "brass", sides=8)
    mb.rod((ax, oy, az - ar - 0.16), (ax, oy, az - ar - 0.2), 0.011, "steel", sides=8)
    return mb.finish()


# ====================================================================== bolt_plate (wall: origin at the rock surface)
@node("bolt_plate", "wall", grime=dict(floor=False), notes="origin = rock surface at the bolt; plate faces +Z")
def bolt_plate():
    mb = MB("bolt_plate")
    import parts as P
    # domed bearing plate (150 x 150 x 6 mm) pressed into the rock
    def dome(v):
        r = math.hypot(v.x, v.z)
        lift = 0.016 * max(0.0, 1 - (r / 0.055) ** 2)
        return Vector((v.x, v.y - lift, v.z))
    mb.box((0.15, 0.006, 0.15), "galvanized", loc=(0, -0.003, 0), center=True, cuts=(4, 0, 4), warp=dome, bevel=0.002,
           seg=1)
    # hemispherical washer + nut + threaded tail
    mb.lathe([(0.03, 0.0), (0.028, -0.006), (0.02, -0.014), (0.012, -0.018), (0.0, -0.018)], "galvanized", sides=12,
             Mx=Matrix.Translation((0, -0.018, 0)) @ rotm((90, 0, 0)))
    P.hexnut(mb, (0, -0.036, 0), 0.017, 0.016, (0, -1, 0), "galvanized")
    mb.rod((0, -0.05, 0), (0, -0.088, 0), 0.0105, "steel_dark", sides=8, bevel=0.002)
    return mb.finish()


# ====================================================================== mesh_panel (wall: 2 x 2 m welded mesh)
@node("mesh_panel", "wall", grime=dict(floor=False),
      notes="2 x 2 m welded mesh sheet (alpha-cut custom_mesh_weld, double-sided), origin = back centre, faces +Z")
def mesh_panel():
    mb = MB("mesh_panel")
    mk.custom_mat("custom_mesh_weld", "mesh_weld.png", rough=0.45, metal=0.9)

    def wobble(u, v):
        return Vector((0, -0.012 - 0.012 * noise.noise(Vector((u * 3.1, v * 3.1, 0.5))) * math.sin(u * math.pi) * math.sin(v * math.pi), 0))
    tb_off = mb.grid(2.0, 2.0, 8, 8, "custom_mesh_weld", Matrix.Identity(4), fn=wobble, uvoff=False)
    # UVs: 1 tile = 0.2 m -> scale metres by 5
    for f in tb_off:
        for lp in f.loops:
            u, v = lp[mb.uvl].uv
            lp[mb.uvl].uv = (u * 5.0 + 5.0, v * 5.0 + 5.0)
    return mb.finish(grime=False)


# ====================================================================== rail_bumper (sits on rail_2m, origin floor centre)
@node("rail_bumper", "tunnel", notes="end-of-track stop clamped to the 0.6 m rails; same frame as rail_2m, buffer faces +Z")
def rail_bumper():
    mb = MB("rail_bumper")
    import parts as P
    rx = GAUGE / 2 + 0.0125
    for s in (-1, 1):
        x = s * rx
        # bent-rail struts: vertical post at the front, raker to the rear, clamp plates on the rail
        mb.box((0.075, 0.075, 0.42), "steel_dark", loc=(x, -0.02, RAIL_TOP), bevel=0.004, seg=1)
        mb.beam((x, 0.0, RAIL_TOP + 0.4), (x, 0.62, RAIL_TOP + 0.02), 0.07, 0.07, "steel_dark", up=(0, 0, 1), bevel=0.004)
        for y in (-0.02, 0.58):
            mb.box((0.14, 0.12, 0.012), "steel_dark", loc=(x, y, RAIL_TOP - 0.003), bevel=0.002, seg=1)
            for dx in (-0.045, 0.045):
                P.bolt(mb, (x + dx, y, RAIL_TOP + 0.009), (0, 0, 1), r=0.007, head=0.011, stud=0.012, washer=False)
    # timber buffer beam faced with a chevron board
    timber(mb, (-0.5, -0.1, RAIL_TOP + 0.36), (0.5, -0.1, RAIL_TOP + 0.36), 0.16, 0.2, up=(0, 0, 1), bevel=0.012, cuts=2)
    mb.box((0.98, 0.012, 0.15), "paint_yellow", loc=(0, -0.186, RAIL_TOP + 0.285), bevel=0.002, seg=1)
    mb.label("chevron", (0, -0.1935, RAIL_TOP + 0.36), 0.96, 0.14)
    for x in (-0.38, 0.38):
        P.bolt(mb, (x, -0.194, RAIL_TOP + 0.36), (0, -1, 0), r=0.008, head=0.013, stud=0.0)
    return mb.finish()
