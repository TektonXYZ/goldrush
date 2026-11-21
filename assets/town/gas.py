"""gas_station: weathered fuel stop. Canopy on steel columns with lights, two pumps (hoses, nozzles,
displays), corrugated kiosk, oil-drum racks, an 8.8 m price pylon whose child `board_face` (sign_face,
UV 0-1, 3.2 x 2.4 m, landscape) the game paints, inside a backlit (emit_white) frame."""
import math

import arch
from arch import B, Op, WF
import tk
from tk import T

GAS = {  # label_gas atlas rows (Blender UV, v up)
    "header": (0.0, 0.75, 1.0, 1.0), "band": (0.0, 0.625, 1.0, 0.75), "kiosk": (0.0, 0.375, 1.0, 0.5),
    "open": (0.0, 0.0, 0.5, 0.25), "unleaded": (0.5, 0.125, 1.0, 0.25), "diesel": (0.5, 0.0, 1.0, 0.125),
}


def pump(b, x, y, z, label):
    """Modern-but-worn dispenser: cabinet, display heads both sides, nozzles + hoses, bollards."""
    mb = b.mb
    w, d, h = 0.95, 0.55, 1.75
    mb.boxc((w + 0.1, d + 0.1, 0.12), "steel_dark", loc=(x, y, z + 0.06), bev=0.01)
    mb.boxc((w, d, h - 0.5), "paint_white", loc=(x, y, z + 0.12 + (h - 0.5) / 2), bev=0.02)
    mb.boxc((w + 0.02, d + 0.02, 0.06), "paint_red", loc=(x, y, z + 0.12 + h - 0.5), bev=0.01)
    mb.boxc((w, d * 0.8, 0.42), "paint_red", loc=(x, y, z + h - 0.21 + 0.12), bev=0.025)
    for sy in (-1, 1):
        yy = y + sy * (d * 0.4 + 0.004)
        # display window (emissive digits) + brand plate
        mb.boxc((0.5, 0.01, 0.2), "emit_green", loc=(x, yy, z + h - 0.15))
        mb.boxc((0.62, 0.01, 0.04), "plastic_black", loc=(x, yy, z + h - 0.03))
        b.lab.panel(0.6, 0.15, "label_gas", loc=(x, y + sy * (d / 2 + 0.006), z + 0.95), uv=GAS[label], rot=(0, 0, 0 if sy < 0 else 180))
        mb.boxc((0.7, 0.01, 0.42), "plastic_black", loc=(x, y + sy * (d / 2 + 0.003), z + 0.42))
        # nozzle holster + nozzle on the end
    for sx in (-1, 1):
        xx = x + sx * (w / 2 + 0.03)
        mb.boxc((0.06, 0.18, 0.3), "plastic_black", loc=(xx, y, z + 1.05))
        with mb.at((xx + sx * 0.04, y, z + 1.12), (0, 0, 90 if sx > 0 else -90)):
            mb.boxc((0.05, 0.12, 0.18), "plastic_black", loc=(0, 0, 0), rot=(20, 0, 0), bev=0.01)
            mb.cyl(0.014, 0.22, "aluminium", loc=(0, -0.08, 0.05), rot=(-70, 0, 0), sides=6)
        # hose: from the top of the cabinet, sagging to near the ground, up to the nozzle
        pts = [(x + sx * (w / 2 - 0.05), y, z + h + 0.05), (x + sx * (w / 2 + 0.25), y + 0.05, z + 1.2),
               (x + sx * (w / 2 + 0.33), y + 0.08, z + 0.45), (x + sx * (w / 2 + 0.2), y + 0.06, z + 0.3),
               (x + sx * (w / 2 + 0.07), y + 0.02, z + 0.95)]
        mb.tube(pts, 0.018, "rubber", sides=6)


def gas_station(seed=71):
    b = B("gas_station", seed)
    mb = b.mb
    # concrete pad (+ oil stains)
    mb.boxc((20.0, 13.0, 0.12), "concrete", loc=(0, -0.5, 0.06), bev=0.03, skip="d")
    for (sx, sy, r) in ((-2.2, -1.2, 1.0), (2.2, 0.6, 1.2), (-2.6, 1.4, 0.7), (1.8, -2.0, 0.8), (-7.0, 3.5, 0.9)):
        n = 9
        pts = [(sx + math.cos(a) * r * (0.7 + 0.3 * math.sin(a * 3 + sx)), sy + math.sin(a) * r * 0.7, 0.122)
               for a in (i / n * math.tau for i in range(n))]
        mb.poly(pts, "concrete", tone=0.55, facing=(0, 0, 1))
    # canopy
    cx, cy, cw, cd = 0.0, -0.5, 12.0, 8.0
    zc = 5.0
    for px in (-4.5, 4.5):
        for py in (cy - 2.6, cy + 2.6):
            mb.boxc((0.32, 0.32, zc), "paint_white", loc=(px, py, zc / 2 + 0.06), bev=0.02, skip="d")
            mb.boxc((0.5, 0.5, 0.25), "concrete", loc=(px, py, 0.18), bev=0.02, skip="d")
            mb.boxc((0.34, 0.34, 0.3), "rust", loc=(px, py, 0.45), bev=0.01, skip="du")
    mb.boxc((cw, cd, 0.18), "galvanized", loc=(cx, cy, zc + 0.86), skip="d")
    mb.poly([(cx - cw / 2, cy - cd / 2, zc + 0.02), (cx + cw / 2, cy - cd / 2, zc + 0.02), (cx + cw / 2, cy + cd / 2, zc + 0.02),
             (cx - cw / 2, cy + cd / 2, zc + 0.02)], "paint_white", facing=(0, 0, -1), tone=0.9)
    for sx in (-1, 1):
        mb.boxc((0.06, cd + 0.12, 0.9), "paint_red", loc=(cx + sx * (cw / 2 + 0.03), cy, zc + 0.45), skip="")
    for sy in (-1, 1):
        mb.boxc((cw + 0.12, 0.06, 0.9), "paint_red", loc=(cx, cy + sy * (cd / 2 + 0.03), zc + 0.45), skip="")
        b.lab.panel(9.6, 0.62, "label_gas", loc=(cx, cy + sy * (cd / 2 + 0.065), zc + 0.14), uv=GAS["band"],
                    rot=(0, 0, 0 if sy < 0 else 180))
    for lx in (-3.0, 0.0, 3.0):
        for ly in (cy - 2.0, cy + 2.0):
            mb.boxc((1.2, 0.5, 0.04), "emit_white", loc=(lx, ly, zc - 0.02))
            mb.boxc((1.3, 0.6, 0.05), "aluminium", loc=(lx, ly, zc - 0.005))
    # pump islands
    for i, px in enumerate((-2.2, 2.2)):
        mb.boxc((1.1, 4.2, 0.2), "concrete", loc=(px, cy, 0.22), bev=0.03)
        mb.boxc((1.14, 4.24, 0.05), "paint_yellow", loc=(px, cy, 0.35), tone=0.8)
        pump(b, px, cy, 0.37, "unleaded" if i == 0 else "diesel")
        for py in (cy - 1.85, cy + 1.85):
            mb.cyl(0.1, 1.0, "paint_yellow", loc=(px, py, 0.37), sides=10, tone=0.85)
            mb.cyl(0.11, 0.06, "paint_black", loc=(px, py, 0.95), sides=10)
        mb.cyl(0.25, 0.9, "plastic_black", loc=(px + 0.35, cy + 1.4, 0.37), r2=0.22, sides=10)
        b.empties.append((f"pump_{i}", (px + (1.0 if i else -1.0), cy, 0.12), (0, 0, 0)))
    # kiosk (corrugated walls, glass front, flat roof with parapet + AC unit)
    kx0, kx1, ky0, ky1 = -9.0, -3.5, 2.2, 5.6
    kz = 3.2
    with b.at(WF(kx0, ky0, 0, 0)):
        ops = [Op(0.6, 3.4, 0.9, 2.5), Op(3.8, 4.8, 0.12, 2.3)]
        arch.flat_wall(mb, kx1 - kx0, 0.12, kz, ops, "corrugated")
        arch.storefront(b, 0.6, 3.4, 0.12, face=0.0, trim="aluminium", panel="paint_white", glass_top=2.4, transom_top=2.5,
                        bulk=0.75, cell=1, frame=0.06)
        arch.door(b, 3.8, 4.8, 0.12, 2.3, face=0.0, trim="aluminium", leaf="aluminium", leaves=1, glazed=True, cell=1,
                  transom=0, vest_d=1.2, counter=False, cw=0.06)
        b.lab.panel(5.0, 0.62, "label_gas", loc=((kx1 - kx0) / 2, -0.07, 2.62), uv=GAS["kiosk"])
        mb.boxc((5.2, 0.06, 0.72), "paint_white", loc=((kx1 - kx0) / 2, -0.03, 2.94), skip="k")
        b.lab.panel(0.8, 0.4, "label_gas", loc=(1.2, 0.07, 1.9), uv=GAS["open"])
    for frame, w_ in ((WF(kx1, ky0, 0, 90), ky1 - ky0), (WF(kx1, ky1, 0, 180), kx1 - kx0), (WF(kx0, ky1, 0, -90), ky1 - ky0)):
        with b.at(frame):
            arch.flat_wall(mb, w_, 0.12, kz, [Op(1.2, 2.2, 1.2, 2.2)] if w_ < 4 else [], "corrugated")
            if w_ < 4:
                arch.window(b, 1.2, 2.2, 1.2, 2.2, face=0.0, trim="aluminium", sash="aluminium", panes=(1, 1), cell=6,
                            cw=0.05, head="plain", sash_kind="fixed", apron=False)
    mb.boxc((kx1 - kx0 + 0.3, ky1 - ky0 + 0.3, 0.15), "galvanized", loc=((kx0 + kx1) / 2, (ky0 + ky1) / 2, kz + 0.075))
    for sx in (-1, 1):
        mb.boxc((0.05, ky1 - ky0 + 0.3, 0.35), "paint_white", loc=((kx0 + kx1) / 2 + sx * (kx1 - kx0 + 0.25) / 2, (ky0 + ky1) / 2, kz + 0.25))
    mb.boxc((1.2, 0.9, 0.7), "galvanized", loc=(-5.0, 4.5, kz + 0.5), bev=0.02)
    mb.cyl(0.32, 0.04, "steel_dark", loc=(-5.0, 4.5, kz + 0.86), sides=14)
    for k in range(8):
        a = k * math.pi / 8
        mb.span((-5.0 - math.cos(a) * 0.3, 4.5 - math.sin(a) * 0.3, kz + 0.9), (-5.0 + math.cos(a) * 0.3, 4.5 + math.sin(a) * 0.3, kz + 0.9),
                0.015, 0.015, "steel_dark")
    mb.boxc((1.4, 0.8, 1.0), "paint_white", loc=(-2.6, 2.5, 0.12 + 0.5), bev=0.04, skip="d")
    mb.boxc((1.42, 0.82, 0.08), "paint_blue", loc=(-2.6, 2.5, 0.12 + 1.0), bev=0.02)
    # oil drum racks
    drums = ("paint_blue", "paint_red", "paint_green", "rust")
    for r_, (rx, ry) in enumerate(((-9.4, -2.0), (-9.4, 0.4))):
        for sx in (-1, 1):
            mb.span((rx + sx * 0.5, ry - 0.9, 0.12), (rx + sx * 0.5, ry - 0.9, 1.4), 0.06, 0.06, "steel_dark")
            mb.span((rx + sx * 0.5, ry + 0.9, 0.12), (rx + sx * 0.5, ry + 0.9, 1.4), 0.06, 0.06, "steel_dark")
            for zz in (0.5, 1.25):
                mb.span((rx + sx * 0.5, ry - 0.9, zz), (rx + sx * 0.5, ry + 0.9, zz), 0.06, 0.06, "steel_dark")
        for k in range(2):
            for lvl, zz in enumerate((0.84, 1.59)):
                mat = drums[(k + lvl + r_) % 4]
                arch.barrel(mb, rx, ry - 0.42 + k * 0.84, zz - 0.3, r=0.29, h=0.88, lid=mat, stave=mat, hoop=mat, lying=True, rot=0)
    for k, (dx, dy) in enumerate(((-7.4, -3.4), (-6.8, -3.6))):
        mb.lathe([(0.29, 0), (0.29, 0.88)], drums[k], loc=(dx, dy, 0.12), sides=14, cap_top=True)
        for hz in (0.29, 0.59):
            mb.lathe([(0.3, hz - 0.02), (0.3, hz + 0.02)], drums[k], loc=(dx, dy, 0.12), sides=14, cap_top=False, cap_bot=False)
    # price pylon (8.8 m) with backlit frame; board_face child
    px, py = 7.6, -5.6
    bw, bh, bz = 3.2, 2.4, 5.45
    for sx in (-1, 1):
        mb.boxc((0.42, 0.42, bz - 0.12), "paint_white", loc=(px + sx * 1.15, py + 0.12, (bz - 0.12) / 2), bev=0.03,
                skip="d")
        mb.boxc((0.7, 0.7, 0.5), "concrete", loc=(px + sx * 1.15, py + 0.12, 0.25), bev=0.03, skip="d")
        mb.boxc((0.44, 0.44, 0.06), "paint_red", loc=(px + sx * 1.15, py + 0.12, bz - 0.4))
    for zz in (2.2, 4.1):
        mb.boxc((1.9, 0.2, 0.25), "steel_dark", loc=(px, py + 0.12, zz), bev=0.01)
    mb.boxc((bw + 0.34, 0.4, bh + 0.3), "steel_dark", loc=(px, py + 0.12, bz + bh / 2), bev=0.02)
    mb.boxc((bw + 0.34, 0.42, 0.06), "paint_red", loc=(px, py + 0.12, bz - 0.15 + 0.03))
    t = 0.07
    for (dx, dz, ww, hh) in ((0, bh / 2 + t / 2, bw + 2 * t, t), (0, -bh / 2 - t / 2, bw + 2 * t, t), (-bw / 2 - t / 2, 0, t, bh),
                             (bw / 2 + t / 2, 0, t, bh)):
        mb.boxc((ww, 0.05, hh), "emit_white", loc=(px + dx, py - 0.1, bz + bh / 2 + dz))
    mb.boxc((bw + 0.34, 0.4, 0.9), "paint_red", loc=(px, py + 0.12, bz + bh + 0.6), bev=0.02)
    b.lab.panel(bw + 0.2, 0.8, "label_gas", loc=(px, py - 0.082, bz + bh + 0.2), uv=GAS["header"])
    b.lab.panel(bw + 0.2, 0.8, "label_gas", loc=(px, py + 0.322, bz + bh + 0.2), uv=GAS["header"], rot=(0, 0, 180))
    mb.boxc((bw, 0.02, bh), "paint_white", loc=(px, py + 0.33, bz + bh / 2), tone=0.85)
    root = b.finish()
    face = tk.MB("board_face")
    face.panel(bw, bh, "sign_face", loc=(px, py - 0.085, bz))
    fo = face.finish(parent=root, weighted=False)
    tk.strip_colors(fo)
    tk.empty("board", (px, py - 0.1, bz + bh / 2), parent=root)
    return root


NODES = {"gas_station": gas_station}
