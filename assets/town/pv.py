"""pv: golden-hour preview staging for the town (EEVEE). Previews only; never exported.

Upgrades the flat library materials with procedural detail (grain, bricks, shingles, corrugation)
so renders read like the in-game PBR look, then stages sun + sky + dirt ground + camera.
"""
import math
import os

import bpy
from mathutils import Vector

import tk

RIG = "_pv"


def _coll():
    c = bpy.data.collections.get(RIG)
    if c is None:
        c = bpy.data.collections.new(RIG)
        bpy.context.scene.collection.children.link(c)
    return c


def _link(o):
    for c in list(o.users_collection):
        c.objects.unlink(o)
    _coll().objects.link(o)
    return o


def clear():
    c = bpy.data.collections.get(RIG)
    if c:
        for o in list(c.objects):
            bpy.data.objects.remove(o, do_unlink=True)


# ------------------------------------------------------------------ material upgrades (preview only)

def _nodes(m):
    return m.node_tree.nodes, m.node_tree.links


def _uv(nt):
    tc = nt.nodes.new("ShaderNodeTexCoord")
    return tc.outputs["UV"]


def _mixmul(m):
    for n in m.node_tree.nodes:
        if n.type == "MIX" and n.blend_type == "MULTIPLY":
            return n
    return None


def upgrade_materials():
    g = bpy.data.materials.get("glass")
    if g is not None:
        pg = g.node_tree.nodes.get("Principled BSDF")
        pg.inputs["Alpha"].default_value = 0.1
        pg.inputs["Base Color"].default_value = tk.hex_lin("#5a6a72")
    for m in bpy.data.materials:
        if m.get("_pv") or m.name not in tk.LIB:
            continue
        m["_pv"] = True
        mix = _mixmul(m)
        if mix is None:
            continue
        nt = m.node_tree
        N, L = nt.nodes, nt.links
        p = N.get("Principled BSDF")
        base = mix.inputs["A"].default_value[:]
        uv = _uv(nt)
        name = m.name
        col_out = None
        bump_h = None
        if name.startswith("wood_"):
            # long grain along U + plank-scale variation
            mp = N.new("ShaderNodeMapping")
            mp.inputs["Scale"].default_value = (0.6, 9.0, 1.0)
            L.new(uv, mp.inputs["Vector"])
            nz = N.new("ShaderNodeTexNoise")
            nz.inputs["Scale"].default_value = 3.0
            nz.inputs["Detail"].default_value = 8.0
            nz.inputs["Roughness"].default_value = 0.6
            L.new(mp.outputs["Vector"], nz.inputs["Vector"])
            ramp = N.new("ShaderNodeValToRGB")
            dk = 0.62 if "painted" not in name else 0.86
            ramp.color_ramp.elements[0].color = tuple(c * dk for c in base[:3]) + (1,)
            ramp.color_ramp.elements[1].color = tuple(min(1, c * 1.12) for c in base[:3]) + (1,)
            L.new(nz.outputs["Fac"], ramp.inputs["Fac"])
            col_out = ramp.outputs["Color"]
            bump_h = nz.outputs["Fac"]
            if "painted" in name:
                # peeling: patches of grey weathered wood
                nz2 = N.new("ShaderNodeTexNoise")
                nz2.inputs["Scale"].default_value = 2.2
                nz2.inputs["Detail"].default_value = 10.0
                mp2 = N.new("ShaderNodeMapping")
                mp2.inputs["Scale"].default_value = (1.5, 5.0, 1.0)
                L.new(uv, mp2.inputs["Vector"])
                L.new(mp2.outputs["Vector"], nz2.inputs["Vector"])
                r2 = N.new("ShaderNodeValToRGB")
                r2.color_ramp.elements[0].position = 0.64
                r2.color_ramp.elements[1].position = 0.68
                L.new(nz2.outputs["Fac"], r2.inputs["Fac"])
                mx = N.new("ShaderNodeMix")
                mx.data_type = "RGBA"
                mx.inputs["B"].default_value = tk.hex_lin("#8a8072")
                L.new(r2.outputs["Color"], mx.inputs["Factor"])
                L.new(col_out, mx.inputs["A"])
                col_out = mx.outputs["Result"]
        elif name == "brick":
            br = N.new("ShaderNodeTexBrick")
            br.inputs["Scale"].default_value = 1.0
            br.inputs["Brick Width"].default_value = 0.215
            br.inputs["Row Height"].default_value = 0.075
            br.inputs["Mortar Size"].default_value = 0.01
            br.inputs["Color1"].default_value = tk.hex_lin("#93503a")
            br.inputs["Color2"].default_value = tk.hex_lin("#7a3a2a")
            br.inputs["Mortar"].default_value = tk.hex_lin("#b8ad9a")
            L.new(uv, br.inputs["Vector"])
            col_out = br.outputs["Color"]
            bump_h = br.outputs["Fac"]
        elif name == "roof_shingle":
            br = N.new("ShaderNodeTexBrick")
            br.inputs["Scale"].default_value = 1.0
            br.inputs["Brick Width"].default_value = 0.16
            br.inputs["Row Height"].default_value = 0.13
            br.inputs["Mortar Size"].default_value = 0.008
            br.inputs["Color1"].default_value = tk.hex_lin("#6a5848")
            br.inputs["Color2"].default_value = tk.hex_lin("#4c3e33")
            br.inputs["Mortar"].default_value = tk.hex_lin("#241c16")
            L.new(uv, br.inputs["Vector"])
            col_out = br.outputs["Color"]
            bump_h = br.outputs["Fac"]
        elif name in ("corrugated",):
            wv = N.new("ShaderNodeTexWave")
            wv.wave_type = "BANDS"
            wv.bands_direction = "X"
            wv.inputs["Scale"].default_value = 13.0
            L.new(uv, wv.inputs["Vector"])
            nz = N.new("ShaderNodeTexNoise")
            nz.inputs["Scale"].default_value = 1.2
            L.new(uv, nz.inputs["Vector"])
            ramp = N.new("ShaderNodeValToRGB")
            ramp.color_ramp.elements[0].color = tk.hex_lin("#6e4a32")
            ramp.color_ramp.elements[1].color = tk.hex_lin("#9aa0a3")
            ramp.color_ramp.elements[0].position = 0.42
            ramp.color_ramp.elements[1].position = 0.6
            L.new(nz.outputs["Fac"], ramp.inputs["Fac"])
            col_out = ramp.outputs["Color"]
            bump_h = wv.outputs["Fac"]
        else:
            nz = N.new("ShaderNodeTexNoise")
            nz.inputs["Scale"].default_value = 4.0
            nz.inputs["Detail"].default_value = 6.0
            L.new(uv, nz.inputs["Vector"])
            ramp = N.new("ShaderNodeValToRGB")
            ramp.color_ramp.elements[0].color = tuple(c * 0.82 for c in base[:3]) + (1,)
            ramp.color_ramp.elements[1].color = tuple(min(1, c * 1.1) for c in base[:3]) + (1,)
            L.new(nz.outputs["Fac"], ramp.inputs["Fac"])
            col_out = ramp.outputs["Color"]
            bump_h = nz.outputs["Fac"] if name in ("rock", "rock_pale", "concrete", "gravel", "dirt") else None
        if col_out is not None:
            L.new(col_out, mix.inputs["A"])
        if bump_h is not None:
            bp = N.new("ShaderNodeBump")
            bp.inputs["Strength"].default_value = 0.25 if name != "corrugated" else 0.6
            bp.inputs["Distance"].default_value = 0.02
            L.new(bump_h, bp.inputs["Height"])
            L.new(bp.outputs["Normal"], p.inputs["Normal"])


# ------------------------------------------------------------------ stage

def stage(sun_from=(-0.93, -0.30), sun_el=11.0, sun_power=7.5, sky=0.22, ground=True, ground_col="#8a7358",
          haze=0.0):
    sc = bpy.context.scene
    clear()
    w = sc.world or bpy.data.worlds.new("World")
    sc.world = w
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    skyn = nt.nodes.new("ShaderNodeTexSky")
    try:
        skyn.sky_type = "SINGLE_SCATTERING"
    except Exception:
        skyn.sky_type = "PREETHAM"
    az = math.atan2(sun_from[1], sun_from[0])
    try:
        skyn.sun_elevation = math.radians(sun_el)
        skyn.sun_rotation = az - math.pi / 2
        skyn.sun_disc = False
        skyn.altitude = 800.0
        skyn.air_density = 1.4
        skyn.aerosol_density = 2.2
    except Exception as e:  # noqa
        print("[pv] sky", e)
    nt.links.new(skyn.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = sky
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    # sun
    ld = bpy.data.lights.new("_pv_sun", "SUN")
    ld.energy = sun_power
    ld.color = tk.hex_lin("#ffc48a")[:3]
    ld.angle = math.radians(1.2)
    sun = _link(bpy.data.objects.new("_pv_sun", ld))
    d = Vector((-sun_from[0], -sun_from[1], -math.tan(math.radians(sun_el)))).normalized()
    sun.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    if ground:
        g = bpy.data.meshes.new("_pv_ground")
        s = 600
        g.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
        go = _link(bpy.data.objects.new("_pv_ground", g))
        m = bpy.data.materials.get("_pv_dirt") or bpy.data.materials.new("_pv_dirt")
        p = m.node_tree.nodes.get("Principled BSDF")
        N, L = m.node_tree.nodes, m.node_tree.links
        nz = N.new("ShaderNodeTexNoise")
        nz.inputs["Scale"].default_value = 0.08
        nz.inputs["Detail"].default_value = 12.0
        ramp = N.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].color = tk.hex_lin("#6e5a44")
        ramp.color_ramp.elements[1].color = tk.hex_lin("#a08a6c")
        L.new(nz.outputs["Fac"], ramp.inputs["Fac"])
        L.new(ramp.outputs["Color"], p.inputs["Base Color"])
        p.inputs["Roughness"].default_value = 0.96
        nz2 = N.new("ShaderNodeTexNoise")
        nz2.inputs["Scale"].default_value = 3.0
        bp = N.new("ShaderNodeBump")
        bp.inputs["Strength"].default_value = 0.3
        L.new(nz2.outputs["Fac"], bp.inputs["Height"])
        L.new(bp.outputs["Normal"], p.inputs["Normal"])
        g.materials.append(m)
    if haze > 0:
        vm = bpy.data.materials.get("_pv_haze")
        wv = nt.nodes.new("ShaderNodeVolumePrincipled")
        wv.inputs["Density"].default_value = haze
        wv.inputs["Color"].default_value = tk.hex_lin("#e8c9a0")
        nt.links.new(wv.outputs["Volume"], out.inputs["Volume"])
    sc.render.engine = "BLENDER_EEVEE"
    ee = sc.eevee
    ee.taa_render_samples = 48
    try:
        ee.use_raytracing = True
        ee.ray_tracing_options.resolution_scale = "2"
    except Exception:
        pass
    try:
        ee.use_shadows = True
        ee.shadow_ray_count = 2
        ee.shadow_step_count = 8
    except Exception:
        pass
    try:
        ee.use_fast_gi = True
    except Exception:
        pass
    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        pass
    sc.view_settings.exposure = 0.0
    return sun


def camera(loc, target, lens=35.0):
    sc = bpy.context.scene
    cd = bpy.data.cameras.new("_pv_cam")
    cd.lens = lens
    cd.clip_start = 0.05
    cd.clip_end = 3000
    cam = _link(bpy.data.objects.new("_pv_cam", cd))
    cam.location = loc
    d = (Vector(target) - Vector(loc)).normalized()
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    sc.camera = cam
    return cam


def render(path, res=(1600, 900), samples=48):
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.eevee.taa_render_samples = samples
    sc.render.image_settings.file_format = "PNG"
    sc.render.filepath = os.path.abspath(path)
    os.makedirs(os.path.dirname(sc.render.filepath), exist_ok=True)
    bpy.ops.render.render(write_still=True)
    print(f"[pv] {sc.render.filepath}")
    return sc.render.filepath
