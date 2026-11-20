"""TekTonXyz statue: Ali's X pfp (anime girl, long straight bubblegum-pink hair, blue anime eyes, purple
STOP MAKING STUPID PEOPLE FAMOUS tee) as a big painted vinyl-figure bust on a gold-trimmed display base. It
stands on the monument pedestal in the town square, facing Main Street.

    node assets/statue/tex.mjs                 # face / shirt / band textures first
    bl assets/statue/build.py                  # → public/models/statue/tekton.glb (+ assets/statue/tekton.blend)
    bl assets/statue/build.py -- --previews    # also renders assets/statue/previews/*.png

Modelling: the head and the torso are signed-distance shapes (smooth unions of ellipsoids, superellipsoids and
capsules) sampled by projecting cube-sphere vertices radially onto them. The hair is one parametric "hood"
(rows from the crown down, columns around the head from the face edge to the back): an egg-shaped cap that
falls straight below its widest line, drapes over the shoulders and arms, curls down onto the skin along the
face and at the middle part, has clump grooves and pointed clump tips, and is closed with Solidify (no holes).
Face and shirt are front projections of the vector textures from tex.mjs.

Design metres are "head space" (base z -0.06..0.24); the export shifts everything up so the base stands at
z = 0, then scales by SCALE. Blender Z-up, the bust faces -Y (= +Z in three.js). Materials are all custom_*,
so the game keeps them exactly as exported (docs/CONTRACTS.md).
"""
import json
import math
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SPEC = json.load(open(os.path.join(HERE, "spec.json")))
TEX = os.path.join(HERE, "tex")
GLB = os.path.join(ROOT, "public", "models", "statue", "tekton.glb")
BLEND = os.path.join(HERE, "tekton.blend")
PREV = os.path.join(HERE, "previews")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []

SCALE = 1.15        # design metres → game metres (bust 3.0 m tall; base 1.66 m across on the 1.75 m pedestal)
Z_CUT = 0.24        # bust cut = top of the display base
Z_BASE0 = -0.06     # bottom of the base (exported at z = 0)
Y0 = 0.02           # hair axis: x = 0, y = Y0

V = lambda *a: np.array(a, dtype=np.float64)  # noqa: E731


# ------------------------------------------------------------------ SDF toolkit (numpy, p = (N, 3))

def _len(v):
    return np.sqrt(np.sum(v * v, axis=-1))


def sd_ellipsoid(p, c, r):
    q = (p - c) / r
    k0 = _len(q)
    k1 = _len((p - c) / (r * r))
    return k0 * (k0 - 1.0) / np.maximum(k1, 1e-9)


def sd_super(p, c, r, n=2.6, m=2.2):
    """superellipsoid pseudo-distance: |x|^n + |y|^n round the sides, blended with z by exponent m"""
    q = np.abs((p - c) / r)
    h = (q[:, 0] ** n + q[:, 1] ** n) ** (1.0 / n)
    g = (h ** m + q[:, 2] ** m) ** (1.0 / m)
    return (g - 1.0) * np.min(r)


def sd_capsule(p, a, b, ra, rb):
    pa, ba = p - a, b - a
    h = np.clip(np.sum(pa * ba, -1) / np.dot(ba, ba), 0.0, 1.0)
    return _len(pa - h[:, None] * ba) - (ra + (rb - ra) * h)


def smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b * (1 - h) + a * h - k * h * (1 - h)


def smax(a, b, k):
    return -smin(-a, -b, k)


def sstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


# ------------------------------------------------------------------ the shapes

def head_sdf(p):
    cr = sd_ellipsoid(p, V(0, 0.02, 1.92), V(0.57, 0.55, 0.54))
    jaw = sd_super(p, V(0, -0.08, 1.60), V(0.485, 0.42, 0.36), 2.4, 2.0)
    chin = sd_ellipsoid(p, V(0, -0.20, 1.365), V(0.225, 0.18, 0.15))
    d = smin(cr, jaw, 0.16)
    d = smin(d, chin, 0.14)
    nose = sd_ellipsoid(p, V(0, -0.47, 1.505), V(0.026, 0.03, 0.04))
    return smin(d, nose, 0.035)


NECK_A, NECK_B = V(0, -0.005, 0.80), V(0, -0.015, 1.40)


def neck_sdf(p):
    return sd_capsule(p, NECK_A, NECK_B, 0.112, 0.104)


def torso_sdf(p):
    """the torso core (chest, trapezius, shoulder caps): convex enough to project radially; arms are separate"""
    chest = sd_super(p, V(0, 0.0, 0.52), V(0.36, 0.25, 0.50), 2.6, 3.0)
    trap = sd_ellipsoid(p, V(0, 0.03, 0.93), V(0.30, 0.15, 0.115))
    sh = np.minimum(sd_ellipsoid(p, V(0.33, 0, 0.88), V(0.14, 0.15, 0.12)),
                    sd_ellipsoid(p, V(-0.33, 0, 0.88), V(0.14, 0.15, 0.12)))
    d = smin(chest, trap, 0.12)
    d = smin(d, sh, 0.10)
    return np.maximum(d, Z_CUT - p[:, 2])


# T-shirt sleeves (top centre, hem centre, radius top, radius at the hem) and the bare arms below them
SLEEVE = (V(0.42, 0.0, 0.875), V(0.487, 0.022, 0.60), 0.132, 0.138)
ARM = (V(0.468, 0.012, 0.76), V(0.505, 0.036, Z_CUT - 0.04), 0.097, 0.09)


def _mirror(v, sx):
    return v * V(sx, 1, 1)


def arm_sdf(p):
    d = np.full(len(p), 1e9)
    for sx in (1.0, -1.0):
        a, b, ra, rb = SLEEVE
        a, b = _mirror(a, sx), _mirror(b, sx)
        ax = (b - a) / np.linalg.norm(b - a)
        sl = np.maximum(sd_capsule(p, a, b, ra, rb), np.sum((p - b) * ax, -1))
        a2, b2, r2a, r2b = ARM
        arm = sd_capsule(p, _mirror(a2, sx), _mirror(b2, sx), r2a, r2b)
        d = np.minimum(d, np.minimum(sl, arm))
    return np.maximum(d, Z_CUT - 0.04 - p[:, 2])


def body_sdf(p):
    return np.minimum(np.minimum(np.minimum(torso_sdf(p), neck_sdf(p)), head_sdf(p)), arm_sdf(p))


def outermost(origins, dirs, sdf, rmax, steps=84, iters=24):
    """distance to the OUTERMOST surface crossing along each ray (rays start inside; shapes may be concave)"""
    n = len(dirs)
    ts = np.linspace(rmax, 0.0, steps)
    pts = origins[:, None, :] + dirs[:, None, :] * ts[None, :, None]
    ins = sdf(pts.reshape(-1, 3)).reshape(n, steps) < 0
    has = ins.any(1)
    first = np.argmax(ins, 1)
    lo = ts[first]
    hi = np.where(first == 0, lo, ts[np.maximum(first - 1, 0)])
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        inside = sdf(origins + dirs * mid[:, None]) < 0
        lo = np.where(inside, mid, lo)
        hi = np.where(inside, hi, mid)
    return np.where(has, 0.5 * (lo + hi), 0.0), has


def grad(sdf, p, e=1e-3):
    g = np.zeros_like(p)
    for k in range(3):
        d = np.zeros(3)
        d[k] = e
        g[:, k] = sdf(p + d) - sdf(p - d)
    return g / np.maximum(_len(g), 1e-12)[:, None]


# ------------------------------------------------------------------ mesh helpers

def link(ob):
    bpy.context.scene.collection.objects.link(ob)
    return ob


def make_mesh(name, verts, faces, mats=(), smooth=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(map(float, v)) for v in verts], [], [tuple(int(i) for i in f) for f in faces])
    me.validate(clean_customdata=False)
    for m in mats:
        me.materials.append(m)
    for p in me.polygons:
        p.use_smooth = smooth
    return link(bpy.data.objects.new(name, me))


def weld_and_orient(ob, inside_point_fn, dist=1e-5):
    """merge coincident verts, make normals consistent and pointing away from inside_point_fn(co)"""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=dist)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=1e-7)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.normal_update()
    score = 0.0
    for f in bm.faces:
        c = f.calc_center_median()
        score += f.normal.dot(c - Vector(inside_point_fn(c))) * f.calc_area()
    if score < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()


def mark_sharp(ob, angle_deg):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    lim = math.radians(angle_deg)
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > lim:
            e.smooth = False
    bm.to_mesh(ob.data)
    bm.free()


def loop_positions(me):
    co = np.zeros(len(me.vertices) * 3)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    li = np.zeros(len(me.loops), dtype=np.int64)
    me.loops.foreach_get("vertex_index", li)
    return co, li


def set_uv(me, uv):
    lay = me.uv_layers.new(name="UVMap")
    lay.data.foreach_set("uv", np.asarray(uv, dtype=np.float64).ravel())


def planar_uv(ob, win, back_mask_fn, back_v):
    """front projection of a spec window; loops flagged by back_mask_fn keep u but jump to row back_v
    (a plain strip of the texture), so nothing projects through to the back"""
    me = ob.data
    co, li = loop_positions(me)
    nrm = np.zeros(len(me.vertices) * 3)
    me.vertices.foreach_get("normal", nrm)
    nrm = nrm.reshape(-1, 3)
    p, n = co[li], nrm[li]
    u = 0.5 + (p[:, 0] - win["cx"]) / win["size"]
    v = (p[:, 2] - win["z0"]) / win["size"]
    back = back_mask_fn(p, n)
    v = np.where(back, back_v, v)
    set_uv(me, np.stack([u, v], 1))


def const_uv(ob, uv):
    me = ob.data
    set_uv(me, np.tile(np.array(uv, dtype=np.float64), (len(me.loops), 1)))


def cube_sphere(n):
    """unit directions + quads of an equal-angle cube sphere (verts welded on the cube edges)"""
    s = np.tan(np.linspace(-1, 1, n + 1) * math.pi / 4)
    verts, index, quads = [], {}, []

    def vid(p):
        p = p / np.linalg.norm(p)
        key = tuple(np.round(p, 6))
        if key not in index:
            index[key] = len(verts)
            verts.append(p)
        return index[key]

    for axis in range(3):
        for sg in (-1.0, 1.0):
            a1, a2 = [k for k in range(3) if k != axis]
            ids = np.zeros((n + 1, n + 1), dtype=np.int64)
            for i in range(n + 1):
                for j in range(n + 1):
                    p = np.zeros(3)
                    p[axis] = sg
                    p[a1] = s[i]
                    p[a2] = s[j]
                    ids[i, j] = vid(p)
            for i in range(n):
                for j in range(n):
                    quads.append((ids[i, j], ids[i + 1, j], ids[i + 1, j + 1], ids[i, j + 1]))
    return np.array(verts), quads


def radial_mesh(name, sdf, centre, n, rmax, mats):
    dirs, quads = cube_sphere(n)
    t, has = outermost(np.tile(centre, (len(dirs), 1)), dirs, sdf, rmax)
    if not has.all():
        print(f"[statue] WARNING {name}: {int((~has).sum())} rays missed")
    ob = make_mesh(name, centre + dirs * t[:, None], quads, mats)
    weld_and_orient(ob, lambda c: centre)
    return ob


# ------------------------------------------------------------------ materials

def hex_lin(h):
    h = h.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return (*out, 1.0)


def material(name, color="#ffffff", rough=0.5, metal=0.0, image=None, extension="REPEAT", coat=0.0):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    nt = m.node_tree
    p = nt.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = hex_lin(color)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    if coat > 0:
        p.inputs["Coat Weight"].default_value = coat
        p.inputs["Coat Roughness"].default_value = 0.3
    if image:
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = bpy.data.images.load(image, check_existing=True)
        tex.extension = extension
        tex.interpolation = "Linear"
        nt.links.new(tex.outputs["Color"], p.inputs["Base Color"])
    m.diffuse_color = hex_lin(color)
    return m


def use_vertex_color(m, on):
    """preview only: multiply the hair's grime/AO vertex colour into the base colour (export keeps it unlinked:
    COLOR_0 is exported by name and three.js multiplies it in on its own)"""
    nt = m.node_tree
    p = nt.nodes["Principled BSDF"]
    tex = next((n for n in nt.nodes if n.type == "TEX_IMAGE"), None)
    for l in list(p.inputs["Base Color"].links):
        nt.links.remove(l)
    if not on:
        if tex:
            nt.links.new(tex.outputs["Color"], p.inputs["Base Color"])
        return
    ca = nt.nodes.new("ShaderNodeVertexColor")
    ca.layer_name = "Color"
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    mix.inputs["Factor"].default_value = 1.0
    if tex:
        nt.links.new(tex.outputs["Color"], mix.inputs["A"])
    else:
        mix.inputs["A"].default_value = p.inputs["Base Color"].default_value
    nt.links.new(ca.outputs["Color"], mix.inputs["B"])
    nt.links.new(mix.outputs["Result"], p.inputs["Base Color"])


# ------------------------------------------------------------------ hair

A_EGG, B_FRONT, B_BACK, C_EGG, Z_C = 0.73, 0.615, 0.71, 0.615, 1.93
Z_TOP = Z_C + C_EGG
GAP = 0.05          # hair clearance over shoulders / arms / back
T_BACK = 0.24       # how far the back hair swings in toward the back as it falls
THICK = 0.05        # solidify thickness of the hair shell
W_PART, W_EDGE, D_FREE = 0.05, 0.07, 0.07
ALPHA_B = 125.0     # the part runs from the forehead over the crown to here (sagittal angle, degrees)
# azimuth of the face edge (0 = front centre) by height: shallow forehead diagonal from the part, straight down
# the cheeks, then swept back behind the shoulders below the jaw (the pfp's hair falls behind them)
PHI_Z = np.array([1.00, 1.07, 1.17, 1.27, 1.36, 1.45, 1.60, 1.80, 1.88, 1.93, 1.98, 2.03, 2.07])
PHI_D = np.array([96, 95, 85, 68, 57, 55, 55, 55, 52, 44, 30, 14, 0], dtype=np.float64)


def phi_edge(z):
    z = np.asarray(z, dtype=np.float64)
    acc = sum(np.interp(z + dz, PHI_Z, PHI_D) for dz in (-0.03, -0.015, 0.0, 0.015, 0.03))
    return np.radians(acc / 5.0)


def r_egg(phi):
    b = np.where(np.cos(phi) > 0, B_FRONT, B_BACK)
    return 1.0 / np.sqrt((np.sin(phi) / A_EGG) ** 2 + (np.cos(phi) / b) ** 2)


def layout(ncl, seed, per=4, dense_front=7, dense_back=6):
    """clump columns for one half: u in 0..1 (face edge → back centre), clump-local s in 0..1, clump id"""
    rng = np.random.default_rng(seed)
    w = 0.7 + 0.6 * rng.random(ncl)
    w[0] *= 0.75
    w /= w.sum()
    e = np.concatenate([[0.0], np.cumsum(w)])
    u, s, c = [], [], []
    for k in range(ncl):
        n = dense_front if k == 0 else dense_back if k == ncl - 1 else per
        for j in range(n):
            t = j / n
            if k == 0:
                t = t ** 1.6
            u.append(e[k] + t * w[k])
            s.append(t)
            c.append(k)
    u.append(1.0)
    s.append(1.0)
    c.append(ncl - 1)
    return np.array(u), np.array(s), np.array(c)


def build_hair(mat):
    NCL = 9
    ur, sr, cr = layout(NCL, seed=7, per=5, dense_back=5)
    ul, sl, cl = layout(NCL, seed=23, per=5, dense_back=5)
    U = np.concatenate([ur, ul[::-1][1:]])
    S = np.concatenate([sr, sl[::-1][1:]])
    CID = np.concatenate([cr, cl[::-1][1:] + NCL])
    SIDE = np.concatenate([np.ones(len(ur)), -np.ones(len(ul) - 1)])
    ncol = len(U)
    j_edge_r, j_edge_l = 0, ncol - 1

    rng = np.random.default_rng(5)
    extra = rng.normal(0.0, 0.055, 2 * NCL)
    groove = (1 - np.sin(np.pi * S)) ** 1.4
    z_tip = 0.33 + 0.24 * (1 - U) ** 1.4 + 0.11 * (1 - np.sin(np.pi * S)) ** 1.5 - extra[CID]
    z_tip = np.maximum(z_tip, Z_CUT + 0.05)

    ND, NCU = 16, 30
    th = np.linspace(0, np.pi / 2, ND + 1)
    tau = (np.arange(1, NCU + 1) / NCU) ** 0.92
    nrow = ND + 1 + NCU
    Z = np.zeros((nrow, ncol))
    SIN_TH = np.ones((nrow, ncol))
    Z[:ND + 1] = Z_C + C_EGG * np.cos(th)[:, None]
    SIN_TH[:ND + 1] = np.sin(th)[:, None]
    Z[ND + 1:] = Z_C - tau[:, None] * (Z_C - z_tip[None, :])
    dome = np.zeros((nrow, ncol), bool)
    dome[:ND + 1] = True
    cur = ~dome

    PHIE = phi_edge(Z)
    PHI = PHIE + U[None, :] * (np.pi - PHIE)
    side = np.broadcast_to(SIDE[None, :], Z.shape)
    RE = r_egg(PHI)
    taper = T_BACK * ((1 - np.cos(PHI)) / 2) ** 4   # only the back swings in; the sides fall straight
    R = np.where(dome, RE * SIN_TH, RE - taper * sstep(Z_C, 0.35, Z))

    # drape: keep the falling hair GAP clear of shoulders, arms and back (outermost body surface per ray)
    dirs = np.stack([side * np.sin(PHI), -np.cos(PHI), np.zeros_like(PHI)], -1)
    orig = np.stack([np.zeros_like(Z), np.full_like(Z, Y0), Z], -1)
    RB = np.zeros_like(Z)
    tb, _ = outermost(orig[cur], dirs[cur], body_sdf, 1.4)
    RB[cur] = tb
    pad = np.pad(RB, ((0, 0), (2, 2)), mode="edge")
    RB = np.max(np.stack([pad[:, k:k + ncol] for k in range(5)]), 0)

    def blur(a, axis, sig):
        k = np.exp(-0.5 * (np.arange(-3, 4) / sig) ** 2)
        k /= k.sum()
        pw = [(3, 3) if ax == axis else (0, 0) for ax in range(2)]
        ap = np.pad(a, pw, mode="edge")
        return sum(k[i] * np.take(ap, range(i, i + a.shape[axis]), axis=axis) for i in range(7))

    RB = blur(blur(RB, 1, 1.6), 0, 1.2)
    R = np.where(cur, smax(R, RB + GAP, 0.05), R)

    # profiles push along the outward radius: from the cap centre on the dome, horizontally on the curtain
    P0 = np.stack([side * R * np.sin(PHI), Y0 - R * np.cos(PHI), Z], -1)
    O = np.stack([np.zeros_like(Z), np.full_like(Z, Y0), np.where(dome, Z_C, Z)], -1)
    DO = P0 - O
    RHO = _len(DO)
    NOUT = DO / np.maximum(RHO, 1e-9)[..., None]

    # middle part: a crease along the sagittal plane over the crown, deepening to the skin at the hairline
    X0 = P0[..., 0]
    Yp = P0[..., 1]
    alpha = np.degrees(np.arctan2(Z - Z_C, -(Yp - Y0)))
    z_a = 2.07
    cap_a = B_FRONT * math.sqrt(1 - ((z_a - Z_C) / C_EGG) ** 2)
    a_front = math.degrees(math.atan2(z_a - Z_C, cap_a))
    pa = V(0, Y0 - cap_a, z_a)
    oc = V(0, Y0, Z_C)
    na = (pa - oc) / np.linalg.norm(pa - oc)
    skin_a, _ = outermost(oc[None], na[None], head_sdf, 1.2)
    d_a = max(0.05, float(np.linalg.norm(pa - oc)) - float(skin_a[0]) + 0.004)
    w_alpha = sstep(a_front - 3, a_front + 3, alpha) * (1 - sstep(ALPHA_B - 22, ALPHA_B, alpha))
    d_part = 0.042 + (d_a - 0.042) * (1 - sstep(a_front, a_front + 22, alpha))
    part = d_part * np.clip(1 - np.abs(X0) / W_PART, 0, 1) ** 2.2 * w_alpha

    # face edge: the hair curls down onto the skin along the face (rounded lock edge), free edge below the jaw
    edge_d = np.zeros_like(Z)
    for je, sg in ((j_edge_r, 1.0), (j_edge_l, -1.0)):
        rs, _ = outermost(O[:, je], NOUT[:, je], head_sdf, 1.2)
        d_skin = np.maximum(RHO[:, je] - rs + 0.004, 0.0)
        half = SIDE == sg
        edge_d[:, half] = d_skin[:, None]
    jaw = sstep(1.20, 1.36, Z)
    edge_d = edge_d * jaw + D_FREE * (1 - jaw)
    q = np.clip((PHI - PHIE) * R / W_EDGE, 0, 1)
    prof = 1 - np.sqrt(np.clip(1 - (1 - q) ** 2, 0, 1))
    mface = sstep(np.radians(0.3), np.radians(4.0), PHIE)
    RHO = RHO - (1 - mface) * part - mface * edge_d * prof
    P = O + NOUT * RHO[..., None]

    # clump grooves along the strands (none on the smooth crown), deeper toward the tips so the clumps separate;
    # pushed along the same outward radius as the profiles (grid normals go bad on the sliver quads at the tips)
    N = NOUT
    A0, A_TIP = 0.028, 0.034
    amp = A0 * sstep(Z_TOP - 0.12, Z_TOP - 0.45, Z) + A_TIP * sstep(z_tip[None, :] + 0.28, z_tip[None, :], Z)
    wedge = np.where(PHIE > np.radians(1), sstep(0.0, 0.08, U)[None, :], 1.0)
    disp = amp * groove[None, :] * wedge
    P = P - N * disp[..., None]

    # grime: darker in the grooves, the part and toward the tips
    ao = 1 - 0.32 * groove[None, :] * np.clip(amp / A0, 0, 1.4) * wedge
    ao *= 1 - 0.35 * (part / 0.05).clip(0, 1) * (1 - mface)
    ao *= 0.86 + 0.14 * sstep(z_tip[None, :], z_tip[None, :] + 0.6, Z)
    thick_w = 0.25 + 0.75 * sstep(z_tip[None, :], z_tip[None, :] + 0.2, Z)

    # sanity: the outer hair must clear the skull / torso except where it deliberately touches the skin
    hp = P.reshape(-1, 3)
    clear = head_sdf(hp)
    on_skin = ((mface * prof) + (1 - mface) * (part / 0.04).clip(0, 1)).reshape(-1) > 0.15
    bad = (clear < 0.004) & ~on_skin
    tclear = torso_sdf(hp)
    print(f"[statue] hair grid {nrow}x{ncol}: {int(bad.sum())} verts dip into the skull, "
          f"min torso clearance {tclear.min():.3f} m")

    verts = P.reshape(-1, 3)
    faces = []
    for i in range(nrow - 1):
        for j in range(ncol - 1):
            a = i * ncol + j
            faces.append((a, a + ncol, a + ncol + 1, a + 1))
    ob = make_mesh("tekton_hair", verts, faces, [mat])
    me = ob.data
    # strand texture: u = column (lines follow the clumps, converge at the crown; 0 ≡ 6 across the part), v = row
    _, li = loop_positions(me)
    ii, jj = np.divmod(li, ncol)
    set_uv(me, np.stack([jj / (ncol - 1) * 6.0, ii / (nrow - 1) * 2.0], 1))
    col = me.color_attributes.new("Color", "FLOAT_COLOR", "POINT")
    aof = ao.reshape(-1)
    col.data.foreach_set("color", np.stack([aof, aof, aof, np.ones_like(aof)], 1).ravel())
    vg = ob.vertex_groups.new(name="thick")
    tw = thick_w.reshape(-1)
    for i in range(len(tw)):
        vg.add([i], float(tw[i]), "REPLACE")
    weld_and_orient(ob, lambda c: (0.0, Y0, min(max(c.z, 0.3), Z_C - 0.2)))

    sol = ob.modifiers.new("Solidify", "SOLIDIFY")
    sol.thickness = THICK
    sol.offset = -1.0
    sol.use_rim = True
    sol.use_even_offset = True
    sol.use_quality_normals = True
    sol.vertex_group = "thick"
    sol.thickness_vertex_group = 0.25
    apply_mods(ob)
    # the inner shell (faces turned toward the head) a little darker
    me = ob.data
    nrm = np.zeros(len(me.vertices) * 3)
    me.vertices.foreach_get("normal", nrm)
    nrm = nrm.reshape(-1, 3)
    co, _ = loop_positions(me)
    axis = np.stack([np.zeros(len(co)), np.full(len(co), Y0), np.clip(co[:, 2], 0.3, Z_C - 0.2)], 1)
    inner = np.sum(nrm * (co - axis), 1) < 0
    c = np.zeros(len(me.vertices) * 4)
    me.color_attributes["Color"].data.foreach_get("color", c)
    c = c.reshape(-1, 4)
    c[inner, :3] *= 0.62
    me.color_attributes["Color"].data.foreach_set("color", c.ravel())
    for p in me.polygons:
        p.use_smooth = True
    mark_sharp(ob, 62)
    ob.vertex_groups.clear()
    return ob


def apply_mods(ob):
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    for m in list(ob.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)


# ------------------------------------------------------------------ neck, neckline, torso

def tube(name, pts, radius, sides, mats, closed=True, frame_normals=None, offset=None):
    """sweep a circle along a polyline; frame_normals gives the 'up' per point (default: z)"""
    pts = np.asarray(pts, dtype=np.float64)
    n = len(pts)
    verts, faces = [], []
    for i in range(n):
        a = pts[(i + 1) % n] if closed or i < n - 1 else pts[i]
        b = pts[i - 1] if closed or i > 0 else pts[i]
        t = a - b
        t /= np.linalg.norm(t)
        up = frame_normals[i] if frame_normals is not None else np.array([0, 0, 1.0])
        nn = up - t * np.dot(up, t)
        nn /= np.linalg.norm(nn)
        bb = np.cross(t, nn)
        c = pts[i] + (nn * offset if offset else 0)
        for k in range(sides):
            ang = 2 * math.pi * k / sides
            verts.append(c + radius * (math.cos(ang) * nn + math.sin(ang) * bb))
    rings = n if closed else n - 1
    for i in range(rings):
        i2 = (i + 1) % n
        for k in range(sides):
            k2 = (k + 1) % sides
            faces.append((i * sides + k, i * sides + k2, i2 * sides + k2, i2 * sides + k))
    return make_mesh(name, verts, faces, mats)


def build_neck(mat):
    sides, rings = 24, 12
    verts, faces = [], []
    for i in range(rings + 1):
        t = i / rings
        c = NECK_A + (NECK_B - NECK_A) * t
        r = 0.112 + (0.104 - 0.112) * t
        for k in range(sides):
            a = 2 * math.pi * k / sides
            verts.append(c + np.array([r * math.cos(a), r * math.sin(a), 0.0]))
    for i in range(rings):
        for k in range(sides):
            k2 = (k + 1) % sides
            faces.append((i * sides + k, i * sides + k2, (i + 1) * sides + k2, (i + 1) * sides + k))
    b0, b1 = len(verts), len(verts) + 1
    verts += [NECK_A.copy(), NECK_B.copy()]
    for k in range(sides):
        k2 = (k + 1) % sides
        faces.append((b0, k2, k))
        faces.append((b1, rings * sides + k, rings * sides + k2))
    ob = make_mesh("neck", verts, faces, [mat])
    weld_and_orient(ob, lambda c: (0.0, -0.01, c.z))
    return ob


def neckline_ring(psi):
    """the crew neckline round the neck: a scoop, lowest at the front"""
    c = np.cos(psi)
    r = np.where(c > 0, 0.15 + 0.022 * c, 0.15 + 0.025 * c)
    return np.stack([r * np.sin(psi), -0.01 - r * np.cos(psi)], -1)


def torso_top(xy):
    o = np.stack([xy[:, 0], xy[:, 1], np.full(len(xy), 0.6)], -1)
    d = np.tile(V(0, 0, 1), (len(xy), 1))
    t, _ = outermost(o, d, torso_sdf, 0.8)
    return 0.6 + t


def build_neckline(skin, shirt):
    n = 72
    psi = np.linspace(0, 2 * math.pi, n, endpoint=False)
    ring = neckline_ring(psi)
    zc = torso_top(ring)
    pts = np.stack([ring[:, 0], ring[:, 1], zc], -1)
    nrm = grad(torso_sdf, pts)
    collar = tube("collar", pts, 0.018, 10, [shirt], closed=True, frame_normals=nrm, offset=0.009)
    # bare skin inside the neckline (from under the neck out to the collar)
    rings = 7
    verts, faces = [], []
    inner = np.stack([0.085 * np.sin(psi), -0.01 - 0.085 * np.cos(psi)], -1)
    for i in range(rings + 1):
        t = i / rings
        xy = inner + (ring - inner) * t
        z = torso_top(xy) + 0.003
        for k in range(n):
            verts.append((xy[k, 0], xy[k, 1], z[k]))
    for i in range(rings):
        for k in range(n):
            k2 = (k + 1) % n
            faces.append((i * n + k, i * n + k2, (i + 1) * n + k2, (i + 1) * n + k))
    patch = make_mesh("neckline_skin", verts, faces, [skin])
    weld_and_orient(patch, lambda c: (0.0, -0.01, 0.6))
    centres = pts + nrm * 0.009
    weld_and_orient(collar, lambda c: tuple(centres[int(np.argmin(np.sum((centres - np.array(c)) ** 2, 1)))]))
    return collar, patch


def axis_lathe(name, a, b, prof, sides, mats):
    """revolve (r, t) profile points round the a→b axis (t = metres from a along it)"""
    ax = (b - a) / np.linalg.norm(b - a)
    ref = V(0, -1, 0)
    e1 = ref - ax * np.dot(ref, ax)
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(ax, e1)
    verts, faces = [], []
    npf = len(prof)
    for k in range(sides):
        ang = 2 * math.pi * k / sides
        d = math.cos(ang) * e1 + math.sin(ang) * e2
        for r, t in prof:
            verts.append(a + ax * t + d * r)
    for k in range(sides):
        k2 = (k + 1) % sides
        for i in range(npf - 1):
            faces.append((k * npf + i, k * npf + i + 1, k2 * npf + i + 1, k2 * npf + i))
    ob = make_mesh(name, verts, faces, mats)

    def on_axis(c):
        c = np.array(c)
        t = np.clip(np.dot(c - a, ax), -1, np.linalg.norm(b - a) + 1)
        return tuple(a + ax * t)

    weld_and_orient(ob, on_axis)
    return ob


def build_arms(skin, shirt):
    """short T-shirt sleeves (purple, with a rolled hem) and the bare upper arms below them"""
    sleeves, arms = [], []
    for sx in (1.0, -1.0):
        a, b, ra, rb = SLEEVE
        a, b = _mirror(a, sx), _mirror(b, sx)
        L = float(np.linalg.norm(b - a))
        prof = [(0.0, -ra)]
        for k in range(1, 7):                       # rounded shoulder dome
            t = k / 7 * math.pi / 2
            prof.append((ra * math.sin(t), -ra * math.cos(t)))
        for k in range(1, 7):                       # sleeve body, flaring slightly to the hem
            f = k / 7
            prof.append((ra + (rb - ra) * f, L * 0.9 * f))
        prof += [(rb + 0.006, L - 0.022), (rb + 0.011, L - 0.01), (rb + 0.006, L), (rb - 0.02, L + 0.002),
                 (0.0, L + 0.002)]
        sleeves.append(axis_lathe("sleeve", a, b, prof, 28, [shirt]))
        a2, b2, r2a, r2b = ARM
        a2, b2 = _mirror(a2, sx), _mirror(b2, sx)
        L2 = float(np.linalg.norm(b2 - a2))
        prof2 = [(0.0, -r2a), (r2a * 0.7, -r2a * 0.7), (r2a, 0.0)]
        for k in range(1, 6):
            f = k / 6
            prof2.append((r2a + (r2b - r2a) * f, L2 * f))
        prof2.append((0.0, L2))
        arms.append(axis_lathe("arm", a2, b2, prof2, 22, [skin]))
    return sleeves, arms


# ------------------------------------------------------------------ base + nameplate

def lathe(name, prof, sides, mats, mat_of_seg, uv_fn=None):
    """revolve (r, z) profile points round Z; mat_of_seg[i] = material slot of segment i..i+1"""
    verts, faces, fmat = [], [], []
    np_ = len(prof)
    for k in range(sides):
        a = 2 * math.pi * k / sides
        for r, z in prof:
            verts.append((r * math.cos(a), r * math.sin(a), z))
    for k in range(sides):
        k2 = (k + 1) % sides
        for i in range(np_ - 1):
            if prof[i][0] < 1e-6 and prof[i + 1][0] < 1e-6:
                continue
            faces.append((k * np_ + i, k2 * np_ + i, k2 * np_ + i + 1, k * np_ + i + 1))
            fmat.append(mat_of_seg[i])
    ob = make_mesh(name, verts, faces, mats)
    for p, mi in zip(ob.data.polygons, fmat):
        p.material_index = mi
    return ob


R_DRUM = 0.66        # printed drum radius (the gold rings stand ~5 cm proud)
PLATE = dict(r=R_DRUM + 0.011, half_deg=31.0, z0=0.022, z1=0.168)


def build_base(m_black, m_gold, m_band):
    zb, rd = Z_BASE0, R_DRUM
    prof = [
        (0.0, zb), (rd + 0.045, zb), (rd + 0.057, zb + 0.008), (rd + 0.06, zb + 0.022), (rd + 0.055, zb + 0.036),
        (rd + 0.035, zb + 0.044), (rd + 0.003, zb + 0.048),                     # bottom gold ring
        (rd, zb + 0.052), (rd, Z_CUT - 0.058),                                 # printed band (error popups)
        (rd + 0.015, Z_CUT - 0.052), (rd + 0.037, Z_CUT - 0.046), (rd + 0.047, Z_CUT - 0.032),
        (rd + 0.043, Z_CUT - 0.018), (rd + 0.025, Z_CUT - 0.010),             # top gold ring
        (rd + 0.017, Z_CUT - 0.006), (rd + 0.007, Z_CUT), (0.0, Z_CUT),       # black top
    ]
    seg = [1, 1, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 0, 0, 0]
    ob = lathe("tekton_base", prof, 96, [m_black, m_gold, m_band], seg)
    weld_and_orient(ob, lambda c: (0.0, 0.0, 0.09))
    me = ob.data
    # UVs: band wraps round the drum (SPEC band repeats), everything else on a plain texel
    co, li = loop_positions(me)
    pidx = np.zeros(len(me.loops), dtype=np.int64)
    for p in me.polygons:
        for l in p.loop_indices:
            pidx[l] = p.index
    mi = np.array([p.material_index for p in me.polygons])[pidx]
    pc = co[li]
    # u = angle round the drum (0 at the back seam), continuous inside each face
    pang = {}
    for p in me.polygons:
        a = np.arctan2([me.vertices[v].co.x for v in p.vertices], [-me.vertices[v].co.y for v in p.vertices])
        if a.max() - a.min() > math.pi:
            a = np.where(a < 0, a + 2 * math.pi, a)
        for l, aa in zip(p.loop_indices, a):
            pang[l] = aa
    ang = np.array([pang[i] for i in range(len(me.loops))])
    rep = SPEC["band"]["repeats"]
    u = (ang / (2 * math.pi) + 0.5) * rep
    z0b, z1b = zb + 0.052, Z_CUT - 0.058
    v = (pc[:, 2] - z0b) / (z1b - z0b)
    u = np.where(mi == 2, u, 0.5)
    v = np.where(mi == 2, v, 0.5)
    set_uv(me, np.stack([u, v], 1))
    for p in me.polygons:
        p.use_smooth = True
    mark_sharp(ob, 34)
    # gold frame behind the nameplate: a curved slab proud of the drum
    r_in, r_out = R_DRUM - 0.007, R_DRUM + 0.008
    a0, a1 = math.radians(PLATE["half_deg"] + 1.6), math.radians(-PLATE["half_deg"] - 1.6)
    z0, z1 = PLATE["z0"] - 0.012, PLATE["z1"] + 0.012
    nseg = 28
    fv, ff = [], []
    for k in range(nseg + 1):
        a = a0 + (a1 - a0) * k / nseg
        for r in (r_in, r_out):
            for z in (z0, z1):
                fv.append((r * math.sin(a), -r * math.cos(a), z))
    for k in range(nseg):
        b0, b1 = k * 4, (k + 1) * 4
        ff += [(b0 + 2, b1 + 2, b1 + 3, b0 + 3),   # front (r_out)
               (b0 + 1, b1 + 1, b1 + 3, b0 + 3),   # top
               (b0 + 0, b1 + 0, b1 + 2, b0 + 2)]   # bottom
    ff += [(0, 1, 3, 2), (nseg * 4, nseg * 4 + 2, nseg * 4 + 3, nseg * 4 + 1)]
    frame = make_mesh("plate_frame", fv, ff, [m_gold])
    weld_and_orient(frame, lambda c: (0.0, 0.0, (z0 + z1) / 2))
    const_uv(frame, (0.5, 0.5))
    mark_sharp(frame, 40)
    return ob, frame


def build_nameplate(mat):
    r, h = PLATE["r"], math.radians(PLATE["half_deg"])
    nseg = 32
    verts, faces, uv = [], [], []
    for k in range(nseg + 1):
        t = k / nseg
        a = -h + 2 * h * t        # -h = viewer's left (x < 0)
        for z in (PLATE["z0"], PLATE["z1"]):
            verts.append((r * math.sin(a), -r * math.cos(a), z))
    for k in range(nseg):
        faces.append((k * 2, k * 2 + 2, k * 2 + 3, k * 2 + 1))
    ob = make_mesh("nameplate_face", verts, faces, [mat])
    weld_and_orient(ob, lambda c: (0.0, 0.0, c.z))
    me = ob.data
    lv = []
    for p in me.polygons:
        for vi in p.vertices:
            k, top = divmod(vi, 2)
            lv.append((k / nseg, float(top)))
    set_uv(me, lv)
    return ob


# ------------------------------------------------------------------ assemble + export

def join(objs, name):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = name
    ob.data.name = name
    return ob


def tri_count(objs):
    n = 0
    for o in objs:
        if o.type == "MESH":
            n += sum(len(p.vertices) - 2 for p in o.data.polygons)
    return n


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    C = SPEC["colors"]
    m_hair = material("custom_tekton_hair", "#ffffff", rough=0.42, image=os.path.join(TEX, "hair.jpg"))
    m_skin = material("custom_tekton_skin", C["skin"], rough=0.5, image=os.path.join(TEX, "face.png"), extension="EXTEND")
    m_shirt = material("custom_tekton_shirt", C["shirt"], rough=0.62, image=os.path.join(TEX, "shirt.png"), extension="EXTEND")
    m_black = material("custom_tekton_base", "#151417", rough=0.26)
    m_gold = material("custom_tekton_gold", "#e3b44a", rough=0.24, metal=1.0)
    m_band = material("custom_tekton_band", "#d9d9d9", rough=0.42, image=os.path.join(TEX, "band.png"))
    m_plate = material("custom_tekton_nameplate", "#2a1f15", rough=0.45)

    head = radial_mesh("head", head_sdf, V(0, -0.02, 1.72), 20, 1.2, [m_skin])
    planar_uv(head, SPEC["face"], lambda p, n: p[:, 1] > 0.0, 0.985)
    neck = build_neck(m_skin)
    const_uv(neck, (0.97, 0.985))
    torso = radial_mesh("torso", torso_sdf, V(0, 0, 0.6), 20, 1.3, [m_shirt])
    planar_uv(torso, SPEC["shirt"], lambda p, n: n[:, 1] > 0.15, 0.97)
    collar, patch = build_neckline(m_skin, m_shirt)
    const_uv(collar, (0.97, 0.97))
    const_uv(patch, (0.97, 0.985))
    sleeves, arms = build_arms(m_skin, m_shirt)
    for o in sleeves:
        const_uv(o, (0.97, 0.97))
        mark_sharp(o, 50)
    for o in arms:
        const_uv(o, (0.97, 0.985))
        mark_sharp(o, 50)
    hair = build_hair(m_hair)
    base, frame = build_base(m_black, m_gold, m_band)
    plate = build_nameplate(m_plate)

    skin = join([head, neck, patch] + arms, "tekton_head")
    body = join([torso, collar] + sleeves, "tekton_body")
    base = join([base, frame], "tekton_base")
    meshes = [hair, skin, body, base, plate]

    M = Matrix.Scale(SCALE, 4) @ Matrix.Translation((0, 0, -Z_BASE0))
    for o in meshes:
        o.data.transform(M)
        o.data.update()
    root = link(bpy.data.objects.new("tekton_statue", None))
    for o in meshes:
        o.parent = root
    for nm, p in (("head_anchor", (0, -0.66, 1.62)), ("plate_anchor", (0, -(R_DRUM + 0.12), 0.095)), ("crown", (0, Y0, Z_TOP))):
        e = link(bpy.data.objects.new(nm, None))
        e.location = M @ Vector(p)
        e.parent = root
    tris = tri_count(meshes)
    for o in meshes:
        print(f"[statue]   {o.name:16s} {tri_count([o]):6d} tris")
    print(f"[statue] total {tris} tris, height {(Z_TOP - Z_BASE0) * SCALE:.2f} m")
    return root, meshes, dict(hair=m_hair, plate=m_plate)


def export(root):
    objs = [root] + list(root.children_recursive)
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = root
    os.makedirs(os.path.dirname(GLB), exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=GLB, export_format="GLB", use_selection=True, export_apply=True, export_yup=True,
        export_animations=False, export_extras=False,
        export_vertex_color="NAME", export_vertex_color_name="Color", export_all_vertex_colors=False,
        export_active_vertex_color_when_no_material=False, export_meshopt_compression_enable=True,
        export_image_format="AUTO", export_tangents=False, export_cameras=False, export_lights=False)
    print(f"[statue] exported {GLB} ({os.path.getsize(GLB) / 1024:.0f} KB)")


# ------------------------------------------------------------------ previews

def preview_stage(golden=False):
    sc = bpy.context.scene
    w = bpy.data.worlds.new("pv")
    try:
        w.use_nodes = True
    except Exception:
        pass
    sc.world = w
    nt = w.node_tree
    bg = nt.nodes["Background"]
    if golden:
        sky = nt.nodes.new("ShaderNodeTexSky")
        try:
            sky.sky_type = "SINGLE_SCATTERING"
        except Exception:
            pass
        try:
            sky.sun_elevation = math.radians(14)
            sky.sun_rotation = math.radians(-90)
            sky.sun_disc = False
        except Exception:
            pass
        nt.links.new(sky.outputs["Color"], bg.inputs["Color"])
        bg.inputs["Strength"].default_value = 0.35
    else:
        bg.inputs["Color"].default_value = (0.42, 0.45, 0.5, 1)
        bg.inputs["Strength"].default_value = 0.55
    for o in [o for o in sc.objects if o.name.startswith("_pv")]:
        bpy.data.objects.remove(o, do_unlink=True)

    def light(name, kind, energy, rot, color=(1, 1, 1), size=None, loc=(0, 0, 0)):
        ld = bpy.data.lights.new(name, kind)
        ld.energy = energy
        ld.color = color
        if size:
            ld.size = size
        ob = link(bpy.data.objects.new(name, ld))
        ob.rotation_euler = [math.radians(a) for a in rot]
        ob.location = loc
        return ob

    if golden:
        light("_pv_sun", "SUN", 5.5, (76, 0, 0), color=(1.0, 0.8, 0.62))   # low sun from the front (-Y)
    else:
        light("_pv_key", "SUN", 3.6, (52, 0, -32), color=(1.0, 0.95, 0.88))
        light("_pv_fill", "SUN", 0.9, (70, 0, 120), color=(0.85, 0.9, 1.0))
        light("_pv_rim", "SUN", 2.2, (-60, 0, 160))
    gm = bpy.data.meshes.new("_pv_ground")
    gm.from_pydata([(-30, -30, 0), (30, -30, 0), (30, 30, 0), (-30, 30, 0)], [], [(0, 1, 2, 3)])
    g = link(bpy.data.objects.new("_pv_ground", gm))
    gm.materials.append(material("_pv_ground_m", "#6d6a64", rough=0.9))
    sc.render.engine = "BLENDER_EEVEE"
    sc.eevee.taa_render_samples = 48
    sc.view_settings.view_transform = "AgX"
    sc.render.film_transparent = False
    return g


def shoot(path, az, el, dist, target=(0, 0, 1.45), lens=50, res=(1000, 1000)):
    sc = bpy.context.scene
    cd = bpy.data.cameras.get("_pv_cam") or bpy.data.cameras.new("_pv_cam")
    cd.lens = lens
    cam = bpy.data.objects.get("_pv_cam") or link(bpy.data.objects.new("_pv_cam", cd))
    t = (Vector(target) + Vector((0, 0, -Z_BASE0))) * SCALE
    a, e = math.radians(az), math.radians(el)
    cam.location = t + Vector((dist * math.cos(e) * math.sin(a), -dist * math.cos(e) * math.cos(a), dist * math.sin(e)))
    cam.rotation_euler = (t - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.image_settings.file_format = "PNG"
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print(f"[statue] preview {path}")


def previews(mats):
    os.makedirs(PREV, exist_ok=True)
    use_vertex_color(mats["hair"], True)
    pm = mats["plate"]
    tex = pm.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(os.path.join(TEX, "nameplate_preview.png"))
    pm.node_tree.links.new(tex.outputs["Color"], pm.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
    preview_stage(golden=False)
    shots = [("front", 0, 6, 7.2), ("three_quarter", 35, 8, 7.2), ("side", 90, 4, 7.2), ("back", 180, 8, 7.2),
             ("back_three_quarter", 140, 18, 7.2), ("low_front", 18, -12, 7.0)]
    for nm, az, el, d in shots:
        if "only" in ARGS and nm not in ARGS:
            continue
        shoot(os.path.join(PREV, f"bl_{nm}.png"), az, el, d)
    shoot(os.path.join(PREV, "bl_face.png"), 0, 2, 3.0, target=(0, -0.3, 1.66), lens=60)
    shoot(os.path.join(PREV, "bl_shirt.png"), 12, 8, 3.2, target=(0, -0.2, 0.62), lens=60)
    preview_stage(golden=True)
    shoot(os.path.join(PREV, "bl_golden.png"), 20, 10, 7.4)


if __name__ == "__main__":
    root, meshes, mats = build()
    export(root)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)  # before previews: they add preview-only textures + lights
    if "--previews" in ARGS:
        previews(mats)
