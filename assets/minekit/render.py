"""EEVEE previews of the mine kit (reads the build .blend; nothing here is exported).

    bl assets/minekit/render.py -- <blend> sheet <out.png> [names,...] [--cols N]
    bl assets/minekit/render.py -- <blend> close <out.png> <name> [az] [el] [--mine] [--zoom k]
    bl assets/minekit/render.py -- <blend> vignette <out.png>
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import mk  # noqa: E402
from mk import DEG, descendants, hexlin, tree_bounds  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


# ====================================================================== preview shaders
def _n(nt, kind, **kw):
    n = nt.nodes.new(kind)
    for k, v in kw.items():
        setattr(n, k, v)
    return n


def preview_material(m):
    name = m.name
    if m.get("label") or m.get("custom"):
        nt = m.node_tree
        p = nt.nodes.get("Principled BSDF")
        tex = [n for n in nt.nodes if n.type == "TEX_IMAGE"][0]
        mk._vc_mult(nt, tex.outputs["Color"], p)
        return
    base = name.split(".")[0]
    if base not in mk.LIB:
        return
    col, rough, metal = mk.LIB[base]
    nt = m.node_tree
    p = nt.nodes.get("Principled BSDF")
    uv = _n(nt, "ShaderNodeTexCoord")
    links = nt.links
    c0 = hexlin(col)

    def mix(a, b, fac):
        mx = _n(nt, "ShaderNodeMix", data_type="RGBA")
        if isinstance(fac, float):
            mx.inputs["Factor"].default_value = fac
        else:
            links.new(fac, mx.inputs["Factor"])
        for sock, val in ((6, a), (7, b)):
            if isinstance(val, tuple):
                mx.inputs[sock].default_value = val
            else:
                links.new(val, mx.inputs[sock])
        return mx.outputs[2]

    def noise(scale, detail=4.0, rough_=0.55, src="UV", dim="3D"):
        nn = _n(nt, "ShaderNodeTexNoise")
        nn.inputs["Scale"].default_value = scale
        nn.inputs["Detail"].default_value = detail
        nn.inputs["Roughness"].default_value = rough_
        links.new(uv.outputs[src], nn.inputs["Vector"])
        return nn

    def ramp(fac, stops):
        r = _n(nt, "ShaderNodeValToRGB")
        links.new(fac, r.inputs["Fac"])
        el = r.color_ramp.elements
        el[0].position, el[0].color = stops[0][0], stops[0][1]
        el[1].position, el[1].color = stops[-1][0], stops[-1][1]
        for pos, c in stops[1:-1]:
            e = el.new(pos)
            e.color = c
        return r.outputs["Color"]

    def scale_col(c, k):
        return (c[0] * k, c[1] * k, c[2] * k, 1.0)

    def bump(height, strength=0.3, dist=0.01):
        b = _n(nt, "ShaderNodeBump")
        b.inputs["Strength"].default_value = strength
        b.inputs["Distance"].default_value = dist
        links.new(height, b.inputs["Height"])
        links.new(b.outputs["Normal"], p.inputs["Normal"])

    color_out = None
    if base.startswith("wood"):
        wv = _n(nt, "ShaderNodeTexWave", wave_type="BANDS", bands_direction="Y")
        wv.inputs["Scale"].default_value = 38.0
        wv.inputs["Distortion"].default_value = 9.0
        wv.inputs["Detail"].default_value = 3.0
        mp = _n(nt, "ShaderNodeMapping")
        mp.inputs["Scale"].default_value = (0.25, 1.0, 1.0)
        links.new(uv.outputs["UV"], mp.inputs["Vector"])
        links.new(mp.outputs["Vector"], wv.inputs["Vector"])
        nz = noise(6.0, 6, 0.6)
        g = ramp(wv.outputs["Fac"], [(0.0, scale_col(c0, 0.55)), (0.5, scale_col(c0, 0.95)), (1.0, scale_col(c0, 1.25))])
        color_out = mix(g, scale_col(c0, 0.6), nz.outputs["Fac"])
        # weathered grey patches
        grey = noise(2.0, 3, 0.5)
        gr = _n(nt, "ShaderNodeMapRange")
        links.new(grey.outputs["Fac"], gr.inputs["Value"])
        gr.inputs[1].default_value, gr.inputs[2].default_value = 0.5, 0.75
        color_out = mix(color_out, (0.16, 0.14, 0.12, 1), gr.outputs["Result"])
        p.inputs["Roughness"].default_value = 0.88
        bump(wv.outputs["Fac"], 0.25, 0.004)
    elif base.startswith("paint") or base in ("plastic_yellow", "helmet_yellow", "helmet_white", "hose_yellow", "hose_red"):
        nz = noise(3.0, 5, 0.6)
        color_out = mix(scale_col(c0, 0.86), scale_col(c0, 1.06), nz.outputs["Fac"])
        if base.startswith("paint"):
            wear = noise(9.0, 8, 0.7)
            wr = _n(nt, "ShaderNodeMapRange")
            links.new(wear.outputs["Fac"], wr.inputs["Value"])
            wr.inputs[1].default_value, wr.inputs[2].default_value = 0.66, 0.70
            color_out = mix(color_out, hexlin("#3a2a1e"), wr.outputs["Result"])
            mr = _n(nt, "ShaderNodeMath", operation="MULTIPLY")
            links.new(wr.outputs["Result"], mr.inputs[0])
            mr.inputs[1].default_value = 0.5
            links.new(mr.outputs[0], p.inputs["Metallic"])
        rn = noise(14.0, 4, 0.5)
        rr = _n(nt, "ShaderNodeMapRange")
        links.new(rn.outputs["Fac"], rr.inputs["Value"])
        rr.inputs[3].default_value, rr.inputs[4].default_value = rough - 0.15, rough + 0.2
        links.new(rr.outputs["Result"], p.inputs["Roughness"])
        bump(rn.outputs["Fac"], 0.06, 0.002)
    elif base in ("steel", "steel_dark", "galvanized", "chrome", "cast_iron", "aluminium", "brass", "copper", "gold",
                  "corrugated"):
        nz = noise(4.0, 6, 0.65)
        color_out = mix(scale_col(c0, 0.8), scale_col(c0, 1.1), nz.outputs["Fac"])
        rn = noise(18.0, 5, 0.6)
        rr = _n(nt, "ShaderNodeMapRange")
        links.new(rn.outputs["Fac"], rr.inputs["Value"])
        rr.inputs[3].default_value, rr.inputs[4].default_value = max(0.05, rough - 0.12), rough + 0.25
        links.new(rr.outputs["Result"], p.inputs["Roughness"])
        if base in ("steel", "steel_dark", "cast_iron"):
            rs = noise(5.0, 8, 0.7)
            rsm = _n(nt, "ShaderNodeMapRange")
            links.new(rs.outputs["Fac"], rsm.inputs["Value"])
            rsm.inputs[1].default_value, rsm.inputs[2].default_value = 0.6, 0.72
            color_out = mix(color_out, hexlin("#5a3018"), rsm.outputs["Result"])
        bump(rn.outputs["Fac"], 0.05, 0.002)
    elif base == "rust":
        nz = noise(7.0, 8, 0.7)
        color_out = ramp(nz.outputs["Fac"], [(0.3, hexlin("#3a1d0e")), (0.5, hexlin("#6e3a1c")), (0.7, hexlin("#8a4a22"))])
        p.inputs["Roughness"].default_value = 0.92
        bump(nz.outputs["Fac"], 0.35, 0.004)
    elif base in ("rock", "rock_dark", "rock_red", "rock_pale", "gravel", "dirt", "coal_ore", "iron_ore", "silver_ore",
                  "gold_ore", "concrete"):
        vor = _n(nt, "ShaderNodeTexVoronoi")
        vor.inputs["Scale"].default_value = 9.0 if base != "gravel" else 30.0
        links.new(uv.outputs["Object"], vor.inputs["Vector"])
        nz = noise(5.0, 8, 0.65, src="Object")
        color_out = mix(scale_col(c0, 0.6), scale_col(c0, 1.25), nz.outputs["Fac"])
        color_out = mix(color_out, scale_col(c0, 0.5), vor.outputs["Distance"])
        if base == "coal_ore":
            p.inputs["Roughness"].default_value = 0.35
        bump(nz.outputs["Fac"], 0.5, 0.02)
    elif base in ("rubber", "cable", "plastic_black", "canvas", "leather", "glass_dark", "fabric_hivis"):
        nz = noise(30.0, 4, 0.5)
        color_out = mix(scale_col(c0, 0.85), scale_col(c0, 1.15), nz.outputs["Fac"])
        bump(nz.outputs["Fac"], 0.08, 0.002)
    elif base == "glass":
        p.inputs["Transmission Weight"].default_value = 1.0
        p.inputs["Roughness"].default_value = 0.04
        p.inputs["Alpha"].default_value = 0.35
        return
    elif base.startswith("emit_") or base == "sign_face":
        uvimg = os.path.join(HERE, "build", "uvtest.png")
        if os.path.exists(uvimg) and base in ("emit_screen", "sign_face"):
            tex = _n(nt, "ShaderNodeTexImage")
            tex.image = bpy.data.images.load(uvimg, check_existing=True)
            links.new(uv.outputs["UV"], tex.inputs["Vector"])
            links.new(tex.outputs["Color"], p.inputs["Base Color"])
            if base == "emit_screen":
                links.new(tex.outputs["Color"], p.inputs["Emission Color"])
                p.inputs["Emission Strength"].default_value = 1.2
        return
    if color_out is not None:
        mk._vc_mult(nt, color_out, p)


# ====================================================================== staging
def world(color="#0b0c0e", strength=1.0):
    s = bpy.context.scene
    w = s.world or bpy.data.worlds.new("World")
    s.world = w
    bg = w.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = hexlin(color)
    bg.inputs["Strength"].default_value = strength


def light(kind, loc, energy, color="#ffffff", size=0.5, target=None, spot=None, name="L", shadow_soft=None):
    ld = bpy.data.lights.new(name, kind)
    ld.energy = energy
    ld.color = hexlin(color)[:3]
    if kind in ("AREA",):
        ld.size = size
    if kind in ("POINT", "SPOT"):
        ld.shadow_soft_size = size
    if kind == "SUN":
        ld.angle = size
    if spot:
        ld.spot_size = spot[0] * DEG
        ld.spot_blend = spot[1]
    o = bpy.data.objects.new(name, ld)
    bpy.context.scene.collection.objects.link(o)
    o.location = loc
    if target is not None:
        d = Vector(target) - Vector(loc)
        o.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return o


def camera(loc, target, lens=35.0, name="Cam"):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.clip_start = 0.02
    cd.clip_end = 300
    o = bpy.data.objects.new(name, cd)
    bpy.context.scene.collection.objects.link(o)
    o.location = loc
    d = Vector(target) - Vector(loc)
    o.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = o
    return o


def setup_render(res=(1600, 1000), samples=64, exposure=0.0, look="AgX - Medium High Contrast"):
    s = bpy.context.scene
    s.render.engine = "BLENDER_EEVEE"
    s.render.resolution_x, s.render.resolution_y = res
    s.render.resolution_percentage = 100
    s.eevee.taa_render_samples = samples
    try:
        s.eevee.use_raytracing = True
        s.eevee.ray_tracing_options.resolution_scale = "2"
    except Exception:
        pass
    try:
        s.eevee.use_shadows = True
        s.eevee.shadow_ray_count = 2
        s.eevee.shadow_step_count = 8
    except Exception:
        pass
    s.view_settings.view_transform = "AgX"
    try:
        s.view_settings.look = look
    except Exception:
        pass
    s.view_settings.exposure = exposure
    s.render.image_settings.file_format = "PNG"


def render(out):
    s = bpy.context.scene
    s.render.filepath = os.path.abspath(out)
    bpy.ops.render.render(write_still=True)
    print(f"[render] {out}")


def roots():
    return [o for o in bpy.context.scene.objects if o.parent is None and not o.name.startswith("_")
            and o.type in ("MESH", "EMPTY")]


def text(body, loc, size=0.18, rot=(90, 0, 0)):
    cu = bpy.data.curves.new("txt", "FONT")
    cu.body = body
    cu.size = size
    cu.align_x = "CENTER"
    o = bpy.data.objects.new("_txt", cu)
    bpy.context.scene.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = [a * DEG for a in rot]
    m = bpy.data.materials.get("_txtmat") or mk.M("emit_white").copy()
    m.name = "_txtmat"
    cu.materials.append(m)
    return o


def floor(z=0.0, size=200, color="#222326"):
    me = bpy.data.meshes.new("_floor")
    me.from_pydata([(-size, -size, z), (size, -size, z), (size, size, z), (-size, size, z)], [], [(0, 1, 2, 3)])
    o = bpy.data.objects.new("_floor", me)
    bpy.context.scene.collection.objects.link(o)
    m = bpy.data.materials.new("_floormat")
    p = m.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value = hexlin(color)
    p.inputs["Roughness"].default_value = 0.9
    me.materials.append(m)
    return o


# ====================================================================== shots
def shot_sheet(out, names=None, cols=None, res=(2000, 1250)):
    rs = {o.name: o for o in roots()}
    names = names or list(rs.keys())
    items = [rs[n] for n in names if n in rs]
    for o in rs.values():
        if o not in items:
            for x in [o] + descendants(o):
                x.hide_render = True
    cols = cols or max(1, math.ceil(math.sqrt(len(items) * 1.6)))
    bounds = [tree_bounds(o) for o in items]
    cell = max(max(hi.x - lo.x, hi.y - lo.y) for lo, hi in bounds) * 1.15 + 0.3
    cell_w = [max(hi.x - lo.x, 0.4) for lo, hi in bounds]
    x = 0.0
    rowz = 0
    placed = []
    row_h = 0.0
    yrow = 0.0
    col = 0
    for o, (lo, hi), w in zip(items, bounds, cell_w):
        if col >= cols:
            col = 0
            x = 0.0
            yrow += row_h + 0.9
            row_h = 0.0
        h = hi.z - lo.z
        kind_lift = -lo.z
        o.location = (x - lo.x, yrow, kind_lift)
        placed.append((o, x + w / 2, yrow, h))
        text(o.name, (x + w / 2, yrow - 0.1 - (hi.y - lo.y) / 2 * 0 - 0.6, 0.02), size=0.16, rot=(0, 0, 0))
        x += w + 0.7
        row_h = max(row_h, hi.y - lo.y)
        col += 1
    bpy.context.view_layer.update()
    pts = []
    for o in items:
        lo, hi = tree_bounds(o)
        pts += [lo, hi]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), 0))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    c = (lo + hi) / 2
    floor(0.0)
    world("#16181c", 0.6)
    span = max(hi.x - lo.x, (hi.y - lo.y) * 1.6)
    cam = camera(c + Vector((0, -span * 0.95, span * 0.75)), c + Vector((0, 0, -span * 0.05)), lens=40)
    light("SUN", c + Vector((5, -6, 10)), 3.2, "#fff1de", size=0.08, target=c)
    light("AREA", c + Vector((-span * 0.6, -span * 0.5, span * 0.5)), 60 * span * span * 0.25, "#dde8ff",
          size=span * 0.8, target=c)
    setup_render(res, 48)
    render(out)


def shot_close(out, name, az=35.0, el=18.0, mine=False, zoom=1.0, res=(1400, 1050), target_z=None, lens=40):
    rs = {o.name: o for o in roots()}
    for o in rs.values():
        if o.name != name:
            for x in [o] + descendants(o):
                x.hide_render = True
    o = rs[name]
    lo, hi = tree_bounds(o)
    c = (lo + hi) / 2
    if target_z is not None:
        c.z = target_z
    r = max((hi - lo).length / 2, 0.15)
    fov = 2 * math.atan(18 / lens * min(res[0] / res[1], res[1] / res[0]))
    d = r / math.sin(fov / 2) * 1.02 / zoom
    a, e = az * DEG, el * DEG
    loc = c + Vector((d * math.cos(e) * math.sin(a), -d * math.cos(e) * math.cos(a), d * math.sin(e)))
    camera(loc, c, lens=lens)
    floor(lo.z - 0.001, color="#1d1e20" if mine else "#26282c")
    if mine:
        world("#030304", 1.0)
        light("POINT", c + Vector((r * 1.2, -r * 1.4, r * 1.1)), 120 * r * r + 30, "#ffb466", size=0.06)
        light("POINT", c + Vector((-r * 1.6, r * 0.6, r * 1.4)), 60 * r * r + 15, "#ff9d4d", size=0.1)
        light("SPOT", loc + Vector((0.15, 0, 0.1)), 400 * d * d * 0.08 + 40, "#e8f0ff", size=0.03,
              target=c, spot=(32, 0.6))
    else:
        world("#1a1c20", 0.7)
        light("SUN", c + Vector((4, -5, 8)), 3.0, "#fff0dc", size=0.06, target=c)
        light("AREA", c + Vector((-r * 3, -r * 2.5, r * 2)), 120 * r * r + 20, "#dbe6ff", size=r * 3, target=c)
        light("AREA", c + Vector((r * 0.5, r * 3.5, r * 2.5)), 160 * r * r + 30, "#ffffff", size=r * 2, target=c)
    setup_render(res, 64, exposure=0.0 if not mine else 0.3)
    render(out)


def shot_layout(out, spec):
    """spec = {"items": [[node, [x, y, z], yaw_deg], ...] (three.js coords: y up, +z = toward camera side),
    "cam": [x, y, z], "target": [x, y, z], "lens": 35, "mine": bool, "lights": [[x, y, z, energy, hex], ...]}"""
    import json
    sp = json.loads(open(spec).read()) if os.path.exists(spec) else json.loads(spec)
    rs = {o.name: o for o in roots()}
    used = {}
    for o in rs.values():
        for x in [o] + descendants(o):
            x.hide_render = True
    def t2b(v):
        return Vector((v[0], -v[2], v[1]))
    for name, pos, yaw in sp["items"]:
        src = rs[name]
        if name not in used:
            o = src
            for x in [o] + descendants(o):
                x.hide_render = False
            used[name] = 1
        else:
            o = src.copy()
            bpy.context.scene.collection.objects.link(o)
            for c in src.children:
                cc = c.copy()
                bpy.context.scene.collection.objects.link(cc)
                cc.parent = o
                for g in c.children:
                    gg = g.copy()
                    bpy.context.scene.collection.objects.link(gg)
                    gg.parent = cc
            for x in [o] + descendants(o):
                x.hide_render = False
        o.location = t2b(pos)
        o.rotation_euler = (0, 0, yaw * DEG)
    if sp.get("floor", True):
        floor(0.0, color=sp.get("floor_color", "#2a2724"))
    for w in sp.get("walls", []):
        me = bpy.data.meshes.new("_wall")
        c, sx, sz, ry = t2b(w[0]), w[1], w[2], w[3]
        me.from_pydata([(-sx / 2, 0, 0), (sx / 2, 0, 0), (sx / 2, 0, sz), (-sx / 2, 0, sz)], [], [(0, 1, 2, 3)])
        o = bpy.data.objects.new("_wall", me)
        bpy.context.scene.collection.objects.link(o)
        o.location = c
        o.rotation_euler = (0, 0, ry * DEG)
        m = bpy.data.materials.get("_wallmat") or mk.M("rock_dark").copy()
        m.name = "_wallmat"
        preview_material(m)
        me.materials.append(m)
    camera(t2b(sp["cam"]), t2b(sp["target"]), lens=sp.get("lens", 35))
    if sp.get("mine", True):
        world("#020203", 1.0)
    else:
        world("#1a1c20", 0.7)
        light("SUN", t2b(sp["target"]) + Vector((4, -5, 8)), 3.0, "#fff0dc", size=0.06, target=t2b(sp["target"]))
    for L in sp.get("lights", []):
        light("POINT", t2b(L[:3]), L[3], L[4], size=0.05)
    for L in sp.get("spots", []):
        light("SPOT", t2b(L[0]), L[2], L[3], size=0.03, target=t2b(L[1]), spot=(L[4], 0.5))
    setup_render(tuple(sp.get("res", (1600, 1000))), sp.get("samples", 64), exposure=sp.get("exposure", 0.0))
    render(out)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    blend, mode, out = argv[0], argv[1], argv[2]
    rest = argv[3:]
    bpy.ops.wm.open_mainfile(filepath=blend)
    for o in bpy.data.objects:  # preview multiplies Col; give grime-less meshes a white layer
        if o.type == "MESH" and o.data.color_attributes.get("Col") is None:
            ca = o.data.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
            for d in ca.data:
                d.color = (1, 1, 1, 1)
    for m in list(bpy.data.materials):
        preview_material(m)
    flags = {a for a in rest if a.startswith("--")}
    pos = [a for a in rest if not a.startswith("--")]

    def opt(name, default):
        if name in rest:
            return float(rest[rest.index(name) + 1])
        return default
    pos = [a for i, a in enumerate(pos) if not (i > 0 and rest[rest.index(a) - 1] in ("--zoom", "--cols", "--tz", "--lens"))]
    if mode == "sheet":
        names = pos[0].split(",") if pos and pos[0] != "all" else None
        shot_sheet(out, names, cols=int(opt("--cols", 0)) or None)
    elif mode == "close":
        name = pos[0]
        az = float(pos[1]) if len(pos) > 1 else 35.0
        el = float(pos[2]) if len(pos) > 2 else 18.0
        tz = opt("--tz", None)
        shot_close(out, name, az, el, mine="--mine" in flags, zoom=opt("--zoom", 1.0), target_z=tz,
                   lens=opt("--lens", 40.0))
    elif mode == "layout":
        shot_layout(out, pos[0])
    elif mode == "vignette":
        import vignette
        vignette.build_and_render(out, sys.modules[__name__])


main()
