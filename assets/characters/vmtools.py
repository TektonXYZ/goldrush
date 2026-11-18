"""vmtools: the four first-person tools of viewmodel.glb, each modelled in its own DESIGN frame:
+Y = the working direction (pick point, chisel, core bit), +Z = up, +X = right, as if held straight ahead.

Tool.grips[side] = (4x4 grip frame in design space, handle radius, wrap radius). A grip frame's Z runs along
the handle from the hand's pinky side to its index side; its -Y is the hand's distal (finger) direction.
Tool.tips = {empty name: design-space point} (impact / dust FX points for the game).
Tool.subs = [(child object, pivot)]: separately animated child nodes (the core bit spins).
"""
import math

import bpy
from mathutils import Matrix, Vector, noise

import bk
import ck
from ck import V


class Tool:
    def __init__(self, name):
        self.name = name
        self.obj = None
        self.subs = []
        self.grips = {}
        self.tips = {}
        self.extra = {}


def grip(o, z_dir, distal, r, wrap_r=None):
    return (ck.zframe(o, z_dir, -V(distal)), r, wrap_r or r)


def ptube(md, start, direction, up, prof, n, mat, cap0=None, cap1=None, p=2.0, mats=None, part=0, phase=0.0):
    """Tube along a straight axis. prof = [(s, r) | (s, rx, ry)]; mats[i] = material of segment i."""
    d = V(direction).normalized()
    pts = [V(start) + d * q[0] for q in prof]
    rad = [((q[1], q[2]) if len(q) > 2 else (q[1], q[1])) for q in prof]
    mf = (lambda i, k: mats[min(i, len(mats) - 1)]) if mats else None
    return ck.tube(md, pts, lambda i, s: rad[i], n, mat, up=up, p=p, cap0=cap0, cap1=cap1, matfn=mf, part=part,
                   phase=phase)


def ribs(s0, s1, r_hi, r_lo, pitch):
    """Alternating ring radii for a ribbed rubber grip between s0 and s1."""
    out = []
    s = s0
    k = 0
    while s <= s1 + 1e-9:
        out.append((s, r_hi if k % 2 == 0 else r_lo))
        s += pitch / 2
        k += 1
    return out


def finish(md, name, sharp=38.0):
    o = md.to_object(name, smooth=True)
    try:
        o.data.set_sharp_from_angle(angle=math.radians(sharp))
    except Exception:
        pass
    return o


def interp_prof(prof, s):
    for a, b in zip(prof, prof[1:]):
        if a[0] <= s <= b[0]:
            u = (s - a[0]) / (b[0] - a[0])
            return [x + (y - x) * u for x, y in zip(a[1:], b[1:])]
    return list(prof[0][1:]) if s < prof[0][0] else list(prof[-1][1:])


def head_md(prof, droop_p, droop_a, zc, n=16, step=0.0045, collar=None, mat="steel_dark"):
    """Forged pick head: a tube along a drooping centreline (adze edge at -Y ... pick tip at +Y), with
    per-ring superellipse sections (thickness along Z, width along X, power), + an eye collar box."""
    md = ck.MeshData()
    s0, s1 = prof[0][0], prof[-1][0]
    ss = []
    s = s0
    while s < s1:
        ss.append(s)
        near_end = min(s - s0, s1 - s)
        s += step * (0.45 if near_end < 0.02 else 1.0)
    ss.append(s1)
    pts = [V((0, q, zc - (droop_p if q > 0 else droop_a) * q * q)) for q in ss]
    rad = [interp_prof(prof, q) for q in ss]
    ck.tube(md, pts, lambda i, s_: (rad[i][0], rad[i][1], rad[i][2]), n, mat, up=(0, 0, 1), cap0="flat",
            cap1=("dome", 2, rad[-1][0] * 0.8))
    if collar:
        size, bev = collar
        ck.rbox(md, size, ck.T(0, 0, zc + 0.001), mat, bevel=bev, seg=3)
    return md


def forge(md, name, voxel, tris, steel_zone, chips=(0.15, 0.2), seed=3):
    """Voxel-union a head, decimate, then forging noise + chipped tips; bright 'steel' where worn."""
    def mf(c, n, part, m):
        return "steel" if steel_zone(c) else "steel_dark"

    o = ck.remesh_transfer(md, name, voxel, tris, smooth_iter=1, smooth_fac=0.25, matfn=mf)
    me = o.data
    lo, hi = chips
    for v in me.vertices:
        co = v.co.copy()
        d = 0.00025 * noise.noise(co * 160.0 + V((seed, 0, 0)))
        t = ck.smoothstep(lo, hi, abs(co.y))
        if t > 0:
            nz = noise.noise(co * 95.0 + V((0, seed * 3.1, 0)))
            d -= 0.0013 * t * max(0.0, nz - 0.15)
        v.co = co + v.normal * d
    ck.box_uv(o)
    try:
        me.set_sharp_from_angle(angle=math.radians(50))
    except Exception:
        pass
    return o


def join(objs, name):
    o = bk.join(objs, name)
    return o


# ====================================================================== pickaxe

PICK_HEAD_Z = 0.432
GRIP_L_Z = -0.245


def pickaxe():
    t = Tool("vm_pickaxe")
    md = ck.MeshData()
    secs = [(-0.300, 0.0118, 0.0096), (-0.2972, 0.0196, 0.0158), (-0.2905, 0.0226, 0.0180), (-0.2810, 0.0224, 0.0178),
            (-0.2690, 0.0207, 0.0161), (-0.2530, 0.0192, 0.0146), (-0.200, 0.0186, 0.0138), (-0.100, 0.0184, 0.0136),
            (0.000, 0.0185, 0.0137), (0.100, 0.0189, 0.0140), (0.200, 0.0198, 0.0146), (0.290, 0.0213, 0.0154),
            (0.360, 0.0232, 0.0164), (0.405, 0.0246, 0.0172), (0.468, 0.0246, 0.0172), (0.4712, 0.0205, 0.0142)]
    pts = [V((0, 0, z)) for z, _, _ in secs]
    ck.tube(md, pts, lambda i, s: (secs[i][1], secs[i][2]), 16, "wood_dark", up=(0, 1, 0), p=2.1,
            cap0="flat", cap1="flat")
    ck.rbox(md, (0.0034, 0.038, 0.0095), ck.T(0, 0, 0.4688), "steel", bevel=0.0008, seg=1)  # wedge
    handle = finish(md, "vm_pickaxe_handle", 50)
    prof = [(-0.191, 0.0013, 0.0212, 5.0), (-0.180, 0.0030, 0.0216, 5.0), (-0.155, 0.0062, 0.0210, 4.6),
            (-0.120, 0.0108, 0.0196, 4.2), (-0.080, 0.0160, 0.0180, 3.8), (-0.040, 0.0200, 0.0168, 3.4),
            (0.000, 0.0215, 0.0175, 3.2), (0.040, 0.0205, 0.0160, 3.0), (0.090, 0.0165, 0.0128, 2.8),
            (0.140, 0.0115, 0.0092, 2.6), (0.180, 0.0068, 0.0058, 2.4), (0.205, 0.0032, 0.0030, 2.2),
            (0.216, 0.0012, 0.0012, 2.0)]
    hm = head_md(prof, 0.62, 0.60, PICK_HEAD_Z, collar=((0.050, 0.068, 0.058), 0.008))
    head = forge(hm, "vm_pickaxe_head", 0.0007, 1150, lambda c: c.y > 0.168 or c.y < -0.150, chips=(0.15, 0.205))
    t.obj = join([handle, head], "vm_pickaxe")
    t.grips["R"] = grip(V((0, 0, 0)), (0, 0, 1), (0, 1, 0), 0.0161, 0.0165)
    t.grips["L"] = grip(V((0, 0, GRIP_L_Z)), (0, 0, 1), (0, 1, 0), 0.0164, 0.0168)
    t.tips["vm_pickaxe_tip"] = V((0, 0.216, PICK_HEAD_Z - 0.62 * 0.216 ** 2))
    return t


def steelpick():
    t = Tool("vm_steelpick")
    md = ck.MeshData()
    prof = [(0.0, 0.0150, 0.0128), (0.003, 0.0232, 0.0200), (0.011, 0.0238, 0.0206), (0.021, 0.0214, 0.0182),
            (0.028, 0.0199, 0.0164)]
    for s, r in ribs(0.036, 0.328, 0.0201, 0.0191, 0.036):
        prof.append((s, r, r * 0.82))
    prof += [(0.336, 0.0204, 0.0170), (0.352, 0.0212, 0.0176), (0.362, 0.0200, 0.0164), (0.366, 0.0150, 0.0118)]
    ptube(md, (0, 0, -0.300), (0, 0, 1), (0, 1, 0), prof, 14, "rubber", cap0="flat", cap1="flat", p=2.2)
    grip_o = finish(md, "vm_steelpick_grip", 45)
    hm = ck.MeshData()
    shank = [(0.050, 0.0118, 0.0080, 2.8), (0.200, 0.0122, 0.0082, 2.8), (0.330, 0.0134, 0.0090, 2.8),
             (0.405, 0.0160, 0.0105, 2.8)]
    pts = [V((0, 0, q[0])) for q in shank]
    ck.tube(hm, pts, lambda i, s: (shank[i][1], shank[i][2], shank[i][3]), 14, "steel_dark", up=(0, 1, 0),
            cap0="flat", cap1="flat")
    hp = [(-0.172, 0.0012, 0.0232, 5.0), (-0.160, 0.0030, 0.0236, 5.0), (-0.135, 0.0064, 0.0226, 4.6),
          (-0.100, 0.0110, 0.0204, 4.2), (-0.060, 0.0160, 0.0178, 3.6), (-0.025, 0.0192, 0.0158, 3.2),
          (0.000, 0.0200, 0.0160, 3.0), (0.040, 0.0182, 0.0140, 3.0), (0.100, 0.0140, 0.0108, 2.8),
          (0.160, 0.0094, 0.0076, 2.5), (0.205, 0.0052, 0.0046, 2.3), (0.228, 0.0022, 0.0020, 2.1),
          (0.236, 0.0009, 0.0009, 2.0)]
    head = head_md(hp, 0.30, 0.42, PICK_HEAD_Z, collar=((0.040, 0.058, 0.050), 0.010))
    hm.add(head)
    head_o = forge(hm, "vm_steelpick_head", 0.0007, 950, lambda c: c.y > 0.185 or c.y < -0.135,
                   chips=(0.17, 0.22), seed=11)
    t.obj = join([grip_o, head_o], "vm_steelpick")
    t.grips["R"] = grip(V((0, 0, 0)), (0, 0, 1), (0, 1, 0), 0.0178, 0.0180)
    t.grips["L"] = grip(V((0, 0, GRIP_L_Z)), (0, 0, 1), (0, 1, 0), 0.0182, 0.0184)
    t.tips["vm_steelpick_tip"] = V((0, 0.236, PICK_HEAD_Z - 0.30 * 0.236 ** 2))
    return t


# ====================================================================== jackhammer

def jackhammer():
    t = Tool("vm_jackhammer")
    md = ck.MeshData()
    sd, py, st = "steel_dark", "paint_yellow", "steel"
    # T-handle crossbar + rubber grips
    ptube(md, (-0.096, 0, 0), (1, 0, 0), (0, 0, 1), [(0, 0.0128), (0.192, 0.0128)], 12, sd)
    for sgn in (1, -1):
        g = [(0.0, 0.0172), (0.004, 0.0214), (0.013, 0.0214), (0.017, 0.0197)]
        g += ribs(0.021, 0.101, 0.0201, 0.0190, 0.022)
        g += [(0.105, 0.0199), (0.109, 0.0228), (0.118, 0.0236), (0.122, 0.0212)]
        ptube(md, (0.088 * sgn, 0, 0), (sgn, 0, 0), (0, 0, 1), g, 12, "rubber", cap1=("dome", 2, 0.004))
    # back head: round cast housing the T-bar passes through, end cap, oil plug
    bh = [(0.0, 0.034), (0.004, 0.044), (0.012, 0.0505), (0.058, 0.0505), (0.066, 0.046), (0.070, 0.040)]
    ptube(md, (0, -0.006, 0), (0, 1, 0), (0, 0, 1), bh, 18, py, cap0="flat")
    ptube(md, (-0.034, 0.010, 0), (1, 0, 0), (0, 0, 1), [(0, 0.017), (0.003, 0.0205), (0.065, 0.0205), (0.068, 0.017)],
          16, py, cap0="flat", cap1="flat")
    ptube(md, (0, -0.016, 0), (0, 1, 0), (0, 0, 1), [(0, 0.030), (0.004, 0.0385), (0.012, 0.0385)], 20, sd,
          cap0="flat")
    for k in range(6):
        a = k / 6 * math.tau + 0.4
        ptube(md, (0.030 * math.cos(a), -0.020, 0.030 * math.sin(a)), (0, 1, 0), (0, 0, 1),
              [(0, 0.0042), (0.006, 0.0042)], 6, "steel", cap0="flat")
    ptube(md, (0, 0.032, 0.046), (0, 0, 1), (0, 1, 0), [(0, 0.0085), (0.008, 0.0085), (0.010, 0.0065)], 10, "brass",
          cap1="flat")  # oil plug
    # body
    body = [(0.000, 0.040), (0.004, 0.046), (0.010, 0.0485), (0.048, 0.0485), (0.054, 0.0450), (0.058, 0.0425),
            (0.064, 0.0425), (0.066, 0.0515), (0.070, 0.0540), (0.090, 0.0540), (0.094, 0.0518), (0.098, 0.0540),
            (0.124, 0.0540), (0.128, 0.0518), (0.132, 0.0540), (0.230, 0.0540), (0.234, 0.0518), (0.238, 0.0540),
            (0.256, 0.0540), (0.262, 0.0500), (0.266, 0.0420), (0.284, 0.0420), (0.288, 0.0440), (0.312, 0.0440),
            (0.318, 0.0405), (0.330, 0.0345), (0.338, 0.0305), (0.352, 0.0305), (0.356, 0.0240)]
    mats = []
    for i in range(len(body) - 1):
        s = body[i][0]
        mats.append(py if 0.064 <= s < 0.262 else sd)
    ptube(md, (0, 0.060, 0), (0, 1, 0), (0, 0, 1), body, 18, sd, cap0="flat", cap1="flat", mats=mats)
    # tie rods + nuts
    for sx in (1, -1):
        ptube(md, (0.0575 * sx, 0.066, -0.010), (0, 1, 0), (0, 0, 1), [(0, 0.0060), (0.292, 0.0060)], 8, st)
        for y in (0.074, 0.350):
            ptube(md, (0.0575 * sx, y - 0.006, -0.010), (0, 1, 0), (0, 0, 1), [(0, 0.0108), (0.012, 0.0108)], 6, sd,
                  cap0="flat", cap1="flat", phase=math.radians(30))
    # chisel (hex shank, collar, moil point)
    ptube(md, (0, 0.392, 0), (0, 1, 0), (0, 0, 1), [(0, 0.0150), (0.078, 0.0150)], 6, sd, cap0="flat",
          phase=math.radians(30))
    ptube(md, (0, 0.468, 0), (0, 1, 0), (0, 0, 1), [(0, 0.0165), (0.004, 0.0215), (0.016, 0.0215), (0.020, 0.0160)],
          12, sd, cap0="flat")
    shaft = [(0, 0.0135), (0.03, 0.0131), (0.08, 0.0122), (0.13, 0.0102), (0.17, 0.0072), (0.196, 0.0040),
             (0.208, 0.0014)]
    ptube(md, (0, 0.488, 0), (0, 1, 0), (0, 0, 1), shaft, 12, sd, cap1=("dome", 2, 0.0015),
          mats=[sd, sd, sd, st, st, st])
    # retainer latch: spring wire looping over the chisel collar
    lp = [V((0.033, 0.398, 0.004)), V((0.034, 0.440, 0.006)), V((0.031, 0.474, 0.008))]
    for k in range(1, 12):
        a = k / 12 * math.pi
        lp.append(V((0.031 * math.cos(a), 0.479, 0.008 + 0.031 * math.sin(a))))
    lp += [V((-0.031, 0.474, 0.008)), V((-0.034, 0.440, 0.006)), V((-0.033, 0.398, 0.004))]
    ck.tube(md, lp, 0.0042, 8, st, up=(0, 0, 1), cap0="flat", cap1="flat")
    for sx in (1, -1):
        ck.rbox(md, (0.012, 0.022, 0.022), ck.T(0.036 * sx, 0.398, 0.004), sd, bevel=0.003)
    # throttle lever under the right grip (the right hand squeezes it)
    lev = [V((0.046, 0.012, -0.020)), V((0.090, 0.013, -0.028)), V((0.140, 0.013, -0.031)), V((0.192, 0.012, -0.029))]
    ck.tube(md, lev, (0.0042, 0.0068), 8, sd, up=(0, 0, 1), p=3.0, cap0="flat", cap1=("dome", 2, 0.003))
    ck.rbox(md, (0.016, 0.020, 0.018), ck.T(0.044, 0.012, -0.026), sd, bevel=0.003)
    # air inlet: swivel elbow + claw coupling + hose stub dropping out of frame
    ptube(md, (0, 0.026, -0.090), (0, -0.25, -1), (0, 1, 0),
          [(0, 0.0130), (0.024, 0.0130), (0.027, 0.0150), (0.040, 0.0150), (0.044, 0.0122)], 12, st, cap1="flat")
    hose = [V((0, 0.016, -0.128)), V((0.004, 0.004, -0.160)), V((0.016, -0.030, -0.215)), V((0.036, -0.064, -0.290)),
            V((0.058, -0.086, -0.380))]
    ck.tube(md, hose, 0.0158, 12, "rubber", up=(0, 1, 0), cap1="flat")
    ptube(md, (0, 0.019, -0.118), (0, -0.25, -1), (0, 1, 0), [(0, 0.0190), (0.014, 0.0190)], 12, st, cap0="flat")
    t.obj = finish(md, "vm_jackhammer")
    t.grips["R"] = grip(V((0.150, 0, 0)), (-1, 0, 0), (0, 1, 0), 0.0198, 0.0228)
    t.grips["L"] = grip(V((-0.150, 0, 0)), (1, 0, 0), (0, 1, 0), 0.0198, 0.0202)
    t.tips["vm_jackhammer_tip"] = V((0, 0.696, 0))
    return t


# ====================================================================== diamond core drill

BIT_ORIGIN = V((0, 0.098, 0))


def diamonddrill():
    t = Tool("vm_diamonddrill")
    md = ck.MeshData()
    al, pb, pyl, sd = "aluminium", "plastic_black", "plastic_yellow", "steel_dark"
    # gear head + spindle + water swivel + valve
    ck.rbox(md, (0.072, 0.062, 0.084), ck.T(0, 0.062, 0.004), al, bevel=0.013, seg=2)
    ptube(md, (0, 0.090, 0), (0, 1, 0), (0, 0, 1), [(0, 0.0245), (0.010, 0.0245)], 16, sd, cap1="flat")
    ptube(md, (0, 0.074, 0), (0, 1, 0), (0, 0, 1), [(0, 0.0280), (0.010, 0.0280)], 16, "brass", cap0="flat",
          cap1="flat")
    ptube(md, (0.026, 0.079, 0), (1, 0, 0), (0, 0, 1), [(0, 0.0062), (0.022, 0.0062)], 8, "brass", cap1="flat")
    ck.rbox(md, (0.005, 0.028, 0.007), ck.T(0.047, 0.079, 0.004), "hose_red", bevel=0.0015)
    # motor housing: yellow shell, black belly, vents, rear cap
    ck.rbox(md, (0.086, 0.178, 0.106), ck.T(0, -0.052, 0.014), pyl, bevel=0.024, seg=2)
    ck.rbox(md, (0.090, 0.150, 0.046), ck.T(0, -0.046, -0.028), pb, bevel=0.016, seg=2)
    for sx in (1, -1):
        for k in range(6):
            ck.rbox(md, (0.004, 0.0075, 0.040), ck.T(0.0425 * sx, -0.108 + k * 0.0155, 0.018), pb, bevel=0.0)
    ck.rbox(md, (0.080, 0.022, 0.098), ck.T(0, -0.142, 0.012), pb, bevel=0.014, seg=2)
    # rear D-handle (rubber grip section, black bridges), trigger
    dp = [V((0, -0.128, 0.052)), V((0, -0.166, 0.062)), V((0, -0.196, 0.052)), V((0, -0.212, 0.020)),
          V((0, -0.220, -0.020)), V((0, -0.227, -0.060)), V((0, -0.218, -0.088)), V((0, -0.190, -0.098)),
          V((0, -0.152, -0.090)), V((0, -0.126, -0.066))]
    dense = []
    for i in range(len(dp) - 1):
        p0, p1, p2, p3 = dp[max(i - 1, 0)], dp[i], dp[i + 1], dp[min(i + 2, len(dp) - 1)]
        for k in range(4):
            dense.append(ck.catmull(p0, p1, p2, p3, k / 4))
    dense.append(dp[-1])
    ck.tube(md, dense, lambda i, s: (0.0146, 0.0178), 12, pb, up=(1, 0, 0), p=2.3, cap0="flat", cap1="flat",
            matfn=lambda i, k: "rubber" if -0.080 < dense[i].z < 0.040 else pb)
    ck.rbox(md, (0.0105, 0.012, 0.028), ck.T(0, -0.197, 0.006) @ ck.rot("X", -12), pb, bevel=0.003)
    ck.rbox(md, (0.006, 0.010, 0.010), ck.T(0.010, -0.206, 0.028), "plastic_yellow", bevel=0.002)
    # cable: strain relief + cable dropping out of frame
    ptube(md, (0, -0.205, -0.098), (0, -0.30, -1), (0, 1, 0), [(0, 0.0110), (0.030, 0.0076), (0.046, 0.0056)], 10,
          "rubber", cap1="flat")
    cab = [V((0, -0.218, -0.142)), V((0.006, -0.226, -0.20)), V((0.022, -0.218, -0.28)), V((0.040, -0.20, -0.38))]
    ck.tube(md, cab, 0.0048, 8, "cable", up=(0, 1, 0), cap1="flat")
    # side handle: clamp block, neck, ribbed rubber grip angled back towards the left hand
    sdir = V((-1, -0.42, -0.06)).normalized()
    mount = V((-0.040, 0.040, -0.004))
    ck.rbox(md, (0.022, 0.030, 0.034), ck.T(mount.x - 0.006, mount.y, mount.z), sd, bevel=0.004)
    ptube(md, mount + sdir * 0.012, sdir, (0, 0, 1), [(0, 0.0105), (0.018, 0.0105), (0.024, 0.0138)], 12, pb)
    g = [(0.0, 0.0150), (0.004, 0.0172)]
    g += ribs(0.008, 0.100, 0.0172, 0.0164, 0.016)
    g += [(0.104, 0.0170), (0.108, 0.0204), (0.117, 0.0210), (0.121, 0.0186)]
    ptube(md, mount + sdir * 0.036, sdir, (0, 0, 1), g, 14, "rubber", cap1=("dome", 2, 0.004))
    t.obj = finish(md, "vm_diamonddrill")
    # the core bit: its own node, spins about its local Y (Blender) = local Z (three.js)
    bm = ck.MeshData()
    prof = [(0.0, -0.001), (0.0200, 0.0), (0.0200, 0.022), (0.0225, 0.024), (0.0225, 0.034), (0.0312, 0.046),
            (0.0312, 0.344), (0.0284, 0.344), (0.0284, 0.300), (0.0, 0.300)]
    ck.lathe(bm, prof, 16, "steel_dark", M=ck.T(BIT_ORIGIN) @ ck.rot("X", -90),
             matfn=lambda i: "steel" if i < 4 else "steel_dark")
    for k in range(8):
        a = k / 8 * 360
        M = ck.T(BIT_ORIGIN) @ ck.rot("Y", a) @ ck.T(0, 0.3495, 0.0300)
        ck.rbox(bm, (0.0190, 0.0115, 0.0046), M, "steel", bevel=0.0009, seg=1)
    bit = finish(bm, "vm_diamonddrill_bit", 40)
    t.subs.append((bit, BIT_ORIGIN.copy()))
    t.grips["R"] = grip(V((0, -0.2205, -0.032)), (0, 0.14, 1), (0, 1, 0), 0.0160, 0.0166)
    lc = mount + sdir * (0.036 + 0.058)
    t.grips["L"] = grip(lc, -sdir, (0, 1, 0), 0.0168, 0.0172)
    t.extra["trigger"] = (V((0, -0.196, 0.008)), V((1, 0, 0)), 0.0055)
    t.tips["vm_diamonddrill_tip"] = V((0, BIT_ORIGIN.y + 0.355, 0))
    return t


def build():
    return {t.name: t for t in (pickaxe(), steelpick(), jackhammer(), diamonddrill())}
