"""monument: granite plinth on octagonal steps, bronze 49er miner (pick on his shoulder, gold pan in
hand) and a 3 x 2 m honour-roll board on the plinth front (child `board_face`, sign_face, UV 0-1)."""
import math

import bmesh
import bpy
from mathutils import Matrix, Vector

import arch
from arch import B
import tk
from tk import T

BRONZE = "custom_bronze"


def statue(name="monument_statue", s=1.3, base=(0, 0, 0)):
    """Skin-modifier figure + hat, beard, boots, pickaxe, gold pan. Returns a mesh object (custom_bronze)."""
    V = [(0, 0.0, 1.0), (0, 0.0, 1.18), (0, 0.01, 1.42), (0, 0.02, 1.58), (0, 0.0, 1.71), (0, 0.0, 1.83),
         (-0.11, 0.0, 0.96), (-0.13, -0.06, 0.53), (-0.13, -0.03, 0.1), (-0.14, -0.17, 0.05),
         (0.11, 0.0, 0.96), (0.12, 0.03, 0.53), (0.13, 0.05, 0.1), (0.15, -0.09, 0.05),
         (-0.2, 0.02, 1.5), (-0.27, 0.04, 1.21), (-0.29, -0.02, 0.98),
         (0.2, 0.02, 1.5), (0.33, -0.1, 1.32), (0.19, -0.2, 1.5)]
    E = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (0, 6), (6, 7), (7, 8), (8, 9), (0, 10), (10, 11), (11, 12), (12, 13),
         (2, 14), (14, 15), (15, 16), (2, 17), (17, 18), (18, 19)]
    RAD = [(0.2, 0.15), (0.185, 0.14), (0.235, 0.165), (0.075, 0.075), (0.1, 0.112), (0.058, 0.058),
           (0.125, 0.12), (0.088, 0.088), (0.066, 0.066), (0.06, 0.042),
           (0.125, 0.12), (0.088, 0.088), (0.066, 0.066), (0.06, 0.042),
           (0.098, 0.098), (0.068, 0.068), (0.052, 0.052),
           (0.098, 0.098), (0.068, 0.068), (0.052, 0.052)]
    me = bpy.data.meshes.new(name + "_skel")
    me.from_pydata([Vector(v) * s for v in V], E, [])
    o = bpy.data.objects.new(name + "_skel", me)
    bpy.context.scene.collection.objects.link(o)
    sk = o.modifiers.new("Skin", "SKIN")
    sk.use_smooth_shade = True
    for i, (rx, ry) in enumerate(RAD):
        me.skin_vertices[0].data[i].radius = (rx * s, ry * s)
    me.skin_vertices[0].data[0].use_root = True
    sub = o.modifiers.new("Sub", "SUBSURF")
    sub.levels = sub.render_levels = 1
    dg = bpy.context.evaluated_depsgraph_get()
    body = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
    bpy.data.objects.remove(o, do_unlink=True)
    # props into an MB, then merge the skinned body in
    mb = tk.MB(name)
    P = lambda *v: Vector(v) * s  # noqa: E731
    # boots
    for x, yb, rz in ((-0.14, -0.06, -8), (0.15, -0.02, 6)):
        mb.boxc((0.13 * s, 0.3 * s, 0.11 * s), BRONZE, loc=tuple(P(x, yb, 0.055)), rot=(0, 0, rz), bev=0.02 * s, seg=2)
    # hat: crown + brim
    hc = P(0, 0.0, 1.8)
    mb.cyl(0.098 * s, 0.13 * s, BRONZE, loc=tuple(hc), r2=0.085 * s, sides=16, bev=0.01)
    mb.cyl(0.24 * s, 0.018 * s, BRONZE, loc=tuple(hc + Vector((0, 0, 0.005))), rot=(4, 0, 0), sides=20, bev=0.006)
    # frock-coat skirt + collar for a heavier silhouette
    mb.lathe([(0.205 * s, 1.2 * s), (0.225 * s, 1.0 * s), (0.25 * s, 0.82 * s), (0.27 * s, 0.68 * s), (0.26 * s, 0.66 * s)], BRONZE,
             sides=16, cap_top=False, cap_bot=False)
    mb.lathe([(0.2 * s, 1.56 * s), (0.13 * s, 1.62 * s), (0.09 * s, 1.64 * s)], BRONZE, sides=14, cap_top=False, cap_bot=False)
    # beard
    mb.cyl(0.07 * s, 0.13 * s, BRONZE, loc=tuple(P(0, -0.06, 1.55)), r2=0.03 * s, rot=(160, 0, 0), sides=10)
    # belt
    mb.lathe([(0.152 * s, 1.15 * s), (0.158 * s, 1.17 * s), (0.158 * s, 1.21 * s), (0.152 * s, 1.23 * s)], BRONZE, sides=16,
             cap_top=False, cap_bot=False)
    mb.boxc((0.07 * s, 0.03 * s, 0.06 * s), BRONZE, loc=tuple(P(0, -0.15, 1.19)), bev=0.006)
    # pickaxe over the right shoulder
    a = P(0.17, -0.34, 1.4)
    c = P(0.25, 0.36, 1.98)
    d = (c - a).normalized()
    mb.span(tuple(a), tuple(c), 0.034 * s, 0.034 * s, BRONZE, up=(1, 0, 0), bev=0.008)
    v = d.cross(Vector((1, 0, 0))).normalized()
    h0, h1 = c - v * 0.46 * s + d * 0.03 * s, c + v * 0.42 * s - d * 0.05 * s
    mb.span(tuple(h0), tuple(c + d * 0.05 * s), 0.07 * s, 0.06 * s, BRONZE, up=(1, 0, 0))
    mb.span(tuple(c + d * 0.05 * s), tuple(h1), 0.07 * s, 0.06 * s, BRONZE, up=(1, 0, 0))
    mb.boxc((0.1 * s, 0.1 * s, 0.1 * s), BRONZE, loc=tuple(c + d * 0.03 * s), bev=0.008)
    # gold pan held at the left side, rim outward
    pc = P(-0.36, -0.04, 0.98)
    with mb.at(M=T(tuple(pc)) @ Matrix.Rotation(math.radians(-90), 4, "Y") @ Matrix.Rotation(math.radians(-15), 4, "X")):
        mb.lathe([(0.12 * s, -0.035 * s), (0.2 * s, 0.03 * s), (0.215 * s, 0.035 * s), (0.2 * s, 0.025 * s), (0.11 * s, -0.025 * s),
                  (0.0, -0.025 * s)], BRONZE, sides=18, cap_bot=True, cap_top=False)
    obj = mb.finish(weighted=False)
    # merge the skinned body
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    uvl = bm.loops.layers.uv.active
    cl = bm.loops.layers.float_color.get("Color")
    bb = bmesh.new()
    bb.from_mesh(body)
    off = len(bm.verts)
    vmap = [bm.verts.new(v.co) for v in bb.verts]
    mi = obj.data.materials.find(BRONZE)
    for f in bb.faces:
        nf = bm.faces.new([vmap[v.index] for v in f.verts])
        nf.smooth = True
        nf.material_index = max(0, mi)
        for lp in nf.loops:
            lp[cl] = (1, 1, 1, 1)
            lp[uvl].uv = (lp.vert.co.x, lp.vert.co.z)
    bb.free()
    bm.to_mesh(obj.data)
    bm.free()
    bpy.data.meshes.remove(body)
    for p in obj.data.polygons:
        p.use_smooth = True
    wn = obj.modifiers.new("WN", "WEIGHTED_NORMAL")
    wn.keep_sharp = True
    obj.location = base
    return obj


def monument(seed=81):
    b = B("monument", seed)
    mb = b.mb
    granite, cap = "rock_pale", "concrete"
    # octagonal steps
    for r, z0, h in ((4.3, 0.0, 0.26), (3.55, 0.26, 0.26)):
        mb.cyl(r / math.cos(math.pi / 8), h, granite, loc=(0, 0, z0), sides=8, rot=(0, 0, 22.5), smooth_=False, bev=0.02)
    zt = 0.52
    # plinth: base course, die, cornice, statue pedestal
    mb.boxc((3.9, 2.9, 0.5), granite, loc=(0, 0, zt + 0.25), bev=0.03, skip="d")
    mb.boxc((4.0, 3.0, 0.08), granite, loc=(0, 0, zt + 0.52), bev=0.02)
    z1 = zt + 0.56
    die_h = 2.35
    mb.boxc((3.5, 2.5, die_h), granite, loc=(0, 0, z1 + die_h / 2), bev=0.02, skip="d")
    z2 = z1 + die_h
    mb.boxc((3.7, 2.7, 0.12), granite, loc=(0, 0, z2 + 0.06), bev=0.02)
    mb.boxc((3.95, 2.95, 0.22), granite, loc=(0, 0, z2 + 0.23), bev=0.03)
    mb.boxc((3.75, 2.75, 0.1), granite, loc=(0, 0, z2 + 0.39), bev=0.02)
    zp = z2 + 0.44
    mb.boxc((1.9, 1.6, 0.55), granite, loc=(0, 0, zp + 0.275), bev=0.03, skip="d")
    mb.boxc((2.05, 1.75, 0.1), granite, loc=(0, 0, zp + 0.6), bev=0.02)
    zs = zp + 0.65
    # honour-roll frame on the front of the die (board_face is a child)
    bw, bh = 3.0, 2.0
    bz0 = z1 + 0.18
    yfr = -1.25
    t = 0.07
    for (dx, dz, ww, hh) in ((0, bh / 2 + t / 2, bw + 2 * t, t), (0, -bh / 2 - t / 2, bw + 2 * t, t),
                             (-bw / 2 - t / 2, 0, t, bh), (bw / 2 + t / 2, 0, t, bh)):
        mb.boxc((ww, 0.07, hh), "brass", loc=(dx, yfr - 0.035, bz0 + bh / 2 + dz), bev=0.012)
    mb.boxc((bw, 0.02, bh), "paint_black", loc=(0, yfr - 0.01, bz0 + bh / 2), skip="k")
    # bronze plaques: dedication on the back, star rosettes on the sides
    b.lab.panel(1.7, 1.06, "label_plaque", loc=(0, 1.25 + 0.012, z1 + 0.9), uv=(0.0, 0.375, 1.0, 1.0), rot=(0, 0, 180))
    mb.boxc((1.78, 0.03, 1.14), BRONZE, loc=(0, 1.25 + 0.012, z1 + 0.9 + 0.53), bev=0.006)
    for sx in (-1, 1):
        mb.cyl(0.32, 0.04, BRONZE, loc=(sx * 1.75, 0, z1 + 1.5), rot=(0, 90, 0), centre=True, sides=16, bev=0.008)
        mb.cyl(0.2, 0.06, BRONZE, loc=(sx * 1.77, 0, z1 + 1.5), rot=(0, 90, 0), centre=True, sides=16)
    # flanking lamp posts on the upper step
    for sx in (-1, 1):
        x, y = sx * 2.55, -2.15
        mb.cyl(0.14, 0.3, "cast_iron", loc=(x, y, zt), r2=0.1, sides=10)
        mb.cyl(0.05, 2.6, "cast_iron", loc=(x, y, zt + 0.3), r2=0.04, sides=8)
        arch.lantern(mb, x, y, zt + 2.9, s=1.15)
    root = b.finish()
    st = statue(base=(0, 0.05, zs))
    st.parent = root
    face = tk.MB("board_face")
    face.panel(bw, bh, "sign_face", loc=(0, yfr - 0.021, bz0))
    fo = face.finish(parent=root, weighted=False)
    tk.strip_colors(fo)
    tk.empty("board", (0, yfr - 0.03, bz0 + bh / 2), parent=root)
    return root


NODES = {"monument": monument}
