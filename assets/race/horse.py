"""GoldRush Downs racehorse + jockey  ->  public/models/race/horse.{glb,json}

    bl assets/race/horse.py -- public/models/race/horse [stage]

stage: shape | rig | full (default). Everything is built from code: the horse and the jockey are
signed-distance-field sculptures (anatomical masses blended with smooth-min), polygonised with surface
nets, projected back onto the field and decimated. Skin weights come from the same primitives
(each mass knows which bone chain it belongs to), the gaits are solved per frame (planar leg IK on the
stance phase, authored fold postures in swing, a steady jockey solved with two-bone IK).

Coordinates: Blender metres, Z up, the horse faces -Y (three.js +Z). Landmarks are written with
P(x, s, z): s = forward (= -Y), x = the horse's left (+X), z = up. Origin on the ground under the girth.
"""
import json
import math
import os
import sys
import time

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

import bk

V = Vector
T0 = time.time()
ARGS = bk.args()
OUT = os.path.abspath(ARGS[0] if ARGS else "public/models/race/horse")
STAGE = ARGS[1] if len(ARGS) > 1 else "full"
HERE = os.path.dirname(os.path.abspath(__file__))
PREV = os.path.join(HERE, "previews")


def log(*a):
    print(f"[horse {time.time() - T0:6.1f}s]", *a, flush=True)


def P(x, s, z):
    return np.array([x, -s, z], dtype=np.float64)


def unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


# ====================================================================== SDF primitives (numpy)

class Prim:
    """A signed-distance primitive. tag = surface region, w = bone weight spec (see weights())."""
    tag = "coat"
    w = None
    blend = 0.03  # weight-influence softness (m)

    def finish(self, lo, hi):
        self.lo, self.hi = np.asarray(lo, float), np.asarray(hi, float)
        return self


class Ell(Prim):
    """Ellipsoid: centre c, radii r along local axes (rows of A, orthonormal)."""

    def __init__(self, c, r, A=None):
        self.c = np.asarray(c, float)
        self.r = np.asarray(r, float)
        self.A = np.eye(3) if A is None else np.asarray(A, float)
        ext = np.sqrt(((self.A * self.r[:, None]) ** 2).sum(0))
        self.finish(self.c - ext, self.c + ext)

    def d(self, Q):
        q = (Q - self.c) @ self.A.T
        k0 = np.linalg.norm(q / self.r, axis=1)
        k1 = np.linalg.norm(q / self.r ** 2, axis=1)
        return k0 * (k0 - 1.0) / np.maximum(k1, 1e-9)


class RCone(Prim):
    """Round cone (capsule with different end radii). squash=(axis, f) flattens it along axis by f."""

    def __init__(self, a, b, ra, rb, squash=None):
        self.a, self.b = np.asarray(a, float), np.asarray(b, float)
        self.ra, self.rb = ra, rb
        self.sq = squash
        r = max(ra, rb)
        self.finish(np.minimum(self.a, self.b) - r, np.maximum(self.a, self.b) + r)

    def d(self, Q):
        f = 1.0
        if self.sq is not None:
            ax, f = unit(self.sq[0]), self.sq[1]
            Q = Q + np.outer(((Q - self.a) @ ax) * (1.0 / f - 1.0), ax)
        a, b, r1, r2 = self.a, self.b, self.ra, self.rb
        ba = b - a
        l2 = ba @ ba
        rr = r1 - r2
        a2 = l2 - rr * rr
        il2 = 1.0 / l2
        pa = Q - a
        y = pa @ ba
        z = y - l2
        xv = pa * l2 - np.outer(y, ba)
        x2 = (xv * xv).sum(1)
        y2 = y * y * l2
        z2 = z * z * l2
        k = np.sign(rr) * rr * rr * x2
        d1 = np.sqrt(x2 + z2) * il2 - r2
        d2 = np.sqrt(x2 + y2) * il2 - r1
        d3 = (np.sqrt(np.maximum(x2 * a2 * il2, 0)) + y * rr) * il2 - r1
        d = np.where(np.sign(z) * a2 * z2 > k, d1, np.where(np.sign(y) * a2 * y2 < k, d2, d3))
        return d * f


class Loft(Prim):
    """Superelliptic sections along a polyline of centres in the sagittal plane.
    nodes: [(centre, dorsal_unit, up, down, halfwidth)], lateral axis = X, offset xo (for paired parts)."""

    def __init__(self, nodes, p=2.0, xo=0.0):
        self.C = np.array([n[0] for n in nodes], float)
        self.N = np.array([unit(n[1]) for n in nodes], float)
        self.U = np.array([n[2] for n in nodes], float)
        self.D = np.array([n[3] for n in nodes], float)
        self.W = np.array([n[4] for n in nodes], float)
        self.p = p
        self.xo = xo
        pts = []
        for c, n, u, d, w in zip(self.C, self.N, self.U, self.D, self.W):
            for sx in (-1, 1):
                pts += [c + n * u + [sx * w, 0, 0], c - n * d + [sx * w, 0, 0]]
        pts = np.array(pts)
        self.finish(pts.min(0) - 0.01, pts.max(0) + 0.01)

    def d(self, Q):
        C = self.C
        A, B = C[:-1], C[1:]
        AB = B - A
        L2 = (AB * AB).sum(1)
        n = len(Q)
        best = np.full(n, np.inf)
        bj = np.zeros(n, int)
        bt = np.zeros(n)
        braw = np.zeros(n)
        for j in range(len(A)):
            traw = ((Q - A[j]) @ AB[j]) / L2[j]
            t = np.clip(traw, 0, 1)
            dist = np.linalg.norm(Q - (A[j] + np.outer(t, AB[j])), axis=1)
            m = dist < best
            best[m], bj[m], bt[m], braw[m] = dist[m], j, t[m], traw[m]
        lerp = lambda arr: arr[bj] + (arr[bj + 1] - arr[bj]) * bt  # noqa: E731
        c = A[bj] + AB[bj] * bt[:, None]
        nn = self.N[bj] + (self.N[bj + 1] - self.N[bj]) * bt[:, None]
        nn /= np.linalg.norm(nn, axis=1)[:, None]
        up, dn, w = lerp(self.U), lerp(self.D), lerp(self.W)
        rel = Q - c
        x = np.abs(rel[:, 0] - self.xo)
        v = (rel * nn).sum(1)
        D = np.where(v > 0, up, dn)
        p = self.p
        r = ((x / w) ** p + (np.abs(v) / D) ** p) ** (1.0 / p)
        d2 = (r - 1.0) * np.minimum(w, D)
        # past the ends: distance along the axis
        L = np.sqrt(L2)
        e = np.where((bj == 0) & (braw < 0), -braw * L[0], 0.0)
        e = np.where((bj == len(A) - 1) & (braw > 1), (braw - 1) * L[-1], e)
        return np.where(e > 0, np.sqrt(np.maximum(d2, 0) ** 2 + e * e), d2)


def smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b + (a - b) * h - k * h * (1.0 - h)


def smax(a, b, k):
    return -smin(-a, -b, k)


class Field:
    """Ordered smooth CSG over primitives: add(prim, k) unions, cut(prim, k) subtracts."""

    def __init__(self):
        self.ops = []

    def add(self, prim, k=0.03, tag=None, w=None, blend=None):
        if tag:
            prim.tag = tag
        if w is not None:
            prim.w = w
        if blend is not None:
            prim.blend = blend
        self.ops.append((prim, "u", k))
        return prim

    def cut(self, prim, k=0.01):
        self.ops.append((prim, "s", k))
        return prim

    def prims(self):
        return [p for p, m, k in self.ops if m == "u"]

    def at(self, Q):
        F = np.full(len(Q), 1.0)
        for prim, mode, k in self.ops:
            m = k + 0.004
            inb = np.all((Q >= prim.lo - m) & (Q <= prim.hi + m), axis=1)
            if not inb.any():
                continue
            d = prim.d(Q[inb])
            F[inb] = smin(F[inb], d, k) if mode == "u" else smax(F[inb], -d, k)
        return F

    def grid(self, lo, hi, h):
        axes = [np.arange(lo[i], hi[i] + h * 0.5, h) for i in range(3)]
        F = np.full([len(a) for a in axes], 1.0, np.float32)
        for prim, mode, k in self.ops:
            m = k + 2 * h
            sl = []
            for i in range(3):
                i0 = max(0, int(math.floor((prim.lo[i] - m - lo[i]) / h)))
                i1 = min(len(axes[i]), int(math.ceil((prim.hi[i] + m - lo[i]) / h)) + 1)
                sl.append(slice(i0, i1))
            if any(s.stop <= s.start for s in sl):
                continue
            X, Y, Z = np.meshgrid(axes[0][sl[0]], axes[1][sl[1]], axes[2][sl[2]], indexing="ij")
            Q = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1)
            d = prim.d(Q).reshape(X.shape)
            sub = F[sl[0], sl[1], sl[2]]
            F[sl[0], sl[1], sl[2]] = smin(sub, d, k) if mode == "u" else smax(sub, -d, k)
        return F, np.asarray(lo, float), h


def surface_nets(F, lo, h):
    """Naive surface nets: one vertex per sign-changing cell, one quad per sign-changing grid edge."""
    c = F < 0
    cs = [c[a:a + c.shape[0] - 1, b:b + c.shape[1] - 1, e:e + c.shape[2] - 1]
          for e in (0, 1) for b in (0, 1) for a in (0, 1)]
    anyin = np.zeros(cs[0].shape, bool)
    allin = np.ones(cs[0].shape, bool)
    for x in cs:
        anyin |= x
        allin &= x
    act = anyin & ~allin
    ci, cj, ck = np.nonzero(act)
    nv = len(ci)
    vid = np.full(act.shape, -1, np.int64)
    vid[ci, cj, ck] = np.arange(nv)
    offs = [(a, b, e) for e in (0, 1) for b in (0, 1) for a in (0, 1)]
    vals = np.stack([F[ci + a, cj + b, ck + e] for a, b, e in offs], 1).astype(np.float64)
    O = np.array(offs, float)
    edges = [(0, 1), (2, 3), (4, 5), (6, 7), (0, 2), (1, 3), (4, 6), (5, 7), (0, 4), (1, 5), (2, 6), (3, 7)]
    acc = np.zeros((nv, 3))
    cnt = np.zeros(nv)
    for a, b in edges:
        va, vb = vals[:, a], vals[:, b]
        m = (va < 0) != (vb < 0)
        t = va[m] / (va[m] - vb[m])
        acc[m] += O[a] + (O[b] - O[a]) * t[:, None]
        cnt[m] += 1
    pos = lo + (np.stack([ci, cj, ck], 1) + acc / cnt[:, None]) * h
    quads = []
    nx, ny, nz = F.shape
    for ax in range(3):
        b_ax, c_ax = (ax + 1) % 3, (ax + 2) % 3
        sl0 = [slice(None)] * 3
        sl1 = [slice(None)] * 3
        sl0[ax] = slice(0, F.shape[ax] - 1)
        sl1[ax] = slice(1, F.shape[ax])
        a0 = c[tuple(sl0)]
        a1 = c[tuple(sl1)]
        ch = a0 != a1
        idx = np.nonzero(ch)
        idx = [np.asarray(i) for i in idx]
        ok = (idx[b_ax] >= 1) & (idx[c_ax] >= 1) & (idx[b_ax] <= F.shape[b_ax] - 2) & (idx[c_ax] <= F.shape[c_ax] - 2)
        idx = [i[ok] for i in idx]
        inside_low = a0[tuple(idx)]

        def cell(db, dc):
            j = [i.copy() for i in idx]
            j[b_ax] = j[b_ax] - db
            j[c_ax] = j[c_ax] - dc
            return vid[tuple(j)]

        q = np.stack([cell(1, 1), cell(0, 1), cell(0, 0), cell(1, 0)], 1)
        q[~inside_low] = q[~inside_low][:, ::-1]
        quads.append(q)
    quads = np.concatenate(quads)
    quads = quads[(quads >= 0).all(1)]
    return pos, quads


def project(field, pos, steps=2, eps=0.0015):
    for _ in range(steps):
        f = field.at(pos)
        g = np.zeros_like(pos)
        for i in range(3):
            d = np.zeros(3)
            d[i] = eps
            g[:, i] = (field.at(pos + d) - field.at(pos - d)) / (2 * eps)
        gl2 = np.maximum((g * g).sum(1), 1e-6)
        step = (f / gl2)[:, None] * g
        nrm = np.linalg.norm(step, axis=1)
        step *= (np.minimum(nrm, 0.006) / np.maximum(nrm, 1e-12))[:, None]
        pos = pos - step
    return pos


def mesh_from(name, pos, faces):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(p) for p in pos], [], [tuple(int(i) for i in f) for f in faces])
    me.update()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    return o


def polygonise(field, name, lo, hi, h, target_tris):
    t = time.time()
    F, lo, h = field.grid(lo, hi, h)
    log(f"{name}: grid {F.shape} in {time.time() - t:.1f}s")
    pos, quads = surface_nets(F, lo, h)
    del F
    pos = project(field, pos)
    o = mesh_from(name, pos, quads)
    bk.select([o])
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=0.0005)
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    # keep the largest connected piece only (stray specks from tiny lobes)
    bm = bmesh.new()
    bm.from_mesh(o.data)
    seen, parts = set(), []
    for v in bm.verts:
        if v in seen:
            continue
        stack, comp = [v], []
        seen.add(v)
        while stack:
            x = stack.pop()
            comp.append(x)
            for e in x.link_edges:
                y = e.other_vert(x)
                if y not in seen:
                    seen.add(y)
                    stack.append(y)
        parts.append(comp)
    parts.sort(key=len, reverse=True)
    junk = [v for comp in parts[1:] if len(comp) < 0.02 * len(parts[0]) for v in comp]
    if junk:
        bmesh.ops.delete(bm, geom=junk, context="VERTS")
    bm.to_mesh(o.data)
    bm.free()
    n0 = len(o.data.polygons) * 2
    d = o.modifiers.new("dec", "DECIMATE")
    d.decimate_type = "COLLAPSE"
    d.ratio = min(1.0, target_tris / n0)
    d.use_collapse_triangulate = True
    bk.apply(o, transform=False)
    for p in o.data.polygons:
        p.use_smooth = True
    log(f"{name}: {n0} -> {bk.tris([o])} tris ({len(parts)} parts) in {time.time() - t:.1f}s")
    return o


# ====================================================================== horse anatomy (rest = square stance)

HEAD_PITCH = math.radians(56)          # head axis below horizontal
HEAD_O = P(0, 0.85, 1.87)              # atlanto-occipital joint (head bone head)
HA = np.array([0, -math.cos(HEAD_PITCH), -math.sin(HEAD_PITCH)])   # towards the muzzle
HN = np.array([0, -math.sin(HEAD_PITCH), math.cos(HEAD_PITCH)])    # dorsal (forehead side)
XL = np.array([1.0, 0, 0])


def hp(u, v, x=0.0):
    """Point in the head frame: u along the face towards the muzzle, v dorsal, x lateral."""
    return HEAD_O + HA * u + HN * v + XL * x


def leg_joints(side):
    """Rest joint centres for one side (+1 = left, -1 = right)."""
    sx = side
    return {
        "scap": P(0.10 * sx, -0.07, 1.50),
        "shoulder": P(0.185 * sx, 0.30, 1.16),
        "elbow": P(0.16 * sx, 0.11, 0.925),
        "knee": P(0.135 * sx, 0.115, 0.49),
        "ffet": P(0.13 * sx, 0.115, 0.175),
        "fcor": P(0.13 * sx, 0.211, 0.065),
        "ftoe": P(0.13 * sx, 0.303, 0.0),
        "hip": P(0.20 * sx, -1.03, 1.22),
        "stifle": P(0.215 * sx, -0.82, 0.83),
        "hock": P(0.13 * sx, -1.125, 0.55),
        "hfet": P(0.13 * sx, -1.125, 0.185),
        "hcor": P(0.13 * sx, -1.038, 0.065),
        "htoe": P(0.13 * sx, -0.956, 0.0),
    }


def neck_nodes():
    """(top, bottom, halfwidth) in (s, z): crest line and throat line of the neck."""
    return [((0.06, 1.59), (0.42, 1.10), 0.20),
            ((0.22, 1.62), (0.50, 1.23), 0.16),
            ((0.38, 1.685), (0.585, 1.36), 0.136),
            ((0.52, 1.765), (0.665, 1.48), 0.118),
            ((0.645, 1.845), (0.735, 1.59), 0.103),
            ((0.75, 1.90), (0.775, 1.68), 0.092),
            ((0.815, 1.905), (0.79, 1.75), 0.082)]


def horse_field():
    f = Field()
    Z = np.array([0, 0, 1.0])
    # ---- trunk: barrel, back, chest (sections along s: top, bottom, halfwidth, widest-at fraction)
    rows = [(-1.17, 1.47, 1.17, 0.10, 0.5), (-1.05, 1.54, 1.06, 0.18, 0.55), (-0.85, 1.58, 1.02, 0.225, 0.55),
            (-0.62, 1.56, 0.955, 0.255, 0.55), (-0.40, 1.535, 0.88, 0.278, 0.56), (-0.18, 1.545, 0.845, 0.285, 0.57),
            (0.02, 1.575, 0.855, 0.268, 0.58), (0.18, 1.575, 0.90, 0.24, 0.58), (0.32, 1.55, 0.99, 0.20, 0.55),
            (0.42, 1.48, 1.07, 0.13, 0.5)]
    nodes = []
    for s, top, bot, w, fr in rows:
        zw = bot + fr * (top - bot)
        nodes.append((P(0, s, zw), Z, top - zw, zw - bot, w))
    f.add(Loft(nodes, p=2.25), k=0.05, w=("spine",))
    # withers ridge
    f.add(Ell(P(0, -0.03, 1.545), (0.05, 0.24, 0.09)), k=0.07, w=("spine",))
    # croup + point of hips
    f.add(Ell(P(0, -0.86, 1.44), (0.20, 0.36, 0.16)), k=0.07, w=("spine",))
    for sx in (1, -1):
        f.add(Ell(P(0.20 * sx, -0.76, 1.43), (0.035, 0.05, 0.04)), k=0.08, w=("spine",))
    # tail head
    f.add(Ell(P(0, -1.16, 1.485), (0.05, 0.09, 0.045)), k=0.04, w=("spine",))

    for sx in (1, -1):
        J = leg_joints(sx)
        side = "L" if sx > 0 else "R"
        hl, fl = ("hl", side), ("fl", side)
        # ---- hindquarter: thigh tapering into the gaskin, hamstrings behind, stifle in front
        f.add(RCone(P(0.135 * sx, -1.03, 1.27), P(0.155 * sx, -0.92, 0.90), 0.185, 0.11, squash=(XL, 0.6)),
              k=0.07, w=("thigh", side))
        f.add(RCone(P(0.08 * sx, -1.17, 1.28), P(0.11 * sx, -1.11, 0.86), 0.10, 0.07, squash=(XL, 0.85)), k=0.06,
              w=("thigh", side))
        f.add(Ell(P(0.15 * sx, -0.76, 1.0), (0.07, 0.12, 0.08)), k=0.09, w=("thigh", side))
        f.add(Ell(P(0.19 * sx, -0.81, 0.885), (0.045, 0.055, 0.06)), k=0.05, w=hl)
        f.add(RCone(P(0.165 * sx, -0.93, 0.88), J["hock"] + P(0, 0, 0.03), 0.10, 0.05), k=0.05, w=hl)
        tib = unit(J["hock"] - J["stifle"])
        A = np.array([XL, np.cross(tib, XL), tib])
        f.add(Ell(P(0.145 * sx, -1.07, 0.76), (0.062, 0.085, 0.14), A), k=0.05, w=hl)
        f.add(RCone(P(0.13 * sx, -1.13, 0.86), P(0.13 * sx, -1.195, 0.60), 0.04, 0.03), k=0.04, w=("hock", side))
        f.add(Ell(J["hock"] + P(0, 0, -0.005), (0.05, 0.07, 0.065)), k=0.03, w=hl)
        f.add(RCone(P(0.13 * sx, -1.115, 0.52), P(0.13 * sx, -1.115, 0.21), 0.03, 0.027), k=0.02, w=hl)
        f.add(RCone(P(0.13 * sx, -1.155, 0.50), P(0.13 * sx, -1.155, 0.21), 0.021, 0.021), k=0.02, w=hl)
        f.add(Ell(J["hfet"] + P(0, -0.005, 0), (0.042, 0.055, 0.045)), k=0.02, w=hl)
        f.add(Ell(J["hfet"] + P(0, -0.04, -0.01), (0.03, 0.03, 0.03)), k=0.02, w=hl)
        f.add(RCone(J["hfet"], J["hcor"] + P(0, 0.005, -0.01), 0.033, 0.035), k=0.02, w=hl)
        # ---- foreleg: shoulder (scapula), upper arm, chest, triceps, elbow, forearm, knee, cannon, fetlock
        ax = unit(J["shoulder"] - J["scap"])
        e2 = unit(np.cross(ax, XL))
        A = np.array([unit(np.cross(e2, ax)), e2, ax])
        f.add(Ell((J["scap"] + J["shoulder"]) / 2 + P(-0.01 * sx, 0, 0), (0.07, 0.12, 0.30), A), k=0.07,
              w=("shoulder", side))
        f.add(Ell(P(0.172 * sx, 0.335, 1.17), (0.05, 0.065, 0.065)), k=0.06, w=fl)
        f.add(RCone(P(0.17 * sx, 0.31, 1.14), P(0.155 * sx, 0.16, 0.93), 0.08, 0.072), k=0.06, w=fl)
        f.add(Ell(P(0.065 * sx, 0.305, 1.08), (0.075, 0.09, 0.13)), k=0.07, w=("breast", side))
        f.add(Ell(P(0.155 * sx, 0.08, 1.05), (0.08, 0.13, 0.12)), k=0.07, w=fl)
        f.add(RCone(P(0.155 * sx, 0.06, 1.0), P(0.155 * sx, 0.075, 0.935), 0.04, 0.045), k=0.04, w=("elbow", side))
        f.add(RCone(J["elbow"] + P(0, 0.01, 0), J["knee"] + P(0, 0, 0.03), 0.08, 0.042), k=0.04, w=fl)
        f.add(Ell(P(0.15 * sx, 0.158, 0.80), (0.062, 0.058, 0.14)), k=0.045, w=fl)
        f.add(Ell(J["knee"] + P(0, 0.005, 0), (0.048, 0.047, 0.055)), k=0.025, w=fl)
        f.add(Ell(J["knee"] + P(0, -0.04, 0.015), (0.022, 0.025, 0.03)), k=0.02, w=fl)
        f.add(RCone(P(0.132 * sx, 0.125, 0.46), P(0.13 * sx, 0.125, 0.20), 0.028, 0.026), k=0.02, w=fl)
        f.add(RCone(P(0.132 * sx, 0.09, 0.45), P(0.13 * sx, 0.088, 0.20), 0.02, 0.021), k=0.02, w=fl)
        f.add(Ell(J["ffet"] + P(0, -0.005, 0), (0.042, 0.055, 0.045)), k=0.02, w=fl)
        f.add(Ell(J["ffet"] + P(0, -0.04, -0.01), (0.03, 0.03, 0.03)), k=0.02, w=fl)
        f.add(RCone(J["ffet"], J["fcor"] + P(0, 0.005, -0.01), 0.033, 0.035), k=0.02, w=fl)

    # ---- neck: loft between the crest line and the throat line
    nodes = []
    for (ts, tz), (bs, bz), w in neck_nodes():
        top, bot = P(0, ts, tz), P(0, bs, bz)
        dd = np.linalg.norm(top - bot)
        c = bot + (top - bot) * 0.45
        nodes.append((c, unit(top - bot), 0.55 * dd, 0.45 * dd, w))
    f.add(Loft(nodes, p=2.1), k=0.06, w=("neck",))

    # ---- head: loft along the face (top line, under line, halfwidth) + jowls, orbits, ears, nostrils
    hrows = [(-0.03, 0.06, -0.07, 0.06), (0.0, 0.088, -0.10, 0.075), (0.06, 0.097, -0.155, 0.09),
             (0.14, 0.097, -0.19, 0.10), (0.22, 0.09, -0.17, 0.094), (0.30, 0.079, -0.118, 0.075),
             (0.40, 0.07, -0.088, 0.062), (0.48, 0.064, -0.08, 0.062), (0.54, 0.058, -0.075, 0.067),
             (0.58, 0.038, -0.055, 0.055), (0.60, 0.008, -0.022, 0.03)]
    nodes = []
    for u, vt, vb, w in hrows:
        c = hp(u, (vt + vb) / 2)
        nodes.append((c, HN, (vt - vb) / 2, (vt - vb) / 2, w))
    f.add(Loft(nodes, p=2.2), k=0.04, w="head")
    A = np.array([XL, HA, HN])
    for sx in (1, -1):
        f.add(Ell(hp(0.15, -0.10, 0.05 * sx), (0.05, 0.10, 0.095), A), k=0.045, w="head")
        f.add(Ell(hp(0.125, 0.055, 0.082 * sx), (0.03, 0.04, 0.028), A), k=0.02, w="head")
        # ears: flattened round cones pointing up/forward/out, with a cupped front
        base = hp(0.015, 0.082, 0.052 * sx)
        e = unit(P(0.28 * sx, 0.24, 0.93))
        tip = base + e * 0.145
        fwd = unit(P(0, 1, 0) - e * (P(0, 1, 0) @ e))
        f.add(RCone(base, base + e * 0.07, 0.036, 0.034, squash=(fwd, 0.55)), k=0.02, w=("ear", "L" if sx > 0 else "R"))
        f.add(RCone(base + e * 0.07, tip, 0.034, 0.008, squash=(fwd, 0.55)), k=0.02, w=("ear", "L" if sx > 0 else "R"))
        f.cut(RCone(base + e * 0.04 + fwd * 0.018 + XL * 0.004 * sx, tip + fwd * 0.006 - e * 0.012, 0.022, 0.004,
                    squash=(fwd, 0.5)), k=0.006)
    for sx in (1, -1):
        # eye socket (the eyeball mesh sits in it) and nostrils
        f.cut(Ell(hp(0.13, 0.036, 0.096 * sx), (0.02, 0.022, 0.016), A), k=0.008)
        na = unit(HA * 0.55 + HN * 0.75 + XL * 0.35 * sx)
        nb = unit(np.cross(na, XL))
        An = np.array([unit(np.cross(nb, na)), nb, na])
        f.cut(Ell(hp(0.565, 0.010, 0.047 * sx), (0.008, 0.012, 0.02), An), k=0.006)
    return f


HORSE_BOX = (P(-0.40, 1.32, 0.0) * [1, 1, 1], P(0.40, -1.40, 2.16))


def horse_box():
    lo, hi = HORSE_BOX
    return np.minimum(lo, hi), np.maximum(lo, hi)


# ====================================================================== explicit meshes (hooves, eyes, hair, tack)

class MB:
    """Mesh builder: verts with optional fixed weights, faces with a material and optional per-loop UVs."""

    def __init__(self):
        self.v, self.vw, self.f, self.fm, self.fuv = [], [], [], [], []

    def add(self, co, w=None):
        self.v.append(np.asarray(co, float))
        self.vw.append(w)
        return len(self.v) - 1

    def face(self, idx, mat, uv=None):
        self.f.append(list(idx))
        self.fm.append(mat)
        self.fuv.append(uv)

    def grid(self, rows, mat, closed=False, uvs=None, flip=False):
        """rows: list of lists of vertex indices (same length). Quads between consecutive rows."""
        n = len(rows[0])
        for r in range(len(rows) - 1):
            for k in range(n if closed else n - 1):
                k2 = (k + 1) % n
                q = [rows[r][k], rows[r][k2], rows[r + 1][k2], rows[r + 1][k]]
                uv = None
                if uvs is not None:
                    uv = [uvs[r][k], uvs[r][k2] if k2 else (uvs[r][n] if len(uvs[r]) > n else uvs[r][k2]),
                          uvs[r + 1][k2] if k2 else (uvs[r + 1][n] if len(uvs[r + 1]) > n else uvs[r + 1][k2]),
                          uvs[r + 1][k]]
                if flip:
                    q = q[::-1]
                    uv = uv[::-1] if uv else None
                self.face(q, mat, uv)

    def fan(self, ring, centre, mat, flip=False):
        n = len(ring)
        for k in range(n):
            q = [ring[k], ring[(k + 1) % n], centre]
            self.face(q[::-1] if flip else q, mat)

    def build(self, name, mats):
        me = bpy.data.meshes.new(name)
        me.from_pydata([tuple(p) for p in self.v], [], [tuple(f) for f in self.f])
        me.update()
        names = []
        for m in self.fm:
            if m not in names:
                names.append(m)
        for n in names:
            me.materials.append(mats[n])
        me.polygons.foreach_set("material_index", [names.index(m) for m in self.fm])
        if any(u is not None for u in self.fuv):
            uvl = me.uv_layers.new(name="UVMap")
            for poly, uv in zip(me.polygons, self.fuv):
                for li, k in zip(poly.loop_indices, range(poly.loop_total)):
                    uvl.data[li].uv = uv[k] if uv is not None else (0.0, 0.0)
        for p in me.polygons:
            p.use_smooth = True
        o = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(o)
        return o


def ring_pts(c, ax, ay, rx, ry, n, phase=0.0):
    return [c + ax * rx * math.cos(phase + k / n * math.tau) + ay * ry * math.sin(phase + k / n * math.tau)
            for k in range(n)]


def hooves(mb):
    """Front and hind hooves: coronet ring (higher at the toe), flared wall, ground ring, sole + top cap."""
    n = 16
    out = {}
    for sx in (1, -1):
        J = leg_joints(sx)
        side = "L" if sx > 0 else "R"
        for kind, cor, toe, rl, rs in (("f", J["fcor"], J["ftoe"], (0.043, 0.062), (0.047, 0.068)),
                                         ("h", J["hcor"], J["htoe"], (0.041, 0.058), (0.045, 0.064))):
            fwd = P(0, 1, 0)
            gc = toe - fwd * rs[1]
            gc[2] = 0.0
            cc = cor.copy()
            cc[1] = (toe - fwd * (rs[1] + 0.068 * 0.0))[1] + 0.0
            cfront = toe[1] - (-0.075 / math.tan(math.radians(56)))  # y grows backwards
            cc = np.array([cor[0], cfront + rs[0], 0.0])
            bone = f"{kind}hoof_{side}"
            rows = []
            for zf, (rlat, rlong), cen in ((1.0, (rl[0], rs[0]), cc), (0.45, ((rl[0] + rl[1]) * 0.52, (rs[0] + rs[1]) * 0.52), None),
                                         (0.0, (rl[1], rs[1]), gc)):
                row = []
                for k in range(n):
                    a = k / n * math.tau
                    ca, sa = math.cos(a), math.sin(a)  # a=0 -> toe
                    if cen is None:
                        c = cc * 0.45 + gc * 0.55
                    else:
                        c = cen
                    x = c[0] + rlat * sa
                    y = c[1] - rlong * ca
                    heel = (1 - ca) / 2
                    if zf == 1.0:
                        z = 0.077 - 0.040 * heel ** 1.4
                    elif zf == 0.45:
                        z = (0.077 - 0.040 * heel ** 1.4) * 0.42
                    else:
                        z = 0.0
                    row.append(mb.add((x, y, z), {bone: 1.0}))
                rows.append(row)
            mb.grid(rows, "horse_hoof", closed=True, flip=True)
            top = mb.add(cc + [0, 0, 0.05], {bone: 1.0})
            mb.fan(rows[0], top, "horse_hoof", flip=True)
            bot = mb.add(gc + [0, 0, 0.004], {bone: 1.0})
            mb.fan(rows[-1], bot, "horse_hoof", flip=False)
            out[bone] = (cc, gc)
    return out


def eyes(mb):
    for sx in (1, -1):
        c = hp(0.13, 0.036, 0.091 * sx)
        nrm = unit(XL * sx * 0.92 + HN * 0.25 + HA * 0.15)
        a1 = unit(np.cross(nrm, XL if abs(nrm[0]) < 0.9 else HN))
        a2 = np.cross(nrm, a1)
        rows = []
        segs, rings, r = 10, 6, 0.026
        top = mb.add(c + nrm * r, {"head": 1.0})
        for i in range(1, rings):
            th = i / rings * math.pi
            rows.append([mb.add(c + nrm * r * math.cos(th) + (a1 * math.cos(k / segs * math.tau) +
                                                             a2 * math.sin(k / segs * math.tau)) * r * math.sin(th),
                                {"head": 1.0}) for k in range(segs)])
        bot = mb.add(c - nrm * r, {"head": 1.0})
        mb.fan(rows[0], top, "horse_eye", flip=True)
        mb.grid(rows, "horse_eye", closed=True, flip=False)
        mb.fan(rows[-1], bot, "horse_eye", flip=False)


def surface_hit(field, start, direction, maxd=0.5, step=0.004):
    """March from inside along direction until the field turns positive; return the surface point."""
    d = unit(direction)
    t = 0.0
    prev = field.at(np.array([start]))[0]
    while t < maxd:
        t += step
        q = start + d * t
        v = field.at(np.array([q]))[0]
        if v > 0 and prev <= 0:
            return start + d * (t - step * v / (v - prev + 1e-12))
        prev = v
    return start + d * t


def surface_hits(field, starts, dirs, maxd=0.7, step=0.003):
    """Batched surface_hit for many rays (all start inside)."""
    S = np.asarray(starts, float)
    D = np.asarray(dirs, float)
    D = D / np.linalg.norm(D, axis=1)[:, None]
    n = len(S)
    res = S + D * maxd
    done = np.zeros(n, bool)
    prev = field.at(S)
    t = 0.0
    while t < maxd and not done.all():
        t += step
        idx = np.nonzero(~done)[0]
        v = field.at(S[idx] + D[idx] * t)
        pv = prev[idx]
        cr = (v > 0) & (pv <= 0)
        hit = idx[cr]
        frac = step * v[cr] / (v[cr] - pv[cr] + 1e-12)
        res[hit] = S[hit] + D[hit] * (t - frac)[:, None]
        done[hit] = True
        prev[idx] = v
    return res


def crest_line(field, n=15):
    """Points on the crest from behind the ears (bridle path) to the withers."""
    nodes = neck_nodes()
    tops = [P(0, ts, tz) for (ts, tz), _, _ in nodes]
    bots = [P(0, bs, bz) for _, (bs, bz), _ in nodes]
    pts = []
    for i in range(n):
        u = 0.86 - i / (n - 1) * 0.82   # fraction along the neck nodes (1 = poll end)
        x = u * (len(nodes) - 1)
        j = min(int(x), len(nodes) - 2)
        t = x - j
        top = tops[j] * (1 - t) + tops[j + 1] * t
        bot = bots[j] * (1 - t) + bots[j + 1] * t
        mid = bot + (top - bot) * 0.5
        pts.append(surface_hit(field, mid, top - bot, maxd=0.4))
    return pts


def mane(mb, field, rng):
    """Pulled racing mane lying on the right (off) side of the neck, ragged locks, + forelock."""
    pts = crest_line(field, n=17)
    n = len(pts)
    rows_out, rows_in = [], []
    side = np.array([-1.0, 0, 0])
    for i, rpt in enumerate(pts):
        u = i / (n - 1)
        L = (0.07 + 0.065 * math.sin(math.pi * min(1, u * 1.1)) ** 0.6) * (1.0 if i % 2 else 0.72) * (0.9 + 0.2 * rng.random())
        down = unit(P(0, 0.30, -1.0))
        ro, ri = [], []
        for j, t in enumerate((0.0, 0.3, 0.65, 1.0)):
            base = rpt + side * (0.01 + 0.075 * t) + down * (L * t * 0.7)
            inner = base - unit(side * 0.7 - down * 0.2) * 0.12
            sp = surface_hit(field, inner, base - inner, maxd=0.3)
            nrm = unit(sp - inner)
            o = sp + nrm * (0.004 + 0.012 * (1 - t) + 0.006 * t)
            ii = sp + nrm * (0.0015 + 0.004 * t)
            if j == 0:
                o = rpt + P(0, 0, 0.012) + side * 0.006
                ii = rpt - P(0, 0, 0.012) - side * 0.012
            ro.append(mb.add(o, ("mane", u, t)))
            ri.append(mb.add(ii, ("mane", u, t)))
        rows_out.append(ro)
        rows_in.append(ri)
    mb.grid(rows_out, "horse_hair", flip=True)
    mb.grid(rows_in, "horse_hair", flip=False)
    for i in range(n - 1):  # ragged tip edge
        mb.face([rows_out[i][-1], rows_out[i + 1][-1], rows_in[i + 1][-1], rows_in[i][-1]], "horse_hair")
    for rows_o, rows_i, fl in ((rows_out[0], rows_in[0], False), (rows_out[-1], rows_in[-1], True)):
        for j in range(3):
            q = [rows_o[j], rows_o[j + 1], rows_i[j + 1], rows_i[j]]
            mb.face(q[::-1] if fl else q, "horse_hair")
    # forelock: lies on the forehead between the eyes
    rows_o, rows_i = [], []
    for j, t in enumerate((0.0, 0.35, 0.7, 1.0)):
        ro, ri = [], []
        for k in range(5):
            x = (k / 4 - 0.5) * (0.045 + 0.04 * t)
            u = 0.03 + 0.17 * t + (0.012 if k % 2 else 0.0) * t
            sp = surface_hit(field, hp(u, -0.02, x), HN, maxd=0.25)
            ro.append(mb.add(sp + HN * (0.005 + 0.007 * (1 - t)), {"head": 1.0}))
            ri.append(mb.add(sp - HN * 0.002, {"head": 1.0}))
        rows_o.append(ro)
        rows_i.append(ri)
    mb.grid(rows_o, "horse_hair", flip=False)
    mb.grid(rows_i, "horse_hair", flip=True)
    for k in range(4):
        mb.face([rows_o[-1][k], rows_i[-1][k], rows_i[-1][k + 1], rows_o[-1][k + 1]], "horse_hair")
    for side_k in (0, 4):
        for j in range(3):
            q = [rows_o[j][side_k], rows_o[j + 1][side_k], rows_i[j + 1][side_k], rows_i[j][side_k]]
            mb.face(q if side_k == 0 else q[::-1], "horse_hair")


TAIL_PATH = [(-1.15, 1.50), (-1.25, 1.445), (-1.305, 1.33), (-1.325, 1.15), (-1.33, 0.95), (-1.325, 0.76),
             (-1.31, 0.56)]


def tail(mb, rng):
    """Dock + hanging hair as a flattened tube along TAIL_PATH with a ragged end."""
    pts = [P(0, s_, z_) for s_, z_ in TAIL_PATH]
    # resample along the path
    seg = [np.linalg.norm(pts[i + 1] - pts[i]) for i in range(len(pts) - 1)]
    tot = sum(seg)
    m = 12
    samples = []
    for i in range(m + 1):
        d = i / m * tot
        j = 0
        while j < len(seg) - 1 and d > seg[j]:
            d -= seg[j]
            j += 1
        t = min(1.0, d / seg[j])
        samples.append((pts[j] * (1 - t) + pts[j + 1] * t, i / m))
    n = 12
    rows = []
    for i, (c, u) in enumerate(samples):
        j = min(i, m - 1)
        tng = unit(samples[min(i + 1, m)][0] - samples[max(i - 1, 0)][0])
        nrm = unit(np.cross(XL, tng))  # front/back in the sagittal plane
        w = 0.032 + 0.05 * smoothstep(0.0, 0.4, u) - 0.022 * smoothstep(0.7, 1.0, u)
        dpt = 0.032 + 0.045 * smoothstep(0.0, 0.4, u) - 0.022 * smoothstep(0.7, 1.0, u)
        row = []
        for k in range(n):
            a = k / n * math.tau
            jag = 0.0
            if i == m:
                jag = 0.06 * (0.5 + 0.5 * math.sin(a * 3 + 0.7)) + 0.03 * rng.random()
            p = c + XL * w * math.cos(a) + nrm * dpt * math.sin(a) + tng * jag
            row.append(mb.add(p, ("tail", u + jag / tot)))
        rows.append(row)
    mb.grid(rows, "horse_hair", closed=True, flip=False)
    end = mb.add(samples[-1][0] + unit(samples[-1][0] - samples[-2][0]) * 0.05, ("tail", 1.05))
    mb.fan(rows[-1], end, "horse_hair", flip=False)
    top = mb.add(samples[0][0] - unit(samples[1][0] - samples[0][0]) * 0.02, ("tail", 0.0))
    mb.fan(rows[0], top, "horse_hair", flip=True)


# ====================================================================== tack

def grad(field, p, e=0.002):
    g = np.zeros(3)
    for k in range(3):
        d = np.zeros(3)
        d[k] = e
        g[k] = field.at(np.array([p + d]))[0] - field.at(np.array([p - d]))[0]
    n = np.linalg.norm(g)
    return g / n if n > 1e-9 else np.array([0.0, 0.0, 1.0])


def body_section_pt(field, s_, ang, sx, zc=1.20):
    """Point on the trunk surface at forward position s_, angle ang (0 = top, pi = bottom) on side sx."""
    c = P(0, s_, zc)
    d = P(math.sin(ang) * sx, 0, math.cos(ang))
    return surface_hit(field, c, d, maxd=0.7, step=0.003)


def arc_samples(field, s_, sx, amax=math.radians(178), n=60, zc=1.20):
    """Surface points down one side of the trunk section, with cumulative arc length from the spine."""
    angs = [amax * k / (n - 1) for k in range(n)]
    pts = list(surface_hits(field, [P(0, s_, zc)] * n, [P(math.sin(a) * sx, 0, math.cos(a)) for a in angs]))
    L = [0.0]
    for k in range(1, n):
        L.append(L[-1] + np.linalg.norm(pts[k] - pts[k - 1]))
    return pts, np.array(L)


def at_arc(pts, L, a):
    k = int(np.clip(np.searchsorted(L, a) - 1, 0, len(L) - 2))
    t = (a - L[k]) / max(L[k + 1] - L[k], 1e-9)
    return pts[k] * (1 - t) + pts[k + 1] * t


def ribbon(mb, pts, nrms, width, mat, wfn, thick=0.003, uv=False):
    """Flat two-sided strap along pts lying on the surface (normals nrms). wfn(i, t) -> weights spec."""
    n = len(pts)
    tops, bots = [], []
    for i in range(n):
        tg = unit(pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)])
        sd = unit(np.cross(nrms[i], tg)) * width / 2
        w = wfn(i, i / (n - 1))
        tops.append((mb.add(pts[i] + sd + nrms[i] * thick, w), mb.add(pts[i] - sd + nrms[i] * thick, w)))
        bots.append((mb.add(pts[i] + sd, w), mb.add(pts[i] - sd, w)))
    for i in range(n - 1):
        a, b = tops[i], tops[i + 1]
        mb.face([a[0], b[0], b[1], a[1]], mat)
        a, b = bots[i], bots[i + 1]
        mb.face([a[1], b[1], b[0], a[0]], mat)


def tube_loop(mb, path, r, mat, w, sides=4, closed=True):
    n = len(path)
    rings = []
    for i in range(n):
        tg = unit(path[(i + 1) % n] - path[(i - 1) % n]) if closed else unit(path[min(i + 1, n - 1)] - path[max(i - 1, 0)])
        a1 = unit(np.cross(tg, XL if abs(tg[0]) < 0.9 else np.array([0, 0, 1.0])))
        a2 = np.cross(tg, a1)
        rings.append([mb.add(path[i] + (a1 * math.cos(k / sides * math.tau) + a2 * math.sin(k / sides * math.tau)) * r, w)
                      for k in range(sides)])
    if closed:
        rings.append(rings[0])
    mb.grid(rings, mat, closed=True, flip=True)


HEAD_ROWS = [(-0.03, 0.06, -0.07), (0.0, 0.088, -0.10), (0.06, 0.097, -0.155), (0.14, 0.097, -0.19),
             (0.22, 0.09, -0.17), (0.30, 0.079, -0.118), (0.40, 0.07, -0.088), (0.48, 0.064, -0.08),
             (0.54, 0.058, -0.075), (0.58, 0.038, -0.055)]


def head_pt(field, u, ang, off=0.004):
    """Head surface point at face position u, angle ang (deg) round the section: 0 = top, 90 = left, 180 = under."""
    us = [r[0] for r in HEAD_ROWS]
    vc = float(np.interp(u, us, [(r[1] + r[2]) / 2 for r in HEAD_ROWS]))
    c = hp(max(u, -0.015), vc)
    a = math.radians(ang)
    q = surface_hit(field, c, HN * math.cos(a) + XL * math.sin(a), maxd=0.3, step=0.002)
    n = grad(field, q)
    return q + n * off, n


def tack(mb, field, JB):
    W_FIELD = ("field",)
    # ---- saddlecloth: one panel per side, uv [0,1]^2 upright as seen from that side
    s0, s1, amax = -0.60, 0.10, 0.44
    nu, nv = 8, 5
    for sx in (1, -1):
        grid_o, grid_i, uvs = [], [], []
        cols = []
        for a in range(nu):
            s_ = s1 + (s0 - s1) * a / (nu - 1)
            pts, L = arc_samples(field, s_, sx)
            cols.append((s_, pts, L))
        for b in range(nv):
            ro, ri, ru = [], [], []
            for a in range(nu):
                s_, pts, L = cols[a]
                arc = amax * (1 - b / (nv - 1))
                q = at_arc(pts, L, arc)
                n = grad(field, q)
                ro.append(mb.add(q + n * 0.009, W_FIELD))
                ri.append(mb.add(q + n * 0.005, W_FIELD))
                U = (s1 - s_) / (s1 - s0) if sx > 0 else (s_ - s0) / (s1 - s0)
                ru.append((U, b / (nv - 1)))
            grid_o.append(ro)
            grid_i.append(ri)
            uvs.append(ru)
        for b in range(nv - 1):
            for a in range(nu - 1):
                q = [grid_o[b][a], grid_o[b][a + 1], grid_o[b + 1][a + 1], grid_o[b + 1][a]]
                uv = [uvs[b][a], uvs[b][a + 1], uvs[b + 1][a + 1], uvs[b + 1][a]]
                qi = [grid_i[b][a], grid_i[b][a + 1], grid_i[b + 1][a + 1], grid_i[b + 1][a]]
                if sx < 0:
                    mb.face(q, "saddlecloth", uv)
                    mb.face(qi[::-1], "saddlecloth", uv[::-1])
                else:
                    mb.face(q[::-1], "saddlecloth", uv[::-1])
                    mb.face(qi, "saddlecloth", uv)
        for a in range(nu - 1):  # hem
            q = [grid_o[0][a], grid_o[0][a + 1], grid_i[0][a + 1], grid_i[0][a]]
            mb.face(q if sx > 0 else q[::-1], "saddlecloth", [(0, 0)] * 4)
    # ---- racing saddle: thin seat + flaps over the cloth, small raised pommel
    s0, s1, amax = -0.34, 0.05, 0.26
    nu, nv = 7, 9
    cols = []
    for a in range(nu):
        s_ = s1 + (s0 - s1) * a / (nu - 1)
        cols.append((s_, {sx: arc_samples(field, s_, sx) for sx in (1, -1)}))
    top, bot = [], []
    for b in range(nv):
        rt, rb = [], []
        arc = -amax + 2 * amax * b / (nv - 1)
        sx = 1 if arc >= 0 else -1
        for a in range(nu):
            s_, sides = cols[a]
            pts, L = sides[sx]
            q = at_arc(pts, L, abs(arc))
            n = grad(field, q)
            fa = (a / (nu - 1))
            prof = 0.012 + 0.024 * max(0.0, 1 - (arc / 0.20) ** 2) * (0.55 + 0.45 * math.exp(-((fa - 0.05) / 0.15) ** 2))
            rt.append(mb.add(q + n * (0.012 + prof), W_FIELD))
            rb.append(mb.add(q + n * 0.011, W_FIELD))
        top.append(rt)
        bot.append(rb)
    mb.grid(top, "tack", flip=False)
    mb.grid(bot, "tack", flip=True)
    for a in range(nu - 1):
        for edge, fl in ((0, True), (nv - 1, False)):
            q = [top[edge][a], top[edge][a + 1], bot[edge][a + 1], bot[edge][a]]
            mb.face(q[::-1] if fl else q, "tack")
    for b in range(nv - 1):
        for edge, fl in ((0, False), (nu - 1, True)):
            q = [top[b][edge], top[b + 1][edge], bot[b + 1][edge], bot[b][edge]]
            mb.face(q[::-1] if fl else q, "tack")
    # ---- girth (behind the elbows, under the belly, side to side)
    s_ = -0.075
    ring_a, ring_b = [], []
    ang = np.linspace(math.radians(52), math.radians(308), 17)
    for s2, lst in ((s_ - 0.032, ring_a), (s_ + 0.032, ring_b)):
        hits = surface_hits(field, [P(0, s2, 1.20)] * len(ang), [P(math.sin(a), 0, math.cos(a)) for a in ang])
        for q in hits:
            n = grad(field, q)
            lst.append(mb.add(q + n * 0.007, W_FIELD))
    mb.grid([ring_a, ring_b], "tack", flip=False)
    # ---- stirrup leathers + irons (follow the rider's feet)
    for sd, sx in (("L", 1), ("R", -1)):
        an, toe = JB["an_" + sd], JB["toe_" + sd]
        fd = unit(toe - an)
        ball = an + fd * 0.10 - P(0, 0, 0.035)
        bar = body_section_pt(field, 0.0, math.radians(60), sx) + P(0.012 * sx, 0, 0)
        top_iron = ball + P(0, 0, 0.085)
        pts = [bar + (top_iron - bar) * t for t in np.linspace(0, 1, 7)]
        nr = [unit(P(sx, 0, 0)) for _ in pts]
        ribbon(mb, pts, nr, 0.026, "tack",
               lambda i, t, sd=sd: {"body": 1 - smoothstep(0.1, 0.95, t), f"j_foot_{sd}": smoothstep(0.1, 0.95, t)},
               thick=0.004)
        # iron: arch + tread around the ball of the foot (plane across the foot)
        side_ax = unit(np.cross(fd, np.array([0, 0, 1.0])))
        path = []
        for k in range(12):
            a = k / 12 * math.tau
            x = math.cos(a) * 0.055
            z = (math.sin(a) * 0.5 + 0.5) * 0.09 if math.sin(a) > 0 else math.sin(a) * 0.008
            path.append(ball + side_ax * x + P(0, 0, z - 0.01))
        tube_loop(mb, path, 0.006, "tack_metal", {f"j_foot_{sd}": 1.0}, sides=4)
    # ---- bridle: headstall (cheekpieces + crown), browband, noseband, throatlatch; bit + rings; reins
    H = {"head": 1.0}

    def strap(path, width=0.02, w=H, off=0.004):
        pts, nrs = [], []
        for u, ang in path:
            q, n = head_pt(field, u, ang, off)
            pts.append(q)
            nrs.append(n)
        ribbon(mb, pts, nrs, width, "tack", (w if callable(w) else (lambda i, t: w)), thick=0.003)

    # headstall: bit ring -> along the cheek (below/behind the eye) -> over the poll behind the ears -> other side
    cheek = [(0.485, 112), (0.42, 108), (0.34, 102), (0.24, 98), (0.14, 104), (0.07, 98), (0.02, 70), (-0.025, 40),
             (-0.035, 0)]
    strap(cheek + [(u, -a) for u, a in cheek[::-1][1:]])
    strap([(0.065, 95), (0.08, 60), (0.085, 0), (0.08, -60), (0.065, -95)], width=0.018)
    strap([(0.42, a) for a in np.linspace(0, 360, 17)], width=0.024)
    strap([(-0.01, 80), (-0.012, 115), (-0.014, 150), (-0.015, 180), (-0.014, 210), (-0.012, 245), (-0.01, 280)],
          width=0.016, w=lambda i, t: {"head": 0.7, "neck3": 0.3})
    bit_c = hp(0.50, -0.05)
    bar = [bit_c + XL * x for x in np.linspace(-0.082, 0.082, 5)]
    rings = []
    for k, q in enumerate(bar[:-1]):
        pass
    tube_loop(mb, bar, 0.006, "tack_metal", H, sides=5, closed=False)
    for sx in (1, -1):
        c = bit_c + XL * 0.084 * sx
        path = [c + (HA * math.cos(k / 10 * math.tau) + HN * math.sin(k / 10 * math.tau)) * 0.028 for k in range(10)]
        tube_loop(mb, path, 0.0045, "tack_metal", H, sides=3)
    # reins: from the back of each ring along the neck into the rider's fists
    for sd, sx in (("L", 1), ("R", -1)):
        a = bit_c + XL * 0.086 * sx - HA * 0.028
        b = JB["wr_" + sd] + unit(JB["hd_" + sd] - JB["wr_" + sd]) * 0.05
        pts, nrs = [], []
        m = 14
        for k in range(m + 1):
            t = k / m
            q = a + (b - a) * t + P(0, 0, 0.05 * math.sin(math.pi * t))
            for _ in range(30):
                fv = field.at(np.array([q]))[0]
                if fv > 0.018 or t > 0.9:
                    break
                q = q + grad(field, q) * (0.018 - fv + 0.002)
            pts.append(q)
            nrs.append(unit(P(sx * 0.9, 0, 0.45)))

        def rw(i, t, sd=sd, pts=pts):
            hw = 1 - smoothstep(0.0, 0.25, t)
            jw = smoothstep(0.55, 0.97, t)
            mid = max(0.0, 1 - hw - jw)
            out = {"head": hw, f"j_hand_{sd}": jw}
            if mid > 0:
                fw = field_weights_cache(pts[i])
                for bn, x in fw.items():
                    out[bn] = out.get(bn, 0) + mid * x
            return out
        ribbon(mb, pts, nrs, 0.018, "tack", rw, thick=0.003)


_FW = {}


def field_weights_cache(q):
    return _FW["fn"](q)


# ====================================================================== skeleton

def frame_x(head, y, x_hint=(1.0, 0.0, 0.0)):
    """4x4 bone frame: Y along the bone, X as close to x_hint as possible (sagittal hinge axis), Z = X x Y."""
    y = V(tuple(y)).normalized()
    x = V(tuple(x_hint))
    x = (x - y * x.dot(y)).normalized()
    z = x.cross(y).normalized()
    m = Matrix((x, y, z)).transposed().to_4x4()
    m.translation = V(tuple(head))
    return m


def horse_bones():
    """[(name, head, tail, parent, deform)] for the horse (rest = square stance)."""
    B = [("root", P(0, -0.3, 0), P(0, 0.3, 0), None, False),
         ("body", P(0, -0.15, 1.20), P(0, 0.30, 1.26), "root", True),
         ("barrel", P(0, -0.25, 1.17), P(0, -0.25, 0.92), "body", True),
         ("loin", P(0, -0.40, 1.42), P(0, -0.72, 1.46), "body", True),
         ("pelvis", P(0, -0.72, 1.46), P(0, -1.15, 1.40), "loin", True)]
    tp = [P(0, s_, z_) for s_, z_ in TAIL_PATH]
    tj = [tp[0], tp[1], tp[2], tp[3], tp[4], tp[6]]
    for k in range(5):
        B.append((f"tail{k + 1}", tj[k], tj[k + 1], "pelvis" if k == 0 else f"tail{k}", True))
    B += [("neck1", P(0, 0.25, 1.38), P(0, 0.48, 1.56), "body", True),
          ("neck2", P(0, 0.48, 1.56), P(0, 0.66, 1.72), "neck1", True),
          ("neck3", P(0, 0.66, 1.72), HEAD_O, "neck2", True),
          ("head", HEAD_O, hp(0.45, 0.0), "neck3", True)]
    for sx, sd in ((1, "L"), (-1, "R")):
        base = hp(0.015, 0.082, 0.052 * sx)
        e = unit(P(0.28 * sx, 0.24, 0.93))
        B.append((f"ear_{sd}", base, base + e * 0.12, "head", True))
    crest = [P(0, 0.05, 1.63), P(0.0, 0.32, 1.70), P(0, 0.56, 1.83), P(0, 0.76, 1.93)]
    for k in range(3):
        B.append((f"mane{k + 1}", crest[k], crest[k + 1], f"neck{k + 1}", True))
    for sx, sd in ((1, "L"), (-1, "R")):
        J = leg_joints(sx)
        B += [(f"scap_{sd}", J["scap"], J["shoulder"], "body", True),
              (f"humerus_{sd}", J["shoulder"], J["elbow"], f"scap_{sd}", True),
              (f"forearm_{sd}", J["elbow"], J["knee"], f"humerus_{sd}", True),
              (f"fcannon_{sd}", J["knee"], J["ffet"], f"forearm_{sd}", True),
              (f"fpastern_{sd}", J["ffet"], J["fcor"], f"fcannon_{sd}", True),
              (f"fhoof_{sd}", J["fcor"], J["ftoe"], f"fpastern_{sd}", True),
              (f"femur_{sd}", J["hip"], J["stifle"], "pelvis", True),
              (f"tibia_{sd}", J["stifle"], J["hock"], f"femur_{sd}", True),
              (f"hcannon_{sd}", J["hock"], J["hfet"], f"tibia_{sd}", True),
              (f"hpastern_{sd}", J["hfet"], J["hcor"], f"hcannon_{sd}", True),
              (f"hhoof_{sd}", J["hcor"], J["htoe"], f"hpastern_{sd}", True)]
    return B


class Rig:
    """Bones as rest frames in armature space; poses are {bone: 4x4 armature-space matrix}."""

    def __init__(self, name):
        self.name = name
        self.order, self.parent, self.rest, self.length, self.deform = [], {}, {}, {}, {}
        self.head0, self.tail0 = {}, {}
        self.obj = None

    def add(self, name, head, tail, parent, deform=True, x_hint=(1.0, 0.0, 0.0)):
        head, tail = np.asarray(head, float), np.asarray(tail, float)
        self.order.append(name)
        self.parent[name] = parent
        self.rest[name] = frame_x(head, tail - head, x_hint)
        self.length[name] = float(np.linalg.norm(tail - head))
        self.deform[name] = deform
        self.head0[name], self.tail0[name] = head, tail

    def build(self):
        arm = bpy.data.armatures.new(self.name)
        o = bpy.data.objects.new(self.name, arm)
        bpy.context.scene.collection.objects.link(o)
        bk.select([o])
        bpy.ops.object.mode_set(mode="EDIT")
        for b in self.order:
            eb = arm.edit_bones.new(b)
            M = self.rest[b]
            eb.head = M.translation
            eb.tail = M @ V((0, self.length[b], 0))
            eb.align_roll(M.to_3x3() @ V((0, 0, 1)))
            eb.use_deform = self.deform[b]
            if self.parent[b]:
                eb.parent = arm.edit_bones[self.parent[b]]
        bpy.ops.object.mode_set(mode="OBJECT")
        for b in self.order:
            self.rest[b] = arm.bones[b].matrix_local.copy()
        for pb in o.pose.bones:
            pb.rotation_mode = "QUATERNION"
        self.obj = o
        return o

    def local_rest(self, b):
        p = self.parent[b]
        return self.rest[b] if p is None else self.rest[p].inverted() @ self.rest[b]

    def basis(self, Pm):
        out = {}
        for b in self.order:
            p = self.parent[b]
            if p is None:
                out[b] = self.rest[b].inverted() @ Pm[b]
            else:
                out[b] = self.local_rest(b).inverted() @ Pm[p].inverted() @ Pm[b]
        return out

    def apply_pose(self, Pm):
        bas = self.basis(Pm)
        for b in self.order:
            pb = self.obj.pose.bones[b]
            loc, rot, sc = bas[b].decompose()
            pb.location, pb.rotation_quaternion, pb.scale = loc, rot, sc
        bpy.context.view_layer.update()

    def rest_pose(self):
        return {b: self.rest[b].copy() for b in self.order}


# ====================================================================== skin weights

CHAIN_DEF = {
    "fl": [("scap", 0.0), ("humerus", 0.08), ("forearm", 0.06), ("fcannon", 0.035), ("fpastern", 0.03), ("fhoof", 0.02)],
    "hl": [("femur", 0.0), ("tibia", 0.07), ("hcannon", 0.04), ("hpastern", 0.03), ("hhoof", 0.02)],
}


def chain_weights(rig, Q, segs):
    """segs: [(bone, head, tail, blend_halfwidth_at_head)] contiguous. Partition of unity along the chain."""
    n = len(Q)
    best = np.full(n, np.inf)
    u = np.zeros(n)
    cum = 0.0
    starts = []
    for b, h, t, bw in segs:
        ab = t - h
        L = np.linalg.norm(ab)
        tt = np.clip(((Q - h) @ ab) / (L * L), 0, 1)
        dist = np.linalg.norm(Q - (h + np.outer(tt, ab)), axis=1)
        m = dist < best
        best[m] = dist[m]
        u[m] = cum + tt[m] * L
        starts.append(cum)
        cum += L
    S = [np.ones(n)]
    for j in range(1, len(segs)):
        bw = max(segs[j][3], 1e-3)
        S.append(smoothstep(starts[j] - bw, starts[j] + bw, u))
    S.append(np.zeros(n))
    out = {}
    for j, (b, h, t, bw) in enumerate(segs):
        w = S[j] - S[j + 1]
        out[b] = out.get(b, 0) + w
    return out


def limb_segs(rig, kind, side):
    return [(f"{b}_{side}", rig.head0[f"{b}_{side}"], rig.tail0[f"{b}_{side}"], bw) for b, bw in CHAIN_DEF[kind]]


def spine_w(Q):
    s_ = -Q[:, 1]
    a = smoothstep(-0.82, -0.62, s_)
    b = smoothstep(-0.50, -0.28, s_)
    return {"pelvis": 1 - a, "loin": a - b, "body": b}


def neck_segs(rig):
    return [("body", P(0, 0.0, 1.30), rig.head0["neck1"], 0.0), ("neck1", rig.head0["neck1"], rig.tail0["neck1"], 0.10),
            ("neck2", rig.head0["neck2"], rig.tail0["neck2"], 0.08), ("neck3", rig.head0["neck3"], rig.tail0["neck3"], 0.07),
            ("head", rig.head0["head"], rig.tail0["head"], 0.05)]


def wmix(*parts):
    """wmix((k, {bone: w}), ...) with k scalar or per-vertex arrays."""
    out = {}
    for k, d in parts:
        for b, w in d.items():
            out[b] = out.get(b, 0) + k * w
    return out


def spec_weights(rig, spec, Q):
    n = len(Q)
    one = np.ones(n)
    if isinstance(spec, str):
        return {spec: one}
    kind = spec[0]
    side = spec[1] if len(spec) > 1 else None
    z = Q[:, 2]
    if kind == "spine":
        return spine_w(Q)
    if kind == "neck":
        return chain_weights(rig, Q, neck_segs(rig))
    if kind == "fl":
        return chain_weights(rig, Q, limb_segs(rig, "fl", side))
    if kind == "hl":
        return chain_weights(rig, Q, limb_segs(rig, "hl", side))
    if kind == "thigh":
        wf = smoothstep(1.38, 1.02, z)
        return wmix((1 - wf, spine_w(Q)), (wf, chain_weights(rig, Q, limb_segs(rig, "hl", side))))
    if kind == "shoulder":
        wb = smoothstep(1.36, 1.56, z) * 0.85
        return wmix((1 - wb, chain_weights(rig, Q, limb_segs(rig, "fl", side))), (wb, {"body": one}))
    if kind == "breast":
        a = smoothstep(0.02, 0.15, np.abs(Q[:, 0])) * 0.75
        return wmix((1 - a, {"body": one}), (a, chain_weights(rig, Q, limb_segs(rig, "fl", side))))
    if kind == "elbow":
        return {f"forearm_{side}": one}
    if kind == "hock":
        wc = smoothstep(0.76, 0.62, z)
        return {f"tibia_{side}": 1 - wc, f"hcannon_{side}": wc}
    if kind == "j":
        return chain_weights(rig, Q, jockey_segs(rig, spec[1], spec[2] if len(spec) > 2 else None))
    if kind == "ear":
        segs = [("head", hp(0.0, 0.0), rig.head0[f"ear_{side}"], 0.0),
                (f"ear_{side}", rig.head0[f"ear_{side}"], rig.tail0[f"ear_{side}"], 0.015)]
        return chain_weights(rig, Q, segs)
    raise ValueError(spec)


def field_weights(rig, field, Q, tau=0.025):
    """Blend each primitive's bone weights by how close the vertex is to that primitive."""
    prims = field.prims()
    D = np.stack([p.d(Q) for p in prims], 1)
    dmin = D.min(1, keepdims=True)
    R = np.exp(-(D - dmin) / np.array([p.blend for p in prims])[None, :])
    R[R < 1e-3] = 0
    tot = R.sum(1)
    out = {}
    for i, p in enumerate(prims):
        m = R[:, i] > 0
        if not m.any():
            continue
        ws = spec_weights(rig, p.w, Q[m])
        for b, w in ws.items():
            if b not in out:
                out[b] = np.zeros(len(Q))
            out[b][m] += R[m, i] * w / tot[m]
    return out


def barrel_share(Q):
    """Fraction of the trunk weight handed to the breathing bone (ribs + belly)."""
    c = P(0, -0.22, 1.12)
    r = np.linalg.norm((Q - c) / np.array([0.40, 0.55, 0.32]), axis=1)
    return 0.55 * (1 - smoothstep(0.7, 1.05, r)) * smoothstep(1.45, 1.25, Q[:, 2])


def smooth_and_limit(obj, W, iters=3, fac=0.5, max_inf=4):
    """W: {bone: per-vertex array}. Laplacian-smooth over edges, keep top max_inf, normalise, write groups."""
    me = obj.data
    nv = len(me.vertices)
    names = sorted(W)
    M = np.stack([W[b] for b in names], 1)
    if iters:
        ed = np.array([e.vertices[:] for e in me.edges], int)
        deg = np.bincount(ed.ravel(), minlength=nv).astype(float)
        for _ in range(iters):
            acc = np.zeros_like(M)
            np.add.at(acc, ed[:, 0], M[ed[:, 1]])
            np.add.at(acc, ed[:, 1], M[ed[:, 0]])
            avg = acc / np.maximum(deg, 1)[:, None]
            M = M * (1 - fac) + avg * fac
    idx = np.argsort(-M, axis=1)[:, :max_inf]
    top = np.take_along_axis(M, idx, 1)
    top[top < 0.01] = 0
    top /= np.maximum(top.sum(1, keepdims=True), 1e-9)
    for g in list(obj.vertex_groups):
        obj.vertex_groups.remove(g)
    groups = {b: obj.vertex_groups.new(name=b) for b in names}
    for v in range(nv):
        for k in range(top.shape[1]):
            if top[v, k] > 0:
                groups[names[idx[v, k]]].add([v], float(top[v, k]), "REPLACE")


def mesh_co(obj):
    me = obj.data
    co = np.zeros(len(me.vertices) * 3)
    me.vertices.foreach_get("co", co)
    return co.reshape(-1, 3)


def mb_weights(rig, field, mb):
    """Resolve MB vertex weight specs into per-vertex dicts (arrays)."""
    n = len(mb.v)
    Q = np.array(mb.v)
    W = {}

    def put(i, d):
        for b, w in d.items():
            if b not in W:
                W[b] = np.zeros(n)
            W[b][i] += w

    mane_i = [i for i, w in enumerate(mb.vw) if isinstance(w, tuple) and w[0] == "mane"]
    if mane_i:
        neckw = chain_weights(rig, Q[mane_i], neck_segs(rig))
        for k, i in enumerate(mane_i):
            _, u, t = mb.vw[i]
            m = 0.85 * smoothstep(0.1, 0.9, t)
            # mane bones: mane3 near the poll (u = 0) ... mane1 near the withers (u = 1)
            a = smoothstep(0.25, 0.45, u)
            b = smoothstep(0.6, 0.8, u)
            put(i, {bn: (1 - m) * w[k] for bn, w in neckw.items()})
            put(i, {"mane3": m * (1 - a), "mane2": m * (a - b), "mane1": m * b})
    for i, w in enumerate(mb.vw):
        if isinstance(w, dict):
            put(i, w)
        elif isinstance(w, tuple) and w[0] == "tail":
            u = w[1]
            js = [0.06, 0.2, 0.38, 0.58, 0.8]
            S = [1.0] + [float(smoothstep(j - 0.06, j + 0.06, u)) for j in js] + [0.0]
            names = ["pelvis", "tail1", "tail2", "tail3", "tail4", "tail5"]
            put(i, {names[k]: S[k] - S[k + 1] for k in range(6)})
        elif isinstance(w, tuple) and w[0] == "field":
            put(i, {b: x[0] for b, x in field_weights(rig, field, Q[i:i + 1]).items()})
    return W


# ====================================================================== gait machinery

def rsz(deg):
    """Rotation about X that turns vectors counter-clockwise in the (s, z) plane (raises the forward end)."""
    return Matrix.Rotation(-math.radians(deg), 4, "X")


def sz_angle(v):
    """Angle (deg) of a Blender vector in the (s, z) plane, s = -y."""
    return math.degrees(math.atan2(v[2], -v[1]))


def sz_dir(a):
    a = math.radians(a)
    return np.array([0.0, -math.cos(a), math.sin(a)])


class Loop:
    """Periodic cubic Hermite (Catmull-Rom with time-aware tangents) through (phase, value) keys on [0, 1)."""

    def __init__(self, keys):
        keys = sorted(((k[0] % 1.0, np.atleast_1d(np.asarray(k[1], float))) for k in keys), key=lambda k: k[0])
        self.t = [k[0] for k in keys]
        self.v = [k[1] for k in keys]
        n = len(keys)
        self.m = []
        for i in range(n):
            tp = self.t[(i + 1) % n] + (1.0 if i + 1 >= n else 0.0)
            tm = self.t[(i - 1) % n] - (1.0 if i - 1 < 0 else 0.0)
            self.m.append((self.v[(i + 1) % n] - self.v[(i - 1) % n]) / max(tp - tm, 1e-9))

    def __call__(self, ph):
        import bisect
        n = len(self.t)
        if n == 1:
            return self.v[0].copy()
        ph = ph % 1.0
        i = bisect.bisect_right(self.t, ph) - 1
        if i < 0:
            i, t0, j, t1 = n - 1, self.t[n - 1] - 1.0, 0, self.t[0]
        else:
            t0 = self.t[i]
            j = (i + 1) % n
            t1 = self.t[j] + (1.0 if j == 0 else 0.0)
        h = max(t1 - t0, 1e-9)
        u = (ph - t0) / h
        u2, u3 = u * u, u * u * u
        return (self.v[i] * (2 * u3 - 3 * u2 + 1) + self.m[i] * h * (u3 - 2 * u2 + u)
                + self.v[j] * (-2 * u3 + 3 * u2) + self.m[j] * h * (u3 - u2))


def wave(ph, keys):
    return float(Loop(keys)(ph)[0])


LEG = {
    "f": dict(root="scap", segs=["humerus", "forearm", "fcannon", "fpastern", "fhoof"],
              # joints between consecutive segs: (ref rest rel, lo, hi)
              lim=[(-15, 125), (-150, 4), (-75, 95), (-40, 40)]),
    "h": dict(root="pelvis", segs=["femur", "tibia", "hcannon", "hpastern", "hhoof"],
              lim=[(-130, -25), (5, 130), (-75, 95), (-40, 40)]),
}


def chain_fk(p0, angs, lens):
    pts = [np.asarray(p0, float)]
    for a, L in zip(angs, lens):
        pts.append(pts[-1] + sz_dir(a) * L)
    return pts


def solve_leg(p0, lens, a_init, toe, a_hoof, refs, wrefs, lims, couple=None, iters=40):
    """Planar IK: absolute angles of the first 4 segments so that the hoof (5th segment, fixed angle a_hoof)
    ends at toe; joint relative angles pulled towards refs (weights wrefs) and kept inside lims."""
    a = np.array(a_init[:4], float)

    def resid(a):
        full = list(a) + [a_hoof]
        pts = chain_fk(p0, full, lens)
        r = [(pts[-1][1] - toe[1]) * 60.0, (pts[-1][2] - toe[2]) * 60.0]
        rel = [full[k + 1] - full[k] for k in range(4)]
        for k in range(4):
            if refs[k] is not None:
                r.append((rel[k] - refs[k]) * wrefs[k] / 30.0)
            lo, hi = lims[k]
            r.append(max(0.0, rel[k] - hi) / 2.0 + min(0.0, rel[k] - lo) / 2.0)
        if couple:
            j1, j2, k_, r1, r2 = couple
            r.append(((rel[j2] - r2) + k_ * (rel[j1] - r1)) * 0.6 / 30.0)
        return np.array(r)

    lam = 1e-3
    f = resid(a)
    for _ in range(iters):
        J = np.zeros((len(f), 4))
        for k in range(4):
            da = np.zeros(4)
            da[k] = 0.05
            J[:, k] = (resid(a + da) - f) / 0.05
        g = J.T @ f
        H = J.T @ J
        step = np.linalg.solve(H + lam * np.eye(4) * (1 + np.diag(H).max()), -g)
        a2 = a + np.clip(step, -15, 15)
        f2 = resid(a2)
        if f2 @ f2 < f @ f:
            a, f = a2, f2
            lam *= 0.5
        else:
            lam *= 4.0
        if f @ f < 1e-10:
            break
    full = list(a) + [a_hoof]
    pts = chain_fk(p0, full, lens)
    err = float(np.linalg.norm(pts[-1][1:] - np.asarray(toe)[1:]))
    return np.array(full), err


# ====================================================================== gaits

def keys(*kv):
    return [(kv[i], kv[i + 1]) for i in range(0, len(kv), 2)]


GAITS = {
    "Gallop": dict(
        frames=25, stride=7.0,
        # transverse gallop, right lead: LH, RH, LF, RF, then the gathered suspension
        legs={"hl_L": (0.00, 0.19), "hl_R": (0.10, 0.19), "fl_L": (0.29, 0.19), "fl_R": (0.43, 0.19)},
        mid={"f": 0.33, "h": -0.98},
        load={"f": 38.0, "h": 34.0},
        dz=keys(0.0, -0.03, 0.15, -0.05, 0.30, -0.05, 0.45, -0.07, 0.60, -0.04, 0.80, 0.0, 0.95, -0.02),
        dy=keys(0.0, 0.0),
        pitch=keys(0.0, -1.0, 0.15, -3.0, 0.30, -3.0, 0.45, 0.0, 0.60, 4.0, 0.80, 2.0, 0.95, 0.0),
        flex=keys(0.0, 8.0, 0.12, 2.0, 0.25, -8.0, 0.45, -4.0, 0.62, 2.0, 0.80, 10.0, 0.95, 10.0),
        neck=keys(0.0, 6.0, 0.2, 3.0, 0.4, -4.0, 0.55, -8.0, 0.7, -2.0, 0.85, 5.0),
        neck_base=(-18.0, -6.0, 4.0, 34.0),
        scap=keys(0.0, 10.0, 0.19, -14.0, 0.5, -2.0, 0.85, 12.0),
        swing={"f": [(0.12, [-150, -110, -140, -175, -190]), (0.35, [-125, -62, -185, -215, -230]),
                     (0.62, [-105, -25, -80, -70, -60]), (0.85, [-100, -45, -55, -30, -15])],
               "h": [(0.12, [-72, -150, -100, -128, -122]), (0.32, [-50, -142, -55, -100, -112]),
                     (0.60, [-35, -125, -45, -70, -70]), (0.85, [-42, -118, -72, -45, -30])]},
        tail_base=(-24.0, -12.0, -14.0, -8.0, -4.0), tail_amp=(3.0, 4.0, 5.0, 5.0, 5.0), tail_lag=0.07,
        mane=(12.0, 8.0), ears=0.0,
    ),
    "Canter": dict(
        frames=36, stride=3.6,
        # right-lead canter: LH, then the diagonal RH + LF, then RF, short suspension
        legs={"hl_L": (0.00, 0.36), "hl_R": (0.20, 0.36), "fl_L": (0.24, 0.36), "fl_R": (0.42, 0.36)},
        mid={"f": 0.28, "h": -0.92},
        load={"f": 30.0, "h": 26.0},
        dz=keys(0.0, -0.02, 0.3, -0.04, 0.55, -0.03, 0.85, 0.02),
        dy=keys(0.0, 0.0),
        pitch=keys(0.0, 3.0, 0.25, 0.0, 0.45, -4.0, 0.7, -1.0, 0.88, 3.5),
        flex=keys(0.0, 6.0, 0.3, -4.0, 0.6, 0.0, 0.85, 7.0),
        neck=keys(0.0, 6.0, 0.25, 0.0, 0.5, -7.0, 0.75, 0.0),
        neck_base=(-9.0, -3.0, 2.0, 16.0),
        scap=keys(0.0, 8.0, 0.36, -11.0, 0.65, -2.0, 0.9, 9.0),
        swing={"f": [(0.15, [-145, -105, -135, -160, -170]), (0.40, [-122, -65, -165, -192, -205]),
                     (0.70, [-108, -40, -75, -60, -50]), (0.88, [-106, -58, -64, -35, -20])],
               "h": [(0.15, [-74, -148, -104, -122, -118]), (0.40, [-52, -140, -62, -96, -106]),
                     (0.70, [-42, -128, -55, -65, -55]), (0.90, [-50, -126, -80, -50, -35])]},
        tail_base=(-16.0, -6.0, -7.0, -3.0, -1.0), tail_amp=(3.0, 4.0, 5.0, 6.0, 6.0), tail_lag=0.08,
        mane=(8.0, 6.0), ears=4.0,
    ),
    "Walk": dict(
        frames=66, stride=1.8,
        # four-beat lateral walk: LH, LF, RH, RF
        legs={"hl_L": (0.00, 0.62), "fl_L": (0.25, 0.62), "hl_R": (0.50, 0.62), "fl_R": (0.75, 0.62)},
        mid={"f": 0.30, "h": -0.93},
        load={"f": 16.0, "h": 13.0},
        dz=[(k / 8, -0.008 + 0.008 * math.cos(4 * math.pi * (k / 8 - 0.1))) for k in range(8)],
        dy=keys(0.0, 0.0),
        pitch=[(k / 8, 0.8 * math.sin(4 * math.pi * k / 8)) for k in range(8)],
        flex=[(k / 8, 2.0 * math.sin(2 * math.pi * k / 8 + 0.6)) for k in range(8)],
        neck=keys(0.0, 2.0, 0.25, -4.0, 0.5, 2.0, 0.75, -4.0),
        neck_base=(2.0, 0.0, 0.0, -2.0),
        scap=keys(0.0, 7.0, 0.62, -8.0, 0.85, 3.0),
        swing={"f": [(0.25, [-135, -95, -150, -150, -140]), (0.6, [-120, -72, -105, -85, -70]),
                     (0.9, [-121, -80, -82, -47, -33])],
               "h": [(0.25, [-66, -140, -85, -112, -112]), (0.6, [-55, -130, -70, -70, -60]),
                     (0.9, [-60, -134, -88, -55, -40])]},
        tail_base=(-6.0, 2.0, 3.0, 1.0, 0.0), tail_amp=(1.0, 1.5, 2.0, 2.5, 3.0), tail_lag=0.1,
        mane=(2.0, 1.5), ears=6.0,
        extra=lambda ph: {"roll": 1.6 * math.sin(math.tau * ph), "tail_swish": 6.0 * math.sin(math.tau * ph - 1.0)},
    ),
}


def pulse(x, a, b, c):
    """0 before a, eases up to 1 at b, back down to 0 at c."""
    return float(smoothstep(a, b, x) * (1 - smoothstep(b, c, x)))


def idle_extra(ph):
    toss = pulse(ph, 0.42, 0.48, 0.60)
    return {"breath": 0.013 * math.sin(math.tau * ph), "dz": 0.004 * math.sin(math.tau * ph),
            "ear_L": -32.0 * pulse(ph, 0.27, 0.30, 0.42) + 10.0 * pulse(ph, 0.42, 0.5, 0.6),
            "ear_turn_R": 40.0 * pulse(ph, 0.58, 0.66, 0.84),
            "neck": 9.0 * toss - 3.0 * pulse(ph, 0.58, 0.66, 0.78),
            "head": -14.0 * pulse(ph, 0.44, 0.50, 0.62),
            "head_roll": 7.0 * math.sin((ph - 0.44) / 0.16 * 3 * math.tau) * pulse(ph, 0.44, 0.5, 0.6),
            "tail_swish": 30.0 * math.sin((ph - 0.12) / 0.26 * math.tau) * pulse(ph, 0.12, 0.2, 0.38),
            "roll": -1.5 * pulse(ph, 0.62, 0.72, 0.96),
            "neck_yaw": 9.0 * pulse(ph, 0.70, 0.80, 0.97)}


GAITS["Idle"] = dict(
    frames=240, stride=0.0, stand=True,
    legs={"hl_L": (0.0, 1.0), "hl_R": (0.0, 1.0), "fl_L": (0.0, 1.0), "fl_R": (0.0, 1.0)},
    mid={"f": 0.303 - 0.0, "h": -0.956},
    load={"f": 0.0, "h": 0.0},
    beta=lambda leg, ph: (16.0 * pulse(ph, 0.62, 0.74, 0.95) if leg == "hl_R" else 0.0),
    dz=keys(0.0, 0.0), dy=keys(0.0, 0.0), pitch=keys(0.0, 0.0), flex=keys(0.0, 0.0), neck=keys(0.0, 0.0),
    neck_base=(0.0, 0.0, 0.0, 0.0), scap=keys(0.0, 0.0), swing={"f": [], "h": []},
    tail_base=(0.0, 0.0, 0.0, 0.0, 0.0), tail_amp=(0.6, 0.8, 1.0, 1.2, 1.4), tail_lag=0.1,
    mane=(0.0, 0.8), ears=4.0, extra=idle_extra,
    rider_extra=lambda ph: {"head_turn": 18.0 * pulse(ph, 0.66, 0.78, 0.95), "torso": 2.0 * math.sin(math.tau * ph)},
)

REST_ANG = {}


def rest_angles(rig):
    for side in ("L", "R"):
        for k, d in LEG.items():
            REST_ANG[(k, side)] = [sz_angle(rig.tail0[f"{b}_{side}"] - rig.head0[f"{b}_{side}"]) for b in d["segs"]]
            REST_ANG[(k + "root", side)] = sz_angle(rig.tail0[f"{d['root']}_{side}"] - rig.head0[f"{d['root']}_{side}"]) \
                if k == "f" else sz_angle(rig.tail0["pelvis"] - rig.head0["pelvis"])


def leg_lens(rig, k, side):
    return [rig.length[f"{b}_{side}"] for b in LEG[k]["segs"]]


def body_motion(g, ph):
    return dict(dz=wave(ph, g["dz"]), dy=wave(ph, g["dy"]), pitch=wave(ph, g["pitch"]), flex=wave(ph, g["flex"]),
                neck=wave(ph, g["neck"]))


def pose_trunk(rig, g, ph, extra=None):
    """Armature-space matrices for the trunk, neck, head, tail, mane and scapulae (no leg segments)."""
    m = body_motion(g, ph)
    if extra:
        for k_, v_ in extra(ph).items():
            m[k_] = m.get(k_, 0.0) + v_
    Pm = {"root": rig.rest["root"].copy()}
    piv = V(tuple(rig.head0["body"]))
    Mb = Matrix.Translation(V((0, -m["dy"], m["dz"])) + piv) @ rsz(m["pitch"]) @ Matrix.Translation(-piv)
    if "roll" in m:
        Mb = Matrix.Translation(piv) @ Matrix.Rotation(math.radians(m["roll"]), 4, "Y") @ Matrix.Translation(-piv) @ Mb
    if "sway" in m:
        Mb = Matrix.Translation(V((m["sway"], 0, 0))) @ Mb
    Pm["body"] = Mb @ rig.rest["body"]
    br = 1.0 + m.get("breath", 0.0)
    Pm["barrel"] = Pm["body"] @ rig.local_rest("barrel") @ Matrix.Diagonal((br, 1.0 + 0.3 * (br - 1), br, 1.0))
    Pm["loin"] = Pm["body"] @ rig.local_rest("loin") @ rsz(m["flex"] * 0.4)
    Pm["pelvis"] = Pm["loin"] @ rig.local_rest("pelvis") @ rsz(m["flex"] * 0.6)
    nb = g["neck_base"]
    share = (0.5, 0.3, 0.2)
    yaw = m.get("neck_yaw", 0.0)
    for k in range(3):
        R = rsz(nb[k] + m["neck"] * share[k])
        if yaw:
            R = Matrix.Rotation(math.radians(yaw / 3), 4, "Z") @ R
        Pm[f"neck{k + 1}"] = Pm["body" if k == 0 else f"neck{k}"] @ rig.local_rest(f"neck{k + 1}") @ R
    Rh = rsz(nb[3] - m["neck"] * 0.35 + m.get("head", 0.0))
    if m.get("head_roll"):
        Rh = Rh @ Matrix.Rotation(math.radians(m["head_roll"]), 4, "Y")
    Pm["head"] = Pm["neck3"] @ rig.local_rest("head") @ Rh
    for sd, sx in (("L", 1), ("R", -1)):
        ear = g["ears"] + m.get(f"ear_{sd}", 0.0)
        Pm[f"ear_{sd}"] = Pm["head"] @ rig.local_rest(f"ear_{sd}") @ rsz(ear) @ \
            Matrix.Rotation(math.radians(m.get(f"ear_turn_{sd}", 0.0)) * sx, 4, "Y")
    a0, a1 = g["mane"]
    for k in range(3):
        roll = a0 + a1 * math.sin(math.tau * (2 * ph) + k * 1.3)
        Pm[f"mane{k + 1}"] = Pm[f"neck{k + 1}"] @ rig.local_rest(f"mane{k + 1}") @ Matrix.Rotation(math.radians(roll), 4, "Y")
    par = "pelvis"
    for k in range(5):
        a = g["tail_base"][k] + g["tail_amp"][k] * math.sin(math.tau * (ph - g["tail_lag"] * k))
        sw = m.get("tail_swish", 0.0) * (k + 1) / 5
        R = rsz(a)
        if sw:
            R = Matrix.Rotation(math.radians(sw), 4, "Z") @ R
        Pm[f"tail{k + 1}"] = Pm[par] @ rig.local_rest(f"tail{k + 1}") @ R
        par = f"tail{k + 1}"
    return Pm, m


def leg_phase(g, leg, ph):
    on, duty = g["legs"][leg]
    lam = (ph - on) % 1.0
    return lam, duty


def gait_frames(rig, g, extra=None):
    """All per-frame armature-space poses for one gait (horse only). Returns list of dicts + slip report."""
    n = g["frames"]
    T = n / 60.0
    stride = g["stride"]
    trunk = []
    for f in range(n):
        ph = f / n
        Pm, m = pose_trunk(rig, g, ph, extra or g.get("extra"))
        trunk.append((Pm, m))
    legs_out = {}
    report = {}
    for leg in ("fl_L", "fl_R", "hl_L", "hl_R"):
        k = leg[0]
        side = leg[-1]
        lens = leg_lens(rig, k, side)
        on, duty = g["legs"][leg]
        rest_a = REST_ANG[(k, side)]
        lims = LEG[k]["lim"]
        rel0 = [rest_a[j + 1] - rest_a[j] for j in range(4)]
        s_mid = g["mid"][k]
        s_land = s_mid + duty * stride / 2
        toe_x = rig.tail0[f"{LEG[k]['segs'][-1]}_{side}"][0]
        knots = []
        exact = {}
        prev = None
        worst = 0.0
        for f in range(n):
            ph = f / n
            lam = (ph - on) % 1.0
            if lam >= duty - 1e-9:
                continue
            Pm, m = trunk[f]
            psi = m["pitch"] + (m["flex"] if k == "h" else 0.0)
            if k == "f":
                Pm_s = Pm["body"] @ rig.local_rest(f"scap_{side}") @ rsz(wave(lam, g["scap"]))
                p0 = np.array(Pm_s @ V((0, rig.length[f"scap_{side}"], 0)))
            else:
                p0 = np.array(Pm["pelvis"] @ rig.local_rest(f"femur_{side}").translation)
            tau = lam / duty
            sg = s_land - lam * stride
            if g.get("stand"):
                sg = -rig.tail0[f"{LEG[k]['segs'][-1]}_{side}"][1]
            toe = P(toe_x, sg, 0.0)
            if g.get("stand"):
                beta = g["beta"](leg, ph)
                load = -0.4 * beta
            else:
                beta = -6.0 * (1 - smoothstep(0.0, 0.12, tau)) + 28.0 * smoothstep(0.62, 1.0, tau)
                load = g["load"][k] * math.sin(math.pi * min(1.0, tau * 1.1))
            a_hoof = rest_a[4] - beta
            refs = [None, 0.0 if k == "f" else None, rel0[2] + load, None]
            wrefs = [0.0, 3.0, 2.0, 0.0]
            if k == "f":
                refs[0] = rel0[0]
                wrefs[0] = 0.15
            couple = (0, 1, 1.0, rel0[0], rel0[1]) if k == "h" else None
            init = prev if prev is not None else [a + psi for a in rest_a]
            A, err = solve_leg(p0, lens, init, toe, a_hoof, refs, wrefs, lims, couple)
            prev = A
            worst = max(worst, err)
            exact[f] = A - psi
            knots.append((lam, A - psi))
        for sig, ang in g["swing"][k]:
            knots.append((duty + sig * (1 - duty), np.array(ang, float)))
        spl = Loop(knots) if len(knots) > 1 else None
        per = []
        for f in range(n):
            lam = (f / n - on) % 1.0
            per.append(exact[f] if f in exact else spl(lam))
        legs_out[leg] = per
        report[leg] = worst
    frames = []
    for f in range(n):
        Pm, m = trunk[f]
        Pm = dict(Pm)
        for leg in ("fl_L", "fl_R", "hl_L", "hl_R"):
            k = leg[0]
            side = leg[-1]
            on, duty = g["legs"][leg]
            lam = (f / n - on) % 1.0
            psi = m["pitch"] + (m["flex"] if k == "h" else 0.0)
            A = legs_out[leg][f] + psi
            if k == "f":
                Pm[f"scap_{side}"] = Pm["body"] @ rig.local_rest(f"scap_{side}") @ rsz(wave(lam, g["scap"]))
                p0 = np.array(Pm[f"scap_{side}"] @ V((0, rig.length[f"scap_{side}"], 0)))
            else:
                p0 = np.array(Pm["pelvis"] @ rig.local_rest(f"femur_{side}").translation)
            pts = chain_fk(p0, A, leg_lens(rig, k, side))
            for j, b in enumerate(LEG[k]["segs"]):
                bn = f"{b}_{side}"
                R = rig.rest[bn].to_3x3().to_4x4()
                Pm[bn] = Matrix.Translation(V(tuple(pts[j]))) @ rsz(A[j] - REST_ANG[(k, side)][j]) @ R
        frames.append(Pm)
    return frames, report


RIDE = {
    # seat = pelvis centre (horse rest space); follow = share of the horse's trunk motion the pelvis takes;
    # torso/neck/headup = degrees forward of vertical; hands = wrist target on a horse bone (rest space)
    "Gallop": dict(seat=P(0, -0.31, 1.80), follow=0.28, torso=76, bend=14, neck=60, headup=6,
                   hands=(P(0.10, 0.37, 1.77), "neck1"), rock=0.02, rock_ph=0.5, pitch_follow=0.3, pump=0.035),
    "Canter": dict(seat=P(0, -0.24, 1.77), follow=0.45, torso=58, bend=10, neck=40, headup=4,
                   hands=(P(0.11, 0.32, 1.76), "neck1"), rock=0.025, rock_ph=0.4, pitch_follow=0.5, pump=0.03),
    "Walk": dict(seat=P(0, -0.21, 1.69), follow=1.0, torso=12, bend=4, neck=12, headup=2,
                 hands=(P(0.13, 0.13, 1.76), "body"), rock=0.01, rock_ph=0.0, pitch_follow=1.0),
    "Idle": dict(seat=P(0, -0.21, 1.685), follow=1.0, torso=8, bend=3, neck=8, headup=0,
                 hands=(P(0.13, 0.12, 1.75), "body"), rock=0.0, rock_ph=0.0, pitch_follow=1.0),
}


def add_rider(rig, g, frames, name, extra=None):
    R = RIDE[name]
    extra = extra or g.get("rider_extra")
    n = len(frames)
    rb_inv = rig.rest["body"].inverted()
    atts = []
    for Pm in frames:
        Bw = Pm["body"] @ rb_inv
        atts.append(np.array(Bw @ V(tuple(R["seat"]))))
    mean = np.mean(atts, 0)
    out = []
    for fi, Pm in enumerate(frames):
        ph = fi / n
        Bw = Pm["body"] @ rb_inv
        pitch = math.degrees(math.atan2(-(Bw.to_3x3() @ V((0, -1, 0)))[2], 1.0)) * -1
        fwd = Bw.to_3x3() @ V((0, -1, 0))
        pitch = math.degrees(math.atan2(fwd[2], -fwd[1]))
        pel = mean + (atts[fi] - mean) * R["follow"] + P(0, R["rock"] * math.sin(math.tau * (ph - R["rock_ph"])), 0)
        ex = extra(ph) if extra else {}
        pel = pel + ex.get("pel", 0.0)
        torso = R["torso"] - pitch * R["pitch_follow"] + ex.get("torso", 0.0)
        hb = R["hands"][1]
        Hm = Pm[hb] @ rig.rest[hb].inverted()
        wr = {}
        nk = wave(ph, g["neck"])
        pump = Hm.to_3x3() @ V((0, -1, 0)) * (-R.get("pump", 0.0) * nk / 8.0)
        for sd, sx in (("L", 1), ("R", -1)):
            hp_ = R["hands"][0] * [sx, 1, 1]
            wr[sd] = np.array(Hm @ V(tuple(hp_)) + pump) + ex.get("hand_" + sd, 0.0)
        ank = {sd: np.array(Bw @ V(tuple(STIRRUP[sd]))) for sd in ("L", "R")}
        q = rider(pel, torso, R["bend"], R["neck"] - pitch * 0.2 + ex.get("neck", 0.0),
                  R["headup"] + ex.get("head", 0.0), wr, ankles=ank)
        for sd in ("L", "R"):
            q["foot_" + sd] = np.array(Bw.to_3x3() @ V(tuple(q["foot_" + sd])))
        J = jockey_joints(q)
        Pm = dict(Pm)
        for b, h_, t_, par in jockey_bonelist(J):
            M = frame_x(h_, t_ - h_)
            if b == "j_head" and ex.get("head_turn"):
                M = M @ Matrix.Rotation(math.radians(ex["head_turn"]), 4, "Y")
            Pm[b] = M
        out.append(Pm)
    return out


def contact_sheet(paths, cols, out, scale=0.5):
    imgs = []
    for p_ in paths:
        im = bpy.data.images.load(p_)
        w, h = im.size
        a = np.array(im.pixels[:], np.float32).reshape(h, w, 4)
        step = int(round(1 / scale))
        imgs.append(a[::step, ::step])
        bpy.data.images.remove(im)
    h, w = imgs[0].shape[:2]
    rows = (len(imgs) + cols - 1) // cols
    sheet = np.ones((rows * h, cols * w, 4), np.float32)
    for i, a in enumerate(imgs):
        r, c = divmod(i, cols)
        sheet[(rows - 1 - r) * h:(rows - r) * h, c * w:(c + 1) * w] = a
    im = bpy.data.images.new("sheet", cols * w, rows * h, alpha=True)
    im.pixels = sheet.ravel()
    im.filepath_raw = out
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    for p_ in paths:
        os.remove(p_)
    log("sheet", os.path.relpath(out))


# ====================================================================== jockey

JL = dict(pel=0.10, spine=0.18, chest=0.21, neck=0.10, head=0.21, ua=0.27, fa=0.245, hand=0.085,
          thigh=0.39, shin=0.375, foot=0.17, sh_w=0.17, hip_w=0.085)


def two_bone(S, W, a, b, pole):
    """Middle joint for root S, end target W, lengths a, b, bending towards pole. Returns (M, W_reached)."""
    S, W, pole = np.asarray(S, float), np.asarray(W, float), np.asarray(pole, float)
    d_vec = W - S
    d = np.linalg.norm(d_vec)
    u = d_vec / max(d, 1e-9)
    d = min(max(d, abs(a - b) + 1e-4), a + b - 1e-4)
    ca = (a * a + d * d - b * b) / (2 * a * d)
    sa = math.sqrt(max(0.0, 1 - ca * ca))
    pv = pole - S
    v = pv - u * (pv @ u)
    v = v / max(np.linalg.norm(v), 1e-9)
    return S + (u * ca + v * sa) * a, S + u * d


def jockey_joints(q):
    """Joint positions from a rider pose q (dict). Lengths are exact, so the same code makes bind + poses."""
    Pc, ut = np.asarray(q["pel"], float), unit(q["up"])
    fn = unit(np.cross(XL, ut))            # belly side
    fn = -fn if fn[1] > 0 else fn          # faces forward (-Y)
    J = {"pel": Pc}
    J["lum"] = Pc + ut * JL["pel"]
    uc = unit(np.array(Matrix.Rotation(-math.radians(q.get("bend", 8.0)), 3, "X") @ V(tuple(ut))))
    J["chest"] = J["lum"] + ut * JL["spine"]
    J["nbase"] = J["chest"] + uc * JL["chest"]
    J["hbase"] = J["nbase"] + unit(q["neck"]) * JL["neck"]
    J["crown"] = J["hbase"] + unit(q["headup"]) * JL["head"]
    J["uc"], J["ut"], J["fn"] = uc, ut, fn
    for sd, sx in (("L", 1), ("R", -1)):
        sh = J["nbase"] - uc * 0.045 + XL * JL["sh_w"] * sx + fn * -0.01
        wr = np.asarray(q["wrist_" + sd], float)
        el, wr2 = two_bone(sh, wr, JL["ua"], JL["fa"], (sh + wr) / 2 + np.asarray(q["epole"]) * [sx, 1, 1])
        J["sh_" + sd], J["el_" + sd], J["wr_" + sd] = sh, el, wr2
        J["kn_" + sd + "_dummy"] = None
        J["hd_" + sd] = wr2 + unit(q["hand_" + sd]) * JL["hand"]
        hip = Pc + XL * JL["hip_w"] * sx - ut * 0.02 + fn * 0.01
        an = np.asarray(q["ankle_" + sd], float)
        kn, an2 = two_bone(hip, an, JL["thigh"], JL["shin"], (hip + an) / 2 + np.asarray(q["kpole"]) * [sx, 1, 1])
        J["hip_" + sd], J["kn_" + sd], J["an_" + sd] = hip, kn, an2
        J["toe_" + sd] = an2 + unit(q["foot_" + sd]) * JL["foot"]
    return J


def jockey_bonelist(J):
    """[(name, head, tail, parent)] for the rider (parented under the horse's body bone)."""
    B = [("j_pelvis", J["pel"], J["lum"], "body"), ("j_spine", J["lum"], J["chest"], "j_pelvis"),
         ("j_chest", J["chest"], J["nbase"], "j_spine"), ("j_neck", J["nbase"], J["hbase"], "j_chest"),
         ("j_head", J["hbase"], J["crown"], "j_neck")]
    for sd in ("L", "R"):
        B += [(f"j_upperarm_{sd}", J["sh_" + sd], J["el_" + sd], "j_chest"),
              (f"j_forearm_{sd}", J["el_" + sd], J["wr_" + sd], f"j_upperarm_{sd}"),
              (f"j_hand_{sd}", J["wr_" + sd], J["hd_" + sd], f"j_forearm_{sd}"),
              (f"j_thigh_{sd}", J["hip_" + sd], J["kn_" + sd], "j_pelvis"),
              (f"j_shin_{sd}", J["kn_" + sd], J["an_" + sd], f"j_thigh_{sd}"),
              (f"j_foot_{sd}", J["an_" + sd], J["toe_" + sd], f"j_shin_{sd}")]
    return B


def tilt(deg_from_vertical):
    a = math.radians(deg_from_vertical)
    return P(0, math.sin(a), math.cos(a))


STIRRUP = {"L": P(0.325, -0.09, 1.29), "R": P(-0.325, -0.09, 1.29)}


def rider(pel, torso, bend, neck, headup, wrists, ankles=None, foot=(0.16, -0.05), hand=(0.75, -0.66)):
    q = dict(pel=pel, up=tilt(torso), bend=bend, neck=tilt(neck), headup=tilt(headup),
             epole=P(0.30, -0.30, -0.25), kpole=P(0.12, 0.6, 0.05))
    for sd, sx in (("L", 1), ("R", -1)):
        q["wrist_" + sd] = wrists[sd]
        an = (ankles or STIRRUP)[sd]
        q["ankle_" + sd] = an
        q["foot_" + sd] = P(0.02 * sx, foot[0], foot[1])
        q["hand_" + sd] = P(0.0, hand[0], hand[1])
    return q


BIND_RIDER = rider(P(0, -0.22, 1.745), 45, 8, 30, 8, {"L": P(0.115, 0.36, 1.72), "R": P(-0.115, 0.36, 1.72)})


def jockey_field(J):
    f = Field()
    ut, uc, fn = J["ut"], J["uc"], J["fn"]
    A_t = np.array([XL, -fn, ut])  # lateral, back, up
    A_c = np.array([XL, unit(np.cross(uc, XL)), uc])
    # pelvis + breeches seat, abdomen, chest (with body protector), shoulders
    f.add(Ell(J["pel"] + ut * 0.01, (0.150, 0.105, 0.11), A_t), k=0.04, w=("j", "spine"))
    f.add(RCone(J["pel"] + ut * 0.06, J["chest"] + ut * 0.04, 0.115, 0.125, squash=(fn, 0.78)), k=0.05, w=("j", "spine"))
    f.add(Ell(J["chest"] + uc * 0.09 + fn * 0.01, (0.155, 0.115, 0.15), A_c), k=0.06, w=("j", "spine"))
    for sd in ("L", "R"):
        f.add(Ell(J["sh_" + sd], (0.05, 0.055, 0.05)), k=0.05, w=("j", "arm", sd))
    # neck + head (face looks forward along -Y)
    f.add(RCone(J["nbase"] - uc * 0.02, J["hbase"] + unit(J["crown"] - J["hbase"]) * 0.02, 0.052, 0.045), k=0.03, w=("j", "spine"))
    hu = unit(J["crown"] - J["hbase"])
    hf = unit(np.cross(XL, hu))
    hf = -hf if hf[1] > 0 else hf
    hc = J["hbase"] + hu * 0.10 + hf * 0.015
    A_h = np.array([XL, hf, hu])
    f.add(Ell(hc, (0.074, 0.095, 0.112), A_h), k=0.03, w=("j", "spine"))
    f.add(Ell(hc + hf * 0.085 - hu * 0.035, (0.045, 0.03, 0.06), A_h), k=0.025, w=("j", "spine"))   # face/jaw
    f.add(Ell(hc + hf * 0.10 - hu * 0.005, (0.012, 0.02, 0.022), A_h), k=0.01, w=("j", "spine"))   # nose
    for sd, sx in (("L", 1), ("R", -1)):
        f.add(Ell(hc + XL * 0.075 * sx - hf * 0.005, (0.012, 0.025, 0.03), A_h), k=0.01, w=("j", "spine"))  # ears
        # arms: silk sleeves are loose
        f.add(RCone(J["sh_" + sd], J["el_" + sd], 0.050, 0.042), k=0.035, w=("j", "arm", sd))
        f.add(RCone(J["el_" + sd], J["wr_" + sd], 0.041, 0.032), k=0.03, w=("j", "arm", sd))
        hd = unit(J["hd_" + sd] - J["wr_" + sd])
        A_f = np.array([XL, unit(np.cross(hd, XL)), hd])
        f.add(Ell(J["wr_" + sd] + hd * 0.045, (0.036, 0.048, 0.055), A_f), k=0.02, w=("j", "arm", sd))
        # legs
        f.add(RCone(J["hip_" + sd] + ut * 0.02, J["kn_" + sd], 0.082, 0.052), k=0.04, w=("j", "leg", sd))
        f.add(RCone(J["kn_" + sd], J["an_" + sd], 0.052, 0.036), k=0.025, w=("j", "leg", sd))
        fd = unit(J["toe_" + sd] - J["an_" + sd])
        f.add(RCone(J["an_" + sd] - fd * 0.06 - P(0, 0, 0.035), J["toe_" + sd] - P(0, 0, 0.02), 0.038, 0.03),
              k=0.025, w=("j", "leg", sd))
    return f


def jockey_segs(rig, which, side=None):
    def seg(b, bw):
        return (b, rig.head0[b], rig.tail0[b], bw)
    if which == "spine":
        return [seg("j_pelvis", 0.0), seg("j_spine", 0.07), seg("j_chest", 0.07), seg("j_neck", 0.035),
                seg("j_head", 0.03)]
    if which == "arm":
        return [("j_chest", rig.head0["j_chest"] * 0.0 + (rig.head0["j_chest"] + rig.tail0["j_chest"]) / 2,
                 rig.head0[f"j_upperarm_{side}"], 0.0),
                seg(f"j_upperarm_{side}", 0.05), seg(f"j_forearm_{side}", 0.045), seg(f"j_hand_{side}", 0.025)]
    if which == "leg":
        return [("j_pelvis", rig.head0["j_pelvis"], rig.head0[f"j_thigh_{side}"], 0.0),
                seg(f"j_thigh_{side}", 0.06), seg(f"j_shin_{side}", 0.05), seg(f"j_foot_{side}", 0.03)]


def jockey_material(rig, Q):
    """Region per point (bind pose): silks / breeches / boots / skin."""
    segs = [(b, rig.head0[b], rig.tail0[b]) for b in rig.order if b.startswith("j_")]
    n = len(Q)
    best = np.full(n, np.inf)
    bi = np.zeros(n, int)
    bt = np.zeros(n)
    for k, (b, h, t) in enumerate(segs):
        ab = t - h
        tt = np.clip(((Q - h) @ ab) / (ab @ ab), 0, 1)
        d = np.linalg.norm(Q - (h + np.outer(tt, ab)), axis=1)
        m = d < best
        best[m], bi[m], bt[m] = d[m], k, tt[m]
    out = []
    for k, t in zip(bi, bt):
        b = segs[k][0]
        if b in ("j_head",):
            m = "jockey_skin"
        elif b == "j_neck":
            m = "jockey_skin" if t > 0.3 else "jockey_silks"
        elif b in ("j_spine", "j_chest"):
            m = "jockey_silks"
        elif b == "j_pelvis":
            m = "jockey_silks" if t > 0.55 else "jockey_breeches"
        elif b.startswith("j_upperarm"):
            m = "jockey_silks"
        elif b.startswith("j_forearm"):
            m = "jockey_silks" if t < 0.93 else "jockey_skin"
        elif b.startswith("j_hand"):
            m = "jockey_skin"
        elif b.startswith("j_thigh"):
            m = "jockey_breeches"
        elif b.startswith("j_shin"):
            m = "jockey_breeches" if t < 0.16 else "jockey_boots"
        else:
            m = "jockey_boots"
        out.append(m)
    return out


def cut_iso(obj, vals, snap=0.12):
    """Split the mesh exactly along vals == 0 (vals: per-vertex list). Returns the per-vertex values after the cut."""
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    val = {v: vals[v.index] for v in bm.verts}
    for e in list(bm.edges):
        a, b = e.verts
        sa, sb = val[a], val[b]
        if (sa < 0) == (sb < 0) or sa == 0 or sb == 0:
            continue
        t = sa / (sa - sb)
        if t < snap:
            val[a] = 0.0
            continue
        if t > 1 - snap:
            val[b] = 0.0
            continue
        ne, nv = bmesh.utils.edge_split(e, a, t)
        val[nv] = 0.0
    for f in list(bm.faces):
        on = [lp.vert for lp in f.loops if val[lp.vert] == 0.0]
        if len(on) != 2:
            continue
        v1, v2 = on
        if any(v2 is e.other_vert(v1) for e in v1.link_edges if e in f.edges):
            continue
        sides = [val[lp.vert] for lp in f.loops if val[lp.vert] != 0.0]
        if not sides or all(x > 0 for x in sides) or all(x < 0 for x in sides):
            continue
        try:
            bmesh.utils.face_split(f, v1, v2)
        except Exception:
            pass
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    bm.verts.index_update()
    out = [0.0] * len(bm.verts)
    for v in bm.verts:
        out[v.index] = val[v]
    bm.to_mesh(me)
    bm.free()
    me.update()
    return out


def nearest_bone(rig, Q, names):
    best = np.full(len(Q), np.inf)
    bi = np.zeros(len(Q), int)
    bt = np.zeros(len(Q))
    for k, b in enumerate(names):
        h, t = rig.head0[b], rig.tail0[b]
        ab = t - h
        tt = np.clip(((Q - h) @ ab) / (ab @ ab), 0, 1)
        d = np.linalg.norm(Q - (h + np.outer(tt, ab)), axis=1)
        m = d < best
        best[m], bi[m], bt[m] = d[m], k, tt[m]
    return bi, bt


def seam_values(rig, J, Q):
    """Signed values whose zero lines are the clothing seams (waist, collar, cuffs, boot tops)."""
    names = [b for b in rig.order if b.startswith("j_")]
    bi, bt = nearest_bone(rig, Q, names)
    nb = np.array(names)[bi]
    out = {}
    waist = J["pel"] + J["ut"] * 0.055
    v = (Q - waist) @ J["ut"]
    torso = np.isin(nb, ["j_pelvis", "j_spine", "j_chest"])
    out["waist"] = np.where(torso, v, np.where(np.char.startswith(nb, "j_thigh") | np.char.startswith(nb, "j_shin")
                                               | np.char.startswith(nb, "j_foot"), -1.0, 1.0))
    un = unit(J["hbase"] - J["nbase"])
    cp = J["nbase"] + un * 0.035
    v = (Q - cp) @ un
    near = np.isin(nb, ["j_neck", "j_chest", "j_head"])
    out["collar"] = np.where(near, v, np.where(nb == "j_head", 1.0, -1.0))
    for sd in ("L", "R"):
        el, wr = J["el_" + sd], J["wr_" + sd]
        ax = unit(wr - el)
        v = (Q - (el + (wr - el) * 0.93)) @ ax
        near = np.isin(nb, [f"j_forearm_{sd}", f"j_hand_{sd}"])
        out["cuff_" + sd] = np.where(near, v, -1.0)
        kn, an = J["kn_" + sd], J["an_" + sd]
        ax = unit(an - kn)
        v = (Q - (kn + (an - kn) * 0.16)) @ ax
        near = np.isin(nb, [f"j_thigh_{sd}", f"j_shin_{sd}"])
        out["boot_" + sd] = np.where(near, v, np.where(nb == f"j_foot_{sd}", 1.0, -1.0))
    return out, nb


def jockey_mesh(rig, J, mats):
    f = jockey_field(J)
    pts = np.array([v for k, v in J.items() if isinstance(v, np.ndarray) and v.shape == (3,) and k not in ("ut", "uc", "fn")])
    lo, hi = pts.min(0) - 0.13, pts.max(0) + 0.13
    o = polygonise(f, "jockey", lo, hi, 0.006, 3050)
    for key in ("waist", "collar", "cuff_L", "cuff_R", "boot_L", "boot_R"):
        vals, _ = seam_values(rig, J, mesh_co(o))
        cut_iso(o, list(vals[key]))
    me = o.data
    for p_ in me.polygons:
        p_.use_smooth = True
    names = ["jockey_silks", "jockey_breeches", "jockey_boots", "jockey_skin"]
    for n in names:
        me.materials.append(mats[n])
    cen = np.zeros(len(me.polygons) * 3)
    me.polygons.foreach_get("center", cen)
    cen = cen.reshape(-1, 3)
    sv, nb = seam_values(rig, J, cen)
    reg = []
    for k, b in enumerate(nb):
        if b == "j_head":
            m = "jockey_skin"
        elif b in ("j_neck", "j_chest", "j_spine"):
            m = "jockey_skin" if sv["collar"][k] > 0 else "jockey_silks"
        elif b == "j_pelvis":
            m = "jockey_silks" if sv["waist"][k] > 0 else "jockey_breeches"
        elif b.startswith("j_upperarm"):
            m = "jockey_silks"
        elif b.startswith("j_forearm"):
            m = "jockey_skin" if sv["cuff_" + b[-1]][k] > 0 else "jockey_silks"
        elif b.startswith("j_hand"):
            m = "jockey_skin"
        elif b.startswith("j_thigh"):
            m = "jockey_breeches"
        elif b.startswith("j_shin"):
            m = "jockey_boots" if sv["boot_" + b[-1]][k] > 0 else "jockey_breeches"
        else:
            m = "jockey_boots"
        reg.append(m)
    me.polygons.foreach_set("material_index", [names.index(r) for r in reg])
    # silks UVs: torso cylinder (u around from the spine, v waist -> collar), sleeves (u around, v shoulder -> cuff)
    co = mesh_co(o)
    uvl = me.uv_layers.new(name="UVMap")
    rgl = me.uv_layers.new(name="SilkRegion")
    waist = J["pel"] + J["ut"] * 0.055
    ax = unit(J["nbase"] - waist)
    tl = np.linalg.norm(J["nbase"] - waist)
    back = -J["fn"]
    back = unit(back - ax * (back @ ax))
    left = unit(np.cross(ax, back))
    if left[0] < 0:
        left = -left
    segs = {sd: (J["sh_" + sd], J["wr_" + sd]) for sd in ("L", "R")}
    for poly in me.polygons:
        if reg[poly.index] != "jockey_silks":
            for li in poly.loop_indices:
                uvl.data[li].uv = (0.0, 0.0)
                rgl.data[li].uv = (0.0, 0.0)
            continue
        c = cen[poly.index]
        region = 0
        for k, sd in enumerate(("L", "R")):
            a, b = segs[sd]
            ab = b - a
            t = ((c - a) @ ab) / (ab @ ab)
            dd = np.linalg.norm(c - (a + ab * np.clip(t, 0, 1)))
            dt = np.linalg.norm((c - waist) - ax * ((c - waist) @ ax))
            if t > 0.02 and dd < dt * 0.9 + 0.01:
                region = k + 1
        uvs = []
        for vi in poly.vertices:
            q = co[vi]
            if region == 0:
                r = q - waist
                v = np.clip((r @ ax) / tl, 0, 1)
                r = r - ax * (r @ ax)
                u = (math.atan2(r @ left, r @ back) / math.tau) % 1.0
            else:
                a, b = segs["L" if region == 1 else "R"]
                axa = unit(b - a)
                r = q - a
                v = np.clip((r @ axa) / np.linalg.norm(b - a), 0, 1)
                r = r - axa * (r @ axa)
                upr = unit(np.array([0, 0, 1.0]) - axa * axa[2])
                sid = unit(np.cross(axa, upr))
                u = (math.atan2(r @ sid, r @ upr) / math.tau) % 1.0
            uvs.append([u, v])
        us = [x[0] for x in uvs]
        if max(us) - min(us) > 0.5:
            for x in uvs:
                if x[0] < 0.5:
                    x[0] += 1.0
        for li, x in zip(poly.loop_indices, uvs):
            uvl.data[li].uv = (x[0], x[1])
            rgl.data[li].uv = (float(region), 0.0)
    uvl.active_render = True
    me.uv_layers.active = uvl
    return o, f


def jockey_gear(mb, J):
    """Helmet cap (with peak), goggles, whip."""
    hu = unit(J["crown"] - J["hbase"])
    hf = unit(np.cross(XL, hu))
    hf = -hf if hf[1] > 0 else hf
    hc = J["hbase"] + hu * 0.10 + hf * 0.015
    cc = hc + hu * 0.03
    rl, rf, ru = 0.095, 0.118, 0.098
    nseg, nrow = 16, 6
    rows, uvr = [], []
    for r in range(nrow):
        row, uvrow = [], []
        for k in range(nseg + 1):
            U = k / nseg
            az = U * math.tau            # 0 = back, quarter = left, half = front
            rim = -0.42 + 0.50 * (1 - math.cos(az)) / 2
            V = r / nrow
            el = rim + (math.pi / 2 - rim) * V
            d = -hf * math.cos(az) + XL * math.sin(az)
            pnt = cc + (-hf * rf * math.cos(az) + XL * rl * math.sin(az)) * math.cos(el) + hu * ru * math.sin(el)
            if k < nseg:
                row.append(mb.add(pnt, {"j_head": 1.0}))
            uvrow.append((U, V))
        rows.append(row)
        uvr.append(uvrow)
    crown = mb.add(cc + hu * ru, {"j_head": 1.0})
    for r in range(nrow - 1):
        for k in range(nseg):
            k2 = (k + 1) % nseg
            mb.face([rows[r][k2], rows[r][k], rows[r + 1][k], rows[r + 1][k2]], "jockey_cap",
                    [uvr[r][k + 1], uvr[r][k], uvr[r + 1][k], uvr[r + 1][k + 1]])
    for k in range(nseg):
        k2 = (k + 1) % nseg
        mb.face([rows[-1][k2], rows[-1][k], crown], "jockey_cap",
                [uvr[-1][k + 1], uvr[-1][k], ((k + 0.5) / nseg, 1.0)])
    # inner rim lip so the brim reads as a shell edge from below
    lip = [mb.add(cc + (mb.v[rows[0][k]] - cc) * 0.9 - hu * 0.004, {"j_head": 1.0}) for k in range(nseg)]
    for k in range(nseg):
        k2 = (k + 1) % nseg
        mb.face([rows[0][k], rows[0][k2], lip[k2], lip[k]], "jockey_cap", [(k / nseg, 0), ((k + 1) / nseg, 0),
                                                                          ((k + 1) / nseg, 0), (k / nseg, 0)])
    # peak (visor): flat flap at the front rim
    pk_o, pk_i = [], []
    for j in range(7):
        U = 0.38 + 0.24 * j / 6
        az = U * math.tau
        rim = -0.42 + 0.50 * (1 - math.cos(az)) / 2
        base = cc + (-hf * rf * math.cos(az) + XL * rl * math.sin(az)) * math.cos(rim) + hu * ru * math.sin(rim)
        out = base + hf * 0.055 * math.sin(math.pi * j / 6) ** 0.7 - hu * 0.012 * math.sin(math.pi * j / 6)
        pk_o.append((mb.add(base, {"j_head": 1.0}), mb.add(out, {"j_head": 1.0}), U))
        pk_i.append((mb.add(base - hu * 0.006, {"j_head": 1.0}), mb.add(out - hu * 0.006, {"j_head": 1.0})))
    for j in range(6):
        (b0, o0, u0), (b1, o1, u1) = pk_o[j], pk_o[j + 1]
        mb.face([b0, b1, o1, o0], "jockey_cap", [(u0, 0.0), (u1, 0.0), (u1, 0.04), (u0, 0.04)])
        (c0, p0), (c1, p1) = pk_i[j], pk_i[j + 1]
        mb.face([c1, c0, p0, p1], "jockey_cap", [(u1, 0.0), (u0, 0.0), (u0, 0.04), (u1, 0.04)])
        mb.face([o0, o1, p1, p0], "jockey_cap", [(u0, 0.04)] * 4)
    # goggles: lens band in front of the eyes, strap round the helmet
    for (ra, rb, h, z0, a0, a1, wd) in ((0.083, 0.112, 0.036, -0.012, 0.30, 0.70, 0.0),
                                        (0.100, 0.124, 0.018, 0.012, -0.30, 0.30, 0.0)):
        top, bot = [], []
        n = 9
        for j in range(n):
            U = a0 + (a1 - a0) * j / (n - 1)
            az = U * math.tau
            pnt = hc + hu * z0 + (-hf * rb * math.cos(az) + XL * ra * math.sin(az))
            top.append(mb.add(pnt + hu * h / 2, {"j_head": 1.0}))
            bot.append(mb.add(pnt - hu * h / 2, {"j_head": 1.0}))
        for j in range(n - 1):
            mb.face([bot[j], bot[j + 1], top[j + 1], top[j]], "jockey_goggles")
            mb.face([top[j], top[j + 1], bot[j + 1], bot[j]], "jockey_goggles")
    # whip: tapered rod from the right fist down the horse's shoulder + popper
    hand = J["wr_R"] + unit(J["hd_R"] - J["wr_R"]) * 0.045
    d = unit(P(-0.30, -0.20, -0.93))
    a1v = unit(np.cross(d, XL))
    a2v = np.cross(d, a1v)
    rings = []
    for j, (t, r) in enumerate(((-0.1, 0.009), (0.0, 0.008), (0.3, 0.006), (0.56, 0.004))):
        c = hand + d * t
        rings.append([mb.add(c + (a1v * math.cos(k / 6 * math.tau) + a2v * math.sin(k / 6 * math.tau)) * r,
                             {"j_hand_R": 1.0}) for k in range(6)])
    mb.grid(rings, "jockey_boots", closed=True, flip=True)
    mb.fan(rings[0], mb.add(hand - d * 0.11, {"j_hand_R": 1.0}), "jockey_boots", flip=False)
    tip = hand + d * 0.56
    pq = [tip + a1v * 0.016, tip + a1v * 0.016 + d * 0.07, tip - a1v * 0.016 + d * 0.07, tip - a1v * 0.016]
    ids = [mb.add(x, {"j_hand_R": 1.0}) for x in pq]
    mb.face(ids, "jockey_boots")
    mb.face(ids[::-1], "jockey_boots")


# ====================================================================== clips, AO, export

def write_clip(rig, name, frames, scale_bones=("barrel",)):
    from bpy_extras import anim_utils
    arm = rig.obj
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    slot = act.slots.new(id_type="OBJECT", name=arm.name)
    cb = anim_utils.action_ensure_channelbag_for_slot(act, slot)
    n = len(frames)
    keys_ = {b: [] for b in rig.order}
    prevq = {}
    for f_ in range(n + 1):
        bas = rig.basis(frames[f_ % n])
        for b in rig.order:
            loc, q, sc = bas[b].decompose()
            if b in prevq and q.dot(prevq[b]) < 0:
                q = -q
            prevq[b] = q
            keys_[b].append((f_, q, loc, sc))
    lin = bpy.types.Keyframe.bl_rna.properties["interpolation"].enum_items["LINEAR"].value
    for b in rig.order:
        ks = keys_[b]
        if ks[-1][1].dot(ks[0][1]) > 0:
            ks[-1] = (ks[-1][0], ks[0][1], ks[0][2], ks[0][3])
        chans = [("rotation_quaternion", 4, lambda k, i: k[1][i]), ("location", 3, lambda k, i: k[2][i])]
        if b in scale_bones:
            chans.append(("scale", 3, lambda k, i: k[3][i]))
        for prop, cnt, get in chans:
            for i in range(cnt):
                fc = cb.fcurves.new(f'pose.bones["{b}"].{prop}', index=i, group_name=b)
                fc.keyframe_points.add(len(ks))
                co = []
                for k in ks:
                    co += [k[0], get(k, i)]
                fc.keyframe_points.foreach_set("co", co)
                fc.keyframe_points.foreach_set("interpolation", [lin] * len(ks))
                fc.update()
    ad = arm.animation_data or arm.animation_data_create()
    track = ad.nla_tracks.new()
    track.name = name
    strip = track.strips.new(name, 0, act)
    strip.name = name
    try:
        strip.action_slot = slot
    except Exception:
        pass
    track.mute = True
    return act


def play(rig, name, frame):
    ad = rig.obj.animation_data
    act = bpy.data.actions[name]
    ad.action = act
    try:
        ad.action_slot = act.slots[0]
    except Exception:
        pass
    bpy.context.scene.frame_set(int(frame))
    bpy.context.view_layer.update()


def unplay(rig):
    if rig.obj.animation_data:
        rig.obj.animation_data.action = None
    for pb in rig.obj.pose.bones:
        pb.location, pb.rotation_quaternion, pb.scale = (0, 0, 0), (1, 0, 0, 0), (1, 1, 1)
    bpy.context.view_layer.update()


def coat_material():
    m = bk.mat("horse_coat", "#808080", rough=0.55)
    nt = m.node_tree
    pr = nt.nodes["Principled BSDF"]
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    sock = lambda socks, ident: next(x for x in socks if x.identifier == ident)  # noqa: E731
    sock(mix.inputs, "Factor_Float").default_value = 1.0
    sock(mix.inputs, "A_Color").default_value = bk.hex_lin("#808080")
    attr = nt.nodes.new("ShaderNodeVertexColor")
    attr.layer_name = "Color"
    nt.links.new(attr.outputs["Color"], sock(mix.inputs, "B_Color"))
    nt.links.new(sock(mix.outputs, "Result_Color"), pr.inputs["Base Color"])
    return m


def bake_ao(obj, samples=192, dist=0.32, floor=0.22):
    s = bpy.context.scene
    s.render.engine = "CYCLES"
    pr = bpy.context.preferences.addons["cycles"].preferences
    pr.compute_device_type = "CUDA"
    pr.get_devices()
    for d in pr.devices:
        d.use = d.type != "CPU"
    s.cycles.device = "GPU"
    s.cycles.samples = samples
    s.world.light_settings.distance = dist
    me = obj.data
    ca = me.color_attributes.get("Color") or me.color_attributes.new("Color", "FLOAT_COLOR", "POINT")
    me.color_attributes.active_color = ca
    try:
        me.color_attributes.render_color_index = me.color_attributes.active_color_index
    except Exception:
        pass
    hidden = []
    for o in s.objects:
        if o is not obj and o.type in ("MESH", "CURVE") and not o.hide_render:
            o.hide_render = True
            hidden.append(o)
    bk.select([obj])
    t = time.time()
    bpy.ops.object.bake(type="AO", target="VERTEX_COLORS")
    for o in hidden:
        o.hide_render = False
    n = len(me.vertices)
    col = np.zeros(n * 4)
    ca.data.foreach_get("color", col)
    col = col.reshape(-1, 4)
    a = np.clip(col[:, 0], 0, 1)
    a = floor + (1 - floor) * a ** 1.15
    col[:, 0] = col[:, 1] = col[:, 2] = a
    col[:, 3] = 1.0
    ca.data.foreach_set("color", col.ravel())
    s.render.engine = "BLENDER_EEVEE"
    log(f"AO baked in {time.time() - t:.1f}s: min {a.min():.2f} mean {a.mean():.2f}")


def export(path, objs):
    path = os.path.abspath(path)
    for o in objs:
        if o.type == "MESH":
            o.data.validate(clean_customdata=False)
    bk.select(objs)
    bpy.ops.export_scene.gltf(
        filepath=path, export_format="GLB", use_selection=True, export_apply=False, export_yup=True,
        export_animations=True, export_animation_mode="NLA_TRACKS", export_force_sampling=False,
        export_vertex_color="MATERIAL", export_all_vertex_colors=False,
        export_meshopt_compression_enable=True, export_skins=True, export_influence_nb=4,
        export_def_bones=False, export_leaf_bone=False, export_optimize_animation_size=True,
        export_reset_pose_bones=True, export_rest_position_armature=True, export_texcoords=True,
        export_normals=True, export_tangents=False, export_extras=False, export_lights=False,
        export_cameras=False, export_materials="EXPORT")
    log(f"exported {os.path.relpath(path)} ({os.path.getsize(path) / 1024:.0f} KB)")


def three(v):
    """Blender (x, y, z) -> three.js (x, z, -y)."""
    return [round(float(v[0]), 4), round(float(v[2]), 4), round(float(-v[1]), 4)]


# ====================================================================== preview staging

def look(name, loc, target, lens=50.0, ortho=None):
    cd = bpy.data.cameras.get(name) or bpy.data.cameras.new(name)
    cd.lens = lens
    cd.sensor_width = 36
    cd.clip_start, cd.clip_end = 0.05, 200
    if ortho:
        cd.type = "ORTHO"
        cd.ortho_scale = ortho
    o = bpy.data.objects.get(name) or bpy.data.objects.new(name, cd)
    if o.name not in bpy.context.scene.collection.objects:
        bpy.context.scene.collection.objects.link(o)
    o.location = V(loc)
    o.rotation_mode = "QUATERNION"
    o.rotation_quaternion = (V(target) - V(loc)).to_track_quat("-Z", "Y")
    bpy.context.scene.camera = o
    return o


def stage_lights():
    s = bpy.context.scene
    w = s.world or bpy.data.worlds.new("World")
    s.world = w
    bg = w.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = bk.hex_lin("#9fb3c8")
    bg.inputs["Strength"].default_value = 0.55

    def lamp(name, kind, energy, loc, target, size=None, color="#ffffff"):
        ld = bpy.data.lights.get(name) or bpy.data.lights.new(name, kind)
        ld.energy = energy
        ld.color = bk.hex_lin(color)[:3]
        if size:
            if kind == "AREA":
                ld.size = size
            else:
                ld.angle = math.radians(size)
        o = bpy.data.objects.get(name) or bpy.data.objects.new(name, ld)
        if o.name not in s.collection.objects:
            s.collection.objects.link(o)
        o.location = V(loc)
        o.rotation_mode = "QUATERNION"
        o.rotation_quaternion = (V(target) - V(loc)).to_track_quat("-Z", "Y")

    lamp("sun", "SUN", 3.2, (4, 2.5, 6), (0, 0, 0.8), size=2, color="#fff1dc")
    lamp("fill", "AREA", 260, (-4, -3, 2.5), (0, 0, 1.0), size=4, color="#dfe9ff")
    lamp("rim", "AREA", 300, (-1, 5, 3), (0, 0, 1.2), size=3)
    if "ground" not in bpy.data.objects:
        g = bpy.data.meshes.new("ground")
        g.from_pydata([(-30, -30, 0), (30, -30, 0), (30, 30, 0), (-30, 30, 0)], [], [(0, 1, 2, 3)])
        go = bpy.data.objects.new("ground", g)
        s.collection.objects.link(go)
        g.materials.append(bk.mat("_ground", "#b89a74", rough=0.95))
    s.render.engine = "BLENDER_EEVEE"
    s.eevee.taa_render_samples = 32
    s.render.resolution_x, s.render.resolution_y = 1280, 900
    s.render.resolution_percentage = 100
    s.view_settings.view_transform = "AgX"
    try:
        s.eevee.use_shadows = True
    except Exception:
        pass


def render(path):
    s = bpy.context.scene
    s.render.image_settings.file_format = "PNG"
    s.render.filepath = os.path.abspath(path)
    bpy.ops.render.render(write_still=True)
    log("render", os.path.relpath(path))


VIEWS = {
    "side": dict(loc=(9.0, 0.0, 1.0), target=(0, 0.0, 1.0), ortho=3.2),
    "bside": dict(loc=(9.0, 0.05, 1.18), target=(0, 0.05, 1.18), ortho=3.6),
    "front34": dict(loc=(4.2, -5.2, 2.0), target=(0, -0.1, 1.0), lens=50),
    "rear34": dict(loc=(4.0, 5.4, 2.1), target=(0, 0.2, 1.0), lens=50),
    "front": dict(loc=(0.0, -9.0, 1.1), target=(0, 0, 1.1), ortho=2.6),
    "rear": dict(loc=(0.0, 9.0, 1.1), target=(0, 0, 1.1), ortho=2.6),
    "top": dict(loc=(0.0, 0.0, 9.0), target=(0, 0.0001, 0), ortho=3.3),
    "head": dict(loc=(1.6, -2.3, 2.0), target=(0, -0.95, 1.7), lens=50),
    "rside": dict(loc=(-9.0, 0.0, 1.0), target=(0, 0.0, 1.0), ortho=3.2),
    "rhead": dict(loc=(-1.7, -2.2, 2.1), target=(0, -0.75, 1.7), lens=50),
}


def shot(name, view, **kw):
    v = dict(VIEWS[view])
    v.update(kw)
    look("cam", v["loc"], v["target"], lens=v.get("lens", 50), ortho=v.get("ortho"))
    if not v.get("ortho"):
        bpy.data.cameras["cam"].type = "PERSP"
    render(os.path.join(PREV, f"{name}.png"))


MATS = [("horse_coat", "#7a7a7a", 0.55, 0.0), ("horse_hair", "#2b2420", 0.6, 0.0), ("horse_hoof", "#3a3430", 0.45, 0.0),
        ("horse_eye", "#0d0a08", 0.08, 0.0), ("tack", "#4a2e1c", 0.5, 0.0), ("tack_metal", "#c9ccd0", 0.3, 1.0),
        ("saddlecloth", "#f2f2ee", 0.8, 0.0), ("jockey_silks", "#c8202c", 0.45, 0.0),
        ("jockey_cap", "#f0c419", 0.45, 0.0), ("jockey_breeches", "#f4f4f0", 0.7, 0.0),
        ("jockey_boots", "#141414", 0.35, 0.0), ("jockey_skin", "#c99272", 0.55, 0.0),
        ("jockey_goggles", "#202428", 0.15, 0.3)]


# ====================================================================== main

def main():
    bk.reset()
    s = bpy.context.scene
    s.render.fps = 60
    coat = coat_material()
    f = horse_field()
    lo, hi = horse_box()
    body = polygonise(f, "horse_body", lo, hi, 0.008, 7600)
    body.data.materials.append(coat)
    mats = {n: bk.mat(n, c, rough=r, metal=m) for n, c, r, m in MATS}
    import random
    rng = random.Random(11)
    mb = MB()
    hooves(mb)
    eyes(mb)
    mane(mb, f, rng)
    tail(mb, rng)
    extras = mb.build("horse_parts", mats)
    log("extras", bk.tris([extras]), "tris")
    stage_lights()
    if STAGE == "shape":
        for vname in ("side", "front34", "rear34", "front", "head", "rside", "rhead"):
            shot(f"shape_{vname}", vname)
        return
    rig = Rig("horse_rig")
    for name, h_, t_, par, dfm in horse_bones():
        rig.add(name, h_, t_, par, dfm)
    JB = jockey_joints(BIND_RIDER)
    for name, h_, t_, par in jockey_bonelist(JB):
        rig.add(name, h_, t_, par, True)
    rig.build()
    log(f"bones: {len(rig.order)}")
    jockey, jfield = jockey_mesh(rig, JB, mats)
    jmb = MB()
    jockey_gear(jmb, JB)
    jgear = jmb.build("jockey_gear", mats)
    log("jockey", bk.tris([jockey]), "+ gear", bk.tris([jgear]), "tris")
    _FW["fn"] = lambda q: {b: float(x[0]) for b, x in field_weights(rig, f, np.array([q])).items() if x[0] > 0.01}
    tmb = MB()
    tack(tmb, f, JB)
    tackobj = tmb.build("tack", mats)
    log("tack", bk.tris([tackobj]), "tris")
    rest_angles(rig)
    t = time.time()
    W = field_weights(rig, f, mesh_co(body))
    W["barrel"] = W.get("body", 0) * barrel_share(mesh_co(body))
    W["body"] = W["body"] - W["barrel"]
    smooth_and_limit(body, W, iters=3)
    smooth_and_limit(extras, mb_weights(rig, f, mb), iters=0)
    smooth_and_limit(jockey, field_weights(rig, jfield, mesh_co(jockey)), iters=2)
    smooth_and_limit(jgear, mb_weights(rig, f, jmb), iters=0)
    smooth_and_limit(tackobj, mb_weights(rig, f, tmb), iters=0)
    for o in (body, extras, jockey, jgear, tackobj):
        o.parent = rig.obj
        md = o.modifiers.new("Armature", "ARMATURE")
        md.object = rig.obj
    log(f"weights in {time.time() - t:.1f}s")
    if STAGE == "rig":
        for vname in ("side", "front34", "head", "rhead"):
            shot(f"rig_{vname}", vname)
        g = GAITS["Gallop"]
        frames, rep = gait_frames(rig, g)
        frames = add_rider(rig, g, frames, "Gallop")
        log("gallop slip (m):", {k: round(v, 3) for k, v in rep.items()})
        paths = []
        for fi in range(0, g["frames"], 2):
            rig.apply_pose(frames[fi])
            look("cam", (9.0, 0.05, 1.0), (0, 0.05, 1.0), ortho=4.0)
            pth = os.path.join(PREV, f"_g{fi:02d}.png")
            render(pth)
            paths.append(pth)
        contact_sheet(paths, 5, os.path.join(PREV, "gallop_sheet.png"), scale=0.5)
        for fi, nm in ((15, "ffold"), (21, "gathered"), (4, "hpush")):
            rig.apply_pose(frames[fi])
            look("cam", (3.2, -2.6, 1.3), (0, 0.0, 0.8), lens=45)
            bpy.data.cameras["cam"].type = "PERSP"
            render(os.path.join(PREV, f"close_{nm}.png"))
        return

    # ---------------------------------------------------------------- full build
    clips = {}
    for name in ("Gallop", "Canter", "Walk", "Idle"):
        g = GAITS[name]
        frames, rep = gait_frames(rig, g)
        frames = add_rider(rig, g, frames, name)
        write_clip(rig, name, frames)
        clips[name] = g
        log(f"clip {name}: {g['frames']} frames, max hoof slip {max(rep.values()):.3f} m")
    unplay(rig)
    bake_ao(body)
    objs = [rig.obj, body, extras, tackobj, jockey, jgear]
    for o in objs[1:]:
        for p_ in o.data.polygons:
            p_.use_smooth = True
    export(OUT + ".glb", objs)
    tris = bk.tris(objs[1:])

    # ---- sidecar json (three.js space: x = horse's left, y = up, z = forward)
    co = mesh_co(body)
    sfw = -co[:, 1]
    m = (np.abs(co[:, 0]) < 0.05) & (sfw > -0.25) & (sfw < 0.15)
    withers = float(co[m, 2].max())
    head_m = sfw > 0.6
    muz = co[head_m][np.argmax(sfw[head_m])]
    pm = (sfw > 0.78) & (sfw < 0.95) & (np.abs(co[:, 0]) < 0.03)
    poll = float(co[pm, 2].max())
    bw = (co[:, 2] > 0.9) & (co[:, 2] < 1.5) & (sfw > -0.75) & (sfw < 0.15)
    half = float(np.abs(co[bw, 0]).max())
    JL_ = leg_joints(1)
    eye = hp(0.13, 0.036, 0.091)
    info = {
        "trisTotal": int(tris), "bones": len(rig.order), "facing": "+Z",
        "units": "metres; y up; x = horse's left side; origin on the ground under the girth",
        "clips": {
            "Gallop": {"duration": round(25 / 60, 4), "strideLength": 7.0, "fps": 60,
                       "footfalls": "transverse gallop, right lead: LH 0.00, RH 0.10, LF 0.29, RF 0.43 (of the cycle), "
                                    "suspension 0.62-1.00"},
            "Canter": {"duration": round(36 / 60, 4), "strideLength": 3.6, "fps": 60,
                       "footfalls": "right lead: LH 0.00, RH 0.20 + LF 0.24, RF 0.42, suspension 0.78-1.00"},
            "Walk": {"duration": round(66 / 60, 4), "strideLength": 1.8, "fps": 60,
                     "footfalls": "LH 0.00, LF 0.25, RH 0.50, RF 0.75"},
            "Idle": {"duration": 4.0, "fps": 60},
        },
        "landmarks": {
            "withersY": round(withers, 4),
            "kneeY": round(float(JL_["knee"][2]), 4),
            "hockY": round(float(JL_["hock"][2]), 4),
            "fetlockY": round(float(JL_["ffet"][2]), 4),
            "hindFetlockY": round(float(JL_["hfet"][2]), 4),
            "coronetY": 0.077,
            "muzzle": three(muz * [0, 1, 1]),
            "eye": three(eye),
            "pollY": round(poll, 4),
            "tailRoot": three(P(0, TAIL_PATH[0][0], TAIL_PATH[0][1])),
            "girthZ": [-0.107, -0.043],
            "frontHoofZ": round(0.303 - 0.068, 4),
            "hindHoofZ": round(-0.956 - 0.064, 4),
            "bodyHalfWidth": round(half, 4),
            "frontLegX": 0.13, "hindLegX": 0.13,
            "notes": "y values are bind-pose heights of joint centres; girthZ = the girth strap's band along z; "
                     "hoof Z = centre of the ground footprint; legs at x = +-0.13",
        },
        "uv": {
            "saddlecloth": "Two side panels, each with its own uv in [0,1]^2, upright and unmirrored as seen from "
                           "that side: v = 0 at the bottom hem, 1 at the spine; u runs left-to-right for the viewer "
                           "(left panel x>0: u grows towards the tail; right panel: towards the head). The saddle "
                           "flap and the rider's boot cover roughly v > 0.35 for u < 0.6 (left) / u > 0.4 (right); "
                           "a race number reads well centred at about (0.80, 0.42) on the left panel and "
                           "(0.20, 0.42) on the right.",
            "jockey_silks": "TEXCOORD_0 (three.js 'uv'): torso = cylinder round the spine, u = 0 at the back "
                            "centre, 0.25 left side, 0.5 chest centre, 0.75 right side, v = 0 at the waist to 1 at "
                            "the collar. Sleeves: u round the arm (0 = top of the arm), v = 0 at the shoulder seam to "
                            "1 at the cuff. Torso and sleeves each span [0,1]^2; TEXCOORD_1 ('uv1') .x tells them "
                            "apart: 0 = torso, 1 = left sleeve, 2 = right sleeve.",
            "jockey_cap": "u round the head (0 = back, 0.25 = left, 0.5 = front over the peak, 0.75 = right), "
                          "v = 0 at the brim to 1 at the crown button; the peak (visor) uses v in [0, 0.04].",
        },
        "meshes": {"horse_body": "coat only, COLOR_0 = baked AO (greyscale)",
                   "horse_parts": "hooves, eyes, mane, forelock, tail",
                   "tack": "saddlecloth, saddle, girth, stirrup leathers + irons, bridle, bit, reins",
                   "jockey": "rider body (silks, breeches, boots, skin)",
                   "jockey_gear": "cap cover, goggles, whip (whip uses jockey_boots)"},
        "materials": [n for n, *_ in MATS],
    }
    with open(OUT + ".json", "w") as fh:
        json.dump(info, fh, indent=2)
    log("json", json.dumps(info["landmarks"]))

    # ---- previews (EEVEE): rest views, gallop phases, canter, walk, idle
    shot("rest_side", "bside")
    for vname in ("front34", "rear34"):
        shot(f"rest_{vname}", vname)
    bcam = dict(loc=(6.5, -2.2, 1.6), target=(0, -0.15, 1.0), lens=40)
    for nm, fr in (("gallop_1_hind_landing", 1), ("gallop_2_extended", 6), ("gallop_3_fore_landing", 8),
                   ("gallop_4_gathered", 21)):
        play(rig, "Gallop", fr)
        shot(nm, "bside")
        look("cam", bcam["loc"], bcam["target"], lens=bcam["lens"])
        bpy.data.cameras["cam"].type = "PERSP"
        render(os.path.join(PREV, nm + "_34.png"))
    for nm, clip, fr in (("canter_diagonal", "Canter", 9), ("walk", "Walk", 20), ("idle_toss", "Idle", 118)):
        play(rig, clip, fr)
        shot(nm, "bside")
        look("cam", bcam["loc"], bcam["target"], lens=bcam["lens"])
        bpy.data.cameras["cam"].type = "PERSP"
        render(os.path.join(PREV, nm + "_34.png"))
    unplay(rig)
    for o in [o for o in bpy.context.scene.objects if o.type in ("CAMERA", "LIGHT") or o.name == "ground"]:
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "horse.blend"))
    log("saved", os.path.relpath(os.path.join(HERE, "horse.blend")), "| tris", tris, "| bones", len(rig.order))

main()
