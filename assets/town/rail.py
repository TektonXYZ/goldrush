"""rail: track_10m, buffer_stop, locomotive (4-4-0 + tender), coach, boxcar.

Track: standard gauge 1.435 m along X, origin at ground centre, railhead at z = RAIL_TOP.
Rolling stock: front faces -Y (three +Z), length along Y, origin on the railhead plane (wheel contact),
centred on the vehicle. Place it at (track y = RAIL_TOP) and yaw +-90 deg to run along a track laid on X.
Wheel children spin about local X; positive rotation = rolling forward (toward -Y / three +Z).
"""
import math

import bpy
from mathutils import Matrix, Vector

import arch
from arch import B
import tk
from tk import T

RAIL_TOP = 0.47
GAUGE = 1.435
RAIL_X = GAUGE / 2 + 0.0325          # railhead centre line
DRIVER_R = 0.7875                     # 62" drivers
SMALL_R = DRIVER_R / 2                # truck + tender wheels (31"): exactly 2 turns per driver turn
CAR_R = 0.42                          # coach / boxcar wheels (33")


# ------------------------------------------------------------------ track

def rail_profile():
    """(y, z) of a ~90 lb rail, base at z = 0, 0.145 tall; returns [(pts, material)] strips."""
    h = 0.145
    head = [(0.0325, h - 0.012), (0.034, h - 0.04), (0.012, h - 0.05)]
    pts = [(-0.07, 0.0), (0.07, 0.0), (0.07, 0.01), (0.012, 0.03), (0.0085, 0.045), (0.0085, h - 0.052),
           (0.034, h - 0.04), (0.0325, h - 0.006), (0.024, h), (-0.024, h), (-0.0325, h - 0.006), (-0.034, h - 0.04),
           (-0.0085, h - 0.052), (-0.0085, 0.045), (-0.012, 0.03), (-0.07, 0.01)]
    return pts


def rail(mb, x0, x1, yc, zb):
    """Extruded rail along X between x0 and x1 centred on y=yc, base at zb. Head = steel, rest = rust."""
    pts = rail_profile()
    n = len(pts)
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        if i == 0:
            continue  # bottom face (sits on the plates)
        is_head = a[1] > 0.09 and b[1] > 0.09
        mat = "steel" if is_head else "rust"
        q = [(x0, yc + a[0], zb + a[1]), (x0, yc + b[0], zb + b[1]), (x1, yc + b[0], zb + b[1]), (x1, yc + a[0], zb + a[1])]
        mb.poly(q, mat, smooth_=True)


def track_10m(seed=31):
    b = B("track_10m", seed)
    mb = b.mb
    L = 10.0
    zt_ballast = 0.22
    # ballast prism (no end caps: segments butt together)
    mb.poly([(-L / 2, -1.5, zt_ballast), (L / 2, -1.5, zt_ballast), (L / 2, 1.5, zt_ballast), (-L / 2, 1.5, zt_ballast)],
            "gravel", facing=(0, 0, 1))
    for sgn in (-1, 1):
        mb.poly([(-L / 2, sgn * 1.5, zt_ballast), (L / 2, sgn * 1.5, zt_ballast), (L / 2, sgn * 2.15, 0.0),
                 (-L / 2, sgn * 2.15, 0.0)], "gravel", facing=(0, sgn, 0.6))
    n = 16
    sp = L / n
    zs0, zs1 = 0.15, 0.31
    for i in range(n):
        x = -L / 2 + sp * (i + 0.5) + mb.rng.uniform(-0.03, 0.03)
        rz = mb.rng.uniform(-1.2, 1.2)
        mb.boxc((0.23, 2.6, zs1 - zs0), "wood_timber", loc=(x, mb.rng.uniform(-0.03, 0.03), (zs0 + zs1) / 2),
                rot=(0, 0, rz), skip="d", tone=mb.tone(0.72, 1.0), uvoff=True, grain=1)
        for sy in (-RAIL_X, RAIL_X):
            mb.boxc((0.19, 0.36, 0.016), "steel_dark", loc=(x, sy, zs1 + 0.008), skip="d")
            for dy in (-0.11, 0.11):
                mb.boxc((0.025, 0.025, 0.03), "steel_dark", loc=(x + 0.05 * (1 if dy > 0 else -1), sy + dy, zs1 + 0.025),
                        skip="d")
    zb = zs1 + 0.016
    for sy in (-RAIL_X, RAIL_X):
        rail(mb, -L / 2, L / 2, sy, zb)
        for side in (-1, 1):
            mb.boxc((0.6, 0.018, 0.075), "rust", loc=(0.0, sy + side * 0.018, zb + 0.06))
    assert abs(zb + 0.145 - RAIL_TOP) < 0.01, zb + 0.145
    b.empties.append(("railhead", (0.0, 0.0, RAIL_TOP), (0, 0, 0)))
    return b.finish()


def buffer_stop(seed=32):
    """Track end: rail stubs + sleepers, a timber buffer beam on a frame of bent rails, red lamp.
    Rails run along X like track_10m; the beam faces -X (toward incoming trains); origin = rail end at x = 0."""
    b = B("buffer_stop", seed)
    mb = b.mb
    L = 3.0
    zt = 0.22
    mb.poly([(0, -1.5, zt), (L, -1.5, zt), (L, 1.5, zt), (0, 1.5, zt)], "gravel", facing=(0, 0, 1))
    for sgn in (-1, 1):
        mb.poly([(0, sgn * 1.5, zt), (L, sgn * 1.5, zt), (L, sgn * 2.15, 0.0), (0, sgn * 2.15, 0.0)], "gravel",
                facing=(0, sgn, 0.6))
    mb.poly([(L, -1.5, zt), (L, 1.5, zt), (L, 2.15, 0.0), (L, -2.15, 0.0)], "gravel", facing=(1, 0, 0.5))
    for i in range(5):
        x = 0.3 + i * 0.6
        mb.boxc((0.23, 2.6, 0.16), "wood_timber", loc=(x, 0, 0.23), skip="d", tone=mb.tone(0.72, 1.0), uvoff=True, grain=1)
        for sy in (-RAIL_X, RAIL_X):
            mb.boxc((0.19, 0.36, 0.016), "steel_dark", loc=(x, sy, 0.318), skip="d")
    zb = 0.326
    for sy in (-RAIL_X, RAIL_X):
        rail(mb, 0.0, L - 0.2, sy, zb)
        # bent-rail struts
        mb.span((0.35, sy, RAIL_TOP), (0.45, sy, 1.55), 0.07, 0.12, "rust", up=(1, 0, 0))
        mb.span((2.5, sy, RAIL_TOP), (0.5, sy, 1.45), 0.07, 0.12, "rust", up=(0, 0, 1))
    # timber buffer beam with striped face
    mb.boxc((0.36, 2.4, 0.42), "paint_red", loc=(0.35, 0, 1.36), bev=0.02)
    for k in range(5):
        mb.boxc((0.012, 0.18, 0.4), "paint_white", loc=(0.165, -0.9 + k * 0.45, 1.36), rot=(35, 0, 0))
    for sy in (-0.55, 0.55):
        mb.cyl(0.16, 0.08, "cast_iron", loc=(0.12, sy, 1.36), rot=(0, 90, 0), centre=True, sides=12, bev=0.01)
    mb.cyl(0.03, 0.5, "cast_iron", loc=(0.4, 0.9, 1.57), sides=6)
    arch.lantern(mb, 0.4, 0.9, 2.07, s=0.9, glow="emit_red")
    return b.finish()


# ------------------------------------------------------------------ wheels

def spoked_wheel(mb, r, spokes=16, width=0.14, flange=0.025, hub_r=None, counterweight=False, crank=None,
                 mat="paint_black", tyre="steel"):
    cw_dir = math.atan2(crank[1], crank[0]) + math.pi if crank is not None else -math.pi / 2
    """Wheel in the YZ plane centred on the current frame origin, axle along X, outer face at +X."""
    hub_r = hub_r or r * 0.2
    tr = r - 0.06
    # tyre with flange (inner side = -X)
    prof = [(r - 0.075, -width / 2), (r + flange, -width / 2), (r + flange, -width / 2 + 0.02), (r, -width / 2 + 0.04),
            (r - 0.005, width / 2), (r - 0.075, width / 2)]
    with mb.at(M=Matrix.Rotation(math.radians(90), 4, "Y")):
        mb.lathe([(a, -z) for a, z in prof], tyre, sides=26, cap_top=False, cap_bot=False, smooth_=True)
        mb.ring(tr - 0.03, r - 0.074, 0.07, mat, loc=(0, 0, -0.035), sides=26)
        mb.cyl(hub_r, 0.16, mat, loc=(0, 0, -0.06), sides=14, bev=0.01)
        mb.cyl(hub_r * 0.45, 0.2, "steel", loc=(0, 0, -0.04), sides=10)
    for k in range(spokes):
        a = k * math.tau / spokes
        ca, sa = math.cos(a), math.sin(a)
        p0 = (0.0, ca * hub_r * 0.9, sa * hub_r * 0.9)
        p1 = (0.0, ca * (tr - 0.02), sa * (tr - 0.02))
        mb.span(p0, p1, 0.055 * (r / 0.79) ** 0.5, 0.03, mat, up=(1, 0, 0))
    if counterweight:
        # crescent opposite the crank pin
        seg = 8
        a0, a1 = cw_dir - math.pi * 0.38, cw_dir + math.pi * 0.38
        pts_o, pts_i = [], []
        for i in range(seg + 1):
            a = a0 + (a1 - a0) * i / seg
            pts_o.append((0.035, math.cos(a) * (tr - 0.03), math.sin(a) * (tr - 0.03)))
            pts_i.append((0.035, math.cos(a) * tr * 0.55, math.sin(a) * tr * 0.55))
        mb.poly(pts_o + list(reversed(pts_i)), mat, thick=0.06, facing=(1, 0, 0))
    if crank is not None:
        cy, cz = crank
        mb.cyl(0.07, 0.07, "steel", loc=(0.05, cy, cz), rot=(0, 90, 0), sides=10, bev=0.01)
        mb.cyl(0.045, 0.16, "steel", loc=(0.1, cy, cz), rot=(0, 90, 0), sides=8)


def disc_wheel(mb, r, width=0.13, mat="paint_black"):
    prof = [(r - 0.06, -width / 2), (r + 0.025, -width / 2), (r + 0.025, -width / 2 + 0.02), (r, -width / 2 + 0.04),
            (r - 0.004, width / 2), (r - 0.06, width / 2)]
    with mb.at(M=Matrix.Rotation(math.radians(90), 4, "Y")):
        mb.lathe([(a, -z) for a, z in prof], "steel", sides=20, cap_top=False, cap_bot=False)
        mb.lathe([(r - 0.06, -0.03), (r * 0.5, -0.05), (r * 0.25, -0.07), (r * 0.2, -0.09), (0.0, -0.1)], mat, sides=20,
                 cap_top=False, cap_bot=False)
        mb.lathe([(r - 0.06, 0.03), (r * 0.5, 0.02), (0.0, 0.02)], mat, sides=20, cap_top=False, cap_bot=False)


def axle_set(parent, name, y, r, kind="spoked", spokes=12, counterweight=False, crank_angle=None, crank_r=0.0,
             crank_phase=(0.0, 90.0), mat="paint_black"):
    """Two wheels + axle as one child object (origin at the axle centre) parented to `parent`."""
    mb = tk.MB(name)
    for side in (-1, 1):
        x = side * RAIL_X
        M = T((x, 0, 0)) @ (Matrix.Identity(4) if side > 0 else Matrix.Rotation(math.pi, 4, "Z"))
        with mb.at(M=M):
            if kind == "spoked":
                crank = None
                if crank_r:
                    ph = math.radians(crank_phase[0] if side > 0 else crank_phase[1])
                    crank = (math.cos(ph) * crank_r * side, math.sin(ph) * crank_r)
                spoked_wheel(mb, r, spokes=spokes, counterweight=counterweight, crank=crank, mat=mat)
            else:
                disc_wheel(mb, r, mat=mat)
    mb.cyl(0.075, 2 * RAIL_X - 0.14, "steel_dark", rot=(0, 90, 0), centre=True, sides=10)
    o = mb.finish()
    o.location = (0, y, r)
    o.parent = parent
    return o


# ------------------------------------------------------------------ locomotive

def locomotive(seed=41):
    """4-4-0 American: diamond stack, box headlamp, brass domes + bell, wooden cab, slatted pilot,
    62" drivers with side + main rods, 8-wheel tender loaded with cordwood."""
    b = B("locomotive", seed)
    mb = b.mb
    zb = 2.12      # boiler centreline
    rb = 0.6       # boiler radius
    rs = 0.66      # smokebox radius
    y_sb0, y_sb1 = -6.95, -5.45    # smokebox
    y_bo1 = -1.5                    # boiler end (firebox front)
    green, black, red = "paint_green", "paint_black", "paint_red"
    # ---- frames + running boards
    for sx in (-0.56, 0.56):
        mb.boxc((0.1, 7.6, 0.34), "steel_dark", loc=(sx, -3.3, 0.8))
    for sx in (-1, 1):
        mb.boxc((0.5, 6.1, 0.05), "steel_dark", loc=(sx * 1.08, -3.3, 1.66), bev=0.008)
        mb.boxc((0.025, 6.1, 0.09), "brass", loc=(sx * 1.34, -3.3, 1.63))
        for yy in (-6.1, -4.2, -2.1, -0.4):
            mb.span((sx * 0.62, yy, 1.3), (sx * 1.25, yy, 1.64), 0.05, 0.04, "steel_dark", up=(0, 1, 0))
    # ---- pilot (cowcatcher) + bumper beam + coupler
    mb.boxc((2.5, 0.28, 0.42), red, loc=(0, -7.12, 1.0), bev=0.02)
    for k in range(13):
        t = (k / 12) * 2 - 1
        xb = t * 1.15
        mb.span((xb, -7.0, 0.9), (xb * 0.12, -8.25, 0.1), 0.06, 0.035, "wood_dark", up=(0, -0.3, 1))
    mb.span((-1.18, -7.0, 0.92), (0, -8.3, 0.1), 0.08, 0.05, "cast_iron", up=(0, 0, 1))
    mb.span((1.18, -7.0, 0.92), (0, -8.3, 0.1), 0.08, 0.05, "cast_iron", up=(0, 0, 1))
    mb.span((-1.2, -7.05, 0.15), (1.2, -7.05, 0.15), 0.08, 0.06, "cast_iron")
    mb.boxc((0.18, 0.5, 0.16), "cast_iron", loc=(0, -7.4, 0.95), bev=0.01)
    mb.cyl(0.05, 0.3, "cast_iron", loc=(0, -7.62, 0.95), rot=(90, 0, 0), centre=True, sides=8)
    # ---- smokebox, door, number plate
    with mb.at(M=T((0, y_sb0, zb)) @ Matrix.Rotation(math.radians(-90), 4, "X")):
        mb.cyl(rs, y_sb1 - y_sb0, black, sides=28, cap_bot=False, cap_top=False)
        mb.lathe([(rs + 0.03, -0.05), (rs + 0.03, 0.04), (rs - 0.02, 0.06)], "brass", sides=28, cap_top=False,
                 cap_bot=False)
        mb.lathe([(rs - 0.02, -0.02), (rs * 0.8, -0.09), (rs * 0.4, -0.12), (0.0, -0.13)], black, sides=28,
                 cap_top=False, cap_bot=False)
        for k in range(6):
            a = k * math.tau / 6 + 0.3
            mb.boxc((0.1, 0.08, 0.05), "steel_dark", loc=(math.cos(a) * rs * 0.85, math.sin(a) * rs * 0.85, -0.1))
    b.lab.quad_uv([(-0.22, y_sb0 - 0.135, zb - 0.22), (0.22, y_sb0 - 0.135, zb - 0.22), (0.22, y_sb0 - 0.135, zb + 0.22),
                   (-0.22, y_sb0 - 0.135, zb + 0.22)], "label_train",
                  uvs=((0.125, 0.0), (0.375, 0.0), (0.375, 0.25), (0.125, 0.25)))
    # ---- boiler + bands + handrails
    with mb.at(M=T((0, y_sb1, zb)) @ Matrix.Rotation(math.radians(-90), 4, "X")):
        mb.cyl(rs, 0.12, black, sides=28, r2=rb, cap_bot=False, cap_top=False)
        mb.cyl(rb, y_bo1 - y_sb1, green, sides=28, cap_bot=False, cap_top=False, loc=(0, 0, 0.12))
        for k in range(5):
            zz = 0.5 + k * (y_bo1 - y_sb1 - 0.7) / 4
            mb.lathe([(rb + 0.004, zz - 0.035), (rb + 0.016, zz - 0.02), (rb + 0.016, zz + 0.02), (rb + 0.004, zz + 0.035)],
                     "brass", sides=28, cap_top=False, cap_bot=False)
    for sx in (-1, 1):
        mb.tube([(sx * (rb + 0.1), -6.7, zb + 0.25), (sx * (rb + 0.1), -1.7, zb + 0.25)], 0.014, "brass", sides=6)
        for yy in (-6.5, -5.0, -3.4, -1.9):
            mb.span((sx * rb * 0.95, yy, zb + 0.24), (sx * (rb + 0.1), yy, zb + 0.25), 0.015, 0.015, "brass")
    # ---- diamond stack + smoke empty
    ys = -6.25
    zt = zb + rs - 0.02
    mb.lathe([(0.3, zt - 0.1), (0.3, zt + 0.05), (0.21, zt + 0.12), (0.2, zt + 0.7), (0.23, zt + 0.74), (0.62, zt + 1.26),
              (0.66, zt + 1.32), (0.6, zt + 1.36), (0.36, zt + 1.62), (0.38, zt + 1.66), (0.3, zt + 1.68)], black,
             loc=(0, ys, 0), sides=20, cap_bot=False, cap_top=False)
    mb.lathe([(0.66, zt + 1.3), (0.68, zt + 1.33), (0.66, zt + 1.36)], "brass", loc=(0, ys, 0), sides=20, cap_top=False,
             cap_bot=False)
    mb.cyl(0.3, 0.02, "steel_dark", loc=(0, ys, zt + 1.6), sides=20)
    b.empties.append(("smoke", (0, ys, zt + 1.7), (0, 0, 0)))
    # ---- box headlamp on its bracket
    hy, hz = -6.72, zb + rs + 0.12
    mb.boxc((0.5, 0.5, 0.14), black, loc=(0, hy + 0.1, hz - 0.07))
    mb.boxc((0.72, 0.8, 0.72), red, loc=(0, hy, hz + 0.36), bev=0.02)
    mb.boxc((0.78, 0.86, 0.06), "brass", loc=(0, hy, hz + 0.75), bev=0.01)
    mb.cyl(0.36, 0.2, black, loc=(0, hy, hz + 0.78), r2=0.08, sides=4, rot=(0, 0, 45))
    mb.cyl(0.07, 0.22, black, loc=(0, hy, hz + 0.96), sides=8)
    mb.cyl(0.25, 0.08, "brass", loc=(0, hy - 0.42, hz + 0.36), rot=(90, 0, 0), centre=True, sides=20, bev=0.01)
    mb.cyl(0.2, 0.02, "emit_warm", loc=(0, hy - 0.465, hz + 0.36), rot=(90, 0, 0), centre=True, sides=20)
    for sx in (-1, 1):
        b.lab.quad_uv([(sx * 0.362, hy - sx * 0.3, hz + 0.12), (sx * 0.362, hy + sx * 0.3, hz + 0.12),
                       (sx * 0.362, hy + sx * 0.3, hz + 0.6), (sx * 0.362, hy - sx * 0.3, hz + 0.6)], "label_train",
                      uvs=((0.52, 0.01), (0.98, 0.01), (0.98, 0.235), (0.52, 0.235)))
    # ---- domes, bell, whistle, sand pipes
    for yy, r_, h_, mat_ in ((-4.55, 0.3, 0.62, green), (-2.6, 0.36, 0.78, "brass")):
        top = zb + rb
        mb.lathe([(r_ + 0.12, top - 0.12), (r_ + 0.03, top - 0.02), (r_, top + 0.06), (r_, top + h_ * 0.7),
                  (r_ * 0.92, top + h_ * 0.82), (r_ * 0.6, top + h_ * 0.95), (0.0, top + h_)], mat_, loc=(0, yy, 0), sides=20,
                 cap_bot=False)
        mb.lathe([(r_ + 0.02, top + h_ * 0.66), (r_ + 0.04, top + h_ * 0.7), (r_ + 0.02, top + h_ * 0.74)], "brass",
                 loc=(0, yy, 0), sides=20, cap_top=False, cap_bot=False)
    wt = zb + rb + 0.78
    mb.cyl(0.04, 0.18, "brass", loc=(0, -2.6, wt), sides=8)
    mb.lathe([(0.06, wt + 0.18), (0.07, wt + 0.22), (0.07, wt + 0.42), (0.05, wt + 0.45), (0.02, wt + 0.5)], "brass",
             loc=(0, -2.6, 0), sides=10, cap_bot=True)
    for sx in (-0.14, 0.14):
        mb.cyl(0.045, 0.22, "brass", loc=(sx, -2.4, wt - 0.05), sides=8)
    by_ = -3.6
    bt = zb + rb
    for sx in (-0.22, 0.22):
        mb.span((sx, by_, bt - 0.05), (sx * 0.8, by_, bt + 0.55), 0.05, 0.05, "cast_iron", up=(0, 1, 0))
    mb.span((-0.2, by_, bt + 0.55), (0.2, by_, bt + 0.55), 0.06, 0.05, "cast_iron")
    mb.lathe([(0.0, bt + 0.12), (0.2, bt + 0.13), (0.19, bt + 0.18), (0.15, bt + 0.32), (0.13, bt + 0.42), (0.09, bt + 0.47),
              (0.0, bt + 0.48)], "brass", loc=(0, by_, 0), sides=16, cap_bot=False)
    # ---- cylinders + steam chests + guides
    yc0, yc1 = -6.35, -5.55
    cz = 0.98
    for sx in (-1, 1):
        x = sx * 1.02
        with mb.at(M=T((x, yc0, cz)) @ Matrix.Rotation(math.radians(-90), 4, "X")):
            mb.cyl(0.27, yc1 - yc0, black, sides=18, cap_bot=False, cap_top=False)
            mb.cyl(0.29, 0.06, "brass", sides=18, loc=(0, 0, -0.03), bev=0.01)
            mb.cyl(0.29, 0.06, "brass", sides=18, loc=(0, 0, yc1 - yc0 - 0.03), bev=0.01)
        mb.boxc((0.42, 0.7, 0.32), black, loc=(x, (yc0 + yc1) / 2, cz + 0.42), bev=0.02)
        mb.boxc((0.44, 0.72, 0.04), "brass", loc=(x, (yc0 + yc1) / 2, cz + 0.6), bev=0.006)
        mb.span((sx * 0.6, (yc0 + yc1) / 2, cz + 0.3), (sx * 0.62, (yc0 + yc1) / 2, zb - 0.3), 0.18, 0.5, black, up=(0, 1, 0))
        for dz in (-0.11, 0.11):
            mb.boxc((0.06, 1.55, 0.05), "steel", loc=(x, yc1 + 0.78, cz + dz))
        mb.boxc((0.2, 0.08, 0.36), "steel_dark", loc=(x, yc1 + 1.58, cz))
    # ---- firebox + cab
    mb.boxc((1.1, 1.9, 0.75), black, loc=(0, -0.55, 1.15))
    yk0, yk1 = -0.55, 1.15
    zf, zr0 = 1.72, 3.75
    cab_mat = "wood_dark"
    mb.boxc((2.75, yk1 - yk0 + 0.2, 0.08), "wood_planks", loc=(0, (yk0 + yk1) / 2, zf))
    for sx in (-1, 1):
        x = sx * 1.34
        # side wall with two arched windows: lower panel, posts, upper rail
        mb.boxc((0.06, yk1 - yk0, 1.05), cab_mat, loc=(x, (yk0 + yk1) / 2, zf + 0.52), bev=0.008)
        mb.boxc((0.07, yk1 - yk0 + 0.04, 0.06), "brass", loc=(x, (yk0 + yk1) / 2, zf + 1.06))
        for yy in (yk0 + 0.06, (yk0 + yk1) / 2, yk1 - 0.06):
            mb.boxc((0.06, 0.12, zr0 - zf - 1.05), cab_mat, loc=(x, yy, zf + 1.05 + (zr0 - zf - 1.05) / 2), bev=0.006)
        mb.boxc((0.06, yk1 - yk0, 0.22), cab_mat, loc=(x, (yk0 + yk1) / 2, zr0 - 0.11))
        for (wa, wb) in ((yk0 + 0.12, (yk0 + yk1) / 2 - 0.06), ((yk0 + yk1) / 2 + 0.06, yk1 - 0.12)):
            mb.poly([(x, wa, zf + 1.1), (x, wb, zf + 1.1), (x, wb, zr0 - 0.22), (x, wa, zr0 - 0.22)], "glass_dark",
                    facing=(sx, 0, 0))
        b.lab.quad_uv([(x + sx * 0.034, (yk0 + yk1) / 2 - 0.36 * sx, zf + 0.2), (x + sx * 0.034, (yk0 + yk1) / 2 + 0.36 * sx, zf + 0.2),
                       (x + sx * 0.034, (yk0 + yk1) / 2 + 0.36 * sx, zf + 0.7), (x + sx * 0.034, (yk0 + yk1) / 2 - 0.36 * sx, zf + 0.7)],
                      "label_train", uvs=((0.06, 0.625), (0.43, 0.625), (0.43, 0.74), (0.06, 0.74)))
        # steps + grab irons
        mb.boxc((0.35, 0.3, 0.04), "steel_dark", loc=(sx * 1.25, yk1 - 0.15, 1.05))
        mb.span((sx * 1.25, yk1 - 0.15, 1.05), (sx * 1.3, yk1 - 0.15, zf), 0.04, 0.03, "steel_dark")
        mb.tube([(sx * 1.39, yk1 + 0.02, zf + 0.2), (sx * 1.39, yk1 + 0.02, zf + 1.5)], 0.015, "brass")
    # front wall with two small windows beside the boiler
    mb.boxc((2.7, 0.06, 0.55), cab_mat, loc=(0, yk0, zr0 - 0.27))
    for sx in (-1, 1):
        mb.boxc((0.62, 0.06, zr0 - zf - 0.55), cab_mat, loc=(sx * 1.0, yk0, zf + (zr0 - zf - 0.55) / 2))
        mb.poly([(sx * 0.72, yk0 - 0.035, zf + 1.2), (sx * 1.25, yk0 - 0.035, zf + 1.2), (sx * 1.25, yk0 - 0.035, zr0 - 0.6),
                 (sx * 0.72, yk0 - 0.035, zr0 - 0.6)], "glass_dark", facing=(0, -1, 0))
    # arched roof
    rw = 1.55
    rings = []
    for i in range(9):
        a = -math.pi / 2 + math.pi * i / 8
        rings.append(a)
    prof = [(math.sin(a) * rw, zr0 + math.cos(a) * 0.32) for a in rings]
    loftL = [[(px, yk0 - 0.35, pz) for px, pz in prof], [(px, yk1 + 0.4, pz) for px, pz in prof]]
    mb.loft(loftL, "paint_black", close=False, smooth_=True)
    mb.loft([[(px, yk1 + 0.4, pz - 0.04) for px, pz in prof], [(px, yk0 - 0.35, pz - 0.04) for px, pz in prof]],
            "wood_planks", close=False, smooth_=True)
    mb.boxc((0.5, yk1 - yk0 + 0.7, 0.12), "paint_black", loc=(0, (yk0 + yk1) / 2 + 0.03, zr0 + 0.36), bev=0.02)
    # backhead (visible through the open cab back)
    with mb.at(M=T((0, yk0 + 0.05, zb)) @ Matrix.Rotation(math.radians(-90), 4, "X")):
        mb.cyl(rb, 0.6, black, sides=20, cap_bot=False)
    mb.cyl(0.12, 0.05, "brass", loc=(0.3, yk0 + 0.66, zb + 0.2), rot=(90, 0, 0), centre=True, sides=14)
    mb.boxc((0.45, 0.04, 0.35), "cast_iron", loc=(0, yk0 + 0.66, zb - 0.3))
    # ---- leading truck frame
    for sx in (-1, 1):
        mb.boxc((0.08, 1.7, 0.12), "cast_iron", loc=(sx * 0.95, -6.0, 0.42))
    mb.boxc((1.9, 0.3, 0.14), "cast_iron", loc=(0, -6.0, 0.55))
    # ---- tender
    ty0, ty1 = 1.45, 7.9
    tz0, tz1 = 1.18, 2.55
    mb.boxc((2.7, ty1 - ty0, 0.22), "steel_dark", loc=(0, (ty0 + ty1) / 2, tz0 - 0.11))
    mb.boxc((2.64, ty1 - ty0 - 0.1, tz1 - tz0), green, loc=(0, (ty0 + ty1) / 2, tz0 + (tz1 - tz0) / 2), bev=0.03)
    for sx in (-1, 1):
        mb.boxc((0.04, ty1 - ty0, 0.18), "brass", loc=(sx * 1.335, (ty0 + ty1) / 2, tz1 - 0.02))
        mb.boxc((0.04, ty1 - ty0 - 0.1, 0.03), "brass", loc=(sx * 1.335, (ty0 + ty1) / 2, tz0 + 0.12))
        b.lab.quad_uv([(sx * 1.325, 4.7 - sx * 2.45, tz0 + 0.38), (sx * 1.325, 4.7 + sx * 2.45, tz0 + 0.38),
                       (sx * 1.325, 4.7 + sx * 2.45, tz0 + 1.05), (sx * 1.325, 4.7 - sx * 2.45, tz0 + 1.05)], "label_train",
                      uvs=((0.02, 0.8), (0.98, 0.8), (0.98, 0.95), (0.02, 0.95)))
        # flared coaming
        mb.span((sx * 1.33, ty0 + 0.3, tz1 + 0.02), (sx * 1.33, ty1, tz1 + 0.02), 0.04, 0.3, "steel_dark", up=(sx * 0.3, 0, 1))
    mb.poly([(-1.3, ty0 + 1.6, tz1), (1.3, ty0 + 1.6, tz1), (1.3, ty1 - 0.05, tz1), (-1.3, ty1 - 0.05, tz1)], green,
            facing=(0, 0, 1))
    mb.cyl(0.32, 0.18, black, loc=(0, ty1 - 1.0, tz1), sides=16, bev=0.01)
    mb.boxc((2.5, 0.28, 0.4), red, loc=(0, ty1 + 0.1, 0.98), bev=0.02)
    mb.boxc((0.18, 0.45, 0.16), "cast_iron", loc=(0, ty1 + 0.4, 0.95), bev=0.01)
    arch.lantern(mb, 0.9, ty1 - 0.25, tz1 + 0.02, s=0.9, glow="emit_red")
    # cordwood bunker load
    wy0, wy1 = ty0 + 0.1, ty0 + 1.55
    mb.boxc((2.4, wy1 - wy0, 0.12), "wood_planks", loc=(0, (wy0 + wy1) / 2, tz1 - 0.6))
    for layer in range(5):
        zz = tz1 - 0.42 + layer * 0.2
        n = 11 - layer
        for k in range(n):
            xx = -1.1 + (2.2 / (n - 1)) * k + (0.06 if layer % 2 else 0) + mb.rng.uniform(-0.03, 0.03)
            if abs(xx) > 1.2 - layer * 0.08:
                continue
            r_ = mb.rng.uniform(0.075, 0.1)
            L_ = mb.rng.uniform(1.15, 1.4)
            mb.cyl(r_, L_, "wood_timber", loc=(xx, (wy0 + wy1) / 2 + mb.rng.uniform(-0.08, 0.08), zz), rot=(90, 0, mb.rng.uniform(-6, 6)),
                   centre=True, sides=6, tone=mb.tone(0.75, 1.0), smooth_=True)
    # tender truck frames
    for yy in (2.75, 6.6):
        for sx in (-1, 1):
            mb.boxc((0.1, 2.0, 0.16), "cast_iron", loc=(sx * 0.97, yy, 0.5), bev=0.01)
            mb.boxc((0.12, 0.35, 0.28), "cast_iron", loc=(sx * 0.97, yy, 0.62))
        mb.boxc((1.9, 0.3, 0.16), "cast_iron", loc=(0, yy, 0.82))
    root = b.finish()
    # ---- wheel sets (children, spin about local X)
    phases = (0.0, 90.0)   # right/left cranks quartered
    crank_r = 0.33
    wheels = []
    for i, (yy, r_, kind) in enumerate(((-6.6, SMALL_R, "spoked"), (-5.4, SMALL_R, "spoked"), (-3.3, DRIVER_R, "driver"),
                                        (-0.9, DRIVER_R, "driver"), (2.0, SMALL_R, "disc"), (3.5, SMALL_R, "disc"),
                                        (5.85, SMALL_R, "disc"), (7.35, SMALL_R, "disc"))):
        if kind == "driver":
            w = axle_set(root, f"wheels_{i}", yy, r_, kind="spoked", spokes=16, counterweight=True, crank_r=crank_r,
                         crank_phase=phases)
        elif kind == "spoked":
            w = axle_set(root, f"wheels_{i}", yy, r_, kind="spoked", spokes=10)
        else:
            w = axle_set(root, f"wheels_{i}", yy, r_, kind="disc")
        wheels.append((w, r_))
    # ---- rods (children, animated by the Run clip)
    rods = {}
    for side, ph in ((1, phases[0]), (-1, phases[1])):
        x = side * (RAIL_X + 0.17)
        a = math.radians(ph)
        cy, cz = math.cos(a) * crank_r, math.sin(a) * crank_r
        # side rod between the two drivers' crank pins
        m = tk.MB(f"siderod_{'r' if side > 0 else 'l'}")
        m.boxc((0.05, 2.5, 0.1), "steel", loc=(0, 0, 0), bev=0.01)
        for yy in (-1.2, 1.2):
            m.cyl(0.09, 0.07, "steel", loc=(0, yy, 0), rot=(0, 90, 0), centre=True, sides=12)
        so = m.finish()
        so.parent = root
        so.location = (x, (-3.3 + -0.9) / 2 + cy, DRIVER_R + cz)
        # main rod from crosshead to the rear crank pin
        m = tk.MB(f"mainrod_{'r' if side > 0 else 'l'}")
        Lm = 3.95
        m.boxc((0.05, Lm, 0.12), "steel", loc=(0, Lm / 2, 0), bev=0.01)
        m.cyl(0.11, 0.08, "steel", loc=(0, 0, 0), rot=(0, 90, 0), centre=True, sides=12)
        m.cyl(0.1, 0.08, "steel", loc=(0, Lm, 0), rot=(0, 90, 0), centre=True, sides=12)
        mo = m.finish()
        mo.parent = root
        # crosshead block on the guides
        m = tk.MB(f"crosshead_{'r' if side > 0 else 'l'}")
        m.boxc((0.14, 0.28, 0.18), "steel", loc=(0, 0, 0), bev=0.01)
        m.cyl(0.035, 0.6, "chrome", loc=(0, -0.3, 0), rot=(90, 0, 0), centre=True, sides=8)
        co = m.finish()
        co.parent = root
        rods[side] = (so, mo, co, x, a, Lm)
    _run_clip(root, wheels, rods, crank_r)
    return root


def _run_clip(root, wheels, rods, crank_r, frames=30):
    """One driver revolution (= pi * 1.575 m travelled). Wheels spin, rods + crossheads follow."""
    sc = bpy.context.scene
    sc.render.fps = 30
    yd0, yd1 = -3.3, -0.9
    ycross0 = -5.55 + 1.58 - 0.0   # crosshead mid position on the guides
    objs = [w for w, _ in wheels]
    for side, (so, mo, co, x, a, Lm) in rods.items():
        objs += [so, mo, co]
    for o in objs:
        o.animation_data_create()
        o.animation_data.action = bpy.data.actions.new(f"Run_{o.name}")
    for f in range(frames + 1):
        th = f / frames * math.tau
        for w, r_ in wheels:
            w.rotation_euler = (th * (DRIVER_R / r_), 0, 0)
            w.keyframe_insert("rotation_euler", frame=f)
        for side, (so, mo, co, x, a, Lm) in rods.items():
            ang = a + th
            cy, cz = math.cos(ang) * crank_r, math.sin(ang) * crank_r
            so.location = (x, (yd0 + yd1) / 2 + cy, DRIVER_R + cz)
            so.keyframe_insert("location", frame=f)
            pin = Vector((x + 0.06 * (1 if side > 0 else -1), yd1 + cy, DRIVER_R + cz))
            # crosshead slides on the guides at z = 0.98, y follows the rod
            dz = 0.98 - pin.z
            dy = -math.sqrt(max(Lm * Lm - dz * dz, 0.01))
            ch = Vector((pin.x, pin.y + dy, 0.98))
            co.location = (x + 0.0, ch.y - 0.02, 0.98)
            co.keyframe_insert("location", frame=f)
            mo.location = ch
            d = pin - ch
            mo.rotation_euler = (math.atan2(d.z, d.y), 0, 0)
            mo.keyframe_insert("location", frame=f)
            mo.keyframe_insert("rotation_euler", frame=f)
    for o in objs:
        act = o.animation_data.action
        try:
            for fc in act.fcurves:
                for kp in fc.keyframe_points:
                    kp.interpolation = "LINEAR"
        except AttributeError:  # layered actions (5.x)
            for layer in act.layers:
                for strip in layer.strips:
                    for cb in strip.channelbags:
                        for fc in cb.fcurves:
                            for kp in fc.keyframe_points:
                                kp.interpolation = "LINEAR"
        tr = o.animation_data.nla_tracks.new()
        tr.name = "Run"
        st = tr.strips.new("Run", 0, act)
        st.name = "Run"
        if hasattr(st, "action_slot") and getattr(act, "slots", None) and len(act.slots):
            try:
                st.action_slot = act.slots[0]
            except Exception:
                pass
        o.animation_data.action = None
    # rest pose = frame 0
    sc.frame_set(0)


# ------------------------------------------------------------------ cars

def _car_truck(mb, yc, r=CAR_R, z_frame=0.62):
    for sx in (-1, 1):
        mb.boxc((0.1, 2.1, 0.12), "cast_iron", loc=(sx * 0.98, yc, r + 0.05), bev=0.01)
        mb.span((sx * 0.98, yc - 1.0, r + 0.12), (sx * 0.98, yc, r - 0.15), 0.08, 0.05, "cast_iron", up=(1, 0, 0))
        mb.span((sx * 0.98, yc + 1.0, r + 0.12), (sx * 0.98, yc, r - 0.15), 0.08, 0.05, "cast_iron", up=(1, 0, 0))
        for dy in (-0.75, 0.75):
            mb.boxc((0.16, 0.24, 0.2), "cast_iron", loc=(sx * 0.98, yc + dy, r - 0.02), bev=0.01)
        for k in range(4):
            mb.boxc((0.3, 0.12, 0.022), "steel_dark", loc=(sx * 0.75, yc, z_frame - 0.12 + k * 0.03))
    mb.boxc((2.0, 0.3, 0.16), "wood_dark", loc=(0, yc, z_frame), bev=0.01)


def _wheelsets(root, ys, r=CAR_R):
    for i, yy in enumerate(ys):
        axle_set(root, f"wheels_{i}", yy, r, kind="disc")


def coach(seed=51):
    """Wooden passenger coach: clerestory roof, 11 windows a side with lit interiors, letterboard,
    end platforms with iron railings, steps and brake wheels, truss rods, two 4-wheel trucks."""
    b = B("coach", seed)
    mb = b.mb
    body = "wood_painted_green"
    yb0, yb1 = -7.0, 7.0           # body ends
    yp0, yp1 = -7.85, 7.85         # platform ends
    zf = 1.22                      # floor
    ze = 3.48                      # eave
    hw = 1.45                      # half width
    # underframe, truss rods, queen posts
    mb.boxc((2.7, yp1 - yp0, 0.24), "wood_dark", loc=(0, 0, zf - 0.12), bev=0.01)
    for sx in (-0.75, 0.75):
        for yy in (-2.2, 2.2):
            mb.boxc((0.08, 0.08, 0.36), "cast_iron", loc=(sx, yy, zf - 0.42))
        mb.tube([(sx, -6.6, zf - 0.2), (sx, -2.2, zf - 0.6), (sx, 2.2, zf - 0.6), (sx, 6.6, zf - 0.2)], 0.018, "steel_dark", sides=5)
    mb.boxc((0.5, 0.9, 0.5), "cast_iron", loc=(0.5, 0.0, zf - 0.55), bev=0.02)
    # body sides: lower panel, window band, letterboard
    win_n = 11
    pitch = (yb1 - yb0 - 0.8) / win_n
    for sx in (-1, 1):
        x = sx * hw
        mb.boxc((0.06, yb1 - yb0, 0.95), body, loc=(x, 0, zf + 0.475), bev=0.006)
        for i in range(win_n + 1):
            yy = yb0 + 0.4 + i * pitch
            mb.boxc((0.012, 0.07, 0.8), body, loc=(x + sx * 0.035, yy, zf + 0.5), skip="kd")
        mb.boxc((0.014, yb1 - yb0 - 0.6, 0.06), body, loc=(x + sx * 0.035, 0, zf + 0.12), skip="k")
        mb.boxc((0.07, yb1 - yb0, 0.05), "wood_dark", loc=(x, 0, zf + 0.97))
        zw0, zw1 = zf + 1.0, zf + 1.9
        for i in range(win_n + 1):
            yy = yb0 + 0.4 + i * pitch
            mb.boxc((0.06, 0.32 if i in (0, win_n) else 0.26, zw1 - zw0), body, loc=(x, yy, (zw0 + zw1) / 2))
        for i in range(win_n):
            ya, yb_ = yb0 + 0.4 + i * pitch + 0.13, yb0 + 0.4 + (i + 1) * pitch - 0.13
            ym = (ya + yb_) / 2
            mb.boxc((0.06, yb_ - ya, 0.12), body, loc=(x, ym, zw1 - 0.06))
            # arched head lights
            mb.poly([(x + sx * 0.001, ya, zw0), (x + sx * 0.001, yb_, zw0), (x + sx * 0.001, yb_, zw1 - 0.12),
                     (x + sx * 0.001, ya, zw1 - 0.12)], "glass", facing=(sx, 0, 0))
            with mb.at(M=T((x, 0, 0)) @ arch.Rz(90 if sx > 0 else -90)):
                u0, u1 = (ya, yb_) if sx > 0 else (-yb_, -ya)
                arch.interior_box(mb, u0, u1, zw0, zw1 - 0.12, 0.04, 0.9, 7, margin=0.05)
        mb.boxc((0.06, yb1 - yb0, ze - zw1), body, loc=(x, 0, zw1 + (ze - zw1) / 2))
        mb.boxc((0.08, yb1 - yb0 + 0.02, 0.05), "wood_dark", loc=(x, 0, zw1 + 0.02))
        b.lab.quad_uv([(x + sx * 0.042, -4.9 * sx, zw1 + 0.12), (x + sx * 0.042, 4.9 * sx, zw1 + 0.12),
                       (x + sx * 0.042, 4.9 * sx, zw1 + 0.42), (x + sx * 0.042, -4.9 * sx, zw1 + 0.42)], "label_train",
                      uvs=((0.02, 0.52), (0.98, 0.52), (0.98, 0.6), (0.02, 0.6)))
    # ends with doors
    for sy in (-1, 1):
        y = sy * (yb1 + 0.03)
        mb.boxc((2.9, 0.06, ze - zf), body, loc=(0, y, zf + (ze - zf) / 2), skip="")
        mb.boxc((0.8, 0.04, 2.0), "wood_dark", loc=(0, y + sy * 0.035, zf + 1.0), bev=0.01)
        mb.poly([(-0.25, y + sy * 0.06, zf + 1.15), (0.25, y + sy * 0.06, zf + 1.15), (0.25, y + sy * 0.06, zf + 1.8),
                 (-0.25, y + sy * 0.06, zf + 1.8)], "glass_dark", facing=(0, sy, 0))
        b.lab.quad_uv([(sy * 0.5, y + sy * 0.065, ze - 0.42), (sy * -0.5, y + sy * 0.065, ze - 0.42),
                       (sy * -0.5, y + sy * 0.065, ze - 0.2), (sy * 0.5, y + sy * 0.065, ze - 0.2)], "label_train",
                      uvs=((0.55, 0.64), (0.96, 0.64), (0.96, 0.74), (0.55, 0.74)))
        # platform, railings, steps, brake staff, lamp
        yp = sy * (yp1 - 0.42)
        mb.boxc((2.7, 0.85, 0.06), "wood_planks", loc=(0, yp, zf - 0.03))
        for sx in (-1, 1):
            mb.tube([(sx * 1.3, y + sy * 0.05, zf + 1.0), (sx * 1.3, yp + sy * 0.36, zf + 1.0), (sx * 0.5, yp + sy * 0.4, zf + 1.0)],
                    0.02, "cast_iron", sides=5)
            for k in range(4):
                yy = y + sy * (0.1 + k * 0.22)
                mb.span((sx * 1.3, yy, zf), (sx * 1.3, yy, zf + 1.0), 0.02, 0.02, "cast_iron")
            for k in range(2):
                zz = zf - 0.32 - k * 0.3
                mb.boxc((0.45, 0.28, 0.04), "steel_dark", loc=(sx * 1.08, yp + sy * 0.25, zz))
            mb.span((sx * 1.3, yp + sy * 0.4, zf - 0.7), (sx * 1.3, yp + sy * 0.4, zf), 0.04, 0.04, "steel_dark")
        mb.cyl(0.02, 1.2, "cast_iron", loc=(0.7 * sy, yp + sy * 0.3, zf), sides=6)
        mb.ring(0.16, 0.19, 0.025, "cast_iron", loc=(0.7 * sy, yp + sy * 0.3, zf + 1.2), sides=14)
        for k in range(4):
            a = k * math.pi / 4
            mb.span((0.7 * sy + math.cos(a) * 0.17, yp + sy * 0.3 + math.sin(a) * 0.17, zf + 1.21),
                    (0.7 * sy - math.cos(a) * 0.17, yp + sy * 0.3 - math.sin(a) * 0.17, zf + 1.21), 0.015, 0.015, "cast_iron")
        mb.boxc((2.6, 0.3, 0.38), "wood_dark", loc=(0, sy * (yp1 + 0.1), zf - 0.32), bev=0.02)
        mb.boxc((0.18, 0.4, 0.16), "cast_iron", loc=(0, sy * (yp1 + 0.35), zf - 0.35), bev=0.01)
    # roof: lower deck + clerestory with small windows + overhanging hoods over the platforms
    rw = 1.0
    for sx in (-1, 1):
        mb.poly([(sx * (hw + 0.12), yp0 - 0.1, ze), (sx * (hw + 0.12), yp1 + 0.1, ze), (sx * rw, yp1 + 0.1, ze + 0.28),
                 (sx * rw, yp0 - 0.1, ze + 0.28)], "canvas", thick=0.04, facing=(sx * 0.3, 0, 1))
        for i in range(10):
            yy = yb0 + 0.6 + i * (yb1 - yb0 - 1.2) / 9
            mb.poly([(sx * rw, yy - 0.28, ze + 0.32), (sx * rw, yy + 0.28, ze + 0.32), (sx * rw, yy + 0.28, ze + 0.52),
                     (sx * rw, yy - 0.28, ze + 0.52)], "glass_dark", facing=(sx, 0, 0))
        mb.poly([(sx * rw, yb0 + 0.3, ze + 0.27), (sx * rw, yb1 - 0.3, ze + 0.27), (sx * rw, yb1 - 0.3, ze + 0.6),
                 (sx * rw, yb0 + 0.3, ze + 0.6)], body, facing=(sx, 0, 0))
        mb.poly([(sx * (rw + 0.08), yb0 + 0.2, ze + 0.6), (sx * (rw + 0.08), yb1 - 0.2, ze + 0.6), (0.0, yb1 - 0.2, ze + 0.82),
                 (0.0, yb0 + 0.2, ze + 0.6 + 0.22)], "canvas", thick=0.04, facing=(sx * 0.3, 0, 1))
    for sy in (-1, 1):
        yy = sy * (yb1 - 0.3)
        mb.poly([(-rw, yy, ze + 0.27), (rw, yy, ze + 0.27), (rw, yy, ze + 0.6), (0, yy, ze + 0.82), (-rw, yy, ze + 0.6)], body,
                facing=(0, sy, 0))
        mb.poly([(-rw - 0.08, yy, ze + 0.6), (rw + 0.08, yy, ze + 0.6), (rw * 0.4, sy * (yp1 + 0.1), ze + 0.36),
                 (-rw * 0.4, sy * (yp1 + 0.1), ze + 0.36)], "canvas", thick=0.04, facing=(0, sy * 0.4, 1))
    for i in range(4):
        mb.cyl(0.07, 0.2, "steel_dark", loc=(0, -5.0 + i * 3.3, ze + 0.8), sides=8)
        mb.cyl(0.11, 0.06, "steel_dark", loc=(0, -5.0 + i * 3.3, ze + 1.0), r2=0.02, sides=8)
    for yy in (-5.25, 5.25):
        _car_truck(mb, yy)
    root = b.finish()
    _wheelsets(root, (-6.0, -4.5, 4.5, 6.0))
    return root


def boxcar(seed=61):
    """Wooden boxcar: vertical sheathing with outside truss bracing, sliding door, roof walk,
    ladders, brake wheel, truss rods, arch-bar trucks."""
    b = B("boxcar", seed)
    mb = b.mb
    red = "wood_painted_red"
    hl, hw = 5.2, 1.42
    zf, zr = 1.2, 3.78
    mb.boxc((2.7, 2 * hl + 0.4, 0.26), "wood_dark", loc=(0, 0, zf - 0.13), bev=0.01)
    for sx in (-0.7, 0.7):
        mb.tube([(sx, -4.8, zf - 0.2), (sx, -1.8, zf - 0.6), (sx, 1.8, zf - 0.6), (sx, 4.8, zf - 0.2)], 0.018, "steel_dark",
                sides=5)
    # body box (sides as battened sheathing)
    for sx in (-1, 1):
        with b.at(arch.WF(sx * hw, -hl * sx, 0, 90 if sx > 0 else -90)):
            ops = [arch.Op(hl - 0.95, hl + 0.95, zf, zr - 0.35)]
            arch.flat_wall(mb, 2 * hl, zf, zr, ops, red, grain=(0, 0, 1), tone=0.95)
            # outside truss: posts + diagonals
            for u in (0.08, 1.6, 3.3, 2 * hl - 3.3, 2 * hl - 1.6, 2 * hl - 0.08):
                mb.boxc((0.1, 0.08, zr - zf), red, loc=(u, -0.04, (zf + zr) / 2), skip="k", bev=0.008)
            for (ua, ub) in ((0.08, 1.6), (1.6, 3.3), (2 * hl - 1.6, 2 * hl - 0.08), (2 * hl - 3.3, 2 * hl - 1.6)):
                if ub <= 3.3:
                    mb.span((ua, -0.04, zf + 0.05), (ub, -0.04, zr - 0.05), 0.1, 0.07, red, up=(0, -1, 0))
                else:
                    mb.span((ua, -0.04, zr - 0.05), (ub, -0.04, zf + 0.05), 0.1, 0.07, red, up=(0, -1, 0))
            mb.boxc((2 * hl, 0.1, 0.14), red, loc=(hl, -0.05, zr - 0.07), skip="k")
            mb.boxc((2 * hl, 0.1, 0.14), red, loc=(hl, -0.05, zf + 0.07), skip="k")
            # sliding door, a little open, on its rail
            arch.interior_box(mb, hl - 0.95, hl + 0.95, zf, zr - 0.35, 0.05, 1.3, 6, margin=0.05)
            dx = hl + 0.55
            mb.boxc((1.9, 0.06, zr - zf - 0.32), red, loc=(dx, -0.16, zf + (zr - zf - 0.32) / 2), skip="")
            for zz in (zf + 0.15, zf + 1.25, zr - 0.5):
                mb.boxc((1.9, 0.03, 0.12), red, loc=(dx, -0.2, zz))
            mb.span((dx - 0.9, -0.2, zf + 0.25), (dx + 0.9, -0.2, zr - 0.6), 0.1, 0.03, red, up=(0, -1, 0))
            mb.boxc((4.2, 0.06, 0.07), "steel_dark", loc=(hl + 0.6, -0.17, zr - 0.25))
            mb.boxc((4.2, 0.06, 0.05), "steel_dark", loc=(hl + 0.6, -0.17, zf + 0.03))
            b.lab.quad_uv([(1.0, -0.085, zf + 1.4), (3.9, -0.085, zf + 1.4), (3.9, -0.085, zf + 1.85), (1.0, -0.085, zf + 1.85)],
                          "label_train", uvs=((0.04, 0.38), (0.96, 0.38), (0.96, 0.47), (0.04, 0.47)))
            b.lab.quad_uv([(1.0, -0.085, zf + 1.05), (3.9, -0.085, zf + 1.05), (3.9, -0.085, zf + 1.25), (1.0, -0.085, zf + 1.25)],
                          "label_train", uvs=((0.04, 0.3), (0.96, 0.3), (0.96, 0.36), (0.04, 0.36)))
    for sy in (-1, 1):
        y = sy * hl
        with b.at(arch.WF(hw * sy, y, 0, 0 if sy < 0 else 180)):
            arch.flat_wall(mb, 2 * hw, zf, zr, [], red, grain=(0, 0, 1), tone=0.95)
            for u in (0.1, hw, 2 * hw - 0.1):
                mb.boxc((0.12, 0.08, zr - zf), red, loc=(u, -0.04, (zf + zr) / 2), skip="k")
            # ladder
            for k in range(8):
                mb.boxc((0.42, 0.03, 0.03), "steel_dark", loc=(0.45, -0.12, zf + 0.25 + k * 0.32))
            for u in (0.24, 0.66):
                mb.boxc((0.03, 0.09, zr - zf - 0.1), "steel_dark", loc=(u, -0.07, (zf + zr) / 2))
        mb.boxc((2.6, 0.3, 0.36), "wood_dark", loc=(0, sy * (hl + 0.25), zf - 0.3), bev=0.02)
        mb.boxc((0.18, 0.4, 0.16), "cast_iron", loc=(0, sy * (hl + 0.5), zf - 0.33), bev=0.01)
    # roof: shallow gable, running board, brake wheel
    for sx in (-1, 1):
        mb.poly([(sx * (hw + 0.1), -hl - 0.1, zr), (sx * (hw + 0.1), hl + 0.1, zr), (0, hl + 0.1, zr + 0.22), (0, -hl - 0.1, zr + 0.22)],
                red, thick=0.05, facing=(sx * 0.2, 0, 1), grain_dir=(1, 0, 0))
    mb.boxc((0.5, 2 * hl + 0.2, 0.04), "wood_planks", loc=(0, 0, zr + 0.3), uvoff=True)
    for k in range(9):
        mb.boxc((0.06, 0.06, 0.1), "wood_dark", loc=(0, -hl + 0.2 + k * (2 * hl - 0.4) / 8, zr + 0.22))
    mb.cyl(0.02, 0.6, "cast_iron", loc=(0.5, hl - 0.15, zr + 0.1), sides=6)
    mb.ring(0.2, 0.23, 0.03, "cast_iron", loc=(0.5, hl - 0.15, zr + 0.7), sides=16)
    for k in range(3):
        a = k * math.pi / 3
        mb.span((0.5 + math.cos(a) * 0.21, hl - 0.15 + math.sin(a) * 0.21, zr + 0.715),
                (0.5 - math.cos(a) * 0.21, hl - 0.15 - math.sin(a) * 0.21, zr + 0.715), 0.02, 0.02, "cast_iron")
    for yy in (-3.6, 3.6):
        _car_truck(mb, yy)
    root = b.finish()
    _wheelsets(root, (-4.35, -2.85, 2.85, 4.35))
    return root


NODES = {"track_10m": track_10m, "buffer_stop": buffer_stop, "locomotive": locomotive, "coach": coach, "boxcar": boxcar}
