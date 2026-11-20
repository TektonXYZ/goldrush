"""Work-face shoring (shoring_1..4) and rubble_wall.
Alcove frame: origin at the alcove MOUTH floor centre, alcove extends toward three.js +Z = Blender -Y.
Alcoves 1-3: 7 m wide x 4.5 m tall x 9 m deep (walls x = +-3.5 vertical to 3.3 m, elliptical arch to 4.5 m).
Alcove 4: 10 x 6.5 x 12 (walls +-5.0 vertical to 4.9, arch to 6.5). Machine envelopes are kept clear."""
import math
import random

import bmesh
from mathutils import Matrix, Vector, noise

import mk
import parts as P
from mk import DEG, MB, child, empty, frame, rotm, trs
from parts import board, timber, wedge

BUILD = {}


def node(name, kind="floor", **meta):
    def deco(fn):
        BUILD[name] = (fn, dict(kind=kind, **meta))
        return fn
    return deco


def ibeam_prof(fl, dp, web, tf):
    hw, hd = fl / 2, dp / 2
    return [(-hd, -hw), (-hd + tf, -hw), (-hd + tf, -web / 2), (hd - tf, -web / 2), (hd - tf, -hw), (hd, -hw),
            (hd, hw), (hd - tf, hw), (hd - tf, web / 2), (-hd + tf, web / 2), (-hd + tf, hw), (-hd, hw)]


def horseshoe(half_w, spring, crown, n_leg=4, n_arch=20, splay=0.04):
    """Centreline of a horseshoe arch in the XZ plane at y = 0 (feet splayed slightly outward)."""
    pts = [Vector((-half_w - splay + splay * k / n_leg, 0, 0.012 + (spring - 0.012) * k / n_leg)) for k in range(n_leg + 1)]
    a, b = half_w, crown - spring
    for k in range(1, n_arch):
        t = math.pi - math.pi * k / n_arch
        pts.append(Vector((a * math.cos(t), 0, spring + b * math.sin(t))))
    pts += [Vector((half_w + splay * k / n_leg, 0, spring - (spring - 0.012) * k / n_leg)) for k in range(n_leg + 1)]
    return pts


def place(pts, y):
    return [Vector((p.x, y, p.z)) for p in pts]


def alcove_pt(u, half_w, spring, crown, inset):
    """Point on an alcove profile by arc parameter u in [0, 1] (left foot -> crown -> right foot), inset toward inside."""
    wall = spring
    arch_len = math.pi * math.sqrt((half_w ** 2 + (crown - spring) ** 2) / 2)
    total = 2 * wall + arch_len
    s = u * total
    if s < wall:
        return Vector((-half_w + inset, 0, s)), Vector((1, 0, 0))
    if s > wall + arch_len:
        return Vector((half_w - inset, 0, total - s)), Vector((-1, 0, 0))
    t = math.pi - math.pi * (s - wall) / arch_len
    a, b = half_w - inset, crown - spring - inset
    p = Vector((a * math.cos(t), 0, spring + b * math.sin(t)))
    n = -Vector((math.cos(t) / max(a, 1e-3), 0, math.sin(t) / max(b, 1e-3))).normalized()
    return p, n


# ====================================================================== shoring_1: timber props, headers, cribs (coal)
@node("shoring_1", "floor", grime=dict(dirt=0.3),
      notes="coal face: round timber props + square headers at z = 0.4/3.3/6.2 with roof boards, two log cribs near the "
            "mouth, face props at z = 7.9; keeps x +-2.8, y <= 4.0 clear")
def shoring_1():
    mb = MB("shoring_1")
    rng = mb.rng
    hdr_bot, hdr_h = 4.02, 0.26
    sets = (-0.4, -3.3, -6.2)
    for y in sets:
        for s in (-1, 1):
            x = s * (3.12 + rng.uniform(-0.03, 0.03))
            r = rng.uniform(0.1, 0.12)
            mb.cyl(r, hdr_bot + 0.02, "wood_timber", sides=10, loc=(x, y + rng.uniform(-0.03, 0.03), 0.0),
                   rot=(rng.uniform(-1.5, 1.5), rng.uniform(-1.5, 1.5), rng.uniform(0, 90)), r2=r * 0.92)
            mb.box((0.36, 0.3, 0.05), "wood_planks", loc=(x, y, 0.0), rot=(0, 0, rng.uniform(-8, 8)), bevel=0.006, seg=1)
            wedge(mb, (x - s * 0.17, y + 0.06, hdr_bot - 0.004), 0.22, 0.08, 0.04, rot=(180, 0, 180 if s > 0 else 0))
            mb.box((0.34, 0.24, 0.04), "wood_planks", loc=(x, y, hdr_bot - 0.04), bevel=0.005, seg=1)
        timber(mb, (-3.42, y, hdr_bot + hdr_h / 2), (3.42, y, hdr_bot + hdr_h / 2), 0.26, hdr_h, up=(0, 0, 1), bevel=0.02,
               cuts=8, bow=0.003, ends=0.015)
    # roof boards between the sets (two bays) + a short bay to the face
    top = hdr_bot + hdr_h
    for y0, y1 in ((sets[0] + 0.0, sets[1]), (sets[1], sets[2])):
        x = -3.2
        while x < 3.15:
            w_ = rng.uniform(0.17, 0.26)
            if rng.random() > 0.1:
                board(mb, (x + w_ / 2, y0 + rng.uniform(-0.05, 0.0), top), (x + w_ / 2, y1 - rng.uniform(0.0, 0.05), top),
                      w_ - 0.005, 0.05, "wood_planks", up=(0, 0, 1), bevel=0.006)
            x += w_ + rng.uniform(0.02, 0.07)
    # cribs (log-cabin stacks) near the mouth, outside the machine envelope
    for s in (-1, 1):
        cx, cy = s * 3.18, -1.85
        layer, z = 0, 0.0
        while z < top - 0.05:
            h = 0.19
            for k in (-1, 1):
                if layer % 2 == 0:
                    timber(mb, (cx + k * 0.24, cy - 0.38, z + h / 2), (cx + k * 0.24, cy + 0.38, z + h / 2), 0.18, h,
                           up=(0, 0, 1), bevel=0.0, cuts=0, bow=0.002, twist=2.5, ends=0.01)
                else:
                    timber(mb, (cx - 0.38, cy + k * 0.24, z + h / 2), (cx + 0.38, cy + k * 0.24, z + h / 2), 0.18, h,
                           up=(0, 0, 1), bevel=0.0, cuts=0, bow=0.002, twist=2.5, ends=0.01)
            z += h
            layer += 1
        wedge(mb, (cx, cy, z), 0.4, 0.14, min(0.08, top + 0.06 - z), rot=(0, 0, 90))
    # face props with header boards near the face
    for s in (-1, 1):
        x, y = s * 3.05, -7.9
        mb.cyl(0.1, hdr_bot + hdr_h - 0.04, "wood_timber", sides=10, loc=(x, y, 0.0), r2=0.092)
        board(mb, (x - s * 0.5, y, hdr_bot + hdr_h - 0.04), (x + s * 0.3, y, hdr_bot + hdr_h - 0.04), 0.22, 0.06,
              "wood_planks", up=(0, 0, 1))
    # timber dogs on header/prop joints
    for y in sets:
        for s in (-1, 1):
            P.staple(mb, (s * 3.12, y - 0.115, hdr_bot - 0.15), (s * 3.12, y - 0.135, hdr_bot + 0.12), (0, -1, 0), r=0.009)
    return mb.finish()


# ====================================================================== shoring_2: steel arch sets + lagging (iron)
@node("shoring_2", "floor", grime=dict(dirt=0.28, streaks=0.12),
      notes="iron: four horseshoe I-beam arches (z = 0.4/3.2/6.0/8.6) with timber lagging between them on the roof and "
            "shoulders, spreader bars at the legs; keeps x +-2.8, y <= 3.95 clear")
def shoring_2():
    mb = MB("shoring_2")
    rng = mb.rng
    half, spring, crown = 3.28, 3.05, 4.32
    prof = ibeam_prof(0.13, 0.16, 0.01, 0.014)
    ys = (-0.4, -3.2, -6.0, -8.6)
    cl = horseshoe(half, spring, crown, n_leg=3, n_arch=14)
    for y in ys:
        pts = place(cl, y)
        n = len(pts)
        mid = n // 2
        for a, b in ((0, mid - 4), (mid - 4, mid + 4), (mid + 4, n - 1)):
            mb.sweep(prof, pts[a:b + 1], "steel_dark", up=(0, 1, 0))
        for ji in (mid - 4, mid + 4):
            p = pts[ji]
            t = (pts[ji + 1] - pts[ji - 1]).normalized()
            for side in (-1, 1):
                c = p + Vector((0, side * 0.011, 0))
                Mx = Matrix.Translation(c) @ frame(t, Vector((0, side, 0)))
                mb.box((0.46, 0.1, 0.012), "steel_dark", center=True, Mx=Mx, bevel=0.003, seg=1)
            nr = Vector((0, 1, 0)).cross(t).normalized()
            for u in (-0.16, -0.05, 0.05, 0.16):
                P.hexnut(mb, p + t * u + Vector((0, -0.02, 0)), 0.013, 0.011, (0, -1, 0), "steel_dark")
        for s in (-1, 1):
            mb.box((0.3, 0.26, 0.016), "steel_dark", loc=(s * (half + 0.04), y, 0.0), bevel=0.003, seg=1)
    # lagging boards between consecutive arches along the arch from shoulder to shoulder
    a, b = half, crown - spring
    for y0, y1 in zip(ys[:-1], ys[1:]):
        t = 0.62 * math.pi
        while t > 0.38 * math.pi - 1e-6:
            r_out = 0.09
            p = Vector(((a + r_out) * math.cos(t), 0, spring + (b + r_out) * math.sin(t)))
            nr = Vector((math.cos(t) * b, 0, math.sin(t) * a)).normalized()
            if rng.random() > 0.08:
                board(mb, (p.x, y0 - 0.06, p.z), (p.x, y1 + 0.06, p.z), 0.22, 0.05, "wood_planks", up=(nr.x, 0, nr.z),
                      bevel=0.0)
            t -= 0.036 * math.pi
        for t in (0.82 * math.pi, 0.72 * math.pi, 0.28 * math.pi, 0.18 * math.pi):
            p = Vector(((a + 0.09) * math.cos(t), 0, spring + (b + 0.09) * math.sin(t)))
            nr = Vector((math.cos(t) * b, 0, math.sin(t) * a)).normalized()
            board(mb, (p.x, y0 - 0.06, p.z), (p.x, y1 + 0.06, p.z), 0.24, 0.05, "wood_planks", up=(nr.x, 0, nr.z), bevel=0.006)
        for s in (-1, 1):  # spreader bars between legs
            for z in (1.0, 2.4):
                mb.rod((s * (half + 0.03), y0 - 0.065, z), (s * (half + 0.03), y1 + 0.065, z), 0.022, "steel_dark", sides=8)
    return mb.finish()


# ====================================================================== shoring_3: rock bolts + mesh + straps (silver)
@node("shoring_3", "floor", grime=dict(dirt=0.2),
      notes="silver: welded mesh over the upper walls and roof of the nominal alcove (walls x = +-3.5 vertical to 3.3, "
            "elliptical arch to 4.5; inset 3 cm), rock bolts with domed plates on a ~1.1 m grid, W-straps across the roof")
def shoring_3():
    mb = MB("shoring_3")
    rng = mb.rng
    mk.custom_mat("custom_mesh_weld", "mesh_weld.png", rough=0.45, metal=0.9)
    half, spring, crown = 3.5, 3.3, 4.5
    inset = 0.03
    depth = 8.8
    u0, u1 = 0.17, 0.83   # from ~1.6 m up the left wall over the roof to the right wall
    total_len = 2 * spring + math.pi * math.sqrt((half ** 2 + (crown - spring) ** 2) / 2)
    nu, nv = 26, 12
    tb = bmesh.new()
    uvl = tb.loops.layers.uv.new("uv")
    grid = []
    for j in range(nv + 1):
        y = -0.2 - depth * j / nv
        row = []
        for i in range(nu + 1):
            u = u0 + (u1 - u0) * i / nu
            p, n = alcove_pt(u, half, spring, crown, inset)
            sag = 0.025 * math.sin(math.pi * (j * 2.0 / nv % 1.0)) * (1 if 0.3 < u < 0.7 else 0.4)
            row.append((tb.verts.new((p.x + n.x * sag, y, p.z + n.z * sag)), (u - u0) * total_len, y))
        grid.append(row)
    for j in range(nv):
        for i in range(nu):
            q = [grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]]
            f = tb.faces.new([a for a, _, _ in q])
            for lp, (_, s_, y_) in zip(f.loops, q):
                lp[uvl].uv = (s_ / 0.2 * 1.0, y_ / 0.2)
    tb.normal_update()
    mb.commit(tb, Matrix.Identity(4), "custom_mesh_weld", None, uvoff=False)
    # bolts on a grid (domed plate + nut + tail) through the mesh
    for j in range(7):
        y = -0.7 - 1.25 * j
        for i in range(7):
            u = u0 + 0.02 + (u1 - u0 - 0.04) * i / 6 + (0.012 if j % 2 else -0.012)
            p, n = alcove_pt(u, half, spring, crown, inset - 0.005)
            Mx = Matrix.Translation(p + Vector((0, rng.uniform(-0.05, 0.05), 0))) @ frame(Vector((0, 1, 0)), n)
            mb.box((0.15, 0.15, 0.007), "galvanized", center=True, Mx=Mx @ Matrix.Translation((0, 0, 0.004)))
            mb.cyl(0.03, 0.012, "galvanized", sides=6, Mx=Mx @ Matrix.Translation((0, 0, 0.007)), r2=0.014, cap=False)
            mb.cyl(0.016, 0.015, "galvanized", sides=6, Mx=Mx @ Matrix.Translation((0, 0, 0.019)))
            mb.rod(Mx @ Vector((0, 0, 0.034)), Mx @ Vector((0, 0, 0.07)), 0.01, "steel_dark", sides=5, cap=False)
    # W-straps across the roof (curved steel strips) at three stations
    for y in (-1.2, -4.5, -7.8):
        pts = []
        for i in range(25):
            u = 0.3 + 0.4 * i / 24
            p, n = alcove_pt(u, half, spring, crown, inset - 0.012)
            pts.append(Vector((p.x, y, p.z)))
        mb.sweep([(-0.004, -0.13), (0.004, -0.13), (0.004, 0.13), (-0.004, 0.13)], pts, "galvanized", up=(0, 1, 0))
        for i in range(5):
            u = 0.31 + 0.38 * i / 4
            p, n = alcove_pt(u, half, spring, crown, inset - 0.02)
            P.hexnut(mb, Vector((p.x, y, p.z)) + n * 0.01, 0.017, 0.015, n, "galvanized")
    return mb.finish(grime=True)


# ====================================================================== shoring_4: heavy steel sets + lagging (gold)
@node("shoring_4", "floor", grime=dict(dirt=0.3, streaks=0.1),
      notes="gold: 10 x 6.5 x 12 m alcove, four heavy H-beam sets (z = 0.5/4.0/7.5/11.0) on concrete footings, knee "
            "braces, tie rods, timber roof lagging and steel wall lagging; keeps x +-4.0, y <= 5.7 clear")
def shoring_4():
    mb = MB("shoring_4")
    rng = mb.rng
    px, cap_bot, cap_h = 4.62, 5.95, 0.4
    ys = (-0.5, -4.0, -7.5, -11.0)

    def hbeam_vertical(x, y, z0, z1, fl=0.3, dp=0.3, web=0.014, tf=0.022):
        prof = ibeam_prof(fl, dp, web, tf)   # depth along X (strong axis resists rib pressure), flanges face +-Z
        Mx = Matrix.Translation((x, y, 0)) @ rotm((90, 0, 0))   # local Y -> world Z
        mb.extrude(prof, z0, z1, "paint_yellow", Mx=Mx)
    for y in ys:
        for s in (-1, 1):
            x = s * px
            mb.box((0.7, 0.7, 0.25), "concrete", loc=(x, y, 0.0), bevel=0.02, seg=1)
            mb.box((0.46, 0.46, 0.025), "steel_dark", loc=(x, y, 0.25), bevel=0.004, seg=1)
            for dx in (-0.17, 0.17):
                for dy in (-0.17, 0.17):
                    P.hexnut(mb, (x + dx, y + dy, 0.275), 0.022, 0.018, (0, 0, 1), "steel_dark")
            hbeam_vertical(x, y, 0.275, cap_bot)
            # knee brace
            mb.beam((x - s * 0.15, y, cap_bot - 0.75), (x - s * 0.8, y, cap_bot - 0.02), 0.16, 0.16, "paint_yellow",
                    up=(0, 1, 0), bevel=0.008)
            for (bx, bz) in ((x - s * 0.17, cap_bot - 0.72), (x - s * 0.78, cap_bot - 0.05)):
                mb.boxc((bx, y, bz), (0.24, 0.32, 0.24), "paint_yellow", bevel=0.01, seg=1)
        # cap beam (H section along X)
        prof = ibeam_prof(0.32, cap_h, 0.016, 0.026)
        capz = cap_bot + cap_h / 2
        pts = [Vector((-5.05, y, capz)), Vector((5.05, y, capz))]
        mb.sweep(prof, pts, "paint_yellow", up=(0, 1, 0))
        for s in (-1, 1):
            mb.boxc((s * px, y, cap_bot - 0.01), (0.36, 0.36, 0.02), "steel_dark", bevel=0.004)
    # tie rods between sets + roof lagging + wall lagging plates
    top = cap_bot + cap_h
    for y0, y1 in zip(ys[:-1], ys[1:]):
        for s in (-1, 1):
            for z in (1.6, 3.6):
                mb.rod((s * (px + 0.0), y0 - 0.16, z), (s * px, y1 + 0.16, z), 0.03, "steel_dark", sides=8)
            for z in [0.5 + 0.55 * k for k in range(9)]:
                if rng.random() > 0.12:
                    mb.box((0.012, abs(y1 - y0) - 0.3, 0.5), "steel_dark", center=True,
                           loc=(s * (px + 0.17), (y0 + y1) / 2, z + 0.25))
        x = -4.9
        while x < 4.88:
            w_ = rng.uniform(0.2, 0.28)
            if rng.random() > 0.08:
                board(mb, (x + w_ / 2, y0 - 0.17, top), (x + w_ / 2, y1 + 0.17, top), w_ - 0.006, 0.06, "wood_timber",
                      up=(0, 0, 1), bevel=0.0)
            x += w_ + rng.uniform(0.02, 0.06)
    return mb.finish()


# ====================================================================== rubble_wall
@node("rubble_wall", "floor", grime=dict(dirt=0.1, ao_floor=0.25),
      notes="blasted broken rock filling the 4.4 x 3.8 drift; the pile face looks toward +Z, toe spills to z = +1.8; "
            "timber barricade with a DANGER sign at z = +2.3")
def rubble_wall():
    mb = MB("rubble_wall")
    rng = random.Random(77)
    W2, spring, crown = 2.2, 2.5, 3.8
    # backing mass: displaced surface closing the drift (so nothing shows through)
    tb = bmesh.new()
    nx, nz = 16, 12
    vs = []
    for j in range(nz + 1):
        row = []
        for i in range(nx + 1):
            x = -W2 - 0.1 + (2 * W2 + 0.2) * i / nx
            zmax = (spring + (crown - spring) * math.sqrt(max(0.0, 1 - (x / (W2 + 0.1)) ** 2))) + 0.1
            z = zmax * j / nz
            y = 0.25 * noise.noise(Vector((x * 1.3, z * 1.3, 4.2))) + 0.35 * (1 - z / (crown + 0.1)) - 0.1
            row.append(tb.verts.new((x, -y, z)))
        vs.append(row)
    for j in range(nz):
        for i in range(nx):
            tb.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
    bmesh.ops.recalc_face_normals(tb, faces=tb.faces[:])
    for f in tb.faces:
        if f.normal.y > 0:
            f.normal_flip()
    tb.normal_update()
    mb.commit(tb, Matrix.Identity(4), "rock_dark", mk.uv_world_box, flat=True)
    # big blocks on the face, smaller ones spilling onto the floor (toe toward +Z = Blender -Y)
    for k in range(46):
        x = rng.uniform(-2.05, 2.05)
        z = rng.uniform(0.2, 3.4) * (1 - 0.35 * abs(x) / 2.2)
        y = -0.25 - rng.uniform(0.0, 0.5) * (1 - z / 3.8)
        s = rng.uniform(0.28, 0.6)
        mb.rock((x, y, z), (s, s * rng.uniform(0.7, 1.1), s * rng.uniform(0.6, 0.9)), rng.choice(("rock", "rock", "rock_dark")),
                seed=k * 7 + 3, detail=1)
    for k in range(70):
        t = rng.random() ** 0.8
        y = -0.4 - 1.5 * t
        x = rng.uniform(-2.0, 2.0) * (1 - 0.25 * t)
        s = rng.uniform(0.1, 0.32) * (1.1 - 0.6 * t)
        z = max(0.02, (1 - t) * 0.9 * rng.uniform(0.3, 1.0)) + s * 0.25
        mb.rock((x, y, z), (s, s * rng.uniform(0.7, 1.2), s * rng.uniform(0.5, 0.8)), rng.choice(("rock", "rock_dark", "gravel")),
                seed=k * 13 + 101, detail=0 if s < 0.2 else 1)
    # fines/gravel apron
    tb = bmesh.new()
    pts = []
    for j in range(7):
        row = []
        for i in range(11):
            x = -2.15 + 4.3 * i / 10
            y = -0.2 - 1.9 * j / 6
            z = max(0.0, 0.55 * (1 - j / 6) ** 1.6 + 0.05 * noise.noise(Vector((x * 2, y * 2, 1.0))))
            row.append(tb.verts.new((x, y, z)))
        pts.append(row)
    for j in range(6):
        for i in range(10):
            tb.faces.new((pts[j][i], pts[j + 1][i], pts[j + 1][i + 1], pts[j][i + 1]))
    bmesh.ops.recalc_face_normals(tb, faces=tb.faces[:])
    for f in tb.faces:
        if f.normal.z < 0:
            f.normal_flip()
    tb.normal_update()
    mb.commit(tb, Matrix.Identity(4), "gravel", mk.uv_world_box)
    # barricade: two posts, two rails (one hanging loose), DANGER sign, hazard tape
    by = -2.3
    for s in (-1, 1):
        timber(mb, (s * 1.25, by, 0.0), (s * 1.25, by, 1.25), 0.12, 0.12, up=(0, 1, 0), bevel=0.01, cuts=2)
        mb.box((0.4, 0.4, 0.05), "wood_planks", loc=(s * 1.25, by, 0.0), rot=(0, 0, rng.uniform(-10, 10)), bevel=0.005, seg=1)
    board(mb, (-1.42, by - 0.08, 1.05), (1.42, by - 0.08, 1.1), 0.18, 0.035, "wood_planks", up=(0, 1, 0))
    board(mb, (-1.42, by - 0.08, 0.6), (1.2, by - 0.08, 0.38), 0.16, 0.035, "wood_planks", up=(0, 1, 0))
    mb.box((0.62, 0.02, 0.44), "paint_white", loc=(0.0, by - 0.11, 0.86), bevel=0.004, seg=1)
    mb.label("danger_blast", (0.0, by - 0.1215, 1.08), 0.6)
    for x in (-0.25, 0.25):
        P.bolt(mb, (x, by - 0.122, 1.26), (0, -1, 0), r=0.005, head=0.009, stud=0.0, washer=False)
    tape = [Vector((-1.25, by - 0.07, 1.2)), Vector((-0.6, by - 0.07, 1.12)), Vector((0.0, by - 0.07, 1.1)),
            Vector((0.6, by - 0.07, 1.13)), Vector((1.25, by - 0.07, 1.2))]
    mb.sweep([(-0.001, -0.035), (0.001, -0.035), (0.001, 0.035), (-0.001, 0.035)], tape, "paint_red", up=(0, 0, 1))
    return mb.finish()
