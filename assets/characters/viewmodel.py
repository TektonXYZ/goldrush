"""viewmodel.glb: MOTHERLODE's first-person arms (work gloves, hi-vis sleeves, watch) + the four hand tools.

    bl assets/characters/viewmodel.py -- [out.glb] [previews_dir] [mode: full|quick|none]

Camera convention: the three.js camera sits at the origin looking down -Z with a vertical FOV of 60 (16:9).
In Blender that is a camera at the origin looking along +Y with +Z up, so everything here is authored in
"camera space": +X right, +Y forward (into the screen), +Z up (glTF export maps it to three.js exactly).

Rig: root > shoulder.L/R > upperarm > forearm > hand > 15 finger bones per hand (index/middle/ring/pinky/
thumb .01-.03). Arms are posed by a numeric two-bone IK towards hand targets; for two-handed tools both
hands are derived from the tool's transform through fixed grip frames, so the left hand never slips. Finger
grips come from glove.wrap (fingers curl joint by joint until they touch the handle). Every clip keys every
bone (three.js AnimationMixer leaves un-keyed bones wherever the previous clip put them).
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import bk  # noqa: E402
import ck  # noqa: E402
import glove  # noqa: E402
import vmtools  # noqa: E402
from ck import V  # noqa: E402

ARGS = bk.args()
OUT = os.path.abspath(ARGS[0]) if ARGS else os.path.join(HERE, "..", "..", "public", "models", "viewmodel.glb")
PREV = os.path.abspath(ARGS[1]) if len(ARGS) > 1 else os.path.join(HERE, "previews")
MODE = ARGS[2] if len(ARGS) > 2 else "full"
FPS = 80
TWO_PI = 2 * math.pi

bk.reset()
scn = bpy.context.scene
scn.render.fps = FPS

# ====================================================================== rig constants (camera space)
SH = {"R": V((0.170, 0.100, -0.300)), "L": V((-0.170, 0.100, -0.300))}
CLAV = {"R": V((0.040, 0.000, -0.270)), "L": V((-0.040, 0.000, -0.270))}
UPPER, FORE, HANDLEN = 0.290, 0.275, 0.090
POLE = {"R": V((0.85, 0.40, -1.00)), "L": V((-0.85, 0.40, -1.00))}
REST_HAND = {
    "R": ck.frame((0.190, 0.360, -0.200), (-0.15, 0.95, 0.25), (0.75, 0.0, 0.66)),
    "L": ck.frame((-0.190, 0.360, -0.200), (0.15, 0.95, 0.25), (-0.75, 0.0, 0.66)),
}


def Hgrip(side, r):
    """Grip frame in the canonical hand space of `side` for a handle of radius r (see vmtools.Tool.grips)."""
    g = V((-0.95, 0.30, 0.07))
    o = V((0.002, 0.071, -(0.0166 + r)))
    if side == "L":
        g.x, o.x = -g.x, -o.x
    g.normalize()
    fwd = V((0, 1, 0)) - g * g.y
    fwd.normalize()
    return ck.zframe(o, g, -fwd)


# ====================================================================== tools + grips
TOOLS = vmtools.build()
GRIP = {}  # tool -> side -> dict(hand_in_design, fingers)
for name, tool in TOOLS.items():
    GRIP[name] = {}
    for side, (G, r, wr) in tool.grips.items():
        H = Hgrip(side, r)
        hid = G @ H.inverted()
        c, d = H.translation, H.to_3x3() @ V((0, 0, 1))
        conv = {"index": -2.0, "middle": -0.5, "ring": 1.0, "pinky": 3.0}  # fingers converge on the handle
        fingers = glove.wrap(side, c, d, wr, skip=("thumb",),
                             spread=conv if side == "R" else {k: -x for k, x in conv.items()})
        fingers.update(glove.thumb_solve(side, c, d, wr, fingers))
        if name == "vm_diamonddrill" and side == "R":
            tp, ta, tr = tool.extra["trigger"]
            inv = hid.inverted()
            tc = inv @ tp
            td = (inv.to_3x3() @ ta).normalized()
            fingers.update(glove.wrap(side, tc, td, tr, skip=("middle", "ring", "pinky", "thumb"), natural=0.3))
        GRIP[name][side] = dict(hid=hid, fingers=fingers)
REL = {s: glove.preset("relaxed", s) for s in "RL"}
REACH = {s: glove.preset("reach", s) for s in "RL"}
FIST = {s: glove.preset("fist", s) for s in "RL"}


def tool_hands(tool, T, fR=None, fL=None):
    g = GRIP[tool]
    return dict(tool=tool, T=T, R=T @ g["R"]["hid"], L=T @ g["L"]["hid"],
                fR=fR or g["R"]["fingers"], fL=fL or g["L"]["fingers"])


# ====================================================================== poses
def pk(g, h, a):
    """Pickaxe key: right-grip position, head position, pick-point direction hint (camera space)."""
    return (V(g), V(h), V(a))


def pick_T(key):
    g, h, a = key
    return ck.zframe(g, h - g, a)


P_IDLE = pk((0.172, 0.400, -0.140), (0.338, 0.598, 0.178), (-0.55, 0.80, -0.22))
SWING = [  # (t, key, opts): the swing plane leans ~25 deg so the head shows its profile at impact
    (0.000, P_IDLE, {}),
    (0.070, pk((0.183, 0.386, -0.156), (0.352, 0.566, 0.162), (-0.50, 0.82, -0.26)), {}),
    (0.170, pk((0.214, 0.255, -0.045), (0.312, 0.150, 0.360), (-0.25, 0.55, 0.80)), {}),
    (0.228, pk((0.182, 0.098, 0.040), (0.240, -0.220, 0.292), (-0.10, 0.55, 0.83)), {}),
    (0.255, pk((0.176, 0.106, 0.046), (0.230, -0.205, 0.308), (-0.10, 0.58, 0.81)), {"ease": lambda u: u ** 1.6}),
    (0.300, pk((0.165, 0.272, 0.050), (0.172, 0.300, 0.482), (-0.20, 0.97, 0.05)), {}),
    (0.320, pk((0.138, 0.352, -0.076), (0.122, 0.545, 0.330), (-0.28, 0.88, -0.30)), {}),
    (0.3375, pk((0.100, 0.400, -0.200), (0.067, 0.692, 0.122), (-0.32, 0.75, -0.58)), {"brk": True}),
    (0.365, pk((0.112, 0.385, -0.172), (0.090, 0.655, 0.175), (-0.30, 0.80, -0.50)), {}),
    (0.450, pk((0.142, 0.388, -0.142), (0.236, 0.618, 0.206), (-0.42, 0.85, -0.32)), {}),
    (0.580, pk((0.176, 0.402, -0.137), (0.350, 0.600, 0.184), (-0.56, 0.80, -0.20)), {}),
    (0.750, P_IDLE, {}),
]
SWING_T = [ck.Track([(t, k[i], o) for t, k, o in SWING]) for i in range(3)]
P_LOW = pk((0.240, 0.330, -0.470), (0.520, 0.470, -0.300), (-0.40, 0.70, -0.60))
EQUIP = [(0.0, P_LOW, {}), (0.27, pk((0.170, 0.402, -0.128), (0.336, 0.600, 0.192), (-0.55, 0.80, -0.20)), {}),
         (0.40, P_IDLE, {})]
EQUIP_T = [ck.Track([(t, k[i], o) for t, k, o in EQUIP]) for i in range(3)]


def breathe(t, period, amp=1.0, seed=0.0):
    w = TWO_PI / period
    return V((0.0024 * math.sin(w * t + seed) + 0.0008 * math.sin(2 * w * t + 1.3 + seed),
              0.0012 * math.sin(w * t + 2.1 + seed),
              0.0042 * math.sin(w * t + 0.6 + seed) + 0.0010 * math.sin(2 * w * t + 0.2 + seed))) * amp


def pick_pose(tool, clip, t):
    if clip == "idle":
        g, h, a = P_IDLE
        b = breathe(t, 3.0)
        b2 = breathe(t, 3.0, 1.25, 0.5)
        T = pick_T((g + b, h + b2, a))
        return tool_hands(tool, T)
    if clip == "swing":
        g, h, a = (tr.at(t) for tr in SWING_T)
        T = pick_T((g, h, a))
        sq = ck.smoothstep(0.27, 0.33, t) * (1 - ck.smoothstep(0.40, 0.55, t))
        fR = glove.squeeze(GRIP[tool]["R"]["fingers"], 7 * sq, "R")
        fL = glove.squeeze(GRIP[tool]["L"]["fingers"], 7 * sq, "L")
        return tool_hands(tool, T, fR, fL)
    if clip == "equip":
        g, h, a = (tr.at(t) for tr in EQUIP_T)
        return tool_hands(tool, pick_T((g, h, a)))
    raise ValueError(clip)


def tframe(pos, fwd, up):
    return ck.frame(pos, fwd, up)


H_IDLE = (V((0.170, 0.360, -0.172)), V((-0.253, 0.954, 0.164)), V((0.03, -0.17, 1.0)))
H_USE = (V((0.166, 0.374, -0.160)), V((-0.245, 0.950, 0.192)), V((0.03, -0.20, 1.0)))
H_LOW = (V((0.20, 0.30, -0.52)), V((0.05, 0.85, -0.55)), V((0.05, 0.55, 0.85)))
D_IDLE = (V((0.170, 0.500, -0.085)), V((-0.321, 0.942, 0.096)), V((0.0, -0.10, 1.0)))
D_USE = (V((0.166, 0.512, -0.080)), V((-0.312, 0.944, 0.110)), V((0.0, -0.11, 1.0)))
D_LOW = (V((0.26, 0.40, -0.50)), V((0.05, 0.85, -0.50)), V((0.0, 0.50, 0.86)))


def held_pose(tool, kind, clip, t):
    idle, use, low = (H_IDLE, H_USE, H_LOW) if kind == "hammer" else (D_IDLE, D_USE, D_LOW)
    if clip == "idle":
        b = breathe(t, 3.0, 1.35 if kind == "hammer" else 1.15, 0.3)
        p, f, u = idle
        f2 = f + V((0.006 * math.sin(TWO_PI * t / 3 + 0.8), 0, 0.008 * math.sin(TWO_PI * t / 3 + 1.7)))
        return tool_hands(tool, tframe(p + b, f2, u))
    if clip == "use":
        p, f, u = use
        w = TWO_PI
        if kind == "hammer":  # 0.5 s loop: 20 Hz blows, 10 Hz shake, 2 Hz shove into the rock
            back = 0.0048 * (0.5 + 0.5 * math.sin(w * 20 * t))
            d = V((0.0017 * math.sin(w * 10 * t + 0.7) + 0.0010 * math.sin(w * 20 * t + 1.9),
                   -back + 0.0055 * math.sin(w * 2 * t),
                   0.0024 * math.sin(w * 20 * t + 0.4) + 0.0013 * math.sin(w * 6 * t + 0.9)))
            fj = V((0.0065 * math.sin(w * 10 * t + 0.3), 0, 0.0085 * math.sin(w * 20 * t + 1.1)))
            uj = V((0.010 * math.sin(w * 10 * t + 2.0), 0, 0))
        else:  # drill: finer buzz + torque wobble about the bit axis
            d = V((0.0009 * math.sin(w * 20 * t + 0.5) + 0.0006 * math.sin(w * 10 * t + 2.2),
                   0.0040 * math.sin(w * 2 * t) - 0.0010 * (0.5 + 0.5 * math.sin(w * 20 * t)),
                   0.0011 * math.sin(w * 20 * t + 1.4) + 0.0007 * math.sin(w * 6 * t)))
            fj = V((0.0030 * math.sin(w * 10 * t + 0.9), 0, 0.0035 * math.sin(w * 20 * t)))
            uj = V((0.022 * math.sin(w * 10 * t + 0.2), 0, 0))
        return tool_hands(tool, tframe(p + d, f + fj, u + uj))
    if clip == "equip":
        dur = 0.45
        k = ck.back_out(ck.clamp(t / (dur * 0.82)), 1.2)
        p = low[0].lerp(idle[0], k)
        f = low[1].lerp(idle[1], k)
        u = low[2].lerp(idle[2], k)
        return tool_hands(tool, tframe(p, f, u))
    raise ValueError(clip)


HI_R = (V((0.200, 0.330, -0.214)), V((-0.22, 0.90, 0.38)), V((0.62, -0.10, 0.78)))
HI_L = (V((-0.205, 0.330, -0.222)), V((0.22, 0.90, 0.38)), V((-0.62, -0.10, 0.78)))
REACH_R = (V((0.070, 0.480, -0.082)), V((-0.10, 0.96, 0.18)), V((0.18, -0.25, 0.95)))


def hands_pose(clip, t):
    if clip == "idle":
        b = breathe(t, 3.0, 1.1)
        bl = breathe(t, 3.0, 1.1, 1.4)
        R = ck.frame(HI_R[0] + b, HI_R[1], HI_R[2])
        L = ck.frame(HI_L[0] + bl, HI_L[1], HI_L[2])
        return dict(tool=None, T=None, R=R, L=L, fR=REL["R"], fL=REL["L"])
    if clip == "reach":  # 0.6 s: reach, open, grab, pull back
        out_k = ck.ease_io(ck.clamp(t / 0.24), 2.2)
        back_k = ck.ease_io(ck.clamp((t - 0.36) / 0.24), 2.0)
        k = out_k * (1 - back_k)
        p = HI_R[0].lerp(REACH_R[0], k)
        f = HI_R[1].lerp(REACH_R[1], k)
        u = HI_R[2].lerp(REACH_R[2], k)
        p += V((0, 0.012, 0.004)) * math.sin(math.pi * ck.clamp((t - 0.22) / 0.14))  # little push at contact
        R = ck.frame(p, f, u)
        o = ck.smoothstep(0.04, 0.20, t)
        grab = ck.smoothstep(0.25, 0.33, t) * (1 - ck.smoothstep(0.46, 0.60, t))
        fR = glove.blend(glove.blend(REL["R"], REACH["R"], o * (1 - grab)), FIST["R"], grab * 0.62)
        fR = glove.blend(fR, REL["R"], ck.smoothstep(0.50, 0.60, t))
        lift = math.sin(math.pi * ck.clamp(t / 0.6)) * 0.010
        L = ck.frame(HI_L[0] + V((0, 0.004, lift)), HI_L[1], HI_L[2])
        return dict(tool=None, T=None, R=R, L=L, fR=fR, fL=REL["L"])
    raise ValueError(clip)


CLIPS = [  # name, seconds, key step (frames), pose fn, tool shown in previews
    ("pick_idle", 3.0, 4, lambda t: pick_pose("vm_pickaxe", "idle", t), "vm_pickaxe"),
    ("pick_swing", 0.75, 1, lambda t: pick_pose("vm_pickaxe", "swing", t), "vm_pickaxe"),
    ("pick_equip", 0.40, 1, lambda t: pick_pose("vm_pickaxe", "equip", t), "vm_pickaxe"),
    ("hammer_idle", 3.0, 4, lambda t: held_pose("vm_jackhammer", "hammer", "idle", t), "vm_jackhammer"),
    ("hammer_use", 0.5, 1, lambda t: held_pose("vm_jackhammer", "hammer", "use", t), "vm_jackhammer"),
    ("hammer_equip", 0.45, 1, lambda t: held_pose("vm_jackhammer", "hammer", "equip", t), "vm_jackhammer"),
    ("drill_idle", 3.0, 4, lambda t: held_pose("vm_diamonddrill", "drill", "idle", t), "vm_diamonddrill"),
    ("drill_use", 0.5, 1, lambda t: held_pose("vm_diamonddrill", "drill", "use", t), "vm_diamonddrill"),
    ("drill_equip", 0.45, 1, lambda t: held_pose("vm_diamonddrill", "drill", "equip", t), "vm_diamonddrill"),
    ("hands_idle", 3.0, 4, lambda t: hands_pose("idle", t), None),
    ("hands_reach", 0.6, 1, lambda t: hands_pose("reach", t), None),
]

# ====================================================================== rig
rig = ck.Rig("vm_rig")
rig.add("root", None, (0, 0, 0), (0, 1, 0), (0, 0, 1), 0.06, deform=False)
for side in "RL":
    sh = f"shoulder.{side}"
    rig.add(sh, "root", CLAV[side], SH[side] - CLAV[side], (0, 0, 1), (SH[side] - CLAV[side]).length, deform=False)
    rig.length[f"upperarm.{side}"] = UPPER
    rig.length[f"forearm.{side}"] = FORE
    Hr = REST_HAND[side]
    chain, ok, E = ck.arm_chain(rig, side, SH[side], Hr.translation, Hr, POLE[side])
    assert ok, "rest pose out of reach"
    rig.add_frame(f"upperarm.{side}", sh, chain[f"upperarm.{side}"], UPPER)
    rig.add_frame(f"forearm.{side}", f"upperarm.{side}", chain[f"forearm.{side}"], FORE)
    rig.add_frame(f"hand.{side}", f"forearm.{side}", chain[f"hand.{side}"], HANDLEN)
    for n, par, M, L in glove.bone_defs(side):
        rig.add_frame(n, par, chain[f"hand.{side}"] @ M, L)
arm = rig.build()


def solve(ps):
    P = {"root": rig.rest["root"]}
    oks = True
    for side in "RL":
        sh = f"shoulder.{side}"
        P[sh] = rig.fk(sh, P, Matrix.Identity(4))
        S = P[sh] @ V((0, rig.length[sh], 0))
        Hm = ps[side]
        chain, ok, _ = ck.arm_chain(rig, side, S, Hm.translation, Hm, POLE[side])
        oks = oks and ok
        P.update(chain)
        fp = ps["f" + side]
        for n, par, M, L in glove.bone_defs(side):
            P[n] = rig.fk(n, P, fp.get(n, Matrix.Identity(4)))
    return P, oks


# ====================================================================== meshes
def mirror_obj(src, name):
    o = src.copy()
    o.data = src.data.copy()
    o.name = o.data.name = name
    bpy.context.scene.collection.objects.link(o)
    o.data.transform(Matrix.Diagonal((-1, 1, 1, 1)))
    o.data.flip_normals()
    for g in o.vertex_groups:
        if g.name.endswith(".R"):
            g.name = g.name[:-2] + ".L"
    return o


def place(obj, M):
    obj.data.transform(M)
    obj.data.update()
    return obj


import time
T0 = time.time()
print("[vm] building gloves")
gR = ck.remesh_transfer(glove.build("R", 1.0), "glove_R", 0.0011, 2050, smooth_iter=3, smooth_fac=0.45,
                        iso=("leather", "fabric_glove"))
guards_md = ck.MeshData()


def guard_pads(md):
    """Rubber knuckle armour (impact gloves): pads on the MCP knuckles and on proximal/middle phalanges."""
    for f in glove.FINGERS:
        frs, lens = glove.finger_frames(f)
        rt, rw = glove.FDEF[f][3]
        head = V(glove.FDEF[f][0])
        bone = f"{f}.01.R"
        # knuckle pad (hand bone)
        M = ck.T(head + V((0, -0.002, 0.0118))) @ ck.rot("Z", -glove.FDEF[f][1]) @ ck.rot("X", 8)
        ck.rbox(md, (rw * 1.75, 0.0165, 0.0052), M, "rubber", bevel=0.0021, seg=1, w={"hand.R": 1.0})
        # proximal + middle phalanx pads
        for j, (scale_l, bone_j) in enumerate(((0.56, f"{f}.01.R"), (0.52, f"{f}.02.R"))):
            L = lens[j]
            M = frs[j] @ ck.T(0, L * 0.5, rt * (0.97 - 0.04 * j) + 0.0021)
            ck.rbox(md, (rw * 1.45 * (1 - 0.08 * j), L * scale_l, 0.0040), M, "rubber", bevel=0.0016, seg=1,
                    w={bone_j: 1.0})
    # bar joining the knuckle pads
    pts = [V(glove.FDEF[f][0]) + V((0, -0.006, 0.0105)) for f in glove.FINGERS]
    ck.tube(md, pts, (0.0028, 0.0050), 8, "rubber", up=(0, 0, 1), cap0=("dome", 2, 0.004), cap1=("dome", 2, 0.004),
            weights=lambda i, s: {"hand.R": 1.0})
    # thumb pad
    tfr, tl = glove.thumb_frames()
    M = tfr[1] @ ck.T(0, tl[1] * 0.5, glove.THUMB["radii"][1][0] * 0.95 + 0.002)
    ck.rbox(md, (0.0185, tl[1] * 0.6, 0.0040), M, "rubber", bevel=0.0016, seg=1, w={"thumb.02.R": 1.0})


guard_pads(guards_md)
padR = guards_md.to_object("pads_R", smooth=True)


def strap_md(side_sign=1):
    """Velcro wrist strap across the back of the cuff, with a pull tab on the thumb side."""
    md = ck.MeshData()
    y0, y1 = -0.0105, -0.0285
    rings = []
    for y in (y0, (y0 + y1) / 2, y1):
        t, w = glove.CUFF[1][1] + 0.0016, glove.CUFF[1][2] + 0.0016
        k = (y - 0.006) / (-0.012 - 0.006)
        t = ck.lerp(glove.CUFF[0][1], glove.CUFF[1][1], k) + 0.0018
        w = ck.lerp(glove.CUFF[0][2], glove.CUFF[1][2], k) + 0.0018
        rings.append((y, t, w))
    pts = [V((0.0006, y, -0.0012)) for y, _, _ in rings]
    ck.tube(md, pts, lambda i, s: (rings[i][1], rings[i][2]), 28, "rubber", up=(0, 0, 1), p=2.3,
            weights=lambda i, s: {"forearm.R": 0.55, "hand.R": 0.45})
    ck.rbox(md, (0.012, 0.016, 0.0032), ck.T(-0.0365, -0.0195, 0.006) @ ck.rot("Y", -60), "rubber", bevel=0.0012,
            w={"forearm.R": 0.55, "hand.R": 0.45})
    return md


strapR = strap_md().to_object("strap_R", smooth=True)
gL, padL, strapL = mirror_obj(gR, "glove_L"), mirror_obj(padR, "pads_L"), mirror_obj(strapR, "strap_L")
for o, side in ((gR, "R"), (padR, "R"), (strapR, "R"), (gL, "L"), (padL, "L"), (strapL, "L")):
    place(o, rig.rest[f"hand.{side}"])


def lcd_image():
    """Watch face: a backlit seven-segment LCD reading 06:42 (embedded texture, label_ material)."""
    W, H = 256, 128
    img = bpy.data.images.new("watch_lcd", W, H, alpha=False)
    bg = (0.42, 0.62, 0.56)
    ink = (0.05, 0.07, 0.06)
    px = [bg] * (W * H)
    seg = {"0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc", "5": "afgcd", "6": "afgedc",
           "7": "abc", "8": "abcdefg", "9": "abcfgd"}

    def rect(x0, y0, x1, y1):
        for y in range(max(0, y0), min(H, y1)):
            for x in range(max(0, x0), min(W, x1)):
                px[y * W + x] = ink

    def digit(ch, x, y, w=40, h=72, t=8):
        s = seg[ch]
        if "a" in s:
            rect(x + t, y + h - t, x + w - t, y + h)
        if "g" in s:
            rect(x + t, y + h // 2 - t // 2, x + w - t, y + h // 2 + t // 2)
        if "d" in s:
            rect(x + t, y, x + w - t, y + t)
        if "f" in s:
            rect(x, y + h // 2, x + t, y + h - t)
        if "b" in s:
            rect(x + w - t, y + h // 2, x + w, y + h - t)
        if "e" in s:
            rect(x, y + t, x + t, y + h // 2)
        if "c" in s:
            rect(x + w - t, y + t, x + w, y + h // 2)

    for i, ch in enumerate("06"):
        digit(ch, 22 + i * 50, 30)
    rect(124, 50, 132, 58)
    rect(124, 76, 132, 84)
    for i, ch in enumerate("42"):
        digit(ch, 142 + i * 50, 30)
    for k in range(5):  # little step-counter bars
        rect(30 + k * 14, 112, 40 + k * 14, 120)
    flat = []
    for c in px:
        flat += [c[0], c[1], c[2], 1.0]
    img.pixels = flat
    img.pack()
    return img


def watch_md():
    """Rugged digital watch over the LEFT glove cuff (built in canonical right space, mirrored later)."""
    md = ck.MeshData()
    y = -0.034
    t, w = 0.0262 + 0.0016, 0.0356 + 0.0016
    pts = [V((0.0006, y + 0.011, -0.0012)), V((0.0006, y - 0.011, -0.0012))]
    ck.tube(md, pts, (t + 0.0012, w + 0.0012), 28, "rubber", up=(0, 0, 1), p=2.3,
            weights=lambda i, s: {"forearm.R": 1.0})
    top = t + 0.0012
    ck.rbox(md, (0.040, 0.044, 0.0125), ck.T(0.0006, y, top + 0.005), "plastic_black", bevel=0.0042, seg=2,
            w={"forearm.R": 1.0})
    ck.rbox(md, (0.034, 0.036, 0.0030), ck.T(0.0006, y, top + 0.0112), "plastic_black", bevel=0.0012, seg=1,
            w={"forearm.R": 1.0})
    for sx in (1, -1):
        for sy in (1, -1):
            ck.rbox(md, (0.0040, 0.0050, 0.0036), ck.T(0.0006 + 0.0212 * sx, y + 0.009 * sy, top + 0.0052), "steel",
                    bevel=0.0, seg=1, w={"forearm.R": 1.0})
    # LCD face: a quad with UV 0..1 (label material keeps its texture in-game)
    z = top + 0.01275
    a, b = 0.0086, 0.0142  # long axis along the arm; text reads elbow -> hand, "up" = thumb side after mirroring
    c = V((0.0006, y, z))
    q = [md.v(c + V(o), {"forearm.R": 1.0}) for o in ((-a, -b, 0), (a, -b, 0), (a, b, 0), (-a, b, 0))]
    md.f(q, "label_watch_face", uv=((0, 1), (0, 0), (1, 0), (1, 1)))
    return md


img = lcd_image()
lab = bpy.data.materials.get("label_watch_face") or ck.material("label_watch_face", "#ffffff", rough=0.25,
                                                                  image=img, emit=True, emit_strength=0.55)
watch = watch_md().to_object("watch_R", smooth=True)
watch.data.polygons.foreach_set("use_smooth", [p.material_index != watch.data.materials.find("label_watch_face")
                                               for p in watch.data.polygons])
watchL = mirror_obj(watch, "watch_L")
bpy.data.objects.remove(watch, do_unlink=True)
place(watchL, rig.rest["hand.L"])


def sleeve(side):
    """Hi-vis jacket sleeve along the rest arm chain, with fabric folds, an elastic hem and reflective bands."""
    S = rig.head(f"upperarm.{side}")
    E = rig.head(f"forearm.{side}")
    W = rig.head(f"hand.{side}")
    yu, yf = (E - S).normalized(), (W - E).normalized()
    hem_back = 0.050 if side == "R" else 0.060
    Hm = W - yf * hem_back
    ang = yu.angle(yf)
    R = 0.07
    d = R * math.tan(ang / 2)
    A, B = E - yu * d, E + yf * d
    pts = []
    start = S - yu * 0.035
    n_up = max(2, int((A - start).length / 0.030))
    for k in range(n_up):
        pts.append(start.lerp(A, k / n_up))
    for k in range(7):
        u = k / 6
        pts.append(A * (1 - u) ** 2 + E * 2 * u * (1 - u) + B * u * u)
    n_f = max(2, int((Hm - B).length / 0.018))
    for k in range(1, n_f + 1):
        pts.append(B.lerp(Hm, k / n_f))
    s_list = [0.0]
    for i in range(1, len(pts)):
        s_list.append(s_list[-1] + (pts[i] - pts[i - 1]).length)
    total = s_list[-1]
    s_elbow = (A - start).length + (B - A).length * 0.5
    inner = (yf - yu).normalized()  # towards the inside of the elbow bend

    def radius(s):
        if s < s_elbow:
            u = s / s_elbow
            return ck.lerp(0.066, 0.058, u)
        u = (s - s_elbow) / (total - s_elbow)
        return ck.lerp(0.057, 0.0465, u ** 0.85)

    def w_at(s):
        t = ck.smoothstep(s_elbow - 0.050, s_elbow + 0.040, s)
        return {f"upperarm.{side}": 1 - t, f"forearm.{side}": t}

    fr = ck.path_frames(pts, up=(0, 0, 1))

    def ring_pts(i, extra=0.0):
        p = pts[i]
        t_, nn, bb = fr[i]
        s = s_list[i]
        r = radius(s) + extra
        out = []
        n = 18
        hem_u = ck.smoothstep(total - 0.028, total - 0.004, s)
        elb = math.exp(-((s - s_elbow) / 0.05) ** 2)
        for k in range(n):
            a = k / n * ck.TAU
            rad = nn * math.cos(a) + bb * math.sin(a)
            inn = max(0.0, rad.dot(inner))
            f = 1.0
            f += 0.020 * math.sin(3 * a + 38 * s) * (1 - hem_u) * 0.8
            f += 0.012 * math.sin(5 * a - 23 * s + 1.3)
            f += 0.045 * math.sin(70 * s) * inn * elb
            f += 0.040 * math.sin(10 * a) * hem_u
            ell = 1.0 if abs(rad.dot(nn)) > 0 else 1.0
            out.append(p + rad * (r * f * (0.93 + 0.07 * abs(math.cos(a))) * ell))
        return out

    md = ck.MeshData()
    rows, uvs = [], []
    for i in range(len(pts)):
        rp = ring_pts(i)
        rows.append([md.v(c, w_at(s_list[i])) for c in rp])
        per = [0.0]
        for k in range(len(rp)):
            per.append(per[-1] + (rp[(k + 1) % len(rp)] - rp[k]).length)
        uvs.append([(u, s_list[i]) for u in per])
    md.grid(rows, "fabric_hivis", True, uvs)
    # rolled hem lip: outer rim -> inner lining going back up the sleeve (normals face the arm)
    t_, nn, bb = fr[-1]
    c_end = pts[-1]
    rim = [md.v(c_end + (c - c_end) * 1.035 + t_ * 0.003, w_at(total)) for c in [md.verts[i] for i in rows[-1]]]
    inner1 = [md.v(c_end + (c - c_end) * 0.90 + t_ * 0.004, w_at(total)) for c in [md.verts[i] for i in rows[-1]]]
    inner2 = [md.v(c_end + (c - c_end) * 0.88 - t_ * 0.030, w_at(total - 0.03)) for c in [md.verts[i] for i in rows[-1]]]
    md.grid([rows[-1], rim, inner1, inner2], "fabric_hivis", True)
    # reflective bands (custom_reflective), following the folds 1.4 mm proud of the cloth
    bands = [(total - 0.120, total - 0.072), (s_elbow * 0.45, s_elbow * 0.45 + 0.05)]
    for b0, b1 in bands:
        idx = [i for i in range(len(pts)) if b0 <= s_list[i] <= b1]
        if len(idx) < 2:
            continue
        brows = []
        for i in idx:
            rp = ring_pts(i, 0.0014)
            brows.append([md.v(c, w_at(s_list[i])) for c in rp])
        lip0 = [md.v(pts[idx[0]] + (md.verts[v] - pts[idx[0]]) * 0.975, w_at(s_list[idx[0]])) for v in brows[0]]
        lip1 = [md.v(pts[idx[-1]] + (md.verts[v] - pts[idx[-1]]) * 0.975, w_at(s_list[idx[-1]])) for v in brows[-1]]
        md.grid([lip0] + brows + [lip1], "custom_reflective", True)
    return md.to_object(f"sleeve_{side}", smooth=True)


sR, sL = sleeve("R"), sleeve("L")
print(f"[vm] meshes built {time.time() - T0:.1f}s")
print("[vm] joining arms")
parts = [gR, gL, padR, padL, strapR, strapL, watchL, sR, sL]
for o in parts:
    if not o.data.uv_layers:
        ck.box_uv(o)
arms = bk.join(parts, "vm_arms")
ck.limit_weights(arms, 4, smooth=1, smooth_fac=0.35)
ck.bake_ao([arms], samples=24, dist=0.035, strength=0.7, floor=0.42)
ck.skin(arms, rig)

# ====================================================================== tools on the right hand
for name, tool in TOOLS.items():
    o = tool.obj
    ck.bake_ao([o] + [s for s, _ in tool.subs], samples=20, dist=0.025, strength=0.65, floor=0.45)
    for sub, piv in tool.subs:
        sub.data.transform(ck.T(-piv))
        sub.location = piv
        sub.parent = o
    for tip_name, p in tool.tips.items():
        e = bpy.data.objects.new(tip_name, None)
        e.empty_display_size = 0.02
        bpy.context.scene.collection.objects.link(e)
        e.location = p
        e.parent = o
    G, r, _ = tool.grips["R"]
    o.matrix_world = rig.rest["hand.R"] @ Hgrip("R", r) @ G.inverted()
    bpy.context.view_layer.update()
    ck.parent_to_bone(o, rig, "hand.R")

# ====================================================================== clips
warn = []
for name, dur, step, fn, _tool in CLIPS:
    n = int(round(dur * FPS))
    frames = sorted(set(list(range(0, n + 1, step)) + [n]))
    cw = ck.ClipWriter(rig, name)
    for f in frames:
        P, ok = solve(fn(f / FPS))
        if not ok:
            warn.append((name, f))
        cw.add(f, rig.basis(P))
    cw.finish()
    print(f"[vm] clip {name}: {dur:.3f}s, {len(frames)} keys")
if warn:
    print(f"[vm] WARNING unreachable IK targets: {warn[:12]}{'...' if len(warn) > 12 else ''} ({len(warn)})")
ck.rest_pose(rig)
print(f"[vm] clips done {time.time() - T0:.1f}s")

# ====================================================================== export
meshes = [arms] + [t.obj for t in TOOLS.values()] + [s for t in TOOLS.values() for s, _ in t.subs]
empties = [o for o in bpy.context.scene.objects if o.type == "EMPTY"]
print("[vm] tris:", {o.name: bk.tris([o]) for o in meshes}, "total", bk.tris(meshes))
ck.export_glb(OUT, [arm] + meshes + empties)
bk.save(os.path.join(HERE, "viewmodel.blend"))

# ====================================================================== previews
if MODE == "none":
    sys.exit(0)

ck.eevee((1280, 720), samples=40)
ck.world("#07080b", 1.0)
cam = ck.camera("fp_cam", (0, 0, 0), fov_v=60, rot=(90, 0, 0), clip=(0.005, 50))
ck.light("headlamp", "SPOT", 22, (0.05, -0.04, 0.09), target=(0.04, 2.0, -0.25), spot=75, blend=0.5,
         color="#eef3ff", size=0.02)
ck.light("warm", "AREA", 45, (-1.0, 0.7, 0.55), target=(0.12, 0.5, -0.12), size=0.8, color="#ffb067")
ck.light("rim", "AREA", 26, (1.0, 1.3, 0.7), target=(0.1, 0.45, -0.1), size=0.6, color="#ffd09a")
ck.light("fill", "AREA", 8, (0.3, -0.6, -0.4), target=(0.15, 0.4, -0.15), size=1.0, color="#9fb6ff")
wall = bpy.data.objects.new("wall", bpy.data.meshes.new("wall"))
bpy.context.scene.collection.objects.link(wall)
wall.data.from_pydata([(-3, 0.87, -2), (3, 0.87, -2), (3, 0.87, 2), (-3, 0.87, 2)], [], [(0, 1, 2, 3)])
wm = bpy.data.materials.new("prev_rock")
wm.use_nodes = True
nt = wm.node_tree
bsdf = nt.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (0.055, 0.047, 0.040, 1)
bsdf.inputs["Roughness"].default_value = 0.85
nz = nt.nodes.new("ShaderNodeTexNoise")
nz.inputs["Scale"].default_value = 9.0
nz.inputs["Detail"].default_value = 8.0
bump = nt.nodes.new("ShaderNodeBump")
bump.inputs["Strength"].default_value = 0.6
nt.links.new(nz.outputs["Fac"], bump.inputs["Height"])
nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
wall.data.materials.append(wm)


def show_tool(name):
    for t in TOOLS.values():
        vis = t.name == name
        t.obj.hide_render = not vis
        for s, _ in t.subs:
            s.hide_render = not vis


def crosshair():
    pass


def shot(clip, frame_no, tool, tag=None):
    show_tool(tool)
    ck.play(rig, clip, frame_no)
    ck.render(os.path.join(PREV, f"vm_{tag or clip}_{frame_no:03d}.png"))


if MODE in ("full", "quick"):
    sw = [0, 6, 14, 18, 20, 22, 24, 26, 27, 29, 36, 46] if MODE == "full" else [0, 18, 24, 27, 30]
    for f in sw:
        shot("pick_swing", f, "vm_pickaxe")
    shot("pick_equip", 0, "vm_pickaxe")
    shot("pick_equip", 14, "vm_pickaxe")
    shot("pick_idle", 0, "vm_steelpick", "steelpick_idle")
    for f in (0, 10, 20, 30):
        shot("hammer_use", f, "vm_jackhammer")
    shot("hammer_idle", 0, "vm_jackhammer")
    shot("drill_idle", 0, "vm_diamonddrill")
    shot("drill_use", 13, "vm_diamonddrill")
    shot("hands_idle", 0, None)
    shot("hands_reach", 20, None)
    shot("hands_reach", 26, None)
print("[vm] done")
