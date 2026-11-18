"""glove: a gloved work hand + its finger rig + a finger-wrap grip solver (shared by viewmodel.py and miner.py).

Canonical RIGHT hand = the hand bone's local space: origin at the wrist joint, +Y distal (towards the
fingers), +Z dorsal (back of the hand), +X ulnar (pinky side), so the thumb sits at -X. The LEFT hand is the
mirror image (x -> -x); its bone frames are mirrored with ck.mirror_x_matrix so they stay right-handed.
For every finger bone (both hands): local Y runs along the finger, local Z is dorsal, and flexion (curling
towards the palm) is a NEGATIVE rotation about local X.

The mesh is built from parts (palm loft, four finger tubes, thumb tube, cuff, knuckle bumps) whose bone
weights are decided while building them; ck.remesh_transfer voxel-unions the parts into one clean surface
and carries those weights and the leather / fabric zones over.
"""
import math

from mathutils import Matrix, Vector

import ck
from ck import V, smoothstep

FINGERS = ("index", "middle", "ring", "pinky")
# MCP joint (x, y, z), splay (deg, + towards the pinky), phalanx lengths, base radius (thickness, width)
FDEF = {
    "index": ((-0.0272, 0.0905, 0.0035), -5.0, (0.0466, 0.0276, 0.0217), (0.0092, 0.0099)),
    "middle": ((-0.0086, 0.0940, 0.0045), -0.5, (0.0504, 0.0313, 0.0228), (0.0095, 0.0102)),
    "ring": ((0.0102, 0.0905, 0.0035), 4.5, (0.0472, 0.0302, 0.0217), (0.0090, 0.0097)),
    "pinky": ((0.0275, 0.0815, 0.0005), 10.5, (0.0376, 0.0228, 0.0196), (0.0080, 0.0086)),
}
REST_FLEX = (6.0, 10.0, 7.0)
# thumb: CMC position, three (direction, dorsal hint) pairs, lengths, radii
THUMB = dict(
    base=(-0.0190, 0.0170, -0.0100),
    dirs=(((-0.60, 0.70, -0.38), (-0.45, -0.20, 0.87)),
          ((-0.42, 0.86, -0.30), (-0.55, -0.05, 0.83)),
          ((-0.30, 0.93, -0.20), (-0.55, 0.00, 0.83))),
    lens=(0.0400, 0.0330, 0.0250),
    radii=((0.0150, 0.0160), (0.0121, 0.0127), (0.0108, 0.0114)),
)
# palm rings along +Y: (y, half-thickness, half-width, centre x, centre z)
PALM = [(-0.010, 0.0194, 0.0288, 0.0005, -0.0010),
        (0.004, 0.0198, 0.0308, 0.0005, -0.0015),
        (0.022, 0.0193, 0.0343, 0.0008, -0.0020),
        (0.042, 0.0183, 0.0381, 0.0010, -0.0020),
        (0.060, 0.0171, 0.0407, 0.0012, -0.0016),
        (0.074, 0.0157, 0.0419, 0.0012, -0.0009),
        (0.084, 0.0136, 0.0408, 0.0010, 0.0000)]
# glove cuff rings along -Y: (y, half-thickness, half-width)
CUFF = [(0.006, 0.0212, 0.0318), (-0.012, 0.0236, 0.0335), (-0.032, 0.0262, 0.0356),
        (-0.052, 0.0285, 0.0372), (-0.070, 0.0298, 0.0382)]


def finger_frames(name, flex=REST_FLEX):
    """Rest frames (canonical right-hand space) of <finger>.01/.02/.03 + lengths."""
    head, splay, lens, _ = FDEF[name]
    F1 = ck.T(head) @ ck.rot("Z", -splay) @ ck.rot("X", -flex[0])
    F2 = F1 @ ck.T(0, lens[0], 0) @ ck.rot("X", -flex[1])
    F3 = F2 @ ck.T(0, lens[1], 0) @ ck.rot("X", -flex[2])
    return [F1, F2, F3], list(lens)


def thumb_frames():
    b = V(THUMB["base"])
    out = []
    p = b
    for (d, z), L in zip(THUMB["dirs"], THUMB["lens"]):
        M = ck.frame(p, d, z)
        out.append(M)
        p = M @ V((0, L, 0))
    return out, list(THUMB["lens"])


def bone_defs(side="R"):
    """[(name, parent, rest frame in canonical space of THIS side, length)] for the finger bones."""
    out = []
    S = (lambda m: m) if side == "R" else ck.mirror_x_matrix
    for f in FINGERS:
        frs, lens = finger_frames(f)
        par = f"hand.{side}"
        for j in range(3):
            n = f"{f}.0{j + 1}.{side}"
            out.append((n, par, S(frs[j]), lens[j]))
            par = n
    frs, lens = thumb_frames()
    par = f"hand.{side}"
    for j in range(3):
        n = f"thumb.0{j + 1}.{side}"
        out.append((n, par, S(frs[j]), lens[j]))
        par = n
    return out


def _chain_w(s, joints, bones, widths):
    """Sequential smooth blends between bones at joint arc-lengths."""
    t = [smoothstep(j - w, j + w, s) for j, w in zip(joints, widths)]
    w = {bones[0]: 1 - t[0]}
    for i in range(1, len(bones)):
        nxt = t[i] if i < len(t) else 0.0
        w[bones[i]] = w.get(bones[i], 0.0) + t[i - 1] * (1 - nxt)
    return w


def build(side="R", detail=1.0, palm_leather=True):
    """MeshData (canonical space of `side`) with weights on '<bone>.<side>' names + materials
    'leather' / 'fabric_glove'. detail scales ring density."""
    md = ck.MeshData()
    R = "R"
    hand, fore = f"hand.{R}", f"forearm.{R}"
    nf = max(8, int(round(14 * detail)))

    def palmar(a):  # ring angle (0 = dorsal, pi = palmar)
        return math.cos(a) < -0.18

    # ---------------------------------------------------------- palm
    def palm_w(p):
        tw = smoothstep(-0.018, 0.008, p.y)
        raw = {fore: 1 - tw}
        kmax = 0.0
        for f in FINGERS:
            head = V(FDEF[f][0])
            px = math.exp(-((p.x - head.x) / 0.0105) ** 2)
            k = smoothstep(head.y - 0.016, head.y + 0.003, p.y) * px
            if k > 1e-4:
                raw[f"{f}.01.{R}"] = tw * k
                kmax = max(kmax, k)
        tf, _ = thumb_frames()
        a, b = tf[0].translation, tf[0] @ V((0, THUMB["lens"][0], 0))
        ab = b - a
        tt = ck.clamp((p - a).dot(ab) / ab.length_squared)
        d = (a + ab * tt - p).length
        th = math.exp(-(d / 0.0125) ** 2) * 0.55 * smoothstep(0.0, -0.006, p.z + 0.004)
        if th > 1e-4:
            raw[f"thumb.01.{R}"] = tw * th
        raw[hand] = tw * max(0.0, 1 - kmax - th)
        tot = sum(raw.values())
        return {k: x / tot for k, x in raw.items() if x / tot > 1e-4}

    path = [V((cx, y, cz)) for (y, _, _, cx, cz) in PALM]
    radii = [(t, w) for (_, t, w, _, _) in PALM]
    # densify the palm path
    pts, rr = [], []
    for i in range(len(path) - 1):
        for k in range(3):
            u = k / 3
            pts.append(path[i].lerp(path[i + 1], u))
            rr.append((ck.lerp(radii[i][0], radii[i + 1][0], u), ck.lerp(radii[i][1], radii[i + 1][1], u)))
    pts.append(path[-1])
    rr.append(radii[-1])
    npalm = max(16, int(round(28 * detail)))

    def palm_shape(i, a, x, y):
        # x along N (dorsal +Z), y along B (+X): arch the back, flatten the palm side a little
        if x > 0:
            x += 0.0028 * (1 - min(1.0, (y / max(rr[i][1], 1e-6)) ** 2))
        else:
            x *= 0.92
        return x, y

    start = len(md.verts)
    md.scalar = -1.0
    rows, fr, sl = ck.tube(md, pts, lambda i, s: rr[i], npalm, "fabric_glove", up=(0, 0, 1), p=2.6,
                           part=1, cap0="flat", cap1=("dome", 3, 0.010), rfn=palm_shape,
                           matfn=lambda i, k: ("leather" if palm_leather and palmar(k / npalm * ck.TAU) else "fabric_glove"))
    for vi in range(start, len(md.verts)):
        md.vw[vi] = palm_w(md.verts[vi])
        p_ = md.verts[vi]
        # leather on the palm side: score > 0 below the palm's mid-plane
        md.vs[vi] = (-(p_.z + 0.0012) / 0.012 - 0.15) if palm_leather else -1.0
    # palm end cap faces default material: make dome palmar faces leather too
    # knuckle bumps (metacarpal heads under the glove)
    for f in FINGERS:
        head = V(FDEF[f][0]) + V((0, -0.002, 0.0055))
        r = FDEF[f][3][1] * 0.82
        md.scalar = -1.0
        sphere(md, head, (r, r * 0.9, r * 0.75), 10, 7, "fabric_glove", {hand: 1.0}, part=5)

    # ---------------------------------------------------------- fingers
    for f in FINGERS:
        frs, lens = finger_frames(f)
        rt, rw = FDEF[f][3]
        total = sum(lens)
        J = [0.0, lens[0], lens[0] + lens[1]]
        steps = []
        s = -0.013
        while s < total - 1e-6:
            steps.append(s)
            # denser near joints
            near = min(abs(s - j) for j in J)
            s += 0.0035 if near < 0.006 else 0.0062
        steps.append(total)
        P = []
        for s in steps:
            if s <= lens[0]:
                M, u = frs[0], s
            elif s <= lens[0] + lens[1]:
                M, u = frs[1], s - lens[0]
            else:
                M, u = frs[2], s - lens[0] - lens[1]
            P.append(M @ V((0, u, 0)))
        bones = [hand, f"{f}.01.{R}", f"{f}.02.{R}", f"{f}.03.{R}"]

        def frad(i, s, rt=rt, rw=rw, J=J, total=total, steps=steps):
            s = steps[i]
            k = 1 - 0.17 * ck.clamp(s / total)
            crease = 1 - 0.045 * sum(math.exp(-((s - j) / 0.0022) ** 2) for j in J[1:])
            pad = 1 + 0.04 * sum(math.exp(-((s - (a + b) / 2) / 0.008) ** 2) for a, b in ((J[0], J[1]), (J[1], J[2])))
            base = 1 + 0.10 * smoothstep(0.004, -0.012, s)  # flare into the palm
            return rt * k * crease * pad * base, rw * k * crease * base

        def fw(i, s, steps=steps, J=J, bones=bones):
            return _chain_w(steps[i], J, bones, (0.0075, 0.0042, 0.0036))

        def fmat(i, k, steps=steps, total=total):
            a = k / nf * ck.TAU
            if steps[i] > total - 0.011:
                return "leather"
            return "leather" if palmar(a) else "fabric_glove"

        up = frs[0].to_3x3() @ V((0, 0, 1))
        f0 = len(md.verts)
        _, ffr, _ = ck.tube(md, P, frad, nf, "fabric_glove", up=up, p=2.2, weights=fw, part=2, cap0="flat",
                            cap1=("dome", 3, rt * 0.95), matfn=fmat)
        # leather score: palmar half of each ring (relative to the local dorsal axis) + the fingertip
        for vi in range(f0, len(md.verts)):
            q = md.verts[vi]
            best, bi = 1e9, 0
            for k, pp in enumerate(P):
                dd = (pp - q).length_squared
                if dd < best:
                    best, bi = dd, k
            t_, n_, b_ = ffr[bi]
            rad = q - P[bi]
            rad = rad - t_ * t_.dot(rad)
            dors = rad.normalized().dot(n_) if rad.length > 1e-7 else 0.0
            tip = (steps[bi] - (total - 0.0115)) / 0.003 if bi < len(steps) else 1.0
            if bi == len(P) - 1:
                tip = max(tip, 1.0)
            md.vs[vi] = max(-dors - 0.18, tip)

    # ---------------------------------------------------------- thumb
    tfr, tl = thumb_frames()
    total = sum(tl)
    J = [0.0, tl[0], tl[0] + tl[1]]
    steps = []
    s = -0.012
    while s < total - 1e-6:
        steps.append(s)
        near = min(abs(s - j) for j in J)
        s += 0.0035 if near < 0.006 else 0.006
    steps.append(total)
    P = []
    for s in steps:
        if s <= tl[0]:
            M, u = tfr[0], s
        elif s <= tl[0] + tl[1]:
            M, u = tfr[1], s - tl[0]
        else:
            M, u = tfr[2], s - tl[0] - tl[1]
        P.append(M @ V((0, u, 0)))
    tb = [hand, f"thumb.01.{R}", f"thumb.02.{R}", f"thumb.03.{R}"]
    TR = THUMB["radii"]

    def trad(i, s):
        s = steps[i]
        if s < tl[0]:
            u = ck.clamp(s / tl[0])
            r = (ck.lerp(TR[0][0], TR[1][0], u ** 1.5), ck.lerp(TR[0][1], TR[1][1], u ** 1.5))
        elif s < tl[0] + tl[1]:
            u = (s - tl[0]) / tl[1]
            r = (ck.lerp(TR[1][0], TR[2][0], u), ck.lerp(TR[1][1], TR[2][1], u))
        else:
            u = (s - tl[0] - tl[1]) / tl[2]
            r = (TR[2][0] * (1 - 0.1 * u), TR[2][1] * (1 - 0.1 * u))
        crease = 1 - 0.04 * sum(math.exp(-((s - j) / 0.0024) ** 2) for j in J[1:])
        return r[0] * crease, r[1] * crease

    md.scalar = 1.0
    ck.tube(md, P, trad, nf, "leather", up=tfr[0].to_3x3() @ V((0, 0, 1)), p=2.2,
            weights=lambda i, s: _chain_w(steps[i], J, tb, (0.010, 0.006, 0.0042)), part=3,
            cap0="flat", cap1=("dome", 3, TR[2][0] * 0.95))

    # ---------------------------------------------------------- cuff
    md.scalar = -1.0
    cp = [V((0.0006, y, -0.0012)) for (y, _, _) in CUFF]
    crr = [(t, w) for (_, t, w) in CUFF]
    ck.tube(md, cp, lambda i, s: crr[i], npalm, "fabric_glove", up=(0, 0, 1), p=2.3, part=4, cap0="flat", cap1="flat",
            weights=lambda i, s: (lambda tw: {fore: 1 - tw, hand: tw})(smoothstep(-0.024, 0.004, cp[i].y)))
    if side == "L":
        mirror(md)
    return md


def sphere(md, c, r, segs, rings, mat, w, part=0):
    rx, ry, rz = r if isinstance(r, (tuple, list)) else (r, r, r)
    c = V(c)
    top = md.v(c + V((0, 0, rz)), dict(w))
    rowsl = []
    for i in range(1, rings):
        ph = math.pi * i / rings
        row = []
        for k in range(segs):
            th = ck.TAU * k / segs
            row.append(md.v(c + V((rx * math.sin(ph) * math.cos(th), ry * math.sin(ph) * math.sin(th), rz * math.cos(ph))), dict(w)))
        rowsl.append(row)
    bot = md.v(c + V((0, 0, -rz)), dict(w))
    for k in range(segs):
        k1 = (k + 1) % segs
        md.f((top, rowsl[0][k], rowsl[0][k1]), mat, None, part)
        md.f((bot, rowsl[-1][k1], rowsl[-1][k]), mat, None, part)
    for i in range(len(rowsl) - 1):
        a, b = rowsl[i], rowsl[i + 1]
        for k in range(segs):
            k1 = (k + 1) % segs
            md.f((a[k], b[k], b[k1], a[k1]), mat, None, part)


def mirror(md):
    """Right-hand MeshData -> left hand (mirror x, rename .R -> .L)."""
    md.transform(Matrix.Diagonal((-1, 1, 1, 1)))
    md.vw = [({k[:-2] + ".L" if k.endswith(".R") else k: x for k, x in w.items()} if w else w) for w in md.vw]
    return md


# ====================================================================== poses + grip solver

def chain_names(side):
    out = {f: [f"{f}.0{j + 1}.{side}" for j in range(3)] for f in FINGERS}
    out["thumb"] = [f"thumb.0{j + 1}.{side}" for j in range(3)]
    return out


def preset(kind, side="R"):
    """Named finger poses -> {bone: 4x4 local rotation relative to rest}."""
    out = {}
    names = chain_names(side)
    if kind == "relaxed":
        curls = {"index": (-14, -22, -12), "middle": (-18, -28, -14), "ring": (-22, -32, -16), "pinky": (-26, -36, -18)}
        th = ((0, 0, -4), (-8, 0, 0), (-10, 0, 0))
    elif kind == "open":
        curls = {f: (6, 4, 2) for f in FINGERS}
        th = ((6, 0, 8), (4, 0, 0), (2, 0, 0))
    elif kind == "reach":  # fingers spread, slightly cupped, ready to grab
        curls = {"index": (-4, -8, -6), "middle": (-6, -10, -6), "ring": (-8, -12, -8), "pinky": (-10, -14, -8)}
        th = ((10, 0, 10), (-4, 0, 0), (-6, 0, 0))
    elif kind == "fist":
        curls = {f: (-80, -100, -60) for f in FINGERS}
        th = ((-10, 0, -30), (-30, 0, 0), (-40, 0, 0))
    elif kind == "press":  # index pointing, others curled
        curls = {"index": (0, -6, -4), "middle": (-60, -90, -50), "ring": (-70, -95, -55), "pinky": (-75, -95, -55)}
        th = ((-6, 0, -18), (-25, 0, 0), (-25, 0, 0))
    else:
        raise ValueError(kind)
    spread = {"index": -3.0, "middle": 0.0, "ring": 3.0, "pinky": 6.0} if kind in ("open", "reach") else {}
    for f in FINGERS:
        for j in range(3):
            rz = (-spread.get(f, 0.0) if side == "R" else spread.get(f, 0.0)) if j == 0 else 0.0
            out[names[f][j]] = local_rot((curls[f][j], 0.0, rz))
    for j in range(3):
        out[names["thumb"][j]] = local_rot(th[j])
    return out


def blend(a, b, t):
    """Slerp two finger poses ({bone: 4x4 local rotation})."""
    out = {}
    for k in set(a) | set(b):
        qa = (a.get(k) or Matrix.Identity(4)).to_quaternion()
        qb = (b.get(k) or Matrix.Identity(4)).to_quaternion()
        out[k] = qa.slerp(qb, t).to_matrix().to_4x4()
    return out


def squeeze(pose, deg, side="R"):
    """Extra flexion on every finger joint (impact grip tighten)."""
    out = dict(pose)
    for f in FINGERS:
        for j in range(3):
            n = f"{f}.0{j + 1}.{side}"
            out[n] = (out.get(n) or Matrix.Identity(4)) @ ck.rot("X", -deg)
    return out


def local_rot(deg):
    rx, ry, rz = deg
    return (ck.rot("X", rx) @ ck.rot("Y", ry) @ ck.rot("Z", rz))


def _seg_line_dist(a, b, c, d, n=7):
    best = 1e9
    for i in range(n):
        p = a.lerp(b, i / (n - 1))
        v = p - c
        best = min(best, (v - d * v.dot(d)).length)
    return best


def wrap(side, handle_c, handle_d, handle_r, pen=0.0012, thumb_pre=((-6, 0, -26),), limits=(95, 105, 75),
         spread=None, skip=(), natural=0.55, thumb_target_r=None):
    """Curl each finger around a cylinder (canonical space of `side`): axis point c, direction d, radius r.
    Returns {bone: 4x4 local rotation}. Joint by joint: flex until that phalanx touches the handle."""
    c, d = V(handle_c), V(handle_d).normalized()
    defs = {n: (M, L) for n, _, M, L in bone_defs(side)}
    names = chain_names(side)
    out = {}
    for f in FINGERS + ("thumb",):
        if f in skip:
            continue
        chain = names[f]
        rt = (FDEF[f][3][0] if f != "thumb" else THUMB["radii"][1][0]) * 0.95
        angles = []
        base = Matrix.Identity(4)
        pre = [(0, 0, 0)] * 3
        if f == "thumb":
            pre = list(thumb_pre) + [(0, 0, 0)] * (3 - len(thumb_pre))
        if spread and f in spread:
            pre[0] = (pre[0][0], pre[0][1], pre[0][2] + spread[f])
        P_parent = base
        for j in range(3):
            M_rest, L = defs[chain[j]]
            local_rest = M_rest if j == 0 else defs[chain[j - 1]][0].inverted() @ M_rest
            lim = limits[j] if f != "thumb" else (35, 70, 70)[j]
            start_j = 1 if f == "thumb" else 0
            r_here = rt * (1 - 0.08 * j)

            def pose_at(th, j=j, local_rest=local_rest, P_parent=P_parent):
                lr = local_rot(pre[j]) @ ck.rot("X", th)
                return P_parent @ local_rest @ lr

            def gap(th, L=L, r_here=r_here):
                M = pose_at(th)
                a, b = M.translation, M @ V((0, L, 0))
                return _seg_line_dist(a, b, c, d) - (handle_r + r_here)

            if j < start_j:
                th = 0.0
            elif gap(0.0) <= -pen:
                th = 0.0
            elif gap(-lim) > -pen:
                th = -lim * natural
            else:
                lo, hi = 0.0, -lim
                for _ in range(24):
                    mid = (lo + hi) / 2
                    if gap(mid) <= -pen:
                        hi = mid
                    else:
                        lo = mid
                th = hi
            M = pose_at(th)
            P_parent = M
            out[chain[j]] = local_rot(pre[j]) @ ck.rot("X", th)
    return out


def hand_points(side, pose):
    """Canonical-space joint positions for a finger pose (debug / contact checks)."""
    defs = {n: (M, L, p) for n, p, M, L in bone_defs(side)}
    P = {f"hand.{side}": Matrix.Identity(4)}
    pts = {}
    for n, p, M, L in bone_defs(side):
        par = P[p]
        local_rest = M if p == f"hand.{side}" else defs[p][0].inverted() @ M
        P[n] = par @ local_rest @ pose.get(n, Matrix.Identity(4))
        pts[n] = (P[n].translation.copy(), P[n] @ V((0, L, 0)))
    return pts


def _gap(a, b, c, d, rr):
    return _seg_line_dist(a, b, c, d) - rr


def _thumb_wrap(side, pre, c, d, r, pen0=0.0012):
    """thumb.01 at local rotation `pre`, then .02/.03 flex until each touches the handle.
    Returns (poses, tip, penetration)."""
    defs = {n: (M, L) for n, _, M, L in bone_defs(side)}
    names = chain_names(side)["thumb"]
    M1, L1 = defs[names[0]]
    P1 = M1 @ pre
    poses = {names[0]: pre}
    pen = 0.0
    a, b = P1.translation, P1 @ V((0, L1, 0))
    pen += max(0.0, -_gap(a, b, c, d, r + THUMB["radii"][0][0] * 0.85))
    Pp = P1
    Mp = M1
    rads = (THUMB["radii"][1][0] * 0.95, THUMB["radii"][2][0] * 0.95)
    for j in (1, 2):
        Mj, Lj = defs[names[j]]
        lr = Mp.inverted() @ Mj
        rr = r + rads[j - 1]

        def gap(th, Pp=Pp, lr=lr, Lj=Lj, rr=rr):
            M = Pp @ lr @ ck.rot("X", th)
            return _gap(M.translation, M @ V((0, Lj, 0)), c, d, rr)

        lim = 80.0
        if gap(0.0) <= -pen0:
            th = 0.0
        elif gap(-lim) > -pen0:
            th = -lim * 0.6
        else:
            lo, hi = 0.0, -lim
            for _ in range(20):
                mid = (lo + hi) / 2
                if gap(mid) <= -pen0:
                    hi = mid
                else:
                    lo = mid
            th = hi
        M = Pp @ lr @ ck.rot("X", th)
        pen += max(0.0, -gap(th) - 0.003)
        poses[names[j]] = ck.rot("X", th)
        Pp, Mp = M, Mj
    tip = Pp @ V((0, defs[names[2]][1] + 0.008, 0))
    return poses, tip, pen


def thumb_solve(side, c, d, r, fingers):
    """Pick thumb.01's rotation so the thumb wraps the handle and its tip rests on the outside of the index
    finger's middle phalanx (a closed power grip). Returns {thumb bone: 4x4 local rotation}."""
    c, d = V(c), V(d).normalized()
    pts = hand_points(side, fingers)
    a, b = pts[f"index.02.{side}"]
    m = a.lerp(b, 0.45)
    out = (m - c) - d * d.dot(m - c)
    out.normalize()
    target = m + out * (FDEF["index"][3][0] + THUMB["radii"][2][0]) * 0.92
    best = None

    def cost(rx, ry, rz):
        poses, tip, pen = _thumb_wrap(side, local_rot((rx, ry, rz)), c, d, r)
        k = (tip - target).length + 6.0 * pen + 0.0008 * (abs(rx) + abs(ry) + abs(rz)) / 10.0
        return k, poses

    for rx in range(-50, 41, 10):
        for ry in range(-60, 31, 10):
            for rz in range(-70, 31, 10):
                k, poses = cost(rx, ry, rz)
                if best is None or k < best[0]:
                    best = (k, (rx, ry, rz), poses)
    for step in (5.0, 2.5):
        cx, cy, cz = best[1]
        for dx in (-step, 0, step):
            for dy in (-step, 0, step):
                for dz in (-step, 0, step):
                    k, poses = cost(cx + dx, cy + dy, cz + dz)
                    if k < best[0]:
                        best = (k, (cx + dx, cy + dy, cz + dz), poses)
    print(f"[glove] thumb {side}: rot {best[1]}, miss {best[0] * 1000:.1f} mm")
    return best[2]
