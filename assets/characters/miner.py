"""miner.glb: MOTHERLODE's third-person miner (other players + NPC crews), 1.78 m, front +Z (Blender -Y),
origin at the feet. One skinned mesh (7 materials) + held props as separate root nodes.

    bl assets/characters/miner.py -- [out.glb] [previews_dir] [mode: full|quick|none]

Body: torso/arms/legs/neck/head lofts voxel-unioned into one surface (bone-heat weights), procedural head
with stubble/brows/hair painted into COLOR_0; clothing shells (vest with reflective tape, collar, rolled
sleeves, belt + pouches + cap-lamp battery + cord, knee pads), leather gloves (glove.py, grouped finger
bones), boots, hard hat + headlamp (empty `lamp`), safety glasses. Clips are procedural: IK feet stay
planted, tool clips keep both hands on the handle. Every clip keys every bone.
"""
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import bmesh  # noqa: E402
import bpy  # noqa: E402
from mathutils import Matrix, Quaternion, Vector, noise  # noqa: E402

import bk  # noqa: E402
import ck  # noqa: E402
import glove  # noqa: E402
from ck import V, clamp, lerp, smoothstep  # noqa: E402

ARGS = bk.args()
OUT = os.path.abspath(ARGS[0]) if ARGS else os.path.join(HERE, "..", "..", "public", "models", "characters", "miner.glb")
PREV = os.path.abspath(ARGS[1]) if len(ARGS) > 1 else os.path.join(HERE, "previews")
MODE = ARGS[2] if len(ARGS) > 2 else "full"
FPS = 30
TAU = math.tau
T0 = time.time()

bk.reset()
scn = bpy.context.scene
scn.render.fps = FPS


def log(*a):
    print(f"[miner {time.time() - T0:5.1f}s]", *a)


def sx(v, side):
    """Mirror a left-side (+X) point to `side`."""
    return V((v[0] if side == "L" else -v[0], v[1], v[2]))


def eul(d):
    if d is None:
        return Matrix.Identity(4)
    return ck.rot("X", d[0]) @ ck.rot("Y", d[1]) @ ck.rot("Z", d[2])


# ====================================================================== skeleton (A-pose rest)
HIP_J = V((0.092, 0.000, 0.925))
KNEE = V((0.096, -0.014, 0.497))
ANKLE = V((0.098, 0.018, 0.085))
BALL = V((0.102, -0.108, 0.022))
TOE = V((0.104, -0.180, 0.018))
SH_J = V((0.178, 0.015, 1.445))
CLAV_H = V((0.025, 0.000, 1.430))
UPPER, FORE, HANDLEN = 0.295, 0.258, 0.090
UPPER_DIR = V((0.70, 0.03, -0.71)).normalized()
FORE_DIR = V((0.60, -0.12, -0.79)).normalized()

rig = ck.Rig("miner_rig")
rig.add("hips", None, (0, 0.0, 0.94), (0, 0, 1), (0, -1, 0), 0.10)
rig.add("spine", "hips", (0, 0.0, 1.04), (0, 0.03, 1), (0, -1, 0), 0.18)
rig.add("chest", "spine", (0, 0.005, 1.22), (0, 0.02, 1), (0, -1, 0), 0.225)
rig.add("neck", "chest", (0, 0.012, 1.468), (0, -0.10, 1), (0, -1, 0), 0.118)
rig.add("head", "neck", (0, 0.000, 1.585), (0, 0, 1), (0, -1, 0), 0.20)
HAND_REST = {}
for side in "LR":
    sj, ch = sx(SH_J, side), sx(CLAV_H, side)
    rig.add(f"shoulder.{side}", "chest", ch, sj - ch, (0, -1, 0), (sj - ch).length)
    ua, fa, hd = f"upperarm.{side}", f"forearm.{side}", f"hand.{side}"
    rig.length[ua], rig.length[fa] = UPPER, FORE
    ud, fd = sx(UPPER_DIR, side), sx(FORE_DIR, side)
    E = sj + ud * UPPER
    W = E + fd * FORE
    dors = sx(V((0.78, 0.0, 0.62)), side)
    Hm = ck.frame(W, fd, dors)
    chain, ok, _ = ck.limb(rig, ua, fa, hd, sj, W, Hm, E + (E - (sj + W) / 2) * 2 + V((0, 0.05, 0)))
    rig.add_frame(ua, f"shoulder.{side}", chain[ua], UPPER)
    rig.add_frame(fa, ua, chain[fa], FORE)
    rig.add_frame(hd, fa, chain[hd], HANDLEN)
    HAND_REST[side] = chain[hd]
    defs = {n: (M, L) for n, p, M, L in glove.bone_defs(side)}
    Hr = chain[hd]
    rig.add_frame(f"fingers.{side}", hd, Hr @ defs[f"middle.01.{side}"][0], defs[f"middle.01.{side}"][1])
    rig.add_frame(f"fingertips.{side}", f"fingers.{side}", Hr @ defs[f"middle.02.{side}"][0],
                  defs[f"middle.02.{side}"][1] + defs[f"middle.03.{side}"][1])
    rig.add_frame(f"thumb.{side}", hd, Hr @ defs[f"thumb.01.{side}"][0], sum(glove.THUMB["lens"]))
    th, sh, ft = f"thigh.{side}", f"shin.{side}", f"foot.{side}"
    hj, kn, an, ba, to = (sx(p, side) for p in (HIP_J, KNEE, ANKLE, BALL, TOE))
    rig.length[th], rig.length[sh] = (kn - hj).length, (an - kn).length
    footM = ck.frame(an, ba - an, (0, 0, 1))
    chain, ok, _ = ck.limb(rig, th, sh, ft, hj, an, footM, kn + (kn - (hj + an) / 2) * 3 + V((0, -0.2, 0)), 0.3)
    rig.add_frame(th, "hips", chain[th], rig.length[th])
    rig.add_frame(sh, th, chain[sh], rig.length[sh])
    rig.add_frame(ft, sh, chain[ft], (ba - an).length)
    rig.add(f"toe.{side}", ft, ba, to - ba, (0, 0, 1), (to - ba).length)
arm = rig.build()
FINGER_BONES = [b for b in rig.order if b.split(".")[0] in ("fingers", "fingertips", "thumb")]
log("rig", len(rig.order), "bones")

# ====================================================================== body union
HC = V((0, 0.008, 1.663))  # head centre


def g(x):
    return math.exp(-x * x)


def head_md():
    md = ck.MeshData()
    rx, ry, rz = 0.0790, 0.1000, 0.1170
    rings, segs = 44, 52
    rows = []
    for i in range(1, rings):
        ph = math.pi * i / rings
        row = []
        for k in range(segs):
            th = TAU * k / segs
            p = V((rx * math.sin(ph) * math.cos(th), ry * math.sin(ph) * math.sin(th), rz * math.cos(ph)))
            row.append(md.v(HC + head_shape(p)))
        rows.append(row)
    top = md.v(HC + head_shape(V((0, 0, rz))))
    bot = md.v(HC + head_shape(V((0, 0, -rz))))
    for k in range(segs):
        k1 = (k + 1) % segs
        md.f((top, rows[0][k], rows[0][k1]), "skin", part=6)
        md.f((bot, rows[-1][k1], rows[-1][k]), "skin", part=6)
    for i in range(len(rows) - 1):
        a, b = rows[i], rows[i + 1]
        for k in range(segs):
            k1 = (k + 1) % segs
            md.f((a[k], b[k], b[k1], a[k1]), "skin", part=6)
    return md


def head_shape(p):
    """Sculpt an ellipsoid into a head (local coords: y forward is NEGATIVE, z up, head centre origin)."""
    x, y, z = p.x, p.y, p.z
    if z < 0.0:  # jaw narrower, back of the lower skull tucks into the neck
        k = smoothstep(0.0, -0.10, z)
        x *= 1 - 0.07 * k
        if y > 0:
            y *= 1 - 0.30 * k
    if z > 0.03:  # cranium slightly fuller at the back
        y += 0.010 * smoothstep(0.03, 0.10, z) * (1 if y > 0 else 0.2)
    if y < -0.055:  # flatter face plane
        y = -0.055 + (y + 0.055) * 0.72
    f = 0.0  # forward displacement (towards -Y) for facial features
    ax = abs(x)
    # nose: bridge -> tip -> base
    if z < 0.03 and z > -0.06:
        prof = smoothstep(0.028, -0.030, z) * (1 - smoothstep(-0.040, -0.052, z))
        f += 0.024 * prof * g(x / (0.0085 + 0.006 * smoothstep(0.0, -0.04, z)))
    f += 0.007 * g(math.hypot(ax - 0.0135, (z + 0.043) * 1.3) / 0.0075)  # alae
    f += 0.0065 * g((z - 0.031) / 0.010) * g(x / 0.050)  # brow ridge
    f -= 0.0105 * g(math.hypot(ax - 0.031, (z - 0.010) * 1.2) / 0.0155)  # eye sockets
    f += 0.005 * g(math.hypot(ax - 0.049, z + 0.012) / 0.016)  # cheekbones
    f += 0.0055 * g(math.hypot(x, (z + 0.062) * 0.9) / 0.030)  # muzzle
    f += 0.0042 * g(math.hypot(x / 1.8, z + 0.055) / 0.0065)  # upper lip
    f += 0.0042 * g(math.hypot(x / 1.7, z + 0.071) / 0.0065)  # lower lip
    f -= 0.0030 * g((z + 0.0635) / 0.0017) * g(x / 0.021)  # mouth line
    f += 0.0120 * g(math.hypot(x / 1.5, z + 0.100) / 0.019)  # square chin
    if y < 0:
        y -= f * smoothstep(-0.02, -0.06, y)
    if ax > 0.035 and z < -0.04:  # strong jaw angle
        x += math.copysign(0.009 * g(math.hypot(y - 0.015, z + 0.078) / 0.024), x)
    return V((x, y, z))


def build_body():
    md = ck.MeshData()
    # torso: (z, half-width, front depth, back depth, centre y)
    prof = [(0.800, 0.150, 0.095, 0.105, 0.010), (0.860, 0.172, 0.100, 0.118, 0.012),
            (0.930, 0.176, 0.098, 0.120, 0.010), (0.990, 0.165, 0.098, 0.106, 0.005),
            (1.060, 0.158, 0.104, 0.098, 0.000), (1.140, 0.161, 0.108, 0.098, -0.003),
            (1.220, 0.169, 0.115, 0.100, -0.005), (1.300, 0.179, 0.121, 0.104, -0.006),
            (1.370, 0.182, 0.117, 0.106, -0.004), (1.420, 0.175, 0.104, 0.101, 0.000),
            (1.462, 0.128, 0.080, 0.084, 0.006), (1.490, 0.080, 0.062, 0.068, 0.010)]
    pts = [V((0, q[4], q[0])) for q in prof]

    def trad(i, s):
        return (max(prof[i][2], prof[i][3]), prof[i][1], 2.5)

    def tshape(i, a, x, y):
        k = prof[i][2] / max(prof[i][2], prof[i][3]) if x > 0 else prof[i][3] / max(prof[i][2], prof[i][3])
        return x * k, y

    ck.tube(md, pts, trad, 36, "fabric_shirt", up=(0, -1, 0), part=1, cap0="flat", cap1="flat", rfn=tshape)
    for side in "LR":
        glove.sphere(md, sx(V((0.170, 0.012, 1.412)), side), (0.064, 0.066, 0.060), 16, 12, "fabric_shirt", {},
                     part=2)
        # arm: shirt sleeve to just above the elbow, bare forearm to the wrist
        sj = rig.head(f"upperarm.{side}")
        E = rig.head(f"forearm.{side}")
        W = rig.head(f"hand.{side}")
        up = [sj + (E - sj) * u for u in (0.0, 0.25, 0.5, 0.75, 0.92)]
        ck.tube(md, up + [E], lambda i, s: [(0.054, 0.052), (0.051, 0.049), (0.048, 0.046), (0.046, 0.044),
                                            (0.044, 0.042), (0.041, 0.040)][i], 18, "fabric_shirt",
                up=(0, -1, 0), part=3, cap0="flat", cap1="flat")
        fp = [E + (W - E) * u for u in (-0.04, 0.2, 0.45, 0.7, 0.9, 1.04)]
        ck.tube(md, fp, lambda i, s: [(0.040, 0.041), (0.040, 0.042), (0.036, 0.038), (0.032, 0.034),
                                      (0.029, 0.031), (0.027, 0.029)][i], 16, "skin", up=(0, -1, 0), part=4,
                cap0="flat", cap1="flat")
        # leg: trousers from hip to the boot
        hj = rig.head(f"thigh.{side}")
        kn = rig.head(f"shin.{side}")
        an = rig.head(f"foot.{side}")
        lp = [hj + V((0, 0.0, 0.06)), hj, hj + (kn - hj) * 0.35, hj + (kn - hj) * 0.7, kn,
              kn + (an - kn) * 0.3, kn + (an - kn) * 0.6, kn + (an - kn) * 0.82]
        lr = [(0.092, 0.090), (0.090, 0.088), (0.084, 0.082), (0.076, 0.074), (0.071, 0.068), (0.067, 0.064),
              (0.062, 0.060), (0.063, 0.061)]
        ck.tube(md, lp, lambda i, s: lr[i], 20, "fabric_denim", up=(0, -1, 0), part=7, cap0="flat", cap1="flat")
    # neck (with an Adam's apple)
    np_ = [V((0, 0.020, 1.440)), V((0, 0.016, 1.500)), V((0, 0.012, 1.560)), V((0, 0.010, 1.625))]
    ck.tube(md, np_, lambda i, s: [(0.068, 0.068), (0.064, 0.064), (0.060, 0.061), (0.056, 0.057)][i], 18, "skin",
            up=(0, -1, 0), part=5, cap0="flat", cap1="flat",
            rfn=lambda i, a, x, y: (x + 0.006 * g((i - 1.4) / 0.6) * max(0.0, math.cos(a)) ** 8, y))
    md.add(head_md())
    for side in "LR":  # ears
        c = HC + sx(V((0.0765, 0.014, 0.002)), side)
        glove.sphere(md, c, (0.011, 0.024, 0.031), 12, 9, "skin", {}, part=8)
    return md


def body_mat(c, n, part, m):
    if part in (1,):
        return "fabric_shirt" if c.z > 0.985 else "fabric_denim"
    if part in (2, 3):
        return "fabric_shirt"
    if part in (4, 5, 6, 8):
        return "skin"
    return "fabric_denim"


log("body union")
body = ck.remesh_transfer(build_body(), "body", 0.0028, 6400, smooth_iter=5, smooth_fac=0.5, matfn=body_mat)
log("body tris", ck.tris([body]))

# ====================================================================== gloves (leather, grouped finger bones)
GROUP = {}
for side in "LR":
    for f in glove.FINGERS:
        GROUP[f"{f}.01.{side}"] = f"fingers.{side}"
        GROUP[f"{f}.02.{side}"] = f"fingertips.{side}"
        GROUP[f"{f}.03.{side}"] = f"fingertips.{side}"
    for j in range(3):
        GROUP[f"thumb.0{j + 1}.{side}"] = f"thumb.{side}"


def merge_groups(obj):
    names = [gr.name for gr in obj.vertex_groups]
    acc = []
    for v in obj.data.vertices:
        w = {}
        for ge in v.groups:
            n = GROUP.get(names[ge.group], names[ge.group])
            w[n] = w.get(n, 0.0) + ge.weight
        acc.append(w)
    for gr in list(obj.vertex_groups):
        obj.vertex_groups.remove(gr)
    groups = {}
    for i, w in enumerate(acc):
        for n, x in w.items():
            gg = groups.get(n) or obj.vertex_groups.new(name=n)
            groups[n] = gg
            gg.add([i], min(1.0, x), "REPLACE")


gl = {}
gR = ck.remesh_transfer(glove.build("R", 0.6), "glove_R", 0.0018, 500, smooth_iter=2, smooth_fac=0.35)
gR.data.materials.clear()
gR.data.materials.append(ck.material("leather"))
gR.data.polygons.foreach_set("material_index", [0] * len(gR.data.polygons))
gL = gR.copy()
gL.data = gR.data.copy()
gL.name = "glove_L"
bpy.context.scene.collection.objects.link(gL)
gL.data.transform(Matrix.Diagonal((-1, 1, 1, 1)))
gL.data.flip_normals()
for gr in gL.vertex_groups:
    if gr.name.endswith(".R"):
        gr.name = gr.name[:-2] + ".L"
for o, side in ((gR, "R"), (gL, "L")):
    merge_groups(o)
    o.data.transform(rig.rest[f"hand.{side}"])
    gl[side] = o


# ====================================================================== boots
def boot(side):
    md = ck.MeshData()
    an = rig.head(f"foot.{side}")
    cx = an.x
    sh = [V((cx, 0.024, z)) for z in (0.07, 0.12, 0.17, 0.205, 0.218)]
    ck.tube(md, sh, lambda i, s: [(0.060, 0.054), (0.062, 0.055), (0.064, 0.057), (0.070, 0.062),
                                  (0.067, 0.059)][i], 18, "leather", up=(0, -1, 0), cap0="flat", cap1="flat")
    # foot: (y, half-width, top height) with a flat-ish sole at z = 0.028
    fp = [(0.108, 0.040, 0.100), (0.070, 0.047, 0.132), (0.010, 0.051, 0.126), (-0.050, 0.055, 0.098),
          (-0.105, 0.057, 0.078), (-0.155, 0.053, 0.070), (-0.192, 0.042, 0.062), (-0.207, 0.024, 0.052)]
    pts = [V((cx, q[0], (q[2] + 0.028) / 2)) for q in fp]
    ck.tube(md, pts, lambda i, s: ((fp[i][2] - 0.028) / 2, fp[i][1], 2.6), 18, "leather", up=(0, 0, 1),
            cap0="flat", cap1=("dome", 2, 0.012))
    so = [(0.114, 0.044), (0.06, 0.054), (-0.02, 0.058), (-0.10, 0.063), (-0.17, 0.057), (-0.205, 0.040),
          (-0.214, 0.022)]
    pts = [V((cx, q[0], 0.0165)) for q in so]
    ck.tube(md, pts, lambda i, s: (0.0165, so[i][1], 5.0), 16, "leather", up=(0, 0, 1), cap0="flat", cap1="flat")
    o = ck.remesh_transfer(md, f"boot_{side}", 0.0024, 420, smooth_iter=1, smooth_fac=0.3)
    ft, toe, shn = f"foot.{side}", f"toe.{side}", f"shin.{side}"
    for gr in list(o.vertex_groups):
        o.vertex_groups.remove(gr)
    gs = {b: o.vertex_groups.new(name=b) for b in (ft, toe, shn)}
    ball_y = rig.head(toe).y
    for v in o.data.vertices:
        c = v.co
        t_sh = smoothstep(0.10, 0.17, c.z) * smoothstep(-0.02, 0.04, c.y)
        t_toe = smoothstep(ball_y + 0.015, ball_y - 0.025, c.y) * (1 - t_sh)
        w = {shn: t_sh, toe: t_toe, ft: max(0.0, 1 - t_sh - t_toe)}
        for b, x in w.items():
            if x > 1e-3:
                gs[b].add([v.index], x, "REPLACE")
    return o


boots = {s: boot(s) for s in "LR"}
log("gloves + boots")

# ====================================================================== bone-heat weights on the body
for b in FINGER_BONES + ["toe.L", "toe.R", "foot.L", "foot.R"]:
    arm.data.bones[b].use_deform = False
bk.select([body, arm], active=arm)
bpy.ops.object.parent_set(type="ARMATURE_AUTO")
for b in FINGER_BONES + ["toe.L", "toe.R", "foot.L", "foot.R"]:
    arm.data.bones[b].use_deform = True
body.parent = None
for m in list(body.modifiers):
    body.modifiers.remove(m)
missing = [v.index for v in body.data.vertices if not v.groups]
log("bone heat done, unweighted verts:", len(missing))
ck.limit_weights(body, 4, smooth=2, smooth_fac=0.3)


# ====================================================================== clothing shells
def ring_at(z, prof, off=0.0, n=24, front_extra=0.0):
    """Points around the torso at height z (interpolated profile), pushed out by `off`."""
    zs = [q[0] for q in prof]
    i = max(0, min(len(prof) - 2, max(j for j in range(len(zs)) if zs[j] <= z) if z >= zs[0] else 0))
    u = clamp((z - zs[i]) / (zs[i + 1] - zs[i]))
    q = [lerp(a, b, u) for a, b in zip(prof[i], prof[i + 1])]
    _, w, df, db, cy = q
    out = []
    for k in range(n):
        th = TAU * k / n  # 0 = front (-Y), pi/2 = character's left (+X)
        c, s = math.cos(th), math.sin(th)
        d = (df + front_extra) if c > 0 else db
        e = 2 / 2.5
        yy = -(d + off) * math.copysign(abs(c) ** e, c)
        xx = (w + off) * math.copysign(abs(s) ** e, s)
        out.append(V((xx, cy + yy, z)))
    return out


TORSO = [(0.800, 0.150, 0.095, 0.105, 0.010), (0.860, 0.172, 0.100, 0.118, 0.012),
         (0.930, 0.176, 0.098, 0.120, 0.010), (0.990, 0.165, 0.098, 0.106, 0.005),
         (1.060, 0.158, 0.104, 0.098, 0.000), (1.140, 0.161, 0.108, 0.098, -0.003),
         (1.220, 0.169, 0.115, 0.100, -0.005), (1.300, 0.179, 0.121, 0.104, -0.006),
         (1.370, 0.182, 0.117, 0.106, -0.004), (1.420, 0.175, 0.104, 0.101, 0.000),
         (1.462, 0.128, 0.080, 0.084, 0.006), (1.490, 0.080, 0.062, 0.068, 0.010)]


def relax_boundary(o, iters=6, fac=0.5, zmin=-1.0):
    """Smooth stair-stepped cut edges into curves (boundary-only Laplacian), keeping the hem ring fixed."""
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bv = [v for v in bm.verts if v.is_boundary and v.co.z > zmin]
    nb = {v: [e.other_vert(v) for e in v.link_edges if e.is_boundary] for v in bv}
    for _ in range(iters):
        new = {}
        for v in bv:
            ns = nb[v]
            if len(ns) == 2:
                new[v] = v.co.lerp((ns[0].co + ns[1].co) / 2, fac)
        for v, c in new.items():
            v.co = c
    bm.to_mesh(o.data)
    bm.free()


def vest():
    md = ck.MeshData()
    n = 32
    zs = [0.985, 1.02, 1.05, 1.10, 1.15, 1.20, 1.25, 1.30, 1.34, 1.38, 1.41, 1.435, 1.458, 1.478]
    rows = [[md.v(p) for p in ring_at(z, TORSO, 0.014 if z < 1.44 else 0.012, n, 0.006)] for z in zs]

    def keep(i, k):
        z = (zs[i] + zs[i + 1]) / 2
        th = (k + 0.5) / n * 360.0
        d_side = min(abs(th - 90), abs(th - 270))
        if 1.215 < z < 1.43:
            shape = math.sqrt(max(0.0, 1 - ((z - 1.36) / 0.15) ** 2))
            if d_side < 46 * shape:
                return False
        dfront = min(th, 360 - th)
        if z > 1.30 and dfront < 6 + 34 * smoothstep(1.30, 1.478, z):
            return False
        if z > 1.44 and abs(th - 180) < 30:
            return False
        return True

    def mat(i, k):
        z0, z1 = zs[i], zs[i + 1]
        th = (k + 0.5) / n * 360.0
        if z0 >= 1.05 - 1e-6 and z1 <= 1.10 + 1e-6:
            return "custom_reflective"
        if z0 >= 1.10 - 1e-6:
            for c in (22.5, 337.5, 157.5, 202.5):
                if abs(th - c) < 5.7:
                    return "custom_reflective"
        return "fabric_hivis"

    for i in range(len(rows) - 1):
        for k in range(n):
            if keep(i, k):
                k1 = (k + 1) % n
                md.f((rows[i][k], rows[i][k1], rows[i + 1][k1], rows[i + 1][k]), mat(i, k))
    o = md.to_object("vest", smooth=True)
    relax_boundary(o, 6, 0.5, zmin=0.995)
    ck.box_uv(o)
    sol = o.modifiers.new("solid", "SOLIDIFY")
    sol.thickness = 0.0045
    sol.offset = -1.0
    sol.use_rim = True
    sol.use_even_offset = True
    bk.apply(o)
    try:
        o.data.set_sharp_from_angle(angle=math.radians(70))
    except Exception:
        pass
    # pocket + zipper strip
    return o


def collar():
    md = ck.MeshData()
    n = 22
    r1 = [md.v(V((0.078 * math.sin(t), 0.010 - 0.072 * math.cos(t), 1.468))) for t in (TAU * k / n for k in range(n))]
    r2 = [md.v(V((0.070 * math.sin(t), 0.012 - 0.064 * math.cos(t), 1.512))) for t in (TAU * k / n for k in range(n))]
    r3 = [md.v(V((0.092 * math.sin(t), 0.014 - 0.084 * math.cos(t), 1.486))) for t in (TAU * k / n for k in range(n))]
    for k in range(n):
        th = (k + 0.5) / n * 360
        if min(th, 360 - th) < 22:
            continue
        k1 = (k + 1) % n
        md.f((r1[k], r1[k1], r2[k1], r2[k]), "fabric_shirt")
        md.f((r2[k], r2[k1], r3[k1], r3[k]), "fabric_shirt")
    o = md.to_object("collar", smooth=True)
    sol = o.modifiers.new("solid", "SOLIDIFY")
    sol.thickness = 0.003
    sol.offset = 0.0
    bk.apply(o)
    return o


def sleeve_roll(side):
    md = ck.MeshData()
    sj = rig.head(f"upperarm.{side}")
    E = rig.head(f"forearm.{side}")
    ax = (E - sj).normalized()
    c = sj + (E - sj) * 0.90
    _, nn, bb = ck.path_frames([sj, E], up=(0, -1, 0))[0]
    pts = []
    for k in range(16):
        a = TAU * k / 16
        pts.append(c + (nn * math.cos(a) * 0.0485 + bb * math.sin(a) * 0.0465))
    pts.append(pts[0])
    ck.tube(md, pts, (0.0125, 0.0105), 8, "fabric_shirt", up=ax)
    return md.to_object(f"roll_{side}", smooth=True)


def belt():
    md = ck.MeshData()
    n = 30
    rows = [[md.v(p) for p in ring_at(z, TORSO, off, n)] for z, off in
            ((0.962, 0.004), (0.966, 0.009), (1.002, 0.009), (1.006, 0.004))]
    md.grid(rows, "leather", True)
    ck.rbox(md, (0.058, 0.012, 0.046), ck.T(0, -0.112, 0.984), "leather", bevel=0.004, seg=1)  # buckle
    ck.rbox(md, (0.070, 0.040, 0.085), ck.T(-0.150, -0.075, 0.938) @ ck.rot("Z", -35), "leather", bevel=0.008,
            seg=2)  # pouch
    ck.rbox(md, (0.072, 0.012, 0.030), ck.T(-0.162, -0.098, 0.980) @ ck.rot("Z", -35), "leather", bevel=0.004,
            seg=1)  # pouch flap
    md.scalar = 0.0
    return md


def battery_cord():
    md = ck.MeshData()
    ck.rbox(md, (0.120, 0.046, 0.098), ck.T(0.0, 0.142, 0.940), "leather", bevel=0.010, seg=2)  # cap-lamp battery
    ck.tube(md, [V((0.168, 0.040, 0.875)), V((0.168, 0.040, 1.005))], 0.042, 14, "leather", up=(0, -1, 0),
            cap0="flat", cap1="flat")  # self-rescuer canister on the left hip
    cord = [V((0.030, 0.150, 0.992)), V((0.040, 0.142, 1.10)), V((0.046, 0.132, 1.25)), V((0.040, 0.118, 1.40)),
            V((0.030, 0.100, 1.50)), V((0.022, 0.092, 1.60)), V((0.040, 0.100, 1.70)), V((0.060, 0.095, 1.745))]
    ck.tube(md, cord, 0.0055, 6, "leather", up=(0, -1, 0))
    return md


def knee_pad(side):
    md = ck.MeshData()
    kn = rig.head(f"shin.{side}")
    c = kn + V((0, -0.074, 0.0))
    glove.sphere(md, c, (0.058, 0.030, 0.072), 12, 8, "leather", {})
    for dz in (0.082, -0.078):
        pts = []
        for k in range(17):
            a = TAU * k / 16
            pts.append(kn + V((0.074 * math.sin(a), -0.004 - 0.070 * math.cos(a), dz)))
        ck.tube(md, pts, (0.004, 0.012), 6, "leather", up=(0, 0, 1))
    return md


def hard_hat():
    md = ck.MeshData()
    c = V((0, 0.006, 1.722))
    rings, segs = 12, 34
    rows = []
    for i in range(0, rings):
        ph = (math.pi / 2) * i / rings
        row = []
        for k in range(segs):
            th = TAU * k / segs
            x = 0.112 * math.cos(ph) * math.sin(th)
            y = -0.133 * math.cos(ph) * math.cos(th)
            z = 0.112 * math.sin(ph)
            ridge = 0.007 * g(x / 0.012) * smoothstep(0.2, 0.7, math.sin(ph))
            row.append(md.v(c + V((x, y, z + ridge))))
        rows.append(row)
    top = md.v(c + V((0, 0, 0.112 + 0.007)))
    for i in range(len(rows) - 1):
        md.grid([rows[i], rows[i + 1]], "helmet_yellow", True)
    for k in range(segs):
        md.f((rows[-1][k], rows[-1][(k + 1) % segs], top), "helmet_yellow")
    # brim: peaked at the front
    inner = rows[0]
    outer, lip = [], []
    for k in range(segs):
        th = TAU * k / segs
        ext = 0.022 + 0.040 * max(0.0, math.cos(th)) ** 2 + 0.010 * max(0.0, -math.cos(th))
        p = md.verts[inner[k]]
        d = V((p.x - c.x, p.y - c.y, 0)).normalized()
        outer.append(md.v(p + d * ext + V((0, 0, -0.010 - 0.006 * max(0.0, math.cos(th))))))
        lip.append(md.v(p + d * ext + V((0, 0, -0.018 - 0.006 * max(0.0, math.cos(th))))))
    under = [md.v(md.verts[i] + V((0, 0, -0.010))) for i in inner]
    md.grid([under, lip, outer, inner], "helmet_yellow", True)
    md.f(list(reversed(under)), "helmet_yellow")
    # lamp bracket + cap lamp + lens
    ck.rbox(md, (0.040, 0.014, 0.034), ck.T(0, -0.134, 1.766), "helmet_yellow", bevel=0.004, seg=1)
    lamp_c = V((0, -0.146, 1.772))
    beam = V((0, -0.985, -0.17)).normalized()
    ck.tube(md, [lamp_c, lamp_c + beam * 0.040], (0.029, 0.029), 18, "helmet_yellow", up=(0, 0, 1), cap0="flat")
    lens = lamp_c + beam * 0.040
    rows2 = []
    for rr, dd in ((0.029, 0.0), (0.025, 0.002), (0.0, 0.004)):
        if rr == 0.0:
            rows2.append(md.v(lens + beam * dd, sc=2.0))
        else:
            fr = ck.path_frames([lens, lens + beam], up=(0, 0, 1))[0]
            rows2.append([md.v(lens + beam * dd + (fr[1] * math.cos(a) + fr[2] * math.sin(a)) * rr, sc=2.0)
                          for a in (TAU * k / 18 for k in range(18))])
    md.grid([rows2[0], rows2[1]], "custom_reflective", True)
    for k in range(18):
        md.f((rows2[1][k], rows2[1][(k + 1) % 18], rows2[2]), "custom_reflective")
    # reflective stripe around the dome
    return md, lens, beam


def glasses():
    md = ck.MeshData()
    c = HC + V((0, 0.012, 0.008))
    rows = []
    for zz in (-0.0125, 0.0, 0.0115):
        row = []
        for k in range(15):
            a = math.radians(-72 + 144 * k / 14)
            r = 0.101 + 0.006 * math.cos(a)
            row.append(md.v(c + V((r * math.sin(a), -r * math.cos(a) * 1.04, zz - 0.004 * math.sin(a) ** 2))))
        rows.append(row)
    md.grid(rows, "helmet_yellow", closed=False)
    for sgn in (1, -1):
        p0 = md.verts[rows[1][0 if sgn < 0 else -1]]
        ck.rbox(md, (0.004, 0.090, 0.008), ck.T(p0.x + 0.002 * sgn, p0.y + 0.045, p0.z + 0.004), "helmet_yellow",
                bevel=0.0012, seg=1)
    o = md.to_object("glasses", smooth=True)
    sol = o.modifiers.new("solid", "SOLIDIFY")
    sol.thickness = 0.0028
    bk.apply(o)
    return o


log("shells")
shell_objs = {"vest": vest(), "collar": collar(), "roll_L": sleeve_roll("L"), "roll_R": sleeve_roll("R")}
shell_objs["belt"] = belt().to_object("belt", smooth=True)
shell_objs["battery"] = battery_cord().to_object("battery", smooth=True)
shell_objs["knee_L"] = knee_pad("L").to_object("knee_L", smooth=True)
shell_objs["knee_R"] = knee_pad("R").to_object("knee_R", smooth=True)
hat_md, LENS, BEAM = hard_hat()
hat = hat_md.to_object("hardhat", smooth=True)
specs = glasses()
for nm, o in shell_objs.items():
    ck.weights_from(body, o)
for o in (hat, specs):
    ck.weights_from(body, o, rigid={"head": 1.0})
bat = shell_objs["battery"]
for gr in list(bat.vertex_groups):
    bat.vertex_groups.remove(gr)
gsp = {b: bat.vertex_groups.new(name=b) for b in ("hips", "spine", "chest", "neck", "head")}
for v in bat.data.vertices:
    z = v.co.z
    w = {"hips": 1 - smoothstep(0.98, 1.10, z), "spine": smoothstep(0.98, 1.10, z) * (1 - smoothstep(1.22, 1.32, z)),
         "chest": smoothstep(1.22, 1.32, z) * (1 - smoothstep(1.44, 1.52, z)),
         "neck": smoothstep(1.44, 1.52, z) * (1 - smoothstep(1.58, 1.64, z)), "head": smoothstep(1.58, 1.64, z)}
    if v.co.x > 0.12 and z < 1.02:
        w = {"hips": 1.0}
    for b, x in w.items():
        if x > 1e-3:
            gsp[b].add([v.index], x, "REPLACE")

# ====================================================================== grime + paint, then one skinned mesh
parts = [body, gl["L"], gl["R"], boots["L"], boots["R"], hat, specs] + list(shell_objs.values())
for o in parts:
    if not o.data.uv_layers:
        ck.box_uv(o)
ck.bake_ao(parts, samples=20, dist=0.06, strength=0.7, floor=0.40)


def face_paint(co, n):
    p = co - HC
    k = 1.0
    if co.z > 1.45:
        # buzz-cut hair at the back/sides of the skull (below the hat), eyebrows, stubble, lips
        hair = smoothstep(0.030, 0.050, p.z) * smoothstep(0.010, 0.040, p.y) + \
            smoothstep(0.025, 0.045, p.z) * smoothstep(0.066, 0.078, abs(p.x)) * smoothstep(0.0, 0.03, p.y)
        k *= 1 - 0.68 * clamp(hair)
        brow = g(math.hypot(abs(p.x) - 0.032, (p.z - 0.034) * 2.2) / 0.016) * smoothstep(-0.05, -0.08, p.y)
        k *= 1 - 0.55 * brow
        stub = smoothstep(-0.03, -0.07, p.z) * smoothstep(0.035, -0.01, p.y) * (1 - smoothstep(-0.12, -0.13, p.z))
        stub = max(stub, g(math.hypot(p.x / 1.6, p.z + 0.050) / 0.010) * smoothstep(-0.07, -0.09, p.y))
        k *= 1 - 0.30 * clamp(stub)
        lips = g(math.hypot(p.x / 1.7, p.z + 0.063) / 0.008) * smoothstep(-0.08, -0.095, p.y)
        k *= 1 - 0.18 * lips
    return k


ck.paint_mul(body, face_paint)
for side in "LR":
    ck.paint_mul(boots[side], lambda co, n: 0.22 if co.z < 0.031 else (0.8 if co.z > 0.2 else 1.0))
    ck.paint_mul(shell_objs[f"knee_{side}"], lambda co, n: 0.16)
ck.paint_mul(specs, lambda co, n: 0.30)
ck.paint_mul(shell_objs["battery"], lambda co, n: 0.18)
ck.paint_mul(hat, lambda co, n: 0.14 if (co.y < -0.128 and co.z > 1.735) else 1.0)
ck.paint_mul(shell_objs["belt"], lambda co, n: 0.55 if abs(co.x) < 0.03 and co.y < -0.1 else 1.0)

for o in parts:
    for gr in o.vertex_groups:
        pass
miner = bk.join(parts, "miner")
ck.limit_weights(miner, 4)
ck.skin(miner, rig)
log("mesh", ck.tris([miner]), "tris", len(miner.data.materials), "materials",
    [m.name for m in miner.data.materials])

# ====================================================================== empties: grip_r, lamp
GRIP_R = 0.0165


def Hgrip(side, r):
    gg = V((-0.95, 0.30, 0.07))
    o = V((0.002, 0.071, -(0.0166 + r)))
    if side == "L":
        gg.x, o.x = -gg.x, -o.x
    gg.normalize()
    fwd = V((0, 1, 0)) - gg * gg.y
    fwd.normalize()
    return ck.zframe(o, gg, -fwd)


grip_r = bpy.data.objects.new("grip_r", None)
grip_r.empty_display_size = 0.05
bpy.context.scene.collection.objects.link(grip_r)
grip_r.matrix_world = rig.rest["hand.R"] @ Hgrip("R", GRIP_R)
ck.parent_to_bone(grip_r, rig, "hand.R")
lamp = bpy.data.objects.new("lamp", None)
lamp.empty_display_size = 0.04
bpy.context.scene.collection.objects.link(lamp)
lamp.matrix_world = ck.frame(LENS, BEAM, (0, 0, 1))  # local +Y (Blender) = beam = three.js local -Z
ck.parent_to_bone(lamp, rig, "head")


# ====================================================================== held props (root nodes, grip at origin)
# Prop frame (Blender): +Z along the handle towards the head/working end, -Y = working direction
# (pick point / chisel / blade face) -> three.js +Y handle, +Z working direction (matches grip_r).
def prop_pickaxe():
    md = ck.MeshData()
    secs = [(-0.300, 0.0120, 0.0098), (-0.296, 0.0200, 0.0160), (-0.286, 0.0222, 0.0178), (-0.262, 0.0195, 0.0148),
            (0.0, 0.0186, 0.0137), (0.300, 0.0213, 0.0154), (0.400, 0.0246, 0.0172), (0.470, 0.0246, 0.0172)]
    ck.tube(md, [V((0, 0, z)) for z, _, _ in secs], lambda i, s: (secs[i][1], secs[i][2]), 10, "wood_dark",
            up=(0, -1, 0), cap0="flat", cap1="flat")
    hp = [(-0.191, 0.0016, 0.0212), (-0.150, 0.0068, 0.0208), (-0.080, 0.0160, 0.0180), (0.0, 0.0215, 0.0175),
          (0.090, 0.0165, 0.0128), (0.170, 0.0080, 0.0068), (0.216, 0.0012, 0.0012)]
    pts = [V((0, -q[0], 0.432 - 0.62 * q[0] ** 2)) for q in hp]  # pick point towards -Y
    ck.tube(md, pts, lambda i, s: (hp[i][1], hp[i][2], 3.0), 10, "steel_dark", up=(0, 0, 1), cap0="flat",
            cap1="flat", matfn=lambda i, k: "steel" if i in (0, 5) else "steel_dark")
    ck.rbox(md, (0.048, 0.064, 0.056), ck.T(0, 0, 0.433), "steel_dark", bevel=0.007, seg=1)
    o = md.to_object("held_pickaxe", smooth=True)
    o.data.set_sharp_from_angle(angle=math.radians(45))
    return o


def prop_jackhammer():
    md = ck.MeshData()
    # design frame (+Y forward, +Z up, right grip at x=+0.15) -> prop frame through the right grip
    ck.tube(md, [V((-0.20, 0, 0)), V((0.20, 0, 0))], 0.0135, 10, "steel_dark", up=(0, 0, 1))
    for sg in (1, -1):
        ck.tube(md, [V((0.090 * sg, 0, 0)), V((0.205 * sg, 0, 0))], 0.0200, 10, "rubber", up=(0, 0, 1),
                cap1="flat")
    body = [(0.0, 0.050), (0.07, 0.050), (0.075, 0.054), (0.28, 0.054), (0.30, 0.044), (0.38, 0.042),
            (0.40, 0.030), (0.42, 0.024)]
    ptsb = [V((0, -0.006 + q[0], 0)) for q in body]
    ck.tube(md, ptsb, lambda i, s: (body[i][1], body[i][1]), 14, "paint_yellow", up=(0, 0, 1), cap0="flat",
            cap1="flat", matfn=lambda i, k: "paint_yellow" if 2 <= i <= 3 else "steel_dark")
    sh = [(0.42, 0.015), (0.50, 0.013), (0.62, 0.008), (0.70, 0.0015)]
    ck.tube(md, [V((0, q[0], 0)) for q in sh], lambda i, s: (sh[i][1], sh[i][1]), 8, "steel", up=(0, 0, 1),
            cap1="flat")
    ck.tube(md, [V((0, 0.02, -0.05)), V((0.01, -0.01, -0.13)), V((0.03, -0.06, -0.24))], 0.015, 8, "rubber",
            up=(0, 1, 0), cap1="flat")
    G = ck.zframe(V((0.15, 0, 0)), V((-1, 0, 0)), V((0, -1, 0)))
    md.transform(G.inverted())
    o = md.to_object("held_jackhammer", smooth=True)
    o.data.set_sharp_from_angle(angle=math.radians(45))
    return o, G


def prop_shovel():
    md = ck.MeshData()
    # grip on the shaft 0.25 m below the D-handle; +Z towards the blade
    ck.tube(md, [V((0, 0, -0.25)), V((0, 0, 0.78))], 0.0170, 10, "wood_dark", up=(0, -1, 0), cap0="flat")
    ck.tube(md, [V((0, 0, -0.25)), V((0, 0, -0.30))], 0.0185, 10, "steel_dark", up=(0, -1, 0))
    ck.tube(md, [V((-0.055, 0, -0.33)), V((0.055, 0, -0.33))], 0.0160, 10, "plastic_black", up=(0, 0, 1),
            cap0="flat", cap1="flat")
    for sg in (1, -1):
        ck.tube(md, [V((0.0, 0, -0.29)), V((0.05 * sg, 0, -0.32))], 0.010, 8, "steel_dark", up=(0, 0, 1))
    ck.tube(md, [V((0, 0, 0.74)), V((0, 0, 0.82))], (0.022, 0.026), 10, "steel_dark", up=(0, -1, 0))
    blade = ck.MeshData()
    rows = []
    for zz, w in ((0.80, 0.075), (0.90, 0.120), (1.02, 0.122), (1.10, 0.090), (1.12, 0.020)):
        rows.append([blade.v(V((x * w, 0.012 * (1 - x * x) - 0.008, zz))) for x in (-1, -0.5, 0, 0.5, 1)])
    blade.grid(rows, "steel_dark", closed=False)
    bo = blade.to_object("blade", smooth=True)
    sol = bo.modifiers.new("s", "SOLIDIFY")
    sol.thickness = 0.003
    ck.absorb(md, bo, "steel_dark")
    o = md.to_object("held_shovel", smooth=True)
    return o


props = [prop_pickaxe()]
pj, JH_G = prop_jackhammer()
props += [pj, prop_shovel()]
for p in props:
    ck.bake_ao([p], samples=16, dist=0.02, strength=0.6, floor=0.45)
log("props", {p.name: ck.tris([p]) for p in props})

# ====================================================================== animation
SIDES = "LR"
REL = {"fingers": 22, "tips": 32, "thumb": (-8, 0, -6)}
GRIP = {"fingers": 68, "tips": 92, "thumb": (-30, -25, -18)}
OPEN = {"fingers": 2, "tips": 4, "thumb": (6, 0, 10)}


class Pose:
    def __init__(self):
        self.hips = V((0, 0, 0))
        self.rot = {}
        self.arm = {}
        self.leg = {}
        self.fing = {"L": REL, "R": REL}


HIPS_LO = rig.rest["hips"].inverted()
THIGH_LOCAL = {s: HIPS_LO @ rig.head(f"thigh.{s}") for s in SIDES}
FOOT_REST = {s: rig.rest[f"foot.{s}"].copy() for s in SIDES}
HEEL = {s: V((rig.head(f"foot.{s}").x, rig.head(f"foot.{s}").y + 0.075, 0.0)) for s in SIDES}
BALLP = {s: V((rig.head(f"toe.{s}").x, rig.head(f"toe.{s}").y, 0.0)) for s in SIDES}


def foot_place(side, y, lift, pitch, yaw=0.0, x=None):
    """Foot target: slide the rest foot to y (+lift), toe-out yaw (deg), pitch (deg, + = toe up) about the heel
    (toe up) or the ball (heel up). Returns (ankle position, foot matrix)."""
    R0 = FOOT_REST[side]
    an0 = R0.translation.copy()
    piv = HEEL[side] if pitch > 0 else BALLP[side]
    M = ck.T(piv) @ ck.rot("X", -pitch) @ ck.T(-piv)
    Y = ck.T(an0.x, an0.y, 0) @ ck.rot("Z", yaw if side == "L" else -yaw) @ ck.T(-an0.x, -an0.y, 0)
    D = ck.T(0 if x is None else x - an0.x, y, lift)
    F = D @ Y @ M
    FM = F @ R0
    return FM.translation.copy(), FM


def arm_fk(side, S, upper_dir, elbow, bend_dir, dorsal, wrist=(0, 0, 0)):
    ud = V(upper_dir).normalized()
    bd = V(bend_dir)
    n = ud.cross(bd)
    if n.length < 1e-6:
        n = ud.orthogonal()
    n.normalize()
    fd = Quaternion(n, math.radians(elbow)) @ ud
    E = S + ud * UPPER
    W = E + fd * FORE
    Hm = ck.frame(W, fd, dorsal) @ eul(wrist)
    return Hm, E + (E - (S + W) / 2) * 2


FAILS = set()


def solve(ps):
    P = {"hips": ck.T(ps.hips) @ rig.rest["hips"] @ eul(ps.rot.get("hips"))}
    for b in ("spine", "chest", "neck", "head"):
        P[b] = rig.fk(b, P, eul(ps.rot.get(b)))
    ok_all = True
    for s in SIDES:
        sh = f"shoulder.{s}"
        P[sh] = rig.fk(sh, P, eul(ps.rot.get(sh)))
        S = P[sh] @ V((0, rig.length[sh], 0))
        spec = ps.arm[s]
        if spec[0] == "ik":
            Hm, pole = spec[1], spec[2]
        else:
            Hm, pole = arm_fk(s, S, *spec[1:])
        ch, ok, _ = ck.limb(rig, f"upperarm.{s}", f"forearm.{s}", f"hand.{s}", S, Hm.translation, Hm, pole)
        if not ok:
            FAILS.add(f"arm.{s}")
        ok_all = ok_all and ok
        P.update(ch)
        fg = ps.fing[s]
        P[f"fingers.{s}"] = rig.fk(f"fingers.{s}", P, ck.rot("X", -fg["fingers"]))
        P[f"fingertips.{s}"] = rig.fk(f"fingertips.{s}", P, ck.rot("X", -fg["tips"]))
        th = fg["thumb"]
        P[f"thumb.{s}"] = rig.fk(f"thumb.{s}", P, eul(th if s == "R" else (th[0], -th[1], -th[2])))
        an, FM, toe = ps.leg[s]
        Hj = P["hips"] @ THIGH_LOCAL[s]
        pole = Hj + V((0, -0.55, -0.35)) + V((0.05 if s == "L" else -0.05, 0, 0))
        ch, ok, _ = ck.limb(rig, f"thigh.{s}", f"shin.{s}", f"foot.{s}", Hj, an, FM, pole, 0.3)
        if not ok:
            FAILS.add(f"leg.{s}")
        ok_all = ok_all and ok
        P.update(ch)
        P[f"toe.{s}"] = rig.fk(f"toe.{s}", P, ck.rot("X", toe))
    return P, ok_all


def stand(ps, wide=0.0, out=8.0, fwd_l=0.0, fwd_r=0.0):
    for s in SIDES:
        x = rig.head(f"foot.{s}").x * (1 + wide)
        y = fwd_l if s == "L" else fwd_r
        an, FM = foot_place(s, y, 0.0, 0.0, out, x)
        ps.leg[s] = (an, FM, 0.0)


def hang_arms(ps, t=0.0, amp=1.0, swing=(0.0, 0.0), elbow=(14, 14)):
    for i, s in enumerate(SIDES):
        sg = 1 if s == "L" else -1
        sw = swing[i]
        ud = V((0.13 * sg, -0.42 * sw, -1.0))
        bend = V((0, -1, 0.15))
        ps.arm[s] = ("fk", ud, elbow[i], bend, V((0.92 * sg, 0.25, 0.1)), (0, 0, 0))


def tool_frame(g_, h_, pick):
    return ck.zframe(g_, h_ - g_, -pick)


def tool_hands(T, left_local, r_l=0.0165, r_r=0.0165):
    R = T @ Hgrip("R", r_r).inverted()
    L = T @ left_local @ Hgrip("L", r_l).inverted()
    return R, L


# ---------------------------------------------------------------- clips
def c_idle(t):
    ps = Pose()
    w = TAU * t / 4.0
    ps.hips = V((0.012 * math.sin(w), 0.002 * math.sin(2 * w), -0.012 + 0.003 * math.sin(2 * w + 0.5)))
    ps.rot["hips"] = (0, 0, 1.6 * math.sin(w))
    ps.rot["spine"] = (1.0 + 0.6 * math.sin(w + 1.0), 0, -1.2 * math.sin(w))
    ps.rot["chest"] = (-1.5 + 1.1 * math.sin(w * 1.0 + 0.4), 0, -0.6 * math.sin(w))
    ps.rot["neck"] = (2.0, 2.0 * math.sin(w + 0.6), 0)
    ps.rot["head"] = (1.5 * math.sin(2 * w), 5.0 * math.sin(w + 1.3), 0)
    stand(ps, 0.12, 9.0, -0.01, 0.02)
    hang_arms(ps, t, elbow=(14 + 2 * math.sin(w), 15 - 2 * math.sin(w)))
    return ps


def walk_cycle(t, period, stride, lift, lean, hips_drop, arm_amp, elbow0, elbow_k, run=False, y_off=0.0):
    ps = Pose()
    ph = (t / period) % 1.0
    w = TAU * ph
    stance = 0.38 if run else 0.60
    for s in SIDES:
        p = (ph + (0.0 if s == "L" else 0.5)) % 1.0
        if p < stance:
            u = p / stance
            y = -stride / 2 + stride * u + y_off
            hl = 0.0
            if run:
                pitch = 8 * (1 - smoothstep(0.0, 0.25, u)) - 30 * smoothstep(0.55, 1.0, u)
            else:
                pitch = 14 * (1 - smoothstep(0.0, 0.16, u)) - 32 * smoothstep(0.62, 1.0, u)
            toe = 30 * smoothstep(0.6, 1.0, u) if pitch < 0 else 0.0
        else:
            u = (p - stance) / (1 - stance)
            e = ck.ease_io(u, 2.0)
            y = stride / 2 - stride * e + y_off
            hl = lift * math.sin(math.pi * u) ** (0.8 if run else 1.0)
            if run:
                hl += 0.10 * math.sin(math.pi * clamp(u * 1.6)) * (1 - u)
            pitch = lerp(-30, 12, smoothstep(0.1, 0.9, u)) if not run else lerp(-35, 8, smoothstep(0.2, 0.9, u))
            toe = 20 * (1 - smoothstep(0.0, 0.3, u))
        an, FM = foot_place(s, y, hl, pitch, 7.0)
        ps.leg[s] = (an, FM, toe)
    if run:
        bob = -hips_drop + 0.035 * (0.5 - 0.5 * math.cos(2 * w * 1.0 + math.pi * 0.9))
    else:
        bob = -hips_drop + 0.034 * math.sin(w * 2.0 - math.pi / 2) * 0.5 + 0.017
    ps.hips = V((0.020 * math.sin(w) * (0.4 if run else 1.0), 0.0, bob))
    ps.rot["hips"] = (lean * 0.4, 6.0 * math.sin(w), 3.5 * math.sin(w + 0.3))
    ps.rot["spine"] = (lean * 0.35, -4.0 * math.sin(w), -1.5 * math.sin(w))
    ps.rot["chest"] = (lean * 0.25, -5.0 * math.sin(w), -1.0 * math.sin(w))
    ps.rot["neck"] = (-lean * 0.4, 2.0 * math.sin(w), 0)
    ps.rot["head"] = (-lean * 0.3, 1.5 * math.sin(w), 0)
    sw = math.sin(w)
    if run:
        for i, s in enumerate(SIDES):
            sg = 1 if s == "L" else -1
            a = sw * (-1 if s == "L" else 1)
            ud = V((0.18 * sg, -0.75 * a, -1.0))
            ps.arm[s] = ("fk", ud, elbow0 + elbow_k * max(0.0, a), V((0.0, -1, 0.3)), V((0.85 * sg, 0.2, 0.35)),
                         (0, 0, 0))
        ps.fing = {"L": {"fingers": 55, "tips": 70, "thumb": (-20, 0, -15)},
                   "R": {"fingers": 55, "tips": 70, "thumb": (-20, 0, -15)}}
    else:
        hang_arms(ps, t, swing=(-arm_amp * sw, arm_amp * sw),
                  elbow=(elbow0 + elbow_k * max(0.0, -sw), elbow0 + elbow_k * max(0.0, sw)))
    return ps


def c_walk(t):
    return walk_cycle(t, 1.1, 0.62, 0.095, 4.0, 0.042, 0.55, 14, 16)


def c_run(t):
    return walk_cycle(t, 0.7, 0.70, 0.16, 12.0, 0.080, 0.0, 78, 22, run=True, y_off=0.10)


SW_PLANE_X = -0.035
SWING_KEYS = [  # t, grip (forward, up), head (forward, up)
    (0.00, (0.30, 1.12), (0.54, 1.48), {}),
    (0.20, (0.24, 1.24), (0.22, 1.67), {}),
    (0.40, (0.06, 1.56), (-0.27, 1.75), {}),
    (0.48, (0.07, 1.57), (-0.26, 1.78), {"ease": lambda u: u ** 1.5}),
    (0.56, (0.24, 1.40), (0.37, 1.80), {}),
    (0.62, (0.31, 1.10), (0.62, 1.32), {"brk": True}),
    (0.68, (0.30, 1.13), (0.59, 1.38), {}),
    (0.86, (0.29, 1.13), (0.53, 1.47), {}),
    (1.10, (0.30, 1.12), (0.54, 1.48), {}),
]
SW_G = ck.Track([(k[0], V((SW_PLANE_X, -k[1][0], k[1][1])), k[3]) for k in SWING_KEYS])
SW_H = ck.Track([(k[0], V((SW_PLANE_X + 0.01, -k[2][0], k[2][1])), k[3]) for k in SWING_KEYS])
LEFT_PICK = ck.T(0, 0, -0.245)


def c_swing(t):
    ps = Pose()
    gp, hp = SW_G.at(t), SW_H.at(t)
    hd = (hp - gp).normalized()
    pick = Quaternion(V((1, 0, 0)), math.radians(90)) @ hd  # perpendicular in the swing plane, forward side
    T = tool_frame(gp, hp, pick)
    R, L = tool_hands(T, LEFT_PICK)
    wind = smoothstep(0.08, 0.40, t) * (1 - smoothstep(0.50, 0.60, t))
    hit = smoothstep(0.52, 0.62, t) * (1 - smoothstep(0.72, 1.05, t))
    ps.hips = V((0.0, 0.01 * wind, -0.045 - 0.040 * hit))
    ps.rot["hips"] = (6 * hit, -8 * wind + 4 * hit, 0)
    ps.rot["spine"] = (4 + 9 * hit - 5 * wind, -10 * wind + 6 * hit, 0)
    ps.rot["chest"] = (2 + 9 * hit - 4 * wind, -12 * wind + 8 * hit, 0)
    ps.rot["neck"] = (-4 * hit + 3 * wind, 6 * wind - 4 * hit, 0)
    ps.rot["head"] = (6 * hit - 6 * wind, 4 * wind - 4 * hit, 0)
    ps.rot["shoulder.R"] = (0, 0, -6 * wind)
    stand(ps, 0.35, 10.0, -0.16, 0.13)
    ps.leg["R"] = (lambda an_fm: (an_fm[0], an_fm[1], 0.0))(foot_place("R", 0.13, 0, 0, 28, -0.16))
    ps.arm["R"] = ("ik", R, R.translation + V((-0.5, 0.35, -0.3)))
    ps.arm["L"] = ("ik", L, L.translation + V((0.5, 0.35, -0.4)))
    ps.fing = {"L": GRIP, "R": GRIP}
    return ps


JH_LEFT = None


def c_drill(t):
    global JH_LEFT
    ps = Pose()
    w = TAU / 0.6
    jit = V((0.0035 * math.sin(w * 6 * t + 0.4) + 0.002 * math.sin(w * 3 * t),
             0.004 * math.sin(w * 6 * t + 1.7) - 0.005 * (0.5 + 0.5 * math.sin(w * 6 * t)),
             0.0045 * math.sin(w * 6 * t + 2.3) + 0.002 * math.sin(w * t)))
    pos = V((0.02, -0.33, 1.00)) + jit
    fwd = V((0.0, -1.0, -0.06)) + V((0.01 * math.sin(w * 3 * t), 0, 0.012 * math.sin(w * 6 * t + 0.5)))
    Td = ck.frame(pos, fwd, (0, 0, 1))
    Tp = Td @ JH_G
    if JH_LEFT is None:
        GL = ck.zframe(V((-0.15, 0, 0)), V((1, 0, 0)), V((0, -1, 0)))
        JH_LEFT = JH_G.inverted() @ GL
    R, L = tool_hands(Tp, JH_LEFT, 0.020, 0.020)
    shake = math.sin(w * 6 * t)
    ps.hips = V((0.0, 0.03, -0.075 + 0.003 * shake))
    ps.rot["hips"] = (8, 0, 0)
    ps.rot["spine"] = (9 + 0.6 * shake, 0, 0)
    ps.rot["chest"] = (6 + 0.8 * math.sin(w * 6 * t + 0.7), 0, 0)
    ps.rot["neck"] = (-6, 0, 0)
    ps.rot["head"] = (6 + 1.0 * math.sin(w * 6 * t + 1.2), 0, 0)
    stand(ps, 0.45, 12.0, -0.17, 0.16)
    ps.arm["R"] = ("ik", R, R.translation + V((-0.5, 0.3, -0.4)))
    ps.arm["L"] = ("ik", L, L.translation + V((0.5, 0.3, -0.4)))
    ps.fing = {"L": GRIP, "R": GRIP}
    return ps


def c_push(t):
    ps = walk_cycle(t, 1.2, 0.54, 0.075, 14.0, 0.050, 0.0, 14, 0)
    bob = ps.hips.z
    for s in SIDES:
        sg = 1 if s == "L" else -1
        pos = V((0.262 * sg, -0.27, 0.865 + bob * 0.7))
        G = ck.zframe(pos, V((0, -1, 0)), V((0, 0, 1)))
        Hm = G @ Hgrip(s, 0.017).inverted()
        ps.arm[s] = ("ik", Hm, Hm.translation + V((0.45 * sg, 0.4, -0.2)))
    ps.rot["neck"] = (-8, 0, 0)
    ps.rot["head"] = (-4, 0, 0)
    ps.fing = {"L": GRIP, "R": GRIP}
    return ps


def c_sit(t):
    ps = Pose()
    w = TAU * t / 4.0
    ps.hips = V((0.0, 0.40, -0.395))
    ps.rot["hips"] = (-6, 0, 0)
    ps.rot["spine"] = (10 + 1.0 * math.sin(w), 0, 0)
    ps.rot["chest"] = (6 + 1.2 * math.sin(w + 0.5), 0, 0)
    ps.rot["neck"] = (-2, 3 * math.sin(w), 0)
    ps.rot["head"] = (7 + 1.5 * math.sin(2 * w), 2 * math.sin(w + 1), 0)
    for s in SIDES:
        an, FM = foot_place(s, -0.035, 0.0, 0.0, 6.0, rig.head(f"foot.{s}").x * 1.15)
        ps.leg[s] = (an, FM, 0.0)
    for s in SIDES:
        sg = 1 if s == "L" else -1
        k = 1 if s == "L" else -1
        tap = V((0.008 * math.sin(TAU * t * 1.5 + k), 0.006 * math.sin(TAU * t + 0.7 * k), 0.006 * max(0.0, math.sin(TAU * t * 3.0 + 1.3 * k))))
        wrist = V((0.165 * sg, 0.030, 0.790)) + tap
        Hm = ck.frame(wrist, V((-0.15 * sg, -1.0, -0.10)), V((0.15 * sg, -0.05, 1.0)))
        ps.arm[s] = ("ik", Hm, wrist + V((0.45 * sg, 0.45, -0.25)))
        ps.fing[s] = {"fingers": 28 + 10 * max(0.0, math.sin(TAU * t * 3.0 + 1.3 * k)),
                      "tips": 30 + 8 * max(0.0, math.sin(TAU * t * 3.0 + 1.3 * k + 0.5)), "thumb": (-6, 0, -8)}
    return ps


def c_operate(t):
    ps = Pose()
    w = TAU * t / 3.0
    ps.hips = V((0.008 * math.sin(w), -0.01, -0.018))
    ps.rot["hips"] = (3, 0, 1.0 * math.sin(w))
    ps.rot["spine"] = (5, 2 * math.sin(w), 0)
    ps.rot["chest"] = (4, 2 * math.sin(w + 0.4), 0)
    ps.rot["neck"] = (6, 0, 0)
    ps.rot["head"] = (10 + 2 * math.sin(2 * w), 6 * math.sin(w + 0.8), 0)
    stand(ps, 0.18, 9.0, -0.04, 0.03)
    throws = {"R": [(0.3, 0.75), (1.6, 2.05)], "L": [(0.9, 1.35), (2.3, 2.75)]}
    for s in SIDES:
        sg = 1 if s == "L" else -1
        d = 0.0
        for a, b in throws[s]:
            u = clamp((t - a) / (b - a))
            d += math.sin(math.pi * u) * (1 if s == "R" else -1)
        pos = V((0.135 * sg, -0.40 - 0.065 * d, 0.995 + 0.015 * abs(d)))
        G = ck.zframe(pos, V((0, -0.25 * d, 1)), V((0, 1, 0)))
        Hm = G @ Hgrip(s, 0.016).inverted()
        ps.arm[s] = ("ik", Hm, Hm.translation + V((0.45 * sg, 0.35, -0.3)))
    ps.fing = {"L": GRIP, "R": GRIP}
    return ps


def c_wave(t):
    ps = c_idle(0.0)
    up = ck.ease_io(clamp(t / 0.45), 2.2) * (1 - ck.ease_io(clamp((t - 1.55) / 0.45), 2.0))
    wv = math.sin(TAU * clamp((t - 0.40) / 1.2) * 3.0) * smoothstep(0.35, 0.55, t) * (1 - smoothstep(1.45, 1.6, t))
    hang = V((-0.13, 0.0, -1.0)).normalized()
    raised = V((-0.72, -0.12, 0.68)).normalized()
    ud = hang.lerp(raised, up).normalized()
    bend = Quaternion(ud, math.radians(28 * wv)) @ V((0, -0.2, 1.0))
    ps.arm["R"] = ("fk", ud, lerp(15, 82, up), bend.normalized(), V((-0.5, 0.75, 0.2)).lerp(V((0.0, 1.0, 0.0)), up),
                   (0, 0, 0))
    ps.rot["head"] = (-2 * up, -10 * up, 4 * up)
    ps.rot["chest"] = (-1, -4 * up, 3 * up)
    ps.fing["R"] = {k: (REL[k] if k != "thumb" else REL[k]) for k in REL} if up < 0.3 else OPEN
    return ps


CLIPS = [  # name, seconds, key step (frames), pose fn
    ("Idle", 4.0, 2, c_idle), ("Walk", 1.1, 1, c_walk), ("Run", 0.7, 1, c_run), ("Swing", 1.1, 1, c_swing),
    ("Drill", 0.6, 1, c_drill), ("Push", 1.2, 1, c_push), ("Sit", 4.0, 2, c_sit), ("Operate", 3.0, 2, c_operate),
    ("Wave", 2.0, 1, c_wave),
]
warn = {}
for name, dur, step, fn in CLIPS:
    n = int(round(dur * FPS))
    frames = sorted(set(list(range(0, n + 1, step)) + [n]))
    cw = ck.ClipWriter(rig, name)
    for f in frames:
        P, ok = solve(fn(f / FPS))
        if not ok:
            warn.setdefault(name, []).append(f)
        cw.add(f, rig.basis(P))
    if FAILS:
        log(name, "clamped limbs:", sorted(FAILS))
        FAILS.clear()
    cw.finish(loc_bones=("hips",))
log("clips", [c[0] for c in CLIPS], "IK clamps:", {k: v for k, v in warn.items()})
ck.rest_pose(rig)

# ====================================================================== export
empties = [grip_r, lamp]
ck.export_glb(OUT, [arm, miner] + empties + props)
bk.save(os.path.join(HERE, "miner.blend"))
log("exported", OUT)
if MODE == "none":
    sys.exit(0)

# ====================================================================== previews
for p in props:
    p.hide_render = True
ck.eevee((900, 1200), samples=32)
ck.world("#3a3f47", 1.0)
ck.light("key", "SUN", 3.4, (0, 0, 5), rot=(50, 0, -35))
ck.light("rim", "AREA", 120, (1.5, 2.2, 2.4), target=(0, 0, 1.0), size=2.0, color="#ffd7a8")
ck.light("fill", "AREA", 60, (-2.0, -1.5, 1.4), target=(0, 0, 1.0), size=2.5, color="#cfdcff")
gnd = bpy.data.objects.new("ground", bpy.data.meshes.new("ground"))
bpy.context.scene.collection.objects.link(gnd)
gnd.data.from_pydata([(-6, -6, 0), (6, -6, 0), (6, 6, 0), (-6, 6, 0)], [], [(0, 1, 2, 3)])
gnd.data.materials.append(bk.mat("prev_ground", "#5b5850", rough=0.9))


def cam_at(az, el=8.0, dist=3.6, tz=0.92, lens=55):
    a, e = math.radians(az), math.radians(el)
    loc = V((dist * math.cos(e) * math.sin(a), -dist * math.cos(e) * math.cos(a), tz + dist * math.sin(e)))
    ck.camera("cam", loc, target=(0, 0, tz), lens=lens)


def attach(prop_name):
    for p in props:
        p.hide_render = p.name != prop_name
        if p.name == prop_name:
            p.parent = grip_r
            p.matrix_parent_inverse = Matrix.Identity(4)
            p.matrix_basis = Matrix.Identity(4)


def shot(tag, clip=None, frame_no=0, az=30, el=8, prop=None, dist=3.6, tz=0.92):
    attach(prop)
    if clip:
        ck.play(rig, clip, frame_no)
    else:
        ck.rest_pose(rig)
    cam_at(az, el, dist, tz)
    ck.render(os.path.join(PREV, f"miner_{tag}.png"))


shot("rest_front", az=0)
shot("rest_side", az=90)
shot("rest_back", az=180)
ck.eevee((1000, 1000), samples=32)
shot("face", az=28, el=-4, dist=0.75, tz=1.64)
shot("face_front", az=0, el=-3, dist=0.75, tz=1.64)
ck.eevee((900, 1200), samples=32)
if MODE == "full":
    shot("Idle_0", "Idle", 0, 35)
    shot("Walk_0", "Walk", 0, 70)
    shot("Walk_8", "Walk", 8, 70)
    shot("Run_5", "Run", 5, 70)
    shot("Swing_top", "Swing", 12, 60, prop="held_pickaxe")
    shot("Swing_impact", "Swing", 19, 70, prop="held_pickaxe")
    shot("Drill_0", "Drill", 0, 50, prop="held_jackhammer")
    shot("Push_0", "Push", 0, 60)
    shot("Sit_0", "Sit", 0, 60)
    shot("Operate_12", "Operate", 12, 35)
    shot("Wave_30", "Wave", 30, 20)
log("done")
