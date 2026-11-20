"""Reusable detail parts for the mine kit (all write into an mk.MB)."""
import math
import random

from mathutils import Matrix, Vector, noise

from mk import DEG, MB, frame, rotm, trs, smoothstep

# Reference drift profile (docs in NODES.md): walls at x = +-2.2 vertical to 2.5 m, elliptical arch to 3.8 m.
DRIFT_W, DRIFT_SPRING, DRIFT_H = 4.4, 2.5, 3.8


def drift_roof(x):
    a = DRIFT_W / 2
    t = min(1.0, abs(x) / a)
    return DRIFT_SPRING + (DRIFT_H - DRIFT_SPRING) * math.sqrt(max(0.0, 1 - t * t))


# ---------------------------------------------------------------- wood

def timber_warp(L, rng, bow=0.008, twist=1.5, ends=0.012, taper=0.0, w=0.25, h=0.25):
    """Deformation for a beam built along local X (centred, length L): bow, twist, rough saw-cut ends."""
    bx, by = rng.uniform(-1, 1) * bow * L, rng.uniform(-1, 1) * bow * L
    tw = rng.uniform(-1, 1) * twist * DEG
    o = Vector((rng.uniform(-9, 9), rng.uniform(-9, 9), rng.uniform(-9, 9)))

    def warp(v):
        t = v.x / L + 0.5  # 0..1
        s = math.sin(t * math.pi)
        a = tw * (t - 0.5)
        y, z = v.y, v.z
        y, z = y * math.cos(a) - z * math.sin(a), y * math.sin(a) + z * math.cos(a)
        k = 1.0 - taper * t
        v = Vector((v.x, y * k + by * s, z * k + bx * s))
        if abs(v.x) > L / 2 - 0.03:
            sg = 1 if v.x > 0 else -1
            v.x += sg * ends * noise.noise(Vector((v.y * 7, v.z * 7, sg * 3)) + o)
        return v
    return warp


def timber(mb, a, b, w, h, mat="wood_timber", up=(0, 0, 1), bevel=0.016, seg=1, cuts=4, bow=0.006, twist=1.2,
           ends=0.01, slant=0.0, roll=0.0):
    """Rough-sawn timber member a->b with chamfered edges, slight bow/twist and uneven ends."""
    a, b = Vector(a), Vector(b)
    L = (b - a).length
    rng = mb.rng
    wp = timber_warp(L, rng, bow, twist, ends, 0.0, w, h)
    sl = slant

    def warp(v):
        v = wp(v)
        if sl and abs(v.x) > L / 2 - 0.03:
            v.x += math.copysign(1, v.x) * v.z * sl
        return v
    return mb.beam(a, b, w, h, mat, up=up, bevel=bevel, seg=seg, cuts=cuts, warp=warp, roll=roll)


def board(mb, a, b, w, t, mat="wood_planks", up=(0, 0, 1), bevel=0.005, roll=0.0, cuts=0):
    rng = mb.rng
    L = (Vector(b) - Vector(a)).length
    wp = timber_warp(L, rng, bow=0.004, twist=2.0, ends=0.006, w=w, h=t)
    return mb.beam(a, b, w, t, mat, up=up, bevel=bevel, seg=1, cuts=cuts or None, warp=wp, roll=roll)


def wedge(mb, center, L, w, t, mat="wood_timber", rot=(0, 0, 0)):
    """Tapered wedge along local X (thick end at +X), resting on its flat face."""
    def warp(v):
        k = 0.12 + 0.88 * (v.x / L + 0.5)
        return Vector((v.x, v.y, v.z * k))
    return mb.box((L, w, t), mat, loc=center, rot=rot, bevel=0.003, seg=1, warp=warp)


# ---------------------------------------------------------------- fasteners

def hexnut(mb, c, r, h, axis=(0, 0, 1), mat="steel_dark", rot0=0.0):
    a = Vector(axis).normalized()
    q = a.to_track_quat("Z", "Y").to_matrix().to_4x4()
    Mx = Matrix.Translation(Vector(c)) @ q @ rotm((0, 0, rot0))
    return mb.cyl(r, h, mat, sides=6, Mx=Mx, bevel=min(r, h) * 0.12, seg=1)


def bolt(mb, c, axis, r=0.008, head=0.012, stud=0.02, mat="steel_dark", washer=True):
    """Hex bolt head (+ washer) sitting on a surface at c, protruding along axis."""
    a = Vector(axis).normalized()
    c = Vector(c)
    if washer:
        q = a.to_track_quat("Z", "Y").to_matrix().to_4x4()
        mb.cyl(head * 1.45, head * 0.18, mat, sides=10, Mx=Matrix.Translation(c) @ q)
        c = c + a * head * 0.18
    hexnut(mb, c, head, head * 0.7, a, mat, rot0=mb.rng.uniform(0, 60))
    if stud > 0:
        mb.rod(c + a * head * 0.7, c + a * (head * 0.7 + stud), r, mat, sides=6)


def rivet(mb, c, axis, r=0.007, mat="steel_dark"):
    a = Vector(axis).normalized()
    q = a.to_track_quat("Z", "Y").to_matrix().to_4x4()
    mb.lathe([(r, 0.0), (r * 0.95, r * 0.35), (r * 0.6, r * 0.65), (0.0, r * 0.75)], mat, sides=8,
             Mx=Matrix.Translation(Vector(c)) @ q, cap0=False)


def staple(mb, p0, p1, normal, r=0.007, depth=0.035, mat="steel_dark"):
    """Timber dog / staple: a U of round bar from p0 to p1, legs driven into the wood along -normal."""
    n = Vector(normal).normalized()
    p0, p1 = Vector(p0), Vector(p1)
    lift = r * 1.2
    pts = [p0 - n * depth, p0 + n * lift, p1 + n * lift, p1 - n * depth]
    mb.tube([pts[0], pts[0].lerp(pts[1], 0.8), pts[1], pts[1].lerp(pts[2], 0.1), pts[2].lerp(pts[1], 0.1), pts[2],
             pts[3].lerp(pts[2], 0.8), pts[3]], r, mat, sides=6)


def chain(mb, p0, p1, link_len=0.045, wire=0.0045, mat="steel_dark", sides=6, segs=8):  # noqa: E501
    """Welded link chain from p0 to p1 (straight), links alternate 90 degrees."""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    L = d.length
    pitch = link_len - 2 * wire * 1.2
    n = max(1, int(L / pitch))
    pitch = L / n
    dirv = d.normalized()
    side0 = dirv.cross(Vector((0, 0, 1)) if abs(dirv.z) < 0.9 else Vector((1, 0, 0))).normalized()
    for i in range(n):
        c = p0 + dirv * (pitch * (i + 0.5))
        side = side0 if i % 2 == 0 else dirv.cross(side0).normalized()
        hw = link_len * 0.32
        hl = link_len / 2 - wire
        pts = []
        for k in range(segs):
            t = k / segs * 2 * math.pi
            # stadium shape
            x = math.cos(t) * hw
            y = math.sin(t) * hl
            pts.append(c + side * x + dirv * y)
        mb.tube(pts, wire, mat, sides=sides, closed=True)


def s_hook(mb, top, r=0.022, wire=0.005, mat="steel_dark", side=(1, 0, 0)):
    """S-hook whose upper curve hangs on `top`; returns the lowest inside point of the lower curve."""
    top = Vector(top)
    sx = Vector(side).normalized()
    up = Vector((0, 0, 1))
    c1 = top - up * r          # upper circle centre (top of the curve = `top`)
    c2 = c1 - up * (2 * r)     # lower circle centre
    pts = []
    for k in range(11):        # upper: from the open end (right) over the top, down the left, to the S centre
        t = math.radians(-10 + 280 * k / 10)
        pts.append(c1 + sx * (r * math.cos(t)) + up * (r * math.sin(t)))
    for k in range(1, 11):     # lower: from the S centre clockwise around to the open end (left)
        t = math.radians(90 - 280 * k / 10)
        pts.append(c2 + sx * (r * math.cos(t)) + up * (r * math.sin(t)))
    mb.tube(pts, wire, mat, sides=6)
    return c2 - up * (r - wire)


def j_hook(mb, wall_pt, normal, reach=0.10, rr=0.03, wire=0.007, mat="galvanized"):
    """Cable J-hook driven into a wall: shank out along `normal`, then a U opening upward.
    Returns the point where a cable resting in the hook has its centre (for cable radius ~0.02)."""
    n = Vector(normal).normalized()
    up = Vector((0, 0, 1))
    w = Vector(wall_pt)
    pts = [w - n * 0.03, w + n * (reach * 0.5)]
    c = w + n * reach - up * rr
    for k in range(13):
        t = math.radians(90 - 290 * k / 12)
        pts.append(c + n * (rr * math.cos(t)) + up * (rr * math.sin(t)))
    mb.tube(pts, wire, mat, sides=6)
    q = n.to_track_quat("Z", "Y").to_matrix().to_4x4()
    mb.cyl(wire * 2.2, 0.008, mat, sides=8, Mx=Matrix.Translation(w) @ q)
    return c - up * (rr - wire - 0.02)


def ring(mb, c, r, wire, axis=(0, 0, 1), mat="steel_dark", segs=16, sides=6):
    a = Vector(axis).normalized()
    q = a.to_track_quat("Z", "Y").to_matrix()
    pts = [Vector(c) + q @ Vector((math.cos(t) * r, math.sin(t) * r, 0)) for t in
           [k / segs * 2 * math.pi for k in range(segs)]]
    mb.tube(pts, wire, mat, sides=sides, closed=True)


def handle_bar(mb, p0, p1, normal, stand=0.05, r=0.009, mat="steel"):
    """Grab handle: two standoffs + bar, from p0 to p1 on a surface with outward normal."""
    n = Vector(normal).normalized()
    p0, p1 = Vector(p0), Vector(p1)
    d = (p1 - p0)
    rr = min(stand * 0.6, d.length * 0.2)
    pts = [p0, p0 + n * (stand - rr)]
    for k in range(1, 4):
        t = k / 4 * math.pi / 2
        pts.append(p0 + n * (stand - rr) + n * (math.sin(t) * rr) + d.normalized() * ((1 - math.cos(t)) * rr))
    pts += [p1 - d.normalized() * rr + n * stand]
    for k in range(1, 4):
        t = k / 4 * math.pi / 2
        pts.append(p1 - d.normalized() * rr + n * stand + d.normalized() * (math.sin(t) * rr) - n * ((1 - math.cos(t)) * rr))
    pts.append(p1)
    mb.tube(pts, r, mat, sides=8)


def hinge(mb, c, h, r=0.012, axis=(0, 0, 1), mat="steel_dark"):
    a = Vector(axis).normalized()
    c = Vector(c)
    mb.rod(c - a * h / 2, c + a * h / 2, r, mat, sides=8, bevel=0.002)


def louvres(mb, center, w, h, n, mat, depth=0.03, angle=40, rot=(0, 0, 0), frame_mat=None, t=0.004):
    """Row of angled slats in a frame, in local XZ facing -Y (front), centred."""
    Mx0 = trs(center, rot)
    fm = frame_mat or mat
    fw = 0.025
    for (x, z, sw, sh) in ((0, h / 2 - fw / 2, w, fw), (0, -h / 2 + fw / 2, w, fw), (-w / 2 + fw / 2, 0, fw, h),
                           (w / 2 - fw / 2, 0, fw, h)):
        mb.box((sw, depth, sh), fm, center=True, Mx=Mx0 @ Matrix.Translation((x, 0, z)), bevel=0.003, seg=1)
    pitch = (h - 2 * fw) / n
    for i in range(n):
        z = -h / 2 + fw + pitch * (i + 0.5)
        Mx = Mx0 @ Matrix.Translation((0, -depth * 0.1, z)) @ rotm((-angle, 0, 0))
        mb.box((w - 2 * fw, pitch * 1.25, t), mat, center=True, Mx=Mx)


def bracket_plate(mb, c, w, h, t, normal=(0, -1, 0), mat="steel_dark", bolts=2):
    n = Vector(normal).normalized()
    Mx = Matrix.Translation(Vector(c)) @ frame(Vector((1, 0, 0)) if abs(n.x) < 0.9 else Vector((0, 1, 0)), n)
    mb.box((w, h, t), mat, Mx=Mx, center=True, bevel=0.002, seg=1)


# ---------------------------------------------------------------- wheels

def flanged_wheel_profile(r_tread, flange=0.022, width=0.075, hub_r=0.05, hub_w=0.11, web=0.018):
    """Lathe profile (r, z) of a cast mine-car wheel, axis = local Z, flange on the -Z (inner) side."""
    w = width
    return [
        (0.0, -hub_w / 2), (hub_r, -hub_w / 2), (hub_r * 1.08, -hub_w / 2 + 0.008),
        (hub_r * 1.25, -web / 2 - 0.004), (r_tread * 0.72, -web / 2), (r_tread - 0.02, -w / 2 + 0.006),
        (r_tread + flange * 0.6, -w / 2 - 0.004), (r_tread + flange, -w / 2 + 0.006), (r_tread + flange * 0.85, -w / 2 + 0.016),
        (r_tread + 0.002, -w / 2 + 0.026), (r_tread * 0.985, w / 2 - 0.006), (r_tread * 0.95, w / 2),
        (r_tread * 0.74, web / 2), (hub_r * 1.25, web / 2 + 0.004), (hub_r * 1.08, hub_w / 2 - 0.008),
        (hub_r, hub_w / 2), (0.0, hub_w / 2),
    ]
