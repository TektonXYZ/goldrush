"""depot: railway station + long timber platform + canopy. The track runs along X behind the platform.

Blender coords (three.js: x same, z = -y): street side faces -Y (three +Z), track side +Y (three -Z).
Platform edge at y = +3.5 (three z = -3.5); rail centreline should sit at y = +5.15 (three z = -5.15).
"""
import math

import arch
from arch import B, Op, WF, Rz
import tk

PLATFORM_EDGE_Y = 3.5
TRACK_Y = 5.15
PLAT_Z = 0.65
SMALL = {k: (0.0, 1 - (i + 1) / 4, 1.0, 1 - i / 4) for i, k in enumerate(("tickets", "waiting", "baggage", "elev"))}


def lamp_post(mb, x, y, z, h=3.6):
    mb.cyl(0.13, 0.35, "cast_iron", loc=(x, y, z), r2=0.09, sides=10)
    mb.cyl(0.055, h - 0.35, "cast_iron", loc=(x, y, z + 0.35), r2=0.045, sides=8)
    mb.cyl(0.09, 0.06, "cast_iron", loc=(x, y, z + h - 0.05), sides=8)
    mb.span((x - 0.3, y, z + h - 0.3), (x + 0.3, y, z + h - 0.3), 0.03, 0.03, "cast_iron")
    arch.lantern(mb, x, y, z + h, s=1.25)


def luggage_cart(mb, x, y, z, rot=0.0):
    with mb.at((x, y, z), (0, 0, rot)):
        L, W = 2.3, 0.95
        r = 0.24
        for sx in (-L / 2 + 0.35, L / 2 - 0.35):
            for sy in (-W / 2 - 0.03, W / 2 + 0.03):
                with mb.at((sx, sy, r), (90, 0, 0)):
                    mb.ring(r - 0.03, r, 0.05, "cast_iron", loc=(0, 0, -0.025), sides=10)
                    for k in range(4):
                        a = k * math.pi / 4
                        mb.span((-math.cos(a) * (r - 0.02), -math.sin(a) * (r - 0.02), 0),
                                (math.cos(a) * (r - 0.02), math.sin(a) * (r - 0.02), 0), 0.02, 0.02, "cast_iron")
                    mb.cyl(0.05, 0.08, "cast_iron", loc=(0, 0, -0.04), sides=8)
            mb.cyl(0.025, W + 0.1, "steel_dark", loc=(sx, 0, r), rot=(90, 0, 0), sides=6, centre=True)
        mb.boxc((L, W, 0.06), "wood_planks", loc=(0, 0, r + 0.12), bev=0.008, uvoff=True)
        for sy in (-W / 2 + 0.04, W / 2 - 0.04):
            mb.boxc((L, 0.07, 0.12), "wood_dark", loc=(0, sy, r + 0.06))
        mb.span((L / 2, -0.3, r + 0.16), (L / 2 + 0.9, -0.1, 0.95), 0.04, 0.04, "steel_dark")
        mb.span((L / 2, 0.3, r + 0.16), (L / 2 + 0.9, 0.1, 0.95), 0.04, 0.04, "steel_dark")
        mb.cyl(0.03, 0.4, "wood_dark", loc=(L / 2 + 0.9, 0, 0.95), rot=(90, 0, 0), centre=True, sides=6)
        # load: two trunks + a crate
        top = r + 0.15
        mb.boxc((0.9, 0.55, 0.5), "leather", loc=(-0.55, -0.1, top + 0.25), rot=(0, 0, 4), bev=0.02)
        for dx in (-0.95, -0.15):
            mb.boxc((0.06, 0.58, 0.53), "brass", loc=(dx, -0.1, top + 0.25), rot=(0, 0, 4))
        mb.boxc((0.75, 0.45, 0.42), "wood_dark", loc=(-0.45, 0.05, top + 0.71), rot=(0, 0, -6), bev=0.02)
        arch.crate(mb, 0.55, 0.05, top, s=(0.6, 0.6, 0.5), rot=12)


def depot(seed=21):
    """Board-and-batten station with deep bracketed eaves, agent's bay, ticket window, baggage room,
    name boards, a 44 m platform with a canopy, lamps, benches, luggage cart and freight."""
    b = B("depot", seed)
    mb = b.mb
    red, white = "wood_painted_red", "wood_painted_white"
    x0, x1 = -8.0, 8.0
    yf, yb = -4.6, 0.6
    fz = PLAT_Z
    z_eave = 4.2
    pitch = 32
    W, D = x1 - x0, yb - yf
    mb.boxc((W, D, fz + 0.12), "concrete", loc=(0, (yf + yb) / 2, (fz - 0.12) / 2), skip="ud", tone=0.5)
    arch.foundation(b, x0, x1, yf, yb, fz, sides="flr")
    # ---------------- platform
    PX = 22.0
    yE = PLATFORM_EDGE_Y
    for (a, c, y0) in ((-PX, x0, -0.2), (x0, x1, yb), (x1, PX, -0.2)):
        arch.deck(mb, a, c, y0, yE - 0.04, fz, along="x", bw=0.16)
    mb.boxc((2 * PX, 0.22, 0.28), "wood_timber", loc=(0, yE - 0.11, fz - 0.045 - 0.14), uvoff=True)
    mb.boxc((2 * PX, 0.05, fz - 0.32), "wood_timber", loc=(0, yE - 0.08, (fz - 0.32) / 2), skip="k", grain=2)
    mb.boxc((2 * PX, 0.09, 0.006), "paint_yellow", loc=(0, yE - 0.42, fz + 0.001), tone=0.85)
    for (a, c) in ((-PX, x0), (x1, PX)):
        mb.boxc((c - a, 0.05, fz - 0.05), "wood_timber", loc=((a + c) / 2, -0.2 + 0.02, (fz - 0.05) / 2), skip="k", grain=2)
    # ramps at both ends
    for sgn in (-1, 1):
        xa, xb = sgn * PX, sgn * (PX + 3.2)
        mb.poly([(xa, -0.2, fz), (xa, yE, fz), (xb, yE, 0.02), (xb, -0.2, 0.02)], "wood_planks", thick=0.06,
                facing=(sgn * 0.2, 0, 1), grain_dir=(0, 1, 0))
        for yy in (-0.2, yE):
            mb.poly([(xa, yy, fz - 0.06), (xa, yy, 0.0), (xb, yy, 0.0)], "wood_timber",
                    facing=(0, -1 if yy < 0 else 1, 0))
        mb.poly([(xa, -0.2, 0.0), (xa, yE, 0.0), (xa, yE, fz - 0.06), (xa, -0.2, fz - 0.06)], "wood_timber",
                facing=(-sgn, 0, 0))
    # street-side steps off the wings
    for xc in (-11.5, 11.5):
        for k in range(3):
            zt = fz * (k + 1) / 4
            yy = -0.2 - 0.3 * (3 - k)
            arch.treads(mb, xc - 1.3, xc + 1.3, yy, yy + 0.32, zt, t=0.05)
            mb.boxc((2.6, 0.03, zt - 0.05), arch.DECK, loc=(xc, yy + 0.04, (zt - 0.05) / 2), skip="k", tone=0.85)
    # ---------------- walls
    street_ops = [Op(2.0, 2.9, 1.95, 3.15), Op(6.2, 7.1, 1.45, 3.3), Op(9.6, 10.5, 1.45, 3.3), Op(11.0, 12.2, fz, 3.6),
                  Op(13.6, 14.5, 1.45, 3.3)]
    with b.at(WF(x0, yf, 0, 0)):
        face = arch.wall(mb, W, fz, z_eave, street_ops, "bnb", red)
        arch.corner_boards(mb, W, fz, z_eave, face, white, cw=0.15)
        arch.water_table(mb, W, fz, face, white, h=0.22)
        for o in (street_ops[0], street_ops[1], street_ops[2], street_ops[4]):
            arch.window(b, o.u0, o.u1, o.v0, o.v1, face=face, trim=white, panes=(2, 1), cell=[6, 0, 5, 5][street_ops.index(o) if street_ops.index(o) < 3 else 3],
                        head="cap", shade=0.25 if o.u0 > 9 else 0.0)
        arch.door(b, 11.0, 12.2, fz, 3.1, face=face, trim=white, leaf=red, leaves=1, glazed=True, cell=5, transom=0.5,
                  vest_d=1.6, counter=False)
        arch.sign_board(b, 8.35, face, 3.86, 4.4, 0.55, "label_station", frame=white, body=white)
    track_ops = [Op(1.5, 2.4, 1.45, 3.3), Op(3.4, 4.6, fz, 3.6), Op(5.5, 6.3, 1.5, 2.6), Op(6.6, 9.4, fz, 3.45),
                 Op(12.4, 14.6, fz, 3.1)]
    with b.at(WF(x1, yb, 0, 180)):
        face_t = arch.wall(mb, W, fz, z_eave, track_ops, "bnb", red)
        arch.corner_boards(mb, W, fz, z_eave, face_t, white, cw=0.15)
        arch.water_table(mb, W, fz, face_t, white, h=0.22)
        arch.window(b, 1.5, 2.4, 1.45, 3.3, face=face_t, trim=white, panes=(2, 1), cell=5, head="cap")
        arch.door(b, 3.4, 4.6, fz, 3.1, face=face_t, trim=white, leaf=red, leaves=1, glazed=True, cell=5, transom=0.5,
                  vest_d=1.6, counter=False, open_deg=0)
        # ticket window: wide sill shelf + grille
        arch.window(b, 5.5, 6.3, 1.5, 2.6, face=face_t, trim=white, panes=(1, 1), cell=0, head="cap", sash_kind="fixed")
        mb.boxc((1.0, 0.32, 0.05), white, loc=(5.9, face_t - 0.16, 1.47), bev=0.008)
        for k in range(5):
            mb.boxc((0.012, 0.012, 1.0), "brass", loc=(5.58 + k * 0.16, face_t - 0.035, 2.05))
        b.lab.panel(1.0, 0.125, "label_depot_small", loc=(5.9, face_t - 0.035 - 0.15, 2.95), uv=SMALL["tickets"])
        mb.boxc((1.06, 0.03, 0.15), white, loc=(5.9, face_t - 0.015 - 0.15 + 0.005, 3.01), skip="k")
        b.lab.panel(1.2, 0.15, "label_depot_small", loc=(4.0, face_t - 0.035, 3.62 + 0.24), uv=SMALL["waiting"])
        # baggage room: sliding barn door on a rail, half open over a dim storeroom
        arch.interior_box(mb, 12.4, 14.6, fz, 3.1, 0.12, 1.6, 6, margin=0.1)
        for side in (12.4, 14.6):
            mb.poly([(side, face_t, fz), (side, 0.12, fz), (side, 0.12, 3.1), (side, face_t, 3.1)], white,
                    facing=(1 if side < 13 else -1, 0, 0))
        mb.poly([(12.4, face_t, 3.1), (14.6, face_t, 3.1), (14.6, 0.12, 3.1), (12.4, 0.12, 3.1)], white, facing=(0, 0, -1))
        dx = 11.55
        mb.boxc((2.3, 0.05, 2.5), red, loc=(dx, face_t - 0.08, fz + 1.3), skip="", tone=0.95)
        for zz in (fz + 0.12, fz + 1.3, fz + 2.46):
            mb.boxc((2.3, 0.03, 0.14), white, loc=(dx, face_t - 0.12, zz))
        for xx in (dx - 1.1, dx + 1.1):
            mb.boxc((0.14, 0.03, 2.5), white, loc=(xx, face_t - 0.12, fz + 1.3))
        mb.span((dx - 1.05, face_t - 0.13, fz + 0.2), (dx + 1.05, face_t - 0.13, fz + 1.25), 0.12, 0.03, white,
                up=(0, -1, 0))
        mb.span((dx - 1.05, face_t - 0.13, fz + 1.35), (dx + 1.05, face_t - 0.13, fz + 2.4), 0.12, 0.03, white,
                up=(0, -1, 0))
        mb.boxc((5.0, 0.06, 0.08), "steel_dark", loc=(13.0, face_t - 0.05, 3.25))
        for xx in (dx - 0.8, dx + 0.8):
            mb.cyl(0.05, 0.06, "steel_dark", loc=(xx, face_t - 0.12, 3.2), rot=(90, 0, 0), centre=True, sides=10)
        b.lab.panel(1.9, 0.24, "label_depot_small", loc=(13.5, face_t - 0.035, 3.3), uv=SMALL["baggage"])
        # name board hung from the eave rafters, facing the track (the deep eave hides the wall)
        hy = face_t - 1.68
        arch.sign_board(b, 8.0, hy, 2.8, 4.0, 0.5, "label_station", frame=white, body=white)
        for u in (6.3, 9.7):
            mb.span((u, hy + 0.03, 3.08), (u, hy + 0.03, 3.38), 0.02, 0.02, "cast_iron")
    for frame, ops in ((WF(x1, yf, 0, 90), [Op(2.15, 3.05, 1.45, 3.3)]), (WF(x0, yb, 0, -90), [Op(2.15, 3.05, 1.9, 3.1)])):
        with b.at(frame):
            f2 = arch.wall(mb, D, fz, z_eave, ops, "bnb", red)
            arch.corner_boards(mb, D, fz, z_eave, f2, white, cw=0.15)
            arch.water_table(mb, D, fz, f2, white, h=0.22)
            for o in ops:
                arch.window(b, o.u0, o.u1, o.v0, o.v1, face=f2, trim=white, cell=5 if o.v0 < 1.6 else 6, head="cap")
    # agent's bay (3 faces) on the track side
    bay = [((1.4, yb), (0.9, yb + 0.9)), ((0.9, yb + 0.9), (-0.9, yb + 0.9)), ((-0.9, yb + 0.9), (-1.4, yb))]
    for (ax, ay), (bx_, by_) in bay:
        ln = math.hypot(bx_ - ax, by_ - ay)
        yaw = math.degrees(math.atan2(by_ - ay, bx_ - ax))
        with b.at(WF(ax, ay, 0, yaw)):
            ww = 0.62 if ln < 1.2 else 1.0
            ops = [Op((ln - ww) / 2, (ln + ww) / 2, 1.35, 3.0)]
            f3 = arch.wall(mb, ln, fz, 3.45, ops, "flat", red)
            arch.window(b, ops[0].u0, ops[0].u1, 1.35, 3.0, face=f3, trim=white, panes=(1, 2), cell=0, head="plain", cw=0.07,
                        box_d=0.3)
            mb.boxc((ln, 0.04, 0.22), white, loc=(ln / 2, -0.02, fz + 0.11), skip="k")
    mb.poly([(1.62, yb, 3.45), (1.0, yb + 1.08, 3.45), (-1.0, yb + 1.08, 3.45), (-1.62, yb, 3.45)], white, thick=0.16,
            facing=(0, 0, -1))
    # ---------------- roof (ridge along X, deep eaves both sides, gables both ends)
    with b.at(Rz(90)):
        zr = arch.gable_roof(b, yf, yb, -x1, -x0, z_eave, pitch, oh_side=2.0, oh_back=0.8, oh_front=0.8,
                             mat="roof_shingle", fascia=white, back_gable=("bnb", red), front_gable=("bnb", red),
                             rafter_step=0.8)
    # knee braces under the deep eaves
    t = math.tan(math.radians(pitch))
    for xx in (-6.6, -3.9, -1.2, 1.5, 4.2, 6.9):
        for sgn, yw in ((1, yb), (-1, yf)):
            mb.boxc((0.14, 0.07, 1.3), white, loc=(xx, yw + sgn * 0.06, 3.3), skip="d")
            d = 1.55
            mb.span((xx, yw + sgn * 0.08, 2.75), (xx, yw + sgn * d, z_eave - 0.1 - d * t), 0.11, 0.11, white, up=(1, 0, 0),
                    bev=0.012)
    # gable stick-work + gable name boards
    for sgn in (-1, 1):
        xg = sgn * (W / 2 + 0.03)
        yc = (yf + yb) / 2
        mb.span((xg, yf + 0.3, z_eave + 0.05), (xg, yb - 0.3, z_eave + 0.05), 0.04, 0.14, white, up=(0, 0, 1))
        mb.span((xg, yc, z_eave + 0.05), (xg, yc, zr - 0.5), 0.04, 0.12, white, up=(0, 0, 1))
        for yy in (yf + 0.9, yb - 0.9):
            mb.span((xg, yy, z_eave + 0.12), (xg, yc, zr - 0.6), 0.04, 0.1, white, up=(0, 0, 1))
        with b.at(WF(xg, yb if sgn < 0 else yf, 0, -90 if sgn < 0 else 90)):
            arch.sign_board(b, D / 2, -0.02, 4.62, 2.9, 0.36, "label_station", frame=white, body=white, molding=0.035)
            if sgn > 0:
                b.lab.panel(1.4, 0.175, "label_depot_small", loc=(D / 2, -0.06, 3.58), uv=SMALL["elev"])
    arch.chimney(mb, -1.6, -1.6, z_eave, zr - z_eave + 0.9, mat="brick")
    arch.stovepipe(mb, 5.0, -2.6, zr - 0.6 * t - 0.04, h=1.3)
    # ---------------- street-side porch at the main door
    pz = fz
    arch.deck(mb, 2.2, 5.0, yf - 1.1, yf + face, pz)
    for k in range(3):
        zt = pz * (k + 1) / 4
        yy = yf - 1.1 - 0.3 * (3 - k)
        arch.treads(mb, 2.2, 5.0, yy, yy + 0.32, zt, t=0.05)
        mb.boxc((2.8, 0.03, zt - 0.05), arch.DECK, loc=(3.6, yy + 0.04, (zt - 0.05) / 2), skip="k", tone=0.85)
        for xs in (2.26, 4.94):
            mb.boxc((0.06, 0.3, zt), "wood_timber", loc=(xs, yy + 0.15, zt / 2), skip="d")
    mb.boxc((2.8, 0.04, pz - 0.05), "wood_timber", loc=(3.6, yf - 1.08, (pz - 0.05) / 2), skip="k")
    # ---------------- canopy over the east platform (central posts, gable roof)
    cy = 1.6
    cx0, cx1 = x1 + 0.6, PX - 0.4
    posts = [cx0 + 0.8 + i * (cx1 - cx0 - 1.6) / 3 for i in range(4)]
    zb = 3.3
    for px in posts:
        arch.square_post(mb, px, cy, fz, zb, "wood_timber", s=0.2)
        for sgn in (-1, 1):
            mb.span((px, cy + sgn * 0.1, zb - 0.8), (px, cy + sgn * 1.2, zb + 0.05), 0.1, 0.1, "wood_timber", up=(1, 0, 0))
    mb.boxc((cx1 - cx0, 0.2, 0.28), "wood_timber", loc=((cx0 + cx1) / 2, cy, zb + 0.14), uvoff=True)
    ce = 2.05
    for sgn in (-1, 1):
        pts = [(cx0, cy, zb + 0.75), (cx1, cy, zb + 0.75), (cx1, cy + sgn * ce, zb + 0.05), (cx0, cy + sgn * ce, zb + 0.05)]
        mb.poly(pts, "corrugated", thick=0.04, facing=(0, sgn * 0.3, 1))
        mb.boxc((cx1 - cx0 + 0.08, 0.03, 0.18), white, loc=((cx0 + cx1) / 2, cy + sgn * (ce + 0.015), zb - 0.03), skip="")
        n = int((cx1 - cx0) / 0.9)
        for i in range(n + 1):
            xx = cx0 + 0.05 + (cx1 - cx0 - 0.1) * i / n
            mb.span((xx, cy, zb + 0.66), (xx, cy + sgn * (ce - 0.05), zb - 0.02), 0.05, 0.1, "wood_timber", up=(0, 0, 1))
    for px in posts[:-1]:
        arch.hanging_lamp(mb, px + (posts[1] - posts[0]) / 2, cy, zb, drop=0.3)
    # ---------------- platform dressing
    lamp_post(mb, -12.0, yE - 0.75, fz)
    lamp_post(mb, -19.5, yE - 0.75, fz)
    arch.bench(mb, 6.2, yb + 0.38, fz, L=1.9, rot=180)
    arch.bench(mb, -2.9, yb + 0.38, fz, L=1.9, rot=180)
    arch.bench(mb, 14.0, cy, fz, L=1.9, rot=90)
    luggage_cart(mb, -13.8, 1.7, fz, rot=8)
    for i, (xx, yy) in enumerate(((-9.0, 1.0), (-9.6, 1.6), (-8.8, 1.9))):
        arch.barrel(mb, xx, yy, fz, tone=0.9 + 0.03 * i)
    arch.crate(mb, -10.6, 1.0, fz, s=(0.8, 0.6, 0.6), rot=-6)
    arch.crate(mb, -10.5, 1.05, fz + 0.6, s=(0.6, 0.5, 0.45), rot=10)
    for k, (xx, yy) in enumerate(((-16.4, 1.2), (-16.0, 1.25), (-16.2, 0.85))):
        mb.lathe([(0.16, 0), (0.17, 0.05), (0.17, 0.45), (0.12, 0.55), (0.08, 0.62), (0.085, 0.68)], "aluminium",
                 loc=(xx, yy, fz), sides=10, cap_top=True)
    # ---------------- markers
    b.empties += [("spawn", (4.0, 2.4, fz), (0, 0, 0)), ("track", (0.0, TRACK_Y, 0.0), (0, 0, 0)),
                  ("door_street", (3.6, yf - 0.6, fz), (0, 0, 0)), ("door_platform", (4.0, yb + 0.7, fz), (0, 0, 180))]
    return b.finish()


NODES = {"depot": depot}
