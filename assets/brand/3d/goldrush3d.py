"""GoldRush 3D brand renders.

    bl goldrush3d.py -- <variant> [--res N] [--samples N] [--out path.png] [--layout stack|line] [--blend]

variants: logo (transparent), logo-dark, icon, banner
"""
import math
import os
import random
import sys

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gr3d as g  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")


def argv():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    opts = {"variant": a[0] if a else "logo"}
    i = 1
    while i < len(a):
        k = a[i].lstrip("-")
        if k == "blend":
            opts["blend"] = True
            i += 1
            continue
        opts[k] = a[i + 1]
        i += 2
    return opts


# ------------------------------------------------------------------ shared logo build

def parent_all(objs, name="Logo"):
    root = g.link(bpy.data.objects.new(name, None))
    for o in objs:
        if o.parent is None:
            o.parent = root
    return root


OPTS = {}


def o_get(k, d):
    return OPTS.get(k, d)


def build_logo(layout="stack", pick=True, tilt=10.0):
    gold = g.gold_polished()
    ngold = g.gold_nugget()
    letters = []
    if layout == "stack":
        top = g.text("GOLD", extrude=0.15, bevel=0.034, mat=gold)
        bot = g.text("RUSH", extrude=0.15, bevel=0.034, mat=gold)
        W = 3.2
        for ob in (top, bot):
            lo, hi = g.dims(ob)
            s = W / (hi.x - lo.x)
            ob.scale = (s, s, s)
        bpy.context.view_layer.update()
        ht = g.dims(top)[1].z - g.dims(top)[0].z
        hb = g.dims(bot)[1].z - g.dims(bot)[0].z
        gap = 0.17
        top.location.z = gap / 2 + ht / 2
        bot.location.z = -gap / 2 - hb / 2
        letters = [top, bot]
    else:
        word = g.text("GOLDRUSH", extrude=0.15, bevel=0.034, mat=gold)
        lo, hi = g.dims(word)
        s = 5.0 / (hi.x - lo.x)
        word.scale = (s, s, s)
        letters = [word]
    bpy.context.view_layer.update()
    lo = Vector((min(g.dims(o)[0].x for o in letters), 0, min(g.dims(o)[0].z for o in letters)))
    hi = Vector((max(g.dims(o)[1].x for o in letters), 0, max(g.dims(o)[1].z for o in letters)))

    parts = list(letters)
    if pick:
        steel = g.steel()
        wood = g.wood()
        L = 3.5
        for side in (-1, 1):
            pk = g.pickaxe(f"Pick{side:+d}", head_mat=steel, handle_mat=wood, band_mat=gold,
                           length=L, span=2.1)
            ang = math.radians(40)
            head = Vector((side * 1.25, 0.42, hi.z + 0.38))
            pk.rotation_euler = (0, side * ang, 0)
            pk.scale = (side, 1, 1)          # mirror so the spikes point inward/up on both
            pk.location = head - Vector((side * math.sin(ang), 0, math.cos(ang))) * L
            pk.location.y = 0.42 + 0.06 * side
            parts += list(pk.children)
    n1 = g.nugget2("NuggetA", seed=int(o_get("n1seed", 21)), size=1.05, mat=ngold)
    n1.scale = (1, 1, 0.8)
    n1.location = (0.05, -0.55, lo.z - 0.32)
    n1.rotation_euler = (0, 0, math.radians(float(o_get("n1rz", -20))))
    n2 = g.nugget2("NuggetB", seed=int(o_get("n2seed", 33)), size=0.5, knobs=2, voxel=0.018, mat=ngold)
    n2.location = (-0.68, -0.45, lo.z - 0.33)
    n2.rotation_euler = (math.radians(-10), math.radians(25), math.radians(-40))
    n3 = g.nugget2("NuggetC", seed=int(o_get("n3seed", 12)), size=0.4, knobs=2, voxel=0.018, mat=ngold)
    n3.location = (0.72, -0.5, lo.z - 0.36)
    n3.rotation_euler = (math.radians(30), math.radians(10), math.radians(70))
    parts += [n1, n2, n3]
    root = parent_all([o for o in bpy.context.scene.objects if o.parent is None and o.type in {"MESH", "EMPTY"}])
    root.rotation_euler.x = math.radians(-tilt)    # lean back: faces mirror the bright upper dome
    bpy.context.view_layer.update()
    return parts, (lo, hi)


STUDIO_STOPS = [
    (-1.0, (0.004, 0.0026, 0.0012)),
    (-0.1, (0.010, 0.0065, 0.003)),
    (0.08, (0.035, 0.023, 0.010)),
    (0.22, (0.42, 0.26, 0.09)),
    (0.42, (1.6, 1.15, 0.5)),
    (1.0, (1.2, 1.0, 0.7)),
]


def studio(cam, target, o, bg_fn=None):
    g.world_studio(STUDIO_STOPS, hdri_mix=float(o.get("hmix", 0.35)), rot_z=float(o.get("hrot", 140)),
                   strength=float(o.get("world", 1.0)), bg_fn=bg_fn,
                   backdrop=float(o.get("backdrop", 1.0)), backdrop_top=float(o.get("btop", 0.3)))
    t = Vector(target)
    key, rim, top = float(o.get("key", 1800)), float(o.get("rim", 1600)), float(o.get("top", 900))
    g.area("Key", t + Vector((-5, -5, 5.5)), t, size=(3.5, 3.5), energy=key, color=(1.0, 0.9, 0.78))
    g.area("Fill", t + Vector((6, -4, 1.0)), t, size=(3, 5), energy=key * 0.25, color=(1.0, 0.95, 0.9))
    g.area("RimL", t + Vector((-6, 4, 2)), t, size=(0.6, 6), energy=rim, color=(1.0, 0.88, 0.7))
    g.area("RimR", t + Vector((6, 4, 2)), t, size=(0.6, 6), energy=rim, color=(1.0, 0.88, 0.7))
    g.area("Top", t + Vector((0, -1, 6)), t, size=(8, 0.8), energy=top, color=(1.0, 0.95, 0.88))
    bounce = float(o.get("bounce", 0))
    if bounce > 0:   # warm floor bounce so undersides mirror gold light, not black
        g.area("Bounce", t + Vector((0.5, -4.5, -3.2)), t, size=(7, 2.2), energy=bounce, color=(1.0, 0.78, 0.45))


def cam_dir(az, el):
    a, e = math.radians(az), math.radians(el)
    return Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))


def world_min_z(parts):
    return min(p.z for p in g._points(parts, step=3))


def variant_logo(o, dark=False):
    res = int(o.get("res", 2048))
    layout = o.get("layout", "stack")
    pick = o.get("pick", "1") == "1"
    look = o.get("look", "AgX - Punchy")
    g.reset()
    g.cycles((res, res), samples=int(o.get("samples", 384)), transparent=not dark, look=look)
    parts, (lo, hi) = build_logo(layout, pick, tilt=float(o.get("tilt", 10)))
    cam = g.camera(lens=70)
    target = Vector((0, 0, (lo.z + hi.z) / 2 - 0.1))
    if dark:
        # leave room under the logo for its reflection
        g.fit(cam, parts, target, cam_dir(float(o.get("az", 10)), float(o.get("el", 8))),
              margin=(0.1, 0.13), center=(0.5, 0.545))
    else:
        g.fit(cam, parts, target, cam_dir(float(o.get("az", 10)), float(o.get("el", 8))),
              margin=(0.06, 0.06))
    bg_fn = None
    if dark:
        zf = world_min_z(parts)
        g.reflective_floor("Floor", zf + 0.004, mask_center=(0, -0.3), mask_radius=(4.2, 2.4),
                           rough=float(o.get("frough", 0.14)), strength=float(o.get("fstr", 0.9)))
        bg_fn = g.bg_radial("#171a1f", "#0c0d10", center=(0.5, 0.56), radius=0.78, power=1.2,
                            glows=[((0.10, 0.052, 0.012), (0.5, 0.22), (0.42, 0.14), float(o.get("glow", 1.0))),
                                   ((0.020, 0.012, 0.004), (0.5, 0.52), (0.55, 0.45), float(o.get("glow", 1.0)))],
                            look=look)
    studio(cam, target, o, bg_fn=bg_fn)
    name = "goldrush-3d-logo-dark" if dark else "goldrush-3d-logo"
    out = o.get("out") or os.path.join(OUT, name + ".png")
    if o.get("blend"):
        g.save_blend(os.path.join(HERE, name + ".blend"))
    g.render(out)


def variant_logo_dark(o):
    variant_logo(o, dark=True)


def variant_icon(o):
    res = int(o.get("res", 2048))
    look = o.get("look", "AgX - Punchy")
    g.reset()
    g.cycles((res, res), samples=int(o.get("samples", 512)), transparent=False, look=look)
    ngold = g.gold_nugget()
    nug = g.nugget2("HeroNugget", seed=int(o.get("seed", 4)), size=2.0, mat=ngold)
    nug.rotation_euler = (math.radians(float(o.get("rx", 8))), math.radians(float(o.get("ry", -10))),
                          math.radians(float(o.get("rz", 25))))
    bpy.context.view_layer.update()
    cam = g.camera(lens=85)
    target = Vector((0, 0, 0))
    m = float(o.get("margin", 0.13))
    g.fit(cam, [nug], target, cam_dir(float(o.get("az", 18)), float(o.get("el", 20))), margin=(m, m))
    bg_fn = g.bg_radial("#1a1d23", "#0c0d10", center=(0.5, 0.52), radius=0.72, power=1.1,
                        glows=[((0.12, 0.06, 0.014), (0.5, 0.5), (0.5, 0.5), float(o.get("glow", 1.0)))],
                        look=look)
    studio(cam, target, o, bg_fn=bg_fn)
    bpy.context.view_layer.update()
    gm = g.glint_mat(strength=float(o.get("glint", 60)))
    for i, (u, v, sz) in enumerate([(0.37, 0.71, 0.32), (0.68, 0.62, 0.2)][:int(o.get("glints", 2))]):
        hp = g.screen_hit(cam, nug, u, v)
        if hp is not None:
            hp = hp + (cam.location - hp).normalized() * 0.08
            g.glint(f"Glint{i}", hp, sz, cam, gm)
    out = o.get("out") or os.path.join(OUT, "goldrush-3d-icon.png")
    if o.get("blend"):
        g.save_blend(os.path.join(HERE, "goldrush-3d-icon.blend"))
    g.render(out)


def ground_h(x, y):
    from mathutils import noise as nz
    h = 0.28 * nz.fractal(Vector((x * 0.2, y * 0.2, 0.5)), 1.0, 2.0, 4, noise_basis="PERLIN_NEW")
    h += 0.05 * nz.fractal(Vector((x * 1.4, y * 1.4, 3.3)), 0.8, 2.0, 3, noise_basis="PERLIN_NEW")
    if y > 3.0:
        h += (y - 3.0) ** 1.4 * 0.12       # ground rises into the back slope
    return h


def ground_mesh(name, x0, x1, y0, y1, step, mat):
    import bmesh as bmm
    bm = bmm.new()
    nx, ny = int((x1 - x0) / step), int((y1 - y0) / step)
    rows = []
    for j in range(ny + 1):
        y = y0 + j * step
        rows.append([bm.verts.new((x0 + i * step, y, ground_h(x0 + i * step, y))) for i in range(nx + 1)])
    for j in range(ny):
        for i in range(nx):
            bm.faces.new((rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i]))
    for f in bm.faces:
        f.smooth = True
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = g.link(bpy.data.objects.new(name, me))
    me.materials.append(mat)
    return ob


def variant_banner(o):
    W, H = (int(v) for v in o.get("res", "3000x1000").split("x"))
    look = o.get("look", "AgX - Punchy")
    rnd = random.Random(int(o.get("seed", 7)))
    g.reset()
    g.cycles((W, H), samples=int(o.get("samples", 384)), transparent=False, look=look)
    gold = g.gold_polished()
    ngold = g.gold_nugget()
    rockm = g.rock_mat()
    groundm = g.rock_mat("Ground", dark=(0.004, 0.0038, 0.0036), light=(0.02, 0.017, 0.014), spec=0.15)
    gb = groundm.node_tree.nodes.get("Bump")
    if gb:
        gb.inputs["Strength"].default_value = 0.8

    # --- letters: one line, leaning back on the rubble
    word = g.text("GOLDRUSH", extrude=0.16, bevel=0.036, mat=gold)
    lo, hi = g.dims(word)
    sc = 6.4 / (hi.x - lo.x)
    word.scale = (sc, sc, sc)
    bpy.context.view_layer.update()
    lo, hi = g.dims(word)
    hgt = hi.z - lo.z
    base = max(ground_h(x, 0.0) for x in (-3, -2, -1, 0, 1, 2, 3))
    tilt = math.radians(float(o.get("tilt", 12)))
    word.rotation_euler.x = -tilt
    word.location = (0, 0.0, base - 0.12 + hgt / 2 * math.cos(tilt))
    bpy.context.view_layer.update()

    ground_mesh("Ground", -18, 18, -7, 16, float(o.get("gstep", 0.07)), groundm)

    # --- camera
    cam = g.camera(lens=float(o.get("lens", 50)))
    target = Vector((0, 0, word.location.z))
    g.fit(cam, [word], target, cam_dir(float(o.get("az", 4)), float(o.get("el", 9))),
          margin=(float(o.get("mx", 0.2)), 0.0), center=(0.5, float(o.get("cy", 0.53))))
    cd = cam.data
    cd.dof.use_dof = True
    cd.dof.focus_distance = (cam.location - Vector((0, -0.2, word.location.z))).length
    cd.dof.aperture_fstop = float(o.get("fstop", 1.2))

    # --- rubble: faceted rocks, bigger toward the edges and back
    for i in range(int(o.get("rocks", 70))):
        x = rnd.uniform(-13, 13)
        y = rnd.uniform(-3.5, 10)
        if abs(x) < 3.6 and -0.9 < y < 0.9:
            continue  # keep the letter faces clear
        edge = min(1.0, abs(x) / 9 + max(0.0, y) / 12)
        sz = rnd.uniform(0.08, 0.28) + edge * rnd.uniform(0.0, 0.8)
        r = g.rock(f"Rock{i}", seed=rnd.randint(0, 9999), size=sz, mat=rockm)
        r.location = (x, y, ground_h(x, y) + sz * 0.15)
        r.rotation_euler = (rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3), rnd.uniform(0, 6.28))
    # gravel: instanced chips everywhere (reads as a mine floor, not sand)
    chips = [g.rock(f"Chip{k}", seed=500 + k, size=1.0, subdiv=2, mat=rockm) for k in range(6)]
    for c in chips:
        c.hide_render = c.hide_viewport = True
    for i in range(int(o.get("gravel", 2600))):
        x = rnd.uniform(-14, 14)
        y = rnd.uniform(-5, 13)
        if abs(x) < 3.3 and -0.5 < y < 0.5:
            continue
        sz = (0.012 + 0.11 * rnd.random() ** 3.0) * (1 + max(0.0, y) / 8)
        ob = bpy.data.objects.new(f"Gravel{i}", chips[i % 6].data)
        g.link(ob)
        ob.scale = (sz, sz, sz)
        ob.rotation_euler = (rnd.uniform(-0.5, 0.5), rnd.uniform(-0.5, 0.5), rnd.uniform(0, 6.28))
        ob.location = (x, y, ground_h(x, y) + sz * 0.1)
    # rocks hugging the letter base (hide the cut line)
    for i in range(26):
        x = rnd.uniform(-3.5, 3.5)
        y = rnd.uniform(-0.55, 0.45)
        sz = rnd.uniform(0.07, 0.2)
        r = g.rock(f"BaseRock{i}", seed=rnd.randint(0, 9999), size=sz, mat=rockm)
        r.location = (x, y, ground_h(x, y) + sz * 0.1)
        r.rotation_euler = (0, 0, rnd.uniform(0, 6.28))

    # --- nuggets: a few hero lumps in front, a scatter of small ones
    bases = [g.nugget2(f"NugBase{k}", seed=sd, size=1.0, knobs=kn, voxel=0.018, mat=ngold)
             for k, (sd, kn) in enumerate([(21, 7), (33, 2), (12, 2), (9, 4), (4, 3)])]
    for b in bases:
        b.hide_render = True
        b.hide_viewport = True
    spots = [(-1.3, -1.35, 0.78, 0), (1.7, -1.15, 0.6, 1), (0.25, -1.95, 0.42, 2), (3.1, -1.7, 0.45, 3),
             (-2.8, -1.0, 0.4, 4), (4.7, -0.5, 0.7, 0), (-4.5, 0.3, 0.55, 1), (4.0, 1.2, 0.42, 2),
             (-3.7, 1.7, 0.36, 3), (0.9, 1.5, 0.32, 4), (-0.8, 1.3, 0.28, 2), (2.9, -3.4, 0.5, 4)]
    for i in range(int(o.get("smalls", 26))):
        x = rnd.uniform(-7.5, 7.5)
        y = rnd.uniform(-2.6, 3.5)
        if x < -4.0 and y < -1.2:
            continue  # bottom-left = profile photo zone
        if abs(x) < 3.4 and -0.7 < y < 0.6:
            continue
        spots.append((x, y, rnd.uniform(0.1, 0.24), rnd.randint(0, 4)))
    nugs = []
    for i, (x, y, sz, k) in enumerate(spots):
        ob = bpy.data.objects.new(f"Nug{i}", bases[k].data)
        g.link(ob)
        ob.scale = (sz, sz, sz * rnd.uniform(0.7, 0.9))
        ob.rotation_euler = (rnd.uniform(-0.2, 0.2), rnd.uniform(-0.2, 0.2), rnd.uniform(0, 6.28))
        ob.location = (x, y, ground_h(x, y) + sz * 0.22)
        nugs.append(ob)

    # --- mine timber posts + lanterns far back (become warm bokeh)
    woodm = g.wood("Timber")
    lan = g.emission("LanternGlass", (1.0, 0.62, 0.25), 40.0)
    for x, y in ((-5.6, 9.5), (6.4, 11.5), (-0.6, 14.0)):
        zb = ground_h(x, y)
        post = g.link(bpy.data.objects.new(f"Post{x}", bpy.data.meshes.new(f"Post{x}")))
        bm = __import__("bmesh").new()
        __import__("bmesh").ops.create_cube(bm, size=1.0)
        bm.to_mesh(post.data)
        bm.free()
        post.scale = (0.32, 0.32, 6)
        post.location = (x, y, zb + 2.6)
        post.data.materials.append(woodm)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.11, location=(x + 0.45 * (1 if x < 0 else -1), y - 0.3, zb + 2.6))
        bulb = bpy.context.object
        bulb.data.materials.append(lan)
        li = bpy.data.lights.new(f"Lantern{x}", "POINT")
        li.energy = float(o.get("lantern", 260))
        li.color = (1.0, 0.6, 0.25)
        li.shadow_soft_size = 0.12
        lo_ = g.link(bpy.data.objects.new(f"Lantern{x}", li))
        lo_.location = bulb.location

    # --- dust motes (out of focus = bokeh)
    dust = g.emission("Dust", (1.0, 0.6, 0.28), float(o.get("dust", 1.5)))
    camp = cam.location.copy()
    for i in range(int(o.get("motes", 60))):
        if rnd.random() < 0.35:   # near the lens -> soft bokeh discs, never over the word
            f = rnd.uniform(0.25, 0.55)
            q = camp.lerp(Vector((rnd.uniform(-9, 9), 0, rnd.uniform(0.0, 3.5))), f)
            x, y, z = q.x + rnd.uniform(-1, 1), q.y, q.z
            sv = world_to_camera_view(bpy.context.scene, cam, Vector((x, y, z)))
            if 0.12 < sv.x < 0.88 and 0.22 < sv.y < 0.8:
                continue
        else:
            x, y, z = rnd.uniform(-11, 11), rnd.uniform(2, 10), rnd.uniform(0.5, 5.0)
        if x < -3 and y < -3 and z < 2.0:
            continue
        if abs(x) < 4 and -1 < y < 1:
            continue
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=rnd.uniform(0.01, 0.03), location=(x, y, z))
        m = bpy.context.object
        m.data.materials.append(dust)
        m.visible_shadow = False
        m.visible_glossy = False
        m.visible_diffuse = False

    haze = float(o.get("haze", 0.0))
    if haze > 0:
        bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 4, 3))
        vol = bpy.context.object
        vol.name = "Haze"
        vol.scale = (40, 34, 8)
        vm, vnt, vout = g.new_mat("HazeMat")
        ps = g._n(vnt, "ShaderNodeVolumePrincipled", (0, 0))
        ps.inputs["Density"].default_value = haze
        ps.inputs["Anisotropy"].default_value = 0.45
        ps.inputs["Color"].default_value = (1.0, 0.92, 0.8, 1)
        g._l(vnt, ps.outputs["Volume"], vout.inputs["Volume"])
        vol.data.materials.append(vm)
        bpy.context.scene.cycles.volume_bounces = 0
    # --- light
    g.world_studio(STUDIO_STOPS, hdri_mix=0.35, rot_z=140, strength=float(o.get("world", 0.75)),
                   backdrop=1.0, backdrop_top=0.3, diffuse=float(o.get("wdiff", 0.0)))
    t = Vector((0, 0, word.location.z))
    g.area("Key", t + Vector((6.5, -6, 7)), t, size=(3, 3), energy=float(o.get("key", 2400)), color=(1.0, 0.8, 0.56))
    sp = bpy.data.lights.new("Pool", "SPOT")
    sp.energy = float(o.get("pool", 9000))
    sp.color = (1.0, 0.78, 0.5)
    sp.spot_size = math.radians(float(o.get("poolang", 34)))
    sp.spot_blend = 0.9
    sp.shadow_soft_size = 0.6
    spo = g.link(bpy.data.objects.new("Pool", sp))
    spo.location = t + Vector((2.5, -4.5, 9))
    g.look_at(spo, t + Vector((0, -0.6, -0.6)))
    g.area("Back", t + Vector((0, 7, 5.5)), t, size=(9, 1.2), energy=float(o.get("back", 700)), color=(1.0, 0.72, 0.4))
    g.area("Cool", t + Vector((-9, -4, 3)), t, size=(4, 4), energy=float(o.get("cool", 500)), color=(0.62, 0.72, 1.0))
    g.area("RimL", t + Vector((-7, 3, 2.2)), t, size=(0.6, 5), energy=float(o.get("rim", 1500)), color=(1.0, 0.85, 0.65))
    g.area("RimR", t + Vector((7, 3, 2.2)), t, size=(0.6, 5), energy=float(o.get("rim", 1500)), color=(1.0, 0.85, 0.65))
    g.area("Top", t + Vector((0, -1, 6)), t, size=(9, 0.8), energy=float(o.get("top", 900)), color=(1.0, 0.92, 0.82))
    g.area("Bounce", t + Vector((0.5, -5, -2.0)), t, size=(9, 2.0), energy=float(o.get("bounce", 600)), color=(1.0, 0.78, 0.45))
    bpy.data.objects["Bounce"].visible_camera = False

    # sparkles on the gold (camera-only sprites)
    gm = g.glint_mat(strength=float(o.get("glint", 60)))
    camv = cam.location
    for i, (k, fz, sz) in enumerate([(0, 0.32, 0.3), (1, 0.3, 0.22), (5, 0.3, 0.26), (3, 0.3, 0.16)]):
        n = nugs[k]
        p = n.location + Vector((0, 0, n.scale.z * fz))
        p = p + (camv - p).normalized() * 0.3
        g.glint(f"Glint{i}", p, sz, cam, gm)
    lo2, hi2 = g.dims(word)
    for i, (fx, sz) in enumerate([(-0.43, 0.28), (0.47, 0.2)]):
        p = Vector((fx * (hi2.x - lo2.x), lo2.y, hi2.z - 0.02))
        p = p + (camv - p).normalized() * 0.4
        g.glint(f"GlintL{i}", p, sz, cam, gm)
    # warm spill behind the letters: silhouettes them against a glowing floor
    sp2 = g.area("Spill", Vector((0, 1.4, word.location.z + 0.9)), Vector((0, 5.5, 0)), size=(8, 0.5),
                 energy=float(o.get("spill", 500)), color=(1.0, 0.62, 0.28))
    sp2.visible_camera = False

    # gold-only lights: letters/nuggets get studio light, the mine floor stays dark
    recv = bpy.data.collections.new("GoldReceivers")
    for ob in [word] + nugs:
        recv.objects.link(ob)
    for ln in ("Key", "Top", "RimL", "RimR", "Bounce", "Back"):
        bpy.data.objects[ln].light_linking.receiver_collection = recv

    out = o.get("out") or os.path.join(OUT, "goldrush-3d-banner.png")
    if o.get("blend"):
        g.save_blend(os.path.join(HERE, "goldrush-3d-banner.blend"))
    g.render(out)


VARIANTS = {"logo": variant_logo, "logo-dark": variant_logo_dark, "icon": variant_icon, "banner": variant_banner}

if __name__ == "__main__":
    o = argv()
    OPTS.update(o)
    VARIANTS[o["variant"]](o)
