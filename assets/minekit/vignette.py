"""Drift vignette: ~14 m of the reference drift dressed with the kit, two warm lantern lights + a faint headlamp.
Called by render.py (vignette mode) after the blend is open and preview shaders are applied."""
import math

import bmesh
import bpy
from mathutils import Matrix, Vector, noise

import mk
from mk import DEG


def tunnel_mesh(length=16.0, y0=2.0):
    """Rough-arch drift (walls +-2.2 to 2.5 m, elliptical arch to 3.8 m) with outward-only noise, open at the ends."""
    bm = bmesh.new()
    nprof, nring = 44, int(length / 0.2)
    rings = []
    for j in range(nring + 1):
        y = y0 - length * j / nring
        ring = []
        for i in range(nprof + 1):
            u = i / nprof
            # parameterise: left wall (0..0.22), arch (0.22..0.78), right wall (0.78..1)
            if u < 0.22:
                x, z, n = -2.2, 2.5 * (u / 0.22), Vector((-1, 0, 0))
            elif u > 0.78:
                x, z, n = 2.2, 2.5 * ((1 - u) / 0.22), Vector((1, 0, 0))
            else:
                t = math.pi - math.pi * (u - 0.22) / 0.56
                x, z = 2.2 * math.cos(t), 2.5 + 1.3 * math.sin(t)
                n = Vector((math.cos(t) / 2.2, 0, math.sin(t) / 1.3)).normalized()
            p = Vector((x, y, z))
            d = 0.06 + 0.16 * (0.5 + 0.5 * noise.noise(p * 0.9)) + 0.07 * noise.noise(p * 3.1) + 0.03 * noise.noise(p * 7.0)
            ring.append(bm.verts.new(p + n * max(0.0, d)))
        rings.append(ring)
    for j in range(nring):
        for i in range(nprof):
            f = bm.faces.new((rings[j][i], rings[j][i + 1], rings[j + 1][i + 1], rings[j + 1][i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    # normals inward
    for f in bm.faces:
        c = f.calc_center_median()
        if f.normal.dot(Vector((-c.x, 0, 1.9 - c.z))) < 0:
            f.normal_flip()
    me = bpy.data.meshes.new("_tunnel")
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new("_tunnel", me)
    bpy.context.scene.collection.objects.link(o)
    for p in me.polygons:
        p.use_smooth = True
    return o


def floor_mesh(length=16.0, y0=2.0):
    bm = bmesh.new()
    nx, ny = 24, int(length / 0.25)
    vs = []
    for j in range(ny + 1):
        y = y0 - length * j / ny
        row = []
        for i in range(nx + 1):
            x = -2.4 + 4.8 * i / nx
            z = 0.025 * noise.noise(Vector((x * 2.0, y * 2.0, 0.3))) - 0.012 + (0.06 * (abs(x) / 2.4) ** 3)
            row.append(bm.verts.new((x, y, z)))
        vs.append(row)
    for j in range(ny):
        for i in range(nx):
            bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    for f in bm.faces:
        if f.normal.z < 0:
            f.normal_flip()
    me = bpy.data.meshes.new("_floorv")
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new("_floorv", me)
    bpy.context.scene.collection.objects.link(o)
    return o


def instance(src, loc, rot_z=0.0):
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
    o.location = loc
    o.rotation_euler = (0, 0, rot_z * DEG)
    for x in [o] + mk.descendants(o):
        x.hide_render = False
    return o


def build_and_render(out, R, cam=None, target=None):
    rs = {o.name: o for o in R.roots()}
    for o in rs.values():
        for x in [o] + mk.descendants(o):
            x.hide_render = True
    t = tunnel_mesh()
    rock = mk.M("rock_dark").copy()
    rock.name = "_vig_rock"
    R.preview_material(rock)
    t.data.materials.append(rock)
    f = floor_mesh()
    fm = mk.M("dirt").copy()
    fm.name = "_vig_floor"
    R.preview_material(fm)
    f.data.materials.append(fm)
    for o in (t, f):
        ca = o.data.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
        for d in ca.data:
            d.color = (1, 1, 1, 1)
    for k in range(9):
        instance(rs["timber_set"], (0, -1.5 * k, 0))
    for k in range(7):
        y = -1.0 - 2.0 * k
        instance(rs["rail_2m"], (0, y, 0))
        instance(rs["cable_2m"], (0, y, 0))
        instance(rs["vent_duct_2m"], (0, y, 0))
        instance(rs["pipe_2m"], (0, y, 0))
    lan = []
    for y in (-1.5, -6.0, -10.5):
        o = instance(rs["lantern"], (-0.55, y, 2.80))
        for x in [o] + mk.descendants(o):
            x.visible_shadow = False   # the light sits inside the bulb/globe
        lan.append(o)
    instance(rs["ore_cart"], (0, -5.2, 0.2))
    bc = instance(rs["bulb_cage"], (0.9, -12.0, 2.80))
    for x in [bc] + mk.descendants(bc):
        x.visible_shadow = False
    bpy.context.view_layer.update()
    R.world("#010101", 1.0)
    # haze
    w = bpy.context.scene.world
    nt = w.node_tree
    vol = nt.nodes.new("ShaderNodeVolumePrincipled")
    vol.inputs["Density"].default_value = 0.012
    vol.inputs["Color"].default_value = (0.85, 0.8, 0.72, 1)
    nt.links.new(vol.outputs["Volume"], nt.nodes["World Output"].inputs["Volume"])
    for o in lan[:2]:
        b = [c for c in o.children if c.name.startswith("bulb")][0]
        p = b.matrix_world.translation
        R.light("POINT", p + Vector((0, 0, -0.01)), 140, "#ffae5c", size=0.04)
    cam_loc = Vector(cam) if cam else Vector((0.55, 1.6, 1.62))
    tgt = Vector(target) if target else Vector((-0.25, -12.0, 1.35))
    R.camera(cam_loc, tgt, lens=24)
    R.light("SPOT", cam_loc + Vector((0.12, -0.05, 0.12)), 45, "#dfe8ff", size=0.02, target=tgt + Vector((0, 0, -0.4)),
            spot=(28, 0.7))
    s = bpy.context.scene
    try:
        s.eevee.volumetric_tile_size = "4"
        s.eevee.volumetric_samples = 64
        s.eevee.volumetric_end = 40
    except Exception:
        pass
    R.setup_render((1600, 900), 96, exposure=0.6)
    R.render(out)
