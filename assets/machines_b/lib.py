"""MOTHERLODE machines-B toolkit (Blender 5.2, run through `bl`).

One `Part` = one mesh object (a rigid piece that moves as a unit). Primitives are appended straight
into the part's bmesh (fast: no bpy.ops per primitive), each with its own small bevel, material slot
and metre-scale UVs. A transform stack (`with p.at(loc, rot):`) lets sub-assemblies (a light, a
motor, a valve bank) be modelled once in local space and placed anywhere.

    p = Part("frame")                      # static part, pivot at origin
    p.box((0, 0, 1), (2, .3, .3), "paint_yellow", bevel=.012)
    p.cyl((0, 0, 0), (0, 0, 2), .1, "chrome", sides=20)
    frame = p.finish(parent=root)

    drum = Part("drum", pivot=(1, 0, 1), axis=(0, 1, 0))   # spins about world +Y
    ...
    d = drum.finish(parent=frame)
    spin(d, "Work", FRAMES, turns=2)        # rotation about the part's axis
    bake_clips(); bake_grime(...); export(root, out)

Conventions (CONTRACTS.md): metres, Blender Z-up, machine front (working end) = -Y (= +Z in three.js),
origin at floor centre. Library material names exactly; `label_*` / `custom_*` keep their embedded images.
Game spotlights shine along the light empty's three.js -Z, which is Blender local +Y: `empty(..., aim=dir)`
points +Y along `dir`.
"""
import json
import math
import os
import random
import struct

import bmesh
import bpy
from mathutils import Euler, Matrix, Quaternion, Vector

import bk

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.abspath(os.path.join(HERE, "..", ".."))
DECALS = os.path.join(HERE, "decals")
PREVIEWS = os.path.join(HERE, "previews")
FPS = 30
TAU = math.tau


def V(*a):
    if len(a) == 1:
        return Vector(a[0])
    return Vector(a)


# ------------------------------------------------------------------------------------------ materials
# Preview look only: the game swaps every library material for its photoscanned PBR set by name.
LIB = {
    "paint_yellow": ("#E8B400", 0.5, 0.0), "paint_orange": ("#E2661A", 0.5, 0.0),
    "paint_red": ("#B0221B", 0.5, 0.0), "paint_white": ("#E6E4DD", 0.5, 0.0),
    "paint_black": ("#1D1E20", 0.55, 0.0), "paint_green": ("#2E6A3A", 0.5, 0.0),
    "paint_blue": ("#1E4C8A", 0.5, 0.0), "paint_grey": ("#6B7074", 0.55, 0.0),
    "steel": ("#8E9296", 0.38, 1.0), "steel_dark": ("#3E4043", 0.5, 0.85),
    "galvanized": ("#A8ADB1", 0.48, 0.9), "chrome": ("#E0E3E6", 0.06, 1.0),
    "rust": ("#7B4024", 0.85, 0.15), "cast_iron": ("#47494B", 0.7, 0.75),
    "copper": ("#C46F42", 0.3, 1.0), "brass": ("#C9A646", 0.3, 1.0),
    "gold": ("#FFC743", 0.16, 1.0), "aluminium": ("#C3C7CB", 0.32, 1.0),
    "rubber": ("#161616", 0.82, 0.0), "hose_red": ("#9C1C15", 0.55, 0.0),
    "hose_yellow": ("#D6A200", 0.55, 0.0), "cable": ("#1D1D1E", 0.55, 0.0),
    "plastic_black": ("#19191B", 0.45, 0.0), "plastic_yellow": ("#E2AF00", 0.42, 0.0),
    "wood_timber": ("#8A6A45", 0.85, 0.0), "wood_planks": ("#8C7A60", 0.85, 0.0),
    "wood_dark": ("#4E3826", 0.8, 0.0),
    "concrete": ("#8B8984", 0.92, 0.0), "corrugated": ("#9AA0A4", 0.5, 0.8),
    "brick": ("#8A4A34", 0.88, 0.0), "roof_shingle": ("#4A4440", 0.9, 0.0),
    "wood_painted_white": ("#D9D4C8", 0.7, 0.0), "wood_painted_red": ("#8E2E22", 0.7, 0.0),
    "wood_painted_green": ("#3D5E3A", 0.7, 0.0),
    "canvas": ("#9C9278", 0.9, 0.0),
    "glass": ("#C8DCE4", 0.04, 0.0), "glass_dark": ("#1E2428", 0.06, 0.0),
    "rock": ("#6E6A64", 0.9, 0.0), "rock_dark": ("#3E3C3A", 0.9, 0.0), "rock_pale": ("#A9A59D", 0.85, 0.0),
    "gravel": ("#6A665F", 0.95, 0.0), "dirt": ("#5A4A3A", 0.95, 0.0),
    "coal_ore": ("#1B1C1E", 0.45, 0.0), "iron_ore": ("#7A3A28", 0.8, 0.1),
    "silver_ore": ("#9AA3AA", 0.5, 0.35), "gold_ore": ("#8C7B4E", 0.6, 0.35),
}
EMIT = {
    "emit_warm": ("#FFB766", 6.0), "emit_white": ("#F4F8FF", 9.0), "emit_red": ("#FF2A1A", 5.0),
    "emit_green": ("#3BFF5A", 4.0), "emit_amber": ("#FF9A1A", 6.0), "emit_screen": ("#7FB8FF", 2.0),
}


def mat(name):
    """Library material (exact name) with a preview-only base look."""
    m = bpy.data.materials.get(name)
    if m is not None:
        return m
    if name in EMIT:
        col, s = EMIT[name]
        m = bk.mat(name, "#202020", rough=0.3, emit=col, emit_strength=s)
    elif name == "glass":
        m = bk.mat(name, LIB[name][0], rough=0.04, alpha=0.28)
    elif name in LIB:
        c, r, me = LIB[name]
        m = bk.mat(name, c, rough=r, metal=me)
    else:
        raise KeyError(f"unknown material {name}: create label_/custom_ materials with label()/custom()")
    m["lib"] = True
    return m


def _img(path, colorspace="sRGB"):
    img = bpy.data.images.load(path, check_existing=True)
    img.colorspace_settings.name = colorspace
    return img


def label(name, png, mode="BLEND", rough=0.55, metal=0.0, emit=0.0, repeat=False):
    """`label_*` / `custom_*` material with an embedded image (kept as-is by the game).
    mode BLEND | CLIP (alpha mask 0.5) | OPAQUE. emit>0 also drives emission from the image."""
    assert name.startswith(("label_", "custom_")), name
    m = bpy.data.materials.get(name)
    if m is not None:
        return m
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    p = nt.nodes.get("Principled BSDF")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = _img(png)
    tex.extension = "REPEAT" if repeat else "EXTEND"
    nt.links.new(tex.outputs["Color"], p.inputs["Base Color"])
    if mode == "BLEND":
        nt.links.new(tex.outputs["Alpha"], p.inputs["Alpha"])
        m.surface_render_method = "BLENDED"
    elif mode == "CLIP":
        rnd = nt.nodes.new("ShaderNodeMath")
        rnd.operation = "ROUND"
        nt.links.new(tex.outputs["Alpha"], rnd.inputs[0])
        nt.links.new(rnd.outputs[0], p.inputs["Alpha"])
        m.surface_render_method = "DITHERED"
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    if emit:
        nt.links.new(tex.outputs["Color"], p.inputs["Emission Color"])
        p.inputs["Emission Strength"].default_value = emit
    m.use_backface_culling = mode != "BLEND"
    m["custom"] = True
    return m


def custom(name, color="#808080", rough=0.5, metal=0.0, alpha=1.0, base=None, normal=None, emis=None,
           emit_color=None, emit=0.0, clip=False, normal_strength=1.0, double=False, alpha_tex=False):
    """`custom_*` PBR material: optional base (sRGB, alpha in A), normal map, emissive map."""
    assert name.startswith("custom_"), name
    m = bpy.data.materials.get(name)
    if m is not None:
        return m
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    p = nt.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value = bk.hex_lin(color)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    if base:
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = _img(base)
        nt.links.new(t.outputs["Color"], p.inputs["Base Color"])
        if alpha_tex:
            nt.links.new(t.outputs["Alpha"], p.inputs["Alpha"])
            m.surface_render_method = "BLENDED"
        if clip:
            rnd = nt.nodes.new("ShaderNodeMath")
            rnd.operation = "ROUND"
            nt.links.new(t.outputs["Alpha"], rnd.inputs[0])
            nt.links.new(rnd.outputs[0], p.inputs["Alpha"])
            m.surface_render_method = "DITHERED"
    if normal:
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = _img(normal, "Non-Color")
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nm.inputs["Strength"].default_value = normal_strength
        nt.links.new(t.outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], p.inputs["Normal"])
    if emis:
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = _img(emis)
        nt.links.new(t.outputs["Color"], p.inputs["Emission Color"])
        p.inputs["Emission Strength"].default_value = emit or 1.0
    elif emit_color:
        p.inputs["Emission Color"].default_value = bk.hex_lin(emit_color)
        p.inputs["Emission Strength"].default_value = emit or 1.0
    if alpha < 1.0:
        p.inputs["Alpha"].default_value = alpha
        m.surface_render_method = "BLENDED"
    m.use_backface_culling = not double
    m["custom"] = True
    return m


def get_mat(name):
    m = bpy.data.materials.get(name)
    return m if m is not None else mat(name)


# ------------------------------------------------------------------------------------------ math utils
def rotm(rot):
    """None | (deg x, y, z) XYZ euler | Matrix3/4 | Quaternion -> 4x4 rotation."""
    if rot is None:
        return Matrix.Identity(4)
    if isinstance(rot, Matrix):
        return rot.to_4x4() if len(rot) == 3 else rot.copy()
    if isinstance(rot, Quaternion):
        return rot.to_matrix().to_4x4()
    return Euler([math.radians(a) for a in rot], "XYZ").to_matrix().to_4x4()


def perp(w):
    """Two unit vectors a, b with a x b = w (right-handed frame a, b, w)."""
    w = Vector(w).normalized()
    ref = Vector((0, 0, 1)) if abs(w.z) < 0.92 else Vector((1, 0, 0))
    a = ref.cross(w).normalized()
    b = w.cross(a).normalized()
    return a, b


def frame(fwd, up=(0, 0, 1)):
    """3x3 rotation whose local +Y = fwd and local +Z ~ up (columns: right, fwd, up)."""
    f = Vector(fwd).normalized()
    u = Vector(up)
    if abs(f.dot(u.normalized())) > 0.98:
        u = Vector((0, 1, 0)) if abs(f.y) < 0.9 else Vector((1, 0, 0))
    r = f.cross(u).normalized()
    u = r.cross(f).normalized()
    return Matrix((r, f, u)).transposed()


def zframe(axis, up=(0, 0, 1)):
    """3x3 rotation whose local +Z = axis."""
    z = Vector(axis).normalized()
    u = Vector(up)
    if abs(z.dot(u.normalized())) > 0.98:
        u = Vector((0, 1, 0)) if abs(z.y) < 0.9 else Vector((1, 0, 0))
    x = u.cross(z).normalized()
    y = z.cross(x).normalized()
    return Matrix((x, y, z)).transposed()


def lerp(a, b, t):
    return a + (b - a) * t


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def bezier(p0, c0, c1, p1, n=24):
    p0, c0, c1, p1 = map(Vector, (p0, c0, c1, p1))
    pts = []
    for i in range(n + 1):
        t = i / n
        u = 1 - t
        pts.append(p0 * u ** 3 + c0 * 3 * u * u * t + c1 * 3 * u * t * t + p1 * t ** 3)
    return pts


def resample(pts, n):
    """Points evenly spaced by arc length along a polyline."""
    pts = [Vector(p) for p in pts]
    L = [0.0]
    for i in range(1, len(pts)):
        L.append(L[-1] + (pts[i] - pts[i - 1]).length)
    tot = L[-1]
    out, j = [], 0
    for k in range(n + 1):
        s = tot * k / n
        while j < len(L) - 2 and L[j + 1] < s:
            j += 1
        seg = L[j + 1] - L[j]
        t = 0 if seg < 1e-9 else (s - L[j]) / seg
        out.append(pts[j].lerp(pts[j + 1], t))
    return out


def catmull(ctrl, res=8):
    """Smooth curve through control points (Catmull-Rom, end tangents mirrored)."""
    P = [Vector(p) for p in ctrl]
    if len(P) < 3:
        return resample(P, res)
    P = [P[0] * 2 - P[1]] + P + [P[-1] * 2 - P[-2]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(res):
            t = k / res
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(P[-2])
    return out


def length(pts):
    return sum((Vector(pts[i]) - Vector(pts[i - 1])).length for i in range(1, len(pts)))


# ------------------------------------------------------------------------------------------ Part
class Part:
    def __init__(self, name, pivot=(0, 0, 0), axis=None, grime=True, smooth=True, angle=38.0, wn=True):
        self.name = name
        self.pivot = Vector(pivot)
        self.axis = Vector(axis).normalized() if axis is not None else None
        self.bm = bmesh.new()
        self.uv = self.bm.loops.layers.uv.new("UVMap")
        self.lock = self.bm.faces.layers.int.new("uvlock")
        self.mats = []
        self.grime = grime
        self.smooth = smooth
        self.angle = angle
        self.wn = wn
        self.T = [Matrix.Identity(4)]

    # -------------------------------------------------------------- transform stack
    def push(self, M):
        self.T.append(self.T[-1] @ M)

    def pop(self):
        self.T.pop()

    class _Ctx:
        def __init__(self, part, M):
            self.part, self.M = part, M

        def __enter__(self):
            self.part.push(self.M)
            return self.part

        def __exit__(self, *a):
            self.part.pop()

    def at(self, loc=(0, 0, 0), rot=None, scale=1.0):
        return Part._Ctx(self, Matrix.Translation(Vector(loc)) @ rotm(rot) @ Matrix.Scale(scale, 4))

    def P(self, p):
        """local point -> world (current transform)."""
        return self.T[-1] @ Vector(p)

    def D(self, d):
        return (self.T[-1].to_3x3() @ Vector(d)).normalized()

    # -------------------------------------------------------------- core
    def _mi(self, m):
        n = m if isinstance(m, str) else m.name
        if n not in self.mats:
            self.mats.append(n)
        return self.mats.index(n)

    def faces(self, co, F, m, uvs=None):
        """Raw faces: co = local points, F = index tuples, uvs = per-face list of uv tuples (locks them)."""
        M = self.T[-1]
        bm = self.bm
        vs = [bm.verts.new(M @ Vector(c)) for c in co]
        mi = self._mi(m)
        out = []
        for k, idx in enumerate(F):
            try:
                f = bm.faces.new([vs[i] for i in idx])
            except ValueError:
                continue
            f.material_index = mi
            if uvs is not None and uvs[k] is not None:
                for lp, uv in zip(f.loops, uvs[k]):
                    lp[self.uv].uv = uv
                f[self.lock] = 1
            out.append(f)
        return out

    def _post(self, fs, bevel=0.0, seg=2, recalc=True, angle=30.0):
        for f in fs:
            f.normal_update()
        if recalc and fs:
            bmesh.ops.recalc_face_normals(self.bm, faces=fs)
        if bevel > 0 and fs:
            lim = math.radians(angle)
            edges = set()
            for f in fs:
                for e in f.edges:
                    if len(e.link_faces) == 2:
                        try:
                            if e.calc_face_angle() > lim:
                                edges.add(e)
                        except ValueError:
                            pass
            if edges:
                bmesh.ops.bevel(self.bm, geom=list(edges), offset=bevel, offset_type="OFFSET", segments=seg,
                                profile=0.5, affect="EDGES", clamp_overlap=True)
        return fs

    def tris(self):
        return sum(len(f.verts) - 2 for f in self.bm.faces)

    # -------------------------------------------------------------- primitives
    def box(self, c, size, m, rot=None, bevel=0.0, seg=2):
        """Box centred on c (local), size (x, y, z), rot = euler degrees / Matrix about the centre."""
        M = Matrix.Translation(Vector(c)) @ rotm(rot) @ Matrix.Diagonal((*size, 1))
        hx = [(-.5, -.5, -.5), (.5, -.5, -.5), (.5, .5, -.5), (-.5, .5, -.5),
              (-.5, -.5, .5), (.5, -.5, .5), (.5, .5, .5), (-.5, .5, .5)]
        co = [M @ Vector(p) for p in hx]
        F = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        return self._post(self.faces(co, F, m), bevel, seg)

    def box2(self, lo, hi, m, bevel=0.0, seg=2):
        lo, hi = Vector(lo), Vector(hi)
        return self.box((lo + hi) / 2, tuple(hi - lo), m, bevel=bevel, seg=seg)

    def cyl(self, p0, p1, r, m, sides=16, r1=None, caps=(True, True), bevel=0.0, seg=2, phase=0.0, uv=True):
        """Cylinder / frustum / cone from p0 to p1 (local points)."""
        p0, p1 = Vector(p0), Vector(p1)
        d = p1 - p0
        Lh = d.length
        if Lh < 1e-7:
            return []
        w = d / Lh
        a, b = perp(w)
        r1 = r if r1 is None else r1
        ang = [phase + TAU * i / sides for i in range(sides)]
        co = [p0 + (a * math.cos(t) + b * math.sin(t)) * r for t in ang]
        apex = r1 < 1e-6
        if apex:
            co.append(p1)
        else:
            co += [p1 + (a * math.cos(t) + b * math.sin(t)) * r1 for t in ang]
        F, U = [], []
        rm = (r + r1) / 2
        slant = math.hypot(Lh, r - r1)
        for i in range(sides):
            j = (i + 1) % sides
            u0, u1 = rm * TAU * i / sides, rm * TAU * (i + 1) / sides
            if apex:
                F.append((i, j, sides))
                U.append([(u0, 0), (u1, 0), ((u0 + u1) / 2, slant)])
            else:
                F.append((i, j, sides + j, sides + i))
                U.append([(u0, 0), (u1, 0), (u1, slant), (u0, slant)])
        if caps[0] and r > 1e-6:
            F.append(tuple(reversed(range(sides))))
            U.append([(math.cos(ang[i]) * r, math.sin(ang[i]) * r) for i in reversed(range(sides))])
        if caps[1] and not apex:
            F.append(tuple(range(sides, 2 * sides)))
            U.append([(math.cos(ang[i]) * r1, math.sin(ang[i]) * r1) for i in range(sides)])
        return self._post(self.faces(co, F, m, U if uv else None), bevel, seg, recalc=all(caps) or apex)

    def lathe(self, c, axis, prof, m, sides=24, caps=True, bevel=0.0, seg=2, phase=0.0):
        """Surface of revolution: prof = [(radius, height), ...] along axis from c."""
        c = Vector(c)
        w = Vector(axis).normalized()
        a, b = perp(w)
        ang = [phase + TAU * i / sides for i in range(sides)]
        co, rings = [], []
        for r, h in prof:
            base = c + w * h
            if r < 1e-6:
                rings.append([len(co)])
                co.append(base)
            else:
                rings.append(list(range(len(co), len(co) + sides)))
                co += [base + (a * math.cos(t) + b * math.sin(t)) * r for t in ang]
        F, U = [], []
        vacc = 0.0
        for k in range(len(rings) - 1):
            A, B = rings[k], rings[k + 1]
            (ra, ha), (rb, hb) = prof[k], prof[k + 1]
            dv = math.hypot(rb - ra, hb - ha)
            rm = max((ra + rb) / 2, 1e-3)
            for i in range(sides):
                j = (i + 1) % sides
                u0, u1 = rm * TAU * i / sides, rm * TAU * (i + 1) / sides
                if len(A) == 1 and len(B) == 1:
                    continue
                if len(A) == 1:
                    F.append((A[0], B[j], B[i]))
                    U.append([((u0 + u1) / 2, vacc), (u1, vacc + dv), (u0, vacc + dv)])
                elif len(B) == 1:
                    F.append((A[i], A[j], B[0]))
                    U.append([(u0, vacc), (u1, vacc), ((u0 + u1) / 2, vacc + dv)])
                else:
                    F.append((A[i], A[j], B[j], B[i]))
                    U.append([(u0, vacc), (u1, vacc), (u1, vacc + dv), (u0, vacc + dv)])
            vacc += dv
        closed = True
        if caps and len(rings[0]) > 1:
            F.append(tuple(reversed(rings[0])))
            r0 = prof[0][0]
            U.append([(math.cos(ang[i]) * r0, math.sin(ang[i]) * r0) for i in reversed(range(sides))])
        elif len(rings[0]) > 1:
            closed = False
        if caps and len(rings[-1]) > 1:
            F.append(tuple(rings[-1]))
            r1 = prof[-1][0]
            U.append([(math.cos(ang[i]) * r1, math.sin(ang[i]) * r1) for i in range(sides)])
        elif len(rings[-1]) > 1:
            closed = False
        fs = self.faces(co, F, m, U)
        return self._post(fs, bevel, seg, recalc=closed)

    def torus(self, c, axis, R, r, m, seg=24, rseg=8, arc=360.0, phase=0.0):
        c = Vector(c)
        w = Vector(axis).normalized()
        a, b = perp(w)
        full = abs(arc - 360.0) < 1e-6
        n = seg if full else seg + 1
        co = []
        for i in range(n):
            t = math.radians(phase) + math.radians(arc) * i / seg
            radial = a * math.cos(t) + b * math.sin(t)
            for k in range(rseg):
                s = TAU * k / rseg
                co.append(c + radial * (R + r * math.cos(s)) + w * r * math.sin(s))
        F, U = [], []
        for i in range(seg):
            i2 = (i + 1) % n if full else i + 1
            for k in range(rseg):
                k2 = (k + 1) % rseg
                F.append((i * rseg + k, i2 * rseg + k, i2 * rseg + k2, i * rseg + k2))
                U.append([(i * 0.05, k * 0.03), ((i + 1) * 0.05, k * 0.03), ((i + 1) * 0.05, (k + 1) * 0.03), (i * 0.05, (k + 1) * 0.03)])
        fs = self.faces(co, F, m, U)
        return self._post(fs, 0, recalc=full)

    def prism(self, p0, p1, prof, m, up=(0, 0, 1), bevel=0.0, seg=2, caps=True):
        """Extrude 2D polygon prof [(x, y)...] from p0 to p1; profile y follows `up`."""
        p0, p1 = Vector(p0), Vector(p1)
        w = (p1 - p0).normalized()
        vax = Vector(up) - w * Vector(up).dot(w)
        if vax.length < 1e-6:
            vax = perp(w)[1]
        vax.normalize()
        uax = vax.cross(w)
        n = len(prof)
        co = [p0 + uax * x + vax * y for x, y in prof] + [p1 + uax * x + vax * y for x, y in prof]
        F = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
        if caps:
            F += [tuple(reversed(range(n))), tuple(range(n, 2 * n))]
        return self._post(self.faces(co, F, m), bevel, seg, recalc=caps)

    def slab(self, pts, thick, m, bevel=0.0, seg=2, normal=None):
        """Planar polygon (local points) thickened along its normal (centred)."""
        P = [Vector(p) for p in pts]
        if normal is None:
            nrm = Vector((0, 0, 0))
            for i in range(len(P)):
                nrm += P[i].cross(P[(i + 1) % len(P)])
            nrm.normalize()
        else:
            nrm = Vector(normal).normalized()
        h = nrm * thick / 2
        n = len(P)
        co = [p - h for p in P] + [p + h for p in P]
        F = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
        F += [tuple(reversed(range(n))), tuple(range(n, 2 * n))]
        return self._post(self.faces(co, F, m), bevel, seg)

    def tube(self, pts, r, m, sides=8, caps=False, r_end=None):
        """Swept circular tube through local points (parallel-transport frames, metre UVs)."""
        P = [Vector(p) for p in pts]
        if len(P) < 2:
            return []
        T = []
        for i in range(len(P)):
            d = P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]
            T.append(d.normalized() if d.length > 1e-9 else Vector((0, 0, 1)))
        Nv, _ = perp(T[0])
        frames = []
        for i, t in enumerate(T):
            if i > 0:
                ax = T[i - 1].cross(t)
                if ax.length > 1e-9:
                    Nv = Matrix.Rotation(T[i - 1].angle(t), 3, ax.normalized()) @ Nv
            Nv = (Nv - t * Nv.dot(t)).normalized()
            frames.append((Nv, t.cross(Nv)))
        co, F, U = [], [], []
        vacc = [0.0]
        for i in range(1, len(P)):
            vacc.append(vacc[-1] + (P[i] - P[i - 1]).length)
        for i, p in enumerate(P):
            rr = r if r_end is None else lerp(r, r_end, i / (len(P) - 1))
            Nn, Bn = frames[i]
            for k in range(sides):
                s = TAU * k / sides
                co.append(p + (Nn * math.cos(s) + Bn * math.sin(s)) * rr)
        C = TAU * r
        for i in range(len(P) - 1):
            for k in range(sides):
                k2 = (k + 1) % sides
                F.append((i * sides + k, i * sides + k2, (i + 1) * sides + k2, (i + 1) * sides + k))
                U.append([(C * k / sides, vacc[i]), (C * (k + 1) / sides, vacc[i]),
                          (C * (k + 1) / sides, vacc[i + 1]), (C * k / sides, vacc[i + 1])])
        if caps:
            F.append(tuple(reversed(range(sides))))
            U.append(None)
            last = (len(P) - 1) * sides
            F.append(tuple(range(last, last + sides)))
            U.append(None)
        fs = self.faces(co, F, m, U)
        for f in fs:
            f.normal_update()
        # orient outward: compare first side face normal with its radial direction
        if fs:
            f0 = fs[0]
            cen = f0.calc_center_median()
            if f0.normal.dot(cen - self.T[-1] @ P[0]) < 0:
                bmesh.ops.reverse_faces(self.bm, faces=fs)
        return fs

    def hose(self, p0, d0, p1, d1, r, m, sides=7, reach=None, sag=0.0, fit="steel", fit_len=0.07, n=18):
        """Hydraulic hose with natural bend radius: leaves p0 along d0, enters p1 coming along -d1
        (d1 = direction pointing out of the p1 fitting). Crimped ferrules + hex nuts at both ends."""
        p0, p1 = Vector(p0), Vector(p1)
        d0, d1 = Vector(d0).normalized(), Vector(d1).normalized()
        dist = (p1 - p0).length
        L = reach if reach is not None else max(0.38 * dist, 7 * r)
        a0 = p0 + d0 * fit_len
        a1 = p1 + d1 * fit_len
        c0 = a0 + d0 * L + Vector((0, 0, -sag))
        c1 = a1 + d1 * L + Vector((0, 0, -sag))
        pts = resample(bezier(a0, c0, c1, a1, 48), n)
        out = self.tube(pts, r, m, sides=sides)
        if fit:
            for p, d in ((p0, d0), (p1, d1)):
                self.cyl(p + d * 0.012, p + d * (fit_len + 0.004), r * 1.32, fit, sides=sides)
                self.cyl(p - d * 0.004, p + d * 0.018, r * 1.62, fit, sides=6)
        return out

    def cable(self, ctrl, r, m="cable", sides=6, res=5):
        return self.tube(catmull(ctrl, res), r, m, sides=sides)

    def loft(self, rings, m, closed=True, caps=True, bevel=0.0, seg=1):
        """Skin successive rings of local points (same count). closed = rings wrap around; caps close the ends."""
        n = len(rings[0])
        co = [Vector(p) for ring in rings for p in ring]
        F = []
        for i in range(len(rings) - 1):
            for k in range(n if closed else n - 1):
                k2 = (k + 1) % n
                F.append((i * n + k, i * n + k2, (i + 1) * n + k2, (i + 1) * n + k))
        if caps and closed:
            F.append(tuple(reversed(range(n))))
            last = (len(rings) - 1) * n
            F.append(tuple(range(last, last + n)))
        return self._post(self.faces(co, F, m), bevel, seg, recalc=caps and closed)

    def sphere(self, c, r, m, seg=16, rings=8, scale=(1, 1, 1)):
        c = Vector(c)
        prof = []
        for i in range(rings + 1):
            t = math.pi * i / rings
            prof.append((math.sin(t) * r, -math.cos(t) * r))
        if scale != (1, 1, 1):
            with self.at(c, scale=1.0):
                self.push(Matrix.Diagonal((*scale, 1)))
                fs = self.lathe((0, 0, 0), (0, 0, 1), prof, m, sides=seg)
                self.pop()
            return fs
        return self.lathe(c, (0, 0, 1), prof, m, sides=seg)

    def ico(self, c, r, m, detail=1, scale=(1, 1, 1), rot=None, deform=None, seed=0, uvbox=True):
        """Icosphere (rocks, lumps). deform(v_local, rng) -> v_local."""
        rng = random.Random(seed)
        tmp = bmesh.new()
        bmesh.ops.create_icosphere(tmp, subdivisions=detail, radius=r)
        M = self.T[-1] @ Matrix.Translation(Vector(c)) @ rotm(rot) @ Matrix.Diagonal((*scale, 1))
        vmap = {}
        for v in tmp.verts:
            co = v.co.copy()
            if deform:
                co = deform(co, rng)
            vmap[v.index] = self.bm.verts.new(M @ co)
        mi = self._mi(m)
        out = []
        tmp.verts.index_update()
        for f in tmp.faces:
            nf = self.bm.faces.new([vmap[v.index] for v in f.verts])
            nf.material_index = mi
            out.append(nf)
        tmp.free()
        return self._post(out, 0)

    # -------------------------------------------------------------- compound helpers
    def bolt(self, p, n, r=0.011, m="steel_dark", washer=False, h=None):
        """Hex bolt head sitting on a surface at p with outward normal n (local)."""
        p, n = Vector(p), Vector(n).normalized()
        h = h or r * 0.75
        base = p
        if washer:
            self.cyl(p - n * 0.001, p + n * r * 0.18, r * 1.55, m, sides=10, caps=(False, True))
            base = p + n * r * 0.18
        self.cyl(base, base + n * h, r, m, sides=6, caps=(False, True), phase=0.3)

    def bolts(self, p0, p1, count, n, r=0.011, m="steel_dark", washer=False):
        p0, p1 = Vector(p0), Vector(p1)
        for i in range(count):
            t = 0.5 if count == 1 else i / (count - 1)
            self.bolt(p0.lerp(p1, t), n, r, m, washer)

    def bolt_ring(self, c, axis, R, count, r=0.011, m="steel_dark", phase=0.0, washer=False):
        c, w = Vector(c), Vector(axis).normalized()
        a, b = perp(w)
        for i in range(count):
            t = phase + TAU * i / count
            self.bolt(c + (a * math.cos(t) + b * math.sin(t)) * R, w, r, m, washer)

    def ibeam(self, p0, p1, h, wdt, m, tw=None, tf=None, up=(0, 0, 1), bevel=0.0):
        tw = tw or wdt * 0.09
        tf = tf or h * 0.09
        a, b = wdt / 2, h / 2
        prof = [(-a, -b), (a, -b), (a, -b + tf), (tw / 2, -b + tf), (tw / 2, b - tf), (a, b - tf), (a, b), (-a, b),
                (-a, b - tf), (-tw / 2, b - tf), (-tw / 2, -b + tf), (-a, -b + tf)]
        return self.prism(p0, p1, prof, m, up=up, bevel=bevel, seg=1)

    def channel(self, p0, p1, h, wdt, m, t=None, up=(0, 0, 1), bevel=0.0):
        """C channel opening toward +profile-x."""
        t = t or h * 0.08
        a, b = wdt / 2, h / 2
        prof = [(-a, -b), (a, -b), (a, -b + t), (-a + t, -b + t), (-a + t, b - t), (a, b - t), (a, b), (-a, b)]
        return self.prism(p0, p1, prof, m, up=up, bevel=bevel, seg=1)

    def angle_iron(self, p0, p1, s, m, t=None, up=(0, 0, 1)):
        t = t or s * 0.12
        prof = [(0, 0), (s, 0), (s, t), (t, t), (t, s), (0, s)]
        return self.prism(p0, p1, prof, m, up=up, seg=1)

    def hyd_cyl(self, p0, p1, rb, rr, m_barrel="paint_yellow", frac=0.55, eye=True, ports=True, m_rod="chrome"):
        """Static hydraulic cylinder p0 (barrel end) -> p1 (rod eye): painted barrel + chrome rod."""
        p0, p1 = Vector(p0), Vector(p1)
        d = p1 - p0
        L = d.length
        w = d / L
        a, b = perp(w)
        e = rb * 1.0 if eye else 0
        pb0, pb1 = p0 + w * e, p0 + w * (e + (L - 2 * e) * frac)
        self.cyl(pb0, pb1, rb, m_barrel, sides=20, bevel=rb * 0.12, seg=2)
        self.cyl(pb1 - w * 0.01, pb1 + w * rb * 0.35, rb * 1.12, m_barrel, sides=20, bevel=rb * 0.08, seg=1)
        self.cyl(pb0 - w * rb * 0.25, pb0 + w * rb * 0.3, rb * 1.12, m_barrel, sides=20, bevel=rb * 0.08, seg=1)
        self.cyl(pb1, p1 - w * e * 0.6, rr, m_rod, sides=16)
        if eye:
            for pe in (p0 + w * e * 0.55, p1 - w * e * 0.6):
                self.cyl(pe - a * rb * 0.55, pe + a * rb * 0.55, rb * 0.62, "steel_dark", sides=14, bevel=0.004, seg=1)
                self.cyl(pe - a * rb * 0.75, pe + a * rb * 0.75, rb * 0.22, "steel", sides=10)
        if ports:
            for t in (0.12, 0.9):
                pp = pb0.lerp(pb1, t) + b * rb
                self.cyl(pp - b * 0.01, pp + b * rb * 0.35, rb * 0.22, "steel", sides=8)
                self.cyl(pp + b * rb * 0.35, pp + b * rb * 0.5, rb * 0.28, "steel", sides=6)

    def handrail(self, path, h=1.05, m="paint_yellow", r=0.022, posts=1.1, toe=True, mid=True, close=False):
        """Guard rail along floor points (local). Top + knee rail, posts, toe board."""
        P = [Vector(p) for p in path]
        if close:
            P = P + [P[0]]
        up = Vector((0, 0, 1))
        for k in ([h, h * 0.52] if mid else [h]):
            self.tube([p + up * k for p in P], r, m, sides=8)
        for i in range(len(P) - 1):
            a, b = P[i], P[i + 1]
            seg = (b - a).length
            n = max(1, round(seg / posts))
            for j in range(n + (1 if i == len(P) - 2 and not close else 0)):
                q = a.lerp(b, j / n)
                self.cyl(q, q + up * (h + r * 0.5), r * 1.05, m, sides=8, caps=(False, True))
            if toe:
                d = (b - a).normalized()
                nrm = d.cross(up)
                self.box((a + b) / 2 + up * 0.05, (seg, 0.008, 0.1), m, rot=zframe_rot(d))
        return P

    def ladder(self, p0, p1, w=0.45, m="paint_yellow", r=0.019, step=0.28):
        p0, p1 = Vector(p0), Vector(p1)
        d = (p1 - p0)
        L = d.length
        a, _ = perp(d)
        if abs(a.z) > 0.5:
            a = Vector((1, 0, 0))
        side = d.normalized().cross(Vector((0, 0, 1)))
        if side.length < 0.1:
            side = Vector((1, 0, 0))
        side.normalize()
        for s in (-1, 1):
            self.cyl(p0 + side * s * w / 2, p1 + side * s * w / 2, r * 1.3, m, sides=8)
        n = int(L / step)
        for i in range(1, n + 1):
            q = p0.lerp(p1, i / (n + 1))
            self.cyl(q - side * w / 2, q + side * w / 2, r, m, sides=6)

    def grille(self, c, w, h, n, normal, m="steel_dark", depth=0.03, t=0.006, up=(0, 0, 1), slant=35):
        """Louvred grille in a plane (normal outward), slats horizontal along 'up'."""
        R = frame(normal, up)
        with self.at(c, R):
            for i in range(n):
                z = -h / 2 + h * (i + 0.5) / n
                self.box((0, 0, z), (w, depth, t), m, rot=(slant, 0, 0))
            self.box((0, -depth * 0.2, h / 2 + 0.01), (w + 0.04, depth, 0.02), m)
            self.box((0, -depth * 0.2, -h / 2 - 0.01), (w + 0.04, depth, 0.02), m)
            for s in (-1, 1):
                self.box((s * (w / 2 + 0.01), -depth * 0.2, 0), (0.02, depth, h + 0.04), m)

    def deck(self, lo, hi, top="custom_chequer", side="steel"):
        """Walkway plate: top face uses `top`, the rest `side`."""
        fs = self.box2(lo, hi, side, bevel=0.004, seg=1)
        mi = self._mi(top)
        # retag the up-facing faces created by this box
        for f in fs:
            if f.is_valid and f.normal.z > 0.99:
                f.material_index = mi
        return fs

    def led_light(self, c, aim, w=0.32, h=0.12, d=0.09, house="paint_black", lens="emit_white", bracket=True):
        """Rectangular LED work light; lens faces `aim` (local direction)."""
        R = frame(aim, (0, 0, 1) if abs(Vector(aim).normalized().z) < 0.95 else (0, 1, 0))
        with self.at(c, R):
            self.box((0, -d * 0.1, 0), (w, d, h), house, bevel=0.008, seg=2)
            self.box((0, d * 0.36, 0), (w * 0.9, 0.012, h * 0.78), lens, bevel=0.003, seg=1)
            for i in range(6):
                x = -w * 0.38 + w * 0.76 * i / 5
                self.box((x, -d * 0.62, 0), (0.008, d * 0.4, h * 0.9), house)
            if bracket:
                for s in (-1, 1):
                    self.box((s * (w / 2 + 0.012), -d * 0.1, 0), (0.01, 0.05, 0.05), "steel_dark")
                self.box((0, -d * 0.1, -h / 2 - 0.05), (w + 0.05, 0.05, 0.012), "steel_dark")

    def round_light(self, c, aim, r=0.09, house="paint_black", lens="emit_white"):
        w = Vector(aim).normalized()
        c = Vector(c)
        self.lathe(c - w * 0.09, w, [(0, 0), (r * 0.55, 0), (r * 0.75, 0.03), (r, 0.08), (r * 1.02, 0.1), (r * 0.9, 0.1)],
                   house, sides=18, caps=False)
        self.cyl(c + w * 0.0, c + w * 0.008, r * 0.9, lens, sides=18)
        for k in range(5):
            self.torus(c - w * (0.02 + k * 0.012), w, r * 0.55 + k * 0.03, 0.004, house, seg=18, rseg=4)

    def gauge_body(self, c, n, r=0.06, m="chrome", up=(0, 0, 1)):
        """Bezel + case for a dial gauge facing n (face decal + needle are separate)."""
        n = Vector(n).normalized()
        c = Vector(c)
        self.lathe(c - n * 0.045, n, [(0, 0), (r * 0.92, 0), (r * 0.95, 0.04), (r * 1.08, 0.042), (r * 1.1, 0.05),
                                      (r * 1.0, 0.056), (r * 0.94, 0.05)], m, sides=20, caps=False)
        self.cyl(c - n * 0.05, c - n * 0.07, r * 0.25, "brass", sides=8)


def zframe_rot(d):
    """Rotation matrix mapping local X -> d (horizontal-ish), Z -> up."""
    d = Vector(d).normalized()
    up = Vector((0, 0, 1))
    if abs(d.dot(up)) > 0.98:
        up = Vector((0, 1, 0))
    y = up.cross(d).normalized()
    z = d.cross(y).normalized()
    return Matrix((d, y, z)).transposed()


# ------------------------------------------------------------------------------------------ finishing
_ALL = []


def finish(part, parent=None, name=None):
    """bmesh -> mesh object: metre box-UVs on unlocked faces, local space about the pivot/axis,
    sharp-by-angle + weighted normals, materials by name."""
    bm = part.bm
    bm.normal_update()
    uvl, lock = part.uv, part.lock
    for f in bm.faces:
        if f[lock]:
            continue
        n = f.normal
        ax = (abs(n.x), abs(n.y), abs(n.z))
        k = ax.index(max(ax))
        for lp in f.loops:
            co = lp.vert.co
            lp[uvl].uv = (co.y, co.z) if k == 0 else ((co.x, co.z) if k == 1 else (co.x, co.y))
    Rw = zframe(part.axis).to_4x4() if part.axis is not None else Matrix.Identity(4)
    W = Matrix.Translation(part.pivot) @ Rw
    bmesh.ops.transform(bm, matrix=W.inverted(), verts=bm.verts)
    nm = name or part.name
    me = bpy.data.meshes.new(nm + "_mesh")     # never equal to a node name: GLTFLoader derives primitive names from it
    bm.to_mesh(me)
    bm.free()
    if "uvlock" in me.attributes:
        me.attributes.remove(me.attributes["uvlock"])
    ob = bpy.data.objects.new(nm, me)
    bpy.context.scene.collection.objects.link(ob)
    for mn in part.mats:
        me.materials.append(get_mat(mn))
    place(ob, W, parent, spin_axis=part.axis is not None)
    if part.smooth:
        for p in me.polygons:
            p.use_smooth = True
        me.set_sharp_from_angle(angle=math.radians(part.angle))
        if part.wn:
            mod = ob.modifiers.new("WN", "WEIGHTED_NORMAL")
            mod.keep_sharp = True
            mod.weight = 50
            mod.mode = "FACE_AREA"
            bk.select([ob])
            bpy.ops.object.modifier_apply(modifier=mod.name)
    else:
        for p in me.polygons:
            p.use_smooth = False
    ob["grime"] = 1 if part.grime else 0
    _ALL.append(ob)
    return ob


Part.finish = lambda self, parent=None, name=None: finish(self, parent, name)


def place(ob, W, parent=None, spin_axis=False):
    """Give `ob` world matrix W, expressed relative to `parent` (identity parent-inverse)."""
    if parent is not None:
        bpy.context.view_layer.update()
        ob.parent = parent
        ob.matrix_parent_inverse = Matrix.Identity(4)
        L = parent.matrix_world.inverted() @ W
    else:
        L = W
    loc, rot, _ = L.decompose()
    ob.location = loc
    if spin_axis:
        ob.rotation_mode = "ZYX"
        e = rot.to_matrix().to_euler("ZYX")
        ob.rotation_euler = e
    else:
        ob.rotation_mode = "XYZ"
        ob.rotation_euler = rot.to_matrix().to_euler("XYZ")
    ob["_rest_loc"] = list(ob.location)
    ob["_rest_rot"] = list(ob.rotation_euler)
    ob["_rest_scale"] = list(ob.scale)


def empty(name, loc, parent=None, aim=None, face=None, up=(0, 0, 1), size=0.2):
    """Named node. aim: world dir for local +Y (= three.js -Z, game spotlights shine that way).
    face: world dir for local -Y (= three.js +Z, operators face that way)."""
    o = bpy.data.objects.new(name, None)
    o.empty_display_type = "ARROWS"
    o.empty_display_size = size
    bpy.context.scene.collection.objects.link(o)
    R = Matrix.Identity(3)
    if aim is not None:
        R = frame(aim, up)
    elif face is not None:
        R = frame(-Vector(face), up)
    place(o, Matrix.Translation(Vector(loc)) @ R.to_4x4(), parent)
    return o


def root(name):
    o = bpy.data.objects.new(name, None)
    o.empty_display_type = "PLAIN_AXES"
    bpy.context.scene.collection.objects.link(o)
    o["_rest_loc"] = [0, 0, 0]
    o["_rest_rot"] = [0, 0, 0]
    o["_rest_scale"] = [1, 1, 1]
    return o


# ------------------------------------------------------------------------------------------ decals
_ATLAS = {}


def atlas(name):
    """Load decals/<name>.json manifest: cells -> uv rects (u0, v0, u1, v1) in Blender UV space."""
    if name not in _ATLAS:
        with open(os.path.join(DECALS, name + ".json")) as f:
            _ATLAS[name] = json.load(f)
    return _ATLAS[name]


def cell_uv(atl, cell):
    a = atlas(atl)
    W, H = a["w"], a["h"]
    x, y, w, h = a["cells"][cell]
    return (x / W, 1 - (y + h) / H, (x + w) / W, 1 - y / H)


def cell_aspect(atl, cell):
    x, y, w, h = atlas(atl)["cells"][cell]
    return w / h


def decal(part, c, n, up, w, h, m, uv=(0, 0, 1, 1), off=0.003):
    """Flat decal quad centred at c on a surface with outward normal n; `up` orients the image."""
    c, n, up = Vector(c), Vector(n).normalized(), Vector(up)
    up = (up - n * up.dot(n)).normalized()
    right = up.cross(n)
    o = c + n * off
    co = [o - right * w / 2 - up * h / 2, o + right * w / 2 - up * h / 2, o + right * w / 2 + up * h / 2,
          o - right * w / 2 + up * h / 2]
    u0, v0, u1, v1 = uv
    return part.faces(co, [(0, 1, 2, 3)], m, [[(u0, v0), (u1, v0), (u1, v1), (u0, v1)]])


def decal_cell(part, atl, cell, c, n, up, h=None, w=None, m=None, off=0.003):
    """Decal from an atlas cell keeping its aspect (give h or w)."""
    asp = cell_aspect(atl, cell)
    if h is None:
        h = w / asp
    if w is None:
        w = h * asp
    return decal(part, c, n, up, w, h, m or f"label_{atl}_decals", cell_uv(atl, cell), off)


def decal_wrap(part, atl, cell, axis_p, axis, radius, ang, along, h=None, w=None, m=None, segs=10,
               mode="around", off=0.003, ref=None):
    """Decal wrapped on a cylinder. ang = centre angle (deg) from `ref` (default perp(axis)[0]),
    along = axial position of the centre. mode 'around' = text runs around the circumference
    (image up = +axis); 'along' = text runs along the axis (image up = outward-tangent)."""
    axis = Vector(axis).normalized()
    a, b = perp(axis)
    if ref is not None:
        a = (Vector(ref) - axis * Vector(ref).dot(axis)).normalized()
        b = axis.cross(a)
    asp = cell_aspect(atl, cell)
    if h is None:
        h = w / asp
    if w is None:
        w = h * asp
    u0, v0, u1, v1 = cell_uv(atl, cell)
    R = radius + off
    co, F, U = [], [], []
    base = Vector(axis_p) + axis * along
    if mode == "around":
        arc = w / R
        for i in range(segs + 1):
            t = math.radians(ang) - arc / 2 + arc * i / segs
            rad = a * math.cos(t) + b * math.sin(t)
            co += [base + rad * R - axis * h / 2, base + rad * R + axis * h / 2]
        for i in range(segs):
            F.append((2 * i, 2 * i + 2, 2 * i + 3, 2 * i + 1))
            ua, ub = lerp(u0, u1, i / segs), lerp(u0, u1, (i + 1) / segs)
            U.append([(ua, v0), (ub, v0), (ub, v1), (ua, v1)])
    else:
        # text runs along +axis; image up = -t so it reads unmirrored from outside
        arc = h / R
        for i in range(segs + 1):
            t = math.radians(ang) - arc / 2 + arc * i / segs
            rad = a * math.cos(t) + b * math.sin(t)
            co += [base + rad * R - axis * w / 2, base + rad * R + axis * w / 2]
        for i in range(segs):
            F.append((2 * i, 2 * i + 2, 2 * i + 3, 2 * i + 1))
            va, vb = lerp(v1, v0, i / segs), lerp(v1, v0, (i + 1) / segs)
            U.append([(u0, va), (u0, vb), (u1, vb), (u1, va)])
    fs = part.faces(co, F, m or f"label_{atl}_decals", U)
    for f in fs:
        f.normal_update()
    return fs


def stripe(part, c, n, up, w, h, period=0.2, m="label_hazard", off=0.003):
    """45-degree hazard band: the square tile (one stripe period) repeats every `period` metres."""
    return decal(part, c, n, up, w, h, m, (0, 0, w / period, h / period), off)


# ------------------------------------------------------------------------------------------ animation
_KEYS = {}  # obj -> clip -> list of (prop, idx, frame, value, interp)


def key(obj, clip, prop, idx, frame, value, interp="LINEAR"):
    _KEYS.setdefault(obj, {}).setdefault(clip, []).append((prop, idx, frame, value, interp))


def rest(obj, prop, idx):
    return {"location": obj["_rest_loc"], "rotation_euler": obj["_rest_rot"], "scale": obj["_rest_scale"]}[prop][idx]


def spin(obj, clip, frames, turns=1.0, idx=2, phase=0.0):
    """Linear rotation about the part's local axis (rotation_euler[idx]); turns may be negative."""
    r0 = rest(obj, "rotation_euler", idx) + phase
    key(obj, clip, "rotation_euler", idx, 0, r0, "LINEAR")
    key(obj, clip, "rotation_euler", idx, frames, r0 + TAU * turns, "LINEAR")


def track(obj, clip, prop, idx, pts, interp="BEZIER", relative=True):
    """pts = [(frame, value)...]; values are offsets from rest when relative."""
    base = rest(obj, prop, idx) if relative else 0.0
    for f, v in pts:
        key(obj, clip, prop, idx, f, base + v, interp)


def move(obj, clip, pts, interp="BEZIER"):
    """pts = [(frame, (dx, dy, dz)) ...] offsets in the parent's space."""
    for f, d in pts:
        for i in range(3):
            key(obj, clip, "location", i, f, rest(obj, "location", i) + d[i], interp)


def hold(obj, clip, frames):
    """Keep obj at rest for the whole clip (so crossfades return it cleanly)."""
    for prop in ("location", "rotation_euler"):
        for i in range(3):
            v = rest(obj, prop, i)
            key(obj, clip, prop, i, 0, v, "LINEAR")
            key(obj, clip, prop, i, frames, v, "LINEAR")


def bake_clips():
    prefs = bpy.context.preferences.edit
    for obj, clips in _KEYS.items():
        ad = obj.animation_data or obj.animation_data_create()
        for clip, keys in clips.items():
            act = bpy.data.actions.new(f"{obj.name}|{clip}")
            act.use_fake_user = True
            ad.action = act
            keys = sorted(keys, key=lambda k: k[2])
            for prop, idx, frame, value, interp in keys:
                prefs.keyframe_new_interpolation_type = interp
                getattr(obj, prop)[idx] = value
                obj.keyframe_insert(prop, index=idx, frame=frame)
            tr = ad.nla_tracks.new()
            tr.name = clip
            st = tr.strips.new(clip, 0, act)
            st.name = clip
            tr.mute = True
            ad.action = None
            obj.location = obj["_rest_loc"]
            obj.rotation_euler = obj["_rest_rot"]
            obj.scale = obj["_rest_scale"]
    prefs.keyframe_new_interpolation_type = "BEZIER"


def pose_at(clip, frame):
    """Apply the clip's keyed values at `frame` (for previews): evaluate by linear/bezier via actions."""
    for obj, clips in _KEYS.items():
        ad = obj.animation_data
        if ad is None:
            continue
        act = bpy.data.actions.get(f"{obj.name}|{clip}")
        ad.action = act
    bpy.context.scene.frame_set(frame)


def clear_pose():
    for obj in _KEYS:
        if obj.animation_data:
            obj.animation_data.action = None
        obj.location = obj["_rest_loc"]
        obj.rotation_euler = obj["_rest_rot"]
        obj.scale = obj["_rest_scale"]
    bpy.context.scene.frame_set(0)


# ------------------------------------------------------------------------------------------ grime bake
def _cycles(samples=32):
    s = bpy.context.scene
    s.render.engine = "CYCLES"
    p = bpy.context.preferences.addons["cycles"].preferences
    p.compute_device_type = "CUDA"
    p.get_devices()
    for d in p.devices:
        d.use = d.type != "CPU"
    s.cycles.device = "GPU"
    s.cycles.samples = samples


def bake_grime(objs, distance=0.45, samples=64, floor=True, floor_z=0.0, low=0.32, gamma=1.15, mud=0.8):
    """Cycles AO -> COLOR_0 (corner colours). 1 = clean, darker in crevices + a little road-dirt near the floor."""
    objs = [o for o in objs if o.type == "MESH"]
    if not objs:
        return
    s = bpy.context.scene
    _cycles(samples)
    w = s.world or bpy.data.worlds.new("World")
    s.world = w
    w.light_settings.distance = distance
    tmp = None
    if floor:
        me = bpy.data.meshes.new("_grime_floor")
        R = 40
        me.from_pydata([(-R, -R, floor_z), (R, -R, floor_z), (R, R, floor_z), (-R, R, floor_z)], [], [(0, 1, 2, 3)])
        tmp = bpy.data.objects.new("_grime_floor", me)
        s.collection.objects.link(tmp)
    for o in objs:
        me = o.data
        for a in list(me.color_attributes):
            me.color_attributes.remove(a)
        a = me.color_attributes.new("Col", "FLOAT_COLOR", "CORNER")
        me.color_attributes.active_color = a
        me.color_attributes.render_color_index = me.color_attributes.active_color_index
    bk.select(objs)
    s.render.bake.target = "VERTEX_COLORS"
    s.render.bake.margin = 0
    bpy.ops.object.bake(type="AO")
    for o in objs:
        me = o.data
        a = me.color_attributes["Col"]
        Mw = o.matrix_world
        zs = [(Mw @ v.co).z for v in me.vertices]
        vidx = [0] * len(me.loops)
        me.loops.foreach_get("vertex_index", vidx)
        cols = [0.0] * (len(me.loops) * 4)
        a.data.foreach_get("color", cols)
        for li in range(len(me.loops)):
            ao = cols[li * 4]
            g = low + (1 - low) * (max(0.0, min(1.0, ao)) ** gamma)
            z = zs[vidx[li]] - floor_z
            g *= mud + (1 - mud) * smooth(z / 0.9)
            cols[li * 4:li * 4 + 4] = (g, g, g, 1.0)
        a.data.foreach_set("color", cols)
    if tmp:
        bpy.data.objects.remove(tmp, do_unlink=True)


# ------------------------------------------------------------------------------------------ export + checks
def descendants(o):
    out = [o]
    for c in o.children:
        out += descendants(c)
    return out


def tri_count(objs):
    n = 0
    for o in objs:
        if o.type == "MESH":
            o.data.calc_loop_triangles()
            n += len(o.data.loop_triangles)
    return n


def bounds(objs):
    bpy.context.view_layer.update()
    pts = []
    for o in objs:
        if o.type == "MESH":
            pts += [o.matrix_world @ Vector(c) for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def export(rt, stem):
    """GLB with meshopt, NLA clips (Work/Idle), COLOR_0 grime, embedded label images."""
    path = os.path.abspath(stem + ".glb")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    objs = descendants(rt)
    bk.select(objs, rt)
    bpy.ops.export_scene.gltf(
        filepath=path, export_format="GLB", use_selection=True, export_apply=True, export_yup=True,
        export_animations=True, export_animation_mode="NLA_TRACKS", export_force_sampling=True,
        export_optimize_animation_size=False, export_optimize_animation_keep_anim_object=True,
        export_vertex_color="ACTIVE", export_all_vertex_colors=False,
        export_active_vertex_color_when_no_material=True,
        export_meshopt_compression_enable=os.environ.get("MB_NO_MESHOPT") is None, export_image_format="AUTO", export_extras=False,
        export_tangents=False, export_texcoords=True, export_normals=True)
    size = os.path.getsize(path)
    # read back the JSON chunk for a structural report
    with open(path, "rb") as f:
        data = f.read()
    L = struct.unpack("<I", data[12:16])[0]
    js = json.loads(data[20:20 + L])
    anims = {}
    for an in js.get("animations", []):
        mx = 0.0
        for smp in an["samplers"]:
            acc = js["accessors"][smp["input"]]
            mx = max(mx, acc.get("max", [0])[0])
        anims[an["name"]] = (round(mx, 3), len(an["channels"]))
    names = [n.get("name") for n in js["nodes"]]
    print(f"[mb] exported {path} {size / 1024:.0f} KB  tris={tri_count(objs)}  anims={anims}")
    return path, js, anims, names


def report(rt, limits, extra=""):
    objs = descendants(rt)
    lo, hi = bounds(objs)
    size = hi - lo
    print(f"[mb] {rt.name}: size X(width)={size.x:.2f}  Y(length)={size.y:.2f}  Z(height)={size.z:.2f}  "
          f"lo={tuple(round(v, 2) for v in lo)} hi={tuple(round(v, 2) for v in hi)}  limits={limits} {extra}")
    per = sorted(((tri_count([o]), o.name) for o in objs if o.type == "MESH"), reverse=True)
    print("[mb] tris by part: " + ", ".join(f"{n}:{t}" for t, n in per[:30]))
    return size


# ------------------------------------------------------------------------------------------ previews
def _preview_materials():
    """Preview-only: multiply grime (Col) into library materials + subtle wear noise."""
    for m in bpy.data.materials:
        if not m.get("lib") or m.get("_pv"):
            continue
        nt = m.node_tree
        p = nt.nodes.get("Principled BSDF")
        if p is None:
            continue
        base = tuple(p.inputs["Base Color"].default_value)
        attr = nt.nodes.new("ShaderNodeVertexColor")
        attr.layer_name = "Col"
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.blend_type = "MULTIPLY"
        mix.inputs["Factor"].default_value = 1.0
        mix.inputs[6].default_value = base
        nt.links.new(attr.outputs["Color"], mix.inputs[7])
        noise = nt.nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 3.0
        noise.inputs["Detail"].default_value = 6.0
        tc = nt.nodes.new("ShaderNodeTexCoord")
        nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
        ramp = nt.nodes.new("ShaderNodeMapRange")
        ramp.inputs["From Min"].default_value = 0.3
        ramp.inputs["From Max"].default_value = 0.7
        ramp.inputs["To Min"].default_value = 0.85
        ramp.inputs["To Max"].default_value = 1.05
        nt.links.new(noise.outputs["Fac"], ramp.inputs["Value"])
        mix2 = nt.nodes.new("ShaderNodeMix")
        mix2.data_type = "RGBA"
        mix2.blend_type = "MULTIPLY"
        mix2.inputs["Factor"].default_value = 1.0
        nt.links.new(mix.outputs[2], mix2.inputs[6])
        nt.links.new(ramp.outputs["Result"], mix2.inputs[7])
        nt.links.new(mix2.outputs[2], p.inputs["Base Color"])
        r0 = p.inputs["Roughness"].default_value
        rr = nt.nodes.new("ShaderNodeMapRange")
        rr.inputs["To Min"].default_value = max(0.02, r0 - 0.12)
        rr.inputs["To Max"].default_value = min(1.0, r0 + 0.15)
        nt.links.new(noise.outputs["Fac"], rr.inputs["Value"])
        nt.links.new(rr.outputs["Result"], p.inputs["Roughness"])
        m["_pv"] = True


def stage(objs, ground="#2b2a28", world_strength=0.55, mood="studio"):
    s = bpy.context.scene
    for o in [o for o in s.objects if o.name.startswith("_pv_")]:
        bpy.data.objects.remove(o, do_unlink=True)
    lo, hi = bounds(objs)
    c = (lo + hi) / 2
    rad = (hi - lo).length / 2
    w = s.world or bpy.data.worlds.new("World")
    s.world = w
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    env = nt.nodes.new("ShaderNodeTexEnvironment")
    exr = os.path.join(os.path.dirname(bpy.app.binary_path), "5.2", "datafiles", "studiolights", "world", "interior.exr")
    if os.path.exists(exr):
        env.image = bpy.data.images.load(exr, check_existing=True)
        nt.links.new(env.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = world_strength
    camray = nt.nodes.new("ShaderNodeLightPath")
    bg2 = nt.nodes.new("ShaderNodeBackground")
    bg2.inputs["Color"].default_value = bk.hex_lin("#101215")
    mixs = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(camray.outputs["Is Camera Ray"], mixs.inputs[0])
    nt.links.new(bg.outputs[0], mixs.inputs[1])
    nt.links.new(bg2.outputs[0], mixs.inputs[2])
    nt.links.new(mixs.outputs[0], out.inputs[0])

    def light(name, kind, energy, loc, size=1.0, color="#ffffff"):
        ld = bpy.data.lights.new("_pv_" + name, kind)
        ld.energy = energy
        ld.color = bk.hex_lin(color)[:3]
        if kind == "AREA":
            ld.size = size
        o = bpy.data.objects.new("_pv_" + name, ld)
        s.collection.objects.link(o)
        o.location = c + Vector(loc) * rad
        d = c - o.location
        o.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
        return o

    light("key", "AREA", 900 * rad ** 2, (-1.4, -1.8, 2.2), size=rad * 1.6, color="#fff1de")
    light("fill", "AREA", 260 * rad ** 2, (2.2, -1.0, 0.8), size=rad * 2.5, color="#dfe8ff")
    light("rim", "AREA", 700 * rad ** 2, (0.8, 2.4, 1.6), size=rad * 1.5, color="#ffffff")
    gm = bpy.data.meshes.new("_pv_ground")
    R = rad * 30
    gm.from_pydata([(-R, -R, lo.z - 0.001), (R, -R, lo.z - 0.001), (R, R, lo.z - 0.001), (-R, R, lo.z - 0.001)], [], [(0, 1, 2, 3)])
    go = bpy.data.objects.new("_pv_ground", gm)
    s.collection.objects.link(go)
    gm.materials.append(bk.mat("_pv_ground", ground, rough=0.92))
    return c, rad


def shot(path, objs, az=35, el=20, target=None, dist=None, lens=40, res=(960, 720), fill=1.05, samples=24):
    """EEVEE still. az 0 = from the machine front (-Y side), 90 = from +X side, 180 = rear."""
    s = bpy.context.scene
    lo, hi = bounds(objs)
    c = (lo + hi) / 2 if target is None else Vector(target)
    rad = (hi - lo).length / 2
    for o in [o for o in s.objects if o.name == "_pv_cam"]:
        bpy.data.objects.remove(o, do_unlink=True)
    cd = bpy.data.cameras.new("_pv_cam")
    cd.lens = lens
    cam = bpy.data.objects.new("_pv_cam", cd)
    s.collection.objects.link(cam)
    asp = res[0] / res[1]
    fov = 2 * math.atan(18 / lens * min(asp, 1 / asp))
    d = dist if dist is not None else rad / math.sin(fov / 2) * fill
    a, e = math.radians(az), math.radians(el)
    cam.location = c + Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e))) * d
    cam.rotation_euler = (c - cam.location).to_track_quat("-Z", "Y").to_euler()
    cd.clip_start = 0.05
    cd.clip_end = d * 30
    s.camera = cam
    s.render.engine = "BLENDER_EEVEE"
    ev = s.eevee
    ev.taa_render_samples = samples
    for attr, val in (("use_raytracing", True), ("use_shadows", True), ("use_fast_gi", True)):
        if hasattr(ev, attr):
            try:
                setattr(ev, attr, val)
            except Exception:
                pass
    s.render.resolution_x, s.render.resolution_y = res
    s.render.resolution_percentage = 100
    s.render.film_transparent = False
    s.view_settings.view_transform = "AgX"
    try:
        s.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        pass
    s.render.image_settings.file_format = "PNG"
    s.render.filepath = os.path.abspath(path)
    os.makedirs(os.path.dirname(s.render.filepath), exist_ok=True)
    bpy.ops.render.render(write_still=True)
    print(f"[mb] preview {path}")


def previews(stem, rt, shots_, clip="Work", frame=None):
    """Render a list of shots: dicts with name + shot() kwargs. Poses the given clip frame first."""
    objs = descendants(rt)
    _preview_materials()
    stage(objs)
    if frame is not None:
        pose_at(clip, frame)
    for sh in shots_:
        kw = dict(sh)
        nm = kw.pop("name")
        fr = kw.pop("frame", None)
        if fr is not None:
            pose_at(clip, fr)
        shot(os.path.join(PREVIEWS, f"{stem}_{nm}.png"), objs, **kw)
    clear_pose()


# ------------------------------------------------------------------------------------------ assemblies
def gauge(stat, dec, atl, cell, c, n, up, r, name, parent, needle="paint_red"):
    """Dial gauge: bezel in `stat`, face decal in `dec`, needle = own part (returned) resting on the
    dial's zero mark (-135 deg). Animate rotation_euler[2]: negative = clockwise = higher reading."""
    c, n = Vector(c), Vector(n).normalized()
    up = Vector(up)
    up = (up - n * up.dot(n)).normalized()
    stat.gauge_body(stat_local(stat, c), stat_dir(stat, n), r)
    decal_cell(dec, atl, cell, c, n, up, h=2 * r * 0.93, off=0.001)
    p0 = c + n * 0.007
    nd = Part(name, pivot=p0, axis=n, grime=False)
    d = Matrix.Rotation(math.radians(135), 3, n) @ up
    side = d.cross(n)
    pts = [p0 - d * r * 0.2 - side * r * 0.05, p0 - side * r * 0.05, p0 + d * r * 0.84, p0 + side * r * 0.05,
           p0 - d * r * 0.2 + side * r * 0.05]
    nd.slab(pts, 0.0025, needle, normal=n)
    nd.cyl(p0 - n * 0.002, p0 + n * 0.004, r * 0.1, needle, sides=10)
    return nd.finish(parent)


def stat_local(part, p):
    """World point -> the part's current local frame (gauge_body works in local coords)."""
    return part.T[-1].inverted() @ Vector(p)


def stat_dir(part, d):
    return (part.T[-1].to_3x3().inverted() @ Vector(d)).normalized()


def needle_keys(ob, clip, frames, value_deg, jitter_deg=4.0, step=6, seed=1, idle=None):
    """Needle reading ~value (degrees clockwise from zero) with flicker; loops seamlessly."""
    r = random.Random(seed)
    pts = []
    f = 0
    while f < frames:
        pts.append((f, -math.radians(value_deg + r.uniform(-jitter_deg, jitter_deg))))
        f += step + r.randint(-2, 2)
    pts.append((frames, pts[0][1]))
    track(ob, clip, "rotation_euler", 2, pts, interp="BEZIER")


def pile(part, c, rx, ry, h, mats, n=26, seed=3, lump=(0.05, 0.13)):
    """Heap of broken rock: deformed mound + loose lumps (flat shaded part recommended)."""
    rng = random.Random(seed)
    c = Vector(c)

    def mound(v, r_):
        k = 1 + 0.18 * math.sin(v.x * 9.1 + seed) * math.cos(v.y * 7.3) + r_.uniform(-0.06, 0.06)
        return Vector((v.x * k, v.y * k, max(0.0, v.z) * k))
    part.ico(c, 1.0, mats[0], detail=2, scale=(rx, ry, h), deform=mound, seed=seed)
    for i in range(n):
        a = rng.uniform(0, TAU)
        rr = math.sqrt(rng.uniform(0, 1))
        x, y = math.cos(a) * rr * rx * 1.05, math.sin(a) * rr * ry * 1.05
        z = h * max(0.0, 1 - rr * rr) ** 0.7
        s = rng.uniform(*lump)

        def lumpy(v, r_):
            return Vector((v.x * r_.uniform(0.7, 1.3), v.y * r_.uniform(0.7, 1.3), v.z * r_.uniform(0.6, 1.0)))
        part.ico(c + Vector((x, y, z * 0.85)), s, rng.choice(mats), detail=1, scale=(1, 1, 0.75),
                 rot=(rng.uniform(0, 90), rng.uniform(0, 90), rng.uniform(0, 360)), deform=lumpy, seed=seed * 100 + i)


def std_materials():
    """Shared label/custom materials every machine may use."""
    d = DECALS
    label("label_hazard", os.path.join(d, "hazard.png"), mode="OPAQUE", repeat=True, rough=0.6)
    custom("custom_chequer", base=os.path.join(d, "chequer_c.png"), normal=os.path.join(d, "chequer_n.png"), metal=0.85, rough=0.42)
    custom("custom_grating", base=os.path.join(d, "grating.png"), clip=True, metal=0.8, rough=0.5, double=True)


def ceiling(z, cx=0.0, cy=0.0, sx=4.0, sy=4.0, hole=None, seed=5):
    """Preview-only rough rock roof (not exported, no shadows) so roof-entering parts read in renders."""
    rng = random.Random(seed)
    p = Part("_ctx_ceiling", smooth=False, wn=False)
    n = 16
    co = []
    for j in range(n + 1):
        for i in range(n + 1):
            x = cx - sx / 2 + sx * i / n
            y = cy - sy / 2 + sy * j / n
            co.append((x, y, z + rng.uniform(-0.05, 0.12)))
    F = []
    for j in range(n):
        for i in range(n):
            a = j * (n + 1) + i
            q = [a, a + n + 1, a + n + 2, a + 1]
            if hole:
                xm = cx - sx / 2 + sx * (i + 0.5) / n
                ym = cy - sy / 2 + sy * (j + 0.5) / n
                if math.hypot(xm - hole[0], ym - hole[1]) < hole[2]:
                    continue
            F.append(tuple(q))
    p.faces(co, F, "rock")
    o = p.finish()
    o.visible_shadow = False
    return o


def merge(objs, name):
    """Join static parts (same parent, identity transforms) into one mesh: one draw call per material."""
    objs = [o for o in objs if o is not None]
    def _top(o):
        bpy.context.view_layer.update()
        return max((o.matrix_world @ Vector(c)).z for c in o.bound_box)
    print("[mb] merge " + name + ": " + ", ".join(f"{o.name}:{tri_count([o])}(z<={_top(o):.2f})" for o in objs))
    bk.select(objs, objs[0])
    bpy.ops.object.join()
    o = bpy.context.view_layer.objects.active
    o.name = name
    o.data.name = name + "_mesh"
    o["grime"] = 1
    return o


def water_material():
    """custom_water: emissive-free, slightly transparent blue-grey sheet with flow streaks + ripple normals."""
    return custom("custom_water", color="#7f98a4", rough=0.05, base=os.path.join(DECALS, "water_c.png"),
                  normal=os.path.join(DECALS, "water_n.png"), alpha_tex=True, double=True, normal_strength=0.8)


def trommel_material():
    """custom_trommel: punched screen plate (alpha mask), visible from both sides."""
    return custom("custom_trommel", color="#7c8186", rough=0.45, metal=0.85, base=os.path.join(DECALS, "perforated.png"),
                  clip=True, double=True)


def molten_material(strength=7.0):
    """custom_molten: strong orange emissive (crust-cell texture drives both colour and glow), kept as-is."""
    return custom("custom_molten", color="#ff7a1a", rough=0.35, base=os.path.join(DECALS, "molten.png"),
                  emis=os.path.join(DECALS, "molten.png"), emit=strength)
