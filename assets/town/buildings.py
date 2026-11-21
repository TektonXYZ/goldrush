"""Main Street buildings: land_office, assay_office, general_store, saloon.

Blender coords: front = -Y (three.js +Z), origin = ground centre of the footprint (porch + steps included).
"""
import math

import arch
from arch import B, Op, WF
import tk
from tk import T

WASH = 0.8  # whitewash gone grey (land office sides + back)
SALOON_WASH = 0.7  # older, greyer whitewash on the saloon's sides + back
LABEL_GLASS_TOP = ((0.02, 0.55, 0.98, 0.94), 4.9)    # "LAND OFFICE"
LABEL_GLASS_BOT = ((0.02, 0.08, 0.98, 0.46), 4.9)    # "ASSAYS · BULLION"


def _foundation(b, x0, x1, y0, y1, z):
    """Mortar core under the body + rubble-stone courses on the sides and back (the porch hides the front)."""
    b.mb.boxc((x1 - x0, y1 - y0, z + 0.12), "concrete", loc=((x0 + x1) / 2, (y0 + y1) / 2, (z - 0.12) / 2), skip="ud",
              tone=0.5)
    arch.foundation(b, x0, x1, y0, y1, z, sides="lrk")


def _parapet_back(mb, x0, x1, y_back, z_eave, z_ridge, z_top, braces=True, roof_pitch=16, roof_y0=None):
    """Unfinished back of a false front above the roof line + end boards + raking braces."""
    xc = (x0 + x1) / 2
    pts = [(x0, y_back, z_eave), (xc, y_back, z_ridge), (x1, y_back, z_eave), (x1, y_back, z_top), (x0, y_back, z_top)]
    mb.poly(pts, "wood_planks", facing=(0, 1, 0), grain_dir=(0, 0, 1))
    # studs on the back
    n = int((x1 - x0) / 0.6)
    t = math.tan(math.radians(roof_pitch))
    for i in range(1, n):
        x = x0 + (x1 - x0) * i / n
        zr = z_ridge - abs(x - xc) * t
        if z_top - zr > 0.3:
            mb.boxc((0.05, 0.1, z_top - zr), "wood_timber", loc=(x, y_back + 0.05, (z_top + zr) / 2), skip="d", uvoff=True)
    if braces:
        for x in (x0 + (x1 - x0) * 0.25, x1 - (x1 - x0) * 0.25):
            zr = z_ridge - abs(x - xc) * t
            mb.span((x, y_back + 0.1, z_top - 0.35), (x, y_back + 2.2, z_ridge - abs(x - xc) * t + 0.08), 0.09, 0.09,
                    "wood_timber", up=(1, 0, 0))


def land_office(seed=11):
    """U.S. Land Office: two-storey white clapboard false front, green trim, bracketed cornice with a
    pediment, balcony porch on turned posts, open double doors over a lit office, CLAIMS FOR SALE board."""
    b = B("land_office", seed)
    mb = b.mb
    W, yf, yb = 10.0, -4.0, 7.0
    x0, x1 = -W / 2, W / 2
    fz = 0.5           # floor
    z_eave = 7.6
    z_top = 8.9        # top of facade siding (cornice starts)
    pitch = 16
    white, green = "wood_painted_white", "wood_painted_green"
    _foundation(b, x0, x1, yf, yb, fz)
    # ---------------- facade
    ops = [Op(0.75, 3.85, fz, 3.65), Op(6.15, 9.25, fz, 3.65), Op(4.15, 5.85, fz, 3.65),
           Op(1.35, 2.35, 5.1, 6.9), Op(7.65, 8.65, 5.1, 6.9), Op(4.45, 5.55, 4.56, 6.9)]
    with b.at(WF(x0, yf, 0, 0)):
        face = arch.wall(mb, W, fz, z_top, ops, "clap", white)
        arch.corner_boards(mb, W, fz, z_top, face, white, cw=0.16)
        arch.storefront(b, 0.75, 3.85, fz, face=face, trim=green, panel=green, glass_top=3.0, transom_top=3.65,
                        bulk=0.6, cell=0)
        arch.storefront(b, 6.15, 9.25, fz, face=face, trim=green, panel=green, glass_top=3.0, transom_top=3.65,
                        bulk=0.6, cell=5)
        arch.door(b, 4.15, 5.85, fz, 3.1, face=face, trim=green, leaf=green, leaves=2, open_deg=74, glazed=True,
                  cell=0, transom=0.55, transom_label=LABEL_GLASS_TOP, vest_d=2.6)
        for u0 in (1.35, 7.65):
            arch.window(b, u0, u0 + 1.0, 5.1, 6.9, face=face, trim=green, panes=(2, 1), cell=4 if u0 < 5 else 3,
                        shade=0.28, head="cap")
        arch.door(b, 4.45, 5.55, 4.56, 6.9, face=face, trim=green, leaf=green, leaves=1, glazed=True, cell=3,
                  transom=0, lamp=False, counter=False, vest_d=0.8, threshold=False)
        # sign board in the frieze
        arch.sign_board(b, W / 2, face, 8.02, 7.2, 1.15, "label_land_office", frame=green, body=green)
    yface = yf + face
    # wall lanterns either side of the door, a hanging lamp under the balcony
    for x in (-1.06, 1.06):
        arch.wall_lantern(mb, x, yface - 0.03, 2.75, arm=0.28)
    # ---------------- porch with balcony
    zbal = arch.porch(b, x0, x1, yface, 2.4, fz, [-4.8, -1.55, 1.55, 4.8], 4.05, roof="balcony", post="turned",
                      trim=white, post_mat=white, rail_mat=white,
                      fascia_label=((0.0, 0.0, 1.0, 1.0), 6.4, "label_land_fascia"))
    arch.hanging_lamp(mb, 0.0, yface - 1.15, 4.31, drop=0.45)
    # ---------------- cornice + pediment crest
    zc = arch.cornice(mb, x0, x1, yface, z_top, proj=0.42, mat=white, spacing=0.95)
    arch.pediment(mb, 0.0, yface - 0.0, zc, 3.9, 0.95, mat=white, back="wood_planks", thick=0.2)
    # ---------------- side + back walls (Queen Anne front, Mary Ann behind: weathered board-and-batten)
    depth = yb - yf
    side_ops = [Op(2.6, 3.5, 1.35, 3.05), Op(5.6, 6.5, 1.35, 3.05), Op(8.6, 9.5, 1.35, 3.05),
                Op(2.6, 3.5, 5.15, 6.75), Op(5.6, 6.5, 5.15, 6.75), Op(8.6, 9.5, 5.15, 6.75)]
    for frame, mirror in ((WF(x1, yf, 0, 90), False), (WF(x0, yb, 0, -90), True)):
        with b.at(frame):
            ops2 = [Op(depth - o.u1, depth - o.u0, o.v0, o.v1) for o in side_ops] if mirror else side_ops
            face2 = arch.wall(mb, depth, fz, z_eave, ops2, "bnb", white, tone=WASH)
            arch.corner_boards(mb, depth, fz, z_eave, face2, white, cw=0.14)
            arch.water_table(mb, depth, fz, face2, white, h=0.2)
            for k, o in enumerate(ops2):
                arch.window(b, o.u0, o.u1, o.v0, o.v1, face=face2, trim=green, sash=white, panes=(2, 1),
                            cell=[6, 3, 4, 1, 7, 6][k] if k % 2 == 0 else None, shade=0.35 if k % 3 == 0 else 0.0,
                            head="plain", cw=0.09, shutters=green if k in (1, 4) else None, lod="simple")
            # eave plate
            mb.boxc((depth, 0.05, 0.2), white, loc=(depth / 2, face2 - 0.025, z_eave - 0.1), skip="k")
    with b.at(WF(x1, yb, 0, 180)):
        bops = [Op(6.4, 7.35, fz, 2.65), Op(2.2, 3.1, 1.35, 3.05), Op(2.2, 3.1, 5.15, 6.75), Op(6.9, 7.8, 5.15, 6.75)]
        face3 = arch.wall(mb, W, fz, z_eave, bops, "bnb", white, tone=WASH)
        arch.water_table(mb, W, fz, face3, white, h=0.2, ops=bops[:1])
        arch.door(b, 6.4, 7.35, fz, 2.65, face=face3, trim=green, leaf="wood_planks", leaves=1, glazed=False,
                  cell=None, transom=0, cw=0.09)
        for o in bops[1:]:
            arch.window(b, o.u0, o.u1, o.v0, o.v1, face=face3, trim=green, sash=white, cell=None, head="plain",
                        cw=0.09, lod="simple")
    # back stoop outside the back door
    mb.boxc((1.4, 0.9, fz - 0.02), "wood_planks", loc=(x1 - 6.875, yb + 0.47, (fz - 0.02) / 2), skip="d", uvoff=True)
    mb.boxc((1.4, 0.32, (fz - 0.02) / 2), "wood_planks", loc=(x1 - 6.875, yb + 1.08, (fz - 0.02) / 4), skip="d")
    # ---------------- roof
    zr = arch.gable_roof(b, x0, x1, yf + 0.16, yb, z_eave, pitch, mat="roof_shingle", fascia=white,
                         back_gable=("bnb", white, WASH))
    _parapet_back(mb, x0, x1, yf + 0.16, z_eave, zr - 0.06, zc - 0.02, roof_pitch=pitch)
    # parapet end boards (false front thickness) + cap
    for x in (x0, x1):
        mb.boxc((0.04, 0.2, zc - fz), white, loc=(x + (0.02 if x > 0 else -0.02), yf + 0.08 - 0.02, (zc + fz) / 2), skip="d")
    t = math.tan(math.radians(pitch))
    arch.chimney(mb, -3.0, 5.2, 7.2, 3.0, mat="brick")
    arch.stovepipe(mb, 2.6, 1.8, z_eave + (W / 2 + 0.45 - 2.6) * t - 0.1 + 0.08, h=1.5)
    # ---------------- porch dressing: CLAIMS FOR SALE board, bench, barrel, crate
    bx, by = -3.15, yface - 2.05
    for dx in (-0.72, 0.72):
        arch.square_post(mb, bx + dx, by, fz, fz + 2.55, "wood_timber", s=0.1)
    mb.boxc((1.36, 0.06, 1.66), "wood_dark", loc=(bx, by - 0.06, fz + 1.72), skip="k")
    mb.span((bx - 0.82, by - 0.12, fz + 2.62), (bx + 0.82, by - 0.12, fz + 2.62), 0.26, 0.04, "wood_planks", up=(0, -0.4, 1))
    b.lab.panel(1.3, 1.6, "label_claims_board", loc=(bx, by - 0.092, fz + 0.92))
    arch.bench(mb, 3.2, yface - 0.34, fz, L=1.9)
    arch.barrel(mb, 4.25, yface - 1.85, fz, tone=0.95)
    arch.crate(mb, -4.25, yface - 1.05, fz, s=(0.62, 0.5, 0.46), rot=8)
    # ---------------- markers
    b.empties += [("door", (0.0, yface - 0.35, fz), (0, 0, 0)),
                  ("door_light", (0.0, yf + 1.2, 2.6), (0, 0, 0)),
                  ("claims_board", (bx, by - 0.2, fz + 1.7), (0, 0, 0))]
    return b.finish()


def _gallery_roof(b, x0, x1, yface, depth, post_xs, z0, z1, trim, roof="corrugated", square=False):
    """Second-tier gallery: slim posts from the balcony up to a shed roof against the facade."""
    mb = b.mb
    ypost = yface - depth + 0.16
    for px in post_xs:
        if square:
            mb.boxc((0.12, 0.12, z1 - z0), trim, loc=(px, ypost, (z0 + z1) / 2), bev=0.012, skip="du")
        else:
            arch.turned_post(mb, px, ypost, z0, z1, trim, s=0.85)
    mb.boxc((x1 - x0 + 0.1, 0.14, 0.2), trim, loc=((x0 + x1) / 2, ypost, z1 + 0.1), bev=0.01)
    for px in post_xs:
        for sgn in (-1, 1):
            if (px <= x0 + 0.3 and sgn < 0) or (px >= x1 - 0.3 and sgn > 0):
                continue
            arch.bracket(mb, px + sgn * 0.065, ypost, z1, sgn, 0.34, 0.34, 0.04, trim)
    zt = z1 + 0.55
    mb.poly([(x0 - 0.15, ypost - 0.3, z1 + 0.22), (x1 + 0.15, ypost - 0.3, z1 + 0.22), (x1 + 0.15, yface, zt),
             (x0 - 0.15, yface, zt)], roof, thick=0.04, facing=(0, -0.3, 1))
    mb.boxc((x1 - x0 + 0.3, 0.03, 0.16), trim, loc=((x0 + x1) / 2, ypost - 0.315, z1 + 0.16), skip="")
    n = int((x1 - x0) / 0.7)
    for i in range(n + 1):
        xx = x0 + (x1 - x0) * i / n
        mb.span((xx, ypost - 0.28, z1 + 0.2), (xx, yface, zt - 0.03), 0.045, 0.1, "wood_timber", up=(0, 0.3, 1))
    return zt


def saloon(seed=13):
    """Green clapboard saloon: two-tier gallery (balcony with its own roof), batwing doors over a lit
    bar, cafe curtains, dentil cornice with a segmental-arch crest, SALOON board."""
    b = B("saloon", seed)
    mb = b.mb
    W, yf, yb = 12.0, -4.0, 8.0
    x0, x1 = -W / 2, W / 2
    fz, z_eave, z_top, pitch = 0.5, 7.9, 9.4, 15
    green, white = "wood_painted_green", "wood_painted_white"
    _foundation(b, x0, x1, yf, yb, fz)
    ground = [(1.2, 2.3), (3.1, 4.2), (7.8, 8.9), (9.7, 10.8)]
    upper = [(1.4, 2.3), (3.5, 4.4), (7.6, 8.5), (9.7, 10.6)]
    ops = [Op(5.15, 6.85, fz, 3.55)] + [Op(a, c, 0.95, 3.35) for a, c in ground] + [Op(a, c, 5.2, 7.0) for a, c in upper] + \
          [Op(5.45, 6.55, 4.62, 7.0)]
    with b.at(WF(x0, yf, 0, 0)):
        face = arch.wall(mb, W, fz, z_top, ops, "clap", green)
        arch.corner_boards(mb, W, fz, z_top, face, white, cw=0.18)
        arch.water_table(mb, W, fz, face, white, h=0.25)
        for k, (a, c) in enumerate(ground):
            arch.window(b, a, c, 0.95, 3.35, face=face, trim=white, panes=(2, 1), cell=2, cafe=0.33, head="pediment")
        for k, (a, c) in enumerate(upper):
            arch.window(b, a, c, 5.2, 7.0, face=face, trim=white, panes=(2, 1), cell=[4, 7, 3, 4][k], shade=0.3, head="cap",
                        shutters=green if k in (0, 3) else None)
        arch.door(b, 5.15, 6.85, fz, 3.05, face=face, trim=white, leaf=white, batwing=True, open_deg=14, cell=2,
                  transom=0.5, vest_d=3.2, counter=True)
        arch.door(b, 5.45, 6.55, 4.62, 7.0, face=face, trim=white, leaf=green, leaves=1, glazed=True, cell=7, transom=0,
                  lamp=False, counter=False, vest_d=0.8, threshold=False)
        arch.sign_board(b, W / 2, face, 8.58, 7.6, 1.5, "label_saloon", frame=white, body=white)
    yface = yf + face
    for x in (-1.25, 1.25):
        arch.wall_lantern(mb, x, yface - 0.03, 2.85, arm=0.3)
    posts = [-5.8, -2.9, 2.9, 5.8]
    zbal = arch.porch(b, x0, x1, yface, 2.4, fz, posts, 4.08, roof="balcony", post="turned", trim=white, post_mat=white,
                      rail_mat=white, rail_style="x")
    arch.hanging_lamp(mb, 0.0, yface - 1.2, 4.34, drop=0.4)
    _gallery_roof(b, x0, x1, yface, 2.4, posts, zbal, 6.85, white, square=True)
    zc = arch.cornice(mb, x0, x1, yface, z_top, proj=0.45, mat=white, spacing=1.0, dentils=False)
    # segmental-arch crest
    half, rise = 3.2, 1.05
    seg = 12
    R = (half * half + rise * rise) / (2 * rise)
    cz = zc + rise - R
    a0 = math.asin(half / R)
    arc = [(math.sin(-a0 + 2 * a0 * i / seg) * R, cz + math.cos(-a0 + 2 * a0 * i / seg) * R) for i in range(seg + 1)]
    mb.poly([(x, yface, z) for x, z in arc], green, facing=(0, -1, 0), grain_dir=(1, 0, 0))
    mb.poly([(x, yf + 0.18, z) for x, z in arc], "wood_planks", facing=(0, 1, 0))
    for i in range(seg):
        (xa, za), (xb, zb) = arc[i], arc[i + 1]
        mb.span((xa, yface - 0.03, za + 0.02), (xb, yface - 0.03, zb + 0.02), 0.28, 0.09, white, up=(0, 0, 1))
    mb.cyl(0.22, 0.05, white, loc=(0, yface - 0.025, zc + 0.5), rot=(90, 0, 0), centre=True, sides=16, bev=0.01)
    star_r = 0.17
    # sides + back: weathered board-and-batten
    depth = yb - yf
    side_ops = [Op(3.4, 4.3, 1.3, 3.1), Op(8.6, 9.5, 1.3, 3.1), Op(3.4, 4.3, 5.2, 6.9), Op(8.6, 9.5, 5.2, 6.9)]
    for frame, mirror in ((WF(x1, yf, 0, 90), False), (WF(x0, yb, 0, -90), True)):
        with b.at(frame):
            ops2 = [Op(depth - o.u1, depth - o.u0, o.v0, o.v1) for o in side_ops] if mirror else side_ops
            # the paint went on the false front; the sides got whitewash (they face the square, in the evening shade)
            f2 = arch.wall(mb, depth, fz, z_eave, ops2, "bnb", white, tone=SALOON_WASH)
            arch.corner_boards(mb, depth, fz, z_eave, f2, green, cw=0.15)
            arch.water_table(mb, depth, fz, f2, green, h=0.22)
            for k, o in enumerate(ops2):
                arch.window(b, o.u0, o.u1, o.v0, o.v1, face=f2, trim=green, sash=white, panes=(2, 1),
                            cell=[2, 6, 7, 4][k] if k % 2 == 0 else None, head="plain", cw=0.09,
                            shutters=green if k in (0, 3) else None, lod="simple")
            mb.boxc((depth, 0.05, 0.2), white, loc=(depth / 2, f2 - 0.025, z_eave - 0.1), skip="k")
    with b.at(WF(x1, yb, 0, 180)):
        bops = [Op(8.0, 8.95, fz, 2.65), Op(2.5, 3.4, 1.35, 3.05), Op(5.0, 5.9, 5.2, 6.9), Op(2.5, 3.4, 5.2, 6.9)]
        f3 = arch.wall(mb, W, fz, z_eave, bops, "bnb", white, tone=SALOON_WASH)
        arch.water_table(mb, W, fz, f3, green, h=0.22, ops=bops[:1])
        arch.door(b, 8.0, 8.95, fz, 2.65, face=f3, trim=green, leaf="wood_planks", leaves=1, glazed=False, cell=None,
                  transom=0, cw=0.09)
        for o in bops[1:]:
            arch.window(b, o.u0, o.u1, o.v0, o.v1, face=f3, trim=green, sash=white, cell=None, head="plain", cw=0.09,
                        lod="simple")
    mb.boxc((1.4, 0.9, fz - 0.02), "wood_planks", loc=(x1 - 8.475, yb + 0.47, (fz - 0.02) / 2), skip="d", uvoff=True)
    zr = arch.gable_roof(b, x0, x1, yf + 0.18, yb, z_eave, pitch, mat="corrugated", fascia=white,
                         back_gable=("bnb", white, SALOON_WASH))
    _parapet_back(mb, x0, x1, yf + 0.18, z_eave, zr - 0.06, zc - 0.02, roof_pitch=pitch)
    for x in (x0, x1):
        mb.boxc((0.04, 0.22, zc - fz), white, loc=(x + (0.02 if x > 0 else -0.02), yf + 0.09 - 0.02, (zc + fz) / 2), skip="d")
    t = math.tan(math.radians(pitch))
    arch.chimney(mb, 3.6, 6.4, 7.6, 2.4, mat="brick")
    arch.stovepipe(mb, -3.0, 2.0, z_eave + (W / 2 + 0.45 - 3.0) * t - 0.1 + 0.08, h=1.6)
    # porch dressing
    arch.barrel(mb, -4.6, yface - 1.9, fz, tone=0.92)
    arch.barrel(mb, -4.3, yface - 1.4, fz, lying=True, rot=80, tone=0.9)
    arch.bench(mb, 3.9, yface - 0.34, fz, L=1.9)
    b.empties += [("door", (0.0, yface - 0.4, fz), (0, 0, 0))]
    return b.finish()


def general_store(seed=15):
    """Weathered-board general store: stepped false front, shed porch on timber posts piled with
    barrels, sacks, crates and mining tools, hoist beam over the upper loading door."""
    b = B("general_store", seed)
    mb = b.mb
    W, yf, yb = 13.0, -4.0, 9.0
    x0, x1 = -W / 2, W / 2
    fz, z_eave, z_top, pitch = 0.5, 7.7, 9.2, 15
    wood, white, red = "wood_planks", "wood_painted_white", "wood_painted_red"
    sidewood = red  # barn-red board-and-batten on the sides and back (the front is the old weathered siding)
    _foundation(b, x0, x1, yf, yb, fz)
    upper = [(1.6, 2.6), (3.8, 4.8), (8.2, 9.2), (10.4, 11.4)]
    steps = [(3.2, 9.8, z_top, z_top + 0.7), (4.9, 8.1, z_top + 0.7, z_top + 1.35)]

    def outline(z):
        if z <= z_top + 1e-3:
            return (0.0, W)
        for a, c, zlo, zhi in steps:
            if zlo - 1e-3 <= z - 0.0 <= zhi + 1e-3 or (zlo < z <= zhi):
                return (a, c)
        return (W / 2, W / 2)
    ops = [Op(0.8, 5.2, fz, 3.6), Op(7.8, 12.2, fz, 3.6), Op(5.6, 7.4, fz, 3.6)] + [Op(a, c, 5.2, 7.0) for a, c in upper] + \
          [Op(6.0, 7.0, 4.8, 7.1)]
    with b.at(WF(x0, yf, 0, 0)):
        face = arch.wall(mb, W, fz, steps[-1][3], ops, "clap", wood, outline=outline)
        arch.corner_boards(mb, W, fz, z_top, face, white, cw=0.16)
        arch.storefront(b, 0.8, 5.2, fz, face=face, trim=white, panel=red, glass_top=3.0, transom_top=3.6, bulk=0.65, cell=1)
        arch.storefront(b, 7.8, 12.2, fz, face=face, trim=white, panel=red, glass_top=3.0, transom_top=3.6, bulk=0.65, cell=1)
        arch.door(b, 5.6, 7.4, fz, 3.0, face=face, trim=white, leaf=red, leaves=2, glazed=True, cell=1, transom=0.6,
                  open_deg=0, vest_d=2.2)
        for k, (a, c) in enumerate(upper):
            arch.window(b, a, c, 5.2, 7.0, face=face, trim=white, panes=(2, 2), cell=[6, None, 3, None][k],
                        shade=0.35 if k == 2 else 0, head="cap")
        # upper loading door (plank doors, one ajar) + hoist beam
        arch.interior_box(mb, 6.0, 7.0, 4.8, 7.1, 0.1, 1.2, 6, margin=0.05)
        for side in (6.0, 7.0):
            mb.poly([(side, face - 0.03, 4.8), (side, 0.1, 4.8), (side, 0.1, 7.1), (side, face - 0.03, 7.1)], white,
                    facing=(1 if side < 6.5 else -1, 0, 0))
        mb.boxc((1.24, 0.03, 0.12), white, loc=(6.5, face - 0.015, 7.16), skip="k")
        mb.boxc((0.5, 0.05, 2.3), wood, loc=(6.25, -0.06 + 0.05, 5.95), rot=(0, 0, -100), tone=0.8)
        mb.boxc((0.5, 0.05, 2.3), wood, loc=(6.72, 0.02, 5.95), tone=0.85)
        # hoist arm swung back flat against the front (sticking out, it cut through the sign from the street):
        # iron pintle + strap at the door jamb, a timber arm along the wall, pulley block, rope and hook
        mb.boxc((0.1, 0.12, 0.3), "steel_dark", loc=(7.06, face - 0.06, 7.2), bev=0.01)
        mb.boxc((1.02, 0.14, 0.16), "wood_timber", loc=(7.6, face - 0.2, 7.28), bev=0.015)
        mb.boxc((0.5, 0.03, 0.05), "steel_dark", loc=(7.35, face - 0.28, 7.28))
        mb.cyl(0.11, 0.07, "steel_dark", loc=(8.0, face - 0.2, 7.08), rot=(90, 0, 0), centre=True, sides=12)
        mb.boxc((0.05, 0.05, 0.12), "steel_dark", loc=(8.0, face - 0.2, 7.18))
        mb.tube([(8.06, face - 0.2, 7.05), (8.06, face - 0.21, 5.6)], 0.011, "canvas", sides=5)
        mb.tube([(7.94, face - 0.2, 7.05), (7.94, face - 0.2, 6.3)], 0.011, "canvas", sides=5)
        mb.cyl(0.035, 0.1, "steel_dark", loc=(8.06, face - 0.21, 5.5), sides=6)
        mb.tube([(8.06, face - 0.21, 5.5), (8.1, face - 0.21, 5.43), (8.03, face - 0.21, 5.38)], 0.012, "steel_dark",
                sides=5)
        arch.sign_board(b, W / 2, face, 8.05, 8.4, 1.3, "label_general_store", frame=white, body=white)
        # cap trims along the stepped outline
        for a, c, zlo, zhi in [(0.0, W, 0, z_top)] + steps:
            mb.boxc((c - a + 0.12, 0.26, 0.1), white, loc=((a + c) / 2, face - 0.1, zhi + 0.05), bev=0.01)
            mb.boxc((c - a + 0.18, 0.3, 0.04), white, loc=((a + c) / 2, face - 0.1, zhi + 0.12), bev=0.006)
            if zlo > 0:
                for xx in (a, c):
                    mb.boxc((0.14, 0.05, zhi - zlo), white, loc=(xx + (0.07 if xx == a else -0.07), face - 0.04, (zlo + zhi) / 2),
                            skip="k")
        mb.boxc((W, 0.04, 0.3), white, loc=(W / 2, face - 0.02, z_top - 0.15), skip="k")
    yface = yf + face
    # back of the stepped false front
    zt = steps[-1][3]
    pts = [(x0, yf + 0.16, z_eave), (0, yf + 0.16, z_eave + (W / 2 + 0.45) * math.tan(math.radians(pitch)) - 0.1),
           (x1, yf + 0.16, z_eave), (x1, yf + 0.16, z_top), (x0 + steps[0][1], yf + 0.16, z_top),
           (x0 + steps[0][1], yf + 0.16, steps[0][3]), (x0 + steps[1][1], yf + 0.16, steps[0][3]),
           (x0 + steps[1][1], yf + 0.16, zt), (x0 + steps[1][0], yf + 0.16, zt), (x0 + steps[1][0], yf + 0.16, steps[0][3]),
           (x0 + steps[0][0], yf + 0.16, steps[0][3]), (x0 + steps[0][0], yf + 0.16, z_top), (x0, yf + 0.16, z_top)]
    mb.poly(pts, "wood_planks", facing=(0, 1, 0), grain_dir=(0, 0, 1))
    for x in (x0 + 3.0, x1 - 3.0, 0.0):
        mb.span((x, yf + 0.25, zt - 0.3 if x == 0 else z_top - 0.2), (x, yf + 2.4, z_eave + 0.6), 0.09, 0.09, "wood_timber",
                up=(1, 0, 0))
    for x in (x0, x1):
        mb.boxc((0.04, 0.2, z_top + 0.1 - fz), white, loc=(x + (0.02 if x > 0 else -0.02), yf + 0.06, (z_top + 0.1 + fz) / 2),
                skip="d")
    # porch with shed roof on timber posts + fascia sign
    posts = [-6.3, -2.2, 2.2, 6.3]
    arch.porch(b, x0, x1, yface, 2.4, fz, posts, 3.95, roof="shed", post="square", trim=white, post_mat="wood_timber",
               roof_mat="corrugated", rise=0.55, brackets=False)
    for px in posts:
        for sgn in (-1, 1):
            mb.span((px, yface - 2.24, 3.4), (px + sgn * 0.6, yface - 2.24, 3.95), 0.08, 0.08, "wood_timber", up=(0, 1, 0))
    b.lab.panel(9.0, 0.42, "label_store_fascia", loc=(0, yface - 2.4 - 0.09, 3.57))
    mb.boxc((9.12, 0.04, 0.5), "wood_dark", loc=(0, yface - 2.4 - 0.06, 3.78))
    for xx in (-4.2, 4.2):
        mb.span((xx, yface - 2.43, 4.03), (xx, yface - 2.3, 4.2), 0.03, 0.03, "steel_dark")
    # porch goods
    for i, (xx, yy, lying) in enumerate(((-5.8, -0.5, False), (-5.2, -0.45, False), (-5.5, -1.0, False), (-4.4, -0.5, True))):
        arch.barrel(mb, xx, yface + yy, fz, lying=lying, rot=90, tone=0.85 + 0.04 * i)
    arch.crate(mb, 4.6, yface - 0.45, fz, s=(0.8, 0.6, 0.6), rot=4)
    arch.crate(mb, 4.65, yface - 0.45, fz + 0.6, s=(0.6, 0.5, 0.45), rot=-8)
    arch.crate(mb, 5.5, yface - 0.5, fz, s=(0.7, 0.6, 0.5), rot=-12)
    for i in range(5):
        arch.sack(mb, -3.4 + i * 0.42, yface - 0.35 - (i % 2) * 0.12, fz, rot=i * 40, tone=0.5 + 0.04 * (i % 3))
    arch.sack(mb, -3.0, yface - 0.4, fz + 0.5, r=0.22, h=0.5, rot=20, tone=0.56)
    for i, kind in enumerate(("shovel", "pick", "shovel", "pick", "shovel")):
        arch.tool_lean(mb, 2.8 + i * 0.28, yface - 0.12, fz, kind=kind, rot=0, lean=-12)
    arch.bench(mb, 1.0, yface - 0.34, fz, L=1.5)
    mb.lathe([(0.32, 0), (0.36, 0.05), (0.38, 0.3), (0.36, 0.32)], "galvanized", loc=(-1.6, yface - 0.6, fz), sides=14,
             cap_top=False)
    # sides + back
    depth = yb - yf
    side_ops = [Op(3.0, 3.9, 1.4, 3.1), Op(7.5, 8.4, 1.4, 3.1), Op(11.0, 11.9, 1.4, 3.1), Op(4.0, 4.9, 5.2, 6.8),
                Op(9.0, 9.9, 5.2, 6.8)]
    for frame, mirror in ((WF(x1, yf, 0, 90), False), (WF(x0, yb, 0, -90), True)):
        with b.at(frame):
            ops2 = [Op(depth - o.u1, depth - o.u0, o.v0, o.v1) for o in side_ops] if mirror else side_ops
            f2 = arch.wall(mb, depth, fz, z_eave, ops2, "bnb", sidewood, tone=0.5)
            arch.corner_boards(mb, depth, fz, z_eave, f2, white, cw=0.14)
            arch.water_table(mb, depth, fz, f2, white, h=0.22)
            for k, o in enumerate(ops2):
                arch.window(b, o.u0, o.u1, o.v0, o.v1, face=f2, trim=white, sash=white, panes=(2, 1),
                            cell=[1, 6, 3, 4, 6][k] if k % 2 == 0 else None, head="plain", cw=0.09, lod="simple")
            mb.boxc((depth, 0.05, 0.2), white, loc=(depth / 2, f2 - 0.025, z_eave - 0.1), skip="k")
    with b.at(WF(x1, yb, 0, 180)):
        bops = [Op(4.0, 6.2, fz, 3.0), Op(9.0, 9.9, 1.4, 3.1), Op(2.0, 2.9, 5.2, 6.8), Op(9.0, 9.9, 5.2, 6.8)]
        f3 = arch.wall(mb, W, fz, z_eave, bops, "bnb", sidewood, tone=0.5)
        arch.water_table(mb, W, fz, f3, white, h=0.22, ops=bops[:1])
        arch.door(b, 4.0, 6.2, fz, 3.0, face=f3, trim=white, leaf=wood, leaves=2, glazed=False, cell=None, transom=0, cw=0.1)
        for o in bops[1:]:
            arch.window(b, o.u0, o.u1, o.v0, o.v1, face=f3, trim=white, sash=white, cell=None, head="plain", cw=0.09,
                        lod="simple")
    mb.boxc((3.0, 1.6, fz - 0.02), "wood_planks", loc=(x1 - 5.1, yb + 0.8, (fz - 0.02) / 2), skip="d", uvoff=True)
    zr = arch.gable_roof(b, x0, x1, yf + 0.16, yb, z_eave, pitch, mat="corrugated", fascia=white,
                         back_gable=("bnb", sidewood, 0.5))
    t = math.tan(math.radians(pitch))
    arch.stovepipe(mb, 3.2, 3.0, z_eave + (W / 2 + 0.45 - 3.2) * t - 0.1 + 0.08, h=1.7, mat="rust")
    arch.stovepipe(mb, -2.4, 6.5, z_eave + (W / 2 + 0.45 - 2.4) * t - 0.1 + 0.08, h=1.4)
    b.empties += [("door", (0.0, yface - 0.4, fz), (0, 0, 0))]
    return b.finish()


def _iron_shutter(mb, uc, sw, z0, z1, hinge, side, y=-0.095, paint="paint_green"):
    """Fireproof iron shutter folded back against a brick front: painted plate, riveted rim and mid rib, two
    strap hinges on pintles leaded into the brick."""
    h = z1 - z0
    zc = (z0 + z1) / 2
    tn = mb.tone(0.85, 1.0)
    mb.boxc((sw, 0.03, h), paint, loc=(uc, y, zc), bev=0.004, tone=tn)
    yr = y - 0.015 - 0.006
    for zz in (z0 + 0.025, z1 - 0.025, zc):
        mb.boxc((sw, 0.012, 0.045), paint, loc=(uc, yr, zz), skip="k", tone=tn)
    for uu in (uc - sw / 2 + 0.0225, uc + sw / 2 - 0.0225):
        mb.boxc((0.045, 0.012, h - 0.09), paint, loc=(uu, yr, zc), skip="k", tone=tn)
        n = int((h - 0.2) / 0.28)
        for k in range(n + 1):
            mb.cyl(0.011, 0.012, "steel_dark", loc=(uu, yr - 0.006, z0 + 0.1 + (h - 0.2) * k / n), rot=(90, 0, 0),
                   sides=6, centre=True, cap_bot=False)
    for zz in (z0 + 0.36, z1 - 0.36):
        L = sw * 0.78
        sx = hinge + (-L / 2 if side < 0 else L / 2)
        mb.boxc((L, 0.014, 0.055), "steel_dark", loc=(sx, yr - 0.007, zz), skip="k")
        mb.cyl(0.04, 0.014, "steel_dark", loc=(hinge + (-L if side < 0 else L), yr - 0.007, zz), rot=(90, 0, 0), sides=10,
               centre=True)
        mb.cyl(0.022, 0.13, "cast_iron", loc=(hinge, -0.05, zz - 0.065), sides=6)


def assay_office(seed=17):
    """Brick assay office: corbelled cornice + stone cap, arched window heads with iron shutters,
    iron double doors, cantilevered awning on tie rods, hanging GOLD BOUGHT blade sign."""
    b = B("assay_office", seed)
    mb = b.mb
    W, yf, yb = 9.0, -4.0, 6.0
    x0, x1 = -W / 2, W / 2
    fz, z_roof, z_par = 0.55, 7.7, 9.0
    brick, stone, iron = "brick", "concrete", "steel_dark"
    green = "wood_painted_green"
    mb.boxc((W + 0.1, yb - yf + 0.06, fz), stone, loc=(0, (yf + yb) / 2 + 0.03, fz / 2), skip="d")
    ground = [(0.9, 2.2), (6.8, 8.1)]
    upper = [(1.15, 2.15), (4.0, 5.0), (6.85, 7.85)]
    ops = [Op(3.7, 5.3, fz, 3.55)] + [Op(a, c, 1.05, 3.25) for a, c in ground] + [Op(a, c, 5.0, 6.8) for a, c in upper]
    with b.at(WF(x0, yf, 0, 0)):
        arch.flat_wall(mb, W, fz, z_par, ops, brick)
        face = 0.0
        # pilasters
        for u in (0.25, W - 0.25):
            mb.boxc((0.5, 0.1, z_par - fz), brick, loc=(u, -0.05, (fz + z_par) / 2), skip="k")
            mb.boxc((0.62, 0.16, 0.3), stone, loc=(u, -0.08, fz + 0.15), bev=0.01)
        mb.boxc((W, 0.06, 0.18), stone, loc=(W / 2, -0.03, 4.35), skip="k", bev=0.008)
        for a, c in ground:
            arch.window(b, a, c, 1.05, 3.25, face=0.0, trim=stone, sash=green, panes=(2, 2), cell=0, cw=0.0, head="none",
                        sill=True, apron=False, reveal=brick)
            arch.brick_arch(mb, (a + c) / 2, c - a, 3.25, 0.0, rise=0.24)
            sw = (c - a) / 2 + 0.02
            for side in (-1, 1):
                ux = a - sw / 2 - 0.06 if side < 0 else c + sw / 2 + 0.06
                _iron_shutter(mb, ux, sw, 1.025, 3.275, hinge=a - 0.06 if side < 0 else c + 0.06, side=side)
        for a, c in upper:
            arch.window(b, a, c, 5.0, 6.8, face=0.0, trim=stone, sash=green, panes=(2, 2), cell=[3, 0, 4][upper.index((a, c))],
                        cw=0.0, head="none", sill=True, apron=False, reveal=brick, shade=0.25)
            arch.brick_arch(mb, (a + c) / 2, c - a, 6.8, 0.0, rise=0.2)
        arch.door(b, 3.7, 5.3, fz, 3.0, face=0.0, trim=iron, leaf=iron, leaves=2, glazed=True, cell=0, transom=0.55,
                  transom_label=LABEL_GLASS_BOT, open_deg=58, vest_d=2.2, cw=0.08)
        arch.brick_arch(mb, W / 2, 1.6, 3.55, 0.0, rise=0.22)
        arch.sign_board(b, W / 2, -0.1, 7.75, 6.4, 1.0, "label_assay_office", frame="wood_painted_white", body="paint_black")
        # corbelled cornice + stone cap
        for k in range(4):
            mb.boxc((W + 0.04 * k, 0.1 + 0.07 * k, 0.15), brick, loc=(W / 2, -(0.05 + 0.035 * k), z_par - 0.6 + k * 0.15),
                    skip="k")
        for i in range(17):
            u = 0.4 + i * (W - 0.8) / 16
            mb.boxc((0.11, 0.16, 0.18), brick, loc=(u, -0.14, z_par - 0.78), skip="k")
        mb.boxc((W + 0.3, 0.55, 0.14), stone, loc=(W / 2, -0.12, z_par + 0.07), bev=0.012)
        mb.boxc((1.6, 0.4, 0.5), brick, loc=(W / 2, -0.05, z_par + 0.39), skip="k")
        mb.boxc((1.8, 0.5, 0.12), stone, loc=(W / 2, -0.07, z_par + 0.7), bev=0.01)
    yface = yf
    # boardwalk + steps (no posts: a cantilevered awning)
    arch.deck(mb, x0, x1, yf - 2.4, yf - 0.02, fz)
    mb.boxc((W + 0.04, 0.05, 0.22), arch.DECK, loc=(0, yf - 2.42, fz - 0.155), skip="k", uvoff=True)
    mb.boxc((W, 0.03, fz - 0.27), arch.DECK, loc=(0, yf - 2.38, (fz - 0.27) / 2), skip="k", grain=2, tone=0.8)
    for sx in (x0, x1):
        mb.boxc((0.03, 2.4, fz - 0.05), arch.DECK, loc=(sx, yf - 1.2, (fz - 0.05) / 2), grain=2, tone=0.8)
    for k in range(2):
        zt = fz * (k + 1) / 3
        yy = yf - 2.4 - 0.3 * (2 - k)
        arch.treads(mb, -W / 2 + 0.1, W / 2 - 0.1, yy, yy + 0.32, zt)
        mb.boxc((W - 0.2, 0.03, zt - 0.045), arch.DECK, loc=(0, yy + 0.04, (zt - 0.045) / 2), skip="k", tone=0.85)
    za = 3.9
    mb.poly([(x0 + 0.1, yf - 2.3, za - 0.35), (x1 - 0.1, yf - 2.3, za - 0.35), (x1 - 0.1, yf - 0.01, za), (x0 + 0.1, yf - 0.01, za)],
            "corrugated", thick=0.04, facing=(0, -0.3, 1))
    mb.boxc((W - 0.2, 0.04, 0.22), "paint_black", loc=(0, yf - 2.32, za - 0.42), skip="")
    for xx in (x0 + 0.4, -1.6, 1.6, x1 - 0.4):
        mb.span((xx, yf - 0.05, za + 1.2), (xx, yf - 2.25, za - 0.36), 0.025, 0.025, "cast_iron")
        mb.boxc((0.12, 0.04, 0.16), "cast_iron", loc=(xx, yf - 0.02, za + 1.2))
    # hanging blade sign
    bx = -2.6
    mb.span((bx, yf - 0.05, 4.55), (bx, yf - 1.55, 4.55), 0.05, 0.05, "cast_iron")
    mb.span((bx, yf - 0.05, 4.05), (bx, yf - 1.0, 4.55), 0.03, 0.03, "cast_iron")
    mb.boxc((0.14, 0.04, 0.2), "cast_iron", loc=(bx, yf - 0.02, 4.45))
    for yy in (yf - 0.3, yf - 1.35):
        mb.span((bx, yy, 4.53), (bx, yy, 4.31), 0.012, 0.012, "cast_iron")
    mb.boxc((0.05, 1.2, 0.62), "paint_black", loc=(bx, yf - 0.83, 4.0), bev=0.006)
    with b.lab.at(M=T((bx, yf - 0.83, 3.69)) @ arch.Rz(90)):
        b.lab.panel(1.14, 0.57, "label_gold_bought", loc=(0, -0.027, 0.025))
    with b.lab.at(M=T((bx, yf - 0.83, 3.69)) @ arch.Rz(-90)):
        b.lab.panel(1.14, 0.57, "label_gold_bought", loc=(0, -0.027, 0.025))
    # side + back walls (brick, stepped side parapets)
    depth = yb - yf
    side_ops = [Op(3.0, 3.9, 1.3, 3.0), Op(6.5, 7.4, 1.3, 3.0), Op(3.0, 3.9, 5.0, 6.6), Op(6.5, 7.4, 5.0, 6.6)]
    for frame, mirror in ((WF(x1, yf, 0, 90), False), (WF(x0, yb, 0, -90), True)):
        with b.at(frame):
            ops2 = [Op(depth - o.u1, depth - o.u0, o.v0, o.v1) for o in side_ops] if mirror else side_ops

            def outline(z, m=mirror):
                if z <= z_roof + 0.6:
                    return (0.0, depth)
                return (depth - 4.0, depth) if m else (0.0, 4.0)
            arch.flat_wall(mb, depth, fz, z_par, ops2, brick, outline=outline)
            for o in ops2:
                arch.window(b, o.u0, o.u1, o.v0, o.v1, face=0.0, trim=stone, sash=green, panes=(1, 2), cell=None,
                            cw=0.0, head="none", apron=False, reveal=brick)
                arch.brick_arch(mb, (o.u0 + o.u1) / 2, o.u1 - o.u0, o.v1, 0.0, rise=0.16)
            a, c = (depth - 4.0, depth) if mirror else (0.0, 4.0)
            mb.boxc((c - a, 0.38, 0.1), stone, loc=((a + c) / 2, 0.1, z_par + 0.05), bev=0.008)
            a2, c2 = (0.0, depth - 4.0) if mirror else (4.0, depth)
            mb.boxc((c2 - a2, 0.38, 0.1), stone, loc=((a2 + c2) / 2, 0.1, z_roof + 0.65), bev=0.008)
    with b.at(WF(x1, yb, 0, 180)):
        bops = [Op(3.8, 5.0, fz, 2.8), Op(1.2, 2.1, 5.0, 6.6), Op(6.9, 7.8, 5.0, 6.6)]
        arch.flat_wall(mb, W, fz, z_roof + 0.6, bops, brick)
        arch.door(b, 3.8, 5.0, fz, 2.8, face=0.0, trim=iron, leaf=iron, leaves=1, glazed=False, cell=None, transom=0, cw=0.06)
        for o in bops[1:]:
            arch.window(b, o.u0, o.u1, o.v0, o.v1, face=0.0, trim=stone, sash=green, cell=None, cw=0.0, head="none",
                        apron=False, reveal=brick)
        mb.boxc((W, 0.38, 0.1), stone, loc=(W / 2, 0.1, z_roof + 0.65), bev=0.008)
    # flat roof (hidden behind parapets), chimney, roof hatch
    mb.poly([(x0, yf + 0.2, z_roof), (x1, yf + 0.2, z_roof), (x1, yb, z_roof - 0.1), (x0, yb, z_roof - 0.1)], "concrete",
            facing=(0, 0, 1))
    mb.poly([(x0 + 0.02, yf + 0.25, z_par), (x1 - 0.02, yf + 0.25, z_par), (x1 - 0.02, yf + 0.25, z_roof),
             (x0 + 0.02, yf + 0.25, z_roof)], brick, facing=(0, 1, 0))
    arch.chimney(mb, 2.8, 4.2, z_roof - 0.1, 1.9, mat="brick")
    arch.chimney(mb, -2.6, 1.5, z_roof, 1.6, mat="brick", w=0.5, d=0.5)
    mb.boxc((0.9, 0.9, 0.35), "wood_planks", loc=(-1.0, 3.5, z_roof + 0.17))
    b.empties += [("door", (0.0, yf - 0.4, fz), (0, 0, 0))]
    return b.finish()
