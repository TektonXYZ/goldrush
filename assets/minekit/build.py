"""Build public/models/mine-kit.glb (every node listed under "Mine kit" in docs/CONTRACTS.md).

    systemd-run --user --scope -q -p MemoryMax=3G -p MemorySwapMax=0 \
        bl assets/minekit/build.py -- [--only a,b] [--nobake] [--glb path] [--blend path]

Without --only: builds everything, exports public/models/mine-kit.glb, saves build/minekit.blend and
build/stats.json (sizes/tris/children for NODES.md).
"""
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import mk  # noqa: E402
from mk import MB, child, descendants, empty, tree_bounds, tree_tris  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))

NODES = """timber_set steel_arch bolt_plate mesh_panel rail_2m rail_bumper ore_cart lantern bulb_cage cable_2m
vent_duct_2m pipe_2m generator fuel_tank desk office_chair monitor pc_tower keyboard desk_lamp tool_rack lockers
first_aid phone_box map_board ore_bin elevator_cage shaft_frame call_panel shoring_1 shoring_2 shoring_3 shoring_4
rubble_wall explosives_crate detonator barrel crate pallet sign_danger sign_exit sign_level fan_unit light_stand
wheelbarrow helmet_rack stretcher water_tank""".split()
EXTRA = ["shaft_frame_landing"]  # helpful extras beyond the contract (documented in NODES.md)

# children the game looks up by name (Blender appends .001 to repeats; the GLB is patched back to these)
CHILD_NAMES = {"bulb", "screen", "board_face", "fill", "gate", "cage_light", "panel_screen", "btn_1", "btn_2",
               "btn_3", "btn_4", "face", "blades", "status_light", "gauge_needle", "exhaust", "snd", "ballast",
               "wheel_0", "wheel_1", "wheel_2", "wheel_3", "gauge_mount"}

# ---------------------------------------------------------------- blockouts (until a real builder exists)
# kind, size (Blender x, y, z), material, children [(name, kind, loc, mat)]
W = "wall"
BLOCK = {
    "bolt_plate": (W, (0.16, 0.09, 0.16), "steel_dark", []),
    "mesh_panel": (W, (2.0, 0.03, 2.0), "galvanized", []),
    "rail_bumper": ("floor", (0.9, 0.5, 0.8), "paint_yellow", []),
    "ore_cart": ("floor", (0.95, 1.75, 1.2), "paint_red",
                 [(f"wheel_{i}", "mesh", (x, y, 0.15), "steel") for i, (x, y) in
                  enumerate(((-0.32, -0.5), (0.32, -0.5), (-0.32, 0.5), (0.32, 0.5)))]),
    "lantern": ("hang", (0.22, 0.22, 0.6), "steel_dark", [("bulb", "mesh", (0, 0, -0.42), "emit_warm")]),
    "bulb_cage": ("hang", (0.14, 0.14, 0.6), "steel_dark", []),
    "cable_2m": ("tunnel", (0.1, 2.0, 0.1), "cable", []),
    "vent_duct_2m": ("tunnel", (0.8, 2.0, 0.8), "hose_yellow", []),
    "pipe_2m": ("tunnel", (0.3, 2.0, 0.3), "steel", []),
    "generator": ("floor", (3.6, 1.5, 2.0), "paint_yellow",
                  [("status_light", "mesh", (1.0, -0.76, 1.5), "emit_green"), ("exhaust", "empty", (-1.0, 0, 2.4), None),
                   ("snd", "empty", (0, 0, 1.0), None)]),
    "fuel_tank": ("floor", (2.2, 1.1, 1.45), "paint_green", [("gauge_needle", "mesh", (0, -0.57, 1.0), "paint_black")]),
    "desk": ("floor", (1.6, 0.8, 0.76), "wood_dark", []),
    "office_chair": ("floor", (0.66, 0.66, 1.05), "plastic_black", []),
    "monitor": ("floor", (0.6, 0.24, 0.5), "plastic_black", [("screen", "mesh", (0, -0.05, 0.3), "emit_screen")]),
    "pc_tower": ("floor", (0.22, 0.48, 0.46), "paint_black", []),
    "keyboard": ("floor", (0.46, 0.17, 0.035), "plastic_black", []),
    "desk_lamp": ("floor", (0.2, 0.4, 0.5), "paint_black", [("bulb", "mesh", (0, -0.25, 0.4), "emit_warm")]),
    "tool_rack": (W, (1.4, 0.25, 1.4), "wood_planks", []),
    "lockers": ("floor", (1.2, 0.5, 1.85), "paint_grey", []),
    "first_aid": (W, (0.42, 0.16, 0.5), "paint_green", []),
    "phone_box": (W, (0.34, 0.2, 0.5), "paint_yellow", []),
    "map_board": (W, (1.6, 0.06, 1.1), "wood_dark", [("board_face", "mesh", (0, -0.065, 0), "sign_face")]),
    "ore_bin": ("floor", (1.4, 1.3, 1.6), "steel_dark", [("fill", "mesh", (0, 0, 0.9), "coal_ore")]),
    "elevator_cage": ("floor", (2.4, 2.4, 3.0), "steel_dark",
                      [("gate", "mesh", (0, -1.2, 0.2), "galvanized"), ("cage_light", "mesh", (0, 0, 2.5), "emit_warm")]),
    "shaft_frame": ("floor", (3.4, 3.4, 4.0), "wood_timber", []),
    "call_panel": (W, (0.36, 0.16, 0.52), "paint_yellow",
                   [(f"btn_{i}", "mesh", (0, -0.17, 0.1 - 0.09 * (i - 1)), "paint_green") for i in range(1, 5)] +
                   [("panel_screen", "mesh", (0, -0.17, 0.2), "emit_screen")]),
    "shoring_1": ("floor", (7.0, 9.0, 4.5), "wood_timber", []),
    "shoring_2": ("floor", (7.0, 9.0, 4.5), "steel_dark", []),
    "shoring_3": ("floor", (7.0, 9.0, 4.5), "galvanized", []),
    "shoring_4": ("floor", (10.0, 12.0, 6.5), "steel_dark", []),
    "rubble_wall": ("floor", (4.4, 2.5, 3.8), "rock", []),
    "explosives_crate": ("floor", (0.6, 0.4, 0.36), "wood_planks", []),
    "detonator": ("floor", (0.3, 0.22, 0.45), "wood_dark", []),
    "barrel": ("floor", (0.6, 0.6, 0.88), "paint_blue", []),
    "crate": ("floor", (1.0, 0.8, 0.75), "wood_planks", []),
    "pallet": ("floor", (1.2, 0.8, 0.144), "wood_planks", []),
    "sign_danger": (W, (0.6, 0.03, 0.45), "paint_yellow", []),
    "sign_exit": (W, (0.5, 0.06, 0.25), "paint_green", []),
    "sign_level": (W, (0.9, 0.04, 0.5), "paint_black", [("face", "mesh", (0, -0.045, 0), "sign_face")]),
    "fan_unit": ("floor", (0.9, 1.4, 1.1), "paint_yellow", [("blades", "mesh", (0, -0.6, 0.55), "steel")]),
    "light_stand": ("floor", (0.9, 0.9, 2.2), "paint_yellow", [("bulb", "mesh", (0, -0.1, 2.0), "emit_warm")]),
    "wheelbarrow": ("floor", (0.65, 1.5, 0.65), "paint_green", []),
    "helmet_rack": (W, (1.0, 0.3, 0.5), "wood_planks", []),
    "stretcher": ("floor", (0.6, 2.1, 0.18), "canvas", []),
    "water_tank": ("floor", (0.9, 0.9, 1.6), "plastic_yellow", []),
}


def blockout(name):
    kind, (sx, sy, sz), mat, kids = BLOCK[name]
    mb = MB(name)
    if kind == "wall":
        mb.box((sx, sy, sz), mat, loc=(0, -sy / 2, -sz / 2), bevel=0.01)
    elif kind == "hang":
        mb.box((sx, sy, sz), mat, loc=(0, 0, -sz), bevel=0.01)
    else:
        mb.box((sx, sy, sz), mat, bevel=0.01)
    root = mb.finish()
    for cname, ck, loc, cmat in kids:
        if ck == "empty":
            empty(cname, loc, parent=root)
        else:
            cb = MB(cname)
            cb.box((0.08, 0.02, 0.08), cmat, center=True)
            o = cb.finish(grime=False)
            child(o, root, loc)
    return root, dict(kind=kind, blockout=True)


# ---------------------------------------------------------------- builders
def load_builders():
    import importlib
    B = {}
    for modname in ("p_tunnel", "p_power", "p_office", "p_shaft", "p_shoring", "p_props"):
        path = os.path.join(HERE, modname + ".py")
        if not os.path.exists(path):
            continue
        mod = importlib.import_module(modname)
        B.update(mod.BUILD)
    return B


def b2t(v):
    """Blender (x, y, z) -> three.js (x, y, z)."""
    return [round(v[0], 3), round(v[2], 3), round(-v[1], 3)]


def layout_positions(items, row_w=34.0, gap=1.6):
    """Shelf-pack the nodes (by their bounds) on the XY plane; returns {name: offset}."""
    pos = {}
    x = y = 0.0
    row_d = 0.0
    for name, (lo, hi) in items:
        w = hi.x - lo.x
        d = hi.y - lo.y
        if x + w > row_w and x > 0:
            x = 0.0
            y -= row_d + gap
            row_d = 0.0
        pos[name] = Vector((x - lo.x, y - hi.y, 0))
        x += w + gap
        row_d = max(row_d, d)
    return pos


def plane(name, center, size, normal="z"):
    import bmesh
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    sx, sy = size
    if normal == "z":
        pts = [(-sx / 2, -sy / 2, 0), (sx / 2, -sy / 2, 0), (sx / 2, sy / 2, 0), (-sx / 2, sy / 2, 0)]
    elif normal == "y":  # vertical, in XZ
        pts = [(-sx / 2, 0, -sy / 2), (sx / 2, 0, -sy / 2), (sx / 2, 0, sy / 2), (-sx / 2, 0, sy / 2)]
    else:  # x: vertical in YZ
        pts = [(0, -sx / 2, -sy / 2), (0, sx / 2, -sy / 2), (0, sx / 2, sy / 2), (0, -sx / 2, sy / 2)]
    bm.faces.new([bm.verts.new(p) for p in pts])
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    o.location = center
    me.materials.append(mk.M("concrete"))
    return o


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    only = None
    bake = True
    glb = os.path.join(ROOT, "public", "models", "mine-kit.glb")
    blend = os.path.join(HERE, "build", "minekit.blend")
    stats_path = os.path.join(HERE, "build", "stats.json")
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--only":
            only = argv[i + 1].split(",")
            i += 1
        elif a == "--nobake":
            bake = False
        elif a == "--glb":
            glb = argv[i + 1]
            i += 1
        elif a == "--blend":
            blend = argv[i + 1]
            i += 1
        i += 1
    if only:
        if "--glb" not in argv:
            glb = os.path.join(HERE, "build", "partial.glb")
        if "--blend" not in argv:
            blend = os.path.join(HERE, "build", "partial.blend")
        stats_path = os.path.join(HERE, "build", "partial_stats.json")

    t0 = time.time()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scn = bpy.context.scene
    scn.unit_settings.system = "METRIC"
    B = load_builders()
    names = only or (NODES + [e for e in EXTRA if e in B])
    roots, metas = {}, {}
    for name in names:
        t1 = time.time()
        if name in B:
            fn, meta = B[name]
            res = fn()
            root = res[0] if isinstance(res, tuple) else res
            if isinstance(res, tuple):
                meta = dict(meta, **res[1])
        else:
            root, meta = blockout(name)
        root.name = name
        roots[name] = root
        metas[name] = meta
        print(f"[minekit] {name:18s} {tree_tris(root):6d} tris  {time.time() - t1:5.2f}s"
              f"{'  (blockout)' if meta.get('blockout') else ''}")

    # ---------------------------------------------------------- grime bake (isolated layout)
    if bake:
        bpy.context.view_layer.update()
        items = [(n, tree_bounds(roots[n])) for n in names]
        pos = layout_positions(items)
        occ = []
        lifts = {}
        for n in names:
            r = roots[n]
            kind = metas[n]["kind"]
            lo, hi = tree_bounds(r)
            lift = 0.0
            if kind == "wall":
                lift = -lo.z + 0.35
                c = pos[n] + Vector(((lo.x + hi.x) / 2, 0.004, lift + (lo.z + hi.z) / 2))
                occ.append(plane(f"_occ_{n}", c, (hi.x - lo.x + 0.5, hi.z - lo.z + 0.5), "y"))
            elif kind == "hang":
                lift = -lo.z + 0.4
                c = pos[n] + Vector((0, 0, lift + 0.003))
                occ.append(plane(f"_occ_{n}", c, (0.6, 0.6), "z"))
            for (pc, ps, pn) in metas[n].get("occ", []):
                occ.append(plane(f"_occ_{n}_{len(occ)}", pos[n] + Vector(pc) + Vector((0, 0, lift)), ps, pn))
            lifts[n] = lift
            r.location = pos[n] + Vector((0, 0, lift))
        # one big floor
        lo_all = Vector((min(p.x for p in pos.values()) - 20, min(p.y for p in pos.values()) - 20, 0))
        occ.append(plane("_occ_floor", (0, 0, -0.001), (400, 400), "z"))
        bpy.context.view_layer.update()
        objs = []
        for n in names:
            for o in [roots[n]] + descendants(roots[n]):
                if o.type == "MESH" and o.data.color_attributes.get("Col") is not None:
                    objs.append(o)
        t1 = time.time()
        mk.bake_ao(objs, distance=0.42, samples=96)
        print(f"[minekit] AO bake {len(objs)} meshes {time.time() - t1:.1f}s")
        for n in names:
            kind = metas[n]["kind"]
            for o in [roots[n]] + descendants(roots[n]):
                if o.type == "MESH" and o.data.color_attributes.get("Col") is not None:
                    g = metas[n].get("grime", {})
                    mk.grime_post(o, origin_z=lifts[n], floor=kind in ("floor", "tunnel") and g.get("floor", True),
                                  streaks=g.get("streaks", 0.0), strength=g.get("strength", 1.0),
                                  seed=len(n), ao_floor=g.get("ao_floor", 0.34), dirt=g.get("dirt", 0.22))
        for o in occ:
            bpy.data.objects.remove(o, do_unlink=True)
        for n in names:
            roots[n].location = (0, 0, 0)
        bpy.context.view_layer.update()

    # ---------------------------------------------------------- export
    rl = [roots[n] for n in names]
    mk.export_glb(glb, rl)

    def fix(nm):
        m = re.match(r"^(.*)\.\d{3}$", nm)
        if m and m.group(1) in CHILD_NAMES:
            return m.group(1)
        return nm
    changed, js = mk.patch_glb_names(glb, fix)
    print(f"[minekit] exported {glb} ({os.path.getsize(glb) / 1024:.0f} KB), renamed {changed} nodes")

    # ---------------------------------------------------------- stats
    stats = {}
    for n in names:
        r = roots[n]
        lo, hi = tree_bounds(r)
        kids = []
        for c in descendants(r):
            mw = c.matrix_world
            kids.append({"name": re.sub(r"\.\d{3}$", "", c.name), "type": c.type.lower(),
                         "pos": b2t(mw.translation), "tris": tree_tris(c) if c.type == "MESH" else 0,
                         "mats": [m.name for m in c.data.materials] if c.type == "MESH" else []})
        mats = sorted({m.name for o in [r] + descendants(r) if o.type == "MESH" for m in o.data.materials})
        tlo, thi = b2t(lo), b2t(hi)
        stats[n] = {"kind": metas[n]["kind"], "blockout": bool(metas[n].get("blockout")),
                    "tris": tree_tris(r), "min": [tlo[0], tlo[1], thi[2]], "max": [thi[0], thi[1], tlo[2]],
                    "size": [round(hi.x - lo.x, 3), round(hi.z - lo.z, 3), round(hi.y - lo.y, 3)],
                    "children": kids, "materials": mats, "notes": metas[n].get("notes", "")}
    json.dump(stats, open(stats_path, "w"), indent=1)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=blend)
    tot = sum(s["tris"] for s in stats.values())
    print(f"[minekit] done: {len(names)} nodes, {tot} tris, {time.time() - t0:.1f}s -> {blend}")


main()
