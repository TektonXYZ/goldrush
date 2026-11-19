"""kit.py: build helpers for MOTHERLODE's claim kit + nature (Blender 5.2 headless via `bl`).

Adapted from How to Trench's MB bmesh builder (copied, not imported) and extended for the photoreal pipeline in
docs/CONTRACTS.md:
  * every face gets a LIBRARY material by name (rock, wood_timber, corrugated, ...) or a custom_/label_ material
  * UV0 in METRES for library materials (local box projection with U along a part's long axis = wood grain,
    cylindrical for round parts, world box projection for rock/terrain); explicit 0-1 UVs for sign faces/cards
  * a per-part "shade" (plank-to-plank variation) is multiplied with a Cycles AO bake into COLOR_0 (grime)
  * bevels (bmesh) + weighted normals on man-made parts; rock keeps crisp fracture edges
  * one GLB with every asset as a separate named root node at the origin (meshopt, Y-up)
"""
import math
import os
import random

import bmesh
import bpy
import numpy as np
from mathutils import Euler, Matrix, Vector, noise

import bk

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.abspath(os.path.join(HERE, "..", ".."))
TEX = os.path.join(HERE, "tex")
PREV = os.path.join(HERE, "previews")
MODELS = os.path.join(PROJECT, "public", "models")

# ---------------------------------------------------------------- library materials (exact names, CONTRACTS.md)
# preview PBR values only: the game swaps these for photoscanned sets by name.
LIB = {
    "rock": ("#7f7a72", 0.92, 0.0), "rock_dark": ("#3a3632", 0.9, 0.0), "rock_red": ("#8a5a44", 0.9, 0.0),
    "rock_pale": ("#b3ada3", 0.9, 0.0), "gravel": ("#8a8378", 0.95, 0.0), "dirt": ("#74604a", 0.97, 0.0),
    "coal_ore": ("#161618", 0.3, 0.0), "iron_ore": ("#6e3b2a", 0.8, 0.1), "gold_ore": ("#9a8150", 0.6, 0.3),
    "wood_timber": ("#6c5642", 0.86, 0.0), "wood_planks": ("#857563", 0.88, 0.0), "wood_dark": ("#4c3826", 0.85, 0.0),
    "wood_painted_white": ("#d6d0c1", 0.7, 0.0), "wood_painted_red": ("#8b2f24", 0.7, 0.0),
    "wood_painted_green": ("#3d5638", 0.7, 0.0),
    "corrugated": ("#a3a6a7", 0.42, 0.85), "rust": ("#7a4527", 0.82, 0.35), "steel": ("#8f9194", 0.38, 1.0),
    "steel_dark": ("#3c3d3f", 0.5, 0.85), "galvanized": ("#b0b4b6", 0.33, 0.9), "cast_iron": ("#3d3b39", 0.7, 0.8),
    "chrome": ("#d8dadc", 0.12, 1.0), "copper": ("#b06a43", 0.4, 1.0), "brass": ("#b08d4a", 0.35, 1.0),
    "aluminium": ("#c4c7ca", 0.35, 1.0),
    "brick": ("#8c4a35", 0.88, 0.0), "concrete": ("#a19c92", 0.9, 0.0), "roof_shingle": ("#5b4a3e", 0.9, 0.0),
    "canvas": ("#b7a98b", 0.9, 0.0), "glass": ("#a9bcc4", 0.05, 0.0), "glass_dark": ("#1f2529", 0.08, 0.0),
    "paint_yellow": ("#e8b400", 0.5, 0.25), "paint_orange": ("#d8601c", 0.5, 0.25), "paint_red": ("#9c2a20", 0.5, 0.25),
    "paint_white": ("#e3e1d9", 0.5, 0.2), "paint_black": ("#1d1d1d", 0.5, 0.25), "paint_green": ("#2f5a3a", 0.5, 0.25),
    "paint_blue": ("#2b4f86", 0.5, 0.25), "paint_grey": ("#6f7377", 0.5, 0.25),
    "rubber": ("#1b1b1b", 0.8, 0.0), "cable": ("#151515", 0.6, 0.0), "hose_red": ("#9a2020", 0.6, 0.0),
    "plastic_black": ("#151515", 0.45, 0.0), "plastic_yellow": ("#e0ad10", 0.45, 0.0),
    "helmet_yellow": ("#e8b400", 0.35, 0.0), "helmet_white": ("#e8e6e0", 0.35, 0.0), "leather": ("#5a3b25", 0.7, 0.0),
    "emit_warm": ("#ffd9a8", 0.4, 0.0), "emit_amber": ("#ffb347", 0.4, 0.0), "emit_white": ("#f4f6ff", 0.4, 0.0),
    "emit_red": ("#ff4030", 0.4, 0.0), "emit_green": ("#40ff60", 0.4, 0.0),
    "sign_face": ("#d9cfb8", 0.85, 0.0),
}
EMIT = {"emit_warm": ("#ffb35a", 9.0), "emit_amber": ("#ff9a26", 8.0), "emit_white": ("#e8eeff", 8.0),
        "emit_red": ("#ff2a1a", 6.0), "emit_green": ("#30ff50", 6.0)}


def _boards(tile, seams_px, res=1024, margin=0.018):
    """(centre m, usable half width m) of each board in a board texture whose joints are at the given pixel columns."""
    s = sorted(seams_px) + [sorted(seams_px)[0] + res]
    return [((a + b) / 2 / res * tile, max(0.02, (b - a) / 2 / res * tile - margin)) for a, b in zip(s, s[1:])]


# The game's planks (2 m tile) and painted_wood (1.6 m tile) textures are rows of boards running along V; joints
# measured from public/textures/*/albedo.webp (column minima). Used by MB._uv_plank.
_PLANKS = _boards(2.0, [62, 172, 287, 403, 516, 631, 746, 861, 973])
_PAINTED = _boards(1.6, [1, 75, 147, 219, 291, 362, 437, 513, 587, 661, 734, 806, 881, 952])
PLANK_BOARDS = {"wood_planks": _PLANKS, "wood_painted_white": _PAINTED, "wood_painted_red": _PAINTED,
                "wood_painted_green": _PAINTED}
SINGLE = 0.45  # a face narrower than this (across the grain) is one board


def MAT(name):
    m = bpy.data.materials.get(name)
    if m is not None:
        return m
    if name.startswith("label_") and os.path.exists(os.path.join(TEX, name + ".png")):
        return custom_mat(name, name + ".png", rough=0.82)
    if name not in LIB:
        raise KeyError(f"material {name} is neither a library name nor a created custom_/label_ material")
    col, rough, metal = LIB[name]
    m = bk.mat(name, col, rough=rough, metal=metal)
    m.use_backface_culling = name not in ("glass", "glass_dark")
    p = m.node_tree.nodes["Principled BSDF"]
    if name in EMIT:
        p.inputs["Emission Color"].default_value = bk.hex_lin(EMIT[name][0])
        p.inputs["Emission Strength"].default_value = EMIT[name][1]
    if name == "glass":
        p.inputs["Alpha"].default_value = 0.28
        m.surface_render_method = "BLENDED"
    return m


def image(path, non_color=False):
    img = bpy.data.images.load(path, check_existing=True)
    if non_color:
        img.colorspace_settings.name = "Non-Color"
    return img


def custom_mat(name, albedo, normal=None, alpha=False, cutoff=0.45, rough=0.85, double=False, nstrength=1.0, spec=0.35):
    """custom_*/label_* material with embedded textures. alpha=True -> glTF alphaMode MASK (Math GREATER_THAN)."""
    assert name.startswith(("custom_", "label_")), name
    m = bpy.data.materials.get(name)
    if m is not None:
        return m
    m = bk.mat(name, "#ffffff", rough=rough)
    nt = m.node_tree
    p = nt.nodes["Principled BSDF"]
    p.inputs["Specular IOR Level"].default_value = spec
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = image(os.path.join(TEX, albedo))
    nt.links.new(tex.outputs["Color"], p.inputs["Base Color"])
    if alpha:
        gt = nt.nodes.new("ShaderNodeMath")
        gt.operation = "GREATER_THAN"
        gt.inputs[1].default_value = cutoff
        nt.links.new(tex.outputs["Alpha"], gt.inputs[0])
        nt.links.new(gt.outputs[0], p.inputs["Alpha"])
        m.surface_render_method = "DITHERED"
    if normal:
        nx = nt.nodes.new("ShaderNodeTexImage")
        nx.image = image(os.path.join(TEX, normal), non_color=True)
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nm.inputs["Strength"].default_value = nstrength
        nt.links.new(nx.outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], p.inputs["Normal"])
    m.use_backface_culling = not double
    m["_custom"] = True
    return m


# ---------------------------------------------------------------- small math helpers
def R(rot):
    return Euler([math.radians(a) for a in rot], "XYZ").to_matrix().to_4x4()


def T(loc):
    return Matrix.Translation(Vector(loc))


def frame(a, b, up=(0, 0, 1)):
    """Matrix whose local Z runs a->b, local X horizontal-ish (perpendicular to `up`)."""
    a, b = Vector(a), Vector(b)
    z = (b - a).normalized()
    u = Vector(up)
    if abs(z.dot(u)) > 0.98:
        u = Vector((0, 1, 0)) if abs(z.y) < 0.9 else Vector((1, 0, 0))
    x = u.cross(z).normalized()
    y = z.cross(x).normalized()
    m = Matrix((x, y, z)).transposed().to_4x4()
    m.translation = a
    return m


def fbm3(p, octaves=4, seed=0.0):
    t, amp, f, nrm = 0.0, 1.0, 1.0, 0.0
    for _ in range(octaves):
        t += amp * noise.noise(Vector((p[0] * f + seed, p[1] * f - seed * 0.7, p[2] * f + seed * 1.3)))
        nrm += amp
        amp *= 0.5
        f *= 2.03
    return t / nrm


def smoothstep(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def sag(a, b, n=10, drop=0.1):
    a, b = Vector(a), Vector(b)
    return [tuple(a.lerp(b, i / n) - Vector((0, 0, math.sin(i / n * math.pi) * drop))) for i in range(n + 1)]


# ---------------------------------------------------------------- the builder
class MB:
    """Append primitives into one bmesh: material slot by name, UV0 (metres or explicit), per-corner shade."""

    def __init__(self, name, seed=1):
        self.name = name
        self.bm = bmesh.new()
        self.uv = self.bm.loops.layers.uv.new("UVMap")
        self.col = self.bm.loops.layers.float_color.new("Col")
        self.ng = self.bm.faces.layers.int.new("nogrime")
        self.mats = []
        self.rng = random.Random(seed)

    # ---- internals
    def _mi(self, mat):
        if mat not in self.mats:
            self.mats.append(mat)
        return self.mats.index(mat)

    @staticmethod
    def _faces(verts):
        seen, out = set(), []
        for v in verts:
            for f in v.link_faces:
                if f not in seen:
                    seen.add(f)
                    out.append(f)
        return out

    def _off(self, on):
        return (self.rng.uniform(0, 4), self.rng.uniform(0, 4)) if on else (0.0, 0.0)

    def _uv_box(self, faces, size, grain, uvoff, scale=1.0):
        g = grain if grain is not None else max(range(3), key=lambda i: size[i])
        ou, ov = self._off(uvoff)
        for f in faces:
            n = f.normal
            k = max(range(3), key=lambda i: abs(n[i]))
            a, b = [i for i in range(3) if i != k]
            if b == g:
                a, b = b, a
            for lp in f.loops:
                co = lp.vert.co
                lp[self.uv].uv = (co[a] * scale + ou, co[b] * scale + ov)

    def _uv_world(self, faces, uvoff, scale=1.0):
        ou, ov = self._off(uvoff)
        for f in faces:
            n = f.normal
            k = max(range(3), key=lambda i: abs(n[i]))
            a, b = [i for i in range(3) if i != k]
            for lp in f.loops:
                co = lp.vert.co
                lp[self.uv].uv = (co[a] * scale + ou, co[b] * scale + ov)

    def _uv_cyl(self, faces, uvoff, axis_len=None):
        ou, ov = self._off(uvoff)
        for f in faces:
            n = f.normal
            if abs(n.z) > 0.7:
                for lp in f.loops:
                    lp[self.uv].uv = (lp.vert.co.x + ou, lp.vert.co.y + ov)
                continue
            angs = [math.atan2(lp.vert.co.y, lp.vert.co.x) for lp in f.loops]
            if max(angs) - min(angs) > math.pi:
                angs = [a + 2 * math.pi if a < 0 else a for a in angs]
            for lp, a in zip(f.loops, angs):
                rr = math.hypot(lp.vert.co.x, lp.vert.co.y)
                lp[self.uv].uv = (lp.vert.co.z + ou, a * rr + ov)

    def _paint(self, faces, mat, shade, var, nogrime):
        mi = self._mi(mat)
        s = shade
        if var and not callable(shade):
            s = shade * (1.0 - self.rng.uniform(0, var))
        for f in faces:
            f.material_index = mi
            f[self.ng] = 1 if nogrime else 0
            for lp in f.loops:
                val = s(lp.vert.co) if callable(s) else s
                lp[self.col] = (val, val, val, 1.0)
        return faces

    # ---- primitives
    def cuboid(self, lo, hi, mat, M=None, bevel=0.0, seg=2, uv="local", grain=None, shade=1.0, var=0.0,
               nogrime=False, uvoff=True, uvscale=1.0):
        """Box from local corner lo to hi, then transformed by M. Returns its faces."""
        lo, hi = Vector(lo), Vector(hi)
        size = hi - lo
        S = T((lo + hi) / 2) @ Matrix.Diagonal((size.x, size.y, size.z, 1.0))
        verts = bmesh.ops.create_cube(self.bm, size=1.0, matrix=S)["verts"]
        faces = self._faces(verts)
        if bevel > 0:
            w = min(bevel, 0.45 * min(size))
            edges = list({e for v in verts for e in v.link_edges})
            res = bmesh.ops.bevel(self.bm, geom=edges, offset=w, offset_type="OFFSET", segments=seg, profile=0.5,
                                  affect="EDGES", clamp_overlap=True)
            faces = self._faces([v for v in verts if v.is_valid] + [v for v in res["verts"] if v.is_valid])
            verts = list({v for f in faces for v in f.verts})
        for f in faces:
            f.normal_update()
        if uv == "local":
            if mat in PLANK_BOARDS:
                self._uv_plank(faces, lo, size, grain, PLANK_BOARDS[mat], uvoff)
            else:
                self._uv_box(faces, size, grain, uvoff, uvscale)
        if M is not None:
            bmesh.ops.transform(self.bm, matrix=M, verts=verts)
        for f in faces:
            f.normal_update()
        if uv == "world":
            self._uv_world(faces, uvoff, uvscale)
        return self._paint(faces, mat, shade, var, nogrime)

    def _uv_plank(self, faces, lo, size, grain, boards, uvoff):
        """Board-texture UVs (library planks / painted_wood: the boards run along V). V runs along the grain; a part
        narrower than SINGLE gets exactly one texture board across it (no texture joint inside a real plank), a wider
        face (a deck or sheathing in one piece) shows the texture's boards at their true metre size."""
        g = grain if grain is not None else max(range(3), key=lambda i: size[i])
        cm, hw = boards[self.rng.randrange(len(boards))]
        ou, ov = self._off(uvoff)
        for f in faces:
            n = f.normal
            k = max(range(3), key=lambda i: abs(n[i]))
            if k == g:  # end grain
                a, b = [i for i in range(3) if i != k]
                for lp in f.loops:
                    co = lp.vert.co
                    lp[self.uv].uv = (co[a] + ou, co[b] + ov)
                continue
            c = 3 - k - g
            w = size[c]
            for lp in f.loops:
                co = lp.vert.co
                if w <= SINGLE:
                    s = (co[c] - lo[c]) / w if w > 1e-6 else 0.5
                    u = cm + (s - 0.5) * min(w, 2 * hw)
                else:
                    u = co[c] + ou
                lp[self.uv].uv = (u, co[g] + ov)

    def box(self, size, mat, loc=(0, 0, 0), rot=(0, 0, 0), **kw):
        """Box sized in metres resting ON loc (bottom centre), rotated about loc (degrees XYZ)."""
        sx, sy, sz = size
        return self.cuboid((-sx / 2, -sy / 2, 0), (sx / 2, sy / 2, sz), mat, T(loc) @ R(rot), **kw)

    def cbox(self, size, mat, loc=(0, 0, 0), rot=(0, 0, 0), **kw):
        """Box centred on loc."""
        sx, sy, sz = size
        return self.cuboid((-sx / 2, -sy / 2, -sz / 2), (sx / 2, sy / 2, sz / 2), mat, T(loc) @ R(rot), **kw)

    def beam(self, a, b, w, h, mat, up=(0, 0, 1), roll=0.0, ext=0.0, **kw):
        """Timber/steel member from a to b (centre line), cross-section w (perp. to `up`) x h. ext lengthens both ends."""
        a, b = Vector(a), Vector(b)
        d = (b - a).normalized()
        a, b = a - d * ext, b + d * ext
        L = (b - a).length
        M = frame(a, b, up) @ Matrix.Rotation(math.radians(roll), 4, "Z")
        return self.cuboid((-w / 2, -h / 2, 0), (w / 2, h / 2, L), mat, M, grain=2, **kw)

    def angle_iron(self, a, b, leg, t, mat, up=(0, 0, 1), roll=0.0, **kw):
        """L-section steel member from a to b (two thin plates)."""
        a, b = Vector(a), Vector(b)
        L = (b - a).length
        M = frame(a, b, up) @ Matrix.Rotation(math.radians(roll), 4, "Z")
        f1 = self.cuboid((-leg / 2, -leg / 2, 0), (leg / 2, -leg / 2 + t, L), mat, M, grain=2, **kw)
        f2 = self.cuboid((-leg / 2, -leg / 2 + t, 0), (-leg / 2 + t, leg / 2, L), mat, M, grain=2, **kw)
        return f1 + f2

    def cylinder(self, r, h, mat, M=None, sides=12, r2=None, cap=True, uv="cyl", shade=1.0, var=0.0, nogrime=False,
                 uvoff=True, bevel=0.0, seg=1):
        """Cylinder/frustum along local Z from 0 to h, then transformed by M."""
        verts = bmesh.ops.create_cone(self.bm, cap_ends=cap, cap_tris=False, segments=sides, radius1=r,
                                      radius2=r if r2 is None else r2, depth=h,
                                      matrix=T((0, 0, h / 2)))["verts"]
        faces = self._faces(verts)
        if bevel > 0 and cap:
            edges = [e for e in {e for v in verts for e in v.link_edges} if len(e.link_faces) == 2 and
                     abs(e.link_faces[0].normal.z - e.link_faces[1].normal.z) > 0.5]
            res = bmesh.ops.bevel(self.bm, geom=edges, offset=min(bevel, r * 0.4), offset_type="OFFSET", segments=seg,
                                  profile=0.5, affect="EDGES", clamp_overlap=True)
            faces = self._faces([v for v in verts if v.is_valid] + [v for v in res["verts"] if v.is_valid])
            verts = list({v for f in faces for v in f.verts})
        for f in faces:
            f.normal_update()
        if uv == "cyl":
            self._uv_cyl(faces, uvoff)
        elif uv == "local":
            self._uv_box(faces, (r, r, h), 2, uvoff)
        if M is not None:
            bmesh.ops.transform(self.bm, matrix=M, verts=verts)
        for f in faces:
            f.normal_update()
        if uv == "world":
            self._uv_world(faces, uvoff)
        return self._paint(faces, mat, shade, var, nogrime)

    def cyl(self, r, h, mat, loc=(0, 0, 0), rot=(0, 0, 0), **kw):
        """Cylinder resting ON loc (axis Z, then rotated about loc)."""
        return self.cylinder(r, h, mat, T(loc) @ R(rot), **kw)

    def rod(self, a, b, r, mat, sides=8, r2=None, up=(0, 0, 1), **kw):
        a, b = Vector(a), Vector(b)
        return self.cylinder(r, (b - a).length, mat, frame(a, b, up), sides=sides, r2=r2, **kw)

    def tube(self, pts, r, mat, sides=6, shade=1.0, nogrime=False, cap=False, radii=None):
        """Tube through world points; u along the length (m), v around."""
        pts = [Vector(p) for p in pts]
        rings, cum = [], [0.0]
        for i in range(1, len(pts)):
            cum.append(cum[-1] + (pts[i] - pts[i - 1]).length)
        prev_x = None
        for i, p in enumerate(pts):
            d = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
            up = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
            x = up.cross(d).normalized() if prev_x is None else (prev_x - d * prev_x.dot(d)).normalized()
            y = d.cross(x).normalized()
            prev_x = x
            rr = radii[i] if radii else r
            rings.append([self.bm.verts.new(p + (x * math.cos(k / sides * math.tau) + y * math.sin(k / sides * math.tau)) * rr)
                          for k in range(sides)])
        faces = []
        for i in range(len(rings) - 1):
            for k in range(sides):
                k2 = (k + 1) % sides
                f = self.bm.faces.new((rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]))
                f.normal_update()
                for lp, (s_, kk) in zip(f.loops, ((cum[i], k), (cum[i], k + 1), (cum[i + 1], k + 1), (cum[i + 1], k))):
                    lp[self.uv].uv = (s_, kk / sides * math.tau * r)
                faces.append(f)
        if cap:
            for ring in (rings[0], rings[-1][::-1]):
                f = self.bm.faces.new(ring[::-1])
                f.normal_update()
                for lp in f.loops:
                    lp[self.uv].uv = (lp.vert.co.x, lp.vert.co.y)
                faces.append(f)
        return self._paint(faces, mat, shade, 0, nogrime)

    def revolve(self, profile, mat, M=None, seg=24, closed=True, shade=1.0, var=0.0, nogrime=False):
        """Revolve a profile [(x, r), ...] around local X (closed loop if `closed`). u = arc length, v = profile."""
        rings = []
        for k in range(seg):
            a = k / seg * math.tau
            rings.append([self.bm.verts.new((x, r * math.cos(a), r * math.sin(a))) for x, r in profile])
        np_ = len(profile)
        cum = [0.0]
        for i in range(1, np_ + (1 if closed else 0)):
            p0, p1 = profile[i - 1], profile[i % np_]
            cum.append(cum[-1] + math.hypot(p1[0] - p0[0], p1[1] - p0[1]))
        faces = []
        rmax = max(r for _, r in profile)
        for k in range(seg):
            k2 = (k + 1) % seg
            for i in range(np_ if closed else np_ - 1):
                i2 = (i + 1) % np_
                f = self.bm.faces.new((rings[k][i], rings[k][i2], rings[k2][i2], rings[k2][i]))
                for lp, (kk, ii) in zip(f.loops, ((k, i), (k, i + 1), (k + 1, i + 1), (k + 1, i))):
                    lp[self.uv].uv = (kk / seg * math.tau * rmax, cum[min(ii, len(cum) - 1)])
                faces.append(f)
        verts = [v for r in rings for v in r]
        if M is not None:
            bmesh.ops.transform(self.bm, matrix=M, verts=verts)
        for f in faces:
            f.normal_update()
        return self._paint(faces, mat, shade, var, nogrime)

    def quad(self, pts, mat, uvs=((0, 0), (1, 0), (1, 1), (0, 1)), shade=1.0, nogrime=False, normals=None):
        vs = [self.bm.verts.new(Vector(p)) for p in pts]
        f = self.bm.faces.new(vs)
        f.normal_update()
        for lp, uv in zip(f.loops, uvs):
            lp[self.uv].uv = uv
        return self._paint([f], mat, shade, 0, nogrime)

    def poly(self, pts, mat, thick=0.0, uv="world", shade=1.0, nogrime=False, uvdir=None):
        vs = [self.bm.verts.new(Vector(p)) for p in pts]
        faces = [self.bm.faces.new(vs)]
        faces[0].normal_update()
        if thick:
            n = faces[0].normal * thick
            back = [self.bm.verts.new(Vector(p) - n) for p in pts]
            faces.append(self.bm.faces.new(list(reversed(back))))
            k = len(pts)
            for i in range(k):
                faces.append(self.bm.faces.new((vs[(i + 1) % k], vs[i], back[i], back[(i + 1) % k])))
        for f in faces:
            f.normal_update()
        if uvdir is not None:
            ua, va = Vector(uvdir[0]), Vector(uvdir[1])
            ou, ov = self._off(True)
            for f in faces:
                for lp in f.loops:
                    lp[self.uv].uv = (lp.vert.co.dot(ua) + ou, lp.vert.co.dot(va) + ov)
        else:
            self._uv_world(faces, True)
        return self._paint(faces, mat, shade, 0, nogrime)

    def mesh(self, verts, faces, mat, uv="world", shade=1.0, nogrime=False, uvs=None, mats=None, uvoff=True):
        """Raw geometry (world coords). mats: optional per-face material names. uvs: per-face lists of uv tuples."""
        vs = [self.bm.verts.new(Vector(p)) for p in verts]
        out = []
        for fi, idx in enumerate(faces):
            try:
                f = self.bm.faces.new([vs[i] for i in idx])
            except ValueError:
                continue
            f.normal_update()
            out.append((fi, f))
        fl = [f for _, f in out]
        if uvs is not None:
            for fi, f in out:
                for lp, uv in zip(f.loops, uvs[fi]):
                    lp[self.uv].uv = uv
        elif uv == "world":
            self._uv_world(fl, uvoff)
        if mats is None:
            return self._paint(fl, mat, shade, 0, nogrime)
        groups = {}
        for fi, f in out:
            groups.setdefault(mats[fi], []).append(f)
        for m, fs in groups.items():
            self._paint(fs, m, shade, 0, nogrime)
        return fl

    def chunk(self, loc, size, seed, mat="rock", detail=1, cuts=5, rot=None, shade=1.0, flat_bottom=True, rough=0.16):
        """Angular rock: icosphere with noise lumps and planar fracture cuts, scaled to `size` (x, y, z extents)."""
        rng = random.Random(seed)
        verts = bmesh.ops.create_icosphere(self.bm, subdivisions=detail, radius=1.0, matrix=Matrix.Identity(4))["verts"]
        planes = []
        for _ in range(cuts):
            n = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-0.4, 1))).normalized()
            planes.append((n, rng.uniform(0.5, 0.82)))
        sv = rng.uniform(0, 100)
        for v in verts:
            p = v.co.copy()
            p *= 1.0 + rough * fbm3(p * 1.6, 3, sv)
            for n, d in planes:
                t = p.dot(n) - d
                if t > 0:
                    p -= n * t
            if flat_bottom and p.z < -0.55:
                p.z = -0.55 - (p.z + 0.55) * 0.15
            v.co = Vector((p.x * size[0] / 2, p.y * size[1] / 2, p.z * size[2] / 2))
        yaw = rng.uniform(0, 360) if rot is None else rot[2]
        tilt = (rng.uniform(-8, 8), rng.uniform(-8, 8)) if rot is None else rot[:2]
        M = T(loc) @ R((tilt[0], tilt[1], yaw))
        bmesh.ops.transform(self.bm, matrix=M, verts=verts)
        faces = self._faces(verts)
        for f in faces:
            f.normal_update()
        self._uv_world(faces, True)
        return self._paint(faces, mat, shade, 0, False)

    def absorb(self, obj, delete=True):
        """Copy an object's mesh (world transform baked) with its UVMap / Col / nogrime / material names."""
        bpy.context.view_layer.update()
        me = obj.data
        M = obj.matrix_world.copy()
        uvl = me.uv_layers.get("UVMap") or (me.uv_layers[0] if me.uv_layers else None)
        col = me.color_attributes.get("Col")
        ng = me.attributes.get("nogrime")
        vmap = [self.bm.verts.new(M @ v.co) for v in me.vertices]
        out = []
        for p in me.polygons:
            try:
                f = self.bm.faces.new([vmap[i] for i in p.vertices])
            except ValueError:
                continue
            mat = me.materials[p.material_index].name if len(me.materials) else "rock"
            f.material_index = self._mi(mat)
            f[self.ng] = ng.data[p.index].value if ng is not None else 0
            for lp, li in zip(f.loops, p.loop_indices):
                lp[self.uv].uv = uvl.data[li].uv if uvl is not None else (0.0, 0.0)
                if col is not None and col.domain == "CORNER":
                    lp[self.col] = col.data[li].color
                elif col is not None:
                    lp[self.col] = col.data[p.vertices[list(p.loop_indices).index(li)]].color
                else:
                    lp[self.col] = (1.0, 1.0, 1.0, 1.0)
            f.normal_update()
            out.append(f)
        if delete:
            bpy.data.objects.remove(obj, do_unlink=True)
        return out

    def face_label(self, faces, mat, normal=(0, -1, 0), u_axis=(1, 0, 0), v_axis=(0, 0, 1), nogrime=True):
        """Turn the largest face pointing along `normal` into a 0-1 UV label face with material `mat`."""
        n = Vector(normal)
        cands = [f for f in faces if f.normal.dot(n) > 0.95]
        f = max(cands, key=lambda f: f.calc_area())
        ua, va = Vector(u_axis), Vector(v_axis)
        us = [lp.vert.co.dot(ua) for lp in f.loops]
        vs = [lp.vert.co.dot(va) for lp in f.loops]
        u0, u1, v0, v1 = min(us), max(us), min(vs), max(vs)
        for lp, u, v in zip(f.loops, us, vs):
            lp[self.uv].uv = ((u - u0) / (u1 - u0), (v - v0) / (v1 - v0))
        f.material_index = self._mi(mat)
        f[self.ng] = 1 if nogrime else 0
        return f

    def tris(self):
        return sum(len(f.verts) - 2 for f in self.bm.faces)

    # ---- finish
    def finish(self, name=None, smooth=50.0, weighted=True, parent=None, loc=None):
        """Bake into an object. smooth = max angle (deg) shaded smooth; sharper edges stay hard. 0 = flat."""
        name = name or self.name
        bm = self.bm
        bm.normal_update()
        thr = math.radians(smooth)
        for f in bm.faces:
            f.smooth = smooth > 0
        for e in bm.edges:
            e.smooth = len(e.link_faces) == 2 and e.calc_face_angle(math.pi) <= thr
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        o = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(o)
        for m in self.mats:
            me.materials.append(MAT(m))
        if weighted and smooth > 0:
            mod = o.modifiers.new("WN", "WEIGHTED_NORMAL")
            mod.keep_sharp = True
            mod.weight = 50
            mod.mode = "FACE_AREA"
            bk.select([o])
            bpy.ops.object.modifier_apply(modifier=mod.name)
        if "Col" in me.color_attributes:
            me.color_attributes.active_color = me.color_attributes["Col"]
        if parent is not None:
            attach(o, parent, loc)
        return o


# ---------------------------------------------------------------- scene graph helpers
def attach(child, parent, loc=None):
    """Parent with identity inverse; if loc is given the child's ORIGIN goes there (mesh stays put in world)."""
    if loc is not None:
        loc = Vector(loc)
        child.data.transform(T(-loc))
        child.location = loc
    child.parent = parent
    child.matrix_parent_inverse = Matrix.Identity(4)
    return child


def empty(name, loc, parent=None, rot=(0, 0, 0)):
    o = bpy.data.objects.new(name, None)
    o.empty_display_type = "PLAIN_AXES"
    o.empty_display_size = 0.3
    o.location = loc
    o.rotation_euler = [math.radians(a) for a in rot]
    bpy.context.scene.collection.objects.link(o)
    if parent is not None:
        o.parent = parent
        o.matrix_parent_inverse = Matrix.Identity(4)
    return o


def tree(root):
    return [root] + list(root.children_recursive)


def mesh_tris(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons) if o.type == "MESH" else 0


def node_tris(root):
    return sum(mesh_tris(o) for o in tree(root))


def node_size(root):
    pts = []
    for o in tree(root):
        if o.type == "MESH":
            pts += [o.matrix_world @ Vector(c) for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def spread(roots, spacing=45.0, cols=6):
    """Lay roots out on a grid (for isolated AO bakes + lineup previews)."""
    for i, r in enumerate(roots):
        r.location = ((i % cols) * spacing, (i // cols) * spacing, 0)
    bpy.context.view_layer.update()


def to_origin(roots):
    for r in roots:
        r.location = (0, 0, 0)
    bpy.context.view_layer.update()


# ---------------------------------------------------------------- grime: Cycles AO -> COLOR_0
def _gpu():
    s = bpy.context.scene
    s.render.engine = "CYCLES"
    p = bpy.context.preferences.addons["cycles"].preferences
    p.compute_device_type = "CUDA"
    p.get_devices()
    for d in p.devices:
        d.use = d.type != "CPU"
    s.cycles.device = "GPU"


def root_of(o):
    while o.parent is not None:
        o = o.parent
    return o


def bake_grime(objs, distance=1.2, samples=64, floor=0.32, gamma=1.0, ground=True, extras=None):
    """AO bake (Cycles, GPU) into each object's vertices, combined with the builder's per-part shade into the
    corner colour 'Col' (exported as COLOR_0). extras: {object name: fn(co Nx3, normal Nx3) -> factor}, with co
    in NODE-LOCAL metres (relative to the root's layout position)."""
    objs = [o for o in objs if o.type == "MESH" and "Col" in o.data.color_attributes]
    if not objs:
        return
    s = bpy.context.scene
    if s.world is None:
        s.world = bpy.data.worlds.new("World")
    _gpu()
    s.cycles.samples = samples
    s.world.light_settings.distance = distance
    g = None
    if ground:
        bpy.ops.mesh.primitive_plane_add(size=2000, location=(0, 0, -0.002))
        g = bpy.context.object
    for o in objs:
        me = o.data
        if "AO" in me.color_attributes:
            me.color_attributes.remove(me.color_attributes["AO"])
        a = me.color_attributes.new("AO", "FLOAT_COLOR", "POINT")
        me.color_attributes.active_color = a
    bk.select(objs)
    bpy.ops.object.bake(type="AO", target="VERTEX_COLORS")
    if g is not None:
        bpy.data.objects.remove(g, do_unlink=True)
    extras = extras or {}
    for o in objs:
        _combine(o, floor, gamma, extras.get(o.name) or extras.get("*"))


def _combine(o, floor, gamma, extra):
    me = o.data
    nl, nv = len(me.loops), len(me.vertices)
    ao = np.zeros(nv * 4, np.float32)
    me.color_attributes["AO"].data.foreach_get("color", ao)
    ao = ao.reshape(-1, 4)[:, 0]
    lv = np.zeros(nl, np.int32)
    me.loops.foreach_get("vertex_index", lv)
    col = me.color_attributes["Col"]
    c = np.zeros(nl * 4, np.float32)
    col.data.foreach_get("color", c)
    c = c.reshape(-1, 4)
    val = c[:, 0] * (floor + (1.0 - floor) * np.power(np.clip(ao[lv], 0, 1), gamma))
    if extra is not None:
        co = np.zeros(nv * 3, np.float32)
        me.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)
        Mw = np.array(o.matrix_world)
        cw = co @ Mw[:3, :3].T + Mw[:3, 3] - np.array(root_of(o).location)
        nrm = np.zeros(nl * 3, np.float32)
        me.corner_normals.foreach_get("vector", nrm)
        val = val * extra(cw[lv], nrm.reshape(-1, 3) @ Mw[:3, :3].T)
    if "nogrime" in me.attributes:
        ng = np.zeros(len(me.polygons), np.int32)
        me.attributes["nogrime"].data.foreach_get("value", ng)
        ls = np.zeros(len(me.polygons), np.int32)
        lt = np.zeros(len(me.polygons), np.int32)
        me.polygons.foreach_get("loop_start", ls)
        me.polygons.foreach_get("loop_total", lt)
        lng = np.repeat(ng, lt)
        val = np.where(lng > 0, 1.0, val)
    val = np.clip(val, 0.0, 1.0)
    c[:, 0] = c[:, 1] = c[:, 2] = val
    c[:, 3] = 1.0
    col.data.foreach_set("color", c.ravel())
    me.color_attributes.remove(me.color_attributes["AO"])
    me.color_attributes.active_color = me.color_attributes["Col"]
    me.color_attributes.render_color_index = me.color_attributes.find("Col")


def shade_by_angle(o, deg):
    """Smooth faces, hard edges above `deg` (for meshes that didn't go through MB.finish, e.g. boolean results)."""
    bm = bmesh.new()
    bm.from_mesh(o.data)
    thr = math.radians(deg)
    for f in bm.faces:
        f.smooth = deg > 0
    for e in bm.edges:
        e.smooth = len(e.link_faces) == 2 and e.calc_face_angle(math.pi) <= thr
    bm.to_mesh(o.data)
    bm.free()


def strip_color(o):
    """No grime on this mesh: drop COLOR_0 entirely (CONTRACTS: don't export white)."""
    me = o.data
    for name in [a.name for a in me.color_attributes]:
        me.color_attributes.remove(me.color_attributes[name])


def cleanup_attrs(objs):
    for o in objs:
        if o.type == "MESH" and "nogrime" in o.data.attributes:
            o.data.attributes.remove(o.data.attributes["nogrime"])


# ---------------------------------------------------------------- export
def export_glb(path, roots):
    objs = []
    for r in roots:
        objs += tree(r)
    cleanup_attrs(objs)
    bk.select(objs)
    path = bk._abs(path)
    bpy.ops.export_scene.gltf(
        filepath=path, export_format="GLB", use_selection=True, export_apply=True, export_yup=True,
        export_animations=False, export_vertex_color="ACTIVE", export_all_vertex_colors=False,
        export_active_vertex_color_when_no_material=False, export_meshopt_compression_enable=True,
        export_image_format="AUTO", export_extras=False, export_cameras=False, export_lights=False,
        export_texcoords=True, export_normals=True, export_tangents=False)
    print(f"[kit] exported {path} ({os.path.getsize(path) / 1024:.0f} KB)")
    return path


def save_blend(path):
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=bk._abs(path))


# ---------------------------------------------------------------- preview look (NOT exported: applied after export)
def _mix_mul(nt, a, b):
    m = nt.nodes.new("ShaderNodeMix")
    m.data_type = "RGBA"
    m.blend_type = "MULTIPLY"
    m.inputs["Factor"].default_value = 1.0
    nt.links.new(a, m.inputs[6])
    nt.links.new(b, m.inputs[7])
    return m.outputs[2]


def preview_materials():
    """Give library materials procedural detail + the COLOR_0 grime so EEVEE previews resemble the game."""
    for m in list(bpy.data.materials):
        if m.name not in LIB or m.get("_pv"):
            continue
        m["_pv"] = True
        nt = m.node_tree
        p = nt.nodes["Principled BSDF"]
        base = p.inputs["Base Color"].default_value[:]
        rgb = nt.nodes.new("ShaderNodeRGB")
        rgb.outputs[0].default_value = base
        tc = nt.nodes.new("ShaderNodeTexCoord")
        uv = tc.outputs["UV"]
        nm = m.name
        ca = nt.nodes.new("ShaderNodeVertexColor")
        ca.layer_name = "Col"
        col = rgb.outputs[0]
        bump_h = None
        bump_s = 0.25
        if nm.startswith("rock") or nm in ("gravel", "dirt", "concrete", "coal_ore", "iron_ore", "gold_ore"):
            n1 = nt.nodes.new("ShaderNodeTexNoise")
            n1.inputs["Scale"].default_value = 1.4 if nm.startswith("rock") else 3.0
            n1.inputs["Detail"].default_value = 8
            n1.inputs["Roughness"].default_value = 0.62
            nt.links.new(tc.outputs["Object"], n1.inputs["Vector"])
            vr = nt.nodes.new("ShaderNodeTexVoronoi")
            vr.feature = "DISTANCE_TO_EDGE"
            vr.inputs["Scale"].default_value = 2.2 if nm.startswith("rock") else 9.0
            nt.links.new(tc.outputs["Object"], vr.inputs["Vector"])
            ramp = nt.nodes.new("ShaderNodeValToRGB")
            ramp.color_ramp.elements[0].color = (0.62, 0.6, 0.58, 1)
            ramp.color_ramp.elements[1].color = (1.18, 1.14, 1.08, 1)
            nt.links.new(n1.outputs["Fac"], ramp.inputs["Fac"])
            col = _mix_mul(nt, col, ramp.outputs["Color"])
            mth = nt.nodes.new("ShaderNodeMath")
            mth.operation = "ADD"
            nt.links.new(n1.outputs["Fac"], mth.inputs[0])
            sm = nt.nodes.new("ShaderNodeMath")
            sm.operation = "MULTIPLY"
            sm.inputs[1].default_value = 0.6
            nt.links.new(vr.outputs["Distance"], sm.inputs[0])
            nt.links.new(sm.outputs[0], mth.inputs[1])
            bump_h, bump_s = mth.outputs[0], 0.5 if nm != "coal_ore" else 0.3
        elif nm.startswith("wood"):
            wv = nt.nodes.new("ShaderNodeTexNoise")
            wv.inputs["Scale"].default_value = 1.0
            wv.inputs["Detail"].default_value = 8
            wv.inputs["Roughness"].default_value = 0.7
            mp = nt.nodes.new("ShaderNodeMapping")
            mp.inputs["Scale"].default_value = (0.7, 16.0, 1.0)
            nt.links.new(uv, mp.inputs["Vector"])
            nt.links.new(mp.outputs["Vector"], wv.inputs["Vector"])
            ramp = nt.nodes.new("ShaderNodeValToRGB")
            ramp.color_ramp.elements[0].color = (0.72, 0.68, 0.64, 1)
            ramp.color_ramp.elements[1].color = (1.12, 1.08, 1.02, 1)
            nt.links.new(wv.outputs["Fac"], ramp.inputs["Fac"])
            col = _mix_mul(nt, col, ramp.outputs["Color"])
            bump_h, bump_s = wv.outputs["Fac"], 0.12
        elif nm in ("corrugated",):
            sep = nt.nodes.new("ShaderNodeSeparateXYZ")
            nt.links.new(uv, sep.inputs[0])
            mul = nt.nodes.new("ShaderNodeMath")
            mul.operation = "MULTIPLY"
            mul.inputs[1].default_value = 2 * math.pi / 0.076
            nt.links.new(sep.outputs["X"], mul.inputs[0])
            sn = nt.nodes.new("ShaderNodeMath")
            sn.operation = "SINE"
            nt.links.new(mul.outputs[0], sn.inputs[0])
            bump_h, bump_s = sn.outputs[0], 0.6
            n1 = nt.nodes.new("ShaderNodeTexNoise")
            n1.inputs["Scale"].default_value = 0.8
            nt.links.new(tc.outputs["Object"], n1.inputs["Vector"])
            ramp = nt.nodes.new("ShaderNodeValToRGB")
            ramp.color_ramp.elements[0].color = (0.75, 0.74, 0.72, 1)
            ramp.color_ramp.elements[1].color = (1.08, 1.06, 1.04, 1)
            nt.links.new(n1.outputs["Fac"], ramp.inputs["Fac"])
            col = _mix_mul(nt, col, ramp.outputs["Color"])
        elif nm == "brick":
            br = nt.nodes.new("ShaderNodeTexBrick")
            br.inputs["Scale"].default_value = 1.0
            br.inputs["Brick Width"].default_value = 0.23
            br.inputs["Row Height"].default_value = 0.075
            br.inputs["Mortar Size"].default_value = 0.01
            br.inputs["Color1"].default_value = (1.0, 1.0, 1.0, 1)
            br.inputs["Color2"].default_value = (0.8, 0.74, 0.7, 1)
            br.inputs["Mortar"].default_value = (1.6, 1.5, 1.35, 1)
            nt.links.new(uv, br.inputs["Vector"])
            col = _mix_mul(nt, col, br.outputs["Color"])
            bump_h, bump_s = br.outputs["Fac"], 0.3
        elif nm in ("rust", "steel", "steel_dark", "galvanized", "cast_iron") or nm.startswith("paint_"):
            n1 = nt.nodes.new("ShaderNodeTexNoise")
            n1.inputs["Scale"].default_value = 4.0
            n1.inputs["Detail"].default_value = 6
            nt.links.new(tc.outputs["Object"], n1.inputs["Vector"])
            ramp = nt.nodes.new("ShaderNodeValToRGB")
            lo = 0.6 if nm == "rust" else 0.85
            ramp.color_ramp.elements[0].color = (lo, lo * 0.97, lo * 0.94, 1)
            ramp.color_ramp.elements[1].color = (1.1, 1.08, 1.05, 1)
            nt.links.new(n1.outputs["Fac"], ramp.inputs["Fac"])
            col = _mix_mul(nt, col, ramp.outputs["Color"])
            bump_h, bump_s = n1.outputs["Fac"], 0.08
        if nm not in EMIT and nm != "glass":
            col = _mix_mul(nt, col, ca.outputs["Color"])
        nt.links.new(col, p.inputs["Base Color"])
        if bump_h is not None:
            bmp = nt.nodes.new("ShaderNodeBump")
            bmp.inputs["Strength"].default_value = bump_s
            bmp.inputs["Distance"].default_value = 0.02
            nt.links.new(bump_h, bmp.inputs["Height"])
            nt.links.new(bmp.outputs["Normal"], p.inputs["Normal"])
    # custom_/label_ materials also show COLOR_0 in-game (three.js multiplies vertex colours)
    for m in bpy.data.materials:
        if m.get("_custom") and not m.get("_pv"):
            m["_pv"] = True
            nt = m.node_tree
            p = nt.nodes["Principled BSDF"]
            link = p.inputs["Base Color"].links
            if link:
                ca = nt.nodes.new("ShaderNodeVertexColor")
                ca.layer_name = "Col"
                out = _mix_mul(nt, link[0].from_socket, ca.outputs["Color"])
                nt.links.new(out, p.inputs["Base Color"])


def preview_signs(pairs):
    """pairs: [(object, png)] -> a preview-only textured material on each sign face (checks UV orientation)."""
    for o, png in pairs:
        m = bpy.data.materials.new(f"_pv_{o.name}")
        p = m.node_tree.nodes["Principled BSDF"]
        t = m.node_tree.nodes.new("ShaderNodeTexImage")
        t.image = image(os.path.join(TEX, png))
        m.node_tree.links.new(t.outputs["Color"], p.inputs["Base Color"])
        p.inputs["Roughness"].default_value = 0.8
        o.data.materials.clear()
        o.data.materials.append(m)


# ---------------------------------------------------------------- golden-hour preview rig
def golden_rig(sun_elev=12.0, sun_az=-40.0, sun_power=4.5, sky_strength=0.32, exposure=0.0, ground="#6f604c",
               ground_size=600, look="AgX - Medium High Contrast"):
    s = bpy.context.scene
    for o in [o for o in s.objects if o.name.startswith("_pv_")]:
        bpy.data.objects.remove(o, do_unlink=True)
    w = s.world or bpy.data.worlds.new("World")
    s.world = w
    nt = w.node_tree
    nt.nodes.clear()
    sky = nt.nodes.new("ShaderNodeTexSky")
    sky.sky_type = "MULTIPLE_SCATTERING"
    sky.sun_disc = False
    sky.sun_elevation = math.radians(sun_elev)
    sky.sun_rotation = math.radians(sun_az + 180.0)
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = sky_strength
    out = nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(sky.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    ld = bpy.data.lights.new("_pv_sun", "SUN")
    ld.energy = sun_power
    ld.color = bk.hex_lin("#ffbe7a")[:3]
    ld.angle = math.radians(1.2)
    sun = bpy.data.objects.new("_pv_sun", ld)
    s.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(90 - sun_elev), 0, math.radians(sun_az))
    if ground:
        g = bpy.data.meshes.new("_pv_ground")
        h = ground_size / 2
        g.from_pydata([(-h, -h, 0), (h, -h, 0), (h, h, 0), (-h, h, 0)], [], [(0, 1, 2, 3)])
        go = bpy.data.objects.new("_pv_ground", g)
        s.collection.objects.link(go)
        gm = bpy.data.materials.get("_pv_ground_mat") or _ground_mat(ground)
        g.materials.append(gm)
    s.render.engine = "BLENDER_EEVEE"
    e = s.eevee
    e.taa_render_samples = 64
    e.use_shadows = True
    e.use_raytracing = True
    e.use_fast_gi = True
    try:
        e.shadow_resolution_scale = 1.0
        e.shadow_ray_count = 2
        e.shadow_step_count = 8
    except AttributeError:
        pass
    s.view_settings.view_transform = "AgX"
    try:
        s.view_settings.look = look
    except TypeError:
        pass
    s.view_settings.exposure = exposure


def _ground_mat(hexcol):
    m = bk.mat("_pv_ground_mat", hexcol, rough=0.95)
    nt = m.node_tree
    p = nt.nodes["Principled BSDF"]
    n1 = nt.nodes.new("ShaderNodeTexNoise")
    n1.inputs["Scale"].default_value = 0.35
    n1.inputs["Detail"].default_value = 10
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = bk.hex_lin("#5b4d3c")
    ramp.color_ramp.elements[1].color = bk.hex_lin("#8d7b62")
    nt.links.new(n1.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], p.inputs["Base Color"])
    bmp = nt.nodes.new("ShaderNodeBump")
    bmp.inputs["Strength"].default_value = 0.3
    n2 = nt.nodes.new("ShaderNodeTexNoise")
    n2.inputs["Scale"].default_value = 12
    nt.links.new(n2.outputs["Fac"], bmp.inputs["Height"])
    nt.links.new(bmp.outputs["Normal"], p.inputs["Normal"])
    return m


def camera(loc, target, lens=35.0):
    s = bpy.context.scene
    cam = s.objects.get("_pv_cam")
    if cam is None:
        cd = bpy.data.cameras.new("_pv_cam")
        cam = bpy.data.objects.new("_pv_cam", cd)
        s.collection.objects.link(cam)
    cam.data.lens = lens
    cam.data.clip_start = 0.05
    cam.data.clip_end = 3000
    cam.location = loc
    d = Vector(target) - Vector(loc)
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    s.camera = cam
    return cam


def render(path, res=(1600, 1000), samples=64):
    s = bpy.context.scene
    s.render.resolution_x, s.render.resolution_y = res
    s.render.resolution_percentage = 100
    s.eevee.taa_render_samples = samples
    s.render.image_settings.file_format = "PNG"
    s.render.filepath = bk._abs(path)
    bpy.ops.render.render(write_still=True)
    print(f"[kit] render {s.render.filepath}")
