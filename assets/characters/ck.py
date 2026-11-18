"""ck: character kit shared by MOTHERLODE's character scripts (viewmodel.py, miner.py).

Run through `bl` (which puts ~/blender-kit on sys.path, so `import bk` works); the scripts add this folder
to sys.path themselves. Everything is metres, Blender Z-up. glTF export converts (x, y, z) -> (x, z, -y).

What lives here:
  * maths: easing, frames (bone convention: local Y along the bone, Z = "up"/dorsal hint, X = Y x Z)
  * MeshData: a tiny list-based mesh builder with per-face materials, per-loop UVs in metres and per-vertex
    bone weights decided at construction time
  * remesh_transfer: voxel-union a multi-part organic mesh, decimate it, and carry weights + materials over
    from the construction parts by nearest-surface lookup
  * bake_ao: ray-cast ambient occlusion into the COLOR_0 grime attribute (1 = clean, darker = occluded)
  * Rig: rest frames -> Blender armature, armature-space poses -> pose-bone basis keys, numeric two-bone IK
  * ClipWriter: writes one named glTF clip straight into F-curves (slotted actions, Blender 5.x) + NLA track
  * export_glb (meshopt), preview cameras/lights
"""
import math
import random

import bmesh
import bpy
from bpy_extras import anim_utils
from mathutils import Matrix, Quaternion, Vector
from mathutils.bvhtree import BVHTree
from mathutils.interpolate import poly_3d_calc

import bk

V = Vector
TAU = math.tau


# ====================================================================== maths

def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def lerp(a, b, t):
    return a + (b - a) * t


def smoothstep(a, b, x):
    if a == b:
        return 0.0 if x < a else 1.0
    t = clamp((x - a) / (b - a))
    return t * t * (3 - 2 * t)


def ease_in(t, p=2.0):
    return clamp(t) ** p


def ease_out(t, p=2.0):
    return 1 - (1 - clamp(t)) ** p


def ease_io(t, p=2.0):
    t = clamp(t)
    return 0.5 * (2 * t) ** p if t < 0.5 else 1 - 0.5 * (2 - 2 * t) ** p


def back_out(t, s=1.6):
    t = clamp(t) - 1
    return t * t * ((s + 1) * t + s) + 1


def basis(y, z_hint):
    """3x3 rotation (columns X, Y, Z): Y = y, Z = z_hint made orthogonal, X = Y x Z (right-handed)."""
    y = V(y).normalized()
    z = V(z_hint)
    z = z - y * y.dot(z)
    if z.length < 1e-9:
        z = y.orthogonal()
    z.normalize()
    x = y.cross(z)
    return Matrix((x, y, z)).transposed()


def frame(pos, y, z_hint):
    m = basis(y, z_hint).to_4x4()
    m.translation = V(pos)
    return m


def rot(axis, deg):
    return Matrix.Rotation(math.radians(deg), 4, axis)


def T(x, y=None, z=None):
    if y is None:
        return Matrix.Translation(V(x))
    return Matrix.Translation((x, y, z))


def mirror_x_matrix(m):
    """Mirror a rigid frame across the YZ plane and keep it right-handed by flipping its local X axis."""
    S = Matrix.Diagonal((-1, 1, 1, 1))
    return S @ m @ S


def zframe(pos, z, y_hint):
    """4x4 frame with Z exactly along z, Y = y_hint made orthogonal, X = Y x Z."""
    z = V(z).normalized()
    y = V(y_hint) - z * z.dot(V(y_hint))
    if y.length < 1e-9:
        y = z.orthogonal()
    y.normalize()
    x = y.cross(z)
    m = Matrix((x, y, z)).transposed().to_4x4()
    m.translation = V(pos)
    return m


class Track:
    """Vector keys over time, cubic Hermite with time-aware (non-uniform Catmull-Rom) tangents.
    keys: [(t, vec)] or [(t, vec, opts)] with opts: brk=True (velocity break: arrive at speed, leave fresh;
    use it for impacts), hold=True (zero velocity), v=Vector (explicit velocity), ease=fn (warp the segment
    starting at this key). loop=True: last key must equal the first; tangents wrap. Non-loop ends hold."""

    def __init__(self, keys, loop=False):
        self.t = [float(k[0]) for k in keys]
        self.p = [V(k[1]) for k in keys]
        self.o = [(k[2] if len(k) > 2 else {}) for k in keys]
        self.loop = loop
        n = len(self.t)
        T = self.t[-1] - self.t[0]
        self.vin, self.vout = [None] * n, [None] * n
        for i in range(n):
            o = self.o[i]
            if "v" in o:
                self.vin[i] = self.vout[i] = V(o["v"])
                continue
            if o.get("hold"):
                self.vin[i] = self.vout[i] = V((0, 0, 0))
                continue
            if i == 0 or i == n - 1:
                if loop:
                    tp, pp = self.t[n - 2] - T, self.p[n - 2]
                    tn, pn = self.t[1] + T, self.p[1]
                    v = (pn - pp) / (tn - tp)
                    self.vin[i] = self.vout[i] = v
                else:
                    self.vin[i] = self.vout[i] = V((0, 0, 0))
                continue
            if o.get("brk"):
                self.vin[i] = (self.p[i] - self.p[i - 1]) / (self.t[i] - self.t[i - 1])
                self.vout[i] = (self.p[i + 1] - self.p[i]) / (self.t[i + 1] - self.t[i])
                continue
            v = (self.p[i + 1] - self.p[i - 1]) / (self.t[i + 1] - self.t[i - 1])
            self.vin[i] = self.vout[i] = v
        for i in range(n):  # a break key's neighbours aim straight at it
            if self.o[i].get("brk") and i > 0 and not self.o[i - 1]:
                pass

    def at(self, t):
        ts = self.t
        if t <= ts[0]:
            return self.p[0].copy()
        if t >= ts[-1]:
            return self.p[-1].copy()
        i = 0
        while i < len(ts) - 2 and t >= ts[i + 1]:
            i += 1
        h = ts[i + 1] - ts[i]
        u = (t - ts[i]) / h
        e = self.o[i].get("ease")
        if e:
            u = e(u)
        u2, u3 = u * u, u * u * u
        return (self.p[i] * (2 * u3 - 3 * u2 + 1) + self.vout[i] * (h * (u3 - 2 * u2 + u))
                + self.p[i + 1] * (-2 * u3 + 3 * u2) + self.vin[i + 1] * (h * (u3 - u2)))


def quat_cont(q, prev):
    if prev is not None and q.dot(prev) < 0:
        q = -q
    return q


def catmull(p0, p1, p2, p3, t):
    t2, t3 = t * t, t * t * t
    return 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3)


# ====================================================================== materials

LIB = {  # preview look for library names (the game swaps them for photoscanned PBR sets by name)
    "skin": ("#b98262", 0.55, 0.0),
    "fabric_hivis": ("#ff5a0a", 0.78, 0.0),
    "fabric_shirt": ("#d6d0c2", 0.85, 0.0),
    "fabric_denim": ("#3f5068", 0.85, 0.0),
    "fabric_glove": ("#4d5258", 0.88, 0.0),
    "leather": ("#9a7752", 0.6, 0.0),
    "helmet_yellow": ("#f2b705", 0.32, 0.0),
    "helmet_white": ("#f0f0ec", 0.32, 0.0),
    "steel": ("#a3a8ae", 0.36, 1.0),
    "steel_dark": ("#4a4d52", 0.48, 1.0),
    "wood_dark": ("#6e4a2c", 0.62, 0.0),
    "wood_timber": ("#94704a", 0.72, 0.0),
    "rubber": ("#1c1c1d", 0.82, 0.0),
    "plastic_black": ("#1f2124", 0.42, 0.0),
    "plastic_yellow": ("#eab307", 0.38, 0.0),
    "paint_yellow": ("#e8b400", 0.5, 0.15),
    "paint_black": ("#202124", 0.5, 0.1),
    "chrome": ("#e2e6ea", 0.08, 1.0),
    "aluminium": ("#b9bec4", 0.32, 1.0),
    "brass": ("#c79a3c", 0.32, 1.0),
    "hose_red": ("#9c2018", 0.6, 0.0),
    "cable": ("#141414", 0.55, 0.0),
    "glass_dark": ("#101418", 0.05, 0.0),
    "custom_reflective": ("#c3c7cc", 0.3, 0.7),
}


def material(name, color=None, rough=None, metal=None, emit=None, emit_strength=0.0, image=None):
    """Principled material whose base colour is `colour x COLOR_0` (the exporter writes baseColorFactor + COLOR_0)."""
    m = bpy.data.materials.get(name)
    if m is not None:
        return m
    c, r, mt = LIB.get(name, ("#bbbbbb", 0.6, 0.0))
    c = color or c
    r = r if rough is None else rough
    mt = mt if metal is None else metal
    m = bk.mat(name, c, rough=r, metal=mt)
    nt = m.node_tree
    p = nt.nodes["Principled BSDF"]
    if image is not None:
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = image
        nt.links.new(tex.outputs["Color"], p.inputs["Base Color"])
        if emit:
            nt.links.new(tex.outputs["Color"], p.inputs["Emission Color"])
            p.inputs["Emission Strength"].default_value = emit_strength
    else:
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.blend_type = "MULTIPLY"
        sock = lambda socks, ident: next(s for s in socks if s.identifier == ident)  # noqa: E731
        sock(mix.inputs, "Factor_Float").default_value = 1.0
        sock(mix.inputs, "A_Color").default_value = bk.hex_lin(c)
        attr = nt.nodes.new("ShaderNodeVertexColor")
        attr.layer_name = "Color"
        nt.links.new(attr.outputs["Color"], sock(mix.inputs, "B_Color"))
        nt.links.new(sock(mix.outputs, "Result_Color"), p.inputs["Base Color"])
        if emit:
            p.inputs["Emission Color"].default_value = bk.hex_lin(emit)
            p.inputs["Emission Strength"].default_value = emit_strength
    return m


# ====================================================================== mesh building

def ring(c, ax, ay, rx, ry, n, p=2.0, phase=0.0, fn=None):
    """Superellipse ring (counter-clockwise from ax towards ay). fn(angle, x, y) -> (x, y) can sculpt it."""
    pts = []
    e = 2.0 / p
    for k in range(n):
        a = phase + k / n * TAU
        ca, sa = math.cos(a), math.sin(a)
        x = rx * math.copysign(abs(ca) ** e, ca)
        y = ry * math.copysign(abs(sa) ** e, sa)
        if fn:
            x, y = fn(a, x, y)
        pts.append(V(c) + V(ax) * x + V(ay) * y)
    return pts


def path_frames(pts, up=(0, 0, 1)):
    """Parallel-transport frames (T, N, B) along a polyline; N starts as `up` made perpendicular."""
    pts = [V(p) for p in pts]
    n = len(pts)
    tans = []
    for i in range(n):
        d = pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]
        tans.append(d.normalized())
    t0 = tans[0]
    nrm = V(up) - t0 * t0.dot(up)
    if nrm.length < 1e-6:
        nrm = t0.orthogonal()
    nrm.normalize()
    out = [(t0, nrm, t0.cross(nrm))]
    for i in range(1, n):
        q = tans[i - 1].rotation_difference(tans[i])
        nrm = (q @ nrm)
        nrm = (nrm - tans[i] * tans[i].dot(nrm)).normalized()
        out.append((tans[i], nrm, tans[i].cross(nrm)))
    return out


class MeshData:
    """List-based mesh builder. Faces carry a material name, optional per-loop UVs and a free `part` tag;
    vertices carry optional {bone: weight} dicts."""

    def __init__(self):
        self.verts, self.vw, self.vs = [], [], []
        self.faces, self.fmat, self.fuv, self.fpart = [], [], [], []
        self.scalar = 0.0  # default per-vertex scalar for new vertices (iso-cut material zones)

    def v(self, co, w=None, sc=None):
        self.verts.append(V(co))
        self.vw.append(w)
        self.vs.append(self.scalar if sc is None else sc)
        return len(self.verts) - 1

    def f(self, idx, mat, uv=None, part=0):
        self.faces.append(tuple(idx))
        self.fmat.append(mat)
        self.fuv.append(uv)
        self.fpart.append(part)

    def grid(self, rows, mat, closed=True, uvs=None, part=0, matfn=None):
        """Quads between consecutive rows (rings) of vertex indices. uvs: per-row list of (u, v) per
        column (closed rings need n+1 columns of uvs for the seam). matfn(i, k) -> material overrides."""
        for i in range(len(rows) - 1):
            a, b = rows[i], rows[i + 1]
            n = len(a)
            for k in range(n if closed else n - 1):
                k1 = (k + 1) % n if closed else k + 1
                uv = None
                if uvs is not None:
                    ku = k + 1
                    uv = (uvs[i][k], uvs[i][ku], uvs[i + 1][ku], uvs[i + 1][k])
                m = matfn(i, k) if matfn else mat
                self.f((a[k], a[k1], b[k1], b[k]), m, uv, part)

    def cap(self, row, mat, center=None, w=None, flip=False, part=0, uvscale=1.0):
        """Fan cap over a ring (planar-ish). Returns the centre vertex index."""
        pts = [self.verts[i] for i in row]
        c = center if center is not None else sum(pts, V()) / len(pts)
        ci = self.v(c, w)
        n = len(row)
        for k in range(n):
            k1 = (k + 1) % n
            tri = (row[k1], row[k], ci) if not flip else (row[k], row[k1], ci)
            self.f(tri, mat, None, part)
        return ci

    def add(self, other):
        off = len(self.verts)
        self.verts += other.verts
        self.vw += other.vw
        self.vs += other.vs
        for f, m, uv, p in zip(other.faces, other.fmat, other.fuv, other.fpart):
            self.faces.append(tuple(i + off for i in f))
            self.fmat.append(m)
            self.fuv.append(uv)
            self.fpart.append(p)

    def transform(self, M):
        self.verts = [M @ v for v in self.verts]
        if M.determinant() < 0:
            self.faces = [tuple(reversed(f)) for f in self.faces]
            self.fuv = [tuple(reversed(u)) if u else None for u in self.fuv]
        return self

    def copy(self):
        o = MeshData()
        o.add(self)
        return o

    def tris(self):
        return sum(len(f) - 2 for f in self.faces)

    def to_object(self, name, smooth=True, recalc=False, auto_uv=True):
        me = bpy.data.meshes.new(name)
        me.from_pydata([tuple(v) for v in self.verts], [], self.faces)
        names = []
        for m in self.fmat:
            if m not in names:
                names.append(m)
        for n in names:
            me.materials.append(material(n))
        me.polygons.foreach_set("material_index", [names.index(m) for m in self.fmat])
        uvl = me.uv_layers.new(name="UVMap")
        need_auto = []
        for pi, poly in enumerate(me.polygons):
            uv = self.fuv[pi]
            if uv is None:
                need_auto.append(pi)
                continue
            for j, li in enumerate(poly.loop_indices):
                uvl.data[li].uv = uv[j]
        o = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(o)
        if recalc:
            bm = bmesh.new()
            bm.from_mesh(me)
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            bm.to_mesh(me)
            bm.free()
        if auto_uv and need_auto:
            box_uv(o, only=set(need_auto))
        me.polygons.foreach_set("use_smooth", [smooth] * len(me.polygons))
        groups = {}
        for vi, w in enumerate(self.vw):
            if not w:
                continue
            for b, x in w.items():
                if x <= 1e-4:
                    continue
                g = groups.get(b) or o.vertex_groups.new(name=b)
                groups[b] = g
                g.add([vi], x, "REPLACE")
        me.update()
        return o


def tube(md, pts, radius, n, mat, up=(0, 0, 1), p=2.0, weights=None, part=0, cap0=None, cap1=None,
         rfn=None, matfn=None, phase=0.0):
    """Rings along a polyline. radius: float | (rx, ry) | callable(i, s) -> (rx, ry). rfn(i, angle, x, y)
    sculpts ring points. weights(i, s) -> {bone: w}. Caps: None | 'flat' | ('dome', steps).
    Returns (rows, frames, s_list). UVs: u = arc length around (m), v = length along (m)."""
    pts = [V(q) for q in pts]
    fr = path_frames(pts, up)
    s_list = [0.0]
    for i in range(1, len(pts)):
        s_list.append(s_list[-1] + (pts[i] - pts[i - 1]).length)
    rows, uvs = [], []
    for i, (q, (t, nn, bb)) in enumerate(zip(pts, fr)):
        pi_ = p
        if callable(radius):
            rr_ = radius(i, s_list[i])
            rx, ry = rr_[0], rr_[1]
            if len(rr_) > 2:
                pi_ = rr_[2]
        elif isinstance(radius, (tuple, list)):
            rx, ry = radius
        else:
            rx = ry = radius
        f = (lambda a, x, y, _i=i: rfn(_i, a, x, y)) if rfn else None
        ringp = ring(q, nn, bb, rx, ry, n, pi_, phase, f)
        w = weights(i, s_list[i]) if weights else None
        rows.append([md.v(c, w) for c in ringp])
        per = [0.0]
        for k in range(n):
            per.append(per[-1] + (ringp[(k + 1) % n] - ringp[k]).length)
        uvs.append([(u, s_list[i]) for u in per])
    md.grid(rows, mat, True, uvs, part, matfn=(lambda i, k: matfn(i, k)) if matfn else None)
    for which, cap in ((0, cap0), (1, cap1)):
        if not cap:
            continue
        row = rows[0] if which == 0 else rows[-1]
        t = fr[0][0] if which == 0 else fr[-1][0]
        sign = -1 if which == 0 else 1
        w = weights(0 if which == 0 else len(pts) - 1, s_list[0 if which == 0 else -1]) if weights else None
        if cap == "flat":
            md.cap(row, mat, w=w, flip=(which == 0), part=part)
        else:
            steps = cap[1]
            depth = cap[2] if len(cap) > 2 else None
            c = sum((md.verts[i] for i in row), V()) / len(row)
            prev = row
            rad = [(md.verts[i] - c) for i in row]
            r0 = sum(r.length for r in rad) / len(rad)
            dep = depth if depth is not None else r0
            for j in range(1, steps):
                ang = j / steps * math.pi / 2
                k = math.cos(ang)
                off = t * sign * math.sin(ang) * dep
                ringp = [c + r * k + off for r in rad]
                cur = [md.v(x, w) for x in ringp]
                if which == 0:
                    md.grid([cur, prev], mat, True, None, part)
                else:
                    md.grid([prev, cur], mat, True, None, part)
                prev = cur
            tip = md.v(c + t * sign * dep, w)
            nn_ = len(prev)
            for k in range(nn_):
                k1 = (k + 1) % nn_
                if which == 0:
                    md.f((prev[k1], prev[k], tip), mat, None, part)
                else:
                    md.f((prev[k], prev[k1], tip), mat, None, part)
    return rows, fr, s_list


def lathe(md, profile, n, mat, M=None, part=0, matfn=None, phase=0.0, weights=None):
    """Revolve [(r, z), ...] around local Z (r=0 ends become poles). M places it. UVs in metres."""
    M = M or Matrix.Identity(4)
    rows, uvs = [], []
    poles = []
    s = 0.0
    prev = None
    for i, (r, z) in enumerate(profile):
        if prev is not None:
            s += math.hypot(r - prev[0], z - prev[1])
        prev = (r, z)
        w = weights(i, z) if weights else None
        if r <= 1e-6:
            poles.append((i, md.v(M @ V((0, 0, z)), w)))
            rows.append(None)
            uvs.append(None)
            continue
        row, uv = [], []
        for k in range(n):
            a = phase + k / n * TAU
            row.append(md.v(M @ V((r * math.cos(a), r * math.sin(a), z)), w))
        circ = TAU * r
        uv = [(k / n * circ, s) for k in range(n + 1)]
        rows.append(row)
        uvs.append(uv)
    for i in range(len(profile) - 1):
        a, b = rows[i], rows[i + 1]
        mat_i = matfn(i) if matfn else mat
        if a is not None and b is not None:
            md.grid([a, b], mat_i, True, [uvs[i], uvs[i + 1]], part)
        elif a is None and b is not None:
            pole = dict(poles)[i]
            for k in range(n):
                md.f((b[(k + 1) % n], b[k], pole), mat_i, None, part)
        elif a is not None and b is None:
            pole = dict(poles)[i + 1]
            for k in range(n):
                md.f((a[k], a[(k + 1) % n], pole), mat_i, None, part)
    return rows


def rbox(md, size, M=None, mat="steel", bevel=0.004, seg=2, part=0, w=None):
    """Bevelled box centred on the origin of M (via a temporary object + bevel modifier)."""
    bpy.ops.mesh.primitive_cube_add(size=1)
    o = bpy.context.object
    o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    if bevel > 0:
        b = o.modifiers.new("b", "BEVEL")
        b.width, b.segments, b.limit_method = bevel, seg, "NONE"
        b.harden_normals = False
    absorb(md, o, mat, M, part=part, w=w)


def absorb(md, obj, mat, M=None, part=0, w=None, keep_mats=False):
    """Copy an object's evaluated mesh (modifiers applied) into md through M, then delete the object."""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    me = ev.to_mesh()
    MW = (M or Matrix.Identity(4)) @ obj.matrix_world
    off = len(md.verts)
    for v in me.vertices:
        md.v(MW @ v.co, dict(w) if w else None)
    flip = MW.determinant() < 0
    names = [s.material.name if s.material else mat for s in obj.material_slots] if keep_mats else None
    for p in me.polygons:
        idx = [off + i for i in p.vertices]
        if flip:
            idx.reverse()
        m = names[p.material_index] if keep_mats and names else mat
        md.f(idx, m, None, part)
    ev.to_mesh_clear()
    bpy.data.objects.remove(obj, do_unlink=True)


def box_uv(obj, only=None, scale=1.0):
    """Box projection in metres for the given polygon indices (or all)."""
    me = obj.data
    uvl = me.uv_layers.active or me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        if only is not None and poly.index not in only:
            continue
        n = poly.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            if ax == 0:
                u, v = co.y * (1 if n.x > 0 else -1), co.z
            elif ax == 1:
                u, v = co.x * (-1 if n.y > 0 else 1), co.z
            else:
                u, v = co.x, co.y * (1 if n.z > 0 else -1)
            uvl.data[li].uv = (u * scale, v * scale)


def metric_smart_uv(obj, angle=60.0):
    """Smart UV project, then scale so 1 UV unit = 1 metre (islands keep their relative density)."""
    bk.select([obj])
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(angle), island_margin=0.002, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    me = obj.data
    uvl = me.uv_layers.active
    a3 = a2 = 0.0
    for p in me.polygons:
        a3 += p.area
        uvs = [uvl.data[li].uv for li in p.loop_indices]
        s = 0.0
        for i in range(1, len(uvs) - 1):
            e1, e2 = uvs[i] - uvs[0], uvs[i + 1] - uvs[0]
            s += abs(e1.x * e2.y - e1.y * e2.x) / 2
        a2 += s
    k = math.sqrt(a3 / a2) if a2 > 0 else 1.0
    for d in uvl.data:
        d.uv = d.uv * k


# ====================================================================== organic remesh + transfer

def cut_iso(obj, vals, thr=0.0, snap=0.12):
    """Split the mesh exactly along the isoline vals == thr (vals: per-vertex list). Returns new per-vertex values.
    Crossing edges are split at the interpolated point, then faces are split between their on-line vertices."""
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    val = {v: vals[v.index] - thr for v in bm.verts}
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
        if any(v2 in (e.other_vert(v1),) for e in v1.link_edges if e in f.edges):
            continue
        sides = [val[lp.vert] for lp in f.loops if val[lp.vert] != 0.0]
        if not sides or all(x > 0 for x in sides) or all(x < 0 for x in sides):
            continue
        try:
            bmesh.utils.face_split(f, v1, v2)
        except Exception:
            pass
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    out = [0.0] * len(bm.verts)
    bm.verts.index_update()
    for v in bm.verts:
        out[v.index] = val[v] + thr
    bm.to_mesh(me)
    bm.free()
    me.update()
    return out


def remesh_transfer(src, name, voxel, target_tris, smooth_iter=4, smooth_fac=0.5, matfn=None, keep_src=False,
                    iso=None):
    """iso = (material_if_positive, material_if_negative): carry src.vs over, cut along vs == 0, zone by sign."""
    """Voxel-union `src` (a MeshData with weights + materials), smooth, decimate to ~target_tris, then carry
    weights (barycentric from the nearest construction face) and materials onto the new surface."""
    srco = src.to_object(name + "_src", smooth=True, auto_uv=False)
    dup = srco.copy()
    dup.data = srco.data.copy()
    dup.name = name
    bpy.context.scene.collection.objects.link(dup)
    for g in list(dup.vertex_groups):
        dup.vertex_groups.remove(g)
    r = dup.modifiers.new("remesh", "REMESH")
    r.mode = "VOXEL"
    r.voxel_size = voxel
    r.use_smooth_shade = True
    bk.apply(dup)
    if smooth_iter:
        s = dup.modifiers.new("smooth", "LAPLACIANSMOOTH")
        s.iterations = smooth_iter
        s.lambda_factor = smooth_fac
        s.use_volume_preserve = True
        bk.apply(dup)
    cur = sum(len(p.vertices) - 2 for p in dup.data.polygons)
    if target_tris and cur > target_tris:
        d = dup.modifiers.new("dec", "DECIMATE")
        d.decimate_type = "COLLAPSE"
        d.ratio = target_tris / cur
        d.use_collapse_triangulate = True
        bk.apply(dup)
    if iso:
        bvh = BVHTree.FromPolygons([tuple(v) for v in src.verts], src.faces, all_triangles=False)
        vals = []
        for v in dup.data.vertices:
            loc, nrm, fi, dist = bvh.find_nearest(v.co)
            face = src.faces[fi]
            ws = poly_3d_calc([src.verts[i] for i in face], loc)
            vals.append(sum(src.vs[i] * k for i, k in zip(face, ws)))
        vals = cut_iso(dup, vals)
        pos, neg = iso
        transfer(src, dup, matfn=None, mats=False)
        me = dup.data
        me.materials.clear()
        me.materials.append(material(pos))
        me.materials.append(material(neg))
        idx = []
        for p in me.polygons:
            sv = [vals[i] for i in p.vertices]
            m = sum(sv) / len(sv)
            idx.append(0 if m > 0 else 1)
        me.polygons.foreach_set("material_index", idx)
    else:
        transfer(src, dup, matfn=matfn)
    if not keep_src:
        bpy.data.objects.remove(srco, do_unlink=True)
    me = dup.data
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    return dup


def transfer(src, dst, matfn=None, weights=True, mats=True):
    """Weights + material (+ part) from MeshData `src` onto object `dst` (both in the same space)."""
    bvh = BVHTree.FromPolygons([tuple(v) for v in src.verts], src.faces, all_triangles=False)
    me = dst.data
    if weights:
        bones = sorted({b for w in src.vw if w for b in w})
        groups = {b: (dst.vertex_groups.get(b) or dst.vertex_groups.new(name=b)) for b in bones}
        for v in me.vertices:
            loc, nrm, fi, dist = bvh.find_nearest(v.co)
            if fi is None:
                continue
            face = src.faces[fi]
            ws = poly_3d_calc([src.verts[i] for i in face], loc)
            acc = {}
            for vi, k in zip(face, ws):
                for b, x in (src.vw[vi] or {}).items():
                    acc[b] = acc.get(b, 0.0) + x * k
            tot = sum(acc.values())
            for b, x in acc.items():
                if x / max(tot, 1e-9) > 1e-4:
                    groups[b].add([v.index], x / max(tot, 1e-9), "REPLACE")
    if mats:
        names = []
        for m in src.fmat:
            if m not in names:
                names.append(m)
        me.materials.clear()
        for n in names:
            me.materials.append(material(n))
        idx = []
        for p in me.polygons:
            loc, nrm, fi, dist = bvh.find_nearest(p.center)
            m = src.fmat[fi] if fi is not None else names[0]
            if matfn:
                m = matfn(p.center, p.normal, src.fpart[fi] if fi is not None else 0, m)
                if m not in names:
                    names.append(m)
                    me.materials.append(material(m))
            idx.append(names.index(m))
        me.polygons.foreach_set("material_index", idx)


def obj_md(obj):
    """MeshData view of an object's mesh (world space) with its vertex-group weights (for transfer())."""
    md = MeshData()
    names = [g.name for g in obj.vertex_groups]
    Mw = obj.matrix_world
    for v in obj.data.vertices:
        w = {names[ge.group]: ge.weight for ge in v.groups if ge.weight > 1e-4}
        md.v(Mw @ v.co, w)
    for p in obj.data.polygons:
        md.f(list(p.vertices), "x")
    return md


def weights_from(body, shell, rigid=None):
    """Give `shell` the interpolated weights of the nearest point on `body` (or rigid {bone: 1})."""
    for g in list(shell.vertex_groups):
        shell.vertex_groups.remove(g)
    if rigid:
        for b, x in rigid.items():
            g = shell.vertex_groups.new(name=b)
            g.add(range(len(shell.data.vertices)), x, "REPLACE")
        return shell
    transfer(obj_md(body), shell, weights=True, mats=False)
    return shell


def limit_weights(obj, max_inf=4, smooth=0, smooth_fac=0.5):
    """Keep the strongest `max_inf` influences per vertex, optionally smooth over edges, renormalise."""
    me = obj.data
    nv = len(me.vertices)
    names = [g.name for g in obj.vertex_groups]
    W = [dict() for _ in range(nv)]
    for v in me.vertices:
        for ge in v.groups:
            W[v.index][names[ge.group]] = ge.weight
    if smooth:
        nb = [[] for _ in range(nv)]
        for e in me.edges:
            a, b = e.vertices
            nb[a].append(b)
            nb[b].append(a)
        for _ in range(smooth):
            new = []
            for i in range(nv):
                acc = {k: x * (1 - smooth_fac) for k, x in W[i].items()}
                if nb[i]:
                    f = smooth_fac / len(nb[i])
                    for j in nb[i]:
                        for k, x in W[j].items():
                            acc[k] = acc.get(k, 0.0) + x * f
                else:
                    acc = dict(W[i])
                new.append(acc)
            W = new
    for g in list(obj.vertex_groups):
        obj.vertex_groups.remove(g)
    groups = {}
    for i, w in enumerate(W):
        top = sorted(w.items(), key=lambda kv: -kv[1])[:max_inf]
        tot = sum(x for _, x in top)
        if tot <= 0:
            continue
        for b, x in top:
            if x / tot < 0.01:
                continue
            g = groups.get(b) or obj.vertex_groups.new(name=b)
            groups[b] = g
            g.add([i], x / tot, "REPLACE")


# ====================================================================== grime (COLOR_0)

def _hemi(n, rng):
    """Cosine-weighted directions around +Z."""
    out = []
    for i in range(n):
        u1, u2 = (i + rng.random()) / n, rng.random()
        r = math.sqrt(u1)
        a = TAU * u2
        out.append(V((r * math.cos(a), r * math.sin(a), math.sqrt(max(0.0, 1 - u1)))))
    return out


def bake_ao(objs, occluders=(), samples=28, dist=0.05, strength=0.75, power=1.0, seed=7, floor=0.35, extra=None):
    """Ray-cast AO per vertex (world space) into a POINT 'Color' attribute: 1 = open, darker = occluded.
    extra(obj, vertex_world, normal_world) -> multiplier lets callers paint wear/dirt on top."""
    rng = random.Random(seed)
    dirs = _hemi(samples, rng)
    verts, polys = [], []
    for o in list(objs) + list(occluders):
        dg = bpy.context.evaluated_depsgraph_get()
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        off = len(verts)
        Mw = o.matrix_world
        verts += [Mw @ v.co for v in me.vertices]
        polys += [tuple(off + i for i in p.vertices) for p in me.polygons]
        ev.to_mesh_clear()
    bvh = BVHTree.FromPolygons(verts, polys, all_triangles=False)
    for o in objs:
        me = o.data
        Mw = o.matrix_world
        Mn = Mw.to_3x3().inverted().transposed()
        ca = me.color_attributes.get("Color")
        if ca is not None:
            me.color_attributes.remove(ca)
        ca = me.color_attributes.new("Color", "BYTE_COLOR", "POINT")
        me.color_attributes.active_color = ca
        try:
            me.color_attributes.render_color_index = me.color_attributes.active_color_index
        except Exception:
            pass
        vals = []
        for v in me.vertices:
            p = Mw @ v.co
            n = (Mn @ v.normal).normalized()
            rq = n.to_track_quat("Z", "Y")
            hit = 0.0
            o0 = p + n * 0.0008
            for d in dirs:
                wd = rq @ d
                loc, _, _, dd = bvh.ray_cast(o0, wd, dist)
                if loc is not None:
                    hit += 1.0 - (dd / dist) ** 0.5 * 0.5
            ao = 1.0 - strength * (hit / samples) ** power
            if extra:
                ao *= extra(o, p, n)
            vals.append(max(floor, min(1.0, ao)))
        for i, a in enumerate(vals):
            ca.data[i].color = (a, a, a, 1.0)


def paint_mul(obj, fn):
    """Multiply the POINT 'Color' attribute by fn(vertex_co_local, normal_local) (wear, stubble, hair...)."""
    me = obj.data
    ca = me.color_attributes.get("Color")
    for v in me.vertices:
        k = fn(v.co, v.normal)
        c = ca.data[v.index].color
        ca.data[v.index].color = (c[0] * k, c[1] * k, c[2] * k, 1.0)


# ====================================================================== rig + IK

class Rig:
    """Bones as rest frames in armature space. Pose = {bone: 4x4 armature-space matrix}."""

    def __init__(self, name):
        self.name = name
        self.order = []
        self.parent = {}
        self.rest = {}
        self.length = {}
        self.deform = {}
        self.obj = None

    def add(self, name, parent, head, y, z_hint, length, deform=True):
        self.order.append(name)
        self.parent[name] = parent
        self.rest[name] = frame(head, y, z_hint)
        self.length[name] = length
        self.deform[name] = deform
        return self.rest[name]

    def add_frame(self, name, parent, M, length, deform=True):
        self.order.append(name)
        self.parent[name] = parent
        self.rest[name] = M.copy()
        self.length[name] = length
        self.deform[name] = deform

    def head(self, b):
        return self.rest[b].translation.copy()

    def tail(self, b):
        return self.rest[b] @ V((0, self.length[b], 0))

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
        worst = 0.0
        for b in self.order:
            ml = arm.bones[b].matrix_local
            for i in range(3):
                for j in range(3):
                    worst = max(worst, abs(ml[i][j] - self.rest[b][i][j]))
        if worst > 1e-3:
            print(f"[ck] WARNING rest frame mismatch {worst:.4f}")
        # use Blender's exact rest matrices from now on (roll quantisation)
        for b in self.order:
            self.rest[b] = arm.bones[b].matrix_local.copy()
        for pb in o.pose.bones:
            pb.rotation_mode = "QUATERNION"
        self.obj = o
        return o

    def local_rest(self, b):
        p = self.parent[b]
        return self.rest[b] if p is None else self.rest[p].inverted() @ self.rest[b]

    def fk(self, b, P, local_rot):
        """Pose matrix of bone b given its parent's pose (in P) and a local rotation (4x4)."""
        p = self.parent[b]
        base = P[p] if p else Matrix.Identity(4)
        return base @ self.local_rest(b) @ local_rot

    def basis(self, P):
        out = {}
        for b in self.order:
            p = self.parent[b]
            if p is None:
                out[b] = self.rest[b].inverted() @ P[b]
            else:
                out[b] = self.local_rest(b).inverted() @ P[p].inverted() @ P[b]
        return out


def two_bone(S, W, a, b, pole):
    """Elbow position for shoulder S, wrist target W, segment lengths a, b; elbow bends towards `pole`
    (a point). Returns (E, W_reached, hinge_normal, ok)."""
    S, W, pole = V(S), V(W), V(pole)
    d_vec = W - S
    d = d_vec.length
    u = d_vec / max(d, 1e-9)
    ok = True
    lo, hi = abs(a - b) + 1e-4, a + b - 1e-4
    if d > hi or d < lo:
        ok = False
    d = clamp(d, lo, hi)
    ca = (a * a + d * d - b * b) / (2 * a * d)
    sa = math.sqrt(max(0.0, 1 - ca * ca))
    pv = pole - S
    v = pv - u * pv.dot(u)
    if v.length < 1e-6:
        v = u.orthogonal()
    v.normalize()
    E = S + (u * ca + v * sa) * a
    return E, S + u * d, u.cross(v).normalized(), ok


def limb(rig, ua, fa, hd, S, W, end_M, pole, twist_share=0.5):
    """Generic two-bone chain (arm or leg): pose matrices for ua/fa/hd reaching end_M (translation = target)."""
    a, b = rig.length[ua], rig.length[fa]
    E, Wr, n, ok = two_bone(S, W, a, b, pole)
    yu = (E - S).normalized()
    yf = (Wr - E).normalized()
    Mu = frame(S, yu, n.cross(yu))
    Mf = frame(E, yf, n.cross(yf))
    hz = end_M.to_3x3() @ V((0, 0, 1))
    hz_p = (hz - yf * yf.dot(hz))
    if hz_p.length > 1e-6:
        hz_p.normalize()
        fz = Mf.to_3x3() @ V((0, 0, 1))
        ang = math.atan2(yf.dot(fz.cross(hz_p)), fz.dot(hz_p))
        Mf = Mf @ Matrix.Rotation(ang * twist_share, 4, "Y")
    H = end_M.copy()
    H.translation = Wr
    return {ua: Mu, fa: Mf, hd: H}, ok, E


def arm_chain(rig, side, S, W, hand_M, pole, twist_share=0.5):
    """Pose matrices for upperarm/forearm/hand of one side reaching hand_M (4x4, translation = wrist)."""
    ua, fa = f"upperarm.{side}", f"forearm.{side}"
    a, b = rig.length[ua], rig.length[fa]
    E, Wr, n, ok = two_bone(S, W, a, b, pole)
    yu = (E - S).normalized()
    yf = (Wr - E).normalized()
    # hinge: elbow flexes about local X = -n (keeps the rest convention: forearm bends towards +Z?)
    Mu = frame(S, yu, n.cross(yu))
    Mf = frame(E, yf, n.cross(yf))
    # distribute the wrist twist into the forearm
    hz = hand_M.to_3x3() @ V((0, 0, 1))
    hz_p = (hz - yf * yf.dot(hz)).normalized()
    fz = Mf.to_3x3() @ V((0, 0, 1))
    ang = math.atan2(yf.dot(fz.cross(hz_p)), fz.dot(hz_p))
    Mf = Mf @ Matrix.Rotation(ang * twist_share, 4, "Y")
    H = hand_M.copy()
    H.translation = Wr
    return {ua: Mu, fa: Mf, f"hand.{side}": H}, ok, E


# ====================================================================== clips

class ClipWriter:
    """Collect per-frame basis matrices for every bone, then write one action + NLA track (one glTF clip)."""

    def __init__(self, rig, name):
        self.rig, self.name = rig, name
        self.keys = {b: [] for b in rig.order}
        self.prev = {b: None for b in rig.order}

    def add(self, frame_no, basis):
        for b in self.rig.order:
            m = basis[b]
            q = quat_cont(m.to_quaternion().normalized(), self.prev[b])
            self.prev[b] = q
            self.keys[b].append((frame_no, q, m.to_translation()))

    def finish(self, loc_bones=()):
        arm = self.rig.obj
        act = bpy.data.actions.new(self.name)
        act.use_fake_user = True
        slot = act.slots.new(id_type="OBJECT", name=arm.name)
        cb = anim_utils.action_ensure_channelbag_for_slot(act, slot)
        lin = bpy.types.Keyframe.bl_rna.properties["interpolation"].enum_items["LINEAR"].value
        for b in self.rig.order:
            ks = self.keys[b]
            n = len(ks)
            chans = [("rotation_quaternion", 4, lambda k, i: k[1][i])]
            if b in loc_bones:
                chans.append(("location", 3, lambda k, i: k[2][i]))
            for prop, cnt, get in chans:
                for i in range(cnt):
                    fc = cb.fcurves.new(f'pose.bones["{b}"].{prop}', index=i, group_name=b)
                    fc.keyframe_points.add(n)
                    co = []
                    for k in ks:
                        co += [k[0], get(k, i)]
                    fc.keyframe_points.foreach_set("co", co)
                    fc.keyframe_points.foreach_set("interpolation", [lin] * n)
                    fc.update()
        ad = arm.animation_data or arm.animation_data_create()
        track = ad.nla_tracks.new()
        track.name = self.name
        start = int(self.keys[self.rig.order[0]][0][0])
        strip = track.strips.new(self.name, start, act)
        strip.name = self.name
        try:
            strip.action_slot = slot
        except Exception:
            pass
        track.mute = True
        self.action, self.slot = act, slot
        return act


def play(rig, act_name, frame_no):
    """Show a clip's pose (for previews)."""
    arm = rig.obj
    ad = arm.animation_data or arm.animation_data_create()
    act = bpy.data.actions[act_name]
    ad.action = act
    try:
        ad.action_slot = act.slots[0]
    except Exception:
        pass
    bpy.context.scene.frame_set(int(frame_no))
    bpy.context.view_layer.update()


def rest_pose(rig):
    arm = rig.obj
    if arm.animation_data:
        arm.animation_data.action = None
    for pb in arm.pose.bones:
        pb.location = (0, 0, 0)
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.scale = (1, 1, 1)
    bpy.context.view_layer.update()


def skin(obj, rig):
    obj.parent = rig.obj
    m = obj.modifiers.new("Armature", "ARMATURE")
    m.object = rig.obj
    return obj


def parent_to_bone(obj, rig, bone):
    """Bone-parent obj keeping its current (rest-pose) world transform."""
    rest_pose(rig)
    Mw = obj.matrix_world.copy()
    obj.parent = rig.obj
    obj.parent_type = "BONE"
    obj.parent_bone = bone
    bpy.context.view_layer.update()
    obj.matrix_world = Mw
    bpy.context.view_layer.update()


# ====================================================================== export + preview

def export_glb(path, objs, sampled=False):
    path = bk._abs(path)
    for o in objs:
        if o.type == "MESH":
            o.data.validate(clean_customdata=False)
    bk.select(objs)
    bpy.ops.export_scene.gltf(
        filepath=path, export_format="GLB", use_selection=True, export_apply=True, export_yup=True,
        export_animations=True, export_animation_mode="NLA_TRACKS", export_force_sampling=sampled,
        export_vertex_color="MATERIAL", export_all_vertex_colors=False,
        export_meshopt_compression_enable=True, export_skins=True, export_influence_nb=4,
        export_def_bones=False, export_leaf_bone=False, export_optimize_animation_size=True,
        export_reset_pose_bones=True, export_rest_position_armature=True, export_texcoords=True,
        export_normals=True, export_tangents=False, export_extras=False, export_lights=False,
        export_cameras=False, export_materials="EXPORT")
    import os
    print(f"[ck] exported {path} ({os.path.getsize(path) / 1024:.1f} KB)")
    return path


def eevee(res=(1600, 900), samples=48, transparent=False):
    s = bpy.context.scene
    s.render.engine = "BLENDER_EEVEE"
    s.eevee.taa_render_samples = samples
    s.render.resolution_x, s.render.resolution_y = res
    s.render.resolution_percentage = 100
    s.render.film_transparent = transparent
    s.view_settings.view_transform = "AgX"
    s.view_settings.look = "AgX - Medium High Contrast"
    try:
        s.eevee.use_shadows = True
        s.eevee.use_raytracing = True
    except Exception:
        pass


def world(color="#0b0c0e", strength=1.0):
    s = bpy.context.scene
    w = s.world or bpy.data.worlds.new("World")
    s.world = w
    bg = w.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = bk.hex_lin(color)
    bg.inputs["Strength"].default_value = strength


def light(name, kind, energy, loc, target=None, size=None, color="#ffffff", spot=None, blend=0.3, rot=None):
    ld = bpy.data.lights.get(name) or bpy.data.lights.new(name, kind)
    ld.energy = energy
    ld.color = bk.hex_lin(color)[:3]
    if size is not None:
        if kind == "AREA":
            ld.size = size
        else:
            ld.shadow_soft_size = size
    if kind == "SPOT" and spot:
        ld.spot_size = math.radians(spot)
        ld.spot_blend = blend
    o = bpy.data.objects.get(name) or bpy.data.objects.new(name, ld)
    if o.name not in bpy.context.scene.collection.objects:
        bpy.context.scene.collection.objects.link(o)
    o.location = loc
    if target is not None:
        d = V(target) - V(loc)
        o.rotation_mode = "QUATERNION"
        o.rotation_quaternion = d.to_track_quat("-Z", "Y")
    elif rot is not None:
        o.rotation_euler = [math.radians(a) for a in rot]
    return o


def camera(name, loc, target=None, fov_v=None, lens=None, ortho=None, rot=None, clip=(0.01, 100)):
    cd = bpy.data.cameras.get(name) or bpy.data.cameras.new(name)
    if fov_v is not None:
        cd.sensor_fit = "VERTICAL"
        cd.lens_unit = "FOV"
        cd.angle_y = math.radians(fov_v)
    if lens is not None:
        cd.sensor_fit = "AUTO"
        cd.lens = lens
    if ortho is not None:
        cd.type = "ORTHO"
        cd.ortho_scale = ortho
    cd.clip_start, cd.clip_end = clip
    o = bpy.data.objects.get(name) or bpy.data.objects.new(name, cd)
    if o.name not in bpy.context.scene.collection.objects:
        bpy.context.scene.collection.objects.link(o)
    o.location = loc
    if target is not None:
        o.rotation_mode = "QUATERNION"
        o.rotation_quaternion = (V(target) - V(loc)).to_track_quat("-Z", "Y")
    elif rot is not None:
        o.rotation_mode = "XYZ"
        o.rotation_euler = [math.radians(a) for a in rot]
    bpy.context.scene.camera = o
    return o


def render(path):
    s = bpy.context.scene
    s.render.image_settings.file_format = "PNG"
    s.render.filepath = bk._abs(path)
    bpy.ops.render.render(write_still=True)
    print(f"[ck] render {s.render.filepath}")
    return s.render.filepath


def tris(objs):
    return bk.tris(objs)
