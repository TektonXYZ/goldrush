"""Build town.glb (every node in docs/CONTRACTS.md), bake grime, export, render previews.

    bl assets/town/build.py -- [--only a,b,c] [--out path.glb] [--preview all|none|a,b] [--nobake] [--blend]

Full build (no --only) writes public/models/town.glb; partial builds go to assets/town/out/partial.glb.
"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import bpy  # noqa: E402

import tk  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
LABELS = {
    "label_land_office": ("label_land_office.jpg", False),
    "label_land_fascia": ("label_land_fascia.jpg", False),
    "label_claims_board": ("label_claims_board.jpg", False),
    "label_assay_office": ("label_assay_office.jpg", False),
    "label_gold_bought": ("label_gold_bought.jpg", False),
    "label_general_store": ("label_general_store.jpg", False),
    "label_store_fascia": ("label_store_fascia.jpg", False),
    "label_saloon": ("label_saloon.jpg", False),
    "label_station": ("label_station.jpg", False),
    "label_depot_small": ("label_depot_small.jpg", False),
    "label_gas": ("label_gas.jpg", False),
    "label_plaque": ("label_plaque.jpg", False),
    "label_train": ("label_train.png", True),
    "label_glass": ("label_glass.png", True),
}


def materials():
    for name, (f, alpha) in LABELS.items():
        tk.label_mat(name, f, alpha=alpha, rough=0.7 if not alpha else 0.45)
    tk.label_mat("custom_interior", "custom_interior.jpg", emissive=1.4)
    tk.custom_mat("custom_bronze", "#6b5232", rough=0.42, metal=1.0)


def registry():
    import buildings
    reg = {"land_office": buildings.land_office}
    for modname in ("depot", "rail", "gas", "monument", "props"):
        try:
            mod = __import__(modname)
        except ImportError:
            continue
        reg.update(getattr(mod, "NODES", {}))
    for name in ("assay_office", "general_store", "saloon"):
        if hasattr(buildings, name):
            reg[name] = getattr(buildings, name)
    return reg


ORDER = ["land_office", "depot", "track_10m", "locomotive", "coach", "saloon", "general_store", "assay_office",
         "gas_station", "monument", "water_tower", "windmill", "telegraph_pole", "wagon", "bench", "street_lamp",
         "boardwalk_4m", "barrels", "hitching_post", "boxcar", "buffer_stop"]
BAKE = {  # AO distance per node (metres), floor offset for rolling stock
    "locomotive": (0.6, None), "coach": (0.7, None), "boxcar": (0.7, None), "track_10m": (0.4, None),
}


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []

    def opt(k, d=None):
        return argv[argv.index(k) + 1] if k in argv else d
    only = opt("--only")
    preview = opt("--preview", "all")
    out = opt("--out")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    materials()
    reg = registry()
    names = [n for n in ORDER if n in reg] if not only else only.split(",")
    missing = [n for n in ORDER if n not in reg]
    roots = {}
    for n in names:
        t0 = time.time()
        r = reg[n]()
        r.name = n
        roots[n] = r
        coll = bpy.data.collections.new("N_" + n)
        sc.collection.children.link(coll)
        for o in [r] + list(r.children_recursive):
            for c in list(o.users_collection):
                c.objects.unlink(o)
            coll.objects.link(o)
        print(f"[town] built {n}: {tk.tri_count(r)} tris in {time.time() - t0:.1f}s")
    if "--nobake" not in argv:
        # spread the nodes out so they don't occlude each other while baking
        for i, (n, r) in enumerate(roots.items()):
            r.location = ((i % 6) * 60.0, (i // 6) * 60.0, 0)
        bpy.context.view_layer.update()
        for n, r in roots.items():
            t0 = time.time()
            dist, floor = BAKE.get(n, (1.2, None))
            tk.bake_grime(r, distance=dist, samples=40, floor_z=0.0)
            print(f"[town] baked {n} in {time.time() - t0:.1f}s")
        for r in roots.values():
            r.location = (0, 0, 0)
        bpy.context.view_layer.update()
    if out is None:
        out = os.path.join(ROOT, "public/models/town.glb") if not only else os.path.join(HERE, "out/partial.glb")
    tk.export(out, list(roots.values()))
    print("[town] NODE SUMMARY")
    for n, r in roots.items():
        lo, hi = tk.bounds(r)
        print(f"  {n:16s} {tk.tri_count(r):6d} tris  W {hi.x - lo.x:6.2f}  D {hi.y - lo.y:6.2f}  H {hi.z - lo.z:6.2f}"
              f"  x[{lo.x:.2f},{hi.x:.2f}] y[{lo.y:.2f},{hi.y:.2f}] z[{lo.z:.2f},{hi.z:.2f}]"
              f"  children: {', '.join(sorted(c.name for c in r.children))}")
    if "--stats" in argv:
        dg = bpy.context.evaluated_depsgraph_get()
        for n, r in roots.items():
            per = {}
            for o in [r] + list(r.children_recursive):
                if o.type != "MESH":
                    continue
                ev = o.evaluated_get(dg)
                me = ev.to_mesh()
                for p in me.polygons:
                    m = me.materials[p.material_index].name if me.materials else "?"
                    per[m] = per.get(m, 0) + len(p.vertices) - 2
                ev.to_mesh_clear()
            top = sorted(per.items(), key=lambda kv: -kv[1])[:8]
            print(f"  {n:16s} " + "  ".join(f"{k}:{v}" for k, v in top))
    if missing and not only:
        print("[town] MISSING NODES:", missing)
    if "--blend" in argv:
        bpy.context.preferences.filepaths.save_version = 0
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "out", "town.blend"))
    if preview != "none":
        import previews
        previews.run(roots, preview)


if __name__ == "__main__":
    main()
