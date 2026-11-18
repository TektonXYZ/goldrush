"""gr3d — shared pieces for the GoldRush 3D brand renders (logo, icon, banner).

Imported by goldrush3d.py. Everything is procedural: Saira Stencil One letters,
noise-displaced nuggets, a pickaxe, a studio lighting rig, Cycles on CUDA.
"""
import math
import os
import random

import bmesh
import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Matrix, Vector, noise

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(HERE, "fonts", "SairaStencilOne-Regular.ttf")
HDRI_DIR = os.path.join(HERE, "hdri")

GOLD = (1.0, 0.66, 0.12)          # linear base colour: Au F0 nudged toward the brand yellow
GOLD_DEEP = (0.95, 0.50, 0.06)


# ------------------------------------------------------------------ scene / render

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    s.unit_settings.system = "METRIC"
    return s


def link(o):
    bpy.context.scene.collection.objects.link(o)
    return o


def cycles(res, samples=384, transparent=False, look="AgX - Medium High Contrast", exposure=0.0):
    s = bpy.context.scene
    s.render.engine = "CYCLES"
    p = bpy.context.preferences.addons["cycles"].preferences
    p.compute_device_type = "CUDA"
    p.get_devices()
    for d in p.devices:
        d.use = d.type != "CPU"
    c = s.cycles
    c.device = "GPU"
    c.samples = samples
    c.use_adaptive_sampling = True
    c.adaptive_threshold = 0.004
    c.use_denoising = True
    c.denoiser = "OPENIMAGEDENOISE"
    for k, v in (("denoising_input_passes", "RGB_ALBEDO_NORMAL"),
                 ("denoising_prefilter", "ACCURATE"),
                 ("denoising_quality", "HIGH"),
                 ("denoising_use_gpu", True)):
        try:
            setattr(c, k, v)
        except Exception:
            pass
    c.max_bounces = 16
    c.glossy_bounces = 12
    c.diffuse_bounces = 4
    c.transmission_bounces = 8
    c.transparent_max_bounces = 16
    c.sample_clamp_indirect = 8.0
    c.blur_glossy = 0.4
    c.caustics_reflective = True
    c.caustics_refractive = False
    s.render.resolution_x, s.render.resolution_y = res
    s.render.resolution_percentage = 100
    s.render.film_transparent = transparent
    s.render.filter_size = 1.2
    s.view_settings.view_transform = "AgX"
    try:
        s.view_settings.look = look
    except Exception as e:  # pragma: no cover
        print("[gr3d] look not set:", e)
    s.view_settings.exposure = exposure
    s.render.image_settings.file_format = "PNG"
    s.render.image_settings.color_mode = "RGBA" if transparent else "RGB"
    s.render.image_settings.color_depth = "8"
    return s


def render(path):
    s = bpy.context.scene
    path = os.path.abspath(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    s.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("[gr3d] wrote", path)
    return path


def save_blend(path):
    path = os.path.abspath(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=path, compress=True)


# ------------------------------------------------------------------ node helpers

def _n(nt, kind, loc=(0, 0), **inputs):
    n = nt.nodes.new(kind)
    n.location = loc
    for k, v in inputs.items():
        n.inputs[k].default_value = v
    return n


def _l(nt, a, b):
    nt.links.new(a, b)


def new_mat(name):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = _n(nt, "ShaderNodeOutputMaterial", (900, 0))
    return m, nt, out


# ------------------------------------------------------------------ materials

def gold_polished(name="GoldPolished", rough=0.2, var=0.05, bump=0.025, color=GOLD):
    """Polished cast gold: metal 1, roughness wobbles ±var, faint cast-surface undulation."""
    m, nt, out = new_mat(name)
    tc = _n(nt, "ShaderNodeTexCoord", (-1200, 0))
    nz = _n(nt, "ShaderNodeTexNoise", (-950, 150), Scale=6.0, Detail=6.0, Roughness=0.55)
    _l(nt, tc.outputs["Object"], nz.inputs["Vector"])
    rr = _n(nt, "ShaderNodeMapRange", (-700, 150))
    rr.inputs["To Min"].default_value = rough - var
    rr.inputs["To Max"].default_value = rough + var
    rr.inputs["From Min"].default_value = 0.3
    rr.inputs["From Max"].default_value = 0.7
    _l(nt, nz.outputs["Fac"], rr.inputs["Value"])
    # subtle hue drift between rich and pale gold
    cr = _n(nt, "ShaderNodeValToRGB", (-700, 400))
    cr.color_ramp.elements[0].color = (*GOLD_DEEP, 1)
    cr.color_ramp.elements[1].color = (*color, 1)
    cr.color_ramp.elements[0].position = 0.25
    cr.color_ramp.elements[1].position = 0.75
    nz2 = _n(nt, "ShaderNodeTexNoise", (-950, 450), Scale=2.2, Detail=3.0)
    _l(nt, tc.outputs["Object"], nz2.inputs["Vector"])
    _l(nt, nz2.outputs["Fac"], cr.inputs["Fac"])
    mix = _n(nt, "ShaderNodeMix", (-450, 400))
    mix.data_type = "RGBA"
    mix.inputs["Factor"].default_value = 0.65
    mix.inputs["A"].default_value = (*color, 1)
    _l(nt, cr.outputs["Color"], mix.inputs["B"])
    # micro undulation (cast metal, not mirror-flat CG)
    nz3 = _n(nt, "ShaderNodeTexNoise", (-950, -200), Scale=14.0, Detail=4.0, Roughness=0.5)
    _l(nt, tc.outputs["Object"], nz3.inputs["Vector"])
    bp = _n(nt, "ShaderNodeBump", (-450, -200), Strength=bump, Distance=0.02)
    _l(nt, nz3.outputs["Fac"], bp.inputs["Height"])
    bs = _n(nt, "ShaderNodeBsdfPrincipled", (0, 0))
    bs.inputs["Metallic"].default_value = 1.0
    bs.inputs["Specular Tint"].default_value = (1.0, 0.93, 0.78, 1)
    _l(nt, mix.outputs["Result"], bs.inputs["Base Color"])
    _l(nt, rr.outputs["Result"], bs.inputs["Roughness"])
    _l(nt, bp.outputs["Normal"], bs.inputs["Normal"])
    _l(nt, bs.outputs["BSDF"], out.inputs["Surface"])
    return m


def gold_nugget(name="GoldNugget"):
    """Raw nugget: polished highs, rough pitted lows, dark dirt in deep crevices."""
    m, nt, out = new_mat(name)
    tc = _n(nt, "ShaderNodeTexCoord", (-1500, 0))
    # pits (voronoi) + grain (noise) as bump
    vor = _n(nt, "ShaderNodeTexVoronoi", (-1200, -300), Scale=34.0, Randomness=1.0)
    _l(nt, tc.outputs["Object"], vor.inputs["Vector"])
    nz = _n(nt, "ShaderNodeTexNoise", (-1200, -600), Scale=28.0, Detail=10.0, Roughness=0.62)
    _l(nt, tc.outputs["Object"], nz.inputs["Vector"])
    pit = _n(nt, "ShaderNodeMapRange", (-950, -300))
    pit.inputs["From Min"].default_value = 0.0
    pit.inputs["From Max"].default_value = 0.35
    pit.inputs["To Min"].default_value = 0.0
    pit.inputs["To Max"].default_value = 0.3
    _l(nt, vor.outputs["Distance"], pit.inputs["Value"])
    hsum = _n(nt, "ShaderNodeMath", (-750, -400))
    hsum.operation = "MULTIPLY_ADD"
    _l(nt, nz.outputs["Fac"], hsum.inputs[0])
    hsum.inputs[1].default_value = 1.0
    _l(nt, pit.outputs["Result"], hsum.inputs[2])
    bp = _n(nt, "ShaderNodeBump", (-500, -400), Strength=0.1, Distance=0.01)
    _l(nt, hsum.outputs["Value"], bp.inputs["Height"])
    # cavity mask: AO (0 in crevices)
    ao = _n(nt, "ShaderNodeAmbientOcclusion", (-1200, 300), Distance=0.12)
    ao.samples = 16
    cav = _n(nt, "ShaderNodeMapRange", (-950, 300))
    cav.inputs["From Min"].default_value = 0.35
    cav.inputs["From Max"].default_value = 0.95
    _l(nt, ao.outputs["AO"], cav.inputs["Value"])
    # roughness: polished on exposed lumps, matte in cavities and pits
    rough = _n(nt, "ShaderNodeMapRange", (-700, 100))
    rough.inputs["To Min"].default_value = 0.42
    rough.inputs["To Max"].default_value = 0.1
    _l(nt, cav.outputs["Result"], rough.inputs["Value"])
    rpit = _n(nt, "ShaderNodeMath", (-500, 100))
    rpit.operation = "MULTIPLY_ADD"
    _l(nt, pit.outputs["Result"], rpit.inputs[0])
    rpit.inputs[1].default_value = -0.12
    _l(nt, rough.outputs["Result"], rpit.inputs[2])
    rpit2 = _n(nt, "ShaderNodeMath", (-350, 100))
    rpit2.operation = "ADD"
    _l(nt, rpit.outputs["Value"], rpit2.inputs[0])
    rpit2.inputs[1].default_value = 0.06
    gold = _n(nt, "ShaderNodeBsdfPrincipled", (-100, 250))
    gold.inputs["Metallic"].default_value = 1.0
    gold.inputs["Base Color"].default_value = (1.0, 0.69, 0.17, 1)
    gold.inputs["Specular Tint"].default_value = (1.0, 0.93, 0.78, 1)
    _l(nt, rpit2.outputs["Value"], gold.inputs["Roughness"])
    _l(nt, bp.outputs["Normal"], gold.inputs["Normal"])
    dirt = _n(nt, "ShaderNodeBsdfPrincipled", (-100, -250))
    dirt.inputs["Base Color"].default_value = (0.09, 0.045, 0.015, 1)
    dirt.inputs["Roughness"].default_value = 0.85
    dirt.inputs["Metallic"].default_value = 0.3
    _l(nt, bp.outputs["Normal"], dirt.inputs["Normal"])
    dm = _n(nt, "ShaderNodeMapRange", (-500, 450))
    dm.inputs["From Min"].default_value = 0.0
    dm.inputs["From Max"].default_value = 0.35
    dm.inputs["To Min"].default_value = 0.85
    dm.inputs["To Max"].default_value = 0.0
    _l(nt, cav.outputs["Result"], dm.inputs["Value"])
    mx = _n(nt, "ShaderNodeMixShader", (300, 0))
    _l(nt, dm.outputs["Result"], mx.inputs["Fac"])
    _l(nt, gold.outputs["BSDF"], mx.inputs[1])
    _l(nt, dirt.outputs["BSDF"], mx.inputs[2])
    _l(nt, mx.outputs["Shader"], out.inputs["Surface"])
    return m


def steel(name="Steel", color=(0.42, 0.43, 0.45), rough=0.32):
    m, nt, out = new_mat(name)
    tc = _n(nt, "ShaderNodeTexCoord", (-1000, 0))
    nz = _n(nt, "ShaderNodeTexNoise", (-800, 0), Scale=30.0, Detail=6.0)
    _l(nt, tc.outputs["Object"], nz.inputs["Vector"])
    rr = _n(nt, "ShaderNodeMapRange", (-550, 0))
    rr.inputs["To Min"].default_value = rough - 0.08
    rr.inputs["To Max"].default_value = rough + 0.1
    _l(nt, nz.outputs["Fac"], rr.inputs["Value"])
    bs = _n(nt, "ShaderNodeBsdfPrincipled", (0, 0))
    bs.inputs["Metallic"].default_value = 1.0
    bs.inputs["Base Color"].default_value = (*color, 1)
    _l(nt, rr.outputs["Result"], bs.inputs["Roughness"])
    _l(nt, bs.outputs["BSDF"], out.inputs["Surface"])
    return m


def wood(name="Wood"):
    m, nt, out = new_mat(name)
    tc = _n(nt, "ShaderNodeTexCoord", (-1200, 0))
    mp = _n(nt, "ShaderNodeMapping", (-1000, 0))
    mp.inputs["Scale"].default_value = (1.0, 1.0, 0.08)   # grain runs along local Z
    _l(nt, tc.outputs["Object"], mp.inputs["Vector"])
    wv = _n(nt, "ShaderNodeTexWave", (-780, 0), Scale=9.0, Distortion=6.0, Detail=4.0)
    wv.wave_type = "RINGS"
    _l(nt, mp.outputs["Vector"], wv.inputs["Vector"])
    cr = _n(nt, "ShaderNodeValToRGB", (-550, 0))
    cr.color_ramp.elements[0].color = (0.055, 0.022, 0.008, 1)
    cr.color_ramp.elements[1].color = (0.20, 0.085, 0.03, 1)
    _l(nt, wv.outputs["Fac"], cr.inputs["Fac"])
    bp = _n(nt, "ShaderNodeBump", (-300, -250), Strength=0.15, Distance=0.01)
    _l(nt, wv.outputs["Fac"], bp.inputs["Height"])
    bs = _n(nt, "ShaderNodeBsdfPrincipled", (0, 0))
    bs.inputs["Roughness"].default_value = 0.42
    bs.inputs["Coat Weight"].default_value = 0.35
    bs.inputs["Coat Roughness"].default_value = 0.2
    _l(nt, cr.outputs["Color"], bs.inputs["Base Color"])
    _l(nt, bp.outputs["Normal"], bs.inputs["Normal"])
    _l(nt, bs.outputs["BSDF"], out.inputs["Surface"])
    return m


def emission(name, color=(1, 1, 1), strength=10.0):
    m, nt, out = new_mat(name)
    e = _n(nt, "ShaderNodeEmission", (0, 0))
    e.inputs["Color"].default_value = (*color, 1)
    e.inputs["Strength"].default_value = strength
    _l(nt, e.outputs["Emission"], out.inputs["Surface"])
    return m


def gradient_card(name, strength=6.0, color=(1.0, 0.95, 0.88), axis="Z", lo=0.0, hi=1.0, power=1.6):
    """Emission card brighter at one end (object-space gradient) — reflected by the gold faces."""
    m, nt, out = new_mat(name)
    tc = _n(nt, "ShaderNodeTexCoord", (-900, 0))
    sep = _n(nt, "ShaderNodeSeparateXYZ", (-700, 0))
    _l(nt, tc.outputs["Generated"], sep.inputs["Vector"])
    mr = _n(nt, "ShaderNodeMapRange", (-500, 0))
    mr.inputs["To Min"].default_value = lo
    mr.inputs["To Max"].default_value = hi
    _l(nt, sep.outputs[{"X": 0, "Y": 1, "Z": 2}[axis]], mr.inputs["Value"])
    pw = _n(nt, "ShaderNodeMath", (-300, 0))
    pw.operation = "POWER"
    _l(nt, mr.outputs["Result"], pw.inputs[0])
    pw.inputs[1].default_value = power
    mul = _n(nt, "ShaderNodeMath", (-150, 0))
    mul.operation = "MULTIPLY"
    _l(nt, pw.outputs["Value"], mul.inputs[0])
    mul.inputs[1].default_value = strength
    e = _n(nt, "ShaderNodeEmission", (100, 0))
    e.inputs["Color"].default_value = (*color, 1)
    _l(nt, mul.outputs["Value"], e.inputs["Strength"])
    _l(nt, e.outputs["Emission"], out.inputs["Surface"])
    return m


# ------------------------------------------------------------------ world

def world_hdri(hdri="studio_small_09_2k.hdr", strength=1.0, rot_z=0.0, camera_bg=None, bg_fn=None):
    """HDRI for lighting/reflections. camera_bg: None (HDRI visible) or a callable that
    builds a colour socket for camera rays: bg_fn(nt) -> output socket."""
    w = bpy.data.worlds.new("World")
    bpy.context.scene.world = w
    try:
        w.use_nodes = True
    except Exception:
        pass
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = _n(nt, "ShaderNodeOutputWorld", (900, 0))
    tc = _n(nt, "ShaderNodeTexCoord", (-1100, 0))
    mp = _n(nt, "ShaderNodeMapping", (-900, 0))
    mp.inputs["Rotation"].default_value = (0, 0, math.radians(rot_z))
    _l(nt, tc.outputs["Generated"], mp.inputs["Vector"])
    env = _n(nt, "ShaderNodeTexEnvironment", (-650, 0))
    env.image = bpy.data.images.load(os.path.join(HDRI_DIR, hdri), check_existing=True)
    _l(nt, mp.outputs["Vector"], env.inputs["Vector"])
    bg = _n(nt, "ShaderNodeBackground", (-300, 0), Strength=strength)
    _l(nt, env.outputs["Color"], bg.inputs["Color"])
    if bg_fn is None:
        _l(nt, bg.outputs["Background"], out.inputs["Surface"])
        return w
    lp = _n(nt, "ShaderNodeLightPath", (-300, 300))
    cam_col = bg_fn(nt)
    cbg = _n(nt, "ShaderNodeBackground", (-50, 200), Strength=1.0)
    _l(nt, cam_col, cbg.inputs["Color"])
    mx = _n(nt, "ShaderNodeMixShader", (300, 0))
    _l(nt, lp.outputs["Is Camera Ray"], mx.inputs["Fac"])
    _l(nt, bg.outputs["Background"], mx.inputs[1])
    _l(nt, cbg.outputs["Background"], mx.inputs[2])
    _l(nt, mx.outputs["Shader"], out.inputs["Surface"])
    return w


def world_studio(stops, hdri="studio_small_09_2k.hdr", hdri_mix=0.25, rot_z=0.0, strength=1.0,
                 bg_fn=None, backdrop=0.0, backdrop_top=0.3, diffuse=1.0):
    """Controlled studio dome: colour ramp over direction elevation (z of the unit view dir),
    plus a little real-HDRI detail so reflections are not CG-clean.
    stops: [(z in -1..1, (r,g,b)), ...]. bg_fn(nt) -> colour socket for camera rays."""
    w = bpy.data.worlds.new("World")
    bpy.context.scene.world = w
    try:
        w.use_nodes = True
    except Exception:
        pass
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = _n(nt, "ShaderNodeOutputWorld", (1200, 0))
    tc = _n(nt, "ShaderNodeTexCoord", (-1300, 0))
    sep = _n(nt, "ShaderNodeSeparateXYZ", (-1050, 300))
    _l(nt, tc.outputs["Generated"], sep.inputs["Vector"])
    mr = _n(nt, "ShaderNodeMapRange", (-850, 300))
    mr.inputs["From Min"].default_value = -1.0
    mr.inputs["From Max"].default_value = 1.0
    _l(nt, sep.outputs["Z"], mr.inputs["Value"])
    ramp = _n(nt, "ShaderNodeValToRGB", (-600, 300))
    cr = ramp.color_ramp
    cr.interpolation = "B_SPLINE"
    while len(cr.elements) < len(stops):
        cr.elements.new(0.5)
    for el, (z, col) in zip(cr.elements, stops):
        el.position = (z + 1) / 2
        el.color = (*col, 1)
    _l(nt, mr.outputs["Result"], ramp.inputs["Fac"])
    mp = _n(nt, "ShaderNodeMapping", (-1050, -100))
    mp.inputs["Rotation"].default_value = (0, 0, math.radians(rot_z))
    _l(nt, tc.outputs["Generated"], mp.inputs["Vector"])
    env = _n(nt, "ShaderNodeTexEnvironment", (-850, -100))
    env.image = bpy.data.images.load(os.path.join(HDRI_DIR, hdri), check_existing=True)
    _l(nt, mp.outputs["Vector"], env.inputs["Vector"])
    # ramp * (1-k + k*hdri_luma-ish): modulate the dome with the photo's structure
    mix = _n(nt, "ShaderNodeMix", (-300, 100))
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    mix.inputs["Factor"].default_value = hdri_mix
    _l(nt, ramp.outputs["Color"], mix.inputs["A"])
    _l(nt, env.outputs["Color"], mix.inputs["B"])
    col = mix.outputs["Result"]
    if backdrop > 0:
        # dark seamless backdrop behind the subject (+Y, low): floors reflect it, not the dome
        sy = _n(nt, "ShaderNodeMapRange", (-850, 600))
        sy.interpolation_type = "SMOOTHSTEP"
        sy.inputs["From Min"].default_value = -0.15
        sy.inputs["From Max"].default_value = 0.45
        _l(nt, sep.outputs["Y"], sy.inputs["Value"])
        sz = _n(nt, "ShaderNodeMapRange", (-850, 800))
        sz.interpolation_type = "SMOOTHSTEP"
        sz.inputs["From Min"].default_value = backdrop_top
        sz.inputs["From Max"].default_value = backdrop_top + 0.3
        sz.inputs["To Min"].default_value = 1.0
        sz.inputs["To Max"].default_value = 0.0
        _l(nt, sep.outputs["Z"], sz.inputs["Value"])
        m1 = _n(nt, "ShaderNodeMath", (-650, 700))
        m1.operation = "MULTIPLY"
        _l(nt, sy.outputs["Result"], m1.inputs[0])
        _l(nt, sz.outputs["Result"], m1.inputs[1])
        m2 = _n(nt, "ShaderNodeMath", (-500, 700))
        m2.operation = "MULTIPLY"
        _l(nt, m1.outputs[0], m2.inputs[0])
        m2.inputs[1].default_value = backdrop
        dk = _n(nt, "ShaderNodeMix", (-150, 300))
        dk.data_type = "RGBA"
        _l(nt, m2.outputs[0], dk.inputs["Factor"])
        _l(nt, col, dk.inputs["A"])
        dk.inputs["B"].default_value = (0.002, 0.0018, 0.0015, 1)
        col = dk.outputs["Result"]
    bg = _n(nt, "ShaderNodeBackground", (0, 0), Strength=strength)
    _l(nt, col, bg.inputs["Color"])
    if diffuse < 1.0:
        # the dome is a reflection set: diffuse surfaces (rock, ground) barely see it
        lpd = _n(nt, "ShaderNodeLightPath", (-300, -300))
        st = _n(nt, "ShaderNodeMapRange", (-150, -300))
        st.inputs["To Min"].default_value = strength * diffuse
        st.inputs["To Max"].default_value = strength
        _l(nt, lpd.outputs["Is Glossy Ray"], st.inputs["Value"])
        _l(nt, st.outputs["Result"], bg.inputs["Strength"])
    if bg_fn is None:
        _l(nt, bg.outputs["Background"], out.inputs["Surface"])
        return w
    lp = _n(nt, "ShaderNodeLightPath", (0, 300))
    cam_col = bg_fn(nt)
    cbg = _n(nt, "ShaderNodeBackground", (300, 250), Strength=1.0)
    _l(nt, cam_col, cbg.inputs["Color"])
    mx = _n(nt, "ShaderNodeMixShader", (700, 0))
    _l(nt, lp.outputs["Is Camera Ray"], mx.inputs["Fac"])
    _l(nt, bg.outputs["Background"], mx.inputs[1])
    _l(nt, cbg.outputs["Background"], mx.inputs[2])
    _l(nt, mx.outputs["Shader"], out.inputs["Surface"])
    return w


# ------------------------------------------------------------------ exact background colours

def _ocio_proc(look):
    import PyOpenColorIO as ocio
    cfg = ocio.GetCurrentConfig()
    p = ocio.LegacyViewingPipeline()
    p.setDisplayViewTransform(ocio.DisplayViewTransform(
        src=cfg.getColorSpace(ocio.ROLE_SCENE_LINEAR).getName(), display="sRGB", view="AgX"))
    if look:
        p.setLooksOverrideEnabled(True)
        p.setLooksOverride(look)
    return p.getProcessor(cfg).getDefaultCPUProcessor()


def hex8(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def scene_for_display(rgb8, look=None):
    """Scene-linear RGB that AgX(+look) displays as the given sRGB 8-bit colour."""
    if isinstance(rgb8, str):
        rgb8 = hex8(rgb8)
    look = look if look is not None else bpy.context.scene.view_settings.look
    look = None if look in (None, "None", "NONE") else look
    proc = _ocio_proc(look)
    tgt = [c / 255 for c in rgb8]
    x = [max(1e-4, (t ** 2.2)) for t in tgt]
    for _ in range(60):
        y = proc.applyRGB(list(x))
        for i in range(3):
            # multiplicative step in log space; display is monotonic per channel
            if y[i] > 1e-6 and tgt[i] > 0:
                x[i] *= (tgt[i] / y[i]) ** 0.8
            elif tgt[i] > 0:
                x[i] *= 2.0
            x[i] = min(max(x[i], 1e-6), 100.0)
    y = proc.applyRGB(list(x))
    print("[gr3d] bg", rgb8, "->", [round(v, 5) for v in x], "check", [round(v * 255, 1) for v in y])
    return tuple(x)


def bg_radial(center_hex, edge_hex, aspect=1.0, center=(0.5, 0.5), radius=0.75, power=1.4,
              glows=(), look=None):
    """Returns bg_fn(nt) for world_studio/world_hdri: a screen-space radial gradient in exact
    display colours plus soft additive glows [(hex_or_lin, (cx, cy), (rx, ry), strength)]."""
    c_in = scene_for_display(center_hex, look)
    c_out = scene_for_display(edge_hex, look)

    def fn(nt):
        tc = _n(nt, "ShaderNodeTexCoord", (-1600, 900))

        def ellipse_falloff(cxy, rxy, pw, y):
            sep = _n(nt, "ShaderNodeSeparateXYZ", (-1400, y))
            _l(nt, tc.outputs["Window"], sep.inputs["Vector"])
            dx = _n(nt, "ShaderNodeMath", (-1200, y + 60))
            dx.operation = "SUBTRACT"
            _l(nt, sep.outputs["X"], dx.inputs[0])
            dx.inputs[1].default_value = cxy[0]
            dy = _n(nt, "ShaderNodeMath", (-1200, y - 60))
            dy.operation = "SUBTRACT"
            _l(nt, sep.outputs["Y"], dy.inputs[0])
            dy.inputs[1].default_value = cxy[1]
            sx = _n(nt, "ShaderNodeMath", (-1050, y + 60))
            sx.operation = "DIVIDE"
            _l(nt, dx.outputs[0], sx.inputs[0])
            sx.inputs[1].default_value = rxy[0] / aspect
            sy = _n(nt, "ShaderNodeMath", (-1050, y - 60))
            sy.operation = "DIVIDE"
            _l(nt, dy.outputs[0], sy.inputs[0])
            sy.inputs[1].default_value = rxy[1]
            cv = _n(nt, "ShaderNodeCombineXYZ", (-900, y))
            _l(nt, sx.outputs[0], cv.inputs["X"])
            _l(nt, sy.outputs[0], cv.inputs["Y"])
            ln = _n(nt, "ShaderNodeVectorMath", (-750, y))
            ln.operation = "LENGTH"
            _l(nt, cv.outputs[0], ln.inputs[0])
            cl = _n(nt, "ShaderNodeMapRange", (-600, y))   # 1 at centre -> 0 at rim (clamped)
            cl.inputs["From Min"].default_value = 0.0
            cl.inputs["From Max"].default_value = 1.0
            cl.inputs["To Min"].default_value = 1.0
            cl.inputs["To Max"].default_value = 0.0
            cl.interpolation_type = "SMOOTHSTEP"
            _l(nt, ln.outputs["Value"], cl.inputs["Value"])
            pw_ = _n(nt, "ShaderNodeMath", (-450, y))
            pw_.operation = "POWER"
            _l(nt, cl.outputs["Result"], pw_.inputs[0])
            pw_.inputs[1].default_value = pw
            return pw_.outputs[0]

        f = ellipse_falloff(center, (radius, radius), power, 900)
        mix = _n(nt, "ShaderNodeMix", (-250, 900))
        mix.data_type = "RGBA"
        mix.inputs["A"].default_value = (*c_out, 1)
        mix.inputs["B"].default_value = (*c_in, 1)
        _l(nt, f, mix.inputs["Factor"])
        sock = mix.outputs["Result"]
        y = 600
        for col, cxy, rxy, k in glows:
            col = col if not isinstance(col, str) else hex_lin(col)[:3]
            gf = ellipse_falloff(cxy, rxy, 2.0, y)
            add = _n(nt, "ShaderNodeMix", (-100, y))
            add.data_type = "RGBA"
            add.blend_type = "ADD"
            _l(nt, gf, add.inputs["Factor"])
            _l(nt, sock, add.inputs["A"])
            add.inputs["B"].default_value = (col[0] * k, col[1] * k, col[2] * k, 1)
            sock = add.outputs["Result"]
            y -= 300
        return sock

    return fn


def hex_lin(h):
    h = h.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return (*out, 1.0)


def reflective_floor(name, z, size=30.0, mask_center=(0, 0), mask_radius=(4.0, 2.5), rough=0.12,
                     strength=1.0, tint=(0.02, 0.02, 0.022)):
    """Glossy black floor that only exists where it reflects: outside an elliptical mask it is
    transparent, so the screen-space background shows through seamlessly."""
    bpy.ops.mesh.primitive_plane_add(size=size)
    ob = bpy.context.object
    ob.name = name
    ob.location = (0, 0, z)
    m, nt, out = new_mat(name + "Mat")
    tc = _n(nt, "ShaderNodeTexCoord", (-1400, 0))
    sep = _n(nt, "ShaderNodeSeparateXYZ", (-1200, 0))
    _l(nt, tc.outputs["Object"], sep.inputs["Vector"])
    dx = _n(nt, "ShaderNodeMath", (-1000, 80))
    dx.operation = "SUBTRACT"
    _l(nt, sep.outputs["X"], dx.inputs[0])
    dx.inputs[1].default_value = mask_center[0]
    dy = _n(nt, "ShaderNodeMath", (-1000, -80))
    dy.operation = "SUBTRACT"
    _l(nt, sep.outputs["Y"], dy.inputs[0])
    dy.inputs[1].default_value = mask_center[1]
    sx = _n(nt, "ShaderNodeMath", (-850, 80))
    sx.operation = "DIVIDE"
    _l(nt, dx.outputs[0], sx.inputs[0])
    sx.inputs[1].default_value = mask_radius[0]
    sy = _n(nt, "ShaderNodeMath", (-850, -80))
    sy.operation = "DIVIDE"
    _l(nt, dy.outputs[0], sy.inputs[0])
    sy.inputs[1].default_value = mask_radius[1]
    cv = _n(nt, "ShaderNodeCombineXYZ", (-700, 0))
    _l(nt, sx.outputs[0], cv.inputs["X"])
    _l(nt, sy.outputs[0], cv.inputs["Y"])
    ln = _n(nt, "ShaderNodeVectorMath", (-550, 0))
    ln.operation = "LENGTH"
    _l(nt, cv.outputs[0], ln.inputs[0])
    mr = _n(nt, "ShaderNodeMapRange", (-400, 0))
    mr.inputs["From Min"].default_value = 0.0
    mr.inputs["From Max"].default_value = 1.0
    mr.inputs["To Min"].default_value = strength
    mr.inputs["To Max"].default_value = 0.0
    mr.interpolation_type = "SMOOTHERSTEP"
    _l(nt, ln.outputs["Value"], mr.inputs["Value"])
    gl = _n(nt, "ShaderNodeBsdfPrincipled", (-200, -200))
    gl.inputs["Base Color"].default_value = (*tint, 1)
    gl.inputs["Roughness"].default_value = rough
    gl.inputs["Metallic"].default_value = 0.0
    tr = _n(nt, "ShaderNodeBsdfTransparent", (-200, 200))
    mx = _n(nt, "ShaderNodeMixShader", (200, 0))
    _l(nt, mr.outputs["Result"], mx.inputs["Fac"])
    _l(nt, tr.outputs["BSDF"], mx.inputs[1])
    _l(nt, gl.outputs["BSDF"], mx.inputs[2])
    _l(nt, mx.outputs["Shader"], out.inputs["Surface"])
    ob.data.materials.append(m)
    return ob


# ------------------------------------------------------------------ geometry

def _mark_cap_edges_sharp(me, axis=2, thresh=0.995):
    """Text caps are flat: split their normals from the bevel so the face stays mirror-flat."""
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    cap = {f.index for f in bm.faces if abs(f.normal[axis]) > thresh}
    for e in bm.edges:
        fs = e.link_faces
        if len(fs) == 2 and ((fs[0].index in cap) != (fs[1].index in cap)):
            e.smooth = False
        else:
            e.smooth = True
    for f in bm.faces:
        f.smooth = True
    bm.to_mesh(me)
    bm.free()


def text(body, name=None, size=1.0, extrude=0.13, bevel=0.03, bres=4, spacing=1.0, mat=None):
    """Extruded, bevelled Saira Stencil One word standing up (faces -Y), centred on origin."""
    cu = bpy.data.curves.new(name or body, "FONT")
    cu.body = body
    cu.font = bpy.data.fonts.load(FONT, check_existing=True)
    cu.size = size
    cu.extrude = extrude
    cu.bevel_depth = bevel
    cu.bevel_resolution = bres
    cu.offset = -bevel * 0.6
    cu.space_character = spacing
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    cu.resolution_u = 32
    ob = link(bpy.data.objects.new(name or body, cu))
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.convert(target="MESH")
    ob = bpy.context.view_layer.objects.active
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=1e-5)
    bpy.ops.object.mode_set(mode="OBJECT")
    _mark_cap_edges_sharp(ob.data, axis=2)
    # stand up: text +Z normal -> -Y (towards a camera on -Y)
    ob.data.transform(Matrix.Rotation(math.radians(90), 4, "X"))
    # centre bounds
    xs = [v.co.x for v in ob.data.vertices]
    zs = [v.co.z for v in ob.data.vertices]
    ob.data.transform(Matrix.Translation((-(min(xs) + max(xs)) / 2, 0, -(min(zs) + max(zs)) / 2)))
    if mat:
        ob.data.materials.append(mat)
    return ob


def dims(ob):
    vs = [ob.matrix_world @ v.co for v in ob.data.vertices]
    return (Vector((min(v.x for v in vs), min(v.y for v in vs), min(v.z for v in vs))),
            Vector((max(v.x for v in vs), max(v.y for v in vs), max(v.z for v in vs))))


def nugget(name="Nugget", seed=1, size=1.0, subdiv=6, elong=(1.25, 0.95, 0.8), lobe=0.22, cells=1.5,
           crease_amt=0.07, mat=None):
    """Organic gold-nugget lump: fused blobs (voronoi cells), creases, fine grain."""
    rnd = random.Random(seed)
    off = Vector((rnd.uniform(-50, 50), rnd.uniform(-50, 50), rnd.uniform(-50, 50)))
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0)
    for v in bm.verts:
        d = v.co.normalized()
        lobes = noise.fractal(d * 0.9 + off, 1.0, 2.0, 3, noise_basis="PERLIN_NEW")
        dist, _pts = noise.voronoi(d * cells + off * 0.37, distance_metric="DISTANCE", exponent=2.0)
        f1, f2 = dist[0], dist[1]
        crease = math.exp(-((f2 - f1) * 5.0) ** 2)
        blob = max(0.0, 1.0 - f1 * 1.2) ** 1.5
        fine = noise.fractal(d * 4.5 + off, 0.9, 2.1, 3, noise_basis="PERLIN_NEW")
        r = 1.0 + lobe * lobes + 0.07 * blob - crease_amt * crease + 0.012 * fine
        v.co = Vector((d.x * elong[0], d.y * elong[1], d.z * elong[2])) * r * size
    for f in bm.faces:
        f.smooth = True
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = link(bpy.data.objects.new(name, me))
    if mat:
        me.materials.append(mat)
    return ob


def nugget2(name="Nugget", seed=1, size=1.0, blobs=9, knobs=7, spread=(0.5, 0.36, 0.26), voxel=0.012,
            pits=0.035, crease=0.03, mat=None):
    """Hero nugget: fused metaball lobes (how real nuggets look) -> voxel remesh ->
    pitted / creased surface displaced along normals. ~1 unit across before `size`."""
    rnd = random.Random(seed)
    mb = bpy.data.metaballs.new(name + "_mb")
    mb.resolution = 0.03
    mb.render_resolution = 0.02
    mb.threshold = 0.6
    core = mb.elements.new()
    core.co = (0, 0, 0)
    core.radius = 0.55
    core.type = "ELLIPSOID"
    core.size_x, core.size_y, core.size_z = 0.42, 0.28, 0.22
    for i in range(blobs):
        e = mb.elements.new()
        e.type = "BALL" if rnd.random() < 0.6 else "ELLIPSOID"
        e.co = (rnd.gauss(0, spread[0] * 0.45), rnd.gauss(0, spread[1] * 0.45), rnd.gauss(0, spread[2] * 0.45))
        e.radius = rnd.uniform(0.3, 0.48)
        if e.type == "ELLIPSOID":
            e.size_x, e.size_y, e.size_z = rnd.uniform(0.12, 0.3), rnd.uniform(0.1, 0.22), rnd.uniform(0.08, 0.18)
        e.stiffness = rnd.uniform(1.5, 2.6)
    for i in range(knobs):   # small knobs fused onto the surface
        e = mb.elements.new()
        e.type = "BALL"
        d = Vector((rnd.gauss(0, 1), rnd.gauss(0, 1), rnd.gauss(0, 0.7))).normalized()
        e.co = Vector((d.x * spread[0], d.y * spread[1], d.z * spread[2])) * rnd.uniform(0.85, 1.25)
        e.radius = rnd.uniform(0.14, 0.24)
        e.stiffness = rnd.uniform(2.0, 3.0)
    ob = link(bpy.data.objects.new(name, mb))
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.convert(target="MESH")
    ob = bpy.context.view_layer.objects.active
    ob.name = name
    rm = ob.modifiers.new("Remesh", "REMESH")
    rm.mode = "VOXEL"
    rm.voxel_size = voxel
    bpy.ops.object.modifier_apply(modifier=rm.name)
    # normalise size: longest bbox side -> 1
    xs = [v.co for v in ob.data.vertices]
    lo = Vector((min(v.x for v in xs), min(v.y for v in xs), min(v.z for v in xs)))
    hi = Vector((max(v.x for v in xs), max(v.y for v in xs), max(v.z for v in xs)))
    c = (lo + hi) / 2
    k = 1.0 / max(hi - lo)
    ob.data.transform(Matrix.Scale(k, 4) @ Matrix.Translation(-c))
    # keep only the biggest connected lump (stray metaball islands look like dust)
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    seen, islands = set(), []
    for v0 in bm.verts:
        if v0.index in seen:
            continue
        stack, isl = [v0], []
        seen.add(v0.index)
        while stack:
            v = stack.pop()
            isl.append(v)
            for e in v.link_edges:
                w = e.other_vert(v)
                if w.index not in seen:
                    seen.add(w.index)
                    stack.append(w)
        islands.append(isl)
    islands.sort(key=len, reverse=True)
    for isl in islands[1:]:
        bmesh.ops.delete(bm, geom=isl, context="VERTS")
    bm.to_mesh(ob.data)
    bm.free()
    # displace along the ORIGINAL normals (read them all first: touching co dirties the cache)
    off = Vector((rnd.uniform(-90, 90), rnd.uniform(-90, 90), rnd.uniform(-90, 90)))
    me = ob.data
    me.update()
    normals = [v.normal.copy() for v in me.vertices]
    cos = [v.co.copy() for v in me.vertices]
    for v, p, n in zip(me.vertices, cos, normals):
        q = p + Vector((noise.noise(p * 5 + off), noise.noise(p * 5 + off * 2), noise.noise(p * 5 + off * 3))) * 0.06
        dist, _ = noise.voronoi(q * 6.0 + off, distance_metric="DISTANCE", exponent=2.0)
        pit = max(0.0, 1.0 - dist[0] / 0.33) ** 2.6          # irregular dimples
        pit *= 0.4 + 0.6 * max(0.0, noise.noise(p * 3.0 - off, noise_basis="PERLIN_NEW") + 0.4)
        dist2, _ = noise.voronoi(p * 3.2 + off * 1.3, distance_metric="DISTANCE", exponent=2.0)
        cr = math.exp(-((dist2[1] - dist2[0]) * 9.0) ** 2)    # creases between lobes
        cmask = noise.noise(p * 2.0 + off * 0.7, noise_basis="PERLIN_NEW")
        cr *= min(1.0, max(0.0, (cmask + 0.1) * 2.5))        # only some creases survive
        grain = noise.fractal(p * 16.0 + off, 0.8, 2.0, 4, noise_basis="PERLIN_NEW")
        warp = noise.fractal(p * 2.2 + off * 0.5, 1.0, 2.0, 2, noise_basis="PERLIN_NEW")
        d = -pits * pit - crease * cr + 0.006 * grain + 0.03 * warp
        v.co = p + n * d
    ob.data.transform(Matrix.Scale(size, 4))
    for f in me.polygons:
        f.use_smooth = True
    if mat:
        me.materials.append(mat)
    return ob


def rock_mat(name="Rock", flecks=True, dark=(0.010, 0.009, 0.008), light=(0.05, 0.042, 0.034), spec=0.3):
    """Dark mine rock (grey-brown, faceted feel) with sparse gold flecks that glint."""
    m, nt, out = new_mat(name)
    tc = _n(nt, "ShaderNodeTexCoord", (-1500, 0))
    nz = _n(nt, "ShaderNodeTexNoise", (-1250, 200), Scale=3.0, Detail=8.0, Roughness=0.6)
    _l(nt, tc.outputs["Object"], nz.inputs["Vector"])
    cr = _n(nt, "ShaderNodeValToRGB", (-1000, 200))
    cr.color_ramp.elements[0].color = (*dark, 1)
    cr.color_ramp.elements[1].color = (*light, 1)
    cr.color_ramp.elements[0].position = 0.35
    cr.color_ramp.elements[1].position = 0.7
    _l(nt, nz.outputs["Fac"], cr.inputs["Fac"])
    nz2 = _n(nt, "ShaderNodeTexNoise", (-1250, -200), Scale=18.0, Detail=10.0, Roughness=0.65)
    _l(nt, tc.outputs["Object"], nz2.inputs["Vector"])
    bp = _n(nt, "ShaderNodeBump", (-700, -200), Strength=0.45, Distance=0.03)
    _l(nt, nz2.outputs["Fac"], bp.inputs["Height"])
    rr = _n(nt, "ShaderNodeMapRange", (-700, 0))
    rr.inputs["To Min"].default_value = 0.55
    rr.inputs["To Max"].default_value = 0.85
    _l(nt, nz2.outputs["Fac"], rr.inputs["Value"])
    rock = _n(nt, "ShaderNodeBsdfPrincipled", (-300, 200))
    rock.inputs["Specular IOR Level"].default_value = spec
    _l(nt, cr.outputs["Color"], rock.inputs["Base Color"])
    _l(nt, rr.outputs["Result"], rock.inputs["Roughness"])
    _l(nt, bp.outputs["Normal"], rock.inputs["Normal"])
    if not flecks:
        _l(nt, rock.outputs["BSDF"], out.inputs["Surface"])
        return m
    vor = _n(nt, "ShaderNodeTexVoronoi", (-1250, -500), Scale=26.0, Randomness=1.0)
    _l(nt, tc.outputs["Object"], vor.inputs["Vector"])
    fm = _n(nt, "ShaderNodeMapRange", (-1000, -500))     # tiny specks at cell centres
    fm.inputs["From Min"].default_value = 0.06
    fm.inputs["From Max"].default_value = 0.035
    _l(nt, vor.outputs["Distance"], fm.inputs["Value"])
    sel = _n(nt, "ShaderNodeMath", (-850, -650))          # only some cells carry gold
    sel.operation = "GREATER_THAN"
    _l(nt, vor.outputs["Color"], sel.inputs[0])
    sel.inputs[1].default_value = 0.82
    fk = _n(nt, "ShaderNodeMath", (-700, -550))
    fk.operation = "MULTIPLY"
    _l(nt, fm.outputs["Result"], fk.inputs[0])
    _l(nt, sel.outputs[0], fk.inputs[1])
    gold = _n(nt, "ShaderNodeBsdfPrincipled", (-300, -300))
    gold.inputs["Base Color"].default_value = (1.0, 0.69, 0.17, 1)
    gold.inputs["Metallic"].default_value = 1.0
    gold.inputs["Roughness"].default_value = 0.2
    mx = _n(nt, "ShaderNodeMixShader", (100, 0))
    _l(nt, fk.outputs[0], mx.inputs["Fac"])
    _l(nt, rock.outputs["BSDF"], mx.inputs[1])
    _l(nt, gold.outputs["BSDF"], mx.inputs[2])
    _l(nt, mx.outputs["Shader"], out.inputs["Surface"])
    return m


def rock(name="Rock", seed=1, size=1.0, subdiv=3, flat=True, squash=0.6, mat=None):
    """Faceted low-poly-ish boulder (matches the game's look)."""
    rnd = random.Random(seed)
    off = Vector((rnd.uniform(-80, 80), rnd.uniform(-80, 80), rnd.uniform(-80, 80)))
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0)
    el = (rnd.uniform(0.9, 1.4), rnd.uniform(0.8, 1.2), squash * rnd.uniform(0.8, 1.2))
    for v in bm.verts:
        d = v.co.normalized()
        r = 1.0 + 0.32 * noise.fractal(d * 1.2 + off, 1.0, 2.0, 3, noise_basis="PERLIN_NEW")
        v.co = Vector((d.x * el[0], d.y * el[1], d.z * el[2])) * r * size
    for f in bm.faces:
        f.smooth = not flat
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = link(bpy.data.objects.new(name, me))
    if mat:
        me.materials.append(mat)
    return ob


def pickaxe(name="Pickaxe", head_mat=None, handle_mat=None, band_mat=None, length=2.6, span=2.2):
    """Pickaxe lying in the XZ plane: handle along +Z, curved head across X at the top.
    Origin at the handle bottom. Returns the parent empty (children = parts)."""
    root = link(bpy.data.objects.new(name, None))
    # --- head: swept tapered tube bent downward, spike one side, chisel the other
    segs, sides = 96, 24
    bm = bmesh.new()
    rings = []
    half = span / 2
    for i in range(segs + 1):
        t = i / segs * 2 - 1                    # -1..1
        x = t * half
        bend = -0.32 * (t * t)                   # tips droop
        a = abs(t)
        if t < 0:   # spike
            r = 0.105 * (max(0.0, 1 - a) ** 0.55) + 0.004
            sy, sz = 1.0, 1.0
        else:       # chisel: flattens into a blade
            r = 0.105 * (max(0.0, 1 - a * 0.92) ** 0.35) + 0.004
            sy, sz = 1.0 + 0.9 * a ** 1.5, max(0.18, 1.0 - 0.85 * a ** 1.2)
        r *= 1.0 + 0.35 * math.exp(-(t / 0.12) ** 2)   # swell at the eye
        ang_t = math.atan2(-0.64 * t * half, half)       # tangent tilt of the droop
        ring = []
        for k in range(sides):
            th = k / sides * 2 * math.pi
            ly, lz = math.cos(th) * r * sy, math.sin(th) * r * sz
            # rotate the ring's local z by the droop tangent
            px = x - math.sin(ang_t) * lz
            pz = bend + math.cos(ang_t) * lz
            ring.append(bm.verts.new((px, ly, pz)))
        rings.append(ring)
    for i in range(segs):
        a, b = rings[i], rings[i + 1]
        for k in range(sides):
            bm.faces.new((a[k], a[(k + 1) % sides], b[(k + 1) % sides], b[k]))
    for ring in (rings[0], rings[-1]):
        bm.faces.new(ring if ring is rings[-1] else list(reversed(ring)))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        f.smooth = True
    me = bpy.data.meshes.new(name + "_head")
    bm.to_mesh(me)
    bm.free()
    head = link(bpy.data.objects.new(name + "_head", me))
    head.location = (0, 0, length - 0.02)
    if head_mat:
        me.materials.append(head_mat)
    head.parent = root
    # eye collar
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.115, depth=0.36)
    eye = bpy.context.object
    eye.name = name + "_eye"
    eye.location = (0, 0, length - 0.08)
    m = eye.modifiers.new("b", "BEVEL")
    m.width, m.segments = 0.025, 3
    eye.data.shade_smooth()
    if head_mat:
        eye.data.materials.append(head_mat)
    eye.parent = root
    # handle: slightly tapered, flared butt
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=32, radius1=0.072, radius2=0.058, depth=length)
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, length / 2))
    for f in bm.faces:
        f.smooth = True
    me = bpy.data.meshes.new(name + "_handle")
    bm.to_mesh(me)
    bm.free()
    handle = link(bpy.data.objects.new(name + "_handle", me))
    m = handle.modifiers.new("b", "BEVEL")
    m.width, m.segments = 0.02, 3
    if handle_mat:
        me.materials.append(handle_mat)
    handle.parent = root
    # butt knob + grip band
    for z, h, r in ((0.0, 0.09, 0.085), (0.32, 0.26, 0.078)):
        bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=r, depth=h)
        o = bpy.context.object
        o.location = (0, 0, z + h / 2)
        mm = o.modifiers.new("b", "BEVEL")
        mm.width, mm.segments = 0.015, 3
        o.data.shade_smooth()
        if band_mat:
            o.data.materials.append(band_mat)
        o.parent = root
    return root


def glint_mat(name="Glint", color=(1.0, 0.9, 0.7), strength=40.0, power=2.5):
    """Emission that fades from the sprite centre to its tips (generated coords)."""
    m, nt, out = new_mat(name)
    tc = _n(nt, "ShaderNodeTexCoord", (-900, 0))
    sub = _n(nt, "ShaderNodeVectorMath", (-700, 0))
    sub.operation = "SUBTRACT"
    _l(nt, tc.outputs["Generated"], sub.inputs[0])
    sub.inputs[1].default_value = (0.5, 0.5, 0.5)
    ln = _n(nt, "ShaderNodeVectorMath", (-550, 0))
    ln.operation = "LENGTH"
    _l(nt, sub.outputs["Vector"], ln.inputs[0])
    mr = _n(nt, "ShaderNodeMapRange", (-400, 0))
    mr.inputs["From Min"].default_value = 0.0
    mr.inputs["From Max"].default_value = 0.5
    mr.inputs["To Min"].default_value = 1.0
    mr.inputs["To Max"].default_value = 0.0
    _l(nt, ln.outputs["Value"], mr.inputs["Value"])
    pw = _n(nt, "ShaderNodeMath", (-250, 0))
    pw.operation = "POWER"
    _l(nt, mr.outputs["Result"], pw.inputs[0])
    pw.inputs[1].default_value = power
    mul = _n(nt, "ShaderNodeMath", (-100, 0))
    mul.operation = "MULTIPLY"
    _l(nt, pw.outputs[0], mul.inputs[0])
    mul.inputs[1].default_value = strength
    e = _n(nt, "ShaderNodeEmission", (100, 0))
    e.inputs["Color"].default_value = (*color, 1)
    _l(nt, mul.outputs[0], e.inputs["Strength"])
    tr = _n(nt, "ShaderNodeBsdfTransparent", (100, 200))
    add = _n(nt, "ShaderNodeAddShader", (300, 0))
    _l(nt, tr.outputs["BSDF"], add.inputs[0])
    _l(nt, e.outputs["Emission"], add.inputs[1])
    _l(nt, add.outputs["Shader"], out.inputs["Surface"])
    return m


def glint(name, loc, size, cam, mat):
    """Classic 4-point sparkle + a smaller diagonal star behind it."""
    a = star_sprite(name, loc, size, cam, mat, rot=0.0)
    b = star_sprite(name + "_x", loc, size * 0.42, cam, mat, rot=math.pi / 4)
    return a, b


def screen_hit(cam, obj, u, v):
    """World point where the camera ray through normalised frame coords (u, v) hits obj."""
    scene = bpy.context.scene
    fr = cam.data.view_frame(scene=scene)        # local corners: tr, br, bl, tl
    tr, br, bl, tl = fr
    local = bl + (br - bl) * u + (tl - bl) * v
    mw = cam.matrix_world
    origin = mw.translation
    d = (mw @ local - origin).normalized()
    inv = obj.matrix_world.inverted()
    o_l = inv @ origin
    d_l = (inv.to_3x3() @ d).normalized()
    ok, loc, nrm, _ = obj.ray_cast(o_l, d_l)
    return (obj.matrix_world @ loc) if ok else None


def star_sprite(name, loc, size, cam, mat, rays=4, rot=0.0):
    """Flat camera-facing glint: thin spikes + core. For sparkle accents."""
    bm = bmesh.new()
    c = bm.verts.new((0, 0, 0))
    n = rays * 2
    ring = []
    for i in range(n):
        a = rot + i / n * 2 * math.pi
        r = size if i % 2 == 0 else size * 0.05
        if rays == 4 and i % 4 == 2:
            r = size * 0.7
        ring.append(bm.verts.new((math.cos(a) * r, math.sin(a) * r, 0)))
    for i in range(n):
        bm.faces.new((c, ring[i], ring[(i + 1) % n]))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = link(bpy.data.objects.new(name, me))
    ob.location = loc
    d = (cam.location - Vector(loc)).normalized()
    ob.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    me.materials.append(mat)
    ob.visible_shadow = False
    ob.visible_diffuse = False
    ob.visible_glossy = False
    return ob


# ------------------------------------------------------------------ lights / camera

def area(name, loc, target, size=(2, 2), energy=500, color=(1, 1, 1), spread=180, glossy=True):
    li = bpy.data.lights.new(name, "AREA")
    li.shape = "RECTANGLE"
    li.size, li.size_y = size
    li.energy = energy
    li.color = color
    li.spread = math.radians(spread)
    ob = link(bpy.data.objects.new(name, li))
    ob.location = loc
    look_at(ob, Vector(target))
    ob.visible_glossy = glossy
    return ob


def card(name, loc, target, size=(4, 2), mat=None, camera_visible=False):
    """Emission mesh card (shows in reflections as a real softbox)."""
    bpy.ops.mesh.primitive_plane_add(size=1)
    ob = bpy.context.object
    ob.name = name
    ob.scale = (size[0], size[1], 1)
    ob.location = loc
    look_at(ob, Vector(target), track="Z")
    ob.visible_camera = camera_visible
    ob.visible_shadow = False
    if mat:
        ob.data.materials.append(mat)
    return ob


def look_at(ob, target, track="-Z"):
    d = Vector(target) - ob.location
    if track == "Z":   # plane normal faces target
        ob.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    else:
        ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def camera(lens=85, sensor=36):
    cd = bpy.data.cameras.new("Cam")
    cd.lens = lens
    cd.sensor_width = sensor
    cam = link(bpy.data.objects.new("Cam", cd))
    bpy.context.scene.camera = cam
    return cam


def _points(objs, step=7):
    dg = bpy.context.evaluated_depsgraph_get()
    pts = []
    for o in objs:
        if o.type != "MESH":
            continue
        e = o.evaluated_get(dg)
        me = e.to_mesh()
        mw = o.matrix_world
        vs = me.vertices
        for i in range(0, len(vs), step):
            pts.append(mw @ vs[i].co)
        e.to_mesh_clear()
    return pts


def fit(cam, objs, target, direction, margin=(0.08, 0.08), center=(0.5, 0.5), iters=7):
    """Place cam along `direction` from `target` so `objs` fill the frame minus margins,
    then shift the lens so their bbox centre lands on `center` (normalised frame coords)."""
    scene = bpy.context.scene
    bpy.context.view_layer.update()
    pts = _points(objs)
    direction = Vector(direction).normalized()
    target = Vector(target)
    W, H = scene.render.resolution_x, scene.render.resolution_y
    dist = 10.0
    cam.data.shift_x = cam.data.shift_y = 0.0
    for _ in range(iters):
        cam.location = target + direction * dist
        look_at(cam, target)
        bpy.context.view_layer.update()
        co = [world_to_camera_view(scene, cam, p) for p in pts]
        x0, x1 = min(c.x for c in co), max(c.x for c in co)
        y0, y1 = min(c.y for c in co), max(c.y for c in co)
        need = max((x1 - x0) / (1 - 2 * margin[0]), (y1 - y0) / (1 - 2 * margin[1]))
        dist *= need
        # recentre via shift (shift is in units of the larger frame dimension)
        big = max(W, H)
        cam.data.shift_x += ((x0 + x1) / 2 - center[0]) * W / big
        cam.data.shift_y += ((y0 + y1) / 2 - center[1]) * H / big
    bpy.context.view_layer.update()
    co = [world_to_camera_view(scene, cam, p) for p in pts]
    bb = (min(c.x for c in co), min(c.y for c in co), max(c.x for c in co), max(c.y for c in co))
    print("[gr3d] fit bbox (ndc):", tuple(round(v, 3) for v in bb), "dist", round(dist, 2))
    return bb
