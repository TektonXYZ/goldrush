"""MOTHERLODE nature kit: pines, a snag, shrubs, granite boulders, rocks, a log pile, a stump, grass.

    bl assets/claimkit/nature.py                  -> public/models/nature.glb (+ .blend, previews)
    bl assets/claimkit/nature.py -- pine_a stump  -> only those nodes (scratch export + previews)

Foliage = alpha-cut cards (glTF alphaMode MASK, double-sided) with embedded textures from tex/ (textures.mjs):
custom_pine_needles, custom_bush, custom_grass. Trunks use custom_bark (ponderosa plates + normal map), the snag
custom_deadwood, cut ends custom_log_end. Card normals are bent outward from the crown (soft volumetric light in
three.js) and every card is wound to face outward, so the DoubleSide normal flip never darkens the visible side.
COLOR_0 on trees is a procedural crown AO (inner/lower needles darker); boulders get a Cycles AO bake.
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bmesh  # noqa: E402
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import bk  # noqa: E402
import kit  # noqa: E402
from kit import MB, R, T, fbm3, smoothstep  # noqa: E402

SHOTS = {}
FOLIAGE = ("custom_pine_needles", "custom_bush", "custom_grass")


def materials():
    kit.custom_mat("custom_bark", "bark.jpg", normal="bark_n.jpg", rough=0.92, nstrength=1.2, spec=0.25)
    kit.custom_mat("custom_deadwood", "deadwood.jpg", normal="deadwood_n.jpg", rough=0.85, nstrength=1.0, spec=0.3)
    kit.custom_mat("custom_log_end", "log_end.jpg", rough=0.9, spec=0.3)
    kit.custom_mat("custom_pine_needles", "pine_needles.png", alpha=True, cutoff=0.45, rough=0.75, double=True, spec=0.35)
    kit.custom_mat("custom_bush", "bush.png", alpha=True, cutoff=0.45, rough=0.8, double=True, spec=0.3)
    kit.custom_mat("custom_grass", "grass.png", alpha=True, cutoff=0.4, rough=0.85, double=True, spec=0.25)


# atlas cells in Blender UV space (v up): spray grows from the cell's left-middle to the right
CELL = {"pond": (0.0, 0.5), "lodge": (0.5, 0.5), "tuft": (0.0, 0.0), "pond_b": (0.5, 0.0)}


def card(mb, origin, along, side, L, W, cell, outward, fold=0.18, mat="custom_pine_needles", shade=1.0):
    """Bent foliage card: attachment edge at `origin`, extends `L` along `along`, `W` wide along `side`;
    centre line folded up by fold*W. Wound so its face points along `outward`."""
    o, a, s = Vector(origin), Vector(along).normalized(), Vector(side).normalized()
    nrm = a.cross(s).normalized()
    if nrm.dot(Vector(outward)) < 0:
        s = -s
        nrm = -nrm
    u0, v0 = CELL[cell]
    lift = nrm * (fold * W)
    p = [o - s * W / 2, o, o + s * W / 2]
    q = [o + a * L - s * W / 2, o + a * L, o + a * L + s * W / 2]
    p[1] = p[1] + lift * 0.4
    q[1] = q[1] + lift
    uvp = [(u0, v0), (u0, v0 + 0.25), (u0, v0 + 0.5)]
    uvq = [(u0 + 0.5, v0), (u0 + 0.5, v0 + 0.25), (u0 + 0.5, v0 + 0.5)]
    # winding: (p0, q0, q1, p1) has normal a x s... ensure outward by construction (s flipped above)
    mb.quad([p[0], p[1], q[1], q[0]], mat, uvs=(uvp[0], uvp[1], uvq[1], uvq[0]), shade=shade)
    mb.quad([p[1], p[2], q[2], q[1]], mat, uvs=(uvp[1], uvp[2], uvq[2], uvq[1]), shade=shade)


def orient_quads_outward(mb, faces_before):
    pass


def trunk(mb, H, r0, seed, mat="custom_bark", sides=8, rings=12, top_r=0.035, flare=1.35, lean=(0, 0), tex=(1.0, 2.0)):
    """Tapered, slightly wobbly trunk. Bark UV: u around (tex[0] m per tile), v up (tex[1] m per tile)."""
    rng = random.Random(seed)
    pts, radii = [], []
    for i in range(rings + 1):
        t = i / rings
        z = H * t
        wob = Vector((fbm3((t * 2.0, seed, 0.3), 2) * 0.25 * t + lean[0] * t * t, fbm3((t * 2.0, seed + 5, 0.8), 2) * 0.25 * t + lean[1] * t * t, 0))
        pts.append(Vector((wob.x, wob.y, z)))
        r = top_r + (r0 - top_r) * (1 - t) ** 1.1
        if t < 0.08:
            r *= 1 + (flare - 1) * (1 - t / 0.08) ** 2
        radii.append(r)
    ringv = []
    for i, (p, r) in enumerate(zip(pts, radii)):
        ringv.append([mb.bm.verts.new(p + Vector((math.cos(k / sides * math.tau), math.sin(k / sides * math.tau), 0)) * r *
                                      (1 + (0.06 * math.sin(k * 2.3 + seed) if i < 2 else 0))) for k in range(sides)])
    faces = []
    for i in range(rings):
        for k in range(sides):
            k2 = (k + 1) % sides
            f = mb.bm.faces.new((ringv[i][k], ringv[i][k2], ringv[i + 1][k2], ringv[i + 1][k]))
            circ0 = 2 * math.pi * radii[i]
            circ1 = 2 * math.pi * radii[i + 1]
            uvs = [(k / sides * circ0 / tex[0], pts[i].z / tex[1]), ((k + 1) / sides * circ0 / tex[0], pts[i].z / tex[1]),
                   ((k + 1) / sides * circ1 / tex[0], pts[i + 1].z / tex[1]), (k / sides * circ1 / tex[0], pts[i + 1].z / tex[1])]
            for lp, uv in zip(f.loops, uvs):
                lp[mb.uv].uv = uv
            f.normal_update()
            faces.append(f)
    mb._paint(faces, mat, 1.0, 0, False)
    return pts, radii


def branch(mb, start, direction, L, r0, droop, seed, mat="custom_bark", segs=2, sides=3):
    """Thin curved limb; returns its points (for card placement)."""
    d = Vector(direction).normalized()
    pts = []
    for i in range(segs + 1):
        t = i / segs
        p = Vector(start) + d * (L * t)
        p.z += droop * L * (t * t - 0.6 * t)
        pts.append(p)
    radii = [r0 * (1 - 0.75 * i / segs) for i in range(segs + 1)]
    mb.tube(pts, r0, mat, sides=sides, radii=radii)
    return pts


def crown_ao(o, centre_z_band=1.0, floor=0.36):
    """Procedural COLOR_0: needles darker toward the trunk and low in the crown, trunk darker at the base."""
    me = o.data
    col = me.color_attributes.get("Col") or me.color_attributes.new("Col", "FLOAT_COLOR", "CORNER")
    nl = len(me.loops)
    co = np.zeros(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    lv = np.zeros(nl, np.int32)
    me.loops.foreach_get("vertex_index", lv)
    pm = np.zeros(len(me.polygons), np.int32)
    me.polygons.foreach_get("material_index", pm)
    lt = np.zeros(len(me.polygons), np.int32)
    me.polygons.foreach_get("loop_total", lt)
    lmat = np.repeat(pm, lt)
    names = [m.name for m in me.materials]
    fol = np.isin(lmat, [i for i, n in enumerate(names) if n in FOLIAGE])
    p = co[lv]
    rd = np.hypot(p[:, 0], p[:, 1])
    z = p[:, 2]
    H = max(z.max(), 0.5)
    out = np.ones(nl, np.float32)
    if fol.any():
        zf = z[fol]
        bands = np.floor(zf / centre_z_band).astype(int)
        rmax = np.zeros_like(zf)
        for b in np.unique(bands):
            m = bands == b
            rmax[m] = max(rd[fol][m].max(), 0.3)
        t = np.clip(rd[fol] / rmax, 0, 1)
        hn = np.clip(zf / H, 0, 1)
        out[fol] = np.clip((floor + (1 - floor) * t ** 0.75) * (0.8 + 0.2 * hn) * 1.08, 0, 1)
    nf = ~fol
    out[nf] = np.clip(0.62 + 0.38 * np.clip(z[nf] / 3.0, 0, 1), 0, 1) * np.where(z[nf] > H * 0.4, 0.82, 1.0)
    c = np.zeros((nl, 4), np.float32)
    c[:, 0] = c[:, 1] = c[:, 2] = out
    c[:, 3] = 1
    col.data.foreach_set("color", c.ravel())
    me.color_attributes.active_color = col
    me.color_attributes.render_color_index = me.color_attributes.find("Col")


def bend_normals(o, up_w=0.45, out_w=0.65, face_w=0.25, centre=(0, 0)):
    """Foliage loops: normals bent outward from the plant axis (soft crown light); others keep smooth normals."""
    me = o.data
    base = [Vector(n.vector) for n in me.corner_normals]
    names = [m.name for m in me.materials]
    res = []
    for poly in me.polygons:
        is_fol = names[poly.material_index] in FOLIAGE
        for li in poly.loop_indices:
            if not is_fol:
                res.append(base[li])
                continue
            v = me.vertices[me.loops[li].vertex_index].co
            out = Vector((v.x - centre[0], v.y - centre[1], 0))
            out = out.normalized() if out.length > 0.05 else Vector((0, 0, 1))
            n = out * out_w + Vector((0, 0, 1)) * up_w + poly.normal * face_w
            res.append(n.normalized())
    me.normals_split_custom_set(res)


def build_pine(name, H, seed, kind="pond"):
    """kind 'pond' = ponderosa (clear bole, rounded open crown of long-needled tufts); 'lodge' = lodgepole
    (slim straight stem, narrow conical crown starting low, short dense needles). Foliage cards run along the
    outer three quarters of every limb, sized to it, alternating flat and upright rolls, plus a tip cluster."""
    rng = random.Random(seed)
    mb = MB(name, seed=seed)
    pond = kind == "pond"
    r0 = H * (0.022 if pond else 0.016)
    tpts, tr = trunk(mb, H * 0.97, r0, seed, sides=8 if pond else 7, rings=12, top_r=0.03, flare=1.4 if pond else 1.25,
                     tex=(0.7, 1.4))
    zc = H * (0.4 if pond else 0.22)
    Rmax = H * (0.2 if pond else 0.12)

    def trunk_at(z):
        i = min(int(z / (H * 0.97) * 12), 11)
        t = (z - tpts[i].z) / max(tpts[i + 1].z - tpts[i].z, 1e-3)
        return tpts[i].lerp(tpts[i + 1], t), tr[i] + (tr[i + 1] - tr[i]) * t

    def profile(t):
        if pond:
            return (math.sin(math.pi * min(1.0, t * 0.88 + 0.12)) ** 0.65) * (1.0 - 0.2 * t)
        return max(0.14, (1 - t) ** 0.9)

    if pond:
        for i in range(6):
            z = rng.uniform(H * 0.16, zc)
            c, r = trunk_at(z)
            a = rng.uniform(0, math.tau)
            d = Vector((math.cos(a), math.sin(a), -0.15))
            branch(mb, c + d * r * 0.8, d, rng.uniform(0.3, 0.9), 0.035, 0.2, seed + i, segs=1, sides=3)
    z = zc
    wi = 0
    spacing = 0.6 if pond else 0.45
    while z < H * 0.94:
        t = (z - zc) / (H - zc)
        c, r = trunk_at(z)
        n = rng.choice([4, 4, 5]) if pond else rng.choice([5, 6])
        rot = rng.uniform(0, math.tau)
        for k in range(n):
            if pond and rng.random() < 0.12:
                continue
            a = rot + k / n * math.tau + rng.uniform(-0.3, 0.3)
            L = Rmax * profile(t) * rng.uniform(0.75, 1.1)
            if L < 0.3:
                continue
            elev = (-0.22 + 0.5 * t) if pond else (-0.2 + 0.25 * t)
            hd = Vector((math.cos(a), math.sin(a), 0))
            d = Vector((math.cos(a), math.sin(a), elev))
            droop = (0.3 - 0.45 * t) if pond else 0.12
            start = c + hd * r * 0.7
            if L > 0.7:
                bp = branch(mb, start, d, L, max(0.025, 0.055 * L / 2.5), droop, seed * 13 + wi * 7 + k, segs=2, sides=3)
            else:
                dn = d.normalized()
                bp = [start, start + dn * L * 0.5, start + dn * L]
            out_dir = Vector((math.cos(a), math.sin(a), 0.2))
            clen = (min(2.3, max(1.05, 0.5 * L + 0.75)) if pond else min(1.4, max(0.75, 0.45 * L + 0.55)))
            ncard = max(2, int(L / (clen * 0.38)) + 1)
            along0 = (bp[-1] - bp[0]).normalized()
            for j in range(ncard):
                tt = min(0.95, 0.22 + 0.78 * (j + rng.uniform(0.0, 0.5)) / ncard)
                si = min(int(tt * (len(bp) - 1)), len(bp) - 2)
                ft = tt * (len(bp) - 1) - si
                base = bp[si].lerp(bp[si + 1], ft)
                along = (along0 + Vector((rng.uniform(-0.3, 0.3), rng.uniform(-0.3, 0.3), rng.uniform(0.05, 0.4)))).normalized()
                side0 = along.cross(Vector((0, 0, 1))).normalized()
                roll = rng.uniform(-0.55, 0.55) if j % 2 == 0 else rng.choice([-1, 1]) * rng.uniform(1.1, 1.57)
                side = (side0 * math.cos(roll) + along.cross(side0).normalized() * math.sin(roll)).normalized()
                cl = clen * rng.uniform(0.85, 1.1)
                cellname = (rng.choice(["pond", "pond", "pond_b"]) if pond else "lodge")
                card(mb, base - along * cl * 0.15, along, side, cl, cl * 0.92, cellname, out_dir, fold=0.2,
                     shade=rng.uniform(0.86, 1.0))
            tip = bp[-1]
            up_out = (out_dir + Vector((0, 0, 0.7))).normalized()
            s1 = up_out.cross(Vector((0, 0, 1))).normalized()
            Lt = clen * (0.75 if pond else 0.8)
            card(mb, tip - up_out * Lt * 0.4, up_out, s1, Lt, Lt, "tuft" if pond else "lodge", out_dir, fold=0.15)
        z += spacing * rng.uniform(0.85, 1.2)
        wi += 1
    top, _ = trunk_at(H * 0.95)
    for k in range(3):
        a = k / 3 * math.pi + rng.uniform(0, 0.4)
        s1 = Vector((math.cos(a), math.sin(a), 0))
        Lt = (1.5 if pond else 1.1)
        card(mb, top - Vector((0, 0, Lt * 0.6)), (0, 0, 1), s1, Lt, Lt * 0.9, "tuft" if pond else "lodge",
             Vector((math.sin(a), -math.cos(a), 0.3)), fold=0.1)
    o = mb.finish(smooth=180, weighted=False)
    bend_normals(o)
    crown_ao(o)
    SHOTS[name] = [("full", (0, -H * 1.55, H * 0.42), (0, 0, H * 0.5), 35), ("up", (2.5, -4.5, 1.7), (0, 0, H * 0.55), 28)]
    return o


def build_pine_dead():
    """Bare grey snag ~11 m: weathered deadwood stem with a broken top and a few snapped limbs."""
    rng = random.Random(77)
    mb = MB("pine_dead", seed=77)
    H = 11.0
    tpts, tr = trunk(mb, H, 0.3, 77, mat="custom_deadwood", sides=8, rings=10, top_r=0.11, flare=1.35, lean=(0.25, -0.1))
    # jagged broken top: a few spikes
    top = tpts[-1]
    for k in range(4):
        a = k / 4 * math.tau + rng.uniform(-0.3, 0.3)
        p0 = top + Vector((math.cos(a), math.sin(a), 0)) * 0.07
        mb.rod(p0, p0 + Vector((math.cos(a) * 0.05, math.sin(a) * 0.05, rng.uniform(0.25, 0.7))), 0.05, "custom_deadwood", sides=4, r2=0.005)
    for i in range(9):
        z = rng.uniform(3.0, H * 0.92)
        ii = min(int(z / H * 10), 9)
        c = tpts[ii].lerp(tpts[ii + 1], (z - tpts[ii].z) / (tpts[ii + 1].z - tpts[ii].z))
        a = rng.uniform(0, math.tau)
        L = rng.uniform(0.4, 1.0) if z < 6 else rng.uniform(0.8, 2.4)
        d = Vector((math.cos(a), math.sin(a), rng.uniform(-0.3, 0.35)))
        branch(mb, c, d, L, 0.06 * min(1, L), rng.uniform(0.1, 0.4), 700 + i, mat="custom_deadwood", segs=2, sides=4)
    o = mb.finish(smooth=180, weighted=False)
    crown_ao(o)
    SHOTS["pine_dead"] = [("full", (0, -16.0, 5.0), (0, 0, 5.4), 35)]
    return o


def build_bush(name, cell_u, seed, height, width, cards, stem_mat="wood_dark"):
    """Shrub: a dome of 'petal' cards (inner ring near-upright, outer ring leaning out), each wound to face
    outward; a few stems underneath."""
    rng = random.Random(seed)
    mb = MB(name, seed=seed)
    for k in range(5):
        a = rng.uniform(0, math.tau)
        mb.rod((0, 0, 0), (math.cos(a) * width * 0.25, math.sin(a) * width * 0.25, height * 0.45), 0.025, stem_mat, sides=4, r2=0.01)
    rings = [(cards // 2, 0.08, 0.18, 1.0, 0.72), (cards - cards // 2, 0.3, 0.6, 0.78, 0.62)]
    for ri, (n, off, tilt, hk, wk) in enumerate(rings):
        rot = rng.uniform(0, math.tau)
        for k in range(n):
            a = rot + k / n * math.tau + rng.uniform(-0.2, 0.2)
            rad = Vector((math.cos(a), math.sin(a), 0))
            tan = Vector((-math.sin(a), math.cos(a), 0))
            up = (Vector((0, 0, 1)) + rad * math.tan(tilt + rng.uniform(-0.08, 0.08))).normalized()
            w = width * wk * rng.uniform(0.85, 1.1)
            h = height * hk * rng.uniform(0.85, 1.08)
            o_ = rad * width * off * rng.uniform(0.7, 1.2) + Vector((0, 0, -0.05))
            pts = [o_ - tan * w / 2, o_ + tan * w / 2, o_ + tan * w / 2 + up * h, o_ - tan * w / 2 + up * h]
            uvs = [(cell_u + 0.0, 0), (cell_u + 0.5, 0), (cell_u + 0.5, 1), (cell_u + 0.0, 1)]
            e1, e2 = pts[1] - pts[0], pts[3] - pts[0]
            if e1.cross(e2).dot(rad) < 0:
                pts = [pts[1], pts[0], pts[3], pts[2]]
                uvs = [uvs[1], uvs[0], uvs[3], uvs[2]]
            mb.quad(pts, "custom_bush", uvs=uvs, shade=rng.uniform(0.85, 1.0))
    o = mb.finish(smooth=180, weighted=False)
    bend_normals(o, up_w=0.7, out_w=0.55, face_w=0.25)
    crown_ao(o, centre_z_band=0.5, floor=0.45)
    SHOTS[name] = [("full", (0, -width * 2.6, height * 0.9), (0, 0, height * 0.45), 35)]
    return o


def boulder_shape(seed, size, detail=3, cuts=6, split=None):
    """Granite boulder vertices: ellipsoid + low-freq lumps + soft joint-plane cuts + fine grain, flat bottom."""
    rng = random.Random(seed)
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=detail, radius=1.0, matrix=Matrix.Identity(4))
    planes = []
    for _ in range(cuts):
        n = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-0.2, 1.0))).normalized()
        planes.append((n, rng.uniform(0.55, 0.85)))
    sv = rng.uniform(0, 100)
    for v in bm.verts:
        p = v.co.copy()
        p *= 1 + 0.22 * fbm3(p * 1.0, 3, sv) + 0.08 * fbm3(p * 2.6, 3, sv + 9) + 0.025 * fbm3(p * 8.0, 2, sv + 4)
        for n, d in planes:
            t = p.dot(n) - d
            if t > 0:
                p -= n * (t * 0.94)
        if p.z < -0.45:
            p.z = -0.45 + (p.z + 0.45) * 0.1
        v.co = Vector((p.x * size[0] / 2, p.y * size[1] / 2, (p.z + 0.38) * size[2] / 2))
    return bm


def bm_into(mb, bm, mat="rock", M=None):
    vmap = {}
    out = []
    for v in bm.verts:
        vmap[v] = mb.bm.verts.new(M @ v.co if M is not None else v.co)
    for f in bm.faces:
        nf = mb.bm.faces.new([vmap[v] for v in f.verts])
        nf.normal_update()
        out.append(nf)
    bm.free()
    mb._uv_world(out, True)
    mb._paint(out, mat, 1.0, 0, False)
    return out


def build_boulder(name, size, seed, detail=3, split=False):
    mb = MB(name, seed=seed)
    if split:
        n = Vector((0.85, 0.2, 0.15)).normalized()
        for side in (-1, 1):
            bm = boulder_shape(seed, size, detail, cuts=6)
            for v in bm.verts:
                wob = 0.06 * fbm3(v.co * 1.7, 2, 3.3)
                t = v.co.dot(n) * side - wob * side
                if t < 0.0:
                    v.co -= n * side * t
            M = T(n * side * 0.035) @ R((0, side * 1.0, side * 1.2))
            bm_into(mb, bm, M=M)
    else:
        bm_into(mb, boulder_shape(seed, size, detail, cuts=6))
    o = mb.finish(smooth=30, weighted=False)
    d = max(size)
    SHOTS[name] = [("full", (-d * 1.2, -d * 1.9, d * 0.8), (0, 0, size[2] * 0.35), 35)]
    return o


def build_rock_cluster():
    rng = random.Random(311)
    mb = MB("rock_cluster", seed=311)
    spots = [((0, 0), (2.2, 1.7, 1.3), 4), ((1.6, 0.6), (1.2, 1.0, 0.8), 3), ((-1.3, 0.9), (1.0, 0.9, 0.65), 3),
             ((0.9, -1.2), (0.8, 0.7, 0.5), 3), ((-1.0, -1.0), (0.6, 0.55, 0.4), 2)]
    for i, ((x, y), sz, det) in enumerate(spots):
        bm = boulder_shape(400 + i, sz, det, cuts=4)
        bm_into(mb, bm, M=T((x, y, -0.05)) @ R((0, 0, rng.uniform(0, 360))))
    for i in range(9):
        a = rng.uniform(0, math.tau)
        rr = rng.uniform(1.3, 2.6)
        s = rng.uniform(0.15, 0.32)
        mb.chunk((math.cos(a) * rr, math.sin(a) * rr, s * 0.25), (s, s * 0.8, s * 0.6), seed=430 + i, detail=1, cuts=4)
    o = mb.finish(smooth=34, weighted=False)
    SHOTS["rock_cluster"] = [("full", (-3.5, -5.2, 2.6), (0, 0, 0.4), 35)]
    return o


def log(mb, a, b, r, seed, sides=10):
    """Cut log: bark sides (u around, v along), growth-ring ends (custom_log_end, UV 0-1 over the disc)."""
    a, b = Vector(a), Vector(b)
    M = kit.frame(a, b)
    Lg = (b - a).length
    ring0, ring1 = [], []
    for k in range(sides):
        ang = k / sides * math.tau
        rr = r * (1 + 0.05 * math.sin(ang * 3 + seed))
        ring0.append(mb.bm.verts.new(M @ Vector((math.cos(ang) * rr, math.sin(ang) * rr, 0))))
        ring1.append(mb.bm.verts.new(M @ Vector((math.cos(ang) * rr, math.sin(ang) * rr, Lg))))
    faces = []
    circ = 2 * math.pi * r
    for k in range(sides):
        k2 = (k + 1) % sides
        f = mb.bm.faces.new((ring0[k], ring0[k2], ring1[k2], ring1[k]))
        uvs = [(k / sides * circ / 0.45, 0), ((k + 1) / sides * circ / 0.45, 0), ((k + 1) / sides * circ / 0.45, Lg / 0.9), (k / sides * circ / 0.45, Lg / 0.9)]
        for lp, uv in zip(f.loops, uvs):
            lp[mb.uv].uv = uv
        f.normal_update()
        faces.append(f)
    mb._paint(faces, "custom_bark", 1.0, 0, False)
    caps = []
    for ring, rev in ((ring0, True), (ring1, False)):
        vs = ring[::-1] if rev else ring
        f = mb.bm.faces.new(vs)
        f.normal_update()
        for lp in f.loops:
            k = ring.index(lp.vert)
            ang = k / sides * math.tau
            lp[mb.uv].uv = (0.5 + 0.48 * math.cos(ang) * (-1 if rev else 1), 0.5 + 0.48 * math.sin(ang))
        caps.append(f)
    mb._paint(caps, "custom_log_end", 1.0, 0, False)


def build_log_pile():
    rng = random.Random(321)
    mb = MB("log_pile", seed=321)
    rows = [4, 3, 2, 1]
    r = 0.19
    for li, n in enumerate(rows):
        for i in range(n):
            x = (i - (n - 1) / 2) * (2 * r + 0.01)
            z = r + li * (2 * r * 0.87)
            rr = r * rng.uniform(0.85, 1.05)
            y0 = -1.5 + rng.uniform(-0.12, 0.12)
            log(mb, (x, y0, z), (x + rng.uniform(-0.05, 0.05), y0 + 3.0 + rng.uniform(-0.15, 0.1), z), rr, 321 + li * 10 + i)
    for sx in (-1, 1):
        for y in (-1.1, 1.1):
            mb.box((0.1, 0.1, 1.2), "wood_dark", loc=(sx * 0.95, y, 0), rot=(0, sx * -8, 0), var=0.1)
    o = mb.finish(smooth=40, weighted=False)
    kit.bake_grime([o], distance=0.6, samples=32, floor=0.4) if False else None
    SHOTS["log_pile"] = [("full", (-3.4, -4.0, 2.0), (0, 0, 0.5), 35)]
    return o


def build_stump():
    rng = random.Random(331)
    mb = MB("stump", seed=331)
    r0, h = 0.42, 0.55
    sides = 12
    ring_b, ring_t = [], []
    for k in range(sides):
        a = k / sides * math.tau
        rb = r0 * (1.25 + 0.12 * math.sin(a * 5 + 1))
        ring_b.append(mb.bm.verts.new((math.cos(a) * rb, math.sin(a) * rb, -0.05)))
        rt = r0 * (1 + 0.04 * math.sin(a * 3))
        ring_t.append(mb.bm.verts.new((math.cos(a) * rt, math.sin(a) * rt, h + 0.06 * math.cos(a))))
    faces = []
    for k in range(sides):
        k2 = (k + 1) % sides
        f = mb.bm.faces.new((ring_b[k], ring_b[k2], ring_t[k2], ring_t[k]))
        circ = 2 * math.pi * r0
        for lp, uv in zip(f.loops, [(k / sides * circ / 0.5, 0), ((k + 1) / sides * circ / 0.5, 0), ((k + 1) / sides * circ / 0.5, h / 1.0), (k / sides * circ / 0.5, h / 1.0)]):
            lp[mb.uv].uv = uv
        f.normal_update()
        faces.append(f)
    mb._paint(faces, "custom_bark", 1.0, 0, False)
    top = mb.bm.faces.new(ring_t)
    top.normal_update()
    for lp in top.loops:
        k = ring_t.index(lp.vert)
        a = k / sides * math.tau
        lp[mb.uv].uv = (0.5 + 0.48 * math.cos(a), 0.5 + 0.48 * math.sin(a))
    mb._paint([top], "custom_log_end", 1.0, 0, False)
    for i in range(6):
        a = i / 6 * math.tau + rng.uniform(-0.25, 0.25)
        d = Vector((math.cos(a), math.sin(a), -0.35))
        mb.tube([Vector((math.cos(a) * r0 * 0.9, math.sin(a) * r0 * 0.9, 0.18)), Vector((math.cos(a) * r0 * 1.5, math.sin(a) * r0 * 1.5, 0.05)),
                 Vector((math.cos(a) * r0 * 2.3, math.sin(a) * r0 * 2.3, -0.06))], 0.13, "custom_bark", sides=5, radii=[0.16, 0.1, 0.04])
    o = mb.finish(smooth=60, weighted=False)
    SHOTS["stump"] = [("full", (-1.4, -2.2, 1.3), (0, 0, 0.25), 35)]
    return o


def build_grass_tuft():
    rng = random.Random(341)
    mb = MB("grass_tuft", seed=341)
    for k in range(4):
        a = k / 4 * math.pi + rng.uniform(-0.15, 0.15)
        s = Vector((math.cos(a), math.sin(a), 0))
        nrm = Vector((-math.sin(a), math.cos(a), 0))
        w, h = rng.uniform(0.75, 0.95), rng.uniform(0.55, 0.75)
        lean = nrm * rng.uniform(-0.1, 0.1)
        p0, p1 = -s * w / 2 + Vector((0, 0, -0.02)), s * w / 2 + Vector((0, 0, -0.02))
        q0, q1 = p0 + Vector((0, 0, h)) + lean, p1 + Vector((0, 0, h)) + lean
        mb.quad([p0, p1, q1, q0], "custom_grass", uvs=((0, 0), (1, 0), (1, 1), (0, 1)))
    o = mb.finish(smooth=180, weighted=False)
    me = o.data
    me.normals_split_custom_set([Vector((0, 0, 1)) for _ in me.loops])
    col = me.color_attributes["Col"]
    for li, lp in enumerate(me.loops):
        z = me.vertices[lp.vertex_index].co.z
        v = 0.55 + 0.45 * smoothstep(0.0, 0.6, z)
        col.data[li].color = (v, v, v, 1)
    me.color_attributes.active_color = col
    me.color_attributes.render_color_index = me.color_attributes.find("Col")
    SHOTS["grass_tuft"] = [("full", (0.0, -1.6, 0.7), (0, 0, 0.3), 35)]
    return o


BUILDERS = {
    "pine_a": lambda: build_pine("pine_a", 17.5, 1, "pond"),
    "pine_b": lambda: build_pine("pine_b", 12.5, 2, "pond"),
    "pine_c": lambda: build_pine("pine_c", 9.0, 3, "lodge"),
    "pine_dead": build_pine_dead,
    "bush_a": lambda: build_bush("bush_a", 0.0, 21, 1.5, 2.0, 16),
    "bush_b": lambda: build_bush("bush_b", 0.5, 22, 1.0, 1.4, 14, stem_mat="wood_planks"),
    "boulder_a": lambda: build_boulder("boulder_a", (1.3, 1.05, 0.85), 201, detail=4),
    "boulder_b": lambda: build_boulder("boulder_b", (2.4, 1.9, 1.5), 202, detail=4),
    "boulder_c": lambda: build_boulder("boulder_c", (3.9, 3.0, 2.3), 203, detail=4, split=True),
    "rock_cluster": build_rock_cluster,
    "log_pile": build_log_pile,
    "stump": build_stump,
    "grass_tuft": build_grass_tuft,
}


def main():
    a = bk.args()
    only = [x for x in a if x in BUILDERS]
    names = only or list(BUILDERS)
    full = not only
    bk.reset()
    materials()
    roots = []
    for n in names:
        r = BUILDERS[n]()
        r.name = r.data.name = n
        roots.append(r)
        print(f"[nature] {n}: {kit.node_tris(r)} tris")
    kit.spread(roots, spacing=40, cols=5)
    rocky = [r for r in roots if r.name.startswith(("boulder", "rock_cluster", "log_pile", "stump"))]
    if rocky:
        kit.bake_grime(rocky, distance=0.9, samples=64, floor=0.32)
    kit.to_origin(roots)
    glb = os.path.join(kit.MODELS, "nature.glb") if full else os.path.join(kit.HERE, "out", "nature-partial.glb")
    kit.export_glb(glb, roots)
    kit.save_blend(os.path.join(kit.HERE, "out", "nature.blend" if full else "nature-partial.blend"))
    if "nopreview" in a:
        return
    kit.preview_materials()
    kit.golden_rig()
    for r in roots:
        r.hide_render = True
    for r in roots:
        r.hide_render = False
        for shot, cam, tgt, lens in SHOTS.get(r.name, []):
            kit.camera(cam, tgt, lens)
            kit.render(os.path.join(kit.PREV, f"{r.name}_{shot}.png"), res=(1000, 1000) if r.name.startswith("pine") else (1200, 800), samples=48)
        r.hide_render = True


main()
