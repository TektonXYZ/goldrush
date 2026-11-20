"""mk: MOTHERLODE mine-kit mesh builder (Blender 5.2, run through `bl`).

Ideas from How to Trench's mb.py, rewritten for PBR library assets:
  * every primitive is built in its own tiny bmesh in LOCAL coordinates, optionally bevelled there,
    gets UVs in METRES by a projection that suits it (box: long axis -> U, cylinder: axis -> U,
    tube: length -> U), then is transformed and appended into ONE bmesh per node, so a prop with
    hundreds of parts builds in milliseconds and has one draw call per material.
  * materials are referenced by LIBRARY NAME (src/core/materials.ts swaps them at load).
  * finish(): sharp edges by angle, smooth shading, weighted normals, optional grime colour layer.

    mb = MB("timber_set")
    mb.box((0.25, 0.25, 2.8), "wood_timber", loc=(1.9, 0, 0), bevel=0.012)
    mb.rod((0, 0, 0), (0, 1, 0), 0.02, "steel")
    obj = mb.finish()
"""
import json
import math
import os
import random
import struct
import zlib

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector, noise

HERE = os.path.dirname(os.path.abspath(__file__))
DEG = math.pi / 180.0


def seed_of(name, extra=0):
    return (zlib.crc32(name.encode()) ^ (extra * 2654435761)) & 0xFFFFFFFF


def V(*a):
    return Vector(a[0]) if len(a) == 1 else Vector(a)


def rotm(rot):
    """Euler XYZ in degrees -> 4x4."""
    return Euler([a * DEG for a in rot], "XYZ").to_matrix().to_4x4()


def trs(loc=(0, 0, 0), rot=(0, 0, 0), scale=None):
    m = Matrix.Translation(Vector(loc)) @ rotm(rot)
    if scale is not None:
        m = m @ Matrix.Diagonal((*scale, 1.0))
    return m


def frame(x_axis, up=(0, 0, 1)):
    """Rotation (4x4) whose local X runs along x_axis and local Z is as close to `up` as possible."""
    x = Vector(x_axis).normalized()
    u = Vector(up)
    if abs(x.dot(u.normalized())) > 0.999:
        u = Vector((0, 1, 0)) if abs(x.y) < 0.9 else Vector((1, 0, 0))
    y = u.cross(x).normalized()
    z = x.cross(y).normalized()
    m = Matrix((x, y, z)).transposed().to_4x4()
    return m


def lerp(a, b, t):
    return a + (b - a) * t


def smoothstep(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


# ====================================================================== materials
# Library names (docs/CONTRACTS.md) with preview/export defaults: (sRGB hex, roughness, metallic)
LIB = {
    "paint_yellow": ("#E8B400", 0.5, 0.0), "paint_orange": ("#D9601A", 0.5, 0.0),
    "paint_red": ("#9E2219", 0.5, 0.0), "paint_white": ("#E3E1DA", 0.5, 0.0),
    "paint_black": ("#1C1C1C", 0.5, 0.0), "paint_green": ("#2E5A36", 0.5, 0.0),
    "paint_blue": ("#1E4A86", 0.5, 0.0), "paint_grey": ("#6B6F73", 0.5, 0.0),
    "steel": ("#8B8E91", 0.38, 1.0), "steel_dark": ("#3B3C3E", 0.5, 0.85),
    "galvanized": ("#A6AAAD", 0.42, 1.0), "chrome": ("#E2E4E6", 0.08, 1.0),
    "rust": ("#6A3A1F", 0.85, 0.25), "cast_iron": ("#3C3A37", 0.7, 0.6),
    "copper": ("#B8693F", 0.35, 1.0), "brass": ("#B58A3A", 0.32, 1.0),
    "gold": ("#E5B53A", 0.2, 1.0), "aluminium": ("#C4C7CA", 0.35, 1.0),
    "rubber": ("#191919", 0.85, 0.0), "hose_red": ("#9E2018", 0.6, 0.0),
    "hose_yellow": ("#D9A300", 0.55, 0.0), "cable": ("#141414", 0.55, 0.0),
    "plastic_black": ("#151515", 0.45, 0.0), "plastic_yellow": ("#E3AE00", 0.45, 0.0),
    "wood_timber": ("#7A5A3B", 0.9, 0.0), "wood_planks": ("#8A7357", 0.88, 0.0),
    "wood_dark": ("#4A3626", 0.85, 0.0), "wood_painted_white": ("#D8D4C8", 0.7, 0.0),
    "wood_painted_red": ("#8E2A1E", 0.7, 0.0), "wood_painted_green": ("#2E4A30", 0.7, 0.0),
    "concrete": ("#8E8C88", 0.9, 0.0), "brick": ("#8A4A36", 0.9, 0.0),
    "corrugated": ("#8F9396", 0.5, 1.0), "canvas": ("#8C7E62", 0.92, 0.0),
    "glass": ("#DCE6EC", 0.04, 0.0), "glass_dark": ("#1E2428", 0.08, 0.0),
    "rock": ("#5C5853", 0.9, 0.0), "rock_dark": ("#2F2D2B", 0.85, 0.0),
    "rock_red": ("#6A3A2A", 0.9, 0.0), "rock_pale": ("#9A968E", 0.9, 0.0),
    "gravel": ("#5F5B55", 0.95, 0.0), "dirt": ("#54453A", 0.95, 0.0),
    "coal_ore": ("#141414", 0.45, 0.0), "iron_ore": ("#5A3424", 0.8, 0.2),
    "silver_ore": ("#8E9296", 0.5, 0.4), "gold_ore": ("#6E5A2A", 0.5, 0.5),
    "leather": ("#5A3A22", 0.7, 0.0), "helmet_yellow": ("#F0B400", 0.32, 0.0),
    "helmet_white": ("#ECEBE6", 0.32, 0.0), "fabric_hivis": ("#F06A10", 0.85, 0.0),
    "emit_warm": ("#FFC27A", 0.4, 0.0), "emit_white": ("#F4F6FF", 0.4, 0.0),
    "emit_red": ("#FF3020", 0.4, 0.0), "emit_green": ("#40FF70", 0.4, 0.0),
    "emit_amber": ("#FFA010", 0.4, 0.0), "emit_screen": ("#101820", 0.2, 0.0),
    "sign_face": ("#E6E0CF", 0.7, 0.0),
}
EMIT = {"emit_warm": ("#FFB46A", 12.0), "emit_white": ("#EEF2FF", 10.0), "emit_red": ("#FF2A1A", 8.0),
        "emit_green": ("#38FF66", 8.0), "emit_amber": ("#FF9A10", 8.0), "emit_screen": ("#22384A", 1.5)}

_ATLAS = None


def atlas():
    """Label atlas rects (pixels) written by labels.mjs -> {name: [x, y, w, h]} + size."""
    global _ATLAS
    if _ATLAS is None:
        p = os.path.join(HERE, "build", "labels.json")
        _ATLAS = json.load(open(p)) if os.path.exists(p) else {"size": [2048, 2048], "rects": {}}
    return _ATLAS


def _image(path, name):
    img = bpy.data.images.get(name)
    if img is None:
        img = bpy.data.images.load(path, check_existing=True)
        img.name = name
    return img


def _vc_mult(nt, color_socket_from, p):
    """base * grime colour attribute (preview only: the game's library multiplies COLOR_0 the same way)."""
    attr = nt.nodes.new("ShaderNodeVertexColor")
    attr.layer_name = "Col"
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    mix.inputs["Factor"].default_value = 1.0
    if color_socket_from is None:
        mix.inputs[6].default_value = p.inputs["Base Color"].default_value[:]
    else:
        nt.links.new(color_socket_from, mix.inputs[6])
    nt.links.new(attr.outputs["Color"], mix.inputs[7])
    nt.links.new(mix.outputs[2], p.inputs["Base Color"])
    return attr


def hexlin(h):
    h = h.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return (*out, 1.0)


def M(name):
    """Material by library name (created once). label_*/custom_* are created by label_mat/custom_mat."""
    m = bpy.data.materials.get(name)
    if m is not None:
        return m
    if name not in LIB:
        raise KeyError(f"not a library material: {name}")
    col, rough, metal = LIB[name]
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    p = nt.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value = hexlin(col)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    if name in EMIT:
        ec, es = EMIT[name]
        p.inputs["Emission Color"].default_value = hexlin(ec)
        p.inputs["Emission Strength"].default_value = es
    if name == "glass":
        p.inputs["Alpha"].default_value = 0.22
        p.inputs["IOR"].default_value = 1.5
        m.surface_render_method = "BLENDED"
    m.diffuse_color = hexlin(col)
    m["lib"] = True
    return m


def label_mat(name="label_minekit", emissive=False, rough=0.55, double=False):
    """Atlas decal material (kept as-is by the game): base colour (+ emission) from labels.png, alpha clip."""
    m = bpy.data.materials.get(name)
    if m is not None:
        return m
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    p = nt.nodes.get("Principled BSDF")
    img = _image(os.path.join(HERE, "build", "labels.png"), "labels.png")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.interpolation = "Linear"
    nt.links.new(tex.outputs["Color"], p.inputs["Base Color"])
    rnd = nt.nodes.new("ShaderNodeMath")
    rnd.operation = "ROUND"
    nt.links.new(tex.outputs["Alpha"], rnd.inputs[0])
    nt.links.new(rnd.outputs[0], p.inputs["Alpha"])
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = 0.0
    if emissive:
        nt.links.new(tex.outputs["Color"], p.inputs["Emission Color"])
        p.inputs["Emission Strength"].default_value = 1.6
    m.use_backface_culling = not double
    m.surface_render_method = "DITHERED"
    m["label"] = True
    return m


def custom_mat(name, png, rough=0.5, metal=0.0, double=True, alpha_clip=True):
    """Tiling alpha-cut texture material (wire mesh, expanded metal). UVs: 1 unit = one texture tile."""
    m = bpy.data.materials.get(name)
    if m is not None:
        return m
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    p = nt.nodes.get("Principled BSDF")
    img = _image(os.path.join(HERE, "build", png), png)
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    nt.links.new(tex.outputs["Color"], p.inputs["Base Color"])
    if alpha_clip:
        rnd = nt.nodes.new("ShaderNodeMath")
        rnd.operation = "ROUND"
        nt.links.new(tex.outputs["Alpha"], rnd.inputs[0])
        nt.links.new(rnd.outputs[0], p.inputs["Alpha"])
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    m.use_backface_culling = not double
    m.surface_render_method = "DITHERED"
    m["custom"] = True
    return m


def get_mat(name):
    if isinstance(name, bpy.types.Material):
        return name
    if name.startswith("label_"):
        return label_mat(name, emissive=name.endswith("_glow"))
    return M(name)


# ====================================================================== UV projections (local space)

def uv_box(size):
    """Box mapping in metres, the longest dimension runs along U on every long face (wood grain)."""
    order = sorted(range(3), key=lambda i: -size[i])
    L = order[0]

    def fn(f, lp):
        n = f.normal
        a = max(range(3), key=lambda i: abs(n[i]))
        co = lp.vert.co
        if a != L:
            other = 3 - a - L
            return co[L], co[other]
        return co[order[1]], co[order[2]]
    return fn


def uv_world_box(f, lp):
    n = f.normal
    a = max(range(3), key=lambda i: abs(n[i]))
    co = lp.vert.co
    if a == 0:
        return co.y, co.z
    if a == 1:
        return co.x, co.z
    return co.x, co.y


def _angle_fix(a, ref):
    while a - ref > math.pi:
        a -= 2 * math.pi
    while ref - a > math.pi:
        a += 2 * math.pi
    return a


def uv_cyl(r):
    """Cylinder along local Z: sides U = z (axis), V = arc length; caps planar."""
    def fn(f, lp):
        n = f.normal
        co = lp.vert.co
        if abs(n.z) > 0.75:
            return co.x, co.y
        c = f.calc_center_median()
        a = _angle_fix(math.atan2(co.y, co.x), math.atan2(c.y, c.x))
        return co.z, a * r
    return fn


# ====================================================================== the builder

class MB:
    def __init__(self, name, seed=0):
        self.name = name
        self.bm = bmesh.new()
        self.uvl = self.bm.loops.layers.uv.new("UVMap")
        self.flat = self.bm.faces.layers.int.new("flat")
        self.mats = []
        self.rng = random.Random(seed_of(name, seed))

    # ------------------------------------------------------------------ core
    def mi(self, mat):
        m = get_mat(mat)
        if m not in self.mats:
            self.mats.append(m)
        return self.mats.index(m)

    def commit(self, tb, Mx, mat, uvfn=None, uvoff=True, flat=False, smooth=True, uvscale=1.0):
        """Append temp bmesh `tb` (local coords, normals valid) with transform Mx.
        mat: a material name, or a list with one name per face of tb (in tb.faces order)."""
        per_face = isinstance(mat, (list, tuple))
        mi = None if per_face else self.mi(mat)
        if uvoff is True:
            ou, ov = self.rng.uniform(0, 8), self.rng.uniform(0, 8)
        elif uvoff:
            ou, ov = uvoff
        else:
            ou = ov = 0.0
        tuv = tb.loops.layers.uv.active
        vmap = {v: self.bm.verts.new(Mx @ v.co) for v in tb.verts}
        out = []
        for fi, f in enumerate(tb.faces):
            try:
                g = self.bm.faces.new([vmap[v] for v in f.verts])
            except ValueError:
                continue
            g.material_index = self.mi(mat[fi]) if per_face else mi
            g.smooth = smooth and not flat
            g[self.flat] = 1 if flat else 0
            for lt, lg in zip(f.loops, g.loops):
                if uvfn is not None:
                    u, v = uvfn(f, lt)
                elif tuv is not None:
                    u, v = lt[tuv].uv
                else:
                    u, v = 0.0, 0.0
                lg[self.uvl].uv = (u * uvscale + ou, v * uvscale + ov)
            out.append(g)
        tb.free()
        return out

    @staticmethod
    def _bevel(tb, width, seg, min_angle=0.9):
        if width <= 0:
            return
        tb.normal_update()
        edges = [e for e in tb.edges if len(e.link_faces) == 2 and e.calc_face_angle(0) > min_angle]
        if edges:
            bmesh.ops.bevel(tb, geom=edges, offset=width, offset_type="OFFSET", segments=seg, profile=0.5,
                            affect="EDGES", clamp_overlap=True)
        tb.normal_update()

    # ------------------------------------------------------------------ primitives
    def box(self, size, mat, loc=(0, 0, 0), rot=(0, 0, 0), bevel=0.0, seg=2, center=False, cuts=None,
            warp=None, uvoff=True, Mx=None, flat=False):
        """Box sized in metres resting ON loc (or centred on it with center=True).
        cuts=(nx,ny,nz) subdivides for deformation/grime resolution; warp(v_local)->v_local deforms."""
        sx, sy, sz = size
        tb = bmesh.new()
        lift = 0.0 if center else sz / 2
        bmesh.ops.create_cube(tb, size=1.0, matrix=Matrix.Translation((0, 0, lift)) @ Matrix.Diagonal((sx, sy, sz, 1)))
        if cuts:
            for axis, n in enumerate(cuts):
                if n and n > 0:
                    for k in range(1, n + 1):
                        t = -0.5 + k / (n + 1)
                        co = [0, 0, 0]
                        co[axis] = t * size[axis] + (lift if axis == 2 else 0)
                        no = [0, 0, 0]
                        no[axis] = 1
                        geom = tb.verts[:] + tb.edges[:] + tb.faces[:]
                        bmesh.ops.bisect_plane(tb, geom=geom, plane_co=co, plane_no=no)
        tb.normal_update()
        self._bevel(tb, bevel, seg)
        if warp:
            for v in tb.verts:
                v.co = warp(v.co.copy())
            tb.normal_update()
        Mx = Mx if Mx is not None else trs(loc, rot)
        return self.commit(tb, Mx, mat, uv_box(size), uvoff=uvoff, flat=flat)

    def boxc(self, center, size, mat, rot=(0, 0, 0), **kw):
        return self.box(size, mat, loc=center, rot=rot, center=True, **kw)

    def beam(self, a, b, w, h, mat, up=(0, 0, 1), bevel=0.0, seg=2, ext=0.0, roll=0.0, cuts=None, warp=None):
        """Rectangular member from a to b (width w across, height h along `up`)."""
        a, b = Vector(a), Vector(b)
        d = b - a
        L = d.length + 2 * ext
        Mx = Matrix.Translation((a + b) / 2) @ frame(d, up) @ rotm((roll, 0, 0))
        n = None
        if cuts:
            n = (cuts, 0, 0)
        return self.box((L, w, h), mat, bevel=bevel, seg=seg, center=True, Mx=Mx, cuts=n, warp=warp)

    def cyl(self, r, h, mat, sides=12, loc=(0, 0, 0), rot=(0, 0, 0), r2=None, bevel=0.0, seg=2, cap=True,
            center=False, Mx=None, uvoff=True, flat=False, smooth=True):
        """Cylinder/frustum along local Z resting ON loc (or centred)."""
        tb = bmesh.new()
        lift = 0.0 if center else h / 2
        bmesh.ops.create_cone(tb, cap_ends=cap, cap_tris=False, segments=sides, radius1=r,
                              radius2=r if r2 is None else r2, depth=h, matrix=Matrix.Translation((0, 0, lift)))
        tb.normal_update()
        if cap:
            self._bevel(tb, bevel, seg, min_angle=1.2)
        Mx = Mx if Mx is not None else trs(loc, rot)
        return self.commit(tb, Mx, mat, uv_cyl(max(r, r2 or 0)), uvoff=uvoff, flat=flat, smooth=smooth)

    def rod(self, a, b, r, mat, sides=8, cap=True, bevel=0.0, r2=None, ext=0.0, seg=1, roll=0.0):
        """Cylinder from point a to b."""
        a, b = Vector(a), Vector(b)
        d = b - a
        L = d.length
        if L < 1e-6:
            return []
        q = d.normalized().to_track_quat("Z", "Y").to_matrix().to_4x4()
        Mx = Matrix.Translation(a - d.normalized() * ext) @ q @ rotm((0, 0, roll))
        return self.cyl(r, L + 2 * ext, mat, sides=sides, Mx=Mx, cap=cap, bevel=bevel, r2=r2, seg=seg)

    def lathe(self, prof, mat, sides=16, Mx=None, loc=(0, 0, 0), rot=(0, 0, 0), cap0=False, cap1=False,
              arc=None, uvoff=True, flat=False):
        """Revolve profile [(r, z), ...] about local Z. U = around (metres at that radius), V = along profile."""
        Mx = Mx if Mx is not None else trs(loc, rot)
        tb = bmesh.new()
        uvl = tb.loops.layers.uv.new("uv")
        full = arc is None
        a0, a1 = (0.0, 2 * math.pi) if full else (arc[0] * DEG, arc[1] * DEG)
        n = sides
        cols = n if full else n + 1
        # profile arc length
        s = [0.0]
        for i in range(1, len(prof)):
            s.append(s[-1] + math.hypot(prof[i][0] - prof[i - 1][0], prof[i][1] - prof[i - 1][1]))
        rmax = max(p[0] for p in prof) or 0.01
        grid = []
        for (r, z) in prof:
            row = []
            for k in range(cols):
                a = a0 + (a1 - a0) * k / n
                row.append(tb.verts.new((r * math.cos(a), r * math.sin(a), z)))
            grid.append(row)
        for i in range(len(prof) - 1):
            for k in range(n):
                k2 = (k + 1) % cols if full else k + 1
                vs = [grid[i][k], grid[i][k2], grid[i + 1][k2], grid[i + 1][k]]
                if len(set(vs)) < 3:
                    continue
                try:
                    f = tb.faces.new(vs)
                except ValueError:
                    continue
                uvs = [(k / n * (a1 - a0) * rmax, s[i]), ((k + 1) / n * (a1 - a0) * rmax, s[i]),
                       ((k + 1) / n * (a1 - a0) * rmax, s[i + 1]), (k / n * (a1 - a0) * rmax, s[i + 1])]
                for lp, uv in zip(f.loops, uvs):
                    lp[uvl].uv = uv
        for cap, row, flip in ((cap0, grid[0], True), (cap1, grid[-1], False)):
            if cap and prof[0 if flip else -1][0] > 1e-5 and full:
                vs = list(reversed(row)) if flip else list(row)
                try:
                    f = tb.faces.new(vs)
                    for lp in f.loops:
                        lp[uvl].uv = (lp.vert.co.x, lp.vert.co.y)
                except ValueError:
                    pass
        bmesh.ops.remove_doubles(tb, verts=tb.verts[:], dist=1e-6)
        bmesh.ops.recalc_face_normals(tb, faces=tb.faces[:])
        tb.normal_update()
        return self.commit(tb, Mx, mat, None, uvoff=uvoff, flat=flat)

    def tube(self, pts, r, mat, sides=8, caps=False, closed=False, radii=None, uvoff=True, twist=0.0, flat=False):
        """Tube through world points (cables, hoses, bent bars). U = length, V = around."""
        pts = [Vector(p) for p in pts]
        if closed:
            pts = pts + [pts[0]]
        n = len(pts)
        tans = []
        for i in range(n):
            if closed and (i == 0 or i == n - 1):
                d = pts[1] - pts[-2]
            else:
                d = pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]
            tans.append(d.normalized())
        # parallel transport
        ref = Vector((0, 0, 1)) if abs(tans[0].z) < 0.9 else Vector((1, 0, 0))
        nrm = tans[0].cross(ref).normalized()
        frames = []
        for i in range(n):
            if i > 0:
                axis = tans[i - 1].cross(tans[i])
                if axis.length > 1e-8:
                    ang = tans[i - 1].angle(tans[i], 0.0)
                    nrm = Matrix.Rotation(ang, 3, axis.normalized()) @ nrm
            bin_ = tans[i].cross(nrm).normalized()
            frames.append((nrm.copy(), bin_))
        tb = bmesh.new()
        uvl = tb.loops.layers.uv.new("uv")
        rings = []
        s = [0.0]
        for i in range(1, n):
            s.append(s[-1] + (pts[i] - pts[i - 1]).length)
        for i, p in enumerate(pts):
            rr = radii[i] if radii else r
            a_, b_ = frames[i]
            ring = []
            for k in range(sides):
                t = k / sides * 2 * math.pi + twist * s[i]
                ring.append(tb.verts.new(p + (a_ * math.cos(t) + b_ * math.sin(t)) * rr))
            rings.append(ring)
        for i in range(n - 1):
            for k in range(sides):
                k2 = (k + 1) % sides
                f = tb.faces.new((rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]))
                uvs = [(s[i], k / sides * 2 * math.pi * r), (s[i], (k + 1) / sides * 2 * math.pi * r),
                       (s[i + 1], (k + 1) / sides * 2 * math.pi * r), (s[i + 1], k / sides * 2 * math.pi * r)]
                for lp, uv in zip(f.loops, uvs):
                    lp[uvl].uv = uv
        if caps and not closed:
            for ring, rev in ((rings[0], True), (rings[-1], False)):
                f = tb.faces.new(list(reversed(ring)) if rev else ring)
                for lp in f.loops:
                    lp[uvl].uv = (0.0, 0.0)
        if closed:
            # weld seam ring
            bmesh.ops.remove_doubles(tb, verts=rings[0] + rings[-1], dist=1e-5)
        bmesh.ops.recalc_face_normals(tb, faces=tb.faces[:])
        tb.normal_update()
        return self.commit(tb, Matrix.Identity(4), mat, None, uvoff=uvoff, flat=flat)

    def sweep(self, prof, path, mat, up=(0, 0, 1), caps=True, uvoff=True, closed_path=False, scale_fn=None):
        """Sweep a closed 2D profile [(x, y)] along a 3D path. Profile x -> path-normal, y -> binormal ~ up."""
        path = [Vector(p) for p in path]
        n = len(path)
        upv = Vector(up)
        tb = bmesh.new()
        uvl = tb.loops.layers.uv.new("uv")
        rings, s = [], [0.0]
        for i in range(1, n):
            s.append(s[-1] + (path[i] - path[i - 1]).length)
        for i, p in enumerate(path):
            if closed_path:
                t = (path[(i + 1) % n] - path[(i - 1) % n]).normalized()
            else:
                t = (path[min(i + 1, n - 1)] - path[max(i - 1, 0)]).normalized()
            u = upv if callable(upv) is False else upv(i)
            side = t.cross(u)
            if side.length < 1e-6:
                side = t.cross(Vector((1, 0, 0)))
            side.normalize()
            yb = side.cross(t).normalized()
            sc = scale_fn(i / max(n - 1, 1)) if scale_fn else 1.0
            rings.append([tb.verts.new(p + side * (x * sc) + yb * (y * sc)) for (x, y) in prof])
        m = len(prof)
        per = [0.0]
        for k in range(1, m + 1):
            a, b = prof[k - 1], prof[k % m]
            per.append(per[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
        segs = n if closed_path else n - 1
        for i in range(segs):
            i2 = (i + 1) % n
            si2 = s[i2] if i2 else s[-1] + (path[0] - path[-1]).length
            for k in range(m):
                k2 = (k + 1) % m
                try:
                    f = tb.faces.new((rings[i][k], rings[i][k2], rings[i2][k2], rings[i2][k]))
                except ValueError:
                    continue
                uvs = [(s[i], per[k]), (s[i], per[k + 1]), (si2, per[k + 1]), (si2, per[k])]
                for lp, uv in zip(f.loops, uvs):
                    lp[uvl].uv = uv
        if caps and not closed_path:
            for ring, rev in ((rings[0], False), (rings[-1], True)):
                try:
                    f = tb.faces.new(list(reversed(ring)) if rev else ring)
                    for lp in f.loops:
                        lp[uvl].uv = (lp.vert.co.x + lp.vert.co.z, lp.vert.co.y + lp.vert.co.z)
                except ValueError:
                    pass
        bmesh.ops.recalc_face_normals(tb, faces=tb.faces[:])
        tb.normal_update()
        return self.commit(tb, Matrix.Identity(4), mat, None, uvoff=uvoff)

    def extrude(self, prof, y0, y1, mat, Mx=None, caps=True, uvoff=True, segs=1, warp=None):
        """Straight extrusion of a closed profile [(x, z)] along local Y from y0 to y1 (segs rows).
        mat: name or one name per profile edge. warp(Vector)->Vector deforms (dents)."""
        tb = bmesh.new()
        uvl = tb.loops.layers.uv.new("uv")
        m = len(prof)
        ys = [y0 + (y1 - y0) * k / segs for k in range(segs + 1)]
        rings = [[tb.verts.new((x, y, z)) for x, z in prof] for y in ys]
        per = [0.0]
        for k in range(1, m + 1):
            a, b = prof[k - 1], prof[k % m]
            per.append(per[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
        face_mats = []
        for j in range(segs):
            r0, r1 = rings[j], rings[j + 1]
            for k in range(m):
                k2 = (k + 1) % m
                f = tb.faces.new((r0[k], r0[k2], r1[k2], r1[k]))
                for lp, uv in zip(f.loops, [(ys[j], per[k]), (ys[j], per[k + 1]), (ys[j + 1], per[k + 1]), (ys[j + 1], per[k])]):
                    lp[uvl].uv = uv
                face_mats.append(mat[k] if isinstance(mat, (list, tuple)) else mat)
        if caps:
            for ring in (rings[0], list(reversed(rings[-1]))):
                try:
                    f = tb.faces.new(ring)
                    for lp in f.loops:
                        lp[uvl].uv = (lp.vert.co.x, lp.vert.co.z)
                    face_mats.append(mat[0] if isinstance(mat, (list, tuple)) else mat)
                except ValueError:
                    pass
        if warp:
            for v in tb.verts:
                v.co = warp(v.co.copy())
        bmesh.ops.recalc_face_normals(tb, faces=tb.faces[:])
        tb.normal_update()
        return self.commit(tb, Mx if Mx is not None else Matrix.Identity(4), face_mats, None, uvoff=uvoff)

    def poly(self, pts, mat, thick=0.0, uv="plane", uvoff=True, flat=False):
        """Polygon from world points (optionally a slab of `thick` behind its normal)."""
        tb = bmesh.new()
        vs = [tb.verts.new(p) for p in pts]
        f = tb.faces.new(vs)
        f.normal_update()
        if thick:
            nrm = f.normal * thick
            back = [tb.verts.new(Vector(p) - nrm) for p in pts]
            tb.faces.new(list(reversed(back)))
            k = len(pts)
            for i in range(k):
                tb.faces.new((vs[(i + 1) % k], vs[i], back[i], back[(i + 1) % k]))
        tb.normal_update()
        return self.commit(tb, Matrix.Identity(4), mat, uv_world_box, uvoff=uvoff, flat=flat)

    def grid(self, w, h, nx, ny, mat, Mx, fn=None, uv01=False, uvoff=True, flat=False, smooth=True):
        """Subdivided plane in local XZ facing -Y (front), w x h centred; fn(u, v) -> local offset Vector."""
        tb = bmesh.new()
        uvl = tb.loops.layers.uv.new("uv")
        vs = []
        for j in range(ny + 1):
            row = []
            for i in range(nx + 1):
                u, v = i / nx, j / ny
                co = Vector(((u - 0.5) * w, 0.0, (v - 0.5) * h))
                if fn:
                    co = co + fn(u, v)
                row.append((tb.verts.new(co), (u, v)))
            vs.append(row)
        for j in range(ny):
            for i in range(nx):
                q = [vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]]
                f = tb.faces.new([a for a, _ in q])
                for lp, (_, (u, v)) in zip(f.loops, q):
                    lp[uvl].uv = (u, v) if uv01 else ((u - 0.5) * w, (v - 0.5) * h)
        tb.normal_update()
        return self.commit(tb, Mx, mat, None, uvoff=False if uv01 else uvoff, flat=flat, smooth=smooth)

    def quad(self, center, w, h, mat, rot=(0, 0, 0), rect=None, Mx=None, double=False):
        """Single quad facing -Y (front) in local XZ, centred. rect = atlas name or (u0, v0, u1, v1) UV box."""
        if isinstance(rect, str):
            A = atlas()
            W, H = A["size"]
            x, y, rw, rh = A["rects"][rect]
            u0, u1 = x / W, (x + rw) / W
            v0, v1 = 1 - (y + rh) / H, 1 - y / H
        elif rect is None:
            u0, v0, u1, v1 = 0.0, 0.0, 1.0, 1.0
        else:
            u0, v0, u1, v1 = rect
        tb = bmesh.new()
        uvl = tb.loops.layers.uv.new("uv")
        c = [tb.verts.new(p) for p in ((-w / 2, 0, -h / 2), (w / 2, 0, -h / 2), (w / 2, 0, h / 2), (-w / 2, 0, h / 2))]
        f = tb.faces.new(c)
        for lp, uv in zip(f.loops, [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]):
            lp[uvl].uv = uv
        if double:
            g = tb.faces.new(list(reversed(c)))
            for lp, uv in zip(g.loops, [(u0, v1), (u1, v1), (u1, v0), (u0, v0)]):
                lp[uvl].uv = uv
        tb.normal_update()
        Mx = Mx if Mx is not None else trs(center, rot)
        return self.commit(tb, Mx, mat, None, uvoff=False)

    def label(self, name, center, w, h=None, rot=(0, 0, 0), mat="label_minekit", Mx=None):
        """Atlas decal; h defaults to w scaled by the atlas rect aspect."""
        if h is None:
            x, y, rw, rh = atlas()["rects"][name]
            h = w * rh / rw
        return self.quad(center, w, h, mat, rot=rot, rect=name, Mx=Mx)

    def clabel(self, name, Mx, r, theta=0.0, w=0.1, h=None, z=0.0, segs=8, mat="label_minekit"):
        """Atlas decal wrapped on a cylinder of radius r about local Z (Mx places the cylinder).
        theta (degrees) = decal centre angle measured from local -Y toward +X; z = decal centre height."""
        A = atlas()
        W, H = A["size"]
        x, y, rw, rh = A["rects"][name]
        if h is None:
            h = w * rh / rw
        u0, u1 = x / W, (x + rw) / W
        v0, v1 = 1 - (y + rh) / H, 1 - y / H
        tb = bmesh.new()
        uvl = tb.loops.layers.uv.new("uv")
        span = w / r
        t0 = theta * DEG - span / 2
        cols = []
        for k in range(segs + 1):
            a = t0 + span * k / segs
            px, py = math.sin(a) * r, -math.cos(a) * r
            cols.append((tb.verts.new((px, py, z - h / 2)), tb.verts.new((px, py, z + h / 2)), k / segs))
        for k in range(segs):
            (b0, t0_, s0), (b1, t1_, s1) = cols[k], cols[k + 1]
            f = tb.faces.new((b0, b1, t1_, t0_))
            for lp, uv in zip(f.loops, [(lerp(u0, u1, s0), v0), (lerp(u0, u1, s1), v0), (lerp(u0, u1, s1), v1),
                                        (lerp(u0, u1, s0), v1)]):
                lp[uvl].uv = uv
        bmesh.ops.recalc_face_normals(tb, faces=tb.faces[:])
        for f in tb.faces:  # outward
            c = f.calc_center_median()
            if f.normal.dot(Vector((c.x, c.y, 0))) < 0:
                f.normal_flip()
        tb.normal_update()
        return self.commit(tb, Mx, mat, None, uvoff=False)

    def rock(self, center, size, mat, seed=0, detail=1, rot=None, rough=0.22, squash=None):
        """Faceted broken rock: displaced icosphere, flat shaded, world box UVs."""
        rng = random.Random(seed)
        tb = bmesh.new()
        bmesh.ops.create_icosphere(tb, subdivisions=detail, radius=0.5)
        off = Vector((rng.uniform(-50, 50), rng.uniform(-50, 50), rng.uniform(-50, 50)))
        # random cut planes make blasted, angular faces
        planes = [Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1))).normalized() for _ in range(5)]
        for v in tb.verts:
            co = v.co.copy()
            k = 1.0 + rough * noise.noise(co * 2.2 + off) + 0.5 * rough * noise.noise(co * 5.0 + off)
            co *= k
            for pn in planes:
                d = co.dot(pn) - 0.36
                if d > 0:
                    co -= pn * d * 0.85
            v.co = Vector((co.x * size[0], co.y * size[1], co.z * size[2]))
        tb.normal_update()
        r = rot if rot is not None else (rng.uniform(0, 360), rng.uniform(0, 360), rng.uniform(0, 360))
        Mx = trs(center, r)
        for v in tb.verts:
            v.co = Mx @ v.co
        tb.normal_update()
        return self.commit(tb, Matrix.Identity(4), mat, uv_world_box, uvoff=True, flat=True)

    # ------------------------------------------------------------------ finish
    def tris(self):
        return sum(len(f.verts) - 2 for f in self.bm.faces)

    def finish(self, grime=True, wn=True, angle=48.0, name=None):
        name = name or self.name
        bm = self.bm
        bm.normal_update()
        thr = angle * DEG
        for e in bm.edges:
            lf = e.link_faces
            if len(lf) != 2:
                continue
            if lf[0][self.flat] or lf[1][self.flat] or lf[0].normal.angle(lf[1].normal, 0.0) > thr:
                e.smooth = False
        me = bpy.data.meshes.new(name + "_mesh")
        bm.to_mesh(me)
        bm.free()
        o = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(o)
        for m in self.mats:
            me.materials.append(m)
        if grime:
            ca = me.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
            me.color_attributes.active_color = ca
            me.color_attributes.render_color_index = 0
            for d in ca.data:
                d.color = (1, 1, 1, 1)
        if wn and len(me.polygons):
            mod = o.modifiers.new("WN", "WEIGHTED_NORMAL")
            mod.keep_sharp = True
            mod.weight = 50
            mod.mode = "FACE_AREA"
            with bpy.context.temp_override(object=o, active_object=o, selected_objects=[o],
                                           selected_editable_objects=[o]):
                bpy.ops.object.modifier_apply(modifier=mod.name)
        o["grime"] = bool(grime)
        return o


# ====================================================================== scene helpers

def empty(name, loc=(0, 0, 0), rot=(0, 0, 0), parent=None, size=0.1):
    o = bpy.data.objects.new(name, None)
    o.empty_display_type = "PLAIN_AXES"
    o.empty_display_size = size
    o.location = loc
    o.rotation_euler = [a * DEG for a in rot]
    bpy.context.scene.collection.objects.link(o)
    if parent is not None:
        o.parent = parent
    return o


def child(obj, parent, loc=(0, 0, 0), rot=(0, 0, 0)):
    obj.parent = parent
    obj.location = loc
    obj.rotation_euler = [a * DEG for a in rot]
    return obj


def descendants(o):
    out = []
    for c in o.children:
        out.append(c)
        out += descendants(c)
    return out


def tree_tris(o):
    n = 0
    for x in [o] + descendants(o):
        if x.type == "MESH":
            n += sum(len(p.vertices) - 2 for p in x.data.polygons)
    return n


def tree_bounds(o):
    pts = []
    for x in [o] + descendants(o):
        if x.type == "MESH":
            mw = x.matrix_world
            pts += [mw @ Vector(c) for c in x.bound_box]
    if not pts:
        return Vector((0, 0, 0)), Vector((0, 0, 0))
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


# ====================================================================== grime bake

def setup_cycles(samples=64):
    s = bpy.context.scene
    s.render.engine = "CYCLES"
    p = bpy.context.preferences.addons["cycles"].preferences
    p.compute_device_type = "CUDA"
    p.get_devices()
    for d in p.devices:
        d.use = d.type != "CPU"
    s.cycles.device = "GPU"
    s.cycles.samples = samples
    s.cycles.use_denoising = False
    if s.world is None:
        s.world = bpy.data.worlds.new("World")


def bake_ao(objs, distance=0.45, samples=96):
    """Cycles AO -> active colour attribute of every object in objs (in one bake call)."""
    setup_cycles(samples)
    s = bpy.context.scene
    s.world.light_settings.distance = distance
    s.render.bake.target = "VERTEX_COLORS"
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.bake(type="AO", target="VERTEX_COLORS")


def grime_post(o, origin_z=0.0, floor=True, streaks=0.0, strength=1.0, seed=0, ao_floor=0.34, dirt=0.22):
    """AO in Col -> final grime: crevices dark, a dirty band near the floor, blotchy variation, streaks.
    Values are linear multipliers on albedo (1 = clean)."""
    me = o.data
    ca = me.color_attributes.get("Col")
    if ca is None:
        return
    mw = o.matrix_world
    off = Vector((seed * 1.37, seed * 0.71, seed * 2.13))
    for i, v in enumerate(me.vertices):
        ao = ca.data[i].color[0]
        p = mw @ v.co
        g = ao_floor + (1 - ao_floor) * (ao ** 1.15)
        if floor:
            hz = p.z - origin_z
            g *= 1.0 - dirt * (1.0 - smoothstep(0.0, 0.55, hz))
        nb = noise.noise(p * 1.6 + off)
        g *= 1.0 - 0.13 * max(0.0, nb) - 0.05 * max(0.0, noise.noise(p * 5.0 + off))
        if streaks:
            sx = noise.noise(Vector((p.x * 9.0, p.y * 9.0, p.z * 0.6)) + off)
            g *= 1.0 - streaks * max(0.0, sx) * smoothstep(0.0, 1.2, p.z - origin_z)
        g = 1.0 - (1.0 - g) * strength
        g = max(0.18, min(1.0, g))
        ca.data[i].color = (g, g, g, 1.0)


# ====================================================================== export

def export_glb(path, roots):
    """Export roots + descendants as GLB (meshopt, Y-up, COLOR_0 from the active colour layer)."""
    objs = []
    for r in roots:
        objs += [r] + descendants(r)
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.hide_set(False)
        o.hide_render = False
        o.select_set(True)
    bpy.context.view_layer.objects.active = roots[0]
    bpy.ops.export_scene.gltf(
        filepath=path, export_format="GLB", use_selection=True, export_apply=True, export_yup=True,
        export_animations=False, export_meshopt_compression_enable=True, export_vertex_color="ACTIVE",
        export_all_vertex_colors=False, export_active_vertex_color_when_no_material=True,
        export_image_format="AUTO", export_texcoords=True, export_normals=True, export_extras=False,
        export_cameras=False, export_lights=False)
    return path


def patch_glb_names(path, fix):
    """Rename glTF nodes in place (Blender can't have duplicate object names: bulb.001 -> bulb)."""
    data = open(path, "rb").read()
    magic, ver, total = struct.unpack("<III", data[:12])
    jlen, jtype = struct.unpack("<II", data[12:20])
    js = json.loads(data[20:20 + jlen].decode())
    rest = data[20 + jlen:]
    changed = 0
    for n in js.get("nodes", []):
        nm = n.get("name", "")
        new = fix(nm)
        if new != nm:
            n["name"] = new
            changed += 1
    jb = json.dumps(js, separators=(",", ":")).encode()
    jb += b" " * ((4 - len(jb) % 4) % 4)
    out = struct.pack("<III", magic, ver, 12 + 8 + len(jb) + len(rest)) + struct.pack("<II", len(jb), jtype) + jb + rest
    open(path, "wb").write(out)
    return changed, js
