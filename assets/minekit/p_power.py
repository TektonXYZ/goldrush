"""ore_cart, generator, fuel_tank (Blender coords: front = -Y = three.js +Z, origin bottom centre)."""
import math

from mathutils import Matrix, Vector, noise

import mk
import parts as P
from mk import DEG, MB, child, empty, frame, rotm, trs

BUILD = {}


def node(name, kind="floor", **meta):
    def deco(fn):
        BUILD[name] = (fn, dict(kind=kind, **meta))
        return fn
    return deco


def offset_poly(pts, t):
    """Offset an open 2D polyline [(x, z)] by t along its left normal."""
    out = []
    n = len(pts)
    for i in range(n):
        a = Vector(pts[max(i - 1, 0)])
        b = Vector(pts[min(i + 1, n - 1)])
        d = (b - a).normalized()
        nrm = Vector((-d.y, d.x))
        out.append((pts[i][0] + nrm.x * t, pts[i][1] + nrm.y * t))
    return out


# ====================================================================== ore_cart
WHEEL_R = 0.15


def wheel_mesh(name, side):
    """Cast flanged mine-car wheel, axis = local X, flange toward the track centre."""
    wb = MB(name)
    W, F, hr, hw, rt = 0.075, 0.022, 0.05, 0.11, WHEEL_R
    web = [(0.0, -hw / 2), (hr, -hw / 2), (hr * 1.18, -0.013), (rt * 0.78, -0.013), (rt - 0.012, -W / 2 + 0.004)]
    rim = [(rt - 0.012, -W / 2 + 0.004), (rt + F * 0.55, -W / 2 - 0.004), (rt + F, -W / 2 + 0.008),
           (rt + F * 0.72, -W / 2 + 0.02), (rt + 0.001, -W / 2 + 0.03), (rt * 0.985, W / 2), (rt * 0.8, W / 2 - 0.004)]
    web2 = [(rt * 0.8, W / 2 - 0.004), (rt * 0.78, 0.013), (hr * 1.18, 0.013), (hr, hw / 2), (0.0, hw / 2)]
    Mx = rotm((0, -90 if side < 0 else 90, 0))
    wb.lathe(web, "cast_iron", sides=12, Mx=Mx)
    wb.lathe(rim, "steel", sides=12, Mx=Mx)
    wb.lathe(web2, "cast_iron", sides=12, Mx=Mx)
    # axle nut + split pin on the outer face
    out = Vector((-side * -1, 0, 0)) * 1.0
    P.hexnut(wb, Vector((side * (hw / 2), 0, 0)), 0.024, 0.02, (side, 0, 0), "steel_dark")
    return wb.finish()


@node("ore_cart", "floor", grime=dict(streaks=0.16, dirt=0.3),
      notes="origin = rail-top contact plane (place at y=0.200 on rail_2m, wheel flanges reach 0.022 below it); "
            "wheel_0..3 spin about local X (roll forward = positive rotation.x for +Z travel)")
def ore_cart():
    mb = MB("ore_cart")
    rng = mb.rng
    gx, ay, zc = 0.3125, 0.36, WHEEL_R
    # ---------------------------------------------------------------- chassis
    for s in (-1, 1):
        x0 = s * 0.215
        w, h, t = 0.05, 0.12, 0.008
        prof = [(0, 0), (w, 0), (w, t), (t, t), (t, h - t), (w, h - t), (w, h), (0, h)]
        mb.extrude([(x0 + s * px, 0.17 + pz) for px, pz in prof], -0.79, 0.79, "steel_dark")
        for y in (-ay, ay):
            mb.boxc((s * 0.222, y, 0.155), (0.055, 0.15, 0.12), "cast_iron", bevel=0.01, seg=2)
            for dy in (-0.05, 0.05):
                P.bolt(mb, (s * 0.2495, y + dy, 0.19), (s, 0, 0), r=0.007, head=0.011, stud=0.0, washer=False)
    for y in (-ay, ay):
        mb.rod((-0.255, y, zc), (0.255, y, zc), 0.027, "steel_dark", sides=10)
    for s in (-1, 1):
        mb.boxc((0, s * 0.81, 0.25), (0.66, 0.06, 0.16), "steel_dark", bevel=0.008, seg=2)
        mb.boxc((0, s * 0.865, 0.255), (0.17, 0.055, 0.12), "cast_iron", bevel=0.012, seg=2)
        mb.rod((0, s * 0.885, 0.335), (0, s * 0.885, 0.19), 0.012, "steel", sides=8)
        mb.cyl(0.02, 0.012, "steel", sides=8, loc=(0, s * 0.885, 0.335))
        for x in (-0.26, 0.26):
            P.bolt(mb, (x, s * 0.84, 0.25), (0, s, 0), r=0.008, head=0.013, stud=0.0)
    for y in (-0.53, 0.53):
        mb.boxc((0, y, 0.335), (0.5, 0.09, 0.09), "steel_dark", bevel=0.008, seg=1)
        mb.boxc((0, y, 0.405), (0.26, 0.06, 0.07), "steel_dark", bevel=0.006, seg=1)
    # coupling: 3-link chain hanging from the front pin, hook at the rear
    P.chain(mb, (0, -0.905, 0.26), (0.03, -1.0, 0.1), link_len=0.1, wire=0.011, mat="steel_dark", sides=5, segs=8)
    hook = [Vector((0, 0.885, 0.27)), Vector((0, 0.95, 0.27)), Vector((0, 0.985, 0.25)), Vector((0, 0.99, 0.21)),
            Vector((0, 0.97, 0.18)), Vector((0, 0.94, 0.19))]
    mb.tube(hook, 0.014, "steel_dark", sides=8)
    # ---------------------------------------------------------------- V-skip body
    R = [(0.49, 1.08), (0.405, 0.95), (0.32, 0.82), (0.235, 0.69), (0.165, 0.585), (0.105, 0.51), (0.05, 0.468),
         (0.0, 0.455)]
    outer = [(-x, z) for x, z in R] + [(x, z) for x, z in reversed(R[:-1])]
    inner = offset_poly(outer, -0.007)  # left normal points down/out for this direction -> negative = inward
    # make sure inner is inside (closer to the axis/up)
    if inner[len(inner) // 2][1] < outer[len(outer) // 2][1]:
        inner = offset_poly(outer, 0.007)
    prof = outer + list(reversed(inner))
    N = len(outer)
    mats = ["paint_red"] * (N - 1) + ["paint_red"] + ["rust"] * (N - 1) + ["paint_red"]
    dents = [(Vector((0.33, -0.28, 0.84)), 0.13, 0.022), (Vector((-0.27, 0.38, 0.74)), 0.11, 0.018),
             (Vector((0.2, 0.55, 0.64)), 0.09, 0.012), (Vector((-0.4, -0.5, 0.97)), 0.08, 0.014)]

    def dent(v):
        for c, rad, dep in dents:
            d = (v - c).length
            if d < rad:
                k = (1 - (d / rad) ** 2) ** 2
                v.x -= math.copysign(dep * k, v.x) * (1.0 if abs(v.x) > 0.05 else 0.0)
                v.z += dep * k * 0.4
        return v
    mb.extrude(prof, -0.75, 0.75, mats, segs=8, caps=True, warp=dent)
    # end plates (outer painted, inner rusted) + rolled rims
    end_pts = [(-0.49, 1.08)] + [(x, z) for x, z in outer[1:-1]] + [(0.49, 1.08)]
    for s in (-1, 1):
        y = s * 0.752
        pts = [Vector((x, y, z)) for x, z in end_pts]
        if s > 0:
            pts = list(reversed(pts))
        mb.poly(pts, "paint_red", thick=0.008)
        ip = [Vector((x * 0.985, y - s * 0.0095, z + 0.004)) for x, z in end_pts]
        if s < 0:
            ip = list(reversed(ip))
        mb.poly(ip, "rust")
        mb.rod((-0.505, y, 1.08), (0.505, y, 1.08), 0.019, "paint_red", sides=8)
    for s in (-1, 1):
        mb.rod((s * 0.49, -0.77, 1.08), (s * 0.49, 0.77, 1.08), 0.02, "paint_red", sides=8)
    # stiffening ribs following the V sides
    side_path = [(x, z) for x, z in R[:-1]]
    for s in (-1, 1):
        for y in (-0.42, 0.0, 0.42):
            pts = []
            for i, (x, z) in enumerate(side_path):
                a = Vector(side_path[max(i - 1, 0)])
                b = Vector(side_path[min(i + 1, len(side_path) - 1)])
                d = (b - a).normalized()
                nrm = Vector((d.y, -d.x)) if d.y < 0 else Vector((-d.y, d.x))
                if nrm.x < 0:
                    nrm = -nrm
                pts.append(Vector((s * (x + nrm.x * 0.007), y, z + nrm.y * 0.007)))
            mb.sweep([(-0.007, -0.028), (0.007, -0.028), (0.007, 0.028), (-0.007, 0.028)], pts, "paint_red", up=(0, 1, 0))
    # tipping latch + handles + maker plate
    mb.rod((0.32, -0.765, 0.94), (0.32, -0.86, 1.02), 0.011, "steel_dark", sides=8)
    mb.cyl(0.02, 0.05, "steel_dark", sides=8, Mx=trs((0.32, -0.86, 1.02), (60, 0, 0)))
    mb.boxc((0.3, -0.79, 0.84), (0.08, 0.05, 0.06), "steel_dark", bevel=0.006, seg=1)
    for x in (-0.3, 0.3):
        P.handle_bar(mb, Vector((x - 0.09, 0.76, 0.98)), Vector((x + 0.09, 0.76, 0.98)), (0, 1, 0), stand=0.06, r=0.011,
                     mat="steel_dark")
    mb.label("sutter_plate", (-0.17, -0.7575, 0.86), 0.22)
    mb.boxc((-0.17, -0.7545, 0.86), (0.235, 0.004, 0.085), "cast_iron", bevel=0.002, seg=1)
    root = mb.finish()
    for i, (x, y) in enumerate(((-gx, -ay), (gx, -ay), (-gx, ay), (gx, ay))):
        w = wheel_mesh(f"wheel_{i}", -1 if x < 0 else 1)
        child(w, root, (x, y, zc))
    return root


# ====================================================================== generator
@node("generator", "floor", grime=dict(dirt=0.28),
      notes="Ironside IP-150 genset, long axis X, control panel + doors on the +Z face; empties exhaust (tailpipe tip, "
            "smoke up +Y) and snd (engine centre); child status_light (emit_green) on the control panel")
def generator():
    mb = MB("generator")
    rng = mb.rng
    L, D = 3.44, 1.36
    z0, z1 = 0.2, 1.82
    yf = -D / 2  # front face
    # ---------------------------------------------------------------- skid
    for s in (-1, 1):
        w, h, t = 0.09, 0.2, 0.01
        prof = [(0, 0), (w, 0), (w, t), (t, t), (t, h - t), (w, h - t), (w, h), (0, h)]
        y0 = s * 0.63
        mb.extrude([(y0 + s * px, pz) for px, pz in prof], -1.8, 1.8, "paint_black", Mx=Matrix.Rotation(-math.pi / 2, 4, "Z"))
    for x in (-1.6, -0.55, 0.55, 1.6):
        mb.boxc((x, 0, 0.1), (0.14 if abs(x) > 1 else 0.22, 1.26, 0.16 if abs(x) > 1 else 0.13), "paint_black", bevel=0.006)
    for x in (-0.55, 0.55):  # forklift pocket mouths
        for s in (-1, 1):
            mb.boxc((x, s * 0.725, 0.1), (0.24, 0.02, 0.14), "paint_black", bevel=0.004)
            mb.boxc((x, s * 0.736, 0.1), (0.2, 0.004, 0.1), "steel_dark")
    for x in (-1.74, 1.74):
        for s in (-1, 1):
            mb.boxc((x, s * 0.63, 0.27), (0.1, 0.025, 0.14), "paint_black", bevel=0.005, seg=1)
            P.ring(mb, (x, s * 0.63, 0.3), 0.03, 0.009, axis=(0, 1, 0), mat="steel_dark", segs=10, sides=6)
    # ---------------------------------------------------------------- enclosure
    mb.box((L, D, z1 - z0), "paint_yellow", loc=(0, 0, z0), bevel=0.012, seg=2, cuts=(3, 1, 2))
    mb.box((L + 0.06, D + 0.06, 0.05), "paint_yellow", loc=(0, 0, z1), bevel=0.012, seg=2)
    mb.box((L - 0.2, D - 0.2, 0.04), "paint_yellow", loc=(0, 0, z1 + 0.05), bevel=0.01, seg=1)
    P.ring(mb, (0, 0, z1 + 0.13), 0.045, 0.012, axis=(1, 0, 0), mat="steel_dark", segs=12)
    mb.boxc((0, 0, z1 + 0.1), (0.14, 0.05, 0.03), "steel_dark", bevel=0.005)
    # corner posts (folded steel)
    for x in (-L / 2, L / 2):
        for s in (-1, 1):
            mb.boxc((x, s * D / 2, (z0 + z1) / 2), (0.05, 0.05, z1 - z0), "paint_yellow", bevel=0.008, seg=2)

    def door(xc, w, zb, zt, face_y, nrm, louvre_rows=8, handle_side=1):
        sgn = 1 if nrm > 0 else -1
        y = face_y + sgn * 0.008
        Mx = Matrix.Translation((xc, y, (zb + zt) / 2))
        if sgn > 0:
            Mx = Mx @ rotm((0, 0, 180))
        mb.box((w, 0.016, zt - zb), "paint_yellow", center=True, Mx=Mx, bevel=0.006, seg=2)
        lz = zt - 0.08 - 0.25
        P.louvres(mb, Vector((xc, y + sgn * 0.012, lz)), w - 0.18, 0.42, 7, "paint_yellow", depth=0.02,
                  angle=38, rot=(0, 0, 180 if sgn > 0 else 0))
        P.louvres(mb, Vector((xc, y + sgn * 0.012, zb + 0.28)), w - 0.18, 0.3, 5, "paint_yellow", depth=0.02,
                  angle=38, rot=(0, 0, 180 if sgn > 0 else 0))
        hx = xc - handle_side * (w / 2 - 0.035)
        for hz in (zb + 0.14, (zb + zt) / 2, zt - 0.14):
            mb.rod((hx, y + sgn * 0.012, hz - 0.05), (hx, y + sgn * 0.012, hz + 0.05), 0.013, "steel_dark", sides=6)
        # T-handle lock
        tx = xc + handle_side * (w / 2 - 0.09)
        mb.cyl(0.03, 0.012, "steel_dark", sides=10, Mx=trs((tx, y + sgn * 0.008, (zb + zt) / 2), (90 * sgn * -1, 0, 0)))
        mb.rod((tx, y + sgn * 0.01, (zb + zt) / 2), (tx, y + sgn * 0.045, (zb + zt) / 2), 0.008, "steel", sides=8)
        mb.rod((tx, y + sgn * 0.045, (zb + zt) / 2 - 0.06), (tx, y + sgn * 0.045, (zb + zt) / 2 + 0.06), 0.009, "steel",
               sides=8, bevel=0.002)
    # front: control panel bay at -X, then two doors
    door(-0.23, 1.16, 0.32, 1.52, yf, -1, handle_side=1)
    door(1.0, 1.16, 0.32, 1.52, yf, -1, handle_side=-1)
    # back: two doors
    door(-0.62, 1.16, 0.32, 1.52, D / 2, 1, handle_side=1)
    door(0.62, 1.16, 0.32, 1.52, D / 2, 1, handle_side=-1)
    # radiator end (+X): grille frame + slats over a dark core
    gx = L / 2
    mb.boxc((gx + 0.004, 0, 1.0), (0.012, 1.18, 1.3), "steel_dark")
    for z in [0.42 + 0.09 * k for k in range(14)]:
        mb.box((0.004, 1.16, 0.06), "paint_yellow", center=True, Mx=trs((gx + 0.02, 0, z), (0, -35, 0)))
    for (cy, cz, sy, sz) in ((0, 1.66, 1.26, 0.06), (0, 0.34, 1.26, 0.06), (-0.6, 1.0, 0.06, 1.38), (0.6, 1.0, 0.06, 1.38),
                             (0, 1.0, 0.04, 1.3)):
        mb.boxc((gx + 0.025, cy, cz), (0.035, sy, sz), "paint_yellow", bevel=0.006, seg=1)
    # alternator end (-X): intake louvres + cable terminal box with two power cables to the floor
    P.louvres(mb, Vector((-L / 2 - 0.012, 0.25, 1.25)), 0.7, 0.8, 10, "paint_yellow", depth=0.02, angle=38, rot=(0, 0, -90))
    mb.boxc((-L / 2 - 0.08, -0.28, 0.62), (0.16, 0.42, 0.38), "paint_yellow", bevel=0.012, seg=2)
    for i, dy in enumerate((-0.37, -0.19)):
        mb.cyl(0.032, 0.05, "plastic_black", sides=10, loc=(-L / 2 - 0.12, dy, 0.38), rot=(0, 0, 0), r2=0.028)
        pts = [Vector((-L / 2 - 0.12, dy, 0.42)), Vector((-L / 2 - 0.12, dy, 0.3)), Vector((-L / 2 - 0.14, dy, 0.12)),
               Vector((-L / 2 - 0.24, dy - 0.02 * i, 0.035)), Vector((-L / 2 - 0.42, dy - 0.05 - 0.03 * i, 0.032)),
               Vector((-L / 2 - 0.5, dy - 0.1, 0.032))]
        mb.tube(pts, 0.026, "cable", sides=10)
    mb.label("warn_hv", (-L / 2 - 0.1615, -0.28, 0.66), 0.13, rot=(0, 0, -90))
    # ---------------------------------------------------------------- control panel
    # layout matches the gen_panel caption overlay (0.6 x 0.375 m, centred cz + 0.02)
    cx, cz = -1.27, 1.2
    mb.boxc((cx, yf - 0.07, cz), (0.72, 0.14, 0.66), "paint_yellow", bevel=0.012, seg=2)
    face = yf - 0.141
    mb.boxc((cx, face + 0.004, cz), (0.64, 0.008, 0.6), "plastic_black", bevel=0.003, seg=1)
    mb.label("gen_panel", (cx, face - 0.0015, cz + 0.02), 0.6)
    cols = [cx - 0.225, cx - 0.1125, cx, cx + 0.1125]
    for dx, nm in zip(cols[:3], ("dial_oil", "dial_temp", "dial_volts")):
        dz = cz + 0.08
        mb.lathe([(0.0, 0.0), (0.05, 0.0), (0.054, 0.004), (0.054, 0.016), (0.046, 0.02)], "steel", sides=16,
                 Mx=trs((dx, face, dz), (90, 0, 0)))
        mb.label(nm, (dx, face - 0.003, dz), 0.088, 0.088)
    mb.boxc((cols[3], face - 0.006, cz + 0.08), (0.11, 0.012, 0.05), "plastic_black", bevel=0.003)
    mb.label("hourmeter", (cols[3], face - 0.0125, cz + 0.08), 0.1)
    # second row: key switch, auto/man toggle, breaker, preheat push button
    rz = cz - 0.08
    mb.cyl(0.026, 0.02, "steel", sides=12, Mx=trs((cx - 0.225, face, rz), (90, 0, 0)))
    mb.box((0.006, 0.03, 0.022), "brass", center=True, loc=(cx - 0.225, face - 0.032, rz))
    mb.cyl(0.012, 0.012, "steel", sides=8, Mx=trs((cx - 0.094, face, rz), (90, 0, 0)))
    mb.rod((cx - 0.094, face - 0.01, rz), (cx - 0.094, face - 0.045, rz + 0.018), 0.0045, "steel", sides=6)
    mb.boxc((cx + 0.04, face - 0.02, rz), (0.05, 0.035, 0.09), "plastic_black", bevel=0.004)
    mb.box((0.02, 0.03, 0.012), "paint_red", center=True, loc=(cx + 0.04, face - 0.045, rz + 0.012))
    mb.cyl(0.02, 0.016, "steel", sides=10, Mx=trs((cx + 0.216, face, rz), (90, 0, 0)))
    mb.cyl(0.014, 0.012, "paint_green", sides=10, Mx=trs((cx + 0.216, face - 0.016, rz), (90, 0, 0)))
    # below the overlay: maker logo + emergency stop
    ex, ez = cx + 0.2, cz - 0.235
    mb.label("estop_plate", (ex, face - 0.002, ez), 0.11, 0.11)
    mb.lathe([(0.0, 0.0), (0.022, 0.0), (0.022, 0.028), (0.034, 0.03), (0.038, 0.038), (0.034, 0.05), (0.018, 0.056),
              (0.0, 0.058)], "paint_red", sides=16, Mx=trs((ex, face, ez), (90, 0, 0)))
    mb.label("ironside_logo", (cx - 0.1, face - 0.0015, ez), 0.3)
    # status light guard on the housing top (lens = child)
    sl = Vector((cx + 0.22, yf - 0.08, cz + 0.33))
    mb.cyl(0.04, 0.02, "plastic_black", sides=12, loc=sl)
    for k in range(4):
        a = k * math.pi / 2 + math.pi / 4
        mb.tube([sl + Vector((math.cos(a) * 0.042, math.sin(a) * 0.042, 0.02)),
                 sl + Vector((math.cos(a) * 0.045, math.sin(a) * 0.045, 0.06)),
                 sl + Vector((math.cos(a) * 0.02, math.sin(a) * 0.02, 0.082)), sl + Vector((0, 0, 0.085))], 0.003,
                "steel_dark", sides=4)
    # ---------------------------------------------------------------- exhaust: silencer on the roof + tailpipe
    sx0, sx1, sy, sz = 0.15, 1.15, 0.28, z1 + 0.32
    for x in (sx0 + 0.15, sx1 - 0.15):
        mb.boxc((x, sy, z1 + 0.11), (0.06, 0.32, 0.12), "steel_dark", bevel=0.005)
        mb.rod((x - 0.03, sy, sz), (x + 0.03, sy, sz), 0.172, "steel_dark", sides=16, cap=False)
    mb.rod((sx0, sy, sz), (sx1, sy, sz), 0.16, "steel_dark", sides=18, bevel=0.012)
    mb.rod((sx0 - 0.0, sy, sz), (sx0 - 0.05, sy, sz), 0.055, "steel_dark", sides=10)
    mb.tube([Vector((sx0 - 0.05, sy, sz)), Vector((sx0 - 0.14, sy, sz)), Vector((sx0 - 0.2, sy, sz - 0.05)),
             Vector((sx0 - 0.22, sy, sz - 0.15)), Vector((sx0 - 0.22, sy, z1 + 0.06))], 0.05, "steel_dark", sides=10)
    tip0 = Vector((sx1 + 0.05, sy, sz))
    pipe = [Vector((sx1, sy, sz)), tip0, Vector((sx1 + 0.13, sy, sz + 0.03)), Vector((sx1 + 0.17, sy, sz + 0.12)),
            Vector((sx1 + 0.18, sy, sz + 0.55))]
    mb.tube(pipe, 0.048, "rust", sides=12)
    tip = pipe[-1]
    # open tip: a short collar ring leaves the pipe visibly hollow
    P.ring(mb, tip, 0.045, 0.006, axis=(0, 0, 1), mat="rust", segs=14, sides=6)
    mb.cyl(0.042, 0.04, "steel_dark", sides=12, loc=tip - Vector((0, 0, 0.06)), cap=False)
    mb.label("warn_hot", (0.65, sy - 0.161 - 0.006, sz - 0.02), 0.09, rot=(0, 0, 0))
    # fuel line from the skid fitting at +X front to the floor
    fl = [Vector((1.64, yf - 0.01, 0.26)), Vector((1.64, yf - 0.06, 0.25)), Vector((1.67, yf - 0.12, 0.17)),
          Vector((1.72, yf - 0.14, 0.04)), Vector((1.84, yf - 0.06, 0.02)), Vector((1.9, yf + 0.12, 0.02))]
    mb.cyl(0.018, 0.04, "brass", sides=8, Mx=trs(fl[0], (90, 0, 0)))
    mb.tube(fl, 0.012, "rubber", sides=8)
    mb.rod(fl[-1], fl[-1] + Vector((0.06, 0.04, 0)), 0.016, "brass", sides=8)
    # decals: maker band, model, warnings
    mb.label("ironside_logo", (0.38, yf - 0.002, 1.66), 1.0)
    mb.label("genset_model", (1.36, yf - 0.002, 1.66), 0.42)
    mb.label("ironside_logo", (-0.1, D / 2 + 0.002, 1.66), 1.0, rot=(0, 0, 180))
    mb.label("warn_ear", (-0.66, yf - 0.019, 0.865), 0.1)
    mb.label("nosmoking", (1.45, yf - 0.019, 0.865), 0.1)
    mb.label("keep_clear", (0.72, D / 2 + 0.019, 1.18), 0.3, rot=(0, 0, 180))
    root = mb.finish()
    # status light lens (child)
    lb = MB("status_light")
    lb.lathe([(0.0, 0.05), (0.018, 0.046), (0.03, 0.03), (0.034, 0.0), (0.0, 0.0)], "emit_green", sides=12)
    lens = lb.finish(grime=False)
    child(lens, root, (sl.x, sl.y, sl.z + 0.02))
    empty("exhaust", (tip.x, tip.y, tip.z), parent=root)
    empty("snd", (0.0, 0.0, 1.0), parent=root)
    return root


# ====================================================================== fuel_tank
@node("fuel_tank", "floor", grime=dict(dirt=0.3, streaks=0.1),
      notes="2000 L bunded diesel tank; gauge on the +Z face: gauge_needle (inside empty gauge_mount, which is "
            "pre-rotated 180 deg about Y) turns about its local Z: rotation.z = -120 deg empty (E, left) .. +120 deg full "
            "(F, right), 0 = half")
def fuel_tank():
    mb = MB("fuel_tank")
    # ---------------------------------------------------------------- bund tray on runners
    BL, BW, bz0, bh = 2.5, 1.3, 0.08, 0.36
    for s in (-1, 1):
        mb.box((BL, 0.12, bz0), "paint_grey", loc=(0, s * 0.5, 0), bevel=0.006, seg=1)
    mb.box((BL, BW, 0.012), "paint_grey", loc=(0, 0, bz0), bevel=0.003, seg=1)
    for (cx, cy, sx, sy) in ((0, -BW / 2, BL, 0.01), (0, BW / 2, BL, 0.01), (-BL / 2, 0, 0.01, BW), (BL / 2, 0, 0.01, BW)):
        mb.box((sx, sy, bh), "paint_grey", loc=(cx, cy, bz0), bevel=0.002, seg=1)
    for (cx, cy, sx, sy) in ((0, -BW / 2, BL + 0.04, 0.05), (0, BW / 2, BL + 0.04, 0.05), (-BL / 2, 0, 0.05, BW),
                             (BL / 2, 0, 0.05, BW)):
        mb.box((sx, sy, 0.012), "paint_grey", loc=(cx, cy, bz0 + bh - 0.012), bevel=0.003, seg=1)
    for x in (-0.8, 0.0, 0.8):
        for s in (-1, 1):
            mb.box((0.05, 0.012, bh - 0.02), "paint_grey", loc=(x, s * (BW / 2 + 0.006), bz0), bevel=0.002, seg=1)
    # ---------------------------------------------------------------- saddles + tank
    R, TL, tz = 0.55, 1.9, bz0 + 0.012 + 0.3 + 0.55
    for x in (-0.62, 0.62):
        mb.box((0.14, 0.84, 0.3), "paint_grey", loc=(x, 0, bz0 + 0.012), bevel=0.006, seg=1)
    mb.rod((-TL / 2, 0, tz), (TL / 2, 0, tz), R, "paint_green", sides=28, cap=False)
    head = [(R, 0.0), (R * 0.985, 0.03), (R * 0.92, 0.065), (R * 0.78, 0.095), (R * 0.52, 0.115), (0.0, 0.124)]
    for s in (-1, 1):
        mb.lathe(head, "paint_green", sides=28, Mx=trs((s * TL / 2, 0, tz), (0, 90 * s, 0)))
        P.ring(mb, (s * TL / 2, 0, tz), R + 0.004, 0.007, axis=(1, 0, 0), mat="paint_green", segs=28, sides=5)
    # saddle straps
    for x in (-0.62, 0.62):
        pts = [Vector((x, (R + 0.008) * math.sin(t), tz + (R + 0.008) * math.cos(t))) for t in
               [math.radians(-100 + 200 * k / 16) for k in range(17)]]
        mb.sweep([(-0.003, -0.03), (0.003, -0.03), (0.003, 0.03), (-0.003, 0.03)], pts, "steel_dark", up=(1, 0, 0))
    # ---------------------------------------------------------------- top fittings
    top = tz + R
    mb.cyl(0.21, 0.05, "paint_green", sides=20, loc=(-0.3, 0, top - 0.01), bevel=0.006)
    mb.cyl(0.23, 0.02, "paint_green", sides=20, loc=(-0.3, 0, top + 0.04), bevel=0.004)
    for k in range(10):
        a = k / 10 * 2 * math.pi
        P.hexnut(mb, (-0.3 + math.cos(a) * 0.2, math.sin(a) * 0.2, top + 0.06), 0.012, 0.012, (0, 0, 1), "steel_dark")
    mb.cyl(0.055, 0.12, "steel", sides=12, loc=(0.42, -0.1, top - 0.02))
    mb.cyl(0.07, 0.05, "paint_red", sides=12, loc=(0.42, -0.1, top + 0.1), bevel=0.008)
    mb.rod((0.42 - 0.07, -0.1, top + 0.125), (0.42 + 0.07, -0.1, top + 0.125), 0.009, "paint_red", sides=6)
    vent = [Vector((0.72, 0.18, top - 0.02)), Vector((0.72, 0.18, top + 0.28)), Vector((0.72, 0.18, top + 0.36)),
            Vector((0.76, 0.18, top + 0.4)), Vector((0.8, 0.18, top + 0.36)), Vector((0.8, 0.18, top + 0.3))]
    mb.tube(vent, 0.025, "steel", sides=10)
    mb.cyl(0.032, 0.03, "steel_dark", sides=10, loc=(0.8, 0.18, top + 0.27))
    # ---------------------------------------------------------------- ladder at -X end
    lx = -TL / 2 - 0.2
    for s in (-1, 1):
        mb.rod((lx, s * 0.2, bz0 + 0.012), (lx + 0.05, s * 0.2, top + 0.12), 0.016, "galvanized", sides=8)
    for k in range(5):
        t = (k + 1) / 6
        mb.rod((lx + 0.05 * t, -0.2, bz0 + (top + 0.1 - bz0) * t), (lx + 0.05 * t, 0.2, bz0 + (top + 0.1 - bz0) * t), 0.013,
               "galvanized", sides=8)
    hoop = [Vector((lx + 0.05, -0.2, top + 0.12)), Vector((lx + 0.1, -0.2, top + 0.2)), Vector((lx + 0.22, -0.2, top + 0.16)),
            Vector((lx + 0.26, -0.2, top + 0.04))]
    mb.tube(hoop, 0.016, "galvanized", sides=8)
    mb.tube([Vector((p.x, 0.2, p.z)) for p in hoop], 0.016, "galvanized", sides=8)
    # ---------------------------------------------------------------- outlet valve + hose over the bund wall
    oz = tz - R + 0.12
    ox = TL / 2 + 0.06
    mb.rod((ox - 0.05, 0, oz), (ox + 0.12, 0, oz), 0.028, "steel", sides=10)
    mb.rod((ox + 0.05, -0.04, oz), (ox + 0.05, 0.04, oz), 0.036, "brass", sides=10, bevel=0.004)
    mb.box((0.15, 0.014, 0.014), "paint_red", center=True, loc=(ox + 0.05, -0.06, oz + 0.035), rot=(0, 20, 0))
    hose = [Vector((ox + 0.12, 0, oz)), Vector((ox + 0.2, 0, oz - 0.02)), Vector((BL / 2 - 0.02, -0.05, bz0 + bh + 0.04)),
            Vector((BL / 2 + 0.08, -0.08, bz0 + bh - 0.02)), Vector((BL / 2 + 0.14, -0.1, 0.15)),
            Vector((BL / 2 + 0.2, -0.16, 0.025)), Vector((BL / 2 + 0.3, -0.3, 0.02))]
    mb.tube(hose, 0.016, "rubber", sides=8)
    # ---------------------------------------------------------------- contents gauge on the front
    gz = tz + 0.1
    gsurf = -math.sqrt(R * R - 0.1 * 0.1)
    gface = -0.66
    GX = -0.2
    mb.boxc((GX, (gsurf + gface + 0.02) / 2, gz - 0.13), (0.06, abs(gface - gsurf), 0.04), "steel_dark", bevel=0.004)
    mb.lathe([(0.0, 0.0), (0.112, 0.0), (0.118, -0.006), (0.118, -0.06), (0.11, -0.07), (0.0, -0.07)], "steel_dark",
             sides=24, Mx=trs((GX, gface, gz), (90, 0, 0)))
    mb.lathe([(0.1, 0.0), (0.122, 0.0), (0.126, 0.008), (0.12, 0.014), (0.1, 0.014)], "steel", sides=24,
             Mx=trs((GX, gface, gz), (90, 0, 0)))
    mb.label("fuel_gauge", (GX, gface - 0.0015, gz), 0.2, 0.2)
    mb.cyl(0.101, 0.002, "glass", sides=24, Mx=trs((GX, gface - 0.012, gz), (90, 0, 0)))
    # decals
    for s in (-1, 1):
        mb.label("diesel_stencil", (0.42 * s, s * -(R + 0.0035), tz - 0.02), 0.72, rot=(0, 0, 0 if s > 0 else 180))
    mb.label("tank_plate", (-0.62, gsurf - 0.003 - 0.012 + 0.012, gz - 0.02), 0.22, rot=(0, 0, 0))
    mb.boxc((-0.62, gsurf + 0.004 - 0.012 + 0.012, gz - 0.02), (0.23, 0.012, 0.115), "steel_dark", bevel=0.002)
    mb.label("flammable", (0.6, -BW / 2 - 0.0075, bz0 + 0.19), 0.3)
    mb.label("nosmoking", (-0.55, -BW / 2 - 0.0075, bz0 + 0.19), 0.15, 0.19)
    root = mb.finish()
    mount = empty("gauge_mount", (GX, gface - 0.006, gz), rot=(0, 0, 180), parent=root)
    nb = MB("gauge_needle")
    nb.box((0.008, 0.002, 0.082), "paint_red", loc=(0, 0, -0.012), center=False, bevel=0.0)
    nb.box((0.004, 0.002, 0.02), "paint_red", loc=(0, 0, 0.07), center=False)
    nb.cyl(0.012, 0.004, "paint_black", sides=12, Mx=rotm((90, 0, 0)) @ Matrix.Translation((0, 0, -0.002)))
    needle = nb.finish(grime=False)
    child(needle, mount, (0, 0, 0))
    return root
