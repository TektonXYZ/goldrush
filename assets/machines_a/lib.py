"""machines-A shared hard-surface kit (MOTHERLODE). Run machine scripts through `bl`, which puts bk on the path.

Geometry is authored in MACHINE SPACE (Blender metres, Z up, front = -Y = three.js +Z, origin at floor centre).
A `Part` collects primitives for ONE mesh object. Each primitive is built in its own small bmesh, bevelled there
(per-primitive width), UV'd in metres (box or cylindrical projection in the primitive's own frame), transformed,
then appended to flat arrays, so a machine with thousands of parts builds in seconds.

    m = Machine("cm12")
    body = m.part("cm12_body")
    body.box((3.3, 2.0, 0.6), c=(0, 0, 0.5), mat="paint_yellow")
    drum = m.part("drum", origin=(0, -3.1, 0.62), parent="boom")
    ...
    m.finish()          # meshes, weighted normals, grime bake
    m.clip("Work", 4.0, solve)   # solve(t) -> {obj_name: (loc, quat, scale)}
    m.export(stem); m.render(views)
"""
import json
import math
import os
import random
import subprocess
import sys
from contextlib import contextmanager

import bmesh
import bpy
from mathutils import Euler, Matrix, Quaternion, Vector, noise
from mathutils.bvhtree import BVHTree

import bk
import time
import traceback
from collections import Counter

TRISTAT = Counter()
_T0 = [time.time()]


def tick(label):
    now = time.time()
    print(f"[time] {label}: {now - _T0[0]:.1f}s")
    _T0[0] = now


HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.abspath(os.path.join(HERE, "..", ".."))
PREVIEWS = os.path.join(HERE, "previews")
DECALS = os.path.join(HERE, "decals")
FPS = 30
LIMITS = (5.6, 7.6, 3.9)  # W (x), L (y), H (z) for depth 1-3 alcoves

V = Vector


def R(rx=0.0, ry=0.0, rz=0.0):
    """Rotation matrix from XYZ Euler degrees (4x4)."""
    return Euler((math.radians(rx), math.radians(ry), math.radians(rz)), "XYZ").to_matrix().to_4x4()


def T(x, y=None, z=None):
    if y is None:
        x, y, z = x
    return Matrix.Translation((x, y, z))


def aim(d, up="Y"):
    """Quaternion turning local +Z onto direction d."""
    return V(d).normalized().to_track_quat("Z", up)


def frame(zdir, xhint=(1, 0, 0)):
    """Quaternion with local +Z along zdir and local +X as close as possible to xhint (stable roll)."""
    z = V(zdir).normalized()
    x = V(xhint)
    x = x - z * x.dot(z)
    if x.length < 1e-6:
        x = z.orthogonal()
    x.normalize()
    y = z.cross(x)
    return Matrix((x, y, z)).transposed().to_quaternion()


def lerp(a, b, t):
    return a + (b - a) * t


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


# ---------------------------------------------------------------- materials
# Preview approximations of the game's material library (src/core/materials.ts replaces them BY NAME at load).
LIB = {
    "paint_yellow": ("#E8B400", 0.42, 0.0), "paint_orange": ("#E06A10", 0.45, 0.0), "paint_red": ("#A3201A", 0.45, 0.0),
    "paint_white": ("#D9D7D0", 0.5, 0.0), "paint_black": ("#1D1E20", 0.5, 0.0), "paint_green": ("#2F5A34", 0.5, 0.0),
    "paint_blue": ("#1F4E8C", 0.45, 0.0), "paint_grey": ("#6E7174", 0.5, 0.0),
    "steel": ("#8E9296", 0.36, 1.0), "steel_dark": ("#34363A", 0.48, 0.85), "galvanized": ("#A8ACAE", 0.5, 1.0),
    "chrome": ("#E9EBED", 0.07, 1.0), "rust": ("#6E3A20", 0.85, 0.2), "cast_iron": ("#3C3D3F", 0.72, 0.7),
    "copper": ("#B5653A", 0.35, 1.0), "brass": ("#C49A45", 0.32, 1.0), "gold": ("#F2C14E", 0.2, 1.0),
    "aluminium": ("#C2C6CA", 0.4, 1.0),
    "rubber": ("#161616", 0.86, 0.0), "hose_red": ("#9C1E16", 0.58, 0.0), "hose_yellow": ("#D9A300", 0.55, 0.0),
    "cable": ("#121212", 0.62, 0.0), "plastic_black": ("#1A1A1A", 0.5, 0.0), "plastic_yellow": ("#E3B21A", 0.45, 0.0),
    "wood_timber": ("#8A6A45", 0.85, 0.0), "wood_planks": ("#7C6650", 0.85, 0.0), "wood_dark": ("#4A3526", 0.8, 0.0),
    "canvas": ("#8C7F62", 0.9, 0.0), "glass": ("#D6E6EC", 0.04, 0.0), "glass_dark": ("#2A3034", 0.08, 0.0),
    "coal_ore": ("#111214", 0.22, 0.0), "rock_dark": ("#2C2B2A", 0.8, 0.0), "dirt": ("#4A3C2E", 0.95, 0.0),
    "emit_warm": ("#FFB45E", 0.4, 0.0), "emit_white": ("#F2F6FF", 0.3, 0.0), "emit_red": ("#FF2A1A", 0.4, 0.0),
    "emit_amber": ("#FF9A1A", 0.4, 0.0), "emit_green": ("#3BFF6A", 0.4, 0.0),
    "leather": ("#5A3B26", 0.7, 0.0),
    "gravel": ("#77706A", 0.92, 0.0), "gold_ore": ("#B9A77E", 0.5, 0.1), "rock": ("#6E6A64", 0.85, 0.0),
    "rock_pale": ("#A8A399", 0.8, 0.0), "rock_red": ("#7A4A3A", 0.85, 0.0), "iron_ore": ("#6A3B2C", 0.8, 0.1),
    "silver_ore": ("#9AA0A6", 0.5, 0.3), "concrete": ("#8C8A85", 0.9, 0.0), "corrugated": ("#8A8F92", 0.5, 0.8),
    "wood_painted_red": ("#8A2A20", 0.7, 0.0), "wood_painted_white": ("#D8D4CA", 0.7, 0.0),
    "wood_painted_green": ("#2E5A3A", 0.7, 0.0),
}
EMIT = {"emit_warm": 6.0, "emit_white": 9.0, "emit_red": 5.0, "emit_amber": 5.0, "emit_green": 4.0}
CLEAN = {"glass", "glass_dark", "chrome", *EMIT}  # grime forced to clean on these


def material(name):
    m = bpy.data.materials.get(name)
    if m is not None:
        return m
    col, rough, metal = LIB.get(name, ("#FF00FF", 0.5, 0.0))
    if name in EMIT:
        m = bk.mat(name, col, rough=rough, metal=metal, emit=col, emit_strength=EMIT[name])
    elif name == "glass":
        m = bk.mat(name, col, rough=rough, metal=0.0, alpha=0.18)
    else:
        m = bk.mat(name, col, rough=rough, metal=metal)
    m["base"] = list(bk.hex_lin(col))
    return m


def grime_preview(on=True):
    """Multiply the baked COLOR_0 grime into base colour for Blender previews (stripped again before export)."""
    for m in bpy.data.materials:
        if m.name.startswith(("label_", "_bk")) or m.name in EMIT or m.name == "glass" or "base" not in m:
            continue
        nt = m.node_tree
        p = nt.nodes.get("Principled BSDF")
        for n in [n for n in nt.nodes if n.name.startswith("grime_")]:
            nt.nodes.remove(n)
        if not on:
            p.inputs["Base Color"].default_value = m["base"]
            continue
        a = nt.nodes.new("ShaderNodeVertexColor")
        a.name = "grime_attr"
        a.layer_name = "grime"
        mx = nt.nodes.new("ShaderNodeMix")
        mx.name = "grime_mix"
        mx.data_type = "RGBA"
        mx.blend_type = "MULTIPLY"
        mx.inputs["Factor"].default_value = 1.0
        mx.inputs[6].default_value = m["base"]
        nt.links.new(a.outputs["Color"], mx.inputs[7])
        nt.links.new(mx.outputs[2], p.inputs["Base Color"])


# ---------------------------------------------------------------- part builder

def _box_uv(bm, uvl):
    for f in bm.faces:
        n = f.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        for lp in f.loops:
            c = lp.vert.co
            if ax == 0:
                lp[uvl].uv = (c.y if n.x > 0 else -c.y, c.z)
            elif ax == 1:
                lp[uvl].uv = (-c.x if n.y > 0 else c.x, c.z)
            else:
                lp[uvl].uv = (c.x, c.y if n.z > 0 else -c.y)


def _cyl_uv(bm, uvl, rad):
    for f in bm.faces:
        if abs(f.normal.z) > 0.75:
            for lp in f.loops:
                lp[uvl].uv = (lp.vert.co.x, lp.vert.co.y)
            continue
        angs = [math.atan2(lp.vert.co.y, lp.vert.co.x) for lp in f.loops]
        if max(angs) - min(angs) > math.pi:
            angs = [a + math.tau if a < 0 else a for a in angs]
        for lp, a in zip(f.loops, angs):
            lp[uvl].uv = (a * rad, lp.vert.co.z)


def _auto_bev(dims):
    return max(0.0025, min(0.022, 0.12 * min(dims)))


def _detail(dims, bev, segs):
    """Detail-aware bevel budget: tiny parts get none, small parts a 1-segment chamfer (only ever downgrades)."""
    mn, mx = min(dims), max(dims)
    if not bev or mx < 0.05 or mn < 0.005:
        return 0.0, 1
    if mn < 0.04 or mx < 0.16:
        return bev, 1
    return bev, segs


class Part:
    """Accumulates primitives for one mesh object. Coordinates are machine space unless inside `with p.at(...)`."""

    def __init__(self, machine, name, origin=(0, 0, 0), parent=None):
        self.m, self.name, self.origin, self.parent = machine, name, V(origin), parent
        self.V, self.F, self.UV, self.FM, self.mats = [], [], [], [], []
        self.stack = [Matrix.Identity(4)]
        self.obj = None
        self.place = None  # (loc, quat): rest transform for parts authored around their own origin
        self.sharp = 46.0  # edges sharper than this stay hard (lower = more faceted, e.g. coal)

    # ------------------------------------------------------------ transform stack
    @contextmanager
    def at(self, loc=(0, 0, 0), rot=(0, 0, 0), q=None, mirror_x=False):
        M = T(V(loc)) @ (q.to_matrix().to_4x4() if q is not None else R(*rot))
        if mirror_x:
            M = Matrix.Diagonal((-1, 1, 1, 1)) @ M
        self.stack.append(self.stack[-1] @ M)
        try:
            yield self
        finally:
            self.stack.pop()

    @contextmanager
    def mirrored(self):
        """Everything inside is mirrored across X=0 (in the current frame)."""
        self.stack.append(self.stack[-1] @ Matrix.Diagonal((-1, 1, 1, 1)))
        try:
            yield self
        finally:
            self.stack.pop()

    def _mi(self, mat):
        if mat not in self.mats:
            self.mats.append(mat)
        return self.mats.index(mat)

    def _emit(self, bm, mat, M_local, bev=0.0, segs=2, angle=30.0, uv="box", rad=1.0, smooth_all=True):
        if bev and bev > 0:
            edges = [e for e in bm.edges if e.is_manifold and e.calc_face_angle(0.0) > math.radians(angle)]
            if edges:
                bmesh.ops.bevel(bm, geom=edges, offset=bev, offset_type="OFFSET", segments=segs, profile=0.5,
                                affect="EDGES", clamp_overlap=True)
        bm.normal_update()
        uvl = bm.loops.layers.uv.verify()
        if uv == "box":
            _box_uv(bm, uvl)
        elif uv == "cyl":
            _cyl_uv(bm, uvl, rad)
        M = self.stack[-1] @ M_local
        flip = M.to_3x3().determinant() < 0
        mi = self._mi(mat)
        base = len(self.V)
        bm.verts.index_update()
        if os.environ.get("TRISTAT"):
            fr = [f for f in traceback.extract_stack()[:-1] if not f.filename.endswith("lib.py")]
            key = f"{self.name}:{fr[-1].lineno}" if fr else self.name
            TRISTAT[key] += sum(len(f.verts) - 2 for f in bm.faces)
        self.V.extend(tuple(M @ v.co) for v in bm.verts)
        for f in bm.faces:
            loops = list(f.loops)
            if flip:
                loops.reverse()
            self.F.append(tuple(base + lp.vert.index for lp in loops))
            self.UV.extend(tuple(lp[uvl].uv) for lp in loops)
            self.FM.append(mi)
        n = len(bm.faces)
        bm.free()
        return n

    # ------------------------------------------------------------ primitives
    def box(self, size, c=(0, 0, 0), rot=(0, 0, 0), mat="paint_yellow", bev=None, segs=2, q=None):
        """Box of `size` centred on c."""
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Diagonal((*size, 1)))
        bev = _auto_bev(size) if bev is None else bev
        bev, segs = _detail(size, bev, segs)
        M = T(V(c)) @ (q.to_matrix().to_4x4() if q is not None else R(*rot))
        return self._emit(bm, mat, M, bev, segs)

    def cyl(self, r, h, c=(0, 0, 0), rot=(0, 0, 0), mat="steel", sides=16, bev=None, segs=2, r2=None, caps=True,
            q=None, axis=None):
        """Cylinder/frustum centred on c, along local Z (rot/q orient it; axis='X'|'Y' shortcut)."""
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=caps, cap_tris=False, segments=sides, radius1=r,
                              radius2=r if r2 is None else r2, depth=h)
        if axis == "X":
            rot = (0, 90, 0)
        elif axis == "Y":
            rot = (90, 0, 0)
        bev = _auto_bev((r * 2, h)) * 0.8 if bev is None else bev
        if r < 0.03:
            bev = 0.0
        elif r < 0.1:
            segs = 1
        bev, segs = _detail((r * 2, h), bev, segs)
        M = T(V(c)) @ (q.to_matrix().to_4x4() if q is not None else R(*rot))
        return self._emit(bm, mat, M, bev if caps else 0, segs, uv="cyl", rad=max(r, r2 or 0))

    def rod(self, p0, p1, r, mat="steel", sides=12, bev=None, caps=True, r2=None):
        """Cylinder from point p0 to p1."""
        p0, p1 = V(p0), V(p1)
        d = p1 - p0
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=caps, cap_tris=False, segments=sides, radius1=r,
                              radius2=r if r2 is None else r2, depth=d.length)
        M = T((p0 + p1) / 2) @ aim(d).to_matrix().to_4x4()
        bev = (min(r * 0.25, 0.01) if r >= 0.025 else 0.0) if bev is None else bev
        return self._emit(bm, mat, M, bev if caps else 0, 1, uv="cyl", rad=r)

    def lathe(self, prof, c=(0, 0, 0), rot=(0, 0, 0), mat="steel", sides=24, bev=0.0, segs=2, q=None,
              cap0=True, cap1=True, angle=35.0, arc=None):
        """Surface of revolution about local Z. prof = [(r, z), ...] in order; r=0 points become poles."""
        bm = bmesh.new()
        rings = []
        n = sides
        a_end = math.tau if arc is None else math.radians(arc)
        cols = n if arc is None else n + 1
        for r, z in prof:
            if r <= 1e-6:
                rings.append([bm.verts.new((0, 0, z))])
            else:
                rings.append([bm.verts.new((r * math.cos(a_end * k / n), r * math.sin(a_end * k / n), z))
                              for k in range(cols)])
        for i in range(len(rings) - 1):
            A, B = rings[i], rings[i + 1]
            for k in range(n):
                k1 = (k + 1) % cols if arc is None else k + 1
                if len(A) == 1 and len(B) == 1:
                    continue
                if len(A) == 1:
                    face = (A[0], B[k1], B[k])
                elif len(B) == 1:
                    face = (A[k], A[k1], B[0])
                else:
                    face = (A[k], A[k1], B[k1], B[k])
                try:
                    bm.faces.new(face)
                except ValueError:
                    pass
        if arc is None:
            if cap0 and len(rings[0]) > 1:
                bm.faces.new(list(reversed(rings[0])))
            if cap1 and len(rings[-1]) > 1:
                bm.faces.new(rings[-1])
        bm.normal_update()
        # make normals point away from the axis on side faces (profiles may run either way)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:]) if (cap0 and cap1 and arc is None) else None
        rad = max(p[0] for p in prof)
        M = T(V(c)) @ (q.to_matrix().to_4x4() if q is not None else R(*rot))
        return self._emit(bm, mat, M, bev, segs, angle=angle, uv="cyl", rad=rad)

    def extrude(self, pts, depth, c=(0, 0, 0), rot=(0, 0, 0), mat="paint_yellow", bev=None, segs=2, q=None):
        """2D polygon (local XY) extruded along local Z by depth, centred on c (explicit prism, outward normals)."""
        area = sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1]
                   for i in range(len(pts)))
        if area < 0:
            pts = pts[::-1]
        bm = bmesh.new()
        bot = [bm.verts.new((x, y, -depth / 2)) for x, y in pts]
        top = [bm.verts.new((x, y, depth / 2)) for x, y in pts]
        bm.faces.new(list(reversed(bot)))
        bm.faces.new(top)
        n = len(pts)
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((bot[i], bot[j], top[j], top[i]))
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        dims = (max(xs) - min(xs), max(ys) - min(ys), depth)
        bev = _auto_bev(dims) if bev is None else bev
        bev, segs = _detail(dims, bev, segs)
        M = T(V(c)) @ (q.to_matrix().to_4x4() if q is not None else R(*rot))
        return self._emit(bm, mat, M, bev, segs)

    def plate(self, pts, thick, plane="YZ", at=0.0, mat="paint_yellow", bev=None, segs=2):
        """Flat plate from a 2D outline drawn in a machine view plane:
        'YZ' side view (pts = (y, z)), extruded along X centred at x=at;
        'XZ' front view (pts = (x, z)), extruded along Y centred at y=at;
        'XY' top view (pts = (x, y)), extruded along Z centred at z=at."""
        if plane == "YZ":
            q = Quaternion((0.5, 0.5, 0.5, 0.5))  # local X->Y, Y->Z, Z->X
            return self.extrude(pts, thick, c=(at, 0, 0), q=q, mat=mat, bev=bev, segs=segs)
        if plane == "XZ":
            q = Euler((math.radians(90), 0, 0)).to_quaternion()  # local Y->Z, Z->-Y
            return self.extrude(pts, thick, c=(0, at, 0), q=q, mat=mat, bev=bev, segs=segs)
        return self.extrude(pts, thick, c=(0, 0, at), mat=mat, bev=bev, segs=segs)

    def loft(self, rings, mat="paint_yellow", close=True, cap0=True, cap1=True, bev=0.0, segs=2, angle=35.0,
             uv="box"):
        """Skin successive rings (lists of points, same length, machine/current-frame space)."""
        bm = bmesh.new()
        vr = [[bm.verts.new(p) for p in ring] for ring in rings]
        n = len(rings[0])
        for i in range(len(vr) - 1):
            for k in range(n if close else n - 1):
                try:
                    bm.faces.new((vr[i][k], vr[i][(k + 1) % n], vr[i + 1][(k + 1) % n], vr[i + 1][k]))
                except ValueError:
                    pass
        if close and cap0:
            bm.faces.new(list(reversed(vr[0])))
        if close and cap1:
            bm.faces.new(vr[-1])
        bm.normal_update()
        if close and cap0 and cap1:
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        return self._emit(bm, mat, Matrix.Identity(4), bev, segs, angle=angle, uv=uv)

    def sphere(self, r, c=(0, 0, 0), mat="steel", seg=16, rings=8, scale=(1, 1, 1), rot=(0, 0, 0), q=None):
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=r,
                                  matrix=Matrix.Diagonal((*scale, 1)))
        M = T(V(c)) @ (q.to_matrix().to_4x4() if q is not None else R(*rot))
        return self._emit(bm, mat, M, 0, uv="cyl", rad=r)

    def tube(self, pts, r, mat="hose_yellow", sides=10, caps=True, r_fn=None, flat=1.0):
        """Swept circle through points (parallel-transport frames, no twisting). UV u=around, v=along (m)."""
        pts = [self.stack[-1] @ V(p) for p in pts]
        n = len(pts)
        tans = []
        for i in range(n):
            d = pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]
            tans.append(d.normalized())
        ref = V((0, 0, 1)) if abs(tans[0].z) < 0.9 else V((1, 0, 0))
        nrm = tans[0].cross(ref).normalized()
        frames = []
        for i in range(n):
            if i > 0:
                axis = tans[i - 1].cross(tans[i])
                if axis.length > 1e-8:
                    ang = tans[i - 1].angle(tans[i])
                    nrm = Quaternion(axis.normalized(), ang) @ nrm
            b = tans[i].cross(nrm).normalized()
            frames.append((nrm.copy(), b))
        base = len(self.V)
        mi = self._mi(mat)
        along = 0.0
        vs_uv = []
        for i, p in enumerate(pts):
            if i > 0:
                along += (pts[i] - pts[i - 1]).length
            rr = r_fn(i / (n - 1)) if r_fn else r
            a_, b_ = frames[i]
            for k in range(sides):
                ang = k / sides * math.tau
                self.V.append(tuple(p + (a_ * math.cos(ang) + b_ * math.sin(ang) * flat) * rr))
            vs_uv.append(along)
        for i in range(n - 1):
            for k in range(sides):
                k1 = (k + 1) % sides
                a0, a1 = base + i * sides + k, base + i * sides + k1
                b0, b1 = base + (i + 1) * sides + k, base + (i + 1) * sides + k1
                self.F.append((a0, a1, b1, b0))
                u0, u1 = k / sides * math.tau * r, (k + 1) / sides * math.tau * r
                self.UV.extend([(u0, vs_uv[i]), (u1, vs_uv[i]), (u1, vs_uv[i + 1]), (u0, vs_uv[i + 1])])
                self.FM.append(mi)
        if caps:
            for i, rev in ((0, True), (n - 1, False)):
                ring = [base + i * sides + k for k in range(sides)]
                if rev:
                    ring = ring[::-1]
                self.F.append(tuple(ring))
                self.UV.extend([(0.0, 0.0)] * sides)
                self.FM.append(mi)
        return pts

    def hose(self, p0, d0, p1, d1, r=0.02, mat="hose_yellow", sag=0.0, steps=28, sides=10, k=0.45,
             fittings="steel", fit_len=0.07):
        """Hose leaving p0 along d0 and arriving at p1 along d1 (cubic bezier, handles k*distance), with gravity
        sag and crimped ferrules at both ends."""
        p0, p1, d0, d1 = V(p0), V(p1), V(d0).normalized(), V(d1).normalized()
        L = (p1 - p0).length
        h0, h1 = p0 + d0 * (L * k + fit_len), p1 - d1 * (L * k + fit_len)
        s0, s1 = p0 + d0 * fit_len, p1 - d1 * fit_len
        pts = []
        for i in range(steps + 1):
            t = i / steps
            a = s0 * (1 - t) ** 3 + h0 * 3 * t * (1 - t) ** 2 + h1 * 3 * t * t * (1 - t) + s1 * t ** 3
            a.z -= sag * math.sin(math.pi * t)
            pts.append(a)
        self.tube([p0] + pts + [p1], r, mat, sides=sides, caps=False)
        if fittings:
            for p, d in ((p0, d0), (p1, -d1)):
                self.rod(p - d * 0.01, p + d * fit_len, r * 1.28, mat=fittings, sides=sides, bev=0.002)
        return pts

    def path(self, pts, r=0.02, mat="hose_yellow", sides=10, res=8, caps=True, tension=0.5, flat=1.0):
        """Catmull-Rom smoothed tube through control points (cables, long hose runs)."""
        P = [V(p) for p in pts]
        out = []
        for i in range(len(P) - 1):
            p0 = P[max(i - 1, 0)]
            p1, p2 = P[i], P[i + 1]
            p3 = P[min(i + 2, len(P) - 1)]
            for s in range(res):
                t = s / res
                t2, t3 = t * t, t * t * t
                out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                                  + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
        out.append(P[-1])
        self.tube(out, r, mat, sides=sides, caps=caps, flat=flat)
        return out

    def quad(self, corners, mat, uvs):
        """One quad (4 points, current frame) with explicit UVs (decals)."""
        M = self.stack[-1]
        base = len(self.V)
        pts = [M @ V(p) for p in corners]
        flip = M.to_3x3().determinant() < 0
        idx = [0, 1, 2, 3]
        if flip:
            idx.reverse()
        self.V.extend(tuple(p) for p in pts)
        self.F.append(tuple(base + i for i in idx))
        self.UV.extend(tuple(uvs[i]) for i in idx)
        self.FM.append(self._mi(mat))

    def rock(self, r, c, seed, mat="coal_ore", detail=1, squash=(1, 1, 0.75), rough=0.28, facet=True, q=None):
        """Faceted lump (coal, rock): jittered icosphere, flat-ish facets."""
        rng = random.Random(seed)
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=detail, radius=r)
        for v in bm.verts:
            k = 1 + rng.uniform(-rough, rough)
            v.co = V((v.co.x * k * squash[0], v.co.y * k * squash[1], v.co.z * k * squash[2]))
        # flatten a few cleavage planes so lumps read as broken coal, not blobs
        for _ in range(3):
            nrm = V((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1))).normalized()
            d = r * rng.uniform(0.45, 0.75)
            for v in bm.verts:
                s = v.co.dot(nrm)
                if s > d:
                    v.co -= nrm * (s - d)
        q = q or Euler((rng.uniform(0, 6.3), rng.uniform(0, 6.3), rng.uniform(0, 6.3))).to_quaternion()
        M = T(V(c)) @ q.to_matrix().to_4x4()
        return self._emit(bm, mat, M, 0, uv="box")

    def decal(self, key, c, n=(0, -1, 0), up=(0, 0, 1), w=None, h=None, off=0.003):
        """Atlas decal quad centred on c, facing n (visible side), image up along `up`. Give w or h (metres)."""
        atlas = self.m.atlas
        x, y, pw, ph = atlas.rects[key]
        asp = pw / ph
        if w is None:
            w = h * asp
        if h is None:
            h = w / asp
        n, up = V(n).normalized(), V(up)
        up = (up - n * up.dot(n)).normalized()
        right = up.cross(n)
        cc = V(c) + n * off
        W, H = atlas.size
        e = 1.0  # px inset
        u0, u1 = (x + e) / W, (x + pw - e) / W
        v0, v1 = 1 - (y + ph - e) / H, 1 - (y + e) / H
        hw, hh = right * (w / 2), up * (h / 2)
        self.quad([cc - hw - hh, cc + hw - hh, cc + hw + hh, cc - hw + hh], atlas.mat_name,
                  [(u0, v0), (u1, v0), (u1, v1), (u0, v1)])
        return w, h

    # ------------------------------------------------------------ compound helpers
    def bolts(self, pts, n=(0, -1, 0), r=0.011, h=0.008, mat="steel_dark", washer=False):
        """Hex bolt heads (optional washers) at points, sitting on a surface with normal n (20 tris each)."""
        q = aim(n)
        nv = V(n).normalized()
        for p in pts:
            p = V(p)
            if washer:
                self.cyl(r * 1.45, 0.0025, c=p + nv * 0.00125, q=q, mat=mat, sides=10, bev=0)
            self.cyl(r, h, c=p + nv * (h / 2 + (0.0025 if washer else 0.0)), q=q, mat=mat, sides=6, bev=0)

    def bolt_circle(self, c, n, R_, count, r=0.011, mat="steel_dark", phase=0.0):
        n = V(n).normalized()
        a = n.orthogonal().normalized()
        b = n.cross(a)
        pts = [V(c) + (a * math.cos(phase + k / count * math.tau) + b * math.sin(phase + k / count * math.tau)) * R_
               for k in range(count)]
        self.bolts(pts, n, r=r, mat=mat)

    def bolt_row(self, p0, p1, count, n, r=0.011, mat="steel_dark"):
        p0, p1 = V(p0), V(p1)
        self.bolts([p0.lerp(p1, i / max(1, count - 1)) for i in range(count)], n, r=r, mat=mat)

    def hyd(self, p0, p1, rb=0.06, rr=0.035, mat="paint_yellow", frac=0.55, sides=16, ports=True):
        """Static hydraulic cylinder from pivot p0 (barrel) to pivot p1 (rod eye)."""
        p0, p1 = V(p0), V(p1)
        d = p1 - p0
        L = d.length
        q = aim(d)
        with self.at(p0, q=q):
            hydraulic_barrel(self, L * frac, rb, mat=mat, sides=sides, ports=ports)
        with self.at(p1, q=aim(-d)):
            hydraulic_rod(self, L * (1 - frac) + rb * 0.6, rr, sides=sides)

    def handrail(self, pts, r=0.019, mat="paint_yellow", posts=None, post_h=None):
        """Tube rail through pts (bent corners) + optional vertical posts down to z values."""
        P = [V(p) for p in pts]
        out = []
        for i, p in enumerate(P):
            if 0 < i < len(P) - 1:
                a, b = (P[i - 1] - p).normalized(), (P[i + 1] - p).normalized()
                rr = 0.07
                c0, c1 = p + a * rr, p + b * rr
                for s in range(5):
                    t = s / 4
                    out.append(c0 * (1 - t) ** 2 + p * 2 * t * (1 - t) + c1 * t * t)
            else:
                out.append(p)
        self.tube(out, r, mat, sides=10, caps=True)
        for (p, z) in posts or []:
            p = V(p)
            self.rod((p.x, p.y, z), p, r, mat=mat, sides=10)

    def grille(self, c, w, h, n_slats, rot=(0, 0, 0), depth=0.05, mat="paint_yellow", slat_mat=None, frame=0.035,
               tilt=35.0, q=None):
        """Louvred grille in local XZ plane facing local -Y: frame + angled slats."""
        slat_mat = slat_mat or mat
        with self.at(c, rot=rot, q=q):
            fr = frame
            self.box((w, depth, fr), c=(0, 0, h / 2 - fr / 2), mat=mat)
            self.box((w, depth, fr), c=(0, 0, -h / 2 + fr / 2), mat=mat)
            self.box((fr, depth, h - 2 * fr), c=(w / 2 - fr / 2, 0, 0), mat=mat)
            self.box((fr, depth, h - 2 * fr), c=(-w / 2 + fr / 2, 0, 0), mat=mat)
            self.box((w - 2 * fr, 0.006, h - 2 * fr), c=(0, depth * 0.45, 0), mat="steel_dark", bev=0)
            inner = h - 2 * fr
            pitch = inner / n_slats
            for i in range(n_slats):
                z = -inner / 2 + pitch * (i + 0.5)
                self.box((w - 2 * fr, depth * 0.85, pitch * 0.9 * 0.32), c=(0, 0, z), rot=(tilt, 0, 0), mat=slat_mat,
                         bev=0.002, segs=1)

    def mesh_panel(self, c, w, h, cell=0.05, wire=0.004, rot=(0, 0, 0), mat="steel_dark", q=None):
        """Welded wire mesh in local XZ plane."""
        with self.at(c, rot=rot, q=q):
            nx, nz = max(1, int(w / cell)), max(1, int(h / cell))
            for i in range(nx + 1):
                x = -w / 2 + i * w / nx
                self.box((wire, wire, h), c=(x, 0, 0), mat=mat, bev=0)
            for j in range(nz + 1):
                z = -h / 2 + j * h / nz
                self.box((w, wire, wire), c=(0, wire, z), mat=mat, bev=0)


# ---------------------------------------------------------------- reusable sub-assemblies (local frames)

def hydraulic_barrel(p, L, rb, mat="paint_yellow", sides=12, ports=True):
    """Barrel along local +Z from 0 (pivot eye at origin) to L. Pivot axis = local X."""
    p.cyl(rb * 0.95, rb * 1.3, c=(0, 0, 0), rot=(0, 90, 0), mat="steel_dark", sides=10, bev=0)
    p.box((rb * 1.25, rb * 1.4, rb * 1.1), c=(0, 0, rb * 0.75), mat=mat, segs=1)
    p.lathe([(0, rb * 1.2), (rb * 1.12, rb * 1.2), (rb * 1.12, rb * 1.55), (rb, rb * 1.62), (rb, L - rb * 0.6),
             (rb * 1.14, L - rb * 0.55), (rb * 1.14, L), (rb * 0.62, L), (0, L)], mat=mat, sides=sides, angle=30)
    if ports:
        for z in (rb * 2.1, L - rb * 1.1):
            p.cyl(rb * 0.28, rb * 0.6, c=(0, rb * 1.1, z), rot=(90, 0, 0), mat="steel", sides=6, bev=0)


def hydraulic_rod(p, L, rr, sides=12):
    """Chrome rod along local +Z from 0 (rod-eye pivot at origin) to L; eye axis = local X."""
    p.cyl(rr * 1.75, rr * 2.4, c=(0, 0, 0), rot=(0, 90, 0), mat="steel_dark", sides=10, bev=0)
    p.box((rr * 2.2, rr * 2.6, rr * 1.6), c=(0, 0, rr * 1.4), mat="steel_dark", segs=1)
    p.cyl(rr, L - rr * 2.2, c=(0, 0, rr * 2.2 + (L - rr * 2.2) / 2), mat="chrome", sides=sides, bev=0)


def work_light(p, c, d, kind="round", r=0.085, up=(0, 0, 1), housing="paint_black", guard=True, sides=14):
    """Lamp at c aimed along d (local +Z of the fixture = beam). Returns the lens centre (~250 tris)."""
    q = aim(d, "Y")
    with p.at(c, q=q):
        if kind == "round":
            p.lathe([(0, -0.15), (r * 0.62, -0.15), (r * 0.95, -0.095), (r * 1.1, -0.03), (r * 1.13, 0.022),
                     (r * 0.9, 0.022), (r * 0.9, -0.016), (0, -0.016)], mat=housing, sides=sides, angle=24)
            p.lathe([(r * 0.9, 0.008), (0, 0.008)], mat="glass", sides=sides, cap0=False, cap1=False)
            p.lathe([(r * 0.78, -0.012), (0, -0.012)], mat="emit_white", sides=sides, cap0=False, cap1=False)
            if guard:
                for a in (0, 90):
                    with p.at((0, 0, 0.045), rot=(0, 0, a)):
                        p.box((r * 2.15, 0.012, 0.012), mat="steel_dark", bev=0)
                p.lathe([(r * 1.02, 0.034), (r * 1.1, 0.034), (r * 1.1, 0.05), (r * 1.02, 0.05)], mat="steel_dark",
                        sides=sides, cap0=False, cap1=False)
        else:  # rectangular LED bar light
            w, h = r * 2.6, r * 1.5
            p.box((w, h, 0.07), c=(0, 0, -0.035), mat=housing, bev=0.008, segs=1)
            for i in range(5):
                p.box((0.008, h * 0.9, 0.035), c=(-w / 2 + 0.03 + i * (w - 0.06) / 4, 0, -0.085), mat=housing, bev=0)
            p.box((w * 0.86, h * 0.76, 0.004), c=(0, 0, 0.002), mat="emit_white", bev=0)
            p.box((w * 0.9, h * 0.8, 0.006), c=(0, 0, 0.006), mat="glass", bev=0)
    return V(c) + V(d).normalized() * 0.02


def lift_eye(p, c, n=(0, 0, 1), r=0.05, mat="paint_yellow"):
    """Welded lifting lug with a hole (plate profile), standing on a surface with normal n."""
    q = aim(n)
    pts = []
    for k in range(13):
        a = math.pi * k / 12
        pts.append((math.cos(a) * r, r * 0.9 + math.sin(a) * r))
    pts = [(r * 1.3, 0)] + pts + [(-r * 1.3, 0)]
    with p.at(c, q=q):
        with p.at((0, 0, 0), rot=(90, 0, 0)):
            p.extrude(pts, 0.025, mat=mat, bev=0.004)
            p.cyl(r * 0.45, 0.03, c=(0, r * 0.9, 0), mat="steel_dark", sides=12, bev=0)


def step_plate(p, c, w, d, mat="steel", t=0.012):
    """Anti-slip step tread: plate with raised bars."""
    p.box((w, d, t), c=c, mat=mat, bev=0.003)
    for i in range(int(w / 0.05)):
        x = c[0] - w / 2 + 0.03 + i * 0.05
        if x < c[0] + w / 2 - 0.02:
            p.box((0.012, d * 0.86, 0.006), c=(x, c[1], c[2] + t / 2 + 0.003), mat=mat, bev=0)


def rect_perimeter(w, h, pitch, inset=0.0):
    """Points around a w x h rectangle (local XY, centred), roughly `pitch` apart, inset from the edge."""
    w, h = w - 2 * inset, h - 2 * inset
    pts = []
    for (x0, y0, x1, y1) in ((-w / 2, -h / 2, w / 2, -h / 2), (w / 2, -h / 2, w / 2, h / 2),
                             (w / 2, h / 2, -w / 2, h / 2), (-w / 2, h / 2, -w / 2, -h / 2)):
        L = math.hypot(x1 - x0, y1 - y0)
        n = max(1, round(L / pitch))
        for i in range(n):
            t = i / n
            pts.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
    return pts


def cover(p, c, n, w, h, t=0.012, mat="paint_yellow", pitch=0.12, bolt_r=0.009, up=(0, 0, 1)):
    """Bolted cover plate lying on a surface (normal n) centred at c."""
    n = V(n).normalized()
    upv = V(up)
    if abs(upv.dot(n)) > 0.95:
        upv = V((0, 1, 0))
    upv = (upv - n * upv.dot(n)).normalized()
    rt = upv.cross(n)
    M = Matrix((rt, upv, n)).transposed().to_quaternion()
    with p.at(c, q=M):
        p.box((w, h, t), c=(0, 0, t / 2), mat=mat, bev=min(0.006, t * 0.4), segs=1)
        if pitch:
            for x, y in rect_perimeter(w, h, pitch, inset=0.022):
                p.cyl(bolt_r, 0.008, c=(x, y, t + 0.004), mat="steel_dark", sides=6, bev=0)


def fp_box(p, c, size, n=(0, 0, 1), up=(0, 1, 0), mat="paint_yellow", pitch=0.1, flange=0.03, lid_t=0.045):
    """Flameproof (explosion-proof) enclosure: box whose bolted cover faces n. c = centre of the BACK face
    (the face opposite the cover); size = (width, height, depth along n)."""
    n = V(n).normalized()
    upv = V(up)
    if abs(upv.dot(n)) > 0.95:
        upv = V((0, 0, 1)) if abs(n.z) < 0.95 else V((0, 1, 0))
    upv = (upv - n * upv.dot(n)).normalized()
    rt = upv.cross(n)
    M = Matrix((rt, upv, n)).transposed().to_quaternion()
    sx, sy, sz = size
    with p.at(c, q=M):
        p.box((sx, sy, sz - lid_t), c=(0, 0, (sz - lid_t) / 2), mat=mat, bev=0.012)
        p.box((sx + 2 * flange, sy + 2 * flange, lid_t * 0.45), c=(0, 0, sz - lid_t + lid_t * 0.225), mat=mat,
              bev=0.006, segs=1)
        p.box((sx + 2 * flange - 0.01, sy + 2 * flange - 0.01, lid_t * 0.55), c=(0, 0, sz - lid_t * 0.275),
              mat=mat, bev=0.008, segs=2)
        for x, y in rect_perimeter(sx + 2 * flange, sy + 2 * flange, pitch, inset=0.018):
            p.cyl(0.0105, 0.012, c=(x, y, sz + 0.005), mat="steel_dark", sides=6, bev=0)
        # lifting handles on the cover
        for x in (-sx * 0.3, sx * 0.3):
            p.rod((x, -0.04, sz), (x, -0.04, sz + 0.05), 0.008, mat="steel", sides=6)
            p.rod((x, 0.04, sz), (x, 0.04, sz + 0.05), 0.008, mat="steel", sides=6)
            p.rod((x, -0.04, sz + 0.05), (x, 0.04, sz + 0.05), 0.008, mat="steel", sides=6)
    return M


def track_frame_q(t, n):
    """Quaternion for a part whose local X stays machine X, local Y = tangent t, local Z = normal n (YZ plane)."""
    return Matrix(((1, 0, 0), (0, t[0], n[0]), (0, t[1], n[1]))).to_quaternion()


def wheel(p, c, side=1, R=0.68, W=0.55, rim=0.335, lugs=24, lug_h=0.05, sides=32, rim_mat="paint_yellow",
          nuts=10, angle=24.0):
    """Mining tyre + disc rim centred at c, axle along machine X, outer face toward side (+1 = +X, -1 = -X).
    R = carcass crown radius (lugs add lug_h). Deep alternating chevron lugs (L-5 style)."""
    q_axis = Euler((0, math.radians(90 * side), 0)).to_quaternion()
    hw = W / 2
    with p.at(c, q=q_axis):
        p.lathe([(rim * 1.04, -hw * 0.8), (R * 0.8, -hw), (R * 0.95, -hw * 0.97), (R, -hw * 0.85),
                 (R, hw * 0.85), (R * 0.95, hw * 0.97), (R * 0.8, hw), (rim * 1.04, hw * 0.8)], mat="rubber",
                sides=sides, cap0=False, cap1=False, angle=40)
        sk = math.tan(math.radians(angle))
        for k in range(lugs):
            a = k / lugs * math.tau
            rad = V((math.cos(a), math.sin(a), 0))
            for s in (-1, 1):
                a2 = a + (math.pi / lugs if s > 0 else 0)
                rad = V((math.cos(a2), math.sin(a2), 0))
                z0, z1 = s * 0.03, s * hw * 0.9
                L = abs(z1 - z0)
                w = 2 * math.pi * R / lugs * 0.42
                pts = [(0, -w / 2), (L, -w / 2 + L * sk), (L, w / 2 + L * sk), (0, w / 2)]
                with p.at(rad * R * 0.995 + V((0, 0, z0)), q=frame(rad, (0, 0, s))):
                    p.extrude(pts, lug_h + 0.02, c=(0, 0, (lug_h + 0.02) / 2 - 0.02), mat="rubber", bev=0)
        # disc rim (outer face toward local +Z), barrel, hub + nuts
        p.cyl(rim, W * 0.82, mat=rim_mat, sides=24, bev=0, caps=False)
        p.lathe([(rim, hw * 0.82), (rim * 0.93, hw * 0.86), (rim * 0.72, hw * 0.6), (rim * 0.5, hw * 0.55),
                 (rim * 0.5, hw * 0.62), (rim * 0.32, hw * 0.66), (0, hw * 0.66)], mat=rim_mat, sides=24,
                cap0=False, cap1=False, angle=30)
        p.lathe([(rim * 0.3, hw * 0.66), (rim * 0.3, hw * 0.74), (rim * 0.2, hw * 0.8), (0, hw * 0.8)],
                mat="steel_dark", sides=16, cap0=False, cap1=False, angle=30)
        for k in range(nuts):
            a = k / nuts * math.tau
            p.cyl(0.018, 0.03, c=(math.cos(a) * rim * 0.41, math.sin(a) * rim * 0.41, hw * 0.66 + 0.01),
                  mat="steel_dark", sides=6, bev=0)
        p.lathe([(0, -hw * 0.55), (rim * 0.5, -hw * 0.55)], mat=rim_mat, sides=16, cap0=False, cap1=False)


def race(s, y0, y1, zc, R):
    """Point on a crawler track loop (YZ racetrack): returns y, z, tangent(y,z), outward normal(y,z)."""
    Ls, arc = y1 - y0, math.pi * R
    s %= 2 * Ls + 2 * arc
    if s < Ls:
        return y0 + s, zc + R, (1.0, 0.0), (0.0, 1.0)
    s -= Ls
    if s < arc:
        f = math.pi / 2 - s / R
        return y1 + R * math.cos(f), zc + R * math.sin(f), (math.sin(f), -math.cos(f)), (math.cos(f), math.sin(f))
    s -= arc
    if s < Ls:
        return y1 - s, zc - R, (-1.0, 0.0), (0.0, -1.0)
    s -= Ls
    f = -math.pi / 2 - s / R
    return y0 + R * math.cos(f), zc + R * math.sin(f), (math.sin(f), -math.cos(f)), (math.cos(f), math.sin(f))


def crawler(p, xc, side, y0, y1, zc, R, width=0.6, n=42, frame_mat="paint_yellow"):
    """Crawler track: shoes with grousers around a racetrack, side frame plate, sprocket/idler hubs, tensioner."""
    L = 2 * (y1 - y0) + 2 * math.pi * R
    pitch = L / n
    for i in range(n):
        y, z, t, nn = race(i * pitch, y0, y1, zc, R)
        with p.at((xc, y, z), q=track_frame_q(t, nn)):
            p.box((width, pitch * 0.9, 0.034), mat="steel_dark", bev=0.006, segs=1)
            p.box((width * 0.97, 0.036, 0.03), c=(0, -pitch * 0.2, 0.031), mat="steel_dark", bev=0)
    Ri = R - 0.1
    pts = [(y1 + Ri * math.cos(math.pi / 2 - math.pi * k / 6), zc + Ri * math.sin(math.pi / 2 - math.pi * k / 6))
           for k in range(7)]
    pts += [(y0 + Ri * math.cos(-math.pi / 2 - math.pi * k / 6), zc + Ri * math.sin(-math.pi / 2 - math.pi * k / 6))
            for k in range(7)]
    xo = xc + side * (width / 2 - 0.085)
    p.plate(pts, 0.05, "YZ", at=xo, mat=frame_mat, bev=0.012)
    p.plate([(y0 + 0.25, zc - 0.12), (y1 - 0.25, zc - 0.12), (y1 - 0.35, zc + 0.12), (y0 + 0.35, zc + 0.12)],
            0.03, "YZ", at=xo + side * 0.035, mat=frame_mat, bev=0.008)
    nb = max(3, int((y1 - y0 - 0.9) / 0.32))
    p.bolt_row((xo + side * 0.05, y0 + 0.45, zc + 0.07), (xo + side * 0.05, y1 - 0.45, zc + 0.07), nb,
               (side, 0, 0), r=0.012)
    p.bolt_row((xo + side * 0.05, y0 + 0.37, zc - 0.07), (xo + side * 0.05, y1 - 0.37, zc - 0.07), nb + 1,
               (side, 0, 0), r=0.012)
    for yy, big in ((y1, True), (y0, False)):
        rr = R * (0.75 if big else 0.64)
        p.lathe([(0, 0.0), (rr, 0.0), (rr, 0.035), (rr * 0.72, 0.06), (rr * 0.72, 0.085), (rr * 0.38, 0.095),
                 (0, 0.095)], c=(xc + side * (width / 2 - 0.06), yy, zc), rot=(0, 90 * side, 0),
                mat="steel_dark" if big else frame_mat, sides=18, angle=28)
        p.bolt_circle((xc + side * (width / 2), yy, zc), (side, 0, 0), rr * 0.55, 6, r=0.013)
    p.box((0.08, 0.5, 0.12), c=(xc + side * (width / 2 - 0.03), y0 + 0.45, zc), mat="steel_dark", bev=0.01)


def custom_mat(name, color, rough=0.5, metal=0.0, alpha=1.0, emit=None, emit_strength=2.0, clean=False):
    """A custom_* material the game keeps exactly as exported (solid colour; optional alpha / emission)."""
    m = bk.mat(name, color, rough=rough, metal=metal, emit=emit, emit_strength=emit_strength, alpha=alpha)
    if clean:
        CLEAN.add(name)
    return m


def wheelbarrow(p, pos, yaw=0.0, tray="paint_green", decal=None, load=None, load_seed=0):
    """Contractor wheelbarrow (dented steel tray, pneumatic tyre, wooden handles). pos = floor centre, yaw deg.
    load = material name for a heaped load in the tray (rock lumps)."""
    QB = Quaternion((0, 0, 1), math.radians(yaw))
    with p.at(pos, q=QB):
        def rr_ring(w, l, z, fy, r=0.06, n=6):
            pts = []
            for cx, cy, a0 in ((w / 2 - r, -l / 2 - fy + r, -90), (w / 2 - r, l / 2 - r, 0), (-w / 2 + r, l / 2 - r, 90),
                               (-w / 2 + r, -l / 2 - fy + r, 180)):
                for k in range(n):
                    a = math.radians(a0 + 90 * k / (n - 1))
                    pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r, z))
            return pts
        outer, inner = [], []
        for i in range(6):
            t = i / 5
            ring = rr_ring(lerp(0.42, 0.66, t), lerp(0.5, 0.78, t), 0.36 + t * 0.26, lerp(0.0, 0.22, t))
            dented = []
            for (x, y, zz) in ring:
                d = noise.noise(V((x * 6.0, y * 6.0, zz * 6.0 + 9.0 + load_seed)))
                nrm = V((x, y + 0.11 * t, 0)).normalized()
                dented.append(tuple(V((x, y, zz)) + nrm * (-0.022 * max(0.0, d) * (1 - abs(2 * t - 1) * 0.6))))
            outer.append(dented)
            inner.append([tuple(V(q) + V((-q[0], -(q[1] + 0.11 * t), 0)).normalized() * 0.006 + V((0, 0, 0.004)))
                          for q in reversed(dented)])
        p.loft(outer, mat=tray, close=True, cap0=True, cap1=False, bev=0, uv="box")
        p.loft(inner, mat=tray, close=True, cap0=True, cap1=False, bev=0, uv="box")
        p.tube([V(q) + V((0, 0, 0.006)) for q in outer[-1] + [outer[-1][0]]], 0.012, mat=tray, sides=6, caps=False)
        for sx in (1, -1):
            p.rod((sx * 0.07, -0.62, 0.2), (sx * 0.22, 0.2, 0.38), 0.014, mat="steel_dark", sides=8)
            p.rod((sx * 0.22, 0.2, 0.38), (sx * 0.27, 0.9, 0.56), 0.02, mat="wood_dark", sides=8)
            p.cyl(0.024, 0.13, c=(sx * 0.275, 0.88, 0.555), q=aim(V((0.07, 0.7, 0.18))), mat="rubber", sides=8, bev=0)
            p.rod((sx * 0.2, 0.12, 0.36), (sx * 0.22, 0.2, 0.0), 0.012, mat="steel_dark", sides=6)
            p.box((0.04, 0.08, 0.012), c=(sx * 0.22, 0.2, 0.006), mat="steel_dark", bev=0)
            p.rod((sx * 0.07, -0.62, 0.2), (sx * 0.12, -0.3, 0.36), 0.01, mat="steel_dark", sides=6)
        p.rod((-0.2, 0.12, 0.36), (0.2, 0.12, 0.36), 0.01, mat="steel_dark", sides=6)
        with p.at((0, -0.62, 0.2), rot=(0, 90, 0)):
            p.lathe([(0.08, -0.04), (0.13, -0.045), (0.18, -0.04), (0.2, -0.02), (0.2, 0.02), (0.18, 0.04),
                     (0.13, 0.045), (0.08, 0.04)], mat="rubber", sides=22, cap0=False, cap1=False, angle=40)
            for k in range(22):
                a = k / 22 * math.tau
                p.box((0.014, 0.022, 0.06), c=(math.cos(a) * 0.2, math.sin(a) * 0.2, 0), rot=(0, 0, math.degrees(a)),
                      mat="rubber", bev=0)
            p.cyl(0.08, 0.07, mat="paint_red", sides=14, bev=0, caps=False)
            p.cyl(0.03, 0.12, mat="steel_dark", sides=8, bev=0)
        if decal:
            p.decal(decal, c=(0.0, 0.362, 0.56), n=(0, 0.88, -0.475), up=(0, 0.475, 0.88), w=0.32)
        if load:
            rng = random.Random(load_seed)
            for k in range(26):
                x, y = rng.uniform(-0.22, 0.22), rng.uniform(-0.3, 0.25)
                hump = 0.12 * (1 - (x / 0.3) ** 2) * (1 - (y / 0.4) ** 2)
                s = rng.uniform(0.04, 0.08)
                p.rock(s, (x, y - 0.04, 0.56 + hump), seed=load_seed * 100 + k, mat=load, detail=1 if s > 0.06 else 0,
                       squash=(1, 0.9, 0.75), rough=0.3)


# ---------------------------------------------------------------- decals (atlas)
INK = "#151515"
YEL = "#E8B400"
WEAR_DEFS = ('<filter id="wear" x="0" y="0" width="100%" height="100%" filterUnits="objectBoundingBox">'
             '<feTurbulence type="fractalNoise" baseFrequency="{f}" numOctaves="4" seed="{seed}" result="n"/>'
             '<feColorMatrix in="n" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 -18 {o}" result="m"/>'
             '<feComposite in="SourceGraphic" in2="m" operator="in"/></filter>')


def svg(w, h, body, wear=0.0, seed=3, freq=0.05):
    """wear 0..1 chips speckled scuffs out of the ink (fractal-noise alpha mask): 0.3 light, 0.6 worn, 1 heavy."""
    thr = 0.86 - 0.10 * wear
    defs = WEAR_DEFS.format(f=freq, seed=seed, o=f"{18 * thr:.3f}") if wear else ""
    g0, g1 = ('<g filter="url(#wear)">', "</g>") if wear else ("", "")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            f'<defs>{defs}</defs>{g0}{body}{g1}</svg>')


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def svg_text(text, font="Barlow Condensed Black", fill=INK, size=200, spacing=0, weight=None, wear=0.3, seed=3,
             stroke=None, stroke_w=0, italic=False):
    """Single-line text on a generous canvas (use with fit=True: trimmed and scaled into the cell)."""
    w, h = int(size * (len(text) * 0.75 + 2)), int(size * 1.6)
    wt = f' font-weight="{weight}"' if weight else ""
    st = f' stroke="{stroke}" stroke-width="{stroke_w}" paint-order="stroke"' if stroke else ""
    it = ' font-style="italic"' if italic else ""
    body = (f'<text x="{size * 0.5}" y="{size * 1.15}" font-family="{font}"{wt}{it} font-size="{size}" '
            f'letter-spacing="{spacing}" fill="{fill}"{st}>{esc(text)}</text>')
    return svg(w, h, body, wear=wear, seed=seed)


def svg_hazard(w, h, band=None, wear=0.25, seed=5, yellow=YEL, black=INK, angle=45):
    band = band or h * 0.5
    body = (f'<defs><pattern id="hz" width="{band * 2}" height="{band * 2}" patternUnits="userSpaceOnUse" '
            f'patternTransform="rotate({angle})"><rect width="{band}" height="{band * 2}" fill="{black}"/>'
            f'<rect x="{band}" width="{band}" height="{band * 2}" fill="{yellow}"/></pattern></defs>'
            f'<rect width="{w}" height="{h}" fill="url(#hz)"/>')
    return svg(w, h, body, wear=wear, seed=seed, freq=0.02)


def svg_chevron(w, h, wear=0.2, seed=8):
    return svg_hazard(w, h, band=h * 0.45, wear=wear, seed=seed, yellow="#E9E9E6", black="#C21D16", angle=-45)


def _alert_tri(x, y, s, fill, mark):
    """Safety-alert triangle (top-left at x,y, size s) with an exclamation mark."""
    return (f'<path d="M{x + s / 2},{y} L{x + s},{y + s * 0.9} L{x},{y + s * 0.9} Z" fill="{fill}" '
            f'stroke="{fill}" stroke-width="{s * 0.06}" stroke-linejoin="round"/>'
            f'<rect x="{x + s * 0.455}" y="{y + s * 0.28}" width="{s * 0.09}" height="{s * 0.34}" rx="{s * 0.03}" fill="{mark}"/>'
            f'<circle cx="{x + s / 2}" cy="{y + s * 0.74}" r="{s * 0.055}" fill="{mark}"/>')


def svg_panel(w, h, kind, lines, wear=0.4, seed=11):
    """Safety sign: OSHA DANGER (black band, red oval, white letters) / ANSI WARNING (orange) / CAUTION (yellow)
    header with alert triangle, then bold body text on white."""
    hh = h * 0.3
    m = h * 0.03
    body = [f'<rect width="{w}" height="{h}" rx="{h * 0.04}" fill="#F4F3EE"/>']
    if kind == "DANGER":
        body.append(f'<rect x="{m}" y="{m}" width="{w - 2 * m}" height="{hh}" rx="{h * 0.025}" fill="#111111"/>')
        body.append(f'<ellipse cx="{w / 2}" cy="{m + hh / 2}" rx="{w * 0.4}" ry="{hh * 0.42}" fill="#C8102E" '
                    f'stroke="#FFFFFF" stroke-width="{hh * 0.05}"/>')
        ts = hh * 0.6
        body.append(f'<text x="{w / 2}" y="{m + hh / 2 + ts * 0.36}" text-anchor="middle" font-family="Barlow Condensed Black" '
                    f'font-size="{ts}" fill="#FFFFFF" letter-spacing="{ts * 0.06}">DANGER</text>')
    else:
        bg, fg = {"WARNING": ("#F26A10", INK), "CAUTION": ("#F7C600", INK), "NOTICE": ("#1E4FA0", "#FFFFFF")}[kind]
        body.append(f'<rect x="{m}" y="{m}" width="{w - 2 * m}" height="{hh}" rx="{h * 0.025}" fill="{bg}"/>')
        ts = hh * 0.62
        tri = hh * 0.66
        gap = ts * 0.25
        tw = len(kind) * 0.5 * ts
        x0 = (w - (tri + gap + tw)) / 2
        body.append(_alert_tri(x0, m + (hh - tri * 0.9) / 2, tri, fg, bg))
        body.append(f'<text x="{x0 + tri + gap}" y="{m + hh / 2 + ts * 0.36}" font-family="Barlow Condensed Black" '
                    f'font-size="{ts}" fill="{fg}" letter-spacing="{ts * 0.04}">{kind}</text>')
    n = len(lines)
    avail = h - hh - h * 0.1
    ls = min(avail / (n * 1.15), w / (max(len(s) for s in lines) * 0.5))
    for i, s in enumerate(lines):
        y = hh + h * 0.06 + ls * (i + 0.92) * 1.12
        body.append(f'<text x="{w / 2}" y="{y}" text-anchor="middle" font-family="Barlow Condensed ExtraBold" '
                    f'font-size="{ls}" fill="{INK}">{esc(s)}</text>')
    return svg(w, h, "".join(body), wear=wear, seed=seed)


def svg_iso(w, h, symbol="!", wear=0.15, seed=13):
    """ISO 7010-style yellow warning triangle with black border."""
    s = min(w, h / 0.9)
    pad = s * 0.04
    pth = f'M{w / 2},{pad} L{w - pad},{s * 0.9 - pad} L{pad},{s * 0.9 - pad} Z'
    body = (f'<path d="{pth}" fill="{INK}" stroke="{INK}" stroke-width="{s * 0.06}" stroke-linejoin="round"/>'
            f'<path d="M{w / 2},{s * 0.16} L{w - s * 0.17},{s * 0.8} L{s * 0.17},{s * 0.8} Z" fill="#F7C600" '
            f'stroke="#F7C600" stroke-width="{s * 0.03}" stroke-linejoin="round"/>')
    if symbol == "!":
        body += (f'<rect x="{w / 2 - s * 0.045}" y="{s * 0.36}" width="{s * 0.09}" height="{s * 0.26}" rx="{s * 0.03}" fill="{INK}"/>'
                 f'<circle cx="{w / 2}" cy="{s * 0.7}" r="{s * 0.05}" fill="{INK}"/>')
    elif symbol == "bolt":  # electrical
        body += (f'<path d="M{w / 2 + s * 0.04},{s * 0.32} L{w / 2 - s * 0.1},{s * 0.56} L{w / 2},{s * 0.56} '
                 f'L{w / 2 - s * 0.05},{s * 0.76} L{w / 2 + s * 0.11},{s * 0.5} L{w / 2 + s * 0.01},{s * 0.5} Z" fill="{INK}"/>')
    elif symbol == "crush":  # hand between rollers
        body += (f'<circle cx="{w / 2 - s * 0.1}" cy="{s * 0.6}" r="{s * 0.1}" fill="none" stroke="{INK}" stroke-width="{s * 0.035}"/>'
                 f'<circle cx="{w / 2 + s * 0.1}" cy="{s * 0.6}" r="{s * 0.1}" fill="none" stroke="{INK}" stroke-width="{s * 0.035}"/>'
                 f'<path d="M{w / 2 - s * 0.03},{s * 0.32} l{s * 0.06},0 l0,{s * 0.2} l-{s * 0.06},0 Z" fill="{INK}"/>')
    return svg(w, h, body, wear=wear, seed=seed)


def svg_plate(w, h, lines, title=None, wear=0.1, seed=17):
    """Stamped aluminium data plate with rivets."""
    body = [f'<rect width="{w}" height="{h}" rx="{h * 0.05}" fill="#B9BEC2"/>',
            f'<rect x="{h * 0.04}" y="{h * 0.04}" width="{w - h * 0.08}" height="{h - h * 0.08}" rx="{h * 0.04}" '
            f'fill="none" stroke="#3A3E42" stroke-width="{h * 0.015}"/>']
    for x, y in ((0.06, 0.12), (0.94, 0.12), (0.06, 0.88), (0.94, 0.88)):
        body.append(f'<circle cx="{w * x}" cy="{h * y}" r="{h * 0.035}" fill="#8A9095" stroke="#50555A" stroke-width="2"/>')
    y = h * 0.2
    if title:
        body.append(f'<text x="{w / 2}" y="{h * 0.27}" text-anchor="middle" font-family="Barlow Condensed Black" '
                    f'font-size="{h * 0.17}" fill="#22262A" letter-spacing="3">{esc(title)}</text>')
        y = h * 0.42
    ls = (h * 0.86 - y) / max(1, len(lines))
    for i, s in enumerate(lines):
        body.append(f'<text x="{w * 0.12}" y="{y + ls * (i + 0.75)}" font-family="JetBrains Mono" font-weight="700" '
                    f'font-size="{ls * 0.62}" fill="#22262A">{esc(s)}</text>')
    return svg(w, h, "".join(body), wear=wear, seed=seed)


def svg_gauge(w, h, vmax=200, unit="PSI", red=0.8, wear=0.05, seed=19, label=None):
    s = min(w, h)
    cx, cy, R = w / 2, h / 2, s * 0.46
    b = [f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="#F2F0EA" stroke="#222" stroke-width="{s * 0.02}"/>']
    a0, a1 = math.radians(225), math.radians(-45)

    def pt(a, rr):
        return cx + math.cos(a) * rr, cy - math.sin(a) * rr
    ar0 = a0 + (a1 - a0) * red
    x0, y0 = pt(ar0, R * 0.8)
    x1, y1 = pt(a1, R * 0.8)
    b.append(f'<path d="M{x0},{y0} A{R * 0.8},{R * 0.8} 0 0 1 {x1},{y1}" fill="none" stroke="#C8102E" stroke-width="{s * 0.05}"/>')
    for i in range(41):
        a = a0 + (a1 - a0) * i / 40
        big = i % 10 == 0
        xa, ya = pt(a, R * (0.72 if big else 0.8))
        xb, yb = pt(a, R * 0.88)
        b.append(f'<line x1="{xa}" y1="{ya}" x2="{xb}" y2="{yb}" stroke="#222" stroke-width="{s * (0.014 if big else 0.006)}"/>')
        if big:
            xt, yt = pt(a, R * 0.56)
            b.append(f'<text x="{xt}" y="{yt + s * 0.03}" text-anchor="middle" font-family="Barlow Condensed ExtraBold" '
                     f'font-size="{s * 0.09}" fill="#222">{int(vmax * i / 40)}</text>')
    b.append(f'<text x="{cx}" y="{cy + R * 0.42}" text-anchor="middle" font-family="Barlow Condensed ExtraBold" '
             f'font-size="{s * 0.08}" fill="#222">{unit}</text>')
    if label:
        b.append(f'<text x="{cx}" y="{cy - R * 0.25}" text-anchor="middle" font-family="Barlow Condensed ExtraBold" '
                 f'font-size="{s * 0.07}" fill="#555">{esc(label)}</text>')
    xn, yn = pt(a0 + (a1 - a0) * 0.58, R * 0.78)
    b.append(f'<line x1="{cx}" y1="{cy}" x2="{xn}" y2="{yn}" stroke="#111" stroke-width="{s * 0.025}" stroke-linecap="round"/>')
    b.append(f'<circle cx="{cx}" cy="{cy}" r="{s * 0.05}" fill="#111"/>')
    return svg(w, h, "".join(b), wear=wear, seed=seed)


def svg_logo(w, h, word, kind="slab", fg=INK, wear=0.25, seed=21, font="Barlow Condensed Black"):
    """Maker wordmarks. 'slab': knocked-out letters in a slanted black bar (paint shows through);
    'plain': letters only; 'badge': letters + underline swoosh."""
    if kind == "slab":
        sk = h * 0.28
        body = (f'<defs><mask id="ko"><rect width="{w}" height="{h}" fill="white"/>'
                f'<text x="{w / 2}" y="{h * 0.78}" text-anchor="middle" font-family="{font}" font-style="italic" '
                f'font-size="{h * 0.82}" letter-spacing="{h * 0.04}" fill="black">{esc(word)}</text></mask></defs>'
                f'<path d="M{sk},0 L{w},0 L{w - sk},{h} L0,{h} Z" fill="{fg}" mask="url(#ko)"/>')
    elif kind == "badge":
        body = (f'<text x="{w / 2}" y="{h * 0.7}" text-anchor="middle" font-family="{font}" font-size="{h * 0.78}" '
                f'letter-spacing="{h * 0.03}" fill="{fg}">{esc(word)}</text>'
                f'<rect x="{w * 0.04}" y="{h * 0.82}" width="{w * 0.92}" height="{h * 0.08}" fill="{fg}"/>')
    else:
        body = (f'<text x="{w / 2}" y="{h * 0.8}" text-anchor="middle" font-family="{font}" font-size="{h * 0.9}" '
                f'letter-spacing="{h * 0.03}" fill="{fg}">{esc(word)}</text>')
    return svg(w, h, body, wear=wear, seed=seed)


class Atlas:
    """Pack decal cells (shelf packing), render them in one PNG with decals.mjs, expose a label_ material."""

    def __init__(self, machine_id, width=2048, mat_name=None, rough=0.55, metal=0.0):
        self.id = machine_id
        self.items = []
        self.rects = {}
        self.size = (width, width)
        self.mat_name = mat_name or f"label_{machine_id}_decals"
        self.rough, self.metal = rough, metal

    def add(self, key, w, h, svg_str, fit=False, align="center", pad=0.04):
        self.items.append(dict(key=key, w=int(w), h=int(h), svg=svg_str, fit=fit, align=align, pad=pad))

    def build(self):
        W = self.size[0]
        x = y = shelf = 0
        gap = 10
        for it in sorted(self.items, key=lambda i: -i["h"]):
            if x + it["w"] > W:
                x, y, shelf = 0, y + shelf + gap, 0
            it["x"], it["y"] = x, y
            self.rects[it["key"]] = (x, y, it["w"], it["h"])
            x += it["w"] + gap
            shelf = max(shelf, it["h"])
        H = 256
        while H < y + shelf:
            H *= 2
        self.size = (W, H)
        out = os.path.join(DECALS, f"{self.id}_decals.png")
        job = dict(width=W, height=H, out=out, items=self.items)
        jp = os.path.join(DECALS, f"{self.id}_job.json")
        os.makedirs(DECALS, exist_ok=True)
        with open(jp, "w") as f:
            json.dump(job, f)
        env = dict(os.environ, FONTCONFIG_FILE=os.path.join(HERE, "fonts", "fonts.conf"))
        node = os.path.expanduser("~/.local/bin/node")
        node = node if os.path.exists(node) else "node"
        r = subprocess.run([node, os.path.join(HERE, "decals.mjs"), jp], env=env, capture_output=True, text=True,
                           cwd=PROJECT)
        if r.returncode != 0:
            raise RuntimeError("decal render failed: " + r.stderr[-2000:])
        print(r.stdout.strip())
        os.remove(jp)
        img = bpy.data.images.load(out, check_existing=False)
        img.name = f"{self.id}_decals.png"
        m = bpy.data.materials.new(self.mat_name)
        nt = m.node_tree
        p = nt.nodes.get("Principled BSDF")
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = img
        tex.interpolation = "Cubic"
        nt.links.new(tex.outputs["Color"], p.inputs["Base Color"])
        nt.links.new(tex.outputs["Alpha"], p.inputs["Alpha"])
        p.inputs["Roughness"].default_value = self.rough
        p.inputs["Metallic"].default_value = self.metal
        m.surface_render_method = "BLENDED"
        m.use_backface_culling = True
        return self


# ---------------------------------------------------------------- machine container

class Machine:
    def __init__(self, mid):
        bk.reset()
        self.id = mid
        bpy.context.scene.render.fps = FPS
        self.parts = {}
        self.order = []
        self.empties = {}
        self.objs = {}
        self.atlas = Atlas(mid)
        self.root = bpy.data.objects.new(mid, None)
        bpy.context.scene.collection.objects.link(self.root)
        self.root.empty_display_size = 0.5
        self.clips = {}

    def part(self, name, origin=(0, 0, 0), parent=None):
        p = Part(self, name, origin, parent)
        self.parts[name] = p
        self.order.append(name)
        return p

    def empty(self, name, loc, parent=None, q=None, beam=None):
        """Named node. beam=dir: orient so three.js local -Z (= Blender local +Y) points along dir."""
        self.empties[name] = (V(loc), parent, q if beam is None else V(beam).normalized().to_track_quat("Y", "Z"))

    # ------------------------------------------------------------ build
    def finish(self, grime=True, rays=20, **gk):
        for name in self.order:
            p = self.parts[name]
            if not p.F:
                continue
            me = bpy.data.meshes.new(name)
            par = self.parts[p.parent].origin if p.parent else V((0, 0, 0))
            me.from_pydata([V(v) - p.origin for v in p.V], [], p.F)
            for mn in p.mats:
                if mn.startswith("label_"):
                    me.materials.append(bpy.data.materials[mn])
                else:
                    me.materials.append(material(mn))
            me.polygons.foreach_set("material_index", p.FM)
            uvl = me.uv_layers.new(name="UVMap")
            flat = [c for uv in p.UV for c in uv]
            uvl.data.foreach_set("uv", flat)
            me.validate(clean_customdata=False)
            me.update()
            me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
            me.set_sharp_from_angle(angle=math.radians(p.sharp))
            o = bpy.data.objects.new(name, me)
            bpy.context.scene.collection.objects.link(o)
            o.parent = self.objs[p.parent] if p.parent else self.root
            o.location = p.origin - par
            if p.place:
                o.location = V(p.place[0])
                o.rotation_mode = "QUATERNION"
                o.rotation_quaternion = p.place[1]
            wn = o.modifiers.new("WN", "WEIGHTED_NORMAL")
            wn.keep_sharp = True
            wn.weight = 50
            wn.mode = "FACE_AREA"
            bk.select([o])
            bpy.ops.object.modifier_apply(modifier="WN")
            p.obj = o
            self.objs[name] = o
        for name, (loc, parent, q) in self.empties.items():
            e = bpy.data.objects.new(name, None)
            e.empty_display_type = "ARROWS"
            e.empty_display_size = 0.25
            bpy.context.scene.collection.objects.link(e)
            if parent:
                po = self.objs[parent]
                e.parent = po
                e.location = loc - self.parts[parent].origin
            else:
                e.parent = self.root
                e.location = loc
            if q is not None:
                e.rotation_mode = "QUATERNION"
                e.rotation_quaternion = q
            self.objs[name] = e
        bpy.context.view_layer.update()
        if grime:
            bake_grime([o for o in self.objs.values() if o.type == "MESH"], rays=rays, **gk)

    # ------------------------------------------------------------ animation
    def clip(self, name, seconds, solve, animated):
        """Sample solve(t in [0,1]) every frame -> {obj_name: dict(loc=, q=, s=)} (missing = rest).
        Every name in `animated` is keyed in this clip so crossfades always reset cleanly."""
        n = max(1, round(seconds * FPS))
        objs = [self.objs[a] for a in animated]
        rest = {o: (o.location.copy(), o.rotation_quaternion.copy() if o.rotation_mode == "QUATERNION"
                    else o.rotation_euler.to_quaternion(), o.scale.copy()) for o in objs}
        self.rest = getattr(self, "rest", {})
        for o in objs:
            self.rest.setdefault(o.name, rest[o])
        rest = {o: self.rest[o.name] for o in objs}
        acts = {}
        for o in objs:
            ad = o.animation_data or o.animation_data_create()
            act = bpy.data.actions.new(f"{name}__{o.name}")
            act.use_fake_user = True
            ad.action = act
            o.rotation_mode = "QUATERNION"
            acts[o] = act
        prevq = {o: None for o in objs}
        for f in range(n + 1):
            t = f / n
            pose = solve(t) if solve else {}
            for o in objs:
                L, Q, S = rest[o]
                d = pose.get(o.name, {})
                loc = V(d["loc"]) if "loc" in d else L
                q = Quaternion(d["q"]) if "q" in d else Q
                s = V(d["s"]) if "s" in d else S
                if prevq[o] is not None and q.dot(prevq[o]) < 0:
                    q = -q
                prevq[o] = q
                o.location, o.rotation_quaternion, o.scale = loc, q, s
                o.keyframe_insert("location", frame=f)
                o.keyframe_insert("rotation_quaternion", frame=f)
                o.keyframe_insert("scale", frame=f)
        for o in objs:
            ad = o.animation_data
            tr = ad.nla_tracks.new()
            tr.name = name
            st = tr.strips.new(name, 0, acts[o])
            st.name = name
            tr.mute = True
            ad.action = None
            L, Q, S = rest[o]
            o.location, o.rotation_quaternion, o.scale = L, Q, S
        self.clips[name] = (seconds, acts)

    def pose(self, clip, t):
        """Put every animated object at clip time t (0..1) for a preview render."""
        seconds, acts = self.clips[clip]
        n = max(1, round(seconds * FPS))
        for o, act in acts.items():
            o.animation_data.action = act
        bpy.context.scene.frame_set(int(round(t * n)))

    def unpose(self):
        for seconds, acts in self.clips.values():
            for o in acts:
                o.animation_data.action = None
                if o.name in self.rest:
                    o.location, o.rotation_quaternion, o.scale = self.rest[o.name]
        bpy.context.scene.frame_set(0)

    # ------------------------------------------------------------ output
    def meshes(self):
        return [o for o in self.objs.values() if o.type == "MESH"]

    def bounds(self):
        pts = []
        bpy.context.view_layer.update()
        for o in self.meshes():
            M = o.matrix_world
            pts += [M @ V(c) for c in o.bound_box]
        lo = V((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
        hi = V((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
        return lo, hi

    def report(self, limits=LIMITS):
        if TRISTAT:
            print("[tristat] top contributors (part:script line -> tris):")
            for k, v in TRISTAT.most_common(40):
                print(f"   {k:28s} {v}")
        lo, hi = self.bounds()
        size = hi - lo
        tri = 0
        rows = []
        for o in self.meshes():
            t = sum(len(p.vertices) - 2 for p in o.data.polygons)
            tri += t
            rows.append(f"{o.name}:{t}")
        print(f"[{self.id}] tris {tri}  ({', '.join(rows)})")
        print(f"[{self.id}] bounds x {lo.x:.2f}..{hi.x:.2f}  y {lo.y:.2f}..{hi.y:.2f}  z {lo.z:.2f}..{hi.z:.2f}  "
              f"size W{size.x:.2f} L{size.y:.2f} H{size.z:.2f}")
        ok = size.x <= limits[0] + 1e-3 and size.y <= limits[1] + 1e-3 and size.z <= limits[2] + 1e-3
        print(f"[{self.id}] fits alcove limit {limits}: {'YES' if ok else 'NO'}")
        print(f"[{self.id}] empties: {sorted(self.empties)}  clips: {sorted(self.clips)}")
        return tri, size

    def export(self, stem):
        grime_preview(False)
        path = os.path.abspath(stem if stem.endswith(".glb") else stem + ".glb")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        objs = [self.root] + list(self.root.children_recursive)
        bk.select(objs, active=self.root)
        bpy.ops.export_scene.gltf(
            filepath=path, export_format="GLB", use_selection=True, export_apply=True, export_yup=True,
            export_animations=True, export_animation_mode="NLA_TRACKS", export_merge_animation="NLA_TRACK",
            export_optimize_animation_keep_anim_object=True, export_force_sampling=True,
            export_vertex_color="NAME", export_vertex_color_name="grime", export_all_vertex_colors=False,
            export_meshopt_compression_enable=True, export_texcoords=True, export_normals=True,
            export_image_format="AUTO", export_extras=False, export_cameras=False, export_lights=False)
        print(f"[{self.id}] exported {path} ({os.path.getsize(path) / 1024:.0f} KB)")
        return path

    def save_blend(self):
        bk.save(os.path.join(HERE, "blend", f"{self.id}.blend"))

    # ------------------------------------------------------------ previews
    def render(self, views, res=(960, 720), samples=20, mood=False, tag=""):
        """views: [(name, cam_loc, target, lens)] -> previews/<id>_<name>.png"""
        grime_preview(True)
        s = bpy.context.scene
        for o in list(bpy.data.objects):
            if o.name.startswith("_pv"):
                bpy.data.objects.remove(o, do_unlink=True)
        coll = bpy.data.collections.get("_pv") or bpy.data.collections.new("_pv")
        if coll.name not in s.collection.children:
            s.collection.children.link(coll)

        def add(o):
            coll.objects.link(o)
            return o
        w = s.world or bpy.data.worlds.new("W")
        s.world = w
        try:
            w.use_nodes = True
        except Exception:
            pass
        bg = w.node_tree.nodes.get("Background")
        bg.inputs["Color"].default_value = bk.hex_lin("#0c0d10" if mood else "#23262c")
        bg.inputs["Strength"].default_value = 0.25 if mood else 1.0
        g = bpy.data.meshes.new("_pv_ground")
        g.from_pydata([(-40, -40, 0), (40, -40, 0), (40, 40, 0), (-40, 40, 0)], [], [(0, 1, 2, 3)])
        go = add(bpy.data.objects.new("_pv_ground", g))
        g.materials.append(bk.mat("_pv_ground", "#2b2a28" if not mood else "#1c1b1a", rough=0.92))
        lo, hi = self.bounds()
        ctr = (lo + hi) / 2
        rad = (hi - lo).length / 2

        def light(name, kind, energy, loc, size=1.0, color="#ffffff", target=None, spot=None):
            ld = bpy.data.lights.new("_pv" + name, kind)
            ld.energy = energy
            ld.color = bk.hex_lin(color)[:3]
            if kind == "AREA":
                ld.size = size
            if kind == "SPOT":
                ld.spot_size = math.radians(spot or 45)
                ld.spot_blend = 0.6
                ld.shadow_soft_size = 0.05
            o = add(bpy.data.objects.new("_pv" + name, ld))
            o.location = loc
            tgt = V(target) if target is not None else ctr
            o.rotation_mode = "QUATERNION"
            o.rotation_quaternion = (tgt - V(loc)).to_track_quat("-Z", "Y")
            return o
        if mood:
            light("key", "SPOT", 900, ctr + V((-2.5, -rad * 1.6, rad * 0.9)), color="#dfe8ff", spot=50)
            light("warm", "POINT", 600, ctr + V((rad * 0.9, rad * 0.3, rad * 0.8)), color="#ffb469")
            light("rim", "AREA", 500, ctr + V((0, rad * 1.5, rad)), size=rad, color="#ffcf9a")
        else:
            light("key", "AREA", 220 * rad ** 2, ctr + V((-rad * 1.2, -rad * 1.4, rad * 1.6)), size=rad * 1.4,
                  color="#fff1dc")
            light("fill", "AREA", 70 * rad ** 2, ctr + V((rad * 1.6, -rad * 0.6, rad * 0.6)), size=rad * 2,
                  color="#d8e4ff")
            light("rim", "AREA", 160 * rad ** 2, ctr + V((rad * 0.4, rad * 1.6, rad * 1.2)), size=rad * 1.5)
        cam_data = bpy.data.cameras.new("_pv_cam")
        cam = add(bpy.data.objects.new("_pv_cam", cam_data))
        s.camera = cam
        s.render.resolution_x, s.render.resolution_y = res
        s.render.resolution_percentage = 100
        s.render.engine = "BLENDER_EEVEE"
        samples = int(os.environ.get("RENDER_SAMPLES", samples))
        s.eevee.taa_render_samples = samples
        try:
            s.eevee.use_raytracing = os.environ.get("RENDER_RT", "0") == "1"
        except Exception:
            pass
        if os.environ.get("RENDER_SCALE"):
            res = tuple(int(r * float(os.environ["RENDER_SCALE"])) for r in res)
            s.render.resolution_x, s.render.resolution_y = res
        s.view_settings.view_transform = "AgX"
        try:
            s.view_settings.look = "AgX - Medium High Contrast"
        except Exception:
            pass
        s.render.image_settings.file_format = "PNG"
        outs = []
        for name, loc, tgt, lens in views:
            cam_data.lens = lens
            cam_data.clip_start = 0.02
            cam_data.clip_end = 200
            cam.location = loc
            cam.rotation_mode = "QUATERNION"
            cam.rotation_quaternion = (V(tgt) - V(loc)).to_track_quat("-Z", "Y")
            path = os.path.join(PREVIEWS, f"{self.id}{tag}_{name}.png")
            s.render.filepath = path
            t0 = time.time()
            bpy.ops.render.render(write_still=True)
            outs.append(path)
            print(f"[{self.id}] preview {path}  ({time.time() - t0:.1f}s)")
        return outs


# ---------------------------------------------------------------- grime bake (AO + low dirt + noise -> COLOR_0)

def _hemi(n):
    out = []
    ga = math.pi * (3 - math.sqrt(5))
    for i in range(n):
        u = (i + 0.5) / n
        r = math.sqrt(u)
        th = i * ga
        out.append((r * math.cos(th), r * math.sin(th), math.sqrt(max(0.0, 1 - u))))
    return out


def bake_grime(objs, rays=20, dist=0.55, strength=0.95, low=0.32, low_h=0.7, noise_amt=0.16, floor=True, seed=1.7,
               lo_clamp=0.2):
    """Cosine-weighted ray AO against the whole machine (+ floor plane), darker near the floor, blotchy noise.
    Writes FLOAT_COLOR point attribute 'grime' (exported as COLOR_0). 1 = clean."""
    bpy.context.view_layer.update()
    verts, polys = [], []
    for o in objs:
        M = o.matrix_world
        base = len(verts)
        verts.extend(M @ v.co for v in o.data.vertices)
        polys.extend([base + i for i in p.vertices] for p in o.data.polygons)
    if floor:
        b = len(verts)
        verts.extend([V((-30, -30, -0.001)), V((30, -30, -0.001)), V((30, 30, -0.001)), V((-30, 30, -0.001))])
        polys.append([b, b + 1, b + 2, b + 3])
    bvh = BVHTree.FromPolygons(verts, polys, epsilon=0.0)
    dirs = _hemi(rays)
    total = 0
    for o in objs:
        me = o.data
        M = o.matrix_world
        N3 = M.to_3x3().inverted().transposed()
        clean_v = set()
        for p in me.polygons:
            mn = me.materials[p.material_index].name if me.materials else ""
            if mn in CLEAN:
                clean_v.update(p.vertices)
        vals = []
        for v in me.vertices:
            if v.index in clean_v:
                vals.extend((1.0, 1.0, 1.0, 1.0))
                continue
            pw = M @ v.co
            n = (N3 @ v.normal).normalized()
            t = n.orthogonal().normalized()
            bb = n.cross(t)
            ph = (v.index * 2.399963) % math.tau
            c, s = math.cos(ph), math.sin(ph)
            t, bb = t * c + bb * s, bb * c - t * s
            org = pw + n * 0.004
            occ = 0.0
            for dx, dy, dz in dirs:
                d = t * dx + bb * dy + n * dz
                hit = bvh.ray_cast(org, d, dist)
                if hit[0] is not None:
                    occ += 1.0 - 0.6 * (hit[3] / dist)
            ao = 1.0 - strength * occ / len(dirs)
            hz = max(0.0, pw.z)
            dirt = 1.0 - low * max(0.0, 1.0 - hz / low_h) ** 1.6
            nz = noise.noise(pw * 1.3 + V((seed, seed * 2, seed * 3)))
            nz2 = noise.noise(pw * 5.1 + V((seed * 3, seed, seed * 2)))
            blot = 1.0 - noise_amt * max(0.0, nz * 0.8 + nz2 * 0.35 + 0.15)
            up = 1.0 - 0.06 * max(0.0, n.z)  # dust settles on upward faces
            val = max(lo_clamp, min(1.0, ao * dirt * blot * up))
            vals.extend((val, val, val, 1.0))
        attr = me.color_attributes.new("grime", "FLOAT_COLOR", "POINT")
        attr.data.foreach_set("color", vals)
        me.color_attributes.active_color = attr
        total += len(me.vertices)
    print(f"[grime] baked {total} verts x {rays} rays")


def args():
    a = bk.args()
    stem = a[0] if a else None
    flags = set(a[1:])
    return stem, flags
