"""Town props: water_tower, windmill (child rotor), telegraph_pole, wagon, bench, street_lamp (child bulb),
boardwalk_4m, barrels, hitching_post. Fronts face -Y (three +Z), origins at the ground centre."""
import math

import bpy
from mathutils import Matrix, Vector

import arch
from arch import B
import tk
from tk import T


def water_tower(seed=91):
    """Railroad water tank: banded timber staves, conical shingle roof, timber trestle with X-bracing,
    swinging spout, ladder."""
    b = B("water_tower", seed)
    mb = b.mb
    zt = 6.4          # tank floor
    R, H = 2.6, 3.7
    legs = [(sx * 1.9, sy * 1.9) for sx in (-1, 1) for sy in (-1, 1)]
    for (x, y) in legs:
        mb.boxc((0.7, 0.7, 0.35), "concrete", loc=(x * 1.12, y * 1.12, 0.175), bev=0.02, skip="d")
        mb.span((x * 1.12, y * 1.12, 0.3), (x, y, zt - 0.3), 0.3, 0.3, "wood_timber", up=(0, 0, 1), bev=0.02)
    for z in (2.2, 4.4):
        f = 1 - (z - 0.3) / (zt - 0.6) * 0.106
        for (a, c) in ((0, 1), (1, 3), (3, 2), (2, 0)):
            (x0, y0), (x1, y1) = legs[a], legs[c]
            k0 = 1.12 - 0.12 * (z - 0.3) / (zt - 0.6)
            mb.span((x0 * k0, y0 * k0, z), (x1 * k0, y1 * k0, z), 0.16, 0.22, "wood_timber", up=(0, 0, 1))
    for (a, c) in ((0, 1), (1, 3), (3, 2), (2, 0)):
        (x0, y0), (x1, y1) = legs[a], legs[c]
        for (za, zb) in ((0.4, 2.2), (2.2, 4.4), (4.4, zt - 0.4)):
            ka = 1.12 - 0.12 * (za - 0.3) / (zt - 0.6)
            kb = 1.12 - 0.12 * (zb - 0.3) / (zt - 0.6)
            mb.span((x0 * ka, y0 * ka, za), (x1 * kb, y1 * kb, zb), 0.1, 0.14, "wood_timber", up=(0, 0, 1))
            mb.span((x1 * ka, y1 * ka, za), (x0 * kb, y0 * kb, zb), 0.1, 0.14, "wood_timber", up=(0, 0, 1))
    # tank floor beams + deck
    for k in range(5):
        x = -2.0 + k
        mb.boxc((0.2, 5.0, 0.3), "wood_timber", loc=(x, 0, zt - 0.15), bev=0.01)
    mb.cyl(R + 0.25, 0.08, "wood_planks", loc=(0, 0, zt), sides=20, uvoff=True)
    # staves + hoops
    mb.lathe([(R, zt + 0.08), (R + 0.02, zt + H * 0.5), (R, zt + H)], "wood_planks", sides=28, cap_bot=False, cap_top=False,
             tone=0.9)
    for k in range(7):
        z = zt + 0.35 + k * (H - 0.5) / 6
        mb.lathe([(R + 0.03, z - 0.025), (R + 0.03, z + 0.025)], "steel_dark", sides=28, cap_top=False, cap_bot=False)
    for k in range(4):
        a = k * math.pi / 2 + 0.4
        mb.boxc((0.06, 0.06, H - 0.3), "steel_dark", loc=(math.cos(a) * (R + 0.05), math.sin(a) * (R + 0.05), zt + H / 2))
    # roof
    mb.cyl(R + 0.35, 1.25, "roof_shingle", loc=(0, 0, zt + H), r2=0.08, sides=24, cap_bot=True)
    mb.cyl(R + 0.36, 0.1, "wood_painted_white", loc=(0, 0, zt + H - 0.02), sides=24, cap_top=False)
    mb.cyl(0.06, 0.6, "steel_dark", loc=(0, 0, zt + H + 1.2), sides=6, r2=0.02)
    # spout (hinged pipe + counterweight chain)
    sx, sy = 0.0, -(R + 0.05)
    mb.cyl(0.28, 0.4, "steel_dark", loc=(sx, sy - 0.1, zt + 0.6), rot=(90, 0, 0), centre=True, sides=12)
    mb.tube([(sx, sy - 0.3, zt + 0.6), (sx, sy - 1.6, zt + 0.1), (sx, sy - 2.4, zt - 0.9)], 0.22, "steel_dark", sides=10, cap=True)
    mb.tube([(sx, sy - 2.4, zt - 0.9), (sx, sy - 2.5, zt - 1.6)], 0.16, "canvas", sides=8, cap=True)
    mb.tube([(sx, sy - 1.6, zt + 0.15), (sx + 0.3, sy - 1.0, zt + 2.6), (sx + 0.3, sy - 0.2, zt + H - 0.2)], 0.012, "steel_dark", sides=4)
    mb.cyl(0.12, 0.5, "cast_iron", loc=(sx + 0.3, sy - 0.75, zt + 1.6), sides=8)
    # ladder on one leg + tank side
    lx, ly = 1.95, -1.95
    for k in range(20):
        z = 0.5 + k * 0.32
        if z > zt + H - 0.2:
            break
        r_ = 2.25 if z < zt else R + 0.25
        mb.boxc((0.45, 0.03, 0.03), "steel_dark", loc=(lx * 0.95 if z < zt else 0.0, ly * 0.95 if z < zt else -r_, z),
                rot=(0, 0, -45 if z < zt else 0))
    # level float board
    mb.boxc((0.25, 0.04, H - 0.4), "wood_painted_white", loc=(R * 0.71 + 0.06, -R * 0.71 - 0.06, zt + H / 2), rot=(0, 0, -45))
    return b.finish()


def windmill(seed=92):
    """Steel-lattice farm windmill: 4-post tapered tower, platform, gearbox head, 18-blade wheel (child
    `rotor`, spins about its local Z in three.js = the wind axis, facing +Z), tail vane, stock tank."""
    b = B("windmill", seed)
    mb = b.mb
    Ht = 9.0
    base, top = 1.5, 0.35
    corners = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
    for (sx, sy) in corners:
        mb.span((sx * base, sy * base, 0.0), (sx * top, sy * top, Ht), 0.07, 0.07, "galvanized", up=(0, 0, 1))
        mb.boxc((0.4, 0.4, 0.3), "concrete", loc=(sx * base, sy * base, 0.15), skip="d")
    n = 6
    for k in range(1, n + 1):
        z = Ht * k / n
        za = Ht * (k - 1) / n
        s0 = base + (top - base) * za / Ht
        s1 = base + (top - base) * z / Ht
        for i in range(4):
            (ax, ay), (bx, by) = corners[i], corners[(i + 1) % 4]
            mb.span((ax * s1, ay * s1, z), (bx * s1, by * s1, z), 0.05, 0.05, "galvanized")
            mb.span((ax * s0, ay * s0, za), (bx * s1, by * s1, z), 0.025, 0.025, "galvanized")
            mb.span((bx * s0, by * s0, za), (ax * s1, ay * s1, z), 0.025, 0.025, "galvanized")
    # platform + head
    mb.boxc((1.4, 1.4, 0.05), "wood_planks", loc=(0, 0, Ht - 0.6))
    mb.cyl(0.12, 0.6, "galvanized", loc=(0, 0, Ht), sides=10)
    mb.boxc((0.45, 0.8, 0.5), "paint_red", loc=(0, 0.05, Ht + 0.6), bev=0.03)
    mb.cyl(0.24, 0.5, "galvanized", loc=(0, 0.05, Ht + 1.1), r2=0.08, sides=10)
    mb.cyl(0.06, 0.55, "steel", loc=(0, -0.35, Ht + 0.85), rot=(90, 0, 0), centre=True, sides=8)
    # tail vane
    mb.span((0, 0.4, Ht + 0.85), (0, 3.2, Ht + 0.95), 0.06, 0.06, "galvanized")
    mb.span((0, 0.4, Ht + 0.55), (0, 2.4, Ht + 0.95), 0.03, 0.03, "galvanized")
    mb.poly([(0, 2.2, Ht + 0.3), (0, 3.6, Ht + 0.45), (0, 3.6, Ht + 1.55), (0, 2.2, Ht + 1.35)], "galvanized", thick=0.012,
            facing=(1, 0, 0))
    # pump rod + stock tank
    mb.cyl(0.02, Ht - 0.3, "steel", loc=(0, 0, 0.3), sides=4)
    mb.lathe([(1.5, 0.0), (1.5, 0.65), (1.55, 0.7)], "galvanized", loc=(2.4, -1.6, 0), sides=24, cap_bot=False, cap_top=False)
    mb.lathe([(1.45, 0.65), (1.45, 0.05)], "galvanized", loc=(2.4, -1.6, 0), sides=24, cap_bot=False, cap_top=False)
    mb.cyl(1.46, 0.02, "glass_dark", loc=(2.4, -1.6, 0.55), sides=24)
    mb.tube([(0.1, 0.0, 0.5), (0.9, -0.6, 0.4), (1.5, -1.2, 0.75), (1.7, -1.3, 0.75)], 0.04, "steel_dark", sides=6)
    root = b.finish()
    # rotor (wheel): hub at origin, blades in the XZ plane, faces -Y (front)
    r = tk.MB("rotor")
    R0, R1 = 0.55, 1.85
    for ring in (R0, R1, (R0 + R1) / 2):
        r.ring(ring - 0.02, ring + 0.02, 0.03, "galvanized", rot=(90, 0, 0), loc=(0, 0.02, 0), sides=24)
    for k in range(18):
        a = k * math.tau / 18
        c, s = math.cos(a), math.sin(a)
        da = 0.14
        pts = []
        for rr in (R0, R1):
            for side in (-1, 1):
                aa = a + side * da * (0.35 if rr == R0 else 1.0) * (R0 / rr if rr == R0 else 0.13 / 0.14)
                pts.append((math.cos(aa) * rr, -0.06 * side, math.sin(aa) * rr))
        q = [pts[0], pts[2], pts[3], pts[1]]
        r.poly(q, "galvanized", thick=0.006)
        r.span((c * 0.12, 0.0, s * 0.12), (c * R1, 0.0, s * R1), 0.02, 0.02, "galvanized")
    r.cyl(0.14, 0.18, "paint_red", rot=(90, 0, 0), centre=True, sides=12, bev=0.01)
    ro = r.finish(parent=root)
    ro.location = (0, -0.68, Ht + 0.85)
    return root


def telegraph_pole(seed=93):
    """8.6 m cedar pole, two crossarms with braces, green glass insulators, short wire stubs (along X),
    step pegs and a small pole transformer (the town runs modern machines)."""
    b = B("telegraph_pole", seed)
    mb = b.mb
    H = 8.6
    mb.cyl(0.14, H, "wood_timber", r2=0.105, sides=10, uvoff=True)
    mb.cyl(0.11, 0.08, "wood_timber", loc=(0, 0, H), r2=0.06, sides=10)
    ins = tk.custom_mat("custom_insulator", "#4f9a84", rough=0.12, metal=0.0, vc=False)
    for k, (z, L, n) in enumerate(((H - 0.35, 2.4, 6), (H - 1.15, 1.8, 4))):
        mb.boxc((L, 0.1, 0.12), "wood_timber", loc=(0, 0.13, z), bev=0.01, uvoff=True)
        for sx in (-1, 1):
            mb.span((0, 0.12, z - 0.65), (sx * 0.55, 0.12, z - 0.05), 0.04, 0.012, "steel_dark")
        for i in range(n):
            x = -L / 2 + 0.12 + i * (L - 0.24) / (n - 1)
            if abs(x) < 0.2:
                continue
            mb.cyl(0.012, 0.12, "wood_dark", loc=(x, 0.13, z + 0.06), sides=5)
            mb.lathe([(0.045, 0.0), (0.05, 0.04), (0.04, 0.08), (0.032, 0.11), (0.0, 0.12)], ins.name, loc=(x, 0.13, z + 0.16),
                     sides=10, cap_bot=True)
            # wire stub both ways along X
            mb.tube([(x - 0.9, 0.13, z + 0.18 - 0.03), (x, 0.13, z + 0.235), (x + 0.9, 0.13, z + 0.18 - 0.03)], 0.005, "cable", sides=4)
    for k in range(10):
        z = 2.3 + k * 0.42
        a = (k % 2) * math.pi
        mb.cyl(0.012, 0.22, "steel_dark", loc=(math.cos(a) * 0.12, math.sin(a) * 0.12, z), rot=(0, 90, 0 if k % 2 else 180),
               sides=5)
    mb.cyl(0.24, 0.62, "galvanized", loc=(0.0, -0.42, H - 2.4), sides=14, bev=0.01)
    mb.boxc((0.1, 0.3, 0.3), "steel_dark", loc=(0, -0.2, H - 2.1))
    mb.tube([(0.0, -0.42, H - 1.75), (0.1, -0.2, H - 1.4), (0.5, 0.13, H - 1.0)], 0.008, "cable", sides=4)
    return b.finish()


def wagon(seed=94):
    """Freight wagon loaded with ore: green box, red running gear, wooden spoked wheels with iron tyres,
    spring seat, brake, tongue with doubletree. Tongue points -Y (front)."""
    b = B("wagon", seed)
    mb = b.mb
    zb = 1.05
    L, Wd = 3.6, 1.05
    mb.boxc((Wd, L, 0.06), "wood_planks", loc=(0, 0.2, zb), uvoff=True)
    for sx in (-1, 1):
        mb.boxc((0.05, L, 0.62), "wood_painted_green", loc=(sx * Wd / 2, 0.2, zb + 0.31), bev=0.008)
        for k in range(5):
            mb.boxc((0.07, 0.05, 0.64), "wood_painted_green", loc=(sx * (Wd / 2 + 0.03), -1.4 + k * 0.8, zb + 0.32))
        mb.boxc((0.08, L + 0.02, 0.05), "steel_dark", loc=(sx * (Wd / 2 + 0.02), 0.2, zb + 0.6))
    for sy in (-1, 1):
        mb.boxc((Wd, 0.05, 0.62), "wood_painted_green", loc=(0, 0.2 + sy * L / 2, zb + 0.31), bev=0.008)
    # ore load
    for k, (x, y, r) in enumerate(((0.0, -0.6, 0.55), (0.1, 0.5, 0.6), (-0.15, 1.3, 0.5), (0.2, -1.2, 0.45))):
        mb.lathe([(r, 0.0), (r * 0.8, 0.25), (r * 0.4, 0.4), (0.0, 0.45)], "rock", loc=(x, y, zb + 0.35), sides=9, cap_bot=False,
                 smooth_=False)
    # running gear
    for (y, r) in ((-1.25, 0.52), (1.45, 0.66)):
        mb.boxc((1.55, 0.14, 0.14), "wood_painted_red", loc=(0, y, r), bev=0.01)
        mb.boxc((1.2, 0.14, 0.18), "wood_painted_red", loc=(0, y, zb - 0.12), bev=0.01)
        for sx in (-1, 1):
            with mb.at(M=T((sx * 0.8, y, r)) @ Matrix.Rotation(math.radians(90), 4, "Y")):
                mb.ring(r - 0.05, r, 0.07, "steel_dark", loc=(0, 0, -0.035), sides=18)
                mb.ring(r - 0.1, r - 0.05, 0.08, "wood_painted_red", loc=(0, 0, -0.04), sides=18)
                mb.cyl(0.11, 0.24, "wood_painted_red", loc=(0, 0, -0.12), r2=0.08, sides=10)
            for k in range(12):
                a = k * math.tau / 12
                mb.span((sx * 0.8, y + math.cos(a) * 0.09, r + math.sin(a) * 0.09), (sx * 0.8, y + math.cos(a) * (r - 0.08), r + math.sin(a) * (r - 0.08)),
                        0.035, 0.05, "wood_painted_red", up=(1, 0, 0))
    mb.span((0, -1.25, 0.6), (0, 1.45, 0.72), 0.08, 0.08, "wood_painted_red")
    mb.span((0, -1.3, 0.55), (0, -3.9, 0.75), 0.08, 0.1, "wood_timber")
    mb.span((-0.55, -3.0, 0.6), (0.55, -3.0, 0.6), 0.08, 0.06, "wood_timber")
    # seat + brake
    mb.boxc((1.0, 0.4, 0.06), "wood_dark", loc=(0, -1.15, zb + 0.95), bev=0.01)
    mb.boxc((1.0, 0.05, 0.3), "wood_dark", loc=(0, -0.95, zb + 1.13), bev=0.01)
    for sx in (-0.4, 0.4):
        mb.span((sx, -1.15, zb + 0.6), (sx, -1.15, zb + 0.95), 0.04, 0.03, "steel_dark")
    mb.span((0.62, -0.7, zb - 0.1), (0.66, -0.9, zb + 1.1), 0.04, 0.04, "steel_dark")
    mb.boxc((0.1, 0.25, 0.12), "wood_dark", loc=(0.62, 1.0, 1.2))
    return b.finish()


def bench(seed=95):
    b = B("bench", seed)
    arch.bench(b.mb, 0, 0, 0, L=1.9)
    return b.finish()


def street_lamp(seed=96):
    """Cast-iron street lamp (3.9 m), fluted base, square lantern; child `bulb` (emit_warm)."""
    b = B("street_lamp", seed)
    mb = b.mb
    mb.cyl(0.2, 0.12, "cast_iron", sides=12, bev=0.01)
    mb.lathe([(0.17, 0.12), (0.15, 0.3), (0.1, 0.45), (0.075, 0.55), (0.085, 0.62), (0.06, 0.7)], "cast_iron", sides=12, cap_bot=False,
             cap_top=False)
    mb.cyl(0.055, 2.75, "cast_iron", loc=(0, 0, 0.7), r2=0.045, sides=10)
    for z in (1.4, 3.35):
        mb.cyl(0.07, 0.06, "cast_iron", loc=(0, 0, z), sides=10, bev=0.01)
    mb.span((-0.32, 0, 3.15), (0.32, 0, 3.15), 0.025, 0.025, "cast_iron")
    zl = 3.45
    w, h = 0.3, 0.42
    mb.cyl(0.08, 0.1, "cast_iron", loc=(0, 0, zl - 0.06), r2=0.12, sides=10)
    mb.boxc((w + 0.05, w + 0.05, 0.04), "cast_iron", loc=(0, 0, zl + 0.02), bev=0.005)
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.boxc((0.025, 0.025, h), "cast_iron", loc=(sx * w / 2, sy * w / 2, zl + 0.04 + h / 2))
    for k in range(4):
        a = k * 90
        nx, ny = math.cos(math.radians(a)), math.sin(math.radians(a))
        p = [(nx * w / 2 - ny * w / 2, ny * w / 2 + nx * w / 2), (nx * w / 2 + ny * w / 2, ny * w / 2 - nx * w / 2)]
        mb.poly([(p[0][0], p[0][1], zl + 0.04), (p[1][0], p[1][1], zl + 0.04), (p[1][0], p[1][1], zl + 0.04 + h),
                 (p[0][0], p[0][1], zl + 0.04 + h)], "glass", facing=(nx, ny, 0))
    mb.cyl(w * 0.9, 0.2, "cast_iron", loc=(0, 0, zl + 0.04 + h), r2=0.03, sides=4, rot=(0, 0, 45))
    mb.cyl(0.03, 0.12, "cast_iron", loc=(0, 0, zl + 0.26 + h), sides=6)
    root = b.finish()
    bulb = tk.MB("bulb")
    bulb.cyl(0.06, 0.16, "emit_warm", sides=10)
    bulb.lathe([(0.0, 0.16), (0.06, 0.16), (0.07, 0.22), (0.0, 0.3)], "emit_warm", sides=10, cap_bot=False)
    bo = bulb.finish(parent=root)
    tk.strip_colors(bo)
    bo.location = (0, 0, zl + 0.1)
    return root


def boardwalk_4m(seed=97):
    """4 m boardwalk section along X matching the shop porches: deck top 0.5 m, deck from y=-0.9 to +1.5
    (back edge = building line), two full-width steps down to y = -1.5 (street side, front)."""
    b = B("boardwalk_4m", seed)
    mb = b.mb
    x0, x1 = -2.0, 2.0
    z = 0.5
    arch.deck(mb, x0, x1, -0.9, 1.5, z)
    mb.boxc((4.0, 0.05, 0.22), arch.DECK, loc=(0, -0.925, z - 0.155), skip="k", uvoff=True)
    mb.boxc((4.0, 0.03, z - 0.27), arch.DECK, loc=(0, -0.885, (z - 0.27) / 2), skip="k", grain=2, tone=0.8)
    for k in range(2):
        zt = z * (k + 1) / 3
        yy = -0.9 - 0.3 * (2 - k)
        arch.treads(mb, -2.0, 2.0, yy, yy + 0.32, zt)
        mb.boxc((4.0, 0.03, zt - 0.045), arch.DECK, loc=(0, yy + 0.04, (zt - 0.045) / 2), skip="k", uvoff=True, tone=0.85)
    for x in (-1.6, 0.0, 1.6):
        mb.boxc((0.1, 2.3, 0.18), "wood_timber", loc=(x, 0.3, z - 0.045 - 0.09), skip="")
    return b.finish()


def barrels(seed=98):
    b = B("barrels", seed)
    mb = b.mb
    arch.barrel(mb, -0.35, 0.0, 0.0, tone=0.95)
    arch.barrel(mb, 0.3, 0.12, 0.0, tone=0.85, rot=40)
    arch.barrel(mb, -0.05, 0.62, 0.0, tone=0.9, rot=15)
    arch.barrel(mb, 0.15, -0.75, 0.0, lying=True, rot=10, tone=0.88)
    mb.cyl(0.24, 0.03, "wood_dark", loc=(0.3, 0.12, 0.86), sides=12)
    return b.finish()


def hitching_post(seed=99):
    b = B("hitching_post", seed)
    mb = b.mb
    # hewn posts (chamfered, weathered caps cut to shed rain), a hewn rail let into the post tops with a bolt
    # head each end, two iron tie rings on staples, and the rail worn pale where the reins rub
    for x in (-1.2, 1.2):
        mb.boxc((0.17, 0.17, 1.12), "wood_timber", loc=(x, 0, 0.56), bev=0.025, skip="d", uvoff=True, tone=mb.tone(0.8, 0.95))
        mb.poly([(x - 0.085, -0.085, 1.12), (x + 0.085, -0.085, 1.12), (x + 0.085, -0.085, 1.16), (x - 0.085, -0.085, 1.2)],
                "wood_timber", thick=0.17, facing=(0, -1, 0), tone=0.75)
        mb.boxc((0.2, 0.2, 0.04), "rock", loc=(x, 0, -0.01), tone=0.7)
        mb.cyl(0.018, 0.012, "steel_dark", loc=(x, -0.087, 1.02), rot=(90, 0, 0), sides=6, centre=True)
    mb.boxc((2.7, 0.11, 0.12), "wood_timber", loc=(0, 0, 0.96), bev=0.02, uvoff=True, tone=0.92, grain=0)
    mb.boxc((1.4, 0.112, 0.012), "wood_timber", loc=(0, 0, 1.025), tone=1.0, grain=0)
    for x in (-0.6, 0.6):
        mb.boxc((0.05, 0.03, 0.02), "steel_dark", loc=(x, -0.06, 0.95))
        mb.ring(0.035, 0.047, 0.012, "steel_dark", loc=(x, -0.066, 0.9), rot=(90, 0, 0), sides=10)
    return b.finish()


NODES = {"water_tower": water_tower, "windmill": windmill, "telegraph_pole": telegraph_pole, "wagon": wagon, "bench": bench,
         "street_lamp": street_lamp, "boardwalk_4m": boardwalk_4m, "barrels": barrels, "hitching_post": hitching_post}
