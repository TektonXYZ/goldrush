"""MOTHERLODE claim kit: every surface building of a mining claim, one named root node each.

    bl assets/claimkit/claimkit.py                       -> public/models/claim-kit.glb (+ .blend, previews)
    bl assets/claimkit/claimkit.py -- portal shack        -> only those nodes, scratch export, previews

Blender Z-up, metres. Fronts face -Y (= +Z in three.js). Every root sits at the origin = bottom centre of its
footprint (the portal: floor of the opening's front centre). See NODES.md for sizes and children.
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bmesh  # noqa: E402
import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import bk  # noqa: E402
import kit  # noqa: E402
from kit import MB, R, T, fbm3, lerp, smoothstep  # noqa: E402

EXTRAS = {}  # object name -> grime modifier fn(local co, normal) (see kit.bake_grime)
SHOTS = {}   # node -> [(name, cam, target, lens)]
SIGNS = []   # (object, preview png) for preview-only sign textures


def bulb(name, loc, r, parent, mat="emit_warm", shape="sphere"):
    """Separate emissive child (the game drives emit_* intensity / may add a light at it)."""
    b = MB(name, seed=3)
    if shape == "sphere":
        bmesh.ops.create_icosphere(b.bm, subdivisions=1, radius=r, matrix=Matrix.Identity(4))
        fs = list(b.bm.faces)
        for f in fs:
            f.normal_update()
        b._uv_world(fs, False)
        b._paint(fs, mat, 1.0, 0, True)
    else:
        b.cyl(r, r * 2.2, mat, loc=(0, 0, -r * 1.1), sides=8, nogrime=True)
    o = b.finish(smooth=80, weighted=False)
    kit.strip_color(o)
    o.location = loc
    kit.attach(o, parent)
    return o


# ====================================================================== PORTAL
def portal_rock(rng):
    """Closed rock solid: strata-aligned front sheet (crisp ledges + staggered joints, a tilted facet per block),
    a notch cut back around the adit, sides/top wrapping back into the terrain wall, closed by a bottom strip and
    a back cap at y = BACK."""
    X0, X1, Z0, Z1, BACK = -8.6, 8.6, -0.4, 12.6, 5.0

    def wob(x):
        return 0.045 * x + 0.28 * fbm3((x * 0.17, 3.1, 0.7), 3)

    strata = []
    s = 0.75
    while s < Z1 - 1.0:
        t = rng.choice([0.28, 0.4, 0.55, 0.75, 0.95, 1.2, 1.5, 1.8])
        s1 = min(s + t, Z1 - 0.75)
        bold = rng.random() < 0.3
        strata.append(dict(s0=s, s1=s1, p=rng.uniform(-0.34, 0.34) if bold else rng.uniform(-0.1, 0.1),
                           u=rng.uniform(0.08, 0.22) if bold else rng.uniform(0.02, 0.08)))
        s = s1
        if s >= Z1 - 0.8:
            break
    ths = [st["s1"] - st["s0"] for st in strata]
    bwa = [0.0] + [0.3 * min(ths[k - 1], ths[k]) for k in range(1, len(strata))] + [0.0]
    bws = [rng.uniform(0, 50) for _ in bwa]

    def bw(k, x):
        return bwa[k] * fbm3((x * 0.23 + bws[k], bws[k], 0.3), 2) * 2.0

    rows = [(Z0, 0, 0.5, True), (0.05, 0, 0.5, True)]
    for k, st in enumerate(strata):
        th = st["s1"] - st["s0"]
        frs = [0.0, 0.3, 0.7, 1.0] if th > 1.0 else ([0.0, 0.5, 1.0] if th > 0.5 else [0.0, 1.0])
        for fr in frs:
            sv = st["s0"] + fr * th + (0.018 if fr == 0 else (-0.018 if fr == 1 else 0.0))
            rows.append((sv, k, fr, False))
    rows.append((Z1, len(strata) - 1, 1.0, True))

    joints = [-7.5, -6.2, -4.9, -3.6, -1.4, 0.6, 2.2, 3.6, 4.8, 6.1, 7.4]
    cols = [x for x in [X0 + i * (X1 - X0) / 24 for i in range(25)] if min(abs(x - j) for j in joints) > 0.18]
    for j in joints:
        cols += [j - 0.024, j + 0.024]
    cols.sort()
    nseg = len(joints) + 1
    # staggered joints: in each stratum only some joints break the rock (like brick bond)
    blk = []
    for k in range(len(strata)):
        ids, b = [], 0
        for m in range(nseg):
            if m > 0 and rng.random() < 0.6:
                b += 1
            ids.append(b)
        blk.append(ids)
    nb = max(max(i) for i in blk) + 1
    Q = [[rng.uniform(-0.2, 0.2) for _ in range(nb)] for _ in strata]
    A = [[rng.uniform(-0.14, 0.14) for _ in range(nb)] for _ in strata]
    B = [[rng.uniform(-0.32, 0.32) for _ in range(nb)] for _ in strata]
    edges = [X0] + joints + [X1]
    xcb = []
    for k in range(len(strata)):
        cen = {}
        for m in range(nseg):
            cen.setdefault(blk[k][m], []).extend([edges[m], edges[m + 1]])
        xcb.append({b: (min(v) + max(v)) / 2 for b, v in cen.items()})
    ribs = [(rng.choice([-1, 1]) * rng.uniform(4.6, 6.8), rng.uniform(0.7, 1.4), rng.uniform(0.35, 0.75)) for _ in range(3)]
    ribs.append((rng.uniform(-1.5, 1.5), 1.6, 0.4))

    def y_at(x, z, k, m, t, fixed):
        ax = abs(x)
        yb = 0.1 * max(z, 0.0) + 0.7 * fbm3((x * 0.16, z * 0.16, 9.1), 3)
        for bx, bw, bd in ribs:
            yb -= bd * math.exp(-((x - bx) / bw) ** 2) * smoothstep(0.0, 2.0, z)
        yb += 2.5 * smoothstep(4.8, 8.6, ax + 0.9 * fbm3((z * 0.31, 1.7, 0.2), 3))
        yb += 2.9 * smoothstep(9.2, 12.6, z + 1.4 * fbm3((x * 0.29, 5.3, 0.4), 3))
        det = 0.0
        if not fixed or z > 0.5:
            st = strata[k]
            th = st["s1"] - st["s0"]
            b = blk[k][m]
            det -= st["p"] + Q[k][b] + A[k][b] * (x - xcb[k][b]) + B[k][b] * (t - 0.5) * th
            det += st["u"] * max(0.0, 1.0 - t / 0.25)
            det += 0.12 * max(0.0, (t - 0.8) / 0.2)
        det += 0.06 * fbm3((x * 1.3, z * 1.3, 2.2), 3)
        near = (1 - smoothstep(3.3, 5.4, ax)) * (1 - smoothstep(5.6, 7.8, z))
        y = lerp(yb + det, 0.24 + 0.45 * det, near)
        y -= 1.55 * (1 - smoothstep(0.0, 1.7, z)) * smoothstep(5.3, 6.6, ax)
        return min(y, BACK - 0.15)

    bm = bmesh.new()
    V = []
    for r_, (sv, k, fr, fixed) in enumerate(rows):
        row = []
        for c_, x in enumerate(cols):
            z = sv if fixed else sv + wob(x) + lerp(bw(k, x), bw(k + 1, x), fr)
            m = sum(1 for j in joints if j < x)
            xx = x
            if c_ in (0, len(cols) - 1) or r_ == len(rows) - 1:
                y = BACK
                if r_ == len(rows) - 1:
                    z += 0.9 * fbm3((x * 0.35, 7.7, 0.1), 3)
                elif c_ in (0, len(cols) - 1) and r_ > 0:
                    xx += 0.28 * fbm3((z * 0.4, 4.4 * (1 if c_ else -1), 0.6), 2) * 2
            else:
                y = y_at(x, z, k, m, fr, fixed)
            row.append(bm.verts.new((xx, y, z)))
        V.append(row)
    nr, nc = len(V), len(cols)
    for r_ in range(nr - 1):
        for c_ in range(nc - 1):
            bm.faces.new((V[r_][c_], V[r_][c_ + 1], V[r_ + 1][c_ + 1], V[r_ + 1][c_]))
    BB = [V[0][0]] + [bm.verts.new((cols[c_], BACK, Z0)) for c_ in range(1, nc - 1)] + [V[0][nc - 1]]
    for c_ in range(nc - 1):
        a, b, cc, d = V[0][c_], BB[c_], BB[c_ + 1], V[0][c_ + 1]
        if c_ == 0:
            bm.faces.new((a, cc, d))
        elif c_ == nc - 2:
            bm.faces.new((a, b, d))
        else:
            bm.faces.new((a, b, cc, d))
    loop = [V[r_][0] for r_ in range(nr)] + [V[nr - 1][c_] for c_ in range(1, nc)] + \
           [V[r_][nc - 1] for r_ in range(nr - 2, -1, -1)] + [BB[c_] for c_ in range(nc - 2, 0, -1)]
    cap = bm.faces.new(loop)
    bmesh.ops.triangulate(bm, faces=[cap], quad_method="BEAUTY", ngon_method="BEAUTY")
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.normal_update()
    nonman = sum(1 for e in bm.edges if len(e.link_faces) != 2)
    print(f"[portal] rock solid: {len(bm.faces)} faces, non-manifold edges: {nonman}")
    uv = bm.loops.layers.uv.new("UVMap")
    col = bm.loops.layers.float_color.new("Col")
    ng = bm.faces.layers.int.new("nogrime")
    for f in bm.faces:
        n = f.normal
        k = max(range(3), key=lambda i: abs(n[i]))
        a, b = [i for i in range(3) if i != k]
        f[ng] = 0
        for lp in f.loops:
            lp[uv].uv = (lp.vert.co[a], lp.vert.co[b])
            lp[col] = (1, 1, 1, 1)
    me = bpy.data.meshes.new("portal_rock")
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new("portal_rock", me)
    bpy.context.scene.collection.objects.link(o)
    me.materials.append(kit.MAT("rock"))
    return o


def portal_cutter(rng, back=3.0):
    pts = [(-2.95, 0.03), (2.95, 0.03), (3.02, 1.5), (2.98, 3.2), (2.72, 4.25), (2.12, 4.85), (1.05, 5.15),
           (0.0, 5.28), (-1.05, 5.15), (-2.12, 4.85), (-2.72, 4.25), (-2.98, 3.2), (-3.02, 1.5)]
    pts = [(x + (rng.uniform(-0.1, 0.1) if z > 1 else 0), z + (rng.uniform(-0.08, 0.08) if z > 1 else 0)) for x, z in pts]
    mb = MB("cutter", seed=2)
    n = len(pts)
    front = [(x, -4.0, z) for x, z in pts]
    rear = [(x, back, z) for x, z in pts]
    verts = front + rear
    faces = [list(range(n)), list(range(n, 2 * n))[::-1]]
    for i in range(n):
        j = (i + 1) % n
        faces.append([j, i, n + i, n + j])
    mb.mesh(verts, faces, "rock_dark")
    bmesh.ops.recalc_face_normals(mb.bm, faces=list(mb.bm.faces))
    return mb.finish(smooth=0, weighted=False)


def lantern(mb, x, side, parent, name):
    """Iron L-bracket on the post face + a hurricane lantern hanging from it. Returns the bulb object."""
    sx = 1 if side > 0 else -1
    y0, arm = 0.0, -0.46
    zt = 3.22
    mb.box((0.09, 0.012, 0.32), "steel_dark", loc=(x, y0 - 0.006, zt - 0.22), bevel=0.003, seg=1)
    mb.rod((x, y0, zt), (x, arm, zt), 0.016, "steel_dark", sides=6)
    mb.rod((x, y0, zt - 0.2), (x, arm * 0.62, zt), 0.011, "steel_dark", sides=5)
    mb.cyl(0.012, 0.05, "steel_dark", loc=(x, arm + 0.02, zt - 0.05), sides=5)
    hx, hy, top = x, arm + 0.02, zt - 0.05
    # bail (wire handle) as a small arch
    pts = [(hx - 0.075 * math.cos(a), hy, top - 0.14 + 0.13 * math.sin(a)) for a in [i / 6 * math.pi for i in range(7)]]
    mb.tube(pts, 0.004, "steel_dark", sides=4)
    mb.cyl(0.11, 0.03, "galvanized", loc=(hx, hy, top - 0.19), sides=12, r2=0.1, bevel=0.006)
    mb.cyl(0.1, 0.065, "galvanized", loc=(hx, hy, top - 0.16), sides=12, r2=0.035)
    mb.cyl(0.03, 0.03, "galvanized", loc=(hx, hy, top - 0.1), sides=8)
    mb.cyl(0.072, 0.17, "glass", loc=(hx, hy, top - 0.36), sides=12, r2=0.066, nogrime=True, cap=False)
    for k in range(4):
        a = k / 4 * math.tau + math.pi / 4
        mb.rod((hx + math.cos(a) * 0.085, hy + math.sin(a) * 0.085, top - 0.37),
               (hx + math.cos(a) * 0.08, hy + math.sin(a) * 0.08, top - 0.19), 0.005, "steel_dark", sides=4)
    mb.cyl(0.1, 0.075, "galvanized", loc=(hx, hy, top - 0.445), sides=12, r2=0.095, bevel=0.006)
    return bulb(name, (hx, hy, top - 0.28), 0.032, parent)


def build_portal():
    rng = random.Random(1849)
    rock = portal_rock(rng)
    cutter = portal_cutter(rng)
    mod = rock.modifiers.new("cut", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.solver = "EXACT"
    mod.object = cutter
    try:
        mod.material_mode = "TRANSFER"
    except AttributeError:
        pass
    bk.select([rock])
    bpy.ops.object.modifier_apply(modifier="cut")
    bpy.data.objects.remove(cutter, do_unlink=True)

    rmb = MB("portal", seed=11)
    faces = rmb.absorb(rock)
    # the reveal in front of the timber set is outside rock, the tunnel behind it is rock_dark
    ri, di = rmb._mi("rock"), rmb._mi("rock_dark")
    for f in faces:
        c = f.calc_center_median()
        if f.material_index == di and c.y < 0.5:
            f.material_index = ri
    # rubble + fallen blocks at the foot (not in the cart path), kept tight to the face (it follows the face back at
    # the sides) so the claim's buildings can stand within 1 m of the portal's front
    spots = []
    for side in (-1, 1):
        for i in range(9):
            x = side * rng.uniform(5.4, 8.2)
            y = rng.uniform(-1.0, -0.25) + (abs(x) - 5.4) * 0.35
            s = rng.uniform(0.22, 0.7)
            spots.append((x, y, s))
        for i in range(5):
            spots.append((side * rng.uniform(3.2, 5.3), rng.uniform(-1.05, -0.7), rng.uniform(0.14, 0.32)))
        bx = side * rng.uniform(6.2, 7.4)
        spots.append((bx, -1.05 + (abs(bx) - 5.4) * 0.35, rng.uniform(0.85, 1.1)))
    for i, (x, y, s) in enumerate(spots):
        rmb.chunk((x, y, s * 0.28), (s * rng.uniform(1.0, 1.5), s * rng.uniform(0.9, 1.3), s * rng.uniform(0.6, 0.9)),
                  seed=100 + i, detail=3 if s > 0.85 else (2 if s > 0.45 else 1), cuts=6 if s > 0.85 else 4,
                  rough=0.1 if s > 0.85 else 0.16)
    root = rmb.finish(smooth=28, weighted=False)

    # -------- timber, rails, lanterns
    mb = MB("portal_frame", seed=12)
    W2 = 2.2 + 0.19  # post centre x (clear opening 4.4 m)
    for sx in (-1, 1):
        mb.box((0.38, 0.4, 3.8), "wood_timber", loc=(sx * W2, 0.2, 0), rot=(0, sx * -0.8, rng.uniform(-1, 1)), bevel=0.028, var=0.08)
        # foot block (sill) under each post
        mb.box((0.5, 0.5, 0.12), "wood_timber", loc=(sx * W2, 0.2, 0.0), bevel=0.02, var=0.12)
        # cap wedges + iron strap plates on the post/cap joint
        mb.box((0.3, 0.06, 0.07), "wood_timber", loc=(sx * W2, -0.01, 3.73), rot=(0, 0, 0), bevel=0.01, seg=1, var=0.15)
        mb.box((0.4, 0.012, 0.36), "rust", loc=(sx * W2, -0.006, 3.56), bevel=0.004, seg=1)
        for bz in (3.62, 3.84):
            for bx in (-0.12, 0.12):
                mb.cyl(0.022, 0.025, "steel_dark", loc=(sx * W2 + bx, -0.012, bz), rot=(90, 0, 0), sides=6)
    mb.box((5.9, 0.42, 0.44), "wood_timber", loc=(0, 0.21, 3.8), rot=(0.3, 0, 0), bevel=0.03, var=0.05)
    # headboards standing on the cap up to the rock arch
    for i in range(21):
        x = -2.85 + i * 0.285
        top = 4.24 + (5.18 - 4.24) * (1 - (abs(x) / 3.0) ** 2.2) + rng.uniform(-0.12, 0.05)
        top = max(top, 4.45)
        mb.box((0.27, 0.055, top - 4.24), "wood_planks", loc=(x, 0.075, 4.24), rot=(rng.uniform(-1.5, 1.5), 0, rng.uniform(-1, 1)),
               var=0.22, grain=2)
    # EST. 1849 plank across the headboards
    pf = mb.box((2.3, 0.05, 0.42), "wood_dark", loc=(0, 0.02, 4.38), rot=(0, 1.2, 0), bevel=0.01, seg=1)
    mb.face_label(pf, "label_est1849", normal=(0, -1, 0))
    for bx in (-1.05, 1.05):
        for bz in (4.45, 4.73):
            mb.cyl(0.014, 0.012, "steel_dark", loc=(bx, -0.006, bz), rot=(90, 0, 0), sides=6)
    # interior sets + lagging (fading into the dark)
    for y in (1.45, 2.6):
        for sx in (-1, 1):
            mb.box((0.3, 0.3, 3.8), "wood_timber", loc=(sx * (2.2 + 0.15), y, 0), rot=(0, 0, rng.uniform(-2, 2)), bevel=0.02, seg=1, var=0.15)
        mb.box((5.3, 0.32, 0.34), "wood_timber", loc=(0, y, 3.8), bevel=0.02, seg=1, var=0.12)
    for i in range(17):
        x = -2.4 + i * 0.3
        zt = 4.15 + 0.6 * (1 - (abs(x) / 2.9) ** 2)
        mb.box((0.25, 2.6, 0.05), "wood_planks", loc=(x, 1.7, min(zt, 4.6)), rot=(0, rng.uniform(-3, 3), 0), var=0.25)
    for sx in (-1, 1):
        for i in range(12):
            z = 0.15 + i * 0.31
            mb.box((0.05, 2.6, 0.27), "wood_planks", loc=(sx * 2.62, 1.7, z), rot=(rng.uniform(-2, 2), 0, 0), var=0.25)
    # cribbing wing walls: stacked logs along x, tie-backs into the face, retaining the spoil at the foot
    for sx in (-1, 1):
        for c_ in range(4):
            z = 0.14 + c_ * 0.27
            x0, x1 = sx * 3.05, sx * (5.3 - c_ * 0.35)
            mb.rod((x0, -0.62, z), (x1, -0.62, z), 0.14, "wood_timber", sides=7, var=0.15)
            for xt in (x0 + sx * 0.25, x1 - sx * 0.2):
                mb.rod((xt, -0.95, z + 0.135), (xt, 0.4, z + 0.135), 0.13, "wood_timber", sides=6, var=0.15)
        # spoil heaped behind/along the crib
        for i in range(6):
            mb.chunk((sx * rng.uniform(3.4, 5.0), rng.uniform(-0.3, 0.0), rng.uniform(1.0, 1.2)),
                     (0.4, 0.35, 0.3), seed=500 + i + (sx > 0) * 10, detail=1, cuts=4)
    # rails (0.6 m gauge) on sleepers and a gravel bed, 4 m out of the portal
    yb0, yb1 = -4.15, 2.95
    mb.mesh([(-0.95, yb0, 0.0), (0.95, yb0, 0.0), (0.68, yb0, 0.06), (-0.68, yb0, 0.06),
             (-0.95, yb1, 0.0), (0.95, yb1, 0.0), (0.68, yb1, 0.06), (-0.68, yb1, 0.06)],
            [(0, 1, 2, 3), (5, 4, 7, 6), (3, 2, 6, 7), (1, 5, 6, 2), (4, 0, 3, 7)], "gravel")
    y = yb1 - 0.25
    while y > yb0 + 0.1:
        mb.box((1.12, 0.16, 0.1), "wood_timber", loc=(rng.uniform(-0.03, 0.03), y, 0.045), rot=(0, 0, rng.uniform(-2.5, 2.5)),
               bevel=0.012, seg=1, var=0.25)
        y -= 0.58
    L = yb1 - yb0 - 0.15
    yc = (yb0 + 0.12 + yb1 - 0.03) / 2
    for sx in (-1, 1):
        x = sx * 0.32
        mb.box((0.075, L, 0.012), "rust", loc=(x, yc, 0.145))
        mb.box((0.015, L, 0.05), "rust", loc=(x, yc, 0.157))
        mb.box((0.042, L, 0.024), "steel", loc=(x, yc, 0.207), bevel=0.004, seg=1)
    # wheel stop at the outer end
    mb.box((1.05, 0.22, 0.2), "wood_timber", loc=(0, yb0 + 0.22, 0.231), bevel=0.02, seg=1, var=0.1)
    for sx in (-1, 1):
        mb.box((0.06, 0.24, 0.24), "rust", loc=(sx * 0.42, yb0 + 0.22, 0.2), bevel=0.004, seg=1)
    bl_ = lantern(mb, -W2, -1, root, "bulb_l")
    br_ = lantern(mb, W2, 1, root, "bulb_r")
    frame = mb.finish(smooth=50, weighted=True, parent=root)

    root.name = root.data.name = "portal"
    tunnel = lambda co, n: _tunnel_fade(co)  # noqa: E731
    EXTRAS["portal"] = tunnel
    EXTRAS["portal_frame"] = tunnel
    SHOTS["portal"] = [
        ("front", (0, -21, 2.4), (0, 0, 4.6), 30),
        ("three_quarter", (-13.5, -14.5, 3.6), (0.5, 0.5, 4.0), 32),
        ("close", (2.6, -5.8, 2.1), (-0.6, 0.4, 3.0), 28),
        ("far", (0, -75, 14), (0, 0, 5), 50),
    ]
    return root


def _tunnel_fade(co):
    import numpy as np
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    inside = (np.abs(x) < 3.15) & (z < 5.4)
    t = np.clip((y - 0.3) / (2.3 - 0.3), 0, 1)
    t = t * t * (3 - 2 * t)
    fade = np.where(inside & (y > 0.3), 1.0 - 0.965 * t, 1.0)
    foot = 0.72 + 0.28 * np.clip(z / 0.7, 0, 1)
    return fade * np.where(np.abs(x) > 3.0, foot, 1.0)


# ====================================================================== SIGNS
def face_child(name, x0, x1, z0, z1, y, parent, preview_png):
    """Flat board face, UV exactly 0-1 (u left->right, v bottom->top as seen from the front, -Y)."""
    m = MB(name, seed=5)
    m.quad([(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)], "sign_face", nogrime=True)
    o = m.finish(smooth=0, weighted=False)
    kit.strip_color(o)
    kit.attach(o, parent, ((x0 + x1) / 2, y, (z0 + z1) / 2))
    SIGNS.append((o, preview_png))
    return o


def build_sign_company():
    rng = random.Random(21)
    mb = MB("sign_company", seed=21)
    PX = 2.05
    for sx in (-1, 1):
        mb.box((0.22, 0.22, 4.76), "wood_timber", loc=(sx * PX, 0.0, 0), rot=(0, 0, rng.uniform(-1.5, 1.5)), bevel=0.02, var=0.08)
        mb.box((0.44, 0.44, 0.1), "concrete", loc=(sx * PX, 0, -0.02), bevel=0.025, seg=1)
        # knee braces from each post down to the ground behind (side stability)
        mb.beam((sx * PX, 0.1, 1.55), (sx * PX, 1.25, 0.02), 0.1, 0.12, "wood_timber", up=(1, 0, 0), bevel=0.01, seg=1, var=0.1)
        mb.box((0.18, 0.18, 0.05), "concrete", loc=(sx * PX, 1.25, -0.01), bevel=0.01, seg=1)
    # the sign is the claim's gate: the path runs under it, so the posts are tied by knee braces up under the board
    # (no cross-bracing in the opening) and everything hangs above 2.3 m
    for sx in (-1, 1):
        mb.beam((sx * (PX - 0.06), 0.1, 2.25), (sx * (PX - 0.78), 0.1, 2.97), 0.1, 0.13, "wood_timber", up=(0, -1, 0), bevel=0.01, seg=1, var=0.1)
        mb.cyl(0.02, 0.32, "steel_dark", loc=(sx * PX, 0.05, 2.3), rot=(-90, 0, 0), sides=6)
    mb.box((4.3, 0.14, 0.16), "wood_timber", loc=(0, 0.1, 2.97), bevel=0.01, seg=1, var=0.08)
    # rail under the board (the plaque hangs from it)
    mb.box((4.5, 0.12, 0.14), "wood_timber", loc=(0, -0.17, 2.98), bevel=0.012, seg=1, var=0.05)
    # board: 5 horizontal planks, 4.8 x 1.4, bottom at 2.6
    for i in range(5):
        mb.box((4.8, 0.03, 0.28), "wood_planks", loc=(0, -0.125, 3.2 + i * 0.28), var=0.15)
    # moulded frame proud of the face
    for z in (3.16, 4.55):
        mb.box((4.9, 0.07, 0.09), "wood_dark", loc=(0, -0.175, z), bevel=0.012, seg=2)
    for sx in (-1, 1):
        mb.box((0.09, 0.07, 1.39), "wood_dark", loc=(sx * 2.405, -0.175, 3.205), bevel=0.012, seg=2)
    # carriage bolts through frame + posts
    for sx in (-1, 1):
        for bz in (3.35, 3.85, 4.35):
            mb.cyl(0.022, 0.02, "steel_dark", loc=(sx * 2.405, -0.21, bz), rot=(90, 0, 0), sides=8, bevel=0.006)
    # little gable roof cap
    ridge, eave, yf, yb = 5.03, 4.7, -0.5, 0.22
    yr = (yf + yb) / 2
    for (ya, yb_) in ((yf, yr), (yr, yb)):
        za, zb = (eave, ridge) if ya == yf else (ridge, eave)
        for i in range(9):
            x0 = -2.62 + i * 0.582
            mb.poly([(x0, ya, za), (x0 + 0.575, ya, za), (x0 + 0.575, yb_, zb), (x0, yb_, zb)], "wood_planks", thick=0.035)
    mb.beam((-2.68, yr, ridge + 0.01), (2.68, yr, ridge + 0.01), 0.14, 0.05, "galvanized", bevel=0.005, seg=1)
    for sx in (-1, 1):
        mb.poly([(sx * 2.6, yf, eave - 0.02), (sx * 2.6, yr, ridge - 0.02), (sx * 2.6, yb, eave - 0.02)], "wood_planks", thick=0.03 * sx)
        mb.beam((sx * 2.63, yf - 0.03, eave - 0.06), (sx * 2.63, yr, ridge + 0.02), 0.04, 0.14, "wood_dark", up=(1, 0, 0), var=0.1)
        mb.beam((sx * 2.63, yr, ridge + 0.02), (sx * 2.63, yb + 0.03, eave - 0.06), 0.04, 0.14, "wood_dark", up=(1, 0, 0), var=0.1)
    # roof supports: a short post + purlin on each main post
    mb.box((4.9, 0.12, 0.1), "wood_timber", loc=(0, 0.0, 4.6), bevel=0.01, seg=1)
    # plaque hanging on S-hooks under the rail
    mb.box((2.24, 0.04, 0.5), "wood_planks", loc=(0, -0.155, 2.34), var=0.1)
    for z in (2.32, 2.82):
        mb.box((2.3, 0.06, 0.05), "wood_dark", loc=(0, -0.195, z - 0.01), bevel=0.008, seg=1)
    for sx in (-1, 1):
        mb.box((0.05, 0.06, 0.5), "wood_dark", loc=(sx * 1.13, -0.195, 2.33), bevel=0.008, seg=1)
        mb.tube([(sx * 0.9, -0.17, 2.98), (sx * 0.9, -0.2, 2.9), (sx * 0.9, -0.17, 2.85)], 0.008, "steel_dark", sides=4)
    root = mb.finish(smooth=50, weighted=True)
    face_child("sign_face", -2.36, 2.36, 3.205, 4.55, -0.168, root, "preview_signface.png")
    face_child("plaque_face", -1.105, 1.105, 2.335, 2.785, -0.2, root, "preview_plaque.png")
    SHOTS["sign_company"] = [("front", (1.2, -8.5, 2.2), (0, 0, 3.0), 35), ("three_quarter", (-5.5, -6.0, 2.6), (0, 0, 3.0), 35)]
    return root


def build_sign_forsale():
    rng = random.Random(31)
    mb = MB("sign_forsale", seed=31)
    px = -0.78
    mb.box((0.14, 0.14, 2.5), "wood_timber", loc=(px, 0, 0), rot=(0, 0, 3), bevel=0.014, var=0.1)
    mb.beam((px - 0.07, 0, 2.32), (0.86, 0, 2.32), 0.1, 0.12, "wood_timber", up=(0, -1, 0), bevel=0.012, seg=1, var=0.1)
    mb.beam((px, 0, 1.78), (px + 0.5, 0, 2.27), 0.07, 0.08, "wood_timber", up=(0, -1, 0), bevel=0.008, seg=1, var=0.1)
    mb.cyl(0.013, 0.02, "steel_dark", loc=(px + 0.07, -0.03, 2.3), rot=(90, 0, 0), sides=6)
    # board on eye hooks
    mb.box((1.34, 0.04, 0.82), "wood_planks", loc=(0.06, 0.02, 1.2), var=0.1)
    for z in (1.18, 2.0):
        mb.box((1.4, 0.06, 0.05), "wood_dark", loc=(0.06, -0.02, z), bevel=0.008, seg=1)
    for sx in (-1, 1):
        mb.box((0.05, 0.06, 0.84), "wood_dark", loc=(0.06 + sx * 0.675, -0.02, 1.18), bevel=0.008, seg=1)
        x = 0.06 + sx * 0.5
        mb.tube([(x, 0, 2.26), (x, -0.01, 2.14), (x, 0, 2.03)], 0.009, "steel_dark", sides=4)
    # stones piled round the foot of the post
    for i in range(5):
        a = i / 5 * math.tau + rng.uniform(-0.3, 0.3)
        mb.chunk((px + math.cos(a) * 0.2, math.sin(a) * 0.2, 0.05), (0.24, 0.2, 0.16), seed=40 + i, detail=0, cuts=3)
    root = mb.finish(smooth=50, weighted=True)
    face_child("forsale_face", -0.59, 0.71, 1.205, 1.995, -0.03, root, "preview_forsale.png")
    SHOTS["sign_forsale"] = [("front", (0.6, -4.2, 1.6), (0, 0, 1.4), 35)]
    return root


# ====================================================================== SHACK
def build_shack():
    """3 x 4 m board-and-batten site office on skids: corrugated gable roof (two rusted sheets), plank door,
    lit 4-pane window (emit_warm behind glass), stovepipe, steps, OFFICE board, hard hat on a nail, rain barrel."""
    rng = random.Random(41)
    mb = MB("shack", seed=41)
    W, D, F, H = 4.0, 3.0, 0.5, 2.45   # width x depth, floor height, wall height
    x0, x1, y0, y1 = -W / 2, W / 2, -D / 2, D / 2
    zt = F + H
    # foundation: concrete blocks, 3 skids, floor deck
    for x in (-1.75, 0.0, 1.75):
        for y in (-1.25, 1.25):
            mb.box((0.36, 0.36, 0.26), "concrete", loc=(x, y, 0), rot=(0, 0, rng.uniform(-6, 6)), bevel=0.02, seg=1, var=0.1)
    for y in (-1.25, 0.0, 1.25):
        mb.box((4.3, 0.2, 0.2), "wood_timber", loc=(0, y, 0.25), bevel=0.015, seg=1, var=0.12)
    mb.box((4.1, 3.1, 0.05), "wood_planks", loc=(0, 0, 0.45), var=0.05)

    BW = 0.3  # board width: every board is its own part (one texture board each), a batten over every joint

    def wall_x(y, xa, xb, za, zb, front):
        """Board-and-batten wall facing -Y (front=True) or +Y: vertical boards, battens over the joints."""
        t = 0.03
        n = max(1, round((xb - xa) / BW))
        bw = (xb - xa) / n
        for i in range(n):
            mb.box((bw - 0.006, t, zb - za), "wood_planks", loc=(xa + bw * (i + 0.5), y, za), grain=2, var=0.14)
        for i in range(1, n):
            x = xa + bw * i
            mb.box((0.06, 0.025, zb - za), "wood_planks", loc=(x, y - 0.027 if front else y + 0.027, za), grain=2, var=0.2)

    def wall_y(x, ya, yb, za, zb, right):
        t = 0.03
        n = max(1, round((yb - ya) / BW))
        bw = (yb - ya) / n
        for i in range(n):
            mb.box((t, bw - 0.006, zb - za), "wood_planks", loc=(x, ya + bw * (i + 0.5), za), grain=2, var=0.14)
        for i in range(1, n):
            y = ya + bw * i
            mb.box((0.025, 0.06, zb - za), "wood_planks", loc=(x + (0.027 if right else -0.027), y, za), grain=2, var=0.2)

    # front wall with door (x -1.45..-0.55) and window (x 0.35..1.35, z 1.35..2.25)
    dx0, dx1, dz1 = -1.45, -0.55, F + 2.05
    wx0, wx1, wz0, wz1 = 0.35, 1.35, F + 0.85, F + 1.75
    wall_x(y0, x0, dx0, F, zt, True)
    wall_x(y0, dx1, wx0, F, zt, True)
    wall_x(y0, wx1, x1, F, zt, True)
    wall_x(y0, dx0, dx1, dz1, zt, True)
    wall_x(y0, wx0, wx1, F, wz0, True)
    wall_x(y0, wx0, wx1, wz1, zt, True)
    wall_x(y1, x0, x1, F, zt, False)
    wall_y(x0, y0, y1, F, zt, False)
    wall_y(x1, y0, y1, F, zt, True)
    # gables
    ridge = zt + 0.85
    for sx in (-1, 1):
        mb.poly([(sx * W / 2, y0, zt), (sx * W / 2, y1, zt), (sx * W / 2, 0, ridge)], "wood_planks", thick=0.03 * sx)
    # corner boards + top plate trim
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.box((0.11, 0.11, H + 0.02), "wood_planks", loc=(sx * (W / 2 + 0.02), sy * (D / 2 + 0.02), F - 0.02), bevel=0.01, seg=1, var=0.15)
    # door: ledged-and-braced planks + frame + hinges + knob
    for i in range(6):  # six painted boards (one texture board each), ledges + brace in front
        mb.box((0.144, 0.04, 2.04), "wood_planks", loc=(dx0 + 0.075 + i * 0.15, y0 + 0.01, F), grain=2, var=0.12)
    for z in (F + 0.25, F + 1.0, F + 1.75):
        mb.box((0.86, 0.035, 0.14), "wood_dark", loc=((dx0 + dx1) / 2, y0 - 0.025, z), bevel=0.008, seg=1)
    mb.beam((dx0 + 0.08, y0 - 0.025, F + 0.38), (dx1 - 0.08, y0 - 0.025, F + 1.73), 0.13, 0.035, "wood_dark", up=(0, -1, 0), bevel=0.008, seg=1)
    for z in (F + 0.3, F + 1.8):
        mb.box((0.36, 0.012, 0.05), "steel_dark", loc=(dx0 + 0.18, y0 - 0.05, z), bevel=0.004, seg=1)
    mb.cyl(0.03, 0.05, "brass", loc=(dx1 - 0.1, y0 - 0.02, F + 1.02), rot=(90, 0, 0), sides=8)
    for x in (dx0 - 0.05, dx1 + 0.05):
        mb.box((0.1, 0.05, 2.1), "wood_painted_white", loc=(x, y0 - 0.03, F), bevel=0.008, seg=1)
    mb.box((1.1, 0.06, 0.1), "wood_painted_white", loc=((dx0 + dx1) / 2, y0 - 0.03, dz1), bevel=0.008, seg=1)
    # window: lit interior box behind glass, frame, muntins, sill
    yi0, yi1 = y0 + 0.02, y0 + 0.32
    mb.quad([(wx0, yi0, wz0), (wx0, yi1, wz0), (wx0, yi1, wz1), (wx0, yi0, wz1)], "wood_dark", uvs=((0, 0), (0.3, 0), (0.3, 0.9), (0, 0.9)), shade=0.5)
    mb.quad([(wx1, yi1, wz0), (wx1, yi0, wz0), (wx1, yi0, wz1), (wx1, yi1, wz1)], "wood_dark", uvs=((0, 0), (0.3, 0), (0.3, 0.9), (0, 0.9)), shade=0.5)
    mb.quad([(wx0, yi0, wz0), (wx1, yi0, wz0), (wx1, yi1, wz0), (wx0, yi1, wz0)], "wood_dark", uvs=((0, 0), (1, 0), (1, 0.3), (0, 0.3)), shade=0.5)
    mb.quad([(wx0, yi1, wz1), (wx1, yi1, wz1), (wx1, yi0, wz1), (wx0, yi0, wz1)], "wood_dark", uvs=((0, 0), (1, 0), (1, 0.3), (0, 0.3)), shade=0.5)
    mb.quad([(wx0, yi1, wz0), (wx0, yi1, wz1), (wx1, yi1, wz1), (wx1, yi1, wz0)], "emit_warm", nogrime=True)
    mb.quad([(wx0, y0 - 0.005, wz0), (wx1, y0 - 0.005, wz0), (wx1, y0 - 0.005, wz1), (wx0, y0 - 0.005, wz1)], "glass", nogrime=True)
    for z in (wz0 - 0.05, wz1):
        mb.box((wx1 - wx0 + 0.16, 0.06, 0.07), "wood_painted_white", loc=((wx0 + wx1) / 2, y0 - 0.03, z), bevel=0.008, seg=1)
    for x in (wx0 - 0.04, wx1 + 0.04):
        mb.box((0.08, 0.06, wz1 - wz0), "wood_painted_white", loc=(x, y0 - 0.03, wz0), bevel=0.008, seg=1)
    mb.box((0.035, 0.04, wz1 - wz0), "wood_painted_white", loc=((wx0 + wx1) / 2, y0 - 0.02, wz0))
    mb.box((wx1 - wx0, 0.04, 0.035), "wood_painted_white", loc=((wx0 + wx1) / 2, y0 - 0.02, (wz0 + wz1) / 2 - 0.017))
    mb.box((wx1 - wx0 + 0.24, 0.14, 0.045), "wood_painted_white", loc=((wx0 + wx1) / 2, y0 - 0.06, wz0 - 0.1), bevel=0.01, seg=1)
    # half curtain inside (canvas)
    mb.quad([(wx0 + 0.03, y0 + 0.1, wz0 + 0.45), (wx0 + 0.42, y0 + 0.1, wz0 + 0.45), (wx0 + 0.42, y0 + 0.1, wz1 - 0.03),
             (wx0 + 0.03, y0 + 0.1, wz1 - 0.03)], "canvas")
    # OFFICE board over the door
    pf = mb.box((0.78, 0.04, 0.2), "wood_dark", loc=((dx1 + wx0) / 2, y0 - 0.05, F + 1.72), bevel=0.006, seg=1)
    mb.face_label(pf, "label_office", normal=(0, -1, 0))
    # roof: rafters' fascia + corrugated sheets (2 rusted) + ridge cap. The front slope stops at the wall plate: the
    # porch roof breaks off it there at a shallower pitch.
    ov, side = 0.38, 0.28
    pitch = math.atan2(ridge - zt, D / 2)
    for sy in (-1, 1):
        ovs = 0.04 if sy < 0 else ov
        zl = zt - ovs * math.tan(pitch)
        if sy > 0:
            mb.beam((x0 - side, sy * (D / 2 + ovs), zl - 0.12), (x1 + side, sy * (D / 2 + ovs), zl - 0.12), 0.04, 0.16, "wood_planks", up=(0, 0, 1), bevel=0.008, seg=1)
        n = 6
        wsheet = (W + 2 * side) / n
        for i in range(n):
            xa = x0 - side + i * wsheet - 0.03
            mat = "rust" if (sy, i) in ((-1, 4), (1, 1)) else "corrugated"
            dz = rng.uniform(0, 0.01)
            ye, ze, zr_ = sy * (D / 2 + ovs), zl + 0.02 + dz, ridge + 0.04 + dz
            pts = [(xa, ye, ze), (xa + wsheet + 0.06, ye, ze), (xa + wsheet + 0.06, 0, zr_), (xa, 0, zr_)]
            mb.poly(pts if sy < 0 else pts[::-1], mat, thick=0.012, uvdir=((1, 0, 0), (0, -sy * math.cos(pitch), math.sin(pitch))))
        for sx in (-1, 1):
            mb.beam((sx * (W / 2 + side), sy * (D / 2 + ovs), zl - 0.05), (sx * (W / 2 + side), 0, ridge + 0.01), 0.04, 0.15, "wood_planks", up=(sx, 0, 0), var=0.1)
    for sy in (-1, 1):
        mb.poly([(x0 - side - 0.02, 0, ridge + 0.065), (x1 + side + 0.02, 0, ridge + 0.065),
                 (x1 + side + 0.02, sy * 0.18, ridge + 0.065 - 0.18 * math.tan(pitch)), (x0 - side - 0.02, sy * 0.18, ridge + 0.065 - 0.18 * math.tan(pitch))],
                "galvanized", thick=0.006)
    # ---- porch: plank deck on a rim joist + blocks, four posts, header, shed roof broken off the main roof at the wall
    # plate, side + front rails (gap for the steps in front of the door), a bench under the window
    PD = 1.5
    pf = y0 - PD                    # porch front
    zd = F - 0.03                   # deck top
    px0, px1 = x0 - 0.2, x1 + 0.2
    mb.box((px1 - px0, PD, 0.04), "wood_planks", loc=(0, y0 - PD / 2, zd - 0.04), grain=1, var=0.08)
    mb.box((px1 - px0 + 0.04, 0.08, 0.2), "wood_timber", loc=(0, pf + 0.04, zd - 0.24), bevel=0.01, seg=1, var=0.1)
    for x in (px0 + 0.06, 0.0, px1 - 0.06):
        mb.box((0.08, PD, 0.16), "wood_timber", loc=(x, y0 - PD / 2, zd - 0.2), var=0.12)
        mb.box((0.34, 0.34, 0.24), "concrete", loc=(x, pf + 0.2, 0), rot=(0, 0, rng.uniform(-6, 6)), bevel=0.02, seg=1, var=0.1)
    zh = zt - (PD + 0.06) * math.tan(math.radians(9)) - 0.02   # header top under the porch roof
    posts = (px0 + 0.07, -1.67, -0.33, px1 - 0.07)
    for x in (px0 + 0.07, px1 - 0.07):
        mb.box((0.12, 0.12, zh - zd), "wood_timber", loc=(x, pf + 0.08, zd), bevel=0.012, seg=1, var=0.1)
    for x in (-1.67, -0.33):
        mb.box((0.1, 0.1, 0.98), "wood_timber", loc=(x, pf + 0.08, zd), bevel=0.01, seg=1, var=0.1)
    mb.box((px1 - px0 + 0.1, 0.12, 0.18), "wood_timber", loc=(0, pf + 0.08, zh - 0.18), bevel=0.01, seg=1, var=0.08)
    for x in (px0 + 0.07, px1 - 0.07):   # knee braces post -> header
        mb.beam((x, pf + 0.08, zh - 0.6), (x + (0.45 if x < 0 else -0.45), pf + 0.08, zh - 0.17), 0.07, 0.07, "wood_timber", up=(0, 1, 0), var=0.1)
    # rails: sides (post -> wall) and the front either side of the steps
    for zr in (zd + 0.45, zd + 0.92):
        for x in (px0 + 0.07, px1 - 0.07):
            mb.beam((x, pf + 0.14, zr), (x, y0 - 0.05, zr), 0.06, 0.09, "wood_planks", up=(1, 0, 0), var=0.15)
        mb.beam((px0 + 0.12, pf + 0.08, zr), (-1.72, pf + 0.08, zr), 0.06, 0.09, "wood_planks", up=(0, 1, 0), var=0.15)
        mb.beam((-0.28, pf + 0.08, zr), (px1 - 0.12, pf + 0.08, zr), 0.06, 0.09, "wood_planks", up=(0, 1, 0), var=0.15)
    # shed roof: rafters + corrugated sheets (one rusty), from the wall plate out past the header
    rp = math.radians(9)
    ye = pf - 0.32
    zr0 = zt + 0.02
    zr1 = zr0 - (y0 - ye) * math.tan(rp)
    for x in (px0 + 0.07, -1.0, 0.85, px1 - 0.07):
        mb.beam((x, y0, zr0 - 0.08), (x, ye + 0.04, zr1 - 0.08), 0.06, 0.12, "wood_timber", up=(0, 0, 1), var=0.1)
    mb.beam((px0 - 0.1, ye, zr1 - 0.1), (px1 + 0.1, ye, zr1 - 0.1), 0.04, 0.15, "wood_planks", up=(0, 0, 1), bevel=0.008, seg=1)
    n = 6
    ws = (px1 - px0 + 0.2) / n
    for i in range(n):
        xa = px0 - 0.1 + i * ws - 0.03
        mat = "rust" if i == 1 else "corrugated"
        dz = rng.uniform(0, 0.008)
        pts = [(xa, ye, zr1 + dz), (xa + ws + 0.06, ye, zr1 + dz), (xa + ws + 0.06, y0 + 0.05, zr0 + 0.01 + dz), (xa, y0 + 0.05, zr0 + 0.01 + dz)]
        mb.poly(pts, mat, thick=0.012, uvdir=((1, 0, 0), (0, math.cos(rp), math.sin(rp))))
    mb.poly([(px0 - 0.12, y0 + 0.06, zr0 + 0.04), (px1 + 0.12, y0 + 0.06, zr0 + 0.04), (px1 + 0.12, y0 - 0.2, zr0 + 0.0),
             (px0 - 0.12, y0 - 0.2, zr0 + 0.0)], "galvanized", thick=0.006)
    # bench under the window
    bxc = 0.85
    mb.box((1.3, 0.36, 0.05), "wood_planks", loc=(bxc, y0 - 0.26, zd + 0.42), grain=0, var=0.12)
    for x in (bxc - 0.55, bxc + 0.55):
        mb.box((0.06, 0.3, 0.42), "wood_timber", loc=(x, y0 - 0.26, zd), var=0.1)
    # stovepipe with flashing cone and rain cap
    spx, spy = 1.25, 0.65
    zr = zt + (D / 2 - spy) * math.tan(pitch)
    mb.cyl(0.085, 1.6, "steel_dark", loc=(spx, spy, zr - 0.3), sides=10)
    mb.cyl(0.2, 0.18, "galvanized", loc=(spx, spy, zr - 0.05), r2=0.09, sides=10)
    mb.cyl(0.19, 0.12, "steel_dark", loc=(spx, spy, zr + 1.42), r2=0.02, sides=10)
    for k in range(3):
        a = k / 3 * math.tau
        mb.rod((spx + math.cos(a) * 0.085, spy + math.sin(a) * 0.085, zr + 1.3), (spx + math.cos(a) * 0.14, spy + math.sin(a) * 0.14, zr + 1.43), 0.008, "steel_dark", sides=4)
    # steps: two treads + the porch deck, in front of the door
    cx_ = (dx0 + dx1) / 2
    for h_, yf in ((0.155, pf - 0.62), (0.31, pf - 0.31)):
        mb.box((1.18, 0.31, h_ - 0.04), "wood_timber", loc=(cx_, yf + 0.155, 0.0), bevel=0.01, seg=1, var=0.1)
        mb.box((1.22, 0.33, 0.04), "wood_planks", loc=(cx_, yf + 0.155, h_ - 0.04), bevel=0.006, seg=1, var=0.15, grain=0)
    for sx in (-1, 1):  # stringers
        mb.beam((cx_ + sx * 0.62, pf - 0.64, 0.02), (cx_ + sx * 0.62, pf, zd - 0.06), 0.05, 0.18, "wood_timber", up=(1, 0, 0), var=0.1)
    # hard hat on a nail by the door
    hx, hy, hz = dx0 - 0.42, y0 - 0.05, F + 1.55
    mb.cyl(0.006, 0.07, "steel_dark", loc=(hx, y0 + 0.02, hz + 0.16), rot=(90, 0, 0), sides=4)
    hat = MB("hat", seed=1)
    bmesh.ops.create_uvsphere(hat.bm, u_segments=12, v_segments=6, radius=1.0, matrix=Matrix.Identity(4))
    hf = list(hat.bm.faces)
    for v in hat.bm.verts:
        if v.co.z < 0:
            v.co.z = 0
        v.co = Vector((v.co.x * 0.135, v.co.y * 0.16, v.co.z * 0.12))
    for f in hf:
        f.normal_update()
    hat._uv_world(hf, False)
    hat._paint(hf, "helmet_white", 1.0, 0, False)
    hat.cyl(0.165, 0.012, "helmet_white", loc=(0, 0.03, 0.0), sides=12)
    hat.box((0.03, 0.3, 0.02), "helmet_white", loc=(0, 0, 0.112), bevel=0.008, seg=1)
    ho = hat.finish(smooth=60, weighted=False)
    ho.rotation_euler = (math.radians(-80), 0, math.radians(10))
    ho.location = (hx, hy, hz)
    mb.absorb(ho)
    # wall lamp over the door + bulb child
    lx = dx0 - 0.24
    mb.box((0.07, 0.04, 0.14), "steel_dark", loc=(lx, y0 - 0.04, F + 1.82))
    mb.tube([(lx, y0 - 0.05, F + 1.9), (lx, y0 - 0.2, F + 2.0), (lx, y0 - 0.32, F + 1.96)], 0.012, "steel_dark", sides=5)
    mb.cyl(0.12, 0.09, "paint_green", loc=(lx, y0 - 0.33, F + 1.86), r2=0.03, sides=12, cap=False)
    # rain barrel at the back-right corner, under the eave
    bx_, by_ = x1 + 0.42, y1 - 0.45
    mb.cyl(0.3, 0.86, "wood_timber", loc=(bx_, by_, 0), sides=12, var=0.1)
    for z in (0.12, 0.7):
        mb.cyl(0.312, 0.05, "rust", loc=(bx_, by_, z), sides=12, cap=False)
    mb.cyl(0.27, 0.01, "rock_dark", loc=(bx_, by_, 0.8), sides=12)
    root = mb.finish(smooth=50, weighted=True)
    bulb("shack_bulb", (dx0 - 0.24, y0 - 0.33, F + 1.85), 0.035, root)
    SHOTS["shack"] = [("three_quarter", (-6.0, -7.5, 2.6), (0, 0, 1.6), 32), ("front", (0.4, -6.5, 1.5), (0, 0, 1.6), 32)]
    return root


# ====================================================================== shared structure helpers
def V3(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def sheave(name, R, width, parent, loc, spokes=8, mat="steel_dark", hub="cast_iron"):
    """Spoked rope sheave, axle along local X, origin at the hub (the game spins it about local X)."""
    m = MB(name, seed=7)
    w = width
    ri = R * 0.88
    prof = [(-w / 2, ri), (-w / 2, R), (-w * 0.18, R - 0.07 * R), (w * 0.18, R - 0.07 * R), (w / 2, R), (w / 2, ri)]
    m.revolve(prof, mat, seg=32)
    m.cylinder(R * 0.12, w * 1.6, hub, M=T((-w * 0.8, 0, 0)) @ R_((0, 90, 0)), sides=12, bevel=0.01)
    m.cylinder(R * 0.045, w * 2.6, "steel", M=T((-w * 1.3, 0, 0)) @ R_((0, 90, 0)), sides=8)
    for k in range(spokes):
        a = k / spokes * math.tau
        ca, sa = math.cos(a), math.sin(a)
        m.rod((0, ca * R * 0.1, sa * R * 0.1), (0, ca * ri * 1.01, sa * ri * 1.01), R * 0.035, mat, sides=6, r2=R * 0.026)
    o = m.finish(smooth=40, weighted=False)
    o.location = loc
    kit.attach(o, parent)
    return o


def R_(rot):
    return R(rot)


def ladder(mb, a, b, width=0.45, mat="steel_dark", rung=0.3, r=0.016, hoops=False, side=(1, 0, 0)):
    a, b = Vector(a), Vector(b)
    sd = Vector(side).normalized() * (width / 2)
    mb.rod(a - sd, b - sd, r * 1.4, mat, sides=6)
    mb.rod(a + sd, b + sd, r * 1.4, mat, sides=6)
    n = int((b - a).length / rung)
    for i in range(1, n):
        p = a.lerp(b, i / n)
        mb.rod(p - sd, p + sd, r, mat, sides=5)
    if hoops:
        d = (b - a).normalized()
        out = d.cross(Vector(side)).normalized()
        for i in range(1, int((b - a).length / 0.9)):
            p = a.lerp(b, (i * 0.9) / (b - a).length) if i * 0.9 > 2.2 else None
            if p is None:
                continue
            pts = [p + sd * math.cos(t) * 1.6 + out * (math.sin(t) * 0.7 + 0.0) for t in [j / 8 * math.pi for j in range(9)]]
            mb.tube(pts, 0.012, mat, sides=4)


def handrail(mb, pts, h=1.05, mat="paint_yellow", r=0.022, post=1.6, closed=False):
    pts = [Vector(p) for p in pts] + ([Vector(pts[0])] if closed else [])
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        n = max(1, int((b - a).length / post))
        for k in range(n + (1 if i == len(pts) - 2 and not closed else 0)):
            p = a.lerp(b, k / n)
            mb.rod(p, p + Vector((0, 0, h)), r, mat, sides=6)
        for hh in (h, h * 0.5):
            mb.rod(a + Vector((0, 0, hh)), b + Vector((0, 0, hh)), r, mat, sides=6)


def rope_tangent(cy, cz, R, py, pz, upper=True):
    """Tangent point on a sheave circle (centre cy,cz in the YZ plane) for a rope running to point (py,pz)."""
    dy, dz = py - cy, pz - cz
    L = math.hypot(dy, dz)
    phi = math.atan2(dz, dy)
    al = math.acos(min(1.0, R / L))
    c1 = (cy + R * math.cos(phi + al), cz + R * math.sin(phi + al))
    c2 = (cy + R * math.cos(phi - al), cz + R * math.sin(phi - al))
    return max(c1, c2, key=lambda c: c[1]) if upper else min(c1, c2, key=lambda c: c[1])


def pit(mb, cx, cy, w, d, z=0.035):
    """Dark shaft opening: a near-black quad (COLOR_0 ~0) inside a collar."""
    mb.quad([(cx - w / 2, cy - d / 2, z), (cx + w / 2, cy - d / 2, z), (cx + w / 2, cy + d / 2, z), (cx - w / 2, cy + d / 2, z)],
            "rock_dark", uvs=((0, 0), (w, 0), (w, d), (0, d)), shade=0.03)


# ====================================================================== HEADFRAME (WOOD)
def build_headframe_wood():
    """Timber gallows frame (~10.6 m) over a shaft collar: battered 4-post tower, back legs to a small winch,
    sheave deck with handrail, ladder, kibble on the rope. Child `sheave` spins about local X."""
    rng = random.Random(51)
    mb = MB("headframe_wood", seed=51)
    TB = "wood_timber"
    zd = 8.6
    sy0 = -1.0                      # shaft centre y
    feet = [(-1.35, -2.25), (1.35, -2.25), (-1.35, 0.25), (1.35, 0.25)]
    tops = [(-0.95, -1.9), (0.95, -1.9), (-0.95, -0.1), (0.95, -0.1)]

    def at(i, z):
        (fx, fy), (tx, ty) = feet[i], tops[i]
        t = (z - 0.25) / (zd - 0.25)
        return (fx + (tx - fx) * t, fy + (ty - fy) * t, z)

    for i, (fx, fy) in enumerate(feet):
        mb.box((0.55, 0.55, 0.3), "concrete", loc=(fx, fy, -0.06), bevel=0.02, seg=1, var=0.1)
        mb.beam(at(i, 0.24), at(i, zd), 0.3, 0.3, TB, bevel=0.022, var=0.1)
    levels = [0.25, 2.35, 4.45, 6.55, zd - 0.15]
    faces4 = [(0, 1), (2, 3), (0, 2), (1, 3)]
    for z in levels[1:]:
        for a, b in faces4:
            mb.beam(at(a, z), at(b, z), 0.2, 0.22, TB, ext=0.14, bevel=0.012, seg=1, var=0.12)
    for li in range(len(levels) - 1):
        z0, z1 = levels[li] + 0.12, levels[li + 1] - 0.1
        for fi, (a, b) in enumerate(faces4):
            if fi == 0 and li == 0:
                continue
            if (li + fi) % 2:
                a, b = b, a
            mb.beam(at(a, z0), at(b, z1), 0.13, 0.16, TB, var=0.15, bevel=0.008, seg=1)
    # back legs + struts + ties, landing behind toward the winch (+Y)
    btop = [(-0.95, -0.1, zd - 0.55), (0.95, -0.1, zd - 0.55)]
    bfoot = [(-1.55, 6.3, 0.22), (1.55, 6.3, 0.22)]
    for k in range(2):
        mb.beam(btop[k], bfoot[k], 0.32, 0.32, TB, bevel=0.02, var=0.08)
        mb.box((0.65, 0.65, 0.3), "concrete", loc=(bfoot[k][0], bfoot[k][1] - 0.15, -0.06), bevel=0.02, seg=1)
        mb.beam(at(2 + k, 4.45), V3(btop[k], bfoot[k], 0.47), 0.18, 0.2, TB, bevel=0.01, seg=1, var=0.12)
        mb.beam(at(2 + k, 2.35), V3(btop[k], bfoot[k], 0.72), 0.18, 0.2, TB, bevel=0.01, seg=1, var=0.12)
    for t in (0.32, 0.66):
        mb.beam(V3(btop[0], bfoot[0], t), V3(btop[1], bfoot[1], t), 0.18, 0.2, TB, ext=0.15, bevel=0.01, seg=1, var=0.12)
    mb.beam(V3(btop[0], bfoot[0], 0.32), V3(btop[1], bfoot[1], 0.66), 0.12, 0.14, TB, var=0.15)
    # deck: bearing beams + planks + toe boards + handrail
    for x in (-0.36, 0.36):
        mb.box((0.3, 2.6, 0.3), TB, loc=(x, -1.0, zd - 0.3), bevel=0.02, seg=1, var=0.08)
    for i in range(10):
        mb.box((2.9, 0.26, 0.06), "wood_planks", loc=(0, -2.2 + i * 0.265, zd), var=0.25)
    cx0, cx1, cy0, cy1 = -1.42, 1.42, -2.32, 0.32
    for x, y in ((cx0, cy0), (cx1, cy0), (cx1, cy1), (cx0, cy1), (0, cy0), (0, cy1), (cx0, -1.0), (cx1, -1.0)):
        mb.box((0.12, 0.12, 1.05), TB, loc=(x, y, zd + 0.06), bevel=0.01, seg=1, var=0.15)
    for (a, b) in (((cx0, cy0), (cx1, cy0)), ((cx1, cy0), (cx1, cy1)), ((cx1, cy1), (cx0, cy1)), ((cx0, cy1), (cx0, cy0))):
        for z in (zd + 1.05, zd + 0.55):
            mb.beam((a[0], a[1], z), (b[0], b[1], z), 0.07, 0.12, "wood_planks", ext=0.06, var=0.15)
    # sheave on cast bearing blocks; front tangent drops into the shaft
    Rs = 0.9
    sc = (0.0, sy0 + Rs, zd + 1.06)
    for x in (-0.36, 0.36):
        mb.box((0.22, 0.4, 0.3), "cast_iron", loc=(x, sc[1], zd + 0.06), bevel=0.02, seg=1)
        mb.box((0.16, 0.16, 0.7), "cast_iron", loc=(x, sc[1], zd + 0.36), bevel=0.015, seg=1)
    sheave("sheave", Rs, 0.16, None, sc)
    # ladder up the left side of the tower
    ladder(mb, (-1.62, -1.0, 0.0), (-1.2, -1.0, zd + 0.9), width=0.46, mat=TB, rung=0.32, r=0.025, side=(0, 1, 0))
    # shaft collar + pit + kibble on the rope
    for (a, b) in (((-1.05, sy0 - 1.05), (1.05, sy0 - 1.05)), ((-1.05, sy0 + 1.05), (1.05, sy0 + 1.05))):
        mb.beam((a[0], a[1], 0.15), (b[0], b[1], 0.15), 0.3, 0.3, TB, ext=0.15, bevel=0.02, seg=1, var=0.1)
    for x in (-1.05, 1.05):
        mb.beam((x, sy0 - 0.9, 0.15), (x, sy0 + 0.9, 0.15), 0.3, 0.3, TB, bevel=0.02, seg=1, var=0.1)
    pit(mb, 0.0, sy0, 1.8, 1.8)
    ky = sy0
    mb.cyl(0.42, 0.75, "steel_dark", loc=(0, ky, 1.1), sides=14, r2=0.46)
    mb.cyl(0.47, 0.06, "rust", loc=(0, ky, 1.82), sides=14, cap=False)
    mb.tube([(-0.44, ky, 1.82)] + [(-0.44 * math.cos(a), ky, 1.82 + 0.5 * math.sin(a)) for a in [i / 8 * math.pi for i in range(1, 9)]], 0.018, "steel_dark", sides=5)
    mb.cyl(0.015, 0.2, "steel_dark", loc=(0, ky, 2.32), sides=5)
    mb.rod((0, sc[1] - Rs, sc[2]), (0, ky, 2.5), 0.016, "cable", sides=5)
    # winch at the rear: drum on a skid + engine, rope from the sheave top
    wy = 4.7
    mb.box((1.8, 1.2, 0.2), TB, loc=(0, wy, 0.0), bevel=0.015, seg=1)
    for x in (-0.62, 0.62):
        mb.box((0.14, 0.5, 0.95), "cast_iron", loc=(x, wy, 0.2), bevel=0.015, seg=1)
    mb.cylinder(0.36, 1.1, "steel_dark", M=T((-0.55, wy, 0.92)) @ R((0, 90, 0)), sides=16, bevel=0.02)
    for x in (-0.56, 0.56):
        mb.cylinder(0.44, 0.04, "cast_iron", M=T((x - 0.02, wy, 0.92)) @ R((0, 90, 0)), sides=16)
    mb.box((0.7, 0.9, 0.75), "paint_green", loc=(1.35, wy, 0.2), bevel=0.04, seg=2)
    mb.cylinder(0.08, 0.8, "steel_dark", M=T((0.6, wy, 0.75)) @ R((0, 90, 0)), sides=8)
    ty_, tz_ = rope_tangent(sc[1], sc[2], Rs, wy, 0.92 + 0.36, upper=True)
    mb.rod((0, ty_, tz_), (0, wy - 0.05, 0.92 + 0.36), 0.016, "cable", sides=5)
    root = mb.finish(smooth=50, weighted=True)
    sh = bpy.data.objects["sheave"]
    kit.attach(sh, root)
    SHOTS["headframe_wood"] = [("three_quarter", (-11.5, -12.5, 5.0), (0, 1.0, 4.6), 32), ("close", (-3.0, -4.6, 9.8), (0, -0.1, 9.5), 30)]
    return root


# ====================================================================== ORE BIN
def build_ore_bin():
    """Timber ore bin on a braced trestle: plank hopper with iron corner straps, sloped bottom, steel chute and
    gate at the front, walkway + rail on top, a heap of ore showing over the rim."""
    rng = random.Random(61)
    mb = MB("ore_bin", seed=61)
    TB = "wood_timber"
    xs, ys = (-1.2, 0.0, 1.2), (-1.3, 1.3)
    zb0, zb1 = 2.8, 5.2   # high enough that the chute lip (1.95 m) clears a conveyor's loading hopper
    for x in xs:
        for y in ys:
            mb.box((0.48, 0.48, 0.28), "concrete", loc=(x, y, -0.05), bevel=0.02, seg=1, var=0.1)
            mb.box((0.26, 0.26, zb1 - 0.2), TB, loc=(x, y, 0.22), rot=(0, 0, rng.uniform(-2, 2)), bevel=0.02, var=0.1)
    for y in ys:
        mb.box((2.9, 0.24, 0.26), TB, loc=(0, y, zb0 - 0.26), bevel=0.015, seg=1, var=0.08)
        for k in range(2):
            a, b = (xs[k], y, 0.3), (xs[k + 1], y, zb0 - 0.3)
            if k:
                a, b = (xs[k], y, zb0 - 0.3), (xs[k + 1], y, 0.3)
            mb.beam(a, b, 0.13, 0.16, TB, up=(0, 1, 0), var=0.15, bevel=0.008, seg=1)
    for x in xs:
        mb.box((0.24, 2.9, 0.26), TB, loc=(x, 0, zb0 - 0.26), bevel=0.015, seg=1, var=0.08)
        mb.beam((x, -1.3, 0.35), (x, 1.3, zb0 - 0.35), 0.12, 0.15, TB, up=(1, 0, 0), var=0.15, bevel=0.008, seg=1)
    # hopper walls: horizontal planks, outside the posts
    nb = 10
    for i in range(nb):
        z = zb0 + i * (zb1 - zb0) / nb
        hh = (zb1 - zb0) / nb - 0.005
        for y in (-1.45, 1.45):
            mb.box((2.8, 0.05, hh), "wood_planks", loc=(0, y, z), var=0.25)
        for x in (-1.35, 1.35):
            mb.box((0.05, 2.95, hh), "wood_planks", loc=(x, 0, z), var=0.25)
    for x in (-1.38, 1.38):
        for y in (-1.48, 1.48):
            for z in (zb0 + 0.3, zb1 - 0.4):
                mb.box((0.1 if True else 0.1, 0.1, 0.12), "rust", loc=(x, y, z), bevel=0.005, seg=1)
    for z in (zb0 + 0.02, zb1 - 0.02):
        for y in (-1.5, 1.5):
            mb.box((2.95, 0.08, 0.12), TB, loc=(0, y, z - 0.06), bevel=0.01, seg=1, var=0.1)
    # sloped bottom (visible underneath) toward the front chute
    mb.poly([(-1.3, -1.42, zb0 + 0.05), (1.3, -1.42, zb0 + 0.05), (1.3, 1.42, zb0 + 0.75), (-1.3, 1.42, zb0 + 0.75)], "wood_planks", thick=-0.06)
    # chute: steel trough sloping forward + gate + lever
    ca, cb = (0, -1.5, zb0 + 0.25), (0, -2.75, zb0 - 0.85)
    M = kit.frame(ca, cb, up=(0, 0, 1))
    mb.cuboid((-0.45, -0.25, 0), (0.45, -0.22, 1.62), "rust", M)
    for sx in (-1, 1):
        mb.cuboid((sx * 0.45 - 0.015, -0.25, 0), (sx * 0.45 + 0.015, 0.12, 1.62), "rust", M)
    mb.box((0.95, 0.025, 0.55), "steel_dark", loc=(0, -1.52, zb0 + 0.08), bevel=0.006, seg=1)
    mb.rod((0.55, -1.56, zb0 + 0.3), (0.85, -1.9, zb0 + 1.1), 0.025, "steel_dark", sides=6)
    mb.cyl(0.045, 0.1, "steel_dark", loc=(0.85, -1.9, zb0 + 1.1), sides=6)
    # top walkway along the back + rail
    mb.box((3.0, 0.7, 0.06), "wood_planks", loc=(0, 1.85, zb1 - 0.02), var=0.15)
    for x in (-1.3, 1.3):
        mb.beam((x, 1.5, zb1 - 0.1), (x, 2.2, zb1 - 0.1), 0.12, 0.14, TB, var=0.1)
    handrail(mb, [(-1.45, 2.2, zb1 + 0.04), (1.45, 2.2, zb1 + 0.04)], h=1.0, mat=TB, r=0.03, post=1.6)
    # ore heap over the rim
    hb = MB("heap", seed=3)
    for i in range(14):
        hb.chunk((rng.uniform(-1.0, 1.0), rng.uniform(-1.1, 1.1), zb1 - 0.25 + rng.uniform(0, 0.12)),
                 (rng.uniform(0.35, 0.6),) * 2 + (0.3,), seed=600 + i, detail=2, cuts=4, mat="rock")
    mb.mesh([(-1.3, -1.42, zb1 - 0.3), (1.3, -1.42, zb1 - 0.3), (1.3, 1.42, zb1 - 0.3), (-1.3, 1.42, zb1 - 0.3), (0, 0, zb1 + 0.05)],
            [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4)], "rock")
    mb.absorb(hb.finish(smooth=30, weighted=False))
    root = mb.finish(smooth=50, weighted=True)
    SHOTS["ore_bin"] = [("three_quarter", (-6.5, -7.5, 3.5), (0, 0, 2.6), 32)]
    return root


# ====================================================================== HEADFRAME (STEEL)
def build_headframe_steel():
    """Riveted steel lattice headframe (~16.3 m): tapering 4-leg tower with girts and X-bracing, box-section back
    legs to the hoist side (+Y), sheave deck with yellow handrails, two sheaves (sheave_0/1, spin about local X),
    caged ladders, cage in its guides at the concrete collar. Empty `hoist_slot` = where the back ropes end."""
    rng = random.Random(71)
    mb = MB("headframe_steel", seed=71)
    P = "paint_red"
    zt = 13.5
    feet = [(-1.85, -2.7), (1.85, -2.7), (-1.85, 0.7), (1.85, 0.7)]
    tops = [(-1.15, -2.05), (1.15, -2.05), (-1.15, 0.05), (1.15, 0.05)]
    rolls = [0, 90, 270, 180]

    def at(i, z):
        (fx, fy), (tx, ty) = feet[i], tops[i]
        t = (z - 0.4) / (zt - 0.4)
        return (fx + (tx - fx) * t, fy + (ty - fy) * t, z)

    for i, (fx, fy) in enumerate(feet):
        mb.box((0.8, 0.8, 0.5), "concrete", loc=(fx, fy, -0.1), bevel=0.03, seg=1, var=0.1)
        mb.box((0.5, 0.5, 0.03), "steel_dark", loc=(fx, fy, 0.4))
        mb.angle_iron(at(i, 0.43), at(i, zt), 0.3, 0.028, P, roll=rolls[i])
    levels = [0.45, 2.65, 4.85, 7.05, 9.25, 11.45, zt - 0.05]
    sides = [(0, 1), (2, 3), (0, 2), (1, 3)]
    for z in levels[1:]:
        for a, b in sides:
            mb.angle_iron(at(a, z), at(b, z), 0.15, 0.014, P, roll=0)
    for li in range(len(levels) - 1):
        z0, z1 = levels[li] + 0.05, levels[li + 1] - 0.05
        for si, (a, b) in enumerate(sides):
            if si == 0 and li == 0:
                continue
            mb.angle_iron(at(a, z0), at(b, z1), 0.09, 0.01, P)
            mb.angle_iron(at(b, z0), at(a, z1), 0.09, 0.01, P, roll=90)
    # back legs: box section with lacing, landing behind on concrete
    btop = [(-1.15, 0.05, zt - 0.45), (1.15, 0.05, zt - 0.45)]
    bfoot = [(-2.05, 5.0, 0.35), (2.05, 5.0, 0.35)]   # steep back legs: the hoist house stands 5.9 m behind the shaft
    for k in range(2):
        mb.beam(btop[k], bfoot[k], 0.38, 0.42, P, bevel=0.01, seg=1)
        mb.box((1.0, 1.0, 0.45), "concrete", loc=(bfoot[k][0], bfoot[k][1] + 0.1, -0.1), bevel=0.03, seg=1)
        for z, t in ((4.85, 0.62), (9.25, 0.3)):
            mb.angle_iron(at(2 + k, z), V3(btop[k], bfoot[k], t), 0.14, 0.014, P)
    n = 7
    for i in range(n):
        t0, t1 = i / n, (i + 1) / n
        a = V3(btop[0], bfoot[0], t0 if i % 2 == 0 else t1)
        b = V3(btop[1], bfoot[1], t1 if i % 2 == 0 else t0)
        mb.angle_iron(a, b, 0.1, 0.012, P)
        mb.angle_iron(V3(btop[0], bfoot[0], t1), V3(btop[1], bfoot[1], t1), 0.12, 0.012, P)
    # deck, beams, handrail
    mb.box((3.3, 3.1, 0.07), "steel_dark", loc=(0, -1.0, zt))
    for x in (-1.1, -0.2, 0.2, 1.1):
        mb.box((0.18, 3.2, 0.32), P, loc=(x, -1.0, zt - 0.32))
    handrail(mb, [(-1.62, -2.52, zt + 0.07), (1.62, -2.52, zt + 0.07), (1.62, 0.52, zt + 0.07), (-1.62, 0.52, zt + 0.07)],
             h=1.1, mat="paint_yellow", r=0.024, post=1.2, closed=True)
    # sheaves (R 1.2) on bearing pedestals; the front tangent drops into the shaft at y = -1.0
    Rs = 1.2
    syc = -1.0 + Rs
    szc = zt + 1.48
    for k, x in enumerate((-0.62, 0.62)):
        for dx in (-0.2, 0.2):
            mb.box((0.16, 0.5, 0.36), "cast_iron", loc=(x + dx, syc, zt + 0.07), bevel=0.02, seg=1)
            mb.box((0.12, 0.2, 0.95), "cast_iron", loc=(x + dx, syc, zt + 0.42), bevel=0.015, seg=1)
        sheave(f"sheave_{k}", Rs, 0.2, None, (x, syc, szc), spokes=10, mat="paint_black")
    # caged ladder up the front-right leg to a mid landing, then to the deck
    ladder(mb, (2.2, -1.0, 0.0), (1.75, -1.0, 7.05), width=0.46, mat="paint_yellow", rung=0.3, r=0.016, hoops=True, side=(0, 1, 0))
    mb.box((1.0, 1.2, 0.05), "steel_dark", loc=(2.05, -1.0, 7.05))
    handrail(mb, [(1.55, -1.6, 7.1), (2.55, -1.6, 7.1), (2.55, -0.4, 7.1), (1.55, -0.4, 7.1)], h=1.0, mat="paint_yellow", r=0.02, post=1.2)
    ladder(mb, (1.75, -0.6, 7.1), (1.3, -0.6, zt), width=0.46, mat="paint_yellow", rung=0.3, r=0.016, hoops=True, side=(0, 1, 0))
    # collar, pit, cage guides, cage, ropes
    mb.box((4.6, 4.4, 0.3), "concrete", loc=(0, -1.0, -0.05), bevel=0.03, seg=1, var=0.05)
    pit(mb, 0.0, -1.0, 2.1, 1.9, z=0.255)
    for x in (-1.0, 1.0):
        mb.box((0.16, 0.22, 11.2), "wood_timber", loc=(x, -1.0, 0.25), var=0.1)
    cz0 = 0.28
    for x in (-0.82, 0.82):
        for y in (-1.72, -0.28):
            mb.box((0.07, 0.07, 2.65), "steel_dark", loc=(x, y, cz0))
    for z in (cz0, cz0 + 2.6):
        mb.box((1.72, 1.52, 0.07), "steel_dark", loc=(0, -1.0, z))
    for x in (-0.84, 0.84):
        mb.box((0.02, 1.4, 2.2), "galvanized", loc=(x, -1.0, cz0 + 0.3))
    mb.box((1.4, 0.02, 2.2), "galvanized", loc=(0, -0.26, cz0 + 0.3))
    mb.box((1.9, 0.18, 0.22), "steel_dark", loc=(0, -1.0, cz0 + 2.68), bevel=0.01, seg=1)
    hs = (0.0, 5.95, 3.25)
    for x in (-0.62, 0.62):
        mb.rod((x, syc - Rs, szc), (x * 0.2, -1.0, cz0 + 2.9), 0.02, "cable", sides=5)
        ty_, tz_ = rope_tangent(syc, szc, Rs, hs[1], hs[2], upper=True)
        mb.rod((x, ty_, tz_), (x * 0.5, hs[1], hs[2]), 0.02, "cable", sides=5)
    root = mb.finish(smooth=50, weighted=True)
    for k in range(2):
        kit.attach(bpy.data.objects[f"sheave_{k}"], root)
    kit.empty("hoist_slot", hs, parent=root)
    SHOTS["headframe_steel"] = [("three_quarter", (-16.0, -17.0, 6.0), (0, 2.0, 7.6), 32), ("close", (-4.0, -6.0, 15.6), (0, -0.4, 14.6), 30)]
    return root


# ====================================================================== HOIST HOUSE
def build_hoist_house():
    """Corrugated-iron hoist house (4.8 x 4.4 m) on a concrete plinth: gable to the front with the cable slot high
    in it (the ropes from the headframe enter here, empty `cable_slot`), man door, lit side windows, sliding
    door, ridge ventilator, engine exhaust, DANGER sign."""
    rng = random.Random(81)
    mb = MB("hoist_house", seed=81)
    W, D, H = 4.8, 4.4, 3.8
    x0, x1, y0, y1 = -W / 2, W / 2, -D / 2, D / 2
    zp = 0.4
    zt = zp + H
    rise = (W / 2) * math.tan(math.radians(24))
    mb.box((W + 0.3, D + 0.3, zp), "concrete", loc=(0, 0, 0), bevel=0.03, seg=1)
    VERT = ((1, 0, 0), (0, 0, 1))
    VERTY = ((0, 1, 0), (0, 0, 1))
    # front gable wall pieces around the slot (x -1.1..1.1, z 3.25..3.8) and the door (x -2.3..-1.4, z 0.4..2.5)
    sx0, sx1, sz0, sz1 = -0.8, 0.8, zp + 2.6, zp + 3.1
    dx0, dx1, dz1 = -2.0, -1.1, zp + 2.1
    def wallF(xa, xb, za, zb, mat="corrugated"):
        mb.poly([(xa, y0, za), (xb, y0, za), (xb, y0, zb), (xa, y0, zb)][::-1], mat, thick=0.03, uvdir=VERT)
    wallF(x0, dx0, zp, zt)
    wallF(dx1, sx0, zp, zt)
    wallF(sx1, x1, zp, zt)
    wallF(dx0, dx1, dz1, zt)
    wallF(sx0, sx1, zp, sz0)
    wallF(sx0, sx1, sz1, zt)
    mb.poly([(x1, y0, zt), (0, y0, zt + rise), (x0, y0, zt)], "corrugated", thick=0.03, uvdir=VERT)
    mb.poly([(x0, y1, zp), (x1, y1, zp), (x1, y1, zt), (0, y1, zt + rise), (x0, y1, zt)][::-1][::-1], "corrugated", thick=-0.03, uvdir=VERT)
    # long walls with 2 lit windows each (+ sliding door on +X)
    for sx in (-1, 1):
        x = sx * W / 2
        wins = [(-1.5, -0.5), (0.5, 1.5)] if sx < 0 else [(-1.75, -0.85)]
        segs, last = [], y0
        for (wa, wb) in wins:
            segs.append((last, wa, zp, zt))
            segs.append((wa, wb, zp, zp + 1.3))
            segs.append((wa, wb, zp + 2.3, zt))
            last = wb
        if sx > 0:
            segs.append((last, -0.3, zp, zt))
            segs.append((-0.3, 1.7, zp + 3.0, zt))
            segs.append((1.7, y1, zp, zt))
        else:
            segs.append((last, y1, zp, zt))
        for (ya, yb, za, zb) in segs:
            pts = [(x, ya, za), (x, yb, za), (x, yb, zb), (x, ya, zb)]
            mb.poly(pts if sx > 0 else pts[::-1], "corrugated", thick=-0.03 * sx * -1, uvdir=VERTY)
        for (wa, wb) in wins:
            wz0, wz1 = zp + 1.3, zp + 2.3
            mb.quad([(x - sx * 0.25, wa, wz0), (x - sx * 0.25, wb, wz0), (x - sx * 0.25, wb, wz1), (x - sx * 0.25, wa, wz1)][::sx], "emit_warm", nogrime=True)
            for z in (wz0 - 0.06, wz1):
                mb.box((0.1, wb - wa + 0.16, 0.08), "wood_painted_white", loc=(x + sx * 0.03, (wa + wb) / 2, z), bevel=0.008, seg=1)
            for y in (wa - 0.04, wb + 0.04):
                mb.box((0.1, 0.08, wz1 - wz0), "wood_painted_white", loc=(x + sx * 0.03, y, wz0), bevel=0.008, seg=1)
            mb.box((0.06, 0.04, wz1 - wz0), "wood_painted_white", loc=(x + sx * 0.03, (wa + wb) / 2, wz0))
            mb.box((0.06, wb - wa, 0.04), "wood_painted_white", loc=(x + sx * 0.03, (wa + wb) / 2, (wz0 + wz1) / 2))
            mb.quad([(x + sx * 0.0, wa, wz0), (x + sx * 0.0, wb, wz0), (x + sx * 0.0, wb, wz1), (x + sx * 0.0, wa, wz1)][::sx], "glass", nogrime=True)
            for yy in (wa, wb):
                mb.quad([(x, yy, wz0), (x - sx * 0.25, yy, wz0), (x - sx * 0.25, yy, wz1), (x, yy, wz1)], "wood_dark", shade=0.4,
                        uvs=((0, 0), (0.25, 0), (0.25, 1), (0, 1)))
    # sliding door on +X with its track
    mb.box((0.06, 2.1, 2.95), "corrugated", loc=(W / 2 + 0.08, 0.7, zp + 0.02), grain=1)
    mb.quad([(W / 2 - 0.02, -0.3, zp), (W / 2 - 0.02, 1.7, zp), (W / 2 - 0.02, 1.7, zp + 3.0), (W / 2 - 0.02, -0.3, zp + 3.0)], "rock_dark", shade=0.15)
    mb.box((0.08, 4.0, 0.1), "steel_dark", loc=(W / 2 + 0.1, 0.5, zp + 3.0))
    # front: man door, slot frame + dark slot box, DANGER sign
    for i in range(6):
        mb.box((0.144, 0.05, 2.08), "wood_planks", loc=(dx0 + 0.075 + i * 0.15, y0 + 0.02, zp), grain=2, var=0.12)
    for z in (zp + 0.3, zp + 1.75):
        mb.box((0.86, 0.035, 0.14), "wood_dark", loc=((dx0 + dx1) / 2, y0 - 0.02, z), bevel=0.006, seg=1, grain=0)
    mb.beam((dx0 + 0.08, y0 - 0.02, zp + 0.42), (dx1 - 0.08, y0 - 0.02, zp + 1.7), 0.12, 0.035, "wood_dark", up=(0, -1, 0), bevel=0.006, seg=1)
    for x in (dx0 - 0.05, dx1 + 0.05):
        mb.box((0.1, 0.06, 2.15), "wood_timber", loc=(x, y0 - 0.03, zp), bevel=0.008, seg=1)
    mb.box((1.1, 0.06, 0.1), "wood_timber", loc=((dx0 + dx1) / 2, y0 - 0.03, dz1), bevel=0.008, seg=1)
    mb.cyl(0.03, 0.05, "brass", loc=(dx1 - 0.12, y0 - 0.02, zp + 1.0), rot=(90, 0, 0), sides=8)
    for z in (sz0 - 0.08, sz1):
        mb.box((sx1 - sx0 + 0.3, 0.12, 0.1), "wood_timber", loc=(0, y0 - 0.04, z), bevel=0.01, seg=1)
    for x in (sx0 - 0.08, sx1 + 0.08):
        mb.box((0.14, 0.12, sz1 - sz0 + 0.1), "wood_timber", loc=(x, y0 - 0.04, sz0 - 0.05), bevel=0.01, seg=1)
    yi = y0 + 0.9
    mb.quad([(sx0, yi, sz0), (sx1, yi, sz0), (sx1, yi, sz1), (sx0, yi, sz1)][::-1][::-1], "rock_dark", shade=0.05,
            uvs=((0, 0), (2.2, 0), (2.2, 0.5), (0, 0.5)))
    for (a, b, c, d) in (((sx0, y0, sz0), (sx1, y0, sz0), (sx1, yi, sz0), (sx0, yi, sz0)),
                         ((sx0, yi, sz1), (sx1, yi, sz1), (sx1, y0, sz1), (sx0, y0, sz1))):
        mb.quad([a, b, c, d], "wood_dark", shade=0.25, uvs=((0, 0), (2.2, 0), (2.2, 0.9), (0, 0.9)))
    for x in (sx0, sx1):
        mb.quad([(x, y0, sz0), (x, yi, sz0), (x, yi, sz1), (x, y0, sz1)][::(1 if x > 0 else -1)], "wood_dark", shade=0.25,
                uvs=((0, 0), (0.9, 0), (0.9, 0.5), (0, 0.5)))
    pf = mb.box((0.52, 0.03, 0.39), "steel", loc=(-0.45, y0 - 0.03, zp + 1.3), bevel=0.004, seg=1)
    mb.face_label(pf, "label_danger", normal=(0, -1, 0))
    # roof: corrugated sheets (ridge along Y), fascia, barge boards, ridge cap, ventilator, exhaust
    ov = 0.35
    pitch = math.radians(24)
    for sx in (-1, 1):
        xe, ze = sx * (W / 2 + ov), zt - ov * math.tan(pitch)
        n = 8
        for i in range(n):
            ya = y0 - 0.25 + i * (D + 0.5) / n
            yb = ya + (D + 0.5) / n + 0.05
            mat = "rust" if (sx, i) in ((-1, 2), (1, 5), (1, 6)) else "corrugated"
            pts = [(xe, ya, ze + 0.03), (xe, yb, ze + 0.03), (0, yb, zt + rise + 0.05), (0, ya, zt + rise + 0.05)]
            mb.poly(pts if sx > 0 else pts[::-1], mat, thick=0.012, uvdir=((0, 1, 0), (sx * -math.cos(pitch), 0, math.sin(pitch))))
        mb.beam((xe, y0 - 0.3, ze - 0.1), (xe, y1 + 0.3, ze - 0.1), 0.04, 0.16, "wood_planks", var=0.1)
        for y in (y0 - 0.27, y1 + 0.27):
            mb.beam((xe, y, ze - 0.05), (0, y, zt + rise + 0.02), 0.04, 0.16, "wood_planks", up=(0, 1, 0), var=0.1)
    mb.beam((0, y0 - 0.3, zt + rise + 0.08), (0, y1 + 0.3, zt + rise + 0.08), 0.32, 0.04, "galvanized", up=(0, 0, 1))
    mb.cyl(0.3, 0.45, "galvanized", loc=(0, 0.5, zt + rise - 0.05), sides=14)
    mb.cyl(0.44, 0.26, "galvanized", loc=(0, 0.5, zt + rise + 0.4), r2=0.06, sides=14)
    # engine exhaust: a stovepipe through the roof with flashing and a rain cap
    epx, epy = 1.25, 1.35
    ezr = zt + (W / 2 - epx) * math.tan(pitch)
    mb.cyl(0.11, 2.1, "steel_dark", loc=(epx, epy, ezr - 0.3), sides=10)
    mb.cyl(0.24, 0.16, "galvanized", loc=(epx, epy, ezr - 0.04), r2=0.12, sides=10)
    mb.cyl(0.24, 0.14, "steel_dark", loc=(epx, epy, ezr + 1.9), r2=0.03, sides=10)
    for k in range(3):
        a_ = k / 3 * math.tau
        mb.rod((epx + math.cos(a_) * 0.11, epy + math.sin(a_) * 0.11, ezr + 1.78), (epx + math.cos(a_) * 0.18, epy + math.sin(a_) * 0.18, ezr + 1.92), 0.01, "steel_dark", sides=4)
    # back gable (faces the road on a claim): a lit window and a fuel line coming in low
    bwx, bwz0, bwz1 = 0.9, zp + 1.3, zp + 2.25
    mb.quad([(bwx - 0.5, y1 + 0.012, bwz0), (bwx + 0.5, y1 + 0.012, bwz0), (bwx + 0.5, y1 + 0.012, bwz1), (bwx - 0.5, y1 + 0.012, bwz1)][::-1], "emit_warm", nogrime=True)
    mb.quad([(bwx - 0.5, y1 + 0.02, bwz0), (bwx + 0.5, y1 + 0.02, bwz0), (bwx + 0.5, y1 + 0.02, bwz1), (bwx - 0.5, y1 + 0.02, bwz1)][::-1], "glass", nogrime=True)
    for z in (bwz0 - 0.06, bwz1):
        mb.box((1.16, 0.1, 0.08), "wood_painted_white", loc=(bwx, y1 + 0.04, z), bevel=0.008, seg=1)
    for x in (bwx - 0.54, bwx + 0.54):
        mb.box((0.08, 0.1, bwz1 - bwz0), "wood_painted_white", loc=(x, y1 + 0.04, bwz0), bevel=0.008, seg=1)
    mb.box((0.04, 0.06, bwz1 - bwz0), "wood_painted_white", loc=(bwx, y1 + 0.035, bwz0))
    mb.box((1.0, 0.06, 0.04), "wood_painted_white", loc=(bwx, y1 + 0.035, (bwz0 + bwz1) / 2))
    mb.tube([(x0 - 1.4, 0.2, 0.06), (x0 - 0.5, 0.2, 0.1), (x0 - 0.12, 0.2, 0.45), (x0 - 0.06, 0.2, 0.8), (x0 + 0.05, 0.2, 0.82)], 0.03, "steel_dark", sides=6)
    root = mb.finish(smooth=50, weighted=True)
    kit.empty("cable_slot", (0, y0 - 0.05, (sz0 + sz1) / 2), parent=root)
    SHOTS["hoist_house"] = [("three_quarter", (-8.0, -9.5, 3.5), (0, 0, 2.6), 32), ("side", (9.0, -6.0, 3.0), (0, 0.5, 2.4), 32),
                           ("back", (5.5, 9.5, 3.0), (0, 0, 2.2), 32)]
    return root


# ====================================================================== CONVEYOR
def build_conveyor():
    """~12 m inclined troughed belt conveyor (24 deg): yellow channel stringers with cross members, 3-roll troughing
    idlers + return rollers, rubber belt, head pulley with motor/gearbox and discharge chute (front, -Y, 6.45 m up),
    tail pulley with loading hopper (back, +Y). Supports sit where the claim layout has room for them: a tail stand,
    a straight bent at t 0.3, a splayed bent at t 0.6 and a straight head tower at t 0.95 (t = 0 tail .. 1 head)."""
    mb = MB("conveyor", seed=91)
    PY = "paint_yellow"
    yt, yh, zt_, zh = 6.0, -6.0, 1.05, 6.45
    L = math.hypot(yt - yh, zh - zt_)
    d = Vector((0, (yh - yt) / L, (zh - zt_) / L))
    up = Vector((0, -d.z, d.y)) * -1
    if up.z < 0:
        up = -up

    def P(t, off_up=0.0, x=0.0):
        p = Vector((x, yt + (yh - yt) * t, zt_ + (zh - zt_) * t)) + up * off_up
        return tuple(p)

    for sx in (-1, 1):
        mb.beam(P(-0.02, -0.2, sx * 0.56), P(1.02, -0.2, sx * 0.56), 0.08, 0.24, PY, up=tuple(up), bevel=0.006, seg=1)
    n = 10
    for i in range(n + 1):
        t = i / n
        mb.beam(P(t, -0.3, -0.56), P(t, -0.3, 0.56), 0.07, 0.07, PY, up=tuple(up))
        if 0 < i < n:
            mb.beam(P(t - 0.05, -0.3, -0.56), P(t + 0.05, -0.12, 0.56), 0.04, 0.04, PY, up=tuple(up))
    # troughing idlers
    for i in range(1, 10):
        t = i / 10
        c = Vector(P(t, -0.02))
        a30 = math.radians(30)
        for k in (-1, 0, 1):
            if k == 0:
                a_, b_ = c + Vector((-0.2, 0, 0)), c + Vector((0.2, 0, 0))
            else:
                o = c + Vector((k * 0.21, 0, 0))
                a_ = o
                b_ = o + Vector((k * 0.3 * math.cos(a30), 0, 0)) + up * (0.3 * math.sin(a30))
            mb.rod(a_, b_, 0.055, "steel", sides=8, up=tuple(up))
        mb.beam(c + up * -0.08 + Vector((-0.55, 0, 0)), c + up * -0.08 + Vector((0.55, 0, 0)), 0.05, 0.05, PY, up=tuple(up))
        for k in (-1, 1):
            mb.beam(c + up * -0.08 + Vector((k * 0.21, 0, 0)), c + up * 0.02 + Vector((k * 0.21, 0, 0)), 0.03, 0.06, PY, up=tuple(d))
            mb.beam(c + up * -0.08 + Vector((k * 0.5, 0, 0)), c + up * 0.17 + Vector((k * 0.5, 0, 0)), 0.03, 0.06, PY, up=tuple(d))
    for i in range(1, 6):
        t = i / 6
        mb.rod(P(t, -0.42, -0.5), P(t, -0.42, 0.5), 0.05, "steel", sides=8, up=tuple(up))
    # belt: troughed top run + flat return
    w0, w1 = 0.2, 0.2 + 0.3 * math.cos(math.radians(30))
    hz = 0.3 * math.sin(math.radians(30))
    for (xa, za, xb, zb) in ((-w1, hz, -w0, 0.0), (-w0, 0.0, w0, 0.0), (w0, 0.0, w1, hz)):
        pa, pb = Vector(P(0.0, 0.035 + za, xa)), Vector(P(0.0, 0.035 + zb, xb))
        pc, pd = Vector(P(1.0, 0.035 + zb, xb)), Vector(P(1.0, 0.035 + za, xa))
        mb.poly([pa, pb, pc, pd], "rubber", thick=-0.012, uvdir=((1, 0, 0), tuple(d)))
    mb.poly([P(0.0, -0.37, -0.45), P(0.0, -0.37, 0.45), P(1.0, -0.37, 0.45), P(1.0, -0.37, -0.45)], "rubber", thick=0.01, uvdir=((1, 0, 0), tuple(d)))
    # pulleys
    hp = Vector(P(1.0, -0.2))
    mb.cylinder(0.3, 1.0, "steel_dark", M=T(hp + Vector((-0.5, 0, 0))) @ R((0, 90, 0)), sides=16, bevel=0.02)
    tp = Vector(P(0.0, -0.2))
    mb.cylinder(0.26, 1.0, "steel_dark", M=T(tp + Vector((-0.5, 0, 0))) @ R((0, 90, 0)), sides=16, bevel=0.02)
    # head: drive (motor + gearbox) on a bracket, discharge hood + chute
    mb.box((0.5, 0.7, 0.06), PY, loc=(0.95, hp.y, hp.z - 0.38))
    mb.box((0.42, 0.42, 0.42), "paint_green", loc=(0.95, hp.y + 0.05, hp.z - 0.32), bevel=0.03, seg=2)
    mb.cylinder(0.2, 0.55, "paint_green", M=T((0.95, hp.y + 0.26, hp.z - 0.12)) @ R((-90, 0, 0)), sides=12, bevel=0.02)
    mb.cylinder(0.06, 0.4, "steel", M=T((0.55, hp.y, hp.z)) @ R((0, 90, 0)), sides=8)
    hy, hz = hp.y - 0.12, hp.z
    mb.mesh([(-0.6, hy + 0.35, hz - 0.45), (0.6, hy + 0.35, hz - 0.45), (0.6, hy - 0.5, hz - 0.45), (-0.6, hy - 0.5, hz - 0.45),
             (-0.6, hy + 0.35, hz + 0.4), (0.6, hy + 0.35, hz + 0.4), (0.6, hy - 0.5, hz + 0.1), (-0.6, hy - 0.5, hz + 0.1)],
            [(4, 5, 6, 7), (1, 2, 6, 5), (3, 0, 4, 7), (2, 3, 7, 6), (0, 1, 5, 4)], "rust")
    mb.beam((0, hy - 0.25, hz - 0.45), (0, hy - 0.75, hz - 1.15), 0.62, 0.42, "rust", up=(0, -1, 0))
    # tail: loading hopper
    tz = tp.z + 0.45
    mb.mesh([(-0.75, tp.y - 0.65, tz + 0.55), (0.75, tp.y - 0.65, tz + 0.55), (0.75, tp.y + 0.65, tz + 0.55), (-0.75, tp.y + 0.65, tz + 0.55),
             (-0.3, tp.y - 0.35, tz), (0.3, tp.y - 0.35, tz), (0.3, tp.y + 0.35, tz), (-0.3, tp.y + 0.35, tz)],
            [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (4, 5, 1, 0)[::-1], (3, 2, 1, 0)], "rust")
    # trestle bents + head tower + tail stand
    for t, splay in ((0.3, 0.0), (0.6, 0.5)):
        top = Vector(P(t, -0.32))
        for sx in (-1, 1):
            a = top + Vector((sx * 0.56, 0, 0))
            b = Vector((sx * (0.56 + splay), top.y, 0.25))
            mb.beam(a, b, 0.14, 0.14, PY, up=(0, 1, 0))
            mb.box((0.6, 0.6, 0.3), "concrete", loc=(b.x, b.y, -0.05), bevel=0.02, seg=1)
            mb.box((0.36, 0.36, 0.03), "steel_dark", loc=(b.x, b.y, 0.25))
        mb.beam(Vector((-(0.56 + splay * 0.55), top.y, top.z * 0.45)), Vector(((0.56 + splay * 0.55), top.y, top.z * 0.45)), 0.1, 0.1, PY)
        mb.beam(Vector((-(0.56 + splay * 0.2), top.y, top.z * 0.83)), Vector(((0.56 + splay * 0.85), top.y, top.z * 0.15)), 0.07, 0.07, PY)
        if splay == 0.0:
            mb.beam(Vector((-0.56, top.y, top.z * 0.15)), Vector((0.56, top.y, top.z * 0.8)), 0.07, 0.07, PY)
    for sx in (-1, 1):
        a = Vector(P(0.02, -0.32, sx * 0.56))
        mb.beam(a, (a.x, a.y, 0.25), 0.12, 0.12, PY)
        mb.box((0.5, 0.5, 0.3), "concrete", loc=(a.x, a.y, -0.05), bevel=0.02, seg=1)
    # the head hangs off the building it feeds: knee struts from under the head frame to a wall plate 1 m past the
    # head pulley (the mill's crusher-house wall), no posts in the yard below
    hw = Vector(P(1.0, -0.32))
    wy = hw.y - 1.0
    for sx in (-1, 1):
        mb.beam(Vector(P(0.9, -0.32, sx * 0.56)), Vector((sx * 0.56, wy + 0.04, hw.z - 1.9)), 0.1, 0.1, PY, up=(1, 0, 0))
        mb.beam(Vector(P(0.97, -0.32, sx * 0.56)), Vector((sx * 0.56, wy + 0.04, hw.z - 0.25)), 0.1, 0.1, PY, up=(1, 0, 0))
    mb.box((1.5, 0.06, 2.0), "steel_dark", loc=(0, wy + 0.03, hw.z - 2.15), bevel=0.01, seg=1)
    root = mb.finish(smooth=50, weighted=True)
    SHOTS["conveyor"] = [("three_quarter", (-9.5, -9.0, 5.0), (0, 0, 3.2), 32), ("head", (2.5, -9.0, 6.8), (0, -5.5, 6.0), 30)]
    return root


# ====================================================================== MILL
def corr_wall(mb, a, b, z0, z1, out, mat="corrugated"):
    """Vertical corrugated wall from a to b (x,y), facing `out` (x,y unit), corrugations vertical."""
    ax, ay = a
    bx, by = b
    pts = [(ax, ay, z0), (bx, by, z0), (bx, by, z1), (ax, ay, z1)]
    nrm = Vector((by - ay, -(bx - ax), 0)).normalized()
    if nrm.dot(Vector((out[0], out[1], 0))) < 0:
        pts = pts[::-1]
    along = Vector((bx - ax, by - ay, 0)).normalized()
    mb.poly(pts, mat, thick=0.03, uvdir=(tuple(along), (0, 0, 1)))


def gable_roof_x(mb, x0, x1, y0, y1, ze, rise, ov=0.35, side=0.3, mats=("corrugated",), rusty=()):
    """Gable roof with the ridge along X: two corrugated slopes (sheets down the slope) + fascia + barges."""
    ym = (y0 + y1) / 2
    half = (y1 - y0) / 2
    tanp = rise / half
    zl = ze - ov * tanp
    for sy in (-1, 1):
        n = max(3, int((x1 - x0 + 2 * side) / 0.85))
        for i in range(n):
            xa = x0 - side + i * (x1 - x0 + 2 * side) / n
            xb = xa + (x1 - x0 + 2 * side) / n + 0.04
            mat = "rust" if (sy, i) in rusty else mats[0]
            ye = ym + sy * (half + ov)
            pts = [(xa, ye, zl + 0.03), (xb, ye, zl + 0.03), (xb, ym, ze + rise + 0.05), (xa, ym, ze + rise + 0.05)]
            mb.poly(pts if sy < 0 else pts[::-1], mat, thick=0.012, uvdir=((1, 0, 0), (0, -sy, tanp)))
        mb.beam((x0 - side, ym + sy * (half + ov), zl - 0.1), (x1 + side, ym + sy * (half + ov), zl - 0.1), 0.04, 0.16, "wood_planks", var=0.1)
    mb.beam((x0 - side, ym, ze + rise + 0.09), (x1 + side, ym, ze + rise + 0.09), 0.3, 0.04, "galvanized")
    for x in (x0 - side, x1 + side):
        for sy in (-1, 1):
            mb.beam((x, ym + sy * (half + ov), zl - 0.05), (x, ym, ze + rise + 0.02), 0.04, 0.16, "wood_planks", up=(1, 0, 0), var=0.1)
    return zl


def window(mb, cx, y, z0, w, h, out=-1, emit="emit_warm", panes=(2, 3), axis="x"):
    """Multi-pane window in a wall facing -Y (out=-1) / +Y, or along x-facing walls when axis='y' (cx is y, y is x)."""
    def P(u, d, z):
        return (cx + u, y + d * out, z) if axis == "x" else (y + d * out, cx + u, z)
    u0, u1, z1 = -w / 2, w / 2, z0 + h
    em = [P(u0, -0.18, z0), P(u1, -0.18, z0), P(u1, -0.18, z1), P(u0, -0.18, z1)]
    if (out < 0) == (axis == "x"):
        em = em[::-1]
    mb.quad(em[::-1] if axis == "x" else em, emit, nogrime=True)
    for zz in (z0 - 0.05, z1):
        a, b = P(u0 - 0.07, 0.03, zz), P(u1 + 0.07, 0.03, zz)
        mb.beam(a, b, 0.07, 0.07, "wood_painted_white", up=(0, 0, 1) if axis == "x" else (0, 0, 1))
    for uu in (u0 - 0.035, u1 + 0.035):
        mb.beam(P(uu, 0.03, z0), P(uu, 0.03, z1), 0.07, 0.06, "wood_painted_white")
    nx, nz = panes
    for i in range(1, nx):
        uu = u0 + (u1 - u0) * i / nx
        mb.beam(P(uu, 0.02, z0), P(uu, 0.02, z1), 0.035, 0.03, "wood_painted_white")
    for j in range(1, nz):
        zz = z0 + h * j / nz
        mb.beam(P(u0, 0.02, zz), P(u1, 0.02, zz), 0.035, 0.03, "wood_painted_white")
    for uu in (u0, u1):
        q = [P(uu, 0.0, z0), P(uu, -0.18, z0), P(uu, -0.18, z1), P(uu, 0.0, z1)]
        mb.quad(q, "wood_dark", shade=0.35, uvs=((0, 0), (0.18, 0), (0.18, h), (0, h)))


def build_mill():
    """Gold mill on a 7.1 x 9.7 m footprint: three corrugated/timber halls stepping down toward the front (crusher
    house 9.4 m at the back, stamp hall with a clerestory, low amalgamation room with the big sliding door), rows of
    glowing windows (emit_warm / emit_amber), tall tapered brick stack at the back-left corner (empty `stack_top`
    at its mouth) with a flue from the crusher house, a timber leach tank + launder at the front-right, and the feed
    hatch high on the crusher house's +X wall at (3.4, y 3.35..4.65, z 4.9..6.1) where the conveyor's head chute
    comes in."""
    rng = random.Random(101)
    mb = MB("mill", seed=101)
    XA0 = -1.4
    blocks = [("A", XA0, 3.4, 1.4, 4.85, 9.4, 1.5), ("B", -3.7, 3.4, -1.8, 1.4, 6.6, 1.5), ("C", -3.7, 1.8, -4.85, -1.8, 3.9, 1.0)]
    for name, x0, x1, y0, y1, h, rise in blocks:
        mb.box((x1 - x0 + 0.3, y1 - y0 + 0.3, 0.45), "concrete", loc=((x0 + x1) / 2, (y0 + y1) / 2, -0.05), bevel=0.03, seg=1, var=0.06)
        zw = 0.4
        wain = 1.25
        # board wainscot, corrugated above
        for (a, b, out) in (((x0, y0), (x1, y0), (0, -1)), ((x1, y0), (x1, y1), (1, 0)), ((x1, y1), (x0, y1), (0, 1)), ((x0, y1), (x0, y0), (-1, 0))):
            if name == "C" and out == (0, 1):
                continue
            if name == "B" and out == (0, 1):
                # only the stretch the crusher house doesn't cover is seen
                a, b = (XA0, y1), (x0, y1)
            corr_wall(mb, a, b, zw + wain, h, out, "corrugated")
            corr_wall(mb, a, b, zw, zw + wain, out, "wood_planks")
        for (x, y) in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
            mb.box((0.16, 0.16, h - zw + 0.02), "wood_timber", loc=(x, y, zw), bevel=0.012, seg=1, var=0.1)
        for (a, b) in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x0, y1), (x0, y0))):
            mb.beam((a[0], a[1], zw + wain), (b[0], b[1], zw + wain), 0.06, 0.1, "wood_timber", ext=0.05, var=0.1)
        # gable end walls (ridge along X: gables face +-X)
        for x, sgn in ((x0, -1), (x1, 1)):
            ym = (y0 + y1) / 2
            pts = [(x, y0, h), (x, y1, h), (x, ym, h + rise)]
            mb.poly(pts if sgn > 0 else pts[::-1], "corrugated", thick=0.03, uvdir=((0, 1, 0), (0, 0, 1)))
        gable_roof_x(mb, x0, x1, y0, y1, h, rise, rusty={"A": ((-1, 2),), "B": ((1, 4),), "C": ((-1, 1), (1, 5))}[name])
    # windows: front of C (warm), sides of B (amber: furnace glow), front + sides of A (warm)
    window(mb, -3.05, -4.85, 1.6, 0.9, 1.3, out=-1, emit="emit_warm", panes=(2, 3))
    for cy in (-0.95, 0.55):
        window(mb, cy, -3.7, 2.2, 0.9, 1.9, out=-1, emit="emit_amber", panes=(2, 4), axis="y")
        window(mb, cy, 3.4, 2.2, 0.9, 1.9, out=1, emit="emit_amber", panes=(2, 4), axis="y")
    for cx in (-2.6, -0.6, 1.6):
        window(mb, cx, -1.8, 4.75, 0.95, 1.15, out=-1, emit="emit_amber", panes=(2, 2))
    for cx in (0.0, 2.0):
        window(mb, cx, 1.4, 7.1, 0.9, 1.15, out=-1, emit="emit_warm", panes=(2, 2))
    window(mb, 2.0, XA0, 6.6, 0.9, 1.3, out=-1, emit="emit_warm", panes=(2, 3), axis="y")
    window(mb, 1.9, 3.4, 7.3, 0.8, 1.1, out=1, emit="emit_warm", panes=(2, 2), axis="y")
    # big sliding door on C front + track
    sdx = 0.55
    # barn-style board door: vertical boards, three ledges + two braces, hung on a track with two rollers
    for i in range(10):
        mb.box((0.186, 0.05, 2.6), "wood_planks", loc=(sdx - 0.95 + 0.095 + i * 0.19, -4.92, 0.42), grain=2, var=0.14)
    mb.beam((sdx - 1.1, -4.97, 3.08), (sdx + 1.25, -4.97, 3.08), 0.06, 0.1, "steel_dark")
    for z in (0.62, 1.6, 2.58):
        mb.box((1.86, 0.04, 0.14), "wood_dark", loc=(sdx, -4.965, z), bevel=0.006, seg=1, grain=0)
    for z0, z1 in ((0.76, 1.55), (1.74, 2.53)):
        mb.beam((sdx - 0.85, -4.965, z0), (sdx + 0.85, -4.965, z1), 0.13, 0.035, "wood_dark", up=(0, -1, 0), bevel=0.006, seg=1)
    for x in (sdx - 0.5, sdx + 0.5):
        mb.cyl(0.07, 0.04, "steel_dark", loc=(x, -4.99, 2.98), rot=(90, 0, 0), sides=8)
    mb.box((0.04, 0.03, 0.3), "steel_dark", loc=(sdx + 0.8, -4.99, 1.3))
    # the claim office moves into the mill's front room: man door, OFFICE board, a little awning, a step
    odx0, odx1, oy = -2.05, -1.15, -4.85
    mb.quad([(odx0, oy - 0.012, 0.42), (odx1, oy - 0.012, 0.42), (odx1, oy - 0.012, 2.5), (odx0, oy - 0.012, 2.5)], "rock_dark", shade=0.2)
    for i in range(6):
        mb.box((0.144, 0.04, 2.04), "wood_planks", loc=(odx0 + 0.075 + i * 0.15, oy - 0.03, 0.43), grain=2, var=0.12)
    for z in (0.65, 1.45, 2.2):
        mb.box((0.86, 0.035, 0.13), "wood_dark", loc=((odx0 + odx1) / 2, oy - 0.06, z), bevel=0.006, seg=1, grain=0)
    mb.beam((odx0 + 0.08, oy - 0.06, 0.75), (odx1 - 0.08, oy - 0.06, 2.1), 0.12, 0.035, "wood_dark", up=(0, -1, 0), bevel=0.006, seg=1)
    mb.cyl(0.03, 0.05, "brass", loc=(odx1 - 0.1, oy - 0.07, 1.42), rot=(90, 0, 0), sides=8)
    for x in (odx0 - 0.05, odx1 + 0.05):
        mb.box((0.1, 0.06, 2.12), "wood_painted_white", loc=(x, oy - 0.04, 0.42), bevel=0.008, seg=1)
    mb.box((1.1, 0.06, 0.1), "wood_painted_white", loc=((odx0 + odx1) / 2, oy - 0.04, 2.5), bevel=0.008, seg=1)
    pfo = mb.box((0.78, 0.04, 0.2), "wood_dark", loc=((odx0 + odx1) / 2, oy - 0.06, 2.68), bevel=0.006, seg=1)
    mb.face_label(pfo, "label_office", normal=(0, -1, 0))
    mb.box((1.3, 0.5, 0.2), "concrete", loc=((odx0 + odx1) / 2, oy - 0.4, 0.0), bevel=0.02, seg=1)
    aw = math.radians(16)
    for x in (odx0 - 0.25, odx1 + 0.25):
        mb.beam((x, oy - 0.02, 2.55), (x, oy - 0.85, 2.95), 0.05, 0.05, "steel_dark", up=(1, 0, 0))
    mb.poly([(odx0 - 0.35, oy - 1.0, 2.98), (odx1 + 0.35, oy - 1.0, 2.98), (odx1 + 0.35, oy - 0.01, 2.98 + 0.99 * math.tan(aw)),
             (odx0 - 0.35, oy - 0.01, 2.98 + 0.99 * math.tan(aw))], "corrugated", thick=0.012, uvdir=((1, 0, 0), (0, math.cos(aw), math.sin(aw))))
    # clerestory monitor on the stamp hall ridge
    zB = 6.6 + 1.5
    ym = -0.2
    mb.box((5.2, 1.3, 0.7), "wood_planks", loc=(-0.4, ym, zB - 0.25), var=0.1)
    for sy in (-1, 1):
        for i in range(8):
            x = -2.8 + i * 0.62
            mb.beam((x, ym + sy * 0.66, zB - 0.15), (x + 0.5, ym + sy * 0.66, zB - 0.15), 0.05, 0.03, "wood_dark", up=(0, sy, 1))
        mb.poly([(-3.1, ym + sy * 0.9, zB + 0.45), (2.3, ym + sy * 0.9, zB + 0.45), (2.3, ym, zB + 0.75), (-3.1, ym, zB + 0.75)][::(-sy)],
                "corrugated", thick=0.012, uvdir=((1, 0, 0), (0, -sy, 0.3)))
    # feed hatch high on the crusher house's +X wall: dark opening, timber frame, a rusty hood over it
    hy0, hy1, hz0, hz1 = 3.35, 4.65, 4.9, 6.1
    mb.quad([(3.43, hy0, hz0), (3.43, hy1, hz0), (3.43, hy1, hz1), (3.43, hy0, hz1)], "rock_dark", shade=0.05,
            uvs=((0, 0), (1.3, 0), (1.3, 1.2), (0, 1.2)))
    mb.box((0.7, 1.7, 0.06), "rust", loc=(3.72, (hy0 + hy1) / 2, hz1 + 0.12), rot=(0, 12, 0))
    for y in (hy0 - 0.06, hy1 + 0.06):
        mb.box((0.12, 0.12, hz1 - hz0 + 0.14), "wood_timber", loc=(3.47, y, hz0 - 0.08))
    mb.box((0.14, hy1 - hy0 + 0.3, 0.12), "wood_timber", loc=(3.47, (hy0 + hy1) / 2, hz0 - 0.14))
    # stack at the back-left corner: brick plinth + tapered round stack + bands + corbelled cap; flue from A
    sx_, sy_ = -2.6, 3.85
    mb.box((1.9, 1.9, 1.7), "brick", loc=(sx_, sy_, 0), bevel=0.02, seg=1)
    mb.box((2.1, 2.1, 0.18), "concrete", loc=(sx_, sy_, 1.7), bevel=0.02, seg=1)
    mb.cyl(0.78, 15.6, "brick", loc=(sx_, sy_, 1.88), r2=0.54, sides=16, cap=False)
    zc = 1.88 + 15.6
    mb.cyl(0.64, 0.42, "brick", loc=(sx_, sy_, zc - 0.05), r2=0.68, sides=16, cap=False)
    mb.revolve([(0.0, 0.68), (0.1, 0.68), (0.1, 0.46), (0.0, 0.46)], "brick", M=T((sx_, sy_, zc + 0.37)) @ R((0, -90, 0)), seg=16)
    mb.quad([(sx_ - 0.43, sy_ - 0.43, zc + 0.05), (sx_ + 0.43, sy_ - 0.43, zc + 0.05), (sx_ + 0.43, sy_ + 0.43, zc + 0.05), (sx_ - 0.43, sy_ + 0.43, zc + 0.05)],
            "rock_dark", shade=0.03, uvs=((0, 0), (1, 0), (1, 1), (0, 1)))
    for k in range(5):
        z = 3.5 + k * 3.0
        r_ = 0.78 + (0.54 - 0.78) * (z - 1.88) / 15.6
        mb.cyl(r_ + 0.025, 0.09, "steel_dark", loc=(sx_, sy_, z), r2=r_ + 0.02, sides=16)
    mb.beam((XA0, sy_, 2.75), (sx_ + 0.62, sy_, 2.75), 0.5, 0.5, "steel_dark", bevel=0.01, seg=1)
    # leach tank + launder at the front-right (beside the amalgamation room)
    tx, ty = 2.75, -3.45
    mb.box((1.9, 1.9, 0.3), "concrete", loc=(tx, ty, -0.05), bevel=0.02, seg=1)
    mb.cyl(0.82, 1.6, "wood_timber", loc=(tx, ty, 0.25), sides=18, var=0.1, cap=False)
    for z in (0.5, 1.05, 1.65):
        mb.cyl(0.845, 0.06, "rust", loc=(tx, ty, z), sides=18, cap=False)
    mb.cyl(0.78, 0.02, "rock_dark", loc=(tx, ty, 1.68), sides=18, shade=0.5)
    mb.box((0.3, 1.45, 0.22), "wood_planks", loc=(tx, -2.5, 2.05), var=0.1, grain=1)
    for sx in (-1, 1):
        mb.box((0.04, 1.45, 0.16), "wood_planks", loc=(tx + sx * 0.15, -2.5, 2.27), var=0.1, grain=1)
    mb.box((0.1, 0.1, 2.05), "wood_timber", loc=(tx, -2.15, 0.0))
    root = mb.finish(smooth=50, weighted=True)
    kit.empty("stack_top", (sx_, sy_, zc + 0.5), parent=root)
    SHOTS["mill"] = [("three_quarter", (-15.0, -16.5, 6.5), (0.0, 0, 6.0), 32), ("front", (5.0, -18.0, 3.0), (0, 0, 5.0), 32),
                     ("side", (16.0, 7.0, 7.0), (0, 1.0, 6.0), 32)]
    return root


# ====================================================================== SMALL PROPS
def build_fuel_tank_small():
    """1,000 l horizontal fuel tank on steel saddles + concrete pad: DIESEL decal, filler, vent, hand pump, hose."""
    mb = MB("fuel_tank_small", seed=111)
    mb.box((2.6, 1.3, 0.12), "concrete", loc=(0, 0, 0), bevel=0.02, seg=1)
    r, L = 0.55, 2.2
    zc = 0.12 + 0.45 + r
    for x in (-0.7, 0.7):
        mb.box((0.12, 1.0, 0.45), "steel_dark", loc=(x, 0, 0.12))
        mb.revolve([(-0.05, r + 0.02), (0.05, r + 0.02), (0.05, r - 0.01), (-0.05, r - 0.01)], "steel_dark", M=T((x, 0, zc)), seg=20)
    tf = mb.cylinder(r, L, "paint_red", M=T((-L / 2, 0, zc)) @ R((0, 90, 0)), sides=20, bevel=0.04, seg=2)
    # DIESEL decal: a curved patch on the -Y side (u along +X, v up)
    nseg = 6
    rr = r + 0.004
    for i in range(nseg):
        a0 = math.radians(210 - i * 60 / nseg)
        a1 = math.radians(210 - (i + 1) * 60 / nseg)
        y0_, z0_ = rr * math.cos(a0), zc + rr * math.sin(a0)
        y1_, z1_ = rr * math.cos(a1), zc + rr * math.sin(a1)
        mb.quad([(-0.62, y0_, z0_), (0.62, y0_, z0_), (0.62, y1_, z1_), (-0.62, y1_, z1_)], "label_fuel",
                uvs=((0, i / nseg), (1, i / nseg), (1, (i + 1) / nseg), (0, (i + 1) / nseg)), nogrime=True)
    mb.cyl(0.09, 0.12, "steel_dark", loc=(0.55, 0, zc + r - 0.02), sides=10, bevel=0.01)
    mb.cyl(0.03, 0.5, "steel_dark", loc=(-0.75, 0.2, zc + r - 0.03), sides=6)
    mb.cyl(0.05, 0.06, "steel_dark", loc=(-0.75, 0.2, zc + r + 0.47), r2=0.02, sides=6)
    # hand pump on top + hose
    mb.cyl(0.05, 0.55, "paint_green", loc=(0.0, -0.1, zc + r - 0.02), sides=8)
    mb.box((0.16, 0.12, 0.2), "paint_green", loc=(0.0, -0.1, zc + r + 0.5), bevel=0.02, seg=1)
    mb.rod((0.0, -0.1, zc + r + 0.62), (0.35, -0.1, zc + r + 0.82), 0.015, "steel", sides=5)
    hose = [(0.0, -0.18, zc + r + 0.55), (0.05, -0.45, zc + r + 0.3), (0.2, -0.62, zc), (0.35, -0.62, zc - 0.5), (0.5, -0.55, zc - 0.7)]
    mb.tube(hose, 0.02, "rubber", sides=6)
    mb.rod((0.5, -0.55, zc - 0.7), (0.5, -0.55, zc - 0.85), 0.025, "brass", sides=6)
    root = mb.finish(smooth=50, weighted=True)
    SHOTS["fuel_tank_small"] = [("three_quarter", (-2.8, -3.6, 2.0), (0, 0, 0.9), 35)]
    return root


def build_ore_cart():
    """Surface V-skip car (side-tipping, 0.6 m gauge) on a 2.4 m rail section with sleepers."""
    mb = MB("ore_cart", seed=121)
    for i in range(5):
        mb.box((1.05, 0.16, 0.1), "wood_timber", loc=(0, -1.0 + i * 0.5, 0), rot=(0, 0, (i - 2) * 1.2), bevel=0.012, seg=1, var=0.25)
    for sx in (-1, 1):
        x = sx * 0.32
        mb.box((0.075, 2.4, 0.012), "rust", loc=(x, 0, 0.1))
        mb.box((0.015, 2.4, 0.05), "rust", loc=(x, 0, 0.112))
        mb.box((0.042, 2.4, 0.024), "steel", loc=(x, 0, 0.162), bevel=0.004, seg=1)
    zr = 0.186
    # chassis + wheels
    for y in (-0.42, 0.42):
        mb.cylinder(0.03, 0.8, "steel", M=T((-0.4, y, zr + 0.17)) @ R((0, 90, 0)), sides=8)
        for sx in (-1, 1):
            mb.cylinder(0.17, 0.07, "cast_iron", M=T((sx * 0.32 - 0.035, y, zr + 0.17)) @ R((0, 90, 0)), sides=14, bevel=0.01)
            mb.cylinder(0.19, 0.02, "cast_iron", M=T((sx * 0.32 - (0.045 if sx > 0 else -0.025), y, zr + 0.17)) @ R((0, 90, 0)), sides=14)
    for sx in (-1, 1):
        mb.box((0.08, 1.4, 0.14), "steel_dark", loc=(sx * 0.42, 0, zr + 0.24), bevel=0.008, seg=1)
    mb.box((0.9, 0.1, 0.1), "steel_dark", loc=(0, 0.72, zr + 0.25))
    mb.box((0.9, 0.1, 0.1), "steel_dark", loc=(0, -0.72, zr + 0.25))
    # V body on trunnions
    zb = zr + 0.42
    prof = [(-0.18, zb), (0.18, zb), (0.55, zb + 0.62), (-0.55, zb + 0.62)]
    for y0_, y1_ in ((-0.68, 0.68),):
        vs = [(x, y0_, z) for x, z in prof] + [(x, y1_, z) for x, z in prof]
        mb.mesh(vs, [(0, 1, 2, 3)[::-1], (4, 5, 6, 7), (0, 1, 5, 4)[::-1], (1, 2, 6, 5)[::-1], (2, 3, 7, 6)[::-1], (3, 0, 4, 7)[::-1]], "rust")
    for y in (-0.69, 0.69):
        mb.revolve([(-0.03, 0.12), (0.03, 0.12), (0.03, 0.04), (-0.03, 0.04)], "steel_dark", M=T((0, y, zb + 0.3)) @ R((0, 0, 90)), seg=12)
    for z in (zb + 0.2, zb + 0.6):
        for sx in (-1, 1):
            w = 0.18 + (0.55 - 0.18) * (z - zb) / 0.62
            mb.box((0.03, 1.4, 0.05), "steel_dark", loc=(sx * (w + 0.01), 0, z - 0.025))
    # a few lumps of ore in it
    for i in range(6):
        mb.chunk((random.Random(i).uniform(-0.3, 0.3), random.Random(i + 9).uniform(-0.5, 0.5), zb + 0.58), (0.26, 0.24, 0.18), seed=130 + i, detail=0, cuts=3)
    root = mb.finish(smooth=50, weighted=True)
    SHOTS["ore_cart"] = [("three_quarter", (-2.6, -3.0, 1.6), (0, 0, 0.6), 35)]
    return root


def heap(name, mat, size, seed, lumps, lump_size):
    rng = random.Random(seed)
    mb = MB(name, seed=seed)
    sx, sy, h = size
    nr, ns = 7, 22
    verts, faces = [(0, 0, h)], []
    for i in range(1, nr + 1):
        t = i / nr
        for k in range(ns):
            a = k / ns * math.tau
            rr = t * (1 + 0.22 * fbm3((math.cos(a) * 1.3, math.sin(a) * 1.3, seed), 2))
            z = h * (1 - t ** 1.4) * (1 + 0.28 * fbm3((math.cos(a) * 4 + t * 3, math.sin(a) * 4, seed + 3), 3))
            if i == nr:
                z = -0.05
            verts.append((math.cos(a) * rr * sx / 2, math.sin(a) * rr * sy / 2, max(z, -0.05)))
    for k in range(ns):
        faces.append((0, 1 + k, 1 + (k + 1) % ns))
    for i in range(nr - 1):
        for k in range(ns):
            a, b = 1 + i * ns + k, 1 + i * ns + (k + 1) % ns
            faces.append((a, a + ns, b + ns, b))
    mb.mesh(verts, faces, mat)
    for i in range(lumps):
        a = rng.uniform(0, math.tau)
        t = rng.uniform(0.15, 1.08)
        x, y = math.cos(a) * t * sx / 2, math.sin(a) * t * sy / 2
        z = max(0.0, h * (1 - min(t, 1) ** 1.4)) - 0.05
        s_ = lump_size * rng.uniform(0.5, 1.4)
        mb.chunk((x, y, z + s_ * 0.2), (s_, s_ * rng.uniform(0.7, 1.0), s_ * 0.7), seed=seed * 10 + i,
                 detail=2 if s_ > lump_size else 1, cuts=4, mat=mat)
    return mb.finish(smooth=30, weighted=False)


def build_pile_coal():
    root = heap("pile_coal", "coal_ore", (3.2, 2.7, 1.25), 141, 46, 0.21)
    SHOTS["pile_coal"] = [("three_quarter", (-3.5, -4.0, 2.2), (0, 0, 0.5), 35)]
    return root


def build_pile_rock():
    root = heap("pile_rock", "rock", (3.4, 3.0, 1.35), 151, 36, 0.35)
    SHOTS["pile_rock"] = [("three_quarter", (-3.6, -4.2, 2.3), (0, 0, 0.5), 35)]
    return root


def build_fence_2m():
    """One fence bay along X: a post at x = -1 and three rough rails running to x = +1 (the next bay's post)."""
    rng = random.Random(161)
    mb = MB("fence_2m", seed=161)
    mb.box((0.14, 0.14, 1.35), "wood_timber", loc=(-1.0, 0, 0), rot=(rng.uniform(-2, 2), rng.uniform(-2, 2), 8), bevel=0.012, var=0.1)
    mb.cyl(0.075, 0.02, "wood_timber", loc=(-1.0, 0, 1.35), sides=6)
    for z in (0.38, 0.76, 1.12):
        mb.beam((-1.0, -0.09, z), (1.0, -0.09, z + rng.uniform(-0.03, 0.03)), 0.06, 0.13, "wood_planks", ext=0.04, up=(0, -1, 0),
                bevel=0.008, seg=1, var=0.2)
        mb.cyl(0.012, 0.015, "steel_dark", loc=(-1.0, -0.12, z), rot=(90, 0, 0), sides=5)
    root = mb.finish(smooth=50, weighted=True)
    SHOTS["fence_2m"] = [("three_quarter", (-2.0, -3.2, 1.3), (0, 0, 0.7), 35)]
    return root


def build_fence_post():
    """The closing post at the end of a fence run (fence_2m bays carry their post at x = -1 only)."""
    rng = random.Random(165)
    mb = MB("fence_post", seed=165)
    mb.box((0.14, 0.14, 1.35), "wood_timber", loc=(0, 0, 0), rot=(rng.uniform(-2, 2), rng.uniform(-2, 2), -6), bevel=0.012, var=0.1)
    mb.cyl(0.075, 0.02, "wood_timber", loc=(0, 0, 1.35), sides=6)
    root = mb.finish(smooth=50, weighted=True)
    SHOTS["fence_post"] = []
    return root


def build_keg():
    """Wooden barrel (0.6 m, 0.86 m tall): bellied staves, three iron hoops, a plank lid."""
    mb = MB("keg", seed=191)
    h, re, rb = 0.86, 0.25, 0.3
    prof = []
    for i in range(9):
        t = i / 8
        prof.append((t * h, re + (rb - re) * math.sin(math.pi * t)))
    # revolve() spins a (x, r) profile around local X: stand it up
    mb.revolve([(0.0, 0.0)] + prof + [(h, 0.0)], "wood_timber", M=R((0, -90, 0)), seg=14, closed=False, var=0.1)
    for t in (0.1, 0.32, 0.68, 0.9):
        z = t * h
        r_ = re + (rb - re) * math.sin(math.pi * t) + 0.006
        mb.cyl(r_, 0.035, "rust", loc=(0, 0, z - 0.017), sides=14, cap=False)
    mb.cyl(re - 0.02, 0.012, "wood_planks", loc=(0, 0, h - 0.03), sides=14)
    root = mb.finish(smooth=50, weighted=False)
    SHOTS["keg"] = []
    return root


def build_lamp_post():
    """Timber pole with a cross-arm, insulators, cable, and a gooseneck enamel shade; child `bulb` (emit_warm)."""
    mb = MB("lamp_post", seed=171)
    mb.cyl(0.13, 5.2, "wood_timber", loc=(0, 0, 0), r2=0.1, sides=10, var=0.1)
    mb.box((1.1, 0.1, 0.1), "wood_timber", loc=(0, 0.0, 4.85), bevel=0.01, seg=1)
    for x in (-0.45, 0.45):
        mb.cyl(0.035, 0.12, "glass_dark", loc=(x, 0, 4.95), r2=0.02, sides=8)
    mb.tube([(0.45, 0, 5.05), (0.3, -0.05, 4.4), (0.12, -0.1, 3.6)], 0.012, "cable", sides=4)
    mb.tube([(0.0, -0.12, 3.1), (0.0, -0.12, 4.6)], 0.014, "steel_dark", sides=5)
    arm = [(0.0, -0.1, 4.25), (0.0, -0.4, 4.5), (0.0, -0.75, 4.55), (0.0, -1.02, 4.42)]
    mb.tube(arm, 0.025, "steel_dark", sides=6)
    mb.cyl(0.26, 0.12, "paint_green", loc=(0, -1.06, 4.22), r2=0.05, sides=16, cap=False)
    mb.cyl(0.05, 0.08, "paint_green", loc=(0, -1.06, 4.33), sides=8)
    root = mb.finish(smooth=50, weighted=True)
    bulb("bulb", (0, -1.06, 4.2), 0.06, root)
    SHOTS["lamp_post"] = [("three_quarter", (-4.5, -7.0, 2.6), (0, -0.4, 2.6), 35)]
    return root


def build_crates():
    """Stack of stencilled supply crates (SUTTER WORKS) + a small keg."""
    rng = random.Random(181)
    mb = MB("crates", seed=181)
    def crate(c, size, yaw):
        sx, sy, sz = size
        fs = mb.box(size, "wood_planks", loc=c, rot=(0, 0, yaw), bevel=0.02, seg=1, var=0.1)
        Mr = R((0, 0, yaw)).to_3x3()
        for nrm, ua in (((0, -1, 0), (1, 0, 0)), ((0, 1, 0), (-1, 0, 0)), ((1, 0, 0), (0, 1, 0)), ((-1, 0, 0), (0, -1, 0))):
            mb.face_label(fs, "label_crate", normal=tuple(Mr @ Vector(nrm)), u_axis=tuple(Mr @ Vector(ua)), v_axis=(0, 0, 1), nogrime=False)
    crate((0.0, 0.0, 0.0), (1.0, 0.8, 0.8), 4)
    crate((0.95, 0.15, 0.0), (0.8, 0.7, 0.7), -9)
    crate((0.25, 0.05, 0.8), (0.75, 0.65, 0.6), 14)
    mb.cyl(0.26, 0.6, "wood_timber", loc=(-0.85, -0.25, 0.0), sides=12, var=0.1)
    for z in (0.08, 0.5):
        mb.cyl(0.27, 0.04, "rust", loc=(-0.85, -0.25, z), sides=12, cap=False)
    root = mb.finish(smooth=50, weighted=True)
    SHOTS["crates"] = [("three_quarter", (-2.4, -3.0, 1.8), (0.1, 0, 0.6), 35)]
    return root


# ====================================================================== registry + run
BUILDERS = {
    "portal": build_portal,
    "shack": build_shack,
    "sign_company": build_sign_company,
    "sign_forsale": build_sign_forsale,
    "headframe_wood": build_headframe_wood,
    "ore_bin": build_ore_bin,
    "headframe_steel": build_headframe_steel,
    "hoist_house": build_hoist_house,
    "conveyor": build_conveyor,
    "mill": build_mill,
    "fuel_tank_small": build_fuel_tank_small,
    "ore_cart": build_ore_cart,
    "pile_coal": build_pile_coal,
    "pile_rock": build_pile_rock,
    "fence_2m": build_fence_2m,
    "fence_post": build_fence_post,
    "lamp_post": build_lamp_post,
    "keg": build_keg,
    "crates": build_crates,
}


def main():
    a = bk.args()
    out = a[0] if a and a[0].endswith((".glb", "claim-kit")) else None
    only = [x for x in a if x in BUILDERS]
    names = only or list(BUILDERS)
    full = not only
    bk.reset()
    roots = []
    for n in names:
        r = BUILDERS[n]()
        assert r.name == n, (r.name, n)
        roots.append(r)
        print(f"[claimkit] {n}: {kit.node_tris(r)} tris")
    kit.spread(roots, spacing=60, cols=5)
    meshes = [o for r in roots for o in kit.tree(r) if o.type == "MESH"]
    kit.bake_grime(meshes, distance=1.4, samples=64, floor=0.3, extras=EXTRAS)
    kit.to_origin(roots)
    glb = os.path.join(kit.MODELS, "claim-kit.glb") if full else os.path.join(kit.HERE, "out", "claim-kit-partial.glb")
    if out and full:
        glb = out if out.endswith(".glb") else out + ".glb"
    kit.export_glb(glb, roots)
    kit.save_blend(os.path.join(kit.HERE, "out", "claim-kit.blend" if full else "claim-kit-partial.blend"))
    if "nopreview" in a:
        return
    # ---- previews (after export: preview-only shading)
    kit.preview_materials()
    kit.preview_signs(SIGNS)
    kit.golden_rig()
    for r in roots:
        r.hide_render = True
        for o in r.children_recursive:
            o.hide_render = True
    for r in roots:
        for o in kit.tree(r):
            o.hide_render = False
        for shot, cam, tgt, lens in SHOTS.get(r.name, []):
            kit.camera(cam, tgt, lens)
            kit.render(os.path.join(kit.PREV, f"{r.name}_{shot}.png"), res=(1400, 900), samples=32)
        for o in kit.tree(r):
            o.hide_render = True


main()
