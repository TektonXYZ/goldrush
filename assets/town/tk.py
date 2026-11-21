"""tk: the town toolkit. A fast bmesh builder with metric UVs, per-corner tone, per-part bevels and
library-named materials, plus grime baking (Cycles AO to vertex colours), export and preview staging.

Every primitive goes straight into ONE bmesh per object (bpy.ops primitives get slow with thousands
of parts). UVs are computed per primitive in its own frame: 1 UV unit = 1 metre, U runs along the
grain (longest axis) for wood and along the horizontal for everything else, V runs up / down-slope.

Conventions (docs/CONTRACTS.md): metres, Blender Z-up, fronts face -Y (= +Z in three.js), origins at
the ground centre of the footprint. Material names are the game's library names, label_* / custom_*
are kept as exported.
"""
import math
import os
import random
from contextlib import contextmanager

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, "tex")

# ------------------------------------------------------------------ materials

# preview look for each library name: (sRGB hex, roughness, metallic, kind)
# kind: "grain" (U along the longest axis) or "up" (U horizontal, V up)
LIB = {
    "wood_planks": ("#8c7b67", 0.86, 0.0, "plank"),
    "wood_dark": ("#4c3a2a", 0.72, 0.0, "grain"),
    "wood_timber": ("#80684e", 0.9, 0.0, "grain"),
    "wood_painted_white": ("#dcd6c8", 0.66, 0.0, "plank"),
    "wood_painted_red": ("#7a2c22", 0.66, 0.0, "plank"),
    "wood_painted_green": ("#2f4b38", 0.62, 0.0, "plank"),
    "corrugated": ("#8d9194", 0.5, 0.65, "up"),
    "roof_shingle": ("#5d4c40", 0.92, 0.0, "up"),
    "brick": ("#8f4b37", 0.86, 0.0, "up"),
    "concrete": ("#a19d95", 0.9, 0.0, "up"),
    "glass": ("#9fb4bf", 0.04, 0.0, "up"),
    "glass_dark": ("#161c22", 0.08, 0.3, "up"),
    "steel": ("#8e9297", 0.38, 1.0, "grain"),
    "steel_dark": ("#2e3033", 0.5, 0.9, "grain"),
    "cast_iron": ("#2b2b2c", 0.62, 0.8, "up"),
    "galvanized": ("#a0a6a9", 0.45, 0.9, "up"),
    "chrome": ("#d4d8dc", 0.08, 1.0, "grain"),
    "rust": ("#6f3c23", 0.9, 0.3, "up"),
    "copper": ("#b36c46", 0.35, 1.0, "up"),
    "brass": ("#b8913f", 0.3, 1.0, "up"),
    "gold": ("#e8b730", 0.2, 1.0, "up"),
    "aluminium": ("#c8ccd0", 0.35, 1.0, "up"),
    "paint_black": ("#1d1d1e", 0.42, 0.0, "up"),
    "paint_red": ("#8c1f17", 0.42, 0.0, "up"),
    "paint_green": ("#1f3f2c", 0.42, 0.0, "up"),
    "paint_white": ("#e5e2db", 0.48, 0.0, "up"),
    "paint_yellow": ("#e8b400", 0.45, 0.0, "up"),
    "paint_orange": ("#d8641c", 0.45, 0.0, "up"),
    "paint_blue": ("#1f4a7a", 0.45, 0.0, "up"),
    "paint_grey": ("#6b6e70", 0.5, 0.0, "up"),
    "rubber": ("#1a1a1a", 0.85, 0.0, "up"),
    "hose_red": ("#8a1a14", 0.6, 0.0, "up"),
    "cable": ("#121212", 0.6, 0.0, "up"),
    "plastic_black": ("#151515", 0.5, 0.0, "up"),
    "plastic_yellow": ("#e0b000", 0.5, 0.0, "up"),
    "canvas": ("#b9aa8a", 0.95, 0.0, "up"),
    "leather": ("#5a3b24", 0.7, 0.0, "up"),
    "gravel": ("#7b7368", 0.95, 0.0, "up"),
    "dirt": ("#7a5f45", 0.95, 0.0, "up"),
    "rock": ("#7e7b75", 0.9, 0.0, "up"),
    "rock_pale": ("#b6b0a5", 0.85, 0.0, "up"),
    "rock_dark": ("#403e3b", 0.9, 0.0, "up"),
    "coal_ore": ("#1b1a19", 0.6, 0.0, "up"),
    "sign_face": ("#2c2722", 0.8, 0.0, "up"),
}
EMIT = {  # name: (base, emission colour, strength)
    "emit_warm": ("#fff1d6", "#ffb45e", 6.0),
    "emit_white": ("#ffffff", "#f4f8ff", 6.0),
    "emit_red": ("#ff3020", "#ff2a14", 5.0),
    "emit_green": ("#30ff60", "#20ff50", 5.0),
    "emit_amber": ("#ffb020", "#ff9a10", 5.0),
    "emit_screen": ("#101418", "#9ac8ff", 2.0),
}

# Plank photo textures (src/core/materials.ts tiles them by real size, no rotation): their boards run along
# texture V, with the board joints at these U pixels (of 1024; measured from the albedo). kind "plank" maps the
# grain to V and fits a single board / trim piece across ONE texture board, so every board reads as one clean
# board instead of a strip of tiles. Wide surfaces keep the photo's own board pitch (or a given one).
PLANK_SETS = {
    "wood_planks": (2.0, (62, 172, 287, 403, 516, 631, 746, 861, 973)),
    "wood_painted_white": (1.6, (1, 75, 147, 219, 291, 362, 437, 513, 587, 661, 734, 806, 881, 952)),
}
PLANK_SETS["wood_painted_red"] = PLANK_SETS["wood_painted_white"]
PLANK_SETS["wood_painted_green"] = PLANK_SETS["wood_painted_white"]
FIT_MAX = 0.42      # boards / trim up to this wide get one texture board each
PING_MAX = 0.95     # round parts up to this circumference: one board wrapped round (no joint lines)


# painted_wood boards ordered by how much paint they still have (ORM.B bare-wood mask, least worn first): fitted
# painted boards pick from the better two thirds so trim reads painted and clapboards don't turn to camouflage
PAINT_GOOD = (5, 4, 3, 8, 9, 6, 7, 10, 2)


def plank_strip(mat, k, inset=0.14):
    """(a, b) in texture metres of texture board k, inset so the photo's joint line stays outside."""
    tile, seams = PLANK_SETS[mat]
    n = len(seams)
    if mat.startswith("wood_painted"):
        k = PAINT_GOOD[k % len(PAINT_GOOD)]
    k %= n
    a = seams[k]
    b = seams[(k + 1) % n] + (1024 if k + 1 == n else 0)
    a, b = a / 1024 * tile, b / 1024 * tile
    d = (b - a) * inset
    return a + d, b - d


def plank_pitch(mat):
    tile, seams = PLANK_SETS[mat]
    return tile / len(seams)


def plank_seam0(mat):
    tile, seams = PLANK_SETS[mat]
    return seams[0] / 1024 * tile


def hex_lin(h):
    h = h.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return (*out, 1.0)


def _principled(m):
    return m.node_tree.nodes.get("Principled BSDF")


def _vc_multiply(m, p, color):
    """Base colour = factor x COLOR_0 (the exporter recognises this and keeps baseColorFactor)."""
    nt = m.node_tree
    attr = nt.nodes.new("ShaderNodeVertexColor")
    attr.layer_name = "Color"
    attr.location = (-500, 300)
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    mix.location = (-250, 300)
    mix.inputs["Factor"].default_value = 1.0
    mix.inputs["A"].default_value = color
    nt.links.new(attr.outputs["Color"], mix.inputs["B"])
    nt.links.new(mix.outputs["Result"], p.inputs["Base Color"])
    m["_base"] = color


def mat(name):
    """Library material (or emit_*). Created once, preview-plausible, exported by name."""
    m = bpy.data.materials.get(name)
    if m is not None:
        return m
    m = bpy.data.materials.new(name)
    p = _principled(m)
    if name in EMIT:
        base, em, s = EMIT[name]
        p.inputs["Base Color"].default_value = hex_lin(base)
        p.inputs["Emission Color"].default_value = hex_lin(em)
        p.inputs["Emission Strength"].default_value = s
        p.inputs["Roughness"].default_value = 0.4
        m["_kind"] = "up"
        return m
    if name not in LIB:
        raise KeyError(f"not a library material: {name}")
    col, rough, metal, kind = LIB[name]
    c = hex_lin(col)
    m.diffuse_color = c
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    if name == "glass":
        p.inputs["Base Color"].default_value = c
        p.inputs["Alpha"].default_value = 0.28
        m.surface_render_method = "BLENDED"
    elif name == "sign_face":
        p.inputs["Base Color"].default_value = c
    else:
        _vc_multiply(m, p, c)
    m["_kind"] = kind
    return m


def label_mat(name, image_file, alpha=False, rough=0.75, emissive=0.0):
    """label_* / custom_* material with an embedded image (kept as exported by the game)."""
    assert name.startswith("label_") or name.startswith("custom_"), name
    m = bpy.data.materials.get(name)
    if m is not None:
        return m
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    p = _principled(m)
    path = os.path.join(TEX, image_file)
    img = bpy.data.images.load(path, check_existing=True)
    img.name = os.path.basename(image_file)
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.location = (-600, 200)
    tex.interpolation = "Linear"
    p.inputs["Roughness"].default_value = rough
    if emissive > 0:
        p.inputs["Base Color"].default_value = (0.02, 0.02, 0.02, 1)
        nt.links.new(tex.outputs["Color"], p.inputs["Emission Color"])
        p.inputs["Emission Strength"].default_value = emissive
    else:
        nt.links.new(tex.outputs["Color"], p.inputs["Base Color"])
    if alpha:
        rnd = nt.nodes.new("ShaderNodeMath")
        rnd.operation = "ROUND"
        rnd.location = (-250, -100)
        nt.links.new(tex.outputs["Alpha"], rnd.inputs[0])
        nt.links.new(rnd.outputs[0], p.inputs["Alpha"])
        m.surface_render_method = "DITHERED"
    m["_kind"] = "label"
    return m


def custom_mat(name, color, rough=0.5, metal=0.0, vc=True):
    """custom_* solid material (e.g. custom_bronze), optionally multiplied by COLOR_0."""
    assert name.startswith("custom_")
    m = bpy.data.materials.get(name)
    if m is not None:
        return m
    m = bpy.data.materials.new(name)
    p = _principled(m)
    c = hex_lin(color)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    if vc:
        _vc_multiply(m, p, c)
    else:
        p.inputs["Base Color"].default_value = c
    m["_kind"] = "up"
    return m


def kind_of(name):
    m = bpy.data.materials.get(name)
    if m is not None and "_kind" in m:
        return m["_kind"]
    if name in LIB:
        return LIB[name][3]
    return "up"


# ------------------------------------------------------------------ math helpers

def R(rot):
    """degrees XYZ euler -> 4x4"""
    return Euler([math.radians(a) for a in rot], "XYZ").to_matrix().to_4x4()


def T(loc):
    return Matrix.Translation(Vector(loc))


def lerp(a, b, t):
    return a + (b - a) * t


def smooth(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


Z = Vector((0, 0, 1))


# ------------------------------------------------------------------ builder

class MB:
    """One mesh object built from many primitives.

    mb = MB("land_office"); mb.box((w, d, h), "wood_planks", loc, rot); obj = mb.finish()
    `with mb.at(loc, rot):` nests a local frame (no scale: UVs stay metric).
    """

    def __init__(self, name, seed=1):
        self.name = name
        self.bm = bmesh.new()
        self.uv = self.bm.loops.layers.uv.new("UVMap")
        self.col = self.bm.loops.layers.float_color.new("Color")
        self.mats = []
        self.rng = random.Random(seed)
        self.M = Matrix.Identity(4)
        self._stack = []

    # -------------------------------------------------------------- frames
    @contextmanager
    def at(self, loc=(0, 0, 0), rot=(0, 0, 0), M=None):
        self._stack.append(self.M)
        self.M = self.M @ (M if M is not None else (T(loc) @ R(rot)))
        try:
            yield self
        finally:
            self.M = self._stack.pop()

    def mi(self, name):
        if name not in self.mats:
            self.mats.append(name)
        return self.mats.index(name)

    def tone(self, lo=0.86, hi=1.0):
        return self.rng.uniform(lo, hi)

    # -------------------------------------------------------------- internals
    def _paint(self, faces, mat, tone, smooth_=False):
        idx = self.mi(mat)
        c = (tone, tone, tone, 1.0)
        for f in faces:
            f.material_index = idx
            f.smooth = smooth_
            for lp in f.loops:
                lp[self.col] = c

    def _uv_axes(self, faces, axes, dims, mat, grain=None, off=(0.0, 0.0), centre=None, vfit=None, strip=None):
        """Planar metric UVs per face in the primitive's own axes (obj space unit vectors).
        axes: 3 obj-space vectors (local x, y, z); dims: sizes along them (for the grain rule).
        Plank materials: grain -> V, and a face narrower than FIT_MAX spans exactly one texture board."""
        kind = kind_of(mat)
        plank = kind == "plank" and mat in PLANK_SETS
        if plank:
            kb = self.rng.randrange(64) if strip is None else strip
            voff = self.rng.uniform(0.0, 3.0)
        for f in faces:
            n = f.normal
            d = [abs(n.dot(a)) for a in axes]
            k = d.index(max(d))
            ip = [i for i in range(3) if i != k]
            if plank:
                if grain is not None and grain in ip:
                    gi = grain
                else:
                    gi = ip[0] if dims[ip[0]] >= dims[ip[1]] else ip[1]
                ci = ip[1] if gi == ip[0] else ip[0]
                ga, ca = axes[gi], axes[ci]
                w = dims[ci]
                if centre is not None and 1e-4 < w <= FIT_MAX:
                    a, b = plank_strip(mat, kb)
                    c0 = centre.dot(ca)
                    g0, L = centre.dot(ga), max(1e-4, dims[gi])
                    for lp in f.loops:
                        p = lp.vert.co
                        t = min(1.0, max(0.0, (p.dot(ca) - c0) / w + 0.5))
                        if vfit is not None:
                            tv = min(1.0, max(0.0, (p.dot(ga) - g0) / L + 0.5))
                            vv = vfit[0] + (vfit[1] - vfit[0]) * tv
                        else:
                            vv = p.dot(ga) + voff
                        lp[self.uv].uv = (a + (b - a) * t, vv)
                else:
                    for lp in f.loops:
                        p = lp.vert.co
                        lp[self.uv].uv = (p.dot(ca) + off[0], p.dot(ga) + off[1] + voff)
                continue
            if grain is not None and grain in ip:
                ui = grain
            elif kind == "grain":
                ui = ip[0] if dims[ip[0]] >= dims[ip[1]] else ip[1]
            else:
                # U = the most horizontal in-plane axis; ties -> the longer
                z0, z1 = abs(axes[ip[0]].z), abs(axes[ip[1]].z)
                if abs(z0 - z1) < 1e-3:
                    ui = ip[0] if dims[ip[0]] >= dims[ip[1]] else ip[1]
                else:
                    ui = ip[0] if z0 < z1 else ip[1]
            vi = ip[1] if ui == ip[0] else ip[0]
            au, av = axes[ui], axes[vi]
            if av.z < -1e-4:
                av = -av
            for lp in f.loops:
                p = lp.vert.co
                lp[self.uv].uv = (p.dot(au) + off[0], p.dot(av) + off[1])

    def _bevel(self, verts, faces, width, segments):
        """Bevel a primitive's edges. Faces must already carry material + colour (rebuilt faces inherit
        them); returns every face of the primitive afterwards (rebuilt originals + new strips)."""
        edges = list({e for f in faces for e in f.edges})
        res = bmesh.ops.bevel(self.bm, geom=edges + list(verts), offset=width, offset_type="OFFSET",
                              segments=segments, profile=0.5, affect="EDGES", clamp_overlap=True,
                              loop_slide=True, harden_normals=False)
        newf = [f for f in res.get("faces", []) if f.is_valid]
        allf = {f for f in faces if f.is_valid} | set(newf)
        for f in list(allf):
            for v in f.verts:
                for g in v.link_faces:
                    allf.add(g)
        allf = [f for f in allf if f.is_valid]
        for f in allf:
            f.normal_update()
        return allf, newf

    def _off(self, uvoff):
        if uvoff is True:
            return (self.rng.uniform(0, 7), self.rng.uniform(0, 7))
        if uvoff:
            return uvoff
        return (0.0, 0.0)

    # -------------------------------------------------------------- primitives
    def box(self, size, mat, loc=(0, 0, 0), rot=(0, 0, 0), tone=1.0, bev=0.0, seg=1, skip="",
            grain=None, uvoff=False, centre=False, vfit=None, strip=None):
        """Box sized in metres resting ON loc (bottom centre; centre=True: centred on loc).
        skip: faces to omit, any of 'l r f k d u' (-x +x -y(front) +y(back) -z +z).
        grain: local axis index (0,1,2) the texture U follows (default: rule by material)."""
        sx, sy, sz = size
        L = self.M @ T(loc) @ R(rot) @ T((0, 0, 0 if centre else sz / 2))
        hx, hy, hz = sx / 2, sy / 2, sz / 2
        corners = [(-hx, -hy, -hz), (hx, -hy, -hz), (hx, hy, -hz), (-hx, hy, -hz),
                   (-hx, -hy, hz), (hx, -hy, hz), (hx, hy, hz), (-hx, hy, hz)]
        vs = [self.bm.verts.new(L @ Vector(c)) for c in corners]
        spec = {"d": (0, 3, 2, 1), "u": (4, 5, 6, 7), "f": (0, 1, 5, 4), "k": (2, 3, 7, 6),
                "l": (3, 0, 4, 7), "r": (1, 2, 6, 5)}
        faces = []
        for key, ids in spec.items():
            if key in skip:
                continue
            try:
                f = self.bm.faces.new([vs[i] for i in ids])
            except ValueError:
                continue
            f.normal_update()
            faces.append(f)
        used = [v for v in vs if v.link_faces]
        for v in vs:
            if not v.link_faces:
                self.bm.verts.remove(v)
        if bev and faces:
            self._paint(faces, mat, tone, smooth_=True)
            faces, _ = self._bevel(used, faces, bev, seg)
        Rm = L.to_3x3()
        axes = [(Rm @ Vector(a)).normalized() for a in ((1, 0, 0), (0, 1, 0), (0, 0, 1))]
        self._uv_axes(faces, axes, (sx, sy, sz), mat, grain, self._off(uvoff), centre=L.translation.copy(), vfit=vfit,
                      strip=strip)
        self._paint(faces, mat, tone, smooth_=bool(bev))
        return faces

    def boxc(self, size, mat, loc=(0, 0, 0), **kw):
        return self.box(size, mat, loc, centre=True, **kw)

    def span(self, a, b, w, h, mat, up=(0, 0, 1), tone=1.0, bev=0.0, seg=1, skip="", uvoff=False):
        """Beam of cross-section w x h from point a to point b (local frame); 'up' orients the h side."""
        a, b = Vector(a), Vector(b)
        d = b - a
        L = d.length
        if L < 1e-6:
            return []
        x = d / L
        upv = Vector(up)
        if abs(x.dot(upv.normalized())) > 0.99:
            upv = Vector((1, 0, 0)) if abs(x.x) < 0.9 else Vector((0, 1, 0))
        y = upv.cross(x).normalized()
        z = x.cross(y).normalized()
        M = Matrix((x, y, z)).transposed().to_4x4()
        M.translation = (a + b) / 2
        with self.at(M=M):
            return self.box((L, w, h), mat, centre=True, tone=tone, bev=bev, seg=seg, skip=skip, grain=0,
                            uvoff=uvoff)

    def cyl(self, r, h, mat, loc=(0, 0, 0), rot=(0, 0, 0), sides=12, r2=None, cap=True, cap_top=None,
            cap_bot=None, tone=1.0, smooth_=True, bev=0.0, seg=1, uvoff=False, centre=False):
        """Cylinder / frustum along local Z resting ON loc (centre=True: centred)."""
        r2 = r if r2 is None else r2
        L = self.M @ T(loc) @ R(rot) @ T((0, 0, -h / 2 if centre else 0))
        ct = cap if cap_top is None else cap_top
        cb = cap if cap_bot is None else cap_bot
        bot = [self.bm.verts.new(L @ Vector((r * math.cos(a), r * math.sin(a), 0)))
               for a in (i / sides * math.tau for i in range(sides))]
        top = [self.bm.verts.new(L @ Vector((r2 * math.cos(a), r2 * math.sin(a), h)))
               for a in (i / sides * math.tau for i in range(sides))]
        side = []
        for i in range(sides):
            j = (i + 1) % sides
            f = self.bm.faces.new((bot[i], bot[j], top[j], top[i]))
            f.normal_update()
            side.append(f)
        caps = []
        if cb:
            f = self.bm.faces.new(list(reversed(bot)))
            f.normal_update()
            caps.append(f)
        if ct:
            f = self.bm.faces.new(top)
            f.normal_update()
            caps.append(f)
        allf = side + caps
        if bev and caps:
            self._paint(allf, mat, tone, smooth_=smooth_)
            allf, _ = self._bevel(bot + top, allf, bev, seg)
        self._uv_cyl(allf, L, max(r, r2), mat, self._off(uvoff))
        self._paint(allf, mat, tone, smooth_=smooth_)
        for f in caps:
            if f.is_valid:
                f.smooth = False
        return allf

    def _uv_cyl(self, faces, L, r, mat, off):
        Li = L.inverted()
        Rm = L.to_3x3().normalized()
        ax = (Rm @ Vector((0, 0, 1))).normalized()
        grain = kind_of(mat) == "grain"
        if kind_of(mat) == "plank" and mat in PLANK_SETS:
            # grain along the axis (V); slim round parts wrap ONE texture board round (ping-pong, no seam)
            kb = self.rng.randrange(64)
            voff = self.rng.uniform(0.0, 3.0)
            sa, sb = plank_strip(mat, kb)
            ping = math.tau * r <= PING_MAX
            for f in faces:
                if abs(f.normal.dot(ax)) > 0.75:
                    ex = (Rm @ Vector((1, 0, 0))).normalized()
                    ey = (Rm @ Vector((0, 1, 0))).normalized()
                    for lp in f.loops:
                        p = lp.vert.co
                        lp[self.uv].uv = (p.dot(ex) + off[0], p.dot(ey) + off[1])
                    continue
                c = Li @ f.calc_center_median()
                ac = math.atan2(c.y, c.x)
                for lp in f.loops:
                    q = Li @ lp.vert.co
                    a = math.atan2(q.y, q.x)
                    if ping:
                        u = sa + (sb - sa) * abs(math.sin(a / 2))
                    else:
                        while a - ac > math.pi:
                            a -= math.tau
                        while a - ac < -math.pi:
                            a += math.tau
                        u = a * r + off[0]
                    lp[self.uv].uv = (u, q.z + voff)
            return
        for f in faces:
            if abs(f.normal.dot(ax)) > 0.75:
                ex = (Rm @ Vector((1, 0, 0))).normalized()
                ey = (Rm @ Vector((0, 1, 0))).normalized()
                for lp in f.loops:
                    p = lp.vert.co
                    lp[self.uv].uv = (p.dot(ex) + off[0], p.dot(ey) + off[1])
                continue
            c = Li @ f.calc_center_median()
            ac = math.atan2(c.y, c.x)
            for lp in f.loops:
                q = Li @ lp.vert.co
                a = math.atan2(q.y, q.x)
                while a - ac > math.pi:
                    a -= math.tau
                while a - ac < -math.pi:
                    a += math.tau
                u, v = a * r, q.z
                uu, vv = (v, u) if grain else (u, v)
                lp[self.uv].uv = (uu + off[0], vv + off[1])

    def lathe(self, prof, mat, loc=(0, 0, 0), rot=(0, 0, 0), sides=12, tone=1.0, cap_top=True, cap_bot=True,
              smooth_=True, sharp_rings=(), uvoff=False):
        """Surface of revolution about local Z. prof = [(r, z), ...] bottom to top."""
        L = self.M @ T(loc) @ R(rot)
        rings = []
        for r_, z_ in prof:
            rings.append([self.bm.verts.new(L @ Vector((r_ * math.cos(a), r_ * math.sin(a), z_)))
                          for a in (i / sides * math.tau for i in range(sides))])
        faces = []
        for k in range(len(rings) - 1):
            for i in range(sides):
                j = (i + 1) % sides
                try:
                    f = self.bm.faces.new((rings[k][i], rings[k][j], rings[k + 1][j], rings[k + 1][i]))
                except ValueError:
                    continue
                f.normal_update()
                faces.append(f)
        caps = []
        if cap_bot and prof[0][0] > 1e-4:
            f = self.bm.faces.new(list(reversed(rings[0])))
            f.normal_update()
            caps.append(f)
        if cap_top and prof[-1][0] > 1e-4:
            f = self.bm.faces.new(rings[-1])
            f.normal_update()
            caps.append(f)
        rmax = max(p[0] for p in prof)
        self._uv_cyl(faces + caps, L, rmax, mat, self._off(uvoff))
        self._paint(faces + caps, mat, tone, smooth_=smooth_)
        for f in caps:
            f.smooth = False
        return faces + caps

    def poly(self, pts, mat, thick=0.0, tone=1.0, grain_dir=None, uvoff=False, smooth_=False, facing=None, pitch=None,
             vfit=None, strip=None, voff=None):
        """Planar polygon (local frame points), optionally extruded `thick` along -normal (a slab).
        facing: local vector the front face must point along (vertex order is flipped if needed).
        pitch: (board width m, local anchor point) for plank materials on wide faces: the texture's boards are
        rescaled to that width with a joint on the anchor (board-and-batten: joints under the battens).
        vfit: (lo, hi) texture metres the face's along-grain extent maps onto (plank materials).
        strip: texture board index for fitted plank faces (default: random)."""
        L = self.M
        if facing is not None:
            P = [Vector(p) for p in pts]
            n = Vector()
            for i in range(len(P)):
                a, b = P[i], P[(i + 1) % len(P)]
                n += Vector(((a.y - b.y) * (a.z + b.z), (a.z - b.z) * (a.x + b.x), (a.x - b.x) * (a.y + b.y)))
            if n.dot(Vector(facing)) < 0:
                pts = list(reversed(pts))
        vs = [self.bm.verts.new(L @ Vector(p)) for p in pts]
        f = self.bm.faces.new(vs)
        f.normal_update()
        faces = [f]
        if thick:
            n = f.normal * thick
            back = [self.bm.verts.new(v.co - n) for v in vs]
            fb = self.bm.faces.new(list(reversed(back)))
            fb.normal_update()
            faces.append(fb)
            k = len(vs)
            for i in range(k):
                j = (i + 1) % k
                g = self.bm.faces.new((vs[j], vs[i], back[i], back[j]))
                g.normal_update()
                faces.append(g)
        self._uv_planar(faces, mat, grain_dir, self._off(uvoff), pitch=pitch, vfit=vfit, strip=strip, voff=voff)
        self._paint(faces, mat, tone, smooth_=smooth_)
        return faces

    def _uv_planar(self, faces, mat, grain_dir=None, off=(0.0, 0.0), pitch=None, vfit=None, strip=None, voff=None):
        kind = kind_of(mat)
        gd = None
        if grain_dir is not None:
            gd = (self.M.to_3x3() @ Vector(grain_dir)).normalized()
        if kind == "plank" and mat in PLANK_SETS:
            kb = self.rng.randrange(64) if strip is None else strip
            voff = self.rng.uniform(0.0, 3.0) if voff is None else voff
            sa, sb = plank_strip(mat, kb)
            if vfit is not None and gd is not None:
                # along-grain extent of the whole primitive (all faces share it)
                vs_all = [v.co.dot(gd) for f in faces for v in f.verts]
                vlo, vhi = min(vs_all), max(vs_all)
            for f in faces:
                n = f.normal
                if gd is not None and abs(gd.dot(n)) < 0.95:
                    av = (gd - n * gd.dot(n)).normalized()
                else:
                    best, av = -1, Vector((0, 0, 1))
                    for e in f.edges:
                        dv = e.verts[1].co - e.verts[0].co
                        if dv.length > best:
                            best, av = dv.length, dv.normalized()
                au = n.cross(av).normalized()
                us = [lp.vert.co.dot(au) for lp in f.loops]
                lo, hi = min(us), max(us)
                w = hi - lo
                for lp, u in zip(f.loops, us):
                    v = lp.vert.co.dot(av) + voff + off[1]
                    if vfit is not None and gd is not None and vhi - vlo > 1e-4:
                        v = vfit[0] + (vfit[1] - vfit[0]) * (lp.vert.co.dot(gd) - vlo) / (vhi - vlo)
                    if 1e-4 < w <= FIT_MAX:
                        uu = sa + (sb - sa) * (u - lo) / w
                    elif pitch is not None:
                        pw, anchor = pitch
                        u0 = (self.M @ Vector(anchor)).dot(au)
                        uu = plank_seam0(mat) + (u - u0) * plank_pitch(mat) / pw
                    else:
                        uu = u + off[0]
                    lp[self.uv].uv = (uu, v)
            return
        for f in faces:
            n = f.normal
            if gd is not None and abs(gd.dot(n)) < 0.95:
                au = (gd - n * gd.dot(n)).normalized()
            elif kind == "grain":
                # longest edge direction
                best, au = -1, None
                for e in f.edges:
                    d = e.verts[1].co - e.verts[0].co
                    if d.length > best:
                        best, au = d.length, d.normalized()
            else:
                h = n.cross(Z)
                au = h.normalized() if h.length > 1e-3 else Vector((1, 0, 0))
            av = n.cross(au).normalized()
            if av.z < -1e-4:
                av = -av
            for lp in f.loops:
                p = lp.vert.co
                lp[self.uv].uv = (p.dot(au) + off[0], p.dot(av) + off[1])

    def quad_uv(self, pts, mat, uvs=((0, 0), (1, 0), (1, 1), (0, 1)), tone=1.0):
        """One quad with explicit UVs (signs: label_* / sign_face, UV 0-1)."""
        vs = [self.bm.verts.new(self.M @ Vector(p)) for p in pts]
        f = self.bm.faces.new(vs)
        f.normal_update()
        for lp, uv in zip(f.loops, uvs):
            lp[self.uv].uv = uv
        self._paint([f], mat, tone)
        return f

    def panel(self, w, h, mat, loc=(0, 0, 0), rot=(0, 0, 0), uv=(0, 0, 1, 1), tone=1.0):
        """Vertical quad facing -Y (front) of size w x h, bottom-centre at loc, UV rect (u0,v0,u1,v1)."""
        u0, v0, u1, v1 = uv
        with self.at(loc, rot):
            return self.quad_uv([(-w / 2, 0, 0), (w / 2, 0, 0), (w / 2, 0, h), (-w / 2, 0, h)], mat,
                                uvs=((u0, v0), (u1, v0), (u1, v1), (u0, v1)), tone=tone)

    def loft(self, rings, mat, close=False, tone=1.0, smooth_=True, cap=False, uv_len=None):
        """Quads between successive rings (local points). U = arc length around the ring, V = along."""
        vr = [[self.bm.verts.new(self.M @ Vector(p)) for p in ring] for ring in rings]
        n = len(rings[0])
        faces = []
        vacc = [0.0]
        for i in range(1, len(vr)):
            ca = sum((v.co for v in vr[i - 1]), Vector()) / n
            cb = sum((v.co for v in vr[i]), Vector()) / n
            vacc.append(vacc[-1] + (cb - ca).length)
        ua = []
        for ring in vr:
            acc = [0.0]
            for j in range(1, n + 1):
                acc.append(acc[-1] + (ring[j % n].co - ring[j - 1].co).length)
            ua.append(acc)
        for i in range(len(vr) - 1):
            for k in range(n if close else n - 1):
                k2 = (k + 1) % n
                f = self.bm.faces.new((vr[i][k], vr[i][k2], vr[i + 1][k2], vr[i + 1][k]))
                f.normal_update()
                faces.append(f)
                uvs = ((ua[i][k], vacc[i]), (ua[i][k + 1], vacc[i]),
                       (ua[i + 1][k + 1], vacc[i + 1]), (ua[i + 1][k], vacc[i + 1]))
                for lp, uv in zip(f.loops, uvs):
                    lp[self.uv].uv = uv
        caps = []
        if cap:
            for ring in (vr[0], vr[-1]):
                f = self.bm.faces.new(ring if ring is vr[-1] else list(reversed(ring)))
                f.normal_update()
                caps.append(f)
            self._uv_planar(caps, mat)
        self._paint(faces + caps, mat, tone, smooth_=smooth_)
        for f in caps:
            f.smooth = False
        return faces + caps

    def tube(self, pts, r, mat, sides=6, tone=1.0, cap=False):
        """Round tube through local points (pipes, rails, wires, hoses)."""
        pts = [Vector(p) for p in pts]
        rings = []
        prev_a = None
        for i, p in enumerate(pts):
            d = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
            if prev_a is None:
                up = Z if abs(d.z) < 0.9 else Vector((1, 0, 0))
                a_ = d.cross(up).normalized()
            else:
                a_ = (prev_a - d * prev_a.dot(d)).normalized()
            prev_a = a_
            b_ = d.cross(a_).normalized()
            rings.append([p + (a_ * math.cos(k / sides * math.tau) + b_ * math.sin(k / sides * math.tau)) * r
                          for k in range(sides)])
        return self.loft(rings, mat, close=True, tone=tone, smooth_=True, cap=cap)

    def ring(self, r_in, r_out, w, mat, loc=(0, 0, 0), rot=(0, 0, 0), sides=24, tone=1.0, smooth_=True):
        """Flat ring (washer / tyre / band) about local Z, thickness w along Z, resting on loc."""
        prof = [(r_in, 0), (r_out, 0), (r_out, w), (r_in, w), (r_in, 0)]
        L = self.M @ T(loc) @ R(rot)
        rings = [[self.bm.verts.new(L @ Vector((rr * math.cos(a), rr * math.sin(a), zz)))
                  for a in (i / sides * math.tau for i in range(sides))] for rr, zz in prof[:4]]
        faces = []
        for k in range(4):
            k2 = (k + 1) % 4
            for i in range(sides):
                j = (i + 1) % sides
                f = self.bm.faces.new((rings[k][i], rings[k][j], rings[k2][j], rings[k2][i]))
                f.normal_update()
                faces.append(f)
        self._uv_cyl(faces, L, r_out, mat, (0, 0))
        self._paint(faces, mat, tone, smooth_=False)
        for f in faces:
            # only the outer/inner cylinders are smooth
            if abs(f.normal.dot((L.to_3x3() @ Z).normalized())) < 0.5:
                f.smooth = smooth_
        return faces

    # -------------------------------------------------------------- finish
    def tris(self):
        return sum(len(f.verts) - 2 for f in self.bm.faces)

    def finish(self, parent=None, sharp_angle=40.0, weighted=True):
        bm = self.bm
        bm.normal_update()
        thr = math.radians(sharp_angle)
        for e in bm.edges:
            if len(e.link_faces) != 2:
                e.smooth = False
                continue
            f0, f1 = e.link_faces
            if not (f0.smooth and f1.smooth) or f0.material_index != f1.material_index:
                e.smooth = False
            else:
                e.smooth = e.calc_face_angle(0.0) < thr
        me = bpy.data.meshes.new(self.name)
        bm.to_mesh(me)
        bm.free()
        o = bpy.data.objects.new(self.name, me)
        bpy.context.scene.collection.objects.link(o)
        for n in self.mats:
            me.materials.append(bpy.data.materials.get(n) or mat(n))
        if "Color" in me.color_attributes:
            me.color_attributes.active_color = me.color_attributes["Color"]
            me.color_attributes.render_color_index = me.color_attributes.active_color_index
        if weighted:
            wn = o.modifiers.new("WN", "WEIGHTED_NORMAL")
            wn.mode = "FACE_AREA"
            wn.keep_sharp = True
            wn.weight = 50
        if parent is not None:
            o.parent = parent
        return o


def empty(name, loc=(0, 0, 0), rot=(0, 0, 0), parent=None, size=0.3):
    o = bpy.data.objects.new(name, None)
    o.empty_display_type = "PLAIN_AXES"
    o.empty_display_size = size
    o.location = loc
    o.rotation_euler = [math.radians(a) for a in rot]
    bpy.context.scene.collection.objects.link(o)
    if parent is not None:
        o.parent = parent
    return o


def strip_colors(obj):
    """Remove COLOR_0 (labels / signs: no grime)."""
    me = obj.data
    for a in list(me.color_attributes):
        me.color_attributes.remove(a)


# ------------------------------------------------------------------ grime bake

def node_objects(root):
    out = [root]
    for c in root.children_recursive:
        out.append(c)
    return out


def bake_grime(root, distance=1.2, samples=48, ground=True, floor_z=0.0, dirt_h=0.7, ao_min=0.32,
               dirt=0.22):
    """Cycles AO -> vertex colours, combined with the per-part tone already in 'Color':
    Color = tone * lerp(ao_min, 1, ao) * ground-splash darkening. Only meshes that carry a 'Color'
    attribute are baked (labels have none)."""
    sc = bpy.context.scene
    objs = node_objects(root)
    meshes = [o for o in objs if o.type == "MESH" and "Color" in o.data.color_attributes]
    if not meshes:
        return
    # isolate: exclude every other node collection from the view layer (Cycles then syncs only this node)
    excluded = []
    mine = root.users_collection[0].name if root.users_collection else None
    for lc in bpy.context.view_layer.layer_collection.children:
        if lc.name.startswith("N_") and lc.name != mine and not lc.exclude:
            lc.exclude = True
            excluded.append(lc)
    keep = set(objs)
    hidden = []
    for o in sc.objects:
        if o not in keep and not o.hide_render:
            o.hide_render = True
            hidden.append(o)
    gp = None
    if ground:
        g = bpy.data.meshes.new("_bake_ground")
        s = 60.0
        g.from_pydata([(-s, -s, floor_z), (s, -s, floor_z), (s, s, floor_z), (-s, s, floor_z)], [], [(0, 1, 2, 3)])
        gp = bpy.data.objects.new("_bake_ground", g)
        sc.collection.objects.link(gp)
        gp.matrix_world = root.matrix_world.copy()
    sc.render.engine = "CYCLES"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "CUDA"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = d.type != "CPU"
        sc.cycles.device = "GPU"
    except Exception as e:  # noqa
        print("[tk] cycles GPU unavailable:", e)
    sc.cycles.samples = samples
    if sc.world is None:
        sc.world = bpy.data.worlds.new("World")
    sc.world.light_settings.distance = distance
    for o in meshes:
        me = o.data
        if "AO" in me.color_attributes:
            me.color_attributes.remove(me.color_attributes["AO"])
        ao = me.color_attributes.new("AO", "FLOAT_COLOR", "CORNER")
        me.color_attributes.active_color = ao
    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    muted = []
    for o in objs:
        ad = o.animation_data
        if ad:
            for tr in ad.nla_tracks:
                if not tr.mute:
                    tr.mute = True
                    muted.append(tr)
    sc.render.bake.target = "VERTEX_COLORS"
    sc.render.bake.use_selected_to_active = False
    bpy.ops.object.bake(type="AO", target="VERTEX_COLORS")
    for o in meshes:
        me = o.data
        Mw = o.matrix_world
        Mr = root.matrix_world.inverted()
        aoa = me.color_attributes["AO"].data
        ca = me.color_attributes["Color"].data
        loops = me.loops
        verts = me.vertices
        for li in range(len(loops)):
            a = aoa[li].color[0]
            t = ca[li].color[0]
            zloc = (Mr @ (Mw @ verts[loops[li].vertex_index].co)).z - floor_z
            g = 1.0 - dirt * (1.0 - smooth(0.0, dirt_h, zloc))
            v = t * lerp(ao_min, 1.0, a ** 1.15) * g
            ca[li].color = (v, v, v, 1.0)
        me.color_attributes.remove(me.color_attributes["AO"])
        me.color_attributes.active_color = me.color_attributes["Color"]
    for tr in muted:
        tr.mute = False
    for lc in excluded:
        lc.exclude = False
    if gp is not None:
        bpy.data.objects.remove(gp, do_unlink=True)
    for o in hidden:
        o.hide_render = False


# ------------------------------------------------------------------ export

def export(path, roots):
    """GLB with meshopt, Y-up, COLOR_0 only where a 'Color' attribute exists, no animations
    unless objects carry NLA clips."""
    objs = []
    for r in roots:
        objs += node_objects(r)
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = roots[0]
    path = os.path.abspath(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=path, export_format="GLB", use_selection=True, export_apply=True, export_yup=True,
        export_animations=True, export_animation_mode="NLA_TRACKS", export_extras=False,
        export_vertex_color="NAME", export_vertex_color_name="Color", export_all_vertex_colors=False,
        export_active_vertex_color_when_no_material=False, export_meshopt_compression_enable=True,
        export_image_format="AUTO", export_tangents=False, export_cameras=False, export_lights=False)
    fix_names(path)
    print(f"[tk] exported {path} ({os.path.getsize(path) / 1024:.1f} KB)")
    return path


def fix_names(path):
    """Strip Blender's '.001' uniqueness suffixes from node/mesh names inside a GLB (children like
    wheels_0 / door repeat across nodes; three.js looks them up inside each node)."""
    import json
    import re
    import struct
    data = open(path, "rb").read()
    magic, ver, total = struct.unpack_from("<III", data, 0)
    jlen, jtype = struct.unpack_from("<II", data, 12)
    js = json.loads(data[20:20 + jlen])
    rest = data[20 + jlen:]
    pat = re.compile(r"\.\d{3}$")
    for key in ("nodes", "meshes"):
        for item in js.get(key, []):
            if "name" in item:
                item["name"] = pat.sub("", item["name"])
    out = json.dumps(js, separators=(",", ":")).encode()
    out += b" " * ((4 - len(out) % 4) % 4)
    blob = struct.pack("<III", magic, ver, 12 + 8 + len(out) + len(rest)) + struct.pack("<II", len(out), jtype) + out + rest
    open(path, "wb").write(blob)


def tri_count(root):
    dg = bpy.context.evaluated_depsgraph_get()
    n = 0
    for o in node_objects(root):
        if o.type != "MESH":
            continue
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        n += sum(len(p.vertices) - 2 for p in me.polygons)
        ev.to_mesh_clear()
    return n


def bounds(root):
    pts = []
    Mi = root.matrix_world.inverted()
    for o in node_objects(root):
        if o.type != "MESH":
            continue
        for c in o.bound_box:
            pts.append(Mi @ (o.matrix_world @ Vector(c)))
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi
