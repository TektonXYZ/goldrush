"""arch: frontier-town architecture kit on top of tk.MB.

Walls are authored in a WALL FRAME: u runs along the wall (left to right seen from outside), v is the
absolute height (z), the wall's outer plane is y = 0 and outside is -y. `WF(x, y, z, yaw)` places a frame;
for a body x in [-W/2, W/2], y in [yf, yb]:
    front WF(-W/2, yf, 0,   0)   right WF(W/2, yf, 0, 90)   back WF(W/2, yb, 0, 180)   left WF(-W/2, yb, 0, -90)
Siding stands proud of y = 0 by `face` (negative); trim sits on the siding.
"""
import math
import random

from mathutils import Matrix, Vector

import tk
from tk import T

DECK = "wood_timber"  # walking surfaces (decks, treads): the lighter sawn-board set reads under a low sun
INTERIOR = "custom_interior"  # 4 x 2 atlas: 0 office 1 store 2 saloon 3 lamp room 4 curtains 5 waiting 6 storeroom 7 parlor


def Rz(d):
    return Matrix.Rotation(math.radians(d), 4, "Z")


def WF(x, y, z, yaw):
    return T((x, y, z)) @ Rz(yaw)


class B:
    """Building context: main mesh builder + label builder (labels carry no COLOR_0) + empties."""

    def __init__(self, name, seed=1):
        self.name = name
        self.mb = tk.MB(name, seed=seed)
        self.lab = tk.MB(name + "_signs", seed=seed + 1)
        self.empties = []  # (name, loc, rot_deg)
        self.children = []  # extra finished objects to parent

    class _Both:
        def __init__(self, b, M):
            self.b, self.M = b, M

        def __enter__(self):
            self.c1 = self.b.mb.at(M=self.M)
            self.c2 = self.b.lab.at(M=self.M)
            self.c1.__enter__()
            self.c2.__enter__()
            return self.b

        def __exit__(self, *a):
            self.c2.__exit__(*a)
            self.c1.__exit__(*a)

    def at(self, M):
        return B._Both(self, M)

    def finish(self, grime=True):
        root = self.mb.finish()
        if self.lab.bm.faces:
            lo = self.lab.finish(parent=root, weighted=False)
            tk.strip_colors(lo)
        else:
            self.lab.bm.free()
        for c in self.children:
            c.parent = root
        for n, loc, rot in self.empties:
            tk.empty(n, loc, rot, parent=root)
        return root


def atlas(cell, cols=4, rows=2):
    c, r = cell % cols, cell // cols
    return (c / cols, 1 - (r + 1) / rows, (c + 1) / cols, 1 - r / rows)


def sub(rect, a0, b0, a1, b1):
    u0, v0, u1, v1 = rect
    return (u0 + (u1 - u0) * a0, v0 + (v1 - v0) * b0, u0 + (u1 - u0) * a1, v0 + (v1 - v0) * b1)


class Op:
    """An opening in a wall frame."""

    def __init__(self, u0, u1, v0, v1):
        self.u0, self.u1, self.v0, self.v1 = u0, u1, v0, v1


def free_spans(a, b, za, zb, ops, pad=0.0):
    spans = [(a, b)]
    for o in ops:
        if o.v1 <= za + 1e-4 or o.v0 >= zb - 1e-4:
            continue
        nxt = []
        for s, e in spans:
            if o.u1 + pad <= s or o.u0 - pad >= e:
                nxt.append((s, e))
                continue
            if o.u0 - pad > s:
                nxt.append((s, o.u0 - pad))
            if o.u1 + pad < e:
                nxt.append((o.u1 + pad, e))
        spans = nxt
    return [(s, e) for s, e in spans if e - s > 0.012]


def vfree_spans(ua, ub, v0, v1, ops):
    spans = [(v0, v1)]
    for o in ops:
        if o.u1 <= ua or o.u0 >= ub:
            continue
        nxt = []
        for s, e in spans:
            if o.v1 <= s or o.v0 >= e:
                nxt.append((s, e))
                continue
            if o.v0 > s:
                nxt.append((s, o.v0))
            if o.v1 < e:
                nxt.append((o.v1, e))
        spans = nxt
    return [(s, e) for s, e in spans if e - s > 0.02]


# ------------------------------------------------------------------ wall surfaces

# painted_wood: the band of the photo (texture metres along the grain, V up; three.js flips the image) where the
# paint is still whole on the three best boards (tk.PAINT_GOOD[0..2]), measured from the bare-wood mask (ORM.B)
CLEAN_V = (0.12, 0.92)
CLEAN_STRIPS = 3


def clapboards(mb, w, v0, v1, ops, mat, e=0.18, t=0.022, outline=None, u0=0.0, tone=(0.9, 1.0)):
    """Horizontal lap siding: each course a tilted board + a lip that throws a shadow line. Courses are cut into
    real board lengths with butt joints staggered course to course; each length is its own texture board (and,
    painted, sits on the photo's intact-paint band so the wear reads as chips, not camouflage)."""
    painted = mat.startswith("wood_painted")
    band = CLEAN_V[1] - CLEAN_V[0]
    v = v0
    while v < v1 - 0.01:
        za, zb = v, min(v + e, v1)
        a, b = (u0, w) if outline is None else outline(zb)
        joints = []
        x = a + mb.rng.uniform(0.5, 2.8)
        while x < b - 0.5:
            joints.append(x)
            x += mb.rng.uniform(2.4, 3.8)
        for s, e2 in free_spans(a, b, za, zb, ops):
            cuts = [s] + [j for j in joints if s + 0.35 < j < e2 - 0.35] + [e2]
            for p, q in zip(cuts, cuts[1:]):
                tn = mb.tone(*tone)
                worn = painted and mb.rng.random() < 0.15   # now and then a board that has lost its paint
                kb = mb.rng.randrange(CLEAN_STRIPS if painted and not worn else 64)
                vf = None
                if painted and not worn:
                    span = min(band, q - p)
                    lo = CLEAN_V[0] + mb.rng.uniform(0.0, band - span)
                    vf = (lo, lo + span)
                mb.poly([(p, -t, za), (q, -t, za), (q, 0, zb), (p, 0, zb)], mat, tone=tn, grain_dir=(1, 0, 0),
                        uvoff=True, vfit=vf, strip=kb)
                mb.poly([(p, 0, za), (q, 0, za), (q, -t, za), (p, -t, za)], mat, tone=tn * 0.75, grain_dir=(1, 0, 0),
                        vfit=vf, strip=kb)
        v = zb


def flat_wall(mb, w, v0, v1, ops, mat, y=0.0, outline=None, grain=(1, 0, 0), u0=0.0, tone=1.0, cell=None, pitch=None):
    vs = {v0, v1}
    for o in ops:
        for q in (o.v0, o.v1):
            if v0 < q < v1:
                vs.add(q)
    vs = sorted(vs)
    # board-and-batten: one quad per board bay (joints under the battens), each bay its own texture board /
    # offset, fixed per column so the window rows don't cut the boards
    split = pitch is not None
    for za, zb in zip(vs, vs[1:]):
        a, b = (u0, w) if outline is None else outline(zb)
        for s, e in free_spans(a, b, za, zb, ops):
            if split:
                pw, anc = pitch
                k0 = math.floor((s - anc[0]) / pw) + 1
                cuts = [s] + [anc[0] + k * pw for k in range(k0, k0 + 400) if s + 1e-3 < anc[0] + k * pw < e - 1e-3] + [e]
                for p, q in zip(cuts, cuts[1:]):
                    col = math.floor(((p + q) / 2 - anc[0]) / pw)
                    r = random.Random(col * 7919 + int(w * 1000) * 13 + len(mat))
                    tn = tone * r.uniform(0.93, 1.0)
                    if mat.startswith("wood_painted"):
                        # a tall painted board: the photo's intact-paint band stretched along the whole board (the
                        # photo is only 1.6 m long; repeating it stacks the same bare patches in rows = camouflage)
                        kb = r.randrange(CLEAN_STRIPS)
                        band = CLEAN_V[1] - CLEAN_V[0]
                        span = band * r.uniform(0.75, 1.0)
                        lo = CLEAN_V[0] + r.uniform(0.0, band - span)
                        H = max(1e-3, v1 - v0)
                        vf = (lo + span * (za - v0) / H, lo + span * (zb - v0) / H)
                        mb.poly([(p, y, za), (q, y, za), (q, y, zb), (p, y, zb)], mat, tone=tn, grain_dir=grain,
                                facing=(0, -1, 0), strip=kb, vfit=vf)
                    elif mat in tk.PLANK_SETS:
                        mb.poly([(p, y, za), (q, y, za), (q, y, zb), (p, y, zb)], mat, tone=tn, grain_dir=grain,
                                facing=(0, -1, 0), strip=r.randrange(64), voff=r.uniform(0.0, 3.0))
                    else:
                        mb.poly([(p, y, za), (q, y, za), (q, y, zb), (p, y, zb)], mat, tone=tn, grain_dir=grain,
                                facing=(0, -1, 0), uvoff=(r.uniform(0, 7), r.uniform(0, 7)))
                continue
            mb.poly([(s, y, za), (e, y, za), (e, y, zb), (s, y, zb)], mat, tone=tone, grain_dir=grain, facing=(0, -1, 0),
                    pitch=pitch)


def battens(mb, w, v0, v1, ops, mat, spacing=0.4, bw=0.07, t=0.024, top=None, u0=0.0, tone=(0.82, 1.0)):
    """Board-and-batten: vertical battens over a flat board wall. top(u) -> top height (gables)."""
    painted = mat.startswith("wood_painted")
    u = u0 + spacing / 2
    while u < w - 0.04:
        vt = v1 if top is None else min(v1, top(u))
        for s, e in vfree_spans(u - bw / 2, u + bw / 2, v0, vt, ops):
            if painted:   # battens keep their paint (the clean band of the photo, stretched along the batten)
                span = (CLEAN_V[1] - CLEAN_V[0]) * min(1.0, (e - s) / 3.0)
                lo = CLEAN_V[0] + mb.rng.uniform(0.0, CLEAN_V[1] - CLEAN_V[0] - span)
                mb.boxc((bw, t, e - s), mat, loc=(u, -t / 2, (s + e) / 2), skip="kd", tone=mb.tone(*tone),
                        vfit=(lo, lo + span), strip=mb.rng.randrange(CLEAN_STRIPS))
            else:
                mb.boxc((bw, t, e - s), mat, loc=(u, -t / 2, (s + e) / 2), skip="kd", tone=mb.tone(*tone), uvoff=True)
        u += spacing


def wall(mb, w, v0, v1, ops, style, mat, outline=None, top=None, u0=0.0, tone=1.0):
    """style: clap | bnb | flat. Returns the y of the outer siding face (trim sits there). tone darkens
    (e.g. 0.8: whitewash gone grey)."""
    if style == "clap":
        clapboards(mb, w, v0, v1, ops, mat, outline=outline, u0=u0, tone=(0.9 * tone, tone))
        return -0.022
    if style == "bnb":
        flat_wall(mb, w, v0, v1, ops, mat, outline=outline, grain=(0, 0, 1), u0=u0, tone=0.95 * tone,
                  pitch=(0.4, (u0 + 0.2, 0, v0)))
        battens(mb, w, v0, v1, ops, mat, top=top, u0=u0, tone=(0.82 * tone, tone))
        return -0.024
    flat_wall(mb, w, v0, v1, ops, mat, outline=outline, u0=u0)
    return 0.0


def gable_wall(mb, w, v0, rise, style, mat, ops=(), tone=1.0):
    """Triangular gable above v0 in a wall frame (u 0..w), apex at w/2."""
    def top(u):
        return v0 + rise * (1 - abs(u - w / 2) / (w / 2))
    if style == "clap":
        e = 0.165
        v = v0
        while v < v0 + rise - 0.03:
            zb = min(v + e, v0 + rise)
            half = (w / 2) * (1 - (zb - v0) / rise)
            a, b = w / 2 - half, w / 2 + half
            for s, e2 in free_spans(a, b, v, zb, ops):
                tn = mb.tone(0.9, 1.0)
                mb.poly([(s, -0.022, v), (e2, -0.022, v), (e2, 0, zb), (s, 0, zb)], mat, tone=tn, grain_dir=(1, 0, 0),
                        uvoff=True)
                mb.poly([(s, 0, v), (e2, 0, v), (e2, -0.022, v), (s, -0.022, v)], mat, tone=tn * 0.75)
            v = zb
        return -0.022
    mb.poly([(0, 0, v0), (w, 0, v0), (w / 2, 0, v0 + rise)], mat, grain_dir=(0, 0, 1), facing=(0, -1, 0),
            pitch=(0.4, (0.2, 0, v0)) if style == "bnb" else None, tone=0.95 * tone)
    if style == "bnb":
        battens(mb, w, v0, v0 + rise, list(ops), mat, top=top, tone=(0.82 * tone, tone))
        return -0.024
    return 0.0


def corner_boards(mb, w, v0, v1, face, mat, cw=0.14, ends=(True, True)):
    t = 0.03
    if ends[0]:
        mb.boxc((cw, t, v1 - v0), mat, loc=(cw / 2, face - t / 2, (v0 + v1) / 2), skip="k", bev=0.006)
    if ends[1]:
        mb.boxc((cw, t, v1 - v0), mat, loc=(w - cw / 2, face - t / 2, (v0 + v1) / 2), skip="k", bev=0.006)


def stone_course(mb, w, z0, z1, *, mats=("rock_pale", "rock_pale", "rock"), ch=0.25, proud=0.05, ext=0.07,
                 mortar="concrete"):
    """Rubble-stone foundation in a wall frame (u 0..w, outside = -y): mortar bed + hand-laid courses of squared
    stones of random length, each its own piece of the rock photo, a little proud and a little out of true."""
    rng = mb.rng
    mb.poly([(-ext, -0.012, z0), (w + ext, -0.012, z0), (w + ext, -0.012, z1), (-ext, -0.012, z1)], mortar,
            facing=(0, -1, 0), tone=0.5)
    n = max(1, round((z1 - z0) / ch))
    hc = (z1 - z0) / n
    for k in range(n):
        za = z0 + k * hc
        u = -ext - rng.uniform(0.0, 0.3)
        while u < w + ext:
            L = rng.uniform(0.32, 0.72)
            a, c = max(u, -ext), min(u + L, w + ext)
            if c - a > 0.08:
                h = hc - rng.uniform(0.022, 0.04)
                d = proud + rng.uniform(-0.015, 0.02)
                mb.boxc((c - a - 0.025, d + 0.03, h), mats[rng.randrange(len(mats))],
                        loc=((a + c) / 2, -d / 2 + 0.015, za + 0.012 + h / 2), rot=(0, rng.uniform(-2.5, 2.5), 0),
                        skip="k", tone=rng.uniform(0.7, 1.0), uvoff=True)
            u += L


def foundation(b, x0, x1, y0, y1, z, *, sides="lrk", z0=-0.12):
    """Rubble foundation round a body footprint (front = -y side 'f', back 'k', left 'l', right 'r')."""
    W, D = x1 - x0, y1 - y0
    frames = {"f": (WF(x0, y0, 0, 0), W), "r": (WF(x1, y0, 0, 90), D), "k": (WF(x1, y1, 0, 180), W),
              "l": (WF(x0, y1, 0, -90), D)}
    for s in sides:
        M, w = frames[s]
        with b.mb.at(M=M):
            stone_course(b.mb, w, z0, z)


def water_table(mb, w, v, face, mat, h=0.2, ops=(), ext=0.0):
    """skirt board along the bottom of the siding + drip cap (broken at door openings)"""
    for a, c in free_spans(-ext, w + ext, v, v + h + 0.03, list(ops)):
        mb.boxc((c - a, 0.03, h), mat, loc=((a + c) / 2, face - 0.015, v + h / 2), skip="k")
        mb.boxc((c - a + 0.02, 0.05, 0.03), mat, loc=((a + c) / 2, face - 0.025, v + h + 0.015), skip="k", bev=0.006)


# ------------------------------------------------------------------ interiors (fake rooms behind glass)

def interior_box(mb, u0, u1, v0, v1, y0, depth, cell, margin=0.12, lamp=None):
    """Five inward-facing quads textured from one cell of the emissive interior atlas."""
    a0, a1 = u0 - margin, u1 + margin
    b0, b1 = v0 - margin, v1 + margin
    y1 = y0 + depth
    rect = atlas(cell)
    m = INTERIOR
    mb.quad_uv([(a0, y1, b0), (a1, y1, b0), (a1, y1, b1), (a0, y1, b1)], m,
               uvs=_uv4(sub(rect, 0.1, 0.12, 0.9, 0.95)))
    l = sub(rect, 0.0, 0.12, 0.1, 0.95)
    mb.quad_uv([(a0, y0, b0), (a0, y1, b0), (a0, y1, b1), (a0, y0, b1)], m,
               uvs=((l[0], l[1]), (l[2], l[1]), (l[2], l[3]), (l[0], l[3])))
    r = sub(rect, 0.9, 0.12, 1.0, 0.95)
    mb.quad_uv([(a1, y1, b0), (a1, y0, b0), (a1, y0, b1), (a1, y1, b1)], m,
               uvs=((r[0], r[1]), (r[2], r[1]), (r[2], r[3]), (r[0], r[3])))
    f = sub(rect, 0.1, 0.0, 0.9, 0.12)
    mb.quad_uv([(a0, y0, b0), (a1, y0, b0), (a1, y1, b0), (a0, y1, b0)], m,
               uvs=((f[0], f[1]), (f[2], f[1]), (f[2], f[3]), (f[0], f[3])))
    c = sub(rect, 0.1, 0.95, 0.9, 1.0)
    mb.quad_uv([(a1, y0, b1), (a0, y0, b1), (a0, y1, b1), (a1, y1, b1)], m,
               uvs=((c[2], c[1]), (c[0], c[1]), (c[0], c[3]), (c[2], c[3])))


def _uv4(r):
    u0, v0, u1, v1 = r
    return ((u0, v0), (u1, v0), (u1, v1), (u0, v1))


# ------------------------------------------------------------------ windows

def window(b, u0, u1, v0, v1, *, face=-0.022, trim="wood_painted_white", sash=None, panes=(2, 1),
           glass="glass", cell=None, shade=0.0, shutters=None, cw=0.1, head="cap", sill=True, apron=True,
           box_d=0.55, sash_kind="dh", reveal=None, cafe=0.0, lod="full"):
    """Double-hung (or fixed) window in a wall frame. panes = (columns, rows per sash).
    cell: interior atlas cell shown through clear glass (None -> glass_dark, no interior)."""
    mb = b.mb
    sash = sash or trim
    reveal = reveal or trim
    w, h = u1 - u0, v1 - v0
    uc = (u0 + u1) / 2
    ct = 0.028
    yc = face - ct
    if lod == "simple":   # side/back walls: one sash frame, one muntin, plain casing
        sash_kind, panes, apron, head = "fixed", (2, 1), False, "plain"
    if cw > 0:
        mb.boxc((cw, ct, h), trim, loc=(u0 - cw / 2, face - ct / 2, (v0 + v1) / 2), skip="k")
        mb.boxc((cw, ct, h), trim, loc=(u1 + cw / 2, face - ct / 2, (v0 + v1) / 2), skip="k")
        if head == "cap":
            hh = 0.15
            mb.boxc((w + 2 * cw, ct, hh), trim, loc=(uc, face - ct / 2, v1 + hh / 2), skip="k")
            # bed moulding, then the projecting drip cap on top (widest member last, like a real cornice)
            mb.boxc((w + 2 * cw + 0.04, ct + 0.025, 0.03), trim, loc=(uc, face - (ct + 0.025) / 2, v1 + hh + 0.015),
                    skip="k")
            mb.boxc((w + 2 * cw + 0.11, ct + 0.065, 0.045), trim, loc=(uc, face - (ct + 0.065) / 2, v1 + hh + 0.0525),
                    skip="k", bev=0.009)
        elif head == "pediment":
            # Italianate head: frieze on two consoles, bed moulding, corona, low pediment with raking cornices
            hh = 0.17
            cwid = w + 2 * cw
            mb.boxc((cwid, ct, hh), trim, loc=(uc, face - ct / 2, v1 + hh / 2), skip="k")
            for sx in (-1, 1):
                mb.boxc((0.07, 0.07, 0.2), trim, loc=(uc + sx * (cwid / 2 - 0.035), face - ct - 0.035, v1 + 0.07),
                        bev=0.01, skip="k")
            z0 = v1 + hh
            mb.boxc((cwid + 0.06, ct + 0.035, 0.035), trim, loc=(uc, face - (ct + 0.035) / 2, z0 + 0.0175), skip="k",
                    bev=0.006)
            mb.boxc((cwid + 0.16, ct + 0.08, 0.05), trim, loc=(uc, face - (ct + 0.08) / 2, z0 + 0.06), skip="k",
                    bev=0.01)
            zc = z0 + 0.085
            pw = cwid + 0.12
            ph = 0.19
            mb.poly([(uc - pw / 2 + 0.05, face - ct, zc), (uc + pw / 2 - 0.05, face - ct, zc), (uc, face - ct, zc + ph - 0.04)],
                    trim, thick=0.03, facing=(0, -1, 0))
            for sx in (-1, 1):
                a = (uc + sx * (pw / 2 + 0.03), face - ct - 0.035, zc + 0.01)
                bb = (uc, face - ct - 0.035, zc + ph + 0.015)
                mb.span(a, bb, ct + 0.09, 0.055, trim, up=(0, 0, 1), bev=0.008)
        elif head == "plain":
            mb.boxc((w + 2 * cw, ct, cw), trim, loc=(uc, face - ct / 2, v1 + cw / 2), skip="k")
    if sill:
        sd = 0.075 + ct
        mb.boxc((w + 2 * cw + 0.08, sd + 0.06, 0.045), trim, loc=(uc, face - sd / 2 + 0.03, v0 - 0.0225), bev=0.008)
        if apron and cw > 0:
            mb.boxc((w + 0.04, ct, 0.09), trim, loc=(uc, face - ct / 2, v0 - 0.045 - 0.045), skip="k")
    ys = 0.05
    mb.poly([(u0, yc, v0), (u0, ys, v0), (u0, ys, v1), (u0, yc, v1)], reveal, facing=(1, 0, 0))
    mb.poly([(u1, yc, v0), (u1, ys, v0), (u1, ys, v1), (u1, yc, v1)], reveal, facing=(-1, 0, 0))
    mb.poly([(u0, yc, v1), (u1, yc, v1), (u1, ys, v1), (u0, ys, v1)], reveal, facing=(0, 0, -1))
    if not sill:
        mb.poly([(u0, yc, v0), (u1, yc, v0), (u1, ys, v0), (u0, ys, v0)], reveal, facing=(0, 0, 1))
    gm = glass if cell is not None else "glass_dark"
    st, rt = 0.05, 0.05
    if sash_kind == "dh":
        vm = (v0 + v1) / 2
        _sash(mb, u0, u1, v0, vm + 0.018, ys, sash, panes, gm, bottom=0.075, top=0.035)
        _sash(mb, u0, u1, vm - 0.018, v1, ys + 0.045, sash, panes, gm, bottom=0.035, top=rt)
    else:
        _sash(mb, u0, u1, v0, v1, ys, sash, panes, gm, bottom=0.07, top=rt, rows_total=True)
    if cell is not None:
        if shade > 0:
            mb.poly([(u0 + 0.02, ys + 0.1, v1 - shade * h), (u1 - 0.02, ys + 0.1, v1 - shade * h),
                     (u1 - 0.02, ys + 0.1, v1 - 0.01), (u0 + 0.02, ys + 0.1, v1 - 0.01)], "canvas", facing=(0, -1, 0))
            mb.boxc((w - 0.03, 0.02, 0.025), "wood_dark", loc=(uc, ys + 0.09, v1 - shade * h - 0.012))
        if cafe > 0:
            zc = v0 + cafe * h
            mb.poly([(u0 + 0.02, ys + 0.1, v0 + 0.02), (u1 - 0.02, ys + 0.1, v0 + 0.02), (u1 - 0.02, ys + 0.1, zc),
                     (u0 + 0.02, ys + 0.1, zc)], "canvas", facing=(0, -1, 0), tone=0.8)
            mb.cyl(0.008, w - 0.04, "brass", loc=(u0 + 0.02, ys + 0.095, zc), rot=(0, 90, 0), sides=4)
        interior_box(mb, u0, u1, v0, v1, ys + 0.12, box_d, cell)
    if shutters:
        sw = w / 2 + 0.015
        for side in (-1, 1):
            ux = (u0 - cw - sw / 2 - 0.01) if side < 0 else (u1 + cw + sw / 2 + 0.01)
            mb.boxc((sw, 0.03, h + 0.04), shutters, loc=(ux, face - 0.015, (v0 + v1) / 2), skip="k", bev=0.005,
                    tone=mb.tone(0.85, 1.0))
            for zz in (v0 + 0.18, v1 - 0.18):
                mb.boxc((sw - 0.06, 0.02, 0.09), shutters, loc=(ux, face - 0.04, zz), skip="k")


def _sash(mb, u0, u1, v0, v1, y, mat, panes, glass, bottom=0.07, top=0.05, rows_total=False):
    st = 0.05
    d = 0.04
    w, h = u1 - u0, v1 - v0
    uc = (u0 + u1) / 2
    yy = y + d / 2
    mb.boxc((st, d, h), mat, loc=(u0 + st / 2, yy, (v0 + v1) / 2), skip="k")
    mb.boxc((st, d, h), mat, loc=(u1 - st / 2, yy, (v0 + v1) / 2), skip="k")
    mb.boxc((w - 2 * st, d, bottom), mat, loc=(uc, yy, v0 + bottom / 2), skip="k")
    mb.boxc((w - 2 * st, d, top), mat, loc=(uc, yy, v1 - top / 2), skip="k")
    gu0, gu1, gv0, gv1 = u0 + st, u1 - st, v0 + bottom, v1 - top
    cols, rows = panes
    mw = 0.022
    for i in range(1, cols):
        uu = gu0 + (gu1 - gu0) * i / cols
        mb.boxc((mw, d * 0.7, gv1 - gv0), mat, loc=(uu, yy, (gv0 + gv1) / 2), skip="k")
    for j in range(1, rows):
        vv = gv0 + (gv1 - gv0) * j / rows
        mb.boxc((gu1 - gu0, d * 0.7, mw), mat, loc=(uc, yy, vv), skip="k")
    mb.poly([(gu0, y + d * 0.6, gv0), (gu1, y + d * 0.6, gv0), (gu1, y + d * 0.6, gv1), (gu0, y + d * 0.6, gv1)], glass,
            facing=(0, -1, 0))


def storefront(b, u0, u1, v_floor, *, face=-0.022, trim="wood_painted_white", panel="wood_painted_white",
               glass_top=3.0, transom_top=3.6, bulk=0.62, mullions=None, cell=1, frame=0.09, label=None):
    """Display window: raised-panel bulkhead, big lights with thin mullions, a transom band of small
    lights above, interior box behind (cell). label = (uv_rect, aspect) gold-leaf decal on the glass."""
    mb = b.mb
    w = u1 - u0
    uc = (u0 + u1) / 2
    ys = 0.06
    vb = v_floor + bulk
    # bulkhead with two raised panels per bay
    mb.boxc((w, 0.05, bulk), panel, loc=(uc, face + 0.01, v_floor + bulk / 2), skip="k")
    nb = max(1, round(w / 1.0))
    pw = (w - 0.1 * (nb + 1)) / nb
    for i in range(nb):
        px = u0 + 0.1 + pw / 2 + i * (pw + 0.1)
        mb.boxc((pw, 0.02, bulk - 0.2), panel, loc=(px, face - 0.025, v_floor + bulk / 2), bev=0.012, skip="k")
    mb.boxc((w + 0.06, 0.1, 0.05), trim, loc=(uc, face - 0.02, vb + 0.025), bev=0.008)  # sill cap
    # frame
    mb.boxc((frame, 0.08, transom_top - vb), trim, loc=(u0 + frame / 2, face - 0.01, (vb + transom_top) / 2), skip="k")
    mb.boxc((frame, 0.08, transom_top - vb), trim, loc=(u1 - frame / 2, face - 0.01, (vb + transom_top) / 2), skip="k")
    mb.boxc((w, 0.08, 0.1), trim, loc=(uc, face - 0.01, glass_top + 0.05), skip="k")
    mb.boxc((w + 0.1, 0.06, 0.16), trim, loc=(uc, face - 0.02, transom_top + 0.08), skip="k", bev=0.01)
    gu0, gu1 = u0 + frame, u1 - frame
    n = mullions if mullions is not None else max(1, round((gu1 - gu0) / 1.2))
    for i in range(1, n):
        uu = gu0 + (gu1 - gu0) * i / n
        mb.boxc((0.05, 0.06, glass_top - vb - 0.05), trim, loc=(uu, ys - 0.01, (vb + 0.05 + glass_top) / 2), skip="k")
    # transom lights
    nt = max(2, round((gu1 - gu0) / 0.45))
    for i in range(1, nt):
        uu = gu0 + (gu1 - gu0) * i / nt
        mb.boxc((0.035, 0.05, transom_top - glass_top - 0.1), trim, loc=(uu, ys - 0.01, (glass_top + 0.1 + transom_top) / 2),
                skip="k")
    for (z0, z1) in ((vb + 0.05, glass_top), (glass_top + 0.1, transom_top)):
        mb.poly([(gu0, ys, z0), (gu1, ys, z0), (gu1, ys, z1), (gu0, ys, z1)], "glass", facing=(0, -1, 0))
    # reveal sides
    yc = face - 0.05
    mb.poly([(u0 + frame, yc, vb), (u0 + frame, ys, vb), (u0 + frame, ys, transom_top), (u0 + frame, yc, transom_top)], trim,
            facing=(1, 0, 0))
    mb.poly([(u1 - frame, yc, vb), (u1 - frame, ys, vb), (u1 - frame, ys, transom_top), (u1 - frame, yc, transom_top)], trim,
            facing=(-1, 0, 0))
    interior_box(mb, gu0, gu1, vb, transom_top, ys + 0.05, 0.9, cell, margin=0.1)
    if label is not None:
        rect, asp = label
        lw = min(gu1 - gu0 - 0.3, 1.6)
        lh = lw / asp
        b.lab.panel(lw, lh, "label_glass", loc=(uc, ys - 0.004, vb + (glass_top - vb) * 0.55), uv=rect)


# ------------------------------------------------------------------ doors

def door(b, u0, u1, v0, v1, *, face=-0.022, trim="wood_painted_white", leaf="wood_painted_green", leaves=2,
         open_deg=0.0, glazed=True, cell=0, transom=0.5, transom_label=None, vest_d=2.4, cw=0.11,
         batwing=False, lamp=True, counter=True, threshold=True):
    """Panelled door(s) in a wall frame. open_deg > 0 swings the leaves inward over a lit vestibule."""
    mb = b.mb
    w = u1 - u0
    uc = (u0 + u1) / 2
    ct = 0.03
    yc = face - ct
    ys = 0.1  # leaf front plane (closed)
    top = v1 + (transom if transom else 0)
    mb.boxc((cw, ct, top - v0 + 0.02), trim, loc=(u0 - cw / 2, face - ct / 2, (v0 + top) / 2), skip="k")
    mb.boxc((cw, ct, top - v0 + 0.02), trim, loc=(u1 + cw / 2, face - ct / 2, (v0 + top) / 2), skip="k")
    mb.boxc((w + 2 * cw, ct, 0.17), trim, loc=(uc, face - ct / 2, top + 0.085), skip="k")
    mb.boxc((w + 2 * cw + 0.09, ct + 0.05, 0.045), trim, loc=(uc, face - (ct + 0.05) / 2, top + 0.17 + 0.022), skip="k",
            bev=0.008)
    mb.boxc((w + 2 * cw + 0.04, ct + 0.03, 0.03), trim, loc=(uc, face - (ct + 0.03) / 2, top + 0.17 + 0.06), skip="k")
    # reveal
    mb.poly([(u0, yc, v0), (u0, ys, v0), (u0, ys, top), (u0, yc, top)], trim, facing=(1, 0, 0))
    mb.poly([(u1, yc, v0), (u1, ys, v0), (u1, ys, top), (u1, yc, top)], trim, facing=(-1, 0, 0))
    mb.poly([(u0, yc, top), (u1, yc, top), (u1, ys, top), (u0, ys, top)], trim, facing=(0, 0, -1))
    if threshold:
        mb.boxc((w + 0.04, 0.2, 0.035), "wood_dark", loc=(uc, (yc + ys) / 2, v0 + 0.017), bev=0.006)
    if transom:
        mb.boxc((w, 0.07, 0.06), trim, loc=(uc, ys + 0.02, v1 + 0.03), skip="k")
        n = max(2, round(w / 0.45))
        for i in range(1, n):
            mb.boxc((0.03, 0.04, transom - 0.06), trim, loc=(u0 + w * i / n, ys + 0.02, v1 + 0.06 + (transom - 0.06) / 2),
                    skip="k")
        mb.poly([(u0, ys + 0.04, v1 + 0.06), (u1, ys + 0.04, v1 + 0.06), (u1, ys + 0.04, top), (u0, ys + 0.04, top)],
                "glass", facing=(0, -1, 0))
        if transom_label is not None:
            rect, asp = transom_label
            lw = w * 0.82
            lh = min(transom - 0.12, lw / asp)
            b.lab.panel(lw, lh, "label_glass", loc=(uc, ys + 0.035, v1 + 0.06 + (transom - 0.06 - lh) / 2), uv=rect)
    lw = w / leaves
    h = v1 - v0
    if batwing:
        bw_h0, bw_h1 = v0 + 0.35, v0 + 1.55
        for i, (hx, sgn) in enumerate(((u0, 1), (u1, -1))):
            ang = open_deg * sgn
            M = T((hx, ys + 0.02, 0)) @ Rz(ang)
            with mb.at(M=M):
                _batwing_leaf(mb, sgn * lw, bw_h0, bw_h1, leaf)
    else:
        hinges = [(u0, 1)] if leaves == 1 else [(u0, 1), (u1, -1)]
        for hx, sgn in hinges:
            ang = open_deg * sgn
            M = T((hx, ys, 0)) @ Rz(ang)
            with mb.at(M=M):
                _door_leaf(mb, sgn * lw, v0 + 0.01, v1, leaf, glazed, cell is not None and open_deg < 5)
    if cell is not None and (open_deg > 5 or glazed or batwing):
        _vestibule(b, u0, u1, v0, top, ys + 0.06, vest_d, cell, lamp=lamp, counter=counter)


def _door_leaf(mb, w, z0, z1, mat, glazed, see_through):
    """leaf in the hinge frame: spans x 0..w (w may be negative), thickness y 0..0.045."""
    sgn = 1 if w > 0 else -1
    W = abs(w)
    d = 0.045
    st, tr, br, lr = 0.11, 0.11, 0.24, 0.19
    h = z1 - z0

    def X(a):
        return sgn * a
    yy = d / 2
    mb.boxc((st, d, h), mat, loc=(X(st / 2), yy, (z0 + z1) / 2), bev=0.005)
    mb.boxc((st, d, h), mat, loc=(X(W - st / 2), yy, (z0 + z1) / 2), bev=0.005)
    mb.boxc((W - 2 * st, d, tr), mat, loc=(X(W / 2), yy, z1 - tr / 2))
    mb.boxc((W - 2 * st, d, br), mat, loc=(X(W / 2), yy, z0 + br / 2))
    zl = z0 + 0.95
    mb.boxc((W - 2 * st, d, lr), mat, loc=(X(W / 2), yy, zl))
    pw = W - 2 * st
    # lower panel (recessed + raised field)
    lz0, lz1 = z0 + br, zl - lr / 2
    mb.boxc((pw, d * 0.4, lz1 - lz0), mat, loc=(X(W / 2), yy, (lz0 + lz1) / 2))
    mb.boxc((pw - 0.08, d * 0.62, lz1 - lz0 - 0.08), mat, loc=(X(W / 2), yy, (lz0 + lz1) / 2), bev=0.012)
    uz0, uz1 = zl + lr / 2, z1 - tr
    if glazed:
        mb.boxc((0.025, d * 0.7, uz1 - uz0), mat, loc=(X(W / 2), yy, (uz0 + uz1) / 2))
        for yg in (yy - 0.004, yy + 0.004):
            mb.poly([(X(st), yg, uz0), (X(W - st), yg, uz0), (X(W - st), yg, uz1), (X(st), yg, uz1)],
                    "glass" if see_through else "glass_dark", facing=(0, -1 if yg < yy else 1, 0))
    else:
        mb.boxc((pw, d * 0.4, uz1 - uz0), mat, loc=(X(W / 2), yy, (uz0 + uz1) / 2))
        mb.boxc((pw - 0.08, d * 0.62, uz1 - uz0 - 0.08), mat, loc=(X(W / 2), yy, (uz0 + uz1) / 2), bev=0.012)
    # knob both sides
    for yk, rot in ((-0.025, 90), (d + 0.025, -90)):
        mb.cyl(0.03, 0.035, "brass", loc=(X(W - 0.07), yk, zl), rot=(rot, 0, 0), sides=10, centre=True)


def _batwing_leaf(mb, w, z0, z1, mat):
    sgn = 1 if w > 0 else -1
    W = abs(w)
    d = 0.035

    def X(a):
        return sgn * a
    mb.boxc((0.07, d, z1 - z0), mat, loc=(X(0.035), d / 2, (z0 + z1) / 2), bev=0.005)
    mb.boxc((0.07, d, z1 - z0 - 0.25), mat, loc=(X(W - 0.035), d / 2, (z0 + z1 - 0.25) / 2), bev=0.005)
    mb.boxc((W, d, 0.12), mat, loc=(X(W / 2), d / 2, z0 + 0.06))
    mb.boxc((W, d, 0.08), mat, loc=(X(W / 2), d / 2, z0 + 0.62))
    # louvres
    for k in range(5):
        zz = z0 + 0.16 + k * 0.085
        mb.boxc((W - 0.1, 0.012, 0.075), mat, loc=(X(W / 2), d / 2, zz + 0.0375), rot=(25, 0, 0))
    # scalloped top: a sloped rail rising toward the hinge
    mb.span((X(0.05), d / 2, z1 - 0.05), (X(W - 0.05), d / 2, z1 - 0.3), 0.07, d, mat, up=(0, 1, 0))
    for k in range(4):
        xx = 0.15 + k * (W - 0.25) / 3
        ztop = z1 - 0.05 - (xx / W) * 0.25
        mb.boxc((0.025, d * 0.6, ztop - (z0 + 0.66)), mat, loc=(X(xx), d / 2, (ztop + z0 + 0.66) / 2))


def _vestibule(b, u0, u1, v0, v1, y0, depth, cell, lamp=True, counter=True):
    mb = b.mb
    margin = 0.35
    interior_box(mb, u0, u1, v0 + margin, v1, y0, depth, cell, margin=margin)
    uc = (u0 + u1) / 2
    if counter:
        cy = y0 + depth * 0.62
        mb.boxc((u1 - u0 + 0.5, 0.55, 1.0), "wood_dark", loc=(uc, cy, v0 + 0.5), skip="d")
        mb.boxc((u1 - u0 + 0.62, 0.65, 0.05), "wood_dark", loc=(uc, cy, v0 + 1.025), bev=0.01)
        mb.cyl(0.07, 0.04, "brass", loc=(uc - 0.4, cy, v0 + 1.05), sides=10)
        mb.cyl(0.012, 0.3, "brass", loc=(uc - 0.4, cy, v0 + 1.09), sides=6)
        mb.cyl(0.11, 0.12, "glass", loc=(uc - 0.4, cy, v0 + 1.36), r2=0.06, sides=10)
        mb.cyl(0.035, 0.08, "emit_warm", loc=(uc - 0.4, cy, v0 + 1.38), sides=8)
    if lamp:
        lz = v1 + 0.15
        mb.cyl(0.006, 0.4, "cast_iron", loc=(uc, y0 + depth * 0.4, lz - 0.05), sides=4)
        mb.cyl(0.22, 0.12, "brass", loc=(uc, y0 + depth * 0.4, lz - 0.18), r2=0.05, sides=12, cap_bot=False)
        mb.cyl(0.06, 0.1, "emit_warm", loc=(uc, y0 + depth * 0.4, lz - 0.24), sides=8)


# ------------------------------------------------------------------ porches

def turned_post(mb, x, y, z0, z1, mat="wood_painted_white", sides=8, s=1.0):
    base_h, top_h = 0.42 * s, 0.32 * s
    bs = 0.15 * s
    mb.boxc((bs, bs, base_h), mat, loc=(x, y, z0 + base_h / 2), bev=0.012, skip="d")
    mb.boxc((bs + 0.025, bs + 0.025, 0.035), mat, loc=(x, y, z0 + base_h + 0.017), bev=0.008)
    zt0 = z0 + base_h + 0.035
    zt1 = z1 - top_h - 0.035
    L = zt1 - zt0
    prof = [(0.066, 0.0), (0.068, 0.03), (0.048, 0.07), (0.066, 0.21), (0.068, 0.26), (0.046, 0.34),
            (0.044, 0.4), (0.047, 0.82), (0.066, 0.885), (0.05, 0.93), (0.068, 0.975), (0.064, 1.0)]
    mb.lathe([(r * s, zt0 + f * L) for r, f in prof], mat, loc=(x, y, 0), sides=sides, cap_top=False, cap_bot=False)
    mb.boxc((bs + 0.025, bs + 0.025, 0.035), mat, loc=(x, y, zt1 + 0.017), bev=0.008)
    mb.boxc((bs, bs, top_h), mat, loc=(x, y, z1 - top_h / 2), bev=0.012, skip="u")


def square_post(mb, x, y, z0, z1, mat="wood_timber", s=0.16):
    mb.boxc((s, s, z1 - z0), mat, loc=(x, y, (z0 + z1) / 2), bev=0.018, skip="d", uvoff=True)


def bracket(mb, x, y, z_top, dirx, La=0.42, Lb=0.42, t=0.045, mat="wood_painted_white", plane="xz"):
    """Scroll-sawn knee bracket: hangs below z_top, reaches La along dirx (or along -y for plane yz)."""
    seg = 5
    prof = [(0.0, 0.0), (La, 0.0), (La, -0.05)]
    for i in range(1, seg):
        a = math.pi / 2 * i / seg
        prof.append((La - (La - 0.05) * math.sin(a), -Lb + (Lb - 0.05) * math.cos(a)))
    prof += [(0.05, -Lb), (0.0, -Lb)]
    if plane == "xz":
        pts = [(x + dirx * a, y - t / 2, z_top + bb) for a, bb in prof]
        mb.poly(pts, mat, thick=t, facing=(0, -1, 0))
    else:  # yz plane, reaching toward -y, centred on x
        pts = [(x - t / 2, y - a, z_top + bb) for a, bb in prof]
        mb.poly(pts, mat, thick=t, facing=(-1, 0, 0))


def railing(mb, a, b, z, h=1.0, mat="wood_painted_white", spacing=0.17, posts=True, post_mat=None, style="baluster",
            bal=0.034):
    a, b = Vector(a), Vector(b)
    d = (b - a)
    L = d.length
    dn = d / L
    post_mat = post_mat or mat
    zt = z + h
    mb.span((a.x, a.y, zt - 0.03), (b.x, b.y, zt - 0.03), 0.095, 0.06, mat, bev=0.01)
    mb.span((a.x, a.y, z + 0.12), (b.x, b.y, z + 0.12), 0.06, 0.05, mat)
    if style == "baluster":
        n = max(1, int(L / spacing))
        for i in range(1, n):
            p = a + d * (i / n)
            mb.boxc((bal, bal, h - 0.21), mat, loc=(p.x, p.y, z + 0.145 + (h - 0.21) / 2), skip="ud", rot=(0, 0, math.degrees(math.atan2(dn.y, dn.x))))
    elif style == "x":
        n = max(1, round(L / 1.2))
        for i in range(n):
            p0 = a + d * (i / n)
            p1 = a + d * ((i + 1) / n)
            mb.span((p0.x, p0.y, z + 0.145), (p1.x, p1.y, zt - 0.06), 0.06, 0.035, mat, up=(0, 0, 1))
            mb.span((p0.x, p0.y, zt - 0.06), (p1.x, p1.y, z + 0.145), 0.06, 0.035, mat, up=(0, 0, 1))
    if posts:
        for p in (a, b):
            mb.boxc((0.11, 0.11, h + 0.06), post_mat, loc=(p.x, p.y, z + (h + 0.06) / 2), bev=0.01, skip="d")
            mb.boxc((0.15, 0.15, 0.04), post_mat, loc=(p.x, p.y, z + h + 0.08), bev=0.01)


def deck(mb, x0, x1, y0, y1, z, mat=DECK, bw=0.14, gap=0.009, t=0.045, along="y"):
    """Plank deck top at z. along='y': boards run front-to-back (porch), 'x': along the street."""
    if along == "y":
        n = int((x1 - x0) / (bw + gap))
        w = (x1 - x0) / n
        for i in range(n):
            xc = x0 + w * (i + 0.5)
            dz = mb.rng.uniform(-0.004, 0.003)
            mb.boxc((w - gap, y1 - y0, t), mat, loc=(xc, (y0 + y1) / 2, z - t / 2 + dz), skip="dk", tone=mb.tone(0.78, 1.0),
                    uvoff=True)
    else:
        n = int((y1 - y0) / (bw + gap))
        w = (y1 - y0) / n
        for i in range(n):
            yc = y0 + w * (i + 0.5)
            dz = mb.rng.uniform(-0.004, 0.003)
            mb.boxc((x1 - x0, w - gap, t), mat, loc=((x0 + x1) / 2, yc, z - t / 2 + dz), skip="d", tone=mb.tone(0.78, 1.0),
                    uvoff=True)


def treads(mb, x0, x1, y0, y1, zt, t=0.045, mat=DECK):
    """A stair tread made of two or three boards (front board noses over the riser), top at zt."""
    n = max(1, round((y1 - y0) / 0.16))
    w = (y1 - y0) / n
    for i in range(n):
        yc = y0 + w * (i + 0.5)
        mb.boxc((x1 - x0, w - 0.008, t), mat, loc=((x0 + x1) / 2, yc, zt - t / 2 + mb.rng.uniform(-0.003, 0.002)),
                tone=mb.tone(0.8, 1.0), uvoff=True, bev=0.006 if i == 0 else 0.0)


def porch(b, x0, x1, yf, depth, deck_z, post_xs, top_z, *, roof="balcony", post="turned", trim="wood_painted_white",
          post_mat=None, steps=2, step_d=0.3, roof_mat="corrugated", rail_mat=None, balcony_rail=True, rise=0.45,
          fascia_label=None, skirt=DECK, brackets=True, deck_mat=DECK, rail_style="baluster"):
    """Covered porch in front of a facade at y = yf (front = -y). top_z = underside of the beam."""
    mb = b.mb
    post_mat = post_mat or trim
    rail_mat = rail_mat or trim
    yfront = yf - depth
    ypost = yfront + 0.16
    deck(mb, x0, x1, yfront, yf, deck_z, mat=deck_mat)
    # rim joist + skirt
    mb.boxc((x1 - x0 + 0.04, 0.05, 0.22), DECK, loc=((x0 + x1) / 2, yfront - 0.025, deck_z - 0.045 - 0.11),
            skip="k", uvoff=True)
    mb.boxc((x1 - x0, 0.03, deck_z - 0.27), skirt, loc=((x0 + x1) / 2, yfront + 0.02, (deck_z - 0.27) / 2), skip="k",
            grain=2, tone=0.8)
    for xs, sgn in ((x0, -1), (x1, 1)):
        mb.boxc((0.05, depth, 0.22), DECK, loc=(xs + sgn * 0.025, yf - depth / 2, deck_z - 0.045 - 0.11), skip="k")
        mb.boxc((0.03, depth, deck_z - 0.27), skirt, loc=(xs + sgn * 0.015, yf - depth / 2, (deck_z - 0.27) / 2), grain=2,
                tone=0.8)
    # steps across the full width
    if steps:
        sh = deck_z / (steps + 1)
        for k in range(steps):
            zt = sh * (k + 1)
            yy0 = yfront - step_d * (steps - k)
            treads(mb, x0 + 0.1, x1 - 0.1, yy0, yy0 + step_d + 0.02, zt)
            mb.boxc((x1 - x0 - 0.2, 0.03, zt - 0.045), DECK, loc=((x0 + x1) / 2, yy0 + 0.04, (zt - 0.045) / 2),
                    skip="k", uvoff=True, tone=0.85)
            for xs in (x0 + 0.12, x1 - 0.12):
                mb.boxc((0.06, step_d, zt), "wood_timber", loc=(xs, yy0 + step_d / 2, zt / 2), skip="d")
    # posts + beam
    for px in post_xs:
        if post == "turned":
            turned_post(mb, px, ypost, deck_z, top_z, post_mat)
        else:
            square_post(mb, px, ypost, deck_z, top_z, post_mat)
    bh = 0.26
    mb.boxc((x1 - x0 + 0.1, 0.16, bh), trim, loc=((x0 + x1) / 2, ypost, top_z + bh / 2), bev=0.01)
    if brackets:
        for px in post_xs:
            for sgn in (-1, 1):
                if (px <= x0 + 0.3 and sgn < 0) or (px >= x1 - 0.3 and sgn > 0):
                    continue
                bracket(mb, px + sgn * 0.075, ypost, top_z, sgn, 0.42, 0.42, 0.045, trim)
    if fascia_label is not None:
        rect, w_m, lname = fascia_label
        h_m = bh - 0.04
        b.lab.panel(w_m, h_m, lname, loc=((x0 + x1) / 2, ypost - 0.081, top_z + 0.02), uv=rect)
    # ceiling joists / boards
    zc = top_z + bh
    if roof == "balcony":
        slab = 0.18
        mb.boxc((x1 - x0 + 0.1, depth - 0.0, slab), "wood_planks", loc=((x0 + x1) / 2, yf - depth / 2 - 0.02, zc + slab / 2),
                skip="", uvoff=True)
        mb.poly([(x0, yf, zc - 0.002), (x1, yf, zc - 0.002), (x1, ypost + 0.08, zc - 0.002), (x0, ypost + 0.08, zc - 0.002)],
                "wood_painted_white", facing=(0, 0, -1), grain_dir=(0, 1, 0))
        zf = zc + slab
        deck(mb, x0 + 0.02, x1 - 0.02, yfront + 0.0, yf, zf + 0.045, along="x")
        mb.boxc((x1 - x0 + 0.14, 0.04, slab + 0.07), trim, loc=((x0 + x1) / 2, yfront - 0.04, zc + (slab + 0.07) / 2 - 0.02),
                skip="k", bev=0.008)
        if balcony_rail:
            zr = zf + 0.045
            railing(mb, (x0 + 0.08, yfront + 0.1), (x1 - 0.08, yfront + 0.1), zr, mat=rail_mat, style=rail_style)
            railing(mb, (x0 + 0.08, yf - 0.05), (x0 + 0.08, yfront + 0.1), zr, mat=rail_mat, posts=False, style=rail_style)
            railing(mb, (x1 - 0.08, yf - 0.05), (x1 - 0.08, yfront + 0.1), zr, mat=rail_mat, posts=False, style=rail_style)
            for px in post_xs[1:-1]:
                mb.boxc((0.11, 0.11, 1.06), rail_mat, loc=(px, yfront + 0.1, zr + 0.53), bev=0.01, skip="d")
                mb.boxc((0.15, 0.15, 0.04), rail_mat, loc=(px, yfront + 0.1, zr + 1.08), bev=0.01)
        return zf + 0.045
    if roof == "shed":
        zt = zc + rise
        oh = 0.25
        mb.poly([(x0 - 0.12, yfront - oh, zc + 0.05), (x1 + 0.12, yfront - oh, zc + 0.05), (x1 + 0.12, yf, zt + 0.05),
                 (x0 - 0.12, yf, zt + 0.05)], roof_mat, thick=0.05, facing=(0, -0.3, 1))
        # rafters under the roof
        n = int((x1 - x0) / 0.6)
        for i in range(n + 1):
            xx = x0 + (x1 - x0) * i / n
            mb.span((xx, yfront - oh + 0.03, zc), (xx, yf, zt - 0.02), 0.05, 0.12, "wood_timber", up=(0, 0.3, 1),
                    skip="")
        mb.boxc((x1 - x0 + 0.24, 0.03, 0.18), trim, loc=((x0 + x1) / 2, yfront - oh - 0.015, zc + 0.02), skip="k")
        return zt
    return zc


# ------------------------------------------------------------------ cornices, crests, roofs

def cornice(mb, x0, x1, y, z, proj=0.4, mat="wood_painted_white", spacing=0.9, brackets=True, dentils=False,
            bk_mat=None, returns=True):
    """Bracketed cornice on a facade whose outer face is the plane y (front = -y). Bottom at z."""
    bk_mat = bk_mat or mat
    xc = (x0 + x1) / 2
    w = x1 - x0

    def member(p, h, zb, bev=0.0):
        ext = p if returns else 0.0
        mb.boxc((w + 2 * ext, p + 0.01, h), mat, loc=(xc, y - p / 2 + 0.005, zb + h / 2), bev=bev,
                skip="" if returns else "lr")
    member(0.07, 0.08, z)
    member(proj - 0.05, 0.21, z + 0.08)
    member(proj, 0.07, z + 0.29, bev=0.012)
    member(proj + 0.025, 0.035, z + 0.36, bev=0.006)
    if dentils:
        n = int(w / 0.11)
        for i in range(n):
            xx = x0 + 0.055 + i * (w - 0.11) / max(1, n - 1)
            mb.boxc((0.05, 0.05, 0.06), mat, loc=(xx, y - 0.07 - 0.025, z + 0.05), skip="k")
    if brackets:
        n = max(2, round(w / spacing))
        for i in range(n + 1):
            xx = x0 + 0.06 + (w - 0.12) * i / n
            bracket(mb, xx, y, z + 0.08, 0, La=proj - 0.06, Lb=0.42, t=0.075, mat=bk_mat, plane="yz")
    return z + 0.395


def pediment(mb, xc, y, z, w, h, mat="wood_painted_white", back="wood_planks", thick=0.16, trim=None, disc=True):
    """Triangular crest on top of a cornice."""
    trim = trim or mat
    mb.poly([(xc - w / 2, y, z), (xc + w / 2, y, z), (xc, y, z + h)], mat, facing=(0, -1, 0), grain_dir=(1, 0, 0))
    mb.poly([(xc - w / 2, y + thick, z), (xc + w / 2, y + thick, z), (xc, y + thick, z + h)], back, facing=(0, 1, 0),
            grain_dir=(0, 0, 1))
    ang = math.degrees(math.atan2(h, w / 2))
    for sgn in (-1, 1):
        a = (xc + sgn * (w / 2 + 0.08), y - 0.03, z - 0.02)
        b = (xc, y - 0.03, z + h + 0.06)
        mb.span(a, b, thick + 0.12, 0.09, trim, up=(0, 0, 1), bev=0.01)
        mb.span((a[0], a[1] - 0.02, a[2] + 0.07), (b[0], b[1] - 0.02, b[2] + 0.07), thick + 0.16, 0.035, trim,
                up=(0, 0, 1))
    if disc:
        mb.cyl(h * 0.22, 0.05, trim, loc=(xc, y - 0.025, z + h * 0.38), rot=(90, 0, 0), sides=16, centre=True, bev=0.01)
        mb.cyl(h * 0.14, 0.07, trim, loc=(xc, y - 0.035, z + h * 0.38), rot=(90, 0, 0), sides=16, centre=True)
    mb.cyl(0.05, 0.35, trim, loc=(xc, y + thick / 2, z + h + 0.08), sides=8, r2=0.02)


def gable_roof(b, x0, x1, y0, y1, z_eave, pitch, *, oh_side=0.45, oh_back=0.4, mat="roof_shingle",
               fascia="wood_painted_white", thick=0.06, rafters=True, ridge="galvanized", back_gable=None,
               rake=True, oh_front=0.0, front_gable=None, rafter_step=0.8):
    """Ridge along y. y0 = front edge (behind the false front), y1 = back wall (overhang added).
    back_gable = (style, material) fills the back triangle."""
    mb = b.mb
    xc = (x0 + x1) / 2
    hs = (x1 - x0) / 2 + oh_side
    rise_tot = hs * math.tan(math.radians(pitch))
    ze = z_eave - oh_side * math.tan(math.radians(pitch)) + thick
    zr = ze + rise_tot
    ye = y1 + oh_back
    yf0 = y0
    y0 = y0 - oh_front
    for sgn in (-1, 1):
        xe = xc + sgn * hs
        pts = [(xc, y0, zr), (xe, y0, ze), (xe, ye, ze), (xc, ye, zr)]
        mb.poly(pts, mat, thick=thick, facing=(sgn * 0.3, 0, 1))
        # fascia along the eave
        mb.boxc((0.035, ye - y0 + 0.04, 0.2), fascia, loc=(xe + sgn * 0.0175, (y0 + ye) / 2, ze - 0.1), bev=0.006)
        if rafters:
            n = int((y1 - yf0) / rafter_step)
            for i in range(n + 1):
                yy = yf0 + 0.2 + (y1 - yf0 - 0.25) * i / n
                xw = xc + sgn * (x1 - x0) / 2
                zw = z_eave
                mb.span((xw, yy, zw - 0.08), (xe - sgn * 0.03, yy, ze - 0.1), 0.05, 0.11, "wood_timber",
                        up=(0, 0, 1), skip="")
        if rake:
            mb.span((xe + sgn * 0.02, ye + 0.02, ze - 0.08), (xc, ye + 0.02, zr - 0.08 + 0.02), 0.035, 0.2, fascia,
                    up=(0, 0, 1), bev=0.006)
            if oh_front > 0:
                mb.span((xe + sgn * 0.02, y0 - 0.02, ze - 0.08), (xc, y0 - 0.02, zr - 0.08 + 0.02), 0.035, 0.2, fascia,
                        up=(0, 0, 1), bev=0.006)
    # ridge cap
    if ridge:
        for sgn in (-1, 1):
            mb.span((xc + sgn * 0.09, y0, zr - 0.035 + 0.01), (xc + sgn * 0.09, ye, zr - 0.035 + 0.01), 0.22, 0.02, ridge,
                    up=(-sgn * math.sin(math.radians(pitch)), 0, math.cos(math.radians(pitch))))
    rise = (x1 - x0) / 2 * math.tan(math.radians(pitch))
    if back_gable:
        style, gm = back_gable[:2]
        with mb.at(M=WF(x1, y1, 0, 180)):
            gable_wall(mb, x1 - x0, z_eave, rise, style, gm, tone=back_gable[2] if len(back_gable) > 2 else 1.0)
    if front_gable:
        style, gm = front_gable
        with mb.at(M=WF(x0, yf0, 0, 0)):
            gable_wall(mb, x1 - x0, z_eave, rise, style, gm)
    return zr


def brick_arch(mb, uc, w, v, face, rise=0.22, depth=0.23, mat="brick", key="concrete"):
    """Segmental brick arch band over an opening (wall frame), with a stone keystone."""
    seg = 9
    half = w / 2 + 0.06
    R = (half * half + rise * rise) / (2 * rise)
    cz = v + rise - R
    a0 = math.asin(half / R)
    inner, outer = [], []
    for i in range(seg + 1):
        a = -a0 + 2 * a0 * i / seg
        inner.append((uc + math.sin(a) * R, face - 0.03, cz + math.cos(a) * R))
        outer.append((uc + math.sin(a) * (R + depth), face - 0.03, cz + math.cos(a) * (R + depth)))
    for i in range(seg):
        mb.poly([inner[i], inner[i + 1], outer[i + 1], outer[i]], mat, facing=(0, -1, 0))
        mb.poly([inner[i], inner[i + 1], (inner[i + 1][0], face, inner[i + 1][2]), (inner[i][0], face, inner[i][2])], mat,
                facing=(0, 0, -1))
        mb.poly([outer[i + 1], outer[i], (outer[i][0], face, outer[i][2]), (outer[i + 1][0], face, outer[i + 1][2])], mat,
                facing=(0, 0, 1))
    mb.boxc((0.16, 0.06, depth + 0.06), key, loc=(uc, face - 0.04, v + rise + depth / 2 - 0.01), bev=0.008)
    # spandrel fill between the flat head and the arch
    mb.poly([(uc - half, face - 0.002, v)] + [(p[0], face - 0.002, p[2]) for p in inner] + [(uc + half, face - 0.002, v)], mat,
            facing=(0, -1, 0))


def stovepipe(mb, x, y, z_base, h=1.6, r=0.085, mat="steel_dark"):
    mb.cyl(r * 2.6, 0.12, "galvanized", loc=(x, y, z_base - 0.04), r2=r * 1.2, sides=10)
    mb.cyl(r, h, mat, loc=(x, y, z_base), sides=10)
    mb.cyl(r * 1.15, 0.05, mat, loc=(x, y, z_base + h * 0.55), sides=10)
    zt = z_base + h
    for k in range(3):
        a = k * math.tau / 3
        mb.span((x + math.cos(a) * r * 0.9, y + math.sin(a) * r * 0.9, zt),
                (x + math.cos(a) * r * 1.2, y + math.sin(a) * r * 1.2, zt + 0.12), 0.012, 0.012, mat)
    mb.cyl(r * 2.3, 0.16, mat, loc=(x, y, zt + 0.1), r2=0.01, sides=10, cap_top=False)


def chimney(mb, x, y, z_base, h, w=0.62, d=0.5, mat="brick", cap="concrete"):
    mb.boxc((w, d, h), mat, loc=(x, y, z_base + h / 2), skip="d")
    mb.boxc((w + 0.1, d + 0.1, 0.12), mat, loc=(x, y, z_base + h - 0.25))
    mb.boxc((w + 0.14, d + 0.14, 0.07), cap, loc=(x, y, z_base + h + 0.035), bev=0.01)
    mb.boxc((w - 0.24, d - 0.2, 0.02), "steel_dark", loc=(x, y, z_base + h + 0.08))


def sign_board(b, xc, y, zc, w, h, label, *, frame="wood_painted_white", body=None, uv=(0, 0, 1, 1), t=0.06,
               molding=0.05):
    """A board on a facade (front plane y): framed box with the painted label quad on its face."""
    mb = b.mb
    body = body or frame
    mb.boxc((w, t, h), body, loc=(xc, y - t / 2, zc), skip="k")
    for (dx, dz, ww, hh) in ((0, h / 2 + molding / 2 - 0.01, w + 2 * molding, molding),
                             (0, -h / 2 - molding / 2 + 0.01, w + 2 * molding, molding),
                             (-w / 2 - molding / 2 + 0.01, 0, molding, h), (w / 2 + molding / 2 - 0.01, 0, molding, h)):
        mb.boxc((ww, t + 0.03, hh), frame, loc=(xc + dx, y - (t + 0.03) / 2, zc + dz), bev=0.008, skip="k")
    b.lab.panel(w - 0.02, h - 0.02, label, loc=(xc, y - t - 0.002, zc - h / 2 + 0.01), uv=uv)


def wall_lantern(mb, x, y, z, out=(0, -1), arm=0.32):
    """Iron bracket + glass-and-iron lantern (emit_warm core) on a wall at plane y."""
    ox, oy = out
    lx, ly = x + ox * arm, y + oy * arm
    mb.boxc((0.12, 0.03, 0.2), "cast_iron", loc=(x, y - 0.015 * oy, z + 0.05))
    mb.span((x, y, z + 0.1), (lx, ly, z + 0.1), 0.025, 0.025, "cast_iron")
    mb.span((x, y, z - 0.05), (lx * 0.6 + x * 0.4, ly * 0.6 + y * 0.4, z + 0.1), 0.02, 0.02, "cast_iron")
    lantern(mb, lx, ly, z - 0.33)


def lantern(mb, x, y, z, s=1.0, glow="emit_warm"):
    """Square carriage lantern standing at z (bottom)."""
    w = 0.17 * s
    h = 0.26 * s
    mb.boxc((w + 0.04, w + 0.04, 0.03), "cast_iron", loc=(x, y, z + 0.015), bev=0.004)
    mb.boxc((w - 0.03, w - 0.03, h - 0.02), glow, loc=(x, y, z + 0.03 + (h - 0.02) / 2))
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.boxc((0.018, 0.018, h), "cast_iron", loc=(x + sx * w / 2, y + sy * w / 2, z + 0.03 + h / 2))
    for side in range(4):
        a = side * 90
        nx, ny = math.cos(math.radians(a)), math.sin(math.radians(a))
        mb.poly([(x + nx * w / 2 - ny * w / 2, y + ny * w / 2 + nx * w / 2, z + 0.03),
                 (x + nx * w / 2 + ny * w / 2, y + ny * w / 2 - nx * w / 2, z + 0.03),
                 (x + nx * w / 2 + ny * w / 2, y + ny * w / 2 - nx * w / 2, z + 0.03 + h),
                 (x + nx * w / 2 - ny * w / 2, y + ny * w / 2 + nx * w / 2, z + 0.03 + h)], "glass", facing=(nx, ny, 0))
    mb.cyl(w * 0.85, 0.12 * s, "cast_iron", loc=(x, y, z + 0.03 + h), r2=0.02, sides=4, rot=(0, 0, 45))
    mb.cyl(0.012, 0.08, "cast_iron", loc=(x, y, z + 0.15 * s + h), sides=4)


def hanging_lamp(mb, x, y, z_ceiling, drop=0.6):
    mb.cyl(0.008, drop, "cast_iron", loc=(x, y, z_ceiling - drop), sides=4)
    lantern(mb, x, y, z_ceiling - drop - 0.33)


def gooseneck(mb, x, y, z, reach=0.55):
    """Barn gooseneck light on a facade (front plane y), shade facing down."""
    mb.cyl(0.05, 0.03, "paint_green", loc=(x, y - 0.015, z), rot=(90, 0, 0), sides=10, centre=True)
    pts = [(x, y - 0.03, z)]
    for i in range(1, 7):
        a = math.pi / 2 * i / 6
        pts.append((x, y - 0.03 - reach * math.sin(a), z + 0.22 * math.sin(a) - 0.0 * i))
    mb.tube(pts, 0.016, "paint_green", sides=6)
    ex, ey, ez = pts[-1]
    mb.cyl(0.2, 0.12, "paint_green", loc=(ex, ey - 0.03, ez - 0.16), r2=0.05, sides=12, cap_bot=False)
    mb.cyl(0.05, 0.04, "emit_warm", loc=(ex, ey - 0.03, ez - 0.17), sides=8)


# ------------------------------------------------------------------ props (shared by buildings and prop nodes)

def barrel(mb, x, y, z=0.0, r=0.29, h=0.86, lid="wood_dark", stave="wood_planks", hoop="steel_dark", tone=1.0,
           lying=False, rot=0.0, sides=12):
    prof = [(r * 0.86, 0.0), (r * 0.94, h * 0.12), (r, h * 0.3), (r * 1.02, h * 0.5), (r, h * 0.7), (r * 0.94, h * 0.88),
            (r * 0.86, h)]
    if lying:
        M = T((x, y, z + r * 1.02)) @ Rz(rot) @ Matrix.Rotation(math.radians(90), 4, "Y") @ T((0, 0, -h / 2))
    else:
        M = T((x, y, z)) @ Rz(rot)
    with mb.at(M=M):
        mb.lathe(prof, stave, sides=sides, cap_top=False, cap_bot=False, tone=tone)
        for hz, hr in ((0.07, 0.9), (0.25, 0.99), (0.75, 0.99), (0.93, 0.9)):
            mb.lathe([(r * hr + 0.009, h * hz - 0.022), (r * hr + 0.009, h * hz + 0.022)], hoop,
                     sides=sides, cap_top=False, cap_bot=False, smooth_=True)
        mb.cyl(r * 0.84, 0.02, lid, loc=(0, 0, h - 0.035), sides=sides)
        mb.cyl(r * 0.84, 0.02, lid, loc=(0, 0, 0.015), sides=sides)


def crate(mb, x, y, z=0.0, s=(0.6, 0.5, 0.45), rot=0.0, mat="wood_planks", tone=1.0, slats=True):
    with mb.at((x, y, z), (0, 0, rot)):
        sx, sy, sz = s
        mb.boxc((sx - 0.02, sy - 0.02, sz - 0.02), mat, loc=(0, 0, sz / 2), tone=tone * 0.95, uvoff=True)
        if slats:
            t = 0.022
            w = 0.07
            for (ax, ay) in ((1, 0), (0, 1)):
                pass
            for sgx in (-1, 1):
                for sgy in (-1, 1):
                    mb.boxc((w, w, sz), mat, loc=(sgx * (sx / 2 - w / 2), sgy * (sy / 2 - w / 2), sz / 2), tone=tone, bev=0.006)
            for sgz in (0, 1):
                zz = 0.035 if sgz == 0 else sz - 0.035
                for sgy in (-1, 1):
                    mb.boxc((sx - 2 * w, t, w), mat, loc=(0, sgy * (sy / 2 - t / 2 + 0.005), zz), tone=tone)
                for sgx in (-1, 1):
                    mb.boxc((t, sy - 2 * w, w), mat, loc=(sgx * (sx / 2 - t / 2 + 0.005), 0, zz), tone=tone)
            # diagonal brace on the long faces
            for sgy in (-1, 1):
                mb.span((-sx / 2 + w, sgy * (sy / 2 + 0.004), 0.07), (sx / 2 - w, sgy * (sy / 2 + 0.004), sz - 0.07), w, t, mat,
                        up=(0, sgy, 0))


def sack(mb, x, y, z=0.0, r=0.24, h=0.62, rot=0.0, mat="canvas", tone=None):
    """Burlap sack: slumped body, shoulders, a gathered neck tied with twine and a tuft above the tie."""
    tone = mb.tone(0.68, 0.82) if tone is None else tone
    prof = [(r * 0.9, 0.0), (r * 1.04, h * 0.12), (r * 1.06, h * 0.4), (r * 0.96, h * 0.66), (r * 0.62, h * 0.8),
            (r * 0.26, h * 0.86), (r * 0.2, h * 0.88)]
    with mb.at((x, y, z), (0, 0, rot)):
        mb.lathe(prof, mat, sides=10, cap_top=False, tone=tone)
        mb.lathe([(r * 0.21, h * 0.875), (r * 0.21, h * 0.915)], "leather", sides=8, cap_top=False, cap_bot=False)
        mb.lathe([(r * 0.2, h * 0.91), (r * 0.36, h * 0.97), (r * 0.3, h * 1.0), (0.0, h * 1.01)], mat, sides=8,
                 cap_bot=False, tone=tone * 0.95)


def bench(mb, x, y, z=0.0, L=1.8, rot=0.0, wood="wood_dark", iron="cast_iron", back=True):
    with mb.at((x, y, z), (0, 0, rot)):
        for i in range(3):
            mb.boxc((L, 0.1, 0.035), wood, loc=(0, -0.13 + i * 0.12, 0.45), bev=0.006, tone=mb.tone(0.85, 1.0), uvoff=True)
        if back:
            for i in range(2):
                mb.boxc((L, 0.035, 0.1), wood, loc=(0, 0.2 + i * 0.02, 0.62 + i * 0.16), rot=(-12, 0, 0), bev=0.006,
                        tone=mb.tone(0.85, 1.0), uvoff=True)
        for sx in (-L / 2 + 0.15, L / 2 - 0.15):
            mb.boxc((0.05, 0.42, 0.04), iron, loc=(sx, 0.0, 0.41))
            mb.span((sx, -0.17, 0.0), (sx, -0.17, 0.43), 0.045, 0.045, iron)
            mb.span((sx, 0.17, 0.0), (sx, 0.22, 0.43), 0.045, 0.045, iron)
            if back:
                mb.span((sx, 0.21, 0.43), (sx, 0.27, 0.92), 0.04, 0.04, iron)
            mb.span((sx, -0.2, 0.43), (sx, -0.2, 0.62), 0.035, 0.035, iron)
            mb.boxc((0.05, 0.3, 0.035), iron, loc=(sx, -0.08, 0.63))


def tool_lean(mb, x, y, z, kind="shovel", rot=0.0, lean=14):
    with mb.at((x, y, z), (lean, 0, rot)):
        if kind == "shovel":
            mb.cyl(0.018, 1.05, "wood_timber", loc=(0, 0, 0.3), sides=6)
            mb.box((0.24, 0.025, 0.3), "steel_dark", loc=(0, 0, 0.0), bev=0.004)
            mb.box((0.12, 0.04, 0.03), "wood_timber", loc=(0, 0, 1.33))
        else:  # pickaxe standing on its head
            mb.cyl(0.02, 0.9, "wood_timber", loc=(0, 0, 0.0), sides=6)
            mb.span((-0.32, 0, 0.95), (0.32, 0, 0.92), 0.04, 0.05, "steel_dark")
